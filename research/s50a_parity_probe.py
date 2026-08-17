#!/usr/bin/env python3
"""Parity-only probe for S5.0A.
Reconstruct exact A7.26 pre-entry state convention and A7.13 60m decision-price convention
from frozen checkpoint aggregates. No new threshold selection and no new trading rule.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import s50_saturday_parent_forensics as s50

SPLIT=83

def row(k,t):
    x=k[k.index<=t]
    return None if x.empty else x.iloc[-1]

def a719_pnl(k,f,t,tr):
    d=t+pd.Timedelta(minutes=240)
    if pd.Timestamp(tr.exit_t)<=d: return tr.pnl,False
    bars=k[(k.index>=t)&(k.index<d)]
    op=float(k.loc[d,'open']); entry=tr.entry
    mfe=float(bars.high.max())/entry-1
    taker=float(np.nanmean(bars.taker_imb.to_numpy()))
    prog=op/entry-1
    act=(mfe>=.005 and mfe<.008 and prog>=.002 and prog<=.004 and taker<0)
    if not act: return tr.pnl,False
    fund,_=s50.funding_cost(k,f,t,d,entry)
    pnl=s50.NOTIONAL*prog-s50.FEE-fund
    return pnl,True

def pre_variant(k,t,kind):
    op=float(k.loc[t,'open'])
    done=t-pd.Timedelta(minutes=5)
    c=float(k.loc[done,'close']); ema=float(k.loc[done,'ema20'])
    if kind=='open_close60':
        pre1=op/float(row(k,t-pd.Timedelta(minutes=60)).close)-1
        pre4=op/float(row(k,t-pd.Timedelta(minutes=240)).close)-1
        slope=ema/float(row(k,t-pd.Timedelta(minutes=65)).ema20)-1
    elif kind=='completed_60_240':
        pre1=c/float(row(k,done-pd.Timedelta(minutes=60)).close)-1
        pre4=c/float(row(k,done-pd.Timedelta(minutes=240)).close)-1
        slope=ema/float(row(k,done-pd.Timedelta(minutes=60)).ema20)-1
    elif kind=='completed_55_235':
        pre1=c/float(row(k,t-pd.Timedelta(minutes=60)).close)-1
        pre4=c/float(row(k,t-pd.Timedelta(minutes=240)).close)-1
        slope=ema/float(row(k,t-pd.Timedelta(minutes=65)).ema20)-1
    elif kind=='open_open':
        pre1=op/float(k.loc[t-pd.Timedelta(minutes=60),'open'])-1
        pre4=op/float(k.loc[t-pd.Timedelta(minutes=240),'open'])-1
        slope=ema/float(row(k,t-pd.Timedelta(minutes=65)).ema20)-1
    else: raise ValueError(kind)
    w=k[(k.index>=t-pd.Timedelta(minutes=60))&(k.index<t)]
    ph=float(w.high.max())
    near=(ph/op-1)<=.001
    return bool(pre1>0 and pre4>0 and op>ema and slope>0 and near)

def fail60(k,t,tr,use_open):
    d=t+pd.Timedelta(minutes=60)
    bars=k[(k.index>=t)&(k.index<d)]
    taker=float(np.nanmean(bars.taker_imb.to_numpy()))
    px=float(k.loc[d,'open']) if use_open else float(bars.iloc[-1].close)
    prog=px/tr.entry-1
    return bool(prog<=-.001 and taker<0),prog,taker

def main():
    k=s50.load_klines(); f=s50.load_funding(); ents=s50.saturday_entries(k)
    trs=[s50.simulate(k,f,t) for t in ents]
    a=[]
    for i,(t,tr) in enumerate(zip(ents,trs)):
        p,act=a719_pnl(k,f,t,tr); a.append((p,act))
    print('A719',len(a),sum(x[1] for x in a),sum(x[0] for x in a),sum(x[0] for x in a[:83]),sum(x[0] for x in a[83:]))
    for kind in ['open_close60','completed_60_240','completed_55_235','open_open']:
        sig=[pre_variant(k,t,kind) for t in ents]
        kept=[a[i][0] for i,s in enumerate(sig) if not s]
        kd=[a[i][0] for i,s in enumerate(sig[:83]) if not s]
        kv=[a[i+83][0] for i,s in enumerate(sig[83:]) if not s]
        print('PRE',kind,'signals',sum(sig),'D',sum(sig[:83]),'V',sum(sig[83:]),'kept',len(kept),'pnl',sum(kept),'D',sum(kd),'V',sum(kv),'dates',[str(ents[i].date()) for i,s in enumerate(sig) if s])
    for use_open in [False,True]:
        sig=[]
        for t,tr in zip(ents,trs):
            s,_,_=fail60(k,t,tr,use_open); sig.append(s)
        losses=sum(s and tr.pnl<=0 for s,tr in zip(sig,trs))
        dl=sum(sig[:83]); vl=sum(sig[83:])
        dloss=sum(sig[i] and trs[i].pnl<=0 for i in range(83)); vloss=sum(sig[i] and trs[i].pnl<=0 for i in range(83,139))
        print('F60','OPEN' if use_open else 'CLOSE','N',sum(sig),'loss',losses,'D',dl,dloss,'V',vl,vloss)

if __name__=='__main__': main()
