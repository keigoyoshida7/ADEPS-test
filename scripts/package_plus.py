"""Package a completed, sealed ADEPS+ benchmark without inference or rendering.

Run only after benchmark_plus.py report. Two deterministic ZIPs separate
JSON evidence from unchanged benchmark input caches. Nothing is published.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
import zlib

import benchmark_plus as benchmark
from export_plus import validate_benchmark

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/plus-v1'
METHODS = tuple(row[0] for row in benchmark.METHODS)


def dump(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class Entry:
    source: Path | bytes
    sha256: str
    size: int
    original_path: str | None = None


def add(entries, name, source, expected=None):
    """Only explicitly selected relative members; never recurse into audio/code."""
    name = str(name)
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or '\\' in name or str(parts) != name or not name:
        raise ValueError('Unsafe ZIP member name')
    if name in entries:
        raise ValueError('Duplicate ZIP member: ' + name)
    if isinstance(source, bytes):
        entry = Entry(source, hashlib.sha256(source).hexdigest(), len(source))
    else:
        path = Path(source)
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Missing or unsafe release source: ' + str(path))
        entry = Entry(path, digest(path), path.stat().st_size, str(path.resolve().relative_to(ROOT.resolve())))
    if expected is not None and entry.sha256 != expected:
        raise ValueError('Release source changed: ' + name)
    entries[name] = entry


def require_equal(actual, expected, message):
    if actual != expected:
        raise ValueError(message)


def verify_completed():
    """Read every saved case, preserving recorded failures and undefined scores."""
    report_path = WORK / 'benchmark.json'
    report = benchmark.read_json(report_path)  # Fail before touching test inputs when unfinished.
    validate_benchmark(report)
    lock = benchmark.verify_lock()
    lock_sha = digest(WORK / 'selection-lock.json')
    pin, scenes, audio = benchmark.pin_test_inputs(lock, create=False)
    provenance = report['provenance']
    expected_provenance = {
        'lock_sha256': lock_sha, 'source_sha256': lock['source_sha256'],
        'source_set_sha256': lock['source_set_sha256'], 'input_sha256': lock['input_sha256'],
        'input_set_sha256': lock['input_set_sha256'],
        'test_input_lock_sha256': digest(WORK / 'final/input-lock.json'), 'test_inputs': pin,
    }
    for key, value in expected_provenance.items():
        require_equal(provenance.get(key), value, 'Benchmark provenance mismatch: ' + key)
    require_equal(report['selection'], lock['selection'], 'Benchmark selection changed')
    environment = benchmark.read_json(WORK / 'final/environment.json')
    require_equal(environment.get('selection_lock_sha256'), lock_sha, 'Runtime selection lock mismatch')
    require_equal(provenance['environment'], environment, 'Runtime record disagrees with report')
    expected_paths = {str((WORK / 'final' / f'{i:04d}' / f'{method}.json').relative_to(ROOT))
                      for i in range(32) for method in METHODS}
    require_equal(set(provenance['case_sha256']), expected_paths, 'Require all 32 × 9 final case hashes')
    actual_paths = {str(path.relative_to(ROOT)) for path in (WORK / 'final').glob('[0-9][0-9][0-9][0-9]/*.json')}
    require_equal(actual_paths, expected_paths, 'Missing or unexpected final case records')
    outcomes = {'completed': 0, 'failed': 0}
    for i in range(32):
        source = WORK / 'cache/test' / f'{i:04d}.npz'
        input_sha = digest(source)
        require_equal(input_sha, pin['cases'][i]['sha256'], 'Final input changed after registration')
        data, meta = benchmark.load_final_scene(source, i, scenes, audio, pin['scene_manifest_sha256'])
        row = report['scenes'][i]
        require_equal((row['id'], row['cluster_id']), (meta['id'], meta['cluster_id']), 'Report scene order/identity mismatch')
        for method in METHODS:
            path = WORK / 'final' / f'{i:04d}' / f'{method}.json'
            relative = str(path.relative_to(ROOT))
            require_equal(digest(path), provenance['case_sha256'][relative], 'Final case changed after report')
            case = benchmark.validate_case(path, method, i, meta, data, input_sha, lock_sha)
            # These checks also bind the full report to traces' exact case files.
            require_equal(case['input_sha256'], input_sha, 'Case input differs from the distributed cache')
            for key in ('metrics', 'curves'):
                require_equal(row[key][method], case[key], 'Report/case mismatch: ' + key)
            require_equal(row['outcomes'][method], case['outcome'], 'Report outcome mismatch')
            require_equal(row['runtime'][method], {key: case[key] for key in ('seconds', 'nfe', 'vjp', 'memory')}, 'Report runtime mismatch')
            outcomes[case['outcome']] += 1
    require_equal(sum(outcomes.values()), 288, 'Incomplete final evaluation')
    return report, lock, pin, audio, outcomes


def dataset_entries(audio):
    require_equal((audio['dataset'], audio['license']), ('VCTK 0.92', 'CC-BY-4.0'), 'Unexpected dataset or redistribution license')
    entries = {}
    for name in ('audio-manifest.json', 'scene-manifest.json', 'subset-plan.json'):
        add(entries, 'dataset/' + name, WORK / 'sealed-data' / name)
    for row in audio['attribution_files']:
        path = benchmark.inside(WORK / 'sealed-data/source', row['path'])
        add(entries, 'dataset/' + path.name, path, row['sha256'])
    require_equal({name for name in entries if name.endswith('.txt')},
                  {'dataset/VCTK-README.txt', 'dataset/VCTK-license.txt'}, 'Both original VCTK attribution files are required')
    credit = {
        'title': 'CSTR VCTK Corpus: English Multi-speaker Corpus for CSTR Voice Cloning Toolkit, version 0.92',
        'creators': ['Christophe Veaux', 'Junichi Yamagishi', 'Kirsten MacDonald'],
        'institution': 'Centre for Speech Technology Research, University of Edinburgh',
        'source_url': audio['source_doi'], 'license': 'CC BY 4.0',
        'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'changes': '48 kHz speech resampled to 16 kHz, convolved with independently adapted ideal HARP room responses, cropped to 32 STFT frames, and used to construct synthetic noisy array observations. The distributed NPZ files preserve the benchmark cache bytes, with no output gain or post-packaging transformation.',
        'speakers': sorted({row['speaker'] for row in audio['files']}),
        'source_files': [{'archive_member': row['archive_member'], 'sha256': row['sha256'], 'speaker': row['speaker']} for row in audio['files']],
        'endorsement': 'The corpus creators and speakers do not endorse this project.',
        'scope': 'License attribution applies to the VCTK-derived speech data. It does not assert a license for third-party HARP source code; no HARP source, original FLAC files or neural weights are included.',
    }
    add(entries, 'ATTRIBUTION.json', dump(credit))
    return entries


def collect_entries(report, lock, pin, audio, outcomes):
    common = dataset_entries(audio)
    records, inputs = dict(common), dict(common)
    add(records, 'fullbenchmark.json', WORK / 'benchmark.json')
    for name in ('selection-lock.json', 'selection.json', 'dps-selection.json'):
        for entries in (records, inputs):
            add(entries, name, WORK / name)
    for entries in (records, inputs):
        add(entries, 'final/input-lock.json', WORK / 'final/input-lock.json')
    add(records, 'final/environment.json', WORK / 'final/environment.json')
    evidence = set((WORK / 'development').rglob('*.json'))
    evidence.update(WORK.glob('*-development.json'))
    evidence.update(WORK.glob('*-dev-audit*.json'))
    evidence.update(path for path in (WORK / 'training-covariance.json', WORK / 'regression-tests.json') if path.exists())
    sealed_evidence, supplementary = [], []
    for path in sorted(evidence):
        relative = str(path.relative_to(ROOT))
        expected = lock['input_sha256'].get(relative)
        name = str(path.relative_to(WORK))
        benchmark.read_json(path)  # Reject partial/invalid JSON evidence.
        add(records, name, path, expected)
        (sealed_evidence if expected else supplementary).append(name)
    for relative, expected in report['provenance']['case_sha256'].items():
        path = benchmark.inside(ROOT, relative)
        add(records, str(path.relative_to(WORK.resolve())), path, expected)
    for item in pin['cases']:
        path = benchmark.inside(ROOT, item['path'])
        add(inputs, f'cache/test/{item["index"]:04d}.npz', path, item['sha256'])
    notes = {
        'selection_lock_sha256': digest(WORK / 'selection-lock.json'),
        'benchmark_sha256': digest(WORK / 'benchmark.json'), 'test_input_lock_sha256': digest(WORK / 'final/input-lock.json'),
        'model_weights_sha256': lock['selection']['model_weights_sha256'],
        'scene_count': 32, 'method_ids': list(METHODS), 'case_count': 288, 'outcomes': outcomes,
        'frozen_development_evidence': sealed_evidence,
        'supplementary_evidence_not_part_of_pre_test_input_seal': supplementary,
        'verification': 'verify_lock, registered input hashes and acquisition checks, all 288 case identities/estimate hashes, and metric recomputation against unchanged caches. No inference, optimization, audio download or scene rendering.',
        'completion_meaning': 'Every predeclared case has a verified record. Failed and undefined outcomes remain present; this does not imply success or an accuracy threshold was passed.',
    }
    readme = (
        'ADEPS+ independent benchmark release\n\n'
        'Read ATTRIBUTION.json and dataset/VCTK-license.txt; derived speech is CC BY 4.0.\n'
        'CSTR VCTK 0.92: Christophe Veaux, Junichi Yamagishi, Kirsten MacDonald; University of Edinburgh.\n'
        'Source: https://doi.org/10.7488/ds/2645 . Changes are recorded in ATTRIBUTION.json.\n'
        'No original FLAC corpus, HARP source code, neural weights, or per-method estimate NPZ files are included.\n\n'
        'plus-evaluation-records.zip contains the full unchanged benchmark, pre-test selections, all 288 final case JSONs\n'
        '(including traces/details, failures and undefined results), and development evidence.\n'
        'plus-final-inputs.zip contains all 32 unchanged cache/test/0000.npz ... 0031.npz benchmark caches.\n'
        'Both archives contain provenance and source attribution. MANIFEST.json hashes every other archive member.\n'
        'Supplementary audit JSONs outside the pre-test seal are labelled separately in the manifest.\n\n'
        'BENCHMARK CACHE FORMAT IS NOT THE INFERENCE CLI FORMAT.\n'
        'Load cache files with numpy.load(path, allow_pickle=False): p[257,6,32], V[257,6,36], reference[257,36,32],\n'
        'frequencies[257], positions[6,3], scalar metadata_json. Coefficients use ACN/N3D N5, before compression/gain.\n'
        '16 kHz / FFT512 / hop128 / periodic Hann / no padding, 32 frames; DC and Nyquist are real.\n'
        'reference and true scene metadata are for evaluation, not reconstruction inputs. Never provide them to a solver.\n'
        'infer_plus.py instead accepts the separately prepared public/models/plus-example-input.npz, containing\n'
        'p_real/p_imag, V_real/V_imag and explicit format metadata, without reference coefficients.\n'
        'Use that prepared scene-0000 input for the CLI example; do not pass these cache NPZs directly.\n'
        'Code and CLI instructions: https://github.com/keigoyoshida7/ADEPS-test/blob/main/docs/PLUS_USAGE.md\n\n'
        'These are synthetic evaluation inputs, not venue recordings. Full-set results do not establish superiority\n'
        'over the original ADEPS paper, general real-room accuracy, or a neural-model benefit by themselves.\n'
    ).encode('utf-8')
    for entries in (records, inputs):
        add(entries, 'README.txt', readme)
    return records, inputs, notes


def write_archive(path, entries, notes, kind):
    manifest = {'schema': 'adeps-plus-release-archive/1', 'kind': kind, **notes,
                'package_source_sha256': digest(Path(__file__)),
                'zip_encoding': {'timestamps': '1980-01-01T00:00:00', 'compression': 'DEFLATE level 6',
                                 'zlib_version': zlib.ZLIB_RUNTIME_VERSION},
                'files': {name: {'sha256': item.sha256, 'bytes': item.size, 'source_path': item.original_path}
                          for name, item in sorted(entries.items())},
                'manifest_scope': 'All archive members except MANIFEST.json itself. Byte hashes refer to uncompressed member bytes.'}
    all_entries = dict(entries)
    add(all_entries, 'MANIFEST.json', dump(manifest))
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for name, item in sorted(all_entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            info._compresslevel = 6
            source = io.BytesIO(item.source) if isinstance(item.source, bytes) else item.source.open('rb')
            h, size = hashlib.sha256(), 0
            with source, archive.open(info, 'w', force_zip64=True) as target:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    target.write(block); h.update(block); size += len(block)
            require_equal((h.hexdigest(), size), (item.sha256, item.size), 'Source changed during packaging: ' + name)
    # Verify the actual compressed artifacts, not merely their source inventory.
    with zipfile.ZipFile(path) as archive:
        require_equal(archive.namelist(), sorted(all_entries), 'ZIP inventory mismatch')
        for name, item in all_entries.items():
            h, size = hashlib.sha256(), 0
            with archive.open(name) as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    h.update(block); size += len(block)
            require_equal((h.hexdigest(), size), (item.sha256, item.size), 'ZIP member verification failed: ' + name)
    return {'sha256': digest(path), 'bytes': Path(path).stat().st_size, 'members': len(all_entries)}


def package(output_dir=None):
    report, lock, pin, audio, outcomes = verify_completed()
    records, inputs, notes = collect_entries(report, lock, pin, audio, outcomes)
    output = Path(output_dir) if output_dir else WORK
    output.mkdir(parents=True, exist_ok=True)
    payloads = [('plus-evaluation-records.zip', records, 'evaluation-records'), ('plus-final-inputs.zip', inputs, 'benchmark-inputs')]
    artifacts = {}
    with tempfile.TemporaryDirectory(prefix='.plus-package-', dir=output) as temporary:
        for name, entries, kind in payloads:
            artifacts[name] = write_archive(Path(temporary) / name, entries, notes, kind)
        # Never replace published release files if any input or case moved mid-build.
        benchmark.verify_lock()
        for entries in (records, inputs):
            for item in entries.values():
                if isinstance(item.source, Path):
                    require_equal(digest(item.source), item.sha256, 'Source changed before release staging')
        result = {'schema': 'adeps-plus-release-packages/1', **notes, 'artifacts': artifacts}
        (Path(temporary) / 'plus-release-manifest.json').write_bytes(dump(result))
        for name in [*artifacts, 'plus-release-manifest.json']:
            (Path(temporary) / name).replace(output / name)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=WORK)
    args = parser.parse_args()
    try:
        print(json.dumps(package(args.output_dir), indent=2, ensure_ascii=False, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(2, f'ADEPS+ package error: {exc}\n')
