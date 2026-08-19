#!/usr/bin/env python3
"""C4: all Friday-WIB BTCUSDT 15m candle + taker-flow shallow identifier."""
from __future__ import annotations
import csv,io,json,math,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from sklearn.tree import DecisionTreeClassifier

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_15m_Candle_Taker_C4_Result.md';OUT_JSON=ROOT/'BTC_Friday_15m_Candle_Taker_C4_Result.json';OUT_ROWS=ROOT/'BTC_Friday_15m_Candle_Taker_C4_Rows.csv'
START=pd.Timestamp('2023-12-02T00:00:00Z');END=pd.Timestamp('2026-08-19T00:00:00Z');BASE='https://data.binance.vision/data/futures/um'
TP=SL=.013;HOLD=24;COST=.0015;NOTIONAL=500.;SEED=20260819
FEATURES=['signal_ret','body_ratio','upper_ratio','lower_ratio','close_pos','range_open','prior1h_ret','taker_imbalance','taker_delta_vs_prior3','rel_quote_volume_24h','rel_range_prior12']

def fetch_zip(url):
    r=requests.get(url,timeout=60,headers={'User-Agent':'bababot-c4/1.0'}); 
    if r.status_code==404:return []
    r.raise_for_status();out=[]
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name=[n for n in zf.namelist() if n.lower().endswith('.csv')][0]
        with zf.open(name) as fh:
            for row in csv.reader(io.TextIOWrapper(fh,encoding='utf-8')):
                if len(row)<11:continue
                try:ts=int(row[0])
                except Exception:continue
                if ts>100_000_000_000_000:ts//=1000
                try:out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[7]),float(row[10])])
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
        fs=[ex.submit(fetch_zip,u) for u in jobs]
        for f in as_completed(fs):rows.extend(f.result())
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','quote_volume','taker_buy_quote']);x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True)
    x=x.dropna().drop_duplicates('ts').sort_values('ts');x=x[(x.ts>=START-pd.Timedelta(days=2))&(x.ts<END)].reset_index(drop=True)
    if len(x)<90000:raise RuntimeError(f'insufficient 15m rows {len(x)}')
    return x

def prepare(x):
    O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);QV=x.quote_volume.to_numpy(float);TB=x.taker_buy_quote.to_numpy(float)
    rg=np.maximum(H-L,1e-12);x['signal_ret']=C/O-1.;x['body_ratio']=np.abs(C-O)/rg;x['upper_ratio']=(H-np.maximum(O,C))/rg;x['lower_ratio']=(np.minimum(O,C)-L)/rg;x['close_pos']=(C-L)/rg;x['range_open']=(H-L)/O
    imb=np.where(QV>0,2*TB/QV-1,np.nan);x['taker_imbalance']=imb;x['taker_delta_vs_prior3']=imb-pd.Series(imb).shift(1).rolling(3,min_periods=3).median().to_numpy()
    x['rel_quote_volume_24h']=QV/pd.Series(QV).shift(1).rolling(96,min_periods=96).median().to_numpy();x['rel_range_prior12']=x.range_open.to_numpy()/pd.Series(x.range_open.to_numpy()).shift(1).rolling(12,min_periods=12).median().to_numpy()
    prior=np.full(len(x),np.nan);prior[4:]=O[4:]/C[:-4]-1.;x['prior1h_ret']=prior
    return x.replace([np.inf,-np.inf],np.nan)
def resolve(ep,hs,ls,fc,side):
    if side>0:tp_hits=np.flatnonzero(hs>=ep*(1+TP));sl_hits=np.flatnonzero(ls<=ep*(1-SL))
    else:tp_hits=np.flatnonzero(ls<=ep*(1-TP));sl_hits=np.flatnonzero(hs>=ep*(1+SL))
    ti=int(tp_hits[0]) if tp_hits.size else 10**9;si=int(sl_hits[0]) if sl_hits.size else 10**9
    if si<=ti:raw=-SL;reason='SL'
    elif ti<10**9:raw=TP;reason='TP'
    else:raw=side*(fc/ep-1);reason='TIME'
    net=raw-COST;return net*NOTIONAL,int(net>0),reason

def build(x):
    O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float);wib=x.ts+pd.Timedelta(hours=7);rows=[]
    okfeat=np.all(np.isfinite(x[FEATURES].to_numpy(float)),axis=1);idx=np.flatnonzero((wib.dt.weekday.to_numpy()==4)&(C!=O)&okfeat);idx=idx[(idx+HOLD<len(x)-1)]
    for i in idx:
        side=1 if C[i]>O[i] else -1;ep=O[i+1];hs=H[i+1:i+1+HOLD];ls=L[i+1:i+1+HOLD];fc=C[i+HOLD];cont=resolve(ep,hs,ls,fc,side);rev=resolve(ep,hs,ls,fc,-side)
        rows.append({'signal_ts':str(x.ts.iloc[i]),'friday_wib':str(wib.iloc[i].date()),'entry_ts':str(x.ts.iloc[i+1]),**{f:float(x.iloc[i][f]) for f in FEATURES},'cont_pnl':cont[0],'cont_win':cont[1],'cont_reason':cont[2],'rev_pnl':rev[0],'rev_win':rev[1],'rev_reason':rev[2]})
    return pd.DataFrame(rows)
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
def text(path):return ' AND '.join(f'{a} {b} {c:.8g}' for a,b,c in path)
def blocks(df,mode,leaf):
    dates=sorted(df.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):out[f'B{i+1}']=stats(df[df.friday_wib.isin(set(ch))&(df[f'{mode}_leaf']==leaf)],f'{mode}_pnl')
    return out

def main():
    x=prepare(load15());df=build(x);dates=sorted(df.friday_wib.unique());cut=int(math.floor(.70*len(dates)));dd=set(dates[:cut]);df['period']=np.where(df.friday_wib.isin(dd),'discovery','validation');disc0=df[df.period=='discovery'].copy();val0=df[df.period=='validation'].copy()
    med={f:float(disc0[f].median()) for f in FEATURES};X=df[FEATURES].copy()
    for f in FEATURES:X[f]=pd.to_numeric(X[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med[f])
    candidates=[];reports={};baseline={}
    for mode in ('cont','rev'):
        clf=DecisionTreeClassifier(criterion='gini',max_depth=2,min_samples_leaf=100,random_state=SEED);clf.fit(X.loc[disc0.index],disc0[f'{mode}_win'].astype(int));df[f'{mode}_leaf']=clf.apply(X);disc=df[df.period=='discovery'];val=df[df.period=='validation'];baseline[mode]={'discovery':stats(disc,f'{mode}_pnl'),'validation':stats(val,f'{mode}_pnl'),'full':stats(df,f'{mode}_pnl')};reps=[]
        for leaf in sorted(set(disc[f'{mode}_leaf'])):
            z=disc[disc[f'{mode}_leaf']==leaf];s=stats(z,f'{mode}_pnl');pred=int(np.argmax(clf.tree_.value[int(leaf)][0]));p=path_to_leaf(clf,int(leaf));q={'mode':mode,'leaf':int(leaf),'predicted_class':pred,'rule':text(p),'path':p,**s};reps.append(q)
            if pred==1 and s['n']>=100 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['pf'] is not None and s['pf']>1:candidates.append(q)
        reports[mode]=reps
    candidates.sort(key=lambda q:(-q['wr'],-q['n'],-q['pf'],q['mode'],q['leaf']));out={'protocol':'C4','friday_dates':len(dates),'signal_rows':len(df),'discovery_dates':len(dd),'validation_dates':len(dates)-len(dd),'features':FEATURES,'discovery_medians':med,'baseline':baseline,'discovery_leaves':reports,'eligible_80_leaves':len(candidates)}
    if not candidates:out.update({'selected':None,'verdict':'REJECT_C4_TAKER_IDENTIFIER','reason':'No positive discovery leaf achieved N>=100 and WR>=80%.'})
    else:
        q=candidates[0];m=q['mode'];leaf=q['leaf'];disc=df[df.period=='discovery'];val=df[df.period=='validation'];sd=stats(disc[disc[f'{m}_leaf']==leaf],f'{m}_pnl');sv=stats(val[val[f'{m}_leaf']==leaf],f'{m}_pnl');sf=stats(df[df[f'{m}_leaf']==leaf],f'{m}_pnl');bl=blocks(df,m,leaf);pos=sum(v['n']>=20 and v['pnl']>0 for v in bl.values());ok=sd['n']>=100 and sd['wr']>=.80 and sv['n']>=40 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=150 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and sv['wr']>baseline[m]['validation']['wr'] and pos>=3
        out['selected']={'mode':m,'leaf':leaf,'rule':q['rule'],'path':q['path'],'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos};out['verdict']='BTC_FRIDAY_C4_TAKER_80_CANDIDATE' if ok else 'REJECT_C4_TAKER_IDENTIFIER'
    df.to_csv(OUT_ROWS,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');F=lambda v,d=2:'-' if v is None else f'{v:.{d}f}';md=['# BTC Friday C4 — 15m Candle + Taker-Flow Result','',f"Friday dates **{len(dates)}**; signal rows **{len(df)}**; eligible discovery 80% leaves **{len(candidates)}**",'']
    for mode in ('cont','rev'):
        md += [f'## {mode.upper()} discovery leaves','', '| Leaf | Pred | N | Wins | WR | Rule |','|---:|---:|---:|---:|---:|---|']
        for q in reports[mode]:md.append(f"| {q['leaf']} | {q['predicted_class']} | {q['n']} | {q['wins']} | {F(100*q['wr'])}% | `{q['rule']}` |")
        md.append('')
    if out.get('selected') is None:md += ['## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        s=out['selected'];md += ['## Selected candle+taker fingerprint','',f"Mode **{s['mode'].upper()}**",f"`{s['rule']}`",'', '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,z in [('Discovery',s['discovery']),('Validation',s['validation']),('Full',s['full'])]:md.append(f"| {name} | {z['n']} | {z['wins']} | {F(100*z['wr'])}% | ${F(z['pnl'])} | ${F(z['exp'],3)} | {F(z['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','Observed historical WR is not a guaranteed future probability. No post-result tree/threshold rescue.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
