"""NumPy reference for synthetic playback-calibration experiments.

This is NOT an implementation or reproduction of ADEPS.  It solves an ordinary
frequency-domain pressure-matching/ridge problem for a *synthetic* loudspeaker
room.  The coordinates, transfer functions, and improvements are synthetic.
There is no audio output, device control, UDP, or real-time filter export here.

Array convention: H[f, m, s] is complex pressure at measurement point m from
physical speaker s. target[f, m, d] is the desired pressure from input d.
G[f, s, d] maps desired inputs to physical speakers.  Corrected pressure is H @ G.
For each frequency:
  lambda_abs = lambda_relative * ||H||_F**2 / speaker_count
  G = (H.conj().T @ H + lambda_abs I)^-1 @ H.conj().T @ target
The unregularized case uses the Moore-Penrose pseudoinverse.  A column-2-norm cap
is applied AFTER optimization, so a capped G is not the unconstrained solution.
That cap bounds total speaker-drive energy for one unit input column.  It does
NOT bound simultaneous-input gain, individual amplifier voltage, or SPL.

Per-frequency matrices do not constitute a causal implementable FIR filter.
Timing, causality, acoustic units, headroom, interpolation and filter realization
must be resolved before any hardware implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

SPEED_OF_SOUND = 343.0
DB_FLOOR = -300.0


def _finite_array(value: Any, name: str, ndim: int, *, complex_ok: bool = False) -> np.ndarray:
    raw = np.asarray(value)
    if not complex_ok and np.iscomplexobj(raw):
        raise ValueError(f"{name} must be real")
    arr = np.asarray(value, dtype=np.complex128 if complex_ok else np.float64)
    if arr.ndim != ndim or any(size == 0 for size in arr.shape):
        raise ValueError(f"{name} must be a nonempty {ndim}-dimensional array")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _scalar(value: float, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0:
        raise ValueError(f"{name} must be greater than zero")
    if nonnegative and result < 0:
        raise ValueError(f"{name} must not be negative")
    return result


def _frequencies(value: Any) -> np.ndarray:
    result = _finite_array(value, "frequencies_hz", 1)
    if np.any(result <= 0) or np.any(np.diff(result) <= 0):
        raise ValueError("frequencies_hz must be positive and strictly increasing")
    return result


def _positions(value: Any, name: str) -> np.ndarray:
    result = _finite_array(value, name, 2)
    if result.shape[1] != 3:
        raise ValueError(f"{name} must have shape (count, 3), in metres")
    return result


def _amplitude_db(value: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(value), 10.0 ** (DB_FLOOR / 20.0)))


def _normalized_error_db(actual: np.ndarray, target: np.ndarray, axis: Any = None) -> np.ndarray:
    """20 log10(||actual-target|| / ||target||); undefined target -> NaN.

    -300 dB is a DISPLAY FLOOR for exact/numerical zero, not measurement accuracy.
    """
    numerator = np.sum(np.abs(actual - target) ** 2, axis=axis)
    denominator = np.sum(np.abs(target) ** 2, axis=axis)
    ratio = np.divide(numerator, denominator, out=np.full_like(numerator, np.nan, dtype=float), where=denominator > 0)
    return 10.0 * np.log10(np.maximum(ratio, 10.0 ** (DB_FLOOR / 10.0)))


def regularized_mimo(
    H: Any,
    target: Any,
    lambda_relative: float = 0.02,
    max_column_norm: float | None = 2.0,
) -> dict[str, np.ndarray]:
    """Compute G plus diagnostics from synthetic OR measured transfer matrices.

    H: (frequency, measurement_point, physical_speaker)
    target: (frequency, measurement_point, desired_input)
    lambda_relative >= 0. A value of zero requests a pseudoinverse solution.
    max_column_norm: optional positive post-solve L2 cap for each G[:, :, d].

    With fewer independent measurement points than speakers the system is
    underdetermined, including when its nonzero singular values look well
    conditioned. A small training error cannot establish spatial generalization.
    """
    observed = _finite_array(H, "H", 3, complex_ok=True)
    desired = _finite_array(target, "target", 3, complex_ok=True)
    if observed.shape[:2] != desired.shape[:2]:
        raise ValueError("H and target must share frequency and measurement dimensions")
    ridge = _scalar(lambda_relative, "lambda_relative", nonnegative=True)
    cap = None if max_column_norm is None else _scalar(max_column_norm, "max_column_norm", positive=True)
    n_freq, n_mic, n_speaker = observed.shape
    scale = np.sum(np.abs(observed) ** 2, axis=(1, 2)) / n_speaker
    lambda_absolute = ridge * scale
    correction = np.empty((n_freq, n_speaker, desired.shape[2]), dtype=np.complex128)
    singular_values = np.linalg.svd(observed, compute_uv=False)
    tolerance = np.maximum(n_mic, n_speaker) * np.finfo(float).eps * singular_values[:, :1]
    rank = np.sum(singular_values > tolerance, axis=1)
    effective_condition = np.full(n_freq, np.inf)
    gram_condition = np.full(n_freq, np.inf)
    regularized_gram_condition = np.full(n_freq, np.inf)
    for f in range(n_freq):
        hf, tf = observed[f], desired[f]
        if ridge == 0 or scale[f] == 0:
            correction[f] = np.linalg.pinv(hf) @ tf
        else:
            hh = hf.conj().T
            correction[f] = np.linalg.solve(hh @ hf + lambda_absolute[f] * np.eye(n_speaker), hh @ tf)
        if rank[f]:
            effective_condition[f] = singular_values[f, 0] / singular_values[f, rank[f] - 1]
        smallest_squared = singular_values[f, -1] ** 2 if rank[f] == n_speaker else 0.0
        largest_squared = singular_values[f, 0] ** 2
        if smallest_squared > 0:
            gram_condition[f] = largest_squared / smallest_squared
        if smallest_squared + lambda_absolute[f] > 0:
            regularized_gram_condition[f] = (largest_squared + lambda_absolute[f]) / (smallest_squared + lambda_absolute[f])
    norms_before = np.linalg.norm(correction, axis=1)
    multipliers = np.ones_like(norms_before)
    if cap is not None:
        multipliers = np.minimum(1.0, cap / np.maximum(norms_before, np.finfo(float).tiny))
        correction *= multipliers[:, None, :]
    return {
        "G": correction,
        "lambda_absolute": lambda_absolute,
        "rank": rank,
        "singular_values": singular_values,
        "effective_condition_number": effective_condition,
        "gram_condition_number": gram_condition,
        "regularized_gram_condition_number": regularized_gram_condition,
        "column_norm_before_cap": norms_before,
        "column_norm_after_cap": np.linalg.norm(correction, axis=1),
        "column_cap_multiplier": multipliers,
        "operator_norm_after_cap": np.linalg.svd(correction, compute_uv=False)[:, 0],
    }


def evaluate_transfer(H: Any, target: Any, G: Any, baseline_map: Any | None = None) -> dict[str, Any]:
    """Evaluate without fitting; pass held-out H/target to assess generalization.

    Default baseline_map is identity and therefore requires desired inputs ==
    physical speakers. For another target basis supply B with shape (S,D) or
    (F,S,D), explicitly defining what 'uncorrected' means.
    """
    observed = _finite_array(H, "H", 3, complex_ok=True)
    desired = _finite_array(target, "target", 3, complex_ok=True)
    correction = _finite_array(G, "G", 3, complex_ok=True)
    nf, nm, ns = observed.shape
    if desired.shape[:2] != (nf, nm) or correction.shape != (nf, ns, desired.shape[2]):
        raise ValueError("incompatible H, target, and G shapes")
    if not np.any(np.abs(desired) > 0):
        raise ValueError("target has zero energy; normalized error is undefined")
    if baseline_map is None:
        if ns != desired.shape[2]:
            raise ValueError("provide baseline_map when desired-input and speaker counts differ")
        raw = observed
    else:
        baseline = np.asarray(baseline_map, dtype=np.complex128)
        if baseline.shape not in [(ns, desired.shape[2]), (nf, ns, desired.shape[2])] or not np.isfinite(baseline).all():
            raise ValueError("baseline_map must be finite with shape (S,D) or (F,S,D)")
        raw = observed @ baseline
    corrected = observed @ correction
    raw_db = float(_normalized_error_db(raw, desired))
    corrected_db = float(_normalized_error_db(corrected, desired))
    return {
        "raw_nrmse_db": raw_db,
        "corrected_nrmse_db": corrected_db,
        "improvement_db": raw_db - corrected_db,
        "raw_error_db_by_frequency": _normalized_error_db(raw, desired, axis=(1, 2)),
        "corrected_error_db_by_frequency": _normalized_error_db(corrected, desired, axis=(1, 2)),
        "raw_error_db_by_channel": _normalized_error_db(raw, desired, axis=(0, 1)),
        "corrected_error_db_by_channel": _normalized_error_db(corrected, desired, axis=(0, 1)),
        "raw_error_db_by_point": _normalized_error_db(raw, desired, axis=(0, 2)),
        "corrected_error_db_by_point": _normalized_error_db(corrected, desired, axis=(0, 2)),
        "raw_error_db_frequency_channel": _normalized_error_db(raw, desired, axis=1),
        "corrected_error_db_frequency_channel": _normalized_error_db(corrected, desired, axis=1),
        "corrected_transfer": corrected,
    }


def synthetic_transfer(
    frequencies_hz: Any,
    speaker_positions: Any,
    microphone_positions: Any,
    room: Any = (12.0, 9.0, 4.0),
    gains_db: Any | None = None,
    delays_ms: Any | None = None,
    reflection: float = 0.35,
    speed_of_sound: float = SPEED_OF_SOUND,
) -> np.ndarray:
    """Monopole direct path + six first-order shoebox image sources.

    Pressure amplitude is 1/distance (normalized at 1 m); no 4*pi factor.
    reflection is a pressure-amplitude coefficient applied equally to each wall.
    It is NOT an absorption coefficient or RT60. No scattering, directivity,
    higher-order reflections, air absorption, microphone response, or noise.
    Per-speaker gain/delay faults multiply direct AND reflected paths.
    """
    freqs = _frequencies(frequencies_hz)
    speakers = _positions(speaker_positions, "speaker_positions")
    microphones = _positions(microphone_positions, "microphone_positions")
    bounds = _finite_array(room, "room", 1)
    if bounds.shape != (3,) or np.any(bounds <= 0):
        raise ValueError("room must contain three positive dimensions in metres")
    if np.any(speakers <= 0) or np.any(speakers >= bounds) or np.any(microphones <= 0) or np.any(microphones >= bounds):
        raise ValueError("all source/measurement positions must be strictly inside the room")
    coefficient = _scalar(reflection, "reflection", nonnegative=True)
    if coefficient > 1:
        raise ValueError("reflection must be a pressure-amplitude coefficient from 0 to 1")
    sound_speed = _scalar(speed_of_sound, "speed_of_sound", positive=True)
    ns = len(speakers)
    gain = np.zeros(ns) if gains_db is None else _finite_array(gains_db, "gains_db", 1)
    delay = np.zeros(ns) if delays_ms is None else _finite_array(delays_ms, "delays_ms", 1)
    if gain.shape != (ns,) or delay.shape != (ns,):
        raise ValueError("gains_db and delays_ms must have one value per speaker")
    if np.any(np.abs(gain) > 120) or np.any(delay < 0):
        raise ValueError("gain must be within +/-120 dB and delays must be nonnegative")
    wave_number = 2.0 * np.pi * freqs / sound_speed

    def propagate(positions: np.ndarray) -> np.ndarray:
        distance = np.linalg.norm(microphones[:, None, :] - positions[None, :, :], axis=2)
        if np.any(distance < 1e-5):
            raise ValueError("a source and measurement point are colocated")
        return np.exp(-1j * wave_number[:, None, None] * distance[None, :, :]) / distance[None, :, :]

    response = propagate(speakers)
    if coefficient:
        for axis in range(3):
            for side in (0.0, bounds[axis]):
                image_sources = speakers.copy()
                image_sources[:, axis] = 2.0 * side - speakers[:, axis]
                response += coefficient * propagate(image_sources)
    electronics = 10.0 ** (gain / 20.0) * np.exp(-2j * np.pi * freqs[:, None] * delay[None, :] / 1000.0)
    return response * electronics[:, None, :]


def ir_to_transfer(impulse_responses: Any, sample_rate: float, frequencies_hz: Any) -> np.ndarray:
    """Exact DTFT samples of REAL discrete IRs shaped (point,speaker,sample).

    No FFT-bin interpolation, normalization, time alignment, onset trimming, or
    deconvolution is performed. All IRs must share a time origin, sample rate,
    level reference and channel ordering. Output shape is (frequency,point,speaker).
    """
    ir = _finite_array(impulse_responses, "impulse_responses", 3)
    fs = _scalar(sample_rate, "sample_rate", positive=True)
    freqs = _frequencies(frequencies_hz)
    if np.any(freqs > fs / 2.0):
        raise ValueError("frequencies_hz must not exceed Nyquist")
    samples = np.arange(ir.shape[2], dtype=np.float64) / fs
    output = np.empty((len(freqs), *ir.shape[:2]), dtype=np.complex128)
    for start in range(0, len(freqs), 8):
        chosen = freqs[start:start + 8]
        kernel = np.exp(-2j * np.pi * chosen[:, None] * samples[None, :])
        output[start:start + len(chosen)] = np.einsum("fn,msn->fms", kernel, ir, optimize=True)
    return output


def ir_diagnostics(impulse_responses: Any, sample_rate: float, onset_fraction: float = 0.1) -> dict[str, Any]:
    """Per point/speaker IR peak, energy, and threshold-crossing onset estimate.

    Onset is the first sample >= onset_fraction * that channel's peak magnitude.
    It is not a guaranteed direct-path arrival; noise/strong reflections can bias
    it. Zero IRs get NaN onset/peak time, converted to null by to_jsonable().
    """
    ir = _finite_array(impulse_responses, "impulse_responses", 3)
    fs = _scalar(sample_rate, "sample_rate", positive=True)
    fraction = _scalar(onset_fraction, "onset_fraction", positive=True)
    if fraction > 1:
        raise ValueError("onset_fraction must be <= 1")
    absolute = np.abs(ir)
    peak = absolute.max(axis=2)
    nonzero = peak > 0
    peak_index = absolute.argmax(axis=2)
    onset_index = (absolute >= fraction * peak[:, :, None]).argmax(axis=2)
    return {
        "onset_threshold_fraction": fraction,
        "onset_ms": np.where(nonzero, onset_index * 1000.0 / fs, np.nan),
        "peak_time_ms": np.where(nonzero, peak_index * 1000.0 / fs, np.nan),
        "peak_absolute": peak,
        "energy": np.sum(ir * ir, axis=2),
        "silent_channel": ~nonzero,
    }


def to_jsonable(value: Any) -> Any:
    """Strict JSON: complex arrays -> {real,imag}; undefined/infinite -> null."""
    if isinstance(value, np.ndarray):
        if np.iscomplexobj(value):
            return {"real": to_jsonable(value.real), "imag": to_jsonable(value.imag)}
        return to_jsonable(value.tolist())
    if isinstance(value, np.generic):
        return to_jsonable(value.item())
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, complex):
        return {"real": to_jsonable(value.real), "imag": to_jsonable(value.imag)}
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def run_demo(
    seed: int = 7,
    lambda_relative: float = 0.02,
    reflection: float = 0.35,
    fault_gain_db: float = -6.0,
    fault_delay_ms: float = 3.0,
    max_column_norm: float | None = 2.0,
    speaker_positions: Any | None = None,
    microphone_positions: Any | None = None,
    geometry_profile: str = "virtual",
) -> dict[str, Any]:
    """JSON-ready synthetic 12-speaker, 9-training-point, 6-held-out-point demo.

    Geometry and transfer model are deterministic. `seed` is retained as metadata
    for API stability; this version introduces no random perturbations or noise.
    Custom speaker/training positions are accepted; held-out positions stay fixed
    and are never fitted. Overlapping custom training and held-out points reject.
    All curves use 64 LOG-SPACED frequencies, not a broadband time-domain score.
    Only speaker 1 has the supplied electronics fault; all others are normal.
    """
    room = np.array([12.0, 9.0, 4.0])
    freqs = np.geomspace(80.0, 8000.0, 64)
    speakers = np.array([[x, y, 3.6] for x in (1.5, 4.5, 7.5, 10.5) for y in (2.0, 4.5, 7.0)]) if speaker_positions is None else _positions(speaker_positions, "speaker_positions")
    training = np.array([[x, y, 1.2] for x in (2.4, 6.0, 9.6) for y in (2.0, 4.5, 7.0)]) if microphone_positions is None else _positions(microphone_positions, "microphone_positions")
    heldout = np.array([[x, y, z] for y, z in ((3.2, 1.2), (5.8, 1.5)) for x in (3.1, 6.1, 9.1)])
    reference_speakers = np.array([[x, y, 3.6] for x in (1.5, 4.5, 7.5, 10.5) for y in (2.0, 4.5, 7.0)])
    origin = np.zeros(3)
    reference_point = np.array([6.0, 4.5, 1.2])
    speaker_names = [f"S{i+1}" for i in range(len(speakers))]
    geometry_source = "SYNTHETIC demo coordinates, not a surveyed venue"
    source_sha256 = None
    if geometry_profile != "virtual":
        raise ValueError("Only the synthetic virtual geometry is available in this edition")
    if np.any(np.linalg.norm(training[:, None, :] - heldout[None, :, :], axis=2) < 0.05):
        raise ValueError("training and fixed held-out positions must be separated by >= 5 cm")
    gains, delays = np.zeros(len(speakers)), np.zeros(len(speakers))
    gains[0] = _scalar(fault_gain_db, "fault_gain_db")
    delays[0] = _scalar(fault_delay_ms, "fault_delay_ms", nonnegative=True)
    # Translate every point to the shoebox corner ONLY for the acoustic model.
    # UI/export preserve the original project axes and origin, without rescaling.
    common = dict(frequencies_hz=freqs, speaker_positions=speakers - origin, room=room)
    H_train = synthetic_transfer(**common, microphone_positions=training - origin, gains_db=gains, delays_ms=delays, reflection=reflection)
    T_train = synthetic_transfer(**common, microphone_positions=training - origin, reflection=0.0)
    H_held = synthetic_transfer(**common, microphone_positions=heldout - origin, gains_db=gains, delays_ms=delays, reflection=reflection)
    T_held = synthetic_transfer(**common, microphone_positions=heldout - origin, reflection=0.0)
    fit = regularized_mimo(H_train, T_train, lambda_relative, max_column_norm)
    train_metrics = evaluate_transfer(H_train, T_train, fit["G"])
    held_metrics = evaluate_transfer(H_held, T_held, fit["G"])
    tradeoff = []
    scan = sorted(set([0.0, 0.001, 0.01, 0.1, 1.0, float(lambda_relative)]))
    for value in scan:
        candidate = regularized_mimo(H_train, T_train, value, max_column_norm)
        tm = evaluate_transfer(H_train, T_train, candidate["G"])
        hm = evaluate_transfer(H_held, T_held, candidate["G"])
        tradeoff.append({
            "lambda_relative": value,
            "train_corrected_nrmse_db": tm["corrected_nrmse_db"],
            "heldout_corrected_nrmse_db": hm["corrected_nrmse_db"],
            "heldout_improvement_db": hm["improvement_db"],
            "maximum_column_norm": float(candidate["column_norm_after_cap"].max()),
            "maximum_column_norm_db": float(_amplitude_db(candidate["column_norm_after_cap"].max())),
            "maximum_operator_norm": float(candidate["operator_norm_after_cap"].max()),
            "fraction_columns_capped": float(np.mean(candidate["column_cap_multiplier"] < 1.0)),
        })
    direct_time = np.linalg.norm(speakers - reference_point, axis=1) / SPEED_OF_SOUND * 1000.0
    # Complex transfer arrays stay available for independent audit and UI slicing.
    matrices = {"observed_training": H_train, "target_training": T_train,
                "corrected_training": train_metrics.pop("corrected_transfer"),
                "observed_heldout": H_held, "target_heldout": T_held,
                "corrected_heldout": held_metrics.pop("corrected_transfer"), "G": fit["G"]}
    heatmaps = {name: {"magnitude_db": _amplitude_db(matrix), "phase_deg": np.angle(matrix, deg=True)} for name, matrix in matrices.items()}
    return to_jsonable({
        "schema_version": "adeps-test-playback-hypothesis-1.0",
        "experiment_kind": "synthetic_playback_pressure_matching_not_ADEPS",
        "provenance": {"geometry": geometry_source, "geometry_profile": geometry_profile, "speaker_positions_override_supplied": speaker_positions is not None, "speaker_positions_edited": not np.array_equal(speakers, reference_speakers), "source_file_sha256": source_sha256, "as_built_verified": False, "room": "Assumed synthetic enclosure, not measured dimensions", "measurement_points": "SYNTHETIC positions", "speaker_processing": "Project EQ/delay/routing NOT modeled; only explicit synthetic faults", "transfer": "SIMULATED, NOT measured", "seed": int(seed), "randomness": "none"},
        "model_limits": ["Not an ADEPS reproduction or microphone-array neural reconstruction", "Direct path plus six first-order image sources only", "No speaker directivity, higher reflections, diffuse noise, latency jitter or hardware saturation", "Independent frequency solutions; causal filter design is not implemented", "Held-out scores cover only the specified simulated points", "Column norm cap is not an SPL or simultaneous-input peak limiter"],
        "configuration": {"geometry_profile": geometry_profile, "lambda_relative": lambda_relative, "reflection_pressure_amplitude": reflection, "fault_gain_db": fault_gain_db, "fault_delay_ms": fault_delay_ms, "fault_speaker_index": 0, "max_column_norm": max_column_norm, "speed_of_sound_m_s": SPEED_OF_SOUND, "frequency_sampling": "64 logarithmically spaced samples; aggregate score is ratio of summed sampled complex energies", "db_display_floor": DB_FLOOR},
        "geometry": {"profile": geometry_profile, "speaker_names": speaker_names, "room_origin_m": origin, "room_dimensions_m": room, "speakers_m": speakers, "training_points_m": training, "heldout_points_m": heldout, "reference_point_m": reference_point, "units": "metres", "coordinate_axes": "x=width, y=depth, z=height"},
        "frequencies_hz": freqs,
        "metrics": {"training": train_metrics, "heldout": held_metrics},
        "channel_diagnostics": {"speaker_index": np.arange(len(speakers)), "fault_gain_db": gains, "fault_delay_ms": delays, "ideal_direct_arrival_ms_at_reference": direct_time, "faulted_direct_arrival_ms_at_reference": direct_time + delays, "arrival_provenance": "known synthetic direct-path travel time plus injected electronics delay; not estimated from a measurement"},
        "fit_diagnostics": {key: value for key, value in fit.items() if key != "G"},
        "matrices": matrices,
        "heatmaps": heatmaps,
        "regularization_tradeoff": tradeoff,
        "interpretation": {"nrmse": "20 log10(norm(actual-target)/norm(target)); lower is better; 0 dB means error norm equals target norm", "improvement_db": "raw_nrmse_db minus corrected_nrmse_db; negative means correction worsened this metric", "rank": "rank below speaker count means unobserved speaker-space degrees of freedom", "null_values": "null means undefined or infinite, never a measured zero", "validation": "Choose settings on training/calibration data; repeatedly tuning against these held-out scores makes them validation data and requires a fresh final test set"},
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_demo()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    else:
        summary = {split: {k: v for k, v in metrics.items() if not isinstance(v, list)} for split, metrics in result["metrics"].items()}
        print(json.dumps(summary, indent=2, allow_nan=False))
