'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const dgram = require('node:dgram');
const {encode, decode, command} = require('./osc-codec');
const {createControlServer} = require('./control-server');

test('OSC int32 byte order, zero padding and receipt string round trip', () => {
  const ping = encode('/adeps-test/ping', [42]);
  assert.equal(ping.toString('hex'), '2f61646570732d746573742f70696e67000000002c6900000000002a');
  assert.deepEqual(decode(ping), {address:'/adeps-test/ping', args:[42], tags:',i'});
  assert.deepEqual(decode(encode('/adeps-test/ack', ['select', 12])), {address:'/adeps-test/ack', args:['select',12], tags:',si'});
  assert.deepEqual(command(decode(encode('/adeps-test/mute'))), {action:'mute',value:1});
  for (const n of [-2147483648, 2147483647]) assert.equal(decode(encode('/adeps-test/ping',[n])).args[0], n);
});

test('Schema rejects invalid commands, float types, malformed padding and packets', () => {
  for (const address of ['/adeps-test/gain','/adeps-test/dsp','/adeps-test/start','/source/1/xyz']) {
    assert.throws(() => command(decode(encode(address,[1]))));
  }
  for (const n of [0,13,-1]) assert.throws(() => command(decode(encode('/adeps-test/select',[n]))));
  assert.throws(() => command(decode(encode('/adeps-test/select',['1']))));
  assert.throws(() => command(decode(encode('/adeps-test/mute',[1]))));
  assert.throws(() => encode('/adeps-test/select',[1.5]));
  assert.throws(() => encode('/adeps-test/ping',[2147483648]));
  const badPadding = encode('/adeps-test/ping',[1]); badPadding[17] = 1;
  assert.throws(() => decode(badPadding));
  const floatPacket = encode('/adeps-test/select',[1]); floatPacket[21] = 'f'.charCodeAt(0);
  assert.throws(() => decode(floatPacket));
  assert.throws(() => decode(Buffer.from('#bundle\0')));
  assert.throws(() => decode(encode('/adeps-test/ping',[1]).subarray(0,19)));
  assert.throws(() => decode(Buffer.concat([encode('/adeps-test/mute'),Buffer.alloc(4)])));
});

test('Loopback UDP ping/select/mute smoke test without Max or audio', async () => {
  const listener = dgram.createSocket('udp4');
  const controls = [], statuses = [], replies = [];
  listener.on('message', bytes => replies.push(decode(bytes)));
  await new Promise(resolve => listener.bind(0,'127.0.0.1',resolve));
  const server = await createControlServer({listenPort:0, replyPort:listener.address().port,
    onControl: async args => {controls.push(args);}, onStatus:(...args) => statuses.push(args)});
  async function request(address,args,expectedCount) {
    await new Promise((resolve,reject) => listener.send(encode(address,args),server.port,'127.0.0.1',error => error ? reject(error) : resolve()));
    for (let i=0; i<100 && replies.length<expectedCount; i++) await new Promise(resolve=>setTimeout(resolve,10));
    assert.equal(replies.length,expectedCount,'Timed out waiting for UDP reply');
  }
  try {
    await request('/adeps-test/ping',[2048],1);
    assert.deepEqual(replies[0],{address:'/adeps-test/pong',args:[2048],tags:',i'});
    assert.deepEqual(controls,[],'Ping cannot control audio');
    await request('/adeps-test/select',[12],2);
    assert.deepEqual(replies[1],{address:'/adeps-test/ack',args:['select',12],tags:',si'});
    assert.deepEqual(controls,[['channel',12]]);
    await request('/adeps-test/mute',[],3);
    assert.deepEqual(replies[2],{address:'/adeps-test/ack',args:['mute',1],tags:',si'});
    assert.deepEqual(controls,[['channel',12],['mute',1]]);
    await new Promise(resolve=>listener.send(encode('/adeps-test/gain',[1]),server.port,'127.0.0.1',resolve));
    await new Promise(resolve=>setTimeout(resolve,50));
    assert.equal(replies.length,3,'Unsupported gain command gets no positive acknowledgement');
    assert.equal(controls.length,2,'Unsupported command cannot reach Max');
    assert.ok(statuses.some(x=>x[0]==='rejected'));
  } finally {await server.close(); await new Promise(resolve=>listener.close(resolve));}
});

test('A duplicate receiver fails explicitly without taking over the active socket', async () => {
  const first = await createControlServer({listenPort:0,replyPort:1});
  try {await assert.rejects(createControlServer({listenPort:first.port,replyPort:1}), /EADDRINUSE/);}
  finally {await first.close();}
});

test('Max patch has closed initial outputs, local bounded gain and exactly 12 DAC routes', () => {
  const patch = JSON.parse(fs.readFileSync(path.join(__dirname,'ADEPS_Test_Channel.maxpat'),'utf8')).patcher;
  const boxes = new Map(patch.boxes.map(x=>[x.box.id,x.box]));
  const edges = patch.lines.map(x=>x.patchline);
  for (const edge of edges) {
    assert.ok(boxes.has(edge.source[0]) && boxes.has(edge.destination[0]));
    assert.ok(edge.source[1] < boxes.get(edge.source[0]).numoutlets);
    assert.ok(edge.destination[1] < boxes.get(edge.destination[0]).numinlets);
  }
  assert.equal(boxes.get('node').text,'node.script bridge.js @autostart 0 @watch 0');
  assert.equal(boxes.get('gate').text,'gate~ 12 0');
  assert.equal(boxes.get('amplitude').text,'*~ 0.');
  assert.equal(boxes.get('gain_signal').text,'line~ 0.');
  assert.equal(boxes.get('level_clip').text,'clip 0. 0.03');
  assert.equal(boxes.get('level').maximum,.03);
  assert.equal(boxes.get('initial_mute').text,'loadmess 0');
  assert.equal(boxes.get('dac').text,'dac~ 1 2 3 4 5 6 7 8 9 10 11 12');
  assert.equal(boxes.get('route').text,'route channel mute status');
  const dacEdges = edges.filter(x=>x.destination[0]==='dac');
  assert.equal(dacEdges.length,12);
  for (let i=0;i<12;i++) assert.ok(dacEdges.some(x=>x.source[0]==='gate'&&x.source[1]===i&&x.destination[1]===i));
  assert.equal(edges.filter(x=>x.destination[0]==='dsp').length,0,'DSP can only be clicked manually');
  assert.ok(![...boxes.values()].some(x=>(x.text||'').startsWith('loadmess 1')));
  // Every channel-change path zeros the gain before opening the new gate.
  const e=(a,ao,b,bi)=>edges.some(x=>x.source[0]===a&&x.source[1]===ao&&x.destination[0]===b&&x.destination[1]===bi);
  assert.ok(e('route',0,'channel',0)&&e('channel',0,'select_trigger',0));
  assert.ok(e('select_trigger',2,'zero_gate',0)&&e('zero_gate',0,'gate',0));
  assert.ok(e('select_trigger',1,'immediate_zero',0)&&e('immediate_zero',0,'gain_signal',0));
  assert.ok(e('select_trigger',0,'channel_clip',0)&&e('channel_clip',0,'gate',0));
  assert.ok(e('route',1,'zero_channel',0)&&e('mute',0,'zero_channel',0));
  assert.ok(e('stop_trigger',1,'zero_channel',0)&&e('stop_trigger',0,'stop_message',0));
});
