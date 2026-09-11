"""Independent ADEPS equation test, not the authors' network or checkpoint.

Eqs. 5, 10, 11 and Algorithm 1 of arXiv:2608.24558v2. The small, trained
EDM MLP and all unspecified choices are documented in NEURAL_PROTOCOL.md.
Complex arrays use [frequency, ACN channel, time]; gradients are real-Euclidean.
"""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
from capture import complex_array, encode, modal_matrix, real_n3d

ORDER = 5
CHANNELS = 36
ALPHA = .67
BETA = 3.
EPS = 1e-8
MAX_BINS = 8192
SYNTHETIC_MIN_HZ = 1.
SYNTHETIC_MAX_HZ = 20_000.
SYNTHETIC_FREQUENCIES = 128
SYNTHETIC_FRAMES = 16
MODEL_DIR = Path(__file__).resolve().parents[1] / 'public' / 'models'


def compress(z):
    """H, with a continuous linear extension inside EPS (declared choice)."""
    r = np.maximum(np.abs(z), EPS)
    return BETA * r ** (ALPHA - 1) * z


def expand(z):
    threshold = BETA * EPS ** ALPHA
    r = np.maximum(np.abs(z), threshold)
    return BETA ** (-1 / ALPHA) * r ** (1 / ALPHA - 1) * z


def radial_vjp(z, upstream, inverse=False):
    """Adjoint of a radial complex map in its two real coordinates."""
    exponent = 1 / ALPHA if inverse else ALPHA
    factor = BETA ** (-1 / ALPHA) if inverse else BETA
    threshold = BETA * EPS ** ALPHA if inverse else EPS
    radius = np.abs(z)
    safe = np.maximum(radius, threshold)
    scale = factor * safe ** (exponent - 1)
    extra = (exponent - 1) * np.real(np.conj(z) * upstream) / safe ** 2
    return scale * (upstream + np.where(radius > threshold, extra, 0) * z)


def pack(z):
    v = z.transpose(0, 2, 1).reshape(-1, CHANNELS)
    return np.concatenate((v.real, v.imag), axis=1)


def unpack(v, shape):
    z = v[:, :CHANNELS] + 1j * v[:, CHANNELS:]
    return z.reshape(shape[0], shape[2], CHANNELS).transpose(0, 2, 1)


def sigmoid(x):
    # tanh is stable without overflow or hard clipping of network derivatives.
    return .5 * (1 + np.tanh(.5 * x))


class TinyDenoiser:
    """Noise-conditioned, per-bin MLP. Analytical VJP, including preconditioning."""
    def __init__(self, directory=None):
        directory = Path(directory or MODEL_DIR)
        self.card = json.loads((directory / 'tiny-spatial-v1.json').read_text())
        payload = (directory / 'tiny-spatial-v1.npz').read_bytes()
        if hashlib.sha256(payload).hexdigest() != self.card['weights_sha256']:
            raise ValueError('Model checksum mismatch')
        with np.load(directory / 'tiny-spatial-v1.npz', allow_pickle=False) as data:
            self.weights = {name: data[name].astype(np.float64) for name in data.files}
        h = int(self.card['hidden_channels'])
        shapes = {'w1': (80, h), 'b1': (h,), 'w2': (h, h), 'b2': (h,),
                  'w3': (h, 72), 'b3': (72,)}
        if set(self.weights) != set(shapes) or any(
            self.weights[k].shape != shape or not np.all(np.isfinite(self.weights[k]))
            for k, shape in shapes.items()
        ):
            raise ValueError('Unsupported denoiser architecture or invalid weights')
        self.sigma_data = float(self.card['sigma_data'])
        if not .01 <= self.sigma_data <= 100:
            raise ValueError('Invalid sigma_data')

    def predict(self, x, sigma):
        """Returns D(x,sigma) and a closure computing J_D(x)^T g."""
        w = self.weights
        sd = self.sigma_data
        cin = 1 / np.sqrt(sigma ** 2 + sd ** 2)
        cskip = sd ** 2 / (sigma ** 2 + sd ** 2)
        cout = sigma * sd * cin
        phase = np.log(sigma) / 4 * np.array([1., 2., 4., 8.])
        embedding = np.r_[np.sin(phase), np.cos(phase)]
        z = pack(x)
        inp = np.concatenate((cin * z, np.broadcast_to(embedding, (len(z), 8))), axis=1)
        a1 = inp @ w['w1'] + w['b1']; s1 = sigmoid(a1); h1 = a1 * s1
        a2 = h1 @ w['w2'] + w['b2']; s2 = sigmoid(a2); h2 = a2 * s2
        out = cskip * z + cout * (h2 @ w['w3'] + w['b3'])

        def vjp(g):
            packed = pack(g)
            delta = (cout * packed @ w['w3'].T) * (s2 + a2 * s2 * (1 - s2))
            delta = (delta @ w['w2'].T) * (s1 + a1 * s1 * (1 - s1))
            delta = delta @ w['w1'].T
            return unpack(cskip * packed + cin * delta[:, :72], x.shape)
        return unpack(out, x.shape), vjp


def consistency(x, sigma, y, EV, denoiser):
    clean, denoiser_vjp = denoiser.predict(x, sigma)
    physical = expand(clean)
    reencoded = EV @ physical
    residual = compress(reencoded) - y
    grad_reencoded = radial_vjp(reencoded, 2 * residual)
    grad_physical = EV.conj().transpose(0, 2, 1) @ grad_reencoded
    grad_clean = radial_vjp(clean, grad_physical, inverse=True)
    gradient = denoiser_vjp(grad_clean)
    return clean, float(np.sum(np.abs(residual) ** 2)), gradient


def schedule(steps, sigma_max=20., sigma_min=.002, rho=10.):
    if type(steps) is not int or not 2 <= steps <= 300:
        raise ValueError('steps must be an integer between 2 and 300')
    # M positive points + explicit terminal zero => exactly M Euler updates.
    ramp = np.linspace(0, 1, steps)
    return np.r_[(sigma_max ** (1 / rho) + ramp *
                  (sigma_min ** (1 / rho) - sigma_max ** (1 / rho))) ** rho, 0.]


def sample(y, EV, denoiser, steps=150, eta_prime=50., seed=42, progress=None):
    sigmas = schedule(steps)
    if not np.isfinite(eta_prime) or not 0 <= eta_prime <= 1000:
        raise ValueError('eta_prime must be between 0 and 1000')
    rng = np.random.default_rng(seed)
    # Each real coordinate has variance sigma_max^2, not a circular CN variance.
    x = y + sigmas[0] * (rng.normal(size=y.shape) + 1j * rng.normal(size=y.shape))
    trace = []
    denominator = float(np.linalg.norm(y))
    start = time.perf_counter()
    for i, (sigma, following) in enumerate(zip(sigmas[:-1], sigmas[1:])):
        clean, loss, grad = consistency(x, sigma, y, EV, denoiser)
        norm = float(np.linalg.norm(grad))
        score = (clean - x) / sigma ** 2
        guidance = -eta_prime * grad / (sigma * norm) if norm > 1e-20 else np.zeros_like(grad)
        prior_step = -sigma * (following - sigma) * score
        guidance_step = -sigma * (following - sigma) * guidance
        x = x + prior_step + guidance_step
        if not np.all(np.isfinite(x)):
            raise ValueError('Inference became non-finite; inspect input scaling, V, and guidance')
        row = {'step': i + 1, 'sigma': float(sigma), 'next_sigma': float(following),
               'encoded_residual': float(np.sqrt(loss) / denominator) if denominator > 0 else None,
               'loss': loss, 'gradient_norm': norm,
               'prior_update_norm': float(np.linalg.norm(prior_step)),
               'guidance_update_norm': float(np.linalg.norm(guidance_step)),
               'elapsed_seconds': time.perf_counter() - start}
        trace.append(row)
        if progress:
            progress({'stage': 'inference', **row, 'total': steps})
    return expand(x), trace


def synthetic_bundle(config):
    q = int(config.get('microphones', 6))
    radius = float(config.get('radius_m', .06))
    snr = float(config.get('snr_db', 50))
    if q not in (4, 5, 6, 8, 12, 16) or not .01 <= radius <= .25 or not 0 <= snr <= 80:
        raise ValueError('Invalid synthetic array settings')
    rng = np.random.default_rng(int(config.get('data_seed', 2026)))
    theta = np.arange(q) * np.pi * (3 - np.sqrt(5))
    z = np.zeros(q) if config.get('coplanar') else 1 - 2 * (np.arange(q) + .5) / q
    positions = np.c_[np.sqrt(1-z*z)*np.cos(theta), np.sqrt(1-z*z)*np.sin(theta), z] * radius
    frequencies = np.geomspace(SYNTHETIC_MIN_HZ, SYNTHETIC_MAX_HZ, SYNTHETIC_FREQUENCIES)
    effective_order = 15 if config.get('mismatch') else ORDER
    directions = rng.normal(size=(5, 3))
    harmonics = real_n3d(effective_order, directions)
    signal_shape = (len(frequencies), 5, SYNTHETIC_FRAMES)
    signals = (rng.normal(size=signal_shape) + 1j*rng.normal(size=signal_shape)) / np.sqrt(2)
    signals *= np.array([1., .7, .22, .15, .1])[None, :, None]
    truth = np.einsum('sc,fst->fct', harmonics, signals)
    physical = modal_matrix(frequencies, positions, effective_order)
    p = physical @ truth
    level = np.sqrt(np.mean(np.abs(p)**2)) * 10 ** (-snr/20)
    p += level * (rng.normal(size=p.shape) + 1j*rng.normal(size=p.shape)) / np.sqrt(2)
    return {'frequencies': frequencies, 'V': physical[:, :, :CHANNELS], 'p': p,
            'reference': truth[:, :4], 'positions': positions,
            'provenance': 'synthetic complex spectra; independent random plane waves, not speech or HARP',
            'effective_order': effective_order}


def load_bundle(bundle):
    if not isinstance(bundle, dict) or bundle.get('schema') != 'adeps-test-array-stft/1':
        raise ValueError('Expected adeps-test-array-stft/1 JSON')
    if bundle.get('sh_ordering') != 'ACN' or bundle.get('sh_normalization') != 'N3D':
        raise ValueError('This checkpoint requires explicit real ACN/N3D conventions')
    v = complex_array(bundle['V_real'], bundle['V_imag'], 'V')
    p = complex_array(bundle['p_real'], bundle['p_imag'], 'p')
    frequencies = np.asarray(bundle['frequencies_hz'], float)
    ref = None
    if 'reference_real' in bundle:
        ref = complex_array(bundle['reference_real'], bundle['reference_imag'], 'reference')
    return {'frequencies': frequencies, 'V': v, 'p': p, 'reference': ref,
            'positions': bundle.get('microphone_positions_m', []),
            'provenance': str(bundle.get('provenance', 'user supplied; acquisition unverified')),
            'effective_order': None}


def validate_data(data, max_bins=MAX_BINS):
    v, p, f, ref = (data[k] for k in ('V', 'p', 'frequencies', 'reference'))
    if v.ndim != 3 or p.ndim != 3 or v.shape[:2] != p.shape[:2] or v.shape[2] != CHANNELS:
        raise ValueError('Neural input: V=[F,Q,36], p=[F,Q,T]. A 4-coefficient V cannot be padded.')
    if not 4 <= v.shape[1] <= 64 or min(v.shape + p.shape) < 1:
        raise ValueError('FOA requires at least 4 microphones; maximum 64')
    if v.shape[0] * p.shape[2] > max_bins:
        raise ValueError(f'Maximum {max_bins} frequency-time bins per run; use a shorter segment')
    if v.size > 600_000 or f.ndim != 1 or len(f) != v.shape[0] or len(f) < 2:
        raise ValueError('Frequency grid or transfer matrix size is invalid')
    if not np.all(np.isfinite(f)) or np.any(f < 0) or np.any(np.diff(f) <= 0):
        raise ValueError('Frequencies must be finite, nonnegative and strictly increasing')
    if not np.all(np.isfinite(v)) or not np.all(np.isfinite(p)):
        raise ValueError('V and p must contain finite values')
    if not np.any(np.abs(p) > 0):
        raise ValueError('The observation is silent; no neural reconstruction is run')
    if ref is not None:
        if ref.shape not in ((len(f), 4, p.shape[2]), (len(f), 36, p.shape[2])):
            raise ValueError('Reference must be aligned [F,4,T] or [F,36,T]')
        data['reference'] = ref[:, :4]
    positions = np.asarray(data['positions'], float)
    if positions.size and (positions.shape != (v.shape[1], 3) or not np.all(np.isfinite(positions))):
        raise ValueError('Microphone positions must be finite [Q,3]')


def quality(estimate, reference):
    if reference is None:
        return {'reference_available': False, 'nrmse_db': None, 'coherence': None}
    norm = np.linalg.norm(reference)
    denom = np.sum(abs(estimate)**2, axis=2) * np.sum(abs(reference)**2, axis=2)
    valid = denom > np.finfo(float).tiny
    coh = np.divide(abs(np.sum(estimate * reference.conj(), axis=2))**2, denom,
                    out=np.full_like(denom, np.nan), where=valid)
    coh = np.clip(coh, 0, 1)
    ref_norm = np.linalg.norm(reference, axis=(1, 2))
    err = np.divide(np.linalg.norm(estimate-reference, axis=(1, 2)), ref_norm,
                    out=np.full_like(ref_norm, np.nan), where=ref_norm > 0)
    return {'reference_available': True,
            'nrmse_db': float(20*np.log10(max(np.linalg.norm(estimate-reference)/norm, 1e-12))) if norm > 0 else None,
            'coherence': float(np.mean(coh[valid])) if valid.any() else None,
            'error_db_by_frequency': 20*np.log10(np.maximum(err, 1e-12)),
            'coherence_by_frequency': np.divide(np.nansum(coh, axis=1), valid.sum(axis=1),
                                               out=np.full(len(coh), np.nan), where=valid.sum(axis=1)>0),
            'coherence_valid_bins': int(valid.sum()), 'coherence_total_bins': int(valid.size)}


def run_neural(config, progress=None, model=None):
    start = time.perf_counter()
    data = load_bundle(config['bundle']) if 'bundle' in config else synthetic_bundle(config)
    validate_data(data)
    v, p, ref = (data[k] for k in ('V', 'p', 'reference'))
    regularization = float(config.get('regularization', .001))
    if not np.isfinite(regularization) or not 1e-8 <= regularization <= 10:
        raise ValueError('regularization must be between 1e-8 and 10')
    steps = config.get('steps', 150)
    eta = float(config.get('eta_prime', 50.))
    seed = config.get('seed', 42)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('seed must be an integer between 0 and 4294967295')
    linear, E, gamma2 = encode(v, p, regularization)
    # Single observation-only gain; never peek at the clean reference.
    scale = float(np.sqrt(np.mean(abs(linear)**2)))
    if scale < 1e-12 or not np.isfinite(scale):
        raise ValueError('Encoded observation is too small; inspect V and recording levels')
    y = compress(linear / scale)
    denoiser = model or TinyDenoiser()
    estimated, trace = sample(y, E @ v, denoiser, steps, eta, seed, progress)
    estimated *= scale
    linear_foa, neural_foa = linear[:, :4], estimated[:, :4]
    singular = np.linalg.svd(v[:, :, :4], compute_uv=False)
    ranks = np.sum(singular > np.maximum(singular[:, :1]*1e-8, 1e-15), axis=1)
    pnorm = np.linalg.norm(p)
    final_encoded = compress((E @ v) @ (estimated/scale))
    input_digest = hashlib.sha256()
    for a in (data['frequencies'], v.real, v.imag, p.real, p.imag):
        input_digest.update(json.dumps(list(a.shape)).encode('ascii'))
        input_digest.update(np.ascontiguousarray(a, dtype='<f8').tobytes())
    return {'kind': 'neural', 'schema': 'adeps-test-neural-run/1',
            'implementation': 'independent ADEPS-equation sampler + tiny trained synthetic MLP',
            'official_model': False, 'paper_performance_reproduced': False,
            'source': 'https://arxiv.org/abs/2608.24558v2', 'model': denoiser.card,
            'input_sha256': input_digest.hexdigest(), 'provenance': data['provenance'],
            'configuration': {'steps': steps, 'eta_prime': eta, 'seed': seed,
                              'regularization': regularization, 'alpha': ALPHA, 'beta': BETA,
                              'sigma_max': 20, 'sigma_min': .002, 'rho': 10,
                              'terminal': 'append zero; M positive points and M Euler updates',
                              'observation_rms_scale': scale, 'gamma_squared_by_frequency': gamma2,
                              'gradient_normalization': 'one L2 norm across all real and imaginary F,C,T coordinates',
                              'input_kind': 'imported' if 'bundle' in config else 'synthetic',
                              'synthetic_settings': {**{k: config.get(k, default) for k, default in
                                [('microphones', 6), ('radius_m', .06), ('snr_db', 50), ('data_seed', 2026),
                                 ('coplanar', False), ('mismatch', False)]},
                                'frequency_min_hz': float(data['frequencies'][0]),
                                'frequency_max_hz': float(data['frequencies'][-1]),
                                'frequency_count': len(data['frequencies']),
                                'frequency_spacing': 'logarithmic',
                                'frames': p.shape[2]} if 'bundle' not in config else None},
            'frequencies_hz': data['frequencies'], 'microphones': v.shape[1],
            'frames': p.shape[2], 'prior_order': ORDER, 'output_order': 1,
            'effective_order': data['effective_order'], 'microphone_positions_m': data['positions'],
            'foa_rank_by_frequency': ranks, 'rank_deficient_bins': int(np.sum(ranks < 4)),
            'quality': {'linear': quality(linear_foa, ref), 'neural': quality(neural_foa, ref)},
            'diagnostics': {'linear_microphone_residual': float(np.linalg.norm(v@linear-p)/pnorm),
                            'neural_microphone_residual': float(np.linalg.norm(v@estimated-p)/pnorm),
                            'final_encoded_residual': float(np.linalg.norm(final_encoded-y)/np.linalg.norm(y)),
                            'elapsed_seconds': time.perf_counter()-start},
            'trace': trace, 'output': {'sh_ordering': 'ACN', 'sh_normalization': 'N3D',
                                      'channel_names': ['W', 'Y', 'Z', 'X'],
                                      'linear_real': linear_foa.real, 'linear_imag': linear_foa.imag,
                                      'neural_real': neural_foa.real, 'neural_imag': neural_foa.imag}}
