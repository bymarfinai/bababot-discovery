#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, pandas as pd
import btc_orb_b0_baseline as b0
import btc_orb_b1_allhour_4h as b1
ROOT=Path(__file__).resolve().parent.parent
GEOMS={'R100':(1.0,1.0),'R125':(1.25,1.0),'R150':(1.5,1.0)}

def stat(z):
    if len(z)==0:return {'n':0,'wins':0,'wr':None,'exp':None,'pf':None}
    v=z.net_ret.astype(float); wins=int((v>0).sum()); gp=float(v[v>0].sum()); gl=float(-v[v<=0].sum())
    return {'n':len(z),'wins':wins,'wr':wins/len(z),'exp':float(v.mean()),'pf':gp/gl if gl>0 else 999.0}
def main():
    k=b0.load(); h4=b1.make_4h(k); rows=[]
    for i in range(len(h4)-4):
        if int(h4.index[i].hour)!=20: continue
        for g,(tp,sl) in GEOMS.items():
            tr=b1.t4_trade(h4,i,'CLASSIC',tp,sl)
            if tr: tr['geom']=g; rows.append(tr)
    df=pd.DataFrame(rows); results=[]
    for g,z in df.groupby('geom'):
        z=z.sort_values('entry_ts').reset_index(drop=True); cut=int(len(z)*.70); d=z.iloc[:cut]; v=z.iloc[cut:]
        ed=np.linspace(0,len(z),5,dtype=int); blocks=[stat(z.iloc[ed[i]:ed[i+1]]) for i in range(4)]
        results.append({'geom':g,'disc':stat(d),'val':stat(v),'pooled':stat(z),'blocks':blocks})
    results.sort(key=lambda r:((r['val']['exp'] or -9),(r['val']['pf'] or 0)),reverse=True)
    useful=[r for r in results if r['val']['exp']>0 and r['val']['pf']>1]
    verdict='POSITIVE_MIN_1R_CANDIDATE_B3' if useful else 'NO_POSITIVE_MIN_1R_CANDIDATE_B3'
    out={'protocol':'BTC_ORB_B3_RR','verdict':verdict,'results':results}
    (ROOT/'BTC_ORB_B3_RR_Result.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    lines=['# BTC ORB B3 — Minimum 1:1 RR Result','',f'**Verdict: {verdict}**','','| RR | Disc N/W/WR | Val N/W/WR | Val Exp | Val PF |','|---|---:|---:|---:|---:|']
    for r in results:
        a,b=r['disc'],r['val']; lines.append(f"| {r['geom']} | {a['n']} / {a['wins']} / {100*a['wr']:.2f}% | {b['n']} / {b['wins']} / {100*b['wr']:.2f}% | {100*b['exp']:.3f}% | {b['pf']:.3f} |")
    lines += ['','No extra filters. Fee 0.15%. Live BBC untouched.']
    (ROOT/'BTC_ORB_B3_RR_Result.md').write_text('\n'.join(lines)+'\n')
    df.to_csv(ROOT/'BTC_ORB_B3_RR_Trades.csv',index=False); print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
