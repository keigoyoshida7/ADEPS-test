import test from 'node:test';
import assert from 'node:assert/strict';
import { buildDecoder, decodeCoefficients, foaDirection, sourceDirection, rightFrontUpToFrontLeftUp } from '../app/lab/decodingMath.ts';
const close = (actual, expected, tolerance = 1e-10) => assert.ok(Math.abs(actual - expected) < tolerance, `${actual} != ${expected}`);
const tetra = [[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]];
const origin = [0,0,0];
test('tetrahedral directions have orthogonal modes and an exact unregularized inverse', () => {
  const d = buildDecoder(tetra, origin, 0);
  assert.equal(d.rank, 4); close(d.condition, 1);
  d.matrix.forEach((row, i) => row.forEach((value, j) => close(value, d.harmonics[i][j] / 4)));
  [0,1,2,3].forEach(channel => {
    const a = [0,0,0,0]; a[channel] = 1;
    decodeCoefficients(d, a).reconstructed.forEach((v, i) => close(v, a[i]));
  });
});
test('ridge solution on a symmetric octahedron shrinks all modes by the known factor', () => {
  const octa = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];
  const d = buildDecoder(octa, origin, 2);
  d.eigenvalues.forEach(v => close(v, 6));
  const a = [1,.25,-.5,1.5];
  decodeCoefficients(d, a).reconstructed.forEach((v, i) => close(v, a[i] * .75));
});
test('a planar ring cannot reproduce the vertical mode despite regularization', () => {
  const d = buildDecoder([[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]], origin, .001);
  assert.equal(d.rank, 3); assert.equal(d.condition, null);
  d.matrix.forEach(row => close(row[2], 0));
  const result = decodeCoefficients(d, [0,0,1,0]);
  close(result.relativeError, 1); result.reconstructed.forEach(v => close(v, 0));
  assert.throws(() => buildDecoder([[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]], origin, 0), /Singular/);
});
test('the angular decoder is unchanged by translation and independent radial scaling', () => {
  const listener = [6,4.5,1.2];
  const positions = tetra.map((p, i) => p.map((v, j) => v * (i + 1) + listener[j]));
  const a = buildDecoder(tetra, origin), b = buildDecoder(positions, listener);
  a.matrix.forEach((row, i) => row.forEach((v, j) => close(v, b.matrix[i][j])));
});
test('ACN/N3D order is W,Y,Z,X and signed speaker gains are preserved', () => {
  foaDirection(sourceDirection(90, 0)).forEach((v, i) => close(v, [1,Math.sqrt(3),0,0][i]));
  foaDirection(sourceDirection(0, 90)).forEach((v, i) => close(v, [1,0,Math.sqrt(3),0][i]));
  const d = buildDecoder(tetra, origin, 0);
  const result = decodeCoefficients(d, [0,0,0,1]);
  assert.ok(result.gains.some(v => v < 0)); close(result.relativeError, 0);
});
test('invalid geometry and coefficients fail explicitly', () => {
  assert.throws(() => buildDecoder([[0,0,0]], origin), /coincides/);
  assert.throws(() => buildDecoder([[NaN,0,0]], origin), /Invalid/);
  assert.throws(() => buildDecoder([], origin), /Invalid/);
  assert.throws(() => buildDecoder(tetra, origin, -1), /Invalid/);
  assert.throws(() => decodeCoefficients(buildDecoder(tetra, origin), [1,2]), /four/);
});

test('saved layout right/front/up axes rotate into front/left/up FOA consistently', () => {
  assert.deepEqual(rightFrontUpToFrontLeftUp([2,3,4]), [3,-2,4]);
  const front = foaDirection(rightFrontUpToFrontLeftUp([0,1,0]));
  front.forEach((v, i) => close(v, [1,0,0,Math.sqrt(3)][i]));
  const right = foaDirection(rightFrontUpToFrontLeftUp([1,0,0]));
  right.forEach((v, i) => close(v, [1,-Math.sqrt(3),0,0][i]));
  const transformed = tetra.map(rightFrontUpToFrontLeftUp);
  close(buildDecoder(transformed, origin, 0).condition, 1);
});
