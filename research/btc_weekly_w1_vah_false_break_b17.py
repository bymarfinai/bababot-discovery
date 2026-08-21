#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv, json, math
import numpy as np
import pandas as pd
import requests
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import roc_auc_score

import btc_weekly_volume_memory_b13 as vm
import btc_weekly_volume_memory_b13_fast as vmfast
import btc_friday_15m_derivatives_c5 as c5

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Result.md'
OUT_JSON=ROOT/'BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Result.json'
OUT_FEAT=ROOT/'BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Features.csv'
OUT_CAND=ROOT/'BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Candidates.csv'
OUT_MODELS=ROOT/'BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Models.csv'
REVISION='B17_V1'
START=pd.Timestamp('2019-09-01',tz='UTC')
END=pd.Timestamp('2026-08-20',tz='UTC')
BASE_FUT='https://data.binance.vision/data/futures/um'
BASE_SPOT='https://data.binance.vision/data/spot'
SEED=20260821

CORE_FEATURES=[
 'break_close_above_vah_atr','break_range_atr','break_body_frac','break_close_pos','break_ret','prior3h_ret','prior6h_ret','week_hours',
 'f_taker_imbalance_1h','f_taker_imbalance_3h','f_taker_imbalance_6h','f_taker_accel_1h_vs_6h','f_qvol_rate_1h','f_qvol_rate_3h',
 'spot_ret_1h','spot_ret_3h','spot_taker_imbalance_1h','spot_taker_imbalance_3h',
 'spot_minus_fut_ret_1h','spot_minus_fut_ret_3h','spot_minus_fut_flow_1h','spot_minus_fut_flow_3h',
 'basis_now','basis_change_1h','basis_change_6h','premium_now','premium_z7d','premium_change_1h','premium_change_6h'
]
EXT_FEATURES=['top_vs_global','top_pos_chg15','global_chg15','metrics_taker_log','oi_chg15','oi_chg60','oi_chg4h']


def fetch_zip(url, kind):
    r=requests.get(url,timeout=75,headers={'User-Agent':'bababot-b17/1.0'})
    if r.status_code in (404,451): return []
    r.raise_for_status()
    with ZipFile(BytesIO(r.content)) as z:
        names=[n for n in z.namelist() if n.lower().endswith('.csv')]
        if not names:return []
        out=[]
        with z.open(names[0]) as fh:
            rd=csv.reader(TextIOWrapper(fh,encoding='utf-8'))
            for row in rd:
                try: ts=int(row[0])
                except Exception: continue
                if ts>100_000_000_000_000: ts//=1000
                try:
                    if kind in ('futures','spot'):
                        if len(row)<11:continue
                        out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4]),float(row[5]),float(row[7]),float(row[10])])
                    else:
                        if len(row)<5:continue
                        out.append([ts,float(row[1]),float(row[2]),float(row[3]),float(row[4])])
                except Exception: continue
        return out


def archive_urls(base, subpath):
    urls=[];cur=START.floor('D').replace(day=1);last_month=pd.Timestamp('2026-08-01',tz='UTC')
    while cur<last_month:
        ym=cur.strftime('%Y-%m');urls.append(f'{base}/monthly/{subpath}/BTCUSDT/15m/BTCUSDT-15m-{ym}.zip');cur+=pd.offsets.MonthBegin(1)
    d=last_month
    while d<END:
        ds=d.strftime('%Y-%m-%d');urls.append(f'{base}/daily/{subpath}/BTCUSDT/15m/BTCUSDT-15m-{ds}.zip');d+=pd.Timedelta(days=1)
    return urls


def load_15m(base, subpath, kind):
    urls=archive_urls(base,subpath);rows=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs=[ex.submit(fetch_zip,u,kind) for u in urls]
        for n,f in enumerate(as_completed(fs),1):
            rows.extend(f.result())
            if n%20==0: print(kind,'archives',n,'/',len(urls),flush=True)
    if kind in ('futures','spot'):
        cols=['ts','open','high','low','close','volume','quote_volume','taker_buy_quote']
    else: cols=['ts','open','high','low','close']
    x=pd.DataFrame(rows,columns=cols)
    if x.empty:raise RuntimeError(f'no {kind} rows')
    x['ts']=pd.to_datetime(pd.to_numeric(x.ts),unit='ms',utc=True)
    for c in cols[1:]:x[c]=pd.to_numeric(x[c],errors='coerce')
    x=x.dropna().drop_duplicates('ts').sort_values('ts')
    x=x[(x.ts>=START)&(x.ts<END)].set_index('ts')
    if len(x)<200000:raise RuntimeError(f'insufficient {kind} rows {len(x)}')
    return x


def prep_premium(p):
    s=p.close.astype(float)
    mu=s.rolling('7D',closed='left',min_periods=192).mean();sd=s.rolling('7D',closed='left',min_periods=192).std(ddof=0)
    p=p.copy();p['z7d']=(s-mu)/sd
    return p


def cutoff(w):return w+pd.Timedelta(days=5,hours=12)
def week_key(t):return vm.b11.week_key(vm.b11.week_start(pd.Timestamp(t)))


def build_baseline(h1,w1):
    idx=h1.index;op=h1.open.to_numpy(float);cl=h1.close.to_numpy(float)
    inst=w1['instance'].reindex(idx,method='ffill').to_numpy(object);vah=w1['VAH'].reindex(idx,method='ffill').to_numpy(float)
    valid=np.array([x is not None and str(x)!='nan' for x in inst]) & np.isfinite(vah);exe=vm.execution(h1);rows=[]
    weeks=[]
    for part in ('external','development','reference_validation','august'):weeks.extend(vm.b11.partition_weeks(part))
    for w in sorted(set(weeks)):
        a=int(idx.searchsorted(w,'left'));z=int(idx.searchsorted(cutoff(w),'right'))
        for i in range(a,z):
            if valid[i] and op[i]<=vah[i] and cl[i]>vah[i]:
                tr=exe(i,'LONG')
                if tr is not None:
                    rows.append({'week':week_key(idx[i]),'week_start':w,'signal_i':i,'signal_ts':idx[i],'level':float(vah[i]),'atr14':float(h1.atr14.iloc[i]),
                                 'h1_open':float(h1.open.iloc[i]),'h1_high':float(h1.high.iloc[i]),'h1_low':float(h1.low.iloc[i]),'h1_close':float(h1.close.iloc[i]),**tr})
                break
    return pd.DataFrame(rows)


def partition_for_week(w):
    t=pd.Timestamp(w)
    if pd.Timestamp('2020-01-01',tz='UTC')<=t<pd.Timestamp('2022-01-01',tz='UTC'):return 'external'
    if pd.Timestamp('2022-01-01',tz='UTC')<=t<pd.Timestamp('2025-01-01',tz='UTC'):return 'development'
    if pd.Timestamp('2025-01-01',tz='UTC')<=t<pd.Timestamp('2026-07-30',tz='UTC'):return 'reference_validation'
    if t>=pd.Timestamp('2026-08-01',tz='UTC'):return 'august'
    return None


def sanity_baseline(c):
    expected={'development':(82,49),'external':(64,36),'reference_validation':(47,24),'august':(2,0)}
    got={}
    for p,(n,w) in expected.items():
        q=c[c.partition==p];got[p]=(len(q),int((q.reason=='TP').sum()))
        if got[p]!=(n,w):raise RuntimeError(f'B17 baseline mismatch {p}: got {got[p]}, expected {(n,w)}')
    return got


def sl(df,end,hours):return df[(df.index>=end-pd.Timedelta(hours=hours))&(df.index<end)]
def retwin(df,end,hours):
    q=sl(df,end,hours)
    return float(q.close.iloc[-1]/q.open.iloc[0]-1) if len(q) else np.nan

def imbalance(df,end,hours):
    q=sl(df,end,hours);v=float(q.quote_volume.sum()) if len(q) else 0.;b=float(q.taker_buy_quote.sum()) if len(q) else 0.
    return 2*b/v-1 if v>0 else np.nan

def qrate(df,end,hours):
    cur=sl(df,end,hours);prior=df[(df.index>=end-pd.Timedelta(days=7))&(df.index<end-pd.Timedelta(hours=hours))]
    if not len(cur) or not len(prior):return np.nan
    a=float(cur.quote_volume.sum())/hours;b=float(prior.quote_volume.sum())/max((7*24-hours),1)
    return a/b if b>0 else np.nan

def last_complete(df,end):
    i=int(df.index.searchsorted(end,'left'))-1
    return None if i<0 else df.iloc[i]
def value_before(df,end,col):
    r=last_complete(df,end);return np.nan if r is None else float(r[col])


def extract_core(row,h1,fut,spot,prem):
    end=pd.Timestamp(row.entry_ts);i=int(row.signal_i);atr=float(row.atr14);rg=max(float(row.h1_high-row.h1_low),1e-12)
    f1=imbalance(fut,end,1);f3=imbalance(fut,end,3);f6=imbalance(fut,end,6);s1=imbalance(spot,end,1);s3=imbalance(spot,end,3)
    fr1=retwin(fut,end,1);fr3=retwin(fut,end,3);sr1=retwin(spot,end,1);sr3=retwin(spot,end,3)
    fl=last_complete(fut,end);sp=last_complete(spot,end);pr=last_complete(prem,end)
    if fl is None or sp is None or pr is None:basis=np.nan;pn=np.nan;pz=np.nan
    else:basis=float(fl.close/sp.close-1);pn=float(pr.close);pz=float(pr.z7d)
    def basis_at(t):
        a=last_complete(fut,t);b=last_complete(spot,t)
        return np.nan if a is None or b is None else float(a.close/b.close-1)
    def prem_at(t):return value_before(prem,t,'close')
    return {
      'break_close_above_vah_atr':(float(row.h1_close)-float(row.level))/atr if atr>0 else np.nan,
      'break_range_atr':rg/atr if atr>0 else np.nan,
      'break_body_frac':abs(float(row.h1_close-row.h1_open))/rg,
      'break_close_pos':(float(row.h1_close-row.h1_low))/rg,
      'break_ret':float(row.h1_close/row.h1_open-1),
      'prior3h_ret':float(h1.close.iloc[i]/h1.close.iloc[i-3]-1) if i>=3 else np.nan,
      'prior6h_ret':float(h1.close.iloc[i]/h1.close.iloc[i-6]-1) if i>=6 else np.nan,
      'week_hours':float((pd.Timestamp(row.signal_ts)-pd.Timestamp(row.week_start))/pd.Timedelta(hours=1)),
      'f_taker_imbalance_1h':f1,'f_taker_imbalance_3h':f3,'f_taker_imbalance_6h':f6,'f_taker_accel_1h_vs_6h':f1-f6,
      'f_qvol_rate_1h':qrate(fut,end,1),'f_qvol_rate_3h':qrate(fut,end,3),
      'spot_ret_1h':sr1,'spot_ret_3h':sr3,'spot_taker_imbalance_1h':s1,'spot_taker_imbalance_3h':s3,
      'spot_minus_fut_ret_1h':sr1-fr1,'spot_minus_fut_ret_3h':sr3-fr3,'spot_minus_fut_flow_1h':s1-f1,'spot_minus_fut_flow_3h':s3-f3,
      'basis_now':basis,'basis_change_1h':basis-basis_at(end-pd.Timedelta(hours=1)),'basis_change_6h':basis-basis_at(end-pd.Timedelta(hours=6)),
      'premium_now':pn,'premium_z7d':pz,'premium_change_1h':pn-prem_at(end-pd.Timedelta(hours=1)),'premium_change_6h':pn-prem_at(end-pd.Timedelta(hours=6))
    }


def load_event_metrics(entries):
    days=set()
    for t in entries:
        d=pd.Timestamp(t).floor('D');days.add(d);days.add(d-pd.Timedelta(days=1))
    frames=[]
    with ThreadPoolExecutor(max_workers=32) as ex:
        fs=[ex.submit(c5.fetch_metric_day,d) for d in sorted(days)]
        for n,f in enumerate(as_completed(fs),1):
            q=f.result()
            if q is not None and len(q):frames.append(q)
            if n%50==0:print('metric event-days',n,'/',len(fs),flush=True)
    if not frames:return pd.DataFrame()
    m=pd.concat(frames,ignore_index=True).drop_duplicates('ts').sort_values('ts').set_index('ts',drop=False)
    return m


def metric_features(m,entry):
    empty={k:np.nan for k in EXT_FEATURES}
    if m.empty:return empty
    q=c5.metric_at(m,pd.Timestamp(entry))
    if q is None:return empty
    out={'top_vs_global':q['top_vs_global'],'top_pos_chg15':q['top_pos_chg15'],'global_chg15':q['global_chg15'],'metrics_taker_log':q['taker_log'],'oi_chg15':q['oi_chg15'],'oi_chg60':q['oi_chg60'],'oi_chg4h':np.nan}
    idx=m.index;j=int(idx.searchsorted(pd.Timestamp(entry),'left'))-1
    if j>=0:
        cur=m.iloc[j];k=int(idx.searchsorted(pd.Timestamp(cur.ts)-pd.Timedelta(hours=4),'right'))-1
        if k>=0 and float(cur.oi)>0 and float(m.iloc[k].oi)>0:out['oi_chg4h']=math.log(float(cur.oi))-math.log(float(m.iloc[k].oi))
    return out


def pf(a):
    a=np.asarray(a,float);gp=float(a[a>0].sum());gl=float(-a[a<0].sum());return gp/gl if gl>0 else (999. if gp>0 else 0.)
def wilson(w,n,z=1.96):
    if n<=0:return 0.
    p=w/n;d=1+z*z/n;return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/d

def stats(z):
    if z.empty:return {'n':0,'tp':0,'sl':0,'time':0,'wr':None,'exp':None,'pf':None,'wilson':0.}
    a=z.net_ret.to_numpy(float);tp=int((z.reason=='TP').sum());sl0=int((z.reason=='SL').sum());tm=int((z.reason=='TIME').sum())
    return {'n':len(z),'tp':tp,'sl':sl0,'time':tm,'wr':tp/len(z),'exp':float(a.mean()),'pf':pf(a),'wilson':wilson(tp,len(z))}


def smd_auc(z,f):
    q=z[[f,'win']].replace([np.inf,-np.inf],np.nan).dropna();w=q[q.win==1][f].to_numpy(float);l=q[q.win==0][f].to_numpy(float)
    if len(w)<3 or len(l)<3:return {'smd':None,'auc':None,'wmed':None,'lmed':None}
    den=math.sqrt(max((np.var(w,ddof=1)+np.var(l,ddof=1))/2,1e-18));s=(float(np.mean(w))-float(np.mean(l)))/den
    try:a=float(roc_auc_score(q.win,q[f]));a=max(a,1-a)
    except Exception:a=None
    return {'smd':s,'auc':a,'wmed':float(np.median(w)),'lmed':float(np.median(l))}


def path_to_leaf(clf,features,leaf):
    tr=clf.tree_;out=[]
    def rec(n,p):
        if n==leaf:out.extend(p);return True
        if tr.children_left[n]==tr.children_right[n]:return False
        f=features[tr.feature[n]];v=float(tr.threshold[n])
        return rec(tr.children_left[n],p+[(f,'<=',v)]) or rec(tr.children_right[n],p+[(f,'>',v)])
    rec(0,[]);return out

def path_text(p):return ' AND '.join(f'{a} {b} {c:.8g}' for a,b,c in p)


def fit_model(cand,features,name):
    complete=cand[np.isfinite(cand[features].to_numpy(float)).all(axis=1)].copy()
    dev=complete[complete.partition=='development'].copy()
    if len(dev)<30 or dev.win.nunique()<2:return None
    clf=DecisionTreeClassifier(max_depth=2,min_samples_leaf=12,class_weight='balanced',random_state=SEED)
    clf.fit(dev[features].to_numpy(float),dev.win.to_numpy(int))
    complete['leaf']=clf.apply(complete[features].to_numpy(float))
    dev=complete[complete.partition=='development']
    choices=[]
    for leaf,g in dev.groupby('leaf'):
        if len(g)<15:continue
        s=stats(g);choices.append((s['wilson'],s['wr'],s['n'],-int(leaf),int(leaf),s))
    if not choices:return None
    choices.sort(reverse=True);leaf=choices[0][4];dstat=choices[0][5];path=path_to_leaf(clf,features,leaf)
    parts={}
    for part in ('development','external','reference_validation','august'):
        q=complete[(complete.partition==part)&(complete.leaf==leaf)].copy();parts[part]=stats(q)
    return {'name':name,'features':features,'clf':clf,'leaf':leaf,'path':path,'rule':path_text(path),'dev_wilson':dstat['wilson'],'dev_n':dstat['n'],'parts':parts,'complete':complete}


def main():
    fut=load_15m(BASE_FUT,'klines','futures');print('futures',len(fut),flush=True)
    spot=load_15m(BASE_SPOT,'klines','spot');print('spot',len(spot),flush=True)
    prem=prep_premium(load_15m(BASE_FUT,'premiumIndexKlines','premium'));print('premium',len(prem),flush=True)
    h1=vm.build_h1(fut);w1=vmfast.build_level_state_fast(fut[['open','high','low','close','volume']],'W1')
    cand=build_baseline(h1,w1);cand['partition']=cand.week_start.map(partition_for_week);cand=cand[cand.partition.notna()].copy();cand['win']=(cand.reason=='TP').astype(int)
    sanity=sanity_baseline(cand);print('baseline sanity',sanity,flush=True)

    core_rows=[]
    for _,r in cand.iterrows():core_rows.append(extract_core(r,h1,fut,spot,prem))
    core=pd.DataFrame(core_rows,index=cand.index)
    for c in CORE_FEATURES:cand[c]=core[c]

    m=load_event_metrics(cand.entry_ts.tolist());print('event metrics rows',len(m),flush=True)
    extrows=[]
    for _,r in cand.iterrows():extrows.append(metric_features(m,r.entry_ts))
    ex=pd.DataFrame(extrows,index=cand.index)
    for c in EXT_FEATURES:cand[c]=ex[c]

    # Per-partition feature completeness.
    core_cov={};ext_cov={}
    for p in ('development','external','reference_validation','august'):
        q=cand[cand.partition==p]
        core_cov[p]=float(np.isfinite(q[CORE_FEATURES].to_numpy(float)).all(axis=1).mean()) if len(q) else 0.
        ext_cov[p]=float(np.isfinite(q[CORE_FEATURES+EXT_FEATURES].to_numpy(float)).all(axis=1).mean()) if len(q) else 0.
    extended_allowed=all(ext_cov[p]>=.75 for p in ('development','external','reference_validation'))

    # Forensic feature table frozen on all features with available values.
    feats=[]
    for f in CORE_FEATURES+EXT_FEATURES:
        row={'feature':f};ss={}
        for p in ('development','external','reference_validation'):
            a=smd_auc(cand[cand.partition==p],f);ss[p]=a
            row[f'{p}_smd']=a['smd'];row[f'{p}_auc']=a['auc'];row[f'{p}_winner_median']=a['wmed'];row[f'{p}_loser_median']=a['lmed']
        vals=[ss[p]['smd'] for p in ('development','external','reference_validation')]
        stable=(all(v is not None for v in vals) and abs(vals[0])>=.25 and abs(vals[1])>=.10 and abs(vals[2])>=.10 and ((vals[0]>0 and vals[1]>0 and vals[2]>0) or (vals[0]<0 and vals[1]<0 and vals[2]<0)))
        row['stable']=stable;feats.append(row)
    ft=pd.DataFrame(feats);ft['dev_abs_smd']=ft.development_smd.abs();ft=ft.sort_values(['stable','dev_abs_smd'],ascending=[False,False]);ft.to_csv(OUT_FEAT,index=False)

    models=[]
    corem=fit_model(cand,CORE_FEATURES,'CORE_TREE')
    if corem:models.append(corem)
    if extended_allowed:
        extm=fit_model(cand,CORE_FEATURES+EXT_FEATURES,'EXTENDED_TREE')
        if extm:models.append(extm)
    if not models:raise RuntimeError('no B17 model could be fit')
    models.sort(key=lambda x:(x['dev_wilson'],x['dev_n'],x['name']=='CORE_TREE'),reverse=True);selected=models[0]

    baseline={p:stats(cand[cand.partition==p]) for p in ('development','external','reference_validation','august')}
    model_rows=[]
    for mo in models:
        for p,s in mo['parts'].items():model_rows.append({'model':mo['name'],'selected':mo is selected,'leaf':mo['leaf'],'rule':mo['rule'],'partition':p,**s})
    pd.DataFrame(model_rows).to_csv(OUT_MODELS,index=False)
    cand.to_csv(OUT_CAND,index=False)

    e=selected['parts']['external'];v=selected['parts']['reference_validation'];be=baseline['external'];bv=baseline['reference_validation']
    useful=bool(e['n']>=12 and v['n']>=10 and e['wr'] is not None and v['wr'] is not None and e['wr']>=.65 and v['wr']>=.65 and e['pf']>1 and v['pf']>1 and e['wr']>be['wr'] and v['wr']>bv['wr'])
    high=bool(e['n']>=10 and v['n']>=10 and e['wr'] is not None and v['wr'] is not None and e['wr']>=.80 and v['wr']>=.80 and e['pf']>1 and v['pf']>1)
    stable_n=int(ft.stable.sum())
    result={'experiment':'B17_W1_VAH_FALSE_BREAK_FILTER','revision':REVISION,'baseline_sanity':sanity,'core_coverage':core_cov,'extended_coverage':ext_cov,'extended_allowed':extended_allowed,'stable_differentiators':stable_n,
            'selected_model':selected['name'],'selected_leaf':selected['leaf'],'selected_rule':selected['rule'],'baseline':baseline,'filtered':selected['parts'],
            'gates':{'B17_USEFUL_FALSE_BREAK_FILTER':'PASS' if useful else 'FAIL','B17_HIGH_PRECISION_FILTER':'PASS' if high else 'FAIL'},'live_bbc_untouched':True}
    OUT_JSON.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')

    pct=lambda x:'-' if x is None else f'{100*x:.2f}%';num=lambda x:'-' if x is None else f'{x:.3f}'
    lines=['# BTC Weekly W1 VAH False-Break Filter B17 — Result','',f"**Verdict: {'B17_USEFUL_FILTER_PASS' if useful else 'B17_NO_USEFUL_FALSE_BREAK_FILTER'}**",'',
           f"Baseline sanity reproduced exactly: **{sanity}**.",f"Stable differentiators: **{stable_n}**.",f"Extended derivatives allowed: **{extended_allowed}**.",'',
           f"Frozen selected model: **{selected['name']}**, leaf **{selected['leaf']}**",f"Rule: `{selected['rule']}`",'',
           '## Baseline vs filtered','', '| Partition | Baseline N/WR/PF | Filtered N/WR/PF | Retention |','|---|---:|---:|---:|']
    for p in ('development','external','reference_validation','august'):
        b=baseline[p];s=selected['parts'][p];ret=s['n']/b['n'] if b['n'] else 0
        lines.append(f"| {p} | {b['n']} / {pct(b['wr'])} / {num(b['pf'])} | {s['n']} / {pct(s['wr'])} / {num(s['pf'])} | {pct(ret)} |")
    lines += ['','## Top forensic differences','', '| Feature | Stable | Dev SMD | Ext SMD | Val SMD | Dev AUC | Ext AUC | Val AUC |','|---|---|---:|---:|---:|---:|---:|---:|']
    for _,r in ft.head(15).iterrows():
        lines.append(f"| `{r.feature}` | {'yes' if r.stable else 'no'} | {num(r.development_smd)} | {num(r.external_smd)} | {num(r.reference_validation_smd)} | {num(r.development_auc)} | {num(r.external_auc)} | {num(r.reference_validation_auc)} |")
    lines += ['','## Data coverage','',f"Core complete coverage: `{core_cov}`",f"Extended complete coverage: `{ext_cov}`",'', '## Gates','',
              f"- B17_USEFUL_FALSE_BREAK_FILTER: **{'PASS' if useful else 'FAIL'}**",f"- B17_HIGH_PRECISION_FILTER: **{'PASS' if high else 'FAIL'}**",'',
              'No OOS retuning. This filter applies only when a W1 VAH breakout candidate exists; it is not a universal weekly-entry rule. Live BBC untouched.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
