'use client';
import { useCallback, useState } from 'react';
import { ArrowRight, Download } from 'lucide-react';
import { useT } from './i18n';
import Scene from './Scene';
import layout from '../../public/reference/synthetic-layout.json';
import { asset } from './assets';
export type LayoutId = 'virtual';
const empty: number[][] = [];
export default function LayoutReference({
  onExperiment,
}: {
  onExperiment: (id: LayoutId) => void;
}) {
  const t = useT();
  const [selected, setSelected] = useState(0);
  const [view, setView] = useState('plan');
  const select = useCallback((i: number) => setSelected(i), []);
  const p = layout.speakers_m[selected];
  return (
    <>
      <div className="context-line">
        <span className="badge">{t('合成データ')}</span>
        <p>
          {t(
            '12台の仮想スピーカー。実在の施設や設置位置を示すものではありません。',
          )}
        </p>
      </div>
      <div className="reference-grid">
        <section className="panel reference-view">
          <div className="panel-head">
            <div>
              <h2>{t('配置を読む')}</h2>
              <p>{t('仮想室 12 × 9 × 4 m · X=幅 / Y=奥行 / Z=高さ')}</p>
            </div>
            <div className="view-toggle">
              <button
                onClick={() => setView('plan')}
                className={view === 'plan' ? 'active' : ''}
              >
                {t('平面')}
              </button>
              <button
                onClick={() => setView('3d')}
                className={view === '3d' ? 'active' : ''}
              >
                3D
              </button>
            </div>
          </div>
          {view === '3d' ? (
            <Scene
              speakers={layout.speakers_m}
              training={empty}
              heldout={empty}
              room={layout.room_dimensions_m}
              selected={selected}
              onSelect={select}
            />
          ) : (
            <svg
              className="layout-plan"
              viewBox="0 0 640 510"
              role="img"
              aria-label={t(
                '仮想スピーカーの平面図。選択すると座標を表示します。',
              )}
            >
              <rect
                x="60"
                y="55"
                width="520"
                height="390"
                fill="none"
                stroke="#555"
              />
              {[0, 3, 6, 9, 12].map((x) => (
                <g key={x}>
                  <line
                    x1={60 + (x * 520) / 12}
                    x2={60 + (x * 520) / 12}
                    y1="55"
                    y2="445"
                    stroke="#252525"
                  />
                  <text x={60 + (x * 520) / 12} y="473" textAnchor="middle">
                    {x}
                  </text>
                </g>
              ))}
              {[0, 3, 6, 9].map((y) => (
                <g key={y}>
                  <line
                    x1="60"
                    x2="580"
                    y1={445 - (y * 390) / 9}
                    y2={445 - (y * 390) / 9}
                    stroke="#252525"
                  />
                  <text x="35" y={449 - (y * 390) / 9}>
                    {y}
                  </text>
                </g>
              ))}
              <text x="300" y="502">
                X / m
              </text>
              <text x="18" y="28">
                Y / m
              </text>
              {layout.speakers_m.map(([x, y], i) => (
                <g
                  key={i}
                  tabIndex={0}
                  role="button"
                  aria-label={`S${i + 1}`}
                  aria-pressed={selected === i}
                  onClick={() => select(i)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      select(i);
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <rect
                    x={60 + (x * 520) / 12 - 7}
                    y={445 - (y * 390) / 9 - 7}
                    width="14"
                    height="14"
                    fill={selected === i ? '#fff' : '#777'}
                  />
                  {selected === i && (
                    <rect
                      x={60 + (x * 520) / 12 - 14}
                      y={445 - (y * 390) / 9 - 14}
                      width="28"
                      height="28"
                      fill="none"
                      stroke="#bbb"
                    />
                  )}
                  <text
                    x={60 + (x * 520) / 12}
                    y={445 - (y * 390) / 9 + 35}
                    textAnchor="middle"
                  >
                    S{i + 1}
                  </text>
                </g>
              ))}
            </svg>
          )}
          <div className="plan-caption">
            {t('枠は合成モデルの室寸法。現地で測定した境界ではありません。')}
          </div>
        </section>
        <section className="panel reference-detail">
          <span className="eyebrow">
            SPEAKER {String(selected + 1).padStart(2, '0')}
          </span>
          <h2>S{selected + 1}</h2>
          <div className="coordinate-values">
            {p.map((v, i) => (
              <div key={i}>
                <span>{['X', 'Y', 'Z'][i]} / m</span>
                <strong>{v.toFixed(2)}</strong>
              </div>
            ))}
          </div>
          <p>
            {t(
              'サンプル座標は計算のための仮定です。実機の配線や出力チャンネルとの対応は設定していません。',
            )}
          </p>
          <button className="primary" onClick={() => onExperiment('virtual')}>
            {t('この配置で実験する')}
            <ArrowRight size={17} />
          </button>
        </section>
      </div>
      <section className="panel reference-table">
        <div className="panel-head">
          <h2>{t('スピーカー座標')}</h2>
          <a href={asset('/reference/synthetic-layout.json')} download>
            <Download size={14} />
            {t('配置JSON')}
          </a>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>X / m</th>
                <th>Y / m</th>
                <th>Z / m</th>
              </tr>
            </thead>
            <tbody>
              {layout.speakers_m.map((point, i) => (
                <tr key={i}>
                  <td>
                    <button onClick={() => select(i)}>S{i + 1}</button>
                  </td>
                  {point.map((v, j) => (
                    <td key={j}>{v.toFixed(2)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
