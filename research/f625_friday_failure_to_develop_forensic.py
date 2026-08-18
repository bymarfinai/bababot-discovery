#!/usr/bin/env python3
"""F6.25 — Friday failure-to-develop / wrong-direction forensic.

Research only; live BBC untouched. No management rule is tuned or promoted.
Frozen Friday layers remain FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.

Primary cohort: latest-stack Friday parent losses whose total parent MFE never
reaches +0.5R. F6.14 found 24 such failures (including the one strict immediate
sink). D3/F6.24 require +1R/+0.5R and therefore should not remove this cohort.

Question: are these failures genuinely distinguishable causally from winners,
and how early? We examine:
1) strictly pre-entry context; and
2) completed-bar path at +5/+10/+15/+30/+60m.

To guard against easy hindsight separation, checkpoint features are compared to:
A) all eventual parent winners alive at that checkpoint; and
B) HARD slow-start winners that are alive and themselves have not yet reached
   +0.5R by that same checkpoint.

No exit threshold, timing sweep, or action PnL optimization is performed.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f614_friday_remaining_loss_anatomy as f614
import f624_friday_context_repair_failure_management as f624

OUT=Path(os.getenv('F625_OUT','f625_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N
CHECKPOINTS=[5,10,15,30,60]


def auc_loss_high(loss_vals,ctrl_vals):
    a=np.asarray(loss_vals,dtype=float); b=np.asarray(ctrl_vals,dtype=float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    # Probability a random loss value exceeds random control; ties count 0.5.
    gt=(a[:,None]>b[None,:]).sum(); eq=(a[:,None]==b[None,:]).sum()
    return float((gt+0.5*eq)/(len(a)*len(b)))


def sep(loss,ctrl,col):
    a=auc_loss_high(loss[col].to_numpy(float),ctrl[col].to_numpy(float))
    return {'auc_loss_high':a,'strength':float(max(a,1-a)) if np.isfinite(a) else np.nan,
            'direction':'higher=loss' if np.isfinite(a) and a>=0.5 else 'lower=loss',
            'loss_median':float(loss[col].median()) if len(loss) and loss[col].notna().any() else np.nan,
            'control_median':float(ctrl[col].median()) if len(ctrl) and ctrl[col].notna().any() else np.nan,
            'n_loss':int(loss[col].notna().sum()),'n_control':int(ctrl[col].notna().sum())}


def pre_context_extra(k,t,tr):
    base=f614.pre_context(k,t,tr)
    def window(minutes): return k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=minutes))]
    def pos(minutes):
        x=window(minutes)
        if x.empty:return (np.nan,np.nan)
        hi=float(x.high.max());lo=float(x.low.min());rg=hi-lo
        if rg<=0:return (np.nan,np.nan)
        return ((float(tr.entry)-lo)/rg,(hi-float(tr.entry))/rg)
    p2,r2=pos(120); p4,r4=pos(240)
    x30=window(30);x60=window(60);x120=window(120)
    last=k.loc[t-pd.Timedelta(minutes=5)]
    rng=max(float(last.high-last.low),1e-12)
    body=abs(float(last.close-last.open));uw=float(last.high-max(last.open,last.close));lw=float(min(last.open,last.close)-last.low)
    def tak(x):
        q=float(x.quote_volume.sum());b=float(x.taker_buy_quote.sum())
        return 2*b/q-1 if q>0 else np.nan
    def slope(col,minutes):
        x=window(minutes)
        if len(x)<2:return np.nan
        return float(x.iloc[-1][col])/float(x.iloc[0][col])-1.0
    return {**base,
        'range_pos2h':p2,'retr_from_high2h':r2,'range_pos4h':p4,'retr_from_high4h':r4,
        'pre_taker30':tak(x30),'pre_taker120':tak(x120),
        'pre_ema7_slope30':slope('ema7',30),'pre_ema20_slope60':slope('ema20',60),
        'pre_last_red':float(last.close<last.open),'pre_last_body_ratio':body/rng,
        'pre_last_upper_wick_ratio':uw/rng,'pre_last_lower_wick_ratio':lw/rng,
    }


def checkpoint_extra(k,t,tr,m):
    dt=t+pd.Timedelta(minutes=m)
    if pd.Timestamp(tr.exit_t)<=dt:return None
    x=k[(k.index>=t)&(k.index<dt)]
    if len(x)!=m//5:return None
    last=x.iloc[-1]
    q=float(x.quote_volume.sum());b=float(x.taker_buy_quote.sum())
    tak=2*b/q-1 if q>0 else np.nan
    tail2=x.iloc[-min(2,len(x)):]
    q2=float(tail2.quote_volume.sum());b2=float(tail2.taker_buy_quote.sum())
    tak2=2*b2/q2-1 if q2>0 else np.nan
    prog=float(last.close)/float(tr.entry)-1.0
    mfe=float(x.high.max())/float(tr.entry)-1.0
    mae=1.0-float(x.low.min())/float(tr.entry)
    closes=x.close.astype(float).to_numpy(); opens=x.open.astype(float).to_numpy()
    highs=x.high.astype(float).to_numpy()
    red_frac=float(np.mean(closes<opens))
    below7=float(last.close<last.ema7); below20=float(last.close<last.ema20)
    if len(closes)>=3:
        y=closes[-3:]/float(tr.entry)-1.0
        slope=float((y[-1]-y[0])/2.0)
    else:slope=np.nan
    lower_high_frac=float(np.mean(np.diff(highs)<0)) if len(highs)>1 else np.nan
    return {
      f'cp{m}_progress_r':prog/R,f'cp{m}_mfe_r':mfe/R,f'cp{m}_mae_r':mae/R,
      f'cp{m}_taker':tak,f'cp{m}_tail2_taker':tak2,
      f'cp{m}_ema7_dist_r':(float(last.close)/float(last.ema7)-1.0)/R,
      f'cp{m}_ema20_dist_r':(float(last.close)/float(last.ema20)-1.0)/R,
      f'cp{m}_below_ema7':below7,f'cp{m}_below_ema20':below20,
      f'cp{m}_red_frac':red_frac,f'cp{m}_last3_progress_slope':slope/R if np.isfinite(slope) else np.nan,
      f'cp{m}_lower_high_frac':lower_high_frac,
    }


def stable_stats(df,target,control,features):
    rows=[]
    for col in features:
        full=sep(target,control,col)
        td=target[target.i<SPLIT];tv=target[target.i>=SPLIT]
        cd=control[control.i<SPLIT];cv=control[control.i>=SPLIT]
        ds=sep(td,cd,col);vs=sep(tv,cv,col)
        dirs=[full['direction'],ds['direction'],vs['direction']]
        same=(len(set(dirs))==1)
        minstr=float(np.nanmin([full['strength'],ds['strength'],vs['strength']])) if all(np.isfinite([full['strength'],ds['strength'],vs['strength']])) else np.nan
        rows.append({'feature':col,'same_direction_full_D_V':bool(same),'min_strength':minstr,
                     'full':full,'discovery':ds,'validation':vs})
    rows.sort(key=lambda r:(r['same_direction_full_D_V'],r['min_strength'] if np.isfinite(r['min_strength']) else -1),reverse=True)
    return rows


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr)
        st=f624.state(k,tr)
        latest_pnl,latest_layer,_=f624.apply(k,t,tr,st)
        pf=f614.path_features(k,t,tr)
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_reason':tr.reason,
             'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'latest_pnl':float(latest_pnl),'latest_layer':latest_layer,
             'strict_sink':bool(pf['strict_sink']),'peak_min':int(pf['peak_min']),
             **pre_context_extra(k,t,tr)}
        for m in CHECKPOINTS:
            cp=checkpoint_extra(k,t,tr,m)
            row[f'cp{m}_alive']=bool(cp is not None)
            if cp:row.update(cp)
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows)
    # Latest five-layer parity from F6.24.
    if abs(df.latest_pnl.sum()-138.3291316546)>0.10:
        raise RuntimeError(f'latest F6.24 stack parity fail {df.latest_pnl.sum()}')

    target=df[(df.parent_pnl<=0)&(df.parent_mfe_r<0.5)&(df.latest_layer=='PARENT')].copy()
    if len(target)!=24:
        raise RuntimeError(f'failure-to-develop cohort parity fail {len(target)} expected 24')
    winners=df[df.parent_pnl>0].copy()

    pre_features=['fib2h_retr','fib2h_range_pct','ret30','ret60','ret120','ret240',
      'pre_ema7_dist','pre_ema20_dist','pre_ema_spread','pre_taker60','range_pos2h','retr_from_high2h',
      'range_pos4h','retr_from_high4h','pre_taker30','pre_taker120','pre_ema7_slope30','pre_ema20_slope60',
      'pre_last_red','pre_last_body_ratio','pre_last_upper_wick_ratio','pre_last_lower_wick_ratio']
    pre_atlas=stable_stats(df,target,winners,pre_features)

    cp_atlas={};slow_counts={}
    for m in CHECKPOINTS:
        alive_t=target[target[f'cp{m}_alive']==True].copy()
        broad=winners[winners[f'cp{m}_alive']==True].copy()
        slow=broad[broad[f'cp{m}_mfe_r']<0.5].copy()
        slow_counts[str(m)]={'target_alive':int(len(alive_t)),'winner_alive':int(len(broad)),'slow_winner_n':int(len(slow))}
        feats=[f'cp{m}_progress_r',f'cp{m}_mfe_r',f'cp{m}_mae_r',f'cp{m}_taker',f'cp{m}_tail2_taker',
               f'cp{m}_ema7_dist_r',f'cp{m}_ema20_dist_r',f'cp{m}_below_ema7',f'cp{m}_below_ema20',
               f'cp{m}_red_frac',f'cp{m}_last3_progress_slope',f'cp{m}_lower_high_frac']
        cp_atlas[str(m)]={'vs_all_winners':stable_stats(df,alive_t,broad,feats),
                          'vs_slow_start_winners':stable_stats(df,alive_t,slow,feats) if len(slow)>0 else []}

    # Cohort anatomy only; natural facts, no fitted action threshold.
    facts={
      'n':int(len(target)),'D':int((target.i<SPLIT).sum()),'V':int((target.i>=SPLIT).sum()),
      'SL':int((target.parent_reason=='SL').sum()),'TIMEOUT':int((target.parent_reason=='TIMEOUT').sum()),
      'strict_sink':int(target.strict_sink.sum()),'aggregate_parent_pnl':float(target.parent_pnl.sum()),
      'median_parent_mfe_r':float(target.parent_mfe_r.median()),'median_parent_mae_r':float(target.parent_mae_r.median()),
      'median_peak_min':float(target.peak_min.median()),
    }

    # Compact top stable results for checkpoint summary.
    def top(rows,n=6):
        return [r for r in rows if r['same_direction_full_D_V']][:n]
    top_pre=top(pre_atlas,8)
    top_hard={m:top(cp_atlas[m]['vs_slow_start_winners'],6) for m in cp_atlas}
    top_broad={m:top(cp_atlas[m]['vs_all_winners'],4) for m in cp_atlas}

    out={'status':'FORENSIC_ONLY_NO_RULE','latest_stack_pnl':float(df.latest_pnl.sum()),
         'target_definition':'parent loss + total MFE <0.5R + latest frozen stack leaves PARENT',
         'facts':facts,'slow_control_counts':slow_counts,
         'top_preentry_stable':top_pre,'top_checkpoint_vs_hard_slow_winners':top_hard,
         'top_checkpoint_vs_all_winners':top_broad,
         'preentry_atlas':pre_atlas,'checkpoint_atlas':cp_atlas,
         'target_dates':target[['date','period','parent_reason','parent_pnl','parent_mfe_r','parent_mae_r','strict_sink','peak_min']].to_dict('records')}
    df.to_csv(OUT/'f625_all_rows.csv',index=False)
    (OUT/'f625_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.25 — Failure-to-Develop / Wrong-Direction Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO MANAGEMENT RULE TUNED OR PROMOTED.**',
        '**Live BBC untouched; frozen Friday stack unchanged.**','',
        '## Cohort parity',
        f"- latest five-layer stack PnL: **{df.latest_pnl.sum():+.3f}**",
        f"- failure-to-develop cohort: **{facts['n']}** = D {facts['D']} / V {facts['V']}",
        f"- SL/TIMEOUT: **{facts['SL']} / {facts['TIMEOUT']}**; strict immediate sink **{facts['strict_sink']}**",
        f"- aggregate parent PnL **{facts['aggregate_parent_pnl']:+.3f}**; median MFE **{facts['median_parent_mfe_r']:.3f}R**, MAE **{facts['median_parent_mae_r']:.3f}R**, peak favorable timing **{facts['median_peak_min']:.1f}m**",'',
        '## Methodological guardrail',
        'Checkpoint features are judged both against all winners and against hard slow-start winners that also have not reached +0.5R at the same checkpoint. This avoids promoting an obvious "has not moved yet" discriminator. No threshold/action PnL optimization is performed.','',
        '## Top strictly pre-entry stable separators']
    for r in top_pre:
        f=r['full'];md.append(f"- `{r['feature']}`: strength full/D/V {f['strength']:.3f}/{r['discovery']['strength']:.3f}/{r['validation']['strength']:.3f}, {f['direction']}; med loss/control {f['loss_median']:.4f}/{f['control_median']:.4f}")
    md += ['', '## Top HARD-control trajectory separators']
    for m in map(str,CHECKPOINTS):
        md.append(f"### +{m}m — target/slow-winner N {slow_counts[m]['target_alive']}/{slow_counts[m]['slow_winner_n']}")
        for r in top_hard[m]:
            f=r['full'];md.append(f"- `{r['feature']}`: strength full/D/V {f['strength']:.3f}/{r['discovery']['strength']:.3f}/{r['validation']['strength']:.3f}, {f['direction']}; med {f['loss_median']:.4f}/{f['control_median']:.4f}")
    md += ['', '## Guardrail','Any next action test must be predeclared from a causal mechanism that survives the hard slow-start-winner control. Do not tune checkpoint timing or numeric cutoffs on this sample.']
    (OUT/'F6.25_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({'facts':facts,'top_pre':top_pre,'top_hard':top_hard},indent=2,default=str),flush=True)

if __name__=='__main__':main()
