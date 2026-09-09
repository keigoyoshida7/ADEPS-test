"""Linear array encoding diagnostics. Not ADEPS or a trained diffusion model."""
import numpy as np
from scipy.special import spherical_jn, sph_harm_y

def real_n3d(order, directions):
    d=np.asarray(directions,float);d=d/np.linalg.norm(d,axis=1)[:,None]
    theta=np.arccos(np.clip(d[:,2],-1,1));phi=np.arctan2(d[:,1],d[:,0]);out=[]
    for n in range(order+1):
        for m in range(-n,n+1):
            y=sph_harm_y(n,abs(m),theta,phi)
            v=y.real if m==0 else np.sqrt(2)*((-1)**m)*(y.imag if m<0 else y.real)
            out.append(v*np.sqrt(4*np.pi))
    return np.stack(out,axis=-1)

def modal_matrix(freqs,positions,order,c=343.):
    xyz=np.asarray(positions,float);r=np.linalg.norm(xyz,axis=1)
    if np.any(r<=0):raise ValueError('マイク位置は原点から離してください。')
    Y=real_n3d(order,xyz);V=np.empty((len(freqs),len(xyz),(order+1)**2),complex)
    for n in range(order+1):
        sl=slice(n*n,(n+1)**2)
        radial=(1j**n)*spherical_jn(n,2*np.pi*np.asarray(freqs)[:,None]*r[None,:]/c)
        V[:,:,sl]=radial[:,:,None]*Y[None,:,sl]
    return V

def complex_array(real,imag,name):
    a=np.asarray(real,float);b=np.asarray(imag,float)
    if a.shape!=b.shape or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError(name+' の実部・虚部の形状または数値が不正です。')
    return a+1j*b

def encode(V,p,regularization):
    F,Q,C=V.shape
    if p.shape[:2]!=(F,Q):raise ValueError('VとマイクSTFTの周波数・マイク数が一致しません。')
    vv=V@V.conj().transpose(0,2,1)
    gamma2=regularization*np.real(np.trace(vv,axis1=1,axis2=2))/Q
    gamma2=np.maximum(gamma2,1e-12)
    E=V.conj().transpose(0,2,1)@np.linalg.solve(vv+gamma2[:,None,None]*np.eye(Q),np.broadcast_to(np.eye(Q),(F,Q,Q)))
    return E@p,E,gamma2

def run_capture(config):
    reg=float(config.get('regularization',.001))
    if not 1e-8<=reg<=10:raise ValueError('正則化は1e-8〜10にしてください。')
    rng=np.random.default_rng(int(config.get('seed',42)))
    imported=config.get('bundle')
    ref=None
    if imported is not None:
        if not isinstance(imported,dict):raise ValueError('bundleはJSON objectにしてください。')
        if imported.get('schema')!='adeps-test-array-stft/1':raise ValueError('schema はadeps-test-array-stft/1が必要です。')
        freqs=np.asarray(imported['frequencies_hz'],float)
        if freqs.ndim!=1:raise ValueError('周波数は1次元配列で指定してください。')
        V=complex_array(imported['V_real'],imported['V_imag'],'V')
        p=complex_array(imported['p_real'],imported['p_imag'],'p')
        if V.ndim!=3 or p.ndim!=3 or any(n==0 for n in V.shape+p.shape) or V.shape[0]!=len(freqs) or p.size>3000000 or V.size>300000 or V.shape[1]>64 or V.shape[2]>256:
            raise ValueError('行列の次元・サイズが対応範囲外です。V=[F,Q,C], p=[F,Q,T]。')
        if 'reference_real' in imported:ref=complex_array(imported['reference_real'],imported['reference_imag'],'reference')
        positions=imported.get('microphone_positions_m',[])
        if 'microphone_positions_m' in imported:
            pos=np.asarray(positions,float)
            if pos.shape!=(V.shape[1],3) or not np.all(np.isfinite(pos)):raise ValueError('マイク座標は有限の[Q,3]配列が必要です。')
        provenance=imported.get('provenance','imported')
        conventions=imported.get('conventions','未記載：規約の一致を確認してください')
        order=int(round(np.sqrt(V.shape[-1])-1))
        if (order+1)**2!=V.shape[-1] or order<1:raise ValueError('FOA出力には4以上の平方数の係数が必要です。')
        if imported.get('sh_ordering')!='ACN' or imported.get('sh_normalization') not in ['N3D','SN3D']:raise ValueError('FOAの先頭4係数を読むため、sh_ordering: ACN と sh_normalization: N3D または SN3D を明記してください。')
        conventions=f"入力申告：ACN/{imported['sh_normalization']}。{conventions}"
    else:
        Q=int(config.get('microphones',8));radius=float(config.get('radius_m',.06));noise=float(config.get('snr_db',35))
        if Q not in [4,6,8,12,16] or not .01<=radius<=.25 or not 0<=noise<=80:raise ValueError('マイク数・半径・SNRが範囲外です。')
        coplanar=bool(config.get('coplanar',False));theta=np.arange(Q)*np.pi*(3-np.sqrt(5))
        z=np.zeros(Q) if coplanar else 1-2*(np.arange(Q)+.5)/Q
        positions=np.c_[np.sqrt(1-z*z)*np.cos(theta),np.sqrt(1-z*z)*np.sin(theta),z]*radius
        freqs=np.geomspace(80,10000,64);order=1;true_order=3 if config.get('mismatch',True) else 1
        V=modal_matrix(freqs,positions,order);Vtrue=modal_matrix(freqs,positions,true_order)
        dirs=np.array([[.8,.45,.3],[-.4,.7,-.2]])
        a=real_n3d(true_order,dirs).T
        sig=(rng.normal(size=(len(freqs),2,96))+1j*rng.normal(size=(len(freqs),2,96)))/np.sqrt(2)
        truth=np.einsum('cs,fst->fct',a,sig)
        p=Vtrue@truth;scale=np.sqrt(np.mean(abs(p)**2,axis=(1,2)))*10**(-noise/20)
        p=p+scale[:,None,None]*(rng.normal(size=p.shape)+1j*rng.normal(size=p.shape))/np.sqrt(2)
        ref=truth[:,:4,:];provenance='synthetic';conventions='試作規約：real ACN/N3D、自由空間・無指向性、exp(+ikr·d)。論文の規約を再現したものではない。'
    if len(freqs)<2 or np.any(~np.isfinite(freqs)) or np.any(freqs<=0) or np.any(np.diff(freqs)<=0):raise ValueError('周波数は正の昇順で指定してください。')
    if V.shape[:2]!=p.shape[:2]:raise ValueError('Vとpの周波数・マイク数が一致しません。')
    if V.shape[0]*V.shape[2]*p.shape[2]>3_000_000:raise ValueError('復元後の行列は300万複素要素までです。時間フレームを共通に分割してください。')
    encoded,E,gamma2=encode(V,p,reg)
    count=min(4,encoded.shape[1]);out=encoded[:,:count]
    residual=V@encoded-p
    observation_norm=np.linalg.norm(p,axis=(1,2))
    ratio=np.divide(np.linalg.norm(residual,axis=(1,2)),observation_norm,out=np.full(len(freqs),np.nan),where=observation_norm>0)
    resdb=20*np.log10(np.maximum(ratio,1e-12))
    sv=np.linalg.svd(V,compute_uv=False);ranks=np.sum(sv>sv[:,0,None]*1e-8,axis=1)
    cond=np.divide(sv[:,0],sv[:,-1],out=np.full(len(freqs),np.inf),where=sv[:,-1]>1e-15)
    cond=np.where(ranks<V.shape[2],np.inf,cond)
    curves={'frequency_hz':freqs.tolist(),'residual_db':[float(x) if np.isfinite(x) else None for x in resdb],'condition':[float(x) if np.isfinite(x) else None for x in cond]}
    quality={'reference_available':ref is not None,'complex_nrmse_db':None,'coherence':None,'si_sdr_db':None}
    if ref is not None:
        if ref.shape!=out.shape:raise ValueError(f'参照信号の形状は{out.shape}に合わせてください。時間・規約も同一である必要があります。')
        if np.any(np.sum(abs(ref)**2,axis=(1,2))<=0):raise ValueError('参照のエネルギーが0の周波数があり、正規化誤差を定義できません。')
        err=20*np.log10(np.maximum(np.linalg.norm(out-ref,axis=(1,2))/np.maximum(np.linalg.norm(ref,axis=(1,2)),1e-15),1e-12))
        cross=np.sum(out*np.conj(ref),axis=2)
        denom=np.sum(abs(out)**2,axis=2)*np.sum(abs(ref)**2,axis=2)
        valid=denom>np.finfo(float).tiny
        coh=np.divide(abs(cross)**2,denom,out=np.full_like(denom,np.nan),where=valid)
        coh=np.clip(coh,0,1)
        coh_freq=np.divide(np.nansum(coh,axis=1),valid.sum(axis=1),out=np.full(len(freqs),np.nan),where=valid.sum(axis=1)>0)
        quality.update(complex_nrmse_db=float(20*np.log10(max(np.linalg.norm(out-ref)/max(np.linalg.norm(ref),1e-15),1e-12))),coherence=float(np.nanmean(coh)) if np.any(valid) else None,coherence_valid_bins=int(valid.sum()),coherence_total_bins=int(valid.size))
        curves.update(error_db=err.tolist(),coherence=[float(x) if np.isfinite(x) else None for x in coh_freq])
    fidx=int(np.argmin(abs(freqs-1000)))
    return {'kind':'capture','provenance':provenance,'method':'線形ridge符号化 / ADEPS未接続','quality':quality,'curves':curves,'microphone_positions_m':np.asarray(positions).tolist(),'order':order,'microphones':V.shape[1],'coefficients':V.shape[2],'rank_min':int(min(ranks)),'rank_by_frequency':ranks.tolist(),'singular_values_at_1khz':sv[fidx].tolist(),'encoder_magnitude_at_1khz':abs(E[fidx,:count]).tolist(),'conventions':conventions,'notes':['デモは単一の合成周波数領域モデル。論文の音声・残響・学習条件とは異なります。','参照がない実測データでは品質誤差とcoherenceを算出しません。','SI-SDRは対応する時間信号の評価を未実装のため未算出。','残差が小さいことだけでは空間復元が正しいとは限りません。','観測エネルギーが0の周波数では相対残差を未算出にします。'],'prototype_regularization':reg,'gamma_squared_by_frequency':gamma2.tolist()}
