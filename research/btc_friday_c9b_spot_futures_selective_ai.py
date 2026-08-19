#!/usr/bin/env python3
"""C9B: C6 expanding selective AI augmented with frozen spot/futures features."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

import btc_friday_selective_ai_c6 as c6
import btc_friday_15m_candle_taker_c4 as c4
import btc_friday_c9a_spot_futures_leadlag as c9a

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_C9B_Spot_Futures_Selective_AI_Result.md';OUT_JSON=ROOT/'BTC_Friday_C9B_Spot_Futures_Selective_AI_Result.json';OUT_CSV=ROOT/'BTC_Friday_C9B_Spot_Futures_Selective_AI_Predictions.csv'
WARMUP=52;THRESH=.80;SEED=20260819
NEW=['spot_ret15','spot_ret60','spot_taker_imbalance','spot_taker_delta_vs_prior3','spot_rel_quote_volume_24h','basis','basis_delta15','basis_delta60','lead_spread','lead_z7d','flow_divergence'];FEATURES=c6.FEATURES+NEW

def model():return HistGradientBoostingClassifier(loss='log_loss',learning_rate=.05,max_iter=100,max_depth=3,min_samples_leaf=30,l2_regularization=1.,random_state=SEED)
def pwin(clf,X):
    if 1 not in clf.classes_:return np.zeros(len(X),dtype=float)
    return clf.predict_proba(X)[:,list(clf.classes_).index(1)]
def pf(a):
    gp=sum(v for v in a if v>0);gl=-sum(v for v in a if v<0);return gp/gl if gl>0 else (999. if gp>0 else None)
def stats(rows):
    a=[float(r['actual_pnl']) for r in rows]
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.,'exp':None,'pf':None}
    w=sum(v>0 for v in a);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}

def spot_feature_table():
    f=c4.load15().rename(columns={'open':'f_open','high':'f_high','low':'f_low','close':'f_close','quote_volume':'f_quote_volume','taker_buy_quote':'f_taker_buy_quote'});s=c9a.load_spot();z=f.merge(s,on='ts',how='inner',validate='one_to_one').sort_values('ts').reset_index(drop=True)
    z['spot_ret15']=z.s_close/z.s_open-1.;z['spot_ret60']=z.s_close/z.s_open.shift(3)-1.;z['fut_ret15']=z.f_close/z.f_open-1.
    z['spot_taker_imbalance']=np.where(z.s_quote_volume>0,2*z.s_taker_buy_quote/z.s_quote_volume-1,np.nan);z['fut_taker_imbalance']=np.where(z.f_quote_volume>0,2*z.f_taker_buy_quote/z.f_quote_volume-1,np.nan)
    z['spot_taker_delta_vs_prior3']=z.spot_taker_imbalance-z.spot_taker_imbalance.shift(1).rolling(3,min_periods=3).median();z['spot_rel_quote_volume_24h']=z.s_quote_volume/z.s_quote_volume.shift(1).rolling(96,min_periods=96).median()
    z['basis']=z.f_close/z.s_close-1.;z['basis_delta15']=z.basis-z.basis.shift(1);z['basis_delta60']=z.basis-z.basis.shift(4);z['lead_spread']=z.spot_ret15-z.fut_ret15;z['flow_divergence']=z.spot_taker_imbalance-z.fut_taker_imbalance
    q=z.set_index('ts');ls=q.lead_spread.astype(float);q['lead_z7d']=(ls-ls.rolling('7D',closed='left',min_periods=192).mean())/ls.rolling('7D',closed='left',min_periods=192).std(ddof=0);q['signal_ts']=q.index
    return q[NEW+['signal_ts']].reset_index(drop=True)
def load():
    base,viol=c6.load_rows();sf=spot_feature_table();base['signal_ts']=pd.to_datetime(base.signal_ts,utc=True);z=base.merge(sf,on='signal_ts',how='inner',validate='one_to_one');viol+=int((z.entry_ts<=z.signal_ts).sum());return z.sort_values(['friday_wib','signal_ts']).reset_index(drop=True),viol

def calibration(top):
    out={}
    for name,lo,hi in [('<0.50',-1,.5),('0.50-0.60',.5,.6),('0.60-0.70',.6,.7),('0.70-0.80',.7,.8),('>=0.80',.8,2)]:
        q=[r for r in top if lo<=r['confidence']<hi];out[name]={'n':len(q),'wins':sum(r['actual_win'] for r in q),'wr':(sum(r['actual_win'] for r in q)/len(q) if q else None),'mean_confidence':(float(np.mean([r['confidence'] for r in q])) if q else None),'pnl':sum(r['actual_pnl'] for r in q)}
    return out

def main():
    df,integrity=load();dates=sorted(df.friday_wib.unique());top=[];leak=0
    for ix,day in enumerate(dates[WARMUP:],start=WARMUP):
        tr=df[df.friday_wib.isin(set(dates[:ix]))].copy();te=df[df.friday_wib==day].copy()
        if tr.empty or te.empty:continue
        if max(tr.friday_wib)>=day:leak+=1
        Xtr=tr[FEATURES].copy();Xte=te[FEATURES].copy()
        for f in FEATURES:
            v=pd.to_numeric(Xtr[f],errors='coerce').replace([np.inf,-np.inf],np.nan);med=float(v.median());med=med if math.isfinite(med) else 0.;Xtr[f]=v.fillna(med);Xte[f]=pd.to_numeric(Xte[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med)
        ml=model();ms=model();ml.fit(Xtr,tr.long_win.astype(int));ms.fit(Xtr,tr.short_win.astype(int));pl=pwin(ml,Xte);ps=pwin(ms,Xte);cand=[]
        for j,(_,r) in enumerate(te.iterrows()):
            if pl[j]>=ps[j]:sd='LONG';cf=float(pl[j]);aw=int(r.long_win);ap=float(r.long_pnl)
            else:sd='SHORT';cf=float(ps[j]);aw=int(r.short_win);ap=float(r.short_pnl)
            cand.append({'friday_wib':day,'signal_ts':str(r.signal_ts),'entry_ts':str(r.entry_ts),'direction':sd,'p_long':float(pl[j]),'p_short':float(ps[j]),'confidence':cf,'actual_win':aw,'actual_pnl':ap,'training_fridays':ix,'training_rows':len(tr)})
        cand.sort(key=lambda r:(-r['confidence'],pd.Timestamp(r['signal_ts'])));top.append(cand[0])
    traded=[r for r in top if r['confidence']>=THRESH];s=stats(traded);blocks={};scored=[r['friday_wib'] for r in top]
    for i,ch in enumerate(np.array_split(np.array(scored,dtype=object),4)):
        ds=set(ch.tolist());q=[r for r in traded if r['friday_wib'] in ds];blocks[f'B{i+1}']={'scored_fridays':len(ds),**stats(q)}
    good=sum(v['n']>=5 and v['wr'] is not None and v['wr']>=.65 and v['pnl']>0 for v in blocks.values());total=integrity+leak;ok=bool(s['n']>=30 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1.30 and good>=3 and total==0);cal=calibration(top)
    out={'protocol':'C9B','joined_rows':len(df),'fridays':len(dates),'warmup':WARMUP,'oos_scored':len(top),'threshold':THRESH,'selected':s,'coverage_pct':100*len(traded)/len(top) if top else 0.,'blocks':blocks,'qualifying_blocks':good,'calibration':cal,'integrity':{'source_alignment':integrity,'training_leak':leak,'total':total},'features':FEATURES,'verdict':'BTC_FRIDAY_C9B_SPOT_FUTURES_AI_80_CANDIDATE' if ok else 'REJECT_C9B_SPOT_FUTURES_AI_IDENTIFIER'}
    pd.DataFrame(top).to_csv(OUT_CSV,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');F=lambda x,d=2:'-' if x is None else f'{x:.{d}f}';md=['# BTC Friday C9B — Spot/Futures Selective Walk-Forward AI Result','',f"**Verdict: {out['verdict']}**",'',f"Joined rows **{len(df)}**; Fridays **{len(dates)}**; OOS scored **{len(top)}**; p>=0.80 trades **{s['n']}** ({F(out['coverage_pct'])}% coverage).",f"Integrity **{total}**.",'','## Selected','','| Trades | Wins | WR | PnL | Exp | PF |','|---:|---:|---:|---:|---:|---:|',f"| {s['n']} | {s['wins']} | {F(100*s['wr'] if s['wr'] is not None else None)}% | ${F(s['pnl'])} | ${F(s['exp'],3)} | {F(s['pf'],3)} |",'','## Calibration','','| Bucket | N | Wins | WR | Mean confidence | PnL |','|---|---:|---:|---:|---:|---:|']
    for k,v in cal.items():md.append(f"| {k} | {v['n']} | {v['wins']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | {F(100*v['mean_confidence'] if v['mean_confidence'] is not None else None)}% | ${F(v['pnl'])} |")
    md+=['','## Blocks','','| Block | Scored | Trades | Wins | WR | PnL |','|---|---:|---:|---:|---:|---:|']
    for k,v in blocks.items():md.append(f"| {k} | {v['scored_fridays']} | {v['n']} | {v['wins']} | {F(100*v['wr'] if v['wr'] is not None else None)}% | ${F(v['pnl'])} |")
    md+=['',f"Promotion-quality blocks **{good}/4**.",'','No p<0.80/model/spot-feature/direction/TP-SL rescue is authorized.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
