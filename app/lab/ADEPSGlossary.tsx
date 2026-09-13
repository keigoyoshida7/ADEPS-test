import { useState } from 'react';
import { ExternalLink, Search, X } from 'lucide-react';
import './ADEPSGlossary.css';

type Category = 'representation' | 'model' | 'inference' | 'data' | 'evaluation';
type FullName = { short: string; english: string; japanese: string; kind?: 'name' | 'notation' | 'format'; source?: keyof typeof sources };
type Entry = { names?: FullName[]; term: string; jp: string; en: string; category: Category; ja: string; explanation: string; keywords?: string; source?: keyof typeof sources };
const sources = {
  paperSource: { title: 'ADEPS · LaTeX acronym definitions', url: 'https://arxiv.org/src/2608.24558v3' },
  formats: { title: 'ICST · Ambisonics conventions', url: 'https://ambisonics.ch/ambisonics-101/formats/' },
  acn: { title: 'FFmpeg · ACN / SN3D', url: 'https://ffmpeg.org/doxygen/trunk/group__lavu__audio__channels.html' },
  dps: { title: 'DPS · Chung et al.', url: 'https://arxiv.org/abs/2209.14687' },
  ncsn: { title: 'NCSN · Song & Ermon', url: 'https://yang-song.net/assets/pdf/NeurIPS2019/ncsn-poster.pdf' },
  ncsnm: { title: 'NCSN++M · Lemercier et al.', url: 'https://arxiv.org/abs/2211.02397' },
  adaln: { title: 'adaLN · Peebles & Xie', url: 'https://arxiv.org/abs/2212.09748' },
  wsj: { title: 'WSJ0 · LDC catalogue', url: 'https://catalog.ldc.upenn.edu/LDC93S6A' },
  stft: { title: 'STFT · SciPy documentation', url: 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.stft.html' },
  fft: { title: 'FFT · SciPy documentation', url: 'https://docs.scipy.org/doc/scipy/reference/fft.html' },
  msc: { title: 'MSC · SciPy documentation', url: 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.coherence.html' },
  rms: { title: 'RMS · MathWorks documentation', url: 'https://www.mathworks.com/help/matlab/ref/rms.html' },
  sha: { title: 'SHA-256 · NIST terminology', url: 'https://csrc.nist.gov/glossary/term/sha_256' },
  hrtf: { title: 'HRTF · SOFA specifications', url: 'https://sofacoustics.org/mediawiki/index.php/General_information_on_SOFA' },
  paper: { title: 'ADEPS · §§2–4', url: 'https://arxiv.org/html/2608.24558v3' },
  edm: { title: 'EDM · Karras et al.', url: 'https://arxiv.org/abs/2206.00364' },
  gena: { title: 'Gen-A · §III-D', url: 'https://arxiv.org/html/2501.08047v1#S3.SS4' },
  ambeo: { title: 'Sennheiser · A/B-format', url: 'https://docs.cloud.sennheiser.com/en-us/ambeo-vr-mic/manual-recording.html' },
  harp: { title: 'HARP · source', url: 'https://github.com/whojavumusic/HARP' },
  vctk: { title: 'VCTK 0.92 · dataset', url: 'https://datashare.ed.ac.uk/items/30e7453c-9ea8-48b4-8e18-f96d0dc62928/full' },
  sisdr: { title: 'SI-SDR · Le Roux et al.', url: 'https://arxiv.org/abs/1811.02508' },
  unet: { title: 'U-Net · Ronneberger et al. · §§1–2', url: 'https://arxiv.org/html/1505.04597v1' },
  fir: { title: 'FIR · SciPy documentation', url: 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.firwin.html' },
  adam: { title: 'Adam · Kingma & Ba · §1', url: 'https://arxiv.org/pdf/1412.6980' },
  adamw: { title: 'AdamW · Loshchilov & Hutter · §3', url: 'https://arxiv.org/html/1711.05101v3' },
  processors: { title: 'CPU / GPU · Intel', url: 'https://www.intel.com/content/www/us/en/products/docs/processors/cpu-vs-gpu.html' },
  mps: { title: 'MPS · Apple Developer', url: 'https://developer.apple.com/metal/pytorch/' },
  rt60: { title: 'RT60 · Pyroomacoustics documentation', url: 'https://pyroomacoustics.readthedocs.io/en/stable/pyroomacoustics.room.html#reverberation-time' },
};
const entries: Entry[] = [
  { term: 'ADEPS', jp: '拡散によるAmbisonicsエンコード', en: 'Ambisonics encoding through diffusion', category: 'model', keywords: '正式名称 頭字語 array agnostic',
    names: [{ short: 'ADEPS', english: 'Ambisonics Diffusion Encoding via Posterior Sampling', japanese: '事後サンプリングによるAmbisonicsの拡散エンコーディング', source: 'paperSource' }],
    ja: '論文のLaTeX原文で定義された名称です。論文タイトルは「Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling」。理想的な音場のpriorと観測モデルを組み合わせ、マイク信号からAmbisonics係数を推定します。',
    explanation: 'This expansion is explicitly defined in the paper’s LaTeX source. Its title is “Array-Agnostic Ambisonics Encoding via Diffusion Posterior Sampling.” The method combines an ideal sound-field prior with an observation model to estimate Ambisonics coefficients from microphone signals.', source: 'paper' },
  { term: 'EDM', jp: '拡散モデルの設計を整理した枠組み', en: 'A framework for diffusion-model design', category: 'model', keywords: '正式名称 デザイン 拡散前処理 preconditioning',
    names: [{ short: 'EDM', english: 'Elucidating the Design Space of Diffusion-Based Generative Models', japanese: '拡散生成モデルの設計空間を明らかにする（参照論文の題名）', kind: 'name', source: 'edm' }],
    ja: 'Karrasらの論文と、その設計枠組みを指す名前です。この実装では入力・出力の尺度調整、ノイズ条件づけ、学習損失などを参照します。EDMを別の推測した英語に展開するのではなく、参照元の論文名を示しています。',
    explanation: 'EDM identifies the Karras et al. paper and design framework. This implementation references its input/output preconditioning, noise conditioning and loss formulation. The source paper title is given here rather than assigning an invented word-by-word expansion.' },
  { term: 'SNR / dB / SPL', jp: '信号と雑音の比、対数単位、音圧レベル', en: 'Signal-to-noise ratio, logarithmic unit and sound pressure level', category: 'evaluation', keywords: '信号対雑音比 デシベル 音圧',
    names: [{ short: 'SNR', english: 'Signal-to-Noise Ratio', japanese: '信号対雑音比', source: 'paperSource' }, { short: 'dB', english: 'decibel', japanese: 'デシベル（比を対数で表す単位）', kind: 'notation' }, { short: 'SPL', english: 'Sound Pressure Level', japanese: '音圧レベル' }],
    ja: 'SNRは信号のエネルギーと雑音のエネルギーの比です。仮想観測のSNRを下げると雑音が増えます。dBは比の単位で、dBと書かれているだけでは音圧を意味しません。SPLは基準音圧に対する音圧レベルで、このUIのσや正規化した再生ゲインとは別です。',
    explanation: 'SNR compares signal energy with noise energy. Lower virtual-observation SNR adds more noise. Decibels express a ratio and do not inherently mean sound pressure. SPL refers to pressure relative to a reference; it is distinct from sigma and normalized playback gain in this UI.' },
  { term: 'W / X / Y / Z', jp: '1次Ambisonicsの成分記号', en: 'First-order Ambisonics component labels', category: 'representation', keywords: '無指向 左 前 上 omnidirectional front left up ACN',
    names: [{ short: 'W, X, Y, Z', english: 'Omnidirectional and Cartesian directional components', japanese: '無指向成分と直交3軸の方向成分', kind: 'notation' }],
    ja: '単語の頭字語ではなく、球面調和成分の記号です。本実装ではWが0次の無指向成分、Xが前、Yが左、Zが上の方向成分。保存順序はACNに従いW,Y,Z,Xです。各文字はスピーカーの出力チャンネル名ではありません。',
    explanation: 'These are spherical-harmonic component labels, not word acronyms. Here W is the order-zero omnidirectional component; X, Y and Z correspond to front, left and up. ACN storage order is W,Y,Z,X. These labels do not identify loudspeaker output channels.' },
  { term: 'WSJ0 / CSR-I', jp: '原著の評価用音声コーパス', en: 'The original paper’s evaluation speech corpus', category: 'data', keywords: 'Wall Street Journal ウォールストリートジャーナル 音声認識',
    names: [{ short: 'WSJ0', english: 'Wall Street Journal corpus · WSJ0', japanese: 'Wall Street Journalの記事などを読み上げた最初のWSJ音声コーパス', kind: 'name', source: 'wsj' }, { short: 'CSR', english: 'Continuous Speech Recognition', japanese: '連続音声認識', source: 'wsj' }],
    ja: '正式な配布名は「CSR-I (WSJ0) Complete」。WSJは新聞名、0はコーパスの識別です。本実装のテストは別話者のVCTKを使っているため、原著のWSJ0評価と同じ条件ではありません。',
    explanation: 'The catalogue title is “CSR-I (WSJ0) Complete.” WSJ refers to the newspaper and 0 identifies the corpus. This implementation evaluates on held-out VCTK speakers, so it does not reproduce the original WSJ0 evaluation conditions.' },
  { term: 'Ambisonics / FOA / HOA', names: [{"short": "FOA", "english": "First-Order Ambisonics", "japanese": "1次Ambisonics", "source": "formats"}, {"short": "HOA", "english": "Higher-Order Ambisonics", "japanese": "高次Ambisonics（High-Order Ambisonicsとも表記）", "source": "paper"}, {"short": "SH", "english": "Spherical Harmonics", "japanese": "球面調和関数", "source": "paperSource"}], jp: '音場を係数で表す', en: 'Represent a sound field with coefficients', category: 'representation', keywords: 'アンビソニックス 球面調和関数 spherical harmonics',
    ja: '周囲の音を方向の基底に分けた表現です。FOAは1次の4成分、HOAはより高次の表現。このUIの学習priorは5次ですが、3D表示と4ch音声の比較は先頭のFOA成分を使います。',
    explanation: 'A representation of surrounding sound using directional basis functions. FOA has four first-order components; HOA includes higher orders. The prior uses order 5, while the 3D view and four-channel audio comparison use its first-order components.', source: 'paper' },
  { term: 'N5 · 36 complex / 72 real', names: [{"short": "N = 5", "english": "Ambisonics order N equals five", "japanese": "Ambisonics次数Nが5という記法", "kind": "notation"}], jp: '5次・36複素成分・72実数成分', en: 'Order 5, 36 complex and 72 real coordinates', category: 'representation', keywords: '次数 チャンネル channels',
    ja: '3次元Ambisonicsの成分数は(N+1)²。5次では36です。STFT上の各成分は実部と虚部を持つため、ネットワークでは36＋36の72実数チャンネルとして扱います。72台のマイクを意味しません。',
    explanation: 'Three-dimensional Ambisonics has (N+1)² components: 36 at order 5. Each STFT coefficient has a real and imaginary part, packed as 36+36 real network channels. This does not mean 72 microphones.', source: 'paper' },
  { term: 'ACN / N3D / SN3D', names: [{"short": "ACN", "english": "Ambisonic Channel Number", "japanese": "Ambisonicsチャンネル番号", "source": "acn"}, {"short": "N3D", "english": "Full 3D Normalisation", "japanese": "3次元の完全正規化", "source": "formats"}, {"short": "SN3D", "english": "Schmidt Semi-Normalised 3D", "japanese": "3次元のSchmidt半正規化", "source": "formats"}], jp: '成分の順序と大きさの規約', en: 'Channel ordering and normalization', category: 'representation', keywords: 'W Y Z X SN3D FuMa',
    ja: 'ACNは成分の並び、N3Dは球面調和関数の正規化です。本実装の先頭4成分はW,Y,Z,X。SN3Dではスケールが、FuMaでは順序やスケールが異なるため、規約を確認して変換します。',
    explanation: 'ACN specifies ordering; N3D specifies spherical-harmonic normalization. This implementation starts with W,Y,Z,X. SN3D differs in scaling; FuMa differs in ordering and scaling. Check the conventions and convert explicitly.' },
  { term: 'A-format / B-format', names: [{"short": "A-format / B-format", "english": "A-format / B-format", "japanese": "カプセル信号形式／Ambisonics信号形式（AとBは形式名）", "kind": "format", "source": "ambeo"}], jp: 'カプセル信号と音場の表現', en: 'Capsule signals and a sound-field representation', category: 'representation', keywords: 'Aフォーマット Bフォーマット raw 生信号',
    ja: 'A-formatは機種に依存するカプセルの信号、B-formatはAmbisonicsへ変換した信号です。B-formatにできることと、ADEPSで必要な応答Vが入手できることは別です。変換後も次数・順序・正規化を確認します。',
    explanation: 'A-format contains device-specific capsule signals; B-format contains encoded Ambisonics. Having a B-format converter does not itself provide the response V needed by ADEPS. Order, channel ordering and normalization still need to be identified.', source: 'ambeo' },
  { term: 'Array / geometry', jp: '複数マイクの位置関係', en: 'The positions of multiple microphones', category: 'representation', keywords: 'アレイ 半径 radius 座標 3D',
    ja: 'アレイは複数の受音点の組です。仮想テストでは数・半径・座標から応答を計算でき、実物のマイクは不要です。実録音を推定する場合は、その録音装置に対応する応答が別途必要です。',
    explanation: 'An array is a collection of sound-receiving positions. Synthetic tests calculate responses from count, radius and coordinates without physical microphones. Processing a real recording requires a response appropriate to that recording device.' },
  { term: 'V / ATF', names: [{"short": "ATF", "english": "Array Transfer Function", "japanese": "アレイ伝達関数", "source": "paperSource"}, {"short": "V", "english": "Modal steering matrix", "japanese": "Ambisonics係数をマイク観測へ写す行列の記号", "kind": "notation", "source": "paper"}], jp: '音場が観測信号へ変わる関係', en: 'How sound-field coefficients become observations', category: 'inference', keywords: '応答 steering matrix transfer matrix 伝達関数 velocity',
    ja: 'このUIのVは、周波数ごとにAmbisonics係数aをマイク信号pへ写す行列です（p≈Va）。録音そのものでも、速度velocityのVでもありません。実機では方向・振幅・位相を含む応答や機器モデルから求めます。',
    explanation: 'Here V maps Ambisonics coefficients a to microphone signals p at each frequency (p≈Va). It is neither the recording itself nor velocity. For a real device, it is derived from directional amplitude/phase responses or an appropriate device model.', source: 'paper' },
  { term: 'Linear / regularization', jp: '線形推定と正則化', en: 'Linear estimation and regularization', category: 'inference', keywords: '線形法 λ lambda γ gamma Linea アンプ',
    ja: '観測信号とVから、学習なしの逆計算で係数を求める比較基準です。正則化は不安定な逆計算による雑音増幅を抑える調整。Linearは数学の「線形」で、Lineaという機器やアンプの名前ではありません。',
    explanation: 'The untrained inverse calculation from observations and V provides a baseline. Regularization limits noise amplification in an unstable inverse. “Linear” refers to the mathematical method, not a Linea amplifier or device.', source: 'paper' },
  { term: 'Prior', jp: '学習した音場の特徴', en: 'Learned tendencies of sound fields', category: 'model', keywords: '事前分布 プライアー',
    ja: '理想係数にはどのような構造が現れやすいかを学んだ情報です。大きいモデルは音声と残響の時間・周波数構造を学習します。マイクの位置やVを記憶させるモデルではありません。',
    explanation: 'A prior describes structures likely to occur in ideal coefficients. The large model learns time–frequency patterns of speech and reverberation. Microphone positions and V are not inputs to its training.', source: 'paper' },
  { term: 'Denoiser Dθ', names: [{"short": "Dθ", "english": "Denoiser parameterized by θ", "japanese": "パラメータθを持つノイズ除去器の記号", "kind": "notation"}], jp: '雑音を加えた係数から推定するモデル', en: 'A model that estimates clean coefficients', category: 'model', keywords: 'デノイザー ノイズ除去',
    ja: '現在の係数とノイズ強度σを受け取り、理想係数を推定するネットワークです。中間のDθの出力は「推定」であり、正解や実際のマイク信号ではありません。',
    explanation: 'The network receives current coefficients and noise scale sigma, then estimates clean coefficients. An intermediate Dθ output is an estimate, not ground truth or an actual microphone signal.', source: 'paper' },
  { term: 'Diffusion / DPS', names: [{"short": "DPS", "english": "Diffusion Posterior Sampling", "japanese": "拡散事後サンプリング", "source": "dps"}], jp: 'priorと観測を使う反復復元', en: 'Iterative reconstruction with a prior and observations', category: 'inference', keywords: '拡散 ディフュージョン Posterior Sampling',
    ja: '雑音を含む初期状態から、ノイズ除去と観測との整合を繰り返して推定します。ここでいう「拡散」は計算手法であり、部屋の音の拡散度を直接測る機能ではありません。',
    explanation: 'Starting from a noisy state, sampling repeatedly combines denoising and consistency with observations. “Diffusion” names the computational method; it does not directly measure acoustic diffuseness in a room.', source: 'paper' },
  { term: 'H / compression', names: [{"short": "H", "english": "Element-wise magnitude-compression operator", "japanese": "成分ごとの振幅圧縮を表す演算子の記号", "kind": "notation"}], jp: '係数の大きさを扱いやすくする変換', en: 'A magnitude transform for network coordinates', category: 'model', keywords: '圧縮 α alpha β beta',
    ja: '位相を保ち、振幅をβ|a|^αに変換します。この実装はα=0.67、β=3。音声ファイルの容量を減らす圧縮ではありません。大型priorでは学習データ由来の共通スケールも使います。',
    explanation: 'H preserves phase and maps magnitude to beta|a|^alpha, here alpha=0.67 and beta=3. It is not file-size compression. The full-size prior also uses a common scale derived from training data.', source: 'paper' },
  { term: 'σ · sigma', names: [{"short": "σ", "english": "sigma · noise standard deviation", "japanese": "シグマ・雑音の標準偏差を表す記号", "kind": "notation"}], jp: 'モデルの座標上のノイズ強度', en: 'Noise scale in model coordinates', category: 'inference', keywords: 'シグマ ノイズ SNR SPL 音圧',
    ja: '圧縮・正規化した係数へ加える雑音の標準偏差です。マイクのSNR、dB SPL、音量、秒数ではありません。ノイズスケジュールのσ=0はこの試作の終端で、対数軸には載せられません。',
    explanation: 'Sigma is the standard deviation of noise added in compressed, normalized coefficient coordinates. It is not microphone SNR, dB SPL, volume or seconds. Terminal sigma=0 is shown separately because zero has no logarithm.', source: 'edm' },
  { term: 'ρ · rho / noise schedule', names: [{"short": "ρ", "english": "rho · noise-schedule spacing parameter", "japanese": "ロー・ノイズ段階の刻み方を決める記号", "kind": "notation"}], jp: 'ノイズを下げる刻み方', en: 'Spacing of the noise levels', category: 'inference', keywords: 'ロー スケジュール',
    ja: 'ρは、最大から最小までのσの並び方を決めます。現在はρ=10。ステップ番号は完了した更新数で、スケジュール全体は曲の再生時間を表していません。',
    explanation: 'Rho controls how sigma levels are spaced between their maximum and minimum; the current setting is 10. Step numbers count completed updates. The schedule is not an audio timeline.', source: 'edm' },
  { term: 'η′ · guidance', names: [{"short": "η′", "english": "eta prime · observation-guidance strength", "japanese": "エータ・プライム・観測拘束の強さを表す記号", "kind": "notation"}], jp: '観測との整合を求める強さ', en: 'Strength of observation guidance', category: 'inference', keywords: 'eta エータ ガイダンス',
    ja: '推定した係数をVで観測側へ戻し、実際の入力と合うように促す更新の強さです。大きいほど良いとは限りません。0でもpriorによる復元は動き、Linearそのものにはなりません。初期状態は観測を使ったwarm startなので、0でも観測の影響は残ります。',
    explanation: 'Guidance controls the update that brings a reconstructed observation closer to the input through V. Larger is not necessarily better. Zero disables this guidance but leaves prior sampling active; it does not become Linear. The observation-dependent warm start retains input information even with guidance set to zero.' },
  { term: 'Seed', jp: '乱数を再現する番号', en: 'A number used to reproduce randomness', category: 'inference', keywords: 'シード ランダム observation seed diffusion seed',
    ja: '同じ条件で乱数を再現するための番号です。現在の音声・部屋は固定で、観測seedは観測雑音だけ、拡散seedは復元の初期雑音を変えます。復元seedだけを変えれば、同じ観測で推定のばらつきを比べられます。',
    explanation: 'A seed reproduces random draws under the same configuration. In the current fixed speech/room scene, the observation seed changes only observation noise; the diffusion seed changes initial sampling noise. Changing only the diffusion seed compares estimates from the same observation.' },
  { term: 'Steps / saved stages', jp: '更新回数と保存された途中の推定', en: 'Updates and saved intermediate estimates', category: 'inference', keywords: 'ステップ checkpoint snapshot チェックポイント',
    ja: 'Stepsは反復計算の回数です。画面の途中段階は保存されたDθの推定、最後の点は終端更新後の結果。すべての更新点に音声が保存されているわけではありません。途中音の連続試聴は保存済み推定の順番再生です。',
    explanation: 'Steps count numerical updates. Saved intermediate stages are denoiser estimates; the final point is the sample after the terminal update. Not every update has saved audio. Process audition plays those saved estimates sequentially.' },
  { term: 'STFT', names: [{"short": "STFT", "english": "Short-Time Fourier Transform", "japanese": "短時間フーリエ変換", "source": "stft"}, {"short": "FFT", "english": "Fast Fourier Transform", "japanese": "高速フーリエ変換", "source": "fft"}, {"short": "iSTFT", "english": "Inverse Short-Time Fourier Transform", "japanese": "逆短時間フーリエ変換", "source": "stft"}], jp: '音を時間と周波数に分ける', en: 'Split audio into time and frequency', category: 'representation', keywords: '短時間フーリエ変換 FFT hop ホップ 窓',
    ja: '短い時間窓ごとに音を周波数成分へ変換します。FFTサイズが周波数の刻み、hopが窓を進める間隔です。このUIのモデルは振幅だけでなく位相を含む複素STFT係数を扱います。',
    explanation: 'The short-time Fourier transform decomposes short audio windows into frequency components. FFT size sets frequency spacing; hop sets how far the window advances. The model uses complex coefficients containing both magnitude and phase.' },
  { term: 'Sample rate / Nyquist / bandwidth', jp: 'サンプルレートと実データの帯域', en: 'Sample rate and the actual data band', category: 'representation', keywords: '周波数 ナイキスト 1Hz 20kHz 16000 16k FFT256 FFT512',
    ja: '16 kHz収録なら表現できる上限は8 kHzです。FFT512の周波数の刻みは31.25 Hz。図を1 Hz〜20 kHzまで広げても、その範囲のデータが増えるわけではありません。各結果の実周波数を確認します。',
    explanation: 'A 16 kHz sample rate has an 8 kHz Nyquist limit. FFT512 has 31.25 Hz spacing. Extending a plot to 1 Hz–20 kHz does not create data in that range. Check each result’s actual frequency grid.' },
  { term: 'HARP', names: [{"short": "HARP", "english": "HARP: A Large-Scale Higher-Order Ambisonic Room Impulse Response Dataset", "japanese": "大規模な高次Ambisonics室内インパルス応答データセット（研究の正式題名）", "kind": "name", "source": "harp"}], jp: '理想的な室内Ambisonics応答の生成', en: 'Generate ideal room Ambisonics responses', category: 'data', keywords: 'シミュレーション 残響 image source',
    ja: '室内の反射と音の到来方向を含むAmbisonics応答を作るために参照するシミュレーターです。本実装は規約やAPIを調整したHARP由来の生成処理で、実際の会場の測定データではありません。',
    explanation: 'HARP generates Ambisonics responses containing room reflections and arrival directions. This project uses a HARP-derived generator with explicit convention and API adaptations. It is not measured venue data.', source: 'harp' },
  { term: 'VCTK / CSTR', names: [{"short": "VCTK", "english": "CSTR VCTK Corpus: English Multi-speaker Corpus for CSTR Voice Cloning Toolkit", "japanese": "CSTR音声クローニングツールキット用の英語複数話者コーパス（正式名称）", "kind": "name", "source": "vctk"}, {"short": "CSTR", "english": "Centre for Speech Technology Research", "japanese": "音声技術研究センター", "source": "vctk"}], jp: '学習と評価に使う音声コーパス', en: 'Speech corpora for training and evaluation', category: 'data', keywords: 'データセット speech corpus 話者',
    ja: 'VCTKは複数話者の音声データ。原著は学習にVCTK、評価にWSJ0を使用します。本実装の取得済み音声は記録に示すVCTK部分集合で、評価も別話者のVCTKです。WSJ0による原著ベンチマークとは区別します。',
    explanation: 'VCTK contains speech from multiple speakers. The paper trains on VCTK and evaluates on WSJ0. This implementation uses the recorded VCTK subset and held-out VCTK speakers for evaluation; it is not the paper’s WSJ0 benchmark.', source: 'vctk' },
  { term: 'Room IR / microphone response', names: [{"short": "IR", "english": "Impulse Response", "japanese": "インパルス応答"}, {"short": "RIR", "english": "Room Impulse Response", "japanese": "室内インパルス応答", "source": "harp"}, {"short": "ARIR", "english": "Ambisonics Room Impulse Response", "japanese": "Ambisonics室内インパルス応答", "source": "paperSource"}], jp: '室内応答とマイク応答の違い', en: 'Room responses versus microphone responses', category: 'data', keywords: '無響室 インパルス応答 ATF RIR ARIR calibration',
    ja: 'Room IRは音源から受音点までの直接音・反射・残響を表します。マイク応答は受音装置が方向や周波数にどう反応するかです。部屋で録ったIRを、そのまま機器だけのVの代わりにはできません。合成テストは実測なしで進められます。',
    explanation: 'A room IR describes the direct sound, reflections and reverberation between source and receiver. A microphone response describes the device’s directional and frequency behavior. A room recording is not automatically a device-only response V. Synthetic tests can proceed without measurements.' },
  { term: 'Train / validation / test', jp: '学習・調整・最終評価の分割', en: 'Separate fitting, development and evaluation', category: 'data', keywords: 'held-out ホールドアウト 汎化 leakage',
    ja: 'Trainで重みを更新し、validationで途中の状態を確認し、testは学習に使わない最終評価にします。大型priorの音声は話者を分けています。候補シーン数と、実際に処理した固有シーン数も別に記録します。',
    explanation: 'Training updates weights, validation checks development, and test data evaluate unseen examples. The full-size prior uses separate speaker groups. The configured scene pool and unique scenes actually processed are recorded separately.' },
  { term: 'Parameters / weights / checkpoint', names: [{"short": "SHA-256", "english": "Secure Hash Algorithm 256-bit", "japanese": "256ビットの安全なハッシュアルゴリズム", "source": "sha"}, {"short": "M", "english": "million", "japanese": "100万を表す数の表記（30.78Mなら約3078万）", "kind": "notation"}], jp: 'モデルの規模と学習した値', en: 'Model size and learned values', category: 'model', keywords: 'パラメータ 重み 保存 チェックポイント 30.78M SHA256',
    ja: 'Parametersは調整できる数の個数、weightsは学習で得た値、checkpointはその保存物です。30.78Mは規模であり精度ではありません。SHA-256はどの保存物かを照合する識別値で、品質スコアではありません。',
    explanation: 'Parameters count adjustable values; weights are the values learned; a checkpoint stores them. 30.78M describes size, not accuracy. SHA-256 identifies the saved artifact and is not a quality score.' },
  { term: 'NCSN++M / adaLN', names: [{"short": "NCSN", "english": "Noise Conditional Score Network", "japanese": "ノイズ条件付きスコアネットワーク", "source": "ncsn"}, {"short": "NCSN++M", "english": "NCSN++M architecture variant", "japanese": "NCSN++の派生構成名（Mの正式な語への展開は出典に記載なし）", "kind": "name", "source": "ncsnm"}, {"short": "adaLN", "english": "Adaptive Layer Normalization", "japanese": "適応的層正規化", "source": "adaln"}], jp: 'ネットワーク構成とノイズ条件づけ', en: 'Architecture and noise conditioning', category: 'model', keywords: 'U-Net CNN adaptive layer normalization preconditioning',
    ja: 'NCSN++Mは元のNCSN++のパラメータ数を抑えた派生構成名です。出典にMの単語への展開はなく、Mediumなどとは断定しません。adaLNはσに応じて内部特徴の正規化を変えます。原著で未公開の細部は独立実装の選択として記録しています。',
    explanation: 'NCSN++M identifies a reduced-parameter NCSN++ configuration. The cited source does not expand M into a word, so it is not labelled Medium here. Adaptive layer normalization conditions internal features on sigma. Undisclosed original details are recorded as independent implementation choices.', source: 'ncsnm' },
  { term: 'U-Net / FIR', jp: '特徴を縮小・拡大する構成とフィルター', en: 'An architecture and filters for changing feature resolution', category: 'model', keywords: 'ユーネット 畳み込み convolutional skip connection リサンプリング resampling 有限長',
    names: [{ short: 'U-Net', english: 'U-Net · U-shaped network architecture', japanese: '縮小側と拡大側をつなぐU字形のネットワーク構成名', kind: 'name', source: 'unet' }, { short: 'FIR', english: 'Finite Impulse Response', japanese: '有限インパルス応答', source: 'fir' }],
    ja: 'U-Netは縮小して広い範囲の特徴を捉え、拡大するときに縮小前の特徴も渡す構成です。Uは図の形に由来します。本実装では時間・周波数の特徴を扱います。FIRは応答が有限長のフィルターで、モデル内部のリサンプリング時に特徴を平滑化します。ここでいうFIRはスピーカーへ送る補正フィルターではありません。',
    explanation: 'U-Net contracts features to capture wider context, then expands them while reusing features from the contracting path. U refers to the diagram’s shape. Here the features span time and frequency. FIR filters have finite-length impulse responses and smooth features during internal resampling; these are not loudspeaker correction filters.' },
  { term: 'Adam / AdamW', jp: '学習時に重みを更新する方法', en: 'Methods for updating weights during training', category: 'model', keywords: 'アダム オプティマイザー optimizer 最適化 勾配 モーメント weight decay 重み減衰 学習率',
    names: [{ short: 'Adam', english: 'Adaptive Moment Estimation', japanese: '適応的モーメント推定（原著で示された名称の由来）', source: 'adam' }, { short: 'AdamW', english: 'Adam with decoupled weight decay', japanese: '重み減衰を勾配更新から分離したAdamの派生方式', kind: 'name', source: 'adamw' }],
    ja: '勾配の平均や二乗の平均を使い、パラメータごとの更新量を調整します。AdamWは重み減衰を分離する方式名です。本実装の学習ではAdamWを使い、weight_decayは0に設定しています。学習の更新回数と、復元時の拡散ステップ数は別です。',
    explanation: 'Adam uses estimates of the gradient’s first and second moments to adapt parameter updates. AdamW names the variant with decoupled weight decay. This implementation trains with AdamW and weight_decay=0. Training optimizer steps and reconstruction diffusion steps count different operations.' },
  { term: 'CPU / GPU / MPS', jp: '計算する装置とMacの実行方式', en: 'Compute hardware and the Mac execution backend', category: 'model', keywords: '中央演算処理装置 画像処理装置 プロセッサー processor メタル Apple Silicon Torch device 計算環境',
    names: [{ short: 'CPU', english: 'Central Processing Unit', japanese: '中央処理装置・幅広い処理を担うプロセッサー', source: 'processors' }, { short: 'GPU', english: 'Graphics Processing Unit', japanese: '画像処理や多数の並列演算を担うプロセッサー', source: 'processors' }, { short: 'MPS', english: 'Metal Performance Shaders', japanese: 'AppleのGPU向け計算フレームワーク', source: 'mps' }],
    ja: 'CPUとGPUは計算装置です。PyTorchのmpsは、Macの対応GPUでモデルを計算するための実行方式を表します。学習記録のdeviceは実際に使った環境です。公開Webで保存例を開いても、その端末でモデルを再計算したことにはなりません。',
    explanation: 'CPU and GPU identify compute hardware. PyTorch’s mps backend runs model operations on a supported Mac GPU. The training record’s device field identifies the environment actually used. Opening a saved example on the public web does not rerun the model on the viewer’s device.' },
  { term: 'T60 / RT60', jp: '残響が60 dB減衰するまでの時間', en: 'Time for reverberant energy to decay by 60 dB', category: 'data', keywords: 'T₆₀ RT₆₀ reverberation time 残響時間 リバーブ 秒 room simulation',
    names: [{ short: 'T60 / RT60', english: '60 dB reverberation time', japanese: '60 dB減衰に対応する残響時間の記号（秒）', kind: 'notation', source: 'rt60' }],
    ja: '音源が止まった後の残響エネルギーが60 dB下がるまでの時間を表します。合成室内応答を作る際の目標T60と、生成された応答から測った残響時間は区別します。反射の打ち切りや音声の切り出しもあるため、設定値どおりの残響を実現したという保証ではありません。',
    explanation: 'This denotes the time for reverberant energy to fall by 60 dB after the source stops. A target T60 used to generate a room response differs from decay measured from the generated response. Truncated reflections and audio crops mean the target value is not a guarantee of the resulting decay.' },
  { term: 'Loss / NMSE / NRMSE', names: [{"short": "MSE", "english": "Mean Squared Error", "japanese": "平均二乗誤差"}, {"short": "NMSE", "english": "Normalized Mean Squared Error", "japanese": "正規化平均二乗誤差"}, {"short": "NRMSE", "english": "Normalized Root Mean Squared Error", "japanese": "正規化二乗平均平方根誤差"}], jp: '学習の誤差と比較の誤差', en: 'Training error and evaluation error', category: 'evaluation', keywords: 'MSE 損失 正規化 誤差 dB',
    ja: '学習lossはEDMの重み付きMSE。NMSEは誤差エネルギー÷正解エネルギーを10 log₁₀でdB化します。同じ集約ならNRMSEの20 log₁₀表現と一致しますが、評価する成分・圧縮・集約が違う指標同士は直接比較できません。',
    explanation: 'Training loss is EDM-weighted MSE. NMSE is 10 log10(error energy / reference energy), equal to a 20 log10 NRMSE with the same aggregation. Metrics with different channels, compression or aggregation are not directly comparable.' },
  { term: 'Gaussian shrinkage', jp: '単純なノイズ除去の比較基準', en: 'A simple denoising baseline', category: 'evaluation', keywords: 'ガウス縮小 shrink ガウシアン',
    ja: '学習記録の単体評価では、入力を1＋σ²で割る単純な処理とも比べます（σdata=1）。雑音が大きい場合は、この処理だけでも誤差が下がります。モデルは無処理だけでなく、この基準をどれだけ改善するかも確認します。',
    explanation: 'The denoising record also compares against dividing the input by 1+sigma², with sigma_data=1. This simple operation can reduce error when noise is strong. Check improvement against this baseline as well as the untreated input.' },
  { term: 'Magnitude Spectrum Error', jp: '周波数ごとの振幅のずれ', en: 'Magnitude discrepancy by frequency', category: 'evaluation', keywords: 'スペクトル誤差 振幅 dB',
    ja: '各時刻・FOA成分の振幅比をdBにし、その絶対値を平均します。低いほど正解に近く、振幅が2倍なら約6.02 dB。ゼロ除算対策には全比較で同じ参照由来のfloorを使い、参照のない帯域は欠損として表示します。',
    explanation: 'At each frequency, absolute dB magnitude discrepancies are averaged over time and FOA channels. Lower is better; doubling magnitude gives about 6.02 dB. A shared reference-derived floor handles zeros, and bands without reference energy are missing.', source: 'gena' },
  { term: 'Coherence / MSC', names: [{"short": "MSC", "english": "Magnitude-Squared Coherence", "japanese": "二乗振幅コヒーレンス", "source": "msc"}], jp: '時間方向の信号の対応', en: 'Consistency of signals across time', category: 'evaluation', keywords: 'コヒーレンス magnitude squared coherence 相関',
    ja: '周波数ごとに時間方向のクロスパワーから求める0〜1の値です。周波数比較図は成分ごとに求めて平均します。高いほど対応しますが、一定の音量差や位相回転があっても1になり得るため、これだけで空間再現の正しさは判断しません。',
    explanation: 'Magnitude-squared coherence is a 0–1 value based on cross-power across time. The frequency plot averages per-channel values. It can equal one despite constant gain or phase differences, so it alone does not establish correct spatial reproduction.', source: 'gena' },
  { term: 'SI-SDR', names: [{"short": "SI-SDR", "english": "Scale-Invariant Signal-to-Distortion Ratio", "japanese": "スケール不変信号対歪み比", "source": "sisdr"}], jp: '音量差を除いて波形を比べる', en: 'Compare waveforms while allowing a gain change', category: 'evaluation', keywords: 'scale invariant 歪み 音質',
    ja: '正解波形に最適な一定ゲインを合わせ、残る誤差との比をdBで示す指標です。大きいほど良好。音量差を除くため、絶対音圧の一致やマイクの校正を評価する指標ではありません。',
    explanation: 'SI-SDR fits a constant gain to the reference waveform and reports the ratio to remaining error in dB. Higher is better. Since gain differences are removed, it does not measure absolute SPL agreement or microphone calibration.', source: 'sisdr' },
  { term: '3D directional RMS / covariance', names: [{"short": "RMS", "english": "Root Mean Square", "japanese": "二乗平均平方根", "source": "rms"}, {"short": "3D", "english": "Three-dimensional", "japanese": "3次元", "kind": "notation"}], jp: '方向ごとの強さを描く', en: 'Visualize directional strength', category: 'evaluation', keywords: '共分散 shape 形 確率 音圧 source map',
    ja: 'FOA成分の共分散と方向の基底から、方向ごとの大きさを計算して描きます。距離を持つ部屋の音圧分布、音源の位置地図、確率分布ではありません。形が変わること自体は精度改善の証拠ではありません。',
    explanation: 'FOA covariance and directional basis functions produce a directional magnitude display. This is not room pressure over distance, a source-location map or a probability distribution. A changed shape does not itself establish improved accuracy.' },
  { term: 'Stereo preview / shared gain', names: [{"short": "HRTF", "english": "Head-Related Transfer Function", "japanese": "頭部伝達関数", "source": "hrtf"}], jp: '同じ音量基準で試聴する', en: 'Listen with a common level reference', category: 'evaluation', keywords: 'HRTF binaural バイノーラル cardioid',
    ja: 'FOAから左右±45°の仮想カーディオイドを作ったステレオ試聴です。HRTF付きのバイノーラル再生ではありません。比較では共通ゲインを使いますが、実際のスピーカー配置へ出力しているわけではありません。',
    explanation: 'The stereo preview decodes FOA to virtual cardioids at ±45°. It is not HRTF binaural rendering. Comparisons use a common gain reference; the browser is not driving a physical loudspeaker array.' },
  { term: 'Offline inference / computed example', jp: 'ローカル復元と計算済み例', en: 'Local reconstruction and saved examples', category: 'model', keywords: 'オフライン 推論 ブラウザー full-size 大型',
    ja: 'モデルの推論はローカルのTorchで実行します。Webで計算済み例を開く操作は、保存された結果の読み込みです。入力条件・重み・更新回数が記録されているため、何を計算した結果か確認できます。',
    explanation: 'Model inference runs locally in Torch. Opening a computed example on the web loads saved results. Recorded input conditions, checkpoint identity and update counts identify what was actually calculated.' },
];

export default function ADEPSGlossary({ language }: { language: 'jp' | 'en' }) {
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<Category | 'all'>('all');
  const categories: [Category | 'all', string][] = [['all', l('すべて', 'All')], ['representation', l('音の表現', 'Representation')],
    ['model', l('学習モデル', 'Model')], ['inference', l('復元の設定', 'Reconstruction')], ['data', l('データ', 'Data')], ['evaluation', l('評価・試聴', 'Evaluation')]];
  const normalize = (text: string) => text.normalize('NFKC').toLocaleLowerCase().trim();
  const words = normalize(query).split(/\s+/).filter(Boolean);
  const filtered = entries.filter(entry => (category === 'all' || entry.category === category) &&
    words.every(word => normalize([entry.term, entry.jp, entry.en, entry.ja, entry.explanation, entry.keywords, ...(entry.names ?? []).flatMap(name => [name.short, name.english, name.japanese])].join(' ')).includes(word)));
  return <article className="adeps-glossary">
    <div className="ag-intro"><span className="eyebrow">WORDS IN THIS WORKSPACE</span><h2>{l('用語から、仕組みを読む。', 'Read the system through its terms.')}</h2>
      <p>{l('略語の英語正式名称と日本語での意味を併記しています。論文・形式の名前や数式の記号は区別し、どちらの言語・正式名称からも検索できます。', 'English full names and Japanese meanings appear together. Paper and format names are distinguished from symbols. Search abbreviations, full names or explanations in either language.')}</p></div>
    <div className="ag-controls"><label className="ag-search"><Search size={18}/><span className="ag-sr-only">{l('用語を検索', 'Search terms')}</span>
      <input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={l('例：V、σ、正解、coherence', 'Try: V, sigma, reference, coherence')}/>
      {query && <button type="button" aria-label={l('検索をクリア', 'Clear search')} onClick={() => setQuery('')}><X size={16}/></button>}</label>
      <div className="ag-categories" aria-label={l('用語の分野', 'Term categories')}>{categories.map(([id, label]) => <button type="button" key={id} aria-pressed={category === id} onClick={() => setCategory(id)}>{label}</button>)}</div>
      <output className="ag-count" aria-live="polite">{l(`${filtered.length} / ${entries.length} 項目`, `${filtered.length} of ${entries.length} terms`)}</output></div>
    <div className="ag-grid">{filtered.map(entry => <section className="ag-card" key={entry.term}>
      <span className="ag-category">{categories.find(([id]) => id === entry.category)?.[1]}</span><h3>{entry.term}</h3>
      {entry.names && <dl style={{ margin: '0 0 17px', paddingBottom: 4, borderBottom: '1px solid #303030', overflowWrap: 'anywhere' }}>{entry.names.map(name => <div key={name.short} style={{ marginBottom: 12 }}>
        <dt style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>{name.short} · {name.kind === 'notation' ? l('記号・表記', 'Symbol / notation') : name.kind === 'format' ? l('形式名', 'Format name') : name.kind === 'name' ? l('論文・データ・構成の名称', 'Paper / dataset / architecture name') : l('略語の正式名称', 'Full name')}</dt>
        <dd style={{ margin: 0, fontSize: 12, lineHeight: 1.75, color: '#ddd' }}><span lang="en">{name.english}</span><br/><span lang="ja" style={{ color: '#aaa' }}>{name.japanese}</span></dd>
      </div>)}</dl>}
      <h4>{l(entry.jp, entry.en)}</h4><p>{l(entry.ja, entry.explanation)}</p>
      <div style={{ marginTop: 'auto', display: 'grid', gap: 6 }}>{[...new Set([entry.source, ...(entry.names ?? []).map(name => name.source)].filter((source): source is keyof typeof sources => !!source))].map(source => <a key={source} href={sources[source].url} target="_blank" rel="noreferrer">{sources[source].title}<ExternalLink size={11}/></a>)}</div>
    </section>)}</div>
    {!filtered.length && <p className="ag-empty">{l('一致する用語がありません。別の言葉を試すか、分野を「すべて」にしてください。', 'No matching terms. Try another word or select All categories.')}</p>}
    <p className="ag-footnote">{l('モデルや結果の状態は「ADEPSの流れ」「復元・比較」の実記録を確認してください。用語の説明は、学習完了や論文と同等の精度を示すものではありません。',
      'Check actual records in ADEPS workflow and Reconstruct & compare for model and result status. These definitions do not imply completed training or paper-level accuracy.')}</p>
  </article>;
}
