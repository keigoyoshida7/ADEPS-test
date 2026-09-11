"""Checks for input-only conditioning and the exported trained estimator."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from spatial_model import FEATURES, SpatialModel, features, unpack


class SpatialModelTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(521)
        self.linear = self.rng.normal(size=(3, 36, 7)) + 1j*self.rng.normal(size=(3, 36, 7))
        a = self.rng.normal(size=(3, 5, 36)) + 1j*self.rng.normal(size=(3, 5, 36))
        self.resolution = np.linalg.pinv(a) @ a
        self.frequency = np.array([20., 1500., 20000.])

    def test_scale_and_temporal_context_are_observation_only(self):
        x, scale = features(self.linear, self.resolution, self.frequency)
        self.assertEqual(x.shape, (21, FEATURES))
        np.testing.assert_allclose(unpack(x[:, :72], scale, self.linear.shape), self.linear, rtol=2e-7)
        scaled, scale2 = features(self.linear * 17.2, self.resolution, self.frequency)
        np.testing.assert_allclose(x, scaled, rtol=2e-7, atol=2e-7)
        np.testing.assert_allclose(scale2, scale * 17.2)
        # A common phase rotation leaves covariance/power conditioning intact.
        rotated, _ = features(self.linear*np.exp(.8j), self.resolution, self.frequency)
        np.testing.assert_allclose(x[:, 397:], rotated[:, 397:], rtol=2e-7, atol=2e-7)
        # Reordering temporal frames changes only the current-bin features.
        reversed_x, _ = features(self.linear[:, :, ::-1], self.resolution, self.frequency)
        np.testing.assert_allclose(x.reshape(3,7,-1)[:,::-1], reversed_x.reshape(3,7,-1), rtol=2e-7, atol=2e-7)

    def test_reject_malformed_or_nonfinite_observation(self):
        with self.assertRaises(ValueError):
            features(self.linear[:, :4], self.resolution, self.frequency)
        with self.assertRaises(ValueError):
            features(self.linear, self.resolution[:, :4], self.frequency)
        with self.assertRaises(ValueError):
            features(self.linear, self.resolution, [20, -1, 20000])
        broken = self.linear.copy(); broken[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            features(broken, self.resolution, self.frequency)

    def test_zero_residual_is_exact_unchanged_linear_and_checks_integrity(self):
        hidden = 32
        sizes = [FEATURES, hidden, hidden, hidden, hidden, 72]
        weights = {f'{kind}{i}': np.zeros(((sizes[i-1],sizes[i]) if kind=='w' else (sizes[i],)),np.float32)
                   for i in range(1,6) for kind in ('w','b')}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory/'spatial-v1.npz'
            np.savez(path, **weights)
            card = {'schema':'adeps-test-physics-residual/1','hidden_channels':hidden,'hidden_layers':4,
                    'weights_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            (directory/'spatial-v1.json').write_text(json.dumps(card))
            model = SpatialModel.load(path)
            actual = model.predict(self.linear, self.resolution, self.frequency)
            np.testing.assert_allclose(actual, self.linear, rtol=2e-7, atol=2e-7)
            np.testing.assert_array_equal(model.predict(np.zeros_like(self.linear), self.resolution, self.frequency), 0)
            path.write_bytes(path.read_bytes()+b'tamper')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                SpatialModel(directory)

    def test_published_trained_export_matches_pytorch(self):
        try:
            import torch
        except ImportError:
            self.skipTest('Training-only PyTorch dependency is not installed')
        model = SpatialModel()
        spec = importlib.util.spec_from_file_location('train_spatial_for_test', ROOT/'scripts/train_spatial_model.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        network = module.Network(model.card['hidden_channels'])
        with torch.no_grad():
            for i, layer in enumerate(network.layers, start=1):
                layer.weight.copy_(torch.from_numpy(model.weights[f'w{i}'].T.copy()))
                layer.bias.copy_(torch.from_numpy(model.weights[f'b{i}']))
        x, _ = features(self.linear, self.resolution, self.frequency)
        with torch.no_grad():
            expected = network(torch.from_numpy(x)).numpy()
        actual = model.predict_features(x, batch_size=5)
        np.testing.assert_allclose(actual, expected, rtol=3e-4, atol=3e-5)
        self.assertEqual(sum(w.size for w in model.weights.values()), model.card['parameter_count'])
        self.assertGreater(model.card['training']['steps'], 0)
        self.assertTrue(model.card['export_parity']['passed'])


if __name__ == '__main__':
    unittest.main()
