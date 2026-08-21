#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score

import btc_weekly_mtf_level_atlas_b11 as b11

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_LEVEL_SURVIVAL_B12_Result.md'
OUT_JSON=ROOT/'BTC_WEEKLY_LEVEL_SURVIVAL_B12_Result.json'
OUT_SEL=ROOT/'BTC_WEEKLY_LEVEL_SURVIVAL_B12_Selected.csv'
OUT_THRESH=ROOT/'BTC_WEEKLY_LEVEL_SURVIVAL_B12_Thresholds.csv'
OUT_IMP=ROOT/'BTC_WEEKLY_LEVEL_SURVIVAL_B12_Importances.csv'

QUANTILES=[0.50,0.60,0.70,0.80,0.85,0.90,0.925,0.95,0.975,0.99,0.995]
TF_CATS=['H1','H4','D1','W1']
FAM_CATS=[
    'PREV_HIGH','PREV_LOW','PREV_OPEN','R3_HIGH','R3_LOW','R6_HIGH','R6_LOW',
    'R12_HIGH','R12_LOW','SWING2_HIGH','SWING2_LOW'
]


def pct(v):
    return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{100*float(v):.2f}%'

def num(v,n=3):
    return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{float(v):.{n}f}'

def parse_instance_ts(s):
    try:
        return pd.Timestamp(str(s).split('|',2)[2])
    except Exception:
        return pd.NaT

def crossing_count(a,level):
    if len(a)<2:return 0
    d=np.asarray(a,float)-float(level)
    return int(np.sum((d[:-1]*d[1:])<0))

def since_last_cross(a,level,cap=72):
    if len(a)<2:return cap
    d=np.asarray(a,float)-float(level)
    ix=np.flatnonzero((d[:-1]*d[1:])<0)
    if not len(ix):return cap
    # ix is transition from ix to ix+1; bars elapsed from newest crossing endpoint.
    return int(min(cap,len(a)-1-(int(ix[-1])+1)))

def build_features(h1,cand):
    z=b11.add_atr(h1)
    idx=z.index
    o=z.open.to_numpy(float); hi=z.high.to_numpy(float); lo=z.low.to_numpy(float); cl=z.close.to_numpy(float); atr=z.atr14.to_numpy(float)
    med24=pd.Series(atr,index=idx).rolling(24,min_periods=12).median().to_numpy(float)
    med72=pd.Series(atr,index=idx).rolling(72,min_periods=24).median().to_numpy(float)
    rows=[]; keep=[]
    for ri,r in cand.iterrows():
        i=int(r.signal_i)
        if i<72 or i>=len(z):continue
        A=float(atr[i]); C=float(cl[i]); L=float(r.level)
        if not np.isfinite(A) or A<=0 or not np.isfinite(C) or C<=0 or not np.isfinite(L):continue
        side=str(r.side); sg=1.0 if side=='LONG' else -1.0
        f={}
        its=parse_instance_ts(r.instance)
        age=(idx[i]-its).total_seconds()/3600.0 if pd.notna(its) else 1344.0
        f['level_age_h']=float(np.clip(age,0,1344))
        for n in (12,24,48,72):
            a=i-n; ph=hi[a:i]; pl=lo[a:i]; pc=cl[a:i]
            f[f'touch_count_{n}']=float(np.sum((pl<=L)&(ph>=L)))
            f[f'near025_count_{n}']=float(np.sum(np.abs(pc-L)<=0.25*A))
            f[f'near050_count_{n}']=float(np.sum(np.abs(pc-L)<=0.50*A))
            f[f'cross_count_{n}']=float(crossing_count(pc,L))
        for n in (6,12,24,48):
            pc=cl[i-n:i]
            f[f'expected_side_frac_{n}']=float(np.mean(sg*(pc-L)>=0))
        f['bars_since_cross_72']=float(since_last_cross(cl[i-72:i],L,72))
        for n in (12,24,48):
            f[f'max_abs_dist_{n}']=float(np.max(np.abs(cl[i-n:i]-L))/A)
        for n in (1,2,4,8,12,24):
            f[f'aligned_ret_{n}']=float(np.clip(sg*(C/float(cl[i-n])-1.0),-0.25,0.25))
            f[f'prior_level_dist_{n}']=float(np.clip(sg*(float(cl[i-n])-L)/A,-20,20))
        for n in (6,12):
            f[f'distance_compression_{n}']=float(np.clip((abs(float(cl[i-n])-L)-abs(C-L))/A,-20,20))
        O=float(o[i]); H=float(hi[i]); LL=float(lo[i]); TR=max(H-LL,1e-12)
        body=C-O
        lower=max(0.0,min(O,C)-LL); upper=max(0.0,H-max(O,C))
        if side=='LONG':
            reject=lower; oppose=upper; penetration=max(0.0,L-LL)
        else:
            reject=upper; oppose=lower; penetration=max(0.0,H-L)
        f['signal_body_aligned']=float(np.clip(sg*body/A,-10,10))
        f['reject_wick_atr']=float(np.clip(reject/A,0,10))
        f['oppose_wick_atr']=float(np.clip(oppose/A,0,10))
        f['penetration_atr']=float(np.clip(penetration/A,0,10))
        f['reclaim_atr']=float(np.clip(sg*(C-L)/A,-10,10))
        f['signal_tr_atr']=float(np.clip(TR/A,0,10))
        f['atr_pct']=float(A/C)
        f['atr_vs_med24']=float(np.clip(A/med24[i],0,10)) if np.isfinite(med24[i]) and med24[i]>0 else 1.0
        f['atr_vs_med72']=float(np.clip(A/med72[i],0,10)) if np.isfinite(med72[i]) and med72[i]>0 else 1.0
        w=b11.week_start(idx[i]); aidx=int(idx.searchsorted(w,side='left'))
        run_hi=float(np.max(hi[aidx:i+1])); run_lo=float(np.min(lo[aidx:i+1]))
        f['week_range_pct']=float((run_hi-run_lo)/C)
        rem=(w+pd.Timedelta(days=7)-idx[i]).total_seconds()/3600.0
        f['hours_remaining']=float(np.clip(rem,0,168))
        hour=idx[i].hour; wd=idx[i].weekday()
        f['hour_sin']=math.sin(2*math.pi*hour/24); f['hour_cos']=math.cos(2*math.pi*hour/24)
        f['weekday_sin']=math.sin(2*math.pi*wd/7); f['weekday_cos']=math.cos(2*math.pi*wd/7)
        f['role_long']=1.0 if side=='LONG' else 0.0
        for tf in TF_CATS:f[f'tf_{tf}']=1.0 if str(r.source_tf)==tf else 0.0
        for fam in FAM_CATS:f[f'fam_{fam}']=1.0 if str(r.family)==fam else 0.0
        rows.append(f); keep.append(ri)
    X=pd.DataFrame(rows,index=keep)
    meta=cand.loc[keep].copy()
    meta['WIN']=(meta.reason=='TP').astype(int)
    meta['event_key']=meta.source_tf.astype(str)+'|'+meta.family.astype(str)+'|'+meta.side.astype(str)+'|'+meta.instance.astype(str)
    return X,meta

def part_mask(meta,name):
    t=pd.to_datetime(meta.signal_ts,utc=True)
    if name=='external':return (t>=b11.EXT0)&(t<b11.EXT1)
    if name=='development':return (t>=b11.DEV0)&(t<b11.DEV1)
    if name=='reference_validation':return (t>=b11.VAL0)&(t<b11.VAL1)
    if name=='august':return (t>=b11.AUG0)&(t<b11.AUG1)
    raise ValueError(name)

def scan_ok(ts):
    t=pd.Timestamp(ts); w=b11.week_start(t); return t<=w+pd.Timedelta(days=5,hours=12)

def route(scored,threshold,weeks):
    ws=b11.week_set(weeks)
    q=scored[scored.week.isin(ws)&scored.signal_ts.map(scan_ok)&(scored.p_hold>=threshold)].copy()
    if q.empty:return q
    q=q.sort_values(['week','signal_ts','p_hold','event_key'],ascending=[True,True,False,True])
    # At each timestamp, highest p event; then first qualifying timestamp/week.
    q=q.groupby(['week','signal_ts'],as_index=False,sort=False).head(1)
    q=q.sort_values(['week','signal_ts']).groupby('week',as_index=False,sort=False).head(1).copy()
    q['route']='LEVEL_SURVIVAL_TRIGGER'
    return q.sort_values('signal_ts').reset_index(drop=True)

def stat(q,weeks):return b11.stat(q,weeks)
def blocks(q,weeks):return b11.block_stats(q,weeks)

def threshold_table(dev,weeks):
    vals=dev.p_hold.to_numpy(float)
    rows=[]
    for qq in QUANTILES:
        th=float(np.quantile(vals,qq)); sel=route(dev,th,weeks); s=stat(sel,weeks)
        rows.append({'quantile':qq,'threshold':th,**s})
    r=pd.DataFrame(rows)
    r['fullcov']=(r.coverage>=1-1e-12).astype(int); r['wr_sort']=r.wr.fillna(-1.0); r['pf_sort']=r.pf.fillna(-1.0)
    r=r.sort_values(['fullcov','wr_sort','wilson','pf_sort','quantile'],ascending=[False,False,False,False,True]).reset_index(drop=True)
    r['selection_rank']=np.arange(1,len(r)+1)
    return r

def gate(s,bs,weeks,wrmin):
    return (s['n']==len(weeks) and abs(s['coverage']-1)<1e-12 and s['wr'] is not None and s['wr']>=wrmin and
            s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1 and
            (s['max_ls']==0 if wrmin>=1 else s['max_ls']<=2) and
            sum(1 for b in bs if b['exp'] is not None and b['exp']>0)>=(4 if wrmin>=1 else 3))

def main():
    h1=b11.load_h1(); print('loaded',len(h1),h1.index.min(),h1.index.max())
    levels={tf:b11.build_source_levels(b11.source_bars(h1,tf),tf) for tf in b11.SOURCE_TFS}
    allcand=b11.generate_candidates(h1,levels)
    cand=allcand[allcand['mode']=='HOLD'].copy().reset_index(drop=True)
    print('HOLD candidates',len(cand))
    X,meta=build_features(h1,cand)
    feat=list(X.columns)
    dm=part_mask(meta,'development')
    Xd=X.loc[dm]; yd=meta.loc[dm,'WIN'].to_numpy(int)
    if len(np.unique(yd))<2:raise RuntimeError('development labels lack both classes')
    clf=RandomForestClassifier(n_estimators=600,max_depth=10,min_samples_leaf=25,max_features='sqrt',
                               class_weight='balanced_subsample',random_state=20260821,n_jobs=-1)
    clf.fit(Xd.to_numpy(float),yd)
    meta=meta.copy(); meta['p_hold']=clf.predict_proba(X.to_numpy(float))[:,1]
    imp=pd.DataFrame({'feature':feat,'importance':clf.feature_importances_}).sort_values('importance',ascending=False)
    imp.to_csv(OUT_IMP,index=False)
    dev=meta.loc[dm].copy(); dev_weeks=b11.partition_weeks('development')
    tt=threshold_table(dev,dev_weeks); tt.to_csv(OUT_THRESH,index=False)
    chosen=tt.iloc[0]; threshold=float(chosen.threshold); quantile=float(chosen.quantile)
    summary={}; selected=[]
    diagnostics={}
    for part in ('development','external','reference_validation','august'):
        pm=part_mask(meta,part); q=meta.loc[pm].copy(); weeks=b11.partition_weeks(part)
        sel=route(q,threshold,weeks); s=stat(sel,weeks); bs=blocks(sel,weeks)
        if len(sel):
            x=sel.copy(); x['partition']=part; selected.append(x)
        y=q.WIN.to_numpy(int); p=q.p_hold.to_numpy(float)
        auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None
        acc=float(accuracy_score(y,p>=0.5)) if len(y) else None
        dist=(sel.groupby(['source_tf','family','side']).size().sort_values(ascending=False).head(15).to_dict() if len(sel) else {})
        summary[part]={'stat':s,'blocks':bs,'candidate_n':int(len(q)),'candidate_win_rate':float(y.mean()) if len(y) else None,
                       'auc':auc,'accuracy_05':acc,'selected_distribution':{str(k):int(v) for k,v in dist.items()}}
    if selected:pd.concat(selected,ignore_index=True).to_csv(OUT_SEL,index=False)
    ew=b11.partition_weeks('external'); vw=b11.partition_weeks('reference_validation')
    robust=gate(summary['external']['stat'],summary['external']['blocks'],ew,1.0) and gate(summary['reference_validation']['stat'],summary['reference_validation']['blocks'],vw,1.0)
    highp=gate(summary['external']['stat'],summary['external']['blocks'],ew,0.80) and gate(summary['reference_validation']['stat'],summary['reference_validation']['blocks'],vw,0.80)
    result={'experiment':'B12_LEVEL_SURVIVAL','threshold_quantile':quantile,'threshold':threshold,'feature_count':len(feat),
            'development_candidate_n':int(dm.sum()),'summary':summary,'top_importances':imp.head(20).to_dict('records'),
            'gates':{'B12_ROBUST_WEEKLY_100':'PASS' if robust else 'FAIL','B12_HIGH_PRECISION_WEEKLY':'PASS' if highp else 'FAIL'},
            'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# BTC Weekly Level Survival B12 — Result','',f"**Verdict: {'B12_ROBUST_WEEKLY_100_PASS' if robust else 'B12_NO_ROBUST_WEEKLY_100'}**",'',
           f'Frozen development threshold quantile **{quantile:.3f}**, p_hold threshold **{threshold:.6f}**.','',
           'Execution: completed level-touch H1 -> next H1 open; net +1% / -1%; 0.15% fee; adverse-first; no non-level fallback.','',
           '| Partition | Candidates / candidate WR / AUC | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for part in ('development','external','reference_validation','august'):
        d=summary[part]; s=d['stat']
        lines.append(f"| {part} | {d['candidate_n']} / {pct(d['candidate_win_rate'])} / {num(d['auc'])} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} | {s['max_ls']} |")
    lines += ['','## Development threshold table','',
              '| Q | Threshold | Coverage | WR | Wilson LB | PF | N |','|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in tt.sort_values('quantile').iterrows():
        lines.append(f"| {r.quantile:.3f} | {r.threshold:.6f} | {pct(r.coverage)} | {pct(r.wr)} | {pct(r.wilson)} | {num(r.pf)} | {int(r.n)} |")
    lines += ['','## Top model importances (descriptive only)','',
              '| Feature | Importance |','|---|---:|']
    for _,r in imp.head(15).iterrows():lines.append(f"| {r.feature} | {r.importance:.5f} |")
    lines += ['','## Gates','',f"- B12_ROBUST_WEEKLY_100: **{'PASS' if robust else 'FAIL'}**",f"- B12_HIGH_PRECISION_WEEKLY: **{'PASS' if highp else 'FAIL'}**",'',
              'No post-result retuning inside B12. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines))

if __name__=='__main__':main()
