# 原論文の指標による追加評価 / Paper-metric comparison

This is **post-hoc scoring of fixed v0.7.0 reconstructions**, not a reproduction of the authors’ experiment. It adds metric views without training, inference, parameter selection, replacement of saved estimates, or changes to the prospective benchmark and its verdict.

公開画面では、論文掲載値と本実装の追加採点を別の表に表示します。原著を上回ったかどうかを判定するページではありません。論文側の表・配置を切り替えても、独自試験の入力や復元結果は変わりません。

## 1. 比較対象と出典

原著は Milstein, Shlezinger and Rafaely, *Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling*, arXiv:2608.24558**v3**, 2026-09-08。表1–3の140個の値はバージョンを固定したHTMLとPDF第4ページから転記しています。出典、照合記録、未知の条件は [paper-reference-v3.json](https://github.com/keigoyoshida7/ADEPS-test/blob/main/public/models/paper-reference-v3.json) に保存しています。[原論文 §4](https://arxiv.org/html/2608.24558v3#S4)、[PDF](https://arxiv.org/pdf/2608.24558v3#page=4)

| 条件 | 原論文 | 本実装の追加評価 |
|---|---|---|
| 学習した事前分布 | 5次、論文記載30.8Mパラメータ | 独立実装の5次、30,781,344パラメータ、保存済み重み |
| テスト音声 | WSJ0 | 学習とは別話者のVCTK |
| 場面 | 1,000 | 保存済み32場面、4話者ペア群 |
| 配置 | 4・5・6本を各4配置＋Project Aria＝13配置 | 半径0.06 mの6本球面アレイ1配置 |
| 音場の次数 | 表1は5次、表2・3は15次 | 5次 |
| 採点する係数 | 1次、4係数 | 1次、4係数、ACN/N3D `[W,Y,Z,X]` |
| マイクノイズ | Gaussian、50 dB SNR | Gaussian、50 dB SNR |
| 処理区間 | 詳細未記載 | 16 kHz、FFT512、hop128、32フレーム |
| 両耳評価 | KU100 HRTF、ERB、引用されたILD/IC | SADIE II KU100から作る独自FOAデコーダと明示した帯域・相関処理 |

原論文の13,000テスト信号は1,000場面×13配置に対応し、13,000の独立した音声場面ではありません。表3は特定の4マイク配置で学習したU-NetとDiff-Enc.を含み、表1・2の4配置をまとめた列とは別です。音声、配置、処理長、学習状態、採点の詳細が異なるため、掲載値との差を「論文からの改善率」として計算しません。

原著の全方式が一様に劣るという結果でもありません。v3表3のSI-SDRはDiff-Enc.が9.52 dB、ADEPSが9.23 dB。コヒーレンスはU-Netが0.83、ADEPSが0.71です。[表3](https://arxiv.org/html/2608.24558v3#S3.T3)

**NRMSEは原論文の表1–3にありません。** 従来の独自試験の主指標として保持し、このページの5指標とは分けます。原著Fig. 1の数値曲線は転記・補間・推測しません。

## 2. 同じ保存結果を採点する

再評価は保存済み `cache/test/0000…0031.npz` と、各場面の9方式の推定NPZを読みます。入力、推定ファイル、選択ロック、凍結ソースのSHA-256と場面・方式の識別子を確認してから採点します。照合に失敗した場合は、新しい音を生成して穴埋めしません。

スペクトルと両耳の評価には、未圧縮の複素Ambisonics係数の先頭4chを使用します。全方式と参照でDC/Nyquistの虚部を0にそろえます。WAV書き出しの共通ゲイン、個別のピーク正規化、プレビュー用cardioid処理は適用しません。スペクトル評価前のiSTFT→STFT再解析も行いません。

正解データは**追加採点**に使います。固定された推定結果を作り直すための入力にはしません。すでに開封したテストに新しい指標を加えるため、結果は事後的・記述的評価です。追加指標に応じて方式や設定を選び直したり、事前の主比較の合否を変更したりしません。

## 3. SI-SDR：保存済みの波形評価を維持

参照波形を `s`、推定波形を `ŝ` とすると、各対象chで

```text
α = <ŝ, s> / <s, s>
s_target = α s
SI-SDR = 10 log10( ||s_target||² / ||ŝ − s_target||² )
```

を使用します。これは推定を参照の方向に射影する尺度不変の指標です。絶対音圧や出力レベルの正しさは保証しません。[Le Roux et al., SDR — half-baked or well done?](https://arxiv.org/abs/1811.02508)

本実装では有限長の重なり加算で4480サンプルの波形を得て、両端256サンプルずつを除く共通3968サンプル、**0.248秒**を採点します。各chの平均を除去し、参照が非活動のchを事前に判定します。参照が活動するchのdB値を等しく平均し、その中の未定義値を除外しません。今回の32場面では参照の4chすべてが活動しています。

数値安定性のための各波形の正の定数倍は、SI-SDRの尺度不変性により値を変えません。ゼロ推定、ゼロ射影、厳密な尺度一致などで有限のスコアを定義できない場合は、理由付きの `null` にします。再評価したSI-SDRが元の保存値と一致することを確認します。スペクトルのゼロ処理の切り替えでは、この値は変わりません。

## 4. 振幅スペクトル誤差とコヒーレンス

ADEPSが引用するGen-Aの式(5)、(6)を使用します。`b`は参照、`b̂`は推定、`t`はフレーム、`f`は周波数、`c`は係数です。[Gen-A §III-D](https://arxiv.org/html/2501.08047v1#S3.SS4)

```text
S(f) = (1 / (T C)) Σc Σt |20 log10(|b[t,f,c]| / |b̂[t,f,c]|)|

C(f) = (1 / C) Σc {
  |Σt conj(b[t,f,c]) b̂[t,f,c]|²
  / (Σt |b[t,f,c]|² · Σt |b̂[t,f,c]|²)
}
```

`S(f)`は小さいほど良く、`C(f)`は0〜1で大きいほど良い指標です。今回は `T=32, C=4`。コヒーレンスはchごとに時間方向の和を取ってから二乗・除算し、その後chを平均します。chと時間を一括してエネルギー平均する指標ではありません。一定の倍率や一定の位相回転でもコヒーレンスは1になり得ます。

場面内では257周波数を等しく平均し、全体では32場面を等しく平均します。DCとNyquistも含みます。対数グラフの表示軸は1 Hz〜20 kHzですが、実際の非DC点は**31.25 Hz〜8 kHz**です。範囲外の数値を生成せず、DCを対数軸の架空の正周波数へ移しません。

原論文からは、ゼロ・無音処理、振幅floor、厳密なDC/Nyquist扱い、全体の集計詳細まで確定できません。そのため次の2条件を別々に残します。どちらも著者の評価コードと同一と確認したものではありません。

| 設定 | 振幅スペクトル誤差 | コヒーレンス |
|---|---|---|
| `strict`：式をそのまま評価 | 片方が0なら発散、両方0なら未定義 | 参照または推定のch時間ベクトルのエネルギーが0なら未定義 |
| `reference_floor`：感度確認 | その場面の参照FOA全体の最大振幅×`10⁻⁶`を、全方式・両側の振幅に共通適用 | 非ゼロ参照に対するゼロ推定は0。ゼロ参照chは未定義のまま |

`10⁻⁶`は参照ピークから**振幅−120 dB**です。推定ごとのピークを基準にしません。極小値でのアンダーフローを避けるため、floorは対数領域で適用します。全参照が0のときは共通floorを定義できません。

非有限値はJSONの `null`、画面の `—` に変換し、理由を記録します。必要なch・周波数・場面に未定義があれば集計値も未定義とし、都合の悪い項目だけを外して平均しません。有限な周波数点の曲線は残るため、全帯域の平均が `—` でも、どの帯域で値を確認できるかは見られます。

この補助条件で値が有限になっても、復元音が改善したわけではありません。**採点規則を変えた感度確認**です。

## 5. ILD / IC：共通KU100デコーダによる独立の代理評価

原著はNeumann KU100のHRTFとERB帯域を用いたILD・IC誤差を記載していますが、HRTFファイル、デコーダ、帯域設計、引用された聴覚処理の実装を完全には特定していません。今回の処理は、この不足を埋めるために選んだ**独立の代理評価**です。[ADEPS §4](https://arxiv.org/html/2608.24558v3#S4)

### HRTFの出所

- SADIE II、University of York、D1（Neumann KU100）。[公式データベース](https://www.york.ac.uk/sadie-project/database.html)、[データセット論文](https://doi.org/10.3390/app8112029)
- 入力：[D1_48K_24bit_256tap_FIR_SOFA.sofa](https://sofacoustics.org/data/database/sadie/D1_48K_24bit_256tap_FIR_SOFA.sofa)。8,802方向、48 kHz、256tap。配布元で低域拡張、拡散音場EQ、窓処理を施した測定データです。
- 元ファイルSHA-256：`e6c72a84dd947b5ef75438ab96a9c2a32ed10f033472b9c4c11a49aff00a8a31`。
- SOFA内に記載されたApache License 2.0とYorkの帰属を、派生デコーダの出典情報に保持します。原測定データを本実装が測ったものとは表示しません。
- 派生JSONのSHA-256：`0d257cb6f57906bc39de294fcf4c665cecc9c705e8c80816744e7a2a4595a33a`。同じ数値環境で再生成したバイト列の一致を確認しています。`paper-ku100-LICENSE.txt` と `paper-ku100-NOTICE.txt` を同じ公開ディレクトリに同梱します。

派生アセット `public/models/paper-ku100-foa.json` は、方向の球面Voronoi面積を重みにした最小二乗で、実球面調和の1次ACN/N3Dへ近似した周波数別の2耳×4chデコーダです。頭の正面は+X、左は+Y、上は+Zで固定します。参照も推定も同じFOAデコーダへ通し、5次や15次の完全な両耳正解と比較するものではありません。生成時の具体的な変換方法と係数のSHAはアセットに記録します。

方向は等間隔とは限らないため、Voronoiセルごとに異なる面積を重みとして使います。元SOFAの測定距離は1.2 m、両耳は左右±0.09 m、`Data.Delay`は両耳とも0です。変換は48 kHzの時間HRIRをFOAへ最小二乗投影し、そのまま0〜8 kHz、31.25 Hz刻みでDTFTを評価します。16 kHzへリサンプリングしたWAVを中間生成する処理ではありません。最終デコーダのDCと16 kHzのNyquistに相当する8 kHzは実数化します。

既存の左右±45°仮想cardioidによる試聴音はHRTFによる両耳信号ではないため、今回のILD/ICの入力には使いません。

### 帯域と手掛かり

ERB-rate `21.4 log10(1 + 0.00437 f)` 上で100〜8,000 Hzを32等分し、重なりのない矩形のFFT-bin群にします。これはガンマトーンや生理学的な聴覚フィルタバンクではありません。このFFT格子で含まれる最初の実binは125 Hzです。各帯域の中心をグラフの横座標に使い、欠けたFFT点を補間しません。[Glasberg and Moore, 1990](https://doi.org/10.1016/0378-5955(90)90170-T)

左右のSTFTを `L, R` として、まず32フレーム全体で共分散 `C_LL, C_RR, C_LR=mean_t(L conj(R))` を平均します。その後、各帯域のbinを等しく平均します。片側スペクトルのParseval係数倍は使用せず、短い区間全体の定常的な代理値を求めます。

```text
P_L = Σf w_band(f) C_LL(f)
P_R = Σf w_band(f) C_RR(f)
ILD = 10 log10(P_L / P_R)

IC_peak = max_(l = −16…16) {
  Re[Σf w_band(f) C_LR(f) exp(i 2π f l / 16000)] / sqrt(P_L P_R)
}
```

16 kHzの−16〜+16サンプルは**±1 ms**です。ICは符号を残した正規化相関の最大値で、相関の絶対値や振幅二乗コヒーレンスではありません。原始的な相関値は−1〜1、参照と推定の絶対差は0〜2の範囲です。

別の感度値として `ic_signed_zero_lag_error` を保存します。これは同じ相関式の `l=0` を使った符号付きICの絶対誤差で、主表示のlag最大値とは区別します。符号付きゼロ遅延の物理的共分散式はMcCormack et al.の式(36)を参照できますが、同論文のRMSEと今回のMAEも異なります。[McCormack et al., 2022](https://doi.org/10.1109/TASLP.2022.3182857)

各帯域で参照と推定のILD/ICの絶対差を取り、**参照の両耳に正のパワーがある帯域**を全方式共通の対象にして等しく平均します。必要な帯域で推定が無音なら、その方式の全体値を `null` にします。推定に合わせた帯域削除やepsilon floorは行いません。参照が無音の帯域は全方式で対象外にし、有効帯域数とマスクを記録します。

Faller–Merimaaの聴覚モデルは、聴覚末梢フィルタ、神経変換、短い時間窓での処理を含みます。今回のSTFT共分散のlag探索はそれを再現していません。`ic_error`という列名が一致していても、原著のIC実装と等価であることは保証できません。[Faller and Merimaa, 2004](https://doi.org/10.1121/1.1791872)、[Merimaa博士論文 §4.2.2](https://aaltodoc.aalto.fi/bitstreams/39a10ff1-8d84-45d0-863b-81a924d264d8/download)

## 6. 再評価手順と記録

検証済みのKU100デコーダ、元の封印済み入力・推定・評価記録がそろった環境で、リポジトリのルートから実行します。推定NPZを含まない小さな公開CSVだけでは、再採点はできません。

デコーダを再生成する場合は、上記のSHAに一致するSOFAを用意します。デコーダの再生成にはh5pyとSciPyが必要です。生成済みデコーダによる両耳指標自体はNumPyで計算しますが、再採点スクリプト全体には既存の波形評価モジュールが使うSciPyも必要です。追加学習やGPUは不要です。

```sh
.venv-paper/bin/python backend/paper_binaural_metrics.py prepare \
  --sofa work/binaural-research/D1_48K_24bit_256tap_FIR_SOFA.sofa \
  --output public/models/paper-ku100-foa.json
```

```sh
.venv-paper/bin/python scripts/rescore_paper_comparison.py \
  --work work/plus-v1 \
  --output public/models/paper-comparison.json
```

新しい出力は次の2ファイルです。

- `public/models/paper-comparison.json`：`adeps-paper-comparison/1`。元benchmarkのSHA、採点ソースと参照表のSHA、方式・場面・2条件、各指標と曲線、集計、未定義状態、出典を保存します。
- `public/models/paper-comparison.csv`：各場面と全場面平均の5指標を、方式・ゼロ処理の条件ごとに並べます。未定義は空欄です。

元の `work/plus-v1/benchmark.json`、`public/models/plus-benchmark.json`、保存済み音声・推定値、選択ロック、学習重みは更新しません。SI-SDRが元の保存値に一致することを検証し、他の4指標を別の記録に追加します。JSONは変更の追跡と詳しい感度・未定義状態の確認、CSVは比較のための表です。

この追加評価に新しい事前登録済みの仮説検定や信頼区間は付けません。従来の主指標の信頼区間は従来の記録に残り、追加指標へ流用しません。短い音声、単一の配置、4つの話者ペア群という制約を含めて読み取ります。

## English reading guide

The five displayed quantities are SI-SDR, magnitude spectrum error, coefficient magnitude-squared coherence, binaural ILD error, and binaural IC error. Published paper values are source records, while the application’s values are a new **post-hoc** report for already saved estimates. No cross-benchmark gain or victory is inferred.

Gen-A Eqs. (5) and (6) supply the spectral core. The strict profile preserves undefined/infinite outcomes as null rather than discarding channels, bins or scenes. The separate sensitivity profile applies one scene-reference peak × `1e-6` amplitude floor (−120 dB) and assigns zero-estimate MSC=0 only when the reference is nonzero. These extra conventions are not specified by the original paper.

SI-SDR retains the sealed evaluation: common waveform synthesis and 256-sample edge crop, 3968 samples at 16 kHz, per-channel mean removal, then the dB mean over reference-active channels. All four reference channels are active in the present 32 scenes. It is unchanged across the two spectral profiles.

The measured SADIE II D1 KU100 HRTFs are converted to one fixed-head FOA decoder, shared by reference and all methods. The 32 rectangular ERB-rate bin groups and clip-mean, ±1 ms lag-peak correlation are an **independent proxy**, not the authors’ exact HRTF/decoder/auditory implementation. Signed zero-lag IC is retained as a sensitivity result. Scores are not derived from the virtual-cardioid listening previews.

The original paper evaluates WSJ0 and 13 arrays; this report evaluates 32 held-out VCTK scenes using one six-microphone spherical geometry. The paper’s unknown STFT, aggregation and auditory details remain unknown. NRMSE is not one of its table metrics. Different corpora, geometry, duration and conventions preclude an absolute claim of exceeding the original paper.
