"""BTC Temporal A5.6 — post-hinge EMA failure exits.

After a Tuesday SELL first achieves +0.50% short MFE, keep the original
TP1.35/SL0.80/6h runner. From subsequent COMPLETED 5m bars, test whether a
close/reclaim of EMA7 or EMA20 is a causal continuation-failure exit.
Exit occurs at the NEXT 5m open after the EMA signal. Parent TP/SL on the signal
bar takes precedence, so no retrospective rescue is allowed.

EMA still does not choose initial direction or entry.
"""
import json
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a54_ema_failure_state as a54
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import FEE_PCT, NOTIONAL

TP=1.35; SL=0.80; HOLD=360


def arm_ok(mode,s):
    if not s:return False
    if mode=='ALL':return True
    if mode=='MAE20':return s['mae']>=0.20
    if mode=='WEAK40':return s['progress_close']<=0.40
    if mode=='FROZEN':return s['progress_close']<=0.35 and s['mae']>=0.20
    return False


def sig(rule,rows,k,e7,e20):
    c=rows[k][4]; pc=rows[k-1][4] if k>0 else c
    if rule=='ABOVE7':return c>e7[k]
    if rule=='RECLAIM7':return c>e7[k] and pc<=e7[k-1]
    if rule=='2ABOVE7':return k>0 and c>e7[k] and pc>e7[k-1]
    if rule=='ABOVE7_UP':return c>e7[k] and e7[k]>e7[k-1]
    if rule=='ABOVE20':return c>e20[k]
    if rule=='RECLAIM20':return c>e20[k] and pc<=e20[k-1]
    if rule=='2ABOVE20':return k>0 and c>e20[k] and pc>e20[k-1]
    return False


def ema_exit(rows,i,s,e7,e20,mode,rule):
    if not arm_ok(mode,s):return None
    e=rows[i][1]; tp=e*(1-TP/100); sl=e*(1+SL/100)
    # Monitoring starts AFTER the hinge trigger candle. Signal on completed bar, exit next open.
    start=s['decision_i']; end=min(len(rows),i+HOLD//5)
    for k in range(start,end):
        if rows[k][0]!=rows[i][0]+(k-i)*TF:return None
        x=rows[k]; ht=x[3]<=tp; hs=x[2]>=sl
        if ht and hs:return None  # parent adverse-first ambiguity = parent exit, no EMA rescue
        if hs or ht:return None
        if sig(rule,rows,k,e7,e20):
            dec=k+1
            if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[k][0]+TF:return None
            ex=rows[dec][1]; gross=100*(e-ex)/e
            return NOTIONAL*(gross-FEE_PCT)/100
    return None


def cfgs():
    out=[]
    for mode in ('ALL','MAE20','WEAK40','FROZEN'):
        for rule in ('ABOVE7','RECLAIM7','2ABOVE7','ABOVE7_UP','ABOVE20','RECLAIM20','2ABOVE20'):
            out.append((mode,rule))
    return out


def eval_cfg(recs,rows,e7,e20,mode,rule):
    z=[]; actions=rescued=damaged=0
    for r in recs:
        f=r['base']; ex=ema_exit(rows,r['i'],r['state'],e7,e20,mode,rule) if r['state'] else None
        if ex is not None:
            f=ex; actions+=1
            if r['base']<=0 and f>0:rescued+=1
            if r['base']>0 and f<=0:damaged+=1
        z.append({'ts':r['ts'],'base':r['base'],'final':f})
    s=a52.summarize(z); b=a52.summarize(z,'base')
    s.update({'mode':mode,'rule':rule,'actions':actions,'rescued':rescued,'damaged':damaged,'delta':rnd(s['pnl']-b['pnl'],3)})
    return s


def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); e7=a54.ema_series(rows,7); e20=a54.ema_series(rows,20)
    split=int(len(recs)*.60); disc=recs[:split]; val=recs[split:]
    base=a52.summarize([{'ts':r['ts'],'final':r['base']} for r in recs])
    tests=[]
    for m,r in cfgs():
        d=eval_cfg(disc,rows,e7,e20,m,r); v=eval_cfg(val,rows,e7,e20,m,r); f=eval_cfg(recs,rows,e7,e20,m,r)
        tests.append({'name':m+'_'+r,'discovery':d,'validation':v,'full':f})
    cross=[x for x in tests if x['discovery']['delta']>0 and x['validation']['delta']>0 and x['full']['wr']>base['wr']]
    cross.sort(key=lambda x:(x['full']['pnl'],x['full']['wr'],-x['full']['damaged']),reverse=True)
    best=sorted(tests,key=lambda x:(x['full']['pnl'],x['full']['wr']),reverse=True)
    out={'status':'A56_POSTHINGE_EMA_EXIT','data':{'tuesdays':len(recs),'discovery':len(disc),'validation':len(val),'configs':len(tests)},
         'base_parent':base,'cross_period':cross,'best_full':best}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
