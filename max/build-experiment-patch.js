'use strict';
// Offline patch generator. Max executes only standard objects in the generated .maxpat.
const fs = require('node:fs');
const path = require('node:path');

function buildPatch() {
  const boxes = [], lines = [];
  let hidden = 0;
  function box(id, maxclass, text, ni, no, rect, extra = {}) {
    const b = {id, maxclass, numinlets: ni, numoutlets: no,
      patching_rect: rect || [30 + (hidden % 7) * 180, 1020 + Math.floor(hidden++ / 7) * 65, 170, 24],
      fontname: 'Yu Mincho', fontsize: 12, ...extra};
    if (text !== null) b.text = text;
    if (rect) Object.assign(b, {presentation: 1, presentation_rect: rect});
    boxes.push({box: b}); return id;
  }
  const obj = (id, text, ni = 1, no = 1) => box(id, 'newobj', text, ni, no);
  const msg = (id, text) => box(id, 'message', text, 2, 1);
  const wire = (a, b, ao = 0, bi = 0, order) => lines.push({patchline: {
    source: [a, ao], destination: [b, bi], ...(order === undefined ? {} : {order})}});
  const note = (id, text, x, y, w, h = 35, size = 13) => box(id, 'comment', text, 1, 0,
    [x, y, w, h], {fontsize: size, textcolor: [.90, .90, .90, 1]});
  const button = (id, text, x, y, w = 170) => box(id, 'textbutton', text, 1, 3,
    [x, y, w, 30], {mode: 0, outputmode: 1, textcolor: [1, 1, 1, 1], bgcolor: [.17, .17, .17, 1]});
  function click(id, target) { // textbutton's left outlet emits bang in momentary mode.
    wire(id, target);
  }
  function control(id, type, rect, extra = {}) {
    return box(id, type, null, 1, type === 'flonum' || type === 'number' ? 2 : 1, rect, extra);
  }
  function boundedGain(id, x, y) {
    control(id, 'flonum', [x, y, 85, 28], {minimum: 0, maximum: .03, format: 6});
    obj(id + '_clip', 'clip 0. 0.03', 3); obj(id + '_ramp', 'pack 0. 100', 2);
    obj(id + '_signal', 'line~ 0.', 2, 2);
    wire(id, id + '_clip'); wire(id + '_clip', id + '_ramp'); wire(id + '_ramp', id + '_signal');
    return id + '_signal';
  }
  note('title', 'ADEPS-test / 音を用意する・収録する・比較する', 25, 15, 1090, 38, 25);
  note('intro', 'Max 9 standard objects / 音声はWAVで手動受け渡し。Webへの音声送信・リアルタイム推論は行いません。', 25, 58, 1080);
  button('stop_all', 'STOP ALL / MUTE', 25, 98, 250);
  box('dsp', 'ezdac~', null, 2, 0, [1020, 96, 40, 40]);
  note('dsp_note', 'DSPはここで手動操作 →', 800, 101, 210);
  msg('zero', '0'); obj('initial_zero', 'loadmess 0');
  click('stop_all', 'zero'); wire('initial_zero', 'zero');

  note('source_title', '01  元音源 / マイクなしの検証にも使用', 25, 147, 1060, 30, 18);
  box('source_mode', 'umenu', null, 1, 3, [25, 188, 215, 28],
    {items: ['OFF', ',', 'Mono WAV', ',', 'Pink noise', ',', 'Log sweep 20Hz–20kHz', ',', 'Short pink burst 100ms']});
  button('source_open', 'Mono WAVを開く', 255, 188, 170);
  control('source_run', 'toggle', [455, 189, 27, 27]);
  note('source_run_note', 'SOURCE RUN', 490, 191, 140);
  button('source_trigger', 'Sweep / burstを1回', 640, 188, 210);
  note('source_note', 'Mono WAV＝声・音楽。Sweep＝8秒、burst＝100ms。生成音はRUNを入れた後にトリガー。選択変更で停止します。', 25, 225, 1070, 35);
  obj('source_select', 'selector~ 4 0', 5); obj('source_file', 'sfplay~ 1', 2, 2);
  obj('pink', 'pink~', 1); obj('source_clip', 'clip~ -1. 1.', 3);
  obj('source_run_ramp', 'pack 0. 20', 2); obj('source_run_signal', 'line~ 0.', 2, 2);
  obj('source_gated', '*~ 0.', 2);
  obj('mode_change', 't i b', 1, 2); msg('source_stop', '0');
  obj('mono_selected', '== 1', 2); obj('file_start_gate', 'gate 1 0', 2);
  obj('file_end_gate', 'gate 1 0', 2); msg('file_open_message', 'open');
  obj('source_run_order', 't i i', 1, 2); obj('source_arm_eof', 'sel 1', 1, 2);
  obj('source_eof_once', 'onebang 0', 2);
  obj('source_open_order', 't b b', 1, 2);
  wire('source_mode', 'mode_change'); wire('mode_change', 'source_stop', 1);
  wire('mode_change', 'source_select', 0); wire('mode_change', 'mono_selected', 0);
  wire('mono_selected', 'file_start_gate'); wire('mono_selected', 'file_end_gate');
  wire('source_run', 'source_run_ramp'); wire('source_run_ramp', 'source_run_signal');
  wire('source_run', 'source_run_order'); wire('source_run_order', 'source_arm_eof', 1);
  wire('source_arm_eof', 'source_eof_once', 0, 1);
  wire('source_run_order', 'file_start_gate', 0, 1); wire('file_start_gate', 'source_file');
  wire('source_file', 'file_end_gate', 1, 1); wire('file_end_gate', 'source_eof_once');
  wire('source_eof_once', 'source_stop');
  wire('source_stop', 'source_run'); wire('source_stop', 'source_file');
  click('source_open', 'source_open_order'); wire('source_open_order', 'source_stop', 1);
  wire('source_open_order', 'file_open_message'); wire('file_open_message', 'source_file');
  wire('source_file', 'source_select', 0, 1); wire('pink', 'source_select', 0, 2);
  wire('source_select', 'source_clip'); wire('source_clip', 'source_gated');
  wire('source_run_signal', 'source_gated', 0, 1); wire('zero', 'source_run');
  wire('zero', 'source_file');

  // A line in log frequency produces a logarithmic 20 Hz to 20 kHz sweep.
  // These two generated tests are path checks, not neural-calibration ground truth.
  obj('sweep_phase', 'line~ 0.', 2, 2); obj('sweep_hz', 'expr~ 20. * exp(6.907755278982137 * $v1)');
  obj('sweep_osc', 'cycle~ 20.', 2); obj('sweep_env', 'line~ 0.', 2, 2);
  obj('sweep_audio', '*~ 0.', 2); obj('burst_env', 'line~ 0.', 2, 2);
  obj('burst_audio', '*~ 0.', 2); obj('test_trigger', 't b b b', 1, 3);
  msg('sweep_ramp', '0., 1. 8000'); msg('sweep_envelope', '0., 1. 20 1. 7960 0. 20');
  msg('burst_envelope', '0., 1. 10 1. 80 0. 10');
  click('source_trigger', 'test_trigger');
  wire('test_trigger', 'sweep_ramp', 2); wire('test_trigger', 'sweep_envelope', 1);
  wire('test_trigger', 'burst_envelope'); wire('sweep_ramp', 'sweep_phase');
  wire('sweep_phase', 'sweep_hz'); wire('sweep_hz', 'sweep_osc');
  wire('sweep_envelope', 'sweep_env'); wire('sweep_osc', 'sweep_audio'); wire('sweep_env', 'sweep_audio', 0, 1);
  wire('burst_envelope', 'burst_env'); wire('pink', 'burst_audio'); wire('burst_env', 'burst_audio', 0, 1);
  wire('sweep_audio', 'source_select', 0, 3); wire('burst_audio', 'source_select', 0, 4);
  for (const target of ['sweep_env', 'burst_env', 'sweep_phase']) {
    wire('zero', target); wire('source_stop', target);
  }

  note('output_note', '会場へ出す時だけ：論理出力 0=閉 / 1–12', 25, 270, 420);
  control('output_channel', 'number', [450, 269, 60, 28], {minimum: 0, maximum: 12});
  note('gain_note', 'OUTPUT GAIN 0–0.030', 550, 273, 230);
  const gain = boundedGain('output_gain', 790, 269);
  note('output_hint', '論理出力はDante番号ではありません。Audio Statusで対応確認。マイクなしで保存するだけなら出力0・GAIN 0で使えます。', 25, 309, 1060, 35);
  obj('output_channel_order', 't i b', 1, 2); msg('output_gain_zero', '0.');
  obj('output_gate', 'gate~ 12 0', 2, 12); obj('output_amp', '*~ 0.', 2);
  obj('output_dac', 'dac~ 1 2 3 4 5 6 7 8 9 10 11 12', 12, 0);
  wire('source_gated', 'output_amp'); wire(gain, 'output_amp', 0, 1);
  wire('output_amp', 'output_gate', 0, 1); wire('output_channel', 'output_channel_order');
  wire('output_channel_order', 'output_gain_zero', 1);
  wire('output_gain_zero', 'output_gain'); wire('output_gain_zero', gain);
  wire('output_channel_order', 'output_gate');
  for (let i = 0; i < 12; i++) wire('output_gate', 'output_dac', i, i);
  wire('zero', 'output_channel'); wire('zero', 'output_gain'); wire('zero', gain);

  note('record_title', '02  WAVを保存 / 保存先を選び、録音 → SOURCE RUN → 停止', 25, 367, 1060, 30, 18);
  obj('samptype_init', 'loadmess samptype int24');
  function recorder(prefix, label, y, channels) {
    button(prefix + '_choose', label + ' 保存先…', 25, y, 230);
    button(prefix + '_start', '録音 START', 275, y, 150);
    button(prefix + '_stop', '停止 / CLOSE', 440, y, 150);
    box(prefix + '_elapsed', 'number~', null, 2, 2, [875, y, 100, 30], {mode: 2});
    note(prefix + '_time_label', '経過 ms', 987, y + 3, 100);
    box(prefix + '_path', 'message', '保存先未選択 / .wav を指定', 2, 1, [25, y + 36, 1050, 25]);
    obj(prefix + '_dialog', 'savedialog WAVE', 1, 2);
    obj(prefix + '_path_order', 't b s s', 1, 3); obj(prefix + '_show_path', 'prepend set');
    obj(prefix + '_wave', 'append wave'); obj(prefix + '_open', 'prepend open');
    obj(prefix + '_recorder', 'sfrecord~ ' + channels, channels);
    msg(prefix + '_one', '1'); msg(prefix + '_zero', '0'); msg(prefix + '_ready', '1');
    obj(prefix + '_ready_gate', 'gate 1 0', 2);
    obj(prefix + '_choose_order', 't b b', 1, 2);
    click(prefix + '_choose', prefix + '_choose_order');
    wire(prefix + '_choose_order', prefix + '_zero', 1);
    wire(prefix + '_choose_order', prefix + '_dialog'); wire(prefix + '_dialog', prefix + '_path_order');
    wire(prefix + '_path_order', prefix + '_show_path', 2); wire(prefix + '_show_path', prefix + '_path');
    wire(prefix + '_path_order', prefix + '_wave', 1); wire(prefix + '_wave', prefix + '_open');
    wire(prefix + '_open', prefix + '_recorder'); wire(prefix + '_path_order', prefix + '_ready');
    wire(prefix + '_ready', prefix + '_ready_gate');
    click(prefix + '_start', prefix + '_one'); wire(prefix + '_one', prefix + '_ready_gate', 0, 1);
    wire(prefix + '_ready_gate', prefix + '_recorder');
    click(prefix + '_stop', prefix + '_zero'); wire(prefix + '_zero', prefix + '_recorder');
    wire(prefix + '_zero', prefix + '_ready_gate'); wire('zero', prefix + '_zero');
    wire('samptype_init', prefix + '_recorder'); wire(prefix + '_recorder', prefix + '_elapsed');
  }
  recorder('source_capture', '元音源 / mono', 411, 1);
  recorder('array_capture', 'マイク / raw 19ch', 495, 19);
  wire('source_gated', 'source_capture_recorder'); // pre-output gain / pre-DAC source only
  obj('array_adc', 'adc~ ' + Array.from({length: 19}, (_, i) => i + 1).join(' '), 1, 19);
  for (let i = 0; i < 19; i++) wire('array_adc', 'array_capture_recorder', i, i);
  button('both_record', '両方の録音 START', 625, 411, 225);
  obj('both_record_order', 't b b', 1, 2);
  click('both_record', 'both_record_order');
  wire('both_record_order', 'array_capture_one', 1); wire('both_record_order', 'source_capture_one');
  note('record_hint', '保存はPCM24bit・現在のDSPサンプルレート。停止後は毎回保存先を選び直す。raw入力1–19は音声ドライバで現地照合。', 25, 575, 1060, 35);
  note('clock_hint', '19ch内は同じ録音処理。再生機器とUSBマイクの共通クロックは保証しません。元mono音源は実空間のFOA正解ではありません。', 25, 611, 1060, 35);

  note('ab_title', '03  オフライン比較 / Webで書き出した同じテストのFOA 4ch WAV', 25, 660, 1080, 30, 18);
  button('linear_open', 'OFF / Linear WAV…', 25, 705, 210);
  button('enhanced_open', 'ON / Enhanced WAV…', 250, 705, 230);
  button('ab_start', 'A+B 同時 START', 495, 705, 190);
  button('ab_stop', 'A+B STOP', 700, 705, 160);
  control('ab_mix', 'toggle', [895, 705, 28, 28]);
  note('ab_mix_label', 'ON = Enhanced', 933, 708, 170);
  note('ab_gain_label', 'FOA BUS GAIN 0–0.030', 25, 755, 265);
  const abGain = boundedGain('ab_gain', 290, 752);
  note('ab_warning', 'FOA = ACN/SN3D / W,Y,Z,X。4本をスピーカーへ直結しないでください。', 410, 755, 685);
  note('ab_bus_note', 'receive~ adeps-experiment.W / .Y / .Z / .X → 同じ外部FOAデコーダー → スピーカー。bus以外へのFOA出力はありません。', 25, 797, 1060, 35);
  note('ab_hint', '同じ長さ・レート・時刻原点・共通gainで書き出したペアを使用。切替は20ms crossfade、同じ輸送位置を維持します。', 25, 837, 1060, 35);
  note('limits', '新規ファイルを開くと比較を停止しGAIN 0。DSPは他パッチと共有。ここに公式ADEPSモデルや自動校正は含まれません。', 25, 879, 1060, 35);
  obj('linear_player', 'sfplay~ 4', 2, 5); obj('enhanced_player', 'sfplay~ 4', 2, 5);
  msg('ab_play_one', '1'); msg('ab_play_zero', '0');
  obj('ab_start_order', 't b b', 1, 2);
  obj('ab_play_pair', 't i i', 1, 2); obj('ab_stop_pair', 't i i', 1, 2);
  click('ab_start', 'ab_start_order'); wire('ab_start_order', 'ab_play_zero', 1);
  wire('ab_start_order', 'ab_play_one'); wire('ab_play_one', 'ab_play_pair');
  wire('ab_play_pair', 'linear_player', 1); wire('ab_play_pair', 'enhanced_player');
  click('ab_stop', 'ab_play_zero'); wire('ab_play_zero', 'ab_stop_pair');
  wire('ab_stop_pair', 'linear_player', 1); wire('ab_stop_pair', 'enhanced_player');
  // sfplay~ emits a bang on halt as well as EOF. onebang prevents recursive 0/bang loops.
  obj('ab_eof_once', 'onebang 1', 2); wire('linear_player', 'ab_eof_once', 4);
  wire('enhanced_player', 'ab_eof_once', 4); wire('ab_eof_once', 'ab_play_zero');
  obj('ab_arm_eof', 't b b', 1, 2);
  // Start order: stop old files -> reset the EOF guard -> start both from zero.
  wire('ab_start_order', 'ab_arm_eof');
  // Replace the direct start edge so arming is deterministically before start.
  lines.splice(lines.findIndex(x => x.patchline.source[0] === 'ab_start_order' && x.patchline.destination[0] === 'ab_play_one'), 1);
  wire('ab_arm_eof', 'ab_eof_once', 1, 1); wire('ab_arm_eof', 'ab_play_one');
  for (const name of ['linear', 'enhanced']) {
    obj(name + '_open_order', 't b b b', 1, 3); msg(name + '_open_msg', 'open');
    click(name + '_open', name + '_open_order'); wire(name + '_open_order', 'ab_play_zero', 2);
    wire(name + '_open_order', 'ab_reset_gain', 1); wire(name + '_open_order', name + '_open_msg');
    wire(name + '_open_msg', name + '_player');
  }
  msg('ab_reset_gain', '0.'); wire('ab_reset_gain', 'ab_gain'); wire('ab_reset_gain', abGain);
  wire('zero', 'ab_play_zero'); wire('zero', 'ab_reset_gain'); wire('zero', 'ab_mix');
  obj('ab_mix_clip', 'clip 0 1', 3); obj('ab_mix_ramp', 'pack 0. 20', 2);
  obj('ab_mix_signal', 'line~ 0.', 2, 2); obj('ab_linear_weight', '!-~ 1.', 2);
  wire('ab_mix', 'ab_mix_clip'); wire('ab_mix_clip', 'ab_mix_ramp'); wire('ab_mix_ramp', 'ab_mix_signal');
  wire('ab_mix_signal', 'ab_linear_weight');
  for (let i = 0; i < 4; i++) {
    const ch = ['W', 'Y', 'Z', 'X'][i];
    obj('ab_a_' + ch, '*~ 0.', 2); obj('ab_b_' + ch, '*~ 0.', 2); obj('ab_sum_' + ch, '+~', 2);
    obj('ab_gain_' + ch, '*~ 0.', 2); obj('ab_send_' + ch, 'send~ adeps-experiment.' + ch, 1, 0);
    wire('linear_player', 'ab_a_' + ch, i); wire('enhanced_player', 'ab_b_' + ch, i);
    wire('ab_linear_weight', 'ab_a_' + ch, 0, 1); wire('ab_mix_signal', 'ab_b_' + ch, 0, 1);
    wire('ab_a_' + ch, 'ab_sum_' + ch); wire('ab_b_' + ch, 'ab_sum_' + ch, 0, 1);
    wire('ab_sum_' + ch, 'ab_gain_' + ch); wire(abGain, 'ab_gain_' + ch, 0, 1);
    wire('ab_gain_' + ch, 'ab_send_' + ch);
  }
  return {patcher: {fileversion: 1, appversion: {major: 9, minor: 0, revision: 0, architecture: 'x64', modernui: 1},
    classnamespace: 'box', rect: [60, 60, 1140, 970], openinpresentation: 1,
    default_fontname: 'Yu Mincho', default_fontsize: 12,
    bgcolor: [.025, .025, .025, 1], editing_bgcolor: [.08, .08, .08, 1],
    boxes, lines}};
}
if (require.main === module) fs.writeFileSync(path.join(__dirname, 'ADEPS_Experiment.maxpat'), JSON.stringify(buildPatch(), null, 2) + '\n');
module.exports = {buildPatch};
