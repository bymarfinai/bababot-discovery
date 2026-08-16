"""Offline BTC Temporal A3 walk-forward dynamic direction research.

Downloads official Binance USD-M Futures monthly BTCUSDT 15m archives and tests
high-coverage Tuesday 06:30 WIB BUY/SELL classification. No Railway/live state.
"""
import csv, io, json, math, statistics, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone, timedelta

TF_MS=15*60*1000
START_MS=int(datetime(2023,12,2,tzinfo=timezone.utc).timestamp()*1000)
END_MS=int(datetime(2026,7,30,tzinfo=timezone.utc).timestamp()*1000)
HORIZONS=(30,60,120,240)
H_BARS={h:h//15 for h in HORIZONS}
TZ=timezone(timedelta(hours=7))


def mean(xs): return statistics.mean(xs) if xs else 0.0
def median(xs): return statistics.median(xs) if xs else None
def r(x,n=4): return round(float(x),n) if x is not None else None
def sgn(x): return 1 if x>0 else -1 if x<0 else 0


def months():
    y,m=2023,12
    while (y,m) <= (2026,7):
        yield y,m
        m+=1
        if m==13: y,m=y+1,1


def load_rows():
    out=[]
    for y,m in months():
        fn=f"BTCUSDT-15m-{y:04d}-{m:02d}.zip"
        url=f"https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/15m/{fn}"
        print("DOWNLOAD",fn,flush=True)
        with urllib.request.urlopen(url,timeout=60) as resp:
            data=resp.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name=z.namelist()[0]
            text=io.TextIOWrapper(z.open(name),encoding='utf-8')
            rd=csv.reader(text)
            for row in rd:
                if not row: continue
                try: ts=int(row[0])
                except: continue
                if ts>10**14: ts//=1000
                if ts<START_MS or ts>=END_MS: continue
                out.append((ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5])))
    out.sort(key=lambda x:x[0])
    ded={x[0]:x for x in out}
    rows=[ded[k] for k in sorted(ded)]
    return rows


def bf(row):
    o,h,l,c=row[1:5]; rng=max(0,h-l); body=abs(c-o)
    return {'o':o,'h':h,'l':l,'c':c,'rng':rng,'body_ratio':body/rng if rng else 0,
            'close_loc':(c-l)/rng if rng else .5,'bull':c>o,'bear':c<o}


def context(rows,idx):
    if idx<672:return None
    ts=rows[idx][0]; dt=datetime.fromtimestamp(ts/1000,tz=timezone.utc).astimezone(TZ)
    ds=dt.replace(hour=0,minute=0,second=0,microsecond=0)
    dsms=int(ds.astimezone(timezone.utc).timestamp()*1000)
    j=idx-1
    while j>=0 and rows[j][0]>=dsms:j-=1
    day=rows[j+1:idx]
    if not day:return None
    pre1=rows[idx-4:idx]; pre4=rows[idx-16:idx]; pre8=rows[idx-8:idx]
    entry=rows[idx][1]; daily_open=day[0][1]
    hod=max(x[2] for x in day); lod=min(x[3] for x in day); dr=max(1e-12,hod-lod)
    ranges=[x[2]-x[3] for x in pre8]
    return {'pre1_ret':100*(entry-pre1[0][1])/pre1[0][1],
            'pre4_ret':100*(entry-pre4[0][1])/pre4[0][1],
            'pre24_ret':100*(entry-rows[idx-96][1])/rows[idx-96][1],
            'pre7d_ret':100*(entry-rows[idx-672][1])/rows[idx-672][1],
            'day_pos':(entry-lod)/dr,'daily_open':daily_open,
            'dist_daily_open_pct':100*(entry-daily_open)/daily_open,
            'hod':hod,'lod':lod,'prevh_hi':max(x[2] for x in pre1),'prevh_lo':min(x[3] for x in pre1),
            'pre_rng_med':median(ranges) or 1e-12}


def occurrence(rows,idx,block):
    if idx+18>=len(rows):return None
    ts=rows[idx][0]
    if rows[idx+1][0]!=ts+TF_MS or rows[idx+2][0]!=ts+2*TF_MS:return None
    c=context(rows,idx)
    if c is None:return None
    b0,b1,er=rows[idx],rows[idx+1],rows[idx+2]; f0,f1=bf(b0),bf(b1)
    wo=b0[1]; oc=b1[4]; oh=max(b0[2],b1[2]); ol=min(b0[3],b1[3]); orng=oh-ol
    obs=100*(oc-wo)/wo
    seq=('U' if f0['bull'] else 'D' if f0['bear'] else 'F')+('U' if f1['bull'] else 'D' if f1['bear'] else 'F')
    pb='L' if c['day_pos']<1/3 else 'M' if c['day_pos']<2/3 else 'U'
    ha=oh>c['hod']; la=ol<c['lod']; phr=oh>c['prevh_hi']; plr=ol<c['prevh_lo']
    feats={'pre1_ret':c['pre1_ret'],'pre4_ret':c['pre4_ret'],'pre24_ret':c['pre24_ret'],'pre7d_ret':c['pre7d_ret'],
           'day_pos':c['day_pos'],'dist_daily_open_pct':c['dist_daily_open_pct'],'obs_ret':obs,
           'bar0_ret':100*(b0[4]-b0[1])/b0[1],'bar1_ret':100*(b1[4]-b1[1])/b1[1],
           'bar0_body':f0['body_ratio'],'bar1_body':f1['body_ratio'],'bar0_close_loc':f0['close_loc'],'bar1_close_loc':f1['close_loc'],
           'obs_range_ratio':orng/max(1e-12,c['pre_rng_med']),'close_vs_prevh_mid_pct':100*(oc-(c['prevh_hi']+c['prevh_lo'])/2)/wo,
           'hod_attack':float(ha),'lod_attack':float(la),'hod_reclaim_down':float(ha and oc<c['hod']),'lod_reclaim_up':float(la and oc>c['lod']),
           'prevh_high_attack':float(phr),'prevh_low_attack':float(plr),'close_above_prevh':float(oc>c['prevh_hi']),'close_below_prevl':float(oc<c['prevh_lo'])}
    states={'full':(sgn(c['pre24_ret']),pb,sgn(obs),seq,int(ha and oc<c['hod']),int(la and oc>c['lod']),int(oc>c['prevh_hi']),int(oc<c['prevh_lo'])),
            'medium':(sgn(c['pre24_ret']),pb,sgn(obs),seq),'coarse':(pb,sgn(obs),seq),'sequence':(sgn(c['pre24_ret']),sgn(obs),seq),'minimal':(pb,sgn(obs))}
    entry=er[1]; labels={}; rets={}; paths={}
    for h in HORIZONS:
        hb=H_BARS[h]; p=rows[idx+2:idx+2+hb]
        if len(p)!=hb or any(p[k][0]!=er[0]+k*TF_MS for k in range(hb)):return None
        rt=100*(p[-1][4]-entry)/entry; labels[h]=sgn(rt); rets[h]=rt; paths[h]=p
    return {'ts':ts,'block':block,'entry':entry,'features':feats,'states':states,'labels':labels,'rets':rets,'paths':paths}

SETS={'OBS_ONLY':['obs_ret','bar0_ret','bar1_ret','bar0_body','bar1_body','bar0_close_loc','bar1_close_loc','obs_range_ratio'],
      'CONTEXT_SEQ':['pre1_ret','pre4_ret','pre24_ret','day_pos','dist_daily_open_pct','obs_ret','bar0_ret','bar1_ret','obs_range_ratio','close_vs_prevh_mid_pct'],
      'FULL_PATH':['pre1_ret','pre4_ret','pre24_ret','pre7d_ret','day_pos','dist_daily_open_pct','obs_ret','bar0_ret','bar1_ret','bar0_body','bar1_body','bar0_close_loc','bar1_close_loc','obs_range_ratio','close_vs_prevh_mid_pct','hod_attack','lod_attack','hod_reclaim_down','lod_reclaim_up','prevh_high_attack','prevh_low_attack','close_above_prevh','close_below_prevl']}


def knn(train,cur,h,names,k):
    stats={}
    for nm in names:
        vs=[x['features'][nm] for x in train]; mu=mean(vs); sd=math.sqrt(mean([(v-mu)**2 for v in vs])); stats[nm]=(mu,sd)
    rr=[]
    for old in train:
        lab=old['labels'][h]
        if lab==0:continue
        ss=0; used=0
        for nm in names:
            mu,sd=stats[nm]
            if sd<1e-9:continue
            d=(cur['features'][nm]-old['features'][nm])/sd; ss+=d*d; used+=1
        dist=math.sqrt(ss/used) if used else 0
        rr.append((dist,lab))
    rr.sort(); nb=rr[:min(k,len(rr))]; score=den=0
    for dist,lab in nb:
        w=1/(.25+dist);score+=w*lab;den+=w
    return (1 if score>0 else -1), abs(score)/den if den else 0


def statepred(train,cur,h,mins):
    for level in ('full','medium','coarse','sequence','minimal'):
        ms=[x for x in train if x['states'][level]==cur['states'][level] and x['labels'][h]!=0]
        if len(ms)>=mins:
            sc=sum(x['labels'][h] for x in ms);return (1 if sc>0 else -1),abs(sc)/len(ms)
    labs=[x['labels'][h] for x in train if x['labels'][h]!=0];sc=sum(labs)
    return (1 if sc>0 else -1),abs(sc)/len(labs)


def ft(path,entry,d,th):
    fav=entry*(1+d*th/100);adv=entry*(1-d*th/100)
    for x in path:
        hi,lo=x[2],x[3]
        hf,ha=(hi>=fav,lo<=adv) if d>0 else (lo<=fav,hi>=adv)
        if hf and ha:return 'AMB'
        if hf:return 'F'
        if ha:return 'A'
    return 'N'


def evaluate(preds,occs,h):
    mp={x['ts']:x for x in occs}; rs=[]
    for p in preds:
        e=mp[p['ts']];act=e['labels'][h];rs.append((e,p['pred'],act,p['pred']==act if act else False,p['pred']*e['rets'][h],p.get('conf',0)))
    resolved=[x for x in rs if x[2]!=0];wins=sum(x[3] for x in resolved)
    blocks=[]
    for b in range(8):
        xs=[x for x in resolved if x[0]['block']==b];bw=sum(x[3] for x in xs);blocks.append(r(100*bw/len(xs),2) if xs else None)
    first={}
    for th in (.3,.5,.8,1.0):
        c=defaultdict(int)
        for e,p,_,_,_,_ in rs:c[ft(e['paths'][h],e['entry'],p,th)]+=1
        dec=c['F']+c['A'];first[str(th)]={'fav':c['F'],'adv':c['A'],'none':c['N'],'amb':c['AMB'],'n':dec,'wr':r(100*c['F']/dec,2) if dec else None}
    wrs=[x for x in blocks if x is not None]
    return {'n':len(rs),'wins':wins,'losses':len(resolved)-wins,'wr':r(100*wins/len(resolved),2),'buy':sum(p>0 for _,p,*_ in rs),'sell':sum(p<0 for _,p,*_ in rs),
            'avg_ret':r(mean([x[4] for x in rs]),4),'med_ret':r(median([x[4] for x in rs]),4),'blocks':blocks,'positive_blocks':sum(x>50 for x in wrs),'blocks60':sum(x>=60 for x in wrs),'min_block':min(wrs) if wrs else None,'ft':first}


def main():
    rows=load_rows(); expected=(END_MS-START_MS)//TF_MS
    print('COVERAGE',len(rows),expected,r(100*len(rows)/expected,2),flush=True)
    occs=[];span=END_MS-START_MS
    for i,row in enumerate(rows):
        dt=datetime.fromtimestamp(row[0]/1000,tz=timezone.utc).astimezone(TZ)
        if dt.weekday()==1 and dt.hour==6 and dt.minute==0:
            block=min(7,max(0,int((row[0]-START_MS)*8/span)))
            o=occurrence(rows,i,block)
            if o:occs.append(o)
    warm=20; ev=occs[warm:]; engines=[]
    for h in HORIZONS:
        ctrls={'BASE_ALWAYS_SELL':lambda e:-1,'OBS_MOMENTUM':lambda e:1 if e['features']['obs_ret']>=0 else -1,'OBS_REVERSAL':lambda e:-1 if e['features']['obs_ret']>=0 else 1}
        for nm,fn in ctrls.items():
            ps=[{'ts':e['ts'],'pred':fn(e),'conf':0} for e in ev];engines.append({'engine':nm,'h':h,**evaluate(ps,occs,h)})
        for mins in (3,5,8):
            ps=[]
            for i in range(warm,len(occs)):
                p,c=statepred(occs[:i],occs[i],h,mins);ps.append({'ts':occs[i]['ts'],'pred':p,'conf':c})
            engines.append({'engine':f'WF_STATE_MIN{mins}','h':h,**evaluate(ps,occs,h)})
        for sn,names in SETS.items():
            for k in (5,9,15,21):
                ps=[]
                for i in range(warm,len(occs)):
                    p,c=knn(occs[:i],occs[i],h,names,k);ps.append({'ts':occs[i]['ts'],'pred':p,'conf':c})
                engines.append({'engine':f'WF_KNN_{sn}_K{k}','h':h,**evaluate(ps,occs,h)})
    top=sorted(engines,key=lambda x:(x['wr'],x['ft']['0.5']['wr'] or -1),reverse=True)
    top05=sorted(engines,key=lambda x:((x['ft']['0.5']['wr'] or -1),x['ft']['0.5']['n'],x['wr']),reverse=True)
    top08=sorted(engines,key=lambda x:((x['ft']['0.8']['wr'] or -1),x['ft']['0.8']['n'],x['wr']),reverse=True)
    out={'status':'A3_OFFLINE_BINANCE_WALKFORWARD','data':{'rows':len(rows),'expected':expected,'coverage':r(100*len(rows)/expected,2),'tuesdays':len(occs),'warmup':warm,'predictions':len(ev),'post_warmup_trade_coverage':100.0},
         'baseline':[x for x in engines if x['engine']=='BASE_ALWAYS_SELL'],'dir70':[x for x in top if x['wr']>=70],'ft05_70':[x for x in top05 if (x['ft']['0.5']['wr'] or 0)>=70 and x['ft']['0.5']['n']>=30],'ft08_70':[x for x in top08 if (x['ft']['0.8']['wr'] or 0)>=70 and x['ft']['0.8']['n']>=30],
         'top_dir':top[:15],'top05':top05[:15],'top08':top08[:15]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
