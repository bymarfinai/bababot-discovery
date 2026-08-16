"""BTC Temporal A3.5 — pre-window 5m sequence -> 06:00 WIB BUY/SELL.

Key correction from A3.4: preserve the original A1 temporal edge by deciding at
06:00, not 30-60 minutes later. All features are computed from completed candles
BEFORE 06:00. Every Tuesday gets BUY/SELL; no WAIT/filter.

Train reusable pre-window mechanics from all prior calendar days at 06:00 and
combine with the historical Tuesday prior. Research only.
"""
import json, math
from collections import defaultdict
from btc_temporal_a34_5m_events import (
    load, ldt, context, future, first_touch, rnd, mean, med, sgn,
    TF, EVAL_START, EVAL_END, HORIZONS
)

LOOKBACKS=(6,12,24,48)  # 30m,60m,120m,240m of completed 5m bars before 06:00

def bucket(v,a,b):return 'L' if v<a else 'M' if v<b else 'H'
def bdir(x):return 'U' if x[4]>x[1] else 'D' if x[4]<x[1] else 'F'

def pre_tokens(rows,i,lb,c):
    obs=rows[i-lb:i];last1=rows[i-12:i];prev1=rows[i-24:i-12] if i>=24 else rows[i-12:i]
    entry=rows[i][1];start=obs[0][1];cl=obs[-1][4];hi=max(x[2] for x in obs);lo=min(x[3] for x in obs);rng=max(hi-lo,1e-9)
    ret=100*(cl-start)/start;ret1=100*(last1[-1][4]-last1[0][1])/last1[0][1]
    seq=''.join(bdir(x) for x in obs)
    seqc=seq if lb<=12 else seq[:3]+'_'+seq[-4:]
    # Daily range/location known exactly at 06:00.
    pos=c['day_pos'];dist_h=100*(c['hod']-entry)/entry;dist_l=100*(entry-c['lod'])/entry
    # Timing of current day's HOD/LOD: how recently they were established.
    day_start=i
    dt=ldt(rows[i][0]); day_open_ms=int(dt.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(__import__('datetime').timezone.utc).timestamp()*1000)
    while day_start>0 and rows[day_start-1][0]>=day_open_ms:day_start-=1
    day=rows[day_start:i]
    hod_idx=max(range(len(day)),key=lambda k:day[k][2]) if day else 0
    lod_idx=min(range(len(day)),key=lambda k:day[k][3]) if day else 0
    mins_since_hod=(len(day)-1-hod_idx)*5 if day else 0;mins_since_lod=(len(day)-1-lod_idx)*5 if day else 0
    # Previous-hour (04:00-05:00 if current last1 is 05:00-06:00) attack/reclaim by last hour.
    ph=max(x[2] for x in prev1);pl=min(x[3] for x in prev1);lh=max(x[2] for x in last1);ll=min(x[3] for x in last1);lc=last1[-1][4]
    ph_attack=lh>ph;pl_attack=ll<pl
    ph_end='ACCEPT' if lc>ph else 'REJECT' if ph_attack else 'NONE'
    pl_end='ACCEPT' if lc<pl else 'RECLAIM' if pl_attack else 'NONE'
    first='NONE'
    for x in last1:
        H=x[2]>ph;L=x[3]<pl
        if H or L:
            first='BOTH' if H and L else 'HIGH' if H else 'LOW';break
    double=ph_attack and pl_attack
    # Taker/volume and absorption on observed window + last hour.
    def flow(xs):
        q=sum(x[6] for x in xs);tb=sum(x[9] for x in xs);t=tb/q if q else .5
        px=100*(xs[-1][4]-xs[0][1])/xs[0][1]
        return t,px
    t,px=flow(obs);t1,px1=flow(last1)
    tprev,_=flow(prev1)
    agg='BUY' if t>.53 else 'SELL' if t<.47 else 'BAL';agg1='BUY' if t1>.53 else 'SELL' if t1<.47 else 'BAL'
    trend='BUYING' if t1>tprev+.015 else 'SELLING' if t1<tprev-.015 else 'FLAT'
    babs=t1>.52 and px1<=0;sabs=t1<.48 and px1>=0
    # Candle-level aggression failures within last hour.
    baf=saf=0
    for x in last1:
        tr=x[9]/x[6] if x[6] else .5;br=100*(x[4]-x[1])/x[1]
        baf+=tr>.55 and br<=0;saf+=tr<.45 and br>=0
    # Trend efficiency distinguishes orderly trend from chop.
    gross=sum(abs(100*(x[4]-x[1])/x[1]) for x in obs);eff=abs(ret)/gross if gross>1e-9 else 0
    # Range/volume relative to immediately preceding equal-size window.
    prev=rows[i-2*lb:i-lb] if i>=2*lb else obs
    range_ratio=(hi-lo)/max(1e-9,max(x[2] for x in prev)-min(x[3] for x in prev))
    qobs=sum(x[6] for x in obs)/len(obs);qpre=sum(x[6] for x in prev)/len(prev);qratio=qobs/max(qpre,1e-9)
    # Where close finishes inside observation range and daily range.
    closepos=(cl-lo)/rng
    toks=[
      'LB_'+str(lb*5),'PRE1_'+('UP' if c['pre1']>0 else 'DOWN'),'PRE4_'+('UP' if c['pre4']>0 else 'DOWN'),
      'PRE24_'+('UP' if c['pre24']>0 else 'DOWN'),'PRE7_'+('UP' if c['pre7']>0 else 'DOWN'),
      'DAYPOS_'+bucket(pos,1/3,2/3),'DOPEN_'+('ABOVE' if entry>=c['daily_open'] else 'BELOW'),
      'PREWIN_'+('UP' if ret>0 else 'DOWN' if ret<0 else 'FLAT'),'LAST1_'+('UP' if ret1>0 else 'DOWN' if ret1<0 else 'FLAT'),
      'SEQ_'+seqc,'CLOSEPOS_'+bucket(closepos,1/3,2/3),'EFF_'+bucket(eff,.25,.55),
      'DISTH_'+bucket(dist_h,.15,.5),'DISTL_'+bucket(dist_l,.15,.5),
      'HODREC_'+bucket(mins_since_hod,30,120),'LODREC_'+bucket(mins_since_lod,30,120),
      'FIRSTPREVH_'+first,'PHEND_'+ph_end,'PLEND_'+pl_end,'DOUBLE_'+str(int(double)),
      'TAKER_'+agg,'TAKER1_'+agg1,'TAKERTREND_'+trend,'BUYABS_'+str(int(babs)),'SELLABS_'+str(int(sabs)),
      'BUYFAIL_'+bucket(baf/12,.1,.3),'SELLFAIL_'+bucket(saf/12,.1,.3),
      'RANGEEXP_'+bucket(range_ratio,.8,1.3),'VOLEXP_'+bucket(qratio,.8,1.3),
    ]
    mp={x.split('_',1)[0]:x for x in toks if '_' in x}
    for a,b in (('DAYPOS','LAST1'),('PRE24','LAST1'),('HODREC','LAST1'),('LODREC','LAST1'),('FIRSTPREVH','PHEND'),('FIRSTPREVH','PLEND'),
                ('TAKER1','LAST1'),('TAKERTREND','LAST1'),('BUYABS','DAYPOS'),('SELLABS','DAYPOS'),('PHEND','DAYPOS'),('PLEND','DAYPOS')):
        if a in mp and b in mp:toks.append('PAIR_'+mp[a]+'__'+mp[b])
    return toks

def logit(p):
    p=max(.02,min(.98,p));return math.log(p/(1-p))

def predict(hist,cur,h,variant):
    yl=[e['fut'][h]['lab'] for e in hist if e['fut'][h]['lab']];yt=[e['fut'][h]['lab'] for e in hist if ldt(e['ts']).weekday()==1 and e['fut'][h]['lab']]
    pg=(sum(y>0 for y in yl)+3)/(len(yl)+6) if yl else .5;pt=(sum(y>0 for y in yt)+2)/(len(yt)+4) if yt else pg
    base=logit(pt if len(yt)>=4 else pg);gb=logit(pg);ef=[]
    for tok in cur['tokens']:
        ys=[e['fut'][h]['lab'] for e in hist if tok in e['tokens'] and e['fut'][h]['lab']]
        if len(ys)<12:continue
        p=(sum(y>0 for y in ys)+3)/(len(ys)+6);v=max(-1.25,min(1.25,logit(p)-gb))*len(ys)/(len(ys)+18)
        ef.append((abs(v),v))
    ef.sort(reverse=True);sel=ef[:3] if variant=='TOP3' else ef[:5] if variant=='TOP5' else ef[:8] if variant=='TOP8' else ef
    score=base
    if sel:score+=1.15*sel[0][1]+.55*mean([x[1] for x in sel[1:]])
    return 1 if score>0 else -1

def evaluate(ps,h):
    n=len(ps);w=sum(p['pred']==p['e']['fut'][h]['lab'] for p in ps);buy=sum(p['pred']>0 for p in ps);blocks=[]
    for b in range(8):
        q=[p for p in ps if p['e']['block']==b];blocks.append(rnd(100*sum(p['pred']==p['e']['fut'][h]['lab'] for p in q)/len(q),2) if q else None)
    ft={}
    for th in (.3,.5,.8,1.0):
        c=defaultdict(int)
        for p in ps:
            f=p['e']['fut'][h];c[first_touch(f['path'],f['entry'],p['pred'],th)]+=1
        d=c['F']+c['A'];ft[str(th)]={'f':c['F'],'a':c['A'],'n':d,'none':c['N'],'wr':rnd(100*c['F']/d,2) if d else None}
    wrs=[x for x in blocks if x is not None]
    return {'n':n,'wins':w,'losses':n-w,'wr':rnd(100*w/n,2),'buy':buy,'sell':n-buy,'blocks':blocks,'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs),'avg_signed_ret':rnd(mean([p['pred']*p['e']['fut'][h]['ret'] for p in ps]),4),'ft':ft}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};expected=(EVAL_END-EVAL_START)//TF;exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows);res=[]
    for lb in LOOKBACKS:
        daily=[]
        for row in rows:
            dt=ldt(row[0])
            if dt.hour!=6 or dt.minute!=0:continue
            i=im[row[0]];c=context(rows,i)
            if c is None or i<lb:continue
            fut={h:future(rows,i,h) for h in HORIZONS}
            if any(v is None for v in fut.values()):continue
            block=min(7,max(0,int((row[0]-EVAL_START)*8/(EVAL_END-EVAL_START)))) if row[0]>=EVAL_START else -1
            daily.append({'ts':row[0],'tokens':pre_tokens(rows,i,lb,c),'fut':fut,'block':block})
        ev=[e for e in daily if EVAL_START<=e['ts']<EVAL_END and ldt(e['ts']).weekday()==1]
        for h in HORIZONS:
            res.append({'engine':'ALWAYS_SELL','lookback_min':lb*5,'h':h,**evaluate([{'pred':-1,'e':e} for e in ev],h)})
            for variant in ('TOP3','TOP5','TOP8','ALL'):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']]
                    ps.append({'pred':predict(hist,e,h,variant),'e':e})
                res.append({'engine':'WF_PRE5M_'+variant,'lookback_min':lb*5,'h':h,**evaluate(ps,h)})
    dyn=[x for x in res if x['engine']!='ALWAYS_SELL'];base=[x for x in res if x['engine']=='ALWAYS_SELL']
    top=sorted(dyn,key=lambda x:(x['wr'],x['positive_blocks']),reverse=True);t05=sorted(dyn,key=lambda x:((x['ft']['0.5']['wr'] or -1),x['ft']['0.5']['n'],x['wr']),reverse=True);t08=sorted(dyn,key=lambda x:((x['ft']['0.8']['wr'] or -1),x['ft']['0.8']['n'],x['wr']),reverse=True)
    out={'status':'A35_PREWINDOW_5M_DYNAMIC_DIRECTION','data':{'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'expected':expected,'tuesdays':139,'predictions':139,'trade_coverage':100.0,'entry':'06:00 WIB exact','features':'completed 5m bars strictly before 06:00'},
         'dir70':[x for x in top if x['wr']>=70],'ft05_70':[x for x in t05 if (x['ft']['0.5']['wr'] or 0)>=70 and x['ft']['0.5']['n']>=50],'ft08_70':[x for x in t08 if (x['ft']['0.8']['wr'] or 0)>=70 and x['ft']['0.8']['n']>=50],'top_dir':top[:20],'top05':t05[:20],'top08':t08[:20],'baselines':base}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),flush=True);print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
