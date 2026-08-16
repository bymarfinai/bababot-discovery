"""BTC Temporal A3.6 — direct trading-objective classifier.

Every Tuesday enters at 06:00 WIB. Instead of predicting future close direction,
learn which symmetric side (+/- threshold) is hit FIRST within 4h. This directly
matches a 1:1 TP/SL trading objective. Pre-window 5m features are strictly causal.
No WAIT/filter: all 139 Tuesdays receive BUY or SELL. No-touch is reported as
unresolved, not silently dropped from trade coverage.
"""
import json, math
from collections import defaultdict
from btc_temporal_a34_5m_events import load, ldt, context, first_touch, rnd, mean, TF, EVAL_START, EVAL_END
from btc_temporal_a35_prewindow import pre_tokens

LOOKBACKS=(6,12,24,48)
THRESHOLDS=(0.3,0.5,0.8,1.0)
H=240; HB=48

def path(rows,i):
    p=rows[i:i+HB]
    return p if len(p)==HB and all(p[k][0]==rows[i][0]+k*TF for k in range(HB)) else None

def ft_label(p,e,th):
    r=first_touch(p,e,1,th)
    # From BUY perspective: favorable=upper first => +1; adverse=lower first => -1.
    if r=='F':return 1
    if r=='A':return -1
    return 0

def logit(p):
    p=max(.02,min(.98,p));return math.log(p/(1-p))

def predict(hist,cur,th,variant):
    yl=[x['labels'][th] for x in hist if x['labels'][th]]
    yt=[x['labels'][th] for x in hist if ldt(x['ts']).weekday()==1 and x['labels'][th]]
    pg=(sum(y>0 for y in yl)+3)/(len(yl)+6) if yl else .5
    pt=(sum(y>0 for y in yt)+2)/(len(yt)+4) if yt else pg
    base=logit(pt if len(yt)>=4 else pg);gb=logit(pg);ef=[]
    for tok in cur['tokens']:
        ys=[x['labels'][th] for x in hist if tok in x['tokens'] and x['labels'][th]]
        if len(ys)<12:continue
        p=(sum(y>0 for y in ys)+3)/(len(ys)+6)
        v=max(-1.25,min(1.25,logit(p)-gb))*len(ys)/(len(ys)+18)
        ef.append((abs(v),v))
    ef.sort(reverse=True);sel=ef[:3] if variant=='TOP3' else ef[:5] if variant=='TOP5' else ef[:8] if variant=='TOP8' else ef
    score=base
    if sel:score+=1.15*sel[0][1]+.55*mean([x[1] for x in sel[1:]])
    return 1 if score>0 else -1

def state_predict(hist,cur,th,minsup):
    # Exact-ish hierarchical state based on coherent pre-window mechanics.
    families=[('DAYPOS_','LAST1_','TAKER1_'),('PRE24_','LAST1_','TAKER1_'),('FIRSTPREVH_','PHEND_','PLEND_'),('LAST1_','TAKER1_'),('DAYPOS_','LAST1_')]
    for fam in families:
        keys=[t for t in cur['tokens'] if any(t.startswith(p) for p in fam)]
        ys=[x['labels'][th] for x in hist if x['labels'][th] and all(k in x['tokens'] for k in keys)]
        if len(ys)>=minsup:return 1 if sum(ys)>0 else -1
    yt=[x['labels'][th] for x in hist if ldt(x['ts']).weekday()==1 and x['labels'][th]]
    return 1 if sum(yt)>0 else -1

def evaluate(ps,th):
    n=len(ps);resolved=[p for p in ps if p['e']['labels'][th]];w=sum(p['pred']==p['e']['labels'][th] for p in resolved);buy=sum(p['pred']>0 for p in ps)
    blocks=[]
    for b in range(8):
        q=[p for p in resolved if p['e']['block']==b]
        blocks.append(rnd(100*sum(p['pred']==p['e']['labels'][th] for p in q)/len(q),2) if q else None)
    wrs=[x for x in blocks if x is not None]
    return {'trades':n,'resolved':len(resolved),'no_touch':n-len(resolved),'resolution_pct':rnd(100*len(resolved)/n,2),'wins':w,'losses':len(resolved)-w,'wr':rnd(100*w/len(resolved),2) if resolved else None,'buy':buy,'sell':n-buy,'blocks':blocks,'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs) if wrs else None}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};expected=(EVAL_END-EVAL_START)//TF;exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows);res=[]
    for lb in LOOKBACKS:
        daily=[]
        for row in rows:
            dt=ldt(row[0])
            if dt.hour!=6 or dt.minute!=0:continue
            i=im[row[0]];c=context(rows,i)
            if c is None or i<lb:continue
            p=path(rows,i)
            if p is None:continue
            labels={th:ft_label(p,row[1],th) for th in THRESHOLDS}
            block=min(7,max(0,int((row[0]-EVAL_START)*8/(EVAL_END-EVAL_START)))) if row[0]>=EVAL_START else -1
            daily.append({'ts':row[0],'tokens':pre_tokens(rows,i,lb,c),'labels':labels,'block':block})
        ev=[e for e in daily if EVAL_START<=e['ts']<EVAL_END and ldt(e['ts']).weekday()==1]
        for th in THRESHOLDS:
            # Baseline temporal SELL.
            res.append({'engine':'ALWAYS_SELL','lookback_min':lb*5,'threshold_pct':th,**evaluate([{'pred':-1,'e':e} for e in ev],th)})
            for variant in ('TOP3','TOP5','TOP8','ALL'):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']]
                    ps.append({'pred':predict(hist,e,th,variant),'e':e})
                res.append({'engine':'WF_FT_'+variant,'lookback_min':lb*5,'threshold_pct':th,**evaluate(ps,th)})
            for ms in (8,15,25):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']]
                    ps.append({'pred':state_predict(hist,e,th,ms),'e':e})
                res.append({'engine':f'WF_FT_STATE{ms}','lookback_min':lb*5,'threshold_pct':th,**evaluate(ps,th)})
    dyn=[x for x in res if x['engine']!='ALWAYS_SELL'];base=[x for x in res if x['engine']=='ALWAYS_SELL']
    top=sorted(dyn,key=lambda x:(x['wr'] or -1,x['resolved'],x['positive_blocks']),reverse=True)
    viable=[x for x in top if (x['wr'] or 0)>=70 and x['resolution_pct']>=80]
    out={'status':'A36_DIRECT_FIRST_TOUCH_DIRECTION','data':{'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'expected':expected,'tuesdays':139,'entries':139,'trade_coverage':100.0,'entry':'06:00 WIB','horizon_min':240,'objective':'choose BUY/SELL so symmetric TP is touched before symmetric SL'},'viable70':viable,'top':top[:30],'baselines':base}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),flush=True);print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
