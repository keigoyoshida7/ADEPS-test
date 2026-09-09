# ADEPS v2: implementation notes for ADEPS-test

Verified 2026-09-08. Scope: arXiv 2608.24558v2, all five PDF pages (body, equations, Tables 1–3, Figure 1, references) downloaded and visually inspected. Page references below are physical PDF pages, 1-based.

## Source status

- Paper: https://arxiv.org/abs/2608.24558v2
- Full PDF: https://arxiv.org/pdf/2608.24558v2
- HTML: https://arxiv.org/html/2608.24558v2
- Author repository that explicitly identifies itself as the official implementation: https://github.com/Amitmils/ADEUPS
- Verified repository revision: `5076f163a1f939c297b55a39b2d9d33e2b224a5f` (2026-09-03), main branch only, no releases. Tree contains only `README.md`.
- Pinned repository evidence: https://github.com/Amitmils/ADEUPS/tree/5076f163a1f939c297b55a39b2d9d33e2b224a5f
- README explicitly states that the codebase is being prepared and the full code will be released when ready. No runnable ADEPS code, model weights, configuration, or train/evaluation manifests are present. The README's MIT badge points at a LICENSE file which is not in the current tree, so do not claim that future code has a verified license.
- `https://github.com/Amitmils/AmbiDiffEnc`, mentioned in indexed copies of the work, currently returns 404 via both repository API and raw README. The downloaded v2 PDF itself contains no source-code footnote. Cite the confirmed ADEUPS repository, not an assumed rename.
- Same author's GenAU is an implementation of another paper (DiffAU, arXiv:2510.00180); do not substitute it for ADEPS.

## What is actually demonstrated

The task is recovery of Ambisonics coefficients from compact microphone-array signals on reverberant speech. A trained prior can be reused on a different array provided the array's physical acquisition model is supplied at inference. This is zero-shot adaptation with respect to microphone geometry, not unknown-physics reconstruction. See p. 1 Introduction and pp. 2–3, Secs. 2–3.

The paper does not validate loudspeaker equalization, speaker/room inversion, AFC setup, 12-channel venue commissioning, musical playback restoration, live operation, or a venue-independent render. A speaker test/correction tool is an engineering application inspired by the separation of content and physical model, not an ADEPS reproduction.

The abstract mentions simulated and real microphone arrays. Section 4 describes simulations projected through the model, including a Project Aria array, and additive simulated noise. Do not restate this as a reported on-site microphone-recording or concert test. The paper does not report deployment measurements for this prototype.

The prior is fifth order (36 Ambisonics channels); evaluated output is first order (4 Ambisonics channels). A 36-channel prior does not establish successful 4-to-36 higher-order upscaling. The conclusion explicitly limits the current method to spatially resolvable orders and lists underdetermined upscaling as future work (p. 4). The 12 synthetic loudspeakers in this prototype are playback channels, not microphone channels or Ambisonics coefficients.

## Forward model and baseline

For Q omnidirectional microphones (p. 2, Eqs. 1–3):

`p_q(k) = sum_(n,m) b_n(k,r_q) Y_n^m(theta_q,phi_q) a_nm(k) + nu_q(k)`

`p(k) = V(k) a_Neff(k) + nu(k)`

- `p`: complex microphone STFT, shape `[Q,F,T]`.
- `V`: complex frequency-dependent modal steering matrix. For inference prior order Np, shape `[F,Q,(Np+1)^2]` (p. 3 Algorithm 1).
- Noise is assumed uncorrelated with Ambisonics coefficients and i.i.d. across microphones.
- The paper writes real-valued spherical harmonics Y and a factorization V=YB. For a general arbitrary-radius array, implement each microphone's radial dependence explicitly or import V: one common diagonal B is not automatically valid if r_q differs. The equation is a physical abstraction, not a ready calibration recipe.
- ATF is the **microphone array's acquisition response**. A speaker-to-room transfer matrix is a different operator with different dimensions and purpose.

Linear encoder (p. 2 Eq. 5):

`Etilde(f) = V(f)^H [V(f)V(f)^H + gamma^2 I_Q]^-1`

Linear baseline target output uses the first `(Nenc+1)^2` rows. The paper requires `(Nenc+1)^2 <= Q` for spatial resolvability; the count is necessary and does not make a poorly placed/coplanar array well-conditioned. Show singular values/conditioning and rank in a diagnostic UI.

## ADEPS inference, not executable without the trained prior

The prior has order `Np > Nenc`. The compression (p. 3, Sec. 3.1) is:

`H(z)= beta |z|^alpha exp(i arg(z))`.

Set `y = H(Etilde p)` and define the acquisition/re-encoding degradation:

`A(x) = H(Etilde V H^-1(x))` (p. 3 Eq. 10).

This is measurement consistency in the **linearly encoded compressed observation space**, not simply a microphone-space residual.

Given the trained denoiser `D_theta(x_i,sigma_i)`:

1. Warm-initialize `x ~ Normal(y, sigma_max^2 I)`.
2. Predict `x0_hat=D_theta(x_i,sigma_i)`.
3. Prior score `s_i=(x0_hat-x_i)/sigma_i^2`.
4. Guidance `s_LH= -eta(sigma_i) grad_(x_i) ||y-A(x0_hat)||_2^2`. This derivative includes the denoiser.
5. `eta(sigma)=eta_prime / [sigma * ||grad_(x_i) ||y-A(x0_hat)||_2^2||_2]`.
6. Update `x_(i+1)=x_i - sigma_i (sigma_(i+1)-sigma_i) (s_i+s_LH)`.
7. Return `H^-1(x_final)` and evaluate first-order channels.

The rho schedule in Eq. 11 is `(sigma_max^(1/rho)+i/(M-1)*(sigma_min^(1/rho)-sigma_max^(1/rho)))^rho`.

Algorithm 1 has a terminal-index ambiguity: it iterates i=0..M-1 but references sigma_(i+1), while Eq. 11 defines the M schedule points. An implementation typically needs an explicit terminal zero or endpoint rule, but the paper does not state the implementation choice. Do not silently label an invented endpoint as official.

## Published settings and omitted configuration

Published (p. 4, Section 4):

- `Np=5`; evaluation `Nenc=1`.
- NCSN++M modified to 36 input/output channels with adaptive linear norm time conditioning, 30.8 million parameters.
- `alpha=.67`, `beta=3`.
- Training sigma schedule: max 80, min .002, rho 10.
- Inference warm start sigma max 20, M=150 reverse steps.
- Training targets: HARP-generated simulated ARIRs convolved with VCTK speech.
- Evaluation: WSJ0 speech.
- 20,000 training scenes, 1,000 evaluation scenes.
- Room dimensions: each horizontal side 6–10 m; height 2–3 m. T60 .1–.4 seconds.
- Array center varies inside a 1×1 m region; 1–2 sources; source distances .8–1.5 m; DOAs varied.
- 13 arrays: Project Aria plus four random irregular realizations each for Q=4,5,6. Pairwise microphone distances .02–.18 m.
- Projected microphone signals corrupted by Gaussian noise at 50 dB SNR; 13,000 test signals.
- Ideal: Neff=Np=5; mismatch: Neff=15, Np=5.

Not specified sufficiently in the paper/repository: sample rate, FFT length/window/hop, chunk length and overlap, FFT scaling, complex channel representation for the network, explicit ACN/FuMa naming, N3D/SN3D convention, SH phase convention, gamma, eta_prime, terminal-step implementation, full layer architecture and model config, optimizer/scheduler/batch size/epochs, train/eval scene lists and seeds, microphone ATFs/geometry files, trained weights, precise binaural rendering/ERB implementation, runtime, latency, real-time factor, GPU/VRAM and training cost. An app may choose its own explicit conventions, but must label them as prototype choices, not ADEPS paper settings.

## Metrics, baselines, and the important non-wins

The study reports (p. 4): SI-SDR (higher), log-magnitude spectral error (lower), magnitude-squared coherence (higher), binaural ILD error and interaural-coherence error (lower). Binaural results use Neumann KU100 HRTFs and ERB bands. The short paper cites definitions rather than fully specifying aggregation and implementation.

Baselines: linear encoding; parametric synthesis with **oracle DOAs and device ATFs** (an upper-bound aided comparator, not a basic panner); and a geometry-trained U-Net on one four-mic array only.

Table 1 ideal SI-SDR, linear -> ADEPS:

- Q4: 6.80 -> 11.66 dB.
- Q5: 7.95 -> 14.18 dB.
- Q6: 9.26 -> 16.20 dB.
- Aria: 3.63 -> 10.00 dB.

Table 2 mismatch SI-SDR, linear -> ADEPS:

- Q4: 6.71 -> 9.85 dB.
- Q5: 7.82 -> 10.57 dB.
- Q6: 9.09 -> 12.67 dB.
- Aria: 3.31 -> 4.94 dB.

Avoid blanket claims that all metrics improve:

- Table 1 ideal coherence: Q4 .81 linear vs .80 ADEPS; Aria .76 vs .73. Parametric Aria spectral error 6.04 dB is better than ADEPS 6.67. Parametric Q4 ILD .98 dB is slightly better than ADEPS 1.02.
- Table 2 mismatch coherence: linear [.82,.82,.83,.76] versus ADEPS [.74,.76,.80,.64], all worse. Aria spectrum error: parametric 7.36 vs ADEPS 7.43 dB. Aria IC error: parametric .08 vs ADEPS .10. Several ILD/IC entries favor the parametric baseline.
- Table 3: U-Net coherence .85 vs ADEPS .78, though SI-SDR 8.03 vs 11.67 dB favors ADEPS.
- Figure 1 plots frequency-dependent spectrum error and coherence averaged across the test signals. It shows low-frequency benefit and high-frequency losses under mismatch; do not manufacture a measured loudspeaker frequency response from this figure.

The table contains counterexamples to the prose's broad assertion of best spectral error across geometries. Prefer actual table numbers.

For a research interface, show metrics as valid only when their required reference data is supplied. SI-SDR/spectral error/coherence require a paired clean Ambisonics reference with matching time/channel conventions. ILD/IC need a specified binaural renderer and HRTF. A lone field recording plus V cannot produce reference quality scores. Measurement residual, clipping, channel rank, and data/clock validity are separate diagnostics; residual alone does not prove perceptual correctness.

## Data availability

ADEPS-specific trained prior and exact scenes have no public release in the verified official repo.

Independent source ingredients do exist:

- HARP generation code: https://github.com/whojavumusic/HARP — source paper https://arxiv.org/abs/2411.14207. Repository provides HOA RIR generation; its default generation example is 7th order/48 kHz. That is **not evidence** that ADEPS used 48 kHz or that the authors' exact scenes are available.
- VCTK 0.92: https://doi.org/10.7488/ds/2645 — public corpus, CC BY 4.0, around 10.94 GB. Public speech corpus does not supply the ADEPS scene splits or weights.
- WSJ0: https://catalog.ldc.upenn.edu/LDC93S6A — cited evaluation dataset; access/license must be obtained through its provider. No download or purchase performed.

## Honest test-system architecture

Keep three clearly labeled paths:

1. Capture research: microphone WAV + measured/modelled V -> linear encoding -> optional future ADEPS adapter -> reconstructed FOA -> reference comparison. ADEPS status stays unavailable until compatible trained weights/code/config are present.
2. Measurement and commissioning: playback channel map -> known test/sweep -> capture -> deterministic IR/transfer response -> gain/delay/response/routing diagnostics. Preserve phase and amplitude of calibration signals; a learned speech prior should not process calibration IRs as if they were speech.
3. Playback: SPAT/Max/rendered tracks -> a separately verified audio interface and playback chain -> speakers. The UI is a controller and visualizer; model-based reconstruction is offline unless actual measured runtime establishes live suitability.

A WebGL view should explain geometry/channel selection and measured point coverage. Without measured spatial transfer data it must not display an attractive animated pressure field as a measurement. A demo can be simulated and marked as such.

The public examples are synthetic. The test system does not establish hardware routing, measured acoustics, or a successful ADEPS reproduction.
