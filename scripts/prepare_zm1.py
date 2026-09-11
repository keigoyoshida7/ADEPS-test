"""Prepare ZM-1 files locally. Never opens an audio device or runs a neural model."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from zm1 import load_iem_sofa, response_profile, replay, load_recording, make_audio_zip, LIMITATIONS


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n')


def plot_audit(data, audit, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(12, 8), layout='constrained')
    ax = fig.add_subplot(221, projection='3d')
    xyz = data['receiver_xyz']
    ax.scatter(*xyz.T, c='white', s=22)
    for i, p in enumerate(xyz): ax.text(*p, str(i+1), fontsize=7)
    ax.set(xlabel='X (m)', ylabel='Y (m)', zlabel='Z (m)', title='19 receivers / dataset coordinates')
    ax.set_box_aspect((1, 1, 1))
    ax = fig.add_subplot(222)
    f = np.asarray(audit['frequency_hz'])
    ax.semilogx(f[1:], np.asarray(audit['train_response_error_db'])[1:], '--', c='.5', label='Fit directions')
    ax.semilogx(f[1:], np.asarray(audit['heldout_response_error_db'])[1:], c='white', label='Held-out directions')
    ax.axvspan(1, 375, color='.4', alpha=.3)
    ax.set(xlim=(1, 20000), xlabel='Frequency (Hz)', ylabel='Relative complex error (dB)', title='Order-5 response fit (lower is better)')
    ax.legend(fontsize=8); ax.grid(alpha=.15)
    ax = fig.add_subplot(223)
    ax.semilogx(f[1:], np.asarray(audit['foa_column_condition'])[1:], c='white')
    ax.set(xlim=(1, 20000), yscale='log', xlabel='Frequency (Hz)', ylabel='Condition number', title='First four columns only / lower is better')
    ax.axvspan(1, 375, color='.4', alpha=.3); ax.grid(alpha=.15)
    ax = fig.add_subplot(224); ax.axis('off')
    text = ('RESPONSE AUDIT — NOT ADEPS PERFORMANCE\n\n'
            f"{audit['training_directions']} fit / {audit['heldout_directions']} held-out directions\n"
            '48 kHz / 128-sample measured IRs\n'
            '375 Hz original DFT spacing; padding is not resolution\n'
            'Shaded low band: no precision claim\n\n'
            'Generation / USB order / pressure reference unverified\n'
            'No new venue recording; no official neural model\n'
            'Local research only; redistribution rights unresolved')
    ax.text(0, .95, text, va='top', fontsize=10, linespacing=1.6)
    fig.suptitle('ZM-1 / microphone-free preparation', fontsize=17)
    fig.savefig(out/'response-audit.png', dpi=170); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    audit = sub.add_parser('audit', help='Read pinned IEM SOFA, fit held-out model, create synthetic replay')
    audit.add_argument('--sofa', type=Path, required=True)
    audit.add_argument('--out', type=Path, required=True)
    inspect = sub.add_parser('inspect', help='Check raw WAV before modeling')
    inspect.add_argument('wav', type=Path)
    pack = sub.add_parser('pack', help='Prepare a short real raw recording for existing importer')
    pack.add_argument('wav', type=Path)
    pack.add_argument('--profile', type=Path, required=True)
    pack.add_argument('--out', type=Path, required=True)
    pack.add_argument('--start', type=float, default=0)
    pack.add_argument('--duration', type=float, default=.1)
    pack.add_argument('--device-generation', choices=['1C', '1D', '3E'], required=True)
    pack.add_argument('--confirm-sofa-channel-order', action='store_true', help='Confirm WAV order matches SOFA receiver order')
    pack.add_argument('--accept-unverified-response', action='store_true', help='Acknowledge generation/pressure-reference compatibility remains unverified')
    args = parser.parse_args()
    if args.command == 'inspect':
        _, _, qc = load_recording(args.wav)
        print(json.dumps(qc, ensure_ascii=False, indent=2))
        return 0 if qc['ready_for_packaging'] else 2
    if args.out.exists():
        raise ValueError('Output already exists; choose a new path to preserve previous work')
    if args.command == 'pack':
        if not args.confirm_sofa_channel_order or not args.accept_unverified_response:
            raise ValueError('Confirm channel order and explicitly accept the unverified response before experimental packaging')
        rate, audio, qc = load_recording(args.wav)
        if not np.isfinite(args.start+args.duration) or args.start < 0 or not .02 <= args.duration <= .15:
            raise ValueError('Use a 0.02–0.15 second segment with nonnegative start')
        begin, end = round(args.start*rate), round((args.start+args.duration)*rate)
        if end > len(audio): raise ValueError('Selected segment exceeds recording length')
        profile = json.loads(args.profile.read_text())
        source_hash = hashlib.sha256(args.wav.read_bytes()).hexdigest()
        payload = make_audio_zip(profile, audio[begin:end],
            f'User-supplied raw-format ZM-1 WAV; capture provenance unverified; user-declared generation {args.device_generation}; source SHA256={source_hash}; start={args.start}s; experimental response, compatibility unverified')
        # Do not disclose the local filename in a shareable input manifest.
        args.out.write_bytes(payload)
        print(f'Prepared {args.out}; no inference or playback performed')
        return 0
    data = load_iem_sofa(args.sofa)
    profile, report = response_profile(data)
    payload, linear, replay_check = replay(data, profile)
    args.out.mkdir(parents=True)
    save_json(args.out/'response-profile.json', profile)
    save_json(args.out/'response-audit.json', report)
    save_json(args.out/'replay-check.json', replay_check)
    (args.out/'replay-input.zip').write_bytes(payload)
    (args.out/'replay-linear-FOA-ACN-SN3D.wav').write_bytes(linear)
    save_json(args.out/'recording-notes-template.json', {
        'device_generation': None, 'device_serial_private': None, 'recording_date': None,
        'sample_rate_hz': 48000, 'raw_channels': 19, 'gain_setting': None,
        'mic_center_xyz_m': None, 'mic_front_direction': None, 'mic_upright': None,
        'source_position_xyz_m': None, 'playback_filename': None,
        'processing_off_confirmed': False, 'sofa_channel_order_confirmed': False,
        'venue_geometry_reference': None, 'notes': ''})
    plot_audit(data, report, args.out)
    (args.out/'READ-ME.md').write_text(
        '# ZM-1：マイクなしの準備結果\n\n'
        '公開された実測応答を読み取り、未使用方向で応答モデルを検査しました。'
        'replay-input.zip は生成した信号を実測IRに通した模擬入力です。新しい実録音ではありません。'
        '公式ADEPS・既存の小型ニューラルモデルはいずれも実行していません。\n\n'
        '- response-audit.png：配置と周波数別の検証結果\n'
        '- response-profile.json：実験用の応答モデル。購入個体との整合は未確認\n'
        '- replay-input.zip：既存の音声読み込み形式との互換性確認用\n'
        '- replay-linear-FOA-ACN-SN3D.wav：線形出力。4chはW/Y/Z/Xで、スピーカー直結不可\n'
        '- recording-notes-template.json：購入後の収録メモ\n\n'
        '## 残る条件\n\n'
        '購入個体の世代・チャンネル順・向き・応答の基準を確認し、現場でraw19chを収録します。'
        '論文と同じ性能の評価には、公式の学習済みモデルと再現条件が別途必要です。'
        'データの権利記載に不一致があるため、応答データと派生ファイルはローカル検証用です。\n\n'
        '[公開データ](https://phaidra.kug.ac.at/o:91937) / '
        '[公式ADEPS公開先](https://github.com/Amitmils/ADEUPS)\n\n'
        '## Technical limitations\n\n'+'\n'.join('- '+x for x in LIMITATIONS)+'\n')
    print(json.dumps({'output': str(args.out), **replay_check}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        raise SystemExit(str(exc))
