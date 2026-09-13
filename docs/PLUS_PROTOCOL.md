# ADEPS+alpha 評価計画 / Evaluation protocol

この文書は、独自実装のADEPS+alphaが、同じ観測からのLinearと現在の独自ADEPSより復元誤差を減らすかを調べるための事前計画です。**目標値は結果ではありません。原著ADEPSを上回ること、実際の会場での効果、聴感上の改善は未確認です。**

封印状態の正本は `work/plus-v1/selection-lock.json` です。最終テストの話者・入力・候補・実装をこの記録に確定し、結果を見る前に計画を封印します。封印時の文書SHA、Git HEAD、未コミット変更の状態、実際に実行するソース集合のSHAを評価記録へ保存します。HEADだけを実行コードの識別子にはしません。新しい結果を見てこの計画を書き換えた場合は、事後変更として履歴を残します。

## 1. 比較する問い

主仮説は「ADEPS+alphaの全帯域FOA誤差が、開発データで調整したLinearと、保存済みの独自ADEPSを両方上回る」です。予測する対象は、理想的な5次Ambisonicsから仮想マイク観測を作り、最初の4係数を復元する合成音声実験です。独自ADEPSは`paper-prior-v1`の30,781,344パラメータのモデルで、著者の公式チェックポイントではありません。

比較するpriorの重みSHA-256は次の値に固定します。重みを追加学習した場合は別のモデル・別の実験として扱い、アルゴリズムだけの効果と混ぜません。

```text
0e88c717770453520331d797392794934c6eb167716007b44bb58633e811d7b2
```

## 2. データの役割と分離

| 役割 | 初回の規模 | 使用目的 | 最終判定への利用 |
| --- | --- | --- | --- |
| Train-only calibration | 既存train話者の64場面 | 固定統計・補正パラメータの学習 | 含めない |
| Development | 既存validation 2話者・40発話から生成された先頭16場面 | 正則化、拘束、ADEPS+alphaの候補選択 | 含めない |
| Legacy diagnostics | 既存test 2話者の過去16場面、公開例A/B/Cなど | 不具合の分析・説明用 | 未使用テストとは呼ばない |
| Sealed final test | 新規8話者×異なる4発話、計32発話／32独立部屋 | 封印後の一度の最終比較 | 全32場面を含める |

最終テストは8話者を互いに重ならない4組へ固定し、各組に独立した8部屋を割り当てます。各組の4場面は1音源、残る4場面は2音源で、合計は**32場面・48音源呼び出し**です。取得する固有発話は32本で、一部を同じ話者ペア内の別場面でも使用します。発話再利用や同じ話者から生じる依存を保つため、各組の8場面を信頼区間の再標本化ブロックにします。同じ話者の複数発話を独立した話者と数えません。

新規8話者は、既存の次の16話者をすべて除外して取得します。元のtestを学習に使っていなくても、結果を見て改良した後の確認用データとして再利用しません。過去の記録は「当時の重み学習では未使用だった評価」として保持します。

```text
train:      p339 p330 p279 p297 p264 p305 p374 p271 p246 p277 p304 p351
validation: p261 p237
old test:   p300 p292
```

新規話者ID、発話ID、4つの話者ペア、全32場面の部屋・音源座標・T60・切り出し位置・生成seedは、封印するmanifestを正本とします。話者の選択seedだけで新規性を保証せず、既存IDとの集合の交差を検査します。部屋seedはcalibration・development・testそれぞれの領域に分け、他splitの件数変更でtestの部屋が変わらないよう、生成済みの仕様を固定します。

取得計画`work/plus-v1/sealed-data/subset-plan.json`では、話者選択seedは`2026091307`、ペアは次の4組です。これは取得対象の選択記録であり、取得や最終評価の完了を示しません。

| Cluster | 話者 |
| --- | --- |
| speaker-pair-0 | p249 / p263 |
| speaker-pair-1 | p259 / p244 |
| speaker-pair-2 | p251 / p314 |
| speaker-pair-3 | p270 / p361 |

同じ音声ファイルや同じ切り出しを複数splitに入れません。取得計画はVCTKの共通文章を避けるため発話番号001–024を除外し、既存320ファイルで使用した全発話番号も除外します。番号による除外は文字起こしそのものの照合ではないため、**話者・音声ファイルは分離、発話内容の完全分離は未確認**です。短い区間の選択や無音判定は、参照だけを用いる固定規則で候補比較前に実行し、同じ区間を全手法へ渡します。結果の良し悪しで切り出しを変えません。

VCTK原音声は公式配布先から必要な発話だけ取得し、出典・ライセンス・SHAを保存します。原音声と加工した公開試聴例には著者、DOI、CC BY 4.0、加工内容を表示します。[VCTK 0.92公式記録](https://datashare.ed.ac.uk/items/30e7453c-9ea8-48b4-8e18-f96d0dc62928/full)

## 3. 観測条件

主評価は次の1条件に固定し、得意なアレイやSNRを後から主条件へ昇格させません。

| 項目 | 主条件 |
| --- | --- |
| 音場／prior／評価次数 | Neff=5 / Np=5 / Nenc=1 |
| マイク | 6ch、既存生成規則による球面配置、半径0.06 m |
| 観測SNR | 50 dB、観測の複素STFTガウス雑音 |
| サンプルレート／STFT | 16,000 Hz / FFT 512 / hop 128 / 32 frames |
| Ambisonics規約 | real SH、ACN/N3D、FOAはW,Y,Z,X |
| 拡散 | 150更新、σmax=20、σmin=0.002、ρ=10、観測からのwarm start |
| 主推論seed | 42、全場面・全拡散手法で同じ規則を使用 |

観測ノイズseed、実際のマイク座標、応答V、観測p、周波数、区間のSHAを場面ごとに記録します。音声・観測・参照・STFTを全手法で共有し、手法ごとに別のノイズを引きません。推論時の正規化は観測またはcalibrationで固定した統計だけから求め、正解音場やtest全体の統計を使いません。参照は入力生成と採点だけに使用します。

この初回試験の雑音は、時間波形を録音して得た雑音ではなく、各STFT成分へ加える独立な複素ガウス雑音です。重なった窓を持つ実録音の雑音とは相関構造が異なり、STFT整合処理による改善量にも影響し得ます。時間領域から生成した雑音・実録音で同じ改善が出ることは未確認です。

Q=4/6の不規則配置、Q=4球面、SNR=30 dB、別の拡散seedは開発または事前指定した副評価とします。追加する場合は実行前に設定と対象場面を固定して、主評価とは別表にします。今回はNeff=15、実マイク応答、実収録、会場再生の試験を含みません。

## 4. 調整するLinearと比較群

現行の線形推定は次式です。設定λは、周波数ごとの絶対的なγ²と区別します。

```text
γ²(f) = max(λ · trace[V(f)V(f)ᴴ] / Q, 10⁻¹²)
E(f)  = V(f)ᴴ [V(f)V(f)ᴴ + γ²(f) I]⁻¹
â(f)  = E(f) p(f)
```

対応実装は[backend/capture.py](../backend/capture.py)です。**λ=.001だけを上回ったことを、調整済みLinearを上回ったこととして扱いません。**

| 手法 | 開発段階での調整 | 最終テスト |
| --- | --- | --- |
| Default Linear | なし、λ=.001 | 全32場面 |
| Tuned Linear | λ∈{10⁻⁸,10⁻⁷,10⁻⁶,10⁻⁵,10⁻⁴,10⁻³,10⁻²,10⁻¹,1,10}の10点 | 選択した1設定で全32場面 |
| Current independent ADEPS | 元のλ=.001、η′=50、同じ保存重み | 150更新で全32場面 |
| Tuned independent ADEPS | tuned Linearのλを共通にし、η′∈{0,1,5,20,50,100}から選択 | 選択した1設定、150更新で全32場面 |
| ADEPS+alpha | calibrationで求めるパラメータ、探索候補、選択規則を別記して封印 | 選択した1設定で全32場面 |

すべての選択にはdevelopmentの全帯域・場面平均誤差だけを使用します。同点は事前指定した固定順で解決します。seed別の最高値、途中段階の最低誤差、testの参照を用いるoracle混合率は選択に使用しません。η′=0でもwarm startは観測依存です。

計算量を抑える段階的探索では、まず全6種類のη′を32更新でdevelopmentの16場面に適用し、上位2候補を残します。η′=50も比較用に保持します。残った設定は同じ16場面で**150更新へ戻して再評価**し、その結果で設定を固定します。32更新の順位を150更新の性能として扱いません。これは限定した探索予算であり、η′の大域最適値を保証しません。ADEPS+alphaの段階的探索も、候補一覧・試行数・昇格数・同点処理をtest前に固定します。

最終比較で現行ADEPSを32更新に短縮しません。改善法が150更新未満なら、その実際の計算量を表示した上で150更新のbaselineと比較します。複数seedの融合などで計算を増やす場合は、同じ計算予算をbaselineに与える追加比較を設けます。モデルforward回数、VJP／backward回数、実時間、デバイス、取得可能なメモリ指標を記録します。このMPS実行では場面終了時の割当量を記録し、ピークメモリは未計測と明記します。重みが同じ比較と、追加学習の効果を含む比較を分けます。

## 5. 主指標と帯域

採点対象は、逆圧縮後・共通の実数DC/Nyquist投影後・出力ゲイン適用前の複素FOA係数です。STFTの片側周波数binを、DCからNyquistまで各1回含めます。時間信号のParseval重みへ置き換えず、全手法で同じ定義を使います。

場面sの誤差とbaseline bに対する改善量を次で定義します。

```text
e_s(method) = 10 log10 [ Σ(f,c,t) |â_s(f,c,t) − a_s(f,c,t)|²
                         / Σ(f,c,t) |a_s(f,c,t)|² ]
d_s(b)      = e_s(b) − e_s(ADEPS+alpha)
Δ(b)        = mean_s d_s(b)
```

`10 log10(NMSE)`と`20 log10(NRMSE)`はこの定義で同じdB値です。主指標は**各場面のdB値の算術平均**で、場面をまたいでエネルギーを先に合算したpooled NMSEとは区別します。FOAは4係数すべてを含み、推定に合わせて参照やゲインを最適化しません。改善量が正なら誤差が減少、負なら悪化です。

| 区分 | 周波数 | 扱い |
| --- | --- | --- |
| 主指標 | 0–8,000 Hz、DCとNyquistを含む257 bins | 成功判定に使用 |
| 副指標A | 31.25–8,000 Hz、256 bins | DCを除いた感度分析 |
| 副指標B | 100–8,000 Hzに入る実bin、125–8,000 Hz、253 bins | 低域への依存を調べる感度分析 |

既知の旧scene0では、参照FOAのDCと31.25 Hzの2binが全エネルギーの約93.61%を占める診断が得られています。これは既知例の性質で、全データの性質とは仮定しません。各新規場面でも周波数ごとの参照エネルギー割合を報告します。低域を除いて改善した結果だけを選び、全帯域で改善したと主張しません。主指標を高域だけへ変更する場合は別の仮説・新しい未使用テストが必要です。

分母が0の完全無音参照は、候補比較前の共通入力検査で扱います。推論開始後に生じた非有限値、出力欠損、完全な失敗は場面を削除せず記録します。完全一致の誤差0は−∞として状態を残し、任意の有限値へ置き換えて平均を作りません。主平均または必要な比較が未定義のままなら、成功条件を満たしたとは判定しません。

## 6. 副指標

周波数別の振幅スペクトル誤差、magnitude-squared coherence（MSC）、時間波形のSI-SDRを報告します。振幅誤差とMSCの定義・数値floor・有効bin数は[frequency_metrics](../backend/diffusion_studio.py)に従い、実行時の定義をJSONにも保存します。方法ごとに異なる周波数・チャンネルを落として平均しません。

- 振幅誤差：周波数ごとに`|20 log10(|参照|/|推定|)|`を時間と4係数で平均します。全手法で共通の参照由来floorを使用します。
- MSC：係数ごとに時間方向のcross powerから算出し、その後、共通の参照有効係数集合で平均します。参照が有効なのに推定が全0の係数がある場合は未定義として報告し、その係数だけを除外して点数を良くしません。
- SI-SDR：同じiSTFT・区間でDCを除去し、FOAチャンネル別の射影誤差を求めます。全手法共通の参照有効チャンネルを使用し、推定側の失敗で未定義になったチャンネルは、その手法だけの平均から除外しません。チャンネル別値、有効数、集約順、無音時の扱いを評価JSONに記録します。旧UIの`mean_valid_channels_db`だけを使う場合は、手法間で有効集合が同一であることを確認し、異なる場合は共通集合による集約か「比較不能」を表示します。振幅の全体倍率に不変な指標なので、NMSEの代替にはしません。

平均値に加え、周波数曲線、場面別値、悪化数、最大悪化、無効値・失敗数を掲載します。低い観測残差、きれいな3D形状、異なるseedでの見た目の変化を復元精度の証明とは扱いません。副指標だけ良かった場合は、その指標・帯域に限定して説明します。[原論文の評価指標](https://arxiv.org/html/2608.24558v3#S4)、[Gen-Aの指標定義](https://arxiv.org/html/2501.08047v1#S3.SS4)

## 7. 信頼区間と成功条件

場面ごとに同じ参照からpaired差`d_s`を作り、全32場面を同じ重みで平均します。信頼区間では、封印した**4つの話者ペアをブロックとして復元抽出**し、各組の8場面をまとめて保持します。各手法で同じ抽出を使用します。4組から4組を引く256通りを全列挙し、改善量のpercentile区間を求めます。quantileの補間規則は`linear`に固定します。

主比較は、ADEPS+alpha対 **tuned Linear** と対 **current independent ADEPS** の2つです。それぞれ97.5%区間（1.25–98.75 percentile）を使い、次の全条件を満たしたときだけ初回主仮説を達成したと記録します。

1. 全帯域の場面平均改善量が、両baselineに対してそれぞれ **0.5 dB以上**。
2. 両比較の97.5%区間の下端がそれぞれ **0 dBより大きい**。
3. 全32場面の結果・失敗状態が揃い、主判定に必要な値が未定義でない。

0.5 dBは事前に選んだ工学的基準で、可聴差の閾値ではありません。2比較に97.5%区間を用いるのは多重比較への配慮ですが、**独立ブロックが4組しかないため、bootstrap区間の被覆精度は不確かです**。条件を満たしても、小標本・同一コーパス・合成部屋による初回結果として公表します。32場面を独立として狭い区間を作ったり、4組を大量の独立話者がいるように説明したりしません。

tuned independent ADEPSとの比較も全例掲載しますが、事後に比較相手を弱いものへ差し替えません。主条件を満たさなかった場合は「未達」または「判定不能」を表示し、良かった副指標も悪かった副指標も併記します。

## 8. 封印と最終テストの初閲覧

最終テストのmanifest・音声のSHA・shape・ライセンスを事前に検査することはできます。ただし、候補を最終テストで動かす、採点する、音を聴いて候補を変えることは、すべて最終テストの初閲覧に数えます。生成準備の段階ではtestの誤差や手法別試聴例を表示しません。

[scripts/plus_data.py](../scripts/plus_data.py)は既存の固定generatorを変更せずに別の取得・場面manifestを作ります。testのrenderには`work/plus-v1/selection-lock.json`が必要です。封印記録ではそのファイルの存在だけでなく、以下の候補・入力・コード・文書SHAとの一致を確認してから最終推論を開始します。

初閲覧の前に次の記録を確定します。

- protocolの版・SHA、時刻、Git commit、推論・採点コードSHA、重みSHA、実行環境。
- calibration／development／testのmanifest SHA、全話者・発話・部屋・観測seed、32場面の入力SHA、話者ペアの割当。
- calibrationで学習したパラメータ、developmentの全探索結果、最終候補の設定、固定seed、選択・同点処理、推論予算。
- 指標の定義、周波数mask、数値floor、無効値規則、CIの単位と補間規則、成功条件。
- 公開する試聴・3D例は場面ID順の先頭 **scene 0000 の1例** に固定します。結果の良し悪しで変更しません。全32場面の数値は別途すべて公開します。

封印後は全32場面と全baselineを実行し、終了したものから良い例だけで結論を出しません。UIに保存する音声・3Dは少数の代表例でも、数値表・JSON/CSVには全32場面を含めます。計算中、未実行、失敗、完了を区別します。

バグ修正で再計算する場合は、原因、影響範囲、最初の閲覧時刻、変更したコードを残します。採点や候補の変更につながった場合、このtestは以後development扱いです。新しい成功判定には別の未使用testを用意し、同じ結果を見直して「未使用」に戻しません。

## 9. 原論文との比較で言える範囲

[ADEPS v3 §4](https://arxiv.org/html/2608.24558v3#S4)は、VCTK学習とWSJ0評価、HARP、Neff=5/15、13種類のアレイなどを用いた数値実験です。今回はVCTKの一部、独自の学習済み重み、限定した32場面・1主条件による独自実験です。元論文の表・曲線と本実験の点数を引き算して、同条件の優劣としません。

著者の[公開README](https://github.com/Amitmils/ADEUPS/blob/main/README.md)と[Releases](https://github.com/Amitmils/ADEUPS/releases)を2026-09-13に確認した時点では、コードは準備中とされ、公開リリースはありませんでした。以後の公開状況は比較を行う時点で再確認します。著者の実装とデータ条件を揃えた独立テストを実行するまでは、表現を **「原論文に着想を得た独自ADEPSに対する改善」** に限定し、**「原著ADEPSを超えた」は未確認**とします。

## English summary

This prospective protocol is sealed by selection-lock.json before final evaluation. The lock records Git HEAD and dirty state as well as hashes of the actual executed source set; HEAD alone does not identify uncommitted code. It evaluates an independent ADEPS+alpha method. The primary evaluation uses 32 fresh utterances from eight speakers excluded from all 16 previously used speakers, 32 independent rooms, and one fixed array condition: order-5 simulation and prior, FOA output, six spherical microphones at 0.06 m, and 50 dB observation SNR. Four disjoint speaker pairs each supply four single-source and four two-source scenes: 48 source uses in total, with some utterances reused within their pair. Calibration uses 64 train-only scenes; candidate selection uses the first 16 existing validation scenes. Previously viewed test examples are diagnostic/development data, not an untouched confirmation set. Common utterance indices 001–024 and every legacy utterance index are excluded, but complete transcript disjointness is not asserted.

Tune Linear over ten trace-normalized regularization values. Keep the current independent ADEPS baseline at 150 reverse updates; a 32-update development search must be checked at 150 updates before freezing candidates. The same checkpoint, inputs, reference, seed policy and numerical conventions are used across methods. Additional training or computation is reported separately.

The primary metric is the arithmetic mean of per-scene complex FOA NMSE in dB, including DC through 8 kHz before export gain. Report DC-excluded and 100 Hz–8 kHz secondary bands without using them to claim full-band success. Spectral error, MSC, SI-SDR, all regressions and failures are also reported.

Success requires at least 0.5 dB mean improvement over both tuned Linear and the current independent ADEPS, and a positive lower endpoint of each 97.5% paired interval. Resample four disjoint speaker-pair blocks, preserving their scenes. Four independent blocks give uncertain interval coverage; any positive result remains a small-sample synthetic experiment, not paper-level or real-room validation. Freeze manifests, candidates, code, metrics and display-example selection before the first final-test score or listening comparison. Results used to change the method become development evidence and require a new untouched test for confirmation.

## 10. 今回の + α の選択規則

方向推定と観測共分散によるWiener初期値、保存済みDθ、物理観測への近接補正、STFT整合性を組み合わせます。新しいニューラル重みの学習は行いません。64場面から求める共分散の候補も調べますが、最終選択へ採用する場合だけ明記します。

ハイブリッドの開発探索は σstart∈{0.3,1,3,10}、Dθの混合率∈{0.25,1}、8段階、各段階のSTFT投影あり、近接補正λ=10⁻⁷です。最後のSTFT整合処理は{0,10,50}回、λ=.001で計24候補です。全16場面の主誤差平均が最小の **Dθを使用する候補** を選択します。同点なら上記リスト順を保ちます。Dθ混合率0の対照も同じ入力・初期値・8段階・後処理で保存し、学習済みモデルを加えたこと自体の効果を分けて報告します。ONがOFFより良いと仮定しません。

方向推定初期値の候補、STFT単独、train共分散、PnP、Linear、ADEPSの開発全記録と選択した設定を封印します。STFT単独比較は tuned Linear を初期値とし、200回・λ=.001です。方向推定は観測から最大2方向、既定256候補、300–2,000 Hzを用い、最終的な周波数ごとの復元は全257 binsです。選択された共分散の拡散成分重み=.25、λ=10⁻⁶、合成の観測SNR=50 dBを既知とする設定を固定します。既知SNRは合成試験の条件であり、実録音で自動的に分かる量ではありません。既知SNRのみを利用する方向成分なしの等方Wiener対照も掲載します。その共分散・負荷は観測から推定されるため、入力に依存しない固定Linearとは区別します。

短い32-frame出力に対するSTFT整合性は、4480サンプルの有限区間の周期Hann重なりから計算します。試聴・SI-SDRは両端256サンプルずつを除いた3968サンプルで共通に比較します。試聴が約0.248秒と短いことを表示し、音楽や長時間音声への性能は未検証です。
