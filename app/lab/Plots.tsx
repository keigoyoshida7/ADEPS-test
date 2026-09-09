'use client';
import { useT } from './i18n';
import { useState } from 'react';
export const fmt = (n: number | null | undefined, d = 2) =>
  n == null || !Number.isFinite(n) ? '—' : n.toFixed(d);
const dashPattern = (dash?: boolean | string) =>
  typeof dash === 'string' ? dash : dash ? '6 5' : undefined;
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
}: {
  x: number[];
  series: Series[];
  label: string;
  unit?: string;
  log?: boolean;
}) {
  const t = useT();

  const [index, setIndex] = useState<number | null>(null);
  const W = 860,
    H = 230,
    L = 58,
    R = 24,
    T = 20,
    B = 34;
  const values = series
    .flatMap((s) => s.values)
    .filter((v): v is number => v != null && Number.isFinite(v));
  if (!values.length || !x.length)
    return <div className="empty">{t('評価可能なデータがありません。')}</div>;
  let lo = Math.min(...values),
    hi = Math.max(...values);
  if (hi - lo < 0.01) {
    lo -= 1;
    hi += 1;
  }
  const pad = (hi - lo) * 0.12;
  lo -= pad;
  hi += pad;
  const xx = (i: number) =>
    L +
    ((W - L - R) *
      ((log ? Math.log(x[i]) : x[i]) - (log ? Math.log(x[0]) : x[0]))) /
      ((log ? Math.log(x.at(-1)!) : x.at(-1)!) -
        (log ? Math.log(x[0]) : x[0]) || 1);
  const yy = (v: number) => T + ((H - T - B) * (hi - v)) / (hi - lo);
  return (
    <div className="plot-wrap">
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
          let k = 0;
          x.forEach((_, i) => {
            if (Math.abs(xx(i) - px) < Math.abs(xx(k) - px)) k = i;
          });
          setIndex(k);
        }}
        onMouseLeave={() => setIndex(null)}
      >
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
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const i = Math.round(t * (x.length - 1));
          return (
            <text key={t} x={xx(i)} y={H - 9} textAnchor="middle">
              {x[i] >= 1000 ? `${fmt(x[i] / 1000, 1)}k` : fmt(x[i], 0)}
            </text>
          );
        })}
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
                v == null
                  ? ''
                  : `${i === 0 || s.values[i - 1] == null ? 'M' : 'L'}${xx(i)},${yy(v)}`,
              )
              .join(' ')}
          />
        ))}
        {index != null && (
          <line
            x1={xx(index)}
            x2={xx(index)}
            y1={T}
            y2={H - B}
            stroke="#aaaaaa"
            strokeDasharray="3 3"
          />
        )}
      </svg>
      <div className="plot-readout">
        {index != null ? (
          <>
            <strong>
              {fmt(x[index], 0)} {log ? 'Hz' : ''}
            </strong>
            {series.map((s) => (
              <span key={s.name} style={{ color: s.color }}>
                {s.name} {fmt(s.values[index])} {unit}
              </span>
            ))}
          </>
        ) : (
          <span>
            {t('グラフ上で周波数ごとの値を確認できます。横軸：')}
            {log ? t('周波数 / Hz（対数）') : 'index'}
            {t('縦軸：')}
            {unit}
          </span>
        )}
      </div>
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
