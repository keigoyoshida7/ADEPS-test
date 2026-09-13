"""Evaluate frozen denoiser weights on new procedural coefficients; never train.

The procedural generator function is loaded directly from the training source,
without importing the training runtime or executing any training code. Evaluation
uses only NumPy/SciPy and the exported NumPy denoiser.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from neural import TinyDenoiser, compress
from capture import real_n3d

SIGMAS = (.002, .01, .03, .1, .3, 1., 3., 10., 20., 80.)
GENERATOR_SEED = 17319
NOISE_SEED = 17320
DB_FLOOR = -300.


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _seed(value, name):
    if type(value) is not int or not 0 <= value < 2**32:
        raise ValueError(f'{name} must be an unsigned 32-bit integer')
    return value


def _matrix(value, name):
    data = np.asarray(value, dtype=np.complex128)
    if data.ndim != 2 or data.shape[1] != 36 or len(data) == 0 or not np.all(np.isfinite(data)):
        raise ValueError(f'{name} must be finite, nonempty complex [vectors,36] coefficients')
    return data


def scores(estimate, clean):
    """Aggregate complex NRMSE and MSE over the 72 real coordinates per vector."""
    target, actual = _matrix(clean, 'clean'), _matrix(estimate, 'estimate')
    if actual.shape != target.shape:
        raise ValueError('Estimate and clean coefficient shapes must match')
    error_energy = float(np.sum(np.abs(actual-target)**2))
    reference_energy = float(np.sum(np.abs(target)**2))
    return {
        'nrmse_db': float(max(DB_FLOOR, 10*np.log10(max(error_energy/reference_energy, 1e-30)))) if reference_energy > 0 else None,
        'real_coordinate_mse': error_energy / (2*target.size),
    }


def evaluate_coefficients(clean, epsilon, sigmas, denoiser):
    """Score predictions; the denoiser receives only noisy coefficients and sigma.

    clean is H(a), already magnitude-compressed. epsilon is fixed across sigma,
    with independent standard-normal real/imaginary coordinates in the protocol.
    The shrink baseline uses only sigma_data saved with the trained model.
    """
    target, noise = _matrix(clean, 'clean'), _matrix(epsilon, 'epsilon')
    if noise.shape != target.shape:
        raise ValueError('Noise and clean coefficient shapes must match')
    sigma_values = np.asarray(sigmas, dtype=float)
    if sigma_values.ndim != 1 or not len(sigma_values) or not np.all(np.isfinite(sigma_values)) or np.any(sigma_values <= 0) or np.any(np.diff(sigma_values) <= 0):
        raise ValueError('Sigma values must be finite, positive and strictly increasing')
    sd = float(denoiser.sigma_data)
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError('Denoiser sigma_data must be positive and finite')
    rows = []
    for sigma in sigma_values:
        noisy = target + float(sigma)*noise
        coefficient = sd**2/(sd**2+float(sigma)**2)
        shrink = coefficient*noisy
        # No clean reference, target variance, V, or array geometry is provided.
        prediction, _unused_vjp = denoiser.predict(noisy[:, :, None].copy(), float(sigma))
        prediction = np.asarray(prediction)
        if prediction.shape != (len(target), 36, 1):
            raise ValueError('Denoiser prediction must have shape [vectors,36,1]')
        learned = _matrix(prediction[:, :, 0], 'prediction')
        metrics = {name: scores(value, target) for name, value in
                   (('noisy', noisy), ('shrink', shrink), ('learned', learned))}
        errors_learned = np.sum(np.abs(learned-target)**2, axis=1)
        errors_shrink = np.sum(np.abs(shrink-target)**2, axis=1)
        wins = int(np.sum(errors_learned < errors_shrink))
        ties = int(np.sum(errors_learned == errors_shrink))
        def improvement(baseline):
            a, b = metrics[baseline]['nrmse_db'], metrics['learned']['nrmse_db']
            return a-b if a is not None and b is not None else None
        rows.append({
            'sigma': float(sigma), 'within_inference_range': bool(.002 <= sigma <= 20.),
            'shrink_coefficient': coefficient, **metrics,
            'learned_improvement_over_noisy_db': improvement('noisy'),
            'learned_improvement_over_shrink_db': improvement('shrink'),
            'learned_win_fraction_vs_shrink': wins/len(target),
            'learned_wins_vs_shrink': wins, 'learned_ties_vs_shrink': ties,
            'learned_losses_vs_shrink': len(target)-wins-ties,
        })
    return rows


def make_data(count, generator_seed, noise_seed):
    if type(count) is not int or not 1 <= count <= 8192:
        raise ValueError('Vector count must be an integer between 1 and 8192')
    _seed(generator_seed, 'generator_seed'); _seed(noise_seed, 'noise_seed')
    source = ROOT/'scripts/train_tiny_prior.py'
    # Keep the actual training generator as the single source of truth without
    # importing torch, constructing a Network, or executing the training script.
    tree = ast.parse(source.read_text(), filename=str(source))
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'vectors']
    if len(matches) != 1 or matches[0].decorator_list:
        raise ValueError('Expected one undecorated vectors function in the training source')
    namespace = {'np': np, 'real_n3d': real_n3d}
    exec(compile(ast.Module(body=matches, type_ignores=[]), str(source), 'exec'), namespace)
    clean = compress(namespace['vectors'](count, generator_seed))
    rng = np.random.default_rng(noise_seed)
    epsilon = rng.normal(size=clean.shape) + 1j*rng.normal(size=clean.shape)
    return clean, epsilon


def generate_report(count=2048, generator_seed=GENERATOR_SEED, noise_seed=NOISE_SEED, model_directory=None):
    started = time.perf_counter()
    denoiser = TinyDenoiser(model_directory)
    card = denoiser.card
    training_seed = int(card['training']['seed'])
    if card['training'].get('source_sha256') is not None:
        raise ValueError('This protocol describes the procedural checkpoint, not a custom HOA-trained model')
    reserved_seeds = {training_seed, training_seed+1, training_seed+2}
    if generator_seed in reserved_seeds or noise_seed in reserved_seeds or generator_seed == noise_seed:
        raise ValueError('Evaluation generator/noise seeds must be distinct and unused in training/validation')
    clean, epsilon = make_data(count, generator_seed, noise_seed)
    rows = evaluate_coefficients(clean, epsilon, SIGMAS, denoiser)
    inference = ROOT/'backend/neural.py'
    generator = ROOT/'scripts/train_tiny_prior.py'
    return {
        'schema': 'adeps-test-tiny-denoiser-evaluation/1',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'evaluation_kind': 'Frozen-model denoising of held-out procedural coefficients; not array reconstruction or real audio',
        'model': {'id': card['id'], 'parameter_count': card['parameter_count'],
                  'weights_sha256': card['weights_sha256'], 'weights_checksum_verified': True,
                  'sigma_data': denoiser.sigma_data, 'training_seed': training_seed,
                  'training_steps': card['training']['steps'], 'official_model': False},
        'dataset': {
            'vectors': count, 'complex_channels': 36, 'real_coordinates_per_vector': 72,
            'generator_seed': generator_seed, 'noise_seed': noise_seed,
            'training_seed': training_seed, 'validation_seed': training_seed+1,
            'training_validation_noise_seed': training_seed+2,
            'same_noise_across_sigma': True,
            'generation_family': 'Same procedural family as tiny-prior training: 1–2 plane waves plus 3 weak rays; random directions, complex phases and gains. New independent seed; not held-out recording environments.',
            'normalization': 'clean = H(a), H uses alpha=.67 and beta=3. Real ACN/N3D, order5, 36 complex coefficients. No per-vector RMS fitting, no target-derived normalization at evaluation.',
            'noise_definition': 'One frozen epsilon with independent N(0,1) real and imaginary coordinates. Input=clean+sigma*epsilon. Sigma is in compressed coefficient units; it is not microphone SNR, acoustic noise level or SPL.',
            'epsilon_real_coordinate_mse': float(np.mean(np.abs(epsilon)**2)/2),
            'clean_real_coordinate_mean_square': float(np.mean(np.abs(clean)**2)/2),
            'clean_sha256': hashlib.sha256(np.ascontiguousarray(clean, dtype='<c16').tobytes()).hexdigest(),
            'epsilon_sha256': hashlib.sha256(np.ascontiguousarray(epsilon, dtype='<c16').tobytes()).hexdigest(),
        },
        'protocol': {
            'sigma_values': list(SIGMAS), 'inference_sigma_range': [.002, 20.],
            'training_sigma_range': [.002, 80.], 'db_floor': DB_FLOOR,
            'shrink_definition': 'c_skip*x, c_skip=sigma_data^2/(sigma^2+sigma_data^2); sigma_data comes only from the training model card. This is the isotropic zero-mean Gaussian-prior baseline, with no fitted test-data statistics.',
            'metric_definitions': {
                'nrmse_db': '20 log10(||estimate-clean||_2/||clean||_2), aggregated over all 36 complex channels and all vectors. Exact zero error displays at -300 dB; zero-energy references yield null.',
                'real_coordinate_mse': 'sum(real(error)^2+imag(error)^2)/(2*vectors*36). No averaging in decibels.',
                'learned_improvement_db': 'Baseline aggregate NRMSE minus learned aggregate NRMSE; positive means learned has lower error.',
                'learned_win_fraction_vs_shrink': 'Fraction of vectors whose summed squared complex error is strictly below shrink error. Ties use exact floating-point equality. This is not a general accuracy percentage.',
            },
        },
        'cases': rows,
        'summary': {
            'sigma_count': len(rows),
            'learned_better_than_noisy_sigma_count': sum(row['learned_improvement_over_noisy_db'] > 0 for row in rows),
            'learned_better_than_shrink_sigma_count': sum(row['learned_improvement_over_shrink_db'] > 0 for row in rows),
            'inference_sigma_count': sum(row['within_inference_range'] for row in rows),
            'elapsed_seconds': time.perf_counter()-started,
        },
        'provenance': {
            'evaluation_script': 'scripts/evaluate_tiny_denoiser.py', 'evaluation_script_sha256': _sha(__file__),
            'generator_training_script': 'scripts/train_tiny_prior.py', 'generator_training_script_sha256': _sha(generator),
            'generator_loading': 'AST extraction of the vectors function from the hashed training source; NumPy/SciPy only; no training-script top-level code executes.',
            'inference_source': 'backend/neural.py', 'inference_source_sha256': _sha(inference),
            'sh_source': 'backend/capture.py', 'sh_source_sha256': _sha(ROOT/'backend/capture.py'),
            'numpy_version': np.__version__,
        },
        'limits': [
            'The existing 24,072-parameter independently trained tiny model is evaluated without training or changing its weights.',
            'New procedural vectors from the same generator family; no real speech, room impulse responses, HARP, VCTK, microphone recording, array response V, or venue data.',
            'This tests the denoiser directly in compressed 36-channel coefficient space. It does not measure full ADEPS inverse-problem accuracy, FOA audio quality, physical soundfield recovery, or the paper checkpoint.',
            'Gaussian shrink is a simple calibrated baseline. Beating noisy input alone is weaker evidence than beating this baseline; failures are retained.',
            'The same epsilon and clean vectors are reused across sigma for paired comparisons. Sigma rows are correlated experiments, not independent trials.',
            'The denoiser receives only noisy coefficients and sigma; clean coefficients are used to form the corruption and calculate scores, never as an additional network input.',
            'No listening or temporal consistency evaluation: each vector is independent and represents one time-frequency coefficient set, not a recording.',
            'Inference elsewhere normalizes from the observed input. This standalone training-domain denoising benchmark does not establish matched distributions after that normalization.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vectors', type=int, default=2048)
    parser.add_argument('--generator-seed', type=int, default=GENERATOR_SEED)
    parser.add_argument('--noise-seed', type=int, default=NOISE_SEED)
    parser.add_argument('--output', type=Path, default=ROOT/'public/models/tiny-denoiser-evaluation.json')
    args = parser.parse_args()
    report = generate_report(args.vectors, args.generator_seed, args.noise_seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2)+'\n')
    print(json.dumps({'output': str(args.output), 'summary': report['summary'],
                      'weights_sha256': report['model']['weights_sha256']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
