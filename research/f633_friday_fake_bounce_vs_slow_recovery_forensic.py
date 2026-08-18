#!/usr/bin/env python3
"""F6.33 — Friday fake-bounce vs slow-recovery forensic, +30m -> +60m.

Research only; live BBC untouched. NO management rule is tuned/promoted.
Frozen Friday stack remains FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29/F6.31/F6.32 remain failed same-sample diagnostics and are NOT frozen.

Question:
F6.32 showed that its +25/+30 EMA7+higher-close+higher-low confirmation was
backwards on the guarded cases: 3 losers confirmed while both guarded winners
were still unconfirmed and got cut at +30m. Do the *subsequent causal paths*
show a difference between fake structural bounce and slow genuine recovery?

Predeclared forensic checkpoints: +35/+40/+45/+50/+55/+60m.
At each checkpoint use only bars closed by that decision-open. Post-+30 data
MUST NOT be used to justify a +30m decision; it can only motivate a later rule.
No timing/threshold/economic sweep and no action is taken in F6.33.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f628_friday_recovery_sequence_10_30_forensic as f628
import f629_friday_context_recovery_fail20_management as f629
import f631_friday_flow_reversal_recovery_guard as f631
import f632_friday_conditional_recovery_window as f632

OUT=Path(os.getenv('F633_OUT','f633_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
CHECKS=(35,40,45,50,55,60)


def _auc_winner_high(w,l,col):
    a=w[col].to_numpy(float); b=l[col].to_numpy(float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    return float(((a[:,None]>b[None,:]).sum()+0.5*(a[:,None]==b[None,:]).sum())/(len(a)*len(b)))


def _sep(w,l,col):
    a=_auc_winner_high(w,l,col)
    return {'strength':float(max(a,1-a)) if np.isfinite(a) else np.nan,
            'direction':'higher=winner' if np.isfinite(a) and a>=.5 else 'lower=winner',
            'winner_median':float(w[col].median()) if len(w) and w[col].notna().any() else np.nan,
            'loss_median':float(l[col].median()) if len(l) and l[col].notna().any() else np.nan,
            'n_winner':int(w[col].notna().sum()),'n_loss':int(l[col].notna().sum())}


def _stat(w,l,col,ew=None,ed=None):
    s=_sep(w,l,col); loo=[]
    for idx in w.index:
        if len(w)>1: loo.append(_sep(w.drop(index=idx),l,col)['strength'])
    for idx in l.index:
        if len(l)>1: loo.append(_sep(w,l.drop(index=idx),col)['strength'])
    ext=None
    if ew is not None and ed is not None and col in ew.columns and col in ed.columns:
        ext=_sep(ew,ed,col)
    return {'feature':col,'subset':s,
            'loo_min_strength':float(np.nanmin(loo)) if loo else np.nan,
            'loo_median_strength':float(np.nanmedian(loo)) if loo else np.nan,
            'external':ext,
            'direction_agrees_external':bool(ext is not None and ext['direction']==s['direction'])}


def pending_alive(tr,base_dt,dt):
    if pd.Timestamp(tr.exit_t)<=dt:return False
    if base_dt is not None and pd.Timestamp(base_dt)<=dt:return False
    return True


def post30_features(k,t,tr,base_dt,m):
    """Strictly causal state at actual t+m decision open."""
    dt=t+pd.Timedelta(minutes=m)
    if dt not in k.index or not pending_alive(tr,base_dt,dt):return {'alive':False}
    z=f628.seq_features(k,t,tr,m)
    if not z.get('alive',False):return {'alive':False}

    allx=k[(k.index>=t)&(k.index<dt)].copy()
    p30=allx[allx.index>=t+pd.Timedelta(minutes=30)].copy()
    if len(p30)!=(m-30)//5 or len(p30)==0:return {'alive':False}
    entry=float(tr.entry)
    close=allx.close.astype(float); low=allx.low.astype(float); high=allx.high.astype(float)
    ema=allx.ema7.astype(float); tak=allx.taker_imb.astype(float)
    hc=close>close.shift(1); hl=low>low.shift(1); hh=high>high.shift(1)
    idx=p30.index
    ema_ok=(close>=ema).loc[idx]; entry_ok=(close>=entry).loc[idx]; flow_ok=(tak>0).loc[idx]
    hc_p=hc.loc[idx];hl_p=hl.loc[idx];hh_p=hh.loc[idx]
    chain=(ema_ok & hc_p & hl_p); full=(chain & flow_ok)

    # Persistence after the first EMA7 reclaim occurring after +30m.
    ema_any=bool(ema_ok.any())
    persistent_ema=False; retest_hold=False; failed_after_reclaim=False
    if ema_any:
        first=ema_ok[ema_ok].index[0]
        tail=ema_ok.loc[first:]
        persistent_ema=bool(tail.all())
        failed_after_reclaim=bool((~tail).any())
        tail_rows=allx.loc[first:]
        if len(tail_rows)>1:
            retest_hold=bool(((tail_rows.low.astype(float)<=tail_rows.ema7.astype(float)) &
                              (tail_rows.close.astype(float)>=tail_rows.ema7.astype(float))).iloc[1:].any())

    entry_any=bool(entry_ok.any())
    persistent_entry=False
    if entry_any:
        firste=entry_ok[entry_ok].index[0]
        persistent_entry=bool(entry_ok.loc[firste:].all())

    flow_any=bool(flow_ok.any()); persistent_flow=False
    if flow_any:
        firstf=flow_ok[flow_ok].index[0]
        persistent_flow=bool(flow_ok.loc[firstf:].all())

    q=float(p30.quote_volume.sum()); tb=float(p30.taker_buy_quote.sum())
    cum_taker=(2*tb/q-1) if q>0 else np.nan
    prev30=k[(k.index>=t+pd.Timedelta(minutes=25))&(k.index<t+pd.Timedelta(minutes=30))]
    ref_low=float(prev30.low.iloc[-1]) if len(prev30)==1 else np.nan
    current=allx.iloc[-1]
    first_tak=float(p30.taker_imb.iloc[0]); cur_tak=float(p30.taker_imb.iloc[-1])

    return {
      'alive':True,
      'progress_r':float(z['progress_r']),'ema7_dist_r':float(z['ema7_dist_r']),
      'cum_taker_after10':float(z['cum_taker_after10']),
      'post30_cum_taker':float(cum_taker),'post30_current_taker':cur_tak,
      'post30_taker_change':cur_tak-first_tak,
      'post30_ema7_hold_share':float(ema_ok.mean()),
      'post30_entry_hold_share':float(entry_ok.mean()),
      'post30_positive_flow_share':float(flow_ok.mean()),
      'post30_higher_close_share':float(hc_p.mean()),
      'post30_higher_low_share':float(hl_p.mean()),
      'post30_higher_high_share':float(hh_p.mean()),
      'post30_chain_share':float(chain.mean()),
      'post30_full_chain_share':float(full.mean()),
      'current_above_ema7':float(bool(ema_ok.iloc[-1])),
      'current_above_entry':float(bool(entry_ok.iloc[-1])),
      'current_flow_positive':float(bool(flow_ok.iloc[-1])),
      'current_higher_close':float(bool(hc_p.iloc[-1])),
      'current_higher_low':float(bool(hl_p.iloc[-1])),
      'current_higher_high':float(bool(hh_p.iloc[-1])),
      'current_chain':float(bool(chain.iloc[-1])),
      'current_full_chain':float(bool(full.iloc[-1])),
      'ema7_reclaim_after30_any':float(ema_any),
      'ema7_persistent_after_reclaim':float(persistent_ema),
      'ema7_failed_after_reclaim':float(failed_after_reclaim),
      'ema7_retest_hold_after_reclaim':float(retest_hold),
      'entry_reclaim_after30_any':float(entry_any),
      'entry_persistent_after_reclaim':float(persistent_entry),
      'flow_positive_after30_any':float(flow_any),
      'flow_persistent_after_turn':float(persistent_flow),
      'fake_bounce_now':float(bool(ema_any and not ema_ok.iloc[-1])),
      'persistent_recovery_now':float(bool(ema_any and persistent_ema and ema_ok.iloc[-1])),
      'persistent_recovery_flow_now':float(bool(ema_any and persistent_ema and ema_ok.iloc[-1] and flow_ok.iloc[-1])),
      'new_low_after30_vs_25_30':float(bool(np.isfinite(ref_low) and float(p30.low.min())<ref_low)),
      'current_green':float(float(current.close)>float(current.open)),
    }


def build_row(k,i,d0):
    t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
    tr=f517.simulate_parent(k,t)
    bst=f624.state(k,tr); base_pnl,base_layer,base_dt=f624.apply(k,t,tr,bst)
    watch=f626.failed_launch_state(k,t,tr)
    watch_active=False
    if watch is not None and watch[f626.RULE]:
        watch_active=bool(base_dt is None or watch['decision_t']<pd.Timestamp(base_dt))
    st=f629.candidate_state(k,t,tr) if watch_active else None
    action29=False
    if st is not None and st[f629.RULE]:
        action29=bool(base_dt is None or st['decision_t']<pd.Timestamp(base_dt))
    gs=f631.guard_state(k,t,tr) if watch_active else None
    guarded=bool(action29 and gs is not None and gs[f631.RULE])

    # Reconstruct F6.32 label for the six guarded cases only.
    f632_action='NA'
    if guarded:
        s25=f632.chain_state(k,t,tr,25) if pending_alive(tr,base_dt,t+pd.Timedelta(minutes=25)) else {'alive':False}
        if s25.get('alive',False) and s25['recovery_chain']:
            f632_action='CONFIRM25_HOLD'
        else:
            s30=f632.chain_state(k,t,tr,30) if pending_alive(tr,base_dt,t+pd.Timedelta(minutes=30)) else {'alive':False}
            if s30.get('alive',False) and s30['recovery_chain']:f632_action='CONFIRM30_HOLD'
            else:f632_action='CUT30'

    row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
         'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
         'base_pnl':float(base_pnl),'base_layer':base_layer,'base_dt':None if base_dt is None else str(base_dt),
         'watch_active':watch_active,'f629_action':action29,'guarded20':guarded,'f632_action':f632_action}
    if guarded:
        row['taker_change20']=float(gs['taker_change'])
    if watch_active:
        for m in CHECKS:
            z=post30_features(k,t,tr,base_dt,m)
            row[f'm{m}_alive']=bool(z.pop('alive'))
            for kk,vv in z.items():row[f'm{m}_{kk}']=vv
    return tr,row


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        tr,row=build_row(k,i,d0);parents.append(tr);rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT/'f633_rows.csv',index=False)
    watches=df[df.watch_active].copy(); guarded=df[df.guarded20].copy()
    if len(watches)!=26 or len(guarded)!=6:raise RuntimeError(f'watch/guard parity {len(watches)}/{len(guarded)}')
    slow_win=guarded[guarded.parent_pnl>0].copy(); all_loss=guarded[guarded.parent_pnl<=0].copy()
    fake_confirm=guarded[(guarded.parent_pnl<=0)&(guarded.f632_action.str.contains('CONFIRM'))].copy()
    if (len(slow_win),len(all_loss),len(fake_confirm))!=(2,4,3):
        raise RuntimeError(f'primary cohort parity {len(slow_win)}/{len(all_loss)}/{len(fake_confirm)}')

    # Broader cross-control: original WATCH future winners vs F6.27-style true dead.
    ext_win=watches[watches.parent_pnl>0].copy()
    ext_dead=watches[(watches.parent_pnl<=0)&(watches.parent_mfe_r<.5)&(watches.base_layer=='PARENT')].copy()
    if (len(ext_win),len(ext_dead))!=(13,9):raise RuntimeError(f'external parity {len(ext_win)}/{len(ext_dead)}')

    cont_names=['progress_r','ema7_dist_r','cum_taker_after10','post30_cum_taker','post30_current_taker','post30_taker_change',
                'post30_ema7_hold_share','post30_entry_hold_share','post30_positive_flow_share','post30_higher_close_share',
                'post30_higher_low_share','post30_higher_high_share','post30_chain_share','post30_full_chain_share']
    bin_names=['current_above_ema7','current_above_entry','current_flow_positive','current_higher_close','current_higher_low','current_higher_high',
               'current_chain','current_full_chain','ema7_reclaim_after30_any','ema7_persistent_after_reclaim','ema7_failed_after_reclaim',
               'ema7_retest_hold_after_reclaim','entry_reclaim_after30_any','entry_persistent_after_reclaim','flow_positive_after30_any',
               'flow_persistent_after_turn','fake_bounce_now','persistent_recovery_now','persistent_recovery_flow_now',
               'new_low_after30_vs_25_30','current_green']

    checkpoints={}
    for m in CHECKS:
        def alive(g):return g[g[f'm{m}_alive']==True].copy()
        sw=alive(slow_win); fc=alive(fake_confirm); al=alive(all_loss); ew=alive(ext_win); ed=alive(ext_dead)
        cstats=[]
        for n in cont_names:
            col=f'm{m}_{n}'
            if len(sw) and len(fc) and col in df.columns:
                r=_stat(sw,fc,col,ew,ed);r['metric']=n;cstats.append(r)
        cstats.sort(key=lambda r:(r['direction_agrees_external'],r['loo_median_strength'],r['subset']['strength']),reverse=True)
        bstats=[]
        for n in bin_names:
            col=f'm{m}_{n}'
            if len(sw) and len(fc) and col in df.columns:
                a=sw[col].dropna();b=fc[col].dropna();x=ew[col].dropna();y=ed[col].dropna()
                if len(a) and len(b):
                    gap=float(a.mean()-b.mean());eg=float(x.mean()-y.mean()) if len(x) and len(y) else np.nan
                    bstats.append({'metric':n,'winner_rate':float(a.mean()),'fake_confirm_loss_rate':float(b.mean()),
                                   'gap_winner_minus_loss':gap,'external_winner_rate':float(x.mean()) if len(x) else np.nan,
                                   'external_dead_rate':float(y.mean()) if len(y) else np.nan,
                                   'external_gap_winner_minus_dead':eg,
                                   'direction_agrees_external':bool(np.isfinite(eg) and gap*eg>=0)})
        bstats.sort(key=lambda r:(r['direction_agrees_external'],abs(r['gap_winner_minus_loss']),abs(r['external_gap_winner_minus_dead']) if np.isfinite(r['external_gap_winner_minus_dead']) else -1),reverse=True)
        checkpoints[str(m)]={
          'alive':{'slow_winner':len(sw),'fake_confirm_loser':len(fc),'all_guarded_loser':len(al),'external_winner':len(ew),'external_true_dead':len(ed)},
          'top_continuous':cstats[:10],'top_boolean':bstats[:10],
        }

    detail_cols=['date','period','parent_pnl','parent_mfe_r','parent_mae_r','f632_action','taker_change20']
    detail=guarded[detail_cols].to_dict('records')
    out={'status':'FORENSIC_ONLY_NO_RULE',
         'question':'After +30m, what separates F6.32 slow winners from fake structural-recovery losers?',
         'checkpoints':list(CHECKS),
         'cohort_counts':{'slow_winner':len(slow_win),'fake_confirm_loser':len(fake_confirm),'all_guarded_loser':len(all_loss),
                          'external_future_winner':len(ext_win),'external_true_dead':len(ext_dead)},
         'guarded_cases':detail,'checkpoints_detail':checkpoints,
         'guardrail':'Post-+30 observations cannot justify the +30 decision. F6.33 is forensic only; no threshold/timing/economic sweep and no rule promotion.'}
    (OUT/'f633_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.33 — Fake Bounce vs Slow Recovery +30→+60 Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**',
        '**Live BBC untouched; F6.29/F6.31/F6.32 remain failed and are NOT frozen.**','',
        '## Cohorts',f'- slow winners F6.32 cut at +30m: **{len(slow_win)}**',
        f'- fake-confirm losers F6.32 released at +25/+30m: **{len(fake_confirm)}**',
        f'- all guarded losers: **{len(all_loss)}**',f'- external cross-control: **{len(ext_win)} winners vs {len(ext_dead)} true-dead**','']
    for m in CHECKS:
        q=checkpoints[str(m)];a=q['alive']
        md += [f'## +{m}m causal snapshot',f"- alive slow-winner/fake-confirm-loser/all-loss: **{a['slow_winner']}/{a['fake_confirm_loser']}/{a['all_guarded_loser']}**; external winner/dead **{a['external_winner']}/{a['external_true_dead']}**"]
        shown=0
        for r in q['top_continuous']:
            if not r['direction_agrees_external']:continue
            s=r['subset'];e=r['external']
            md.append(f"- `{r['metric']}`: strength **{s['strength']:.3f}** ({s['direction']}), med W/L **{s['winner_median']:.4f}/{s['loss_median']:.4f}**; LOO med/min **{r['loo_median_strength']:.3f}/{r['loo_min_strength']:.3f}**; external **{e['strength']:.3f}** same direction")
            shown+=1
            if shown>=4:break
        for r in q['top_boolean'][:4]:
            md.append(f"- state `{r['metric']}` W/fake-L **{100*r['winner_rate']:.1f}%/{100*r['fake_confirm_loss_rate']:.1f}%**; external W/dead **{100*r['external_winner_rate']:.1f}%/{100*r['external_dead_rate']:.1f}%**; agree **{r['direction_agrees_external']}**")
        md.append('')
    md += ['## Guardrail','Everything after +30m is descriptive for a *later* decision only. Do not use this run to claim the prior +30m cut was knowable, and do not tune timing or numeric thresholds from these tiny cohorts.']
    (OUT/'F6.33_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
