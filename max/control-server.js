'use strict';
const dgram = require('node:dgram');
const {encode, decode, command} = require('./osc-codec');

// Always loopback. Port overrides exist only for isolated automated tests.
async function createControlServer({listenPort = 8872, replyPort = 8873, onControl = async () => {}, onStatus = () => {}} = {}) {
  const socket = dgram.createSocket('udp4');
  let closed = false, queue = Promise.resolve();
  let windowStart = Date.now(), count = 0;
  const send = (address, args) => new Promise((resolve, reject) => {
    if (closed) return resolve();
    socket.send(encode(address, args), replyPort, '127.0.0.1', error => error ? reject(error) : resolve());
  });
  socket.on('message', (bytes, remote) => {
    if (remote.address !== '127.0.0.1' || closed) return;
    if (Date.now() - windowStart >= 1000) {windowStart = Date.now(); count = 0;}
    if (++count > 100) return;
    let selected;
    try { selected = command(decode(bytes)); }
    catch (error) { onStatus('rejected', error.message); return; }
    queue = queue.then(async () => {
      if (closed) return;
      if (selected.action === 'ping') {
        await send('/adeps-test/pong', [selected.value]);
      } else {
        // This is an application-level receipt, not DAC/Dante verification.
        await onControl(selected.action === 'select' ? ['channel', selected.value] : ['mute', 1]);
        await send('/adeps-test/ack', [selected.action, selected.value]);
      }
    }).catch(error => onStatus('error', error.message));
  });
  try {
    await new Promise((resolve, reject) => {
      socket.once('error', reject);
      socket.bind(listenPort, '127.0.0.1', () => {socket.removeListener('error', reject); resolve();});
    });
  } catch (error) { try {socket.close();} catch {} throw error; }
  socket.on('error', error => onStatus('error', error.message));
  onStatus('listening', socket.address().port);
  return {
    port: socket.address().port,
    async close() {
      if (closed) return;
      closed = true;
      await queue;
      await new Promise(resolve => socket.close(resolve));
    }
  };
}
module.exports = {createControlServer};
