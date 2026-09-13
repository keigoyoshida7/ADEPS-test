#!/usr/bin/env python3
"""Restore the exact released speech-data manifests and their verified payloads.

Only official VCTK and pinned HARP URLs from paper_data.py are used. Acquisition
runs in a temporary non-public directory; its regenerated bookkeeping is never
substituted for the original manifest bytes. This does not train or run a model.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile
import zlib

try:
    from . import paper_data
except ImportError:
    import paper_data

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {'subset-plan.json': 2_000_000, 'audio-manifest.json': 4_000_000,
          'scene-manifest.json': 32_000_000}
MAX_ZIP_BYTES = 40_000_000
MAX_REPORT_BYTES = 4_000_000
SOURCE_FILES = ('scripts/paper_data.py', 'scripts/train_paper_prior.py',
                'backend/paper_prior.py')
SPLITS = ('train', 'validation', 'test')
HARP_FILES = ('README.md', 'requirements.txt', 'v1/Generate.py', 'v1/SphericalHarmonic.py')
ATTRIBUTION = {'source/VCTK-README.txt': paper_data.VCTK_README_URL,
               'source/VCTK-license.txt': paper_data.VCTK_LICENSE_URL}


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _json(payload, name):
    def invalid(value):
        raise ValueError(f'Non-finite JSON number in {name}: {value}')
    def number(value):
        result = float(value)
        if not math.isfinite(result):
            invalid(value)
        return result
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object,
                           parse_constant=invalid, parse_float=number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f'Invalid JSON: {name}') from error
    _require(isinstance(value, dict), f'{name} must contain one JSON object')
    return value


def _read_bounded(path, limit):
    path = Path(path)
    _require(path.is_file() and path.stat().st_size <= limit, f'File missing or too large: {path.name}')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    _require(len(data) <= limit, f'File exceeds size limit: {path.name}')
    return data


def read_bundle(metadata_zip, report_path, metadata_sha256=None):
    """Read three top-level JSON members; never extract archive paths to disk."""
    packed = _read_bounded(metadata_zip, MAX_ZIP_BYTES)
    if metadata_sha256 is not None:
        _require(_hash(metadata_sha256) and digest_bytes(packed) == metadata_sha256,
                 'Metadata ZIP SHA-256 mismatch')
    report = _json(_read_bounded(report_path, MAX_REPORT_BYTES), 'report.json')
    try:
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            members = archive.infolist()
            _require(len(members) == 3 and {item.filename for item in members} == set(LIMITS),
                     'Metadata ZIP must contain exactly the three known top-level JSON files')
            raw = {}
            for item in members:
                mode = stat.S_IFMT(item.external_attr >> 16)
                _require(not item.is_dir() and mode in (0, stat.S_IFREG)
                         and not item.flag_bits & 1
                         and item.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                         'Metadata ZIP contains a link, directory, encrypted or unsupported member')
                limit = LIMITS[item.filename]
                _require(0 <= item.file_size <= limit, f'Metadata member too large: {item.filename}')
                with archive.open(item) as stream:
                    payload = stream.read(limit + 1)
                _require(len(payload) == item.file_size and len(payload) <= limit,
                         f'Metadata member size mismatch: {item.filename}')
                raw[item.filename] = payload
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, zlib.error) as error:
        raise ValueError('Invalid metadata ZIP') from error
    documents = {name: _json(value, name) for name, value in raw.items()}
    expected = validate_metadata(raw, documents, report)
    return raw, report, expected, digest_bytes(packed)


def validate_metadata(raw, documents, report):
    """Validate the hash chain, official sources and every writable payload path."""
    _require(report.get('schema') == 'adeps-test-paper-prior-training/1'
             and report.get('status') == 'evaluated'
             and isinstance(report.get('model'), dict)
             and report['model'].get('id') == 'paper-prior-v1'
             and _hash(report['model'].get('weights_sha256')),
             'An evaluated paper-prior-v1 report is required')
    data = report.get('data', {})
    _require(isinstance(data, dict) and _hash(data.get('manifest_sha256'))
             and digest_bytes(raw['scene-manifest.json']) == data['manifest_sha256'],
             'Scene manifest does not match the checkpoint report SHA-256')
    plan, audio, scene = (documents[name] for name in LIMITS)
    _require(all(value.get('schema') == paper_data.SCHEMA for value in (plan, audio, scene)),
             'Unsupported metadata schema')
    _require(scene.get('audio_manifest_path') == 'audio-manifest.json'
             and scene.get('audio_manifest_sha256') == digest_bytes(raw['audio-manifest.json']),
             'Audio manifest SHA-256 or relative path mismatch')
    if 'audio_manifest_sha256' in data:
        _require(data['audio_manifest_sha256'] == scene['audio_manifest_sha256'],
                 'Report/audio manifest SHA-256 mismatch')
    # Check only known repository files; never resolve paths supplied by JSON.
    recorded_sources = report.get('source_sha256', {})
    _require(isinstance(recorded_sources, dict), 'Report source-code hashes are missing')
    for name in SOURCE_FILES:
        _require(_hash(recorded_sources.get(name))
                 and paper_data.sha256(ROOT / name) == recorded_sources[name],
                 f'Checkout differs from the recorded training source: {name}')
    _require(scene.get('scene_generator_script_sha256') == recorded_sources['scripts/paper_data.py'],
             'Scene generator identity differs from the training report')
    _require(plan.get('stage') == 'planned-not-downloaded'
             and audio.get('stage') == 'downloaded-and-crc-sha-verified'
             and plan.get('archive_url') == paper_data.VCTK_URL
             and plan.get('source_doi') == paper_data.VCTK_DOI,
             'Only the recorded official VCTK source is supported')
    for key, value in plan.items():
        if key not in ('stage', 'files'):
            _require(audio.get(key) == value, f'Plan/audio metadata differ: {key}')
    files, acquired = plan.get('files'), audio.get('files')
    _require(isinstance(files, list) and 1 <= len(files) <= 5000
             and isinstance(acquired, list) and len(acquired) == len(files),
             'Invalid planned/acquired file list')
    splits = plan.get('speaker_splits', {})
    _require(isinstance(splits, dict) and set(splits) == set(SPLITS)
             and all(isinstance(splits[key], list) and splits[key] for key in SPLITS),
             'Three nonempty speaker splits are required')
    speakers = [speaker for split in SPLITS for speaker in splits[split]]
    _require(all(isinstance(s, str) and re.fullmatch(r'p[0-9]+', s) for s in speakers)
             and len(set(speakers)) == len(speakers), 'Invalid or overlapping speaker splits')
    expected = {}
    for before, after in zip(files, acquired):
        _require(isinstance(before, dict) and isinstance(after, dict), 'Invalid audio record')
        _require(all(after.get(key) == value for key, value in before.items()),
                 'Planned and acquired audio members differ')
        speaker, member, split = before.get('speaker'), before.get('archive_member'), before.get('split')
        _require(isinstance(member, str) and isinstance(speaker, str)
                 and split in SPLITS and speaker in splits[split], 'Invalid member speaker or split')
        _require(re.fullmatch(r'(?:VCTK-Corpus-0\.92/)?wav48_silence_trimmed/' + re.escape(speaker)
                             + '/' + re.escape(speaker) + r'_[0-9]+_mic2\.flac', member) is not None,
                 'Unsafe or unsupported VCTK member path')
        relative = f'audio/{speaker}/{member.rsplit("/", 1)[-1]}'
        _require(after.get('path') == relative and relative not in expected
                 and _hash(after.get('sha256'))
                 and _integer(before.get('size_bytes'), 1, 100_000_000)
                 and _integer(before.get('compressed_bytes'), 1, 100_000_000)
                 and isinstance(before.get('crc32'), str)
                 and re.fullmatch(r'[0-9a-f]{8}', before['crc32']) is not None,
                 'Invalid audio path, identity or size')
        _require(after.get('sample_rate') == 48000 and _integer(after.get('frames'), 1),
                 'Unexpected VCTK sample rate or frame count')
        expected[relative] = (before['size_bytes'], after['sha256'])
    _require(plan.get('extracted_member_bytes') == sum(row['size_bytes'] for row in files)
             and plan.get('compressed_member_bytes') == sum(row['compressed_bytes'] for row in files)
             and _integer(plan.get('metadata_transfer_bytes'), 0, 50_000_000)
             and _integer(plan.get('archive_size_bytes'), 1)
             and isinstance(plan.get('archive_etag'), str), 'Invalid archive sizes or identity')
    _require(data.get('downloaded_utterances') == len(files), 'Report audio count differs')
    for split in SPLITS:
        _require(data.get(f'{split}_speakers') == splits[split], 'Report speaker split differs')
    harp = audio.get('harp_upstream', {})
    _require(isinstance(harp, dict) and harp.get('commit') == paper_data.HARP_COMMIT,
             'Unsupported HARP source commit')
    if 'harp_commit' in data:
        _require(data['harp_commit'] == paper_data.HARP_COMMIT, 'Report HARP commit differs')
    source_paths = {**ATTRIBUTION, **{f'upstream/HARP/{name}': paper_data.HARP_SOURCE + name for name in HARP_FILES}}
    actual_sources = audio.get('attribution_files', []) + harp.get('files', [])
    _require(len(actual_sources) == len(source_paths) and all(isinstance(row, dict) for row in actual_sources),
             'Missing or unexpected upstream source records')
    by_url = {row.get('url'): row for row in actual_sources}
    _require(len(by_url) == len(source_paths) and set(by_url) == set(source_paths.values()),
             'Only pinned upstream and official attribution URLs are permitted')
    for relative, url in source_paths.items():
        row = by_url[url]
        _require(row.get('path') == Path(relative).name and _hash(row.get('sha256'))
                 and _integer(row.get('bytes'), 1, 1_000_000), 'Invalid upstream source identity')
        expected[relative] = (row['bytes'], row['sha256'])
    rows = scene.get('scenes')
    _require(isinstance(rows, list) and 3 <= len(rows) <= 100000, 'Invalid scene list')
    counts, ids = dict.fromkeys(SPLITS, 0), set()
    for row in rows:
        _require(isinstance(row, dict) and row.get('split') in SPLITS
                 and isinstance(row.get('id'), str) and row['id'] not in ids,
                 'Invalid or duplicate scene record')
        split = row['split']; ids.add(row['id']); counts[split] += 1
        indexes = row.get('audio_indexes')
        _require(isinstance(indexes, list) and indexes
                 and all(_integer(i, 0, len(acquired) - 1) and acquired[i]['split'] == split for i in indexes),
                 'Invalid audio index or split leakage in scene manifest')
    _require(scene.get('planned_scene_counts') == counts and all(counts.values()),
             'Scene counts do not match metadata')
    for name, payload in raw.items():
        expected[name] = (len(payload), digest_bytes(payload))
    return expected


def verify_tree(directory, expected, metadata=True):
    """Hash every file; reject symlinks and unexpected payloads."""
    directory = Path(directory)
    _require(directory.is_dir() and not directory.is_symlink(), 'Data directory is missing or a symlink')
    actual = set()
    for path in directory.rglob('*'):
        _require(not path.is_symlink(), 'Symlinks are not allowed in a restored data directory')
        _require(path.is_dir() or path.is_file(), 'Unsupported data-directory entry')
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    wanted = set(expected) if metadata else set(expected) - set(LIMITS)
    relevant = actual if metadata else actual - set(LIMITS)
    _require(relevant == wanted, 'Data directory has missing or unexpected files')
    for relative in sorted(wanted):
        path = directory / relative
        size, digest = expected[relative]
        _require(path.stat().st_size == size and paper_data.sha256(path) == digest,
                 f'Payload SHA-256 or size mismatch: {relative}')


def _destination(path):
    original = Path(path).expanduser().absolute()
    _require(not original.is_symlink(), 'Destination cannot be a symlink')
    target = original.resolve()
    _require(target != ROOT and not any(target.is_relative_to(ROOT / folder) for folder in ('public', 'dist')),
             'Choose a dedicated non-public data directory, outside public/ and dist/')
    return target


def restore(metadata_zip, report_path, destination, *, metadata_sha256=None,
            max_bytes=500_000_000, verify_only=False, acquire=None):
    _require(_integer(max_bytes, 1, 2_000_000_000), 'Transfer budget must be 1..2,000,000,000 bytes')
    target = _destination(destination)
    raw, report, expected, metadata_digest = read_bundle(metadata_zip, report_path, metadata_sha256)
    summary = {'model': report['model']['id'], 'weights_sha256': report['model']['weights_sha256'],
               'scene_manifest_sha256': report['data']['manifest_sha256'],
               'metadata_zip_sha256': metadata_digest, 'files_verified': len(expected),
               'destination': str(target)}
    if verify_only:
        verify_tree(target, expected)
        return {**summary, 'status': 'verified-existing'}
    _require(not target.exists() or (target.is_dir() and not any(target.iterdir())),
             'Destination is not empty; use --verify-only to check it without changing it')
    target.parent.mkdir(parents=True, exist_ok=True)
    # A sibling staging tree permits a final rename without copying large audio.
    with tempfile.TemporaryDirectory(prefix='.adeps-restore-', dir=target.parent) as temporary:
        staging = Path(temporary) / 'payload'
        staging.mkdir()
        (staging / 'subset-plan.json').write_bytes(raw['subset-plan.json'])
        (acquire or paper_data.acquire_subset)(staging, max_bytes=max_bytes)
        verify_tree(staging, expected, metadata=False)
        for name, payload in raw.items():
            (staging / name).write_bytes(payload)
        verify_tree(staging, expected)
        _require(not target.is_symlink() and (not target.exists() or (target.is_dir() and not any(target.iterdir()))),
                 'Destination changed during acquisition; nothing was installed')
        if target.exists():
            target.rmdir()  # only an empty directory, checked immediately above
        os.rename(staging, target)
    return {**summary, 'status': 'restored-exact-manifests'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, required=True, help='Release ZIP containing only the three original JSON manifests')
    parser.add_argument('--report', type=Path, required=True, help='Evaluated model report.json')
    parser.add_argument('--destination', type=Path, required=True, help='Empty non-public data directory')
    parser.add_argument('--metadata-sha256', help='Expected release ZIP SHA-256, when provided by the publisher')
    parser.add_argument('--max-mb', type=int, default=500, help='Bounded archive transfer budget in decimal MB (default: 500)')
    parser.add_argument('--verify-only', action='store_true', help='Verify an existing tree; no network or writes')
    args = parser.parse_args()
    try:
        result = restore(args.metadata, args.report, args.destination, metadata_sha256=args.metadata_sha256,
                         max_bytes=args.max_mb * 1_000_000, verify_only=args.verify_only)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        parser.exit(1, f'Restore failed: {error}\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
