"""Regressions for physical conventions, held-out fitting and 19ch integrity."""
import copy
import unittest
import numpy as np
from capture import real_n3d
from zm1 import (zenith_xyz, fit_modal, inspect_audio, validate_profile,
                 make_audio_zip, SOFA_SHA256)
from neural_audio import prepare_zip


class ZM1Tests(unittest.TestCase):
    def test_zenith_does_not_silently_become_elevation(self):
        points = zenith_xyz([[0, 0, 1], [0, 90, 1], [90, 90, 2], [0, 180, 1]])
        np.testing.assert_allclose(points, [[0,0,1], [1,0,0], [0,2,0], [0,0,-1]], atol=1e-14)
        # Independent cardinal check of the existing SH convention.
        np.testing.assert_allclose(real_n3d(1, points),
            [[1,0,np.sqrt(3),0], [1,0,0,np.sqrt(3)],
             [1,np.sqrt(3),0,0], [1,0,-np.sqrt(3),0]], atol=1e-14)

    def test_complex_fit_recovers_known_modes_and_excludes_holdout(self):
        rng = np.random.default_rng(28)
        d = rng.normal(size=(200,3)); d /= np.linalg.norm(d, axis=1)[:,None]
        truth = rng.normal(size=(3,19,36))+1j*rng.normal(size=(3,19,36))
        h = np.einsum('fqc,dc->fqd', truth, real_n3d(5,d))
        train = np.arange(200)%5 != 0
        v = fit_modal(h,d,np.ones(200),train)
        np.testing.assert_allclose(v, truth, atol=2e-13)
        h[:,:,~train] = 1e9+4e8j
        np.testing.assert_array_equal(fit_modal(h,d,np.ones(200),train),v)

    def test_raw_audio_rejects_wrong_format_and_reports_integrity(self):
        rng = np.random.default_rng(18)
        audio = rng.normal(size=(4800,19))*.01
        self.assertTrue(inspect_audio(48000,audio)['ready_for_packaging'])
        for rate,a in [(16000,audio),(48000,audio[:,:4])]:
            with self.assertRaises(ValueError): inspect_audio(rate,a)
        for problem in ('silent','clip','duplicate'):
            a=audio.copy()
            if problem=='silent': a[:,2]=0
            if problem=='clip': a[300,2]=1
            if problem=='duplicate': a[:,2]=a[:,4]
            self.assertFalse(inspect_audio(48000,a)['ready_for_packaging'])

    def test_profile_grid_and_existing_zip_importer(self):
        rng = np.random.default_rng(1)
        v = rng.normal(size=(129,19,36))+1j*rng.normal(size=(129,19,36))
        profile = dict(schema='adeps-test-zm1-response/1',source_sha256=SOFA_SHA256,
            sh_ordering='ACN',sh_normalization='N3D',analysis_sample_rate_hz=48000,
            n_fft=256,hop=128,frequencies_hz=np.fft.rfftfreq(256,1/48000).tolist(),
            V_real=v.real.tolist(),V_imag=v.imag.tolist(),microphone_positions_m=rng.normal(size=(19,3)).tolist(),
            response_status='test-only')
        audio = .01*rng.normal(size=(4800,19))
        payload = make_audio_zip(profile,audio,'synthetic test fixture')
        bundle,metadata,reference = prepare_zip(payload,{'duration_seconds':.1})
        np.testing.assert_allclose(bundle['V_real']+1j*bundle['V_imag'],v)
        self.assertEqual(bundle['p_real'].shape[1],19)
        self.assertIsNone(reference)
        wrong=copy.deepcopy(profile); wrong['frequencies_hz'][2]+=.1
        with self.assertRaises(ValueError): validate_profile(wrong)
        wrong=copy.deepcopy(profile); wrong['V_imag']=np.zeros((129,1,36)).tolist()
        with self.assertRaises(ValueError): validate_profile(wrong)
        audio[:,3]=audio[:,4]
        with self.assertRaises(ValueError): make_audio_zip(profile,audio,'duplicate')


if __name__=='__main__': unittest.main()
