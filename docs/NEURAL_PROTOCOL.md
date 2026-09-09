# Neural experiment — implementation and field-test protocol

Version 0.3, 10 September 2026. This is an **independent equation test with a small trained prior**, not the authors' implementation or a reproduction of their reported results.

## 日本語：最初の使い方

1. 「ニューラル推論」→「合成データで試す」→「推論して比較する」。マイク不要です。
2. 線形と推論のFOA誤差、coherence、反復ごとの残差を確認します。悪化した結果も表示します。
3. 「合成WAV例を選ぶ」でもう一度実行すると、比較用の4ch WAVを保存できます。
4. 自分の録音は、同時刻の4ch以上の `microphones.wav` と、対応する `array.json` をZIP直下に入れます。別時刻に1本のマイクを動かした録音は、一般の時間変化する音場の同時アレイ観測を置き換えません。
5. まず16 kHz・0.4秒の区間で計算します。長い録音でも開始時刻を変えて選択できます。入力ZIPは圧縮前後32 MB、1回の推論は8192周波数時間点までです。処理時間は実際の計算結果に記録します。
6. 線形・推論を同じAmbisonicsデコーダと同じ再生ゲインで比較します。FOAの4chは4台のスピーカー出力ではありません。スピーカーのIR計測や音場補正とは別の実験です。

同梱モデルは48,000個の合成空間係数で学習した24,072パラメータのMLPです。論文の30.8MパラメータNCSN++M、HARP/VCTK音声学習、WSJ0評価は再現していません。実際の発話・残響・機器で改善する保証はありません。著者の公開リポジトリは2026-09-10の確認時点でREADMEのみです。

## 1. Source and status

[1] Amit Milstein, Nir Shlezinger, Boaz Rafaely. **Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling**, arXiv:2608.24558v2, 2026. [Paper](https://arxiv.org/abs/2608.24558v2), [full text](https://arxiv.org/html/2608.24558v2), [DOI](https://doi.org/10.48550/arXiv.2608.24558).

[2] Authors' [ADEUPS repository, inspected revision 5076f163a1f939c297b55a39b2d9d33e2b224a5f](https://github.com/Amitmils/ADEUPS/tree/5076f163a1f939c297b55a39b2d9d33e2b224a5f). README only when rechecked on 10 September 2026. No official checkpoint, full network, or reproducible configuration was available.

[3] Tero Karras et al. **Elucidating the Design Space of Diffusion-Based Generative Models**, 2022. [Paper](https://arxiv.org/abs/2206.00364). The small test model independently implements EDM-style preconditioning and weighted denoising loss. No code from the NVIDIA repository is copied.

## 2. Equation-to-code mapping

All tensors in this application use **[F,C,T]** or **[F,Q,T]**, whereas the paper writes microphone observations with Q first. `C=36`, prior order 5. Evaluation and audio export use only the first four FOA coefficients. This does not establish recovery of all 36 coefficients from four microphones.

| Paper | Implementation in `backend/neural.py` |
|---|---|
| Eq. (5) | `capture.encode`: E = Vᴴ(VVᴴ+γ²I)⁻¹; the same order-5 E is used for the warm observation and this experiment's linear comparison |
| §3.1 compression | `compress` / `expand`: H(z)=β|z|^α exp(i arg z), α=.67, β=3 |
| Eq. (10) | `consistency`: A(x)=H(EV H⁻¹(x)); y=H(Ep / observation_scale) |
| Eq. (9), Algorithm 1 | Full real-Euclidean derivative of ‖A(Dθ(x,σ))−y‖² **through Dθ**, H⁻¹, EV, H |
| Score | (Dθ(x,σ)−x)/σ² |
| Guidance | −η′ grad / (σ‖grad‖₂); one norm over all real/imaginary F,C,T coordinates |
| Eq. (11) | 150 positive rho-spaced sigmas, 20 to .002, rho=10 |
| Algorithm 1 Euler step | x_next = x − σ(σ_next−σ)(score+guidance) |
| Output | H⁻¹(x_final) × observation_scale; truncate to FOA |

The likelihood is in **compressed linearly encoded space**, not simply the microphone residual. The UI reports both separately. Its trace evaluates Dθ before each Euler update; the final encoded residual is recomputed on the final output.

Tests compare the complete likelihood derivative with finite differences, including the network derivative, at several noise levels. This is a numerical validation of this implementation, not a claim that the authors used identical details.

## 3. Explicit independent choices

- **Network:** two 96-wide SiLU layers, 72 real/imaginary coordinates + 8 sine/cosine log-sigma features; 36 complex outputs. It processes each time-frequency bin independently. It has **no temporal or frequency context**, unlike the paper's NCSN++M.
- **EDM preconditioning:** c_in=1/sqrt(σ²+σ_data²), c_skip=σ_data²/(σ²+σ_data²), c_out=σσ_data/sqrt(σ²+σ_data²). σ_data is estimated from training real/imaginary coordinates and saved in the card. It is not an assertion of the paper's exact preconditioning convention.
- **Training:** 48,000 independent procedural coefficient vectors, 1–2 direct plane waves plus 3 weak random rays; real ACN/N3D, random direction, phase and gain. These are not 48,000 rooms or speech scenes. There is no microphone array in the training input. Validation uses 2,048 separately generated vectors with another seed. No HARP, VCTK, WSJ0, real recordings, or external pretrained weights are used.
- **Optimization:** 4,000 steps, batch 512, AdamW, lr=.001, weight_decay=.0001; noise sigma sampled log-uniformly from .002 to 80. Weighted loss λ=(σ²+σ_data²)/(σσ_data)². This sampling/training configuration is our choice, not the paper's released training recipe.
- **Input scale:** one scalar RMS of E·p over the whole inference segment; divide before compression and restore afterwards. The reference signal never sets the scale or enters inference. This normalization does not guarantee the same amplitude distribution as training.
- **SH:** real ACN/N3D; FOA order W,Y,Z,X. The modelled freefield V uses the prototype's exp(+ikr·d) convention. Device response, coordinates, source-direction convention and recorded channels must agree. This does not identify the paper's unpublished exact conventions.
- **γ²:** max(relative_regularization × trace(VVᴴ)/Q, 1e−12) separately by frequency, default relative_regularization=.001.
- **η′:** default 50, adjustable 0–1000. It is not published in the source. A fixed η′ with a global normalized gradient has a different relative influence for different segment sizes; record and compare settings. 0 disables observation guidance for an ablation.
- **Warm noise:** independent real and imaginary Normal(0,σ_max²) coordinates. The paper does not resolve all complex-network representation details.
- **Endpoint:** append zero to the M positive sigma points and perform exactly M updates. This explicitly resolves the paper's final-index ambiguity; it is not presented as the authors' endpoint rule.
- **At zero:** H is extended linearly for |z|≤1e−8, with a matching inverse. This avoids an undefined derivative at zero. Outside that tiny neighborhood, the cited radial power law is unchanged. A gradient norm≤1e−20 produces zero guidance.
- **No invented quality guarantees:** small-model inference may be worse than linear estimation. No parameter was selected to claim the paper's numerical gains. One synthetic example is not a room or speech evaluation.

Weights are safe numeric NPZ (no pickle loading) and verified against SHA-256 in `public/models/tiny-spatial-v1.json`. The card records initialization seed, data generation, objective, parameters, optimization log and validation values before/after training. The result records its hash and the observation/transfer hash.

Training is reproducible with `python3 scripts/train_tiny_prior.py` in an environment with PyTorch, NumPy and SciPy. Inference requires only NumPy and SciPy, including in the browser. `--hoa-npz` can train the **same independent architecture** on user-supplied clean [samples,36] complex coefficients (a_real/a_imag). It performs a random-vector validation split; a proper room/speaker-separated research evaluation must be prepared separately. The saved model remains an independent MLP, with no promise of compatibility with future official checkpoints.

## 4. Input formats

### Complex JSON

`schema: adeps-test-array-stft/1`, `sh_ordering: ACN`, `sh_normalization: N3D`.

- `frequencies_hz`: nonnegative increasing [F].
- `V_real`, `V_imag`: [F,Q,36], the acquisition model of the microphones, not a speaker-to-listener response matrix.
- `p_real`, `p_imag`: [F,Q,T], recorded or simulated microphone STFTs.
- Optional `reference_real`, `reference_imag`: aligned [F,4,T] or [F,36,T] clean Ambisonics; only FOA evaluated.
- Optional `microphone_positions_m`: [Q,3], matching the WAV/STFT channel order.
- `provenance`: describe recorded/synthetic origin, array, conventions and calibration.

Unknown normalization, fewer than four microphones, non-finite values, silence, or a four-coefficient V are rejected. Missing high-order transfer columns cannot be recovered by zero-padding. At least four microphones are necessary for FOA; geometry and frequency-dependent rank also matter. At DC, the freefield model cannot resolve all FOA components.

### WAV ZIP

At ZIP root: `array.json`, `microphones.wav`, and optional `reference.wav`. The WAV must be one synchronous multichannel recording, 4–64 channels at 8–96 kHz. Optional reference is four-channel real ACN/N3D with exactly the same original sample rate, sample count and timing. A stereo file is not a microphone array.

`array.json` uses `schema: adeps-test-array-audio/1`. See the downloadable template. Choose either:

- **Supplied V**: V_real/V_imag and frequencies_hz must exactly match the STFT grid. No silent interpolation, geometry guessing, or calibration is performed.
- **Modelled V**: explicit `array_model: freefield-omnidirectional` and one finite XYZ position in metres per channel. This assumes omni sensors in free space, with no scattering body or device transfer. Do not label this as a measured response of a commercial array. Cardioid handheld microphones are not described by this model.

Default analysis is 16 kHz, FFT 256, periodic Hann, hop 128, scipy `scaling=spectrum`, zero boundary padding. Other supported rates: 8/24/48 kHz; FFT 128/512/1024 with half-window hop. Resampling, if needed, uses scipy resample_poly and is recorded. The selected segment is processed independently; context beyond its boundaries is not used. Both methods share this STFT. These settings are explicit prototype choices, not documented ADEPS paper values.

Maximum 8192 F×T bins, ZIP 32 MB compressed/uncompressed. Start with .4 s at 16 kHz. Short-window/segment boundary effects limit interpretation. This version does not stitch long recordings, denoise live, or claim speech restoration quality.

Local offline equivalent:

```sh
python3 scripts/infer_audio.py input.zip new_result.zip --start 0 --duration .4 --steps 150 --eta 50 --seed 42
```

No audio device is opened. Existing output files are preserved by requiring a new filename.

## 5. Results and playback

- Complex NRMSE: 20 log10(‖estimate−reference‖/‖reference‖), aggregated across FOA and displayed by frequency; lower is better. This is our complex error, **not** the paper's log-magnitude spectral error metric.
- Coherence: magnitude-squared complex cross-time correlation, averaged over valid channel/frequency pairs. Zero-energy pairs are excluded and counted.
- WAV SI-SDR: zero-mean time signals, least-squares scalar projection separately per FOA channel; arithmetic mean of valid channel scores. Exact paper aggregation is not asserted. No reference means no reference-quality scores.
- Residuals, FOA rank, input levels, actual elapsed seconds and every Euler-step diagnostic are retained. These do not prove perceptual quality.
- Output ZIP contains result.json plus linear/neural/reference FOA WAVs (reference only if supplied). All files share **one scalar output gain**: min(1,.95/max_peak) over the N3D comparison signals. No method is independently normalized. Raw complex output in JSON remains unscaled. WAVs are 32-bit float.
- For real waveform synthesis, DC and Nyquist are projected to real values before iSTFT. Arbitrary reconstructed spectra may be STFT-inconsistent; the overlap-add waveform is the exported audio. Complex-STFT quality and waveform SI-SDR are therefore different checks.
- Both ACN/N3D and ACN/SN3D versions are included. FOA conversion is diag(1,1/√3,1/√3,1/√3), keeping W,Y,Z,X order.
- Use the same correctly configured Ambisonics decoder in Max/Spat or another host for A/B playback. Four FOA coefficients are **not** four speaker feeds. No loudspeaker decoding, binaural HRTF, Dante mapping, automatic device configuration or live audio output is performed by this inference tool.

The existing Max channel-test bridge is a separate routing check; it is not the neural inference host. Saved results can be compared offline without a live microphone. To test the actual acoustical capture at a venue, first prepare the synchronous array recording and a valid acquisition response V. A single measurement microphone used for loudspeaker IRs serves a different purpose.

## 6. What remains required for a paper reproduction

Official network/configuration, licensed weights, exact STFT and complex conventions, acquisition models, gamma/eta and endpoint settings, training/evaluation splits, and the authors' complete metric protocol. The current public assets do not provide these. The small model and equation sampler allow implementation tests now; they do not establish the paper's reported gains or field performance.
