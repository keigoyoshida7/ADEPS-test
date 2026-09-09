'use client';
import { useT } from './i18n';
import { asset } from './assets';
import { useState, type ReactNode } from 'react';
import { ArrowRight, Copy, Download, ExternalLink } from 'lucide-react';
const PAPER = 'https://arxiv.org/html/2608.24558v2';
const REPO =
  'https://github.com/Amitmils/ADEUPS/tree/5076f163a1f939c297b55a39b2d9d33e2b224a5f';
const citation =
  'Amit Milstein, Nir Shlezinger, and Boaz Rafaely. “Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling.” arXiv:2608.24558v2, 27 August 2026. https://doi.org/10.48550/arXiv.2608.24558';
const application =
  '本デモはMilstein, Shlezinger, and Rafaely（2026, arXiv:2608.24558v2）が示す、信号表現と物理取得モデルを分ける考え方を参照した。マイクからFOAへの経路には同論文の式(5)に示される線形符号化を独自実装し、チャンネル規約と正則化の設定を明示した。スピーカー再生側には別途、正則化した線形音圧マッチングによる合成実験を実装した。さらに式(10)・式(11)・Algorithm 1に基づく拡散推論を独自実装し、合成空間係数で学習した小型MLPを接続した。著者のネットワーク・学習データ・重み、および論文の公表性能や実際の音響システムでの性能は再現・検証していない。';
function Cite({ at, children }: { at: string; children: ReactNode }) {
  return (
    <a
      className="citation"
      href={`${PAPER}#${at}`}
      target="_blank"
      rel="noreferrer"
    >
      [1 · {children}]
    </a>
  );
}
function Section({
  id,
  n,
  title,
  children,
}: {
  id: string;
  n: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="panel info-section">
      <div className="info-section-title">
        <span>{n}</span>
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}
export default function ResearchInfo({
  onNavigate,
}: {
  onNavigate: (page: string) => void;
}) {
  const t = useT();

  const [message, setMessage] = useState('');
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setMessage('コピーしました。');
    } catch {
      setMessage(
        'コピーできませんでした。引用文を選択してコピーするか、BibTeXを保存してください。',
      );
    }
  }
  return (
    <article className="research-info">
      <div className="context-line">
        <span className="badge">{t('研究・実装ノート')}</span>
        <p>{t('参照版：arXiv v2 · 原典と実装の照合：2026.09.10')}</p>
      </div>
      <div className="info-intro">
        <h2>{t('何を参照し、何を実装したか。')}</h2>
        <p>
          {t(
            'ADEPS-testは、空間音響の線形推定と、独自の小型priorを使う拡散推論を調べる研究デモです。',
          )}{' '}
          {t('このページでは、参照論文の数式と本デモの処理の対応を示します。')}{' '}
          {t(
            'マイクからFOAへの経路では式(5)と同じ形式の線形符号化を実装し、再生側では別の正則化した音圧マッチングを検証します。',
          )}{' '}
          {t(
            '圧縮・観測整合性・denoiserを通る勾配・反復更新を独自実装しました。著者のNCSN++Mと学習済み重みは未公開で、論文の性能を再現したとは扱いません。',
          )}
        </p>
      </div>
      <div className="info-status-grid">
        <div>
          <span>{t('01 / 数式を実装')}</span>
          <h3>{t('マイク → FOA')}</h3>
          <p>
            {t(
              '式(5)と同じ形式の線形encoder。データ・規約・正則化は本試作で明示。',
            )}
          </p>
          <button onClick={() => onNavigate('capture')}>
            {t('線形ベースラインへ')}
            <ArrowRight size={14} />
          </button>
        </div>
        <div>
          <span>{t('02 / 考え方を応用')}</span>
          <h3>{t('スピーカー再生の検証')}</h3>
          <p>
            {t(
              '物理応答を独立させ、従来の線形補正を合成データで評価する独自の応用。',
            )}
          </p>
          <button onClick={() => onNavigate('playback')}>
            {t('再生系の実験へ')}
            <ArrowRight size={14} />
          </button>
        </div>
        <div>
          <span>{t('03 / 独自モデルで実行')}</span>
          <h3>{t('ADEPSの拡散推論')}</h3>
          <p>
            {t(
              '合成空間係数で学習した小型MLPと拡散推論式を接続。線形との比較、反復履歴、FOA WAVを書き出します。',
            )}
          </p>
          <button onClick={() => onNavigate('neural')}>
            {t('ニューラル推論へ')}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
      <div className="info-toc" aria-label={t('研究ノートの目次')}>
        {[
          ['citation', t('引用情報')],
          ['mapping', t('論文と実装の対応')],
          ['capture', t('マイク側の数式')],
          ['playback', t('再生系への応用')],
          ['evaluation', t('結果の読み方')],
          ['geometry', t('配置・測定・外部制御')],
          ['status', t('未実装と次の段階')],
          ['references', t('参考文献')],
        ].map(([id, label], i) => (
          <a key={id} href={`#info-${id}`}>
            <span>{String(i + 1).padStart(2, '0')}</span>
            {label}
          </a>
        ))}
      </div>
      <Section id="info-citation" n="01" title={t('参照論文と引用の書き方')}>
        <p className="bibliographic-title">
          Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling
        </p>
        <p>
          Amit Milstein / Nir Shlezinger / Boaz Rafaely
          <br />
          {t('arXiv:2608.24558v2 · 改訂 2026年8月27日（初稿 8月25日）')}
        </p>
        <div className="source-links">
          <a
            href="https://arxiv.org/abs/2608.24558v2"
            target="_blank"
            rel="noreferrer"
          >
            {t('書誌・バージョン')}
            <ExternalLink size={13} />
          </a>
          <a
            href="https://arxiv.org/pdf/2608.24558v2"
            target="_blank"
            rel="noreferrer"
          >
            {t('原論文PDF')}
          </a>
          <a
            href="https://doi.org/10.48550/arXiv.2608.24558"
            target="_blank"
            rel="noreferrer"
          >
            DOI
          </a>
        </div>
        <p>
          {t(
            '論文はマイクアレイからのAmbisonics符号化を扱います。アレイが変わっても学習済みpriorを使えますが、推論時の物理モデルVは必要です。',
          )}
          <Cite at="S1">§1</Cite>
          {t(
            '本ページの日本語は要約と本試作の解説です。著者の文章をそのまま翻訳・転載した引用文ではありません。',
          )}
        </p>
        <div className="info-copy">
          <h3>{t('資料に使える引用表記')}</h3>
          <p>{citation}</p>
          <button onClick={() => copy(citation)}>
            <Copy size={14} />
            {t('引用表記をコピー')}
          </button>
          <a
            className="button-link"
            href={asset('/info/references.bib')}
            download
          >
            <Download size={14} />
            BibTeX
          </a>
        </div>
        <div className="info-copy">
          <h3>{t('この試作の応用範囲を説明する文章')}</h3>
          <p>{t(application)}</p>
          <button onClick={() => copy(t(application))}>
            <Copy size={14} />
            {t('説明文をコピー')}
          </button>
        </div>
        <p className="muted" role="status" aria-live="polite">
          {t(message)}
        </p>
      </Section>
      <Section id="info-mapping" n="02" title={t('論文の箇所と、実装の対応')}>
        <div className="table-scroll">
          <table className="info-map">
            <thead>
              <tr>
                <th>{t('原典の箇所')}</th>
                <th>{t('この試作での扱い')}</th>
                <th>{t('実装・確認する画面')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <Cite at="S2.E2">{t('§2.1・式(2)')}</Cite>
                  <br />p = V a + ν
                </td>
                <td>
                  <b>{t('モデルを明示する考え方を参照。')}</b>
                  {t(
                    'Vとマイク観測を別々に入力できる構造にした。座標だけで実際のデバイス応答が分かるとは仮定しない。',
                  )}
                </td>
                <td>
                  backend/capture.py
                  <br />
                  modal_matrix / run_capture
                  <br />
                  {t('「マイク → Ambisonics」')}
                </td>
              </tr>
              <tr>
                <td>
                  <Cite at="S2.E5">{t('§2.3・式(5)')}</Cite>
                  <br />
                  {t('線形encoder')}
                </td>
                <td>
                  <b>{t('同じ行列形式を独自実装。')}</b>
                  {t(
                    '論文中でも既存の線形ベースラインとして示される式。ADEPSのニューラル手法全体を実装したという意味ではない。',
                  )}
                </td>
                <td>
                  backend/capture.py / encode
                  <br />
                  {t('正則化、rank、参照との誤差')}
                </td>
              </tr>
              <tr>
                <td>
                  <Cite at="S3.E10">{t('§3.1・式(10)')}</Cite>
                  <br />
                  <Cite at="algorithm1">Algorithm 1</Cite>
                </td>
                <td>
                  <b>{t('式を独自実装。')}</b>
                  {t(
                    '圧縮領域の観測整合性を計算し、denoiserを含む全経路を微分。勾配を有限差分で検証しました。マイク領域の残差とは別に表示します。',
                  )}
                </td>
                <td>
                  {t('backend/neural.py / consistency, sample')}
                  <br />
                  {t('独自学習MLP・150回のEuler更新')}
                </td>
              </tr>
              <tr>
                <td>
                  <Cite at="S3.SS4">§3.4</Cite>
                  <br />
                  {t('物理モデルとpriorの分離')}
                </td>
                <td>
                  <b>{t('再生側に応用した設計上の着想。')}</b>
                  {t(
                    '会場応答Hと補正Gを分けて評価する。ただしマイク取得Vとは別の演算子であり、同じアルゴリズムではない。',
                  )}
                </td>
                <td>
                  backend/numerics.py
                  <br />
                  synthetic_transfer / regularized_mimo
                </td>
              </tr>
              <tr>
                <td>
                  <Cite at="S3.T2">Table 2</Cite>
                  <br />
                  <Cite at="S4.F1">Figure 1</Cite>
                </td>
                <td>
                  <b>{t('評価方針の参考。')}</b>
                  {t(
                    '単一スコアで成功を決めず、周波数・参照の有無・rankを併記。論文と同一の評価データや集計は使用していない。',
                  )}
                </td>
                <td>
                  {t('各結果ページ・JSON')}
                  <br />
                  {t('改善と悪化、未定義値を分けて表示')}
                </td>
              </tr>
              <tr>
                <td>
                  {t('デモの仮想配置')}
                  <br />
                  {t('論文の実験とは別のデータ')}
                </td>
                <td>
                  <b>{t('配置とデータの出典を明示。')}</b>
                  {t(
                    '3D表示と計算で共通の座標を使う。サンプル配置は仮想データで、実在の施設の測量値ではない。',
                  )}
                </td>
                <td>{t('配置の確認画面')}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>
      <Section
        id="info-capture"
        n="03"
        title={t('マイク側：式(5)をどう実装したか')}
      >
        <div className="flow">
          <div>
            {t('観測 p と取得モデル V')}
            <small>{t('複素数・共通の周波数と規約')}</small>
          </div>
          <ArrowRight />
          <div className="ok">
            {t('線形encoder E')}
            <small>{t('現在実装している処理')}</small>
          </div>
          <ArrowRight />
          <div>
            {t('FOAの4成分')}
            <small>{t('参照があれば品質を比較')}</small>
          </div>
        </div>
        <div className="formula">
          E(f) = V(f)ᴴ [ V(f)V(f)ᴴ + γ²(f)I ]⁻¹
          <br />
          â(f) = E(f)p(f)
        </div>
        <p>
          {t('行列形式の参照先は')}
          <Cite at="S2.E5">{t('式(5)')}</Cite>
          {t(
            '。この試作の配列はV=[F,Q,C]、p=[F,Q,T]です。Fは周波数、Qはマイク数、Cは係数数、Tはフレーム数。論文Algorithm 1のp=[Q,F,T]とは軸順が異なるため、そのまま渡さず対応を確認します。',
          )}
        </p>
        <h3>{t('論文からコピーした設定ではない部分')}</h3>
        <div className="formula">
          {'γ²(f) = max { r · Re tr[V(f)V(f)ᴴ] / Q, 10⁻¹² }'}
        </div>
        <p>
          {t(
            '画面の「正則化」は本試作の相対値rです。Vのスケールから周波数ごとのγ²を作り、最小値を設けています。画面の値を論文のγそのものと読むことはできません。この設定は結果JSONの',
          )}
          <code>prototype_regularization</code>
          {t('と')}
          <code>gamma_squared_by_frequency</code>
          {t('に保存します。')}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('項目')}</th>
                <th>{t('現在の実装')}</th>
                <th>{t('解釈')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('合成デモの規約')}</td>
                <td>{t('real ACN / N3D、FOA順 W,Y,Z,X')}</td>
                <td>
                  {t(
                    '本試作で明記した規約。論文の未記載の規約を推定したものではない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('物理モデル')}</td>
                <td>{t('自由空間・無指向性・exp(+ikr·d)')}</td>
                <td>
                  {t(
                    '頭部・筐体・実マイク特性や部屋の残響を自動では含まない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('モデル不一致のデモ')}</td>
                <td>{t('生成3次 → 推定1次')}</td>
                <td>
                  {t(
                    '論文の実験条件と異なる、rankや不一致を観察するための独自例。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('ファイル入力')}</td>
                <td>
                  {t('V・p・任意の参照をJSONで入力。ACNとN3D/SN3Dを宣言。')}
                </td>
                <td>
                  {t(
                    '生のWAVからSTFTを作る処理はこの経路に未実装。入力の時刻・位相・規約は入力者が揃える。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('出力と診断')}</td>
                <td>
                  {t('先頭4係数をFOAとして評価。rank・特異値・条件数・残差。')}
                </td>
                <td>
                  {t(
                    'rank不足でも数値は返り得る。小さい残差だけでは正しい復元を示さない。',
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <details>
          <summary>{t('独自のニューラル推論で加えた処理')}</summary>
          <div className="formula">
            𝓗(z) = β |z|ᵅ exp(i arg z)
            <br />y = 𝓗(Ẽp),　𝓐(x) = 𝓗(Ẽ V 𝓗⁻¹(x))
          </div>
          <p>
            {t(
              '圧縮した領域でdenoiserの推定を観測に整合させる過程が必要です。',
            )}
            <Cite at="S3.E10">{t('式(10)')}</Cite>
            <Cite at="algorithm1">Algorithm 1</Cite>
            {t(
              'ニューラル推論のページでは𝓗・𝓐・独自学習MLP・拡散の反復更新を接続しています。小型モデルは論文の音声学習priorとは異なります。',
            )}
          </p>
          <p>
            {t(
              '線形ページの残差は ‖Vâ−p‖ / ‖p‖。ニューラルページは圧縮領域の y−𝓐(Dθ(x,σ)) と、denoiserを通る勾配で反復更新します。両方の残差を区別して保存します。',
            )}
            <Cite at="S2.E9">{t('式(9)')}</Cite>
            {t(
              '残差を表示するだけで後者を実行したことにはなりません。なお𝓗は圧縮関数、次節のHはスピーカー伝達行列で、別の記号です。',
            )}
          </p>
        </details>
      </Section>
      <Section
        id="info-playback"
        n="04"
        title={t('再生側：独立した音圧マッチング実験')}
      >
        <p>
          {t(
            'ここからは本試作の設計です。音源表現と会場の物理応答を別々に扱う構成を採り、スピーカーから測定位置までの応答Hに対して、補正Gを計算します。これは従来の正則化した音圧マッチングであり、ADEPSの式(10)をスピーカーにそのまま適用する処理ではありません。',
          )}
        </p>
        <div className="flow">
          <div>
            {t('入力 u')}
            <small>{t('作品の信号・レンダラー')}</small>
          </div>
          <ArrowRight />
          <div>
            {t('補正 G')}
            <small>{t('本試作では周波数ごとの行列')}</small>
          </div>
          <ArrowRight />
          <div>
            {t('スピーカー・室内応答 H')}
            <small>{t('合成モデル、将来は実測')}</small>
          </div>
          <ArrowRight />
          <div>
            {t('測定位置の音圧')}
            <small>{t('目標Tと比較')}</small>
          </div>
        </div>
        <div className="formula">
          min_G ‖H G − T‖²F + λ ‖G‖²F
          <br />G = (HᴴH + λI)⁻¹ HᴴT
          <br />
          λ(f) = λrelative · ‖H(f)‖²F / S
        </div>
        <p>
          {t(
            '各周波数でHは[M,S]、Tは[M,D]、Gは[S,D]。Mは調整点、Sはスピーカー、Dは目標入力の数です。λ=0では擬似逆行列を使います。上限が有効な場合、解いた後にGの列ノルムを制限するため、制限後のGは上式の無制約解と同一ではありません。',
          )}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('本試作で決めた項目')}</th>
                <th>{t('現在の処理と限界')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('目標T')}</td>
                <td>
                  {t(
                    '同じスピーカー位置からの、反射・機器誤差がない直接音。作品に最適な目標音場を求めたものではない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('応答H')}</td>
                <td>
                  {t(
                    '音速343 m/s、1/距離、直接音と直方体6面の一次反射。S1に既知のゲイン・遅延を加える。指向性・高次反射・飽和・実DSPは含まない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('評価の分離')}</td>
                <td>
                  {t(
                    '9点で補正を決め、別の6点で評価する。繰り返し未使用点を見て条件を選ぶなら、それは検証用となり、最終評価には新しい点が必要。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('周波数とレベル制約')}</td>
                <td>
                  {t(
                    '80–8,000 Hzの64点。列ノルム上限は単一入力時のモデル内の駆動エネルギー制約で、同時入力のピークや会場SPLを保証しない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('実機への適用')}</td>
                <td>
                  {t(
                    '周波数別行列をJSONで保存できる。連続帯域の補間・因果FIR・遅延・バイパスを備えた実時間フィルタは未生成。',
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="info-evidence">
          {t(
            '実装根拠：backend/numerics.py の synthetic_transfer、regularized_mimo、evaluate_transfer、run_demo。テスト：tests/test_numerics.py。',
          )}
        </p>
      </Section>
      <Section
        id="info-evaluation"
        n="05"
        title={t('論文の数値と、この画面の結果を区別する')}
      >
        <p>
          {t(
            '論文のTable 2では、モデル不一致時にSI-SDRが改善する一方、coherenceは線形法より低くなっています。',
          )}
          <Cite at="S3.T2">Table 2</Cite>
          {t('本試作でも、単一の改善値だけで空間再現の成功とは判定しません。')}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('論文Table 2 / 線形 → ADEPS')}</th>
                <th>4 mic</th>
                <th>5 mic</th>
                <th>6 mic</th>
                <th>Aria</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('SI-SDR / dB（高いほど良い）')}</td>
                <td>6.71 → 9.85</td>
                <td>7.82 → 10.57</td>
                <td>9.09 → 12.67</td>
                <td>3.31 → 4.94</td>
              </tr>
              <tr>
                <td>{t('coherence（高いほど良い）')}</td>
                <td>0.82 → 0.74</td>
                <td>0.82 → 0.76</td>
                <td>0.83 → 0.80</td>
                <td>0.76 → 0.64</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="muted">
          {t(
            '論文の公表値の一部を出典付きで整理しています。実機の測定値でも、本デモによる再計算結果でもありません。論文Figure 1はマイク符号化の評価図であり、スピーカーや実際の部屋の周波数応答としては使用していません。',
          )}
        </p>
        <h3>{t('このアプリで算出する指標')}</h3>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('指標')}</th>
                <th>{t('必要な情報・現在の意味')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('複素NRMSE / dB')}</td>
                <td>
                  {t(
                    '20 log10(‖推定−目標‖/‖目標‖)。振幅と位相を含み、小さいほど良い。SI-SDR、SPL、聴感評価とは異なる。',
                  )}
                </td>
              </tr>
              <tr>
                <td>coherence</td>
                <td>
                  {t(
                    'FOAの対応する参照がある場合に、有効な周波数・係数で二乗coherenceを集計。無音等で定義できない項目は除外。論文の集計条件との一致は未検証。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('残差・rank')}</td>
                <td>
                  {t(
                    'モデルと観測の整合、観測できる自由度。参照なしでも診断できるが、それだけで復元品質を証明しない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>SI-SDR / ILD / IC</td>
                <td>
                  {t(
                    '現在は未算出。整合する時間信号、両耳レンダラー、HRTF等を準備して別途実装する必要がある。',
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <h3>{t('調整点と未使用点を分けて読む')}</h3>
        <p>
          {t(
            '調整点で誤差が減っても、未使用点で同じ改善が得られるとは限りません。',
          )}{' '}
          {t(
            '現在選択している配置と条件の結果を確認し、改善と悪化を両方記録します。',
          )}{' '}
          {t(
            '合成モデルの結果を、論文の性能や実機での効果の検証結果として扱うことはできません。',
          )}
        </p>{' '}
      </Section>
      <Section
        id="info-geometry"
        n="06"
        title={t('配置・測定データ・Maxとのつながり')}
      >
        <p>
          {t(
            '3D表示は、仮想配置または入力された座標を確認するためのものです。',
          )}{' '}
          {t(
            'サンプル配置は操作と計算を説明する仮想データであり、実際の施設の配置や測量結果を示しません。',
          )}{' '}
          {t(
            '座標だけでは、マイクの取得特性Vやスピーカーから測定位置までの応答Hは確定しません。',
          )}
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('情報')}</th>
                <th>{t('確認できること')}</th>
                <th>{t('別途必要な確認')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('配置データ')}</td>
                <td>{t('座標、単位、原点、軸の向き、チャンネル名の対応。')}</td>
                <td>
                  {t(
                    '実物の位置、配線、出力順との一致は、測量や機器の記録と照合する。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('WebGL・平面図')}</td>
                <td>
                  {t('スピーカーと測定点の位置、選択状態、相互の位置関係。')}
                </td>
                <td>
                  {t(
                    '測定された音圧場や、空間全体の聴感品質を表示しているわけではない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('マイク観測とV')}</td>
                <td>
                  {t(
                    '共通の周波数と規約を持つ複素数STFTと取得行列を使い、線形符号化を検証する。',
                  )}
                </td>
                <td>
                  {t(
                    'マイク応答、同期、位相、チャンネル順を確認する。Vをスピーカー応答Hと取り違えない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('実測IRの解析')}</td>
                <td>
                  {t(
                    '共通の時刻原点を保ったIRの応答と到達目安を調べ、対応する参照があれば比較する。',
                  )}
                </td>
                <td>
                  {t(
                    '自動スイープ収録、未知の配線の同定、独立した時間合わせまで完了したという意味ではない。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('任意のMax連携')}</td>
                <td>
                  {t(
                    'ローカルブリッジを接続する場合、状態確認・テストチャンネル選択・ミュート要求を扱う。',
                  )}
                </td>
                <td>
                  {t(
                    'Web上の表示だけでは、機器との接続や実音出力は確認できない。',
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <h3>{t('仮想室と実測データを分ける')}</h3>
        <p>
          {t('仮想室の寸法や壁の反射は、計算のために選んだ条件です。')}{' '}
          {t(
            '実測データを使う場合は、座標の単位と原点、チャンネル対応、収録時刻、参照信号の条件を合わせます。',
          )}{' '}
          {t(
            '座標表示を測定記録の代わりにせず、計算結果には使用した条件とデータの出典を残します。',
          )}
        </p>
        <div className="source-links">
          <button onClick={() => onNavigate('layout')}>
            {t('配置を確認')}
            <ArrowRight size={14} />
          </button>
          <button onClick={() => onNavigate('ir')}>
            {t('IR解析へ')}
            <ArrowRight size={14} />
          </button>
          <button onClick={() => onNavigate('capture')}>
            {t('マイク側の検証へ')}
            <ArrowRight size={14} />
          </button>
        </div>
        <h3>{t('実機を使う場合の進め方')}</h3>
        <p>
          {t(
            'まず論理チャンネルと物理入出力を対応付け、同期した測定を複数位置で取得します。',
          )}{' '}
          {t(
            '調整に使う位置と、評価のために残す位置を分けて、同じ参照条件で比較します。',
          )}{' '}
          {t(
            '補正を実機に適用するには、因果フィルタ、遅延、レベル制約、バイパス、再測定を別途検証する必要があります。',
          )}{' '}
          {t(
            'スイープやIRは校正信号として位相と振幅を保持し、音声用の生成priorを通してから測定値として扱うことはしません。',
          )}
        </p>
      </Section>
      <Section
        id="info-status"
        n="07"
        title={t('ADEPSの公開状態と、今後必要な条件')}
      >
        <p>
          {t(
            '2026年9月10日に再確認した公式ADEUPSリポジトリはREADMEのみで、コードを準備中と記載されています。確認したツリーに、実行可能なADEPS実装や学習済み重みはありません。',
          )}
          <a className="citation" href={REPO} target="_blank" rel="noreferrer">
            {t('[2 · 確認したcommit]')}
          </a>
          {t('公開状態は今後変わり得ます。')}
        </p>
        <p>
          {t(
            '論文では5次・36係数のpriorを学習し、評価出力は1次・4係数です。推論は150ステップ。',
          )}
          <Cite at="S4">§4</Cite>
          {t(
            '5次・36係数のpriorと1次・4係数の評価出力は、Ambisonics表現の次数と成分数です。スピーカー台数を表すものでも、4chから36chへの復元成功を示すものでもありません。不足決定な高次係数への拡張は今後の課題とされています。',
          )}
          <Cite at="S5">§5</Cite>
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('段階')}</th>
                <th>{t('揃えるもの')}</th>
                <th>{t('その段階で確認すること')}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t('① モデルの接続')}</td>
                <td>
                  {t(
                    '正しい重み、構成、利用条件。STFTのFFT・窓・hop、複素数の表現、SHの順序と正規化。',
                  )}
                </td>
                <td>
                  {t('テンソルの形・レベル・時間・位相規約が互換であること。')}
                </td>
              </tr>
              <tr>
                <td>{t('② 推論の再現')}</td>
                <td>{t('γ、η′、圧縮、noise schedule、反復の終端処理。')}</td>
                <td>
                  {t(
                    '観測整合性が論文と同じ領域で計算されること。細部を推測した場合は独自実装と明示。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('③ 論文条件との照合')}</td>
                <td>
                  {t('学習・評価データの条件、参照信号、指標と集計方法。')}
                </td>
                <td>
                  {t(
                    '同一条件のベースラインを用意し、改善する指標と悪化する指標を両方示すこと。',
                  )}
                </td>
              </tr>
              <tr>
                <td>{t('④ 実機での検証')}</td>
                <td>
                  {t(
                    '実際のVまたは再生応答H、同期、配線と座標、計算時間、出力制約。',
                  )}
                </td>
                <td>
                  {t(
                    '物理モデルの妥当性、未知の測定点での性能、実運用に耐える遅延と再現性。',
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <details>
          <summary>{t('論文から確定できない実装上の細部')}</summary>
          <p>
            {t(
              'サンプルレート、FFT・窓・hop、チャンネル規約、γとη′の値などは、今回確認した本文・公開物だけでは十分に定まりません。Algorithm 1は最後の反復でもσᵢ₊₁を参照しますが、式(11)のM個のscheduleとの終端の対応は明記されていません。',
            )}
            <Cite at="S3.E11">{t('式(11)')}</Cite>
            <Cite at="algorithm1">Algorithm 1</Cite>
            {t(
              'これらを独自に決めて動かせても、その選択を公式実装の再現とは記載しません。',
            )}
          </p>
          <p>
            {t('学習目的は')}
            <Cite at="S3.E12">{t('§3.3・式(12)')}</Cite>
            {t(
              'に示されます。本試作では独自の合成空間係数と小型MLPにEDM型の重み付き二乗損失を適用し、学習済み重みと検証記録を同梱しました。論文の音声・残響データやネットワークは再現していません。各推論の時間を計測し、実時間動作は保証しません。',
            )}
          </p>
        </details>
        <a
          className="button-link"
          href={asset('/examples/adeps-adapter-requirements.json')}
          download
        >
          <Download size={14} />
          {t('アダプター接続条件 JSON')}
        </a>
      </Section>
      <Section id="info-references" n="08" title={t('参考文献・参照資料')}>
        <ol className="bibliography">
          <li id="ref-1">
            <b>{t('Milstein, Shlezinger & Rafaely（2026）')}</b>
            {t('上記論文、arXiv:2608.24558v2。')}
            <a
              href="https://arxiv.org/abs/2608.24558v2"
              target="_blank"
              rel="noreferrer"
            >
              {t('固定版の書誌')}
            </a>{' '}
            {t(' ／ ')}
            <a href={PAPER} target="_blank" rel="noreferrer">
              {t('節・式・表へのリンクを含む本文')}
            </a>
            {t(
              '。論文表示のライセンスはCC BY 4.0。本ページは要約・整理・独自の応用説明を含み、原論文の変更版ではありません。',
            )}
          </li>
          <li id="ref-2">
            <b>Amitmils / ADEUPS</b>
            {t('著者が公式実装用と明記したリポジトリ。確認commit')}
            <code>5076f163a1f939c297b55a39b2d9d33e2b224a5f</code>
            {t('。')}
            <a href={REPO} target="_blank" rel="noreferrer">
              {t('固定ツリー')}
            </a>{' '}
            {t(' ／ ')}
            <a
              href="https://github.com/Amitmils/ADEUPS"
              target="_blank"
              rel="noreferrer"
            >
              {t('最新の公開状態')}
            </a>
            {t('。本試作へコード・重みを取り込んだ出典ではありません。')}
          </li>
        </ol>
        <div className="source-links">
          <a
            className="button-link"
            href={asset('/info/references.bib')}
            download
          >
            <Download size={14} />
            {t('参考文献をBibTeXで保存')}
          </a>
          <a href={asset('/info/ADEPS_REVIEW.md')} download>
            {t('論文の詳細読解メモ')}
          </a>
        </div>
        <p className="info-evidence">
          {t(
            'このページの対応関係は同梱のソースと検証記録に基づきます。計算の結果は各画面の「結果JSON」で、条件・座標・出典とともに保存できます。',
          )}
        </p>
      </Section>
    </article>
  );
}
