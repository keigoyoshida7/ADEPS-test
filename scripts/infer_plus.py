"""Recompute the independent ADEPS+ composition from a validated array STFT.

No reference, true source direction, training, or automatic download is used.
The selected frozen weights and any declared source hashes must match locally.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from infer_paper_prior import load_input

SOURCE_PATHS = (
    'scripts/infer_plus.py', 'scripts/infer_paper_prior.py',
    'backend/plus_system.py', 'backend/plus_hybrid.py', 'backend/plus_spatial.py',
    'backend/plus_consistency.py', 'backend/plus_reconstruction.py',
    'backend/plus_diffusion.py', 'backend/paper_inference.py',
    'backend/paper_prior.py', 'backend/neural.py', 'backend/capture.py',
)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def json_text(value, *, indent=None):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(',', ':') if indent is None else None, indent=indent)


def configuration_sha256(value):
    return hashlib.sha256(json_text(value).encode('utf-8')).hexdigest()


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def numeric(value, name, lo, hi):
    if type(value) not in (int, float) or not np.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'{name} must be a finite number in [{lo}, {hi}].')
    return value


def integer(value, name, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f'{name} must be an integer in [{lo}, {hi}].')


def load_selection(path):
    selection = json.loads(Path(path).read_text(encoding='utf-8'))
    json_text(selection)  # Reject NaN/Infinity in any declared metadata.
    if not isinstance(selection, dict) or selection.get('schema') != 'adeps-plus-selection/1':
        raise ValueError('Expected selection schema adeps-plus-selection/1.')
    if not valid_sha(selection.get('model_weights_sha256')):
        raise ValueError('Selection must declare a valid model_weights_sha256.')
    config = selection.get('configuration')
    required = {'steps', 'sigma_start', 'relaxation', 'use_stft_consistency',
                'stft_iterations', 'ridge_relative'}
    if not isinstance(config, dict) or not required <= config.keys() or set(config) - required - {'spatial_config'}:
        raise ValueError('Selection must contain the explicit supported hybrid configuration.')
    integer(config['steps'], 'steps', 2, 150)
    numeric(config['sigma_start'], 'sigma_start', .002, 80.)
    numeric(config['relaxation'], 'relaxation', 0., 1.)
    numeric(config['ridge_relative'], 'ridge_relative', 0., 10.)
    if type(config['use_stft_consistency']) is not bool:
        raise ValueError('use_stft_consistency must be boolean.')
    if type(config['stft_iterations']) is not int or config['stft_iterations'] != 0:
        raise ValueError('The selected system records final consistency separately; stft_iterations must be zero.')
    integer(selection.get('post_iterations'), 'post_iterations', 0, 10000)
    numeric(selection.get('post_ridge_relative'), 'post_ridge_relative', 0., 10.)
    spatial = config.get('spatial_config')
    if spatial is not None:
        from plus_hybrid import SPATIAL_DEFAULTS
        if not isinstance(spatial, dict) or set(spatial) - SPATIAL_DEFAULTS.keys():
            raise ValueError('Invalid spatial_config keys.')
        full = {**SPATIAL_DEFAULTS, **spatial}
        integer(full['direction_count'], 'direction_count', 32, 4096)
        integer(full['max_sources'], 'max_sources', 0, 2)
        for key, lo, hi in (('diffuse_weight', 0., 1.), ('regularization', 1e-8, 10.),
                            ('whitening_loading', 1e-8, 10.), ('covariance_fit_loading', 1e-10, 1.),
                            ('analysis_low_hz', np.finfo(float).tiny, 8000.),
                            ('analysis_high_hz', np.finfo(float).tiny, 8000.),
                            ('minimum_separation_deg', np.finfo(float).tiny, 180.-1e-12)):
            numeric(full[key], key, lo, hi)
        if full['analysis_low_hz'] >= full['analysis_high_hz']:
            raise ValueError('Spatial analysis band must be ordered low to high.')
        if full['noise_snr_db'] is not None:
            numeric(full['noise_snr_db'], 'noise_snr_db', -20., 120.)
        if type(full['noise_real_endpoints']) is not bool:
            raise ValueError('noise_real_endpoints must be boolean.')
    provenance = selection.get('provenance', {})
    if not isinstance(provenance, dict):
        raise ValueError('Selection provenance must be an object.')
    source_hashes = provenance.get('source_sha256', {})
    if not isinstance(source_hashes, dict):
        raise ValueError('provenance.source_sha256 must map repository paths to SHA256 strings.')
    for relative, expected in source_hashes.items():
        if not isinstance(relative, str) or not valid_sha(expected):
            raise ValueError('Invalid declared source checksum.')
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT) or not source.is_file():
            raise ValueError(f'Declared source is unavailable inside the repository: {relative}')
        if file_sha256(source) != expected:
            raise ValueError(f'Selection source checksum mismatch: {relative}')
    return selection


def validate_input(data):
    if (data['sample_rate_hz'], data['n_fft'], data['hop']) != (16000, 512, 128):
        raise ValueError('The frozen prior requires 16 kHz, n_fft=512, hop=128.')
    if data['p'].shape[2] < 2:
        raise ValueError('At least two STFT frames are required for the trimmed listening WAV.')
    if np.any(data['p'][[0, -1]].imag != 0) or np.any(data['V'][[0, -1]].imag != 0):
        raise ValueError('Real-waveform DC and Nyquist of p and V must already be real.')
    json_text(data['provenance'])


def noise_selection(selection, noise_snr=None, estimate_noise=False):
    if noise_snr is not None and estimate_noise:
        raise ValueError('Supply --noise-snr or --estimate-noise, not both.')
    selected = deepcopy(selection)
    config = selected['configuration']
    spatial = dict(config.get('spatial_config') or {})
    if noise_snr is not None:
        numeric(noise_snr, 'noise_snr', -20., 120.)
        spatial['noise_snr_db'] = float(noise_snr)
        origin = 'explicit_user_supplied_snr'
    elif estimate_noise:
        spatial['noise_snr_db'] = None
        origin = 'observation_covariance_fit'
    else:
        origin = 'selected_configuration_assumption'
    if noise_snr is not None or estimate_noise:
        config['spatial_config'] = spatial
    snr = spatial.get('noise_snr_db', 50.)
    if snr is None:
        description = ('Noise is fitted from the observed covariance together with directional and diffuse powers; '
                       'reverberation/model error can be mistaken for noise. It is not a calibrated noise measurement.')
    else:
        numeric(snr, 'selected noise_snr_db', -20., 120.)
        description = (f'Assumed SNR={snr:g} dB is supplied side information, not inferred or verified from this recording. '
                       'The released default was selected for synthetic 50 dB observations.')
    return selected, {'mode': origin, 'snr_db': snr, 'description': description,
                      'changed_from_selection': noise_snr is not None or estimate_noise,
                      'real_recording_noise_verified': False}


def run(args, *, prior_factory=None, reconstruct_fn=None):
    """Run the public CLI; injectable callables permit CPU-only contract tests."""
    data = load_input(args.input)
    validate_input(data)
    original = load_selection(args.selection)
    selected, noise = noise_selection(original, args.noise_snr, args.estimate_noise)
    source_hashes = {path: file_sha256(ROOT / path) for path in SOURCE_PATHS}
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f'Use a new output directory; this one already exists: {output}')
    checkpoint = Path(args.checkpoint)
    card = json.loads((checkpoint / 'report.json').read_text(encoding='utf-8'))
    if card.get('schema') != 'adeps-test-paper-prior-training/1':
        raise ValueError('Unsupported checkpoint report schema.')
    expected_weights = original['model_weights_sha256']
    if card.get('model', {}).get('weights_sha256') != expected_weights:
        raise ValueError('Selected weights do not match the checkpoint report.')
    if file_sha256(checkpoint / 'paper-prior-v1.pt') != expected_weights:
        raise ValueError('Selected weights do not match the actual checkpoint file.')
    print(json_text({'status': 'validated', 'observation_sha256': data['observation_sha256'],
                     'model_weights_sha256': expected_weights, 'noise_assumption': noise,
                     'denoiser_enabled': not args.no_denoiser}), flush=True)
    if prior_factory is None:
        from paper_inference import PaperPrior
        prior_factory = PaperPrior
    if reconstruct_fn is None:
        from plus_system import reconstruct
        reconstruct_fn = reconstruct
    prior = prior_factory(checkpoint, args.device)
    if prior.card.get('model', {}).get('weights_sha256') != expected_weights:
        raise ValueError('Loaded prior does not match selected weights.')
    start = time.perf_counter()
    result = reconstruct_fn(data['p'], data['V'], data['frequencies'], prior, selected,
                            denoiser=not args.no_denoiser)
    elapsed = time.perf_counter() - start
    if source_hashes != {path: file_sha256(ROOT / path) for path in SOURCE_PATHS}:
        raise ValueError('Reconstruction sources changed during this run; repeat with fixed code.')
    shape = (len(data['frequencies']), 36, data['p'].shape[2])
    estimates = {}
    for name in ('linear', 'spatial', 'estimate'):
        value = np.asarray(result[name], np.complex128)
        if value.shape != shape or not np.all(np.isfinite(value)):
            raise ValueError(f'{name} is not a finite full N5 result.')
        if np.any(value[[0, -1]].imag != 0):
            raise ValueError(f'{name} contains complex DC/Nyquist incompatible with a real WAV.')
        estimates[name] = value
    from plus_consistency import synthesize_spectra
    audio = {name: synthesize_spectra(value[:, :4], n_fft=512, hop=128)[:, 256:-256].T
             for name, value in estimates.items()}
    samples = (shape[2] - 1) * 128
    if any(value.shape != (samples, 4) or not np.all(np.isfinite(value)) for value in audio.values()):
        raise ValueError('Invalid trimmed FOA audio.')
    peak = max(float(np.max(abs(value))) for value in audio.values())
    shared_gain = .95 / peak if peak > 0 else 1.
    effective_configuration = {'hybrid': result['configuration'],
        'selected_composition': result['selection'], 'denoiser_enabled': not args.no_denoiser,
        'noise_assumption': noise}
    metadata = {key: value for key, value in result.items() if key not in estimates}
    metadata.update(schema='adeps-plus-inference-output/1',
        observation_sha256=data['observation_sha256'], input_file_sha256=data['input_file_sha256'],
        model_weights_sha256=expected_weights, selection_file_sha256=file_sha256(args.selection),
        selected_configuration=original, effective_configuration=effective_configuration,
        configuration_sha256=configuration_sha256(effective_configuration),
        source_sha256=source_hashes,
        input_provenance=data['provenance'], noise_assumption=noise,
        elapsed_seconds=elapsed, device=str(prior.device),
        sample_rate_hz=16000, n_fft=512, hop=128, frequencies_hz=data['frequencies'].tolist(),
        sh_ordering='ACN', sh_normalization='N3D', prior_order=5,
        reference_used=False, reference_quality_metrics_computed=False,
        official_model=False, paper_performance_reproduced=False,
        audio={'sample_rate_hz': 16000, 'samples': samples, 'duration_seconds': samples/16000,
            'channels': 4, 'channel_order': ['W', 'Y', 'Z', 'X'], 'normalization': 'N3D',
            'wav_subtype': '32-bit IEEE float', 'shared_gain': shared_gain,
            'peak_before_shared_gain': peak, 'gain_applied_to_npz': False,
            'gain_definition': '0.95 / max absolute FOA WAV sample over Linear, spatial, and final hybrid; same scalar for all three.',
            'trim_each_end_samples': 256,
            'full_synthesis_samples': 512 + (shape[2]-1)*128,
            'synthesis': 'Finite periodic-Hann weighted overlap-add, then trim 256 samples at each end.',
            'stft_result_domain': 'Full uncompressed N5 spectra before synthesis, trim and audio gain.'})
    json_text(metadata)  # Fail before creating a partial output directory.
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f'.{output.name}-', dir=output.parent))
    try:
        arrays = {f'{name}_{part}': getattr(value, part) for name, value in estimates.items()
                  for part in ('real', 'imag')}
        np.savez_compressed(staging / 'reconstruction.npz', **arrays,
            frequencies_hz=data['frequencies'], sample_rate_hz=16000, n_fft=512, hop=128,
            sh_ordering='ACN', sh_normalization='N3D',
            observation_sha256=data['observation_sha256'], model_weights_sha256=expected_weights,
            configuration_sha256=metadata['configuration_sha256'],
            input_provenance_json=json_text(data['provenance']), metadata_json=json_text(metadata))
        from scipy.io import wavfile
        for name, value in audio.items():
            wavfile.write(staging / f'{name}-foa.wav', 16000, (value * shared_gain).astype(np.float32))
        metadata['artifacts'] = {path.name: {'sha256': file_sha256(path), 'bytes': path.stat().st_size}
                                 for path in sorted(staging.iterdir())}
        (staging / 'summary.json').write_text(json_text(metadata, indent=2) + '\n', encoding='utf-8')
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json_text({'status': 'complete', 'output': str(output), 'nfe': result['nfe'],
                     'configuration_sha256': metadata['configuration_sha256'],
                     'elapsed_seconds': elapsed}), flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, help='Validated synchronous array STFT NPZ, not a plain WAV.')
    parser.add_argument('--selection', default=str(ROOT / 'public/models/plus-selection.json'))
    parser.add_argument('--checkpoint', default=str(ROOT / 'work/paper-prior-v1'))
    parser.add_argument('--output', required=True, help='New output directory; existing directories are never overwritten.')
    parser.add_argument('--device', choices=['auto', 'mps', 'cuda', 'cpu'], default='auto')
    parser.add_argument('--no-denoiser', action='store_true', help='Same consistency loop, no learned denoiser calls (NFE=0).')
    noise = parser.add_mutually_exclusive_group()
    noise.add_argument('--noise-snr', type=float, help='Explicit supplied SNR in dB, not an automatic measurement.')
    noise.add_argument('--estimate-noise', action='store_true', help='Fit noise jointly from observation covariance; no known SNR.')
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f'ADEPS+ input/configuration error: {exc}\n')


if __name__ == '__main__':
    main()
