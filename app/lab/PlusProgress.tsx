import { useEffect, useId, useState } from 'react';
import { asset } from './assets';
import './PlusProgress.css';

type Phase = 'development' | 'sealed_test' | 'exporting' | 'complete' | 'failed';
type Count = { label_jp: string; label_en: string; completed: number; total: number };
export type PlusProgressRecord = Count & {
  schema: 'adeps-plus-progress/1'; phase: Phase; updated_at: string;
  detail_jp: string; detail_en: string; phase_counts?: Count[];
};
const phases: Record<Phase, [string, string]> = {
  development: ['開発データで確認中', 'Development evaluation'],
  sealed_test: ['未使用データで評価中', 'Held-out evaluation'],
  exporting: ['結果を書き出し中', 'Exporting results'],
  complete: ['処理完了', 'Processing complete'],
  failed: ['処理の失敗を記録', 'Failure recorded'],
};
const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
const count = (value: unknown): value is number => Number.isSafeInteger(value) && typeof value === 'number' && value >= 0;
const validCount = (value: unknown): value is Count => object(value) && text(value.label_jp) && text(value.label_en)
  && count(value.completed) && count(value.total) && value.completed <= value.total;

/** A saved count is progress evidence, never a reconstruction-quality score. */
export function validPlusProgress(value: unknown): value is PlusProgressRecord {
  if (!object(value) || !validCount(value)) return false;
  const r = value as unknown as PlusProgressRecord;
  return r.schema === 'adeps-plus-progress/1' && Object.hasOwn(phases, r.phase)
    && text(r.updated_at) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(r.updated_at)
    && Number.isFinite(Date.parse(r.updated_at))
    && typeof r.detail_jp === 'string' && typeof r.detail_en === 'string'
    && (r.phase !== 'complete' || r.completed === r.total)
    && (r.phase_counts === undefined || Array.isArray(r.phase_counts) && r.phase_counts.length <= 12 && r.phase_counts.every(validCount));
}

export default function PlusProgress({ language, active = true }: { language: 'jp' | 'en'; active?: boolean }) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [record, setRecord] = useState<PlusProgressRecord | null>(null);
  const [error, setError] = useState<'load' | 'invalid' | null>(null);
  const [now, setNow] = useState(Date.now);
  const titleId = useId();
  useEffect(() => {
    if (!active) return;
    let disposed = false, pending = false;
    let request: AbortController | undefined;
    let deadline: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      setNow(Date.now());
      if (pending) return;
      pending = true;
      request = new AbortController();
      const controller = request;
      deadline = setTimeout(() => controller.abort(), 12_000);
      try {
        const response = await fetch(asset('models/plus-progress.json'), { cache: 'no-store', signal: controller.signal });
        if (disposed) return;
        if (response.status === 404) { setRecord(null); setError(null); return; }
        if (!response.ok) throw new Error('Progress unavailable');
        const data: unknown = await response.json();
        if (disposed) return;
        if (!validPlusProgress(data)) { setError('invalid'); return; }
        setRecord(data); setError(null);
      } catch {
        if (!disposed) setError('load');
      } finally {
        clearTimeout(deadline);
        pending = false;
      }
    };
    void refresh();
    const timer = setInterval(() => { void refresh(); }, 15_000);
    return () => { disposed = true; clearInterval(timer); clearTimeout(deadline); request?.abort(); };
  }, [active]);

  if (!active || !record && !error) return null;
  const terminal = record?.phase === 'complete' || record?.phase === 'failed';
  const stale = !!record && !terminal && now - Date.parse(record.updated_at) > 120_000;
  const countLabel = (item: Count) => item.total > 0 ? `${item.completed.toLocaleString()} / ${item.total.toLocaleString()}` : l('件数未確定', 'Total not set');
  const updated = record ? new Date(record.updated_at).toLocaleString(language === 'jp' ? 'ja-JP' : 'en-US', { timeZoneName: 'short' }) : '';
  return <section className="plus-progress" aria-labelledby={titleId} data-terminal={terminal || undefined}>
    <header className="pp-heading">
      <h3 id={titleId}>{l('処理の進行記録', 'Processing progress')}</h3>
      {record && <span className="pp-phase">{l(...phases[record.phase])}</span>}
    </header>
    {record && <>
      <div className="pp-current" aria-live="polite" aria-atomic="true"><span>{l(record.label_jp, record.label_en)}</span><strong>{countLabel(record)}</strong></div>
      {!terminal && record.total > 0 && <progress className="pp-bar" max={record.total} value={record.completed} aria-label={l(record.label_jp, record.label_en)}>{countLabel(record)}</progress>}
      {!terminal && (record.detail_jp || record.detail_en) && <p className="pp-detail">{l(record.detail_jp, record.detail_en)}</p>}
      {record.phase === 'failed' && <p className="pp-detail">{l(record.detail_jp, record.detail_en)}</p>}
      <div className="pp-updated"><span>{l('記録日時', 'Record updated')} <time dateTime={record.updated_at}>{updated}</time></span>
        {stale && <span className="pp-stale">{l('2分以上、記録の更新がありません。', 'No record update for over 2 minutes.')}</span>}
      </div>
      {!terminal && !!record.phase_counts?.length && <details className="pp-counts"><summary>{l('工程ごとの件数', 'Counts by stage')}</summary><dl>{record.phase_counts.map((item, i) => <div key={i}><dt>{l(item.label_jp, item.label_en)}</dt><dd>{countLabel(item)}</dd></div>)}</dl></details>}
    </>}
    {error && <output className="pp-error">{error === 'invalid' ? l('新しい進行記録の形式を確認できません。', 'The latest progress record could not be validated.') : l('進行記録を読み込めません。', 'The progress record could not be loaded.')}
      {record ? l(' 表示は最後に確認できた記録です。', ' The last verified record remains visible.') : l(' 完了状況は未確認です。', ' Completion status is unknown.')}</output>}
    {!terminal && <p className="pp-note">{l('表示中は15秒ごとに記録を確認します。件数は現在の工程の処理数で、精度や成功の予測ではありません。', 'Checks the record every 15 seconds while visible. Counts describe work in this stage, not accuracy or predicted success.')}</p>}
  </section>;
}
