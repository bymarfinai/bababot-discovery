"""A3.2 research only: learn 06:00 WIB path states from prior calendar days and evaluate forced BUY/SELL direction on every Tuesday. No orders/live code."""
import json, math
from collections import defaultdict
from btc_temporal_a31_pathscan import load, local, ctx, tokens, future, first_touch, rr, mean, TF, EVAL_START, EVAL_END, HORIZONS

DECISIONS=(1,2,3,4,6,8)

def enrich(xs):
    out=list(xs); d={}
    for x in xs:
        for p in ('DAYPOS','OBS','PRE24','PRE4','HOD','LOD','OPENEND','FIRST','LAST2','SEQ','OPENPATH','PH','PL'):
            if x.startswith(p+'_'): d[p]=x
    for a,b in (('DAYPOS','OBS'),('PRE24','OBS'),('PRE4','OBS'),('HOD','OBS'),('LOD','OBS'),('OPENEND','OBS'),('FIRST','OBS'),('LAST2','DAYPOS'),('SEQ','DAYPOS'),('OPENPATH','OBS'),('PH','OBS'),('PL','OBS')):
        if a in d and b in d: out.append('PAIR_'+d[a]+'__'+d[b])
    return out

def logit(p):
    p=max(.02,min(.98,p)); return math.log(p/(1-p))

def get_prior(hist,h,tue=False):
    ys=[e['fut'][h]['lab'] for e in hist if e['fut'][h]['lab'] and (not tue or local(e['ts']).weekday()==1)]
    return ((sum(y>0 for y in ys)+2)/(len(ys)+4),len(ys)) if ys else (.5,0)

def predict(hist,cur,h,mode):
    pg,_=get_prior(hist,h,False); pt,nt=get_prior(hist,h,True)
    base=logit(pt if mode.startswith('TUE') and nt>=4 else pg); gb=logit(pg); ef=[]
    for tok in cur['tokens']:
        ys=[e['fut'][h]['lab'] for e in hist if tok in e['tokens'] and e['fut'][h]['lab']]
        if len(ys)<10: continue
        p=(sum(y>0 for y in ys)+3)/(len(ys)+6)
        v=max(-1.1,min(1.1,logit(p)-gb))*len(ys)/(len(ys)+20)
        ef.append((abs(v),v))
    ef.sort(reverse=True)
    sel=ef[:3] if mode.endswith('TOP3') else ef[:5] if mode.endswith('TOP5') else ef
    score=base+(1.25*mean([x[1] for x in sel]) if sel else 0)
    return 1 if score>0 else -1

def evaluate(ps,h):
    n=len(ps); w=sum(p['pred']==p['e']['fut'][h]['lab'] for p in ps); buy=sum(p['pred']>0 for p in ps)
    blocks=[]
    for b in range(8):
        q=[p for p in ps if p['e']['block']==b]
        blocks.append(rr(100*sum(p['pred']==p['e']['fut'][h]['lab'] for p in q)/len(q),2) if q else None)
    ft={}
    for th in (.3,.5,.8,1.0):
        c=defaultdict(int)
        for p in ps:
            f=p['e']['fut'][h]; c[first_touch(f['path'],f['entry'],p['pred'],th)]+=1
        dn=c['F']+c['A']; ft[str(th)]={'f':c['F'],'a':c['A'],'n':dn,'none':c['N'],'wr':rr(100*c['F']/dn,2) if dn else None}
    wrs=[x for x in blocks if x is not None]
    return {'n':n,'wins':w,'losses':n-w,'wr':rr(100*w/n,2),'buy':buy,'sell':n-buy,'blocks':blocks,'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs),'ft':ft,'avg_signed_ret':rr(mean([p['pred']*p['e']['fut'][h]['ret'] for p in ps]),4)}

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; results=[]
    for nb in DECISIONS:
        daily=[]
        for row in rows:
            dt=local(row[0])
            if dt.hour!=6 or dt.minute!=0: continue
            i=im[row[0]]; c=ctx(rows,i)
            if c is None or i+nb>=len(rows): continue
            fs={h:future(rows,i+nb,h) for h in HORIZONS}
            if any(v is None for v in fs.values()): continue
            b=min(7,max(0,int((row[0]-EVAL_START)*8/(EVAL_END-EVAL_START)))) if row[0]>=EVAL_START else -1
            daily.append({'ts':row[0],'tokens':enrich(tokens(rows,i,nb,c)),'fut':fs,'block':b})
        ev=[e for e in daily if EVAL_START<=e['ts']<EVAL_END and local(e['ts']).weekday()==1]
        decision=f'{6+nb//4:02d}:{(nb%4)*15:02d}'
        for h in HORIZONS:
            results.append({'engine':'ALWAYS_SELL','decision':decision,'h':h,**evaluate([{'pred':-1,'e':e} for e in ev],h)})
            for mode in ('GENERAL_TOP3','GENERAL_TOP5','TUE_TOP3','TUE_TOP5','TUE_ALL'):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']]
                    ps.append({'pred':predict(hist,e,h,mode),'e':e})
                results.append({'engine':'CROSSDAY_'+mode,'decision':decision,'h':h,**evaluate(ps,h)})
    dyn=[x for x in results if x['engine']!='ALWAYS_SELL']; base=[x for x in results if x['engine']=='ALWAYS_SELL']
    top=sorted(dyn,key=lambda x:(x['wr'],x['positive_blocks']),reverse=True)
    t05=sorted(dyn,key=lambda x:((x['ft']['0.5']['wr'] or -1),x['ft']['0.5']['n']),reverse=True)
    t08=sorted(dyn,key=lambda x:((x['ft']['0.8']['wr'] or -1),x['ft']['0.8']['n']),reverse=True)
    out={'status':'A32_CROSSDAY_DYNAMIC_DIRECTION','data':{'tuesdays':139,'predictions':139,'trade_coverage':100.0,'training':'all prior calendar days at same temporal window'},'dir70':[x for x in top if x['wr']>=70],'ft05_70':[x for x in t05 if (x['ft']['0.5']['wr'] or 0)>=70 and x['ft']['0.5']['n']>=30],'ft08_70':[x for x in t08 if (x['ft']['0.8']['wr'] or 0)>=70 and x['ft']['0.8']['n']>=30],'top_dir':top[:15],'top05':t05[:15],'top08':t08[:15],'baselines':base}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')))
if __name__=='__main__': main()
