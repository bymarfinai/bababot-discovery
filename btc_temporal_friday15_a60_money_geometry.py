"""BTC Temporal Friday15 A6.0 — money geometry discovery.

Independent engine from frozen Tuesday champion.
Entry: every Friday exact 15:00 WIB 5m open.
Direction: BUY only.
Sizing/fees/ambiguity policy match Tuesday money research.
Research only; does not mutate live BBC or Tuesday frozen champion.
"""
import json
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

FEE_PCT=0.15
MARGIN_USD=10.0
LEVERAGE=50.0
NOTIONAL=MARGIN_USD*LEVERAGE
TPS=(0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00,1.10,1.20,1.30,1.40,1.50,1.60,1.80,2.00)
SLS=(0.30,0.40,0.50,0.60,0.70,0.80,0.90,1.00,1.10,1.20,1.30,1.40)
HOLDS=(120,240,360,480,600,720)


def trade(rows,i,tp,sl,hold):
    e=rows[i][1]
    tp_px=e*(1+tp/100.0)
    sl_px=e*(1-sl/100.0)
    end=min(len(rows),i+hold//5)
    exit_px=None; reason='TIMEOUT'; bars=0
    for j in range(i,end):
        x=rows[j]
        if x[0]!=rows[i][0]+(j-i)*TF:return None
        hit_tp=x[2]>=tp_px
        hit_sl=x[3]<=sl_px
        bars=j-i+1
        if hit_tp and hit_sl:
            exit_px=sl_px; reason='AMB_SL'; break
        if hit_sl:
            exit_px=sl_px; reason='SL'; break
        if hit_tp:
            exit_px=tp_px; reason='TP'; break
    if exit_px is None:
        if end<=i:return None
        exit_px=rows[end-1][4]; bars=end-i
    gross_pct=100.0*(exit_px-e)/e
    net_pct=gross_pct-FEE_PCT
    return {'ts':rows[i][0],'entry':e,'exit':exit_px,'reason':reason,'bars':bars,
            'gross_pct':gross_pct,'net_pct':net_pct,
            'gross_usd':NOTIONAL*gross_pct/100.0,'fee_usd':NOTIONAL*FEE_PCT/100.0,
            'net_usd':NOTIONAL*net_pct/100.0}


def max_dd(pnls):
    eq=peak=mdd=0.0
    for p in pnls:
        eq+=p; peak=max(peak,eq); mdd=max(mdd,peak-eq)
    return mdd


def loss_streak(pnls):
    best=cur=0
    for p in pnls:
        if p<=0:cur+=1;best=max(best,cur)
        else:cur=0
    return best


def summarize(ts,tp,sl,hold):
    pnls=[x['net_usd'] for x in ts]; n=len(ts)
    pos=sum(x for x in pnls if x>0); neg=-sum(x for x in pnls if x<0)
    wins=sum(x>0 for x in pnls)
    blocks=[]
    for b in range(8):
        q=[x['net_usd'] for x in ts if min(7,max(0,int((x['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        blocks.append(rnd(sum(q),3))
    return {'tp_pct':tp,'sl_pct':sl,'hold_min':hold,'rr':rnd(tp/sl,3),'trades':n,
            'tp_hits':sum(x['reason']=='TP' for x in ts),'sl_hits':sum(x['reason'] in ('SL','AMB_SL') for x in ts),
            'ambiguous_sl':sum(x['reason']=='AMB_SL' for x in ts),'timeouts':sum(x['reason']=='TIMEOUT' for x in ts),
            'net_win_trades':wins,'net_loss_trades':n-wins,'net_wr':rnd(100*wins/n,2),
            'gross_pnl_usd':rnd(sum(x['gross_usd'] for x in ts),3),'fees_usd':rnd(sum(x['fee_usd'] for x in ts),3),
            'net_pnl_usd':rnd(sum(pnls),3),'expectancy_usd':rnd(sum(pnls)/n,4),
            'profit_factor':rnd(pos/neg,3) if neg>0 else None,'max_dd_usd':rnd(max_dd(pnls),3),
            'max_loss_streak':loss_streak(pnls),'positive_blocks':sum(x>0 for x in blocks),'block_net_usd':blocks,
            'avg_hold_min':rnd(sum(x['bars']*5 for x in ts)/n,2)}


def subset_summary(ts):
    pnls=[x['net_usd'] for x in ts]; n=len(ts); pos=sum(x for x in pnls if x>0); neg=-sum(x for x in pnls if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in pnls)/n,2),'pnl':rnd(sum(pnls),3),
            'exp':rnd(sum(pnls)/n,4),'pf':rnd(pos/neg,3) if neg>0 else None,'mdd':rnd(max_dd(pnls),3),'ls':loss_streak(pnls)}


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}
    expected=(EVAL_END-EVAL_START)//TF; exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows)
    idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.hour==15 and d.minute==0:idx.append(im[x[0]])
    split=int(len(idx)*.60)
    results=[]
    for hold in HOLDS:
      for tp in TPS:
       for sl in SLS:
        ts=[trade(rows,i,tp,sl,hold) for i in idx]
        if all(t is not None for t in ts):
            s=summarize(ts,tp,sl,hold)
            s['discovery']=subset_summary(ts[:split]); s['validation']=subset_summary(ts[split:])
            s['delta_sign_consistent']=s['discovery']['pnl']>0 and s['validation']['pnl']>0
            results.append(s)
    bynet=sorted(results,key=lambda x:(x['net_pnl_usd'],x['positive_blocks'],-x['max_dd_usd']),reverse=True)
    cross=sorted([x for x in results if x['delta_sign_consistent']],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    stable=sorted([x for x in results if x['positive_blocks']>=6 and x['net_pnl_usd']>0],key=lambda x:(x['net_pnl_usd'],x['profit_factor'] or 0,-x['max_dd_usd']),reverse=True)
    balanced=sorted([x for x in results if x['positive_blocks']>=6 and x['delta_sign_consistent']],
                    key=lambda x:(x['expectancy_usd']/(1+x['max_dd_usd']/25),x['profit_factor'] or 0,-x['max_loss_streak']),reverse=True)
    highwr=sorted([x for x in results if x['net_pnl_usd']>0],key=lambda x:(x['net_wr'],x['net_pnl_usd']),reverse=True)
    out={'status':'FRIDAY15_A60_MONEY_GEOMETRY','data':{'coverage_pct':rnd(100*exact/expected,2),'rows_5m':exact,'fridays':len(idx),'discovery_n':split,'validation_n':len(idx)-split,'entry':'Friday 15:00 WIB exact open','direction':'BUY','fee_roundtrip_pct':FEE_PCT,'notional_usd':NOTIONAL,'configs':len(results)},
         'best_net':bynet[:20],'best_cross_period':cross[:20],'best_stable':stable[:20],'best_balanced':balanced[:20],'highest_wr_profitable':highwr[:20]}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),'FRIDAYS',len(idx),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
