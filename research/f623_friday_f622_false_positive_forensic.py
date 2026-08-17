#!/usr/bin/env python3
"""F6.23 — Friday F6.22 false-positive winner vs true low-giveback forensic.

FORENSIC ONLY. No management rule tuning/promotion. Live BBC untouched.
Frozen stack and F6.22 rule remain unchanged.

Question:
Among trades that causally triggered F6.22 PERSISTENT_FAILURE_65, why did
7 eventual parent winners recover while 5 low-giveback parent losses truly fail?

Cohorts are frozen from F6.22 action set:
- TRUE_LOW_FAILURE: F6.22 acted, parent pnl <= 0, parent MFE >= +0.5R and < +1R. Expected N=5.
- FALSE_POS_WINNER: F6.22 acted, parent pnl > 0. Expected N=7.
- The 2 acted high-giveback losses are excluded from the primary comparison.

All features are causal and available at/before the fixed +65m decision. No
post-decision recovery/MFE/final outcome is used as a feature. Outcomes are
labels only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f620_friday_failure_to_accelerate_management as f620
import f622_friday_persistent_failure65_management as f622

OUT=Path(os.getenv('F623_OUT','f623_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL


def auc(y,x):
    y=np.asarray(y,dtype=int); x=np.asarray(x,dtype=float)
    ok=np.isfinite(x); y=y[ok]; x=x[ok]
    p=x[y==1]; n=x[y==0]
    if len(p)==0 or len(n)==0:return np.nan
    s=0.0
    for a in p:
        s += float(np.sum(a>n)) + .5*float(np.sum(a==n))
    return s/(len(p)*len(n))


def slope(v):
    a=np.asarray(v,dtype=float); ok=np.isfinite(a)
    if ok.sum()<2:return np.nan
    xx=np.arange(len(a),dtype=float)[ok]
    return float(np.polyfit(xx,a[ok],1)[0])


def longest_true(a):
    best=cur=0
    for z in a:
        if bool(z):cur+=1;best=max(best,cur)
        else:cur=0
    return int(best)


def cross_up(a):
    a=np.asarray(a,dtype=bool)
    return int(np.sum((~a[:-1]) & a[1:])) if len(a)>1 else 0


def safe_div(a,b):
    return float(a/b) if np.isfinite(a) and np.isfinite(b) and abs(b)>1e-12 else np.nan


def pre_context(k,tr):
    """Strictly pre-entry 1h/2h/24h structure."""
    t=tr.entry_t; e=float(tr.entry)
    out={}
    for mins in (60,120):
        w=k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=mins))]
        if len(w)!=mins//5:continue
        hi=float(w.high.max()); lo=float(w.low.min()); op=float(w.iloc[0].open)
        rng=hi-lo
        out[f'pre{mins}_ret']=float(w.iloc[-1].close/op-1)
        out[f'pre{mins}_range_pct']=float(hi/lo-1) if lo>0 else np.nan
        out[f'pre{mins}_entry_range_pos']=safe_div(e-lo,rng)
        out[f'pre{mins}_retr_from_high']=safe_div(hi-e,rng)
        q=float(w.quote_volume.sum()); tb=float(w.taker_buy_quote.sum())
        out[f'pre{mins}_taker']=float(2*tb/q-1) if q>0 else np.nan
        out[f'pre{mins}_dist_low_pct']=float(e/lo-1) if lo>0 else np.nan
        out[f'pre{mins}_dist_high_pct']=float(hi/e-1) if e>0 else np.nan
    prior=k[(k.index<t)&(k.index>=t-pd.Timedelta(hours=24))].copy()
    if len(prior)>=240:
        vol12=prior.quote_volume.rolling(12).sum().dropna()
        rng12=(prior.high.rolling(12).max()/prior.low.rolling(12).min()-1).dropna()
        last12=prior.iloc[-12:]
        curv=float(last12.quote_volume.sum()); curr=float(last12.high.max()/last12.low.min()-1)
        out['pre60_volume_vs_24h_med']=safe_div(curv,float(vol12.median())) if len(vol12) else np.nan
        out['pre60_range_vs_24h_med']=safe_div(curr,float(rng12.median())) if len(rng12) else np.nan
    return out


def decision_features(k,tr,st):
    ht=st['hit_t']; dt=st['decision_t']; e=float(tr.entry)
    w=k[(k.index>=ht)&(k.index<dt)].copy()
    if len(w)!=13:return None
    close=w.close.astype(float).to_numpy(); high=w.high.astype(float).to_numpy(); low=w.low.astype(float).to_numpy()
    ema7=w.ema7.astype(float).to_numpy(); ema20=w.ema20.astype(float).to_numpy(); tak=w.taker_imb.astype(float).to_numpy()
    qv=w.quote_volume.astype(float).to_numpy(); vol=w.volume.astype(float).to_numpy()
    progress=(close/e-1)/R
    half=progress>=.5; above7=close>=ema7; above20=close>=ema20
    ht_minutes=float((ht-tr.entry_t)/pd.Timedelta(minutes=1))

    # Maximum observed price/progress only inside the causal window up to decision.
    max_i=int(np.argmax(high)); max_px=float(high[max_i]); max_r=float((max_px/e-1)/R)
    decision_close=float(close[-1]); decision_r=float(progress[-1])
    impulse=max_px-e; retr=max_px-decision_close

    # Milestone loss/rebuild based on completed closes after first +0.5R hit.
    lost=np.where(~half)[0]
    if len(lost):
        li=int(lost[0]); rebuild=bool(np.any(half[li+1:])); rebuild_n=cross_up(half[li:])
    else:
        li=-1; rebuild=False; rebuild_n=0

    # Flow recovery attempts and late participation.
    pos=tak>0
    neg=np.where(tak<0)[0]
    flow_recover=False
    if len(neg):flow_recover=bool(np.any(pos[int(neg[0])+1:]))

    # Entry-to-halfR initial impulse quality, using completed bars from entry through hit bar.
    initial=k[(k.index>=tr.entry_t)&(k.index<=ht)].copy()
    iq=float(initial.quote_volume.sum()) if len(initial) else np.nan
    itak=np.nan
    if len(initial):
        qq=float(initial.quote_volume.sum()); bb=float(initial.taker_buy_quote.sum())
        itak=float(2*bb/qq-1) if qq>0 else np.nan
    pre60=k[(k.index<tr.entry_t)&(k.index>=tr.entry_t-pd.Timedelta(minutes=60))]
    preq=float(pre60.quote_volume.sum()) if len(pre60)==12 else np.nan

    return {
      'time_to_halfR_min':ht_minutes,
      'predecision_max_progress_r':max_r,
      'minutes_halfR_to_predecision_max':float(max_i*5),
      'decision_progress_r':decision_r,
      'retained_vs_max':safe_div(max(decision_r,0),max_r) if max_r>0 else np.nan,
      'impulse_retrace_fraction':safe_div(retr,impulse),
      'progress_mean_r':float(np.mean(progress)),
      'progress_slope':slope(progress),
      'progress_last3_slope':slope(progress[-3:]),
      'bars_close_ge_halfR':int(np.sum(half)),
      'frac_close_ge_halfR':float(np.mean(half)),
      'longest_below_halfR':longest_true(~half),
      'halfR_rebuild_after_loss':float(rebuild),
      'halfR_rebuild_count':float(rebuild_n),
      'ema7_reclaims':float(cross_up(above7)),
      'ema20_reclaims':float(cross_up(above20)),
      'longest_below_ema7':float(longest_true(~above7)),
      'longest_below_ema20':float(longest_true(~above20)),
      'frac_below_ema7':float(np.mean(~above7)),
      'frac_below_ema20':float(np.mean(~above20)),
      'taker_mean':float(np.mean(tak)),
      'taker_median':float(np.median(tak)),
      'taker_first4_mean':float(np.mean(tak[:4])),
      'taker_middle5_mean':float(np.mean(tak[4:9])),
      'taker_last4_mean':float(np.mean(tak[-4:])),
      'taker_last2_mean':float(np.mean(tak[-2:])),
      'taker_slope':slope(tak),
      'frac_taker_positive':float(np.mean(pos)),
      'flow_positive_after_negative':float(flow_recover),
      'quote_volume_first4':float(np.sum(qv[:4])),
      'quote_volume_last4':float(np.sum(qv[-4:])),
      'late_vs_early_quote_volume':safe_div(float(np.sum(qv[-4:])),float(np.sum(qv[:4]))),
      'quote_volume_slope':slope(qv),
      'base_volume_slope':slope(vol),
      'initial_impulse_quote_volume':iq,
      'initial_impulse_volume_vs_pre60':safe_div(iq,preq),
      'initial_impulse_taker':itak,
      'decision_dist_ema20_pct':float(decision_close/float(ema20[-1])-1),
      'decision_ema7_vs_ema20_pct':float(float(ema7[-1])/float(ema20[-1])-1),
      'final3_higher_low':float(len(low)>=3 and low[-2]>low[-3] and low[-1]>low[-2]),
      'higher_low_fraction':float(np.mean(low[1:]>low[:-1])) if len(low)>1 else np.nan,
    }


def loo_strength(g,feat):
    vals=[]
    for j in range(len(g)):
        z=g.drop(g.index[j]); A=auc(z.y,z[feat])
        if np.isfinite(A):vals.append(max(A,1-A))
    return (float(min(vals)),float(np.median(vals))) if vals else (np.nan,np.nan)


def main():
    k=f517.load_klines(); days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    rows=[]; parents=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        st=f622.persistent_state(k,tr)
        pnl,layer,_=f622.apply(k,t,tr,st)
        acted=(layer==f622.RULE)
        row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'mfe_r':float(tr.mfe/R),
             'f622_acted':bool(acted),'f622_managed_pnl':float(pnl)}
        if acted and st is not None:
            row.update(pre_context(k,tr))
            z=decision_features(k,tr,st)
            if z:row.update(z)
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f623_rows.csv',index=False)

    loss=df[(df.f622_acted)&(df.parent_pnl<=0)&(df.mfe_r>=.5)&(df.mfe_r<1)].copy()
    win=df[(df.f622_acted)&(df.parent_pnl>0)].copy()
    if len(loss)!=5 or len(win)!=7:
        raise AssertionError(f'F6.22 cohort parity expected loss=5 win=7; got {len(loss)} {len(win)}')

    excluded_high=df[(df.f622_acted)&(df.parent_pnl<=0)&(df.mfe_r>=1)&(df.mfe_r<2)]
    idcols={'i','period','date','parent_pnl','parent_win','mfe_r','f622_acted','f622_managed_pnl'}
    feats=[c for c in df.columns if c not in idcols and pd.api.types.is_numeric_dtype(df[c])]
    rec=[]
    for f in feats:
        a=loss[['period',f]].dropna(); b=win[['period',f]].dropna()
        if len(a)<3 or len(b)<3:continue
        z=pd.concat([a.assign(y=1),b.assign(y=0)],ignore_index=True)
        A=auc(z.y,z[f]); d=z[z.period=='discovery']; v=z[z.period=='validation']
        AD=auc(d.y,d[f]); AV=auc(v.y,v[f]); loomin,loomed=loo_strength(z,f)
        rec.append({'feature':f,'n_loss':len(a),'n_win':len(b),'auc_loss_high':A,
                    'strength':max(A,1-A) if np.isfinite(A) else np.nan,
                    'direction':'higher_failure' if np.isfinite(A) and A>=.5 else 'lower_failure',
                    'auc_D':AD,'auc_V':AV,'median_failure':float(a[f].median()),'median_false_win':float(b[f].median()),
                    'loo_min_strength':loomin,'loo_median_strength':loomed})
    atlas=pd.DataFrame(rec).sort_values('strength',ascending=False); atlas.to_csv(OUT/'f623_feature_atlas.csv',index=False)

    # Compact shortlist: strong full-sample effect, D same direction, V same direction when defined,
    # and LOO does not collapse. V is tiny (1 failure/2 winners), so mark rather than overclaim.
    def same_dir(A,B):
        return np.isfinite(A) and np.isfinite(B) and ((A>=.5)==(B>=.5))
    short=[]
    for _,r in atlas.iterrows():
        ok=(r.strength>=.70 and same_dir(r.auc_loss_high,r.auc_D) and
            (not np.isfinite(r.auc_V) or same_dir(r.auc_loss_high,r.auc_V)) and r.loo_median_strength>=.65)
        if ok:short.append(r.to_dict())

    out={'cohorts':{'true_low_failures':len(loss),'false_positive_winners':len(win),'excluded_high_givebacks':len(excluded_high),
                    'loss_D':int((loss.period=='discovery').sum()),'loss_V':int((loss.period=='validation').sum()),
                    'win_D':int((win.period=='discovery').sum()),'win_V':int((win.period=='validation').sum())},
         'shortlist':short[:12],'top_features':atlas.head(20).to_dict('records'),
         'case_rows':pd.concat([loss.assign(label='TRUE_LOW_FAILURE'),win.assign(label='FALSE_POS_WINNER')])[
             ['date','period','label','parent_pnl','mfe_r','time_to_halfR_min','predecision_max_progress_r','decision_progress_r','halfR_rebuild_count','longest_below_ema7','taker_first4_mean','taker_last4_mean','initial_impulse_taker','pre120_entry_range_pos','pre120_retr_from_high','late_vs_early_quote_volume']
         ].to_dict('records')}
    (OUT/'f623_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.23 — F6.22 False-Positive Winner Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO EXIT RULE TUNED/PROMOTED.**',
        '**Live BBC untouched; frozen stack and F6.22 unchanged.**','',
        '## Frozen cohorts',f"- true low failures: **{len(loss)}** (D {(loss.period=='discovery').sum()} / V {(loss.period=='validation').sum()})",
        f"- false-positive eventual winners: **{len(win)}** (D {(win.period=='discovery').sum()} / V {(win.period=='validation').sum()})",
        f"- excluded high givebacks: **{len(excluded_high)}**",'',
        '## Strong causal separators']
    if not short:md.append('- none pass the compact full/D/V + LOO screen')
    else:
        for r in short[:12]:
            md.append(f"- {r['feature']}: strength {r['strength']:.3f}, AUC D/V {r['auc_D']:.3f}/{r['auc_V']:.3f}; {r['direction']}; median failure {r['median_failure']:.4f} vs false-win {r['median_false_win']:.4f}; LOO median {r['loo_median_strength']:.3f}")
    md += ['','## Top feature atlas']
    for _,r in atlas.head(12).iterrows():
        md.append(f"- {r.feature}: strength {r.strength:.3f}, AUC {r.auc_loss_high:.3f}, D/V {r.auc_D:.3f}/{r.auc_V:.3f}, failure {r.median_failure:.4f}, false-win {r.median_false_win:.4f}")
    md += ['','## Guardrail','Only information known at/before the fixed F6.22 +65m decision is used as a feature. Final winner/loss outcome is label-only. Validation contains only one true low failure, so V direction is informative but not sufficient proof. Any F6.24 action rule must be predeclared from a small interpretable subset; do not threshold-sweep this 12-case cohort.']
    (OUT/'F6.23_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
