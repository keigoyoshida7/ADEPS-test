'use client';
import { useT, LocaleProvider, LanguageToggle } from './i18n';
import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AudioLines,
  Box,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  Download,
  FileAudio,
  FlaskConical,
  LoaderCircle,
  Play,
  Radio,
  RotateCcw,
  Settings2,
  ShieldCheck,
  VolumeX,
} from 'lucide-react';
import Scene from './Scene';
import ResearchInfo from './ResearchInfo';
import LayoutReference, { type LayoutId } from './LayoutReference';
import { asset } from './assets';
import MaxReference from './MaxReference';
import NeuralInference from './NeuralInference';
import ModelLab from './ModelLab';
import { analysisApi as api, isLocalEngine } from './scientificClient';
import { Plot, Heatmap, fmt } from './Plots';

type Result = Record<string, any>;
const defaults = {
  lambda_relative: 0.02,
  reflection: 0.35,
  fault_gain_db: -6,
  fault_delay_ms: 3,
  max_column_norm: 2,
};
const captureDefaults = {
  microphones: 8,
  radius_m: 0.06,
  snr_db: 35,
  regularization: 0.001,
  coplanar: false,
  mismatch: true,
  seed: 42,
};
const pages = [
  {
    id: 'layout',
    name: 'スピーカーの配置',
    en: 'SYNTHETIC GEOMETRY',
    icon: Box,
  },
  { id: 'playback', name: '再生系の実験', en: 'PLAYBACK', icon: Box },
  { id: 'paper', name: '論文と実装の範囲', en: 'EVIDENCE', icon: CircleHelp },
  { id: 'model', name: '学習モデル比較', en: 'LEARNED MODEL A/B', icon: FlaskConical },
  { id: 'neural', name: '旧小型モデルの拡散推論', en: 'LEGACY DIFFUSION', icon: FlaskConical },
  {
    id: 'capture',
    name: 'マイク → Ambisonics',
    en: 'LINEAR BASELINE',
    icon: AudioLines,
  },
  { id: 'ir', name: '実測IRを調べる', en: 'MEASUREMENTS', icon: FileAudio },
  { id: 'max', name: 'Max・接続の確認', en: 'LOCAL BRIDGE', icon: Radio },
];
const C = {
  raw: '#a0a0a0',
  train: '#f2f2f2',
  held: '#c0c0c0',
  blue: '#949494',
};
function download(name: string, value: unknown, raw = false) {
  const blob = new Blob(
    [raw ? String(value) : JSON.stringify(value, null, 2)],
    { type: raw ? 'text/csv;charset=utf-8' : 'application/json' },
  );
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Metric({
  label,
  value,
  unit,
  detail,
  tone,
}: {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  tone?: string;
}) {
  return (
    <div className={`metric ${tone || ''}`}>
      <span>{label}</span>
      <div>
        {value}
        <small>{unit}</small>
      </div>
      <p>{detail}</p>
    </div>
  );
}
function Control({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  help,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  min: number;
  max: number;
  step: number;
  unit?: string;
  help?: string;
}) {
  return (
    <label className="control">
      <span>
        {label}
        <strong>
          {value} {unit}
        </strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {help && <small>{help}</small>}
    </label>
  );
}
function Note({
  children,
  tone = '',
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className={`note ${tone}`}>
      <CircleHelp size={17} />
      <div>{children}</div>
    </div>
  );
}
function ResultHeader({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="panel-head">
      <div>
        <h2>{title}</h2>
        {sub && <p>{sub}</p>}
      </div>
      {children}
    </div>
  );
}

export default function Lab() {
  return (
    <LocaleProvider>
      <LabContent />
    </LocaleProvider>
  );
}
function LabContent() {
  const t = useT();

  const [tab, setTab] = useState('layout'),
    [view, setView] = useState('curves');
  const [profile, setProfile] = useState<string>('virtual');
  const [play, setPlay] = useState<Result | null>(null),
    [capture, setCapture] = useState<Result | null>(null),
    [ir, setIR] = useState<Result | null>(null);
  const [config, setConfig] = useState(defaults),
    [capConfig, setCapConfig] = useState(captureDefaults);
  const [geometry, setGeometry] = useState<number[][] | null>(null),
    [dirty, setDirty] = useState(false),
    [capDirty, setCapDirty] = useState(false);
  const [selected, setSelected] = useState(0),
    [freqIndex, setFreqIndex] = useState(35),
    [matrix, setMatrix] = useState('G'),
    [phase, setPhase] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [status, setStatus] = useState<Result | null>(null),
    [runTime, setRunTime] = useState('');
  const [irFile, setIRFile] = useState<File | null>(null),
    [irDirty, setIrDirty] = useState(false),
    [irPoint, setIRPoint] = useState(0),
    [irSpeaker, setIRSpeaker] = useState(0),
    [capFile, setCapFile] = useState<File | null>(null);
  const [history, setHistory] = useState<Result[]>([]),
    [maxMessage, setMaxMessage] = useState<
      string | { key: string; values: unknown[] }
    >('');
  const stableSelect = useCallback((n: number) => setSelected(n), []);
  const loadStatus = useCallback(
    () =>
      api('status')
        .then(setStatus)
        .catch(() => setStatus(null)),
    [],
  );
  async function runPlay(reset = false, nextProfile = profile) {
    setBusy(true);
    setError('');
    try {
      const cfg = reset ? defaults : config;
      const r = await api('playback', {
        ...cfg,
        geometry_profile: nextProfile,
        ...(!reset && geometry ? { speaker_positions: geometry } : {}),
      });
      setPlay(r);
      setProfile(nextProfile);
      setSelected(0);
      setGeometry(r.geometry.speakers_m);
      setDirty(false);
      setRunTime(new Date().toLocaleTimeString('ja-JP'));
      setHistory((h) =>
        [
          {
            time: new Date().toISOString(),
            configuration: r.configuration,
            profile: r.geometry.profile,
            edited: r.provenance.speaker_positions_edited,
            training: r.metrics.training.corrected_nrmse_db,
            heldout: r.metrics.heldout.corrected_nrmse_db,
          },
          ...h,
        ].slice(0, 12),
      );
      if (reset) setConfig(defaults);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function runCapture() {
    setBusy(true);
    setError('');
    try {
      const bundle = capFile ? JSON.parse(await capFile.text()) : undefined;
      const r = await api('capture', {
        ...capConfig,
        ...(bundle !== undefined ? { bundle } : {}),
      });
      setCapture(r);
      setCapDirty(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function runIR() {
    if (!irFile) return;
    setBusy(true);
    setError('');
    try {
      setIR(await api('ir', undefined, await irFile.arrayBuffer()));
      setIRPoint(0);
      setIRSpeaker(0);
      setIrDirty(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void runPlay();
    void loadStatus();
    const timer = setInterval(loadStatus, 2000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (tab === 'capture' && !capture && !busy) void runCapture();
  }, [tab]);
  function changeConfig(key: keyof typeof defaults, value: number) {
    setConfig((c) => ({ ...c, [key]: value }));
    setDirty(true);
  }
  function changeCap(key: string, value: unknown) {
    setCapConfig((c) => ({ ...c, [key]: value }));
    setCapDirty(true);
  }
  async function maxCommand(command: string, channel?: number) {
    try {
      setStatus(await api('max', { command, channel }));
      setMaxMessage(
        command === 'ping'
          ? '確認要求を送りました。応答が届くと状態が変わります。'
          : command === 'mute'
            ? 'ローカルMaxへミュート要求を送信しました。実音の停止はMaxでも確認してください。'
            : {
                key: 'S${channel}をローカルMaxへ送信しました。発音レベルはMaxで手動設定します。',
                values: [channel],
              },
      );
      setTimeout(loadStatus, 250);
    } catch (e) {
      setMaxMessage((e as Error).message);
    }
  }
  const result =
    tab === 'playback'
      ? play
      : tab === 'capture'
        ? capture
        : tab === 'ir'
          ? ir
          : null;
  function exportResult() {
    if (result)
      download(
        `ADEPS_TEST_${tab}_${new Date().toISOString().slice(0, 19).replaceAll(':', '-')}.json`,
        {
          export_schema: 'adeps-test-lab-run/1',
          exported_at: new Date().toISOString(),
          app_version: '0.4.0',
          result,
        },
      );
  }
  function exportCSV() {
    if (!play) return;
    const t = play.metrics.training,
      h = play.metrics.heldout;
    download(
      'ADEPS_TEST_synthetic_frequency_errors.csv',
      'frequency_hz,training_raw_nrmse_db,training_corrected_nrmse_db,heldout_raw_nrmse_db,heldout_corrected_nrmse_db\n' +
        play.frequencies_hz
          .map((f: number, i: number) =>
            [
              f,
              t.raw_error_db_by_frequency[i],
              t.corrected_error_db_by_frequency[i],
              h.raw_error_db_by_frequency[i],
              h.corrected_error_db_by_frequency[i],
            ].join(','),
          )
          .join('\n'),
      true,
    );
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-symbol">
            <AudioLines size={27} />
          </span>
          <div>
            ADEPS<span>test</span>
          </div>
        </div>
        <div className="sidebar-label">EXPERIMENT WORKSPACE</div>
        <nav>
          {pages.map((p) => (
            <button
              key={p.id}
              className={tab === p.id ? 'active' : ''}
              onClick={() => {
                setTab(p.id);
                setError('');
              }}
            >
              <p.icon size={20} />
              <span>
                {t(p.name)}
                <small>{p.en}</small>
              </span>
              {tab === p.id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div>
            <span className={`dot ${status ? 'on' : ''}`} />
            {status
              ? t(isLocalEngine ? '解析エンジン 接続中' : 'ブラウザ内で計算')
              : t('計算エンジンを準備中')}
          </div>
          <div>
            <span className={`dot ${status?.max_reply ? 'on' : ''}`} />
            Max {status?.max_reply ? t('応答あり') : t('応答なし')}
          </div>
          <p>
            RESEARCH PROTOTYPE · 0.4
            <br />
            2026.09.11 / RESEARCH USE
          </p>
          <span className="silent">
            <VolumeX size={14} />
            {t('ブラウザから音は出ません')}
          </span>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <span className="eyebrow">SPATIAL AUDIO / ADEPS-test</span>
            <h1>{t(pages.find((p) => p.id === tab)?.name)}</h1>
          </div>
          <div className="top-actions">
            <LanguageToggle />
            <span className="badge">{t('独自学習モデル · 実験用')}</span>
            {result && (
              <button onClick={exportResult}>
                <Download size={16} />
                {t('結果JSON')}
              </button>
            )}
          </div>
        </header>
        {error && (
          <div className="error" role="alert">
            {t(error)}
            <button onClick={() => setError('')}>{t('閉じる')}</button>
          </div>
        )}
        {!status && (
          <Note tone="warn">
            {t(
              '計算エンジンを準備しています。初回は必要なデータの読み込みに時間がかかります。',
            )}
          </Note>
        )}
        <div hidden={tab !== 'neural'}><NeuralInference /></div>
        <div hidden={tab !== 'model'}><ModelLab /></div>
        {tab === 'layout' && (
          <LayoutReference
            onExperiment={(id: LayoutId) => {
              setTab('playback');
              void runPlay(true, id);
            }}
          />
        )}
        {tab === 'playback' && (
          <>
            <div className="context-line">
              <span className="badge cyan">{t('合成データ')}</span>
              <p>
                {t(
                  '仮想配置を使った合成実験。実在の施設の測定結果ではありません。',
                )}
              </p>
              <span>{t('試作手法：周波数ごとの線形補正')}</span>
            </div>
            <div className="work-grid">
              <section className="panel scene-panel">
                <ResultHeader
                  title={t('空間を見ながら、検証する')}
                  sub={t('仮想室 12 × 9 × 4 m · X=幅 / Y=奥行 / Z=高さ')}
                >
                  <span className="badge">WebGL</span>
                </ResultHeader>
                {play && geometry ? (
                  <Scene
                    speakers={geometry}
                    training={play.geometry.training_points_m}
                    heldout={play.geometry.heldout_points_m}
                    room={play.geometry.room_dimensions_m}
                    origin={play.geometry.room_origin_m}
                    selected={selected}
                    onSelect={stableSelect}
                  />
                ) : (
                  <div className="scene loading">
                    <LoaderCircle className="spin" />
                    {t('数値モデルを計算中…')}
                  </div>
                )}
                <div className="scene-legend">
                  <span>
                    <i className="speaker-dot" />
                    {t('S：スピーカー 12')}
                  </span>
                  <span>
                    <i className="train-dot" />
                    {t('M：調整に使う9点')}
                  </span>
                  <span>
                    <i className="held-dot" />
                    {t('V：調整に使わない6点')}
                  </span>
                </div>
                {geometry && (
                  <div className="position-editor">
                    <label>
                      {t('選択')}
                      <select
                        value={selected}
                        onChange={(e) => setSelected(+e.target.value)}
                      >
                        {geometry.map((_, i) => (
                          <option key={i} value={i}>
                            S{i + 1} · {play?.geometry.speaker_names?.[i] || ''}
                          </option>
                        ))}
                      </select>
                    </label>
                    {['X', 'Y', 'Z'].map((axis, i) => (
                      <label key={axis}>
                        {axis} / m
                        <input
                          type="number"
                          min={(play?.geometry.room_origin_m?.[i] || 0) + 0.05}
                          max={
                            (play?.geometry.room_origin_m?.[i] || 0) +
                            (play?.geometry.room_dimensions_m?.[i] || 1) -
                            0.05
                          }
                          step="0.05"
                          value={geometry[selected]?.[i] ?? 0}
                          onChange={(e) => {
                            const v = Number(e.target.value);
                            setGeometry((g) =>
                              g!.map((p, n) =>
                                n === selected
                                  ? p.map((x, k) => (k === i ? v : x))
                                  : p,
                              ),
                            );
                            setDirty(true);
                          }}
                        />
                      </label>
                    ))}
                    <span>{t('配置変更後に再計算')}</span>
                  </div>
                )}
              </section>
              <section className="panel controls-panel">
                <ResultHeader
                  title={t('実験条件')}
                  sub={t('反射と機器誤差を加えて比較')}
                />
                <Control
                  label={t('正則化 λ（相対値）')}
                  value={config.lambda_relative}
                  min={0.001}
                  max={1}
                  step={0.001}
                  onChange={(v) => changeConfig('lambda_relative', v)}
                  help={t('大きくすると逆補正を抑える。改善は保証されません。')}
                />
                <Control
                  label={t('壁の反射係数')}
                  value={config.reflection}
                  min={0}
                  max={0.8}
                  step={0.05}
                  onChange={(v) => changeConfig('reflection', v)}
                  help={t('一次反射の圧力振幅。吸音率・RT60ではありません。')}
                />
                <div className="control-group-title">
                  S1{profile !== 'virtual' ? ' / Front C' : ''}{' '}
                  {t('に加える仮想の誤差')}
                </div>
                <Control
                  label={t('ゲイン差')}
                  value={config.fault_gain_db}
                  min={-18}
                  max={6}
                  step={1}
                  unit="dB"
                  onChange={(v) => changeConfig('fault_gain_db', v)}
                />
                <Control
                  label={t('追加遅延')}
                  value={config.fault_delay_ms}
                  min={0}
                  max={10}
                  step={0.25}
                  unit="ms"
                  onChange={(v) => changeConfig('fault_delay_ms', v)}
                />
                <Control
                  label={t('補正の列ノルム上限')}
                  value={config.max_column_norm}
                  min={0.5}
                  max={4}
                  step={0.25}
                  onChange={(v) => changeConfig('max_column_norm', v)}
                  help={t(
                    '単一入力時のモデル内エネルギー制約。音量リミッターではありません。',
                  )}
                />
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => runPlay()}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <Play size={17} />
                  )}
                  {t('条件を計算する')}
                </button>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => runPlay(true)}
                >
                  <RotateCcw size={14} />
                  {t('初期条件に戻す')}
                </button>
              </section>
            </div>
            {dirty && (
              <Note tone="warn">
                {t(
                  '条件を変更しました。以下の結果は前回の計算です。「条件を計算する」で更新してください。',
                )}
              </Note>
            )}
            {play && (
              <>
                <div className="metrics">
                  <Metric
                    label={t('調整に使った9点')}
                    value={fmt(play.metrics.training.corrected_nrmse_db)}
                    unit="dB"
                    detail={t(
                      '補正前 ${fmt(play.metrics.training.raw_nrmse_db)} dB → 補正後',
                      [fmt(play.metrics.training.raw_nrmse_db)],
                    )}
                    tone="good"
                  />
                  <Metric
                    label={t('調整に使わない6点')}
                    value={fmt(play.metrics.heldout.corrected_nrmse_db)}
                    unit="dB"
                    detail={t(
                      '補正前 ${fmt(play.metrics.heldout.raw_nrmse_db)} dB → 補正後',
                      [fmt(play.metrics.heldout.raw_nrmse_db)],
                    )}
                    tone={
                      play.metrics.heldout.improvement_db < 0 ? 'warn' : 'good'
                    }
                  />
                  <Metric
                    label={t('未使用点での変化')}
                    value={fmt(Math.abs(play.metrics.heldout.improvement_db))}
                    unit="dB"
                    detail={
                      play.metrics.heldout.improvement_db < 0
                        ? t('悪化：現条件での補正は採用できません')
                        : t('改善：この合成モデル・評価点での結果')
                    }
                    tone={
                      play.metrics.heldout.improvement_db < 0 ? 'warn' : 'good'
                    }
                  />
                  <Metric
                    label={t('観測できる自由度')}
                    value={`${Math.min(...play.fit_diagnostics.rank)} / ${geometry?.length}`}
                    detail={t('最小rank / スピーカー数。全周波数を確認。')}
                  />
                </div>
                <Note
                  tone={play.metrics.heldout.improvement_db < 0 ? 'warn' : ''}
                >
                  <strong>
                    {play.metrics.heldout.improvement_db < 0
                      ? t(
                          '調整点で良くなっても、空間全体で良くなるとは限りません。',
                        )
                      : t('この結果は合成条件での検証です。')}
                  </strong>{' '}
                  {t(
                    'NRMSEは小さいほど良好。0 dBは「誤差の大きさが目標と同じ」です。未使用点を見ながら条件を選んだ場合、最後に別のテスト点を用意してください。',
                  )}
                </Note>
                <section className="panel results">
                  <div className="result-tabs">
                    {[
                      ['curves', t('周波数と各ch')],
                      ['matrix', t('補正行列・rank')],
                      ['tradeoff', t('正則化の比較')],
                      ['geometry', t('配置と経路')],
                      ['history', t('実行履歴')],
                    ].map(([id, name]) => (
                      <button
                        key={id}
                        className={view === id ? 'active' : ''}
                        onClick={() => setView(id)}
                      >
                        {name}
                      </button>
                    ))}
                    <small>
                      {t('最終計算')}
                      {runTime}
                    </small>
                  </div>
                  {view === 'curves' && (
                    <>
                      <ResultHeader
                        title={t('目標からの誤差')}
                        sub={t(
                          '80–8,000 Hz / 64周波数。複素振幅と位相を含むNRMSE。',
                        )}
                      >
                        <button onClick={exportCSV}>
                          <Download size={15} />
                          CSV
                        </button>
                      </ResultHeader>
                      <Plot frequency
                        x={play.frequencies_hz}
                        label={t('誤差が低いほど良好')}
                        series={[
                          {
                            name: t('調整点・補正前'),
                            values:
                              play.metrics.training.raw_error_db_by_frequency,
                            color: C.raw,
                            dash: '2 4',
                          },
                          {
                            name: t('調整点・補正後'),
                            values:
                              play.metrics.training
                                .corrected_error_db_by_frequency,
                            color: C.train,
                          },
                          {
                            name: t('未使用点・補正前'),
                            values:
                              play.metrics.heldout.raw_error_db_by_frequency,
                            color: C.blue,
                            dash: '8 4',
                          },
                          {
                            name: t('未使用点・補正後'),
                            values:
                              play.metrics.heldout
                                .corrected_error_db_by_frequency,
                            color: C.held,
                            dash: '10 3 2 3',
                          },
                        ]}
                      />
                      <ResultHeader
                        title={t('入力チャンネルごとの未使用点での誤差')}
                        sub={t(
                          'Gは他のスピーカーにも信号を配るため、S1の故障が別の入力chにも影響します。',
                        )}
                      />
                      <div className="table-scroll">
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>{t('入力ch')}</th>
                                <th>{t('補正前 / dB')}</th>
                                <th>{t('補正後 / dB')}</th>
                                <th>{t('変化')}</th>
                                <th>{t('選択')}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {play.metrics.heldout.raw_error_db_by_channel.map(
                                (raw: number, i: number) => {
                                  const corrected =
                                    play.metrics.heldout
                                      .corrected_error_db_by_channel[i];
                                  return (
                                    <tr
                                      key={i}
                                      className={
                                        selected === i ? 'selected' : ''
                                      }
                                    >
                                      <td>{i + 1}</td>
                                      <td>{fmt(raw)}</td>
                                      <td>{fmt(corrected)}</td>
                                      <td
                                        className={
                                          raw < corrected
                                            ? 'negative'
                                            : 'positive'
                                        }
                                      >
                                        {fmt(Math.abs(raw - corrected))} dB{' '}
                                        {raw < corrected
                                          ? t('悪化')
                                          : t('改善')}
                                      </td>
                                      <td>
                                        <button onClick={() => setSelected(i)}>
                                          S{i + 1}
                                          {t('を見る')}
                                        </button>
                                      </td>
                                    </tr>
                                  );
                                },
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      <Plot frequency
                        x={play.frequencies_hz}
                        label={t('入力ch ${selected + 1} / 未使用点', [
                          selected + 1,
                        ])}
                        series={[
                          {
                            name: t('補正前'),
                            values:
                              play.metrics.heldout.raw_error_db_frequency_channel.map(
                                (r: number[]) => r[selected],
                              ),
                            color: C.raw,
                          },
                          {
                            name: t('補正後'),
                            values:
                              play.metrics.heldout.corrected_error_db_frequency_channel.map(
                                (r: number[]) => r[selected],
                              ),
                            color: C.held,
                            dash: '10 3 2 3',
                          },
                        ]}
                      />
                    </>
                  )}
                  {view === 'matrix' && (
                    <>
                      <ResultHeader
                        title={t('どの入力を、どの出力へ配るか')}
                        sub={t(
                          'G：物理スピーカー × 目標入力。周波数ごとの複素係数。実機用FIRは未生成。',
                        )}
                      />
                      <div className="matrix-controls">
                        <label>
                          {t('表示')}
                          <select
                            value={matrix}
                            onChange={(e) => setMatrix(e.target.value)}
                          >
                            {Object.keys(play.heatmaps).map((k) => (
                              <option key={k}>{k}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          {t('周波数')}
                          {fmt(play.frequencies_hz[freqIndex], 0)} Hz
                          <input
                            type="range"
                            min="0"
                            max="63"
                            value={freqIndex}
                            onChange={(e) => setFreqIndex(+e.target.value)}
                          />
                        </label>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={phase}
                            onChange={(e) => setPhase(e.target.checked)}
                          />
                          {t('位相を見る')}
                        </label>
                      </div>
                      <Heatmap
                        matrix={
                          play.heatmaps[matrix][
                            phase ? 'phase_deg' : 'magnitude_db'
                          ][freqIndex]
                        }
                        title={
                          matrix === 'G'
                            ? t('縦：スピーカー出力 / 横：目標入力')
                            : t('縦：測定点 / 横：スピーカーまたは目標入力')
                        }
                        phase={phase}
                      />
                      <div className="metrics small-metrics">
                        <Metric
                          label={t('この周波数のrank')}
                          value={`${play.fit_diagnostics.rank[freqIndex]}`}
                          detail={t('スピーカー数未満なら未観測の自由度あり')}
                        />
                        <Metric
                          label={t('非ゼロ特異値の条件数')}
                          value={fmt(
                            play.fit_diagnostics.effective_condition_number[
                              freqIndex
                            ],
                          )}
                          detail={t('rank不足を解消する数値ではありません')}
                        />
                        <Metric
                          label={t('正則化後のGram条件数')}
                          value={fmt(
                            play.fit_diagnostics
                              .regularized_gram_condition_number[freqIndex],
                            1,
                          )}
                          detail={t('計算の安定性を見る補助値')}
                        />
                        <Metric
                          label={t('Gの作用素ノルム')}
                          value={fmt(
                            play.fit_diagnostics.operator_norm_after_cap[
                              freqIndex
                            ],
                          )}
                          detail={t('同時入力時の最大線形ゲイン')}
                        />
                      </div>
                      <div className="singulars">
                        {play.fit_diagnostics.singular_values[freqIndex].map(
                          (v: number, i: number) => (
                            <div key={i}>
                              <span>σ{i + 1}</span>
                              <meter
                                min="0"
                                max={
                                  play.fit_diagnostics.singular_values[
                                    freqIndex
                                  ][0]
                                }
                                value={v}
                              />
                              <b>{fmt(v, 4)}</b>
                            </div>
                          ),
                        )}
                      </div>
                      <Note>
                        {t(
                          'Gは各周波数を独立に解いた解析値です。因果性・遅延・FIR化・出力ヘッドルームを検証するまでは再生機器に適用できません。行列の実部・虚部は「結果JSON」に含まれます。',
                        )}
                      </Note>
                    </>
                  )}
                  {view === 'tradeoff' && (
                    <>
                      <ResultHeader
                        title={t('正則化を変えると、何が変わるか')}
                        sub={t(
                          '同一データで再計算した値です。未使用点の改善を約束するものではありません。',
                        )}
                      />
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>{t('相対λ')}</th>
                              <th>{t('調整点 / dB')}</th>
                              <th>{t('未使用点 / dB')}</th>
                              <th>{t('未使用点の変化')}</th>
                              <th>{t('最大列ノルム')}</th>
                              <th>{t('最大作用素ノルム')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {play.regularization_tradeoff.map((r: Result) => (
                              <tr key={r.lambda_relative}>
                                <td>{r.lambda_relative}</td>
                                <td>{fmt(r.train_corrected_nrmse_db)}</td>
                                <td>{fmt(r.heldout_corrected_nrmse_db)}</td>
                                <td
                                  className={
                                    r.heldout_improvement_db < 0
                                      ? 'negative'
                                      : 'positive'
                                  }
                                >
                                  {fmt(r.heldout_improvement_db)} dB
                                </td>
                                <td>{fmt(r.maximum_column_norm)}</td>
                                <td>{fmt(r.maximum_operator_norm)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="formula">G = (HᴴH + λI)⁻¹ HᴴT</div>
                      <p>
                        {t(
                          'H：観測した伝達行列。T：目標の伝達行列。λ = 相対λ × ‖H‖²F / スピーカー数。解いた後に各列の2ノルムを制限します。12出力を9点で合わせる初期条件は劣決定で、場所に依存する反射にも過適合します。',
                        )}
                      </p>
                    </>
                  )}
                  {view === 'geometry' && (
                    <>
                      <ResultHeader
                        title={t('実験で使った配置')}
                        sub={t(
                          '仮想配置です。上の編集欄では、次の計算に使うスピーカー位置を変更できます。',
                        )}
                      />
                      <div className="two-col">
                        {[
                          ['speakers_m', t('S / スピーカー')],
                          ['training_points_m', t('M / 調整点')],
                          ['heldout_points_m', t('V / 未使用点')],
                        ].map(([key, title]) => (
                          <div key={key}>
                            <h3>{title}</h3>
                            <div className="table-scroll">
                              <table>
                                <thead>
                                  <tr>
                                    <th>{t('番号 / 名前')}</th>
                                    <th>X / m</th>
                                    <th>Y / m</th>
                                    <th>Z / m</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {play.geometry[key].map(
                                    (p: number[], i: number) => (
                                      <tr key={i}>
                                        <td>
                                          {i + 1}
                                          {key === 'speakers_m'
                                            ? ` · ${play.geometry.speaker_names?.[i] || ''}`
                                            : ''}
                                        </td>
                                        {p.map((v, j) => (
                                          <td key={j}>{fmt(v)}</td>
                                        ))}
                                      </tr>
                                    ),
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ))}
                      </div>
                      <h3>{t('合成モデルの経路')}</h3>
                      <p>
                        {t(
                          '直接音＋直方体の6面からの一次反射、音速343 m/s。音圧は1/距離。指向性・高次反射・拡散・マイク特性・非線形は含みません。目標Tは、機器誤差と反射がない直接音のみです。',
                        )}
                      </p>
                    </>
                  )}
                  {view === 'history' && (
                    <>
                      <ResultHeader
                        title={t('このセッションの実行履歴')}
                        sub={t(
                          '最新12件。ブラウザを再読込すると消えます。保存には結果JSONを使用してください。',
                        )}
                      />
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>{t('時刻 / 配置')}</th>
                              <th>λ</th>
                              <th>{t('反射')}</th>
                              <th>S1 gain / delay</th>
                              <th>{t('調整点')}</th>
                              <th>{t('未使用点')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {history.map((r, i) => (
                              <tr key={i}>
                                <td>
                                  {new Date(r.time).toLocaleTimeString('ja-JP')}
                                  <br />
                                  {t('仮想グリッド')}
                                  {r.edited ? t('（配置を編集）') : ''}
                                </td>
                                <td>{r.configuration.lambda_relative}</td>
                                <td>
                                  {
                                    r.configuration
                                      .reflection_pressure_amplitude
                                  }
                                </td>
                                <td>
                                  {r.configuration.fault_gain_db} dB /{' '}
                                  {r.configuration.fault_delay_ms} ms
                                </td>
                                <td>{fmt(r.training)} dB</td>
                                <td>{fmt(r.heldout)} dB</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </section>
              </>
            )}
          </>
        )}
        {tab === 'capture' && (
          <>
            <div className="context-line">
              <span className="badge cyan">{t('線形ベースライン')}</span>
              <p>
                {t(
                  'マイクアレイ → FOA。ADEPSの学習済み拡散モデルは含みません。',
                )}
              </p>
            </div>
            <div className="work-grid">
              <section className="panel">
                <ResultHeader
                  title={t('アレイの復元可能性を調べる')}
                  sub={t(
                    '本試作の既知の伝達モデルVと、線形符号化Eを使います。',
                  )}
                />
                <div className="flow">
                  <div>
                    {t('マイク観測 p')}
                    <small>F × Q × T</small>
                  </div>
                  <ChevronRight />
                  <div>
                    {t('線形符号化 E')}
                    <small>Vᴴ(VVᴴ + γ²I)⁻¹</small>
                  </div>
                  <ChevronRight />
                  <div>
                    {t('FOA推定')}
                    <small>W / Y / Z / X</small>
                  </div>
                </div>
                <Note>
                  {t(
                    '論文のADEPSは、この線形推定に学習済み拡散モデルと観測整合性の勾配を組み合わせます。この画面は比較の出発点となる線形処理だけを検証します。',
                  )}
                </Note>
                {capture && (
                  <>
                    <div className="metrics three">
                      <Metric
                        label={t('参照との複素NRMSE')}
                        value={fmt(capture.quality.complex_nrmse_db)}
                        unit="dB"
                        detail={
                          capture.quality.reference_available
                            ? t('本試作の参照と比較。小さいほど良好。')
                            : t('参照なし：品質を算出しません')
                        }
                      />
                      <Metric
                        label={t('平均coherence')}
                        value={fmt(capture.quality.coherence, 3)}
                        detail={t(
                          '有効な周波数・係数の二乗coherence平均。本試作の定義。',
                        )}
                      />
                      <Metric
                        label={t('最小rank / 係数数')}
                        value={`${capture.rank_min} / ${capture.coefficients}`}
                        detail={t('rank不足の成分は観測だけでは復元困難')}
                        tone={
                          capture.rank_min < capture.coefficients ? 'warn' : ''
                        }
                      />
                    </div>
                    <Plot frequency
                      x={capture.curves.frequency_hz}
                      label={t('線形符号化の診断')}
                      series={[
                        {
                          name: t('マイク空間の相対残差'),
                          values: capture.curves.residual_db,
                          color: C.raw,
                        },
                        ...(capture.curves.error_db
                          ? [
                              {
                                name: t('参照に対するFOA誤差'),
                                values: capture.curves.error_db,
                                color: C.train,
                              },
                            ]
                          : []),
                      ]}
                    />
                    <p className="muted">
                      {t(
                        '残差が小さいことだけでは、空間表現の正しさを示せません。SI-SDRは未算出です。',
                      )}
                    </p>
                  </>
                )}
              </section>
              <section className="panel controls-panel">
                <ResultHeader
                  title={t('アレイ条件')}
                  sub={t('合成デモの条件。論文の実験設定ではありません。')}
                />
                <label className="select-label">
                  {t('マイク数')}
                  <select
                    value={capConfig.microphones}
                    onChange={(e) => changeCap('microphones', +e.target.value)}
                  >
                    {[4, 6, 8, 12, 16].map((n) => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                </label>
                <Control
                  label={t('アレイ半径')}
                  value={capConfig.radius_m}
                  unit="m"
                  min={0.01}
                  max={0.25}
                  step={0.01}
                  onChange={(v) => changeCap('radius_m', v)}
                />
                <Control
                  label={t('観測SNR')}
                  value={capConfig.snr_db}
                  unit="dB"
                  min={0}
                  max={80}
                  step={5}
                  onChange={(v) => changeCap('snr_db', v)}
                />
                <label className="select-label">
                  {t('相対正則化')}
                  <select
                    value={capConfig.regularization}
                    onChange={(e) =>
                      changeCap('regularization', +e.target.value)
                    }
                  >
                    {[0.00000001, 0.000001, 0.0001, 0.001, 0.01, 0.1, 1].map(
                      (n) => (
                        <option key={n}>{n}</option>
                      ),
                    )}
                  </select>
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={capConfig.coplanar}
                    onChange={(e) => changeCap('coplanar', e.target.checked)}
                  />
                  {t('マイクを同一平面に置く')}
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={capConfig.mismatch}
                    onChange={(e) => changeCap('mismatch', e.target.checked)}
                  />
                  {t('観測は3次・推定は1次にする')}
                </label>
                <p className="muted">
                  {t('不一致をオフにすると観測も1次になります。')}
                </p>
                <hr />
                <label className="file-label">
                  {t('V・マイクSTFTのJSONを読む')}
                  <input
                    type="file"
                    accept=".json,application/json"
                    onChange={(e) => {
                      setCapFile(e.target.files?.[0] || null);
                      setCapDirty(true);
                    }}
                  />
                </label>
                {capFile && (
                  <p className="muted">
                    {t(
                      'JSON選択中は、そのファイルのV・観測データで計算します。上のマイク数・半径・SNR・配置設定は使いません。正則化は有効です。',
                    )}
                  </p>
                )}
                {capFile && (
                  <button
                    onClick={() => {
                      setCapFile(null);
                      setCapDirty(true);
                    }}
                  >
                    {t('読み込みを解除：')}
                    {capFile.name}
                  </button>
                )}
                <button
                  className="primary"
                  disabled={busy}
                  onClick={runCapture}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <Play size={16} />
                  )}
                  {t('線形処理を計算する')}
                </button>
              </section>
            </div>
            {capDirty && (
              <Note tone="warn">
                {t('入力条件が変更されています。結果は前回の計算です。')}
              </Note>
            )}
            {capture && (
              <section className="panel">
                <ResultHeader
                  title={t('伝達モデルと規約')}
                  sub={t('データ由来：${capture.provenance}', [
                    capture.provenance,
                  ])}
                />
                <p>{t(capture.conventions)}</p>
                <div className="two-col">
                  <Heatmap
                    matrix={capture.encoder_magnitude_at_1khz.map(
                      (r: number[]) =>
                        r.map((v) => 20 * Math.log10(Math.max(v, 1e-12))),
                    )}
                    title={t('約1 kHzのE / 縦FOA・横マイク / dB')}
                  />
                  <div>
                    <h3>{t('約1 kHzの特異値')}</h3>
                    {capture.singular_values_at_1khz.map(
                      (v: number, i: number) => (
                        <div className="value-row" key={i}>
                          <span>σ{i + 1}</span>
                          <b>{fmt(v, 6)}</b>
                        </div>
                      ),
                    )}
                  </div>
                </div>
                <details>
                  <summary>{t('マイク座標 / m')}</summary>
                  <pre>
                    {JSON.stringify(capture.microphone_positions_m, null, 2)}
                  </pre>
                </details>
                <h3>{t('読み込み形式')}</h3>
                <p>
                  {t(
                    'schema: adeps-test-array-stft/1。sh_ordering=ACN、sh_normalization=N3DまたはSN3Dが必須。Vの係数数は4以上。V_real/V_imag=[周波数,マイク,係数]、p_real/p_imag=[周波数,マイク,時間]。参照は任意でreference_real/reference_imag=[周波数,最初の4係数,時間]。全て同じSTFT・規約・時刻・レベルを使用します。',
                  )}
                </p>
                <a href={asset('/examples/array-input-schema.json')} download>
                  {t('入力形式サンプルJSON')}
                </a>
              </section>
            )}
          </>
        )}
        {tab === 'ir' && (
          <>
            <div className="context-line">
              <span className="badge">{t('データ読み込み')}</span>
              <p>
                {t(
                  '録音済みのインパルス応答を、同じ時刻原点のまま解析します。',
                )}
              </p>
            </div>
            <section className="panel">
              <ResultHeader
                title={t('IRをまとめたZIPを読み込む')}
                sub={t(
                  '1スピーカーにつき1つのWAV。WAVの各チャンネルは測定マイク。manifest.jsonで順序を指定。',
                )}
              />
              <div className="upload-row">
                <label className="file-label">
                  <FileAudio size={24} />
                  <span>{irFile?.name || t('IR ZIPを選択')}</span>
                  <input
                    type="file"
                    accept=".zip,application/zip"
                    onChange={(e) => {
                      setIRFile(e.target.files?.[0] || null);
                      setIrDirty(true);
                    }}
                  />
                </label>
                <button
                  className="primary"
                  disabled={!irFile || busy}
                  onClick={runIR}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <ChartNoAxesCombined size={16} />
                  )}
                  {t('IRを解析する')}
                </button>
                <a
                  className="button-link"
                  href={asset('/examples/synthetic-IR.zip')}
                  download="ADEPS_test_synthetic_IR_example.zip"
                >
                  <Download size={16} />
                  {t('動作確認用ZIP')}
                </a>
              </div>
              <Note>
                {t(
                  'サンプルZIPは4仮想スピーカー・6仮想測定点の合成データです。実測の目標IRがない場合、到達時刻や応答は表示しますが「補正で何dB改善した」という評価は行いません。',
                )}
              </Note>
            </section>
            {irDirty && ir && (
              <Note tone="warn">
                {t(
                  '新しいファイルが選択されています。以下は前回の解析結果です。「IRを解析する」で更新してください。',
                )}
              </Note>
            )}
            {ir && (
              <>
                <section className="panel">
                  <ResultHeader
                    title={t('読み込んだデータ')}
                    sub={t('由来：${ir.provenance}', [ir.provenance])}
                  />
                  <div className="metrics">
                    <Metric
                      label={t('スピーカー数')}
                      value={String(ir.speakers)}
                      detail={t('speaker_filesの順序')}
                    />
                    <Metric
                      label={t('測定点数')}
                      value={String(ir.microphones)}
                      detail={t('各WAVのチャンネル数')}
                    />
                    <Metric
                      label={t('サンプルレート')}
                      value={fmt(ir.sample_rate / 1000, 1)}
                      unit="kHz"
                      detail={`${ir.samples} samples / ${fmt((ir.samples / ir.sample_rate) * 1000, 1)} ms`}
                    />
                    <Metric
                      label={t('目標IR')}
                      value={ir.target_available ? t('あり') : t('なし')}
                      detail={
                        ir.target_available
                          ? t('申告されたtarget_filesを比較に使用')
                          : t('品質の良否は判定しません')
                      }
                    />
                  </div>
                  <div className="matrix-controls">
                    <label>
                      {t('測定点')}
                      <select
                        value={irPoint}
                        onChange={(e) => setIRPoint(+e.target.value)}
                      >
                        {Array.from({ length: ir.microphones }, (_, i) => (
                          <option key={i} value={i}>
                            M{i + 1}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      {t('スピーカー')}
                      <select
                        value={irSpeaker}
                        onChange={(e) => setIRSpeaker(+e.target.value)}
                      >
                        {Array.from({ length: ir.speakers }, (_, i) => (
                          <option key={i} value={i}>
                            S{i + 1}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <Plot frequency
                    x={ir.frequencies_hz}
                    label={t(
                      'S${irSpeaker + 1} → M${irPoint + 1} / WAVのデジタル振幅基準（SPLではありません）',
                      [irSpeaker + 1, irPoint + 1],
                    )}
                    series={[
                      {
                        name: t('応答振幅'),
                        values: ir.response_db.map(
                          (f: number[][]) => f[irPoint][irSpeaker],
                        ),
                        color: C.train,
                      },
                    ]}
                  />
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>{t('経路')}</th>
                          <th>{t('相対閾値の到達 / ms')}</th>
                          <th>{t('ピーク時刻 / ms')}</th>
                          <th>{t('ピーク振幅')}</th>
                          <th>{t('IRエネルギー')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ir.diagnostics.onset_ms[irPoint].map(
                          (v: number | null, s: number) => (
                            <tr key={s}>
                              <td>
                                S{s + 1} → M{irPoint + 1}
                              </td>
                              <td>{fmt(v, 3)}</td>
                              <td>
                                {fmt(
                                  ir.diagnostics.peak_time_ms[irPoint][s],
                                  3,
                                )}
                              </td>
                              <td>
                                {fmt(
                                  ir.diagnostics.peak_absolute[irPoint][s],
                                  4,
                                )}
                              </td>
                              <td>
                                {fmt(ir.diagnostics.energy[irPoint][s], 5)}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                  </div>
                  {ir.metrics && (
                    <>
                      <h3>{t('指定された目標との比較')}</h3>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>{t('評価点')}</th>
                              <th>{t('補正前 / dB')}</th>
                              <th>{t('補正後 / dB')}</th>
                              <th>{t('改善 / dB（負は悪化）')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(ir.metrics).map(([k, v]) => {
                              const m = v as Result;
                              return (
                                <tr key={k}>
                                  <td>
                                    {k === 'training'
                                      ? t('調整点')
                                      : t('未使用点')}
                                  </td>
                                  <td>{fmt(m.raw_nrmse_db)}</td>
                                  <td>{fmt(m.corrected_nrmse_db)}</td>
                                  <td
                                    className={
                                      m.improvement_db < 0
                                        ? 'negative'
                                        : 'positive'
                                    }
                                  >
                                    {fmt(m.improvement_db)}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      {!ir.metrics.heldout && (
                        <Note tone="warn">
                          {t(
                            '独立した評価点が指定されていないため、空間的な汎化は評価できません。',
                          )}
                        </Note>
                      )}
                    </>
                  )}
                  <details>
                    <summary>{t('manifestと測定条件を確認')}</summary>
                    <pre>{JSON.stringify(ir.manifest, null, 2)}</pre>
                  </details>
                </section>
              </>
            )}
            <section className="panel">
              <h2>{t('実機で測定する前に揃えるもの')}</h2>
              <ol>
                <li>{t('スピーカーIDとDante受信ch、実際のXYZ座標。')}</li>
                <li>
                  {t('全IRで共通の収録時刻原点・サンプルレート・出力ゲイン。')}
                </li>
                <li>{t('調整用の点と、調整に使わない評価用の点。')}</li>
                <li>
                  {t(
                    '比較の意味が明確な目標応答。既知の良好状態や明示した物理モデルなど。',
                  )}
                </li>
              </ol>
              <p>
                {t(
                  'この試作は測定済みIRの解析までです。測定信号の出力・収録・スイープの逆畳み込みは実行しません。ファイルごとの自動時間合わせも行いません。',
                )}
              </p>
              <a href={asset('/examples/manifest-template.json')} download>
                {t('実測用manifestテンプレート')}
              </a>
            </section>
          </>
        )}
        {tab === 'max' && (
          <MaxReference
            local={isLocalEngine}
            status={status}
            message={t(maxMessage)}
            onCommand={maxCommand}
          />
        )}
        {tab === 'paper' && <ResearchInfo onNavigate={setTab} />}
        <footer>
          <FlaskConical size={14} />
          {t('ADEPS-test · 計算と測定の違いを保ったテスト環境')}
          <span>{t('音響モデル・参照・評価点を結果JSONに記録')}</span>
        </footer>
      </main>
    </div>
  );
}
