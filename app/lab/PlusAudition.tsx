'use client';

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Download, ExternalLink, RotateCcw } from 'lucide-react';
import DiffusionScene from './DiffusionScene';
import { MicrophoneArrayView } from './MicrophoneArrayView';
import { directionalGrid, directionalRms } from './diffusionMath';
import { Plot, fmt } from './Plots';
import { asset } from './assets';
import type { FrequencyMetrics } from './SpectralComparison';
import './PlusAudition.css';

type Band = 'broadband' | 'low' | 'mid' | 'high';
type Estimate = {
  id: string; label_jp: string; label_en: string;
  covariance: Record<Band, number[][]>; preview_wav_base64: string;
  metrics: { nrmse_db: number | null; coherence: number | null; si_sdr_db: number | null };
  frequency_metrics: FrequencyMetrics;
};
type Example = {
  schema: 'adeps-plus-example/1'; scene_id: string; input_sha256?: string;
  archive_url?: string; inference_input_url?: string; inference_input_file_sha256?: string; inference_input_observation_sha256?: string;
  frequencies_hz: number[]; microphone_positions_m: number[][]; shared_gain: number;
  audio: { sample_rate_hz: number; duration_seconds: number; shared_gain?: number; attribution: {
    title: string; corpus: string; license: string; license_url: string; source_url: string;
    changes: string; speakers: string[]; files: string[];
  } };
  reference: Estimate; estimates: Estimate[];
};
type Props = { url: string; language: 'jp' | 'en'; active?: boolean };
type LoadState = { url: string; status: 'ready'; data: Example } | { url: string; status: 'loading' | 'missing' | 'invalid' | 'error' };
const BANDS: Band[] = ['broadband', 'low', 'mid', 'high'];
const DIRECTIONS = directionalGrid();
const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
const nullable = (n: unknown): n is number | null => n === null || finite(n);
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.length > 0;
const strings = (value: unknown): value is string[] => Array.isArray(value) && value.every(text);
const checksum = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value);
function downloadPath(value: unknown, extension: 'npz' | 'zip') {
  return typeof value === 'string' && new RegExp(`^models/[a-zA-Z0-9_-]+\\.${extension}$`).test(value) ? value : undefined;
}
function safeLink(value: unknown) {
  if (typeof value !== 'string') return undefined;
  try { const parsed = new URL(value); return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : undefined; }
  catch { return undefined; }
}
function matrix(value: unknown): value is number[][] {
  return Array.isArray(value) && value.length === 4 && value.every(row => Array.isArray(row) && row.length === 4 && row.every(finite));
}
function frequencyMetrics(value: unknown, grid: number[]): value is FrequencyMetrics {
  if (!record(value) || value.schema !== 'adeps-test-spectral-metrics/1' || value.channels !== 4
    || !Number.isInteger(value.frames) || (value.frames as number) < 1
    || !finite(value.magnitude_floor_absolute) || value.magnitude_floor_absolute < 0 || value.magnitude_floor_relative !== 1e-12
    || !Array.isArray(value.frequency_hz) || !value.frequency_hz.every((f, i) => f === grid[i]) || value.frequency_hz.length !== grid.length) return false;
  return ['magnitude_spectrum_error_db', 'magnitude_squared_coherence'].every((key, i) =>
    Array.isArray(value[key]) && value[key].length === grid.length
    && value[key].every((n: unknown) => n === null || (finite(n) && n >= 0 && (i === 0 || n <= 1))))
    && ['reference_active_channels', 'coherence_valid_channels', 'reference_below_floor_cells', 'estimate_below_floor_cells'].every((key, i) =>
      Array.isArray(value[key]) && value[key].length === grid.length
      && value[key].every((n: unknown) => finite(n) && Number.isInteger(n) && n >= 0 && n <= (i < 2 ? 4 : 4 * (value.frames as number))));
}
function estimate(value: unknown, grid: number[]): value is Estimate {
  if (!record(value) || !text(value.id) || !/^[a-z0-9_-]+$/.test(value.id) || !text(value.label_jp) || !text(value.label_en)
    || !record(value.covariance) || !record(value.metrics) || !frequencyMetrics(value.frequency_metrics, grid)
    || !text(value.preview_wav_base64) || value.preview_wav_base64.length > 20000000
    || !/^[A-Za-z0-9+/=\s]+$/.test(value.preview_wav_base64)) return false;
  return BANDS.every(band => matrix((value.covariance as Record<string, unknown>)[band]))
    && ['nrmse_db', 'coherence', 'si_sdr_db'].every(key => nullable((value.metrics as Record<string, unknown>)[key]))
    && (value.metrics.coherence === null || (finite(value.metrics.coherence) && value.metrics.coherence >= 0 && value.metrics.coherence <= 1));
}
function example(value: unknown): value is Example {
  if (!record(value) || value.schema !== 'adeps-plus-example/1' || !text(value.scene_id)
    || (value.input_sha256 !== undefined && !checksum(value.input_sha256))
    || (value.archive_url !== undefined && !downloadPath(value.archive_url, 'zip'))
    || !finite(value.shared_gain) || value.shared_gain <= 0 || !record(value.audio)
    || (value.audio.shared_gain !== undefined && value.audio.shared_gain !== value.shared_gain)
    || !finite(value.audio.sample_rate_hz) || value.audio.sample_rate_hz !== 16000
    || !finite(value.audio.duration_seconds) || value.audio.duration_seconds <= 0
    || !Array.isArray(value.frequencies_hz) || value.frequencies_hz.length !== 257
    || !value.frequencies_hz.every((f, i) => finite(f) && Math.abs(f - i * 31.25) < 1e-6)
    || !Array.isArray(value.microphone_positions_m) || value.microphone_positions_m.length < 1
    || !value.microphone_positions_m.every(row => Array.isArray(row) && row.length === 3 && row.every(finite))) return false;
  if ([value.inference_input_url, value.inference_input_file_sha256, value.inference_input_observation_sha256].some(field => field !== undefined)
    && (!downloadPath(value.inference_input_url, 'npz') || !checksum(value.inference_input_file_sha256)
      || !checksum(value.inference_input_observation_sha256) || value.inference_input_observation_sha256 !== value.input_sha256)) return false;
  const grid = value.frequencies_hz as number[], attribution = value.audio.attribution;
  if (!record(attribution) || !['title', 'corpus', 'license', 'changes'].every(key => text(attribution[key]))
    || !safeLink(attribution.license_url) || !safeLink(attribution.source_url) || !strings(attribution.speakers) || !strings(attribution.files)
    || !estimate(value.reference, grid) || !Array.isArray(value.estimates) || value.estimates.length < 2
    || !value.estimates.every(item => estimate(item, grid))) return false;
  const estimates = value.estimates as Estimate[];
  const all = [value.reference as Estimate, ...estimates], reference = all[0].frequency_metrics;
  return estimates.some(item => item.id === 'linear_tuned') && new Set(all.map(item => item.id)).size === all.length
    && all.every(item => item.frequency_metrics.frames === reference.frames
      && item.frequency_metrics.magnitude_floor_absolute === reference.magnitude_floor_absolute);
}

export default function PlusAudition({ url, language, active = true }: Props) {
  const jp = language === 'jp', l = (ja: string, en: string) => jp ? ja : en;
  const id = useId(), audio = useRef<HTMLAudioElement>(null);
  const [load, setLoad] = useState<LoadState>({ url: '', status: 'loading' });
  const [retry, setRetry] = useState(0), [method, setMethod] = useState('plus');
  const [enabled, setEnabled] = useState(true), [band, setBand] = useState<Band>('broadband');
  const [listenReference, setListenReference] = useState(false), [loop, setLoop] = useState(true);
  const [view, setView] = useState<'field' | 'array'>('field');
  const [frequency, setFrequency] = useState(1000), [audioError, setAudioError] = useState(false);
  const data = load.url === url && load.status === 'ready' ? load.data : null;
  const estimates = data?.estimates ?? [], linear = estimates.find(item => item.id === 'linear_tuned');
  const chosen = estimates.find(item => item.id === method && item.id !== 'linear_tuned')
    ?? estimates.find(item => item.id === 'plus') ?? estimates.find(item => item.id !== 'linear_tuned');
  const current = enabled ? chosen : linear;
  const listening = listenReference ? data?.reference : current;
  const source = listening ? `data:audio/wav;base64,${listening.preview_wav_base64}` : undefined;
  const name = (value: Estimate) => jp ? value.label_jp : value.label_en;
  const scale = useMemo(() => {
    if (!data) return 1;
    let maximum = 0;
    for (const item of [data.reference, ...data.estimates]) for (const b of BANDS) {
      for (const direction of DIRECTIONS) maximum = Math.max(maximum, directionalRms(item.covariance[b], direction));
    }
    return maximum > 0 && Number.isFinite(maximum) ? maximum : 1;
  }, [data]);

  useEffect(() => {
    const controller = new AbortController();
    // Loading is external state; URL identity also prevents displaying a previous example.
    // oxlint-disable-next-line react/react-compiler
    setLoad({ url, status: 'loading' });
    setMethod('plus'); setEnabled(true); setListenReference(false);
    if (!url) { setLoad({ url, status: 'missing' }); return () => controller.abort(); }
    void (async () => {
      try {
        const response = await fetch(url, { signal: controller.signal, cache: 'no-cache' });
        if (!response.ok) { if (!controller.signal.aborted) setLoad({ url, status: response.status === 404 ? 'missing' : 'error' }); return; }
        const value: unknown = await response.json();
        if (!controller.signal.aborted) setLoad(example(value) ? { url, status: 'ready', data: value } : { url, status: 'invalid' });
      } catch { if (!controller.signal.aborted) setLoad({ url, status: 'error' }); }
    })();
    return () => controller.abort();
  }, [url, retry]);
  useEffect(() => {
    const element = audio.current;
    element?.pause();
    // Audio remains stopped when switching methods, examples or tabs. Only native Play starts it.
    // oxlint-disable-next-line react/react-compiler
    setAudioError(false);
    return () => { element?.pause(); };
  }, [source, active]);

  function choose(value: string) { audio.current?.pause(); setMethod(value); setListenReference(false); }
  function toggle() { audio.current?.pause(); setEnabled(value => !value); setListenReference(false); }
  function downloadCsv() {
    if (!data) return;
    const all = data.estimates;
    const rows: (string | number | null)[][] = [['scene_id', 'frequency_hz', ...all.flatMap(item => [
      `${item.id}_magnitude_error_db`, `${item.id}_coherence`, `${item.id}_coherence_valid_channels`])],
      ...data.frequencies_hz.map((hz, i) => [data.scene_id, hz, ...all.flatMap(item => [
        item.frequency_metrics.magnitude_spectrum_error_db[i], item.frequency_metrics.magnitude_squared_coherence[i],
        item.frequency_metrics.coherence_valid_channels[i]])])];
    const csvCell = (cell: string | number | null) => {
      if (cell === null) return '';
      const value = typeof cell === 'string' && /^[=+\-@\t\r]/.test(cell) ? `'${cell}` : String(cell);
      return `"${value.replaceAll('"', '""')}"`;
    };
    const csv = '\uFEFF' + rows.map(row => row.map(csvCell).join(',')).join('\r\n');
    const href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = href; link.download = `ADEPS-plus_${data.scene_id.replace(/[^\w-]/g, '_')}_frequencies.csv`;
    link.click(); setTimeout(() => URL.revokeObjectURL(href), 1000);
  }

  const state = load.url === url ? load.status : 'loading';
  if (!data || !linear || !chosen || !current) return <section className="plus-audition pla-empty" aria-label={l('音と形で比較', 'Compare sound and shape')}>
    <span className="pla-eyebrow">LISTEN / COMPARE</span><h3>{l('同じ入力で、音と形を比較', 'Compare sound and shape from the same input')}</h3>
    <output className="pla-status">{state === 'loading' ? l('計算済みの比較例を読み込んでいます。', 'Loading the computed comparison example.')
      : state === 'missing' ? l('この比較例はまだ公開されていないか、取得できません。生成されたデータが揃うと表示できます。', 'This comparison example is not published or cannot be found. It will appear when the generated data is available.')
      : state === 'invalid' ? l('比較例のデータ形式が一致しません。現在の形式で生成された例が必要です。', 'The example does not match the expected data format. An example generated with the current format is required.')
      : l('比較例を読み込めませんでした。', 'The comparison example could not be loaded.')}</output>
    {state !== 'loading' && <button type="button" onClick={() => setRetry(value => value + 1)}><RotateCcw size={13}/>{l('再読み込み', 'Retry')}</button>}
  </section>;

  const baseline = linear.frequency_metrics, selected = chosen.frequency_metrics;
  const index = data.frequencies_hz.reduce((best, value, i) => Math.abs(value - frequency) < Math.abs(data.frequencies_hz[best] - frequency) ? i : best, 0);
  const maxError = Math.max(1, ...data.estimates.flatMap(item => item.frequency_metrics.magnitude_spectrum_error_db.filter((n): n is number => n !== null))) * 1.06;
  const attribution = data.audio.attribution;
  return <section className="plus-audition" aria-label={l('音と形で比較', 'Compare sound and shape')}>
    <header className="pla-heading"><span className="pla-eyebrow">LISTEN / COMPARE · {data.scene_id}</span>
      <h3>{l('同じ入力で、音と形を比較', 'Compare sound and shape from the same input')}</h3>
      <p>{l('計算済みの同じ音声を切り替えます。ONは選択した方式、OFFは調整済みLinearです。新しい推論や現場録音は、この切り替えでは実行しません。',
        'Switch between computed results for the same audio. ON uses the selected method; OFF uses tuned Linear. Switching does not run new inference or record a room.')}</p></header>
    <div className="pla-controls"><label htmlFor={`${id}-method`}>{l('比較する方式', 'Comparison method')}<select id={`${id}-method`} value={chosen.id} onChange={event => choose(event.target.value)}>
      {estimates.filter(item => item.id !== 'linear_tuned').map(item => <option key={item.id} value={item.id}>{name(item)}</option>)}</select></label>
      <button type="button" className="pla-switch" role="switch" aria-checked={enabled} onClick={toggle} aria-label={l('選択方式をON / OFF', 'Turn selected method ON / OFF')}>{enabled ? 'ON' : 'OFF'}<small>{enabled ? name(chosen) : name(linear)}</small></button>
    </div>
    <div className="pla-view-options"><fieldset aria-label={l('表示対象', 'View')}><button type="button" aria-pressed={view === 'field'} onClick={() => setView('field')}>{l('方向別の強さ', 'Directional strength')}</button>
      <button type="button" aria-pressed={view === 'array'} onClick={() => setView('array')}>{l('仮想マイク配置', 'Virtual microphone array')}</button></fieldset>
      <label htmlFor={`${id}-band`}>{l('表示帯域', 'Display band')}<select id={`${id}-band`} value={band} onChange={event => setBand(event.target.value as Band)}>
        {BANDS.map((b, i) => <option key={b} value={b}>{l(['広帯域 · 31.25 Hz–8 kHz', '低域 · 31.25–468.75 Hz', '中域 · 500–1968.75 Hz', '高域 · 2–8 kHz'][i], ['Broadband · 31.25 Hz–8 kHz', 'Low · 31.25–468.75 Hz', 'Mid · 500–1968.75 Hz', 'High · 2–8 kHz'][i])}</option>)}</select></label></div>
    {active && (view === 'field' ? <DiffusionScene covariance={current.covariance[band]} referenceCovariance={data.reference.covariance[band]}
      comparisonCovariance={enabled ? linear.covariance[band] : chosen.covariance[band]} microphonePositions={data.microphone_positions_m} language={language} commonScale={scale}/>
      : <MicrophoneArrayView positions={data.microphone_positions_m} language={language} label={l('共通の仮想マイク配置', 'Shared virtual microphone array')}
        caption={l('この例の観測生成に使った座標。+X＝前、+Y＝左、+Z＝上。実機を測った座標ではありません。', 'Coordinates used to synthesize this example’s observations. +X front, +Y left, +Z up. These are not measured hardware positions.')}/>)}
    <p className="pla-note">{l('面', 'Surface')}: {name(current)} · {l('実線', 'Solid wire')}: {name(data.reference)} · {l('破線', 'Dashed wire')}: {name(enabled ? linear : chosen)}<br/>
      {l('全方式・全帯域で同じ縮尺の、FOA共分散に基づく相対的な方向別RMSです。部屋の音圧分布や現場の性能を示す図ではありません。', 'Relative directional RMS from FOA covariance, with one scale across all methods and bands. This is not a room-pressure map or evidence of performance in a venue.')}{' '}
      {l('3Dの帯域平均はDCを除きます。全帯域NRMSEと周波数の詳細表はDCを含みます。', 'The 3D band averages exclude DC. Full-band NRMSE and the frequency-detail table include DC.')}</p>
    <div className="pla-listen"><div className="pla-listen-controls"><label htmlFor={`${id}-audio`}>{l('試聴する音', 'Audio to audition')}<select id={`${id}-audio`} value={listenReference ? 'reference' : 'current'} onChange={event => { audio.current?.pause(); setListenReference(event.target.value === 'reference'); }}>
      <option value="current">{name(current)}</option><option value="reference">{name(data.reference)}</option></select></label>
      <label className="pla-checkbox"><input type="checkbox" checked={loop} onChange={event => setLoop(event.target.checked)}/>{l('繰り返す', 'Loop')}</label></div>
      {/* No verified transcript accompanies the reconstructed audio; the metrics and shape are available as text. */}
      {/* oxlint-disable-next-line jsx-a11y/media-has-caption */}
      {active && <audio ref={audio} controls preload="none" loop={loop} src={source} onError={() => setAudioError(true)} aria-label={`${l('試聴', 'Audition')}: ${listening ? name(listening) : ''}`}/>}
      {audioError && <p role="alert">{l('この音声を再生できませんでした。', 'This audio could not be played.')}</p>}
      <p>{l('再生ボタンを押すと音が出ます。切り替え時は停止します。±45°の仮想カーディオイドによるステレオ試聴で、HRTFやスピーカー出力ではありません。',
        'Press Play to hear audio. Switching stops playback. This is stereo from virtual cardioids at ±45°, without HRTFs or loudspeaker feeds.')}{' '}
        {l('3Dの視点や表示帯域を変えても、試聴音は変わりません。', 'Changing the 3D view or display band does not change the audio.')}<br/>
        {data.audio.sample_rate_hz / 1000} kHz · {fmt(data.audio.duration_seconds, 3)} s · {l('全方式共通の出力ゲイン', 'Shared output gain for every method')}: {data.shared_gain.toPrecision(5)}</p></div>
    <div className="pla-table-wrap"><table><caption>{l('この1例のFOA 4chに対する値。—は未定義で、0ではありません。', 'Metrics for this example’s four FOA channels. A dash is undefined, not zero.')}</caption>
      <thead><tr><th>{l('方式', 'Method')}</th><th>NRMSE dB ↓</th><th>Coherence ↑</th><th>SI-SDR dB ↑</th></tr></thead><tbody>
        {estimates.map(item => <tr key={item.id} data-current={item.id === current.id}><th scope="row">{name(item)}{item.id === current.id && <small>{l('表示中', 'Shown')}</small>}</th>
          <td>{fmt(item.metrics.nrmse_db, 3)}</td><td>{fmt(item.metrics.coherence, 4)}</td><td>{fmt(item.metrics.si_sdr_db, 3)}</td></tr>)}</tbody></table></div>
    <div className="pla-spectral"><h4>{l('周波数ごとの比較', 'Comparison by frequency')} · {name(chosen)}</h4>
      <p>{l('ON/OFFによらず、選択方式と調整済みLinearの2本を比較します。計算データは0–8 kHz。1 Hz–20 kHzの表示軸のうち未計算の帯域は空白で、DCは詳細表に残します。',
        'These two curves compare the selected method with tuned Linear regardless of ON/OFF. Data spans 0–8 kHz. Uncomputed bands on the 1 Hz–20 kHz axis remain blank; DC is retained in the table.')}</p>
      <p>{l('参照が非常に弱い周波数では相対誤差が大きくなることがあります。このdB値は音量やSPLではありません。', 'Relative error can be large where the reference is very weak. These dB values are not loudness or SPL.')}</p>
      <Plot x={data.frequencies_hz} frequency yDomain={[0, maxError]} unit="dB" label={l('振幅スペクトル誤差・小さいほど良い', 'Magnitude spectrum error · lower is better')}
        series={[{ name: name(linear), values: baseline.magnitude_spectrum_error_db, color: '#999', dash: '7 5' }, { name: name(chosen), values: selected.magnitude_spectrum_error_db, color: '#f2f2f2' }]}/>
      <Plot x={data.frequencies_hz} frequency yDomain={[0, 1]} unit="MSC" label={l('二乗コヒーレンス・1に近いほど良い', 'Magnitude-squared coherence · closer to 1 is better')}
        series={[{ name: name(linear), values: baseline.magnitude_squared_coherence, color: '#999', dash: '7 5' }, { name: name(chosen), values: selected.magnitude_squared_coherence, color: '#f2f2f2' }]}/>
      <label className="pla-frequency" htmlFor={`${id}-frequency`}>{l('周波数の値を見る', 'Inspect a frequency')}<select id={`${id}-frequency`} value={data.frequencies_hz[index]} onChange={event => setFrequency(Number(event.target.value))}>
        {data.frequencies_hz.map(hz => <option key={hz} value={hz}>{hz} Hz{hz === 0 ? ' · DC' : ''}</option>)}</select></label>
      <div className="pla-table-wrap"><table><caption>{data.frequencies_hz[index]} Hz</caption><thead><tr><th>{l('方式', 'Method')}</th><th>{l('振幅誤差 dB', 'Magnitude error dB')}</th><th>Coherence</th><th>{l('有効ch', 'Valid ch')}</th></tr></thead>
        <tbody>{[linear, chosen].map(item => <tr key={item.id}><th>{name(item)}</th><td>{fmt(item.frequency_metrics.magnitude_spectrum_error_db[index], 4)}</td><td>{fmt(item.frequency_metrics.magnitude_squared_coherence[index], 5)}</td><td>{item.frequency_metrics.coherence_valid_channels[index]}/4</td></tr>)}</tbody></table></div>
      <button type="button" onClick={downloadCsv}><Download size={13}/>{l('全方式・全周波数をCSV保存', 'Save every method and frequency as CSV')}</button>
      <details><summary>{l('指標の計算方法と引用', 'Metric definitions and references')}</summary>
        <p>{l('振幅誤差は各周波数で |20 log₁₀(|参照|/|推定|)| を時間×4ch平均。Coherenceは時間方向のcross-powerからchごとに求めた二乗値の平均です。同じ参照・同じ振幅床を使い、未定義は欠損として表示します。Coherence単独で方向や音場の正しさは保証できません。',
          'Magnitude error averages |20 log₁₀(|reference|/|estimate|)| over time × four channels at each frequency. Coherence averages channel-wise magnitude-squared cross-power over time. All methods share the reference and magnitude floor; undefined values remain missing. Coherence alone cannot establish spatial accuracy.')}</p>
        <p>ε = {baseline.magnitude_floor_absolute.toExponential(5)} · {baseline.frames} {l('フレーム', 'frames')} · {l('参照の有効ch', 'Active reference ch')}: {baseline.reference_active_channels[index]}/4</p>
        <a href="https://arxiv.org/html/2501.08047v1#S3.SS4" target="_blank" rel="noreferrer">Gen-A · Eqs. (5), (6)<ExternalLink size={12}/></a>
        <p>{l('1例の合成データに対する比較です。最終テスト全体の集計や、実空間での性能証明とは異なります。', 'This compares one synthetic example. It is separate from the aggregate final-test evaluation and does not establish real-room performance.')}</p>
      </details></div>
    <details className="pla-attribution"><summary>{l('音源の出典とデータの識別', 'Audio attribution and data identity')}</summary><p>{attribution.title} · {attribution.corpus}</p>
      <p>{attribution.changes}</p><p>{l('話者', 'Speakers')}: {attribution.speakers.join(', ')}<br/>{l('使用ファイル', 'Files')}: {attribution.files.join(', ')}</p>
      <a href={safeLink(attribution.source_url)} target="_blank" rel="noreferrer">{l('元データ', 'Source dataset')}<ExternalLink size={12}/></a>
      <a href={safeLink(attribution.license_url)} target="_blank" rel="noreferrer">{attribution.license}<ExternalLink size={12}/></a>
      {data.archive_url && <a href={asset(data.archive_url)} download><Download size={12}/>{l('全方式の音声・記録ZIP', 'Audio and records for all methods')}</a>}
      {data.inference_input_url && <a href={asset(data.inference_input_url)} download><Download size={12}/>{l('この例を再計算する入力NPZ', 'Input NPZ to recompute this example')}</a>}
      <p>{l('観測p・V・周波数の識別', 'Identity of observations p, V and frequencies')}: {data.input_sha256 ?? data.scene_id}</p>
      {data.inference_input_file_sha256 && <p>{l('入力NPZのファイルSHA256', 'Input NPZ file SHA256')}: {data.inference_input_file_sha256}<br/>{l('推論用NPZには、正解係数や正解の音源方向を含みません。', 'The inference NPZ contains no target coefficients or oracle source directions.')}</p>}</details>
  </section>;
}
