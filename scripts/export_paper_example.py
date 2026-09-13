"""Evaluate one declared held-out scene with Linear and the full-size DPS prior.

This is a saved demonstration, not a live browser computation or a paper test
set average. VCTK-derived previews are redistributed with CC BY 4.0 credit.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--checkpoint', default=str(ROOT/'work/paper-prior-v1'))
    parser.add_argument('--scene', type=int, default=0)
    parser.add_argument('--steps', type=int, default=150)
    parser.add_argument('--guidance', type=float, default=50.)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', default=str(ROOT/'work/paper-prior-v1/example'))
    args = parser.parse_args()
    from paper_studio import make_observation
    from diffusion_studio import run_studio
    from paper_inference import PaperPrior, sample
    from train_paper_prior import write_json
    prior = PaperPrior(args.checkpoint)
    observation = make_observation(prior, args.manifest, {'scene_index': args.scene, 'steps': args.steps,
                                                        'eta_prime': args.guidance, 'seed': args.seed})
    start = time.perf_counter()
    result, archive = run_studio({}, observation=observation, model=prior, sampler=sample,
                                 progress=lambda row: print(json.dumps(row), flush=True))
    p, v, frequencies = observation['p'], observation['V'], observation['frequencies']
    rate, fft, hop = (observation['audio'][key] for key in ('sample_rate_hz', 'n_fft', 'hop'))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output/'paper-prior-example.json', result)
    (output/'paper-prior-example.zip').write_bytes(archive)
    np.savez_compressed(output/'array-input.npz', p_real=p.real, p_imag=p.imag, V_real=v.real,
                        V_imag=v.imag, frequencies_hz=frequencies, sample_rate_hz=rate, n_fft=fft, hop=hop,
                        sh_ordering='ACN', sh_normalization='N3D',
                        observation_sha256=observation['input_sha256'],
                        attribution_json=json.dumps(observation['attribution'],ensure_ascii=False),
                        provenance_json=json.dumps(observation['example_provenance'],ensure_ascii=False),
                        audio_json=json.dumps(observation['audio'],ensure_ascii=False))
    print(json.dumps({'stage': 'saved', 'output': str(output), 'elapsed_seconds': time.perf_counter()-start,
                      'metrics': result['metrics']}), flush=True)


if __name__ == '__main__':
    main()
