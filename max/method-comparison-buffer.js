// Max's embedded JS (not Node): confirm the actual buffer after its completion bang.
autowatch = 0;
inlets = 1;
outlets = 1;
function loaded(index) {
  var buffer = new Buffer(jsarguments[1] + '-cmp-' + index);
  outlet(0, ['loaded', index, buffer.channelcount(), buffer.framecount(), buffer.length()]);
}
