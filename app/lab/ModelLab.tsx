'use client';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, CircleHelp, Download, FileAudio, LoaderCircle, Play, Square } from 'lucide-react';
import { useLanguage } from './i18n';
import { analysisApi, cancelAnalysis, isLocalEngine, onAnalysisProgress, type AnalysisProgress } from './scientificClient';
import { asset } from './assets';
import { Plot, fmt } from './Plots';
import sharedErrors from './neural-errors.json';
import './ModelLab.css';

type Quality = {
  reference_available?: boolean;
  nrmse_db?: number | null;
  coherence?: number | null;
  log_spectral_mae_db?: number | null;
  error_db_by_frequency?: (number | null)[];
  coherence_by_frequency?: (number | null)[];
  si_sdr?: { mean_valid_channels_db?: number | null } | null;
};
type SpatialResult = {
  kind: string;
  frequencies_hz: number[];
  microphones: number;
  frames: number;
  model: { name?: string; architecture?: string; parameter_count?: number; weights_sha256?: string; input_features?: number; training?: { steps?: number; selected_step?: number }; [key: string]: unknown };
  configuration: Record<string, unknown>;
  provenance: unknown;
  input_sha256?: string;
  tuning?: Record<string, unknown>;
  rank_deficient_bins?: number;
  legacy?: { skipped?: boolean; note?: string };
  quality: { linear: Quality; enhanced: Quality; legacy?: Quality };
  diagnostics: { elapsed_seconds?: number; linear_microphone_residual?: number | null; enhanced_microphone_residual?: number | null; [key: string]: unknown };
  output?: { linear_real: unknown; linear_imag: unknown; enhanced_real: unknown; enhanced_imag: unknown };
  audio?: { shared_export_gain?: number; [key: string]: unknown };
  bytes?: ArrayBuffer;
  filename?: string;
  notes?: string[];
};
type InputMode = 'synthetic' | 'source' | 'array';
const defaults = { microphones: 6, radius_m: .06, snr_db: 30, data_seed: 90210,
  scene: 'speech_like', regularization: .001, start_seconds: 0, duration_seconds: .4, analysis_sample_rate_hz: 16000, include_legacy: false };
type Configuration = typeof defaults;
type JsonRecord = Record<string, any>;
const japaneseErrors: Record<string, string> = {
  ...sharedErrors,
  'Unsupported microphone count': '対応するマイク数を選んでください。',
  'data_seed must be an unsigned 32-bit integer': '入力のseedは0〜4294967295の整数にしてください。',
  'Invalid array radius, SNR, or regularization': 'アレイ半径・SNR・正則化の値が範囲外です。',
  'Unknown source scene': '対応する音の条件を選んでください。',
  'Invalid frozen inference tuning': '保存された推論設定が不正です。ページを再読み込みしてください。',
  'Learned prediction has invalid shape or non-finite values': 'モデルの出力形式または数値が不正です。入力と応答データを確認してください。',
  'Mono WAV must be between 1 byte and 32 MB': '空ではない32 MB以下のWAVを選んでください。',
  'Choose a mono source WAV (8–96 kHz), not an array recording': '音源には8〜96 kHzのモノラルWAVを選んでください。マイク録音はZIP入力を使います。',
  'Unsupported WAV sample format': 'このWAVのサンプル形式には対応していません。',
  'Source WAV is silent or non-finite': '音源が無音か、不正な数値を含んでいます。',
  'Select a finite nonnegative start and a 0.02–5 second duration': '開始位置は0秒以上、区間長は0.02〜5秒にしてください。',
  'Selected segment exceeds the source WAV': '指定した区間がWAVの長さを超えています。開始位置と区間長を確認してください。',
  'Source simulation supports analysis sample rates 16 or 48 kHz': '解析レートには16 kHzまたは48 kHzを選んでください。',
  'Maximum 65536 frequency-time bins per run; use a shorter segment': '周波数×時間は65,536点までです。短い区間で実行してください。',
  'Segment exceeds 65536 frequency-time bins; shorten duration': '指定区間は周波数×時間65,536点を超えています。区間長を短くしてください。',
};

function save(name: string, content: BlobPart, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function serializable(result: SpatialResult) {
  const { bytes: _bytes, ...data } = result;
  return data;
}
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

export default function ModelLab() {
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [mode, setMode] = useState<InputMode>('synthetic');
  const [config, setConfig] = useState(defaults);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<SpatialResult | null>(null);
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false), [preparing, setPreparing] = useState(false);
  const [error, setError] = useState(''), [dirty, setDirty] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [progress, setProgress] = useState<AnalysisProgress>({ stage: 'ready' });
  const [benchmark, setBenchmark] = useState<JsonRecord | null>(null);
  const [benchmarkError, setBenchmarkError] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const locked = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    fetch(asset('/models/spatial-benchmark.json'), { signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error(String(response.status)); return response.json(); })
      .then(value => { if (mounted.current) setBenchmark(value); })
      .catch(error => { if (error.name !== 'AbortError' && mounted.current) setBenchmarkError(true); });
    return () => { mounted.current = false; controller.abort(); };
  }, []);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed((Date.now() - started) / 1000), 250);
    const unsubscribe = onAnalysisProgress(setProgress);
    return () => { clearInterval(timer); unsubscribe(); };
  }, [busy]);

  function update<K extends keyof Configuration>(key: K, value: Configuration[K]) {
    if (locked.current) return;
    setConfig(previous => ({ ...previous, [key]: value })); setDirty(!!result);
  }
  function changeMode(next: InputMode) {
    if (locked.current) return;
    setMode(next); setFile(null); setDirty(!!result); setError('');
    if (fileInput.current) fileInput.current.value = '';
  }
  async function run() {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError(''); setElapsed(0); setProgress({ stage: 'runtime' });
    try {
      if (mode !== 'synthetic' && !file) throw new Error(l('入力ファイルを選んでください。', 'Choose an input file.'));
      if (file && file.size > 32_000_000) throw new Error(l('入力ファイルは32 MBまでです。短い区間で保存してください。', 'Input limit: 32 MB. Save a short segment.'));
      for (const [key, value] of Object.entries(config)) {
        if (typeof value === 'number' && !Number.isFinite(value)) throw new Error(l(`条件「${key}」を確認してください。`, `Check the “${key}” setting.`));
      }
      const value = await analysisApi(mode === 'source' ? 'spatial-source' : mode === 'array' ? 'spatial-audio' : 'spatial',
        { ...config, enabled: true }, mode !== 'synthetic' ? await file!.arrayBuffer() : undefined);
      if (!value.quality?.linear || !value.quality?.enhanced || !Array.isArray(value.frequencies_hz)) {
        throw new Error(l('比較結果の形式を確認できませんでした。', 'The response does not contain a valid comparison.'));
      }
      if (mounted.current) { setResult(value as SpatialResult); setDirty(false); }
    } catch (error) {
      if (mounted.current) setError((error as Error).message);
    } finally {
      locked.current = false; if (mounted.current) setBusy(false);
    }
  }
  async function example() {
    if (locked.current) return;
    locked.current = true; setPreparing(true); setError('');
    try {
      const value = await analysisApi('spatial-example', {});
      if (!value.bytes) throw new Error(l('サンプルZIPを生成できませんでした。', 'The example ZIP could not be generated.'));
      if (mounted.current) save(value.filename || 'ADEPS_spatial_input_example.zip', value.bytes, 'application/zip');
    } catch (error) { if (mounted.current) setError((error as Error).message); }
    finally { locked.current = false; if (mounted.current) setPreparing(false); }
  }
  function numeric(key: keyof Configuration, jp: string, en: string, min: number, max: number, step: number) {
    return <label className="neural-field"><span>{l(jp, en)}</span><input aria-label={l(jp, en)} type="number"
      value={Number(config[key])} min={min} max={max} step={step} onChange={event => update(key, Number(event.target.value))}/></label>;
  }
  const linear = result?.quality.linear, enhanced = result?.quality.enhanced;
  const selected = enabled ? enhanced : linear;
  const difference = finite(linear?.nrmse_db) && finite(enhanced?.nrmse_db) ? linear.nrmse_db - enhanced.nrmse_db : null;
  const reference = finite(linear?.nrmse_db) && finite(enhanced?.nrmse_db);
  const selectionName = enabled ? l('ON · 独自モデル', 'ON · Independent model') : l('OFF · 線形エンコーダ', 'OFF · Linear encoder');
  const fraction = progress.total ? Math.min(1, (progress.step || 0) / progress.total) : undefined;
  const cases = benchmark ? (Array.isArray(benchmark.cases) ? benchmark.cases : Array.isArray(benchmark.results) ? benchmark.results : []) : [];
  const benchmarkMismatch = !!(benchmark?.model_sha256 && result?.model.weights_sha256 && benchmark.model_sha256 !== result.model.weights_sha256);

  return <div className="model-lab neural-page">
    <div className="model-intro">
      <div className="model-intro-title"><span className="eyebrow">INDEPENDENT LEARNED ENCODER · 02</span>
        <h2>{l('同じ音で、違いを確かめる。', 'One input. Two reconstructions.')}</h2></div>
      <p>{l('マイク応答から得た物理情報と、観測した音の時間的な特徴を学習モデルへ入力します。線形処理と独自モデルを一度に計算し、ON / OFFで同じ試行の結果を切り替えます。',
        'Condition the learned model on physical information from the microphone response and temporal features of the observations. Compute linear and learned reconstructions together, then switch ON / OFF within the same trial.')}</p>
      <div className="model-flow">{[l('音源・マイク観測', 'Source or microphone input'), l('同じ入力を2つの処理へ', 'Two methods, same input'), l('参照との誤差を比較', 'Compare against a reference'), l('FOAを書き出す', 'Export FOA')].map((text, i) =>
        <span key={text}><b>{String(i + 1).padStart(2, '0')}</b>{text}{i < 3 && <ArrowRight size={14}/>}</span>)}</div>
    </div>
    <div className="note"><CircleHelp size={17}/><div>{l('独自学習・独自手法です。論文の公式ADEPSモデルとの直接比較は未実施です。ここで線形法に勝っても、論文を上回ったことにはなりません。改善・悪化・評価できない条件をすべて残します。',
      'This is an independently trained method. No direct evaluation against the authors’ ADEPS model has been performed. Beating linear encoding here does not establish an improvement over the paper. Improvements, regressions and unevaluable cases are retained.')}</div></div>

    <div className="model-workspace">
      <section className="panel model-settings">
        <div className="panel-head"><h2>{l('入力を選ぶ', 'Choose the input')}</h2><span>01 — INPUT</span></div>
        <fieldset disabled={busy || preparing}>
          <label className="neural-field"><span>{l('検証の方法', 'Experiment')}</span><select aria-label={l('検証の方法', 'Experiment')} value={mode} onChange={event => changeMode(event.target.value as InputMode)}>
            <option value="synthetic">{l('合成データ · マイク不要', 'Synthetic data · no microphone')}</option>
            <option value="source">{l('MaxなどのモノラルWAV → 仮想マイク', 'Mono WAV from Max → virtual array')}</option>
            <option value="array">{l('マイク録音 ＋ 応答データ ZIP', 'Microphone recording + response ZIP')}</option>
          </select></label>
          {mode === 'synthetic' && <label className="neural-field model-spaced"><span>{l('音の条件', 'Sound condition')}</span><select aria-label={l('音の条件', 'Sound condition')} value={config.scene} onChange={event => update('scene', event.target.value)}>
            <option value="speech_like">{l('音声に似た合成音', 'Speech-like synthesis')}</option>
            <option value="music">{l('音楽に似た合成音', 'Music-like synthesis')}</option>
            <option value="noise">{l('広帯域ノイズ', 'Broadband noise')}</option>
            <option value="transient">{l('短い過渡音', 'Transient sound')}</option>
          </select></label>}
          {mode === 'synthetic' && <p className="neural-small">{l('1 Hz〜20 kHzの128周波数で合成した複素スペクトルです。実音声の録音や、1 Hzの測定分解能を表すものではありません。音を聴いて比較する場合は、WAV入力を使います。',
            'Synthetic complex spectra at 128 frequencies from 1 Hz to 20 kHz. These are not recorded audio or a 1 Hz measurement resolution. Use a WAV input for listening comparisons.')}</p>}
          {mode !== 'synthetic' && <div className="model-file">
            <div className="neural-field"><span>{mode === 'source' ? l('モノラルWAV', 'Mono WAV') : l('array.json ＋ microphones.wav のZIP', 'ZIP: array.json + microphones.wav')}</span>
              <input ref={fileInput} type="file" hidden accept={mode === 'source' ? '.wav,audio/wav' : '.zip,application/zip'} onChange={event => { setFile(event.target.files?.[0] || null); setDirty(!!result); }}/>
              <button type="button" className="model-file-button" onClick={() => fileInput.current?.click()}><FileAudio size={15}/>{mode === 'source' ? l('WAVファイルを選ぶ', 'Choose a WAV file') : l('ZIPファイルを選ぶ', 'Choose a ZIP file')}</button>
              {!file && <small className="neural-small">{l('ファイルは選択されていません。', 'No file selected.')}</small>}</div>
            {file && <p className="neural-small">{file.name} · {(file.size / 1e6).toFixed(2)} MB</p>}
            {mode === 'source' && <label className="neural-field model-spaced"><span>{l('解析レート / Hz', 'Analysis rate / Hz')}</span><select aria-label={l('解析レート / Hz', 'Analysis rate / Hz')} value={config.analysis_sample_rate_hz} onChange={event => {
              const rate = Number(event.target.value);
              setConfig(previous => ({ ...previous, analysis_sample_rate_hz: rate, duration_seconds: rate === 48000 ? .1 : .4 }));
              setDirty(!!result);
            }}><option value="16000">16,000 Hz · {l('上限8 kHz', 'up to 8 kHz')}</option><option value="48000">48,000 Hz · {l('20 kHz帯域を含む', 'includes 20 kHz')}</option></select>
              <small className="neural-small">{l('選択すると区間長を16 kHzでは0.4秒、48 kHzでは0.1秒へ変更します。入力WAVは8〜96 kHz。必要に応じて解析レートへ変換します。',
                'Selecting a rate sets the segment to 0.4 s at 16 kHz or 0.1 s at 48 kHz. Input WAV: 8–96 kHz, resampled to the analysis rate as needed.')}</small></label>}
            <div className="neural-fields">{numeric('start_seconds', '開始位置 / 秒', 'Start / seconds', 0, 36000, .1)}{numeric('duration_seconds', '区間長 / 秒', 'Segment / seconds', .02, 5, .05)}</div>
            <p className="neural-small">{mode === 'source' ? l('保存した音源を仮想アレイで収録したことにして計算します。実際の会場やマイクの性能を測定するものではありません。',
              'Simulate recording this source through a virtual array. This does not measure a real venue or microphone.') : l('実録音と、そのマイクに対応する取得行列Vが必要です。単にB-formatへ変換した録音やモノラル音源では代用できません。',
              'Requires microphone observations and a matching acquisition matrix V. A B-format conversion or a mono source alone is not a substitute.')}</p>
            <p className="neural-small">{l('新モデルは周波数×時間65,536点まで。標準の窓設定では16 kHzで約4秒、48 kHzで約1.3秒が目安です。正確な上限は窓・hopに依存します。ZIPの解析レートはarray.jsonに従います。',
              'The new model supports up to 65,536 frequency-time bins: roughly 4 s at 16 kHz or 1.3 s at 48 kHz with standard windows. The exact limit depends on the window and hop. ZIP analysis follows array.json.')}</p>
            <p className="neural-small">{l('旧小型MLPとの追加比較は8192点まで。表示軸は1 Hz〜20 kHzですが、データのない帯域には曲線を描きません。',
              'Optional legacy small-MLP comparison remains limited to 8192 bins. The display spans 1 Hz–20 kHz; bands without data are not plotted.')}</p>
          </div>}
          {mode !== 'array' && <div className="neural-fields">
            <label className="neural-field"><span>{l('仮想マイク数', 'Virtual microphones')}</span><select aria-label={l('仮想マイク数', 'Virtual microphones')} value={config.microphones} onChange={event => update('microphones', Number(event.target.value))}>{[4, 5, 6, 8, 12, 16].map(value => <option key={value}>{value}</option>)}</select></label>
            {numeric('radius_m', 'アレイ半径 / m', 'Array radius / m', .01, .25, .01)}
            {numeric('snr_db', '観測SNR / dB', 'Observation SNR / dB', 0, 80, 5)}
            {numeric('data_seed', '入力のseed', 'Input seed', 0, 4294967295, 1)}
          </div>}
          <div className="model-spaced">{numeric('regularization', '線形処理の相対正則化', 'Relative linear regularization', .00000001, 10, .001)}</div>
          <label className="neural-check"><input type="checkbox" checked={config.include_legacy} onChange={event => update('include_legacy', event.target.checked)}/>{l('旧小型MLPの拡散推論も比較する（時間がかかります）', 'Also compare legacy small-MLP diffusion (slower)')}</label>
        </fieldset>
        <div className="neural-actions"><button className="primary" disabled={busy || preparing || (mode !== 'synthetic' && !file)} onClick={run}>
          {busy ? <LoaderCircle size={16} className="spin"/> : <Play size={16}/>} {l('同じ入力で比較する', 'Compare the same input')}</button>
          {busy && !isLocalEngine && <button onClick={cancelAnalysis}><Square size={14}/>{l('中止', 'Stop')}</button>}</div>
        {busy && <div className="neural-progress" role="status" aria-live="polite"><progress value={fraction} max={1}/><span>{progress.stage === 'spatial' ? l('モデルを計算中', 'Computing the learned model') : l('計算を準備中', 'Preparing computation')}{progress.total ? ` · ${progress.step || 0} / ${progress.total}` : ''} · {fmt(elapsed, 1)} s</span></div>}
        {error && <div className="error" role="alert">{language === 'jp' ? japaneseErrors[error] || error : error === '計算を中止しました。' ? 'Computation stopped.' : error}</div>}
        <button className="model-example" disabled={busy || preparing} onClick={example}>{preparing ? <LoaderCircle size={15} className="spin"/> : <FileAudio size={15}/>} {l('合成マイク録音の入力例 ZIP', 'Example synthetic recording ZIP')}</button>
        <p className="neural-small">{l('ON / OFFの切替では再計算しません。音源、観測ノイズ、モデル重み、出力ゲインを変えずに比較します。',
          'ON / OFF does not rerun inference. The input, observation noise, model weights and export gain remain fixed.')}</p>
      </section>

      <section className="panel model-results">
        <div className="panel-head"><h2>{l('結果を比べる', 'Compare the results')}</h2><span>02 — A / B</span></div>
        <div className="model-toggle-row"><div><span className="eyebrow">OUTPUT SELECTION</span><p>{selectionName}</p></div>
          <div className="model-toggle" role="group" aria-label={l('モデルのON / OFF', 'Model ON / OFF')}>
            <button type="button" aria-pressed={!enabled} onClick={() => setEnabled(false)}>OFF<span>{l('線形', 'Linear')}</span></button>
            <button type="button" aria-pressed={enabled} onClick={() => setEnabled(true)}>ON<span>{l('独自モデル', 'Learned')}</span></button>
          </div></div>
        <p className="model-toggle-help">{l('切り替わるのは表示と書き出し対象です。会場やMaxの音をリアルタイムに切り替える操作ではありません。',
          'Switches the displayed result and selected export. This does not switch live audio in Max or at a venue.')}</p>
        {dirty && <div className="note" role="status">{l('入力条件を変更しました。表示中は前回の結果です。再実行して更新してください。', 'Input settings changed. These are the previous results. Run again to update.')}</div>}
        {!result ? <div className="model-empty"><span>A / B</span><h3>{l('まずは、マイクなしで。', 'Start without a microphone.')}</h3><p>{l('「同じ入力で比較する」を押すと、独自モデルと線形処理の結果がここに表示されます。正解のある合成入力で、改善と失敗を確認できます。',
          'Select “Compare the same input” to see learned and linear results. A synthetic input with a known reference reveals both improvements and failures.')}</p></div> : <>
          <div className="neural-result-caption"><span>{result.microphones} MIC · {result.frequencies_hz.length} FREQ · {result.frames} FRAME</span><span>{fmt(result.diagnostics.elapsed_seconds, 2)} s</span></div>
          <div className="model-quality" aria-live="polite">
            <div><span>{l('選択した出力のFOA誤差', 'Selected output: FOA error')}</span><strong>{fmt(selected?.nrmse_db)}<small> dB</small></strong><p>{l('複素NRMSE · 小さいほど良い', 'Complex NRMSE · lower is better')}</p></div>
            <div><span>{l('Coherence', 'Coherence')}</span><strong>{fmt(selected?.coherence, 3)}</strong><p>{l('参照との整合 · 大きいほど良い', 'Agreement with reference · higher is better')}</p></div>
          </div>
          {!!result.rank_deficient_bins && <div className="note">{l('FOAを識別するランクが不足する周波数があります。DCや配列の形状を確認してください。',
            'Some frequencies do not provide full FOA rank. Check DC and array geometry.')} {result.rank_deficient_bins} / {result.frequencies_hz.length}</div>}
          {result.legacy?.skipped && <div className="note">{l('この区間は8192点を超えるため、旧小型MLPの比較は省略しました。新モデルと線形処理の比較は実行済みです。',
            'This segment exceeds 8192 bins, so the legacy small-MLP comparison was skipped. The new model and linear comparison completed.')}</div>}
          {reference ? <div className="model-verdict"><b>{difference! > 1e-9 ? l('この試行では独自モデルが改善', 'Learned model improved this trial') : difference! < -1e-9 ? l('この試行では線形処理が良好', 'Linear encoding was better in this trial') : l('この試行の誤差は同等', 'Equal error in this trial')}</b>
            <span>{l('NRMSE差：線形 − 独自', 'NRMSE difference: linear − learned')} {fmt(difference)} dB</span>
            <p>{l('この入力と条件に限る結果です。論文の公表値との直接比較や、実際の会場での改善を示しません。',
              'This result applies to this input and configuration. It is not a direct comparison to the paper or evidence of improvement in a real venue.')}</p></div>
            : <div className="note">{l('対応する正解FOAがないため、復元誤差とcoherenceを算出できません。マイク観測との残差が小さくても、音場が正しく復元されたとは限りません。',
              'Without a matching reference FOA, reconstruction error and coherence are unavailable. A small microphone residual alone does not establish accurate reconstruction.')}</div>}
          <div className="table-scroll model-metrics-table"><table><thead><tr><th>{l('同じ入力', 'Same input')}</th><th>OFF / {l('線形', 'Linear')}</th><th>ON / {l('独自', 'Learned')}</th>{result.quality.legacy && <th>{l('旧小型MLP', 'Legacy MLP')}</th>}</tr></thead>
            <tbody>{[
              { name: 'FOA NRMSE / dB ↓', key: 'nrmse_db' as const }, { name: 'Coherence ↑', key: 'coherence' as const },
              { name: l('対数スペクトル誤差 / dB ↓', 'Log-spectral error / dB ↓'), key: 'log_spectral_mae_db' as const },
            ].map(row => <tr key={row.key}><td>{row.name}</td><td>{fmt(linear?.[row.key], row.key === 'coherence' ? 3 : 2)}</td><td>{fmt(enhanced?.[row.key], row.key === 'coherence' ? 3 : 2)}</td>{result.quality.legacy && <td>{fmt(result.quality.legacy[row.key], row.key === 'coherence' ? 3 : 2)}</td>}</tr>)}
              {(linear?.si_sdr || enhanced?.si_sdr) && <tr><td>SI-SDR / dB ↑</td><td>{fmt(linear?.si_sdr?.mean_valid_channels_db)}</td><td>{fmt(enhanced?.si_sdr?.mean_valid_channels_db)}</td>{result.quality.legacy && <td>{fmt(result.quality.legacy.si_sdr?.mean_valid_channels_db)}</td>}</tr>}
            </tbody></table></div>
          {reference && <Plot frequency x={result.frequencies_hz} label={l('FOA誤差 · 小さいほど良い', 'FOA error · lower is better')}
            series={[{ name: l('OFF · 線形', 'OFF · Linear'), values: linear?.error_db_by_frequency || [], color: enabled ? '#898989' : '#fff', dash: true },
              { name: l('ON · 独自モデル', 'ON · Learned'), values: enhanced?.error_db_by_frequency || [], color: enabled ? '#fff' : '#898989' },
              ...(result.quality.legacy ? [{ name: l('旧小型MLP', 'Legacy MLP'), values: result.quality.legacy.error_db_by_frequency || [], color: '#666', dash: '2 5' }] : [])]}/>}
          {reference && <details className="model-details"><summary>{l('周波数ごとのcoherence', 'Coherence by frequency')}</summary><Plot frequency x={result.frequencies_hz} unit="" label={l('Coherence · 大きいほど良い', 'Coherence · higher is better')}
            series={[{ name: l('OFF · 線形', 'OFF · Linear'), values: linear?.coherence_by_frequency || [], color: '#999', dash: true }, { name: l('ON · 独自モデル', 'ON · Learned'), values: enhanced?.coherence_by_frequency || [], color: '#fff' }]}/></details>}
          <div className="neural-actions">
            <button onClick={() => {
              const data = serializable(result);
              save(`ADEPS_spatial_${enabled ? 'ON' : 'OFF'}_result.json`, JSON.stringify({ ...data, selection: { enabled, method: enabled ? 'enhanced' : 'linear' },
                selected_output: result.output ? { real: enabled ? result.output.enhanced_real : result.output.linear_real, imag: enabled ? result.output.enhanced_imag : result.output.linear_imag } : null }, null, 2));
            }}><Download size={15}/>{l('選択した出力・比較結果 JSON', 'Selected output + comparison JSON')}</button>
            {result.bytes && <button onClick={() => save(result.filename || 'ADEPS_spatial_FOA_comparison.zip', result.bytes!, 'application/zip')}><Download size={15}/>{l('OFF / ON 両方のFOA WAV', 'Both OFF / ON FOA WAVs')}</button>}
          </div>
          {result.audio && <p className="neural-small">{l('FOAはW,Y,Z,Xの4ch。出力一式には両方の処理を同じゲインで保存します。比較するときは、同じAmbisonicsデコーダ・スピーカー設定で再生してください。',
            'FOA contains four channels: W,Y,Z,X. The bundle exports both methods with a shared gain. Compare using the same Ambisonics decoder and speaker settings.')} {l('共通ゲイン', 'Shared gain')}: {fmt(result.audio.shared_export_gain, 4)}</p>}
        </>}
      </section>
    </div>

    {result && <section className="panel model-record">
      <div className="panel-head"><h2>{l('何を計算したか', 'What was computed')}</h2><span>03 — RECORD</span></div>
      <div className="model-record-grid"><div><span>{l('使用したモデル', 'Model used')}</span><h3>{result.model.name || 'Independent spatial model'}</h3><p>{result.model.architecture}</p></div>
        <div><span>{l('学習済みパラメータ', 'Trained parameters')}</span><h3>{result.model.parameter_count?.toLocaleString(language === 'jp' ? 'ja-JP' : 'en-US') || '—'}</h3><p>{l('学習ステップ', 'Training steps')}: {result.model.training?.steps?.toLocaleString() || '—'}<br/>{l('採用したステップ', 'Selected checkpoint step')}: {result.model.training?.selected_step?.toLocaleString() || '—'}<br/>{l('入力特徴数', 'Input features')}: {result.model.input_features ?? '—'}</p></div>
        <div><span>{l('マイク領域の相対残差', 'Relative microphone residual')}</span><h3>{fmt(result.diagnostics.linear_microphone_residual, 4)} → {fmt(result.diagnostics.enhanced_microphone_residual, 4)}</h3><p>{l('観測との整合の診断。復元品質の点数ではありません。', 'Observation consistency diagnostic, not a reconstruction-quality score.')}</p></div></div>
      <p className="neural-hash">SHA-256 / {result.model.weights_sha256 || '—'}{result.input_sha256 && <><br/>INPUT / {result.input_sha256}</>}</p>
      <div className="model-applied-settings"><h3>{l('この試行で適用した設定', 'Settings applied in this trial')}</h3><p>{l('予測の混合率', 'Prediction blend')}: {fmt(typeof result.tuning?.blend === 'number' ? result.tuning.blend : null, 2)} · {l('追加の観測整合', 'Additional observation consistency')}: {result.tuning?.consistency === 0 ? l('OFF（係数0）', 'OFF (coefficient 0)') : typeof result.tuning?.consistency === 'number' ? `${l('ON', 'ON')} (${fmt(result.tuning.consistency, 2)})` : '—'}</p>
        <p className="neural-small">{l('物理情報は解像行列R = E Vとしてモデルに入力します。追加の観測整合は独立した後処理で、調整用検証では係数0が選ばれたため、同梱設定では適用しません。',
          'Physical information enters the model through R = E V. Additional observation consistency is a separate post-processing step. Tuning validation selected coefficient 0, so the bundled setting does not apply that step.')}</p></div>
      <details className="model-details"><summary>{l('設定・出典・制約をすべて見る', 'Inspect settings, provenance and limitations')}</summary><pre>{JSON.stringify({ model: result.model, configuration: result.configuration, tuning: result.tuning, provenance: result.provenance, diagnostics: result.diagnostics, notes: result.notes }, null, 2)}</pre></details>
    </section>}

    <section className="panel model-benchmark">
      <div className="panel-head"><div><h2>{l('学習に使わなかった条件で評価する', 'Evaluate beyond the training data')}</h2><p>{l('学習・調整用の検証・最終テストを分けます。失敗したケースも含めて比較します。',
        'Training, tuning validation and final testing are separated. Failed cases remain in the comparison.')}</p></div><span>04 — BENCHMARK</span></div>
      <p className="neural-small">{l('以下は同梱モデルの合成データによる評価記録です。上の入力条件を変えても、この記録は変わりません。論文と同一のデータ・モデルによる比較ではありません。',
        'The following is the bundled model’s recorded synthetic evaluation. Changing the controls above does not change this record. It does not use the paper’s identical data or model.')}</p>
      {benchmark ? <>
        {benchmarkMismatch && <div className="note" role="status">{l('この評価記録のモデルのハッシュが、上の試行で使った重みと一致しません。別バージョンの評価記録として扱い、現在のモデルの性能とは判断しないでください。',
          'This benchmark model hash differs from the weights used in the trial above. Treat it as a record for another version, not as evidence for the current model.')}</div>}
        <p className="neural-hash">BENCHMARK MODEL SHA-256 / {benchmark.model_sha256 || '—'}</p>
        {finite(benchmark.summary?.mean_improvement_over_tuned_linear_db) && <div className="model-strong-baseline"><div><span>{l('調整済みの線形法に対する平均改善量', 'Mean improvement over tuned linear encoding')}</span><strong>{fmt(benchmark.summary.mean_improvement_over_tuned_linear_db)}<small> dB</small></strong></div><p>{l('別の検証セットで線形法の正則化を選び、最終テストで固定して比較しています。正の値で独自モデルが良好です。',
          'Linear regularization was selected on separate validation data and frozen for final testing. Positive values favor the learned model.')} {l('線形の相対正則化', 'Linear relative regularization')}: {finite(benchmark.tuning?.selected_linear_regularization) ? benchmark.tuning.selected_linear_regularization : '—'}</p></div>}
        {benchmark.summary && <div className="model-benchmark-summary">
          <div><span>{l('既定線形に対する改善 / 悪化 / 同等', 'Improved / worse / equal vs default linear')}</span><strong>{benchmark.summary.win_count ?? '—'} / {benchmark.summary.loss_count ?? '—'} / {benchmark.summary.tie_count ?? '—'}</strong><small>{benchmark.summary.cases ?? cases.length} {l('条件', 'cases')}</small></div>
          <div><span>{l('既定線形に対する平均改善量', 'Mean improvement over default linear')}</span><strong>{fmt(benchmark.summary.mean_improvement_db)}<small> dB</small></strong><small>{l('正の値で独自モデルが良好', 'Positive favors the learned model')}</small></div>
          <div><span>{l('既定線形に対する改善量の中央値', 'Median improvement over default linear')}</span><strong>{fmt(benchmark.summary.median_improvement_db)}<small> dB</small></strong><small>{l('既定線形NRMSE − 独自NRMSE', 'Default linear NRMSE − learned NRMSE')}</small></div>
          <div><span>{l('既定線形に対する平均改善量の95%区間', '95% interval: improvement over default linear')}</span><strong>{fmt(benchmark.summary.bootstrap_95ci_db?.[0])} … {fmt(benchmark.summary.bootstrap_95ci_db?.[1])}<small> dB</small></strong><small>{l('テスト条件の再標本化による区間', 'Resampling interval over test cases')}</small></div>
        </div>}
        <p className="neural-small">{l('学習 → モデル検証 → 調整用検証 → 最終テストの順に分離。具体的なseedと生成条件は下の詳細に保存しています。テストの音源分布が実録音と一致する保証はありません。',
          'Training → model validation → tuning validation → final test are separate. Seeds and generation conditions are recorded below. The test source distribution is not guaranteed to match real recordings.')}</p>
        {cases.length > 0 && <div className="table-scroll model-benchmark-table"><table><thead><tr><th>{l('条件', 'Condition')}</th><th>MIC / SNR</th><th>{l('既定線形 NRMSE / dB', 'Default linear NRMSE / dB')}</th><th>{l('調整済み線形 NRMSE / dB', 'Tuned linear NRMSE / dB')}</th><th>{l('独自 NRMSE / dB', 'Learned NRMSE / dB')}</th><th>{l('調整済み線形と比較', 'Against tuned linear')}</th><th>{l('Coherence 既定線形 → 独自', 'Coherence default linear → learned')}</th></tr></thead><tbody>{cases.map((row: JsonRecord, index: number) => {
          const base = row.quality?.linear?.nrmse_db ?? row.linear?.nrmse_db ?? row.linear_nrmse_db;
          const learned = row.quality?.enhanced?.nrmse_db ?? row.enhanced?.nrmse_db ?? row.enhanced_nrmse_db;
          const tuned = row.tuned_linear_nrmse_db;
          return <tr key={row.id || index}><td>{row.name || row.id || row.scene || `Case ${index + 1}`}<small className="model-case-flags">{[row.mismatch ? l('音場の次数不一致', 'Order mismatch') : '', row.coplanar ? l('同一平面', 'Coplanar') : ''].filter(Boolean).join(' · ')}</small></td><td>{row.microphones ?? '—'} / {row.snr_db ?? '—'} dB</td><td>{fmt(base)}</td><td>{fmt(tuned)}</td><td>{fmt(learned)}</td><td>{row.error ? l('計算失敗', 'Failed') : finite(tuned) && finite(learned) ? learned < tuned ? l('独自が良好', 'Learned better') : learned > tuned ? l('線形が良好', 'Linear better') : l('同等', 'Equal') : l('未評価', 'Not evaluated')}</td><td>{fmt(row.linear_coherence, 3)} → {fmt(row.enhanced_coherence, 3)}</td></tr>;
        })}</tbody></table></div>}
        {Array.isArray(benchmark.audio_cases) && benchmark.audio_cases.length > 0 && <div className="model-audio-benchmark">
          <h3>{l('時間波形を通した追加テスト', 'Additional waveform tests')}</h3>
          <p className="neural-small">{l('合成WAVを仮想アレイへ通した別のテストです。実際の会場での収録ではありません。スペクトル上の誤差が改善しても、時間波形のSI-SDRは悪化する場合があります。',
            'Separate tests pass synthetic WAV files through a virtual array. These are not venue recordings. Spectral error may improve while waveform SI-SDR becomes worse.')}</p>
          <div className="table-scroll"><table><thead><tr><th>{l('合成WAV', 'Synthetic WAV')}</th><th>{l('FOA NRMSE：線形 → 独自 / dB ↓', 'FOA NRMSE: linear → learned / dB ↓')}</th><th>{l('SI-SDR：線形 → 独自 / dB ↑', 'SI-SDR: linear → learned / dB ↑')}</th><th>{l('指標ごとの変化', 'Change by metric')}</th></tr></thead><tbody>{benchmark.audio_cases.map((row: JsonRecord, index: number) => {
            const ql = row.quality?.linear, qe = row.quality?.enhanced;
            const ln = ql?.nrmse_db, en = qe?.nrmse_db, ls = ql?.si_sdr?.mean_valid_channels_db, es = qe?.si_sdr?.mean_valid_channels_db;
            const metricChange = (before: unknown, after: unknown, higher: boolean) => !finite(before) || !finite(after) ? l('未評価', 'Unavailable') : before === after ? l('同等', 'Equal') : (higher ? after > before : after < before) ? l('改善', 'Improved') : l('悪化', 'Worse');
            const names: Record<string, string> = { harmonic: l('倍音を含む音', 'Harmonic tone'), burst: l('短いノイズ', 'Noise burst'), chirp: l('周波数が変化する音', 'Chirp') };
            return <tr key={row.id || index}><td>{names[row.id] || row.name || row.id || `WAV ${index + 1}`}<small className="model-case-flags">{row.sample_rate_hz / 1000} kHz · {row.duration_seconds} s</small></td><td>{fmt(ln)} → {fmt(en)}</td><td>{fmt(ls)} → {fmt(es)}</td><td>NRMSE {metricChange(ln, en, false)}<br/>SI-SDR {metricChange(ls, es, true)}</td></tr>;
          })}</tbody></table></div>
        </div>}
        <details className="model-details"><summary>{l('分割・条件・評価記録の詳細', 'Splits, conditions and full evaluation record')}</summary><pre>{JSON.stringify(benchmark, null, 2)}</pre></details>
        <a className="button-link model-spaced" href={asset('/models/spatial-benchmark.json')} download><Download size={15}/>{l('評価記録 JSON', 'Evaluation record JSON')}</a>
      </> : <p role="status" className="neural-small">{benchmarkError ? l('評価記録を読み込めませんでした。評価結果は未確認です。', 'The evaluation record could not be loaded; its results are unverified.') : l('評価記録を読み込み中…', 'Loading the evaluation record…')}</p>}
    </section>

    <section className="panel model-max-guide">
      <div className="panel-head"><div><h2>{l('Maxでは、どんな音を送るか。', 'What should Max send?')}</h2><p>{l('まずWAVファイルで往復して、音源と復元結果を確認します。', 'Begin with a WAV-file workflow to inspect the source and reconstruction.')}</p></div><span>05 — MAX</span></div>
      <div className="model-max-path"><span>Max · {l('音源を作る', 'Create a source')}</span><ArrowRight size={15}/><span>{l('モノラルWAVで保存', 'Save a mono WAV')}</span><ArrowRight size={15}/><span>{l('このページの仮想マイクへ', 'Virtual array on this page')}</span><ArrowRight size={15}/><span>{l('FOAを保存して比較', 'Export and compare FOA')}</span></div>
      <div className="model-max-columns"><div><h3>{l('先に試す音', 'Start with these sounds')}</h3><p>{l('短い発話、音程のある音楽、広帯域ノイズ、短い打音。同じ素材を使い、ON / OFFの誤差と聴感を比較します。声に似た合成音だけで、実際の声への性能を判断しません。',
        'Short speech, pitched music, broadband noise and brief transients. Compare ON / OFF errors and listening with identical material. Speech-like synthesis alone does not establish performance on real speech.')}</p></div>
        <div><h3>{l('実際の空間を試すとき', 'For a real acoustic space')}</h3><p>{l('Maxからスピーカーへ再生し、マイクアレイで同期録音します。その録音と対応する応答VをZIPで入力します。再生したモノラル音源は、マイク位置での正解FOAにはなりません。',
          'Play from Max through the speakers and record with a synchronized microphone array. Import that recording with its matching response V as a ZIP. The mono playback source is not reference FOA at the microphone position.')}</p></div></div>
      <div className="note"><CircleHelp size={17}/><div>{l('これまでのMax連携はチャンネル選択・ミュート等の制御です。音声がWebへ自動送信される構成ではありません。新しいパッチも、保存したファイルで比較するための実験用です。スイープ・IRを学習モデルで加工して校正値に使わないでください。',
        'The existing Max bridge handles controls such as channel selection and mute. It does not automatically stream audio to the web. The new patch supports file-based experiments. Do not process sweeps or IRs through the learned model and use them as calibration measurements.')}</div></div>
      <a className="button-link model-spaced" href={asset('/examples/ADEPS_Max_Experiment.zip')} download><Download size={15}/>{l('Max実験パッチ一式を保存', 'Download the Max experiment patch')}</a>
    </section>
  </div>;
}
