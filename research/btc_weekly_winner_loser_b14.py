#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, accuracy_score

import btc_h1_low_reject_structure_lr1 as dataio
import btc_weekly_direction_b10 as b10

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_WINNER_LOSER_B14_Result.md'
OUT_JSON=ROOT/'BTC_WEEKLY_WINNER_LOSER_B14_Result.json'
OUT_FEATURES=ROOT/'BTC_WEEKLY_WINNER_LOSER_B14_Features.csv'
OUT_TOP=ROOT/'BTC_WEEKLY_WINNER_LOSER_B14_Top20.csv'
OUT_Q=ROOT/'BTC_WEEKLY_WINNER_LOSER_B14_Quantiles.csv'
OUT_LOG=ROOT/'BTC_WEEKLY_WINNER_LOSER_B14_Run.log'

REV='B14_V1'
SAT_HOURS=5*24+12
EXT0=pd.Timestamp('2020-01-01',tz='UTC'); EXT1=pd.Timestamp('2022-01-01',tz='UTC')
DEV0=pd.Timestamp('2022-01-01',tz='UTC'); DEV1=pd.Timestamp('2025-01-01',tz='UTC')
VAL0=pd.Timestamp('2025-01-01',tz='UTC'); VAL1=pd.Timestamp('2026-07-30',tz='UTC')
AUG0=pd.Timestamp('2026-08-01',tz='UTC'); END=pd.Timestamp('2026-08-20',tz='UTC')

FEATURES=[
'aligned_ret1','aligned_ret3','aligned_ret6','aligned_ret12','aligned_ret24','aligned_ret48',
'eff3','eff6','eff12','eff24','dirfrac3','dirfrac6','dirfrac12',
'ema8_dist_aligned','ema21_dist_aligned','ema55_dist_aligned','ema8_slope3_aligned','ema21_slope3_aligned',
'atr_pct','tr_atr','trmean3_over24','trmean6_over24','range3_atr','range6_atr','range12_atr','range24_atr','range_vs_med12',
'body_aligned','supportive_wick','opposing_wick','close_loc_aligned','sweep_reclaim3','sweep_reclaim6','breakout3','breakout6',
'pos12_aligned','pos24_aligned','pos48_aligned','forward12_atr','forward24_atr','forward48_atr','adverse12_atr','adverse24_atr','adverse48_atr',
'prevday_forward_atr','prevday_adverse_atr','prevweek_forward_atr','prevweek_adverse_atr',
'week_pos_aligned','week_ret_aligned','week_range_pct','day_pos_aligned','day_ret_aligned','day_range_pct','hours_into_week','hours_remaining',
'hour_sin','hour_cos','dow_sin','dow_cos']

def prep():
    k=dataio.load_1h().copy(); k['ts']=pd.to_datetime(k['ts'],utc=True)
    x=k[(k.ts>=EXT0)&(k.ts<END)].set_index('ts').sort_index()[['open','high','low','close']].astype(float)
    pc=x.close.shift(1)
    tr=pd.concat([x.high-x.low,(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14,min_periods=14).mean(); x['tr']=tr; x['atr']=atr; x['atr_pct']=atr/x.close; x['tr_atr']=tr/atr
    r1=x.close.pct_change(); x['r1raw']=r1
    for n in [1,3,6,12,24,48]: x[f'ret{n}']=x.close.pct_change(n)
    absr=r1.abs()
    for n in [3,6,12,24]:
        x[f'effraw{n}']=x[f'ret{n}']/absr.rolling(n,min_periods=n).sum().replace(0,np.nan)
    for n in [3,6,12]: x[f'upfrac{n}']=(r1>0).astype(float).rolling(n,min_periods=n).mean()
    for span in [8,21,55]:
        e=x.close.ewm(span=span,adjust=False).mean(); x[f'ema{span}_dist']=(x.close-e)/atr
        if span in [8,21]: x[f'ema{span}_slope3']=e.pct_change(3)
    x['trmean3_over24']=tr.rolling(3,min_periods=3).mean()/tr.rolling(24,min_periods=24).mean()
    x['trmean6_over24']=tr.rolling(6,min_periods=6).mean()/tr.rolling(24,min_periods=24).mean()
    for n in [3,6,12,24,48]:
        hi=x.high.rolling(n,min_periods=n).max(); lo=x.low.rolling(n,min_periods=n).min()
        x[f'hi{n}']=hi; x[f'lo{n}']=lo; x[f'pos{n}']=(x.close-lo)/(hi-lo).replace(0,np.nan)
        if n in [3,6,12,24]: x[f'range{n}_atr']=(hi-lo)/atr
    x['range_vs_med12']=(x.high-x.low)/(tr.shift(1).rolling(12,min_periods=12).median())
    cr=(x.high-x.low).replace(0,np.nan); x['body_raw']=(x.close-x.open)/cr
    x['upper_wick']=(x.high-x[['open','close']].max(axis=1))/cr
    x['lower_wick']=(x[['open','close']].min(axis=1)-x.low)/cr
    x['close_loc']=(x.close-x.low)/cr
    for n in [3,6]:
        x[f'prior_hi{n}']=x.high.shift(1).rolling(n,min_periods=n).max(); x[f'prior_lo{n}']=x.low.shift(1).rolling(n,min_periods=n).min()
    # day state + prior day
    dk=pd.Series(x.index.floor('D'),index=x.index); dg=x.groupby(dk,sort=False)
    x['day_hi_run']=dg.high.cummax(); x['day_lo_run']=dg.low.cummin(); x['day_open']=dg.open.transform('first')
    x['day_pos']=(x.close-x.day_lo_run)/(x.day_hi_run-x.day_lo_run).replace(0,np.nan); x['day_ret']=x.close/x.day_open-1; x['day_range_pct']=(x.day_hi_run-x.day_lo_run)/x.day_open
    dd=x.groupby(dk).agg(high=('high','max'),low=('low','min')).sort_index(); pdmap=pd.DataFrame({'pdh':dd.high.shift(1),'pdl':dd.low.shift(1)})
    x['pdh']=dk.map(pdmap.pdh); x['pdl']=dk.map(pdmap.pdl)
    # week state + prior week
    wk=pd.Series([b10.week_start(t) for t in x.index],index=x.index); wg=x.groupby(wk,sort=False)
    x['week_start']=wk; x['week_hi_run']=wg.high.cummax(); x['week_lo_run']=wg.low.cummin(); x['week_open']=wg.open.transform('first')
    x['week_pos']=(x.close-x.week_lo_run)/(x.week_hi_run-x.week_lo_run).replace(0,np.nan); x['week_ret']=x.close/x.week_open-1; x['week_range_pct']=(x.week_hi_run-x.week_lo_run)/x.week_open
    ww=x.groupby(wk).agg(high=('high','max'),low=('low','min')).sort_index(); pw=pd.DataFrame({'pwh':ww.high.shift(1),'pwl':ww.low.shift(1)})
    x['pwh']=wk.map(pw.pwh); x['pwl']=wk.map(pw.pwl)
    hour=x.index.hour.to_numpy(float); dow=x.index.weekday.to_numpy(float)
    x['hour_sin']=np.sin(2*np.pi*hour/24); x['hour_cos']=np.cos(2*np.pi*hour/24); x['dow_sin']=np.sin(2*np.pi*dow/7); x['dow_cos']=np.cos(2*np.pi*dow/7)
    return x

def weeks_for(a,b,x): return b10.complete_weeks(a,b,x.index.max()+pd.Timedelta(hours=1))
def part_weeks(name,x):
    return {'external':weeks_for(EXT0,EXT1,x),'development':weeks_for(DEV0,DEV1,x),'reference_validation':weeks_for(VAL0,VAL1,x),'august':weeks_for(AUG0,END,x)}[name]

def side_features(x,i,side,w):
    r=x.iloc[i]; d=1.0 if side=='LONG' else -1.0; atr=float(r.atr)
    z={}
    for n in [1,3,6,12,24,48]: z[f'aligned_ret{n}']=d*float(r[f'ret{n}'])
    for n in [3,6,12,24]: z[f'eff{n}']=d*float(r[f'effraw{n}'])
    for n in [3,6,12]:
        u=float(r[f'upfrac{n}']); z[f'dirfrac{n}']=u if side=='LONG' else 1-u
    for s in [8,21,55]: z[f'ema{s}_dist_aligned']=d*float(r[f'ema{s}_dist'])
    z['ema8_slope3_aligned']=d*float(r.ema8_slope3); z['ema21_slope3_aligned']=d*float(r.ema21_slope3)
    for c in ['atr_pct','tr_atr','trmean3_over24','trmean6_over24','range3_atr','range6_atr','range12_atr','range24_atr','range_vs_med12']: z[c]=float(r[c])
    z['body_aligned']=d*float(r.body_raw); z['supportive_wick']=float(r.lower_wick if side=='LONG' else r.upper_wick); z['opposing_wick']=float(r.upper_wick if side=='LONG' else r.lower_wick); z['close_loc_aligned']=float(r.close_loc if side=='LONG' else 1-r.close_loc)
    for n in [3,6]:
        ph=float(r[f'prior_hi{n}']); pl=float(r[f'prior_lo{n}'])
        z[f'sweep_reclaim{n}']=float((r.low<pl and r.close>=pl) if side=='LONG' else (r.high>ph and r.close<=ph))
        z[f'breakout{n}']=float(r.close>ph if side=='LONG' else r.close<pl)
    for n in [12,24,48]:
        pos=float(r[f'pos{n}']); hi=float(r[f'hi{n}']); lo=float(r[f'lo{n}']);
        z[f'pos{n}_aligned']=pos if side=='LONG' else 1-pos
        z[f'forward{n}_atr']=((hi-r.close) if side=='LONG' else (r.close-lo))/atr
        z[f'adverse{n}_atr']=((r.close-lo) if side=='LONG' else (hi-r.close))/atr
    z['prevday_forward_atr']=((r.pdh-r.close) if side=='LONG' else (r.close-r.pdl))/atr; z['prevday_adverse_atr']=((r.close-r.pdl) if side=='LONG' else (r.pdh-r.close))/atr
    z['prevweek_forward_atr']=((r.pwh-r.close) if side=='LONG' else (r.close-r.pwl))/atr; z['prevweek_adverse_atr']=((r.close-r.pwl) if side=='LONG' else (r.pwh-r.close))/atr
    wp=float(r.week_pos); dp=float(r.day_pos); z['week_pos_aligned']=wp if side=='LONG' else 1-wp; z['week_ret_aligned']=d*float(r.week_ret); z['week_range_pct']=float(r.week_range_pct)
    z['day_pos_aligned']=dp if side=='LONG' else 1-dp; z['day_ret_aligned']=d*float(r.day_ret); z['day_range_pct']=float(r.day_range_pct)
    h=(x.index[i]-w).total_seconds()/3600; z['hours_into_week']=h; z['hours_remaining']=168-h
    for c in ['hour_sin','hour_cos','dow_sin','dow_cos']: z[c]=float(r[c])
    return z

def build_rows(x,name,weeks):
    rows=[]
    for wi,w in enumerate(weeks,1):
        cut=w+pd.Timedelta(hours=SAT_HOURS); a=int(x.index.searchsorted(w,'left')); b=int(x.index.searchsorted(cut,'right'))
        for i in range(a,b):
            if i+1>=len(x): continue
            for side in ['LONG','SHORT']:
                try: f=side_features(x,i,side,w)
                except Exception: continue
                if any(not np.isfinite(v) for v in f.values()): continue
                o=b10.side_outcome(x,i,side,w)
                if o is None: continue
                rows.append({'partition':name,'week':b10.week_key(w),'signal_ts':x.index[i],'side':side,'reason':o['reason'],'net_ret':float(o['net_ret']),**f})
        if wi%30==0: print(name,'weeks',wi,'/',len(weeks),flush=True)
    return pd.DataFrame(rows)

def auc_oriented(y,v):
    try:
        a=roc_auc_score(y,v); return max(a,1-a)
    except Exception:return None

def feature_stats(z,part):
    q=z[(z.partition==part)&(z.reason.isin(['TP','SL']))].copy(); y=(q.reason=='TP').astype(int).to_numpy(); out=[]
    for f in FEATURES:
        a=q.loc[q.reason=='TP',f].to_numpy(float); b=q.loc[q.reason=='SL',f].to_numpy(float)
        va=np.var(a,ddof=1) if len(a)>1 else 0; vb=np.var(b,ddof=1) if len(b)>1 else 0; pooled=math.sqrt(max(((len(a)-1)*va+(len(b)-1)*vb)/max(len(a)+len(b)-2,1),1e-18))
        smd=(float(np.mean(a))-float(np.mean(b)))/pooled
        out.append({'partition':part,'feature':f,'winner_mean':float(np.mean(a)),'loser_mean':float(np.mean(b)),'winner_median':float(np.median(a)),'loser_median':float(np.median(b)),'smd':float(smd),'abs_smd':abs(float(smd)),'auc_oriented':auc_oriented(y,q[f].to_numpy(float)),'n':len(q)})
    return pd.DataFrame(out)

def clf_stats(rows,top):
    d=rows[(rows.partition=='development')&(rows.reason.isin(['TP','SL']))]; X=d[top].to_numpy(float); y=(d.reason=='TP').astype(int).to_numpy()
    m=Pipeline([('s',StandardScaler()),('lr',LogisticRegression(C=1.0,max_iter=2000,class_weight='balanced',random_state=20260821))]); m.fit(X,y); out={}
    for p in ['development','external','reference_validation','august']:
        q=rows[(rows.partition==p)&(rows.reason.isin(['TP','SL']))]; yy=(q.reason=='TP').astype(int).to_numpy(); pr=m.predict_proba(q[top].to_numpy(float))[:,1]; pred=(pr>=.5).astype(int)
        out[p]={'n':len(q),'auc':float(roc_auc_score(yy,pr)) if len(np.unique(yy))>1 else None,'accuracy':float(accuracy_score(yy,pred)) if len(q) else None,'base_wr':float(yy.mean()) if len(q) else None}
    return out

def quantiles(rows,stable,devstats):
    d=rows[(rows.partition=='development')&(rows.reason.isin(['TP','SL']))]; out=[]
    rank=devstats.set_index('feature')
    for f in stable[:8]:
        sign=1 if float(rank.loc[f,'smd'])>0 else -1; vals=d[f].to_numpy(float); qs=[.25,.5,.75]
        for qv in qs:
            th=float(np.quantile(vals,qv));
            for p in ['development','external','reference_validation']:
                z=rows[(rows.partition==p)&(rows.reason.isin(['TP','SL']))]; mask=z[f]>=th if sign>0 else z[f]<=th; zz=z[mask]; out.append({'feature':f,'winner_favored':'HIGH' if sign>0 else 'LOW','dev_quantile':qv,'threshold':th,'partition':p,'n':len(zz),'tp':int((zz.reason=='TP').sum()),'sl':int((zz.reason=='SL').sum()),'wr':float((zz.reason=='TP').mean()) if len(zz) else None})
    return pd.DataFrame(out)

def main():
    x=prep(); print('H1',len(x),x.index.min(),x.index.max(),flush=True)
    allr=[]
    for p in ['development','external','reference_validation','august']:
        w=part_weeks(p,x); allr.append(build_rows(x,p,w))
    rows=pd.concat(allr,ignore_index=True); print('candidate-side rows',len(rows),flush=True)
    summaries={}
    for p in ['development','external','reference_validation','august']:
        q=rows[rows.partition==p]; summaries[p]={'n':len(q),'tp':int((q.reason=='TP').sum()),'sl':int((q.reason=='SL').sum()),'time':int((q.reason=='TIME').sum()),'decisive_wr':float((q[q.reason.isin(['TP','SL'])].reason=='TP').mean()) if len(q[q.reason.isin(['TP','SL'])]) else None}
    fs=pd.concat([feature_stats(rows,p) for p in ['development','external','reference_validation']],ignore_index=True); fs.to_csv(OUT_FEATURES,index=False)
    dev=fs[fs.partition=='development'].sort_values(['abs_smd','auc_oriented','feature'],ascending=[False,False,True]).reset_index(drop=True); top=dev.head(20).feature.tolist()
    piv=fs.pivot(index='feature',columns='partition',values='smd'); stable=[]
    for f in top:
        if f not in piv.index:continue
        dv=float(piv.loc[f,'development']); ex=float(piv.loc[f,'external']); va=float(piv.loc[f,'reference_validation'])
        if abs(dv)>=.20 and abs(ex)>=.10 and abs(va)>=.10 and np.sign(dv)==np.sign(ex)==np.sign(va): stable.append(f)
    top_rows=[]
    for f in top:
        rec={'feature':f,'stable':f in stable}
        for p in ['development','external','reference_validation']:
            rr=fs[(fs.feature==f)&(fs.partition==p)].iloc[0]; rec[f'{p}_smd']=float(rr.smd); rec[f'{p}_auc']=float(rr.auc_oriented); rec[f'{p}_winner_median']=float(rr.winner_median); rec[f'{p}_loser_median']=float(rr.loser_median)
        top_rows.append(rec)
    pd.DataFrame(top_rows).to_csv(OUT_TOP,index=False)
    clf=clf_stats(rows,top); qtab=quantiles(rows,stable,dev); qtab.to_csv(OUT_Q,index=False)
    strong=len(stable)>=3 and clf['external']['auc']>=.65 and clf['reference_validation']['auc']>=.65
    very=clf['external']['auc']>=.75 and clf['reference_validation']['auc']>=.75
    result={'experiment':'B14_WINNER_LOSER_FINGERPRINT','revision':REV,'coverage':{'first':str(x.index.min()),'last':str(x.index.max()),'h1_rows':len(x)},'summaries':summaries,'top20':top_rows,'stable_differentiators':stable,'stable_count':len(stable),'classifier':clf,'strong_evidence':strong,'very_strong':very,'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# BTC Weekly Winner-vs-Loser Fingerprint B14 — Result','',f"**Stable differentiators: {len(stable)}**",f"**Strong evidence gate: {'PASS' if strong else 'FAIL'}**",f"**Very-strong separability: {'PASS' if very else 'FAIL'}**",'',f"Coverage **{x.index.min()} -> {x.index.max()}**, H1 rows **{len(x):,}**.",'','## Candidate-side outcome base rates','', '| Partition | N | TP | SL | TIME | decisive WR |','|---|---:|---:|---:|---:|---:|']
    for p,s in summaries.items(): lines.append(f"| {p} | {s['n']} | {s['tp']} | {s['sl']} | {s['time']} | {100*s['decisive_wr']:.2f}% |")
    lines += ['','## Frozen development top-20 feature differences','','| Feature | Stable | Dev SMD | Ext SMD | Val SMD | Dev AUC* | Ext AUC* | Val AUC* |','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in top_rows: lines.append(f"| `{r['feature']}` | {'YES' if r['stable'] else 'no'} | {r['development_smd']:.3f} | {r['external_smd']:.3f} | {r['reference_validation_smd']:.3f} | {r['development_auc']:.3f} | {r['external_auc']:.3f} | {r['reference_validation_auc']:.3f} |")
    lines += ['','*AUC is orientation-free max(AUC,1-AUC).','','## Stable differentiators']+[f"- `{f}`" for f in stable]+['','## Frozen top-20 logistic separability','','| Partition | N | ROC AUC | Accuracy | Base WR |','|---|---:|---:|---:|---:|']
    for p,s in clf.items(): lines.append(f"| {p} | {s['n']} | {s['auc']:.3f} | {100*s['accuracy']:.2f}% | {100*s['base_wr']:.2f}% |")
    lines += ['','This is a fingerprint diagnostic, not yet a one-trade-per-week strategy. No OOS retuning. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines),flush=True)

if __name__=='__main__': main()
