import assert from 'node:assert/strict';
import test from 'node:test';
import { auditionClipAt, buildAuditionTimeline } from '../app/lab/processAuditionTimeline.ts';

test('saved stages repeat in order with contiguous nonoverlapping intervals', () => {
  const timeline = buildAuditionTimeline([.35, .4, .25], 2);
  assert.deepEqual(timeline.clips.map(clip => clip.stageIndex), [0, 0, 1, 1, 2, 2]);
  assert.deepEqual(timeline.clips.map(clip => clip.repeatIndex), [0, 1, 0, 1, 0, 1]);
  assert.ok(Math.abs(timeline.duration - 2) < 1e-12);
  for (let i = 0; i < timeline.clips.length; i++) {
    assert.equal(timeline.clips[i].start, i ? timeline.clips[i - 1].end : 0);
    assert.equal(timeline.clips[i].fade, .005);
  }
});

test('audio clock selects the next clip exactly at boundaries and none outside playback', () => {
  const timeline = buildAuditionTimeline([.35, .35], 2);
  assert.equal(auditionClipAt(timeline, 0), timeline.clips[0]);
  for (const clip of timeline.clips) {
    assert.equal(auditionClipAt(timeline, clip.start), clip);
    assert.equal(auditionClipAt(timeline, (clip.start + clip.end) / 2), clip);
  }
  for (const time of [-.001, timeline.duration, timeline.duration + 1, Infinity, NaN]) assert.equal(auditionClipAt(timeline, time), undefined);
});

test('1/2/4 repeats retain exact duration and short clips have bounded nonoverlapping fades', () => {
  for (const repeats of [1, 2, 4]) {
    const timeline = buildAuditionTimeline([.004, 1], repeats);
    assert.equal(timeline.clips.length, 2 * repeats);
    assert.ok(Math.abs(timeline.duration - 1.004 * repeats) < 1e-12);
    assert.equal(timeline.clips[0].fade, .001);
    assert.ok(timeline.clips.every(clip => clip.fade * 2 <= clip.end - clip.start));
  }
});

test('invalid durations and repetition counts fail instead of scheduling ambiguous audio', () => {
  for (const durations of [[], [0], [-1], [NaN], [Infinity], [.35, 0]]) assert.throws(() => buildAuditionTimeline(durations, 2));
  for (const repeats of [0, 3, 8, 1.5, NaN, '2']) assert.throws(() => buildAuditionTimeline([.35], repeats));
});
