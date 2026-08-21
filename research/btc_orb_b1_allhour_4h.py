#!/usr/bin/env python3
"""BTC ORB B1 — all-hour intraday ORB + strict 4H breakout baseline."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import btc_orb_b0_baseline as b0

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_ORB_B1_AllHour_4H_Result.md'
OUT_JSON=ROOT/'BTC_ORB_B1_AllHour_4H_Result.json'
OUT_CSV=ROOT/'BTC_ORB_B1_AllHour_4H_Candidates.csv'
GEOMS=b0.GEOMS


def pf(v):
    gp=sum(x for x in v if x>0); gl=-sum(x for x in v if x<=0)
    return gp/gl if gl>0 else (999.0 if gp>0 else 0.0)

def stat(z):
    if len(z)==0:return {'n':0,'wr':None,'exp':None,'pf':None}
    v=z.net_ret.astype(float).tolist(); wins=sum(x>0 for x in v)
    return {'n':len(v),'wr':wins/len(v),'exp':float(np.mean(v)),'pf':pf(v)}

def blocks(z):
    z=z.sort_values('entry_ts').reset_index(drop=True); ed=np.linspace(0,len(z),5,dtype=int)
    return [stat(z.iloc[ed[i]:ed[i+1]]) for i in range(4)]

def gate(z):
    z=z.sort_values('entry_ts').reset_index(drop=True); split=int(len(z)*.70); d=z.iloc[:split]; v=z.iloc[split:]
    ds,vs,ps=stat(d),stat(v),stat(z); bs=blocks(z); pos=sum((x['exp'] if x['exp'] is not None else -9)>0 for x in bs)
    ok=bool(ps['n']>=250 and ds['n']>=150 and vs['n']>=70 and ps['wr']>=.68 and ds['wr']>=.67 and vs['wr']>=.67 and ds['exp']>0 and vs['exp']>0 and ds['pf']>1.10 and vs['pf']>1.10 and pos>=3)
    return ds,vs,ps,pos,ok

def track_a(k):
    days=pd.date_range(b0.START.floor('D'),b0.END.floor('D')-pd.Timedelta(days=1),freq='D'); rows=[]
    for day in days:
      for hour in range(24):
       for om in b0.OR_MINS:
        for kind in ['CLASSIC','FAILED_BREAK']:
         det=b0.detect(k,day,hour,om,kind)
         if det is None: continue
         for geom,(tm,sm) in GEOMS.items():
          tr=b0.trade(k,det,tm,sm)
          if tr:
           tr.update({'track':'ALL_HOUR','anchor_hour':hour,'or_min':om,'trigger':kind,'geom':geom}); rows.append(tr)
    return pd.DataFrame(rows)

def make_4h(k):
    x=k[['open','high','low','close']].copy()
    return x.resample('4h',origin='start_day',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()

def t4_trade(h4, i, kind, tm, sm):
    if i+2>=len(h4):return None
    ref=h4.iloc[i]; trig=h4.iloc[i+1]; ref_t=h4.index[i]; trig_t=h4.index[i+1]
    hi=float(ref.high); lo=float(ref.low); w=hi-lo
    if w<=0:return None
    side=None
    if kind=='CLASSIC':
        if float(trig.close)>hi: side='LONG'
        elif float(trig.close)<lo: side='SHORT'
    else:
        up=float(trig.high)>hi and float(trig.close)<=hi
        dn=float(trig.low)<lo and float(trig.close)>=lo
        if up and not dn:side='SHORT'
        elif dn and not up:side='LONG'
    if side is None:return None
    et=h4.index[i+2]; entry=float(h4.iloc[i+2].open)
    tp=entry+tm*w if side=='LONG' else entry-tm*w
    sl=entry-sm*w if side=='LONG' else entry+sm*w
    fut=h4.iloc[i+2:i+5]
    if fut.empty:return None
    reason='TIME'; exit_px=float(fut.iloc[-1].close); exit_t=fut.index[-1]+pd.Timedelta(hours=4)
    for t,b in fut.iterrows():
        hit_sl=float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
        hit_tp=float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
        if hit_sl:reason='SL';exit_px=sl;exit_t=t+pd.Timedelta(hours=4);break
        if hit_tp:reason='TP';exit_px=tp;exit_t=t+pd.Timedelta(hours=4);break
    gross=(exit_px/entry-1)*(1 if side=='LONG' else -1); net=gross-b0.FEE
    return {'track':'H4','anchor_hour':int(ref_t.hour),'or_min':240,'trigger':kind,'geom':None,'entry_ts':et,'side':side,'net_ret':net,'reason':reason,'ref_t':ref_t,'trigger_ts':trig_t}

def track_b(k):
    h4=make_4h(k); rows=[]
    for i in range(len(h4)-4):
      for kind in ['CLASSIC','FAILED_BREAK']:
       for geom,(tm,sm) in GEOMS.items():
        tr=t4_trade(h4,i,kind,tm,sm)
        if tr:tr['geom']=geom;rows.append(tr)
    return pd.DataFrame(rows)

def main():
    k=b0.load(); a=track_a(k); b=track_b(k); df=pd.concat([a,b],ignore_index=True)
    results=[]
    # all-hour cells: exact anchor hour
    for keys,z in a.groupby(['anchor_hour','or_min','trigger','geom']):
        ds,vs,ps,pos,ok=gate(z)
        results.append({'track':'ALL_HOUR','anchor_hour':int(keys[0]),'or_min':int(keys[1]),'trigger':keys[2],'geom':keys[3],'disc':ds,'val':vs,'pooled':ps,'positive_blocks':pos,'pass70':ok})
    # 4H cells: each UTC 4H anchor separately and pooled across anchors
    for keys,z in b.groupby(['anchor_hour','trigger','geom']):
        ds,vs,ps,pos,ok=gate(z)
        results.append({'track':'H4','anchor_hour':int(keys[0]),'or_min':240,'trigger':keys[1],'geom':keys[2],'disc':ds,'val':vs,'pooled':ps,'positive_blocks':pos,'pass70':ok})
    for kind in ['CLASSIC','FAILED_BREAK']:
      for geom in GEOMS:
       z=b[(b.trigger==kind)&(b.geom==geom)]
       ds,vs,ps,pos,ok=gate(z)
       results.append({'track':'H4_POOLED','anchor_hour':'ALL','or_min':240,'trigger':kind,'geom':geom,'disc':ds,'val':vs,'pooled':ps,'positive_blocks':pos,'pass70':ok})
    cand=[r for r in results if r['pass70']]
    ranked=sorted(results,key=lambda r:((r['val']['wr'] or 0),(r['val']['exp'] or -9),(r['val']['n'] or 0)),reverse=True)
    verdict='ROBUST_70_CANDIDATE_B1' if cand else 'NO_ROBUST_70_CANDIDATE_B1'
    out={'protocol':'BTC_ORB_B1_ALLHOUR_4H','verdict':verdict,'candidates':cand,'top20':ranked[:20],'trade_rows':{'all_hour':len(a),'h4':len(b)}}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    pd.DataFrame([{'track':r['track'],'anchor_hour':r['anchor_hour'],'or_min':r['or_min'],'trigger':r['trigger'],'geom':r['geom'],'disc_n':r['disc']['n'],'disc_wr':r['disc']['wr'],'val_n':r['val']['n'],'val_wr':r['val']['wr'],'val_exp':r['val']['exp'],'val_pf':r['val']['pf'],'pass70':r['pass70']} for r in results]).to_csv(OUT_CSV,index=False)
    md=['# BTC ORB B1 — All-Hour + 4H Result','',f'**Verdict: {verdict}**','',f"All-hour trade rows: **{len(a):,}**; 4H trade rows: **{len(b):,}**.",'','## Top validation-ranked cells','','| Track | Hour UTC | OR | Trigger | Geometry | Disc N/WR | Val N/WR | Val Exp | PF | Pass70 |','|---|---:|---:|---|---|---:|---:|---:|---:|---|']
    for r in ranked[:20]:
        md.append(f"| {r['track']} | {r['anchor_hour']} | {r['or_min']}m | {r['trigger']} | {r['geom']} | {r['disc']['n']} / {100*r['disc']['wr']:.2f}% | {r['val']['n']} / {100*r['val']['wr']:.2f}% | {100*r['val']['exp']:.3f}% | {r['val']['pf']:.3f} | {r['pass70']} |")
    md += ['','Live BBC untouched. No post-result hour/geometry rescue inside B1.']; OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
