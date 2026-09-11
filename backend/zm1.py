"""Local-only ZM-1 intake and IEM response audit. No diffusion or device access.

This deliberately accepts one audited SOFA revision, not arbitrary SOFA files.
IEM stores zenith in column two of BOTH spherical position arrays. Generic
SOFA elevation handling would silently reflect/misplace these directions.
"""
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.io import wavfile
from capture import real_n3d, encode
from neural_audio import read_wave, wav_bytes, prepare_zip, inverse_spectra
from numerics import to_jsonable

SOFA_SHA256 = 'd3e4a44e5df480db7b36c4cf613d9eb481fa8016dce07c09ac00e275e7d212f5'
SOFA_URL = 'https://phaidra.kug.ac.at/o:91937'
LIMITATIONS = [
    'Research response candidate, not a calibrated response for a purchased unit.',
    'Measured ZM-1 generation, serial number and mapping to current USB channels are unconfirmed.',
    'Absolute incident-pressure reference, source equalization and common time origin are unconfirmed.',
    'Finite-distance source (1.5 m); SH fitting treats source direction as a plane-wave basis approximation.',
    '128 samples at 48 kHz cover 2.667 ms. Zero padding adds frequency samples, not measured resolution.',
    'Original 128-point DFT spacing is 375 Hz. No physical accuracy claim at 1 Hz or across 1–20 kHz.',
    'Order-5 fitting is a truncation; 19 capsules cannot uniquely observe all 36 order-5 coefficients.',
    'Public-domain landing metadata conflicts with the unspecified license inside SOFA; do not redistribute the response or derived assets until clarified.',
    'No official ADEPS weights are used. These tools do not establish paper performance or speaker calibration.',
]


def zenith_xyz(positions):
    """[azimuth degrees, zenith degrees, radius metres] -> Cartesian XYZ."""
    p = np.asarray(positions, float)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        raise ValueError('Expected finite [N,3] spherical coordinates')
    if np.any((p[:, 1] < 0) | (p[:, 1] > 180)) or np.any(p[:, 2] <= 0):
        raise ValueError('Invalid zenith or radius')
    az, ze = np.deg2rad(p[:, :2]).T
    return p[:, 2, None] * np.c_[np.sin(ze)*np.cos(az), np.sin(ze)*np.sin(az), np.cos(ze)]


def load_iem_sofa(path):
    import h5py  # Optional local dependency; never included in the browser bundle.
    path = Path(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOFA_SHA256:
        raise ValueError('SOFA checksum differs from the audited IEM ZM-1 revision; re-audit before use')
    with h5py.File(path, 'r') as f:
        ir = np.asarray(f['Data.IR'], float)
        source = np.asarray(f['SourcePosition'], float)
        receiver = np.asarray(f['ReceiverPosition'], float)[:, :, 0]
        rate = np.asarray(f['Data.SamplingRate'], float)
        delay = np.asarray(f['Data.Delay'], float)
        if ir.shape != (576, 19, 128) or source.shape != (576, 3) or receiver.shape != (19, 3):
            raise ValueError('Unexpected IEM response dimensions')
        if rate.shape != (1,) or rate[0] != 48000 or np.any(delay != 0):
            raise ValueError('Unsupported sample rate or nonzero delay')
        if not np.isfinite(ir).all() or not np.all(np.sum(ir*ir, axis=2) > 0):
            raise ValueError('Non-finite or silent direction/capsule response')
    return {'ir': ir, 'source': source, 'receiver_xyz': zenith_xyz(receiver),
            'directions': zenith_xyz(source)/source[:, 2, None], 'sample_rate': 48000,
            'sha256': digest, 'source_url': SOFA_URL}


def holdout_mask(source):
    """Deterministic interleaved angular holdout; no held-out response enters fit."""
    az = np.searchsorted(np.unique(source[:, 0]), source[:, 0])
    ze = np.searchsorted(np.unique(source[:, 1]), source[:, 1])
    return (az + 2*ze) % 5 == 0


def fit_modal(transfer, directions, weights, train):
    """Fit H[f,q,d] ≈ V[f,q,c] Y[d,c] using area-weighted complex LS."""
    y = real_n3d(5, directions)
    root_w = np.sqrt(weights[train])
    design = y[train]*root_w[:, None]
    if np.linalg.matrix_rank(design) != 36:
        raise ValueError('Training directions do not span order 5')
    projector = np.linalg.pinv(design)*root_w[None, :]
    return np.einsum('cd,fqd->fqc', projector, transfer[:, :, train])


def response_profile(data, n_fft=256):
    if n_fft not in (128, 256, 512):
        raise ValueError('Use FFT 128, 256 or 512; larger manifests exceed current input bounds')
    f = np.fft.rfftfreq(n_fft, 1/data['sample_rate'])
    h = np.fft.rfft(data['ir'], n=n_fft, axis=2).transpose(2, 1, 0)
    held = holdout_mask(data['source'])
    weights = np.sin(np.deg2rad(data['source'][:, 1]))
    v = fit_modal(h, data['directions'], weights, ~held)
    y = real_n3d(5, data['directions'])
    predicted = np.einsum('fqc,dc->fqd', v, y)
    def error(mask):
        w = weights[mask][None, None, :]
        num = np.sum(abs(predicted[:, :, mask]-h[:, :, mask])**2*w, axis=(1, 2))
        den = np.sum(abs(h[:, :, mask])**2*w, axis=(1, 2))
        return 10*np.log10(np.maximum(num/den, 1e-30))
    sv = np.linalg.svd(v, compute_uv=False)
    sv_foa = np.linalg.svd(v[:, :, :4], compute_uv=False)
    profile = {
        'schema': 'adeps-test-zm1-response/1', 'source_sha256': data['sha256'],
        'source_url': SOFA_URL, 'response_status': 'experimental-unverified-device-compatibility',
        'source_angle_convention': 'azimuth/zenith, degrees (audited IEM exception)',
        'sh_ordering': 'ACN', 'sh_normalization': 'N3D', 'order': 5,
        'analysis_sample_rate_hz': 48000, 'n_fft': n_fft, 'hop': n_fft//2,
        'frequencies_hz': f.tolist(), 'V_real': v.real.tolist(), 'V_imag': v.imag.tolist(),
        'microphone_positions_m': data['receiver_xyz'].tolist(),
        'channel_order': 'SOFA receiver index; correspondence to a real USB recording unverified',
        'training_direction_indices': np.flatnonzero(~held).tolist(),
        'heldout_direction_indices': np.flatnonzero(held).tolist(),
        'limitations': LIMITATIONS,
    }
    audit = {
        'source_sha256': data['sha256'], 'source_url': SOFA_URL,
        'raw_response_shape': list(data['ir'].shape), 'sample_rate_hz': 48000,
        'source_distance_m': np.unique(data['source'][:, 2]).tolist(),
        'training_directions': int((~held).sum()), 'heldout_directions': int(held.sum()),
        'frequency_hz': f, 'train_response_error_db': error(~held),
        'heldout_response_error_db': error(held),
        'order5_rank': np.sum(sv > sv[:, :1]*1e-8, axis=1),
        'foa_column_condition': sv_foa[:, 0]/np.maximum(sv_foa[:, -1], 1e-30),
        'foa_condition_note': 'Condition of first four columns only; does not measure higher-order interference or calibrated accuracy.',
        'metric': 'Area-weighted relative complex pressure-response fit error; not speech SI-SDR or ADEPS improvement.',
        'official_model': False, 'paper_performance_reproduced': False, 'limitations': LIMITATIONS,
    }
    return profile, to_jsonable(audit)


def validate_profile(profile):
    if profile.get('schema') != 'adeps-test-zm1-response/1' or profile.get('source_sha256') != SOFA_SHA256:
        raise ValueError('Expected an audited IEM ZM-1 response profile')
    n = profile.get('n_fft')
    if n not in (128, 256, 512) or profile.get('analysis_sample_rate_hz') != 48000 or profile.get('hop') != n//2:
        raise ValueError('Unsupported response STFT')
    if profile.get('sh_ordering') != 'ACN' or profile.get('sh_normalization') != 'N3D':
        raise ValueError('Expected real ACN/N3D response')
    real = np.asarray(profile['V_real'], float)
    imag = np.asarray(profile['V_imag'], float)
    if real.shape != imag.shape:
        raise ValueError('Response real/imaginary shapes must match without broadcasting')
    v = real+1j*imag
    grid = np.asarray(profile['frequencies_hz'])
    if v.shape != (n//2+1, 19, 36) or not np.isfinite(v).all():
        raise ValueError('Invalid response matrix')
    if grid.shape != (n//2+1,) or not np.allclose(grid, np.fft.rfftfreq(n, 1/48000), atol=1e-6, rtol=0):
        raise ValueError('Response frequency grid does not match STFT')
    coordinates = np.asarray(profile['microphone_positions_m'], float)
    if coordinates.shape != (19,3) or not np.isfinite(coordinates).all():
        raise ValueError('Expected finite receiver coordinates [19,3]')
    return v


def inspect_audio(rate, audio):
    if rate != 48000 or audio.ndim != 2 or audio.shape[1] != 19:
        raise ValueError('ZM-1 intake requires raw 19-channel WAV at 48 kHz; B-format/stereo is not raw capsule audio')
    if len(audio) == 0 or not np.isfinite(audio).all():
        raise ValueError('Empty or non-finite recording')
    peak = np.max(abs(audio), axis=0)
    rms = np.sqrt(np.mean(audio*audio, axis=0))
    silent = np.flatnonzero(peak <= 1e-10).tolist()
    clipped = np.sum(abs(audio) >= 1, axis=0).tolist()
    duplicate = [[i, j] for i in range(19) for j in range(i+1, 19)
                 if np.array_equal(audio[:, i], audio[:, j]) and peak[i] > 1e-10]
    return {'sample_rate_hz': rate, 'channels': 19, 'samples': len(audio),
            'duration_seconds': len(audio)/rate, 'peak_by_channel': peak.tolist(),
            'rms_by_channel': rms.tolist(), 'silent_channels_zero_based': silent,
            'samples_at_or_above_full_scale': clipped, 'exact_duplicate_channel_pairs_zero_based': duplicate,
            'ready_for_packaging': not silent and not any(clipped) and not duplicate,
            'scope': 'Digital integrity check only; does not verify sensitivity, phase, capsule position, channel mapping or clipping earlier in the recording chain.'}


def load_recording(path):
    p = Path(path)
    if p.stat().st_size > 512_000_000:
        raise ValueError('Export a raw 19ch excerpt smaller than 512 MB first')
    rate, audio = read_wave(p.read_bytes())
    return rate, audio, inspect_audio(rate, audio)


def make_audio_zip(profile, audio, provenance):
    validate_profile(profile)
    qc = inspect_audio(48000, audio)
    if not qc['ready_for_packaging']:
        raise ValueError('Recording has silent, duplicate or full-scale channels; inspect before packaging')
    manifest = {key: profile[key] for key in ('sh_ordering', 'sh_normalization', 'analysis_sample_rate_hz',
                'n_fft', 'hop', 'frequencies_hz', 'V_real', 'V_imag', 'microphone_positions_m')}
    manifest.update(schema='adeps-test-array-audio/1', provenance=provenance,
                    response_source_sha256=profile['source_sha256'],
                    response_status=profile['response_status'], limitations=LIMITATIONS)
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('array.json', json.dumps(manifest, allow_nan=False))
        z.writestr('microphones.wav', wav_bytes(48000, audio))
    payload = output.getvalue()
    # Verify against the CURRENT importer, including its frequency/bin/size limits.
    prepare_zip(payload, {'duration_seconds': len(audio)/48000})
    return payload


def replay(data, profile):
    """Generated excitation through a held-out measured IR; NOT a field recording."""
    from scipy.signal import fftconvolve
    validate_profile(profile)
    indices = profile['heldout_direction_indices']
    # One middle-elevation direction, excluded from the response fit.
    idx = min(indices, key=lambda k: abs(data['source'][k, 1]-70)+abs(data['source'][k, 0]-45))
    rng = np.random.default_rng(20260911)
    excitation = .06*rng.normal(size=4800)
    excitation *= np.sin(np.pi*np.arange(4800)/4799)**2
    audio = fftconvolve(excitation[:, None], data['ir'][idx].T, mode='full', axes=0)[:4800]
    payload = make_audio_zip(profile, audio,
        f'MEASUREMENT-BASED SYNTHETIC REPLAY: generated noise convolved with IEM held-out direction {idx}; not a new recording, no official ADEPS, no reference FOA')
    bundle, metadata, _ = prepare_zip(payload, {'duration_seconds': .1})
    v = bundle['V_real']+1j*bundle['V_imag']
    p = bundle['p_real']+1j*bundle['p_imag']
    encoded, _, _ = encode(v, p, .001)
    linear = inverse_spectra(encoded[:, :4], metadata)
    gain = min(1., .95/max(float(np.max(abs(linear))), 1e-30))
    check = {'kind': 'measurement-based-synthetic-replay', 'heldout_direction_index': idx,
             'source_azimuth_zenith_degrees': data['source'][idx, :2].tolist(),
             'microphones': 19, 'input_frames': p.shape[2], 'frequency_bins': p.shape[0],
             'input_duration_seconds': .1, 'linear_export_gain': gain,
             'linear_output_finite': bool(np.isfinite(linear).all()),
             'reference_foa_available': False, 'si_sdr': None,
             'official_model': False, 'neural_inference_run': False,
             'note': 'Pipeline check only. Same measured dataset, held-out angle. Common time/pressure reference unresolved; no ground-truth FOA or perceptual quality claim.'}
    return payload, wav_bytes(48000, linear*gain/np.sqrt([1, 3, 3, 3])), check
