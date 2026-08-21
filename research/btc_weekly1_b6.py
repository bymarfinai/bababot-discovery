#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, pandas as pd
import btc_orb_b0_baseline as b0
ROOT=Path(__file__).resolve().parent.parent
OUTJ=ROOT/'BTC_WEEKLY1_B6_Result.json'; OUTM=ROOT/'BTC_WEEKLY1_B6_Result.md'
RRS={'R100':1.0,'R125':1.25,'R150':1.5}
FEE=b0.FEE

def rs(k,tf):
    x=k[['open','high','low','close']].resample(tf,origin='start_day',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    pc=x.close.shift(1); tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr']=tr.rolling(14,min_periods=14).mean().shift(1)
    return x.dropna()

def one_trade(x,idx,side,rr,hold):
    e=float(x.iloc[idx].open); atr=float(x.iloc[idx].atr)
    if not np.isfinite(atr) or atr<=0:return None
    tp=e+rr*atr if side=='LONG' else e-rr*atr; sl=e-atr if side=='LONG' else e+atr
    fut=x.iloc[idx:idx+hold]
    if fut.empty:return None
    exit_px=float(fut.iloc[-1].close); reason='TIME'
    for _,b in fut.iterrows():
        hs=float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
        ht=float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
        if hs: exit_px=sl; reason='SL'; break
        if ht: exit_px=tp; reason='TP'; break
    gross=(exit_px/e-1)*(1 if side=='LONG' else -1); net=gross-FEE
    return net,reason

def stat(v):
    if not v:return {'n':0,'wins':0,'wr':None,'exp':None,'pf':None}
    a=np.array(v,float); w=int((a>0).sum()); gp=a[a>0].sum(); gl=-a[a<=0].sum()
    return {'n':len(a),'wins':w,'wr':w/len(a),'exp':float(a.mean()),'pf':float(gp/gl if gl>0 else 999)}

def main():
    k=b0.load(); results=[]
    for tf,hold in [('1h',6),('4h',3)]:
        x=rs(k,tf)
        for dow in range(7):
            hours=range(24) if tf=='1h' else [0,4,8,12,16,20]
            for hour in hours:
                ids=[i for i,t in enumerate(x.index) if t.weekday()==dow and t.hour==hour and i+hold<=len(x)]
                for side in ['LONG','SHORT']:
                    for rn,rr in RRS.items():
                        vals=[]
                        for i in ids:
                            r=one_trade(x,i,side,rr,hold)
                            if r is not None: vals.append(r[0])
                        if len(vals)<100: continue
                        cut=int(len(vals)*.70); d=stat(vals[:cut]); v=stat(vals[cut:]); p=stat(vals)
                        results.append({'tf':tf,'dow':dow,'hour_utc':hour,'side':side,'rr':rn,'disc':d,'val':v,'pooled':p})
    ranked=sorted(results,key=lambda r:((r['val']['wr'] or 0),(r['val']['exp'] or -9),(r['val']['pf'] or 0)),reverse=True)
    strong=[r for r in ranked if r['val']['n']>=40 and r['val']['exp']>0 and r['val']['pf']>1]
    out={'protocol':'BTC_WEEKLY1_B6','strong_count':len(strong),'top30':ranked[:30],'top_strong':strong[:20]}
    OUTJ.write_text(json.dumps(out,indent=2,default=str)+'\n')
    names=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    md=['# BTC Weekly-One B6 — Result','','Exactly one fixed-slot trade per week; ATR(14) risk; fee 0.15%.','','| TF | Day | Hour UTC | Side | RR | Disc N/WR | Val N/W/WR | Val Exp | PF |','|---|---|---:|---|---|---:|---:|---:|---:|']
    for r in ranked[:30]:
        d,v=r['disc'],r['val']; md.append(f"| {r['tf']} | {names[r['dow']]} | {r['hour_utc']:02d}:00 | {r['side']} | {r['rr']} | {d['n']} / {100*d['wr']:.2f}% | {v['n']} / {v['wins']} / {100*v['wr']:.2f}% | {100*v['exp']:.3f}% | {v['pf']:.3f} |")
    OUTM.write_text('\n'.join(md)+'\n'); print(json.dumps(out,indent=2,default=str))
if __name__=='__main__': main()
