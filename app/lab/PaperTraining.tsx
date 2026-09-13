import { useEffect, useState } from 'react';
import { ExternalLink, LoaderCircle, Play, RefreshCw } from 'lucide-react';
import { asset } from './assets';
import { Plot } from './Plots';
import './PaperTraining.css';

type EvaluationRow = { sigma: number; noisy_nmse_db: number; gaussian_nmse_db: number; trained_nmse_db: number; improvement_over_noisy_db: number; improvement_over_gaussian_db: number };
export type TrainingReport = {
  schema: 'adeps-test-paper-prior-training/1'; status: 'training' | 'evaluated'; updated_at: string;
  model: { id: string; name: string; parameters: number; prior_order: number; complex_channels: number; architecture: string; weights_sha256: string | null };
  training: { optimizer_steps: number; examples_seen: number; unique_scenes_seen: number; elapsed_seconds: number; device: string; optimizer: string; learning_rate: number; batch_size: number; gradient_accumulation: number; seed: number };
  data: { generator: string; corpus: string; train_speakers: string[]; validation_speakers: string[]; test_speakers: string[]; downloaded_utterances: number; train_scene_pool: number; validation_scenes: number; test_scenes: number; manifest_sha256: string; array_conditioning: false; sources: { title: string; url: string; license: string }[] };
  configuration: { sample_rate_hz: number; n_fft: number; hop: number; frames: number; normalization: string; compressed_std: number; sigma_data: number; sigma_min: number; sigma_max: number; rho: number };
  history: { step: number; loss: number; validation_loss?: number; elapsed_seconds: number }[];
  evaluation: null | { split: string; scenes: number; speaker_ids: string[]; rows: EvaluationRow[]; summary: string };
  paper: { source: string; matched: string[]; differences: string[] };
  artifacts: { checkpoint_url?: string; command: string; report_url: string };
};
type LoadState = { state: 'loading' } | { state: 'unavailable' | 'invalid' } | { state: 'ready'; report: TrainingReport };
const REPORT = '/models/paper-prior-training.json';
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const nonnegative = (value: unknown) => finite(value) && value >= 0;
const count = (value: unknown) => nonnegative(value) && Number.isInteger(value);
const positive = (value: unknown) => finite(value) && value > 0;
const hash = (value: unknown) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(v => typeof v === 'string');
const text = (value: unknown): value is string => typeof value === 'string';
const safeLink = (value: string | undefined) => {
  if (!value) return undefined;
  if (value.startsWith('https://')) return value;
  return /^[\w./-]+$/.test(value) && !value.includes('..') && !value.startsWith('//') ? asset(value) : undefined;
};

export function validTrainingReport(input: unknown): input is TrainingReport {
  if (!input || typeof input !== 'object') return false;
  const r = input as TrainingReport;
  if (r.schema !== 'adeps-test-paper-prior-training/1' || !['training', 'evaluated'].includes(r.status)
    || !text(r.updated_at) || !Number.isFinite(Date.parse(r.updated_at)) || !r.model || !r.training || !r.data || !r.configuration || !r.paper || !r.artifacts) return false;
  const { model: m, training: t, data: d, configuration: c } = r;
  if (m.id !== 'paper-prior-v1' || ![m.id, m.name, m.architecture, t.device, t.optimizer, d.generator, d.corpus, c.normalization, r.artifacts.command].every(text)
    || !positive(m.parameters) || !Number.isInteger(m.parameters) || m.prior_order !== 5 || m.complex_channels !== 36
    || !(m.weights_sha256 === null || hash(m.weights_sha256)) || (r.status === 'evaluated' && !hash(m.weights_sha256))
    || ![t.optimizer_steps, t.examples_seen, t.unique_scenes_seen, t.seed, d.downloaded_utterances, d.train_scene_pool, d.validation_scenes, d.test_scenes].every(count)
    || !nonnegative(t.elapsed_seconds) || !positive(t.learning_rate)
    || ![t.batch_size, t.gradient_accumulation, c.sample_rate_hz, c.n_fft, c.hop, c.frames].every(v => positive(v) && Number.isInteger(v))
    || ![c.compressed_std, c.sigma_data, c.sigma_min, c.sigma_max, c.rho].every(positive) || c.sigma_min >= c.sigma_max
    || d.array_conditioning !== false || !hash(d.manifest_sha256)
    || ![d.train_speakers, d.validation_speakers, d.test_speakers, r.paper.matched, r.paper.differences].every(strings)
    || !Array.isArray(d.sources) || !d.sources.every(s => s && [s.title, s.url, s.license].every(text))
    || !text(r.paper.source) || !text(r.artifacts.report_url)) return false;
  const splits = [...d.train_speakers, ...d.validation_speakers, ...d.test_speakers];
  if (new Set(splits).size !== splits.length) return false;
  if (!Array.isArray(r.history) || !r.history.every((row, i) => row && count(row.step) && row.step <= t.optimizer_steps
    && (i === 0 || row.step > r.history[i - 1].step) && nonnegative(row.loss) && nonnegative(row.elapsed_seconds)
    && (row.validation_loss === undefined || finite(row.validation_loss)))) return false;
  if (r.evaluation === null) return r.status === 'training';
  const e = r.evaluation;
  if (!e || !text(e.split) || !positive(e.scenes) || !Number.isInteger(e.scenes) || !strings(e.speaker_ids)
    || !text(e.summary) || !Array.isArray(e.rows) || !e.rows.length) return false;
  return e.rows.every((row, i) => row && positive(row.sigma) && (i === 0 || row.sigma > e.rows[i - 1].sigma)
    && [row.noisy_nmse_db, row.gaussian_nmse_db, row.trained_nmse_db, row.improvement_over_noisy_db, row.improvement_over_gaussian_db].every(finite)
    && Math.abs(row.noisy_nmse_db - row.trained_nmse_db - row.improvement_over_noisy_db) < 1e-5
    && Math.abs(row.gaussian_nmse_db - row.trained_nmse_db - row.improvement_over_gaussian_db) < 1e-5);
}

export default function PaperTraining({ language, active = true, onLoadExample, exampleBusy = false, exampleDisabled = false, exampleError = '', sectionId = 'paper-prior-training' }: {
  language: 'jp' | 'en'; active?: boolean; sectionId?: string; onLoadExample?: (expectedWeightsSha: string) => void; exampleBusy?: boolean; exampleDisabled?: boolean; exampleError?: string;
}) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [load, setLoad] = useState<LoadState>({ state: 'loading' });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void fetch(asset(REPORT), { cache: 'no-store', signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('unavailable');
      const data: unknown = await response.json();
      if (!controller.signal.aborted) setLoad(validTrainingReport(data) ? { state: 'ready', report: data } : { state: 'invalid' });
    }).catch(() => { if (!controller.signal.aborted) setLoad({ state: 'unavailable' }); });
    return () => controller.abort();
  }, [active, revision]);
  const report = load.state === 'ready' ? load.report : null;
  useEffect(() => {
    if (!active || report?.status !== 'training') return;
    const timer = window.setTimeout(() => setRevision(value => value + 1), 30000);
    return () => window.clearTimeout(timer);
  }, [active, report, revision]);
  const n = (value: number) => value.toLocaleString(language === 'jp' ? 'ja-JP' : 'en-US');
  const decimal = (value: number, places = 3) => value.toFixed(places);
  const delta = (value: number) => `${value > 0 ? '+' : ''}${decimal(value)}`;
  const evaluation = report?.evaluation;
  const improved = evaluation?.rows.filter(row => row.improvement_over_gaussian_db > 0).length ?? 0;
  const checkpoint = safeLink(report?.artifacts.checkpoint_url);
  return <section id={sectionId} className="paper-training" aria-label={l('音声で学習する拡散priorの記録', 'Speech-trained diffusion prior record')}>
    <header className="pt-heading"><span className="pt-eyebrow">SPEECH PRIOR / LOCAL TRAINING</span>
      <h3>{l('音声と残響から学ぶ、拡散prior。', 'A diffusion prior trained on speech and reverberation.')}</h3>
      <p>{l('大規模な時間・周波数モデルの学習と評価を、ローカルのTorch環境で行う独立実装です。このパネルは保存された記録を表示します。ページを開いても、新モデルの学習や推論は始まりません。',
        'An independently implemented time–frequency model trained and evaluated in local Torch. This panel displays saved records. Opening this page does not train or run the new model.')}</p>
      <p className="pt-runtime">{l('公開Web：計算済み例の表示・比較・試聴 ／ 新しい復元計算：ローカルTorch', 'Public web: view, compare and hear computed examples / New reconstruction: local Torch')}</p>
    </header>
    <div className="pt-toolbar"><span>{report ? l('記録日時', 'Record updated') + ': ' + new Date(report.updated_at).toLocaleString(language === 'jp' ? 'ja-JP' : 'en-US') : l('保存済みの学習記録を確認', 'Checking the saved training record')}</span>
      <button type="button" onClick={() => setRevision(value => value + 1)}><RefreshCw size={13}/>{l('記録を再読込', 'Reload record')}</button></div>
    {load.state === 'loading' && <p className="pt-notice">{l('学習記録を読み込んでいます。', 'Loading the training record.')}</p>}
    {(load.state === 'unavailable' || load.state === 'invalid') && <p className="pt-notice">{load.state === 'invalid'
      ? l('記録の形式や整合性を確認できませんでした。未確認の値を精度として表示しません。', 'The record format or consistency could not be verified. Unverified values are not displayed as accuracy.')
      : l('このページでは、まだ有効な学習記録を読み込めません。学習が完了したことやモデルの精度は確認できていません。', 'A valid training record is not available here yet. Training completion and model accuracy are unconfirmed.')}</p>}
    {report && <>
      <div className="pt-identity"><span>{report.model.id}</span><span>{report.status === 'evaluated' ? l('保存した重みを評価済み', 'Saved checkpoint evaluated') : l('学習の中間記録', 'Intermediate training record')}</span></div>
      <dl className="pt-numbers">
        <div><dt>{l('パラメータ', 'Parameters')}</dt><dd>{n(report.model.parameters)}</dd></div>
        <div><dt>{l('重みの更新回数', 'Optimizer steps')}</dt><dd>{n(report.training.optimizer_steps)}</dd></div>
        <div><dt>{l('学習に使った固有シーン', 'Unique scenes seen')}</dt><dd>{n(report.training.unique_scenes_seen)}</dd></div>
        <div><dt>{l('学習話者', 'Training speakers')}</dt><dd>{n(report.data.train_speakers.length)}</dd></div>
      </dl>
      <p className="pt-data">{report.data.generator} + {report.data.corpus} · {l('読み込んだ発話', 'Downloaded utterances')} {n(report.data.downloaded_utterances)} · {l('処理した例数（繰り返し含む）', 'Examples processed, including repeats')} {n(report.training.examples_seen)}</p>
      <p className="pt-scope">{l('学習ターゲットは、マイク観測に変換する前の理想的な5次Ambisonics係数です。マイク配置や応答Vはpriorの学習入力に含めません。音声・室内応答の出所と分割は、この記録に示した範囲です。',
        'Training targets are ideal order-5 Ambisonics coefficients before microphone observation. Array geometry and response V are not prior inputs. Speech, room-response sources and splits are limited to those recorded here.')}</p>
      {onLoadExample && <div className="pt-example"><button type="button" disabled={exampleBusy || exampleDisabled || report.status !== 'evaluated' || !report.model.weights_sha256}
        onClick={() => { if (report.model.weights_sha256) onLoadExample(report.model.weights_sha256); }}>
        {exampleBusy ? <LoaderCircle size={15} className="spin"/> : <Play size={15}/>}{exampleBusy ? l('計算済み例を読み込んでいます', 'Loading the computed example') : l('新モデルの計算済み例を開く', 'Load full-size model example')}</button>
        <p>{l('この重みで実際に計算した音声例を、上の3D表示・線形比較・試聴へ読み込みます。学習記録と重みSHAが一致する例だけを開きます。新モデルをブラウザーで再計算する操作ではありません。',
          'Load an example actually computed with these weights into the 3D view, linear comparison and audio player above. The example must match this record’s checkpoint SHA. This does not rerun the new model in your browser.')}</p>
        {exampleError && <p role="alert">{exampleError}</p>}</div>}
      {report.history.length > 0 && <div className="pt-chart"><Plot x={report.history.map(row => row.step)} log={false} unit="loss" xLabel={l('重みの更新回数', 'Optimizer step')}
        label={l('保存された学習曲線 · 低いほど小さい誤差', 'Recorded training curve · lower error is better')}
        series={[{ name: l('学習損失', 'Training loss'), values: report.history.map(row => row.loss), color: '#eee' }]} />
        <p>{l('EDMの重み付きMSEです。学習損失の低下だけでは、未知の音声や実会場での改善を示せません。記録された更新点を結んで表示しています。', 'EDM-weighted MSE. Lower training loss alone does not demonstrate improvement on unseen speech or in a venue. Lines connect recorded updates.')}</p></div>}
      {report.history.some(row => row.validation_loss !== undefined) && <div className="pt-chart"><Plot
        x={report.history.filter(row => row.validation_loss !== undefined).map(row => row.step)} log={false} unit="dB" xLabel={l('重みの更新回数', 'Optimizer step')}
        label={l('検証データの誤差 · 学習損失とは別の尺度', 'Validation error · a different scale from training loss')}
        series={[{ name: l('3つのσの平均NMSE', 'Mean NMSE over 3 sigma values'), values: report.history.filter(row => row.validation_loss !== undefined).map(row => row.validation_loss!), color: '#bbb' }]} />
        <p>{l('検証用4シーンに対しσ=0.1・1・10それぞれで集約NMSEを求め、3つのdB値を算術平均しています。上の学習MSEと同じ縦軸では比較しません。', 'Pooled NMSE is computed on four validation scenes at sigma 0.1, 1 and 10, then the three dB values are arithmetically averaged. It is not compared on the same vertical scale as training MSE above.')}</p></div>}
      <div className="pt-evaluation"><h4>{l('学習に使わないデータでのノイズ除去', 'Denoising on held-out data')}</h4>
        {evaluation ? <>
          <p>{evaluation.split} · {n(evaluation.scenes)} {l('シーン', 'scenes')} · {l('話者', 'speakers')}: {evaluation.speaker_ids.join(', ')}<br/>
            {l(`ガウス縮小より誤差が小さかった条件：${improved} / ${evaluation.rows.length}。改善・悪化を両方表示します。`, `Lower error than Gaussian shrinkage: ${improved} / ${evaluation.rows.length} conditions. Both improvements and regressions are shown.`)}</p>
          <Plot x={evaluation.rows.map(row => row.sigma)} label={l('ノイズ強度ごとの復元誤差', 'Denoising error by noise level')} xLabel="σ" unit="dB"
            series={[{ name: l('無処理', 'Noisy input'), values: evaluation.rows.map(row => row.noisy_nmse_db), color: '#888', dash: true },
              { name: l('ガウス縮小', 'Gaussian shrinkage'), values: evaluation.rows.map(row => row.gaussian_nmse_db), color: '#bbb', dash: '2 5' },
              { name: l('新しい学習済みprior', 'New trained prior'), values: evaluation.rows.map(row => row.trained_nmse_db), color: '#fff' }]} />
          <div className="pt-table-wrap"><table><caption>{l('誤差はdBで低いほど良好。差は正なら学習済みpriorが改善、負なら悪化。', 'Lower error in dB is better. Positive differences favor the trained prior; negative differences indicate regression.')}</caption>
            <thead><tr><th scope="col">σ</th><th scope="col">{l('無処理', 'Noisy')}</th><th scope="col">{l('ガウス縮小', 'Gaussian')}</th><th scope="col">{l('学習済み', 'Trained')}</th><th scope="col">{l('対 無処理', 'Vs noisy')}</th><th scope="col">{l('対 ガウス縮小', 'Vs Gaussian')}</th></tr></thead>
            <tbody>{evaluation.rows.map(row => <tr key={row.sigma}><th scope="row">{row.sigma}</th><td>{decimal(row.noisy_nmse_db)}</td><td>{decimal(row.gaussian_nmse_db)}</td><td>{decimal(row.trained_nmse_db)}</td><td>{delta(row.improvement_over_noisy_db)}</td><td>{delta(row.improvement_over_gaussian_db)}</td></tr>)}</tbody></table></div>
          <p>{l('圧縮した理想係数に雑音を加えた、denoiser単体の検証です。σは係数上の雑音強度で、マイクのSNRや音圧ではありません。この結果だけでは、Vを使う反復復元・録音・会場再生の精度はわかりません。',
            'This tests the denoiser on corrupted compressed ideal coefficients. Sigma is coefficient-domain noise, not microphone SNR or SPL. These scores alone do not establish accuracy of iterative reconstruction with V, recordings, or venue playback.')}</p>
          <p>{l('NMSE = 10 log₁₀（全シーン・72実数成分・周波数・時間の誤差二乗和 ÷ 正解二乗和）。ガウス縮小は noisy ÷ (1 + σ²)、固定σdata=1。各σでは3つの方法に同一のノイズ付き入力を渡します。',
            'NMSE = 10 log₁₀(total squared error / total clean energy), pooled over scenes, 72 real coordinates, frequency and time. Gaussian shrinkage is noisy / (1 + sigma²), with fixed sigma_data=1. At each sigma, all three methods receive the same corrupted input.')}</p>
        </> : <p className="pt-notice">{l('この記録には独立評価の結果がまだありません。学習回数やモデルの大きさから精度を推測しません。', 'This record does not yet contain held-out results. Accuracy is not inferred from training steps or model size.')}</p>}
      </div>
      <details className="pt-details"><summary>{l('データ・分割・学習条件・重みの識別', 'Data, splits, training settings and checkpoint identity')}</summary>
        <dl>
          <div><dt>{l('ネットワーク', 'Network')}</dt><dd>{report.model.architecture}</dd></div>
          <div><dt>{l('話者の分割', 'Speaker split')}</dt><dd>{l('学習', 'Train')}: {report.data.train_speakers.join(', ')}<br/>{l('検証', 'Validation')}: {report.data.validation_speakers.join(', ')}<br/>{l('テスト', 'Test')}: {report.data.test_speakers.join(', ')}</dd></div>
          <div><dt>{l('シーン数', 'Scene counts')}</dt><dd>{l('学習候補', 'Training pool')} {n(report.data.train_scene_pool)} / {l('検証', 'Validation')} {n(report.data.validation_scenes)} / {l('テスト', 'Test')} {n(report.data.test_scenes)}<br/>{l('候補数と実際に処理した固有シーン数は区別します。', 'Pool size and the unique scenes actually processed are different counts.')}</dd></div>
          <div><dt>STFT</dt><dd>{n(report.configuration.sample_rate_hz)} Hz · FFT {report.configuration.n_fft} · hop {report.configuration.hop} · {report.configuration.frames} {l('フレーム', 'frames')}<br/>{l('学習時は各正解の共通RMSで割り、位相を保つ振幅圧縮後、学習16例から求めた固定RMSで割ります。記録のcompressed_stdは平均を引かないRMSを格納したキーです。推論時の最初の尺度にはLinear推定のRMSだけを使います。', 'Training divides by each clean target’s common RMS, applies phase-preserving magnitude compression, then divides by a fixed RMS from 16 training examples. The compressed_std key stores uncentered RMS, not centered standard deviation. Inference uses only Linear-estimate RMS for the first scale.')}</dd></div>
          <div><dt>{l('圧縮後の固定RMS', 'Fixed compressed-domain RMS')}</dt><dd>{decimal(report.configuration.compressed_std, 8)} · {l('学習16例から計算', 'Computed from 16 training examples')}</dd></div>
          <div><dt>{l('学習条件', 'Training settings')}</dt><dd>{report.training.optimizer} · lr {report.training.learning_rate} · batch {report.training.batch_size} · {l('勾配蓄積', 'gradient accumulation')} {report.training.gradient_accumulation}<br/>seed {report.training.seed} · {report.training.device} · {decimal(report.training.elapsed_seconds / 60, 1)} min</dd></div>
          <div><dt>{l('ノイズ条件', 'Noise settings')}</dt><dd>σ {report.configuration.sigma_min}–{report.configuration.sigma_max} · ρ {report.configuration.rho} · σdata {decimal(report.configuration.sigma_data, 6)}<br/>{l('σは実部・虚部それぞれに加える雑音の標準偏差です。1つの複素係数の雑音二乗振幅の期待値は2σ²です。', 'Sigma is noise standard deviation for each real or imaginary coordinate. Expected squared noise magnitude per complex coefficient is 2 sigma².')}</dd></div>
          <div><dt>{l('データ一覧 SHA-256', 'Data manifest SHA-256')}</dt><dd><code>{report.data.manifest_sha256}</code></dd></div>
          <div><dt>{l('保存重み SHA-256', 'Checkpoint SHA-256')}</dt><dd><code>{report.model.weights_sha256 ?? l('この記録には未保存', 'Not saved in this record')}</code></dd></div>
        </dl>
        <div className="pt-sources">{report.data.sources.map((source, i) => <div key={`${source.url}-${i}`}>{safeLink(source.url) ? <a href={safeLink(source.url)} target="_blank" rel="noreferrer">{source.title}<ExternalLink size={12}/></a> : <span>{source.title}</span>}<small>{source.license}</small></div>)}</div>
      </details>
      <details className="pt-details"><summary>{l('論文と揃えた点・異なる点', 'Alignment with and differences from the paper')}</summary>
        <p>{l('原著と同じ公式重み・実装・評価結果ではありません。近いパラメータ数でも、学習量やデータの分布が異なれば同じ精度にはなりません。下記は保存記録の原文です。',
          'These are not the authors’ official weights, implementation or results. Similar parameter counts do not establish equal accuracy when training scale or data distributions differ. The following lists reproduce the record’s original wording.')}</p>
        <div className="pt-paper-grid"><div><h5>{l('揃えた条件', 'Aligned conditions')}</h5><ul>{report.paper.matched.map((item, i) => <li key={i}>{item}</li>)}</ul></div><div><h5>{l('残る違い', 'Remaining differences')}</h5><ul>{report.paper.differences.map((item, i) => <li key={i}>{item}</li>)}</ul></div></div>
        {safeLink(report.paper.source) && <a href={safeLink(report.paper.source)} target="_blank" rel="noreferrer">{l('論文の出典', 'Paper source')}<ExternalLink size={12}/></a>}
      </details>
      <details className="pt-details"><summary>{l('ローカル実行と記録の取得', 'Local execution and records')}</summary>
        <p>{l('下は学習を再開するコマンド例です。学習時のoptimizerと乱数状態を含むtraining-state.ptが必要です。復元用の重みだけからの再開ではありません。新しい復元計算の起動方法は「実装と評価の詳細」に記載しています。', 'Below is an example for resuming training. It requires training-state.pt with optimizer and RNG state; inference weights alone are insufficient. See the implementation details for starting reconstruction.')}</p>
        <pre>{report.artifacts.command}</pre>
        {checkpoint && <a href={checkpoint} target="_blank" rel="noreferrer">{l('ローカル用チェックポイント', 'Checkpoint for local use')}<ExternalLink size={12}/></a>}
      </details>
    </>}
    <div className="pt-links"><a href={asset(REPORT)} target="_blank" rel="noreferrer">{l('学習・評価の全記録 JSON', 'Full training and evaluation JSON')}<ExternalLink size={12}/></a><a href={asset('/info/PAPER_PRIOR.md')} target="_blank" rel="noreferrer">{l('実装と評価の詳細 · JP / EN', 'Implementation and evaluation · JP / EN')}<ExternalLink size={12}/></a></div>
  </section>;
}
