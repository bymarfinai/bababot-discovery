#!/usr/bin/env python3
"""F6.11 — Friday15 causal Fibonacci forensic.

Research only; live BBC untouched.

Question: is the Friday early-sink / failed-acceptance state related to where the
entry sits inside a *pre-entry* swing range and standard Fibonacci retracement
levels?

Guardrails:
- only completed 5m bars strictly before entry define the swing;
- no post-entry swing endpoints are used;
- no Fib threshold is optimized or promoted here;
- report natural horizons and standard Fib levels only.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f69_friday_early_sink_candidate_robustness as f69

OUT=Path(os.getenv('F611_OUT','f611_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N
HORIZONS=[60,120,240,480,1440]
FIBS=np.array([0.236,0.382,0.500,0.618,0.786],dtype=float)


def auc(y, score):
    y=np.asarray(y,dtype=bool); s=np.asarray(score,dtype=float)
    ok=np.isfinite(s); y=y[ok]; s=s[ok]
    p=s[y]; n=s[~y]
    if len(p)==0 or len(n)==0: return np.nan
    # Mann-Whitney AUC with ties=0.5
    wins=0.0
    for x in p:
        wins += np.sum(x>n) + 0.5*np.sum(x==n)
    return float(wins/(len(p)*len(n)))


def fib_features(k,t,entry,hmin):
    pre=k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=hmin))]
    if len(pre)<2: return None
    hi=float(pre.high.max()); lo=float(pre.low.min()); rg=hi-lo
    if rg<=0: return None
    thi=pre.high.idxmax(); tlo=pre.low.idxmin()
    # range position: 0=at low, 1=at high
    pos=(entry-lo)/rg
    # conventional retracement depth from the high of a low->high bullish swing
    retr=(hi-entry)/rg
    bullish=bool(tlo<thi)
    bearish=bool(thi<tlo)
    dists=np.abs(FIBS-retr)
    j=int(np.argmin(dists))
    return {
        'hi':hi,'lo':lo,'range_pct':100*rg/entry,
        'range_pos':float(pos),'retr_depth':float(retr),
        'bullish_swing':bullish,'bearish_swing':bearish,
        'nearest_fib':float(FIBS[j]),'nearest_fib_dist':float(dists[j]),
        'dist_382':float(abs(retr-0.382)),'dist_500':float(abs(retr-0.5)),
        'dist_618':float(abs(retr-0.618)),'dist_786':float(abs(retr-0.786)),
    }


def fmt(x):
    return None if x is None or not np.isfinite(x) else float(x)


def group_summary(df,label):
    z=df[df[label]]
    out={'n':int(len(z))}
    for h in HORIZONS:
        for c in ['retr_depth','range_pos','nearest_fib_dist','dist_382','dist_500','dist_618','dist_786']:
            col=f'h{h}_{c}'
            out[f'{col}_median']=fmt(z[col].median())
        out[f'h{h}_bullish_swing_rate']=fmt(z[f'h{h}_bullish_swing'].mean())
        out[f'h{h}_nearest_fib_counts']={str(k):int(v) for k,v in z[f'h{h}_nearest_fib'].value_counts(dropna=True).sort_index().items()}
    return out


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        bars=k[(k.index>=t)&(k.index<tr.exit_t)]
        first=bars.iloc[0]
        rest=bars.iloc[1:]
        first5_red=bool(float(first.close)<tr.entry)
        strict_sink=bool(first5_red and (rest.empty or float(rest.high.max())<tr.entry-1e-12))
        early10=f69.early_state(k,t,tr)
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'entry':float(tr.entry),'parent_win':bool(tr.pnl>0),'parent_pnl':float(tr.pnl),
             'first5_red':first5_red,'strict_sink':strict_sink,'early10':early10}
        for h in HORIZONS:
            f=fib_features(k,t,float(tr.entry),h)
            if f is None:
                for c in ['range_pct','range_pos','retr_depth','bullish_swing','bearish_swing','nearest_fib','nearest_fib_dist','dist_382','dist_500','dist_618','dist_786']:
                    row[f'h{h}_{c}']=np.nan
            else:
                for c,v in f.items():
                    if c in ['hi','lo']: continue
                    row[f'h{h}_{c}']=v
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f611_rows.csv',index=False)

    # Main comparison cohorts.
    labels=['early10','strict_sink','first5_red']
    summary={'base':{'n':int(len(df)),'early10':int(df.early10.sum()),'strict_sink':int(df.strict_sink.sum()),'first5_red':int(df.first5_red.sum())}}
    for lab in labels:
        summary[lab]=group_summary(df,lab)

    # Red-recover cohort = first5 red but not strict sink, to answer sink vs recover directly.
    df['red_recover']=df.first5_red & ~df.strict_sink
    summary['red_recover']=group_summary(df,'red_recover')

    # AUC atlas. Positive target = strict sink and separately EARLY10 action.
    atlas=[]
    for target in ['strict_sink','early10']:
        for h in HORIZONS:
            for feature in ['retr_depth','range_pos','nearest_fib_dist','dist_382','dist_500','dist_618','dist_786','range_pct']:
                col=f'h{h}_{feature}'
                vals=[]
                for name,g in [('full',df),('discovery',df[df.i<SPLIT]),('validation',df[df.i>=SPLIT])]:
                    vals.append((name,auc(g[target],g[col])))
                atlas.append({'target':target,'horizon_min':h,'feature':feature,
                              **{f'auc_{n}':fmt(v) for n,v in vals}})
    adf=pd.DataFrame(atlas)
    adf.to_csv(OUT/'f611_auc_atlas.csv',index=False)

    # Natural Fib-zone distributions among bullish pre-entry swings only.
    fibdist=[]
    for h in HORIZONS:
        g=df[df[f'h{h}_bullish_swing']==True]
        for cohort,mask in [('early10',g.early10),('strict_sink',g.strict_sink),('red_recover',g.red_recover),('all',pd.Series(True,index=g.index))]:
            z=g[mask]
            vc=z[f'h{h}_nearest_fib'].value_counts(dropna=True)
            for fib in FIBS:
                fibdist.append({'horizon_min':h,'cohort':cohort,'fib':float(fib),'n':int(len(z)),
                                'count':int(vc.get(float(fib),0)),
                                'share':float(vc.get(float(fib),0)/len(z)) if len(z) else np.nan})
    pd.DataFrame(fibdist).to_csv(OUT/'f611_fib_distribution.csv',index=False)

    # Stable-looking associations are descriptive only: require same direction full/D/V.
    stable=[]
    for _,r in adf.iterrows():
        a=[r.auc_full,r.auc_discovery,r.auc_validation]
        if all(np.isfinite(x) for x in a):
            hi=all(x>=0.60 for x in a); lo=all(x<=0.40 for x in a)
            if hi or lo:
                stable.append(r.to_dict())
    sdf=pd.DataFrame(stable)
    sdf.to_csv(OUT/'f611_stable_associations.csv',index=False)

    out={'status':'DESCRIPTIVE_CAUSAL_FIB_FORENSIC__NO_RULE_PROMOTED',
         'summary':summary,
         'stable_associations':stable,
         'top_by_full_auc':adf.assign(edge=(adf.auc_full-0.5).abs()).sort_values('edge',ascending=False).head(15).drop(columns='edge').to_dict('records')}
    (OUT/'f611_summary.json').write_text(json.dumps(out,indent=2,default=float))

    md=['# Friday15 F6.11 — Causal Fibonacci Forensic','',
        '**Status:** COMPLETE — DESCRIPTIVE; NO FIB RULE PROMOTED','**Live BBC untouched.**','',
        '## Method','All Fib anchors use only completed 5m bars strictly before Friday 15:00 WIB entry. Horizons: 1h,2h,4h,8h,24h. Standard levels: 23.6/38.2/50/61.8/78.6.','',
        '## Cohorts',f"- All Friday trades: {len(df)}",f"- F6.9 EARLY10 actions: {int(df.early10.sum())}",f"- strict immediate sinks: {int(df.strict_sink.sum())}",f"- first5-red recover/non-strict-sink: {int(df.red_recover.sum())}",'',
        '## Stable associations (same AUC direction Full / Discovery / Validation)']
    if stable:
        for r in stable:
            md.append(f"- {r['target']} | {int(r['horizon_min'])}m | {r['feature']}: AUC {r['auc_full']:.3f} / {r['auc_discovery']:.3f} / {r['auc_validation']:.3f}")
    else:
        md.append('- None at the predeclared >=0.60 or <=0.40 AUC stability screen.')
    md += ['', '## Guardrail','A Fib relationship here is explanatory only. Do not add a Fib gate to F6.9 from this same sample. If a clean mechanism appears, freeze it first and validate separately.']
    (OUT/'F6.11_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
