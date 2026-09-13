"""Reflect completed local evaluation artifacts; never fabricate scores."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work/plus-v1'
PUBLIC=ROOT/'public/models/plus-progress.json'


def snapshot():
    stamp=datetime.now(timezone.utc).isoformat()
    if (WORK/'web-artifacts-verified.json').exists():
        phase='complete'; completed=total=288
        label=('評価と表示の確認を完了','Evaluation and display verification complete')
        detail=('全32場面・9方式の記録を表示しています。','Showing all 32 scenes and nine methods.')
    elif (WORK/'benchmark.json').exists():
        phase='exporting'; completed=total=288
        label=('評価記録と試聴例を確認中','Checking the report and listening examples')
        detail=('全方式の計算が完了しました。数値・3D・音声と公開内容を照合しています。','Computation is complete; verifying numbers, 3D views, audio and publication.')
    elif (WORK/'selection-lock.json').exists():
        phase='sealed_test';total=288
        completed=len(list((WORK/'final').glob('*/*.json')))
        label=('設定を固定して最終テストを計算中','Running the final test with frozen settings')
        detail=('新しい8話者・32場面を9方式で比較。全結果が揃ってから判定します。','Comparing nine methods on 32 scenes from eight new speakers. Assessment waits for all results.')
    else:
        phase='development'
        promoted=[]
        log=WORK/'dps-selection.log'
        if log.exists():
            for line in log.read_text().splitlines():
                try: row=json.loads(line)
                except (ValueError,TypeError): continue
                if row.get('status')=='stage_2':promoted=row['promoted']
        if promoted:
            total=16*len(promoted)
            completed=sum(len(list((WORK/'development'/f'dps-legacy-r1e-07-s150-eta{eta:g}').glob('[0-9][0-9][0-9][0-9].json'))) for eta in promoted)
            label=('比較対象のADEPSを150段階で確認中','Checking comparison ADEPS settings at 150 steps')
        else:
            total=96
            completed=sum(len(list(path.glob('[0-9][0-9][0-9][0-9].json'))) for path in (WORK/'development').glob('dps-legacy-r1e-07-s32-eta*'))
            label=('開発データで比較条件を調整中','Selecting comparison settings on development data')
        detail=('設定選びには既存の開発用16場面のみを使用。最終テストの結果はまだ見ていません。','Settings are selected on 16 development scenes; final-test results have not been viewed.')
    if not 0<=completed<=total:raise ValueError('Unexpected progress counts')
    return {'schema':'adeps-plus-progress/1','phase':phase,'completed':completed,'total':total,'updated_at':stamp,
            'label_jp':label[0],'label_en':label[1],'detail_jp':detail[0],'detail_en':detail[1]}


def main(watch=False):
    PUBLIC.parent.mkdir(parents=True,exist_ok=True)
    while True:
        state=snapshot();temp=PUBLIC.with_suffix('.json.tmp')
        temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');temp.replace(PUBLIC)
        if not watch or state['phase']=='complete':break
        time.sleep(15)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--watch',action='store_true')
    main(parser.parse_args().watch)
