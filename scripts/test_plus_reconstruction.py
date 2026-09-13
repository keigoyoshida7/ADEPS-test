"""CPU-only independent closed-form tests; not evidence of model improvement.

Run: python3 scripts/test_plus_reconstruction.py
"""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from plus_reconstruction import proximal_correction


class ProximalCorrectionTests(unittest.TestCase):
    def test_zero_ridge_fits_measurement_preserves_nullspace_and_inputs(self):
        # Both rows are orthogonal but complex: catches missing adjoints.
        v = np.array([[[1, 1j, 0], [0, 0, 2j]]], dtype=complex)
        p = np.array([[[3 + 2j, 1 - 4j], [-2j, 4]]])
        z = np.array([[[1 + 2j, 3], [-2 + 1j, 4j], [5, 6j]]])
        saved = [a.copy() for a in (z, p, v)]
        out, report = proximal_correction(z, p, v, ridge_relative=0.)
        np.testing.assert_allclose(v @ out, p, atol=2e-14)
        null_vector = np.array([1., 1j, 0.]) / np.sqrt(2)
        np.testing.assert_allclose(null_vector.conj() @ out[0],
                                   null_vector.conj() @ z[0], atol=2e-14)
        for original, copy in zip((z, p, v), saved):
            np.testing.assert_array_equal(original, copy)
        self.assertEqual(report['rank_by_frequency'], [2])

    def test_positive_ridge_matches_independent_complex_normal_equations(self):
        rng = np.random.default_rng(872)
        v = rng.normal(size=(3, 2, 4)) + 1j * rng.normal(size=(3, 2, 4))
        z = rng.normal(size=(3, 4, 5)) + 1j * rng.normal(size=(3, 4, 5))
        p = rng.normal(size=(3, 2, 5)) + 1j * rng.normal(size=(3, 2, 5))
        rel = np.array([0., .02, .5])
        noise = np.array([.25, .2, 1.])
        prior = np.array([.5, 2., 4.])
        out, info = proximal_correction(z, p, v, ridge_relative=rel,
                                         noise_variance=noise, prior_variance=prior)
        for f in range(3):
            adjoint = v[f].conj().T
            lam = rel[f] * np.sum(abs(v[f]) ** 2) / 2 + noise[f] / prior[f]
            expected = np.linalg.solve(adjoint @ v[f] + lam * np.eye(4),
                                       adjoint @ p[f] + lam * z[f])
            np.testing.assert_allclose(out[f], expected, atol=3e-13)
            self.assertAlmostEqual(info['lambda_by_frequency'][f], lam)
        self.assertTrue(np.all(np.array(info['residual_norm_after_by_frequency']) <=
                               np.array(info['residual_norm_before_by_frequency']) + 1e-12))
        json.dumps(info, allow_nan=False)

    def test_noise_floor_produces_known_gaussian_shrinkage(self):
        v = np.eye(2)[None]
        z = np.zeros((1, 2, 4))
        # Orthogonal signal and noise patterns of exact squared norms 2 and 8.
        truth = np.array([[[1, -1, 0, 0], [0, 0, 0, 0]]], dtype=complex)
        noise = np.array([[[0, 0, 2j, -2j], [0, 0, 0, 0]]])
        p = truth + noise
        out, report = proximal_correction(z, p, v, ridge_relative=0.,
                                          noise_variance=4., prior_variance=1.)
        np.testing.assert_allclose(out, p / 5, atol=1e-15)
        self.assertLess(np.sum(abs(out - truth) ** 2), np.sum(abs(p - truth) ** 2))
        self.assertEqual(report['absolute_noise_ridge_by_frequency'], [4.])
        # This constructed case tests algebra, not that all noisy signals improve.

    def test_rank_deficient_dc_and_zero_matrix_have_finite_honest_residuals(self):
        v = np.array([[[1., 0], [1., 0]], [[0, 0], [0, 0]]])
        z = np.array([[[4 + 1j], [3 - 2j]], [[7 + 2j], [-9j]]])
        p = np.array([[[2.], [4.]], [[1.], [0.]]])
        out, info = proximal_correction(z, p, v, ridge_relative=0.)
        np.testing.assert_allclose(out[0, :, 0], [3., 3 - 2j], atol=2e-15)
        np.testing.assert_array_equal(out[1], z[1])
        self.assertEqual(info['rank_by_frequency'], [1, 0])
        np.testing.assert_allclose(info['residual_norm_after_by_frequency'], [np.sqrt(2), 1.])
        reg, _ = proximal_correction(z, p, v, ridge_relative=.001, noise_variance=1e-5)
        self.assertTrue(np.all(np.isfinite(reg)))
        silent, info = proximal_correction(np.zeros_like(z), np.zeros_like(p), v)
        np.testing.assert_array_equal(silent, 0.)
        self.assertEqual(info['relative_residual_after_by_frequency'], [None, None])
        json.dumps(info, allow_nan=False)

    def test_real_endpoints_remain_real_and_common_physical_rescaling_is_equivariant(self):
        rng = np.random.default_rng(33)
        v, z, p = (rng.normal(size=shape) for shape in ((2, 3, 4), (2, 4, 3), (2, 3, 3)))
        out, _ = proximal_correction(z, p, v, noise_variance=.2, prior_variance=.4)
        np.testing.assert_array_equal(out.imag, 0.)
        for scale in (.03, 7.):
            changed, _ = proximal_correction(z * scale, p * scale, v,
                noise_variance=.2 * scale ** 2, prior_variance=.4 * scale ** 2)
            np.testing.assert_allclose(changed, out * scale, atol=1e-13)

    def test_zero_ridge_projection_cannot_increase_full_coefficient_error_when_feasible(self):
        rng = np.random.default_rng(61)
        v = rng.normal(size=(2, 3, 7)) + 1j * rng.normal(size=(2, 3, 7))
        truth = rng.normal(size=(2, 7, 4)) + 1j * rng.normal(size=(2, 7, 4))
        z = rng.normal(size=truth.shape) + 1j * rng.normal(size=truth.shape)
        out, _ = proximal_correction(z, v @ truth, v, ridge_relative=0.)
        self.assertLess(np.linalg.norm(out - truth), np.linalg.norm(z - truth))

    def test_rcond_is_explicit_and_positive_ridge_does_not_truncate_small_modes(self):
        v = np.diag([1., 1e-8])[None]
        z = np.zeros((1, 2, 1))
        p = np.ones((1, 2, 1))
        exact, report = proximal_correction(z, p, v, ridge_relative=0., rcond=1e-6)
        np.testing.assert_allclose(exact[0, :, 0], [1., 0.])
        self.assertEqual(report['rank_by_frequency'], [1])
        soft, _ = proximal_correction(z, p, v, ridge_relative=0., noise_variance=1e-16, rcond=1e-6)
        self.assertAlmostEqual(soft[0, 1, 0].real, 5e7, places=6)

    def test_invalid_shape_values_and_hyperparameters_are_rejected(self):
        z, p, v = np.ones((2, 4, 3)), np.ones((2, 2, 3)), np.ones((2, 2, 4))
        for args in ((z[0], p, v), (z, p[:, :, :2], v), (z[:, :3], p, v),
                     (z * np.nan, p, v), (z, p, v * np.inf), (z[:0], p[:0], v[:0])):
            with self.subTest(shapes=[a.shape for a in args]), self.assertRaises(ValueError):
                proximal_correction(*args)
        for kwargs in ({'ridge_relative': -1}, {'noise_variance': -1},
                       {'prior_variance': 0}, {'rcond': 1}, {'rcond': -1},
                       {'noise_variance': [1, 2, 3]}, {'noise_variance': np.inf},
                       {'ridge_relative': 1j}, {'prior_variance': [1, np.nan]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                proximal_correction(z, p, v, **kwargs)


class PnPRefinementTests(unittest.TestCase):
    def fixture(self):
        import plus_diffusion
        self.module = plus_diffusion
        f = np.fft.rfftfreq(512, 1 / 16000)
        v = np.broadcast_to(np.eye(36)[:4], (len(f), 4, 36)).astype(complex)
        p = np.ones((len(f), 4, 2), complex)
        p[:, 0] = 2.
        prior = SimpleNamespace(std=1.3, card={'configuration': {
            'sample_rate_hz': 16000, 'n_fft': 512, 'hop': 128},
            'model': {'name': 'unit-test mock, not trained weights'}})
        return p, v, f, prior

    def test_identity_denoiser_fixed_observation_scale_and_exact_network_count(self):
        p, v, f, prior = self.fixture()
        initial = np.full((len(f), 36, 2), 7., complex)
        initial[:, 4:] += 2j
        inputs, outputs, progress = [], [], []

        def identity(prior_, x, sigma):
            inputs.append((x.copy(), sigma))
            return x.copy()

        with patch.object(self.module, '_denoise_no_grad', side_effect=identity) as mock:
            result = self.module.refine(p, v, f, prior, initial, steps=3,
                sigma_start=1., ridge_relative=0., snapshot=lambda row, a: outputs.append((row, a)),
                progress=progress.append)
        self.assertEqual(mock.call_count, 3)
        self.assertEqual(result['nfe'], 3)
        self.assertEqual(len(result['trace']), 3)
        self.assertEqual(len(progress), 3)
        self.assertEqual(len(outputs), 4)  # Three PnP snapshots plus final no-NFE prox.
        self.assertAlmostEqual(result['observation_rms_scale'], 2 / 1.001)
        np.testing.assert_allclose(v @ result['estimate'], p, atol=2e-14)
        np.testing.assert_allclose(result['estimate'][1:-1, 4:], initial[1:-1, 4:], atol=3e-14)
        np.testing.assert_array_equal(result['estimate'][[0, -1]].imag, 0.)
        self.assertEqual(inputs[-1][1], .002)
        self.assertIsNone(result['trace'][-1]['next_sigma'])
        self.assertFalse(result['configuration']['weights_updated'])
        self.assertFalse(result['configuration']['reference_used'])
        # Mutating callback-owned arrays cannot change the estimator's output.
        outputs[-1][1][:] = 0
        self.assertGreater(np.linalg.norm(result['estimate']), 0)
        json.dumps(result['trace'], allow_nan=False)
        json.dumps(result['configuration'], allow_nan=False)

    def test_no_noise_is_seed_independent_optional_initial_noise_is_reproducible(self):
        p, v, f, prior = self.fixture()
        with patch.object(self.module, '_denoise_no_grad', side_effect=lambda prior, x, sigma: .9 * x):
            base = dict(steps=2, ridge_relative=.01, relaxation=.5)
            a = self.module.refine(p, v, f, prior, seed=1, **base)
            b = self.module.refine(p, v, f, prior, seed=72, **base)
            np.testing.assert_array_equal(a['estimate'], b['estimate'])
            c = self.module.refine(p, v, f, prior, seed=1, initial_noise_scale=.05, **base)
            d = self.module.refine(p, v, f, prior, seed=1, initial_noise_scale=.05, **base)
            e = self.module.refine(p, v, f, prior, seed=2, initial_noise_scale=.05, **base)
            np.testing.assert_array_equal(c['estimate'], d['estimate'])
            self.assertGreater(np.linalg.norm(c['estimate'] - e['estimate']), 0)

    def test_invalid_input_fails_before_network_and_invalid_denoiser_stops_immediately(self):
        p, v, f, prior = self.fixture()
        with patch.object(self.module, '_denoise_no_grad', side_effect=lambda prior, x, sigma: x) as mock:
            for kwargs in ({'steps': 1}, {'steps': 2.5}, {'relaxation': 1.1},
                           {'sigma_start': .001}, {'sigma_start': 81.}, {'noise_variance': -1.},
                           {'initial_noise_scale': -1.}, {'scale_mode': 'target'}, {'seed': -1}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    self.module.refine(p, v, f, prior, **kwargs)
            with self.assertRaises(ValueError):
                self.module.refine(p, v, f + 1, prior)
            with self.assertRaises(ValueError):
                self.module.refine(p * 0, v, f, prior)
            bad = p.copy()
            bad[0, 0, 0] += 1j
            with self.assertRaises(ValueError):
                self.module.refine(bad, v, f, prior)
            mock.assert_not_called()
        with patch.object(self.module, '_denoise_no_grad', side_effect=lambda prior, x, sigma: x * np.nan) as mock:
            with self.assertRaises(ValueError):
                self.module.refine(p, v, f, prior, steps=2)
            self.assertEqual(mock.call_count, 1)

    def test_native_pack_uses_cpu_no_grad_and_keeps_real_imaginary_channel_order(self):
        self.fixture()
        try:
            import torch
        except ImportError:
            self.skipTest('Optional native no_grad test requires Torch; NumPy algebra tests remain runnable.')

        class SmallNetwork(torch.nn.Module):
            def forward(self, x, sigma):
                self.grad_enabled = torch.is_grad_enabled()
                self.input_requires_grad = x.requires_grad
                return torch.cat([2 * x[:, :36] + x[:, 36:],
                                  3 * x[:, 36:] - x[:, :36]], dim=1)

        net = SmallNetwork().eval()
        prior = SimpleNamespace(network=net, device='cpu')
        rng = np.random.default_rng(612)
        x = rng.normal(size=(5, 36, 3)) + 1j * rng.normal(size=(5, 36, 3))
        out = self.module._denoise_no_grad(prior, x, .5)
        expected = 2 * x.real + x.imag + 1j * (3 * x.imag - x.real)
        np.testing.assert_allclose(out, expected, rtol=2e-7, atol=7e-7)
        self.assertFalse(net.grad_enabled)
        self.assertFalse(net.input_requires_grad)


if __name__ == '__main__':
    unittest.main(verbosity=2)
