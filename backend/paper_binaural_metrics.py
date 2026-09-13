"""Independent KU100/ERB binaural proxy metrics, not exact ADEPS reproduction.

The original paper does not identify its HRTF measurement file, decoder design,
ERB bands, or the precise implementation of its cited auditory model. This
module fixes those choices explicitly and never modifies v0.7.0 scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DECODER = ROOT / 'public/models/paper-ku100-foa.json'
FREQUENCIES = np.fft.rfftfreq(512, 1 / 16000)
SOFA_URL = 'https://sofacoustics.org/data/database/sadie/D1_48K_24bit_256tap_FIR_SOFA.sofa'
SOFA_SHA256 = 'e6c72a84dd947b5ef75438ab96a9c2a32ed10f033472b9c4c11a49aff00a8a31'
SOURCES = [
    {'title': 'ADEPS, Section 4 and references 9, 31, 32', 'url': 'https://arxiv.org/html/2608.24558v3#S4'},
    {'title': 'McCormack et al. (2022), Eqs. 32–36: binaural covariance, physical ILD and signed zero-lag IC',
     'url': 'https://doi.org/10.1109/TASLP.2022.3182857'},
    {'title': 'Faller and Merimaa (2004): auditory-model interaural coherence',
     'url': 'https://doi.org/10.1121/1.1791872'},
    {'title': 'Merimaa (2006), Section 4.2.2, Eqs. 4.1–4.5: author account of the 2004 model',
     'url': 'https://aaltodoc.aalto.fi/bitstreams/39a10ff1-8d84-45d0-863b-81a924d264d8/download'},
    {'title': 'Glasberg and Moore (1990): auditory-filter bandwidths and ERB-rate scale',
     'url': 'https://doi.org/10.1016/0378-5955(90)90170-T'},
    {'title': 'SADIE II database, University of York', 'url': 'https://www.york.ac.uk/sadie-project/database.html'},
]


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def coefficient_sha256(matrix):
    matrix = np.asarray(matrix, np.complex128)
    digest = hashlib.sha256()
    for part in (matrix.real, matrix.imag):
        digest.update(json.dumps(list(part.shape), separators=(',', ':')).encode())
        digest.update(np.ascontiguousarray(part, dtype='<f8').tobytes())
    return digest.hexdigest()


def _frequencies(value):
    value = np.asarray(value, dtype=float)
    if value.shape != (257,) or not np.all(np.isfinite(value)) or not np.allclose(value, FREQUENCIES, atol=1e-8, rtol=0):
        raise ValueError('Expected the fixed 16 kHz / FFT512 frequency grid, 257 bins from 0 to 8000 Hz.')
    return value


def load_decoder(path=DEFAULT_DECODER):
    path = Path(path)
    record = json.loads(path.read_text(encoding='utf-8'))
    _json(record)
    if record.get('schema') != 'adeps-test-ku100-foa-decoder/1':
        raise ValueError('Unsupported KU100 decoder asset schema.')
    _frequencies(record.get('frequencies_hz'))
    matrix = np.asarray(record['real'], dtype=float) + 1j * np.asarray(record['imag'], dtype=float)
    _validate_matrix(matrix)
    if coefficient_sha256(matrix) != record.get('coefficient_sha256'):
        raise ValueError('KU100 decoder coefficient checksum mismatch.')
    if record.get('sh_ordering') != 'ACN' or record.get('sh_normalization') != 'N3D':
        raise ValueError('The decoder must use ACN/N3D.')
    metadata = {key: value for key, value in record.items() if key not in ('real', 'imag', 'frequencies_hz')}
    metadata['asset_sha256'] = _sha(path)
    return {'matrix': matrix, 'metadata': metadata}


def _validate_matrix(matrix):
    if matrix.shape != (257, 2, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError('Decoder must contain finite [257 frequencies, 2 ears, 4 FOA channels] coefficients.')
    if np.any(matrix[[0, -1]].imag != 0):
        raise ValueError('The 16 kHz renderer must have real DC and Nyquist coefficients.')


def _foa(value, name):
    value = np.asarray(value, np.complex128)
    if value.ndim != 3 or value.shape[0] != 257 or value.shape[1] < 4 or value.shape[2] != 32:
        raise ValueError(f'{name} must be [257, channels>=4, 32] complex ACN/N3D spectra.')
    if not np.all(np.isfinite(value)):
        raise ValueError(f'{name} contains nonfinite coefficients; no valid binaural score can be returned.')
    value = value[:, :4].copy()
    value[[0, -1]] = value[[0, -1]].real
    return value


def render_binaural(foa, frequencies=FREQUENCIES, *, decoder=None):
    """Apply one fixed-forward-head FOA HRTF decoder to uncompressed spectra."""
    _frequencies(frequencies)
    decoder = load_decoder() if decoder is None else decoder
    matrix = np.asarray(decoder['matrix'], np.complex128)
    _validate_matrix(matrix)
    result = np.einsum('fec,fct->fet', matrix, _foa(foa, 'FOA'), optimize=True)
    if not np.all(np.isfinite(result)):
        raise ValueError('Binaural rendering overflowed.')
    return result


def erb_bands(frequencies=FREQUENCIES, *, bands=32, low_hz=100., high_hz=8000.):
    """Non-overlapping rectangular groups equally spaced on the ERB-rate scale.

    This is spectral-bin pooling, not a gammatone or physiological filterbank.
    Every available bin with centre in [low, high] belongs to exactly one band.
    """
    frequencies = _frequencies(frequencies)
    if type(bands) is not int or not 1 <= bands <= 64:
        raise ValueError('bands must be an integer from 1 to 64.')
    if not np.isfinite([low_hz, high_hz]).all() or not 0 < low_hz < high_hz <= 8000:
        raise ValueError('Require 0 < low_hz < high_hz <= 8000.')
    rate = lambda f: 21.4 * np.log10(1 + .00437 * f)
    inverse = lambda e: (10 ** (e / 21.4) - 1) / .00437
    edges_rate = np.linspace(rate(low_hz), rate(high_hz), bands + 1)
    edges = inverse(edges_rate)
    edges[0], edges[-1] = low_hz, high_hz
    centres = inverse((edges_rate[:-1] + edges_rate[1:]) / 2)
    weights = np.array([(frequencies >= edges[b]) &
                        ((frequencies <= edges[b + 1]) if b == bands - 1 else (frequencies < edges[b + 1]))
                        for b in range(bands)], dtype=float)
    counts = weights.sum(axis=1).astype(int)
    # Empty bands remain explicitly absent; they are never interpolated.
    weights = np.divide(weights, counts[:, None], out=np.zeros_like(weights), where=counts[:, None] > 0)
    return {'weights': weights, 'center_frequencies_hz': centres, 'edges_hz': edges,
            'bin_counts': counts, 'requested_range_hz': [float(low_hz), float(high_hz)]}


def binaural_cues(binaural, frequencies=FREQUENCIES, *, band_definition=None, lag_limit_ms=1.):
    """Clip-mean physical-ear cues and a stationary cross-spectrum lag proxy.

    IC_peak = max_l Re(sum_f w_b C_LR(f) exp(i 2 pi f l/fs)) /
              sqrt(sum_f w_b C_LL(f) sum_f w_b C_RR(f)).
    l is every integer sample in [-16,+16] by default. No magnitude, squaring,
    mean subtraction, peripheral rectification or auditory compression is used.
    """
    frequencies = _frequencies(frequencies)
    value = np.asarray(binaural, np.complex128)
    if value.shape != (257, 2, 32) or not np.all(np.isfinite(value)):
        raise ValueError('Expected finite [257,2,32] binaural STFT coefficients.')
    if type(lag_limit_ms) not in (int, float) or not np.isfinite(lag_limit_ms) or not 0 <= lag_limit_ms <= 5:
        raise ValueError('lag_limit_ms must be finite, between 0 and 5 ms.')
    band_definition = erb_bands(frequencies) if band_definition is None else band_definition
    weights = np.asarray(band_definition['weights'], dtype=float)
    if weights.ndim != 2 or weights.shape[1] != 257 or not np.all(np.isfinite(weights)) or np.any(weights < 0):
        raise ValueError('Invalid nonnegative band weights.')
    # One common scale preserves every interaural cue and avoids overflow or
    # underflow from the physical signal level. It is not ear normalization.
    peak = max(float(abs(value.real).max()), float(abs(value.imag).max()))
    # NumPy complex division may first form 1/peak, which overflows for a
    # finite subnormal peak. Real divisions retain the intended unit scale.
    z = value.real / peak + 1j * (value.imag / peak) if peak > 0 else value
    powers = np.mean(abs(z) ** 2, axis=2)
    cross = np.mean(z[:, 0] * z[:, 1].conj(), axis=1)
    power = weights @ powers
    active = np.all(power > 0, axis=1)
    denominator = np.sqrt(power[:, 0]) * np.sqrt(power[:, 1])
    lag_samples = int(np.floor(lag_limit_ms * 16000 / 1000 + 1e-12))
    lags = np.arange(-lag_samples, lag_samples + 1)
    phase = np.exp(2j * np.pi * frequencies[:, None] * lags[None, :] / 16000)
    numerator = np.real((weights * cross[None, :]) @ phase)
    correlation = np.divide(numerator, denominator[:, None], out=np.full_like(numerator, np.nan), where=active[:, None])
    if np.any(abs(correlation[active]) > 1 + 1e-10):
        raise ValueError('Invalid normalized cross-correlation; Cauchy bound exceeded.')
    correlation[active] = np.clip(correlation[active], -1, 1)  # Only floating-point roundoff.
    ild = np.full(len(weights), np.nan)
    ild[active] = 10 / np.log(10) * (np.log(power[active, 0]) - np.log(power[active, 1]))
    lag_peak = np.max(correlation, axis=1)
    zero_lag = correlation[:, lag_samples]
    peak_lag = np.full(len(weights), np.nan)
    peak_lag[active] = lags[np.argmax(correlation[active], axis=1)] / 16000 * 1000
    return {'ild_db': ild, 'ic_lag_peak': lag_peak, 'ic_signed_zero_lag': zero_lag,
            'both_ears_active': active, 'relative_ear_power': power, 'peak_lag_ms': peak_lag,
            'lag_samples': lags, 'actual_lag_limit_ms': lag_samples / 16000 * 1000}


def _nullable(values):
    return [float(x) if np.isfinite(x) else None for x in np.asarray(values)]


def evaluate_binaural(estimate, reference, frequencies=FREQUENCIES, *, decoder=None,
                      bands=32, low_hz=100., high_hz=8000., lag_limit_ms=1.):
    """Return explicit, reference-common proxy MAEs; missing required bands fail.

    All estimates and the reference are truncated to FOA and use the same
    decoder. A zero estimate in a reference-active band produces null, not a
    flattering score computed after dropping the failed band.
    """
    frequencies = _frequencies(frequencies)
    decoder = load_decoder() if decoder is None else decoder
    band = erb_bands(frequencies, bands=bands, low_hz=low_hz, high_hz=high_hz)
    reference_cues = binaural_cues(render_binaural(reference, frequencies, decoder=decoder), frequencies,
                                   band_definition=band, lag_limit_ms=lag_limit_ms)
    estimate_cues = binaural_cues(render_binaural(estimate, frequencies, decoder=decoder), frequencies,
                                  band_definition=band, lag_limit_ms=lag_limit_ms)
    required = reference_cues['both_ears_active'] & (band['bin_counts'] > 0)
    valid = required & estimate_cues['both_ears_active']
    complete = bool(required.any()) and np.array_equal(required, valid)
    errors = {}
    for key in ('ild_db', 'ic_lag_peak', 'ic_signed_zero_lag'):
        error = np.abs(reference_cues[key] - estimate_cues[key])
        error[~valid] = np.nan
        errors[key] = error
    mean = lambda key: float(np.mean(errors[key][required])) if complete else None
    selected_bins = np.flatnonzero(np.any(band['weights'] > 0, axis=0))
    result = {
        'schema': 'adeps-test-binaural-proxy/1',
        'metrics': {'ild_error_db': mean('ild_db'), 'ic_error': mean('ic_lag_peak'),
                    'ic_signed_zero_lag_error': mean('ic_signed_zero_lag'),
                    'status': 'defined' if complete else 'zero_reference' if not required.any() else 'undefined_required_band'},
        'curves': {'center_frequencies_hz': band['center_frequencies_hz'].tolist(),
                   'ild_error_db': _nullable(errors['ild_db']), 'ic_error': _nullable(errors['ic_lag_peak']),
                   'ic_signed_zero_lag_error': _nullable(errors['ic_signed_zero_lag'])},
        'details': {
            'classification': 'reference-informed independent proxy; not exact ADEPS paper metric reproduction',
            'official_metric_implementation': False, 'paper_comparable_absolute_scores': False,
            'renderer': decoder.get('metadata', {'id': 'custom_decoder', 'source': 'caller supplied; not verified as KU100'}),
            'reference_and_estimate_order': 1, 'channels': ['W', 'Y', 'Z', 'X'],
            'normalization': 'N3D', 'ordering': 'ACN',
            'head_orientation': {'forward': '+X', 'left': '+Y', 'up': '+Z', 'yaw_pitch_roll_degrees': [0, 0, 0]},
            'domain': 'Uncompressed FOA STFT; real DC/Nyquist; same frequency-domain decoder; no WAV trim, output gain or head rotations.',
            'time_aggregation': 'Uniform covariance average over all 32 saved STFT frames before band cues. No 10 ms running window.',
            'band': {'kind': 'rectangular FFT-bin groups equally spaced on ERB-rate, not a gammatone filterbank',
                     'formula': 'ERB-rate(f_Hz)=21.4 log10(1+0.00437 f_Hz)',
                     'count': bands, 'requested_hz': band['requested_range_hz'],
                     'actual_bin_range_hz': [float(frequencies[selected_bins[0]]), float(frequencies[selected_bins[-1]])] if len(selected_bins) else None,
                     'edges_hz': band['edges_hz'].tolist(), 'bin_counts': band['bin_counts'].tolist(),
                     'endpoint_policy': 'Left-inclusive and right-exclusive, with the final high edge included. DC excluded. No interpolation of missing bins.',
                     'within_band_weighting': 'Equal weights for available one-sided bins; cues computed after pooling covariance. No Parseval doubling.'},
            'ild_formula': '10 log10(P_L/P_R); physical-ear level difference, positive for a louder left ear.',
            'ic_primary': 'lag_peak_stationary_cross_spectrum',
            'ic_formula': 'max_l Re(sum_f w_b(f) C_LR(f) exp(i 2pi f l/16000))/sqrt(P_L P_R), with C_LR=mean_t(L conj(R)).',
            'lag_samples': reference_cues['lag_samples'].tolist(), 'lag_limit_ms': reference_cues['actual_lag_limit_ms'],
            'ic_sensitivity_formula': 'Signed zero-lag: Re(sum_f w_b(f) C_LR(f))/sqrt(P_L P_R); not absolute value or squared coherence.',
            'ic_raw_range': [-1, 1], 'cue_error_aggregation': 'Absolute reference-estimate difference per ERB band, arithmetic mean over reference-active bands; not RMSE.',
            'reference_active_bands': required.tolist(), 'valid_bands': valid.tolist(),
            'reference_active_band_count': int(required.sum()), 'valid_band_count': int(valid.sum()),
            'undefined_policy': 'Both reference ears must have positive band power. A failed estimate in any required band makes the scalar null. No epsilon floor or method-dependent band deletion.',
            'reference_cues': {key: _nullable(reference_cues[key]) for key in ('ild_db', 'ic_lag_peak', 'ic_signed_zero_lag', 'peak_lag_ms')},
            'estimate_cues': {key: _nullable(estimate_cues[key]) for key in ('ild_db', 'ic_lag_peak', 'ic_signed_zero_lag', 'peak_lag_ms')},
            'limitations': [
                'ADEPS does not specify its exact KU100 measurement set, decoder, ERB grouping or auditory-cue implementation.',
                'The cited Faller-Merimaa model uses a gammatone auditory periphery, neural transduction and 10 ms running covariance; none is reproduced here.',
                'Signed zero-lag sensitivity follows the physical covariance form of McCormack et al. Eq.36; its RMSE evaluation differs from the MAE here.',
                'The first-order decoder truncates spatial detail equally for reference and estimates. These are not comparisons to full-order binaural ground truth.',
                'This short fixed-head synthetic clip and these proxy scores do not establish localization, listener preference or real-room perceptual quality.',
            ], 'sources': SOURCES,
        },
    }
    _json(result)
    return result


def prepare_decoder(sofa_path, output_path=DEFAULT_DECODER):
    """Rebuild the small derived asset from one checksum-pinned licensed SOFA.

    Requires h5py and SciPy only during preparation. Does not download data.
    Run: python backend/paper_binaural_metrics.py prepare --sofa PATH
    The distributed JSON is sufficient for CPU-only runtime evaluation.
    """
    import h5py
    import scipy
    from scipy.spatial import SphericalVoronoi

    sofa_path, output_path = Path(sofa_path), Path(output_path)
    if _sha(sofa_path) != SOFA_SHA256:
        raise ValueError('Source SOFA does not match the pinned SADIE II D1 measurement file.')
    decode = lambda value: value.decode('utf-8') if isinstance(value, (bytes, np.bytes_)) else str(value)
    with h5py.File(sofa_path, 'r') as source:
        if decode(source.attrs['SOFAConventions']) != 'SimpleFreeFieldHRIR':
            raise ValueError('Expected SimpleFreeFieldHRIR.')
        attributes = {key: decode(value) for key, value in source.attrs.items()}
        if 'Apache License, Version 2.0' not in attributes['License']:
            raise ValueError('Expected the original Apache-2.0 source license notice.')
        if decode(source['SourcePosition'].attrs['Type']) != 'spherical' or decode(source['SourcePosition'].attrs['Units']) != 'degree, degree, metre':
            raise ValueError('Expected spherical directions in degrees and metres.')
        if not np.array_equal(source['ListenerView'][:], [[1., 0., 0.]]) or not np.array_equal(source['ListenerUp'][:], [[0., 0., 1.]]):
            raise ValueError('Unexpected listener orientation.')
        receiver = np.asarray(source['ReceiverPosition'])[:, :, 0]
        if not np.array_equal(receiver, [[0., .09, 0.], [0., -.09, 0.]]):
            raise ValueError('Expected left then right KU100 ears.')
        sampling_rate = float(np.asarray(source['Data.SamplingRate']).item())
        if sampling_rate != 48000 or np.any(np.asarray(source['Data.Delay']) != 0):
            raise ValueError('Expected 48 kHz HRIRs with zero additional SOFA delays.')
        positions = np.asarray(source['SourcePosition'], dtype=float)
        impulses = np.asarray(source['Data.IR'], dtype=float)
    if impulses.shape != (8802, 2, 256) or not np.isfinite(impulses).all():
        raise ValueError('Unexpected SADIE II D1 response dimensions or values.')
    azimuth, elevation = np.radians(positions[:, 0]), np.radians(positions[:, 1])
    directions = np.column_stack((np.cos(elevation) * np.cos(azimuth),
                                  np.cos(elevation) * np.sin(azimuth), np.sin(elevation)))
    # Group coincident pole / azimuth-wrap measurements before Voronoi areas.
    # Averaging is direction-based and does not depend on any test signals.
    _, first, inverse = np.unique(np.round(directions, decimals=10), axis=0, return_index=True, return_inverse=True)
    unique = directions[first]
    unique /= np.linalg.norm(unique, axis=1, keepdims=True)
    pooled = np.zeros((len(unique), 2, 256), dtype=float)
    np.add.at(pooled, inverse, impulses)
    pooled /= np.bincount(inverse)[:, None, None]
    voronoi = SphericalVoronoi(unique, threshold=1e-8)
    areas = voronoi.calculate_areas()
    weights = areas / (4 * np.pi)
    if not np.all(weights > 0) or not np.isclose(weights.sum(), 1., atol=1e-10):
        raise ValueError('Invalid spherical quadrature areas.')
    y = np.column_stack((np.ones(len(unique)), np.sqrt(3) * unique[:, 1],
                         np.sqrt(3) * unique[:, 2], np.sqrt(3) * unique[:, 0]))
    gram = y.T @ (weights[:, None] * y)
    analysis = np.linalg.solve(gram, y.T * weights[None, :])
    # Least-squares projection and DTFT commute. Projecting the real HRIRs
    # first avoids storing an unnecessary 8802 x 2 x 257 complex HRTF array.
    filters = np.einsum('cd,det->ect', analysis, pooled, optimize=True)
    phase = np.exp(-2j * np.pi * FREQUENCIES[:, None] * np.arange(256)[None, :] / sampling_rate)
    matrix = np.einsum('ect,ft->fec', filters, phase, optimize=True)
    matrix[[0, -1]] = matrix[[0, -1]].real
    _validate_matrix(matrix)
    # No timestamp or local paths: repeated preparation has identical bytes
    # in the same numerical environment.
    result = {
        'schema': 'adeps-test-ku100-foa-decoder/1',
        'id': 'SADIE-II-D1-KU100-FOA-weighted-LS-16k-v1',
        'source': {'subject': 'D1 Neumann KU100', 'dataset': 'SADIE II',
                   'url': SOFA_URL, 'sha256': SOFA_SHA256, 'bytes': sofa_path.stat().st_size,
                   'dataset_url': 'https://www.york.ac.uk/sadie-project/database.html',
                   'citation_doi': 'https://doi.org/10.3390/app8112029',
                   'source_positions': 8802, 'unique_directions': len(unique), 'distance_metres': [float(positions[:, 2].min()), float(positions[:, 2].max())],
                   'hrir_sampling_rate_hz': sampling_rate, 'hrir_samples': 256,
                   'additional_sofa_delays_samples': [0, 0],
                   'comment': attributes['Comment'], 'history': attributes['History'],
                   'date_created': attributes['DateCreated'], 'date_modified': attributes['DateModified']},
        'license': {'spdx': 'Apache-2.0', 'copyright': 'Copyright 2018, University of York',
                    'url': 'https://www.apache.org/licenses/LICENSE-2.0',
                    'original_notice': attributes['License'],
                    'distributed_license': 'models/paper-ku100-LICENSE.txt',
                    'distributed_notice': 'models/paper-ku100-NOTICE.txt'},
        'sh_order': 1, 'sh_ordering': 'ACN', 'sh_normalization': 'N3D',
        'sh_basis': '[1, sqrt(3)*y, sqrt(3)*z, sqrt(3)*x]',
        'ears': ['left (+Y)', 'right (-Y)'],
        'listener_forward': [1, 0, 0], 'listener_up': [0, 0, 1],
        'sample_rate_hz': 16000, 'n_fft': 512, 'frequencies_hz': FREQUENCIES.tolist(),
        'preparation': {
            'method': 'Independent complex least-squares first-order HRTF fit; not magnitude least squares or a confirmed ADEPS renderer.',
            'formula': 'D_e(f) = H_e(f)^T W Y (Y^T W Y)^-1; B_e(f,t)=D_e(f) a_FOA(f,t).',
            'quadrature': 'Unit-sphere Voronoi cell areas divided by 4pi, coincident direction responses averaged before fitting.',
            'quadrature_area_sum': float(areas.sum()), 'gram_condition_number': float(np.linalg.cond(gram)),
            'projector_identity_max_error': float(np.max(abs(analysis @ y - np.eye(4)))),
            'frequency_conversion': 'DTFT of projected 256-tap 48 kHz HRIR at 0:31.25:8000 Hz; no interpolation or resampling. Force DC and 16 kHz Nyquist decoder coefficients real.',
            'changes': 'Spherical-area-weighted projection to first-order real ACN/N3D; evaluate the decoder at the 16 kHz FFT512 grid; discard imaginary parts at its real-waveform endpoints. Original HRTFs already have low-frequency extension, diffuse-field EQ and windowing.',
            'rebuild_command': 'python backend/paper_binaural_metrics.py prepare --sofa D1_48K_24bit_256tap_FIR_SOFA.sofa --output public/models/paper-ku100-foa.json',
            'dependencies': {'numpy': np.__version__, 'scipy': scipy.__version__, 'h5py': h5py.__version__},
            'no_test_data_or_scores_used': True,
        },
        'coefficient_sha256': coefficient_sha256(matrix),
        'real': matrix.real.tolist(), 'imag': matrix.imag.tolist(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json(result) + '\n', encoding='utf-8')
    return {'path': str(output_path), 'sha256': _sha(output_path), 'bytes': output_path.stat().st_size,
            'source_sha256': SOFA_SHA256, 'unique_directions': len(unique), 'coefficient_sha256': result['coefficient_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='Build the compact licensed decoder from the pinned local SOFA file; no downloads.')
    prepare.add_argument('--sofa', type=Path, required=True)
    prepare.add_argument('--output', type=Path, default=DEFAULT_DECODER)
    args = parser.parse_args()
    print(json.dumps(prepare_decoder(args.sofa, args.output), indent=2))
