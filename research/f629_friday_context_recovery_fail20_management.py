#!/usr/bin/env python3
"""F6.29 — Friday context-conditioned adaptive small-loss management.

Research only; live BBC untouched. Frozen Friday layers remain unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.

ONE predeclared diagnostic rule, no timing/threshold sweep:
  CONTEXT_RECOVERY_FAIL_20
  1) F6.26 FAILED_LAUNCH_10 fires at +10m, but +10m is WATCH only;
  2) the completed 5m candle immediately before entry was red (natural boolean
     pre-entry context highlighted by F6.27; no fitted body/wick threshold);
  3) from +10m through +20m, no completed 5m close has reclaimed EMA7
     (the strongest early recovery-persistence clue in F6.28);
  4) if still alive and no frozen layer exited earlier, exit at actual +20m open.

This is a same-sample economic diagnostic. F6.27/F6.28 inspected both chronology
periods, so D/V here are stability slices, NOT untouched out-of-sample validation.
No rule is promoted automatically.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f624_friday_context_repair_failure_management as f624
import f625_friday_failure_to_develop_forensic as f625
import f626_friday_failed_launch10_management as f626
import f628_friday_recovery_sequence_10_30_forensic as f628

OUT=Path(os.getenv('F629_OUT','f629_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='CONTEXT_RECOVERY_FAIL_20'


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


def candidate_state(k,t,tr):
    watch=f626.failed_launch_state(k,t,tr)
    if watch is None or not watch[f626.RULE]: return None
    dt=t+pd.Timedelta(minutes=20)
    if dt not in k.index or pd.Timestamp(tr.exit_t)<=dt: return None
    ctx=f625.pre_context_extra(k,t,tr)
    seq=f628.seq_features(k,t,tr,20)
    if not seq.get('alive',False): return None
    pre_last_red=bool(ctx['pre_last_red']>0.5)
    no_ema7_reclaim=bool(seq['ema7_reclaim_any']<0.5)
    signal=bool(pre_last_red and no_ema7_reclaim)
    return {'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
            'pre_last_red':pre_last_red,'no_ema7_reclaim_10_20':no_ema7_reclaim,
            'ema7_failure_share':float(seq['ema7_failure_share']),
            'progress20_r':float(seq['progress_r']),'cum_taker_after10':float(seq['cum_taker_after10']),RULE:signal}


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        bst=f624.state(k,tr); base_pnl,base_layer,base_dt=f624.apply(k,t,tr,bst)
        watch=f626.failed_launch_state(k,t,tr)
        watch_active=False
        if watch is not None and watch[f626.RULE]:
            watch_active=bool(base_dt is None or watch['decision_t']<pd.Timestamp(base_dt))
        st=candidate_state(k,t,tr) if watch_active else None
        managed=float(base_pnl); layer=base_layer; action=False
        if st is not None and st[RULE]:
            dt=st['decision_t']
            if base_dt is None or dt<pd.Timestamp(base_dt):
                managed=float(f616.cut_pnl(float(tr.entry),float(st['decision_open']))); layer=RULE; action=True
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'base_dt':None if base_dt is None else str(base_dt),
             'watch_active':watch_active,'managed_pnl':managed,'managed_layer':layer,'incremental':managed-float(base_pnl),'active_action':action}
        if st is not None:
            row.update({'raw_signal':bool(st[RULE]),'decision_t':str(st['decision_t']),'pre_last_red':st['pre_last_red'],
                        'no_ema7_reclaim_10_20':st['no_ema7_reclaim_10_20'],'ema7_failure_share':st['ema7_failure_share'],
                        'progress20_r':st['progress20_r'],'cum_taker_after10':st['cum_taker_after10']})
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f629_rows.csv',index=False)
    parent_m=metrics(df.parent_pnl); base_m=metrics(df.base_pnl); managed_m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'latest five-layer parity fail {base_m}')
    watches=df[df.watch_active].copy()
    if len(watches)!=26: raise RuntimeError(f'F6.26 active WATCH parity fail {len(watches)}')
    raw=df[df.raw_signal==True].copy() if 'raw_signal' in df.columns else df.iloc[0:0]
    acts=df[df.active_action].copy()
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<0.5)&(df.base_layer=='PARENT')].copy()
    caught=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r<0.5)&(acts.base_layer=='PARENT')]
    inc=float(managed_m['pnl']-base_m['pnl']); incD=float(d.incremental.sum()); incV=float(v.incremental.sum())
    winner_acted=int((acts.parent_pnl>0).sum()); loss_acted=int((acts.parent_pnl<=0).sum())
    baseline_pos_nonpos=int(((acts.base_pnl>0)&(acts.managed_pnl<=0)).sum())
    parent_win_nonpos=int(((acts.parent_pnl>0)&(acts.managed_pnl<=0)).sum())
    loss_to_positive=int(((acts.parent_pnl<=0)&(acts.managed_pnl>0)).sum())
    saved_on_losers=float(acts.loc[acts.parent_pnl<=0,'incremental'].sum()) if len(acts) else 0.0
    damage_on_winners=float(acts.loc[acts.parent_pnl>0,'incremental'].sum()) if len(acts) else 0.0
    jack=[float(inc-r.incremental) for _,r in acts.iterrows()]
    edges=np.linspace(0,len(df),5,dtype=int); blocks=[]
    for j in range(4):
        g=df.iloc[edges[j]:edges[j+1]]
        blocks.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),'actions':int(g.active_action.sum()),'incremental':float(g.incremental.sum())})
    screen=bool(inc>0 and incD>=0 and incV>=0 and len(caught)>0 and baseline_pos_nonpos==0 and
                managed_m['wr']>=base_m['wr'] and managed_m['dd']<=base_m['dd']+1e-9)
    out={'status':'SAME_SAMPLE_DIAGNOSTIC_ONLY','rule_definition':{
          'watch':'+10m F6.26 FAILED_LAUNCH_10 becomes WATCH only',
          'context':'last completed 5m candle before entry is red',
          'recovery_fail':'no completed post-+10m close reclaims EMA7 by +20m',
          'exit':'actual +20m open if still alive and before any frozen exit','tuning':'none'},
         'parent':parent_m,'frozen_five_layer':base_m,'managed':managed_m,
         'active_watches':int(len(watches)),'raw_signals':int(len(raw)),'active_actions':int(len(acts)),
         'actions_D':int((acts.i<SPLIT).sum()),'actions_V':int((acts.i>=SPLIT).sum()),'preempted_by_frozen':int(len(raw)-len(acts)),
         'f625_target_n':int(len(target)),'failure_to_develop_caught':int(len(caught)),'failure_to_develop_catch_rate':float(len(caught)/len(target)),
         'parent_winners_acted':winner_acted,'parent_losses_acted':loss_acted,'loss_to_positive':loss_to_positive,
         'parent_winner_to_nonpositive':parent_win_nonpos,'baseline_positive_to_nonpositive':baseline_pos_nonpos,
         'saved_on_parent_losers':saved_on_losers,'damage_on_parent_winners':damage_on_winners,
         'incremental_vs_frozen':inc,'incremental_D':incD,'incremental_V':incV,
         'wr_gain_pp':float((managed_m['wr']-base_m['wr'])*100),'dd_improvement':float(base_m['dd']-managed_m['dd']),
         'positive_increment_actions':int((acts.incremental>0).sum()),'negative_increment_actions':int((acts.incremental<0).sum()),
         'jackknife_min_remaining_incremental':float(min(jack)) if jack else np.nan,'blocks4':blocks,'screen_pass':screen,
         'actions_detail':acts[['date','period','parent_pnl','parent_mfe_r','parent_mae_r','base_pnl','base_layer','managed_pnl','incremental','pre_last_red','no_ema7_reclaim_10_20','ema7_failure_share','progress20_r','cum_taker_after10']].to_dict('records') if len(acts) else []}
    (OUT/'f629_summary.json').write_text(json.dumps(out,indent=2,default=str))
    md=['# Friday F6.29 — Context-Conditioned Recovery-Fail +20m Management','',
        f"**Diagnostic screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-sample economic diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact rule','F6.26 at +10m becomes WATCH. At +20m, exit at actual decision open only when the pre-entry last 5m candle was red AND there has been no completed EMA7 reclaim after +10m. Frozen layers keep priority if they exited earlier.','',
        '## Frozen parity',f"- five-layer PnL **{base_m['pnl']:+.3f}**, WR **{base_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f}**, DD **{base_m['dd']:.3f}**",'',
        '## Result',f"- active WATCH cohort **{len(watches)}**; raw/action signals **{len(raw)} / {len(acts)}**; D/V actions **{(acts.i<SPLIT).sum()} / {(acts.i>=SPLIT).sum()}**",f"- parent winners/losses acted **{winner_acted} / {loss_acted}**",f"- F6.25 failure-to-develop caught **{len(caught)}/{len(target)} ({100*len(caught)/len(target):.1f}%)**",f"- loser savings **{saved_on_losers:+.3f}**; winner damage **{damage_on_winners:+.3f}**",f"- incremental **{inc:+.3f}**; D/V **{incD:+.3f} / {incV:+.3f}**",f"- PnL **{base_m['pnl']:+.3f} -> {managed_m['pnl']:+.3f}**; WR **{base_m['wr']*100:.2f}% -> {managed_m['wr']*100:.2f}%**",f"- PF **{base_m['pf']:.3f} -> {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} -> {managed_m['dd']:.3f}**",f"- baseline positive→nonpositive **{baseline_pos_nonpos}**; jackknife min remaining incremental **{min(jack) if jack else float('nan'):+.3f}**",'',
        '## Guardrail','Because F6.27/F6.28 used both chronology slices during forensic selection, D/V here are robustness slices, not untouched validation. Do not tune timing or add body/wick/taker thresholds from this result.']
    (OUT/'F6.29_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
