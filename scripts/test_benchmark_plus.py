"""Deterministic CPU plumbing tests; no model, corpus or sealed test is read."""
import contextlib
import copy
import io
import json
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import benchmark_plus as b


def development_fixture(root,out):
    rows=[{'scene':scene,'regularization':10.**exponent,'nrmse_db':float((exponent+7)**2)}
          for scene in range(16) for exponent in range(-8,2)]
    summary=[{'regularization':10.**exponent,'mean_nrmse_db':float((exponent+7)**2)} for exponent in range(-8,2)]
    linear={'split':'validation','count':16,'rows':rows,'summary':summary,'selected':summary[1]}
    first=[];second=[]
    for steps,etas,target in [(32,[0.,1.,5.,20.,50.,100.],first),(150,[0.,1.,50.],second)]:
        for eta in etas:
            path=out/'development'/f'{steps}-{eta}'/'summary.json'
            b.save(path,{'fixture':'No inference; fixed arithmetic development score','eta':eta,'steps':steps})
            target.append({'steps':steps,'eta_prime':eta,'regularization':1e-7,'mean_nrmse_db':eta,
                           'summary_path':str(path.relative_to(root)),'summary_sha256':b.sha(path)})
    dps={'schema':'adeps-plus-dps-selection/1','count':16,'stage_1':first,'stage_2':second,
         'selected':second[0],'source_sha256':{}}
    chosen={'configuration':{'steps':8,'sigma_start':.3,'relaxation':.25,'use_stft_consistency':True,
                             'stft_iterations':0,'ridge_relative':1e-7},
            'post_iterations':50,'post_ridge_relative':.001,'scores':[-10.]*16,
            'mean_nrmse_db':-10.,'trained_denoiser_used':True}
    hybrid={'rows':[chosen],'selected':chosen,'no_denoiser_control':{'mean_nrmse_db':-11.}}
    return linear,dps,hybrid


def scene_fixture(index=0):
    frequencies,positions,v=b.expected_array()
    rng=np.random.default_rng(7229)
    reference=.1*(rng.normal(size=(257,36,32))+1j*rng.normal(size=(257,36,32)))
    reference[[0,-1]]=reference[[0,-1]].real
    pressure=v@reference
    noise_rng=np.random.default_rng(850000+index)
    noise=noise_rng.normal(size=pressure.shape)+1j*noise_rng.normal(size=pressure.shape)
    noise[[0,-1]]=noise[[0,-1]].real
    amplitude=np.linalg.norm(pressure)/np.linalg.norm(noise)*10**(-50/20)
    audio={'files':[{'sha256':'fixture-speech','speaker':'speaker-0','split':'test'}]}
    specs=[{'id':f'fixture-{i}','cluster_id':f'pair-{i//8}','speaker_pair':['speaker-0','speaker-1'],
            'audio_indexes':[0],'sources_m':[[1.,2.,3.]]} for i in range(32)]
    manifest={'scenes':specs}
    metadata={**specs[index],'manifest_sha256':'fixture-manifest','split':'test','scene_index':index,
              'observation_seed':850000+index,'snr_db':50.,'microphones':6,'radius_m':.06,
              'sample_rate':16000,'n_fft':512,'hop':128,'frames':32,'target_sh_order':5,
              'target_normalization':'N3D','target_ordering':'ACN W,Y,Z,X','compression_applied':False,
              'normalization_applied':False,'reference_is_array_independent':True,
              'source_audio_sha256':['fixture-speech'],'noise_complex_variance':float(2*amplitude**2)}
    return {'p':pressure+amplitude*noise,'V':v.copy(),'reference':reference,
            'frequencies':frequencies.copy(),'positions':positions.copy()},metadata,manifest,audio


class BenchmarkPlumbingTests(unittest.TestCase):
    def test_strict_json_and_artifact_paths(self):
        for payload in ('{"x": NaN}','{"x": Infinity}','{"x": 1e400}','{"x": 1,"x": 2}'):
            with self.assertRaises(ValueError):b.parse_json(payload)
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(b.inside(directory,'a/b'),Path(directory).resolve()/'a/b')
            for value in ('../escape','/outside',''):
                with self.assertRaises(ValueError):b.inside(directory,value)

    def test_grid_selection_rejects_missing_scene_and_losing_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();linear,dps,hybrid=development_fixture(root,root/'work/plus-v1')
            b.validate_development_selection(linear,dps,hybrid)
            for which,mutate in [('linear',lambda x:x['rows'].pop()),
                                 ('linear',lambda x:x.update(selected=x['summary'][0])),
                                 ('dps',lambda x:x['stage_2'].pop()),
                                 ('dps',lambda x:x.update(selected=x['stage_2'][-1])),
                                 ('hybrid',lambda x:x['selected']['scores'].pop())]:
                values=copy.deepcopy({'linear':linear,'dps':dps,'hybrid':hybrid})
                mutate(values[which])
                with self.assertRaises(ValueError):b.validate_development_selection(**values)

    def test_seal_roundtrip_rejects_source_input_and_inventory_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();out=root/'work/plus-v1'
            sources=['scripts/benchmark_plus.py','scripts/select_plus_dps.py','backend/paper_inference.py']
            for name in sources:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture-source\n')
            weight=root/'work/paper-prior-v1/paper-prior-v1.pt';weight.parent.mkdir(parents=True);weight.write_bytes(b'fixture-not-weights')
            model_sha=b.sha(weight)
            b.save(weight.parent/'report.json',{'model':{'weights_sha256':model_sha}})
            sealed=out/'sealed-data';sealed.mkdir(parents=True)
            (sealed/'audio').mkdir();(sealed/'audio/fixture.wav').write_bytes(b'fixture-not-audio')
            (sealed/'upstream/HARP').mkdir(parents=True);(sealed/'upstream/HARP/README.md').write_text('fixture-upstream')
            (sealed/'source').mkdir();(sealed/'source/license.txt').write_text('fixture-attribution')
            b.save(sealed/'audio-manifest.json',{'files':[{'path':'audio/fixture.wav','sha256':b.sha(sealed/'audio/fixture.wav')}],
                'harp_upstream':{'commit':'fixture','files':[{'url':'https://raw.githubusercontent.com/whojavumusic/HARP/fixture/README.md',
                                                          'sha256':b.sha(sealed/'upstream/HARP/README.md')}]},
                'attribution_files':[{'path':'license.txt','sha256':b.sha(sealed/'source/license.txt')}]})
            for name in ('subset-plan.json','scene-manifest.json'):b.save(sealed/name,{'fixture':True})
            for name in ('audio-manifest.json','scene-manifest.json'):b.save(root/'work/paper-data'/name,{'fixture':True})
            for split,count in [('train',64),('validation',16)]:
                for index in range(count):
                    path=out/'cache'/split/f'{index:04d}.npz';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture-cache')
            linear,dps,hybrid=development_fixture(root,out)
            for name,value in [('linear-development.json',linear),('dps-selection.json',dps),('hybrid-development.json',hybrid)]:b.save(out/name,value)
            with patch.multiple(b,ROOT=root,OUT=out,SOURCES=sources,MODEL_SHA=model_sha),patch.object(b,'git_snapshot',return_value={'head_commit':'fixture-head','has_uncommitted_changes':True}),contextlib.redirect_stdout(io.StringIO()):
                b.seal();lock=b.verify_lock()
                self.assertEqual(lock['method_ids'],[row[0] for row in b.METHODS])
                self.assertEqual(len(lock['method_ids']),9)
                self.assertIn('scripts/select_plus_dps.py',lock['source_sha256'])
                self.assertTrue(lock['git']['has_uncommitted_changes'])
                with self.assertRaises(ValueError):b.seal()
                for target in (root/sources[0],sealed/'audio/fixture.wav'):
                    original=target.read_bytes();target.write_bytes(original+b'changed')
                    with self.assertRaises(ValueError):b.verify_lock()
                    target.write_bytes(original)
                damaged=copy.deepcopy(lock);damaged['source_sha256'].pop(sources[0]);damaged['source_set_sha256']=b.canonical_sha(damaged['source_sha256'])
                b.save(out/'selection-lock.json',damaged)
                with self.assertRaises(ValueError):b.verify_lock()

    def test_actual_cache_fixture_binds_observation_and_metadata(self):
        data,metadata,manifest,audio=scene_fixture()
        b.validate_final_scene(data,metadata,0,manifest,audio,'fixture-manifest')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'0000.npz'
            np.savez_compressed(path,**data,metadata_json=json.dumps(metadata))
            loaded,record=b.load_final_scene(path,0,manifest,audio,'fixture-manifest')
            np.testing.assert_array_equal(loaded['reference'],data['reference'])
            self.assertEqual(record,metadata)
        for key,value in [('scene_index',1),('source_audio_sha256',['different']),('normalization_applied',True),('noise_complex_variance',0.)]:
            altered={**metadata,key:value}
            with self.assertRaises(ValueError):b.validate_final_scene(data,altered,0,manifest,audio,'fixture-manifest')
        for key in ('p','V','reference','positions'):
            changed={**data,key:data[key].copy()};changed[key].flat[7]+=.1
            with self.assertRaises(ValueError):b.validate_final_scene(changed,metadata,0,manifest,audio,'fixture-manifest')

    def test_input_registration_is_immutable_and_requires_all_32(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();out=root/'work/plus-v1'
            b.save(out/'selection-lock.json',{'fixture':True})
            b.save(out/'sealed-data/audio-manifest.json',{'fixture':True})
            b.save(out/'sealed-data/scene-manifest.json',{'audio_manifest_sha256':b.sha(out/'sealed-data/audio-manifest.json')})
            cache=out/'cache/test';cache.mkdir(parents=True)
            for index in range(32):(cache/f'{index:04d}.npz').write_text(f'fixture input {index}')
            def load(path,index,*args):return {},{'id':f'scene-{index}','cluster_id':f'pair-{index//8}'}
            with patch.multiple(b,ROOT=root,OUT=out),patch.object(b,'load_final_scene',side_effect=load):
                with self.assertRaises(ValueError):b.pin_test_inputs({})
                first,_,_=b.pin_test_inputs({},create=True)
                again,_,_=b.pin_test_inputs({});self.assertEqual(first,again)
                (cache/'0007.npz').write_text('changed reference/observation container')
                with self.assertRaises(ValueError):b.pin_test_inputs({})
                (cache/'0007.npz').unlink()
                with self.assertRaises(ValueError):b.pin_test_inputs({},create=True)

    def test_saved_result_validation_checks_identity_hash_and_recomputed_metrics(self):
        data,metadata,_,_=scene_fixture()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            target=Path(directory)/'linear_default.npz'
            with patch.object(b,'run_method',return_value=(2*data['reference'],{'nfe':0,'vjp':0})) as run:
                record=b.record_case(target,'linear_default',0,metadata,data,'input-sha','lock-sha',None,{})
                self.assertEqual(set(run.call_args.args[1]),{'p','V','frequencies'})
            self.assertAlmostEqual(record['metrics']['nrmse_db'],0.,places=12)
            record_path=target.with_suffix('.json')
            self.assertEqual(b.validate_case(record_path,'linear_default',0,metadata,data,'input-sha','lock-sha'),record)
            for field,value in [('method','plus'),('input_sha256','different'),('estimate_sha256','different')]:
                b.save(record_path,{**record,field:value})
                with self.assertRaises(ValueError):b.validate_case(record_path,'linear_default',0,metadata,data,'input-sha','lock-sha')
            changed=copy.deepcopy(record);changed['metrics']['nrmse_db']=-9.;b.save(record_path,changed)
            with self.assertRaises(ValueError):b.validate_case(record_path,'linear_default',0,metadata,data,'input-sha','lock-sha')
            b.save(record_path,record)
            original=target.read_bytes();target.write_bytes(original+b'changed')
            with self.assertRaises(ValueError):b.validate_case(record_path,'linear_default',0,metadata,data,'input-sha','lock-sha')

    def test_failed_case_is_retained_never_retried_or_replaced_by_zero(self):
        data,metadata,_,_=scene_fixture()
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            target=Path(directory)/'plus.npz'
            with patch.object(b,'run_method',side_effect=RuntimeError('fixture failure')) as run:
                first=b.record_case(target,'plus',0,metadata,data,'input-sha','lock-sha',None,{})
                second=b.record_case(target,'plus',0,metadata,data,'input-sha','lock-sha',None,{})
                self.assertEqual(run.call_count,1)
            self.assertEqual(first,second);self.assertEqual(first['outcome'],'failed');self.assertIsNone(first['nfe'])
            self.assertFalse(target.exists());self.assertTrue(all(first['metrics'][key] is None for key in b.METRIC_KEYS))
            json.dumps(first,allow_nan=False)
            orphan=Path(directory)/'orphan.npz';orphan.write_bytes(b'fixture')
            with self.assertRaises(ValueError):b.record_case(orphan,'plus',0,metadata,data,'input-sha','lock-sha',None,{})

    def test_original_baseline_retains_all_order_scale_and_150_step_settings(self):
        data,_,_,_=scene_fixture()
        linear=np.ones_like(data['reference']);linear[:,4:]*=9
        encoder=np.zeros((257,36,6),complex)
        received={}
        def sample(value,matrix,prior,**kwargs):
            received.update(value=value.copy(),matrix=matrix.copy(),kwargs=kwargs)
            return np.ones_like(value),[]
        fake=types.ModuleType('paper_inference');fake.sample=sample
        with patch.dict('sys.modules',{'paper_inference':fake}),patch.object(b,'encode',return_value=(linear,encoder,None)) as encode:
            estimate,diagnostics=b.run_method('adeps_current',data,None,{'linear_regularization':1e-7,'dps':{'eta_prime':1.,'regularization':1e-7}})
        self.assertEqual(encode.call_args.args[2],.001)
        self.assertEqual(received['kwargs'],{'steps':150,'eta_prime':50.,'seed':42})
        scale=float(np.sqrt(np.mean(abs(linear)**2)))
        self.assertGreater(scale,1.)
        np.testing.assert_allclose(received['value'],b.compress(linear/scale))
        np.testing.assert_allclose(estimate,scale)
        self.assertEqual((diagnostics['nfe'],diagnostics['vjp']),(150,150))

    def test_complete_report_keeps_failed_case_and_missing_record_blocks_publication(self):
        # Arithmetic result fixtures exercise orchestration and aggregation;
        # actual estimate rescoring is tested separately above.
        with tempfile.TemporaryDirectory() as directory,contextlib.redirect_stdout(io.StringIO()):
            root=Path(directory).resolve();out=root/'work/plus-v1'
            b.save(out/'selection-lock.json',{'fixture':True});lock_sha=b.sha(out/'selection-lock.json')
            environment={'selection_lock_sha256':lock_sha,'device':'fixture CPU'}
            b.record_environment(out/'final/environment.json',environment)
            b.record_environment(out/'final/environment.json',environment)
            with self.assertRaises(ValueError):b.record_environment(out/'final/environment.json',{**environment,'device':'different'})
            pin={'scene_manifest_sha256':'fixture','cases':[{'sha256':f'input-{i}'} for i in range(32)]}
            b.save(out/'final/input-lock.json',pin)
            lock={'selection':{'fixture':True},'primary_comparisons':['linear_tuned','adeps_current'],
                  'git':{'head_commit':'fixture'},'source_sha256':{},'source_set_sha256':'fixture',
                  'input_sha256':{},'input_set_sha256':'fixture'}
            data={'reference':np.ones((257,36,32),complex)}
            def load(path,index,*args):return data,{'id':f'scene-{index}','cluster_id':f'pair-{index//8}',
                                                     'speaker_pair':['fixtureA','fixtureB'],'sources_m':[[1,2,3]]}
            for index in range(32):
                for identifier,_,_,_,nfe in b.METHODS:
                    score=-2. if identifier=='plus' else -1.
                    metrics={key:.5 if key=='coherence' else 1. if key=='magnitude_error_db' else score for key in b.METRIC_KEYS}
                    curves={key:[.5 if key=='magnitude_squared_coherence' else 1. if key=='magnitude_spectrum_error_db' else score]*257 for key in b.CURVE_KEYS}
                    case={'metrics':metrics,'curves':curves,'details':{},'outcome':'completed','seconds':.25,'nfe':nfe,'vjp':0,'memory':{}}
                    if (index,identifier)==(0,'plus'):
                        case.update(outcome='failed',nfe=None,vjp=None)
                        case['metrics']={**{key:None for key in b.METRIC_KEYS},'status':'failure'}
                        case['curves']={key:[None]*257 for key in b.CURVE_KEYS}
                    b.save(out/'final'/f'{index:04d}'/f'{identifier}.json',case)
            with patch.multiple(b,ROOT=root,OUT=out),patch.object(b,'verify_lock',return_value=lock),patch.object(b,'pin_test_inputs',return_value=(pin,{},{})),patch.object(b,'load_final_scene',side_effect=load),patch.object(b,'validate_case',side_effect=lambda path,*args:b.read_json(path)):
                b.report();result=b.read_json(out/'benchmark.json')
                self.assertEqual(len(result['methods']),9);self.assertEqual(len(result['scenes']),32)
                plus=next(method for method in result['methods'] if method['id']=='plus')
                self.assertEqual((plus['completed'],plus['failed']),(31,1));self.assertIsNone(plus['nfe'])
                self.assertIsNone(plus['mean_nrmse_db']);self.assertFalse(result['primary_passed'])
                self.assertEqual(plus['valid_counts']['metrics']['nrmse_db'],31)
                self.assertEqual(result['conditions']['evaluated_audio_samples'],3968)
                previous=b.sha(out/'benchmark.json')
                (out/'final/0003/linear_default.json').unlink()
                with self.assertRaises(FileNotFoundError):b.report()
                self.assertEqual(b.sha(out/'benchmark.json'),previous)

    def test_git_snapshot_reports_real_head_and_dirty_content_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            def git(*args):return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True).stdout.decode().strip()
            git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
            (root/'a').write_text('first');git('add','a');git('commit','-m','fixture')
            clean=b.git_snapshot(root)
            self.assertEqual(clean['head_commit'],git('rev-parse','HEAD'));self.assertFalse(clean['has_uncommitted_changes'])
            (root/'a').write_text('second');(root/'untracked').write_text('third')
            dirty=b.git_snapshot(root)
            self.assertTrue(dirty['has_uncommitted_changes']);self.assertEqual(dirty['head_commit'],clean['head_commit'])
            self.assertNotEqual(dirty['working_tree_sha256'],clean['working_tree_sha256'])
            self.assertEqual(dirty['working_tree_file_count'],2)


if __name__=='__main__':unittest.main(verbosity=2)
