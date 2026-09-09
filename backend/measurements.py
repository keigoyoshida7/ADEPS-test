"""Read synchronized IR WAV bundles. Never contact capture hardware."""
import io,json,zipfile
import numpy as np
from scipy.io import wavfile
from numerics import ir_to_transfer,ir_diagnostics,regularized_mimo,evaluate_transfer,to_jsonable

def read_bundle(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sum(x.file_size for x in z.infolist())>100_000_000:raise ValueError('展開後100 MBまでです。')
        if len(z.infolist())>200:raise ValueError('ZIP内のファイルが多すぎます。')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('schema')!='adeps-test-ir-bundle/1':raise ValueError('schema: adeps-test-ir-bundle/1 が必要です。')
        files=manifest.get('speaker_files',[])
        if not 1<=len(files)<=32:raise ValueError('スピーカーWAVは1〜32個にしてください。')
        fs=None;shape=None
        def read_set(names):
            nonlocal fs,shape
            arrays=[]
            for name in names:
                rate,raw=wavfile.read(io.BytesIO(z.read(name)))
                if raw.ndim==1:raw=raw[:,None]
                if raw.ndim!=2 or raw.shape[1]>64:raise ValueError('WAVのマイク数は64chまでです。')
                if np.issubdtype(raw.dtype,np.integer):
                    info=np.iinfo(raw.dtype)
                    a=(raw.astype(float)-128)/128 if raw.dtype==np.uint8 else raw.astype(float)/max(abs(info.min),info.max)
                else:a=raw.astype(float)
                if not np.all(np.isfinite(a)):raise ValueError('WAVに非有限値があります。')
                if fs is None:fs,shape=rate,a.shape
                if rate!=fs or a.shape!=shape:raise ValueError('全WAVのサンプルレート・長さ・マイク数を揃えてください。個別の時間合わせは行いません。')
                arrays.append(a.T)
            return np.stack(arrays,axis=1)
        observed=read_set(files)
        if observed.size>3_000_000:raise ValueError('IRは合計300万サンプルまでです。測定後、共通の時間窓で切り出してください。')
        target_files=manifest.get('target_files',[])
        if target_files and len(target_files)!=len(files):raise ValueError('target_filesはspeaker_filesと同数が必要です。')
        target=read_set(target_files) if target_files else None
    return manifest,fs,observed,target

def analyze_bundle(data,regularization=.02):
    m,fs,ir,target=read_bundle(data)
    freqs=np.geomspace(80,min(8000,fs*.45),64)
    H=ir_to_transfer(ir,fs,freqs);diag=ir_diagnostics(ir,fs)
    result={'kind':'ir','provenance':m.get('provenance','imported_unverified'),'manifest':m,'sample_rate':fs,'samples':ir.shape[2],'microphones':ir.shape[0],'speakers':ir.shape[1],'frequencies_hz':freqs,'diagnostics':diag,'response_db':20*np.log10(np.maximum(abs(H),1e-15)),'target_available':target is not None,'notes':['入力ZIPを解析しました。測定日時・時刻原点・ゲインはmanifestの申告値で、現場確認はしていません。','相対ピーク10%の到達時刻は目安です。ノイズや反射で直接音からずれる場合があります。','各IRの時間位置を個別に揃えると相対遅延が消えるため、自動整列しません。']}
    if target is not None:
        T=ir_to_transfer(target,fs,freqs)
        train=m.get('training_indices',list(range(ir.shape[0])))
        held=m.get('heldout_indices',[])
        if not train or any(type(i)!=int or not 0<=i<ir.shape[0] for i in train+held) or len(set(train+held))!=len(train+held):raise ValueError('訓練・未使用点のindexは重複なしの有効な0始まり整数が必要です。')
        fit=regularized_mimo(H[:,train],T[:,train],regularization,2.)
        metrics={'training':evaluate_transfer(H[:,train],T[:,train],fit['G'])}
        if held:metrics['heldout']=evaluate_transfer(H[:,held],T[:,held],fit['G'])
        for v in metrics.values():v.pop('corrected_transfer')
        result.update(metrics=metrics,correction=fit['G'],rank_by_frequency=fit['rank'],regularization=regularization)
    return to_jsonable(result)

def sample_zip():
    """Tiny synthetic fixture; deliberately labeled, never a physical measurement."""
    fs=48000;n=2048;ns=4;nm=6
    ir=np.zeros((nm,ns,n),np.float32);target=np.zeros_like(ir)
    for p in range(nm):
        for s in range(ns):
            delay=300+80*p+60*s;gain=1/(2+p*.3+s*.2)
            target[p,s,delay]=gain
            ir[p,s,delay+(48 if s==0 else 0)]=gain*(.5 if s==0 else 1)
            ir[p,s,delay+333]=gain*.18
    manifest={'schema':'adeps-test-ir-bundle/1','provenance':'synthetic_fixture_not_a_measurement','description':'動作確認用：4仮想スピーカー、6仮想測定点。実測ではありません。','speaker_files':[f'speaker_{s+1:02d}.wav' for s in range(ns)],'target_files':[f'target_{s+1:02d}.wav' for s in range(ns)],'training_indices':[0,1,2,3],'heldout_indices':[4,5],'time_reference':'common sample 0; no independent alignment','level_reference':'arbitrary normalized digital units','speaker_labels':[f'S{s+1}' for s in range(ns)],'microphone_labels':[f'M{p+1}' for p in range(nm)]}
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for group,arr in [('speaker',ir),('target',target)]:
            for s in range(ns):
                wav=io.BytesIO();wavfile.write(wav,fs,arr[:,s].T);z.writestr(f'{group}_{s+1:02d}.wav',wav.getvalue())
    return output.getvalue()
