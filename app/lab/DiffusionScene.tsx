'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { directionalGrid, directionalRms } from './diffusionMath';
import './DiffusionScene.css';

export { directionalRms } from './diffusionMath';

export type DiffusionSceneProps = {
  /** Re(mean(a a^H)), real 4 x 4, ACN / N3D channel order W, Y, Z, X. */
  covariance: number[][];
  referenceCovariance?: number[][];
  comparisonCovariance?: number[][];
  microphonePositions: number[][];
  sourceDirections?: number[][];
  language: 'jp' | 'en';
  /** Positive shared RMS divisor. Use the same value across time steps or separate viewers. */
  commonScale?: number;
};

type SceneContext = {
  group: THREE.Group;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  extent: number;
  view: string;
  reset: () => void;
};

const LONGITUDES = 64;
const LATITUDES = 32;
const DIRECTIONS = directionalGrid(LONGITUDES, LATITUDES);
const AXES = [
  { direction: [1, 0, 0], jp: '前 +X', en: 'Front +X' },
  { direction: [0, 1, 0], jp: '左 +Y', en: 'Left +Y' },
  { direction: [0, 0, 1], jp: '上 +Z', en: 'Up +Z' },
];

function xyz(p: number[]) { return new THREE.Vector3(p[0], p[2], -p[1]); }
function finitePoint(p: number[]) { return p.length >= 3 && p.slice(0, 3).every(Number.isFinite); }
function number(value: number) {
  return value === 0 ? '0' : Math.abs(value) < .001 || Math.abs(value) >= 1000 ? value.toExponential(2) : value.toPrecision(4);
}
function disposeObjects(group: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();
  group.traverse(object => {
    const mesh = object as THREE.Mesh;
    if (mesh.geometry) geometries.add(mesh.geometry);
    if (mesh.material) (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach(material => {
      materials.add(material);
      const mapped = material as THREE.MeshBasicMaterial;
      if (mapped.map) textures.add(mapped.map);
    });
  });
  textures.forEach(texture => texture.dispose());
  materials.forEach(material => material.dispose());
  geometries.forEach(geometry => geometry.dispose());
}
function label(text: string, position: THREE.Vector3, size: number, opacity = 1) {
  const canvas = document.createElement('canvas');
  canvas.width = 384;
  canvas.height = 96;
  const context = canvas.getContext('2d');
  if (!context) return new THREE.Group();
  context.fillStyle = '#ededed';
  context.font = '400 36px "Yu Mincho", "YuMincho", serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, canvas.width / 2, canvas.height / 2);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(canvas), transparent: true, opacity, depthTest: false, depthWrite: false,
  }));
  sprite.position.copy(position);
  sprite.scale.set(size * 4, size, 1);
  sprite.renderOrder = 5;
  return sprite;
}
function surface(covariance: number[][], scale: number) {
  const geometry = new THREE.BufferGeometry();
  const vertices = new Float32Array(DIRECTIONS.length * 3);
  DIRECTIONS.forEach((direction, i) => {
    const radius = directionalRms(covariance, direction) / scale;
    vertices[i * 3] = direction[0] * radius;
    vertices[i * 3 + 1] = direction[2] * radius;
    vertices[i * 3 + 2] = -direction[1] * radius;
  });
  const indices: number[] = [];
  for (let lat = 0; lat < LATITUDES; lat++) for (let lon = 0; lon < LONGITUDES; lon++) {
    const a = lat * (LONGITUDES + 1) + lon, b = a + LONGITUDES + 1;
    indices.push(a, b, a + 1, b, b + 1, a + 1);
  }
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}
function wireSurface(covariance: number[][], scale: number, dashed: boolean) {
  // Sparse meridians and parallels make overlapping surfaces easier to read.
  const points: THREE.Vector3[] = [];
  const point = (index: number) => xyz(DIRECTIONS[index]).multiplyScalar(directionalRms(covariance, DIRECTIONS[index]) / scale);
  for (let lat = 4; lat < LATITUDES; lat += 4) for (let lon = 0; lon < LONGITUDES; lon++) {
    const i = lat * (LONGITUDES + 1) + lon;
    points.push(point(i), point(i + 1));
  }
  for (let lon = 0; lon < LONGITUDES; lon += 8) for (let lat = 0; lat < LATITUDES; lat++) {
    const i = lat * (LONGITUDES + 1) + lon;
    points.push(point(i), point(i + LONGITUDES + 1));
  }
  const material = dashed
    ? new THREE.LineDashedMaterial({ color: 0xb9b9b9, dashSize: .045, gapSize: .035, transparent: true, opacity: .75 })
    : new THREE.LineBasicMaterial({ color: 0xf0f0f0, transparent: true, opacity: .55 });
  const lines = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(points), material);
  if (dashed) lines.computeLineDistances();
  return lines;
}

export function DiffusionScene({ covariance, referenceCovariance, comparisonCovariance,
  microphonePositions, sourceDirections = [], language, commonScale }: DiffusionSceneProps) {
  const host = useRef<HTMLElement>(null);
  const contextRef = useRef<SceneContext | null>(null);
  const [view, setView] = useState<'response' | 'array'>('response');
  const [webglError, setWebglError] = useState(false);
  const jp = language === 'jp';
  const values = useMemo(() => {
    const maximum = (matrix?: number[][]) => matrix ? Math.max(...DIRECTIONS.map(direction => directionalRms(matrix, direction))) : 0;
    const current = maximum(covariance), reference = maximum(referenceCovariance), comparison = maximum(comparisonCovariance);
    const scale = commonScale !== undefined && Number.isFinite(commonScale) && commonScale > 0
      ? commonScale : Math.max(current, reference, comparison) || 1;
    return { current, reference, comparison, scale };
  }, [covariance, referenceCovariance, comparisonCovariance, commonScale]);

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false }); }
    catch {
      // WebGL availability is external browser state, discovered when its context is created.
      // oxlint-disable-next-line react/react-compiler
      setWebglError(true);
      return;
    }
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#080808');
    const group = new THREE.Group();
    scene.add(group);
    scene.add(new THREE.AmbientLight(0xffffff, 1.2));
    const light = new THREE.DirectionalLight(0xffffff, 2.3);
    light.position.set(2, 4, 3);
    scene.add(light);
    const camera = new THREE.PerspectiveCamera(38, 1, .0001, 1000);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.setAttribute('aria-hidden', 'true');
    element.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = .08;
    controls.enablePan = false;
    const context: SceneContext = { group, camera, controls, extent: 1, view: '', reset: () => {
      camera.position.set(context.extent * 2.2, context.extent * 1.6, context.extent * 2.6);
      controls.target.set(0, 0, 0);
      controls.update();
    } };
    contextRef.current = context;
    context.reset();
    const resize = () => {
      const width = Math.max(element.clientWidth, 1), height = Math.max(element.clientHeight, 1);
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();
    const lost = (event: Event) => { event.preventDefault(); setWebglError(true); };
    const restored = () => setWebglError(false);
    renderer.domElement.addEventListener('webglcontextlost', lost);
    renderer.domElement.addEventListener('webglcontextrestored', restored);
    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', lost);
      renderer.domElement.removeEventListener('webglcontextrestored', restored);
      disposeObjects(scene);
      renderer.dispose();
      renderer.domElement.remove();
      if (contextRef.current === context) contextRef.current = null;
    };
  }, []);

  useEffect(() => {
    const context = contextRef.current;
    if (!context) return;
    const { group, camera, controls } = context;
    disposeObjects(group);
    group.clear();
    const positions = microphonePositions.filter(finitePoint);
    const physical = view === 'array';
    const extent = physical ? Math.max(.01, ...positions.map(p => Math.hypot(...p.slice(0, 3)))) * 1.6
      : Math.max(1, values.current / values.scale, values.reference / values.scale, values.comparison / values.scale) * 1.2;
    if (!physical) {
      group.add(new THREE.Mesh(surface(covariance, values.scale), new THREE.MeshStandardMaterial({
        color: 0xd6d6d6, roughness: .82, metalness: 0, side: THREE.DoubleSide,
        transparent: true, opacity: .7, depthWrite: false,
      })));
      if (referenceCovariance) group.add(wireSurface(referenceCovariance, values.scale, false));
      if (comparisonCovariance) group.add(wireSurface(comparisonCovariance, values.scale, true));
      sourceDirections.filter(finitePoint).forEach((source, i) => {
        if (!Math.hypot(...source.slice(0, 3))) return;
        const direction = xyz(source).normalize();
        group.add(new THREE.ArrowHelper(direction, new THREE.Vector3(), extent * .98, 0x777777, extent * .06, extent * .025));
        group.add(label(`S${i + 1}`, direction.multiplyScalar(extent * 1.08), extent * .075, .85));
      });
    } else {
      positions.forEach((position, i) => {
        const point = xyz(position);
        const marker = new THREE.Mesh(new THREE.SphereGeometry(extent * .026, 16, 12), new THREE.MeshBasicMaterial({ color: 0xeeeeee }));
        marker.position.copy(point);
        group.add(marker);
        group.add(label(`M${i + 1}`, point.clone().add(new THREE.Vector3(0, extent * .08, 0)), extent * .065));
        group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), point]), new THREE.LineBasicMaterial({ color: 0x434343 })));
      });
      const grid = new THREE.GridHelper(extent * 2, 8, 0x454545, 0x222222);
      group.add(grid);
    }
    AXES.forEach(axis => {
      const direction = xyz(axis.direction);
      group.add(new THREE.ArrowHelper(direction, new THREE.Vector3(), extent, 0x999999, extent * .045, extent * .018));
      const axisLabel = physical ? `${jp ? axis.jp : axis.en} / ${number(extent)} m` : jp ? axis.jp : axis.en;
      group.add(label(axisLabel, direction.multiplyScalar(extent * 1.16), extent * .075));
      const negative = xyz(axis.direction).multiplyScalar(-extent);
      const negativeLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints([negative, new THREE.Vector3()]), new THREE.LineDashedMaterial({ color: 0x3f3f3f, dashSize: extent * .035, gapSize: extent * .025 }));
      negativeLine.computeLineDistances();
      group.add(negativeLine);
    });
    const origin = new THREE.Mesh(new THREE.SphereGeometry(extent * .009, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    group.add(origin);
    context.extent = extent;
    camera.near = extent / 10000;
    camera.far = extent * 1000;
    camera.updateProjectionMatrix();
    controls.minDistance = extent * .35;
    controls.maxDistance = extent * 15;
    if (context.view !== view) { context.view = view; context.reset(); }
  }, [view, covariance, referenceCovariance, comparisonCovariance, microphonePositions, sourceDirections, language, values, jp]);

  const matrices = [{ label: jp ? '現在の推定' : 'Current estimate', matrix: covariance },
    ...(referenceCovariance ? [{ label: jp ? '参照' : 'Reference', matrix: referenceCovariance }] : []),
    ...(comparisonCovariance ? [{ label: jp ? '比較' : 'Comparison', matrix: comparisonCovariance }] : [])];

  return <section className="diffusion-scene" aria-label={jp ? '推定音場とマイク配置の3D表示' : '3D inferred-field and microphone-array views'}>
    <div className="diffusion-scene-toolbar">
      <fieldset className="diffusion-scene-modes" aria-label={jp ? '表示の種類' : 'View mode'}>
        <button type="button" aria-pressed={view === 'response'} onClick={() => setView('response')}>{jp ? '方向別の強さ' : 'Directional strength'}</button>
        <button type="button" aria-pressed={view === 'array'} onClick={() => setView('array')}>{jp ? 'マイク配置' : 'Microphone array'}</button>
      </fieldset>
      <button type="button" className="diffusion-scene-reset" onClick={() => contextRef.current?.reset()} disabled={webglError}>{jp ? '視点を戻す' : 'Reset view'}</button>
    </div>
    <figure className="diffusion-scene-viewport" ref={host} aria-label={view === 'response'
      ? jp ? '共通スケールの方向別RMS。数値表でも確認できます。' : 'Directional RMS on a shared scale. Values are also available in the table.'
      : jp ? 'メートル単位のマイク位置。数値表でも確認できます。' : 'Microphone positions in metres. Values are also available in the table.'}>
      {webglError && <div className="diffusion-scene-fallback">{jp ? 'WebGLを利用できません。下の数値表で確認できます。' : 'WebGL is unavailable. The numerical tables below remain available.'}</div>}
      <div className="diffusion-scene-guide">{jp ? 'ドラッグ：回転　スクロール：拡大' : 'Drag to rotate · Scroll to zoom'}</div>
      <div className="diffusion-scene-unit">{view === 'response' ? `r = RMS / ${number(values.scale)}` : `${microphonePositions.length} ${jp ? 'マイク' : 'microphones'} · m`}</div>
    </figure>
    {view === 'response' && <div className="diffusion-scene-legend">
      <span><i className="diffusion-scene-solid" />{jp ? '現在の推定' : 'Current estimate'}</span>
      {referenceCovariance && <span><i className="diffusion-scene-wire" />{jp ? '参照' : 'Reference'}</span>}
      {comparisonCovariance && <span><i className="diffusion-scene-dashed" />{jp ? '比較' : 'Comparison'}</span>}
      {sourceDirections.length > 0 && <span>S · {jp ? '既知の音源方向' : 'Known source direction'}</span>}
    </div>}
    <p className="diffusion-scene-caption">{view === 'response'
      ? jp ? '半径は、FOAの共分散から求めた方向別RMSです。各面を同じスケールで表示しています。部屋の音圧分布や、音源が存在する確率を示す図ではありません。'
        : 'Radius shows directional RMS from the FOA covariance. All surfaces share one scale. This is not a room-pressure map or a source-location probability map.'
      : jp ? '中心を原点にした実寸のマイク座標です。方向別RMSの形状とは別の座標スケールで表示しています。'
        : 'Microphone coordinates in metres, relative to the origin. This physical layout uses a different coordinate scale from the directional RMS view.'}</p>
    <details className="diffusion-scene-values" open={webglError || undefined}>
      <summary>{jp ? '軸方向の数値・マイク座標' : 'Axis values and microphone coordinates'}</summary>
      <div className="diffusion-scene-table-wrap"><table><caption>{jp ? '方向別RMS（表示用の縮尺を適用する前）' : 'Directional RMS before display scaling'}</caption><thead><tr><th>{jp ? '方向' : 'Direction'}</th>{matrices.map(item => <th key={item.label}>{item.label}</th>)}</tr></thead>
        <tbody>{AXES.flatMap(axis => [1, -1].map(sign => {
          const direction = axis.direction.map(value => value * sign);
          const name = sign === 1 ? jp ? axis.jp : axis.en : `−${axis.en.slice(-1)}`;
          return <tr key={`${axis.en}${sign}`}><th>{name}</th>{matrices.map(item => <td key={item.label}>{number(directionalRms(item.matrix, direction))}</td>)}</tr>;
        }))}</tbody></table></div>
      <div className="diffusion-scene-table-wrap"><table><caption>{jp ? 'マイク位置（m）' : 'Microphone positions (m)'}</caption><thead><tr><th>{jp ? 'マイク' : 'Mic'}</th><th>X</th><th>Y</th><th>Z</th></tr></thead><tbody>{microphonePositions.map((position, index) => <tr key={index}><th>M{index + 1}</th>{[0, 1, 2].map(axis => <td key={axis}>{Number.isFinite(position[axis]) ? number(position[axis]) : '—'}</td>)}</tr>)}</tbody></table></div>
    </details>
  </section>;
}

export default DiffusionScene;
