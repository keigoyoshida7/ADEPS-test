export const paperMetricKeys = ['si_sdr_db', 'spectral_error_db', 'coherence', 'ild_error_db', 'ic_error'] as const;
export type PaperMetricKey = typeof paperMetricKeys[number];
export type PaperScores = Record<PaperMetricKey, number | null>;
export type PaperCurves = Record<'spectral_error_db' | 'coherence' | 'ild_error_db' | 'ic_error', (number | null)[]>;
export type PaperProfile = 'strict' | 'reference_floor';
export type PaperSceneResult = { metrics: PaperScores; curves: PaperCurves; sensitivity: Record<string, unknown> };
export type PaperComparison = {
  schema: 'adeps-paper-comparison/1'; status: 'evaluated'; evaluation_kind: 'post_hoc_fixed_estimates';
  original_paper_reproduced: false; source_benchmark_sha256: string; created_at: string;
  methods: { id: string; label_jp: string; label_en: string }[];
  conditions: { scenes: number; microphones: number; sample_rate_hz: number };
  frequencies_hz: number[]; binaural_frequencies_hz: number[];
  scenes: { id: string; cluster_id: string; profiles: Record<PaperProfile, Record<string, PaperSceneResult>> }[];
  profiles: Record<PaperProfile, { means: Record<string, PaperScores>; finite_scene_counts: Record<string, Record<PaperMetricKey, number>>; curves: Record<string, PaperCurves> }>;
  definitions: Record<string, unknown>;
  provenance: { reference_sha256: string; source_sha256: Record<string, string> };
};
export type PaperReference = {
  schema: 'adeps-paper-reference/1';
  source: { title: string; authors: string[]; version: string; html_url: string; pdf_url: string };
  tables: { number: number; title: string; source_url: string; N_eff: number; N_p: number; N_enc: number;
    array_ids: string[]; rows: { method_id: string; label: string; values: Record<string, PaperScores> }[] }[];
};

const isObject = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const hash = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const safeUrl = (v: unknown) => {
  if (typeof v !== 'string') return false;
  try { const u = new URL(v); return u.protocol === 'https:' && !u.username && !u.password; } catch { return false; }
};
function value(key: PaperMetricKey, v: unknown) {
  return v === null || finite(v) && (key === 'si_sdr_db' || v >= 0) && (key !== 'coherence' || v <= 1) && (key !== 'ic_error' || v <= 2);
}
const scores = (v: unknown): v is PaperScores => isObject(v) && paperMetricKeys.every(k => value(k, v[k]));
const same = (a: number | null, b: number | null) => a === null || b === null ? a === b : Math.abs(a - b) <= 1e-8 * Math.max(1, Math.abs(a), Math.abs(b));
const average = (a: (number | null)[]) => a.every(finite) ? a.reduce((sum, v) => sum + v / a.length, 0) : null;

export function validPaperReference(data: unknown): data is PaperReference {
  if (!isObject(data)) return false;
  const d = data as unknown as PaperReference;
  return d.schema === 'adeps-paper-reference/1' && isObject(d.source) && typeof d.source.title === 'string'
    && d.source.version === 'v3' && d.source.html_url === 'https://arxiv.org/html/2608.24558v3'
    && safeUrl(d.source.pdf_url) && Array.isArray(d.tables) && d.tables.length === 3
    && d.tables.every((t, i) => isObject(t) && t.number === i + 1 && safeUrl(t.source_url)
      && [t.N_eff, t.N_p, t.N_enc].every(finite) && typeof t.title === 'string'
      && Array.isArray(t.array_ids) && t.array_ids.length > 0 && new Set(t.array_ids).size === t.array_ids.length
      && t.array_ids.every(id => typeof id === 'string') && Array.isArray(t.rows) && t.rows.length > 0
      && t.rows.every(isObject) && new Set(t.rows.map(r => r.method_id)).size === t.rows.length && t.rows.every(r => isObject(r)
        && typeof r.method_id === 'string' && typeof r.label === 'string' && isObject(r.values)
        && t.array_ids.every(id => scores(r.values[id]) && paperMetricKeys.every(k => r.values[id][k] !== null))));
}

export function validPaperComparison(data: unknown, original: {
  methods: { id: string }[]; scenes: { id: string; cluster_id: string; metrics: Record<string, { si_sdr_db: number | null }> }[];
}, sourceSha256: string): data is PaperComparison {
  if (!isObject(data)) return false;
  const d = data as unknown as PaperComparison;
  if (d.schema !== 'adeps-paper-comparison/1' || d.status !== 'evaluated' || d.evaluation_kind !== 'post_hoc_fixed_estimates'
    || d.original_paper_reproduced !== false || !hash(sourceSha256) || d.source_benchmark_sha256 !== sourceSha256 || !isObject(d.provenance)
    || !hash(d.provenance.reference_sha256) || !isObject(d.definitions) || !isObject(d.conditions)
    || d.conditions.scenes !== original.scenes.length || d.conditions.sample_rate_hz !== 16000
    || !Array.isArray(d.methods) || d.methods.length !== original.methods.length
    || !d.methods.every((m, i) => isObject(m) && m.id === original.methods[i].id && typeof m.label_jp === 'string' && typeof m.label_en === 'string')
    || !Array.isArray(d.scenes) || d.scenes.length !== original.scenes.length || !d.scenes.length
    || !Array.isArray(d.frequencies_hz) || d.frequencies_hz.length !== 257 || !d.frequencies_hz.every((f, i) => f === i * 31.25)
    || !Array.isArray(d.binaural_frequencies_hz) || d.binaural_frequencies_hz.length < 2
    || !d.binaural_frequencies_hz.every((f, i, a) => finite(f) && f > 0 && f < 8000 && (i === 0 || f > a[i - 1]))) return false;
  const ids = d.methods.map(m => m.id);
  function curves(v: unknown): v is PaperCurves {
    return isObject(v) && (['spectral_error_db', 'coherence', 'ild_error_db', 'ic_error'] as const).every(k =>
      Array.isArray(v[k]) && v[k].length === (k === 'coherence' || k === 'spectral_error_db' ? 257 : d.binaural_frequencies_hz.length)
      && v[k].every(n => value(k, n)));
  }
  if (!d.scenes.every((s, i) => isObject(s) && s.id === original.scenes[i].id && s.cluster_id === original.scenes[i].cluster_id
    && isObject(s.profiles) && (['strict', 'reference_floor'] as const).every(p => isObject(s.profiles[p]) && ids.every(id => {
      const r = s.profiles[p][id];
      return isObject(r) && scores(r.metrics) && curves(r.curves)
        && same(r.metrics.si_sdr_db, original.scenes[i].metrics[id].si_sdr_db);
    })))) return false;
  return isObject(d.profiles) && (['strict', 'reference_floor'] as const).every(p => {
    const a = d.profiles[p];
    return isObject(a) && isObject(a.means) && isObject(a.curves) && isObject(a.finite_scene_counts) && ids.every(id =>
      scores(a.means[id]) && curves(a.curves[id]) && isObject(a.finite_scene_counts[id]) && paperMetricKeys.every(k => {
        const numbers = d.scenes.map(s => s.profiles[p][id].metrics[k]);
        return same(a.means[id][k], average(numbers)) && a.finite_scene_counts[id][k] === numbers.filter(finite).length;
      }) && (Object.keys(a.curves[id]) as (keyof PaperCurves)[]).every(k => a.curves[id][k].every((n, i) =>
        same(n, average(d.scenes.map(s => s.profiles[p][id].curves[k][i]))))));
  });
}
