#!/usr/bin/env python3
"""C0: all Friday-WIB BTCUSDT 1h candle archetype identifier."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import market_hunter_mh0_datavision_runner as dv

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_AllHour_Candle_C0_Result.md'
OUT_JSON=ROOT/'BTC_Friday_AllHour_Candle_C0_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_AllHour_Candle_C0_Rows.csv'
START=pd.Timestamp('2023-12-02T00:00:00Z');END=pd.Timestamp('2026-08-19T00:00:00Z')
TP=SL=.013;COST=.0015;NOTIONAL=500.;SEED=20260819
FEATURES=['signal_ret','body_ratio','upper_ratio','lower_ratio','close_pos','range_open','direction',
          'range_ratio_prev3median','body_delta_prev3median','upper_delta_prev3median','lower_delta_prev3median',
          'prior3h_ret','signal_minus_prior3avg']

def load():
    raw=dv.archive_request('BTCUSDT',START-pd.Timedelta(days=2),END)
    z=pd.DataFrame(raw)
    df=pd.DataFrame({'ts':pd.to_datetime(pd.to_numeric(z.iloc[:,0]),unit='ms',utc=True),
                     'open':pd.to_numeric(z.iloc[:,1]),'high':pd.to_numeric(z.iloc[:,2]),'low':pd.to_numeric(z.iloc[:,3]),'close':pd.to_numeric(z.iloc[:,4])})
    return df.dropna().drop_duplicates('ts').sort_values('ts').reset_index(drop=True)
def geom(o,h,l,c):
    rg=max(h-l,1e-12);return abs(c-o)/rg,(h-max(o,c))/rg,(min(o,c)-l)/rg,(c-l)/rg,(h-l)/o
def trade(df,i,side):
    if i+6>=len(df):return None
    ep=float(df.iloc[i+1].open);tp=ep*(1+TP) if side>0 else ep*(1-TP);sl=ep*(1-SL) if side>0 else ep*(1+SL)
    raw=None;reason=None
    for j in range(i+1,i+7):
        r=df.iloc[j];hi=float(r.high);lo=float(r.low)
        hit_tp=hi>=tp if side>0 else lo<=tp;hit_sl=lo<=sl if side>0 else hi>=sl
        if hit_sl:raw=-SL;reason='SL';break
        if hit_tp:raw=TP;reason='TP';break
    if raw is None:
        px=float(df.iloc[i+6].close);raw=side*(px/ep-1);reason='TIME'
    net=raw-COST;return {'pnl':net*NOTIONAL,'win':int(net>0),'reason':reason,'raw':raw}
def pf(vals):
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<=0);return gp/gl if gl>0 else (999.0 if gp>0 else None)
def stats(df,pnlcol):
    a=df[pnlcol].astype(float).tolist()
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    w=sum(x>0 for x in a);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}
def build_rows(df):
    rows=[]
    for i in range(3,len(df)-6):
        r=df.iloc[i];wib=r.ts+pd.Timedelta(hours=7)
        if wib.weekday()!=4:continue
        o,h,l,c=map(float,[r.open,r.high,r.low,r.close])
        if c==o:continue
        body,up,lo,cp,rg=geom(o,h,l,c);prev=df.iloc[i-3:i]
        prev_body=[];prev_up=[];prev_lo=[]
        for _,p in prev.iterrows():
            b,u,d,_,_=geom(float(p.open),float(p.high),float(p.low),float(p.close));prev_body.append(b);prev_up.append(u);prev_lo.append(d)
        prev_ranges=(prev.high.astype(float)-prev.low.astype(float))/prev.open.astype(float)
        sigret=c/o-1.;p3ret=float(prev.iloc[-1].close)/float(prev.iloc[0].open)-1.;direction=1 if sigret>0 else -1
        ft={'signal_ret':sigret,'body_ratio':body,'upper_ratio':up,'lower_ratio':lo,'close_pos':cp,'range_open':rg,'direction':direction,
            'range_ratio_prev3median':rg/max(float(np.median(prev_ranges)),1e-12),'body_delta_prev3median':body-float(np.median(prev_body)),
            'upper_delta_prev3median':up-float(np.median(prev_up)),'lower_delta_prev3median':lo-float(np.median(prev_lo)),
            'prior3h_ret':p3ret,'signal_minus_prior3avg':sigret-p3ret/3.0}
        cont=trade(df,i,direction);rev=trade(df,i,-direction)
        if cont is None or rev is None:continue
        rows.append({'signal_ts':str(r.ts),'friday_wib':str(wib.date()),'entry_ts':str(df.iloc[i+1].ts),**ft,
                     'cont_pnl':cont['pnl'],'cont_win':cont['win'],'cont_reason':cont['reason'],
                     'rev_pnl':rev['pnl'],'rev_win':rev['win'],'rev_reason':rev['reason']})
    return pd.DataFrame(rows)
def path_to_leaf(clf,leaf):
    tr=clf.tree_;path=[]
    def rec(n,conds):
        if n==leaf:path.extend(conds);return True
        if tr.children_left[n]==tr.children_right[n]:return False
        f=FEATURES[tr.feature[n]];x=float(tr.threshold[n])
        return rec(tr.children_left[n],conds+[(f,'<=',x)]) or rec(tr.children_right[n],conds+[(f,'>',x)])
    rec(0,[]);return path
def rule_text(path):return ' AND '.join(f'{f} {op} {x:.8g}' for f,op,x in path)
def blocks(df,mode,leaf):
    dates=sorted(df.friday_wib.unique());chunks=np.array_split(np.array(dates,dtype=object),4);out={};pc=f'{mode}_pnl'
    for i,ch in enumerate(chunks):out[f'B{i+1}']=stats(df[df.friday_wib.isin(set(ch)) & (df[f'{mode}_leaf']==leaf)],pc)
    return out

def main():
    px=load();df=build_rows(px)
    dates=sorted(df.friday_wib.unique());cut=max(1,int(math.floor(.70*len(dates))));disc_dates=set(dates[:cut]);val_dates=set(dates[cut:])
    df['period']=np.where(df.friday_wib.isin(disc_dates),'discovery','validation')
    disc=df[df.period=='discovery'];val=df[df.period=='validation']
    med={f:float(pd.to_numeric(disc[f],errors='coerce').replace([np.inf,-np.inf],np.nan).median()) for f in FEATURES}
    X=df[FEATURES].copy()
    for f in FEATURES:X[f]=pd.to_numeric(X[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med[f])
    candidates=[];models={};leaf_reports={}
    for mode in ('cont','rev'):
        y=disc[f'{mode}_win'].astype(int);clf=DecisionTreeClassifier(criterion='gini',max_depth=2,min_samples_leaf=100,random_state=SEED)
        clf.fit(X.loc[disc.index],y);df[f'{mode}_leaf']=clf.apply(X);models[mode]=clf
        reps=[]
        for leaf in sorted(set(df.loc[disc.index,f'{mode}_leaf'])):
            z=df.loc[disc.index][df.loc[disc.index,f'{mode}_leaf']==leaf];s=stats(z,f'{mode}_pnl');path=path_to_leaf(clf,int(leaf));pred=int(np.argmax(clf.tree_.value[int(leaf)][0]))
            q={'mode':mode,'leaf':int(leaf),'predicted_class':pred,'rule':rule_text(path),'path':path,**s};reps.append(q)
            if pred==1 and s['n']>=100 and s['wr'] is not None and s['wr']>=.80:candidates.append(q)
        leaf_reports[mode]=reps
    candidates.sort(key=lambda q:(-q['wr'],-q['n'],q['mode'],q['leaf']))
    baseline={mode:{'discovery':stats(disc,f'{mode}_pnl'),'validation':stats(val,f'{mode}_pnl'),'full':stats(df,f'{mode}_pnl')} for mode in ('cont','rev')}
    out={'protocol':'C0','dates':{'n':len(dates),'discovery_n':len(disc_dates),'validation_n':len(val_dates),'first':dates[0],'last':dates[-1]},
         'rows':len(df),'features':FEATURES,'discovery_medians':med,'leaf_reports':leaf_reports,'baseline':baseline}
    if not candidates:
        out.update({'selected':None,'verdict':'REJECT_C0_80_CANDLE_IDENTIFIER','reason':'No continuation/reversal discovery leaf met N>=100 and WR>=80%.'})
    else:
        q=candidates[0];mode=q['mode'];leaf=q['leaf'];sd=stats(df[(df.period=='discovery')&(df[f'{mode}_leaf']==leaf)],f'{mode}_pnl');sv=stats(df[(df.period=='validation')&(df[f'{mode}_leaf']==leaf)],f'{mode}_pnl');sf=stats(df[df[f'{mode}_leaf']==leaf],f'{mode}_pnl');bl=blocks(df,mode,leaf);pos=sum(x['n']>0 and x['pnl']>0 for x in bl.values())
        qualify=bool(sd['n']>=100 and sd['wr']>=.80 and sv['n']>=40 and sv['wr'] is not None and sv['wr']>=.80 and sf['n']>=150 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and pos>=3 and baseline[mode]['validation']['wr'] is not None and sv['wr']>baseline[mode]['validation']['wr'])
        out['selected']={'mode':mode,'leaf':leaf,'rule':q['rule'],'path':q['path'],'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos}
        out['verdict']='BTC_FRIDAY_ALLHOUR_80_CANDIDATE' if qualify else 'REJECT_C0_80_CANDLE_IDENTIFIER'
    OUT_ROWS.write_text(df.to_csv(index=False));OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def F(x,d=2):return '-' if x is None else f'{x:.{d}f}'
    md=['# BTC Friday All-Hour Candle C0 — Result','',f"Friday dates: **{len(dates)}**; signal candles: **{len(df)}**",f"Discovery/validation Friday dates: **{len(disc_dates)} / {len(val_dates)}**",'']
    for mode in ('cont','rev'):
        md += [f'## {mode.upper()} tree discovery leaves','', '| Leaf | Pred | N | Wins | WR | Rule |','|---:|---:|---:|---:|---:|---|']
        for q in leaf_reports[mode]:md.append(f"| {q['leaf']} | {q['predicted_class']} | {q['n']} | {q['wins']} | {F(100*q['wr'])}% | `{q['rule']}` |")
        md.append('')
    if out.get('selected') is None:
        md += ['## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        s=out['selected'];md += ['## Selected candle fingerprint','',f"Mode: **{s['mode'].upper()}**",f"Rule: `{s['rule']}`",'', '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,x in [('Discovery',s['discovery']),('Validation',s['validation']),('Full',s['full'])]:md.append(f"| {name} | {x['n']} | {x['wins']} | {F(100*x['wr'])}% | ${F(x['pnl'],2)} | ${F(x['exp'],3)} | {F(x['pf'],3)} |")
        md += ['','### Chronological blocks','','| Block | N | WR | PnL | PF |','|---|---:|---:|---:|---:|']
        for b,x in s['blocks'].items():md.append(f"| {b} | {x['n']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],2)} | {F(x['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','Observed historical WR is not a guaranteed future probability.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
