#!/usr/bin/env python3
"""SUN1.6 — Sunday 16:00 WIB SELL TP-boundary extension.

Purpose: determine whether TP 2.5% was a true local optimum or merely the upper
boundary of SUN1.2's TP grid.

Frozen from SUN1.2 candidate:
- Sunday 16:00 WIB SELL
- max hold 18h
- reference SL 1.4%
- $500 notional, 0.15% round-trip fee, historical funding
- adverse-first same-5m ambiguity

Two predeclared views, both discovery-selected only:
A) Clean TP boundary line: hold 18h, SL fixed 1.4%, TP 1.0..5.0 step 0.1.
B) Small boundary surface: hold 18h, TP 2.0..5.0 step 0.1, SL 1.0..1.8 step 0.1.
Validation is report-only and never used to select.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50

OUT=Path(os.getenv('SUN16_OUT','sun16_out')); OUT.mkdir(parents=True,exist_ok=True)
NOTIONAL=500.0; FEE=0.0015*NOTIONAL
START=pd.Timestamp('2023-12-02',tz='UTC'); END=pd.Timestamp('2026-07-30',tz='UTC')
DISC_N=83; HOLD_H=18; MAX_BARS=HOLD_H*12; INF=10000
TP_LINE=np.round(np.arange(1.0,5.0001,0.1),1)
TP_SURF=np.round(np.arange(2.0,5.0001,0.1),1)
SL_SURF=np.round(np.arange(1.0,1.8001,0.1),1)
REF_SL=1.4

def metrics(a):
    a=np.asarray(a,float); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peak[1:]-eq))
    return {'n':len(a),'wins':int((a>0).sum()),'wr':float((a>0).mean()),'pnl':float(a.sum()),
            'pf':gp/gl if gl>0 else 999.0,'dd':dd,'exp':float(a.mean())}

def entries(k):
    idx=k.index; local=idx+pd.Timedelta(hours=7)
    m=(idx>=START)&(idx<END)&(local.dayofweek==6)&(local.hour==16)&(local.minute==0)
    e=list(idx[m]);
    if len(e)!=139: raise RuntimeError(f'entry parity {len(e)}')
    return e

def funding_map(k,f):
    out={}
    for r in f.itertuples(index=False):
        t=pd.Timestamp(r.ts)
        if t in k.index: out[t]=(float(r.rate),float(k.loc[t,'open']))
    return out

def prepare(k,fmap,e):
    n=len(e); ep=np.empty(n); highs=np.empty((n,MAX_BARS)); lows=np.empty_like(highs); closes=np.empty_like(highs); fc=np.zeros_like(highs)
    for i,t in enumerate(e):
        bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(hours=HOLD_H))].iloc[:MAX_BARS]
        if len(bars)!=MAX_BARS: raise RuntimeError(f'incomplete {t}')
        ep[i]=float(k.loc[t,'open']); highs[i]=bars.high.to_numpy(float); lows[i]=bars.low.to_numpy(float); closes[i]=bars.close.to_numpy(float)
        c=0.0
        for j,bt in enumerate(bars.index):
            if bt>t and bt in fmap:
                rate,px=fmap[bt]
                # short direction=-1; pnl subtract direction*fund => receives positive funding
                c += -1*(NOTIONAL/ep[i])*px*rate
            fc[i,j]=c
    return ep,highs,lows,closes,fc

def first_idx(cond):
    anyhit=cond.any(axis=1); idx=cond.argmax(axis=1)
    return np.where(anyhit,idx,INF).astype(int)

def simulate(ep,highs,lows,closes,fc,tp,sl):
    # SELL: favorable down, adverse up
    fi=first_idx(lows<=ep[:,None]*(1-tp/100.0)); ai=first_idx(highs>=ep[:,None]*(1+sl/100.0))
    is_sl=(ai<=fi)&(ai<INF); is_tp=(fi<ai)&(fi<INF); timeout=~(is_sl|is_tp)
    ex=np.where(is_sl,ai,np.where(is_tp,fi,MAX_BARS-1)).astype(int)
    gross=np.empty(len(ep)); gross[is_tp]=tp/100.0; gross[is_sl]=-sl/100.0
    gross[timeout]=1.0-closes[timeout,MAX_BARS-1]/ep[timeout]
    # fc already signed as short funding cost (negative if short receives positive rate)
    pnl=NOTIONAL*gross-FEE-fc[np.arange(len(ep)),ex]
    return pnl,is_tp,is_sl,timeout

def row(ep,highs,lows,closes,fc,tp,sl):
    pnl,a,b,c=simulate(ep,highs,lows,closes,fc,tp,sl)
    D=metrics(pnl[:DISC_N]); V=metrics(pnl[DISC_N:]); F=metrics(pnl)
    return {'tp_pct':float(tp),'sl_pct':float(sl),'D':D,'V':V,'full':F,
            'tp_n':int(a.sum()),'sl_n':int(b.sum()),'timeout_n':int(c.sum())}

def main():
    k=f517.load_klines(); f=s50.load_funding(); e=entries(k); ep,hi,lo,cl,fc=prepare(k,funding_map(k,f),e)
    line=[row(ep,hi,lo,cl,fc,tp,REF_SL) for tp in TP_LINE]
    surface=[row(ep,hi,lo,cl,fc,tp,sl) for tp in TP_SURF for sl in SL_SURF]
    # discovery-only choices
    line_champ=max(line,key=lambda r:(r['D']['pnl'],r['D']['pf']))
    surf_champ=max(surface,key=lambda r:(r['D']['pnl'],r['D']['pf']))
    ref25=next(r for r in line if abs(r['tp_pct']-2.5)<1e-9)
    # local neighborhood line around winner for readable output
    win_tp=line_champ['tp_pct']; neighborhood=[r for r in line if abs(r['tp_pct']-win_tp)<=0.5+1e-9]
    out={'status':'COMPLETE_BOUNDARY_EXTENSION','definition':{'hour_wib':16,'direction':'SELL','hold_h':18,'discovery_n':83,'validation_n':56,
         'line_tp_grid':[1.0,5.0,0.1],'line_sl_fixed':1.4,'surface_tp_grid':[2.0,5.0,0.1],'surface_sl_grid':[1.0,1.8,0.1],
         'notional':500,'fee_rt_pct':0.15,'funding':'historical','ambiguity':'adverse-first'},
         'reference_tp25_sl14':ref25,'line_discovery_champion':line_champ,'surface_discovery_champion':surf_champ,
         'line_neighborhood':neighborhood,'guardrail':'Selection uses discovery only; validation report-only. This extends the prior upper TP boundary rather than retuning from validation.'}
    (OUT/'sun16_summary.json').write_text(json.dumps(out,indent=2))
    md=['# SUN1.6 — Sunday 16:00 SELL TP Boundary Extension','',
        '**Status: COMPLETE — discovery-only boundary extension; live BBC untouched.**','',
        '## Reference old boundary TP2.5 / SL1.4 / 18h',
        f"- D: WR **{100*ref25['D']['wr']:.2f}%**, PnL **${ref25['D']['pnl']:+.2f}**, PF **{ref25['D']['pf']:.2f}**",
        f"- V: WR **{100*ref25['V']['wr']:.2f}%**, PnL **${ref25['V']['pnl']:+.2f}**, PF **{ref25['V']['pf']:.2f}**",
        f"- Full: WR **{100*ref25['full']['wr']:.2f}%**, PnL **${ref25['full']['pnl']:+.2f}**, PF **{ref25['full']['pf']:.2f}**",'',
        '## TP-line discovery champion (SL fixed 1.4)',
        f"- **TP {line_champ['tp_pct']:.1f}% / SL 1.4% / 18h**",
        f"- D: WR **{100*line_champ['D']['wr']:.2f}%**, PnL **${line_champ['D']['pnl']:+.2f}**, PF **{line_champ['D']['pf']:.2f}**",
        f"- V: WR **{100*line_champ['V']['wr']:.2f}%**, PnL **${line_champ['V']['pnl']:+.2f}**, PF **{line_champ['V']['pf']:.2f}**",
        f"- Full: WR **{100*line_champ['full']['wr']:.2f}%**, PnL **${line_champ['full']['pnl']:+.2f}**, PF **{line_champ['full']['pf']:.2f}**",'',
        '## Extended 2D discovery champion',
        f"- **TP {surf_champ['tp_pct']:.1f}% / SL {surf_champ['sl_pct']:.1f}% / 18h**",
        f"- D: WR **{100*surf_champ['D']['wr']:.2f}%**, PnL **${surf_champ['D']['pnl']:+.2f}**, PF **{surf_champ['D']['pf']:.2f}**",
        f"- V: WR **{100*surf_champ['V']['wr']:.2f}%**, PnL **${surf_champ['V']['pnl']:+.2f}**, PF **{surf_champ['V']['pf']:.2f}**",
        f"- Full: WR **{100*surf_champ['full']['wr']:.2f}%**, PnL **${surf_champ['full']['pnl']:+.2f}**, PF **{surf_champ['full']['pf']:.2f}**",'',
        '## TP-line neighborhood around discovery winner']
    for r in neighborhood:
        md.append(f"- TP {r['tp_pct']:.1f}: D {r['D']['pnl']:+.2f} (WR {100*r['D']['wr']:.1f}%, PF {r['D']['pf']:.2f}); V {r['V']['pnl']:+.2f}; Full {r['full']['pnl']:+.2f}")
    md += ['', '## Guardrail', out['guardrail']]
    (OUT/'SUN1.6_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__': main()
