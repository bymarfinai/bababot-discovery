#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import btc_h1_low_reject_structure_lr1 as dataio

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Weekly100_Causal_W100V1_Result.md'; OUT_JSON=ROOT/'BTC_Weekly100_Causal_W100V1_Result.json'; OUT_TRADES=ROOT/'BTC_Weekly100_Causal_W100V1_Trades.csv'; OUT_AUG=ROOT/'BTC_Weekly100_Causal_W100V1_August.csv'
FEE=.0015; NOTIONAL=500.
EXT0=pd.Timestamp('2020-01-01',tz='UTC'); EXT1=pd.Timestamp('2022-01-01',tz='UTC')
DEV0=pd.Timestamp('2022-01-01',tz='UTC'); DEV1=pd.Timestamp('2025-01-01',tz='UTC')
VAL0=pd.Timestamp('2025-01-01',tz='UTC'); VAL1=pd.Timestamp('2026-07-30',tz='UTC')
AUG0=pd.Timestamp('2026-08-01',tz='UTC'); AUG1=pd.Timestamp('2026-08-20',tz='UTC')
PARTS={'external':(EXT0,EXT1),'development':(DEV0,DEV1),'reference_validation':(VAL0,VAL1),'august':(AUG0,AUG1)}

def week_id(ts):
    x=pd.Timestamp(ts).isocalendar(); return f'{int(x.year)}-W{int(x.week):02d}'

def make_bars(x,tf):
    z=x.set_index('ts')[['open','high','low','close']].copy()
    if tf=='H1': return z
    return z.resample('4h',origin='start_day',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()

def opportunities(bars,tf):
    rows=[]
    for i in range(len(bars)-8):
        ref,trig=bars.iloc[i],bars.iloc[i+1]; w=float(ref.high-ref.low); rg=float(trig.high-trig.low)
        if w<=0 or rg<=0: continue
        side=None; ext=0.
        if float(trig.close)>float(ref.high): side='LONG'; ext=(float(trig.close)-float(ref.high))/w
        elif float(trig.close)<float(ref.low): side='SHORT'; ext=(float(ref.low)-float(trig.close))/w
        if side is None: continue
        body=abs(float(trig.close)-float(trig.open)); et=bars.index[i+2]
        rows.append({'tf':tf,'i':i,'entry_ts':et,'week':week_id(et),'side':side,'ref_width':w,'score':ext*(body/rg),'extension':ext,'body_ratio':body/rg,'entry':float(bars.iloc[i+2].open)})
    return pd.DataFrame(rows)

def represented_weeks(bars,a,b): return len({week_id(t) for t in bars[(bars.index>=a)&(bars.index<b)].index})

def calibrate(opp,bars):
    d=opp[(opp.entry_ts>=DEV0)&(opp.entry_ts<DEV1)]; W=represented_weeks(bars,DEV0,DEV1); M=len(d)
    if not W or not M: raise RuntimeError('no development sample')
    q=max(0.,1.-W/M); return float(np.quantile(d.score.astype(float),q)),q,W,M

def select_weekly(opp,thr):
    q=opp[opp.score>=thr].sort_values('entry_ts').copy()
    return q.groupby('week',sort=False,group_keys=False).head(1).reset_index(drop=True) if len(q) else q

def execute(bars,sel):
    pos={t:i for i,t in enumerate(bars.index)}; out=[]
    for _,r in sel.iterrows():
        et=pd.Timestamp(r.entry_ts)
        if et not in pos: continue
        fut=bars.iloc[pos[et]:pos[et]+6]
        if len(fut)<6: continue
        d=r.to_dict(); e=float(r.entry); w=float(r.ref_width); side=r.side
        if side=='LONG': sl=e-w; tp=e+w+.0030*e
        else: sl=e+w; tp=e-w-.0030*e
        reason='TIME'; xp=float(fut.iloc[-1].close); xt=fut.index[-1]
        for t,b in fut.iterrows():
            hs=float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
            ht=float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
            if hs: reason='SL'; xp=sl; xt=t; break
            if ht: reason='TP'; xp=tp; xt=t; break
        raw=(xp/e-1.)*(1 if side=='LONG' else -1); net=raw-FEE
        d.update({'sl':sl,'tp':tp,'risk_frac':w/e,'reason':reason,'exit_ts':xt,'net_ret':net,'pnl':net*NOTIONAL}); out.append(d)
    return pd.DataFrame(out)

def pf(v):
    a=np.asarray(v,float); gp=a[a>0].sum(); gl=-a[a<=0].sum(); return float(gp/gl) if gl>0 else (999. if gp>0 else 0.)

def stat(z,weeks):
    if z.empty: return {'n':0,'tp':0,'sl':0,'time':0,'decisive_wr':None,'positive_wr':None,'pnl':0.,'exp':None,'pf':None,'trades_per_week':0.,'weeks_traded':0,'weeks_total':weeks,'weeks_no_trade':weeks}
    dec=z[z.reason.isin(['TP','SL'])]
    return {'n':int(len(z)),'tp':int((z.reason=='TP').sum()),'sl':int((z.reason=='SL').sum()),'time':int((z.reason=='TIME').sum()),'decisive_wr':float((dec.reason=='TP').mean()) if len(dec) else None,'positive_wr':float((z.net_ret>0).mean()),'pnl':float(z.pnl.sum()),'exp':float(z.pnl.mean()),'pf':pf(z.net_ret),'trades_per_week':float(len(z)/weeks) if weeks else None,'weeks_traded':int(z.week.nunique()),'weeks_total':int(weeks),'weeks_no_trade':int(max(0,weeks-z.week.nunique()))}

def blocks(z):
    z=z.sort_values('entry_ts').reset_index(drop=True)
    if z.empty:return []
    ed=np.linspace(0,len(z),5,dtype=int); out=[]
    for i in range(4):
        q=z.iloc[ed[i]:ed[i+1]]; dec=q[q.reason.isin(['TP','SL'])]
        out.append({'block':f'B{i+1}','n':int(len(q)),'tp':int((q.reason=='TP').sum()),'sl':int((q.reason=='SL').sum()),'time':int((q.reason=='TIME').sum()),'wr':float((dec.reason=='TP').mean()) if len(dec) else None,'pnl':float(q.pnl.sum())})
    return out

def pct(v): return '-' if v is None else f'{100*float(v):.2f}%'
def money(v): return '-' if v is None else f'${float(v):+.2f}'
def pfmt(v): return '-' if v is None else f'{float(v):.3f}'

def main():
    x=dataio.load_1h().copy(); x['ts']=pd.to_datetime(x.ts,utc=True); x=x.sort_values('ts').drop_duplicates('ts').reset_index(drop=True)
    result={'protocol':'BTC_WEEKLY100_CAUSAL_W100V1','coverage':{'first':str(x.ts.min()),'last':str(x.ts.max()),'h1_rows':int(len(x))},'timeframes':{}}; ats=[]
    for tf in ['H1','H4']:
        bars=make_bars(x,tf); opp=opportunities(bars,tf); thr,q,dw,dm=calibrate(opp,bars); sel=select_weekly(opp,thr); tr=execute(bars,sel)
        rr={'threshold':thr,'quantile':q,'development_weeks':dw,'development_opportunities':dm,'raw_opportunities':int(len(opp)),'partitions':{},'blocks':{}}
        for name,(a,b) in PARTS.items():
            z=tr[(tr.entry_ts>=a)&(tr.entry_ts<b)].copy(); weeks=represented_weeks(bars,a,b); rr['partitions'][name]=stat(z,weeks); rr['blocks'][name]=blocks(z)
        result['timeframes'][tf]=rr; ats.append(tr)
    robust=[]; high=[]
    for tf,r in result['timeframes'].items():
        e=r['partitions']['external']; v=r['partitions']['reference_validation']; eb=r['blocks']['external']; vb=r['blocks']['reference_validation']; ep=sum(b['pnl']>0 for b in eb); vp=sum(b['pnl']>0 for b in vb)
        if e['n']>=20 and v['n']>=20 and e['decisive_wr']==1. and v['decisive_wr']==1. and e['pnl']>0 and v['pnl']>0 and ep>=3 and vp>=3: robust.append(tf)
        if e['n']>=20 and v['n']>=20 and (e['decisive_wr'] or 0)>=.80 and (v['decisive_wr'] or 0)>=.80 and e['pnl']>0 and v['pnl']>0 and ep>=3 and vp>=3: high.append(tf)
    result['W100V1_ROBUST_100_FOUND']=bool(robust); result['W100V1_ROBUST_100_TIMEFRAMES']=robust; result['W100V1_HIGH_PRECISION_CANDIDATE']=bool(high); result['W100V1_HIGH_PRECISION_TIMEFRAMES']=high
    alltr=pd.concat(ats,ignore_index=True); alltr.to_csv(OUT_TRADES,index=False); alltr[(alltr.entry_ts>=AUG0)&(alltr.entry_ts<AUG1)].to_csv(OUT_AUG,index=False); OUT_JSON.write_text(json.dumps(result,indent=2,default=str)+'\n')
    md=['# BTC Weekly-100 Causal Search W100-V1 — Result','',f"Coverage **{x.ts.min()} -> {x.ts.max()}**, official H1 rows **{len(x):,}**.",'','Development-only strength threshold targets ~1 raw breakout/week; first above-threshold signal per ISO week only. Net RR1:1 after 0.15% fee; H1 hold6H; H4 hold24H; adverse-first.','','| TF | Threshold | Partition | N | Trades/wk | Weeks | TP/SL/TIME | Decisive WR | Positive WR | PnL | Exp | PF |','|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for tf,r in result['timeframes'].items():
        for p in ['development','reference_validation','external','august']:
            s=r['partitions'][p]
            md.append(f"| {tf} | {r['threshold']:.6f} | {p} | {s['n']} | {s['trades_per_week']:.2f} | {s['weeks_traded']}/{s['weeks_total']} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['decisive_wr'])} | {pct(s['positive_wr'])} | {money(s['pnl'])} | {money(s['exp'])} | {pfmt(s['pf'])} |")
    for tf,r in result['timeframes'].items():
        md += ['',f'## {tf} blocks','']
        for p in ['reference_validation','external']:
            md.append(f'**{p}**')
            for b in r['blocks'][p]: md.append(f"- {b['block']}: N{b['n']}, {b['tp']}TP/{b['sl']}SL/{b['time']}TIME, WR {pct(b['wr'])}, PnL {money(b['pnl'])}")
    md += ['','## Verdicts','',f"**W100V1_ROBUST_100_FOUND: {'PASS' if robust else 'FAIL'}**",f"Robust 100% timeframes: {', '.join(robust) if robust else 'none'}",f"**W100V1_HIGH_PRECISION_CANDIDATE: {'PASS' if high else 'FAIL'}**",f"High-precision timeframes: {', '.join(high) if high else 'none'}",'','No post-result threshold, weekday/session/side, RR, hold, or weekly-selection rescue.']
    OUT_MD.write_text('\n'.join(md)+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
