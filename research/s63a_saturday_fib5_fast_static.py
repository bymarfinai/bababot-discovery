#!/usr/bin/env python3
"""S6.3A fast parity transfer: exact Friday F6.12 FIB5 rule on Saturday static parent.
No tuning; research only; live untouched.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd
import s50_saturday_parent_forensics as s50

OUT=Path(os.getenv('S63A_OUT','s63a_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83

def metrics(p):
    p=np.asarray(p,float); w=int((p>0).sum()); gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peaks=np.maximum.accumulate(np.r_[0.,eq]); dd=float((peaks[1:]-eq).max())
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':len(p),'wins':w,'losses':len(p)-w,'wr':w/len(p),'pnl':float(p.sum()),'exp':float(p.mean()),'pf':gp/gl if gl else math.inf,'dd':dd,'ls':ls}

def main():
    k=s50.load_klines(); f=s50.load_funding(); entries=s50.saturday_entries(k)
    trades=[s50.simulate(k,f,t) for t in entries]
    if len(trades)!=139: raise RuntimeError('N parity')
    # Exact F6.12 decision geometry, vectorized.
    prev_hi=k.high.shift(1).rolling(24,min_periods=12).max()
    prev_lo=k.low.shift(1).rolling(24,min_periods=12).min()
    prev_ref=k.close.shift(1)
    dec_range=100.0*(prev_hi-prev_lo)/prev_ref
    baseline=dec_range.shift(1).rolling(288,min_periods=1).median()
    rows=[]
    for i,(t,tr) in enumerate(zip(entries,trades)):
        hi=float(prev_hi.loc[t]); lo=float(prev_lo.loc[t]); rg=hi-lo
        retr=(hi-float(tr.entry))/rg
        range_pct=100.0*rg/float(tr.entry)
        b=float(baseline.loc[t])
        first5_red=float(k.loc[t,'close'])<float(tr.entry)
        alive5=pd.Timestamp(tr.exit_t)>t+pd.Timedelta(minutes=5)
        action=bool(first5_red and alive5 and retr<=0.382 and np.isfinite(b) and range_pct>b)
        managed=float(tr.pnl); cut=np.nan
        if action:
            cut=float(k.loc[t+pd.Timedelta(minutes=5),'open'])
            managed=s50.NOTIONAL*(cut/float(tr.entry)-1.0)-s50.FEE
        rows.append({'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,'parent_pnl':tr.pnl,'parent_win':tr.pnl>0,'reason':tr.reason,
                     'retr2h':retr,'range2h_pct':range_pct,'baseline':b,'first5_red':first5_red,'action':action,'managed_pnl':managed,'delta':managed-tr.pnl})
    df=pd.DataFrame(rows); df.to_csv(OUT/'s63a_rows.csv',index=False)
    parent=metrics(df.parent_pnl); managed=metrics(df.managed_pnl); a=df[df.action]; d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    out={'parent':parent,'managed':managed,'delta':managed['pnl']-parent['pnl'],'actions':len(a),'winners_cut':int(a.parent_win.sum()),'losers_cut':int((~a.parent_win).sum()),
         'positive_actions':int((a.delta>0).sum()),'negative_actions':int((a.delta<0).sum()),'disc_delta':float(d.delta.sum()),'val_delta':float(v.delta.sum()),
         'action_parent_pnl':float(a.parent_pnl.sum()),'action_managed_pnl':float(a.managed_pnl.sum()),
         'actions_detail':a.to_dict('records')}
    out['transfer_pass']=bool(out['delta']>0 and out['disc_delta']>0 and out['val_delta']>0 and out['winners_cut']==0)
    (OUT/'summary.json').write_text(json.dumps(out,indent=2,default=float))
    (OUT/'S6.3A_CHECKPOINT.md').write_text('\n'.join([
        '# Saturday S6.3A — Exact Friday FIB5 Static Transfer','',f"**Status:** {'TRANSFER PASS' if out['transfer_pass'] else 'TRANSFER NOT PASS'}",'**No Saturday tuning. Live untouched.**','',
        f"- actions: **{out['actions']}**; winners cut **{out['winners_cut']}**; losers cut **{out['losers_cut']}**",
        f"- PnL **{parent['pnl']:+.3f} -> {managed['pnl']:+.3f}**, delta **{out['delta']:+.3f}**",
        f"- D/V delta **{out['disc_delta']:+.3f} / {out['val_delta']:+.3f}**",
        f"- PF **{parent['pf']:.3f} -> {managed['pf']:.3f}**, DD **{parent['dd']:.3f} -> {managed['dd']:.3f}**",
    ])+'\n')
    print(json.dumps(out,indent=2,default=float),flush=True)
if __name__=='__main__': main()
