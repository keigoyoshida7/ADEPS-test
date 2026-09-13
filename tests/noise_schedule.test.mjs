import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { fromNoiseTrace, noiseSchedule } from '../app/lab/noiseSchedule.ts';

const fixture = JSON.parse(readFileSync(new URL('./fixtures/noise-schedule.json', import.meta.url), 'utf8'));
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) <= 1e-12, `${actual} differs from ${expected}`);

test('planned schedules match every Python sigma for 8, 24 and 80 actual updates', () => {
  assert.equal(fixture.schema, 'adeps-test-noise-schedule-fixture/1');
  assert.equal(fixture.cases.length, 3);
  for (const example of fixture.cases) {
    const points = noiseSchedule(example.steps, example.sigma_min, example.sigma_max, example.rho);
    assert.equal(points.length, example.steps + 1);
    assert.equal(points.filter(point => point.sigma > 0).length, example.steps);
    assert.equal(points.filter(point => point.sigma === 0).length, 1);
    points.forEach((point, i) => {
      assert.equal(point.step, i);
      near(point.sigma, example.points[i].sigma);
      if (i > 0) assert.ok(point.sigma < points[i - 1].sigma);
    });
    assert.equal(points[0].step, 0, 'Initial state precedes the first update');
    assert.deepEqual(points.at(-1), { step: example.steps, sigma: 0 });
  }
});

test('custom rho=1 schedule is linear and preserves the positive pre-terminal minimum', () => {
  const points = noiseSchedule(4, .1, 10, 1);
  [10, 6.7, 3.4, .1, 0].forEach((value, i) => near(points[i].sigma, value));
  assert.equal(points[3].step, 3);
  assert.deepEqual(points[4], { step: 4, sigma: 0 });
  assert.equal(noiseSchedule(2).length, 3);
  assert.equal(noiseSchedule(300).length, 301);
});

test('invalid planned schedule settings return no synthetic curve', () => {
  for (const args of [
    [1], [301], [8.5], [NaN], [Infinity], ['8'], [true],
    [8, 0], [8, -.002], [8, NaN], [8, Infinity], [8, '.002'],
    [8, .002, .001], [8, 20, 20], [8, .002, Infinity], [8, .002, NaN],
    [8, .002, 20, 0], [8, .002, 20, -1], [8, .002, 20, NaN], [8, .002, 20, Infinity],
  ]) assert.deepEqual(noiseSchedule(...args), [], `Invalid schedule: ${args}`);
});

test('trace display preserves recorded endpoints instead of reconstructing a formula', () => {
  const trace = Object.freeze([
    Object.freeze({ step: 1, sigma: 12, next_sigma: 4.5 }),
    Object.freeze({ step: 2, sigma: 4.5, next_sigma: .4 }),
    Object.freeze({ step: 3, sigma: .4, next_sigma: .015 }),
    Object.freeze({ step: 4, sigma: .015, next_sigma: 0 }),
  ]);
  const expected = [12, 4.5, .4, .015, 0].map((sigma, step) => ({ step, sigma }));
  const points = fromNoiseTrace(trace);
  assert.deepEqual(points, expected);
  assert.notDeepEqual(points, noiseSchedule(4), 'The actual trace must not be replaced by the default schedule');
  // D(x_0, sigma_0) is the pre-update-1 snapshot; the final sample is after update M.
  assert.equal(points[0].sigma, trace[0].sigma);
  assert.equal(points[3].sigma, trace[3].sigma);
  assert.deepEqual(points.at(-1), { step: 4, sigma: 0 });
  points[0].sigma = 99;
  assert.equal(trace[0].sigma, 12, 'Returned points must not mutate the saved trace');
});

test('incomplete, discontinuous or non-finite traces do not fall back to planned data', () => {
  const valid = [{ step: 1, sigma: 10, next_sigma: 1 }, { step: 2, sigma: 1, next_sigma: 0 }];
  const withRow = (index, change) => valid.map((row, i) => i === index ? { ...row, ...change } : { ...row });
  const cases = [null, {}, [], [valid[0]], Array(301).fill(null),
    withRow(0, { step: 0 }), withRow(1, { step: 1 }), withRow(1, { step: 3 }),
    withRow(0, { sigma: NaN }), withRow(0, { sigma: 0 }), withRow(0, { sigma: -1 }),
    withRow(0, { next_sigma: undefined }), withRow(0, { next_sigma: Infinity }),
    withRow(0, { next_sigma: 10 }), withRow(0, { next_sigma: 11 }), withRow(0, { next_sigma: 0 }),
    withRow(1, { sigma: .5 }), withRow(1, { next_sigma: -.1 }), withRow(1, { next_sigma: .1 }),
  ];
  for (const trace of cases) assert.deepEqual(fromNoiseTrace(trace), []);
  for (const example of fixture.cases) {
    const trace = example.points.slice(0, -1).map((point, i) => ({
      step: i + 1, sigma: point.sigma, next_sigma: example.points[i + 1].sigma,
    }));
    assert.deepEqual(fromNoiseTrace(trace), example.points);
  }
});
