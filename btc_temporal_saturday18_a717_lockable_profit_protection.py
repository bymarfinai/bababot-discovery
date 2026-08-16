"""Saturday18 A7.17 — strict-causal lockable profit protection.

Frozen parent: BUY Saturday 18:00 WIB / TP2.6% / SL1.2% / max18h.
No entry filtering; all 139 parent entries remain.

Frozen candidate from A7.16:
- checkpoint: after 240 completed minutes, decision at next 5m OPEN
- thesis has reached MFE >= +0.50%
- current progress is +0.20%..+0.40%
- completed-window taker edge < 0

Actions compared:
1) DIRECT: exit at the actual decision open.
2) LOCK +0.15% or +0.20%: if decision open is already through the lock, exit at the
   actual decision open; otherwise arm the lock while leaving original TP2.6 alive.
   If a later 5m bar touches both TP and lock, lock is assumed first (adverse precedence).

All EMA/flow state is strict causal via A7.13b. Historical funding is charged only until
actual simulated exit. One original BUY position => one round-trip fee total; no phantom
extra fee and no retrospective fills.
"""
import json
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a713b_strict_causal_separability as a713b
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade, FEE_PCT, NOTIONAL, max_dd, loss_streak
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080;CP=240
LOCKS=(0.15,0.20)

def detector(s):
    return bool(s and s['mfe']>=0.5 and 0.20<=s['progress']<=0.40 and s['taker']<0)

def block_id(ts): return min(7,max(0,int((ts-EVAL_START)*8/(EVAL_END-EVAL_START))))

def funding_long(funding,tsmap,entry_ts,exit_ts,qty,entry_px):
    z=0.0
    for ft,rate in funding:
        if ft<=entry_ts:continue
        if ft>exit_ts:break
        px=(tsmap.get(ft) or [None,entry_px])[1]
        z += -qty*px*rate
    return z

def pnl_at_exit(entry_px,exit_px,entry_ts,exit_ts,funding,tsmap):
    gross_pct=100*(exit_px-entry_px)/entry_px
    raw=NOTIONAL*(gross_pct-FEE_PCT)/100.0
    fp=funding_long(funding,tsmap,entry_ts,exit_ts,NOTIONAL/entry_px,entry_px)
    return raw+fp

def managed(rows,r,mode,funding,tsmap,lock=None):
    s=r['state']
    if not detector(s): return r['base'],False,'NO_SIGNAL'
    j=s['decision_i']; e=r['entry']; dec=rows[j][1]; entry_ts=rows[r['i']][0]
    if mode=='DIRECT':
        return pnl_at_exit(e,dec,entry_ts,rows[j][0],funding,tsmap),True,'DIRECT'
    lock_px=e*(1+lock/100.0); tp_px=e*(1+TP/100.0)
    # A missed/through lock can only be filled at the actual decision open.
    if dec<=lock_px:
        return pnl_at_exit(e,dec,entry_ts,rows[j][0],funding,tsmap),True,'MARKET_THROUGH_LOCK'
    end=min(len(rows),r['i']+HOLD//5)
    exit_px=None;exit_i=None;reason='TIMEOUT'
    for k in range(j,end):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:return r['base'],False,'DATA_GAP'
        x=rows[k]; hit_lock=x[3]<=lock_px; hit_tp=x[2]>=tp_px
        if hit_lock and hit_tp:
            exit_px=lock_px;exit_i=k;reason='LOCK_AMBIG';break
        if hit_lock:
            exit_px=lock_px;exit_i=k;reason='LOCK';break
        if hit_tp:
            exit_px=tp_px;exit_i=k;reason='TP';break
    if exit_px is None:
        exit_i=end-1;exit_px=rows[exit_i][4]
    return pnl_at_exit(e,exit_px,entry_ts,rows[exit_i][0],funding,tsmap),True,reason

def summarize(vals,key):
    p=[x[key] for x in vals];n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    blocks=[rnd(sum(x[key] for x in vals if block_id(x['ts'])==b),3) for b in range(8)]
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4),
      'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(max_dd(p),3),'ls':loss_streak(p),
      'positive_blocks':sum(x>0 for x in blocks),'blocks':blocks}

def evaluate(rows,recs,mode,funding,tsmap,lock=None):
    vals=[];actions=rescued=damaged=clipped=improved_losses=0;reasons={}
    for r in recs:
        final,act,reason=managed(rows,r,mode,funding,tsmap,lock)
        if act:
            actions+=1;reasons[reason]=reasons.get(reason,0)+1
            if r['base']<=0 and final>0:rescued+=1
            if r['base']>0 and final<=0:damaged+=1
            if r['base']>0 and final>0 and final<r['base']:clipped+=1
            if r['base']<=0 and final>r['base']:improved_losses+=1
        vals.append({'ts':r['ts'],'base':r['base'],'final':final})
    b=summarize(vals,'base');z=summarize(vals,'final')
    z.update({'delta':rnd(z['pnl']-b['pnl'],3),'actions':actions,'rescued':rescued,'damaged':damaged,
              'clipped_winners':clipped,'improved_losses':improved_losses,'reasons':reasons})
    return z

def build():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows}
    e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);funding,_,miss=load_funding();recs=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==5 and d.hour==18 and d.minute==0):continue
        i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
        if t is None:continue
        base,_,_=a74.funding_adjust(rows,t,funding,tsmap)
        recs.append({'i':i,'ts':x[0],'entry':t['entry'],'base':base,
                     'state':a713b.causal_state(rows,i,CP,e7,e20)})
    return rows,tsmap,funding,miss,recs

def main():
    rows,tsmap,funding,miss,recs=build();disc=recs[:83];val=recs[83:]
    base=summarize([{'ts':r['ts'],'base':r['base']} for r in recs],'base')
    configs=[('DIRECT',None)]+[('LOCK',x) for x in LOCKS]
    out=[]
    for mode,lock in configs:
        out.append({'mode':mode,'lock':lock,
          'discovery':evaluate(rows,disc,mode,funding,tsmap,lock),
          'validation':evaluate(rows,val,mode,funding,tsmap,lock),
          'full':evaluate(rows,recs,mode,funding,tsmap,lock)})
    print('RESULT_JSON',json.dumps({'status':'SATURDAY18_A717_LOCKABLE_PROFIT_PROTECTION','parent':base,
      'checkpoint_min':CP,'detector':'MFE>=0.5 & progress 0.20..0.40 & taker<0','funding_missing':miss,'configs':out},separators=(',',':')),flush=True)
if __name__=='__main__':main()
