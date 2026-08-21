#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor, as_completed
import json, math
import numpy as np
import pandas as pd
import requests

import btc_weekly_mtf_level_atlas_b11 as b11

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_VOLUME_MEMORY_B13_Result.md'
OUT_JSON=ROOT/'BTC_WEEKLY_VOLUME_MEMORY_B13_Result.json'
OUT_SEL=ROOT/'BTC_WEEKLY_VOLUME_MEMORY_B13_Selected.csv'
OUT_RULES=ROOT/'BTC_WEEKLY_VOLUME_MEMORY_B13_Rules.csv'
OUT_ATLAS=ROOT/'BTC_WEEKLY_VOLUME_MEMORY_B13_Atlas.csv'

START_LOAD=pd.Timestamp('2019-09-01',tz='UTC')
END_LOAD=pd.Timestamp('2026-08-20',tz='UTC')
LEVELS=['VWAP','POC','VAL','VAH']
TFS=['H1','H4','D1','W1']
MODES=['HOLD','RECLAIM','BODY','WICK']
FAV=0.0115; ADV=0.0085; FEE=0.0015


def fetch_zip(url):
    r=requests.get(url,timeout=90)
    if r.status_code in (404,451): return []
    r.raise_for_status()
    with ZipFile(BytesIO(r.content)) as z:
        names=[n for n in z.namelist() if n.endswith('.csv')]
        if not names:return []
        with z.open(names[0]) as f:
            q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4,5],dtype=str)
    q.columns=['ts','open','high','low','close','volume']
    q=q[pd.to_numeric(q.ts,errors='coerce').notna()].copy()
    for c in ['ts','open','high','low','close','volume']:q[c]=pd.to_numeric(q[c],errors='coerce')
    return q.dropna().values.tolist()


def load_15m():
    base='https://data.binance.vision/data/futures/um'
    urls=[]; cur=START_LOAD.floor('D').replace(day=1)
    last_month=pd.Timestamp('2026-08-01',tz='UTC')
    while cur<last_month:
        ym=cur.strftime('%Y-%m'); urls.append(f'{base}/monthly/klines/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip'); cur+=pd.offsets.MonthBegin(1)
    d=last_month
    while d<END_LOAD:
        ds=d.strftime('%Y-%m-%d'); urls.append(f'{base}/daily/klines/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip'); d+=pd.Timedelta(days=1)
    rows=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs=[ex.submit(fetch_zip,u) for u in urls]
        for n,f in enumerate(as_completed(fs),1):
            rows.extend(f.result())
            if n%10==0:print('archives',n,'/',len(urls))
    if not rows:raise RuntimeError('no 15m rows')
    x=pd.DataFrame(rows,columns=['ts','open','high','low','close','volume'])
    x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True)
    for c in ['open','high','low','close','volume']:x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.dropna().drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=START_LOAD)&(x.ts<END_LOAD)].set_index('ts')
    return x


def week_start_index(index):
    return pd.DatetimeIndex([b11.week_start(t) for t in index])


def period_key(index,tf):
    if tf=='H1':return index.floor('h')
    if tf=='H4':return index.floor('4h')
    if tf=='D1':return index.floor('D')
    if tf=='W1':return week_start_index(index)
    raise ValueError(tf)

def duration(tf):return {'H1':pd.Timedelta(hours=1),'H4':pd.Timedelta(hours=4),'D1':pd.Timedelta(days=1),'W1':pd.Timedelta(days=7)}[tf]


def profile_levels(g):
    lo=float(g.low.min()); hi=float(g.high.max())
    tp=(g.high.to_numpy(float)+g.low.to_numpy(float)+g.close.to_numpy(float))/3.0
    vol=g.volume.to_numpy(float); vs=float(vol.sum())
    vwap=float(np.sum(tp*vol)/vs) if vs>0 else float(np.mean(tp))
    if not np.isfinite(hi-lo) or hi<=lo+1e-12:
        return vwap,float(np.mean(tp)),float(np.mean(tp)),float(np.mean(tp))
    edges=np.linspace(lo,hi,25); centers=(edges[:-1]+edges[1:])/2.0
    bi=np.searchsorted(edges,tp,side='right')-1; bi=np.clip(bi,0,23)
    hist=np.bincount(bi,weights=vol,minlength=24).astype(float)
    poc=int(np.argmax(hist)); target=0.70*float(hist.sum())
    left=right=poc; cum=float(hist[poc])
    while cum<target and (left>0 or right<23):
        lv=float(hist[left-1]) if left>0 else -1.0
        rv=float(hist[right+1]) if right<23 else -1.0
        if left>0 and (right>=23 or lv>=rv):
            left-=1; cum+=float(hist[left])
        elif right<23:
            right+=1; cum+=float(hist[right])
        else:break
    return vwap,float(centers[poc]),float(centers[left]),float(centers[right])


def build_level_state(x15,tf):
    keys=period_key(x15.index,tf)
    rows=[]
    for k,g in x15.groupby(keys,sort=True):
        # Require a minimally complete source period to avoid archive-edge partials.
        expected={'H1':4,'H4':16,'D1':96,'W1':672}[tf]
        if len(g)<max(1,int(expected*0.95)):continue
        vwap,poc,val,vah=profile_levels(g)
        rows.append({'avail_ts':pd.Timestamp(k)+duration(tf),'instance':pd.Timestamp(k).isoformat(),
                     'VWAP':vwap,'POC':poc,'VAL':val,'VAH':vah})
    q=pd.DataFrame(rows).sort_values('avail_ts').set_index('avail_ts')
    return q


def build_h1(x15):
    h=x15.resample('1h',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    pc=h.close.shift(1)
    tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    h['atr14']=tr.rolling(14,min_periods=14).mean()
    return h


def confirmation(mode,side,o,h,l,c,level,atr):
    finite=np.isfinite(level)&np.isfinite(atr)&(atr>0); near=np.abs(c-level)<=0.75*atr
    body=np.abs(c-o); lower=np.maximum(0,np.minimum(o,c)-l); upper=np.maximum(0,h-np.maximum(o,c))
    if side=='LONG':
        hold=(l<=level)&(c>=level)
        extra={'HOLD':np.ones(len(c),bool),'RECLAIM':l<level,'BODY':c>o,'WICK':lower>=0.5*np.maximum(body,1e-12)}[mode]
    else:
        hold=(h>=level)&(c<=level)
        extra={'HOLD':np.ones(len(c),bool),'RECLAIM':h>level,'BODY':c<o,'WICK':upper>=0.5*np.maximum(body,1e-12)}[mode]
    return finite&near&hold&extra


def execution(h1):
    idx=h1.index; op=h1.open.to_numpy(float); hi=h1.high.to_numpy(float); lo=h1.low.to_numpy(float); cl=h1.close.to_numpy(float); cache={}
    def run(si,side):
        key=(int(si),side)
        if key in cache:return cache[key]
        ei=int(si)+1
        if ei>=len(h1):return None
        ets=idx[ei]; w=b11.week_start(ets); wend=w+pd.Timedelta(days=7); stop=int(idx.searchsorted(wend,'left'))
        if not (w<=ets<wend) or stop<=ei:return None
        entry=float(op[ei]); tp=entry*(1+FAV) if side=='LONG' else entry*(1-FAV); sl=entry*(1-ADV) if side=='LONG' else entry*(1+ADV)
        reason='TIME'; px=float(cl[stop-1]); xi=stop-1
        for j in range(ei,stop):
            if side=='LONG':hs=lo[j]<=sl; ht=hi[j]>=tp
            else:hs=hi[j]>=sl; ht=lo[j]<=tp
            if hs:reason='SL';px=sl;xi=j;break
            if ht:reason='TP';px=tp;xi=j;break
        gross=(px/entry-1)*(1 if side=='LONG' else -1)
        r={'entry_ts':ets,'exit_ts':idx[xi],'entry':entry,'tp':tp,'sl':sl,'reason':reason,'net_ret':gross-FEE,'hours':int(xi-ei+1)}
        cache[key]=r;return r
    return run


def generate_candidates(h1,states):
    idx=h1.index; o=h1.open.to_numpy(float); hi=h1.high.to_numpy(float); lo=h1.low.to_numpy(float); cl=h1.close.to_numpy(float); atr=h1.atr14.to_numpy(float)
    exe=execution(h1); rows=[]
    for tf,state in states.items():
        print('volume atlas',tf)
        inst=state['instance'].reindex(idx,method='ffill').to_numpy(object)
        valid=np.array([x is not None and str(x)!='nan' for x in inst])
        for lev in LEVELS:
            lv=state[lev].reindex(idx,method='ffill').to_numpy(float)
            for side in ('LONG','SHORT'):
                role='SUPPORT' if side=='LONG' else 'RESISTANCE'
                for mode in MODES:
                    mask=confirmation(mode,side,o,hi,lo,cl,lv,atr)&valid
                    inds=np.flatnonzero(mask); seen=set(); rule=f'{tf}|{lev}|{role}|{mode}'
                    for i in inds:
                        iid=f'{tf}|{lev}|{inst[i]}|{role}'
                        if iid in seen:continue
                        seen.add(iid)
                        tr=exe(int(i),side)
                        if tr is None:continue
                        rows.append({'rule':rule,'source_tf':tf,'level_type':lev,'role':role,'mode':mode,'signal_i':int(i),
                                     'signal_ts':idx[i],'side':side,'level':float(lv[i]),'instance':iid,'week':b11.week_key(b11.week_start(idx[i])),**tr})
    q=pd.DataFrame(rows)
    if q.empty:raise RuntimeError('no B13 candidates')
    return q.sort_values(['signal_ts','rule']).reset_index(drop=True)


def scan_ok(ts):
    t=pd.Timestamp(ts);return t<=b11.week_start(t)+pd.Timedelta(days=5,hours=12)

def route_rule(cand,rule,weeks):
    ws=b11.week_set(weeks);q=cand[(cand.rule==rule)&cand.week.isin(ws)&cand.signal_ts.map(scan_ok)].sort_values('signal_ts')
    if q.empty:return q
    q=q.groupby('week',as_index=False,sort=False).head(1).copy();q['route']='PRIMARY_RULE';return q.sort_values('signal_ts')

def rank_rules(cand,weeks):
    rows=[]
    for rule in sorted(cand.rule.unique()):
        q=route_rule(cand,rule,weeks);s=b11.stat(q,weeks);parts=rule.split('|')
        rows.append({'rule':rule,'source_tf':parts[0],'level_type':parts[1],'role':parts[2],'mode':parts[3],**s})
    r=pd.DataFrame(rows);r['fullcov']=(r.coverage>=1-1e-12).astype(int);r['wr_sort']=r.wr.fillna(-1);r['pf_sort']=r.pf.fillna(-1)
    r=r.sort_values(['fullcov','wr_sort','wilson','pf_sort','n','rule'],ascending=[False,False,False,False,False,True]).reset_index(drop=True);r['rank']=np.arange(1,len(r)+1)
    return r

def top4(r):
    out=[];seen=set()
    for _,x in r.iterrows():
        k=(x.source_tf,x.level_type)
        if k in seen:continue
        seen.add(k);out.append(x.rule)
        if len(out)==4:break
    return out

def route_top4(cand,rules,weeks):
    ws=b11.week_set(weeks);rank={r:i for i,r in enumerate(rules)}
    q=cand[cand.rule.isin(rules)&cand.week.isin(ws)&cand.signal_ts.map(scan_ok)].copy()
    if q.empty:return q
    q['rrank']=q.rule.map(rank);q=q.sort_values(['signal_ts','rrank','rule']).groupby('week',as_index=False,sort=False).head(1).copy();q['route']='TOP4_ROUTER';return q.sort_values('signal_ts')

def atlas(cand):
    rows=[];q=cand[cand.signal_ts.map(scan_ok)]
    for (tf,lev,mode),g in q.groupby(['source_tf','level_type','mode']):
        for part in ('development','external','reference_validation'):
            weeks=b11.partition_weeks(part);ws=b11.week_set(weeks);x=g[g.week.isin(ws)].sort_values('signal_ts'); routed=x.groupby('week',as_index=False,sort=False).head(1) if len(x) else x;s=b11.stat(routed,weeks)
            rows.append({'source_tf':tf,'level_type':lev,'mode':mode,'partition':part,'candidate_n':len(x),'raw_wr':float((x.reason=='TP').mean()) if len(x) else None,
                         'coverage':s['coverage'],'weekly_wr':s['wr'],'long_n':int((x.side=='LONG').sum()),'short_n':int((x.side=='SHORT').sum()),'median_hours':float(x.hours.median()) if len(x) else None})
    return pd.DataFrame(rows)
def gate(s,bs,weeks,wrmin):
    return (s['n']==len(weeks) and abs(s['coverage']-1)<1e-12 and s['wr'] is not None and s['wr']>=wrmin and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1 and (s['max_ls']==0 if wrmin>=1 else s['max_ls']<=2) and sum(1 for b in bs if b['exp'] is not None and b['exp']>0)>=(4 if wrmin>=1 else 3))
def pct(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{100*float(v):.2f}%'
def num(v):return '-' if v is None or (isinstance(v,float) and not np.isfinite(v)) else f'{float(v):.3f}'

def main():
    x15=load_15m();print('15m',len(x15),x15.index.min(),x15.index.max())
    h1=build_h1(x15);states={tf:build_level_state(x15,tf) for tf in TFS}
    for tf,s in states.items():print(tf,len(s))
    cand=generate_candidates(h1,states);cand=cand[cand.signal_ts>=b11.EXT0].copy()
    dw=b11.partition_weeks('development');ranks=rank_rules(cand,dw);primary=str(ranks.iloc[0].rule);t4=top4(ranks);ranks.to_csv(OUT_RULES,index=False)
    aa=atlas(cand);aa.to_csv(OUT_ATLAS,index=False)
    summary={};sels=[]
    for selector in ('PRIMARY_RULE','TOP4_ROUTER'):
        summary[selector]={}
        for part in ('development','external','reference_validation','august'):
            weeks=b11.partition_weeks(part);q=route_rule(cand,primary,weeks) if selector=='PRIMARY_RULE' else route_top4(cand,t4,weeks);s=b11.stat(q,weeks);bs=b11.block_stats(q,weeks)
            if len(q):qq=q.copy();qq['selector']=selector;qq['partition']=part;sels.append(qq)
            summary[selector][part]={'stat':s,'blocks':bs}
    if sels:pd.concat(sels,ignore_index=True).to_csv(OUT_SEL,index=False)
    ew=b11.partition_weeks('external');vw=b11.partition_weeks('reference_validation');robust=False;highp=False;passing=None
    for sel in ('PRIMARY_RULE','TOP4_ROUTER'):
        e=summary[sel]['external'];v=summary[sel]['reference_validation']
        if gate(e['stat'],e['blocks'],ew,1) and gate(v['stat'],v['blocks'],vw,1):robust=True;passing=sel
        if gate(e['stat'],e['blocks'],ew,.8) and gate(v['stat'],v['blocks'],vw,.8):highp=True
    result={'experiment':'B13_VOLUME_MEMORY','coverage':{'first':str(h1.index.min()),'last':str(h1.index.max()),'h1_rows':len(h1),'m15_rows':len(x15)},
            'primary_rule':primary,'top4_router':t4,'development_top10':ranks.head(10).replace({np.nan:None}).to_dict('records'),'selectors':summary,
            'gates':{'B13_ROBUST_WEEKLY_100':'PASS' if robust else 'FAIL','B13_HIGH_PRECISION_WEEKLY':'PASS' if highp else 'FAIL','passing_selector':passing},'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    lines=['# BTC Weekly Volume-Memory Levels B13 — Result','',f"**Verdict: {'B13_ROBUST_WEEKLY_100_PASS' if robust else 'B13_NO_ROBUST_WEEKLY_100'}**",'',
           f"15m rows **{len(x15):,}**, H1 execution rows **{len(h1):,}**, {h1.index.min()} -> {h1.index.max()}.",'',
           f'Frozen development PRIMARY_RULE: **{primary}**','', 'Frozen TOP4_ROUTER:']+[f'- {i+1}. `{x}`' for i,x in enumerate(t4)]+['',
           '| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |','|---|---|---:|---:|---:|---:|---:|---:|']
    for sel in ('PRIMARY_RULE','TOP4_ROUTER'):
        for part in ('development','external','reference_validation','august'):
            s=summary[sel][part]['stat'];lines.append(f"| {sel} | {part} | {s['weeks']}/{s['n']}/{pct(s['coverage'])} | {s['tp']}/{s['sl']}/{s['time']} | {pct(s['wr'])} | {pct(s['exp'])} | {num(s['pf'])} | {s['max_ls']} |")
    lines += ['','## Development top 10','', '| Rank | Rule | Coverage | WR | Wilson LB | PF | N |','|---:|---|---:|---:|---:|---:|---:|']
    for _,x in ranks.head(10).iterrows():lines.append(f"| {int(x['rank'])} | `{x.rule}` | {pct(x.coverage)} | {pct(x.wr)} | {pct(x.wilson)} | {num(x.pf)} | {int(x.n)} |")
    lines += ['','## Gates','',f"- B13_ROBUST_WEEKLY_100: **{'PASS' if robust else 'FAIL'}**",f"- B13_HIGH_PRECISION_WEEKLY: **{'PASS' if highp else 'FAIL'}**",'', 'Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines))

if __name__=='__main__':main()
