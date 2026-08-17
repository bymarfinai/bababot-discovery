#!/usr/bin/env python3
"""Saturday T-Method S5.2D — Pre-Warning Latent Runner Immunity Atlas.

Research only; live BBC untouched. No management action is applied.

Frozen cohort: the exact 43 FLOW_EMA_PROTECT warnings from S5.2B.
Question: BEFORE the warning is acted on, can causal state distinguish the 19
warnings that later become >=+0.80 deep runners from the 24 true nondeep warnings?

No threshold sweep. Continuous features are compared by medians and rank AUC in
full/discovery/validation. A feature is only called directionally stable when the
same deep-vs-nondeep direction appears in both chronology halves.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s52b_selective_runner_protect as b52

OUT=Path(os.getenv('S52D_OUT','s52d_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83

FEATURES=[
 'time_to05_min','hinge_taker','hinge_ema_dist','hinge_ema_slope60',
 'warning_min','hinge_to_warning_min','warning_progress','warning_post_taker',
 'warning_ema20_dist','warning_ema20_slope60','warning_ema7_dist','warning_ema7_slope60',
 'prewarning_mfe','prewarning_mae','posthinge_max_close_progress','posthinge_min_close_progress',
 'posthinge_recent15_taker','posthinge_pos_taker_frac','posthinge_ema7_above_frac',
 'posthinge_ema20_above_frac','rebuild04_count','rebuild05_count'
]


def rank_auc(x,y):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=bool)
    m=np.isfinite(x); x=x[m]; y=y[m]
    if y.sum()==0 or (~y).sum()==0:return np.nan
    r=pd.Series(x).rank(method='average').to_numpy()
    n1=y.sum(); n0=(~y).sum()
    return float((r[y].sum()-n1*(n1+1)/2)/(n1*n0))


def slope60(k,bar_t,col):
    old_t=bar_t-pd.Timedelta(minutes=60)
    if old_t not in k.index:return np.nan
    old=float(k.loc[old_t,col]); cur=float(k.loc[bar_t,col])
    return cur/old-1 if old else np.nan


def event_features(k,t,tr,h05,ev,mem):
    d=pd.Timestamp(ev['decision_t'])
    # All bars strictly before warning decision are completed and causal.
    bars=k[(k.index>=t)&(k.index<d)]
    post=k[(k.index>=h05)&(k.index<d)] if h05 is not None else k.iloc[0:0]
    last_t=d-pd.Timedelta(minutes=5)
    last=k.loc[last_t]
    recent=post.tail(3).taker_imb.to_numpy(dtype=float) if len(post) else np.array([])
    posfrac=float((post.taker_imb>0).mean()) if len(post) else np.nan
    ema7frac=float((post.close>post.ema7).mean()) if len(post) else np.nan
    ema20frac=float((post.close>post.ema20).mean()) if len(post) else np.nan
    closes=post.close.to_numpy(dtype=float)/tr.entry-1 if len(post) else np.array([])
    return {
      'time_to05_min': np.nan if h05 is None else (h05-t).total_seconds()/60,
      'hinge_taker': float(mem.get('hinge_taker',np.nan)),
      'hinge_ema_dist': float(mem.get('hinge_ema_dist',np.nan)),
      'hinge_ema_slope60': float(mem.get('hinge_ema_slope60',np.nan)),
      'warning_min': (d-t).total_seconds()/60,
      'hinge_to_warning_min': np.nan if h05 is None else (d-h05).total_seconds()/60,
      'warning_progress': float(ev['decision_open']/tr.entry-1),
      'warning_post_taker': float(ev['post_taker']),
      'warning_ema20_dist': float(ev['decision_open']/float(ev['ema20'])-1),
      'warning_ema20_slope60': slope60(k,last_t,'ema20'),
      'warning_ema7_dist': float(ev['decision_open']/float(last.ema7)-1),
      'warning_ema7_slope60': slope60(k,last_t,'ema7'),
      'prewarning_mfe': float(bars.high.max()/tr.entry-1) if len(bars) else np.nan,
      'prewarning_mae': float(1-bars.low.min()/tr.entry) if len(bars) else np.nan,
      'posthinge_max_close_progress': float(np.max(closes)) if len(closes) else np.nan,
      'posthinge_min_close_progress': float(np.min(closes)) if len(closes) else np.nan,
      'posthinge_recent15_taker': float(np.nanmean(recent)) if len(recent) else np.nan,
      'posthinge_pos_taker_frac': posfrac,
      'posthinge_ema7_above_frac': ema7frac,
      'posthinge_ema20_above_frac': ema20frac,
      'rebuild04_count': int((closes>=.004).sum()) if len(closes) else 0,
      'rebuild05_count': int((closes>=.005).sum()) if len(closes) else 0,
    }


def comp(df,feat,period,mask):
    g=df[mask].copy(); de=g[g.eventual_deep]; nd=g[~g.eventual_deep]
    md=float(de[feat].median()) if len(de) and de[feat].notna().any() else np.nan
    mn=float(nd[feat].median()) if len(nd) and nd[feat].notna().any() else np.nan
    auc=rank_auc(g[feat].to_numpy(),g.eventual_deep.to_numpy())
    direction='DEEP_HIGH' if np.isfinite(md) and np.isfinite(mn) and md>mn else ('DEEP_LOW' if np.isfinite(md) and np.isfinite(mn) and md<mn else 'TIE')
    return {'feature':feat,'period':period,'n':len(g),'deep_n':len(de),'nondeep_n':len(nd),'deep_median':md,'nondeep_median':mn,'auc_deep_high':auc,'direction':direction}


def catrow(df,label,mask):
    g=df[mask]; d=g[g.idx<SPLIT]; v=g[g.idx>=SPLIT]
    def r(x):return float(x.eventual_deep.mean()) if len(x) else np.nan
    return {'state':label,'n':len(g),'deep_rate':r(g),'disc_n':len(d),'disc_deep_rate':r(d),'val_n':len(v),'val_deep_rate':r(v)}


def main():
    k=s50.load_klines(); k['ema7']=k['close'].ewm(span=7,adjust=False).mean()
    f=s50.load_funding(); entries=s50.saturday_entries(k); trades=[s50.simulate(k,f,t) for t in entries]
    rows=[]
    for i,(t,tr) in enumerate(zip(entries,trades)):
        pre=a50.pre_context(k,t); s240=a50.state240(k,t,tr); base_pnl=a50.a719_pnl(k,f,t,tr,s240); base_exit=b52.a719_exit_time(t,tr,s240)
        h05,h08=a52.first_hinges(k,t,tr)
        mem=a52.prehinge_memory(k,t,tr,h05) if h05 is not None else {'prior_failure':False,'hinge_taker':np.nan,'hinge_ema_dist':np.nan,'hinge_ema_slope60':np.nan}
        ev=b52.first_action_event(k,t,tr,base_exit,h05,bool(mem.get('prior_failure',False)),mem.get('hinge_taker',np.nan),adaptive=False)
        if ev is None:continue
        pp,reason,_,_=b52.protected_pnl(k,f,t,tr,base_exit,base_pnl,ev)
        r={'idx':i,'date':tr.date,'pre_state':pre['pre_state'],'pre_score':pre['pre_stretch_score'],
           'prior_failure':bool(mem.get('prior_failure',False)),'a719_pnl':float(base_pnl),'protect_pnl':float(pp),'protect_delta':float(pp-base_pnl),
           'eventual_deep':bool(h08 is not None),'protect_reason':reason}
        r.update(event_features(k,t,tr,h05,ev,mem)); rows.append(r)
    df=pd.DataFrame(rows).sort_values('idx').reset_index(drop=True)
    # Frozen parity from S5.2B/C.
    if len(df)!=43 or (int((df.idx<SPLIT).sum()),int((df.idx>=SPLIT).sum()))!=(28,15):raise RuntimeError('43-event D/V parity fail')
    if int(df.eventual_deep.sum())!=19 or int((~df.eventual_deep).sum())!=24:raise RuntimeError('deep/nondeep parity fail')
    if int((df.eventual_deep&(df.protect_delta<0)).sum())!=15:raise RuntimeError('damaged deep parity fail')
    if abs(df.loc[df.eventual_deep,'protect_delta'].sum()+81.5693647)>.02:raise RuntimeError('deep delta parity fail')
    if abs(df.loc[~df.eventual_deep,'protect_delta'].sum()-29.2215077)>.02:raise RuntimeError('nondeep delta parity fail')
    df.to_csv(OUT/'s52d_warning_features.csv',index=False)
    comps=[]
    masks={'full':np.ones(len(df),dtype=bool),'disc':df.idx<SPLIT,'val':df.idx>=SPLIT}
    for feat in FEATURES:
        for p,m in masks.items():comps.append(comp(df,feat,p,m))
    c=pd.DataFrame(comps)
    # Summarize stability without choosing a trading threshold.
    stab=[]
    for feat in FEATURES:
        q=c[c.feature.eq(feat)].set_index('period')
        dd=q.loc['disc']; vv=q.loc['val']; ff=q.loc['full']
        same=dd.direction==vv.direction and dd.direction!='TIE'
        # Informational strength only; no action promotion.
        disc_sep=abs(float(dd.auc_deep_high)-.5) if np.isfinite(dd.auc_deep_high) else np.nan
        val_sep=abs(float(vv.auc_deep_high)-.5) if np.isfinite(vv.auc_deep_high) else np.nan
        stab.append({'feature':feat,'full_auc':ff.auc_deep_high,'disc_auc':dd.auc_deep_high,'val_auc':vv.auc_deep_high,'disc_direction':dd.direction,'val_direction':vv.direction,'same_direction':bool(same),'min_half_separation':float(min(disc_sep,val_sep)) if np.isfinite(disc_sep) and np.isfinite(val_sep) else np.nan})
    st=pd.DataFrame(stab).sort_values(['same_direction','min_half_separation'],ascending=[False,False]); st.to_csv(OUT/'s52d_feature_stability.csv',index=False)
    cats=[]
    cats += [catrow(df,'PRE_PULLBACK',df.pre_state.eq('PULLBACK')),catrow(df,'PRE_NORMAL',df.pre_state.eq('NORMAL')),catrow(df,'PRE_STRETCHED',df.pre_state.eq('STRETCHED'))]
    cats += [catrow(df,'PRIOR_FAILURE',df.prior_failure),catrow(df,'CLEAN',~df.prior_failure)]
    cats += [catrow(df,'HINGE_TAKER_POS',df.hinge_taker>0),catrow(df,'HINGE_TAKER_NONPOS',df.hinge_taker<=0)]
    cats += [catrow(df,'WARN_EMA20_SLOPE_POS',df.warning_ema20_slope60>0),catrow(df,'WARN_EMA20_SLOPE_NONPOS',df.warning_ema20_slope60<=0)]
    cats += [catrow(df,'WARN_EMA7_SLOPE_POS',df.warning_ema7_slope60>0),catrow(df,'WARN_EMA7_SLOPE_NONPOS',df.warning_ema7_slope60<=0)]
    cat=pd.DataFrame(cats); cat.to_csv(OUT/'s52d_native_states.csv',index=False)
    summary={'events':len(df),'disc':int((df.idx<SPLIT).sum()),'val':int((df.idx>=SPLIT).sum()),'deep':int(df.eventual_deep.sum()),'nondeep':int((~df.eventual_deep).sum()),'stability':st.to_dict(orient='records'),'native_states':cat.to_dict(orient='records')}
    (OUT/'s52d_summary.json').write_text(json.dumps(summary,indent=2,default=float))
    lines=['# BTC Temporal Saturday T-Method S5.2D — Pre-Warning Latent Runner Immunity Atlas','', '**Status:** COMPLETE — FORENSIC ONLY; NO IMMUNITY RULE PROMOTED','**Research only:** live BBC untouched','', '## Frozen parity',f'- Warning cohort: **{len(df)}** = 28 discovery / 15 validation',f'- Latent future-deep: **{int(df.eventual_deep.sum())}**; true nondeep: **{int((~df.eventual_deep).sum())}**','- All features are known no later than the warning decision-open.','', '## Continuous feature stability','| Feature | Full AUC | Disc AUC | Val AUC | D direction | V direction | Same direction | Min half separation |','|---|---:|---:|---:|---|---|---:|---:|']
    for _,r in st.iterrows():lines.append(f"| {r.feature} | {r.full_auc:.3f} | {r.disc_auc:.3f} | {r.val_auc:.3f} | {r.disc_direction} | {r.val_direction} | {'YES' if r.same_direction else 'NO'} | {r.min_half_separation:.3f} |")
    lines += ['', '## Native causal states','| State | N | Deep rate | D N/rate | V N/rate |','|---|---:|---:|---:|---:|']
    for _,r in cat.iterrows():
        def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.1f}%'
        lines.append(f"| {r.state} | {int(r.n)} | {pct(r.deep_rate)} | {int(r.disc_n)}/{pct(r.disc_deep_rate)} | {int(r.val_n)}/{pct(r.val_deep_rate)} |")
    lines += ['', '## Guardrail','- Future-deep is an outcome label only; no feature threshold was optimized.', '- A usable immunity rule would need the same separation direction in discovery and validation and enough support in both halves.', '- This atlas does not alter A7.19, A7.26, or S5.2B execution.']
    (OUT/'S5.2D_CHECKPOINT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=float))

if __name__=='__main__':main()
