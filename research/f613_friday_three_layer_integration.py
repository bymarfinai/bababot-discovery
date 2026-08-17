#!/usr/bin/env python3
"""F6.13 — Integrate frozen/provisional Friday loss-management layers.
Research only; live BBC untouched. No rule retuning.
Priority: F6.12 +5m Fib cut -> F6.9 +10m early sink -> F6.5 +60m true failure.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import f611_friday_fibonacci_forensic as f611
import f612_friday_fib_early5_cut as f612
import f69_friday_early_sink_candidate_robustness as f69

OUT=Path(os.getenv('F613_OUT','f613_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N

def metrics(p):
    p=np.asarray(p,dtype=float); w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':len(p),'wins':w,'losses':len(p)-w,'wr':w/len(p),'pnl':float(p.sum()),'pf':float(gp/gl) if gl>0 else math.inf,'dd':dd,'ls':ls}

def cut_pnl(entry,px):
    return f517.NOTIONAL*(px/entry-1.0)-f517.ROUND_TRIP_FEE

def fib5_state(k,t,tr):
    f2=f611.fib_features(k,t,float(tr.entry),120)
    baseline=f612.rolling_2h_range_baseline(k,t)
    if f2 is None or not np.isfinite(baseline): return False
    first=k.loc[t]
    return bool(float(first.close)<tr.entry and tr.exit_t>t+pd.Timedelta(minutes=5) and
                float(f2['retr_depth'])<=0.382 and float(f2['range_pct'])>baseline)

def main():
    k=f517.load_klines(); days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8); tr=f517.simulate_parent(k,t); parents.append(tr)
        a5=fib5_state(k,t,tr); a10=f69.early_state(k,t,tr); a60=f69.f65_state(k,t,tr)
        p5=cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=5),'open'])) if a5 else float(tr.pnl)
        p10=cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=10),'open'])) if a10 else float(tr.pnl)
        p60=cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=60),'open'])) if a60 else float(tr.pnl)
        base=float(tr.pnl); layer_base=base; base_layer='PARENT'
        if a10: layer_base=p10; base_layer='EARLY10'
        elif a60: layer_base=p60; base_layer='F65_60'
        triple=base; layer='PARENT'
        if a5: triple=p5; layer='FIB5'
        elif a10: triple=p10; layer='EARLY10'
        elif a60: triple=p60; layer='F65_60'
        rows.append({'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,'parent_pnl':base,'parent_win':base>0,
                     'a5':a5,'a10':a10,'a60':a60,'p5':p5,'p10':p10,'p60':p60,
                     'base_layered_pnl':layer_base,'base_layer':base_layer,'triple_pnl':triple,'layer':layer,
                     'base_delta':layer_base-base,'triple_delta':triple-base,'incremental_vs_base':triple-layer_base})
    f517.assert_parent(parents); df=pd.DataFrame(rows); df.to_csv(OUT/'f613_rows.csv',index=False)
    parent=metrics(df.parent_pnl); base=metrics(df.base_layered_pnl); triple=metrics(df.triple_pnl)
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    ov=df[df.a5 & df.a10].copy()
    out={
      'parent':parent,'f69_f65_layered':base,'triple_layered':triple,
      'f69_f65_delta':float(base['pnl']-parent['pnl']),'triple_delta':float(triple['pnl']-parent['pnl']),
      'incremental_fib5_vs_f69_f65':float(triple['pnl']-base['pnl']),
      'incremental_discovery':float(d.incremental_vs_base.sum()),'incremental_validation':float(v.incremental_vs_base.sum()),
      'raw_actions':{'fib5':int(df.a5.sum()),'early10':int(df.a10.sum()),'f65':int(df.a60.sum())},
      'active_layers':df.layer.value_counts().to_dict(),
      'overlaps':{'fib5_early10':int((df.a5&df.a10).sum()),'fib5_f65':int((df.a5&df.a60).sum()),'early10_f65':int((df.a10&df.a60).sum()),'all3':int((df.a5&df.a10&df.a60).sum())},
      'fib5_parent_winners_cut':int(df[df.a5].parent_win.sum()),
      'overlap5_10':ov[['date','period','parent_pnl','p5','p10']].assign(delta5_vs10=lambda x:x.p5-x.p10).to_dict('records'),
      'overlap5_10_aggregate_delta':float((ov.p5-ov.p10).sum()) if len(ov) else 0.0,
      'dd_improvement_vs_parent':float(parent['dd']-triple['dd'])
    }
    out['integration_pass']=bool(out['incremental_fib5_vs_f69_f65']>0 and out['incremental_discovery']>=0 and out['incremental_validation']>0 and out['fib5_parent_winners_cut']==0)
    (OUT/'f613_summary.json').write_text(json.dumps(out,indent=2,default=float))
    md=['# Friday15 F6.13 — Three-Layer Integration','',f"**Status:** COMPLETE — {'INTEGRATION PASS' if out['integration_pass'] else 'NOT PROMOTED'}",'**Live BBC untouched; no rule retuning.**','',
        '## Priority','1. F6.12 Fib +5m; 2. F6.9 +10m; 3. F6.5 +60m.','',
        '## Result',f"- parent PnL **{parent['pnl']:+.3f}**",f"- F6.9+F6.5 layered **{base['pnl']:+.3f}**",f"- three-layer **{triple['pnl']:+.3f}**",
        f"- Fib5 incremental vs existing layers **{out['incremental_fib5_vs_f69_f65']:+.3f}**",f"- incremental D/V **{out['incremental_discovery']:+.3f} / {out['incremental_validation']:+.3f}**",
        f"- triple PF **{triple['pf']:.3f}**, DD **{triple['dd']:.3f}**",f"- overlaps Fib5/EARLY10 **{out['overlaps']['fib5_early10']}**"]
    (OUT/'F6.13_CHECKPOINT.md').write_text('\n'.join(md)+'\n'); print(json.dumps(out,indent=2,default=float),flush=True)
if __name__=='__main__': main()
