"""Freeze validation-only inference settings, then run an independent test.

No paper scores are used as optimization targets. Final-test seeds are never
used by the trainer or tuning. Result files must not already exist.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from capture import encode
from neural import quality
from neural_audio import wav_bytes
from numerics import to_jsonable
from spatial import synthetic, run_spatial, run_spatial_source
from spatial_model import SpatialModel


def configurations(start):
    rows = []
    for q, radius in ((4, .045), (6, .06), (12, .09), (19, .049)):
        for snr in (15, 40):
            for scene in ('speech_like', 'music', 'noise', 'transient'):
                rows.append({'microphones': q, 'radius_m': radius, 'snr_db': snr,
                             'scene': scene, 'regularization': .001, 'data_seed': start+len(rows),
                             'mismatch': q == 19, 'coplanar': False})
    for q in (4, 6):
        for mismatch in (False, True):
            rows.append({'microphones': q, 'radius_m': .06, 'snr_db': 30,
                         'scene': 'speech_like', 'regularization': .001, 'data_seed': start+len(rows),
                         'mismatch': mismatch, 'coplanar': True})
    return rows


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(to_jsonable(value), f, indent=2, ensure_ascii=False, allow_nan=False)


def tune(model, path):
    candidates = {(blend, consistency): [] for blend in (.25, .5, .75, 1.) for consistency in (0., .15, .5)}
    linear_rows = {r: [] for r in (1e-5, 1e-4, .001, .01, .1)}
    baseline = []
    configs = configurations(25000)
    for index, config in enumerate(configs):
        d = synthetic(config)
        linear, e, _ = encode(d['V'], d['p'], .001)
        predicted = model.predict(linear, e@d['V'], d['frequencies'])
        baseline.append(quality(linear[:, :4], d['reference'])['nrmse_db'])
        for (blend, consistency), errors in candidates.items():
            estimate = linear + blend*(predicted-linear)
            estimate += consistency*(e@(d['p']-d['V']@estimate))
            errors.append(quality(estimate[:, :4], d['reference'])['nrmse_db'])
        for reg, errors in linear_rows.items():
            a, _, _ = encode(d['V'], d['p'], reg)
            errors.append(quality(a[:, :4], d['reference'])['nrmse_db'])
        print(f'validation {index+1}/{len(configs)}', flush=True)
    # Bypass is reported as a baseline, not disguised as a learned checkpoint.
    selected = min(candidates, key=lambda key: np.mean(candidates[key]))
    linear_reg = min(linear_rows, key=lambda key: np.mean(linear_rows[key]))
    record = {'schema': 'adeps-test-spatial-tuning/1', 'status': 'frozen-validation-only',
              'model_sha256': model.card['weights_sha256'], 'blend': selected[0], 'consistency': selected[1],
              'selected_linear_regularization': linear_reg, 'seed_range': [25000, 25000+len(configs)-1],
              'objective': 'Mean paired-scene FOA complex NRMSE dB; references used only for offline validation selection.',
              'validation_baseline_db': float(np.mean(baseline)),
              'validation_selected_db': float(np.mean(candidates[selected])),
              'candidates': [{'blend': key[0], 'consistency': key[1], 'mean_nrmse_db': float(np.mean(values))}
                             for key, values in candidates.items()],
              'linear_candidates': [{'regularization': key, 'mean_nrmse_db': float(np.mean(values))}
                                     for key, values in linear_rows.items()],
              'configuration_sha256': hashlib.sha256(json.dumps(configs, sort_keys=True).encode()).hexdigest(),
              'test_data_used': False}
    write_new(path, record)
    return record


def evaluate(model, tuning_path, output, include_legacy):
    tuning = json.loads(tuning_path.read_text())
    if tuning['model_sha256'] != model.card['weights_sha256']:
        raise ValueError('Frozen tuning belongs to another model; tune on validation again before opening a new test')
    cases = []
    configs = configurations(90000)
    split = {'training': model.card['training']['training_scene_seeds'],
             'model_validation': model.card['training']['validation_scene_seeds'],
             'inference_validation': tuning['seed_range'], 'final_test': [90000, 90000+len(configs)-1],
             'audio_test': [91000, 91002]}
    ranges = list(split.values())
    if any(max(a[0], b[0]) <= min(a[1], b[1]) for i, a in enumerate(ranges) for b in ranges[i+1:]):
        raise ValueError('Training, validation and final-test seed ranges must not overlap')
    split['all_seed_ranges_disjoint'] = True
    for index, config in enumerate(configs):
        result = run_spatial({**config, 'include_legacy': include_legacy and index in (0, 8)}, model=model, tuning=tuning)
        a, b = result['quality']['linear'], result['quality']['enhanced']
        data = synthetic(config)
        stronger, _, _ = encode(data['V'], data['p'], tuning['selected_linear_regularization'])
        stronger_score = quality(stronger[:, :4], data['reference'])['nrmse_db']
        cases.append({'id': f'test-{index+1:02}', **config, 'seed': config['data_seed'],
                      'linear_nrmse_db': a['nrmse_db'], 'enhanced_nrmse_db': b['nrmse_db'],
                      'improvement_db': a['nrmse_db']-b['nrmse_db'],
                      'linear_coherence': a['coherence'], 'enhanced_coherence': b['coherence'],
                      'tuned_linear_nrmse_db': stronger_score,
                      'improvement_over_tuned_linear_db': stronger_score-b['nrmse_db'],
                      'elapsed_seconds': result['diagnostics']['elapsed_seconds'],
                      'input_sha256': result['input_sha256'],
                      'legacy': result['quality'].get('legacy')})
        print(json.dumps({'stage': 'test', 'case': index+1, 'delta_db': cases[-1]['improvement_db']}), flush=True)
    delta = np.array([row['improvement_db'] for row in cases])
    rng = np.random.default_rng(70137)
    boot = rng.choice(delta, (4000, len(delta)), replace=True).mean(axis=1)
    audio_cases = []
    for index, (kind, rate, duration) in enumerate((('harmonic', 16000, .4), ('burst', 16000, .4), ('chirp', 48000, .1))):
        t = np.arange(int(rate*(duration+.1)))/rate
        if kind == 'harmonic':
            signal = .1*sum(np.sin(2*np.pi*(137*k*t + .4*k*t*t))/k for k in range(1, 7))
        elif kind == 'burst':
            signal = .15*np.sin(2*np.pi*731*t)*np.exp(-60*np.maximum(0, t-.04))*(t>=.04)
        else:
            signal = .12*np.sin(2*np.pi*(50*t+95000*t*t))
        signal *= np.sin(np.pi*np.minimum(t/duration, 1.))**2
        result, _ = run_spatial_source(wav_bytes(rate, signal), {'microphones': 6, 'snr_db': 25,
             'data_seed': 91000+index, 'duration_seconds': duration, 'analysis_sample_rate_hz': rate}, model=model, tuning=tuning)
        audio_cases.append({'id': kind, 'sample_rate_hz': rate, 'duration_seconds': duration,
                            'seed': 91000+index, 'input_sha256': result['input_sha256'],
                            'quality': result['quality'], 'provenance': result['provenance']})
    report = {'schema': 'adeps-test-spatial-benchmark/1', 'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'model_sha256': model.card['weights_sha256'], 'tuning': tuning,
              'split': split,
              'summary': {'cases': len(cases), 'win_count': int(np.sum(delta>1e-6)),
                          'loss_count': int(np.sum(delta < -1e-6)), 'tie_count': int(np.sum(abs(delta)<=1e-6)),
                          'mean_improvement_db': float(delta.mean()), 'median_improvement_db': float(np.median(delta)),
                          'bootstrap_95ci_db': np.quantile(boot, [.025, .975]),
                          'mean_improvement_over_tuned_linear_db': float(np.mean([c['improvement_over_tuned_linear_db'] for c in cases]))},
              'cases': cases, 'audio_cases': audio_cases,
              'paper': {'comparable': False, 'reference_url': 'https://arxiv.org/html/2608.24558v3',
                        'reason': 'Different independent synthetic dataset, generative process, model, arrays and aggregation. '
                                  'Published ADEPS scores are not same-input baselines. Official checkpoint unavailable.',
                        'table1_6mic_reported': {'linear_si_sdr_db': 9.26, 'adeps_si_sdr_db': 16.20},
                        'table2_6mic_reported': {'linear_si_sdr_db': 9.09, 'adeps_si_sdr_db': 12.67}},
              'limits': ['No venue recording or measured array response in this benchmark.',
                         '19-capsule test is a virtual geometry, not a ZM-1 calibration.',
                         'Same predefined test suite for every case; bad cases are retained.',
                         'Bootstrap resamples these synthetic scenes; not confidence for arbitrary real rooms.',
                         'FOA complex NRMSE and coherence are paired here. Spectral MAE is our explicitly defined metric.',
                         'Waveform SI-SDR only for aligned synthetic FOA reference; no audio scores invented for complex-bin scenes.']}
    write_new(output, report)
    return report['summary']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('tune', 'evaluate'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--legacy', action='store_true')
    args = parser.parse_args()
    model = SpatialModel()
    tuning_file = ROOT/'public/models/spatial-tuning.json'
    if args.operation == 'tune':
        result = tune(model, args.output or tuning_file)
    else:
        result = evaluate(model, tuning_file, args.output or ROOT/'public/models/spatial-benchmark.json', args.legacy)
    print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))
