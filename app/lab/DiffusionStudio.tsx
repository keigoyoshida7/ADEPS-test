import { useEffect, useMemo, useRef, useState } from 'react';
import { Download, LoaderCircle, Play, Shuffle, Square, Trash2 } from 'lucide-react';
import { useLanguage } from './i18n';
import { analysisApi, cancelAnalysis, isLocalEngine, onAnalysisProgress, type AnalysisProgress } from './scientificClient';
import DiffusionScene from './DiffusionScene';
import ModelProvenance from './ModelProvenance';
import MicrophoneArrayView from './MicrophoneArrayView';
import { virtualArrayPositions } from './arrayGeometry';
import { Plot, fmt } from './Plots';
import './DiffusionStudio.css';

type Band = 'broadband' | 'low' | 'mid' | 'high';
type Covariance = Record<Band, number[][]>;
type Metrics = { nrmse_db?: number | null; coherence?: number | null; encoded_residual?: number | null; si_sdr_db?: number | null };
type Estimate = { id: string; label: string; stage: string; step: number; sigma: number; covariance: Covariance; preview_wav_base64: string; metrics: Metrics };
type Configuration = { microphones: number; radius_m: number; geometry: 'sphere' | 'ring'; snr_db: number; observation_seed: number; seed: number; eta_prime: number; steps: number };
type StudioResult = {
  configuration: Configuration; input_sha256: string; microphone_positions_m: number[][];
  source_directions: { id: string; direction: number[] }[];
  reference: Estimate; linear: Estimate; checkpoints: Estimate[];
  trace: { step: number; sigma: number; encoded_residual: number }[];
  audio: { shared_gain: number; [key: string]: unknown }; model: Record<string, unknown>; bytes: ArrayBuffer; filename: string;
};
type Run = { id: number; created: string; result: StudioResult };
const defaults: Configuration = { microphones: 6, radius_m: .06, geometry: 'sphere', snr_db: 35, observation_seed: 2026, seed: 42, eta_prime: 50, steps: 24 };
const zero = Array.from({ length: 4 }, () => [0, 0, 0, 0]);
const rmsBound = (matrix: number[][]) => 2 * Math.sqrt(Math.max(0, matrix.reduce((sum, row, i) => sum + row[i], 0)));
const originalCovariance = (estimate: Estimate | undefined, band: Band, gain = 1) =>
  estimate?.covariance[band].map(row => row.map(value => value / (gain * gain))) ?? zero;

export default function DiffusionStudio({ active = true }: { active?: boolean }) {
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [config, setConfig] = useState(defaults);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedId, setSelectedId] = useState<number>();
  const [stepIndex, setStepIndex] = useState(0);
  const [enabled, setEnabled] = useState(true);
  const [band, setBand] = useState<Band>('broadband');
  const [spatialView, setSpatialView] = useState<'array' | 'soundfield'>('array');
  const [arraySource, setArraySource] = useState<'settings' | 'run'>('settings');
  const [overlay, setOverlay] = useState<'reference' | 'linear' | 'previous' | 'none'>('reference');
  const [sharedScale, setSharedScale] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<AnalysisProgress>();
  const [error, setError] = useState('');
  const [loop, setLoop] = useState(false);
  const [listening, setListening] = useState<'selected' | 'reference'>('selected');
  const audioRef = useRef<HTMLAudioElement>(null);
  const counter = useRef(0);
  const run = runs.find(item => item.id === selectedId) ?? runs.at(-1);
  const result = run?.result;
  const previewPositions = useMemo(() => virtualArrayPositions(config.microphones, config.radius_m, config.geometry), [config.microphones, config.radius_m, config.geometry]);
  const savedArray = arraySource === 'run' && !!result;
  const arrayPositions = savedArray ? result.microphone_positions_m : previewPositions;
  const arrayConfig = savedArray ? result.configuration : config;
  const checkpoint = result?.checkpoints[Math.min(stepIndex, result.checkpoints.length - 1)];
  const estimate = enabled ? checkpoint : result?.linear;
  const previous = runs.filter(item => item.id !== run?.id && item.result.input_sha256 === result?.input_sha256).at(-1);
  const compare = overlay === 'reference' ? result?.reference : overlay === 'linear' ? result?.linear : overlay === 'previous' ? previous?.result.checkpoints.at(-1) : undefined;
  const preview = listening === 'reference' ? result?.reference : estimate;
  const audioUrl = preview ? `data:audio/wav;base64,${preview.preview_wav_base64}` : undefined;
  const commonAudioGain = result ? Math.min(...runs.filter(item => item.result.input_sha256 === result.input_sha256).map(item => item.result.audio.shared_gain as number)) : 1;
  const previewLevel = result ? Math.min(1, commonAudioGain / result.audio.shared_gain) : 1;
  useEffect(() => { if (audioRef.current) audioRef.current.volume = previewLevel; }, [audioUrl, previewLevel]);
  const currentCovariance = useMemo(() => originalCovariance(estimate, band, result?.audio.shared_gain), [estimate, band, result]);
  const compareResult = overlay === 'previous' ? previous?.result : result;
  const compareCovariance = useMemo(() => compare ? originalCovariance(compare, band, compareResult?.audio.shared_gain) : undefined, [compare, band, compareResult]);
  useEffect(() => onAnalysisProgress(setProgress), []);
  useEffect(() => { if (!active) audioRef.current?.pause(); }, [active]);
  const scale = useMemo(() => {
    if (!result || !sharedScale) return undefined;
    const same = runs.filter(item => item.result.input_sha256 === result.input_sha256);
    return Math.max(1e-12, ...same.flatMap(item => [item.result.reference, item.result.linear, ...item.result.checkpoints].map(point => rmsBound(originalCovariance(point, band, item.result.audio.shared_gain)))));
  }, [runs, result, band, sharedScale]);
  const changed = result && Object.entries(config).some(([key, value]) => value !== result.configuration[key as keyof Configuration]);
  const bandNames: Record<Band, string> = {
    broadband: l('全帯域 · 62.5 Hz–8 kHz', 'Broadband · 62.5 Hz–8 kHz'), low: l('低域 · 62.5–437.5 Hz', 'Low · 62.5–437.5 Hz'), mid: l('中域 · 500–1937.5 Hz', 'Mid · 500–1937.5 Hz'), high: l('高域 · 2–8 kHz', 'High · 2–8 kHz'),
  };
  const set = (key: keyof Configuration, value: number | string) => {
    setConfig(c => ({ ...c, [key]: value }));
    if (key === 'microphones' || key === 'radius_m' || key === 'geometry') {
      setArraySource('settings'); setSpatialView('array');
    }
  };
  async function reconstruct(next = config) {
    setBusy(true); setError(''); setProgress(undefined); audioRef.current?.pause();
    try {
      const response = await analysisApi('diffusion-studio', next) as StudioResult;
      const id = ++counter.current;
      setRuns(items => [...items, { id, created: new Date().toLocaleTimeString(), result: response }].slice(-6));
      setSelectedId(id); setStepIndex(response.checkpoints.length - 1); setEnabled(true); setListening('selected');
      setArraySource('run'); setSpatialView('soundfield');
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  function newCandidate() {
    const next = { ...config, seed: (config.seed + 1) >>> 0 };
    setConfig(next); void reconstruct(next);
  }
  function selectRun(item: Run) {
    setSelectedId(item.id); setStepIndex(item.result.checkpoints.length - 1); setListening('selected');
    setArraySource('run');
  }
  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([result.bytes], { type: 'application/zip' }));
    const a = document.createElement('a'); a.href = url; a.download = `ADEPS_diffusion_run-${run!.id}_seed-${result.configuration.seed}.zip`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const configField = (key: keyof Configuration, label: string, min: number, max: number, step = 1) => (
    <label className="ds-field"><span>{label}</span><input type="number" value={config[key]} min={min} max={max} step={step}
      onChange={e => set(key, Number(e.target.value))} required /></label>
  );
  const progressText = progress?.stage === 'inference'
    ? `${l('復元中', 'Reconstructing')} ${progress.step ?? 0} / ${progress.total ?? config.steps}`
    : l('計算データを準備しています', 'Preparing the computation');

  return <section className="diffusion-studio" aria-label={l('拡散・音場スタジオ', 'Diffusion soundfield studio')}>
    <div className="ds-intro"><span className="eyebrow">DIFFUSION / LISTEN · OBSERVE · COMPARE</span>
      <h2>{l('ひとつの観測、いくつもの復元。', 'One observation. Many reconstructions.')}</h2>
      <p>{l('仮想マイクが拾った同じ音から、初期ノイズと観測への拘束を変えて復元。途中の推定を聴き、Ambisonicsの形を見比べます。', 'Reconstruct the same virtual microphone observation with different initial noise and observation guidance. Listen to intermediate estimates and compare their Ambisonics shapes.')}</p>
      <p className="ds-caption">{l('独自学習の小型拡散モデルによる実験です。論文と同等の精度は未検証で、学習モデル比較タブのMLPとは別モデルです。', 'An experiment with an independently trained small diffusion model. Paper-level accuracy is unverified. This is a separate model from the MLP in Learned Model A/B.')}</p>
    </div>
    <details className="panel ds-settings"><summary>{l('モデルの学習データと学習方法', 'Model training data and method')}</summary><ModelProvenance kind="diffusion" /></details>
    <div className="ds-workspace">
      <form className="ds-settings panel" onSubmit={event => { event.preventDefault(); void reconstruct(); }}>
        <fieldset disabled={busy}>
          <div className="ds-section-heading"><span>01</span><h3>{l('観測をつくる', 'Create an observation')}</h3></div>
          <p className="ds-caption">{l('2方向の短い音を、仮想マイクで録音します。この設定を保つと入力は同じです。', 'Two short sounds from different directions, recorded by virtual microphones. Keeping these settings preserves the input.')}</p>
          <div className="ds-fields">
            <label className="ds-field"><span>{l('マイクの本数', 'Microphones')}</span><select value={config.microphones} onChange={e => set('microphones', +e.target.value)}>{[4, 6, 8, 12, 16].map(q => <option key={q}>{q}</option>)}</select></label>
            <label className="ds-field"><span>{l('配置', 'Geometry')}</span><select value={config.geometry} onChange={e => set('geometry', e.target.value)}><option value="sphere">{l('球面', 'Sphere')}</option><option value="ring">{l('水平リング', 'Horizontal ring')}</option></select></label>
            {configField('radius_m', l('半径 / m', 'Radius / m'), .01, .25, .01)}
            {configField('snr_db', l('SNR / dB', 'SNR / dB'), 0, 80)}
          </div>
          <p className="ds-caption">{l('SNRを下げるほどノイズが増えます。水平リングは上下方向の情報が不足します。', 'Lower SNR adds noise. A horizontal ring lacks vertical information.')}</p>
          <details><summary>{l('観測のseed', 'Observation seed')}</summary>{configField('observation_seed', l('音源・観測ノイズのseed', 'Source and observation seed'), 0, 4294967295)}</details>
          <div className="ds-section-heading"><span>02</span><h3>{l('復元を変える', 'Shape the reconstruction')}</h3></div>
          <div className="ds-fields">
            {configField('seed', l('拡散のseed', 'Diffusion seed'), 0, 4294967295)}
            {configField('steps', l('推論ステップ数', 'Inference steps'), 8, 80)}
          </div>
          <label className="ds-field ds-guidance"><span>{l('観測への拘束', 'Observation guidance')}<strong>{config.eta_prime}</strong></span><input type="range" min="0" max="100" step="1" value={config.eta_prime} onChange={e => set('eta_prime', +e.target.value)} /></label>
          <p className="ds-caption">{l('0で観測整合性の勾配をOFF。初期状態には観測が残ります。値を上げても、精度が単調に上がるとは限りません。', 'At 0, the observation-consistency gradient is off; initialization still uses the observation. Stronger guidance does not guarantee greater accuracy.')}</p>
          <button type="submit" className="ds-primary">{busy ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />}{l('復元する', 'Reconstruct')}</button>
          <button type="button" onClick={newCandidate} className="ds-next"><Shuffle size={15} />{l('seedを＋1して別候補を作る', 'Create another candidate · seed +1')}</button>
        </fieldset>
        {busy && <output className="ds-progress"><p>{progressText}</p><progress max={progress?.total ?? config.steps} value={progress?.step ?? 0} />{!isLocalEngine && <button type="button" onClick={cancelAnalysis}><Square size={12} />{l('中止', 'Cancel')}</button>}</output>}
        {error && <div className="error" role="alert">{error}</div>}
        <p className="ds-caption">{l('ブラウザ内で計算します。試聴ボタンを押すまで音は出ません。', 'Computed in your browser. Audio plays only when you press play.')}</p>
      </form>
      <div className="ds-result panel">
        <div className="ds-result-head"><div><span className="eyebrow">03 / SPATIAL VIEW</span><h3>{result ? `${l('復元', 'Run')} ${run!.id}` : l('マイクアレイと音場', 'Microphone array and soundfield')}</h3></div>
          {result && <button role="switch" aria-checked={enabled} onClick={() => { setEnabled(!enabled); setListening('selected'); }} className={enabled ? 'ds-on' : ''}>{l('拡散', 'Diffusion')} {enabled ? 'ON' : 'OFF'}</button>}
        </div>
        {changed && <p className="ds-pending">{l('設定を変更しました。推定と音は、選択中の復元結果のままです。アレイ表示では現在の設定と復元に使用した配置を選べます。', 'Settings changed. The estimate and audio remain from the selected saved run. In the array view, choose current settings or the geometry used for that run.')}</p>}
        <div className="ds-spatial-tabs" role="group" aria-label={l('3D表示を選ぶ', 'Choose a 3D view')}>
          <button aria-pressed={spatialView === 'array'} onClick={() => setSpatialView('array')}>{l('アレイ配置 3D', 'Microphone array 3D')}</button>
          <button aria-pressed={spatialView === 'soundfield'} onClick={() => setSpatialView('soundfield')}>{l('復元した音場', 'Reconstructed soundfield')}</button>
        </div>
        {spatialView === 'array' && <div className="ds-array-view">
          <div className="ds-array-source" role="group" aria-label={l('表示する配置', 'Array geometry source')}>
            <button aria-pressed={!savedArray} onClick={() => setArraySource('settings')}>{l('現在の設定', 'Current settings')}</button>
            <button aria-pressed={savedArray} disabled={!result} onClick={() => setArraySource('run')}>{result ? `${l('復元', 'Run')} ${run!.id} ${l('で使用', 'geometry')}` : l('復元に使った配置', 'Saved run geometry')}</button>
          </div>
          <p className="ds-caption">{savedArray ? l('選択した復元結果に保存されたマイク座標です。', 'Microphone coordinates stored with the selected run.') : l('現在の設定のプレビューです。復元を実行しなくても配置を確認できます。', 'Preview of the current settings. Inspect the geometry without running reconstruction.')} {arrayConfig.microphones} MIC · {arrayConfig.geometry === 'ring' ? l('水平リング', 'Horizontal ring') : l('球面', 'Sphere')} · {l('半径', 'radius')} {fmt(arrayConfig.radius_m * 100, 1)} cm</p>
          {active && <MicrophoneArrayView positions={arrayPositions} language={language} />}
          <p className="ds-caption">{l('点はマイク素子の位置です。カメラの回転は視点だけを変え、配置・録音条件は変えません。実機の筐体や指向性を再現する図ではありません。', 'Points are microphone-element positions. Camera rotation changes only the viewpoint, not the geometry or recording conditions. This does not model a physical microphone housing or directivity.')}</p>
        </div>}
        {spatialView === 'soundfield' && <>
        <div className="ds-view-options"><label>{l('表示帯域', 'View band')} <select value={band} onChange={e => setBand(e.target.value as Band)}>{Object.entries(bandNames).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
          <label>{l('重ねて比較', 'Overlay')} <select value={overlay} onChange={e => setOverlay(e.target.value as typeof overlay)}><option value="reference">{l('合成の正解', 'Synthetic reference')}</option><option value="linear">{l('線形推定 / OFF', 'Linear / OFF')}</option><option value="previous" disabled={!previous}>{l('同じ入力の別候補', 'Another candidate, same input')}</option><option value="none">{l('なし', 'None')}</option></select></label>
        </div>
        {active && <DiffusionScene covariance={currentCovariance} referenceCovariance={overlay === 'reference' ? compareCovariance : undefined} comparisonCovariance={overlay !== 'reference' ? compareCovariance : undefined} microphonePositions={result?.microphone_positions_m ?? []} sourceDirections={result?.source_directions.map(source => source.direction) ?? []} language={language} commonScale={scale} />}
        {!result && <p className="ds-empty">{l('「復元する」で音と音場を生成します。アレイ配置は復元前から確認できます。', 'Select Reconstruct to generate audio and the soundfield. Array geometry is available before reconstruction.')}</p>}
        </>}
        {result && <>
          <div className="ds-scale"><label><input type="checkbox" checked={sharedScale} onChange={e => setSharedScale(e.target.checked)} />{l('同じ入力の全ステップ・候補で表示スケールを共通化', 'Use one visual scale across all steps and candidates with this input')}</label></div>
          <p className="ds-caption">{l('実線面：選択中の推定 ／ 比較面：', 'Solid surface: selected estimate / overlay: ')}{overlay === 'reference' ? l('合成の正解', 'synthetic reference') : overlay === 'linear' ? l('線形推定', 'linear') : overlay === 'previous' ? `Run ${previous?.id ?? '—'}` : l('なし', 'none')}{!sharedScale && l('。表示ごとにスケールが変わります。', '. Scale changes between views.')}</p>
          <div className="ds-timeline"><div><h3>{l('復元の途中を選ぶ', 'Choose a reconstruction stage')}</h3><span>{enabled ? `${checkpoint?.stage === 'final_sample' ? l('最終', 'Final') : l('途中', 'Intermediate')} · ${checkpoint?.step} / ${result.configuration.steps}` : l('OFF · 線形推定', 'OFF · Linear estimate')}</span></div>
            <input aria-label={l('復元の途中', 'Reconstruction stage')} type="range" min="0" max={result.checkpoints.length - 1} step="1" value={stepIndex} disabled={!enabled} onChange={e => { setStepIndex(+e.target.value); setListening('selected'); }} />
            <div className="ds-stage-buttons">{result.checkpoints.map((point, i) => <button key={point.id} disabled={!enabled} className={i === stepIndex && enabled ? 'active' : ''} onClick={() => { setStepIndex(i); setListening('selected'); }} aria-label={`${l('ステップ', 'Step')} ${point.step}`}>{point.step}{point.stage === 'final_sample' ? ' ●' : ''}</button>)}</div>
            <p className="ds-caption">{l('途中はノイズ除去後の推定、●は最後の更新後の出力。スライダーは保存済みのステップを切り替えます。', 'Intermediate stages are denoised estimates; ● is the output after the last update. The slider switches between saved stages.')}</p>
          </div>
          <div className="ds-listen"><div className="ds-listen-head"><h3>{l('選んだ音を聴く', 'Listen to the selection')}</h3><select aria-label={l('試聴する音', 'Audio to preview')} value={listening} onChange={e => setListening(e.target.value as typeof listening)}><option value="selected">{l('選択中の推定', 'Selected estimate')}</option><option value="reference">{l('合成の正解', 'Synthetic reference')}</option></select></div>
            <audio ref={audioRef} key={audioUrl} src={audioUrl} controls preload="metadata" loop={loop} aria-label={l('短い合成音の推定を試聴', 'Preview the short synthetic sound estimate')}>
              <track kind="captions" srcLang={language === 'jp' ? 'ja' : 'en'} label={l('音の説明', 'Sound description')} src={`data:text/vtt;charset=utf-8,${encodeURIComponent('WEBVTT\n\n00:00.000 --> 00:00.350\n' + l('2方向の合成音：高さの変わる音と短いノイズ。その選択中の推定。', 'Two-direction synthetic sound: changing tones and a short noise burst, in the selected estimate.'))}`} />
            </audio>
            <label className="ds-loop"><input type="checkbox" checked={loop} onChange={e => setLoop(e.target.checked)} />{l('短いクリップをループ再生', 'Loop the short clip')}</label>
            <p className="ds-caption">{l('固定方向の仮想マイクによるステレオ試聴です。3Dのカメラや表示帯域を変えても、音は変わりません。ヘッドホン向けHRTF再生ではありません。', 'Stereo preview through fixed virtual microphones. Rotating the 3D camera or changing the view band does not change the audio. This is not HRTF headphone rendering.')}</p>
            <p className="ds-caption">{l('候補を切り替えると、同じ入力の履歴内で再生ゲインを揃えます。ZIPの書き出しゲインは試行ごとに異なる場合があります。', 'Switching candidates aligns playback gain across the history with the same input. Downloaded ZIPs may have different export gains between runs.')} {l('共通試聴ゲイン', 'Common preview gain')}: {fmt(commonAudioGain, 4)}</p>
          </div>
          <div className="ds-metrics"><div><span>{l('正解との誤差 / NRMSE', 'Reference error / NRMSE')}</span><strong>{fmt(estimate?.metrics.nrmse_db)} <small>dB</small></strong><p>{l('低いほど一致', 'Lower is closer')}</p></div><div><span>{l('正解とのcoherence', 'Reference coherence')}</span><strong>{fmt(estimate?.metrics.coherence, 3)}</strong><p>{l('1に近いほど一致', 'Closer to 1 is better')}</p></div></div>
          <p className="ds-caption">{l('推定精度と形の変化は別です。形が変わることや、きれいに見えることは改善の証明にはなりません。', 'Accuracy and visible variation are separate. A changed or attractive shape does not establish improvement.')}</p>
          <div className="ds-download"><button onClick={download}><Download size={15} />{l('全ステップの4ch WAV・結果を保存', 'Save all stages · 4ch WAV + results')}</button><span>{l('ACN / N3D · W, Y, Z, X', 'ACN / N3D · W, Y, Z, X')}</span></div>
        </>}
      </div>
    </div>
    {runs.length > 0 && <section className="panel ds-history"><div className="ds-history-heading"><div><span className="eyebrow">04 / RECONSTRUCTION LOG</span><h3>{l('復元ごとの記録', 'Reconstruction history')}</h3></div><button onClick={() => { audioRef.current?.pause(); setRuns([]); setSelectedId(undefined); }} disabled={busy}><Trash2 size={14} />{l('履歴を消す', 'Clear history')}</button></div>
      <p className="ds-caption">{l('このタブで直近6件を保持します。再読み込みで消えるため、残したい結果はZIPで保存してください。', 'The latest six runs stay in this tab. Reloading clears them; download a ZIP to keep a result.')}</p>
      <div className="ds-run-list">{runs.map(item => <button className={item.id === run?.id ? 'active' : ''} key={item.id} onClick={() => selectRun(item)}><span>Run {item.id}<small>{item.created}</small></span><strong>seed {item.result.configuration.seed}</strong><span>η′ {item.result.configuration.eta_prime} · {item.result.configuration.steps} {l('ステップ', 'steps')}</span><small>{item.result.input_sha256 === result?.input_sha256 ? l('選択中と同じ入力', 'Same input as selected') : l('異なる入力', 'Different input')}</small><span>NRMSE {fmt(item.result.checkpoints.at(-1)?.metrics.nrmse_db)} dB</span></button>)}</div>
      {result && <><p className="ds-hash">{l('選択中の入力', 'Selected input')} SHA-256 · {result.input_sha256}</p><button disabled={busy} onClick={() => setConfig(Object.fromEntries(Object.keys(defaults).map(key => [key, result.configuration[key as keyof Configuration]])) as Configuration)}>{l('この復元の設定を読み込む', 'Load settings from this run')}</button></>}
    </section>}
    {result && <section className="panel ds-details"><h3>{l('推論の変化を数値で見る', 'Inspect the inference numerically')}</h3>
      <Plot x={result.trace.map(row => row.step)} series={[{ name: l('観測との不一致（圧縮領域）', 'Observation mismatch (compressed domain)'), values: result.trace.map(row => row.encoded_residual), color: '#eee' }]} label={l('各反復のノイズ除去後の推定を評価', 'Denoised estimate evaluated at each iteration')} log={false} unit="" xLabel={l('反復', 'Iteration')} />
      <div className="ds-table"><table><thead><tr><th>{l('完了ステップ', 'Completed steps')}</th><th>σ</th><th>NRMSE / dB</th><th>Coherence</th></tr></thead><tbody>{result.checkpoints.map(point => <tr key={point.id}><td>{point.step}{point.stage === 'final_sample' ? ' ●' : ''}</td><td>{fmt(point.sigma, 4)}</td><td>{fmt(point.metrics.nrmse_db)}</td><td>{fmt(point.metrics.coherence, 4)}</td></tr>)}</tbody></table></div>
      <details><summary>{l('入力・音声・モデルの詳細', 'Input, audio and model details')}</summary><pre>{JSON.stringify({ configuration: result.configuration, input_sha256: result.input_sha256, audio: result.audio, model: result.model }, null, 2)}</pre></details>
    </section>}
  </section>;
}
