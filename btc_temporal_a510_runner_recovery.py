"""BTC Temporal A5.10 — fake mean-reversion / runner recovery.

Start from frozen A5.9. Only FastMR actions are eligible. After a +0.20 lock
has been armed, inspect COMPLETED 5m bars before that lock is touched. If a
causal bearish-continuation signal appears, cancel the lock at the next 5m open
and restore the original TP1.35 / SL0.80 / 6h runner.

Goal: recover clipped large winners without undoing rescued losers.
No entry/direction/TP/SL optimization.
"""
import json
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a54_ema_failure_state as a54
import btc_temporal_a57_giveback_sequence as a57
import btc_temporal_a58_fast_mean_reversion as a58
import btc_temporal_a59_frozen_fastmr_robustness as a59
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=1.35; LOCK=0.20; HOLD=360
CFG=a59.FROZEN


def progress(e,p): return 100.0*(e-p)/e


def first_signal(rows,i,ev,e7,rule):
    """Return completed-bar index of recovery signal before active lock/TP is touched."""
    dec=ev['k']+1; end=min(len(rows),i+HOLD//5)
    if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[ev['k']][0]+TF:return None
    e=rows[i][1]; pstop=e*(1-LOCK/100); tp=e*(1-TP/100)
    # If the lock is already lost at activation, no recovery window exists.
    if rows[dec][1]>=pstop:return None
    consec35=consec40=0
    ev_low=rows[ev['k']][3]
    for k in range(dec,end):
        x=rows[k]
        if x[0]!=rows[dec][0]+(k-dec)*TF:return None
        # Active stop/TP has intrabar precedence; cannot rescue retrospectively.
        if x[2]>=pstop or x[3]<=tp:return None
        pc=progress(e,x[4]); lowp=progress(e,x[3])
        consec35 = consec35+1 if pc>=0.35 else 0
        consec40 = consec40+1 if pc>=0.40 else 0
        reject7 = x[2]>=e7[k] and x[4]<e7[k]
        newlow = x[3] < ev_low
        ok=False
        if rule=='C35': ok=pc>=0.35
        elif rule=='C40': ok=pc>=0.40
        elif rule=='C45': ok=pc>=0.45
        elif rule=='C50': ok=pc>=0.50
        elif rule=='2C35': ok=consec35>=2
        elif rule=='2C40': ok=consec40>=2
        elif rule=='REJECT7_C30': ok=reject7 and pc>=0.30
        elif rule=='REJECT7_C35': ok=reject7 and pc>=0.35
        elif rule=='NEWLOW_C30': ok=newlow and pc>=0.30
        elif rule=='NEWLOW_C35': ok=newlow and pc>=0.35
        if ok:
            nx=k+1
            if nx>=end or nx>=len(rows) or rows[nx][0]!=x[0]+TF:return None
            # Lock remains active until cancellation at next open.
            if rows[nx][1]>=pstop:return None
            return {'k':k,'decision_i':nx,'time':(k-i)*5,'progress':pc,'low_progress':lowp,
                    'reject7':reject7,'newlow':newlow}
    return None


def build(rows):
    a57.G_ROWS=rows; im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); e7=a54.ema_series(rows,7); e20=a54.ema_series(rows,20)
    qs=a57.build_enriched(rows,recs,e7,e20)
    out=[]
    for r in qs:
        q=dict(r); f59,act=a59.final_for(r,rows,CFG); q['a59']=f59; q['a59_action']=act; q['fast_ev']=None
        if act and not r['frozen'] and r['seq']:
            q['fast_ev']=a58.candidate(r['seq'],CFG[0],CFG[1],CFG[2])
        out.append(q)
    return out,e7


def summarize(qs,key): return a52.summarize([{'ts':r['ts'],'final':r[key]} for r in qs])


def evaluate(qs,rows,e7,rule):
    z=[]; actions=[]
    for r in qs:
        f=r['a59']; sig=None
        if r.get('fast_ev'):
            sig=first_signal(rows,r['i'],r['fast_ev'],e7,rule)
            if sig:
                # Cancel FastMR lock and restore the already-open original runner.
                f=r['a52']
                actions.append({'ts':r['ts'],'a52':r['a52'],'a59':r['a59'],'final':f,
                                'delta_vs_a59':f-r['a59'],'signal_time':sig['time'],
                                'signal_progress':sig['progress'],'reject7':sig['reject7'],'newlow':sig['newlow'],
                                'restored_big_winner':r['a52']>r['a59'] and r['a52']>0,
                                'undid_rescue':r['a52']<=0 and r['a59']>0})
        z.append({'ts':r['ts'],'final':f})
    s=a52.summarize(z); b=summarize(qs,'a59')
    s.update({'rule':rule,'recovery_actions':len(actions),
              'restored_big_winners':sum(a['restored_big_winner'] for a in actions),
              'undid_rescues':sum(a['undid_rescue'] for a in actions),
              'delta_vs_a59':rnd(s['pnl']-b['pnl'],3)})
    return s,actions


def atlas(qs,rows,e7):
    out=[]
    for r in qs:
        if not r.get('fast_ev'):continue
        item={'ts':r['ts'],'a52':rnd(r['a52'],3),'a59':rnd(r['a59'],3),
              'delta59':rnd(r['a59']-r['a52'],3),'rescued':r['a52']<=0<r['a59'],
              'clipped_big_winner':r['a52']>1.0 and r['a59']<r['a52']-1.0}
        for rule in ('C35','C40','C45','C50','2C35','2C40','REJECT7_C30','REJECT7_C35','NEWLOW_C30','NEWLOW_C35'):
            s=first_signal(rows,r['i'],r['fast_ev'],e7,rule)
            item[rule]=None if not s else {'time':s['time'],'progress':rnd(s['progress'],3)}
        out.append(item)
    return out


def main():
    rows=load(); qs,e7=build(rows); split=int(len(qs)*.60); disc=qs[:split]; val=qs[split:]
    base59=summarize(qs,'a59'); tests=[]
    rules=('C35','C40','C45','C50','2C35','2C40','REJECT7_C30','REJECT7_C35','NEWLOW_C30','NEWLOW_C35')
    for rule in rules:
        d,da=evaluate(disc,rows,e7,rule); v,va=evaluate(val,rows,e7,rule); f,fa=evaluate(qs,rows,e7,rule)
        tests.append({'name':rule,'discovery':d,'validation':v,'full':f,'actions':fa})
    cross=[x for x in tests if x['discovery']['delta_vs_a59']>0 and x['validation']['delta_vs_a59']>0 and x['full']['pnl']>base59['pnl']]
    cross.sort(key=lambda x:(x['full']['pnl'],x['full']['wr'],-x['full']['undid_rescues']),reverse=True)
    best=sorted(tests,key=lambda x:(x['full']['pnl'],x['full']['wr']),reverse=True)
    out={'status':'A510_RUNNER_RECOVERY','data':{'tuesdays':len(qs),'fastmr_actions':sum(bool(r.get('fast_ev')) for r in qs),'rules':len(rules)},
         'a59_benchmark':base59,'atlas':atlas(qs,rows,e7),'cross_period_upgrades':cross,'best_full':best}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
