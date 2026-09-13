"""Complete the preregistered two-stage DPS baseline selection on development."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from plus_experiments import OUT, ROOT, run_dps, save

ETAS = [0., 1., 5., 20., 50., 100.]
REGULARIZATION = 1e-7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_stage(etas, steps):
    rows = []
    for eta in etas:
        path = OUT/'development'/f'dps-legacy-r{REGULARIZATION:g}-s{steps}-eta{eta:g}'/'summary.json'
        summary = json.loads(path.read_text())
        records = summary['rows']
        if sorted(record['scene'] for record in records) != list(range(16)):
            raise ValueError('Every candidate must include precisely all 16 development scenes')
        for record in records:
            source = OUT/'cache/validation'/f"{record['scene']:04d}.npz"
            if record['input_file_sha256'] != sha(source):
                raise ValueError(f'Changed development input: {source}')
            if (record['eta_prime'],record['steps'],record['seed'],record['scale_mode'],record['regularization']) != (eta,steps,42,'legacy',REGULARIZATION):
                raise ValueError(f'Unexpected baseline configuration: {path}')
            if record['model_sha256'] != '0e88c717770453520331d797392794934c6eb167716007b44bb58633e811d7b2':
                raise ValueError('Baseline weights changed')
        rows.append({'eta_prime':eta,'steps':steps,'regularization':REGULARIZATION,
                     'mean_nrmse_db':summary['mean_nrmse_db'],
                     'summary_path':str(path.relative_to(ROOT)), 'summary_sha256':sha(path)})
    return rows


def main(wait_pid=None):
    if (OUT/'selection-lock.json').exists():
        raise ValueError('Do not select hyperparameters after final-test sealing')
    if wait_pid is not None:
        print(json.dumps({'status':'waiting_for_stage_1','pid':wait_pid}),flush=True)
        while True:
            try: os.kill(wait_pid,0)
            except ProcessLookupError: break
            time.sleep(5)
    first=read_stage(ETAS,32)
    promoted=sorted(set([row['eta_prime'] for row in sorted(first,key=lambda row:(row['mean_nrmse_db'],ETAS.index(row['eta_prime'])))[:2]]+[50.]),key=ETAS.index)
    print(json.dumps({'status':'stage_2','promoted':promoted,'steps':150,'scene_count':16}),flush=True)
    run_dps(promoted,150,16,'legacy',REGULARIZATION)
    second=read_stage(promoted,150)
    selected=min(second,key=lambda row:(row['mean_nrmse_db'],ETAS.index(row['eta_prime'])))
    result={'schema':'adeps-plus-dps-selection/1','split':'development','count':16,
            'rule':'Six eta values at 32 steps; top two plus eta=50 at 150 steps; lowest full-band mean dB; ties use ascending predefined eta order.',
            'stage_1':first,'stage_2':second,'selected':selected,
            'source_sha256':{name:sha(ROOT/name) for name in ['scripts/select_plus_dps.py','scripts/plus_experiments.py','backend/paper_inference.py']}}
    save(OUT/'dps-selection.json',result)
    print(json.dumps({'status':'selection_complete','selected':selected}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-pid',type=int)
    args=parser.parse_args()
    main(args.wait_pid)
