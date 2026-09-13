"""Render saved ADEPS+ benchmark values as standalone scientific SVG/PNG figures.

Reads only the completed benchmark JSON. No inputs, model, inference, metric
recomputation or parameter selection. Missing values remain gaps/undefined.
Matplotlib must already be installed; this script never changes the environment.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import tempfile

import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager, pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
IDS = ('linear_default', 'linear_tuned', 'linear_noise', 'adeps_current', 'adeps_tuned',
       'spatial_only', 'consistency_only', 'plus', 'plus_no_denoiser')
CURVES = ('nrmse_db', 'magnitude_spectrum_error_db', 'magnitude_squared_coherence')
METRICS = ('nrmse_db', 'non_dc_nrmse_db', 'speech_band_nrmse_db', 'magnitude_error_db', 'coherence', 'si_sdr_db')
FREQUENCIES = np.arange(257, dtype=float) * 31.25
FREQUENCY_IDS = ('linear_tuned', 'adeps_current', 'adeps_tuned', 'plus', 'plus_no_denoiser')
LABELS = dict(zip(IDS, ('Linear · default', 'Linear · tuned', 'Isotropic Wiener · known SNR',
    'ADEPS · current', 'ADEPS · tuned', 'Spatial covariance', 'Linear + STFT consistency',
    '+ α · denoiser ON', '+ α · denoiser OFF')))
STYLES = {'linear_tuned': ('#aaa', (0, (7, 3)), 1.7), 'adeps_current': ('#ddd', (0, (2, 3)), 1.8),
          'adeps_tuned': ('#aaa', (0, (8, 3, 2, 3)), 1.7), 'plus': ('#fff', '-', 2.1),
          'plus_no_denoiser': ('#ccc', (0, (11, 3, 2, 3, 2, 3)), 1.8)}
PAPER = 'https://arxiv.org/html/2608.24558v3'
PROTOCOL = 'https://github.com/keigoyoshida7/ADEPS-test/blob/main/docs/PLUS_PROTOCOL.md'


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def number(value):
    return value is None or finite(value)


def count(value):
    return type(value) is int and value >= 0


def text(value):
    return isinstance(value, str) and bool(value.strip())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_curves(value):
    require(isinstance(value, dict) and set(value) == set(IDS), 'Require all nine method curves')
    for method in IDS:
        row = value[method]
        require(isinstance(row, dict), 'Invalid method curves')
        for key in CURVES:
            values = row.get(key)
            require(isinstance(values, list) and len(values) == 257 and all(number(v) for v in values), 'Missing/nonfinite curve bins')
            if key != 'nrmse_db':
                require(all(v is None or v >= 0 for v in values), 'Negative magnitude error/coherence')
            if key == 'magnitude_squared_coherence':
                require(all(v is None or v <= 1 for v in values), 'Coherence outside 0..1')


def validate_report(r):
    """Structural/identity validation only: plot stored means and CIs unchanged."""
    require(isinstance(r, dict) and r.get('schema') == 'adeps-plus-benchmark/1' and r.get('status') == 'evaluated',
            'A completed adeps-plus-benchmark/1 report is required')
    c = r.get('conditions')
    expected = {'scenes': 32, 'clusters': 4, 'microphones': 6, 'radius_m': .06, 'snr_db': 50,
                'sample_rate_hz': 16000, 'geometry': 'sphere', 'source_counts': [1, 2], 'matched_order': 5,
                'evaluated_audio_samples': 3968, 'evaluated_audio_seconds': .248}
    require(isinstance(c, dict) and all(c.get(k) == v for k, v in expected.items()), 'Report conditions differ from this figure protocol')
    require(isinstance(r.get('frequencies_hz'), list) and r['frequencies_hz'] == FREQUENCIES.tolist(), 'Require all 257 bins including DC')
    methods = r.get('methods')
    require(isinstance(methods, list) and all(isinstance(m, dict) for m in methods)
            and tuple(m.get('id') for m in methods) == IDS, 'Require all nine methods in their saved order')
    for m in methods:
        require(text(m.get('label_en')) and number(m.get('mean_nrmse_db')) and 'mean_nrmse_db' in m, 'Missing method label/mean')
        require(count(m.get('completed')) and count(m.get('failed')) and m['completed'] + m['failed'] == 32, 'Incomplete per-method evaluation')
    scenes = r.get('scenes')
    require(isinstance(scenes, list) and len(scenes) == 32 and all(isinstance(s, dict) and text(s.get('id')) and text(s.get('cluster_id')) for s in scenes), 'Require 32 named scenes')
    require(len({s['id'] for s in scenes}) == 32 and sorted(Counter(s['cluster_id'] for s in scenes).values()) == [8] * 4, 'Invalid scene/cluster inventory')
    pairs = {}
    for s in scenes:
        pair = s.get('speaker_pair')
        require(isinstance(pair, list) and len(pair) == 2 and all(text(speaker) for speaker in pair)
                and len(set(pair)) == 2 and type(s.get('source_count')) is int and s['source_count'] in (1, 2), 'Invalid speaker/source inventory')
        pairs.setdefault(s['cluster_id'], sorted(pair))
        require(pairs[s['cluster_id']] == sorted(pair), 'Speaker pair changed inside a cluster')
        require(isinstance(s.get('metrics'), dict) and set(s['metrics']) == set(IDS)
                and isinstance(s.get('outcomes'), dict) and set(s['outcomes']) == set(IDS), 'Incomplete scene methods')
        for method in IDS:
            values = s['metrics'][method]
            require(isinstance(values, dict) and all(key in values and number(values[key]) for key in METRICS), 'Invalid saved scene metrics')
            require(s['outcomes'][method] in ('completed', 'failed'), 'Missing saved outcome')
        validate_curves(s.get('curves'))
    require(len({speaker for pair in pairs.values() for speaker in pair}) == 8, 'Require eight distinct held-out speakers')
    for m in methods:
        require(sum(s['outcomes'][m['id']] == 'completed' for s in scenes) == m['completed'], 'Method completion count differs from saved scenes')
    validate_curves(r.get('curves'))
    comparisons = r.get('comparisons')
    require(isinstance(comparisons, list) and len(comparisons) == 8 and all(isinstance(row, dict) for row in comparisons), 'Require all eight stored comparisons')
    require({row.get('baseline') for row in comparisons} == set(IDS) - {'plus'}, 'Missing/duplicate comparison baseline')
    for row in comparisons:
        require(row.get('candidate') == 'plus' and row.get('confidence_level') == .975 and row.get('count') == 32, 'Comparison scope differs')
        require(all(key in row and number(row[key]) for key in ('mean_gain_db', 'ci_low_db', 'ci_high_db')), 'Invalid saved mean/CI')
        low, high = row['ci_low_db'], row['ci_high_db']
        require((low is None) == (high is None) and (low is None or low <= high), 'Invalid confidence interval')
        require(row['mean_gain_db'] is not None or low is None, 'Undefined comparison cannot have a finite CI')
        require(all(count(row.get(k)) for k in ('wins', 'losses', 'ties', 'invalid'))
                and sum(row[k] for k in ('wins', 'losses', 'ties', 'invalid')) == 32, 'Incomplete paired outcomes')
        require(row.get('clusters') == sorted({s['cluster_id'] for s in scenes}), 'CI cluster identifiers differ')
    require(isinstance(r.get('provenance'), dict), 'Missing report provenance')


def read_report(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    payload = Path(path).read_bytes()
    report = json.loads(payload, object_pairs_hook=unique, parse_constant=invalid)
    validate_report(report)
    return report, hashlib.sha256(payload).hexdigest()


def choose_font():
    available = {item.name for item in font_manager.fontManager.ttflist}
    return next((name for name in ('YuMincho', 'Yu Mincho', '游明朝', 'DejaVu Serif') if name in available), 'serif')


def style(font):
    return {'font.family': font, 'font.size': 11, 'text.color': '#eee', 'axes.labelcolor': '#ddd',
            'axes.edgecolor': '#777', 'axes.facecolor': '#080808', 'figure.facecolor': '#080808',
            'savefig.facecolor': '#080808', 'xtick.color': '#bbb', 'ytick.color': '#ddd',
            'axes.spines.top': False, 'axes.spines.right': False, 'axes.titleweight': 'normal',
            'grid.color': '#444', 'grid.linewidth': .6, 'grid.alpha': .6, 'axes.unicode_minus': True,
            'svg.fonttype': 'path', 'svg.hashsalt': 'adeps-plus-results-v1'}


def footnotes(fig, digest, font, *, frequency):
    note = ('Positive-bin curves use 31.25 Hz–8 kHz only; nulls remain gaps. The full-band main metric includes DC, omitted on the log axis.'
            if frequency else 'Dots and intervals are stored values. Positive gain favors +α (denoiser ON). Four clusters give uncertain interval coverage.')
    lines = [note,
        '32 synthetic rooms · 8 VCTK speakers / 4 speaker-pair clusters · 1–2 speech sources · 6-mic sphere, radius 6 cm · known SNR 50 dB.',
        'Matched N5; FOA ACN/N3D; 16 kHz / FFT 512 / hop 128; short 32-frame excerpts. Waveform scoring and preview cover 0.248 s after edge trim.',
        'Frozen independent 30.78M prior. Synthetic, short-time results only; no original-paper superiority or long-form audio quality established.',
        'ADEPS-inspired implementation: Milstein, Shlezinger & Rafaely (2026) · ' + PAPER,
        'Evaluation protocol: ' + PROTOCOL,
        f'Record SHA-256: {digest}   |   Font: {font}']
    base = .178 if frequency else .186
    gap = .022 if frequency else .025
    for index, line in enumerate(lines):
        fig.text(.045, base - index * gap, line, fontsize=8.3, color='#aaa', ha='left', va='top')


def frequency_figure(report, digest, font):
    fig, axes = plt.subplots(3, 1, figsize=(14.4, 12), sharex=True)
    fig.subplots_adjust(left=.095, right=.965, top=.815, bottom=.265, hspace=.23)
    fig.suptitle('ADEPS + α · frequency comparison', x=.095, y=.966, ha='left', fontsize=23)
    fig.text(.095, .922, 'Mean saved scene curves · one observation per scene · five reconstruction methods', fontsize=11, color='#bbb')
    titles = ('(a) Complex reconstruction error · lower is better', '(b) Magnitude spectrum error · lower is better', '(c) Magnitude-squared coherence · higher is better')
    labels = ('NRMSE [dB]', 'Magnitude error [dB]', 'MSC')
    positive = FREQUENCIES > 0
    for ax, key, title, ylabel in zip(axes, CURVES, titles, labels):
        for method in FREQUENCY_IDS:
            color, dash, width = STYLES[method]
            values = np.array([np.nan if value is None else value for value in report['curves'][method][key]], dtype=float)
            ax.plot(FREQUENCIES[positive], values[positive], color=color, linestyle=dash, linewidth=width, label=LABELS[method])
        ax.set_title(title, loc='left', fontsize=11, pad=11)
        ax.set_ylabel(ylabel, labelpad=10)
        ax.set_xscale('log'); ax.set_xlim(1, 20000); ax.grid(axis='y')
        ax.tick_params(axis='both', labelsize=10)
        for bound in (31.25, 8000): ax.axvline(bound, color='#555', linewidth=.7, linestyle=':')
        if key == 'magnitude_squared_coherence': ax.set_ylim(0, 1)
        elif key == 'magnitude_spectrum_error_db': ax.set_ylim(bottom=0)
    axes[0].text(4, .8, 'No data', transform=axes[0].get_xaxis_transform(), color='#777', fontsize=9)
    axes[0].text(11500, .8, 'No data', transform=axes[0].get_xaxis_transform(), color='#777', fontsize=9, ha='center')
    # Preserve all peaks in the main panel; this explicitly labelled inset
    # makes the lower-error region readable without changing stored values.
    detail = axes[1].inset_axes([.035, .33, .275, .46])
    for method in FREQUENCY_IDS:
        color, dash, width = STYLES[method]
        values = np.array([np.nan if value is None else value for value in report['curves'][method]['magnitude_spectrum_error_db']], dtype=float)
        detail.plot(FREQUENCIES[positive], values[positive], color=color, linestyle=dash, linewidth=width * .65)
    detail.set_xscale('log'); detail.set_xlim(31.25, 8000); detail.set_ylim(0, 25)
    detail.set_xticks([100, 1000, 8000], ['100', '1k', '8k']); detail.set_yticks([0, 10, 20])
    detail.tick_params(axis='both', labelsize=7, length=2)
    detail.set_title('Detail: 0–25 dB · 31.25 Hz–8 kHz', fontsize=8, pad=5)
    detail.grid(axis='y', alpha=.35)
    axes[-1].set_xticks([1, 10, 31.25, 100, 1000, 8000, 20000], ['1', '10', '31.25', '100', '1k', '8k', '20k'])
    axes[-1].set_xlabel('Frequency [Hz] · logarithmic display 1 Hz–20 kHz', labelpad=12)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc='upper left', bbox_to_anchor=(.085, .895), ncol=3, frameon=False,
               handlelength=4.6, columnspacing=2.3, labelspacing=.8, fontsize=10)
    footnotes(fig, digest, font, frequency=True)
    return fig


def expand_limits(ax, values, *, include_zero=False):
    values = [value for value in values if value is not None]
    if include_zero: values.append(0.)
    low, high = (min(values), max(values)) if values else (-1., 1.)
    width = max(high - low, 1.)
    ax.set_xlim(low - .13 * width, high + .25 * width)


def summary_figure(report, digest, font):
    fig = plt.figure(figsize=(16, 10))
    left, right = fig.add_axes([.195, .32, .28, .475]), fig.add_axes([.69, .32, .275, .475])
    fig.suptitle('ADEPS + α · all methods and paired comparisons', x=.045, y=.96, ha='left', fontsize=23)
    fig.text(.045, .91, 'Saved full-band scene means, including DC · all nine methods retained · lower NRMSE is better', fontsize=11, color='#bbb')
    means = [row['mean_nrmse_db'] for row in report['methods']]
    for y, method, value in zip(range(9), IDS, means):
        if value is None:
            left.text(.5, y, 'Undefined', transform=left.get_yaxis_transform(), ha='center', va='center', color='#aaa', fontsize=10)
        else:
            left.plot(value, y, marker='s' if method == 'plus_no_denoiser' else 'o', markersize=7,
                      markerfacecolor='#fff' if method == 'plus' else '#080808', markeredgecolor='#eee', linestyle='none')
            left.annotate(f'{value:.3f}', (value, y), xytext=(9, 0), textcoords='offset points', va='center', fontsize=9)
    left.set_yticks(range(9), [LABELS[method] for method in IDS]); left.set_ylim(8.65, -.65)
    expand_limits(left, means)
    left.set_xlabel('Mean NRMSE [dB]', labelpad=12); left.set_title('(a) Absolute reconstruction error', loc='left', fontsize=12, pad=17)
    baselines = [method for method in IDS if method != 'plus']
    comparisons = {row['baseline']: row for row in report['comparisons']}
    limits = []
    for y, method in enumerate(baselines):
        row = comparisons[method]; value, low, high = (row[key] for key in ('mean_gain_db', 'ci_low_db', 'ci_high_db'))
        limits.extend([value, low, high])
        if low is not None:
            right.hlines(y, low, high, color='#ccc', linewidth=1.2)
            right.vlines([low, high], y-.09, y+.09, color='#ccc', linewidth=1.)
        if value is None:
            right.text(.5, y, 'Undefined', transform=right.get_yaxis_transform(), ha='center', va='center', color='#aaa', fontsize=10)
        else:
            right.plot(value, y, 's' if method == 'plus_no_denoiser' else 'o', color='#eee', markersize=5)
            right.annotate(f'{value:+.3f}', (high if high is not None else value, y), xytext=(8, 0), textcoords='offset points', va='center', fontsize=9)
    right.axvline(0, color='#777', linestyle='--', linewidth=.8)
    right.set_yticks(range(8), [LABELS[method] for method in baselines]); right.set_ylim(7.6, -.6)
    expand_limits(right, limits, include_zero=True)
    right.set_xlabel('Gain [dB] = error(baseline) − error(+α ON)\nPositive favors +α (denoiser ON)', labelpad=12)
    right.set_title('(b) Paired gain · nominal 97.5% cluster CI', loc='left', fontsize=12, pad=17)
    for ax in (left, right):
        ax.grid(axis='x'); ax.tick_params(axis='y', length=0, pad=9, labelsize=10); ax.tick_params(axis='x', labelsize=10)
    off = comparisons['plus_no_denoiser']
    gain = 'undefined' if off['mean_gain_db'] is None else f"{off['mean_gain_db']:+.3f} dB"
    ci = 'undefined' if off['ci_low_db'] is None else f"[{off['ci_low_db']:+.3f}, {off['ci_high_db']:+.3f}] dB"
    fig.text(.045, .252, f"ON vs OFF: mean gain {gain} · nominal 97.5% CI {ci} · ON improved {off['wins']}/32, worsened {off['losses']}/32; tied {off['ties']}, undefined {off['invalid']}.", fontsize=10, color='#eee')
    fig.text(.045, .225, 'An improvement of the combined method does not by itself show a benefit from the learned denoiser.', fontsize=9.5, color='#bbb')
    footnotes(fig, digest, font, frequency=False)
    return fig


def render(report_path, output_dir):
    report, digest = read_report(report_path)
    font = choose_font()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    description = f'Saved ADEPS+ synthetic benchmark only; record SHA-256 {digest}. Font {font}. No metric recomputation or inference. {PAPER} . Protocol: {PROTOCOL}'
    # Stage in system temporary storage, then write and verify final paths
    # without renaming files out of a Documents/FileProvider staging folder.
    with matplotlib.rc_context(style(font)), tempfile.TemporaryDirectory(prefix='adeps-plus-plots-') as temporary:
        for name, builder in [('plus-frequency-comparison', frequency_figure), ('plus-summary-comparison', summary_figure)]:
            fig = builder(report, digest, font)
            try:
                for extension in ('svg', 'png'):
                    target = Path(temporary) / f'{name}.{extension}'
                    metadata = {'Title': name, 'Description': description}
                    if extension == 'svg': metadata.update({'Date': None, 'Creator': 'ADEPS-test · Matplotlib'})
                    fig.savefig(target, format=extension, dpi=220, metadata=metadata)
                    artifacts[target.name] = {'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
            finally:
                plt.close(fig)
        require(hashlib.sha256(Path(report_path).read_bytes()).hexdigest() == digest, 'Benchmark changed while rendering; figures not published')
        for name in artifacts:
            (output / name).write_bytes((Path(temporary) / name).read_bytes())
        for name, expected in artifacts.items():
            target = output / name
            require(target.is_file() and target.stat().st_size == expected['bytes']
                    and hashlib.sha256(target.read_bytes()).hexdigest() == expected['sha256'],
                    'Final figure failed persistence verification: ' + name)
    return {'schema': 'adeps-plus-scientific-figures/1', 'report_sha256': digest, 'font': font,
            'figure_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'plotted_frequency_bins': 256, 'plotted_frequency_range_hz': [31.25, 8000],
            'display_frequency_range_hz': [1, 20000], 'main_metric_includes_dc': True,
            'metrics_recomputed': False, 'artifacts': artifacts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'work/plus-v1/benchmark.json')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'public/models')
    parser.add_argument('--manifest', type=Path, help='Optional figure SHA manifest path; defaults beside the benchmark report.')
    args = parser.parse_args()
    try:
        result = render(args.report, args.output_dir)
        manifest = args.manifest or args.report.parent / 'figures-manifest.json'
        manifest.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f'ADEPS+ plot error: {exc}\n')
