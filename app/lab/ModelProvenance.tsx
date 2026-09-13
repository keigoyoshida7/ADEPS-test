import { ExternalLink } from 'lucide-react';
import tinyCard from '../../public/models/tiny-spatial-v1.json';
import spatialCard from '../../public/models/spatial-v1.json';
import { asset } from './assets';
import { useLanguage } from './i18n';
import './ModelProvenance.css';

type Kind = 'diffusion' | 'spatial' | 'all';
const SOURCE = 'https://github.com/keigoyoshida7/ADEPS-test/blob/main';
const PAPER_DATA = 'https://arxiv.org/html/2608.24558v3#S4';

export default function ModelProvenance({ kind = 'all' }: { kind?: Kind }) {
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const n = (value: number) => value.toLocaleString(language === 'jp' ? 'ja-JP' : 'en-US');
  const tiny = tinyCard.training;
  const spatial = spatialCard.training;
  const descriptions = [
    {
      kind: 'diffusion', card: tinyCard,
      title: l('旧ブラウザー版の小型prior', 'Archived small browser prior'),
      subtitle: l('ノイズのある空間係数から、元の係数を推定する学習', 'Learning to denoise spatial coefficients'),
      count: n(tiny.samples), unit: l('合成ベクトル', 'synthetic vectors'),
      steps: n(tiny.steps),
      pipeline: [
        l('方向・位相・強さを乱数で決め、1〜2方向の平面波と3本の弱い成分を合成する。', 'Generate 1–2 plane waves and 3 weaker components with random directions, phases and strengths.'),
        l('5次・36複素係数を圧縮し、強さを変えたガウス雑音を加える。', 'Compress 36 complex fifth-order coefficients, then add Gaussian noise at varying strengths.'),
        l('元の係数へ戻す誤差を学習する。推論では、このdenoiserと既知のVを反復計算へ接続する。', 'Learn to recover the clean coefficients. At inference, combine this denoiser with known V in iterative sampling.'),
      ],
      rows: [
        [l('生成したデータ', 'Generated data'), l(`${n(tiny.samples)}ベクトルで学習、別に生成した${n(tiny.validation_samples)}で検証。録音時間や部屋の数ではありません。`, `${n(tiny.samples)} training vectors and ${n(tiny.validation_samples)} separately generated validation vectors. These are not recording durations or room counts.`)],
        [l('乱数seed', 'Seeds'), l(`学習・初期化 ${tiny.seed}。検証データ ${tiny.seed + 1}、検証ノイズ ${tiny.seed + 2}（学習コードの生成規則）。`, `Training/initialization ${tiny.seed}; validation data ${tiny.seed + 1}; validation noise ${tiny.seed + 2} (generation rules in the training code).`)],
        [l('ネットワーク', 'Network'), l(`SiLU隠れ層2層×幅${tinyCard.hidden_channels}。実部・虚部72＋ノイズレベル特徴8。時間・周波数の各点を独立に処理。`, `Two SiLU hidden layers of width ${tinyCard.hidden_channels}. 72 real/imaginary inputs plus 8 noise-level features. Each time–frequency bin is processed independently.`)],
        [l('学習方法', 'Training'), `AdamW · lr 0.001 · weight decay 0.0001 · batch ${tiny.batch_size} · ${n(tiny.steps)} steps`],
        [l('学習した誤差', 'Objective'), l('EDM型の重み付きノイズ除去二乗誤差。σは0.002〜80の対数一様分布。4,000ステップ後の重みを保存。', 'EDM-style weighted squared denoising error. σ is log-uniform from 0.002 to 80. The weights after 4,000 steps are saved.')],
        [l('出典の記録', 'Provenance record'), l('外部学習ファイルは使わず手続き生成。source_sha256はnull。学習時のコードcommit/hashはモデルカードに記録されていません。', 'Procedural generation without an external training file; source_sha256 is null. The model card does not record the training-time code commit/hash.')],
      ],
      limitation: l('発話・残響の文脈は学習していません。マイク配列はpriorの学習入力に含めず、推論時にVとして与えます。線形推定より悪化する場合もあります。', 'No speech or reverberation context was learned. The prior is trained without array geometry; V is supplied at inference. Results may be worse than linear encoding.'),
      script: 'train_tiny_prior.py',
    },
    {
      kind: 'spatial', card: spatialCard,
      title: l('学習モデル比較・残差推定器', 'Learned model comparison · residual estimator'),
      subtitle: l('線形推定と物理情報から、係数の補正量を学習', 'Learning coefficient corrections from linear and physical information'),
      count: n(spatial.selected_checkpoint_unique_scenes), unit: l('合成シーン', 'synthetic scenes'),
      steps: n(spatial.steps),
      pipeline: [
        l('1〜5方向の平面波と拡散成分を合成し、仮想アレイでの観測を計算する。', 'Generate 1–5 plane waves plus diffuse components, and compute virtual-array observations.'),
        l('線形係数・E V・共分散・パワー・周波数から465個の特徴を作る。', 'Build 465 features from linear coefficients, E V, covariance, powers and frequency.'),
        l('正しい合成係数との差を教師あり学習。推論は1回の予測で、拡散サンプリングは行わない。', 'Learn the correction against known synthetic coefficients. Inference is one prediction, without diffusion sampling.'),
      ],
      rows: [
        [l('生成したデータ', 'Generated data'), l(`${n(spatial.selected_checkpoint_unique_scenes)}シーン×64周波数×8フレーム＝${n(spatial.samples)}ビン。検証は64シーン／${n(spatial.validation_samples)}ビン。各ビンは独立した録音ではありません。`, `${n(spatial.selected_checkpoint_unique_scenes)} scenes × 64 frequencies × 8 frames = ${n(spatial.samples)} bins. Validation: 64 scenes / ${n(spatial.validation_samples)} bins. Bins are not separate recordings.`)],
        [l('仮想条件', 'Simulated conditions'), l('理想無指向性4/5/6/8/12素子、半径4〜10 cm、SNR 10〜50 dB。1 Hz〜20 kHzの64対数周波数、5次または15次の係数。実際の音声STFTではありません。', 'Ideal omni arrays with 4/5/6/8/12 sensors, 4–10 cm radius and 10–50 dB SNR. 64 logarithmic frequencies from 1 Hz to 20 kHz; order 5 or 15 fields. These are not speech STFTs.')],
        [l('乱数seed', 'Seeds'), l(`初期化 ${spatial.seed}。学習 ${spatial.training_scene_seeds.join('–')}、検証 ${spatial.validation_scene_seeds.join('–')}。最終テストは90000以降を別に確保。`, `Initialization ${spatial.seed}; training ${spatial.training_scene_seeds.join('–')}; validation ${spatial.validation_scene_seeds.join('–')}. Seeds from 90000 are reserved separately for final tests.`)],
        [l('ネットワーク', 'Network'), l(`SiLU隠れ層${spatialCard.hidden_layers}層×幅${spatialCard.hidden_channels}。465入力特徴、36複素係数の残差を予測。`, `${spatialCard.hidden_layers} SiLU hidden layers of width ${spatialCard.hidden_channels}; 465 input features and residual predictions for 36 complex coefficients.`)],
        [l('学習方法', 'Training'), `AdamW · lr 0.0008 → 0.00004 (cosine) · weight decay 0.0001 · batch ${spatial.batch_size} · gradient clip 2`],
        [l('損失と重み選択', 'Loss and checkpoint selection'), l(`正規化した複素二乗誤差。先頭FOA 4成分の重み1、他32成分0.025。${n(spatial.steps)}ステップ中、別の検証で最良だった${n(spatial.selected_step)}を採用。`, `Normalized complex squared error: weight 1 for the first 4 FOA coefficients, 0.025 for the other 32. Separate validation selected step ${n(spatial.selected_step)} from ${n(spatial.steps)} training steps.`)],
        [l('出典の記録', 'Provenance record'), l('学習・検証のシーン条件リストのSHA-256を保存。生成データ全体のハッシュや、当時のコードcommit/hashとは異なります。', 'SHA-256 hashes record the training/validation scene-specification lists. These are not hashes of the complete generated tensors or the training-time code commit.')],
      ],
      limitation: l('共分散などは入力区間の全フレームを使うオフライン処理です。実録音・実測マイク応答は未学習で、合成検証の改善は実機の性能保証になりません。', 'Covariance and related features use all frames in the input window, making this offline processing. Real recordings and measured microphone responses were not used for training; synthetic gains do not establish hardware performance.'),
      script: 'train_spatial_model.py',
    },
  ].filter(description => kind === 'all' || kind === description.kind);

  return <section className="model-provenance" aria-label={l('モデルのデータと学習記録', 'Model data and training provenance')}>
    <div className="mp-heading">
      <span className="mp-eyebrow">DATA / TRAINING</span>
      <h3>{l('旧ブラウザーモデルの学習記録', 'Archived browser-model training records')}</h3>
      <p>{l('この欄は既存のtiny-spatial-v1とspatial-v1の記録です。この2モデルは独自の合成データを使い、論文の音声コーパス・室内応答、実際の会場録音、ADEPS公式の学習済み重みは使っていません。画面操作で再学習はしません。',
        'This section documents the existing tiny-spatial-v1 and spatial-v1 models. These two models use independent synthetic data, without the paper’s speech corpora or room responses, venue recordings, or official ADEPS weights. Interface actions do not retrain them.')}</p>
      {(kind === 'diffusion' || kind === 'all') && <p>{l('新しい音声priorは、ローカルTorch用の別モデルです。学習・評価の実記録は「音声と残響から学ぶ、拡散prior。」のパネルを参照してください。', 'The new speech prior is a separate model for local Torch. Its actual training and evaluation records appear in the “A diffusion prior trained on speech and reverberation” panel.')}</p>}
    </div>
    <div className="mp-data-origin">
      <p className="mp-data-status">{l('既存2モデルの学習：独自の合成データ ／ 論文のデータセットは未使用', 'Training of these two existing models: independent synthetic data / Paper datasets not used')}</p>
      <div className="mp-data-comparison">
        <article><h4>{l('論文のデータ', 'Data used in the paper')}</h4>
          <p>{l('HARPで生成したAmbisonics室内インパルス応答（ARIR）に、学習用のVCTK音声と評価用のWSJ0音声を畳み込んでいます。学習20,000シーン、評価1,000シーンです。',
            'Simulated Ambisonics room impulse responses (ARIRs) generated with HARP are convolved with VCTK speech for training and WSJ0 speech for evaluation: 20,000 training scenes and 1,000 evaluation scenes.')}</p>
          <a href={PAPER_DATA} target="_blank" rel="noreferrer">{l('出典：ADEPS論文 v3・§4', 'Source: ADEPS paper v3, §4')}<ExternalLink size={12}/></a>
        </article>
        <article><h4>{l('既存2モデルのデータ', 'Data used by the two existing models')}</h4>
          {(kind === 'diffusion' || kind === 'all') && <p>{l(`小型denoiserは、独自生成した${n(tiny.samples)}個の空間係数ベクトルで学習。HARPによる室内応答生成や、VCTK・WSJ0などの音声コーパスは使用していません。`,
            `The small denoiser was trained on ${n(tiny.samples)} independently generated spatial-coefficient vectors. It does not use HARP room-response generation or speech corpora such as VCTK and WSJ0.`)}</p>}
          {(kind === 'spatial' || kind === 'all') && <p>{l(`残差推定器も独自の平面波・仮想アレイを使用し、選択した重みは${n(spatial.selected_checkpoint_unique_scenes)}合成シーンで学習。音声コーパスは使用していません。`,
            `The residual estimator also uses independently generated plane waves and virtual arrays. Its selected weights were trained on ${n(spatial.selected_checkpoint_unique_scenes)} synthetic scenes, without a speech corpus.`)}</p>}
        </article>
      </div>
      <p className="mp-data-citation">{l('論文から参照したのは手法・式です。データの流用や公式重みの利用を意味しません。合成係数ベクトルの数と、論文の音声シーンの数も同じ単位ではありません。',
        'The paper is cited for its method and equations. This does not mean its datasets or official weights were reused. Synthetic coefficient-vector counts and the paper’s speech-scene counts are different units.')}</p>
    </div>
    <div className="mp-models">{descriptions.map(description => <article className="mp-model" key={description.kind}>
      <div className="mp-title"><span>{description.card.id}</span><h4>{description.title}</h4><p>{description.subtitle}</p></div>
      <dl className="mp-numbers">
        <div><dt>{l('学習済みパラメータ', 'Trained parameters')}</dt><dd>{n(description.card.parameter_count)}</dd></div>
        <div><dt>{description.unit}</dt><dd>{description.count}</dd></div>
        <div><dt>{l('学習ステップ', 'Training steps')}</dt><dd>{description.steps}</dd></div>
      </dl>
      <ol className="mp-process">{description.pipeline.map((text, index) => <li key={index}><span>{String(index + 1).padStart(2, '0')}</span><p>{text}</p></li>)}</ol>
      <details className="mp-details">
        <summary>{l('生成条件・学習方法・重みの識別を開く', 'Inspect generation, training and weight identity')}</summary>
        <dl>{description.rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        <div className="mp-hash"><span>{l('同梱重みのSHA-256', 'Bundled weights SHA-256')}</span><code>{description.card.weights_sha256}</code></div>
      </details>
      <p className="mp-limits">{description.limitation}</p>
      <div className="mp-links">
        <a href={`${SOURCE}/scripts/${description.script}`} target="_blank" rel="noreferrer">{l('生成・学習コード', 'Generation and training code')}<ExternalLink size={12}/></a>
        <a href={asset(`/models/${description.card.id}.json`)} target="_blank" rel="noreferrer">{l('モデルカード・学習ログ', 'Model card and training log')}<ExternalLink size={12}/></a>
        {description.kind === 'diffusion' && <a href={asset('/models/tiny-denoiser-evaluation.json?v=0.5.3')} target="_blank" rel="noreferrer">{l('別seedでのノイズ除去検証・全記録', 'Denoising evaluation with new seeds · full record')}<ExternalLink size={12}/></a>}
      </div>
    </article>)}</div>
    <p className="mp-conclusion">{l('どちらも独自の試作モデルです。モデルの大きさや合成データでの数値だけで、論文と同等・論文以上の精度を示したとは扱いません。',
      'Both are independent prototypes. Model size and synthetic scores do not demonstrate accuracy equal to or better than the paper.')}</p>
    <a className="mp-document" href={asset('/info/MODEL_TRAINING.md')} target="_blank" rel="noreferrer">{l('データの出典と学習記録の詳細 · JP / EN', 'Data sources and training record · JP / EN')}<ExternalLink size={12}/></a>
  </section>;
}
