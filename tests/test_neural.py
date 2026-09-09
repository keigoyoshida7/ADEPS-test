"""Scientific regressions for the independent neural sampler and audio interchange."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft
import neural
from neural_audio import example_zip, prepare_zip, inverse_spectra, run_audio, si_sdr
from numerics import to_jsonable


def small_bundle(reference=True):
    rng = np.random.default_rng(502)
    v = (rng.normal(size=(3,6,36))+1j*rng.normal(size=(3,6,36)))/6
    a = rng.normal(size=(3,36,4))+1j*rng.normal(size=(3,36,4))
    p = v@a
    bundle = {'schema':'adeps-test-array-stft/1','sh_ordering':'ACN','sh_normalization':'N3D',
              'frequencies_hz':[100,400,1600], 'V_real':v.real.tolist(),'V_imag':v.imag.tolist(),
              'p_real':p.real.tolist(),'p_imag':p.imag.tolist()}
    if reference:
        bundle.update(reference_real=a[:,:4].real.tolist(),reference_imag=a[:,:4].imag.tolist())
    return bundle


class NeuralMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = neural.TinyDenoiser()

    def test_compression_inverse_including_zero_extension(self):
        z = np.array([0,1e-12+2e-12j,.3+.4j,2+3j,-1j])
        np.testing.assert_allclose(neural.expand(neural.compress(z)),z,rtol=1e-13,atol=1e-24)

    def test_radial_real_euclidean_vjp(self):
        rng = np.random.default_rng(12)
        z = rng.normal(size=20)+1j*rng.normal(size=20)
        direction = rng.normal(size=20)+1j*rng.normal(size=20)
        g = rng.normal(size=20)+1j*rng.normal(size=20)
        for inverse, fn in [(False,neural.compress),(True,neural.expand)]:
            delta = 1e-6
            finite = np.real(np.vdot(g,(fn(z+delta*direction)-fn(z-delta*direction))/(2*delta)))
            exact = np.real(np.vdot(neural.radial_vjp(z,g,inverse),direction))
            self.assertAlmostEqual(finite,exact,places=7)

    def test_full_likelihood_gradient_includes_denoiser(self):
        rng = np.random.default_rng(51)
        x = rng.normal(size=(2,36,3))+1j*rng.normal(size=(2,36,3))
        direction = rng.normal(size=x.shape)+1j*rng.normal(size=x.shape)
        ev = (rng.normal(size=(2,36,36))+1j*rng.normal(size=(2,36,36)))/40
        y = x*.4
        for sigma in [.05,.7,20.]:
            _,_,gradient = neural.consistency(x,sigma,y,ev,self.model)
            delta = 1e-5
            finite = (neural.consistency(x+delta*direction,sigma,y,ev,self.model)[1]-
                      neural.consistency(x-delta*direction,sigma,y,ev,self.model)[1])/(2*delta)
            exact = np.real(np.vdot(gradient,direction))
            self.assertAlmostEqual(finite,exact,delta=2e-6*max(1,abs(exact)))

    def test_model_checksum_is_enforced(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            for name in ['tiny-spatial-v1.json','tiny-spatial-v1.npz']:
                (p/name).write_bytes((neural.MODEL_DIR/name).read_bytes())
            with (p/'tiny-spatial-v1.npz').open('ab') as out:
                out.write(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):
                neural.TinyDenoiser(p)

    def test_schedule_exactly_150_updates_and_explicit_terminal(self):
        s = neural.schedule(150)
        self.assertEqual(len(s),151)
        self.assertAlmostEqual(s[0],20)
        self.assertAlmostEqual(s[-2],.002)
        self.assertEqual(s[-1],0)
        self.assertTrue(np.all(np.diff(s)<0))
        for steps in [1,301,150.5,True]:
            with self.assertRaises(ValueError): neural.schedule(steps)

    def test_zero_gradient_does_not_divide_by_zero(self):
        class Identity:
            def predict(self,x,sigma):return x,lambda g:g
        y = np.zeros((2,36,2),complex)
        ev = np.zeros((2,36,36),complex)
        output, trace = neural.sample(y,ev,Identity(),steps=3)
        self.assertTrue(np.all(np.isfinite(output)))
        self.assertTrue(all(row['gradient_norm']==0 and row['guidance_update_norm']==0 for row in trace))

    def test_reproducible_outputs_and_reference_never_enters_inference(self):
        b = small_bundle()
        r = neural.run_neural({'bundle':b,'steps':5},model=self.model)
        changed = copy.deepcopy(b)
        changed['reference_real'] = (np.asarray(b['reference_real'])*100).tolist()
        changed['reference_imag'] = (np.asarray(b['reference_imag'])*100).tolist()
        r2 = neural.run_neural({'bundle':changed,'steps':5},model=self.model)
        np.testing.assert_array_equal(r['output']['neural_real'],r2['output']['neural_real'])
        self.assertEqual(r['configuration']['observation_rms_scale'],r2['configuration']['observation_rms_scale'])
        self.assertEqual(r['input_sha256'],r2['input_sha256'])

    def test_no_reference_means_no_quality_claim(self):
        r = neural.run_neural({'bundle':small_bundle(False),'steps':3},model=self.model)
        self.assertIsNone(r['quality']['neural']['nrmse_db'])
        self.assertIsNone(r['quality']['neural']['coherence'])
        self.assertFalse(r['paper_performance_reproduced'])
        self.assertFalse(r['official_model'])
        json.dumps(to_jsonable(r),allow_nan=False)

    def test_invalid_order_conventions_and_silent_data_reject(self):
        for change in ('order','normalization','microphones','silence','reference'):
            b = small_bundle()
            if change == 'order':
                for key in ['V_real','V_imag']: b[key]=np.asarray(b[key])[:,:,:4].tolist()
            elif change == 'normalization': b['sh_normalization']='SN3D'
            elif change == 'silence':
                for key in ['p_real','p_imag']: b[key]=np.zeros_like(b[key]).tolist()
            elif change == 'reference': b['reference_real'][0][0][0]=float('nan')
            else:
                for key in ['V_real','V_imag','p_real','p_imag']: b[key]=np.asarray(b[key])[:,:3].tolist()
            with self.assertRaises(ValueError): neural.run_neural({'bundle':b,'steps':3},model=self.model)

    def test_seed_changes_posterior_sample(self):
        config={'bundle':small_bundle(),'steps':3}
        a=neural.run_neural({**config,'seed':1},model=self.model)
        b=neural.run_neural({**config,'seed':2},model=self.model)
        self.assertFalse(np.allclose(a['output']['neural_real'],b['output']['neural_real']))


class NeuralAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.archive=example_zip()

    def test_stft_istft_roundtrip_preserves_phase_channels_and_gain(self):
        bundle, metadata, ref = prepare_zip(self.archive,{'duration_seconds':.1})
        spectrum=bundle['reference_real']+1j*bundle['reference_imag']
        np.testing.assert_allclose(inverse_spectra(spectrum,metadata),ref,atol=1e-14)

    def test_segment_bounds_and_capacity_reject(self):
        for cfg in [{'start_seconds':10},{'duration_seconds':1}, {'duration_seconds':.8}]:
            with self.assertRaises(ValueError):prepare_zip(self.archive,cfg)

    def test_audio_export_shared_gain_and_sn3d_conversion(self):
        result,payload=run_audio(self.archive,{'steps':3,'duration_seconds':.05})
        gain=result['audio']['shared_export_gain']
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for name in ('linear','neural'):
                rate,a=wavfile.read(io.BytesIO(archive.read(f'{name}_FOA_ACN_N3D.wav')))
                _,b=wavfile.read(io.BytesIO(archive.read(f'{name}_FOA_ACN_SN3D.wav')))
                spectrum=result['output'][name+'_real']+1j*result['output'][name+'_imag']
                np.testing.assert_allclose(a,inverse_spectra(spectrum,result['audio'])*gain,atol=4e-8)
                np.testing.assert_allclose(b,a/np.sqrt([1,3,3,3]),atol=4e-8)
                self.assertEqual(a.shape,(800,4))
                self.assertEqual(rate,16000)
            saved=json.loads(archive.read('result.json'))
            self.assertEqual(saved['model']['weights_sha256'],result['model']['weights_sha256'])

    def test_si_sdr_scale_invariance_and_silent_reference(self):
        rng=np.random.default_rng(42)
        ref=rng.normal(size=(1000,4)); a=ref+.1*rng.normal(size=ref.shape)
        np.testing.assert_allclose(si_sdr(a,ref)['by_channel_db'],si_sdr(a*3,ref)['by_channel_db'],atol=1e-12)
        self.assertIsNone(si_sdr(a,np.zeros_like(ref))['mean_valid_channels_db'])
        self.assertIsNone(si_sdr(a,None))


if __name__=='__main__':unittest.main()
