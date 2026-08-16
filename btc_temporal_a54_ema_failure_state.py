"""BTC Temporal A5.4 — EMA failure-state forensics after +0.50% short MFE.

Question: does EMA state explain which Tuesday 06:00 SELL runners later give back?
Parent is frozen: SELL 06:00 WIB, TP1.35%, SL0.80%, max hold6h.
EMA is NOT used for initial direction/entry. It is observed only after the A5 hinge:
first completed 5m candle that touches +0.50% short MFE.

Causal EMA features at the completed trigger candle:
- close relative to EMA7 / EMA20
- EMA7 / EMA20 slopes (1-bar and 3-bar)
- EMA7-EMA20 spread and compression
- bullish reclaim of EMA7 / EMA20
- two-close acceptance above EMA7 / EMA20

Selection split remains first 83 Tuesdays discovery / last 56 validation.
Only a compact set of interpretable EMA gates is tested.
"""
import json, statistics
import btc_temporal_a52_runner_protect as a52
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END


def ema_series(rows, period):
    a=2.0/(period+1.0); out=[]; v=None
    for x in rows:
        c=x[4]
        v=c if v is None else a*c+(1-a)*v
        out.append(v)
    return out


def med(xs):
    return rnd(statistics.median(xs),4) if xs else None


def pct(a,b):
    return 100.0*(a-b)/b if b else 0.0


def add_ema(rows,recs,e7,e20):
    out=[]
    for r in recs:
        q=dict(r); s=r['state']
        if not s:
            q['ema']=None; out.append(q); continue
        j=s['trigger_i']; c=rows[j][4]
        p1=max(0,j-1); p2=max(0,j-2); p3=max(0,j-3)
        prevc=rows[p1][4]
        # Positive distance means close is ABOVE EMA: adverse/failure-like for a short.
        d7=pct(c,e7[j]); d20=pct(c,e20[j])
        sl7_1=pct(e7[j],e7[p1]); sl7_3=pct(e7[j],e7[p3])
        sl20_1=pct(e20[j],e20[p1]); sl20_3=pct(e20[j],e20[p3])
        spread=pct(e7[j],e20[j])
        prev_spread=pct(e7[p1],e20[p1])
        e={
          'd7':d7,'d20':d20,'s7_1':sl7_1,'s7_3':sl7_3,'s20_1':sl20_1,'s20_3':sl20_3,
          'spread':spread,'spread_change':spread-prev_spread,
          'above7':c>e7[j],'above20':c>e20[j],
          'reclaim7':c>e7[j] and prevc<=e7[p1],
          'reclaim20':c>e20[j] and prevc<=e20[p1],
          'two_above7':j>=1 and c>e7[j] and prevc>e7[p1],
          'two_above20':j>=1 and c>e20[j] and prevc>e20[p1],
          'ema7_up':sl7_1>0,'ema20_up':sl20_1>0,
          'fast_above_slow':e7[j]>e20[j],
          'bull_cross':e7[j]>e20[j] and e7[p1]<=e20[p1],
          # compression toward zero from a bearish fast-below-slow state
          'bear_spread_compress':spread<0 and spread>prev_spread,
        }
        q['ema']=e; out.append(q)
    return out


def grp(q):
    q=[r for r in q if r.get('ema')]
    fields=('d7','d20','s7_1','s7_3','s20_1','s20_3','spread','spread_change')
    flags=('above7','above20','reclaim7','reclaim20','two_above7','two_above20','ema7_up','ema20_up','fast_above_slow','bull_cross','bear_spread_compress')
    z={'n':len(q)}
    for f in fields:z[f+'_med']=med([r['ema'][f] for r in q])
    for f in flags:z[f+'_pct']=rnd(100*sum(bool(r['ema'][f]) for r in q)/len(q),2) if q else None
    return z


def atlas(recs):
    h=[r for r in recs if r['state'] and r['protect'] is not None and r.get('ema')]
    # Oracle action label at hinge: PROTECT better vs leaving parent RUNNER.
    pb=[r for r in h if r['protect']>r['base']]
    rb=[r for r in h if r['base']>=r['protect']]
    neg=[r for r in h if r['base']<=0]; pos=[r for r in h if r['base']>0]
    return {'hinge':len(h),'protect_better':grp(pb),'runner_better':grp(rb),'base_negative':grp(neg),'base_positive':grp(pos)}


def condition(name,r):
    s=r['state']; e=r.get('ema')
    if not s or not e:return False
    weak35=s['progress_close']<=0.35
    weak40=s['progress_close']<=0.40
    mae20=s['mae']>=0.20
    mae15=s['mae']>=0.15
    frozen=weak35 and mae20
    # EMA-only diagnostics
    if name=='ABOVE7': return e['above7']
    if name=='RECLAIM7': return e['reclaim7']
    if name=='TWO_ABOVE7': return e['two_above7']
    if name=='EMA7_UP': return e['ema7_up']
    if name=='ABOVE7_UP': return e['above7'] and e['ema7_up']
    if name=='ABOVE20': return e['above20']
    if name=='RECLAIM20': return e['reclaim20']
    if name=='TWO_ABOVE20': return e['two_above20']
    if name=='FAST_ABOVE_SLOW': return e['fast_above_slow']
    if name=='BEAR_COMPRESS': return e['bear_spread_compress']
    # Does EMA improve precision of the frozen A5.2 failure state?
    if name=='FROZEN': return frozen
    if name=='FROZEN_ABOVE7': return frozen and e['above7']
    if name=='FROZEN_RECLAIM7': return frozen and e['reclaim7']
    if name=='FROZEN_7UP': return frozen and e['ema7_up']
    if name=='FROZEN_ABOVE7_7UP': return frozen and e['above7'] and e['ema7_up']
    if name=='FROZEN_ABOVE20': return frozen and e['above20']
    if name=='FROZEN_RECLAIM20': return frozen and e['reclaim20']
    if name=='FROZEN_COMPRESS': return frozen and e['bear_spread_compress']
    # Can EMA safely broaden the frozen state and catch more givebacks?
    if name=='BROAD_ABOVE7': return weak40 and mae15 and e['above7']
    if name=='BROAD_RECLAIM7': return weak40 and mae15 and e['reclaim7']
    if name=='BROAD_ABOVE7_7UP': return weak40 and mae15 and e['above7'] and e['ema7_up']
    if name=='BROAD_ABOVE20': return weak40 and mae15 and e['above20']
    if name=='BROAD_COMPRESS': return weak40 and mae15 and e['bear_spread_compress']
    if name=='BROAD_2ABOVE7': return weak40 and mae15 and e['two_above7']
    return False

NAMES=(
 'ABOVE7','RECLAIM7','TWO_ABOVE7','EMA7_UP','ABOVE7_UP','ABOVE20','RECLAIM20','TWO_ABOVE20','FAST_ABOVE_SLOW','BEAR_COMPRESS',
 'FROZEN','FROZEN_ABOVE7','FROZEN_RECLAIM7','FROZEN_7UP','FROZEN_ABOVE7_7UP','FROZEN_ABOVE20','FROZEN_RECLAIM20','FROZEN_COMPRESS',
 'BROAD_ABOVE7','BROAD_RECLAIM7','BROAD_ABOVE7_7UP','BROAD_ABOVE20','BROAD_COMPRESS','BROAD_2ABOVE7'
)


def evaluate(recs,name):
    out=[]; actions=rescued=damaged=0
    for r in recs:
        f=r['base']
        if r['protect'] is not None and condition(name,r):
            f=r['protect']; actions+=1
            if r['base']<=0 and f>0:rescued+=1
            if r['base']>0 and f<=0:damaged+=1
        out.append({'ts':r['ts'],'base':r['base'],'final':f})
    z=a52.summarize(out); b=a52.summarize(out,'base')
    z.update({'rule':name,'actions':actions,'rescued':rescued,'damaged':damaged,'delta':rnd(z['pnl']-b['pnl'],3)})
    return z


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx)
    e7=ema_series(rows,7); e20=ema_series(rows,20)
    recs=add_ema(rows,recs,e7,e20)
    split=int(len(recs)*.60); disc=recs[:split]; val=recs[split:]
    base={'discovery':a52.summarize([{'ts':r['ts'],'final':r['base']} for r in disc]),
          'validation':a52.summarize([{'ts':r['ts'],'final':r['base']} for r in val]),
          'full':a52.summarize([{'ts':r['ts'],'final':r['base']} for r in recs])}
    tests=[]
    for n in NAMES:
        d=evaluate(disc,n); v=evaluate(val,n); f=evaluate(recs,n)
        tests.append({'name':n,'discovery':d,'validation':v,'full':f})
    # Cross-period candidates must improve PnL in both halves and not reduce full WR.
    cross=[x for x in tests if x['discovery']['delta']>0 and x['validation']['delta']>0 and x['full']['wr']>=base['full']['wr']]
    cross.sort(key=lambda x:(x['full']['pnl'],x['full']['wr'],-x['full']['damaged']),reverse=True)
    byfull=sorted(tests,key=lambda x:(x['full']['pnl'],x['full']['wr'],-x['full']['damaged']),reverse=True)
    out={'status':'A54_EMA_FAILURE_STATE','parent':{'tp':1.35,'sl':0.8,'hold':360,'hinge':0.5,'lock':0.2},
         'data':{'tuesdays':len(recs),'discovery':len(disc),'validation':len(val),'ema_periods':[7,20],'tests':len(tests)},
         'baseline':base,'atlas':{'discovery':atlas(disc),'validation':atlas(val),'full':atlas(recs)},
         'cross_period':cross,'best_full':byfull}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
