"""BTC Friday A6.2 — all-clock discovery then validation.

Uses ONLY first 60% Fridays to choose candidate clock-hours by raw directional behavior.
Then runs the fixed A6.0 money grid on those preselected hours and reports last-40%
validation. This is a clock-migration diagnostic, not a production optimizer.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

HORIZONS=(30,60,120,240,360)
SELECT_HOURS=6


def raw(rows,idx,h):
    vals=[]
    for i in idx:
        j=i+h//5
        if j>=len(rows) or rows[j][0]!=rows[i][0]+(h//5)*TF: continue
        vals.append(100*(rows[j][1]-rows[i][1])/rows[i][1])
    if not vals:return {'n':0,'wr':0,'avg':0,'med':0}
    z=sorted(vals)
    return {'n':len(vals),'wr':rnd(100*sum(v>0 for v in vals)/len(vals),2),'avg':rnd(sum(vals)/len(vals),4),'med':rnd(z[len(z)//2],4)}


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    hidx={h:[] for h in range(24)}
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.minute==0: hidx[d.hour].append(im[x[0]])
    # same occurrence counts; split per hour chronologically
    atlas={}; rank=[]
    for h,idx in hidx.items():
        sp=int(len(idx)*.60); di=idx[:sp]; vi=idx[sp:]
        d={str(z):raw(rows,di,z) for z in HORIZONS}; v={str(z):raw(rows,vi,z) for z in HORIZONS}; f={str(z):raw(rows,idx,z) for z in HORIZONS}
        atlas[str(h)]={'n':len(idx),'discovery':d,'validation':v,'full':f}
        for z in HORIZONS:
            q=d[str(z)]
            rank.append({'hour':h,'horizon':z,'wr':q['wr'],'avg':q['avg'],'med':q['med']})
    # Deterministic discovery-only selection: highest directional WR, then avg return; one slot per hour.
    rank.sort(key=lambda x:(x['wr'],x['avg'],x['med']),reverse=True)
    chosen=[]
    for r in rank:
        if r['hour'] not in chosen:
            chosen.append(r['hour'])
        if len(chosen)>=SELECT_HOURS:break
    scans={}; cross_all=[]
    for h in chosen:
        idx=hidx[h]; sp=int(len(idx)*.60); results=[]
        for hold in a60.HOLDS:
          for tp in a60.TPS:
           for sl in a60.SLS:
            ts=[a60.trade(rows,i,tp,sl,hold) for i in idx]
            if not all(t is not None for t in ts):continue
            s=a60.summarize(ts,tp,sl,hold); s['hour']=h
            s['discovery']=a60.subset_summary(ts[:sp]); s['validation']=a60.subset_summary(ts[sp:])
            results.append(s)
            if s['discovery']['pnl']>0 and s['validation']['pnl']>0:cross_all.append(s)
        bd=sorted(results,key=lambda x:(x['discovery']['pnl'],x['discovery']['pf'] or 0),reverse=True)[:10]
        cross=sorted([x for x in results if x['discovery']['pnl']>0 and x['validation']['pnl']>0],key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],x['profit_factor'] or 0),reverse=True)[:20]
        scans[str(h)]={'best_discovery':bd,'cross_period':cross}
    cross_all.sort(key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],x['profit_factor'] or 0),reverse=True)
    out={'status':'FRIDAY_A62_ALLCLOCK_DISCOVERY','selection_method':'first60% only: rank hour-horizon by directional WR then avg return','top_discovery_pairs':rank[:30],'chosen_hours':chosen,'raw_atlas':atlas,'money_scans':scans,'best_cross_period':cross_all[:40]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
