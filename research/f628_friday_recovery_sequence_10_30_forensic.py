#!/usr/bin/env python3
"""F6.28 — Friday recovery sequence +10m -> +30m forensic.

Research only; live BBC untouched. NO management rule is tuned/promoted.
F6.26 remains failed and is NOT frozen.

Question:
After FAILED_LAUNCH_10 fires, can the causal recovery trajectory observed between
+10m and +30m separate exact TRUE_DEAD trades from FALSE_WINNER trades?

The checkpoints are predeclared: +15/+20/+25/+30m. Features use only bars that
have fully closed by each checkpoint. Natural zero/boolean thresholds only;
there is no threshold sweep and no economic action in this milestone.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f624_friday_context_repair_failure_management as f624
import f626_friday_failed_launch10_management as f626
import f627_friday_failed_launch_true_vs_recovery_forensic as f627

OUT=Path(os.getenv('F628_OUT','f628_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
CHECKS=(15,20,25,30)


def _streak(vals):
    n=0
    for v in reversed(list(vals)):
        if bool(v): n+=1
        else: break
    return int(n)


def seq_features(k,t,tr,m):
    """Strictly causal features available at decision-open t + m minutes."""
    dt=t+pd.Timedelta(minutes=m)
    ex=pd.Timestamp(tr.exit_t)
    allx=k[(k.index>=t)&(k.index<dt)].copy()
    if dt not in k.index or len(allx)!=m//5 or ex<=dt:
        return {'alive':False}

    entry=float(tr.entry)
    post=allx.iloc[2:].copy()  # bars closing strictly after the +10m WATCH point
    prev_close=allx.close.astype(float).shift(1)
    prev_low=allx.low.astype(float).shift(1)
    prev_high=allx.high.astype(float).shift(1)

    ema_ok=allx.close.astype(float)>=allx.ema7.astype(float)
    entry_ok=allx.close.astype(float)>=entry
    flow_ok=allx.taker_imb.astype(float)>0
    hc=allx.close.astype(float)>prev_close
    hl=allx.low.astype(float)>prev_low
    hh=allx.high.astype(float)>prev_high

    # Restrict trajectory summaries to bars AFTER the +10m watch declaration.
    idx=post.index
    ema_p=ema_ok.loc[idx]; entry_p=entry_ok.loc[idx]; flow_p=flow_ok.loc[idx]
    hc_p=hc.loc[idx]; hl_p=hl.loc[idx]; hh_p=hh.loc[idx]
    repair_struct=(ema_p & hc_p & hl_p)
    repair_full=(repair_struct & flow_p)
    reaccel=(hc_p & hh_p & flow_p)
    persistent_bear=((~ema_p) & (~entry_p) & (~flow_p))

    last=allx.iloc[-1]
    q=float(post.quote_volume.sum()) if len(post) else 0.0
    tb=float(post.taker_buy_quote.sum()) if len(post) else 0.0
    cum_taker=(2*tb/q-1) if q>0 else np.nan
    ema_dist=(float(last.close)/float(last.ema7)-1)/R

    ema_reclaim_any=bool(ema_p.any()) if len(post) else False
    entry_reclaim_any=bool(entry_p.any()) if len(post) else False
    full_repair_any=bool(repair_full.any()) if len(post) else False
    struct_repair_any=bool(repair_struct.any()) if len(post) else False

    current_above_ema7=bool(ema_ok.iloc[-1])
    current_above_entry=bool(entry_ok.iloc[-1])
    current_flow_positive=bool(flow_ok.iloc[-1])
    current_hc=bool(hc.iloc[-1]); current_hl=bool(hl.iloc[-1]); current_hh=bool(hh.iloc[-1])
    current_struct=bool(current_above_ema7 and current_hc and current_hl)
    current_full=bool(current_struct and current_flow_positive)
    current_reaccel=bool(current_hc and current_hh and current_flow_positive)
    repair_score=int(current_above_ema7)+int(current_hc)+int(current_hl)+int(current_flow_positive)

    # Predeclared semantic states; no fitted numeric threshold.
    unrepaired_now=bool((not current_above_ema7) and (not current_above_entry) and (not full_repair_any))
    unrepaired_with_flow=bool(unrepaired_now and np.isfinite(cum_taker) and cum_taker<=0)
    false_bounce=bool(ema_reclaim_any and (not current_above_ema7))
    recovery_chain=bool(ema_reclaim_any and current_above_ema7 and current_hl and current_hc)
    recovery_chain_flow=bool(recovery_chain and current_flow_positive)

    return {
      'alive':True,
      'progress_r':(float(last.close)/entry-1)/R,
      'ema7_dist_r':ema_dist,
      'cum_taker_after10':cum_taker,
      'ema7_failure_share':float((~ema_p).mean()) if len(post) else np.nan,
      'below_entry_share':float((~entry_p).mean()) if len(post) else np.nan,
      'negative_taker_share':float((~flow_p).mean()) if len(post) else np.nan,
      'persistent_bear_share':float(persistent_bear.mean()) if len(post) else np.nan,
      'struct_repair_share':float(repair_struct.mean()) if len(post) else np.nan,
      'full_repair_share':float(repair_full.mean()) if len(post) else np.nan,
      'reaccel_share':float(reaccel.mean()) if len(post) else np.nan,
      'repair_score_now':float(repair_score),
      'ema7_hold_streak':float(_streak(ema_p)),
      'entry_hold_streak':float(_streak(entry_p)),
      'struct_repair_streak':float(_streak(repair_struct)),
      'full_repair_count':float(repair_full.sum()),
      'struct_repair_count':float(repair_struct.sum()),
      'ema7_reclaim_any':float(ema_reclaim_any),
      'entry_reclaim_any':float(entry_reclaim_any),
      'struct_repair_any':float(struct_repair_any),
      'full_repair_any':float(full_repair_any),
      'current_above_ema7':float(current_above_ema7),
      'current_above_entry':float(current_above_entry),
      'current_flow_positive':float(current_flow_positive),
      'current_higher_close':float(current_hc),
      'current_higher_low':float(current_hl),
      'current_higher_high':float(current_hh),
      'current_struct_repair':float(current_struct),
      'current_full_repair':float(current_full),
      'current_reaccel':float(current_reaccel),
      'unrepaired_now':float(unrepaired_now),
      'unrepaired_with_flow':float(unrepaired_with_flow),
      'false_bounce_now':float(false_bounce),
      'recovery_chain_now':float(recovery_chain),
      'recovery_chain_flow_now':float(recovery_chain_flow),
    }


def rate_stat(dead,win,col):
    out={'feature':col}
    dirs=[]; gaps=[]
    for name,mask in [('full',lambda x:pd.Series(True,index=x.index)),('discovery',lambda x:x.i<SPLIT),('validation',lambda x:x.i>=SPLIT)]:
        a=dead[mask(dead)][col].dropna(); b=win[mask(win)][col].dropna()
        da=float(a.mean()) if len(a) else np.nan; wb=float(b.mean()) if len(b) else np.nan
        gap=da-wb if np.isfinite(da) and np.isfinite(wb) else np.nan
        out[name]={'dead_rate':da,'winner_rate':wb,'gap_dead_minus_winner':gap,'n_dead':int(len(a)),'n_winner':int(len(b))}
        if np.isfinite(gap): dirs.append('dead_high' if gap>=0 else 'winner_high'); gaps.append(abs(gap))
    out['same_direction_available_splits']=bool(len(set(dirs))==1) if dirs else False
    out['min_abs_gap_available_splits']=float(min(gaps)) if gaps else np.nan
    return out


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        base_st=f624.state(k,tr); base_pnl,base_layer,base_dt=f624.apply(k,t,tr,base_st)
        st=f626.failed_launch_state(k,t,tr)
        active=False
        if st is not None and st[f626.RULE]:
            active=bool(base_dt is None or st['decision_t']<pd.Timestamp(base_dt))
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'active_f626':active}
        if active:
            for m in CHECKS:
                z=seq_features(k,t,tr,m)
                row[f'm{m}_alive']=bool(z.pop('alive'))
                for kk,vv in z.items(): row[f'm{m}_{kk}']=vv
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f628_rows.csv',index=False)
    active=df[df.active_f626].copy()
    if len(active)!=26: raise RuntimeError(f'F6.26 active parity fail {len(active)}')
    dead=active[(active.parent_pnl<=0)&(active.parent_mfe_r<.5)&(active.base_layer=='PARENT')].copy()
    win=active[active.parent_pnl>0].copy()
    other=active[(active.parent_pnl<=0)&~active.index.isin(dead.index)].copy()
    if (len(dead),len(win),len(other))!=(9,13,4): raise RuntimeError(f'cohort parity fail {len(dead)}/{len(win)}/{len(other)}')

    cont_names=['progress_r','ema7_dist_r','cum_taker_after10','ema7_failure_share','below_entry_share','negative_taker_share','persistent_bear_share','struct_repair_share','full_repair_share','reaccel_share','repair_score_now','ema7_hold_streak','entry_hold_streak','struct_repair_streak','full_repair_count','struct_repair_count']
    binary_names=['ema7_reclaim_any','entry_reclaim_any','struct_repair_any','full_repair_any','current_above_ema7','current_above_entry','current_flow_positive','current_higher_close','current_higher_low','current_higher_high','current_struct_repair','current_full_repair','current_reaccel','unrepaired_now','unrepaired_with_flow','false_bounce_now','recovery_chain_now','recovery_chain_flow_now']

    checkpoints={}
    for m in CHECKS:
        alive_d=dead[dead[f'm{m}_alive']==True].copy(); alive_w=win[win[f'm{m}_alive']==True].copy(); alive_o=other[other[f'm{m}_alive']==True].copy()
        cstats=[]
        for n in cont_names:
            col=f'm{m}_{n}'
            if col in active.columns and len(alive_d) and len(alive_w):
                r=f627.robust_stat(alive_d,alive_w,col); r['metric']=n; cstats.append(r)
        cstats.sort(key=lambda r:(r['same_direction_available_splits'],r['min_strength_available_splits'],r['loo_median_strength']),reverse=True)
        bstats=[]
        for n in binary_names:
            col=f'm{m}_{n}'
            if col in active.columns:
                r=rate_stat(alive_d,alive_w,col); r['metric']=n; bstats.append(r)
        bstats.sort(key=lambda r:(r['same_direction_available_splits'],r['min_abs_gap_available_splits']),reverse=True)
        checkpoints[str(m)]={
          'alive':{'dead':int(len(alive_d)),'winner':int(len(alive_w)),'other':int(len(alive_o)),
                   'dead_exited_before_or_at':int(len(dead)-len(alive_d)),'winner_exited_before_or_at':int(len(win)-len(alive_w))},
          'top_continuous':cstats[:10], 'all_continuous':cstats,
          'top_binary':bstats[:10], 'all_binary':bstats,
        }

    # Compact natural-state table for the exact adaptive-cut question.
    state_table=[]
    for m in CHECKS:
        ad=dead[dead[f'm{m}_alive']==True]; aw=win[win[f'm{m}_alive']==True]
        for state in ('unrepaired_now','unrepaired_with_flow','false_bounce_now','recovery_chain_now','recovery_chain_flow_now'):
            r=rate_stat(ad,aw,f'm{m}_{state}')
            state_table.append({'minute':m,'state':state,**r})

    out={'status':'FORENSIC_ONLY_NO_RULE','question':'Does +10->+30m recovery persistence separate true-dead from false-winner after F6.26 watch?',
         'checkpoints':list(CHECKS),'cohort_counts':{'true_dead':len(dead),'false_winner':len(win),'other_loser':len(other)},
         'checkpoints_detail':checkpoints,'natural_state_table':state_table,
         'guardrail':'Every checkpoint uses only completed bars available at that decision-open. No threshold/timing sweep; no economic action; F6.26 remains failed.'}
    (OUT/'f628_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.28 — Recovery Sequence +10m → +30m Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**','**Live BBC untouched; F6.26 remains failed and is NOT frozen.**','',
        '## Objective','Treat +10m as WATCH, then test whether recovery persistence through +15/+20/+25/+30m causally separates true-dead from future winners.','',
        f'- true-dead: **{len(dead)}** (D {(dead.i<SPLIT).sum()} / V {(dead.i>=SPLIT).sum()})',
        f'- false-winner: **{len(win)}** (D {(win.i<SPLIT).sum()} / V {(win.i>=SPLIT).sum()})','']
    for m in CHECKS:
        q=checkpoints[str(m)]; a=q['alive']
        md += [f'## +{m}m causal snapshot',f"- alive dead/winner: **{a['dead']} / {a['winner']}**; already exited dead/winner: **{a['dead_exited_before_or_at']} / {a['winner_exited_before_or_at']}**"]
        for r in q['top_continuous'][:4]:
            f=r['full']; d=r['discovery']; v=r['validation']
            md.append(f"- continuous `{r['metric']}`: strength full/D/V **{f['strength']:.3f}/{d['strength'] if np.isfinite(d['strength']) else float('nan'):.3f}/{v['strength'] if np.isfinite(v['strength']) else float('nan'):.3f}**, {f['direction']}")
        for r in q['top_binary'][:4]:
            f=r['full']; d=r['discovery']; v=r['validation']
            md.append(f"- state `{r['metric']}` dead vs winner rate full **{100*f['dead_rate']:.1f}%/{100*f['winner_rate']:.1f}%**, gap D/V **{100*d['gap_dead_minus_winner'] if np.isfinite(d['gap_dead_minus_winner']) else float('nan'):+.1f}pp/{100*v['gap_dead_minus_winner'] if np.isfinite(v['gap_dead_minus_winner']) else float('nan'):+.1f}pp**")
        md.append('')
    md += ['## Natural adaptive states (predeclared, not promoted)']
    for r in state_table:
        f=r['full']; d=r['discovery']; v=r['validation']
        md.append(f"- +{r['minute']}m `{r['state']}`: dead/winner **{100*f['dead_rate']:.1f}%/{100*f['winner_rate']:.1f}%**; D/V gap **{100*d['gap_dead_minus_winner'] if np.isfinite(d['gap_dead_minus_winner']) else float('nan'):+.1f}pp/{100*v['gap_dead_minus_winner'] if np.isfinite(v['gap_dead_minus_winner']) else float('nan'):+.1f}pp**")
    md += ['','## Guardrail','This milestone may identify a recovery sequence worth freezing next, but it does not cut a trade. The next management test must predeclare ONE timing/state architecture from these causal results, then measure loss saved versus future winners damaged on the frozen five-layer stack.']
    (OUT/'F6.28_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
