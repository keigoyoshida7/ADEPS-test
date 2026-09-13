"""CPU-only checks of speech-studio observations and audio/metadata packaging.

Run: python -m unittest discover -s training_tests -p test_paper_studio.py

No dataset, room simulator, model checkpoint, Torch, or device is needed. The
unused native inference imports are replaced only while loading this module;
actual observation, encoder, metrics, and WAV-export code are exercised. The
in-memory plane-wave fixture and sampler are NOT speech/prior-quality evidence.
No fixture audio, metadata, or ZIP is written into the project or public assets.
"""
import base64
import copy
import hashlib
import importlib.util
import io
import json
import sys
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile
from scipy.signal import stft

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from capture import encode, modal_matrix, real_n3d
from diffusion_studio import coherence_summary, frequency_metrics, run_studio
from neural import expand
from neural_audio import inverse_spectra


def forbidden_native_inference(*args, **kwargs):
    raise AssertionError('This CPU packaging test must never load or run a model')


# Load the real module without importing Torch or replacing other tests' module
# instances. The temporary dependency entry is restored immediately afterward.
inference_stub = types.ModuleType('paper_inference')
inference_stub.PaperPrior = forbidden_native_inference
inference_stub.sample = forbidden_native_inference
spec = importlib.util.spec_from_file_location('_paper_studio_cpu_tests', ROOT / 'backend/paper_studio.py')
studio = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'paper_inference': inference_stub}):
    spec.loader.exec_module(studio)


class PaperStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rate, cls.fft, cls.hop, cls.frames = 16000, 512, 128, 32
        cls.samples = cls.fft + (cls.frames - 1) * cls.hop
        t = np.arange(cls.samples) / cls.rate
        cls.wave = (.5 * np.sin(2 * np.pi * 330 * t)
                    + .15 * np.cos(2 * np.pi * 770 * t)
                    + .2 * np.exp(-((t - .12) / .009) ** 2))
        cls.direction = np.array([.36, -.48, .8])
        cls.coefficients = real_n3d(5, cls.direction[None])[0]
        _, _, spectrum = stft(cls.wave, fs=cls.rate, window='hann',
                              nperseg=cls.fft, noverlap=cls.fft-cls.hop,
                              nfft=cls.fft, boundary=None, padded=False)
        cls.clean = cls.coefficients[:, None, None] * spectrum[None]
        cls.manifest_path = ROOT / '__in_memory_test_manifest__.json'
        cls.manifest_sha = hashlib.sha256(b'in-memory-test-manifest-only').hexdigest()
        cls.generator_sha = hashlib.sha256((ROOT / 'scripts/paper_data.py').read_bytes()).hexdigest()

    def setUp(self):
        case = self

        class FakeSceneDataset:
            def __init__(self, manifest, **kwargs):
                self.received = (manifest, kwargs)
                self.audio = {'files': [{'speaker': 'fixture-speaker',
                                        'archive_member': 'fixture-only/not-a-corpus-recording.flac'}]}

            def __getitem__(self, index):
                case.selected_scene_index = index
                receiver = np.array([2., 3., 1.5])
                return {'clean_stft': case.clean.copy(),
                        'metadata': {'id': f'fixture-test-{index}', 'split': 'test',
                                     'sources_m': [(receiver + 1.25 * case.direction).tolist()],
                                     'receiver_m': receiver.tolist(), 'audio_indexes': [0],
                                     'target_sh_order': 5, 'target_normalization': 'N3D'}}

        original_digest = studio.digest

        def digest(path):
            return self.manifest_sha if Path(path) == self.manifest_path else original_digest(path)

        self.dataset_factory = self.enterContext(patch.object(studio, 'SceneDataset', side_effect=FakeSceneDataset))
        self.enterContext(patch.object(studio, 'digest', side_effect=digest))
        self.prior = types.SimpleNamespace(std=1., card={
            'configuration': {'sample_rate_hz': self.rate, 'n_fft': self.fft,
                              'hop': self.hop, 'frames': self.frames,
                              'max_image_order_override': None},
            'source_sha256': {'scripts/paper_data.py': self.generator_sha},
            'data': {'manifest_sha256': self.manifest_sha},
            'model': {'id': 'in-memory-test-fixture-not-a-trained-model'},
        })

    def observation(self, **config):
        return studio.make_observation(self.prior, self.manifest_path, {'steps': 8, **config})

    def test_clean_sh_reference_and_held_out_scene_provenance(self):
        result = self.observation(scene_index=7)
        np.testing.assert_allclose(self.coefficients[:4],
                                   [1., -.48*np.sqrt(3), .8*np.sqrt(3), .36*np.sqrt(3)], atol=1e-14)
        np.testing.assert_array_equal(result['reference'], self.clean.transpose(1, 0, 2))
        np.testing.assert_allclose(result['source_directions'][0]['direction'], self.direction, atol=1e-15)
        self.assertEqual(result['reference'].shape, (257, 36, 32))
        self.assertEqual(self.selected_scene_index, 7)
        self.assertEqual(self.dataset_factory.call_args.kwargs,
                         {'split': 'test', 'sample_rate': 16000, 'n_fft': 512,
                          'hop': 128, 'frames': 32, 'max_image_order': None})
        self.assertEqual(result['example_provenance']['scene']['id'], 'fixture-test-7')
        self.assertEqual(result['example_provenance']['manifest_sha256'], self.manifest_sha)
        attribution = result['attribution']
        self.assertEqual(attribution['speakers'], ['fixture-speaker'])
        self.assertEqual(attribution['files'], ['fixture-only/not-a-corpus-recording.flac'])
        self.assertEqual(attribution['license'], 'CC BY 4.0')
        self.assertEqual(attribution['source_url'], 'https://doi.org/10.7488/ds/2645')
        self.assertIn('Resampled', attribution['changes'])

    def test_array_controls_and_even_ring_spacing(self):
        ring = self.observation(microphones=8, geometry='ring', radius_m=.09)
        position = ring['microphone_positions_m']
        self.assertEqual(ring['V'].shape, (257, 8, 36))
        self.assertEqual(ring['p'].shape, (257, 8, 32))
        np.testing.assert_allclose(position[:, 2], 0., atol=0.)
        np.testing.assert_allclose(np.linalg.norm(position, axis=1), .09, atol=1e-15)
        # Equal neighboring chord lengths catch using Fibonacci angles in ring mode.
        chords = np.linalg.norm(np.roll(position, -1, axis=0) - position, axis=1)
        np.testing.assert_allclose(chords, 2*.09*np.sin(np.pi/8), atol=1e-15)
        sphere = self.observation(microphones=12, geometry='sphere', radius_m=.12)
        self.assertEqual(sphere['V'].shape, (257, 12, 36))
        np.testing.assert_allclose(np.linalg.norm(sphere['microphone_positions_m'], axis=1), .12, atol=1e-15)
        self.assertGreater(np.ptp(sphere['microphone_positions_m'][:, 2]), .1)
        self.assertNotEqual(ring['input_sha256'], sphere['input_sha256'])

    def test_forward_response_complex_phase_endpoints_and_requested_noise(self):
        result = self.observation()
        expected_v = modal_matrix(result['frequencies'], result['microphone_positions_m'], 5)
        expected_v[[0, -1]] = expected_v[[0, -1]].real
        np.testing.assert_array_equal(result['V'], expected_v)
        self.assertGreater(np.linalg.norm(result['V'][1:-1].imag), 0.)
        for key in ('V', 'reference', 'p'):
            np.testing.assert_array_equal(result[key][[0, -1]].imag, 0.)
        clean_observation = result['V'] @ result['reference']
        noise = result['p'] - clean_observation
        measured_snr = 20*np.log10(np.linalg.norm(clean_observation)/np.linalg.norm(noise))
        self.assertAlmostEqual(measured_snr, 50., places=10)
        changed = self.observation(snr_db=17.)
        noise_changed = changed['p'] - clean_observation
        self.assertAlmostEqual(20*np.log10(np.linalg.norm(clean_observation)/np.linalg.norm(noise_changed)), 17., places=10)

    def test_observation_is_repeatable_and_independent_of_diffusion_controls(self):
        first = self.observation()
        for controls in ({}, {'seed': 99}, {'eta_prime': 0.}, {'steps': 16},
                         {'seed': 1, 'eta_prime': 100., 'steps': 150}):
            with self.subTest(controls=controls):
                other = self.observation(**controls)
                self.assertEqual(first['input_sha256'], other['input_sha256'])
                for key in ('V', 'p', 'reference'):
                    np.testing.assert_array_equal(first[key], other[key])
        for controls in ({'observation_seed': 17}, {'snr_db': 10.}, {'radius_m': .08}):
            with self.subTest(controls=controls):
                other = self.observation(**controls)
                self.assertNotEqual(first['input_sha256'], other['input_sha256'])
                np.testing.assert_array_equal(first['reference'], other['reference'])
                self.assertFalse(np.array_equal(first['p'], other['p']))

    def test_generator_and_manifest_mismatch_fail_before_rendering(self):
        for key, nested_key, message in (
                ('source_sha256', 'scripts/paper_data.py', 'room-data generator'),
                ('data', 'manifest_sha256', 'manifest')):
            with self.subTest(provenance=key):
                original = copy.deepcopy(self.prior.card)
                self.prior.card[key][nested_key] = '0'*64
                with self.assertRaisesRegex(ValueError, message):
                    self.observation()
                self.dataset_factory.assert_not_called()
                self.prior.card = original

    def test_unpadded_stft_preview_is_exact_central_waveform(self):
        result = self.observation()
        actual = inverse_spectra(result['reference'][:, :4], result['audio'])
        first_four = np.array([1., -.48*np.sqrt(3), .8*np.sqrt(3), .36*np.sqrt(3)])
        expected = self.wave[256:-256, None]*first_four[None]
        self.assertEqual(self.samples, 4480)
        self.assertEqual(actual.shape, (3968, 4))
        np.testing.assert_allclose(actual, expected, rtol=0, atol=5e-15)
        self.assertEqual(result['audio']['samples'], 3968)
        self.assertEqual(result['audio']['preview_trim_each_end_samples'], 256)
        self.assertEqual(result['audio']['duration_seconds'], .248)
        self.assertIn('before this trim', result['audio']['preview_trim_reason'])

    def test_in_memory_zip_preserves_shared_gain_stages_metrics_and_credit(self):
        observation = self.observation()
        raw_snapshots = {}

        def fixture_sampler(y, ev, model, steps, eta_prime, seed, progress, snapshot):
            base = expand(y)
            for step, factor in ((0, .7), (2, 1.5)):
                value = base*factor
                raw_snapshots[f'denoised_{step:03d}'] = value.copy()
                snapshot({'stage': 'denoised_estimate', 'step': step,
                          'iteration': step+1, 'sigma': 20./(step+1)}, value)
            final = base*3.
            raw_snapshots['final'] = final.copy()
            snapshot({'stage': 'final_sample', 'step': steps,
                      'iteration': steps, 'sigma': 0.}, final.copy())
            return final, []

        result, archive_bytes = run_studio({}, observation=observation, model=self.prior,
                                          sampler=fixture_sampler)
        linear, _, _ = encode(observation['V'], observation['p'], .001)
        scale = np.sqrt(np.mean(abs(linear)**2))
        diagnostic = result['scaling_diagnostic']
        reference_rms = np.sqrt(np.mean(abs(observation['reference'])**2))
        self.assertAlmostEqual(diagnostic['reference_hoa_rms'], reference_rms, places=14)
        self.assertAlmostEqual(diagnostic['linear_hoa_rms'], scale, places=14)
        self.assertAlmostEqual(diagnostic['linear_to_reference_rms_ratio'], scale/reference_rms, places=14)
        self.assertIs(diagnostic['used_for_inference'], False)
        spectra = {'reference': observation['reference'], 'linear': linear,
                   **{key: value*scale for key, value in raw_snapshots.items()}}
        unscaled_waves = {key: inverse_spectra(value[:, :4], observation['audio'])
                          for key, value in spectra.items()}
        maximum_peak = max(float(np.max(abs(wave))) for wave in unscaled_waves.values())
        expected_gain = min(1., .95/maximum_peak)
        self.assertLess(expected_gain, 1.)  # Exercise actual attenuation, not just gain=1.
        self.assertAlmostEqual(result['audio']['shared_gain'], expected_gain, places=14)
        self.assertEqual(result['frames'], 32)
        self.assertEqual(result['audio']['sh_ordering'], 'ACN')
        self.assertEqual(result['audio']['sh_normalization'], 'N3D')
        self.assertEqual(result['audio']['channel_names'], ['W', 'Y', 'Z', 'X'])
        self.assertEqual(result['checkpoints'][-1]['stage'], 'final_sample')
        self.assertEqual(result['checkpoints'][-1]['step'], 8)
        self.assertEqual(result['checkpoints'][-1]['sigma'], 0.)
        items = [result['reference'], result['linear'], *result['checkpoints']]
        # Check the documented virtual cardioids independently of PREVIEW_MATRIX.
        preview_matrix = np.array([[.5, .5/np.sqrt(6), 0., .5/np.sqrt(6)],
                                   [.5, -.5/np.sqrt(6), 0., .5/np.sqrt(6)]])
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            metadata = json.loads(archive.read('metadata.json'))
            self.assertEqual(metadata['audio']['attribution'], observation['attribution'])
            self.assertEqual(metadata['example_provenance'], observation['example_provenance'])
            self.assertEqual(metadata['model']['id'], 'in-memory-test-fixture-not-a-trained-model')
            self.assertNotIn('preview_wav_base64', archive.read('metadata.json').decode())
            for item in items:
                with self.subTest(stage=item['id']):
                    expected = unscaled_waves[item['id']]*expected_gain
                    rate, wave = wavfile.read(io.BytesIO(archive.read(item['wav_filename'])))
                    self.assertEqual((rate, wave.shape, wave.dtype), (16000, (3968, 4), np.dtype('float32')))
                    np.testing.assert_allclose(wave, expected, rtol=2e-7, atol=1e-8)
                    rate, preview = wavfile.read(io.BytesIO(base64.b64decode(item['preview_wav_base64'])))
                    self.assertEqual((rate, preview.shape, preview.dtype), (16000, (3968, 2), np.dtype('int16')))
                    np.testing.assert_allclose(preview.astype(float)/32767, expected @ preview_matrix.T,
                                               rtol=0, atol=.51/32767)
                    metric = item['frequency_metrics']
                    self.assertEqual(item['metrics']['coherence_by_frequency'],
                                     metric['magnitude_squared_coherence'])
                    self.assertEqual(metric['frames'], 32)
                    self.assertEqual(metric['channels'], 4)
                    self.assertEqual(len(metric['frequency_hz']), 257)
                    np.testing.assert_array_equal(metric['frequency_hz'], np.arange(257)*31.25)
        self.assertEqual(result['metrics']['final'], result['checkpoints'][-1]['metrics'])


class CoherenceSummaryTests(unittest.TestCase):
    def test_missing_z_does_not_silently_yield_perfect_scalar(self):
        reference = np.ones((3, 4, 4), dtype=complex)
        reference[2] = 0.
        estimate = np.ones_like(reference)
        estimate[0, 2] = 0.  # Required Z missing only at the first frequency.
        spectral = frequency_metrics(estimate, reference, [0., 1000., 8000.])
        result = coherence_summary(spectral)
        self.assertEqual(spectral['magnitude_squared_coherence'], [None, 1., None])
        self.assertIsNone(result['coherence'])
        self.assertEqual(result['coherence_status'], 'undefined_missing_estimate')
        self.assertEqual(result['coherence_valid_frequency_bins'], 1)
        self.assertEqual(result['coherence_reference_active_frequency_bins'], 2)
        self.assertEqual(result['coherence_missing_estimate_frequency_bins'], 1)
        self.assertEqual(result['coherence_excluded_reference_silent_frequency_bins'], 1)
        self.assertEqual(result['coherence_valid_bins'], 7)
        self.assertEqual(result['coherence_total_bins'], 12)

    def test_frequency_mean_is_equal_weight_and_includes_active_endpoints(self):
        reference = np.ones((2, 4, 2), dtype=complex)
        reference[0, 1:] = 0.  # DC has one active coefficient, Nyquist has four.
        estimate = reference.copy()
        estimate[1, :, 1] = -1.  # Time vectors [1,1] and [1,-1] are orthogonal.
        result = coherence_summary(frequency_metrics(estimate, reference, [0., 8000.]))
        self.assertEqual(result['coherence_by_frequency'], [1., 0.])
        self.assertEqual(result['coherence'], .5)  # Not the channel-weighted 1/5.
        self.assertEqual(result['coherence_status'], 'defined')
        self.assertEqual(result['coherence_valid_frequency_bins'], 2)
        self.assertEqual(result['coherence_reference_active_frequency_bins'], 2)
        self.assertEqual(result['coherence_missing_estimate_frequency_bins'], 0)
        self.assertIn('DC and Nyquist', result['coherence_definition'])

    def test_silent_reference_remains_undefined(self):
        reference = np.zeros((2, 4, 2), dtype=complex)
        result = coherence_summary(frequency_metrics(np.ones_like(reference), reference, [0., 8000.]))
        self.assertIsNone(result['coherence'])
        self.assertEqual(result['coherence_status'], 'undefined_no_reference')
        self.assertEqual(result['coherence_valid_frequency_bins'], 0)
        self.assertEqual(result['coherence_reference_active_frequency_bins'], 0)
        self.assertEqual(result['coherence_missing_estimate_frequency_bins'], 0)
        self.assertEqual(result['coherence_excluded_reference_silent_frequency_bins'], 2)


if __name__ == '__main__':
    unittest.main()
