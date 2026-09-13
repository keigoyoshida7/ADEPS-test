"""Temporary figure fixtures only; never read or publish final benchmark data."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

if importlib.util.find_spec('matplotlib') is not None:
    import plot_plus_results as p
else:
    p = None


def fixture():
    means = [-11., -14., -15., -12., -14.5, -18., -17., -20., -20.3]
    curves = {}
    for i, method in enumerate(p.IDS):
        base = np.linspace(0, 1, 257)
        curves[method] = {'nrmse_db': (means[i] + 2 * np.sin(base * 8)).tolist(),
                          'magnitude_spectrum_error_db': (1 + i / 7 + base).tolist(),
                          'magnitude_squared_coherence': (.75 + base / 8 + i / 100).tolist()}
    # A missing positive bin remains a visible gap, and DC must never be drawn.
    curves['plus']['nrmse_db'][0] = 9999.
    curves['plus']['nrmse_db'][45] = None
    methods = [{'id': method, 'label_en': p.LABELS[method], 'mean_nrmse_db': means[i], 'completed': 32, 'failed': 0} for i, method in enumerate(p.IDS)]
    scenes = [{'id': f'fixture-{i}', 'cluster_id': f'pair-{i // 8}',
               'speaker_pair': [f'speaker-{2 * (i // 8)}', f'speaker-{2 * (i // 8) + 1}'], 'source_count': 1 + i % 2,
               'metrics': {method: {key: 1. for key in p.METRICS} for method in p.IDS},
               'outcomes': {method: 'completed' for method in p.IDS}, 'curves': deepcopy(curves)} for i in range(32)]
    comparisons = []
    for method, mean in zip(p.IDS, means):
        if method == 'plus': continue
        gain = mean - means[7]
        comparisons.append({'baseline': method, 'candidate': 'plus', 'mean_gain_db': gain,
            'ci_low_db': gain - .2, 'ci_high_db': gain + .2, 'count': 32, 'confidence_level': .975,
            'wins': 32 if gain > 0 else 0, 'losses': 32 if gain < 0 else 0, 'ties': 0, 'invalid': 0,
            'clusters': [f'pair-{i}' for i in range(4)]})
    return {'schema': 'adeps-plus-benchmark/1', 'status': 'evaluated',
            'conditions': {'scenes': 32, 'clusters': 4, 'microphones': 6, 'radius_m': .06, 'snr_db': 50,
                           'sample_rate_hz': 16000, 'geometry': 'sphere', 'source_counts': [1, 2], 'matched_order': 5,
                           'evaluated_audio_samples': 3968, 'evaluated_audio_seconds': .248},
            'frequencies_hz': p.FREQUENCIES.tolist(), 'methods': methods, 'scenes': scenes,
            'curves': curves, 'comparisons': comparisons, 'provenance': {'fixture_only': True}}


@unittest.skipIf(p is None, 'Optional Matplotlib is not installed; standalone plotting tests require it.')
class FigureTests(unittest.TestCase):
    def test_frequency_curves_preserve_gaps_and_never_plot_dc_or_extrapolate(self):
        report = fixture(); p.validate_report(report)
        with p.matplotlib.rc_context(p.style(p.choose_font())):
            fig = p.frequency_figure(report, 'a' * 64, p.choose_font())
            try:
                for ax in fig.axes:
                    self.assertEqual(ax.get_xlim(), (1., 20000.))
                    for line in ax.lines[:5]:
                        self.assertEqual(len(line.get_xdata()), 256)
                        self.assertEqual((line.get_xdata()[0], line.get_xdata()[-1]), (31.25, 8000.))
                plus = fig.axes[0].lines[3].get_ydata()
                self.assertTrue(np.isnan(plus[44])); self.assertLess(np.nanmax(plus), 9999.)
            finally: p.plt.close(fig)

    def test_summary_uses_stored_means_intervals_and_retains_better_off(self):
        report = fixture()
        report['methods'][0]['mean_nrmse_db'] = -22.3456  # Read the stored value, never recompute it here.
        fig = p.summary_figure(report, 'a' * 64, p.choose_font())
        try:
            left, right = fig.axes
            self.assertEqual(left.lines[0].get_xdata()[0], -22.3456)
            self.assertEqual(len(left.get_yticklabels()), 9)
            self.assertIn('OFF', left.get_yticklabels()[-1].get_text())
            off_point = right.lines[-2]
            self.assertAlmostEqual(off_point.get_xdata()[0], -.3)
            interval = right.collections[-2].get_segments()[0]
            self.assertAlmostEqual(interval[0, 0], -.5); self.assertAlmostEqual(interval[-1, 0], -.1)
        finally: p.plt.close(fig)

    def test_missing_incomplete_or_nonfinite_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError): p.render(Path(directory) / 'missing.json', Path(directory) / 'output')
            self.assertFalse((Path(directory) / 'output').exists())
        for edit in [lambda r: r.update(status='running'), lambda r: r['methods'].pop(),
                     lambda r: r['curves']['plus']['magnitude_squared_coherence'].__setitem__(2, 1.1),
                     lambda r: r['comparisons'][0].update(ci_low_db=99., ci_high_db=1.),
                     lambda r: r['scenes'][0].update(speaker_pair=['leaked', 'pair'])]:
            report = fixture(); edit(report)
            with self.assertRaises(ValueError): p.validate_report(report)

    def test_standalone_svg_png_render_only_in_temporary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'fixture.json'
            source.write_text(json.dumps(fixture(), allow_nan=False))
            result = p.render(source, root / 'figures')
            self.assertEqual(len(result['artifacts']), 4)
            self.assertFalse(result['metrics_recomputed'])
            for name in result['artifacts']:
                data = (root / 'figures' / name).read_bytes()
                self.assertGreater(len(data), 10000)
                if name.endswith('.svg'):
                    self.assertIn(result['report_sha256'].encode(), data)
                    self.assertIn(b'no original-paper superiority', data)
                    self.assertIn(b'0.248 s after edge trim', data)
                else:
                    self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                    width, height = struct.unpack('>II', data[16:24])
                    self.assertGreaterEqual(width, 3000); self.assertGreaterEqual(height, 2000)


if __name__ == '__main__':
    unittest.main()
