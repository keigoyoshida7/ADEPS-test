"""Post-hoc paper-metric evaluation of sealed ADEPS+ estimates; CPU only.

No inference, training, selection, or edits to the v0.7.0 benchmark. Every
input/estimate must match its sealed record before a new score is calculated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
KEYS = ('si_sdr_db', 'spectral_error_db', 'coherence', 'ild_error_db', 'ic_error')
PROFILES = ('strict', 'reference_floor')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_file(path, expected):
    if not isinstance(expected, str) or len(expected) != 64 or sha(path) != expected:
        raise ValueError(f'File does not match the recorded SHA-256: {path.name}')


def complete_mean(values):
    """Never delete failed/undefined scenes when averaging."""
    if not values or any(v is None or isinstance(v, bool) or not math.isfinite(v) for v in values):
        return None
    return math.fsum(float(v) / len(values) for v in values)


def aggregate_profiles(scenes, methods):
    output = {}
    for profile in PROFILES:
        means, counts, curves = {}, {}, {}
        for method in methods:
            rows = [s['profiles'][profile][method] for s in scenes]
            means[method] = {key: complete_mean([r['metrics'][key] for r in rows]) for key in KEYS}
            counts[method] = {key: sum(r['metrics'][key] is not None for r in rows) for key in KEYS}
            curves[method] = {key: [complete_mean([r['curves'][key][i] for r in rows])
                for i in range(len(rows[0]['curves'][key]))] for key in rows[0]['curves']}
        output[profile] = {'means': means, 'finite_scene_counts': counts, 'curves': curves}
    return output


def csv_bytes(report):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['scope', 'scene_id', 'cluster_id', 'profile', 'method', *KEYS])
    for profile in PROFILES:
        for method in report['methods']:
            writer.writerow(['all_scenes', '', '', profile, method['id'],
                *[report['profiles'][profile]['means'][method['id']][k] for k in KEYS]])
        for scene in report['scenes']:
            for method in report['methods']:
                writer.writerow(['single_scene', scene['id'], scene['cluster_id'], profile, method['id'],
                    *[scene['profiles'][profile][method['id']]['metrics'][k] for k in KEYS]])
    return ('\ufeff' + stream.getvalue()).encode('utf-8')


def rescore(work: Path, output: Path):
    from paper_comparison_metrics import evaluate_paper_spectra, real_wave_foa
    from paper_binaural_metrics import evaluate_binaural
    from plus_metrics import si_sdr_metrics

    original = work / 'benchmark.json'
    source_paths = ('backend/paper_comparison_metrics.py', 'backend/paper_binaural_metrics.py',
                    'scripts/rescore_paper_comparison.py')
    source_hashes = {p: sha(ROOT / p) for p in source_paths}
    reference_hash = sha(ROOT / 'public/models/paper-reference-v3.json')
    decoder_hash = sha(ROOT / 'public/models/paper-ku100-foa.json')
    source = json.loads(original.read_text())
    if source.get('schema') != 'adeps-plus-benchmark/1' or source.get('status') != 'evaluated':
        raise ValueError('A completed sealed ADEPS+ benchmark is required.')
    cases = source['provenance']['test_inputs']['cases']
    methods = [m['id'] for m in source['methods']]
    if len(cases) != len(source['scenes']) or len({c['scene_id'] for c in cases}) != len(cases):
        raise ValueError('Scene manifest is incomplete or duplicated.')
    for path, digest in source['provenance']['source_sha256'].items():
        checked_file(ROOT / path, digest)
    checked_file(work / 'selection-lock.json', source['provenance']['lock_sha256'])
    baseline_hash = sha(original)
    scenes, file_hashes, definitions = [], {}, {}
    for case, saved in zip(cases, source['scenes']):
        index = case['index']
        if saved['id'] != case['scene_id'] or saved['cluster_id'] != case['cluster_id']:
            raise ValueError('Scene identity mismatch.')
        path = work / 'cache' / 'test' / f'{index:04d}.npz'
        checked_file(path, case['sha256'])
        file_hashes[f'cache/test/{index:04d}.npz'] = case['sha256']
        with np.load(path, allow_pickle=False) as z:
            reference = z['reference'].copy()
            frequencies = z['frequencies'].copy()
        scene = {'id': saved['id'], 'cluster_id': saved['cluster_id'],
                 'profiles': {p: {} for p in PROFILES}}
        for method in methods:
            record_path = work / 'final' / f'{index:04d}' / f'{method}.json'
            record = json.loads(record_path.read_text())
            estimate_path = record_path.with_suffix('.npz')
            if (record['method'] != method or record['scene_id'] != saved['id']
                    or record['input_sha256'] != case['sha256']
                    or record['selection_lock_sha256'] != source['provenance']['lock_sha256']
                    or record['outcome'] != 'completed'):
                raise ValueError(f'Invalid saved reconstruction record: {record_path.name}')
            checked_file(estimate_path, record['estimate_sha256'])
            for f in (record_path, estimate_path):
                file_hashes[f.relative_to(work).as_posix()] = sha(f)
            with np.load(estimate_path, allow_pickle=False) as z:
                estimate = z['estimate'].copy()
            sdr = si_sdr_metrics(estimate[:, :4], reference[:, :4])
            old_sdr = saved['metrics'][method]['si_sdr_db']
            if (old_sdr is None) != (sdr['si_sdr_db'] is None) or (old_sdr is not None and
                    not math.isclose(old_sdr, sdr['si_sdr_db'], abs_tol=1e-9, rel_tol=1e-9)):
                raise ValueError('SI-SDR differs from the sealed waveform metric.')
            a, b = real_wave_foa(estimate), real_wave_foa(reference)
            binaural = evaluate_binaural(a, b, frequencies)
            spectra = evaluate_paper_spectra(a, b, frequencies)
            for profile in PROFILES:
                spectral = spectra if profile == 'strict' else spectra['sensitivity']
                scene['profiles'][profile][method] = {
                    'metrics': {'si_sdr_db': sdr['si_sdr_db'], **spectral['metrics'],
                        **{k: binaural['metrics'][k] for k in ('ild_error_db', 'ic_error')}},
                    'curves': {**spectral['curves'], **{k: binaural['curves'][k]
                        for k in ('ild_error_db', 'ic_error')}},
                    'statuses': {'si_sdr': sdr['status'], 'spectral': spectral['details'].get('statuses'),
                                 'binaural': binaural['metrics'].get('status')},
                    'spectral_details': {
                        'undefined_by_frequency': {k: {str(i): status for i, status in enumerate(
                            spectral['details'][k + '_status_by_frequency']) if not status.startswith('defined')}
                            for k in ('spectral_error', 'coherence')},
                        'counts': {k: sum(v) if isinstance(v, list) else v for k, v in spectral['details']['counts'].items()},
                        **{k: v for k, v in spectral['details'].items() if k.startswith('floor_')}},
                    'sensitivity': {'ic_signed_zero_lag_error': binaural['metrics']['ic_signed_zero_lag_error']},
                    'binaural_details': {k: binaural['details'][k] for k in (
                        'reference_active_bands', 'valid_bands', 'reference_active_band_count', 'valid_band_count',
                        'reference_cues', 'estimate_cues')},
                }
                if profile not in definitions:
                    definitions[profile] = {'profile': spectral['details']['profile'],
                        'definitions': spectral['details']['definitions']}
            if 'binaural' not in definitions:
                definitions['binaural'] = {k: v for k, v in binaural['details'].items() if k not in (
                    'reference_active_bands', 'valid_bands', 'reference_active_band_count', 'valid_band_count',
                    'reference_cues', 'estimate_cues')}
                definitions['binaural_frequencies_hz'] = binaural['curves']['center_frequencies_hz']
                definitions['si_sdr'] = {'definition': sdr['definition'],
                    'evaluated_samples': sdr['evaluated_samples'], 'trim_each_end_samples': sdr['trim_each_end_samples']}
        scenes.append(scene)
        print(f'Re-scored {len(scenes)}/{len(cases)} scenes, all {len(methods)} methods', flush=True)
    profiles = aggregate_profiles(scenes, methods)
    report = {'schema': 'adeps-paper-comparison/1', 'status': 'evaluated',
        'created_at': datetime.now(timezone.utc).isoformat(), 'evaluation_kind': 'post_hoc_fixed_estimates',
        'original_paper_reproduced': False, 'source_benchmark_sha256': baseline_hash,
        'source_benchmark_url': 'models/plus-benchmark.json', 'reference_url': 'models/paper-reference-v3.json',
        'conditions': source['conditions'], 'methods': source['methods'], 'scenes': scenes,
        'metric_keys': list(KEYS), 'frequencies_hz': frequencies.tolist(),
        'binaural_frequencies_hz': definitions.pop('binaural_frequencies_hz'),
        'profiles': profiles, 'definitions': definitions,
        'provenance': {'input_and_result_sha256': file_hashes,
            'source_sha256': source_hashes,
            'reference_sha256': reference_hash, 'decoder_sha256': decoder_hash,
            'python': platform.python_version(), 'numpy': np.__version__,
            'selection_lock_sha256': source['provenance']['lock_sha256']}}
    if sha(original) != baseline_hash:
        raise ValueError('Original benchmark changed during evaluation.')
    for path, digest in source_hashes.items():
        checked_file(ROOT / path, digest)
    checked_file(ROOT / 'public/models/paper-reference-v3.json', reference_hash)
    checked_file(ROOT / 'public/models/paper-ku100-foa.json', decoder_hash)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
    output.with_suffix('.csv').write_bytes(csv_bytes(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'work/plus-v1')
    parser.add_argument('--output', type=Path, default=ROOT / 'public/models/paper-comparison.json')
    args = parser.parse_args()
    result = rescore(args.work.resolve(), args.output.resolve())
    print(json.dumps({'output': str(args.output), 'scenes': len(result['scenes']),
        'sha256': sha(args.output)}, ensure_ascii=False))
