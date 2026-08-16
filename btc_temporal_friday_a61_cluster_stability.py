"""BTC Temporal Friday A6.1 — investigate whether the Friday BUY edge shifts within 14:00-18:00 WIB.

No Tuesday rules are transferred. Each hour is independently evaluated with the same
A6.0 BUY money geometry grid and chronological split. Also reports raw directional
close-return by horizon to diagnose clock migration vs true edge decay.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

HOURS=(14,15,16,17,18)
HORIZONS=(30,60,120,240,360)


def raw_dir(rows,idx,h):
    vals=[]
    for i in idx:
        j=i+h//5
        if j>=len(rows) or rows[j][0]!=rows[i][0]+(h//5)*TF: continue
        e=rows[i][1]; c=rows[j][1]
        vals.append(100*(c-e)/e)
    if not vals:return None
    return {'n':len(vals),'wr':rnd(100*sum(x>0 for x in vals)/len(vals),2),'avg_pct':rnd(sum(vals)/len(vals),4),'median_pct':rnd(sorted(vals)[len(vals)//2],4)}


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    hour_idx={h:[] for h in HOURS}
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.minute==0 and d.hour in hour_idx: hour_idx[d.hour].append(im[x[0]])
    per_hour={}; all_cross=[]
    for h,idx in hour_idx.items():
        sp=int(len(idx)*.60); disc_idx=idx[:sp]; val_idx=idx[sp:]
        raw={'full':{str(z):raw_dir(rows,idx,z) for z in HORIZONS},'discovery':{str(z):raw_dir(rows,disc_idx,z) for z in HORIZONS},'validation':{str(z):raw_dir(rows,val_idx,z) for z in HORIZONS}}
        results=[]
        for hold in a60.HOLDS:
          for tp in a60.TPS:
           for sl in a60.SLS:
            ts=[a60.trade(rows,i,tp,sl,hold) for i in idx]
            if not all(t is not None for t in ts):continue
            s=a60.summarize(ts,tp,sl,hold); s['discovery']=a60.subset_summary(ts[:sp]); s['validation']=a60.subset_summary(ts[sp:])
            s['hour']=h
            results.append(s)
            if s['discovery']['pnl']>0 and s['validation']['pnl']>0: all_cross.append(s)
        fullbest=sorted(results,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)[:10]
        discbest=sorted(results,key=lambda x:(x['discovery']['pnl'],x['discovery']['pf'] or 0),reverse=True)[:10]
        valbest=sorted(results,key=lambda x:(x['validation']['pnl'],x['validation']['pf'] or 0),reverse=True)[:10]
        cross=sorted([x for x in results if x['discovery']['pnl']>0 and x['validation']['pnl']>0],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)[:20]
        per_hour[str(h)]={'n':len(idx),'raw_directional':raw,'best_full':fullbest,'best_discovery':discbest,'best_validation':valbest,'cross_period':cross}
    all_cross.sort(key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    out={'status':'FRIDAY_A61_CLUSTER_STABILITY','hours':HOURS,'per_hour':per_hour,'best_cross_period_all_hours':all_cross[:40]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
