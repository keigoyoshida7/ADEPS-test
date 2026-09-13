import { useEffect, useId, useState } from 'react';
import { Download, ExternalLink } from 'lucide-react';
import { asset } from './assets';
import { fmt, Plot } from './Plots';
import type { PlusBenchmark } from './ADEPSPlus';
import { paperMetricKeys, validPaperComparison, validPaperReference } from './paperComparisonData';
import type { PaperComparison as ComparisonData, PaperCurves, PaperMetricKey, PaperProfile, PaperReference, PaperScores } from './paperComparisonData';
import './PaperComparison.css';

type Load = { state: 'loading' | 'unavailable' | 'invalid' } | { state: 'ready'; data: ComparisonData; paper: PaperReference };
const metricInfo: Record<PaperMetricKey, { short: string; jp: string; en: string; up: boolean; unit: string; digits: number }> = {
  si_sdr_db: { short: 'SI-SDR', jp: '波形の復元', en: 'Waveform reconstruction', up: true, unit: 'dB', digits: 2 },
  spectral_error_db: { short: 'Spectrum error', jp: '振幅スペクトル誤差', en: 'Magnitude spectrum error', up: false, unit: 'dB', digits: 2 },
  coherence: { short: 'Coherence', jp: '係数のコヒーレンス', en: 'Coefficient coherence', up: true, unit: '', digits: 3 },
  ild_error_db: { short: 'ILD error', jp: '左右のレベル差の誤差', en: 'Interaural level-difference error', up: false, unit: 'dB', digits: 2 },
  ic_error: { short: 'IC error', jp: '左右の相関の誤差', en: 'Interaural-coherence error', up: false, unit: '', digits: 3 },
};
const arrayName = (id: string) => ({ mics4: '4 mics', mics5: '5 mics', mics6: '6 mics', aria: 'Project Aria' }[id] ?? id);
const lines = [{ color: '#fff' }, { color: '#bbb', dash: '9 5' }, { color: '#ddd', dash: '2 4' }, { color: '#888', dash: '10 3 2 3' }, { color: '#ddd', dash: '12 6' }, { color: '#aaa', dash: '5 5' }, { color: '#eee', dash: '1 3' }, { color: '#bbb', dash: '8 3 1 3' }, { color: '#888', dash: '3 6' }];

export default function PaperComparison({ language, active, original, sourceSha256 }: { language: 'jp' | 'en'; active: boolean; original: PlusBenchmark; sourceSha256: string }) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [load, setLoad] = useState<Load>({ state: 'loading' });
  const [profile, setProfile] = useState<PaperProfile>('strict');
  const [tableNumber, setTableNumber] = useState(1);
  const [arrayId, setArrayId] = useState('mics6');
  const [sceneId, setSceneId] = useState('all');
  const [baseline, setBaseline] = useState('linear_tuned');
  const [selectedMethod, setSelectedMethod] = useState('plus');
  const [visible, setVisible] = useState(['linear_tuned', 'adeps_current', 'plus', 'plus_no_denoiser']);
  const selectId = useId();
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void Promise.all(['models/paper-comparison.json', 'models/paper-reference-v3.json'].map(async path => {
      const response = await fetch(asset(path), { signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error('unavailable');
      return response.text();
    })).then(async ([reportText, paperText]) => {
      const data: unknown = JSON.parse(reportText), paper: unknown = JSON.parse(paperText);
      if (!validPaperComparison(data, original, sourceSha256) || !validPaperReference(paper)) {
        if (!controller.signal.aborted) setLoad({ state: 'invalid' });
        return;
      }
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(paperText))))
        .map(v => v.toString(16).padStart(2, '0')).join('');
      if (!controller.signal.aborted) setLoad(digest === data.provenance.reference_sha256 ? { state: 'ready', data, paper } : { state: 'invalid' });
    }).catch(() => { if (!controller.signal.aborted) setLoad({ state: 'unavailable' }); });
    return () => controller.abort();
  }, [active, original, sourceSha256]);

  const heading = <header className="ap-section-heading"><span className="eyebrow">PAPER METRICS / POST-HOC EVALUATION</span><h3>{l('原論文と、同じ指標で見る。', 'Read the results through the paper’s metrics.')}</h3></header>;
  if (load.state !== 'ready') return <section id="paper-metrics" className="ap-section paper-comparison">{heading}<p aria-live="polite">{load.state === 'loading' ? l('指標と引用値を照合しています。', 'Checking metric records and quoted results.') : load.state === 'invalid' ? l('元の評価記録・集計・引用データの整合性を確認できませんでした。', 'The source results, aggregation or reference data could not be verified.') : l('指標の比較記録を読み込めませんでした。ページを再読み込みしてください。', 'Could not load the metric comparison. Please reload the page.')}</p></section>;
  const { data, paper } = load;
  const table = paper.tables.find(t => t.number === tableNumber)!;
  const array = table.array_ids.includes(arrayId) ? arrayId : table.array_ids[0];
  const aggregate = data.profiles[profile];
  const scene = data.scenes.find(s => s.id === sceneId);
  const scores = (id: string): PaperScores => scene ? scene.profiles[profile][id].metrics : aggregate.means[id];
  const curves = (id: string): PaperCurves => scene ? scene.profiles[profile][id].curves : aggregate.curves[id];
  const name = (id: string) => { const m = data.methods.find(v => v.id === id)!; return l(m.label_jp, m.label_en); };
  const scope = scene ? scene.id : l(`全${data.scenes.length}場面の平均`, `Mean of all ${data.scenes.length} scenes`);
  const columnHeadings = (proxy: boolean) => <tr><th scope="col">{l('方式', 'Method')}</th>{paperMetricKeys.map(k => <th key={k} scope="col">{metricInfo[k].short}{proxy && (k === 'ild_error_db' || k === 'ic_error') ? ' †' : ''}<br/>{metricInfo[k].unit} {metricInfo[k].up ? '↑' : '↓'}</th>)}</tr>;
  const cells = (values: PaperScores, originalRow = false) => paperMetricKeys.map(k => <td key={k} title={values[k] === null ? l('必要な値に未定義があるため平均しません。詳細は下の指標定義を参照。', 'A required value is undefined; it is not omitted from the mean. See the metric definitions.') : undefined}>{fmt(values[k], originalRow ? 2 : metricInfo[k].digits)}</td>);
  const chart = (key: keyof PaperCurves) => {
    const series = data.methods.filter(m => visible.includes(m.id)).map((m, i) => ({ name: name(m.id), values: curves(m.id)[key], ...lines[i % lines.length] }));
    const peak = Math.max(0.001, ...series.flatMap(s => s.values.flatMap(v => v === null ? [] : [v])));
    return <Plot x={key === 'ild_error_db' || key === 'ic_error' ? data.binaural_frequencies_hz : data.frequencies_hz}
      series={series} label={l(metricInfo[key].jp, metricInfo[key].en)} unit={metricInfo[key].unit || (key === 'coherence' ? 'MSC' : 'IC error')}
      frequency yDomain={key === 'coherence' ? [0, 1] : [0, peak * 1.12]}/>;
  };
  return <section id="paper-metrics" className="ap-section paper-comparison">{heading}
    <p>{l('論文の5指標を並べ、保存済みの32場面・9方式を追加評価しました。復元音・学習済み重み・事前の評価結果は変更していません。', 'The paper’s five metrics are shown together, with additional scoring of the saved 32 scenes and nine methods. Reconstructions, trained weights and the prospective benchmark are unchanged.')}</p>
    <div className="pc-mismatch"><strong>{l('指標を揃えることと、同じ試験で比べることは別です。', 'Matching metrics does not make these the same benchmark.')}</strong><p>{l('原論文はWSJ0・1,000場面・13アレイ。本実装は別話者のVCTK・32場面・球面6本の1配置です。数値を並べても、原論文への勝敗や改善率は算出しません。', 'The paper evaluates WSJ0, 1,000 scenes and 13 arrays. Our test uses held-out VCTK, 32 scenes and one six-microphone spherical geometry. The numbers are shown as context, without a cross-benchmark victory or improvement percentage.')}</p></div>

    <div className="ap-controls pc-controls">
      <label htmlFor={`${selectId}-table`}>{l('原論文の条件', 'Paper condition')}</label>
      <select id={`${selectId}-table`} value={tableNumber} onChange={e => setTableNumber(Number(e.target.value))}>
        <option value={1}>{l('Table 1 · 次数一致 N=5', 'Table 1 · Order matched N=5')}</option>
        <option value={2}>{l('Table 2 · 次数不一致 N=15→5', 'Table 2 · Order mismatch N=15→5')}</option>
        <option value={3}>{l('Table 3 · 配置専用モデルとの比較', 'Table 3 · Array-specific models')}</option>
      </select>
      <label htmlFor={`${selectId}-array`}>{l('マイク配置', 'Array')}</label><select id={`${selectId}-array`} value={array} onChange={e => setArrayId(e.target.value)}>{table.array_ids.map(id => <option key={id} value={id}>{arrayName(id)}</option>)}</select>
    </div>
    <div className="ap-table-wrap pc-original"><table><caption>{l('原論文の掲載値（参考）', 'Published paper values (reference)')} · Table {table.number} / {arrayName(array)} / N_eff={table.N_eff}, N_p={table.N_p}, N_enc={table.N_enc}</caption><thead>{columnHeadings(false)}</thead><tbody>{table.rows.map(r => <tr key={r.method_id}><th scope="row">{r.label}</th>{cells(r.values[array], true)}</tr>)}</tbody></table></div>
    <p className="ap-note">{l('出典：Milstein・Shlezinger・Rafaely, arXiv:2608.24558v3, Tables 1–3。Param.には正解の音源方向と機器応答を渡しています。', 'Source: Milstein, Shlezinger & Rafaely, arXiv:2608.24558v3, Tables 1–3. Param. receives oracle source directions and device responses.')} <a href={table.source_url} target="_blank" rel="noreferrer">{l('引用元を開く', 'Open cited table')}<ExternalLink size={12}/></a></p>
    {tableNumber !== 1 && <p className="pc-condition-warning">{l('以下の独自結果は次数5一致のままです。原論文側の選択を変えても、こちらが次数15や4本配置の評価に切り替わるわけではありません。', 'Our results below remain order-5 matched. Changing the paper selector does not turn our test into an order-15 or four-microphone evaluation.')}</p>}

    <div className="ap-controls pc-controls">
      <label htmlFor={`${selectId}-profile`}>{l('ゼロ付近の扱い', 'Near-zero convention')}</label><select id={`${selectId}-profile`} value={profile} onChange={e => setProfile(e.target.value as PaperProfile)}>
        <option value="strict">{l('論文の式 · 未定義は —', 'Literal equations · undefined = —')}</option><option value="reference_floor">{l('補助評価 · −120 dBで安定化', 'Sensitivity · −120 dB stabilization')}</option>
      </select>
      <label htmlFor={`${selectId}-scene`}>{l('独自試験の場面', 'Our test scene')}</label><select id={`${selectId}-scene`} value={sceneId} onChange={e => setSceneId(e.target.value)}><option value="all">{l('全32場面の平均', 'Mean of all 32 scenes')}</option>{data.scenes.map(s => <option value={s.id} key={s.id}>{s.id} / {s.cluster_id}</option>)}</select>
    </div>
    <p className="ap-note">{profile === 'strict' ? l('Gen-Aの式を4chすべてに適用します。ゼロ出力や0/0で値が定義できない場合は — とし、その場面を平均から除外しません。', 'Apply the Gen-A equations to all four channels. Undefined ratios or zero-output terms are shown as —; no affected scene is dropped from the average.') : l('原論文には指定されていない補助条件です。全方式共通の参照振幅floorを−120 dBに固定し、非ゼロ参照に対するゼロ出力のMSCを0として扱います。', 'This sensitivity convention is not specified by the paper: a common reference-based −120 dB amplitude floor and MSC=0 for zero output against a nonzero reference.')} {l('SI-SDRと左右の耳の評価は、この切り替えでは変わりません。', 'This switch does not change SI-SDR or the binaural metrics.')}</p>
    <div className="ap-table-wrap"><table><caption>{l('本実装の追加評価', 'Additional evaluation of our implementation')} · {scope} · {profile === 'strict' ? l('論文の式', 'Literal equations') : l('安定化した補助評価', 'Stabilized sensitivity')}</caption><thead>{columnHeadings(true)}</thead><tbody>{data.methods.map(m => <tr key={m.id} data-plus={m.id === 'plus'}><th scope="row">{name(m.id)}</th>{cells(scores(m.id))}</tr>)}</tbody></table></div>
    <p className="ap-note">† {l('ILD / ICはSADIE IIの実測KU100 HRTFを使う独自のERB帯域評価です。原論文と同一のHRTFセット・デコーダ・聴覚モデルは確認できていないため、厳密再現ではありません。既存のcardioid試聴音から計算した値ではありません。', 'ILD / IC use independent ERB-band scoring with measured SADIE II KU100 HRTFs. The original HRTF set, decoder and auditory model are not fully specified, so this is not an exact reproduction. These scores are not calculated from the existing cardioid audio previews.')}</p>

    <details className="ap-details"><summary>{l('同じ入力での改善・悪化を、5指標で比較', 'Compare gains and regressions on identical inputs')}</summary>
      <div className="ap-controls pc-controls"><label htmlFor={`${selectId}-method`}>{l('評価する方式', 'Method')}</label><select id={`${selectId}-method`} value={selectedMethod} onChange={e => setSelectedMethod(e.target.value)}>{data.methods.map(m => <option value={m.id} key={m.id}>{name(m.id)}</option>)}</select><label htmlFor={`${selectId}-baseline`}>{l('比較基準', 'Baseline')}</label><select id={`${selectId}-baseline`} value={baseline} onChange={e => setBaseline(e.target.value)}>{data.methods.map(m => <option value={m.id} key={m.id}>{name(m.id)}</option>)}</select></div>
      <div className="pc-deltas">{paperMetricKeys.map(k => {
        const a = scores(selectedMethod)[k], b = scores(baseline)[k];
        const delta = a === null || b === null ? null : (metricInfo[k].up ? a - b : b - a);
        const pair = data.scenes.map(s => [s.profiles[profile][selectedMethod].metrics[k], s.profiles[profile][baseline].metrics[k]]);
        const complete = pair.filter(([x, y]) => x !== null && y !== null);
        const wins = complete.filter(([x, y]) => metricInfo[k].up ? x! > y! : x! < y!).length;
        return <div key={k}><span>{metricInfo[k].short}</span><strong>{delta !== null && delta > 0 ? '+' : ''}{fmt(delta, metricInfo[k].digits)} <small>{metricInfo[k].unit}</small></strong><p>{l('正の値ほど改善', 'Positive means improvement')}{!scene && <><br/>{l(`改善 ${wins} / 比較可能 ${complete.length} 場面`, `Improved ${wins} / ${complete.length} comparable scenes`)}{complete.length < data.scenes.length && <><br/>{l(`未定義 ${data.scenes.length - complete.length} 場面`, `${data.scenes.length - complete.length} undefined scenes`)}</>}</>}</p></div>;
      })}</div><p className="ap-note">{l('この差は同じ独自試験内だけの比較です。追加指標による事後の記述で、事前の主比較の合否を変更しません。', 'These differences compare only methods within our own test. This post-hoc description does not change the prospective primary verdict.')}</p>
    </details>

    <details className="ap-details" open><summary>{l('論文と同じ2種類の周波数図で見る', 'Inspect the two frequency plots used in the paper')}</summary>
      <fieldset className="ap-scope-picker pc-methods"><legend>{l('曲線を表示する方式', 'Visible methods')}</legend>{data.methods.map(m => <label key={m.id}><input type="checkbox" checked={visible.includes(m.id)} onChange={e => setVisible(v => e.target.checked ? [...v, m.id] : v.filter(id => id !== m.id))}/>{name(m.id)}</label>)}</fieldset>
      <div className="ap-charts pc-plots"><div><h4>{l('振幅スペクトル誤差', 'Magnitude spectrum error')} <small>{l('低いほど良好', 'Lower is better')}</small></h4>{chart('spectral_error_db')}</div><div><h4>{l('コヒーレンス', 'Coherence')} <small>{l('1に近いほど良好', 'Closer to 1 is better')}</small></h4>{chart('coherence')}</div></div>
      <p className="ap-note">{scope} · {l('表示軸 1 Hz–20 kHz／実データ 31.25 Hz–8 kHz。平均にはDCも含みます。原著Fig. 1の数値曲線は未公開のため、図から推測した線は重ねていません。', 'Axis: 1 Hz–20 kHz; actual non-DC data: 31.25 Hz–8 kHz. Means also include DC. Fig. 1 numerical curves are not published; no guessed traces are overlaid.')} <a href={`${paper.source.html_url}#S4.F1`} target="_blank" rel="noreferrer">{l('原著Fig. 1', 'Original Fig. 1')}</a></p>
      <details className="ap-details"><summary>{l('左右の耳の誤差をERB帯域ごとに見る（独自代理評価）', 'Binaural errors by ERB band (independent proxy)')}</summary><div className="ap-charts pc-plots"><div><h4>ILD error · dB</h4>{chart('ild_error_db')}</div><div><h4>IC error</h4>{chart('ic_error')}</div></div><p className="ap-note">{l('計算に含む周波数は125–8,000 Hz。耳の向きは正面に固定。ERBは耳の周波数分解能を近似する帯域で、グラフの点は各帯域の中心です。ICは係数のMSCと異なり、左右信号の時間差を含む相関から求めます。', 'Included FFT bins span 125–8,000 Hz. Head orientation is fixed forward. ERB approximates auditory frequency resolution; points mark band centers. IC uses cross-correlation between ears including time lags, unlike coefficient MSC.')}</p></details>
    </details>

    <details className="ap-details pc-definitions"><summary>{l('計算式・揃えられた条件・残る違い', 'Definitions, aligned conditions and remaining differences')}</summary>
      <dl><dt>SI-SDR ↑</dt><dd>{l('参照波形に最も合う1つの倍率を求め、残った誤差と比較。Le Roux et al. の射影式を使用。本実装の平均除去・両端256サンプル除外・参照が非ゼロのchのdB平均は独自の運用条件です（今回の全場面では4ch）。', 'Project onto the reference waveform using one optimal scale (Le Roux et al.). Our mean removal, 256-sample edge crop and reference-active channel dB average are local conventions (all four channels in these scenes).')}</dd>
      <dt>Magnitude spectrum error ↓</dt><dd><code>mean_c,t |20 log10(|a| / |â|)|</code><br/>{l('Gen-A Eq. (5)。周波数ごとに4ch×全フレームを等しく平均し、さらに全周波数・全場面を等平均します。', 'Gen-A Eq. (5). Equal mean over all four channels and frames at each frequency, then equal means over frequencies and scenes.')}</dd>
      <dt>Coherence ↑</dt><dd><code>mean_c |Σt a·conj(â)|² / (Σt |a|² · Σt |â|²)</code><br/>{l('Gen-A Eq. (6)。振幅だけでなく位相の一貫性も含みます。ゼロ参照chは両設定で未定義のままです。', 'Gen-A Eq. (6), including phase consistency. A zero-reference channel remains undefined in both profiles.')}</dd>
      <dt>ILD error ↓ / IC error ↓</dt><dd>{l('FOA参照と各復元を同じKU100デコーダで両耳化し、ERB帯域の手掛かりの絶対差を平均します。ILDは左右のパワー比のdB値。ICは±1 msの遅れの中で最大となる正規化相関です。原著の詳細が不明なため、聴覚末梢モデルを含む厳密な再現ではありません。', 'Render the reference FOA and every estimate through the same KU100 decoder and average absolute ERB-band cue differences. ILD is the ear-power ratio in dB; IC is peak normalized correlation within ±1 ms. This is not an exact reproduction of an unspecified original auditory front end.')}</dd></dl>
      <div className="ap-table-wrap"><table><caption>{l('同じ指標でも変わる評価条件', 'Evaluation conditions that still differ')}</caption><thead><tr><th>{l('項目', 'Condition')}</th><th>{l('原論文', 'Original paper')}</th><th>{l('本実装', 'This evaluation')}</th></tr></thead><tbody>
        <tr><th>{l('評価する係数', 'Scored coefficients')}</th><td>N_enc = 1 / 4ch</td><td>N_enc = 1 / 4ch</td></tr>
        <tr><th>{l('事前分布の次数', 'Prior order')}</th><td>N_p = 5</td><td>N_p = 5</td></tr>
        <tr><th>{l('観測ノイズ', 'Observation noise')}</th><td>Gaussian / 50 dB SNR</td><td>Gaussian / 50 dB SNR</td></tr>
        <tr><th>{l('テスト音声', 'Test speech')}</th><td>WSJ0</td><td>VCTK / {l('別話者', 'held-out speakers')}</td></tr>
        <tr><th>{l('場面・アレイ数', 'Scenes / arrays')}</th><td>1,000 / 13</td><td>32 / 1</td></tr>
        <tr><th>{l('評価区間', 'Evaluation segment')}</th><td>{l('詳細未記載', 'Not fully specified')}</td><td>32 STFT frames / SI-SDR 0.248 s</td></tr>
        <tr><th>{l('HRTF・聴覚処理', 'HRTF / auditory processing')}</th><td>KU100 / {l('詳細未記載', 'details unspecified')}</td><td>SADIE II KU100 / {l('独自ERB代理評価', 'independent ERB proxy')}</td></tr>
        <tr><th>{l('ゼロ処理・平均', 'Zero handling / averaging')}</th><td>{l('詳細未記載', 'Not fully specified')}</td><td>{l('本画面の2条件を明示', 'Two explicit conventions')}</td></tr>
      </tbody></table></div>
      <p>{l('NRMSEは従来の独自試験の主指標です。原論文のTable 1–3にないため、この5列へ混ぜていません。十分な長さのWSJ0、原著アレイ応答、著者と同じ評価コード・HRTF条件が揃うまでは、原著より高精度とは判定できません。', 'NRMSE remains the primary metric of our prospective test. It is not in Tables 1–3 and is kept outside these five columns. A claim of surpassing the paper requires matching WSJ0 segments, array responses, author evaluation code and HRTF conditions.')}</p>
      <a href={asset('info/PAPER_COMPARISON.md')}>{l('計算仕様・HRTFの出所・再評価手順', 'Metric specification, HRTF provenance and re-scoring steps')}</a>
    </details>
    <div className="ap-links"><a href={asset('models/paper-comparison.csv')} download><Download size={14}/>{l('全場面・5指標 CSV', 'All scenes / five metrics CSV')}</a><a href={asset('models/paper-comparison.json')} download><Download size={14}/>{l('再評価の記録 JSON', 'Re-scoring record JSON')}</a><a href={asset('models/paper-reference-v3.json')} download>{l('原論文の引用値・出典', 'Paper values and provenance')}</a><a href={paper.source.html_url} target="_blank" rel="noreferrer">{l('原論文 v3', 'Original paper v3')}<ExternalLink size={14}/></a></div>
  </section>;
}
