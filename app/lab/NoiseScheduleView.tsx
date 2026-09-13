'use client';

import { useId, useMemo, useState } from 'react';
import type { PointerEvent } from 'react';
import './NoiseScheduleView.css';

type Point = { step: number; sigma: number };
export type NoiseScheduleViewProps = {
  points: Point[];
  language: 'jp' | 'en';
  sourceLabel: string;
  checkpoints?: Point[];
  selectedStep?: number;
  onSelectCheckpoint?: (step: number) => void;
  parameters?: { sigmaMax: number; sigmaMin: number; rho: number };
};
const W = 760, H = 326, LEFT = 70, RIGHT = 730, TOP = 35, BOTTOM = 215, ZERO = 252;
const number = (value: number) => value === 0 ? '0' : Math.abs(value) < .0001 || Math.abs(value) >= 100000
  ? value.toExponential(4) : Number(value.toPrecision(6)).toString();

export function NoiseScheduleView({ points, language, sourceLabel, checkpoints = [], selectedStep,
  onSelectCheckpoint, parameters }: NoiseScheduleViewProps) {
  const jp = language === 'jp', id = useId();
  const [scale, setScale] = useState<'log' | 'linear'>('log');
  const [inspection, setInspection] = useState<{ key: string; step: number } | null>(null);
  const data = useMemo(() => {
    const valid = points.length >= 3 && points.every((point, i) => point.step === i && Number.isFinite(point.sigma)
      && (i === points.length - 1 ? point.sigma === 0 : point.sigma > 0)
      && (i === 0 || point.sigma <= points[i - 1].sigma));
    const rows = valid ? points.map((point, i) => ({ ...point, next: points[i + 1]?.sigma,
      delta: i < points.length - 1 ? points[i + 1].sigma - point.sigma : undefined })) : [];
    const csv = ['step,sigma,next_sigma,delta_sigma', ...rows.map(row => [row.step, row.sigma, row.next ?? '', row.delta ?? ''].join(','))].join('\n');
    return { valid, rows, csv, key: points.map(point => `${point.step}:${point.sigma}`).join('|') };
  }, [points]);
  const key = `${data.key}/${selectedStep ?? ''}`;
  const m = Math.max(1, data.rows.length - 1);
  const fallback = selectedStep !== undefined && data.rows[selectedStep] ? selectedStep : 0;
  const inspected = inspection?.key === key ? inspection.step : fallback;
  const current = data.rows[inspected];
  const saved = new Set(checkpoints.filter(point => data.rows[point.step]
    && Math.abs(point.sigma - data.rows[point.step].sigma) <= 1e-9 * Math.max(1, point.sigma)).map(point => point.step));
  const maximum = data.rows[0]?.sigma || 1, minimum = data.rows[m - 1]?.sigma || .001;
  const logMax = Math.log10(maximum), logMin = Math.log10(minimum);
  const x = (step: number) => LEFT + step / m * (RIGHT - LEFT);
  const y = (sigma: number) => scale === 'log'
    ? sigma === 0 ? ZERO : TOP + (logMax - Math.log10(sigma)) / (logMax - logMin || 1) * (BOTTOM - TOP)
    : TOP + (1 - sigma / maximum) * (BOTTOM - TOP);
  const ticks = Array.from({ length: 5 }, (_, i) => scale === 'log'
    ? 10 ** (logMax + i / 4 * (logMin - logMax)) : maximum * (1 - i / 4));
  const xTicks = [...new Set(Array.from({ length: 5 }, (_, i) => Math.round(i / 4 * m)))];
  const line = data.rows.filter(point => scale === 'linear' || point.sigma > 0).map(point => `${x(point.step)},${y(point.sigma)}`).join(' ');
  const pointerStep = (event: PointerEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    return Math.round(Math.max(0, Math.min(1, ((event.clientX - bounds.left) / bounds.width * W - LEFT) / (RIGHT - LEFT))) * m);
  };

  return <section className="noise-schedule" aria-label={jp ? 'ノイズスケジュール' : 'Noise schedule'}>
    <header className="nsv-heading"><span>DIFFUSION / NOISE SCHEDULE</span><h3>{jp ? '反復ごとのノイズレベル' : 'Noise level at each iteration'}</h3>
      <p className="nsv-source">{sourceLabel}</p><p>{jp ? '反復回数と値を正確に比較するため、2Dで表示します。σは計算に設定したノイズ標準偏差です。実際に残った雑音量、再生時間、SNRやdBを表す値ではありません。' : 'A 2D plot makes steps and values precise to compare. σ is the scheduled noise standard deviation, not estimated residual noise, playback time, SNR or dB.'}</p></header>
    {!data.valid ? <p className="nsv-empty">{jp ? '有効なスケジュールがありません。0から連続するstep、減少する正のσ、最後のσ=0が必要です。' : 'No valid schedule. Steps must start at 0 and be consecutive, with decreasing positive σ levels and a final σ=0.'}</p>
      : <>
        <div className="nsv-toolbar"><fieldset aria-label={jp ? '縦軸の表示' : 'Vertical scale'}>{(['log', 'linear'] as const).map(value => <button type="button" key={value} aria-pressed={scale === value} onClick={() => setScale(value)}>{value === 'log' ? (jp ? '対数' : 'Logarithmic') : (jp ? '線形' : 'Linear')}</button>)}</fieldset>
          <span>{m} {jp ? '回の更新' : 'updates'} / {m + 1} {jp ? '点' : 'points'}</span>
          <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(data.csv)}`} download="noise-schedule.csv">CSV ↓</a></div>
        <div className="nsv-plot"><svg viewBox={`0 0 ${W} ${H}`} aria-label={jp ? '横軸は完了したEuler更新回数、縦軸はノイズ標準偏差σ。下のスライダーと表でも確認できます。' : 'Completed Euler updates on the horizontal axis; noise standard deviation sigma vertically. Also available through the slider and table below.'}
          onPointerMove={event => setInspection({ key, step: pointerStep(event) })} onPointerDown={event => setInspection({ key, step: pointerStep(event) })}>
          <title>{jp ? '反復回数とノイズ標準偏差' : 'Iteration count and noise standard deviation'}</title>
          <text className="nsv-axis-name" x={LEFT} y={17}>σ · {scale === 'log' ? (jp ? '対数' : 'log') : (jp ? '線形' : 'linear')}</text>
          {ticks.map((tick, i) => <g key={i}><line className="nsv-grid" x1={LEFT} x2={RIGHT} y1={y(tick)} y2={y(tick)}/><text x={LEFT - 12} y={y(tick) + 4} textAnchor="end">{number(tick)}</text></g>)}
          {scale === 'log' && <g><rect className="nsv-zero-gutter" x={LEFT} y={235} width={RIGHT - LEFT} height={32}/><text x={LEFT + 10} y={ZERO + 4}>{jp ? '終端 σ=0（対数軸の外）' : 'Terminal σ=0 (outside log axis)'}</text></g>}
          {xTicks.map(step => <g key={step}><line className="nsv-grid" x1={x(step)} x2={x(step)} y1={TOP} y2={BOTTOM}/><text x={x(step)} y={287} textAnchor="middle">{step}</text></g>)}
          <polyline className="nsv-curve" points={line}/>
          {current && <line className="nsv-inspect-line" x1={x(current.step)} x2={x(current.step)} y1={TOP} y2={scale === 'log' && current.sigma === 0 ? ZERO : BOTTOM}/>}
          {data.rows.map(point => <g key={point.step}>
            {point.step === selectedStep && <circle className="nsv-active" cx={x(point.step)} cy={y(point.sigma)} r={9}/>}
            {saved.has(point.step) ? <rect className="nsv-saved" x={x(point.step) - 4} y={y(point.sigma) - 4} width={8} height={8}/>
              : <circle className="nsv-point" cx={x(point.step)} cy={y(point.sigma)} r={2.5}/>}
          </g>)}
          <text className="nsv-axis-name" x={(LEFT + RIGHT) / 2} y={314} textAnchor="middle">{jp ? '完了したEuler更新回数（音声の時間ではありません）' : 'Completed Euler updates (not audio time)'}</text>
        </svg></div>
        <div className="nsv-legend"><span>● {jp ? '全スケジュール点' : 'Every scheduled level'}</span><span>□ {jp ? '復元を保存した時点' : 'Saved reconstruction'}</span><span>◎ {jp ? '表示中の復元' : 'Displayed reconstruction'}</span></div>
        <div className="nsv-inspector"><label htmlFor={id}>{jp ? '調べる更新回数' : 'Inspect completed updates'} <strong>{inspected} / {m}</strong></label>
          <input id={id} type="range" min={0} max={m} step={1} value={inspected} aria-valuetext={`step ${inspected}, sigma ${number(data.rows[inspected].sigma)}`} onChange={event => setInspection({ key, step: Number(event.target.value) })}/>
          {current && <><output className="nsv-readout" aria-live="polite"><span>step <strong>{current.step}</strong></span><span>σ <strong>{number(current.sigma)}</strong></span><span>{jp ? '次のσ' : 'Next σ'} <strong>{current.next === undefined ? '—' : number(current.next)}</strong></span><span>Δσ <strong>{current.delta === undefined ? '—' : number(current.delta)}</strong></span></output>
            {saved.has(current.step) && onSelectCheckpoint ? <button className="nsv-open" type="button" onClick={() => onSelectCheckpoint(current.step)}>{jp ? 'この時点の復元を見る' : 'View this reconstruction'} →</button>
              : <p className="nsv-inspect-note">{jp ? 'この点は数値のみ確認できます。保存していない復元や音声は生成しません。' : 'This point is available for numerical inspection only. No unsaved reconstruction or audio is generated.'}</p>}</>}
        </div>
        <details className="nsv-details"><summary>{jp ? '全ステップの数値を見る' : 'Inspect every scheduled value'}</summary><div className="nsv-table-wrap"><table><caption>{jp ? 'Δσ = 次のσ − 現在のσ。最後の行は次の更新がないため空欄。' : 'Δσ = next σ − current σ. The terminal row has no next update.'}</caption>
          <thead><tr><th scope="col">step</th><th scope="col">σ</th><th scope="col">{jp ? '次のσ' : 'Next σ'}</th><th scope="col">Δσ</th><th scope="col">{jp ? '復元' : 'Reconstruction'}</th></tr></thead>
          <tbody>{data.rows.map(row => <tr key={row.step} data-inspected={row.step === current?.step}><th scope="row">{row.step}</th><td>{number(row.sigma)}</td><td>{row.next === undefined ? '—' : number(row.next)}</td><td>{row.delta === undefined ? '—' : number(row.delta)}</td><td>{saved.has(row.step) ? (jp ? '保存あり' : 'Saved') : '—'}</td></tr>)}</tbody>
        </table></div></details>
      </>}
    <details className="nsv-details nsv-method"><summary>{jp ? '計算式・読み方・引用' : 'Formula, interpretation and references'}</summary>
      <p>{jp ? '正のノイズレベルは論文の式(11)にあるρ間隔のスケジュールを参照しています。σの下がり方と推定精度の向上は同じ意味ではありません。' : 'Positive noise levels follow the ρ-spaced schedule referenced in paper Eq. (11). Decreasing σ does not itself demonstrate improving reconstruction accuracy.'} <a href="https://arxiv.org/html/2608.24558v3#S3.SS2" target="_blank" rel="noreferrer">ADEPS §3.2 / Eq. (11)</a> · <a href="https://arxiv.org/abs/2206.00364" target="_blank" rel="noreferrer">EDM [19]</a></p>
      <code>σᵢ = [σmax^(1/ρ) + i/(M−1) · (σmin^(1/ρ) − σmax^(1/ρ))]^ρ<br/>i = 0, …, M−1;　σM = 0</code>
      {parameters && <p className="nsv-parameters">σmax = {number(parameters.sigmaMax)}　/　σmin = {number(parameters.sigmaMin)}　/　ρ = {number(parameters.rho)}</p>}
      <p>{jp ? 'この試作ではM個の正のレベルの後に終了用の0を明示的に加え、M回のEuler更新を行います。M−1ではσmin、Mで0です。対数軸に0は置けないため、別の終端欄に表示します。Δσは隣り合うレベルの差です。グラフを読むだけでは推論を実行しません。' : 'This prototype explicitly appends terminal zero after M positive levels and performs M Euler updates: σmin at M−1, then zero at M. Zero cannot lie on a logarithmic axis, so it has a separate terminal strip. Δσ is the difference between consecutive levels. Inspecting this graph does not run inference.'}</p>
    </details>
  </section>;
}

export default NoiseScheduleView;
