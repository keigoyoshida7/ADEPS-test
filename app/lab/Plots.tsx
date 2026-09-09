'use client';
import { useT } from './i18n';
import { useState } from 'react';
export const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !Number.isFinite(n) ? '—' : n.toFixed(d);
const dashPattern = (dash?: boolean | string) =>
  typeof dash === 'string' ? dash : dash ? '6 5' : undefined;
const FREQUENCY_TICKS = [1, 10, 100, 1000, 10000, 20000];
const frequencyLabel = (hz: number) =>
  hz >= 1000 ? `${Number((hz / 1000).toFixed(2))} kHz` : `${Number(hz.toFixed(2))} Hz`;
type Series = {
  name: string;
  values: (number | null)[];
  color: string;
  dash?: boolean | string;
};
export function Plot({
  x,
  series,
  label,
  unit = 'dB',
  log = true,
  xLabel,
  frequency = false,
}: {
  x: number[];
  series: Series[];
  label: string;
  unit?: string;
  log?: boolean;
  xLabel?: string;
  frequency?: boolean;
}) {
  const t = useT();

  const [index, setIndex] = useState<number | null>(null);
  const W = 860,
    H = 230,
    L = 58,
    R = 24,
    T = 20,
    B = 34;
  const logarithmic = frequency || log;
  const validX = (i: number) => Number.isFinite(x[i]) &&
    (!logarithmic || x[i] > 0) && (!frequency || (x[i] >= 1 && x[i] <= 20000));
  const visibleIndices = x.flatMap((_, i) => validX(i) &&
    series.some(s => s.values[i] != null && Number.isFinite(s.values[i])) ? [i] : []);
  const values = series.flatMap(s => visibleIndices.map(i => s.values[i]))
    .filter((v): v is number => v != null && Number.isFinite(v));
  if (!values.length || !x.length)
    return <div className="empty">{t('評価可能なデータがありません。')}</div>;
  const activeIndex = index != null && visibleIndices.includes(index) ? index : null;
  const dataMin = x[visibleIndices[0]], dataMax = x[visibleIndices.at(-1)!];
  const domainMin = frequency ? 1 : dataMin, domainMax = frequency ? 20000 : dataMax;
  let lo = Math.min(...values),
    hi = Math.max(...values);
  if (hi - lo < 0.01) {
    lo -= 1;
    hi += 1;
  }
  const pad = (hi - lo) * 0.12;
  lo -= pad;
  hi += pad;
  const xPosition = (value: number) =>
    L +
    ((W - L - R) *
      ((logarithmic ? Math.log(value) : value) - (logarithmic ? Math.log(domainMin) : domainMin))) /
      ((logarithmic ? Math.log(domainMax) : domainMax) -
        (logarithmic ? Math.log(domainMin) : domainMin) || 1);
  const xx = (i: number) => xPosition(x[i]);
  const ticks = frequency ? FREQUENCY_TICKS : [0, .25, .5, .75, 1]
    .map(ratio => x[visibleIndices[Math.round(ratio * (visibleIndices.length - 1))]])
    .filter((value, i, all) => all.indexOf(value) === i);
  const yy = (v: number) => T + ((H - T - B) * (hi - v)) / (hi - lo);
  return (
    <div className="plot-wrap" data-frequency-range={frequency ? '1-20000' : undefined}>
      <div className="plot-key">
        {series.map((s) => (
          <span key={s.name}>
            <svg width="32" height="8" aria-hidden="true">
              <line
                x1="0"
                x2="32"
                y1="4"
                y2="4"
                stroke={s.color}
                strokeWidth="2"
                strokeDasharray={dashPattern(s.dash)}
              />
            </svg>
            {s.name}
          </span>
        ))}
        <small>{label}</small>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="plot"
        role="img"
        aria-label={label}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const px = ((e.clientX - r.left) / r.width) * W;
          // Do not snap to an endpoint while hovering over an unmeasured band.
          if (px < xPosition(dataMin) || px > xPosition(dataMax)) {
            setIndex(null);
            return;
          }
          let k = visibleIndices[0];
          visibleIndices.forEach(i => {
            if (Math.abs(xx(i) - px) < Math.abs(xx(k) - px)) k = i;
          });
          setIndex(k);
        }}
        onMouseLeave={() => setIndex(null)}
      >
        {frequency && <g aria-hidden="true">
          <rect x={L} y={T} width={Math.max(0, xPosition(dataMin) - L)} height={H-T-B} fill="#ffffff" opacity="0.025" />
          <rect x={xPosition(dataMax)} y={T} width={Math.max(0, W-R-xPosition(dataMax))} height={H-T-B} fill="#ffffff" opacity="0.025" />
        </g>}
        {[0, 1, 2, 3, 4].map((i) => {
          const v = lo + ((hi - lo) * i) / 4;
          return (
            <g key={i}>
              <line x1={L} x2={W - R} y1={yy(v)} y2={yy(v)} stroke="#323232" />
              <text x={L - 9} y={yy(v) + 4} textAnchor="end">
                {fmt(v, 1)}
              </text>
            </g>
          );
        })}
        {ticks.map(value => <g key={value}>
          {frequency && <line x1={xPosition(value)} x2={xPosition(value)} y1={T} y2={H-B} stroke="#242424" />}
          <text x={xPosition(value)} y={H - 9} textAnchor="middle">
            {frequency ? frequencyLabel(value) : value >= 1000 ? `${fmt(value / 1000, 1)}k` : fmt(value, 0)}
          </text>
        </g>)}
        {series.map((s) => (
          <path
            key={s.name}
            fill="none"
            stroke={s.color}
            strokeWidth={2.2}
            strokeDasharray={
              typeof s.dash === 'string' ? s.dash : s.dash ? '6 5' : undefined
            }
            d={s.values
              .map((v, i) =>
                v == null || !Number.isFinite(v) || !validX(i)
                  ? ''
                  : `${i === 0 || !validX(i-1) || s.values[i-1] == null || !Number.isFinite(s.values[i-1]) ? 'M' : 'L'}${xx(i)},${yy(v)}`,
              )
              .join(' ')}
          />
        ))}
        {activeIndex != null && (
          <line
            x1={xx(activeIndex)}
            x2={xx(activeIndex)}
            y1={T}
            y2={H - B}
            stroke="#aaaaaa"
            strokeDasharray="3 3"
          />
        )}
      </svg>
      <div className="plot-readout">
        {activeIndex != null ? (
          <>
            <strong>
              {fmt(x[activeIndex], frequency ? 2 : 0)} {xLabel || (logarithmic ? 'Hz' : '')}
            </strong>
            {series.map((s) => (
              <span key={s.name} style={{ color: s.color }}>
                {s.name} {fmt(s.values[activeIndex])} {unit}
              </span>
            ))}
          </>
        ) : (
          <span>
            {t('グラフ上で各点の値を確認できます。横軸：')}
            {frequency ? t('周波数 / Hz（対数）') : xLabel || (log ? t('周波数 / Hz（対数）') : 'index')}
            {t('縦軸：')}
            {unit}
          </span>
        )}
      </div>
      {frequency && <p className="plot-coverage">
        <span>{t('表示：1 Hz〜20 kHz（対数）')}</span>
        <span>{t('表示帯域内のデータ：')}{frequencyLabel(dataMin)} – {frequencyLabel(dataMax)}</span>
        <span>{t('データのない帯域には曲線を描きません。')}</span>
      </p>}
    </div>
  );
}
export function Heatmap({
  matrix,
  title,
  phase = false,
}: {
  matrix: number[][];
  title: string;
  phase?: boolean;
}) {
  const t = useT();

  if (!matrix?.length) return null;
  const cells = matrix.flat().filter(Number.isFinite);
  const lo = phase ? -180 : Math.max(-60, Math.min(...cells)),
    hi = phase ? 180 : Math.max(lo + 1, ...cells);
  return (
    <div className="heat">
      <div className="subheading">
        {title}
        <span>
          {phase
            ? t('暗 −180° → 明 +180°（角度の大小）')
            : t('暗 ${fmt(lo, 0)} → 明 ${fmt(hi, 0)} dB', [
                fmt(lo, 0),
                fmt(hi, 0),
              ])}
        </span>
      </div>
      <div
        className="heat-grid"
        style={{ gridTemplateColumns: `32px repeat(${matrix[0].length},1fr)` }}
      >
        <b />
        {matrix[0].map((_, i) => (
          <b key={i}>{i + 1}</b>
        ))}
        {matrix.map((row, r) => (
          <div className="heat-row" key={r}>
            <b>{r + 1}</b>
            {row.map((v, c) => {
              const a = Math.min(1, Math.max(0, (v - lo) / (hi - lo)));
              return (
                <div
                  key={c}
                  className="heat-cell"
                  style={{
                    background: `hsl(0 0% ${12 + a * 76}%)`,
                    color: a > 0.45 ? '#101010' : '#eeeeee',
                  }}
                  title={t(
                    "行${r + 1} / 列${c + 1}: ${fmt(v)} ${phase ? '°' : 'dB'}",
                    [r + 1, c + 1, fmt(v), phase ? '°' : 'dB'],
                  )}
                >
                  {fmt(v, 0)}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
