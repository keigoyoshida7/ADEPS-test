"""Independent, trained physics-conditioned residual spatial estimator.

This is not ADEPS's diffusion model or an author checkpoint. Input is real
ACN/N3D modal coefficients in complex [frequency, 36, time] form. The inference
API deliberately accepts no clean reference. It runs using NumPy only.
"""
from pathlib import Path
import hashlib
import json
import numpy as np

CHANNELS = 36
FEATURES = 465
MODEL_ID = 'spatial-v1'
MODEL_DIR = Path(__file__).resolve().parents[1] / 'public' / 'models'


def features(linear, resolution, frequencies):
    """Build physics conditioning with input-only per-frequency RMS scaling.

The scale averages the first four observed coefficients over the supplied
frames. This exact function is used for training and inference; no target
signal, microphone SNR, or reference amplitude is consulted.
"""
    linear = np.asarray(linear, dtype=np.complex128)
    resolution = np.asarray(resolution, dtype=np.complex128)
    frequencies = np.asarray(frequencies, dtype=float)
    if linear.ndim != 3 or linear.shape[1] != CHANNELS or min(linear.shape) < 1:
        raise ValueError('linear must have nonempty shape [F,36,T]')
    nf, _, nt = linear.shape
    if resolution.shape != (nf, CHANNELS, CHANNELS):
        raise ValueError('resolution must have shape [F,36,36]')
    if frequencies.shape != (nf,) or np.any(frequencies < 0):
        raise ValueError('frequencies must have shape [F] and be nonnegative')
    if not all(np.all(np.isfinite(a)) for a in (linear, resolution, frequencies)):
        raise ValueError('Spatial estimator input must be finite')
    if nf * nt > 131072:
        raise ValueError('Split input into at most 131072 frequency-time bins')
    scale = np.sqrt(np.mean(np.abs(linear[:, :4]) ** 2, axis=(1, 2)))
    # Zero input maps to zero after inverse scaling. A tiny floor only keeps
    # feature arithmetic finite; it is not a target-derived noise estimate.
    scale = np.maximum(scale, 1e-12)
    z = (linear / scale[:, None, None]).transpose(0, 2, 1).reshape(-1, CHANNELS)
    r = resolution[:, :4].reshape(nf, -1)
    # Relative logarithmic Hz coordinate, fixed to the declared 1--20 kHz
    # training interval. Values outside that interval remain extrapolation.
    lf = (np.log10(np.maximum(frequencies, 1.)) / np.log10(20000.) * 2 - 1)[:, None]
    condition = np.concatenate((r.real, r.imag,
                                np.diagonal(resolution, axis1=1, axis2=2).real, lf), axis=1)
    normalized = linear / scale[:, None, None]
    covariance = normalized[:, :4] @ normalized[:, :4].conj().transpose(0, 2, 1) / nt
    covariance = covariance.reshape(nf, 16)
    power = np.mean(np.abs(normalized)**2, axis=2)
    condition = np.concatenate((condition, covariance.real, covariance.imag, power), axis=1)
    condition = np.repeat(condition, nt, axis=0)
    x = np.concatenate((z.real, z.imag, condition), axis=1)
    if not np.all(np.isfinite(x)) or np.max(np.abs(x)) > 1e8:
        raise ValueError('Unstable encoding scale or resolution matrix')
    return x.astype(np.float32), scale


def unpack(packed, scale, shape):
    packed = np.asarray(packed)
    z = packed[:, :CHANNELS] + 1j * packed[:, CHANNELS:]
    return z.reshape(shape[0], shape[2], CHANNELS).transpose(0, 2, 1) * np.asarray(scale)[:, None, None]


def silu(x):
    return x * (.5 * (1 + np.tanh(.5 * x)))


class SpatialModel:
    """Four hidden SiLU layers with an identity skip and window covariance context."""
    def __init__(self, directory=None):
        directory = Path(directory or MODEL_DIR)
        self.card = json.loads((directory / f'{MODEL_ID}.json').read_text())
        path = directory / f'{MODEL_ID}.npz'
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.card['weights_sha256']:
            raise ValueError('Spatial model checksum mismatch')
        if self.card.get('schema') != 'adeps-test-physics-residual/1':
            raise ValueError('Unsupported spatial model schema')
        hidden = int(self.card['hidden_channels'])
        if not 32 <= hidden <= 2048 or self.card.get('hidden_layers') != 4:
            raise ValueError('Unsupported spatial model architecture')
        sizes = [FEATURES, hidden, hidden, hidden, hidden, 72]
        expected = {f'{kind}{i}': ((sizes[i-1], sizes[i]) if kind == 'w' else (sizes[i],))
                    for i in range(1, 6) for kind in ('w', 'b')}
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != set(expected):
                raise ValueError('Unsupported spatial model weight names')
            self.weights = {key: data[key].astype(np.float32) for key in data.files}
        if any(self.weights[k].shape != shape or not np.all(np.isfinite(self.weights[k]))
               for k, shape in expected.items()):
            raise ValueError('Invalid spatial model tensor shape or values')

    @classmethod
    def load(cls, path=None):
        path = Path(path) if path else MODEL_DIR
        return cls(path.parent if path.suffix in ('.npz', '.json') else path)

    def predict_features(self, x, batch_size=1024):
        x = np.asarray(x, dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != FEATURES or not np.all(np.isfinite(x)):
            raise ValueError('Expected finite [bins,465] features')
        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError('batch_size must be a positive integer')
        parts = []
        for offset in range(0, len(x), batch_size):
            source = x[offset:offset + batch_size]
            h = source
            for i in range(1, 5):
                h = silu(h @ self.weights[f'w{i}'] + self.weights[f'b{i}'])
            parts.append(source[:, :72] + h @ self.weights['w5'] + self.weights['b5'])
        return np.concatenate(parts, axis=0) if parts else np.empty((0, 72), np.float32)

    def predict(self, linear, resolution, frequencies, noise_gain=None):
        """Return complex [F,36,T]; noise_gain is reserved and not used.

No test-time reference, automatic quality selection, sampling noise, microphone
access, or physical projection is hidden inside this estimator. A caller may
compare OFF (unchanged ridge) and ON using a separately fixed blend/projection.
"""
        x, scale = features(linear, resolution, frequencies)
        prediction = unpack(self.predict_features(x), scale, np.shape(linear))
        # Completely silent inputs are explicitly invariant despite learned bias.
        prediction[:, :, np.all(np.abs(linear) == 0, axis=(0, 1))] = 0
        if not np.all(np.isfinite(prediction)):
            raise ValueError('Spatial model produced nonfinite output')
        return prediction
