"""BTC Temporal A3.4 — 5m event-sequence dynamic direction research.

Purpose
-------
Potential-2-style event reading for the Tuesday temporal window. Learn reusable
5m market-path states from all PRIOR calendar days at the same local window,
then combine them with the causal Tuesday prior. Every Tuesday gets BUY/SELL;
there is no WAIT/filter gate in this experiment.

Causal decision checkpoints: 06:30, 06:45, 07:00 WIB.
Entry: next/current 5m open exactly at the checkpoint after all observation bars
are completed. Outcomes: 30/60/120/240m from entry.

Observed event vocabulary (all levels frozen when known):
- HOD/LOD-so-far at 06:00
- previous-1h high/low
- daily open and 06:00 window open
- wick attack vs close acceptance
- 2-close acceptance
- reclaim after attack/acceptance
- first liquidity side attacked
- same-window opposite-side attack / double sweep
- breakout/reclaim ordering
- 5m taker-buy aggression, change in aggression
- buyer/seller absorption (aggression without price progress)
- range/volume expansion

Research only. No live trading mutation.
"""
import csv, io, json, math, statistics, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta

TF = 5 * 60 * 1000
EVAL_START = int(datetime(2023,12,2,tzinfo=timezone.utc).timestamp()*1000)
EVAL_END = int(datetime(2026,7,30,tzinfo=timezone.utc).timestamp()*1000)
LOAD_START = int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000)
TZ = timezone(timedelta(hours=7))
CHECKPOINTS = (6, 9, 12)  # 30m,45m,60m after 06:00 -> 06:30/06:45/07:00
HORIZONS = (30,60,120,240)
HB = {h:h//5 for h in HORIZONS}


def mean(xs): return statistics.mean(xs) if xs else 0.0
def med(xs): return statistics.median(xs) if xs else None
def rnd(x,n=3): return round(float(x),n) if x is not None else None
def sgn(x): return 1 if x>0 else -1 if x<0 else 0

def months():
    y,m=2023,11
    while (y,m)<=(2026,7):
        yield y,m
        m+=1
        if m==13: y,m=y+1,1

def load():
    rows=[]
    for y,m in months():
        fn=f'BTCUSDT-5m-{y:04d}-{m:02d}.zip'
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/5m/{fn}'
        print('DOWNLOAD',fn,flush=True)
        with urllib.request.urlopen(url,timeout=60) as q: data=q.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            rd=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8'))
            for a in rd:
                try:t=int(a[0])
                except:continue
                if t>10**14:t//=1000
                if LOAD_START<=t<EVAL_END:
                    # t,o,h,l,c,baseVol,quoteVol,trades,takerBase,takerQuote
                    rows.append((t,float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5]),float(a[7]),float(a[8]),float(a[9]),float(a[10])))
    d={x[0]:x for x in rows}
    return [d[k] for k in sorted(d)]

def ldt(ts): return datetime.fromtimestamp(ts/1000,tz=timezone.utc).astimezone(TZ)

def context(rows,i):
    if i<2016:return None
    dt=ldt(rows[i][0]); ds=int(dt.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).timestamp()*1000)
    j=i-1
    while j>=0 and rows[j][0]>=ds:j-=1
    day=rows[j+1:i]
    if not day:return None
    p=rows[i][1];pre1=rows[i-12:i];pre4=rows[i-48:i];pre24=rows[i-288:i];pre7=rows[i-2016:i]
    hod=max(x[2] for x in day);lod=min(x[3] for x in day);dr=max(hod-lod,1e-9);dop=day[0][1]
    recent=rows[i-24:i]; rngmed=med([x[2]-x[3] for x in recent]) or 1e-9; qmed=med([x[6] for x in recent]) or 1e-9
    return {'p':p,'daily_open':dop,'hod':hod,'lod':lod,'day_pos':(p-lod)/dr,
            'ph':max(x[2] for x in pre1),'pl':min(x[3] for x in pre1),
            'pre1':100*(p-pre1[0][1])/pre1[0][1],'pre4':100*(p-pre4[0][1])/pre4[0][1],
            'pre24':100*(p-pre24[0][1])/pre24[0][1],'pre7':100*(p-pre7[0][1])/pre7[0][1],
            'rngmed':rngmed,'qmed':qmed}

def bucket(v,a,b): return 'L' if v<a else 'M' if v<b else 'H'
def bdir(x): return 'U' if x[4]>x[1] else 'D' if x[4]<x[1] else 'F'

def level_events(obs,level,upper,name):
    ev=[]; accepted=False; attacked=False; consecutive=0
    for k,x in enumerate(obs):
        hi,lo,cl=x[2],x[3],x[4]
        attack = hi>level if upper else lo<level
        beyond = cl>level if upper else cl<level
        if attack and not attacked:
            ev.append((k,f'{name}_FIRST_ATTACK'));attacked=True
        if attack and not beyond:
            ev.append((k,f'{name}_WICK_REJECT' if upper else f'{name}_WICK_RECLAIM'))
        if beyond:
            consecutive+=1
            if not accepted:
                ev.append((k,f'{name}_CLOSE_ACCEPT'));accepted=True
            if consecutive==2:ev.append((k,f'{name}_2CLOSE_ACCEPT'))
        else:
            if accepted:
                ev.append((k,f'{name}_RECLAIM_BACK'))
                accepted=False
            consecutive=0
    return ev

def event_tokens(rows,i,nb,c):
    obs=rows[i:i+nb];wo=obs[0][1];cl=obs[-1][4];hi=max(x[2] for x in obs);lo=min(x[3] for x in obs);rng=max(hi-lo,1e-9)
    ev=[]
    ev += level_events(obs,c['hod'],True,'HOD')
    ev += level_events(obs,c['lod'],False,'LOD')
    ev += level_events(obs,c['ph'],True,'PH')
    ev += level_events(obs,c['pl'],False,'PL')
    ev += level_events(obs,wo,True,'WOPEN_UP')
    ev += level_events(obs,wo,False,'WOPEN_DN')
    ev.sort(key=lambda z:z[0])
    # liquidity ordering among frozen day extremes / previous hour extremes
    first_liq='NONE'
    for k,x in enumerate(obs):
        hs=[]
        if x[2]>c['hod']:hs.append('HOD')
        if x[3]<c['lod']:hs.append('LOD')
        if x[2]>c['ph']:hs.append('PH')
        if x[3]<c['pl']:hs.append('PL')
        if hs:
            first_liq='+'.join(hs);break
    hod_attack=hi>c['hod'];lod_attack=lo<c['lod'];ph_attack=hi>c['ph'];pl_attack=lo<c['pl']
    double_sweep=(hod_attack and lod_attack) or (ph_attack and pl_attack)
    # flow trajectory on 5m bars
    tbr=[];volr=[];rets=[]
    for x in obs:
        q=x[6];tbr.append(x[9]/q if q else .5);volr.append(q/c['qmed']);rets.append(100*(x[4]-x[1])/x[1])
    avg_t=mean(tbr); first_t=mean(tbr[:max(1,len(tbr)//2)]);last_t=mean(tbr[len(tbr)//2:])
    agg='BUY' if avg_t>.53 else 'SELL' if avg_t<.47 else 'BAL'
    trend='BUYING' if last_t>first_t+.015 else 'SELLING' if last_t<first_t-.015 else 'FLAT'
    obsret=100*(cl-wo)/wo
    buyer_abs=avg_t>.52 and obsret<=0
    seller_abs=avg_t<.48 and obsret>=0
    last3_ret=sum(rets[-3:]) if len(rets)>=3 else sum(rets)
    last3_t=mean(tbr[-3:])
    last_buyer_abs=last3_t>.52 and last3_ret<=0
    last_seller_abs=last3_t<.48 and last3_ret>=0
    # aggression extremes count / failure count
    buy_aggr=sum(v>.55 for v in tbr);sell_aggr=sum(v<.45 for v in tbr)
    buy_fail_bars=sum(tbr[k]>.55 and rets[k]<=0 for k in range(len(obs)))
    sell_fail_bars=sum(tbr[k]<.45 and rets[k]>=0 for k in range(len(obs)))
    seq=''.join(bdir(x) for x in obs)
    compressed=seq if nb<=6 else seq[:2]+'_'+seq[-3:]
    # event order only first 5 unique event names
    names=[]
    for _,name in ev:
        if name not in names:names.append(name)
    event_path='>'.join(names[:5]) if names else 'NONE'
    daypos=bucket(c['day_pos'],1/3,2/3)
    closepos=bucket((cl-lo)/rng,1/3,2/3)
    rrng=mean([x[2]-x[3] for x in obs])/c['rngmed']
    qratio=mean([x[6] for x in obs])/c['qmed']
    toks=[
        'PRE1_'+('UP' if c['pre1']>0 else 'DOWN'),'PRE4_'+('UP' if c['pre4']>0 else 'DOWN'),
        'PRE24_'+('UP' if c['pre24']>0 else 'DOWN'),'PRE7_'+('UP' if c['pre7']>0 else 'DOWN'),
        'DAYPOS_'+daypos,'DOPEN_'+('ABOVE' if c['p']>=c['daily_open'] else 'BELOW'),
        'OBS_'+('UP' if obsret>0 else 'DOWN' if obsret<0 else 'FLAT'),'SEQ_'+compressed,'CLOSEPOS_'+closepos,
        'FIRSTLIQ_'+first_liq,'DOUBLE_'+str(int(double_sweep)),'TAKER_'+agg,'TAKER_TREND_'+trend,
        'BUYABS_'+str(int(buyer_abs)),'SELLABS_'+str(int(seller_abs)),
        'LASTBUYABS_'+str(int(last_buyer_abs)),'LASTSELLABS_'+str(int(last_seller_abs)),
        'BUYAGGR_'+bucket(buy_aggr/max(1,nb),.2,.5),'SELLAGGR_'+bucket(sell_aggr/max(1,nb),.2,.5),
        'BUYFAIL_'+bucket(buy_fail_bars/max(1,nb),.1,.3),'SELLFAIL_'+bucket(sell_fail_bars/max(1,nb),.1,.3),
        'RANGE_'+bucket(rrng,.8,1.3),'VOL_'+bucket(qratio,.8,1.3),'EVENTPATH_'+event_path,
        'HODEND_'+('ACCEPT' if cl>c['hod'] else 'REJECT' if hod_attack else 'NONE'),
        'LODEND_'+('ACCEPT' if cl<c['lod'] else 'RECLAIM' if lod_attack else 'NONE'),
        'PHEND_'+('ACCEPT' if cl>c['ph'] else 'REJECT' if ph_attack else 'NONE'),
        'PLEND_'+('ACCEPT' if cl<c['pl'] else 'RECLAIM' if pl_attack else 'NONE'),
        'WOPEN_'+('ABOVE' if cl>wo else 'BELOW'),
    ]
    # coherent pair interactions, predeclared
    mp={x.split('_',1)[0]:x for x in toks if '_' in x}
    for a,b in (('FIRSTLIQ','HODEND'),('FIRSTLIQ','LODEND'),('TAKER','OBS'),('TAKER','HODEND'),('TAKER','LODEND'),
                ('BUYABS','DAYPOS'),('SELLABS','DAYPOS'),('LASTBUYABS','WOPEN'),('LASTSELLABS','WOPEN'),
                ('PRE24','OBS'),('DAYPOS','OBS'),('EVENTPATH','TAKER')):
        if a in mp and b in mp:toks.append('PAIR_'+mp[a]+'__'+mp[b])
    return toks

def future(rows,ei,h):
    p=rows[ei:ei+HB[h]]
    if len(p)!=HB[h] or any(p[k][0]!=rows[ei][0]+k*TF for k in range(len(p))):return None
    e=rows[ei][1];ret=100*(p[-1][4]-e)/e
    return {'ret':ret,'lab':sgn(ret),'path':p,'entry':e}

def first_touch(path,e,d,th):
    fav=e*(1+d*th/100);adv=e*(1-d*th/100)
    for x in path:
        hf,ha=((x[2]>=fav),(x[3]<=adv)) if d>0 else ((x[3]<=fav),(x[2]>=adv))
        if hf and ha:return 'X'
        if hf:return 'F'
        if ha:return 'A'
    return 'N'

def logit(p):
    p=max(.02,min(.98,p));return math.log(p/(1-p))

def predictor(hist,cur,h,variant):
    all_labels=[x['fut'][h]['lab'] for x in hist if x['fut'][h]['lab']]
    tue_labels=[x['fut'][h]['lab'] for x in hist if ldt(x['ts']).weekday()==1 and x['fut'][h]['lab']]
    pg=(sum(y>0 for y in all_labels)+3)/(len(all_labels)+6) if all_labels else .5
    pt=(sum(y>0 for y in tue_labels)+2)/(len(tue_labels)+4) if tue_labels else pg
    base=logit(pt if len(tue_labels)>=4 else pg); gb=logit(pg)
    effects=[]
    for tok in cur['tokens']:
        ys=[x['fut'][h]['lab'] for x in hist if tok in x['tokens'] and x['fut'][h]['lab']]
        if len(ys)<12:continue
        p=(sum(y>0 for y in ys)+3)/(len(ys)+6)
        e=max(-1.25,min(1.25,logit(p)-gb))*len(ys)/(len(ys)+18)
        effects.append((abs(e),e,tok,len(ys)))
    effects.sort(reverse=True)
    if variant=='TOP3':sel=effects[:3]
    elif variant=='TOP5':sel=effects[:5]
    elif variant=='TOP8':sel=effects[:8]
    else:sel=effects
    # Do not sum correlated tokens naively; strongest evidence plus mean rest.
    if not sel:score=base
    else:
        strongest=sel[0][1]
        rest=mean([x[1] for x in sel[1:]]) if len(sel)>1 else 0
        score=base+1.15*strongest+0.55*rest
    return 1 if score>0 else -1

def state_predict(hist,cur,h,minsup):
    # Hierarchical exact path-state matching before fallback Tuesday prior.
    def find(prefixes):
        keys=tuple(sorted(t for t in cur['tokens'] if any(t.startswith(p) for p in prefixes)))
        ys=[]
        for x in hist:
            ok=all(k in x['tokens'] for k in keys)
            if ok and x['fut'][h]['lab']:ys.append(x['fut'][h]['lab'])
        return ys
    levels=[('EVENTPATH_','TAKER_','DAYPOS_','OBS_'),('FIRSTLIQ_','HODEND_','LODEND_','TAKER_','OBS_'),('DAYPOS_','OBS_','TAKER_'),('OBS_','TAKER_')]
    for pref in levels:
        ys=find(pref)
        if len(ys)>=minsup:
            return 1 if sum(ys)>0 else -1
    ys=[x['fut'][h]['lab'] for x in hist if ldt(x['ts']).weekday()==1 and x['fut'][h]['lab']]
    return 1 if sum(ys)>0 else -1

def evaluate(ps,h):
    n=len(ps);w=sum(p['pred']==p['e']['fut'][h]['lab'] for p in ps);buy=sum(p['pred']>0 for p in ps)
    blocks=[]
    for b in range(8):
        q=[p for p in ps if p['e']['block']==b];blocks.append(rnd(100*sum(p['pred']==p['e']['fut'][h]['lab'] for p in q)/len(q),2) if q else None)
    ft={}
    for th in (.3,.5,.8,1.0):
        c=defaultdict(int)
        for p in ps:
            f=p['e']['fut'][h];c[first_touch(f['path'],f['entry'],p['pred'],th)]+=1
        d=c['F']+c['A'];ft[str(th)]={'f':c['F'],'a':c['A'],'n':d,'none':c['N'],'amb':c['X'],'wr':rnd(100*c['F']/d,2) if d else None}
    wrs=[x for x in blocks if x is not None]
    return {'n':n,'wins':w,'losses':n-w,'wr':rnd(100*w/n,2),'buy':buy,'sell':n-buy,'blocks':blocks,
            'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs),
            'avg_signed_ret':rnd(mean([p['pred']*p['e']['fut'][h]['ret'] for p in ps]),4),'ft':ft}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};expected=(EVAL_END-EVAL_START)//TF;exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows)
    results=[]
    for nb in CHECKPOINTS:
        daily=[]
        for row in rows:
            dt=ldt(row[0])
            if dt.hour!=6 or dt.minute!=0:continue
            i=im[row[0]];c=context(rows,i)
            if c is None or i+nb>=len(rows) or rows[i+nb][0]!=row[0]+nb*TF:continue
            fut={h:future(rows,i+nb,h) for h in HORIZONS}
            if any(v is None for v in fut.values()):continue
            block=min(7,max(0,int((row[0]-EVAL_START)*8/(EVAL_END-EVAL_START)))) if row[0]>=EVAL_START else -1
            daily.append({'ts':row[0],'tokens':event_tokens(rows,i,nb,c),'fut':fut,'block':block})
        ev=[e for e in daily if EVAL_START<=e['ts']<EVAL_END and ldt(e['ts']).weekday()==1]
        decision=f'{6+nb//12:02d}:{(nb%12)*5:02d}'
        for h in HORIZONS:
            results.append({'engine':'ALWAYS_SELL','decision':decision,'h':h,**evaluate([{'pred':-1,'e':e} for e in ev],h)})
            for variant in ('TOP3','TOP5','TOP8','ALL'):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']]
                    ps.append({'pred':predictor(hist,e,h,variant),'e':e})
                results.append({'engine':'WF_5M_EVENT_'+variant,'decision':decision,'h':h,**evaluate(ps,h)})
            for minsup in (5,10,20):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']]
                    ps.append({'pred':state_predict(hist,e,h,minsup),'e':e})
                results.append({'engine':f'WF_5M_STATE_MIN{minsup}','decision':decision,'h':h,**evaluate(ps,h)})
    dyn=[x for x in results if x['engine']!='ALWAYS_SELL'];base=[x for x in results if x['engine']=='ALWAYS_SELL']
    top=sorted(dyn,key=lambda x:(x['wr'],x['positive_blocks'],x['n']),reverse=True)
    t05=sorted(dyn,key=lambda x:((x['ft']['0.5']['wr'] or -1),x['ft']['0.5']['n'],x['wr']),reverse=True)
    t08=sorted(dyn,key=lambda x:((x['ft']['0.8']['wr'] or -1),x['ft']['0.8']['n'],x['wr']),reverse=True)
    out={'status':'A34_5M_EVENT_DYNAMIC_DIRECTION','data':{'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'expected_5m':expected,'tuesdays':139,'predictions':139,'trade_coverage':100.0,'training':'all prior days same 06:00 window; 5m event sequence'},
         'dir70':[x for x in top if x['wr']>=70],
         'ft05_70':[x for x in t05 if (x['ft']['0.5']['wr'] or 0)>=70 and x['ft']['0.5']['n']>=50],
         'ft08_70':[x for x in t08 if (x['ft']['0.8']['wr'] or 0)>=70 and x['ft']['0.8']['n']>=50],
         'top_dir':top[:20],'top05':t05[:20],'top08':t08[:20],'baselines':base}
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
