# 音声priorの実装と評価 / Speech prior: implementation and evaluation

この記録は、音声と室内応答から理想的な5次Ambisonics係数を作り、時間・周波数の文脈を扱う拡散denoiserを独自に学習する取り組みです。モデルIDは`paper-prior-v1`です。原著の公式重みではありません。

モデル名、実パラメータ数、重みの更新回数、処理した固有シーン数、話者、保存重みのSHA-256、評価結果は、[学習・評価JSON](../public/models/paper-prior-training.json)を一次記録とします。予定の学習量を、完了した学習量として扱いません。`status: training`は保存時点の中間記録、`status: evaluated`はその記録の重みで評価を行ったことを示します。プロセスが現在動いていることや、論文と同じ精度に達したことを意味しません。

初回の学習・評価は完了し、記録は`evaluated`です。**30,781,344パラメータ、2,000更新、2,000例、1,913固有シーン**を処理し、記録上の学習時間はMPSで3,286.508秒（54.775分）。評価は学習と話者・シーンを分けたVCTKの16シーン、10種類のσで実施しました。無処理より9/10条件、ガウス縮小より8/10条件で集約NMSEが改善し、後者との差はσ=1で最大**1.8356 dB**です。σ=0.002・80ではガウス縮小より悪化しました。この集計は正解率ではなく、denoiser単体の条件別評価です。別途完了した3例の反復復元は、すべて最終NRMSEがLinearより悪化しています。十分な収束や論文と同じ品質に達したとは確認できていません。

この評価に対応する推論用重みのSHA-256：

```text
0e88c717770453520331d797392794934c6eb167716007b44bb58633e811d7b2
```

## 学習するもの

ターゲットは、マイクの応答Vを適用する前の理想的な5次・36複素係数です。実部と虚部を合わせた72チャンネルを、時間・周波数の構造を保った状態で扱います。マイク配置やVはpriorの学習入力に含めず、復元時の観測モデルとして分けて与えます。

音声コーパス、室内応答生成方法、取得した発話数、話者の分割、学習・検証・テストのシーン数はJSONの`data`に保存します。HARPと音声コーパスは異なる役割を持ちます。HARPは室内応答の生成、音声コーパスは畳み込む音の出典です。一部だけを使用した場合、コーパス全体で学習したとは記載しません。

`unique_scenes_seen`は実際に処理した固有シーン、`examples_seen`は繰り返しを含む例数、`train_scene_pool`は使用できる学習シーンの候補数です。この3つは同じ値とは限りません。更新に使った例数は、固定RMSを求めるために読む学習16例とは分けたカウントです。話者の重複を避けて分割しても、同じコーパスや同じ室内生成規則の範囲の評価であり、未知の会場での性能保証にはなりません。

`compressed_std`は変数名ですが、実際は学習の最初の16例の圧縮後72実数成分から求める非中心化RMS（`sqrt(mean(x²))`）です。平均を引く標準偏差とは区別します。σは各実数成分へ加える雑音の標準偏差で、複素1係数あたりの雑音二乗振幅の期待値は2σ²です。

STFTのサンプルレート、FFT長、hop、フレーム数、正規化、圧縮係数、ノイズ分布は学習条件です。別の周波数グリッドや独立した乱数ベクトルを、同じ音声入力として扱いません。実際の設定は`configuration`と学習コードに従います。

## 評価の読み方

学習曲線は`history`に記録された更新点を結んで表示します。学習損失はEDMの重み付きMSE、`mean((D(x + σε, σ) - x)²) × (σ² + 1) / σ²`です（固定`σ_data=1`）。学習損失の低下は、正解が既知の独立データで改善したこととは別です。

`history.validation_loss`は、検証用4シーンについてσ=0.1・1・10のそれぞれで集約NMSEを求め、その3つのdB値を算術平均したものです。学習MSEと単位が違うため、同じ縦軸には重ねません。

`evaluation`がある場合は、各σで同じ正解と同じノイズ付き入力を3手法に渡し、無処理、ガウス縮小、学習済みpriorの誤差を比較します。誤差は`10 log10(全シーン・72実数成分・周波数・時間の誤差二乗和 / 正解二乗和)`です。正解は振幅圧縮`H(a)`を学習時に求めた固定の非中心化RMS（平均を引かない）で割った座標にあります。ガウス縮小は`noisy / (1 + σ²)`（固定`σ_data=1`）です。この単純処理だけでも雑音が大きい条件では改善し得るため、無処理との差だけで学習の効果を判断しません。dB差は正なら学習済みpriorの誤差が小さく、負なら悪化です。σは圧縮係数上のノイズ強度で、マイクSNR・音圧・録音機器の雑音仕様ではありません。

この単体評価は、Vを使う反復復元、Ambisonics音声の試聴、マイク録音、会場の音場復元と分けます。後段の品質を評価する場合は、同じ入力・応答V・参照・STFT・再生ゲインで線形推定と比較し、使用した重みのSHA-256を記録する必要があります。

## ブラウザーとローカル実行

公開ページは保存した学習・評価記録と音声復元例を閲覧します。ページを開いたことや記録を再読込したことでは、学習やTorch推論は始まりません。旧小型モデルの操作・評価欄は公開UIから取り除いています。

タブは左から「ADEPSの流れ」「復元・比較」「スピーカーで再生」「論文と実装の範囲」「用語の解説」です。学習記録は「ADEPSの流れ」、保存例の選択と復元の履歴は「復元・比較」で確認します。スピーカー向けのデコーディングは復元後の別工程です。

「学習済みモデルの計算例を開く」は、実際に計算した3つの音声例を3D表示・途中経過・線形推定との比較・試聴へ読み込みます。学習記録との`model.id`・`weights_sha256`・パラメータ数の一致に加え、選択したseed・拘束・ステップ数、固定観測の設定、結果に記録された仮想マイク座標、シーン0とデータ一覧SHA、STFT設定を照合します。同じ重みの保存例を既に開いている場合は`input_sha256`の一致も確認します。これは保存結果の閲覧であり、新モデルの再計算ではありません。発話、話者、ファイル、CC BY 4.0の出典・ライセンス、加工内容は例の`audio.attribution`に保存して試聴欄にも表示します。保存された途中段階と最終結果の4ch WAVを含むZIPは保存時に別途取得します。全150更新のすべてに音声が保存されるわけではありません。

次の3条件を実際の学習済み重みで計算し、JSONと音声ZIPの書き出しを完了しました。UIはその保存結果を読み込みます。ファイルが不足・不一致なら明示的にエラーとなり、別の例やモデルへ置き換えません。

| 例 / Example | 拡散seed / Diffusion seed | 拘束 / Guidance η′ | 更新数 / Steps | JSON / ZIPの名前 |
| --- | ---: | ---: | ---: | --- |
| A | 42 | 50 | 150 | `paper-prior-example` |
| B | 43 | 50 | 150 | `paper-prior-seed43` |
| C | 42 | 0 | 150 | `paper-prior-eta0` |

共通のLinear NRMSEは**−2.196845 dB**。最終復元はA **−2.089547 dB**、B **−2.053539 dB**、C **−0.329145 dB**で、誤差はそれぞれ0.107298・0.143306・1.867700 dB増えました。改善量「Linear − 復元」はすべて負です。denoiserがガウス縮小より8/10条件で良かったことは、この反復復元がLinearを上回ることを保証しません。

3例で一致した観測入力のSHA-256：`4b81bd6843b9af3521fda8b340a19b4879ba35b33e3fea583aa9cb69f2f9b135`。

共通条件はテストシーン0、球面6本・半径0.06 m、SNR 50 dB、観測ノイズseed 173927です。公開先は`public/models/`の各`.json`と`.zip`。A/Bでは拡散の初期雑音だけ、A/Cでは観測への拘束だけを変えます。Cも観測に依存するwarm startから始めます。順番に開くと直近6件の履歴から比較でき、選択だけでは表示中の結果は変わりません。差が見えることと、復元精度が良くなることは別で、同じ正解・Linearとの指標や試聴で確認します。

設定を変えた復元はローカルTorch用の`/api/paper-studio`で実行します。公開Webの再計算ボタンは無効で、[ローカル画面](http://127.0.0.1:5178/)へ案内します。単にリンクを開くだけでは計算環境は起動しません。評価済みの学習記録、チェックポイント、データ一覧、VCTKファイルが必要です。標準の配置は6素子・半径6 cm、観測SNR 50 dB、推論150ステップ。マイク本数・配置・半径・SNR・観測ノイズseed・拡散seed・拘束・ステップ数を変更できます。音声・部屋はテスト分割の固定シーン0で、観測seedだけで音源や部屋は変わりません。

公開例とローカル結果は、同じ表示・途中経過・線形比較・試聴で扱います。設定変更だけでは保存結果を再計算しません。拘束η′=0でも初期状態は観測を使ったwarm startなので、観測から完全に独立した生成ではありません。復元環境の起動は下記の「ローカル画面を起動する」を参照してください。JSONの`artifacts.command`は学習再開用のコマンド例で、復元APIの起動コマンドではありません。重みがない場合・記録とSHAが合わない場合はエラーを表示し、別モデルで代用しません。

### 固定観測から推論する（元音声の復元なし）

配布予定の4つのファイルは`paper-prior-v1.pt`、`report.json`、`array-input.npz`、`paper-data-metadata.zip`です。固定した観測からの推論には最初の3つを使用します。[v0.6.0リリース](https://github.com/keigoyoshida7/ADEPS-test/releases/tag/v0.6.0)への公開後、重みとレポート、観測NPZを`work/paper-prior-v1/`へ置いてください。NPZに観測信号p、応答V、STFTの規約・設定が含まれるため、VCTK原音声、HARPコード、データ一覧の復元は不要です。

リポジトリのソースとPython環境（`requirements-paper-training.txt`）を用意し、次を実行します。CLI推論ではNode.jsやAPIサーバーは使いません。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-paper/bin/python scripts/infer_paper_prior.py \
  --checkpoint work/paper-prior-v1 \
  --input work/paper-prior-v1/array-input.npz \
  --output work/paper-prior-v1/restored-seed42-eta50.npz \
  --steps 150 --guidance 50 --seed 42
```

同じ入力でBを計算するには`--seed 43`、Cには`--seed 42 --guidance 0`を使い、出力名も変えます。結果NPZには5次の復元係数と同じ観測のLinear係数、同名JSONには推論記録・入力のSHAが保存されます。このコマンドはWebUI用の保存例JSONや試聴WAVを直接生成するものではありません。NPZ内のアレイと観測は固定なので、本数・配置・半径・観測雑音を変えた仮想テストには次のデータ復元が必要です。

### 別のPCで仮想観測を作り直す

[v0.6.0リリース](https://github.com/keigoyoshida7/ADEPS-test/releases/tag/v0.6.0)に公開された`paper-prior-v1.pt`（推論用重み）、`report.json`（その重みの学習・評価記録）、`paper-data-metadata.zip`（3つのデータ一覧）が揃ってから実行します。リリースや添付物が未公開の場合は取得できません。VCTK原音声やHARPコードはこのZIPに含めず、専用コマンドで元の公式配布先から取得します。

環境を準備してから、重みとレポートを`work/paper-prior-v1/`へ、データ一覧ZIPを同じ場所へ置きます。`work/paper-data/`がまだ存在しない新しい環境で実行します。

```sh
.venv-paper/bin/python scripts/restore_paper_data.py \
  --metadata work/paper-prior-v1/paper-data-metadata.zip \
  --report work/paper-prior-v1/report.json \
  --destination work/paper-data \
  --metadata-sha256 4b75cc98945b2c8a9d31fb2817228e105a3764212a7b90eb0488d76db518bfe0
```

約3.06 MBの一覧ZIPから元の320発話を取得し、すべてのファイルSHAを照合します。VCTKの約11.7 GBの全体ZIPはダウンロードしません。空でない既存データフォルダーは上書きしません。取得結果の転送量などで元の一覧を書き換えず、チェックポイントと同じ一覧をバイト単位で保持します。公開レポートに記録した3つの学習ソースSHAも照合するため、対応するv0.6.0のソースを使ってください。

取得した厳密な復元フォルダーは、同じコマンドへ`--verify-only`を付けて通信なしで照合できます。追加の手作業ファイルやsymlinkを含む場合は、完全一致ではないとして報告します。HARPの読み込みで生成される`__pycache__`も追加ファイルとして検出しますが、それだけでコーパスの破損を意味しません。学習・推論の起動時に`PYTHONDONTWRITEBYTECODE=1`を付けると、このキャッシュの新規生成を防げます。チェックポイントの読み込み時にも重みSHAを検証します。PythonやTorchのバージョン・計算デバイスによる差があるため、別PCの再計算をビット単位で同一とは保証しません。

`training-state.pt`はoptimizer・乱数状態を含む学習再開用で、推論用重みとは別です。この作業用PCに保存します。配布する推論用重みだけでは`--resume`できません。最初からの学習は`train_paper_prior.py --manifest ... --output ... --steps ...`で行います。`--evaluate-only`は最終重みと一致したレポートが揃ったディレクトリにだけ使用してください。

### ローカル画面を起動する

リポジトリのルートで、[学習データの準備](PAPER_DATA.md)とチェックポイント・評価済みレポートの配置を済ませます。既定の重みは`work/paper-prior-v1/paper-prior-v1.pt`、レポートは同じディレクトリの`report.json`、データ一覧は`work/paper-data/scene-manifest.json`です。APIは一覧SHAと重みSHAを照合します。UI用の`public/models/paper-prior-training.json`も同じ評価済みレポートに揃えます。

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-paper/bin/python backend/server.py
```

別のターミナルで：

```sh
npm run dev:local
```

[http://127.0.0.1:5178/](http://127.0.0.1:5178/)の「復元・比較」で「ローカルで復元する」を選びます。Python環境には`requirements-paper-training.txt`の依存関係が必要です。別の配置先を使う場合はAPI起動時の`ADEPS_PAPER_CHECKPOINT`と`ADEPS_PAPER_MANIFEST`で指定できます。学習と大規模モデルの推論を同時に走らせるとメモリを共有するため、学習を終えてから再計算します。

## 論文との対応

[ADEPS v3 §3–4](https://arxiv.org/html/2608.24558v3#S3)の、アレイと独立した高次Ambisonics prior、複素係数の振幅圧縮、EDM型ノイズ除去、観測整合を使う拡散復元を参照します。論文は30.8MパラメータのNCSN++Mを基にしたモデル、HARPによる室内応答、学習にVCTK、評価にWSJ0、学習20,000・評価1,000シーンを記載しています。[ADEPS §4](https://arxiv.org/html/2608.24558v3#S4)

今回の実装で揃えた条件はJSONの`paper.matched`、異なる条件は`paper.differences`に記録します。近いパラメータ数は精度の同等性を示しません。ネットワークの細部、学習量、データの分割・範囲、ノイズ分布、前処理、評価条件が違えば、スコアを直接引き算して論文を上回ったとは判断できません。

[著者の公開リポジトリ](https://github.com/Amitmils/ADEUPS)は別の公開先です。本プロジェクトの独自チェックポイントを著者のモデルとして扱いません。

---

## English

This is an independent speech and time–frequency diffusion prior named `paper-prior-v1`. It is not the authors' official checkpoint. The [training/evaluation JSON](../public/models/paper-prior-training.json) records the actual model ID, parameter count, optimizer updates, unique scenes processed, speakers, checkpoint SHA-256 and scores. Planned work is not reported as completed work. `training` identifies an intermediate saved record; `evaluated` means the recorded checkpoint was evaluated, not that paper-level performance was reproduced.

The first training/evaluation run is complete and recorded as `evaluated`: **30,781,344 parameters, 2,000 optimizer updates, 2,000 examples and 1,913 unique training scenes**, with 3,286.508 seconds (54.775 minutes) of MPS training. Across ten noise levels on 16 speaker- and scene-held-out VCTK examples, the denoiser improved pooled NMSE over noisy identity at 9/10 levels and Gaussian shrinkage at 8/10. The best gain over shrinkage was **1.8356 dB at sigma=1**; sigma=0.002 and 80 regressed. These counts are not an accuracy percentage. All three separately completed inverse-reconstruction examples have worse final NRMSE than Linear. Convergence and paper-level quality remain unverified. The evaluated checkpoint SHA-256 is shown above.

Training targets are ideal order-5, 36-complex-channel Ambisonics coefficients before applying a microphone response V. The 72 real/imaginary channels retain their time–frequency organization. Array geometry and V are not inputs to prior training; they belong to the reconstruction observation model. HARP supplies room-response generation and the speech corpus supplies source audio. Corpus subsets, actual downloads and train/validation/test speakers must be identified separately.

The JSON distinguishes unique scenes processed, examples processed including repeats, and the available training-scene pool. Speaker-disjoint evaluation still uses the declared corpus and acoustic-generation family; it does not establish performance in unseen venues. Sample rate, FFT, hop, frames, normalization and noise settings are part of the model's input contract. The key `compressed_std` stores uncentered RMS, `sqrt(mean(x²))`, over 72 compressed real coordinates from the first 16 training examples; it does not subtract the mean. Sigma is noise standard deviation per real coordinate, so expected squared noise magnitude per complex coefficient is 2 sigma².

Recorded training loss is EDM-weighted MSE with fixed `sigma_data=1`. Validation history instead reports an arithmetic mean of three pooled NMSE values in dB, using four validation scenes at sigma 0.1, 1 and 10. These different units are plotted separately. Neither a training loss nor its decline is held-out accuracy.

When available, denoising evaluation compares unchanged noisy coefficients, Gaussian shrinkage and the trained prior on the same clean targets and corrupted input at each sigma. NMSE is `10 log10(total squared error / total clean energy)`, pooling scenes, 72 real coordinates, frequency and time in the normalized compressed domain. Gaussian shrinkage is `noisy / (1 + sigma²)`. Positive dB differences favor the trained prior; negative differences indicate regression. Sigma describes noise in compressed coefficient coordinates, not microphone SNR or SPL. Denoiser-only results do not establish iterative inverse-problem, listening or real-room performance.

The public page displays saved training/evaluation records and computed reconstruction examples. Loading or refreshing it does not execute Torch. The older small-model controls and evaluation panel have been removed from the public interface.

The tabs run left to right: **ADEPS workflow → Reconstruct & compare → Speaker playback → Paper & implementation → Glossary**. The workflow shows the training record; Reconstruct & compare selects saved computations and keeps run history. Speaker decoding is a separate downstream operation.

“Open the trained model’s computed example” loads one of the three actual computations: its saved trajectory, 3D representation, linear baseline and audio. The loader checks model ID, checkpoint SHA, parameter count, the selected configuration, recorded virtual-microphone coordinates, test scene 0, manifest SHA and STFT settings. If another example from the same checkpoint is already loaded, its input SHA must also match. Speech source, speaker/file IDs, CC BY 4.0 attribution and processing appear in `audio.attribution` and with the player. The separate ZIP is fetched on download and contains 4-channel WAVs for saved stages, not necessarily every one of the 150 updates.

Three saved-example choices are configured: A (diffusion seed 42, guidance η′=50), B (seed 43, η′=50) and C (seed 42, η′=0), all with 150 steps. Their filenames are `paper-prior-example`, `paper-prior-seed43` and `paper-prior-eta0`, each with `.json` and `.zip` in `public/models/`. All hold test scene 0, six microphones on a 0.06 m sphere, SNR 50 dB and observation-noise seed 173927 fixed. A/B compare initial sampling noise; A/C compare guidance. C still uses an observation-dependent warm start. Open examples in turn to compare them through the latest-six-run history. A difference between outputs does not itself mean higher reconstruction accuracy.

All three examples were computed with the trained full-size model and exported to JSON and audio ZIP. Their shared Linear NRMSE is **−2.196845 dB**; final reconstruction NRMSE is A **−2.089547**, B **−2.053539** and C **−0.329145 dB**. Error therefore increased by 0.107298, 0.143306 and 1.867700 dB respectively. Improvement defined as Linear error minus reconstructed error is negative for every case. The common observation SHA-256 is recorded above. Beating Gaussian shrinkage at 8/10 denoising levels does not guarantee beating Linear in iterative reconstruction.

The public viewer reads these saved results; missing or mismatched files produce an error instead of substitute results. Selection alone does not change the displayed result, and opening a saved example neither reruns the model nor autoplays it.

New reconstruction with changed settings runs in local Torch via `/api/paper-studio`. Public-web recomputation is disabled and links to the [local interface](http://127.0.0.1:5178/); opening this link does not start the environment. An evaluated report, checkpoint, matching data manifest and VCTK files are required. Defaults are six sensors, 6 cm radius, 50 dB observation SNR and 150 inference steps. Controls change the microphone count, geometry, radius, SNR, observation-noise seed, diffusion seed, guidance and step count. Speech and room conditions remain fixed to test scene 0; the observation seed changes only observation noise.

Loaded and newly computed full-size results share the trajectory, linear comparison and audio viewer. Editing settings does not change a saved result. Guidance eta-prime=0 still uses an observation-dependent warm start. Use the server and UI startup commands above for reconstruction. The JSON field `artifacts.command` is a training-resumption example, not the command to start the reconstruction API. Missing or mismatched checkpoints produce an error; no alternative model is substituted.

### Infer from the prepared observation without restoring the corpus

The four planned release assets are `paper-prior-v1.pt`, `report.json`, `array-input.npz` and `paper-data-metadata.zip`. For fixed-observation inference, download only the first three once published and place them under `work/paper-prior-v1/`. With the matching repository source and Python requirements installed, run:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-paper/bin/python scripts/infer_paper_prior.py \
  --checkpoint work/paper-prior-v1 \
  --input work/paper-prior-v1/array-input.npz \
  --output work/paper-prior-v1/restored-seed42-eta50.npz \
  --steps 150 --guidance 50 --seed 42
```

The NPZ contains the observation p, array response V and STFT metadata, so this route requires no source corpus, HARP source retrieval or scene regeneration. It also needs no Node.js or API server. Use seed 43 for B, or seed 42 with guidance 0 for C; change output names to preserve each result. Output NPZ contains full order-5 reconstructed and same-input Linear coefficients; its accompanying JSON records inference and input identity. This command does not directly export the browser's saved-example format or listening WAVs. The prepared observation stays fixed. Changing array geometry or measurement-noise settings through the UI still requires corpus/metadata restoration, as described below.

### Restore data for new virtual observations

The implementation references [ADEPS §3–4](https://arxiv.org/html/2608.24558v3#S3). The paper describes a 30.8M-parameter NCSN++M-based backbone, HARP room responses, VCTK for training, WSJ0 for evaluation, and 20,000 training / 1,000 evaluation scenes. Actual aligned conditions and differences are recorded in `paper.matched` and `paper.differences`. Similar model size does not demonstrate equal or better accuracy; direct comparison requires matching data, preprocessing, model details and metrics. The [authors' repository](https://github.com/Amitmils/ADEUPS) remains distinct from this implementation.

To restore this exact experiment on another computer, first obtain inference weights, `report.json` and `paper-data-metadata.zip` once all are published in the [v0.6.0 release](https://github.com/keigoyoshida7/ADEPS-test/releases/tag/v0.6.0). Unpublished assets cannot yet be retrieved. Run the restoration command above with the matching source checkout. It retrieves only the selected official audio members and pinned HARP source, verifies every payload SHA and preserves the original metadata bytes. A nonempty destination is not overwritten; `--verify-only` performs an offline exact-tree check. Generated `__pycache__` files also count as extras, which alone does not indicate corrupted corpus files. Prefix training and inference launches with `PYTHONDONTWRITEBYTECODE=1` to avoid creating them. Inference weights do not include optimizer/RNG state and cannot alone resume training. Matching random state does not guarantee bitwise identity across different library versions and devices.
