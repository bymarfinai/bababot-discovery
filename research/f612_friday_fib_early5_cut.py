#!/usr/bin/env python3
"""F6.12 — Friday15 causal Fibonacci-context +5m cut test.

Research only; live BBC untouched.

Frozen, predeclared rule (no threshold sweep):
At +5m, exit BUY at the actual +5m open iff:
1) first completed 5m candle closed below entry;
2) position is still alive at +5m;
3) pre-entry 2h retracement depth from the 2h high is <= 38.2%;
4) the pre-entry 2h range is larger than its causal rolling 24h median baseline.

The 38.2% level is a standard Fib level carried from F6.11, not optimized here.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f611_friday_fibonacci_forensic as f611

OUT=Path(os.getenv('F612_OUT','f612_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N


def metrics(p):
    p=np.asarray(p,dtype=float)
    w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':w,'losses':int(len(p)-w),'wr':float(w/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'exp':float(p.mean()) if len(p) else np.nan,'pf':float(gp/gl) if gl>0 else math.inf,
            'dd':dd,'ls':int(ls),'gross_profit':gp,'gross_loss':gl}


def rolling_2h_range_baseline(k,t):
    vals=[]
    # Prior 24h, sampled every completed 5m decision point strictly before entry.
    for s in pd.date_range(t-pd.Timedelta(hours=24), t-pd.Timedelta(minutes=5), freq='5min'):
        pre=k[(k.index<s)&(k.index>=s-pd.Timedelta(hours=2))]
        if len(pre)<12: continue
        hi=float(pre.high.max()); lo=float(pre.low.min()); ref=float(pre.close.iloc[-1])
        if ref>0 and hi>lo:
            vals.append(100.0*(hi-lo)/ref)
    return float(np.median(vals)) if vals else np.nan


def block_table(df,nblocks):
    n=len(df); edges=np.linspace(0,n,nblocks+1,dtype=int); out=[]
    for j in range(nblocks):
        g=df.iloc[edges[j]:edges[j+1]]; a=g[g.action]
        out.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),'n':int(len(g)),
                    'actions':int(len(a)),'delta':float(g.delta.sum()),
                    'strict_sinks_cut':int(a.strict_sink.sum()),'parent_winners_cut':int(a.parent_win.sum())})
    return out


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        f2=f611.fib_features(k,t,float(tr.entry),120)
        if f2 is None: raise RuntimeError(f'missing 2h fib features for {tr.date}')
        baseline=rolling_2h_range_baseline(k,t)

        first=k.loc[t]
        first5_red=bool(float(first.close)<tr.entry)
        alive5=bool(tr.exit_t>t+pd.Timedelta(minutes=5))

        bars=k[(k.index>=t)&(k.index<tr.exit_t)]
        rest=bars.iloc[1:]
        strict_sink=bool(first5_red and (rest.empty or float(rest.high.max())<tr.entry-1e-12))
        red_recover=bool(first5_red and not strict_sink)

        shallow=bool(float(f2['retr_depth'])<=0.382)
        expansion=bool(np.isfinite(baseline) and float(f2['range_pct'])>baseline)
        action=bool(first5_red and alive5 and shallow and expansion)

        managed=float(tr.pnl); cut_px=np.nan
        if action:
            cut_px=float(k.loc[t+pd.Timedelta(minutes=5),'open'])
            managed=f517.NOTIONAL*(cut_px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
        delta=managed-float(tr.pnl)
        rows.append({'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
                     'entry':float(tr.entry),'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_reason':tr.reason,
                     'first5_red':first5_red,'alive5':alive5,'strict_sink':strict_sink,'red_recover':red_recover,
                     'retr2h':float(f2['retr_depth']),'range2h_pct':float(f2['range_pct']),'range2h_baseline24h':baseline,
                     'range_expansion_ratio':float(f2['range_pct']/baseline) if np.isfinite(baseline) and baseline>0 else np.nan,
                     'shallow_382':shallow,'large_expansion':expansion,'action':action,'cut_px':cut_px,
                     'managed_pnl':managed,'delta':delta})
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f612_rows.csv',index=False)

    parent=metrics(df.parent_pnl); managed=metrics(df.managed_pnl)
    a=df[df.action].copy(); d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]

    # Jackknife action contributions.
    jack=[]
    for idx,r in a.iterrows():
        p=df.managed_pnl.copy(); p.loc[idx]=df.loc[idx,'parent_pnl']
        m=metrics(p)
        jack.append({'removed_date':r.date,'removed_delta':float(r.delta),'remaining_delta':float(m['pnl']-parent['pnl'])})
    jdf=pd.DataFrame(jack); jdf.to_csv(OUT/'f612_jackknife.csv',index=False)
    b4=block_table(df,4); b8=block_table(df,8)
    pd.DataFrame(b4).to_csv(OUT/'f612_blocks4.csv',index=False); pd.DataFrame(b8).to_csv(OUT/'f612_blocks8.csv',index=False)

    strict_total=int(df.strict_sink.sum()); strict_cut=int(a.strict_sink.sum())
    redrec_total=int(df.red_recover.sum()); redrec_cut=int(a.red_recover.sum())
    out={
      'rule':'first5_red + alive5 + preentry_2h_retr<=38.2% + preentry_2h_range>causal_prior24h_median_2h_range -> exit actual +5m open',
      'parent':parent,'managed':managed,'delta':float(managed['pnl']-parent['pnl']),
      'discovery_delta':float(d.delta.sum()),'validation_delta':float(v.delta.sum()),
      'actions':int(len(a)),'parent_winners_cut':int(a.parent_win.sum()),'parent_losers_cut':int((~a.parent_win).sum()),
      'positive_action_deltas':int((a.delta>0).sum()),'negative_action_deltas':int((a.delta<0).sum()),
      'strict_sink_total':strict_total,'strict_sinks_cut':strict_cut,'strict_sink_recall':float(strict_cut/strict_total) if strict_total else np.nan,
      'red_recover_total':redrec_total,'red_recover_cut':redrec_cut,
      'action_strict_sink_precision':float(strict_cut/len(a)) if len(a) else np.nan,
      'action_parent_pnl':float(a.parent_pnl.sum()),'action_managed_pnl':float(a.managed_pnl.sum()),
      'dd_improvement':float(parent['dd']-managed['dd']),
      'jackknife_min_remaining_delta':float(jdf.remaining_delta.min()) if len(jdf) else np.nan,
      'jackknife_max_remaining_delta':float(jdf.remaining_delta.max()) if len(jdf) else np.nan,
      'blocks4':b4,'blocks8':b8,
      'actions_detail':a[['date','period','parent_pnl','managed_pnl','delta','parent_win','strict_sink','red_recover','retr2h','range2h_pct','range2h_baseline24h','range_expansion_ratio']].to_dict('records')
    }
    out['economic_pass']=bool(out['delta']>0 and out['discovery_delta']>0 and out['validation_delta']>0 and out['parent_winners_cut']==0)
    (OUT/'f612_summary.json').write_text(json.dumps(out,indent=2,default=float))

    md=['# Friday15 F6.12 — Fib Context +5m Early Cut','',
        f"**Status:** COMPLETE — {'ECONOMIC PASS' if out['economic_pass'] else 'NOT PROMOTED'}",'**Research only; live BBC untouched.**','',
        '## Frozen rule','At +5m: first5 red + alive + pre-entry 2h retracement <=38.2% + 2h range above its causal prior-24h rolling median -> exit actual +5m open. No threshold sweep.','',
        '## Result',
        f"- actions **{out['actions']}**; parent winners cut **{out['parent_winners_cut']}**; losers cut **{out['parent_losers_cut']}**",
        f"- strict sinks caught **{out['strict_sinks_cut']}/{out['strict_sink_total']}**; red-recover trades cut **{out['red_recover_cut']}/{out['red_recover_total']}**",
        f"- PnL **{parent['pnl']:+.3f} -> {managed['pnl']:+.3f}**, delta **{out['delta']:+.3f}**",
        f"- Discovery/Validation delta **{out['discovery_delta']:+.3f} / {out['validation_delta']:+.3f}**",
        f"- PF **{parent['pf']:.3f} -> {managed['pf']:.3f}**, DD **{parent['dd']:.3f} -> {managed['dd']:.3f}**",'',
        '## Interpretation','This directly tests whether the F6.11 shallow-Fib + local-expansion context is strong enough to justify an earlier +5m loss cut. It is not a replacement for frozen F6.9/F6.5 unless it improves economics without clipping recoverable winners.']
    (OUT/'F6.12_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
