"""Numerical and audio-contract checks, not evidence of acoustic improvement."""
import base64
import io
import json
import unittest
import zipfile
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

import diffusion_studio as studio
from capture import encode
from neural import expand, sample
from neural_audio import inverse_spectra


class LinearTestDenoiser:
    def predict(self, x, sigma):
        return .7*x, lambda upstream: .7*upstream


class FrequencyMetricTests(unittest.TestCase):
    def test_identity_and_twofold_gain_have_closed_form_metrics(self):
        reference = np.ones((2, 4, 8), dtype=complex)*(1+2j)
        untouched = reference.copy()
        identity = studio.frequency_metrics(reference, reference, [100., 200.])
        doubled = studio.frequency_metrics(2*reference, reference, [100., 200.])
        np.testing.assert_allclose(identity['magnitude_spectrum_error_db'], 0., atol=1e-14)
        np.testing.assert_allclose(identity['magnitude_squared_coherence'], 1., atol=1e-14)
        np.testing.assert_allclose(doubled['magnitude_spectrum_error_db'], 20*np.log10(2), atol=1e-13)
        np.testing.assert_allclose(doubled['magnitude_squared_coherence'], 1., atol=1e-14)
        self.assertEqual(identity['magnitude_floor_absolute'], doubled['magnitude_floor_absolute'])
        np.testing.assert_array_equal(reference, untouched)

    def test_msc_aggregates_time_before_channels_and_retains_phase_ambiguity(self):
        reference = np.ones((2, 4, 4), dtype=complex)
        estimate = reference.copy()
        estimate[0] *= np.array([1., -1., 1., -1.])  # Orthogonal over time in each channel.
        estimate[1] *= np.array([1., -1., 1., -1.])[:, None]  # Fixed but different channel phase.
        result = studio.frequency_metrics(estimate, reference, [100., 200.])
        np.testing.assert_allclose(result['magnitude_spectrum_error_db'], [0., 0.], atol=1e-14)
        np.testing.assert_allclose(result['magnitude_squared_coherence'], [0., 1.], atol=1e-14)
        estimate[0, 2:] = reference[0, 2:]
        mixed = studio.frequency_metrics(estimate, reference, [100., 200.])
        self.assertAlmostEqual(mixed['magnitude_squared_coherence'][0], .5)

    def test_zero_reference_is_null_and_zero_estimate_does_not_hide_bad_channels(self):
        reference = np.ones((3, 4, 4), dtype=complex)
        reference[0] = 0
        estimate = reference.copy()
        estimate[0] = 2  # No reference at this frequency: never report perfect recovery.
        estimate[1, 1] = 0
        reference[2, 1:] = 0
        estimate[2, 1:] = 1  # Generated energy in silent reference channels must be penalized.
        result = studio.frequency_metrics(estimate, reference, [0., 100., 200.])
        self.assertEqual(result['magnitude_spectrum_error_db'][0], None)
        self.assertEqual(result['magnitude_squared_coherence'], [None, None, 1.])
        self.assertEqual(result['reference_active_channels'], [0, 4, 1])
        self.assertEqual(result['coherence_valid_channels'], [0, 3, 1])
        np.testing.assert_allclose(result['magnitude_spectrum_error_db'][1:], [60., 180.], atol=1e-12)
        self.assertEqual(result['reference_below_floor_cells'], [16, 0, 12])
        self.assertEqual(result['estimate_below_floor_cells'], [0, 4, 0])
        json.dumps(result, allow_nan=False)
        silent = studio.frequency_metrics(np.zeros((1, 4, 2)), np.zeros((1, 4, 2)), [100.])
        self.assertEqual(silent['magnitude_spectrum_error_db'], [None])
        self.assertEqual(silent['magnitude_squared_coherence'], [None])
        json.dumps(silent, allow_nan=False)

    def test_shared_gain_does_not_change_metrics_or_coherence_at_extreme_scales(self):
        reference = np.ones((1, 4, 4), dtype=complex)
        estimate = 2*reference
        original = studio.frequency_metrics(estimate, reference, [125.])
        for gain in (1e-150, .031, 1e150):
            result = studio.frequency_metrics(estimate*gain, reference*gain, [125.])
            np.testing.assert_allclose(result['magnitude_spectrum_error_db'], original['magnitude_spectrum_error_db'], atol=1e-12)
            np.testing.assert_allclose(result['magnitude_squared_coherence'], [1.], atol=1e-14)
            self.assertAlmostEqual(result['magnitude_floor_absolute']/original['magnitude_floor_absolute']/gain, 1.)

    def test_invalid_shapes_frequencies_and_nonfinite_coefficients_are_rejected(self):
        reference = np.ones((2, 4, 4), dtype=complex)
        cases = [(reference[:1], reference, [100., 200.]),
                 (reference[:, :3], reference[:, :3], [100., 200.]),
                 (reference[:, :, :0], reference[:, :, :0], [100., 200.]),
                 (reference*np.nan, reference, [100., 200.]),
                 (reference, reference, [100., 100.]),
                 (reference, reference, [-1., 100.]),
                 (reference, reference, [100., np.inf])]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                studio.frequency_metrics(*args)


class DiffusionSnapshotHookTests(unittest.TestCase):
    def test_hook_is_observational_and_final_is_exact_return(self):
        rng = np.random.default_rng(1)
        y = rng.normal(size=(2, 36, 2)) + 1j*rng.normal(size=(2, 36, 2))
        ev = np.broadcast_to(np.eye(36), (2, 36, 36))
        expected, old_trace = sample(y, ev, LinearTestDenoiser(), steps=8, eta_prime=0., seed=7)
        events = []

        def observe(meta, coefficients):
            events.append((meta, coefficients.copy()))
            coefficients[:] = 999  # Must not mutate the integration or return value.

        actual, trace = sample(y, ev, LinearTestDenoiser(), steps=8, eta_prime=0., seed=7, snapshot=observe)
        np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(events[-1][1], actual)
        self.assertEqual(len(events), 9)
        self.assertEqual(events[0][0]['step'], 0)
        self.assertEqual(events[0][0]['iteration'], 1)
        self.assertEqual(events[-1][0], {'stage': 'final_sample', 'step': 8, 'iteration': 8, 'sigma': 0.})
        self.assertEqual(len(old_trace), len(trace))
        self.assertTrue(all(row['guidance_update_norm'] == 0 for row in trace))
        # First snapshot is the denoiser's clean estimate, not raw noisy x.
        from neural import expand, schedule
        sigma = schedule(8)[0]
        rng = np.random.default_rng(7)
        initial = y + sigma*(rng.normal(size=y.shape) + 1j*rng.normal(size=y.shape))
        np.testing.assert_array_equal(events[0][1], expand(.7*initial))


class DiffusionStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = {'steps': 8, 'duration_seconds': .08, 'eta_prime': 0.}
        cls.result, cls.payload = studio.run_studio(cls.config)

    def test_configuration_rejects_invalid_values(self):
        cases = [{'steps': 7}, {'steps': 81}, {'steps': True}, {'steps': 8.1},
                 {'microphones': 5}, {'geometry': 'line'}, {'radius_m': 0},
                 {'radius_m': float('nan')}, {'snr_db': -1}, {'eta_prime': 101},
                 {'eta_prime': True}, {'seed': -1}, {'seed': 2**32},
                 {'observation_seed': '2026'}, {'sample_rate': 48000},
                 {'n_fft': 512}, {'duration_seconds': .5}, {'regularization': 0}]
        for cfg in cases:
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                studio.settings(cfg)
        with self.assertRaises(ValueError):
            studio.settings(None)

    def test_observation_seed_is_separate_from_all_diffusion_controls(self):
        data = studio.make_observation(self.config)
        changed = studio.make_observation({**self.config, 'seed': 19, 'eta_prime': 80, 'steps': 80})
        self.assertEqual(data['input_sha256'], changed['input_sha256'])
        np.testing.assert_array_equal(data['p'], changed['p'])
        other_observation = studio.make_observation({**self.config, 'observation_seed': 2027})
        self.assertNotEqual(data['input_sha256'], other_observation['input_sha256'])
        self.assertLessEqual(data['frequencies'].size*data['p'].shape[-1], 8192)
        # Radius and topology affect the physical response, not just the graphic.
        for changed_cfg in ({'radius_m': .08}, {'geometry': 'ring'}, {'microphones': 4}):
            other = studio.make_observation({**self.config, **changed_cfg})
            self.assertNotEqual(data['input_sha256'], other['input_sha256'])

    def test_repeatable_model_output_eta_zero_and_stochastic_seed(self):
        again, _ = studio.run_studio(self.config)
        self.assertEqual(again['input_sha256'], self.result['input_sha256'])
        self.assertEqual(again['checkpoints'], self.result['checkpoints'])
        self.assertTrue(all(x['guidance_update_norm'] == 0. for x in again['trace']))
        changed, _ = studio.run_studio({**self.config, 'seed': 43})
        self.assertEqual(changed['input_sha256'], self.result['input_sha256'])
        self.assertNotEqual(changed['checkpoints'][-1]['preview_wav_base64'],
                            self.result['checkpoints'][-1]['preview_wav_base64'])
        self.assertEqual(again['model']['id'], 'tiny-spatial-v1')
        self.assertFalse(again['official_model'])

    def test_covariance_is_actual_complex_second_moment_and_directional_rms(self):
        rng = np.random.default_rng(321)
        f = np.array([0., 125., 1000., 5000., 8000.])
        a = rng.normal(size=(5, 4, 3)) + 1j*rng.normal(size=(5, 4, 3))
        matrices = studio.covariance(a, f)
        vectors = a[1:].transpose(0, 2, 1).reshape(-1, 4)
        expected = (vectors.T @ vectors.conj()).real / len(vectors)
        np.testing.assert_allclose(matrices['broadband'], expected, atol=1e-15)
        np.testing.assert_allclose(matrices['low'], (a[1] @ a[1].conj().T).real / 3, atol=1e-15)
        direction = np.array([.7, -.2, .4]); direction /= np.linalg.norm(direction)
        y = np.r_[1., np.sqrt(3)*direction[[1, 2, 0]]]
        direct = np.mean(abs(vectors@y)**2)
        self.assertAlmostEqual(float(y@np.asarray(matrices['broadband'])@y), float(direct), places=12)
        for matrix in matrices.values():
            self.assertGreaterEqual(np.linalg.eigvalsh(matrix).min(), -1e-12)
        gain = .23
        for name, matrix in studio.covariance(a*gain, f).items():
            np.testing.assert_allclose(matrix, np.asarray(matrices[name])*gain*gain, atol=1e-15)

    def test_zip_preview_shared_gain_and_final_contract(self):
        result = self.result
        items = [result['reference'], result['linear'], *result['checkpoints']]
        self.assertEqual(len(result['checkpoints']), 7)
        self.assertEqual(result['checkpoints'][-1]['stage'], 'final_sample')
        self.assertEqual(result['checkpoints'][-1]['step'], self.config['steps'])
        self.assertEqual(result['checkpoints'][-1]['sigma'], 0)
        json.dumps(result, allow_nan=False)
        with zipfile.ZipFile(io.BytesIO(self.payload)) as archive:
            self.assertEqual(len(archive.namelist()), len(items)+2)
            metadata_text = archive.read('metadata.json').decode()
            self.assertNotIn('preview_wav_base64', metadata_text)
            metadata = json.loads(metadata_text)
            self.assertEqual(metadata['input_sha256'], result['input_sha256'])
            self.assertEqual(metadata['frequency_metric_definitions'], result['frequency_metric_definitions'])
            exported_items = [metadata['reference'], metadata['linear'], *metadata['checkpoints']]
            for item, exported in zip(items, exported_items):
                curves = item['frequency_metrics']
                self.assertEqual(curves, exported['frequency_metrics'])
                self.assertEqual(curves['frequency_hz'], result['frequencies_hz'])
                self.assertEqual(curves['reference_active_channels'], items[0]['frequency_metrics']['reference_active_channels'])
                self.assertEqual(curves['magnitude_floor_absolute'], items[0]['frequency_metrics']['magnitude_floor_absolute'])
                self.assertEqual(curves['channels'], 4)
                self.assertEqual(curves['frames'], result['frames'])
                for name in ('magnitude_spectrum_error_db', 'magnitude_squared_coherence'):
                    self.assertEqual(len(curves[name]), len(result['frequencies_hz']))
                    self.assertTrue(all(value is None or np.isfinite(value) for value in curves[name]))
            for item in items:
                rate, audio = wavfile.read(io.BytesIO(archive.read(item['wav_filename'])))
                self.assertEqual((rate, audio.shape), (16000, (1280, 4)))
                self.assertEqual(audio.dtype, np.float32)
                self.assertLessEqual(float(np.max(abs(audio))), .950001)
                preview_rate, stereo = wavfile.read(io.BytesIO(base64.b64decode(item['preview_wav_base64'])))
                self.assertEqual(preview_rate, rate)
                self.assertEqual(stereo.dtype, np.int16)
                np.testing.assert_allclose(stereo.astype(float)/32767, audio @ studio.PREVIEW_MATRIX.T,
                                           rtol=0, atol=1/32767)
        self.assertEqual(result['metrics']['final'], result['checkpoints'][-1]['metrics'])

    def test_real_sampler_final_matches_export_and_linear_has_same_gain(self):
        seen = {}
        real_sample = studio.sample

        def capture(*args, **kwargs):
            output, trace = real_sample(*args, **kwargs)
            seen['final'] = output.copy()
            return output, trace

        with patch.object(studio, 'sample', side_effect=capture):
            result, payload = studio.run_studio(self.config)
        scale = result['configuration']['observation_rms_scale']
        expected_foa = studio.real_wave_foa(seen['final']*scale)
        expected = inverse_spectra(expected_foa, result['audio'])*result['audio']['shared_gain']
        expected_covariance = studio.covariance(expected_foa*result['audio']['shared_gain'], result['frequencies_hz'])
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            _, actual = wavfile.read(io.BytesIO(archive.read('final_FOA_ACN_N3D.wav')))
            np.testing.assert_array_equal(actual, expected.astype(np.float32))
            data = studio.make_observation(self.config)
            linear, _, _ = encode(data['V'], data['p'], self.config.get('regularization', .001))
            expected_linear = inverse_spectra(studio.real_wave_foa(linear), result['audio'])*result['audio']['shared_gain']
            _, actual_linear = wavfile.read(io.BytesIO(archive.read('linear_FOA_ACN_N3D.wav')))
            np.testing.assert_array_equal(actual_linear, expected_linear.astype(np.float32))
        self.assertEqual(result['checkpoints'][-1]['covariance'], expected_covariance)
        self.assertEqual(result['checkpoints'][-1]['frequency_metrics'], studio.frequency_metrics(
            expected_foa, studio.real_wave_foa(data['reference']), result['frequencies_hz']))

    def test_ring_reports_unobservable_elevation_without_claiming_recovery(self):
        result, _ = studio.run_studio({**self.config, 'geometry': 'ring'})
        self.assertTrue(all(rank < 4 for rank in result['foa_rank_by_frequency']))
        self.assertTrue(any('lacks elevation' in note for note in result['notes']))
        positions = np.asarray(result['microphone_positions_m'])
        np.testing.assert_array_equal(positions[:, 2], 0.)

    def test_large_checkpoint_sets_one_attenuation_for_all_outputs(self):
        def loud_sample(y, ev, denoiser, *, steps, eta_prime, seed, progress, snapshot):
            final = expand(y)*100
            snapshot({'stage': 'denoised_estimate', 'step': 0, 'iteration': 1,
                      'sigma': 20.}, final*2)
            snapshot({'stage': 'final_sample', 'step': steps, 'iteration': steps,
                      'sigma': 0.}, final)
            return final, []

        with patch.object(studio, 'sample', side_effect=loud_sample):
            result, payload = studio.run_studio(self.config)
        gain = result['audio']['shared_gain']
        self.assertLess(gain, 1.)
        self.assertAlmostEqual(gain*result['audio']['unscaled_output_peak'], .95)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            _, linear = wavfile.read(io.BytesIO(archive.read('linear_FOA_ACN_N3D.wav')))
            _, loud = wavfile.read(io.BytesIO(archive.read('denoised_000_FOA_ACN_N3D.wav')))
            np.testing.assert_allclose(loud, linear*200, rtol=1e-6, atol=1e-7)
            self.assertAlmostEqual(float(np.max(abs(loud))), .95, places=6)
        # The visual amplitude changes by that same global gain, not item RMS.
        np.testing.assert_allclose(result['checkpoints'][0]['covariance']['broadband'],
                                   np.asarray(result['linear']['covariance']['broadband'])*200**2,
                                   rtol=1e-12, atol=1e-14)


if __name__ == '__main__':
    unittest.main()
