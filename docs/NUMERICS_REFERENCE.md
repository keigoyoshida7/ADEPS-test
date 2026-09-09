# ADEPS-test: independent numerical reference

## Scope and provenance

`backend/numerics.py` is a NumPy-only numerical reference. It implements a
conventional frequency-domain loudspeaker pressure-matching experiment.
**It does not implement or reproduce the ADEPS neural model or its microphone
array reconstruction results.** The public preset is fully synthetic:
a 12 × 9 × 4 m shoebox, 12 omnidirectional sources, 9 fitting points, and
6 separate held-out points. Coordinates, reflections and electronics faults
are simulation inputs, not a venue survey or measured performance.

The same numerical routines can be executed in a browser Python/WebAssembly
runtime or by the optional local Python API. The runtime choice does not make
the simulated data a measurement or turn independent-frequency correction
matrices into an audio filter.

No audio, network control, UDP, Max, Dante routing, or device output is performed.
The correction matrices are analysis results. They are not causal filters ready
to load into playback hardware.

## API

```python
from numerics import run_demo, regularized_mimo, evaluate_transfer

# Returns only strict-JSON-compatible lists/dicts/scalars; no NumPy dependency
# remains in this returned object. Infinite/undefined metrics become null.
result = run_demo(
    seed=7,
    lambda_relative=0.02,
    reflection=0.35,
    fault_gain_db=-6,
    fault_delay_ms=3,
    max_column_norm=2.0,
    speaker_positions=None,
    microphone_positions=None,
)

# Lower-level APIs preserve NumPy arrays. Both accept real measured H as well as
# synthetic H, provided the measurement/target time and level references agree.
fit = regularized_mimo(H_train, target_train, 0.02, 2.0)
unseen_result = evaluate_transfer(H_unseen, target_unseen, fit['G'])
```

Dimensions:

| Symbol | Shape | Meaning |
|---|---|---|
| `H` | F × M × S | Pressure transfer from each physical speaker to each measured point |
| `target` | F × M × D | Desired pressure transfer for each independent desired input |
| `G` | F × S × D | Correction mapping desired inputs into physical speakers |
| `H @ G` | F × M × D | Predicted corrected pressure transfer |

In the demo D = S = 12. The uncorrected baseline is identity routing. Custom
desired-input bases use an explicit `baseline_map` when evaluating.

For each frequency independently, the implementation uses

`G = (HᴴH + λI)⁻¹ Hᴴ target`

where `λ = lambda_relative × ||H||²_F / S`. This relative convention keeps the
same solution if both observed and target matrices are rescaled equally.
`lambda_relative = 0` uses a Moore–Penrose pseudoinverse. The method does not
regularize toward identity. With M < S, even a perfect H = target generally yields
a projector rather than identity. This matters for unseen positions.

After fitting, each column of G is rescaled only if its complex Euclidean norm
exceeds `max_column_norm`. This caps total modeled speaker-drive energy for one
input excited alone. It does **not** cap simultaneous coherent inputs, individual
hardware output peak, or sound pressure level. `operator_norm_after_cap` exposes
the simultaneous-input worst-case linear gain. Capping changes the result from
the unconstrained ridge optimum.

## Model

For the `virtual` profile, the room is 12 × 9 × 4 m. Twelve omnidirectional sources are at z = 3.6 m.
There are nine training points and six different held-out points. The coordinate
axes are x = width, y = depth, z = height. These are synthetic positions, not surveyed installation values.

Each path is `exp(-j 2π f distance / 343) / distance`. Six image sources add the
first reflection from each shoebox wall. `reflection` is a linear **pressure
amplitude** coefficient, not an absorption coefficient or RT60. It is the same
for all six boundaries. The first speaker has the injected gain/delay fault;
all other electronics are ideal. The same fault applies to that source's direct
and reflected paths. The target keeps only the ideal direct paths, with no fault.

The seed is accepted and recorded, but the current model is entirely
deterministic and does not introduce stochastic noise. Sixty-four frequencies
are logarithmically sampled from 80 to 8000 Hz. No source directivity, higher
reflections, diffuse scattering, air absorption, microphone response, measurement
noise, jitter, nonlinearities, or speaker headroom is modeled.

## Initial numeric result

The defaults above currently calculate:

| Evaluation points | Raw complex NRMSE | Corrected complex NRMSE | Improvement |
|---|---:|---:|---:|
| Nine fitted training points | −4.6223 dB | −22.8957 dB | +18.2734 dB |
| Six unused points | −5.3778 dB | −0.5368 dB | **−4.8410 dB: worse** |

This is an informative failure of generalization, not a software success metric.
With 12 speakers and at most nine independent fitted pressure observations,
speaker-space directions remain unobserved. The selected independent-frequency
solution also overfits location-dependent reflections. Do not present a low
training residual as a successful venue calibration. Denser independent spatial
sampling, a physically justified target, a realizable filter objective and a
fresh evaluation set are necessary research steps.

`regularization_tradeoff` recomputes the actual solution at λ values 0, 0.001,
0.01, 0.1, 1 and the user's selected λ (duplicates removed). It does not invent
monotonic improvement. Once a user tunes parameters using these held-out scores,
those points have become a validation set; an independent final test set is then
needed.

## UI field guide

- `frequencies_hz`: common 64-sample x axis.
- `geometry`: room, sources, training positions, held-out positions, reference
  position. Use different visible markers for fit and evaluation locations.
- `metrics.training` / `metrics.heldout`: overall raw/corrected NRMSE,
  improvement; curves per frequency, desired-input channel, and evaluation point;
  frequency-by-input curves. A negative improvement is a real deterioration.
- `fit_diagnostics`: singular-value spectrum, rank, effective condition number,
  Gram condition, regularized Gram condition, column norms before/after cap,
  cap multipliers, operator gain. A finite *effective* condition number describes
  only retained nonzero singular values. Null Gram condition means infinity.
- `heatmaps[NAME].magnitude_db[frequency_index]` / `.phase_deg[frequency_index]`:
  select a frequency and plot the matrix. Each H heatmap is point × speaker/input;
  G is physical speaker × desired input. Phase range is −180 to +180 degrees.
- `matrices[NAME]`: full complex arrays represented as `{real: [...], imag: [...]}`.
  Available names are `observed_training`, `target_training`,
  `corrected_training`, `observed_heldout`, `target_heldout`,
  `corrected_heldout`, and `G`.
- `channel_diagnostics`: injected gain/delay and analytically known direct-path
  arrival at the reference point. These are model ground truth, not estimates.

NRMSE = `20 log10(||actual − target|| / ||target||)`. Lower is better. Zero dB
means the error norm equals the target norm, not perfect reproduction. Aggregate
values use ratios of summed complex energies at sampled frequencies, points and
inputs; they are not an average of displayed dB values, a perceptual score, an SPL
measure, an acoustic coverage percentage, or a continuous-band integral.
−300 dB is only a display floor for exact/numerical zero.

## Measured IR entry points

`ir_to_transfer(ir, sample_rate, frequencies_hz)` accepts REAL IRs shaped
`(measurement_point, speaker, sample)`. It evaluates the exact discrete-time
Fourier transform at the chosen frequencies, without FFT-bin interpolation.
It neither aligns nor trims signals. It is appropriate only after the upstream
measurement process has supplied consistent sample rate, time origin, acoustic
level reference, point order, speaker order, and a meaningful target. It rejects
NaN/infinite inputs, empty arrays, nonpositive or unordered frequencies and
frequencies above Nyquist.

`ir_diagnostics(...)` provides per point/speaker peak amplitude, energy, peak
time and first crossing of a relative threshold (default 10% of that IR's peak).
That onset is only an estimate; noise and strong reflections may make it unlike
the true direct-path arrival. Silent IRs return null onset/peak time when serialized.
Do not independently align each measured IR: that would erase the relative delay
information the calibration is intended to characterize.

## Alternative plane-wave fitting design (not implemented)

The implemented microphone baseline is in `backend/capture.py` and uses a modal
transfer matrix with declared real ACN/N3D conventions. The different design
below is a possible future comparison; it is not implemented and must not be
labelled ADEPS.
For an array with measured positions r_m and plane-wave directions u_q, define
`A[f,m,q] = exp(+j k_f u_q·r_m)` for a declared propagation convention. The target
can be real ACN/SN3D FOA `[W,Y,Z,X] = [1,u_y,u_z,u_x]`. Use quadrature weights w_q
and learn `E[f,4,m]` from

`min_E ||(E A − Y) diag(sqrt(w))||²_F + μ ||E||²_F`.

Then hold out directions and evaluate `E A_test − Y_test`, report array rank,
noise amplification and spatial aliasing. A rigid spherical array requires its
own modal scattering response; the open-array plane-wave expression above is
not a rigid-sphere model. FOA degree/order, normalization, directional convention,
and phase convention must be explicit before comparing against another model.
That would provide a transparent baseline only, without generative denoising,
microphone upscaling, ADEPS adaptation losses, or learned acoustics.

## Tests

From the repository root, with NumPy and SciPy installed:

```sh
PYTHONPATH=backend python3 -m unittest discover -s tests -v
```

The numerical test suite covers identity recovery, a closed-form ridge solution, relative
regularization scaling, cap meaning, finite handling of rank-deficient and zero
H, real independent-point recovery of a shared gain/phase fault, honest
held-out deterioration in an underdetermined counterexample, geometry/fault
phase, exact IR DTFT/time origin, invalid-input rejection, reproducibility and
strict JSON serialization.
