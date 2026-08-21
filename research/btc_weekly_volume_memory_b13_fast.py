#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import btc_weekly_volume_memory_b13 as base


def profile_levels_array(high, low, close, volume):
    lo=float(np.min(low)); hi=float(np.max(high))
    tp=(high+low+close)/3.0
    vs=float(np.sum(volume))
    vwap=float(np.sum(tp*volume)/vs) if vs>0 else float(np.mean(tp))
    if not np.isfinite(hi-lo) or hi<=lo+1e-12:
        m=float(np.mean(tp)); return vwap,m,m,m
    edges=np.linspace(lo,hi,25)
    centers=(edges[:-1]+edges[1:])/2.0
    bi=np.searchsorted(edges,tp,side='right')-1
    bi=np.clip(bi,0,23)
    hist=np.bincount(bi,weights=volume,minlength=24).astype(float)
    poc=int(np.argmax(hist))
    target=0.70*float(np.sum(hist))
    left=right=poc; cum=float(hist[poc])
    while cum<target and (left>0 or right<23):
        lv=float(hist[left-1]) if left>0 else -1.0
        rv=float(hist[right+1]) if right<23 else -1.0
        if left>0 and (right>=23 or lv>=rv):
            left-=1; cum+=float(hist[left])
        elif right<23:
            right+=1; cum+=float(hist[right])
        else:
            break
    return vwap,float(centers[poc]),float(centers[left]),float(centers[right])


def build_level_state_fast(x15, tf):
    keys=base.period_key(x15.index,tf)
    kns=keys.asi8
    starts=np.flatnonzero(np.r_[True,kns[1:]!=kns[:-1]])
    ends=np.r_[starts[1:],len(x15)]
    hi=x15.high.to_numpy(float); lo=x15.low.to_numpy(float)
    cl=x15.close.to_numpy(float); vol=x15.volume.to_numpy(float)
    expected={'H1':4,'H4':16,'D1':96,'W1':672}[tf]
    min_n=max(1,int(expected*0.95))
    dur=base.duration(tf)
    rows=[]
    for n,(s,e) in enumerate(zip(starts,ends),1):
        if e-s<min_n: continue
        vwap,poc,val,vah=profile_levels_array(hi[s:e],lo[s:e],cl[s:e],vol[s:e])
        k=pd.Timestamp(keys[s])
        rows.append((k+dur,k.isoformat(),vwap,poc,val,vah))
        if n%10000==0: print('profile',tf,n,'/',len(starts),flush=True)
    q=pd.DataFrame(rows,columns=['avail_ts','instance','VWAP','POC','VAL','VAH'])
    return q.sort_values('avail_ts').set_index('avail_ts')


def generate_candidates_fast(h1, states):
    idx=h1.index
    o=h1.open.to_numpy(float); hi=h1.high.to_numpy(float)
    lo=h1.low.to_numpy(float); cl=h1.close.to_numpy(float)
    atr=h1.atr14.to_numpy(float)
    exe=base.execution(h1)
    rows=[]
    for tf,state in states.items():
        print('volume atlas FAST',tf,flush=True)
        inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
        valid=np.array([x is not None and str(x)!='nan' for x in inst],dtype=bool)
        for lev in base.LEVELS:
            lv=state[lev].reindex(idx,method='ffill').to_numpy(float)
            for side in ('LONG','SHORT'):
                role='SUPPORT' if side=='LONG' else 'RESISTANCE'
                for mode in base.MODES:
                    mask=base.confirmation(mode,side,o,hi,lo,cl,lv,atr)&valid
                    inds=np.flatnonzero(mask)
                    if not len(inds): continue
                    # Active source-period instances are monotone in time. Among qualifying
                    # bars, keep only the first qualifying bar for each level-instance+role,
                    # exactly matching the original seen-set semantics.
                    qi=inst[inds]
                    keep=np.r_[True,qi[1:]!=qi[:-1]]
                    first_inds=inds[keep]
                    rule=f'{tf}|{lev}|{role}|{mode}'
                    for i in first_inds:
                        tr=exe(int(i),side)
                        if tr is None: continue
                        iid=f'{tf}|{lev}|{inst[i]}|{role}'
                        rows.append({'rule':rule,'source_tf':tf,'level_type':lev,'role':role,'mode':mode,
                                     'signal_i':int(i),'signal_ts':idx[i],'side':side,'level':float(lv[i]),
                                     'instance':iid,'week':base.b11.week_key(base.b11.week_start(idx[i])),**tr})
        print('candidates so far',len(rows),flush=True)
    q=pd.DataFrame(rows)
    if q.empty: raise RuntimeError('no B13 candidates')
    return q.sort_values(['signal_ts','rule']).reset_index(drop=True)


def main():
    # Monkey-patch only computational implementation; frozen semantics stay identical.
    base.build_level_state=build_level_state_fast
    base.generate_candidates=generate_candidates_fast
    base.main()


if __name__=='__main__':
    main()
