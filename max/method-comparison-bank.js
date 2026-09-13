'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const {createHash} = require('node:crypto');

const METHODS = Object.freeze(['reference', 'linear_default', 'linear_tuned', 'linear_noise',
  'adeps_current', 'adeps_tuned', 'spatial_only', 'consistency_only', 'plus', 'plus_no_denoiser']);
const SHA = /^[a-f0-9]{64}$/;
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const finite = value => typeof value === 'number' && Number.isFinite(value);

// Validate the audio actually loaded by Max, not just the manifest's declarations.
function inspectWav(bytes) {
  if (bytes.length < 44 || bytes.toString('ascii', 0, 4) !== 'RIFF' ||
      bytes.toString('ascii', 8, 12) !== 'WAVE' || bytes.readUInt32LE(4) + 8 !== bytes.length)
    throw new Error('Expected a complete RIFF/WAVE file');
  let fmt, audio;
  for (let pos = 12; pos < bytes.length;) {
    if (pos + 8 > bytes.length) throw new Error('Truncated WAV chunk');
    const id = bytes.toString('ascii', pos, pos + 4), length = bytes.readUInt32LE(pos + 4);
    const start = pos + 8, end = start + length;
    if (end > bytes.length) throw new Error('Truncated WAV payload');
    if (id === 'fmt ') { if (fmt) throw new Error('Duplicate fmt chunk'); fmt = bytes.subarray(start, end); }
    if (id === 'data') { if (audio) throw new Error('Duplicate data chunk'); audio = bytes.subarray(start, end); }
    pos = end + (length % 2);
  }
  if (!fmt || fmt.length < 16 || !audio) throw new Error('Missing WAV format/data');
  const format = fmt.readUInt16LE(0), channels = fmt.readUInt16LE(2), sampleRate = fmt.readUInt32LE(4);
  if (format !== 3 || channels !== 4 || sampleRate !== 16000 || fmt.readUInt16LE(14) !== 32 ||
      fmt.readUInt16LE(12) !== 16 || fmt.readUInt32LE(8) !== 256000 || audio.length % 16 !== 0)
    throw new Error('Required WAV: IEEE FLOAT32, 4 channels, 16000 Hz');
  let peak = 0;
  for (let i = 0; i < audio.length; i += 4) {
    const sample = audio.readFloatLE(i);
    if (!Number.isFinite(sample)) throw new Error('Nonfinite WAV sample');
    peak = Math.max(peak, Math.abs(sample));
  }
  return {channels, sample_rate_hz: sampleRate, samples: audio.length / 16, peak};
}

function validateManifest(manifest) {
  if (!manifest || manifest.schema !== 'adeps-max-method-bank/1' ||
      manifest.sample_rate_hz !== 16000 || !Number.isInteger(manifest.samples) ||
      manifest.samples < 16 || manifest.samples > 1920000 ||
      JSON.stringify(manifest.channel_order) !== '["W","Y","Z","X"]' ||
      manifest.normalization !== 'N3D' || !finite(manifest.shared_gain) || manifest.shared_gain <= 0 ||
      !SHA.test(manifest.input_sha256 || '')) throw new Error('Invalid method-bank metadata');
  if (!Array.isArray(manifest.methods) || manifest.methods.length !== METHODS.length ||
      new Set(manifest.methods.map(item => item.id)).size !== METHODS.length)
    throw new Error('Bank must contain reference and all nine methods exactly once');
  // Canonical order is independent of the manifest's array order.
  const methods = METHODS.map(id => {
    const item = manifest.methods.find(method => method.id === id);
    if (!item || item.file !== `foa/${id}_FOA_ACN_N3D.wav` || !SHA.test(item.sha256 || ''))
      throw new Error('Invalid method filename or SHA256');
    const label = item.label || item.label_en || item.id;
    if (typeof label !== 'string' || label.length > 150 || /[\u0000-\u001f]/.test(label))
      throw new Error('Invalid method label');
    return {...item, label};
  });
  const matrix = manifest.decoder && manifest.decoder.matrix;
  if (!Array.isArray(matrix) || matrix.length !== 12 || matrix.some(row =>
    !Array.isArray(row) || row.length !== 4 || row.some(x => !finite(x) || Math.abs(x) > 16)))
    throw new Error('Expected a finite 12 by 4 FOA decoder matrix');
  if (manifest.decoder.normalization && manifest.decoder.normalization !== 'N3D')
    throw new Error('Decoder normalization must be N3D');
  return {...manifest, methods};
}

async function loadBank(filename) {
  if (typeof filename !== 'string' || !path.isAbsolute(filename)) throw new Error('Select an absolute manifest path');
  const realFile = await fs.realpath(filename), directory = path.dirname(realFile);
  const raw = await fs.readFile(realFile);
  if (raw.length > 2 * 1024 * 1024) throw new Error('Manifest is too large');
  const manifest = validateManifest(JSON.parse(raw.toString('utf8')));
  const methods = [];
  for (const item of manifest.methods) {
    const file = await fs.realpath(path.join(directory, item.file));
    if (!file.startsWith(directory + path.sep)) throw new Error('WAV must remain inside the bank folder');
    const stat = await fs.stat(file);
    if (!stat.isFile() || stat.size > 32 * 1024 * 1024) throw new Error('Invalid WAV file size');
    const bytes = await fs.readFile(file);
    if (sha256(bytes) !== item.sha256) throw new Error(`WAV SHA256 mismatch: ${item.id}`);
    const wav = inspectWav(bytes);
    if (wav.samples !== manifest.samples) throw new Error(`WAV duration mismatch: ${item.id}`);
    methods.push({...item, absolute_file: file, wav});
  }
  return {...manifest, methods, manifest_sha256: sha256(raw), manifest_file: realFile};
}
module.exports = {METHODS, sha256, inspectWav, validateManifest, loadBank};
