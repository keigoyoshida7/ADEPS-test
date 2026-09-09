"""Independent, bounded final review regressions; app checkout is read-only."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('capture_final_review', BASE / 'backend/capture.py')
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)

def bundle(F=2,Q=4,C=4,T=12,reference=True):
    rng=np.random.default_rng(92)
    V=np.broadcast_to(np.eye(Q,C),(F,Q,C)).copy()
    p=rng.normal(size=(F,Q,T))+1j*rng.normal(size=(F,Q,T))
    out={'schema':'adeps-test-array-stft/1','sh_ordering':'ACN','sh_normalization':'N3D',
         'frequencies_hz':[100,400],'V_real':V.tolist(),'V_imag':np.zeros_like(V).tolist(),
         'p_real':p.real.tolist(),'p_imag':p.imag.tolist()}
    if reference:out.update(reference_real=p[:,:4].real.tolist(),reference_imag=p[:,:4].imag.tolist())
    return out

class FinalCaptureReview(unittest.TestCase):
    def test_silent_observation_residual_is_undefined(self):
        b=bundle(reference=False)
        for k in ['p_real','p_imag']:b[k]=np.zeros((2,4,12)).tolist()
        r=capture.run_capture({'bundle':b})
        self.assertTrue(all(x is None for x in r['curves']['residual_db']))
        json.dumps(r,allow_nan=False)

    def test_mixed_silent_and_valid_coherence_bins(self):
        b=bundle()
        for k in ['p_real','p_imag','reference_real','reference_imag']:
            a=np.array(b[k]);a[:,2,:]=0;b[k]=a.tolist()
        r=capture.run_capture({'bundle':b,'regularization':1e-8})
        self.assertEqual(r['quality']['coherence_valid_bins'],6)
        self.assertAlmostEqual(r['quality']['coherence'],1,places=12)

    def test_zero_output_has_undefined_coherence_and_zero_db_error(self):
        b=bundle()
        for k in ['p_real','p_imag']:b[k]=np.zeros((2,4,12)).tolist()
        r=capture.run_capture({'bundle':b})
        self.assertIsNone(r['quality']['coherence'])
        self.assertEqual(r['quality']['coherence_valid_bins'],0)
        self.assertAlmostEqual(r['quality']['complex_nrmse_db'],0)

    def test_sn3d_declared_v_reference_stays_consistent(self):
        b=bundle();b['sh_normalization']='SN3D'
        r=capture.run_capture({'bundle':b,'regularization':1e-8})
        self.assertIn('ACN/SN3D',r['conventions'])
        self.assertLess(r['quality']['complex_nrmse_db'],-150)

    def test_unknown_or_missing_sh_convention_rejects(self):
        for key,value in [('sh_ordering','FuMa'),('sh_ordering',None),('sh_normalization','unknown')]:
            b=bundle();b[key]=value
            with self.assertRaises(ValueError):capture.run_capture({'bundle':b})

    def test_derived_encoding_size_rejects_before_allocation(self):
        # V and p are tiny, but output F*C*T exceeds three million complex values.
        # Mock prevents the reviewed implementation from doing the expansion.
        b=bundle(F=2,Q=1,C=256,T=6000,reference=False)
        with patch.object(capture,'encode',side_effect=AssertionError('encoder called before expanded size guard')):
            with self.assertRaises(ValueError):capture.run_capture({'bundle':b})

if __name__=='__main__':unittest.main(verbosity=2)
