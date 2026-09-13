"""Train-only ideal-HOA covariance and its explicitly linear Wiener baseline.

This is an additional statistical baseline, not a diffusion model. Targets
used to fit covariance have no array geometry; inference uses p and V only.
"""
import numpy as np


def covariance_from_targets(targets):
    moments, count = None, 0
    for value in targets:
        a = np.asarray(value, np.complex128)
        if a.ndim != 3 or a.shape[1] != 36 or not np.isfinite(a).all():
            raise ValueError('Expected finite ideal [F,36,T] HOA targets')
        rms = float(np.sqrt(np.mean(abs(a)**2)))
        if rms < 1e-12:
            raise ValueError('Cannot fit a silent target')
        scaled = a/rms
        moment = scaled@scaled.conj().transpose(0,2,1)/a.shape[2]
        moments = moment if moments is None else moments+moment
        count += 1
    if not count:
        raise ValueError('No training targets')
    return moments/count, count


def wiener(p, v, covariance, *, shrinkage=.5, regularization=1e-5):
    p, v, covariance = map(lambda x:np.asarray(x,np.complex128), (p,v,covariance))
    if (p.ndim!=3 or v.ndim!=3 or covariance.shape!=(v.shape[0],v.shape[2],v.shape[2])
        or p.shape[:2]!=v.shape[:2] or not all(np.isfinite(x).all() for x in (p,v,covariance))):
        raise ValueError('Invalid Wiener arrays')
    if not 0<=shrinkage<=1 or not 0<=regularization<=10:
        raise ValueError('Invalid shrinkage or regularization')
    f,q,c=v.shape
    ca=(covariance+covariance.conj().transpose(0,2,1))/2
    power=np.real(np.trace(ca,axis1=1,axis2=2))/c
    if np.any(power<=0):
        raise ValueError('Training covariance must have positive power at every frequency')
    ca=(1-shrinkage)*ca+shrinkage*power[:,None,None]*np.eye(c)
    vh=v.conj().transpose(0,2,1)
    gram=v@ca@vh
    ridge=np.maximum(regularization*np.real(np.trace(gram,axis1=1,axis2=2))/q,1e-20)
    operator=ca@vh@np.linalg.solve(gram+ridge[:,None,None]*np.eye(q),np.broadcast_to(np.eye(q),(f,q,q)))
    result=operator@p
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite Wiener solution')
    return result
