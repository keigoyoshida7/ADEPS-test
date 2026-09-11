import io
import unittest
import zipfile
from unittest.mock import patch
import numpy as np
from scipy.io import wavfile
from capture import encode
from spatial import (synthetic, as_bundle, run_spatial, run_spatial_audio,
                     run_spatial_source, source_zip, settings)
from neural_audio import prepare_zip, example_zip, wav_bytes


class MockModel:
    card = {'name': 'test-only deterministic shrinkage', 'parameter_count': 0}
    def predict(self, linear, resolution, frequencies):
        return .8*linear


class SpatialTests(unittest.TestCase):
    def test_disabled_is_exact_linear_without_loading_model(self):
        cfg = {'enabled': False, 'data_seed': 41001}
        data = synthetic(cfg)
        linear, _, _ = encode(data['V'], data['p'], .001)
        result = run_spatial(cfg)
        np.testing.assert_array_equal(result['output']['linear_real'], linear[:, :4].real)
        for part in ('real', 'imag'):
            np.testing.assert_array_equal(result['output']['linear_'+part], result['output']['enhanced_'+part])
        self.assertIsNone(result['model']['weights_sha256'])

    def test_reference_does_not_change_prediction_or_input_hash(self):
        data = synthetic({'data_seed': 41002})
        bundle = as_bundle(data)
        first = run_spatial({'bundle': bundle}, model=MockModel())
        bundle['reference_real'] = np.zeros_like(bundle['reference_real']) + 999
        bundle['reference_imag'] = np.zeros_like(bundle['reference_imag'])
        second = run_spatial({'bundle': bundle}, model=MockModel())
        self.assertEqual(first['input_sha256'], second['input_sha256'])
        for part in ('real', 'imag'):
            np.testing.assert_array_equal(first['output']['enhanced_'+part], second['output']['enhanced_'+part])
        self.assertNotEqual(first['quality']['enhanced']['nrmse_db'], second['quality']['enhanced']['nrmse_db'])
        del bundle['reference_real'], bundle['reference_imag']
        unknown = run_spatial({'bundle': bundle}, model=MockModel())
        self.assertFalse(unknown['quality']['enhanced']['reference_available'])
        self.assertIsNone(unknown['quality']['enhanced']['nrmse_db'])

    def test_audio_bypass_alignment_and_shared_gain(self):
        result, packed = run_spatial_audio(example_zip(), {'enabled': False, 'duration_seconds': .4})
        with zipfile.ZipFile(io.BytesIO(packed)) as z:
            rate, a = wavfile.read(io.BytesIO(z.read('linear_FOA_ACN_N3D.wav')))
            rate_b, b = wavfile.read(io.BytesIO(z.read('enhanced_FOA_ACN_N3D.wav')))
        self.assertEqual(rate, rate_b)
        self.assertEqual(a.shape, (6400, 4))
        np.testing.assert_array_equal(a, b)
        self.assertLessEqual(result['audio']['shared_export_gain'], 1.)
        self.assertTrue(np.isfinite(a).all())
        self.assertIsNotNone(result['quality']['enhanced']['si_sdr'])

    def test_mono_source_is_simulation_and_offset_is_applied_once(self):
        rate = 16000
        t = np.arange(rate)/rate
        payload = wav_bytes(rate, .2*np.sin(2*np.pi*431*t))
        cfg = {'enabled': False, 'duration_seconds': .2, 'start_seconds': .6, 'data_seed': 41003}
        z, meta = source_zip(payload, cfg)
        bundle, audio, ref = prepare_zip(z, {**cfg, 'start_seconds': 0})
        self.assertEqual(ref.shape, (3200, 4))
        self.assertIn('NOT a venue recording', bundle['provenance'])
        result, exported = run_spatial_source(payload, cfg)
        self.assertEqual(result['audio']['source_start_seconds'], .6)
        self.assertEqual(result['audio']['samples'], 3200)
        self.assertGreater(len(exported), 1000)

    def test_bad_source_and_configuration_are_rejected(self):
        for cfg in ({'enabled': 'false'}, {'microphones': 3}, {'snr_db': float('nan')},
                    {'data_seed': -1}, {'scene': 'invented'}, {'regularization': float('inf')}):
            with self.assertRaises(ValueError):
                settings(cfg)
        for data in (np.zeros(1600), np.ones((1600, 2)), np.full(1600, np.nan)):
            with self.assertRaises(ValueError):
                source_zip(wav_bytes(16000, data), {})

    def test_resampled_source_uses_exact_generated_length(self):
        for rate, target, duration in ((8000, 48000, .02004), (44100, 16000, .10009)):
            source = .1*np.sin(2*np.pi*300*np.arange(rate)/rate)
            config = {'enabled': False, 'analysis_sample_rate_hz': target, 'duration_seconds': duration}
            payload = wav_bytes(rate, source)
            _, meta = source_zip(payload, config)
            result, _ = run_spatial_source(payload, config)
            self.assertEqual(result['audio']['samples'], meta['simulation_samples'])

    def test_longer_audio_path_and_legacy_limit_are_explicit(self):
        source = .1*np.sin(2*np.pi*300*np.arange(32000)/16000)
        result, _ = run_spatial_source(wav_bytes(16000, source),
                                     {'enabled': False, 'duration_seconds': 1., 'include_legacy': True})
        self.assertEqual(result['audio']['samples'], 16000)
        self.assertTrue(result['legacy']['skipped'])

    def test_invalid_model_output_rejected(self):
        class Invalid(MockModel):
            def predict(self, linear, resolution, frequencies):
                return np.full_like(linear, np.nan)
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            run_spatial({}, model=Invalid())


if __name__ == '__main__':
    unittest.main()
