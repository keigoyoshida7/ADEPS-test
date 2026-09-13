export type NoisePoint = { step: number; sigma: number };

/**
 * Planned sigma schedule in normalized, magnitude-compressed coefficient space.
 * Sigma is a diffusion parameter, not measured residual noise or acoustic SPL.
 * The positive points follow paper Eq. (11). Like backend/neural.schedule,
 * append an explicit terminal zero: M positive points, M updates, steps 0..M.
 */
export function noiseSchedule(
  steps: number,
  sigmaMin = .002,
  sigmaMax = 20,
  rho = 10,
): NoisePoint[] {
  if (!Number.isInteger(steps) || steps < 2 || steps > 300 ||
    !Number.isFinite(sigmaMin) || !Number.isFinite(sigmaMax) || !Number.isFinite(rho) ||
    sigmaMin <= 0 || sigmaMax <= sigmaMin || rho <= 0) return [];
  const upper = sigmaMax ** (1 / rho);
  const lower = sigmaMin ** (1 / rho);
  const points = Array.from({ length: steps }, (_, step) => ({
    step,
    sigma: (upper + (step / (steps - 1)) * (lower - upper)) ** rho,
  }));
  // Reject combinations whose finite-precision evaluation is no longer a valid schedule.
  if (points.some((point, i) => !Number.isFinite(point.sigma) || point.sigma <= 0 ||
    (i > 0 && point.sigma >= points[i - 1].sigma))) return [];
  return [...points, { step: steps, sigma: 0 }];
}

/**
 * Read an actual completed sampler trace without inventing or recomputing values.
 * A trace row's step is one-based; sigma is before that update and next_sigma after it.
 * Therefore the first sigma belongs to step 0, and the final next_sigma to step M.
 */
export function fromNoiseTrace(
  trace: { step: number; sigma: number; next_sigma: number }[],
): NoisePoint[] {
  if (!Array.isArray(trace) || trace.length < 2 || trace.length > 300) return [];
  const points: NoisePoint[] = [];
  for (let i = 0; i < trace.length; i++) {
    const row = trace[i];
    if (!row || row.step !== i + 1 || !Number.isFinite(row.sigma) || row.sigma <= 0 ||
      !Number.isFinite(row.next_sigma) || row.next_sigma < 0 || row.next_sigma >= row.sigma ||
      (i > 0 && row.sigma !== trace[i - 1].next_sigma) ||
      (i < trace.length - 1 ? row.next_sigma <= 0 : row.next_sigma !== 0)) return [];
    if (i === 0) points.push({ step: 0, sigma: row.sigma });
    points.push({ step: row.step, sigma: row.next_sigma });
  }
  return points;
}
