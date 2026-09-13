"""Independent CPU tests of the finite STFT convention and joint baseline."""
import json
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np
from scipy.signal import stft, istft

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from plus_consistency import analyze_waveform, synthesize_spectra, project_stft, reconstruct
from plus_reconstruction import proximal_correction


class ConsistencyTests(unittest.TestCase):
    def test_matches_independent_scipy_unpadded_analysis_and_inverse(self):
        rng = np.random.default_rng(87)
        wave = rng.normal(size=(4, 512 + 31 * 128))
        _, _, expected = stft(wave, fs=16000, window='hann', nperseg=512,
            noverlap=384, nfft=512, boundary=None, padded=False, axis=-1, scaling='spectrum')
        actual = analyze_waveform(wave)
        np.testing.assert_allclose(actual, expected.transpose(1, 0, 2), atol=5e-17)
        reconstructed = synthesize_spectra(actual)
        self.assertEqual(reconstructed.shape, wave.shape)
        np.testing.assert_array_equal(reconstructed[:, 0], 0.)
        np.testing.assert_allclose(reconstructed[:, 1:], wave[:, 1:], atol=3e-12)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)  # Initial Hann-zero sample only.
            _, scipy_wave = istft(expected, fs=16000, window='hann', nperseg=512,
                noverlap=384, nfft=512, input_onesided=True, boundary=False, scaling='spectrum')
        np.testing.assert_allclose(reconstructed, scipy_wave, atol=4e-12)

    def test_idempotent_for_arbitrary_spectra_and_keeps_legitimate_dc(self):
        rng = np.random.default_rng(94)
        spectra = rng.normal(size=(257, 4, 5)) + 1j * rng.normal(size=(257, 4, 5))
        saved = spectra.copy()
        projected = project_stft(spectra)
        np.testing.assert_allclose(project_stft(projected), projected, atol=2e-15)
        np.testing.assert_array_equal(projected[[0, -1]].imag, 0.)
        np.testing.assert_array_equal(spectra, saved)
        constant = analyze_waveform(np.full((2, 512 + 4 * 128), 3.))
        np.testing.assert_allclose(constant[0], 3., atol=1e-14)
        np.testing.assert_allclose(project_stft(constant), constant, atol=1e-14)

    def test_projection_is_orthogonal_in_conjugate_symmetric_metric(self):
        rng = np.random.default_rng(410)
        raw = rng.normal(size=(257, 2, 4)) + 1j * rng.normal(size=(257, 2, 4))
        consistent = analyze_waveform(rng.normal(size=(2, 512 + 3 * 128)))
        error = raw - project_stft(raw)
        weights = np.full(257, 2.)
        weights[[0, -1]] = 1.
        inner = np.real(np.sum(weights[:, None, None] * error.conj() * consistent))
        self.assertAlmostEqual(inner, 0., places=12)

    def test_joint_loop_matches_uncached_closed_form_and_reports_final_residual(self):
        rng = np.random.default_rng(518)
        n_fft, hop, frames = 16, 4, 4
        v = rng.normal(size=(9, 2, 3)) + 1j * rng.normal(size=(9, 2, 3))
        v[[0, -1]] = v[[0, -1]].real
        truth = analyze_waveform(rng.normal(size=(3, n_fft + (frames - 1) * hop)), n_fft=n_fft, hop=hop)
        p = v @ truth
        initial = .2 * (rng.normal(size=truth.shape) + 1j * rng.normal(size=truth.shape))
        expected = initial.copy()
        for _ in range(3):
            expected = project_stft(expected, n_fft=n_fft, hop=hop)
            expected, _ = proximal_correction(expected, p, v, ridge_relative=.02)
        expected = project_stft(expected, n_fft=n_fft, hop=hop)
        result = reconstruct(p, v, initial=initial, iterations=3, ridge_relative=.02, n_fft=n_fft, hop=hop)
        np.testing.assert_allclose(result['estimate'], expected, atol=2e-15)
        self.assertEqual(result['nfe'], 0)
        self.assertEqual(len(result['trace']), 3)
        self.assertLess(result['final_consistency_relative'], 2e-15)
        self.assertAlmostEqual(result['final_pressure_residual']['norm'], np.linalg.norm(p - v @ expected))
        json.dumps({k: val for k, val in result.items() if k != 'estimate'}, allow_nan=False)

    def test_single_frame_zero_and_input_validation(self):
        raw = np.ones((257, 1, 1), complex)
        self.assertEqual(synthesize_spectra(raw).shape, (1, 512))
        np.testing.assert_allclose(project_stft(project_stft(raw)), project_stft(raw), atol=1e-14)
        np.testing.assert_array_equal(project_stft(np.zeros_like(raw)), 0.)
        for kwargs in ({'n_fft': 511}, {'hop': 512}, {'hop': 0}):
            with self.assertRaises(ValueError):
                project_stft(raw, **kwargs)
        for bad in (raw * np.nan, raw[:256], raw[:, :, :0]):
            with self.assertRaises(ValueError):
                project_stft(bad)
        with self.assertRaises(ValueError):
            analyze_waveform(np.ones((2, 513)))
        with self.assertRaises(ValueError):
            analyze_waveform(np.ones((2, 512), complex))


if __name__ == '__main__':
    unittest.main(verbosity=2)
