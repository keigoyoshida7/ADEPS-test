"""Deployable composition selected without final-test reference coefficients.

The configuration is explicit and portable. No dataset path, reference, source
direction or evaluation score enters this reconstruction interface.
"""
from plus_hybrid import reconstruct as hybrid
from plus_consistency import reconstruct as consistency


def reconstruct(p, v, frequencies, prior, selection, *, denoiser=True):
    config = dict(selection['configuration'])
    if config.get('stft_iterations', 0) != 0:
        raise ValueError('The selected composition requires a separately recorded final consistency stage')
    if not denoiser:
        config['relaxation'] = 0.
    result = hybrid(p, v, frequencies, prior, **config)
    iterations = selection['post_iterations']
    if type(iterations) is not int or not 0 <= iterations <= 10000:
        raise ValueError('Invalid final consistency iteration count')
    if iterations:
        post = consistency(p, v, frequencies, initial=result['estimate'], iterations=iterations,
                           ridge_relative=selection['post_ridge_relative'])
        result['estimate'] = post['estimate']
        result['post_trace'] = post['trace']
        result['post_diagnostics'] = {key: value for key, value in post.items() if key not in ('estimate', 'trace')}
    result['selection'] = {'configuration':config, 'post_iterations':iterations,
                           'post_ridge_relative':selection['post_ridge_relative']}
    result['method'] = 'independent_spatial_diffusion_prior_consistency_hybrid' if denoiser else 'same_hybrid_without_learned_denoiser'
    return result
