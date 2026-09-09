'use strict';
// Only Node for Max loads this entry point. Starting it is a manual patch action.
const Max = require('max-api');
const {createControlServer} = require('./control-server');

let server;
async function main() {
  // Initialization can only close the local gate and lower its gain.
  await Max.outlet('mute', 1);
  server = await createControlServer({
    onControl: args => Max.outlet(...args),
    onStatus: (state, detail) => {
      Max.outlet('status', state, String(detail));
      Max.post('ADEPS-test bridge:', state, String(detail));
    }
  });
}
async function shutdown() {
  await Max.outlet('mute', 1);
  if (server) await server.close();
  process.exit(0);
}
process.on('SIGTERM', () => shutdown().catch(() => process.exit(1)));
process.on('SIGINT', () => shutdown().catch(() => process.exit(1)));
main().catch(async error => {
  await Max.outlet('mute', 1);
  await Max.post('ADEPS-test bridge could not start:', error.message, Max.POST_LEVELS.ERROR);
  process.exitCode = 1;
});
