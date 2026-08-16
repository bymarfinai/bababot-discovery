"""A4.3b — summarize WR/PnL frontier for static Tuesday 06:00 SELL TP/SL."""
import json
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import trade, summarize

HOLD=240
GRID=tuple(round(0.20+0.05*i,2) for i in range(21))

def indices(rows):
    im={x[0]:i for i,x in enumerate(rows)}; out=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==1 and d.hour==6 and d.minute==0: out.append(im[x[0]])
    return out

def sim(rows,idx,tp,sl):
    ts=[trade(rows,i,tp,sl,HOLD) for i in idx]
    return summarize(ts,tp,sl,HOLD)

def slim(x):
    return {k:x[k] for k in ('tp_pct','sl_pct','rr','net_wr','net_pnl_usd','expectancy_usd','profit_factor','max_dd_usd','positive_blocks','net_win_trades','net_loss_trades','tp_hits','sl_hits','timeouts')}

def main():
    rows=load(); idx=indices(rows); split=int(len(idx)*.60); di=idx[:split]; vi=idx[split:]
    arr=[]
    for tp in GRID:
      for sl in GRID:
        f=sim(rows,idx,tp,sl); d=sim(rows,di,tp,sl); v=sim(rows,vi,tp,sl)
        arr.append({'f':f,'d':d,'v':v})
    profitable=[x for x in arr if x['f']['net_pnl_usd']>0]
    best_wr_profit=sorted(profitable,key=lambda x:(x['f']['net_wr'],x['f']['net_pnl_usd']),reverse=True)[:15]
    thresholds={}
    for wr in (55,60,62,65,67,70):
        q=[x for x in arr if x['f']['net_wr']>=wr and x['f']['net_pnl_usd']>0]
        thresholds[str(wr)]={'count':len(q),'best':slim(max(q,key=lambda x:x['f']['net_pnl_usd'])['f']) if q else None}
    # Cross-period positive and WR-focused.
    cross=[x for x in arr if x['d']['net_pnl_usd']>0 and x['v']['net_pnl_usd']>0]
    cross_wr=sorted(cross,key=lambda x:(x['f']['net_wr'],x['f']['net_pnl_usd']),reverse=True)[:15]
    out={'status':'A43B_STATIC_FRONTIER','data':{'tuesdays':len(idx),'discovery':len(di),'validation':len(vi),'configs':len(arr)},
         'highest_wr_among_full_profitable':[{'full':slim(x['f']),'discovery':slim(x['d']),'validation':slim(x['v'])} for x in best_wr_profit],
         'profitable_wr_thresholds':thresholds,
         'highest_wr_cross_period_positive':[{'full':slim(x['f']),'discovery':slim(x['d']),'validation':slim(x['v'])} for x in cross_wr]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
