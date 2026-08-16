"""Saturday18 A7.20 — weak-pop (+0.3..<0.5) sequence atlas.

Classification only, no management change.
Frozen parent remains Saturday18 BUY TP2.6/SL1.2/18h.

At the first causal +0.30% favorable hinge, compare eventual parent winners with taxonomy-B
losses (MFE +0.3..<+0.5). Observe whether +0.50 continuation occurs before giveback, and
how quickly completed 5m closes return to +0.25/+0.20/+0.15.

No EMA thresholds are tuned here.
"""
import json, statistics
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a712_loss_taxonomy as a712
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_saturday18_a70_money_geometry import trade
from btc_temporal_saturday18_a73_funding_cost_stress import load_funding

TP=2.6;SL=1.2;HOLD=1080;HINGE=0.30
GB=(0.25,0.20,0.15)

def med(x):return rnd(statistics.median(x),4) if x else None

def first_hinge(rows,i):
    e=rows[i][1];end=min(len(rows),i+HOLD//5);px=e*(1+HINGE/100)
    for k in range(i,end):
        if rows[k][0]!=rows[i][0]+(k-i)*TF:return None
        x=rows[k]
        # parent adverse precedence; if SL/TP already resolves same bar, do not create a hinge after resolution
        ht=x[2]>=e*(1+TP/100);hs=x[3]<=e*(1-SL/100)
        if hs:return None
        if x[2]>=px:return k
        if ht:return None
    return None

def seq(rows,i,h):
    e=rows[i][1];end=min(len(rows),i+HOLD//5);out={'hinge_min':(h-i)*5,'to_05_before_gb':{}}
    # first completed bar after hinge bar; no same-bar hindsight
    first05=None; gbtime={z:None for z in GB}
    for k in range(h+1,end):
        if rows[k][0]!=rows[h][0]+(k-h)*TF:break
        x=rows[k]
        if first05 is None and x[2]>=e*1.005:first05=(k-h)*5
        for z in GB:
            if gbtime[z] is None and x[4]<=e*(1+z/100):gbtime[z]=(k-h)*5
        if first05 is not None and all(v is not None for v in gbtime.values()):break
    out['to_05_time']=first05
    for z in GB:
        out[f'gb_{z:.2f}_time']=gbtime[z]
        out[f'up05_before_gb_{z:.2f}']=first05 is not None and (gbtime[z] is None or first05<gbtime[z])
    return out

def grp(q):
    if not q:return {'n':0}
    o={'n':len(q),'hinge_min_med':med([x['seq']['hinge_min'] for x in q]),'to_05_reach':sum(x['seq']['to_05_time'] is not None for x in q)}
    for z in GB:
        ts=[x['seq'][f'gb_{z:.2f}_time'] for x in q if x['seq'][f'gb_{z:.2f}_time'] is not None]
        o[f'gb_{z:.2f}_reach']=len(ts);o[f'gb_{z:.2f}_time_med']=med(ts)
        o[f'up05_before_gb_{z:.2f}_count']=sum(x['seq'][f'up05_before_gb_{z:.2f}'] for x in q)
    return o

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};tsmap={x[0]:x for x in rows};funding,_,miss=load_funding();recs=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==5 and d.hour==18 and d.minute==0):continue
        i=im[x[0]];t=trade(rows,i,TP,SL,HOLD)
        if t is None:continue
        base,_,_=a74.funding_adjust(rows,t,funding,tsmap);p=a712.path_stats(rows,i);tax=a712.taxonomy(p,t['reason']) if base<=0 else 'WIN'
        h=first_hinge(rows,i)
        if h is not None:recs.append({'ts':x[0],'base':base,'tax':tax,'seq':seq(rows,i,h)})
    dcut=EVAL_START+(EVAL_END-EVAL_START)*83/139
    # preserve canonical first83 occurrence split by ordering, not timestamp approximation
    recs.sort(key=lambda x:x['ts']); all_occ=[]
    # derive split from chronological occurrence rank in original 139: rebuild ordered Saturday timestamps
    sats=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            z=ldt(x[0])
            if z.weekday()==5 and z.hour==18 and z.minute==0:sats.append(x[0])
    split_ts=sats[83]
    parts={'full':recs,'discovery':[r for r in recs if r['ts']<split_ts],'validation':[r for r in recs if r['ts']>=split_ts]}
    out={'status':'SATURDAY18_A720_WEAKPOP_SEQUENCE','hinge':HINGE,'funding_missing':miss,'groups':{}}
    for name,q in parts.items():
        out['groups'][name]={'winner':grp([r for r in q if r['tax']=='WIN']),'B_weakpop_loss':grp([r for r in q if r['tax']=='B_WEAK_POP_0.3_TO_0.5'])}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
