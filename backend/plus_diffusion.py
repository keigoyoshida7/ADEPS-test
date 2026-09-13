"""Independent warm-start, plug-and-play Ambisonics continuation experiment.

Alternates the FROZEN full-size denoiser with physical complex data consistency.
This is NOT ADEPS Algorithm 1, reverse-diffusion ODE integration, an exact
posterior sampler, or online learning. The decreasing denoiser noise parameter
is a continuation control, not a measurement-noise estimate.

Conceptual source: DiffPIR, Eq. (12), https://arxiv.org/html/2305.08995 . Our
nonlinear H compression, fixed observation scale, relaxation and no-renoising
loop are independent choices; they do not reproduce its DDPM/HQS derivation.
The learned prior and H originate from our documented ADEPS-derived experiment:
https://arxiv.org/html/2608.24558v3 . No reference is accepted by this estimator.
"""
from __future__ import annotations

import time

import numpy as np

from capture import encode
from neural import compress, expand
from plus_reconstruction import proximal_correction


def _denoise_no_grad(prior, x, sigma):
    """Native 72-real packing, without allocating a VJP/autograd graph."""
    import torch

    if prior.network.training:
        raise ValueError('The frozen prior must be in evaluation mode.')
    packed = np.concatenate([x.real.transpose(1, 0, 2),
                             x.imag.transpose(1, 0, 2)], axis=0)
    if np.max(np.abs(packed)) > np.finfo(np.float32).max:
        raise ValueError('Compressed coefficients exceed the prior float32 range.')
    with torch.no_grad():
        tensor = torch.as_tensor(packed[None], dtype=torch.float32, device=prior.device)
        value = prior.network(tensor, torch.tensor([sigma], dtype=torch.float32, device=prior.device))
        expected = (1, 72, x.shape[0], x.shape[2])
        if tuple(value.shape) != expected:
            raise ValueError('The frozen prior returned an incompatible tensor shape.')
        packed_clean = value.detach().cpu().numpy()[0]
    return (packed_clean[:36] + 1j * packed_clean[36:]).transpose(1, 0, 2).astype(np.complex128)


def _positive(value, name, *, zero=False):
    if isinstance(value, (bool, complex)) or not np.isscalar(value):
        raise ValueError(f'{name} must be a real scalar.')
    value = float(value)
    if not np.isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(f'{name} must be finite and {"nonnegative" if zero else "positive"}.')
    return value


def refine(p, v, frequencies, prior, initial=None, *, steps=16,
           sigma_start=1., sigma_min=.002, rho=10., relaxation=.5,
           regularization=.001, ridge_relative=.001, noise_variance=0.,
           prior_variance=1., scale_mode='linear_w', initial_noise_scale=0.,
           seed=42, real_endpoints=True, progress=None, snapshot=None):
    """Return physical ``estimate``, fixed scale, trace and actual NFE count.

    p=[F,Q,T], v=[F,Q,36], initial=[F,36,T], full trained STFT grid. Default
    initialization is Linear. Scale always comes from Linear, never ``initial``
    or a target: RMS of its W coefficient by default, or all 36 coefficients
    with explicit scale_mode='linear_all'. The same scale is kept throughout.

    x=H(a/scale)/prior.std; each stage applies D(x,sigma), inverse-H, relaxes
    toward that physical estimate, then applies proximal_correction(p,V).
    The next network input is H(a_corrected/scale)/std. There is no ODE update,
    likelihood VJP or per-stage noise injection. Optional initial noise has
    per-real-component SD sigma_start*initial_noise_scale in compressed units.
    All sigma levels are positive, with no denoiser call at zero. A final raw
    proximal pass is explicit and adds no network evaluation.

    noise_variance and prior_variance use the ORIGINAL physical input units,
    regardless of the internal normalization. See proximal_correction for the
    complex variance convention. real_endpoints projects only estimates to real
    DC/Nyquist and requires caller-supplied p/V at those bins to already be real.
    This is an explicit waveform constraint, not an inferred correction of V.
    All hyperparameters must be selected without the final test references.
    """
    try:
        p, v = np.asarray(p, np.complex128), np.asarray(v, np.complex128)
        frequencies = np.asarray(frequencies, float)
    except (TypeError, ValueError) as exc:
        raise ValueError('Expected numeric observations, array matrix and frequencies.') from exc
    cfg = prior.card['configuration']
    sample_rate, n_fft, hop = (int(cfg[name]) for name in ('sample_rate_hz', 'n_fft', 'hop'))
    if (sample_rate, n_fft, hop) != (16000, 512, 128):
        raise ValueError('This experiment expects the frozen 16 kHz / FFT512 / hop128 prior.')
    expected = np.fft.rfftfreq(n_fft, 1 / sample_rate)
    if frequencies.shape != expected.shape or not np.allclose(frequencies, expected, rtol=0, atol=1e-6):
        raise ValueError('Expected the complete trained one-sided STFT frequency grid.')
    if p.ndim != 3 or v.shape != (len(expected), p.shape[1], 36) or p.shape[0] != len(expected):
        raise ValueError('Expected p=[F,Q,T], v=[F,Q,36].')
    if not 4 <= p.shape[1] <= 64 or not 1 <= p.shape[2] <= 256:
        raise ValueError('Expected 4–64 microphones and 1–256 frames.')
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(v)):
        raise ValueError('Observations and V must be finite.')
    if not isinstance(steps, (int, np.integer)) or isinstance(steps, bool) or not 2 <= steps <= 150:
        raise ValueError('steps must be an integer between 2 and 150.')
    sigma_start = _positive(sigma_start, 'sigma_start')
    sigma_min = _positive(sigma_min, 'sigma_min')
    rho = _positive(rho, 'rho')
    if not .002 <= sigma_min <= sigma_start <= 80. or rho > 100:
        raise ValueError('Use .002 <= sigma_min <= sigma_start <= 80 and rho <= 100.')
    relaxation = _positive(relaxation, 'relaxation', zero=True)
    if relaxation > 1:
        raise ValueError('relaxation must be in [0,1].')
    regularization = _positive(regularization, 'regularization')
    if not 1e-8 <= regularization <= 10:
        raise ValueError('Linear regularization must be between 1e-8 and 10.')
    initial_noise_scale = _positive(initial_noise_scale, 'initial_noise_scale', zero=True)
    if initial_noise_scale > 10:
        raise ValueError('initial_noise_scale must be at most 10.')
    if not isinstance(seed, (int, np.integer)) or isinstance(seed, bool) or seed < 0:
        raise ValueError('seed must be a nonnegative integer.')
    if not isinstance(real_endpoints, (bool, np.bool_)):
        raise ValueError('real_endpoints must be boolean.')
    std = _positive(prior.std, 'prior.std')
    if real_endpoints and (np.any(p[[0, -1]].imag != 0) or np.any(v[[0, -1]].imag != 0)):
        raise ValueError('DC/Nyquist p and V must already be real when real_endpoints=True.')

    def finite(value, name):
        if value.shape != (len(expected), 36, p.shape[2]) or not np.all(np.isfinite(value)):
            raise ValueError(f'{name} has nonfinite values or an incompatible shape.')
        return value

    def endpoints(value):
        value = value.copy()
        if real_endpoints:
            value[[0, -1]] = value[[0, -1]].real
        return value

    linear, _, _ = encode(v, p, regularization)
    finite(linear, 'Linear estimate')
    if scale_mode not in ('linear_w', 'linear_all'):
        raise ValueError('scale_mode must be linear_w or linear_all.')
    basis = linear[:, :1] if scale_mode == 'linear_w' else linear
    scale = float(np.sqrt(np.mean(abs(basis) ** 2)))
    if not np.isfinite(scale) or scale < 1e-12:
        raise ValueError('Silent or invalid observation-derived scale; select scale_mode explicitly.')
    a = endpoints(finite(np.asarray(linear if initial is None else initial, np.complex128), 'Initial estimate'))
    parameters = dict(ridge_relative=ridge_relative, noise_variance=noise_variance,
                      prior_variance=prior_variance)
    # Validate all proximal parameters before the first expensive network call.
    _, initial_proximal = proximal_correction(a, p, v, **parameters)
    x = finite(compress(a / scale) / std, 'Initial compressed estimate')
    if initial_noise_scale:
        rng = np.random.default_rng(seed)
        x = finite(x + sigma_start * initial_noise_scale * (
            rng.normal(size=x.shape) + 1j * rng.normal(size=x.shape)), 'Initial noisy estimate')
    sigmas = np.linspace(sigma_start ** (1 / rho), sigma_min ** (1 / rho), steps) ** rho
    sigmas[0], sigmas[-1] = sigma_start, sigma_min
    trace, start = [], time.perf_counter()
    observation_norm = float(np.linalg.norm(p))
    for i, sigma in enumerate(sigmas):
        clean = finite(np.asarray(_denoise_no_grad(prior, x, float(sigma)), np.complex128), 'Denoiser output')
        z = endpoints(finite(expand(std * clean) * scale, 'Expanded denoiser output'))
        mixed = finite(a + relaxation * (z - a), 'Relaxed physical estimate')
        corrected, _ = proximal_correction(mixed, p, v, **parameters)
        corrected = endpoints(finite(corrected, 'Proximal estimate'))
        row = {'step': i + 1, 'sigma': float(sigma),
               'next_sigma': float(sigmas[i + 1]) if i + 1 < steps else None,
               'nfe': i + 1, 'denoiser_update_norm': float(np.linalg.norm(z - a)),
               'proximal_update_norm': float(np.linalg.norm(corrected - mixed)),
               'update_norm': float(np.linalg.norm(corrected - a)),
               'relative_observation_residual': float(np.linalg.norm(v @ corrected - p) / observation_norm),
               'elapsed_seconds': time.perf_counter() - start}
        if any(not np.isfinite(value) for value in row.values() if value is not None):
            raise ValueError('PnP diagnostics became nonfinite; rescale inputs.')
        trace.append(row)
        a = corrected
        if snapshot:
            snapshot({'stage': 'pnp_refinement', **row}, a.copy())
        if progress:
            progress({'stage': 'pnp_refinement', 'total': steps, **row})
        x = finite(compress(a / scale) / std, 'Next compressed estimate')
    a, final_proximal = proximal_correction(a, p, v, **parameters)
    a = endpoints(finite(a, 'Final physical estimate'))
    if snapshot:
        snapshot({'stage': 'final_proximal', 'step': steps, 'sigma': None, 'nfe': steps}, a.copy())
    return {'estimate': a, 'linear': linear, 'trace': trace, 'nfe': steps,
            'observation_rms_scale': scale, 'scale_mode': scale_mode,
            'compressed_std': std,
            'final_proximal': final_proximal, 'model': prior.card.get('model', {}),
            'configuration': {'method': 'independent_pnp_continuation', 'steps': steps,
                'sigma_start': sigma_start, 'sigma_min': sigma_min, 'rho': rho,
                'relaxation': relaxation, 'regularization': regularization,
                'scale_mode': scale_mode, 'initial_noise_scale': initial_noise_scale,
                'seed': int(seed), 'real_endpoints': bool(real_endpoints),
                'initialization': 'linear' if initial is None else 'caller_supplied',
                'proximal_parameters': {key: initial_proximal[key] for key in (
                    'ridge_relative_by_frequency', 'noise_variance_by_frequency',
                    'prior_variance_by_frequency', 'lambda_by_frequency', 'lambda_definition')},
                'final_extra_proximal_pass': True, 'reference_used': False,
                'weights_updated': False, 'exact_posterior_sampler': False}}
