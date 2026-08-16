"""Saturday18 A7.18 — forensic atlas for the 9 A7.17 lockable signals.

No management optimization. For each strict-causal 240m signal, inspect what occurs after
the decision open and BEFORE a +0.20% protective boundary is first touched.

Question: do original winners demonstrate causal recovery/continuation before that boundary
more often than original losers? Same-bar recovery and lock => lock first.
"""
import json, statistics
import btc_temporal_saturday18_a717_lockable_profit_protection as a717
from btc_temporal_a34_5m_events import rnd, TF

RECOVERY=(0.35,0.40,0.45,0.50,0.55,0.60)
LOCK=0.20

def med(x): return rnd(statistics.median(x),4) if x else None

def event(rows,r):
    s=r['state']
    if not a717.detector(s):return None
    j=s['decision_i'];e=r['entry'];lock_px=e*(1+LOCK/100);end=min(len(rows),r['i']+a717.HOLD//5)
    out={'ts':r['ts'],'base':r['base'],'winner':r['base']>0,'decision_progress':s['progress'],'mfe_at_signal':s['mfe'],'taker':s['taker']}
    first_lock=None
    rec={z:None for z in RECOVERY}
    for k in range(j,end):
        if rows[k][0]!=rows[j][0]+(k-j)*TF:break
        x=rows[k]
        hit_lock=x[3]<=lock_px
        # adverse precedence: if lock is touched on this bar, no recovery from same bar counts.
        if hit_lock:
            first_lock=(k-j)*5
            break
        for z in RECOVERY:
            if rec[z] is None and x[2]>=e*(1+z/100):rec[z]=(k-j)*5
    out['lock_time']=first_lock
    for z in RECOVERY:out[f'recover_{z:.2f}_before_lock']=rec[z] is not None;out[f'recover_{z:.2f}_time']=rec[z]
    # Completed-bar rejection/recovery markers before lock.
    ema7_reclaim=ema20_reclaim=two_up=None
    e7=a717.a74.ema_series(rows,7);e20=a717.a74.ema_series(rows,20)
    streak=0
    stop=end if first_lock is None else min(end,j+first_lock//5)
    for k in range(j,stop):
        c=rows[k][4]
        if ema7_reclaim is None and c>e7[k]:ema7_reclaim=(k-j+1)*5
        if ema20_reclaim is None and c>e20[k]:ema20_reclaim=(k-j+1)*5
        streak=streak+1 if rows[k][4]>rows[k][1] else 0
        if two_up is None and streak>=2:two_up=(k-j+1)*5
    out['ema7_reclaim_before_lock']=ema7_reclaim;out['ema20_reclaim_before_lock']=ema20_reclaim;out['two_up_before_lock']=two_up
    return out

def grp(ev,win):
    q=[x for x in ev if x['winner']==win];o={'n':len(q),'decision_progress_med':med([x['decision_progress'] for x in q]),'lock_time_med':med([x['lock_time'] for x in q if x['lock_time'] is not None])}
    for z in RECOVERY:
        k=f'recover_{z:.2f}_before_lock';o[k]=sum(x[k] for x in q);o[f'recover_{z:.2f}_pct']=rnd(100*o[k]/len(q),2) if q else None
    o['ema7_reclaim_count']=sum(x['ema7_reclaim_before_lock'] is not None for x in q)
    o['ema20_reclaim_count']=sum(x['ema20_reclaim_before_lock'] is not None for x in q)
    o['two_up_count']=sum(x['two_up_before_lock'] is not None for x in q)
    return o

def main():
    rows,tsmap,funding,miss,recs=a717.build();ev=[event(rows,r) for r in recs];ev=[x for x in ev if x]
    d=[x for x in ev if x['ts']<=recs[82]['ts']];v=[x for x in ev if x['ts']>recs[82]['ts']]
    out={'status':'SATURDAY18_A718_LOCK_SIGNAL_FORENSICS','signals':len(ev),'full':{'winner':grp(ev,True),'loser':grp(ev,False)},'discovery':{'winner':grp(d,True),'loser':grp(d,False)},'validation':{'winner':grp(v,True),'loser':grp(v,False)},'events':ev}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
