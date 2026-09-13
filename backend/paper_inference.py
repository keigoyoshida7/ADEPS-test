"""Native PyTorch-only inference for the full-size prior; never browser bundled.

Uses the existing analytical complex physical-model gradients and an exact
autograd VJP through the time-frequency network. The compressed training-domain
scale is included in BOTH the forward degradation and its gradient.
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

from capture import encode
from neural import compress, expand, radial_vjp, schedule
from paper_prior import PaperDenoiser


class PaperPrior:
    def __init__(self, directory, device='auto'):
        directory = Path(directory)
        self.card = json.loads((directory / 'report.json').read_text())
        weights = directory / 'paper-prior-v1.pt'
        digest = hashlib.sha256(weights.read_bytes()).hexdigest()
        if digest != self.card['model']['weights_sha256']:
            raise ValueError('Full-size prior weight checksum mismatch')
        if self.card['schema'] != 'adeps-test-paper-prior-training/1':
            raise ValueError('Unsupported full-size model card')
        self.device = device
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
        checkpoint = torch.load(weights, map_location='cpu', weights_only=True)
        self.network = PaperDenoiser(**checkpoint['model_config'])
        self.network.load_state_dict(checkpoint['model'])
        self.network.to(self.device).eval().requires_grad_(False)
        self.std = float(self.card['configuration']['compressed_std'])
        if not np.isfinite(self.std) or self.std <= 0:
            raise ValueError('Invalid training-domain standard deviation')

    def predict(self, x, sigma):
        """x=[F,36,T] in normalized compressed coordinates; sigma in same units."""
        if x.ndim != 3 or x.shape[1] != 36:
            raise ValueError('Full-size prior requires complex [F,36,T]')
        packed = np.concatenate([x.real.transpose(1, 0, 2), x.imag.transpose(1, 0, 2)], axis=0)
        tensor = torch.tensor(packed[None], dtype=torch.float32, device=self.device, requires_grad=True)
        clean = self.network(tensor, torch.tensor([sigma], dtype=torch.float32, device=self.device))

        def unpack(value):
            a = value.detach().cpu().numpy()[0]
            return (a[:36] + 1j * a[36:]).transpose(1, 0, 2).astype(np.complex128)

        def vjp(g):
            values = np.concatenate([g.real.transpose(1, 0, 2), g.imag.transpose(1, 0, 2)], axis=0)
            gradient, = torch.autograd.grad(clean, tensor, torch.as_tensor(values[None], dtype=torch.float32, device=self.device))
            return unpack(gradient)

        return unpack(clean), vjp


def consistency(x, sigma, y, ev, prior):
    clean, vjp = prior.predict(x, sigma)
    if clean.shape != x.shape or not np.all(np.isfinite(clean)):
        raise ValueError('The denoiser returned invalid coefficients')
    physical = expand(prior.std * clean)
    encoded = ev @ physical
    residual = compress(encoded) / prior.std - y
    grad_encoded = radial_vjp(encoded, 2 * residual / prior.std)
    grad_physical = ev.conj().transpose(0, 2, 1) @ grad_encoded
    grad_clean = prior.std * radial_vjp(prior.std * clean, grad_physical, inverse=True)
    loss = float(np.sum(abs(residual) ** 2))
    gradient = vjp(grad_clean)
    if not np.isfinite(loss) or gradient.shape != x.shape or not np.all(np.isfinite(gradient)):
        raise ValueError('Observation consistency produced a nonfinite loss or gradient')
    return clean, loss, gradient


def reconstruct(p, v, frequencies, prior, *, sample_rate=16000, n_fft=512, hop=128,
                steps=150, eta_prime=50., seed=42, regularization=.001, progress=None):
    cfg = prior.card['configuration']
    expected = np.fft.rfftfreq(n_fft, 1 / sample_rate)
    if any(cfg[k] != value for k, value in [('sample_rate_hz', sample_rate), ('n_fft', n_fft), ('hop', hop)]):
        raise ValueError('The input STFT must match the trained sample rate, FFT and hop')
    if np.shape(frequencies) != expected.shape or not np.allclose(frequencies, expected, rtol=0, atol=1e-6):
        raise ValueError('Expected the complete uniform one-sided STFT grid, not logarithmic frequency samples')
    if p.ndim != 3 or v.shape != (len(expected), p.shape[1], 36) or p.shape[0] != len(expected):
        raise ValueError('Expected p=[F,Q,T], V=[F,Q,36]')
    if not 4 <= p.shape[1] <= 64 or not 1 <= p.shape[2] <= 256:
        raise ValueError('Expected 4–64 microphones and 1–256 time frames')
    if not np.isfinite(regularization) or not 1e-8 <= regularization <= 10:
        raise ValueError('Regularization must be finite and between 1e-8 and 10')
    if p.shape[2] > 256 or not np.all(np.isfinite(p)) or not np.all(np.isfinite(v)):
        raise ValueError('Nonfinite input or more than 256 STFT time frames')
    if not np.isfinite(eta_prime) or not 0 <= eta_prime <= 1000:
        raise ValueError('Invalid guidance strength')
    linear, encoder, gamma = encode(v, p, regularization)
    scale = float(np.sqrt(np.mean(abs(linear) ** 2)))
    if not np.isfinite(scale) or scale < 1e-12:
        raise ValueError('Silent or invalid observation')
    result, trace = sample(compress(linear / scale), encoder @ v, prior, steps, eta_prime, seed, progress)
    return {'linear': linear, 'neural': result * scale, 'trace': trace,
            'observation_rms_scale': scale, 'compressed_std': prior.std,
            'gamma_squared_by_frequency': gamma, 'model': prior.card['model']}


def sample(y, ev, prior, steps=150, eta_prime=50., seed=42, progress=None, snapshot=None):
    """Signature-compatible studio sampler; y is H of observation-scaled HOA.

    Transform to the trained compressed domain internally, and return expanded
    coefficients in the caller's original observation-normalized units.
    """
    if not np.isfinite(prior.std) or prior.std <= 0:
        raise ValueError('Invalid training-domain standard deviation')
    if not np.isfinite(eta_prime) or not 0 <= eta_prime <= 1000:
        raise ValueError('Invalid guidance strength')
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(ev)):
        raise ValueError('The observation and forward operator must be finite')
    y = y / prior.std
    denominator = float(np.linalg.norm(y))
    if not np.isfinite(denominator) or denominator < 1e-12:
        raise ValueError('Silent or invalid observation')
    sigmas = schedule(steps)
    rng = np.random.default_rng(seed)
    x = y + sigmas[0] * (rng.normal(size=y.shape) + 1j * rng.normal(size=y.shape))
    trace = []
    start = time.perf_counter()
    for i, (sigma, following) in enumerate(zip(sigmas[:-1], sigmas[1:])):
        clean, loss, gradient = consistency(x, sigma, y, ev, prior)
        norm = float(np.linalg.norm(gradient))
        if not np.isfinite(norm):
            raise ValueError('Observation gradient norm is nonfinite')
        if snapshot:
            snapshot({'stage': 'denoised_estimate', 'step': i, 'iteration': i + 1,
                      'sigma': float(sigma)}, expand(prior.std * clean).copy())
        score = (clean - x) / sigma ** 2
        guide = -eta_prime * gradient / (sigma * norm) if norm > 1e-20 else np.zeros_like(gradient)
        prior_step = -sigma * (following - sigma) * score
        guidance_step = -sigma * (following - sigma) * guide
        x = x + prior_step + guidance_step
        if not np.all(np.isfinite(x)):
            raise ValueError('Inference became nonfinite')
        row = {'step': i + 1, 'sigma': float(sigma), 'next_sigma': float(following),
               'encoded_residual': float(np.sqrt(loss) / denominator),
               'loss': loss, 'gradient_norm': norm,
               'prior_update_norm': float(np.linalg.norm(prior_step)),
               'guidance_update_norm': float(np.linalg.norm(guidance_step)),
               'elapsed_seconds': time.perf_counter() - start}
        trace.append(row)
        if progress:
            progress({'stage': 'inference', **row, 'total': steps})
    result = expand(prior.std * x)
    if not np.all(np.isfinite(result)):
        raise ValueError('Expanded Ambisonics coefficients are nonfinite')
    if snapshot:
        snapshot({'stage': 'final_sample', 'step': steps, 'iteration': steps, 'sigma': 0.}, result.copy())
    return result, trace
