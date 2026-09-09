"""Local offline entrypoint: same checkpoint, math and WAV export as the Web UI."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from neural_audio import run_audio

parser = argparse.ArgumentParser()
parser.add_argument('input_zip',type=Path)
parser.add_argument('output_zip',type=Path)
parser.add_argument('--start',type=float,default=0)
parser.add_argument('--duration',type=float,default=.4)
parser.add_argument('--steps',type=int,default=150)
parser.add_argument('--eta',type=float,default=50.)
parser.add_argument('--seed',type=int,default=42)
args = parser.parse_args()
if args.output_zip.exists():
    raise SystemExit('Choose a new output filename; existing results are preserved.')
def progress(row):
    if row['step']%10 == 0:
        print(f"{row['step']}/{row['total']}  residual={row['encoded_residual']:.5g}",flush=True)
result, archive = run_audio(args.input_zip.read_bytes(),
                           {'start_seconds':args.start,'duration_seconds':args.duration,
                            'steps':args.steps,'eta_prime':args.eta,'seed':args.seed},progress)
args.output_zip.write_bytes(archive)
print(f"Saved {args.output_zip}; {result['diagnostics']['elapsed_seconds']:.2f} s")
