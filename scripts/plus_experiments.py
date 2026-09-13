"""Development experiments; selection uses validation only, never sealed truth."""
import argparse
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from capture import encode
from neural import compress
from diffusion_studio import frequency_metrics

OUT = ROOT/'work/plus-v1'


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    temp.replace(path)


def load_scene(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files if key != 'metadata_json'}, json.loads(str(data['metadata_json']))


def nmse(estimate, reference):
    return float(10*np.log10(max(np.sum(abs(estimate-reference)**2)/np.sum(abs(reference)**2), 1e-30)))


def metrics(estimate, reference, frequencies):
    estimate, reference = estimate[:,:4].copy(), reference[:,:4]
    estimate[[0,-1]] = estimate[[0,-1]].real
    if not np.all(np.isfinite(estimate)):
        raise ValueError('Nonfinite candidate; cannot silently drop this scene')
    result = {'nrmse_db': nmse(estimate, reference)}
    for name, low in [('non_dc', 1.), ('speech_band', 100.)]:
        mask = frequencies >= low
        result[name+'_nrmse_db'] = nmse(estimate[mask], reference[mask])
    return result


def linear_sweep(split='validation', count=16):
    if split != 'validation':
        raise ValueError('Hyperparameters may only be selected on validation')
    rows = []
    for index in range(count):
        path = OUT/'cache'/split/f'{index:04d}.npz'
        data, metadata = load_scene(path)
        for exponent in range(-8, 2):
            value = 10.**exponent
            estimate, _, _ = encode(data['V'], data['p'], value)
            rows.append({'scene': index, 'regularization': value,
                         **metrics(estimate, data['reference'], data['frequencies'])})
    summary = [{'regularization': 10.**exp,
                'mean_nrmse_db': float(np.mean([row['nrmse_db'] for row in rows if row['regularization']==10.**exp]))}
               for exp in range(-8, 2)]
    selected = min(summary, key=lambda x:x['mean_nrmse_db'])
    result = {'schema':'adeps-plus-linear-development/1', 'split':split, 'count':count,
              'selection_metric':'mean full-band complex FOA NRMSE dB, all scenes retained',
              'rows':rows, 'summary':summary, 'selected':selected}
    save(OUT/'linear-development.json',result)
    print(json.dumps({'stage':'linear-sweep','summary':summary,'selected':selected}),flush=True)


def run_dps(etas, steps, count, scale_mode='legacy', regularization=.001):
    import torch
    from paper_inference import PaperPrior, sample
    torch.set_num_threads(2)
    prior = PaperPrior(ROOT/'work/paper-prior-v1')
    for eta in etas:
        directory = OUT/'development'/f'dps-{scale_mode}-r{regularization:g}-s{steps}-eta{eta:g}'
        rows = []
        for index in range(count):
            path = OUT/'cache/validation'/f'{index:04d}.npz'
            target = directory/f'{index:04d}.npz'
            metric_path = directory/f'{index:04d}.json'
            if target.exists() and metric_path.exists():
                rows.append(json.loads(metric_path.read_text()))
                continue
            data, metadata = load_scene(path)
            linear, encoder, _ = encode(data['V'], data['p'], regularization)
            scale = float(np.sqrt(np.mean(abs(linear if scale_mode=='legacy' else linear[:,:1])**2)))
            started = time.perf_counter()
            output, trace = sample(compress(linear/scale), encoder@data['V'], prior,
                                   steps=steps, eta_prime=eta, seed=42)
            output *= scale
            row = {'scene':index, 'eta_prime':eta, 'steps':steps, 'seed':42, 'scale_mode':scale_mode,
                   'regularization':regularization,
                   'scale':scale, 'seconds':time.perf_counter()-started,
                   'model_sha256':prior.card['model']['weights_sha256'],
                   'input_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   **metrics(output,data['reference'],data['frequencies']), 'trace':trace}
            directory.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(target, estimate=output)
            save(metric_path,row)
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='trace'}),flush=True)
            # Release the graph allocator between independent scenes on the
            # 8 GB shared-memory host; this does not alter model parameters.
            del output, linear, encoder, data
            gc.collect()
            if prior.device == 'mps':
                torch.mps.synchronize()
                torch.mps.empty_cache()
        save(directory/'summary.json', {'rows':[{k:v for k,v in row.items() if k!='trace'} for row in rows],
             'mean_nrmse_db':float(np.mean([row['nrmse_db'] for row in rows]))})


def covariance_search():
    from plus_covariance import covariance_from_targets, wiener
    paths=[OUT/'cache/train'/f'{i:04d}.npz' for i in range(64)]
    if not all(path.exists() for path in paths):
        raise ValueError('All 64 predefined training-calibration targets must exist')
    covariance,count=covariance_from_targets(load_scene(path)[0]['reference'] for path in paths)
    np.savez_compressed(OUT/'training-covariance.npz',covariance=covariance)
    save(OUT/'training-covariance.json',{'schema':'adeps-plus-training-covariance/1',
         'count':count,'split':'train','array_independent':True,'normalization':'Each ideal target divided by its common all-order RMS',
         'source_sha256':hashlib.sha256((ROOT/'backend/plus_covariance.py').read_bytes()).hexdigest(),
         'target_sha256':[hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]})
    rows=[]
    scenes=[load_scene(OUT/'cache/validation'/f'{i:04d}.npz')[0] for i in range(16)]
    for shrinkage in [0.,.25,.5,.75,.9,1.]:
        for regularization in [1e-8,1e-6,1e-4,.001,.01]:
            values=[]
            for scene,data in enumerate(scenes):
                estimate=wiener(data['p'],data['V'],covariance,shrinkage=shrinkage,regularization=regularization)
                values.append({'scene':scene,**metrics(estimate,data['reference'],data['frequencies'])})
            row={'shrinkage':shrinkage,'regularization':regularization,'scenes':values,
                 'mean_nrmse_db':float(np.mean([v['nrmse_db'] for v in values]))}
            rows.append(row)
    result={'schema':'adeps-plus-covariance-search/1','rows':rows,'selected':min(rows,key=lambda x:x['mean_nrmse_db'])}
    save(OUT/'covariance-development.json',result)
    print(json.dumps({k:v for k,v in result['selected'].items() if k!='scenes'}),flush=True)


def run_pnp(count=16):
    import torch
    from paper_inference import PaperPrior
    from plus_diffusion import refine
    torch.set_num_threads(2)
    prior=PaperPrior(ROOT/'work/paper-prior-v1')
    regularization=json.loads((OUT/'linear-development.json').read_text())['selected']['regularization']
    # Fixed first continuation search. All candidates see the same 16 dev
    # scenes, no post-hoc removal and no final-test input is read here.
    summaries=[]
    for sigma in [.1,.3,1.,3.]:
        for relaxation in [.25,1.]:
            config={'steps':8,'sigma_start':sigma,'relaxation':relaxation,
                    'regularization':regularization,'ridge_relative':regularization,
                    'scale_mode':'linear_w','initial_noise_scale':0.}
            directory=OUT/'development'/f'pnp-w-s8-sigma{sigma:g}-relax{relaxation:g}'
            rows=[]
            for index in range(count):
                target=directory/f'{index:04d}.npz';metric_path=directory/f'{index:04d}.json'
                if target.exists() and metric_path.exists():
                    rows.append(json.loads(metric_path.read_text()));continue
                path=OUT/'cache/validation'/f'{index:04d}.npz'
                data,_=load_scene(path)
                started=time.perf_counter()
                result=refine(data['p'],data['V'],data['frequencies'],prior,**config)
                estimate=result['estimate']
                row={'scene':index,'configuration':config,'seconds':time.perf_counter()-started,
                     **metrics(estimate,data['reference'],data['frequencies']),
                     'model_sha256':prior.card['model']['weights_sha256'],
                     'input_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'trace':result['trace']}
                directory.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(target,estimate=estimate)
                save(metric_path,row);rows.append(row)
                print(json.dumps({k:v for k,v in row.items() if k not in ('trace','model_sha256','input_file_sha256')}),flush=True)
                del result,estimate,data
                gc.collect()
                if prior.device=='mps':torch.mps.synchronize();torch.mps.empty_cache()
            summary={'configuration':config,'directory':str(directory.relative_to(OUT)),
                     'mean_nrmse_db':float(np.mean([row['nrmse_db'] for row in rows]))}
            save(directory/'summary.json',summary);summaries.append(summary)
    save(OUT/'pnp-development.json',{'rows':summaries,'selected':min(summaries,key=lambda row:row['mean_nrmse_db'])})


def run_hybrid(count=16):
    import torch
    from paper_inference import PaperPrior
    from plus_hybrid import reconstruct
    from plus_consistency import reconstruct as joint_consistency
    torch.set_num_threads(2)
    prior=PaperPrior(ROOT/'work/paper-prior-v1')
    summaries=[]
    configs=[{'steps':8,'sigma_start':sigma,'relaxation':relaxation,
              'use_stft_consistency':True,'stft_iterations':0,'ridge_relative':1e-7}
             for sigma in [.3,1.,3.,10.] for relaxation in [.25,1.]]
    configs.append({**configs[0],'relaxation':0.})
    for config in configs:
        directory=OUT/'development'/f"hybrid-s8-sigma{config['sigma_start']:g}-relax{config['relaxation']:g}"
        rows=[]
        for index in range(count):
            target=directory/f'{index:04d}.npz'; metric_path=directory/f'{index:04d}.json'
            if target.exists() and metric_path.exists():
                rows.append(json.loads(metric_path.read_text()));continue
            path=OUT/'cache/validation'/f'{index:04d}.npz'
            data,_=load_scene(path)
            started=time.perf_counter()
            result=reconstruct(data['p'],data['V'],data['frequencies'],prior,**config)
            estimate=result['estimate']
            row={'scene':index,'configuration':config,'seconds':time.perf_counter()-started,
                 'nfe':result['nfe'],**metrics(estimate,data['reference'],data['frequencies']),
                 'model_sha256':prior.card['model']['weights_sha256'],
                 'input_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'source_sha256':{file:hashlib.sha256((ROOT/'backend'/file).read_bytes()).hexdigest()
                                  for file in ['plus_hybrid.py','plus_diffusion.py','plus_spatial.py','plus_consistency.py','plus_reconstruction.py']},
                 'trace':result['trace'],'post_variants':[]}
            directory.mkdir(parents=True,exist_ok=True)
            # Post-processing variants reuse precisely the same neural output.
            arrays={'estimate':estimate}
            for iterations in [10,50]:
                post=joint_consistency(data['p'],data['V'],data['frequencies'],initial=estimate,
                                       iterations=iterations,ridge_relative=.001)
                arrays[f'post{iterations}']=post['estimate']
                row['post_variants'].append({'iterations':iterations,'ridge_relative':.001,
                    **metrics(post['estimate'],data['reference'],data['frequencies'])})
            np.savez_compressed(target,**arrays)
            save(metric_path,row);rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ('trace','source_sha256','model_sha256','input_file_sha256')}),flush=True)
            del result,estimate,data,post,arrays
            gc.collect()
            if prior.device=='mps':torch.mps.synchronize();torch.mps.empty_cache()
        for iterations in [0,10,50]:
            scores=[row['nrmse_db'] if iterations==0 else next(v['nrmse_db'] for v in row['post_variants'] if v['iterations']==iterations) for row in rows]
            summaries.append({'configuration':config,'post_iterations':iterations,'post_ridge_relative':.001,
                 'directory':str(directory.relative_to(OUT)), 'mean_nrmse_db':float(np.mean(scores)),
                 'scores':scores,'trained_denoiser_used':config['relaxation']>0})
        save(directory/'summary.json',{'rows':summaries[-3:]})
    save(OUT/'hybrid-development.json',{'rows':summaries,
         'selected':min((row for row in summaries if row['trained_denoiser_used']),key=lambda row:row['mean_nrmse_db']),
         'no_denoiser_control':min((row for row in summaries if not row['trained_denoiser_used']),key=lambda row:row['mean_nrmse_db'])})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['linear','dps','covariance','pnp','hybrid'])
    parser.add_argument('--count',type=int,default=16)
    parser.add_argument('--steps',type=int,default=32)
    parser.add_argument('--etas',type=float,nargs='+',default=[0,1,5,20,50,100])
    parser.add_argument('--scale',choices=['legacy','w'],default='legacy')
    parser.add_argument('--regularization',type=float,default=.001)
    args = parser.parse_args()
    if args.command=='linear': linear_sweep(count=args.count)
    elif args.command=='covariance': covariance_search()
    elif args.command=='pnp': run_pnp(args.count)
    elif args.command=='hybrid': run_hybrid(args.count)
    else: run_dps(args.etas,args.steps,args.count,args.scale,args.regularization)
