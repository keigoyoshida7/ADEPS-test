"""Native full-size prior inference on a prepared synchronous array STFT NPZ.

NPZ fields: p_real,p_imag [F,Q,T], V_real,V_imag [F,Q,36], frequencies_hz,
sample_rate_hz,n_fft,hop,sh_ordering='ACN',sh_normalization='N3D'. Metadata is
mandatory: arbitrary log-frequency synthetic bins are not valid speech input.
Output contains full N5 estimates, the same-input Linear baseline and trace.
"""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def load_input(path):
    """Validate and fingerprint the actual NPZ arrays before loading a model."""
    payload = Path(path).read_bytes()
    with np.load(io.BytesIO(payload), allow_pickle=False) as data:
        def text(key):
            value = np.asarray(data[key])
            if value.shape != () or not isinstance(value.item(), str):
                raise ValueError(f'{key} must be a scalar string')
            return value.item()

        def integer(key):
            value = np.asarray(data[key])
            if value.shape != () or type(value.item()) is not int or value.item() <= 0:
                raise ValueError(f'{key} must be a positive scalar integer')
            return value.item()

        def real_array(key):
            value = np.asarray(data[key])
            if value.dtype.kind not in 'fiu' or not np.all(np.isfinite(value)):
                raise ValueError(f'{key} must contain finite real numbers')
            return value.astype(np.float64)

        if text('sh_ordering') != 'ACN' or text('sh_normalization') != 'N3D':
            raise ValueError('Input requires explicit real ACN/N3D conventions')
        rate, fft, hop = (integer(key) for key in ('sample_rate_hz', 'n_fft', 'hop'))
        if fft % 2 or fft > 65536 or hop > fft:
            raise ValueError('Require an even n_fft <= 65536 and hop <= n_fft')
        frequencies = real_array('frequencies_hz')
        expected = np.fft.rfftfreq(fft, 1/rate)
        if frequencies.shape != expected.shape or not np.allclose(frequencies, expected, rtol=0, atol=1e-6):
            raise ValueError('Expected the complete uniform one-sided STFT frequency grid')
        pr, pi, vr, vi = (real_array(key) for key in ('p_real', 'p_imag', 'V_real', 'V_imag'))
        if (pr.ndim != 3 or pr.shape != pi.shape or vr.shape != vi.shape
                or vr.shape != (len(frequencies), pr.shape[1], 36)
                or pr.shape[0] != len(frequencies)
                or not 4 <= pr.shape[1] <= 64 or not 1 <= pr.shape[2] <= 256):
            raise ValueError('Expected matching real/imaginary p=[F,4..64,1..256], V=[F,Q,36]')
        digest = hashlib.sha256()
        # Exactly the paper_studio convention: shapes, then little-endian f8.
        for array in (frequencies, vr, vi, pr, pi):
            digest.update(json.dumps(list(array.shape)).encode())
            digest.update(np.ascontiguousarray(array, dtype='<f8').tobytes())
        observation_sha256 = digest.hexdigest()
        if 'observation_sha256' in data and text('observation_sha256') != observation_sha256:
            raise ValueError('Declared observation_sha256 does not match the actual NPZ arrays')
        provenance = {key.removesuffix('_json'): json.loads(text(key))
                      for key in ('attribution_json', 'provenance_json', 'audio_json') if key in data}
        provenance['observation_sha256'] = observation_sha256
    return {'p': pr + 1j*pi, 'V': vr + 1j*vi, 'frequencies': frequencies,
            'sample_rate_hz': rate, 'n_fft': fft, 'hop': hop,
            'observation_sha256': observation_sha256, 'provenance': provenance,
            'input_file_sha256': hashlib.sha256(payload).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True, help='Directory containing report.json and paper-prior-v1.pt')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--steps', type=int, default=150)
    parser.add_argument('--guidance', type=float, default=50.)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--device', default='auto', choices=['auto', 'mps', 'cuda', 'cpu'])
    args = parser.parse_args()
    data = load_input(args.input)
    frequencies, rate, fft, hop = (data[key] for key in ('frequencies', 'sample_rate_hz', 'n_fft', 'hop'))
    provenance = data['provenance']
    from paper_inference import PaperPrior, reconstruct
    prior = PaperPrior(args.checkpoint, args.device)
    result = reconstruct(data['p'], data['V'], frequencies, prior, sample_rate=rate,
                         n_fft=fft, hop=hop, steps=args.steps,
                         eta_prime=args.guidance, seed=args.seed,
                         progress=lambda row: print(json.dumps(row), flush=True))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, linear_real=result['linear'].real, linear_imag=result['linear'].imag,
                        neural_real=result['neural'].real, neural_imag=result['neural'].imag,
                        frequencies_hz=frequencies,sample_rate_hz=rate,n_fft=fft,hop=hop,
                        sh_ordering='ACN',sh_normalization='N3D',
                        observation_sha256=data['observation_sha256'],
                        input_provenance_json=json.dumps(provenance,ensure_ascii=False))
    metadata = {k: value.tolist() if isinstance(value, np.ndarray) else value for k, value in result.items() if k not in ('linear', 'neural')}
    metadata.update(steps=args.steps, guidance=args.guidance, seed=args.seed,
                    sample_rate_hz=rate,n_fft=fft,hop=hop,frequencies_hz=frequencies.tolist(),
                    sh_ordering='ACN',sh_normalization='N3D',prior_order=5,
                    input_file_sha256=data['input_file_sha256'],
                    observation_sha256=data['observation_sha256'],
                    input_provenance=provenance,
                    official_model=False, paper_performance_reproduced=False)
    path.with_suffix('.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
