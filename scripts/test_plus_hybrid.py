"""CPU-only contract checks for the independent hybrid, without trained weights.

All fixtures are generated in memory. A deterministic stand-in replaces the
frozen-network call; these tests are not model-quality or paper benchmarks.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from capture import encode
from neural import compress, expand
import plus_hybrid as hybrid
from plus_consistency import project_stft, reconstruct as consistency
from plus_reconstruction import proximal_correction


def real_endpoints(value):
    value = value.copy()
    value[[0, -1]] = value[[0, -1]].real
    return value


class HybridTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(81742)
        self.f = np.fft.rfftfreq(512, 1 / 16000)
        # Deliberately rank-limited nontrivial complex observation map. The
        # arbitrary spectra exercise algebra without pretending to be speech.
        self.v = real_endpoints((rng.normal(size=(257, 4, 36)) +
                                1j * rng.normal(size=(257, 4, 36))) / 6)
        self.p = real_endpoints((rng.normal(size=(257, 4, 4)) +
                                1j * rng.normal(size=(257, 4, 4))) * .02)
        self.initial = real_endpoints((rng.normal(size=(257, 36, 4)) +
                                      1j * rng.normal(size=(257, 36, 4))) * .006)
        self.prior = SimpleNamespace(std=1.13679, card={
            'configuration': {'sample_rate_hz': 16000, 'n_fft': 512, 'hop': 128},
            'model': {'id': 'CPU-test-stand-in-only'}})

    def spatial(self, p, v, frequencies, **kwargs):
        return {'estimate': self.initial.copy(), 'diagnostics': {
            'oracle_used': False, 'test_fixture_only': True}}

    @staticmethod
    def denoise(prior, x, sigma):
        # Non-identity complex perturbation tests normalization, the nonlinear
        # inverse and the array-nullspace component independently of weights.
        return x * (.8 + .03j) / (1 + .02 * sigma)

    def manual(self, steps=3, sigma_start=1., relaxation=.25,
               use_stft_consistency=False, ridge_relative=1e-7):
        linear = real_endpoints(encode(self.v, self.p, 1e-7)[0])
        scale = np.sqrt(np.mean(abs(linear[:, :1])**2))
        a = self.initial.copy()
        sigma = np.linspace(sigma_start**.1, .002**.1, steps)**10
        sigma[0], sigma[-1] = sigma_start, .002
        inputs = []
        for level in sigma:
            if relaxation:
                x = compress(a / scale) / self.prior.std
                inputs.append(x.copy())
                d = real_endpoints(expand(self.prior.std * self.denoise(self.prior, x, level)) * scale)
                a = a + relaxation * (d - a)
            if use_stft_consistency:
                a = project_stft(a)
            # This deliberately calls the public solver afresh rather than
            # sharing hybrid's cached correction matrix.
            a = real_endpoints(proximal_correction(a, self.p, self.v,
                                                 ridge_relative=ridge_relative)[0])
        return a, linear, scale, inputs

    def run_hybrid(self, **kwargs):
        with patch.object(hybrid, 'reconstruct_spatial', side_effect=self.spatial), \
             patch.object(hybrid, '_denoise_no_grad', side_effect=self.denoise):
            return hybrid.reconstruct(self.p, self.v, self.f, self.prior, **kwargs)

    def test_manual_complex_loop_fixed_scale_nfe_and_input_preservation(self):
        expected, linear, scale, expected_inputs = self.manual(steps=3, ridge_relative=.03)
        p, v, initial = self.p.copy(), self.v.copy(), self.initial.copy()
        with patch.object(hybrid, 'reconstruct_spatial', side_effect=self.spatial) as spatial, \
             patch.object(hybrid, '_denoise_no_grad', side_effect=self.denoise) as denoise, \
             patch.object(hybrid, 'project_stft', side_effect=AssertionError('Unexpected projection')), \
             patch.object(hybrid, 'joint_consistency', side_effect=AssertionError('Unexpected final pass')):
            actual = hybrid.reconstruct(self.p, self.v, self.f, self.prior, steps=3, ridge_relative=.03)
        np.testing.assert_allclose(actual['estimate'], expected, atol=2e-17, rtol=3e-13)
        np.testing.assert_array_equal(actual['linear'], linear)
        np.testing.assert_array_equal(actual['spatial'], initial)
        np.testing.assert_array_equal(self.p, p)
        np.testing.assert_array_equal(self.v, v)
        self.assertFalse(np.shares_memory(actual['estimate'], actual['spatial']))
        self.assertEqual(actual['diagnostics']['observation_rms_scale'], scale)
        self.assertEqual(actual['nfe'], 3)
        self.assertEqual(denoise.call_count, 3)
        self.assertEqual(actual['trace'][0]['sigma'], 1.)
        self.assertEqual(actual['trace'][-1]['sigma'], .002)
        self.assertIsNone(actual['trace'][-1]['next_sigma'])
        self.assertEqual([row['nfe'] for row in actual['trace']], [1, 2, 3])
        self.assertTrue(all(row['model_call'] for row in actual['trace']))
        for call, x in zip(denoise.call_args_list, expected_inputs):
            np.testing.assert_allclose(call.args[1], x, atol=3e-13, rtol=3e-13)
        self.assertEqual(spatial.call_args.kwargs, hybrid.SPATIAL_DEFAULTS)
        self.assertFalse(actual['configuration']['exact_dps'])
        self.assertFalse(actual['configuration']['reference_used'])
        self.assertFalse(actual['configuration']['final_stft_projection'])
        json.dumps({key: actual[key] for key in ('configuration', 'diagnostics', 'trace')}, allow_nan=False)

    def test_zero_relaxation_skips_network_but_keeps_stft_and_proximal_steps(self):
        expected, _, _, _ = self.manual(steps=4, relaxation=0., use_stft_consistency=True)
        with patch.object(hybrid, 'reconstruct_spatial', side_effect=self.spatial), \
             patch.object(hybrid, '_denoise_no_grad', side_effect=AssertionError('Must not call model')) as denoise, \
             patch.object(hybrid, 'project_stft', wraps=project_stft) as project:
            actual = hybrid.reconstruct(self.p, self.v, self.f, self.prior,
                                        steps=4, relaxation=0., use_stft_consistency=True)
        np.testing.assert_allclose(actual['estimate'], expected, atol=3e-17, rtol=3e-13)
        self.assertEqual(denoise.call_count, 0)
        self.assertEqual(project.call_count, 4)
        self.assertEqual(actual['nfe'], 0)
        self.assertEqual(len(actual['trace']), 4)
        for row in actual['trace']:
            self.assertFalse(row['model_call'])
            self.assertEqual(row['nfe'], 0)
            self.assertEqual(row['denoiser_update_norm'], 0.)
            self.assertEqual(row['relaxed_denoiser_update_norm'], 0.)
        self.assertFalse(actual['diagnostics']['learned_perturbation_enabled'])
        self.assertGreater(actual['diagnostics']['total_change_from_spatial_norm'], 0.)

    def test_optional_final_consistency_is_separate_and_reported(self):
        after_loop, _, _, _ = self.manual(steps=2)
        expected = consistency(self.p, self.v, self.f, initial=after_loop,
                               iterations=3, ridge_relative=1e-7)
        actual = self.run_hybrid(steps=2, stft_iterations=3)
        np.testing.assert_allclose(actual['estimate'], expected['estimate'], atol=4e-17, rtol=8e-13)
        self.assertEqual(actual['nfe'], 2)
        self.assertEqual(len(actual['trace']), 2)
        self.assertTrue(actual['configuration']['final_stft_projection'])
        self.assertEqual(actual['configuration']['final_stft_iterations'], 3)
        post = actual['diagnostics']['final_consistency']
        self.assertEqual(len(post['trace']), 3)
        self.assertNotIn('estimate', post)
        np.testing.assert_allclose(project_stft(actual['estimate']), actual['estimate'], atol=5e-17)
        json.dumps(post, allow_nan=False)

    def test_deterministic_coefficients_and_observation_scaling(self):
        first = self.run_hybrid(steps=2, use_stft_consistency=True)
        second = self.run_hybrid(steps=2, use_stft_consistency=True)
        np.testing.assert_array_equal(first['estimate'], second['estimate'])
        scale_factor = 3.25
        self.p *= scale_factor
        self.initial *= scale_factor
        scaled = self.run_hybrid(steps=2, use_stft_consistency=True)
        np.testing.assert_allclose(scaled['estimate'], scale_factor * first['estimate'], atol=1e-16, rtol=5e-13)
        self.assertAlmostEqual(scaled['diagnostics']['observation_rms_scale'],
                               scale_factor * first['diagnostics']['observation_rms_scale'])

    def test_invalid_input_and_options_fail_before_network(self):
        with patch.object(hybrid, '_denoise_no_grad', side_effect=AssertionError('Should reject first')):
            for kwargs in ({'steps': 1}, {'steps': True}, {'sigma_start': 0.},
                           {'relaxation': float('nan')}, {'relaxation': -.1},
                           {'ridge_relative': float('inf')}, {'stft_iterations': -1},
                           {'use_stft_consistency': 1}, {'spatial_config': {'oracle': True}}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    hybrid.reconstruct(self.p, self.v, self.f, self.prior, **kwargs)
            for target in ('p', 'v'):
                bad = getattr(self, target).copy()
                bad[0, 0, 0] += .01j
                with self.subTest(target=target), self.assertRaises(ValueError):
                    hybrid.reconstruct(bad if target == 'p' else self.p,
                                        bad if target == 'v' else self.v, self.f, self.prior)
            bad_p = self.p.copy()
            bad_p[5, 1, 1] = np.nan
            with self.assertRaises(ValueError):
                hybrid.reconstruct(bad_p, self.v, self.f, self.prior)
            with self.assertRaises(ValueError):
                hybrid.reconstruct(self.p, self.v, self.f + .1, self.prior)
            with self.assertRaises(ValueError):
                hybrid.reconstruct(np.zeros_like(self.p), self.v, self.f, self.prior)
            self.prior.std = 0.
            with self.assertRaises(ValueError):
                hybrid.reconstruct(self.p, self.v, self.f, self.prior)

    def test_malformed_denoiser_output_is_not_reported_as_success(self):
        with patch.object(hybrid, 'reconstruct_spatial', side_effect=self.spatial):
            for bad in (np.zeros((257, 4, 4)), np.full((257, 36, 4), np.nan)):
                with self.subTest(shape=bad.shape), \
                     patch.object(hybrid, '_denoise_no_grad', return_value=bad), \
                     self.assertRaisesRegex(ValueError, 'Frozen denoiser'):
                    hybrid.reconstruct(self.p, self.v, self.f, self.prior, steps=2)

    def test_real_spatial_cpu_initialization_uses_only_observations(self):
        with patch.object(hybrid, '_denoise_no_grad', side_effect=self.denoise):
            result = hybrid.reconstruct(self.p, self.v, self.f, self.prior,
                                         steps=2, relaxation=0.)
        self.assertTrue(np.all(np.isfinite(result['estimate'])))
        self.assertTrue(np.all(result['estimate'][[0, -1]].imag == 0))
        self.assertFalse(result['diagnostics']['spatial']['oracle_used'])
        self.assertEqual(result['configuration']['spatial_configuration']['noise_snr_db'], 50.)
        self.assertEqual(result['nfe'], 0)
        json.dumps(result['diagnostics'], allow_nan=False)


if __name__ == '__main__':
    unittest.main()
