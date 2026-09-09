import io,json,unittest,zipfile
import numpy as np
from measurements import sample_zip,analyze_bundle
from capture import run_capture
from test_capture import make_bundle

class ImportTests(unittest.TestCase):
    def altered(self,change):
        out=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(sample_zip())) as old,zipfile.ZipFile(out,'w') as new:
            m=json.loads(old.read('manifest.json'));change(m)
            for n in old.namelist():new.writestr(n,json.dumps(m) if n=='manifest.json' else old.read(n))
        return out.getvalue()
    def test_ir_preserves_shared_time_origin_and_label(self):
        r=analyze_bundle(sample_zip())
        self.assertEqual(r['provenance'],'synthetic_fixture_not_a_measurement')
        self.assertAlmostEqual(r['diagnostics']['onset_ms'][0][0],7.25)
        self.assertEqual(r['sample_rate'],48000)
        self.assertIn('heldout',r['metrics'])
        json.dumps(r,allow_nan=False)
    def test_no_target_has_no_quality_score(self):
        r=analyze_bundle(self.altered(lambda m:m.pop('target_files')))
        self.assertFalse(r['target_available']);self.assertNotIn('metrics',r)
    def test_train_and_validation_overlap_rejects(self):
        with self.assertRaises(ValueError):analyze_bundle(self.altered(lambda m:m.update(heldout_indices=[0,5])))
    def test_silent_foa_coefficient_does_not_reduce_coherence(self):
        b=make_bundle()
        for key in ['p_real','p_imag','reference_real','reference_imag']:
            a=np.asarray(b[key]);a[:,2,:]=0;b[key]=a.tolist()
        r=run_capture({'bundle':b,'regularization':1e-8})
        self.assertAlmostEqual(r['quality']['coherence'],1,places=12)
        self.assertEqual(r['quality']['coherence_valid_bins'],6)
    def test_foa_import_requires_convention_and_four_coefficients(self):
        b=make_bundle(reference=False);b['sh_ordering']='FuMa'
        with self.assertRaises(ValueError):run_capture({'bundle':b})
        with self.assertRaises(ValueError):run_capture({'bundle':make_bundle(reference=False,C=1)})

if __name__=='__main__':unittest.main()
