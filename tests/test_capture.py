"""Independent tests of the app's capture baseline; app source is read-only.

Run from workspace root:
  work/adeps-test-lab-venv/bin/python -m unittest discover -s work/research -p test_capture_reference.py -v

Some strict-import tests deliberately fail until the app's validation is fixed.
They are not expected-failure decorators, so each becomes an ordinary regression
test when the application is corrected.
"""

import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np

APP = Path(__file__).resolve().parents[1] / "backend/capture.py"
SPEC = importlib.util.spec_from_file_location("capture_under_review", APP)
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


def make_bundle(*, reference=True, F=2, Q=4, C=4, T=12):
    rng = np.random.default_rng(3)
    v = np.broadcast_to(np.eye(Q, C), (F, Q, C)).astype(complex).copy()
    p = rng.normal(size=(F, Q, T)) + 1j * rng.normal(size=(F, Q, T))
    bundle = {
        "schema": "adeps-test-array-stft/1", "sh_ordering":"ACN", "sh_normalization":"N3D",
        "frequencies_hz": np.geomspace(100, 400, F).tolist(),
        "V_real": v.real.tolist(), "V_imag": v.imag.tolist(),
        "p_real": p.real.tolist(), "p_imag": p.imag.tolist(),
        "microphone_positions_m": [[0.06, 0, 0], [0, 0.06, 0], [-0.06, 0, 0], [0, 0, 0.06]][:Q],
        "provenance": "synthetic independent test fixture",
        "conventions": "real ACN/N3D; coherent complex frequency frames",
    }
    if reference:
        bundle.update(reference_real=p[:, :min(C, 4)].real.tolist(), reference_imag=p[:, :min(C, 4)].imag.tolist())
    return bundle


class CaptureMathTests(unittest.TestCase):
    def test_real_n3d_foa_acn_xyz_components_and_normalization(self):
        directions = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, -2, -3]], float)
        unit = directions / np.linalg.norm(directions, axis=1, keepdims=True)
        expected = np.c_[np.ones(len(unit)), np.sqrt(3) * unit[:, 1], np.sqrt(3) * unit[:, 2], np.sqrt(3) * unit[:, 0]]
        actual = capture.real_n3d(1, directions)
        np.testing.assert_allclose(actual, expected, atol=1e-14)

    def test_addition_theorem_real_n3d_higher_orders(self):
        directions = [[1, 0.3, -0.2], [-0.4, -0.2, 0.8], [0, 1, 0]]
        actual = capture.real_n3d(3, directions)
        for degree in range(4):
            np.testing.assert_allclose(np.sum(actual[:, degree ** 2:(degree + 1) ** 2] ** 2, axis=1), 2 * degree + 1, atol=1e-13)

    def test_free_field_modal_expansion_matches_declared_plane_wave_sign(self):
        # Degree 12 converges rapidly for this low-frequency/radius fixture.
        positions = np.array([[0.06, 0, 0], [0, -0.06, 0], [0.02, 0.03, 0.04]])
        direction = np.array([0.8, 0.45, 0.3]); direction /= np.linalg.norm(direction)
        frequencies = np.array([100., 500.])
        v = capture.modal_matrix(frequencies, positions, 12)
        coefficients = capture.real_n3d(12, direction[None])[0]
        actual = v @ coefficients
        expected = np.exp(2j * np.pi * frequencies[:, None] * (positions @ direction)[None] / 343.)
        np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_high_snr_matched_synthetic_model_is_low_error_and_finite(self):
        result = capture.run_capture({"snr_db": 80, "mismatch": False, "regularization": 1e-8})
        self.assertEqual(result["rank_min"], 4)
        self.assertLess(result["quality"]["complex_nrmse_db"], -50)
        self.assertGreater(result["quality"]["coherence"], 0.9999)
        self.assertIsNone(result["quality"]["si_sdr_db"])
        json.dumps(result, allow_nan=False)

    def test_coplanar_array_loses_vertical_foa_rank(self):
        result = capture.run_capture({"snr_db": 80, "mismatch": False, "regularization": 1e-8, "coplanar": True})
        self.assertEqual(result["rank_min"], 3)
        self.assertTrue(all(value == 3 for value in result["rank_by_frequency"]))
        self.assertGreater(result["quality"]["complex_nrmse_db"], -20)
        self.assertTrue(all(value is None for value in result["curves"]["condition"]))

    def test_missing_reference_does_not_claim_reconstruction_quality(self):
        result = capture.run_capture({"bundle": make_bundle(reference=False)})
        self.assertFalse(result["quality"]["reference_available"])
        for metric in ["complex_nrmse_db", "coherence", "si_sdr_db"]:
            self.assertIsNone(result["quality"][metric])
        self.assertNotIn("error_db", result["curves"])
        self.assertNotIn("coherence", result["curves"])

    def test_identity_import_encoding_has_expected_ridge_bias(self):
        result = capture.run_capture({"bundle": make_bundle(), "regularization": 1e-8})
        self.assertLess(result["quality"]["complex_nrmse_db"], -150)
        self.assertGreater(result["quality"]["coherence"], 1 - 1e-12)
        json.dumps(result, allow_nan=False)

    def test_coherence_does_not_hide_gain_error_in_nrmse(self):
        bundle = make_bundle()
        bundle["p_real"] = (np.array(bundle["p_real"]) * 2).tolist()
        bundle["p_imag"] = (np.array(bundle["p_imag"]) * 2).tolist()
        result = capture.run_capture({"bundle": bundle, "regularization": 1e-8})
        self.assertAlmostEqual(result["quality"]["complex_nrmse_db"], 0, places=5)
        self.assertGreater(result["quality"]["coherence"], 1 - 1e-12)

    def test_mismatched_reference_and_non_square_coefficients_reject(self):
        bad_reference = make_bundle()
        bad_reference["reference_real"] = np.zeros((2, 3, 12)).tolist()
        bad_reference["reference_imag"] = np.zeros((2, 3, 12)).tolist()
        with self.assertRaises(ValueError):
            capture.run_capture({"bundle": bad_reference})
        with self.assertRaises(ValueError):
            capture.run_capture({"bundle": make_bundle(reference=False, C=3)})

    def test_nan_data_and_invalid_regularization_reject(self):
        bundle = make_bundle()
        bundle["p_real"][0][0][0] = float("nan")
        with self.assertRaises(ValueError):
            capture.run_capture({"bundle": bundle})
        for invalid in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                capture.run_capture({"regularization": invalid})


class CaptureStrictImportTests(unittest.TestCase):
    def test_empty_import_bundle_must_not_silently_run_synthetic_demo(self):
        with self.assertRaises(ValueError):
            capture.run_capture({"bundle": {}})

    def test_frequency_array_must_be_one_dimensional(self):
        bundle = make_bundle()
        bundle["frequencies_hz"] = [[100], [400]]
        with self.assertRaises(ValueError):
            capture.run_capture({"bundle": bundle})

    def test_empty_time_axis_must_reject(self):
        with self.assertRaises(ValueError):
            capture.run_capture({"bundle": make_bundle(reference=False, T=0)})

    def test_silent_reference_has_no_defined_normalized_quality(self):
        bundle = make_bundle()
        for key in ["p_real", "p_imag", "reference_real", "reference_imag"]:
            bundle[key] = np.zeros((2, 4, 12)).tolist()
        try:
            result = capture.run_capture({"bundle": bundle})
        except ValueError:
            return  # Clear rejection is also scientifically valid.
        self.assertIsNone(result["quality"]["complex_nrmse_db"])
        self.assertIsNone(result["quality"]["coherence"])

    def test_zero_energy_reference_frequency_is_marked_undefined(self):
        bundle = make_bundle()
        for key in ["p_real", "p_imag", "reference_real", "reference_imag"]:
            bundle[key][0] = np.zeros((4, 12)).tolist()
        try:
            result = capture.run_capture({"bundle": bundle})
        except ValueError:
            return
        self.assertIsNone(result["curves"]["error_db"][0])
        self.assertIsNone(result["curves"]["coherence"][0])

    def test_unobservable_coefficient_space_is_not_given_finite_inverse_condition(self):
        result = capture.run_capture({"bundle": make_bundle(reference=False, Q=4, C=9)})
        self.assertEqual(result["rank_min"], 4)
        self.assertTrue(all(value is None for value in result["curves"]["condition"]),
                        "V has 9 coefficient columns but rank 4; retained-spectrum condition=1 is not the inverse condition")

    def test_nonfinite_or_malformed_positions_reject(self):
        for positions in [[[float("nan"), 0, 0]] * 4, [[0.06, 0]] * 4, [[0.06, 0, 0]] * 3]:
            bundle = make_bundle()
            bundle["microphone_positions_m"] = positions
            with self.assertRaises(ValueError):
                capture.run_capture({"bundle": bundle})


if __name__ == "__main__":
    unittest.main()
