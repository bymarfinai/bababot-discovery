#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import btc_orb_b0_baseline as b0
import btc_orb_b1_allhour_4h as b1

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_ORB_B2_SimpleFilters_Result.md'
OUT_JSON=ROOT/'BTC_ORB_B2_SimpleFilters_Result.json'
OUT_CSV=ROOT/'BTC_ORB_B2_SimpleFilters_Trades.csv'


def pf(v):
    gp=sum(x for x in v if x>0); gl=-sum(x for x in v if x<=0)
    return gp/gl if gl>0 else (999.0 if gp>0 else 0.0)

def stat(z):
    if len(z)==0:return {'n':0,'wr':None,'exp':None,'pf':None}
    v=z.net_ret.astype(float).tolist(); wins=sum(x>0 for x in v)
    return {'n':len(v),'wr':wins/len(v),'exp':float(np.mean(v)),'pf':pf(v)}

def blocks(z):
    z=z.sort_values('entry_ts').reset_index(drop=True)
    ed=np.linspace(0,len(z),5,dtype=int)
    return [stat(z.iloc[ed[i]:ed[i+1]]) for i in range(4)]

def evaluate(z,parent_val_n):
    z=z.sort_values('entry_ts').reset_index(drop=True)
    split=int(len(z)*.70); d=z.iloc[:split]; v=z.iloc[split:]
    ds,vs,ps=stat(d),stat(v),stat(z)
    bs=blocks(z); pos=sum((x['exp'] if x['exp'] is not None else -9)>0 for x in bs)
    retain=vs['n']/parent_val_n if parent_val_n else 0
    ok=bool(vs['n']>=70 and vs['wr']>=.67 and vs['exp']>0 and vs['pf']>1.10 and pos>=3 and retain>=.50)
    return ds,vs,ps,pos,retain,ok

def main():
    k=b0.load(); h4=b1.make_4h(k)
    rows=[]
    # Frozen parent: reference candle 20:00 UTC, classic breakout, T050_S100.
    for i in range(len(h4)-4):
        ref_t=h4.index[i]
        if int(ref_t.hour)!=20: continue
        ref=h4.iloc[i]; trig=h4.iloc[i+1]
        hi=float(ref.high); lo=float(ref.low); w=hi-lo
        if w<=0: continue
        side=None; boundary=None
        if float(trig.close)>hi: side='LONG'; boundary=hi
        elif float(trig.close)<lo: side='SHORT'; boundary=lo
        if side is None: continue
        tr=b1.t4_trade(h4,i,'CLASSIC',0.50,1.00)
        if tr is None: continue
        cr=max(float(trig.high)-float(trig.low),1e-12)
        body_ratio=abs(float(trig.close)-float(trig.open))/cr
        extension=(float(trig.close)-boundary)/w if side=='LONG' else (boundary-float(trig.close))/w
        tr.update({'body_ratio':body_ratio,'extension':extension,'ref_hour':20})
        rows.append(tr)
    df=pd.DataFrame(rows).sort_values('entry_ts').reset_index(drop=True)
    df.to_csv(OUT_CSV,index=False)

    # Parent split first so retention is measured against frozen parent validation N.
    p_split=int(len(df)*.70); parent_val_n=len(df.iloc[p_split:])
    variants={
      'BASE': pd.Series(True,index=df.index),
      'BODY50': df.body_ratio>=0.50,
      'EXT10': df.extension>=0.10,
      'BODY50_EXT10': (df.body_ratio>=0.50)&(df.extension>=0.10),
    }
    results=[]
    for name,mask in variants.items():
        z=df[mask].copy()
        ds,vs,ps,pos,retain,ok=evaluate(z,parent_val_n)
        results.append({'variant':name,'disc':ds,'val':vs,'pooled':ps,'positive_blocks':pos,'val_retention_vs_parent':retain,'pass67':ok})
    ranked=sorted(results,key=lambda r:(r['pass67'],r['val']['wr'] or 0,r['val']['exp'] or -9,r['val']['n']),reverse=True)
    cand=[r for r in ranked if r['variant']!='BASE' and r['pass67']]
    verdict='SIMPLE_FILTER_IMPROVEMENT_FOUND' if cand else 'NO_SIMPLE_FILTER_IMPROVEMENT_B2'
    champion=cand[0] if cand else None
    out={'protocol':'BTC_ORB_B2_SIMPLE_FILTERS','verdict':verdict,'parent_rows':len(df),'champion':champion,'results':results}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    md=['# BTC ORB B2 — Simple Filters Result','',f'**Verdict: {verdict}**','',f'Frozen parent trades: **{len(df):,}**.','','| Variant | Disc N/WR | Val N/WR | Val Exp | Val PF | Retain | +Blocks | Pass67 |','|---|---:|---:|---:|---:|---:|---:|---|']
    for r in ranked:
        md.append(f"| {r['variant']} | {r['disc']['n']} / {100*r['disc']['wr']:.2f}% | {r['val']['n']} / {100*r['val']['wr']:.2f}% | {100*r['val']['exp']:.3f}% | {r['val']['pf']:.3f} | {100*r['val_retention_vs_parent']:.1f}% | {r['positive_blocks']}/4 | {r['pass67']} |")
    if champion:
        md += ['','## Champion','',f"**{champion['variant']}** — validation WR {100*champion['val']['wr']:.2f}% on {champion['val']['n']} trades, expectancy {100*champion['val']['exp']:.3f}%, PF {champion['val']['pf']:.3f}."]
    md += ['','Only the preregistered BODY50 and EXT10 filters were tested. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str))

if __name__=='__main__': main()
