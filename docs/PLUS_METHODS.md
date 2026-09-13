# ADEPS + α — 独自の復元方式と出典

このページは、論文と当方の実装を区別するための説明です。ここでの ADEPS は公開済みの独自実装、改善版は **方向共分散・固定学習済みノイズ除去器・波形整合・観測整合を組み合わせた独自方式**です。著者の公式モデルや、ADEPS Algorithm 1 の完全な再実装ではありません。

## 何を変更したか

従来の比較では、次数5の36係数を6本の仮想マイクから推定します。各周波数で得られる観測は6成分なので、正則化を弱くしても36係数すべてを一意に求めることはできません。そこで、方向に関する統計、学習済みの音場の傾向、隣接するSTFTフレームが同じ波形から作られるという条件を併用します。

推論が受け取るのは `p`（仮想マイクの信号）、`V`（既知のアレイ応答）、周波数、保存済みの重み、事前に選択した設定です。正解のAmbisonics係数・正解の音源方向・評価スコアを復元関数へ渡しません。正解は合成観測の生成と採点だけに使います。

```text
同じ観測 p、既知の応答 V
  ↓
方向を観測から推定 → 方向成分＋拡散成分の共分散 → 初期Ambisonics
  ↓
固定学習済み除去器による補正
  ↓
実際の波形として成立するSTFTへ整合
  ↓
V × 復元値 が p に近づくように補正
  ↺ 雑音パラメータを減らしながら反復
  ↓
追加の波形／観測整合 → FOA → 共通条件で採点・試聴
```

このループは決定的な **plug-and-play continuation** です。初期乱数を使う厳密な事後分布サンプリングとは呼びません。σは除去器の制御パラメータで、マイク雑音の実測値ではありません。

## 1. 方向に関する補助処理

固定した球面上の256方向を、ACN/N3Dの実球面調和関数へ変換します。各方向をVで仮想マイク側へ写し、観測の300–2,000 Hzの帯域から、最大2方向の成分を推定します。方向は正解データから取得しません。

各周波数の観測共分散を、推定した方向成分・拡散成分・センサー雑音に非負最小二乗法で当てはめます。得た音場共分散を等方的な共分散へ一部寄せ、Wiener形式の推定を行います。

```text
C_a = 方向成分の共分散 + 拡散成分の共分散
â   = C_a Vᴴ (V C_a Vᴴ + C_noise)⁻¹ p
```

今回の主評価では合成SNR=50 dBが既知です。この情報を使って、観測の総パワーから白色雑音パワーを見積もります。実マイクの未知雑音を測った値ではありません。同じSNR情報を使う等方Wienerも比較対象に含めます。この対照の共分散・負荷は観測から求めるため、係数が入力に依存しない固定Linearとは区別します。SNRを指定しない場合の推定、仮定SNRを30/40/60 dBへ変えた開発時の感度分析も別記録です。

任意配列のパラメトリック符号化とCOMPASSの、方向成分と拡散成分を扱う考え方を参考にしています。処理やパラメータを一致させた再現実装ではありません。[McCormack et al., 2022](https://doi.org/10.1109/TASLP.2022.3182857)、[COMPASS, 2018](https://acris.aalto.fi/ws/portalfiles/portal/30261835/ELEC_COMPASS_ICASSP2018_APolitis_STervo.pdf)

## 2. 固定した学習済みモデルによる補正

使用するのは既存の **30,781,344パラメータの独自モデル**です。理想的な次数5、アレイに依存しないAmbisonics係数を、HARPを調整した室内応答とVCTK 0.92の音声から作り、2,000回の更新で学習しています。今回の方式選択では重みを更新していません。訓練コーパス・実際に使用した場面数・損失・重みのSHAは、[学習記録](PAPER_PRIOR.md)と公開モデルカードに残しています。

入力の音量基準には、調整済みLinearのW係数から計算したRMSを一度だけ使います。正解から音量を計算しません。各反復で正規化基準を動かすこともしません。これは、従来の36係数全体のRMSと、理想係数を使った訓練時のRMSとの分布のずれを減らすための独自の選択です。完全に同一の尺度になるという保証はありません。

```text
x       = H(a / scale) / compressed_scale
z       = scale × H⁻¹(compressed_scale × Dθ(x, σ))
a_mixed = a + relaxation × (z − a)
```

Hの複素圧縮、次数5の学習事前分布、σを減らす考え方はADEPSを参照しています。除去器自体は当方が学習したもので、著者の重みではありません。[ADEPS](https://arxiv.org/html/2608.24558v3)

Linearの有用な情報を保持し補正を足すという方針は、残差学習を扱う関連研究も参考にしました。ただし、今回の除去器を残差ターゲットで再学習したわけではありません。[Deppisch et al., Residual Learning for Neural Ambisonics Encoders](https://arxiv.org/html/2601.18322v1)

## 3. 観測との一致を保つ補正

補正は圧縮Hの中ではなく、逆圧縮した物理的な複素係数に適用します。

```text
a_next = z + Vᴴ (V Vᴴ + λ I)⁻¹ (p − V z)
```

λは観測雑音と正則化のための量です。実装は特異値分解を使い、DCなどで階数が不足しても処理できます。λ=0では擬似逆行列を用います。雑音がある観測を厳密に一致させれば精度が上がる、という保証はありません。

線形逆問題を解く近接処理はDiffPIR、観測で決まる部分と決まらない部分を区別する発想はDDNMを参考にしています。当方には非線形Hが入るため、それらのサンプリング式をそのまま移植したものではありません。[DiffPIR](https://arxiv.org/html/2305.08995)、[DDNM](https://arxiv.org/html/2212.00490)

## 4. 一つの波形として成立させる処理

STFTの周波数・時間フレームは、互いに独立ではありません。同じ波形を重なった窓で解析しているため、隣のフレームとの関係を満たす必要があります。各Ambisonics係数をいったん波形へ戻し、同じ窓で再解析して整合させます。

```text
P_STFT(a) = STFT(iSTFT(a))
```

16 kHz、FFT512、hop128、periodic Hann、境界paddingなしの条件を、合成ターゲットと一致させています。32フレームに対応する4,480サンプルを保持し、推定段階で区間を切り落としません。片側スペクトルの内側を2倍に数える内積では直交射影に対応しますが、今回の主NMSEの全bin等重みと同一の距離とは主張しません。

今回の合成雑音は各STFT成分へ独立に加えており、実録音の重なった窓から得る雑音とは相関が異なります。整合性を使う方式の利得が、その生成条件に依存する可能性も残ります。時間領域の雑音や実録音での追試は未実施です。

この整合と観測補正を交互に行う方法も、学習を使わない比較方式として評価しています。改善版の成績が上がっても、そのすべてをニューラルモデルの効果としないためです。[Le Roux, Ono & Sagayama, 2008](https://www.jonathanleroux.org/pdf/LeRoux2008SAPA09b.pdf)、[Consistent Wiener Filtering, 2012](https://merl.com/publications/TR2012-090)

## 選択と比較

設定は既存validationの16場面で選択します。改善版の初回探索はσstart∈{0.3,1,3,10}、relaxation∈{0.25,1}、除去器8回、追加の整合反復∈{0,10,50}です。学習済み補正を完全にOFFにした同じ処理も別に保存します。ONの候補から選んだ最良値を改善版として報告し、OFFがより良い場合はそれも明示します。

また、既存ADEPS、調整済みADEPS、初期Linear、調整済みLinear、既知SNRの等方Wiener、方向処理のみ、波形整合のみを同じ入力で比較します。振幅だけでなく位相を含む全帯域FOA誤差を主指標にし、スペクトル誤差・MSC・SI-SDRも併記します。

最終判定では、学習・開発で使っていない8話者の32場面を使います。設定・コード・音声・重み・評価方法のSHAを、最終テストを開く前に記録します。失敗や悪化した例を削除しません。詳細は[評価プロトコル](PLUS_PROTOCOL.md)を参照してください。

## What this implementation establishes

This is an independent spatial-covariance / frozen-denoiser / STFT-and-array-consistency hybrid, not the authors' official ADEPS model or an exact posterior sampler. The 30.78M denoiser is unchanged. Reconstruction consumes observations and array responses, never target coefficients or oracle directions. The learned-refinement OFF control is always reported, including when it performs better. The benchmark can establish performance relative to the tested independent baselines under the sealed synthetic conditions; it does not establish superiority over the original paper or real-room reproduction quality.
