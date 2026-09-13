# ADEPS+ の再計算

ADEPS+ は、マイク観測から推定した空間成分、独自に学習した固定モデル、音声・観測の整合処理を組み合わせる実験方式です。論文の公式実装や、論文と同じ精度を保証するものではありません。公開 Web UI の保存済み結果を見ることと、手元の入力をこの CLI で再計算することは別です。

方式・引用は [PLUS_METHODS.md](PLUS_METHODS.md)、開発と最終テストの分離・事前の成功条件は [PLUS_PROTOCOL.md](PLUS_PROTOCOL.md) を参照してください。既存の30.78Mモデルを固定し、観測由来の方向共分散Wiener推定とSTFT／観測整合を加えています。

## Webで確認・ダウンロード

v0.7.0の左から3つ目、[ADEPS + α](https://keigoyoshida7.github.io/ADEPS-test/?v=0.7.0&tab=plus)が専用タブです。GitHub Pagesでは計算済みの評価JSONを表示し、手元の録音やモデルをブラウザ内で新たに処理することはありません。

1. 全9方式の平均・場面別誤差・周波数曲線を確認します。32場面と4話者ペアの比較で、悪化・未定義の結果も含みます。
2. 固定scene 0000の試聴欄で方式を選びます。ここにある **ON/OFFスイッチは、選択方式と調整済みLinearを切り替えるもの**です。学習済み除去器だけの寄与を見る場合は、方式一覧の「ADEPS + α・学習済み補正ON」と「同じα処理・学習済み補正OFF」を比較します。
3. [音声・記録ZIP](../public/models/plus-example-audio.zip)をダウンロードすると、参照＋9方式のFOA FLOAT32 WAV、固定cardioidステレオ試聴、設定・全比較の評価記録・出典とライセンスを確認できます。FOAとステレオを合わせた全対象に、同じgainを使っています。

同じ公開例を手元で再計算するための [plus-example-input.npz](../public/models/plus-example-input.npz) も取得できます。ZIPにも同一バイトの入力NPZを同梱します。このNPZには観測 `p`、応答 `V`、周波数・規約・出典と識別情報だけを含め、正解のAmbisonics係数や正解の音源方向は含めません。

対応する公開記録は [plus-benchmark.json](../public/models/plus-benchmark.json)、[plus-selection.json](../public/models/plus-selection.json)、[plus-example.json](../public/models/plus-example.json) です。完成済みの評価記録が揃った場合だけ表示し、未公開・不整合のデータから結果を作りません。32場面の成績と、約0.248秒の1試聴例の印象を分けて判断します。

## 必要なもの

- このリポジトリと `public/models/plus-selection.json`。設定を手で変更すると、公開評価と同じ条件ではなくなります。
- `report.json` と `paper-prior-v1.pt` が入った固定モデルのフォルダ。既定は `work/paper-prior-v1` です。
- NumPy、SciPy、PyTorch を含む Python 環境。この作業環境では `.venv-paper/bin/python` を使います。モデル・環境の準備は [PAPER_PRIOR.md](PAPER_PRIOR.md) を参照してください。CLI が自動で大きなデータや重みをダウンロードすることはありません。
- 同期したマイク観測と、そのマイク構成に対応する複素伝達行列 `V` を持つ入力 NPZ。普通の WAV や B-format WAV を、そのまま `--input` に渡すことはできません。

入力は 16 kHz、FFT 512、hop 128、実数 ACN/N3D、N5 の36係数を前提にします。`p_real / p_imag` は `[257, マイク数, フレーム数]`、`V_real / V_imag` は `[257, マイク数, 36]` です。マイク数は4〜64、WAVを書き出すフレーム数は2〜256。学習と同じ短い単位は32フレームです。周波数は0〜8 kHzの全257点で、DC・Nyquistは実数です。`sample_rate_hz / n_fft / hop / frequencies_hz / sh_ordering / sh_normalization` の明記も必要です。

実際の録音を扱うには、マイクのチャンネル順・同期・向きと `V` の規約を合わせる必要があります。現地収録から適切な `V` を自動で作る機能は、この CLI にはありません。

## 実行

リポジトリのルートで実行します。出力先には、まだ存在しないフォルダを指定してください。

```bash
.venv-paper/bin/python scripts/infer_plus.py \
  --input public/models/plus-example-input.npz \
  --output work/plus-recomputed \
  --device mps
```

これは公開時の固定scene 0000を、同じ観測から再計算する手順です。追加の未使用データによる独立評価ではありません。ダウンロード先が異なる場合は `--input` のパスを変えてください。別の環境では `--device auto` または `cpu` を使えます。重みや設定の場所を変える場合は `--checkpoint`、`--selection` を指定します。選択された重みと実ファイルの SHA256 が違う場合は停止します。設定にコードの SHA256 が宣言されている場合も照合します。

`plus-example.json` の `input_sha256` は周波数・V・pの数値とshapeを使う**観測そのものの識別値**で、入力NPZの `observation_sha256` と一致します。`inference_input_file_sha256` はダウンロードするNPZのバイト列の識別値です。`input_file_sha256` は元の評価用cacheファイルの識別値であり、これらを混同しません。

既定の空間推定は、**合成実験の SNR 50 dB という既知条件**を使います。省略して実録音へ使っても、その録音が50 dBだったと確認したことにはなりません。仮定は起動時と保存 JSON に表示されます。

- SNR を別途把握している場合：`--noise-snr 40` のように明示します。
- SNR が不明な場合：`--estimate-noise` で、方向成分・拡散成分と一緒に観測共分散からノイズ量を推定します。残響やモデル誤差をノイズと取り違える可能性があり、校正済みの騒音計測ではありません。

この2オプションは同時に指定できません。どちらも公開時の条件を変更するため、同じ評価結果は保証されません。

## 学習済みモデルの寄与を比較する

同じ入力・設定で別の出力先を指定し、`--no-denoiser` を付けます。

```bash
.venv-paper/bin/python scripts/infer_plus.py \
  --input public/models/plus-example-input.npz \
  --output work/plus-without-denoiser \
  --device mps \
  --no-denoiser
```

この条件では空間推定と同じ回数の整合処理を残し、学習済みノイズ除去器だけを呼びません。`nfe=0` と各段階の `model_call=false` が記録されます。解析方式だけの `spatial` と最終結果の差には整合処理の効果も含まれるため、学習の寄与はこの ON/OFF 条件で確かめます。ノイズのオプションを変更した場合も、両方の実行で揃えてください。

## 出力

| ファイル | 内容 |
| --- | --- |
| `reconstruction.npz` | `estimate_real / estimate_imag`、`linear_real / linear_imag`、`spatial_real / spatial_imag`。36係数の未圧縮・音量調整前の結果です。 |
| `estimate-foa.wav` | 最終結果の FOA、4ch FLOAT32。 |
| `linear-foa.wav` | 同じ入力から求めた調整済み Linear の FOA。 |
| `spatial-foa.wav` | 学習済みモデルを使う前の空間推定の FOA。 |
| `summary.json` | 実効設定とその SHA256、入力・重み・コードの SHA256、各段階の補正量と観測残差、モデル呼び出し回数、入力の出所・音声ライセンス情報、出力ファイルの SHA256。 |

WAV の順序は **W, Y, Z, X（ACN/N3D）**です。通常のステレオではないので、試聴・スピーカー再生には対応するデコーダーが必要です。

有限区間の逆 STFT の後、両端を256 samplesずつ切り出します。32フレームなら3968 samples＝0.248秒です。同じ実行内の3方式には、3本全体の最大振幅が0.95になる**同一の gain**を適用し、方式間の相対音量を保ちます。別々の実行では gain が変わる場合があるため、ON/OFFを厳密に比較する際は `summary.json` の `audio.shared_gain` を戻して共通の音量に揃えるか、未調整の NPZ を使ってください。

入力の `attribution_json / provenance_json / audio_json` は保存結果へ引き継ぎます。音声の再配布条件は元データのライセンスに従ってください。この CLI は正解音声を生成・参照せず、参照に対する NRMSE などの精度指標も計算しません。観測との一致だけでは、復元音場の正しさは証明できません。

## 完成した評価記録を公開形式へまとめる

研究用の全評価がすでに `work/plus-v1/` に保存されている場合、次の出力処理を使えます。

```bash
.venv-paper/bin/python scripts/export_plus.py
```

この処理は新しい推論や音場生成を行いません。全32場面・9方式の `benchmark.json`、事前選択の設定とseal、固定scene 0000の保存係数・出所・SHAが揃って一致した場合に、上記3つの公開JSON、`plus-example-input.npz`、`plus-example-audio.zip` を `public/models/` へ出力します。入力NPZは既存の推論ローダーで読み戻し、元のp/V/周波数と完全一致することを確認します。別の出力先は `--output-dir` で指定できます。元のVCTK FLAC、HARPソースコード、ニューラル重みはこのZIPに含めません。

公開用ZIPは参照と全9方式の**10対象共通gain**、単独CLIの出力はLinear・空間推定・最終結果の**3対象共通gain**です。それぞれの記録にgainと切り出し条件を保存します。元の周波数別・複素係数の誤差はgain適用前で、図の共分散だけに共通gainの2乗を適用します。

## English

The third **ADEPS + α** tab displays saved benchmark results; GitHub Pages does not run the native model. It compares nine methods under a precommitted 32-scene/four-speaker-pair protocol. The listening example is fixed to final scene 0000, never chosen for its score. The display's ON/OFF switch compares the selected method with tuned Linear; choose the separate learned-refinement OFF method to isolate the denoiser's contribution.

Use `scripts/infer_plus.py` with [plus-example-input.npz](../public/models/plus-example-input.npz) to recompute the exact public scene locally. The prepared NPZ contains microphone observations and the array response, without target coefficients or oracle directions. Its canonical `observation_sha256` matches the example JSON's `input_sha256`; `inference_input_file_sha256` identifies the downloadable file bytes. The frozen weights, selection and declared source hashes must match. `--no-denoiser` keeps the consistency processing but makes zero denoiser calls. `--noise-snr` supplies known side information; `--estimate-noise` fits noise from the observation covariance. The default 50 dB is a synthetic experiment assumption, not a measurement of an arbitrary recording.

The [downloadable ZIP](../public/models/plus-example-audio.zip) contains reference plus all nine methods, matched-gain FOA and stereo WAVs, the identical prepared input NPZ, attribution/license, selection and evaluation records. `scripts/export_plus.py` packages completed saved results without running inference or regenerating scenes. See [methods and citations](PLUS_METHODS.md) and the [evaluation protocol](PLUS_PROTOCOL.md) for the limits of the comparison. Historical v0.6.0 examples are now known diagnostic/development material, not fresh final confirmation data.
