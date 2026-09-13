"""Independent ADEPS+alpha physical-coefficient data-consistency experiment.

This module changes neither the frozen denoiser nor the original ADEPS sampler.
It operates AFTER inverse magnitude compression, BEFORE any WAV/export gain.
No reference/ground-truth argument is accepted. It does not guarantee improved
reconstruction quality or implement an exact diffusion posterior sampler.

The complex linear proximal solution below adapts the data subproblem in
DiffPIR, Eq. (12b): https://arxiv.org/html/2305.08995 . At zero regularization it
has DDNM's range/nullspace form, Eq. (13): https://arxiv.org/html/2212.00490 .
These papers describe image methods; applying their algebra to Ambisonics is
our independent adaptation, not their original implementation or evaluation.
"""
from __future__ import annotations

import numpy as np


def _frequency_parameter(value, frequencies, name, *, positive=False):
    raw = np.asarray(value)
    if np.iscomplexobj(raw):
        raise ValueError(f'{name} must be real.')
    try:
        array = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be numeric.') from exc
    if array.ndim == 0:
        array = np.full(frequencies, float(array))
    if array.shape != (frequencies,) or not np.all(np.isfinite(array)):
        raise ValueError(f'{name} must be a finite scalar or [F] array.')
    if np.any(array <= 0 if positive else array < 0):
        raise ValueError(f'{name} must be {"positive" if positive else "nonnegative"}.')
    return array


def _complex_cube(value, name):
    try:
        array = np.asarray(value, dtype=np.complex128)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be numeric.') from exc
    if array.ndim != 3 or min(array.shape) == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f'{name} must be a finite, nonempty three-dimensional array.')
    return array


def proximal_correction(z, p, v, *, ridge_relative=0.001,
                        noise_variance=0.0, prior_variance=1.0, rcond=1e-12):
    """Return ``(corrected, JSON-safe diagnostics)`` for a raw complex estimate.

    Shapes: z=[F,C,T], p=[F,Q,T], v=[F,Q,C]. The caller must use matching
    physical units, STFT frames, SH conventions and endpoint handling. If z is
    normalized by r, p must also be divided by r and noise_variance by r**2.
    Never pass compressed H(z), individually normalized audio, or only FOA if
    v still maps all 36 N5 coefficients. Inputs are not modified.

    For each frequency f, lambda_f = ridge_relative_f * tr(V V^H) / Q
    + noise_variance_f / prior_variance_f. The first term follows the relative
    ridge scale of the baseline encoder. The second is an explicitly supplied
    absolute ridge floor, under an isotropic local Gaussian model. Variances
    mean E[|complex value|**2], not the variance of one real component. They
    may be zero (noise only) or frequency vectors; no hidden floor or noise
    estimate is computed. Estimate/tune them on validation or declared noise,
    never the test reference. prior_variance is a tuning/local-model value,
    NOT a claimed calibrated uncertainty of the trained neural model.

        corrected = z + V^H (V V^H + lambda I)^-1 (p - V z)

    This minimizes ||p-Va||_F**2 + lambda ||a-z||_F**2. We evaluate the
    algebraically equivalent batched SVD filter s/(s**2+lambda), avoiding
    squared condition numbers in Gram solves. For lambda=0, a truncated
    Moore-Penrose inverse uses singular values > rcond*s_max. It preserves
    the retained nullspace component of z and fits the observable projection
    of p; inconsistent/rank-deficient measurements need not have zero residual.
    A positive lambda retains ALL nonzero singular modes (no rcond truncation).
    Diagnostics rank uses the declared rcond for both cases.
    """
    z, p, v = (_complex_cube(value, name) for value, name in
               ((z, 'z'), (p, 'p'), (v, 'v')))
    frequencies, microphones, coefficients = v.shape
    if z.shape[:2] != (frequencies, coefficients) or p.shape != (frequencies, microphones, z.shape[2]):
        raise ValueError('Expected z=[F,C,T], p=[F,Q,T], v=[F,Q,C] with shared F and T.')
    relative = _frequency_parameter(ridge_relative, frequencies, 'ridge_relative')
    noise = _frequency_parameter(noise_variance, frequencies, 'noise_variance')
    prior = _frequency_parameter(prior_variance, frequencies, 'prior_variance', positive=True)
    cutoff = _frequency_parameter(rcond, 1, 'rcond')[0]
    if cutoff >= 1:
        raise ValueError('rcond must be in [0,1).')

    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            u, singular, vh = np.linalg.svd(v, full_matrices=False)
            trace_scale = np.sum(singular ** 2, axis=1) / microphones
            absolute_noise_ridge = noise / prior
            ridge = relative * trace_scale + absolute_noise_ridge
            residual = p - v @ z
            active = singular > cutoff * singular[:, :1]
            positive_ridge = ridge > 0
            gain = np.zeros_like(singular)
            gain[positive_ridge] = (singular[positive_ridge] /
                (singular[positive_ridge] ** 2 + ridge[positive_ridge, None]))
            zero_mask = (~positive_ridge[:, None]) & active
            np.divide(1., singular, out=gain, where=zero_mask)
            correction = vh.conj().transpose(0, 2, 1) @ (
                gain[:, :, None] * (u.conj().transpose(0, 2, 1) @ residual))
            corrected = z + correction
            after = p - v @ corrected
            before_norm = np.linalg.norm(residual, axis=(1, 2))
            after_norm = np.linalg.norm(after, axis=(1, 2))
            observation_norm = np.linalg.norm(p, axis=(1, 2))
            correction_norm = np.linalg.norm(correction, axis=(1, 2))
    except (FloatingPointError, np.linalg.LinAlgError) as exc:
        raise ValueError('Numerical range or SVD failure; rescale finite physical inputs.') from exc
    if not all(np.all(np.isfinite(array)) for array in
               (corrected, ridge, before_norm, after_norm, correction_norm, observation_norm)):
        raise ValueError('Correction produced nonfinite values; rescale physical inputs.')

    def relative_norm(values):
        with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
            ratios = np.divide(values, observation_norm,
                out=np.full_like(values, np.nan), where=observation_norm > 0)
        return [float(ratio) if np.isfinite(ratio) else None for ratio in ratios]

    diagnostics = {
        'method': 'physical_complex_soft_proximal_correction',
        'domain': 'uncompressed complex coefficients, before export gain',
        'shape': {'frequencies': frequencies, 'microphones': microphones,
                  'coefficients': coefficients, 'frames': z.shape[2]},
        'lambda_by_frequency': ridge.tolist(),
        'ridge_relative_by_frequency': relative.tolist(),
        'trace_vvh_over_q_by_frequency': trace_scale.tolist(),
        'noise_variance_by_frequency': noise.tolist(),
        'prior_variance_by_frequency': prior.tolist(),
        'absolute_noise_ridge_by_frequency': absolute_noise_ridge.tolist(),
        'lambda_definition': 'ridge_relative * trace(V V^H) / Q + noise_variance / prior_variance',
        'variance_definition': 'E[abs(complex value)^2]; same input scale, not per-real-component variance',
        'svd_rcond': float(cutoff),
        'rank_by_frequency': np.sum(active, axis=1).tolist(),
        'zero_lambda_by_frequency': (~positive_ridge).tolist(),
        'residual_norm_before_by_frequency': before_norm.tolist(),
        'residual_norm_after_by_frequency': after_norm.tolist(),
        'relative_residual_before_by_frequency': relative_norm(before_norm),
        'relative_residual_after_by_frequency': relative_norm(after_norm),
        'relative_residual_missing_definition': 'zero computed observation norm or float64 ratio overflow',
        'correction_norm_by_frequency': correction_norm.tolist(),
        'reference_used': False,
        'quality_improvement_guaranteed': False,
    }
    return corrected, diagnostics
