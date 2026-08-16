"""BTC Temporal A5.8 — fast mean-reversion rescue on top of A5.2.

For A5.2-untouched hinge trades only, test the stable A5.7 forensic pattern:
1) trade first reached +0.50% short MFE while materially below EMA20;
2) profit then gives back quickly (pullback threshold or EMA7 reclaim) relative
   to the hinge time;
3) intervene either by market exit next 5m open or by arming +0.20% profit lock
   while retaining original TP1.35.

Parent direction/entry/TP/SL/6h unchanged. First 83 discovery / last 56 validation.
"""
import json
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a54_ema_failure_state as a54
import btc_temporal_a57_giveback_sequence as a57
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import FEE_PCT, NOTIONAL

TP=1.35; SL=0.80; HOLD=360; LOCK=0.20


def event_for(seq,kind):
    if kind=='PULL35': return seq.get('first_pull35')
    if kind=='PULL30': return seq.get('first_pull30')
    if kind=='RECLAIM7': return seq.get('first_reclaim7')
    if kind=='2ABOVE7': return seq.get('first_2above7')
    return None


def candidate(seq,kind,d20,latency):
    if not seq or seq['hinge_d20']>-d20:return None
    ev=event_for(seq,kind)
    if not ev:return None
    lag=ev['time']-seq['hinge_time']
    return ev if lag<=latency else None


def market_exit(rows,i,ev):
    dec=ev['k']+1; end=min(len(rows),i+HOLD//5)
    if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[ev['k']][0]+TF:return None
    e=rows[i][1]; ex=rows[dec][1]; gross=100*(e-ex)/e
    return NOTIONAL*(gross-FEE_PCT)/100


def lock20_result(rows,i,ev):
    """From next open: if +0.20 already lost, exit actual open; else arm +0.20 stop and keep TP1.35."""
    dec=ev['k']+1; end=min(len(rows),i+HOLD//5)
    if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[ev['k']][0]+TF:return None
    e=rows[i][1]; pstop=e*(1-LOCK/100); tp=e*(1-TP/100)
    op=rows[dec][1]
    if op>=pstop:
        ex=op
    else:
        ex=None
        for k in range(dec,end):
            x=rows[k]
            if x[0]!=rows[dec][0]+(k-dec)*TF:return None
            hs=x[2]>=pstop; ht=x[3]<=tp
            if hs and ht: ex=pstop; break  # adverse-first
            if hs: ex=pstop; break
            if ht: ex=tp; break
        if ex is None: ex=rows[end-1][4]
    gross=100*(e-ex)/e
    return NOTIONAL*(gross-FEE_PCT)/100


def configs():
    out=[]
    # Compact thresholds centered on robust A5.7 median separation, not a large optimizer.
    for kind in ('PULL35','PULL30','RECLAIM7','2ABOVE7'):
        for d20 in (0.30,0.35,0.40):
            for lat in (20,30,45,60):
                for mode in ('MARKET','LOCK20'):
                    out.append((kind,d20,lat,mode))
    return out


def evaluate(qs,rows,cfg):
    kind,d20,lat,mode=cfg
    zs=[]; actions=rescued=damaged=0
    for r in qs:
        f=r['a52']
        if not r['frozen'] and r['seq']:
            ev=candidate(r['seq'],kind,d20,lat)
            ex=(market_exit(rows,r['i'],ev) if mode=='MARKET' else lock20_result(rows,r['i'],ev)) if ev else None
            if ex is not None:
                f=ex; actions+=1
                if r['a52']<=0 and f>0:rescued+=1
                if r['a52']>0 and f<=0:damaged+=1
        zs.append({'ts':r['ts'],'base':r['a52'],'final':f})
    s=a52.summarize(zs); b=a52.summarize(zs,'base')
    s.update({'kind':kind,'d20':d20,'latency':lat,'mode':mode,'actions':actions,'rescued':rescued,'damaged':damaged,'delta_vs_a52':rnd(s['pnl']-b['pnl'],3)})
    return s


def main():
    rows=load(); a57.G_ROWS=rows; im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); e7=a54.ema_series(rows,7); e20=a54.ema_series(rows,20)
    qs=a57.build_enriched(rows,recs,e7,e20); split=int(len(qs)*.60); disc=qs[:split]; val=qs[split:]
    def bench(p):return a52.summarize([{'ts':r['ts'],'final':r['a52']} for r in p])
    b={'discovery':bench(disc),'validation':bench(val),'full':bench(qs)}
    tests=[]
    for cfg in configs():
        d=evaluate(disc,rows,cfg); v=evaluate(val,rows,cfg); f=evaluate(qs,rows,cfg)
        tests.append({'name':f'{cfg[0]}_D20{cfg[1]:.2f}_L{cfg[2]}_{cfg[3]}','discovery':d,'validation':v,'full':f})
    cross=[x for x in tests if x['discovery']['delta_vs_a52']>0 and x['validation']['delta_vs_a52']>0 and x['full']['pnl']>=b['full']['pnl'] and x['full']['wr']>=b['full']['wr']]
    cross.sort(key=lambda x:(x['full']['wr'],x['full']['pnl'],-x['full']['damaged']),reverse=True)
    money=[x for x in tests if x['discovery']['delta_vs_a52']>0 and x['validation']['delta_vs_a52']>0]
    money.sort(key=lambda x:(x['full']['pnl'],x['full']['wr']),reverse=True)
    # frontier: higher WR while retaining >=95% of A5.2 PnL, diagnostic only
    frontier=[x for x in tests if x['full']['wr']>b['full']['wr'] and x['full']['pnl']>=.95*b['full']['pnl']]
    frontier.sort(key=lambda x:(x['full']['wr'],x['full']['pnl']),reverse=True)
    out={'status':'A58_FAST_MEAN_REVERSION','data':{'tuesdays':len(qs),'configs':len(tests),'discovery':len(disc),'validation':len(val)},
         'a52_benchmark':b,'strict_cross_period_upgrades':cross[:20],'cross_period_money':money[:20],'wr95_frontier':frontier[:20]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
