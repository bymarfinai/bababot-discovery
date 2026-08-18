#!/usr/bin/env python3
"""SUN1.5 — Transfer Tuesday static TP/SL geometry to selected Sunday SELL hours.
Research only; live BBC untouched.

Test exact Tuesday base geometry only (not Tuesday adaptive management):
TP 1.35%, SL 0.80%, max hold 6h, SELL.
Hours: Sunday 09,16,17,20,21 WIB.
$500 notional, 0.15% RT fee, historical funding, adverse-first same-5m ambiguity.
Discovery first 83 Sundays, validation last 56, plus full 139.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun12_sunday_hold_exit_and_allhour_surface as s12

OUT=Path(os.getenv('SUN15_OUT','sun15_out')); OUT.mkdir(parents=True,exist_ok=True)
TP=1.35; SL=0.80; HOLD=6; HOURS=[9,16,17,20,21]; DISC_N=83

def metrics(x):
    a=np.asarray(x,float); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float(np.max(pk[1:]-eq)) if len(eq) else 0.
    return {'n':int(len(a)),'wins':int((a>0).sum()),'wr':float((a>0).mean()),'pnl':float(a.sum()),'pf':float(gp/gl if gl>0 else 999.),'dd':dd,'exp':float(a.mean())}

def simulate_hour(k,fmap,h):
    entries,entry,highs,lows,closes,fund=s12.prepare_hour(k,fmap,h)
    hb=HOLD*12; timeout=hb-1
    fav=s12.first_idx(lows <= entry[:,None]*(1-TP/100.0))
    adv=s12.first_idx(highs >= entry[:,None]*(1+SL/100.0))
    fi=np.where(fav<hb,fav,s12.INF); ai=np.where(adv<hb,adv,s12.INF)
    is_sl=(ai<=fi)&(ai<s12.INF); is_tp=(fi<ai)&(fi<s12.INF)
    ex_idx=np.where(is_sl,ai,np.where(is_tp,fi,timeout)).astype(int)
    gross=np.empty(len(entry),float); gross[is_tp]=TP/100.; gross[is_sl]=-SL/100.
    rem=~(is_tp|is_sl); gross[rem]=1.0-closes[rem,timeout]/entry[rem]
    # short direction = -1 in SUN1.2: pnl = notional*gross - fee + funding cost credit
    fc=fund[np.arange(len(entry)),ex_idx]
    pnl=s12.NOTIONAL*gross-s12.FEE+fc
    return pnl,is_tp,is_sl,rem

def main():
    k=f517.load_klines(); f=s50.load_funding(); fmap=s12.funding_map(k,f)
    rows=[]
    for h in HOURS:
        pnl,tp,sl,to=simulate_hour(k,fmap,h)
        d=metrics(pnl[:DISC_N]); v=metrics(pnl[DISC_N:]); full=metrics(pnl)
        rows.append({'hour_wib':h,'direction':'SELL','tp_pct':TP,'sl_pct':SL,'hold_h':HOLD,
                     'D':d,'V':v,'full':full,'tp_n':int(tp.sum()),'sl_n':int(sl.sum()),'timeout_n':int(to.sum())})
    summary={'status':'COMPLETE_TUESDAY_GEOMETRY_TRANSFER_STATIC_ONLY',
             'definition':{'tp_pct':TP,'sl_pct':SL,'hold_h':HOLD,'direction':'SELL','hours_wib':HOURS,
                           'note':'Tuesday adaptive layers A5.2/A5.9/A5.11 NOT transferred; this isolates base TP/SL/hold geometry.',
                           'notional':500,'fee_rt_pct':0.15,'funding':'historical','ambiguity':'adverse-first'},
             'rows':rows}
    (OUT/'sun15_summary.json').write_text(json.dumps(summary,indent=2))
    md=['# SUN1.5 — Tuesday Base Geometry Transfer to Sunday','',
        '**Static transfer only: TP1.35 / SL0.80 / max hold 6h SELL. Tuesday adaptive management is NOT included.**','',
        '| Sunday hour | D WR | D PnL | D PF | V WR | V PnL | V PF | Full WR | Full PnL | Full PF | TP/SL/TO |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        d,v,fu=r['D'],r['V'],r['full']
        md.append(f"| {r['hour_wib']:02d}:00 | {100*d['wr']:.2f}% | ${d['pnl']:+.2f} | {d['pf']:.2f} | {100*v['wr']:.2f}% | ${v['pnl']:+.2f} | {v['pf']:.2f} | {100*fu['wr']:.2f}% | ${fu['pnl']:+.2f} | {fu['pf']:.2f} | {r['tp_n']}/{r['sl_n']}/{r['timeout_n']} |")
    (OUT/'SUN1.5_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__': main()
