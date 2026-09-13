"""Seal, run, and report the first ADEPS+ held-out benchmark.

Selection is made from development records only. The final test is never
consulted by the selection function, and resuming requires the same inputs,
settings, checkpoint, metrics, and estimator source hashes.
"""
import argparse
import gc
import hashlib
import json
import platform
import math
import os
import subprocess
import sys
import time
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'scripts'))
from plus_experiments import OUT, save
from capture import encode, modal_matrix
from neural import compress
from plus_metrics import evaluate_metrics, aggregate, paired_comparison, DOMAIN, METRIC_KEYS, CURVE_KEYS

SOURCES=['scripts/benchmark_plus.py','scripts/plus_data.py','scripts/paper_data.py',
         'scripts/plus_experiments.py','scripts/select_plus_dps.py',
         'backend/plus_system.py','backend/plus_hybrid.py','backend/plus_spatial.py',
         'backend/plus_diffusion.py','backend/plus_consistency.py','backend/plus_reconstruction.py',
         'backend/plus_metrics.py','backend/plus_covariance.py','backend/paper_inference.py','backend/paper_prior.py',
         'backend/capture.py','backend/neural.py','backend/diffusion_studio.py','backend/neural_audio.py',
         'backend/numerics.py','docs/PLUS_PROTOCOL.md','requirements-paper-training.txt']
METHODS=[
    ('linear_default','Linear・初期設定','Linear · default','linear',0),
    ('linear_tuned','Linear・調整済み','Linear · tuned','linear',0),
    ('linear_noise','等方Wiener・既知SNR','Isotropic Wiener · known SNR','ablation',0),
    ('adeps_current','既存ADEPS独自実装','Current independent ADEPS','adeps',150),
    ('adeps_tuned','ADEPS独自実装・調整済み','Independent ADEPS · tuned','adeps',150),
    ('spatial_only','方向共分散のみ','Directional covariance only','ablation',0),
    ('consistency_only','Linear＋波形整合','Linear + waveform consistency','ablation',0),
    ('plus','ADEPS + α・学習済み補正ON','ADEPS + α · learned refinement ON','plus',8),
    ('plus_no_denoiser','同じα処理・学習済み補正OFF','Same α processing · learned refinement OFF','ablation',0),
]
MODEL_SHA='0e88c717770453520331d797392794934c6eb167716007b44bb58633e811d7b2'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def parse_json(payload):
    def reject_constant(value):
        raise ValueError(f'Nonfinite JSON constant: {value}')
    def unique_keys(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError(f'Duplicate JSON key: {key}')
            result[key]=value
        return result
    def finite_float(value):
        result=float(value)
        if not math.isfinite(result):raise ValueError('Nonfinite JSON number: '+value)
        return result
    return json.loads(payload,parse_constant=reject_constant,parse_float=finite_float,object_pairs_hook=unique_keys)


def read_json(path):return parse_json(Path(path).read_text())


def inside(root,relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError('Expected a nonempty relative artifact path')
    candidate=(Path(root)/relative).resolve()
    if not candidate.is_relative_to(Path(root).resolve()):raise ValueError('Artifact path escapes its root')
    return candidate


def git_snapshot(root=ROOT):
    """Read Git identity and hash tracked/nonignored working-file contents.

    This is a recorded snapshot, not a clean-commit assertion. The explicit
    frozen source hashes remain authoritative after UI/artifact changes.
    """
    def git(*args):
        return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True).stdout
    head=git('rev-parse','HEAD').decode().strip()
    paths=sorted(set(path for path in git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0') if path))
    entries=[]
    for raw in paths:
        relative=os.fsdecode(raw); path=Path(root)/relative
        if path.is_symlink():
            entries.append([relative,'symlink',hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()])
        elif path.is_file():entries.append([relative,'file',sha(path)])
        else:entries.append([relative,'missing',None])
    status=git('status','--porcelain=v1','--untracked-files=all').decode()
    if git('rev-parse','HEAD').decode().strip()!=head:raise ValueError('Git HEAD changed while recording the seal')
    return {'head_commit':head,'branch':git('branch','--show-current').decode().strip(),
            'has_uncommitted_changes':bool(status),'status_porcelain':status,
            'working_tree_sha256':canonical_sha(entries),'working_tree_file_count':len(entries),
            'tracked_diff_sha256':hashlib.sha256(git('diff','--binary','--no-ext-diff','HEAD','--')).hexdigest(),
            'scope':'Tracked and nonignored untracked working-file bytes, symlink targets and missing-file markers. May be uncommitted; frozen source_sha256 is authoritative.'}


def source_input_paths():
    """Manifest plus declared upstream/attribution files; no audio rendering."""
    directory=OUT/'sealed-data'; audio=read_json(directory/'audio-manifest.json')
    paths=[]
    for item in audio['files']:
        target=inside(directory,item['path'])
        if sha(target)!=item['sha256']:raise ValueError('Final test audio checksum mismatch')
        paths.append(str(target.relative_to(ROOT)))
    upstream=audio['harp_upstream']
    prefix=f"https://raw.githubusercontent.com/whojavumusic/HARP/{upstream['commit']}/"
    for item in upstream['files']:
        if not item['url'].startswith(prefix):raise ValueError('Unexpected pinned HARP source URL')
        target=inside(directory/'upstream/HARP',item['url'][len(prefix):])
        if sha(target)!=item['sha256']:raise ValueError('Pinned HARP source checksum mismatch')
        paths.append(str(target.relative_to(ROOT)))
    for item in audio['attribution_files']:
        target=inside(directory/'source',item['path'])
        if sha(target)!=item['sha256']:raise ValueError('Attribution checksum mismatch')
        paths.append(str(target.relative_to(ROOT)))
    return paths


def verify_lock():
    path=OUT/'selection-lock.json'
    lock=read_json(path)
    if lock.get('schema')!='adeps-plus-selection-lock/1':raise ValueError('Invalid selection lock')
    if set(lock['source_sha256'])!=set(SOURCES):raise ValueError('Incomplete or unexpected frozen source inventory')
    if lock.get('source_set_sha256')!=canonical_sha(lock['source_sha256']):raise ValueError('Invalid frozen-source digest')
    for name,digest in lock['source_sha256'].items():
        if sha(inside(ROOT,name))!=digest:raise ValueError('Sealed source changed: '+name)
    for name,digest in lock['input_sha256'].items():
        if sha(inside(ROOT,name))!=digest:raise ValueError('Sealed input/checkpoint changed: '+name)
    if lock.get('input_set_sha256')!=canonical_sha(lock['input_sha256']):raise ValueError('Invalid frozen-input digest')
    if (lock.get('method_ids')!=[row[0] for row in METHODS] or lock.get('primary_comparisons')!=['linear_tuned','adeps_current']
        or (lock.get('primary_threshold_db'),lock.get('confidence_level'),lock.get('clusters'),lock.get('scenes'))!=(.5,.975,4,32)):
        raise ValueError('Frozen comparison design changed')
    if read_json(OUT/'selection.json')!=lock['selection']:raise ValueError('Selection disagrees with lock')
    if read_json(OUT/'dps-selection.json')['selected']!=lock['dps']:raise ValueError('DPS selection disagrees with lock')
    required={'work/plus-v1/sealed-data/subset-plan.json','work/plus-v1/sealed-data/audio-manifest.json',
              'work/plus-v1/sealed-data/scene-manifest.json','work/plus-v1/selection.json',
              'work/plus-v1/dps-selection.json','work/plus-v1/hybrid-development.json',
              'work/plus-v1/linear-development.json','work/paper-prior-v1/report.json',
              'work/paper-prior-v1/paper-prior-v1.pt',*source_input_paths()}
    if not required.issubset(lock['input_sha256']):raise ValueError('Incomplete frozen input inventory')
    if lock['selection'].get('model_weights_sha256')!=MODEL_SHA:raise ValueError('The preregistered checkpoint changed')
    return lock


def validate_development_selection(linear,dps,hybrid):
    """A seal cannot turn partial grids or a non-winning candidate into final."""
    grid=[10.**power for power in range(-8,2)]
    if (linear.get('count'),linear.get('split'))!=(16,'validation') or len(linear['rows'])!=160:
        raise ValueError('Complete ten-gamma Linear selection on all 16 development scenes is required')
    if [row['regularization'] for row in linear['summary']]!=grid:raise ValueError('Linear gamma grid changed')
    for candidate in linear['summary']:
        rows=[row for row in linear['rows'] if row['regularization']==candidate['regularization']]
        if sorted(row['scene'] for row in rows)!=list(range(16)) or not math.isclose(float(np.mean([row['nrmse_db'] for row in rows])),candidate['mean_nrmse_db'],rel_tol=0,abs_tol=1e-8):
            raise ValueError('Incomplete or inconsistent Linear development candidate')
    if linear['selected']!=min(linear['summary'],key=lambda row:row['mean_nrmse_db']):raise ValueError('Linear selection is not the full-band winner')
    etas=[0.,1.,5.,20.,50.,100.]
    if [row['eta_prime'] for row in dps['stage_1']]!=etas or any(row['steps']!=32 for row in dps['stage_1']):
        raise ValueError('DPS first-stage grid is incomplete')
    promoted=sorted(set([row['eta_prime'] for row in sorted(dps['stage_1'],key=lambda row:(row['mean_nrmse_db'],etas.index(row['eta_prime'])))[:2]]+[50.]),key=etas.index)
    if [row['eta_prime'] for row in dps['stage_2']]!=promoted or any(row['steps']!=150 for row in dps['stage_2']):
        raise ValueError('DPS second-stage grid is incomplete or differs from the promotion rule')
    if dps['selected']!=min(dps['stage_2'],key=lambda row:(row['mean_nrmse_db'],etas.index(row['eta_prime']))):
        raise ValueError('DPS selection is not the full-budget winner')
    if any(row['regularization']!=linear['selected']['regularization'] for row in dps['stage_1']+dps['stage_2']):
        raise ValueError('DPS candidates do not share tuned Linear regularization')
    candidates=[row for row in hybrid['rows'] if row.get('trained_denoiser_used') is True]
    if not candidates or hybrid['selected']!=min(candidates,key=lambda row:row['mean_nrmse_db']):
        raise ValueError('Hybrid selection must be the full-band winner with learned refinement enabled')
    for candidate in candidates:
        if len(candidate['scores'])!=16 or not math.isclose(float(np.mean(candidate['scores'])),candidate['mean_nrmse_db'],rel_tol=0,abs_tol=1e-8):
            raise ValueError('Incomplete or inconsistent hybrid development candidate')


def seal():
    path=OUT/'selection-lock.json'
    if path.exists():raise ValueError('Selection already sealed; never overwrite after a test has been seen')
    if (OUT/'cache/test').exists():raise ValueError('Final test was already rendered before this seal')
    hybrid=read_json(OUT/'hybrid-development.json')
    dps=read_json(OUT/'dps-selection.json')
    linear=read_json(OUT/'linear-development.json')
    validate_development_selection(linear,dps,hybrid)
    if (dps.get('schema')!='adeps-plus-dps-selection/1' or dps.get('count')!=16
        or dps['selected'].get('steps')!=150 or dps['selected'] not in dps['stage_2']
        or dps['selected']['regularization']!=linear['selected']['regularization']):
        raise ValueError('A complete 150-step DPS development selection on tuned Linear is required')
    for name,digest in dps['source_sha256'].items():
        if sha(inside(ROOT,name))!=digest:raise ValueError('DPS selection source changed')
    for candidate in dps['stage_1']+dps['stage_2']:
        if sha(inside(ROOT,candidate['summary_path']))!=candidate['summary_sha256']:
            raise ValueError('DPS development evidence changed')
    chosen=hybrid['selected']
    if len(chosen['scores'])!=16 or abs(float(np.mean(chosen['scores']))-chosen['mean_nrmse_db'])>1e-8:
        raise ValueError('Selected hybrid must retain all 16 development scores')
    model_card=read_json(ROOT/'work/paper-prior-v1/report.json')
    if model_card['model'].get('weights_sha256')!=MODEL_SHA or sha(ROOT/'work/paper-prior-v1/paper-prior-v1.pt')!=MODEL_SHA:
        raise ValueError('This experiment must use the preregistered frozen model')
    selection={'schema':'adeps-plus-selection/1',
               **{key:chosen[key] for key in ['configuration','post_iterations','post_ridge_relative']},
               'model_weights_sha256':sha(ROOT/'work/paper-prior-v1/paper-prior-v1.pt'),
               'selection_split':'validation','selection_scenes':16,
               'selection_metric':'Mean full-band complex FOA NRMSE dB; best of the predeclared candidates with learned refinement enabled.',
               'no_denoiser_control_is_reported_even_if_better':True,
               'independent_algorithm_not_official_ADEPS':True,
               'provenance':{'source_sha256':{name:sha(ROOT/name) for name in SOURCES if name.startswith('backend/')}}}
    save(OUT/'selection.json',selection)
    inputs=['work/plus-v1/sealed-data/subset-plan.json','work/plus-v1/sealed-data/audio-manifest.json',
            'work/plus-v1/sealed-data/scene-manifest.json','work/plus-v1/selection.json',
            'work/plus-v1/hybrid-development.json','work/plus-v1/dps-selection.json',
            'work/plus-v1/linear-development.json','work/paper-prior-v1/report.json',
            'work/paper-prior-v1/paper-prior-v1.pt','work/paper-data/audio-manifest.json','work/paper-data/scene-manifest.json']
    inputs+=source_input_paths()
    for split,count in [('train',64),('validation',16)]:
        inputs += [str((OUT/'cache'/split/f'{index:04d}.npz').relative_to(ROOT)) for index in range(count)]
    # Preserve every recorded development candidate, including losing/ablation
    # candidates. Test caches and final outcomes are deliberately absent here.
    inputs += [str(p.relative_to(ROOT)) for p in sorted((OUT/'development').rglob('*.json'))]
    inputs += [str(p.relative_to(ROOT)) for p in sorted(OUT.glob('*-development.json'))]
    inputs += [str(p.relative_to(ROOT)) for p in sorted(OUT.glob('training-covariance.*'))]
    inputs=sorted(set(inputs))
    source_hashes={name:sha(ROOT/name) for name in SOURCES}
    input_hashes={name:sha(ROOT/name) for name in inputs}
    lock={'schema':'adeps-plus-selection-lock/1','created_utc':datetime.now(timezone.utc).isoformat(),
          'status':'sealed_before_final_test_rendering_or_inference',
          'source_sha256':source_hashes,'source_set_sha256':canonical_sha(source_hashes),
          'input_sha256':input_hashes,'input_set_sha256':canonical_sha(input_hashes),
          'git':git_snapshot(),
          'selection':selection,'dps':dps['selected'],
          'linear_regularization':linear['selected']['regularization'],
          'method_ids':[row[0] for row in METHODS],
          'primary_comparisons':['linear_tuned','adeps_current'],
          'primary_threshold_db':.5,'confidence_level':.975,'clusters':4,'scenes':32,
          'selected_inputs_are_not_part_of_model_inference':True}
    if any(sha(ROOT/name)!=digest for name,digest in source_hashes.items()):
        raise ValueError('A benchmark source changed while preparing the seal')
    save(path,lock)
    print(json.dumps({'stage':'sealed','sha256':sha(path),'selection':selection,'dps':lock['dps']}),flush=True)


@lru_cache(maxsize=1)
def expected_array():
    q=6; z=1-2*(np.arange(q)+.5)/q; angle=np.arange(q)*np.pi*(3-np.sqrt(5))
    positions=.06*np.c_[np.sqrt(1-z*z)*np.cos(angle),np.sqrt(1-z*z)*np.sin(angle),z]
    f=np.fft.rfftfreq(512,1/16000)
    v=modal_matrix(f,positions,5);v[[0,-1]]=v[[0,-1]].real
    return f,positions,v


def validate_final_scene(data,metadata,index,manifest,audio,manifest_sha):
    """Bind a rendered cache to its sealed specification and known observation.

    This verifies metadata and the p=V*reference+fixed-noise construction; it
    does not independently rerender the HARP/speech convolution a second time.
    """
    if type(index) is not int or not 0<=index<32:raise ValueError('Final scene index outside 0..31')
    specs=manifest['scenes']
    if len(specs)!=32 or len({s['id'] for s in specs})!=32:raise ValueError('Expected 32 unique sealed scene specifications')
    spec=specs[index]
    if any(metadata.get(key)!=value for key,value in spec.items()):raise ValueError('Cache scene specification disagrees with sealed manifest')
    expected={'manifest_sha256':manifest_sha,'split':'test','scene_index':index,'observation_seed':850000+index,
              'snr_db':50.,'microphones':6,'radius_m':.06,'sample_rate':16000,'n_fft':512,'hop':128,'frames':32,
              'target_sh_order':5,'target_normalization':'N3D','target_ordering':'ACN W,Y,Z,X',
              'compression_applied':False,'normalization_applied':False,'reference_is_array_independent':True}
    if any(metadata.get(key)!=value for key,value in expected.items()):raise ValueError('Cache acquisition/STFT provenance mismatch')
    source_hashes=[audio['files'][i]['sha256'] for i in spec['audio_indexes']]
    if metadata.get('source_audio_sha256')!=source_hashes:raise ValueError('Cache speech files disagree with sealed manifest')
    if any(audio['files'][i]['speaker'] not in spec['speaker_pair'] or audio['files'][i]['split']!='test' for i in spec['audio_indexes']):
        raise ValueError('Source speaker/cluster leakage in final specification')
    if set(data)!={'p','V','reference','frequencies','positions'}:raise ValueError('Unexpected cache fields')
    for key,shape in [('p',(257,6,32)),('V',(257,6,36)),('reference',(257,36,32)),('frequencies',(257,)),('positions',(6,3))]:
        if data[key].shape!=shape or data[key].dtype.kind not in 'fci' or not np.all(np.isfinite(data[key])):
            raise ValueError('Invalid cached numeric array: '+key)
    if not np.any(data['reference'][:,:4]):raise ValueError('Sealed FOA target is silent before inference')
    f,positions,v=expected_array()
    for key,expected_value in [('frequencies',f),('positions',positions),('V',v)]:
        if not np.allclose(data[key],expected_value,rtol=1e-12,atol=1e-14):raise ValueError('Cached array model changed: '+key)
    if any(np.any(data[key][[0,-1]].imag!=0) for key in ('p','V','reference')):raise ValueError('Cache real endpoints changed')
    pressure=v@data['reference']
    rng=np.random.default_rng(850000+index)
    noise=rng.normal(size=pressure.shape)+1j*rng.normal(size=pressure.shape);noise[[0,-1]]=noise[[0,-1]].real
    amplitude=float(np.linalg.norm(pressure)/np.linalg.norm(noise)*10**(-50/20))
    if not math.isfinite(amplitude) or amplitude<=0:raise ValueError('Silent or invalid sealed observation')
    actual_variance=metadata.get('noise_complex_variance')
    if not isinstance(actual_variance,(int,float)) or not math.isclose(actual_variance,2*amplitude**2,rel_tol=1e-12):
        raise ValueError('Cached observation variance changed')
    if not np.allclose(data['p'],pressure+amplitude*noise,rtol=1e-12,atol=float(np.max(abs(pressure)))*1e-12):
        raise ValueError('Cache pressure does not match sealed deterministic observation')


def load_final_scene(path,index,manifest,audio,manifest_sha):
    with np.load(path,allow_pickle=False) as archive:
        value=archive['metadata_json']
        if value.shape!=() or value.dtype.kind not in 'US':raise ValueError('Expected scalar metadata JSON')
        metadata=parse_json(value.item())
        data={key:archive[key].copy() for key in archive.files if key!='metadata_json'}
    validate_final_scene(data,metadata,index,manifest,audio,manifest_sha)
    return data,metadata


def pin_test_inputs(lock,*,create=False):
    manifest_path=OUT/'sealed-data/scene-manifest.json';manifest=read_json(manifest_path)
    audio=read_json(OUT/'sealed-data/audio-manifest.json');manifest_sha=sha(manifest_path)
    if manifest['audio_manifest_sha256']!=sha(OUT/'sealed-data/audio-manifest.json'):
        raise ValueError('Sealed audio and scene manifests disagree')
    paths=sorted((OUT/'cache/test').glob('*.npz'))
    if [p.name for p in paths]!=[f'{i:04d}.npz' for i in range(32)]:raise ValueError('All 32 exact test caches must exist before inference')
    items=[]
    for index,path in enumerate(paths):
        _,metadata=load_final_scene(path,index,manifest,audio,manifest_sha)
        items.append({'index':index,'scene_id':metadata['id'],'cluster_id':metadata['cluster_id'],
                      'path':str(path.relative_to(ROOT)),'sha256':sha(path)})
    pin={'schema':'adeps-plus-test-inputs/1','selection_lock_sha256':sha(OUT/'selection-lock.json'),
         'scene_manifest_sha256':manifest_sha,'cases':items,
         'validation':'Sealed scene/audio identifiers, STFT/array conditions and deterministic p=V*reference+noise checked. Reference convolution is not independently rerendered.'}
    path=OUT/'final/input-lock.json'
    if path.exists():
        if read_json(path)!=pin:raise ValueError('Final caches changed after first input registration')
    elif create:
        if any((OUT/'final').glob('[0-9][0-9][0-9][0-9]/*.json')):raise ValueError('Existing test results have no registered input lock')
        save(path,pin)
    else:raise ValueError('No registered final input lock; results cannot be reported')
    return pin,manifest,audio


def failed_values(reference,frequencies,reason):
    values=evaluate_metrics(np.full(reference.shape,np.nan+0j),reference,frequencies)
    values['metrics']['reason']=reason;values['details']['failure']=reason
    return values


def save_estimate(path,estimate):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.npz.tmp')
    with temporary.open('wb') as handle:np.savez_compressed(handle,estimate=estimate)
    temporary.replace(path)


def validate_case(path,identifier,index,metadata,data,input_sha,lock_sha):
    case=read_json(path);target=path.with_suffix('.npz')
    expected={'schema':'adeps-plus-case/1','method':identifier,'scene':index,'scene_id':metadata['id'],
              'cluster_id':metadata['cluster_id'],'input_sha256':input_sha,'selection_lock_sha256':lock_sha}
    if any(case.get(key)!=value for key,value in expected.items()):raise ValueError('Case identity/input mismatch: '+str(path))
    if case.get('outcome') not in ('completed','failed') or type(case.get('seconds')) not in (float,int) or not math.isfinite(case['seconds']) or case['seconds']<0:
        raise ValueError('Invalid case outcome/runtime')
    for key in ('nfe','vjp'):
        count=case.get(key)
        if count is not None and (type(count) is not int or count<0):raise ValueError('Invalid observed compute counter')
        if case['outcome']=='completed' and count is None:raise ValueError('Completed case is missing its compute counter')
    digest=case.get('estimate_sha256')
    if digest is None:
        if target.exists() or case['outcome']!='failed':raise ValueError('Missing or unexpected estimate artifact')
        if case['metrics'].get('status')!='failure' or any(case['metrics'].get(key) is not None for key in METRIC_KEYS):
            raise ValueError('A failed case must retain undefined metrics')
        if any(case['curves'].get(key)!=[None]*257 for key in CURVE_KEYS):raise ValueError('A failed case must retain undefined curves')
    else:
        if not target.is_file() or sha(target)!=digest:raise ValueError('Saved estimate checksum mismatch')
        with np.load(target,allow_pickle=False) as archive:
            if archive.files!=['estimate']:raise ValueError('Unexpected estimate fields')
            estimate=archive['estimate']
        if estimate.shape!=data['reference'].shape or not np.all(np.isfinite(estimate)):raise ValueError('Saved estimate is malformed')
        calculated=evaluate_metrics(estimate,data['reference'],data['frequencies'])
        if case['metrics']!=calculated['metrics'] or case['curves']!=calculated['curves']:
            raise ValueError('Saved metrics disagree with the estimate/current reference')
        if case['details']!=calculated['details']:raise ValueError('Saved metric domain/status details changed')
        if (case['outcome']=='failed')!=(calculated['metrics']['status']=='failure'):
            raise ValueError('Case outcome disagrees with numeric result')
    return case


def record_environment(path,environment):
    """Never replace the runtime identity of already evaluated cases."""
    if path.exists():
        if read_json(path)!=environment:raise ValueError('Cannot resume with a different runtime environment')
    else:
        if any(path.parent.glob('[0-9][0-9][0-9][0-9]/*.json')):raise ValueError('Existing cases have no runtime record')
        save(path,environment)


def record_case(target,identifier,index,metadata,data,input_sha,lock_sha,prior,lock,*,memory_reader=None):
    """Preserve an attempted method even if it fails; never retry it silently."""
    record_path=target.with_suffix('.json')
    if record_path.exists():
        return validate_case(record_path,identifier,index,metadata,data,input_sha,lock_sha)
    if target.exists():raise ValueError('Orphan estimate without result record; investigate before resuming: '+str(target))
    estimate=None;diagnostics={};nfe=None;vjp=None;elapsed=None
    # Synchronize the shared GPU around wall-clock timing; metric/export work
    # remains outside the measured reconstruction interval.
    synchronize = None
    if getattr(prior, 'device', None) == 'mps':
        import torch
        synchronize = torch.mps.synchronize
        synchronize()
    started=time.perf_counter()
    try:
        observation={key:data[key] for key in ('p','V','frequencies')}
        estimate,diagnostics=run_method(identifier,observation,prior,lock)
        if synchronize is not None: synchronize()
        elapsed=time.perf_counter()-started
        estimate=np.asarray(estimate)
        if estimate.shape!=data['reference'].shape or not np.all(np.isfinite(estimate)):
            raise ValueError('Method returned a malformed or nonfinite estimate')
        nfe=diagnostics.get('nfe');vjp=diagnostics.get('vjp',0)
        if any(type(value) is not int or value<0 for value in (nfe,vjp)):
            raise ValueError('Method did not report valid model/VJP counts')
        values=evaluate_metrics(estimate,data['reference'],data['frequencies'])
        # Check diagnostics before creating an estimate artifact: NaN in a
        # secondary trace must not abort the run without retaining the failure.
        json.dumps(diagnostics,allow_nan=False)
    except (ArithmeticError,ValueError,RuntimeError,MemoryError,TypeError) as exc:
        elapsed=time.perf_counter()-started if elapsed is None else elapsed
        failure=f'{type(exc).__name__}: {exc}'
        estimate=None;diagnostics={'failure':failure};nfe=None;vjp=None
        values=failed_values(data['reference'],data['frequencies'],failure)
    # File-system errors deliberately stop the run; a missing artifact is
    # different from an estimator failure and must never be called evaluated.
    if estimate is not None:save_estimate(target,estimate)
    memory=memory_reader() if memory_reader else {}
    record={'schema':'adeps-plus-case/1','method':identifier,'scene':index,'scene_id':metadata['id'],
            'cluster_id':metadata['cluster_id'],'outcome':'failed' if values['metrics']['status']=='failure' else 'completed',
            'seconds':elapsed,'nfe':nfe,'vjp':vjp,'input_sha256':input_sha,
            'estimate_sha256':sha(target) if estimate is not None else None,'selection_lock_sha256':lock_sha,
            **values,'diagnostics':diagnostics,'memory':memory}
    save(record_path,record)
    print(json.dumps({'stage':'final-test','scene':index,'method':identifier,'outcome':record['outcome'],
                      'seconds':elapsed,'nrmse_db':values['metrics']['nrmse_db']},allow_nan=False),flush=True)
    return record


def run_method(identifier,data,prior,lock):
    from paper_inference import sample
    from plus_spatial import reconstruct_spatial
    from plus_consistency import reconstruct as consistency
    from plus_system import reconstruct as plus
    p,v,f=data['p'],data['V'],data['frequencies']
    if identifier in ('linear_default','linear_tuned'):
        a,_,_=encode(v,p,.001 if identifier=='linear_default' else lock['linear_regularization'])
        return a,{'nfe':0,'vjp':0}
    if identifier in ('linear_noise','spatial_only'):
        result=reconstruct_spatial(p,v,f,max_sources=0 if identifier=='linear_noise' else 2,
                                   diffuse_weight=.25,regularization=1e-6,noise_snr_db=50.)
        return result['estimate'],{'nfe':0,'vjp':0,'diagnostics':result['diagnostics']}
    if identifier=='consistency_only':
        linear,_,_=encode(v,p,lock['linear_regularization'])
        result=consistency(p,v,f,initial=linear,iterations=200,ridge_relative=.001)
        return result['estimate'],{key:value for key,value in result.items() if key!='estimate'}
    if identifier in ('adeps_current','adeps_tuned'):
        reg=.001 if identifier=='adeps_current' else lock['dps']['regularization']
        eta=50. if identifier=='adeps_current' else lock['dps']['eta_prime']
        linear,encoder,_=encode(v,p,reg)
        scale=float(np.sqrt(np.mean(abs(linear)**2)))
        a,trace=sample(compress(linear/scale),encoder@v,prior,steps=150,eta_prime=eta,seed=42)
        return a*scale,{'nfe':150,'vjp':150,'trace':trace,'regularization':reg,'eta_prime':eta,'seed':42,'scale':scale}
    if identifier in ('plus','plus_no_denoiser'):
        result=plus(p,v,f,prior,lock['selection'],denoiser=identifier=='plus')
        return result['estimate'],{key:value for key,value in result.items() if key not in ('estimate','linear','spatial')}
    raise ValueError('Unknown method')


def evaluate():
    import torch
    import scipy
    from paper_inference import PaperPrior
    lock=verify_lock()
    pin,manifest,audio=pin_test_inputs(lock,create=True)
    lock_sha=sha(OUT/'selection-lock.json')
    torch.set_num_threads(2)
    prior=PaperPrior(ROOT/'work/paper-prior-v1')
    run_dir=OUT/'final'
    record_environment(run_dir/'environment.json',{'python':platform.python_version(),'numpy':np.__version__,
         'scipy':scipy.__version__,'torch':torch.__version__,'device':prior.device,'platform':platform.platform(),
         'selection_lock_sha256':lock_sha})
    def read_memory():
        if prior.device!='mps':return {'scope':'No memory measurement on this device'}
        return {'allocated_after_case_bytes':int(torch.mps.current_allocated_memory()),
                'driver_after_case_bytes':int(torch.mps.driver_allocated_memory()),
                'scope':'End-of-case counters after metric calculation/export, not peak-memory measurements'}
    for index in range(32):
        path=OUT/'cache/test'/f'{index:04d}.npz'
        data,metadata=load_final_scene(path,index,manifest,audio,pin['scene_manifest_sha256'])
        input_sha=sha(path)
        if input_sha!=pin['cases'][index]['sha256']:raise ValueError('Input changed after registration')
        for value in data.values():value.setflags(write=False)
        for identifier,_,_,_,_ in METHODS:
            target=run_dir/f'{index:04d}'/f'{identifier}.npz'
            record_case(target,identifier,index,metadata,data,input_sha,lock_sha,prior,lock,memory_reader=read_memory)
            gc.collect()
            if prior.device=='mps':torch.mps.synchronize();torch.mps.empty_cache()


def report():
    lock=verify_lock()
    pin,manifest,audio=pin_test_inputs(lock)
    lock_sha=sha(OUT/'selection-lock.json')
    environment=read_json(OUT/'final/environment.json')
    if environment.get('selection_lock_sha256')!=lock_sha:raise ValueError('Runtime identity disagrees with selection lock')
    scenes=[]; cases={row[0]:[] for row in METHODS};case_hashes={}
    for index in range(32):
        data,metadata=load_final_scene(OUT/'cache/test'/f'{index:04d}.npz',index,manifest,audio,pin['scene_manifest_sha256'])
        row={'id':metadata['id'],'cluster_id':metadata['cluster_id'],'metrics':{},'curves':{},
             'outcomes':{},'runtime':{},'metric_details':{},
             'speaker_pair':metadata['speaker_pair'],'source_count':len(metadata['sources_m']),
             'dc_reference_energy_fraction':float(np.sum(abs(data['reference'][0,:4])**2)/np.sum(abs(data['reference'][:,:4])**2)),
             'reference_energy_by_frequency_fraction':(np.sum(abs(data['reference'][:,:4])**2,axis=(1,2))/np.sum(abs(data['reference'][:,:4])**2)).tolist()}
        for identifier,_,_,_,_ in METHODS:
            path=OUT/'final'/f'{index:04d}'/f'{identifier}.json'
            case=validate_case(path,identifier,index,metadata,data,pin['cases'][index]['sha256'],lock_sha)
            row['metrics'][identifier]=case['metrics'];row['curves'][identifier]=case['curves']
            row['outcomes'][identifier]=case['outcome']
            row['runtime'][identifier]={key:case[key] for key in ('seconds','nfe','vjp','memory')}
            row['metric_details'][identifier]={key:case['details'][key] for key in ('si_sdr','coherence','nrmse_frequency_status','failure') if key in case['details']}
            cases[identifier].append(case);case_hashes[str(path.relative_to(ROOT))]=sha(path)
        scenes.append(row)
    aggregate_result=aggregate(scenes,[row[0] for row in METHODS])
    methods=[{'id':identifier,'label_jp':jp,'label_en':en,'kind':kind,
              'mean_nrmse_db':aggregate_result['means'][identifier]['nrmse_db'],
              'mean_seconds':float(np.mean([case['seconds'] for case in cases[identifier]])),
              'nfe':float(np.mean([case['nfe'] for case in cases[identifier]])) if all(case['nfe'] is not None for case in cases[identifier]) else None,
              'planned_nfe':nfe,'completed':sum(case['outcome']=='completed' for case in cases[identifier]),
              'failed':sum(case['outcome']=='failed' for case in cases[identifier]),
              'metrics':aggregate_result['means'][identifier],'valid_counts':aggregate_result['valid_counts'][identifier]}
             for identifier,jp,en,kind,nfe in METHODS]
    comparisons=[paired_comparison(scenes,identifier,'plus') for identifier,_,_,_,_ in METHODS if identifier!='plus']
    primary=[row for row in comparisons if row['baseline'] in lock['primary_comparisons']]
    result={'schema':'adeps-plus-benchmark/1','status':'evaluated',
            'title_jp':'同じ観測から、どこまで正確に復元できたか。',
            'title_en':'How accurately can we reconstruct the same observation?',
            'conditions':{'scenes':32,'clusters':4,'microphones':6,'radius_m':.06,'snr_db':50,'sample_rate_hz':16000,
                          'geometry':'sphere','source_counts':[1,2],'matched_order':5,'evaluated_audio_samples':3968,
                          'evaluated_audio_seconds':.248},
            'methods':methods,'comparisons':comparisons,'primary_passed':all(row['passed'] for row in primary),
            'scenes':scenes,'frequencies_hz':np.fft.rfftfreq(512,1/16000).tolist(),
            'curves':aggregate_result['curves'],'selection':lock['selection'],
            'provenance':{'lock_sha256':lock_sha,'source_sha256':lock['source_sha256'],
                          'git_at_selection_seal':lock['git'],'source_set_sha256':lock['source_set_sha256'],
                          'input_set_sha256':lock['input_set_sha256'],'test_input_lock_sha256':sha(OUT/'final/input-lock.json'),
                          'test_inputs':pin,'case_sha256':case_hashes,
                          'input_sha256':lock['input_sha256'],'evaluation_domain':DOMAIN,
                          'training':'Frozen independent 30,781,344-parameter prior; 2,000 optimizer updates on ideal HARP-adapted N5 HOA / VCTK targets. No new neural training in this solver comparison.',
                          'development':'16 legacy validation scenes; all method selection before final test.',
                          'test':'32 rooms / 8 fresh VCTK speakers / 4 speaker-pair clusters; VCTK rather than WSJ0.',
                          'reference_use':'Synthetic observation generation and scoring only; no reconstruction interface accepts a reference.',
                          'undefined_results':'All nine methods and all 32 scenes are retained. Null/failure outcomes are never dropped or changed into zero; any undefined member makes its corresponding full-set mean undefined.',
                          'runtime':'Per-method wall-clock time includes reconstruction and excludes metric calculation/export. Failed attempts remain in the timing denominator. nfe is observed mean over all cases, or null if unavailable; planned_nfe is only the configured call budget.',
                          'memory':'Recorded accelerator counters are after each case, not observed peak memory.',
                          'environment':environment},
            'sources':[{'title':'ADEPS — Milstein, Shlezinger & Rafaely (2026)','url':'https://arxiv.org/html/2608.24558v3'},
                       {'title':'DiffPIR — diffusion priors for inverse problems','url':'https://arxiv.org/html/2305.08995'},
                       {'title':'DDNM — range and null-space decomposition','url':'https://arxiv.org/html/2212.00490'},
                       {'title':'Residual Learning for Neural Ambisonics Encoders (2026)','url':'https://arxiv.org/html/2601.18322v1'},
                       {'title':'Parametric Ambisonic Encoding of Arbitrary Microphone Arrays (2022)','url':'https://doi.org/10.1109/TASLP.2022.3182857'},
                       {'title':'Explicit consistency constraints for STFT spectrograms (2008)','url':'https://www.jonathanleroux.org/pdf/LeRoux2008SAPA09b.pdf'},
                       {'title':'VCTK 0.92 — Yamagishi, Veaux & MacDonald','url':'https://doi.org/10.7488/ds/2645'}],
            'limitations_jp':['比較したADEPSは当方の独自実装です。著者の公式重み・WSJ0評価との同条件比較ではなく、原論文を上回ったとは確認できていません。',
                '8話者・4組の小標本です。97.5%区間にも不確実性があり、別のコーパス・録音・配列への一般化は未検証です。',
                '最終評価は1または2音源の音声、次数5の一致モデル、半径6 cmの単一6本球面アレイ、既知50 dB SNRのみです。方向推定は最大2方向を仮定しており、この設定への適合がα処理を助ける可能性があります。音楽・任意の音場・他のアレイ・実室の優位性は示していません。',
                '雑音はSTFT成分ごとに独立に加えています。実録音の雑音とは相関が異なり、波形整合処理の利得がこの合成条件に依存する可能性があります。',
                '波形評価は共通の端部除去後3,968サンプル（0.248秒）です。数値上の改善が、そのまま可聴差や長時間の再生品質を保証するものではありません。',
                '改善版は方向共分散・固定学習済み除去器・STFT整合・観測補正の独自な組合せです。厳密なADEPS拡散事後サンプリングではありません。',
                '学習済み補正OFFの結果も掲載しています。ONがOFFを下回る場合、改善を拡散モデル単独の効果とは主張しません。'],
            'limitations_en':['ADEPS here is our independent implementation. Author weights and the WSJ0 benchmark are unavailable for an equivalent comparison; superiority over the paper is unverified.',
                'Only eight speakers in four clusters. The 97.5% intervals are uncertain; other corpora, recordings and arrays remain untested.',
                'Final evaluation covers only one or two speech sources, matched order-5 observations, one six-microphone spherical array of radius 6 cm and known 50 dB SNR. Direction estimation assumes at most two dominant directions; this fit to the test domain may assist α. No advantage on music, arbitrary sound fields, other arrays or physical rooms is established.',
                'Noise is independent across STFT components, unlike overlapping-window STFTs of recorded waveform noise. Consistency gains may depend on this simulation choice.',
                'Waveform scoring uses 3,968 samples (0.248 seconds) after the common edge trim. Numerical gains do not guarantee an audible difference or long-form reproduction quality.',
                'The improvement is an independent combination of directional covariance, a frozen denoiser, STFT consistency and physical correction; it is not exact ADEPS posterior sampling.',
                'Learned-refinement OFF is reported too. If ON performs worse, the overall improvement is not attributed to diffusion alone.'],
            'example_url':'models/plus-example.json'}
    save(OUT/'benchmark.json',result)
    print(json.dumps({'primary_passed':result['primary_passed'],'methods':methods,'comparisons':comparisons}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['seal','evaluate','report','verify'])
    args=parser.parse_args()
    if args.command=='seal':seal()
    elif args.command=='evaluate':evaluate()
    elif args.command=='report':report()
    else:verify_lock();print('sealed identities verified')
