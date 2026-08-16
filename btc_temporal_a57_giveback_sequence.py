"""BTC Temporal A5.7 — giveback sequence forensics after +0.50% MFE.

Goal: improve the balanced A5.2 champion, not re-optimize TP/SL.
Parent remains Tuesday 06:00 SELL, TP1.35/SL0.80/6h.
A5.2 frozen protection remains first priority. For hinge trades NOT acted on by
A5.2, study causal post-hinge sequences involving pullback depth and EMA7/20
interaction, then test deterministic market-exit rules at the NEXT 5m open.

No initial entries are filtered. No EMA is used to choose direction.
Discovery = first 83 Tuesdays, validation = last 56 Tuesdays.
"""
import json, statistics
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a54_ema_failure_state as a54
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import FEE_PCT, NOTIONAL

TP=1.35; SL=0.80; HOLD=360
FROZEN_NAME='HIGH_MAE_WEAK'; FROZEN_P={'weak_close':0.35,'mae':0.20}


def frozen_action(r):
    return r['state'] is not None and r['protect'] is not None and a52.rule(FROZEN_NAME,r['state'],FROZEN_P)


def ema_dist(close,ema): return 100*(close-ema)/ema if ema else 0.0

def progress(e,p): return 100*(e-p)/e


def sequence(rows,i,s,e7,e20):
    """Collect only causal events after the +0.50% hinge, before parent exit."""
    if not s:return None
    e=rows[i][1]; tp=e*(1-TP/100); sl=e*(1+SL/100)
    start=s['decision_i']; end=min(len(rows),i+HOLD//5)
    trig=s['trigger_i']; tc=rows[trig][4]
    out={
      'hinge_time':s['time_min'],'hinge_progress':s['progress_close'],'hinge_mae':s['mae'],
      'hinge_d7':ema_dist(tc,e7[trig]),'hinge_d20':ema_dist(tc,e20[trig]),
      'first_above7':None,'first_reclaim7':None,'first_2above7':None,
      'first_above20':None,'first_2above20':None,'first_touch7_reject':None,
      'first_touch20_reject':None,'first_pull40':None,'first_pull35':None,
      'first_pull30':None,'first_pull25':None,'first_pull20':None,
      'second_attempt_accept7':None,
    }
    reject7_k=None
    for k in range(start,end):
        if rows[k][0]!=rows[i][0]+(k-i)*TF:break
        x=rows[k]; ht=x[3]<=tp; hs=x[2]>=sl
        if ht or hs:break
        c=x[4]; pc=rows[k-1][4] if k>0 else c
        pr=progress(e,c); tm=(k-i+1)*5
        d7=ema_dist(c,e7[k]); d20=ema_dist(c,e20[k])
        rec={'k':k,'time':tm,'progress':pr,'d7':d7,'d20':d20,'ema7_slope':100*(e7[k]-e7[k-1])/e7[k-1] if k>0 else 0.0,
             'ema20_slope':100*(e20[k]-e20[k-1])/e20[k-1] if k>0 else 0.0}
        if out['first_above7'] is None and c>e7[k]: out['first_above7']=rec
        if out['first_reclaim7'] is None and c>e7[k] and pc<=e7[k-1]: out['first_reclaim7']=rec
        if out['first_2above7'] is None and k>0 and c>e7[k] and pc>e7[k-1]: out['first_2above7']=rec
        if out['first_above20'] is None and c>e20[k]: out['first_above20']=rec
        if out['first_2above20'] is None and k>0 and c>e20[k] and pc>e20[k-1]: out['first_2above20']=rec
        # touch/reject = bar traded to/through EMA but completed back below it (bearish defense)
        if out['first_touch7_reject'] is None and x[2]>=e7[k] and c<e7[k]:
            out['first_touch7_reject']=rec; reject7_k=k
        if out['first_touch20_reject'] is None and x[2]>=e20[k] and c<e20[k]: out['first_touch20_reject']=rec
        # second attempt acceptance: after an earlier EMA7 rejection, later close above EMA7 within 6 bars
        if reject7_k is not None and out['second_attempt_accept7'] is None and k>reject7_k and k<=reject7_k+6 and c>e7[k]:
            out['second_attempt_accept7']=rec
        for th,key in ((0.40,'first_pull40'),(0.35,'first_pull35'),(0.30,'first_pull30'),(0.25,'first_pull25'),(0.20,'first_pull20')):
            if out[key] is None and pr<=th: out[key]=rec
    return out


def event_exit(rows,i,ev):
    """Exit at next 5m open after a completed event candle."""
    if ev is None:return None
    dec=ev['k']+1; end=min(len(rows),i+HOLD//5)
    if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[ev['k']][0]+TF:return None
    e=rows[i][1]; ex=rows[dec][1]; gross=progress(e,ex)
    return NOTIONAL*(gross-FEE_PCT)/100


def event_for_rule(seq,name):
    if not seq:return None
    # Simple sequence rules: event must happen while enough short profit remains.
    if name=='2ABOVE7_P35':
        e=seq['first_2above7']; return e if e and e['progress']>=0.35 else None
    if name=='2ABOVE7_P30':
        e=seq['first_2above7']; return e if e and e['progress']>=0.30 else None
    if name=='2ABOVE7_P25':
        e=seq['first_2above7']; return e if e and e['progress']>=0.25 else None
    if name=='RECLAIM7_P35':
        e=seq['first_reclaim7']; return e if e and e['progress']>=0.35 else None
    if name=='RECLAIM7_P30':
        e=seq['first_reclaim7']; return e if e and e['progress']>=0.30 else None
    if name=='ABOVE7_P35':
        e=seq['first_above7']; return e if e and e['progress']>=0.35 else None
    if name=='ABOVE7_P30':
        e=seq['first_above7']; return e if e and e['progress']>=0.30 else None
    if name=='SECOND_ACCEPT7_P30':
        e=seq['second_attempt_accept7']; return e if e and e['progress']>=0.30 else None
    if name=='SECOND_ACCEPT7_P25':
        e=seq['second_attempt_accept7']; return e if e and e['progress']>=0.25 else None
    # Overextension at hinge, then EMA acceptance while still profitable.
    if name=='D20_25_RECLAIM7_P30':
        e=seq['first_reclaim7']; return e if seq['hinge_d20']<=-0.25 and e and e['progress']>=0.30 else None
    if name=='D20_25_2ABOVE7_P30':
        e=seq['first_2above7']; return e if seq['hinge_d20']<=-0.25 and e and e['progress']>=0.30 else None
    if name=='D7_20_2ABOVE7_P30':
        e=seq['first_2above7']; return e if seq['hinge_d7']<=-0.20 and e and e['progress']>=0.30 else None
    # Price-path pullback first, then EMA acceptance. Require EMA event at/after pullback event.
    if name=='PULL35_THEN_2ABOVE7':
        p=seq['first_pull35']; e=seq['first_2above7']; return e if p and e and e['k']>=p['k'] and e['progress']>=0.20 else None
    if name=='PULL30_THEN_2ABOVE7':
        p=seq['first_pull30']; e=seq['first_2above7']; return e if p and e and e['k']>=p['k'] and e['progress']>=0.20 else None
    return None

RULES=('2ABOVE7_P35','2ABOVE7_P30','2ABOVE7_P25','RECLAIM7_P35','RECLAIM7_P30',
       'ABOVE7_P35','ABOVE7_P30','SECOND_ACCEPT7_P30','SECOND_ACCEPT7_P25',
       'D20_25_RECLAIM7_P30','D20_25_2ABOVE7_P30','D7_20_2ABOVE7_P30',
       'PULL35_THEN_2ABOVE7','PULL30_THEN_2ABOVE7')


def build_enriched(rows,recs,e7,e20):
    out=[]
    for r in recs:
        q=dict(r); q['frozen']=frozen_action(r); q['seq']=sequence(rows,r['i'],r['state'],e7,e20) if r['state'] else None
        q['a52']=r['protect'] if q['frozen'] else r['base']
        out.append(q)
    return out


def evaluate(qs,rows,name):
    out=[]; actions=rescued=damaged=0; add_actions=0
    for r in qs:
        f=r['a52']
        if not r['frozen'] and r['seq']:
            ev=event_for_rule(r['seq'],name); ex=event_exit(rows,r['i'],ev) if ev else None
            if ex is not None:
                add_actions+=1; f=ex
                if r['a52']<=0 and f>0:rescued+=1
                if r['a52']>0 and f<=0:damaged+=1
        out.append({'ts':r['ts'],'base':r['a52'],'final':f})
    s=a52.summarize(out); b=a52.summarize(out,'base')
    s.update({'rule':name,'additional_actions':add_actions,'rescued':rescued,'damaged':damaged,'delta_vs_a52':rnd(s['pnl']-b['pnl'],3)})
    return s


def median_or_none(xs): return rnd(statistics.median(xs),4) if xs else None

def atlas(qs):
    # Only hinge trades untouched by A5.2; compare eventual negative vs positive A5.2 outcomes.
    z=[r for r in qs if r['seq'] and not r['frozen']]
    neg=[r for r in z if r['a52']<=0]; pos=[r for r in z if r['a52']>0]
    def group(g):
        d={'n':len(g)}
        for key in ('hinge_d7','hinge_d20','hinge_progress','hinge_mae'):
            d[key+'_med']=median_or_none([r['seq'][key] for r in g])
        for ev in ('first_reclaim7','first_2above7','second_attempt_accept7','first_pull35','first_pull30'):
            hits=[r['seq'][ev] for r in g if r['seq'][ev] is not None]
            d[ev+'_pct']=rnd(100*len(hits)/len(g),2) if g else None
            d[ev+'_progress_med']=median_or_none([x['progress'] for x in hits])
            d[ev+'_time_med']=median_or_none([x['time'] for x in hits])
        return d
    # Oracle capacity: among untouched A5.2 negatives, how many event exits would itself be positive.
    oracle={}
    for nm in RULES:
        n=good=0
        for r in neg:
            ev=event_for_rule(r['seq'],nm); ex=event_exit(G_ROWS,r['i'],ev) if ev else None
            if ex is not None:
                n+=1; good+=ex>0
        oracle[nm]={'negative_triggers':n,'positive_exits':good}
    return {'untouched_hinge':len(z),'negative':group(neg),'positive':group(pos),'oracle_negative_exit_capacity':oracle}

G_ROWS=None

def main():
    global G_ROWS
    rows=load(); G_ROWS=rows; im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); e7=a54.ema_series(rows,7); e20=a54.ema_series(rows,20)
    qs=build_enriched(rows,recs,e7,e20); split=int(len(qs)*.60); disc=qs[:split]; val=qs[split:]
    # A5.2 benchmark reconstructed from frozen state.
    def bench(part): return a52.summarize([{'ts':r['ts'],'final':r['a52']} for r in part])
    tests=[]
    for nm in RULES:
        d=evaluate(disc,rows,nm); v=evaluate(val,rows,nm); f=evaluate(qs,rows,nm)
        tests.append({'name':nm,'discovery':d,'validation':v,'full':f})
    cross=[x for x in tests if x['discovery']['delta_vs_a52']>0 and x['validation']['delta_vs_a52']>0 and x['full']['wr']>=bench(qs)['wr'] and x['full']['pnl']>=bench(qs)['pnl']]
    cross.sort(key=lambda x:(x['full']['wr'],x['full']['pnl'],-x['full']['damaged']),reverse=True)
    best=sorted(tests,key=lambda x:(x['full']['pnl'],x['full']['wr'],-x['full']['damaged']),reverse=True)
    out={'status':'A57_GIVEBACK_SEQUENCE','data':{'tuesdays':len(qs),'discovery':len(disc),'validation':len(val),'rules':len(RULES)},
         'a52_benchmark':{'discovery':bench(disc),'validation':bench(val),'full':bench(qs)},
         'atlas':{'discovery':atlas(disc),'validation':atlas(val),'full':atlas(qs)},
         'cross_period_upgrades':cross,'best_full':best}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
