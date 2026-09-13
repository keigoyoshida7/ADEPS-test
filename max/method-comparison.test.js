'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const dgram = require('node:dgram');
const vm = require('node:vm');
const {METHODS, sha256, inspectWav, validateManifest, loadBank} = require('./method-comparison-bank');
const {ComparisonController} = require('./method-comparison-controller');
const {command, createComparisonServer} = require('./method-comparison-server');
const {encode, decode} = require('./osc-codec');
const {buildPatch} = require('./build-method-comparison-patch');

function wav(frames = 32) {
  const b = Buffer.alloc(44 + frames * 16);
  b.write('RIFF'); b.writeUInt32LE(b.length - 8, 4); b.write('WAVEfmt ', 8);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(3, 20); b.writeUInt16LE(4, 22);
  b.writeUInt32LE(16000, 24); b.writeUInt32LE(256000, 28); b.writeUInt16LE(16, 32); b.writeUInt16LE(32, 34);
  b.write('data', 36); b.writeUInt32LE(frames * 16, 40);
  for (let i = 44; i < b.length; i += 4) b.writeFloatLE(Math.sin(i) * .2, i);
  return b;
}
function manifest() {
  return {schema: 'adeps-max-method-bank/1', sample_rate_hz: 16000, samples: 32,
    channel_order: ['W', 'Y', 'Z', 'X'], normalization: 'N3D', shared_gain: 2,
    input_sha256: 'a'.repeat(64), methods: METHODS.map(id => ({id, label: id,
      file: `foa/${id}_FOA_ACN_N3D.wav`, sha256: sha256(wav()), absolute_file: `/fixture/${id}.wav`})),
    decoder: {normalization: 'N3D', matrix: Array.from({length: 12}, () => [.1, .2, -.1, 0])}};
}
async function fixture(t) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'adeps-max-bank-'));
  t.after(() => fs.rm(dir, {recursive: true, force: true}));
  await fs.mkdir(path.join(dir, 'foa'));
  const m = manifest();
  for (const item of m.methods) await fs.writeFile(path.join(dir, item.file), wav());
  const file = path.join(dir, 'max-comparison.json'); await fs.writeFile(file, JSON.stringify(m));
  return {dir, file, m};
}

test('WAV parser verifies channels, finite samples, exact RIFF length and actual frames', () => {
  const good = wav(); assert.equal(inspectWav(good).samples, 32);
  const channels = Buffer.from(good); channels.writeUInt16LE(2, 22); assert.throws(() => inspectWav(channels), /4 channels/);
  const invalid = Buffer.from(good); invalid.writeFloatLE(NaN, 44); assert.throws(() => inspectWav(invalid), /Nonfinite/);
  assert.throws(() => inspectWav(good.subarray(0, good.length - 1)), /complete/);
});
test('Manifest rejects duplicate methods, wrong normalization, traversal and malformed decoder', () => {
  const m = manifest(); assert.equal(validateManifest(m).methods.length, 10);
  assert.throws(() => validateManifest({...m, normalization: 'SN3D'}));
  const duplicate = structuredClone(m); duplicate.methods[0] = duplicate.methods[1]; assert.throws(() => validateManifest(duplicate));
  const traversal = structuredClone(m); traversal.methods[0].file = '../reference.wav'; assert.throws(() => validateManifest(traversal));
  const badD = structuredClone(m); badD.decoder.matrix[0][1] = NaN; assert.throws(() => validateManifest(badD));
  const shuffled = {...m, methods: [...m.methods].reverse()}; assert.deepEqual(validateManifest(shuffled).methods.map(x => x.id), METHODS);
});
test('Disk bank verifies all ten WAV hashes and lengths; corruption is rejected', async t => {
  const {dir, file, m} = await fixture(t);
  const bank = await loadBank(file); assert.equal(bank.samples, 32); assert.equal(bank.methods.length, 10);
  assert.equal(bank.manifest_sha256, sha256(await fs.readFile(file)));
  await fs.writeFile(path.join(dir, m.methods[9].file), wav(33));
  await assert.rejects(loadBank(file), /SHA256 mismatch/);
});
test('Resolved WAV symlinks cannot escape the selected bank directory', async t => {
  const {dir, file, m} = await fixture(t);
  const outside = path.join(os.tmpdir(), `adeps-outside-${process.pid}.wav`);
  await fs.writeFile(outside, wav()); t.after(() => fs.rm(outside, {force: true}));
  const target = path.join(dir, m.methods[0].file); await fs.unlink(target); await fs.symlink(outside, target);
  await assert.rejects(loadBank(file), /inside the bank/);
});
test('Controller waits for all actual Max buffer confirmations and does not start audio', async () => {
  const events = []; let c;
  c = new ComparisonController(async (...event) => {
    events.push(event);
    if (event[0] === 'buffer') {
      assert.equal(c.ready, false);
      queueMicrotask(() => c.bufferLoaded(event[1], 4, 32, 2));
    }
  }, {bankLoader: async () => manifest()});
  await c.load('/fixture/max-comparison.json');
  assert.equal(c.status().ready, true); assert.equal(c.status().selected, 'linear_tuned');
  assert.equal(events.filter(e => e[0] === 'buffer').length, 10);
  assert.equal(events.filter(e => e[0] === 'decoder' && e.length === 5).length, 48);
  assert.ok(events.findIndex(e => e[0] === 'mute') < events.findIndex(e => e[0] === 'buffer'));
  assert.equal(events.some(e => ['gain', 'run', 'dsp', 'start'].includes(e[0])), false);
  const before = events.length; await c.select('plus', 'a'.repeat(64));
  assert.deepEqual(events[before], ['weights', 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]);
  assert.equal(events.slice(before).some(e => ['duration', 'buffer', 'mute'].includes(e[0])), false);
  await assert.rejects(c.select('plus_no_denoiser', 'b'.repeat(64)), /hash changed/);
  assert.equal(c.selected, 'plus');
});
test('A Max shape mismatch and missing completion stay unready and muted', async () => {
  let c; const events = [];
  c = new ComparisonController(async (...event) => {events.push(event);
    if (event[0] === 'buffer') queueMicrotask(() => c.bufferLoaded(event[1], 2, 32, 2));
  }, {bankLoader: async () => manifest()});
  await assert.rejects(c.load('/fixture/m.json'), /shape\/rate/);
  assert.equal(c.ready, false); assert.equal(c.bank, null); assert.ok(events.filter(e => e[0] === 'mute').length >= 2);
  const c2 = new ComparisonController(async () => {}, {bankLoader: async () => manifest(), timeoutMs: 10});
  await assert.rejects(c2.load('/fixture/m.json'), /did not confirm/); assert.equal(c2.ready, false);
});
test('Network command whitelist has no start, gain or unmute and requires bank hash', () => {
  assert.deepEqual(command(decode(encode('/adeps-compare/mute'))), {action: 'mute'});
  assert.equal(command(decode(encode('/adeps-compare/select', ['plus', 'a'.repeat(64)]))).value, 'plus');
  for (const [address, args] of [['/adeps-compare/start', []], ['/adeps-compare/gain', [1]],
    ['/adeps-compare/select', ['plus']], ['/adeps-compare/select', ['unknown', 'a'.repeat(64)]],
    ['/adeps-compare/mute', [0]]]) assert.throws(() => command(decode(encode(address, args))));
});
test('Loopback status/ACKs report exact loaded bank; wrong bank cannot select', async t => {
  const client = dgram.createSocket('udp4');
  await new Promise(resolve => client.bind(0, '127.0.0.1', resolve));
  let state = {ready: false, selected: '', input_sha256: ''}, selected = 0, mutes = 0;
  const server = await createComparisonServer({listenPort: 0, replyPort: client.address().port,
    status: () => state, onSelect: async id => {selected++; state.selected = id;}, onMute: async () => {mutes++;}});
  t.after(async () => {await server.close(); client.close();});
  const request = (address, args = []) => new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('UDP response timeout')), 1000);
    client.once('message', data => {clearTimeout(timeout); resolve(decode(data));});
    client.send(encode(address, args), server.port, '127.0.0.1');
  });
  assert.deepEqual((await request('/adeps-compare/ping', [37])).args, [37, 0, '', '']);
  assert.equal((await request('/adeps-compare/select', ['plus', 'a'.repeat(64)])).address, '/adeps-compare/error');
  state = {ready: true, selected: 'linear_tuned', input_sha256: 'a'.repeat(64)};
  assert.equal((await request('/adeps-compare/select', ['plus', 'b'.repeat(64)])).address, '/adeps-compare/error');
  assert.equal(selected, 0);
  assert.deepEqual((await request('/adeps-compare/select', ['plus', 'a'.repeat(64)])).args, ['select', 'plus', 'a'.repeat(64)]);
  assert.deepEqual((await request('/adeps-compare/ping', [38])).args, [38, 1, 'plus', 'a'.repeat(64)]);
  assert.equal((await request('/adeps-compare/mute')).address, '/adeps-compare/ack'); assert.equal(mutes, 1);
});
test('Generated graph uses one playhead, ten 4ch readers, common gain and manual DSP', () => {
  const p = buildPatch().patcher, byId = Object.fromEntries(p.boxes.map(({box}) => [box.id, box]));
  assert.equal(p.boxes.filter(({box}) => box.text?.startsWith('phasor~')).length, 1);
  assert.equal(p.boxes.filter(({box}) => box.text?.startsWith('play~')).length, 10);
  const edges = (a, b) => p.lines.some(({patchline: l}) => l.source[0] === a && l.destination[0] === b);
  for (let i = 0; i < 10; i++) assert.ok(edges('position_ms', `play${i}`));
  for (let c = 0; c < 4; c++) assert.ok(edges('master_signal', `foa${c}`));
  assert.ok(edges('initial_zero', 'zero')); assert.ok(edges('stop_all', 'zero')); assert.ok(edges('watchdog', 'zero'));
  assert.ok(byId.node.text.includes('@autostart 0'));
  assert.ok(byId.node.text.includes('method-comparison-entry.js'));
  assert.ok(edges('open_bundled', 'load_bundled')); assert.ok(edges('load_bundled', 'node'));
  assert.equal(p.lines.some(({patchline: l}) => l.source[0] === 'initial_zero' && l.destination[0] === 'load_bundled'), false);
  assert.equal(p.boxes.some(({box}) => box.text?.startsWith('expr~')), false);
  assert.equal(byId.fade_minimum.text, 'minimum~');
  assert.equal(byId.envelope.text, 'clip~ 0. 1.');
  assert.equal(p.lines.some(({patchline: l}) => l.destination[0] === 'dsp'), false);
  assert.equal(byId.decoder.text, 'matrix~ 4 12 0. @ramp 50');
  assert.equal(byId.master_gain.minimum, 0); assert.equal(byId.master_gain.maximum, 1);
  assert.equal(byId.gain_clip.text, 'clip 0. 1.');
  for (const {patchline: l} of p.lines) {
    assert.ok(byId[l.source[0]], `unknown source ${l.source[0]}`); assert.ok(byId[l.destination[0]]);
    assert.ok(l.source[1] < byId[l.source[0]].numoutlets); assert.ok(l.destination[1] < byId[l.destination[0]].numinlets);
  }
});
test('Method ramps form a convex mix even when selections interrupt an earlier fade', () => {
  let weights = Array(10).fill(0); weights[2] = 1;
  for (const selected of [8, 9, 0, 4, 2]) {
    const next = weights.map((x, i) => x * .65 + (i === selected ? .35 : 0));
    assert.ok(Math.abs(next.reduce((a, b) => a + b) - 1) < 1e-12);
    assert.ok(next.every(x => x >= 0 && x <= 1)); weights = next;
  }
});
test('Node-for-Max wrapper starts the separate entry point even when require.main differs', async () => {
  const source = await fs.readFile(path.join(__dirname, 'method-comparison-entry.js'), 'utf8');
  let started = 0;
  const requireStub = name => {
    if (name === 'max-api') return {outlet: async () => {}, post: () => {}};
    if (name === './method-comparison-controller') return {start: async () => {started++;}};
    throw new Error(`Unexpected import ${name}`);
  };
  requireStub.main = {id: 'node-for-max-wrapper'};
  vm.runInNewContext(source, {require: requireStub, module: {id: 'required-user-script'}});
  assert.equal(started, 1);
});
