"""BTC Temporal A5.9 — frozen robustness for A5.8 fast mean-reversion rule.

Frozen candidate selected in A5.8:
- keep A5.2 frozen management first;
- only on A5.2-untouched hinge trades;
- hinge close >=0.40% below EMA20 (d20 <= -0.40%);
- completed close gives back to <= +0.30% short progress within <=60 minutes after hinge;
- from next 5m open arm +0.20% profit lock (or exit actual open if lock already lost), retain TP1.35.

No re-selection here. Report block/year/action/LOO and compact local plateau.
"""
import json
import btc_temporal_a52_runner_protect as a52
import btc_temporal_a54_ema_failure_state as a54
import btc_temporal_a57_giveback_sequence as a57
import btc_temporal_a58_fast_mean_reversion as a58
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

FROZEN=('PULL30',0.40,60,'LOCK20')


def final_for(r,rows,cfg):
    f=r['a52']; action=None
    if not r['frozen'] and r['seq']:
        ev=a58.candidate(r['seq'],cfg[0],cfg[1],cfg[2])
        ex=a58.lock20_result(rows,r['i'],ev) if ev else None
        if ex is not None:
            f=ex
            action={'ts':r['ts'],'base_a52':r['a52'],'final':f,'delta':f-r['a52'],
                    'rescued':r['a52']<=0 and f>0,'damaged':r['a52']>0 and f<=0,
                    'hinge_d20':r['seq']['hinge_d20'],'hinge_d7':r['seq']['hinge_d7'],
                    'hinge_time':r['seq']['hinge_time'],'event_time':ev['time'],
                    'latency':ev['time']-r['seq']['hinge_time'],'event_progress':ev['progress']}
    return f,action


def summary(qs,rows,cfg=FROZEN):
    zs=[]; acts=[]
    for r in qs:
        f,a=final_for(r,rows,cfg); zs.append({'ts':r['ts'],'final':f})
        if a:acts.append(a)
    s=a52.summarize(zs); s.update({'actions':len(acts),'rescued':sum(a['rescued'] for a in acts),'damaged':sum(a['damaged'] for a in acts)})
    return s,acts


def bench(qs,key): return a52.summarize([{'ts':r['ts'],'final':r[key]} for r in qs])


def main():
    rows=load(); a57.G_ROWS=rows; im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); e7=a54.ema_series(rows,7); e20=a54.ema_series(rows,20)
    qs=a57.build_enriched(rows,recs,e7,e20)
    full,acts=summary(qs,rows)
    parent=bench(qs,'base'); a52b=bench(qs,'a52')

    # 8 chronological blocks using the same fixed full evaluation span.
    blocks=[]; span=EVAL_END-EVAL_START
    for b in range(8):
        q=[r for r in qs if min(7,max(0,int((r['ts']-EVAL_START)*8/span)))==b]
        s,aa=summary(q,rows)
        blocks.append({'block':b+1,'n':len(q),'parent':bench(q,'base'),'a52':bench(q,'a52'),'a59':s,
                       'actions':len(aa),'delta_vs_a52':rnd(s['pnl']-bench(q,'a52')['pnl'],3)})

    years=[]
    for y in sorted(set(ldt(r['ts']).year for r in qs)):
        q=[r for r in qs if ldt(r['ts']).year==y]; s,aa=summary(q,rows)
        years.append({'year':y,'n':len(q),'parent':bench(q,'base'),'a52':bench(q,'a52'),'a59':s,
                      'actions':len(aa),'delta_vs_a52':rnd(s['pnl']-bench(q,'a52')['pnl'],3)})

    # Leave one A5.8 action out (revert only that event to A5.2) to measure single-event dependence.
    amap={a['ts']:a for a in acts}; loo=[]
    for omit in acts:
        z=[]
        for r in qs:
            f=r['a52']
            if r['ts'] in amap and r['ts']!=omit['ts']:f=amap[r['ts']]['final']
            z.append({'ts':r['ts'],'final':f})
        s=a52.summarize(z)
        loo.append({'omitted_ts':omit['ts'],'omitted_delta':rnd(omit['delta'],3),'pnl':s['pnl'],'wr':s['wr'],'pf':s['pf'],'mdd':s['mdd']})

    # Local behavioral plateau around the frozen rule; descriptive only.
    plateau=[]
    for kind in ('PULL30','PULL35'):
        for d20 in (0.35,0.375,0.40,0.425,0.45):
            for lat in (30,45,60,75):
                cfg=(kind,d20,lat,'LOCK20'); s,aa=summary(qs,rows,cfg)
                plateau.append({'kind':kind,'d20':d20,'latency':lat,'actions':len(aa),
                                'rescued':sum(a['rescued'] for a in aa),'damaged':sum(a['damaged'] for a in aa),
                                'wr':s['wr'],'pnl':s['pnl'],'pf':s['pf'],'mdd':s['mdd'],'blocks_pos':s['blocks_pos'],
                                'delta_vs_a52':rnd(s['pnl']-a52b['pnl'],3)})
    plateau.sort(key=lambda x:(x['pnl'],x['wr']),reverse=True)

    split=int(len(qs)*.60); ds,da=summary(qs[:split],rows); vs,va=summary(qs[split:],rows)
    out={'status':'A59_FROZEN_FASTMR_ROBUSTNESS',
         'frozen_rule':{'kind':'PULL30','hinge_d20_max':-0.40,'max_latency_min':60,'management':'LOCK20','tp':1.35,'sl':0.80,'hold_min':360},
         'benchmarks':{'static_parent':parent,'a52':a52b,'a59':full},
         'split':{'discovery':ds,'validation':vs,'discovery_actions':len(da),'validation_actions':len(va)},
         'actions':acts,'blocks':blocks,'years':years,'leave_one_action_out':loo,'local_plateau':plateau[:30]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
