"""Offline, synthetic diffusion trajectory viewer with genuine sampler snapshots.

Uses the existing independently trained TinyDenoiser, not the ADEPS authors'
model and not the separate deterministic spatial residual model. No devices,
network, uploads, or training are involved.
"""
import base64
import hashlib
import io
import json
import zipfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import stft

from capture import encode, modal_matrix, real_n3d
from neural import ALPHA, BETA, CHANNELS, MAX_BINS, ORDER, TinyDenoiser, compress, quality, sample
from neural_audio import inverse_spectra, si_sdr, wav_bytes
from numerics import to_jsonable


BANDS = {'broadband': (20., 8000.), 'low': (20., 500.),
         'mid': (500., 2000.), 'high': (2000., 8000.)}
_diagonal = .5 / np.sqrt(6.)
PREVIEW_MATRIX = np.array([[.5, _diagonal, 0., _diagonal],
                           [.5, -_diagonal, 0., _diagonal]])


def _integer(config, key, default, lower, upper):
    value = config.get(key, default)
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f'{key} must be an integer between {lower} and {upper}')
    return value


def _number(config, key, default, lower, upper):
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{key} must be a finite number between {lower} and {upper}')
    value = float(value)
    if not np.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f'{key} must be a finite number between {lower} and {upper}')
    return value


def settings(config):
    if not isinstance(config, dict):
        raise ValueError('Diffusion studio configuration must be an object')
    q = _integer(config, 'microphones', 6, 4, 16)
    if q not in (4, 6, 8, 12, 16):
        raise ValueError('microphones must be 4, 6, 8, 12, or 16')
    geometry = config.get('geometry', 'sphere')
    if geometry not in ('sphere', 'ring'):
        raise ValueError('geometry must be sphere or ring')
    return {'microphones': q, 'geometry': geometry,
            'radius_m': _number(config, 'radius_m', .06, .01, .25),
            'snr_db': _number(config, 'snr_db', 30., 0., 80.),
            'observation_seed': _integer(config, 'observation_seed', 2026, 0, 2**32-1),
            'seed': _integer(config, 'seed', 42, 0, 2**32-1),
            'eta_prime': _number(config, 'eta_prime', 50., 0., 100.),
            'steps': _integer(config, 'steps', 24, 8, 80),
            'sample_rate': _integer(config, 'sample_rate', 16000, 16000, 16000),
            'duration_seconds': _number(config, 'duration_seconds', .35, .08, .45),
            'n_fft': _integer(config, 'n_fft', 256, 256, 256),
            'regularization': _number(config, 'regularization', .001, 1e-8, 10.)}


def _unit_direction(azimuth, elevation):
    az, el = np.deg2rad([azimuth, elevation])
    return np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])


def make_observation(config):
    """Coherent time-domain sources, transformed once, then sampled by modal V.

    This is an order-matched, STFT-domain plane-wave model. It does not simulate
    a measured capsule response or a room, and it deliberately does not claim
    full-order propagation accuracy at high frequencies/large array radii.
    """
    cfg = settings(config)
    rate, fft = cfg['sample_rate'], cfg['n_fft']
    count = int(round(rate*cfg['duration_seconds']))
    hop = fft//2
    q = cfg['microphones']
    if cfg['geometry'] == 'ring':
        angles = 2*np.pi*np.arange(q)/q
        positions = cfg['radius_m']*np.c_[np.cos(angles), np.sin(angles), np.zeros(q)]
    else:
        angles = np.arange(q)*np.pi*(3-np.sqrt(5))
        z = 1-2*(np.arange(q)+.5)/q
        positions = cfg['radius_m']*np.c_[np.sqrt(1-z*z)*np.cos(angles),
                                         np.sqrt(1-z*z)*np.sin(angles), z]
    rng = np.random.default_rng(cfg['observation_seed'])
    t = np.arange(count)/rate
    envelope = np.sin(np.pi*np.arange(count)/(count-1))**2
    phases = rng.uniform(0, 2*np.pi, 3)
    tonal = .16*envelope*(np.sin(2*np.pi*(330*t+90*t*t)+phases[0])
                          + .28*np.sin(2*np.pi*660*t+phases[1]))
    pulse_envelope = np.exp(-.5*((t-.62*count/rate)/.009)**2)
    transient = (.10*envelope*np.sin(2*np.pi*(1180*t+180*t*t)+phases[2])
                 + .055*pulse_envelope*rng.normal(size=count))
    waves = np.stack([tonal, transient])
    directions = np.stack([_unit_direction(-45, 25), _unit_direction(115, -20)])
    frequencies, _, spectrum = stft(waves, fs=rate, window='hann', nperseg=fft,
                                     noverlap=fft-hop, nfft=fft, boundary='zeros',
                                     padded=True, scaling='spectrum', axis=-1)
    truth = np.einsum('sc,sft->fct', real_n3d(ORDER, directions), spectrum)
    v = modal_matrix(frequencies, positions, ORDER)
    # Real-valued endpoints are the declared projection for sampled real audio.
    v[[0, -1]] = v[[0, -1]].real
    truth[[0, -1]] = truth[[0, -1]].real
    p = v @ truth
    noise = rng.normal(size=(q, count))
    _, _, noise_spectrum = stft(noise, fs=rate, window='hann', nperseg=fft,
                                noverlap=fft-hop, nfft=fft, boundary='zeros',
                                padded=True, scaling='spectrum', axis=-1)
    noise_spectrum = noise_spectrum.transpose(1, 0, 2)
    noise_scale = np.linalg.norm(p)/np.linalg.norm(noise_spectrum)*10**(-cfg['snr_db']/20)
    p = p + noise_scale*noise_spectrum
    if len(frequencies)*p.shape[2] > MAX_BINS:
        raise ValueError(f'Maximum {MAX_BINS} frequency-time bins per studio run')
    digest = hashlib.sha256()
    for a in (frequencies, v.real, v.imag, p.real, p.imag):
        digest.update(json.dumps(list(a.shape)).encode('ascii'))
        digest.update(np.ascontiguousarray(a, dtype='<f8').tobytes())
    audio = {'sample_rate_hz': rate, 'sample_rate': rate, 'samples': count,
             'duration_seconds': count/rate, 'n_fft': fft, 'hop': hop,
             'window': 'periodic Hann', 'stft_scaling': 'scipy spectrum; zero padding',
             'frequency_bin_spacing_hz': rate/fft, 'nyquist_hz': rate/2,
             'real_wave_projection': 'Set imaginary DC and Nyquist coefficients to zero before covariance, metrics, and WAV export.'}
    sources = [{'id': 'tonal', 'label': 'Harmonic chirp', 'direction': directions[0].tolist(),
                'azimuth_deg': -45., 'elevation_deg': 25.},
               {'id': 'transient', 'label': 'Upper tone and short noise burst',
                'direction': directions[1].tolist(), 'azimuth_deg': 115., 'elevation_deg': -20.}]
    return {'configuration': cfg, 'V': v, 'p': p, 'reference': truth,
            'frequencies': frequencies, 'microphone_positions_m': positions,
            'source_directions': sources, 'audio': audio,
            'input_sha256': digest.hexdigest()}


def real_wave_foa(spectra):
    foa = np.array(spectra[:, :4], dtype=np.complex128, copy=True)
    foa[[0, -1]] = foa[[0, -1]].real
    return foa


def covariance(spectra, frequencies):
    """Real, uncentered second moment of actual complex FOA coefficients.

    R = Re(mean over selected frequency bins and time frames of a a^H).
    No per-item normalization, frequency whitening, or microphone-position
    interpolation is applied. Global WAV gain is applied by the caller.
    """
    a = np.asarray(spectra)
    f = np.asarray(frequencies)
    if a.ndim != 3 or a.shape[1] != 4 or a.shape[0] != len(f) or a.shape[2] < 1:
        raise ValueError('Covariance expects [frequency,4,time] coefficients')
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(f)):
        raise ValueError('Covariance requires finite coefficients and frequencies')
    result = {}
    for name, (lo, hi) in BANDS.items():
        mask = (f >= lo) & ((f <= hi) if name in ('broadband', 'high') else (f < hi))
        if not mask.any():
            raise ValueError(f'No frequency bins in covariance band {name}')
        subset = a[mask]
        r = np.einsum('fct,fdt->cd', subset, subset.conj()).real / (mask.sum()*a.shape[2])
        result[name] = ((r+r.T)/2).tolist()
    return result


def _preview_pcm16(rate, audio):
    stereo = audio @ PREVIEW_MATRIX.T
    data = np.rint(np.clip(stereo, -1., 1.)*32767).astype(np.int16)
    target = io.BytesIO()
    wavfile.write(target, rate, data)
    return target.getvalue()


def run_studio(config, progress=None):
    """Return JSON-safe trajectory metadata plus a ZIP of actual 4-channel WAVs."""
    data = make_observation(config)
    cfg = data['configuration']
    v, p, reference = data['V'], data['p'], data['reference']
    if progress:
        progress({'stage': 'preparing', 'message': 'Preparing coherent synthetic sources and array response'})
    linear, encoder, gamma = encode(v, p, cfg['regularization'])
    scale = float(np.sqrt(np.mean(abs(linear)**2)))
    if not np.isfinite(scale) or scale < 1e-12:
        raise ValueError('Encoded observation is too small for the diffusion prior')
    y = compress(linear/scale)
    ev = encoder @ v
    denoiser = TinyDenoiser()
    wanted = set(np.rint(np.linspace(0, cfg['steps']-2, 6)).astype(int).tolist())
    snapshots = []

    def snapshot(meta, coefficients):
        if meta['stage'] == 'final_sample' or meta['step'] in wanted:
            snapshots.append((dict(meta), coefficients*scale))

    final, trace = sample(y, ev, denoiser, steps=cfg['steps'], eta_prime=cfg['eta_prime'],
                          seed=cfg['seed'], progress=progress, snapshot=snapshot)
    final *= scale
    if not np.array_equal(snapshots[-1][1], final):
        raise RuntimeError('Final snapshot differs from the actual sampler output')
    raw = [({'id': 'reference', 'label': 'Synthetic reference', 'stage': 'reference',
             'step': None, 'iteration': None, 'sigma': None}, reference),
           ({'id': 'linear', 'label': 'Linear baseline', 'stage': 'linear',
             'step': None, 'iteration': None, 'sigma': None}, linear)]
    for meta, coefficients in snapshots:
        is_final = meta['stage'] == 'final_sample'
        meta.update(id='final' if is_final else f"denoised_{meta['step']:03d}",
                    label='Final sampled output' if is_final else f"Denoised estimate before update {meta['iteration']}")
        raw.append((meta, coefficients))
    foas = [real_wave_foa(coefficients) for _, coefficients in raw]
    signals = [inverse_spectra(a, data['audio']) for a in foas]
    if not all(np.all(np.isfinite(a)) for a in signals):
        raise ValueError('Audio reconstruction became non-finite')
    peak = max(float(np.max(abs(a))) for a in signals)
    gain = min(1., .95/peak) if peak > 0 else 1.
    audio = {**data['audio'], 'shared_gain': gain, 'shared_export_gain': gain,
             'unscaled_output_peak': peak,
             'gain_basis': 'One attenuation from the largest 4ch sample across reference, linear, and every checkpoint; no per-item loudness normalization.',
             'sh_ordering': 'ACN', 'sh_normalization': 'N3D', 'channel_names': ['W', 'Y', 'Z', 'X'],
             'preview': {'channels': 2, 'encoding': 'PCM16 WAV',
                         'kind': 'fixed virtual cardioid pair; not binaural or HRTF rendering',
                         'left_azimuth_deg': 45., 'right_azimuth_deg': -45.,
                         'elevation_deg': 0., 'matrix': PREVIEW_MATRIX.tolist(),
                         'formula': 's(d)=0.5 W + 0.5/sqrt(3) (d_y Y + d_z Z + d_x X)'},
             'bands_hz': {name: {'min_hz': lo, 'max_hz': hi,
                                 'max_inclusive': name in ('broadband', 'high'),
                                 'actual_min_hz': float(data['frequencies'][
                                     (data['frequencies'] >= lo) & ((data['frequencies'] <= hi) if name in ('broadband', 'high') else (data['frequencies'] < hi))][0])}
                          for name, (lo, hi) in BANDS.items()}}
    items = []
    for (meta, full), foa, signal in zip(raw, foas, signals):
        metric = quality(foa, foas[0])
        metric['encoded_residual'] = float(np.linalg.norm(compress(ev@(full/scale))-y)/np.linalg.norm(y))
        metric['encoded_residual_definition'] = 'Relative compressed E V residual of all 36 unprojected sampler coefficients against the encoded observation; not a FOA accuracy metric.'
        metric['si_sdr'] = si_sdr(signal, signals[0])
        item = {**meta, 'covariance': covariance(foa*gain, data['frequencies']),
                'preview_wav_base64': base64.b64encode(_preview_pcm16(audio['sample_rate_hz'], signal*gain)).decode('ascii'),
                'metrics': metric, 'wav_filename': f"{meta['id']}_FOA_ACN_N3D.wav"}
        items.append(item)
    singular = np.linalg.svd(v[:, :, :4], compute_uv=False)
    ranks = np.sum(singular > np.maximum(singular[:, :1]*1e-8, 1e-15), axis=1)
    result = {'kind': 'diffusion-studio', 'schema': 'adeps-test-diffusion-studio/1',
              'implementation': 'Existing independent EDM TinyDenoiser and ADEPS-equation Euler sampler; synthetic audio experiment',
              'official_model': False, 'paper_performance_reproduced': False,
              'paper_source': 'https://arxiv.org/abs/2608.24558v3',
              'model': denoiser.card, 'input_sha256': data['input_sha256'],
              'configuration': {**cfg, 'alpha': ALPHA, 'beta': BETA,
                                'sigma_max': 20., 'sigma_min': .002, 'rho': 10.,
                                'observation_rms_scale': scale,
                                'gamma_squared_by_frequency': gamma,
                                'effective_order': ORDER, 'prior_order': ORDER,
                                'terminal': 'M positive sigma points followed by zero; exactly M Euler updates'},
              'microphone_positions_m': data['microphone_positions_m'],
              'source_directions': data['source_directions'],
              'frequencies_hz': data['frequencies'], 'frames': int(p.shape[2]),
              'frequency_time_bins': int(len(data['frequencies'])*p.shape[2]),
              'foa_rank_by_frequency': ranks, 'rank_deficient_bins': int(np.sum(ranks < 4)),
              'audio': audio, 'trace': trace,
              'covariance_definition': 'R_b = Re mean_{frequency in band,time}(a a^H), using real-wave-projected ACN/N3D FOA and shared export gain. Directional coefficient RMS = sqrt(max(0,Y R_b Y^T)); Y=[1,sqrt(3)d_y,sqrt(3)d_z,sqrt(3)d_x]. This is a directional representation at the array centre, not a room pressure map or microphone response.',
              'checkpoint_semantics': 'Intermediate items are D(x_i,sigma_i), expanded, before Euler update i+1; step counts completed updates. Final item is the actual expanded state after the terminal Euler update, not another denoiser call. All FOA endpoints undergo the declared real-wave projection.',
              'reference': items[0], 'linear': items[1], 'checkpoints': items[2:],
              'metrics': {'linear': items[1]['metrics'], 'final': items[-1]['metrics']},
              'notes': [
                  'Procedural coherent tonal/transient waveforms, two fixed plane-wave directions, no real speech, room, or microphone recording.',
                  'The same order-5 modal model generates observations and is used for inversion; high-frequency model truncation and real-hardware mismatch are not tested.',
                  'Observation seed changes source phases, transient noise, and microphone noise. Diffusion seed changes initialization only; eta and steps do not change the input hash.',
                  'eta=0 disables the measurement-gradient guidance; the initialization remains conditioned on the encoded observation.',
                  'A planar ring lacks elevation information; a visually plausible generated Z component is not evidence that it was measured.',
                  'This 24,072-parameter procedural prior is not the paper checkpoint; no improvement or paper-level quality is guaranteed.',
                  'Covariances use STFT-bin means, not calibrated SPL or a spatial pressure field. Intermediate clean estimates may worsen and are not noisy latent states.',
                  'PCM16 stereo previews use a fixed cardioid pair; 4ch WAVs must be Ambisonics-decoded before speaker playback.'
              ]}
    result = to_jsonable(result)
    metadata = {**result, 'reference': {k: value for k, value in result['reference'].items() if k != 'preview_wav_base64'},
                'linear': {k: value for k, value in result['linear'].items() if k != 'preview_wav_base64'},
                'checkpoints': [{k: value for k, value in item.items() if k != 'preview_wav_base64'} for item in result['checkpoints']]}
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item, signal in zip(items, signals):
            archive.writestr(item['wav_filename'], wav_bytes(audio['sample_rate_hz'], signal*gain))
        archive.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2))
        archive.writestr('READ-ME.txt',
                          'Diffusion studio: independent tiny procedural EDM model, not official ADEPS.\n'
                          'WAVs: 4ch float32, ACN/N3D W,Y,Z,X; same segment and shared gain.\n'
                          'Within this ZIP, use the same Ambisonics decoder and playback level for every file.\n'
                          'Across runs, account for each metadata.audio.shared_gain before comparing levels.\n'
                          'Intermediate denoised files estimate a clean signal before the named update; final is the actual terminal sample.\n'
                          'These channels are not four speaker feeds. No audio-device routing is configured.\n'
                          f'Shared gain: {gain:.12g}\nSee metadata.json for all provenance, conventions, and limitations.\n')
    if progress:
        progress({'stage': 'complete', 'message': 'Diffusion snapshots and aligned WAV files ready', 'total': cfg['steps']})
    return result, target.getvalue()
