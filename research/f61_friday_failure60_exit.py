#!/usr/bin/env python3
"""F6.1 — Friday15 frozen +60m FAILURE management counterfactual.
Research only; live BBC untouched.

Frozen from F6.0 (no threshold changes):
FAILURE_60 iff position is alive at +60m AND
- progress60 <= 0
- taker60 < 0
- ema20_dist60 <= 0

Counterfactual action:
- exit at actual +60m open.
All non-FAILURE trades keep the frozen parent unchanged.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60

OUT=Path(os.getenv('F61_OUT','f61_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N


def metrics(p):
    p=np.asarray(p,dtype=float); w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':len(p),'wins':w,'losses':len(p)-w,'wr':w/len(p) if len(p) else np.nan,'pnl':float(p.sum()),'exp':float(p.mean()) if len(p) else np.nan,'pf':gp/gl if gl>0 else math.inf,'dd':dd,'ls':ls}


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    rows=[]; parents=[]
    for i,d in enumerate(days):
        t=pd.Timestamp(d.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        pf=f60.path_features(k,t,tr)
        failure=bool(pf['alive60'] and pf['progress60']<=0 and pf['taker60']<0 and pf['ema20_dist60']<=0)
        managed=tr.pnl; exit_px=np.nan; delta=0.0
        if failure:
            dt=t+pd.Timedelta(minutes=60)
            exit_px=float(k.loc[dt,'open'])
            managed=f517.NOTIONAL*(exit_px/tr.entry-1.0)-f517.ROUND_TRIP_FEE
            delta=managed-tr.pnl
        rows.append({'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,'parent_pnl':tr.pnl,'parent_win':tr.pnl>0,'failure60':failure,'progress60':pf['progress60'],'taker60':pf['taker60'],'ema20_dist60':pf['ema20_dist60'],'managed_pnl':managed,'managed_win':managed>0,'delta':delta,'exit60_px':exit_px,'improved':delta>1e-12,'damaged':delta<-1e-12,'winner_to_loss':bool(tr.pnl>0 and managed<=0),'loss_to_win':bool(tr.pnl<=0 and managed>0)})
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f61_rows.csv',index=False)

    parent=metrics(df.parent_pnl); managed=metrics(df.managed_pnl)
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    result={
      'parent':parent,'managed':managed,'delta':managed['pnl']-parent['pnl'],
      'actions':int(df.failure60.sum()),'improved':int(df.improved.sum()),'damaged':int(df.damaged.sum()),
      'winner_to_loss':int(df.winner_to_loss.sum()),'loss_to_win':int(df.loss_to_win.sum()),
      'discovery':{'parent':metrics(d.parent_pnl),'managed':metrics(d.managed_pnl),'delta':float(d.delta.sum()),'actions':int(d.failure60.sum())},
      'validation':{'parent':metrics(v.parent_pnl),'managed':metrics(v.managed_pnl),'delta':float(v.delta.sum()),'actions':int(v.failure60.sum())},
    }
    # Predeclared promotion gate: positive delta in both chronology halves, overall PnL improves, no parent winner becomes managed loss.
    result['gate']={'overall_delta_positive':result['delta']>0,'discovery_delta_positive':result['discovery']['delta']>0,'validation_delta_positive':result['validation']['delta']>0,'no_winner_to_loss':result['winner_to_loss']==0}
    result['pass']=all(result['gate'].values())
    (OUT/'f61_summary.json').write_text(json.dumps(result,indent=2,default=float))

    pct=lambda x:f'{100*x:.2f}%'; money=lambda x:f'${x:+.3f}'
    md=['# Friday15 F6.1 — Frozen FAILURE_60 Exit Counterfactual','',
        f"**Status:** COMPLETE — {'PASS' if result['pass'] else 'FAIL'}",'**Research only:** live BBC untouched','',
        '## Frozen rule','`FAILURE_60 = alive + progress<=0 + taker<0 + close<=EMA20`; exit at actual +60m open.','',
        '## Result',
        f"- Parent: **{parent['wins']}W/{parent['losses']}L, WR {pct(parent['wr'])}, {money(parent['pnl'])}**",
        f"- Managed: **{managed['wins']}W/{managed['losses']}L, WR {pct(managed['wr'])}, {money(managed['pnl'])}**",
        f"- Delta: **{money(result['delta'])}**",
        f"- Actions: **{result['actions']}**; improved {result['improved']}; damaged {result['damaged']}",
        f"- Winner->loss: **{result['winner_to_loss']}**; loss->win: **{result['loss_to_win']}**",'',
        '## Chronology',
        f"- Discovery delta: **{money(result['discovery']['delta'])}** on {result['discovery']['actions']} actions",
        f"- Validation delta: **{money(result['validation']['delta'])}** on {result['validation']['actions']} actions",'',
        '## Gate',
        f"- Overall positive: {result['gate']['overall_delta_positive']}",
        f"- Discovery positive: {result['gate']['discovery_delta_positive']}",
        f"- Validation positive: {result['gate']['validation_delta_positive']}",
        f"- No winner->loss: {result['gate']['no_winner_to_loss']}",
    ]
    (OUT/'F6.1_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(result,indent=2,default=float),flush=True)

if __name__=='__main__': main()
