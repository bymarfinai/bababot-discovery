#!/usr/bin/env python3
"""F6.32 — Friday conditional recovery window after F6.31 flow divergence.

Research only; live BBC untouched. Frozen Friday stack remains unchanged:
FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31 remain failed same-sample diagnostics and are NOT frozen.

ONE predeclared sequential architecture; no threshold/timing sweep:
  CONDITIONAL_RECOVERY_WINDOW_30
  1) F6.29 CONTEXT_RECOVERY_FAIL_20 would cut at +20m;
  2) if F6.31 natural flow-divergence guard is absent, retain F6.29 +20m cut;
  3) if guard is present, defer the +20m cut and open a maximum 10m grace window;
  4) at +25m, if a natural recovery chain is present (EMA7 has reclaimed,
     current close is above EMA7, current close > prior close, current low >
     prior low), release the trade back to frozen five-layer management;
  5) otherwise continue WATCH to +30m; if that same recovery chain is present
     at +30m, release back to frozen management; if not, exit at actual +30m open;
  6) any parent/frozen exit occurring before a pending checkpoint has priority.

All conditions are natural inequalities/EMA state. There is no fitted magnitude
threshold and +25/+30 are fixed sequential checkpoints, not alternatives chosen
post hoc. This remains same-sample economic diagnostics only.
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
import f628_friday_recovery_sequence_10_30_forensic as f628
import f629_friday_context_recovery_fail20_management as f629
import f631_friday_flow_reversal_recovery_guard as f631

OUT=Path(os.getenv('F632_OUT','f632_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
RULE='CONDITIONAL_RECOVERY_WINDOW_30'


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


def chain_state(k,t,tr,m):
    """Natural recovery-chain state strictly known at t+m decision open."""
    z=f628.seq_features(k,t,tr,m)
    if not z.get('alive',False): return {'alive':False}
    return {
      'alive':True,
      'recovery_chain':bool(z['recovery_chain_now']>0.5),
      'above_ema7':bool(z['current_above_ema7']>0.5),
      'higher_close':bool(z['current_higher_close']>0.5),
      'higher_low':bool(z['current_higher_low']>0.5),
      'ema7_reclaim_any':bool(z['ema7_reclaim_any']>0.5),
      'progress_r':float(z['progress_r']),
      'cum_taker_after10':float(z['cum_taker_after10']),
    }


def pending_alive(tr,base_dt,dt):
    if pd.Timestamp(tr.exit_t)<=dt:return False
    if base_dt is not None and pd.Timestamp(base_dt)<=dt:return False
    return True


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
        f629_action=False; f629_pnl=float(base_pnl)
        gs=f631.guard_state(k,t,tr) if watch_active else None
        guarded=False
        if st is not None and st[f629.RULE]:
            dt20=st['decision_t']
            if base_dt is None or dt20<pd.Timestamp(base_dt):
                f629_action=True
                f629_pnl=float(f616.cut_pnl(float(tr.entry),float(st['decision_open'])))
                guarded=bool(gs is not None and gs[f631.RULE])

        # F6.31 reference: guard means revert fully to baseline; otherwise F6.29 cut.
        f631_pnl=float(base_pnl) if (f629_action and guarded) else f629_pnl

        managed=float(base_pnl)
        action='BASE'
        confirm25=False; confirm30=False; cut30=False; frozen_during_grace=False
        s25=None; s30=None

        if f629_action and not guarded:
            managed=f629_pnl; action='CUT20'
        elif f629_action and guarded:
            dt25=t+pd.Timedelta(minutes=25)
            if not pending_alive(tr,base_dt,dt25):
                managed=float(base_pnl); action='FROZEN_BEFORE25'; frozen_during_grace=True
            else:
                s25=chain_state(k,t,tr,25)
                if s25.get('alive',False) and s25['recovery_chain']:
                    managed=float(base_pnl); action='CONFIRM25_HOLD'; confirm25=True
                else:
                    dt30=t+pd.Timedelta(minutes=30)
                    if not pending_alive(tr,base_dt,dt30):
                        managed=float(base_pnl); action='FROZEN_25_30'; frozen_during_grace=True
                    else:
                        s30=chain_state(k,t,tr,30)
                        if s30.get('alive',False) and s30['recovery_chain']:
                            managed=float(base_pnl); action='CONFIRM30_HOLD'; confirm30=True
                        else:
                            managed=float(f616.cut_pnl(float(tr.entry),float(k.loc[dt30,'open'])))
                            action='CUT30'; cut30=True

        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'base_dt':None if base_dt is None else str(base_dt),
             'watch_active':watch_active,'f629_action':f629_action,'f629_pnl':f629_pnl,'guarded20':guarded,'f631_pnl':f631_pnl,
             'managed_pnl':managed,'action':action,'confirm25':confirm25,'confirm30':confirm30,'cut30':cut30,
             'frozen_during_grace':frozen_during_grace,'incremental_vs_base':managed-float(base_pnl),
             'incremental_vs_f629':managed-f629_pnl,'incremental_vs_f631':managed-f631_pnl}
        if gs is not None:
            row.update({'new_lower_low20':bool(gs['new_lower_low']),'taker_improves20':bool(gs['taker_improves']),
                        'taker_change20':float(gs['taker_change'])})
        if s25 is not None and s25.get('alive',False):
            row.update({f'cp25_{kk}':vv for kk,vv in s25.items() if kk!='alive'})
        if s30 is not None and s30.get('alive',False):
            row.update({f'cp30_{kk}':vv for kk,vv in s30.items() if kk!='alive'})
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT/'f632_rows.csv',index=False)
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

    c25=guarded[guarded.confirm25].copy(); c30=guarded[guarded.confirm30].copy(); ccut=guarded[guarded.cut30].copy(); fg=guarded[guarded.frozen_during_grace].copy()
    unguarded=acts[~acts.guarded20].copy()
    inc=float(managed_m['pnl']-base_m['pnl']); inc629=float(managed_m['pnl']-f629_m['pnl']); inc631=float(managed_m['pnl']-f631_m['pnl'])
    d=df[df.i<SPLIT];v=df[df.i>=SPLIT]
    incD=float(d.incremental_vs_base.sum());incV=float(v.incremental_vs_base.sum())
    delta629D=float(d.incremental_vs_f629.sum());delta629V=float(v.incremental_vs_f629.sum())
    delta631D=float(d.incremental_vs_f631.sum());delta631V=float(v.incremental_vs_f631.sum())

    baseline_pos_nonpos=int(((df.base_pnl>0)&(df.managed_pnl<=0)).sum())
    parent_winners_preserved=int(((acts.parent_pnl>0)&(df.loc[acts.index,'managed_pnl']>0)).sum())
    parent_winners_acted=int((acts.parent_pnl>0).sum())
    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<.5)&(df.base_layer=='PARENT')]
    defensive=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r<.5)&(acts.base_layer=='PARENT')&
                   ((acts.action=='CUT20')|(acts.action=='CUT30'))]
    saved_on_losers=float(acts.loc[acts.parent_pnl<=0,'incremental_vs_base'].sum())
    damage_on_winners=float(acts.loc[acts.parent_pnl>0,'incremental_vs_base'].sum())
    jack=[float(inc-r.incremental_vs_base) for _,r in acts.iterrows() if abs(r.incremental_vs_base)>1e-12]

    screen=bool(inc>0 and incD>=0 and incV>=0 and baseline_pos_nonpos==0 and managed_m['wr']>=base_m['wr'] and
                managed_m['dd']<=base_m['dd']+1e-9 and managed_m['pnl']>=f629_m['pnl']-1e-9)
    out={
      'status':'SAME_SAMPLE_DIAGNOSTIC_ONLY',
      'rule_definition':{
        'candidate':'F6.29 +20m cut candidate',
        'guard20':'F6.31 lower-low + improving-taker divergence',
        'grace':'guarded cases defer cut for max 10m',
        'confirm25':'EMA7 recovery_chain_now at +25m -> frozen HOLD',
        'confirm30':'if not confirmed at +25m, same recovery_chain_now at +30m -> frozen HOLD',
        'fail30':'if still unconfirmed/alive at +30m -> actual +30m-open cut',
        'priority':'parent/frozen exit before checkpoint wins','tuning':'none; fixed sequential +25/+30 natural-state checkpoints'},
      'frozen_five_layer':base_m,'f629_diagnostic':f629_m,'f631_guard':f631_m,'conditional_window':managed_m,
      'active_watches':int(len(watches)),'f629_actions':int(len(acts)),'guarded20':int(len(guarded)),'unguarded_cut20':int(len(unguarded)),
      'confirm25':int(len(c25)),'confirm30':int(len(c30)),'cut30':int(len(ccut)),'frozen_during_grace':int(len(fg)),
      'guarded_winner_n':int((guarded.parent_pnl>0).sum()),'guarded_loser_n':int((guarded.parent_pnl<=0).sum()),
      'confirm25_winner_loser':[int((c25.parent_pnl>0).sum()),int((c25.parent_pnl<=0).sum())],
      'confirm30_winner_loser':[int((c30.parent_pnl>0).sum()),int((c30.parent_pnl<=0).sum())],
      'cut30_winner_loser':[int((ccut.parent_pnl>0).sum()),int((ccut.parent_pnl<=0).sum())],
      'parent_winners_acted':parent_winners_acted,'parent_winners_preserved_positive':parent_winners_preserved,
      'failure_to_develop_defensively_cut':int(len(defensive)),'f625_target_n':int(len(target)),
      'saved_on_parent_losers_vs_frozen':saved_on_losers,'damage_on_parent_winners_vs_frozen':damage_on_winners,
      'incremental_vs_frozen':inc,'incremental_vs_f629':inc629,'incremental_vs_f631':inc631,
      'incremental_vs_frozen_D':incD,'incremental_vs_frozen_V':incV,
      'delta_vs_f629_D':delta629D,'delta_vs_f629_V':delta629V,'delta_vs_f631_D':delta631D,'delta_vs_f631_V':delta631V,
      'baseline_positive_to_nonpositive':baseline_pos_nonpos,'wr_gain_pp_vs_frozen':float((managed_m['wr']-base_m['wr'])*100),
      'dd_improvement_vs_frozen':float(base_m['dd']-managed_m['dd']),
      'jackknife_min_remaining_incremental_vs_frozen':float(min(jack)) if jack else np.nan,'screen_pass':screen,
      'guarded_detail':guarded[['date','period','parent_pnl','base_pnl','f629_pnl','f631_pnl','managed_pnl','action','incremental_vs_base','taker_change20']].to_dict('records'),
      'guardrail':'F6.32 is motivated by F6.30/F6.31 on the same sample. D/V are robustness slices only. Do not tune confirmation timing or add magnitude thresholds from this run.'}
    (OUT/'f632_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.32 — Conditional Recovery Window','',
        f"**Diagnostic screen: {'PASS' if screen else 'FAIL'}**",
        '**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**','',
        '## Exact sequential architecture','F6.29 would cut at +20m. If F6.31 lower-low + improving-flow divergence is absent, keep the +20m cut. If divergence exists, defer for max 10m: recovery-chain confirmation at +25m releases to frozen HOLD; otherwise check once more at +30m; if still unconfirmed, cut at actual +30m open.','',
        '## Routing',f"- F6.29 actions **{len(acts)}**; guarded into grace **{len(guarded)}**; immediate +20m cuts **{len(unguarded)}**",f"- +25 confirmations **{len(c25)}**; +30 confirmations **{len(c30)}**; +30 cuts **{len(ccut)}**; frozen exits during grace **{len(fg)}**",f"- +25 confirm winner/loser **{(c25.parent_pnl>0).sum()}/{(c25.parent_pnl<=0).sum()}**",f"- +30 confirm winner/loser **{(c30.parent_pnl>0).sum()}/{(c30.parent_pnl<=0).sum()}**",f"- +30 cut winner/loser **{(ccut.parent_pnl>0).sum()}/{(ccut.parent_pnl<=0).sum()}**",'',
        '## Economics',f"- PnL frozen **{base_m['pnl']:+.3f}** → F6.29 **{f629_m['pnl']:+.3f}** → F6.31 **{f631_m['pnl']:+.3f}** → F6.32 **{managed_m['pnl']:+.3f}**",f"- incremental vs frozen **{inc:+.3f}**; vs F6.29 **{inc629:+.3f}**; vs F6.31 **{inc631:+.3f}**",f"- D/V vs frozen **{incD:+.3f} / {incV:+.3f}**",f"- WR **{base_m['wr']*100:.2f}% → {managed_m['wr']*100:.2f}%**; PF **{base_m['pf']:.3f} → {managed_m['pf']:.3f}**; DD **{base_m['dd']:.3f} → {managed_m['dd']:.3f}**",f"- baseline positive→nonpositive **{baseline_pos_nonpos}**; parent winners preserved positive **{parent_winners_preserved}/{parent_winners_acted}**",f"- failure-to-develop defensively cut **{len(defensive)}/{len(target)}**",'',
        '## Guardrail','This is still same-sample architecture research. Do not retune +25/+30, EMA7, higher-close/higher-low definition, or add flow-magnitude thresholds based on this result.']
    (OUT/'F6.32_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
