"""Publish already-computed ADEPS+ results, using preselected test scene zero.

No model, scene renderer, optimization, or test-set method selection is run.
The complete saved benchmark and sealed identities are prerequisites. The
example is presentation of those saved coefficients, not a new evaluation.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from diffusion_studio import (BANDS, PREVIEW_MATRIX, FREQUENCY_METRIC_DEFINITIONS,
                              _preview_pcm16, coherence_summary, covariance,
                              frequency_metrics, real_wave_foa)
from neural_audio import wav_bytes
from plus_consistency import synthesize_spectra
from infer_paper_prior import load_input

METHOD_IDS = ('linear_default', 'linear_tuned', 'linear_noise', 'adeps_current',
              'adeps_tuned', 'spatial_only', 'consistency_only', 'plus', 'plus_no_denoiser')
FREQUENCIES = np.fft.rfftfreq(512, 1 / 16000)
EXPORT_SOURCES = ('scripts/export_plus.py', 'scripts/infer_paper_prior.py', 'backend/diffusion_studio.py',
                  'backend/neural_audio.py', 'backend/plus_consistency.py')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def read_json(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    dump(value)
    return value


def scalar(value):
    return value is None or (type(value) in (int, float) and np.isfinite(value))


def validate_benchmark(report):
    if report.get('schema') != 'adeps-plus-benchmark/1' or report.get('status') != 'evaluated':
        raise ValueError('Only a completed adeps-plus-benchmark/1 report can be published.')
    conditions = report['conditions']
    if any(conditions.get(key) != value for key, value in
           [('scenes', 32), ('clusters', 4), ('microphones', 6), ('sample_rate_hz', 16000)]):
        raise ValueError('Require the complete predeclared 32-scene, four-cluster, six-microphone test.')
    if not np.array_equal(report['frequencies_hz'], FREQUENCIES):
        raise ValueError('The report must use every 0..8 kHz STFT bin.')
    ids = [row['id'] for row in report['methods']]
    if tuple(ids) != METHOD_IDS:
        raise ValueError('All nine methods must remain in their declared order.')
    scenes = report['scenes']
    if len(scenes) != 32 or len({s['id'] for s in scenes}) != 32:
        raise ValueError('Require all 32 unique final scenes, with failures retained.')
    clusters = Counter(s['cluster_id'] for s in scenes)
    if len(clusters) != 4 or set(clusters.values()) != {8}:
        raise ValueError('Require four clusters of eight scenes.')
    metric_keys = ('nrmse_db', 'non_dc_nrmse_db', 'speech_band_nrmse_db',
                   'magnitude_error_db', 'coherence', 'si_sdr_db')
    curve_keys = ('nrmse_db', 'magnitude_spectrum_error_db', 'magnitude_squared_coherence')
    for scene in scenes:
        for method in ids:
            scores = scene['metrics'][method]
            if any(key not in scores or not scalar(scores[key]) for key in metric_keys):
                raise ValueError('Incomplete or nonfinite saved scene metrics.')
            for key in curve_keys:
                values = scene['curves'][method][key]
                if not isinstance(values, list) or len(values) != 257 or not all(scalar(v) for v in values):
                    raise ValueError('Incomplete saved scene curves.')
    for row in report['methods']:
        values = [s['metrics'][row['id']]['nrmse_db'] for s in scenes]
        mean = float(np.mean(values)) if all(v is not None for v in values) else None
        actual = row['mean_nrmse_db']
        if (mean is None) != (actual is None) or (mean is not None and not np.isclose(mean, actual, rtol=0, atol=1e-8)):
            raise ValueError('Published method mean differs from the complete saved scene set.')
    dump(report)


def verify_seal(work, report, selection):
    lock_path = work / 'selection-lock.json'
    lock = read_json(lock_path)
    if (lock.get('schema') != 'adeps-plus-selection-lock/1'
            or lock.get('status') != 'sealed_before_final_test_rendering_or_inference'):
        raise ValueError('Missing pre-test selection seal.')
    lock_sha = sha(lock_path)
    if report['provenance']['lock_sha256'] != lock_sha:
        raise ValueError('Benchmark selection lock mismatch.')
    if selection != lock['selection'] or selection != report['selection']:
        raise ValueError('The published selection must be the exact pre-test selection.')
    if tuple(lock['method_ids']) != METHOD_IDS:
        raise ValueError('The sealed method set differs.')
    for mapping in ('source_sha256', 'input_sha256'):
        if report['provenance'][mapping] != lock[mapping]:
            raise ValueError('Benchmark provenance differs from the seal.')
        for relative, digest in lock[mapping].items():
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != digest:
                raise ValueError(f'Sealed identity changed or missing: {relative}')
    return lock_sha


def canonical_observation_sha(data):
    digest = hashlib.sha256()
    for value in (data['frequencies'], data['V'].real, data['V'].imag, data['p'].real, data['p'].imag):
        digest.update(json.dumps(list(value.shape)).encode())
        digest.update(np.ascontiguousarray(value, dtype='<f8').tobytes())
    return digest.hexdigest()


def prepared_input(data, credit, *, scene_id, cache_file_sha, selection_sha, model_sha):
    """Pack only observation arrays and allow-listed attribution/provenance.

    The inference NPZ deliberately excludes reference spectra and all scene
    geometry/source directions. Verify the actual bytes with the same strict,
    non-pickle loader used by native inference before returning the payload.
    """
    provenance = {'schema': 'adeps-plus-prepared-observation/1', 'scene_id': scene_id,
        'scene_index': 0, 'split': 'test', 'source_cache_file_sha256': cache_file_sha,
        'selection_file_sha256': selection_sha, 'model_weights_sha256': model_sha,
        'reference_coefficients_included': False, 'true_source_directions_included': False,
        'observation_kind': 'Fixed synthetic microphone STFT, matched order 5, known 50 dB SNR.'}
    output = io.BytesIO()
    np.savez_compressed(output, p_real=data['p'].real, p_imag=data['p'].imag,
        V_real=data['V'].real, V_imag=data['V'].imag, frequencies_hz=data['frequencies'],
        sample_rate_hz=16000, n_fft=512, hop=128, sh_ordering='ACN', sh_normalization='N3D',
        observation_sha256=canonical_observation_sha(data),
        attribution_json=json.dumps(credit, ensure_ascii=False, allow_nan=False),
        provenance_json=json.dumps(provenance, ensure_ascii=False, allow_nan=False))
    payload = output.getvalue()
    with tempfile.NamedTemporaryFile(suffix='.npz') as temporary:
        temporary.write(payload)
        temporary.flush()
        loaded = load_input(temporary.name)
    if any(not np.array_equal(loaded[key], data[source]) for key, source in
           [('p', 'p'), ('V', 'V'), ('frequencies', 'frequencies')]):
        raise ValueError('Prepared inference input differs from the saved physical observation.')
    digest = hashlib.sha256(payload).hexdigest()
    if loaded['observation_sha256'] != canonical_observation_sha(data) or loaded['input_file_sha256'] != digest:
        raise ValueError('Prepared observation or file-byte checksum mismatch.')
    return payload, digest


def read_example_inputs(work, report, lock_sha):
    path = work / 'cache/test/0000.npz'
    with np.load(path, allow_pickle=False) as archive:
        data = {key: archive[key].copy() for key in ('reference', 'p', 'V', 'frequencies', 'positions')}
        metadata = json.loads(str(archive['metadata_json']))
    if (metadata.get('scene_index') != 0 or metadata.get('split') != 'test'
            or metadata['id'] != report['scenes'][0]['id']):
        raise ValueError('Only preselected final test scene 0000 may be exported.')
    for key, shape in [('reference', (257, 36, 32)), ('p', (257, 6, 32)),
                       ('V', (257, 6, 36)), ('positions', (6, 3)), ('frequencies', (257,))]:
        if data[key].shape != shape or not np.all(np.isfinite(data[key])):
            raise ValueError(f'Invalid saved {key}.')
    if not np.array_equal(data['frequencies'], FREQUENCIES):
        raise ValueError('Example STFT grid differs from the benchmark.')
    input_sha = sha(path)
    arrays, cases = {}, {}
    for identifier in METHOD_IDS:
        estimate_path = work / 'final/0000' / f'{identifier}.npz'
        case = read_json(estimate_path.with_suffix('.json'))
        if (case.get('schema') != 'adeps-plus-case/1' or case['method'] != identifier
                or case['scene'] != 0 or case['scene_id'] != metadata['id']
                or case['cluster_id'] != metadata['cluster_id']
                or case['input_sha256'] != input_sha or case['estimate_sha256'] != sha(estimate_path)
                or case['selection_lock_sha256'] != lock_sha):
            raise ValueError(f'Saved example identity mismatch: {identifier}')
        if (case['metrics'] != report['scenes'][0]['metrics'][identifier]
                or case['curves'] != report['scenes'][0]['curves'][identifier]):
            raise ValueError(f'Example scores differ from the final report: {identifier}')
        with np.load(estimate_path, allow_pickle=False) as result:
            value = result['estimate'].copy()
        if value.shape != (257, 36, 32) or not np.all(np.isfinite(value)):
            raise ValueError(f'Cannot render failed/nonfinite saved example: {identifier}. Keep its benchmark failure; never substitute another scene.')
        arrays[identifier], cases[identifier] = value, case
    return data, metadata, arrays, cases, input_sha


def attribution(work, metadata):
    audio_path, scene_path = work / 'sealed-data/audio-manifest.json', work / 'sealed-data/scene-manifest.json'
    audio, scenes = read_json(audio_path), read_json(scene_path)
    if (scenes['audio_manifest_sha256'] != sha(audio_path)
            or metadata['manifest_sha256'] != sha(scene_path)):
        raise ValueError('The example audio/scene manifests differ from its saved provenance.')
    spec = next((row for row in scenes['scenes'] if row['id'] == metadata['id']), None)
    if spec is None or spec['audio_indexes'] != metadata['audio_indexes'] or spec['split'] != 'test':
        raise ValueError('Example attribution cannot be traced to its sealed scene.')
    files = [audio['files'][index] for index in spec['audio_indexes']]
    if [row['sha256'] for row in files] != metadata['source_audio_sha256'] or any(row['split'] != 'test' for row in files):
        raise ValueError('Source audio identity or split mismatch.')
    if audio['dataset'] != 'VCTK 0.92' or audio['license'] != 'CC-BY-4.0':
        raise ValueError('Unexpected dataset/license; inspect its permissions before publishing audio.')
    value = {'title': 'VCTK 0.92 — Junichi Yamagishi, Christophe Veaux, Kirsten MacDonald',
        'corpus': audio['dataset'], 'license': 'CC BY 4.0',
        'license_url': 'https://creativecommons.org/licenses/by/4.0/', 'source_url': audio['source_doi'],
        'speakers': [row['speaker'] for row in files], 'files': [row['archive_member'] for row in files],
        'source_audio_sha256': [row['sha256'] for row in files],
        'changes': 'Speech resampled from 48 kHz to 16 kHz; convolved with independently adapted ideal HARP room responses; cropped to 32 STFT frames; synthetic noisy array observations reconstructed by the nine listed methods. Listening audio uses finite Hann inversion, 256-sample trim at each edge, one common gain and optional fixed virtual-cardioid stereo decoding. Dataset authors and speakers do not endorse this project.'}
    credits = {}
    attribution_root = (work / 'sealed-data/source').resolve()
    for item in audio.get('attribution_files', []):
        # acquire_subset stores original README/license documents in source/;
        # their manifest paths are relative to that directory, unlike audio/.
        path = (attribution_root / item['path']).resolve()
        if not path.is_relative_to(attribution_root) or sha(path) != item['sha256']:
            raise ValueError('Dataset attribution/license file checksum mismatch.')
        credits[f'dataset/{Path(item["path"]).name}'] = path.read_bytes()
    return value, audio, scenes, credits


def validate_example(example):
    """Python mirror of the current PlusAudition shape/finite data contract."""
    if example.get('schema') != 'adeps-plus-example/1' or not example['scene_id']:
        raise ValueError('Invalid example schema or scene id.')
    if not np.array_equal(example['frequencies_hz'], FREQUENCIES) or len(example['estimates']) != 9:
        raise ValueError('Expected every frequency and all nine estimates.')
    if tuple(item['id'] for item in example['estimates']) != METHOD_IDS:
        raise ValueError('Example methods must remain complete and ordered.')
    all_items = [example['reference'], *example['estimates']]
    floor = all_items[0]['frequency_metrics']['magnitude_floor_absolute']
    for item in all_items:
        if not item['label_jp'] or not item['label_en']:
            raise ValueError('Every method needs JP/EN labels.')
        for band in BANDS:
            matrix = np.asarray(item['covariance'][band])
            if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
                raise ValueError('Invalid 4x4 covariance.')
        fm = item['frequency_metrics']
        if (fm['schema'] != 'adeps-test-spectral-metrics/1' or fm['channels'] != 4 or fm['frames'] != 32
                or fm['frequency_hz'] != example['frequencies_hz']
                or fm['magnitude_floor_absolute'] != floor or fm['magnitude_floor_relative'] != 1e-12):
            raise ValueError('Methods must share reference floor, frames and frequency grid.')
        for key in ('magnitude_spectrum_error_db', 'magnitude_squared_coherence'):
            values = fm[key]
            if len(values) != 257 or any(not scalar(v) or (v is not None and (v < 0 or (key.endswith('coherence') and v > 1))) for v in values):
                raise ValueError('Invalid spectral curve.')
        for key in ('reference_active_channels', 'coherence_valid_channels', 'reference_below_floor_cells', 'estimate_below_floor_cells'):
            maximum = 128 if 'floor' in key else 4
            if len(fm[key]) != 257 or any(type(v) is not int or not 0 <= v <= maximum for v in fm[key]):
                raise ValueError('Invalid spectral support counts.')
        if any(not scalar(item['metrics'][key]) for key in ('nrmse_db', 'coherence', 'si_sdr_db')):
            raise ValueError('Invalid scalar scores.')
        base64.b64decode(item['preview_wav_base64'], validate=True)
    dump(example)


def build_example(data, metadata, arrays, cases, methods, credit, input_sha, provenance):
    """Prepare presentation from saved spectra/metrics; never run an estimator."""
    foas = {'reference': real_wave_foa(data['reference']),
            **{identifier: real_wave_foa(arrays[identifier]) for identifier in METHOD_IDS}}
    waveforms = {identifier: synthesize_spectra(value, n_fft=512, hop=128)[:, 256:-256].T
                 for identifier, value in foas.items()}
    if any(a.shape != (3968, 4) or not np.all(np.isfinite(a)) for a in waveforms.values()):
        raise ValueError('All methods must use the same finite-inverse 3968-sample crop.')
    peak = max(max(float(np.max(abs(a))), float(np.max(abs(a @ PREVIEW_MATRIX.T)))) for a in waveforms.values())
    gain = .95 / peak if peak > 0 else 1.
    if not np.isfinite(gain) or gain <= 0:
        raise ValueError('Invalid shared export gain.')
    reference_spectral = frequency_metrics(foas['reference'], foas['reference'], FREQUENCIES)
    reference_metric = {'nrmse_db': None, 'coherence': coherence_summary(reference_spectral)['coherence'],
                        'si_sdr_db': None, 'status': 'exact_reference_match',
                        'nrmse_status': 'exact_match_minus_infinity', 'si_sdr_status': 'exact_scale_match_plus_infinity'}
    labels = {'reference': ('参照の合成音場', 'Reference synthetic field'),
              **{row['id']: (row['label_jp'], row['label_en']) for row in methods}}
    entries, wavs = [], {}
    for identifier, foa in foas.items():
        spectral = reference_spectral if identifier == 'reference' else deepcopy(cases[identifier]['details']['frequency_metrics'])
        if spectral['magnitude_floor_absolute'] != reference_spectral['magnitude_floor_absolute']:
            raise ValueError('Saved frequency scores do not share this example reference floor.')
        if any(spectral[key] != reference_spectral[key] for key in
               ('reference_active_channels', 'reference_below_floor_cells')):
            raise ValueError('Saved frequency scores do not share this example reference mask.')
        metric = reference_metric if identifier == 'reference' else deepcopy(cases[identifier]['metrics'])
        signal = waveforms[identifier] * gain
        filename = f'{identifier}_FOA_ACN_N3D.wav'
        preview = _preview_pcm16(16000, signal)
        wavs[f'foa/{filename}'] = wav_bytes(16000, signal)
        wavs[f'preview/{identifier}_stereo.wav'] = preview
        entries.append({'id': identifier, 'label_jp': labels[identifier][0], 'label_en': labels[identifier][1],
            'covariance': covariance(foa*gain, FREQUENCIES),
            'preview_wav_base64': base64.b64encode(preview).decode('ascii'),
            'metrics': metric, 'frequency_metrics': spectral, 'wav_filename': filename})
    example = {'schema': 'adeps-plus-example/1', 'scene_id': metadata['id'],
        'scene_index': 0, 'scene_selection': 'Fixed final-test scene 0000, chosen before inspecting method results; no best-example search.',
        'input_sha256': canonical_observation_sha(data), 'input_file_sha256': input_sha,
        'input_sha256_definition': 'Canonical SHA256 over frequency, V real, V imaginary, p real, p imaginary shapes and contiguous little-endian float64 bytes; no reference coefficients.',
        'input_file_sha256_definition': 'Original saved cache/test/0000.npz byte hash, distinct from the prepared inference NPZ file hash.',
        'frequencies_hz': FREQUENCIES.tolist(), 'microphone_positions_m': data['positions'].tolist(),
        'shared_gain': gain,
        'audio': {'sample_rate_hz': 16000, 'duration_seconds': 3968/16000, 'samples': 3968,
            'full_synthesis_samples': 4480, 'trim_each_end_samples': 256,
            'attribution': credit, 'shared_gain': gain,
            'gain_definition': '0.95 / largest absolute sample over reference and all nine methods, considering both FOA and the fixed stereo decode. One scalar for every FOA WAV, stereo preview and coefficient covariance (gain squared).',
            'peak_before_gain': peak, 'foa_channels': ['W', 'Y', 'Z', 'X'], 'sh_normalization': 'N3D',
            'preview': {'type': 'fixed virtual-cardioid pair, not HRTF binaural or speaker feeds',
                        'matrix': PREVIEW_MATRIX.tolist(), 'left_azimuth_deg': 45., 'right_azimuth_deg': -45.,
                        'formula': 's(d)=0.5 W + 0.5/sqrt(3)*(d_y Y+d_z Z+d_x X)', 'encoding': 'PCM16'},
            'inverse': 'Finite unpadded periodic-Hann weighted overlap-add; common symmetric 256-sample trim.'},
        'covariance_definition': 'Re mean_{frequency in band,time}(a a^H), ACN/N3D FOA after real DC/Nyquist projection and shared gain. Directional RMS=sqrt(max(0,Y R Y^T)), Y=[1,sqrt(3)d_y,sqrt(3)d_z,sqrt(3)d_x]. Not calibrated SPL, a room pressure map, or the stereo-cardioid response.',
        'covariance_bands_hz': {name: {'min_hz': lo, 'max_hz': hi, 'max_inclusive': name in ('broadband', 'high')}
                                for name, (lo, hi) in BANDS.items()},
        'covariance_dc_policy': 'Existing visualizer bands start at 20 Hz; DC is excluded from covariance only. Full-band benchmark and frequency curves retain DC. Means across bins are not integrated band energies.',
        'frequency_metric_definitions': {**FREQUENCY_METRIC_DEFINITIONS,
            'scope': 'One preselected scene from the completed ADEPS+ held-out benchmark; all nine methods use this same synthetic matched-order-5 reference. Individual example scores are not aggregate or real-room quality.'},
        'reference': entries[0], 'estimates': entries[1:], 'provenance': provenance,
        'scene_metadata': metadata, 'archive_url': 'models/plus-example-audio.zip',
        'official_model': False, 'paper_performance_reproduced': False}
    validate_example(example)
    return example, wavs


def export(work, destination):
    work, destination = Path(work), Path(destination)
    report_path, selection_path = work / 'benchmark.json', work / 'selection.json'
    report, selection = read_json(report_path), read_json(selection_path)
    validate_benchmark(report)
    lock_sha = verify_seal(work, report, selection)
    data, metadata, arrays, cases, input_sha = read_example_inputs(work, report, lock_sha)
    credit, audio_manifest, scene_manifest, credit_files = attribution(work, metadata)
    provenance = {'benchmark_sha256': sha(report_path), 'selection_sha256': sha(selection_path),
        'selection_lock_sha256': lock_sha, 'model_weights_sha256': selection['model_weights_sha256'],
        'source_sha256': {path: sha(ROOT / path) for path in EXPORT_SOURCES},
        'case_estimate_sha256': {key: value['estimate_sha256'] for key, value in cases.items()},
        'case_record_sha256': {key: sha(work / 'final/0000' / f'{key}.json') for key in METHOD_IDS},
        'audio_manifest_sha256': sha(work / 'sealed-data/audio-manifest.json'),
        'scene_manifest_sha256': sha(work / 'sealed-data/scene-manifest.json'),
        'saved_results_only': True, 'new_inference_or_scene_rendering': False}
    example, wavs = build_example(data, metadata, arrays, cases, report['methods'], credit, input_sha, provenance)
    input_payload, input_digest = prepared_input(data, credit, scene_id=metadata['id'],
        cache_file_sha=input_sha, selection_sha=sha(selection_path), model_sha=selection['model_weights_sha256'])
    example['inference_input_url'] = 'models/plus-example-input.npz'
    example['inference_input_file_sha256'] = input_digest
    example['inference_input_observation_sha256'] = example['input_sha256']
    # A flat, nonrecursive metadata copy avoids embedding base64 previews in ZIP.
    zip_example = deepcopy(example)
    for item in [zip_example['reference'], *zip_example['estimates']]:
        item.pop('preview_wav_base64')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as target:
        for name, payload in {**wavs, **credit_files}.items():
            target.writestr(name, payload)
        target.writestr('example.json', dump(zip_example))
        target.writestr('benchmark.json', report_path.read_bytes())
        target.writestr('selection.json', selection_path.read_bytes())
        target.writestr('selection-lock.json', (work / 'selection-lock.json').read_bytes())
        target.writestr('plus-example-input.npz', input_payload)
        target.writestr('dataset/audio-manifest.json', dump(audio_manifest))
        target.writestr('dataset/scene-manifest.json', dump(scene_manifest))
        for identifier, value in cases.items():
            target.writestr(f'records/{identifier}.json', dump(value))
        target.writestr('README.txt',
            'ADEPS+ independent reconstruction comparison: fixed held-out scene 0000.\n'
            '10 aligned FOA files: reference plus all 9 methods, FLOAT32 ACN/N3D W,Y,Z,X, 16 kHz / 3968 samples.\n'
            '10 PCM16 stereo previews: fixed virtual-cardioid pair, not HRTF binaural.\n'
            'All files share one gain; keep the same decoder/playback level when comparing.\n'
            'Covariance uses that same gain squared; saved frequency/scalar metrics remain before gain.\n'
            'plus-example-input.npz reproduces this exact microphone observation through infer_plus.py.\n'
            'The inference input contains no reference coefficients or true source directions; those remain separate evaluation/presentation records.\n'
            'Derived VCTK 0.92 audio, CC BY 4.0; authors/files/changes/license are in example.json and dataset/.\n'
            'No original FLAC corpus, neural weights or HARP source code are included.\n'
            'One saved example does not establish superiority over the original paper or real-room accuracy.\n')
    payloads = {'plus-benchmark.json': report_path.read_bytes(), 'plus-selection.json': selection_path.read_bytes(),
                'plus-example.json': dump(example), 'plus-example-audio.zip': archive.getvalue(),
                'plus-example-input.npz': input_payload}
    # All validation and serialization precede publication; never leave dummy
    # or partially computed result content at the public paths.
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (destination / f'.{name}.tmp').write_bytes(payload)
    for name in payloads:
        (destination / f'.{name}.tmp').replace(destination / name)
    return {'schema': 'adeps-plus-publication/1', 'scene_id': metadata['id'],
            'input_sha256': example['input_sha256'], 'methods': list(METHOD_IDS), 'shared_gain': example['shared_gain'],
            'artifacts': {name: {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
                          for name, payload in payloads.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT / 'work/plus-v1')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'public/models')
    args = parser.parse_args()
    try:
        print(json.dumps(export(args.work_dir, args.output_dir), indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f'ADEPS+ export error: {error}\n')
