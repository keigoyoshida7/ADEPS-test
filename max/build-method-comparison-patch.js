'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {METHODS} = require('./method-comparison-bank');

function buildPatch() {
  const boxes = [], lines = []; let hidden = 0;
  function box(id, maxclass, text, ni, no, rect, extra = {}) {
    const b = {id, maxclass, numinlets: ni, numoutlets: no,
      patching_rect: rect || [30 + (hidden % 8) * 185, 850 + Math.floor(hidden++ / 8) * 62, 178, 24],
      fontname: 'Yu Mincho', fontsize: 12, ...extra};
    if (text !== null) b.text = text;
    if (rect) Object.assign(b, {presentation: 1, presentation_rect: rect});
    boxes.push({box: b}); return id;
  }
  const obj = (id, text, ni = 1, no = 1) => box(id, 'newobj', text, ni, no);
  const msg = (id, text) => box(id, 'message', text, 2, 1);
  const wire = (a, b, ao = 0, bi = 0, order) => lines.push({patchline: {
    source: [a, ao], destination: [b, bi], ...(order === undefined ? {} : {order})}});
  const note = (id, text, x, y, width, height = 40, size = 13) =>
    box(id, 'comment', text, 1, 0, [x, y, width, height], {fontsize: size, textcolor: [.92, .92, .92, 1]});
  const button = (id, text, x, y, width = 195) => box(id, 'textbutton', text, 1, 3,
    [x, y, width, 33], {mode: 0, outputmode: 1, textcolor: [1, 1, 1, 1], bgcolor: [.17, .17, .17, 1]});

  note('title', 'ADEPS-test / 方式を選んで、同じ音を比較する', 25, 16, 980, 42, 25);
  note('subtitle', 'METHOD COMPARISON · 同期FOAバンク → 共通N3Dデコーダー → 12ch / One playhead, one output gain', 25, 65, 980, 40);
  button('stop_all', 'STOP / MUTE', 25, 112, 260);
  note('muted_default', '起動・読込・停止時は音量0 / Gain starts at zero', 305, 114, 540);
  box('dsp', 'ezdac~', null, 2, 0, [930, 111, 42, 42]);
  note('dsp_note', 'DSP手動 →', 830, 119, 100);
  button('start_node', '1  Controllerを開始 / Start', 25, 172, 250);
  button('open_bundled', '2  同梱バンク / Load bundled bank', 290, 172, 295);
  button('open_bank', '別バンクを開く / Other bank', 600, 172, 225);
  button('stop_node', 'Controller停止', 840, 172, 130);
  obj('node', 'node.script method-comparison-entry.js @autostart 0 @watch 0', 1, 2);
  msg('script_start', 'script start'); msg('script_stop', 'script stop');
  wire('start_node', 'script_start'); wire('script_start', 'node');
  msg('load_bundled', 'load_bundled'); wire('open_bundled', 'zero'); wire('open_bundled', 'load_bundled'); wire('load_bundled', 'node');
  wire('stop_node', 'zero'); wire('stop_node', 'script_stop'); wire('script_stop', 'node');
  obj('dialog', 'opendialog'); obj('native_path', 'conformpath slash boot'); obj('load_bank', 'prepend load');
  wire('open_bank', 'zero'); wire('open_bank', 'dialog'); wire('dialog', 'native_path');
  wire('native_path', 'load_bank'); wire('load_bank', 'node');
  note('status_display', 'Controller stopped / 音声出力は停止中', 25, 217, 950, 48, 14);
  obj('status_prepend', 'prepend set'); wire('status_prepend', 'status_display');
  obj('route', 'route ready mute status duration buffer weights decoder menu selected alive', 1, 11);
  wire('node', 'route');
  wire('route', 'status_prepend', 2);
  obj('node_print', 'print ADEPS-comparison-node'); wire('node', 'node_print', 1);

  note('section', '3  再生方式 / Reconstruction method', 25, 278, 950, 32, 19);
  box('method', 'umenu', null, 1, 3, [25, 320, 945, 32], {items: METHODS.flatMap((name, i) => i ? [',', name] : [name])});
  obj('select_index', 'prepend select_index'); wire('method', 'select_index'); wire('select_index', 'node');
  wire('route', 'method', 7);
  note('selected_display', 'No bank loaded', 25, 362, 945, 42, 17);
  obj('selected_prepend', 'prepend set'); wire('route', 'selected_prepend', 8); wire('selected_prepend', 'selected_display');
  note('selection_note', '方式選択だけでは再生しません。再生中は位置を保持して50msで切替えます。/ Selection keeps the shared playhead.', 25, 411, 945, 42);

  box('run', 'toggle', null, 1, 1, [25, 474, 35, 35]);
  note('run_note', '4  LOOP RUN（手動）', 73, 477, 250);
  box('master_gain', 'flonum', null, 1, 2, [370, 474, 110, 35], {minimum: 0, maximum: 1, format: 6});
  note('gain_note', '5  共通音量 0–1 / Shared gain', 496, 477, 475);
  note('play_note', 'RUN → MaxのAudio Statusで出力先確認 → DSP → 音量を少しずつ上げる。停止後は再度音量を設定。', 25, 523, 945, 40);
  note('loop_note', '全方式を同時に読み、選択分だけ出力。末尾250ms無音、外端5ms共通フェード。短片は0.248秒の検証例です。', 25, 563, 945, 40);
  note('output_note', '出力1–12＝保存プロジェクトID順。物理/Dante番号は別途照合。11/12は以前の画面記録と逆のため確認。', 25, 612, 945, 42);
  note('scope_note', '同じ合成観測からの保存済み比較。現地の新録音を推定する処理ではありません。AFCの既存入力にはそのまま接続しないでください。', 25, 657, 945, 42);
  note('meter_note', 'デコード後（共通音量適用済み）/ Decoded output levels', 25, 705, 945, 25);
  for (let i = 0; i < 12; i++) {
    box(`meter${i}`, 'meter~', null, 1, 1, [25 + i * 79, 740, 68, 14]);
    note(`meterlabel${i}`, `S${i + 1}`, 25 + i * 79, 757, 68, 24, 11);
  }

  // The patch's local stop path remains operational if Node stops responding.
  msg('zero', '0'); obj('initial_zero', 'loadmess 0');
  wire('initial_zero', 'zero'); wire('stop_all', 'zero'); wire('route', 'zero', 1);
  wire('zero', 'run'); wire('zero', 'master_gain');
  obj('not_ready', 'sel 0', 1, 2); wire('route', 'not_ready', 0); wire('not_ready', 'zero');
  obj('ready_gate', 'gate 1 0', 2); wire('route', 'ready_gate', 0, 0); wire('run', 'ready_gate', 0, 1);
  obj('run_stopped', 'sel 0', 1, 2); msg('gain_zero', '0'); wire('run', 'run_stopped'); wire('run_stopped', 'gain_zero'); wire('gain_zero', 'master_gain');
  obj('watchdog_order', 't b b', 1, 2); msg('watchdog_cancel', 'stop'); obj('watchdog', 'delay 1500');
  wire('route', 'watchdog_order', 9); wire('watchdog_order', 'watchdog_cancel', 1); wire('watchdog_cancel', 'watchdog');
  wire('watchdog_order', 'watchdog'); wire('watchdog', 'zero');
  msg('watchdog_not_ready', '0'); wire('watchdog', 'watchdog_not_ready'); wire('watchdog_not_ready', 'ready_gate');
  msg('watchdog_error', 'set Controller heartbeat lost / STOPPED'); wire('watchdog', 'watchdog_error'); wire('watchdog_error', 'status_display');

  // A single ms-valued signal drives all ten play~ objects: no independent clocks.
  obj('period', '+ 250.', 2); obj('frequency', 'expr 1000. / $f1'); obj('running_frequency', '* 0.', 2);
  obj('phasor', 'phasor~ 0. @phaseoffset 0.', 2); obj('position_ms', '*~ 1.', 2);
  wire('route', 'period', 3); wire('period', 'frequency'); wire('frequency', 'running_frequency', 0, 1);
  obj('run_order', 't i i', 1, 2); obj('restart_select', 'sel 1', 1, 2); msg('restart_phase', '0.');
  wire('ready_gate', 'run_order'); wire('run_order', 'restart_select', 1);
  wire('restart_select', 'restart_phase'); wire('restart_phase', 'phasor', 0, 1);
  wire('run_order', 'running_frequency'); wire('running_frequency', 'phasor'); wire('phasor', 'position_ms'); wire('period', 'position_ms', 0, 1);
  // STOP gates the frozen position to zero. A manual RUN starts every bank at zero.
  obj('run_ramp', 'pack 0. 10', 2); obj('run_signal', 'line~ 0.', 2, 2);
  wire('ready_gate', 'run_ramp'); wire('run_ramp', 'run_signal');
  wire('zero', 'run_ramp'); wire('zero', 'running_frequency');
  obj('fade_in', '/~ 5.', 2); obj('remaining_ms', '!-~ 0.', 2); obj('fade_out', '/~ 5.', 2);
  obj('fade_minimum', 'minimum~', 2); obj('envelope', 'clip~ 0. 1.', 3);
  wire('position_ms', 'fade_in'); wire('position_ms', 'remaining_ms'); wire('route', 'remaining_ms', 3, 1);
  wire('remaining_ms', 'fade_out'); wire('fade_in', 'fade_minimum'); wire('fade_out', 'fade_minimum', 0, 1);
  wire('fade_minimum', 'envelope');
  obj('gain_clip', 'clip 0. 1.', 3); obj('gain_pack', 'pack 0. 100', 2); obj('gain_signal', 'line~ 0.', 2, 2);
  wire('master_gain', 'gain_clip'); wire('gain_clip', 'gain_pack'); wire('gain_pack', 'gain_signal');
  obj('envelope_run', '*~ 0.', 2); obj('master_signal', '*~ 0.', 2);
  wire('envelope', 'envelope_run'); wire('run_signal', 'envelope_run', 0, 1);
  wire('envelope_run', 'master_signal'); wire('gain_signal', 'master_signal', 0, 1);
  obj('buffer_route', `route ${METHODS.map((_, i) => i).join(' ')}`, 1, 11); wire('route', 'buffer_route', 4);
  obj('weights', `unpack ${METHODS.map(() => '0.').join(' ')}`, 1, 10); wire('route', 'weights', 5);
  obj('buffer_confirm', 'js method-comparison-buffer.js #0'); wire('buffer_confirm', 'node');
  for (let i = 0; i < 10; i++) {
    obj(`buffer${i}`, `buffer~ #0-cmp-${i} 0 4`, 1, 2);
    obj(`play${i}`, `play~ #0-cmp-${i} 4`, 1, 5);
    wire('buffer_route', `buffer${i}`, i); wire('position_ms', `play${i}`);
    msg(`loaded${i}`, `loaded ${i}`); wire(`buffer${i}`, `loaded${i}`, 1); wire(`loaded${i}`, 'buffer_confirm');
    obj(`weight_pack${i}`, 'pack 0. 50', 2); obj(`weight${i}`, 'line~ 0.', 2, 2);
    wire('weights', `weight_pack${i}`, i); wire(`weight_pack${i}`, `weight${i}`);
    for (let ch = 0; ch < 4; ch++) {
      obj(`weighted${i}_${ch}`, '*~ 0.', 2); wire(`play${i}`, `weighted${i}_${ch}`, ch);
      wire(`weight${i}`, `weighted${i}_${ch}`, 0, 1);
    }
  }
  obj('decoder', 'matrix~ 4 12 0. @ramp 50', 4, 13); wire('route', 'decoder', 6);
  obj('dac', 'dac~ 1 2 3 4 5 6 7 8 9 10 11 12', 12, 0);
  for (let ch = 0; ch < 4; ch++) {
    obj(`sum${ch}`, '+~ 0.', 2); obj(`foa${ch}`, '*~ 0.', 2);
    for (let i = 0; i < 10; i++) wire(`weighted${i}_${ch}`, `sum${ch}`);
    wire(`sum${ch}`, `foa${ch}`); wire('master_signal', `foa${ch}`, 0, 1); wire(`foa${ch}`, 'decoder', 0, ch);
  }
  for (let ch = 0; ch < 12; ch++) {wire('decoder', 'dac', ch, ch); wire('decoder', `meter${ch}`, ch);}
  return {patcher: {fileversion: 1, appversion: {major: 9, minor: 0, revision: 0, architecture: 'x64', modernui: 1},
    classnamespace: 'box', rect: [80, 70, 1020, 815], openinpresentation: 1, default_fontname: 'Yu Mincho',
    default_fontsize: 12, bgcolor: [.045, .045, .045, 1], boxes, lines}};
}
if (require.main === module) fs.writeFileSync(path.join(__dirname, 'ADEPS_Method_Comparison.maxpat'), JSON.stringify(buildPatch(), null, 2) + '\n');
module.exports = {buildPatch};
