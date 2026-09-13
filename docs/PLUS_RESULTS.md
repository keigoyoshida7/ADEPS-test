# ADEPS + α — 最終評価 / Final evaluation

独自の改善版と、同じ学習済み重みを使う独自ADEPS・Linearを比較した記録です。**原著の公式モデルを上回ったという結果ではありません。**

[比較と試聴](https://keigoyoshida7.github.io/ADEPS-test/?tab=plus&v=0.7.0) · [全結果JSON](../public/models/plus-benchmark.json) · [方式と引用](PLUS_METHODS.md) · [事前プロトコル](PLUS_PROTOCOL.md) · [再計算](PLUS_USAGE.md)

## 固定した条件

学習・開発で使っていないVCTKの8話者、4話者ペア、32部屋です。1–2音源の短い音声を、半径6 cmの6本球面アレイ、既知SNR 50 dB、次数5が一致するシミュレーションで評価しました。16 kHz、FFT512、hop128、32フレームです。波形指標と試聴は端部を共通に除いた0.248秒です。

設定は既存validationの16場面で選択し、コード・設定・入力一覧・重みの識別値を最終データの評価前に固定しました。正解係数や正解方向は復元関数へ渡さず、採点と観測生成だけに使っています。評価後の設定変更・悪化例の除外は行いません。

## 主指標：位相を含む複素FOAの復元誤差

DCから8 kHzまでの全257周波数を含む、場面ごとのNRMSE [dB]の算術平均です。**低いほど良い**指標で、振幅だけの誤差や全音声を一括した誤差ではありません。時間は各方式の復元処理の平均で、モデルの初期読込・採点・書き出しを含みません。

| 方式 / Method | 平均NRMSE / dB | 平均時間 / s | 完了 / 失敗 |
| --- | ---: | ---: | ---: |
| Linear・初期設定 / Linear · default | -13.202 | 0.002 | 32 / 0 |
| Linear・調整済み / Linear · tuned | -14.322 | 0.002 | 32 / 0 |
| 等方Wiener・既知SNR / Isotropic Wiener · known SNR | -14.323 | 0.032 | 32 / 0 |
| 既存ADEPS独自実装 / Current independent ADEPS | -4.061 | 38.686 | 32 / 0 |
| ADEPS独自実装・調整済み / Independent ADEPS · tuned | -8.217 | 37.621 | 32 / 0 |
| 方向共分散のみ / Directional covariance only | -18.265 | 0.093 | 32 / 0 |
| Linear＋波形整合 / Linear + waveform consistency | -20.861 | 2.744 | 32 / 0 |
| ADEPS + α・学習済み補正ON / ADEPS + α · learned refinement ON | -26.500 | 2.186 | 32 / 0 |
| 同じα処理・学習済み補正OFF / Same α processing · learned refinement OFF | -26.702 | 0.915 | 32 / 0 |

## 同じ場面での改善量

改善量は「比較方式の誤差 − 学習済み除去器ONの＋αの誤差」です。正なら＋αが良く、負なら比較方式が良いことを表します。97.5%区間は4つの話者ペアを単位とする256通りの再標本化による区間です。独立な単位が4組しかなく、区間の信頼性にも限界があります。

| 比較相手 | 平均改善 / dB | 97.5%区間 / dB | 勝 / 負 / 同点 / 未定義 |
| --- | ---: | --- | ---: |
| Linear・初期設定 / Linear · default | 13.299 | 11.439 – 15.149 | 32 / 0 / 0 / 0 |
| Linear・調整済み / Linear · tuned | 12.178 | 9.483 – 14.684 | 32 / 0 / 0 / 0 |
| 等方Wiener・既知SNR / Isotropic Wiener · known SNR | 12.177 | 9.481 – 14.684 | 32 / 0 / 0 / 0 |
| 既存ADEPS独自実装 / Current independent ADEPS | 22.439 | 20.805 – 23.866 | 32 / 0 / 0 / 0 |
| ADEPS独自実装・調整済み / Independent ADEPS · tuned | 18.284 | 16.865 – 19.344 | 32 / 0 / 0 / 0 |
| 方向共分散のみ / Directional covariance only | 8.235 | 5.781 – 10.953 | 32 / 0 / 0 / 0 |
| Linear＋波形整合 / Linear + waveform consistency | 5.639 | 4.883 – 6.393 | 32 / 0 / 0 / 0 |
| 同じα処理・学習済み補正OFF / Same α processing · learned refinement OFF | -0.202 | -0.237 – -0.156 | 0 / 32 / 0 / 0 |

事前に定めた主判定（調整済みLinearと既存ADEPSの両方に平均0.5 dB以上改善し、両区間の下限が0より大きい）：**達成 / passed**。調整済みADEPSや他の補助方式との比較も上表に残しています。

## 学習済み除去器の寄与

学習済み除去器OFFの方がONより平均 0.202 dB 良い結果でした。したがって、今回の全体改善を拡散モデルの効果とは主張しません。方向に関する統計と、波形・観測の整合処理が主に効いていることを示す比較です。これは今回の固定条件での結果で、他条件まで除去器が不要と結論するものではありません。

使用したニューラル重みは既存の30,781,344パラメータ・2,000更新の独自モデルです。今回の方式選択・最終評価では再学習していません。Linearから残差を学ぶ関連論文は設計の参考ですが、この重みを残差ターゲットで学習し直したわけではありません。

## 周波数と補助指標

[周波数比較図 SVG](../public/models/plus-frequency-comparison.svg) · [PNG](../public/models/plus-frequency-comparison.png) · [全方式の比較図 SVG](../public/models/plus-summary-comparison.svg) · [PNG](../public/models/plus-summary-comparison.png)

Webでは1 Hz–20 kHzの対数軸を使いますが、実際の正周波数の計算点は31.25 Hz–8 kHzです。範囲外を補間で埋めません。DCは主指標に含め、対数グラフではなく数値表で確認します。振幅スペクトル誤差、MSC、SI-SDR、DC除外・125 Hz以上の帯域誤差も全場面のJSONに保存しています。


平均の補助指標も以下に示します。NRMSEと振幅誤差は低いほど、MSCとSI-SDRは高いほど良い指標です。主指標で勝っても、すべての補助指標で勝ったとは扱いません。

| 方式 | DC除外NRMSE / dB | 125 Hz以上NRMSE / dB | 振幅誤差 / dB | MSC | SI-SDR / dB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Linear・初期設定 | -15.195 | -16.476 | 9.552 | 未定義 | 15.347 |
| Linear・調整済み | -19.519 | -16.787 | 9.521 | 未定義 | 17.137 |
| 等方Wiener・既知SNR | -19.521 | -16.787 | 10.169 | 未定義 | 17.123 |
| 既存ADEPS独自実装 | -4.303 | -4.046 | 14.753 | 0.143 | 5.702 |
| ADEPS独自実装・調整済み | -9.210 | -7.519 | 14.190 | 0.226 | 11.372 |
| 方向共分散のみ | -25.521 | -22.893 | 4.395 | 未定義 | 21.965 |
| Linear＋波形整合 | -19.839 | -17.086 | 7.101 | 0.646 | 19.845 |
| ADEPS + α・学習済み補正ON | -25.521 | -22.811 | 4.530 | 0.781 | 25.289 |
| 同じα処理・学習済み補正OFF | -25.726 | -23.021 | 4.104 | 0.798 | 25.515 |

＋α ONは方向共分散のみの方式に比べ、DCを除いたNRMSE、125 Hz以上のNRMSE、振幅誤差の平均ではわずかに悪化しました。学習済み補正OFFは上記6指標すべてでONより平均が良好です。全帯域の主指標が良くなったことを、すべての帯域・指標での改善とは述べません。

MSCの未定義は処理失敗や0を意味しません。Linear系ではDCやNyquist（8 kHz）で参照に存在する成分の推定がゼロになるため、相関の分母を定義できません。方向共分散のみもscene 0020のNyquistで同じ問題があります。未定義の周波数や場面を黙って除いた平均は作らず、全帯域平均を未定義のまま保存しています。周波数ごとの有効な値はグラフとJSONで確認できます。

## この結果が示していないこと

- 比較したADEPSは当方の独自実装です。著者の公式重み・WSJ0評価との同条件比較ではなく、原論文を上回ったとは確認できていません。
- 8話者・4組の小標本です。97.5%区間にも不確実性があり、別のコーパス・録音・配列への一般化は未検証です。
- 最終評価は1または2音源の音声、次数5の一致モデル、半径6 cmの単一6本球面アレイ、既知50 dB SNRのみです。方向推定は最大2方向を仮定しており、この設定への適合がα処理を助ける可能性があります。音楽・任意の音場・他のアレイ・実室の優位性は示していません。
- 雑音はSTFT成分ごとに独立に加えています。実録音の雑音とは相関が異なり、波形整合処理の利得がこの合成条件に依存する可能性があります。
- 波形評価は共通の端部除去後3,968サンプル（0.248秒）です。数値上の改善が、そのまま可聴差や長時間の再生品質を保証するものではありません。
- 改善版は方向共分散・固定学習済み除去器・STFT整合・観測補正の独自な組合せです。厳密なADEPS拡散事後サンプリングではありません。
- 学習済み補正OFFの結果も掲載しています。ONがOFFを下回る場合、改善を拡散モデル単独の効果とは主張しません。

## 再現用記録と出典

[v0.7.0配布物](https://github.com/keigoyoshida7/ADEPS-test/releases/tag/v0.7.0)に、全評価・開発記録、変更していない32場面のベンチマーク入力、事前選択したscene 0000の再計算入力・試聴を含めます。ベンチマーク用入力には採点用の正解を含みます。CLI用のprepared inputは正解を含まない別形式です。既存の重みは[v0.6.0](https://github.com/keigoyoshida7/ADEPS-test/releases/tag/v0.6.0)にあります。

音声：VCTK 0.92 — Yamagishi, Veaux & MacDonald, [DOI 10.7488/ds/2645](https://doi.org/10.7488/ds/2645), CC BY 4.0。合成室内応答・STFT加工・復元を施しています。原著のWSJ0評価ではありません。関連論文から応用した箇所は[方式と引用](PLUS_METHODS.md)を参照してください。

評価JSON SHA-256: `2a93066087321a836d30babb58e3c0418e23bbd9f9c0a20271af613570285a2c`

事前固定記録 SHA-256: `dd82ca0c440ccbc410fa4268796d470fd97e811b03e879ca6f21b2d2a7e4d94e`

## English scope

This is a sealed synthetic comparison against independently implemented Linear and ADEPS baselines, not the authors’ released model. All 32 scenes and all nine methods are retained, including failures and regressions. Positive paired gain favors the learned-denoiser ON hybrid. The learned-denoiser OFF control is reported without hiding a better result. The 30.78M prior is frozen; no new neural training is claimed.

The benchmark covers eight held-out VCTK speakers in four pair clusters, one six-microphone spherical geometry, known 50 dB SNR, matched order-5 observations and 1–2 speech sources. Independent STFT-bin noise and short 0.248-second waveform scoring limit the interpretation. The results do not establish original-paper superiority, general array invariance, long-form listening quality, music performance or physical-room performance.
