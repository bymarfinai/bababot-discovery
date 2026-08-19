#!/usr/bin/env python3
"""C5: BTC Friday 15m candle + causal Binance futures derivatives metrics."""
from __future__ import annotations
import csv,io,json,math,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from sklearn.tree import DecisionTreeClassifier

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_15m_Derivatives_C5_Result.md';OUT_JSON=ROOT/'BTC_Friday_15m_Derivatives_C5_Result.json';OUT_ROWS=ROOT/'BTC_Friday_15m_Derivatives_C5_Rows.csv'
START=pd.Timestamp('2023-12-02T00:00:00Z');END=pd.Timestamp('2026-07-30T00:00:00Z');BASE='https://data.binance.vision/data/futures/um'
TP=SL=.013;HOLD=24;COST=.0015;NOTIONAL=500.;SEED=20260819
FEATURES=['signal_ret','body_ratio','upper_ratio','lower_ratio','close_pos','range_open','prior1h_ret','top_vs_global','top_pos_chg15','global_chg15','taker_log','oi_chg15','oi_chg60']


def fetch_kline_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-c5/1.0'})
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<5:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4])])
                except Exception:continue
    return out

def load15():
    jobs=[];cur=pd.Timestamp(START.year,START.month,1,tz='UTC');em=pd.Timestamp(END.year,END.month,1,tz='UTC')
    while cur<em:
        ym=cur.strftime('%Y-%m');jobs.append(f'{BASE}/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip');cur+=pd.offsets.MonthBegin(1)
    d=em
    while d<END.normalize():
        ds=d.strftime('%Y-%m-%d');jobs.append(f'{BASE}/daily/klines/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip');d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        fs=[ex.submit(fetch_kline_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close']);x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True)
    x=x.dropna().drop_duplicates('ts').sort_values('ts');x=x[(x.ts>=START-pd.Timedelta(days=1))&(x.ts<END)].reset_index(drop=True)
    if len(x)<90000:raise RuntimeError(f'insufficient 15m rows {len(x)}')
    return x

def fetch_metric_day(day):
    ds=day.strftime('%Y-%m-%d');url=f'{BASE}/daily/metrics/BTCUSDT/BTCUSDT-metrics-{ds}.zip'
    try:
        r=requests.get(url,timeout=30,headers={'User-Agent':'bababot-c5/1.0'})
        if r.status_code==404:return None
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
            with zf.open(name) as fh:df=pd.read_csv(fh)
        df.columns=[str(c).strip().lower() for c in df.columns]
        aliases={'ts':['create_time','timestamp','time'],'oi':['sum_open_interest_value'],'top':['sum_toptrader_long_short_ratio'],'global':['count_long_short_ratio'],'taker':['sum_taker_long_short_vol_ratio']};cols={}
        for k,opts in aliases.items():
            for o in opts:
                if o in df.columns:cols[k]=o;break
        if any(k not in cols for k in aliases):return None
        raw=df[cols['ts']]
        if pd.api.types.is_numeric_dtype(raw):
            v=pd.to_numeric(raw,errors='coerce');unit='us' if v.dropna().median()>1e14 else 'ms';ts=pd.to_datetime(v,unit=unit,utc=True,errors='coerce')
        else:ts=pd.to_datetime(raw,utc=True,errors='coerce')
        out=pd.DataFrame({'ts':ts,'oi':pd.to_numeric(df[cols['oi']],errors='coerce'),'top':pd.to_numeric(df[cols['top']],errors='coerce'),'global':pd.to_numeric(df[cols['global']],errors='coerce'),'taker':pd.to_numeric(df[cols['taker']],errors='coerce')})
        return out.dropna().replace([np.inf,-np.inf],np.nan).dropna()
    except Exception:return None

def load_metrics():
    days=pd.date_range((START-pd.Timedelta(days=2)).normalize(),END-pd.Timedelta(days=1),freq='D',tz='UTC');frames=[]
    with ThreadPoolExecutor(max_workers=48) as ex:
        fs=[ex.submit(fetch_metric_day,d) for d in days]
        done=0
        for f in as_completed(fs):
            z=f.result();done+=1
            if z is not None and len(z):frames.append(z)
            if done%250==0:print(f'metrics {done}/{len(fs)}')
    if not frames:raise RuntimeError('no metrics')
    m=pd.concat(frames,ignore_index=True).drop_duplicates('ts').sort_values('ts').set_index('ts',drop=False)
    m=m[(m.index>=START-pd.Timedelta(days=2))&(m.index<END)]
    if len(m)<200000:raise RuntimeError(f'insufficient metrics rows {len(m)}')
    return m

def geom_features(x):
    O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);rg=np.maximum(H-L,1e-12);x['signal_ret']=C/O-1.;x['body_ratio']=np.abs(C-O)/rg;x['upper_ratio']=(H-np.maximum(O,C))/rg;x['lower_ratio']=(np.minimum(O,C)-L)/rg;x['close_pos']=(C-L)/rg;x['range_open']=(H-L)/O;prior=np.full(len(x),np.nan);prior[4:]=O[4:]/C[:-4]-1.;x['prior1h_ret']=prior;return x

def metric_at(m,entry):
    idx=m.index;i=int(idx.searchsorted(entry,side='left'))-1
    if i<0:return None
    cur=m.iloc[i];cts=cur.ts
    if entry-cts< pd.Timedelta(0) or entry-cts>pd.Timedelta(minutes=15):return None
    j15=int(idx.searchsorted(cts-pd.Timedelta(minutes=15),side='right'))-1;j60=int(idx.searchsorted(cts-pd.Timedelta(minutes=60),side='right'))-1
    if j15<0 or j60<0:return None
    p15=m.iloc[j15];p60=m.iloc[j60]
    vals=[cur.top,cur['global'],cur.taker,cur.oi,p15.top,p15['global'],p15.oi,p60.oi]
    vals=[float(v) for v in vals]
    if any((not math.isfinite(v) or v<=0) for v in vals):return None
    return {'top_vs_global':math.log(float(cur.top))-math.log(float(cur['global'])),'top_pos_chg15':math.log(float(cur.top))-math.log(float(p15.top)),'global_chg15':math.log(float(cur['global']))-math.log(float(p15['global'])),'taker_log':math.log(float(cur.taker)),'oi_chg15':math.log(float(cur.oi))-math.log(float(p15.oi)),'oi_chg60':math.log(float(cur.oi))-math.log(float(p60.oi))}
def resolve(ep,hs,ls,fc,side):
    if side>0:th=np.flatnonzero(hs>=ep*(1+TP));sh=np.flatnonzero(ls<=ep*(1-SL))
    else:th=np.flatnonzero(ls<=ep*(1-TP));sh=np.flatnonzero(hs>=ep*(1+SL))
    ti=int(th[0]) if th.size else 10**9;si=int(sh[0]) if sh.size else 10**9
    if si<=ti:raw=-SL;reason='SL'
    elif ti<10**9:raw=TP;reason='TP'
    else:raw=side*(fc/ep-1);reason='TIME'
    net=raw-COST;return net*NOTIONAL,int(net>0),reason

def build(x,m):
    x=geom_features(x);O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);wib=x.ts+pd.Timedelta(hours=7);rows=[];integrity=0
    idx=np.flatnonzero((wib.dt.weekday.to_numpy()==4)&(C!=O));idx=idx[(idx>=4)&(idx+HOLD<len(x)-1)]
    for i in idx:
        entry_t=x.ts.iloc[i]+pd.Timedelta(minutes=15);mf=metric_at(m,entry_t)
        if mf is None:continue
        if not (m.index[m.index.searchsorted(entry_t,side='left')-1] < entry_t):integrity+=1
        side=1 if C[i]>O[i] else -1;ep=O[i+1];hs=H[i+1:i+1+HOLD];ls=L[i+1:i+1+HOLD];fc=C[i+HOLD];cont=resolve(ep,hs,ls,fc,side);rev=resolve(ep,hs,ls,fc,-side)
        base={f:float(x.iloc[i][f]) for f in FEATURES[:7]};rows.append({'signal_ts':str(x.ts.iloc[i]),'friday_wib':str(wib.iloc[i].date()),'entry_ts':str(x.ts.iloc[i+1]),**base,**mf,'cont_pnl':cont[0],'cont_win':cont[1],'cont_reason':cont[2],'rev_pnl':rev[0],'rev_win':rev[1],'rev_reason':rev[2]})
    return pd.DataFrame(rows),integrity
def pf(a):
    gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0);return gp/gl if gl>0 else (999. if gp>0 else None)
def stats(z,col):
    a=z[col].astype(float).tolist() if len(z) else []
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    w=sum(v>0 for v in a);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}
def path_to_leaf(clf,leaf):
    tr=clf.tree_;path=[]
    def rec(n,conds):
        if n==leaf:path.extend(conds);return True
        if tr.children_left[n]==tr.children_right[n]:return False
        f=FEATURES[tr.feature[n]];v=float(tr.threshold[n]);return rec(tr.children_left[n],conds+[(f,'<=',v)]) or rec(tr.children_right[n],conds+[(f,'>',v)])
    rec(0,[]);return path
def text(p):return ' AND '.join(f'{a} {b} {c:.8g}' for a,b,c in p)
def blocks(df,mode,leaf):
    dates=sorted(df.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):out[f'B{i+1}']=stats(df[df.friday_wib.isin(set(ch))&(df[f'{mode}_leaf']==leaf)],f'{mode}_pnl')
    return out

def main():
    x=load15();m=load_metrics();df,viol=build(x,m)
    if df.empty:raise RuntimeError('no aligned Friday rows')
    dates=sorted(df.friday_wib.unique());cut=int(math.floor(.70*len(dates)));dd=set(dates[:cut]);df['period']=np.where(df.friday_wib.isin(dd),'discovery','validation');disc0=df[df.period=='discovery'].copy();med={f:float(disc0[f].median()) for f in FEATURES};X=df[FEATURES].copy()
    for f in FEATURES:X[f]=pd.to_numeric(X[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med[f])
    cand=[];reps={};baseline={}
    for mode in ('cont','rev'):
        clf=DecisionTreeClassifier(criterion='gini',max_depth=2,min_samples_leaf=80,random_state=SEED);clf.fit(X.loc[disc0.index],disc0[f'{mode}_win'].astype(int));df[f'{mode}_leaf']=clf.apply(X);disc=df[df.period=='discovery'];val=df[df.period=='validation'];baseline[mode]={'discovery':stats(disc,f'{mode}_pnl'),'validation':stats(val,f'{mode}_pnl'),'full':stats(df,f'{mode}_pnl')};rr=[]
        for leaf in sorted(set(disc[f'{mode}_leaf'])):
            z=disc[disc[f'{mode}_leaf']==leaf];s=stats(z,f'{mode}_pnl');pred=int(np.argmax(clf.tree_.value[int(leaf)][0]));p=path_to_leaf(clf,int(leaf));q={'mode':mode,'leaf':int(leaf),'predicted_class':pred,'rule':text(p),'path':p,**s};rr.append(q)
            if pred==1 and s['n']>=80 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['pf'] is not None and s['pf']>1:cand.append(q)
        reps[mode]=rr
    cand.sort(key=lambda q:(-q['wr'],-q['n'],-q['pf'],q['mode'],q['leaf']));out={'protocol':'C5','friday_dates':len(dates),'aligned_rows':len(df),'discovery_dates':len(dd),'validation_dates':len(dates)-len(dd),'metrics_rows':len(m),'features':FEATURES,'baseline':baseline,'discovery_leaves':reps,'eligible_80_leaves':len(cand),'integrity_violations':viol}
    if not cand:out.update({'selected':None,'verdict':'REJECT_C5_DERIVATIVES_IDENTIFIER','reason':'No positive discovery derivatives leaf achieved N>=80 and WR>=80%.'})
    else:
        q=cand[0];mo=q['mode'];leaf=q['leaf'];disc=df[df.period=='discovery'];val=df[df.period=='validation'];sd=stats(disc[disc[f'{mo}_leaf']==leaf],f'{mo}_pnl');sv=stats(val[val[f'{mo}_leaf']==leaf],f'{mo}_pnl');sf=stats(df[df[f'{mo}_leaf']==leaf],f'{mo}_pnl');bl=blocks(df,mo,leaf);pos=sum(v['n']>=15 and v['pnl']>0 for v in bl.values());ok=sd['n']>=80 and sd['wr']>=.80 and sv['n']>=30 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=120 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and sv['wr']>baseline[mo]['validation']['wr'] and pos>=3 and viol==0
        out['selected']={'mode':mo,'leaf':leaf,'rule':q['rule'],'path':q['path'],'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos};out['verdict']='BTC_FRIDAY_C5_DERIVATIVES_80_CANDIDATE' if ok else 'REJECT_C5_DERIVATIVES_IDENTIFIER'
    df.to_csv(OUT_ROWS,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');F=lambda v,d=2:'-' if v is None else f'{v:.{d}f}';md=['# BTC Friday C5 — 15m Candle + Derivatives-State Result','',f"Friday dates **{len(dates)}**; aligned rows **{len(df)}**; metrics rows **{len(m)}**",f"Integrity violations **{viol}**; eligible discovery 80% leaves **{len(cand)}**",'']
    for mode in ('cont','rev'):
        md += [f'## {mode.upper()} discovery leaves','', '| Leaf | Pred | N | Wins | WR | Rule |','|---:|---:|---:|---:|---:|---|']
        for q in reps[mode]:md.append(f"| {q['leaf']} | {q['predicted_class']} | {q['n']} | {q['wins']} | {F(100*q['wr'])}% | `{q['rule']}` |")
        md.append('')
    if out.get('selected') is None:md += ['## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        s=out['selected'];md += ['## Selected derivatives fingerprint','',f"Mode **{s['mode'].upper()}**",f"`{s['rule']}`",'', '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,z in [('Discovery',s['discovery']),('Validation',s['validation']),('Full',s['full'])]:md.append(f"| {name} | {z['n']} | {z['wins']} | {F(100*z['wr'])}% | ${F(z['pnl'])} | ${F(z['exp'],3)} | {F(z['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','All metrics are latest strictly-before-entry observations. No post-result derivatives/tree rescue.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
