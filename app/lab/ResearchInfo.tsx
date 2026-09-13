'use client';
import { useLanguage, useT } from './i18n';
import { asset } from './assets';
import { useState, type ReactNode } from 'react';
import { ArrowRight, Copy, Download, ExternalLink } from 'lucide-react';
const PAPER = 'https://arxiv.org/html/2608.24558v2';
const REPO =
  'https://github.com/Amitmils/ADEUPS/tree/5076f163a1f939c297b55a39b2d9d33e2b224a5f';
const citation =
  'Amit Milstein, Nir Shlezinger, and Boaz Rafaely. “Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling.” arXiv:2608.24558v2, 27 August 2026. https://doi.org/10.48550/arXiv.2608.24558';
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
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const application = l(
    '本デモはMilstein, Shlezinger, and Rafaely（2026, arXiv:2608.24558v2）が示す、信号表現と物理取得モデルを分ける考え方を参照した。マイクからFOAへの経路には式(5)と同じ形式の線形符号化を独自実装した。旧実験では式(10)・式(11)・Algorithm 1に基づく拡散推論と小型MLPを接続した。追加した学習モデル比較では、線形推定・物理解像行列・時間共分散・チャンネルのパワーを入力する教師あり残差ネットワークを独自学習した。追加の観測整合は検証で係数0が選ばれ、同梱設定では適用していない。この新手法はADEPSの拡散モデルではない。学習・調整・最終評価を分け、同じ入力による線形法との比較を行う。著者のネットワーク・学習データ・重み、論文の公表性能、実際の音響システムでの性能は再現・検証していない。',
    'This demo draws on the separation of signal representation and physical acquisition model in Milstein, Shlezinger, and Rafaely (2026, arXiv:2608.24558v2). Its microphone-to-FOA path independently implements the linear encoding form in Eq. (5). The legacy experiment combines a small MLP with diffusion inference based on Eqs. (10)–(11) and Algorithm 1. The added learned-model comparison uses an independently trained supervised residual network conditioned on the linear estimate, physical resolution matrix, temporal covariance and channel powers. Validation selected zero additional observation consistency, so the bundled configuration does not apply that post-processing step. This new method is not the ADEPS diffusion model. Training, tuning and final evaluation are separated; linear and learned methods are compared using identical inputs. The authors’ network, training data, weights, published performance and real-system performance have not been reproduced or verified.',
  );

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
        <p>{l('新しい「学習モデル比較」では、物理モデルで条件付けした教師あり残差ネットワークを独自学習しました。旧小型モデルと区別し、同一入力のON / OFF、未使用条件での評価、Maxの音源ファイルを使う検証を追加しています。',
          'The new “Learned model comparison” independently trains a physics-conditioned supervised residual network. It is separate from the legacy small model and adds paired ON / OFF comparison, held-out evaluation and tests using source files from Max.')}</p>
        <p>{l('「拡散スタジオ」は、既存の小型priorによる実際の反復推論を、途中のFOA・方向別レベル・音で調べる追加画面です。仮想マイク配置を変える実験と、同じ観測に対して拡散seedを変える実験を区別します。',
          '“Diffusion studio” adds an interface for exploring actual iterative inference with the existing small prior through intermediate FOA, directional levels and audio. Changing the virtual array is a separate experiment from changing the diffusion seed for the same observation.')}</p>
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
          <span>{l('03 / 独自学習モデル', '03 / Independently trained model')}</span>
          <h3>{l('同じ入力でON / OFFを比較', 'Compare ON / OFF on the same input')}</h3>
          <p>
            {l('物理解像行列で条件付けした学習モデルと線形処理を比較。誤差・coherence・未使用条件の評価・FOA WAVを確認します。',
              'Compare a learned model conditioned on the physical resolution matrix with linear encoding. Inspect error, coherence, held-out evaluation and FOA WAV exports.')}
          </p>
          <button onClick={() => onNavigate('model')}>
            {l('学習モデル比較へ', 'Open learned model comparison')}
            <ArrowRight size={14} />
          </button>
        </div>
        <div>
          <span>{l('04 / 拡散の過程を調べる', '04 / Explore the diffusion process')}</span>
          <h3>{l('途中のFOAを形と音で比較', 'Compare intermediate FOA as shape and audio')}</h3>
          <p>{l('独自の小型priorを使う反復推論。seed・観測整合の強さを変え、保存した中間推定と最終出力を確認します。',
            'Iterative inference with an independent small prior. Explore seeds and guidance strengths, then inspect saved intermediate estimates and the final output.')}</p>
          <button onClick={() => onNavigate('diffusion')}>
            {l('拡散スタジオへ', 'Open diffusion studio')}
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
          ['learned', l('独自学習モデルと比較', 'Independent learned model')],
          ['diffusion', l('拡散スタジオの読み方', 'Reading the diffusion studio')],
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
          <p>{application}</p>
          <button onClick={() => copy(application)}>
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
                <td><Cite at="S2.E2">{t('§2.1・式(2)')}</Cite><br/><Cite at="S2.E5">{t('§2.3・式(5)')}</Cite></td>
                <td><b>{l('物理モデルを条件に使う独自の学習手法。', 'An independent learned method conditioned on the physical model.')}</b>
                  {l('E pとE V、時間共分散・パワーを残差ネットワークへ入力します。追加の観測整合は検証で係数0を選び、同梱設定では省略。論文の拡散推論とは異なる教師あり手法です。',
                    'A residual network receives E p, E V, temporal covariance and power. Validation selected zero additional observation consistency, so the bundled configuration omits that update. This is a supervised method distinct from the paper’s diffusion inference.')}</td>
                <td>{l('「学習モデル比較」 / ON・OFF・未使用条件の評価', '“Learned model comparison” / ON, OFF and held-out evaluation')}</td>
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
                  {l('SI-SDRは、対応する時間領域の参照FOAがある音声入力で算出。複素スペクトルのみの合成入力では未算出。ILD / ICには両耳レンダラーとHRTF等が必要で、現在は未実装。',
                    'SI-SDR is computed for audio input with matching time-domain reference FOA, but not for synthetic complex spectra alone. ILD / IC require a binaural renderer and HRTF; they remain unimplemented.')}
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
      <Section id="info-learned" n="08" title={l('独自学習モデル：何を変え、どう比較するか', 'Independent learned model: changes and evaluation')}>
        <p>{l('新しいモデルは、論文と同じ課題である「マイク観測と既知の応答VからFOAを推定する」ための独自手法です。拡散の反復を増やす代わりに、教師あり残差ネットワークによる一度の予測を使います。論文を上回る性能は目標であり、現在の結果から達成したとは主張しません。',
          'The new model addresses the same task—estimating FOA from microphone observations and a known response V—using an independent method. It uses a single supervised residual-network prediction instead of repeated diffusion updates. Exceeding the paper’s performance is an objective, not an established result.')}
          <Cite at="S2.E2">{l('観測モデル', 'Observation model')}</Cite></p>
        <p className="muted">{l('この追加章はv3も参照しています。既存の式・表との対応は、初期に照合したv2への固定リンクを保持しています。',
          'This added section also references v3. Existing equation and table mappings retain links to v2, the version initially reviewed.')} <a href="https://arxiv.org/html/2608.24558v3" target="_blank" rel="noreferrer">arXiv:2608.24558v3</a></p>
        <h3>{l('学習した部分と物理モデルの役割', 'Learned and physical components')}</h3>
        <p>{l('線形推定 âₗᵢₙ = E p と解像行列 R = E V を作り、時間共分散・36チャンネルのパワーとともに残差ネットワークへ入力します。465個の特徴量から、5次・36成分の複素空間係数を予測します。追加の観測整合としてE(p − Vâ)に比例する更新も実装していますが、別の検証セットで予測の混合率1・追加整合の係数0が選ばれたため、今回同梱の設定では追加更新を行いません。これらの設定は最終テストの前に固定しています。',
          'The network receives the linear estimate âₗᵢₙ = E p, resolution matrix R = E V, temporal covariance and powers of the 36 channels. It predicts 36 complex fifth-order spatial coefficients from 465 features. An optional update proportional to E(p − Vâ) is implemented, but separate tuning validation selected a prediction blend of 1 and an additional consistency coefficient of 0. The bundled configuration therefore omits that update. These settings were frozen before final testing.')}</p>
        <p>{l('学習の損失では、評価対象となる一次・4成分のFOAを重視します。参照FOAは学習と評価のために使い、推定器の入力には渡しません。マイクの位置だけから実機の応答Vを推測できるという前提も置きません。',
          'The training loss emphasizes the four first-order FOA components used for evaluation. Reference FOA is used for training and scoring, never as estimator input. Microphone coordinates alone are not assumed to determine a real device’s response V.')}</p>
        <p>{l('今回の同梱モデルは隠れ層4層・幅512・1,063,496パラメータです。時間共分散やパワーは入力した区間の全フレームから計算するため、未来のフレームも利用するオフライン処理です。リアルタイムの因果モデルではありません。',
          'The bundled model has four hidden layers of width 512 and 1,063,496 parameters. Temporal covariance and power use every frame of the supplied window, including future frames. This is offline, noncausal processing rather than a real-time causal model.')}</p>
        <div className="table-scroll"><table><thead><tr><th>{l('比較するもの', 'Comparison')}</th><th>{l('今回の扱い', 'Current treatment')}</th></tr></thead><tbody>
          <tr><td>{l('OFF：線形推定', 'OFF: linear encoding')}</td><td>{l('同じ観測p・応答V・正則化で計算した線形出力。ON / OFFを押すたびに入力を生成し直しません。', 'Linear output from the same p, V and regularization. Toggling ON / OFF never regenerates the input.')}</td></tr>
          <tr><td>{l('調整済みの線形法', 'Tuned linear encoding')}</td><td>{l('ベンチマークでは、別の検証セットで線形法の正則化を選んだ比較対象も追加。既定値の線形法に対する改善だけで判断しません。', 'The benchmark also includes a stronger linear baseline whose regularization was selected on separate validation data. Improvement over the default baseline alone is not the sole criterion.')}</td></tr>
          <tr><td>{l('ON：独自モデル', 'ON: independent model')}</td><td>{l('物理解像行列・時間特徴で条件付けした残差ネットワーク。今回の追加観測整合はOFF。重みのハッシュ、適用設定、計算時間を結果に保存。', 'A residual network conditioned on the physical resolution matrix and temporal features. Additional observation consistency is OFF in this configuration. Results record the weights hash, applied settings and computation time.')}</td></tr>
          <tr><td>{l('旧小型MLP', 'Legacy small MLP')}</td><td>{l('別のタブに拡散推論の実験を保存。新しい比較画面でも任意で同じ入力に実行できます。これも公式ADEPSではありません。', 'Its diffusion experiment remains in a separate tab and can optionally run on the same input in the new comparison. It is not official ADEPS either.')}</td></tr>
          <tr><td>{l('論文のADEPS', 'ADEPS from the paper')}</td><td>{l('課題・観測モデル・線形ベースライン・評価の目的を参照。学習データ・ネットワーク・公式重みが一致していないため、公表スコアと本試作の数値を直接競わせません。', 'Referenced for the task, observation model, linear baseline and evaluation goals. Because the training data, network and official weights differ, published scores are not directly ranked against this prototype.')}</td></tr>
        </tbody></table></div>
        <h3>{l('学習・調整・最終評価を分ける', 'Separate training, tuning and final evaluation')}</h3>
        <p>{l('学習データは、方向を持つ音場と位相遅延を含む合成データです。実際の音声コーパスや部屋の測定値ではありません。学習用、モデル選択用の検証、混合率などの調整用、最終テストで生成seedを分けます。使用した条件とseedは「学習モデル比較」の評価記録に保存します。最終結果を見てモデルを選び直す場合、そのテストは調整用となり、新しい最終テストが必要です。',
          'Training uses synthetic directional fields with phase delays, not recorded speech corpora or measured rooms. Separate generator seeds are used for training, model-validation, inference tuning and final tests. Conditions and seeds are saved in the comparison’s evaluation record. If test results inform another model selection, that test becomes tuning data and a new final test is needed.')}</p>
        <p>{l('今回の学習は3,072シーン（seed 10000〜13071）、モデル検証は64シーン（20000〜20063）。12,000ステップ学習し、モデル検証で選んだ10,400ステップ時点の重みを採用しました。別の36シーン（25000〜25035）で推論条件と線形比較対象を調整し、最終テストは90000以降、WAVテストは91000以降の別seedを使います。',
          'This run trains on 3,072 scenes (seeds 10000–13071) and validates the model on 64 scenes (20000–20063). Training runs for 12,000 steps; model validation selected the checkpoint at step 10,400. A separate 36 scenes (25000–25035) tune inference settings and the linear baseline. Final tests use seeds starting at 90000 and WAV tests starting at 91000.')}</p>
        <p>{l('改善した割合に加えて、悪化した条件、平均・中央値、信頼区間を確認します。NRMSEが改善してもcoherenceや聴感が悪化する場合があります。参照のない実録音では復元品質の数値を空欄にし、観測残差だけで成功とは判定しません。',
          'Inspect regressions, mean and median changes, confidence intervals and the fraction improved. Better NRMSE may coexist with poorer coherence or listening quality. For real recordings without a reference, reconstruction-quality fields remain unavailable; observation residual alone is not treated as success.')}</p>
        <h3>{l('Maxと実録音を使う検証', 'Testing with Max and recordings')}</h3>
        <p>{l('現在のWebとMaxの連携は制御メッセージです。新しい実験パッチでは発話・音楽・ノイズ・過渡音をモノラルWAVに保存し、その音源をWeb上の仮想アレイに入力できます。これは合成の収音テストです。実際の空間を評価するときは、スピーカーから再生し、マイクアレイで収録した音と対応する応答Vを入力します。どちらもファイルによるオフライン検証であり、会場の音をリアルタイムに補正する機能ではありません。',
          'The existing Web–Max link carries control messages. The new experiment patch saves speech, music, noise or transient sources as mono WAV files for a virtual array in the browser. That is a simulated capture test. For a real space, play through speakers and import the array recording with its matching response V. Both are offline file-based experiments, not live venue correction.')}</p>
        <div className="source-links"><button onClick={() => onNavigate('model')}>{l('学習モデル比較へ', 'Open learned model comparison')}<ArrowRight size={14}/></button>
          <button onClick={() => onNavigate('neural')}>{l('旧小型モデルの拡散推論へ', 'Open legacy small-model diffusion')}<ArrowRight size={14}/></button>
          <a href={asset('/models/spatial-benchmark.json')} download>{l('評価条件・記録 JSON', 'Evaluation conditions and record JSON')}</a>
          <a href={asset('/info/SPATIAL_MODEL.md')} target="_blank" rel="noreferrer">{l('手法・学習・失敗例の詳細', 'Method, training and failure analysis')}</a>
          <a href={asset('/examples/ADEPS_Max_Experiment.zip')} download>{l('Max実験パッチ', 'Max experiment patch')}</a></div>
      </Section>
      <Section id="info-diffusion" n="09" title={l('拡散スタジオ：反復・形・音の意味', 'Diffusion studio: iterations, shape and audio')}>
        <p>{l('この画面は、既存のTinyDenoiserと拡散サンプラーを使って実際に推論します。24,072パラメータの小型MLPは独自の合成空間係数で学習したもので、各時間・周波数点を独立に処理します。論文の音声priorや公式重みではなく、論文と同等の品質・再現性を示すものではありません。「学習モデル比較」の教師あり残差ネットワークとは別の処理です。',
          'This interface runs the existing TinyDenoiser and diffusion sampler. The 24,072-parameter MLP was trained on independently generated spatial coefficients and processes each time–frequency bin separately. It is not the paper’s speech prior or official weights, and does not establish paper-level quality or reproduction. It is separate from the supervised residual network in “Learned model comparison”.')}</p>
        <p>{l('既定の音源区間は0.35秒・16 kHz、FFT 256・hop 128です。DCを除く解析点は62.5 Hz〜8 kHzを62.5 Hz刻みで扱います。別の合成スペクトル実験の1 Hz〜20 kHz表示とは範囲が異なります。画面内の履歴は最新6件までで、残したい結果はZIPへ保存します。',
          'The default segment is 0.35 seconds at 16 kHz, with FFT 256 and hop 128. Non-DC analysis bins cover 62.5 Hz–8 kHz in 62.5 Hz steps, a different range from the separate 1 Hz–20 kHz synthetic-spectrum experiment. The interface retains the latest six runs; save ZIPs for results you want to keep.')}</p>
        <p>{l('参照したのは、観測と物理モデルを分ける考え方、圧縮した線形符号化空間での観測整合、denoiserを通る勾配を使った反復更新です。3D表示、途中の試聴、操作画面は本試作独自の追加です。',
          'The referenced ideas are the separation of observations and the physical model, observation consistency in compressed linearly encoded space, and iterative updates using gradients through the denoiser. The 3D view, intermediate audition and interface are independent additions.')}
          <Cite at="S2.E2">{l('観測モデル', 'Observation model')}</Cite>
          <Cite at="S3.E10">{l('式(10)', 'Eq. (10)')}</Cite>
          <Cite at="algorithm1">Algorithm 1</Cite>
        </p>
        <div className="table-scroll"><table><thead><tr><th>{l('操作・表示', 'Control or display')}</th><th>{l('意味', 'Meaning')}</th></tr></thead><tbody>
          <tr><td>{l('仮想アレイの配置', 'Virtual array layout')}</td><td>{l('音源を仮想マイクで拾う条件を変え、Vと観測を再計算します。実際のマイクを移動させたり、施設の配置を変更したりする操作ではありません。',
            'Changes the simulated capture conditions and recomputes V and the observations. It does not move a physical microphone or change a venue layout.')}</td></tr>
          <tr><td>{l('拡散seed', 'Diffusion seed')}</td><td>{l('音源・仮想アレイ・観測ノイズの条件を固定したまま、反復開始時の乱数を変えます。違う出力が得られても、正解や品質の向上を意味しません。',
            'Changes the random initialization while source, virtual array and observation-noise conditions stay fixed. A different output is not evidence of a correct or better reconstruction.')}</td></tr>
          <tr><td>{l('観測整合の強さ η′', 'Observation guidance η′')}</td><td>{l('観測へ整合させる更新の強さです。0でこの勾配更新を止めますが、初期値には観測が残るため、完全に無条件の生成にはなりません。大きくしても品質が単調に上がるわけではありません。',
            'Scales updates toward observation consistency. Zero disables this gradient update, but the initialization still contains the observation, so generation is not fully unconditional. Increasing it does not guarantee better quality.')}</td></tr>
          <tr><td>{l('途中の形と音', 'Intermediate shape and audio')}</td><td>{l('保存した反復時点のノイズ除去後のFOA推定を使います。反復番号は音源の再生時刻ではありません。最終出力は最後の反復更新後の結果として別に確認します。',
            'Uses denoised FOA estimates saved at selected iterations. An iteration number is not an audio playback time. The final output is inspected separately as the result after the last update.')}</td></tr>
          <tr><td>{l('3Dの方向別RMS', '3D directional RMS')}</td><td>{l('選択したFOA複素スペクトルの帯域別共分散から、方向ごとの合成信号のRMSを計算します。音源位置の地図、推定確率、部屋の中の音圧分布ではありません。再生系の配置・音圧マッチングの図とも異なります。',
            'Computes the RMS of a directional synthesis from the band-wise covariance of the selected complex FOA spectra. It is not a source-position map, probability distribution or room-pressure field. It also differs from playback-layout and pressure-matching views.')}</td></tr>
        </tbody></table></div>
        <h3>{l('試聴とMaxでの利用', 'Audition and use in Max')}</h3>
        <p>{l('ブラウザのステレオ試聴は、FOAから作った左右の仮想カーディオイドです。HRTFを使うバイノーラル再生ではないため、上下や前後の聴こえ方の評価には使いません。保存する4ch FOAはACN/N3D・W,Y,Z,X順です。Maxではこの規約に合う外部Ambisonicsデコーダーへ入力します。既存のMax比較パッチのSN3D経路へ入れる場合は、規約の変換が必要です。',
          'Browser stereo audition uses left and right virtual cardioids derived from FOA. It does not use HRTFs and is not suitable for evaluating elevation or front–back binaural cues. Exported four-channel FOA uses ACN/N3D in W,Y,Z,X order. In Max, use an external Ambisonics decoder configured for that convention. The existing Max comparison patch’s SN3D path requires a normalization conversion.')}</p>
        <p>{l('3D表示では試行ごとの書き出しゲインを除き、共通スケールがONなら同じ入力の履歴を共通の尺度で比較します。ブラウザの試聴も、対象の切り替え時に同じ入力の履歴内でゲインを揃えます。手動でプレーヤー音量を変えると比較条件が変わります。ZIPのWAVには試行ごとのゲインが残るため、Maxで別試行を比較する場合は保存したゲインを確認して揃えます。',
          'The 3D view removes run-specific export gain and, with shared scale enabled, compares history with the same input on one visual scale. Changing the audition target also aligns browser playback gain across that input’s history. Manually changing player volume changes the comparison condition. ZIP WAVs retain run-specific gains; inspect and align those gains when comparing different runs in Max.')}</p>
        <p>{l('同じ区間・同じ再生条件で比較し、音や形が魅力的かという制作上の判断と、参照信号にどれだけ近いかという復元精度は別に記録します。',
          'Compare the same segment and playback conditions. Record creative preferences about sound and shape separately from reconstruction accuracy against a reference.')}</p>
        <div className="source-links">
          <button onClick={() => onNavigate('diffusion')}>{l('拡散スタジオへ', 'Open diffusion studio')}<ArrowRight size={14}/></button>
          <a href={asset('/info/DIFFUSION_STUDIO.md')} target="_blank" rel="noreferrer">{l('操作と表示の詳細 · JP / EN', 'Controls and display details · JP / EN')}</a>
        </div>
      </Section>
      <Section id="info-references" n="10" title={t('参考文献・参照資料')}>
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
