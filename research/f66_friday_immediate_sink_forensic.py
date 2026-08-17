#!/usr/bin/env python3
"""F6.6 — Friday15 immediate-sink path forensic.

Research only; live BBC untouched.

Question: are there Friday BUY trades that go below entry immediately and never
come back?

No threshold fitting. Three nested, natural definitions are reported:
A) NEVER_ABOVE_ENTRY: after entry open, no 5m high ever exceeds entry before parent exit.
B) FIRST5_RED_NEVER_TRADE_RECLAIM: first 5m closes below entry, and from the
   second 5m bar onward no high reaches entry.
C) FIRST5_RED_NEVER_CLOSE_RECLAIM: first 5m closes below entry, and from the
   second 5m bar onward no close reaches entry.

These are descriptive hindsight path labels only, not causal entry/exit rules.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60
import f63_friday_failure60_candle_morphology as f63

OUT=Path(os.getenv('F66_OUT','f66_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N


def summarize(g: pd.DataFrame) -> dict:
    if len(g)==0:
        return {'n':0,'wins':0,'losses':0,'wr':None,'pnl':0.0,'tp':0,'sl':0,'timeout':0,
                'failure60':0,'upperwick_true_failure':0,'median_mfe_pct':None,'median_mae_pct':None}
    return {
        'n':int(len(g)),
        'wins':int(g.parent_win.sum()),
        'losses':int((~g.parent_win).sum()),
        'wr':float(g.parent_win.mean()),
        'pnl':float(g.parent_pnl.sum()),
        'tp':int((g.parent_reason=='TP').sum()),
        'sl':int((g.parent_reason=='SL').sum()),
        'timeout':int((g.parent_reason=='TIMEOUT').sum()),
        'failure60':int(g.failure60.sum()),
        'upperwick_true_failure':int(g.upperwick_true_failure.sum()),
        'median_mfe_pct':float(g.mfe_pct.median()),
        'median_mae_pct':float(g.mae_pct.median()),
    }


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        bars=k[(k.index>=t)&(k.index<tr.exit_t)].copy()
        # For an SL on the first bar, this includes the first bar; for timeout it includes all 72.
        if bars.empty:
            raise RuntimeError(f'no path bars {tr.date}')
        first=bars.iloc[0]
        rest=bars.iloc[1:]

        first5_red=bool(float(first.close)<tr.entry)
        never_above=bool(float(bars.high.max()) <= tr.entry + 1e-12)
        rest_never_trade_reclaim=bool(rest.empty or float(rest.high.max()) < tr.entry - 1e-12)
        rest_never_close_reclaim=bool(rest.empty or float(rest.close.max()) < tr.entry - 1e-12)
        strict_trade=bool(first5_red and rest_never_trade_reclaim)
        close_reclaim=bool(first5_red and rest_never_close_reclaim)

        # First causal close-reclaim time after first bar, if any.
        first_trade_reclaim_min=np.nan; first_close_reclaim_min=np.nan
        for j,(ts,b) in enumerate(rest.iterrows(), start=1):
            if not np.isfinite(first_trade_reclaim_min) and float(b.high)>=tr.entry:
                first_trade_reclaim_min=float(j*5)
            if not np.isfinite(first_close_reclaim_min) and float(b.close)>=tr.entry:
                first_close_reclaim_min=float((j+1)*5)  # close time from entry
            if np.isfinite(first_trade_reclaim_min) and np.isfinite(first_close_reclaim_min):
                break

        pf=f60.path_features(k,t,tr)
        failure60=bool(pf['alive60'] and pf['progress60']<=0 and pf['taker60']<0 and pf['ema20_dist60']<=0)
        uw=False
        if failure60:
            cf=f63.candle(k,t+pd.Timedelta(minutes=60),tr.entry)
            uw=bool(cf is not None and cf['UPPER_WICK_DOM'])

        rows.append({
            'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
            'entry':tr.entry,'parent_pnl':tr.pnl,'parent_win':tr.pnl>0,'parent_reason':tr.reason,
            'mfe_pct':100*tr.mfe,'mae_pct':100*tr.mae,
            'first5_close_ret_pct':100*(float(first.close)/tr.entry-1.0),
            'first5_high_ret_pct':100*(float(first.high)/tr.entry-1.0),
            'first5_low_ret_pct':100*(float(first.low)/tr.entry-1.0),
            'first5_red':first5_red,
            'never_above_entry':never_above,
            'first5_red_never_trade_reclaim':strict_trade,
            'first5_red_never_close_reclaim':close_reclaim,
            'first_trade_reclaim_min':first_trade_reclaim_min,
            'first_close_reclaim_min':first_close_reclaim_min,
            'failure60':failure60,'upperwick_true_failure':bool(failure60 and uw),
        })

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f66_rows.csv',index=False)

    labels={
      'never_above_entry':'NEVER_ABOVE_ENTRY',
      'first5_red_never_trade_reclaim':'FIRST5_RED_NEVER_TRADE_RECLAIM',
      'first5_red_never_close_reclaim':'FIRST5_RED_NEVER_CLOSE_RECLAIM',
    }
    out={}
    for col,name in labels.items():
        z=df[df[col]]
        out[name]={
            'full':summarize(z),
            'discovery':summarize(z[z.i<SPLIT]),
            'validation':summarize(z[z.i>=SPLIT]),
            'dates':z[['date','parent_pnl','parent_reason','mfe_pct','mae_pct','failure60','upperwick_true_failure']].to_dict('records'),
        }

    # Useful base rates to avoid cherry-picking interpretation.
    red=df[df.first5_red]
    out['BASE']={
        'all':summarize(df),
        'first5_red':summarize(red),
        'first5_red_n':int(len(red)),
        'first5_red_then_ever_trade_reclaim_n':int((red.first5_red & ~red.first5_red_never_trade_reclaim).sum()),
        'first5_red_then_ever_close_reclaim_n':int((red.first5_red & ~red.first5_red_never_close_reclaim).sum()),
    }
    (OUT/'f66_summary.json').write_text(json.dumps(out,indent=2,default=float))

    md=['# Friday15 F6.6 — Immediate Sink Path Forensic','',
        '**Status:** COMPLETE — DESCRIPTIVE ONLY','**Live BBC untouched. No rule promoted.**','',
        '## Question','Are there Friday BUY trades that go below entry immediately and never come back?','']
    for key in ['NEVER_ABOVE_ENTRY','FIRST5_RED_NEVER_TRADE_RECLAIM','FIRST5_RED_NEVER_CLOSE_RECLAIM']:
        x=out[key]['full']; d=out[key]['discovery']; v=out[key]['validation']
        md += [f'## {key}',
               f"- Full: N={x['n']}, {x['wins']}W/{x['losses']}L, WR={(100*x['wr'] if x['wr'] is not None else 0):.2f}%, PnL={x['pnl']:+.3f}",
               f"- Discovery: N={d['n']}, {d['wins']}W/{d['losses']}L",
               f"- Validation: N={v['n']}, {v['wins']}W/{v['losses']}L",
               f"- Parent exits: TP={x['tp']}, SL={x['sl']}, TIMEOUT={x['timeout']}",
               f"- Overlap FAILURE_60={x['failure60']}, upper-wick true-failure={x['upperwick_true_failure']}",'']
    md += ['## Guardrail','These labels use the future path and are therefore hindsight descriptions. The next valid step, if useful, is to identify how early the sink state becomes causally detectable without using future non-reclaim as an input.']
    (OUT/'F6.6_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)

if __name__=='__main__': main()
