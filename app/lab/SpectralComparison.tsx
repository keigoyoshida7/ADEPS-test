import { useId, useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import { Plot, fmt } from './Plots';
import './SpectralComparison.css';

export type FrequencyMetrics = {
  schema: 'adeps-test-spectral-metrics/1';
  frequency_hz: number[];
  magnitude_spectrum_error_db: (number | null)[];
  magnitude_squared_coherence: (number | null)[];
  reference_active_channels: number[];
  coherence_valid_channels: number[];
  reference_below_floor_cells: number[];
  estimate_below_floor_cells: number[];
  magnitude_floor_absolute: number;
  magnitude_floor_relative: number;
  channels: number;
  frames: number;
};
export type SpectralEstimate = {
  id: string; label: string; stage: string; step: number; sigma: number;
  frequency_metrics?: FrequencyMetrics;
};
type Props = {
  language: 'jp' | 'en'; runId: string | number; inputSha256: string;
  linear: SpectralEstimate; diffusion: SpectralEstimate; checkpoints: SpectralEstimate[];
};
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const hz = (value: number) => value >= 1000 ? `${Number((value / 1000).toFixed(4))} kHz` : `${Number(value.toFixed(4))} Hz`;
const sigma = (value: number) => Number(value.toPrecision(5)).toString();
const csvCell = (value: string | number | null) => value === null ? '' : `"${String(value).replaceAll('"', '""')}"`;

function validMetrics(value: FrequencyMetrics | undefined): value is FrequencyMetrics {
  if (!value || value.schema !== 'adeps-test-spectral-metrics/1' || value.channels !== 4
    || !Number.isInteger(value.frames) || value.frames < 1
    || !finite(value.magnitude_floor_absolute) || value.magnitude_floor_absolute < 0
    || value.magnitude_floor_relative !== 1e-12 || !Array.isArray(value.frequency_hz) || value.frequency_hz.length < 2
    || !value.frequency_hz.every((f, i, all) => finite(f) && f >= 0 && (i === 0 || f > all[i - 1]))
    || !value.frequency_hz.some(f => f >= 1 && f <= 20000)) return false;
  const length = value.frequency_hz.length;
  return [value.magnitude_spectrum_error_db, value.magnitude_squared_coherence].every((values, metric) =>
    Array.isArray(values) && values.length === length && values.every(n => n === null || (finite(n) && n >= 0 && (metric === 0 || n <= 1))))
    && [value.reference_active_channels, value.coherence_valid_channels, value.reference_below_floor_cells, value.estimate_below_floor_cells]
      .every((values, field) => Array.isArray(values) && values.length === length
        && values.every(n => Number.isInteger(n) && n >= 0 && n <= (field < 2 ? value.channels : value.frames * value.channels)));
}
const matchingGrid = (a: FrequencyMetrics, b: FrequencyMetrics) => a.frequency_hz.length === b.frequency_hz.length
  && a.frequency_hz.every((value, index) => value === b.frequency_hz[index])
  && a.frames === b.frames && a.channels === b.channels
  && a.magnitude_floor_absolute === b.magnitude_floor_absolute;

export default function SpectralComparison({ language, runId, inputSha256, linear, diffusion, checkpoints }: Props) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [selectedFrequency, setSelectedFrequency] = useState(1000);
  const frequencyId = useId();
  const baseline = linear.frequency_metrics;
  const selected = diffusion.frequency_metrics;
  const ready = validMetrics(baseline) && validMetrics(selected) && matchingGrid(baseline, selected)
    && linear.id !== diffusion.id && diffusion.stage !== 'linear';
  const label = diffusion.stage === 'final_sample' ? l('最終出力', 'Final output') : l('途中の推定', 'Intermediate estimate');
  const names = { linear: 'Linear', diffusion: l('ADEPS-test · 独自実装', 'ADEPS-test · independent implementation') };
  const index = ready ? baseline.frequency_hz.reduce((best, value, i, values) =>
    Math.abs(value - selectedFrequency) < Math.abs(values[best] - selectedFrequency) ? i : best, 0) : 0;
  const positiveFrequencies = ready ? baseline.frequency_hz.filter(f => f >= 1 && f <= 20000) : [];
  const domainValues = ready ? [linear, diffusion, ...checkpoints].flatMap(estimate => {
    const metrics = estimate.frequency_metrics;
    return validMetrics(metrics) && matchingGrid(baseline, metrics) ? metrics.magnitude_spectrum_error_db.filter((v, i): v is number =>
      finite(v) && metrics.frequency_hz[i] >= 1 && metrics.frequency_hz[i] <= 20000) : [];
  }) : [];
  const errorMax = Math.max(1, ...domainValues) * 1.08;
  const delta = (a: number | null, b: number | null) => a == null || b == null ? null : a - b;
  const signed = (value: number | null, digits = 3) => value == null ? '—' : `${value > 0 ? '+' : ''}${fmt(value, digits)}`;

  function downloadCsv() {
    if (!ready) return;
    const headers = ['run_id', 'input_sha256', 'diffusion_id', 'stage', 'completed_steps', 'sigma', 'frequency_hz',
      'linear_magnitude_spectrum_error_db', 'adeps_test_magnitude_spectrum_error_db', 'magnitude_improvement_db',
      'linear_magnitude_squared_coherence', 'adeps_test_magnitude_squared_coherence', 'coherence_improvement',
      'reference_active_channels', 'linear_coherence_valid_channels', 'adeps_test_coherence_valid_channels',
      'reference_below_floor_cells', 'linear_below_floor_cells', 'adeps_test_below_floor_cells',
      'magnitude_floor_absolute', 'magnitude_floor_relative', 'frames', 'channels'];
    const rows = baseline.frequency_hz.map((f, i) => [runId, inputSha256, diffusion.id, diffusion.stage, diffusion.step, diffusion.sigma, f,
      baseline.magnitude_spectrum_error_db[i], selected.magnitude_spectrum_error_db[i], delta(baseline.magnitude_spectrum_error_db[i], selected.magnitude_spectrum_error_db[i]),
      baseline.magnitude_squared_coherence[i], selected.magnitude_squared_coherence[i], delta(selected.magnitude_squared_coherence[i], baseline.magnitude_squared_coherence[i]),
      baseline.reference_active_channels[i], baseline.coherence_valid_channels[i], selected.coherence_valid_channels[i],
      baseline.reference_below_floor_cells[i], baseline.estimate_below_floor_cells[i], selected.estimate_below_floor_cells[i],
      baseline.magnitude_floor_absolute, baseline.magnitude_floor_relative, baseline.frames, baseline.channels]);
    const csv = '\uFEFF' + [headers, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n') + '\r\n';
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url;
    link.download = `ADEPS-test_spectral_run-${String(runId).replace(/[^\w-]/g, '_')}_step-${diffusion.step}.csv`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="panel spectral-comparison" aria-label={l('周波数ごとの復元精度', 'Reconstruction accuracy by frequency')}>
    <header className="sc-heading"><span className="sc-eyebrow">FREQUENCY / LINEAR × ADEPS-TEST</span>
      <h3>{l('周波数ごとの復元精度', 'Reconstruction accuracy by frequency')}</h3>
      <p>{l('同じ合成の正解に対して、Linearと選択した拡散ステップを比較します。拡散のON/OFFや試聴音を切り替えても、この2本の比較は保たれます。',
        'Compare Linear and the selected diffusion stage against the same synthetic reference. The two methods remain distinct when you toggle diffusion or change the preview audio.')}</p>
    </header>
    <div className="sc-run"><span>Run {runId}</span><span>{label} · {l('完了ステップ', 'Completed steps')} {diffusion.step} · σ {sigma(diffusion.sigma)}</span></div>
    {!ready ? <p className="sc-unavailable" role="status">{l('この記録には比較可能な周波数データがありません。現在のバージョンで復元を実行すると、Linearと拡散の比較を保存できます。',
      'This record has no comparable frequency data. Reconstruct with the current version to save the Linear and diffusion comparison.')}</p> : <>
      <p className="sc-coverage">{l('表示軸', 'Display axis')}: 1 Hz–20 kHz · {l('計算済みの周波数', 'Computed frequencies')}: {hz(positiveFrequencies[0])}–{hz(positiveFrequencies.at(-1)!)}
        <span>{l('未計算の帯域は空白。0 Hz（DC）は詳細表とCSVだけに残しています。', 'Uncomputed bands remain empty. The 0 Hz DC bin is retained only in the table and CSV.')}</span></p>
      <div className="sc-plots">
        <div><h4>{l('振幅スペクトル誤差', 'Magnitude spectrum error')} <small>{l('低いほど良い', 'Lower is better')}</small></h4>
          <Plot x={baseline.frequency_hz} frequency yDomain={[0, errorMax]} unit="dB" label={l('Magnitude Spectrum Error · 全保存ステップで縦軸共通', 'Magnitude Spectrum Error · shared scale across saved stages')}
            series={[{ name: names.linear, values: baseline.magnitude_spectrum_error_db, color: '#999', dash: '7 5' }, { name: names.diffusion, values: selected.magnitude_spectrum_error_db, color: '#f3f3f3' }]} />
        </div>
        <div><h4>Coherence <small>{l('1に近いほど良い', 'Closer to 1 is better')}</small></h4>
          <Plot x={baseline.frequency_hz} frequency yDomain={[0, 1]} unit="MSC" label={l('Magnitude-squared coherence · 0–1固定', 'Magnitude-squared coherence · fixed 0–1')}
            series={[{ name: names.linear, values: baseline.magnitude_squared_coherence, color: '#999', dash: '7 5' }, { name: names.diffusion, values: selected.magnitude_squared_coherence, color: '#f3f3f3' }]} />
        </div>
      </div>
      <p className="sc-caption">{l('参照が非常に弱い周波数では、振幅の相対誤差が大きくなることがあります。このdBは音量や音圧レベル（SPL）ではありません。',
        'Relative magnitude error can become large where the reference is very weak. These dB values are not playback volume or sound pressure level (SPL).')}</p>
      <div className="sc-frequency"><label htmlFor={frequencyId}>{l('値を確認する周波数', 'Inspect frequency')}</label>
        <select id={frequencyId} value={baseline.frequency_hz[index]} onChange={e => setSelectedFrequency(Number(e.target.value))}>
          {baseline.frequency_hz.map(f => <option key={f} value={f}>{hz(f)}{f === 0 ? ' · DC' : ''}</option>)}
        </select><span>{l('この周波数の値は、選択ステップと連続試聴の進行に追従します。', 'Values at this frequency follow the selected stage and process audition.')}</span>
      </div>
      <div className="sc-values" aria-live="polite">
        <article><h4>{l('振幅スペクトル誤差', 'Magnitude spectrum error')} · {hz(baseline.frequency_hz[index])}</h4>
          <dl><div><dt>Linear</dt><dd>{fmt(baseline.magnitude_spectrum_error_db[index], 3)} <small>dB</small></dd></div>
            <div><dt>ADEPS-test</dt><dd>{fmt(selected.magnitude_spectrum_error_db[index], 3)} <small>dB</small></dd></div></dl>
          <p>{l('差（Linear − ADEPS-test）', 'Difference (Linear − ADEPS-test)')} <strong>{signed(delta(baseline.magnitude_spectrum_error_db[index], selected.magnitude_spectrum_error_db[index]))} dB</strong></p>
        </article>
        <article><h4>Coherence · {hz(baseline.frequency_hz[index])}</h4>
          <dl><div><dt>Linear</dt><dd>{fmt(baseline.magnitude_squared_coherence[index], 5)}</dd></div>
            <div><dt>ADEPS-test</dt><dd>{fmt(selected.magnitude_squared_coherence[index], 5)}</dd></div></dl>
          <p>{l('差（ADEPS-test − Linear）', 'Difference (ADEPS-test − Linear)')} <strong>{signed(delta(selected.magnitude_squared_coherence[index], baseline.magnitude_squared_coherence[index]), 5)}</strong></p>
        </article>
      </div>
      <p className="sc-caption">{l('どちらの「差」も、正なら拡散側が改善、負なら悪化です。—は計算できない値で、0を意味しません。', 'For both differences, positive means diffusion improved; negative means it worsened. A dash means unavailable, not zero.')}
        {' '}{l('この周波数の参照に信号があるch', 'Reference channels with signal at this frequency')}: {baseline.reference_active_channels[index]}/4 · {l('Coherenceの有効ch', 'Valid coherence channels')}: Linear {baseline.coherence_valid_channels[index]}, ADEPS-test {selected.coherence_valid_channels[index]}</p>
      <div className="sc-export"><button type="button" onClick={downloadCsv}><Download size={14}/>{l('このステップの全周波数をCSV保存', 'Save all frequencies for this stage as CSV')}</button></div>
      <details className="sc-details"><summary>{l('全周波数の数値を見る', 'Inspect values at every frequency')}</summary>
        <div className="sc-table"><table><caption>{l('実測定ではなく、このrunの合成FOAに対する計算値。周波数を押すと上の比較値も切り替わります。', 'Computed against this run’s synthetic FOA reference, not physical measurements. Select a frequency to update the readout above.')}</caption>
          <thead><tr><th scope="col">Hz</th><th scope="col">Linear<br/>{l('振幅誤差 dB', 'Magnitude error dB')}</th><th scope="col">ADEPS-test<br/>{l('振幅誤差 dB', 'Magnitude error dB')}</th><th scope="col">Linear<br/>Coherence</th><th scope="col">ADEPS-test<br/>Coherence</th><th scope="col">{l('参照の有効ch', 'Reference active ch')}</th></tr></thead>
          <tbody>{baseline.frequency_hz.map((f, i) => <tr key={f} data-selected={index === i}><th scope="row"><button type="button" onClick={() => setSelectedFrequency(f)}>{f}{f === 0 ? ' DC' : ''}</button></th>
            <td>{fmt(baseline.magnitude_spectrum_error_db[i], 4)}</td><td>{fmt(selected.magnitude_spectrum_error_db[i], 4)}</td>
            <td>{fmt(baseline.magnitude_squared_coherence[i], 5)}</td><td>{fmt(selected.magnitude_squared_coherence[i], 5)}</td><td>{baseline.reference_active_channels[i]}/4</td></tr>)}</tbody>
        </table></div>
      </details>
      <details className="sc-details"><summary>{l('計算方法と引用を見る', 'Inspect methods and references')}</summary>
        <dl className="sc-methods">
          <div><dt>{l('比較の正解', 'Reference')}</dt><dd>{l('このrunを生成した未圧縮のFOA 4ch（ACN/N3D、W/Y/Z/X）。DC・Nyquistの虚部を0にした後、出力ゲインを掛ける前の複素STFT係数を採点します。WAV化後にSTFTを取り直した値ではありません。',
            'The uncompressed FOA reference for this run: four ACN/N3D channels, W/Y/Z/X. Scores use complex STFT coefficients after setting the DC/Nyquist imaginary parts to zero and before output gain. They are not computed by reanalyzing the reconstructed WAV.')}</dd></div>
          <div><dt>{l('振幅スペクトル誤差', 'Magnitude error')}</dt><dd><code>mean(c,t) |20 log₁₀(max(|ref|, ε) / max(|estimate|, ε))|</code><br/>{l(`各周波数で${baseline.frames}フレーム×4chを等しく平均します。周波数全体のRMS比やNRMSEではありません。`, `At each frequency, average equally over ${baseline.frames} frames × 4 channels. This is not a broadband RMS ratio or NRMSE.`)}</dd></div>
          <div><dt>Coherence</dt><dd><code>mean(c) [|Σt conj(ref) × estimate|² / (Σt |ref|² × Σt |estimate|²)]</code><br/>{l('時間方向のクロスパワーからch別の二乗コヒーレンスを求め、参照に信号があるchで平均。単一の時間周波数点の相関ではありません。', 'Compute magnitude-squared coherence from cross-power over time for each channel, then average channels with nonzero reference energy. This is not correlation at one time–frequency point.')}</dd></div>
          <div><dt>{l('Coherenceの限界', 'Coherence limitation')}</dt><dd>{l('一定のゲインや位相のずれがあっても1になる場合があります。1フレームだけに信号がある場合も1となるため、方向や音場の正しさを単独で保証する指標ではありません。', 'Coherence can equal 1 despite a constant gain or phase error, and is trivial with only one active frame. It does not alone establish correct direction or soundfield reconstruction.')}</dd></div>
          <div><dt>{l('ゼロと極小値', 'Zeros and very small values')}</dt><dd>{l('振幅の床εは参照全体の最大振幅×10⁻¹²とfloat64の最小正規化正数の大きい方。Linearと全ステップに同じ値を使用します。', 'The magnitude floor ε is the larger of the global reference peak × 10⁻¹² and the smallest positive normal float64 value, shared by Linear and every stage.')} ε = {baseline.magnitude_floor_absolute.toExponential(5)}<br/>
            {l('参照が全chで無音の周波数は両指標を空欄にします。参照に信号があるchで推定がゼロの場合、その周波数のCoherenceは未定義として空欄にし、有効なchだけで良い平均を作りません。', 'If every reference channel is silent at a frequency, both metrics are unavailable. If an estimate has zero energy in any active reference channel, coherence at that frequency is undefined; it is not averaged over the remaining valid channels.')}<br/>
            {l('選択周波数で床を下回る係数数', 'Coefficients below the floor at the selected frequency')}: {l('参照', 'reference')} {baseline.reference_below_floor_cells[index]}, Linear {baseline.estimate_below_floor_cells[index]}, ADEPS-test {selected.estimate_below_floor_cells[index]} / {baseline.frames * 4}</dd></div>
        </dl>
        <div className="sc-sources"><a href="https://arxiv.org/html/2608.24558v3#S4" target="_blank" rel="noreferrer">{l('ADEPS論文 · §4 / Fig. 1', 'ADEPS paper · §4 / Fig. 1')}<ExternalLink size={12}/></a>
          <a href="https://arxiv.org/html/2501.08047v1#S3.SS4" target="_blank" rel="noreferrer">{l('指標の式 · Gen-A §III-D, Eq. (5), (6)', 'Metric definitions · Gen-A §III-D, Eqs. (5), (6)')}<ExternalLink size={12}/></a></div>
        <p className="sc-caption">{l('式を参照し、ゼロ除算・対数のための床と空欄の扱いを本実装で明示しました。論文で同じ数値処理が使われたとの確認はしていません。', 'The formulas are cited; this implementation explicitly defines the floor and missing-value policy. The paper’s use of identical numerical handling has not been established.')}</p>
      </details>
    </>}
    <p className="sc-limits">{l('1つの短い合成クリップの検証です。生成・推論とも5次の条件で、比較する出力はFOA。論文のParametric・次数不一致条件は含まず、公式重みも使っていません。論文の多数シーンの平均値との直接比較や、実空間での性能保証には使えません。',
      'This evaluates one short synthetic clip, with order-5 generation and inference and FOA output. It excludes the paper’s parametric and order-mismatched conditions and does not use official weights. It cannot establish equivalence to the paper’s multi-scene averages or real-room performance.')}</p>
    <p className="sc-hash">{l('入力の識別', 'Input identity')} SHA-256 · {inputSha256}</p>
  </section>;
}
