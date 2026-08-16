"""BTC Temporal A5.3 — robustness of frozen A5.2 runner/protect rule.

Frozen candidate from A5.2:
- Parent Tuesday 06:00 SELL, TP1.35 / SL0.80 / hold6h.
- Hinge: first completed 5m candle that touches +0.50% short MFE.
- PROTECT only if trigger candle closes with <= +0.35% short progress AND
  cumulative pre/through-trigger MAE >= 0.20%.
- Protection lock +0.20%, executable from next 5m open/bar.

No candidate selection here. We report 8-block, yearly, intervention-level,
leave-one-action-out sensitivity, and a small local plateau around the frozen rule.
"""
import json, datetime
import btc_temporal_a52_runner_protect as a52
from btc_temporal_a34_5m_events import load, ldt, rnd, EVAL_START, EVAL_END

FROZEN=('HIGH_MAE_WEAK',{'weak_close':0.35,'mae':0.20})
LOCAL_WC=(0.30,0.35,0.40,0.45)
LOCAL_MAE=(0.15,0.20,0.25,0.30)

def action_records(recs,name,p):
    out=[]
    for r in recs:
        if r['protect'] is not None and a52.rule(name,r['state'],p):
            final=r['protect']
            out.append({'ts':r['ts'],'base':r['base'],'final':final,'delta':final-r['base'],
                        'rescued':r['base']<=0 and final>0,'damaged':r['base']>0 and final<=0,
                        'time_min':r['state']['time_min'],'progress_close':r['state']['progress_close'],
                        'mae':r['state']['mae'],'mfe':r['state']['mfe']})
    return out

def period_summary(recs,name,p):
    z=a52.evaluate(recs,name,p)
    return {k:z[k] for k in ('trades','wins','losses','wr','pnl','exp','pf','mdd','ls','blocks_pos','actions','rescued','damaged','delta')}

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; idx=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=a52.build(rows,idx); name,p=FROZEN
    full=period_summary(recs,name,p)
    acts=action_records(recs,name,p)

    blocks=[]
    span=EVAL_END-EVAL_START
    for b in range(8):
        q=[r for r in recs if min(7,max(0,int((r['ts']-EVAL_START)*8/span)))==b]
        blocks.append({'block':b+1,'n':len(q),'base':a52.summarize([{'ts':r['ts'],'final':r['base']} for r in q]),
                       'frozen':period_summary(q,name,p),'actions':len(action_records(q,name,p))})
    years=[]
    for y in sorted(set(ldt(r['ts']).year for r in recs)):
        q=[r for r in recs if ldt(r['ts']).year==y]
        years.append({'year':y,'n':len(q),'base':a52.summarize([{'ts':r['ts'],'final':r['base']} for r in q]),
                      'frozen':period_summary(q,name,p),'actions':len(action_records(q,name,p))})

    # Leave one intervention out: remove each action (revert that one to parent) to see dependence on a single event.
    loo=[]
    frozen_map={a['ts']:a for a in acts}
    for omit in acts:
        rs=[]
        for r in recs:
            f=r['base']
            if r['ts'] in frozen_map and r['ts']!=omit['ts']: f=frozen_map[r['ts']]['final']
            rs.append({'ts':r['ts'],'final':f})
        s=a52.summarize(rs)
        loo.append({'omitted_ts':omit['ts'],'omitted_delta':rnd(omit['delta'],3),'pnl':s['pnl'],'wr':s['wr'],'pf':s['pf']})

    plateau=[]
    for wc in LOCAL_WC:
        for m in LOCAL_MAE:
            q=a52.evaluate(recs,'HIGH_MAE_WEAK',{'weak_close':wc,'mae':m})
            plateau.append({'weak_close':wc,'mae':m,'actions':q['actions'],'rescued':q['rescued'],'damaged':q['damaged'],
                            'wr':q['wr'],'pnl':q['pnl'],'delta':q['delta'],'pf':q['pf'],'mdd':q['mdd']})
    plateau.sort(key=lambda x:(x['pnl'],x['wr']),reverse=True)

    out={'status':'A53_FROZEN_ROBUSTNESS','frozen_rule':{'hinge':0.5,'weak_close_max':0.35,'mae_min':0.20,'lock':0.20},
         'full':full,'actions':acts,'block_results':blocks,'year_results':years,
         'leave_one_action_out':loo,'local_plateau':plateau}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
