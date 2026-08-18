#!/usr/bin/env python3
"""SUN1.4 — causal Sunday 09:00 SELL -> reverse BUY after +0.4% short TP.
Vectorized research harness; live BBC untouched.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50

OUT=Path(os.getenv('SUN14_OUT','sun14_out')); OUT.mkdir(parents=True,exist_ok=True)
NOTIONAL=500.; FEE=.0015*NOTIONAL
START=pd.Timestamp('2023-12-02',tz='UTC'); END=pd.Timestamp('2026-07-30',tz='UTC'); DISC_N=83
FIRST_TP=.004; FIRST_SL=.015; FIRST_H=18
TPS=np.round(np.arange(.3,2.5001,.1),1); SLS=np.round(np.arange(.3,1.5001,.1),1); HOLDS=[1,2,4,6,8,12]
INF=99999

def metrics(a):
    a=np.asarray(a,float)
    if not len(a): return dict(n=0,wins=0,wr=np.nan,pnl=0.,pf=np.nan,dd=0.,exp=np.nan)
    w=a>0; gp=a[w].sum(); gl=-a[~w].sum(); eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=np.max(pk[1:]-eq)
    return dict(n=len(a),wins=int(w.sum()),wr=float(w.mean()),pnl=float(a.sum()),pf=float(gp/gl) if gl>0 else 999.,dd=float(dd),exp=float(a.mean()))

def entries(k):
    idx=k.index; loc=idx+pd.Timedelta(hours=7); m=(idx>=START)&(idx<END)&(loc.dayofweek==6)&(loc.hour==9)&(loc.minute==0); e=list(idx[m])
    if len(e)!=139: raise RuntimeError(f'entry parity {len(e)}')
    return e

def fund_cost(k,f,t0,t1,ep,direction):
    z=f[(f.ts>t0)&(f.ts<=t1)]; q=NOTIONAL/ep; x=0.
    for r in z.itertuples(index=False):
        px=float(k.loc[r.ts,'open']) if r.ts in k.index else ep; x += direction*q*px*float(r.rate)
    return x

def first_leg(k,f,t):
    ep=float(k.loc[t,'open']); tp=ep*(1-FIRST_TP); sl=ep*(1+FIRST_SL); bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(hours=FIRST_H))]
    if len(bars)!=216: raise RuntimeError(f'first path {t} {len(bars)}')
    reason='TIMEOUT'; ex_t=t+pd.Timedelta(hours=FIRST_H); ex_px=float(bars.iloc[-1].close)
    for b in bars.itertuples(index=False):
        if float(b.high)>=sl: reason='SL'; ex_t=b.ts+pd.Timedelta(minutes=5); ex_px=sl; break
        if float(b.low)<=tp: reason='TP'; ex_t=b.ts+pd.Timedelta(minutes=5); ex_px=tp; break
    gross=1-ex_px/ep; pnl=NOTIONAL*gross-FEE-fund_cost(k,f,t,ex_t,ep,-1)
    return dict(entry_t=t,reason=reason,pnl=pnl,rev_t=ex_t if reason=='TP' else None,trigger_min=(ex_t-t).total_seconds()/60 if reason=='TP' else np.nan)

def first_idx(cond):
    anyhit=cond.any(1); return np.where(anyhit,cond.argmax(1),INF).astype(int)

def pack(r):
    d={}
    for k,v in r.items():
        if isinstance(v,np.integer): v=int(v)
        elif isinstance(v,np.floating): v=float(v)
        d[k]=v
    return d

def main():
    k=f517.load_klines(); f=s50.load_funding(); es=entries(k); first=[first_leg(k,f,t) for t in es]
    fp=np.array([x['pnl'] for x in first]); reasons=[x['reason'] for x in first]; trig_idx=np.array([i for i,x in enumerate(first) if x['reason']=='TP'],int)
    n=len(trig_idx); maxbars=max(HOLDS)*12
    rev_entry=np.empty(n); highs=np.empty((n,maxbars)); lows=np.empty_like(highs); closes=np.empty_like(highs); fcum=np.zeros_like(highs)
    for j,i in enumerate(trig_idx):
        rt=first[i]['rev_t']; ep=float(k.loc[rt,'open']); rev_entry[j]=ep; bars=k[(k.index>=rt)&(k.index<rt+pd.Timedelta(hours=max(HOLDS)))].iloc[:maxbars]
        if len(bars)!=maxbars: raise RuntimeError(f'reverse path {rt} {len(bars)}')
        highs[j]=bars.high.to_numpy(float); lows[j]=bars.low.to_numpy(float); closes[j]=bars.close.to_numpy(float)
        q=NOTIONAL/ep; acc=0.
        for bidx,bt in enumerate(bars.index):
            if bt>rt:
                rr=f[f.ts==bt]
                if len(rr): acc += q*float(k.loc[bt,'open'])*float(rr.iloc[0].rate)
            fcum[j,bidx]=acc
    fav=np.empty((n,len(TPS)),int); adv=np.empty((n,len(SLS)),int)
    for a,tp in enumerate(TPS): fav[:,a]=first_idx(highs>=rev_entry[:,None]*(1+tp/100))
    for b,sl in enumerate(SLS): adv[:,b]=first_idx(lows<=rev_entry[:,None]*(1-sl/100))
    orig_i=trig_idx; dmask=orig_i<DISC_N; vmask=~dmask; rows=[]
    for hh in HOLDS:
        hb=hh*12; tout=hb-1
        for a,tp in enumerate(TPS):
            fi=np.where(fav[:,a]<hb,fav[:,a],INF)
            for b,sl in enumerate(SLS):
                ai=np.where(adv[:,b]<hb,adv[:,b],INF); is_sl=(ai<=fi)&(ai<INF); is_tp=(fi<ai)&(fi<INF); ex=np.where(is_sl,ai,np.where(is_tp,fi,tout)).astype(int)
                gross=np.empty(n); gross[is_tp]=tp/100; gross[is_sl]=-sl/100; rem=~(is_tp|is_sl); gross[rem]=closes[rem,tout]/rev_entry[rem]-1
                rp=NOTIONAL*gross-FEE-fcum[np.arange(n),ex]
                chain=fp.copy(); chain[orig_i]+=rp
                dm=metrics(rp[dmask]); vm=metrics(rp[vmask]); fm=metrics(rp); dc=metrics(chain[:DISC_N]); vc=metrics(chain[DISC_N:]); fc=metrics(chain)
                rows.append(dict(hold_h=hh,tp_pct=float(tp),sl_pct=float(sl),rr=float(tp/sl),D_rev_n=dm['n'],D_rev_wr=dm['wr'],D_rev_pnl=dm['pnl'],D_rev_pf=dm['pf'],V_rev_n=vm['n'],V_rev_wr=vm['wr'],V_rev_pnl=vm['pnl'],V_rev_pf=vm['pf'],full_rev_wr=fm['wr'],full_rev_pnl=fm['pnl'],full_rev_pf=fm['pf'],D_chain_pnl=dc['pnl'],D_chain_wr=dc['wr'],D_chain_pf=dc['pf'],V_chain_pnl=vc['pnl'],V_chain_wr=vc['wr'],V_chain_pf=vc['pf'],full_chain_pnl=fc['pnl'],full_chain_wr=fc['wr'],full_chain_pf=fc['pf']))
    df=pd.DataFrame(rows); elig=df[(df.D_rev_pnl>0)&(df.D_rev_pf>1)]; champ=(elig if len(elig) else df).sort_values(['D_chain_pnl','D_rev_pnl','D_rev_pf'],ascending=False).iloc[0]
    eq={str(int(r.hold_h)):pack(r) for _,r in df[(df.tp_pct==.4)&(df.sl_pct==.4)].sort_values('hold_h').iterrows()}
    frD=metrics(fp[:DISC_N]); frV=metrics(fp[DISC_N:]); frF=metrics(fp); tm=np.array([first[i]['trigger_min'] for i in trig_idx])
    summary={'status':'COMPLETE_REVERSE_AFTER_04_CAUSAL','definition':{'first_leg':'Sunday 09:00 WIB SELL TP0.4 SL1.5 hold18h','reverse':'BUY next 5m open after first-leg TP','discovery_n':83,'validation_n':56,'reverse_holds_h':HOLDS,'reverse_tp_grid':[.3,2.5,.1],'reverse_sl_grid':[.3,1.5,.1],'fee_rt_pct_each_leg':.15,'notional_each_leg':500,'funding':'historical'},'first_leg':{'full_reason_counts':{x:reasons.count(x) for x in ['TP','SL','TIMEOUT']},'D':frD,'V':frV,'full':frF,'reverse_triggers_full':int(n),'reverse_triggers_D':int(dmask.sum()),'reverse_triggers_V':int(vmask.sum()),'trigger_time_min_median':float(np.median(tm)),'trigger_time_min_p25':float(np.percentile(tm,25)),'trigger_time_min_p75':float(np.percentile(tm,75))},'discovery_selected':pack(champ),'equal_04_04_by_hold':eq,'top20_discovery_chain':[pack(r) for _,r in df.sort_values(['D_chain_pnl','D_rev_pnl'],ascending=False).head(20).iterrows()],'guardrail':'Reverse parameters selected on discovery only. Validation report-only. Reverse entry is next 5m open, never intrabar wick.'}
    (OUT/'sun14_summary.json').write_text(json.dumps(summary,indent=2,default=str)); df.to_csv(OUT/'sun14_surface.csv',index=False)
    c=summary['discovery_selected']; fr=summary['first_leg']; md=['# Sunday 09:00 WIB — SUN1.4 Reverse BUY after SELL +0.4%','','**Status: COMPLETE — causal next-5m reversal; discovery-only selection; live BBC untouched.**','','## First leg',f"- SELL 09:00 TP0.4 / SL1.5 / 18h: full TP/SL/timeout **{fr['full_reason_counts']['TP']}/{fr['full_reason_counts']['SL']}/{fr['full_reason_counts']['TIMEOUT']}**.",f"- Reverse triggers D/V/full: **{fr['reverse_triggers_D']}/{fr['reverse_triggers_V']}/{fr['reverse_triggers_full']}**.",f"- Trigger time median **{fr['trigger_time_min_median']:.0f}m** (P25 {fr['trigger_time_min_p25']:.0f}, P75 {fr['trigger_time_min_p75']:.0f}).",'', '## Discovery-selected reverse BUY',f"- hold **{int(c['hold_h'])}h**, TP **{c['tp_pct']:.1f}%**, SL **{c['sl_pct']:.1f}%**, RR {c['rr']:.2f}.",f"- Reverse D: WR **{100*c['D_rev_wr']:.2f}%**, PnL **${c['D_rev_pnl']:+.2f}**, PF **{c['D_rev_pf']:.2f}**.",f"- Reverse V: WR **{100*c['V_rev_wr']:.2f}%**, PnL **${c['V_rev_pnl']:+.2f}**, PF **{c['V_rev_pf']:.2f}**.",f"- Reverse full: WR **{100*c['full_rev_wr']:.2f}%**, PnL **${c['full_rev_pnl']:+.2f}**, PF **{c['full_rev_pf']:.2f}**.",'','## Combined chain',f"- D **${c['D_chain_pnl']:+.2f}**, WR {100*c['D_chain_wr']:.2f}%, PF {c['D_chain_pf']:.2f}.",f"- V **${c['V_chain_pnl']:+.2f}**, WR {100*c['V_chain_wr']:.2f}%, PF {c['V_chain_pf']:.2f}.",f"- Full **${c['full_chain_pnl']:+.2f}**, WR {100*c['full_chain_wr']:.2f}%, PF {c['full_chain_pf']:.2f}.",'','## Reverse 0.4/0.4 reference']
    for hh,r in eq.items(): md.append(f"- {hh}h: reverse D {r['D_rev_pnl']:+.2f}, V {r['V_rev_pnl']:+.2f}, full {r['full_rev_pnl']:+.2f}; full WR {100*r['full_rev_wr']:.1f}%; chain {r['full_chain_pnl']:+.2f}")
    md += ['','## Guardrail',summary['guardrail']]; (OUT/'SUN1.4_CHECKPOINT.md').write_text('\n'.join(md)+'\n'); print(json.dumps(summary,indent=2,default=str),flush=True)
if __name__=='__main__': main()
