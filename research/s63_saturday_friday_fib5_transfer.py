#!/usr/bin/env python3
"""S6.3 — Exact Friday F6.12 FIB5 transfer to Saturday18 BUY.

Research only; live BBC untouched.

No Saturday tuning is allowed. Port the Friday F6.12 state exactly:
At +5m, exit BUY at actual +5m open iff:
1) first completed 5m candle closed below entry;
2) position still alive at +5m;
3) pre-entry 2h retracement depth from 2h high <= 38.2%;
4) pre-entry 2h range > causal rolling prior-24h median 2h range.

Evaluate against:
A) frozen Saturday static parent; and
B) S5.7G champion (NO_BULL_TOP_Q_30 on top of A7.19), with FIB5 chronological priority.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s57g_frozen_candidate_robustness as s57g

OUT=Path(os.getenv('S63_OUT','s63_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83


def metrics(p):
    p=np.asarray(p,dtype=float)
    w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':w,'losses':int(len(p)-w),'wr':float(w/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'exp':float(p.mean()) if len(p) else np.nan,
            'pf':float(gp/gl) if gl>0 else math.inf,'dd':dd,'ls':int(ls)}


def fib2h(k,t,entry):
    pre=k[(k.index<t)&(k.index>=t-pd.Timedelta(hours=2))]
    if len(pre)<12: return None
    hi=float(pre.high.max()); lo=float(pre.low.min()); rg=hi-lo
    if rg<=0: return None
    return {'retr':float((hi-entry)/rg),'range_pct':float(100.0*rg/entry)}


def rolling_2h_range_baseline(k,t):
    vals=[]
    for s in pd.date_range(t-pd.Timedelta(hours=24),t-pd.Timedelta(minutes=5),freq='5min'):
        pre=k[(k.index<s)&(k.index>=s-pd.Timedelta(hours=2))]
        if len(pre)<12: continue
        hi=float(pre.high.max()); lo=float(pre.low.min()); ref=float(pre.close.iloc[-1])
        if ref>0 and hi>lo: vals.append(100.0*(hi-lo)/ref)
    return float(np.median(vals)) if vals else np.nan


def block_table(df,nblocks,delta_col):
    edges=np.linspace(0,len(df),nblocks+1,dtype=int); out=[]
    for j in range(nblocks):
        g=df.iloc[edges[j]:edges[j+1]]; a=g[g.action]
        out.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),'n':int(len(g)),
                    'actions':int(len(a)),'delta':float(g[delta_col].sum()),
                    'parent_winners_cut':int(a.parent_win.sum())})
    return out


def main():
    k=s50.load_klines(); f=s50.load_funding(); entries=s50.saturday_entries(k)
    trades=[s50.simulate(k,f,t) for t in entries]
    if len(trades)!=139: raise RuntimeError(f'parent N parity fail {len(trades)}')

    rows=[]
    for i,(t,tr) in enumerate(zip(entries,trades)):
        fib=fib2h(k,t,float(tr.entry))
        if fib is None: raise RuntimeError(f'missing fib {tr.date}')
        baseline=rolling_2h_range_baseline(k,t)
        first=k.loc[t]
        first5_red=bool(float(first.close)<float(tr.entry))
        alive5=bool(pd.Timestamp(tr.exit_t)>t+pd.Timedelta(minutes=5))
        shallow=bool(fib['retr']<=0.382)
        expansion=bool(np.isfinite(baseline) and fib['range_pct']>baseline)
        action=bool(first5_red and alive5 and shallow and expansion)
        managed=float(tr.pnl); cut_px=np.nan
        if action:
            cut_px=float(k.loc[t+pd.Timedelta(minutes=5),'open'])
            managed=s50.NOTIONAL*(cut_px/float(tr.entry)-1.0)-s50.FEE
        rows.append({'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
                     'entry':float(tr.entry),'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),
                     'parent_reason':tr.reason,'first5_red':first5_red,'alive5':alive5,
                     'retr2h':fib['retr'],'range2h_pct':fib['range_pct'],'range2h_baseline24h':baseline,
                     'range_expansion_ratio':fib['range_pct']/baseline if np.isfinite(baseline) and baseline>0 else np.nan,
                     'shallow_382':shallow,'large_expansion':expansion,'action':action,'cut_px':cut_px,
                     'fib5_pnl':managed,'fib5_delta':managed-float(tr.pnl)})
    df=pd.DataFrame(rows)

    # S5.7G champion parity and integration. Use its exact frozen implementation.
    gdf,parent_all,a719_all=s57g.build_rows()
    champ=gdf[gdf.candidate=='NO_BULL_TOP_Q_30'].copy().sort_values('idx')
    if len(champ)!=139: raise RuntimeError('champion N parity fail')
    if abs(float(champ.strategy_pnl.sum())-111.240) > 0.05: raise RuntimeError(f'champion pnl parity fail {champ.strategy_pnl.sum()}')
    df['champion_pnl']=champ.strategy_pnl.to_numpy(float)
    df['champion_action']=champ.action.to_numpy(bool)
    df['integrated_pnl']=np.where(df.action,df.fib5_pnl,df.champion_pnl)
    df['integrated_delta_vs_champion']=df.integrated_pnl-df.champion_pnl
    df.to_csv(OUT/'s63_rows.csv',index=False)

    parent=metrics(df.parent_pnl); fib5=metrics(df.fib5_pnl); champion=metrics(df.champion_pnl); integ=metrics(df.integrated_pnl)
    a=df[df.action].copy(); d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]

    # Action jackknife on static-parent FIB5 contribution.
    jack=[]
    for idx,r in a.iterrows():
        jack.append({'removed_date':r.date,'removed_delta':float(r.fib5_delta),
                     'remaining_delta':float(df.fib5_delta.sum()-r.fib5_delta)})
    jdf=pd.DataFrame(jack); jdf.to_csv(OUT/'s63_jackknife.csv',index=False)
    b4=block_table(df,4,'fib5_delta'); b8=block_table(df,8,'fib5_delta')
    pd.DataFrame(b4).to_csv(OUT/'s63_blocks4.csv',index=False); pd.DataFrame(b8).to_csv(OUT/'s63_blocks8.csv',index=False)

    out={
      'rule':'EXACT_FRIDAY_F612_TRANSFER: first5_red + alive5 + preentry_2h_retr<=38.2% + preentry_2h_range>causal_prior24h_median_2h_range -> exit actual +5m open',
      'static_parent':parent,'fib5_on_static':fib5,
      'fib5_delta_vs_static':float(fib5['pnl']-parent['pnl']),
      'disc_delta_vs_static':float(d.fib5_delta.sum()),'val_delta_vs_static':float(v.fib5_delta.sum()),
      'actions':int(len(a)),'parent_winners_cut':int(a.parent_win.sum()),'parent_losers_cut':int((~a.parent_win).sum()),
      'positive_action_deltas':int((a.fib5_delta>0).sum()),'negative_action_deltas':int((a.fib5_delta<0).sum()),
      'action_parent_pnl':float(a.parent_pnl.sum()),'action_fib5_pnl':float(a.fib5_pnl.sum()),
      'jackknife_min_remaining_delta':float(jdf.remaining_delta.min()) if len(jdf) else np.nan,
      'blocks4':b4,'blocks8':b8,
      'champion':champion,'integrated':integ,
      'incremental_vs_champion':float(integ['pnl']-champion['pnl']),
      'disc_incremental_vs_champion':float(d.integrated_delta_vs_champion.sum()),
      'val_incremental_vs_champion':float(v.integrated_delta_vs_champion.sum()),
      'fib5_overlap_champion_actions':int((df.action & df.champion_action).sum()),
      'fib5_unique_vs_champion_actions':int((df.action & ~df.champion_action).sum()),
      'actions_detail':a[['date','period','parent_pnl','fib5_pnl','fib5_delta','parent_win','parent_reason','retr2h','range2h_pct','range2h_baseline24h','range_expansion_ratio','champion_pnl','champion_action','integrated_delta_vs_champion']].to_dict('records')
    }
    out['static_transfer_pass']=bool(out['fib5_delta_vs_static']>0 and out['disc_delta_vs_static']>0 and out['val_delta_vs_static']>0 and out['parent_winners_cut']==0)
    out['champion_incremental_pass']=bool(out['incremental_vs_champion']>0 and out['disc_incremental_vs_champion']>0 and out['val_incremental_vs_champion']>0)
    (OUT/'s63_summary.json').write_text(json.dumps(out,indent=2,default=float))

    md=['# Saturday S6.3 — Exact Friday FIB5 Transfer','',
        f"**Static transfer:** {'PASS' if out['static_transfer_pass'] else 'NOT PASS'}",
        f"**Incremental vs S5.7G champion:** {'PASS' if out['champion_incremental_pass'] else 'NOT PASS'}",
        '**Research only; live BBC untouched. No Saturday threshold tuning.**','',
        '## Frozen transferred rule','Exact Friday F6.12: first5 red + alive + pre-entry 2h retracement <=38.2% + 2h range above causal prior-24h median -> exit actual +5m open.','',
        '## Static parent transfer',
        f"- actions **{out['actions']}**, winners cut **{out['parent_winners_cut']}**, losers cut **{out['parent_losers_cut']}**",
        f"- PnL **{parent['pnl']:+.3f} -> {fib5['pnl']:+.3f}**, delta **{out['fib5_delta_vs_static']:+.3f}**",
        f"- D/V delta **{out['disc_delta_vs_static']:+.3f} / {out['val_delta_vs_static']:+.3f}**",
        f"- PF **{parent['pf']:.3f} -> {fib5['pf']:.3f}**, DD **{parent['dd']:.3f} -> {fib5['dd']:.3f}**",'',
        '## Incremental on S5.7G champion',
        f"- champion PnL **{champion['pnl']:+.3f} -> integrated {integ['pnl']:+.3f}**, incremental **{out['incremental_vs_champion']:+.3f}**",
        f"- D/V incremental **{out['disc_incremental_vs_champion']:+.3f} / {out['val_incremental_vs_champion']:+.3f}**",
        f"- Fib5 overlap with champion actions **{out['fib5_overlap_champion_actions']}**, unique Fib5 actions **{out['fib5_unique_vs_champion_actions']}**",'',
        '## Guardrail','Because Saturday is a different weekday/parent and the exact Friday rule is transferred without tuning, this is a meaningful cross-context transfer test. Still, all results use the historical Saturday sample; do not retune based on this run.']
    (OUT/'S6.3_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
