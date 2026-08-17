"""Friday T-Method F5.9 — causal sequential reversal router.

Uses only information available at each 5m decision open. All Friday15 entries
remain. At the FIRST signal while parent BUY is alive, compare:
- EXIT_ONLY: close BUY at actual decision open.
- REVERSE: close BUY and open fixed SHORT 0.7/0.7/180m (own fee).

Two compact mechanism families motivated by F5.8:
A) EXHAUSTION: terminal bullish burst / expansion before a potential turn.
B) CONFIRMATION: favorable excursion followed by causal giveback + seller turn.

Selection uses first 82 Fridays only. Last 56 are validation report-only.
A reversal rule is only scientifically interesting if REVERSE adds value over
EXIT_ONLY, not merely over the original BUY parent.
"""
import json, statistics
import btc_temporal_friday15_f57_reversal_pivot_atlas as F57
import btc_temporal_friday15_f58_prepivot_causal_signature as F58
from btc_temporal_a34_5m_events import load, ldt, rnd
from btc_temporal_friday15_a60_money_geometry import trade, max_dd, loss_streak


def summarize(ps):
    if not ps:return {'n':0}
    pos=sum(x for x in ps if x>0);neg=-sum(x for x in ps if x<=0);w=sum(x>0 for x in ps)
    return {'n':len(ps),'wr':rnd(100*w/len(ps),2),'pnl':rnd(sum(ps),3),'exp':rnd(statistics.mean(ps),4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(ps),3),'ls':loss_streak(ps)}


def build(rows):
    recs=[]
    for i in F57.indices(rows):
        p=trade(rows,i,F57.BUY_TP,F57.BUY_SL,F57.BUY_HOLD)
        if p is None:continue
        ev=[]
        for m in range(F57.START_MIN,F57.END_MIN+1,F57.STEP_MIN):
            j=i+m//5
            if j>=len(rows) or rows[j][0]!=rows[i][0]+(j-i)*F57.TF:continue
            if not F57.parent_alive_before(rows,i,j):continue
            z=F58.feat(rows,i,j); s=F57.short_trade(rows,j)
            if z is None or s is None:continue
            buy=F57.buy_close_pnl(rows[i][1],rows[j][1])
            z.update({'m':m,'j':j,'exit_only':buy,'reverse':buy+s['net_usd'],'short':s['net_usd'],'short_reason':s['reason']})
            ev.append(z)
        recs.append({'ts':rows[i][0],'parent':p['net_usd'],'reason':p['reason'],'events':ev})
    return recs


def configs():
    out=[]
    # Confirmation after an already useful BUY excursion.
    for mfe in (0.30,0.40,0.50,0.60):
      for gb in (0.05,0.10,0.15,0.20,0.30):
        out.append(('CONFIRM_5',{'mfe':mfe,'gb':gb}))
        out.append(('CONFIRM_15',{'mfe':mfe,'gb':gb}))
        out.append(('CONFIRM_FLOW',{'mfe':mfe,'gb':gb}))
        out.append(('CONFIRM_STRICT',{'mfe':mfe,'gb':gb}))
    # Exhaustion / terminal expansion while BUY still positive.
    for prog in (0.20,0.30,0.40,0.50,0.70):
      for rr in (1.5,2.0,2.5,3.0):
        out.append(('EXHAUST_RANGE',{'prog':prog,'rr':rr}))
        out.append(('EXHAUST_RANGE_FLOW',{'prog':prog,'rr':rr}))
        out.append(('EXHAUST_RANGE_VOL',{'prog':prog,'rr':rr}))
    return out


def fires(name,p,z):
    if name=='CONFIRM_5':return z['mfe']>=p['mfe'] and z['giveback']>=p['gb'] and z['ret5']<0
    if name=='CONFIRM_15':return z['mfe']>=p['mfe'] and z['giveback']>=p['gb'] and z['ret5']<0 and z['ret15']<0
    if name=='CONFIRM_FLOW':return z['mfe']>=p['mfe'] and z['giveback']>=p['gb'] and z['ret5']<0 and z['taker15']<0
    if name=='CONFIRM_STRICT':return z['mfe']>=p['mfe'] and z['giveback']>=p['gb'] and z['ret5']<0 and z['ret15']<0 and z['taker15']<0
    if name=='EXHAUST_RANGE':return z['progress']>=p['prog'] and z['ret5']>0 and z['range_ratio']>=p['rr']
    if name=='EXHAUST_RANGE_FLOW':return z['progress']>=p['prog'] and z['ret5']>0 and z['taker5']>0 and z['range_ratio']>=p['rr']
    if name=='EXHAUST_RANGE_VOL':return z['progress']>=p['prog'] and z['ret5']>0 and z['range_ratio']>=p['rr'] and z['volume_ratio']>=2.0
    return False


def evaluate(recs,name,p):
    parent=[];exits=[];revs=[];actions=[];shorts=[]
    for r in recs:
        parent.append(r['parent']);sig=None
        for z in r['events']:
            if fires(name,p,z):sig=z;break
        if sig is None:
            exits.append(r['parent']);revs.append(r['parent'])
        else:
            exits.append(sig['exit_only']);revs.append(sig['reverse']);shorts.append(sig['short'])
            actions.append({'ts':r['ts'],'m':sig['m'],'parent':r['parent'],'exit':sig['exit_only'],'reverse':sig['reverse'],'short':sig['short']})
    bp=summarize(parent);ex=summarize(exits);rv=summarize(revs);sh=summarize(shorts)
    return {'rule':name,'params':p,'actions':len(actions),'parent':bp,'exit_only':ex,'reverse':rv,'short_legs':sh,
            'exit_delta':rnd(ex['pnl']-bp['pnl'],3),'reverse_delta':rnd(rv['pnl']-bp['pnl'],3),
            'reverse_vs_exit':rnd(rv['pnl']-ex['pnl'],3),
            'action_minutes':{'median':rnd(statistics.median([a['m'] for a in actions]),2) if actions else None,
                              'min':min([a['m'] for a in actions],default=None),'max':max([a['m'] for a in actions],default=None)}}


def main():
    rows=load();recs=build(rows);split=int(len(recs)*.60);disc=recs[:split];val=recs[split:]
    base=summarize([r['parent'] for r in recs]);cand=[]
    for n,p in configs():
        d=evaluate(disc,n,p)
        if d['actions']<5:continue
        # Discovery selection requires the SHORT leg itself add positive value vs simply exiting.
        if d['reverse_delta']>0 and d['reverse_vs_exit']>0 and d['short_legs'].get('pnl',0)>0:
            v=evaluate(val,n,p);f=evaluate(recs,n,p)
            cand.append({'discovery':d,'validation':v,'full':f})
    cand.sort(key=lambda x:(x['discovery']['reverse_delta'],x['discovery']['reverse_vs_exit']),reverse=True)
    cross=[]
    for x in cand:
        d=x['discovery'];v=x['validation'];f=x['full']
        if v['reverse_delta']>0 and v['reverse_vs_exit']>0 and v['short_legs'].get('pnl',0)>0:
            cross.append(x)
    cross.sort(key=lambda x:(x['full']['reverse']['pnl'],x['validation']['reverse_delta'],x['full']['reverse_vs_exit']),reverse=True)
    # Best exit-only candidates separately: tells us if signal is useful only to close BUY, not reverse.
    exitc=[]
    for n,p in configs():
        d=evaluate(disc,n,p)
        if d['actions']>=5 and d['exit_delta']>0:
            v=evaluate(val,n,p);f=evaluate(recs,n,p)
            if v['exit_delta']>0:exitc.append({'discovery':d,'validation':v,'full':f})
    exitc.sort(key=lambda x:x['full']['exit_only']['pnl'],reverse=True)
    out={'status':'FRIDAY_TMETHOD_F59_CAUSAL_REVERSAL_ROUTER','data':{'entries':len(recs),'discovery':split,'validation':len(recs)-split,'configs':len(configs())},
         'baseline':base,'discovery_reverse_candidates':cand[:20],'strict_cross_positive_reverse':cross[:20],
         'strict_cross_positive_exit_only':exitc[:20],
         'notes':'All signals causal and first-fire sequential. Selection discovery only; validation report-only. Fixed SHORT geometry from F5.7.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
