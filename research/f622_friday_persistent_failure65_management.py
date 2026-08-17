#!/usr/bin/env python3
"""F6.22 — Friday PERSISTENT_FAILURE_65 management.

Research only; live BBC untouched. Frozen F6.12/F6.9/F6.5 and F6.18 D3
remain unchanged.

Motivation from F6.21/F6.21b:
- fixed +35/+65 snapshots were too noisy;
- persistent EMA7 rejection and weak late buyer flow were the closest
  interpretable trajectory clues, but no single feature was cross-stable.

Exactly ONE predeclared causal state is tested; no threshold sweep:
  PERSISTENT_FAILURE_65
  - trade has causally reached +0.5R;
  - exactly 65m after the first +0.5R hit;
  - the final four completed 5m bars ALL close below their EMA7;
  - mean taker imbalance of the final two completed 5m bars is < 0;
  - exit at the actual +65m decision open.

The 4-bar persistence window is a natural 20-minute confirmation window,
not a sweep of the F6.21 observed 5-vs-4 median streak.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f620_friday_failure_to_accelerate_management as f620

OUT=Path(os.getenv('F622_OUT','f622_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
RULE='PERSISTENT_FAILURE_65'


def metrics(pnls):
    p=np.asarray(pnls,dtype=float); wins=int((p>0).sum())
    gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq])
    dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':wins,'losses':int(len(p)-wins),
            'wr':float(wins/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'pf':float(gp/gl) if gl>0 else math.inf,
            'dd':dd,'ls':int(ls)}


def persistent_state(k,tr):
    ht=f616.first_hit(k,tr,0.5*R)
    if ht is None:return None
    dt=ht+pd.Timedelta(minutes=65)
    if dt not in k.index or tr.exit_t<=dt:return None
    w=k[(k.index>=ht)&(k.index<dt)].copy()
    if len(w)!=13:return None
    tail4=w.iloc[-4:]
    tail2=w.iloc[-2:]
    all_below7=bool((tail4.close.astype(float)<tail4.ema7.astype(float)).all())
    flow2=float(tail2.taker_imb.astype(float).mean())
    return {
        'hit_t':ht,'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
        'tail4_all_below_ema7':all_below7,
        'tail2_taker_mean':flow2,
        RULE:bool(all_below7 and flow2<0),
    }


def candidate_event(tr,st):
    if st is None or not st[RULE]:return None
    dt=st['decision_t']
    if tr.exit_t<=dt:return None
    return (dt,RULE,f616.cut_pnl(tr.entry,float(st['decision_open'])))


def apply(k,t,tr,st):
    ev=list(f620.frozen_events(k,t,tr))
    ce=candidate_event(tr,st)
    if ce is not None:ev.append(ce)
    if not ev:return float(tr.pnl),'PARENT',None
    ev.sort(key=lambda x:x[0])
    dt,layer,pnl=ev[0]
    return float(pnl),layer,dt


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        fe=f620.frozen_events(k,t,tr)
        if fe:
            base_dt,base_layer,base_pnl=fe[0]
        else:
            base_dt,base_layer,base_pnl=None,'PARENT',float(tr.pnl)
        st=persistent_state(k,tr)
        pnl,layer,dt=apply(k,t,tr,st)
        row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),
             'frozen_pnl':float(base_pnl),'frozen_layer':base_layer,
             'managed_pnl':pnl,'managed_layer':layer,'incremental':pnl-float(base_pnl)}
        if st:
            row['signal']=bool(st[RULE]); row['tail4_all_below_ema7']=st['tail4_all_below_ema7']; row['tail2_taker_mean']=st['tail2_taker_mean']; row['decision_t']=str(st['decision_t'])
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f622_rows.csv',index=False)

    parent_m=metrics(df.parent_pnl); base_m=metrics(df.frozen_pnl); m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-123.232)>0.10 or abs(base_m['wr']*100-51.45)>0.08:
        raise AssertionError(f'F6.18 stack parity mismatch {base_m}')

    acts=df[df.managed_layer==RULE].copy()
    d=df[df.i<f517.SPLIT_N]; v=df[df.i>=f517.SPLIT_N]
    low=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r>=0.5)&(acts.parent_mfe_r<1.0)]
    high=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r>=1.0)&(acts.parent_mfe_r<2.0)]
    inc=float(m['pnl']-base_m['pnl']); incD=float(d.incremental.sum()); incV=float(v.incremental.sum())
    loss_pos=int(((acts.parent_pnl<=0)&(acts.managed_pnl>0)).sum())
    win_nonpos=int(((acts.parent_pnl>0)&(acts.managed_pnl<=0)).sum())
    screen=bool(inc>0 and incD>=0 and incV>=0 and len(low)>0 and win_nonpos==0 and m['wr']>=base_m['wr'] and m['dd']<=base_m['dd']+1e-9)

    out={
      'rule_definition':{
        'milestone':'+0.5R','decision':'65m after first causal +0.5R hit',
        'ema7_persistence':'final 4 completed 5m bars all close below EMA7',
        'flow':'mean taker imbalance of final 2 completed 5m bars < 0',
        'exit':'actual +65m 5m open'},
      'parent':parent_m,'frozen_four_layer':base_m,'managed':m,
      'actions':int(len(acts)),'actions_D':int((acts.i<f517.SPLIT_N).sum()),'actions_V':int((acts.i>=f517.SPLIT_N).sum()),
      'parent_winners_acted':int(acts.parent_win.sum()),'parent_losses_acted':int((~acts.parent_win).sum()),
      'low_givebacks_acted':int(len(low)),'high_givebacks_acted':int(len(high)),
      'loss_to_positive':loss_pos,'winner_to_nonpositive':win_nonpos,
      'positive_increment_actions':int((acts.incremental>0).sum()),'negative_increment_actions':int((acts.incremental<0).sum()),
      'incremental_vs_frozen':inc,'incremental_D':incD,'incremental_V':incV,
      'wr_gain_pp':float((m['wr']-base_m['wr'])*100),'dd_improvement':float(base_m['dd']-m['dd']),
      'screen_pass':screen,
      'action_dates':acts[['date','period','parent_pnl','parent_mfe_r','frozen_pnl','managed_pnl','incremental','tail2_taker_mean']].to_dict('records') if len(acts) else []}
    (OUT/'f622_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.22 — PERSISTENT_FAILURE_65 Management','',
        '**Status: COMPLETE — single predeclared causal action test. Live BBC untouched.**','',
        '## Frozen rule','- first causal +0.5R milestone','- evaluate exactly +65m later','- final four completed 5m closes are all below EMA7','- final two completed 5m taker imbalance mean < 0','- exit at actual decision-time open','- no EMA20/Fib/new timing sweep','',
        '## Baseline',f"Frozen four-layer: **{base_m['pnl']:+.3f}**, WR **{base_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f}**, DD **{base_m['dd']:.3f}**.",'',
        '## Result',f"- actions **{len(acts)}** (D {(acts.i<f517.SPLIT_N).sum()} / V {(acts.i>=f517.SPLIT_N).sum()})",f"- low givebacks caught **{len(low)}**; high givebacks caught **{len(high)}**; eventual winners acted **{acts.parent_win.sum()}**",f"- loss→positive **{loss_pos}**; winner→nonpositive **{win_nonpos}**",f"- incremental **{inc:+.3f}**; D/V **{incD:+.3f} / {incV:+.3f}**",f"- managed PnL **{m['pnl']:+.3f}**, WR **{m['wr']*100:.2f}%**, PF **{m['pf']:.3f}**, DD **{m['dd']:.3f}**",f"- screen **{'PASS' if screen else 'FAIL'}**",'',
        '## Guardrail','F6.22 is motivated by same-sample trajectory forensic. A PASS remains provisional until independent OOS trigger evidence accumulates. Do not retune 4 bars, 2-bar flow, or 65m timing on this sample.']
    (OUT/'F6.22_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
