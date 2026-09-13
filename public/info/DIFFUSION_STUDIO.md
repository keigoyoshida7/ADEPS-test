# 拡散スタジオ / Diffusion studio

拡散スタジオは、仮想マイクの観測からFOAを推定する**独自の小型拡散実験**です。実際に反復計算を行い、途中のノイズ除去後の推定と最終出力を、形・指標・音で確認します。図だけを変形させるアニメーションではありません。

同梱の `TinyDenoiser` は24,072パラメータのMLPで、独自生成した空間係数から学習しています。論文の音声データ・ネットワーク・公式重みは使っていません。音声や実会場での改善、論文と同等の品質、論文を上回る結果は未検証です。「学習モデル比較」の1,063,496パラメータの教師あり残差ネットワークとは別の処理です。

この画面の音源は、倍音を含むチャープと短いノイズバーストを含むトーンの2種類です。方向は方位−45°・仰角25°、方位115°・仰角−20°に固定しています。発話・実録音・実測室ではありません。観測の生成と逆推定には同じ5次のモデルを使うため、モデルの不一致や高周波での次数打ち切りへの頑健性を証明する実験ではありません。

## 日本語：まず試す

1. 4つ目のタブ「拡散スタジオ」を開き、既定の条件で計算します。マイクは不要です。
2. 線形推定と最終出力を切り替え、同じ条件で音と形を比較します。中間推定は保存された時点を選んで確認できます。
3. **入力条件を固定して拡散seedだけ変更**します。同じ観測から、初期乱数によってどのような差が出るかを見る実験です。
4. 観測整合の強さ `η′` を変えて再計算します。大きくするほど良くなるとは限りません。`0` は観測整合の勾配更新を止めますが、初期値に観測が含まれるため完全な無条件生成にはなりません。
5. 次に仮想アレイの形・マイク数・半径を変えます。こちらはVと観測が変わるため、seedだけを変更した比較とは別の実験として記録します。
6. 気に入った結果や悪化した結果も、条件とFOA WAVを保存します。制作上の好みと復元精度の評価は分けます。

既定の音源区間は**0.35秒・16 kHz**、FFTは256、hopは128です。DCを除く解析点は**62.5 Hz〜8 kHz、62.5 Hz刻み**です。このスタジオの音声解析を、別の合成スペクトル実験の1 Hz〜20 kHz表示と取り違えないでください。画面内の履歴は最新6件までなので、残したい結果はZIPへ保存します。

### 何を固定し、何を変えるか

| 条件 | 処理への影響 |
|---|---|
| 仮想マイクの球状／平面リング配置、数、半径 | シミュレーションのVとマイク観測を変える。実際の施設のスピーカー配置は変更しない |
| 観測seed・観測SNR | 仮想入力の乱数条件や観測ノイズを変える |
| 拡散seed | 同じ観測に加える推論開始時の乱数を変える |
| `η′` | 圧縮した符号化空間での観測整合更新の強さを変える |
| 反復回数 | 同じ開始・終了ノイズレベルをつなぐスケジュールの刻み方を変える。計算を長くすれば品質が保証されるという意味ではない |
| 表示帯域・保存済み中間点の選択 | 計算済みのFOAから表示する結果を選ぶ。選択操作自体は再学習ではない |

独自の仮想アレイは、自由空間の理想的な無指向性センサーを仮定します。形や素子数を市販マイクに合わせても、その製品固有の校正応答にはなりません。

平面リングでは上下を分ける観測情報が不足します。拡散priorがZ成分や上下方向に形を作っても、その情報をマイクが測定できたことを意味しません。参照との誤差と、周波数ごとのFOA rankも確認します。

### 反復番号と途中の音

反復中の保存対象は、Euler更新前にモデルが予測したノイズ除去後の係数 `D(xᵢ, σᵢ)` です。圧縮を戻し、FOAの4成分を取り出して試聴と表示に使います。反復番号は音源の再生時刻ではありません。

保存記録の `step` は完了した更新数、`iteration` はこれから行う更新の番号です。中間点では `step = i`、`iteration = i + 1` です。最後にはノイズレベル0への更新を終えた状態 `x_M` を別の最終出力として保存します。途中のノイズ除去推定と最後の更新結果は、同じものとして扱いません。

この小型priorは時間・周波数の各点を独立に処理します。隣り合うフレームや周波数の文脈を学習する音声モデルではないため、途中の音にノイズや音色の変化、復元の悪化が出ることがあります。

### アレイ配置を3Dで見る（v0.5.2）

「アレイ配置 3D」は、復元を実行する前から表示できます。本数・球面／水平リング・半径を変えると、同じ配置生成式でプレビューを更新します。入力順のM1…を選んで座標を確認でき、上・正面・左側への視点切替、回転、拡大縮小、座標表に対応します。座標はX前・Y左・Z上、保存値m／画面の数値cmです。マーカーの寸法は実際のカプセル径ではありません。

「現在の設定」は入力欄のプレビュー、「復元Nで使用」はその結果に保存された `microphone_positions_m` です。配置の設定を変えると現在のプレビューへ切り替えますが、保存済みの音と推定は変わりません。復元の履歴を選ぶと、その復元に使った配置が選択されます。3Dカメラの操作は視点だけを変え、マイクの物理配置を回転させません。

「学習モデル比較」と「マイク → Ambisonics」でも、計算結果に含まれる配置を表示します。学習モデル比較の合成配置はseedに応じて回転するため、現在の入力値から配置を推測せず、実際の結果の座標を使います。入力に座標がない場合は配置情報なしと表示します。

**English.** The **Microphone array 3D** view is available before reconstruction. Microphone count, sphere/ring layout and radius update a geometry-only preview using the same formula as the observation generator. Numbered microphones retain input-channel order. Rotate, zoom, choose top/front/left views, and inspect XYZ coordinates and extents. Coordinates use X front, Y left, Z up; stored metres are displayed in centimetres. Markers do not represent capsule dimensions.

**Current settings** previews the form; **Run N geometry** uses coordinates stored in that result. Editing geometry switches to the draft preview without changing saved audio or estimates. Selecting history shows that run’s geometry. Camera movement only changes the viewpoint. Learned-model comparison and linear capture show returned result coordinates, never guessed placements for inputs without positions.

### 3D表示の意味

3Dの形は、FOA複素スペクトルの**帯域別チャンネル共分散に基づく方向別RMS**です。推論の途中で得られた信号から計算しており、推論確率や確信度ではありません。部屋の中の位置ごとの音圧分布、音源位置を同定した地図、実測したスピーカー指向性でもありません。

real ACN/N3D、チャンネル順 `W,Y,Z,X` のFOAを `a`、選択帯域を `B` とすると、表示用の計算は次です。

```text
R_B = Re mean_(f in B, t) [ a(f,t) a(f,t)ᴴ ]
y(d) = [1, √3 d_y, √3 d_z, √3 d_x]
rms_B(d) = sqrt(max(0, y(d) R_B y(d)ᵀ))
```

`d` は単位方向ベクトルです。共分散にはチャンネル間の関係も含まれ、チャンネルごとのレベルだけを球面へ貼り付けたものではありません。この方向合成と、以下のステレオ試聴のカーディオイドは異なる重みを使います。

帯域は全帯域20–8000 Hz、低域20–500 Hz未満、中域500–2000 Hz未満、高域2000–8000 Hzです。16 kHz・FFT 256の周波数間隔は62.5 Hzなので、表示範囲の端の20 Hzが独立した解析点として存在するわけではありません。各帯域はスペクトル点の平均であり、帯域内の積分パワーや校正済みSPLではありません。

共分散は推論後のFOAスペクトルから直接計算し、DCとNyquistの虚部を0にします。書き出した音を再度STFTにした値ではないため、スペクトルの不整合を含む推定では、波形のSI-SDRとスペクトル上の誤差を別々に読みます。

保存された共分散には、その試行の書き出しゲインの二乗が適用されています。**3D表示では、そのゲインの二乗で割って元の係数レベルへ戻します。** 「同じ入力の全ステップ・候補で表示スケールを共通化」がONなら、同じ入力ハッシュの履歴を共通の尺度で表示するため、試行ごとの書き出し減衰が図の比較に混ざりません。OFFでは表示ごとに尺度が変わり、図の大きさで試行間の振幅差を判断できません。

### 音の比較とMax

- ブラウザのステレオ試聴は、FOAから作った正面左右45°の**仮想カーディオイド**です。HRTFを使うバイノーラルではありません。上下・前後の知覚を検証する用途には使いません。
- 線形、参照、保存した中間点、最終出力には、同じ試行で共通の書き出しゲインを使います。さらにブラウザで試聴対象を切り替える際、同じ入力ハッシュの履歴内で最小の書き出しゲインに揃えるよう、プレーヤー音量を調整します。手動でプレーヤー音量を変えると、この比較条件も変わります。
- ZIPのWAVは、引き続き試行ごとの書き出しゲインです。異なる試行のZIPをMaxで比較する際は、`metadata.json` の `audio.shared_gain` を確認し、共通ゲインへ揃えます。各ファイルを別々にピーク正規化しません。
- 保存する4ch FOAは **ACN/N3D、W,Y,Z,X** です。Maxでは対応する外部Ambisonicsデコーダーへ読み込みます。4chを4台のスピーカーへ直接つなぐ形式ではありません。
- 既存のMax実験パッチはACN/SN3Dの比較経路です。そこへ入れる場合は、Wを維持し、Y・Z・Xをそれぞれ `1/√3` 倍してN3DからSN3Dへ変換するか、別のN3D対応経路を使います。
- 保存したファイルによるオフライン試聴です。WebからMaxへのライブ音声送信や会場のリアルタイム補正ではありません。

保存ZIPには `reference_FOA_ACN_N3D.wav`、`linear_FOA_ACN_N3D.wav`、6個の `denoised_..._FOA_ACN_N3D.wav`、`final_FOA_ACN_N3D.wav`、`metadata.json`、`READ-ME.txt` が入ります。FOA WAVは32bit float、ブラウザのステレオ試聴はPCM16です。メタデータのschemaは `adeps-test-diffusion-studio/1` で、入力ハッシュ、モデルの出典、設定、ゲイン、帯域、指標、反復の記録を保持します。同じ入力かどうかは、音を聴いた印象だけでなく `input_sha256` で確認できます。

## English: use and interpretation

This studio runs an **independent small-model diffusion experiment**. It reconstructs FOA from a virtual microphone observation and exposes saved denoised intermediate estimates and the final output as shape, diagnostics and audio. The shapes come from computed signal estimates, not a decorative deformation animation.

The existing 24,072-parameter `TinyDenoiser` MLP was trained on independently generated spatial coefficients. It does not use the paper’s speech data, architecture or official weights. Paper-level quality, reproduction of published results and improvement on real speech or venue recordings are unverified. This is a separate method from the 1,063,496-parameter supervised residual network in “Learned model comparison”.

The two procedural sources are a harmonic chirp and a tone with a short noise burst, fixed at azimuth/elevation −45°/25° and 115°/−20°. They are not speech, recordings or a measured room. The same fifth-order model generates observations and performs inversion, so this is not evidence of robustness to model mismatch or high-frequency order truncation.

### Start with a controlled comparison

1. Open the fourth tab, “Diffusion studio”, and run the default experiment. No microphone is required.
2. Compare linear and final output with the same playback conditions. Select saved intermediate estimates to inspect the process.
3. Keep the source, virtual array and observation-noise conditions fixed; change **only the diffusion seed**. This changes the random initialization for the same observation.
4. Change guidance `η′` and rerun. Larger guidance does not guarantee better results. Zero removes the observation-consistency gradient update, but initialization still contains the observation: this is not fully unconditional generation.
5. Change array geometry, microphone count or radius as a separate experiment. These change V and the microphone observation, not just the diffusion path.
6. Save conditions and FOA audio for appealing results and regressions alike. Creative preference and reconstruction accuracy are separate judgments.

The default segment is **0.35 seconds at 16 kHz**, with FFT 256 and hop 128. Non-DC analysis bins run from **62.5 Hz to 8 kHz in 62.5 Hz steps**. This studio’s audio analysis is separate from the 1 Hz–20 kHz display in the synthetic-spectrum experiment. The interface keeps the latest six runs; save a ZIP for results you want to retain.

The virtual array assumes ideal omnidirectional sensors in free space. Matching its shape or sensor count to a commercial microphone does not provide that device’s calibrated response.

A planar ring lacks information for separating elevation. A generated Z component or vertical structure does not prove that the microphones measured it. Inspect reference errors and frequency-dependent FOA rank as well.

### Intermediate estimates and the 3D display

Selected checkpoints store the denoised estimate `D(xᵢ, σᵢ)` **before** the Euler update. It is expanded out of compressed space and truncated to FOA for audio and display. `step` counts completed updates (`i`); `iteration` identifies the next update (`i+1`). The final sample stores the actual state `x_M` after the update to zero noise. An iteration number is not an audio timestamp, and an intermediate denoised prediction is not the final sampler state.

The prior processes time–frequency bins independently, without learned temporal or frequency context. Intermediate or final audio can contain noise, coloration or poorer reconstruction than the linear baseline.

The 3D shape is **directional RMS derived from band-wise covariance of complex FOA spectra**. The equations above use real ACN/N3D coefficients in W,Y,Z,X order. They retain cross-channel relations rather than plotting independent channel powers. The result is neither a probability/confidence map, a source-location estimate, a pressure field over room positions nor a measured loudspeaker directivity.

Bands are broadband 20–8000 Hz, low 20–below 500 Hz, mid 500–below 2000 Hz and high 2000–8000 Hz. Analysis uses 16 kHz and FFT 256, giving a 62.5 Hz bin spacing; a 20 Hz display boundary does not imply an independent 20 Hz measurement bin. Band covariance averages spectral bins rather than integrating band power, and is not calibrated SPL. This directional synthesis uses different weights from the stereo cardioids below.

Covariance is computed directly from inferred FOA spectra after setting imaginary DC and Nyquist components to zero. It is not computed by reanalysing the exported waveform. If inferred spectra are inconsistent, waveform SI-SDR and spectral errors must therefore be read separately.

Saved covariance includes the square of that run’s export gain. **The 3D view divides by this squared gain to restore the original coefficient level.** With the shared visual scale enabled, history entries with the same input hash use one scale, so differing export attenuation does not affect the visual comparison. Disabling it lets the scale change between views; displayed size then cannot establish amplitude differences between runs.

### Audio and Max

Browser stereo audition uses virtual cardioids facing ±45° from the front. It uses no HRTFs and is not binaural rendering for evaluating elevation or front–back cues. Linear, reference, saved intermediate estimates and final output share one export gain within a run. When changing the audition target, browser playback volume compensates to the smallest export gain among history entries with the same input hash. Manually changing the player’s volume changes this comparison condition.

Downloaded WAVs retain their run-specific export gain. When comparing ZIPs from different runs in Max, inspect `audio.shared_gain` in `metadata.json` and align them to a common gain. Do not independently peak-normalize the files.

Four-channel exports use **ACN/N3D in W,Y,Z,X order**. Load them into an external Ambisonics decoder in Max with matching conventions; FOA channels are not individual loudspeaker feeds. For the existing Max experiment patch’s ACN/SN3D path, retain W and multiply Y,Z,X by `1/√3`, or use a separate N3D-compatible path. This is offline file exchange, not a live Web-to-Max audio stream or real-time venue correction.

The ZIP contains `reference_FOA_ACN_N3D.wav`, `linear_FOA_ACN_N3D.wav`, six `denoised_..._FOA_ACN_N3D.wav` files, `final_FOA_ACN_N3D.wav`, `metadata.json` and `READ-ME.txt`. FOA files are float32 WAV; stereo previews are PCM16. Metadata uses schema `adeps-test-diffusion-studio/1` and records the input hash, model provenance, settings, gain, bands, metrics and iteration trace. Compare `input_sha256` to verify that different runs use the same input.

## 原典と実装 / Sources and implementation

1. Amit Milstein, Nir Shlezinger, and Boaz Rafaely. *Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling*. [arXiv:2608.24558v2](https://arxiv.org/html/2608.24558v2), 2026. Existing implementation mappings refer to the observation model, compressed encoded consistency in Eq. (10), the noise schedule, and Algorithm 1. The interactive geometry, directional-covariance display and intermediate audition are additions made for this prototype; they are not presented as methods or findings reported by the paper.
2. [Neural implementation protocol](NEURAL_PROTOCOL.md) records the independent network, procedural training, compression, normalization, gradients and endpoint choices. The studio reuses this small prior; it does not replace the independently trained supervised model described in [SPATIAL_MODEL.md](SPATIAL_MODEL.md).
