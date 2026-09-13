# 拡散スタジオ / Diffusion studio

> **過去の実装記録 / Historical implementation.** このページはv0.5.4以前の経路を記録しています。v0.6.0の公開UIは30.78Mの音声priorへ移行し、旧小型モデルの操作画面を取り除きました。現在のモデル・データ・評価・実行方法は[音声priorの実装と評価](PAPER_PRIOR.md)を参照してください。This page records an earlier implementation; see the linked current record for v0.6.0.

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

### Linear / ADEPS-testを周波数ごとに比較する（v0.5.4）

復元結果の下に、同じ合成FOA参照を使った**振幅スペクトル誤差**と**Magnitude-Squared Coherence（MSC）**のグラフを表示します。破線がそのrunのLinear、実線が選択中の保存済み拡散推定です。中間段階・最終結果・履歴を選ぶと更新され、「過程を再生」でも再生中の段階に追従します。拡散OFFで音をLinearに切り替えていても、この比較では選択中の拡散結果を保持します。

横軸は対数の1 Hz〜20 kHzです。現在の計算は16 kHz・FFT256なので非DCビンは62.5 Hz〜8 kHzで、計算外の帯域や評価が未定義の点は空白にします。誤差の縦軸は同じrunの全保存段階で共通、MSCは0〜1に固定します。周波数を選んで双方の値と差を読み、表・CSVへ保存できます。ZIPの `metadata.json` にも各保存段階の `frequency_metrics` を含めます。

#### 指標と引用

[ADEPS §4とFig.1](https://arxiv.org/html/2608.24558v3#S4)が参照する[Gen-A §III-D、式(5)(6)](https://arxiv.org/html/2501.08047v1#S3.SS4)に基づきます。`b`は合成参照、`b̂`は推定、`t`はSTFTフレーム、`c`はFOAの4チャンネル（W,Y,Z,X）です。

```text
S(f) = mean_(t,c) |20 log10(|b(t,f,c)| / |b̂(t,f,c)|)|
C(f) = mean_c [ |sum_t conj(b(t,f,c)) b̂(t,f,c)|²
                 / (sum_t |b(t,f,c)|² × sum_t |b̂(t,f,c)|²) ]
```

S(f)は小さいほど、MSCは1に近いほど参照に一致します。MSCはチャンネルごとに時間方向の相関を計算してからチャンネル平均し、時間・チャンネルをまとめた単一の相関にはしません。振幅スペクトル誤差は既存の複素NRMSEとは異なる指標です。一定のゲイン差や位相差があってもMSCだけは1になる場合があるので、2つの図を合わせて読みます。

採点には、表示とWAV生成に使う**未圧縮FOAのSTFT係数**を使います。DC/Nyquistの実数化後、共通書き出しゲインを適用する前に比較し、各推定の独立した音量正規化やWAVの再解析は行いません。

原典にはεや無音時の詳細処理がないため、次は本実装の追加条件です。振幅には参照全体の最大振幅×10⁻¹²の共通floorを両手法へ適用し、全フレーム×4チャンネルで平均します。参照が無音の周波数は評価しません。MSCでは参照に有効なエネルギーがある共通チャンネル集合を使います。その中で推定のエネルギーが0になるチャンネルがあれば、その周波数のMSCを未定義（null）にし、残りの良いチャンネルだけの平均に変えません。floorや有効チャンネル数は結果に記録します。

ここでの「ADEPS-test」は既存の独自TinyDenoiserによる推論です。参照生成・推論とも5次のモデルであり、論文の15次音場によるMismatched条件やParam法はこの図へ追加していません。図は1回の短い合成クリップの計算結果で、論文の多数のテスト信号の集計とは異なります。論文の曲線を複写した値でも、論文と同等の精度を証明した結果でもありません。

**English.** Each reconstruction now compares its fixed Linear baseline with the selected stored diffusion stage using frequency-dependent magnitude-spectrum error and magnitude-squared coherence. Stage changes, saved-run selection and process audition update the comparison. Switching diffusion OFF for playback does not replace the diffusion comparison curve with Linear. The spectrum-error axis is shared across all stored stages in that run; coherence is fixed to 0…1. The frequency axis spans 1 Hz…20 kHz, with actual non-DC data at 62.5 Hz…8 kHz. Uncomputed or undefined values remain blank. Inspect numerical values, export CSV, or retain every stage's `frequency_metrics` in the ZIP metadata.

The definitions follow [Gen-A Eq. (5)(6)](https://arxiv.org/html/2501.08047v1#S3.SS4), as cited by [ADEPS §4/Fig.1](https://arxiv.org/html/2608.24558v3#S4). Magnitude error averages the absolute dB-magnitude discrepancy over time and FOA channels. MSC computes temporal cross-power per channel before channel averaging. Evaluation uses uncompressed FOA STFTs after real-wave endpoint projection and before export gain. This is not the compressed denoiser benchmark or complex NRMSE.

The original equations do not specify zero handling. Our extension applies a common reference-peak ×10⁻¹² magnitude floor, marks silent reference frequencies undefined, and uses the same reference-active channel set for all methods' MSC. A zero-energy estimate in any of those channels makes that frequency's MSC undefined rather than averaging only the remaining channels. Inspect the recorded floor/counts. These are single synthetic-clip results from the independent tiny model with matched order-5 generation and inversion, not the paper's aggregate curves, Param baseline, or order-15 mismatched experiment.

### ノイズスケジュールの図（v0.5.3）

「ノイズスケジュール」で、横軸を完了したEuler更新の数（0〜M）、縦軸をノイズ尺度σとして表示します。予定の点は実装と同じ式から生成し、復元後に「復元Nの記録」を選ぶと、実行ログの `sigma` / `next_sigma` から直接表示します。現在の設定と保存結果は区別します。

```text
σ_i = [σ_max^(1/ρ) + i/(M−1) × (σ_min^(1/ρ) − σ_max^(1/ρ))]^ρ
       i = 0,…,M−1
σ_M = 0   （本実装で明示した最終更新先）
```

式は[ADEPSの式(11)](https://arxiv.org/html/2608.24558v3#S3.SS2)と、その参考文献[19]の[EDM](https://arxiv.org/abs/2206.00364)を参照しています。現在は推論開始σ=20、最後の正σ=0.002、ρ=10を固定し、UIの推論ステップ数M（8〜80）に合わせて離散点が変わります。M個の正のノイズ水準＋終端0で、更新はM回です。学習で使ったσ分布は別で、[学習記録](MODEL_TRAINING.md)に記載しています。

縦軸は対数／通常目盛を切り替えられます。対数ではσ=0を軸上の小さな正値に置き換えず、終端として別に表示します。点を選ぶとσ、次のσ、差分を確認でき、全点のCSVを書き出せます。保存済みの復元段階に対応する点だけ「この時点の復元を見る」から3D音場と試聴対象を選択できます。保存していない中間点の音は作りません。

σは正規化・圧縮した係数領域のノイズ尺度です。録音時間（秒）、マイク観測のSNR、再生音に実際に残るノイズ量、推定精度そのものではありません。図が0へ到達しても完全な復元を意味しません。

**English.** The **Noise schedule** view plots completed Euler updates (0…M) against the scheduled noise scale σ. **Current settings** calculates the planned points using the same formula; **Run N record** reads the actual `sigma`/`next_sigma` execution trace. Inference fixes σmax=20, σmin=0.002 and ρ=10, while M follows the existing 8–80-step control. M positive levels plus an explicit terminal zero give M Euler updates. Training-noise sampling is separate.

Switch between logarithmic and linear sigma axes. Zero is shown separately from the logarithmic axis, never clamped to a positive value. Inspect a point and export all schedule rows to CSV. Only steps with stored reconstructions offer **View this reconstruction**, selecting the corresponding existing 3D and audio output. Sigma is a normalized compressed-coefficient noise scale, not playback seconds, microphone SNR, measured residual audio noise or a reconstruction-accuracy score.

### 学習済みノイズ除去器の精度を確認する（v0.5.3）

画面下部の「学習済みノイズ除去器の検証」は、同梱の `tiny-spatial-v1` の重みを固定して行った**1回のノイズ除去の評価**です。推論の反復回数、最終FOAの誤差、部屋の測定精度とは異なります。ノイズスケジュールが下がるだけでは、精度の改善を確認したことにはなりません。

- **正解データ**：学習と同じ生成方法から、別のseed（17319）で生成した2,048個の5次・36複素係数ベクトル。学習48,000個のseed 7319、元の検証2,048個のseed 7320とは別です。実録音や別の部屋を分けた検証ではありません。
- **入力**：圧縮した正解 `H(a)` の実部・虚部へ、それぞれ標準偏差σの正規ノイズを加えます。ノイズseedは17320。全σ・全手法で同じ正解と標準ノイズを使います。
- **比較**：未処理の入力、`σdata²/(σdata²+σ²)` 倍する単純ガウス縮小、学習済みモデルの3種類。縮小法のσdataは学習済みカードの固定値を使い、検証データに合わせて調整しません。正解は入力の生成と採点に使い、除去器へ追加情報として渡しません。
- **条件**：σ = 0.002, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 20, 80。80は学習ノイズの範囲内ですが、現在のスタジオの推論範囲（σ≤20）外です。周波数Hzの比較ではありません。
- **指標**：NRMSEは全2,048×36複素係数をまとめた `20 log10(‖推定−正解‖₂/‖正解‖₂)` で、小さいほど良好です。MSEは実部・虚部を別の座標として、誤差の二乗和を `2×2,048×36` で割ります。いずれも圧縮した係数領域の値です。

グラフ・σ選択・全条件の表・JSONで確認できます。差の符号は **単純縮小のNRMSE − 学習済みのNRMSE** なので、正が改善、負が悪化です。重みのSHA-256が現在のモデルカードと一致しない記録は、現在の精度として表示しません。seed、評価コード、生成・学習コード、推論コードとそのハッシュも保存します。

**今回の結果**：未処理から改善したのは10条件中7条件ですが、単純ガウス縮小からの改善は3条件です。最大でもσ=1で約 **0.033 dB**、残り7条件は悪化しました。単純縮小との差は全条件で0.1 dB未満です。これを大きな学習効果や論文同等の性能とは解釈できません。σごとの結果は同じベクトルとノイズを使うため、独立した10回の試験でもありません。

この更新では重みの再学習や最適化は行っていません。独立した合成ベクトルへの評価であり、声・音楽・残響・時間方向の連続性・実マイクの応答V・会場録音は未評価です。実際の逆推定では観測から正規化するため、この学習領域の評価と分布が一致する保証もありません。[評価JSON](../public/models/tiny-denoiser-evaluation.json)と[評価コード](../scripts/evaluate_tiny_denoiser.py)を参照してください。

**English.** The **Trained denoiser validation** panel evaluates one direct call to the frozen `tiny-spatial-v1` denoiser on 2,048 newly generated fifth-order coefficient vectors. Generator seed 17319 and noise seed 17320 are separate from the original training/validation seeds. Data come from the same procedural family as training, not held-out rooms or recordings. Independent Gaussian noise is added to each real and imaginary coordinate of `H(a)`; the same clean targets and standard noise are reused at ten sigma values from 0.002 to 80.

Compare unchanged noisy input, Gaussian shrinkage using the model card's fixed σdata, and the learned denoiser. Aggregate complex NRMSE in dB and MSE per real coordinate are reported in the compressed domain. Positive **shrinkage NRMSE minus learned NRMSE** means improvement. The UI verifies the weight hash against the bundled model card and exposes all conditions, seeds, code hashes and the downloadable record. Sigma 80 lies outside the studio's usual inference range.

The trained denoiser improved over noisy input at 7/10 tested levels, but over simple shrinkage at only 3/10. Its largest gain over shrinkage was approximately 0.033 dB at σ=1; it regressed at the other seven levels. All differences were below 0.1 dB. This update evaluates existing weights without retraining and does not establish paper-level performance, final inverse-problem accuracy, temporal consistency, or improvement on speech, music, microphones or real rooms.

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

**「復元過程を続けて聴く」（v0.5.3）** は、復元後に「過程を再生」を押すと、保存済み中間点から最終出力へ順に進みます。同じ短い音を各段階で1・2・4回（既定2回）繰り返すため、推定による音の変化を聴き比べられます。選択中の段階・指標・3D表示が再生位置に追従します。再生開始時に音場表示へ移りますが、途中でノイズスケジュールへ切り替えると、実行ログ上の対応する保存点でも進行を確認できます。

全段階に共通のゲインを適用し、各短音の両端だけ約5 msフェードします。段階同士を重ねたり、各段階を別々に音量正規化したりしません。「停止」、個別試聴、段階の手動選択、再計算、別の履歴やタブへの移動で連続試聴を停止します。自動再生はありません。**保存した推定の順次試聴であり、現場の音へリアルタイムに適応したり、その場で学習したりする機能ではありません。** σの進行は音声内の時間とは異なります。初期の推定が弱い音、ノイズ、音色の変化として聞こえても、改善は参照誤差と別に判断します。

**English.** After a reconstruction, **Play the process** sequences stored intermediate estimates through the final output. Repeat each short clip once, twice (default), or four times. The stage selector, metrics and 3D display follow audio playback; switching to the saved noise-schedule view shows the corresponding stored step. Every clip uses the same gain and approximately 5 ms edge fades, without overlapping different reconstructions or individually normalizing them. Stop, manual audition/stage selection, recomputing, changing runs, or leaving the tab cancels the sequence. Playback requires an explicit click. This auditions saved estimates, not live acoustic adaptation or online learning; diffusion sigma is not audio time.

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
