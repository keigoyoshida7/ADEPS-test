# ADEPS-test

理想的なAmbisonics音声を学ぶ拡散priorと、仮想マイクの観測からの復元を調べる研究用アプリです。日本語／英語、黒背景・白字・游明朝体、3Dアレイ表示、反復過程の試聴、周波数別の誤差比較に対応します。独立した **ADEPS + α** タブでは、固定した学習済みモデルに方向推定・波形整合・観測整合を加える方式を比較します。

[Web UI](https://keigoyoshida7.github.io/ADEPS-test/?v=0.7.1) · [ADEPS + α の方式と引用](docs/PLUS_METHODS.md) · [評価プロトコル](docs/PLUS_PROTOCOL.md) · [再計算とダウンロード](docs/PLUS_USAGE.md) · [学習記録](public/models/paper-prior-training.json) · [データの出所](docs/PAPER_DATA.md)

## v0.7.1 — 原論文の指標で比較

「ADEPS + α」上部に、原著v3のTable 1–3の引用値と本実装の再評価を追加しました。SI-SDR、振幅スペクトル誤差、MSC、ILD誤差、IC誤差の5列で、全32場面・9方式を表示します。周波数図、場面選択、同じ入力での方式比較、CSV/JSONの保存に対応します。

スペクトル/MSCは引用先Gen-Aの式に従う値と、−120 dBの参照共通floorを使う独自の感度評価を切り替えます。ILD/ICは実測SADIE II KU100 HRTFによる独自ERB代理指標です。**原著と同じ評価コード・音声・アレイ条件ではないため、原著に対する勝敗は判定しません。** 新たな学習や推論はせず、v0.7.0の保存結果を追加採点しています。旧主指標・評価記録は不変です。[式・出典・再評価手順](docs/PAPER_COMPARISON.md)を参照してください。

## v0.7.0 — ADEPS + α

**最終32場面の比較が完了しました。** 主指標の平均複素FOA NRMSEは、調整済みLinear −14.322 dB、現在の独自ADEPS −4.061 dB、調整済み独自ADEPS −8.217 dB、＋αの学習済み補正ON −26.500 dBでした（低いほど良い）。＋α ONはこれら3方式に対して全32場面で改善しました。一方、**学習済み補正OFFが −26.702 dBで最良**で、ONはOFFより全32場面で悪化しました。この改善を拡散モデル単独の効果とは主張しません。平均の改善と未定義を含む補助指標・評価条件は[最終評価レポート](docs/PLUS_RESULTS.md)に掲載しています。原著の公式モデルや実録音に対する優位性は未確認です。

既存の **30,781,344パラメータの学習済みノイズ除去器を固定**したまま、観測から最大2方向を推定する共分散Wiener推定、STFTを同じ波形から得られる形へ戻す投影、既知のアレイ応答Vに合う観測補正を組み合わせます。推論に正解係数や正解方向を渡さず、ニューラル重みを追加学習しません。これは独自の決定的な反復方式で、原論文の厳密な拡散事後サンプリングとは異なります。

比較対象は全9方式です。**初期Linear、調整済みLinear、既知SNRの等方Wiener推定、既存の独自ADEPS、調整済みの独自ADEPS、方向共分散のみ、Linear＋波形整合、ADEPS + α ON、同じα処理で学習済み補正OFF**を同じ入力で比べます。OFFでも整合処理を残し、学習済み除去器を呼ばないことで、その寄与を分けます。ONがOFFより良いとは仮定しません。

設定は既存validationの16場面で選び、新規8話者・32部屋・4話者ペアの最終比較を、設定・コード・重み・データのSHAとともに事前確定します。主指標はDCを含む0–8 kHzの複素FOA誤差で、全32場面を残し、97.5%の話者ペア単位の区間も記録します。6本の理想マイク・半径0.06 m・次数5一致・既知SNR 50 dBという合成条件です。成功条件と結果は区別し、原著の公式モデルや実会場に対する優位性は主張しません。詳細は[方式](docs/PLUS_METHODS.md)と[事前プロトコル](docs/PLUS_PROTOCOL.md)を参照してください。

画面は次の6タブです。

1. **ADEPSの流れ**：理想音声 → 学習 → 仮想観測 → Linear → 拡散復元 → 比較・試聴。
2. **復元・比較**：従来の独自ADEPSの保存例・途中の推定・3D・周波数曲線・試聴とローカル再計算。
3. **ADEPS + α**：9方式の集計と場面別比較、学習済み補正ON/OFF、事前に選んだscene 0000の3D・試聴。
4. **スピーカーで再生**：提供された保存プロジェクトの12ch配置を使う、後段のFOAデコーディング。
5. **論文と実装の範囲**：引用、式、対応点、独自実装、未再現の条件。
6. **用語の解説**：47項目の正式名称、和訳、数式の記号を検索。

## v0.6.0 の学習・評価記録（保存）

以下は旧版で完了した記録です。この結果を見て方式を改良したため、旧testと公開例A/B/Cは現在は既知の診断・開発用データとして扱い、新しい最終判定へ混ぜません。

**30,781,344パラメータのNCSN++M由来U-Net**を独自実装し、HARP由来の室内応答とVCTK音声から得た理想5次Ambisonicsで、**2,000回の重み更新・1,913固有シーンの学習と評価を完了**しました。MPSでの記録上の学習時間は約54.8分です。36複素係数を72実数チャンネルの時間・周波数テンソルとして扱い、学習ターゲットにはマイク配置や応答Vを入れません。重みのSHA-256、学習曲線、全評価値は上記JSONを参照してください。

当時の重み学習で未使用だった16シーンを使うdenoiser単体評価では、10個のノイズ強度のうち無処理より9条件、ガウス縮小より8条件で集約NMSEが改善しました。ガウス縮小との差はσ=1で最大1.836 dB、σ=0.002・80では悪化しました。一方、**旧版で計算・書き出しを完了した3つの音声復元例は、すべて最終NRMSEがLinearより悪化**しました。単体のノイズ除去評価と、観測からの反復復元の成績は分けて確認します。十分な収束や論文と同じ品質は確認できていません。

原著の公式モデルではありません。論文と近いモデル規模は、同じ精度の保証ではありません。VCTKは選択した320発話・16話者の部分集合で、学習用は240発話・12話者です。WSJ0は使用せず、別話者のVCTKで評価します。予定の20,000学習シーンを全て学習済みとは扱いません。ネットワークや前処理の独自選択、データの範囲、失敗を含む評価を公開します。

旧小型モデル、会場のマイク測定・IR解析、再生系のキャリブレーション操作は現在のUIから取り除いています。過去のコード・Maxパッチは履歴と既存ファイルに残っています。

## Webで見る

3つ目の[ADEPS + αタブ](https://keigoyoshida7.github.io/ADEPS-test/?v=0.7.1&tab=plus)は、完成した[最終評価JSON](public/models/plus-benchmark.json)を読み込み、9方式の平均・場面別誤差・周波数曲線を表示します。試聴例は結果を見る前に固定したscene 0000で、良かった例への差し替えは行いません。ファイルが未完成・未公開・不整合なら、その状態を表示して結果を補いません。公開ページでの操作は保存結果の切り替えであり、モデルの再計算ではありません。

[音声と記録のZIP](public/models/plus-example-audio.zip)には、参照＋9方式の4ch FOA WAV、固定cardioidステレオ試聴、出典・ライセンス・設定・評価記録をまとめます。10対象すべてに共通gainを使い、3Dの共分散にも同じgainの2乗を適用します。公開例とCLIの使い分けは[利用手順](docs/PLUS_USAGE.md)を参照してください。

[再計算用入力NPZ](public/models/plus-example-input.npz)は、公開scene 0000と同じマイク観測・V・周波数を保存したもので、ZIPにも同じファイルを含めます。正解係数や正解方向は推論入力に入れません。[CLIの実行手順](docs/PLUS_USAGE.md)で、このファイルを入力に指定します。例JSONの `input_sha256` は観測そのものの識別値、`inference_input_file_sha256` は配布NPZのバイト列の識別値です。

公開Webでは**保存した実際の学習記録と復元例**を閲覧します。「復元・比較」で保存例を選び、「学習済みモデルの計算例を開く」を押します。評価済み学習記録と同じ重みを使い、指定条件に一致する実結果ファイルが公開された例だけを読み込みます。ファイルが未公開・不一致ならエラーを表示し、結果を補いません。途中の推定を選ぶと、3D・指標・試聴対象が切り替わります。拡散OFFでは同じ観測からのLinearを試聴します。

v0.6.0の旧公開例は次の3例です。実際の学習済み重みで計算し、音声と結果を書き出しました。共通のLinear NRMSEは−2.196845 dBです。改善量は「Linearの誤差 − 復元の誤差」で、負の値は悪化を表します。新しい32場面の比較とは別の記録です。

| 例 / Example | 拡散seed / Diffusion seed | 拘束 / Guidance η′ | ステップ / Steps | 最終NRMSE / dB | 改善量 / Δ dB |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 42 | 50 | 150 | −2.089547 | −0.107298 |
| B | 43 | 50 | 150 | −2.053539 | −0.143306 |
| C | 42 | 0 | 150 | −0.329145 | −1.867700 |

共通条件は旧テストシーン0（現在は既知の診断用）、球面6本・半径0.06 m、SNR 50 dB、観測ノイズseed 173927です。A/Bは初期雑音、A/Cは観測への拘束の違いを同じ観測で比較します。Cも観測に依存するwarm startを使うため、観測と無関係な生成ではありません。各例を順に開くと履歴から切り替えられます。選択だけでは計算も表示中の結果の変更も行わず、読み込み後も自動再生しません。

3D音場はFOAの方向別RMS表示です。部屋全体の音圧や、実測された音場の表示ではありません。スピーカーの3D図は別の後段工程として扱います。

周波数の横軸は1 Hz〜20 kHzです。今回の16 kHz音声・FFT512に含まれる非DCの計算点は**31.25 Hz〜8 kHz**で、値がない帯域に曲線を補いません。表示範囲だけで音声の帯域が広がることはありません。

公開例の発話の出典・ライセンス・加工内容は画面とZIPに付記します。試聴用の短区間は約0.248秒で、全比較対象に共通ゲインを適用します。スピーカー出力やMaxへの送信は自動では行いません。

## 設定を変えて復元する

30.8Mモデルの再計算は**ローカルPython/Torch**で実行します。GitHub Pagesは保存結果の閲覧用で、学習やTorchを実行するサーバーではありません。

**ADEPS + αを再計算する場合**は、[infer_plus.py の手順](docs/PLUS_USAGE.md)に従います。`--selection`で事前選択済み設定、`--checkpoint`で同じ重みを指定し、`--no-denoiser`で学習済み補正だけをOFFにできます。入力・重み・設定・コードの識別と、全36係数のNPZ、共通gainのFOA WAV、処理記録を保存します。以下の `infer_paper_prior.py` とローカルUIの操作は、従来のADEPS復元経路です。

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

ADEPS-test is an independent research interface for an array-independent Ambisonics diffusion prior and reconstruction from simulated microphone observations. It provides Japanese/English navigation, array and FOA visualization, saved denoising trajectories, matched-gain listening and frequency-wise comparisons.

### Version 0.7.0: ADEPS + α

The separate third tab compares an independent **observation-derived directional-covariance Wiener initializer, frozen 30.78M denoiser, STFT projections and physical observation corrections**. The weights are unchanged, and reconstruction receives no target coefficients or oracle source directions. This deterministic continuation is not the paper's exact diffusion posterior sampler.

All nine comparators are retained: default Linear, tuned Linear, known-SNR isotropic Wiener estimation, current independent ADEPS, tuned independent ADEPS, spatial covariance alone, Linear plus waveform consistency, ADEPS + α with learned refinement ON, and the same α processing with that refinement OFF. The OFF control retains the consistency steps and performs zero denoiser evaluations; ON is not assumed to be better.

The [precommitted protocol](docs/PLUS_PROTOCOL.md) separates the 16-scene development selection from a fresh final set of 32 rooms, eight speakers and four speaker-pair clusters. It retains every scene and full-band FOA error including DC, with 97.5% paired cluster intervals. Six ideal microphones, a 0.06 m radius, matched order 5 and known synthetic 50 dB SNR define this experiment. Completion and success must be established from the final evaluation record; the protocol is not a performance result. Neither superiority over the original paper nor real-room performance is established by this setup.

GitHub Pages displays precomputed results. The [example ZIP](public/models/plus-example-audio.zip) contains the preselected scene 0000, reference plus all nine methods, aligned FOA and stereo audio under one shared gain, and attribution, configuration and evaluation records. The same [prepared observation NPZ](public/models/plus-example-input.npz) is available separately and inside the ZIP, containing p/V/frequency data without target coefficients or oracle directions. Recompute it locally with [infer_plus.py](docs/PLUS_USAGE.md), including `--no-denoiser` for the learned-contribution control. The [method and citation guide](docs/PLUS_METHODS.md) explains each independent adaptation.

### Historical version 0.6.0 records

Version 0.6.0 uses an independently implemented **30,781,344-parameter NCSN++M-derived U-Net**, trained on ideal order-5 HOA from selected VCTK speech and HARP-derived simulated room responses. Actual training consumption, checkpoint identity and held-out results are recorded in the [model report](public/models/paper-prior-training.json). This is neither the authors' official checkpoint nor a demonstrated reproduction of their quality. VCTK is a subset, and speaker-disjoint VCTK evaluation replaces the paper's WSJ0 evaluation.

The initial training and evaluation run is complete: **2,000 optimizer updates, 1,913 unique training scenes and 54.8 minutes of recorded MPS training**. Denoiser-only evaluation on 16 scenes not used to train those weights improved pooled NMSE over noisy identity at 9/10 noise levels and over Gaussian shrinkage at 8/10. The maximum gain over shrinkage was 1.836 dB at sigma=1; sigma=0.002 and 80 regressed. In contrast, **all three completed v0.6.0 reconstruction examples have worse final NRMSE than Linear**: A −2.089547, B −2.053539 and C −0.329145 dB, against the shared Linear baseline −2.196845 dB. Their error increased by 0.107298, 0.143306 and 1.867700 dB respectively. These observed legacy examples now serve diagnostic/development purposes and are excluded from the new final confirmation set. Standalone denoising and inverse reconstruction are different evaluations; convergence and paper-level quality remain unverified.

The six tabs are **ADEPS workflow → Reconstruct & compare → ADEPS + α → Speaker playback → Paper & implementation → Glossary**. The glossary contains 47 cards with English full names, Japanese meanings and sources. Speaker decoding is a separate downstream illustration using the supplied 12-channel project layout, with channel-order and coordinate conventions documented in that view.

In **Reconstruct & compare**, choose a saved computation and open it. The three legacy choices are A (diffusion seed 42, guidance η′=50), B (seed 43, η′=50) and C (seed 42, η′=0), each with 150 steps. All use the old test scene 0, six microphones on a 0.06 m sphere, SNR 50 dB and observation-noise seed 173927. A/B compare initial-noise choices; A/C compare guidance while holding the observation fixed. C still uses an observation-dependent warm start. Open the examples in turn to compare them through history. These are separate from the new ADEPS + α final-test scene 0000.

All three examples were actually computed and exported with the trained full-size model. The public viewer loads their saved results and verifies the evaluated report, checkpoint and selected conditions; missing or mismatched files produce an error. Selection alone neither computes nor changes the displayed result, and loading does not autoplay. New reconstruction requires the local Torch API and matching checkpoint/data; it does not silently use a smaller browser model.

For inference from the fixed observation alone, obtain `paper-prior-v1.pt`, `report.json` and `array-input.npz` once published in the release, place them under `work/paper-prior-v1/`, and run the `infer_paper_prior.py` command above after installing the Python requirements. This path needs no source corpus, HARP scene regeneration, Node.js or UI server. It writes reconstructed/Linear coefficients to NPZ and an accompanying JSON record. Change `--seed` to 43 for B or `--guidance` to 0 with seed 42 for C, and use distinct output names. Changing virtual microphone geometry through the UI still requires the metadata and corpus restoration described in the [guide](docs/PAPER_PRIOR.md).
