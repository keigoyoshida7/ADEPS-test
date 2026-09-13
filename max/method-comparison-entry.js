'use strict';
// Node for Max can require the target through its wrapper, so require.main is not
// a reliable entry-point test. Keep this startup file separate from testable code.
const Max = require('max-api');
require('./method-comparison-controller').start().catch(async error => {
  await Max.outlet('ready', 0);
  await Max.outlet('mute');
  await Max.outlet('status', `ERROR: ${error.message}`);
  Max.post(error.message);
});
