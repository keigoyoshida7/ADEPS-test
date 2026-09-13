'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './MicrophoneArrayView.css';

export type MicrophoneArrayViewProps = {
  /** Microphone centres in metres, in input/channel order: +X front, +Y left, +Z up. */
  positions: number[][];
  language: 'jp' | 'en';
  label?: string;
  caption?: string;
};
type View = 'reset' | 'top' | 'front' | 'side';
type Controls = { view: (preset: View) => void; zoom: (factor: number) => void };
const xyz = (p: number[]) => new THREE.Vector3(p[0], p[2], -p[1]);
const cm = (metres: number) => {
  const value = metres * 100;
  return value === 0 ? '0' : Math.abs(value) < .001 || Math.abs(value) >= 100000
    ? value.toExponential(2) : Number(value.toFixed(3)).toString();
};
function dispose(scene: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>(), textures = new Set<THREE.Texture>();
  scene.traverse(object => {
    const mesh = object as THREE.Mesh;
    if (mesh.geometry) geometries.add(mesh.geometry);
    if (mesh.material) (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).forEach(material => {
      materials.add(material);
      const map = (material as THREE.MeshBasicMaterial).map;
      if (map) textures.add(map);
    });
  });
  textures.forEach(texture => texture.dispose());
  materials.forEach(material => material.dispose());
  geometries.forEach(geometry => geometry.dispose());
}
function textLabel(text: string, position: THREE.Vector3, size: number) {
  const canvas = document.createElement('canvas');
  canvas.width = 384; canvas.height = 80;
  const context = canvas.getContext('2d');
  if (!context) return new THREE.Group();
  context.fillStyle = '#eeeeee';
  context.font = '400 34px "Yu Mincho", "YuMincho", serif';
  context.textAlign = 'center'; context.textBaseline = 'middle';
  context.fillText(text, 192, 40);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false, depthWrite: false }));
  sprite.position.copy(position); sprite.scale.set(size * 4.8, size, 1); sprite.renderOrder = 2;
  return sprite;
}

export function MicrophoneArrayView({ positions, language, label, caption }: MicrophoneArrayViewProps) {
  const jp = language === 'jp';
  const host = useRef<HTMLDivElement>(null), controlsRef = useRef<Controls | null>(null);
  const markersRef = useRef<THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial>[]>([]);
  const savedView = useRef<{ direction: THREE.Vector3; relativeDistance: number } | null>(null);
  const [selected, setSelected] = useState(0), [webglError, setWebglError] = useState(false);
  const data = useMemo(() => {
    const rows = Array.isArray(positions) ? positions : [];
    const invalid = rows.flatMap((p, i) => !Array.isArray(p) || p.length !== 3 || !p.every(Number.isFinite) ? [i + 1] : []);
    const points = invalid.length ? [] : rows;
    const ranges = [0, 1, 2].map(axis => points.length
      ? [Math.min(...points.map(p => p[axis])), Math.max(...points.map(p => p[axis]))] : [0, 0]);
    const extent = Math.max(.01, ...points.flatMap(p => p.map(Math.abs)));
    const raw = extent / 4, power = 10 ** Math.floor(Math.log10(raw));
    const spacing = [1, 2, 5, 10].find(step => step * power >= raw)! * power;
    return { points, invalid, ranges, spacing, extent: Math.ceil(extent / spacing) * spacing };
  }, [positions]);
  const index = Math.min(selected, data.points.length - 1), point = data.points[index];

  useEffect(() => {
    const element = host.current;
    if (!element || !data.points.length) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
    catch {
      // WebGL is external browser state, only known when creating the context.
      // oxlint-disable-next-line react/react-compiler
      setWebglError(true);
      return;
    }
    // oxlint-disable-next-line react/react-compiler
    setWebglError(false);
    const scene = new THREE.Scene(), extent = data.extent;
    scene.background = new THREE.Color('#080808');
    const camera = new THREE.PerspectiveCamera(38, 1, extent / 10000, extent * 1000);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.setAttribute('aria-hidden', 'true');
    element.appendChild(renderer.domElement);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true; orbit.enablePan = false;
    orbit.minDistance = extent * .2; orbit.maxDistance = extent * 60;
    const grid = new THREE.GridHelper(extent * 2, Math.round(extent * 2 / data.spacing), 0x454545, 0x242424);
    scene.add(grid);
    const axes = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
    axes.forEach((axis, i) => {
      const direction = xyz(axis);
      scene.add(new THREE.ArrowHelper(direction, new THREE.Vector3(), extent * 1.16, 0xa0a0a0, extent * .05, extent * .022));
      scene.add(textLabel(['+X', '+Y', '+Z'][i], direction.clone().multiplyScalar(extent * 1.3), extent * .2));
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([direction.clone().multiplyScalar(-extent), new THREE.Vector3()]),
        new THREE.LineDashedMaterial({ color: 0x454545, dashSize: extent * .035, gapSize: extent * .025 }));
      line.computeLineDistances(); scene.add(line);
    });
    scene.add(textLabel('0', new THREE.Vector3(0, -extent * .11, 0), extent * .13));
    const markers = data.points.map((p, i) => {
      const position = xyz(p);
      const marker = new THREE.Mesh(new THREE.SphereGeometry(extent * .023, 16, 12), new THREE.MeshBasicMaterial({ color: 0xb0b0b0 }));
      marker.position.copy(position); scene.add(marker);
      scene.add(textLabel(`M${i + 1}`, position.clone().add(new THREE.Vector3(0, extent * .14, 0)), extent * .18));
      scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([position, new THREE.Vector3(position.x, 0, position.z)]),
        new THREE.LineBasicMaterial({ color: 0x333333 })));
      return marker;
    });
    markersRef.current = markers;
    const fitDistance = () => {
      const vertical = THREE.MathUtils.degToRad(camera.fov / 2), horizontal = Math.atan(Math.tan(vertical) * camera.aspect);
      return extent * 1.6 / Math.sin(Math.min(vertical, horizontal));
    };
    const fit = (view: View) => {
      const distance = fitDistance();
      const direction = { reset: [1.6, 1.25, 1.8], top: [.00001, 1, 0], front: [1, 0, 0], side: [0, 0, -1] }[view];
      // Flush any remaining orbit momentum before applying an exact preset.
      orbit.enableDamping = false; orbit.update();
      orbit.target.set(0, 0, 0); camera.position.copy(new THREE.Vector3(...direction).normalize().multiplyScalar(distance));
      orbit.update(); orbit.enableDamping = true;
    };
    const controls: Controls = { view: fit, zoom: factor => {
      const distance = THREE.MathUtils.clamp(camera.position.length() * factor, orbit.minDistance, orbit.maxDistance);
      camera.position.setLength(distance); orbit.update();
    } };
    controlsRef.current = controls;
    let sized = false;
    const resize = () => {
      const width = Math.max(element.clientWidth, 1), height = Math.max(element.clientHeight, 1);
      const direction = sized ? camera.position.clone().normalize() : savedView.current?.direction.clone();
      const relativeDistance = sized ? camera.position.length() / fitDistance() : savedView.current?.relativeDistance ?? 1;
      renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix();
      if (direction) {
        camera.position.copy(direction.multiplyScalar(THREE.MathUtils.clamp(fitDistance() * relativeDistance, orbit.minDistance, orbit.maxDistance)));
        orbit.update();
      } else fit('reset');
      sized = true;
    };
    const observer = new ResizeObserver(resize); observer.observe(element); resize();
    const lost = (event: Event) => { event.preventDefault(); setWebglError(true); };
    const restored = () => setWebglError(false);
    renderer.domElement.addEventListener('webglcontextlost', lost);
    renderer.domElement.addEventListener('webglcontextrestored', restored);
    let frame = 0;
    const animate = () => { frame = requestAnimationFrame(animate); orbit.update(); renderer.render(scene, camera); };
    animate();
    return () => {
      savedView.current = { direction: camera.position.clone().normalize(), relativeDistance: camera.position.length() / fitDistance() };
      cancelAnimationFrame(frame); observer.disconnect(); orbit.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', lost);
      renderer.domElement.removeEventListener('webglcontextrestored', restored);
      dispose(scene); renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
      if (controlsRef.current === controls) { controlsRef.current = null; markersRef.current = []; }
    };
  }, [data]);

  useEffect(() => {
    markersRef.current.forEach((marker, i) => {
      marker.material.color.setHex(i === index ? 0xffffff : 0xb0b0b0);
      marker.scale.setScalar(i === index ? 1.6 : 1);
    });
  }, [index, data]);

  const presets: [View, string][] = [['reset', jp ? '視点を戻す' : 'Reset'], ['top', jp ? '上' : 'Top'], ['front', jp ? '正面' : 'Front'], ['side', jp ? '左側' : 'Left side']];
  return <section className="mic-array-view" aria-label={label || (jp ? 'マイクアレイの3D配置' : 'Microphone array in 3D')}>
    <header className="mav-heading"><span>MICROPHONE ARRAY / 3D</span><h3>{label || (jp ? 'マイクアレイの配置' : 'Microphone array geometry')}</h3>
      <p>{jp ? 'X：前　Y：左　Z：上。入力した座標を同じ縮尺で表示します。' : 'X: front · Y: left · Z: up. Supplied coordinates are shown at a uniform scale.'}</p></header>
    {!data.points.length ? <p className="mav-empty">{data.invalid.length
      ? (jp ? `座標が不正です：M${data.invalid.join('、M')}。各マイクに有限の X・Y・Z（m）が必要です。` : `Invalid coordinates: M${data.invalid.join(', M')}. Every microphone needs finite X, Y and Z coordinates in metres.`)
      : (jp ? 'マイク座標はまだありません。配置データを読み込むと表示します。' : 'No microphone coordinates yet. Load array positions to view them here.')}</p>
      : <>
        <div className="mav-toolbar"><div>{presets.map(([view, text]) => <button type="button" key={view} disabled={webglError} onClick={() => controlsRef.current?.view(view)}>{text}</button>)}</div>
          <div><button type="button" aria-label={jp ? '拡大' : 'Zoom in'} disabled={webglError} onClick={() => controlsRef.current?.zoom(.8)}>＋</button><button type="button" aria-label={jp ? '縮小' : 'Zoom out'} disabled={webglError} onClick={() => controlsRef.current?.zoom(1.25)}>−</button></div></div>
        <div ref={host} className="mav-viewport">
          <span className="mav-guide">{jp ? 'ドラッグで回転 · スクロールで拡大縮小' : 'Drag to rotate · Scroll to zoom'}</span>
          <span className="mav-scale">{jp ? 'グリッド1区画' : 'Grid interval'} {cm(data.spacing)} cm</span>
          {webglError && <p className="mav-fallback">{jp ? 'この環境では3Dを表示できません。下の座標一覧で配置を確認できます。' : '3D is unavailable in this environment. Use the coordinate table below to inspect the array.'}</p>}
        </div>
        <dl className="mav-extents">{data.ranges.map(([min, max], axis) => <div key={axis}><dt>{['X', 'Y', 'Z'][axis]} {jp ? '範囲' : 'range'}</dt><dd>{cm(min)} → {cm(max)} <small>cm</small><span>Δ {cm(max - min)} cm</span></dd></div>)}</dl>
        <div className="mav-selection"><span>{jp ? `${data.points.length}本のマイク · 番号で選択` : `${data.points.length} microphones · Select a number`}</span>
          <fieldset className="mav-numbers" aria-label={jp ? 'マイクを選択' : 'Select a microphone'}>{data.points.map((_, i) => <button type="button" key={i} aria-pressed={i === index} onClick={() => setSelected(i)}>M{i + 1}</button>)}</fieldset>
          <output className="mav-readout" aria-live="polite">M{index + 1}　{point.map((value, axis) => `${['X', 'Y', 'Z'][axis]} ${cm(value)} cm`).join('　/　')}</output>
        </div>
        <details className="mav-coordinates" open={webglError || undefined}><summary>{jp ? '全マイクの座標を見る' : 'Inspect every microphone coordinate'}</summary>
          <div><table><caption>{jp ? '入力順のマイク中心座標（cm）' : 'Microphone centres in input order (cm)'}</caption><thead><tr><th scope="col">{jp ? 'マイク' : 'Microphone'}</th>{['X', 'Y', 'Z'].map(axis => <th scope="col" key={axis}>{axis} / cm</th>)}</tr></thead>
            <tbody>{data.points.map((p, i) => <tr key={i} data-selected={i === index}><th scope="row">M{i + 1}</th>{p.map((value, axis) => <td key={axis}>{cm(value)}</td>)}</tr>)}</tbody></table></div>
        </details>
      </>}
    <p className="mav-caption">{caption && <>{caption} </>}{jp ? '点の中心がマイク座標です。マーカーの大きさは見やすさのための表示で、筐体の寸法ではありません。' : 'Point centres are microphone coordinates. Marker sizes aid visibility and do not represent physical capsule or housing dimensions.'}</p>
  </section>;
}

export default MicrophoneArrayView;
