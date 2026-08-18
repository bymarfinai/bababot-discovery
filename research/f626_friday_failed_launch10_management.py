#!/usr/bin/env python3
"""F6.26 — Friday FAILED_LAUNCH_10 management.

Research only; live BBC untouched. Frozen Friday layers remain unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.

Exactly one predeclared causal rule from F6.25; no threshold/timing sweep:
  FAILED_LAUNCH_10
  - evaluate exactly +10m after Friday entry using two completed 5m bars;
  - position is still alive at the +10m decision open;
  - price has never reached +0.5R during those two completed bars;
  - second 5m high < first 5m high (lower high);
  - second completed close < entry;
  - second completed close < EMA7;
  - exit at actual +10m open.

The +0.5R level is the natural risk milestone, not a fitted F6.25 MFE cutoff.
No MFE threshold such as 0.18R, no taker filter, no wick/body filter, no EMA20,
and no timing alternatives are tested here.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f624_friday_context_repair_failure_management as f624

OUT=Path(os.getenv('F626_OUT','f626_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
RULE='FAILED_LAUNCH_10'
SPLIT=f517.SPLIT_N


def metrics(pnls):
    p=np.asarray(pnls,dtype=float); wins=int((p>0).sum())
    gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':wins,'losses':int(len(p)-wins),'wr':float(wins/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'pf':float(gp/gl) if gl>0 else math.inf,'dd':dd,'ls':int(ls)}


def failed_launch_state(k,t,tr):
    dt=t+pd.Timedelta(minutes=10)
    if dt not in k.index or pd.Timestamp(tr.exit_t)<=dt:return None
    w=k[(k.index>=t)&(k.index<dt)]
    if len(w)!=2:return None
    b1=w.iloc[0]; b2=w.iloc[1]
    no_half_r=bool(float(w.high.max()) < float(tr.entry)*(1.0+0.5*R))
    lower_high=bool(float(b2.high) < float(b1.high))
    below_entry=bool(float(b2.close) < float(tr.entry))
    below_ema7=bool(float(b2.close) < float(b2.ema7))
    signal=bool(no_half_r and lower_high and below_entry and below_ema7)
    return {
      'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
      'no_half_r':no_half_r,'lower_high':lower_high,'below_entry':below_entry,'below_ema7':below_ema7,
      'mfe10_r':float((float(w.high.max())/float(tr.entry)-1.0)/R),
      'progress10_r':float((float(b2.close)/float(tr.entry)-1.0)/R),
      'ema7_dist10_r':float((float(b2.close)/float(b2.ema7)-1.0)/R),
      RULE:signal,
    }


def candidate_pnl(tr,st):
    return f616.cut_pnl(float(tr.entry),float(st['decision_open']))


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr)
        f624st=f624.state(k,tr)
        base_pnl,base_layer,base_dt=f624.apply(k,t,tr,f624st)
        st=failed_launch_state(k,t,tr)
        managed=float(base_pnl); layer=base_layer; action=False
        if st is not None and st[RULE]:
            dt=st['decision_t']
            # Frozen layers win ties; candidate can only preempt a strictly later frozen exit.
            if base_dt is None or dt < pd.Timestamp(base_dt):
                managed=float(candidate_pnl(tr,st)); layer=RULE; action=True
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_reason':tr.reason,
             'parent_mfe_r':float(tr.mfe/R),'base_pnl':float(base_pnl),'base_layer':base_layer,
             'base_dt':None if base_dt is None else str(base_dt),'managed_pnl':managed,'managed_layer':layer,
             'incremental':managed-float(base_pnl),'active_action':action}
        if st is not None:
            row.update({'raw_signal':bool(st[RULE]),'decision_t':str(st['decision_t']),
                        'no_half_r':bool(st['no_half_r']),'lower_high':bool(st['lower_high']),
                        'below_entry':bool(st['below_entry']),'below_ema7':bool(st['below_ema7']),
                        'mfe10_r':float(st['mfe10_r']),'progress10_r':float(st['progress10_r']),
                        'ema7_dist10_r':float(st['ema7_dist10_r'])})
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT/'f626_rows.csv',index=False)
    parent_m=metrics(df.parent_pnl);base_m=metrics(df.base_pnl);managed_m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'latest five-layer parity fail {base_m}')

    raw=df[df.raw_signal==True].copy() if 'raw_signal' in df.columns else df.iloc[0:0]
    acts=df[df.active_action].copy()
    d=df[df.i<SPLIT];v=df[df.i>=SPLIT]
    # F6.25 exact wrong-direction/failure-to-develop cohort under latest frozen stack.
    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<0.5)&(df.base_layer=='PARENT')].copy()
    if len(target)!=24:raise RuntimeError(f'F6.25 target parity fail {len(target)}')
    caught=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r<0.5)&(acts.base_layer=='PARENT')]
    inc=float(managed_m['pnl']-base_m['pnl']);incD=float(d.incremental.sum());incV=float(v.incremental.sum())
    winner_acted=int((acts.parent_pnl>0).sum());baseline_pos_nonpos=int(((acts.base_pnl>0)&(acts.managed_pnl<=0)).sum())
    parent_win_nonpos=int(((acts.parent_pnl>0)&(acts.managed_pnl<=0)).sum())
    loss_to_positive=int(((acts.parent_pnl<=0)&(acts.managed_pnl>0)).sum())

    jack=[float(inc-r.incremental) for _,r in acts.iterrows()]
    edges=np.linspace(0,len(df),5,dtype=int);blocks=[]
    for j in range(4):
        g=df.iloc[edges[j]:edges[j+1]]
        blocks.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),
                       'actions':int(g.active_action.sum()),'incremental':float(g.incremental.sum())})

    screen=bool(inc>0 and incD>=0 and incV>=0 and len(caught)>0 and baseline_pos_nonpos==0 and
                managed_m['wr']>=base_m['wr'] and managed_m['dd']<=base_m['dd']+1e-9)
    out={
      'rule_definition':{
        'decision':'+10m actual open after two completed 5m bars',
        'conditions':['still alive','never reached +0.5R','second high < first high','second close < entry','second close < EMA7'],
        'exit':'actual +10m open','tuning':'none'},
      'parent':parent_m,'frozen_five_layer':base_m,'managed':managed_m,
      'f625_target_n':int(len(target)),'raw_signals':int(len(raw)),'active_actions':int(len(acts)),
      'actions_D':int((acts.i<SPLIT).sum()),'actions_V':int((acts.i>=SPLIT).sum()),
      'preempted_by_frozen':int(len(raw)-len(acts)),
      'failure_to_develop_caught':int(len(caught)),
      'failure_to_develop_catch_rate':float(len(caught)/len(target)),
      'parent_winners_acted':winner_acted,'parent_losses_acted':int((acts.parent_pnl<=0).sum()),
      'loss_to_positive':loss_to_positive,'parent_winner_to_nonpositive':parent_win_nonpos,
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,
      'positive_increment_actions':int((acts.incremental>0).sum()),'negative_increment_actions':int((acts.incremental<0).sum()),
      'incremental_vs_frozen':inc,'incremental_D':incD,'incremental_V':incV,
      'wr_gain_pp':float((managed_m['wr']-base_m['wr'])*100),'dd_improvement':float(base_m['dd']-managed_m['dd']),
      'jackknife_min_remaining_incremental':float(min(jack)) if jack else np.nan,'blocks4':blocks,'screen_pass':screen,
      'actions_detail':acts[['date','period','parent_pnl','parent_mfe_r','base_pnl','base_layer','managed_pnl','incremental','mfe10_r','progress10_r','ema7_dist10_r']].to_dict('records') if len(acts) else []}
    (OUT/'f626_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.26 — FAILED_LAUNCH_10 Management','',
        f"**Screen: {'PASS' if screen else 'FAIL'}**",
        '**Research only; live BBC untouched. No threshold/timing sweep.**','',
        '## Exact predeclared rule','At +10m, exit at actual decision open iff still alive, never reached +0.5R, second 5m high < first 5m high, second close < entry, and second close < EMA7. Frozen layers win any same-time tie.','',
        '## Frozen parity',f"- latest five-layer: **{base_m['pnl']:+.3f}**, {base_m['wins']}W/{base_m['losses']}L, WR **{base_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f}**, DD **{base_m['dd']:.3f}**",'',
        '## Result',f"- raw/active signals **{len(raw)} / {len(acts)}**; D/V actions **{(acts.i<SPLIT).sum()} / {(acts.i>=SPLIT).sum()}**",f"- F6.25 failure-to-develop caught **{len(caught)}/24 ({100*len(caught)/24:.1f}%)**",f"- parent winners/losses acted **{winner_acted} / {(acts.parent_pnl<=0).sum()}**",f"- loss→positive **{loss_to_positive}**; baseline positive→nonpositive **{baseline_pos_nonpos}**",f"- incremental **{inc:+.3f}**; D/V **{incD:+.3f} / {incV:+.3f}**",f"- PnL **{base_m['pnl']:+.3f} -> {managed_m['pnl']:+.3f}**; WR **{base_m['wr']*100:.2f}% -> {managed_m['wr']*100:.2f}%**",f"- PF **{base_m['pf']:.3f} -> {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} -> {managed_m['dd']:.3f}**",f"- jackknife min remaining incremental **{min(jack) if jack else float('nan'):+.3f}**",'',
        '## Guardrail','This is a same-sample action test motivated by F6.25. Do not retune +10m, lower-high definition, +0.5R milestone, EMA7, or add taker/body filters based on this run.']
    (OUT/'F6.26_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
