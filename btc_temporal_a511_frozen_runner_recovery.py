"""BTC Temporal A5.11 — frozen robustness for A5.10 runner recovery.

Frozen recovery rule selected in A5.10 on top of A5.9:
- A5.9 FastMR lock is already armed;
- before the +0.20 lock is touched, a COMPLETED 5m bar trades to/above EMA7
  but closes back below EMA7 (bearish EMA7 rejection);
- short close-progress remains >= +0.30%;
- cancel the lock at the next 5m open and restore TP1.35/SL0.80/6h runner.

No re-selection. Report split/block/year/leave-one-action-out and a tiny local
progress-threshold plateau around the frozen +0.30% level.
"""
import json
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a510_runner_recovery as a510
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

FROZEN_PROGRESS=0.30


def reject_signal(rows,i,ev,e7,pmin):
    dec=ev['k']+1; end=min(len(rows),i+a510.HOLD//5)
    if dec>=end or dec>=len(rows) or rows[dec][0]!=rows[ev['k']][0]+TF:return None
    e=rows[i][1]; pstop=e*(1-a510.LOCK/100); tp=e*(1-a510.TP/100)
    if rows[dec][1]>=pstop:return None
    for k in range(dec,end):
        x=rows[k]
        if x[0]!=rows[dec][0]+(k-dec)*TF:return None
        if x[2]>=pstop or x[3]<=tp:return None
        pc=a510.progress(e,x[4])
        if x[2]>=e7[k] and x[4]<e7[k] and pc>=pmin:
            nx=k+1
            if nx>=end or nx>=len(rows) or rows[nx][0]!=x[0]+TF:return None
            if rows[nx][1]>=pstop:return None
            return {'k':k,'time':(k-i)*5,'progress':pc}
    return None


def final_for(r,rows,e7,pmin=FROZEN_PROGRESS):
    f=r['a59']; act=None
    if r.get('fast_ev'):
        s=reject_signal(rows,r['i'],r['fast_ev'],e7,pmin)
        if s:
            f=r['a52']
            act={'ts':r['ts'],'a52':r['a52'],'a59':r['a59'],'final':f,
                 'delta':f-r['a59'],'signal_time':s['time'],'signal_progress':s['progress'],
                 'restored_large':r['a52']>=1.0 and r['a59']<1.0,
                 'undid_rescue':r['a52']<=0<r['a59']}
    return f,act


def summary(qs,rows,e7,pmin=FROZEN_PROGRESS):
    z=[]; acts=[]
    for r in qs:
        f,a=final_for(r,rows,e7,pmin); z.append({'ts':r['ts'],'final':f})
        if a:acts.append(a)
    s=a52.summarize(z); s.update({'actions':len(acts),'restored_large':sum(a['restored_large'] for a in acts),
                                  'undid_rescues':sum(a['undid_rescue'] for a in acts)})
    return s,acts


def bench(qs,key): return a52.summarize([{'ts':r['ts'],'final':r[key]} for r in qs])


def main():
    rows=load(); qs,e7=a510.build(rows); full,acts=summary(qs,rows,e7)
    a59b=bench(qs,'a59'); a52b=bench(qs,'a52'); parent=bench(qs,'base')
    split=int(len(qs)*.60); ds,da=summary(qs[:split],rows,e7); vs,va=summary(qs[split:],rows,e7)

    span=EVAL_END-EVAL_START; blocks=[]
    for b in range(8):
        q=[r for r in qs if min(7,max(0,int((r['ts']-EVAL_START)*8/span)))==b]
        s,aa=summary(q,rows,e7)
        blocks.append({'block':b+1,'n':len(q),'a59':bench(q,'a59'),'a511':s,
                       'actions':len(aa),'delta_vs_a59':rnd(s['pnl']-bench(q,'a59')['pnl'],3)})

    years=[]
    for y in sorted(set(ldt(r['ts']).year for r in qs)):
        q=[r for r in qs if ldt(r['ts']).year==y]; s,aa=summary(q,rows,e7)
        years.append({'year':y,'n':len(q),'a59':bench(q,'a59'),'a511':s,
                      'actions':len(aa),'delta_vs_a59':rnd(s['pnl']-bench(q,'a59')['pnl'],3)})

    # Leave one recovery action out, reverting it to A5.9.
    amap={a['ts']:a for a in acts}; loo=[]
    for omit in acts:
        z=[]
        for r in qs:
            f=r['a59'] if r['ts']==omit['ts'] else (amap[r['ts']]['final'] if r['ts'] in amap else r['a59'])
            z.append({'ts':r['ts'],'final':f})
        s=a52.summarize(z)
        loo.append({'omitted_ts':omit['ts'],'omitted_delta':rnd(omit['delta'],3),'pnl':s['pnl'],'wr':s['wr'],'pf':s['pf'],'mdd':s['mdd']})

    plateau=[]
    for p in (0.25,0.275,0.30,0.325,0.35,0.375,0.40):
        fs,fa=summary(qs,rows,e7,p); dd,daa=summary(qs[:split],rows,e7,p); vv,vaa=summary(qs[split:],rows,e7,p)
        plateau.append({'progress_min':p,'full':fs,'discovery_delta':rnd(dd['pnl']-bench(qs[:split],'a59')['pnl'],3),
                        'validation_delta':rnd(vv['pnl']-bench(qs[split:],'a59')['pnl'],3),
                        'action_deltas':[rnd(a['delta'],3) for a in fa]})

    out={'status':'A511_FROZEN_RUNNER_RECOVERY',
         'frozen_rule':{'after':'A5.9 FastMR arm','ema':'EMA7','pattern':'high >= EMA7 and close < EMA7',
                        'min_short_progress':0.30,'decision':'cancel +0.20 lock next 5m open; restore TP1.35/SL0.80/6h'},
         'benchmarks':{'static_parent':parent,'a52':a52b,'a59':a59b,'a511':full},
         'split':{'discovery':ds,'validation':vs,'discovery_actions':len(da),'validation_actions':len(va)},
         'actions':acts,'blocks':blocks,'years':years,'leave_one_action_out':loo,'local_plateau':plateau}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
