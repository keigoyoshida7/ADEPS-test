"""Independent spatial-prior / frozen-denoiser / physical-consistency hybrid.

The initialization is the observation-only analytic estimator in plus_spatial.
This loop is deterministic and injects no diffusion noise. Its descending
sigma is a denoiser continuation parameter, not an estimate of sensor noise.
It is not ADEPS Algorithm 1, its ODE, an exact posterior sampler, or COMPASS.
Neither references nor true source directions are accepted. Existing ADEPS,
PnP, training data, and trained weights are left unchanged.
"""
from __future__ import annotations

import time

import numpy as np

from capture import encode
from neural import compress, expand
from plus_consistency import project_stft, reconstruct as joint_consistency
from plus_diffusion import _denoise_no_grad
from plus_reconstruction import proximal_correction
from plus_spatial import reconstruct_spatial


SPATIAL_DEFAULTS = {
    'direction_count': 256, 'max_sources': 2, 'diffuse_weight': .25,
    'regularization': 1e-6, 'analysis_low_hz': 300., 'analysis_high_hz': 2000.,
    'whitening_loading': .001, 'minimum_separation_deg': 35.,
    'covariance_fit_loading': 1e-6, 'noise_snr_db': 50., 'noise_real_endpoints': True,
}


def _scalar(value, name, lo, hi):
    if isinstance(value, (bool, complex)) or not np.isscalar(value):
        raise ValueError(f'{name} must be a real scalar.')
    value = float(value)
    if not np.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f'{name} must be finite and in [{lo}, {hi}].')
    return value


def _integer(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not lo <= value <= hi:
        raise ValueError(f'{name} must be an integer in [{lo}, {hi}].')
    return int(value)


def reconstruct(p, v, frequencies, prior, *, steps=8, sigma_start=1., relaxation=.25,
                use_stft_consistency=False, stft_iterations=0, spatial_config=None,
                ridge_relative=1e-7):
    """Return physical [F,36,T] hybrid, Linear and untouched spatial estimates.

    Scale is fixed once from the W-channel RMS of Linear with relative ridge
    1e-7, independent of the evolving estimate and of ridge_relative (which
    controls the proximal corrections). Each stage performs:
      D(H(a/scale)/std, sigma) -> scale H^-1(std D) -> relaxation
      -> optional finite-STFT projection -> physical proximal correction.

    DC and Nyquist of p/V must already be real; only estimates are projected.
    sigma follows the rho=10 schedule from sigma_start to .002, without a
    zero-sigma call. With relaxation=0, all denoiser calls are skipped (NFE=0)
    while the same number of STFT/proximal stages still run. Trace sigma then
    describes the schedule only, and model_call=False records the ablation.
    Optional final joint consistency runs only when stft_iterations>0; its
    final STFT projection can increase pressure residual and is reported.

    Default spatial initialization uses synthetic SNR=50 dB as declared side
    information. Supply spatial_config={'noise_snr_db': None} when that SNR is
    unavailable. No default is an estimate of a real microphone's noise level.
    """
    try:
        p, v = np.asarray(p, np.complex128), np.asarray(v, np.complex128)
        frequencies = np.asarray(frequencies, float)
    except (TypeError, ValueError) as exc:
        raise ValueError('Expected numeric pressure, acquisition matrix and frequencies.') from exc
    cfg = prior.card['configuration']
    sample_rate, n_fft, hop = (cfg[name] for name in ('sample_rate_hz', 'n_fft', 'hop'))
    if (sample_rate, n_fft, hop) != (16000, 512, 128):
        raise ValueError('This hybrid requires the frozen 16 kHz / FFT512 / hop128 prior.')
    expected = np.fft.rfftfreq(n_fft, 1 / sample_rate)
    if frequencies.shape != expected.shape or not np.allclose(frequencies, expected, rtol=0, atol=1e-6):
        raise ValueError('Expected the complete trained one-sided STFT frequency grid.')
    if p.ndim != 3 or p.shape[0] != len(expected) or v.shape != (len(expected), p.shape[1], 36):
        raise ValueError('Require p=[257,Q,T] and V=[257,Q,36].')
    if not 4 <= p.shape[1] <= 64 or not 1 <= p.shape[2] <= 256:
        raise ValueError('Require 4–64 microphones and 1–256 frames.')
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(v)):
        raise ValueError('Pressure and V must be finite.')
    if np.any(p[[0, -1]].imag != 0) or np.any(v[[0, -1]].imag != 0):
        raise ValueError('The declared real-waveform p/V must already have real DC and Nyquist.')
    steps = _integer(steps, 'steps', 2, 150)
    stft_iterations = _integer(stft_iterations, 'stft_iterations', 0, 10000)
    sigma_start = _scalar(sigma_start, 'sigma_start', .002, 80.)
    relaxation = _scalar(relaxation, 'relaxation', 0., 1.)
    ridge_relative = _scalar(ridge_relative, 'ridge_relative', 0., 10.)
    std = _scalar(prior.std, 'prior.std', np.finfo(float).tiny, np.finfo(float).max)
    if type(use_stft_consistency) is not bool:
        raise ValueError('use_stft_consistency must be a bool.')
    if spatial_config is not None and not isinstance(spatial_config, dict):
        raise ValueError('spatial_config must be None or a parameter dictionary.')
    selected_spatial = dict(SPATIAL_DEFAULTS)
    if spatial_config:
        unknown = set(spatial_config) - set(selected_spatial)
        if unknown:
            raise ValueError(f'Unknown spatial settings: {sorted(unknown)}')
        selected_spatial.update(spatial_config)
    # Convert accepted NumPy scalar settings to portable JSON scalar values.
    selected_spatial = {key: value.item() if isinstance(value, np.generic) else value
                        for key, value in selected_spatial.items()}
    shape = (len(expected), 36, p.shape[2])

    def finite(a, name):
        a = np.asarray(a, np.complex128)
        if a.shape != shape or not np.all(np.isfinite(a)):
            raise ValueError(f'{name} returned an invalid shape or nonfinite coefficients.')
        return a

    def endpoints(a):
        a = a.copy()
        a[[0, -1]] = a[[0, -1]].real
        return a

    linear = endpoints(finite(encode(v, p, 1e-7)[0], 'Tuned Linear'))
    scale = float(np.sqrt(np.mean(abs(linear[:, :1])**2)))
    if not np.isfinite(scale) or scale < 1e-12:
        raise ValueError('The observation-derived Linear W scale is silent or invalid.')
    spatial_result = reconstruct_spatial(p, v, frequencies, **selected_spatial)
    spatial = endpoints(finite(spatial_result['estimate'], 'Spatial initialization'))
    a = spatial.copy()
    # Validate and cache the same fixed SVD proximal map before the expensive
    # neural evaluations. This is the exact linear correction map, not a new fit.
    correction_map, proximal_parameters = proximal_correction(
        np.zeros((len(expected), 36, p.shape[1]), complex),
        np.broadcast_to(np.eye(p.shape[1]), (len(expected), p.shape[1], p.shape[1])),
        v, ridge_relative=ridge_relative)
    pressure_norm = float(np.linalg.norm(p))

    def residual(value):
        ratio = float(np.linalg.norm(v @ value - p) / pressure_norm)
        if not np.isfinite(ratio):
            raise ValueError('Pressure residual overflow; rescale the input.')
        return ratio

    initial_residual = residual(a)
    sigmas = np.linspace(sigma_start**.1, .002**.1, steps)**10
    sigmas[0], sigmas[-1] = sigma_start, .002
    trace, nfe, start = [], 0, time.perf_counter()
    for i, sigma in enumerate(sigmas):
        before_residual = residual(a)
        if relaxation > 0:
            x = finite(compress(a / scale) / std, 'Compressed neural input')
            clean = finite(_denoise_no_grad(prior, x, float(sigma)), 'Frozen denoiser')
            nfe += 1
            denoised = endpoints(finite(expand(std * clean) * scale, 'Expanded denoiser'))
        else:
            denoised = a
        mixed = finite(a + relaxation * (denoised - a), 'Relaxed estimate')
        mixed_residual = residual(mixed)
        projected = finite(project_stft(mixed, n_fft=n_fft, hop=hop), 'STFT projector') if use_stft_consistency else mixed
        updated = endpoints(finite(projected + correction_map @ (p - v @ projected), 'Proximal correction'))
        row = {'step': i + 1, 'sigma': float(sigma), 'next_sigma': float(sigmas[i+1]) if i+1 < steps else None,
               'nfe': nfe, 'model_call': relaxation > 0,
               'denoiser_update_norm': float(np.linalg.norm(denoised - a)),
               'relaxed_denoiser_update_norm': float(np.linalg.norm(mixed - a)),
               'stft_projection_update_norm': float(np.linalg.norm(projected - mixed)),
               'proximal_update_norm': float(np.linalg.norm(updated - projected)),
               'total_update_norm': float(np.linalg.norm(updated - a)),
               'pressure_residual_before': before_residual,
               'pressure_residual_after_relaxation': mixed_residual,
               'pressure_residual_after_stft': residual(projected),
               'pressure_residual_after_proximal': residual(updated),
               'elapsed_seconds': time.perf_counter() - start}
        if any(value is not None and not np.isfinite(value) for value in row.values()):
            raise ValueError('Hybrid diagnostics became nonfinite.')
        trace.append(row)
        a = updated
    before_final = residual(a)
    post = None
    if stft_iterations > 0:
        post = joint_consistency(p, v, frequencies, initial=a, iterations=stft_iterations,
                                 ridge_relative=ridge_relative, n_fft=n_fft, hop=hop,
                                 sample_rate=sample_rate)
        a = endpoints(finite(post['estimate'], 'Final joint consistency'))
    configuration = {'method': 'independent_spatial_frozen_denoiser_consistency_hybrid',
                     'steps': steps, 'sigma_start': sigma_start, 'sigma_min': .002, 'rho': 10.,
                     'relaxation': relaxation, 'initial_noise_scale': 0., 'deterministic': True,
                     'use_stft_consistency_each_step': use_stft_consistency,
                     'final_stft_iterations': stft_iterations,
                     'final_stft_projection': stft_iterations > 0,
                     'spatial_configuration': selected_spatial,
                     'linear_regularization': 1e-7, 'ridge_relative': ridge_relative,
                     'scale_mode': 'fixed_tuned_linear_w_rms',
                     'sample_rate_hz': sample_rate, 'n_fft': n_fft, 'hop': hop,
                     'reference_used': False, 'weights_updated': False,
                     'exact_dps': False, 'exact_posterior_sampler': False}
    diagnostics = {'schema': 'adeps-test-plus-hybrid/1', 'oracle_used': False,
                   'official_implementation': False,
                   'observation_rms_scale': scale, 'compressed_std': std,
                   'scale_definition': 'One fixed complex RMS of tuned-Linear W across frequency and time; no reference or stage-dependent scale.',
                   'spatial_only_preserved': True, 'spatial': spatial_result['diagnostics'],
                   'trained_denoiser_evaluations': nfe,
                   'learned_perturbation_enabled': relaxation > 0,
                   'learned_contribution_definition': 'Compare spatial-only and same consistency loop with relaxation=0. A hybrid/spatial difference alone also includes physical/STFT corrections and is not an isolated learned gain.',
                   'initial_spatial_pressure_residual': initial_residual,
                   'pressure_residual_before_final_consistency': before_final,
                   'final_pressure_residual': residual(a),
                   'total_change_from_spatial_norm': float(np.linalg.norm(a - spatial)),
                   'proximal_parameters': {key: proximal_parameters[key] for key in (
                       'lambda_by_frequency', 'ridge_relative_by_frequency',
                       'noise_variance_by_frequency', 'prior_variance_by_frequency', 'lambda_definition')},
                   'final_consistency': None if post is None else {key: value for key, value in post.items() if key != 'estimate'},
                   'model': prior.card.get('model', {}),
                   'limitations': ['Experimental nonlinear continuation, no posterior-sampling or quality guarantee.',
                                   'Default 50 dB SNR is synthetic side information, not a measured real-room value.',
                                   'Spatial stage models mutually uncorrelated directions plus diffuse sound; coherent echoes may violate this model.',
                                   'Finite STFT/proximal iterations do not prove simultaneous exact satisfaction of both constraints.']}
    return {'estimate': a, 'linear': linear, 'spatial': spatial, 'trace': trace, 'nfe': nfe,
            'configuration': configuration, 'diagnostics': diagnostics}
