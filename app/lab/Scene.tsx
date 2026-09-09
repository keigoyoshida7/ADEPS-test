'use client';
import { useT } from './i18n';
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
type Props = {
  speakers: number[][];
  training: number[][];
  heldout: number[][];
  room: number[];
  selected: number;
  onSelect: (n: number) => void;
  compact?: boolean;
  origin?: number[];
  showRoom?: boolean;
};
export default function Scene({
  speakers,
  training,
  heldout,
  room,
  selected,
  onSelect,
  compact = false,
  origin,
  showRoom = true,
}: Props) {
  const t = useT();

  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!host.current) return;
    const el = host.current;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setError('WebGLを使用できません。配置表と解析は利用できます。');
      return;
    }
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#080808');
    const camera = new THREE.PerspectiveCamera(40, 1, 0.001, 1000);
    const scale = Math.max(...room);
    const base = origin || [0, 0, 0];
    const center = new THREE.Vector3(
      base[0] + room[0] / 2,
      base[2] + room[2] / 2,
      -(base[1] + room[1] / 2),
    );
    camera.position.set(
      center.x + scale * 0.95,
      scale * 0.95,
      center.z + scale * 1.15,
    );
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(center);
    controls.enableDamping = true;
    controls.minDistance = scale * 0.2;
    controls.maxDistance = scale * 3;
    scene.add(new THREE.AmbientLight(0xffffff, 2));
    const light = new THREE.DirectionalLight(0xffffff, 3);
    light.position.set(scale, scale, scale);
    scene.add(light);
    const grid = new THREE.GridHelper(scale, 12, 0x505050, 0x262626);
    grid.position.set(center.x, base[2], center.z);
    scene.add(grid);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(room[0], room[2], room[1])),
      new THREE.LineBasicMaterial({
        color: 0x656565,
        transparent: true,
        opacity: 0.65,
      }),
    );
    edges.position.copy(center);
    if (showRoom) scene.add(edges);
    if (!showRoom) {
      edges.geometry.dispose();
      (edges.material as THREE.Material).dispose();
    }
    const pickables: THREE.Object3D[] = [];
    function marker(points: number[][], color: number, kind: string) {
      points.forEach((p, i) => {
        const chosen = kind === 'S' && i === selected;
        const r = scale * (compact ? 0.024 : 0.013) * (chosen ? 1.45 : 1);
        const geo =
          kind === 'S'
            ? new THREE.BoxGeometry(r * 1.9, r * 1.4, r * 1.9)
            : kind === 'V'
              ? new THREE.OctahedronGeometry(r)
              : new THREE.SphereGeometry(r * 0.8, 16, 12);
        const mesh = new THREE.Mesh(
          geo,
          new THREE.MeshBasicMaterial({ color: chosen ? 0xffffff : color }),
        );
        mesh.position.set(p[0], p[2], -p[1]);
        mesh.userData = { kind, index: i };
        scene.add(mesh);
        if (kind === 'S') pickables.push(mesh);
        const canvas = document.createElement('canvas');
        canvas.width = 192;
        canvas.height = 64;
        const ctx = canvas.getContext('2d')!;
        ctx.fillStyle = chosen
          ? '#fff'
          : `#${color.toString(16).padStart(6, '0')}`;
        ctx.font = '400 40px "Yu Mincho", "YuMincho", serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${kind}${i + 1}`, 96, 42);
        const sprite = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: new THREE.CanvasTexture(canvas),
            depthTest: false,
          }),
        );
        sprite.position
          .copy(mesh.position)
          .add(new THREE.Vector3(0, r * 2.3, 0));
        sprite.scale.set(scale * 0.18, scale * 0.06, 1);
        scene.add(sprite);
        if (kind === 'S' && !compact) {
          const line = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints([
              mesh.position,
              new THREE.Vector3(p[0], base[2], -p[1]),
            ]),
            new THREE.LineBasicMaterial({
              color,
              transparent: true,
              opacity: 0.15,
            }),
          );
          scene.add(line);
        }
      });
    }
    marker(speakers, 0xdfdfdf, 'S');
    marker(training, 0x999999, 'M');
    marker(heldout, 0xbdbdbd, 'V');
    const ray = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let down = [0, 0];
    const start = (e: PointerEvent) => {
      down = [e.clientX, e.clientY];
    };
    const click = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        (-(e.clientY - rect.top) / rect.height) * 2 + 1,
      );
      ray.setFromCamera(pointer, camera);
      const hit = ray.intersectObjects(pickables)[0];
      if (hit) onSelect(hit.object.userData.index);
    };
    renderer.domElement.addEventListener('pointerdown', start);
    renderer.domElement.addEventListener('pointerup', click);
    const resize = new ResizeObserver(() => {
      const w = el.clientWidth,
        h = el.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    resize.observe(el);
    let frame = 0;
    function loop() {
      frame = requestAnimationFrame(loop);
      controls.update();
      renderer.render(scene, camera);
    }
    loop();
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', start);
      renderer.domElement.removeEventListener('pointerup', click);
      scene.traverse((o) => {
        if ((o as THREE.Mesh).geometry) (o as THREE.Mesh).geometry.dispose();
        const mats = (o as THREE.Mesh).material;
        if (mats)
          (Array.isArray(mats) ? mats : [mats]).forEach((m) => {
            if ('map' in m) (m.map as THREE.Texture | null)?.dispose();
            m.dispose();
          });
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [
    speakers,
    training,
    heldout,
    room,
    selected,
    onSelect,
    compact,
    origin,
    showRoom,
  ]);
  return (
    <div
      className="scene"
      ref={host}
      role="img"
      aria-label={t('スピーカー・測定点の3D配置。配置表でも値を確認できます。')}
    >
      {error && <div className="scene-error">{t(error)}</div>}
      <div className="scene-guide">
        {t('ドラッグ：回転 スクロール：拡大 Sをクリック：選択')}
      </div>
    </div>
  );
}
