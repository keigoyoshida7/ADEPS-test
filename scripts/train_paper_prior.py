"""Train a full-size, array-independent HOA speech prior locally.

Requires optional training dependencies. No microphone coordinates, transfer
matrices, mic noise, or Linear estimates enter this training data interface.
Run outputs contain no speech files. A configured scene pool is NOT a count
of scenes actually consumed: both counts are recorded separately.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temp.replace(path)


def prepare_target(stft, compressed_std=1.):
    """One common scalar preserves all relative HOA channel levels/phases.

    Training uses clean-example RMS; inference must use observation-only RMS.
    The scalar compressed_std is estimated on TRAINING examples only. These
    scaling choices are independent because the paper does not specify them.
    """
    z = np.asarray(stft)
    if z.ndim != 3 or z.shape[0] != 36 or not np.iscomplexobj(z):
        raise ValueError('Expected ideal complex ACN/N3D [36, F, T]')
    rms = float(np.sqrt(np.mean(np.abs(z) ** 2)))
    if not np.isfinite(rms) or rms < 1e-12:
        raise ValueError('Silent or nonfinite HOA training scene')
    z = z / rms
    z = 3. * np.maximum(np.abs(z), 1e-8) ** (-.33) * z
    packed = np.concatenate([z.real, z.imag], axis=0).astype(np.float32)
    return packed / compressed_std


def rho_sample(generator, count, sigma_min=.002, sigma_max=80., rho=10.):
    # Continuous uniform u on the Eq.11 rho-spaced curve. Paper does not
    # specify the training discretization M or a probability mass per step.
    u = torch.rand(count, generator=generator)
    return (sigma_max ** (1/rho) + u * (sigma_min ** (1/rho) - sigma_max ** (1/rho))) ** rho


def nmse_db(error, energy):
    return float(10 * np.log10(max(error / max(energy, 1e-30), 1e-30)))


def evaluate(model, examples, device, seed=91873, sigmas=(.002, .01, .03, .1, .3, 1., 3., 10., 20., 80.)):
    """Same held-out examples/noise for identity, Gaussian and trained priors."""
    model.eval()
    generator = torch.Generator().manual_seed(seed)
    rows = []
    with torch.no_grad():
        for sigma in sigmas:
            errors = np.zeros(3, dtype=np.float64)
            energy = 0.
            for example in examples:
                clean = torch.from_numpy(example[None])
                noise = torch.randn(clean.shape, generator=generator)
                noisy = clean + sigma * noise
                predicted = model(noisy.to(device), torch.tensor([sigma], device=device)).cpu()
                if not torch.isfinite(predicted).all():
                    raise RuntimeError('Nonfinite held-out prediction')
                # sigma_data=1, zero-mean isotropic Gaussian reference prior.
                gaussian = noisy / (1 + sigma * sigma)
                for i, estimate in enumerate((noisy, gaussian, predicted)):
                    errors[i] += float(torch.sum((estimate.double() - clean.double()) ** 2))
                energy += float(torch.sum(clean.double() ** 2))
            values = [nmse_db(error, energy) for error in errors]
            rows.append({'sigma': sigma, 'noisy_nmse_db': values[0], 'gaussian_nmse_db': values[1],
                         'trained_nmse_db': values[2], 'improvement_over_noisy_db': values[0] - values[2],
                         'improvement_over_gaussian_db': values[1] - values[2]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', default=str(ROOT / 'work/paper-prior-v1'))
    parser.add_argument('--steps', type=int, default=2000, help='Total optimizer steps, including any resumed steps')
    parser.add_argument('--frames', type=int, default=32)
    parser.add_argument('--accumulate', type=int, default=1)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--seed', type=int, default=260824558)
    parser.add_argument('--device', choices=['auto', 'mps', 'cuda', 'cpu'], default='auto')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--evaluate-only', action='store_true')
    parser.add_argument('--eval-scenes', type=int, default=16)
    parser.add_argument('--save-every', type=int, default=100)
    parser.add_argument('--max-image-order', type=int, default=None)
    args = parser.parse_args()
    if args.steps < 1 or args.accumulate < 1 or args.eval_scenes < 1:
        parser.error('steps, accumulate and eval-scenes must be positive')
    from paper_data import SceneDataset
    from paper_prior import PaperDenoiser
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    device = args.device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    generator = torch.Generator().manual_seed(args.seed + 1)
    rng = np.random.default_rng(args.seed + 2)
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text())
    immutable = {key: getattr(args, key) for key in ('frames', 'accumulate', 'learning_rate', 'seed', 'max_image_order')}
    immutable['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in
                                 [Path(__file__), ROOT/'backend/paper_prior.py', ROOT/'scripts/paper_data.py']}
    dataset_args = dict(sample_rate=16000, n_fft=512, hop=128, frames=args.frames)
    if args.max_image_order is not None:
        dataset_args['max_image_order'] = args.max_image_order
    datasets = {split: SceneDataset(manifest_path, split=split, **dataset_args)
                for split in ('train', 'validation', 'test')}
    train = datasets['train']
    model = PaperDenoiser(sigma_data=1.).to(device)
    # Checkpointing recomputes activations, leaving model width/depth unchanged.
    if hasattr(model, 'gradient_checkpointing'):
        model.gradient_checkpointing = True
    parameters = sum(p.numel() for p in model.parameters())
    if parameters < 25_000_000:
        raise RuntimeError('This run requires the full-size architecture, not a small substitute')
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.)
    history, seen, step, elapsed_previous = [], set(), 0, 0.
    compressed_std = None
    checkpoint_path = output / 'training-state.pt'
    if args.resume or args.evaluate_only:
        state = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
        if state['manifest_sha256'] != digest(manifest_path) or state['frames'] != args.frames:
            raise ValueError('Resume data manifest/frame configuration mismatch')
        if state['immutable'] != immutable:
            raise ValueError('Resume requires identical data generation, accumulation, optimizer, seed and source hashes')
        model.load_state_dict(state['model'])
        optimizer.load_state_dict(state['optimizer'])
        step, seen, history = state['step'], set(state['seen']), state['history']
        compressed_std = state['compressed_std']
        generator.set_state(state['generator_state'])
        rng.bit_generator.state = json.loads(state['numpy_rng_json'])
        elapsed_previous = state['elapsed_seconds']
        del state
    if compressed_std is None:
        moments = [float(np.mean(prepare_target(train[i]['clean_stft']) ** 2)) for i in range(min(16, len(train)))]
        compressed_std = float(np.sqrt(np.mean(moments)))
    print(json.dumps({'stage': 'ready', 'parameters': parameters, 'device': device,
                      'compressed_std': compressed_std, 'scene_pool': len(train), 'step': step}), flush=True)
    validation = [prepare_target(datasets['validation'][i]['clean_stft'], compressed_std)
                  for i in range(min(4, len(datasets['validation'])))]
    started = time.perf_counter()
    audio_manifest = json.loads((manifest_path.parent / manifest['audio_manifest_path']).read_text())
    manifest_summary = {f'{split}_speakers': audio_manifest['speaker_splits'][split]
                        for split in ('train', 'validation', 'test')}
    manifest_summary.update(downloaded_utterances=len(audio_manifest['files']),
                            downloaded_audio_bytes=sum(row['size_bytes'] for row in audio_manifest['files']),
                            downloaded_audio_seconds=sum(row['duration_seconds'] for row in audio_manifest['files']),
                            audio_manifest_sha256=manifest['audio_manifest_sha256'],
                            harp_commit=audio_manifest['harp_upstream']['commit'],
                            scene_split_policy=manifest['split_policy'])
    model_config = model.config_dict()
    if hasattr(model_config, '__dict__'):
        model_config = vars(model_config)
    report = {
        'schema': 'adeps-test-paper-prior-training/1', 'status': 'training',
        'model': {'id': 'paper-prior-v1', 'name': 'N5 HOA speech EDM prior', 'parameters': parameters,
                  'prior_order': 5, 'complex_channels': 36,
                  'architecture': 'Independent NCSN++M-derived time-frequency U-Net with adaptive layer normalization and EDM preconditioning',
                  'config': model_config, 'weights_sha256': None},
        'training': {'optimizer_steps': step, 'examples_seen': step * args.accumulate,
                     'unique_scenes_seen': len(seen), 'elapsed_seconds': elapsed_previous,
                     'device': device, 'optimizer': 'AdamW', 'learning_rate': args.learning_rate,
                     'batch_size': 1, 'gradient_accumulation': args.accumulate, 'seed': args.seed,
                     'weight_decay': 0., 'gradient_clip_l2': 1., 'ema': False,
                     'environment': {'python': platform.python_version(), 'torch': torch.__version__,
                                     'numpy': np.__version__, 'platform': platform.platform()}},
        'data': {'generator': 'HARP-adapted ideal HOA image-source responses', 'corpus': 'VCTK 0.92 subset',
                 'train_speakers': [], 'validation_speakers': [], 'test_speakers': [],
                 'downloaded_utterances': 0, 'train_scene_pool': len(train),
                 'validation_scenes': len(datasets['validation']), 'test_scenes': len(datasets['test']),
                 'manifest_sha256': digest(manifest_path), 'array_conditioning': False,
                 'sources': [{'title': 'VCTK 0.92 — Yamagishi, Veaux, MacDonald', 'url': 'https://doi.org/10.7488/ds/2645', 'license': 'CC BY 4.0'},
                             {'title': 'HARP', 'url': 'https://github.com/whojavumusic/HARP', 'license': 'No repository license found; upstream code is not redistributed'}],
                 **manifest_summary},
        'configuration': {'sample_rate_hz': 16000, 'n_fft': 512, 'hop': 128, 'frames': args.frames,
                          'normalization': 'One HOA complex RMS per example, H(z)=3|z|^0.67 exp(i phase), then one fixed training-derived compressed standard deviation. Inference uses observation-only RMS.',
                          'compressed_std': compressed_std, 'sigma_data': 1.,
                          'sigma_min': .002, 'sigma_max': 80., 'rho': 10.,
                          'sigma_sampling': 'Continuous uniform interpolation parameter on the Eq.11 rho curve; the paper does not disclose training M.',
                          'max_image_order_override': args.max_image_order},
        'history': history, 'evaluation': None,
        'paper': {'source': 'https://arxiv.org/html/2608.24558v3',
                  'matched': ['Ideal order-5, 36 complex Ambisonics channels as the training target',
                              'No acquisition-array geometry, aliasing or microphone noise in training',
                              'Reverberant speech targets from VCTK and HARP-derived ideal HOA room simulation',
                              'EDM preconditioning, weighted denoising loss, sigma range 0.002–80 and rho=10',
                              'Time-frequency convolutional denoiser with noise-conditioned adaptive layer normalization'],
                  'differences': ['Independent network implementation; official ADEPS weights and full training code were not available at verification.',
                                  'Exact topology, optimizer, STFT and signal normalization are independently specified because they are not fully disclosed.',
                                  'VCTK subset and limited actual optimizer steps; a 20,000-scene pool is not 20,000 completed training examples.',
                                  'Held-out VCTK speakers replace licensed WSJ0 evaluation; this is not the paper benchmark.',
                                  'No claim of paper-level quality, convergence, room calibration or measured real-array generalization.']},
        'artifacts': {'command': '.venv-paper/bin/python scripts/train_paper_prior.py --manifest work/paper-data/scene-manifest.json --output work/paper-prior-v1 --resume --steps 20000',
                      'report_url': 'models/paper-prior-training.json'},
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }

    def save(current_step, final=False):
        elapsed = elapsed_previous + time.perf_counter() - started
        report['training'].update(optimizer_steps=current_step, examples_seen=current_step * args.accumulate,
                                  unique_scenes_seen=len(seen), elapsed_seconds=elapsed)
        report['updated_at'] = datetime.now(timezone.utc).isoformat()
        state = {'schema': 'adeps-test-paper-prior-state/1',
                 'model': {k: v.detach().cpu() for k, v in model.state_dict().items()},
                 'optimizer': optimizer.state_dict(), 'step': current_step, 'seen': sorted(seen),
                 'history': history, 'compressed_std': compressed_std,
                 'manifest_sha256': digest(manifest_path), 'frames': args.frames,
                 'generator_state': generator.get_state(), 'numpy_rng_json': json.dumps(rng.bit_generator.state),
                 'elapsed_seconds': elapsed, 'model_config': model_config}
        state['immutable'] = immutable
        temp = checkpoint_path.with_suffix('.tmp')
        torch.save(state, temp)
        temp.replace(checkpoint_path)
        del state
        if final:
            weights = output / 'paper-prior-v1.pt'
            temp = weights.with_suffix('.tmp')
            torch.save({'model': {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        'model_config': model_config, 'schema': 'adeps-test-paper-prior-weights/1'}, temp)
            temp.replace(weights)
            report['model']['weights_sha256'] = digest(weights)
            report['model']['weights_bytes'] = weights.stat().st_size
        write_json(output / 'report.json', report)

    while step < args.steps and not args.evaluate_only:
        model.train()
        optimizer.zero_grad(set_to_none=True)
        total_loss = 0.
        for _ in range(args.accumulate):
            index = int(rng.integers(len(train)))
            item = train[index]
            clean = torch.from_numpy(prepare_target(item['clean_stft'], compressed_std)[None]).to(device)
            sigma = rho_sample(generator, 1).to(device)
            noise = torch.randn(clean.shape, generator=generator).to(device)
            predicted = model(clean + sigma[:, None, None, None] * noise, sigma)
            weight = (sigma * sigma + 1) / (sigma * sigma)
            loss = ((predicted - clean).square().mean(dim=(1, 2, 3)) * weight).mean()
            if not torch.isfinite(loss):
                raise RuntimeError(f'Nonfinite training loss at step {step + 1}')
            (loss / args.accumulate).backward()
            total_loss += float(loss.detach().cpu()) / args.accumulate
            seen.add(index)
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
        optimizer.step()
        step += 1
        row = {'step': step, 'loss': total_loss, 'elapsed_seconds': elapsed_previous + time.perf_counter() - started}
        history.append(row)
        if step <= 3 or step % 10 == 0:
            print(json.dumps({'stage': 'training', **row, 'gradient_norm': float(norm.detach().cpu()),
                              'unique_scenes': len(seen)}), flush=True)
        if step % args.save_every == 0:
            val = evaluate(model, validation, device, sigmas=(.1, 1., 10.))
            row['validation_loss'] = float(np.mean([r['trained_nmse_db'] for r in val]))
            save(step)
            print(json.dumps({'stage': 'checkpoint', 'step': step, 'validation_nmse_db_mean_3sigmas': row['validation_loss']}), flush=True)
    if args.evaluate_only:
        report = json.loads((output / 'report.json').read_text())
        if report['training']['optimizer_steps'] != step:
            raise ValueError('Report and training-state step mismatch')
    else:
        save(step, final=True)
    # Test set is read only after training, never used for early selection.
    test_count = min(args.eval_scenes, len(datasets['test']))
    test = [prepare_target(datasets['test'][i]['clean_stft'], compressed_std) for i in range(test_count)]
    rows = evaluate(model, test, device)
    report['evaluation'] = {'split': 'speaker- and scene-disjoint VCTK test subset', 'scenes': test_count,
                            'speaker_ids': report['data'].get('test_speakers', []), 'rows': rows,
                            'metric': '10 log10 pooled squared error / pooled clean energy, in compressed 72-real-channel STFT coordinates, before inverse encoding.',
                            'noise_seed': 91873,
                            'summary': f"Trained beats noisy identity at {sum(r['improvement_over_noisy_db'] > 0 for r in rows)}/{len(rows)} noise levels; beats the isotropic Gaussian prior at {sum(r['improvement_over_gaussian_db'] > 0 for r in rows)}/{len(rows)}. This is denoising, not the paper's Linear-versus-ADEPS encoding benchmark."}
    report['status'] = 'evaluated'
    report['source_sha256'] = {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), ROOT/'backend/paper_prior.py', ROOT/'scripts/paper_data.py']}
    report['updated_at'] = datetime.now(timezone.utc).isoformat()
    write_json(output / 'report.json', report)
    print(json.dumps({'stage': 'evaluated', 'step': step, 'report': str(output / 'report.json'),
                      'summary': report['evaluation']['summary']}), flush=True)


if __name__ == '__main__':
    main()
