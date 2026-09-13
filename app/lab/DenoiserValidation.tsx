'use client';

import { useEffect, useId, useState } from 'react';
import { Download, ExternalLink, RotateCcw } from 'lucide-react';
import tinyCard from '../../public/models/tiny-spatial-v1.json';
import { asset } from './assets';
import { Plot } from './Plots';
import './DenoiserValidation.css';

type Score = { nrmse_db: number; real_coordinate_mse: number };
type TestCase = {
  sigma: number; within_inference_range: boolean;
  noisy: Score; shrink: Score; learned: Score;
  learned_improvement_over_noisy_db: number; learned_improvement_over_shrink_db: number;
  learned_win_fraction_vs_shrink: number;
  learned_wins_vs_shrink: number; learned_ties_vs_shrink: number; learned_losses_vs_shrink: number;
};
type Evaluation = {
  schema: 'adeps-test-tiny-denoiser-evaluation/1'; generated_at_utc: string;
  model: { id: string; parameter_count: number; weights_sha256: string; sigma_data: number; training_seed: number; training_steps: number };
  dataset: { vectors: number; complex_channels: number; real_coordinates_per_vector: number;
    generator_seed: number; noise_seed: number; training_seed: number; validation_seed: number;
    same_noise_across_sigma: boolean; generation_family: string; normalization: string; noise_definition: string };
  protocol: { sigma_values: number[]; inference_sigma_range: number[]; training_sigma_range: number[];
    shrink_definition: string; metric_definitions: Record<string, string>; db_floor: number };
  cases: TestCase[];
  summary: { sigma_count: number; learned_better_than_noisy_sigma_count: number; learned_better_than_shrink_sigma_count: number };
  provenance: { evaluation_script: string; evaluation_script_sha256: string; generator_training_script: string;
    generator_training_script_sha256: string; inference_source: string; inference_source_sha256: string };
  limits: string[];
};
type LoadState = { state: 'loading' } | { state: 'error'; reason: 'network' | 'invalid' | 'mismatch' } | { state: 'ready'; report: Evaluation };
const REPORT = '/models/tiny-denoiser-evaluation.json?v=0.5.3';
const REPO = 'https://github.com/keigoyoshida7/ADEPS-test/blob/main/';
const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
const hash = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const positiveInteger = (value: unknown) => finite(value) && Number.isInteger(value) && value > 0;
const numeric = (value: number, digits = 3) => Math.abs(value) > 0 && (Math.abs(value) < .001 || Math.abs(value) >= 100000)
  ? value.toExponential(3) : value.toFixed(digits);
const sigmaText = (value: number) => Number(value.toPrecision(4)).toString();
const deltaText = (value: number) => `${value > 0 ? '+' : ''}${numeric(value)} dB`;
const safeCodeLink = (path: string) => /^[\w./-]+$/.test(path) && !path.startsWith('/') && !path.includes('..') ? `${REPO}${path}` : null;

function validReport(input: unknown): input is Evaluation {
  if (!input || typeof input !== 'object') return false;
  const r = input as Evaluation;
  if (r.schema !== 'adeps-test-tiny-denoiser-evaluation/1' || !r.model || !r.dataset || !r.protocol || !r.provenance
    || !Array.isArray(r.cases) || r.cases.length < 2 || !Array.isArray(r.limits)
    || !positiveInteger(r.dataset.vectors) || !positiveInteger(r.model.parameter_count)
    || !finite(r.model.sigma_data) || r.model.sigma_data <= 0 || typeof r.model.id !== 'string'
    || typeof r.generated_at_utc !== 'string' || r.dataset.same_noise_across_sigma !== true
    || r.dataset.complex_channels !== 36 || r.dataset.real_coordinates_per_vector !== 72
    || !hash(r.model.weights_sha256)
    || ![r.dataset.generator_seed, r.dataset.noise_seed, r.dataset.training_seed, r.dataset.validation_seed]
      .every(value => finite(value) && Number.isInteger(value) && value >= 0)
    || ![r.provenance.evaluation_script, r.provenance.generator_training_script, r.provenance.inference_source]
      .every(value => typeof value === 'string' && value.length > 0)
    || ![r.provenance.evaluation_script_sha256, r.provenance.generator_training_script_sha256, r.provenance.inference_source_sha256].every(hash)
    || ![r.protocol.inference_sigma_range, r.protocol.training_sigma_range].every(values =>
      Array.isArray(values) && values.length === 2 && values.every(value => finite(value) && value > 0) && values[0] < values[1])) return false;
  return r.cases.every((row, i) => row && typeof row === 'object' && finite(row.sigma) && row.sigma > 0
    && typeof row.within_inference_range === 'boolean' && (i === 0 || row.sigma > r.cases[i - 1].sigma)
    && ['noisy', 'shrink', 'learned'].every(key => {
      const score = row[key as 'noisy' | 'shrink' | 'learned'];
      return score && finite(score.nrmse_db) && finite(score.real_coordinate_mse) && score.real_coordinate_mse >= 0;
    }) && finite(row.learned_improvement_over_noisy_db) && finite(row.learned_improvement_over_shrink_db)
    && finite(row.learned_win_fraction_vs_shrink) && row.learned_win_fraction_vs_shrink >= 0 && row.learned_win_fraction_vs_shrink <= 1
    && [row.learned_wins_vs_shrink, row.learned_ties_vs_shrink, row.learned_losses_vs_shrink].every(n => Number.isInteger(n) && n >= 0)
    && row.learned_wins_vs_shrink + row.learned_ties_vs_shrink + row.learned_losses_vs_shrink === r.dataset.vectors);
}

export default function DenoiserValidation({ language }: { language: 'jp' | 'en' }) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const count = (value: number) => value.toLocaleString(language === 'jp' ? 'ja-JP' : 'en-US');
  const [load, setLoad] = useState<LoadState>({ state: 'loading' });
  const [retry, setRetry] = useState(0);
  const [selectedSigma, setSelectedSigma] = useState(1);
  const sigmaId = useId();
  useEffect(() => {
    const controller = new AbortController();
    setLoad({ state: 'loading' });
    void fetch(asset(REPORT), { signal: controller.signal, cache: 'no-cache' }).then(async response => {
      if (!response.ok) throw new Error('network');
      const value: unknown = await response.json();
      if (controller.signal.aborted) return;
      if (!validReport(value)) { setLoad({ state: 'error', reason: 'invalid' }); return; }
      if (value.model.id !== tinyCard.id || value.model.weights_sha256 !== tinyCard.weights_sha256) {
        setLoad({ state: 'error', reason: 'mismatch' }); return;
      }
      setLoad({ state: 'ready', report: value });
    }).catch(() => { if (!controller.signal.aborted) setLoad({ state: 'error', reason: 'network' }); });
    return () => controller.abort();
  }, [retry]);
  const report = load.state === 'ready' ? load.report : null;
  const current = report?.cases.find(row => row.sigma === selectedSigma) ?? report?.cases.find(row => row.sigma === 1) ?? report?.cases[0];
  const improvedConditions = report?.cases.filter(row => row.learned_improvement_over_shrink_db > 1e-9).length ?? 0;
  const worseConditions = report?.cases.filter(row => row.learned_improvement_over_shrink_db < -1e-9).length ?? 0;
  const bestImprovement = report ? Math.max(...report.cases.map(row => row.learned_improvement_over_shrink_db)) : 0;
  const methods = [
    { key: 'noisy' as const, label: l('何も除去しない', 'Unchanged noisy input'), detail: l('ノイズを加えた入力を、そのまま答えにする基準。', 'Return the noisy input unchanged.') },
    { key: 'shrink' as const, label: l('単純なガウス縮小', 'Simple Gaussian shrinkage'), detail: l('信号とノイズの分散から、入力全体を一律に小さくする基準。', 'Uniformly scale the input using signal and noise variances.') },
    { key: 'learned' as const, label: l('学習済みdenoiser', 'Trained denoiser'), detail: l('同梱の学習済み重みで、ノイズ除去を1回実行。', 'One denoising call using the bundled learned weights.') },
  ];
  const verdict = (delta: number) => delta > 1e-9 ? l('改善', 'Better') : delta < -1e-9 ? l('悪化', 'Worse') : l('同等', 'Tied');
  const sourceRows = report ? [
    { label: l('検証コード', 'Evaluation code'), path: report.provenance.evaluation_script, sha: report.provenance.evaluation_script_sha256 },
    { label: l('合成データ生成・学習コード', 'Data generation and training code'), path: report.provenance.generator_training_script, sha: report.provenance.generator_training_script_sha256 },
    { label: l('推論コード', 'Inference code'), path: report.provenance.inference_source, sha: report.provenance.inference_source_sha256 },
  ] : [];

  return <section className="denoiser-validation" aria-label={l('学習済みノイズ除去器の検証', 'Trained denoiser validation')} aria-busy={load.state === 'loading'}>
    <header className="dv-heading"><span className="dv-eyebrow">DENOISER / HELD-OUT TEST</span>
      <h3>{l('学習済みノイズ除去器の検証', 'Trained denoiser validation')}</h3>
      <p className="dv-data-origin">{l('論文のデータセット：未使用 ／ 独自の合成データ', 'Paper datasets: not used / Independently generated synthetic data')}</p>
      <p>{l('新しく生成した正解のわかる合成係数にノイズを加え、学習済みdenoiserがどれだけ元に戻せるかを測定した記録です。ノイズスケジュールの表示や、会場での録音評価とは別の検証です。',
        'This record measures how well the trained denoiser recovers newly generated synthetic coefficients after adding noise. It is separate from the noise schedule and from evaluation of venue recordings.')}</p>
    </header>
    {load.state === 'loading' && <p className="dv-status" role="status">{l('保存された検証結果を読み込んでいます…', 'Loading the saved evaluation…')}</p>}
    {load.state === 'error' && <div className="dv-status dv-error" role="alert">
      <p>{load.reason === 'mismatch' ? l('検証記録の重みと現在のモデルが一致しないため、現在の精度として表示できません。', 'The recorded weights do not match the current model, so these scores cannot represent its accuracy.')
        : load.reason === 'invalid' ? l('検証記録の形式または数値を確認できません。結果のJSONを確認してください。', 'The evaluation format or numerical values are invalid. Inspect the JSON record.')
          : l('検証結果を読み込めませんでした。再読み込みできます。', 'The evaluation could not be loaded. You can try again.')}</p>
      <button type="button" onClick={() => setRetry(value => value + 1)}><RotateCcw size={13}/>{l('再読み込み', 'Retry')}</button>
    </div>}
    {report && current && <>
      <div className="dv-record-line"><span>{report.model.id} · {count(report.model.parameter_count)} {l('パラメータ', 'parameters')}</span>
        <span>{count(report.dataset.vectors)} {l('個の未学習の合成ベクトル / σごと', 'held-out synthetic vectors per σ')}</span></div>
      <p className="dv-finding">{l(`単純縮小との比較：${report.cases.length}条件中、改善は${improvedConditions}条件、悪化は${worseConditions}条件。${bestImprovement > 0 ? `最大の改善は${numeric(bestImprovement)} dBです。` : '改善した条件はありません。'} 条件数はノイズ強度の数で、精度の百分率ではありません。`,
        `Compared with simple shrinkage: better at ${improvedConditions} of ${report.cases.length} noise levels, worse at ${worseConditions}. ${bestImprovement > 0 ? `The largest improvement is ${numeric(bestImprovement)} dB.` : 'No tested condition improved.'} These are counts of noise levels, not an accuracy percentage.`)}</p>
      <div className="dv-selector"><label htmlFor={sigmaId}>{l('確認するノイズの強さ', 'Inspect noise strength')} <span>σ</span></label>
        <select id={sigmaId} value={current.sigma} onChange={event => setSelectedSigma(Number(event.target.value))}>{report.cases.map(row => <option key={row.sigma} value={row.sigma}>σ = {sigmaText(row.sigma)}{row.within_inference_range ? '' : l(' · 通常の推論範囲外', ' · outside usual inference range')}</option>)}</select>
        <p>{l('σは圧縮した複素係数の実部・虚部に加えたノイズの標準偏差です。Hz、音量dB、残ったノイズ量ではありません。', 'σ is the noise standard deviation added to the real and imaginary compressed coefficients. It is not Hz, playback dB, or remaining noise.')}</p>
      </div>
      <div className="dv-score-grid">{methods.map(method => <article className="dv-score" key={method.key} data-learned={method.key === 'learned'}>
        <h4>{method.label}</h4><p>{method.detail}</p>
        <div className="dv-score-value">{numeric(current[method.key].nrmse_db)} <span>dB</span></div>
        <span className="dv-metric-label">NRMSE · {l('小さいほど良い', 'lower is better')}</span>
        <div className="dv-mse"><span>{l('実座標あたりのMSE', 'MSE per real coordinate')}</span><strong>{numeric(current[method.key].real_coordinate_mse, 6)}</strong></div>
      </article>)}</div>
      <div className="dv-difference" data-outcome={current.learned_improvement_over_shrink_db < 0 ? 'worse' : 'better'} aria-live="polite">
        <div><span>{l('学習済みdenoiserと単純縮小の差', 'Trained denoiser vs simple shrinkage')}</span>
          <strong>{verdict(current.learned_improvement_over_shrink_db)} · {deltaText(current.learned_improvement_over_shrink_db)}</strong></div>
        <p>{l('差 = 単純縮小のNRMSE − 学習済みdenoiserのNRMSE。正なら改善、負なら悪化です。', 'Difference = shrinkage NRMSE − trained-denoiser NRMSE. Positive means better; negative means worse.')}
          {Math.abs(current.learned_improvement_over_shrink_db) < .1 && ` ${l('この条件での差は0.1 dB未満です。', 'The difference in this condition is less than 0.1 dB.')}`}</p>
        <p className="dv-vector-count">{l(`σ=${sigmaText(current.sigma)}の${count(report.dataset.vectors)}ベクトル中、単純縮小より誤差が小さかったのは${count(current.learned_wins_vs_shrink)}、大きかったのは${count(current.learned_losses_vs_shrink)}、同等は${count(current.learned_ties_vs_shrink)}。`,
          `At σ=${sigmaText(current.sigma)}, ${count(current.learned_wins_vs_shrink)} of ${count(report.dataset.vectors)} vectors had lower error than shrinkage, ${count(current.learned_losses_vs_shrink)} had higher error, and ${count(current.learned_ties_vs_shrink)} tied.`)}</p>
      </div>
      <div className="dv-chart"><Plot x={report.cases.map(row => row.sigma)} log xLabel={l('ノイズ標準偏差 σ（対数）', 'Noise standard deviation σ (log)')} xFormatter={sigmaText}
        label={l('ノイズ強度ごとの復元誤差 · 下ほど良い', 'Reconstruction error at each noise level · lower is better')} unit="NRMSE dB"
        series={[{ name: methods[0].label, values: report.cases.map(row => row.noisy.nrmse_db), color: '#888888', dash: '7 5' },
          { name: methods[1].label, values: report.cases.map(row => row.shrink.nrmse_db), color: '#c0c0c0', dash: '2 5' },
          { name: methods[2].label, values: report.cases.map(row => row.learned.nrmse_db), color: '#f2f2f2' }]}/>
        <p>{l('同じ正解係数と同じ標準正規ノイズを使い、σだけを変えて比較しています。線で結んだ間の値は未測定です。80は学習ノイズ範囲内ですが、通常の拡散推論（σ≤20）の範囲外です。',
          'The same clean coefficients and standard-normal noise are reused while varying σ. Values between connected points were not measured. σ=80 is within the training noise range but outside normal diffusion inference (σ≤20).')}</p></div>
      <p className="dv-limits">{l('この数値は、独立に生成した合成係数への1回のノイズ除去性能です。実際の声・残響・マイクアレイでの復元精度や、反復処理の最終精度を保証しません。ADEPS公式モデルの結果ではありません。',
        'These scores describe a single denoising call on independently generated synthetic coefficients. They do not establish accuracy on real speech, reverberation, microphone arrays, or the final iterative reconstruction. They are not results from the official ADEPS model.')}</p>
      <details className="dv-details"><summary>{l('すべてのノイズ条件の精度を見る', 'Inspect accuracy at every noise level')}</summary><div className="dv-table-wrap"><table>
        <caption>{l('NRMSEは小さいほど良い。差は単純縮小−学習済みで、正なら改善。', 'Lower NRMSE is better. Difference is shrinkage minus learned; positive means improvement.')}</caption>
        <thead><tr><th scope="col">σ</th><th scope="col">{l('未処理', 'Noisy')}<br/>NRMSE dB</th><th scope="col">{l('単純縮小', 'Shrinkage')}<br/>NRMSE dB</th><th scope="col">{l('学習済み', 'Learned')}<br/>NRMSE dB</th><th scope="col">{l('縮小との差', 'Vs shrinkage')}</th><th scope="col">{l('学習済みMSE', 'Learned MSE')}</th></tr></thead>
        <tbody>{report.cases.map(row => <tr key={row.sigma} data-selected={row.sigma === current.sigma}><th scope="row"><button type="button" onClick={() => setSelectedSigma(row.sigma)} aria-label={l(`σ=${sigmaText(row.sigma)}を確認`, `Inspect σ=${sigmaText(row.sigma)}`)}>{sigmaText(row.sigma)}</button>{!row.within_inference_range && <small>{l('推論範囲外', 'Outside inference')}</small>}</th>
          <td>{numeric(row.noisy.nrmse_db)}</td><td>{numeric(row.shrink.nrmse_db)}</td><td>{numeric(row.learned.nrmse_db)}</td><td>{deltaText(row.learned_improvement_over_shrink_db)}<small>{verdict(row.learned_improvement_over_shrink_db)}</small></td><td>{numeric(row.learned.real_coordinate_mse, 6)}</td></tr>)}</tbody>
      </table></div></details>
      <details className="dv-details"><summary>{l('評価方法・未学習データ・モデルの識別', 'Protocol, held-out data and model identity')}</summary>
        <dl className="dv-protocol"><div><dt>{l('評価の単位', 'Evaluation unit')}</dt><dd>{l(`${count(report.dataset.vectors)}個の独立した合成ベクトル。それぞれ5次・36複素係数＝72実座標。音声ファイルや会場の数ではありません。`, `${count(report.dataset.vectors)} independently generated synthetic vectors, each with 36 fifth-order complex coefficients = 72 real coordinates. These are not counts of audio files or venues.`)}</dd></div>
          <div><dt>{l('検証用seed', 'Held-out seeds')}</dt><dd>{l('係数の生成', 'Coefficient generation')} {report.dataset.generator_seed} / {l('ノイズ', 'Noise')} {report.dataset.noise_seed}<br/>{l('元の学習', 'Original training')} {report.dataset.training_seed} / {l('元の検証', 'Original validation')} {report.dataset.validation_seed}<br/>{l('学習と同じ生成規則から、新しいseedで作ったデータです。未知の実環境を録音したデータではありません。', 'New seeds generate data from the same procedural family as training. These are not recordings from unseen real environments.')}</dd></div>
          <div><dt>{l('公平な比較', 'Paired comparison')}</dt><dd>{l('3つの方法には同じノイズ付き係数を入力。正解は採点だけに使い、モデルの入力に渡しません。この結果を使った再学習は行っていません。', 'All three methods receive the same noisy coefficients. Clean targets are used only for scoring, never as model inputs. No retraining was performed using these results.')}</dd></div>
          <div><dt>{l('単純縮小の式', 'Shrinkage formula')}</dt><dd><code>estimate = [σdata² / (σdata² + σ²)] × noisy</code><br/>σdata = {numeric(report.model.sigma_data, 6)} · {l('同梱モデルの固定値', 'fixed value from the bundled model')}</dd></div>
          <div><dt>NRMSE</dt><dd><code>20 log₁₀(‖estimate − clean‖₂ / ‖clean‖₂)</code><br/>{l('圧縮係数の複素誤差。全ベクトルと全36係数をまとめて計算します。', 'Complex error in compressed coefficients, aggregated over all vectors and all 36 coefficients.')}</dd></div>
          <div><dt>{l('実座標MSE', 'Real-coordinate MSE')}</dt><dd><code>Σ(real_error² + imag_error²) / (72 × N)</code><br/>{l('実部・虚部を別々に数えた、1実座標あたりの平均二乗誤差。', 'Mean squared error per real coordinate, counting real and imaginary parts separately.')}</dd></div>
          <div><dt>{l('適用範囲', 'Scope')}</dt><dd>{l('学習時の圧縮係数の領域で検証しています。別途行う拡散推論は観測入力から正規化するため、その後の分布がこのテストと一致するかは未検証です。各σでは同じ係数とノイズを再利用し、条件間の結果は独立した試行ではありません。', 'This evaluates the compressed coefficient domain used in training. The separate diffusion pipeline normalizes from its observed input; a matching distribution after that normalization has not been established. The same coefficients and noise are reused across σ, so noise-level results are not independent trials.')}</dd></div>
          <div><dt>{l('報告の生成日時（UTC）', 'Report generated (UTC)')}</dt><dd>{report.generated_at_utc}</dd></div>
        </dl>
        <div className="dv-hash"><span>{l('検証した重みのSHA-256 · 同梱モデルと一致', 'Evaluated weights SHA-256 · matches the bundled model')}</span><code>{report.model.weights_sha256}</code></div>
        <div className="dv-code-records">{sourceRows.map(row => <div key={row.path}><span>{row.label}</span>{safeCodeLink(row.path) ? <a href={safeCodeLink(row.path)!} target="_blank" rel="noreferrer">{row.path}<ExternalLink size={12}/></a> : <span>{row.path}</span>}<code>{row.sha}</code></div>)}</div>
      </details>
    </>}
    <div className="dv-links"><a href={asset(REPORT)} download="tiny-denoiser-evaluation.json"><Download size={13}/>{l('検証記録JSONを保存', 'Download evaluation JSON')}</a>
      <a href={asset('/models/tiny-spatial-v1.json')} target="_blank" rel="noreferrer">{l('モデルカード', 'Model card')}<ExternalLink size={12}/></a></div>
  </section>;
}
