"""Independent NCSN++M-derived N5 Ambisonics denoising prior with EDM scaling.

This is not an official ADEPS implementation/checkpoint or an exact reproduction.
The ADEPS repository contains only a README at the time of implementation. ADEPS
discloses NCSN++M, 36 complex channels, adaLN and 30.8M parameters, but not the
complete network configuration or adaLN placement. We retain the author's M
widths (128; 1,2,2,2), one encoder/two decoder residual blocks per level, BigGAN
resampling blocks, FIR [1,3,3,1], progressive input/output and middle attention.
Our explicit choices: channelwise adaLN at each residual block's second norm,
one attention head, small nonzero residual/output initialization, right zero
padding to a multiple of eight, and EDM preconditioning (without score /sigma).

Independent code written from the published architecture, not vendored code.
Sources:
https://arxiv.org/html/2608.24558v3 (Sections 3.3, 4)
https://github.com/sp-uhh/sgmse/blob/c1399bfb700e96ad49257def4e4edf8fe61e4acc/sgmse/backbones/ncsnpp.py
https://github.com/facebookresearch/DiT/blob/main/models.py (adaLN mechanism)
https://arxiv.org/abs/2206.00364 (EDM preconditioning, Table 1)
Upstream SGMSE root license is MIT; its NCSN++ source headers are Apache-2.0.

Input/output are H(a) in [batch,72,frequency,time]: first 36 real ACN/N3D
coefficients, then their 36 imaginary parts. No microphone positions, V, or
linearly encoded observations condition this prior. Compression, dataset
scaling, STFT, training noise/loss and posterior sampling belong to the caller.
"""
from __future__ import annotations

import math
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint


class ChannelNorm(nn.Module):
    """True layer normalization over feature channels at each time/frequency."""

    def forward(self, x: Tensor) -> Tensor:
        return F.layer_norm(x.movedim(1, -1), (x.shape[1],), eps=1e-6).movedim(-1, 1)


def _groups(channels: int) -> int:
    return math.gcd(channels, min(channels // 4, 32))


class FIRResample(nn.Module):
    """Separable 4-tap binomial low-pass, with explicit zero insertion for up."""

    def __init__(self, up: bool):
        super().__init__()
        tap = torch.tensor([1., 3., 3., 1.]) / 8
        self.register_buffer('kernel', torch.outer(tap, tap)[None, None])
        self.up = up

    def forward(self, x: Tensor) -> Tensor:
        channels = x.shape[1]
        kernel = self.kernel.to(dtype=x.dtype).expand(channels, 1, 4, 4)
        if self.up:
            expanded = x.new_zeros(x.shape[0], channels, x.shape[2] * 2, x.shape[3] * 2)
            expanded[:, :, ::2, ::2] = x
            return F.conv2d(F.pad(expanded, (1, 2, 1, 2)), kernel * 4, groups=channels)
        return F.conv2d(x, kernel, stride=2, padding=1, groups=channels)


class ResidualBlock(nn.Module):
    """BigGAN-style resampling block with noise-conditioned second adaLN."""

    def __init__(self, incoming: int, outgoing: int, embedding: int,
                 resample: str | None = None, dropout: float = 0.):
        super().__init__()
        self.norm1 = nn.GroupNorm(_groups(incoming), incoming, eps=1e-6)
        self.conv1 = nn.Conv2d(incoming, outgoing, 3, padding=1)
        self.norm2 = ChannelNorm()
        self.modulation = nn.Linear(embedding, outgoing * 2)
        self.dropout = nn.Dropout(dropout)
        self.conv2 = nn.Conv2d(outgoing, outgoing, 3, padding=1)
        self.skip = nn.Conv2d(incoming, outgoing, 1) if incoming != outgoing or resample else nn.Identity()
        self.resample = FIRResample(resample == 'up') if resample else nn.Identity()
        nn.init.normal_(self.conv2.weight, std=1e-3)
        nn.init.zeros_(self.conv2.bias)
        nn.init.normal_(self.modulation.weight, std=1e-3)
        nn.init.zeros_(self.modulation.bias)

    def forward(self, x: Tensor, embedding: Tensor) -> Tensor:
        h = self.resample(F.silu(self.norm1(x)))
        h = self.conv1(h)
        shift, scale = self.modulation(F.silu(embedding)).chunk(2, dim=1)
        h = self.norm2(h) * (1 + scale[:, :, None, None]) + shift[:, :, None, None]
        h = self.conv2(self.dropout(F.silu(h)))
        return (self.skip(self.resample(x)) + h) / math.sqrt(2)


class MiddleAttention(nn.Module):
    """Single-head attention over downsampled time/frequency tokens only."""

    def __init__(self, channels: int):
        super().__init__()
        self.norm = nn.GroupNorm(_groups(channels), channels, eps=1e-6)
        self.qkv = nn.Conv2d(channels, channels * 3, 1)
        self.output = nn.Conv2d(channels, channels, 1)
        nn.init.normal_(self.output.weight, std=1e-3)
        nn.init.zeros_(self.output.bias)

    def forward(self, x: Tensor) -> Tensor:
        batch, channels, frequency, time = x.shape
        q, k, v = self.qkv(self.norm(x)).flatten(2).transpose(1, 2).chunk(3, dim=-1)
        h = F.scaled_dot_product_attention(q[:, None], k[:, None], v[:, None])
        h = h[:, 0].transpose(1, 2).reshape(batch, channels, frequency, time)
        return (x + self.output(h)) / math.sqrt(2)


class NCSNppMBackbone(nn.Module):
    def __init__(self, base_channels: int, channel_mult: tuple[int, ...],
                 gradient_checkpointing: bool, dropout: float):
        super().__init__()
        self.gradient_checkpointing = gradient_checkpointing
        self.levels = len(channel_mult)
        width = base_channels
        embedding = width * 4
        self.register_buffer('fourier_frequencies', torch.randn(width) * 16)
        self.embedding = nn.Sequential(nn.Linear(width * 2, embedding), nn.SiLU(),
                                       nn.Linear(embedding, embedding))
        self.input = nn.Conv2d(72, width, 3, padding=1)
        self.down_blocks = nn.ModuleList()
        self.downsample = nn.ModuleList()
        self.input_projection = nn.ModuleList()
        self.pyramid_down = FIRResample(False)
        self.pyramid_up = FIRResample(True)
        skip_channels = [width]
        channels = width
        for i, multiplier in enumerate(channel_mult):
            out = width * multiplier
            self.down_blocks.append(ResidualBlock(channels, out, embedding, dropout=dropout))
            channels = out
            skip_channels.append(channels)
            if i < self.levels - 1:
                self.downsample.append(ResidualBlock(channels, channels, embedding, 'down', dropout))
                self.input_projection.append(nn.Conv2d(72, channels, 1))
                skip_channels.append(channels)
        self.middle1 = ResidualBlock(channels, channels, embedding, dropout=dropout)
        self.attention = MiddleAttention(channels)
        self.middle2 = ResidualBlock(channels, channels, embedding, dropout=dropout)
        self.up_blocks = nn.ModuleList()
        self.upsample = nn.ModuleList()
        self.output_heads = nn.ModuleList()
        for i in reversed(range(self.levels)):
            out = width * channel_mult[i]
            blocks = nn.ModuleList()
            for _ in range(2):
                blocks.append(ResidualBlock(channels + skip_channels.pop(), out, embedding, dropout=dropout))
                channels = out
            self.up_blocks.append(blocks)
            head = nn.Sequential(nn.GroupNorm(_groups(channels), channels, eps=1e-6), nn.SiLU(),
                                 nn.Conv2d(channels, 72, 3, padding=1))
            nn.init.normal_(head[-1].weight, std=1e-3)
            nn.init.zeros_(head[-1].bias)
            self.output_heads.append(head)
            if i:
                self.upsample.append(ResidualBlock(channels, channels, embedding, 'up', dropout))
        assert not skip_channels

    def _run(self, module: nn.Module, *args: Tensor) -> Tensor:
        if self.gradient_checkpointing and self.training and torch.is_grad_enabled():
            return checkpoint(module, *args, use_reentrant=False)
        return module(*args)

    def forward(self, x: Tensor, noise_condition: Tensor) -> Tensor:
        frequency, time = x.shape[-2:]
        multiple = 2 ** (self.levels - 1)
        x = F.pad(x, (0, (-time) % multiple, 0, (-frequency) % multiple))
        phase = 2 * math.pi * noise_condition[:, None] * self.fourier_frequencies[None]
        embedding = self.embedding(torch.cat([torch.sin(phase), torch.cos(phase)], dim=1))
        h = self.input(x)
        skips = [h]
        pyramid = x
        for i, block in enumerate(self.down_blocks):
            h = self._run(block, h, embedding)
            skips.append(h)
            if i < self.levels - 1:
                h = self._run(self.downsample[i], h, embedding)
                pyramid = self.pyramid_down(pyramid)
                h = (h + self.input_projection[i](pyramid)) / math.sqrt(2)
                skips.append(h)
        h = self._run(self.middle1, h, embedding)
        h = self._run(self.attention, h)
        h = self._run(self.middle2, h, embedding)
        output = None
        for i, blocks in enumerate(self.up_blocks):
            for block in blocks:
                h = self._run(block, torch.cat([h, skips.pop()], dim=1), embedding)
            level_output = self.output_heads[i](h)
            output = level_output if output is None else self.pyramid_up(output) + level_output
            if i < self.levels - 1:
                h = self._run(self.upsample[i], h, embedding)
        return output[:, :, :frequency, :time]


class PaperDenoiser(nn.Module):
    """N5 prior D(x,sigma); sigma_data=.5 is an explicit EDM default, not a paper fact.

    sigma_data must describe the chosen normalized, compressed training domain.
    Keep it and the complex ordering with checkpoints. Input sigma must be
    positive; do not evaluate the network at the sampler's final sigma=0.
    Reducing base_channels is supported for unit tests, not the default model.
    """

    def __init__(self, sigma_data: float = .5, base_channels: int = 128,
                 channel_mult: tuple[int, ...] = (1, 2, 2, 2),
                 gradient_checkpointing: bool = True, dropout: float = 0.):
        super().__init__()
        if not math.isfinite(sigma_data) or sigma_data <= 0:
            raise ValueError('sigma_data must be finite and positive')
        if base_channels < 8 or base_channels % 4:
            raise ValueError('base_channels must be >= 8 and divisible by 4')
        if len(channel_mult) != 4 or any(not isinstance(c, int) or c < 1 for c in channel_mult):
            raise ValueError('channel_mult must contain four positive integer multipliers')
        if not 0 <= dropout < 1:
            raise ValueError('dropout must be in [0,1)')
        self.sigma_data = float(sigma_data)
        self.base_channels = base_channels
        self.channel_mult = tuple(channel_mult)
        self.dropout = float(dropout)
        self.model = NCSNppMBackbone(base_channels, self.channel_mult, gradient_checkpointing, dropout)

    def config_dict(self) -> dict[str, Any]:
        """Constructor arguments only, suitable for PaperDenoiser(**checkpoint['config'])."""
        return {'sigma_data': self.sigma_data, 'base_channels': self.base_channels,
                'channel_mult': list(self.channel_mult),
                'gradient_checkpointing': self.model.gradient_checkpointing, 'dropout': self.dropout}

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def forward(self, x: Tensor, sigma: Tensor) -> Tensor:
        if x.ndim != 4 or x.shape[1] != 72 or min(x.shape[0], *x.shape[2:]) < 1 or not x.is_floating_point():
            raise ValueError('x must be real floating [batch,72,frequency,time] with positive dimensions')
        if sigma.ndim != 1 or sigma.shape[0] != x.shape[0]:
            raise ValueError('sigma must have shape [batch]')
        if not torch.isfinite(sigma).all().item() or not (sigma > 0).all().item():
            raise ValueError('sigma must be finite and positive; final zero belongs to the sampler')
        x = x.float()
        sigma = sigma.to(device=x.device, dtype=torch.float32).reshape(-1, 1, 1, 1)
        denominator = sigma.square() + self.sigma_data ** 2
        c_in = denominator.rsqrt()
        c_skip = self.sigma_data ** 2 / denominator
        c_out = sigma * self.sigma_data * c_in
        prediction = self.model(c_in * x, sigma.flatten().log() / 4)
        return c_skip * x + c_out * prediction.float()
