"""Saturday18 A7.1 — extend A7.0 boundary to test long runners without changing entry."""
import json
from btc_temporal_saturday18_a70_money_geometry import load, ldt, rnd, TF, EVAL_START, EVAL_END, trade, summarize, subset_summary

TPS=(1.20,1.40,1.60,1.80,2.00,2.20,2.40,2.60,2.80,3.00)
SLS=(0.70,0.80,0.90,1.00,1.10,1.20,1.30,1.40,1.50)
HOLDS=(480,720,960,1200,1440)

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==5 and d.hour==18 and d.minute==0: idx.append(im[x[0]])
    split=int(len(idx)*.60)
    results=[]
    for hold in HOLDS:
      for tp in TPS:
       for sl in SLS:
        ts=[trade(rows,i,tp,sl,hold) for i in idx]
        if all(t is not None for t in ts):
            s=summarize(ts,tp,sl,hold)
            s['discovery']=subset_summary(ts[:split]); s['validation']=subset_summary(ts[split:])
            s['cross_period']=s['discovery']['pnl']>0 and s['validation']['pnl']>0
            results.append(s)
    bynet=sorted(results,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)
    cross=sorted([x for x in results if x['cross_period']],key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    stable=sorted([x for x in results if x['positive_blocks']>=6 and x['net_pnl_usd']>0],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    balanced=sorted([x for x in cross if x['positive_blocks']>=6],key=lambda x:(x['expectancy_usd']/(1+x['max_dd_usd']/25),x['profit_factor'] or 0,-x['max_loss_streak']),reverse=True)
    out={'status':'SATURDAY18_A71_BOUNDARY_EXTENSION','data':{'saturdays':len(idx),'discovery_n':split,'validation_n':len(idx)-split,'configs':len(results),'tp_range':[min(TPS),max(TPS)],'sl_range':[min(SLS),max(SLS)],'holds':HOLDS},'best_net':bynet[:25],'best_cross_period':cross[:25],'best_stable':stable[:25],'best_balanced':balanced[:25]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
