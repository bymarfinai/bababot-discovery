#!/usr/bin/env python3
"""SR83: BTC all-day support/resistance confidence, annual expanding pseudo-OOS.

Research-only. Target is first-touch level HOLD reliability, not trading PnL.
Protocol frozen in BTC_SR83_AllDay_Level_Confidence_Preregistration.md.
"""
from __future__ import annotations
import csv, io, json, math, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from sklearn.tree import DecisionTreeClassifier

import btc_friday_sr80_level_reliability as sr
import btc_friday_sr81_prior_proof_level as sr81

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_SR83_AllDay_Level_Confidence_Result.md'
OUT_JSON=ROOT/'BTC_SR83_AllDay_Level_Confidence_Result.json'
OUT_ROWS=ROOT/'BTC_SR83_AllDay_Level_Confidence_Rows.csv'
OUT_OOS=ROOT/'BTC_SR83_AllDay_Level_Confidence_OOS.csv'
BASE='https://data.binance.vision/data/futures/um'
LOAD_START=pd.Timestamp('2019-12-01T00:00:00Z');LOAD_END=pd.Timestamp('2026-08-01T00:00:00Z')
DAY_START='2020-01-01';DAY_END='2026-07-29'
FEATURES=['is_support','has_pday','has_w7','has_swing','confluence_count','distance_open_atr','prior_near_count_7d','age_hours',
          'approach_ret30_toward','approach_ret60_toward','approach_ret120_toward','approach_range30_atr','approach_range60_atr',
          'approach_toward_fraction6','approach_toward_fraction12','volume30_rel24','ema20_slope3h_aligned','ema20_slope6h_aligned','atr_pct','hours_to_touch']
FOLDS=[((2020,2022),2023),((2020,2023),2024),((2020,2024),2025),((2020,2025),2026)]

def fetch_month(ym):
    url=f'{BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{ym}.zip';r=requests.get(url,timeout=90,headers={'User-Agent':'bababot-sr83/1.0'})
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<8:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5]),float(row[7])])
                except Exception:continue
    return out

def load():
    cur=pd.Timestamp(LOAD_START.year,LOAD_START.month,1,tz='UTC');last=pd.Timestamp(2026,7,1,tz='UTC');months=[]
    while cur<=last:months.append(cur.strftime('%Y-%m'));cur+=pd.offsets.MonthBegin(1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(fetch_month,m) for m in months]
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','volume','quote_volume'])
    if x.empty:raise RuntimeError('no Data Vision data')
    x.ts=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True);x=x.dropna().drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=LOAD_START)&(x.ts<LOAD_END)].copy();x=x.set_index('ts',drop=False)
    if len(x)<650000:raise RuntimeError(f'insufficient 5m rows {len(x)}')
    return x

def day_freezes():
    ds=pd.date_range(DAY_START,DAY_END,freq='D')
    return [pd.Timestamp(d.date()).tz_localize('Asia/Jakarta').tz_convert('UTC') for d in ds]

def approach(k,h,touch,side,atr):
    pre24=k[k.index<touch].tail(24);pre12=pre24.tail(12);pre6=pre24.tail(6)
    if len(pre24)<24:return {f:np.nan for f in FEATURES if f.startswith('approach_') or f.startswith('ema20_') or f=='volume30_rel24'}
    sign=-1.0 if side=='SUPPORT' else 1.0
    ret=lambda z:float(z.iloc[-1].close/z.iloc[0].open-1.0)
    bret=lambda z:z.close.to_numpy(float)/z.open.to_numpy(float)-1.0
    hc=sr.completed_h1_before(h,touch)
    s3=float(hc.iloc[-1].ema20/hc.iloc[-4].ema20-1.0) if len(hc)>=4 else np.nan
    s6=float(hc.iloc[-1].ema20/hc.iloc[-7].ema20-1.0) if len(hc)>=7 else np.nan
    return {'approach_ret30_toward':sign*ret(pre6),'approach_ret60_toward':sign*ret(pre12),'approach_ret120_toward':sign*ret(pre24),
            'approach_range30_atr':float(pre6.high.max()-pre6.low.min())/atr,'approach_range60_atr':float(pre12.high.max()-pre12.low.min())/atr,
            'approach_toward_fraction6':float(np.mean(sign*bret(pre6)>0)),'approach_toward_fraction12':float(np.mean(sign*bret(pre12)>0)),
            'volume30_rel24':sr.volume_rel24(k,touch),'ema20_slope3h_aligned':s3 if side=='SUPPORT' else -s3,
            'ema20_slope6h_aligned':s6 if side=='SUPPORT' else -s6}

def build_events(k,h):
    rows=[];viol=0
    for n,fs in enumerate(day_freezes()):
        if fs not in k.index:continue
        hc=sr.completed_h1_before(h,fs)
        if hc.empty or not np.isfinite(hc.iloc[-1].atr14):continue
        atr=float(hc.iloc[-1].atr14);dopen=float(k.loc[fs].open);de=fs+pd.Timedelta(days=1)
        levels=sr.cluster_levels(sr.raw_levels(k,h,fs),atr);day=k[(k.index>=fs)&(k.index<de)]
        priorh=h[(h.index>=fs-pd.Timedelta(days=7))&(h.index<fs)]
        for ci,c in enumerate(levels):
            level=float(c['level'])
            if level==dopen:continue
            side='SUPPORT' if level<dopen else 'RESISTANCE'
            mask=(day.low.to_numpy(float)<=level)&(day.high.to_numpy(float)>=level);hits=np.flatnonzero(mask)
            if len(hits)==0:continue
            touch=day.index[int(hits[0])];tol=.10*atr
            near=int(((priorh.low.to_numpy(float)<=level+tol)&(priorh.high.to_numpy(float)>=level-tol)).sum()) if len(priorh) else 0
            youngest=max(pd.Timestamp(o) for o in c['origins']);age=(fs-youngest).total_seconds()/3600
            if youngest>=fs:viol+=1
            af=approach(k,h,touch,side,atr);out=sr81.resolve_fast(k,touch,level,side,atr)
            local=fs.tz_convert('Asia/Jakarta')
            rows.append({'day_wib':str(local.date()),'year':int(local.year),'freeze_utc':str(fs),'touch_utc':str(touch),'cluster_id':f'{local.date()}-{ci}',
                         'level':level,'side':side,'sources':'|'.join(c['sources']),'families':'|'.join(c['families']),
                         'is_support':int(side=='SUPPORT'),'has_pday':int('PDAY' in c['families']),'has_w7':int('W7' in c['families']),'has_swing':int('SWING' in c['families']),
                         'confluence_count':int(c['confluence_count']),'distance_open_atr':abs(level-dopen)/atr,'prior_near_count_7d':near,'age_hours':age,
                         'atr_pct':atr/dopen,'hours_to_touch':(touch-fs).total_seconds()/3600,**af,'outcome':out['outcome']})
    return pd.DataFrame(rows),viol

def wilson(w,n):
    if n<=0:return [None,None]
    p=w/n;z=1.959963984540054;den=1+z*z/n;c=(p+z*z/(2*n))/den;hh=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0.,c-hh),min(1.,c+hh)]
def stats(z):
    if len(z)==0:return {'n':0,'hold':0,'break':0,'rate':None,'wilson95':[None,None]}
    w=int((z.outcome=='HOLD').sum());n=len(z);return {'n':n,'hold':w,'break':n-w,'rate':w/n,'wilson95':wilson(w,n)}
def path(clf,leaf):
    tr=clf.tree_;ans=[]
    def rec(node,c):
        if node==leaf:ans.extend(c);return True
        if tr.children_left[node]==tr.children_right[node]:return False
        f=FEATURES[tr.feature[node]];th=float(tr.threshold[node])
        return rec(tr.children_left[node],c+[[f,'<=',th]]) or rec(tr.children_right[node],c+[[f,'>',th]])
    rec(0,[]);return ans
def rule(p):return ' AND '.join(f'{f} {op} {v:.7g}' for f,op,v in p)

def main():
    k=load();h=sr.build_h1(k);events,viol=build_events(k,h)
    if events.empty:raise RuntimeError('no SR83 events')
    events.to_csv(OUT_ROWS,index=False);res=events[events.outcome.isin(['HOLD','BREAK'])].copy()
    if len(res)<1000:raise RuntimeError(f'too few resolved {len(res)}')
    foldout=[];fold_reports=[]
    for (lo,hi),ty in FOLDS:
        train=res[(res.year>=lo)&(res.year<=hi)].copy();test=res[res.year==ty].copy()
        if len(train)<300 or len(test)<50:raise RuntimeError(f'insufficient fold {lo}-{hi}->{ty}: {len(train)}/{len(test)}')
        med={f:float(pd.to_numeric(train[f],errors='coerce').replace([np.inf,-np.inf],np.nan).median()) for f in FEATURES}
        def matrix(z):
            X=z[FEATURES].copy()
            for f in FEATURES:X[f]=pd.to_numeric(X[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med[f])
            return X
        Xt=matrix(train);Xv=matrix(test);yt=(train.outcome=='HOLD').astype(int)
        clf=DecisionTreeClassifier(criterion='gini',max_depth=4,min_samples_leaf=50,random_state=20260819);clf.fit(Xt,yt)
        trleaf=clf.apply(Xt);teleaf=clf.apply(Xv);train=train.copy();test=test.copy();train['leaf']=trleaf;test['leaf']=teleaf
        elig=[]
        for lf in sorted(set(trleaf)):
            q=train[train.leaf==lf];s=stats(q);node=int(lf);cls=int(clf.classes_[int(np.argmax(clf.tree_.value[node][0]))])
            if cls==1 and s['n']>=50 and s['rate'] is not None and s['rate']>=.80:elig.append(int(lf))
        rules=[{'leaf':lf,'train':stats(train[train.leaf==lf]),'rule':rule(path(clf,lf))} for lf in elig]
        test['high_confidence']=test.leaf.isin(set(elig));hc=test[test.high_confidence].copy();hc['test_year']=ty;foldout.append(hc)
        fold_reports.append({'train_years':f'{lo}-{hi}','test_year':ty,'train_n':len(train),'test_n':len(test),'eligible_leaves':rules,
                             'eligible_leaf_count':len(elig),'unconditional':stats(test),'high_confidence':stats(hc),'coverage':len(hc)/len(test)})
    oos=pd.concat(foldout,ignore_index=True) if foldout else pd.DataFrame(columns=res.columns.tolist()+['high_confidence','test_year'])
    oos.to_csv(OUT_OOS,index=False);high=stats(oos);testyears=set(y for _,y in FOLDS);alltest=res[res.year.isin(testyears)];base=stats(alltest)
    folds_n15=sum(r['high_confidence']['n']>=15 for r in fold_reports)
    lowfold_ok=all(r['high_confidence']['rate'] is None or r['high_confidence']['n']<15 or r['high_confidence']['rate']>=.65 for r in fold_reports)
    improve=sum(r['high_confidence']['n']>0 and r['high_confidence']['rate']>r['unconditional']['rate'] for r in fold_reports)
    lift=(high['rate']-base['rate']) if high['rate'] is not None and base['rate'] is not None else None
    ok=bool(high['n']>=100 and high['rate'] is not None and high['rate']>=.80 and lift is not None and lift>=.10 and folds_n15>=3 and lowfold_ok and improve>=3 and viol==0)
    sides={s:stats(oos[oos.side==s]) for s in ['SUPPORT','RESISTANCE']} if len(oos) else {}
    fam={f:stats(oos[oos.families.astype(str).str.contains(f,regex=False)]) for f in ['PDAY','W7','SWING']} if len(oos) else {}
    counts=events.outcome.value_counts().to_dict()
    out={'protocol':'SR83','status':'COMPLETE','touch_events':len(events),'resolved_events':len(res),'outcome_counts':{str(k):int(v) for k,v in counts.items()},
         'integrity_violations':viol,'pseudo_oos_unconditional':base,'pseudo_oos_high_confidence':high,'lift_pp':None if lift is None else 100*lift,
         'pseudo_oos_coverage':len(oos)/len(alltest) if len(alltest) else 0,'folds':fold_reports,'folds_with_n15':folds_n15,'folds_improving_on_baseline':improve,
         'support_resistance_descriptive':sides,'source_family_descriptive':fam,
         'verdict':'BTC_SR83_OOS_80_LEVEL_IDENTIFIER' if ok else 'REJECT_SR83_OOS_80_LEVEL_IDENTIFIER',
         'guardrail':'No post-result tree/leaf/feature/side/source/year threshold rescue.'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    pct=lambda x:'-' if x is None else f'{100*x:.2f}%';ci=lambda q:'-' if q[0] is None else f'{100*q[0]:.1f}%–{100*q[1]:.1f}%'
    md=['# BTC SR83 — All-Day Level Confidence Walk-Forward Result','',f"**Verdict: {out['verdict']}**",'',
        f"All first-touch events: **{len(events)}**; resolved: **{len(res)}**; integrity violations: **{viol}**",f"Outcome counts: `{out['outcome_counts']}`",'',
        '## Pseudo-OOS headline','','| Cohort | N | HOLD | BREAK | HOLD rate | Wilson 95% |','|---|---:|---:|---:|---:|---:|',
        f"| Unconditional test years | {base['n']} | {base['hold']} | {base['break']} | {pct(base['rate'])} | {ci(base['wilson95'])} |",
        f"| HIGH_CONFIDENCE_HOLD | {high['n']} | {high['hold']} | {high['break']} | **{pct(high['rate'])}** | {ci(high['wilson95'])} |",
        f"\nCoverage: **{100*out['pseudo_oos_coverage']:.2f}%**; lift vs baseline: **{out['lift_pp'] if out['lift_pp'] is not None else float('nan'):+.2f}pp**.",'',
        '## Annual expanding folds','','| Train | Test | Test N | Eligible leaves | HC N | HC HOLD rate | Baseline | Coverage |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in fold_reports:md.append(f"| {r['train_years']} | {r['test_year']} | {r['test_n']} | {r['eligible_leaf_count']} | {r['high_confidence']['n']} | {pct(r['high_confidence']['rate'])} | {pct(r['unconditional']['rate'])} | {100*r['coverage']:.2f}% |")
    md += ['','## Frozen eligible leaf rules by fold']
    for r in fold_reports:
        md.append(f"\n### Test {r['test_year']}")
        if not r['eligible_leaves']:md.append('- none')
        else:
            for z in r['eligible_leaves']:md.append(f"- leaf {z['leaf']}: train N {z['train']['n']}, HOLD {pct(z['train']['rate'])}: `{z['rule']}`")
    md += ['','Historical pseudo-OOS HOLD reliability is not a guarantee of future support/resistance behavior and is not trade PnL.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__':main()
