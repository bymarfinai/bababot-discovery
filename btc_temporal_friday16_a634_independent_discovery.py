"""BTC Friday16 A6.34 — independent temporal discovery.

No Friday15 entry/management rules are reused for discovery.
Entry: every Friday exact 16:00 WIB 5m open.
Phase 1: raw BUY vs SELL at 30/60/120/240/360m.
Phase 2: BUY money geometry using same fee/notional/adverse-first policy as Friday15 A6.0.
Research only; live BBC untouched.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

HORIZONS=(30,60,120,240,360)
TPS=a60.TPS; SLS=a60.SLS; HOLDS=a60.HOLDS


def econ(trades):
    p=[x['net_usd'] for x in trades]; n=len(p); pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3),'ls':a60.loss_streak(p)}


def raw(rows,idx,h,side):
    vals=[]; mfes=[]; maes=[]
    for i in idx:
        j=i+h//5
        if j>=len(rows) or rows[j][0]!=rows[i][0]+(h//5)*TF: continue
        e=rows[i][1]; q=rows[i:j]
        close=q[-1][4]
        if side=='BUY':
            ret=100*(close-e)/e
            mfe=max(100*(x[2]-e)/e for x in q); mae=max(100*(e-x[3])/e for x in q)
        else:
            ret=100*(e-close)/e
            mfe=max(100*(e-x[3])/e for x in q); mae=max(100*(x[2]-e)/e for x in q)
        vals.append(ret); mfes.append(mfe); maes.append(mae)
    return {'n':len(vals),'wr':rnd(100*sum(x>0 for x in vals)/len(vals),2),
            'avg_signed_pct':rnd(statistics.mean(vals),4),'median_signed_pct':rnd(statistics.median(vals),4),
            'mfe_med':rnd(statistics.median(mfes),4),'mae_med':rnd(statistics.median(maes),4),
            'mfe_mae_ratio':rnd(statistics.median(mfes)/statistics.median(maes),4) if statistics.median(maes)>0 else None}


def summarize_cfg(rows,idx,tp,sl,hold):
    ts=[a60.trade(rows,i,tp,sl,hold) for i in idx]
    if not all(ts): return None
    s=a60.summarize(ts,tp,sl,hold)
    s['discovery']=econ(ts[:82]); s['validation']=econ(ts[82:])
    s['cross_positive']=s['discovery']['pnl']>0 and s['validation']['pnl']>0
    return s


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.hour==16 and d.minute==0: idx.append(im[x[0]])
    assert len(idx) in (138,139),len(idx)
    split=82 if len(idx)>=138 else int(len(idx)*.6)
    raw_out={}
    for side in ('BUY','SELL'):
        raw_out[side]={str(h):{'full':raw(rows,idx,h,side),'discovery':raw(rows,idx[:split],h,side),'validation':raw(rows,idx[split:],h,side)} for h in HORIZONS}
    results=[]
    for hold in HOLDS:
        for tp in TPS:
            for sl in SLS:
                z=summarize_cfg(rows,idx,tp,sl,hold)
                if z: results.append(z)
    best_net=sorted(results,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)[:20]
    cross=sorted([x for x in results if x['cross_positive']],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)[:20]
    stable=sorted([x for x in results if x['positive_blocks']>=6 and x['cross_positive']],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)[:20]
    highwr=sorted([x for x in results if x['net_pnl_usd']>0],key=lambda x:(x['net_wr'],x['net_pnl_usd']),reverse=True)[:20]
    out={'status':'FRIDAY16_A634_INDEPENDENT_DISCOVERY','data':{'fridays':len(idx),'discovery_n':split,'validation_n':len(idx)-split,
         'entry':'Friday 16:00 WIB exact open','fee_pct':a60.FEE_PCT,'notional_usd':a60.NOTIONAL,'configs':len(results)},
         'raw':raw_out,'best_net':best_net,'best_cross_period':cross,'best_stable':stable,'highest_wr_profitable':highwr}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
