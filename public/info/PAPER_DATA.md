# 音声と室内応答から学ぶためのデータ準備 / Speech and room-response data

このページは `scripts/paper_data.py` の出所・取得方法・生成方法を記録します。データを用意したことと、その全量で学習・評価したことは別です。実際に消費した話者・音声・シーン数は、各学習実行のログで確認してください。既存の `tiny-spatial-v1` の学習データが後からVCTKに変わるわけではありません。

This document describes data preparation, not proof that a model trained on the entire planned dataset. Consult each training run's record for the scenes and audio actually consumed. Preparing VCTK does not change the historical training provenance of `tiny-spatial-v1`.

## 出所 / Sources

| 項目 / Item | 論文 / Paper | この準備コード / This preparation code |
| --- | --- | --- |
| 室内応答 / Room responses | HARPによる理想Ambisonics ARIR | HARP v1クラスを基にした明示的な修正adapterとPyroomacoustics ISM。元の生成スクリプトをそのまま実行する方式ではない / Explicit corrected HARP-v1 class adapter and Pyroomacoustics ISM, not the unchanged upstream generation script |
| 学習音声 / Training speech | VCTK | 公式VCTK 0.92から選択したmic2 FLAC / Selected mic2 FLAC files from official VCTK 0.92 |
| 評価音声 / Evaluation speech | WSJ0 | WSJ0は未所有・未取得。話者を分離したVCTKを試走用に使用 / WSJ0 is not owned or downloaded; held-out VCTK is used for pilot validation and tests |
| シーン数 / Scene counts | 学習20,000、評価1,000 | 既定の計画は学習20,000、検証100、テスト100。manifestは計画で、全シーンの生成・学習完了を意味しない / Default manifest plans 20,000/100/100 scenes; this is not a completed training count |

論文のデータ構成と条件の出典は [ADEPS v3, §4](https://arxiv.org/html/2608.24558v3#S4)。HARPは [Saini and Peissig, HARP公式コード](https://github.com/whojavumusic/HARP) の v1 を参照し、commit `e4408f8a849c3c1906ee53e44606945e54b0af46` に固定しています。

The paper's data and room conditions are documented in [ADEPS v3, §4](https://arxiv.org/html/2608.24558v3#S4). HARP upstream is [Saini and Peissig's official repository](https://github.com/whojavumusic/HARP), pinned to the commit above.

## VCTKのライセンスと部分取得 / VCTK licensing and bounded retrieval

公式資料は [VCTK 0.92 / DOI 10.7488/ds/2645](https://doi.org/10.7488/ds/2645)、[大学の配布ページ](https://datashare.ed.ac.uk/handle/10283/3443)、[README](https://datashare.ed.ac.uk/server/api/core/bitstreams/bb7edd96-5d96-4c0e-8989-1e45597e7b72/content)、[添付ライセンス](https://datashare.ed.ac.uk/server/api/core/bitstreams/956a1688-0b59-428c-8a2f-10837433dde3/content)。READMEとライセンスは **Creative Commons Attribution 4.0 International (CC BY 4.0)** を指定しています。著者名、出典、ライセンスと変更の表示を保持します。コードはREADMEとライセンスもデータと同じ場所へ保存します。

The official README and attached license specify **CC BY 4.0**. Preserve attribution, the source and license, and identify changes. The preparation script saves both documents beside the data. Source attribution: Junichi Yamagishi, Christophe Veaux and Kirsten MacDonald (2019), *CSTR VCTK Corpus: English Multi-speaker Corpus for CSTR Voice Cloning Toolkit (version 0.92)*, University of Edinburgh, CSTR, DOI 10.7488/ds/2645.

2026-09-13の公式APIで確認したZIPサイズは **11,747,302,977 bytes**。全体を取得・展開する方法は使いません。HTTP RangeでZIP64の中央目次と選択メンバーだけ取得します。サーバーがRangeを無視してHTTP 200を返した場合は、本文を読む前に停止します。全体取得へのフォールバックはありません。

The official archive is **11,747,302,977 bytes**, as checked on 2026-09-13. Only ZIP64 metadata and selected members are retrieved using HTTP Range. An HTTP 200 response is rejected before its body is read; there is no full-download fallback. Every response is checked for the requested range, total size and unchanged ETag. This DSpace endpoint returned HTTP 416 for conditional `If-Match` range requests, so identity is checked from the response instead.

既定の選択は学習12話者・検証2話者・テスト2話者、各20発話で **320 FLAC**。確認した計画では圧縮メンバー39,503,776 bytes、展開39,557,123 bytes、目次の転送13,017,760 bytesです。選択seedは17391。全話者・全発話を取得した状態ではありません。p280とp315はmic2収録上の問題に合わせ除外しています。

The initial subset is **320 FLAC files**, with 12 training, 2 validation and 2 test speakers, 20 utterances each. The reviewed plan totals 39,503,776 compressed-member bytes and 39,557,123 extracted bytes; directory retrieval used 13,017,760 bytes. Selection seed: 17391. This is a subset, not the full corpus. Speakers p280 and p315 are excluded because the official documentation notes mic2 recording issues.

**取得完了 / Retrieval completed, 2026-09-13:** 全320ファイルのCRC・サイズ・SHA-256・48 kHz mono形式を確認。音声合計18.01分、取得コマンドの実転送53,832,256 bytes（目次・read-ahead込み）。別途実行した取得前planの目次転送や小さな出所文書は、この53.8 MBには含みません。ZIP全体は保存していません。

All 320 selected files were retrieved and checked. They contain 18.01 minutes of speech in total. The acquisition command transferred 53,832,256 bytes, including directory reads and bounded read-ahead; earlier planning requests and small source documents are separate. The complete ZIP was not saved.

| Split | Speakers | Files | Speech minutes | Speaker IDs |
| --- | ---: | ---: | ---: | --- |
| Train | 12 | 240 | 13.5226 | p339, p330, p279, p297, p264, p305, p374, p271, p246, p277, p304, p351 |
| Validation | 2 | 40 | 2.1264 | p261, p237 |
| Test | 2 | 40 | 2.3608 | p300, p292 |

取得した元のFLACコーパスは公開アプリへ同梱しません。公開する短い加工済み復元例には、話者・発話・出典・CC BY 4.0・加工内容を付記します。既定の保存先 `work/paper-data/` はGitで除外されます。`--data-dir /absolute/path` で外部ディスク等へ変更できます。取得上限は既定500 MB、取得前に少なくとも2 GBの空きを残す検査をします。上流HARPコードは同ディレクトリの `upstream/HARP/` に保存し、Gitへ含めません。固定commitのツリーにLICENSEファイルは見当たりませんでした。リポジトリが公開されていることを、コード再配布の包括的な許諾とは扱っていません。

Original FLAC corpus files and downloaded HARP source are not included in the public app or Git repository. Short processed reconstruction previews are published separately with speaker/file IDs, source attribution, CC BY 4.0 and a description of changes. The default `work/paper-data/` is ignored by Git; `--data-dir` may point to an external disk. Retrieval is capped at 500 MB by default, with at least 2 GB free disk space retained. No LICENSE file was found in the pinned HARP tree; public availability is not represented as an unrestricted redistribution license.

## 実行 / Commands

Use the environment containing NumPy, SciPy, SoundFile, requests and Pyroomacoustics. The local pilot uses `.venv-paper/bin/python` with Pyroomacoustics 0.9.0.

```sh
# Metadata only; inspect the proposed speakers and byte counts before fetching.
.venv-paper/bin/python scripts/paper_data.py plan

# Only the members in subset-plan.json, with CRC, size and SHA-256 records.
.venv-paper/bin/python scripts/paper_data.py fetch --max-mb 500

# Generate lightweight scene specifications; do not render 20,000 audio files.
.venv-paper/bin/python scripts/paper_data.py manifest

# Render one real VCTK + simulated-ARIR target and inspect its runtime/metadata.
.venv-paper/bin/python scripts/paper_data.py smoke
```

各FLACはZIP中央目次のサイズ・CRC32と照合し、取得後にSHA-256、48 kHz・monoであること、フレーム数を記録します。部分取得なので **ZIP全体のSHA-256を検証したとは記載しません**。上流のETag/サイズと各メンバーCRCが転送検査、各ファイルSHAが取得後の内容識別です。再実行ではローカルファイルのサイズ・CRCが一致すれば音声を再取得しません。

Each FLAC is checked against its central-directory size and CRC32, and its SHA-256, sample rate, channel count and duration are recorded. **The full archive SHA-256 is not verified by a partial download.** ETag/size and member CRCs check transport consistency; per-file SHA-256 identifies the retrieved content. Valid local members can be reused on retry.

## HARP adapterと理想ターゲット / HARP adapter and ideal targets

上流の [v1/Generate.py](https://github.com/whojavumusic/HARP/blob/e4408f8a849c3c1906ee53e44606945e54b0af46/v1/Generate.py) は `create_ambisonic_array(order, sample_rate)`、`simulate_room(...)` を提供し、SH指向性を持つほぼ同一点の素子からARIRを計算します。[v1/SphericalHarmonic.py](https://github.com/whojavumusic/HARP/blob/e4408f8a849c3c1906ee53e44606945e54b0af46/v1/SphericalHarmonic.py) の応答を、そのまま本実装のACN/N3Dとして扱うことはできません。

The upstream API creates nearly colocated spherical-harmonic receivers and computes image-source RIRs. Its raw directivity output is not used as if it already matched this implementation's ACN/N3D convention. The adapter loads the pinned upstream `SphericalHarmonicDirectivity` class as its base and explicitly replaces its response and old initialization/API behavior.

明示的な変更点 / Explicit changes:

- **正規化と符号 / Normalization and signs:** real ACN/N3D、`Y00=1`、FOAの並びは `W,Y,Z,X`、一次応答は `[1, √3 y, √3 z, √3 x]`。負mを含め解析的なSH式で定義します。上流の一律0.5倍や負方位角の一括+πは適用しません。
- **受音位置 / Receiver position:** 全36係数を厳密に同一点で取得。実マイク配置・筐体・Vを入れない、アレイに依存しない5次ターゲットです。これは36本の実マイク録音ではありません。
- **部屋 / Rooms:** 寸法 `[6,10] × [6,10] × [2,3] m`、目標T60 `[0.1,0.4] s`、受音点の水平位置は部屋中央の1 m × 1 m内。1–2音源を0.8–1.5 mに配置し、壁外になる候補は再生成。すべての条件をmanifestへ記録します。
- **反射 / Reflections:** Pyroomacousticsの `inverse_sabine` と同じ、少なくとも `c × T60` を覆う幾何学条件で推奨ISM次数を求め、既定では切り詰めません。材料は一様の周波数非依存吸音、空気吸収とray tracingは無効。元のHARP v1の材料抽選・固定30次・波形ピーク正規化とは異なります。
- **吸音率 / Absorption:** Sabineの初期推定が1を超える短い目標T60では、Eyring式 `α=1−exp(−αSabine)` で初期化。その後、同じ部屋の単一受音点の無指向性RIRでRT30外挿を測り、最大8回の二分探索で吸音率を調整します。全音源の平均が目標の5%以内になれば終了。これは本adapterの独自選択で、論文の非公開生成設定との一致を意味しません。全trialの吸音率・測定値をmetadataへ記録します。
- **残響時間 / Decay:** 目標T60は実現値の保証ではありません。W応答の30 dB減衰から外挿したRT60推定を別に記録します。`--max-image-order` を明示した場合は推奨次数と切り詰めの有無を記録し、無断で同等条件と扱いません。
- **波形 / Waveform:** 48 kHz VCTKを16 kHzへpolyphase resamplingし、各音源を各ARIRと畳み込みます。長いRIRの無音末尾だけを選ぶcropを避け、極小エネルギー窓の再選択も記録します。
- **STFT:** Hann、16 kHz、FFT512、hop128、32 frames、paddingなしの短い区間。これはローカル試走用の独自設定です。論文の学習区間・ネットワーク文脈と同一だとは記載しません。

The generated target is clean, array independent HOA. Neither microphone-array recordings nor an encoding matrix V are used to generate the prior's target. Device-specific forward models belong in the subsequent inverse-problem evaluation. Correct source provenance alone does not establish reproduction of the paper's model, full speech distribution, rendering or reported metrics.

## Python API

```python
from scripts.paper_data import SceneDataset

dataset = SceneDataset(
    "work/paper-data/scene-manifest.json",
    split="train",                  # train / validation / test
    sample_rate=16000,
    n_fft=512, hop=128, frames=32,
    rir_cache_size=8,
    max_image_order=None,           # c*T60 spatial coverage recommendation
)
sample = dataset[0]
clean = sample["clean_stft"]        # np.complex64, shape [36, 257, 32]
metadata = sample["metadata"]
```

`clean_stft` は未圧縮・未正規化です。論文の圧縮 `H(z)=3 |z|^0.67 exp(j arg(z))` と学習時の正規化はtrainer側で明示してください。係数を実部・虚部に分けると72実座標になります。波形や全STFTをディスクへ保存せず、必要なsceneのみ生成します。小容量PCではDataLoaderの `num_workers=0` を使用し、キャッシュを制限してください。

The dataset returns uncompressed, unnormalized complex targets. Apply and record compression and normalization in the trainer. A 72-real-coordinate tensor is obtained by splitting real and imaginary parts. Room targets are generated on demand rather than storing every waveform or STFT. Use zero data-loader workers and a bounded RIR cache on small-memory machines.

## ローカル確認 / Local checks

2026-09-13に、全36係数を独立したSciPy `sph_harm_y` による実ACN/N3Dと128方向で照合し、相対・絶対誤差1e−12以内で一致しました。さらに6方向の直接音RIRのch比をACN/N3D基準と比較し、絶対誤差2e−6以内を確認しました。

An actual VCTK file convolved with the ideal ARIR produced finite `complex64[36,257,32]` coefficients in an initial 1.14-second smoke run. These runtime figures include local setup and are not throughput guarantees. Absorption calibration was then checked on both an ordinary scene and a short-T60 scene where unmodified `inverse_sabine` fails. For the first scene, the target was 0.1938 s and the resulting W-response RT30 extrapolation was 0.1876 s; the full recommended image order 25 was retained. This is evidence for the adapter's operation, not a trained-model quality result.

正式な20,000/100/100シーンmanifestの `train-000000` でも、有限な `[36,257,32]` ターゲットの生成を1.254秒で確認しました。RIRキャッシュを無効にして同じ実VCTKシーンを2回生成したところ、STFTはビット単位で一致し、metadataも一致しました。最初の部屋の吸音率校正は6試行で、目標とW実現値の差は約−3.2%。短いT60の確認例は3試行で、2音源のW減衰推定が0.1310/0.1186秒、目標0.1189秒に対して平均約+5.0%でした。これらは確認例で、20,200シーンすべてを描画・検査した集計ではありません。

The final manifest passed speaker-disjointness, unique scene-seed and manifest-hash checks. The following identities describe the initial prepared data and frozen generator used when training began:

| Record | SHA-256 |
| --- | --- |
| `scripts/paper_data.py` | `476e564b3ce7125cbdfac8f066e19e0ca0a46e26fd9823ca8aa17d10b7c2a1ad` |
| `audio-manifest.json` | `ac8fcde0db78c3157c1321149eeb64aa4955487ab484e0ea9cd54ac7db729f70` |
| `scene-manifest.json` | `0b09f39d96ef9e2ff1824cee839f12e4982d8ef434122113df657e8b7f785c6d` |

## 識別と評価の限界 / Identity and evaluation limits

- `subset-plan.json`: 取得前の話者分割、メンバー名、サイズ、CRC、archive URL/ETag。
- `audio-manifest.json`: 実際に取得した音声のSHA-256と長さ、出典資料、外部HARPコードのcommitとファイルSHA。
- `scene-manifest.json`: 各sceneの部屋・音源・受音位置・seed・音声参照・crop条件。音声manifestのSHAを保持。
- 各dataset sampleのmetadata: 使用音声SHA、反射次数、推定減衰、生成条件とSTFT条件。

**Speaker separation is not the same as sentence separation:** VCTK includes passages shared across speakers, so held-out speakers may read text also heard during training. WSJ0 evaluation, all-corpus training, the authors' exact HARP configuration, and equality with the paper's official checkpoint are not established by this subset. Record actual consumed scenes, held-out scores, failures and resource limits separately.
