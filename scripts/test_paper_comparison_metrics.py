"""Analytic CPU fixtures for published equations and declared zero sensitivity."""
import json
import math
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from paper_comparison_metrics import evaluate_paper_spectra, real_wave_foa


F = np.fft.rfftfreq(512, 1 / 16000)


class PaperMetricTests(unittest.TestCase):
    def test_known_channel_gains_use_equal_channels_and_mean_log_not_log_mean(self):
        reference = np.ones((257, 4, 32), complex)
        estimate = reference * np.array([1., 2., 4., 8.])[None, :, None]
        result = evaluate_paper_spectra(estimate, reference, F)
        expected = 20 * math.log10(2) * 1.5
        self.assertAlmostEqual(result['metrics']['spectral_error_db'], expected, places=12)
        self.assertAlmostEqual(result['metrics']['coherence'], 1., places=12)
        self.assertAlmostEqual(result['sensitivity']['metrics']['spectral_error_db'], expected, places=12)
        self.assertEqual(len(result['curves']['coherence']), 257)

    def test_time_sum_before_squaring_distinguishes_orthogonality_from_phase(self):
        reference = np.ones((257, 4, 32), complex)
        orthogonal = reference * np.tile([1., -1.], 16)[None, None, :]
        result = evaluate_paper_spectra(orthogonal, reference, F)
        self.assertEqual(result['metrics']['spectral_error_db'], 0.)
        self.assertEqual(result['metrics']['coherence'], 0.)
        phase = evaluate_paper_spectra(1j * reference, reference, F)
        self.assertEqual(phase['metrics']['spectral_error_db'], 0.)
        self.assertAlmostEqual(phase['metrics']['coherence'], 1., places=12)
        orthogonal[:, 0] = 1.
        # One coherent channel out of four remains 1/4 even with a large
        # channel-specific signal amplitude. No pooled-energy substitute.
        reference[:, 0] *= 1000.
        orthogonal[:, 0] *= 1000.
        partial = evaluate_paper_spectra(orthogonal, reference, F)
        self.assertAlmostEqual(partial['metrics']['coherence'], .25, places=12)

    def test_endpoint_missing_estimate_has_separate_strict_and_sensitivity_results(self):
        reference = np.ones((257, 4, 32), complex)
        estimate = reference.copy(); estimate[[0, -1], 1:] = 0
        result = evaluate_paper_spectra(estimate, reference, F)
        self.assertIsNone(result['metrics']['spectral_error_db'])
        self.assertIsNone(result['metrics']['coherence'])
        self.assertEqual(result['details']['spectral_error_status_by_frequency'][0], 'positive_infinity_one_zero_magnitude')
        self.assertEqual(result['details']['coherence_status_by_frequency'][0], 'undefined_zero_estimate_channel')
        operational = result['sensitivity']
        self.assertAlmostEqual(operational['curves']['spectral_error_db'][0], 90.)
        self.assertAlmostEqual(operational['curves']['coherence'][0], .25, places=12)
        self.assertAlmostEqual(operational['metrics']['spectral_error_db'], 180 / 257, places=12)
        self.assertAlmostEqual(operational['metrics']['coherence'], (255 + .5) / 257, places=12)
        self.assertEqual(operational['details']['counts']['zero_estimate_reference_active_channels_by_frequency'][0], 3)
        self.assertEqual(operational['details']['floor_relative_db'], -120.)

    def test_zero_reference_channel_is_never_dropped_or_given_perfect_coherence(self):
        reference = np.ones((257, 4, 32), complex); reference[:, 3] = 0
        estimate = reference.copy()
        result = evaluate_paper_spectra(estimate, reference, F)
        self.assertIsNone(result['metrics']['spectral_error_db'])
        self.assertEqual(result['details']['spectral_error_status_by_frequency'][0], 'undefined_zero_over_zero')
        for profile in (result, result['sensitivity']):
            self.assertIsNone(profile['metrics']['coherence'])
            self.assertIsNone(profile['details']['coherence_by_channel'][0][3])
            self.assertEqual(profile['details']['counts']['channels'], 4)
        self.assertEqual(result['sensitivity']['metrics']['spectral_error_db'], 0.)
        silent = evaluate_paper_spectra(np.zeros_like(estimate), np.zeros_like(reference), F)
        self.assertIsNone(silent['sensitivity']['metrics']['spectral_error_db'])
        self.assertEqual(silent['sensitivity']['details']['floor_absolute_status'], 'no_nonzero_reference')
        json.dumps(silent, allow_nan=False)

    def test_floor_is_reference_common_and_tiny_magnitudes_are_explicitly_clipped(self):
        reference = np.ones((257, 4, 32), complex); reference[4, 0, 0] = 1e-9
        first = reference.copy(); first[4, 0, 0] = 1e-12
        second = first * 1e9
        a = evaluate_paper_spectra(first, reference, F)
        b = evaluate_paper_spectra(second, reference, F)
        self.assertAlmostEqual(a['curves']['spectral_error_db'][4], 60 / 128, places=12)
        self.assertEqual(a['sensitivity']['curves']['spectral_error_db'][4], 0.)
        self.assertEqual(a['sensitivity']['details']['floor_absolute_amplitude'], 1e-6)
        self.assertEqual(a['sensitivity']['details']['floor_absolute_amplitude'], b['sensitivity']['details']['floor_absolute_amplitude'])
        self.assertEqual(a['sensitivity']['details']['counts']['reference_below_floor_cells_by_frequency'][4], 1)

    def test_endpoint_projection_is_explicit_and_inputs_are_never_modified(self):
        reference = np.ones((257, 36, 32), complex)
        estimate = reference.copy(); estimate[[0, -1], :4] = 1j
        original = estimate.copy()
        supplied = evaluate_paper_spectra(estimate, reference, F)
        self.assertEqual(supplied['metrics']['spectral_error_db'], 0.)
        self.assertAlmostEqual(supplied['metrics']['coherence'], 1., places=12)
        projected = real_wave_foa(estimate)
        self.assertEqual(projected.shape, (257, 4, 32))
        self.assertTrue(np.all(projected[[0, -1]] == 0))
        scored = evaluate_paper_spectra(projected, real_wave_foa(reference), F)
        self.assertIsNone(scored['metrics']['coherence'])
        np.testing.assert_array_equal(estimate, original)

    def test_amplitude_rescaling_is_stable_and_changes_only_the_reference_floor_level(self):
        reference = np.full((257, 4, 32), 1 + .5j)
        original = evaluate_paper_spectra(2 * reference, reference, F)
        for gain in (1e250, 1e-250):
            result = evaluate_paper_spectra(2 * reference * gain, reference * gain, F)
            for profile, expected in [(result, original), (result['sensitivity'], original['sensitivity'])]:
                self.assertAlmostEqual(profile['metrics']['spectral_error_db'], expected['metrics']['spectral_error_db'], places=10)
                self.assertAlmostEqual(profile['metrics']['coherence'], expected['metrics']['coherence'], places=12)
            json.dumps(result, allow_nan=False)

    def test_invalid_shapes_and_nonfinite_inputs_fail_without_fake_values(self):
        reference = np.ones((257, 4, 32), complex)
        for estimate, target, frequencies in [(reference[:256], reference, F), (reference[:, :3], reference, F),
                                               (reference, reference, F[::-1]), (reference, reference, F[:-1])]:
            with self.assertRaises(ValueError):evaluate_paper_spectra(estimate, target, frequencies)
        invalid = reference.copy(); invalid[4, 1, 2] = np.nan
        for estimate, target in [(invalid, reference), (reference, invalid)]:
            with self.assertRaises(ValueError):evaluate_paper_spectra(estimate, target, F)
        with self.assertRaises(ValueError):real_wave_foa(invalid)


if __name__ == '__main__':
    unittest.main(verbosity=2)
