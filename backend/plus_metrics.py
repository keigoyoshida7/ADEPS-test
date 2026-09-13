"""Reference-common, JSON-safe ADEPS+ benchmark metrics; no model inference.

The benchmark uses uncompressed ACN/N3D FOA, an unweighted one-sided STFT
metric, and the finite unpadded Hann inverse with the same edge trim for every
method. None is an explicitly recorded undefined/infinite result, never zero.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from diffusion_studio import frequency_metrics, coherence_summary, FREQUENCY_METRIC_DEFINITIONS
from plus_consistency import synthesize_spectra


METRIC_KEYS = ('nrmse_db', 'non_dc_nrmse_db', 'speech_band_nrmse_db',
               'magnitude_error_db', 'coherence', 'si_sdr_db')
CURVE_KEYS = ('nrmse_db', 'magnitude_spectrum_error_db', 'magnitude_squared_coherence')
FREQUENCIES = np.fft.rfftfreq(512, 1 / 16000)
DOMAIN = {
    'sample_rate_hz': 16000, 'n_fft': 512, 'hop': 128, 'frames': 32,
    'channels': 4, 'ordering': 'ACN', 'normalization': 'N3D',
    'coefficient_domain': 'Uncompressed FOA W,Y,Z,X, real DC/Nyquist, before export gain.',
    'nmse_definition': '10 log10(sum abs(estimate-reference)^2 / sum abs(reference)^2). Each one-sided frequency bin has weight one; no Parseval doubling.',
    'scene_aggregation': 'Arithmetic mean of per-scene dB values; not pooled scene energy.',
    'full_band_hz': [0., 8000.], 'full_band_bins': 257,
    'non_dc_band_hz': [31.25, 8000.], 'non_dc_band_bins': 256,
    'speech_band_requested_hz': [100., 8000.], 'speech_band_actual_hz': [125., 8000.],
    'speech_band_bins': 253,
    'inverse': 'Periodic Hann, spectrum scaling, boundary=None, padded=False, weighted overlap-add.',
    'inverse_samples': 4480, 'trim_each_end_samples': 256, 'evaluated_audio_samples': 3968,
    'si_sdr_definition': 'Remove each channel mean after common 256-sample edge trim; project estimate onto reference per channel; arithmetic dB mean across the reference-active channels only if all required scores are finite.',
    'si_sdr_reference_mask': 'Exactly nonzero zero-mean reference energy; independent of estimate.',
    'undefined_policy': 'Null plus status: zero reference, exact match (-infinite NMSE), exact scale match (+infinite SI-SDR), zero projection (-infinite SI-SDR), or numerical failure. Never omit an estimate-failing reference-active channel.',
}


def _finite_number(value):
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)) and math.isfinite(value)


def _valid_value(key, value):
    if value is None:
        return True
    if not _finite_number(value):
        return False
    if key in ('coherence', 'magnitude_squared_coherence'):
        return 0 <= value <= 1
    if key in ('magnitude_error_db', 'magnitude_spectrum_error_db'):
        return value >= 0
    return True


def _foa(value, name):
    try:
        a = np.asarray(value, dtype=np.complex128)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} must contain numeric coefficients.') from exc
    if a.ndim != 3 or a.shape[0] != 257 or a.shape[1] < 4 or a.shape[2] != 32:
        raise ValueError(f'{name} must be [257, channels>=4, 32].')
    return a


def _log_energy(value):
    """Log squared norm without squaring the original physical scale."""
    peak = max(float(np.max(np.abs(value.real))), float(np.max(np.abs(value.imag))))
    if peak == 0:
        return None
    scaled = value / peak
    energy = float(np.sum(scaled.real ** 2 + scaled.imag ** 2))
    return 2 * math.log(peak) + math.log(energy)


def _nmse(estimate, reference):
    reference_log = _log_energy(reference)
    if reference_log is None:
        return None, 'zero_reference'
    with np.errstate(over='ignore', invalid='ignore'):
        error = estimate - reference
    if np.all(np.isfinite(error)):
        error_log = _log_energy(error)
    else:
        scale = max(float(np.max(np.abs(estimate.real))), float(np.max(np.abs(estimate.imag))),
                    float(np.max(np.abs(reference.real))), float(np.max(np.abs(reference.imag))))
        error_log = _log_energy(estimate / scale - reference / scale)
        if error_log is not None:
            error_log += 2 * math.log(scale)
    if error_log is None:
        return None, 'exact_match'
    result = 10 / math.log(10) * (error_log - reference_log)
    return (float(result), 'defined') if math.isfinite(result) else (None, 'numerical_failure')


def si_sdr_metrics(estimate, reference):
    """FOA STFT -> reference-common channel SI-SDR on the 3968-sample crop.

    No gain alignment is performed except the scale-invariant projection in
    the SI-SDR definition. The original common physical gain is unchanged.
    """
    estimated = synthesize_spectra(estimate)[:, 256:-256]
    target = synthesize_spectra(reference)[:, 256:-256]
    if estimated.shape != (4, 3968) or target.shape != estimated.shape:
        raise ValueError('Expected a common 3968-sample FOA evaluation crop.')
    # Per-channel scales cancel in SI-SDR and keep mean/projection finite.
    ref_peaks = np.max(np.abs(target), axis=1)
    est_peaks = np.max(np.abs(estimated), axis=1)
    b = np.divide(target, ref_peaks[:, None], out=np.zeros_like(target), where=ref_peaks[:, None] > 0)
    a = np.divide(estimated, est_peaks[:, None], out=np.zeros_like(estimated), where=est_peaks[:, None] > 0)
    b -= b.mean(axis=1, keepdims=True)
    a -= a.mean(axis=1, keepdims=True)
    reference_energy = np.sum(b * b, axis=1)
    active = reference_energy > 0
    values, statuses = [], []
    for channel in range(4):
        if not active[channel]:
            value, status = None, 'reference_inactive'
        elif not np.any(a[channel]):
            value, status = None, 'zero_estimate'
        else:
            projection = (np.sum(a[channel] * b[channel]) / reference_energy[channel]) * b[channel]
            target_log = _log_energy(projection)
            error_log = _log_energy(a[channel] - projection)
            if target_log is None:
                value, status = None, 'zero_projection'
            elif error_log is None:
                value, status = None, 'exact_scale_match'
            else:
                value = float(10 / math.log(10) * (target_log - error_log))
                status = 'defined' if math.isfinite(value) else 'numerical_failure'
                if status != 'defined':
                    value = None
        values.append(value)
        statuses.append(status)
    required = [values[c] for c in range(4) if active[c]]
    complete = bool(required) and all(_finite_number(v) for v in required)
    return {'si_sdr_db': float(np.mean(required)) if complete else None,
            'status': 'defined' if complete else 'zero_reference' if not required else 'undefined_required_channel',
            'by_channel_db': values, 'by_channel_status': statuses,
            'reference_active_channels': active.tolist(), 'reference_active_count': int(active.sum()),
            'finite_channel_count': sum(_finite_number(v) for v in required),
            'undefined_required_channels': [c for c in range(4) if active[c] and values[c] is None],
            'evaluated_samples': 3968, 'trim_each_end_samples': 256,
            'definition': DOMAIN['si_sdr_definition']}


def _failure(reason):
    return {'metrics': {**{key: None for key in METRIC_KEYS}, 'status': 'failure', 'reason': reason},
            'curves': {key: [None] * 257 for key in CURVE_KEYS},
            'details': {'domain': dict(DOMAIN), 'failure': reason}}


def evaluate_metrics(estimate, reference, frequencies):
    """Evaluate one method; return {metrics, curves, details}, all JSON-safe.

    Input arrays may include higher orders; only the first four channels are
    scored, after copying and taking real endpoints. Invalid shape/reference
    raises ValueError. A nonfinite estimate returns an explicit failed result.
    """
    frequencies = np.asarray(frequencies, dtype=float)
    if frequencies.shape != (257,) or not np.all(np.isfinite(frequencies)) or not np.allclose(frequencies, FREQUENCIES, rtol=0, atol=1e-6):
        raise ValueError('Expected 257 uniform frequencies, 0..8000 Hz at 31.25 Hz.')
    source, truth = _foa(estimate, 'Estimate'), _foa(reference, 'Reference')
    if not np.all(np.isfinite(truth)):
        raise ValueError('Reference coefficients must be finite; this is an invalid test input.')
    if not np.all(np.isfinite(source)):
        return _failure('nonfinite_estimate')
    a, b = source[:, :4].copy(), truth[:, :4].copy()
    a[[0, -1]] = a[[0, -1]].real
    b[[0, -1]] = b[[0, -1]].real
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            full, full_status = _nmse(a, b)
            non_dc, non_dc_status = _nmse(a[1:], b[1:])
            speech, speech_status = _nmse(a[4:], b[4:])
            frequency_errors = [_nmse(a[f], b[f]) for f in range(257)]
            spectral = frequency_metrics(a, b, frequencies)
            coherence = coherence_summary(spectral)
            magnitude = [v for v, count in zip(spectral['magnitude_spectrum_error_db'], spectral['reference_active_channels']) if count > 0]
            magnitude_scalar = float(np.mean(magnitude)) if magnitude and all(_finite_number(v) for v in magnitude) else None
            sdr = si_sdr_metrics(a, b)
    except (FloatingPointError, OverflowError, ValueError) as exc:
        return _failure(f'numerical_failure: {exc}')
    metrics = {'nrmse_db': full, 'non_dc_nrmse_db': non_dc, 'speech_band_nrmse_db': speech,
               'magnitude_error_db': magnitude_scalar, 'coherence': coherence['coherence'], 'si_sdr_db': sdr['si_sdr_db'],
               'status': full_status, 'nrmse_status': full_status, 'non_dc_nrmse_status': non_dc_status,
               'speech_band_nrmse_status': speech_status, 'coherence_status': coherence['coherence_status'],
               'si_sdr_status': sdr['status']}
    curves = {'nrmse_db': [value for value, _ in frequency_errors],
              'magnitude_spectrum_error_db': spectral['magnitude_spectrum_error_db'],
              'magnitude_squared_coherence': spectral['magnitude_squared_coherence']}
    return {'metrics': metrics, 'curves': curves,
            'details': {'domain': dict(DOMAIN), 'frequency_metrics': spectral,
                        'nrmse_frequency_status': [status for _, status in frequency_errors],
                        'coherence': coherence, 'si_sdr': sdr,
                        'spectral_definitions': dict(FREQUENCY_METRIC_DEFINITIONS),
                        'magnitude_scalar_definition': 'Equal mean across reference-active frequencies; all reference-active bins must be defined.',
                        'dc_reference_energy_fraction': _energy_fraction(b[0:1], b),
                        'dc_and_first_bin_reference_energy_fraction': _energy_fraction(b[0:2], b)}}


def _energy_fraction(part, whole):
    denominator, numerator = _log_energy(whole), _log_energy(part)
    if denominator is None:
        return None
    return float(math.exp(numerator - denominator)) if numerator is not None else 0.


def _checked_scenes(scenes, method_ids, expected_clusters, expected_scenes_per_cluster, *, need_curves):
    if not isinstance(scenes, list) or not scenes or not isinstance(method_ids, (list, tuple)) or not method_ids:
        raise ValueError('Nonempty scenes and method_ids are required.')
    if any(not isinstance(m, str) or not m for m in method_ids) or len(set(method_ids)) != len(method_ids):
        raise ValueError('Method ids must be unique nonempty strings.')
    ids, clusters = set(), {}
    for scene in scenes:
        if not isinstance(scene, dict) or not isinstance(scene.get('id'), str) or not scene['id'] or scene['id'] in ids:
            raise ValueError('Scenes must have unique nonempty ids.')
        ids.add(scene['id'])
        cluster = scene.get('cluster_id')
        if not isinstance(cluster, str) or not cluster:
            raise ValueError('Every scene must identify its speaker-pair cluster.')
        clusters.setdefault(cluster, []).append(scene)
        for method in method_ids:
            metric = scene.get('metrics', {}).get(method)
            if not isinstance(metric, dict) or any(key not in metric or not _valid_value(key, metric[key]) for key in METRIC_KEYS):
                raise ValueError('Every method/scene must contain finite-or-null scalar metrics; never drop failed cases.')
            if need_curves:
                curve = scene.get('curves', {}).get(method)
                if not isinstance(curve, dict) or any(not isinstance(curve.get(key), list) or len(curve[key]) != 257
                    or any(not _valid_value(key, v) for v in curve[key]) for key in CURVE_KEYS):
                    raise ValueError('Every method/scene needs all 257 finite-or-null curve values.')
    if expected_clusters is not None and len(clusters) != expected_clusters:
        raise ValueError(f'Expected {expected_clusters} independent speaker-pair clusters.')
    if expected_scenes_per_cluster is not None and any(len(rows) != expected_scenes_per_cluster for rows in clusters.values()):
        raise ValueError(f'Expected exactly {expected_scenes_per_cluster} scenes per cluster, including failures.')
    return clusters


def _complete_mean(values):
    if not values or not all(_finite_number(v) for v in values):
        return None
    # Divide before summing so finite representable means do not overflow.
    value = math.fsum(float(v) / len(values) for v in values)
    return value if math.isfinite(value) else None


def aggregate(scenes, method_ids, *, expected_clusters=4, expected_scenes_per_cluster=8):
    """Mean the complete common scene set; undefined values remain undefined.

    Scenes follow the UI schema: {id,cluster_id,metrics:{id:...},curves:{id:...}}.
    Defaults enforce the final 4x8 design. Pass both expectations as None for
    development aggregation. Timing/NFE remain caller-supplied runtime facts.
    """
    clusters = _checked_scenes(scenes, method_ids, expected_clusters, expected_scenes_per_cluster, need_curves=True)
    means, curves, valid_counts = {}, {}, {}
    for method in method_ids:
        means[method] = {key: _complete_mean([s['metrics'][method][key] for s in scenes]) for key in METRIC_KEYS}
        curves[method] = {key: [_complete_mean([s['curves'][method][key][f] for s in scenes]) for f in range(257)] for key in CURVE_KEYS}
        valid_counts[method] = {
            'metrics': {key: sum(_finite_number(s['metrics'][method][key]) for s in scenes) for key in METRIC_KEYS},
            'curves': {key: [sum(_finite_number(s['curves'][method][key][f]) for s in scenes) for f in range(257)] for key in CURVE_KEYS}}
    return {'means': means, 'curves': curves, 'valid_counts': valid_counts,
            'scene_count': len(scenes), 'cluster_count': len(clusters),
            'aggregation': 'Equal arithmetic mean of all scene values; any undefined member makes its aggregate undefined.'}


def paired_comparison(scenes, baseline_id, candidate_id, *, expected_clusters=4, expected_scenes_per_cluster=8):
    """Pair scene errors, then enumerate all 4^4 cluster bootstrap draws.

    A positive difference favors the candidate. Failed/nonfinite/undefined
    scene results never silently disappear. No reference/input files are read.
    """
    clusters = _checked_scenes(scenes, [baseline_id, candidate_id], expected_clusters, expected_scenes_per_cluster, need_curves=False)
    if len(clusters) != 4 or len({len(rows) for rows in clusters.values()}) != 1:
        raise ValueError('This preregistered comparison requires four equally sized speaker-pair clusters.')
    deltas = []
    cluster_deltas = []
    for cluster in sorted(clusters):
        values = []
        for scene in clusters[cluster]:
            b, a = scene['metrics'][baseline_id]['nrmse_db'], scene['metrics'][candidate_id]['nrmse_db']
            delta = float(b - a) if _finite_number(b) and _finite_number(a) else None
            if delta is not None and not math.isfinite(delta):
                delta = None
            values.append(delta)
            deltas.append(delta)
        cluster_deltas.append(_complete_mean(values))
    complete = all(_finite_number(v) for v in deltas)
    gain = _complete_mean(deltas)
    if complete:
        draws = [_complete_mean([cluster_deltas[i] for i in indices])
                 for indices in itertools.product(range(4), repeat=4)]
        scale = max(abs(v) for v in draws)
        low, high = ((float(v * scale) for v in np.quantile(np.asarray(draws) / scale, [.0125, .9875], method='linear'))
                     if scale > 0 else (0., 0.))
    else:
        low, high = None, None
    return {'baseline': baseline_id, 'candidate': candidate_id, 'mean_gain_db': gain,
            'ci_low_db': low, 'ci_high_db': high, 'wins': sum(v is not None and v > 0 for v in deltas),
            'losses': sum(v is not None and v < 0 for v in deltas), 'ties': sum(v == 0 for v in deltas),
            'invalid': sum(v is None for v in deltas), 'count': len(deltas),
            'passed': bool(complete and gain >= .5 and low > 0),
            'status': 'defined' if complete else 'undefined_scene_result',
            'confidence_level': .975, 'bootstrap_samples': 256 if complete else 0,
            'bootstrap_definition': 'All 4^4 equally probable ordered draws of four speaker-pair clusters with replacement; retain every scene per cluster; NumPy linear quantile.',
            'clusters': sorted(clusters), 'cluster_mean_gains_db': cluster_deltas,
            'scope': 'Four independent clusters give uncertain interval coverage; not paper or venue validation.'}
