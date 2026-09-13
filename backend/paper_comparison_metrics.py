"""Gen-A Eq. (5)/(6), cited by ADEPS, with explicit independent zero policies.

These functions do not reproduce undisclosed author evaluation code. They
never load models, change the sealed benchmark, reanalyse waveforms, select
frequency bands, or renormalize the supplied coefficients. The default result
retains the literal equations' undefined/infinite outcomes. A separately named
sensitivity result uses a declared common-reference amplitude floor and a
zero-estimate MSC extension; neither choice is specified by the cited papers.
"""
from __future__ import annotations

import math
from copy import deepcopy

import numpy as np


SCHEMA = 'adeps-test-paper-comparison-metrics/1'
SENSITIVITY_FLOOR_RELATIVE = 1e-6  # amplitude: 20 log10(1e-6) = -120 dB
DEFINITIONS = {
    'spectral_error_db': 'Gen-A Eq. (5): S(f) = mean_(c=1..4,t) abs(20 log10(abs(reference)/abs(estimate))).',
    'coherence': 'Gen-A Eq. (6): C(f) = (1/4) sum_c abs(sum_t conj(reference)*estimate)^2 / (sum_t abs(reference)^2 * sum_t abs(estimate)^2).',
    'frequency_aggregation': 'Arithmetic mean across every supplied frequency, including DC and Nyquist. Any undefined/infinite member makes the scalar null; no missing-bin exclusion.',
    'channel_aggregation': 'Exactly four FOA channels, equally weighted. No reference-active-channel subset and no energy-weighted pooling.',
    'scene_aggregation': 'Caller must report its scene aggregation; equal-scene complete means are recommended. This function scores one scene only.',
    'representation': 'First four supplied, uncompressed complex Ambisonics channels. Identical convention, gain and preprocessing required across methods.',
    'endpoint_policy': 'No endpoint projection inside evaluate_paper_spectra. All supplied frequencies are included. Optional real_wave_foa explicitly projects DC/Nyquist before evaluation.',
    'strict_zeros': 'Spectral: one zero magnitude gives +infinity; 0/0 is undefined. MSC: either channel time-vector with zero energy is undefined. Nonfinite quantities are represented by null plus status.',
    'sensitivity_zeros': 'Spectral magnitudes are floored by one common reference-derived level. MSC with nonzero reference and a zero estimate is assigned 0; any zero-reference channel remains undefined. No channel or frequency is omitted.',
    'sensitivity_floor': 'For this scene, one floor for all channels/time/frequencies: max(abs(reference FOA))*1e-6, or -120 dB amplitude relative to that reference peak. Applied in the log domain; it never depends on the estimate.',
    'source_specified': ['Spectral equation and channel/time averaging: Gen-A Eq. (5).',
                         'MSC equation and channel averaging: Gen-A Eq. (6).',
                         'Gen-A Table I reports metrics averaged over all frequencies.',
                         'ADEPS evaluates FOA and cites Gen-A for these two metrics.'],
    'source_unspecified': ['ADEPS evaluation STFT, exact frequency inclusion and scene aggregation.',
                           'Magnitude epsilon/floor and zero-reference/zero-estimate conventions.',
                           'DC/Nyquist treatment and any transform-domain to waveform preprocessing.'],
    'scope': 'Independent operationalization of published equations, not verified author-code equivalence or a matched paper benchmark.',
    'sources': [{'title': 'Gen-A, Section III-D, Eqs. (5) and (6), Table I',
                 'url': 'https://arxiv.org/html/2501.08047v1#S3.SS4'},
                {'title': 'ADEPS v3, Section 4',
                 'url': 'https://arxiv.org/html/2608.24558v3#S4'}],
}


def _array(value, name):
    value = np.asarray(value, dtype=np.complex128)
    if value.ndim != 3 or value.shape[0] != 257 or value.shape[1] < 4 or value.shape[2] != 32:
        raise ValueError(f'{name} must be [257, channels>=4, 32].')
    return value[:, :4]


def real_wave_foa(spectra):
    """Explicit common real-wave endpoint projection; always returns a copy."""
    result = _array(spectra, 'Spectra').copy()
    if not np.all(np.isfinite(result)):
        raise ValueError('Real-wave FOA projection requires finite coefficients.')
    result[[0, -1]] = result[[0, -1]].real
    return result


def _log_magnitude(value):
    """Log magnitude without overflow, including subnormal input components."""
    scale = np.maximum(np.abs(value.real), np.abs(value.imag))
    real = np.divide(value.real, scale, out=np.zeros_like(scale), where=scale > 0)
    imag = np.divide(value.imag, scale, out=np.zeros_like(scale), where=scale > 0)
    result = np.full(scale.shape, -np.inf)
    nonzero = scale > 0
    result[nonzero] = np.log10(scale[nonzero]) + .5 * np.log10(real[nonzero]**2 + imag[nonzero]**2)
    return result, nonzero


def _unit_time_vectors(value):
    scale = np.maximum(np.abs(value.real), np.abs(value.imag)).max(axis=2)
    real = np.divide(value.real, scale[..., None], out=np.zeros_like(value.real), where=scale[..., None] > 0)
    imag = np.divide(value.imag, scale[..., None], out=np.zeros_like(value.real), where=scale[..., None] > 0)
    unit = real + 1j * imag
    norm = np.sqrt(np.sum(unit.real**2 + unit.imag**2, axis=2))
    unit = np.divide(unit, norm[..., None], out=np.zeros_like(unit), where=norm[..., None] > 0)
    return unit, scale > 0


def _complete_mean(values):
    if any(value is None for value in values):
        return None
    return math.fsum(value / len(values) for value in values)


def _profile(magnitude, coherence_by_channel, magnitude_status, coherence_status, counts, *, sensitivity, floor_log10):
    coherent = [float(np.mean(row)) if all(value is not None for value in row) else None for row in coherence_by_channel]
    metrics = {'spectral_error_db': _complete_mean(magnitude), 'coherence': _complete_mean(coherent)}
    floor_absolute = None
    if floor_log10 is not None:
        floor_absolute = 10.**floor_log10
        if floor_absolute == 0 or not math.isfinite(floor_absolute):
            floor_absolute = None
    details = {
        'profile': 'reference_floor_zero_estimate_sensitivity' if sensitivity else 'literal_equations_strict',
        'is_author_implementation': False,
        'definitions': deepcopy(DEFINITIONS),
        'statuses': {key: 'defined' if value is not None else 'undefined_required_frequency' for key, value in metrics.items()},
        'spectral_error_status_by_frequency': magnitude_status,
        'coherence_status_by_frequency': coherence_status,
        'coherence_by_channel': coherence_by_channel,
        'counts': {**counts, 'spectral_error_finite_frequencies': sum(x is not None for x in magnitude),
                   'coherence_finite_frequencies': sum(x is not None for x in coherent),
                   'frequencies': 257, 'channels': 4, 'frames': 32},
        'floor_relative_amplitude': SENSITIVITY_FLOOR_RELATIVE if sensitivity else None,
        'floor_relative_db': -120. if sensitivity else None,
        'floor_log10_absolute_amplitude': floor_log10 if sensitivity else None,
        'floor_absolute_amplitude': floor_absolute if sensitivity else None,
        'floor_absolute_status': ('no_floor' if not sensitivity else 'no_nonzero_reference' if floor_log10 is None
                                  else 'representable' if floor_absolute is not None else 'below_float64_range_log_domain_used'),
    }
    return {'metrics': metrics, 'curves': {'spectral_error_db': magnitude, 'coherence': coherent}, 'details': details}


def evaluate_paper_spectra(estimate, reference, frequencies):
    """Return strict Eq. (5)/(6) plus a separately identified zero sensitivity.

    Inputs are [257,C>=4,32]; only FOA is considered. Frequency values may use
    another sampling rate but must be supplied in increasing order. No signal
    transform or endpoint modification is implicit. Invalid inputs raise;
    mathematically undefined and infinite outcomes are retained as JSON nulls.
    """
    a, b = _array(estimate, 'Estimate'), _array(reference, 'Reference')
    f = np.asarray(frequencies, dtype=float)
    if f.shape != (257,) or not np.all(np.isfinite(f)) or f[0] < 0 or np.any(np.diff(f) <= 0):
        raise ValueError('Expected 257 finite increasing nonnegative frequencies.')
    if not np.all(np.isfinite(b)) or not np.all(np.isfinite(a)):
        raise ValueError('Spectral metrics require finite FOA coefficients.')
    a_log, a_nonzero = _log_magnitude(a)
    b_log, b_nonzero = _log_magnitude(b)
    both_zero = (~a_nonzero & ~b_nonzero).sum(axis=(1, 2))
    one_zero = (a_nonzero != b_nonzero).sum(axis=(1, 2))
    strict_magnitude, strict_magnitude_status = [], []
    for index in range(257):
        if both_zero[index]:
            strict_magnitude.append(None); strict_magnitude_status.append('undefined_zero_over_zero')
        elif one_zero[index]:
            strict_magnitude.append(None); strict_magnitude_status.append('positive_infinity_one_zero_magnitude')
        else:
            strict_magnitude.append(float(np.mean(np.abs(20 * (b_log[index] - a_log[index])))))
            strict_magnitude_status.append('defined')

    a_unit, a_active = _unit_time_vectors(a)
    b_unit, b_active = _unit_time_vectors(b)
    channel_msc = np.clip(np.abs(np.sum(b_unit.conj() * a_unit, axis=2))**2, 0., 1.)
    strict_channels, sensitivity_channels, strict_msc_status, sensitivity_msc_status = [], [], [], []
    for index in range(257):
        strict_channels.append([float(channel_msc[index, c]) if a_active[index, c] and b_active[index, c] else None for c in range(4)])
        sensitivity_channels.append([float(channel_msc[index, c]) if b_active[index, c] else None for c in range(4)])
        if not b_active[index].all():
            strict_msc_status.append('undefined_zero_reference_channel')
            sensitivity_msc_status.append('undefined_zero_reference_channel')
        elif not a_active[index].all():
            strict_msc_status.append('undefined_zero_estimate_channel')
            sensitivity_msc_status.append('defined_zero_estimate_extension')
        else:
            strict_msc_status.append('defined'); sensitivity_msc_status.append('defined')

    floor_log10 = float(np.max(b_log)) + math.log10(SENSITIVITY_FLOOR_RELATIVE) if b_nonzero.any() else None
    if floor_log10 is None:
        sensitivity_magnitude = [None] * 257
        sensitivity_magnitude_status = ['undefined_no_reference_floor'] * 257
    else:
        sensitivity_magnitude = np.mean(np.abs(20 * (np.maximum(b_log, floor_log10) - np.maximum(a_log, floor_log10))), axis=(1, 2)).tolist()
        sensitivity_magnitude_status = ['defined_reference_floor'] * 257
    counts = {'both_zero_magnitude_cells_by_frequency': both_zero.tolist(),
              'one_zero_magnitude_cells_by_frequency': one_zero.tolist(),
              'reference_active_channels_by_frequency': b_active.sum(axis=1).tolist(),
              'estimate_active_channels_by_frequency': a_active.sum(axis=1).tolist(),
              'zero_estimate_reference_active_channels_by_frequency': (b_active & ~a_active).sum(axis=1).tolist()}
    strict = _profile(strict_magnitude, strict_channels, strict_magnitude_status, strict_msc_status, counts,
                      sensitivity=False, floor_log10=None)
    sensitivity_counts = {**counts,
                          'reference_below_floor_cells_by_frequency': (b_log < floor_log10).sum(axis=(1, 2)).tolist() if floor_log10 is not None else None,
                          'estimate_below_floor_cells_by_frequency': (a_log < floor_log10).sum(axis=(1, 2)).tolist() if floor_log10 is not None else None}
    sensitivity = _profile(sensitivity_magnitude, sensitivity_channels, sensitivity_magnitude_status, sensitivity_msc_status,
                           sensitivity_counts, sensitivity=True, floor_log10=floor_log10)
    return {'schema': SCHEMA, 'frequency_hz': f.tolist(), **strict, 'sensitivity': sensitivity}
