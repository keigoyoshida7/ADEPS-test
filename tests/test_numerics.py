"""Scientific invariant/edge-case tests; run with python -m unittest discover."""

import json
import unittest

import numpy as np

from numerics import (
    evaluate_transfer, ir_diagnostics, ir_to_transfer, regularized_mimo,
    run_demo, synthetic_transfer, to_jsonable,
)


class MimoReferenceTests(unittest.TestCase):
    def setUp(self):
        self.eye = np.broadcast_to(np.eye(3, dtype=complex), (2, 3, 3)).copy()

    def test_identity_maps_to_identity_without_regularization(self):
        fit = regularized_mimo(self.eye, self.eye, lambda_relative=0, max_column_norm=None)
        np.testing.assert_allclose(fit["G"], self.eye, atol=1e-14)
        self.assertTrue(np.all(fit["rank"] == 3))

    def test_ridge_matches_closed_form_for_scaled_identity(self):
        fit = regularized_mimo(2 * self.eye, self.eye, 0.1, None)
        np.testing.assert_allclose(fit["lambda_absolute"], 0.4)
        np.testing.assert_allclose(fit["G"], self.eye * (2 / 4.4), atol=1e-14)

    def test_known_gain_delay_correction_improves_independent_points(self):
        # Full-column-rank training identifies a shared electronics fault.
        # Held-out transfer rows are independently drawn and never fitted.
        rng = np.random.default_rng(25)
        target_train = rng.normal(size=(5, 8, 3)) + 1j * rng.normal(size=(5, 8, 3))
        target_test = rng.normal(size=(5, 4, 3)) + 1j * rng.normal(size=(5, 4, 3))
        electronic = np.array([0.5 * np.exp(-0.7j), 1.3 * np.exp(0.3j), 0.8 * np.exp(-1.1j)])
        h_train = target_train * electronic[None, None, :]
        h_test = target_test * electronic[None, None, :]
        fit = regularized_mimo(h_train, target_train, 1e-8, None)
        metrics = evaluate_transfer(h_test, target_test, fit["G"])
        self.assertGreater(metrics["improvement_db"], 100)
        np.testing.assert_allclose(fit["G"], np.broadcast_to(np.diag(1 / electronic), (5, 3, 3)), atol=1e-6)

    def test_heldout_failure_is_not_hidden_in_underdetermined_case(self):
        training = np.array([[[1, 0]]], dtype=complex)
        heldout = np.array([[[0, 1]]], dtype=complex)
        fit = regularized_mimo(training, training, 0, None)
        result = evaluate_transfer(heldout, heldout, fit["G"])
        self.assertLess(result["improvement_db"], 0)
        self.assertEqual(result["corrected_nrmse_db"], 0)
        self.assertTrue(np.isinf(fit["gram_condition_number"][0]))
        self.assertEqual(fit["rank"][0], 1)

    def test_rank_deficient_and_all_zero_matrices_are_finite(self):
        for H in (np.ones((2, 2, 3), complex), np.zeros((2, 2, 3), complex)):
            for ridge in (0, 0.1):
                fit = regularized_mimo(H, np.ones((2, 2, 3)), ridge, 2)
                self.assertTrue(np.isfinite(fit["G"]).all())
                self.assertTrue(np.isinf(fit["gram_condition_number"]).all())

    def test_column_cap_applies_to_total_drive_norm(self):
        fit = regularized_mimo(self.eye * 0.1, self.eye, 0, 2)
        np.testing.assert_allclose(fit["column_norm_before_cap"], 10)
        np.testing.assert_allclose(fit["column_norm_after_cap"], 2)
        np.testing.assert_allclose(fit["column_cap_multiplier"], 0.2)

    def test_relative_ridge_is_invariant_to_common_measurement_scale(self):
        fit1 = regularized_mimo(self.eye, self.eye, 0.02, None)
        fit2 = regularized_mimo(self.eye * 1e-5, self.eye * 1e-5, 0.02, None)
        np.testing.assert_allclose(fit1["G"], fit2["G"], rtol=1e-13)

    def test_invalid_inputs_reject(self):
        for ridge in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                regularized_mimo(self.eye, self.eye, ridge)
        for cap in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                regularized_mimo(self.eye, self.eye, max_column_norm=cap)
        invalid = self.eye.copy()
        invalid[0, 0, 0] = complex(float("nan"), 0)
        with self.assertRaises(ValueError):
            regularized_mimo(invalid, self.eye)
        with self.assertRaises(ValueError):
            regularized_mimo(self.eye, self.eye[:, :2])
        with self.assertRaises(ValueError):
            evaluate_transfer(self.eye, self.eye * 0, self.eye)

    def test_direct_geometric_model_gain_and_delay(self):
        frequencies = np.array([100., 1000.])
        speakers = [[2, 2, 2]]
        points = [[3, 2, 2]]
        response = synthetic_transfer(frequencies, speakers, points, reflection=0, gains_db=[6.020599913279624], delays_ms=[2])
        expected = 2 * np.exp(-2j * np.pi * frequencies * (1 / 343 + 0.002))
        np.testing.assert_allclose(response[:, 0, 0], expected, atol=1e-13)
        with self.assertRaises(ValueError):
            synthetic_transfer(frequencies, speakers, speakers)
        with self.assertRaises(ValueError):
            synthetic_transfer([0, 100], speakers, points)
        with self.assertRaises(ValueError):
            synthetic_transfer(frequencies, speakers, points, reflection=-0.1)

    def test_ir_exact_dtft_and_onset_preserve_time_origin(self):
        ir = np.zeros((2, 3, 128))
        ir[:, :, 7] = 0.5
        frequencies = np.array([80., 1234.5, 8000.])
        h = ir_to_transfer(ir, 48000, frequencies)
        expected = 0.5 * np.exp(-2j * np.pi * frequencies * 7 / 48000)
        np.testing.assert_allclose(h, np.broadcast_to(expected[:, None, None], (3, 2, 3)), atol=1e-13)
        diagnostic = ir_diagnostics(ir, 48000)
        np.testing.assert_allclose(diagnostic["onset_ms"], 7 / 48)
        np.testing.assert_allclose(diagnostic["energy"], 0.25)
        silent = ir_diagnostics(ir * 0, 48000)
        self.assertTrue(np.isnan(silent["onset_ms"]).all())
        with self.assertRaises(ValueError):
            ir_to_transfer(ir, 0, frequencies)
        with self.assertRaises(ValueError):
            ir_to_transfer(ir, 48000, [25000])

    def test_demo_is_reproducible_strict_json_and_contains_unseen_points(self):
        demo = run_demo()
        encoded = json.dumps(demo, allow_nan=False)
        self.assertEqual(encoded, json.dumps(run_demo(), allow_nan=False))
        self.assertEqual(len(demo["frequencies_hz"]), 64)
        self.assertEqual(len(demo["geometry"]["speakers_m"]), 12)
        train = np.array(demo["geometry"]["training_points_m"])
        held = np.array(demo["geometry"]["heldout_points_m"])
        self.assertGreater(np.linalg.norm(train[:, None] - held[None], axis=2).min(), 0.05)
        self.assertEqual(len(demo["regularization_tradeoff"]), 6)
        self.assertIsNone(to_jsonable(float("inf")))
        self.assertEqual(len(demo["heatmaps"]["G"]["magnitude_db"]), 64)


if __name__ == "__main__":
    unittest.main()
