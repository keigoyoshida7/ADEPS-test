"""CPU-only CLI contracts. Temporary fixtures are not released quality data."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infer_plus as cli
from plus_consistency import synthesize_spectra
import plus_hybrid


class InferenceCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / 'checkpoint'
        self.checkpoint.mkdir()
        weight = self.checkpoint / 'paper-prior-v1.pt'
        weight.write_bytes(b'CPU test fixture: not actual neural weights')
        self.sha = cli.file_sha256(weight)
        self.card = {'schema': 'adeps-test-paper-prior-training/1',
                     'model': {'weights_sha256': self.sha, 'test_fixture_only': True},
                     'configuration': {'sample_rate_hz': 16000, 'n_fft': 512,
                                       'hop': 128, 'compressed_std': 1.13679}}
        (self.checkpoint / 'report.json').write_text(json.dumps(self.card))
        self.selection = {'schema': 'adeps-plus-selection/1', 'model_weights_sha256': self.sha,
            'configuration': {'steps': 2, 'sigma_start': 1., 'relaxation': .25,
                'use_stft_consistency': True, 'stft_iterations': 0, 'ridge_relative': 1e-7},
            'post_iterations': 2, 'post_ridge_relative': 1e-7,
            'provenance': {'test_fixture_only': True}}
        self.selection_path = self.root / 'selection.json'
        self.selection_path.write_text(json.dumps(self.selection))
        self.input_path = self.root / 'input.npz'
        rng = np.random.default_rng(923)
        self.v = np.broadcast_to(np.eye(4, 36), (257, 4, 36)).copy().astype(complex)
        self.p = (rng.normal(size=(257, 4, 4)) + 1j*rng.normal(size=(257, 4, 4))) * .01
        self.p[[0, -1]] = self.p[[0, -1]].real
        self.fields = dict(p_real=self.p.real, p_imag=self.p.imag,
            V_real=self.v.real, V_imag=self.v.imag, frequencies_hz=np.fft.rfftfreq(512, 1/16000),
            sample_rate_hz=16000, n_fft=512, hop=128, sh_ordering='ACN', sh_normalization='N3D',
            attribution_json=json.dumps({'license': 'test attribution only', 'author': 'Fixture author'}),
            provenance_json=json.dumps({'source': 'generated CPU fixture, no actual audio'}),
            audio_json=json.dumps({'samples': 896}),
            # allow_pickle=False must leave unrelated reference entries unread.
            reference_real=np.array([object()], dtype=object))
        np.savez_compressed(self.input_path, **self.fields)
        self.args = SimpleNamespace(input=self.input_path, selection=self.selection_path,
            checkpoint=self.checkpoint, output=self.root/'output', device='cpu',
            no_denoiser=False, noise_snr=None, estimate_noise=False)

    def fake_prior(self, checkpoint, device):
        return SimpleNamespace(card=self.card, std=1.13679, device='cpu-fixture')

    def execute(self, **kwargs):
        with redirect_stdout(io.StringIO()), \
             patch.object(plus_hybrid, '_denoise_no_grad', side_effect=lambda prior, x, sigma: x*.9):
            return cli.run(self.args, prior_factory=self.fake_prior, **kwargs)

    def test_export_preserves_hashes_attribution_full_n5_and_common_gain(self):
        summary = self.execute()
        output = self.args.output
        self.assertEqual(summary['nfe'], 2)
        self.assertEqual(summary['model_weights_sha256'], self.sha)
        self.assertEqual(summary['input_provenance']['attribution']['author'], 'Fixture author')
        self.assertFalse(summary['reference_used'])
        self.assertFalse(summary['reference_quality_metrics_computed'])
        self.assertEqual(summary['audio']['samples'], 384)
        self.assertEqual(summary['audio']['full_synthesis_samples'], 896)
        self.assertEqual(summary['audio']['trim_each_end_samples'], 256)
        self.assertEqual(summary['noise_assumption']['snr_db'], 50.)
        self.assertFalse(summary['noise_assumption']['real_recording_noise_verified'])
        self.assertEqual(cli.configuration_sha256(summary['effective_configuration']),
                         summary['configuration_sha256'])
        restored = json.loads((output/'summary.json').read_text())
        self.assertEqual(restored, summary)
        with np.load(output/'reconstruction.npz', allow_pickle=False) as data:
            self.assertNotIn('reference_real', data.files)
            self.assertEqual(data['observation_sha256'].item(), cli.load_input(self.input_path)['observation_sha256'])
            self.assertEqual(data['configuration_sha256'].item(), summary['configuration_sha256'])
            self.assertEqual(json.loads(data['input_provenance_json'].item()), summary['input_provenance'])
            peak = 0.
            for name in ('estimate', 'linear', 'spatial'):
                spectra = data[f'{name}_real'] + 1j*data[f'{name}_imag']
                self.assertEqual(spectra.shape, (257, 36, 4))
                raw = synthesize_spectra(spectra[:, :4])[:, 256:-256].T
                rate, audio = wavfile.read(output/f'{name}-foa.wav')
                self.assertEqual(rate, 16000)
                self.assertEqual(audio.dtype, np.float32)
                self.assertEqual(audio.shape, (384, 4))
                np.testing.assert_array_equal(audio, (raw*summary['audio']['shared_gain']).astype(np.float32))
                peak = max(peak, float(abs(audio).max()))
            self.assertAlmostEqual(peak, .95, places=6)
        for name, artifact in summary['artifacts'].items():
            self.assertEqual(cli.file_sha256(output/name), artifact['sha256'])
            self.assertEqual((output/name).stat().st_size, artifact['bytes'])

    def test_no_denoiser_keeps_same_consistency_configuration(self):
        self.args.no_denoiser = True
        with redirect_stdout(io.StringIO()), \
             patch.object(plus_hybrid, '_denoise_no_grad', side_effect=AssertionError('Must skip model')):
            result = cli.run(self.args, prior_factory=self.fake_prior)
        self.assertEqual(result['nfe'], 0)
        self.assertEqual(len(result['trace']), 2)
        self.assertEqual(len(result['post_trace']), 2)
        self.assertTrue(all(not row['model_call'] for row in result['trace']))
        self.assertEqual(result['selection']['configuration']['relaxation'], 0.)
        self.assertEqual(result['selection']['post_iterations'], 2)

    def test_tampered_observation_hash_rejected_before_prior(self):
        np.savez_compressed(self.input_path, **self.fields, observation_sha256='0'*64)
        with patch.object(self, 'fake_prior', side_effect=AssertionError('Prior must not load')) as factory:
            with self.assertRaisesRegex(ValueError, 'observation_sha256'):
                cli.run(self.args, prior_factory=factory)
        self.assertFalse(self.args.output.exists())

    def test_wrong_checkpoint_rejected_before_prior(self):
        (self.checkpoint/'paper-prior-v1.pt').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'actual checkpoint'), \
             patch.object(self, 'fake_prior', side_effect=AssertionError('Prior must not load')) as factory:
            cli.run(self.args, prior_factory=factory)
        self.assertFalse(self.args.output.exists())

    def test_selection_source_hash_and_required_configuration_are_enforced(self):
        self.selection['provenance']['source_sha256'] = {'backend/plus_hybrid.py': '0'*64}
        self.selection_path.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(ValueError, 'source checksum mismatch'):
            cli.load_selection(self.selection_path)
        self.selection['provenance'].pop('source_sha256')
        self.selection['configuration'].pop('steps')
        self.selection_path.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(ValueError, 'explicit supported'):
            cli.load_selection(self.selection_path)

    def test_noise_override_is_explicit_and_does_not_mutate_selection(self):
        original = json.loads(json.dumps(self.selection))
        selected, info = cli.noise_selection(self.selection, noise_snr=40.)
        self.assertEqual(selected['configuration']['spatial_config']['noise_snr_db'], 40.)
        self.assertEqual(info['mode'], 'explicit_user_supplied_snr')
        self.assertTrue(info['changed_from_selection'])
        estimated, info = cli.noise_selection(self.selection, estimate_noise=True)
        self.assertIsNone(estimated['configuration']['spatial_config']['noise_snr_db'])
        self.assertEqual(info['mode'], 'observation_covariance_fit')
        self.assertEqual(self.selection, original)
        with self.assertRaises(ValueError):
            cli.noise_selection(self.selection, noise_snr=float('nan'))

    def test_existing_output_is_not_overwritten(self):
        self.args.output.mkdir()
        sentinel = self.args.output/'keep.txt'
        sentinel.write_text('existing')
        with self.assertRaises(FileExistsError), \
             patch.object(self, 'fake_prior', side_effect=AssertionError('Prior must not load')) as factory:
            cli.run(self.args, prior_factory=factory)
        self.assertEqual(sentinel.read_text(), 'existing')


if __name__ == '__main__':
    unittest.main()
