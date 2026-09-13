"""Optional Torch tests of the native prior's complex posterior gradient chain.

The objective below implements H and its inverse independently from the
runtime analytical VJP. Finite differences include both training-domain scale
factors, a non-Hermitian complex EV, and a non-holomorphic denoiser.
"""
import sys
import unittest
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from paper_inference import PaperPrior, consistency, sample
from paper_prior import PaperDenoiser

torch.set_num_threads(2)


def independent_h(z, inverse=False):
    radius = np.abs(z)
    alpha, beta, floor = .67, 3., 1e-8
    threshold = beta * floor ** alpha if inverse else floor
    unit = np.divide(z, radius, out=np.zeros_like(z), where=radius > 0)
    if inverse:
        normal = (radius / beta) ** (1 / alpha) * unit
        linear = z / (beta * floor ** (alpha - 1))
    else:
        normal = beta * radius ** alpha * unit
        linear = beta * floor ** (alpha - 1) * z
    return np.where(radius < threshold, linear, normal)


def objective(x, sigma, y, ev, prior):
    clean, _ = prior.predict(x, sigma)
    physical = independent_h(prior.std * clean, inverse=True)
    residual = independent_h(ev @ physical) / prior.std - y
    return float(np.sum(np.abs(residual) ** 2))


class NonHolomorphicPrior:
    def __init__(self, std):
        self.std = std

    def predict(self, x, sigma):
        # Re(D)=.5 Re(x), Im(D)=.1 Im(x): not a complex-linear function.
        return .3 * x + .2 * x.conj(), lambda g: .3 * g + .2 * g.conj()


class PaperInferenceTests(unittest.TestCase):
    def fixture(self, shape=(8, 36, 8), seed=571):
        rng = np.random.default_rng(seed)
        x = .1 * (rng.normal(size=shape) + 1j * rng.normal(size=shape))
        y = .1 * (rng.normal(size=shape) + 1j * rng.normal(size=shape))
        ev = (rng.normal(size=(shape[0], 36, 36)) +
              1j * rng.normal(size=(shape[0], 36, 36))) / np.sqrt(36)
        return rng, x, y, ev

    def test_complete_chain_matches_complex_directional_finite_difference(self):
        rng, x, y, ev = self.fixture(shape=(3, 36, 4))
        for std in (.25, 2.6):
            prior = NonHolomorphicPrior(std)
            _, loss, gradient = consistency(x, .7, y, ev, prior)
            self.assertAlmostEqual(loss, objective(x, .7, y, ev, prior), places=11)
            for imaginary in (False, True):
                direction = rng.normal(size=x.shape) * (1j if imaginary else 1.)
                direction /= np.linalg.norm(direction)
                epsilon = 1e-5
                numerical = (objective(x + epsilon * direction, .7, y, ev, prior) -
                             objective(x - epsilon * direction, .7, y, ev, prior)) / (2 * epsilon)
                analytic = float(np.real(np.vdot(gradient, direction)))
                np.testing.assert_allclose(analytic, numerical, rtol=2e-6, atol=2e-8)

    def test_linear_extension_near_zero_has_correct_scaled_derivative(self):
        rng, x, y, ev = self.fixture(shape=(2, 36, 3), seed=120)
        x, y = x * 1e-7, y * 1e-7
        prior = NonHolomorphicPrior(2.6)
        _, _, gradient = consistency(x, .1, y, ev, prior)
        direction = rng.normal(size=x.shape) + 1j * rng.normal(size=x.shape)
        direction /= np.linalg.norm(direction)
        epsilon = 1e-10
        numerical = (objective(x + epsilon * direction, .1, y, ev, prior) -
                     objective(x - epsilon * direction, .1, y, ev, prior)) / (2 * epsilon)
        np.testing.assert_allclose(np.real(np.vdot(gradient, direction)), numerical, rtol=2e-6, atol=1e-15)

    def test_native_predict_pack_and_vjp_preserve_complex_channel_time_axes(self):
        class CoupledChannels(nn.Module):
            def forward(self, x, sigma):
                real, imag = x[:, :36], x[:, 36:]
                return torch.cat([.7 * real + .2 * torch.roll(imag, 1, dims=-1),
                                  -.3 * real + .5 * imag], dim=1)

        prior = PaperPrior.__new__(PaperPrior)
        prior.device, prior.std, prior.network = 'cpu', 2.6, CoupledChannels()
        rng, x, _, _ = self.fixture(shape=(5, 36, 7))
        predicted, vjp = prior.predict(x, .7)
        expected = .7 * x.real + .2 * np.roll(x.imag, 1, axis=-1) + 1j * (-.3 * x.real + .5 * x.imag)
        np.testing.assert_allclose(predicted, expected, rtol=2e-6, atol=3e-8)
        g = rng.normal(size=x.shape) + 1j * rng.normal(size=x.shape)
        expected_vjp = .7 * g.real - .3 * g.imag + 1j * (.2 * np.roll(g.real, -1, axis=-1) + .5 * g.imag)
        np.testing.assert_allclose(vjp(g), expected_vjp, rtol=2e-6, atol=3e-7)

    def test_actual_network_complete_chain_matches_finite_difference(self):
        torch.manual_seed(571)
        prior = PaperPrior.__new__(PaperPrior)
        prior.device, prior.std = 'cpu', 2.6
        prior.network = PaperDenoiser(sigma_data=1., base_channels=8,
                                     gradient_checkpointing=False).eval().requires_grad_(False)
        rng, x, y, ev = self.fixture()
        _, loss, gradient = consistency(x, .7, y, ev, prior)
        self.assertTrue(np.isfinite(gradient).all())
        self.assertAlmostEqual(loss, objective(x, .7, y, ev, prior), places=10)
        for imaginary in (False, True):
            direction = rng.normal(size=x.shape) * (1j if imaginary else 1.)
            direction /= np.linalg.norm(direction)
            # The actual network uses float32. This larger central-difference
            # step and tolerance accommodate rounding in two network passes.
            epsilon = .01
            numerical = (objective(x + epsilon * direction, .7, y, ev, prior) -
                         objective(x - epsilon * direction, .7, y, ev, prior)) / (2 * epsilon)
            analytic = float(np.real(np.vdot(gradient, direction)))
            np.testing.assert_allclose(analytic, numerical, rtol=.01, atol=5e-4)

    def test_exact_consistency_has_zero_loss_and_gradient(self):
        # Runtime H and independent polar H differ at float64 rounding level;
        # an identity EV leaves H(H^-1(std*clean))/std equal to clean.
        _, x, _, _ = self.fixture(shape=(2, 36, 3))
        prior = NonHolomorphicPrior(2.6)
        y, _ = prior.predict(x, .7)
        ev = np.broadcast_to(np.eye(36, dtype=complex), (2, 36, 36))
        _, loss, gradient = consistency(x, .7, y, ev, prior)
        self.assertLess(loss, 1e-27)
        self.assertLess(np.linalg.norm(gradient), 1e-13)

    def test_invalid_denoiser_or_vjp_never_returns_successful_sample(self):
        _, x, _, _ = self.fixture(shape=(2, 36, 3))
        ev = np.broadcast_to(np.eye(36, dtype=complex), (2, 36, 36))
        for corrupt_clean in (False, True):
            class InvalidPrior:
                std = 1.
                def predict(self, current, sigma):
                    clean = np.full_like(current, np.nan) if corrupt_clean else current / 2
                    return clean, lambda gradient: np.full_like(gradient, np.nan)
            # A zero guidance setting must not hide a broken gradient either.
            for eta in (0., 50.):
                with self.assertRaises(ValueError):
                    sample(x, ev, InvalidPrior(), steps=2, eta_prime=eta)

    def test_sample_records_both_updates_and_accepts_finite_zero_gradient(self):
        _, x, _, _ = self.fixture(shape=(2, 36, 3))
        ev = np.broadcast_to(np.eye(36, dtype=complex), (2, 36, 36))
        class ConstantPrior:
            std = 1.
            def predict(self, current, sigma):
                return x.copy(), lambda gradient: np.zeros_like(gradient)
        progress = []
        result, trace = sample(x, ev, ConstantPrior(), steps=2, progress=progress.append)
        self.assertTrue(np.isfinite(result).all())
        self.assertEqual(len(trace), 2)
        self.assertTrue(all(row['guidance_update_norm'] == 0 for row in trace))
        self.assertTrue(all(np.isfinite(row['prior_update_norm']) for row in trace))
        self.assertEqual(progress[-1]['stage'], 'inference')
        self.assertEqual(progress[-1]['total'], 2)


if __name__ == '__main__':
    unittest.main()
