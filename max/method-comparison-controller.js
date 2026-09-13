'use strict';
const path = require('node:path');
const {loadBank, METHODS} = require('./method-comparison-bank');
const {createComparisonServer} = require('./method-comparison-server');

// Kept independent of max-api so the complete state machine can be tested on CPU.
class ComparisonController {
  constructor(outlet, {bankLoader = loadBank, timeoutMs = 10000} = {}) {
    this.outlet = outlet; this.bankLoader = bankLoader; this.timeoutMs = timeoutMs;
    this.bank = null; this.ready = false; this.loading = false; this.selected = ''; this.pending = null;
    this.selectionQueue = Promise.resolve();
  }
  status() {return {ready: this.ready, selected: this.selected, input_sha256: this.bank?.input_sha256 || ''};}
  async mute() {await this.outlet('mute');}
  async reset() {
    this.ready = false; this.selected = '';
    await this.outlet('ready', 0); await this.mute(); await this.outlet('selected', 'No bank loaded');
  }
  async load(filename) {
    if (this.loading) throw new Error('A bank is already loading');
    this.loading = true;
    try {
      await this.reset(); this.bank = null;
      const bank = await this.bankLoader(filename);
      this.bank = bank;
      await this.outlet('menu', 'clear');
      for (const method of bank.methods) await this.outlet('menu', 'append', method.label);
      await this.outlet('decoder', 'clear');
      for (let output = 0; output < 12; output++) for (let input = 0; input < 4; input++)
        await this.outlet('decoder', input, output, bank.decoder.matrix[output][input], 0);
      await this.outlet('duration', bank.samples / bank.sample_rate_hz * 1000);
      for (let index = 0; index < bank.methods.length; index++) {
        await new Promise((resolve, reject) => {
          const timer = setTimeout(() => {
            this.pending = null; reject(new Error(`Max buffer ${index + 1} did not confirm loading`));
          }, this.timeoutMs);
          this.pending = {index, resolve: () => {clearTimeout(timer); this.pending = null; resolve();},
            reject: error => {clearTimeout(timer); this.pending = null; reject(error);}};
          Promise.resolve(this.outlet('buffer', index, 'replace', bank.methods[index].absolute_file))
            .catch(error => this.pending?.reject(error));
        });
        await this.outlet('status', `Verified buffer ${index + 1}/10: ${bank.methods[index].label}`);
      }
      this.ready = true;
      await this.select('linear_tuned');
      await this.outlet('ready', 1);
      await this.outlet('status', `READY / ${bank.samples} samples / N3D / shared gain already in WAVs`);
    } catch (error) {
      this.bank = null; await this.reset(); throw error;
    } finally {this.loading = false;}
  }
  bufferLoaded(index, channels, frames, milliseconds) {
    const pending = this.pending;
    if (!pending || pending.index !== index) return;
    if (channels !== 4 || frames !== this.bank.samples || !Number.isFinite(milliseconds) ||
      Math.abs(milliseconds - frames / 16) > 0.01) {
      pending.reject(new Error('Loaded Max buffer shape/rate differs from the verified WAV')); return;
    }
    pending.resolve();
  }
  select(id, expectedHash = null) {
    const perform = async () => {
      if (!this.ready || !METHODS.includes(id)) throw new Error('Bank not ready or unknown method');
      if (expectedHash !== null && this.bank.input_sha256 !== expectedHash) throw new Error('Loaded bank input hash changed');
      const index = METHODS.indexOf(id);
      // One list arrives in one Max scheduler event. All ten line~ ramps share 50 ms.
      await this.outlet('weights', ...METHODS.map((_, i) => i === index ? 1 : 0));
      this.selected = id;
      await this.outlet('menu', 'set', index);
      await this.outlet('selected', this.bank.methods[index].label);
    };
    const action = this.selectionQueue.then(perform);
    this.selectionQueue = action.catch(() => {});
    return action;
  }
}

async function main() {
  const Max = require('max-api');
  const controller = new ComparisonController((...args) => Max.outlet(...args));
  const error = async value => {await controller.mute(); await Max.outlet('status', `ERROR: ${value.message}`); Max.post(value.message);};
  await controller.reset();
  Max.addHandler('load', filename => controller.load(filename).catch(error));
  Max.addHandler('load_bundled', () => controller.load(path.resolve(__dirname, '../max-comparison.json')).catch(error));
  Max.addHandler('loaded', (...args) => controller.bufferLoaded(...args));
  Max.addHandler('select_index', index => controller.select(METHODS[index]).catch(error));
  Max.addHandler('mute', () => controller.mute());
  const server = await createComparisonServer({status: () => controller.status(),
    onSelect: (id, expectedHash) => controller.select(id, expectedHash), onMute: () => controller.mute(), onError: value => Max.post(value.message)});
  await Max.outlet('status', `Controller listening on 127.0.0.1:${server.port}; load max-comparison.json`);
  const heartbeat = setInterval(() => Max.outlet('alive'), 250);
  const shutdown = async () => {clearInterval(heartbeat); await controller.reset(); await server.close(); process.exit(0);};
  process.once('SIGTERM', shutdown); process.once('SIGINT', shutdown);
}
module.exports = {ComparisonController, start: main};
