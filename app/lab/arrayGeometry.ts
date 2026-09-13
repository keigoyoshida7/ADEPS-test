/** Matches backend/diffusion_studio.py:make_observation, in metres and input-channel order.
 * Geometry only: this preview does not generate observations or run inference.
 */
export function virtualArrayPositions(count: number, radius: number, geometry: 'sphere' | 'ring'): number[][] {
  if (!Number.isInteger(count) || count < 1 || count > 256 || !Number.isFinite(radius) || radius <= 0 || !['sphere', 'ring'].includes(geometry)) return [];
  return Array.from({ length: count }, (_, i) => {
    const angle = geometry === 'ring' ? 2 * Math.PI * i / count : i * Math.PI * (3 - Math.sqrt(5));
    const z = geometry === 'ring' ? 0 : 1 - 2 * (i + .5) / count;
    const horizontal = Math.sqrt(1 - z * z);
    return [radius * horizontal * Math.cos(angle), radius * horizontal * Math.sin(angle), radius * z];
  });
}
