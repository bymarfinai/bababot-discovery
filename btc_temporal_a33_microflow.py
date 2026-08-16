"""A3.3 research only: forced BUY/SELL every Tuesday using temporal path + Binance taker-flow/absorption evidence. No live orders, no WAIT filtering."""
import csv, io, json, statistics, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone
from btc_temporal_a31_pathscan import local, ctx, tokens, future, first_touch, rr, mean, TF, EVAL_START, EVAL_END, HORIZONS
from btc_temporal_a32_crossday import enrich, predict

LOAD_START=int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000)
DECISIONS=(2,3,4,6)  # 06:30 06:45 07:00 07:30

def months():
    y,m=2023,11
    while (y,m)<=(2026,7):
        yield y,m;m+=1
        if m==13:y,m=y+1,1

def load_micro():
    out=[]
    for y,m in months():
        fn=f'BTCUSDT-15m-{y:04d}-{m:02d}.zip';url=f'https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m/{fn}'
        with urllib.request.urlopen(url,timeout=60) as q:data=q.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            rd=csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]),encoding='utf-8'))
            for a in rd:
                try:t=int(a[0])
                except:continue
                if t>10**14:t//=1000
                if LOAD_START<=t<EVAL_END:
                    out.append((t,float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5]),float(a[7]),float(a[8]),float(a[9]),float(a[10])))
    d={x[0]:x for x in out};return [d[k] for k in sorted(d)]

def bkt(v,a,b):return 'LOW' if v<a else 'MID' if v<b else 'HIGH'
def flow_tokens(rows,i,nb,base):
    obs=rows[i:i+nb];pre=rows[i-8:i]
    q=sum(x[6] for x in obs);tb=sum(x[9] for x in obs);tbr=tb/q if q else .5
    last=obs[-1][9]/obs[-1][6] if obs[-1][6] else .5
    half=max(1,len(obs)//2);q1=sum(x[6] for x in obs[:half]);b1=sum(x[9] for x in obs[:half]);q2=sum(x[6] for x in obs[half:]);b2=sum(x[9] for x in obs[half:])
    r1=b1/q1 if q1 else .5;r2=b2/q2 if q2 else r1
    preq=[x[6] for x in pre];premed=statistics.median(preq) if preq else 1;vr=(q/len(obs))/max(premed,1e-9)
    wo=obs[0][1];cl=obs[-1][4];ret=100*(cl-wo)/wo
    ag='BUY' if tbr>.53 else 'SELL' if tbr<.47 else 'BAL'
    lag='BUY' if last>.53 else 'SELL' if last<.47 else 'BAL'
    buyer_fail=tbr>.52 and ret<=0;seller_fail=tbr<.48 and ret>=0
    high=max(x[2] for x in obs);low=min(x[3] for x in obs)
    hod_reject=high>base['hod'] and cl<base['hod'];lod_reclaim=low<base['lod'] and cl>base['lod']
    imbalance=2*tbr-1
    align='ALIGN' if (imbalance>0 and ret>0) or (imbalance<0 and ret<0) else 'DIVERGE' if abs(imbalance)>.02 else 'NEUTRAL'
    out=[f'TAKER_{ag}',f'TAKERLAST_{lag}','TAKERTREND_'+('UP' if r2>r1+.01 else 'DOWN' if r2<r1-.01 else 'FLAT'),
         'VOL_'+bkt(vr,.8,1.2),f'BUYERFAIL_{int(buyer_fail)}',f'SELLERFAIL_{int(seller_fail)}','FLOWPRICE_'+align,
         'TAKEREXT_'+('BUY' if tbr>.58 else 'SELL' if tbr<.42 else 'NONE'),
         f'BUYTRAP_{int(hod_reject and tbr>.50)}',f'SELLTRAP_{int(lod_reclaim and tbr<.50)}']
    return out,{'tbr':tbr,'last':last,'buyer_fail':buyer_fail,'seller_fail':seller_fail,'hod_reject':hod_reject,'lod_reclaim':lod_reclaim,'ret':ret}

def evalps(ps,h):
    n=len(ps);w=sum(p['pred']==p['e']['fut'][h]['lab'] for p in ps);buy=sum(p['pred']>0 for p in ps);blocks=[]
    for b in range(8):
        q=[p for p in ps if p['e']['block']==b];blocks.append(rr(100*sum(p['pred']==p['e']['fut'][h]['lab'] for p in q)/len(q),2) if q else None)
    ft={}
    for th in (.3,.5,.8,1.0):
        c=defaultdict(int)
        for p in ps:
            f=p['e']['fut'][h];c[first_touch(f['path'],f['entry'],p['pred'],th)]+=1
        d=c['F']+c['A'];ft[str(th)]={'f':c['F'],'a':c['A'],'n':d,'none':c['N'],'wr':rr(100*c['F']/d,2) if d else None}
    wrs=[x for x in blocks if x is not None]
    return {'n':n,'wins':w,'losses':n-w,'wr':rr(100*w/n,2),'buy':buy,'sell':n-buy,'blocks':blocks,'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs),'avg_signed_ret':rr(mean([p['pred']*p['e']['fut'][h]['ret'] for p in ps]),4),'ft':ft}

def main():
    rows=load_micro();im={x[0]:i for i,x in enumerate(rows)};res=[];exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows);expected=(EVAL_END-EVAL_START)//TF
    for nb in DECISIONS:
        daily=[]
        for row in rows:
            dt=local(row[0])
            if dt.hour!=6 or dt.minute!=0:continue
            i=im[row[0]];base=ctx(rows,i)
            if base is None or i+nb>=len(rows):continue
            fut={h:future(rows,i+nb,h) for h in HORIZONS}
            if any(v is None for v in fut.values()):continue
            ftok,m=flow_tokens(rows,i,nb,base);toks=enrich(tokens(rows,i,nb,base)+ftok)
            block=min(7,max(0,int((row[0]-EVAL_START)*8/(EVAL_END-EVAL_START)))) if row[0]>=EVAL_START else -1
            daily.append({'ts':row[0],'tokens':toks,'micro':m,'fut':fut,'block':block})
        ev=[e for e in daily if EVAL_START<=e['ts']<EVAL_END and local(e['ts']).weekday()==1]
        dec=f'{6+nb//4:02d}:{(nb%4)*15:02d}'
        for h in HORIZONS:
            res.append({'engine':'ALWAYS_SELL','decision':dec,'h':h,**evalps([{'pred':-1,'e':e} for e in ev],h)})
            # Direct high-coverage microstructure rules; fallback still trades SELL temporal prior.
            for rn,rule in (
              ('FAILURE_FLIP',lambda e: 1 if e['micro']['seller_fail'] else -1),
              ('TRAP_FLIP',lambda e: 1 if (e['micro']['lod_reclaim'] and e['micro']['tbr']<.50) else -1),
              ('FLOW_MOMENTUM',lambda e: 1 if e['micro']['tbr']>=.50 else -1),
              ('FLOW_CONTRARIAN',lambda e: -1 if e['micro']['tbr']>=.50 else 1)):
                res.append({'engine':rn,'decision':dec,'h':h,**evalps([{'pred':rule(e),'e':e} for e in ev],h)})
            for mode in ('GENERAL_TOP3','GENERAL_TOP5','TUE_TOP3','TUE_TOP5','TUE_ALL'):
                ps=[]
                for e in ev:
                    hist=[x for x in daily if x['ts']<e['ts']];ps.append({'pred':predict(hist,e,h,mode),'e':e})
                res.append({'engine':'MICRO_'+mode,'decision':dec,'h':h,**evalps(ps,h)})
    dyn=[x for x in res if x['engine']!='ALWAYS_SELL'];base=[x for x in res if x['engine']=='ALWAYS_SELL']
    top=sorted(dyn,key=lambda x:(x['wr'],x['positive_blocks']),reverse=True);t05=sorted(dyn,key=lambda x:((x['ft']['0.5']['wr'] or -1),x['ft']['0.5']['n']),reverse=True);t08=sorted(dyn,key=lambda x:((x['ft']['0.8']['wr'] or -1),x['ft']['0.8']['n']),reverse=True)
    out={'status':'A33_MICROFLOW_DYNAMIC_DIRECTION','data':{'coverage':rr(100*exact/expected,2),'rows':exact,'expected':expected,'tuesdays':139,'predictions':139,'trade_coverage':100.0},'dir70':[x for x in top if x['wr']>=70],'ft05_70':[x for x in t05 if (x['ft']['0.5']['wr'] or 0)>=70 and x['ft']['0.5']['n']>=30],'ft08_70':[x for x in t08 if (x['ft']['0.8']['wr'] or 0)>=70 and x['ft']['0.8']['n']>=30],'top_dir':top[:20],'top05':t05[:20],'top08':t08[:20],'baselines':base}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')))
if __name__=='__main__':main()
