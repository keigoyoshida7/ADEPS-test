"""Train the independent test prior. Requires PyTorch; inference does not.

Default data are procedural complex spatial vectors, not speech/room recordings.
Optional --hoa-npz must contain clean coefficients a_real/a_imag [samples,36],
already real ACN/N3D and scaled to the intended normalized inference range.
No microphone geometry or transfer matrix is provided to the learned model.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from capture import real_n3d
from neural import compress


def vectors(count, seed):
    rng = np.random.default_rng(seed)
    directions = rng.normal(size=(count * 5, 3))
    harmonics = real_n3d(5, directions).reshape(count, 5, 36)
    amplitudes = (rng.normal(size=(count, 5)) + 1j*rng.normal(size=(count, 5))) / np.sqrt(2)
    amplitudes *= np.array([1., .7, .22, .15, .1])
    amplitudes[:, 1] *= rng.integers(0, 2, size=count)
    a = np.einsum('nsc,ns->nc', harmonics, amplitudes)
    a *= np.exp(rng.normal(0, .35, (count, 1)))
    return a


class Network(nn.Module):
    def __init__(self, hidden=96, sigma_data=2.):
        super().__init__()
        self.l1 = nn.Linear(80, hidden)
        self.l2 = nn.Linear(hidden, hidden)
        self.l3 = nn.Linear(hidden, 72)
        self.sd = sigma_data

    def forward(self, x, sigma):
        cin = 1 / torch.sqrt(sigma**2 + self.sd**2)
        skip = self.sd**2 / (sigma**2 + self.sd**2)
        cout = sigma * self.sd * cin
        phase = torch.log(sigma)/4 * x.new_tensor([1., 2., 4., 8.])
        z = torch.cat([cin*x, torch.sin(phase), torch.cos(phase)], dim=1)
        z = torch.nn.functional.silu(self.l1(z))
        z = torch.nn.functional.silu(self.l2(z))
        return skip*x + cout*self.l3(z)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=int, default=4000)
    parser.add_argument('--seed', type=int, default=7319)
    parser.add_argument('--hidden', type=int, default=96)
    parser.add_argument('--hoa-npz', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'public/models')
    args = parser.parse_args()
    torch.set_num_threads(3)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    if args.hoa_npz:
        with np.load(args.hoa_npz, allow_pickle=False) as data:
            a = data['a_real'] + 1j * data['a_imag']
        if a.ndim != 2 or a.shape[1] != 36 or len(a) < 2000 or not np.all(np.isfinite(a)):
            raise ValueError('Expected at least 2000 finite complex [samples,36] clean ACN/N3D vectors')
        a = a[rng.permutation(len(a))]
        train, valid = a[:-1024], a[-1024:]
        data_description = 'User-provided clean HOA vectors; random held-out vectors (not a held-out room/speaker split)'
        source_hash = hashlib.sha256(args.hoa_npz.read_bytes()).hexdigest()
    else:
        train, valid = vectors(48000, args.seed), vectors(2048, args.seed+1)
        data_description = 'Procedural independent 36-coefficient complex vectors: 1–2 plane waves plus 3 weak rays; randomized directions/phases/gains. No speech, HARP, or measured room data.'
        source_hash = None
    def convert(a):
        h = compress(a)
        return torch.tensor(np.c_[h.real, h.imag], dtype=torch.float32)
    clean, validation = convert(train), convert(valid)
    sd = float(clean.square().mean().sqrt())
    net = Network(args.hidden, sd)
    optimizer = torch.optim.AdamW(net.parameters(), lr=.001, weight_decay=.0001)
    generator = torch.Generator().manual_seed(args.seed+2)
    sigmas = torch.exp(torch.linspace(np.log(.03), np.log(10.), 6))
    noise = torch.randn(validation.shape, generator=generator)
    def evaluate():
        with torch.no_grad():
            return [{'sigma': float(s), 'noisy_mse': float((s*noise).square().mean()),
                     'denoised_mse': float((net(validation+s*noise, s.expand(len(validation),1))-validation).square().mean())}
                    for s in sigmas]
    initial = evaluate()
    started = time.perf_counter()
    log = []
    for step in range(args.steps):
        target = clean[torch.randint(len(clean), (512,))]
        sigma = torch.exp(torch.rand(512,1)*(np.log(80)-np.log(.002))+np.log(.002))
        noisy = target + sigma * torch.randn_like(target)
        weight = (sigma**2+sd**2)/(sigma*sd)**2
        loss = (weight*(net(noisy,sigma)-target).square()).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        if (step+1)%500 == 0 or step == args.steps-1:
            row = {'step': step+1, 'weighted_training_loss': float(loss.detach()),
                   'seconds': round(time.perf_counter()-started, 2)}
            log.append(row)
            print(json.dumps(row), flush=True)
    final = evaluate()
    args.output.mkdir(parents=True, exist_ok=True)
    weights = {}
    for i in (1,2,3):
        layer = getattr(net, f'l{i}')
        weights[f'w{i}'] = layer.weight.detach().numpy().T.copy()
        weights[f'b{i}'] = layer.bias.detach().numpy().copy()
    path = args.output/'tiny-spatial-v1.npz'
    np.savez(path, **weights)
    card = {'id': 'tiny-spatial-v1', 'schema': 'adeps-test-independent-mlp/1',
            'official_model': False, 'paper_performance_reproduced': False,
            'architecture': 'per-time-frequency-bin EDM MLP, 72 real/imag coordinates + 8 log-sigma features, two SiLU hidden layers; no temporal or frequency context',
            'hidden_channels': args.hidden, 'parameter_count': sum(p.numel() for p in net.parameters()),
            'prior_order': 5, 'sh_ordering': 'real ACN', 'sh_normalization': 'N3D',
            'alpha': .67, 'beta': 3, 'sigma_data': sd,
            'weights_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'training': {'seed': args.seed, 'steps': args.steps, 'batch_size': 512,
                         'samples': len(clean), 'validation_samples': len(validation),
                         'data': data_description, 'source_sha256': source_hash,
                         'optimizer': 'AdamW lr=.001 weight_decay=.0001',
                         'objective': 'EDM preconditioned weighted squared denoising error',
                         'noise_distribution': 'log-uniform sigma .002 to 80 (independent choice)',
                         'log': log, 'validation_before': initial, 'validation_after': final,
                         'runtime': f'PyTorch {torch.__version__}, CPU, 3 threads'},
            'limits': ['Not the paper NCSN++M (30.8M parameters).',
                       'Synthetic-vector validation is not speech, room, or field performance evidence.',
                       'No assurance of improvement on recordings; compare the unchanged linear baseline.',
                       'This file format does not promise compatibility with future author checkpoints.'],
            'sources': ['https://arxiv.org/abs/2608.24558v2', 'https://arxiv.org/abs/2206.00364']}
    (args.output/'tiny-spatial-v1.json').write_text(json.dumps(card, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'checkpoint': str(path), 'sha256': card['weights_sha256'], 'validation': final}), flush=True)


if __name__ == '__main__':
    main()
