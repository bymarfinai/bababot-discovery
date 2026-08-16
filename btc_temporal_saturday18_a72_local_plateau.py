"""Saturday18 A7.2 — local plateau around long-runner geometry found in A7.1."""
import json
from btc_temporal_saturday18_a70_money_geometry import load, ldt, EVAL_START, EVAL_END, trade, summarize, subset_summary

TPS=(2.4,2.6,2.8,3.0,3.2,3.4,3.6,3.8,4.0)
SLS=(1.0,1.1,1.2,1.3,1.4)
HOLDS=(1080,1200,1320,1440)

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==5 and d.hour==18 and d.minute==0: idx.append(im[x[0]])
    split=int(len(idx)*.60)
    res=[]
    for hold in HOLDS:
      for tp in TPS:
       for sl in SLS:
        ts=[trade(rows,i,tp,sl,hold) for i in idx]
        if not all(t is not None for t in ts): continue
        s=summarize(ts,tp,sl,hold)
        s['discovery']=subset_summary(ts[:split]); s['validation']=subset_summary(ts[split:])
        s['cross_period']=s['discovery']['pnl']>0 and s['validation']['pnl']>0
        res.append(s)
    cross=[x for x in res if x['cross_period']]
    stable=[x for x in cross if x['positive_blocks']>=6]
    bynet=sorted(res,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)
    robust=sorted(stable,key=lambda x:(min(x['discovery']['exp'],x['validation']['exp']),x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    # Plateau summaries by exact hold and TP/SL neighborhoods.
    hold_summary={}
    for h in HOLDS:
        q=[x for x in res if x['hold_min']==h]
        hold_summary[str(h)]={'configs':len(q),'cross':sum(x['cross_period'] for x in q),'stable6':sum(x['cross_period'] and x['positive_blocks']>=6 for x in q),'positive_full':sum(x['net_pnl_usd']>0 for x in q),'median_net':sorted(x['net_pnl_usd'] for x in q)[len(q)//2]}
    out={'status':'SATURDAY18_A72_LOCAL_PLATEAU','data':{'saturdays':len(idx),'configs':len(res),'tp':TPS,'sl':SLS,'holds':HOLDS},'best_net':bynet[:25],'best_robust':robust[:25],'hold_summary':hold_summary}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
