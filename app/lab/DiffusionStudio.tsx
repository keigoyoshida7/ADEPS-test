import { useEffect, useMemo, useRef, useState } from 'react';
import { Download, LoaderCircle, Play, Shuffle, Trash2 } from 'lucide-react';
import { useLanguage } from './i18n';
import { analysisApi, isLocalEngine, onAnalysisProgress, type AnalysisProgress } from './scientificClient';
import DiffusionScene from './DiffusionScene';
import MicrophoneArrayView from './MicrophoneArrayView';
import NoiseScheduleView from './NoiseScheduleView';
import PaperTraining, { validTrainingReport, type TrainingReport } from './PaperTraining';
import ProcessAudition from './ProcessAudition';
import SpectralComparison, { type SpectralEstimate } from './SpectralComparison';
import { noiseSchedule, fromNoiseTrace } from './noiseSchedule';
import { virtualArrayPositions } from './arrayGeometry';
import { asset } from './assets';
import { Plot, fmt } from './Plots';
import './DiffusionStudio.css';

type Band = 'broadband' | 'low' | 'mid' | 'high';
type Covariance = Record<Band, number[][]>;
type Metrics = { nrmse_db?: number | null; coherence?: number | null; encoded_residual?: number | null; si_sdr_db?: number | null;
  coherence_status?: string; coherence_valid_frequency_bins?: number; coherence_reference_active_frequency_bins?: number };
type Estimate = { id: string; label: string; stage: string; step: number; sigma: number; covariance: Covariance; preview_wav_base64: string; metrics: Metrics; frequency_metrics?: SpectralEstimate['frequency_metrics'] };
type Configuration = { microphones: number; radius_m: number; geometry: 'sphere' | 'ring'; snr_db: number; observation_seed: number; seed: number; eta_prime: number; steps: number };
type Attribution = { title: string; corpus: string; speakers: string[]; files: string[]; license: string; license_url: string; source_url: string; changes: string };
type StudioResult = {
  configuration: Configuration & { sigma_max: number; sigma_min: number; rho: number }; input_sha256: string; microphone_positions_m: number[][];
  source_directions: { id: string; direction: number[] }[];
  reference: Estimate; linear: Estimate; checkpoints: Estimate[];
  trace: { step: number; sigma: number; next_sigma: number; encoded_residual: number }[];
  audio: { shared_gain: number; sample_rate_hz?: number; n_fft?: number; hop?: number; duration_seconds?: number; attribution?: Attribution; [key: string]: unknown };
  frequencies_hz?: number[]; model: Record<string, unknown>; bytes?: ArrayBuffer; filename: string; savedExample?: boolean; archiveUrl?: string;
  example_provenance?: { split: string; scene_index: number; manifest_sha256: string };
  scaling_diagnostic?: Record<string, unknown>;
};
type Run = { id: number; created: string; result: StudioResult };
const defaults: Configuration = { microphones: 6, radius_m: .06, geometry: 'sphere', snr_db: 50, observation_seed: 173927, seed: 42, eta_prime: 50, steps: 150 };
const zero = Array.from({ length: 4 }, () => [0, 0, 0, 0]);
const rmsBound = (matrix: number[][]) => 2 * Math.sqrt(Math.max(0, matrix.reduce((sum, row, i) => sum + row[i], 0)));
const originalCovariance = (estimate: Estimate | undefined, band: Band, gain = 1) =>
  estimate?.covariance[band].map(row => row.map(value => value / (gain * gain))) ?? zero;
const PAPER_EXAMPLES = [
  { id: 'example', label: 'A', seed: 42, eta_prime: 50 },
  { id: 'seed43', label: 'B', seed: 43, eta_prime: 50 },
  { id: 'eta0', label: 'C', seed: 42, eta_prime: 0 },
] as const;
type PaperExampleId = typeof PAPER_EXAMPLES[number]['id'];
const paperExampleConfiguration = (example: typeof PAPER_EXAMPLES[number]): Configuration => ({ ...defaults, seed: example.seed, eta_prime: example.eta_prime });
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const vector3 = (value: unknown): value is number[] => Array.isArray(value) && value.length === 3 && value.every(finite);
const hash = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const modelText = (model: Record<string, unknown>, key: string) => typeof model[key] === 'string' ? model[key] : '';
function validExample(value: unknown, weightsSha: string): value is StudioResult {
  if (!value || typeof value !== 'object') return false;
  const r = value as StudioResult;
  if (!r.model || r.model.id !== 'paper-prior-v1' || r.model.weights_sha256 !== weightsSha || !hash(r.input_sha256)
    || !r.configuration || !r.audio || !finite(r.audio.shared_gain) || r.audio.shared_gain <= 0 || r.audio.shared_gain > 1
    || !Array.isArray(r.microphone_positions_m) || r.microphone_positions_m.length !== r.configuration.microphones || !r.microphone_positions_m.every(vector3)
    || !Array.isArray(r.source_directions) || !r.source_directions.every(source => source && vector3(source.direction))
    || !Array.isArray(r.checkpoints) || r.checkpoints.length < 1
    || !Array.isArray(r.trace) || fromNoiseTrace(r.trace).length !== r.configuration.steps + 1
    || !Array.isArray(r.frequencies_hz) || !r.frequencies_hz.length || !r.frequencies_hz.every((f, i) => finite(f) && f >= 0 && (i === 0 || f > r.frequencies_hz![i - 1]))) return false;
  const cfg = r.configuration;
  if (!Object.keys(defaults).every(key => key === 'geometry' ? ['sphere', 'ring'].includes(cfg.geometry) : finite(cfg[key as keyof Configuration]))
    || !finite(cfg.sigma_max) || !finite(cfg.sigma_min) || !finite(cfg.rho)) return false;
  const complete = r.checkpoints.at(-1);
  if (complete?.stage !== 'final_sample' || complete.step !== cfg.steps || complete.sigma !== 0) return false;
  const estimates = [r.reference, r.linear, ...r.checkpoints];
  if (!estimates.every(estimate => estimate && typeof estimate.id === 'string' && typeof estimate.stage === 'string'
    && typeof estimate.preview_wav_base64 === 'string' && estimate.preview_wav_base64.startsWith('UklGR') && estimate.metrics && estimate.covariance
    && (['broadband', 'low', 'mid', 'high'] as Band[]).every(band => {
      const matrix = estimate.covariance[band];
      return Array.isArray(matrix) && matrix.length === 4 && matrix.every(row => Array.isArray(row) && row.length === 4 && row.every(finite));
    }))) return false;
  const credit = r.audio.attribution;
  return !!credit && [credit.title, credit.corpus, credit.license, credit.license_url, credit.source_url, credit.changes].every(text => typeof text === 'string')
    && Array.isArray(credit.speakers) && credit.speakers.every(s => typeof s === 'string')
    && Array.isArray(credit.files) && credit.files.every(s => typeof s === 'string')
    && credit.license_url.startsWith('https://') && credit.source_url.startsWith('https://');
}

export default function DiffusionStudio({ active = true }: { active?: boolean }) {
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [config, setConfig] = useState(defaults);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedId, setSelectedId] = useState<number>();
  const [stepIndex, setStepIndex] = useState(0);
  const [enabled, setEnabled] = useState(true);
  const [band, setBand] = useState<Band>('broadband');
  const [spatialView, setSpatialView] = useState<'array' | 'soundfield' | 'schedule'>(() =>
    new URLSearchParams(window.location.search).get('view') === 'schedule' ? 'schedule' : 'array');
  const [arraySource, setArraySource] = useState<'settings' | 'run'>('settings');
  const [scheduleSource, setScheduleSource] = useState<'settings' | 'run'>('settings');
  const [overlay, setOverlay] = useState<'reference' | 'linear' | 'previous' | 'none'>('reference');
  const [sharedScale, setSharedScale] = useState(true);
  const [busy, setBusy] = useState(false);
  const [exampleBusy, setExampleBusy] = useState(false);
  const [exampleId, setExampleId] = useState<PaperExampleId>('example');
  const [exampleError, setExampleError] = useState('');
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [modelRecord, setModelRecord] = useState<TrainingReport>();
  const modelReady = modelRecord?.status === 'evaluated' && hash(modelRecord.model.weights_sha256);
  const [progress, setProgress] = useState<AnalysisProgress>();
  const [error, setError] = useState('');
  const [loop, setLoop] = useState(false);
  const [listening, setListening] = useState<'selected' | 'reference'>('selected');
  const [auditionStopToken, setAuditionStopToken] = useState(0);
  const stopProcess = () => setAuditionStopToken(token => token + 1);
  const audioRef = useRef<HTMLAudioElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const counter = useRef(0);
  const operationBusy = useRef(false);
  const run = runs.find(item => item.id === selectedId) ?? runs.at(-1);
  const result = run?.result;
  const modelId = typeof result?.model.id === 'string' ? result.model.id : 'paper-prior-v1';
  const modelParameters = result?.model.parameters ?? result?.model.parameter_count;
  const attribution = result?.audio.attribution;
  const previewPositions = useMemo(() => virtualArrayPositions(config.microphones, config.radius_m, config.geometry), [config.microphones, config.radius_m, config.geometry]);
  const savedArray = arraySource === 'run' && !!result;
  const arrayPositions = savedArray ? result.microphone_positions_m : previewPositions;
  const arrayConfig = savedArray ? result.configuration : config;
  const plannedSchedule = useMemo(() => noiseSchedule(config.steps), [config.steps]);
  const savedTrace = result?.trace;
  // oxlint-disable-next-line react/react-compiler -- Saved runs are never mutated; retain stable chart data despite async audio-buffer escape analysis.
  const savedSchedule = useMemo(() => savedTrace ? fromNoiseTrace(savedTrace) : [], [savedTrace]);
  const showingSavedSchedule = scheduleSource === 'run' && !!result;
  const checkpoint = result?.checkpoints[Math.min(stepIndex, result.checkpoints.length - 1)];
  const estimate = enabled ? checkpoint : result?.linear;
  const selectedNrmse = estimate?.metrics.nrmse_db;
  const linearNrmse = result?.linear.metrics.nrmse_db;
  const nrmseImprovement = finite(selectedNrmse) && finite(linearNrmse) ? linearNrmse - selectedNrmse : undefined;
  const previous = runs.filter(item => item.id !== run?.id && item.result.input_sha256 === result?.input_sha256).at(-1);
  const compare = overlay === 'reference' ? result?.reference : overlay === 'linear' ? result?.linear : overlay === 'previous' ? previous?.result.checkpoints.at(-1) : undefined;
  const preview = listening === 'reference' ? result?.reference : estimate;
  const audioUrl = preview ? `data:audio/wav;base64,${preview.preview_wav_base64}` : undefined;
  const commonAudioGain = result ? Math.min(...runs.filter(item => item.result.input_sha256 === result.input_sha256).map(item => item.result.audio.shared_gain as number)) : 1;
  const previewLevel = result ? Math.min(1, commonAudioGain / result.audio.shared_gain) : 1;
  useEffect(() => { if (audioRef.current) audioRef.current.volume = previewLevel; }, [audioUrl, previewLevel]);
  const selectedGain = result?.audio.shared_gain;
  // oxlint-disable-next-line react/react-compiler -- Saved covariances are read-only; stable references prevent unnecessary WebGL scene resets.
  const currentCovariance = useMemo(() => originalCovariance(estimate, band, selectedGain), [estimate, band, selectedGain]);
  const compareResult = overlay === 'previous' ? previous?.result : result;
  // oxlint-disable-next-line react/react-compiler -- Saved covariances are read-only; stable references prevent unnecessary WebGL scene resets.
  const compareCovariance = useMemo(() => compare ? originalCovariance(compare, band, compareResult?.audio.shared_gain) : undefined, [compare, band, compareResult]);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    const read = async () => {
      try {
        const response = await fetch(asset('/models/paper-prior-training.json'), { cache: 'no-store', signal: controller.signal });
        const record: unknown = response.ok ? await response.json() : undefined;
        if (!controller.signal.aborted) setModelRecord(validTrainingReport(record) ? record : undefined);
      } catch { if (!controller.signal.aborted) setModelRecord(undefined); }
    };
    void read();
    const timer = window.setInterval(() => { void read(); }, 30000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [active]);
  useEffect(() => onAnalysisProgress(setProgress), []);
  useEffect(() => { if (!active) audioRef.current?.pause(); }, [active]);
  const selectedInputHash = result?.input_sha256;
  const scale = useMemo(() => {
    if (!selectedInputHash || !sharedScale) return undefined;
    const same = runs.filter(item => item.result.input_sha256 === selectedInputHash);
    return Math.max(1e-12, ...same.flatMap(item => [item.result.reference, item.result.linear, ...item.result.checkpoints].map(point => rmsBound(originalCovariance(point, band, item.result.audio.shared_gain)))));
  }, [runs, selectedInputHash, band, sharedScale]);
  const changed = result && Object.entries(config).some(([key, value]) => value !== result.configuration[key as keyof Configuration]);
  const frequencies = result?.frequencies_hz ?? [];
  const bandRange = (min: number, max: number, inclusive = false) => {
    const values = frequencies.filter(f => f >= min && (inclusive ? f <= max : f < max));
    const hz = (value: number) => value >= 1000 ? `${Number((value / 1000).toFixed(3))} kHz` : `${Number(value.toFixed(3))} Hz`;
    return values.length ? ` · ${hz(values[0])}–${hz(values.at(-1)!)}` : '';
  };
  const bandNames: Record<Band, string> = {
    broadband: l('全帯域', 'Broadband') + bandRange(20, 8000, true), low: l('低域', 'Low') + bandRange(20, 500), mid: l('中域', 'Mid') + bandRange(500, 2000), high: l('高域', 'High') + bandRange(2000, 8000, true),
  };
  const set = (key: keyof Configuration, value: number | string) => {
    setConfig(c => ({ ...c, [key]: value }));
    if (key === 'microphones' || key === 'radius_m' || key === 'geometry') {
      setArraySource('settings'); setSpatialView('array');
    }
    if (key === 'steps') { setScheduleSource('settings'); setSpatialView('schedule'); }
  };
  async function reconstruct(next = config) {
    if (operationBusy.current || busy || !isLocalEngine) return;
    operationBusy.current = true;
    stopProcess();
    setBusy(true); setError(''); setProgress(undefined); audioRef.current?.pause();
    try {
      const recordResponse = await fetch(asset('/models/paper-prior-training.json'), { cache: 'no-store' });
      const record: unknown = recordResponse.ok ? await recordResponse.json() : undefined;
      if (!validTrainingReport(record) || record.status !== 'evaluated' || !hash(record.model.weights_sha256)) {
        throw new Error(l('評価済みチェックポイントの学習記録を確認できません。記録とローカル環境を確認してください。', 'The training record for an evaluated checkpoint is unavailable. Check the record and local environment.'));
      }
      const response: unknown = await analysisApi('paper-studio', next);
      if (!validExample(response, record.model.weights_sha256) || response.model.parameters !== record.model.parameters) {
        throw new Error(l('復元結果と学習記録のモデル・重み・データ形式が一致しません。結果は読み込んでいません。', 'The reconstruction does not match the training record’s model, checkpoint or data format. The result was not loaded.'));
      }
      setModelRecord(record);
      const id = ++counter.current;
      setRuns(items => [...items, { id, created: new Date().toLocaleTimeString(), result: response }].slice(-6));
      setSelectedId(id); setStepIndex(response.checkpoints.length - 1); setEnabled(true); setListening('selected');
      setArraySource('run'); setSpatialView('soundfield');
      setScheduleSource('run');
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { operationBusy.current = false; setBusy(false); }
  }
  async function loadPaperExample(expectedWeightsSha?: string) {
    if (operationBusy.current || busy) return;
    operationBusy.current = true;
    const example = PAPER_EXAMPLES.find(item => item.id === exampleId)!;
    const expectedConfig = paperExampleConfiguration(example);
    const exampleBase = `/models/paper-prior-${example.id}`;
    stopProcess(); audioRef.current?.pause();
    setBusy(true); setExampleBusy(true); setExampleError('');
    try {
      const [recordResponse, exampleResponse] = await Promise.all([
        fetch(asset('/models/paper-prior-training.json'), { cache: 'no-store' }),
        fetch(asset(`${exampleBase}.json`), { cache: 'no-store' }),
      ]);
      if (!recordResponse.ok || !exampleResponse.ok) throw new Error(l('新モデルの計算済み例を読み込めませんでした。公開ファイルがまだ揃っていない可能性があります。', 'The computed example could not be loaded. Its published files may not be ready yet.'));
      const record = await recordResponse.json();
      const candidate: unknown = await exampleResponse.json();
      if (!validTrainingReport(record) || record.status !== 'evaluated' || record.model.id !== 'paper-prior-v1'
        || !hash(record.model.weights_sha256) || (expectedWeightsSha !== undefined && record.model.weights_sha256 !== expectedWeightsSha) || !validExample(candidate, record.model.weights_sha256)) {
        throw new Error(l('計算済み例と学習記録の重み・データ形式が一致しません。学習記録を再読込してください。', 'The example and training record do not match in checkpoint or data format. Reload the training record.'));
      }
      if (candidate.model.parameters !== record.model.parameters) throw new Error(l('計算例と学習記録のモデル構造が一致しません。', 'The example and training record disagree on model size.'));
      const provenance = candidate.example_provenance;
      const expectedPositions = virtualArrayPositions(expectedConfig.microphones, expectedConfig.radius_m, expectedConfig.geometry);
      const knownExample = runs.find(item => item.result.savedExample && item.result.model.weights_sha256 === record.model.weights_sha256);
      if (Object.entries(expectedConfig).some(([key, value]) => candidate.configuration[key as keyof Configuration] !== value)
        || provenance?.split !== 'test' || provenance.scene_index !== 0 || provenance.manifest_sha256 !== record.data.manifest_sha256
        || candidate.audio.sample_rate_hz !== record.configuration.sample_rate_hz || candidate.audio.n_fft !== record.configuration.n_fft || candidate.audio.hop !== record.configuration.hop
        || candidate.microphone_positions_m.some((position, channel) => position.some((value, axis) => Math.abs(value - expectedPositions[channel][axis]) > 1e-12))
        || (knownExample && candidate.input_sha256 !== knownExample.result.input_sha256)) {
        throw new Error(l('選択例のseed・拘束・ステップ数、または共通の観測条件が一致しません。この例は読み込んでいません。', 'The selected example has a different seed, guidance, step count or shared observation. It was not loaded.'));
      }
      setModelRecord(record);
      const response: StudioResult = { ...candidate, savedExample: true, archiveUrl: asset(`${exampleBase}.zip`), filename: `ADEPS_paper-prior-v1_${example.id}_seed-${example.seed}_eta-${example.eta_prime}.zip` };
      const id = ++counter.current;
      setRuns(items => [...items, { id, created: new Date().toLocaleTimeString(), result: response }].slice(-6));
      setSelectedId(id); setStepIndex(response.checkpoints.length - 1); setEnabled(true); setListening('selected');
      setArraySource('run'); setScheduleSource('run'); setSpatialView('soundfield');
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) { setExampleError(e instanceof Error ? e.message : String(e)); }
    finally { operationBusy.current = false; setBusy(false); setExampleBusy(false); }
  }
  function newCandidate() {
    const next = { ...config, seed: (config.seed + 1) >>> 0 };
    setConfig(next); void reconstruct(next);
  }
  function selectRun(item: Run) {
    stopProcess();
    setSelectedId(item.id); setStepIndex(item.result.checkpoints.length - 1); setListening('selected');
    setArraySource('run'); setScheduleSource('run');
  }
  async function download() {
    if (!result) return;
    setDownloadBusy(true); setError('');
    try {
      let bytes = result.bytes;
      if (!bytes && result.archiveUrl) {
        const response = await fetch(result.archiveUrl, { cache: 'no-store' });
        if (!response.ok) throw new Error(l('この計算例のZIPを取得できませんでした。', 'The example ZIP could not be downloaded.'));
        bytes = await response.arrayBuffer();
      }
      if (!bytes) throw new Error(l('保存する音声データがありません。', 'No audio archive is available.'));
      const url = URL.createObjectURL(new Blob([bytes], { type: 'application/zip' }));
      const a = document.createElement('a'); a.href = url; a.download = result.savedExample ? result.filename : `${modelId}_run-${run!.id}_seed-${result.configuration.seed}.zip`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setDownloadBusy(false); }
  }
  const configField = (key: keyof Configuration, label: string, min: number, max: number, step = 1) => (
    <label className="ds-field"><span>{label}</span><input type="number" value={config[key]} min={min} max={max} step={step}
      onChange={e => set(key, Number(e.target.value))} required /></label>
  );
  const progressText = exampleBusy ? l('新モデルの計算済み音声例を読み込んでいます', 'Loading the new model’s computed audio example') : progress?.stage === 'inference'
    ? `${l('復元中', 'Reconstructing')} ${progress.step ?? 0} / ${progress.total ?? config.steps}`
    : l('計算データを準備しています', 'Preparing the computation');

  return <section className="diffusion-studio" aria-label={l('拡散・音場スタジオ', 'Diffusion soundfield studio')}>
    <div className="ds-intro"><span className="eyebrow">DIFFUSION / LISTEN · OBSERVE · COMPARE</span>
      <h2>{l('ひとつの観測、いくつもの復元。', 'One observation. Many reconstructions.')}</h2>
      <p>{l('音声と合成室内応答から作った仮想マイクの観測を、学習済みの時間・周波数モデルで復元します。線形推定と切り替え、途中の推定と最終結果を聴いて比較できます。', 'Reconstruct virtual microphone observations generated from speech and simulated room responses with a trained time–frequency model. Switch to linear encoding and compare intermediate estimates with the final result.')}</p>
      <p className="ds-caption">{result?.savedExample
        ? l(`表示中：${modelId}をローカルTorchで実行した計算済み音声例です。`, `Showing an audio example computed locally in Torch with ${modelId}.`)
        : l('公開Webでは計算済み例を開けます。設定を変えた新しい復元はローカルTorch環境で実行します。', 'Open a computed example on the public web. Reconstructing with changed settings requires local Torch.')}
        {' '}{l('独自実装で、論文と同等の精度は未検証です。', 'This is an independent implementation; paper-level accuracy is unverified.')}</p>
      <div className="pt-example"><div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'end', gap: 12 }}>
        <label className="ds-field" style={{ flex: '1 1 240px', maxWidth: 430 }}><span>{l('保存された計算例', 'Saved computation')}</span>
          <select disabled={busy} value={exampleId} onChange={event => { setExampleId(event.target.value as PaperExampleId); setExampleError(''); }}>
            {PAPER_EXAMPLES.map(example => <option key={example.id} value={example.id}>{example.label} · seed {example.seed} · η′ {example.eta_prime}{example.eta_prime === 0 ? l('（観測への拘束なし）', ' (guidance off)') : ''}</option>)}
          </select>
        </label>
        <button type="button" disabled={busy} onClick={() => { void loadPaperExample(); }}>
        {exampleBusy ? <LoaderCircle size={16} className="spin"/> : <Play size={16}/>}{exampleBusy ? l('計算済み例を読み込んでいます', 'Loading the computed example') : l('学習済みモデルの計算例を開く', 'Open the trained model’s computed example')}</button>
        </div>
        <p>{l('学習記録と重みSHAが一致する音声・途中経過・評価を読み込みます。再計算や自動再生は行いません。', 'Load audio, saved stages and scores whose checkpoint SHA matches the training record. This does not rerun the model or start playback.')}</p>
        <p>{l('共通：test scene 0・球面6本・半径0.06 m・SNR 50 dB・観測ノイズseed 173927・150ステップ。AとBは拡散のseedだけ、AとCは観測への拘束だけが異なります。', 'Shared: test scene 0, six microphones on a 0.06 m sphere, SNR 50 dB, observation-noise seed 173927 and 150 steps. A/B differ only in diffusion seed; A/C differ only in observation guidance.')}</p>
        <p>{l('C（η′=0）も観測を含む初期状態から始まります。順に開くと下の履歴から比較できます。選択だけでは表示中の結果は変わりません。', 'C (η′=0) still starts from an observation-based warm start. Open each example to compare them in the history below. Changing this selection does not change the displayed result.')}</p>
        {exampleError && <p role="alert">{exampleError}</p>}
      </div>
    </div>
    <div className="ds-workspace">
      <form className="ds-settings panel" onSubmit={event => { event.preventDefault(); void reconstruct(); }}>
        <fieldset disabled={busy}>
          <div className="ds-section-heading"><span>01</span><h3>{l('観測をつくる', 'Create an observation')}</h3></div>
          <p className="ds-caption">{l('モデル：paper-prior-v1。学習に使わない話者の固定音声と、合成室内応答から観測を作ります。', 'Model: paper-prior-v1. Observations use a fixed held-out speech scene with simulated room responses.')}</p>
          <p className="ds-caption">{l('音声・部屋のシーンは固定です。マイク配置・SNR・観測ノイズseedを保つと、観測入力は同じです。', 'The speech and room scene are fixed. Keeping the array, SNR and observation-noise seed preserves the input.')}</p>
          <div className="ds-fields">
            <label className="ds-field"><span>{l('マイクの本数', 'Microphones')}</span><select value={config.microphones} onChange={e => set('microphones', +e.target.value)}>{[4, 6, 8, 12, 16].map(q => <option key={q}>{q}</option>)}</select></label>
            <label className="ds-field"><span>{l('配置', 'Geometry')}</span><select value={config.geometry} onChange={e => set('geometry', e.target.value)}><option value="sphere">{l('球面', 'Sphere')}</option><option value="ring">{l('水平リング', 'Horizontal ring')}</option></select></label>
            {configField('radius_m', l('半径 / m', 'Radius / m'), .01, .25, .01)}
            {configField('snr_db', l('SNR / dB', 'SNR / dB'), 0, 80)}
          </div>
          <p className="ds-caption">{l('SNRを下げるほどノイズが増えます。水平リングは上下方向の情報が不足します。', 'Lower SNR adds noise. A horizontal ring lacks vertical information.')}</p>
          <details><summary>{l('観測のseed', 'Observation seed')}</summary>{configField('observation_seed', l('観測ノイズのseed', 'Observation-noise seed'), 0, 4294967295)}</details>
          <div className="ds-section-heading"><span>02</span><h3>{l('復元を変える', 'Shape the reconstruction')}</h3></div>
          <div className="ds-fields">
            {configField('seed', l('拡散のseed', 'Diffusion seed'), 0, 4294967295)}
            {configField('steps', l('推論ステップ数', 'Inference steps'), 8, 150)}
          </div>
          <label className="ds-field ds-guidance"><span>{l('観測への拘束', 'Observation guidance')}<strong>{config.eta_prime}</strong></span><input type="range" min="0" max="100" step="1" value={config.eta_prime} onChange={e => set('eta_prime', +e.target.value)} /></label>
          <p className="ds-caption">{l('0で観測整合性の勾配をOFF。初期状態には観測が残ります。値を上げても、精度が単調に上がるとは限りません。', 'At 0, the observation-consistency gradient is off; initialization still uses the observation. Stronger guidance does not guarantee greater accuracy.')}</p>
          <button type="submit" className="ds-primary" disabled={!isLocalEngine || !modelReady}>{busy ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />}{l('ローカルで復元する', 'Reconstruct locally')}</button>
          <button type="button" onClick={newCandidate} className="ds-next" disabled={!isLocalEngine || !modelReady}><Shuffle size={15} />{l('seedを＋1して別候補を作る', 'Create another candidate · seed +1')}</button>
        </fieldset>
        {busy && !exampleBusy && <output className="ds-progress"><p>{progressText}</p><progress max={progress?.total ?? config.steps} value={progress?.step} /></output>}
        {!isLocalEngine && <p className="ds-pending">{l('設定を変えた復元には、モデルとデータを備えたローカル計算環境が必要です。', 'Reconstruction with changed settings requires a local environment with the model and data.')} <a href="http://127.0.0.1:5178/">{l('ローカル画面を開く', 'Open the local interface')}</a></p>}
        {isLocalEngine && !modelReady && <p className="ds-pending">{l('評価済みの学習記録を確認中です。復元には有効な記録・チェックポイント・データが必要です。', 'Waiting for an evaluated training record. Reconstruction requires a valid record, checkpoint and data.')}</p>}
        <p className="ds-caption">{l('設定変更だけでは再計算しません。試聴ボタンを押すまで音は出ません。', 'Changing settings does not rerun the model. Audio plays only when you press play.')}</p>
      </form>
      <div className="ds-result panel" ref={resultRef}>
        <div className="ds-result-head"><div><span className="eyebrow">03 / EXPERIMENT VIEW</span><h3>{result ? `${l('復元', 'Run')} ${run!.id}` : l('配置・復元・ノイズ', 'Array · Reconstruction · Noise')}</h3></div>
          {result && <button role="switch" aria-checked={enabled} onClick={() => { stopProcess(); setEnabled(!enabled); setListening('selected'); }} className={enabled ? 'ds-on' : ''}>{l('拡散', 'Diffusion')} {enabled ? 'ON' : 'OFF'}</button>}
        </div>
        {result && <p className="ds-caption">{l('表示・試聴中のモデル', 'Model being viewed and heard')}: <strong>{modelId}</strong>{finite(modelParameters) && ` · ${modelParameters.toLocaleString()} ${l('パラメータ', 'parameters')}`}
          {result.savedExample && l(' · ローカルで計算済みの例', ' · Precomputed locally')}</p>}
        {result?.savedExample && <p className="ds-pending">{l('この音声・参照・途中経過は、保存された計算例です。設定を変更しても、表示中の記録は変わりません。', 'This audio, reference and trajectory are a saved result. Editing settings does not change the displayed record.')}</p>}
        {changed && <p className="ds-pending">{l('設定を変更しました。推定と音は、選択中の復元結果のままです。アレイとスケジュールでは、現在の設定か復元時の記録かを選べます。', 'Settings changed. The estimate and audio remain from the selected saved run. For the array and schedule, choose current settings or the saved run record.')}</p>}
        <fieldset className="ds-spatial-tabs" style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }} aria-label={l('表示を選ぶ', 'Choose a view')}>
          <button aria-pressed={spatialView === 'array'} onClick={() => setSpatialView('array')}>{l('アレイ配置 3D', 'Microphone array 3D')}</button>
          <button aria-pressed={spatialView === 'soundfield'} onClick={() => setSpatialView('soundfield')}>{l('復元した音場', 'Reconstructed soundfield')}</button>
          <button aria-pressed={spatialView === 'schedule'} onClick={() => setSpatialView('schedule')}>{l('ノイズスケジュール', 'Noise schedule')}</button>
        </fieldset>
        {spatialView === 'array' && <div className="ds-array-view">
          <fieldset className="ds-array-source" style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }} aria-label={l('表示する配置', 'Array geometry source')}>
            <button aria-pressed={!savedArray} onClick={() => setArraySource('settings')}>{l('現在の設定', 'Current settings')}</button>
            <button aria-pressed={savedArray} disabled={!result} onClick={() => setArraySource('run')}>{result ? `${l('復元', 'Run')} ${run!.id} ${l('で使用', 'geometry')}` : l('復元に使った配置', 'Saved run geometry')}</button>
          </fieldset>
          <p className="ds-caption">{savedArray ? l('選択した復元結果に保存されたマイク座標です。', 'Microphone coordinates stored with the selected run.') : l('現在の設定のプレビューです。復元を実行しなくても配置を確認できます。', 'Preview of the current settings. Inspect the geometry without running reconstruction.')} {arrayConfig.microphones} MIC · {arrayConfig.geometry === 'ring' ? l('水平リング', 'Horizontal ring') : l('球面', 'Sphere')} · {l('半径', 'radius')} {fmt(arrayConfig.radius_m * 100, 1)} cm</p>
          {active && <MicrophoneArrayView positions={arrayPositions} language={language} />}
          <p className="ds-caption">{l('点はマイク素子の位置です。カメラの回転は視点だけを変え、配置・録音条件は変えません。実機の筐体や指向性を再現する図ではありません。', 'Points are microphone-element positions. Camera rotation changes only the viewpoint, not the geometry or recording conditions. This does not model a physical microphone housing or directivity.')}</p>
        </div>}
        {spatialView === 'schedule' && <div className="ds-schedule-view">
          <fieldset className="ds-array-source" style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }} aria-label={l('表示するスケジュール', 'Schedule source')}>
            <button aria-pressed={!showingSavedSchedule} onClick={() => setScheduleSource('settings')}>{l('現在の設定', 'Current settings')}</button>
            <button aria-pressed={showingSavedSchedule} disabled={!result} onClick={() => setScheduleSource('run')}>{result ? `${l('復元', 'Run')} ${run!.id} ${l('の記録', 'record')}` : l('復元の記録', 'Saved run record')}</button>
          </fieldset>
          <p className="ds-caption">{showingSavedSchedule ? l('復元時の実行ログに保存されたσを表示します。設定欄を変えても、この記録は変わりません。', 'Sigma values come directly from the saved execution trace. Editing settings does not change this record.') : l('現在の推論ステップ数から計算した予定です。開始σ=20、終了前σ=0.002、ρ=10は固定です。', 'Planned schedule for the current inference-step count. Start σ=20, last positive σ=0.002 and ρ=10 are fixed.')}</p>
          <NoiseScheduleView points={showingSavedSchedule ? savedSchedule : plannedSchedule} language={language}
            sourceLabel={showingSavedSchedule ? `${l('復元', 'Run')} ${run!.id} · ${l('実行ログ', 'Execution trace')}` : l('現在の設定 · 未実行の予定', 'Current settings · Planned, not executed')}
            parameters={showingSavedSchedule ? { sigmaMax: result.configuration.sigma_max, sigmaMin: result.configuration.sigma_min, rho: result.configuration.rho } : { sigmaMax: 20, sigmaMin: .002, rho: 10 }}
            checkpoints={showingSavedSchedule ? result.checkpoints : []}
            selectedStep={showingSavedSchedule && enabled ? checkpoint?.step : undefined}
            onSelectCheckpoint={showingSavedSchedule ? step => {
              const index = result.checkpoints.findIndex(item => item.step === step);
              if (index >= 0) { stopProcess(); setStepIndex(index); setEnabled(true); setListening('selected'); setSpatialView('soundfield'); }
            } : undefined} />
          <p className="ds-caption">{l('これは推論時のスケジュールです。学習時のノイズ分布、マイク観測のSNR、再生音に残ったノイズ量とは異なります。', 'This is the inference schedule. It is distinct from the training-noise distribution, microphone-observation SNR and remaining noise in the rendered audio.')}</p>
        </div>}
        {spatialView === 'soundfield' && <>
        <div className="ds-view-options"><label>{l('表示帯域', 'View band')} <select value={band} onChange={e => setBand(e.target.value as Band)}>{Object.entries(bandNames).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
          <label>{l('重ねて比較', 'Overlay')} <select value={overlay} onChange={e => setOverlay(e.target.value as typeof overlay)}><option value="reference">{l('合成の正解', 'Synthetic reference')}</option><option value="linear">{l('線形推定 / OFF', 'Linear / OFF')}</option><option value="previous" disabled={!previous}>{l('同じ入力の別候補', 'Another candidate, same input')}</option><option value="none">{l('なし', 'None')}</option></select></label>
        </div>
        {active && <DiffusionScene covariance={currentCovariance} referenceCovariance={overlay === 'reference' ? compareCovariance : undefined} comparisonCovariance={overlay !== 'reference' ? compareCovariance : undefined} microphonePositions={result?.microphone_positions_m ?? []} sourceDirections={result?.source_directions.map(source => source.direction) ?? []} language={language} commonScale={scale} />}
        {!result && <p className="ds-empty">{l('「学習済みモデルの計算例を開く」で音と復元結果を読み込めます。アレイ配置は計算前のプレビューです。', 'Open the trained model’s computed example to load its audio and reconstruction. Array geometry is a preview before computation.')}</p>}
        </>}
        {result && <>
          {spatialView === 'soundfield' && <>
          <div className="ds-scale"><label><input type="checkbox" checked={sharedScale} onChange={e => setSharedScale(e.target.checked)} />{l('同じ入力の保存段階・候補で表示スケールを共通化', 'Use one visual scale across saved stages and candidates with this input')}</label></div>
          <p className="ds-caption">{l('実線面：選択中の推定 ／ 比較面：', 'Solid surface: selected estimate / overlay: ')}{overlay === 'reference' ? l('合成の正解', 'synthetic reference') : overlay === 'linear' ? l('線形推定', 'linear') : overlay === 'previous' ? `Run ${previous?.id ?? '—'}` : l('なし', 'none')}{!sharedScale && l('。表示ごとにスケールが変わります。', '. Scale changes between views.')}</p>
          </>}
          <div className="ds-timeline"><div><h3>{l('復元の途中を選ぶ', 'Choose a reconstruction stage')}</h3><span>{enabled ? `${checkpoint?.stage === 'final_sample' ? l('最終', 'Final') : l('途中', 'Intermediate')} · ${checkpoint?.step} / ${result.configuration.steps}` : l('OFF · 線形推定', 'OFF · Linear estimate')}</span></div>
            <input aria-label={l('復元の途中', 'Reconstruction stage')} type="range" min="0" max={result.checkpoints.length - 1} step="1" value={stepIndex} disabled={!enabled} onChange={e => { stopProcess(); setStepIndex(+e.target.value); setListening('selected'); }} />
            <div className="ds-stage-buttons">{result.checkpoints.map((point, i) => <button key={point.id} disabled={!enabled} className={i === stepIndex && enabled ? 'active' : ''} onClick={() => { stopProcess(); setStepIndex(i); setListening('selected'); }} aria-label={`${l('ステップ', 'Step')} ${point.step}`}>{point.step}{point.stage === 'final_sample' ? ' ●' : ''}</button>)}</div>
            <p className="ds-caption">{l('途中はノイズ除去後の推定、●は最後の更新後の出力。スライダーは保存済みのステップを切り替えます。', 'Intermediate stages are denoised estimates; ● is the output after the last update. The slider switches between saved stages.')}</p>
          </div>
          <div className="ds-listen"><div className="ds-listen-head"><h3>{l('選んだ音を聴く', 'Listen to the selection')}</h3><select aria-label={l('試聴する音', 'Audio to preview')} value={listening} onChange={e => { stopProcess(); setListening(e.target.value as typeof listening); }}><option value="selected">{l('選択中の推定', 'Selected estimate')}</option><option value="reference">{l('合成の正解', 'Synthetic reference')}</option></select></div>
            <audio ref={audioRef} key={audioUrl} src={audioUrl} onPlay={stopProcess} controls preload="metadata" loop={loop} aria-label={l('音声復元を試聴', 'Preview the speech reconstruction')}>
              <track kind="captions" srcLang={language === 'jp' ? 'ja' : 'en'} label={l('音の説明', 'Sound description')} src={`data:text/vtt;charset=utf-8,${encodeURIComponent('WEBVTT\n\n00:00.000 --> ' + new Date(Math.max(.001, result.audio.duration_seconds ?? .35) * 1000).toISOString().slice(11, 23) + '\n' + l('VCTKの未学習話者音声と合成室内応答から作った観測に対する、選択中の復元。', 'Selected reconstruction of a virtual observation generated from held-out VCTK speech and simulated room responses.'))}`} />
            </audio>
            <label className="ds-loop"><input type="checkbox" checked={loop} onChange={e => setLoop(e.target.checked)} />{l('短いクリップをループ再生', 'Loop the short clip')}</label>
            <p className="ds-caption">{l('固定方向の仮想マイクによるステレオ試聴です。3Dのカメラや表示帯域を変えても、音は変わりません。ヘッドホン向けHRTF再生ではありません。', 'Stereo preview through fixed virtual microphones. Rotating the 3D camera or changing the view band does not change the audio. This is not HRTF headphone rendering.')}</p>
            <p className="ds-caption">{l('候補を切り替えると、同じ入力の履歴内で再生ゲインを揃えます。ZIPの書き出しゲインは試行ごとに異なる場合があります。', 'Switching candidates aligns playback gain across the history with the same input. Downloaded ZIPs may have different export gains between runs.')} {l('共通試聴ゲイン', 'Common preview gain')}: {fmt(commonAudioGain, 4)}</p>
            {attribution && <div className="ds-caption"><p>{attribution.title} · {attribution.corpus}<br/>{l('話者', 'Speakers')}: {attribution.speakers.join(', ')} · {attribution.files.join(', ')}</p>
              <p><a href={attribution.source_url} target="_blank" rel="noreferrer">{l('音声の出典', 'Audio source')}</a> · <a href={attribution.license_url} target="_blank" rel="noreferrer">{attribution.license}</a></p><p>{l('加工内容（記録の原文）', 'Processing, as recorded')}: {attribution.changes}</p></div>}
          </div>
          <ProcessAudition stages={result.checkpoints} runKey={String(run!.id)} gain={previewLevel} language={language} active={active && !busy} stopToken={auditionStopToken}
            onStart={() => { audioRef.current?.pause(); setEnabled(true); setListening('selected'); setSpatialView('soundfield'); }}
            onStage={index => { setStepIndex(index); setEnabled(true); setListening('selected'); }} />
          <div className="ds-metrics">
            <div><span>{enabled ? l('選択中の復元 / NRMSE', 'Selected reconstruction / NRMSE') : l('OFF · Linear / NRMSE', 'OFF · Linear / NRMSE')}</span>
              <strong>{finite(selectedNrmse) ? <>{fmt(selectedNrmse)} <small>dB</small></> : l('データなし', 'Unavailable')}</strong><p>{l('同じ正解との誤差 · 低いほど一致', 'Error against the same reference · lower is closer')}</p></div>
            <div><span>{l('同じ入力のLinear / NRMSE', 'Same-input Linear / NRMSE')}</span>
              <strong>{finite(linearNrmse) ? <>{fmt(linearNrmse)} <small>dB</small></> : l('データなし', 'Unavailable')}</strong><p>{l('この復元に保存された線形推定の誤差', 'Baseline error saved with this reconstruction')}</p></div>
            <div><span>{l('Linearに対する誤差の改善量', 'Error improvement over Linear')}</span>
              <strong>{finite(nrmseImprovement) ? <>{nrmseImprovement > 0 ? '+' : ''}{fmt(nrmseImprovement)} <small>dB</small></> : l('比較できません', 'Unavailable')}</strong>
              <p>{!finite(nrmseImprovement) ? l('比較に必要な誤差データがありません', 'A required error value is unavailable') : !enabled ? l('OFF：同じLinearを表示しているため差は0', 'OFF: the selected estimate is the same Linear baseline, so the difference is 0') : nrmseImprovement > 0 ? l('改善：選択中の復元の誤差が小さい', 'Improved: the selected reconstruction has lower error') : nrmseImprovement < 0 ? l('悪化：選択中の復元の誤差が大きい', 'Regressed: the selected reconstruction has higher error') : l('Linearと同じ誤差', 'The same error as Linear')}</p>
              <p>{l('Linearの誤差 − 選択中の誤差。正は改善、負は悪化。', 'Linear error minus selected error. Positive is better; negative is worse.')}</p></div>
            <div><span>{l('正解とのcoherence', 'Reference coherence')}</span><strong>{fmt(estimate?.metrics.coherence, 3)}</strong>
            <p>{estimate?.metrics.coherence_status === 'undefined_missing_estimate' ? l('必要な成分の推定がゼロのため未定義', 'Undefined: a required estimated component is zero') : estimate?.metrics.coherence_status === 'undefined_no_reference' ? l('有効な正解成分がないため未定義', 'Undefined: no active reference component') : l('周波数ごとのMSCの平均 · DCを含む', 'Mean frequency-wise MSC · includes DC')}</p>
            {estimate?.metrics.coherence_reference_active_frequency_bins !== undefined && <p>{l('有効な周波数', 'Valid frequencies')}: {estimate.metrics.coherence_valid_frequency_bins} / {estimate.metrics.coherence_reference_active_frequency_bins}</p>}
          </div></div>
          <p className="ds-caption">{l('推定精度と形の変化は別です。形が変わることや、きれいに見えることは改善の証明にはなりません。', 'Accuracy and visible variation are separate. A changed or attractive shape does not establish improvement.')}</p>
          <div className="ds-download"><button onClick={download} disabled={downloadBusy}>{downloadBusy ? <LoaderCircle size={15} className="spin"/> : <Download size={15} />}{l('保存段階の4ch WAV・結果を保存', 'Save recorded stages · 4ch WAV + results')}</button><span>{l('ACN / N3D · W, Y, Z, X', 'ACN / N3D · W, Y, Z, X')}</span></div>
        </>}
      </div>
    </div>
    {error && <div className="error" role="alert">{error}</div>}
    {result && checkpoint && <SpectralComparison language={language} runId={run!.id} inputSha256={result.input_sha256}
      linear={result.linear} diffusion={checkpoint} checkpoints={result.checkpoints} />}
    <PaperTraining language={language} active={active} onLoadExample={sha => { void loadPaperExample(sha); }} exampleBusy={exampleBusy} exampleDisabled={busy} exampleError={exampleError} />
    {runs.length > 0 && <section className="panel ds-history"><div className="ds-history-heading"><div><span className="eyebrow">04 / RECONSTRUCTION LOG</span><h3>{l('復元ごとの記録', 'Reconstruction history')}</h3></div><button onClick={() => { audioRef.current?.pause(); setRuns([]); setSelectedId(undefined); }} disabled={busy}><Trash2 size={14} />{l('履歴を消す', 'Clear history')}</button></div>
      <p className="ds-caption">{l('このタブで直近6件を保持します。再読み込みで消えるため、残したい結果はZIPで保存してください。', 'The latest six runs stay in this tab. Reloading clears them; download a ZIP to keep a result.')}</p>
      <div className="ds-run-list">{runs.map(item => <button className={item.id === run?.id ? 'active' : ''} key={item.id} onClick={() => selectRun(item)}><span>Run {item.id}<small>{item.result.savedExample && l('読込 ', 'Loaded ')}{item.created}</small><small>{modelText(item.result.model, 'id')}{item.result.savedExample && l(' · 保存例', ' · Saved example')}</small></span><strong>seed {item.result.configuration.seed}</strong><span>η′ {item.result.configuration.eta_prime} · {item.result.configuration.steps} {l('ステップ', 'steps')}</span><small>{item.result.input_sha256 === result?.input_sha256 ? l('選択中と同じ入力', 'Same input as selected') : l('異なる入力', 'Different input')}</small><span>NRMSE {fmt(item.result.checkpoints.at(-1)?.metrics.nrmse_db)} dB</span></button>)}</div>
      {result && <><p className="ds-hash">{l('選択中の入力', 'Selected input')} SHA-256 · {result.input_sha256}<br/>{l('モデル', 'Model')} {modelId} · SHA-256 {modelText(result.model, 'weights_sha256')}</p>{<button disabled={busy} onClick={() => setConfig(Object.fromEntries(Object.keys(defaults).map(key => [key, result.configuration[key as keyof Configuration]])) as Configuration)}>{l('この復元の設定を読み込む', 'Load settings from this run')}</button>}</>}
    </section>}
    {result && <section className="panel ds-details"><h3>{l('推論の変化を数値で見る', 'Inspect the inference numerically')}</h3>
      <Plot x={result.trace.map(row => row.step)} series={[{ name: l('観測との不一致（圧縮領域）', 'Observation mismatch (compressed domain)'), values: result.trace.map(row => row.encoded_residual), color: '#eee' }]} label={l('各反復のノイズ除去後の推定を評価', 'Denoised estimate evaluated at each iteration')} log={false} unit="" xLabel={l('反復', 'Iteration')} />
      <div className="ds-table"><table><thead><tr><th>{l('完了ステップ', 'Completed steps')}</th><th>σ</th><th>NRMSE / dB</th><th>Coherence</th></tr></thead><tbody>{result.checkpoints.map(point => <tr key={point.id}><td>{point.step}{point.stage === 'final_sample' ? ' ●' : ''}</td><td>{fmt(point.sigma, 4)}</td><td>{fmt(point.metrics.nrmse_db)}</td><td>{fmt(point.metrics.coherence, 4)}</td></tr>)}</tbody></table></div>
      <p className="ds-caption">{l('Coherenceは正解が有効な周波数の等重み平均です。必要な推定成分が欠けた周波数が1つでもある場合、全体値は未定義（—）とし、欠けた成分を除いて高い値を出すことはしません。', 'Coherence averages reference-active frequencies equally. If any required estimated component is missing at any frequency, the overall value is undefined (—); missing components are not omitted to produce a higher score.')}</p>
      <details><summary>{l('入力・音声・モデルの詳細', 'Input, audio and model details')}</summary><pre>{JSON.stringify({ configuration: result.configuration, input_sha256: result.input_sha256, audio: result.audio, model: result.model, scaling_diagnostic: result.scaling_diagnostic }, null, 2)}</pre></details>
    </section>}
  </section>;
}
