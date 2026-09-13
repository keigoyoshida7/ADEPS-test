import { useEffect, useId, useState } from 'react';
import { ArrowRight, Download, ExternalLink, RefreshCw } from 'lucide-react';
import { asset } from './assets';
import { fmt, Plot } from './Plots';
import PlusAudition from './PlusAudition';
import PlusProgress from './PlusProgress';
import PaperComparison from './PaperComparison';
import './ADEPSPlus.css';

type Value = number | null;
type Metric = { nrmse_db: Value; non_dc_nrmse_db: Value; speech_band_nrmse_db: Value; magnitude_error_db: Value; coherence: Value; si_sdr_db: Value };
type Curve = { nrmse_db: Value[]; magnitude_spectrum_error_db: Value[]; magnitude_squared_coherence: Value[] };
type Method = { id: string; label_jp: string; label_en: string; kind: string; mean_nrmse_db: Value; mean_seconds: Value; nfe: Value };
type Comparison = { baseline: string; mean_gain_db: Value; ci_low_db: Value; ci_high_db: Value; wins: number; count: number; passed: boolean };
export type PlusBenchmark = {
  schema: 'adeps-plus-benchmark/1'; status: 'evaluated'; title_jp: string; title_en: string;
  conditions: { scenes: number; clusters: number; microphones: number; radius_m: number; snr_db: number; sample_rate_hz: number };
  methods: Method[]; comparisons: Comparison[];
  scenes: { id: string; cluster_id: string; metrics: Record<string, Metric>; curves?: Record<string, Curve> }[];
  frequencies_hz: number[]; curves: Record<string, Curve>; selection: Record<string, unknown>; provenance: Record<string, unknown>;
  sources: { title: string; url: string }[]; limitations_jp: string[]; limitations_en: string[]; example_url?: string;
};
type Load = { state: 'loading' | 'unavailable' | 'invalid' } | { state: 'ready'; report: PlusBenchmark; sha256: string };
const REPORT = 'models/plus-benchmark.json';
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const numeric = (value: unknown): value is Value => value === null || finite(value);
const count = (value: unknown): value is number => finite(value) && Number.isInteger(value) && value >= 0;
const positive = (value: unknown): value is number => finite(value) && value > 0;
const text = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
const object = (value: unknown) => value !== null && typeof value === 'object' && !Array.isArray(value);
const texts = (value: unknown): value is string[] => Array.isArray(value) && value.every(text);
const sameNumber = (a: Value, b: Value) => a === null || b === null ? a === b : Math.abs(a - b) < 1e-5;
const https = (value: unknown): value is string => {
  if (!text(value)) return false;
  try { const url = new URL(value); return url.protocol === 'https:' && !url.username && !url.password; } catch { return false; }
};
const mean = (values: Value[]): Value => values.every(finite) ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
const signed = (value: Value, digits = 3) => value === null ? '—' : `${value > 0 ? '+' : ''}${fmt(value, digits)}`;
const difference = (baseline: Value, estimate: Value): Value => baseline === null || estimate === null ? null : baseline - estimate;
const hz = (value: number) => value >= 1000 ? `${Number((value / 1000).toFixed(5))} kHz` : `${Number(value.toFixed(5))} Hz`;
const styles = [{ color: '#f5f5f5' }, { color: '#bbb', dash: '8 5' }, { color: '#888', dash: '2 5' }, { color: '#ddd', dash: '10 4 2 4' }, { color: '#999', dash: '4 3' }, { color: '#eee', dash: '14 5' }, { color: '#aaa', dash: '1 3' }, { color: '#ccc', dash: '6 3 1 3' }, { color: '#999', dash: '12 3 3 3' }];
const metricKeys = ['nrmse_db', 'non_dc_nrmse_db', 'speech_band_nrmse_db', 'magnitude_error_db', 'coherence', 'si_sdr_db'] as const;
const curveKeys = ['nrmse_db', 'magnitude_spectrum_error_db', 'magnitude_squared_coherence'] as const;

/** Reject incomplete, nonfinite or internally inconsistent result records. */
export function validPlusBenchmark(input: unknown): input is PlusBenchmark {
  if (!object(input)) return false;
  const r = input as PlusBenchmark;
  if (r.schema !== 'adeps-plus-benchmark/1' || r.status !== 'evaluated' || !text(r.title_jp) || !text(r.title_en)
    || !object(r.conditions) || !object(r.selection) || !object(r.provenance)) return false;
  const c = r.conditions;
  if (![c.scenes, c.clusters, c.microphones, c.sample_rate_hz].every(v => count(v) && v > 0) || c.sample_rate_hz !== 16000
    || c.clusters > c.scenes || !positive(c.radius_m) || !finite(c.snr_db)) return false;
  if (!Array.isArray(r.methods) || r.methods.length < 3 || r.methods.length > 12
    || !r.methods.every(m => object(m) && [m.id, m.label_jp, m.label_en, m.kind].every(text)
      && numeric(m.mean_nrmse_db) && (m.mean_seconds === null || finite(m.mean_seconds) && m.mean_seconds >= 0)
      && (m.nfe === null || count(m.nfe))) || r.methods.filter(m => m.kind === 'plus').length !== 1) return false;
  const ids = r.methods.map(m => m.id), plus = r.methods.find(m => m.kind === 'plus')!;
  if (new Set(ids).size !== ids.length || !Array.isArray(r.frequencies_hz) || r.frequencies_hz.length !== 257
    || r.frequencies_hz[0] !== 0 || !r.frequencies_hz.every((f, i) => finite(f) && Math.abs(f - i * 31.25) < 1e-6)
    || Math.abs(r.frequencies_hz.at(-1)! - c.sample_rate_hz / 2) > 1e-6) return false;
  const validCurves = (curves: Record<string, Curve>) => object(curves) && ids.every(id => object(curves[id])
    && curveKeys.every(key => Array.isArray(curves[id][key]) && curves[id][key].length === r.frequencies_hz.length
      && curves[id][key].every(v => numeric(v) && (v === null || key === 'nrmse_db' || v >= 0 && (key !== 'magnitude_squared_coherence' || v <= 1)))));
  if (!validCurves(r.curves) || !Array.isArray(r.scenes) || r.scenes.length !== c.scenes
    || !r.scenes.every(s => object(s) && text(s.id) && text(s.cluster_id) && object(s.metrics)
      && ids.every(id => object(s.metrics[id]) && metricKeys.every(key => numeric(s.metrics[id][key]))
        && (s.metrics[id].magnitude_error_db === null || s.metrics[id].magnitude_error_db >= 0)
        && (s.metrics[id].coherence === null || s.metrics[id].coherence >= 0 && s.metrics[id].coherence <= 1))
      && (s.curves === undefined || validCurves(s.curves)))) return false;
  if (new Set(r.scenes.map(s => s.id)).size !== c.scenes || new Set(r.scenes.map(s => s.cluster_id)).size !== c.clusters
    || r.methods.some(m => !sameNumber(m.mean_nrmse_db, mean(r.scenes.map(s => s.metrics[m.id].nrmse_db))))) return false;
  if (!Array.isArray(r.comparisons) || r.comparisons.length < 2 || new Set(r.comparisons.map(b => b?.baseline)).size !== r.comparisons.length
    || !r.comparisons.every(b => {
      if (!object(b) || !ids.includes(b.baseline) || b.baseline === plus.id || b.count !== c.scenes || !count(b.wins) || b.wins > b.count
        || ![b.mean_gain_db, b.ci_low_db, b.ci_high_db].every(numeric) || typeof b.passed !== 'boolean'
        || (b.ci_low_db === null) !== (b.ci_high_db === null)
        || (b.ci_low_db !== null && b.ci_high_db !== null && b.ci_low_db > b.ci_high_db)) return false;
      const deltas = r.scenes.map(s => difference(s.metrics[b.baseline].nrmse_db, s.metrics[plus.id].nrmse_db));
      return sameNumber(b.mean_gain_db, mean(deltas)) && b.wins === deltas.filter(v => v !== null && v > 0).length
        && b.passed === (b.mean_gain_db !== null && b.mean_gain_db >= .5 && b.ci_low_db !== null && b.ci_low_db > 0 && deltas.every(finite));
    })) return false;
  return Array.isArray(r.sources) && r.sources.every(s => object(s) && text(s.title) && https(s.url))
    && texts(r.limitations_jp) && texts(r.limitations_en) && (r.example_url === undefined || text(r.example_url));
}

function downloadSceneCsv(report: PlusBenchmark) {
  const rows: (string | Value)[][] = [['scene_id', 'cluster_id', 'method_id', ...metricKeys]];
  for (const scene of report.scenes) for (const method of report.methods) {
    rows.push([scene.id, scene.cluster_id, method.id, ...metricKeys.map(key => scene.metrics[method.id][key])]);
  }
  const csv = '\uFEFF' + rows.map(row => row.map(v => v === null ? '' : `"${String(v).replaceAll('"', '""')}"`).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = 'ADEPS-plus-all-scenes.csv'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function ADEPSPlus({ language, active = true, onNavigate }: { language: 'jp' | 'en'; active?: boolean; onNavigate: (page: string) => void }) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [load, setLoad] = useState<Load>({ state: 'loading' });
  const [revision, setRevision] = useState(0);
  const [sceneId, setSceneId] = useState('');
  const [frequency, setFrequency] = useState(1000);
  const [curveScope, setCurveScope] = useState<'aggregate' | 'scene'>('aggregate');
  const [visibleMethods, setVisibleMethods] = useState(['plus', 'linear_tuned', 'adeps_current', 'plus_no_denoiser']);
  const frequencyId = useId(), sceneSelectId = useId();
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void fetch(asset(REPORT), { cache: 'no-store', signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('unavailable');
      const raw = await response.text();
      const value: unknown = JSON.parse(raw);
      const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw))))
        .map(v => v.toString(16).padStart(2, '0')).join('');
      if (!controller.signal.aborted) setLoad(validPlusBenchmark(value) ? { state: 'ready', report: value, sha256 } : { state: 'invalid' });
    }).catch(() => { if (!controller.signal.aborted) setLoad({ state: 'unavailable' }); });
    return () => controller.abort();
  }, [active, revision]);
  const report = load.state === 'ready' ? load.report : null;
  const selected = report?.scenes.find(s => s.id === sceneId) ?? report?.scenes[0];
  const plus = report?.methods.find(m => m.kind === 'plus');
  const name = (method: Method) => l(method.label_jp, method.label_en);
  const curveData = report && selected ? curveScope === 'scene' && selected.curves ? selected.curves : report.curves : null;
  const actualScope = curveScope === 'scene' && selected?.curves ? 'scene' : 'aggregate';
  const frequencyIndex = report ? report.frequencies_hz.reduce((best, f, i, all) => Math.abs(f - frequency) < Math.abs(all[best] - frequency) ? i : best, 0) : 0;
  const bestMean = report ? Math.min(...report.methods.flatMap(m => m.mean_nrmse_db === null ? [] : [m.mean_nrmse_db])) : null;
  const primary = report?.comparisons.filter(c => ['linear_tuned', 'adeps_current'].includes(c.baseline)) ?? [];
  const primaryPassed = primary.length === 2 && primary.every(c => c.passed);
  const withoutDenoiser = report?.methods.find(m => m.id === 'plus_no_denoiser');
  const denoiserGain = plus && withoutDenoiser ? difference(withoutDenoiser.mean_nrmse_db, plus.mean_nrmse_db) : null;
  const ordered = report ? [...report.methods.filter(m => m.kind === 'plus'), ...report.methods.filter(m => m.kind !== 'plus')] : [];
  const series = (key: keyof Curve) => ordered.flatMap((m, i) => visibleMethods.includes(m.id) ? [{ name: name(m), values: curveData![m.id][key], ...styles[i % styles.length] }] : []);
  const positiveFrequencies = report?.frequencies_hz.filter(f => f >= 1 && f <= 20000) ?? [];
  const phases = [
    [l('理想音場', 'Ideal field'), l('音声＋独立した部屋', 'Speech + separate rooms')],
    [l('同じ仮想観測', 'Same observation'), 'p = Va + noise'],
    [l('3系統で復元', 'Reconstruct'), 'Linear / ADEPS / + α'],
    [l('未使用データで比較', 'Held-out comparison'), l('全場面・全帯域', 'Every scene, full band')],
  ];
  return <article className="adeps-plus">
    <header className="ap-intro"><span className="eyebrow">ADEPS + α / INDEPENDENT BENCHMARK</span>
      <h2>{l('復元の違いを、精度で確かめる。', 'Measure what the reconstruction changes.')}</h2>
      <p>{l('Linear、独自ADEPS、改善方法を同じ観測から比較します。平均の改善だけでなく、悪化した場面と結果の不確実性まで記録します。',
        'Compare Linear, our independent ADEPS and the proposed improvement on identical observations. Inspect regressions and uncertainty alongside average gains.')}</p>
      <div className="ap-toolbar"><span>{l('計算済みの評価記録を表示', 'Saved evaluation results')}</span><button type="button" disabled={load.state === 'loading'} onClick={() => { setLoad({ state: 'loading' }); setRevision(v => v + 1); }}><RefreshCw size={14}/>{l('再読込', 'Reload')}</button></div>
    </header>
    <ol className="ap-flow" aria-label={l('比較までの工程', 'Evaluation flow')}>{phases.map(([title, detail], i) => <li key={title}><span className="ap-step-number">0{i + 1}</span><div><strong>{title}</strong><small>{detail}</small></div>{i < phases.length - 1 && <ArrowRight size={16} aria-hidden="true"/>}</li>)}</ol>
    <p className="ap-scope">{l('原著ADEPSの公式モデルや公表精度を再現した評価ではありません。原著を上回ったかは未確認です。ここでの値は合成音声の復元誤差で、実会場の測定値ではありません。',
      'This does not reproduce the authors’ official model or benchmark. Outperforming the original paper is unverified. Scores describe synthetic reconstruction, not venue measurements.')}</p>
    <details className="ap-details ap-method-explanation"><summary>{l('＋αで何を加えたか', 'What the additional processing does')}</summary>
      <ol className="ap-method-steps">
        <li><strong>{l('方向を探す', 'Find directions')}</strong><p>{l('同じ仮想マイク信号から、主な音の方向を最大2つ推定します。正解の方向は渡しません。', 'Estimate up to two dominant directions from the same microphone signals. Ground-truth directions are not supplied.')}</p></li>
        <li><strong>{l('復元の初期値を作る', 'Build an initial reconstruction')}</strong><p>{l('推定した方向と広がる音の成分を使って、Wiener法で音場を復元します。', 'Use the estimated directions and a diffuse component to reconstruct the field with Wiener filtering.')}</p></li>
        <li><strong>{l('学習済みモデルで少しずつ調整する', 'Refine with the trained model')}</strong><p>{l('既存の30.78Mモデルのノイズ除去結果を混ぜながら、観測との一致とSTFTの整合性を保ちます。モデルOFFでは、このノイズ除去だけを外します。', 'Blend denoising from the existing 30.78M model while enforcing measurement and STFT consistency. The model-OFF control skips only the denoising contribution.')}</p></li>
        <li><strong>{l('波形の整合性を仕上げる', 'Finish waveform consistency')}</strong><p>{l('重なった時間区間が同じ波形を表すように再調整します。最後に、未使用の正解音場と全手法を同じ条件で比較します。', 'Reconcile overlapping time windows so they represent a consistent waveform. Evaluate every method against the same held-out reference.')}</p></li>
      </ol><p className="ap-note">{l('これは論文に着想を得た独自の復元手順です。元のADEPSと同じ拡散サンプラーではありません。ニューラル重みは追加学習せず、開発データで処理の設定を選んでいます。', 'This is an independently designed, paper-inspired reconstruction procedure, not the original ADEPS sampler. Neural weights are frozen; processing settings are selected on development data.')}</p>
      <div className="ap-links"><a href={asset('info/PLUS_METHODS.md')}>{l('方法・参照論文の詳細', 'Methods and references')}</a><a href={asset('info/PLUS_PROTOCOL.md')}>{l('事前の評価計画', 'Prospective evaluation protocol')}</a><a href={asset('info/PLUS_USAGE.md')}>{l('自分の入力で実行する', 'Run on your own input')}</a></div>
    </details>
    <PlusProgress language={language} active={active}/>
    {!report && <section className="ap-empty" aria-live="polite"><span className="eyebrow">{load.state === 'loading' ? 'LOADING' : 'NO VERIFIED RESULT'}</span>
      <h3>{load.state === 'loading' ? l('比較記録を読み込んでいます。', 'Loading the comparison record.') : load.state === 'invalid' ? l('評価記録の整合性を確認できませんでした。', 'The evaluation record could not be verified.') : l('評価結果は、まだ読み込めません。', 'Evaluation results are not available yet.')}</h3>
      <p>{load.state === 'invalid' ? l('数値・場面数・曲線・集計の対応を確認してから表示します。再読込しても変わらない場合は、記録の書き出しを確認してください。', 'Numbers, scene counts, curves and summaries must agree before display. If reloading does not help, check the exported record.')
        : l('計算が完了し、実際の評価ファイルが用意されると、このページに比較表と周波数の図が表示されます。ページを開くだけでは計算は始まりません。', 'Tables and frequency plots appear when an actual evaluation file is ready. Opening this page does not start computation.')}</p></section>}
    {report && selected && plus && curveData && <>
      <PaperComparison language={language} active={active} original={report} sourceSha256={load.state === 'ready' ? load.sha256 : ''}/>
      <section className="ap-section"><header className="ap-section-heading"><span className="eyebrow">01 / OVERVIEW</span><h3>{l(report.title_jp, report.title_en)}</h3></header>
        <div className="ap-verdict"><strong>{primaryPassed ? l('事前に決めた2つの主比較を達成', 'Both predefined primary comparisons passed') : l('主比較の達成は未確認', 'Primary success has not been established')}</strong><p>{l('主比較は、調整済みLinearと現在の独自ADEPSに対する誤差の改善です。下の他の比較は、各処理の効果を分けて調べるためにも掲載しています。', 'The primary comparisons test error reduction against tuned Linear and the current independent ADEPS. Other comparisons below also isolate the contribution of each processing step.')}</p></div>
        {withoutDenoiser && <div className="ap-ablation"><strong>{l('学習済みモデル自体の寄与', 'Contribution of the trained denoiser')}</strong><p>{denoiserGain === null ? l('比較できる値が揃っていません。', 'Comparable values are unavailable.') : denoiserGain > 0 ? l(`同じ処理のモデルOFFに対して、ONの平均誤差は ${fmt(denoiserGain, 3)} dB 改善しました。`, `Against the same processing with the model OFF, ON improved mean error by ${fmt(denoiserGain, 3)} dB.`) : denoiserGain < 0 ? l(`同じ処理では、モデルOFFの方が平均誤差で ${fmt(-denoiserGain, 3)} dB 良好でした。この試験で、学習済みモデルの追加が精度を上げたとは言えません。`, `With otherwise identical processing, model OFF achieved ${fmt(-denoiserGain, 3)} dB lower mean error. This test does not establish a benefit from adding the trained denoiser.`) : l('同じ処理のモデルONとOFFで、平均誤差は同じでした。この指標では学習済みモデルを加える利益は確認できません。', 'With otherwise identical processing, model ON and OFF have equal mean error. This metric shows no benefit from adding the trained denoiser.')}</p></div>}
        <dl className="ap-conditions"><div><dt>{l('評価場面', 'Scenes')}</dt><dd>{report.conditions.scenes}</dd></div><div><dt>{l('話者ペア群', 'Speaker-pair clusters')}</dt><dd>{report.conditions.clusters}</dd></div><div><dt>{l('仮想マイク', 'Virtual array')}</dt><dd>{report.conditions.microphones}<small> ch / {report.conditions.radius_m * 100} cm</small></dd></div><div><dt>{l('観測SNR', 'Observation SNR')}</dt><dd>{report.conditions.snr_db}<small> dB</small></dd></div></dl>
        <div className="ap-table-wrap"><table><caption>{l('全帯域の場面平均NRMSE。低いほど誤差が小さい。—は未定義・未計測です。', 'Mean per-scene full-band NRMSE. Lower is better. A dash means undefined or unmeasured.')}</caption><thead><tr><th scope="col">{l('方法', 'Method')}</th><th scope="col">NRMSE <small>dB</small></th><th scope="col">{l('平均計算時間', 'Mean runtime')}</th><th scope="col">{l('モデル評価回数', 'Model evaluations')}</th></tr></thead><tbody>{report.methods.map(m => <tr key={m.id} data-plus={m.kind === 'plus'}><th scope="row">{name(m)}{m.mean_nrmse_db !== null && m.mean_nrmse_db === bestMean && <small className="ap-best">{l('この比較で平均誤差が最小', 'Lowest mean error in this comparison')}</small>}</th><td>{fmt(m.mean_nrmse_db, 4)}</td><td>{m.mean_seconds !== null && m.mean_seconds < .1 ? `${fmt(m.mean_seconds * 1000, 2)} ms` : `${fmt(m.mean_seconds, 2)} s`}</td><td>{fmt(m.nfe, 0)}</td></tr>)}</tbody></table></div>
        <p className="ap-note">{l('DCを含む全周波数・FOA 4chの複素誤差を、出力ゲインを掛ける前に評価。各場面のdB値を等しく平均します。モデル評価回数だけでは、勾配計算を含む実行コストを表しません。', 'Complex error over every frequency, including DC, and all four FOA channels before output gain; per-scene dB values receive equal weight. Model-evaluation counts alone do not capture gradient-computation cost.')}</p>
        <div className="ap-comparisons">{report.comparisons.map(comparison => {
          const baseline = report.methods.find(m => m.id === comparison.baseline)!;
          const deltas = report.scenes.map(s => difference(s.metrics[baseline.id].nrmse_db, s.metrics[plus.id].nrmse_db));
          const losses = deltas.filter(v => v !== null && v < 0).length, ties = deltas.filter(v => v === 0).length, missing = deltas.filter(v => v === null).length;
          return <article key={baseline.id} className="ap-comparison"><span>{name(plus)} / {name(baseline)}</span><h4>{signed(comparison.mean_gain_db)} <small>dB</small></h4>
            <p>{l('平均改善量', 'Mean improvement')} · {comparison.passed ? l('この比較の基準を達成', 'Criterion met for this comparison') : comparison.mean_gain_db === null || comparison.ci_low_db === null ? l('判定不能', 'Not assessable') : l('この比較の基準は未達', 'Criterion not met for this comparison')}</p>
            <div className="ap-ci"><span>97.5% {l('区間', 'interval')}</span><strong>{signed(comparison.ci_low_db)} — {signed(comparison.ci_high_db)} dB</strong></div>
            <p className="ap-counts">{l('改善', 'Improved')} {comparison.wins} / {l('悪化', 'Worse')} {losses} / {l('同値', 'Tied')} {ties} / {l('未定義', 'Undefined')} {missing}<br/>{l('全', 'Total')} {comparison.count} {l('場面', 'scenes')}</p></article>;
        })}</div>
        <p className="ap-note">{l('改善量＝baselineの誤差 − ADEPS + αの誤差。正なら改善、負なら悪化。2つの主比較の事前基準は全帯域0.5 dB以上の改善と区間下端>0 dBです。他の比較にも同じ数値基準を表示します。場面を同じ話者ペアごとにまとめた区間で、少数の話者群では不確実性が大きく残ります。', 'Gain = baseline error − ADEPS + α error. Positive is better; negative is worse. The two primary comparisons require at least 0.5 dB full-band gain and an interval lower endpoint above zero; the same numerical threshold is shown for the other comparisons. Intervals retain speaker-pair groups; few groups leave substantial uncertainty.')}</p>
      </section>
      <section className="ap-section"><header className="ap-section-heading"><span className="eyebrow">02 / EVERY SCENE</span><h3>{l('どの場面で、何が変わったか。', 'See what changes in every scene.')}</h3></header>
        <div className="ap-controls"><label htmlFor={sceneSelectId}>{l('詳細を見る場面', 'Inspect scene')}</label><select id={sceneSelectId} value={selected.id} onChange={e => setSceneId(e.target.value)}>{report.scenes.map(s => <option key={s.id} value={s.id}>{s.id} · {s.cluster_id}</option>)}</select><button type="button" onClick={() => downloadSceneCsv(report)}><Download size={14}/>{l('全場面CSV', 'All-scene CSV')}</button></div>
        <p className="ap-note">{selected.id} · {selected.cluster_id}</p>
        <div className="ap-table-wrap"><table><caption>{l('選択した場面。副帯域が良くても、全帯域の改善とは限りません。', 'Selected scene. Better secondary-band scores do not imply full-band improvement.')}</caption><thead><tr><th scope="col">{l('方法', 'Method')}</th><th scope="col">{l('全帯域', 'Full band')}<br/>NRMSE dB</th><th scope="col">31.25 Hz–8 kHz<br/>NRMSE dB</th><th scope="col">100 Hz–8 kHz<br/>NRMSE dB</th><th scope="col">{l('振幅誤差', 'Magnitude error')}<br/>dB</th><th scope="col">MSC</th><th scope="col">SI-SDR<br/>dB</th></tr></thead><tbody>{report.methods.map(m => <tr key={m.id} data-plus={m.kind === 'plus'}><th scope="row">{name(m)}</th>{metricKeys.map(key => <td key={key}>{fmt(selected.metrics[m.id][key], key === 'coherence' ? 5 : 3)}</td>)}</tr>)}</tbody></table></div>
        <p className="ap-note">{l('100 Hz–8 kHzの実際の最初のbinは125 Hzです。MSC・SI-SDRは高いほど良く、他の誤差は低いほど良い指標です。未定義の値を0や改善に置き換えません。', 'The first actual bin within 100 Hz–8 kHz is 125 Hz. Higher MSC and SI-SDR are better; other errors are better when lower. Undefined scores are not replaced by zero or counted as improvements.')}</p>
        <p className="ap-note">{l('MSCが未定義になる場合：参照にある成分の推定がゼロの周波数では、相関の分母を定義できません。今回のLinear系ではDCや8 kHzに該当します。未定義の周波数を除いた平均で置き換えず、—のまま残します。', 'MSC may be undefined when an estimated component has zero energy although the reference does not, making its denominator undefined. This occurs at DC or 8 kHz for the Linear controls. The full-band average remains undefined rather than silently omitting these bins.')}</p>
        <details className="ap-details"><summary>{l('全場面の全帯域NRMSEを表示', 'Show full-band NRMSE for every scene')}</summary><div className="ap-table-wrap"><table><caption>{l('場面を選ぶと、上の詳細表が切り替わります。結果が悪い場面もすべて掲載します。', 'Select a scene to update the detail table above. Regressions remain in the table.')}</caption><thead><tr><th scope="col">{l('場面 / 話者群', 'Scene / cluster')}</th>{report.methods.map(m => <th key={m.id} scope="col">{name(m)}<br/>dB</th>)}</tr></thead><tbody>{report.scenes.map(s => <tr key={s.id} data-selected={selected.id === s.id}><th scope="row"><button type="button" aria-pressed={selected.id === s.id} onClick={() => setSceneId(s.id)}>{s.id}<small>{s.cluster_id}</small></button></th>{report.methods.map(m => <td key={m.id}>{fmt(s.metrics[m.id].nrmse_db, 4)}</td>)}</tr>)}</tbody></table></div></details>
      </section>
      <section className="ap-section"><header className="ap-section-heading"><span className="eyebrow">03 / FREQUENCY</span><h3>{l('周波数ごとに確かめる。', 'Inspect accuracy across frequency.')}</h3></header>
        <fieldset className="ap-scope-picker"><legend>{l('図に表示する方法', 'Methods shown in the plots')}</legend>{report.methods.map(method => <label key={method.id}><input type="checkbox" checked={visibleMethods.includes(method.id)} onChange={() => setVisibleMethods(current => current.includes(method.id) ? current.length > 1 ? current.filter(id => id !== method.id) : current : [...current, method.id])}/>{name(method)}</label>)}</fieldset>
        {selected.curves && <fieldset className="ap-scope-picker"><legend>{l('曲線の対象', 'Curve scope')}</legend>{(['aggregate', 'scene'] as const).map(scope => <label key={scope}><input type="radio" name={`${frequencyId}-scope`} checked={actualScope === scope} onChange={() => setCurveScope(scope)}/>{scope === 'aggregate' ? l('全場面の集計', 'All-scene aggregate') : `${l('選択場面', 'Selected scene')} · ${selected.id}`}</label>)}</fieldset>}
        <p className="ap-coverage"><strong>{actualScope === 'aggregate' ? l('全場面の集計曲線', 'All-scene aggregate curves') : selected.id}</strong><span>{l('表示軸', 'Display axis')} 1 Hz–20 kHz · {l('計算済みの正周波数', 'Computed positive frequencies')} {positiveFrequencies.length ? `${hz(positiveFrequencies[0])}–${hz(positiveFrequencies.at(-1)!)}` : '—'}</span>{l('未計算の帯域は空白です。DC（0 Hz）は対数軸に描けないため、下の表で別に確認できます。', 'Uncomputed bands remain empty. DC (0 Hz) cannot appear on a logarithmic axis; inspect it separately in the table below.')}</p>
        <div className="ap-charts"><div><h4>NRMSE <small>{l('低いほど良い', 'Lower is better')}</small></h4><Plot x={report.frequencies_hz} frequency series={series('nrmse_db')} label={l('周波数ごとの複素FOA誤差', 'Complex FOA error at each frequency')} unit="dB"/></div>
          <div><h4>{l('振幅スペクトル誤差', 'Magnitude spectrum error')} <small>{l('低いほど良い', 'Lower is better')}</small></h4><Plot x={report.frequencies_hz} frequency series={series('magnitude_spectrum_error_db')} label={l('振幅の差 · dBは音圧ではありません', 'Magnitude difference · dB is not sound pressure')} unit="dB"/></div>
          <div><h4>Coherence <small>{l('1に近いほど良い', 'Closer to 1 is better')}</small></h4><Plot x={report.frequencies_hz} frequency series={series('magnitude_squared_coherence')} label={l('時間方向の整合性 · MSC', 'Temporal consistency · MSC')} unit="MSC" yDomain={[0, 1]}/></div></div>
        <div className="ap-controls"><label htmlFor={frequencyId}>{l('数値を見る周波数', 'Inspect frequency')}</label><select id={frequencyId} value={report.frequencies_hz[frequencyIndex]} onChange={e => setFrequency(Number(e.target.value))}>{report.frequencies_hz.map(f => <option value={f} key={f}>{hz(f)}{f === 0 ? ' · DC' : ''}</option>)}</select><button type="button" onClick={() => setFrequency(0)}>{l('DCを確認', 'Inspect DC')}</button></div>
        <div className="ap-table-wrap"><table><caption>{actualScope === 'aggregate' ? l('全場面の集計', 'All-scene aggregate') : selected.id} · {hz(report.frequencies_hz[frequencyIndex])}{report.frequencies_hz[frequencyIndex] === 0 ? ' · DC' : ''}</caption><thead><tr><th scope="col">{l('方法', 'Method')}</th><th scope="col">NRMSE dB</th><th scope="col">{l('振幅誤差 dB', 'Magnitude error dB')}</th><th scope="col">MSC</th></tr></thead><tbody>{report.methods.map(m => <tr key={m.id} data-plus={m.kind === 'plus'}><th scope="row">{name(m)}</th>{curveKeys.map(key => <td key={key}>{fmt(curveData[m.id][key][frequencyIndex], key === 'magnitude_squared_coherence' ? 5 : 3)}</td>)}</tr>)}</tbody></table></div>
        <p className="ap-note">{l('全帯域NRMSEは参照エネルギーの分布に影響されます。低域やDCの支配を隠すために帯域を除外しません。曲線と全帯域平均は集計方法が異なり、曲線のdBを単純平均して主指標にはできません。', 'Full-band NRMSE depends on reference-energy distribution. Low frequencies or DC are not removed to hide their influence. Frequency curves and full-band scores use different aggregation; averaging the curve’s dB values does not recover the primary metric.')}</p>
      </section>
      {report.example_url && <PlusAudition url={asset(report.example_url)} language={language} active={active}/>}
      <section className="ap-section"><header className="ap-section-heading"><span className="eyebrow">04 / EVIDENCE</span><h3>{l('結果を支える記録。', 'The record behind the result.')}</h3></header><ul className="ap-limitations">{(language === 'jp' ? report.limitations_jp : report.limitations_en).map((item, i) => <li key={i}>{item}</li>)}</ul>
        <details className="ap-details"><summary>{l('候補の選択・学習と評価の分離', 'Selection and separation of training and evaluation')}</summary><p>{l('パラメータは開発データで選び、最終評価を見る前に固定します。最終評価で選び直した結果は、未使用テストの証拠として扱えません。以下は記録に含まれる設定です。', 'Select parameters on development data and freeze them before viewing final-test results. Retuning on the final test invalidates an untouched-test claim. The recorded settings follow.')}</p><pre>{JSON.stringify(report.selection, null, 2)}</pre></details>
        <details className="ap-details"><summary>{l('重み・入力・計算環境の識別', 'Checkpoint, input and runtime identity')}</summary><pre>{JSON.stringify(report.provenance, null, 2)}</pre></details>
        <div className="ap-links"><a href={asset('info/PLUS_RESULTS.md')}>{l('最終評価レポート', 'Final evaluation report')}</a><a href={asset(REPORT)} download><Download size={14}/>{l('評価JSONを保存', 'Download evaluation JSON')}</a>
          <a href={asset('models/plus-frequency-comparison.svg')} download><Download size={14}/>{l('周波数比較図を保存 · SVG', 'Download frequency comparison · SVG')}</a>
          <a href={asset('models/plus-summary-comparison.svg')} download><Download size={14}/>{l('評価の比較図を保存 · SVG', 'Download evaluation summary · SVG')}</a>
          {report.example_url && <a href={asset('models/plus-example-input.npz')} download><Download size={14}/>{l('再計算用の入力を保存', 'Download the input for recomputation')}</a>}{report.sources.map(source => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title}<ExternalLink size={12}/></a>)}</div>
      </section>
    </>}
    <div className="ap-end"><p>{l('学習・開発・最終テストの分割と、原論文との差を確認してから、結果の意味を判断します。', 'Interpret the scores alongside the training, development and test split and differences from the paper.')}</p><button type="button" onClick={() => onNavigate('paper')}>{l('論文と実装の範囲', 'Paper & implementation')}<ArrowRight size={14}/></button><a href="https://arxiv.org/html/2608.24558v3#S4" target="_blank" rel="noreferrer">{l('原論文 §4', 'Original paper §4')}<ExternalLink size={12}/></a></div>
  </article>;
}
