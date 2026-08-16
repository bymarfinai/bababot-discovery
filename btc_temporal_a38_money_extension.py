"""BTC Temporal A3.8 — extend A3.7 because the winner sat on TP/hold grid boundaries."""
import json
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import trade, summarize, FEE_PCT, MARGIN_USD, LEVERAGE, NOTIONAL

TPS=(1.0,1.2,1.4,1.6,1.8,2.0)
SLS=(0.6,0.8,1.0,1.2)
HOLDS=(360,480,720)

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    expected=(EVAL_END-EVAL_START)//TF
    exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows)
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    res=[]
    for hold in HOLDS:
        for tp in TPS:
            for sl in SLS:
                ts=[trade(rows,i,tp,sl,hold) for i in idx]
                if all(t is not None for t in ts):res.append(summarize(ts,tp,sl,hold))
    bynet=sorted(res,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)
    stable=sorted([x for x in res if x['positive_blocks']>=6 and x['net_pnl_usd']>0],key=lambda x:(x['net_pnl_usd'],-x['max_dd_usd']),reverse=True)
    out={'status':'A38_TUESDAY_MONEY_BOUNDARY_EXTENSION','data':{'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'tuesdays':len(idx),'entry':'Tuesday 06:00 WIB SELL','fee_roundtrip_pct':FEE_PCT,'notional_usd':NOTIONAL,'grid_configs':len(res)},'best_net':bynet[:25],'best_stable':stable[:25]}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),'TUESDAYS',len(idx),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
