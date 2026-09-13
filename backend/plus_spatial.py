"""Experimental observation-only directional/covariance Ambisonics estimator.

This is an independent analytic candidate, not an implementation of COMPASS,
the McCormack et al. encoder, or an official ADEPS model.  It accepts only the
microphone spectra, the known complex acquisition matrix, and frequencies.
There is deliberately no interface for reference coefficients or source DOAs.

References informing the design (not claims of algorithmic equivalence):
  https://doi.org/10.1109/TASLP.2022.3182857
  https://acris.aalto.fi/ws/portalfiles/portal/30261835/ELEC_COMPASS_ICASSP2018_APolitis_STervo.pdf
  https://arxiv.org/abs/2501.08047
"""
import numpy as np
from scipy.optimize import nnls

from capture import real_n3d


def _sphere(count):
    z = 1. - 2. * (np.arange(count) + .5) / count
    phi = np.arange(count) * np.pi * (3. - np.sqrt(5.))
    radius = np.sqrt(1. - z * z)
    return np.c_[radius * np.cos(phi), radius * np.sin(phi), z]


def _hermitian(a):
    return .5 * (a + a.conj().swapaxes(-1, -2))


def _directions(p, v, frequencies, dictionary, count, lo, hi, loading, separation):
    band = (frequencies >= lo) & (frequencies <= hi)
    power = np.mean(np.abs(p)**2, axis=(1, 2))
    # Relative machine-precision exclusion only; no target-dependent activity
    # threshold and no search for an alternative band if the declared one fails.
    band &= power > np.max(power) * np.finfo(float).eps
    acquisition_power = np.mean(np.abs(v)**2, axis=(1, 2))
    band &= acquisition_power > np.max(acquisition_power) * np.finfo(float).eps
    if not np.any(band):
        return [], {'status': 'no_observed_energy_in_analysis_band', 'frequency_bins': 0}
    vb, pb = v[band], p[band]
    diffuse = _hermitian(vb @ vb.conj().transpose(0, 2, 1))
    eigenvalues, eigenvectors = np.linalg.eigh(diffuse)
    floor = np.maximum(loading * np.mean(eigenvalues, axis=1), np.finfo(float).tiny)
    invroot = 1. / np.sqrt(np.maximum(eigenvalues, floor[:, None]))
    whitening = (eigenvectors * invroot[:, None, :]) @ eigenvectors.conj().transpose(0, 2, 1)
    observed = whitening @ pb
    templates = (whitening @ vb) @ dictionary.T
    initial_energy = np.sum(abs(observed)**2, axis=(1, 2))
    usable = initial_energy > np.max(initial_energy) * np.finfo(float).eps
    observed, templates, initial_energy = observed[usable], templates[usable], initial_energy[usable]
    if not len(initial_energy):
        return [], {'status': 'no_usable_whitened_observation', 'frequency_bins': 0}
    directions = _sphere(dictionary.shape[0])
    selected, summaries = [], []
    for _ in range(count):
        covariance = observed @ observed.conj().transpose(0, 2, 1)
        template_norm = np.sum(abs(templates)**2, axis=1)
        numerator = np.einsum('fqd,fqr,frd->fd', templates.conj(), covariance, templates).real
        denominator = template_norm * initial_energy[:, None]
        score = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
        # Equal weight per predeclared analysis frequency. Absolute source power
        # is estimated separately from the original (unwhitened) covariance.
        average = np.maximum(0., np.mean(score, axis=0))
        eligible = np.ones(len(directions), dtype=bool)
        for previous in selected:
            eligible &= directions @ directions[previous] < np.cos(np.deg2rad(separation))
        if not np.any(eligible) or np.max(average[eligible]) <= np.finfo(float).eps:
            break
        peak = int(np.argmax(np.where(eligible, average, -np.inf)))
        selected.append(peak)
        median = float(np.median(average[eligible]))
        summaries.append({'dictionary_index': peak, 'score': float(average[peak]),
                          'eligible_median_score': median,
                          'score_above_median': float(average[peak] - median)})
        h = templates[:, :, peak]
        norm = np.sum(abs(h)**2, axis=1)
        invnorm = np.divide(1., norm, out=np.zeros_like(norm), where=norm > 0)
        coefficients = np.einsum('fq,fqt->ft', h.conj(), observed) * invnorm[:, None]
        observed = observed - h[:, :, None] * coefficients[:, None, :]
        # Deflate both data and remaining atoms for conditional source search.
        overlap = np.einsum('fq,fqd->fd', h.conj(), templates) * invnorm[:, None]
        templates = templates - h[:, :, None] * overlap[:, None, :]
    return selected, {'status': 'estimated' if selected else 'no_resolved_component',
                      'frequency_bins': int(np.sum(usable)), 'scores': summaries,
                      'whitening': 'Regularized inverse square root of V V^H; no measured target covariance.',
                      'component_count_is_requested_maximum': True}


def reconstruct_spatial(p, V, frequencies, *, direction_count=256, max_sources=2,
                        diffuse_weight=.25, regularization=.001,
                        analysis_low_hz=300., analysis_high_hz=2000.,
                        whitening_loading=.001, minimum_separation_deg=35.,
                        covariance_fit_loading=1e-6, noise_snr_db=None,
                        noise_real_endpoints=True):
    """Return an all-order estimate and JSON-safe observation-only diagnostics.

    Input p=[F,Q,T], V=[F,Q,C], C=(N+1)^2, real ACN/N3D conventions.
    A fixed spherical dictionary is rendered through V. Broadband, diffuse-
    whitened matched-power search selects at most two directions. Nonnegative
    least squares fits each frequency's observed sensor covariance to source
    atoms, V V^H diffuse covariance, and independent equal-power sensor noise.

    The fitted HOA covariance is shrunk toward trace(Ca)/C * I using
    diffuse_weight in [0,1]. Noise plus regularization times fitted per-sensor
    signal power loads the Wiener solve. This assumes uncorrelated directional
    components and does not guarantee correct coherent-reflection recovery.
    The covariance fit has a small positive ridge on normalized atom weights,
    ensuring a unique solution even for indistinguishable atoms (e.g. DC).
    A common observation maximum rescales numerical operations only. Returned
    coefficients have the original input's physical scale and channel order.

    Optional noise_snr_db is known synthetic SNR side information, not inferred
    SNR. It fixes white sensor noise using mean(|p|^2)/(1+10^(SNR/10)); no clean
    noise realization is accessed. With noise_real_endpoints=True the caller
    declares a complete one-sided STFT: DC and Nyquist noise have half the
    interior complex variance, while the pooled variance remains unchanged.
    The same SNR information must be provided to comparison methods.
    """
    p, v = np.asarray(p, dtype=np.complex128), np.asarray(V, dtype=np.complex128)
    f = np.asarray(frequencies, dtype=float)
    if p.ndim != 3 or v.ndim != 3 or p.shape[:2] != v.shape[:2] or min(p.shape + v.shape) <= 0:
        raise ValueError('Require p=[F,Q,T] and V=[F,Q,C] with matching nonempty F,Q')
    if f.shape != (p.shape[0],) or np.any(f < 0) or np.any(np.diff(f) <= 0):
        raise ValueError('Frequencies must be nonnegative and strictly ascending')
    if not all(np.all(np.isfinite(a)) for a in (p, v, f)):
        raise ValueError('Nonfinite pressure, acquisition matrix, or frequencies')
    channels = v.shape[2]
    order = int(np.sqrt(channels)) - 1
    if (order + 1)**2 != channels or order < 1 or channels > 256:
        raise ValueError('V must contain a complete order 1–15 real ACN/N3D basis')
    if isinstance(direction_count, bool) or not isinstance(direction_count, (int, np.integer)) or not 32 <= direction_count <= 4096:
        raise ValueError('direction_count must be an integer in 32..4096')
    if type(max_sources) is not int or not 0 <= max_sources <= 2:
        raise ValueError('max_sources must be 0, 1, or 2')
    settings = (diffuse_weight, regularization, analysis_low_hz, analysis_high_hz, whitening_loading, minimum_separation_deg, covariance_fit_loading)
    if not all(np.isfinite(value) for value in settings):
        raise ValueError('All estimator settings must be finite')
    if not 0 <= diffuse_weight <= 1 or not 1e-8 <= regularization <= 10 or not 1e-8 <= whitening_loading <= 10:
        raise ValueError('Invalid covariance shrinkage or relative loading')
    if not 0 < analysis_low_hz < analysis_high_hz or not 0 < minimum_separation_deg < 180:
        raise ValueError('Invalid analysis band or angular separation')
    if not 1e-10 <= covariance_fit_loading <= 1:
        raise ValueError('covariance_fit_loading must be positive and in 1e-10..1')
    if noise_snr_db is not None and (not np.isfinite(noise_snr_db) or not -20 <= noise_snr_db <= 120):
        raise ValueError('noise_snr_db must be None or a finite declared SNR in -20..120 dB')
    if type(noise_real_endpoints) is not bool:
        raise ValueError('noise_real_endpoints must be a bool')
    if noise_snr_db is not None and noise_real_endpoints:
        if len(f) < 2 or f[0] != 0 or not np.allclose(np.diff(f), f[1], rtol=1e-10, atol=1e-8):
            raise ValueError('Real endpoint noise requires the complete uniform one-sided STFT grid starting at DC')
        if np.max(abs(p[[0, -1]].imag)) > max(1e-12 * float(np.max(abs(p))), np.finfo(float).tiny):
            raise ValueError('Declared DC/Nyquist observations must be real')
    scale = float(np.max(abs(p)))
    method = 'Independent observation-only directional covariance Wiener candidate'
    diagnostics = {'schema': 'adeps-test-plus-spatial/1', 'oracle_used': False,
                   'official_implementation': False, 'reference_or_source_directions_used': False,
                   'sh_ordering': 'ACN', 'sh_normalization': 'N3D', 'order': order,
                   'direction_count': int(direction_count), 'max_sources': max_sources,
                   'diffuse_weight': float(diffuse_weight), 'regularization': float(regularization),
                   'analysis_band_hz': [float(analysis_low_hz), float(analysis_high_hz)],
                   'whitening_loading': float(whitening_loading),
                   'minimum_separation_deg': float(minimum_separation_deg),
                   'covariance_fit_loading': float(covariance_fit_loading),
                   'noise_snr_db': None if noise_snr_db is None else float(noise_snr_db),
                   'noise_real_endpoints': noise_real_endpoints if noise_snr_db is not None else None,
                   'noise_side_information': 'None; covariance fit estimates noise.' if noise_snr_db is None else 'Known synthetic pooled SNR supplied by caller; pressure-only noise power estimate. Comparisons must receive the same side information.',
                   'covariance_fit': 'Per-frequency ridge-regularized nonnegative least squares on unit-norm covariance atoms: directional + V V^H diffuse + I sensor noise.',
                   'diffuse_weight_definition': 'Shrink fitted HOA covariance toward an isotropic covariance with the same trace; 1 is fully isotropic.',
                   'regularization_definition': 'Estimated sensor-noise power plus relative loading times fitted mean sensor signal power.',
                   'source_statistics_assumption': 'Direction components are mutually uncorrelated; correlated early echoes can violate this model.',
                   'complex_scale': 'Common observed maximum magnitude for numerical scaling only; no reference-based normalization.'}
    if scale == 0:
        diagnostics.update(status='silent_observation', estimated_directions=[])
        return {'estimate': np.zeros((p.shape[0], channels, p.shape[2]), complex),
                'diagnostics': diagnostics, 'method': method}
    observed = p / scale
    fixed_noise = None
    if noise_snr_db is not None:
        pooled_noise = float(np.mean(abs(observed)**2) / (1 + 10**(noise_snr_db/10)))
        relative_variance = np.ones(len(f))
        if noise_real_endpoints:
            relative_variance[[0, -1]] = .5
        fixed_noise = pooled_noise * relative_variance / np.mean(relative_variance)
    directions = _sphere(direction_count)
    dictionary = real_n3d(order, directions)
    indexes, direction_info = _directions(observed, v, f, dictionary, max_sources,
                                         analysis_low_hz, analysis_high_hz,
                                         whitening_loading, minimum_separation_deg)
    chosen = dictionary[indexes]
    steering = v @ chosen.T
    covariance = _hermitian(observed @ observed.conj().transpose(0, 2, 1) / p.shape[2])
    diffuse = _hermitian(v @ v.conj().transpose(0, 2, 1))
    eye_q, eye_c = np.eye(p.shape[1]), np.eye(channels)
    estimates = np.empty((p.shape[0], channels, p.shape[2]), complex)
    powers = np.zeros((len(f), len(indexes) + 2))
    fit_errors, loads, posterior_trace = [], [], []
    for i in range(len(f)):
        source_atoms = [np.outer(steering[i, :, j], steering[i, :, j].conj()) for j in range(len(indexes))]
        atoms = [*source_atoms, diffuse[i], eye_q]
        design = np.stack([np.r_[a.real.ravel(), a.imag.ravel()] for a in atoms], axis=1)
        column_norm = np.linalg.norm(design, axis=0)
        valid = column_norm > np.finfo(float).tiny
        target = np.r_[covariance[i].real.ravel(), covariance[i].imag.ravel()]
        fit_columns = valid.copy()
        adjusted_target = target
        if fixed_noise is not None:
            fit_columns[-1] = False
            powers[i, -1] = fixed_noise[i]
            adjusted_target = target - design[:, -1] * fixed_noise[i]
        normalized = design[:, fit_columns] / column_norm[fit_columns]
        fit_design = np.vstack([normalized, np.sqrt(covariance_fit_loading) * np.eye(np.sum(fit_columns))])
        fit_target = np.r_[adjusted_target, np.zeros(np.sum(fit_columns))]
        fitted = nnls(fit_design, fit_target, maxiter=100)[0] if np.any(fit_columns) else np.empty(0)
        powers[i, fit_columns] = fitted / column_norm[fit_columns]
        ca = powers[i, -2] * eye_c
        for j, y in enumerate(chosen):
            ca = ca + powers[i, j] * np.outer(y, y)
        isotropic_power = float(np.trace(ca).real / channels)
        ca = (1 - diffuse_weight) * ca + diffuse_weight * isotropic_power * eye_c
        predicted = _hermitian(v[i] @ ca @ v[i].conj().T)
        sensor_power = max(0., float(np.trace(predicted).real / p.shape[1]))
        # The tiny floor is numerical, relative to this globally scaled clip.
        loading = max(float(powers[i, -1]) + regularization * sensor_power, 1e-12)
        e = np.linalg.solve(predicted + loading * eye_q, v[i] @ ca).conj().T
        estimates[i] = e @ observed[i]
        residual = design @ powers[i] - target
        denominator = float(np.linalg.norm(target))
        fit_errors.append(float(np.linalg.norm(residual) / denominator) if denominator else 0.)
        loads.append(loading * scale**2)
        posterior = _hermitian(ca - e @ v[i] @ ca)
        posterior_trace.append(max(0., float(np.trace(posterior).real)) * scale**2)
    estimates *= scale
    if not np.all(np.isfinite(estimates)):
        raise ValueError('Nonfinite covariance reconstruction')
    # p is real at DC/Nyquist only when supplied that way. Do not fabricate
    # endpoint projection here: the caller owns its STFT/WAV convention.
    diagnostics.update(status='estimated', direction_estimation=direction_info,
                       estimated_directions=[{'direction': directions[index].tolist(),
                           'azimuth_deg': float(np.rad2deg(np.arctan2(directions[index, 1], directions[index, 0]))),
                           'elevation_deg': float(np.rad2deg(np.arcsin(directions[index, 2]))),
                           'dictionary_index': int(index)} for index in indexes],
                       covariance_fit_relative_error_by_frequency=fit_errors,
                       fitted_component_power_by_frequency=(powers * scale**2).tolist(),
                       fitted_component_order=[*(f'direction_{j+1}' for j in range(len(indexes))), 'diffuse', 'sensor_noise'],
                       loading_power_by_frequency=loads,
                       posterior_trace_by_frequency=posterior_trace,
                       fixed_noise_power_by_frequency=None if fixed_noise is None else (fixed_noise * scale**2).tolist(),
                       posterior_is_model_based_uncertainty_not_measured_accuracy=True)
    return {'estimate': estimates, 'diagnostics': diagnostics, 'method': method}
