"""Optional PyTorch tests: python -m unittest discover -s training_tests.

Kept outside browser/numerical CI, which does not require PyTorch. The small
width below exercises the same architecture; production size is checked too.
"""
import io
import math
import sys
import unittest
from pathlib import Path

import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from paper_prior import FIRResample, PaperDenoiser

torch.set_num_threads(2)


class PaperPriorTests(unittest.TestCase):
    def make_model(self, checkpointing=False):
        return PaperDenoiser(sigma_data=1., base_channels=8,
                             gradient_checkpointing=checkpointing)

    def test_production_size_is_real_30m_architecture(self):
        model = PaperDenoiser(sigma_data=1.)
        self.assertEqual(model.parameter_count(), 30_781_344)
        self.assertEqual([block.conv1.out_channels for block in model.model.down_blocks],
                         [128, 256, 256, 256])
        self.assertEqual(len(model.model.output_heads), 4)
        self.assertEqual(len(model.model.downsample), 3)
        self.assertTrue(model.model.gradient_checkpointing)

    def test_arbitrary_stft_size_and_all_parameter_paths(self):
        torch.manual_seed(8102)
        model = self.make_model(True)
        x = torch.randn(2, 72, 17, 11, requires_grad=True)
        y = model(x, torch.tensor([.002, 80.]))
        self.assertEqual(y.shape, x.shape)
        self.assertTrue(torch.isfinite(y).all())
        y.square().mean().backward()
        self.assertTrue(torch.isfinite(x.grad).all())
        for name, parameter in model.named_parameters():
            self.assertIsNotNone(parameter.grad, name)
            self.assertTrue(torch.isfinite(parameter.grad).all(), name)

    def test_257_frequency_32_frames(self):
        model = self.make_model().eval()
        with torch.no_grad():
            result = model(torch.randn(1, 72, 257, 32), torch.tensor([1.]))
        self.assertEqual(tuple(result.shape), (1, 72, 257, 32))
        self.assertTrue(torch.isfinite(result).all())

    def test_edm_coefficients_independently(self):
        class ConstantBackbone(nn.Module):
            def forward(self, x, noise):
                self.received = (x.detach().clone(), noise.detach().clone())
                return torch.full_like(x, 2.)

        model = self.make_model()
        model.model = ConstantBackbone()
        x = torch.ones(2, 72, 3, 2)
        sigma = torch.tensor([.5, 2.])
        output = model(x, sigma)
        for i, s in enumerate([.5, 2.]):
            expected = 1 / (s * s + 1) + 2 * s / math.sqrt(s * s + 1)
            torch.testing.assert_close(output[i], torch.full_like(output[i], expected))
            torch.testing.assert_close(model.model.received[0][i], x[i] / math.sqrt(s * s + 1))
            self.assertAlmostEqual(model.model.received[1][i].item(), math.log(s) / 4, places=6)

    def test_checkpointed_forward_and_gradients_match(self):
        torch.manual_seed(512)
        normal, checked = self.make_model(False), self.make_model(True)
        checked.load_state_dict(normal.state_dict())
        x = torch.randn(2, 72, 16, 8)
        sigma = torch.tensor([.1, 3.])
        a, b = normal(x, sigma), checked(x, sigma)
        torch.testing.assert_close(a, b, rtol=0, atol=0)
        a.square().mean().backward()
        b.square().mean().backward()
        for p, q in zip(normal.parameters(), checked.parameters()):
            torch.testing.assert_close(p.grad, q.grad, rtol=1e-5, atol=1e-7)

    def test_batch_independence_and_noise_condition(self):
        torch.manual_seed(72)
        model = self.make_model().eval()
        x = torch.randn(2, 72, 16, 8)
        with torch.no_grad():
            together = model(x, torch.tensor([1., 3.]))
            alone = model(x[:1], torch.tensor([1.]))
            other_noise = model.model(x[:1], torch.tensor([2.]))
            first_noise = model.model(x[:1], torch.tensor([1.]))
        torch.testing.assert_close(together[:1], alone, rtol=2e-5, atol=1e-6)
        self.assertGreater((other_noise - first_noise).abs().max().item(), 1e-6)

    def test_config_and_weights_roundtrip(self):
        model = self.make_model().eval()
        buffer = io.BytesIO()
        torch.save({'config': model.config_dict(), 'weights': model.state_dict()}, buffer)
        buffer.seek(0)
        saved = torch.load(buffer, weights_only=True)
        restored = PaperDenoiser(**saved['config']).eval()
        restored.load_state_dict(saved['weights'])
        x, sigma = torch.randn(1, 72, 8, 8), torch.tensor([.2])
        with torch.no_grad():
            torch.testing.assert_close(model(x, sigma), restored(x, sigma), rtol=0, atol=0)

    def test_resampling_shape_and_interior_dc_gain(self):
        constant = torch.ones(1, 4, 16, 16, requires_grad=True)
        down = FIRResample(False)(constant)
        up = FIRResample(True)(constant)
        self.assertEqual(tuple(down.shape), (1, 4, 8, 8))
        self.assertEqual(tuple(up.shape), (1, 4, 32, 32))
        torch.testing.assert_close(down[..., 2:-2, 2:-2], torch.ones_like(down[..., 2:-2, 2:-2]))
        torch.testing.assert_close(up[..., 4:-4, 4:-4], torch.ones_like(up[..., 4:-4, 4:-4]))
        up.sum().backward()
        self.assertTrue(torch.isfinite(constant.grad).all())

    def test_invalid_parameters_shapes_and_sigmas(self):
        for config in ({'sigma_data': 0}, {'sigma_data': float('nan')}, {'base_channels': 7},
                       {'channel_mult': [1, 2]}, {'dropout': 1.}):
            with self.assertRaises(ValueError):
                PaperDenoiser(**config)
        model = self.make_model()
        x = torch.randn(1, 72, 8, 8)
        for sigma in (torch.tensor([0.]), torch.tensor([-1.]), torch.tensor([float('inf')]),
                      torch.tensor([float('nan')]), torch.tensor([[1.]]), torch.tensor([1., 2.])):
            with self.assertRaises(ValueError):
                model(x, sigma)
        for bad in (x[:, :36], x[0], torch.ones(1, 72, 8, 8, dtype=torch.int64)):
            with self.assertRaises(ValueError):
                model(bad, torch.tensor([1.]))


if __name__ == '__main__':
    unittest.main()
