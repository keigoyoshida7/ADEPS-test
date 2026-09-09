'use client';
import { useEffect, useRef, useState } from 'react';
import { Download, Play, Square, ArrowRight, LoaderCircle, FileAudio, CircleHelp } from 'lucide-react';
import { useLanguage, useT } from './i18n';
import errorTranslations from './neural-errors.json';
import { analysisApi, cancelAnalysis, isLocalEngine, onAnalysisProgress, type AnalysisProgress } from './scientificClient';
import { Plot, fmt } from './Plots';
import { asset } from './assets';

type Result = Record<string, any>;
const defaults = { steps: 150, eta_prime: 50, seed: 42, regularization: .001,
  microphones: 6, radius_m: .06, snr_db: 50, data_seed: 2026, mismatch: false,
  coplanar: false, start_seconds: 0, duration_seconds: .4 };
function save(name: string, content: BlobPart, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const db = (value: number | null) => value === null ? null : 20 * Math.log10(Math.max(value, 1e-12));

export default function NeuralInference() {
  const language = useLanguage();
  const t = useT();
  const translatedError = (message: string) => language === 'jp' ? (errorTranslations as Record<string,string>)[message] || message : t(message);
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [mode, setMode] = useState<'demo' | 'stft' | 'audio'>('demo');
  const [config, setConfig] = useState(defaults);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false), [preparing, setPreparing] = useState(false);
  const [error, setError] = useState(''), [dirty, setDirty] = useState(false);
  const [progress, setProgress] = useState<AnalysisProgress>({ stage: 'ready' });
  const [elapsed, setElapsed] = useState(0);
  const selectedFile = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed((Date.now() - started) / 1000), 500);
    const unsubscribe = onAnalysisProgress(setProgress);
    return () => { clearInterval(timer); unsubscribe(); };
  }, [busy]);
  function update(key: keyof typeof defaults, value: number | boolean) {
    setConfig(c => ({ ...c, [key]: value })); setDirty(!!result);
  }
  async function run() {
    setBusy(true); setError(''); setElapsed(0); setProgress({ stage: 'runtime' });
    try {
      if (file && file.size > 32_000_000) throw new Error(l('入力は32 MBまでです。', 'Input limit: 32 MB.'));
      if (mode !== 'demo' && !file) throw new Error(l('入力ファイルを選んでください。', 'Choose an input file.'));
      const value = mode === 'audio'
        ? await analysisApi('neural-audio', config, await file!.arrayBuffer())
        : await analysisApi('neural', { ...config, ...(mode === 'stft' ? { bundle: JSON.parse(await file!.text()) } : {}) });
      setResult(value); setDirty(false);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function example(useNow: boolean) {
    setPreparing(true); setError('');
    try {
      const value = await analysisApi('neural-example', {});
      if (useNow) {
        setMode('audio'); setFile(new File([value.bytes], value.filename, { type: 'application/zip' }));
        setConfig(c => ({ ...c, start_seconds: 0, duration_seconds: .4 })); setDirty(!!result);
        if (selectedFile.current) selectedFile.current.value = '';
      } else save(value.filename, value.bytes, 'application/zip');
    } catch (e) { setError((e as Error).message); }
    finally { setPreparing(false); }
  }
  function number(key: keyof typeof defaults, jp: string, en: string, min: number, max: number, step: number) {
    return <label className="neural-field"><span>{l(jp, en)}</span><input aria-label={l(jp,en)} type="number" min={min} max={max} step={step}
      value={Number(config[key])} onChange={e => update(key, Number(e.target.value))} /></label>;
  }
  const linear = result?.quality.linear, neural = result?.quality.neural;
  const trace = result?.trace || [];
  const fraction = progress.step && progress.total ? progress.step / progress.total : 0;
  const stage = progress.stage === 'inference' ? l('拡散推論', 'Diffusion inference')
    : progress.stage === 'model' ? l('モデルを読み込み中', 'Loading the model')
    : l('計算を準備中', 'Preparing the analysis');

  return <div className="neural-page">
    <div className="neural-intro">
      <span className="eyebrow">INDEPENDENT NEURAL EXPERIMENT · 01</span>
      <h2>{l('観測から、空間の表現へ。', 'From observations to a spatial representation.')}</h2>
      <p>{l('論文の拡散推論式を、独自学習の小型モデルで試します。マイクの合成データ、保存したSTFT、短い録音区間を入力できます。',
        'Test the paper’s diffusion inference equations with an independently trained small model. Use synthetic observations, saved STFT data, or a short recorded segment.')}</p>
      <div className="neural-flow" aria-label={l('処理の流れ', 'Processing flow')}>
        {[l('マイク信号 ＋ 応答 V', 'Microphone signals + response V'), l('線形推定 E·p', 'Linear estimate E·p'),
          l('学習済みprior ＋ 観測との整合', 'Learned prior + observation consistency'), l('FOA・比較・書き出し', 'FOA · comparison · export')]
          .map((text, i) => <span key={text}><b>{String(i+1).padStart(2,'0')}</b>{text}{i < 3 && <ArrowRight size={15}/>}</span>)}
      </div>
    </div>
    <div className="note"><CircleHelp size={18}/><div>{l('同梱モデルは合成の空間係数で独自学習した小型MLPです。著者のNCSN++M・学習済み重みは未公開で、論文の音声・残響条件や性能を再現したものではありません。',
      'The bundled prior is a small MLP trained independently on synthetic spatial coefficients. The authors’ NCSN++M code and weights remain unreleased; this is not a reproduction of their speech, reverberation, or performance results.')}
      {' '}<a href={asset('/info/NEURAL_PROTOCOL.md')} target="_blank" rel="noreferrer">{l('実装と評価条件', 'Implementation and evaluation protocol')}</a></div></div>

    <div className="neural-workspace">
      <section className="panel neural-settings">
        <div className="panel-head"><h2>{l('入力と推論条件', 'Input and inference settings')}</h2><span>01 — INPUT</span></div>
        <fieldset disabled={busy || preparing}>
          <label className="neural-field"><span>{l('入力', 'Input')}</span><select aria-label={l('入力','Input')} value={mode} onChange={e => {
            setMode(e.target.value as typeof mode); setFile(null); setDirty(!!result);
            if (selectedFile.current) selectedFile.current.value = '';
          }}>
            <option value="demo">{l('合成データで試す・マイク不要', 'Synthetic data · no microphone needed')}</option>
            <option value="audio">{l('録音WAV ＋ アレイ情報 ZIP', 'Recorded WAV + array metadata ZIP')}</option>
            <option value="stft">{l('複素STFT ＋ V のJSON', 'Complex STFT + V JSON')}</option>
          </select></label>
          {mode === 'demo' ? <>
            <div className="neural-fields">
              <label className="neural-field"><span>{l('マイク数', 'Microphones')}</span><select aria-label={l('マイク数','Microphones')} value={config.microphones} onChange={e => update('microphones',Number(e.target.value))}>
                {[4,5,6,8,12,16].map(q => <option key={q}>{q}</option>)}</select></label>
              {number('radius_m','アレイ半径 / m','Array radius / m',.01,.25,.01)}
              {number('snr_db','観測SNR / dB','Observation SNR / dB',0,80,5)}
              {number('data_seed','合成データのseed','Synthetic data seed',0,4294967295,1)}
            </div>
            <label className="neural-check"><input type="checkbox" checked={config.mismatch} onChange={e => update('mismatch',e.target.checked)}/>{l('モデル不一致：真の音場15次 / 推論5次', 'Model mismatch: true field order 15 / prior order 5')}</label>
            <label className="neural-check"><input type="checkbox" checked={config.coplanar} onChange={e => update('coplanar',e.target.checked)}/>{l('マイクを同一平面に置く', 'Place microphones in one plane')}</label>
            <p className="neural-small">{l('32周波数 × 16フレーム。ランダムな平面波の複素係数で、録音や発話ではありません。', '32 frequencies × 16 frames of random plane-wave complex spectra, not recordings or speech.')}</p>
          </> : <>
            <input ref={selectedFile} aria-label={l('入力ファイル', 'Input file')} type="file" accept={mode === 'audio' ? '.zip' : '.json'} onChange={e => { setFile(e.target.files?.[0] || null); setDirty(!!result); }}/>
            {file && <p className="neural-small">{file.name} · {(file.size/1e6).toFixed(2)} MB</p>}
            {mode === 'audio' ? <>
              <div className="neural-fields">{number('start_seconds','開始時刻 / 秒','Start / seconds',0,36000,.1)}{number('duration_seconds','区間長 / 秒','Segment / seconds',.02,5,.05)}</div>
              <p className="neural-small">{l('ZIPの直下に microphones.wav と array.json。任意で同期した reference.wav。既定は16 kHz・0.4秒。周波数×時間は8192点までです。',
                'Place microphones.wav and array.json at the ZIP root, optionally with synchronized reference.wav. Default: 16 kHz, 0.4 s. Maximum 8192 frequency-time bins.')}</p>
            </> : <p className="neural-small">{l('adeps-test-array-stft/1。V=[F,Q,36]、p=[F,Q,T]、real ACN/N3D。4係数だけのVは使用できません。',
              'adeps-test-array-stft/1. V=[F,Q,36], p=[F,Q,T], real ACN/N3D. A V with only four coefficients is not sufficient.')}</p>}
          </>}
          <div className="neural-fields">
            {number('steps','反復回数','Iterations',2,300,1)}
            {number('eta_prime','観測整合性の強さ η′','Consistency strength η′',0,1000,1)}
            {number('seed','推論のseed','Inference seed',0,4294967295,1)}
            {number('regularization','相対正則化','Relative regularization',.00000001,10,.001)}
          </div>
          <p className="neural-small">{l('150回・α=.67・β=3・σ=20→.002・ρ=10は論文を参照。η′=50、相対正則化、最後のσ=0、入出力のレベル規約は独自の選択です。η′の効き方はデータのサイズにも依存します。',
            '150 iterations, α=.67, β=3, σ=20→.002 and ρ=10 follow the paper. η′=50, relative regularization, terminal σ=0 and signal scaling are independent choices. The effect of η′ also depends on input size.')}</p>
        </fieldset>
        <div className="neural-actions"><button className="primary" onClick={run} disabled={busy || preparing || (mode !== 'demo' && !file)}>{busy ? <LoaderCircle size={16} className="spin"/> : <Play size={16}/>} {l('推論して比較する', 'Run inference and compare')}</button>
          {busy && !isLocalEngine && <button onClick={cancelAnalysis}><Square size={14}/>{l('中止', 'Stop')}</button>}</div>
        {busy && <div className="neural-progress" role="status" aria-live="polite"><progress value={fraction} max={1}/><span>{stage} · {progress.step || 0} / {config.steps} · {fmt(elapsed,1)} s</span></div>}
        {error && <div className="error" role="alert">{translatedError(error)}</div>}
        <div className="neural-actions"><button disabled={busy || preparing} onClick={() => example(true)}><FileAudio size={15}/>{l('合成WAV例を選ぶ', 'Use synthetic WAV example')}</button>
          <button disabled={busy || preparing} onClick={() => example(false)}><Download size={15}/>{l('入力ZIPの例', 'Example input ZIP')}</button></div>
        <a className="neural-small" href={asset('/examples/array-audio-template.json')} download>{l('自分のマイク用 array.json テンプレート', 'array.json template for your microphone array')}</a>
      </section>

      <section className="panel neural-results">
        <div className="panel-head"><h2>{l('同じ観測からの比較', 'Compare the same observations')}</h2><span>02 — RESULTS</span></div>
        {dirty && <div className="note">{l('条件が変わりました。表示は前回の結果です。再実行すると更新されます。', 'Settings changed. These are the previous results; run again to update.')}</div>}
        {!result ? <div className="neural-empty"><span>â</span><h3>{l('まず合成データで動作を確認', 'Start with the synthetic data')}</h3><p>{l('「推論して比較する」で計算します。マイクは不要です。結果には使用した重みと条件、線形処理との違いを保存します。',
          'Select “Run inference and compare.” No microphone is needed. Results record the weights, settings and difference from linear encoding.')}</p></div> : <>
          <div className="neural-result-caption"><span>{result.microphones} MIC · {result.frequencies_hz.length} FREQ · {result.frames} FRAME</span><span>{fmt(result.diagnostics.elapsed_seconds,2)} s</span></div>
          <div className="neural-comparison">
            <div><span>{l('線形エンコーダ', 'Linear encoder')}</span><strong>{fmt(linear.nrmse_db)}<small> dB</small></strong><p>{l('FOAの複素NRMSE・小さいほど良い', 'FOA complex NRMSE · lower is better')}</p><span>Coherence {fmt(linear.coherence,3)}</span></div>
            <div><span>{l('独自モデル ＋ 拡散推論', 'Independent model + diffusion')}</span><strong>{fmt(neural.nrmse_db)}<small> dB</small></strong><p>{l('FOAの複素NRMSE・小さいほど良い', 'FOA complex NRMSE · lower is better')}</p><span>Coherence {fmt(neural.coherence,3)}</span></div>
          </div>
          {neural.nrmse_db != null && linear.nrmse_db != null ? <p className="neural-verdict">{neural.nrmse_db < linear.nrmse_db
            ? l('この試行では拡散推論の誤差が小さくなりました。', 'Diffusion produced a lower error in this run.')
            : l('この試行では拡散推論の誤差が大きくなりました。', 'Diffusion produced a higher error in this run.')}
            {' '}{l('差', 'Difference')} {fmt(Math.abs(neural.nrmse_db-linear.nrmse_db))} dB</p>
            : <div className="note">{l('対応する参照信号がないため、復元品質の誤差やcoherenceは未算出です。観測との残差だけで品質を判断できません。',
              'Without an aligned reference, reconstruction error and coherence cannot be calculated. Observation residual alone does not establish quality.')}</div>}
          {neural.si_sdr && <p>{l('時間信号のSI-SDR：線形', 'Waveform SI-SDR: linear')} {fmt(linear.si_sdr?.mean_valid_channels_db)} → {fmt(neural.si_sdr?.mean_valid_channels_db)} dB</p>}
          {result.rank_deficient_bins > 0 && <div className="note">{l('FOAを識別するランクが不足する周波数があります。DCや同一平面の配置も確認してください。',
            'Some frequencies do not have full FOA rank. Check DC and coplanar geometry.')}{' '}{result.rank_deficient_bins} / {result.frequencies_hz.length}</div>}
          {linear.reference_available && <Plot x={result.frequencies_hz} log={result.frequencies_hz[0] > 0} xLabel="Hz"
            series={[{ name:l('線形','Linear'), values:linear.error_db_by_frequency, color:'#999', dash:true },
              { name:l('拡散推論','Diffusion'), values:neural.error_db_by_frequency, color:'#f5f5f5' }]}
            label={l('周波数ごとのFOA誤差・小さいほど良い', 'FOA error by frequency · lower is better')}/>}
          {linear.reference_available && <details><summary>{l('周波数ごとのcoherenceを見る', 'Inspect coherence by frequency')}</summary><Plot x={result.frequencies_hz} log={result.frequencies_hz[0] > 0} xLabel="Hz" unit=""
            series={[{ name:l('線形','Linear'), values:linear.coherence_by_frequency, color:'#999', dash:true },
              { name:l('拡散推論','Diffusion'), values:neural.coherence_by_frequency, color:'#f5f5f5' }]}
            label={l('Coherence・大きいほど良い', 'Coherence · higher is better')}/></details>}
          <div className="neural-actions"><button onClick={() => {
            const { bytes, ...data } = result;
            save('ADEPS_test_neural_result.json', JSON.stringify(data, null, 2));
          }}><Download size={15}/>{l('結果・条件 JSON', 'Result + settings JSON')}</button>
            {result.bytes && <button onClick={() => save(result.filename, result.bytes, 'application/zip')}><Download size={15}/>{l('比較用FOA WAV一式', 'FOA WAV comparison bundle')}</button>}</div>
          {result.audio && <p className="neural-small">{l('W,Y,Z,Xの4ch。N3D・SN3D両方を保存します。全WAVに共通のゲインを適用。スピーカー再生には同じ設定のAmbisonicsデコーダを使って比較してください。',
            'Four channels: W,Y,Z,X. Both N3D and SN3D files are exported with a shared gain. Compare using the same Ambisonics decoder and playback settings.')}
            {' '}{l('共通ゲイン', 'Shared gain')}: {fmt(result.audio.shared_export_gain,4)}</p>}
        </>}
      </section>
    </div>

    {result && <section className="panel neural-trace">
      <div className="panel-head"><div><h2>{l('反復の中で何が変わったか', 'What changed during inference')}</h2><p>{l('各反復のdenoiser出力に対する圧縮領域の残差です。最終出力の残差は別に示します。',
        'The trace evaluates each iteration’s denoiser output in the compressed domain. The final output residual is shown separately.')}</p></div><span>03 — TRACE</span></div>
      <Plot x={trace.map((row: Result) => row.step)} log={false} xLabel={l('反復回数', 'Iteration')} label={l('反復回数 / 圧縮観測との相対残差', 'Iteration / relative encoded-observation residual')}
        series={[{ name:'‖𝓗(EV𝓗⁻¹(Dθ)) − y‖ / ‖y‖', values:trace.map((row: Result) => db(row.encoded_residual)), color:'#eee' }]}/>
      <div className="neural-result-caption"><span>{l('最終出力の圧縮残差', 'Final encoded residual')}: {fmt(result.diagnostics.final_encoded_residual,5)}</span><span>{l('マイク領域の相対残差：線形 → 推論', 'Microphone residual: linear → diffusion')}: {fmt(result.diagnostics.linear_microphone_residual,4)} → {fmt(result.diagnostics.neural_microphone_residual,4)}</span></div>
      <details><summary>{l('反復ごとの数値をすべて見る', 'Inspect every iteration')}</summary><div className="table-scroll neural-step-table"><table><thead><tr>
        {['Step','σ','Residual','‖gradient‖','‖prior update‖','‖guidance update‖'].map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>
        {trace.map((row: Result) => <tr key={row.step}><td>{row.step}</td><td>{fmt(row.sigma,4)}</td><td>{fmt(row.encoded_residual,5)}</td><td>{fmt(row.gradient_norm,4)}</td><td>{fmt(row.prior_update_norm,4)}</td><td>{fmt(row.guidance_update_norm,4)}</td></tr>)}
      </tbody></table></div></details>
      <details><summary>{l('使用したモデルと再現条件', 'Model and reproducibility record')}</summary><p>{result.model.architecture}</p><p>{result.model.parameter_count.toLocaleString()} parameters · {result.model.training.steps} training steps</p>
        <p>{l('入力の出典', 'Input provenance')}: {result.provenance}</p><p className="neural-hash">Weights SHA-256: {result.model.weights_sha256}<br/>Input SHA-256: {result.input_sha256}</p>
        <a href={asset('/models/tiny-spatial-v1.json')} target="_blank" rel="noreferrer">{l('学習記録・検証値を開く', 'Open the training record and validation values')}</a></details>
    </section>}
    <section className="panel neural-field-guide"><div className="panel-head"><h2>{l('現場で試すときの順序', 'Taking the experiment to a venue')}</h2><span>04 — FIELD TEST</span></div>
      <ol><li>{l('合成データと入力ZIP例で、推論・保存・線形との比較が動くことを確認します。', 'Verify inference, exports and the linear comparison with synthetic data and the example ZIP.')}</li>
        <li>{l('4本以上の同期したマイク信号と、各チャンネルに対応するアレイ応答Vを用意します。無指向性の自由空間モデルを使う場合は、配列の原点からのXYZ座標を明示します。機器の筐体・指向性を含む実測Vとは区別します。',
          'Provide at least four synchronized microphone signals and the matching array response V. If using the omnidirectional freefield model, specify XYZ positions relative to the array origin. This model does not include measured device housing or directivity effects.')}</li>
        <li>{l('短い区間をオフラインで処理し、WAV一式と条件を保存します。同じ録音に対してseedやη′を変え、結果が安定するか確認します。',
          'Process a short segment offline and save the WAVs and settings. Vary the seed and η′ for the same recording to examine stability.')}</li>
        <li>{l('FOAをMax / Spatなどの同じデコーダに通し、線形と推論を同じ音量で聴き比べます。FOAの4係数を、そのまま4台のスピーカーへ割り当てないでください。',
          'Decode FOA through the same Max / Spat or other decoder and compare at matched levels. The four FOA coefficients are not direct feeds for four loudspeakers.')}</li></ol>
      <p>{l('録音済みのアレイ信号とVがあれば、推論時にマイクをつなぐ必要はありません。スピーカーのIR測定用マイク1本だけでは、同時刻のアレイ観測を置き換えられません。',
        'With saved array signals and V, no microphone needs to be connected during inference. A single microphone used for loudspeaker IR measurement does not replace simultaneous array observations.')}</p>
      <a href={asset('/info/NEURAL_PROTOCOL.md')} target="_blank" rel="noreferrer">{l('データ形式・数式・引用・制約を読む', 'Read the data formats, equations, citations and limits')}</a>
    </section>
  </div>;
}
