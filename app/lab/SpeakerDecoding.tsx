'use client';
import { useMemo, useState } from 'react';
import { ArrowRight, Download, ExternalLink } from 'lucide-react';
import Scene from './Scene';
import ADEPSProcessDiagram from './ADEPSProcessDiagram';
import layout from '../../public/reference/speaker-layout-12ch.json';
import { buildDecoder, decodeCoefficients, foaDirection, sourceDirection, rightFrontUpToFrontLeftUp } from './decodingMath';
import './SpeakerDecoding.css';

const LISTENER = [0, 0, 1.2];
const LISTENER_MARKER = [LISTENER];
const EMPTY_POINTS: number[][] = [];
// These bounds fit the illustration. They do not represent measured room walls.
const VIEW_ORIGIN = [0, 1, 2].map(axis => Math.min(0, ...layout.speakers.map(p => p.position_m[axis])) - (axis === 2 ? 0 : .5));
const VIEW_SIZE = [0, 1, 2].map(axis => Math.max(0, ...layout.speakers.map(p => p.position_m[axis])) - VIEW_ORIGIN[axis] + .5);
const CHANNELS = ['W', 'Y', 'Z', 'X'];
const fixed = (value: number, digits = 4) => Math.abs(value) < .5 * 10 ** -digits ? (0).toFixed(digits) : value.toFixed(digits);
type Props = { language: 'jp' | 'en'; active: boolean; onNavigate: (page: string) => void };

export default function SpeakerDecoding({ language, active, onNavigate }: Props) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [planar, setPlanar] = useState(false);
  const [azimuth, setAzimuth] = useState(0);
  const [elevation, setElevation] = useState(0);
  const [logLambda, setLogLambda] = useState(-3);
  const [selected, setSelected] = useState(0);
  const speakers = useMemo(() => layout.speakers.map(({ position_m: p }) => [p[0], p[1], planar ? LISTENER[2] : p[2]]), [planar]);
  const decoder = useMemo(() => buildDecoder(speakers.map(rightFrontUpToFrontLeftUp), rightFrontUpToFrontLeftUp(LISTENER), 10 ** logLambda), [speakers, logLambda]);
  const coefficients = useMemo(() => foaDirection(sourceDirection(azimuth, elevation)), [azimuth, elevation]);
  const result = useMemo(() => decodeCoefficients(decoder, coefficients), [decoder, coefficients]);
  const maxGain = Math.max(...result.gains.map(Math.abs), 1e-12);
  const exportCSV = () => {
    const rows = [
      '# ADEPS-test angular FOA speaker decoder; independent of the learned prior',
      `# source=public/reference/speaker-layout-12ch.json; saved project sha256=${layout.source.sha256}`,
      `# layout=${planar ? 'virtual planar comparison; z=listener height' : 'saved project coordinates; physical positions and routes not verified'}`,
      `# assumed_listener_raw_m=${LISTENER.join(' ')}; rawX=right; rawY=front; rawZ=up; FOA_xyz=raw(Y,-X,Z)`,
      `# convention=ACN/N3D; column order=W Y Z X; lambda=${decoder.regularization}; rank=${decoder.rank}`,
      '# feeds=D*FOA; D=Y*inverse(transpose(Y)*Y+lambda*I); negative values mean polarity inversion',
      '# no distance compensation; no room correction; no hardware routing; no output level limiting',
      `# channel_order_note=${layout.channel_order_note.en}` ,
      'speaker_id,W,Y,Z,X',
      ...decoder.matrix.map((row, i) => [`S${i + 1}`, ...row.map(v => v.toPrecision(15))].join(',')),
    ];
    const url = URL.createObjectURL(new Blob([rows.join('\n') + '\n'], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `ADEPS-test-FOA-decoder-${planar ? 'planar' : 'saved-12ch'}.csv`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return <div className="speaker-decoding">
    <section className="decoding-intro">
      <span className="eyebrow">AFTER RECONSTRUCTION · SPEAKER DECODING</span>
      <h2>{l('復元した音場を、スピーカーに分ける', 'Turn reconstructed Ambisonics into speaker feeds')}</h2>
      <p>{l('ADEPSで復元するAmbisonicsと、スピーカーへ配るデコーディングは別の工程です。ここでは保存済みの12ch配置から変換行列を計算し、配置による違いを確認できます。', 'Ambisonics reconstruction and decoding to loudspeakers are separate stages. This page calculates a decoder from the saved 12-channel layout so you can inspect how that layout affects the conversion.')}</p>
      <ADEPSProcessDiagram language={language} kind="decode"/>
      <p className="decoding-note">{l('W/Y/Z/Xはスピーカー番号ではありません。4chをそのまま4台へつなぐと、ここで示すデコーディングにはなりません。このページは行列の確認用で、復元WAVの自動読込・音声出力・実機への送信は行いません。', 'W/Y/Z/X are not speaker numbers. Connecting the four channels directly to four speakers does not perform this decoding. This page inspects the matrix; it does not automatically load reconstructed WAVs, play audio, or send signals to hardware.')}</p>
    </section>

    <section className="decoding-workspace">
      <div className="decoding-layout-panel">
        <div className="decoding-section-title"><span className="eyebrow">01 · LAYOUT</span><h3>{l('保存済みの12ch配置', 'The saved 12-channel layout')}</h3></div>
        <label className="decoding-select">{l('比較する配置', 'Layout to inspect')}
          <select value={planar ? 'planar' : 'original'} onChange={event => setPlanar(event.target.value === 'planar')}>
            <option value="original">{l('保存プロジェクト：12ch', 'Saved project: 12 channels')}</option>
            <option value="planar">{l('比較用：全て聴取点と同じ高さ', 'Comparison: all speakers at listener height')}</option>
          </select>
        </label>
        {active && <Scene speakers={speakers} training={LISTENER_MARKER} heldout={EMPTY_POINTS} room={VIEW_SIZE}
          origin={VIEW_ORIGIN} showRoom={false} selected={selected} onSelect={setSelected}/>}
        <p className="decoding-note">{l('S1〜S12＝保存出力ID順のスピーカー。丸印M1＝仮定した聴取基準点 [0, 0, 1.2] m。表示は元の座標を保ち、X右・Y前・Z上として扱います。格子は表示補助で、部屋の寸法・現地の設置位置・接続先は未確認です。', 'S1–S12 follow the saved output IDs. The round M1 marker is an assumed listener at [0, 0, 1.2] m. Displayed coordinates preserve the original values, interpreted as X right, Y front, Z up. The grid is only a visual aid. Room dimensions, installed positions, and physical routes have not been verified.')}</p>
        <p className="decoding-note">{layout.channel_order_note[language]}</p>
        <a className="decoding-source" href={`${import.meta.env.BASE_URL}reference/speaker-layout-12ch.json`} target="_blank" rel="noreferrer">{l('元の配置データ', 'Original layout data')} <ExternalLink size={13}/></a>
        <div className="decoding-stats">
          <div><small>{l('独立な空間成分', 'Independent spatial modes')}</small><strong>{decoder.rank} / 4</strong></div>
          <div><small>{l('配置行列Yの条件数', 'Condition number of Y')}</small><strong>{decoder.condition === null ? '∞' : decoder.condition.toFixed(2)}</strong></div>
          <div><small>{l('選択中', 'Selected speaker')}</small><strong>S{selected + 1} <span className="decoding-speaker-label">{layout.speakers[selected].label}</span></strong><small>{speakers[selected].map(v => v.toFixed(2)).join(' / ')} m</small></div>
        </div>
        {decoder.rank < 4 ? <p className="decoding-warning">{l('この平面配置ではZ成分を再現できません。正則化で計算を安定させても、足りない上下方向の情報は増えません。仰角を上げると、右の成分比較で違いを確認できます。', 'This planar layout cannot reproduce the Z mode. Regularization stabilizes the calculation but cannot add the missing vertical capability. Increase elevation to see the difference in the mode comparison.')}</p>
          : <p className="decoding-note">{l('4成分を代数的に扱える配置です。ただし全台が上方にあり、成分を合わせるための打ち消しや大きなゲインが生じ得ます。条件数やランクは、部屋全体の再生品質を保証しません。', 'This layout can represent four modes algebraically. With all speakers elevated, matching modes can require cancellation and large gains. Rank and condition number do not guarantee playback quality throughout a room.')}</p>}
      </div>

      <div className="decoding-gains-panel">
        <div className="decoding-section-title"><span className="eyebrow">02 · DECODER</span><h3>{l('音の方向を変えて、配り方を見る', 'Move a virtual source and inspect the feeds')}</h3></div>
        <p className="decoding-note">{l('単位振幅の平面波を仮定した計算例です。復元結果の音源位置を検出しているわけではありません。', 'This example assumes a unit-amplitude plane wave. It is not a detected source location from a reconstruction.')}</p>
        <div className="decoding-controls">
          <label><span>{l('方位角', 'Azimuth')}<output>{azimuth}°</output></span><input type="range" min="-180" max="180" step="1" value={azimuth} onChange={e => setAzimuth(Number(e.target.value))}/></label>
          <label><span>{l('仰角', 'Elevation')}<output>{elevation}°</output></span><input type="range" min="-90" max="90" step="1" value={elevation} onChange={e => setElevation(Number(e.target.value))}/></label>
          <label><span>{l('正則化 λ', 'Regularization λ')}<output>{decoder.regularization.toPrecision(2)}</output></span><input type="range" min="-6" max="0" step=".25" value={logLambda} onChange={e => setLogLambda(Number(e.target.value))}/></label>
        </div>
        <p className="decoding-note">{l('方位0°＝前（元の+Y）、+90°＝左（元の−X）。正の仰角は上方向です。', 'Azimuth 0° is front (original +Y), +90° is left (original −X). Positive elevation points upward.')}</p>
        <div className="decoding-gain-list" aria-label={l('スピーカー別の符号付きゲイン', 'Signed gain per speaker')}>
          {result.gains.map((gain, i) => <button type="button" key={i} aria-pressed={selected === i} className={selected === i ? 'selected' : ''} onClick={() => setSelected(i)}>
            <span>S{i + 1}</span><span className="decoding-gain-track" aria-hidden="true"><i style={{ left: `${gain < 0 ? 50 + gain / maxGain * 50 : 50}%`, width: `${Math.abs(gain) / maxGain * 50}%` }}/></span><output>{fixed(gain)}</output>
          </button>)}
        </div>
        <p className="decoding-note">{l('負のゲインは極性反転です。棒の中央が0、左右が符号、長さはこの方向での最大絶対値を基準にします。値は音量制限やラウドネス正規化をしていません。', 'A negative gain reverses polarity. Bars are centered on zero and scaled to the largest absolute gain for this direction. Values have no output limiting or loudness normalization.')}</p>
        <div className="decoding-mode-table"><table><caption>{l('目標aと、配分後の成分Yᵀg', 'Target a and modes after decoding, Yᵀg')}</caption><thead><tr><th>{l('成分', 'Mode')}</th><th>{l('目標', 'Target')}</th><th>{l('配分後', 'Decoded')}</th></tr></thead><tbody>
          {CHANNELS.map((name, i) => <tr key={name}><th>{name}</th><td>{fixed(coefficients[i])}</td><td>{fixed(result.reconstructed[i])}</td></tr>)}
        </tbody></table></div>
        <p className="decoding-note">{l('成分の相対誤差', 'Relative mode error')}: {((result.relativeError ?? 0) * 100).toFixed(2)}% · {l('行列内の計算値で、実際の音圧測定値ではありません。', 'An algebraic result, not a measured pressure error.')}</p>
      </div>
    </section>

    <section className="decoding-method">
      <div className="decoding-section-title"><span className="eyebrow">03 · USE THE MATRIX</span><h3>{l('4成分を12出力に変換する', 'Convert four components to twelve outputs')}</h3></div>
      <p>{l('復元FOAの各サンプルa(t)に、12行×4列のDを掛けると12chのスピーカー信号になります。Dは配置とλで決まり、方位角・仰角のスライダーでは変わりません。学習済みモデルはこの変換には使いません。', 'Multiply each reconstructed FOA sample a(t) by the 12 × 4 matrix D to obtain twelve speaker feeds. D depends on the layout and λ; the source-angle sliders do not change it. This conversion uses no trained model.')}</p>
      <button type="button" className="decoding-export" onClick={exportCSV}><Download size={16}/>{l('デコーダー行列をCSVで保存', 'Download decoder matrix as CSV')}</button>
      <details><summary>{l('変換式・全係数・対象範囲', 'Equations, complete matrix, and scope')}</summary>
        <p>{l('保存配置のX右・Y前・Z上を、Ambisonicsのx前・y左・z上へ [x,y,z]=[Y,−X,Z] と回転し、聴取点との差分を使います。', 'Saved X-right/Y-front/Z-up coordinates are rotated into Ambisonics x-front/y-left/z-up as [x,y,z]=[Y,−X,Z], relative to the assumed listener.')}</p>
        <p>{l('聴取点から各スピーカーへ向かう単位方向をd=(dx,dy,dz)とし、Yの各行を[1,√3dy,√3dz,√3dx]とします。ACN/N3D規約の一次Ambisonics（FOA）を使います。', 'For each unit direction d=(dx,dy,dz) from the listener to a speaker, a row of Y is [1,√3dy,√3dz,√3dx]. The input uses first-order Ambisonics (FOA) in ACN/N3D convention.')}</p>
        <pre>D = Y (YᵀY + λI)⁻¹{'\n'}g = D a{'\n'}â = Yᵀg</pre>
        <p>{l('これは正則化した最小ノルムのモードマッチングです。大きいλはゲインを抑える一方、目標成分とのずれを増やします。YのランクはYᵀYの最大固有値×10⁻¹⁰を閾値として計算し、ランク不足の条件数は∞と表示します。', 'This is regularized minimum-norm mode matching. Increasing λ reduces gains while increasing mode mismatch. Rank uses a threshold of 10⁻¹⁰ times the largest eigenvalue of YᵀY. A rank-deficient layout displays an infinite condition number.')}</p>
        <div className="decoding-matrix-scroll"><table><caption>{l('Dの全係数（保存出力ID × FOA成分）', 'Complete D matrix (saved output ID × FOA component)')}</caption><thead><tr><th>{l('出力', 'Output')}</th>{CHANNELS.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>{decoder.matrix.map((row, i) => <tr key={i}><th>S{i + 1} · {layout.speakers[i].label}</th>{row.map((v, j) => <td key={j}>{fixed(v, 6)}</td>)}</tr>)}</tbody></table></div>
        <p>{l('角度だけの基礎モデルです。距離による減衰・到達時間、スピーカー指向性、部屋の反射、機器ごとのレベルやルーティングは含みません。実際の配置・規約・接続先を合わせ、必要な距離補償や出力レベル調整を別途行うことが、スピーカー環境での検証につながります。', 'This is a basic angular model. It excludes distance attenuation and arrival time, speaker directivity, room reflections, hardware levels, and routing. Testing on speakers requires matching the actual layout, channel convention, and destinations, then handling distance compensation and output levels separately.')}</p>
        <p>{l('デコードはADEPS推論後の独立した再生処理です。この配置での行列計算は、ADEPSの推定精度や論文の再現を示す評価ではありません。', 'Decoding is a separate playback stage after ADEPS inference. This layout-based matrix calculation does not evaluate ADEPS reconstruction accuracy or establish reproduction of the paper.')}</p>
      </details>
      <button type="button" className="decoding-back" onClick={() => onNavigate('diffusion')}>{l('復元・比較へ戻る', 'Go to reconstruction & comparison')} <ArrowRight size={15}/></button>
    </section>
  </div>;
}
