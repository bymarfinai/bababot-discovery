#!/usr/bin/env python3
"""Saturday T-Method S5.4 — EMA Failure-State Forensic.

Research only; live BBC untouched. No management action is applied.

Purpose
-------
Mirror the *method* of Tuesday A5.4, not its thresholds. EMA is studied only
after Saturday BUY has already proven favorable impulse by causally reaching
+0.50% MFE. We ask whether 5m EMA7/EMA20 state at the +0.50 hinge, and causal
post-hinge acceptance/breakdown relative to those EMAs, separates future deep
runners (later reach +0.80 before frozen parent exit) from shallow runners
(reach +0.50 but never +0.80).

No EMA threshold sweep and no exit/protect rule. Outcome labels are forensic only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s52b_selective_runner_protect as b52

OUT=Path(os.getenv('S54_OUT','s54_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83

FEATURES=[
    'hinge_close_dist_ema7','hinge_close_dist_ema20',
    'hinge_open_dist_ema7','hinge_open_dist_ema20',
    'ema7_slope_5m','ema20_slope_5m','ema7_slope_60m','ema20_slope_60m',
    'ema7_ema20_spread','ema_spread_abs',
    'hinge_progress_close','prehinge_mae'
]
EVENTS=[
    'first_close_below_ema7_min','first_close_below_ema20_min',
    'two_close_below_ema7_min','two_close_below_ema20_min',
    'first_reclaim_above_ema7_after_break_min','first_reclaim_above_ema20_after_break_min'
]


def rank_auc(x,y):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=bool)
    m=np.isfinite(x); x=x[m]; y=y[m]
    if len(x)==0 or y.sum()==0 or (~y).sum()==0:return np.nan
    r=pd.Series(x).rank(method='average').to_numpy(); n1=y.sum(); n0=(~y).sum()
    return float((r[y].sum()-n1*(n1+1)/2)/(n1*n0))


def slope(k, t, col, mins):
    old=t-pd.Timedelta(minutes=mins)
    if old not in k.index:return np.nan
    a=float(k.loc[t,col]); b=float(k.loc[old,col])
    return a/b-1 if b else np.nan


def hinge_features(k,t,tr,h05):
    bt=h05-pd.Timedelta(minutes=5)
    b=k.loc[bt]
    prev_t=bt-pd.Timedelta(minutes=5)
    prev=k.loc[prev_t] if prev_t in k.index else None
    bars=k[(k.index>=t)&(k.index<h05)]
    ema7=float(b.ema7); ema20=float(b.ema20)
    return {
        'hinge_close_dist_ema7': float(b.close)/ema7-1,
        'hinge_close_dist_ema20': float(b.close)/ema20-1,
        'hinge_open_dist_ema7': float(b.open)/ema7-1,
        'hinge_open_dist_ema20': float(b.open)/ema20-1,
        'ema7_slope_5m': slope(k,bt,'ema7',5),
        'ema20_slope_5m': slope(k,bt,'ema20',5),
        'ema7_slope_60m': slope(k,bt,'ema7',60),
        'ema20_slope_60m': slope(k,bt,'ema20',60),
        'ema7_ema20_spread': ema7/ema20-1,
        'ema_spread_abs': abs(ema7/ema20-1),
        'hinge_progress_close': float(b.close)/tr.entry-1,
        'prehinge_mae': 1-float(bars.low.min())/tr.entry if len(bars) else np.nan,
        'hinge_above_ema7': bool(float(b.close)>ema7),
        'hinge_above_ema20': bool(float(b.close)>ema20),
        'hinge_reclaim_ema7': bool(prev is not None and float(prev.close)<=float(prev.ema7) and float(b.close)>ema7),
        'hinge_reclaim_ema20': bool(prev is not None and float(prev.close)<=float(prev.ema20) and float(b.close)>ema20),
    }


def posthinge_events(k,tr,h05,base_exit):
    bars=k[(k.index>=h05)&(k.index<base_exit)]
    below7=below20=0
    broke7=broke20=False
    out={e:np.nan for e in EVENTS}
    for b in bars.itertuples(index=False):
        d=b.ts+pd.Timedelta(minutes=5)
        c=float(b.close); e7=float(b.ema7); e20=float(b.ema20)
        if c<e7:
            below7+=1
            if not broke7:
                broke7=True
                out['first_close_below_ema7_min']=(d-h05).total_seconds()/60
            if below7>=2 and not np.isfinite(out['two_close_below_ema7_min']):
                out['two_close_below_ema7_min']=(d-h05).total_seconds()/60
        else:
            if broke7 and not np.isfinite(out['first_reclaim_above_ema7_after_break_min']):
                out['first_reclaim_above_ema7_after_break_min']=(d-h05).total_seconds()/60
            below7=0
        if c<e20:
            below20+=1
            if not broke20:
                broke20=True
                out['first_close_below_ema20_min']=(d-h05).total_seconds()/60
            if below20>=2 and not np.isfinite(out['two_close_below_ema20_min']):
                out['two_close_below_ema20_min']=(d-h05).total_seconds()/60
        else:
            if broke20 and not np.isfinite(out['first_reclaim_above_ema20_after_break_min']):
                out['first_reclaim_above_ema20_after_break_min']=(d-h05).total_seconds()/60
            below20=0
    return out


def compare(df,feat,period,mask):
    g=df[mask]; de=g[g.deep]; sh=g[~g.deep]
    md=float(de[feat].median()) if len(de) and de[feat].notna().any() else np.nan
    ms=float(sh[feat].median()) if len(sh) and sh[feat].notna().any() else np.nan
    auc=rank_auc(g[feat].to_numpy(),g.deep.to_numpy())
    direction='DEEP_HIGH' if np.isfinite(md) and np.isfinite(ms) and md>ms else ('DEEP_LOW' if np.isfinite(md) and np.isfinite(ms) and md<ms else 'TIE')
    return {'feature':feat,'period':period,'n':len(g),'deep_n':len(de),'shallow_n':len(sh),'deep_median':md,'shallow_median':ms,'auc_deep_high':auc,'direction':direction}


def event_row(df,event):
    rows=[]
    for p,mask in [('full',np.ones(len(df),dtype=bool)),('disc',df.idx<SPLIT),('val',df.idx>=SPLIT)]:
        g=df[mask]; de=g[g.deep]; sh=g[~g.deep]
        def rate(x):return float(x[event].notna().mean()) if len(x) else np.nan
        def med(x):return float(x[event].median()) if len(x) and x[event].notna().any() else np.nan
        rows.append({'event':event,'period':p,'n':len(g),'deep_n':len(de),'shallow_n':len(sh),
                     'deep_event_rate':rate(de),'shallow_event_rate':rate(sh),'deep_median_min':med(de),'shallow_median_min':med(sh)})
    return rows


def main():
    k=s50.load_klines(); k['ema7']=k['close'].ewm(span=7,adjust=False).mean(); k['ema20']=k['close'].ewm(span=20,adjust=False).mean()
    f=s50.load_funding(); entries=s50.saturday_entries(k); trades=[s50.simulate(k,f,t) for t in entries]
    rows=[]
    for i,(t,tr) in enumerate(zip(entries,trades)):
        s240=a50.state240(k,t,tr); a719=a50.a719_pnl(k,f,t,tr,s240); base_exit=b52.a719_exit_time(t,tr,s240)
        h05,h08=a52.first_hinges(k,t,tr)
        if h05 is None:continue
        r={'idx':i,'date':tr.date,'parent_pnl':float(tr.pnl),'a719_pnl':float(a719),'deep':bool(h08 is not None),'shallow':bool(h08 is None),
           'time_to05_min':(h05-t).total_seconds()/60}
        r.update(hinge_features(k,t,tr,h05)); r.update(posthinge_events(k,tr,h05,base_exit)); rows.append(r)
    df=pd.DataFrame(rows).sort_values('idx').reset_index(drop=True)
    # Frozen parity.
    if len(df)!=89 or int(df.deep.sum())!=61 or int(df.shallow.sum())!=28:raise RuntimeError('hinge/deep parity fail')
    # Parent/A7.19 parity checked over all trades separately.
    all_parent=sum(float(x.pnl) for x in trades)
    all_a719=0.0
    for t,tr in zip(entries,trades):
        s240=a50.state240(k,t,tr); all_a719+=a50.a719_pnl(k,f,t,tr,s240)
    if abs(all_parent-87.199692)>.02 or abs(all_a719-103.3830997612)>.02:raise RuntimeError('frozen control parity fail')
    df.to_csv(OUT/'s54_hinge_forensics.csv',index=False)

    comps=[]; masks={'full':np.ones(len(df),dtype=bool),'disc':df.idx<SPLIT,'val':df.idx>=SPLIT}
    for feat in FEATURES:
        for p,m in masks.items():comps.append(compare(df,feat,p,m))
    c=pd.DataFrame(comps); c.to_csv(OUT/'s54_hinge_feature_compare.csv',index=False)
    ev=[]
    for e in EVENTS:ev.extend(event_row(df,e))
    e=pd.DataFrame(ev); e.to_csv(OUT/'s54_posthinge_ema_events.csv',index=False)

    # Categorical hinge-state transfer.
    cat=[]
    for name,col in [('HINGE_ABOVE_EMA7','hinge_above_ema7'),('HINGE_ABOVE_EMA20','hinge_above_ema20'),('HINGE_RECLAIM_EMA7','hinge_reclaim_ema7'),('HINGE_RECLAIM_EMA20','hinge_reclaim_ema20')]:
        for val in [True,False]:
            m=df[col].eq(val); g=df[m]; d=g[g.idx<SPLIT]; v=g[g.idx>=SPLIT]
            rate=lambda x: float(x.deep.mean()) if len(x) else np.nan
            cat.append({'state':f'{name}={val}','n':len(g),'deep_rate':rate(g),'disc_n':len(d),'disc_deep_rate':rate(d),'val_n':len(v),'val_deep_rate':rate(v)})
    cat=pd.DataFrame(cat); cat.to_csv(OUT/'s54_hinge_states.csv',index=False)

    summary={'hinge_n':len(df),'deep_n':int(df.deep.sum()),'shallow_n':int(df.shallow.sum()),'feature_compare':comps,'events':ev,'states':cat.to_dict(orient='records')}
    (OUT/'s54_summary.json').write_text(json.dumps(summary,indent=2,default=float))

    def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.1f}%'
    lines=['# BTC Temporal Saturday T-Method S5.4 — EMA Failure-State Forensic','',
           '**Status:** COMPLETE — FORENSIC ONLY; NO EMA ACTION PROMOTED','**Research only:** live BBC untouched','',
           '## Frozen parity',f'- +0.50 hinge trades: **{len(df)}**',f'- Future deep >=+0.80: **{int(df.deep.sum())}**; shallow: **{int(df.shallow.sum())}**',
           f'- Parent all-trade PnL: **${all_parent:+.3f}**; A7.19: **${all_a719:+.3f}**','',
           '## Hinge continuous EMA features','| Feature | Full deep/shallow median | Full AUC | Discovery direction/AUC | Validation direction/AUC |','|---|---:|---:|---:|---:|']
    for feat in FEATURES:
        q=c[c.feature.eq(feat)].set_index('period'); ff=q.loc['full']; dd=q.loc['disc']; vv=q.loc['val']
        lines.append(f"| {feat} | {ff.deep_median:.6f} / {ff.shallow_median:.6f} | {ff.auc_deep_high:.3f} | {dd.direction}/{dd.auc_deep_high:.3f} | {vv.direction}/{vv.auc_deep_high:.3f} |")
    lines += ['', '## Post-hinge EMA events','| Event | Full deep/shallow rate | D deep/shallow | V deep/shallow | Full median minutes deep/shallow |','|---|---:|---:|---:|---:|']
    for evt in EVENTS:
        q=e[e.event.eq(evt)].set_index('period'); ff=q.loc['full']; dd=q.loc['disc']; vv=q.loc['val']
        lines.append(f"| {evt} | {pct(ff.deep_event_rate)} / {pct(ff.shallow_event_rate)} | {pct(dd.deep_event_rate)} / {pct(dd.shallow_event_rate)} | {pct(vv.deep_event_rate)} / {pct(vv.shallow_event_rate)} | {ff.deep_median_min:.1f} / {ff.shallow_median_min:.1f} |")
    lines += ['', '## Guardrail','- Future deep/shallow is forensic outcome only.', '- No EMA-distance threshold or exit timing was optimized.', '- S5.5 is allowed only if S5.4 finds a directionally stable EMA failure/overextension relationship in discovery and validation.']
    (OUT/'S5.4_CHECKPOINT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=float))

if __name__=='__main__':main()
