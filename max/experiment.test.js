'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {buildPatch} = require('./build-experiment-patch');
const patch = buildPatch().patcher;
const boxes = new Map(patch.boxes.map(x => [x.box.id, x.box]));
const edges = patch.lines.map(x => x.patchline);
const edge = (a, b, ao = 0, bi = 0) => edges.some(e => e.source[0] === a && e.source[1] === ao && e.destination[0] === b && e.destination[1] === bi);

// Deterministic control-event interpreter for the subset that governs transport,
// mute and recorder arming. This does not emulate MSP DSP or a hardware driver.
function controls() {
  const state = new Map(), events = [];
  let budget = 10000;
  function out(id, outlet, value) {
    for (const e of edges.filter(x => x.source[0] === id && x.source[1] === outlet)
      .sort((a, b) => (a.order || 0) - (b.order || 0))) send(e.destination[0], value, e.destination[1]);
  }
  function send(id, value = 'bang', inlet = 0) {
    assert.ok(--budget > 0, 'control cycle did not terminate');
    const b = boxes.get(id), text = b.text || '', tokens = text.split(' ');
    events.push([id, inlet, value]);
    if (b.maxclass === 'message') {
      if (typeof value === 'string' && value.startsWith('set ')) return;
      const n = Number(text); out(id, 0, text.trim() !== '' && Number.isFinite(n) ? n : text); return;
    }
    if (['toggle', 'number', 'flonum'].includes(b.maxclass)) {
      state.set(id, value); out(id, 0, value); return;
    }
    if (b.maxclass === 'textbutton') {out(id, 0, 'bang'); return;}
    if (tokens[0] === 't') {
      for (let i = tokens.length - 1; i >= 1; i--) out(id, i - 1, tokens[i] === 'b' ? 'bang' : value);
      return;
    }
    if (tokens[0] === 'sel') {out(id, Number(value) === Number(tokens[1]) ? 0 : 1, Number(value) === Number(tokens[1]) ? 'bang' : value); return;}
    if (tokens[0] === '==') {out(id, 0, Number(value) === Number(tokens[1]) ? 1 : 0); return;}
    if (tokens[0] === 'gate') {
      if (!state.has(id)) state.set(id, Number(tokens[2] || 0));
      if (inlet === 0) state.set(id, Number(value));
      else if (state.get(id)) out(id, 0, value);
      return;
    }
    if (tokens[0] === 'onebang') {
      if (!state.has(id)) state.set(id, Number(tokens[1] || 0));
      if (inlet === 1) state.set(id, 1);
      else if (state.get(id)) {state.set(id, 0); out(id, 0, 'bang');}
      return;
    }
    if (tokens[0] === 'clip') {out(id, 0, Math.max(Number(tokens[1]), Math.min(Number(tokens[2]), Number(value)))); return;}
    if (tokens[0] === 'pack') {out(id, 0, [value, Number(tokens[2])]); return;}
    if (tokens[0] === 'prepend') {out(id, 0, tokens[1] + ' ' + value); return;}
    if (tokens[0] === 'append') {out(id, 0, value + ' ' + tokens[1]); return;}
    if (tokens[0] === 'sfplay~') {
      if (typeof value === 'number') {
        state.set(id, value !== 0);
        // Include the documented halt bang; this catches accidental 0/bang recursion.
        if (!value) out(id, Number(tokens[1]), 'bang');
      }
      return;
    }
    if (tokens[0] === 'sfrecord~' || tokens[0] === 'line~' || tokens[0] === 'gate~') state.set(id, value);
  }
  return {send, state, events};
}

test('generated artifact is reproducible and all declared connections resolve', () => {
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(__dirname, 'ADEPS_Experiment.maxpat'), 'utf8')), {patcher: patch});
  assert.equal(boxes.size, patch.boxes.length, 'duplicate object id');
  const signatures = new Set();
  for (const e of edges) {
    assert.ok(boxes.has(e.source[0]) && boxes.has(e.destination[0]));
    assert.ok(e.source[1] >= 0 && e.source[1] < boxes.get(e.source[0]).numoutlets);
    assert.ok(e.destination[1] >= 0 && e.destination[1] < boxes.get(e.destination[0]).numinlets);
    const key = JSON.stringify([e.source, e.destination]);
    assert.ok(!signatures.has(key), 'duplicate patch cord ' + key); signatures.add(key);
  }
});

test('no startup audio, network objects, runtime JS, or automatic DSP path', () => {
  assert.equal(boxes.get('initial_zero').text, 'loadmess 0');
  assert.equal(boxes.get('source_select').text, 'selector~ 4 0');
  assert.equal(boxes.get('output_gate').text, 'gate~ 12 0');
  assert.equal(boxes.get('output_amp').text, '*~ 0.');
  assert.ok(!edges.some(e => e.destination[0] === 'dsp'));
  assert.ok(!patch.boxes.some(({box}) => /^(node\.script|js |udpsend|udpreceive|net\.send|loadmess 1|loadmess start)/.test(box.text || '')));
  const sim = controls(); sim.send('zero');
  for (const id of ['output_channel', 'output_gain', 'ab_gain', 'source_run']) assert.equal(Number(sim.state.get(id)), 0);
  for (const id of ['source_file', 'linear_player', 'enhanced_player']) assert.equal(sim.state.get(id), false);
});

test('physical outputs carry only gated bounded mono source; FOA never reaches a DAC', () => {
  assert.equal(boxes.get('output_gain_clip').text, 'clip 0. 0.03');
  assert.equal(boxes.get('ab_gain_clip').text, 'clip 0. 0.03');
  assert.ok(edge('source_gated', 'output_amp') && edge('output_gain_signal', 'output_amp', 0, 1));
  const dacEdges = edges.filter(e => e.destination[0] === 'output_dac');
  assert.equal(dacEdges.length, 12);
  for (let i = 0; i < 12; i++) assert.ok(edge('output_gate', 'output_dac', i, i));
  for (const ch of ['W', 'Y', 'Z', 'X']) {
    assert.equal(boxes.get('ab_send_' + ch).text, 'send~ adeps-experiment.' + ch);
    assert.ok(edge('ab_gain_signal', 'ab_gain_' + ch, 0, 1));
    assert.deepEqual(edges.filter(e => e.source[0] === 'ab_gain_' + ch).map(e => e.destination[0]), ['ab_send_' + ch]);
  }
  const sim = controls(); sim.send('output_gain', .03); sim.send('output_channel', 7);
  assert.equal(sim.state.get('output_gain_signal'), 0);
  const lastGainZero = sim.events.findIndex(e => e[0] === 'output_gain_signal' && e[2] === 0);
  const gateSeven = sim.events.findIndex(e => e[0] === 'output_gate' && e[2] === 7);
  assert.ok(lastGainZero >= 0 && gateSeven > lastGainZero, 'mute must precede a new output');
});

test('raw19 recording is one multichannel file with unprocessed ordered ADC channels', () => {
  assert.equal(boxes.get('array_capture_recorder').text, 'sfrecord~ 19');
  assert.equal(boxes.get('array_adc').text, 'adc~ ' + Array.from({length: 19}, (_, i) => i + 1).join(' '));
  for (let i = 0; i < 19; i++) assert.ok(edge('array_adc', 'array_capture_recorder', i, i));
  assert.ok(edge('source_gated', 'source_capture_recorder'));
  assert.ok(!edge('output_amp', 'source_capture_recorder'), 'reference source must not depend on speaker gain');
  assert.equal(boxes.get('samptype_init').text, 'loadmess samptype int24');
  const sim = controls(); sim.send('source_capture_start');
  assert.ok(!sim.events.some(e => e[0] === 'source_capture_recorder' && e[2] === 1), 'choose a file first');
  sim.send('source_capture_path_order', '/tmp/source.wav'); sim.send('source_capture_start');
  assert.equal(sim.state.get('source_capture_recorder'), 1);
  sim.send('source_capture_stop'); sim.send('source_capture_start');
  assert.equal(sim.state.get('source_capture_recorder'), 0, 'stop closes the file, so restart requires another chosen path');
});

test('A/B starts both at the beginning, switches weights without restarting, and stops together', () => {
  const sim = controls(); sim.send('zero'); sim.send('ab_start');
  assert.equal(sim.state.get('linear_player'), true); assert.equal(sim.state.get('enhanced_player'), true);
  const n = sim.events.length; sim.send('ab_mix', 1);
  assert.ok(!sim.events.slice(n).some(e => /_player$/.test(e[0])), 'A/B switching must not reset transport');
  assert.deepEqual(sim.state.get('ab_mix_signal'), [1, 20]);
  sim.send('ab_eof_once');
  assert.equal(sim.state.get('linear_player'), false); assert.equal(sim.state.get('enhanced_player'), false);
  sim.send('ab_start'); sim.send('ab_stop');
  assert.equal(sim.state.get('linear_player'), false); assert.equal(sim.state.get('enhanced_player'), false);
});

test('file selection and STOP avoid halt/EOF feedback loops and never start another source', () => {
  const sim = controls(); sim.send('source_mode', 1); sim.send('mode_change', 1);
  sim.send('source_run', 1); assert.equal(sim.state.get('source_file'), true);
  sim.send('source_stop'); assert.equal(sim.state.get('source_file'), false);
  sim.send('source_run', 1); sim.send('mode_change', 2);
  assert.equal(sim.state.get('source_file'), false); assert.equal(sim.state.get('source_run'), 0);
  sim.send('source_run', 1); assert.equal(sim.state.get('source_file'), false, 'pink mode cannot start the file');
  sim.send('zero'); assert.equal(sim.state.get('source_run'), 0);
});

test('sweep is logarithmic over 8s, limited to audible test band, with finite fades', () => {
  assert.equal(boxes.get('sweep_ramp').text, '0., 1. 8000');
  const expression = boxes.get('sweep_hz').text.replace('expr~ ', '').replace('$v1', 'phase').replace('exp(', 'Math.exp(');
  const hz = new Function('phase', 'return ' + expression);
  assert.ok(Math.abs(hz(0) - 20) < 1e-9); assert.ok(Math.abs(hz(1) - 20000) < 1e-7);
  assert.ok(Math.abs(hz(.5) - Math.sqrt(20 * 20000)) < 1e-7);
  assert.equal(boxes.get('sweep_envelope').text, '0., 1. 20 1. 7960 0. 20');
  assert.equal(boxes.get('burst_envelope').text, '0., 1. 10 1. 80 0. 10');
  for (const id of ['sweep_env', 'burst_env']) assert.ok(edge('source_stop', id) && edge('zero', id));
});
