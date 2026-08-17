#!/usr/bin/env python3
"""Saturday T-Method S5.2A — Post-Failure Recovery / Shallow Runner Forensic.

Research only. No trade-management action is applied.
Frozen controls remain parent, A7.19 full coverage, and A7.26 selective benchmark.

Question: among Saturday BUY trades that causally prove some favorable impulse by
first reaching +0.50% MFE, does the path *before* that hinge identify recovery
quality? We preserve early FAILURE only as memory/context, then observe whether
the runner graduates to +0.80% or gives back.

All pre-hinge features are causal and use only completed 5m decisions available
no later than the +0.50 hinge-completion decision.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s51a_adaptive_failure_timing_atlas as a51

OUT=Path(os.getenv('S52A_OUT','s52a_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83


def met(g):
    if len(g)==0:return {'n':0,'wins':0,'wr':np.nan,'pnl':0.0,'a719_pnl':0.0,'deep_rate':np.nan,'shallow_rate':np.nan}
    return {'n':len(g),'wins':int((g.parent_pnl>0).sum()),'wr':float((g.parent_pnl>0).mean()),
            'pnl':float(g.parent_pnl.sum()),'a719_pnl':float(g.a719_pnl.sum()),
            'deep_rate':float(g.deep.mean()),'shallow_rate':float(g.shallow.mean())}

def splitrow(df,mask,label):
    g=df[mask];d=g[g.idx<SPLIT];v=g[g.idx>=SPLIT]
    r={'label':label,**met(g)}
    for p,x in [('disc',d),('val',v)]:
        m=met(x);r.update({f'{p}_{k}':z for k,z in m.items()})
    return r

def first_hinges(k,t,tr):
    ex=pd.Timestamp(tr.exit_t); bars=k[(k.index>=t)&(k.index<ex)]
    h05=h08=None
    for b in bars.itertuples(index=False):
        if h05 is None and float(b.high)/tr.entry-1>=.005:h05=b.ts+pd.Timedelta(minutes=5)
        if h08 is None and float(b.high)/tr.entry-1>=.008:h08=b.ts+pd.Timedelta(minutes=5)
    return h05,h08

def decision(k,t,tr,d):
    if d not in k.index or d<=t:return None
    bars=k[(k.index>=t)&(k.index<d)]
    mins=int((d-t).total_seconds()/60)
    if len(bars)!=mins//5:return None
    op=float(k.loc[d,'open']); prog=op/tr.entry-1; tak=float(np.nanmean(bars.taker_imb.to_numpy()))
    mfe=float(bars.high.max())/tr.entry-1; mae=1-float(bars.low.min())/tr.entry
    done=k.loc[d-pd.Timedelta(minutes=5)]; ema=float(done.ema20)
    oldt=d-pd.Timedelta(minutes=65); old=k.loc[oldt] if oldt in k.index else None
    slope=ema/float(old.ema20)-1 if old is not None else np.nan
    return {'progress':prog,'taker':tak,'mfe':mfe,'mae':mae,'ema_dist':op/ema-1,'ema_slope60':slope,
            'failure':bool(prog<=-.001 and tak<0),
            'ema_reclaim':bool(op>ema and np.isfinite(slope) and slope>0)}

def prehinge_memory(k,t,tr,h05):
    # Decisions from +15m through hinge completion inclusive. The hinge itself is
    # known only at h05, so using h05 decision state is causal for any later action.
    if h05 is None:return {}
    states=[]
    for d in pd.date_range(t+pd.Timedelta(minutes=15),h05,freq='5min',tz='UTC'):
        if pd.Timestamp(tr.exit_t)<=d:break
        st=decision(k,t,tr,d)
        if st is not None:states.append((d,st))
    fail=[(d,s) for d,s in states if s['failure']]
    prior_fail=bool(fail)
    # consecutive failure persistence before/at hinge
    cur=best=0
    for _,s in states:
        if s['failure']:cur+=5;best=max(best,cur)
        else:cur=0
    reclaim_after_fail=False
    first_fail_min=np.nan
    last_fail_min=np.nan
    if fail:
        firstd=fail[0][0];lastd=fail[-1][0]
        first_fail_min=(firstd-t).total_seconds()/60;last_fail_min=(lastd-t).total_seconds()/60
        reclaim_after_fail=any(d>firstd and s['ema_reclaim'] for d,s in states)
    hs=decision(k,t,tr,h05)
    return {'prior_failure':prior_fail,'prehinge_fail_persist_max':best,
            'first_fail_before05_min':first_fail_min,'last_fail_before05_min':last_fail_min,
            'ema_reclaim_after_failure_before05':reclaim_after_fail,
            'hinge_progress':hs['progress'] if hs else np.nan,'hinge_taker':hs['taker'] if hs else np.nan,
            'hinge_mae':hs['mae'] if hs else np.nan,'hinge_ema_dist':hs['ema_dist'] if hs else np.nan,
            'hinge_ema_slope60':hs['ema_slope60'] if hs else np.nan}

def posthinge(k,t,tr,h05,h08):
    ex=pd.Timestamp(tr.exit_t)
    if h05 is None:return {}
    after=k[(k.index>=h05)&(k.index<ex)]
    gb40=gb30=None
    for b in after.itertuples(index=False):
        close=float(b.close)/tr.entry-1
        if gb40 is None and close<=.004:gb40=b.ts+pd.Timedelta(minutes=5)
        if gb30 is None and close<=.003:gb30=b.ts+pd.Timedelta(minutes=5)
        if gb40 is not None and gb30 is not None:break
    def dt(x):return np.nan if x is None else (x-h05).total_seconds()/60
    to08=np.nan if h08 is None else (h08-h05).total_seconds()/60
    if h08 is not None and (gb40 is None or h08<=gb40):path='GRADUATE_FIRST'
    elif gb40 is not None and dt(gb40)<=5:path='FAST_GIVEBACK'
    else:path='PULLBACK_BEFORE_GRADUATE'
    return {'min_05_to_08':to08,'min_05_to_gb40':dt(gb40),'min_05_to_gb30':dt(gb30),'post05_path':path}

def timebin(x):
    if not np.isfinite(x):return 'NO_HINGE'
    if x<=60:return '<=60m'
    if x<=120:return '65-120m'
    if x<=240:return '125-240m'
    return '>240m'

def med(g,col):return float(g[col].median()) if len(g) and g[col].notna().any() else np.nan

def feature_compare(df):
    rows=[]
    for cohort,mask in [('ALL_HINGE',df.hinge05),('PRIOR_FAILURE',df.hinge05&df.prior_failure),('CLEAN',df.hinge05&~df.prior_failure)]:
        g=df[mask]
        for period,pg in [('full',g),('disc',g[g.idx<SPLIT]),('val',g[g.idx>=SPLIT])]:
            de=pg[pg.deep];sh=pg[pg.shallow]
            rows.append({'cohort':cohort,'period':period,'n_deep':len(de),'n_shallow':len(sh),
                'deep_t05_med':med(de,'time_to05_min'),'shallow_t05_med':med(sh,'time_to05_min'),
                'deep_prior_fail_rate':float(de.prior_failure.mean()) if len(de) else np.nan,
                'shallow_prior_fail_rate':float(sh.prior_failure.mean()) if len(sh) else np.nan,
                'deep_persist_med':med(de,'prehinge_fail_persist_max'),'shallow_persist_med':med(sh,'prehinge_fail_persist_max'),
                'deep_hinge_taker_med':med(de,'hinge_taker'),'shallow_hinge_taker_med':med(sh,'hinge_taker'),
                'deep_hinge_mae_med':med(de,'hinge_mae'),'shallow_hinge_mae_med':med(sh,'hinge_mae'),
                'deep_ema_dist_med':med(de,'hinge_ema_dist'),'shallow_ema_dist_med':med(sh,'hinge_ema_dist')})
    return rows

def main():
    k=s50.load_klines();f=s50.load_funding();ents=s50.saturday_entries(k);trs=[s50.simulate(k,f,t) for t in ents]
    rec=[]
    for i,(t,tr) in enumerate(zip(ents,trs)):
        pre=a50.pre_context(k,t);s240=a50.state240(k,t,tr);a719=a50.a719_pnl(k,f,t,tr,s240)
        h05,h08=first_hinges(k,t,tr)
        r={'idx':i,'date':tr.date,'pre_state':pre['pre_state'],'pre_score':pre['pre_stretch_score'],
           'parent_pnl':float(tr.pnl),'a719_pnl':float(a719),'hinge05':h05 is not None,'deep':h08 is not None,
           'shallow':h05 is not None and h08 is None,
           'time_to05_min':np.nan if h05 is None else (h05-t).total_seconds()/60,
           'time_to08_min':np.nan if h08 is None else (h08-t).total_seconds()/60}
        if h05 is not None:
            r.update(prehinge_memory(k,t,tr,h05));r.update(posthinge(k,t,tr,h05,h08))
        else:
            r.update({'prior_failure':False,'prehinge_fail_persist_max':0,'first_fail_before05_min':np.nan,'last_fail_before05_min':np.nan,
                      'ema_reclaim_after_failure_before05':False,'hinge_progress':np.nan,'hinge_taker':np.nan,'hinge_mae':np.nan,
                      'hinge_ema_dist':np.nan,'hinge_ema_slope60':np.nan,'min_05_to_08':np.nan,'min_05_to_gb40':np.nan,
                      'min_05_to_gb30':np.nan,'post05_path':'NO_HINGE'})
        rec.append(r)
    df=pd.DataFrame(rec)
    # Hard parity gates.
    if len(df)!=139 or int((df.parent_pnl>0).sum())!=65 or abs(df.parent_pnl.sum()-87.20)>.20:raise RuntimeError('parent parity fail')
    if abs(df.a719_pnl.sum()-103.3830997612)>.01:raise RuntimeError('A7.19 parity fail')
    if int(df.hinge05.sum())!=89 or int(df.deep.sum())!=61 or int(df.shallow.sum())!=28:raise RuntimeError('hinge parity fail')
    df['time05_bin']=df.time_to05_min.apply(timebin)
    df['recovery_memory']=np.where(~df.hinge05,'NO_HINGE',np.where(~df.prior_failure,'CLEAN',np.where(df.ema_reclaim_after_failure_before05,'FAIL_THEN_RECLAIM','FAIL_NO_RECLAIM')))
    df.to_csv(OUT/'s52a_trade_forensics.csv',index=False)
    tables={}
    tables['hinge']=[splitrow(df,df.hinge05,'REACHED_0.5'),splitrow(df,~df.hinge05,'NO_0.5')]
    tables['memory']=[]
    for st in ['CLEAN','FAIL_THEN_RECLAIM','FAIL_NO_RECLAIM']:
        tables['memory'].append(splitrow(df,df.recovery_memory.eq(st),st))
    tables['time05']=[]
    for st in ['<=60m','65-120m','125-240m','>240m']:
        tables['time05'].append(splitrow(df,df.hinge05&df.time05_bin.eq(st),st))
    tables['post05']=[]
    for st in ['GRADUATE_FIRST','FAST_GIVEBACK','PULLBACK_BEFORE_GRADUATE']:
        tables['post05'].append(splitrow(df,df.hinge05&df.post05_path.eq(st),st))
    tables['memory_x_runner']=[]
    for mem in ['CLEAN','FAIL_THEN_RECLAIM','FAIL_NO_RECLAIM']:
        for run in ['DEEP','SHALLOW']:
            m=df.recovery_memory.eq(mem)&(df.deep if run=='DEEP' else df.shallow)
            tables['memory_x_runner'].append(splitrow(df,m,f'{mem}+{run}'))
    # Prior failure persistence before +0.5, descriptive predeclared views.
    tables['prior_failure_persist']=[]
    for pm in [5,10,15,20,30]:
        m=df.hinge05&df.prior_failure&(df.prehinge_fail_persist_max>=pm)
        tables['prior_failure_persist'].append(splitrow(df,m,f'PRIOR_FAIL_PERSIST>={pm}M'))
    fc=feature_compare(df)
    pd.DataFrame(fc).to_csv(OUT/'s52a_feature_compare.csv',index=False)
    summary={'n':len(df),'parent_pnl':float(df.parent_pnl.sum()),'a719_pnl':float(df.a719_pnl.sum()),
             'hinge05_n':int(df.hinge05.sum()),'deep_n':int(df.deep.sum()),'shallow_n':int(df.shallow.sum()),
             'tables':tables,'feature_compare':fc}
    (OUT/'s52a_summary.json').write_text(json.dumps(summary,indent=2,default=float))
    def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.2f}%'
    def money(x):return f'${x:+.3f}'
    def tab(rows):
        z=['| State | N | WR | Parent PnL | A7.19 PnL | Deep | Discovery N/Deep | Validation N/Deep |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for r in rows:z.append(f"| {r['label']} | {r['n']} | {pct(r['wr'])} | {money(r['pnl'])} | {money(r['a719_pnl'])} | {pct(r['deep_rate'])} | {r['disc_n']} / {pct(r['disc_deep_rate'])} | {r['val_n']} / {pct(r['val_deep_rate'])} |")
        return '\n'.join(z)
    md=['# BTC Temporal Saturday T-Method S5.2A — Post-Failure Recovery / Shallow Runner Forensic','',
        '**Status:** COMPLETE — FORENSIC ONLY; NO MANAGEMENT ACTION PROMOTED','**Research only:** live BBC untouched','',
        '## Frozen parity',f"- Parent: 139 trades / {money(df.parent_pnl.sum())}",f"- A7.19: {money(df.a719_pnl.sum())}",
        f"- +0.5 hinge: {int(df.hinge05.sum())}; deep >=+0.8: {int(df.deep.sum())}; shallow +0.5..<+0.8: {int(df.shallow.sum())}",'',
        '## 1. Hinge split',tab(tables['hinge']),'','## 2. Pre-hinge recovery memory',tab(tables['memory']),'',
        '## 3. Time to +0.5',tab(tables['time05']),'','## 4. Post-+0.5 path',tab(tables['post05']),'',
        '## 5. Recovery memory x runner maturity',tab(tables['memory_x_runner']),'','## 6. Prior-failure persistence before +0.5',tab(tables['prior_failure_persist']),'',
        '## 7. Deep vs shallow causal hinge features','']
    for r in fc:
        if r['period']=='full':
            md.append(f"- {r['cohort']}: deep/shallow N {r['n_deep']}/{r['n_shallow']}; time-to-0.5 median {r['deep_t05_med']:.1f}/{r['shallow_t05_med']:.1f}m; prior-failure rate {pct(r['deep_prior_fail_rate'])}/{pct(r['shallow_prior_fail_rate'])}; prehinge failure persistence median {r['deep_persist_med']:.1f}/{r['shallow_persist_med']:.1f}m; hinge taker median {r['deep_hinge_taker_med']:+.4f}/{r['shallow_hinge_taker_med']:+.4f}.")
    md += ['', '## Interpretation',
           '- Early FAILURE is retained only as path memory; S5.1/S5.1B already rejected it as a direct exit trigger.',
           '- S5.2A asks whether prior weakness + recovery quality changes the probability of graduating from +0.5 to +0.8.',
           '- Future labels DEEP/SHALLOW are forensic outcomes only. Any S5.2B action must be triggered by information known causally after the +0.5 hinge, such as giveback/confirmation behavior.',
           '- No threshold or action is selected in this milestone.']
    (OUT/'S5.2A_CHECKPOINT.md').write_text('\n'.join(md))
    print('S52A',json.dumps({'hinge05':int(df.hinge05.sum()),'deep':int(df.deep.sum()),'shallow':int(df.shallow.sum()),'memory_counts':df[df.hinge05].recovery_memory.value_counts().to_dict()},default=float))

if __name__=='__main__':main()
