/** Real ACN / N3D first-order basis: W, Y, Z, X. Direction is Cartesian XYZ. */
export function directionalRms(covariance: number[][], direction: number[]): number {
  if (direction.length < 3 || !direction.slice(0, 3).every(Number.isFinite)) return 0;
  const length = Math.hypot(direction[0], direction[1], direction[2]);
  if (!(length > 0) || !Number.isFinite(length)) return 0;
  const y = [1, Math.sqrt(3) * direction[1] / length,
    Math.sqrt(3) * direction[2] / length, Math.sqrt(3) * direction[0] / length];
  let power = 0;
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 4; col++) {
      const value = covariance[row]?.[col];
      if (!Number.isFinite(value)) return 0;
      power += y[row] * value * y[col];
    }
  }
  return Math.sqrt(Math.max(0, power));
}

/** Fixed sphere grid used for every surface, including the shared display scale. */
export function directionalGrid(longitudes = 64, latitudes = 32): number[][] {
  const directions: number[][] = [];
  for (let latitude = 0; latitude <= latitudes; latitude++) {
    const theta = Math.PI * latitude / latitudes;
    for (let longitude = 0; longitude <= longitudes; longitude++) {
      const phi = 2 * Math.PI * longitude / longitudes;
      directions.push([Math.sin(theta) * Math.cos(phi), Math.sin(theta) * Math.sin(phi), Math.cos(theta)]);
    }
  }
  return directions;
}
