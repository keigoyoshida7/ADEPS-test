"""Separate, reproducible ADEPS+ development and sealed evaluation data.

Imports the frozen v0.6.0 generator; never changes or overwrites its files.
No final-test rendering/scoring is performed by the acquisition command.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'backend'))
from paper_data import (RangeReader, VCTK_URL, VCTK_DOI, SCHEMA, acquire_subset,
                        SceneDataset, sha256, write_json, scene_spec)
from capture import modal_matrix

BASE = ROOT / 'work/paper-data'
OUT = ROOT / 'work/plus-v1'


def plan_fresh():
    destination = OUT / 'sealed-data'
    if (destination / 'subset-plan.json').exists():
        raise ValueError('A sealed plan already exists; never silently reselect a test set')
    old = json.loads((BASE / 'audio-manifest.json').read_text())
    excluded = sorted({row['speaker'] for row in old['files']})
    # Fixed in source BEFORE final test inference. Exclude common VCTK sentences
    # 001..024 and every utterance index consumed in the existing subset. This
    # conservative index exclusion is not proof of transcript disjointness.
    excluded_ids = {int(Path(row['archive_member']).name.split('_')[1]) for row in old['files']}
    rng = np.random.default_rng(2026091307)
    with RangeReader(max_bytes=50_000_000) as remote, zipfile.ZipFile(remote) as archive:
        groups = {}
        for info in archive.infolist():
            match = re.fullmatch(r'wav48_silence_trimmed/(p\d+)/(p\d+)_(\d+)_mic2.flac', info.filename)
            if not match:
                continue
            speaker, number = match[1], int(match[3])
            if speaker in excluded or speaker in ('p280', 'p315') or number <= 24 or number in excluded_ids:
                continue
            groups.setdefault(speaker, []).append(info)
        eligible = sorted(key for key, files in groups.items() if len(files) >= 4)
        speakers = [str(x) for x in rng.choice(eligible, 8, replace=False)]
        files = []
        for speaker in speakers:
            available = sorted(groups[speaker], key=lambda x: x.filename)
            for index in sorted(rng.choice(len(available), 4, replace=False)):
                item = available[index]
                files.append({'split': 'test', 'speaker': speaker, 'archive_member': item.filename,
                              'size_bytes': item.file_size, 'compressed_bytes': item.compress_size,
                              'crc32': f'{item.CRC:08x}'})
        plan = {'schema': SCHEMA, 'stage': 'planned-not-downloaded', 'dataset': 'VCTK 0.92',
                'source_doi': VCTK_DOI, 'license': 'CC-BY-4.0', 'archive_url': VCTK_URL,
                'archive_size_bytes': remote.size, 'archive_etag': remote.etag,
                'metadata_transfer_bytes': remote.transferred,
                'compressed_member_bytes': sum(row['compressed_bytes'] for row in files),
                'extracted_member_bytes': sum(row['size_bytes'] for row in files),
                'speaker_splits': {'train': [], 'validation': [], 'test': speakers},
                'selection': {'seed': 2026091307, 'excluded_speakers': excluded,
                              'excluded_utterance_ids': sorted(excluded_ids), 'minimum_utterance_id': 25,
                              'text_disjointness': 'Common first 24 and all legacy utterance indices excluded; full transcript disjointness not asserted.'},
                'files': files}
    write_json(destination / 'subset-plan.json', plan)
    return plan


def fresh_manifest():
    destination = OUT / 'sealed-data'
    path = destination / 'scene-manifest.json'
    if path.exists():
        raise ValueError('A sealed scene manifest already exists')
    audio = json.loads((destination / 'audio-manifest.json').read_text())
    speakers = audio['speaker_splits']['test']
    # Four speaker pairs, eight rooms each: four single-source and four
    # two-source rooms. Repeated utterances are clustered, never treated as
    # independent evidence in the confidence interval.
    rows = []
    for pair in range(4):
        a, b = speakers[2*pair:2*pair+2]
        indexes_a = [i for i, row in enumerate(audio['files']) if row['speaker'] == a]
        indexes_b = [i for i, row in enumerate(audio['files']) if row['speaker'] == b]
        for trial in range(8):
            seed = 937000000 + 10007 * (pair*8+trial)
            spec = scene_spec(seed)
            count = 1 if trial < 4 else 2
            # Generate until this predefined source-count condition is met;
            # this occurs before any audio rendering or method output exists.
            while len(spec['sources_m']) != count:
                seed += 1
                spec = scene_spec(seed)
            indices = ([indexes_a[trial//2] if trial % 2 == 0 else indexes_b[trial//2]]
                       if count == 1 else [indexes_a[trial-4], indexes_b[trial-4]])
            spec.update(id=f'plus-test-{pair*8+trial:04d}', split='test',
                        audio_indexes=indices, crop_fraction=float(np.random.default_rng(seed+1).uniform()),
                        cluster_id=f'speaker-pair-{pair}', speaker_pair=[a, b])
            rows.append(spec)
    manifest = {'schema': SCHEMA, 'audio_manifest_path': 'audio-manifest.json',
                'audio_manifest_sha256': sha256(destination / 'audio-manifest.json'),
                'scene_generator_script_sha256': sha256(ROOT / 'scripts/paper_data.py'),
                'selection_source_sha256': sha256(__file__), 'target_order': 5,
                'target_convention': 'ACN/N3D real SH, Y00=1, first order W,Y,Z,X',
                'split_policy': 'Eight fresh speakers excluded from all 16 legacy speakers; 4 disjoint speaker-pair clusters.',
                'planned_scene_counts': {'train': 0, 'validation': 0, 'test': 32}, 'scenes': rows}
    write_json(path, manifest)
    return manifest


def render(split, count):
    if split == 'test':
        lock = OUT / 'selection-lock.json'
        if not lock.exists():
            raise ValueError('Final test cannot be rendered before selection-lock.json exists')
        from benchmark_plus import verify_lock
        verify_lock()
        manifest = OUT / 'sealed-data/scene-manifest.json'
    else:
        manifest = BASE / 'scene-manifest.json'
    dataset = SceneDataset(manifest, split=split, rir_cache_size=0)
    directory = OUT / 'cache' / split
    directory.mkdir(parents=True, exist_ok=True)
    # First 64 train scenes for covariance/scale calibration; first 16
    # validation scenes for development. All scenes retained, including weak
    # speech and DC-heavy cases. Never pick by method performance.
    for index in range(min(count, len(dataset))):
        target = directory / f'{index:04d}.npz'
        if target.exists():
            continue
        value = dataset[index]
        reference = value['clean_stft'].transpose(1, 0, 2).astype(np.complex128)
        reference[[0, -1]] = reference[[0, -1]].real
        frequencies = np.fft.rfftfreq(512, 1/16000)
        q, radius = 6, .06
        z = 1 - 2 * (np.arange(q)+.5)/q
        angle = np.arange(q)*np.pi*(3-np.sqrt(5))
        positions = radius*np.c_[np.sqrt(1-z*z)*np.cos(angle), np.sqrt(1-z*z)*np.sin(angle), z]
        v = modal_matrix(frequencies, positions, 5)
        v[[0, -1]] = v[[0, -1]].real
        pressure = v @ reference
        seed = {'train': 650000, 'validation': 750000, 'test': 850000}[split] + index
        rng = np.random.default_rng(seed)
        noise = rng.normal(size=pressure.shape)+1j*rng.normal(size=pressure.shape)
        noise[[0, -1]] = noise[[0, -1]].real
        amplitude = np.linalg.norm(pressure)/np.linalg.norm(noise)*10**(-50/20)
        noisy = pressure + amplitude*noise
        metadata = {**value['metadata'], 'manifest_sha256': sha256(manifest),
                    'observation_seed': seed, 'snr_db': 50., 'microphones': q, 'radius_m': radius,
                    'noise_complex_variance': float(2*amplitude**2),
                    'split': split, 'scene_index': index,
                    'source_attribution': 'VCTK 0.92, Yamagishi/Veaux/MacDonald, CC BY 4.0, doi:10.7488/ds/2645'}
        np.savez_compressed(target, reference=reference, p=noisy, V=v, frequencies=frequencies,
                            positions=positions, metadata_json=json.dumps(metadata, ensure_ascii=False))
        print(json.dumps({'stage': 'render', 'split': split, 'index': index,
                          'dc_energy_fraction': float(np.sum(abs(reference[0,:4])**2)/np.sum(abs(reference[:,:4])**2))}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'fetch', 'manifest', 'render'])
    parser.add_argument('--split', choices=['train', 'validation', 'test'], default='validation')
    parser.add_argument('--count', type=int, default=16)
    args = parser.parse_args()
    if args.command == 'plan':
        value = plan_fresh()
        print(json.dumps({'speakers': value['speaker_splits']['test'], 'files': len(value['files'])}))
    elif args.command == 'fetch':
        acquire_subset(OUT / 'sealed-data', 80_000_000)
    elif args.command == 'manifest':
        value = fresh_manifest()
        print(json.dumps({'scenes': len(value['scenes']), 'manifest_sha256': sha256(OUT/'sealed-data/scene-manifest.json')}))
    else:
        render(args.split, args.count)
