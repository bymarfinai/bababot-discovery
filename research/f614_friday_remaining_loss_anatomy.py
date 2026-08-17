#!/usr/bin/env python3
"""Friday F6.14 — Remaining Loss Anatomy.

Research only; live BBC untouched.
No management rule tuning. Frozen stack is preserved:
F6.12 FIB5 -> F6.9 EARLY10 -> F6.5 +60 upper-wick cut.

Purpose: explain WHY Friday losses occur and, especially, what mechanisms remain
unhandled after the current three-layer management stack.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f611_friday_fibonacci_forensic as f611
import f612_friday_fib_early5_cut as f612
import f69_friday_early_sink_candidate_robustness as f69
import f613_friday_three_layer_integration as f613

OUT=Path(os.getenv('F614_OUT','f614_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL  # natural risk = 0.70%
SPLIT=f517.SPLIT_N


def path_features(k,t,tr):
    bars=k[(k.index>=t)&(k.index<tr.exit_t)].copy()
    if bars.empty: raise RuntimeError(f'no path {tr.date}')
    # Subsequent bars after the first completed 5m.
    first=bars.iloc[0]
    rest=bars.iloc[1:]
    first5_red=bool(float(first.close)<tr.entry)
    strict_sink=bool(first5_red and (rest.empty or float(rest.high.max())<tr.entry-1e-12))

    # MFE expressed in natural R units.
    mfe=float(tr.mfe); mae=float(tr.mae)
    mfe_r=mfe/R; mae_r=mae/R

    # Peak favorable excursion timing.
    fav=(bars.high.astype(float)/tr.entry-1.0)
    peak_idx=fav.idxmax(); peak_min=int((peak_idx-t)/pd.Timedelta(minutes=1))+5

    # Causal checkpoint snapshots using completed bars only.
    cps={}
    for m in [5,10,15,30,60,120,180]:
        d=t+pd.Timedelta(minutes=m)
        if tr.exit_t<=d:
            cps[m]={'alive':False}
            continue
        x=k[(k.index>=t)&(k.index<d)]
        if len(x)!=m//5:
            cps[m]={'alive':False}; continue
        last=x.iloc[-1]
        qv=float(x.quote_volume.sum()); tb=float(x.taker_buy_quote.sum())
        taker=(2*tb/qv-1.0) if qv>0 else np.nan
        cps[m]={
            'alive':True,
            'progress':float(last.close)/tr.entry-1.0,
            'close_above_entry':bool(float(last.close)>=tr.entry),
            'high_reclaim':bool(float(x.high.max())>=tr.entry),
            'ema7_dist':float(last.close)/float(last.ema7)-1.0,
            'ema20_dist':float(last.close)/float(last.ema20)-1.0,
            'taker':taker,
            'mfe':float(x.high.max())/tr.entry-1.0,
            'mae':1.0-float(x.low.min())/tr.entry,
        }

    # Hindsight anatomy bucket, descriptive only.
    if strict_sink:
        archetype='A_IMMEDIATE_SINK'
    elif mfe < 0.5*R:
        archetype='B_NEVER_GOT_0.5R'
    elif mfe < 1.0*R:
        archetype='C_PARTIAL_LT_1R'
    elif mfe < 2.0*R:
        archetype='D_GOOD_START_GIVEBACK_1_2R'
    elif mfe < 2.5*R:
        archetype='E_RUNNER_GIVEBACK_2_2.5R'
    else:
        archetype='F_ALMOST_TP_GIVEBACK_GE_2.5R'

    return {
        'first5_red':first5_red,'strict_sink':strict_sink,
        'mfe':mfe,'mae':mae,'mfe_r':mfe_r,'mae_r':mae_r,'peak_min':peak_min,
        'archetype':archetype,'cps':cps,
    }


def pre_context(k,t,tr):
    f2=f611.fib_features(k,t,float(tr.entry),120)
    baseline=f612.rolling_2h_range_baseline(k,t)
    pre=k[(k.index<t)&(k.index>=t-pd.Timedelta(hours=4))]
    def ret(minutes):
        x=k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=minutes))]
        if x.empty:return np.nan
        return float(x.iloc[-1].close)/float(x.iloc[0].open)-1.0
    last=k.loc[t-pd.Timedelta(minutes=5)]
    return {
        'fib2h_retr':float(f2['retr_depth']) if f2 else np.nan,
        'fib2h_range_pct':float(f2['range_pct']) if f2 else np.nan,
        'fib2h_baseline':baseline,
        'fib_shallow382':bool(f2 and float(f2['retr_depth'])<=0.382),
        'range2h_expanded':bool(f2 and np.isfinite(baseline) and float(f2['range_pct'])>baseline),
        'ret30':ret(30),'ret60':ret(60),'ret120':ret(120),'ret240':ret(240),
        'pre_ema7_dist':float(last.close)/float(last.ema7)-1.0,
        'pre_ema20_dist':float(last.close)/float(last.ema20)-1.0,
        'pre_ema_spread':float(last.ema7)/float(last.ema20)-1.0,
        'pre_taker60': (lambda x: (2*float(x.taker_buy_quote.sum())/float(x.quote_volume.sum())-1.0) if float(x.quote_volume.sum())>0 else np.nan)(k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=60))]),
    }


def summarize(g):
    if len(g)==0:return {'n':0}
    return {
        'n':int(len(g)),
        'pnl':float(g.managed_pnl.sum()),
        'parent_pnl':float(g.parent_pnl.sum()),
        'median_mfe_r':float(g.mfe_r.median()),
        'median_mae_r':float(g.mae_r.median()),
        'median_peak_min':float(g.peak_min.median()),
        'first5_red_pct':float(g.first5_red.mean()),
        'shallow382_pct':float(g.fib_shallow382.mean()),
        'expanded2h_pct':float(g.range2h_expanded.mean()),
        'median_fib2h_retr':float(g.fib2h_retr.median()),
    }


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        pf=path_features(k,t,tr); pc=pre_context(k,t,tr)
        a5=f613.fib5_state(k,t,tr); a10=f69.early_state(k,t,tr); a60=f69.f65_state(k,t,tr)
        layer='PARENT'; managed=float(tr.pnl)
        if a5:
            layer='FIB5'; managed=f613.cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=5),'open']))
        elif a10:
            layer='EARLY10'; managed=f613.cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=10),'open']))
        elif a60:
            layer='F65_60'; managed=f613.cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=60),'open']))

        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_reason':tr.reason,
             'managed_pnl':float(managed),'managed_win':bool(managed>0),'layer':layer,
             'a5':a5,'a10':a10,'a60':a60,
             **{kk:vv for kk,vv in pf.items() if kk!='cps'},**pc}
        for m,st in pf['cps'].items():
            for kk,vv in st.items(): row[f'cp{m}_{kk}']=vv
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f614_all_rows.csv',index=False)

    losses=df[df.parent_pnl<=0].copy()
    managed_losses=df[df.managed_pnl<=0].copy()
    untouched=managed_losses[managed_losses.layer=='PARENT'].copy()
    winners=df[df.parent_pnl>0].copy()

    # Mutually-exclusive anatomy counts for all parent losses and still-unhandled losses.
    arch_all={a:summarize(g) for a,g in losses.groupby('archetype')}
    arch_untouched={a:summarize(g) for a,g in untouched.groupby('archetype')}

    # Layer attribution: which original loss mechanism is already being intercepted.
    layer_arch=pd.crosstab(losses.archetype,losses.layer).reset_index()
    layer_arch.to_csv(OUT/'f614_layer_by_archetype.csv',index=False)

    # Checkpoint state comparison for untouched losses vs parent winners.
    cp_compare={}
    for m in [5,10,15,30,60,120,180]:
        rec={}
        for name,g in [('untouched_loss',untouched),('winner',winners)]:
            alive=g[g.get(f'cp{m}_alive',False)==True] if f'cp{m}_alive' in g else g.iloc[0:0]
            rec[name]={
                'n_alive':int(len(alive)),
                'median_progress':float(alive[f'cp{m}_progress'].median()) if len(alive) else np.nan,
                'close_above_entry_pct':float(alive[f'cp{m}_close_above_entry'].mean()) if len(alive) else np.nan,
                'median_taker':float(alive[f'cp{m}_taker'].median()) if len(alive) else np.nan,
                'median_ema7_dist':float(alive[f'cp{m}_ema7_dist'].median()) if len(alive) else np.nan,
                'median_mfe_r':float((alive[f'cp{m}_mfe']/R).median()) if len(alive) else np.nan,
            }
        cp_compare[str(m)]=rec

    # Stable D/V anatomy for untouched losses.
    dv={}
    for period,g in [('discovery',untouched[untouched.i<SPLIT]),('validation',untouched[untouched.i>=SPLIT])]:
        dv[period]={'n':int(len(g)),'archetypes':g.archetype.value_counts().to_dict(),
                    'parent_reasons':g.parent_reason.value_counts().to_dict(),
                    'median_mfe_r':float(g.mfe_r.median()) if len(g) else np.nan,
                    'median_fib2h_retr':float(g.fib2h_retr.median()) if len(g) else np.nan}

    # Natural threshold-free facts around recovery/giveback.
    facts={
        'all_parent_losses':int(len(losses)),
        'losses_intercepted_by_any_layer':int((losses.layer!='PARENT').sum()),
        'untouched_losses':int(len(untouched)),
        'untouched_sl':int((untouched.parent_reason=='SL').sum()),
        'untouched_timeout':int((untouched.parent_reason=='TIMEOUT').sum()),
        'untouched_never_0.5R':int((untouched.mfe_r<0.5).sum()),
        'untouched_reached_0.5R':int((untouched.mfe_r>=0.5).sum()),
        'untouched_reached_1R':int((untouched.mfe_r>=1.0).sum()),
        'untouched_reached_2R':int((untouched.mfe_r>=2.0).sum()),
        'untouched_reached_2.5R':int((untouched.mfe_r>=2.5).sum()),
        'untouched_first5_green':int((~untouched.first5_red).sum()),
        'untouched_first5_red':int(untouched.first5_red.sum()),
        'untouched_shallow382_expanded':int((untouched.fib_shallow382 & untouched.range2h_expanded).sum()),
    }

    out={
        'frozen_stack':'FIB5 -> EARLY10 -> F65_60; no retuning',
        'parent':{'n':int(len(df)),'wins':int((df.parent_pnl>0).sum()),'losses':int(len(losses)),'pnl':float(df.parent_pnl.sum())},
        'managed':{'wins':int((df.managed_pnl>0).sum()),'losses':int((df.managed_pnl<=0).sum()),'pnl':float(df.managed_pnl.sum()),'layers':df.layer.value_counts().to_dict()},
        'facts':facts,'all_loss_archetypes':arch_all,'untouched_loss_archetypes':arch_untouched,
        'untouched_dv':dv,'checkpoint_compare':cp_compare,
        'winner_context':summarize(winners),'untouched_context':summarize(untouched),
    }
    (OUT/'f614_summary.json').write_text(json.dumps(out,indent=2,default=float))

    # human-readable checkpoint
    order=['A_IMMEDIATE_SINK','B_NEVER_GOT_0.5R','C_PARTIAL_LT_1R','D_GOOD_START_GIVEBACK_1_2R','E_RUNNER_GIVEBACK_2_2.5R','F_ALMOST_TP_GIVEBACK_GE_2.5R']
    md=['# Friday15 F6.14 — Remaining Loss Anatomy','',
        '**Status:** COMPLETE — FORENSIC ONLY; NO RULE TUNING','**Research only; live BBC untouched.**','',
        '## Scope',f"Parent losses: **{len(losses)}**. Intercepted by current stack: **{facts['losses_intercepted_by_any_layer']}**. Still untouched: **{len(untouched)}**.",'',
        '## Untouched loss anatomy']
    for a in order:
        x=arch_untouched.get(a,{'n':0}); md.append(f"- {a}: **{x.get('n',0)}**")
    md += ['', '## Natural path facts',
           f"- untouched that never reached +0.5R: **{facts['untouched_never_0.5R']}**",
           f"- reached +0.5R then still lost: **{facts['untouched_reached_0.5R']}**",
           f"- reached +1R then still lost: **{facts['untouched_reached_1R']}**",
           f"- reached +2R then still lost: **{facts['untouched_reached_2R']}**",
           f"- reached +2.5R then still lost: **{facts['untouched_reached_2.5R']}**",
           f"- first5 green/red among untouched: **{facts['untouched_first5_green']} / {facts['untouched_first5_red']}**",'',
           '## Interpretation','The remaining losses are not assumed to share one cause. This milestone separates early thesis failure from trades that were initially correct but later gave back favorable excursion. Any next management rule must target one archetype causally and leave frozen layers unchanged.']
    (OUT/'F6.14_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
