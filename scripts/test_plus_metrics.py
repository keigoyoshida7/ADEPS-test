"""CPU-only quantitative tests; generated fixtures never become benchmark data."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from plus_consistency import analyze_waveform, synthesize_spectra
from plus_metrics import evaluate_metrics, aggregate, paired_comparison, FREQUENCIES, METRIC_KEYS, CURVE_KEYS


class MetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t = np.arange(4480) / 16000
        wave = np.array([np.sin(2 * np.pi * f * t) + .13 * np.cos(2 * np.pi * (f + 87) * t)
                         for f in (375, 750, 1125, 1500)])
        cls.reference = analyze_waveform(wave)

    def test_double_gain_changes_nmse_but_not_coherence_or_si_sdr(self):
        r = evaluate_metrics(2 * self.reference, self.reference, FREQUENCIES)
        self.assertAlmostEqual(r['metrics']['nrmse_db'], 0., places=12)
        self.assertAlmostEqual(r['metrics']['non_dc_nrmse_db'], 0., places=12)
        self.assertAlmostEqual(r['metrics']['coherence'], 1., places=12)
        sdr = r['details']['si_sdr']
        self.assertEqual(sdr['reference_active_count'], 4)
        for value, status in zip(sdr['by_channel_db'], sdr['by_channel_status']):
            self.assertTrue(status == 'exact_scale_match' or value > 250.)
        self.assertEqual(sdr['evaluated_samples'], 3968)
        self.assertEqual(sdr['trim_each_end_samples'], 256)
        json.dumps(r, allow_nan=False)

    def test_phase_is_penalized_by_complex_error_not_magnitude_or_coherence(self):
        reference = np.ones((257, 4, 32), complex)
        reference[[0, -1]] = 0
        r = evaluate_metrics(1j * reference, reference, FREQUENCIES)
        self.assertAlmostEqual(r['metrics']['nrmse_db'], 10 * math.log10(2), places=12)
        self.assertAlmostEqual(r['metrics']['magnitude_error_db'], 0., places=12)
        self.assertAlmostEqual(r['metrics']['coherence'], 1., places=12)
        self.assertIsNone(r['curves']['nrmse_db'][0])
        self.assertEqual(r['details']['nrmse_frequency_status'][0], 'zero_reference')

    def test_unweighted_full_band_keeps_dc_and_common_endpoint_projection_is_copy_only(self):
        reference = np.ones((257, 5, 32), complex)
        estimate = reference.copy()
        estimate[0, :4] *= 2
        estimate[:, 4] = 1000  # Higher-order channels are not FOA scoring.
        estimate[[0, -1]] += 100j
        saved = estimate.copy()
        r = evaluate_metrics(estimate, reference, FREQUENCIES)
        self.assertAlmostEqual(r['metrics']['nrmse_db'], 10 * math.log10(1 / 257), places=12)
        self.assertIsNone(r['metrics']['non_dc_nrmse_db'])
        self.assertEqual(r['metrics']['non_dc_nrmse_status'], 'exact_match')
        self.assertEqual(r['details']['domain']['speech_band_bins'], 253)
        self.assertAlmostEqual(r['details']['dc_reference_energy_fraction'], 1 / 257, places=14)
        np.testing.assert_array_equal(estimate, saved)
        np.testing.assert_array_equal(reference, np.ones(reference.shape))

    def test_si_sdr_uses_reference_common_channels_and_matches_independent_waveform_score(self):
        reference = self.reference.copy()
        reference[:, 3] = 0
        rng = np.random.default_rng(743)
        estimate = reference + .001 * (rng.normal(size=reference.shape) + 1j * rng.normal(size=reference.shape))
        r = evaluate_metrics(estimate, reference, FREQUENCIES)
        sdr = r['details']['si_sdr']
        self.assertEqual(sdr['reference_active_channels'], [True, True, True, False])
        self.assertEqual(sdr['finite_channel_count'], 3)
        a = synthesize_spectra(estimate)[:, 256:-256]
        b = synthesize_spectra(reference)[:, 256:-256]
        a -= a.mean(axis=1, keepdims=True)
        b -= b.mean(axis=1, keepdims=True)
        expected = []
        for c in range(3):
            target = np.dot(a[c], b[c]) / np.dot(b[c], b[c]) * b[c]
            expected.append(10 * np.log10(np.dot(target, target) / np.dot(a[c] - target, a[c] - target)))
        np.testing.assert_allclose(sdr['by_channel_db'][:3], expected, atol=3e-12)
        self.assertAlmostEqual(r['metrics']['si_sdr_db'], np.mean(expected), places=11)
        failed = estimate.copy()
        failed[:, 1] = 0
        bad = evaluate_metrics(failed, reference, FREQUENCIES)
        self.assertEqual(bad['details']['si_sdr']['reference_active_channels'], sdr['reference_active_channels'])
        self.assertEqual(bad['details']['si_sdr']['finite_channel_count'], 2)
        self.assertEqual(bad['details']['si_sdr']['by_channel_status'][1], 'zero_estimate')
        self.assertIsNone(bad['metrics']['si_sdr_db'])
        self.assertIsNone(bad['metrics']['coherence'])

    def test_exact_zero_nonfinite_and_invalid_inputs_are_not_finite_fake_scores(self):
        exact = evaluate_metrics(self.reference, self.reference, FREQUENCIES)
        self.assertIsNone(exact['metrics']['nrmse_db'])
        self.assertEqual(exact['metrics']['nrmse_status'], 'exact_match')
        zero = evaluate_metrics(np.zeros_like(self.reference), np.zeros_like(self.reference), FREQUENCIES)
        self.assertEqual(zero['metrics']['nrmse_status'], 'zero_reference')
        bad = self.reference.copy()
        bad[10, 0, 0] = np.inf
        failed = evaluate_metrics(bad, self.reference, FREQUENCIES)
        self.assertEqual(failed['metrics']['status'], 'failure')
        self.assertTrue(all(failed['metrics'][key] is None for key in METRIC_KEYS))
        for result in (exact, zero, failed):
            json.dumps(result, allow_nan=False)
        with self.assertRaises(ValueError):
            evaluate_metrics(self.reference, bad, FREQUENCIES)
        with self.assertRaises(ValueError):
            evaluate_metrics(self.reference[:256], self.reference, FREQUENCIES)
        with self.assertRaises(ValueError):
            evaluate_metrics(self.reference, self.reference, FREQUENCIES + 1)


def scenes_with_gains(gains):
    rows = []
    for cluster, gain in enumerate(gains):
        for index in range(8):
            # Pure arithmetic fixtures: one scene = one scalar metric, not
            # synthetic audio published as a measured benchmark.
            rows.append({'id': f's-{cluster}-{index}', 'cluster_id': f'pair-{cluster}',
                         'metrics': {'baseline': {key: .5 if key == 'coherence' else 1. if key == 'magnitude_error_db' else 0. for key in METRIC_KEYS},
                                     'plus': {key: .5 if key == 'coherence' else 1. if key == 'magnitude_error_db' else -float(gain) for key in METRIC_KEYS}},
                         'curves': {method: {key: [.5 if key == 'magnitude_squared_coherence' else float(cluster)] * 257 for key in CURVE_KEYS}
                                    for method in ('baseline', 'plus')}})
    return rows


class AggregationTests(unittest.TestCase):
    def test_paired_exact_cluster_enumeration_and_equal_scene_mean(self):
        scenes = scenes_with_gains([0, 0, 0, 4])
        r = paired_comparison(scenes, 'baseline', 'plus')
        # Each bootstrap mean equals the number of times the fourth cluster
        # was drawn: Binomial(n=4,p=1/4), with counts 81,108,54,12,1 / 256.
        self.assertEqual(r['bootstrap_samples'], 256)
        self.assertAlmostEqual(r['mean_gain_db'], 1.)
        self.assertEqual(r['ci_low_db'], 0.)
        self.assertEqual(r['ci_high_db'], 3.)
        self.assertEqual((r['wins'], r['ties'], r['losses']), (8, 24, 0))
        self.assertFalse(r['passed'])
        a = aggregate(scenes, ['baseline', 'plus'])
        self.assertEqual(a['means']['plus']['nrmse_db'], -1.)
        self.assertEqual(a['curves']['plus']['nrmse_db'][0], 1.5)
        self.assertEqual(a['valid_counts']['plus']['metrics']['nrmse_db'], 32)

    def test_success_threshold_regression_and_failed_scene_remains_in_denominator(self):
        self.assertTrue(paired_comparison(scenes_with_gains([.5] * 4), 'baseline', 'plus')['passed'])
        worse = paired_comparison(scenes_with_gains([-1] * 4), 'baseline', 'plus')
        self.assertEqual(worse['losses'], 32)
        self.assertEqual(worse['ci_high_db'], -1.)
        scenes = scenes_with_gains([1] * 4)
        scenes[0]['metrics']['plus']['nrmse_db'] = None
        scenes[0]['curves']['plus']['nrmse_db'][0] = None
        r = paired_comparison(scenes, 'baseline', 'plus')
        self.assertEqual((r['wins'], r['invalid'], r['count']), (31, 1, 32))
        self.assertIsNone(r['mean_gain_db'])
        self.assertIsNone(r['ci_low_db'])
        self.assertFalse(r['passed'])
        a = aggregate(scenes, ['baseline', 'plus'])
        self.assertIsNone(a['means']['plus']['nrmse_db'])
        self.assertIsNone(a['curves']['plus']['nrmse_db'][0])
        self.assertEqual(a['valid_counts']['plus']['curves']['nrmse_db'][0], 31)
        json.dumps({'aggregate': a, 'comparison': r}, allow_nan=False)

    def test_missing_duplicate_unbalanced_and_nonfinite_records_are_rejected(self):
        original = scenes_with_gains([1] * 4)
        for mutation in (lambda s: s.pop(), lambda s: s[1].update(id=s[0]['id']),
                         lambda s: s[0]['metrics']['plus'].update(nrmse_db=np.nan),
                         lambda s: s[0]['metrics']['plus'].update(coherence=1.1),
                         lambda s: s[0]['curves']['plus']['nrmse_db'].pop()):
            scenes = copy.deepcopy(original)
            mutation(scenes)
            with self.assertRaises(ValueError):
                aggregate(scenes, ['baseline', 'plus'])
        with self.assertRaises(ValueError):
            paired_comparison(original[:-1], 'baseline', 'plus')


if __name__ == '__main__':
    unittest.main(verbosity=2)
