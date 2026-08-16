"""Saturday18 A7.22 — deep-runner (+0.8 MFE) giveback sequence atlas.

Classification only. Freeze parent and A7.19; do not change management here.
Universe: parent trades that causally reach +0.80% before SL/TP resolution.
Compare eventual parent winners vs D_DEEP_GIVEBACK_GE_0.8 losses.

After the first +0.80% hinge, observe completed 5m closes giving back to +0.70/+0.60/+0.50/+0.40,
plus first completed close below EMA7/EMA20. EMA values are computed from that completed bar,
which is causal because any action would occur next 5m open.
"""
import json, statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080;HINGE=0.8
GB=(0.70,0.60,0.50,0.40)

def med(x):return rnd(statistics.median(x),4) if x else None

def event(rows,i,e7,e20):
    e=rows[i][1];end=min(len(rows),i+HOLD//5);h=None
    for k in range(i,end):
        if rows[k][0]!=rows[i][0]+(k-i)*TF:return None
        x=rows[k]
        if x[3]<=e*(1-SL/100):return None
        if x[2]>=e*(1+HINGE/100):h=k;break
        if x[2]>=e*(1+TP/100):return None
    if h is None:return None
    times={z:None for z in GB}; below7=below20=None; two_below20=None; streak20=0
    for k in range(h+1,end):
        if rows[k][0]!=rows[h][0]+(k-h)*TF:break
        x=rows[k];elapsed=(k-h)*5
        for z in GB:
            if times[z] is None and x[4]<=e*(1+z/100):times[z]=elapsed
        if below7 is None and x[4]<e7[k]:below7=elapsed
        if x[4]<e20[k]:
            if below20 is None:below20=elapsed
            streak20+=1
            if two_below20 is None and streak20>=2:two_below20=elapsed
        else:streak20=0
    return {'hinge_min':(h-i)*5,'times':times,'below7':below7,'below20':below20,'two_below20':two_below20}

def grp(q):
    if not q:return {'n':0}
    o={'n':len(q),'hinge_min_med':med([x['ev']['hinge_min'] for x in q])}
    for z in GB:
        t=[x['ev']['times'][z] for x in q if x['ev']['times'][z] is not None]
        o[f'gb_{z:.2f}_reach']=len(t);o[f'gb_{z:.2f}_time_med']=med(t)
        for speed in (15,30,60,120):o[f'gb_{z:.2f}_within_{speed}']=sum(x['ev']['times'][z] is not None and x['ev']['times'][z]<=speed for x in q)
    for k in ('below7','below20','two_below20'):
        t=[x['ev'][k] for x in q if x['ev'][k] is not None];o[k+'_reach']=len(t);o[k+'_time_med']=med(t)
    return o

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};funding,_,miss=load_funding();e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);recs=[];sats=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if d.weekday()==5 and d.hour==18 and d.minute==0:
            sats.append(x[0]);i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
            if t is None:continue
            base,_,_=a74.funding_adjust(rows,t,funding,tsmap);p=a712.path_stats(rows,i);tax=a712.taxonomy(p,t['reason']) if base<=0 else 'WIN';ev=event(rows,i,e7,e20)
            if ev:recs.append({'ts':x[0],'base':base,'tax':tax,'ev':ev})
    split=sats[83];parts={'full':recs,'discovery':[r for r in recs if r['ts']<split],'validation':[r for r in recs if r['ts']>=split]}
    out={'status':'SATURDAY18_A722_DEEP_RUNNER_SEQUENCE','hinge':HINGE,'funding_missing':miss,'groups':{}}
    for name,q in parts.items():
        out['groups'][name]={'winner':grp([r for r in q if r['tax']=='WIN']),'D_loss':grp([r for r in q if r['tax']=='D_DEEP_GIVEBACK_GE_0.8'])}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
