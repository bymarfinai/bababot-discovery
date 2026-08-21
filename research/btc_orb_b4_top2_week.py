#!/usr/bin/env python3
from pathlib import Path
import json, numpy as np, pandas as pd
import btc_orb_b0_baseline as b0
import btc_orb_b1_allhour_4h as b1
ROOT=Path(__file__).resolve().parent.parent
RRS={'R100':(1.0,1.0),'R125':(1.25,1.0),'R150':(1.5,1.0)}

def stat(z):
    if len(z)==0:return {'n':0,'wins':0,'wr':None,'exp':None,'pf':None}
    v=z.net_ret.astype(float); wins=int((v>0).sum()); gp=float(v[v>0].sum()); gl=float(-v[v<=0].sum())
    return {'n':len(z),'wins':wins,'wr':wins/len(z),'exp':float(v.mean()),'pf':gp/gl if gl>0 else 999.0}

def blocks(z):
    z=z.sort_values('entry_ts').reset_index(drop=True); ed=np.linspace(0,len(z),5,dtype=int)
    return [stat(z.iloc[ed[i]:ed[i+1]]) for i in range(4)]

def opportunities(h4):
    rows=[]
    for i in range(len(h4)-4):
        ref=h4.iloc[i]; trig=h4.iloc[i+1]; hi=float(ref.high); lo=float(ref.low); w=hi-lo
        if w<=0: continue
        side=None; ext=0.0
        if float(trig.close)>hi: side='LONG'; ext=(float(trig.close)-hi)/w
        elif float(trig.close)<lo: side='SHORT'; ext=(lo-float(trig.close))/w
        if side is None: continue
        body=abs(float(trig.close)-float(trig.open)); rng=max(float(trig.high)-float(trig.low),1e-12); body_ratio=body/rng
        et=h4.index[i+2]
        iso=et.isocalendar(); week=f'{iso.year}-W{int(iso.week):02d}'
        rows.append({'i':i,'entry_ts':et,'side':side,'week':week,'ext_score':ext,'ext_body_score':ext*body_ratio,'anchor_hour':int(h4.index[i].hour)})
    return pd.DataFrame(rows)

def main():
    k=b0.load(); h4=b1.make_4h(k); opp=opportunities(h4); selected=[]
    for rank_col in ['ext_score','ext_body_score']:
        top=opp.sort_values(['week',rank_col,'entry_ts'],ascending=[True,False,True]).groupby('week',group_keys=False).head(2).copy()
        for rr,(tp,sl) in RRS.items():
            for _,r in top.iterrows():
                tr=b1.t4_trade(h4,int(r.i),'CLASSIC',tp,sl)
                if tr:
                    tr.update({'ranking':rank_col,'rr':rr,'week':r.week,'score':float(r[rank_col]),'anchor_hour':int(r.anchor_hour)})
                    selected.append(tr)
    df=pd.DataFrame(selected); results=[]
    for (ranking,rr),z in df.groupby(['ranking','rr']):
        z=z.sort_values('entry_ts').reset_index(drop=True); cut=int(len(z)*.70); d=z.iloc[:cut]; v=z.iloc[cut:]
        weeks=z.week.nunique(); results.append({'ranking':ranking,'rr':rr,'trades_per_week':len(z)/weeks if weeks else None,'disc':stat(d),'val':stat(v),'pooled':stat(z),'blocks':blocks(z)})
    results.sort(key=lambda r:((r['val']['wr'] or 0),(r['val']['exp'] or -9),(r['val']['pf'] or 0)),reverse=True)
    out={'protocol':'BTC_ORB_B4_TOP2_WEEK','opportunities':len(opp),'results':results}
    (ROOT/'BTC_ORB_B4_Top2Week_Result.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
    lines=['# BTC ORB B4 — Top 2 Per Week Result','',f'Raw H4 breakout opportunities: **{len(opp):,}**.','','| Ranking | RR | Trades/wk | Disc N/W/WR | Val N/W/WR | Val Exp | Val PF |','|---|---:|---:|---:|---:|---:|---:|']
    for r in results:
        a,b=r['disc'],r['val']; lines.append(f"| {r['ranking']} | {r['rr']} | {r['trades_per_week']:.2f} | {a['n']} / {a['wins']} / {100*a['wr']:.2f}% | {b['n']} / {b['wins']} / {100*b['wr']:.2f}% | {100*b['exp']:.3f}% | {b['pf']:.3f} |")
    lines += ['','At most two selected H4 opportunities per ISO week. No additional indicators or post-result threshold rescue. Live BBC untouched.']
    (ROOT/'BTC_ORB_B4_Top2Week_Result.md').write_text('\n'.join(lines)+'\n'); df.to_csv(ROOT/'BTC_ORB_B4_Top2Week_Trades.csv',index=False); print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
