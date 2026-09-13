import { useEffect, useId, useRef, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { asset } from './assets';
import { isLocalEngine } from './scientificClient';
import './MaxComparison.css';

type Method = { id: string; label_jp: string; label_en: string };
type Bank = { id: string; title_jp: string; title_en: string; archive_url: string; duration_seconds: number; samples: number; sample_rate_hz: number; scenes: number; input_sha256: string };
type Catalogue = { schema: 'adeps-max-comparison/1'; methods: Method[]; banks: Bank[]; normalization: 'N3D'; channel_order: string[] };
type Status = { max_reply: boolean; ready: boolean; selected_method: string; input_sha256: string; reply_age_seconds: number | null; acknowledged?: boolean };
const methodIds = ['reference', 'linear_default', 'linear_tuned', 'linear_noise', 'adeps_current', 'adeps_tuned', 'spatial_only', 'consistency_only', 'plus', 'plus_no_denoiser'];
const hash = (value: unknown) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
function catalogue(value: unknown): value is Catalogue {
  if (!value || typeof value !== 'object') return false;
  const r = value as Catalogue;
  return r.schema === 'adeps-max-comparison/1' && r.normalization === 'N3D'
    && Array.isArray(r.channel_order) && r.channel_order.join(',') === 'W,Y,Z,X'
    && Array.isArray(r.methods) && r.methods.length === methodIds.length && methodIds.every(id => r.methods.filter(m => m?.id === id).length === 1)
    && r.methods.every(m => typeof m.label_jp === 'string' && typeof m.label_en === 'string')
    && Array.isArray(r.banks) && r.banks.length > 0 && new Set(r.banks.map(b => b?.id)).size === r.banks.length
    && r.banks.every(b => b && typeof b.id === 'string' && typeof b.title_jp === 'string' && typeof b.title_en === 'string'
      && /^models\/[a-zA-Z0-9_-]+\.zip$/.test(b.archive_url) && hash(b.input_sha256)
      && b.sample_rate_hz === 16000 && Number.isInteger(b.samples) && b.samples > 0
      && Number.isInteger(b.scenes) && b.scenes > 0 && Number.isFinite(b.duration_seconds)
      && Math.abs(b.samples / b.sample_rate_hz - b.duration_seconds) < 1e-6);
}
function status(value: unknown): value is Status {
  if (!value || typeof value !== 'object') return false;
  const s = value as Status;
  return typeof s.max_reply === 'boolean' && typeof s.ready === 'boolean'
    && typeof s.selected_method === 'string' && (!s.selected_method || methodIds.includes(s.selected_method))
    && typeof s.input_sha256 === 'string' && (!s.input_sha256 || hash(s.input_sha256));
}

export default function MaxComparison({ language, selectedMethod, onSelect, active }: {
  language: 'jp' | 'en'; selectedMethod: string; onSelect: (id: string) => void; active: boolean;
}) {
  const jp = language === 'jp', l = (ja: string, en: string) => jp ? ja : en;
  const id = useId(), mounted = useRef(true);
  const requestSerial = useRef(0), busyRef = useRef(false);
  const [data, setData] = useState<Catalogue | null>(null), [failed, setFailed] = useState(false);
  const [bankId, setBankId] = useState('montage'), [connection, setConnection] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [retry, setRetry] = useState(0);
  const bank = data?.banks.find(b => b.id === bankId) ?? data?.banks[0];
  const matching = !!bank && connection?.max_reply && connection.ready && connection.input_sha256 === bank.input_sha256;
  const selected = data?.methods.find(m => m.id === selectedMethod);
  const label = (method: Method) => jp ? method.label_jp : method.label_en;
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    requestSerial.current += 1;
    // A selection change invalidates the description of the previous request.
    // oxlint-disable-next-line react/react-compiler
    setMessage('');
  }, [selectedMethod, bankId, active, language]);
  useEffect(() => {
    if (data && active && window.location.hash === '#max-comparison') document.getElementById('max-comparison')?.scrollIntoView();
  }, [data, active]);
  useEffect(() => {
    const controller = new AbortController();
    void fetch(asset('models/max-comparison.json'), { signal: controller.signal, cache: 'no-cache' })
      .then(async r => { if (!r.ok) throw Error('load'); const v: unknown = await r.json(); if (!catalogue(v)) throw Error('format'); return v; })
      .then(v => { if (!controller.signal.aborted) { setData(v); setFailed(false); } })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    if (!isLocalEngine || !active) return;
    const controller = new AbortController();
    const poll = async () => {
      if (busyRef.current) return;
      const serial = ++requestSerial.current;
      try {
        const r = await fetch('/lab-api/max-compare', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: 'ping' }), signal: controller.signal, cache: 'no-store' });
        const v: unknown = r.ok ? await r.json() : null;
        if (!controller.signal.aborted && requestSerial.current === serial) setConnection(status(v) ? v : null);
      } catch { if (!controller.signal.aborted && requestSerial.current === serial) setConnection(null); }
    };
    void poll(); const timer = setInterval(() => { void poll(); }, 3000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [active]);
  async function command(action: 'ping' | 'select' | 'mute') {
    if (!isLocalEngine || busyRef.current || !active || (action === 'select' && (!bank || !selected))) return;
    busyRef.current = true;
    const serial = ++requestSerial.current;
    setBusy(true); setMessage('');
    const requested = selectedMethod;
    try {
      const r = await fetch('/lab-api/max-compare', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: action, ...(action === 'select' ? { method: requested, expected_input_sha256: bank!.input_sha256 } : {}) }),
        signal: AbortSignal.timeout(6000) });
      const v: unknown = await r.json();
      if (!mounted.current || requestSerial.current !== serial) return;
      if (status(v)) setConnection(v);
      if (!r.ok || !status(v) || !v.max_reply || v.acknowledged !== true) throw Error('connection');
      if (action === 'select' && (v.selected_method !== requested || v.input_sha256 !== bank!.input_sha256)) throw Error('selection');
      setMessage(action === 'select' ? l(`Maxが方式の選択を受け付けました：${selected ? label(selected) : requested}`, `Max accepted the method selection: ${selected ? label(selected) : requested}`)
        : action === 'mute' ? l('Maxがミュート要求を受け付けました。', 'Max accepted the mute request.')
          : l('Maxから応答がありました。', 'Max replied.'));
    } catch { if (mounted.current && requestSerial.current === serial) setMessage(l('操作を確認できませんでした。MaxのNode、読込済みバンク、ローカル接続を確認してください。', 'The command could not be confirmed. Check the Max Node controller, loaded bank and local connection.')); }
    finally { busyRef.current = false; if (mounted.current) setBusy(false); }
  }
  return <section className="max-comparison" id="max-comparison" aria-label={l('Maxで方式を聴き比べる', 'Compare methods in Max')}>
    <header><span className="pla-eyebrow">MAX / SAME INPUT</span><h4>{l('Maxで方式を聴き比べる', 'Compare methods in Max')}</h4>
      <p>{l('計算済みの同じ音を、再生位置を保って切り替えます。方式ごとの音量補正はせず、共通ゲインと共通の12chデコーダを使います。', 'Switch computed versions of the same audio while keeping the playback position. All methods use one shared gain and one 12-channel decoder; there is no per-method normalization.')}</p></header>
    <div className="max-flow" aria-label={l('音声の経路', 'Audio path')}>
      {[l('同じ入力', 'Same input'), l('方式を選択', 'Select method'), 'FOA · N3D', l('共通デコーダ', 'Shared decoder'), 'S1–S12'].map((text, i) => <span key={i}>{i > 0 && <b aria-hidden="true">→</b>}{text}</span>)}
    </div>
    {!data ? <output>{failed ? l('比較バンクを読み込めません。', 'The comparison banks could not be loaded.') : l('比較バンクを読み込んでいます。', 'Loading comparison banks.')}
      {failed && <button type="button" onClick={() => setRetry(v => v + 1)}><RefreshCw size={13}/>{l('再読込', 'Retry')}</button>}</output> : <>
      <div className="max-options"><label htmlFor={`${id}-bank`}>{l('比較する音声', 'Audio bank')}<select id={`${id}-bank`} disabled={busy} value={bank?.id} onChange={e => { setBankId(e.target.value); setMessage(''); }}>
        {data.banks.map(b => <option key={b.id} value={b.id}>{jp ? b.title_jp : b.title_en}</option>)}</select></label>
        <label htmlFor={`${id}-method`}>{l('Maxで聴く方式', 'Method to hear in Max')}<select id={`${id}-method`} disabled={busy} value={selected?.id ?? ''} onChange={e => { onSelect(e.target.value); setMessage(''); }}>
          {data.methods.map(m => <option key={m.id} value={m.id}>{label(m)}</option>)}</select></label></div>
      {bank && <p>{bank.scenes} {l('場面', 'scenes')} · {bank.duration_seconds.toFixed(3)} s · {bank.sample_rate_hz / 1000} kHz · FOA 4ch · ACN/N3D (W, Y, Z, X)<br/>
        {bank.scenes > 1 ? l('各0.248秒の短片を無音の間隔で並べた比較用音声です。連続した長い発話ではありません。グラフの試聴例は引き続き場面0000です。', 'A montage of 0.248-second excerpts separated by silence, not a continuous utterance. The plotted audition example above remains scene 0000.') : l('0.248秒の短い比較例です。繰り返して音色や方向の差を確かめます。', 'A short 0.248-second example. Loop it to compare timbre and direction.')}</p>}
      <div className="max-actions">{bank && <a className="max-download" href={asset(bank.archive_url)} download><Download size={15}/>{l('Maxパッチ＋全方式の音声を保存', 'Download Max patch + all methods')}</a>}
        <a href={asset('info/README_COMPARISON.md')} target="_blank" rel="noreferrer">{l('Maxの使い方', 'Max instructions')}</a></div>
      <ol><li>{l('ZIPを展開し、maxフォルダのADEPS_Method_Comparison.maxpatを開く。「Controllerを開始」→「同梱バンク」の順に押す。', 'Extract the ZIP and open max/ADEPS_Method_Comparison.maxpat. Click Start controller, then Load bundled bank.')}</li>
        <li>{l('Maxで出力機器とS1–S12の対応を確認。再生を開始し、共通音量を0から手動で上げる。', 'In Max, check the audio device and S1–S12 routing. Start playback and manually raise the shared volume from zero.')}</li>
        <li>{l('Max内の方式メニューで切り替える。ローカル版では、このページから方式の選択も送れる。', 'Switch methods using the Max menu. In local mode, this page can also send the selection.')}</li></ol>
      <div className="max-connection"><span>{!isLocalEngine ? l('公開Web版 · Maxのメニューで選択', 'Public web version · select in Max')
        : !connection?.max_reply ? l('Maxの応答なし', 'No Max reply') : !connection.ready ? l('Maxに接続 · バンク未準備', 'Connected · bank not ready')
          : !matching ? l('Maxに接続 · 選択中と別のバンク', 'Connected · a different bank is loaded') : l('Maxに接続 · バンク一致', 'Connected · matching bank')}</span>
        {isLocalEngine && <div className="max-actions"><button type="button" disabled={busy || !active} onClick={() => { void command('ping'); }}>{l('接続を確認', 'Check connection')}</button>
          <button type="button" disabled={busy || !active || !matching || !selected} onClick={() => { void command('select'); }}>{l('この方式をMaxへ送る', 'Send method to Max')}</button>
          <button type="button" disabled={busy || !active} onClick={() => { void command('mute'); }}>{l('ミュート要求', 'Request mute')}</button></div>}
        {connection?.max_reply && connection.selected_method && <p>{l('Max側の選択', 'Selected in Max')}: {data.methods.find(m => m.id === connection.selected_method) ? label(data.methods.find(m => m.id === connection.selected_method)!) : connection.selected_method}</p>}
        {message && <output>{message}</output>}
        <p>{isLocalEngine ? l('応答は制御の受付を示します。実音の出力確認ではありません。再生開始と音量はMaxで操作します。', 'A reply confirms control acceptance, not audible output. Start playback and set the volume in Max.')
          : l('公開ページはMaxへ直接接続しません。ZIPだけでもMax側で全方式を選べます。Webから操作する場合は、ソース一式のADEPS-test.commandでローカル版を開きます。', 'The public page does not connect directly to Max. The ZIP lets you select every method inside Max. To control it from the web UI, run ADEPS-test.command from the source checkout.')}</p></div>
      <p className="pla-note">{l('「ADEPS」は本プロジェクトの独自実装です。任意のライブ入力の推論、室内補正、実機への自動チャンネル割当は行いません。S1–S12と実出力は現地で照合してください。', '“ADEPS” denotes this project’s independent implementation. This does not infer arbitrary live input, correct the room or assign hardware channels automatically. Verify S1–S12 against the actual outputs on site.')}</p>
    </>}
  </section>;
}
