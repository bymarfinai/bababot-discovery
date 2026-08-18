#!/usr/bin/env python3
"""F6.31 — Friday flow-reversal recovery guard on F6.29 +20m cut.

Research only; live BBC untouched. Frozen Friday stack remains unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29 remains a FAILED same-sample diagnostic and is NOT frozen.

ONE predeclared natural-state protection, no threshold/timing sweep:
  FLOW_REVERSAL_GUARD_20
  1) F6.29 CONTEXT_RECOVERY_FAIL_20 would cut at +20m;
  2) inspect only the two completed post-WATCH bars: b3 (+10->15m)
     and b4 (+15->20m);
  3) price makes a fresh lower low on b4 vs b3 (b4.low < b3.low), while
     taker imbalance improves on b4 vs b3 (b4.taker_imb > b3.taker_imb);
  4) this price/flow divergence PROTECTS the trade from the +20m cut and
     returns management to the frozen five-layer baseline; otherwise the
     original F6.29 +20m cut is retained.

The rule uses only natural inequalities (new low, improving flow). No fitted
magnitude threshold, no alternate time, and no later-path information.
Because F6.30 was generated from the same sample, this is still a same-sample
economic diagnostic and cannot be auto-promoted even if it passes.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f629_friday_context_recovery_fail20_management as f629

OUT=Path(os.getenv('F631_OUT','f631_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='FLOW_REVERSAL_GUARD_20'


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


def guard_state(k,t,tr):
    """Strictly causal natural price/flow divergence known at +20m open."""
    dt=t+pd.Timedelta(minutes=20)
    if dt not in k.index or pd.Timestamp(tr.exit_t)<=dt:return None
    bars=k[(k.index>=t)&(k.index<dt)]
    if len(bars)!=4:return None
    b3,b4=bars.iloc[2],bars.iloc[3]
    new_lower_low=bool(float(b4.low)<float(b3.low))
    taker_improves=bool(float(b4.taker_imb)>float(b3.taker_imb))
    return {
      'decision_t':dt,
      'b3_low':float(b3.low),'b4_low':float(b4.low),
      'b3_taker':float(b3.taker_imb),'b4_taker':float(b4.taker_imb),
      'new_lower_low':new_lower_low,'taker_improves':taker_improves,
      'taker_change':float(b4.taker_imb-b3.taker_imb),
      RULE:bool(new_lower_low and taker_improves),
    }


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr)
        bst=f624.state(k,tr); base_pnl,base_layer,base_dt=f624.apply(k,t,tr,bst)
        watch=f626.failed_launch_state(k,t,tr)
        watch_active=False
        if watch is not None and watch[f626.RULE]:
            watch_active=bool(base_dt is None or watch['decision_t']<pd.Timestamp(base_dt))

        st=f629.candidate_state(k,t,tr) if watch_active else None
        f629_action=False; f629_pnl=float(base_pnl); f631_pnl=float(base_pnl); guard=False
        gs=guard_state(k,t,tr) if watch_active else None
        if st is not None and st[f629.RULE]:
            dt=st['decision_t']
            if base_dt is None or dt<pd.Timestamp(base_dt):
                f629_action=True
                f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
                guard=bool(gs is not None and gs[RULE])
                f631_pnl=float(base_pnl) if guard else f629_pnl

        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'watch_active':watch_active,
             'f629_action':f629_action,'f629_pnl':f629_pnl,'guard':guard,'managed_pnl':f631_pnl,
             'incremental_vs_base':f631_pnl-float(base_pnl),'incremental_vs_f629':f631_pnl-f629_pnl}
        if st is not None:
            row.update({'f629_raw_signal':bool(st[f629.RULE]),'progress20_r':float(st['progress20_r']),
                        'cum_taker_after10':float(st['cum_taker_after10'])})
        if gs is not None:
            row.update({'new_lower_low':bool(gs['new_lower_low']),'taker_improves':bool(gs['taker_improves']),
                        'b3_taker':float(gs['b3_taker']),'b4_taker':float(gs['b4_taker']),'taker_change':float(gs['taker_change'])})
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT/'f631_rows.csv',index=False)
    base_m=metrics(df.base_pnl); f629_m=metrics(df.f629_pnl); managed_m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'latest five-layer parity fail {base_m}')
    if abs(f629_m['pnl']-147.5396282208)>0.10 or f629_m['wins']!=70:
        raise RuntimeError(f'F6.29 parity fail {f629_m}')

    watches=df[df.watch_active].copy(); acts=df[df.f629_action].copy(); guards=acts[acts.guard].copy(); cuts=acts[~acts.guard].copy()
    if len(watches)!=26 or len(acts)!=12:raise RuntimeError(f'watch/action parity {len(watches)}/{len(acts)}')
    fw=acts[acts.parent_pnl>0]; losses=acts[acts.parent_pnl<=0]
    if (len(fw),len(losses))!=(3,9):raise RuntimeError(f'F6.29 cohort parity {len(fw)}/{len(losses)}')

    # Exact guard rates on the F6.29 action set and the broader F6.27-style cross-control.
    false_winner_guard_rate=float(fw.guard.mean()) if len(fw) else np.nan
    cut_loss_guard_rate=float(losses.guard.mean()) if len(losses) else np.nan
    ext_win=watches[watches.parent_pnl>0].copy()
    ext_dead=watches[(watches.parent_pnl<=0)&(watches.parent_mfe_r<.5)&(watches.base_layer=='PARENT')].copy()
    if (len(ext_win),len(ext_dead))!=(13,9):raise RuntimeError(f'external cohort parity {len(ext_win)}/{len(ext_dead)}')
    # guard_state exists for every active +20m-alive WATCH in this cohort; natural state evaluated irrespective of F6.29 context.
    ext_win_guard=((ext_win.new_lower_low==True)&(ext_win.taker_improves==True))
    ext_dead_guard=((ext_dead.new_lower_low==True)&(ext_dead.taker_improves==True))
    ext_win_guard_rate=float(ext_win_guard.mean())
    ext_dead_guard_rate=float(ext_dead_guard.mean())

    inc_base=float(managed_m['pnl']-base_m['pnl'])
    inc_f629=float(managed_m['pnl']-f629_m['pnl'])
    d=df[df.i<SPLIT];v=df[df.i>=SPLIT]
    incD=float(d.incremental_vs_base.sum());incV=float(v.incremental_vs_base.sum())
    deltaD=float(d.incremental_vs_f629.sum());deltaV=float(v.incremental_vs_f629.sum())
    winner_restored=int(((guards.parent_pnl>0)&(guards.base_pnl>0)&(guards.f629_pnl<=0)).sum())
    guarded_winners=int((guards.parent_pnl>0).sum());guarded_losses=int((guards.parent_pnl<=0).sum())
    remaining_winner_damage=float(cuts.loc[cuts.parent_pnl>0,'f629_pnl'].sum()-cuts.loc[cuts.parent_pnl>0,'base_pnl'].sum()) if len(cuts[cuts.parent_pnl>0]) else 0.0
    restored_winner_value=float(guards.loc[guards.parent_pnl>0,'incremental_vs_f629'].sum()) if guarded_winners else 0.0
    forfeited_loser_savings=float(guards.loc[guards.parent_pnl<=0,'incremental_vs_f629'].sum()) if guarded_losses else 0.0
    baseline_pos_nonpos=int(((df.base_pnl>0)&(df.managed_pnl<=0)).sum())
    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<.5)&(df.base_layer=='PARENT')]
    caught=cuts[(cuts.parent_pnl<=0)&(cuts.parent_mfe_r<.5)&(cuts.base_layer=='PARENT')]
    jack=[float(inc_base-r.incremental_vs_base) for _,r in cuts.iterrows() if abs(r.incremental_vs_base)>1e-12]

    screen=bool(inc_base>0 and incD>=0 and incV>=0 and baseline_pos_nonpos==0 and
                managed_m['wr']>=base_m['wr'] and managed_m['dd']<=base_m['dd']+1e-9 and guarded_winners>0)
    out={
      'status':'SAME_SAMPLE_DIAGNOSTIC_ONLY',
      'rule_definition':{
        'parent_candidate':'F6.29 CONTEXT_RECOVERY_FAIL_20 would cut at +20m',
        'guard':'b4 (+15→20m) makes lower low vs b3 (+10→15m) AND b4 taker imbalance > b3 taker imbalance',
        'guard_action':'do NOT take F6.29 +20m cut; revert to frozen five-layer management',
        'otherwise':'retain F6.29 actual +20m-open cut','tuning':'none; natural inequalities only'},
      'frozen_five_layer':base_m,'f629_diagnostic':f629_m,'guarded_management':managed_m,
      'active_watches':int(len(watches)),'f629_actions':int(len(acts)),'guarded_actions':int(len(guards)),'remaining_cuts':int(len(cuts)),
      'guarded_winners':guarded_winners,'guarded_losses':guarded_losses,'winner_restored_to_positive':winner_restored,
      'false_winner_guard_rate':false_winner_guard_rate,'cut_loss_guard_rate':cut_loss_guard_rate,
      'external_future_winner_guard_rate':ext_win_guard_rate,'external_true_dead_guard_rate':ext_dead_guard_rate,
      'restored_winner_value_vs_f629':restored_winner_value,'forfeited_loser_savings_vs_f629':forfeited_loser_savings,
      'remaining_winner_damage_vs_base':remaining_winner_damage,
      'incremental_vs_frozen':inc_base,'incremental_vs_f629':inc_f629,
      'incremental_vs_frozen_D':incD,'incremental_vs_frozen_V':incV,'delta_vs_f629_D':deltaD,'delta_vs_f629_V':deltaV,
      'failure_to_develop_still_cut':int(len(caught)),'f625_target_n':int(len(target)),
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,
      'wr_gain_pp_vs_frozen':float((managed_m['wr']-base_m['wr'])*100),'dd_improvement_vs_frozen':float(base_m['dd']-managed_m['dd']),
      'jackknife_min_remaining_incremental_vs_frozen':float(min(jack)) if jack else np.nan,'screen_pass':screen,
      'guard_detail':guards[['date','period','parent_pnl','base_pnl','f629_pnl','managed_pnl','incremental_vs_f629','new_lower_low','taker_improves','b3_taker','b4_taker','taker_change']].to_dict('records') if len(guards) else [],
      'remaining_cut_detail':cuts[['date','period','parent_pnl','base_pnl','f629_pnl','incremental_vs_base','new_lower_low','taker_improves','taker_change']].to_dict('records') if len(cuts) else [],
      'guardrail':'F6.30 informed this exact natural state on the same sample. D/V are robustness slices only, not untouched validation. No auto-promotion.'}
    (OUT/'f631_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.31 — Flow-Reversal Recovery Guard','',
        f"**Diagnostic screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact predeclared guard','When F6.29 would cut at +20m, protect/HOLD instead iff the +15→20m bar makes a fresh lower low versus +10→15m while taker imbalance improves. This is a natural price/flow divergence; no fitted magnitude threshold.','',
        '## Guard selectivity',f"- F6.29 false winners guarded **{guarded_winners}/3 ({100*false_winner_guard_rate:.1f}%)**",f"- F6.29 cut-losers guarded **{guarded_losses}/9 ({100*cut_loss_guard_rate:.1f}%)**",f"- broader 13 winner / 9 true-dead guard rate **{100*ext_win_guard_rate:.1f}% / {100*ext_dead_guard_rate:.1f}%**",'',
        '## Economics',f"- frozen PnL **{base_m['pnl']:+.3f}** → F6.29 **{f629_m['pnl']:+.3f}** → guarded **{managed_m['pnl']:+.3f}**",f"- incremental vs frozen **{inc_base:+.3f}**; vs F6.29 **{inc_f629:+.3f}**",f"- D/V incremental vs frozen **{incD:+.3f} / {incV:+.3f}**",f"- WR **{base_m['wr']*100:.2f}% → {managed_m['wr']*100:.2f}%**; PF **{base_m['pf']:.3f} → {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} → {managed_m['dd']:.3f}**",f"- baseline positive→nonpositive **{baseline_pos_nonpos}**; winner restored to positive **{winner_restored}**",f"- failure-to-develop still cut **{len(caught)}/{len(target)}**",'',
        '## Guardrail','This exact guard was motivated by F6.30 on the same sample. A PASS means the architecture is economically promising, not validated. Do not tune the divergence magnitude or timing on this sample.']
    (OUT/'F6.31_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
