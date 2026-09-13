"""Local-only full-size speech prior studio; synthetic observations, no devices."""
import hashlib
import json
import os
import sys
import threading
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from paper_data import SceneDataset, sha256 as digest
from capture import modal_matrix
from diffusion_studio import _integer, _number, run_studio
from paper_inference import PaperPrior, sample


def configuration(config):
    q = _integer(config, 'microphones', 6, 4, 16)
    if q not in (4, 6, 8, 12, 16):
        raise ValueError('microphones must be 4, 6, 8, 12, or 16')
    geometry = config.get('geometry', 'sphere')
    if geometry not in ('sphere', 'ring'):
        raise ValueError('geometry must be sphere or ring')
    return {'microphones': q, 'geometry': geometry,
            'radius_m': _number(config, 'radius_m', .06, .01, .25),
            'snr_db': _number(config, 'snr_db', 50., 0., 80.),
            'observation_seed': _integer(config, 'observation_seed', 173927, 0, 2**32-1),
            'seed': _integer(config, 'seed', 42, 0, 2**32-1),
            'eta_prime': _number(config, 'eta_prime', 50., 0., 100.),
            'steps': _integer(config, 'steps', 150, 8, 150),
            'scene_index': _integer(config, 'scene_index', 0, 0, 99)}


def make_observation(prior, manifest_path, config):
    options = configuration(config)
    scene_index = options['scene_index']
    cfg = prior.card['configuration']
    if digest(ROOT/'scripts/paper_data.py') != prior.card['source_sha256']['scripts/paper_data.py']:
        raise ValueError('The room-data generator differs from the checkpoint provenance')
    if digest(manifest_path) != prior.card['data']['manifest_sha256']:
        raise ValueError('Example manifest differs from the checkpoint provenance')
    dataset = SceneDataset(manifest_path, split='test', sample_rate=cfg['sample_rate_hz'],
                           n_fft=cfg['n_fft'], hop=cfg['hop'], frames=cfg['frames'],
                           max_image_order=cfg['max_image_order_override'])
    scene = dataset[scene_index]
    reference = scene['clean_stft'].transpose(1, 0, 2).astype(np.complex128)
    rate, fft, hop, frames = cfg['sample_rate_hz'], cfg['n_fft'], cfg['hop'], cfg['frames']
    frequencies = np.fft.rfftfreq(fft, 1/rate)
    q, radius = options['microphones'], options['radius_m']
    angles = 2*np.pi*np.arange(q)/q if options['geometry'] == 'ring' else np.arange(q)*np.pi*(3 - np.sqrt(5))
    z = np.zeros(q) if options['geometry'] == 'ring' else 1 - 2 * (np.arange(q) + .5) / q
    positions = radius * np.c_[np.sqrt(1-z*z)*np.cos(angles), np.sqrt(1-z*z)*np.sin(angles), z]
    v = modal_matrix(frequencies, positions, 5)
    v[[0, -1]] = v[[0, -1]].real
    reference[[0, -1]] = reference[[0, -1]].real
    p = v @ reference
    rng = np.random.default_rng(options['observation_seed'])
    noise = rng.normal(size=p.shape) + 1j * rng.normal(size=p.shape)
    noise[[0, -1]] = noise[[0, -1]].real
    p += noise * np.linalg.norm(p) / np.linalg.norm(noise) * 10 ** (-options['snr_db'] / 20)
    sources = []
    for i, source in enumerate(scene['metadata']['sources_m']):
        direction = np.asarray(source) - scene['metadata']['receiver_m']
        direction /= np.linalg.norm(direction)
        sources.append({'id': f'speech-{i}', 'label': f'Speech source {i+1}', 'direction': direction.tolist(),
                        'azimuth_deg': float(np.rad2deg(np.arctan2(direction[1], direction[0]))),
                        'elevation_deg': float(np.rad2deg(np.arcsin(direction[2])))})
    h = hashlib.sha256()
    for a in (frequencies, v.real, v.imag, p.real, p.imag):
        h.update(json.dumps(list(a.shape)).encode()); h.update(np.ascontiguousarray(a, dtype='<f8').tobytes())
    files = [dataset.audio['files'][i] for i in scene['metadata']['audio_indexes']]
    attribution = {'title': 'VCTK 0.92 — Junichi Yamagishi, Christophe Veaux, Kirsten MacDonald',
                   'corpus': 'VCTK 0.92', 'speakers': [f['speaker'] for f in files],
                   'files': [f['archive_member'] for f in files], 'license': 'CC BY 4.0',
                   'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                   'source_url': 'https://doi.org/10.7488/ds/2645',
                   'changes': 'Resampled to 16 kHz, convolved with synthetic ideal HOA room responses, cropped, encoded/reconstructed, shared attenuation and virtual-cardioid stereo rendering. The original speakers do not endorse this project.'}
    # Training crops have unpadded Hann windows. Symmetric iSTFT trimming avoids
    # the zero-window endpoints; metrics still use the original 32 STFT frames.
    samples = (frames - 1) * hop
    observation = {
        'configuration': {'microphones': q, 'geometry': options['geometry'], 'radius_m': radius,
                          'snr_db': options['snr_db'], 'observation_seed': options['observation_seed'], 'seed': options['seed'],
                          'eta_prime': options['eta_prime'], 'steps': options['steps'],
                          'sample_rate': rate, 'duration_seconds': samples/rate,
                          'n_fft': fft, 'regularization': .001},
        'V': v, 'p': p, 'reference': reference, 'frequencies': frequencies,
        'microphone_positions_m': positions, 'source_directions': sources,
        'input_sha256': h.hexdigest(),
        'audio': {'sample_rate_hz': rate, 'sample_rate': rate, 'samples': samples,
                  'duration_seconds': samples/rate, 'n_fft': fft, 'hop': hop,
                  'window': 'periodic Hann', 'stft_scaling': 'scipy spectrum',
                  'frequency_bin_spacing_hz': rate/fft, 'nyquist_hz': rate/2,
                  'preview_trim_each_end_samples': fft//2,
                  'preview_trim_reason': 'Trim the unpadded training crop Hann endpoints symmetrically for every method; spectra are evaluated before this trim.'},
        'implementation': 'Independent full-size 30.78M NCSN++M-derived HARP/VCTK speech prior with actual trained weights and ADEPS-equation DPS; held-out speech scene.',
        'metric_scope': f"One speaker/scene-held-out VCTK example with a HARP-adapted ideal room, matched order 5 and {q} ideal omnidirectional virtual microphones, {options['snr_db']} dB synthetic STFT measurement SNR. Not the WSJ0 paper aggregate or a real microphone test.",
        'attribution': attribution,
        'notes': ['Computed by the full-size local Torch model; loading a saved example in the browser does not rerun that model.',
                  'The test scene index is selected before seeing results; no best-example selection is performed.',
                  'Ideal order-5 HARP-adapted room response convolved with held-out VCTK speech; no venue or microphone recording.',
                  'The same truncated order-5 V generates observations and is used for inversion. Order-15 mismatch and physical capsule responses are not tested.',
                  'Measurement noise is independent complex STFT Gaussian noise at the requested pooled SNR, with real DC/Nyquist. This does not model a physical recording chain.',
                  'Intermediate items are denoised estimates before each update, final is the terminal state; quality can regress.',
                  'Magnitude/MSC are FOA coefficient-domain metrics; previews use a fixed virtual cardioid pair, not HRTF binaural or loudspeaker feeds.',
                  'No claim of convergence, paper-level accuracy or improvement over Linear.']}
    observation['example_provenance'] = {'split': 'test', 'scene_index': scene_index,
        'scene': scene['metadata'], 'manifest_sha256': digest(manifest_path),
        'inference_source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ('backend/paper_inference.py', 'backend/paper_studio.py',
                         'backend/diffusion_studio.py', 'backend/capture.py',
                         'backend/neural.py', 'backend/neural_audio.py', 'backend/numerics.py')},
        'selection': 'Fixed scene 0 by default, no best-example selection'}
    return observation


_lock = threading.Lock()
_prior = None
_prior_hash = None


def run_paper_studio(config, progress=None):
    global _prior, _prior_hash
    if not _lock.acquire(blocking=False):
        raise ValueError('The full-size model is already computing; wait for the current run')
    try:
        directory = Path(os.environ.get('ADEPS_PAPER_CHECKPOINT', ROOT/'work/paper-prior-v1'))
        manifest = Path(os.environ.get('ADEPS_PAPER_MANIFEST', ROOT/'work/paper-data/scene-manifest.json'))
        if not (directory/'report.json').exists() or not (directory/'paper-prior-v1.pt').exists() or not manifest.exists():
            raise ValueError('新モデルの重み・データが必要です。PAPER_PRIOR.md のローカル実行手順を確認してください。')
        card = json.loads((directory/'report.json').read_text())
        if card['status'] != 'evaluated':
            raise ValueError('Training/evaluation has not finished; no fallback model is used')
        if _prior is None or _prior_hash != card['model']['weights_sha256']:
            _prior = PaperPrior(directory)
            _prior_hash = card['model']['weights_sha256']
        data = make_observation(_prior, manifest, config)
        return run_studio({}, progress, model=_prior, observation=data, sampler=sample)
    finally:
        _lock.release()
