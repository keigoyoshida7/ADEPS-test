"""Package fixed FOA reconstructions for one shared Max speaker decoder.

No inference, new scene rendering, optimization, scoring, or benchmark edits.
Scene zero preserves the already published WAV bytes. The optional montage
uses every sealed test scene in order, a shared fade/gap, and one global gain.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_plus as saved

METHOD_IDS = ('reference', *saved.METHOD_IDS)
MAX_FILES = ('ADEPS_Method_Comparison.maxpat', 'method-comparison-entry.js', 'method-comparison-controller.js',
             'method-comparison-server.js', 'method-comparison-bank.js',
             'method-comparison-buffer.js', 'README_COMPARISON.md',
             'osc-codec.js', 'package.json')
RATE, CLIP_SAMPLES, GAP_SAMPLES, FADE_SAMPLES = 16000, 3968, 2400, 80


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def dump(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def checked_file(path, expected):
    payload = Path(path).read_bytes()
    if not isinstance(expected, str) or digest(payload) != expected:
        raise ValueError(f'SHA-256 mismatch: {Path(path).name}')
    return payload


def verify_packaging_seal(work, report, selection):
    """Verify the recorded seal, without re-reading unrelated development data.

    Every consumed final input/estimate is checked separately below. This
    packaging step does not re-audit the pre-test source/development files.
    """
    lock_path = Path(work)/'selection-lock.json'
    lock = saved.read_json(lock_path)
    lock_sha = saved.sha(lock_path)
    if (lock.get('schema') != 'adeps-plus-selection-lock/1'
            or lock.get('status') != 'sealed_before_final_test_rendering_or_inference'
            or report['provenance']['lock_sha256'] != lock_sha
            or selection != lock['selection'] or selection != report['selection']
            or tuple(lock['method_ids']) != saved.METHOD_IDS
            or any(report['provenance'][key] != lock[key]
                   for key in ('source_sha256', 'input_sha256'))):
        raise ValueError('Benchmark, selection and pre-test seal identities differ.')
    return lock_sha


def speaker_decoder(layout, layout_sha):
    """Exactly the UI angular ACN/N3D decoder, not room pressure correction."""
    if (layout.get('schema') != 'adeps-test-speaker-layout/1'
            or layout.get('units') != 'metres'
            or layout['coordinate_system']['axes'] != {'x': 'right', 'y': 'front', 'z': 'up'}
            or [s['id'] for s in layout['speakers']] != list(range(1, 13))):
        raise ValueError('Expected the saved 12-speaker ID order and raw metre axes.')
    positions = np.asarray([s['position_m'] for s in layout['speakers']], dtype=float)
    rotation = np.asarray(layout['coordinate_system']['foa_from_raw_matrix'], dtype=float)
    expected_rotation = np.array([[0., 1., 0.], [-1., 0., 0.], [0., 0., 1.]])
    if positions.shape != (12, 3) or not np.isfinite(positions).all() or not np.array_equal(rotation, expected_rotation):
        raise ValueError('Invalid saved positions or front/left/up rotation.')
    listener = np.array([0., 0., 1.2])
    offsets = (positions - listener) @ rotation.T
    distances = np.linalg.norm(offsets, axis=1)
    if np.any(distances <= 1e-12):
        raise ValueError('A speaker coincides with the assumed listener.')
    directions = offsets / distances[:, None]
    y = np.column_stack((np.ones(12), np.sqrt(3)*directions[:, 1],
                         np.sqrt(3)*directions[:, 2], np.sqrt(3)*directions[:, 0]))
    gram = y.T @ y
    matrix = np.linalg.solve(gram + .001*np.eye(4), y.T).T
    eigenvalues = np.linalg.eigvalsh(gram)
    rank = int(np.count_nonzero(eigenvalues > eigenvalues[-1]*1e-10))
    return {'matrix': matrix.tolist(), 'normalization': 'N3D', 'ordering': 'ACN',
            'channel_order': ['W', 'Y', 'Z', 'X'], 'regularization': .001,
            'listener_m': listener.tolist(), 'listener_is_assumed': True,
            'listener_axes': 'Raw saved X right, Y front, Z up',
            'raw_to_foa_matrix': rotation.tolist(), 'directions_foa': directions.tolist(),
            'formula': 'D=Y(Y^T Y+0.001 I)^-1; feeds=D*a; Y=[1,sqrt(3)dy,sqrt(3)dz,sqrt(3)dx]',
            'rank': rank, 'condition_number': float(np.sqrt(eigenvalues[-1]/eigenvalues[0])) if rank == 4 else None,
            'layout': {'file': 'reference/speaker-layout-12ch.json', 'sha256': layout_sha,
                       'source': deepcopy(layout['source']), 'speakers': deepcopy(layout['speakers']),
                       'verification': deepcopy(layout['verification']),
                       'channel_order_note': deepcopy(layout['channel_order_note'])},
            'negative_gain': 'Polarity inversion; do not replace signed coefficients with magnitudes.',
            'scope': 'Angular mode matching only; no distance/delay compensation, measured room correction, automatic output protection or physical routing.'}


def waveform(value):
    foa = saved.real_wave_foa(value)
    result = saved.synthesize_spectra(foa, n_fft=512, hop=128)[:, 256:-256].T
    if result.shape != (CLIP_SAMPLES, 4) or not np.isfinite(result).all():
        raise ValueError('Saved coefficients must yield the common finite 3968-sample FOA crop.')
    return result


def read_foa_wav(payload, samples):
    rate, audio = wavfile.read(io.BytesIO(payload))
    if rate != RATE or audio.dtype != np.float32 or audio.shape != (samples, 4) or not np.isfinite(audio).all():
        raise ValueError('Bank WAV must be finite FLOAT32, 16 kHz, four synchronous FOA channels.')
    return audio


def check_published_wavs(example, payloads, waves):
    """The scene-zero bank is byte-preserving; reject repacked/mismatched audio."""
    gain = example['shared_gain']
    audio = example['audio']
    if (type(gain) not in (int, float) or not np.isfinite(gain) or gain <= 0
            or audio['shared_gain'] != gain or audio['sample_rate_hz'] != RATE
            or audio['samples'] != CLIP_SAMPLES or audio['foa_channels'] != ['W', 'Y', 'Z', 'X']
            or audio['sh_normalization'] != 'N3D' or set(waves) != set(METHOD_IDS)):
        raise ValueError('Published example gain, convention, or bank dimensions differ.')
    peak = max(max(float(abs(a).max()), float(abs(a @ saved.PREVIEW_MATRIX.T).max()))
               for a in waves.values())
    expected_gain = .95/peak if peak > 0 else 1.
    if not np.isclose(gain, expected_gain, rtol=1e-12, atol=0):
        raise ValueError('Published gain is not the common all-method gain.')
    for identifier in METHOD_IDS:
        name = f'foa/{identifier}_FOA_ACN_N3D.wav'
        if name not in payloads or not np.array_equal(read_foa_wav(payloads[name], CLIP_SAMPLES),
                                                     (waves[identifier]*gain).astype(np.float32)):
            raise ValueError(f'Published FOA differs from the sealed reconstruction: {identifier}')
    return float(gain)


def collection_sha(timeline):
    identities = [{'scene_id': row['scene_id'], 'input_sha256': row['input_sha256']} for row in timeline]
    return digest(json.dumps(identities, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def montage(wave_sets, scene_records, decoder):
    """One gain for every method/scene; no per-scene loudness normalization."""
    if not wave_sets or len(wave_sets) != len(scene_records):
        raise ValueError('Montage scenes and identities must match.')
    samples = len(wave_sets)*CLIP_SAMPLES + (len(wave_sets)-1)*GAP_SAMPLES
    bank = {key: np.zeros((samples, 4), dtype=np.float64) for key in METHOD_IDS}
    fade = np.ones(CLIP_SAMPLES)
    fade[:FADE_SAMPLES] = np.linspace(0., 1., FADE_SAMPLES)
    fade[-FADE_SAMPLES:] = np.linspace(1., 0., FADE_SAMPLES)
    timeline = []
    for index, (waves, scene) in enumerate(zip(wave_sets, scene_records)):
        if set(waves) != set(METHOD_IDS):
            raise ValueError('Every montage scene must contain reference and all nine methods.')
        start = index*(CLIP_SAMPLES + GAP_SAMPLES)
        for key in METHOD_IDS:
            a = np.asarray(waves[key], dtype=float)
            if a.shape != (CLIP_SAMPLES, 4) or not np.isfinite(a).all():
                raise ValueError('Invalid montage waveform.')
            bank[key][start:start+CLIP_SAMPLES] = a*fade[:, None]
        timeline.append({**scene, 'start_sample': start, 'end_sample_exclusive': start+CLIP_SAMPLES,
                         'start_seconds': start/RATE, 'duration_seconds': CLIP_SAMPLES/RATE})
    d = np.asarray(decoder['matrix'])
    peak = max(max(float(abs(a).max()), float(abs(a @ d.T).max())) for a in bank.values())
    gain = .95/peak if peak > 0 else 1.
    if not np.isfinite(gain) or gain <= 0:
        raise ValueError('Invalid montage common gain.')
    payloads = {f'foa/{key}_FOA_ACN_N3D.wav': saved.wav_bytes(RATE, a*gain) for key, a in bank.items()}
    return payloads, {'samples': samples, 'shared_gain': gain, 'input_sha256': collection_sha(timeline),
        'input_sha256_definition': 'SHA-256 of ordered scene_id/input_sha256 objects, sorted-key compact UTF-8 JSON. Each input hash contains only the physical observation, not reference or estimates.',
        'timeline': timeline, 'gap_samples': GAP_SAMPLES, 'gap_seconds': GAP_SAMPLES/RATE,
        'fade_samples_each_edge': FADE_SAMPLES, 'fade_seconds_each_edge': FADE_SAMPLES/RATE,
        'fade': 'Linear 0→1 over first 80 samples and 1→0 over last 80; identical for all methods and scenes.',
        'gain_definition': 'One 0.95/global_peak scalar over all faded scenes, all methods plus reference, all FOA samples and their common 12-speaker decode; already applied. No per-scene or per-method normalization.',
        'peak_before_gain': peak}


def bank_manifest(identifier, details, labels, audio_payloads, decoder, provenance, attribution):
    methods = []
    max_foa = max_speaker = 0.
    for key in METHOD_IDS:
        filename = f'foa/{key}_FOA_ACN_N3D.wav'
        audio = read_foa_wav(audio_payloads[filename], details['samples'])
        max_foa = max(max_foa, float(abs(audio).max()))
        max_speaker = max(max_speaker, float(abs(audio @ np.asarray(decoder['matrix']).T).max()))
        methods.append({'id': key, 'label': labels[key][1], 'label_jp': labels[key][0],
                        'label_en': labels[key][1], 'file': filename, 'sha256': digest(audio_payloads[filename])})
    return {'schema': 'adeps-max-method-bank/1', 'bank_id': identifier,
        'sample_rate_hz': RATE, 'samples': details['samples'], 'duration_seconds': details['samples']/RATE,
        'channel_order': ['W', 'Y', 'Z', 'X'], 'ordering': 'ACN', 'normalization': 'N3D',
        'encoding': 'FLOAT32', 'shared_gain': details['shared_gain'], 'shared_gain_applied': True,
        'input_sha256': details['input_sha256'], 'methods': methods, 'decoder': decoder,
        'audio': details, 'attribution': attribution, 'provenance': provenance,
        'peak_after_gain': {'foa': max_foa, 'common_12_speaker_decode': max_speaker},
        'recommended_extra_attenuation': min(1., .95/max(max_foa, max_speaker)) if max(max_foa, max_speaker) else 1.,
        'default_method': 'linear_tuned', 'default_on_method': 'plus', 'default_off_method': 'linear_tuned',
        'limits_jp': ['計算済み音声の同期比較です。Max上で新しい音声のADEPS推論は行いません。',
                      '各場面は0.248秒の短片です。モンタージュも長い発話を連続推定したものではありません。',
                      'FOAの4chはスピーカー番号ではありません。共通デコーダを一度だけ通します。',
                      '保存IDと実機の出力経路は別です。11/12の過去記録との差は現地で照合します。'],
        'limits_en': ['Synchronized playback of saved reconstructions, not live ADEPS inference.',
                      'Each scene is a 0.248-second crop; a montage does not establish continuous long-form inference.',
                      'Four FOA channels are not speaker IDs; apply the common decoder exactly once.',
                      'Saved IDs do not establish physical output routes; resolve the earlier 11/12 discrepancy on site.']}


def zip_bytes(manifest, payloads):
    if 'max-comparison.json' in payloads or any(Path(p).is_absolute() or '..' in Path(p).parts for p in payloads):
        raise ValueError('Unsafe or duplicate bank manifest path.')
    record = deepcopy(manifest)
    record['files'] = {name: {'sha256': digest(payload), 'bytes': len(payload)} for name, payload in sorted(payloads.items())}
    files = {**payloads, 'max-comparison.json': dump(record)}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    result = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        if len(archive.namelist()) != len(files) or any(archive.read(name) != value for name, value in files.items()):
            raise ValueError('ZIP readback failed.')
    return result


def read_montage_scenes(work, report, lock_sha):
    waves, identities, credits = [], [], []
    common_credit_files = None
    for index, (source, declared) in enumerate(zip(report['scenes'], report['provenance']['test_inputs']['cases'])):
        if declared['index'] != index or declared['scene_id'] != source['id'] or declared['cluster_id'] != source['cluster_id']:
            raise ValueError('Sealed montage scene ordering mismatch.')
        cache = work/f'cache/test/{index:04d}.npz'
        checked_file(cache, declared['sha256'])
        with np.load(cache, allow_pickle=False) as z:
            data = {k: z[k].copy() for k in ('reference', 'p', 'V', 'frequencies')}
            metadata = json.loads(str(z['metadata_json']))
        if metadata['id'] != source['id'] or metadata['scene_index'] != index or metadata['split'] != 'test':
            raise ValueError('Montage cache metadata mismatch.')
        if not np.array_equal(data['frequencies'], saved.FREQUENCIES):
            raise ValueError('Montage frequency grid mismatch.')
        one = {'reference': waveform(data['reference'])}
        case_shas = {}
        for key in saved.METHOD_IDS:
            case_path = work/f'final/{index:04d}/{key}.json'
            case = saved.read_json(case_path)
            estimate_path = case_path.with_suffix('.npz')
            if (case.get('schema') != 'adeps-plus-case/1' or case['outcome'] != 'completed'
                    or case['method'] != key or case['scene'] != index or case['scene_id'] != source['id']
                    or case['cluster_id'] != source['cluster_id'] or case['input_sha256'] != declared['sha256']
                    or case['selection_lock_sha256'] != lock_sha or case['metrics'] != source['metrics'][key]
                    or case['curves'] != source['curves'][key]):
                raise ValueError('Incomplete or mismatched saved montage estimate.')
            checked_file(estimate_path, case['estimate_sha256'])
            with np.load(estimate_path, allow_pickle=False) as z:
                value = z['estimate']
                if value.shape != (257, 36, 32) or not np.isfinite(value).all():
                    raise ValueError('Invalid saved montage coefficients.')
                one[key] = waveform(value)
            case_shas[key] = {'record_sha256': saved.sha(case_path), 'estimate_sha256': case['estimate_sha256']}
        credit, _, _, credit_files = saved.attribution(work, metadata)
        if common_credit_files is not None and credit_files != common_credit_files:
            raise ValueError('Montage dataset attribution documents differ.')
        common_credit_files = credit_files
        credits.append({'scene_id': source['id'], **credit})
        identities.append({'scene_id': source['id'], 'scene_index': index, 'cluster_id': source['cluster_id'],
                           'input_sha256': saved.canonical_observation_sha(data), 'input_file_sha256': declared['sha256'],
                           'source_files': credit['files'], 'source_speakers': credit['speakers'], 'cases': case_shas})
        waves.append(one)
        print(f'Validated saved montage scene {index+1}/32', file=sys.stderr, flush=True)
    if len(waves) != 32:
        raise ValueError('Montage requires all 32 scenes, without selection or omissions.')
    return waves, identities, credits, common_credit_files


def export(work, destination, *, include_montage=True):
    work, destination = Path(work), Path(destination)
    report_path = work/'benchmark.json'
    report = saved.read_json(report_path)
    saved.validate_benchmark(report)
    report_sha = saved.sha(report_path)
    selection = saved.read_json(work/'selection.json')
    print('Verifying the recorded seal and consumed final artifacts…', file=sys.stderr, flush=True)
    lock_sha = verify_packaging_seal(work, report, selection)
    print('Recorded seal verified. Packaging the saved example…', file=sys.stderr, flush=True)
    original_directory = ROOT/'public/models'
    if saved.sha(original_directory/'plus-benchmark.json') != report_sha:
        raise ValueError('Published benchmark differs from the sealed source.')
    example = saved.read_json(original_directory/'plus-example.json')
    saved.validate_example(example)
    if example['provenance']['benchmark_sha256'] != report_sha or example['provenance']['selection_lock_sha256'] != lock_sha:
        raise ValueError('Published example provenance differs from the sealed benchmark.')
    data, metadata, arrays, _, cache_sha = saved.read_example_inputs(work, report, lock_sha)
    if example['input_file_sha256'] != cache_sha or example['input_sha256'] != saved.canonical_observation_sha(data):
        raise ValueError('Published example observation differs from its sealed input.')
    declared = report['provenance']['test_inputs']['cases']
    if len(declared) != 32 or declared[0]['sha256'] != cache_sha:
        raise ValueError('Saved scene-zero input is absent from the complete test lock.')
    source_archive = original_directory/'plus-example-audio.zip'
    with zipfile.ZipFile(source_archive) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError('Duplicate published ZIP entries.')
        payloads = {f'foa/{key}_FOA_ACN_N3D.wav': archive.read(f'foa/{key}_FOA_ACN_N3D.wav') for key in METHOD_IDS}
    waves = {'reference': waveform(data['reference']), **{key: waveform(a) for key, a in arrays.items()}}
    gain = check_published_wavs(example, payloads, waves)
    credit, _, _, credit_files = saved.attribution(work, metadata)
    layout_path = ROOT/'public/reference/speaker-layout-12ch.json'
    layout_bytes = layout_path.read_bytes()
    decoder = speaker_decoder(json.loads(layout_bytes), digest(layout_bytes))
    shared_files = {'reference/speaker-layout-12ch.json': layout_bytes, **credit_files}
    for filename in MAX_FILES:
        shared_files[f'max/{filename}'] = (ROOT/'max'/filename).read_bytes()
    shared_files['README.txt'] = (
        'ADEPS-test / saved reconstruction method comparison\n'
        'Open max/ADEPS_Method_Comparison.maxpat, then choose the root max-comparison.json.\n'
        'FOA WAVs are already gain-scaled FLOAT32 ACN/N3D W,Y,Z,X. Do not apply shared_gain again.\n'
        'Use the shared 12x4 decoder exactly once. Stereo cardioid and KU100 metric audio are not included.\n'
        'All methods use the same synthetic inputs and transport; this is not real-time inference.\n'
        'The example is 0.248 seconds. Montage scenes retain the same short duration, with declared fades and gaps.\n'
        'Open does not authorize automatic audio; start, master gain and physical routing are manual.\n'
        'Read max/README_COMPARISON.md and the manifest, including the saved channel 11/12 discrepancy.\n'
        'VCTK attribution and original license documents are included. No original corpus, model weights or new scores.\n'
    ).encode('utf-8')
    labels = {'reference': ('参照の合成音場', 'Reference synthetic field'),
              **{m['id']: (m['label_jp'], m['label_en']) for m in report['methods']}}
    provenance = {'benchmark_sha256': report_sha, 'selection_lock_sha256': lock_sha,
                  'source_example_sha256': saved.sha(original_directory/'plus-example.json'),
                  'source_audio_archive_sha256': saved.sha(source_archive),
                  'exporter_sha256': saved.sha(Path(__file__)), 'saved_estimates_only': True,
                  'new_inference': False, 'metrics_unchanged': True,
                  'verification_scope': 'Recorded selection-lock identity, benchmark identity, and every consumed final input/estimate SHA-256 verified. Pre-test source and development files are not re-audited during this audio packaging step.'}
    details = {'samples': CLIP_SAMPLES, 'shared_gain': gain, 'input_sha256': example['input_sha256'],
               'input_sha256_definition': example['input_sha256_definition'], 'scene_id': metadata['id'],
               'timeline': [{'scene_id': metadata['id'], 'scene_index': 0, 'start_sample': 0,
                             'end_sample_exclusive': CLIP_SAMPLES, 'start_seconds': 0., 'duration_seconds': CLIP_SAMPLES/RATE}],
               'fade_samples_each_edge': 0, 'gap_samples': 0,
               'gain_definition': example['audio']['gain_definition'] + ' Already applied; preserve original WAV bytes.'}
    bank = bank_manifest('example', details, labels, payloads, decoder, provenance, credit)
    outputs = {'max-comparison-bank.zip': zip_bytes(bank, {**shared_files, **payloads})}
    banks = [('example', '短い同一場面', 'Single saved scene', 'max-comparison-bank.zip', bank, 1)]
    if include_montage:
        all_waves, identities, credits, documents = read_montage_scenes(work, report, lock_sha)
        audio, info = montage(all_waves, identities, decoder)
        montage_credit = {'title': credit['title'], 'license': credit['license'], 'license_url': credit['license_url'],
                         'source_url': credit['source_url'], 'corpus': credit['corpus'], 'scenes': credits,
                         'changes': credit['changes'] + ' Montage concatenates all 32 fixed test crops in order, using identical 5 ms fades and 150 ms silent gaps, followed by one global gain.'}
        bank = bank_manifest('montage', info, labels, audio, decoder, provenance, montage_credit)
        outputs['max-comparison-montage-bank.zip'] = zip_bytes(bank, {**shared_files, **documents, **audio,
            'timeline.json': dump(info['timeline'])})
        banks.append(('montage', '32場面を順番に聴く', 'All 32 scenes in order', 'max-comparison-montage-bank.zip', bank, 32))
    summary = {'schema': 'adeps-max-comparison/1', 'methods': [
        {'id': key, 'label_jp': labels[key][0], 'label_en': labels[key][1]} for key in METHOD_IDS],
        'normalization': 'N3D', 'channel_order': ['W', 'Y', 'Z', 'X'], 'ordering': 'ACN',
        'banks': [{'id': key, 'title_jp': jp, 'title_en': en, 'archive_url': 'models/'+filename,
                   'duration_seconds': b['duration_seconds'], 'sample_rate_hz': RATE, 'samples': b['samples'],
                   'scenes': count, 'input_sha256': b['input_sha256'], 'shared_gain': b['shared_gain'],
                   'shared_gain_applied': True, 'archive_sha256': digest(outputs[filename]), 'archive_bytes': len(outputs[filename])}
                  for key, jp, en, filename, b, count in banks],
        'provenance': provenance, 'decoder': decoder,
        'limits_jp': bank['limits_jp'], 'limits_en': bank['limits_en']}
    if saved.sha(report_path) != report_sha or saved.sha(original_directory/'plus-benchmark.json') != report_sha:
        raise ValueError('The original benchmark changed during packaging.')
    outputs['max-comparison.json'] = dump(summary)
    destination.mkdir(parents=True, exist_ok=True)
    for filename, payload in outputs.items():
        (destination/filename).write_bytes(payload)
    if any((destination/name).read_bytes() != payload for name, payload in outputs.items()):
        raise ValueError('Published bank readback failed.')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT/'work/plus-v1')
    parser.add_argument('--output', type=Path, default=ROOT/'public/models')
    parser.add_argument('--no-montage', action='store_true')
    args = parser.parse_args()
    result = export(args.work, args.output, include_montage=not args.no_montage)
    print(json.dumps({'banks': result['banks']}, ensure_ascii=False, indent=2))
