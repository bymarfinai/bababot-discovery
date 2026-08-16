"""BTC Friday15 A6.4 — short-horizon executable money geometry.

Motivation: later-period Friday15 BUY retains its clearest directional bias in the
first ~30m, while A6.0 tested minimum 120m hold. This study fills that gap.

Entry: Friday exact 15:00 WIB BUY. Same $500 notional, 0.15% round-trip fee,
conservative same-5m TP+SL => SL. Timeout exits actual final completed 5m close.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

TPS=tuple(round(0.20+0.05*i,2) for i in range(17)) # .20..1.00
SLS=tuple(round(0.20+0.05*i,2) for i in range(17))
HOLDS=(30,45,60,90,120)


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)};idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.hour==15 and d.minute==0:idx.append(im[x[0]])
    sp=int(len(idx)*.60); results=[]
    for hold in HOLDS:
      for tp in TPS:
       for sl in SLS:
        ts=[a60.trade(rows,i,tp,sl,hold) for i in idx]
        if not all(ts):continue
        s=a60.summarize(ts,tp,sl,hold);s['discovery']=a60.subset_summary(ts[:sp]);s['validation']=a60.subset_summary(ts[sp:])
        results.append(s)
    cross=[x for x in results if x['discovery']['pnl']>0 and x['validation']['pnl']>0]
    cross.sort(key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    best=sorted(results,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],x['profit_factor'] or 0),reverse=True)
    stable=sorted([x for x in results if x['positive_blocks']>=6 and x['net_pnl_usd']>0],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0),reverse=True)
    highwr=sorted([x for x in results if x['net_pnl_usd']>0],key=lambda x:(x['net_wr'],x['net_pnl_usd']),reverse=True)
    # Discovery-selected top-10 viewed against validation, explicitly not reselected on validation.
    disc=sorted(results,key=lambda x:(x['discovery']['pnl'],x['discovery']['pf'] or 0),reverse=True)[:20]
    out={'status':'FRIDAY15_A64_SHORT_HORIZON','data':{'fridays':len(idx),'discovery':sp,'validation':len(idx)-sp,'configs':len(results),'tp_range':[min(TPS),max(TPS)],'sl_range':[min(SLS),max(SLS)],'holds':HOLDS},
         'best_full':best[:20],'cross_period_positive':cross[:30],'stable_6of8':stable[:20],'highest_wr_profitable':highwr[:20],'best_discovery_then_validation':disc}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
