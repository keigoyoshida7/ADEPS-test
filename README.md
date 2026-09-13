# ADEPS-test

理想的なAmbisonics音声を学ぶ拡散priorと、仮想マイクの観測からの復元を調べる研究用アプリです。日本語／英語、黒背景・白字・游明朝体、3Dアレイ表示、反復過程の試聴、Linearとの周波数別比較に対応します。

[Web UI](https://keigoyoshida7.github.io/ADEPS-test/?v=0.6.0) · [学習と評価の記録](public/models/paper-prior-training.json) · [実装と実行方法](docs/PAPER_PRIOR.md) · [データの出所](docs/PAPER_DATA.md)

## v0.6.0

**30,781,344パラメータのNCSN++M由来U-Net**を独自実装し、HARP由来の室内応答とVCTK音声から得た理想5次Ambisonicsで、**2,000回の重み更新・1,913固有シーンの学習と評価を完了**しました。MPSでの記録上の学習時間は約54.8分です。36複素係数を72実数チャンネルの時間・周波数テンソルとして扱い、学習ターゲットにはマイク配置や応答Vを入れません。重みのSHA-256、学習曲線、全評価値は上記JSONを参照してください。

未学習の16シーンを使うdenoiser単体評価では、10個のノイズ強度のうち無処理より9条件、ガウス縮小より8条件で集約NMSEが改善しました。ガウス縮小との差はσ=1で最大1.836 dB、σ=0.002・80では悪化しました。一方、**計算・書き出しを完了した3つの音声復元例は、すべて最終NRMSEがLinearより悪化**しました。単体のノイズ除去評価と、観測からの反復復元の成績は分けて確認します。十分な収束や論文と同じ品質は確認できていません。

原著の公式モデルではありません。論文と近いモデル規模は、同じ精度の保証ではありません。VCTKは選択した320発話・16話者の部分集合で、学習用は240発話・12話者です。WSJ0は使用せず、別話者のVCTKで評価します。予定の20,000学習シーンを全て学習済みとは扱いません。ネットワークや前処理の独自選択、データの範囲、失敗を含む評価を公開します。

画面は次の順です。

1. **ADEPSの流れ**：理想音声 → 学習 → 仮想観測 → Linear → 拡散復元 → 比較・試聴を順番に確認。
2. **復元・比較**：同じ入力のLinearと拡散推定、初期ノイズseed、観測への拘束、途中の推定、3D、ノイズスケジュール、誤差・coherence、WAV・CSV保存。
3. **スピーカーで再生**：提供された保存プロジェクトの12ch配置による後段のFOAデコーディング。位置・チャンネル順・方向別の係数を確認する独立した工程です。
4. **論文と実装の範囲**：引用、式、対応点、独自実装、未再現の条件。
5. **用語の解説**：略語の正式名称、和訳、数式の記号を検索。

旧小型モデル、会場のマイク測定・IR解析、再生系のキャリブレーション操作は現在のUIから取り除いています。過去のコード・Maxパッチは履歴と既存ファイルに残っています。

## Webで見る

公開Webでは**保存した実際の学習記録と復元例**を閲覧します。「復元・比較」で保存例を選び、「学習済みモデルの計算例を開く」を押します。評価済み学習記録と同じ重みを使い、指定条件に一致する実結果ファイルが公開された例だけを読み込みます。ファイルが未公開・不一致ならエラーを表示し、結果を補いません。途中の推定を選ぶと、3D・指標・試聴対象が切り替わります。拡散OFFでは同じ観測からのLinearを試聴します。

実際の学習済み重みで次の3例を計算し、音声と結果を書き出しました。共通のLinear NRMSEは−2.196845 dBです。改善量は「Linearの誤差 − 復元の誤差」で、負の値は悪化を表します。

| 例 / Example | 拡散seed / Diffusion seed | 拘束 / Guidance η′ | ステップ / Steps | 最終NRMSE / dB | 改善量 / Δ dB |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 42 | 50 | 150 | −2.089547 | −0.107298 |
| B | 43 | 50 | 150 | −2.053539 | −0.143306 |
| C | 42 | 0 | 150 | −0.329145 | −1.867700 |

共通条件はテストシーン0、球面6本・半径0.06 m、SNR 50 dB、観測ノイズseed 173927です。A/Bは初期雑音、A/Cは観測への拘束の違いを同じ観測で比較します。Cも観測に依存するwarm startを使うため、観測と無関係な生成ではありません。各例を順に開くと履歴から切り替えられます。選択だけでは計算も表示中の結果の変更も行わず、読み込み後も自動再生しません。

3D音場はFOAの方向別RMS表示です。部屋全体の音圧や、実測された音場の表示ではありません。スピーカーの3D図は別の後段工程として扱います。

周波数の横軸は1 Hz〜20 kHzです。今回の16 kHz音声・FFT512に含まれる非DCの計算点は**31.25 Hz〜8 kHz**で、値がない帯域に曲線を補いません。表示範囲だけで音声の帯域が広がることはありません。

公開例の発話の出典・ライセンス・加工内容は画面とZIPに付記します。試聴用の短区間は約0.248秒で、全比較対象に共通ゲインを適用します。スピーカー出力やMaxへの送信は自動では行いません。

## 設定を変えて復元する

30.8Mモデルの再計算は**ローカルPython/Torch**で実行します。GitHub Pagesは保存結果の閲覧用で、学習やTorchを実行するサーバーではありません。

この作業用PCでは環境・データ・重みを`work/`以下に用意します。別のPCでは[セットアップとチェックポイント](docs/PAPER_PRIOR.md)を参照してください。推論にはPython 3.11以降と評価済みチェックポイント・一致するレポートが必要です。UIで仮想観測を作り直す場合は、Node.js 22.13以降、データ一覧と元音声も使用します。

配布された固定観測`array-input.npz`からの推論だけなら、元音声や室内応答を再生成する必要はありません。重み・レポート・NPZを`work/paper-prior-v1/`へ置き、Python環境を準備して次を実行します。各ファイルは[v0.6.0リリース](https://github.com/keigoyoshida7/ADEPS-test/releases/tag/v0.6.0)への公開後に取得できます。

```sh
python3 -m venv .venv-paper
.venv-paper/bin/python -m pip install -r requirements-paper-training.txt
```

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-paper/bin/python scripts/infer_paper_prior.py \
  --checkpoint work/paper-prior-v1 \
  --input work/paper-prior-v1/array-input.npz \
  --output work/paper-prior-v1/restored-seed42-eta50.npz \
  --steps 150 --guidance 50 --seed 42
```

このコマンドは推論結果のNPZと記録のJSONを保存します。CLIだけならNode.jsやUIサーバーは不要です。`--seed 43`でB、`--seed 42 --guidance 0`でCの条件に変えられます。結果を残すため出力名も変更してください。

**UIでマイク配置などを変える場合**は、[データ復元手順](docs/PAPER_PRIOR.md)でデータ一覧と元音声も用意します。固定NPZだけでは新しい観測を生成できません。準備後、1つ目のターミナルでAPIを起動します。

```sh
npm ci
PYTHONDONTWRITEBYTECODE=1 .venv-paper/bin/python backend/server.py
```

別のターミナルでUIを起動します。

```sh
npm run dev:local
```

[ローカルUI](http://127.0.0.1:5178/?tab=diffusion)でアレイ・ノイズ・seed・拘束・ステップ数を選び「ローカルで復元する」を押します。重みやデータが不足・不一致ならエラーを返し、別モデルで置き換えません。学習と推論は同じ計算資源を使うので、同時に実行せず順番に行います。

## 検証

```sh
npm run typecheck
npm run test:studio
npm run test:numerics
npm run test:max
.venv-paper/bin/python -m unittest discover -s training_tests -v
npm run build
```

数式・ファイル形式のテストと、学習済みモデルの品質評価は別です。後者は重みを固定して未学習のテスト分割で実行し、無処理／ガウス縮小／学習済みdenoiserを同じ入力で比較します。復元例では別途、同じ観測・V・正解でLinearとDPSを比較します。単一例の結果から論文全体や実会場の性能を断定しません。

## 出典

- Milstein, Shlezinger, Rafaely. [Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling](https://arxiv.org/abs/2608.24558v3), 2026. 手法と実験条件の参照元。
- [著者のADEUPSリポジトリ](https://github.com/Amitmils/ADEUPS)。本プロジェクトの独自重みの配布元ではありません。
- [SGMSE NCSN++Mコード](https://github.com/sp-uhh/sgmse/blob/c1399bfb700e96ad49257def4e4edf8fe61e4acc/sgmse/backbones/ncsnpp.py)。構成を理解するための参照元。原著の改変モデルそのものではありません。
- Saini and Peissig. [HARP](https://github.com/whojavumusic/HARP)。固定revisionをローカルに取得し、SH規約等を修正した独自adapterで応答を生成。
- Yamagishi, Veaux, MacDonald. [CSTR VCTK Corpus v0.92](https://doi.org/10.7488/ds/2645), 2019, CC BY 4.0。選択した音声を使用。

## English

ADEPS-test is an independent research interface for an array-independent Ambisonics diffusion prior and reconstruction from simulated microphone observations. It provides Japanese/English navigation, array and FOA visualization, saved denoising trajectories, matched-gain listening and frequency-wise comparison with Linear encoding.

Version 0.6.0 uses an independently implemented **30,781,344-parameter NCSN++M-derived U-Net**, trained on ideal order-5 HOA from selected VCTK speech and HARP-derived simulated room responses. Actual training consumption, checkpoint identity and held-out results are recorded in the [model report](public/models/paper-prior-training.json). This is neither the authors' official checkpoint nor a demonstrated reproduction of their quality. VCTK is a subset, and speaker-disjoint VCTK evaluation replaces the paper's WSJ0 evaluation.

The initial training and evaluation run is complete: **2,000 optimizer updates, 1,913 unique training scenes and 54.8 minutes of recorded MPS training**. Denoiser-only evaluation on 16 held-out scenes improved pooled NMSE over noisy identity at 9/10 noise levels and over Gaussian shrinkage at 8/10. The maximum gain over shrinkage was 1.836 dB at sigma=1; sigma=0.002 and 80 regressed. In contrast, **all three completed reconstruction examples have worse final NRMSE than Linear**: A −2.089547, B −2.053539 and C −0.329145 dB, against the shared Linear baseline −2.196845 dB. Their error increased by 0.107298, 0.143306 and 1.867700 dB respectively. Standalone denoising and inverse reconstruction are different evaluations; convergence and paper-level quality remain unverified.

The five tabs are **ADEPS workflow → Reconstruct & compare → Speaker playback → Paper & implementation → Glossary**. The glossary contains 41 cards with English full names, Japanese meanings and sources. Speaker decoding is a separate downstream illustration using the supplied 12-channel project layout, with channel-order and coordinate conventions documented in that view.

In **Reconstruct & compare**, choose a saved computation and open it. The three configured choices are A (diffusion seed 42, guidance η′=50), B (seed 43, η′=50) and C (seed 42, η′=0), each with 150 steps. All use test scene 0, six microphones on a 0.06 m sphere, SNR 50 dB and observation-noise seed 173927. A/B compare initial-noise choices; A/C compare guidance while holding the observation fixed. C still uses an observation-dependent warm start. Open the examples in turn to compare them through history.

All three examples were actually computed and exported with the trained full-size model. The public viewer loads their saved results and verifies the evaluated report, checkpoint and selected conditions; missing or mismatched files produce an error. Selection alone neither computes nor changes the displayed result, and loading does not autoplay. New reconstruction requires the local Torch API and matching checkpoint/data; it does not silently use a smaller browser model.

For inference from the fixed observation alone, obtain `paper-prior-v1.pt`, `report.json` and `array-input.npz` once published in the release, place them under `work/paper-prior-v1/`, and run the `infer_paper_prior.py` command above after installing the Python requirements. This path needs no source corpus, HARP scene regeneration, Node.js or UI server. It writes reconstructed/Linear coefficients to NPZ and an accompanying JSON record. Change `--seed` to 43 for B or `--guidance` to 0 with seed 42 for C, and use distinct output names. Changing virtual microphone geometry through the UI still requires the metadata and corpus restoration described in the [guide](docs/PAPER_PRIOR.md).
