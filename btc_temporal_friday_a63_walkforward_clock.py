"""BTC Friday A6.3 — causal walk-forward clock/regime rotation.

Each Friday BEFORE the selected trade, rank all 24 WIB clock-hours x fixed horizons
using only prior Fridays. Then take exactly one market trade that Friday.

Two families:
- BUY_ONLY: direction remains BUY; rotate only clock/horizon.
- DYNAMIC_DIR: direction is the sign of the prior-window mean return for that
  clock/horizon, so Friday can adapt BUY/SELL without future information.

No TP/SL optimization here: exit at the selected fixed horizon close. This isolates
whether a causal Friday clock/regime selector exists after 0.15% round-trip fee.
"""
import json, math, statistics
from collections import defaultdict, Counter
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

FEE=0.15
HORIZONS=(30,60,120,240,360)
LOOKBACKS=(13,26,52)
MODES=('MEAN','LCB')
FAMILIES=('BUY_ONLY','DYNAMIC_DIR')


def raw_return(rows,i,h):
    j=i+h//5
    if j>=len(rows) or rows[j][0]!=rows[i][0]+(h//5)*TF:return None
    return 100.0*(rows[j][4]-rows[i][1])/rows[i][1]


def score(xs,mode):
    if not xs:return -1e9
    m=sum(xs)/len(xs)
    if mode=='MEAN' or len(xs)<2:return m
    sd=statistics.stdev(xs)
    return m-0.5*sd/math.sqrt(len(xs))


def maxdd(xs):
    e=p=m=0.0
    for x in xs:
        e+=x;p=max(p,e);m=max(m,p-e)
    return m


def streak(xs):
    c=b=0
    for x in xs:
        if x<=0:c+=1;b=max(b,c)
        else:c=0
    return b


def summarize(trades):
    if not trades:return {'n':0}
    usd=[5.0*t['net_pct'] for t in trades] # $500 notional => $5 per 1%
    pos=sum(x for x in usd if x>0);neg=-sum(x for x in usd if x<0)
    # Chronological 8 equal-count blocks for this adaptive stream.
    bs=[]
    for b in range(8):
        a=len(usd)*b//8;z=len(usd)*(b+1)//8;bs.append(sum(usd[a:z]))
    return {'n':len(usd),'wins':sum(x>0 for x in usd),'wr':rnd(100*sum(x>0 for x in usd)/len(usd),2),
            'pnl':rnd(sum(usd),3),'exp':rnd(sum(usd)/len(usd),4),'pf':rnd(pos/neg,3) if neg else None,
            'mdd':rnd(maxdd(usd),3),'ls':streak(usd),'blocks_pos':sum(x>0 for x in bs),
            'avg_net_pct':rnd(sum(t['net_pct'] for t in trades)/len(trades),4),
            'hours':dict(Counter(t['hour'] for t in trades).most_common()),
            'horizons':dict(Counter(t['horizon'] for t in trades).most_common()),
            'directions':dict(Counter(t['dir'] for t in trades).most_common())}


def build_fridays(rows):
    # Map local-Friday date -> exact-hour open index. Only keep complete 24-hour Fridays.
    dmap=defaultdict(dict)
    for i,x in enumerate(rows):
        if EVAL_START<=x[0]<EVAL_END:
            d=ldt(x[0])
            if d.weekday()==4 and d.minute==0:
                dmap[d.date()][d.hour]=i
    return [(d,dmap[d]) for d in sorted(dmap) if len(dmap[d])==24]


def run(rows,fridays,lb,mode,family,gate=False):
    out=[]
    # precompute raw return matrix by Friday index/hour/horizon
    ret={}
    for fi,(date,hm) in enumerate(fridays):
        for h,i in hm.items():
            for hz in HORIZONS:
                r=raw_return(rows,i,hz)
                if r is not None:ret[(fi,h,hz)]=r
    for fi in range(lb,len(fridays)):
        best=None
        for h in range(24):
            for hz in HORIZONS:
                hist=[ret[(k,h,hz)] for k in range(fi-lb,fi) if (k,h,hz) in ret]
                if len(hist)<lb:continue
                if family=='BUY_ONLY':
                    # expected executable net return for BUY
                    vals=[x-FEE for x in hist]
                    sc=score(vals,mode); direction='BUY'
                else:
                    # choose direction using prior-window raw mean only, then score that direction after fee
                    mu=sum(hist)/len(hist); direction='BUY' if mu>=0 else 'SELL'
                    vals=[(x if direction=='BUY' else -x)-FEE for x in hist]
                    sc=score(vals,mode)
                cand=(sc,h,hz,direction,sum(vals)/len(vals))
                if best is None or cand[0]>best[0]:best=cand
        if best is None:continue
        sc,h,hz,direction,hist_mean=best
        if gate and sc<=0:continue
        r=ret.get((fi,h,hz))
        if r is None:continue
        signed=r if direction=='BUY' else -r
        out.append({'date':str(fridays[fi][0]),'hour':h,'horizon':hz,'dir':direction,
                    'score':sc,'hist_mean_net':hist_mean,'raw_pct':r,'net_pct':signed-FEE})
    return out


def static(rows,fridays,h,hz,direction='BUY',start=52):
    ts=[]
    for fi in range(start,len(fridays)):
        i=fridays[fi][1][h];r=raw_return(rows,i,hz)
        if r is None:continue
        s=r if direction=='BUY' else -r
        ts.append({'date':str(fridays[fi][0]),'hour':h,'horizon':hz,'dir':direction,'net_pct':s-FEE})
    return summarize(ts)


def main():
    rows=load(); fridays=build_fridays(rows)
    tests=[]
    for fam in FAMILIES:
      for lb in LOOKBACKS:
       for mode in MODES:
        for gate in (False,True):
            tr=run(rows,fridays,lb,mode,fam,gate)
            s=summarize(tr);s.update({'family':fam,'lookback':lb,'mode':mode,'gate_positive_score':gate,
                                     'coverage_pct':rnd(100*len(tr)/(len(fridays)-lb),2) if len(fridays)>lb else 0,
                                     'recent10':tr[-10:]})
            tests.append(s)
    forced=sorted([x for x in tests if not x['gate_positive_score']],key=lambda x:(x.get('pnl',-1e9),x.get('pf') or 0,x.get('wr',0)),reverse=True)
    gated=sorted([x for x in tests if x['gate_positive_score']],key=lambda x:(x.get('pnl',-1e9),x.get('pf') or 0,x.get('coverage_pct',0)),reverse=True)
    # Apples-to-apples static references begin after 52-week warmup.
    refs={
      'fri15_buy_30m':static(rows,fridays,15,30,'BUY',52),
      'fri15_buy_240m':static(rows,fridays,15,240,'BUY',52),
      'fri04_buy_30m':static(rows,fridays,4,30,'BUY',52),
      'fri23_buy_60m':static(rows,fridays,23,60,'BUY',52),
    }
    out={'status':'FRIDAY_A63_WALKFORWARD_CLOCK','fridays':len(fridays),'fee_pct':FEE,
         'method':'one trade per Friday; rank 24 hours x 5 horizons using prior N Fridays only; fixed-horizon close exit',
         'forced_one_trade_ranked':forced,'positive_score_gate_ranked':gated,'static_refs_after_52w_warmup':refs}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
