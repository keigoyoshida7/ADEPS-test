"""Train an independent physics-conditioned spatial residual network.

Procedural plane waves and diffuse modal energy are not speech recordings,
VCTK, measured room responses, HARP, or the ADEPS training set. Seeds 10000+
are training scenes and 20000+ are validation scenes; 90000+ are reserved for
an external final test. Real data and reference files are never read.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from capture import encode, modal_matrix, real_n3d
from spatial_model import FEATURES, SpatialModel, features


class Network(nn.Module):
    def __init__(self, hidden=512):
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(a, b) for a, b in
                                    zip([FEATURES, hidden, hidden, hidden, hidden],
                                        [hidden, hidden, hidden, hidden, 72])])
        nn.init.zeros_(self.layers[-1].weight)
        nn.init.zeros_(self.layers[-1].bias)

    def forward(self, x):
        h = x
        for layer in self.layers[:-1]:
            h = torch.nn.functional.silu(layer(h))
        return x[:, :72] + self.layers[-1](h)


def scene(seed, frequencies=64, frames=8):
    rng = np.random.default_rng(seed)
    q = int(rng.choice([4, 5, 6, 8, 12]))
    radius = rng.uniform(.04, .1)
    phi = np.arange(q) * np.pi * (3 - np.sqrt(5))
    z = 1 - 2 * (np.arange(q) + .5) / q
    xyz = np.c_[np.sqrt(1-z*z)*np.cos(phi), np.sqrt(1-z*z)*np.sin(phi), z]
    # SO(3) rotation; array orientations are split along with scene seeds.
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    rotation[:, 0] *= np.linalg.det(rotation)
    xyz = xyz @ rotation * radius
    if rng.random() < .35:
        xyz += rng.normal(size=xyz.shape) * radius * .035
    # Same fixed full display band as the application; no claim that a physical
    # microphone or this finite simulated modal model is accurate over it all.
    frequency = np.geomspace(1, 20000, frequencies)
    count = int(rng.integers(1, 6))
    order = 15 if rng.random() < .3 else 5
    coefficients = (order + 1) ** 2
    harmonics = real_n3d(order, rng.normal(size=(count, 3)))
    sources = (rng.normal(size=(frequencies, count, frames)) +
               1j * rng.normal(size=(frequencies, count, frames))) / np.sqrt(2)
    for frame in range(1, frames):
        sources[:, :, frame] = .65 * sources[:, :, frame-1] + np.sqrt(1-.65**2)*sources[:, :, frame]
    levels = np.ones(count)
    # Deliberately broad independent synthetic spectra with optional smooth
    # spectral tilt and sparse spectral activity. These are not speech STFTs.
    levels[1:] = 10 ** rng.uniform(-1., -.1, max(0, count-1))
    tilt = (np.maximum(frequency, 80) / 1000) ** rng.uniform(-.5, .5)
    sources *= levels[None, :, None] * tilt[:, None, None]
    truth = np.einsum('sc,fst->fct', harmonics, sources)
    diffuse = (rng.normal(size=truth.shape) + 1j*rng.normal(size=truth.shape)) / np.sqrt(2)
    truth += diffuse * rng.uniform(0, .2) * tilt[:, None, None]
    v_true = modal_matrix(frequency, xyz, order)
    v = v_true[:, :, :36]
    p = v_true @ truth
    snr = rng.uniform(10, 50)
    sigma = np.sqrt(np.mean(np.abs(p)**2, axis=(1,2))) * 10 ** (-snr / 20)
    p += sigma[:, None, None] * (rng.normal(size=p.shape)+1j*rng.normal(size=p.shape))/np.sqrt(2)
    regularization = .001 if rng.random() < .7 else 10 ** rng.uniform(-4, -1.5)
    linear, encoder, _ = encode(v, p, regularization)
    x, scale = features(linear, encoder @ v, frequency)
    target = (truth[:, :36] / scale[:, None, None]).transpose(0, 2, 1).reshape(-1, 36)
    y = np.c_[target.real, target.imag].astype(np.float32)
    return x, y, {'seed': seed, 'microphones': q, 'radius_m': radius,
                  'snr_db': snr, 'sources': count, 'soundfield_order': order,
                  'regularization': regularization}


def make_dataset(start, count):
    xs, ys, specs = [], [], []
    for i in range(count):
        x, y, spec = scene(start + i)
        xs.append(x); ys.append(y); specs.append(spec)
    return np.concatenate(xs), np.concatenate(ys), specs


def augment_phase(x, y):
    phase = torch.rand(len(x), 1, device=x.device) * (2 * np.pi)
    c, s = torch.cos(phase), torch.sin(phase)
    result = x.clone()
    result[:, :36] = x[:, :36]*c - x[:, 36:72]*s
    result[:, 36:72] = x[:, :36]*s + x[:, 36:72]*c
    target = torch.cat((y[:, :36]*c-y[:, 36:]*s,
                        y[:, :36]*s+y[:, 36:]*c), dim=1)
    return result, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--steps', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=38741)
    parser.add_argument('--hidden', type=int, default=512)
    parser.add_argument('--train-scenes', type=int, default=3072)
    parser.add_argument('--chunk-scenes', type=int, default=512)
    parser.add_argument('--chunk-steps', type=int, default=2000)
    parser.add_argument('--previous-trial', type=Path, action='append', default=[])
    parser.add_argument('--validation-scenes', type=int, default=32)
    parser.add_argument('--batch-size', type=int, default=512)
    parser.add_argument('--device', choices=['mps', 'cpu'], default='mps' if torch.backends.mps.is_available() else 'cpu')
    parser.add_argument('--output', type=Path, default=ROOT/'public/models')
    args = parser.parse_args()
    if not 1 <= args.train_scenes < 10000 or not 1 <= args.validation_scenes < 5000:
        raise ValueError('Keep the declared scene seed ranges disjoint')
    if args.steps < 1 or args.batch_size < 1:
        raise ValueError('Training steps and batch size must be positive')
    torch.set_num_threads(3)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    started = time.perf_counter()
    print(json.dumps({'stage': 'generate', 'training_scenes': args.train_scenes,
                      'validation_scenes': args.validation_scenes}), flush=True)
    if args.chunk_scenes < 1 or args.chunk_steps < 1:
        raise ValueError('Chunk settings must be positive')
    chunk_count = (args.train_scenes + args.chunk_scenes - 1) // args.chunk_scenes
    train_x, train_y, train_specs = make_dataset(10000, min(args.chunk_scenes, args.train_scenes))
    all_train_specs = {row['seed']: row for row in train_specs}
    valid_x, valid_y, valid_specs = make_dataset(20000, args.validation_scenes)
    generation_seconds = time.perf_counter() - started
    device = torch.device(args.device)
    net = Network(args.hidden).to(device)
    optimizer = torch.optim.AdamW(net.parameters(), lr=.0008, weight_decay=.0001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.steps, eta_min=.00004)
    # Non-FOA outputs regularize the shared spatial representation but the first
    # four real and imaginary components determine model checkpoint selection.
    weights = torch.full((72,), .025, device=device)
    weights[:4] = 1.; weights[36:40] = 1.
    foa_indices = [0,1,2,3,36,37,38,39]

    def evaluate():
        prediction = []
        net.eval()
        with torch.no_grad():
            for offset in range(0, len(valid_x), 1024):
                tensor = torch.from_numpy(valid_x[offset:offset+1024]).to(device)
                prediction.append(net(tensor).cpu().numpy())
        pred = np.concatenate(prediction)
        baseline = valid_x[:, :72]
        y = valid_y
        def metrics(value):
            err = value-y
            f = foa_indices
            return {'normalized_foa_mse': float(np.mean(err[:, f]**2)),
                    'foa_nrmse_db': float(10*np.log10(np.sum(err[:, f]**2)/np.sum(y[:, f]**2))),
                    'all36_nrmse_db': float(10*np.log10(np.sum(err**2)/np.sum(y**2)))}
        net.train()
        return {'linear': metrics(baseline), 'learned': metrics(pred)}

    initial = evaluate()
    best_loss = float('inf'); best_step = 0; best_state = None; logs = []
    trained_started = time.perf_counter()
    active_chunk = 0
    for step in range(1, args.steps+1):
        chunk = ((step - 1) // args.chunk_steps) % chunk_count
        if chunk != active_chunk:
            del train_x, train_y
            gc.collect()
            chunk_start = chunk * args.chunk_scenes
            train_x, train_y, train_specs = make_dataset(10000+chunk_start, min(args.chunk_scenes, args.train_scenes-chunk_start))
            all_train_specs.update({row['seed']: row for row in train_specs})
            active_chunk = chunk
        indices = rng.integers(0, len(train_x), args.batch_size)
        x = torch.from_numpy(train_x[indices]).to(device)
        y = torch.from_numpy(train_y[indices]).to(device)
        x, y = augment_phase(x, y)
        error = net(x) - y
        loss = (error.square() * weights).sum(dim=1).mean() / weights.sum()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), 2.)
        optimizer.step(); scheduler.step()
        if step % 200 == 0 or step == args.steps:
            evaluation = evaluate()
            value = evaluation['learned']['normalized_foa_mse']
            if value < best_loss:
                best_loss = value; best_step = step
                best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
            row = {'step': step, 'training_loss': float(loss.detach().cpu()),
                   'seconds': round(time.perf_counter()-trained_started, 3), 'validation': evaluation}
            logs.append(row); print(json.dumps(row), flush=True)
    net.load_state_dict(best_state)
    final = evaluate()
    weights_numpy = {}
    for i, layer in enumerate(net.layers, start=1):
        weights_numpy[f'w{i}'] = layer.weight.detach().cpu().numpy().T.copy()
        weights_numpy[f'b{i}'] = layer.bias.detach().cpu().numpy().copy()
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / 'spatial-v1.npz'
    np.savez(path, **weights_numpy)
    card = {
        'id': 'spatial-v1', 'schema': 'adeps-test-physics-residual/1',
        'name': 'Physics-conditioned residual spatial estimator',
        'official_model': False, 'paper_performance_reproduced': False,
        'paper_superiority_demonstrated': False,
        'architecture': 'Four-hidden-layer SiLU MLP; complex identity residual; 465 input features: 72 observed real/imag coefficients, 288 real/imag entries in the first 4 rows of E@V, 36 real diagonal entries, 1 logarithmic frequency, 32 real/imag entries of first-4 temporal covariance, and 36 observed channel powers. One deterministic forward pass, no diffusion sampling.',
        'hidden_channels': args.hidden, 'hidden_layers': 4, 'input_features': FEATURES,
        'parameter_count': sum(p.numel() for p in net.parameters()),
        'input_channels': 36, 'output_channels': 36,
        'prior_order': 5, 'sh_ordering': 'real ACN', 'sh_normalization': 'N3D',
        'normalization': 'Per-frequency RMS of the first four LINEAR input coefficients over supplied time frames; floor 1e-12; target never used to normalize inputs.',
        'weights_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'training': {
            'seed': args.seed, 'steps': args.steps, 'selected_step': best_step,
            'batch_size': args.batch_size, 'samples': len(all_train_specs)*512,
            'chunk_scenes': args.chunk_scenes, 'chunk_steps': args.chunk_steps,
            'training_scene_seeds': [min(all_train_specs), max(all_train_specs)],
            'selected_checkpoint_scene_seeds': [10000, 10000+min(args.train_scenes, (((best_step-1)//args.chunk_steps)+1)*args.chunk_scenes)-1],
            'selected_checkpoint_unique_scenes': min(args.train_scenes, (((best_step-1)//args.chunk_steps)+1)*args.chunk_scenes),
            'validation_scene_seeds': [20000, 20000+args.validation_scenes-1],
            'reserved_final_test_seed_start': 90000,
            'validation_samples': len(valid_x),
            'data': 'Independent procedural 1--5 plane waves plus diffuse modal energy; real ACN/N3D; 64 geometric frequencies 1 Hz--20 kHz, 8 correlated complex frames. Ideal omnidirectional free-field arrays, random 3D rotation, 4/5/6/8/12 capsules, radii .04--.10 m, 10--50 dB SNR, order 5 or order 15 soundfield. Not audio speech STFTs, not VCTK, not HARP, and no field recordings.',
            'augmentation': 'Random common complex phase per training bin. Directions, array orientation/radius, source strengths, spectral tilt, diffuse energy, noise and regularization vary across synthetic scenes.',
            'optimizer': 'AdamW lr=.0008 weight_decay=.0001; cosine decay to .00004; gradient-norm cap 2.',
            'objective': 'Normalized complex squared residual error; first 4 coefficients weight 1, remaining 32 weight .025; select checkpoint by held-out-scene normalized FOA MSE.',
            'selection': 'Minimum validation FOA MSE at 200-step intervals; no final-test data consulted.',
            'generation_seconds': round(generation_seconds,3),
            'generation_seconds_note': 'Initial training chunk plus validation only; later chunk generation is included in training_seconds.',
            'selection_is_validation_not_final_test': True,
            'validation_foa_improvement_db': final['linear']['foa_nrmse_db']-final['learned']['foa_nrmse_db'],
            'training_seconds': round(time.perf_counter()-trained_started,3),
            'runtime': f'PyTorch {torch.__version__}, {args.device}, CPU threads 3',
            'validation_before': initial, 'validation_after': final, 'log': logs,
            'training_scenes_sha256': hashlib.sha256(json.dumps(sorted(all_train_specs.values(),key=lambda r:r['seed']),sort_keys=True).encode()).hexdigest(),
            'validation_scenes_sha256': hashlib.sha256(json.dumps(valid_specs,sort_keys=True).encode()).hexdigest(),
        },
        'limits': [
            'An independently trained proposal, not the paper 30.8M-parameter diffusion network and not an official checkpoint.',
            'Model size or synthetic validation cannot establish superiority to ADEPS, speech reconstruction quality, or venue performance.',
            'No explicit reverberant-room or microphone directivity response training; measured arrays and real speech are distribution shifts.',
            'Temporal covariance uses the entire supplied window (offline/noncausal); no learned long-range speech or adjacent-frequency structure.',
            'Underdetermined spatial modes cannot be uniquely recovered; learned outputs can hallucinate spatial structure.',
            '1 Hz--20 kHz is a simulated evaluation/display range, not a certified physical microphone bandwidth.',
            'Inference has no reference-driven selection. Physical projection and ON/OFF mixing, if used, belong to the calling application.'
        ],
        'sources': ['https://arxiv.org/abs/2608.24558'],
        'license': 'MIT (independently authored code and procedurally trained weights)',
        'inference_context': 'Covariance, power and RMS are computed from all frames of the supplied window. Offline/noncausal; no clean target and no external state.',
    }
    prior_trials = []
    for trial_path in args.previous_trial:
        trial = json.loads(trial_path.read_text())
        prior_trials.append({'weights_sha256': trial['weights_sha256'], 'parameter_count': trial['parameter_count'],
                             'features': trial['architecture'], 'training': trial['training'],
                             'outcome': 'Earlier held-out validation did not improve on the unchanged linear baseline; not used as evidence of improvement.'})
    card['development_trials'] = prior_trials
    card_path = args.output / 'spatial-v1.json'
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2)+'\n')
    # Validate the actual exported NumPy implementation against the trained
    # PyTorch graph. This uses held-out input features, never clean references.
    exported = SpatialModel(args.output)
    check_x = valid_x[:257]
    with torch.no_grad():
        expected = net(torch.from_numpy(check_x).to(device)).cpu().numpy()
    actual = exported.predict_features(check_x, batch_size=113)
    max_error = float(np.max(np.abs(expected-actual)))
    relative = float(np.linalg.norm(expected-actual)/max(np.linalg.norm(expected),1e-12))
    if not np.allclose(expected, actual, rtol=3e-4, atol=3e-5):
        raise RuntimeError(f'NumPy export differs from PyTorch: max={max_error}, relative={relative}')
    card['export_parity'] = {'checked_bins': len(check_x), 'max_abs_error': max_error,
                             'relative_l2_error': relative, 'rtol': 3e-4, 'atol': 3e-5, 'passed': True}
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'stage': 'complete', 'checkpoint': str(path),
                      'parameters': card['parameter_count'], 'selected_step': best_step,
                      'validation': final, 'export_parity': card['export_parity']}), flush=True)


if __name__ == '__main__':
    main()
