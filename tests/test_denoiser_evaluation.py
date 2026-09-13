"""Independent denoiser metrics, provenance and frozen-checkpoint regressions."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evaluate_tiny_denoiser', ROOT/'scripts/evaluate_tiny_denoiser.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class ShrinkSpy:
    """A denoiser with known closed-form output, never given the clean target."""
    sigma_data = 2.

    def __init__(self):
        self.calls = []

    def predict(self, x, sigma):
        self.calls.append((x.copy(), sigma))
        def forbidden_gradient(*_):
            raise AssertionError('Evaluation must not calculate training gradients')
        return self.sigma_data**2/(self.sigma_data**2+sigma**2)*x, forbidden_gradient


class DenoiserEvaluationTests(unittest.TestCase):
    def test_complex_energy_metric_has_the_real_coordinate_factor_of_two(self):
        clean = np.full((2, 36), 2.+0j)
        result = evaluation.scores(clean+(1+1j), clean)
        self.assertAlmostEqual(result['real_coordinate_mse'], 1., places=14)
        self.assertAlmostEqual(result['nrmse_db'], 10*np.log10(.5), places=13)
        self.assertEqual(evaluation.scores(clean, clean), {'nrmse_db': -300., 'real_coordinate_mse': 0.})
        zero_reference = evaluation.scores(clean, np.zeros_like(clean))
        self.assertIsNone(zero_reference['nrmse_db'])
        self.assertEqual(zero_reference['real_coordinate_mse'], 2.)

    def test_frozen_unit_noise_and_closed_form_shrink_without_gradients(self):
        clean = np.full((4, 36), 2.+1j)
        epsilon = np.tile(np.array([1+1j, -1+1j, 1-1j, -1-1j]), (4, 9))
        model = ShrinkSpy()
        rows = evaluation.evaluate_coefficients(clean, epsilon, [.1, 1.], model)
        for row, (received, sigma) in zip(rows, model.calls):
            self.assertEqual(received.shape, (4, 36, 1))
            np.testing.assert_allclose((received[:, :, 0]-clean)/sigma, epsilon, atol=2e-15)
            self.assertAlmostEqual(row['noisy']['real_coordinate_mse'], sigma**2, places=14)
            self.assertEqual(row['shrink_coefficient'], 4/(4+sigma**2))
            self.assertEqual(row['learned'], row['shrink'])
            self.assertEqual(row['learned_improvement_over_shrink_db'], 0.)
            self.assertEqual(row['learned_ties_vs_shrink'], 4)
            self.assertEqual(row['learned_win_fraction_vs_shrink'], 0.)

    def test_changed_reference_cannot_change_a_prediction_of_the_same_observation(self):
        first, second = ShrinkSpy(), ShrinkSpy()
        shape = (2, 36)
        row_a = evaluation.evaluate_coefficients(np.full(shape, 3+2j), np.zeros(shape), [1.], first)[0]
        row_b = evaluation.evaluate_coefficients(np.full(shape, 4+2j), -np.ones(shape), [1.], second)[0]
        np.testing.assert_array_equal(first.calls[0][0], second.calls[0][0])
        self.assertEqual(first.calls[0][1], second.calls[0][1])
        self.assertEqual(row_a['shrink_coefficient'], row_b['shrink_coefficient'])
        self.assertNotEqual(row_a['learned']['real_coordinate_mse'], row_b['learned']['real_coordinate_mse'])

    def test_rejects_invalid_sigmas_shapes_predictions_and_reused_seeds(self):
        clean = np.ones((2, 36), dtype=complex)
        for sigmas in ([0], [-1], [np.nan], [np.inf], [1, 1], [2, 1], []):
            with self.subTest(sigmas=sigmas), self.assertRaises(ValueError):
                evaluation.evaluate_coefficients(clean, clean, sigmas, ShrinkSpy())
        with self.assertRaises(ValueError):
            evaluation.evaluate_coefficients(clean, clean[:1], [1.], ShrinkSpy())
        for prediction in (np.ones((2, 36)), np.full((2, 36, 1), np.nan)):
            model = ShrinkSpy()
            model.predict = lambda x, sigma: (prediction, None)
            with self.subTest(shape=prediction.shape), self.assertRaises(ValueError):
                evaluation.evaluate_coefficients(clean, clean, [1.], model)
        for generator, noise in ((7319, 17320), (7320, 17320), (17319, 7321), (17319, 17319)):
            with self.subTest(generator=generator, noise=noise), self.assertRaises(ValueError):
                evaluation.generate_report(8, generator, noise)

    def test_numpy_only_generator_matches_training_source_fixture_and_repeats(self):
        # These values were frozen from importing train_tiny_prior.vectors in the
        # training runtime, before replacing that import with AST extraction.
        with patch.dict(sys.modules, {'torch': None}):
            clean, epsilon = evaluation.make_data(8, 17319, 17320)
            a = evaluation.generate_report(count=8)
            b = evaluation.generate_report(count=8)
        selected = [0, 1, 2, 3, 8, 35]
        expected_real = [-1.7401326386372316, 1.8089453950329397, 2.3588260526135856, -.8081742993190986, 1.461272753721094, -1.3478883899808094]
        expected_imag = [-2.713732437807214, .9979933436835345, -1.1793731453835004, 5.074204571788788, -4.569962535332427, 4.770144250384018]
        np.testing.assert_allclose(clean[0, selected], np.array(expected_real)+1j*np.array(expected_imag), rtol=1e-12, atol=1e-12)
        self.assertEqual(clean.shape, (8, 36))
        self.assertEqual(epsilon.shape, clean.shape)
        self.assertAlmostEqual(float(np.mean(np.abs(clean)**2)/2), 5.547214749041101, places=11)
        self.assertEqual(a['dataset'], b['dataset'])
        self.assertEqual(a['cases'], b['cases'])
        self.assertEqual(a['protocol']['sigma_values'], list(evaluation.SIGMAS))
        self.assertEqual(a['summary']['inference_sigma_count'], 9)
        self.assertEqual(a['summary']['sigma_count'], 10)
        self.assertTrue(a['model']['weights_checksum_verified'])
        weights = ROOT/'public/models/tiny-spatial-v1.npz'
        self.assertEqual(a['model']['weights_sha256'], hashlib.sha256(weights.read_bytes()).hexdigest())
        # There is no NaN or Infinity hidden anywhere in this small real-model run.
        json.dumps(a, allow_nan=False)

    def test_checkpoint_corruption_is_rejected_before_any_generator_execution(self):
        directory = ROOT/'public/models'
        before = hashlib.sha256((directory/'tiny-spatial-v1.npz').read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            for filename in ('tiny-spatial-v1.json', 'tiny-spatial-v1.npz'):
                shutil.copyfile(directory/filename, Path(temporary)/filename)
            with (Path(temporary)/'tiny-spatial-v1.npz').open('ab') as handle:
                handle.write(b'not the verified checkpoint')
            with patch.object(evaluation, 'make_data', side_effect=AssertionError('Do not generate for corrupt weights')):
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    evaluation.generate_report(8, model_directory=temporary)
        self.assertEqual(before, hashlib.sha256((directory/'tiny-spatial-v1.npz').read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
