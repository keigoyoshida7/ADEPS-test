import { ArrowDown, CornerDownRight, LockKeyhole, Repeat2 } from 'lucide-react';
import './ADEPSProcessDiagram.css';

type Props = { language: 'jp' | 'en'; kind: 'train' | 'reconstruct' | 'decode'; focus?: 'observe' | 'linear' | 'dps' | 'compare' };
type Node = { id: string; title: string; symbol: string; detail: string };

export default function ADEPSProcessDiagram({ language, kind, focus }: Props) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  let title: string, caption: string, nodes: Node[];
  if (kind === 'train') {
    title = l('学習：正解から「戻し方」を覚える', 'Training: learn to recover clean coefficients');
    caption = l('36複素成分＝実部36＋虚部36。rは各例のRMS、sは学習データから決める固定RMS。雑音は正規化・圧縮した係数に加えます。マイク配置や応答Vは、この学習へ渡しません。', '36 complex coefficients are packed as 36 real + 36 imaginary channels. Here r is the per-example RMS and s is a fixed RMS from training data. Noise is added after normalization and compression. No microphone geometry or response V enters training.');
    nodes = [
      { id: 'target', title: l('理想N5の正解', 'Ideal N5 target'), symbol: 'x = H(a / r) / s', detail: l('音声＋室内応答から生成', 'Rendered from speech + room responses') },
      { id: 'noise', title: l('雑音を加える', 'Add training noise'), symbol: 'x + σε', detail: l('ノイズ強度σを変えて学ぶ', 'Train across noise scales σ') },
      { id: 'denoiser', title: l('Denoiserで推定', 'Denoise'), symbol: 'x̂ = Dθ(x + σε, σ)', detail: l('時間・周波数・成分をまとめて推定', 'Joint time–frequency–channel estimation') },
      { id: 'loss', title: l('正解との誤差', 'Compare with the target'), symbol: 'x̂ ↔ x', detail: l('重み付き誤差からθを更新', 'Update θ using the weighted error') },
    ];
  } else if (kind === 'reconstruct') {
    title = l('復元：同じ観測から、Linearと拡散を比べる', 'Reconstruction: compare Linear and diffusion from one observation');
    caption = l('シミュレーションで正解aから観測pを作ります。復元時に渡すのはpとVで、正解aは評価用に分けて保持します。推論中にモデルの重みθは更新しません。', 'Simulation creates p from a known reference a. Reconstruction receives p and V; the reference is held separately for evaluation. Model weights θ stay fixed during inference.');
    nodes = [
      { id: 'observe', title: l('仮想マイクの観測', 'Virtual-array observation'), symbol: 'p = Va + ν', detail: l('信号pと既知の応答Vを渡す', 'Provide signals p and known response V') },
      { id: 'linear', title: l('線形推定', 'Linear estimate'), symbol: 'âLinear = Ep', detail: l('Vから作るE・比較の基準', 'E comes from V; also the baseline') },
      { id: 'dps', title: l('拡散で繰り返し修正', 'Iterative DPS'), symbol: 'Dθ  +  V', detail: l('モデルによる推定＋観測との整合', 'Denoising + observation consistency') },
      { id: 'n5', title: l('理想N5を推定', 'Estimate ideal N5'), symbol: 'â · 36 complex', detail: l('各段階の係数を保存', 'Save intermediate coefficient estimates') },
      { id: 'compare', title: l('FOAを表示・書出', 'View / export FOA'), symbol: 'W · Y · Z · X', detail: l('先頭4成分で比較・試聴', 'Compare and audition the first four modes') },
    ];
  } else {
    title = l('再生：4つの空間成分を12台へ配る', 'Playback: distribute four spatial modes to twelve speakers');
    caption = l('復元モデルDθと、スピーカーへの変換行列Dは別のものです。ここでは行列を計算・表示します。実際のWAV変換と機器への出力は別途接続します。', 'The reconstruction model Dθ and speaker decoder matrix D are different. This page calculates and displays D. Applying it to WAV files and routing audio to hardware are separate steps.');
    nodes = [
      { id: 'foa', title: l('復元したFOA', 'Reconstructed FOA'), symbol: 'a(t) = [W, Y, Z, X]ᵀ', detail: l('ACN/N3Dの4ch音声', 'Four-channel ACN/N3D audio') },
      { id: 'decoder', title: l('配置に合わせて変換', 'Decode for this layout'), symbol: 'g(t) = D a(t)', detail: l('12行×4列の行列・学習なし', 'A 12 × 4 matrix; no training') },
      { id: 'feeds', title: l('12台分の信号', 'Twelve speaker feeds'), symbol: 'S1 · S2 · … · S12', detail: l('保存IDに対応する出力順', 'Output order follows saved speaker IDs') },
    ];
  }

  return <figure className={`adeps-process-diagram pd-${kind}`}>
    <figcaption>{title}</figcaption>
    <ol className="pd-nodes" style={{ '--pd-count': nodes.length } as React.CSSProperties}>
      {nodes.map((node, index) => <li key={node.id} className={`pd-node${node.id === focus ? ' is-focus' : ''}${node.id === 'decoder' ? ' has-layout-input' : ''}`}>
        {node.id === 'decoder' && <div className="pd-layout-input"><span>{l('保存した12chの座標 ＋ 仮定した聴取点', 'Saved 12-channel coordinates + assumed listener')}</span><ArrowDown size={16} aria-hidden="true"/></div>}
        <span className="pd-number">{String(index + 1).padStart(2, '0')}</span>
        <strong>{node.title}</strong><code>{node.symbol}</code><span className="pd-detail">{node.detail}</span>
        {node.id === 'loss' && <span className="pd-fixed"><Repeat2 size={12} aria-hidden="true"/>{l('θを更新して繰り返す', 'Update θ and repeat')}</span>}
        {node.id === 'dps' && <span className="pd-fixed"><Repeat2 size={12} aria-hidden="true"/>σ ↓ <LockKeyhole size={11} aria-hidden="true"/>{l('θは固定', 'θ fixed')}</span>}
      </li>)}
    </ol>
    {kind === 'train' && <div className="pd-reference-branch"><CornerDownRight size={17} aria-hidden="true"/><span>{l('正解xを誤差の計算にも渡す', 'The clean target x also goes to the error calculation')}</span><span className="pd-branch-end">x → x̂ − x</span></div>}
    {kind === 'reconstruct' && <>
      <div className="pd-reference-branch"><CornerDownRight size={17} aria-hidden="true"/><span>{l('評価だけの枝：正解FOA ↔ Linear / 拡散のFOA', 'Evaluation-only branch: reference FOA ↔ Linear / diffusion FOA')}</span><span className="pd-branch-end">{l('正解を復元器へ渡さない', 'Reference stays outside the estimator')}</span></div>
      <p className="pd-view-note">{l('3D形状はFOAの方向別RMSを表します。部屋の各地点の音圧や、音源位置を描いた図ではありません。', 'The 3D shape represents directional FOA RMS, not pressure at room positions or a source-location map.')}</p>
    </>}
    <p className="pd-caption">{caption}</p>
  </figure>;
}
