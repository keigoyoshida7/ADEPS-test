import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validPaperComparison, validPaperReference } from '../app/lab/paperComparisonData.ts';

const originalBytes = readFileSync(new URL('../public/models/plus-benchmark.json', import.meta.url));
const original = JSON.parse(originalBytes);
const sourceHash = createHash('sha256').update(originalBytes).digest('hex');
const report = JSON.parse(readFileSync(new URL('../public/models/paper-comparison.json', import.meta.url)));
const reference = JSON.parse(readFileSync(new URL('../public/models/paper-reference-v3.json', import.meta.url)));
const copy = () => structuredClone(report);

test('published re-scoring belongs to the exact original benchmark and aggregates every scene', () => {
  assert.equal(validPaperComparison(report, original, sourceHash), true);
  assert.equal(validPaperReference(reference), true);
});
test('a different source, dropped scene or modified mean is rejected', () => {
  assert.equal(validPaperComparison(report, original, 'a'.repeat(64)), false);
  const missing = copy(); missing.scenes.pop();
  assert.equal(validPaperComparison(missing, original, sourceHash), false);
  const mean = copy(); mean.profiles.reference_floor.means.plus.spectral_error_db += 1;
  assert.equal(validPaperComparison(mean, original, sourceHash), false);
});
test('changing a curve, suppressing an undefined result or inventing successful coverage is rejected', () => {
  const curve = copy(); curve.profiles.strict.curves.plus.coherence[30] = 0;
  assert.equal(validPaperComparison(curve, original, sourceHash), false);
  const undefinedMean = copy(); undefinedMean.profiles.strict.means.linear_tuned.spectral_error_db = 0;
  assert.equal(validPaperComparison(undefinedMean, original, sourceHash), false);
  const counts = copy(); counts.profiles.strict.finite_scene_counts.linear_tuned.coherence = 32;
  assert.equal(validPaperComparison(counts, original, sourceHash), false);
});
test('wrong paper version, invalid values and malformed reference rows fail closed', () => {
  const version = structuredClone(reference); version.source.version = 'v1';
  assert.equal(validPaperReference(version), false);
  const row = structuredClone(reference); row.tables[0].rows[0] = null;
  assert.equal(validPaperReference(row), false);
  const score = structuredClone(reference); score.tables[0].rows[0].values.mics4.coherence = 1.1;
  assert.equal(validPaperReference(score), false);
});
