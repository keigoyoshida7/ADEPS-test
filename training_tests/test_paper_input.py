"""Small NPZ provenance tests; no Torch, corpus, trained model, or GPU."""
import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import infer_paper_prior as inference


class PaperInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.path = self.folder/'fixture.npz'
        self.fields = {
            'frequencies_hz': np.fft.rfftfreq(512, 1/16000),
            'p_real': np.arange(257*4*3, dtype=float).reshape(257, 4, 3)/1000,
            'p_imag': np.full((257, 4, 3), .17),
            'V_real': np.full((257, 4, 36), .21),
            'V_imag': np.full((257, 4, 36), -.31),
            'sample_rate_hz': 16000, 'n_fft': 512, 'hop': 128,
            'sh_ordering': 'ACN', 'sh_normalization': 'N3D',
            'attribution_json': json.dumps({'title': 'In-memory numerical fixture, not recorded audio'}),
            'provenance_json': json.dumps({'fixture': True}),
            'audio_json': json.dumps({'sample_rate_hz': 16000, 'n_fft': 512, 'hop': 128}),
        }
        digest = hashlib.sha256()
        for key in ('frequencies_hz', 'V_real', 'V_imag', 'p_real', 'p_imag'):
            value = self.fields[key]
            digest.update(json.dumps(list(value.shape)).encode())
            digest.update(np.ascontiguousarray(value, dtype='<f8').tobytes())
        self.expected_hash = digest.hexdigest()

    def save(self, **overrides):
        np.savez_compressed(self.path, **{**self.fields, **overrides})

    def test_computes_actual_observation_identity_and_retains_credit(self):
        for declaration in ({}, {'observation_sha256': self.expected_hash}):
            with self.subTest(declared=bool(declaration)):
                self.save(**declaration)
                result = inference.load_input(self.path)
                self.assertEqual(result['observation_sha256'], self.expected_hash)
                self.assertEqual(result['provenance']['observation_sha256'], self.expected_hash)
                self.assertEqual(result['input_file_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
                self.assertEqual(result['provenance']['attribution'], json.loads(self.fields['attribution_json']))
                self.assertEqual(result['provenance']['provenance'], {'fixture': True})
                self.assertEqual(result['provenance']['audio'], json.loads(self.fields['audio_json']))
                np.testing.assert_array_equal(result['p'], self.fields['p_real']+1j*self.fields['p_imag'])
                np.testing.assert_array_equal(result['V'], self.fields['V_real']+1j*self.fields['V_imag'])

    def test_tampered_declared_hash_fails_before_model_loading(self):
        self.save(observation_sha256='0'*64)
        fake_backend = types.ModuleType('paper_inference')
        fake_backend.PaperPrior = Mock(side_effect=AssertionError('Model must not load'))
        fake_backend.reconstruct = Mock()
        with patch.dict(sys.modules, {'paper_inference': fake_backend}), patch.object(sys, 'argv',
                ['infer_paper_prior.py', '--input', str(self.path), '--checkpoint', 'nonexistent',
                 '--output', str(self.folder/'output.npz')]):
            with self.assertRaisesRegex(ValueError, 'does not match the actual NPZ arrays'):
                inference.main()
        fake_backend.PaperPrior.assert_not_called()
        fake_backend.reconstruct.assert_not_called()
        self.assertFalse((self.folder/'output.npz').exists())

    def test_actual_array_tampering_invalidates_a_previously_valid_hash(self):
        changed = self.fields['p_real'].copy()
        changed[31, 2, 1] += .001
        self.save(p_real=changed, observation_sha256=self.expected_hash)
        with self.assertRaisesRegex(ValueError, 'observation_sha256'):
            inference.load_input(self.path)

    def test_rejects_broadcast_imaginary_shape_and_fractional_stft_metadata(self):
        for change in ({'p_imag': self.fields['p_imag'][..., 0]},
                       {'sample_rate_hz': 16000.5}, {'hop': True},
                       {'frequencies_hz': np.geomspace(1., 8000., 257)},
                       {'V_real': np.full((257, 4, 36), np.nan)}):
            with self.subTest(change=list(change)):
                self.save(**change)
                with self.assertRaises(ValueError):
                    inference.load_input(self.path)

    def test_cli_output_retains_computed_identity_stft_and_credit(self):
        self.save(observation_sha256=self.expected_hash)
        fake_backend = types.ModuleType('paper_inference')
        fake_backend.PaperPrior = Mock(return_value=object())
        fake_backend.reconstruct = Mock(return_value={
            'linear': np.ones((257, 36, 3), dtype=complex),
            'neural': np.full((257, 36, 3), 2+3j), 'trace': [],
            'model': {'id': 'test-fixture-not-a-model'}, 'observation_rms_scale': .1,
        })
        output = self.folder/'output.npz'
        with patch.dict(sys.modules, {'paper_inference': fake_backend}), patch.object(sys, 'argv',
                ['infer_paper_prior.py', '--input', str(self.path), '--checkpoint', 'mocked',
                 '--output', str(output), '--device', 'cpu']):
            inference.main()
        with np.load(output, allow_pickle=False) as data:
            self.assertEqual(str(data['observation_sha256']), self.expected_hash)
            np.testing.assert_array_equal(data['frequencies_hz'], self.fields['frequencies_hz'])
            self.assertEqual((int(data['sample_rate_hz']), int(data['n_fft']), int(data['hop'])), (16000, 512, 128))
            stored = json.loads(str(data['input_provenance_json']))
            self.assertEqual(stored['attribution'], json.loads(self.fields['attribution_json']))
        metadata = json.loads(output.with_suffix('.json').read_text())
        self.assertEqual(metadata['observation_sha256'], self.expected_hash)
        self.assertEqual(metadata['input_provenance'], stored)
        self.assertEqual(metadata['input_file_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertIs(metadata['official_model'], False)
        self.assertIs(metadata['paper_performance_reproduced'], False)


if __name__ == '__main__':
    unittest.main()
