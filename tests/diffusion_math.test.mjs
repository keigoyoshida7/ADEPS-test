import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { directionalGrid, directionalRms } from '../app/lab/diffusionMath.ts';
import { virtualArrayPositions } from '../app/lab/arrayGeometry.ts';

const near = (actual, expected, tolerance = 1e-10) =>
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} differs from ${expected}`);
const diagonal = values => values.map((value, row) => values.map((_, col) => row === col ? value : 0));

test('ACN/N3D W,Y,Z,X maps to Cartesian directions without swapping axes', () => {
  const axes = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  const channelForAxis = [3, 1, 2];
  axes.forEach((direction, axis) => {
    near(directionalRms(diagonal([1, 0, 0, 0]), direction), 1);
    [1, 2, 3].forEach(channel => {
      const matrix = diagonal([0, 0, 0, 0].map((_, i) => +(i === channel)));
      near(directionalRms(matrix, direction), channel === channelForAxis[axis] ? Math.sqrt(3) : 0);
    });
  });
});

test('a known plane wave peaks in its source direction with the expected FOA beam response', () => {
  const source = [2 / 7, 3 / 7, 6 / 7];
  const coefficients = [1, Math.sqrt(3) * 3 / 7, Math.sqrt(3) * 6 / 7, Math.sqrt(3) * 2 / 7];
  const matrix = coefficients.map(a => coefficients.map(b => a * b));
  // A unit plane wave gives |1 + 3 cos(angle)| with this FOA convention.
  near(directionalRms(matrix, source), 4);
  near(directionalRms(matrix, source.map(value => -value)), 2);
  near(directionalRms(matrix, [3, -2, 0]), 1);
  near(directionalRms(matrix, source.map(value => value * 5)), 4);
  const directions = directionalGrid();
  const peak = directions.reduce((best, direction) => directionalRms(matrix, direction) > directionalRms(matrix, best) ? direction : best);
  const alignment = peak.reduce((sum, value, i) => sum + value * source[i], 0);
  assert.ok(alignment > .995, 'Sampled peak should point toward the known source');
  assert.ok(directions.every(direction => directionalRms(matrix, direction) <= 4 + 1e-10));
});

test('positive covariance preserves isotropy and square-amplitude scaling', () => {
  const isotropic = diagonal([1, 1, 1, 1]);
  const covariance = [[2, .5, .25, 0], [.5, 1, 0, 0], [.25, 0, .75, 0], [0, 0, 0, .5]];
  const stronger = covariance.map(row => row.map(value => value * 9));
  for (const direction of directionalGrid(12, 6)) {
    near(directionalRms(isotropic, direction), 2);
    const original = directionalRms(covariance, direction);
    assert.ok(Number.isFinite(original) && original > 0);
    near(directionalRms(stronger, direction), original * 3);
  }
});

test('zero fields and invalid directions do not produce NaN visual geometry', () => {
  const identity = diagonal([1, 1, 1, 1]);
  near(directionalRms(diagonal([0, 0, 0, 0]), [1, 0, 0]), 0);
  for (const direction of [[], [1], [0, 0, 0], [NaN, 0, 1], [0, Infinity, 1]]) {
    assert.equal(directionalRms(identity, direction), 0);
  }
  assert.equal(directionalRms([], [1, 0, 0]), 0);
  assert.equal(directionalRms(diagonal([NaN, 0, 0, 0]), [1, 0, 0]), 0);
});

test('sphere samples follow XYZ with positive Z at the pole and positive Y after positive X', () => {
  const directions = directionalGrid(4, 2);
  assert.equal(directions.length, 15);
  directions.forEach(direction => near(Math.hypot(...direction), 1));
  const expectedEquator = [[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0], [1, 0, 0]];
  expectedEquator.forEach((expected, i) => expected.forEach((value, axis) => near(directions[5 + i][axis], value)));
  directions.slice(0, 5).forEach(direction => near(direction[2], 1));
  directions.slice(10).forEach(direction => near(direction[2], -1));
});

test('draft microphone coordinates match independent Python observation fixtures channel by channel', () => {
  const fixture = JSON.parse(readFileSync(new URL('./fixtures/diffusion-geometry.json', import.meta.url), 'utf8'));
  assert.equal(fixture.schema, 'adeps-test-diffusion-array-geometry/1');
  assert.equal(fixture.cases.length, 6);
  for (const example of fixture.cases) {
    const actual = virtualArrayPositions(example.microphones, example.radius_m, example.geometry);
    assert.equal(actual.length, example.microphone_positions_m.length, `${example.geometry}, ${example.microphones} microphones`);
    example.microphone_positions_m.forEach((expected, channel) => {
      assert.equal(actual[channel].length, 3);
      expected.forEach((value, axis) => near(actual[channel][axis], value, 1e-12));
      near(Math.hypot(...actual[channel]), example.radius_m, 1e-12);
    });
  }
});

test('invalid draft array settings produce no invented coordinates', () => {
  for (const count of [0, -1, 4.5, NaN, Infinity, '6']) {
    assert.deepEqual(virtualArrayPositions(count, .06, 'sphere'), [], `Invalid count: ${count}`);
  }
  for (const radius of [0, -.06, NaN, Infinity]) {
    assert.deepEqual(virtualArrayPositions(6, radius, 'sphere'), [], `Invalid radius: ${radius}`);
  }
  assert.deepEqual(virtualArrayPositions(6, .06, 'line'), []);
});
