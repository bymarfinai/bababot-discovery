"""BTC Temporal A3.9 — local refinement around A3.8 stable optimum."""
import json
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import trade, summarize, FEE_PCT, NOTIONAL

TPS=(1.25,1.3,1.35,1.4,1.45,1.5,1.55)
SLS=(0.7,0.75,0.8,0.85,0.9)
HOLDS=(360,420,480,540,600)

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
    stable=[x for x in res if x['positive_blocks']>=6 and x['net_pnl_usd']>0]
    bynet=sorted(res,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)
    st=sorted(stable,key=lambda x:(x['net_pnl_usd'],x['profit_factor'],-x['max_dd_usd']),reverse=True)
    balanced=sorted(stable,key=lambda x:(x['expectancy_usd']/(1+x['max_dd_usd']/25),-x['max_loss_streak'],x['profit_factor']),reverse=True)
    out={'status':'A39_TUESDAY_MONEY_LOCAL_REFINE','data':{'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'tuesdays':len(idx),'fee_roundtrip_pct':FEE_PCT,'notional_usd':NOTIONAL,'grid_configs':len(res)},'best_net':bynet[:20],'best_stable':st[:20],'best_balanced':balanced[:20]}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),'TUESDAYS',len(idx),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
