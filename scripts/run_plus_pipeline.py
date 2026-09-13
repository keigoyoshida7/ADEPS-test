"""Run the authorized local experiment sequentially after development selection.

No tuning, cloud resources, publication or replacement of sealed records occurs.
A failed stage stops immediately so the cause can be reviewed before resuming.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/plus-v1'


def run(stage, arguments):
    record={'stage':stage,'status':'running','started_at':datetime.now(timezone.utc).isoformat()}
    target=WORK/'pipeline-stage.json'
    target.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    with (WORK/f'pipeline-{stage}.log').open('w') as output:
        result=subprocess.run([sys.executable,*arguments],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
    record.update(status='complete' if result.returncode==0 else 'failed',returncode=result.returncode,
                  finished_at=datetime.now(timezone.utc).isoformat())
    target.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
    if result.returncode:raise RuntimeError(f'{stage} failed. Inspect work/plus-v1/pipeline-{stage}.log before continuing.')


def main(pid):
    if pid:
        while True:
            try:os.kill(pid,0)
            except ProcessLookupError:break
            time.sleep(5)
    if not (WORK/'dps-selection.json').is_file():raise ValueError('Completed development selection is required')
    run('seal',['scripts/benchmark_plus.py','seal'])
    run('cli-smoke',['scripts/infer_plus.py','--input','work/paper-prior-v1/example/array-input.npz',
                    '--selection','work/plus-v1/selection.json','--checkpoint','work/paper-prior-v1',
                    '--output','work/plus-v1/native-cli-smoke','--device','mps'])
    run('render',['scripts/plus_data.py','render','--split','test','--count','32'])
    run('evaluate',['scripts/benchmark_plus.py','evaluate'])
    run('report',['scripts/benchmark_plus.py','report'])
    run('export',['scripts/export_plus.py'])
    print('Full experiment and export completed; inspect all results and UI before publication.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--wait-pid',type=int)
    main(parser.parse_args().wait_pid)
