#!/usr/bin/env python3
"""C7B: C6 selective walk-forward AI augmented only with frozen premium features."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

import btc_friday_c7a_premium_dislocation as c7a

ROOT=Path(__file__).resolve().parent.parent
C4=ROOT/'BTC_Friday_15m_Candle_Taker_C4_Rows.csv';C5=ROOT/'BTC_Friday_15m_Derivatives_C5_Rows.csv'
OUT_MD=ROOT/'BTC_Friday_C7B_Premium_Selective_AI_Result.md';OUT_JSON=ROOT/'BTC_Friday_C7B_Premium_Selective_AI_Result.json';OUT_CSV=ROOT/'BTC_Friday_C7B_Premium_Selective_AI_Predictions.csv'
WARMUP=52;THRESH=.80;SEED=20260819
BASE_FEATURES=['signal_ret','body_ratio','upper_ratio','lower_ratio','close_pos','range_open','prior1h_ret','taker_imbalance','taker_delta_vs_prior3','rel_quote_volume_24h','rel_range_prior12','top_vs_global','top_pos_chg15','global_chg15','taker_log','oi_chg15','oi_chg60']
PREM=['premium_close','premium_z7d','premium_delta15','premium_delta60','premium_range_z7d'];FEATURES=BASE_FEATURES+PREM


def model():return HistGradientBoostingClassifier(loss='log_loss',learning_rate=.05,max_iter=100,max_depth=3,min_samples_leaf=30,l2_regularization=1.0,random_state=SEED)
def pwin(clf,X):
    if 1 not in clf.classes_:return np.zeros(len(X),dtype=float)
    return clf.predict_proba(X)[:,list(clf.classes_).index(1)]
def pf(a):
    gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0);return gp/gl if gl>0 else (999. if gp>0 else None)
def stats(rows):
    a=[float(r['actual_pnl']) for r in rows]
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    w=sum(v>0 for v in a);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}


def load():
    a=pd.read_csv(C4);b=pd.read_csv(C5)
    keep_a=['signal_ts','taker_imbalance','taker_delta_vs_prior3','rel_quote_volume_24h','rel_range_prior12','cont_pnl','cont_win','rev_pnl','rev_win']
    z=b.merge(a[keep_a],on='signal_ts',how='inner',suffixes=('_c5','_c4'),validate='one_to_one');viol=0
    for stem in ('cont_pnl','rev_pnl'):viol+=int(((pd.to_numeric(z[f'{stem}_c5'])-pd.to_numeric(z[f'{stem}_c4'])).abs()>1e-9).sum())
    for stem in ('cont_win','rev_win'):viol+=int((pd.to_numeric(z[f'{stem}_c5']).astype(int)!=pd.to_numeric(z[f'{stem}_c4']).astype(int)).sum())
    for stem in ('cont_pnl','rev_pnl'):z[stem]=pd.to_numeric(z[f'{stem}_c5'])
    for stem in ('cont_win','rev_win'):z[stem]=pd.to_numeric(z[f'{stem}_c5']).astype(int)
    for c in BASE_FEATURES[:7]+BASE_FEATURES[11:]:z[c]=pd.to_numeric(z[c],errors='coerce')
    for c in BASE_FEATURES[7:11]:z[c]=pd.to_numeric(z[c],errors='coerce')
    z['signal_ts']=pd.to_datetime(z.signal_ts,utc=True);z['entry_ts']=pd.to_datetime(z.entry_ts,utc=True);z['friday_wib']=z.friday_wib.astype(str)
    p=c7a.load_premium().copy();s=p.p_close.astype(float);rng=(p.p_high-p.p_low).astype(float)
    p['premium_close']=s;p['premium_z7d']=p.premium_z
    p['premium_delta15']=s-s.shift(1);p['premium_delta60']=s-s.shift(4)
    rm=rng.rolling('7D',closed='left',min_periods=192).mean();rs=rng.rolling('7D',closed='left',min_periods=192).std(ddof=0);p['premium_range_z7d']=(rng-rm)/rs
    pp=p[['premium_close','premium_z7d','premium_delta15','premium_delta60','premium_range_z7d']].copy();pp['signal_ts']=pp.index
    z=z.merge(pp.reset_index(drop=True),on='signal_ts',how='inner',validate='one_to_one')
    if z.empty:raise RuntimeError('empty premium join')
    viol+=int((z.entry_ts<=z.signal_ts).sum())
    green=z.signal_ret>0;z['long_win']=np.where(green,z.cont_win,z.rev_win).astype(int);z['short_win']=np.where(green,z.rev_win,z.cont_win).astype(int);z['long_pnl']=np.where(green,z.cont_pnl,z.rev_pnl).astype(float);z['short_pnl']=np.where(green,z.rev_pnl,z.cont_pnl).astype(float)
    for c in PREM:z[c]=pd.to_numeric(z[c],errors='coerce')
    return z.sort_values(['friday_wib','signal_ts']).reset_index(drop=True),viol


def calibration(top):
    out={}
    for name,lo,hi in [('<0.50',-1,.5),('0.50-0.60',.5,.6),('0.60-0.70',.6,.7),('0.70-0.80',.7,.8),('>=0.80',.8,2)]:
        q=[r for r in top if lo<=r['confidence']<hi]
        out[name]={'n':len(q),'wins':sum(r['actual_win'] for r in q),'wr':(sum(r['actual_win'] for r in q)/len(q) if q else None),'mean_confidence':(float(np.mean([r['confidence'] for r in q])) if q else None),'pnl':sum(r['actual_pnl'] for r in q)}
    return out


def main():
    df,integrity=load();dates=sorted(df.friday_wib.unique())
    if len(dates)<=WARMUP:raise RuntimeError(f'only {len(dates)} Fridays')
    top=[];leak=0
    for ix,day in enumerate(dates[WARMUP:],start=WARMUP):
        train=df[df.friday_wib.isin(set(dates[:ix]))].copy();test=df[df.friday_wib==day].copy()
        if train.empty or test.empty:continue
        if max(train.friday_wib)>=day:leak+=1
        Xtr=train[FEATURES].copy();Xte=test[FEATURES].copy()
        for f in FEATURES:
            v=pd.to_numeric(Xtr[f],errors='coerce').replace([np.inf,-np.inf],np.nan);med=float(v.median());med=med if math.isfinite(med) else 0.;Xtr[f]=v.fillna(med);Xte[f]=pd.to_numeric(Xte[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med)
        ml=model();ms=model();ml.fit(Xtr,train.long_win.astype(int));ms.fit(Xtr,train.short_win.astype(int));pl=pwin(ml,Xte);ps=pwin(ms,Xte);cand=[]
        for j,(_,r) in enumerate(test.iterrows()):
            if pl[j]>=ps[j]:sd='LONG';conf=float(pl[j]);aw=int(r.long_win);ap=float(r.long_pnl)
            else:sd='SHORT';conf=float(ps[j]);aw=int(r.short_win);ap=float(r.short_pnl)
            cand.append({'friday_wib':day,'signal_ts':str(r.signal_ts),'entry_ts':str(r.entry_ts),'direction':sd,'p_long':float(pl[j]),'p_short':float(ps[j]),'confidence':conf,'actual_win':aw,'actual_pnl':ap,'training_fridays':ix,'training_rows':len(train)})
        cand.sort(key=lambda r:(-r['confidence'],pd.Timestamp(r['signal_ts'])));top.append(cand[0])
    traded=[r for r in top if r['confidence']>=THRESH];s=stats(traded);scored=[r['friday_wib'] for r in top];blocks={}
    for i,ch in enumerate(np.array_split(np.array(scored,dtype=object),4)):
        ds=set(ch.tolist());q=[r for r in traded if r['friday_wib'] in ds];blocks[f'B{i+1}']={'scored_fridays':len(ds),**stats(q)}
    good=sum(v['n']>=5 and v['wr'] is not None and v['wr']>=.65 and v['pnl']>0 for v in blocks.values());total_integrity=integrity+leak
    ok=bool(s['n']>=30 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1.30 and good>=3 and total_integrity==0)
    cal=calibration(top);out={'protocol':'C7B','joined_rows':len(df),'fridays':len(dates),'warmup':WARMUP,'oos_scored':len(top),'threshold':THRESH,'selected':s,'coverage_pct':100*len(traded)/len(top) if top else 0.,'blocks':blocks,'qualifying_blocks':good,'calibration':cal,'integrity':{'source_or_alignment':integrity,'training_leak':leak,'total':total_integrity},'features':FEATURES,'verdict':'BTC_FRIDAY_C7B_PREMIUM_AI_80_CANDIDATE' if ok else 'REJECT_C7B_PREMIUM_AI_IDENTIFIER'}
    pd.DataFrame(top).to_csv(OUT_CSV,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    F=lambda x,d=2:'-' if x is None else f'{x:.{d}f}';md=['# BTC Friday C7B — Premium-Augmented Selective Walk-Forward AI Result','',f"**Verdict: {out['verdict']}**",'',f"Joined rows **{len(df)}**; Fridays **{len(dates)}**; pseudo-OOS scored **{len(top)}**; fixed p>=0.80 trades **{s['n']}** ({F(out['coverage_pct'])}% coverage).",f"Integrity violations **{total_integrity}**.",'','## Selected pseudo-OOS trades','','| Trades | Wins | WR | PnL | Exp/trade | PF |','|---:|---:|---:|---:|---:|---:|',f"| {s['n']} | {s['wins']} | {F(100*s['wr'] if s['wr'] is not None else None)}% | ${F(s['pnl'])} | ${F(s['exp'],3)} | {F(s['pf'],3)} |",'','## Calibration','','| Bucket | Fridays | Wins | WR | Mean confidence | PnL |','|---|---:|---:|---:|---:|---:|']
    for k,v in cal.items():md.append(f"| {k} | {v['n']} | {v['wins']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | {F(100*v['mean_confidence'] if v['mean_confidence'] is not None else None)}% | ${F(v['pnl'])} |")
    md+=['','## OOS blocks','','| Block | Scored | Trades | Wins | WR | PnL |','|---|---:|---:|---:|---:|---:|']
    for k,v in blocks.items():md.append(f"| {k} | {v['scored_fridays']} | {v['n']} | {v['wins']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | ${F(v['pnl'])} |")
    md+=['',f"Promotion-quality blocks: **{good}/4**.",'','No lowering p<0.80, model tuning, premium lookback tuning, direction rescue, or TP/SL rescue is authorized.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
