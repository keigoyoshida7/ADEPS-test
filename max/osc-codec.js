'use strict';

// The intentionally narrow OSC 1.0 subset used by this local test bridge.
// One message per datagram; int32 and UTF-8 strings only; no bundles.
function oscString(value) {
  if (typeof value !== 'string' || value.includes('\0')) throw new Error('Invalid OSC string');
  const bytes = Buffer.from(value, 'utf8');
  const out = Buffer.alloc(Math.ceil((bytes.length + 1) / 4) * 4);
  bytes.copy(out);
  return out;
}

function encode(address, args = []) {
  if (typeof address !== 'string' || !address.startsWith('/')) throw new Error('Invalid OSC address');
  const tags = args.map(value => {
    if (typeof value === 'string') return 's';
    if (Number.isInteger(value) && value >= -2147483648 && value <= 2147483647) return 'i';
    throw new Error('Only int32 or string OSC arguments are supported');
  });
  const parts = [oscString(address), oscString(',' + tags.join(''))];
  args.forEach((value, i) => {
    if (tags[i] === 's') parts.push(oscString(value));
    else { const bytes = Buffer.alloc(4); bytes.writeInt32BE(value); parts.push(bytes); }
  });
  return Buffer.concat(parts);
}

function decode(input) {
  const bytes = Buffer.from(input);
  if (bytes.length < 8 || bytes.length > 256 || bytes.length % 4 !== 0) throw new Error('Invalid OSC packet size');
  let offset = 0;
  function readString() {
    const end = bytes.indexOf(0, offset);
    if (end < 0) throw new Error('Unterminated OSC string');
    const value = bytes.subarray(offset, end).toString('utf8');
    if (!Buffer.from(value, 'utf8').equals(bytes.subarray(offset, end))) throw new Error('Invalid UTF-8');
    const next = Math.ceil((end + 1) / 4) * 4;
    if (next > bytes.length) throw new Error('Truncated OSC padding');
    for (let i = end; i < next; i++) if (bytes[i] !== 0) throw new Error('Nonzero OSC padding');
    offset = next;
    return value;
  }
  const address = readString();
  if (!address.startsWith('/')) throw new Error('Only OSC messages are supported');
  const tags = readString();
  if (!/^,[is]*$/.test(tags)) throw new Error('Unsupported OSC type tag');
  const args = [];
  for (const tag of tags.slice(1)) {
    if (tag === 's') args.push(readString());
    else {
      if (offset + 4 > bytes.length) throw new Error('Truncated OSC int32');
      args.push(bytes.readInt32BE(offset)); offset += 4;
    }
  }
  if (offset !== bytes.length) throw new Error('Unexpected trailing OSC data');
  return { address, args, tags };
}

function command(message) {
  const {address, args, tags} = message;
  if (address === '/adeps-test/ping' && tags === ',i' && args.length === 1) return {action:'ping', value:args[0]};
  if (address === '/adeps-test/select' && tags === ',i' && args.length === 1 && args[0] >= 1 && args[0] <= 12) return {action:'select', value:args[0]};
  if (address === '/adeps-test/mute' && tags === ',' && args.length === 0) return {action:'mute', value:1};
  throw new Error('Command is outside the allowed ADEPS-test schema');
}

module.exports = {encode, decode, command};
