#!/usr/bin/env python3
"""F6.34 — Friday +35m higher-close continuation management.

Research only; live BBC untouched. Frozen Friday stack remains unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31/F6.32 remain failed same-sample diagnostics and are NOT frozen.

ONE predeclared natural-state rule, motivated by F6.33; no threshold/timing sweep:
  HIGHER_CLOSE_CONTINUATION_35
  1) F6.29 CONTEXT_RECOVERY_FAIL_20 would cut at +20m;
  2) if F6.31 lower-low + improving-taker divergence is absent, retain the
     actual +20m-open cut;
  3) if divergence is present, do NOT use EMA confirmation at +25/+30;
     defer the decision to +35m;
  4) at the actual +35m decision open, inspect only fully completed candles:
     if the +30->35m close is higher than the +25->30m close, release the trade
     back to frozen five-layer management; otherwise cut at the actual +35m open;
  5) any parent/frozen exit at or before +35m has priority.

The confirmation is one natural inequality only. No EMA threshold, taker
magnitude threshold, alternate timing, or post-+35 information is used.
Because F6.33 selected this architecture on the same sample, this is a
same-sample economic diagnostic and cannot auto-promote even if it passes.
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
import f631_friday_flow_reversal_recovery_guard as f631

OUT=Path(os.getenv('F634_OUT','f634_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='HIGHER_CLOSE_CONTINUATION_35'


def metrics(pnls):
    p=np.asarray(pnls,dtype=float); wins=int((p>0).sum())
    gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':wins,'losses':int(len(p)-wins),
            'wr':float(wins/len(p)) if len(p) else np.nan,'pnl':float(p.sum()),
            'pf':float(gp/gl) if gl>0 else math.inf,'dd':dd,'ls':int(ls)}


def continuation35_state(k,t,tr):
    """Strictly causal state known at t+35m open."""
    dt=t+pd.Timedelta(minutes=35)
    if dt not in k.index or pd.Timestamp(tr.exit_t)<=dt:return None
    bars=k[(k.index>=t)&(k.index<dt)]
    if len(bars)!=7:return None
    prev=bars.iloc[-2]   # +25 -> +30
    cur=bars.iloc[-1]    # +30 -> +35
    higher_close=bool(float(cur.close)>float(prev.close))
    return {
      'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
      'prev_close':float(prev.close),'current_close':float(cur.close),
      'higher_close':higher_close,
      'current_green':bool(float(cur.close)>float(cur.open)),
      'current_higher_high':bool(float(cur.high)>float(prev.high)),
      'current_higher_low':bool(float(cur.low)>float(prev.low)),
      'current_taker':float(cur.taker_imb),
      RULE:higher_close,
    }


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

        st=f629.candidate_state(k,t,tr) if watch_active else None
        f629_action=False; f629_pnl=float(base_pnl)
        gs=f631.guard_state(k,t,tr) if watch_active else None
        guarded20=False
        if st is not None and st[f629.RULE]:
            dt20=st['decision_t']
            if base_dt is None or dt20<pd.Timestamp(base_dt):
                f629_action=True
                f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
                guarded20=bool(gs is not None and gs[f631.RULE])

        f631_pnl=float(base_pnl) if (f629_action and guarded20) else f629_pnl
        managed=float(base_pnl); action='BASE'; c35=None

        if f629_action and not guarded20:
            managed=f629_pnl; action='CUT20'
        elif f629_action and guarded20:
            dt35=t+pd.Timedelta(minutes=35)
            # Frozen/parent outcome has priority if already complete by decision time.
            if pd.Timestamp(tr.exit_t)<=dt35 or (base_dt is not None and pd.Timestamp(base_dt)<=dt35):
                managed=float(base_pnl); action='FROZEN_BEFORE35'
            else:
                c35=continuation35_state(k,t,tr)
                if c35 is None: raise RuntimeError(f'missing causal +35 state {tr.date}')
                if c35[RULE]:
                    managed=float(base_pnl); action='CONFIRM35_HOLD'
                else:
                    managed=float(f616.cut_pnl(float(tr.entry),float(c35['decision_open']))); action='CUT35'

        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'base_dt':None if base_dt is None else str(base_dt),
             'watch_active':watch_active,'f629_action':f629_action,'f629_pnl':f629_pnl,
             'guarded20':guarded20,'f631_pnl':f631_pnl,'managed_pnl':managed,'action':action,
             'incremental_vs_base':managed-float(base_pnl),'incremental_vs_f629':managed-f629_pnl,
             'incremental_vs_f631':managed-f631_pnl}
        if gs is not None:
            row.update({'new_lower_low20':bool(gs['new_lower_low']),'taker_improves20':bool(gs['taker_improves']),
                        'taker_change20':float(gs['taker_change'])})
        if c35 is not None:
            row.update({'higher_close35':bool(c35['higher_close']),'current_green35':bool(c35['current_green']),
                        'higher_high35':bool(c35['current_higher_high']),'higher_low35':bool(c35['current_higher_low']),
                        'current_taker35':float(c35['current_taker']),'decision_open35':float(c35['decision_open'])})
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f634_rows.csv',index=False)
    base_m=metrics(df.base_pnl); f629_m=metrics(df.f629_pnl); f631_m=metrics(df.f631_pnl); managed_m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-138.3291316546)>0.10 or base_m['wins']!=73 or base_m['n']!=138:
        raise RuntimeError(f'latest five-layer parity fail {base_m}')
    if abs(f629_m['pnl']-147.5396282208)>0.10 or f629_m['wins']!=70:
        raise RuntimeError(f'F6.29 parity fail {f629_m}')
    if abs(f631_m['pnl']-146.3791787865)>0.10 or f631_m['wins']!=72:
        raise RuntimeError(f'F6.31 parity fail {f631_m}')

    watches=df[df.watch_active].copy(); acts=df[df.f629_action].copy(); guarded=acts[acts.guarded20].copy()
    if len(watches)!=26 or len(acts)!=12 or len(guarded)!=6:
        raise RuntimeError(f'watch/action/guard parity {len(watches)}/{len(acts)}/{len(guarded)}')
    holds=guarded[guarded.action=='CONFIRM35_HOLD'].copy(); cuts35=guarded[guarded.action=='CUT35'].copy(); frozen=guarded[guarded.action=='FROZEN_BEFORE35'].copy()
    cut20=acts[~acts.guarded20].copy()

    inc=float(managed_m['pnl']-base_m['pnl']); inc629=float(managed_m['pnl']-f629_m['pnl']); inc631=float(managed_m['pnl']-f631_m['pnl'])
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    incD=float(d.incremental_vs_base.sum()); incV=float(v.incremental_vs_base.sum())
    delta629D=float(d.incremental_vs_f629.sum()); delta629V=float(v.incremental_vs_f629.sum())
    delta631D=float(d.incremental_vs_f631.sum()); delta631V=float(v.incremental_vs_f631.sum())
    baseline_pos_nonpos=int(((df.base_pnl>0)&(df.managed_pnl<=0)).sum())
    winners=acts[acts.parent_pnl>0]; losses=acts[acts.parent_pnl<=0]
    winners_preserved=int((winners.managed_pnl>0).sum())
    saved_loser=float(losses.incremental_vs_base.sum()); winner_damage=float(winners.incremental_vs_base.sum())
    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<.5)&(df.base_layer=='PARENT')]
    defensive=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r<.5)&(acts.base_layer=='PARENT')&acts.action.isin(['CUT20','CUT35'])]
    jack=[float(inc-r.incremental_vs_base) for _,r in acts.iterrows() if abs(r.incremental_vs_base)>1e-12]

    screen=bool(inc>0 and incD>=0 and incV>=0 and baseline_pos_nonpos==0 and
                managed_m['wr']>=base_m['wr'] and managed_m['dd']<=base_m['dd']+1e-9 and
                managed_m['pnl']>=f629_m['pnl']-1e-9)
    out={'status':'SAME_SAMPLE_DIAGNOSTIC_ONLY',
      'rule_definition':{
        'candidate':'F6.29 +20m cut candidate',
        'guard20':'F6.31 lower-low + improving-taker divergence',
        'unguarded':'retain actual +20m-open cut',
        'guarded':'defer directly to +35m; ignore +25/+30 EMA confirmation',
        'confirm35':'+30->35 close > +25->30 close -> release to frozen HOLD',
        'fail35':'otherwise actual +35m-open cut',
        'priority':'parent/frozen exit at or before +35 wins','tuning':'none; one natural higher-close inequality'},
      'frozen_five_layer':base_m,'f629_diagnostic':f629_m,'f631_guard':f631_m,'f634_management':managed_m,
      'active_watches':int(len(watches)),'f629_actions':int(len(acts)),'guarded20':int(len(guarded)),'immediate_cut20':int(len(cut20)),
      'confirm35_hold':int(len(holds)),'cut35':int(len(cuts35)),'frozen_before35':int(len(frozen)),
      'confirm35_winner_loser':[int((holds.parent_pnl>0).sum()),int((holds.parent_pnl<=0).sum())],
      'cut35_winner_loser':[int((cuts35.parent_pnl>0).sum()),int((cuts35.parent_pnl<=0).sum())],
      'guarded_winner_n':int((guarded.parent_pnl>0).sum()),'guarded_loser_n':int((guarded.parent_pnl<=0).sum()),
      'parent_winners_acted':int(len(winners)),'parent_winners_preserved_positive':winners_preserved,
      'failure_to_develop_defensively_cut':int(len(defensive)),'f625_target_n':int(len(target)),
      'saved_on_parent_losers_vs_frozen':saved_loser,'damage_on_parent_winners_vs_frozen':winner_damage,
      'incremental_vs_frozen':inc,'incremental_vs_f629':inc629,'incremental_vs_f631':inc631,
      'incremental_vs_frozen_D':incD,'incremental_vs_frozen_V':incV,
      'delta_vs_f629_D':delta629D,'delta_vs_f629_V':delta629V,'delta_vs_f631_D':delta631D,'delta_vs_f631_V':delta631V,
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,'wr_gain_pp_vs_frozen':float((managed_m['wr']-base_m['wr'])*100),
      'dd_improvement_vs_frozen':float(base_m['dd']-managed_m['dd']),
      'jackknife_min_remaining_incremental_vs_frozen':float(min(jack)) if jack else np.nan,'screen_pass':screen,
      'guarded_detail':guarded[['date','period','parent_pnl','base_pnl','f629_pnl','f631_pnl','managed_pnl','action','incremental_vs_base','higher_close35','taker_change20']].to_dict('records'),
      'guardrail':'F6.33 selected +35 higher-close on this same sample. D/V are robustness slices only; no auto-promotion and no timing/threshold retuning.'}
    (OUT/'f634_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.34 — +35m Higher-Close Continuation Management','',
        f"**Diagnostic screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact predeclared architecture','F6.29 candidate without F6.31 divergence keeps the +20m cut. Divergence cases wait directly to +35m. If the completed +30→35 candle closes above the +25→30 close, release to frozen HOLD; otherwise cut at the actual +35m open. Frozen/parent exit at or before +35 keeps priority.','',
        '## Routing',f"- F6.29 actions **{len(acts)}**; guarded to +35 **{len(guarded)}**; immediate +20 cuts **{len(cut20)}**",f"- +35 HOLD **{len(holds)}**; +35 cuts **{len(cuts35)}**; frozen before +35 **{len(frozen)}**",f"- +35 HOLD winner/loser **{(holds.parent_pnl>0).sum()} / {(holds.parent_pnl<=0).sum()}**",f"- +35 cut winner/loser **{(cuts35.parent_pnl>0).sum()} / {(cuts35.parent_pnl<=0).sum()}**",'',
        '## Economics',f"- frozen PnL **{base_m['pnl']:+.3f}** → F6.29 **{f629_m['pnl']:+.3f}** → F6.31 **{f631_m['pnl']:+.3f}** → F6.34 **{managed_m['pnl']:+.3f}**",f"- incremental vs frozen **{inc:+.3f}**; vs F6.29 **{inc629:+.3f}**; vs F6.31 **{inc631:+.3f}**",f"- D/V incremental vs frozen **{incD:+.3f} / {incV:+.3f}**",f"- WR **{base_m['wr']*100:.2f}% → {managed_m['wr']*100:.2f}%**; PF **{base_m['pf']:.3f} → {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} → {managed_m['dd']:.3f}**",f"- baseline positive→nonpositive **{baseline_pos_nonpos}**; acted parent winners preserved positive **{winners_preserved}/{len(winners)}**",f"- failure-to-develop defensively cut **{len(defensive)}/{len(target)}**",'',
        '## Guardrail','F6.33 selected this +35 higher-close architecture on the same sample. Even a PASS is architecture evidence, not untouched validation. Do not retune +35 or add magnitude filters from this result.']
    (OUT/'F6.34_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
