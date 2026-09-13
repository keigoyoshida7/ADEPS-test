# データの出典と学習記録 / Data sources and training record

この文書は、同梱モデルカード、学習コード、重みファイルを照合した記録です。**現在の学習データは、このプロジェクトのコードで生成した合成データです。** 実際の会場録音、測定した室内IR、HARP・VCTK・WSJ0の音声コーパス、ADEPS著者の学習済み重みは使用していません。今回の説明追加で再学習は行っていません。

## 日本語：まず、3種類の処理を分ける

| 画面・処理 | 学習の有無 | データの出どころ |
|---|---|---|
| 再生系「目標からの誤差」 | **学習なし** | 仮想配置、距離、音速、直接音・一次反射から応答Hを計算し、その都度補正行列Gを解く |
| 拡散スタジオ／小型prior | **独自学習あり** | 方向・位相・強さを乱数で決めた36複素係数のベクトル |
| 学習モデル比較／残差推定器 | **独自学習あり** | 仮想音場と仮想アレイから作る観測、線形推定、既知の正解係数 |

再生系の「調整点」「未使用点」は、補正行列を求める位置と評価用の位置です。ニューラルネットワークの学習・検証データではありません。処理は正則化した音圧マッチングで、`G = (HᴴH + λI)⁻¹HᴴT` を周波数ごとに求めます。`λ=0`では擬似逆行列を使い、設定に応じて解いた後の列ノルムを制限します。[再生系の計算コード](https://github.com/keigoyoshida7/ADEPS-test/blob/main/backend/numerics.py)

### 1. 拡散スタジオの `tiny-spatial-v1`

**どこからデータを作ったか。** 学習コードの `vectors(count, seed)` は、1〜2方向の主な平面波と3本の弱い方向成分を合成します。方向、複素振幅の位相・強さ、共通ゲインを変え、5次・36成分のreal ACN/N3D係数を生成します。これは録音ファイルの切り抜きではなく、独立した複素ベクトルです。マイク配置や取得応答Vはこのpriorの学習入力に含めず、推論時に別途使います。

| 項目 | 同梱モデルの記録 |
|---|---|
| 学習データ | 48,000個の独立36複素係数ベクトル |
| 検証データ | 別に生成した2,048ベクトル |
| seed | 学習データ・初期化7319、検証データ7320、検証ノイズ7321。後二者はコードの`seed+1`、`seed+2`から確認 |
| 構造 | 80入力（実部・虚部72＋ノイズレベル特徴8）、幅96のSiLU隠れ層2層、72出力 |
| 学習済みパラメータ | 24,072 |
| 学習方法 | AdamW、学習率0.001、weight decay 0.0001、batch 512、4,000ステップ |
| 保存した重み | 4,000ステップ終了後。最小の検証損失で途中の重みを選ぶ処理ではない |
| 検証方法 | 固定した検証ノイズを使い、σ=0.03〜10の6条件で学習前後を比較 |
| 記録された環境 | PyTorch 2.9.0、CPU、3 threads |

**何を学習したか。** 生成した係数を振幅圧縮 `H`（α=0.67、β=3）で変換し、その実部・虚部へガウス雑音を加えます。ノイズ標準偏差σは0.002〜80の対数一様分布です。EDM型の事前調整を施したMLPに、圧縮した元の係数へ戻す誤差を学習させます。

```text
target = real/imag(H(a))
noisy = target + σ × Gaussian noise
loss = mean [ ((σ² + σ_data²) / (σ × σ_data)²)
              × (D(noisy, σ) − target)² ]
```

`σ_data` は学習用の圧縮係数のRMSから求め、カードに保存しています。各時間・周波数点を独立に処理し、隣接フレーム、周波数間の構造、言葉や残響の文脈は学習していません。拡散スタジオのトーンやノイズバーストは推論用の例であり、モデルが実際の発話を学習した証拠ではありません。

**出典として残っているもの。** `training.source_sha256` は`null`です。この項目は外部`--hoa-npz`ファイルを使った場合のハッシュで、同梱モデルは手続き生成経路を使うため外部ファイルがありません。学習時のコードcommitやコード全体のハッシュを記録した値ではありません。モデルカードにも当時のコードcommit/hashは残っていません。

- [生成・学習コード](https://github.com/keigoyoshida7/ADEPS-test/blob/main/scripts/train_tiny_prior.py)
- [モデルカード・学習ログ](https://github.com/keigoyoshida7/ADEPS-test/blob/main/public/models/tiny-spatial-v1.json)
- [推論コード](https://github.com/keigoyoshida7/ADEPS-test/blob/main/backend/neural.py)

### 2. 学習モデル比較の `spatial-v1`

**どこからデータを作ったか。** 学習コードの `scene(seed)` は1〜5方向の平面波と拡散した係数成分を合成します。理想的な無指向性アレイに対し、取得応答V、雑音を含む観測p、線形推定`E p`を計算します。方向、アレイの回転・半径、強度、スペクトル傾斜、拡散成分、ノイズ、正則化を変えます。これらは実際の音声STFTや測定した室内応答ではありません。

| 項目 | 同梱モデルの記録 |
|---|---|
| 学習データ | 3,072シーン×64周波数×8フレーム＝1,572,864ビン |
| 検証データ | 64シーン×64周波数×8フレーム＝32,768ビン |
| 周波数・時間構造 | 1 Hz〜20 kHzの64対数周波数、8個の相関した複素フレーム。録音時間は対応付けていない |
| アレイ | 4/5/6/8/12素子、半径4〜10 cm、理想無指向性・自由空間、3D回転、一部は位置の微小なばらつきあり |
| 音場・ノイズ | 5次または15次の係数、SNR 10〜50 dB。推定は先頭36係数を対象 |
| seed | 初期化38741、学習10000〜13071、検証20000〜20063 |
| 構造 | 465入力特徴、幅512のSiLU隠れ層4層、36複素係数の残差出力 |
| 学習済みパラメータ | 1,063,496 |
| 学習方法 | AdamW、初期学習率0.0008からcosine減衰で0.00004、weight decay 0.0001、batch 512、勾配ノルム上限2 |
| 学習実行 | 12,000ステップ。512シーンずつのchunkを2,000ステップごとに切り替える |
| 保存した重み | 200ステップごとの独立した検証でFOA損失が最小だった10,400ステップ |
| 記録された環境 | PyTorch 2.9.0、Apple MPS、CPU threads 3 |

1,572,864は特徴ベクトルにしたビン数であり、1,572,864個の独立した部屋や録音ではありません。同じシーンの周波数・時間点を共有しています。学習・検証の分割はシーンseedで行います。

**何を学習したか。** 入力は線形推定の36複素係数、解像行列`E V`、時間共分散、チャンネルのパワー、周波数です。正規化尺度は線形入力のFOA RMSだけから計算し、正解係数は入力の正規化に使いません。元の線形係数に残差を加え、合成した正解係数へ近づける教師あり学習です。

```text
prediction = normalized_linear_coefficients + MLP(features)
loss = weighted mean of squared real/imaginary coefficient errors
weight = 1 for the first 4 FOA coefficients; 0.025 for the remaining 32
```

学習時には、同じ複素位相回転を入力係数と正解へ適用します。推論は1回の決定的な順伝播で、拡散サンプリングはありません。時間共分散・パワー・RMSには与えた区間全体を使うため、未来のフレームも含むオフライン処理です。

**評価をどう分けたか。** モデルの重み選択に使う64シーンとは別に、推論の混合率などの調整はseed 25000〜25035、最終複素スペクトルテストは90000〜90035、合成WAVテストは91000〜91002を使います。重み選択用の検証で改善しても、それ自体は最終評価でも実録音の品質保証でもありません。結果と悪化例は[SPATIAL_MODEL.md](SPATIAL_MODEL.md)に分けて記録しています。

**出典として残っているもの。** カードの`training_scenes_sha256`と`validation_scenes_sha256`は、シーンseed、素子数、半径、SNRなどの**条件リストをJSON化したもの**のハッシュです。生成した全入力・正解テンソルのハッシュや学習時のコードcommitではありません。同梱のモデルカードは、現在のスクリプトの既定値（2,000step・検証32シーン）ではなく、実行時に指定された12,000step・検証64シーンを記録しています。

- [生成・学習コード](https://github.com/keigoyoshida7/ADEPS-test/blob/main/scripts/train_spatial_model.py)
- [モデルカード・学習ログ](https://github.com/keigoyoshida7/ADEPS-test/blob/main/public/models/spatial-v1.json)
- [特徴量・推論コード](https://github.com/keigoyoshida7/ADEPS-test/blob/main/backend/spatial_model.py)

### 3. 重みの確認と、再現の限界

同梱NPZファイルから再計算したSHA-256は、次のモデルカード値と一致しています。

| モデル | 同梱重みのSHA-256 |
|---|---|
| tiny-spatial-v1 | `a5c7e36437b4ed932ff5bbf04a56ab96b3e12954b49c2bb699035370608e48cb` |
| spatial-v1 | `4ce8deee16af297b3a3557b827438e469798c00e9c4aa936172cb8a7475b046c` |

重みを同定できることと、学習経路をバイト単位で再現できることは別です。全学習ベクトルはデータセットとして同梱しておらず、生成コードとseedから作る構成です。リンク先は現在の公開コードで、当時の学習コードを固定した証明ではありません。端末・依存ライブラリ・乱数計算の差もあるため、再実行して完全に同じ重みになるとは保証しません。

どちらも独自の合成実験用モデルです。**公式ADEPSの再現、論文以上の精度、実際の音声や会場での改善は、この学習記録だけでは示せません。** モデルが形や音を生成できること、参照のある合成条件で数値が良いこと、実環境で正しく復元できることを区別します。

## English

This document checks the bundled model cards, training scripts and weight files. **Training data were generated by this project’s code.** No venue recordings, measured room IRs, HARP/VCTK/WSJ0 audio corpora or pretrained weights from the ADEPS authors were used. Documenting provenance did not retrain either model.

### Three separate processes

- **Playback, “Error from target”: no neural training.** A synthetic transfer H is calculated from geometry, distance, sound speed, direct sound and first-order reflections. Regularized pressure matching solves G for the current conditions. Calibration/held-out positions are spatial fitting/evaluation points, not neural training data. The code is linked above.
- **Diffusion studio: independently trained tiny prior.** It learns denoising from generated complex spatial coefficient vectors. Known V is supplied separately at inference.
- **Learned model comparison: independently trained residual estimator.** It learns corrections to linear encoding using virtual-array observations and known synthetic target coefficients. Inference is deterministic, not diffusion sampling.

### Tiny prior: data and training

`vectors(count, seed)` combines 1–2 main plane waves and 3 weaker directional components with random directions, complex gains/phases and overall gain. It creates 36 complex fifth-order real ACN/N3D coefficients per vector. There is no microphone geometry in the learned prior’s inputs and no recorded speech or room context.

The bundled model uses 48,000 training vectors and 2,048 independently generated validation vectors. The training/initialization seed is 7319; validation data and validation noise use 7320 and 7321, derived from the script’s `seed+1` and `seed+2`. These counts are vectors, not rooms or recording durations.

The MLP has 24,072 parameters, two 96-wide SiLU hidden layers, 72 real/imaginary coefficient inputs plus 8 noise-level features, and 72 outputs. Training uses AdamW, learning rate 0.001, weight decay 0.0001, batches of 512 and 4,000 steps. The final 4,000-step weights are saved rather than selecting an intermediate checkpoint on validation.

Coefficients are amplitude-compressed with α=0.67 and β=3. Gaussian noise is added with σ sampled log-uniformly from 0.002 to 80. The loss is the EDM-style weighted squared denoising error shown above; `σ_data` is estimated from the compressed training coefficients. Validation compares fixed noise at six σ values from 0.03 to 10 before and after training. The recorded runtime environment is PyTorch 2.9.0 on CPU with three threads.

The model works independently at each time–frequency bin. It does not learn cross-frame, cross-frequency, linguistic or room-reverberation context. The tones and noise bursts in the studio are inference examples, not evidence of speech training.

The card’s `training.source_sha256` is `null` because procedural generation was used. This field hashes an external `--hoa-npz` input when one is supplied; it is not a training-code hash. No training-time code commit/hash is recorded in the card. Links to the current generator/trainer, model card and inference implementation appear in the Japanese section above.

### Residual estimator: data and training

`scene(seed)` creates 1–5 plane waves plus diffuse modal components, then computes virtual-array V, noisy observations p and linear estimates E p. Arrays have 4/5/6/8/12 ideal omnidirectional sensors, radius 4–10 cm, random 3D orientation and sometimes small position perturbations. Scenes vary directions, source strengths, spectral tilt, diffuse energy, noise and regularization. They use order-5 or order-15 fields, 10–50 dB SNR, 64 logarithmic frequencies from 1 Hz to 20 kHz and eight correlated complex frames. They are not speech STFTs or measured rooms.

Training comprises 3,072 scenes × 64 frequencies × 8 frames = 1,572,864 feature bins. Validation comprises 64 scenes = 32,768 bins. Bins share scene conditions and are not independent recordings. Seeds are 38741 for initialization, 10000–13071 for training scenes and 20000–20063 for validation scenes.

The network has four 512-wide SiLU hidden layers and 1,063,496 parameters. Its 465 features include 36 complex linear coefficients, physical resolution E V, temporal covariance, powers and frequency. It predicts a residual added to the linear estimate. Inputs and targets share an input-only RMS normalization; target coefficients never set input scaling. The loss weights normalized real/imaginary squared errors by 1 for the first four FOA coefficients and 0.025 for the remaining 32. A common random complex phase augments input coefficients and targets during training.

Training uses AdamW with learning rate 0.0008 decaying by cosine schedule to 0.00004, weight decay 0.0001, batch 512 and gradient-norm cap 2. Training runs 12,000 steps, switching 512-scene chunks every 2,000 steps. Independent validation every 200 steps selected step 10,400. The recorded environment is PyTorch 2.9.0 with Apple MPS and three CPU threads. Inference uses the whole supplied window for covariance, power and RMS, making it offline/noncausal.

Model selection, inference tuning and final tests remain separate: tuning scenes use seeds 25000–25035, final complex-spectrum tests use 90000–90035 and synthetic-WAV tests use 91000–91002. The model card’s training/validation SHA-256 values hash JSON lists of scene specifications, not the complete input/target tensors or the historical code commit. The recorded run used 12,000 steps and 64 validation scenes, which differ from the current script defaults of 2,000 steps and 32 validation scenes. Consult the linked model card for the bundled run and [SPATIAL_MODEL.md](SPATIAL_MODEL.md) for evaluation and regressions.

### Weight identity and limits

The weight hashes in the table above were checked against the bundled NPZ files. Identifying a weight file does not guarantee byte-identical retraining. Full training vectors are not bundled as a dataset; they are generated from code and seeds. Source links point to the current repository code rather than a recorded training-time commit. Hardware, dependencies and numerical differences may change retraining results.

Both models are independent synthetic experiments. Model size, a denoising result or improved synthetic metrics do not establish official ADEPS reproduction, superiority over the paper or improvement on real speech and venues.

## 参照した研究 / Research references

- Amit Milstein, Nir Shlezinger, Boaz Rafaely. *Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling*. [arXiv:2608.24558](https://arxiv.org/abs/2608.24558). Referenced for the inverse problem, observation model and diffusion posterior-sampling ideas; it is not the source of these weights or synthetic training vectors.
- Tero Karras et al. *Elucidating the Design Space of Diffusion-Based Generative Models*. [arXiv:2206.00364](https://arxiv.org/abs/2206.00364). Referenced for EDM-style denoiser preconditioning and weighted denoising loss in the small independent prior. Full implementation choices are recorded in [NEURAL_PROTOCOL.md](NEURAL_PROTOCOL.md).
