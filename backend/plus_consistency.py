"""Untrained joint STFT/array-consistency baseline, independent of ADEPS.

A complex spectrogram is consistent when STFT(iSTFT(A)) = A. See Le Roux,
Ono and Sagayama (2008), Section 3:
https://www.jonathanleroux.org/pdf/LeRoux2008SAPA09b.pdf
Related consistency-constrained filtering, Le Roux and Vincent (2012):
https://merl.com/publications/TR2012-090

This implementation uses our finite, unpadded periodic-Hann crop and alternates
that real-linear projector with physical complex array data consistency. It is
not the cited authors' algorithm, learned inference, or a quality guarantee.
No target/reference is accepted. DC is retained, never set to zero: a crop's
DC bin can contain legitimate low-frequency content, not just a constant offset.
"""
from __future__ import annotations

import time

import numpy as np

from plus_reconstruction import proximal_correction


def _parameters(n_fft, hop):
    if any(not isinstance(v, (int, np.integer)) or isinstance(v, bool) for v in (n_fft, hop)):
        raise ValueError('FFT and hop must be integers.')
    if n_fft < 4 or n_fft % 2 or not 1 <= hop < n_fft:
        raise ValueError('Use an even FFT >=4 and 1 <= hop < FFT.')
    window = .5 - .5 * np.cos(2 * np.pi * np.arange(n_fft) / n_fft)
    return window


def _spectra(value, n_fft):
    try:
        a = np.asarray(value, np.complex128)
    except (TypeError, ValueError) as exc:
        raise ValueError('Spectra must be numeric.') from exc
    if a.ndim != 3 or min(a.shape) == 0 or a.shape[0] != n_fft // 2 + 1 or not np.all(np.isfinite(a)):
        raise ValueError('Expected finite one-sided spectra [FFT/2+1, channels, frames].')
    return a


def analyze_waveform(audio, *, n_fft=512, hop=128):
    """Real [channels,samples] -> complex [F,channels,T], no padding or trim.

    Exact scipy.signal.stft convention: periodic Hann, scaling='spectrum',
    boundary=None, padded=False, detrend=False. Length must be FFT+(T-1)*hop.
    """
    window = _parameters(n_fft, hop)
    raw = np.asarray(audio)
    if np.iscomplexobj(raw):
        raise ValueError('Waveform must be real.')
    signal = np.asarray(raw, np.float64)
    if signal.ndim != 2 or min(signal.shape) == 0 or not np.all(np.isfinite(signal)):
        raise ValueError('Expected finite real audio [channels,samples].')
    samples = signal.shape[1]
    if samples < n_fft or (samples - n_fft) % hop:
        raise ValueError('Finite crop length must be FFT+(frames-1)*hop; no trimming is implicit.')
    frames = np.lib.stride_tricks.sliding_window_view(signal, n_fft, axis=1)[:, ::hop]
    spectra = np.fft.rfft(frames * window, n=n_fft, axis=-1) / window.sum()
    result = spectra.transpose(2, 0, 1)
    if not np.all(np.isfinite(result)):
        raise ValueError('STFT overflow; rescale the physical input.')
    return result


def synthesize_spectra(spectra, *, n_fft=512, hop=128):
    """Weighted overlap-add inverse on the complete finite unpadded crop.

    DC/Nyquist imaginary parts cannot represent a real waveform and are removed
    by irfft. No other bin is removed. The initial sample has Hann weight zero
    in every available frame, so its unobservable value is set to zero. Every
    positive overlap weight is used without an arbitrary threshold. This is
    not the boundary=True/trimmed preview-WAV inverse used elsewhere in the UI.
    """
    window = _parameters(n_fft, hop)
    a = _spectra(spectra, n_fft)
    frames = np.fft.irfft(a.transpose(1, 2, 0), n=n_fft, axis=-1) * window.sum()
    samples = n_fft + (a.shape[2] - 1) * hop
    signal = np.zeros((a.shape[1], samples), np.float64)
    denominator = np.zeros(samples, np.float64)
    for t in range(a.shape[2]):
        sl = slice(t * hop, t * hop + n_fft)
        signal[:, sl] += frames[:, t] * window
        denominator[sl] += window ** 2
    np.divide(signal, denominator, out=signal, where=denominator > 0)
    signal[:, denominator == 0] = 0.
    if not np.all(np.isfinite(signal)):
        raise ValueError('Inverse STFT overflow; rescale the physical input.')
    return signal


def project_stft(spectra, *, n_fft=512, hop=128):
    """Idempotent, real-linear projection onto this finite STFT's range.

    Orthogonality uses the complete conjugate-symmetric Fourier metric, or
    one-sided weights [1,2,...,2,1]. Do not claim orthogonality under unweighted
    one-sided Frobenius error, which is the project's separate benchmark metric.
    """
    return analyze_waveform(synthesize_spectra(spectra, n_fft=n_fft, hop=hop), n_fft=n_fft, hop=hop)


def reconstruct(p, v, frequencies=None, *, initial=None, iterations=50,
                ridge_relative=1e-7, noise_variance=0., prior_variance=1.,
                n_fft=512, hop=128, sample_rate=16000, rcond=1e-12,
                snapshot=None, progress=None):
    """Alternate a <- project_stft(a); a <- prox(a,p,V), then final project.

    p=[F,Q,T], V=[F,Q,C]; initial is physical/uncompressed [F,C,T]. With no
    initial, use zero-centered ridge encoding with these proximal parameters.
    V and p are only read. No rescaling, microphone calibration, endpoint
    rewriting of the observations, or reference-dependent operation occurs.
    The returned final estimate is STFT-consistent; its pressure residual may
    be greater than immediately before the final projection and is recorded.

    Constant V/regularization enables caching the same SVD-based physical
    correction map once. This is algebraically identical to repeatedly calling
    proximal_correction, including its lambda=0 truncated-pseudoinverse rule.
    Fixed finite iterations are not a proof that both constraints are satisfied.
    """
    _parameters(n_fft, hop)
    p = _spectra(p, n_fft)
    v = np.asarray(v, np.complex128)
    f, q, frames = p.shape
    if v.ndim != 3 or v.shape[:2] != (f, q) or v.shape[2] == 0 or not np.all(np.isfinite(v)):
        raise ValueError('Expected finite V=[F,Q,C] matching observations.')
    if not isinstance(iterations, (int, np.integer)) or isinstance(iterations, bool) or not 0 <= iterations <= 10000:
        raise ValueError('iterations must be an integer between 0 and 10000.')
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError('sample_rate must be positive and finite.')
    if frequencies is not None:
        expected = np.fft.rfftfreq(n_fft, 1 / sample_rate)
        frequencies = np.asarray(frequencies, float)
        if frequencies.shape != expected.shape or not np.allclose(frequencies, expected, rtol=0, atol=1e-6):
            raise ValueError('Expected the complete uniform one-sided STFT frequency grid.')
    parameters = dict(ridge_relative=ridge_relative, noise_variance=noise_variance,
                      prior_variance=prior_variance, rcond=rcond)
    correction_map, parameter_report = proximal_correction(
        np.zeros((f, v.shape[2], q), complex), np.broadcast_to(np.eye(q), (f, q, q)), v, **parameters)
    a = correction_map @ p if initial is None else _spectra(initial, n_fft).copy()
    if a.shape != (f, v.shape[2], frames):
        raise ValueError('Initial coefficients must match [F,C,T].')
    observation_norm = float(np.linalg.norm(p))

    def residual(value):
        norm = float(np.linalg.norm(p - v @ value))
        ratio = norm / observation_norm if observation_norm > 0 else None
        if not np.isfinite(norm) or (ratio is not None and not np.isfinite(ratio)):
            raise ValueError('Observation residual overflow; rescale inputs.')
        return norm, ratio

    initial_residual = residual(a)
    trace, start = [], time.perf_counter()
    for i in range(iterations):
        consistent = project_stft(a, n_fft=n_fft, hop=hop)
        updated = consistent + correction_map @ (p - v @ consistent)
        if not np.all(np.isfinite(updated)):
            raise ValueError('Joint consistency iteration became nonfinite.')
        _, projected_ratio = residual(consistent)
        _, updated_ratio = residual(updated)
        row = {'iteration': i + 1, 'stft_projection_change_norm': float(np.linalg.norm(consistent - a)),
               'pressure_residual_after_stft': projected_ratio,
               'pressure_residual_after_proximal': updated_ratio,
               'elapsed_seconds': time.perf_counter() - start}
        trace.append(row)
        a = updated
        if snapshot:
            snapshot({'stage': 'joint_consistency_after_proximal', **row}, a.copy())
        if progress:
            progress({'stage': 'joint_consistency', 'total': iterations, **row})
    before_final = residual(a)
    final = project_stft(a, n_fft=n_fft, hop=hop)
    final_residual = residual(final)
    return {'estimate': final, 'trace': trace, 'nfe': 0,
        'method': 'untrained_linear_joint_stft_array_consistency',
        'configuration': {'iterations': int(iterations), 'n_fft': n_fft, 'hop': hop,
            'sample_rate_hz': sample_rate, 'window': 'periodic Hann', 'scaling': 'spectrum',
            'boundary': None, 'padded': False, 'samples': n_fft + (frames - 1) * hop,
            'initialization': 'zero_centered_ridge' if initial is None else 'caller_supplied',
            'final_stft_projection': True, 'reference_used': False, 'trained_model_used': False,
            'proximal_parameters': {key: parameter_report[key] for key in (
                'lambda_by_frequency', 'ridge_relative_by_frequency', 'noise_variance_by_frequency',
                'prior_variance_by_frequency', 'lambda_definition', 'svd_rcond')}},
        'initial_pressure_residual': {'norm': initial_residual[0], 'relative': initial_residual[1]},
        'pressure_residual_before_final_projection': {'norm': before_final[0], 'relative': before_final[1]},
        'final_pressure_residual': {'norm': final_residual[0], 'relative': final_residual[1]},
        'final_consistency_relative': float(np.linalg.norm(project_stft(final, n_fft=n_fft, hop=hop) - final) /
                                             max(np.linalg.norm(final), np.finfo(float).tiny))}
