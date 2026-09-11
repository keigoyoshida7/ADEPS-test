"""Offline WAV preparation/export. No audio-device or network operations."""
import io
import json
import zipfile
from math import gcd
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft, istft, resample_poly
from capture import complex_array, modal_matrix, real_n3d
from numerics import to_jsonable
from neural import run_neural, MAX_BINS


def read_wave(payload):
    rate, audio = wavfile.read(io.BytesIO(payload))
    if audio.ndim != 2 or not 4 <= audio.shape[1] <= 64 or not 8000 <= rate <= 96000:
        raise ValueError('Use one synchronous multichannel WAV, 4–64 channels, 8–96 kHz')
    if audio.dtype.kind == 'i':
        audio = audio.astype(float) / (2 ** (8*audio.dtype.itemsize - 1))
    elif audio.dtype == np.uint8:
        audio = (audio.astype(float)-128)/128
    elif audio.dtype.kind == 'f':
        audio = audio.astype(float)
    else:
        raise ValueError('Unsupported WAV sample representation')
    if not np.all(np.isfinite(audio)):
        raise ValueError('Non-finite WAV samples')
    return int(rate), audio


def wav_bytes(rate, data):
    out = io.BytesIO()
    wavfile.write(out, rate, np.asarray(data, np.float32))
    return out.getvalue()


def prepare_zip(payload, config, max_bins=MAX_BINS):
    """Import array.json + microphones.wav [+ reference.wav], without extracting paths."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        files = archive.infolist()
        if len(files) > 8 or sum(f.file_size for f in files) > 32_000_000:
            raise ValueError('Uncompressed audio ZIP limit: 32 MB, 8 entries')
        if len({f.filename for f in files}) != len(files):
            raise ValueError('Duplicate ZIP entries are not supported')
        manifest = json.loads(archive.read('array.json'))
        original_rate, source = read_wave(archive.read('microphones.wav'))
        reference = None
        if 'reference.wav' in archive.namelist():
            ref_rate, reference = read_wave(archive.read('reference.wav'))
            if ref_rate != original_rate or reference.shape != (len(source), 4):
                raise ValueError('Reference WAV must be synchronized 4-channel FOA at the same sample rate and length')
    if manifest.get('schema') != 'adeps-test-array-audio/1':
        raise ValueError('Expected array.json schema adeps-test-array-audio/1')
    if manifest.get('sh_ordering') != 'ACN' or manifest.get('sh_normalization') != 'N3D':
        raise ValueError('array.json must declare real ACN/N3D')
    rate = manifest.get('analysis_sample_rate_hz', 16000)
    fft = manifest.get('n_fft', 256)
    hop = manifest.get('hop', 128)
    if rate not in (8000, 16000, 24000, 48000) or fft not in (128,256,512,1024) or type(hop) is not int or hop != fft//2:
        raise ValueError('Supported STFT: Hann, FFT 128/256/512/1024, 50% overlap; sample rate 8/16/24/48 kHz')
    start = float(config.get('start_seconds', 0))
    duration = float(config.get('duration_seconds', .4))
    if not np.isfinite(start+duration) or start < 0 or not .02 <= duration <= 5:
        raise ValueError('Choose a valid segment: 0.02–5 seconds')
    begin, end = int(round(start*original_rate)), int(round((start+duration)*original_rate))
    if begin >= len(source) or end > len(source)+1:
        raise ValueError('Selected segment exceeds the WAV duration')
    end = min(end, len(source))
    source = source[begin:end]
    if reference is not None:
        reference = reference[begin:end]
    if rate != original_rate:
        divisor = gcd(rate, original_rate)
        source = resample_poly(source, rate//divisor, original_rate//divisor, axis=0)
        if reference is not None:
            reference = resample_poly(reference, rate//divisor, original_rate//divisor, axis=0)
    if len(source) < fft:
        raise ValueError('The selected segment must be at least one FFT window long')
    if (fft//2+1) * (int(np.ceil(len(source)/hop))+1) > max_bins:
        raise ValueError(f'Segment exceeds {max_bins} frequency-time bins; shorten duration')
    def transform(audio):
        f, _, z = stft(audio.T, fs=rate, window='hann', nperseg=fft, noverlap=fft-hop,
                       nfft=fft, boundary='zeros', padded=True, scaling='spectrum')
        return f, z.transpose(1,0,2)
    frequencies, p = transform(source)
    positions = manifest.get('microphone_positions_m', [])
    if 'V_real' in manifest:
        measured = complex_array(manifest['V_real'], manifest['V_imag'], 'V')
        grid = np.asarray(manifest['frequencies_hz'], float)
        if measured.shape != (len(frequencies), source.shape[1], 36) or grid.shape != frequencies.shape or not np.allclose(grid, frequencies, rtol=0, atol=1e-6):
            raise ValueError('Imported V must match this exact STFT frequency grid, [F,Q,36]; no silent interpolation')
        v = measured
        v_kind = 'user-supplied array transfer (calibration unverified)'
    else:
        if manifest.get('array_model') != 'freefield-omnidirectional':
            raise ValueError('Supply V or explicitly select the freefield-omnidirectional array model')
        coordinates = np.asarray(positions, float)
        if coordinates.shape != (source.shape[1],3) or not np.all(np.isfinite(coordinates)):
            raise ValueError('Provide one finite XYZ position in metres per WAV channel')
        v = modal_matrix(frequencies, coordinates, 5)
        v_kind = 'modelled freefield omnidirectional; not a measured device response'
    bundle = {'schema': 'adeps-test-array-stft/1', 'sh_ordering': 'ACN', 'sh_normalization': 'N3D',
              'frequencies_hz': frequencies, 'V_real': v.real, 'V_imag': v.imag,
              'p_real': p.real, 'p_imag': p.imag, 'microphone_positions_m': positions,
              'provenance': str(manifest.get('provenance', 'user supplied WAV')) + '; ' + v_kind}
    if reference is not None:
        _, z = transform(reference)
        bundle.update(reference_real=z.real, reference_imag=z.imag)
    audio_metadata = {'original_sample_rate_hz': original_rate, 'sample_rate_hz': rate,
                      'n_fft': fft, 'hop': hop, 'window': 'periodic Hann',
                      'scaling': 'scipy spectrum; zero boundary padding',
                      'start_seconds': begin/original_rate, 'duration_seconds': len(source)/rate,
                      'samples': len(source), 'array_transfer': v_kind,
                      'input_peak': float(np.max(abs(source))),
                      'input_samples_at_or_above_full_scale': int(np.sum(abs(source)>=1))}
    return bundle, audio_metadata, reference


def inverse_spectra(spectra, metadata):
    # Real-wave constraints: DC and Nyquist have no imaginary degree of freedom.
    z = spectra.copy()
    z[[0,-1]] = z[[0,-1]].real
    _, signal = istft(z.transpose(1,0,2), fs=metadata['sample_rate_hz'], window='hann',
                      nperseg=metadata['n_fft'], noverlap=metadata['n_fft']-metadata['hop'],
                      nfft=metadata['n_fft'], input_onesided=True, boundary=True, scaling='spectrum')
    return signal.T[:metadata['samples']]


def si_sdr(estimate, reference):
    if reference is None:
        return None
    a = estimate - estimate.mean(axis=0)
    b = reference - reference.mean(axis=0)
    energy = np.sum(b*b, axis=0)
    valid = energy > 1e-20
    projection = np.divide(np.sum(a*b,axis=0), energy, out=np.zeros(4), where=valid)*b
    error = np.sum((a-projection)**2, axis=0)
    target = np.sum(projection**2, axis=0)
    valid &= target > 1e-20
    values = np.where(valid, 10*np.log10(np.maximum(target,1e-30)/np.maximum(error,1e-30)), np.nan)
    return {'by_channel_db': values, 'mean_valid_channels_db': float(np.mean(values[valid])) if valid.any() else None,
            'valid_channels': int(valid.sum()), 'definition': 'zero-mean per-channel projection; arithmetic mean across valid FOA channels'}


def run_audio(payload, config, progress=None):
    bundle, metadata, reference = prepare_zip(payload, config)
    result = run_neural({**config, 'bundle': bundle}, progress)
    result['audio'] = metadata
    signals = {}
    for name in ('linear','neural'):
        spectra = result['output'][name+'_real'] + 1j*result['output'][name+'_imag']
        signals[name] = inverse_spectra(spectra, metadata)
        result['quality'][name]['si_sdr'] = si_sdr(signals[name], reference)
    if reference is not None:
        signals['reference'] = reference
    peak = max(float(np.max(abs(a))) for a in signals.values())
    gain = min(1., .95/peak) if peak > 0 else 1.
    metadata['shared_export_gain'] = gain
    metadata['unscaled_output_peak'] = peak
    metadata['output_note'] = 'All WAVs share one gain. ACN W,Y,Z,X. N3D and converted SN3D versions. Decode FOA before loudspeaker output.'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, signal in signals.items():
            archive.writestr(f'{name}_FOA_ACN_N3D.wav', wav_bytes(metadata['sample_rate_hz'], signal*gain))
            archive.writestr(f'{name}_FOA_ACN_SN3D.wav', wav_bytes(metadata['sample_rate_hz'], signal*gain/np.sqrt([1,3,3,3])))
        archive.writestr('result.json', json.dumps(to_jsonable(result), ensure_ascii=False, allow_nan=False, indent=2))
        archive.writestr('READ-ME.txt', 'Independent ADEPS equation test with a small synthetic MLP, not the authors model.\n'
                          'Compare linear and neural files with the SAME decoder and playback level.\n'
                          'ACN channel order: W, Y, Z, X. Select N3D or SN3D to match your decoder.\n'
                          'These four channels are Ambisonics coefficients, not four loudspeaker feeds.\n'
                          'No binaural HRTF rendering or speaker routing is included.\n'
                          f'Shared WAV export gain: {gain:.12g}. Raw complex spectra remain in result.json.\n')
    return result, output.getvalue()


def example_zip():
    """A reproducible dry plane-wave oscillator example, not a room recording."""
    rate, count = 16000, 12800
    t = np.arange(count)/rate
    directions = np.array([[.8,.45,.3],[-.4,.7,-.2]])
    directions /= np.linalg.norm(directions,axis=1)[:,None]
    waves = np.stack([.18*np.sin(2*np.pi*(310*t+80*t*t)), .12*np.sin(2*np.pi*733*t)])
    waves *= np.sin(np.pi*np.arange(count)/(count-1))**2
    q = 6
    theta = np.arange(q)*np.pi*(3-np.sqrt(5)); z = 1-2*(np.arange(q)+.5)/q
    positions = .06*np.c_[np.sqrt(1-z*z)*np.cos(theta),np.sqrt(1-z*z)*np.sin(theta),z]
    f = np.fft.rfftfreq(count,1/rate)
    transfer = np.exp(2j*np.pi*f[:,None,None]*(positions@directions.T)[None,:,:]/343)
    spectra = np.einsum('fqs,sf->fq',transfer,np.fft.rfft(waves,axis=1))
    microphones = np.fft.irfft(spectra, n=count, axis=0)
    reference = (real_n3d(1,directions).T@waves).T
    manifest = {'schema':'adeps-test-array-audio/1', 'sh_ordering':'ACN', 'sh_normalization':'N3D',
                'array_model':'freefield-omnidirectional', 'microphone_positions_m':positions.tolist(),
                'analysis_sample_rate_hz':16000,'n_fft':256,'hop':128,
                'provenance':'Synthetic dry oscillator plane waves, FFT periodic propagation, no room or hardware measurement'}
    output = io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('array.json',json.dumps(manifest,indent=2))
        archive.writestr('microphones.wav',wav_bytes(rate,microphones))
        archive.writestr('reference.wav',wav_bytes(rate,reference))
    return output.getvalue()
