#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, pandas as pd
import btc_orb_b0_baseline as b0
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'BTC_ORB_B5_Confirmation_Result.json'; OUTMD=ROOT/'BTC_ORB_B5_Confirmation_Result.md'
RR={'R100':1.0,'R150':1.5}
NY_HOUR_UTC=13
OR_MIN=30
SEARCH_MIN=180
HOLD_MIN=240
FEE=b0.FEE

def pf(v):
    gp=sum(x for x in v if x>0); gl=-sum(x for x in v if x<=0); return gp/gl if gl>0 else (999.0 if gp>0 else 0.0)
def stat(z):
    if len(z)==0:return {'n':0,'wins':0,'wr':None,'exp':None,'pf':None}
    v=z.net_ret.astype(float).tolist(); wins=sum(x>0 for x in v)
    return {'n':len(v),'wins':wins,'wr':wins/len(v),'exp':float(np.mean(v)),'pf':pf(v)}
def simulate(k, day, variant, rr):
    st=pd.Timestamp(day.date(),tz='UTC')+pd.Timedelta(hours=NY_HOUR_UTC); rend=st+pd.Timedelta(minutes=OR_MIN)
    orb=k[(k.index>=st)&(k.index<rend)]
    if len(orb)!=OR_MIN//5:return None
    hi=float(orb.high.max()); lo=float(orb.low.min()); w=hi-lo
    if w<=0:return None
    scan=k[(k.index>=rend)&(k.index<rend+pd.Timedelta(minutes=SEARCH_MIN))]
    side=None; touched=False; outside_seen=False; pulled=False; confirm_t=None
    for t,b in scan.iterrows():
        c=float(b.close); h=float(b.high); l=float(b.low)
        if not touched:
            if h>hi: side='LONG'; touched=True
            elif l<lo: side='SHORT'; touched=True
            else: continue
        if side=='LONG':
            if variant=='OUTSIDE_CLOSE' and c>hi: confirm_t=t; break
            if variant=='RETEST_HOLD' and l<=hi and c>hi: confirm_t=t; break
            if variant=='PULLBACK_CONT':
                if not outside_seen and c>hi: outside_seen=True; continue
                if outside_seen and not pulled:
                    if c<=hi: return None
                    if l<=hi*1.0015: pulled=True
                    continue
                if outside_seen and pulled and c>hi: confirm_t=t; break
        else:
            if variant=='OUTSIDE_CLOSE' and c<lo: confirm_t=t; break
            if variant=='RETEST_HOLD' and h>=lo and c<lo: confirm_t=t; break
            if variant=='PULLBACK_CONT':
                if not outside_seen and c<lo: outside_seen=True; continue
                if outside_seen and not pulled:
                    if c>=lo: return None
                    if h>=lo*0.9985: pulled=True
                    continue
                if outside_seen and pulled and c<lo: confirm_t=t; break
    if confirm_t is None:return None
    et=confirm_t+pd.Timedelta(minutes=5)
    if et not in k.index:return None
    entry=float(k.loc[et,'open']); r=w
    tp=entry+rr*r if side=='LONG' else entry-rr*r
    sl=entry-r if side=='LONG' else entry+r
    bars=k[(k.index>=et)&(k.index<et+pd.Timedelta(minutes=HOLD_MIN))]
    if bars.empty:return None
    reason='TIME'; exit_px=float(bars.iloc[-1].close)
    for _,b in bars.iterrows():
        hs=float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
        hl=float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
        if hl: reason='SL'; exit_px=sl; break
        if hs: reason='TP'; exit_px=tp; break
    gross=(exit_px/entry-1)*(1 if side=='LONG' else -1); net=gross-FEE
    return {'entry_ts':et,'side':side,'variant':variant,'rr':rr,'net_ret':net,'reason':reason}
def main():
    k=b0.load(); days=pd.date_range(b0.START.floor('D'),b0.END.floor('D')-pd.Timedelta(days=1),freq='D'); rows=[]
    for d in days:
        for v in ['OUTSIDE_CLOSE','RETEST_HOLD','PULLBACK_CONT']:
            for name,r in RR.items():
                tr=simulate(k,d,v,r)
                if tr: tr['rr_name']=name; rows.append(tr)
    df=pd.DataFrame(rows); res=[]
    for (v,r),z in df.groupby(['variant','rr_name']):
        z=z.sort_values('entry_ts').reset_index(drop=True); cut=int(len(z)*.70); d=z.iloc[:cut]; q=z.iloc[cut:]
        weeks=max(1,(z.entry_ts.max()-z.entry_ts.min()).days/7) if len(z)>1 else 1
        res.append({'variant':v,'rr':r,'disc':stat(d),'val':stat(q),'pooled':stat(z),'trades_per_week':len(z)/weeks})
    res.sort(key=lambda x:((x['val']['wr'] or 0),(x['val']['exp'] or -9)),reverse=True)
    out={'protocol':'BTC_ORB_B5_CONFIRMATION','results':res}
    OUT.write_text(json.dumps(out,indent=2,default=str)+'\n')
    lines=['# BTC ORB B5 — Confirmation Layer Result','','| Variant | RR | Val N/W/WR | Val Exp | PF | Trades/wk |','|---|---:|---:|---:|---:|---:|']
    for x in res:
        a=x['val']; lines.append(f"| {x['variant']} | {x['rr']} | {a['n']} / {a['wins']} / {100*a['wr']:.2f}% | {100*a['exp']:.3f}% | {a['pf']:.3f} | {x['trades_per_week']:.2f} |")
    OUTMD.write_text('\n'.join(lines)+'\n'); print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
