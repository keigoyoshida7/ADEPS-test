import { useState } from 'react';
import { ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';
import PaperTraining from './PaperTraining';
import ADEPSProcessDiagram from './ADEPSProcessDiagram';
import './ADEPSWorkflow.css';

type Props = { language: 'jp' | 'en'; active?: boolean; onNavigate: (page: string) => void };

export default function ADEPSWorkflow({ language, active = true, onNavigate }: Props) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [selected, setSelected] = useState(0);
  const steps = [
    { title: l('理想データ', 'Ideal data'), heading: l('正解になる音場を用意する', 'Prepare the target sound field'), phase: l('学習の準備', 'Prepare training'),
      input: l('VCTKの音声 ＋ HARP由来の室内応答', 'VCTK speech + HARP-derived room responses'),
      output: l('理想的な5次Ambisonics · 36複素成分 a', 'Ideal order-5 Ambisonics · 36 complex coefficients a'),
      explanation: l('音声に方向と残響を与え、マイク観測へ変換する前の理想係数を作ります。音場の表現を学ぶためのデータで、マイク配置や機種の応答は入力しません。',
        'Speech is rendered with direction and reverberation to create ideal coefficients before microphone observation. These data describe sound fields; array positions and microphone responses are not training inputs.'),
      note: l('取得した音声、話者の分割、実際に学習へ使ったシーン数は、次の工程の記録で確認します。', 'Downloaded speech, speaker splits and scenes actually used are recorded in the next stage.') },
    { title: l('モデル学習', 'Train the prior'), heading: l('音場の特徴をモデルに学習させる', 'Learn a prior over sound fields'), phase: l('ローカルで学習', 'Local training'),
      input: l('理想係数を圧縮・正規化したデータ ＋ 学習用の雑音', 'Compressed, normalized ideal coefficients + training noise'),
      output: l('ノイズから理想係数を推定するモデル Dθ', 'A denoiser Dθ that estimates ideal coefficients'),
      explanation: l('30.78Mパラメータの独立したNCSN++M由来モデルで、時間・周波数・36成分の関係を学びます。学習はローカル環境で行い、このページには保存された更新回数・評価を表示します。',
        'The independent 30.78M-parameter NCSN++M-derived model learns relationships across time, frequency and 36 coefficients. Training runs locally; this page displays recorded updates and evaluation.'),
      note: l('モデルの大きさは精度の保証ではありません。学習中・評価済みの状態と、未知のデータでの結果を下の実記録で確認します。', 'Model size does not guarantee accuracy. Check the actual record below for training status and held-out results.') },
    { title: l('仮想観測', 'Virtual observation'), heading: l('マイクには何が届くかを計算する', 'Simulate what an array observes'), phase: l('学習と別のテスト', 'Separate reconstruction test'),
      input: l('テスト用の正解係数 a ＋ 仮想アレイの応答 V ＋ 雑音 ν', 'Test reference a + virtual-array response V + noise ν'),
      output: l('各マイクで観測される信号 p = Va + ν', 'Observed microphone signals p = Va + ν'),
      explanation: l('マイクの数・半径・配置から、理想係数が観測信号へ変わる過程を計算します。Vはこの取得過程を表すもので、②の学習済みモデルとは別です。正解は後の評価用に保持します。',
        'Array count, radius and positions determine how ideal coefficients become observations. V describes this acquisition process and is separate from the trained prior in stage 2. The reference is retained for evaluation.'),
      note: l('観測は仮想アレイのモデルから生成します。各結果に保存された音声・アレイ条件を確認し、同じ観測で比較します。', 'Observations are generated using a virtual-array model. Check the speech and array conditions recorded with each result, and compare methods on the same observation.') },
    { title: 'Linear', heading: l('まず、線形法で推定する', 'Start with a linear estimate'), phase: l('比較の基準', 'Comparison baseline'),
      input: l('同じ観測信号 p ＋ 既知の応答 V', 'The same observations p + known response V'),
      output: l('正則化した逆計算による係数 âLinear', 'Coefficients âLinear from a regularized inverse'),
      explanation: l('Vから線形エンコーダーを作り、観測信号をAmbisonicsへ戻します。この工程に学習はありません。雑音や解像度の制約で残る誤差を、拡散復元との比較の基準にします。',
        'A linear encoder derived from V maps observations back to Ambisonics. This stage needs no training. Its remaining noise and resolution errors form the baseline for diffusion reconstruction.'),
      note: l('Linearと拡散復元には同じ観測信号を渡します。正解係数は復元の入力に使いません。', 'Linear and diffusion receive the same observations. Reference coefficients are not reconstruction inputs.') },
    { title: l('拡散復元', 'DPS reconstruction'), heading: l('priorと観測の両方を使って復元する', 'Reconstruct using the prior and the observation'), phase: l('反復して推定', 'Iterative estimation'),
      input: l('Linear推定 ＋ 応答V ＋ prior Dθ ＋ 初期雑音', 'Linear estimate + response V + prior Dθ + initial noise'),
      output: l('各段階の推定と、最後のAmbisonics係数', 'Intermediate estimates and final Ambisonics coefficients'),
      explanation: l('ノイズ強度σを下げながら、モデルによる推定と観測への整合を繰り返します。保存した途中の推定を選ぶと、形・音・誤差の変化を追えます。σは音声の再生時刻ではありません。',
        'As noise scale sigma decreases, the sampler combines denoising with consistency to the observation. Saved estimates let you follow changes in shape, audio and error. Sigma is not an audio playback time.'),
      note: l('30.78Mモデルの再計算はローカルTorch環境で行います。Webでは実際に計算した例を、重みの識別情報とともに読み込みます。', 'The 30.78M model is recomputed in local Torch. The web page loads actual computed examples with checkpoint identity.') },
    { title: l('比較・試聴', 'Compare & listen'), heading: l('同じ正解に対して、差を確かめる', 'Compare against the same reference'), phase: l('結果の検証', 'Evaluate the result'),
      input: l('正解・Linear・拡散の各段階の係数', 'Reference, Linear and saved diffusion coefficients'),
      output: l('周波数別の誤差・Coherence・方向表示・試聴', 'Frequency errors, coherence, directional view and audio'),
      explanation: l('Magnitude Spectrum ErrorとCoherenceで周波数ごとの差を見て、同じ音量基準で聴き比べます。3DはFOAの方向別の強さを示します。形の変化と、推定精度の改善は分けて確かめます。',
        'Inspect frequency-dependent magnitude spectrum error and coherence, then compare audio at a shared level. The 3D view shows FOA directional strength. Evaluate accuracy separately from visible changes.'),
      note: l('「復元・比較」でモデルと結果の出所を確認し、Linearとの切り替え、途中経過の連続試聴、数値の保存を行えます。', 'In Reconstruct & compare, check the model and result source, switch against Linear, audition the saved sequence and export the numbers.') },
  ];
  const step = steps[selected];
  return <article className="adeps-workflow">
    <div className="aw-intro"><span className="eyebrow">FROM DATA TO RECONSTRUCTION</span>
      <h2>{l('何を作り、何を確かめるか。', 'What we build. What we test.')}</h2>
      <p>{l('6つの工程を順にたどります。学習は音場の特徴を覚える工程、復元はそのモデルと観測を使って係数を推定する工程です。',
        'Follow six stages. Training learns a prior over sound fields; reconstruction uses that prior and an observation to estimate coefficients.')}</p>
      <div className="aw-modes"><p><strong>{l('Webで結果を見る', 'Inspect results on the web')}</strong>{l('実際の学習記録と計算済み例を読み込み、変化を比較・試聴。', 'Load actual training records and computed examples to compare and audition changes.')}</p>
        <p><strong>{l('ローカルで計算する', 'Compute locally')}</strong>{l('30.78Mの音声priorと観測の応答Vを使って復元。', 'Reconstruct using the 30.78M speech prior and observation response V.')}</p></div>
    </div>
    <ol className="aw-steps" aria-label={l('ADEPSの6工程', 'Six ADEPS stages')}>{steps.map((item, index) => <li key={index}>
      <button type="button" className={selected === index ? 'active' : ''} aria-current={selected === index ? 'step' : undefined}
        onClick={() => setSelected(index)} aria-controls="adeps-workflow-stage"><span>{String(index + 1).padStart(2, '0')}</span>{item.title}</button>
    </li>)}</ol>
    <section id="adeps-workflow-stage" className="aw-stage" aria-labelledby="aw-stage-title">
      <div className="aw-stage-top"><span className="eyebrow">{String(selected + 1).padStart(2, '0')} / 06 · {step.phase}</span>
        <div className="aw-paging"><button type="button" disabled={selected === 0} onClick={() => setSelected(value => value - 1)}><ArrowLeft size={13}/>{l('前へ', 'Previous')}</button>
          <button type="button" disabled={selected === 5} onClick={() => setSelected(value => value + 1)}>{l('次へ', 'Next')}<ArrowRight size={13}/></button></div></div>
      <h3 id="aw-stage-title">{step.heading}</h3>
      <ADEPSProcessDiagram language={language} kind={selected < 2 ? 'train' : 'reconstruct'} focus={selected < 2 ? undefined : (['observe', 'linear', 'dps', 'compare'] as const)[selected - 2]}/>
      <div className="aw-io"><div><span>{l('入力', 'Input')}</span><p>{step.input}</p></div><ArrowDown size={18}/><div><span>{l('出力', 'Output')}</span><p>{step.output}</p></div></div>
      <p className="aw-explanation">{step.explanation}</p><p className="aw-note">{step.note}</p>
      {selected === 1 && <PaperTraining language={language} active={active} sectionId="workflow-training-record"/>}
      {selected >= 4 && <div className="aw-action"><button type="button" onClick={() => onNavigate('diffusion')}>
        {selected === 4 ? l('復元を試す', 'Open reconstruction') : l('比較と試聴を開く', 'Open comparison & audio')}<ArrowRight size={16}/></button></div>}
      {selected !== 1 && selected < 4 && <button type="button" className="aw-continue" onClick={() => setSelected(value => value + 1)}>{l('次の工程へ', 'Continue to the next stage')}<ArrowRight size={15}/></button>}
    </section>
    <div className="aw-evidence"><p>{l('原著の公式モデルや公表精度を再現したものではありません。実装した範囲と残る違いを、引用とともに記録しています。',
      'This does not reproduce the authors’ official model or reported accuracy. Implemented scope and remaining differences are documented with citations.')}</p>
      <button type="button" onClick={() => onNavigate('glossary')}>{l('用語の解説', 'Glossary')}<ArrowRight size={14}/></button></div>
  </article>;
}
