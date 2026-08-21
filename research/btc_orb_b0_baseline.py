#!/usr/bin/env python3
"""BTC ORB B0 — frozen baseline reconstruction. Research only."""
from __future__ import annotations
import io, json, os, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
CACHE=Path(os.getenv('ORB_B0_CACHE','/tmp/orb_b0_cache')); CACHE.mkdir(parents=True,exist_ok=True)
OUT_MD=ROOT/'BTC_ORB_B0_Result.md'; OUT_JSON=ROOT/'BTC_ORB_B0_Result.json'; OUT_CSV=ROOT/'BTC_ORB_B0_Trades.csv'
BASE='https://data.binance.vision/data/futures/um'; SYMBOL='BTCUSDT'
START=pd.Timestamp('2023-01-01',tz='UTC'); END=pd.Timestamp('2026-08-21',tz='UTC')
SESSIONS={'ASIA':0,'LONDON':7,'NEW_YORK':13}; OR_MINS=[15,30,60]
GEOMS={'T050_S100':(.50,1.00),'T075_S100':(.75,1.00),'T100_S100':(1.00,1.00),'T075_S075':(.75,.75)}
SEARCH_MIN=180; HOLD_MIN=240; FEE=0.0015
S=requests.Session(); S.headers.update({'User-Agent':'bababot-discovery-orb-b0/1.0'})

def month_iter(a,b):
    cur=pd.Timestamp(a.year,a.month,1,tz='UTC'); last=pd.Timestamp(b.year,b.month,1,tz='UTC')
    while cur<=last:
        yield cur.year,cur.month; cur += pd.offsets.MonthBegin(1)

def get(url,name):
    p=CACHE/name
    if p.exists(): return p.read_bytes()
    r=S.get(url,timeout=60)
    if r.status_code==404:return None
    r.raise_for_status(); p.write_bytes(r.content); return r.content

def readzip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:return pd.read_csv(f,header=None)

def load():
    fs=[]
    for y,m in month_iter(START,END):
        ym=f'{y:04d}-{m:02d}'; name=f'{SYMBOL}-5m-{ym}.zip'
        data=get(f'{BASE}/monthly/klines/{SYMBOL}/5m/{name}',name)
        if data is not None: fs.append(readzip(data)); continue
        d0=pd.Timestamp(y,m,1,tz='UTC'); d1=min(d0+pd.offsets.MonthBegin(1),END)
        for d in pd.date_range(d0,d1-pd.Timedelta(days=1),freq='D'):
            ds=d.strftime('%Y-%m-%d'); dn=f'{SYMBOL}-5m-{ds}.zip'; dd=get(f'{BASE}/daily/klines/{SYMBOL}/5m/{dn}',dn)
            if dd is not None: fs.append(readzip(dd))
    x=pd.concat(fs,ignore_index=True).iloc[:,:12]
    x.columns=['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']
    for c in ['open','high','low','close']:x[c]=pd.to_numeric(x[c],errors='coerce')
    ot=pd.to_numeric(x.open_time,errors='coerce'); unit='us' if ot.dropna().median()>1e14 else 'ms'; x['ts']=pd.to_datetime(ot,unit=unit,utc=True)
    x=x.dropna(subset=['ts','open','high','low','close']).drop_duplicates('ts').sort_values('ts')
    return x[(x.ts>=START)&(x.ts<END)].set_index('ts',drop=False)

def detect(k,day,session_hour,or_min,kind):
    st=pd.Timestamp(day.date(),tz='UTC')+pd.Timedelta(hours=session_hour); rend=st+pd.Timedelta(minutes=or_min)
    orb=k[(k.index>=st)&(k.index<rend)]
    if len(orb)!=or_min//5:return None
    hi=float(orb.high.max()); lo=float(orb.low.min()); width=hi-lo
    if width<=0:return None
    scan=k[(k.index>=rend)&(k.index<rend+pd.Timedelta(minutes=SEARCH_MIN))]
    for t,b in scan.iterrows():
        if kind=='CLASSIC':
            if float(b.close)>hi: return ('LONG',t+pd.Timedelta(minutes=5),hi,lo,width,t)
            if float(b.close)<lo: return ('SHORT',t+pd.Timedelta(minutes=5),hi,lo,width,t)
        else:
            up=float(b.high)>hi and float(b.close)<=hi
            dn=float(b.low)<lo and float(b.close)>=lo
            if up and dn: continue
            if up:return ('SHORT',t+pd.Timedelta(minutes=5),hi,lo,width,t)
            if dn:return ('LONG',t+pd.Timedelta(minutes=5),hi,lo,width,t)
    return None

def trade(k,det,tp_mult,sl_mult):
    side,et,hi,lo,w,trig=det
    if et not in k.index:return None
    entry=float(k.loc[et,'open'])
    if side=='LONG': tp=entry+tp_mult*w; sl=entry-sl_mult*w
    else: tp=entry-tp_mult*w; sl=entry+sl_mult*w
    bars=k[(k.index>=et)&(k.index<et+pd.Timedelta(minutes=HOLD_MIN))]
    if bars.empty:return None
    reason='TIME'; exit_px=float(bars.iloc[-1].close); exit_t=bars.iloc[-1].ts+pd.Timedelta(minutes=5)
    for _,b in bars.iterrows():
        hit_sl=float(b.low)<=sl if side=='LONG' else float(b.high)>=sl
        hit_tp=float(b.high)>=tp if side=='LONG' else float(b.low)<=tp
        if hit_sl: reason='SL'; exit_px=sl; exit_t=b.ts+pd.Timedelta(minutes=5); break
        if hit_tp: reason='TP'; exit_px=tp; exit_t=b.ts+pd.Timedelta(minutes=5); break
    gross=(exit_px/entry-1.0)*(1 if side=='LONG' else -1); net=gross-FEE
    return {'entry_ts':et,'trigger_ts':trig,'side':side,'entry':entry,'exit_ts':exit_t,'exit_px':exit_px,'reason':reason,'win':net>0,'tp_hit':reason=='TP','net_ret':net,'or_width_pct':w/entry,'or_high':hi,'or_low':lo}

def pf(v):
    gp=sum(x for x in v if x>0); gl=-sum(x for x in v if x<=0); return gp/gl if gl>0 else (999.0 if gp>0 else 0.0)

def stat(z):
    if len(z)==0:return {'n':0,'wins':0,'wr':None,'exp':None,'pf':None}
    v=z.net_ret.astype(float).tolist(); wins=sum(x>0 for x in v)
    return {'n':len(v),'wins':wins,'wr':wins/len(v),'exp':float(np.mean(v)),'pf':pf(v)}

def blocks(z):
    z=z.sort_values('entry_ts').reset_index(drop=True); ed=np.linspace(0,len(z),5,dtype=int); out=[]
    for i in range(4):out.append(stat(z.iloc[ed[i]:ed[i+1]]))
    return out

def main():
    k=load(); days=pd.date_range(START.floor('D'),END.floor('D')-pd.Timedelta(days=1),freq='D'); rows=[]
    for day in days:
      for sess,h in SESSIONS.items():
       for om in OR_MINS:
        for kind in ['CLASSIC','FAILED_BREAK']:
         d=detect(k,day,h,om,kind)
         if d is None:continue
         for g,(tm,sm) in GEOMS.items():
          tr=trade(k,d,tm,sm)
          if tr: tr.update({'session':sess,'or_min':om,'trigger':kind,'geom':g}); rows.append(tr)
    df=pd.DataFrame(rows).sort_values('entry_ts'); df.to_csv(OUT_CSV,index=False)
    results=[]
    for keys,z in df.groupby(['session','or_min','trigger','geom']):
        z=z.sort_values('entry_ts').reset_index(drop=True); split=int(len(z)*.70); d=z.iloc[:split]; v=z.iloc[split:]
        ds,vs,ps=stat(d),stat(v),stat(z); bs=blocks(z); posblocks=sum((b['exp'] or -1)>0 for b in bs)
        # one config is one session by construction, so session concentration is 100%; promotion is assessed again on pooled family below.
        results.append({'scope':'single','session':keys[0],'or_min':keys[1],'trigger':keys[2],'geom':keys[3],'disc':ds,'val':vs,'pooled':ps,'positive_blocks':posblocks,'pass70':False})
    # pooled same-rule across all 3 sessions: this is the main baseline candidate.
    for om in OR_MINS:
     for kind in ['CLASSIC','FAILED_BREAK']:
      for g in GEOMS:
       z=df[(df.or_min==om)&(df.trigger==kind)&(df.geom==g)].sort_values('entry_ts').reset_index(drop=True)
       split=int(len(z)*.70); d=z.iloc[:split]; v=z.iloc[split:]; ds,vs,ps=stat(d),stat(v),stat(z); bs=blocks(z); posblocks=sum((b['exp'] or -1)>0 for b in bs)
       counts=z.session.value_counts(); conc=float(counts.max()/len(z)) if len(z) else 1.0
       ok=bool(ps['n']>=300 and ds['n']>=180 and vs['n']>=80 and ps['wr']>=.68 and ds['wr']>=.67 and vs['wr']>=.67 and ps['exp']>0 and ds['exp']>0 and vs['exp']>0 and ds['pf']>1.10 and vs['pf']>1.10 and posblocks>=3 and conc<=.70)
       results.append({'scope':'pooled3','session':'ALL','or_min':om,'trigger':kind,'geom':g,'disc':ds,'val':vs,'pooled':ps,'positive_blocks':posblocks,'session_concentration':conc,'pass70':ok})
    cand=[r for r in results if r['scope']=='pooled3' and r['pass70']]
    cand=sorted(cand,key=lambda r:(r['val']['exp'],r['val']['wr'],r['val']['n']),reverse=True)
    verdict='ROBUST_70_ORB_BASELINE' if cand else 'NO_ROBUST_70_ORB_BASELINE_B0'; champion=cand[0] if cand else None
    ranked=sorted([r for r in results if r['scope']=='pooled3'],key=lambda r:((r['val']['wr'] or 0),(r['val']['exp'] or -9),r['val']['n']),reverse=True)
    out={'protocol':'BTC_ORB_B0','verdict':verdict,'champion':champion,'top10':ranked[:10],'total_trade_rows':len(df)}; OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    md=['# BTC ORB B0 — Result','',f'**Verdict: {verdict}**','',f'Trade rows across frozen configurations: **{len(df):,}**.','', '## Top pooled baselines','', '| OR | Trigger | Geometry | Disc N/WR | Val N/WR | Val Exp | Val PF | Pass70 |','|---:|---|---|---:|---:|---:|---:|---|']
    for r in ranked[:10]:
        md.append(f"| {r['or_min']}m | {r['trigger']} | {r['geom']} | {r['disc']['n']} / {100*r['disc']['wr']:.2f}% | {r['val']['n']} / {100*r['val']['wr']:.2f}% | {100*r['val']['exp']:.3f}% | {r['val']['pf']:.3f} | {r['pass70']} |")
    if champion: md += ['','## Frozen B0 champion','',f"**{champion['trigger']} / {champion['or_min']}m / {champion['geom']} across all three sessions**",'',f"Pooled WR {100*champion['pooled']['wr']:.2f}%; validation WR {100*champion['val']['wr']:.2f}%; validation PF {champion['val']['pf']:.3f}."]
    md += ['','Live BBC untouched. No post-result B0 parameter rescue is authorized.']; OUT_MD.write_text('\n'.join(md)+'\n'); print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
