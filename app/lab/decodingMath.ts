/** Angular FOA mode matching only. Coordinates are metres; ACN/N3D order W,Y,Z,X. */
export type Vector3 = [number, number, number];
export type Decoder = {
  directions: number[][];
  harmonics: number[][];
  matrix: number[][];
  eigenvalues: number[];
  rank: number;
  condition: number | null;
  regularization: number;
};
const validPoint = (p: number[]) => p.length === 3 && p.every(Number.isFinite);
export function foaDirection(direction: number[]): number[] {
  if (!validPoint(direction)) throw new Error('Invalid direction');
  const norm = Math.hypot(...direction);
  if (norm <= 1e-12) throw new Error('A speaker coincides with the listener');
  const [x, y, z] = direction.map(v => v / norm);
  return [1, Math.sqrt(3) * y, Math.sqrt(3) * z, Math.sqrt(3) * x];
}
/** Saved-layout axes X=right,Y=front,Z=up -> Ambisonics X=front,Y=left,Z=up. */
export function rightFrontUpToFrontLeftUp(point: number[]): Vector3 {
  if (!validPoint(point)) throw new Error('Invalid coordinates');
  return [point[1], -point[0], point[2]];
}
export function sourceDirection(azimuthDegrees: number, elevationDegrees: number): Vector3 {
  if (![azimuthDegrees, elevationDegrees].every(Number.isFinite)) throw new Error('Invalid source angle');
  const az = azimuthDegrees * Math.PI / 180, el = elevationDegrees * Math.PI / 180;
  return [Math.cos(el) * Math.cos(az), Math.cos(el) * Math.sin(az), Math.sin(el)];
}
/** Jacobi rotations of a real symmetric 4x4 Gram matrix. */
function eigenvalues4(input: number[][]): number[] {
  const a = input.map(row => [...row]);
  for (let iteration = 0; iteration < 80; iteration++) {
    let p = 0, q = 1;
    for (let i = 0; i < 4; i++) for (let j = i + 1; j < 4; j++) {
      if (Math.abs(a[i][j]) > Math.abs(a[p][q])) { p = i; q = j; }
    }
    if (Math.abs(a[p][q]) < 1e-13) break;
    const angle = Math.atan2(2 * a[p][q], a[q][q] - a[p][p]) / 2;
    const c = Math.cos(angle), s = Math.sin(angle);
    const pp = a[p][p], qq = a[q][q], pq = a[p][q];
    for (let k = 0; k < 4; k++) if (k !== p && k !== q) {
      const kp = a[k][p], kq = a[k][q];
      a[k][p] = a[p][k] = c * kp - s * kq;
      a[k][q] = a[q][k] = s * kp + c * kq;
    }
    a[p][p] = c * c * pp - 2 * c * s * pq + s * s * qq;
    a[q][q] = s * s * pp + 2 * c * s * pq + c * c * qq;
    a[p][q] = a[q][p] = 0;
  }
  return a.map((row, i) => Math.max(0, row[i])).sort((a, b) => b - a);
}
function inverse4(input: number[][]): number[][] {
  const rows = input.map((row, i) => [...row, ...Array.from({ length: 4 }, (_, j) => Number(i === j))]);
  for (let col = 0; col < 4; col++) {
    let pivot = col;
    for (let row = col + 1; row < 4; row++) if (Math.abs(rows[row][col]) > Math.abs(rows[pivot][col])) pivot = row;
    if (Math.abs(rows[pivot][col]) < 1e-14) throw new Error('Singular decoder: use positive regularization');
    [rows[col], rows[pivot]] = [rows[pivot], rows[col]];
    const divisor = rows[col][col];
    rows[col] = rows[col].map(v => v / divisor);
    for (let row = 0; row < 4; row++) if (row !== col) {
      const factor = rows[row][col];
      rows[row] = rows[row].map((v, k) => v - factor * rows[col][k]);
    }
  }
  return rows.map(row => row.slice(4));
}
export function buildDecoder(speakers: number[][], listener: number[], regularization = .001): Decoder {
  if (!validPoint(listener) || !speakers.length || !speakers.every(validPoint)) throw new Error('Invalid speaker coordinates');
  if (!Number.isFinite(regularization) || regularization < 0) throw new Error('Invalid regularization');
  const offsets = speakers.map(p => p.map((v, i) => v - listener[i]));
  const harmonics = offsets.map(foaDirection);
  const directions = offsets.map(p => p.map(v => v / Math.hypot(...p)));
  const gram = Array.from({ length: 4 }, (_, i) => Array.from({ length: 4 }, (_, j) => harmonics.reduce((sum, row) => sum + row[i] * row[j], 0)));
  const eigenvalues = eigenvalues4(gram);
  const rank = eigenvalues.filter(value => value > eigenvalues[0] * 1e-10).length;
  if (rank < 4 && regularization === 0) throw new Error('Singular decoder: use positive regularization');
  const inverse = inverse4(gram.map((row, i) => row.map((v, j) => v + (i === j ? regularization : 0))));
  const matrix = harmonics.map(row => Array.from({ length: 4 }, (_, j) => row.reduce((sum, v, i) => sum + v * inverse[i][j], 0)));
  return { directions, harmonics, matrix, eigenvalues, rank,
    condition: rank === 4 ? Math.sqrt(eigenvalues[0] / eigenvalues[3]) : null, regularization };
}
export function decodeCoefficients(decoder: Decoder, coefficients: number[]) {
  if (coefficients.length !== 4 || !coefficients.every(Number.isFinite)) throw new Error('Expected four finite FOA coefficients');
  const gains = decoder.matrix.map(row => row.reduce((sum, v, i) => sum + v * coefficients[i], 0));
  const reconstructed = Array.from({ length: 4 }, (_, i) => gains.reduce((sum, g, j) => sum + decoder.harmonics[j][i] * g, 0));
  const norm = Math.hypot(...coefficients);
  return { gains, reconstructed, relativeError: norm ? Math.hypot(...reconstructed.map((v, i) => v - coefficients[i])) / norm : null };
}
