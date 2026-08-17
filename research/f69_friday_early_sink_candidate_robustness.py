#!/usr/bin/env python3
"""F6.9 — Friday15 early-sink candidate robustness + layered management.

Research only; live BBC untouched.

IMPORTANT DISCOVERY STATUS:
The candidate below emerged during post-F6.8 exploratory combination inspection.
Therefore this milestone is a SAME-SAMPLE robustness audit, not independent
confirmation. No threshold changes are allowed here.

Frozen candidate from exploration:
At +10m, exit at actual +10m open iff:
1) first 5m candle closed below entry;
2) position is alive at +10m;
3) second completed 5m candle high remains below entry (no trade reclaim);
4) second completed 5m candle close is below EMA7;
5) second completed 5m candle body ratio < 50% of its range.

The 50% body threshold is frozen for this audit. No retuning/sweep.

Also measure interaction with the already-frozen F6.5 +60m upper-wick true-failure
cut. Early candidate has priority; F6.5 is evaluated only if no early exit occurred.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60
import f63_friday_failure60_candle_morphology as f63

OUT=Path(os.getenv('F69_OUT','f69_out')); OUT.mkdir(parents=True,exist_ok=True)
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


def body_ratio(b):
    rg=float(b.high)-float(b.low)
    return abs(float(b.close)-float(b.open))/rg if rg>0 else 0.0


def early_state(k,t,tr):
    b1=k.loc[t]; b2=k.loc[t+pd.Timedelta(minutes=5)]; dt=t+pd.Timedelta(minutes=10)
    return bool(
        float(b1.close)<tr.entry and
        tr.exit_t>dt and
        float(b2.high)<tr.entry-1e-12 and
        float(b2.close)<float(b2.ema7) and
        body_ratio(b2)<0.50
    )


def f65_state(k,t,tr):
    pf=f60.path_features(k,t,tr)
    failure=bool(pf['alive60'] and pf['progress60']<=0 and pf['taker60']<0 and pf['ema20_dist60']<=0)
    if not failure: return False
    cf=f63.candle(k,t+pd.Timedelta(minutes=60),tr.entry)
    return bool(cf is not None and cf['UPPER_WICK_DOM'])


def block_table(df,delta_col,nblocks):
    n=len(df); edges=np.linspace(0,n,nblocks+1,dtype=int); out=[]
    for j in range(nblocks):
        g=df.iloc[edges[j]:edges[j+1]]
        a=g[g[delta_col].abs()>1e-12]
        out.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),
                    'n':int(len(g)),'actions':int(len(a)),'delta':float(g[delta_col].sum()),
                    'positive_actions':int((a[delta_col]>0).sum()),'negative_actions':int((a[delta_col]<0).sum())})
    return out


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        early=early_state(k,t,tr)
        f65=f65_state(k,t,tr)

        early_pnl=float(tr.pnl); early_delta=0.0
        if early:
            px=float(k.loc[t+pd.Timedelta(minutes=10),'open'])
            early_pnl=f517.NOTIONAL*(px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
            early_delta=early_pnl-float(tr.pnl)

        f65_pnl=float(tr.pnl); f65_delta=0.0
        if f65:
            px=float(k.loc[t+pd.Timedelta(minutes=60),'open'])
            f65_pnl=f517.NOTIONAL*(px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
            f65_delta=f65_pnl-float(tr.pnl)

        layered_pnl=float(tr.pnl); layer='PARENT'
        if early:
            layered_pnl=early_pnl; layer='EARLY10'
        elif f65:
            layered_pnl=f65_pnl; layer='F65_60'

        rows.append({'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
                     'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_reason':tr.reason,
                     'early10':early,'f65':f65,'early_pnl':early_pnl,'early_delta':early_delta,
                     'f65_pnl':f65_pnl,'f65_delta':f65_delta,'layered_pnl':layered_pnl,
                     'layered_delta':layered_pnl-float(tr.pnl),'layer':layer})
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f69_rows.csv',index=False)

    early=df[df.early10].copy(); f65=df[df.f65].copy()
    if len(early)!=10: raise RuntimeError(f'candidate parity expected 10 got {len(early)}')
    if int(early.parent_win.sum())!=0: raise RuntimeError('candidate winner parity changed')
    if len(f65)!=6: raise RuntimeError(f'F6.5 parity expected 6 got {len(f65)}')

    parent=metrics(df.parent_pnl); em=metrics(df.early_pnl); lm=metrics(df.layered_pnl)
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]

    # Action-level jackknife: remove one early action at a time (restore parent for that date).
    jack=[]
    for idx,r in early.iterrows():
        p=df.early_pnl.copy(); p.loc[idx]=df.loc[idx,'parent_pnl']
        m=metrics(p)
        jack.append({'removed_date':r.date,'removed_delta':float(r.early_delta),
                     'remaining_delta':float(m['pnl']-parent['pnl']),'remaining_dd':float(m['dd'])})
    jdf=pd.DataFrame(jack); jdf.to_csv(OUT/'f69_jackknife.csv',index=False)

    b4=block_table(df,'early_delta',4); b8=block_table(df,'early_delta',8)
    pd.DataFrame(b4).to_csv(OUT/'f69_blocks4.csv',index=False)
    pd.DataFrame(b8).to_csv(OUT/'f69_blocks8.csv',index=False)

    early_result={
      'actions':int(len(early)),'parent_winners_cut':int(early.parent_win.sum()),
      'positive_actions':int((early.early_delta>0).sum()),'negative_actions':int((early.early_delta<0).sum()),
      'action_parent_pnl':float(early.parent_pnl.sum()),'action_managed_pnl':float(early.early_pnl.sum()),
      'delta':float(em['pnl']-parent['pnl']),'discovery_delta':float(d.early_delta.sum()),'validation_delta':float(v.early_delta.sum()),
      'parent':parent,'managed':em,'dd_improvement':float(parent['dd']-em['dd']),
      'jackknife_min_delta':float(jdf.remaining_delta.min()),'jackknife_max_delta':float(jdf.remaining_delta.max()),
      'blocks4':b4,'blocks8':b8,
    }
    early_result['robust_same_sample']=bool(
        early_result['delta']>0 and early_result['discovery_delta']>0 and early_result['validation_delta']>0 and
        early_result['parent_winners_cut']==0 and early_result['dd_improvement']>=0 and
        early_result['jackknife_min_delta']>0 and all(x['delta']>=0 for x in b4 if x['actions']>0)
    )

    layered={
      'early_actions':int(df.early10.sum()),'f65_actions':int((~df.early10 & df.f65).sum()),
      'overlap_actions':int((df.early10 & df.f65).sum()),
      'parent':parent,'managed':lm,'delta':float(lm['pnl']-parent['pnl']),
      'discovery_delta':float(d.layered_delta.sum()),'validation_delta':float(v.layered_delta.sum()),
      'dd_improvement':float(parent['dd']-lm['dd'])
    }
    out={'discovery_status':'POST_F68_EXPLORATORY_CANDIDATE__NOT_INDEPENDENT_OOS',
         'early_candidate':early_result,'layered_with_f65':layered,
         'actions':early[['date','period','parent_pnl','early_pnl','early_delta','parent_reason']].to_dict('records')}
    (OUT/'f69_summary.json').write_text(json.dumps(out,indent=2,default=float))

    md=['# Friday15 F6.9 — Early-Sink Candidate Robustness','',
        f"**Status:** COMPLETE — {'SAME-SAMPLE ROBUST PASS' if early_result['robust_same_sample'] else 'SAME-SAMPLE ROBUST FAIL'}",
        '**Important:** candidate was discovered after F6.8 exploration; this is NOT independent OOS confirmation.',
        '**Research only; live BBC untouched.**','',
        '## Frozen candidate','At +10m: first5 red + still alive + second 5m has not traded back to entry + second close below EMA7 + second body ratio <50% -> exit actual +10m open.','',
        '## Candidate economics',
        f"- actions **{early_result['actions']}**, parent winners cut **{early_result['parent_winners_cut']}**",
        f"- action PnL **{early_result['action_parent_pnl']:+.3f} -> {early_result['action_managed_pnl']:+.3f}**",
        f"- strategy delta **{early_result['delta']:+.3f}**; Discovery **{early_result['discovery_delta']:+.3f}**; Validation **{early_result['validation_delta']:+.3f}**",
        f"- PnL **{parent['pnl']:+.3f} -> {em['pnl']:+.3f}**; PF **{parent['pf']:.3f} -> {em['pf']:.3f}**; DD **{parent['dd']:.3f} -> {em['dd']:.3f}**",
        f"- positive/negative actions **{early_result['positive_actions']}/{early_result['negative_actions']}**",
        f"- jackknife remaining delta range **{early_result['jackknife_min_delta']:+.3f} .. {early_result['jackknife_max_delta']:+.3f}**",'',
        '## Layered with frozen F6.5',
        f"- overlap **{layered['overlap_actions']}**",
        f"- active early actions **{layered['early_actions']}**, later F6.5 actions **{layered['f65_actions']}**",
        f"- layered PnL **{parent['pnl']:+.3f} -> {lm['pnl']:+.3f}**, delta **{layered['delta']:+.3f}**",
        f"- Discovery/Validation delta **{layered['discovery_delta']:+.3f} / {layered['validation_delta']:+.3f}**",
        f"- PF **{parent['pf']:.3f} -> {lm['pf']:.3f}**, DD **{parent['dd']:.3f} -> {lm['dd']:.3f}**",'',
        '## Guardrail','Do not call this independently validated or deploy it live from this result alone. The exact candidate must remain frozen for future unseen Friday observations / true OOS extension. No body-threshold or EMA variant retuning on the same 971-day sample.']
    (OUT/'F6.9_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
