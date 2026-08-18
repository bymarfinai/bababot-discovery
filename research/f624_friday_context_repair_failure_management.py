#!/usr/bin/env python3
"""F6.24 — Friday CONTEXT_REPAIR_FAILURE_65 management.

Research only; live BBC untouched. Frozen F6.12/F6.9/F6.5 and F6.18 D3
remain unchanged. F6.20/F6.22 remain failed diagnostics, not frozen layers.

Exactly ONE predeclared causal rule from F6.23; no threshold sweep:
  CONTEXT_REPAIR_FAILURE_65
  - first causal +0.5R milestone exists;
  - exactly +65m after that first +0.5R hit;
  - F6.22 bearish persistence is present:
      final four completed 5m closes all below EMA7 AND
      mean taker imbalance of final two completed 5m bars < 0;
  - entry is in the UPPER HALF (>50%) of the strictly pre-entry 2h range;
  - from first +0.5R hit to decision, there are ZERO EMA20 reclaims
    (no completed-bar transition from close<EMA20 to close>=EMA20);
  - exit at actual +65m decision open.

The >50% threshold is the natural geometric half-range split, not fitted to
F6.23's observed 68.4% failure median. EMA20 reclaim is a transition count,
not an EMA-distance threshold.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f620_friday_failure_to_accelerate_management as f620
import f622_friday_persistent_failure65_management as f622

OUT=Path(os.getenv('F624_OUT','f624_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
RULE='CONTEXT_REPAIR_FAILURE_65'


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


def cross_up(a):
    a=np.asarray(a,dtype=bool)
    return int(np.sum((~a[:-1]) & a[1:])) if len(a)>1 else 0


def state(k,tr):
    # Reuse F6.22 causal milestone, decision, and bearish-persistence definition.
    b=f622.persistent_state(k,tr)
    if b is None:return None
    ht=b['hit_t']; dt=b['decision_t']

    # Strictly pre-entry 2h structure: 24 completed 5m bars, no entry bar.
    pre=k[(k.index<tr.entry_t)&(k.index>=tr.entry_t-pd.Timedelta(minutes=120))]
    if len(pre)!=24:return None
    hi=float(pre.high.max()); lo=float(pre.low.min()); rng=hi-lo
    if not np.isfinite(rng) or rng<=0:return None
    entry_pos=float((tr.entry-lo)/rng)

    # Completed bars available at decision: [hit_t, decision_t).
    w=k[(k.index>=ht)&(k.index<dt)]
    if len(w)!=13:return None
    above20=(w.close.astype(float).to_numpy()>=w.ema20.astype(float).to_numpy())
    ema20_reclaims=cross_up(above20)
    no_repair=bool(ema20_reclaims==0)
    upper_half=bool(entry_pos>0.5)
    signal=bool(b[f622.RULE] and upper_half and no_repair)
    return {
        **b,
        'pre120_entry_range_pos':entry_pos,
        'upper_half_2h':upper_half,
        'ema20_reclaims':int(ema20_reclaims),
        'no_ema20_reclaim':no_repair,
        RULE:signal,
    }


def candidate_event(tr,st):
    if st is None or not st[RULE]:return None
    dt=st['decision_t']
    if tr.exit_t<=dt:return None
    return (dt,RULE,f517.NOTIONAL*(float(st['decision_open'])/tr.entry-1.0)-f517.ROUND_TRIP_FEE)


def apply(k,t,tr,st):
    # Compete only with the actually frozen four-layer stack.
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
        frozen=f620.frozen_events(k,t,tr)
        if frozen:
            base_dt,base_layer,base_pnl=frozen[0]
        else:
            base_dt,base_layer,base_pnl=None,'PARENT',float(tr.pnl)
        st=state(k,tr)
        pnl,layer,dt=apply(k,t,tr,st)
        row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),
             'frozen_pnl':float(base_pnl),'frozen_layer':base_layer,
             'managed_pnl':pnl,'managed_layer':layer,'incremental':pnl-float(base_pnl)}
        if st is not None:
            row.update({
                'f622_signal':bool(st[f622.RULE]),
                'pre120_entry_range_pos':float(st['pre120_entry_range_pos']),
                'upper_half_2h':bool(st['upper_half_2h']),
                'ema20_reclaims':int(st['ema20_reclaims']),
                'no_ema20_reclaim':bool(st['no_ema20_reclaim']),
                'tail2_taker_mean':float(st['tail2_taker_mean']),
                'signal':bool(st[RULE]),
                'decision_t':str(st['decision_t'])})
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f624_rows.csv',index=False)

    parent_m=metrics(df.parent_pnl); base_m=metrics(df.frozen_pnl); m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-123.232)>0.10 or abs(base_m['wr']*100-51.45)>0.08:
        raise AssertionError(f'frozen stack parity mismatch {base_m}')

    acts=df[df.managed_layer==RULE].copy()
    d=df[df.i<f517.SPLIT_N]; v=df[df.i>=f517.SPLIT_N]
    low=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r>=.5)&(acts.parent_mfe_r<1)]
    high=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r>=1)&(acts.parent_mfe_r<2)]
    inc=float(m['pnl']-base_m['pnl']); incD=float(d.incremental.sum()); incV=float(v.incremental.sum())
    loss_pos=int(((acts.parent_pnl<=0)&(acts.managed_pnl>0)).sum())
    win_nonpos=int(((acts.parent_pnl>0)&(acts.managed_pnl<=0)).sum())
    winner_acted=int((acts.parent_pnl>0).sum())
    # Same conservative promotion gate used in recent Friday management research.
    screen=bool(inc>0 and incD>=0 and incV>=0 and len(low)>0 and win_nonpos==0 and
                m['wr']>=base_m['wr'] and m['dd']<=base_m['dd']+1e-9)

    # Diagnostic funnel from F6.22 -> upper-half -> no-repair -> active action.
    eligible=df[df.f622_signal==True].copy() if 'f622_signal' in df.columns else df.iloc[0:0]
    funnel={
      'f622_signals':int(len(eligible)),
      'upper_half':int((eligible.upper_half_2h==True).sum()) if len(eligible) else 0,
      'no_ema20_reclaim':int((eligible.no_ema20_reclaim==True).sum()) if len(eligible) else 0,
      'both_context_repair':int(((eligible.upper_half_2h==True)&(eligible.no_ema20_reclaim==True)).sum()) if len(eligible) else 0,
      'active_actions_after_chronology':int(len(acts)),
    }

    out={
      'rule_definition':{
        'base':'F6.22 bearish persistence at +65m after first +0.5R',
        'context':'strictly pre-entry 2h entry range position > 0.50',
        'repair':'zero EMA20 close reclaims from +0.5R hit through decision',
        'exit':'actual +65m decision open'},
      'parent':parent_m,'frozen_four_layer':base_m,'managed':m,'funnel':funnel,
      'actions':int(len(acts)),'actions_D':int((acts.i<f517.SPLIT_N).sum()),'actions_V':int((acts.i>=f517.SPLIT_N).sum()),
      'parent_winners_acted':winner_acted,'parent_losses_acted':int((acts.parent_pnl<=0).sum()),
      'low_givebacks_acted':int(len(low)),'high_givebacks_acted':int(len(high)),
      'loss_to_positive':loss_pos,'winner_to_nonpositive':win_nonpos,
      'positive_increment_actions':int((acts.incremental>0).sum()),'negative_increment_actions':int((acts.incremental<0).sum()),
      'incremental_vs_frozen':inc,'incremental_D':incD,'incremental_V':incV,
      'wr_gain_pp':float((m['wr']-base_m['wr'])*100),'dd_improvement':float(base_m['dd']-m['dd']),
      'screen_pass':screen,
      'action_dates':acts[['date','period','parent_pnl','parent_mfe_r','frozen_pnl','managed_pnl','incremental','pre120_entry_range_pos','ema20_reclaims','tail2_taker_mean']].to_dict('records') if len(acts) else []}
    (OUT/'f624_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.24 — CONTEXT_REPAIR_FAILURE_65 Management','',
        '**Status: COMPLETE — single predeclared causal action test. Live BBC untouched.**','',
        '## Frozen rule',
        '- first causal +0.5R milestone',
        '- evaluate exactly +65m later',
        '- F6.22 bearish persistence: final 4 completed 5m closes below EMA7 + final-2 taker mean < 0',
        '- strictly pre-entry 2h entry position > 50% of local range',
        '- zero EMA20 reclaims from first +0.5R hit to decision',
        '- exit at actual decision open',
        '- no timing / taker / range-position / EMA-distance sweep','',
        '## Baseline',f"Frozen four-layer: **{base_m['pnl']:+.3f}**, WR **{base_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f}**, DD **{base_m['dd']:.3f}**.",'',
        '## Funnel',f"- F6.22 raw signals **{funnel['f622_signals']}**",f"- upper-half context **{funnel['upper_half']}**",f"- zero EMA20 reclaim **{funnel['no_ema20_reclaim']}**",f"- both context+repair conditions **{funnel['both_context_repair']}**",f"- active after chronology **{len(acts)}**",'',
        '## Result',f"- actions **{len(acts)}** (D {(acts.i<f517.SPLIT_N).sum()} / V {(acts.i>=f517.SPLIT_N).sum()})",f"- low givebacks caught **{len(low)}**; high givebacks caught **{len(high)}**; eventual winners acted **{winner_acted}**",f"- loss→positive **{loss_pos}**; winner→nonpositive **{win_nonpos}**",f"- incremental **{inc:+.3f}**; D/V **{incD:+.3f} / {incV:+.3f}**",f"- managed PnL **{m['pnl']:+.3f}**, WR **{m['wr']*100:.2f}%**, PF **{m['pf']:.3f}**, DD **{m['dd']:.3f}**",f"- screen **{'PASS' if screen else 'FAIL'}**",'',
        '## Guardrail','F6.24 is same-sample provisional because the state was motivated by F6.23 on the same history. Do not retune the 50% half-range split, EMA20-reclaim definition, flow window, or +65m timing on this sample. A PASS still requires independent OOS trigger evidence.']
    (OUT/'F6.24_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
