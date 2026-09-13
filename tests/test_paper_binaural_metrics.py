"""CPU analytic fixtures for separately versioned binaural proxy evaluation."""
from __future__ import annotations

import json
import unittest

import numpy as np

from paper_binaural_metrics import (FREQUENCIES, binaural_cues, coefficient_sha256,
                                    erb_bands, evaluate_binaural, load_decoder,
                                    render_binaural)


class BinauralMetricTests(unittest.TestCase):
    def setUp(self):
        # Memory-only test decoder: W is left and Y is right. Never distributed
        # or described as measured HRTFs.
        matrix = np.zeros((257, 2, 4), complex)
        matrix[:, 0, 0] = 1
        matrix[:, 1, 1] = 1
        self.decoder = {'matrix': matrix, 'metadata': {'id': 'analytic-test-fixture-not-HRTF'}}
        rng = np.random.default_rng(32619)
        x = rng.normal(size=(257, 32)) + 1j * rng.normal(size=(257, 32))
        x[[0, -1]] = x[[0, -1]].real
        self.reference = np.zeros((257, 4, 32), complex)
        self.reference[:, 0] = x
        self.reference[:, 1] = x

    def score(self, estimate, reference=None, **kwargs):
        return evaluate_binaural(estimate, self.reference if reference is None else reference,
                                  FREQUENCIES, decoder=self.decoder, **kwargs)

    def test_identical_signals_have_zero_error_and_json_is_finite(self):
        result = self.score(self.reference)
        self.assertEqual(result['metrics'], {'ild_error_db': 0., 'ic_error': 0.,
                                            'ic_signed_zero_lag_error': 0., 'status': 'defined'})
        self.assertEqual(result['details']['reference_active_band_count'], 32)
        json.dumps(result, allow_nan=False)

    def test_known_left_gain_changes_ild_by_six_db_without_changing_ic(self):
        estimate = self.reference.copy()
        estimate[:, 0] *= 2
        result = self.score(estimate)
        self.assertAlmostEqual(result['metrics']['ild_error_db'], 20 * np.log10(2), places=12)
        self.assertAlmostEqual(result['metrics']['ic_error'], 0, places=12)
        self.assertAlmostEqual(result['metrics']['ic_signed_zero_lag_error'], 0, places=12)

    def test_lag_peak_is_distinct_from_signed_zero_lag_and_squared_coherence(self):
        # At 1 kHz a four-sample delay at 16 kHz has a quarter-cycle phase.
        reference = np.zeros_like(self.reference)
        reference[32, :2] = 1
        estimate = reference.copy()
        estimate[32, 1] = -1j
        result = self.score(estimate, reference)
        self.assertAlmostEqual(result['metrics']['ic_error'], 0., places=12)
        self.assertAlmostEqual(result['metrics']['ic_signed_zero_lag_error'], 1., places=12)
        self.assertEqual(result['details']['reference_active_band_count'], 1)
        # A polarity inversion is not erased with abs() or squaring.
        estimate[32, 1] = -1
        result = self.score(estimate, reference)
        self.assertAlmostEqual(result['metrics']['ic_signed_zero_lag_error'], 2., places=12)

    def test_missing_estimate_ear_or_band_invalidates_whole_scalar(self):
        estimate = self.reference.copy()
        estimate[32:40, 1] = 0
        # All-zero estimate is not treated as perfect coherence or ignored.
        result = self.score(np.zeros_like(estimate))
        self.assertEqual(result['metrics']['status'], 'undefined_required_band')
        self.assertIsNone(result['metrics']['ild_error_db'])
        self.assertIsNone(result['metrics']['ic_error'])
        self.assertEqual(result['details']['reference_active_band_count'], 32)
        self.assertEqual(result['details']['valid_band_count'], 0)
        # One failed reference-active band must not be omitted from the mean.
        band = erb_bands()
        estimate = self.reference.copy()
        estimate[band['weights'][10] > 0, 1] = 0
        result = self.score(estimate)
        self.assertEqual(result['details']['valid_band_count'], 31)
        self.assertIsNone(result['metrics']['ic_error'])

    def test_silent_reference_produces_explicit_undefined_not_zero(self):
        result = self.score(self.reference, np.zeros_like(self.reference))
        self.assertEqual(result['metrics']['status'], 'zero_reference')
        self.assertTrue(all(v is None for v in result['curves']['ic_error']))
        json.dumps(result, allow_nan=False)

    def test_finite_subnormal_audio_is_not_misclassified_as_silence(self):
        for scale in (1e-310, 1e-320):
            with np.errstate(over='raise', invalid='raise'):
                cues = binaural_cues(np.full((257, 2, 32), scale, dtype=complex))
            self.assertTrue(cues['both_ears_active'].all())
            np.testing.assert_allclose(cues['ic_lag_peak'], 1., atol=1e-14)
            np.testing.assert_allclose(cues['ic_signed_zero_lag'], 1., atol=1e-14)
            np.testing.assert_array_equal(cues['ild_db'], 0.)

    def test_common_scale_invariance_and_no_higher_order_oracle_use(self):
        estimate = self.reference.copy()
        estimate[:, 0] *= 1.7
        base = self.score(estimate)['metrics']
        for scale in (1e-120, 1e120):
            result = self.score(estimate * scale, self.reference * scale)['metrics']
            for key in ('ild_error_db', 'ic_error', 'ic_signed_zero_lag_error'):
                self.assertAlmostEqual(base[key], result[key], places=11)
        full = np.concatenate((estimate, np.full((257, 32, 32), 1000.)), axis=1)
        self.assertEqual(self.score(full)['metrics'], base)

    def test_erb_grouping_covers_requested_available_bins_once_and_retains_nyquist(self):
        bands = erb_bands()
        covered = (bands['weights'] > 0).sum(axis=0)
        np.testing.assert_array_equal(covered, (FREQUENCIES >= 100).astype(int))
        self.assertTrue(np.all(bands['bin_counts'] > 0))
        self.assertEqual(int(bands['bin_counts'].sum()), 253)
        self.assertEqual(bands['weights'][-1, -1] > 0, True)
        self.assertTrue(np.all(bands['weights'][:, 0] == 0))
        self.assertEqual(FREQUENCIES[np.flatnonzero(covered)[0]], 125.)

    def test_nonfinite_or_wrong_grid_is_rejected_not_reported_success(self):
        bad = self.reference.copy(); bad[100, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            self.score(bad)
        with self.assertRaises(ValueError):
            render_binaural(self.reference, FREQUENCIES + 1, decoder=self.decoder)
        with self.assertRaises(ValueError):
            self.score(self.reference, bands=True)
        with self.assertRaises(ValueError):
            binaural_cues(np.zeros((257, 2, 32)), lag_limit_ms=float('nan'))

    def test_shipped_ku100_asset_checksum_real_endpoints_and_orientation(self):
        decoder = load_decoder()
        self.assertEqual(decoder['metadata']['coefficient_sha256'], coefficient_sha256(decoder['matrix']))
        self.assertEqual(decoder['metadata']['license']['spdx'], 'Apache-2.0')
        self.assertEqual(decoder['metadata']['source']['subject'], 'D1 Neumann KU100')
        matrix = decoder['matrix']
        self.assertTrue(np.all(matrix[[0, -1]].imag == 0))
        # Real N3D plane waves: [W,Y,Z,X] = [1,sqrt(3)*dy,sqrt(3)*dz,sqrt(3)*dx].
        left = matrix[32] @ np.array([1, np.sqrt(3), 0, 0])
        right = matrix[32] @ np.array([1, -np.sqrt(3), 0, 0])
        self.assertGreater(abs(left[0]), abs(left[1]))
        self.assertGreater(abs(right[1]), abs(right[0]))


if __name__ == '__main__':
    unittest.main()
