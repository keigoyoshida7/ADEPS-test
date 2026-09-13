'use client';
import { useState, type ReactNode } from 'react';
import { ArrowRight, Copy, Download, ExternalLink } from 'lucide-react';
import { useLanguage } from './i18n';
import { asset } from './assets';

const PAPER = 'https://arxiv.org/html/2608.24558v3';
const CODE = 'https://github.com/keigoyoshida7/ADEPS-test/blob/main/';
const citation = 'Amit Milstein, Nir Shlezinger, and Boaz Rafaely. “Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling.” arXiv:2608.24558v3, 8 September 2026. https://doi.org/10.48550/arXiv.2608.24558';
function Section({ id, number, title, children }: { id: string; number: string; title: string; children: ReactNode }) {
  return <section id={id} className="panel info-section"><div className="info-section-title"><span>{number}</span><h2>{title}</h2></div>{children}</section>;
}
function Source({ href, children }: { href: string; children: ReactNode }) {
  return <a className="citation" href={href} target="_blank" rel="noreferrer">{children} <ExternalLink size={11}/></a>;
}

export default function ResearchInfo({ onNavigate }: { onNavigate: (page: string) => void }) {
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  async function copyCitation() {
    try { await navigator.clipboard.writeText(citation); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  const mapping = [
    { title: 'Linear · Eq. (5)', formula: 'Ẽ = Vᴴ (VVᴴ + γ²I)⁻¹',
      text: l('既知のVから正則化した線形エンコーダーを作ります。学習を使わず、DPSと同じ入力から比較の基準を計算します。', 'Build a regularized linear encoder from known V. This untrained baseline uses the same observation as DPS.'), ref: '#S2.SS3' },
    { title: 'H · §3.1', formula: 'H(z) = 3 |z|⁰·⁶⁷ exp(i∠z)',
      text: l('位相を保った振幅圧縮を使います。ゼロ近傍の連続な線形延長と、共通の正規化スケールは本実装で明示した数値処理です。', 'Use phase-preserving magnitude compression. The continuous linear extension near zero and common normalization scale are explicit numerical choices in this implementation.'), ref: '#S3.SS1' },
    { title: 'Observation consistency · Eq. (10)', formula: 'A(z) = H(Ẽ V H⁻¹(z))',
      text: l('推定を非圧縮係数へ戻し、仮想観測と線形再符号化を経て入力との誤差を求めます。学習時の固定スケールを入れたforwardと、その勾配の両方を実装しています。', 'Expand the estimate, simulate acquisition and linear re-encoding, then compare with the observation. Both the forward map and its gradient include the fixed training-domain scale.'), ref: '#S3.SS1' },
    { title: 'EDM · Eq. (12)', formula: 'L = mean[(Dθ(x + σε, σ) − x)²] × (σ² + 1) / σ²',
      text: l('σdata=1のEDM前処理と重み付きMSEを使い、36複素成分の時間・周波数構造を学習します。学習損失と、未知データでの評価値は別に記録します。', 'Use EDM preconditioning and weighted MSE with sigma_data=1 to learn time–frequency structure across 36 complex coefficients. Training loss and held-out metrics are recorded separately.'), ref: '#S3.SS3' },
    { title: 'Noise schedule · Eq. (11)', formula: 'σᵢ = [σmax¹⁄ρ + i/(M−1) (σmin¹⁄ρ − σmax¹⁄ρ)]ρ',
      text: l('ρ=10、学習範囲0.002〜80、復元の開始20・最小0.002を採用。ローカル復元の既定は150更新です。最後にσ=0を追加する終端処理と、学習時の連続一様な補間パラメータは独立実装の選択です。', 'Use rho=10, training sigma 0.002–80 and reconstruction sigma 20–0.002. Local reconstruction defaults to 150 updates. Appending terminal sigma=0 and drawing a continuous uniform interpolation parameter during training are independent implementation choices.'), ref: '#S3.SS2' },
    { title: 'Guidance · §3.1 / Algorithm 1', formula: 'g = ∇x ‖y − A(Dθ(x,σ))‖² ; guidance = −η′g / (σ‖g‖₂)',
      text: l('ネットワークを通る勾配も含め、観測へ整合する方向を計算します。η′はその更新の強さです。途中のdenoiser推定と、終端更新後の最終sampleを区別して保存します。', 'Compute observation guidance including the gradient through the network. Eta-prime controls its strength. Saved intermediate denoiser estimates are distinguished from the sample after the terminal update.'), ref: '#S3.SS1' },
  ];
  return <article className="research-info">
    <div className="info-intro"><span className="eyebrow">SOURCES / IMPLEMENTATION / LIMITS</span><h2>{l('論文から、何を実装したか。', 'From the paper to this implementation.')}</h2>
      <p>{l('理想Ambisonicsのpriorを学習し、取得応答Vを復元時に使う設計を参照しています。30.78Mの音声モデルを独立実装し、学習・復元・評価の出所を確認できる形にしました。著者の公式重みや公表性能の再現を示すものではありません。',
        'This project follows the separation of an ideal Ambisonics prior from acquisition response V at reconstruction. Its independent 30.78M speech model has traceable training, reconstruction and evaluation records. It does not reproduce the authors’ official weights or reported performance.')}</p></div>
    <div className="info-status-grid">
      <div><span>{l('モデル', 'MODEL')}</span><h3>30,781,344</h3><p>{l('独立したNCSN++M由来の時間・周波数モデル。5次、36複素成分、72実数チャンネル。', 'Independent NCSN++M-derived time–frequency model: order 5, 36 complex coefficients, 72 real channels.')}</p><Source href={`${CODE}backend/paper_prior.py`}>{l('モデルの実装', 'Network implementation')}</Source></div>
      <div><span>{l('学習の実績', 'ACTUAL TRAINING')}</span><h3>{l('保存記録で確認', 'Read the record')}</h3><p>{l('更新回数、実際に使ったシーン数、評価、重みSHAを記録。「ADEPSの流れ」の②で表示します。', 'Optimizer updates, scenes actually seen, evaluation and checkpoint SHA are recorded. View them in workflow stage 2.')}</p><button type="button" onClick={() => onNavigate('workflow')}>{l('手順と学習記録へ', 'Workflow & training record')}<ArrowRight size={14}/></button></div>
      <div><span>{l('復元結果', 'RECONSTRUCTION')}</span><h3>{l('同じ入力で比較', 'Compare the same input')}</h3><p>{l('Webは計算済み例の表示、再計算はローカルTorchです。結果のモデルIDと重みSHAで出所を確かめます。', 'The web displays computed examples; local Torch performs recomputation. Model ID and checkpoint SHA identify each result.')}</p><button type="button" onClick={() => onNavigate('diffusion')}>{l('復元・比較へ', 'Reconstruct & compare')}<ArrowRight size={14}/></button></div>
    </div>
    <section className="panel info-section">
      <div className="info-section-title"><span>+ α</span><h2>{l('関連研究から加えた復元処理', 'Reconstruction additions informed by related research')}</h2></div>
      <p>{l('別タブでは、同じ学習済みモデルに方向共分散・波形としてのSTFT整合・観測補正を組み合わせた独自方式を比較します。学習済み補正をOFFにした比較も掲載し、何が改善に寄与したかを分けて確認します。重みの再学習や、原著ADEPSを上回ったという主張は含みません。', 'The separate tab compares an independent combination of the same trained model, directional covariance, STFT waveform consistency and observation correction. A learned-refinement OFF control separates the contribution of each part. This does not retrain the checkpoint or establish superiority over the original ADEPS paper.')}</p>
      <button type="button" onClick={() => onNavigate('plus')}>{l('ADEPS + αの比較へ', 'Open ADEPS + α comparison')}<ArrowRight size={14}/></button>
      <Source href={asset('info/PLUS_METHODS.md')}>{l('実装方法と引用元', 'Methods and citations')}</Source>
      <Source href={asset('info/PLUS_PROTOCOL.md')}>{l('評価条件と判定方法', 'Evaluation protocol')}</Source>
      <Source href={asset('info/PLUS_USAGE.md')}>{l('自分の入力で再計算', 'Recompute with your input')}</Source>
    </section>
    <nav className="info-toc" aria-label={l('このページの項目', 'On this page')}>
      {[['paper-source', l('原著と引用', 'Paper & citation')], ['paper-equations', l('数式との対応', 'Equation mapping')], ['paper-training', l('データと学習', 'Data & training')], ['paper-limits', l('評価と残る違い', 'Evaluation & differences')]].map(([id, label], i) => <a key={id} href={`#${id}`}><span>0{i + 1}</span>{label}</a>)}
    </nav>
    <Section id="paper-source" number="01" title={l('原著と引用', 'Paper and citation')}>
      <p className="bibliographic-title">Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling</p>
      <p>Amit Milstein · Nir Shlezinger · Boaz Rafaely<br/>arXiv:2608.24558v3 · {l('2026年9月8日', '8 September 2026')}</p>
      <Source href={PAPER}>ADEPS v3</Source><Source href="https://github.com/Amitmils/ADEUPS">{l('著者の公開リポジトリ', 'Authors’ repository')}</Source>
      <p>{l('2026年9月13日の確認時点で、著者のリポジトリはREADMEのみで、公式学習コード・重みは取得できませんでした。このページのモデルは当プロジェクトの独立実装です。',
        'At verification on 13 September 2026, the authors’ repository contained only a README; official training code and weights were unavailable. The model here is this project’s independent implementation.')}</p>
      <div className="info-copy"><p>{citation}</p><button type="button" onClick={copyCitation}><Copy size={14}/>{copied ? l('コピー済み', 'Copied') : l('引用をコピー', 'Copy citation')}</button>
        {copyError && <p>{l('コピーできませんでした。上の引用文を選択してコピーしてください。', 'Copy failed. Select and copy the citation above.')}</p>}</div>
    </Section>
    <Section id="paper-equations" number="02" title={l('数式をどう応用したか', 'How the equations are applied')}>
      <p>{l('以下は本実装の計算を説明する対応表です。Hは振幅圧縮、Ẽは線形エンコーダー、Vは取得応答、Dθは学習済みdenoiserです。', 'This mapping describes the implemented calculations. H is magnitude compression, Ẽ the linear encoder, V acquisition response and Dθ the denoiser.')}</p>
      {mapping.map(item => <details key={item.title} className="info-equation-detail"><summary>{item.title}</summary><div className="formula">{item.formula}</div><p>{item.text}<Source href={`${PAPER}${item.ref}`}>ADEPS</Source></p></details>)}
      <p>{l('EDM前処理、チェックポイントの保存復元、複素行列の随伴、正規化スケールを含むDPSの勾配を数値テストしています。これらは実装の整合性の検査で、学習の収束や音響性能の保証ではありません。',
        'Numerical tests cover EDM preconditioning, checkpoint round trips, complex adjoints and DPS gradients including normalization scales. They check implementation consistency, not convergence or acoustic performance.')}</p>
      <Source href="https://arxiv.org/abs/2206.00364">EDM · Karras et al. (2022)</Source><Source href={`${CODE}backend/paper_inference.py`}>{l('復元の実装', 'Reconstruction implementation')}</Source><Source href={`${CODE}training_tests/test_paper_inference.py`}>{l('勾配の検証', 'Gradient tests')}</Source>
    </Section>
    <Section id="paper-training" number="03" title={l('データ・モデル・学習の出所', 'Data, model and training provenance')}>
      <h3>{l('理想係数を作る', 'Generate ideal coefficients')}</h3>
      <p>{l('VCTK 0.92の部分集合を音源に、HARP由来の室内応答を畳み込み、理想的な5次ACN/N3D係数を生成します。HARPの規約とAPIへの調整を明示し、元の出力と同一とは扱いません。マイク配置・V・機器の雑音はpriorの学習入力に含めません。',
        'A VCTK 0.92 subset is convolved with HARP-derived room responses to produce ideal order-5 ACN/N3D coefficients. Convention and API adaptations are explicit; outputs are not described as unchanged upstream HARP. Array geometry, V and device noise are not prior training inputs.')}</p>
      <Source href="https://doi.org/10.7488/ds/2645">VCTK 0.92 · CC BY 4.0</Source><Source href="https://github.com/whojavumusic/HARP">HARP</Source><Source href={`${CODE}scripts/paper_data.py`}>{l('生成処理と出所記録', 'Data generation and provenance')}</Source>
      <h3>{l('時間・周波数を扱うモデル', 'A model of time–frequency structure')}</h3>
      <p>{l('引用[28]の著者公開NCSN++Mを構成の参照とし、4段階のU-Net、128を基底幅とする(1,2,2,2)の特徴幅、FIRリサンプリング、中央のattention、adaLNを独立実装しました。実数で数えた学習パラメータは30,781,344です。数合わせだけの未使用パラメータは含めていません。',
        'The authors’ NCSN++M code cited as [28] guides an independent four-level U-Net with base width 128, multipliers (1,2,2,2), FIR resampling, middle attention and adaLN. It contains 30,781,344 trainable parameters, with no unused parameters added to match a count.')}</p>
      <Source href="https://github.com/sp-uhh/sgmse/blob/c1399bfb700e96ad49257def4e4edf8fe61e4acc/sgmse/backbones/ncsnpp.py">NCSN++M · {l('著者実装', 'author implementation')}</Source><Source href="https://arxiv.org/abs/2211.02397">Lemercier et al. (2023)</Source>
      <h3>{l('学習条件と実際の実行量', 'Training settings and actual work completed')}</h3>
      <p>{l('16 kHz・FFT512・hop128・32フレームを基準とし、理想係数の共通RMS、振幅圧縮、学習データだけから求める固定スケールを適用します。AdamW、勾配クリップ、マイクロバッチ1などの選択は保存記録に残します。学習候補が20,000シーンでも、その全部を処理したという意味ではありません。',
        'The reference configuration uses 16 kHz, FFT512, hop128 and 32 frames. A common coefficient RMS, magnitude compression and a fixed training-derived scale are applied. Choices including AdamW, gradient clipping and microbatch one are recorded. A 20,000-scene pool does not mean all those scenes were processed.')}</p>
      <p>{l('学習曲線は保存済み更新点、評価は未使用話者のデータです。trainingは中間記録、evaluatedは記録の重みを評価済みという状態であり、プロセスの稼働状況や原著精度への到達は表しません。',
        'Learning curves show saved updates and evaluation uses held-out speakers. “training” means an intermediate record; “evaluated” means the recorded checkpoint was evaluated. Neither status proves a running process or paper-level accuracy.')}</p>
      <a href={asset('/models/paper-prior-training.json')} target="_blank" rel="noreferrer"><Download size={13}/> {l('実際の学習・評価記録 JSON', 'Actual training and evaluation JSON')}</a><Source href={`${CODE}scripts/train_paper_prior.py`}>{l('学習コード', 'Training code')}</Source>
    </Section>
    <Section id="paper-limits" number="04" title={l('比較できる範囲と残る違い', 'What can be compared and what differs')}>
      <div className="table-scroll"><table><thead><tr><th>{l('項目', 'Aspect')}</th><th>{l('このUIで確認すること', 'What this UI verifies')}</th><th>{l('原著との違い・限界', 'Difference or limit')}</th></tr></thead><tbody>
        <tr><th>{l('モデル', 'Model')}</th><td>{l('36複素成分の独立した音声priorと、実際の重み。', 'Independent 36-complex-channel speech prior and actual checkpoint.')}</td><td>{l('adaLN挿入位置、細部の構成・学習条件などは未公開部分を独自に選択。規模の近さは同精度の証明ではありません。', 'Undisclosed adaLN placement, architectural details and training settings are independently chosen. Similar size does not establish equal accuracy.')}</td></tr>
        <tr><th>{l('データ分割', 'Data split')}</th><td>{l('話者とシーンを分けたVCTK部分集合。実使用数を記録。', 'VCTK subset with separate speakers and scenes; actual usage counts recorded.')}</td><td>{l('原著のWSJ0評価を再現していません。候補シーン数と学習済みシーン数は区別します。', 'The original WSJ0 evaluation is not reproduced. Available and consumed scene counts are distinct.')}</td></tr>
        <tr><th>{l('復元の比較', 'Reconstruction comparison')}</th><td>{l('同じ観測・V・正解でLinearと独立DPSを比較。', 'Compare Linear and independent DPS using the same observations, V and reference.')}</td><td>{l('現在の仮想N5条件を、原著のN_eff=15・各実機アレイ・全評価条件と同一には扱いません。', 'Current virtual N5 conditions do not reproduce the paper’s N_eff=15, real-device arrays or complete evaluation suite.')}</td></tr>
        <tr><th>{l('周波数指標', 'Frequency metrics')}</th><td>{l('FOAの振幅dB誤差と、時間集約後に成分平均するMSC。', 'FOA magnitude error in dB and MSC averaged over channels after temporal aggregation.')}</td><td>{l('ゼロ対策の共通floorと欠損処理は独自に明示。単体denoiserのNMSEは別の評価です。', 'Common numerical floors and undefined values are explicitly handled. Denoiser-only NMSE is a separate evaluation.')}</td></tr>
        <tr><th>{l('3D・音声', '3D and audio')}</th><td>{l('FOA共分散の方向表示、仮想カーディオイドの試聴。', 'Directional FOA covariance display and virtual-cardioid preview.')}</td><td>{l('部屋の物理音圧、音源位置地図、HRTF再生、実空間での性能ではありません。', 'Not room pressure, source localization, HRTF playback or measured real-space performance.')}</td></tr>
      </tbody></table></div>
      <p>{l('原著は周波数指標の定義をGen-Aへ参照しています。本UIの振幅誤差・MSCはその定義を参照し、数値的なゼロ対策と有効成分数を結果に記録します。データや条件が異なる数値を並べて「論文を上回った」とは判断しません。',
        'The paper references Gen-A for frequency metric definitions. This UI follows its magnitude-error and MSC definitions, recording numerical zero handling and valid channel counts. Scores from different data or conditions are not treated as evidence of outperforming the paper.')}</p>
      <Source href="https://arxiv.org/html/2501.08047v1#S3.SS4">Gen-A · Eqs. (5)–(6)</Source><Source href={asset('/info/PAPER_PRIOR.md')}>{l('実装と評価の詳細記録', 'Detailed implementation and evaluation record')}</Source>
      <p><button type="button" onClick={() => onNavigate('glossary')}>{l('専門用語を確認する', 'Look up the terms')}<ArrowRight size={14}/></button></p>
    </Section>
  </article>;
}
