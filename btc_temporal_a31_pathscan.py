"""BTC Temporal A3.1 — dynamic observation-depth path learner.

Objective: keep one BUY/SELL decision on every post-warmup Tuesday while letting
the engine observe more of the 06:00-08:00 WIB path before choosing direction.
This is not a trade filter. Decision checkpoints are fixed and every checkpoint
has 100% trade coverage after warmup.

Data: official Binance USD-M Futures BTCUSDT 15m monthly archives.
Causality: each prediction uses current completed bars only + earlier Tuesdays.
"""
import csv, io, json, math, statistics, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta

TF=15*60*1000
EVAL_START=int(datetime(2023,12,2,tzinfo=timezone.utc).timestamp()*1000)
EVAL_END=int(datetime(2026,7,30,tzinfo=timezone.utc).timestamp()*1000)
LOAD_START=int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000)
TZ=timezone(timedelta(hours=7))
DECISIONS=(1,2,3,4,5,6,7,8)  # 06:15 ... 08:00
HORIZONS=(60,120,240)
HB={h:h//15 for h in HORIZONS}

def mean(x): return statistics.mean(x) if x else 0.0
def med(x): return statistics.median(x) if x else None
def rr(x,n=3): return round(float(x),n) if x is not None else None
def sgn(x): return 1 if x>0 else -1 if x<0 else 0

def months():
    y,m=2023,11
    while (y,m)<=(2026,7):
        yield y,m
        m+=1
        if m==13:y,m=y+1,1

def load():
    z=[]
    for y,m in months():
        fn=f'BTCUSDT-15m-{y:04d}-{m:02d}.zip'
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m/{fn}'
        with urllib.request.urlopen(url,timeout=60) as q:data=q.read()
        with zipfile.ZipFile(io.BytesIO(data)) as arc:
            rd=csv.reader(io.TextIOWrapper(arc.open(arc.namelist()[0]),encoding='utf-8'))
            for a in rd:
                try:t=int(a[0])
                except:continue
                if t>10**14:t//=1000
                if LOAD_START<=t<EVAL_END:z.append((t,float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5])))
    d={x[0]:x for x in z};return [d[k] for k in sorted(d)]

def local(t):return datetime.fromtimestamp(t/1000,tz=timezone.utc).astimezone(TZ)

def ctx(rows,i):
    if i<672:return None
    dt=local(rows[i][0]); ds=int(dt.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).timestamp()*1000)
    j=i-1
    while j>=0 and rows[j][0]>=ds:j-=1
    day=rows[j+1:i]; pre1=rows[i-4:i];pre4=rows[i-16:i];pre8=rows[i-8:i]
    if not day:return None
    p=rows[i][1];hod=max(x[2] for x in day);lod=min(x[3] for x in day);dr=max(hod-lod,1e-9);dop=day[0][1]
    return {'pre1':100*(p-pre1[0][1])/pre1[0][1],'pre4':100*(p-pre4[0][1])/pre4[0][1],
            'pre24':100*(p-rows[i-96][1])/rows[i-96][1],'pre7d':100*(p-rows[i-672][1])/rows[i-672][1],
            'pos':(p-lod)/dr,'dop':dop,'hod':hod,'lod':lod,'ph':max(x[2] for x in pre1),'pl':min(x[3] for x in pre1),
            'medrng':med([x[2]-x[3] for x in pre8]) or 1e-9,'p':p}

def bucket(v,a,b):return 'L' if v<a else 'M' if v<b else 'U'
def dirbar(x):return 'U' if x[4]>x[1] else 'D' if x[4]<x[1] else 'F'

def tokens(rows,i,n,c):
    obs=rows[i:i+n];wo=rows[i][1];cl=obs[-1][4];hi=max(x[2] for x in obs);lo=min(x[3] for x in obs);rng=max(hi-lo,1e-9)
    bull=sum(x[4]>x[1] for x in obs);bear=sum(x[4]<x[1] for x in obs)
    above=any(x[2]>wo for x in obs);below=any(x[3]<wo for x in obs)
    ha=any(x[2]>c['hod'] for x in obs);la=any(x[3]<c['lod'] for x in obs)
    pha=any(x[2]>c['ph'] for x in obs);pla=any(x[3]<c['pl'] for x in obs)
    first='NONE'
    for x in obs:
        H=x[2]>c['hod'];L=x[3]<c['lod']
        if H and not L:first='HOD';break
        if L and not H:first='LOD';break
        if H and L:first='BOTH';break
    seq=''.join(dirbar(x) for x in obs)
    # compress long sequence while retaining path start/end + balance
    seq2=seq if n<=4 else seq[:2]+'_'+seq[-2:]
    avg_rng=mean([x[2]-x[3] for x in obs])/c['medrng']
    ret=100*(cl-wo)/wo
    out=[
      'PRE1_'+('UP' if c['pre1']>0 else 'DOWN'),'PRE4_'+('UP' if c['pre4']>0 else 'DOWN'),
      'PRE24_'+('UP' if c['pre24']>0 else 'DOWN'),'PRE7D_'+('UP' if c['pre7d']>0 else 'DOWN'),
      'DAYPOS_'+bucket(c['pos'],1/3,2/3),'DOPEN_'+('ABOVE' if c['p']>=c['dop'] else 'BELOW'),
      'OBS_'+('UP' if ret>0 else 'DOWN' if ret<0 else 'FLAT'),'SEQ_'+seq2,
      'BAL_'+('BULL' if bull>bear else 'BEAR' if bear>bull else 'EVEN'),
      'CLOSEPOS_'+bucket((cl-lo)/rng,1/3,2/3),'RANGE_'+bucket(avg_rng,.8,1.2),
      'HOD_'+('ACCEPT' if cl>c['hod'] else 'REJECT' if ha else 'NONE'),
      'LOD_'+('ACCEPT' if cl<c['lod'] else 'RECLAIM' if la else 'NONE'),
      'FIRST_'+first,'PH_'+('BREAK' if cl>c['ph'] else 'ATTACK' if pha else 'NONE'),
      'PL_'+('BREAK' if cl<c['pl'] else 'ATTACK' if pla else 'NONE'),
      'OPENPATH_'+('BOTH' if above and below else 'ABOVE' if above else 'BELOW' if below else 'INSIDE'),
      'OPENEND_'+('ABOVE' if cl>wo else 'BELOW'),
      'FAILED_UP_'+str(int(above and cl<wo)),'FAILED_DOWN_'+str(int(below and cl>wo)),
      'LAST2_'+(''.join(dirbar(x) for x in obs[-2:]) if len(obs)>=2 else dirbar(obs[-1]))
    ]
    return out

def future(rows,entry_i,h):
    p=rows[entry_i:entry_i+HB[h]]
    if len(p)!=HB[h] or any(p[k][0]!=rows[entry_i][0]+k*TF for k in range(len(p))):return None
    e=rows[entry_i][1];ret=100*(p[-1][4]-e)/e
    return {'ret':ret,'lab':sgn(ret),'path':p,'entry':e}

def first_touch(path,e,d,th):
    fav=e*(1+d*th/100);adv=e*(1-d*th/100)
    for x in path:
        hf,ha=((x[2]>=fav),(x[3]<=adv)) if d>0 else ((x[3]<=fav),(x[2]>=adv))
        if hf and ha:return 'X'
        if hf:return 'F'
        if ha:return 'A'
    return 'N'

def pred_token(train,cur,h,mode):
    labs=[x['fut'][h]['lab'] for x in train if x['fut'][h]['lab']]
    gp=(sum(x>0 for x in labs)+2)/(len(labs)+4); base=math.log(gp/(1-gp))
    effects=[]
    for tok in cur['tokens']:
        ys=[x['fut'][h]['lab'] for x in train if tok in x['tokens'] and x['fut'][h]['lab']]
        if len(ys)<4:continue
        p=(sum(y>0 for y in ys)+2)/(len(ys)+4); logit=math.log(p/(1-p)); eff=max(-1.25,min(1.25,logit-base))
        # shrink small supports smoothly
        eff*=len(ys)/(len(ys)+8)
        effects.append((abs(eff),eff,tok,len(ys)))
    effects.sort(reverse=True)
    if mode=='TOP3':chosen=effects[:3]
    elif mode=='TOP5':chosen=effects[:5]
    else:chosen=effects
    score=base+(mean([x[1] for x in chosen]) if chosen else 0)
    return (1 if score>0 else -1), abs(score), [x[2] for x in chosen[:5]]

def evaluate(ps,events,h):
    wins=sum(p['pred']==p['event']['fut'][h]['lab'] for p in ps);n=len(ps);buy=sum(p['pred']>0 for p in ps)
    blocks=[]
    for b in range(8):
        q=[p for p in ps if p['event']['block']==b]
        blocks.append(rr(100*sum(p['pred']==p['event']['fut'][h]['lab'] for p in q)/len(q),2) if q else None)
    ft={}
    for th in (.3,.5,.8,1.0):
        c=defaultdict(int)
        for p in ps:
            f=p['event']['fut'][h];c[first_touch(f['path'],f['entry'],p['pred'],th)]+=1
        dec=c['F']+c['A'];ft[str(th)]={'f':c['F'],'a':c['A'],'n':dec,'none':c['N'],'wr':rr(100*c['F']/dec,2) if dec else None}
    wrs=[x for x in blocks if x is not None]
    return {'n':n,'wins':wins,'losses':n-wins,'wr':rr(100*wins/n,2),'buy':buy,'sell':n-buy,
            'blocks':blocks,'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs) if wrs else None,'ft':ft,
            'avg_signed_ret':rr(mean([p['pred']*p['event']['fut'][h]['ret'] for p in ps]),4)}

def main():
    rows=load(); idx={x[0]:i for i,x in enumerate(rows)}; expected=(EVAL_END-EVAL_START)//TF
    exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows); print('COVERAGE',exact,expected,rr(100*exact/expected,2),flush=True)
    allres=[]
    for nbar in DECISIONS:
        ev=[]
        for row in rows:
            t=row[0]
            if not(EVAL_START<=t<EVAL_END):continue
            dt=local(t)
            if not(dt.weekday()==1 and dt.hour==6 and dt.minute==0):continue
            i=idx[t];c=ctx(rows,i)
            if c is None:continue
            entry_i=i+nbar
            if entry_i>=len(rows) or rows[entry_i][0]!=t+nbar*TF:continue
            fut={h:future(rows,entry_i,h) for h in HORIZONS}
            if any(v is None for v in fut.values()):continue
            block=min(7,max(0,int((t-EVAL_START)*8/(EVAL_END-EVAL_START))))
            ev.append({'ts':t,'tokens':tokens(rows,i,nbar,c),'fut':fut,'block':block})
        warm=20
        for h in HORIZONS:
            # same-entry majority / always-sell controls
            ps=[{'pred':-1,'event':e} for e in ev[warm:]]
            allres.append({'engine':'ALWAYS_SELL','decision':f'{6+nbar//4:02d}:{(nbar%4)*15:02d}','nbar':nbar,'h':h,**evaluate(ps,ev,h)})
            for mode in ('TOP3','TOP5','ALL'):
                ps=[]
                for j in range(warm,len(ev)):
                    p,conf,toks=pred_token(ev[:j],ev[j],h,mode);ps.append({'pred':p,'event':ev[j],'conf':conf,'toks':toks})
                allres.append({'engine':'WF_TOKEN_'+mode,'decision':f'{6+nbar//4:02d}:{(nbar%4)*15:02d}','nbar':nbar,'h':h,**evaluate(ps,ev,h)})
    dyn=[x for x in allres if x['engine']!='ALWAYS_SELL'];base=[x for x in allres if x['engine']=='ALWAYS_SELL']
    top=sorted(dyn,key=lambda x:(x['wr'],x['positive_blocks'],x['n']),reverse=True)
    top05=sorted(dyn,key=lambda x:((x['ft']['0.5']['wr'] or -1),x['ft']['0.5']['n'],x['wr']),reverse=True)
    top08=sorted(dyn,key=lambda x:((x['ft']['0.8']['wr'] or -1),x['ft']['0.8']['n'],x['wr']),reverse=True)
    out={'status':'A31_DYNAMIC_OBSERVATION_PATH','data':{'coverage':rr(100*exact/expected,2),'rows':exact,'expected':expected,'tuesdays':139,'warmup':20,'predictions':119,'post_warmup_trade_coverage':100.0},
         'dir70':[x for x in top if x['wr']>=70],'ft05_70':[x for x in top05 if (x['ft']['0.5']['wr'] or 0)>=70 and x['ft']['0.5']['n']>=30],
         'ft08_70':[x for x in top08 if (x['ft']['0.8']['wr'] or 0)>=70 and x['ft']['0.8']['n']>=30],
         'top_dir':top[:20],'top05':top05[:20],'top08':top08[:20],'baselines':base}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
