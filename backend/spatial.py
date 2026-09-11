"""Independent learned spatial encoder and paired, offline evaluation.

This is not the ADEPS checkpoint or diffusion algorithm.  A supervised residual
network conditions on a physical resolution matrix; optional soft data consistency
uses a coefficient frozen on validation (zero in this release). References are
passed to metrics only, never to the estimator.
"""
import hashlib
import io
import json
import time
import zipfile
from math import gcd
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
from capture import encode, modal_matrix, real_n3d
from neural import load_bundle, validate_data, quality, run_neural
from neural_audio import prepare_zip, inverse_spectra, si_sdr, wav_bytes, example_zip
from numerics import to_jsonable

MODEL_DIR = Path(__file__).resolve().parents[1] / 'public' / 'models'
SCENES = ('speech_like', 'music', 'noise', 'transient')
MAX_SPATIAL_BINS = 65536


def settings(config):
    q = config.get('microphones', 6)
    seed = config.get('data_seed', 90210)
    radius = float(config.get('radius_m', .06))
    snr = float(config.get('snr_db', 30))
    reg = float(config.get('regularization', .001))
    scene = config.get('scene', 'speech_like')
    if type(q) is not int or q not in (4, 5, 6, 8, 12, 16, 19, 32, 60, 64):
        raise ValueError('Unsupported microphone count')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('data_seed must be an unsigned 32-bit integer')
    if not .01 <= radius <= .25 or not 0 <= snr <= 80 or not 1e-8 <= reg <= 10:
        raise ValueError('Invalid array radius, SNR, or regularization')
    if scene not in SCENES:
        raise ValueError('Unknown source scene')
    for key in ('enabled', 'include_legacy', 'mismatch', 'coplanar'):
        if key in config and type(config[key]) is not bool:
            raise ValueError(key + ' must be boolean')
    return q, seed, radius, snr, reg, scene


def array_positions(q, radius, coplanar=False, rotation=0.):
    angle = np.arange(q) * np.pi * (3 - np.sqrt(5)) + rotation
    z = np.zeros(q) if coplanar else 1 - 2 * (np.arange(q) + .5) / q
    return radius * np.c_[np.sqrt(1-z*z)*np.cos(angle), np.sqrt(1-z*z)*np.sin(angle), z]


def synthetic(config):
    """Independent smooth complex-scene generator. Not speech recordings/HARP.

    Correlated time envelopes, delayed arrivals, random directions and model-order
    mismatch are generated without consulting any trained weights. The logarithmic
    frequency samples are not a WAV/STFT or a 1 Hz measurement resolution.
    """
    q, seed, radius, snr, _, scene = settings(config)
    rng = np.random.default_rng(seed)
    frequencies = np.geomspace(1., 20_000., 128)
    frames = 16
    positions = array_positions(q, radius, config.get('coplanar', False), float(rng.uniform(-np.pi, np.pi)))
    order = 15 if config.get('mismatch', False) else 5
    source_count = 3 if scene == 'music' else 2
    directions = rng.normal(size=(source_count, 3))
    amplitudes = rng.uniform(.4, 1., source_count)
    noise = (rng.normal(size=(128, source_count, frames)) + 1j*rng.normal(size=(128, source_count, frames))) / np.sqrt(2)
    times = np.arange(frames) * .008
    if scene == 'speech_like':
        spectrum = .15 + 1 / (1 + (frequencies/2200)**2)
        envelope = .2 + .8 * np.sin(np.pi * np.arange(frames)/(frames-1))**2
    elif scene == 'music':
        spectrum = .1 + sum(np.exp(-.5 * ((np.log2(frequencies) - np.log2(f))/ .12)**2)
                            for f in (220, 440, 880, 1760, 3520, 7040))
        envelope = .6 + .4 * np.cos(2*np.pi*3*times)**2
    elif scene == 'transient':
        spectrum = np.ones(128)
        envelope = np.exp(-np.arange(frames)/3.)
    else:
        spectrum = np.ones(128)
        envelope = np.ones(frames)
    if scene != 'noise':
        for t in range(1, frames):
            noise[:, :, t] = .78*noise[:, :, t-1] + np.sqrt(1-.78**2)*noise[:, :, t]
    signals = noise * amplitudes[None, :, None] * spectrum[:, None, None] * envelope[None, None, :]
    truth = np.einsum('sc,fst->fct', real_n3d(order, directions), signals)
    # Independent reflected arrivals of each source, with coherent phase delays.
    for reflection in range(3):
        reflected = rng.normal(size=(source_count, 3))
        delay = rng.uniform(.006, .055, source_count)
        phase = np.exp(-2j*np.pi*frequencies[:, None]*delay[None, :])
        truth += (.3 / (reflection+1)) * np.einsum(
            'sc,fst->fct', real_n3d(order, reflected), signals*phase[:, :, None])
    v_true = modal_matrix(frequencies, positions, order)
    p = v_true @ truth
    sigma = np.sqrt(np.mean(abs(p)**2)) * 10**(-snr/20)
    p += sigma*(rng.normal(size=p.shape) + 1j*rng.normal(size=p.shape))/np.sqrt(2)
    return {'frequencies': frequencies, 'V': v_true[:, :, :36], 'p': p,
            'reference': truth[:, :4], 'positions': positions, 'effective_order': order,
            'provenance': 'Independent synthetic complex spectra: '+scene+
              ', coherent delayed arrivals; finite-order free-field array. Not recorded speech, HARP or a measured room.'}


def as_bundle(data):
    out = {'schema': 'adeps-test-array-stft/1', 'sh_ordering': 'ACN', 'sh_normalization': 'N3D',
           'frequencies_hz': data['frequencies'], 'V_real': data['V'].real, 'V_imag': data['V'].imag,
           'p_real': data['p'].real, 'p_imag': data['p'].imag,
           'microphone_positions_m': data['positions'], 'provenance': data['provenance']}
    if data.get('reference') is not None:
        out.update(reference_real=data['reference'].real, reference_imag=data['reference'].imag)
    return out


def input_hash(data):
    digest = hashlib.sha256()
    for value in (data['frequencies'], data['V'].real, data['V'].imag, data['p'].real, data['p'].imag):
        digest.update(json.dumps(list(value.shape)).encode())
        digest.update(np.ascontiguousarray(value, dtype='<f8').tobytes())
    return digest.hexdigest()


def run_spatial(config, progress=None, model=None, tuning=None):
    start = time.perf_counter()
    _, _, _, _, reg, _ = settings(config)
    data = load_bundle(config['bundle']) if 'bundle' in config else synthetic(config)
    validate_data(data, max_bins=MAX_SPATIAL_BINS)
    v, p, reference = (data[k] for k in ('V', 'p', 'reference'))
    linear, encoder, gamma = encode(v, p, reg)
    if progress:
        progress({'stage': 'spatial', 'step': 1, 'total': 3})
    enabled = config.get('enabled', True)
    if model is None and enabled:
        from spatial_model import SpatialModel
        model = SpatialModel()
    tuning_path = MODEL_DIR / 'spatial-tuning.json'
    if tuning is None:
        tuning = json.loads(tuning_path.read_text()) if tuning_path.exists() else {'blend': 1., 'consistency': .15, 'status': 'untuned'}
    if enabled and model.card.get('weights_sha256') and tuning.get('model_sha256') != model.card['weights_sha256']:
        raise ValueError('Frozen inference tuning does not match the model weights')
    blend, consistency = float(tuning['blend']), float(tuning['consistency'])
    if not 0 <= blend <= 1 or not 0 <= consistency <= 1:
        raise ValueError('Invalid frozen inference tuning')
    if enabled:
        predicted = model.predict(linear, encoder @ v, data['frequencies'])
        if predicted.shape != linear.shape or not np.all(np.isfinite(predicted)):
            raise ValueError('Learned prediction has invalid shape or non-finite values')
        enhanced = linear + blend * (predicted - linear)
        enhanced += consistency * (encoder @ (p - v @ enhanced))
        card = model.card
    else:
        enhanced = linear.copy()
        card = {'name': 'Bypass', 'architecture': 'Linear encoder; learned model not loaded',
                'parameter_count': 0, 'weights_sha256': None, 'training': {'steps': 0}}
    if progress:
        progress({'stage': 'spatial', 'step': 2, 'total': 3})
    pnorm = float(np.linalg.norm(p))
    sv = np.linalg.svd(v[:, :, :4], compute_uv=False)
    rank = np.sum(sv > np.maximum(sv[:, :1]*1e-8, 1e-15), axis=1)
    def metric(a):
        m = quality(a[:, :4], reference)
        if reference is not None:
            # Explicit custom definition, not asserted identical to paper SE.
            floor = max(float(np.sqrt(np.mean(abs(reference)**2)))*1e-6, 1e-15)
            m['log_spectral_mae_db'] = float(np.mean(abs(20*np.log10(np.maximum(abs(a[:, :4]), floor))
                                                           -20*np.log10(np.maximum(abs(reference), floor)))))
        else:
            m['log_spectral_mae_db'] = None
        return m
    notes = ['Independent trained residual encoder, not the ADEPS diffusion checkpoint.',
             'OFF is the exact linear baseline. ON uses the same observation and physical response.',
             'No reference is used by the estimator; references are evaluated only after inference.',
             'Synthetic scores do not establish venue performance or superiority to the paper.',
             'No live Max audio stream, microphone measurement, speaker correction or binaural decoder.']
    result = {'kind': 'spatial', 'schema': 'adeps-test-spatial-run/1',
              'implementation': 'physics-conditioned supervised residual encoder; optional validation-selected soft consistency',
              'official_model': False, 'paper_performance_reproduced': False,
              'source': 'https://arxiv.org/abs/2608.24558v3', 'model': card,
              'configuration': {k: value for k, value in config.items() if k != 'bundle'},
              'tuning': tuning, 'input_sha256': input_hash(data), 'provenance': data['provenance'],
              'frequencies_hz': data['frequencies'], 'microphones': v.shape[1], 'frames': p.shape[2],
              'microphone_positions_m': data['positions'], 'effective_order': data['effective_order'],
              'foa_rank_by_frequency': rank, 'rank_deficient_bins': int(np.sum(rank < 4)),
              'quality': {'linear': metric(linear), 'enhanced': metric(enhanced)},
              'diagnostics': {'elapsed_seconds': time.perf_counter()-start,
                              'linear_microphone_residual': float(np.linalg.norm(v@linear-p)/pnorm),
                              'enhanced_microphone_residual': float(np.linalg.norm(v@enhanced-p)/pnorm)},
              'output': {'sh_ordering': 'ACN', 'sh_normalization': 'N3D', 'channel_names': ['W', 'Y', 'Z', 'X'],
                         'linear_real': linear[:, :4].real, 'linear_imag': linear[:, :4].imag,
                         'enhanced_real': enhanced[:, :4].real, 'enhanced_imag': enhanced[:, :4].imag},
              'notes': notes}
    if config.get('include_legacy', False) and v.shape[0]*p.shape[2] > 8192:
        result['legacy'] = {'skipped': True, 'note': 'The previous tiny sampler is limited to 8192 bins; shorten the audio to compare it.'}
        result['notes'].append(result['legacy']['note'])
    elif config.get('include_legacy', False):
        legacy = run_neural({'bundle': as_bundle(data), 'steps': 150, 'eta_prime': 50.,
                             'regularization': reg, 'seed': 42}, progress)
        result['quality']['legacy'] = legacy['quality']['neural']
        result['legacy'] = {'model': legacy['model'], 'configuration': legacy['configuration'],
                            'elapsed_seconds': legacy['diagnostics']['elapsed_seconds'],
                            'note': 'Previous independent tiny model; not official ADEPS.'}
        result['output'].update(legacy_real=legacy['output']['neural_real'], legacy_imag=legacy['output']['neural_imag'])
    result['diagnostics']['elapsed_seconds'] = time.perf_counter()-start
    if progress:
        progress({'stage': 'spatial', 'step': 3, 'total': 3})
    return result


def export_audio(result, metadata, reference):
    signals = {}
    for name in ('linear', 'enhanced', 'legacy'):
        if name+'_real' not in result['output']:
            continue
        spectra = result['output'][name+'_real'] + 1j*result['output'][name+'_imag']
        signals[name] = inverse_spectra(spectra, metadata)
        result['quality'][name]['si_sdr'] = si_sdr(signals[name], reference)
    if reference is not None:
        signals['reference'] = reference
    peak = max(float(np.max(abs(a))) for a in signals.values())
    gain = min(1., .95/peak) if peak > 0 else 1.
    result['audio'] = {**metadata, 'shared_export_gain': gain, 'unscaled_output_peak': peak,
                       'gain_basis': 'Maximum peak across both estimates and the reference if present; one common export gain.'}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, signal in signals.items():
            for norm, factors in (('N3D', np.ones(4)), ('SN3D', np.sqrt([1, 3, 3, 3]))):
                z.writestr(f'{name}_FOA_ACN_{norm}.wav', wav_bytes(metadata['sample_rate_hz'], signal*gain/factors))
        z.writestr('result.json', json.dumps(to_jsonable(result), ensure_ascii=False, allow_nan=False, indent=2))
        z.writestr('READ-ME.txt', 'Paired offline comparison, shared gain and sample alignment.\n'
                   'OFF = linear, ON = enhanced. ACN W,Y,Z,X. Choose matching N3D/SN3D.\n'
                   'Use the SAME FOA decoder and level. These are NOT direct speaker feeds.\n'
                   'Independent model, not an ADEPS paper reproduction or a calibrated room measurement.\n')
    return result, stream.getvalue()


def run_spatial_audio(payload, config, progress=None, model=None, tuning=None):
    bundle, metadata, reference = prepare_zip(payload, config, max_bins=MAX_SPATIAL_BINS)
    result = run_spatial({**config, 'bundle': bundle}, progress, model, tuning)
    return export_audio(result, metadata, reference)


def source_zip(payload, config):
    """Max mono WAV -> virtual array and exact simulated FOA reference.

    Padded FFT propagation of plane waves. This is not the acoustic transfer of
    physical speakers or a recording at the venue. Echoes are deliberate simulation.
    """
    q, seed, radius, snr, _, _ = settings(config)
    if not payload or len(payload) > 32_000_000:
        raise ValueError('Mono WAV must be between 1 byte and 32 MB')
    rate, original = wavfile.read(io.BytesIO(payload))
    if original.ndim != 1 or not 8000 <= rate <= 96000 or len(original) == 0:
        raise ValueError('Choose a mono source WAV (8–96 kHz), not an array recording')
    if original.dtype.kind == 'i':
        original = original.astype(float) / 2**(8*original.dtype.itemsize-1)
    elif original.dtype == np.uint8:
        original = (original.astype(float)-128)/128
    elif original.dtype.kind == 'f':
        original = original.astype(float)
    else:
        raise ValueError('Unsupported WAV sample format')
    if not np.all(np.isfinite(original)) or not np.any(original):
        raise ValueError('Source WAV is silent or non-finite')
    start, duration = float(config.get('start_seconds', 0)), float(config.get('duration_seconds', .4))
    if not np.isfinite(start+duration) or start < 0 or not .02 <= duration <= 5:
        raise ValueError('Select a finite nonnegative start and a 0.02–5 second duration')
    begin, end = int(round(start*rate)), int(round((start+duration)*rate))
    if begin >= len(original) or end > len(original):
        raise ValueError('Selected segment exceeds the source WAV')
    analysis_rate = config.get('analysis_sample_rate_hz', 16000)
    if analysis_rate not in (16000, 48000):
        raise ValueError('Source simulation supports analysis sample rates 16 or 48 kHz')
    source = original[begin:end]
    if rate != analysis_rate:
        divisor = gcd(rate, analysis_rate)
        source = resample_poly(source, analysis_rate//divisor, rate//divisor)
    # Preserve initial silence/latency; do not independently align microphone peaks.
    rng = np.random.default_rng(seed)
    xyz = array_positions(q, radius, config.get('coplanar', False))
    directions = np.array([[.8, .45, .3], [-.4, .7, -.2], [.3, -.4, .7]])
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    padding = int(.08*analysis_rate)
    padded = np.pad(source, (padding, padding))
    f = np.fft.rfftfreq(len(padded), 1/analysis_rate)
    arrivals = np.fft.rfft(padded)[:, None] * np.exp(-2j*np.pi*f[:, None]*np.array([0., .017, .039]))
    arrivals *= np.array([1., .25, .12])
    transfer = np.exp(2j*np.pi*f[:, None, None]*(xyz@directions.T)[None, :, :]/343.)
    microphones = np.fft.irfft(np.einsum('fqs,fs->fq', transfer, arrivals), n=len(padded), axis=0)[padding:padding+len(source)]
    ref_spectra = arrivals @ real_n3d(1, directions)
    reference = np.fft.irfft(ref_spectra, n=len(padded), axis=0)[padding:padding+len(source)]
    sigma = float(np.sqrt(np.mean(microphones**2))) * 10**(-snr/20)
    microphones += sigma*rng.normal(size=microphones.shape)
    manifest = {'schema': 'adeps-test-array-audio/1', 'sh_ordering': 'ACN', 'sh_normalization': 'N3D',
                'array_model': 'freefield-omnidirectional', 'microphone_positions_m': xyz.tolist(),
                'analysis_sample_rate_hz': analysis_rate, 'n_fft': 256, 'hop': 128,
                'provenance': 'User mono source + virtual plane-wave array with 17/39 ms simulated echoes. '
                    'NOT a venue recording or measured microphone response. source_sha256='+hashlib.sha256(payload).hexdigest()}
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('array.json', json.dumps(manifest))
        z.writestr('microphones.wav', wav_bytes(analysis_rate, microphones))
        z.writestr('reference.wav', wav_bytes(analysis_rate, reference))
    return out.getvalue(), {'source_sample_rate_hz': rate, 'source_start_seconds': begin/rate,
                           'source_duration_seconds': (end-begin)/rate,
                           'simulation_sample_rate_hz': analysis_rate, 'simulation_samples': len(source),
                           'source_sha256': hashlib.sha256(payload).hexdigest(),
                           'input_kind': 'mono source through a virtual array; synthetic reference'}


def run_spatial_source(payload, config, progress=None, model=None, tuning=None):
    packed, source_metadata = source_zip(payload, config)
    # Source selection was performed once above. Never apply its offset twice.
    exact_duration = source_metadata['simulation_samples']/source_metadata['simulation_sample_rate_hz']
    bundle, metadata, reference = prepare_zip(packed, {**config, 'start_seconds': 0,
             'duration_seconds': exact_duration}, max_bins=MAX_SPATIAL_BINS)
    metadata.update(source_metadata)
    result = run_spatial({**config, 'bundle': bundle}, progress, model, tuning)
    return export_audio(result, metadata, reference)
