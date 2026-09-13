'use strict';
const dgram = require('node:dgram');
const {encode, decode} = require('./osc-codec');
const {METHODS} = require('./method-comparison-bank');

function command(message) {
  const {address, tags, args} = message;
  if (address === '/adeps-compare/ping' && tags === ',i') return {action: 'ping', value: args[0]};
  if (address === '/adeps-compare/select' && tags === ',ss' && METHODS.includes(args[0]) && /^[a-f0-9]{64}$/.test(args[1]))
    return {action: 'select', value: args[0], expectedHash: args[1]};
  if (address === '/adeps-compare/mute' && tags === ',') return {action: 'mute'};
  throw new Error('Allowed commands: ping int32, select method-id expected-hash, mute (no arguments)');
}

async function createComparisonServer({listenPort = 8874, replyPort = 8875,
  status = () => ({ready: false, selected: '', input_sha256: ''}),
  onSelect = async () => {}, onMute = async () => {}, onError = () => {}} = {}) {
  const socket = dgram.createSocket('udp4');
  let closed = false, queue = Promise.resolve(), windowStart = Date.now(), count = 0;
  const send = (address, args) => new Promise((resolve, reject) => {
    if (closed) return resolve();
    socket.send(encode(address, args), replyPort, '127.0.0.1', error => error ? reject(error) : resolve());
  });
  socket.on('message', (bytes, remote) => {
    if (closed || remote.address !== '127.0.0.1') return;
    if (Date.now() - windowStart >= 1000) {windowStart = Date.now(); count = 0;}
    if (++count > 100) return;
    let requested;
    try {requested = command(decode(bytes));} catch (error) {onError(error); return;}
    queue = queue.then(async () => {
      if (closed) return;
      try {
        if (requested.action === 'ping') {
          const s = status();
          await send('/adeps-compare/status', [requested.value, s.ready ? 1 : 0, s.selected || '', s.input_sha256 || '']);
        } else {
          if (requested.action === 'select') {
            if (!status().ready) throw new Error('Load and verify all ten buffers in Max first');
            if (status().input_sha256 !== requested.expectedHash) throw new Error('Loaded bank input hash differs from the selected Web bank');
            await onSelect(requested.value, requested.expectedHash);
          } else await onMute();
          const s = status();
          await send('/adeps-compare/ack', [requested.action, requested.value || '', s.input_sha256 || '']);
        }
      } catch (error) {
        onError(error);
        await send('/adeps-compare/error', [requested.action, String(error.message).slice(0, 120)]);
      }
    }).catch(onError);
  });
  try {
    await new Promise((resolve, reject) => {
      socket.once('error', reject);
      socket.bind(listenPort, '127.0.0.1', () => {socket.removeListener('error', reject); resolve();});
    });
  } catch (error) {try {socket.close();} catch {} throw error;}
  socket.on('error', onError);
  return {port: socket.address().port, async close() {
    if (closed) return; closed = true; await queue;
    await new Promise(resolve => socket.close(resolve));
  }};
}
module.exports = {command, createComparisonServer};
