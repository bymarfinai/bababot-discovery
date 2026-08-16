"""BTC Temporal A3.7 — money-first optimizer for Tuesday 06:00 WIB SELL.

Fixed high-coverage temporal setup: SELL every Tuesday at exact 06:00 WIB.
Purpose: find economically superior TP/SL/max-hold geometry after fees, rather
than optimize headline WR. Uses official Binance Futures 5m archives via A3.4 loader.

Rules
-----
- Entry: exact 06:00 WIB 5m open, every Tuesday in the frozen 971-day window.
- Direction: SELL only (the strongest high-coverage temporal prior from A1/A3).
- TP grid: 0.4,0.5,0.6,0.7,0.8,1.0,1.2 percent.
- SL grid: 0.4,0.5,0.6,0.7,0.8,1.0 percent.
- Max hold: 120,240,360 minutes.
- If neither TP nor SL is touched: exit at the final 5m close of max-hold.
- If both TP and SL are touched in the same 5m candle: count SL first
  (conservative intrabar ambiguity policy).
- Fee: 0.15% round-trip of notional on every trade.
- Fixed sizing: $10 margin x 50 leverage = $500 notional, no compounding.
- Research only; no live mutation.
"""
import json, math
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TPS=(0.4,0.5,0.6,0.7,0.8,1.0,1.2)
SLS=(0.4,0.5,0.6,0.7,0.8,1.0)
HOLDS=(120,240,360)
FEE_PCT=0.15
MARGIN_USD=10.0
LEVERAGE=50.0
NOTIONAL=MARGIN_USD*LEVERAGE


def trade(rows,i,tp,sl,hold):
    e=rows[i][1]
    tp_px=e*(1-tp/100.0)
    sl_px=e*(1+sl/100.0)
    nb=hold//5
    end=min(len(rows),i+nb)
    exit_px=None; reason='TIMEOUT'; bars=0
    for j in range(i,end):
        x=rows[j]
        # Require contiguous bars from entry.
        if x[0] != rows[i][0] + (j-i)*TF:
            return None
        hit_tp=x[3] <= tp_px
        hit_sl=x[2] >= sl_px
        bars=j-i+1
        if hit_tp and hit_sl:
            # Conservative: adverse side first when 5m ordering is unknowable.
            exit_px=sl_px; reason='AMB_SL'; break
        if hit_sl:
            exit_px=sl_px; reason='SL'; break
        if hit_tp:
            exit_px=tp_px; reason='TP'; break
    if exit_px is None:
        if end<=i:return None
        exit_px=rows[end-1][4]
        bars=end-i
    gross_pct=100.0*(e-exit_px)/e  # short return on notional
    net_pct=gross_pct-FEE_PCT
    gross_usd=NOTIONAL*gross_pct/100.0
    fee_usd=NOTIONAL*FEE_PCT/100.0
    net_usd=NOTIONAL*net_pct/100.0
    return {'ts':rows[i][0],'entry':e,'exit':exit_px,'reason':reason,'bars':bars,
            'gross_pct':gross_pct,'net_pct':net_pct,'gross_usd':gross_usd,
            'fee_usd':fee_usd,'net_usd':net_usd}


def max_drawdown(pnls):
    eq=0.0; peak=0.0; mdd=0.0
    for p in pnls:
        eq+=p
        peak=max(peak,eq)
        mdd=max(mdd,peak-eq)
    return mdd


def loss_streak(pnls):
    best=cur=0
    for p in pnls:
        if p<=0:cur+=1;best=max(best,cur)
        else:cur=0
    return best


def summarize(ts,tp,sl,hold):
    pnls=[x['net_usd'] for x in ts]
    gross=[x['gross_usd'] for x in ts]
    n=len(ts); wins=sum(x>0 for x in pnls); losses=n-wins
    tpc=sum(x['reason']=='TP' for x in ts)
    slc=sum(x['reason'] in ('SL','AMB_SL') for x in ts)
    amb=sum(x['reason']=='AMB_SL' for x in ts)
    timeout=sum(x['reason']=='TIMEOUT' for x in ts)
    pos=sum(x for x in pnls if x>0); neg=-sum(x for x in pnls if x<0)
    blocks=[]
    for b in range(8):
        q=[x['net_usd'] for x in ts if min(7,max(0,int((x['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        blocks.append(rnd(sum(q),3))
    return {
      'tp_pct':tp,'sl_pct':sl,'hold_min':hold,'rr':rnd(tp/sl,3),'trades':n,
      'tp_hits':tpc,'sl_hits':slc,'ambiguous_sl':amb,'timeouts':timeout,
      'net_win_trades':wins,'net_loss_trades':losses,'net_wr':rnd(100*wins/n,2),
      'gross_pnl_usd':rnd(sum(gross),3),'fees_usd':rnd(sum(x['fee_usd'] for x in ts),3),
      'net_pnl_usd':rnd(sum(pnls),3),'expectancy_usd':rnd(sum(pnls)/n,4),
      'return_on_10_margin_sum_pct':rnd(100*sum(pnls)/MARGIN_USD,2),
      'profit_factor':rnd(pos/neg,3) if neg>0 else None,
      'max_dd_usd':rnd(max_drawdown(pnls),3),'max_loss_streak':loss_streak(pnls),
      'positive_blocks':sum(x>0 for x in blocks),'block_net_usd':blocks,
      'avg_hold_min':rnd(sum(x['bars']*5 for x in ts)/n,2)
    }


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    expected=(EVAL_END-EVAL_START)//TF
    exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows)
    idx=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        dt=ldt(x[0])
        if dt.weekday()==1 and dt.hour==6 and dt.minute==0:
            idx.append(im[x[0]])
    results=[]
    for hold in HOLDS:
        for tp in TPS:
            for sl in SLS:
                trades=[]
                for i in idx:
                    t=trade(rows,i,tp,sl,hold)
                    if t is not None:trades.append(t)
                if len(trades)==len(idx):
                    results.append(summarize(trades,tp,sl,hold))
    by_net=sorted(results,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)
    stable=sorted([x for x in results if x['positive_blocks']>=6 and x['net_pnl_usd']>0],
                  key=lambda x:(x['net_pnl_usd'],x['expectancy_usd'],-x['max_dd_usd']),reverse=True)
    rr1=sorted([x for x in results if abs(x['rr']-1.0)<1e-9],key=lambda x:x['net_pnl_usd'],reverse=True)
    out={'status':'A37_TUESDAY_MONEY_OPTIMIZER','data':{
        'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'expected_5m':expected,
        'tuesdays':len(idx),'entry':'Tuesday 06:00 WIB exact open','direction':'SELL',
        'margin_usd':MARGIN_USD,'leverage':LEVERAGE,'notional_usd':NOTIONAL,
        'fee_roundtrip_pct':FEE_PCT,'intrabar_ambiguity':'SL first','timeout':'actual final 5m close',
        'grid_configs':len(results)},
        'best_net':by_net[:20],'best_stable':stable[:20],'best_rr1':rr1[:15]}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),'TUESDAYS',len(idx),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
