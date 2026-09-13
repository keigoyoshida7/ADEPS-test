# Max method comparison — validation record

2026-09-13, v0.7.2. This feature plays saved reconstructions. It does not change inference, checkpoints, test inputs or published metrics.

## Native Max and local Web UI

The distributed scene-0000 ZIP was extracted into a separate directory and its `max/ADEPS_Method_Comparison.maxpat` opened in the installed Max application. Starting the controller and explicitly clicking **Load bundled bank** produced `READY / 3968 samples / N3D` only after the ten Max buffers confirmed their dimensions. The decoded output gain remained zero and DSP was not started during this check.

The actual Node for Max process accepted all ten method IDs through the local Python API; each response confirmed the same bank input SHA256. Max's menu visibly reflected the final method. The local Web page then successfully selected ADEPS + α and tuned Linear, and showed the corresponding accepted method. Changing the Web selection alone did not change the method reported by Max; the Send button was required.

The final 32-scene ZIP was also extracted and opened independently in Max. Its ten buffers reported `READY / 201376 samples / N3D` (12.586 seconds). The local Web page recognized the matching montage bank and successfully selected ADEPS + α; the actual Max response confirmed method `plus` and input SHA256 `178ce8aeb95dcb076e6aa4dceafeddf20575273ac5ef9aed1d28d9edb2a6136d`. DSP remained off and master gain remained zero.

Native loading found and resolved two issues before delivery: Max has no `expr~` object for the proposed envelope, so standard signal arithmetic is used; Node for Max can load through a wrapper, so a dedicated startup file invokes the controller without relying on `require.main === module`.

## Automated checks

- Bank metadata, complete FLOAT32 RIFF parsing, SHA256, all ten files, buffer completion, bank identity on selection, restricted loopback control and generated patch connections.
- A shared signal-rate playhead and complementary linear method ramps, including interrupted changes; one common signed 12×4 decoder and one manually controlled master gain.
- Export integrity: scene-0000 WAVs match the existing published bytes; all montage inputs and saved estimates are checked against their recorded identities. Every method uses the same timeline, fades, gaps and single global gain. No per-method or per-scene normalization.
- API tests cover wrong reply sequences, mismatched banks, unknown methods, timeouts, unavailable Max and preservation of the older channel-control API.
- Existing numerical, Max, browser-math, +α and paper-metric suites, TypeScript checks and production build are included in release verification.

## Remaining physical verification

These checks do **not** establish audible output, loudspeaker routing, room response, sound-pressure level, or sample-accurate output at a particular hardware sample rate. Audio was deliberately not enabled because other user patches were open. At the venue, verify output device, sample rate and the S1–S12 map, start from zero gain, and compare the same bank at an unchanged master setting. Saved channels 11/12 require the documented route check. The 32-scene montage comprises short clips, not continuous speech inference.

See [Max instructions](../max/README_COMPARISON.md) and [bank exporter](../scripts/export_max_comparison.py).
