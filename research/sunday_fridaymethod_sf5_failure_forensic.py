#!/usr/bin/env python3
"""Sunday Friday-method SF5 — failure-to-develop forensic.

Mirrors Friday F6.25 methodology on the reset Sunday16 parent.
No management rule is optimized or promoted here.

Target cohort: parent-negative Sunday SELL trades whose total MFE never reaches +0.5R,
where R = parent SL 1.4%, so +0.5R = +0.70% favorable.
Controls at each checkpoint:
 A) all eventual winners still alive;
 B) HARD slow-start winners still alive whose MFE by that checkpoint is also <0.5R.

Causal checkpoints: +2h, +4h, +6h, matching Sunday path anatomy.
Discovery first83 / validation last56 are robustness slices only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17b_sunday16_loss_prevday_forensics_exactfunding as sun17b

sun17=sun17b.base
sun17.funding_short=sun17b.exact_sun16_funding
OUT=Path(os.getenv('SUNFM5_OUT','sunfm5_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83; R=0.014; CHECKPOINTS=[120,240,360]


def auc_loss_high(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    cmp=a[:,None]-b[None,:]
    return float((np.sum(cmp>0)+0.5*np.sum(cmp==0))/cmp.size)


def sep(loss,ctrl,col):
    a=auc_loss_high(loss[col].to_numpy(float),ctrl[col].to_numpy(float))
    return {'auc_loss_high':a,'strength':max(a,1-a) if np.isfinite(a) else np.nan,
            'direction':'higher=loss' if np.isfinite(a) and a>=.5 else 'lower=loss',
            'loss_median':float(loss[col].median()) if len(loss) else np.nan,
            'control_median':float(ctrl[col].median()) if len(ctrl) else np.nan,
            'n_loss':int(loss[col].notna().sum()),'n_control':int(ctrl[col].notna().sum())}


def stable(target,ctrl,features):
    rows=[]
    for col in features:
        f=sep(target,ctrl,col); d=sep(target[target.i<DISC_N],ctrl[ctrl.i<DISC_N],col); v=sep(target[target.i>=DISC_N],ctrl[ctrl.i>=DISC_N],col)
        same=f['direction']==d['direction']==v['direction']
        score=min(f['strength'],d['strength'],v['strength']) if same and all(np.isfinite([f['strength'],d['strength'],v['strength']])) else 0.0
        rows.append({'feature':col,'same_direction':same,'min_strength':score,'full':f,'D':d,'V':v})
    rows.sort(key=lambda x:(x['same_direction'],x['min_strength']),reverse=True)
    return rows


def pre(k,t,tr):
    x=k[(k.index<t)&(k.index>=t-pd.Timedelta(hours=6))]
    x2=k[(k.index<t)&(k.index>=t-pd.Timedelta(hours=2))]
    last=k.loc[t-pd.Timedelta(minutes=5)]
    def tak(z):
        q=float(z.quote_volume.sum()); b=float(z.taker_buy_quote.sum()); return 2*b/q-1 if q>0 else np.nan
    hi=float(x2.high.max());lo=float(x2.low.min()); rg=hi-lo
    ep=float(tr['entry'])
    return {
      'pre_range_pos2h':(ep-lo)/rg if rg>0 else np.nan,
      'pre_taker2h':tak(x2),'pre_taker6h':tak(x),
      'pre_close_vs_ema7':float(last.close)/float(last.ema7)-1,
      'pre_close_vs_ema20':float(last.close)/float(last.ema20)-1,
      'pre_ema_spread':float(last.ema7)/float(last.ema20)-1,
      'pre_ret2h':float(last.close)/float(x2.iloc[0].open)-1 if len(x2) else np.nan,
      'pre_ret6h':float(last.close)/float(x.iloc[0].open)-1 if len(x) else np.nan,
    }


def cp(k,tr,m):
    t=tr['entry_t']; dt=t+pd.Timedelta(minutes=m)
    if tr['exit_t']<=dt:return None
    x=k[(k.index>=t)&(k.index<dt)]
    if len(x)!=m//5:return None
    last=x.iloc[-1]; tail=x.iloc[-6:]; q=float(x.quote_volume.sum()); b=float(x.taker_buy_quote.sum())
    q2=float(tail.quote_volume.sum()); b2=float(tail.taker_buy_quote.sum())
    ep=float(tr['entry']); closes=x.close.astype(float).to_numpy(); opens=x.open.astype(float).to_numpy()
    return {
      f'cp{m}_progress_r':(1-float(last.close)/ep)/R,
      f'cp{m}_mfe_r':(1-float(x.low.min())/ep)/R,
      f'cp{m}_mae_r':(float(x.high.max())/ep-1)/R,
      f'cp{m}_taker':2*b/q-1 if q>0 else np.nan,
      f'cp{m}_tail30_taker':2*b2/q2-1 if q2>0 else np.nan,
      f'cp{m}_close_vs_ema7_r':(float(last.close)/float(last.ema7)-1)/R,
      f'cp{m}_close_vs_ema20_r':(float(last.close)/float(last.ema20)-1)/R,
      f'cp{m}_above7':float(last.close>=last.ema7),
      f'cp{m}_above20':float(last.close>=last.ema20),
      f'cp{m}_green_frac':float(np.mean(closes>opens)),
      f'cp{m}_last3_slope_r':((closes[-1]-closes[-3])/ep/2/R) if len(closes)>=3 else np.nan,
    }


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun17.entries(k); trs=[sun17.simulate_parent(k,f,t) for t in es]
    rows=[]
    for i,tr in enumerate(trs):
        r={'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),'win':bool(tr['pnl']>0),
           'pnl':float(tr['pnl']),'reason':tr['reason'],'mfe_r':float(tr['mfe']/R),'mae_r':float(tr['mae']/R),**pre(k,tr['entry_t'],tr)}
        for m in CHECKPOINTS:
            z=cp(k,tr,m);r[f'cp{m}_alive']=bool(z is not None)
            if z:r.update(z)
        rows.append(r)
    df=pd.DataFrame(rows); df.to_csv(OUT/'sunfm5_rows.csv',index=False)
    if len(df)!=139 or int(df.win.sum())!=66 or abs(df.pnl.sum()-63.599379132074105)>0.25:raise RuntimeError('parent parity fail')
    target=df[(~df.win)&(df.mfe_r<0.5)].copy(); winners=df[df.win].copy()
    pre_features=['pre_range_pos2h','pre_taker2h','pre_taker6h','pre_close_vs_ema7','pre_close_vs_ema20','pre_ema_spread','pre_ret2h','pre_ret6h']
    pre_atlas=stable(target,winners,pre_features)
    cps={}; counts={}
    for m in CHECKPOINTS:
        T=target[target[f'cp{m}_alive']==True]; A=winners[winners[f'cp{m}_alive']==True]
        S=A[A[f'cp{m}_mfe_r']<0.5]
        feats=[f'cp{m}_progress_r',f'cp{m}_mfe_r',f'cp{m}_mae_r',f'cp{m}_taker',f'cp{m}_tail30_taker',
               f'cp{m}_close_vs_ema7_r',f'cp{m}_close_vs_ema20_r',f'cp{m}_above7',f'cp{m}_above20',f'cp{m}_green_frac',f'cp{m}_last3_slope_r']
        cps[str(m)]={'vs_all':stable(T,A,feats),'vs_slow':stable(T,S,feats)}
        counts[str(m)]={'target':len(T),'all_winners':len(A),'slow_winners':len(S)}
    def tops(arr,n=6):return [x for x in arr if x['same_direction']][:n]
    out={'status':'FORENSIC_ONLY_NO_RULE','target_definition':'parent loss with total MFE <0.5R (0.70%)',
         'target':{'n':len(target),'D':int((target.i<DISC_N).sum()),'V':int((target.i>=DISC_N).sum()),'pnl':float(target.pnl.sum()),
                   'SL':int((target.reason=='SL').sum()),'TIMEOUT':int((target.reason=='TIMEOUT').sum()),'median_mfe_r':float(target.mfe_r.median()),'median_mae_r':float(target.mae_r.median())},
         'counts':counts,'top_pre':tops(pre_atlas,8),'top_slow':{m:tops(cps[m]['vs_slow'],8) for m in cps},
         'pre_atlas':pre_atlas,'checkpoint_atlas':cps,
         'guardrail':'Forensic only. Hard slow-start winner control prevents trivial no-movement rules. No action timing or threshold optimized.'}
    (OUT/'sunfm5_summary.json').write_text(json.dumps(out,indent=2,default=str))
    md=['# Sunday Friday-Method SF5 — Failure-to-Develop Forensic','', '**Status: COMPLETE — FORENSIC ONLY; NO RULE PROMOTED.**','',
        f"- Failure-to-develop cohort **{len(target)}** = D {(target.i<DISC_N).sum()} / V {(target.i>=DISC_N).sum()}, aggregate PnL **${target.pnl.sum():+.2f}**.",
        f"- SL/TIMEOUT **{(target.reason=='SL').sum()}/{(target.reason=='TIMEOUT').sum()}**; median MFE **{target.mfe_r.median():.3f}R**, MAE **{target.mae_r.median():.3f}R**.",'',
        '## Top separators vs HARD slow-start winners']
    for m in map(str,CHECKPOINTS):
        md.append(f"### +{int(m)//60}h — target/slow winner {counts[m]['target']}/{counts[m]['slow_winners']}")
        for x in tops(cps[m]['vs_slow'],6):
            q=x['full'];md.append(f"- `{x['feature']}` strength full/D/V **{q['strength']:.3f}/{x['D']['strength']:.3f}/{x['V']['strength']:.3f}**, {q['direction']}; med loss/control {q['loss_median']:.4f}/{q['control_median']:.4f}")
    md += ['', '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF5_FORENSIC.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__':main()
