#!/usr/bin/env python3
"""F6.27 — Friday FAILED_LAUNCH_10 true-dead vs recovery forensic.

Research only; live BBC untouched. NO management rule is tuned/promoted.
Frozen Friday stack remains FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.26 remains a FAILED diagnostic and is NOT added to the frozen stack.

Primary contrast is restricted to ACTIVE F6.26 actions at the exact +10m decision:
A) TRUE_DEAD: exact F6.25 failure-to-develop members caught by F6.26
   (parent loss, total parent MFE < +0.5R, frozen baseline still PARENT).
B) FALSE_WINNER: eventual parent winners actively cut by F6.26.

Other F6.26-acted losers are kept only as secondary reference and are not mixed
into the primary labels.

Causal features use only strictly pre-entry data and the two completed 5m bars
known at +10m. Post-+10m path is reported DESCRIPTIVELY to explain what the two
cohorts subsequently do; it is never used as a decision feature.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f624_friday_context_repair_failure_management as f624
import f625_friday_failure_to_develop_forensic as f625
import f626_friday_failed_launch10_management as f626

OUT=Path(os.getenv('F627_OUT','f627_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N


def auc_loss_high(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    a=a[np.isfinite(a)];b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    return float(((a[:,None]>b[None,:]).sum()+0.5*(a[:,None]==b[None,:]).sum())/(len(a)*len(b)))


def sep(a,b,col):
    x=auc_loss_high(a[col],b[col])
    return {'auc_dead_high':x,'strength':float(max(x,1-x)) if np.isfinite(x) else np.nan,
            'direction':'higher=dead' if np.isfinite(x) and x>=.5 else 'lower=dead',
            'dead_median':float(a[col].median()) if len(a) and a[col].notna().any() else np.nan,
            'winner_median':float(b[col].median()) if len(b) and b[col].notna().any() else np.nan,
            'n_dead':int(a[col].notna().sum()),'n_winner':int(b[col].notna().sum())}


def robust_stat(dead,win,col):
    full=sep(dead,win,col)
    out={'feature':col,'full':full}
    dirs=[full['direction']]; strengths=[full['strength']]
    for name,mask in [('discovery',lambda x:x.i<SPLIT),('validation',lambda x:x.i>=SPLIT)]:
        a=dead[mask(dead)];b=win[mask(win)]
        s=sep(a,b,col) if len(a) and len(b) else {'auc_dead_high':np.nan,'strength':np.nan,'direction':'NA','dead_median':np.nan,'winner_median':np.nan,'n_dead':len(a),'n_winner':len(b)}
        out[name]=s
        if np.isfinite(s['strength']):dirs.append(s['direction']);strengths.append(s['strength'])
    out['same_direction_available_splits']=bool(len(set(dirs))==1)
    out['min_strength_available_splits']=float(min(strengths)) if strengths else np.nan
    # Leave-one-out full-sample separation strength, descriptive robustness for tiny N.
    loo=[]
    for idx in dead.index:
        s=sep(dead.drop(index=idx),win,col);loo.append(s['strength'])
    for idx in win.index:
        s=sep(dead,win.drop(index=idx),col);loo.append(s['strength'])
    out['loo_min_strength']=float(np.nanmin(loo)) if loo else np.nan
    out['loo_median_strength']=float(np.nanmedian(loo)) if loo else np.nan
    return out


def cfeat(b,entry):
    o=float(b.open);h=float(b.high);l=float(b.low);c=float(b.close);rg=max(h-l,1e-12)
    body=abs(c-o);uw=h-max(o,c);lw=min(o,c)-l
    return {'ret_r':(c/entry-1)/R,'high_r':(h/entry-1)/R,'low_r':(l/entry-1)/R,
            'range_r':(rg/entry)/R,'red':float(c<o),'body_ratio':body/rg,
            'upper_wick_ratio':uw/rg,'lower_wick_ratio':lw/rg,
            'close_location':(c-l)/rg,'taker':float(b.taker_imb),'quote_volume':float(b.quote_volume),
            'ema7_dist_r':(c/float(b.ema7)-1)/R,'ema20_dist_r':(c/float(b.ema20)-1)/R}


def pre_level_features(k,t,entry):
    out={}
    for mins in (30,60,120,240):
        x=k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=mins))]
        hi=float(x.high.max());lo=float(x.low.min());rg=max(hi-lo,1e-12)
        out[f'pre{mins}_entry_pos']=(entry-lo)/rg
        out[f'pre{mins}_dist_low_r']=((entry/lo)-1)/R if lo>0 else np.nan
        out[f'pre{mins}_dist_high_r']=((hi/entry)-1)/R if entry>0 else np.nan
    pre60=k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=60))]
    out['pre60_qv_median5']=float(pre60.quote_volume.median())
    return out


def post_path(k,t,tr):
    """Outcome-descriptive only; NEVER a causal decision feature."""
    ex=pd.Timestamp(tr.exit_t)
    after=k[(k.index>=t+pd.Timedelta(minutes=10))&(k.index<ex)]
    def first_close(cond):
        z=after[cond(after)]
        return np.nan if z.empty else float((pd.Timestamp(z.iloc[0].ts)-t)/pd.Timedelta(minutes=1)+5)
    entry=float(tr.entry)
    # First later completed close reclaiming entry / EMA7 / EMA20.
    reclaim_entry=first_close(lambda x:x.close.astype(float)>=entry)
    reclaim_ema7=first_close(lambda x:x.close.astype(float)>=x.ema7.astype(float))
    reclaim_ema20=first_close(lambda x:x.close.astype(float)>=x.ema20.astype(float))
    # First later hit of natural milestones by high; known only after that bar completes.
    def first_high(thr):
        z=after[after.high.astype(float)>=entry*(1+thr)]
        return np.nan if z.empty else float((pd.Timestamp(z.iloc[0].ts)-t)/pd.Timedelta(minutes=1)+5)
    out={'post_reclaim_entry_min':reclaim_entry,'post_reclaim_ema7_min':reclaim_ema7,'post_reclaim_ema20_min':reclaim_ema20,
         'post_hit_05r_min':first_high(.5*R),'post_hit_1r_min':first_high(1.0*R)}
    for m in (15,20,30,60,120):
        dt=t+pd.Timedelta(minutes=m)
        x=k[(k.index>=t)&(k.index<dt)]
        if dt not in k.index or ex<=dt or len(x)!=m//5:
            out[f'post{m}_alive']=False;continue
        last=x.iloc[-1];q=float(x.quote_volume.sum());tb=float(x.taker_buy_quote.sum())
        out[f'post{m}_alive']=True
        out[f'post{m}_progress_r']=(float(last.close)/entry-1)/R
        out[f'post{m}_mfe_r']=(float(x.high.max())/entry-1)/R
        out[f'post{m}_mae_r']=(1-float(x.low.min())/entry)/R
        out[f'post{m}_taker']=2*tb/q-1 if q>0 else np.nan
        out[f'post{m}_above_entry']=float(float(last.close)>=entry)
        out[f'post{m}_above_ema7']=float(float(last.close)>=float(last.ema7))
        out[f'post{m}_above_ema20']=float(float(last.close)>=float(last.ema20))
    return out


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr)
        base_st=f624.state(k,tr);base_pnl,base_layer,base_dt=f624.apply(k,t,tr,base_st)
        st=f626.failed_launch_state(k,t,tr)
        active=False
        if st is not None and st[f626.RULE]:
            dt=st['decision_t']
            active=bool(base_dt is None or dt<pd.Timestamp(base_dt))
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'active_f626':active}
        if active:
            row.update(f625.pre_context_extra(k,t,tr));row.update(pre_level_features(k,t,float(tr.entry)))
            w=k[(k.index>=t)&(k.index<t+pd.Timedelta(minutes=10))]
            b1,b2=w.iloc[0],w.iloc[1];a=cfeat(b1,float(tr.entry));b=cfeat(b2,float(tr.entry))
            for kk,vv in a.items():row[f'b1_{kk}']=vv
            for kk,vv in b.items():row[f'b2_{kk}']=vv
            qmed=row['pre60_qv_median5']
            row.update({
              'b1_qv_vs_pre60med':a['quote_volume']/qmed if qmed>0 else np.nan,
              'b2_qv_vs_pre60med':b['quote_volume']/qmed if qmed>0 else np.nan,
              'b2_vs_b1_qv':b['quote_volume']/a['quote_volume'] if a['quote_volume']>0 else np.nan,
              'taker_change_b2_b1':b['taker']-a['taker'],
              'progress_change_b2_b1':b['ret_r']-a['ret_r'],
              'range_change_b2_b1':b['range_r']-a['range_r'],
              'b2_lower_low':float(float(b2.low)<float(b1.low)),
              'b2_lower_close':float(float(b2.close)<float(b1.close)),
              'b2_break_b1_low_close':float(float(b2.close)<float(b1.low)),
              'ema7_above_ema20_b2':float(float(b2.ema7)>float(b2.ema20)),
              'b2_close_vs_pre30low_r':(float(b2.close)/float(k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=30))].low.min())-1)/R,
            })
            row.update(post_path(k,t,tr))
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT/'f627_rows.csv',index=False)
    active=df[df.active_f626].copy()
    if len(active)!=26:raise RuntimeError(f'F6.26 active parity fail {len(active)}')
    dead=active[(active.parent_pnl<=0)&(active.parent_mfe_r<.5)&(active.base_layer=='PARENT')].copy()
    win=active[active.parent_pnl>0].copy()
    other=active[(active.parent_pnl<=0)&~active.index.isin(dead.index)].copy()
    if len(dead)!=9 or len(win)!=13 or len(other)!=4:
        raise RuntimeError(f'cohort parity fail dead/win/other={len(dead)}/{len(win)}/{len(other)}')

    causal_features=[
      'pre_last_body_ratio','pre_last_upper_wick_ratio','pre_last_lower_wick_ratio','pre_last_red',
      'pre_ema_spread','pre_taker30','pre_taker60','pre_taker120','ret30','ret60','ret120','ret240',
      'range_pos2h','retr_from_high2h','range_pos4h','retr_from_high4h',
      'pre30_entry_pos','pre60_entry_pos','pre120_entry_pos','pre240_entry_pos',
      'pre30_dist_low_r','pre60_dist_low_r','pre120_dist_low_r','pre240_dist_low_r',
      'b1_ret_r','b1_high_r','b1_low_r','b1_range_r','b1_red','b1_body_ratio','b1_upper_wick_ratio','b1_lower_wick_ratio','b1_close_location','b1_taker','b1_qv_vs_pre60med','b1_ema7_dist_r','b1_ema20_dist_r',
      'b2_ret_r','b2_high_r','b2_low_r','b2_range_r','b2_red','b2_body_ratio','b2_upper_wick_ratio','b2_lower_wick_ratio','b2_close_location','b2_taker','b2_qv_vs_pre60med','b2_ema7_dist_r','b2_ema20_dist_r',
      'b2_vs_b1_qv','taker_change_b2_b1','progress_change_b2_b1','range_change_b2_b1','b2_lower_low','b2_lower_close','b2_break_b1_low_close','ema7_above_ema20_b2','b2_close_vs_pre30low_r']
    stats=[robust_stat(dead,win,c) for c in causal_features if c in active.columns]
    stats.sort(key=lambda r:(r['same_direction_available_splits'],r['min_strength_available_splits'],r['loo_median_strength']),reverse=True)
    top=stats[:15]

    # Descriptive post-decision cohort path summaries.
    post={}
    for name,g in [('true_dead',dead),('false_winner',win),('other_loser',other)]:
        rec={'n':int(len(g)),'D':int((g.i<SPLIT).sum()),'V':int((g.i>=SPLIT).sum()),
             'parent_pnl_sum':float(g.parent_pnl.sum()),'parent_mfe_r_med':float(g.parent_mfe_r.median()),'parent_mae_r_med':float(g.parent_mae_r.median())}
        for c in ['post_reclaim_entry_min','post_reclaim_ema7_min','post_reclaim_ema20_min','post_hit_05r_min','post_hit_1r_min']:
            rec[c+'_median']=float(g[c].median()) if g[c].notna().any() else np.nan
            rec[c+'_rate']=float(g[c].notna().mean())
        for m in (15,20,30,60,120):
            alive=g[g[f'post{m}_alive']==True]
            rec[f'post{m}_alive_n']=int(len(alive))
            for c in ('progress_r','mfe_r','mae_r','taker','above_entry','above_ema7','above_ema20'):
                col=f'post{m}_{c}'
                rec[f'post{m}_{c}_median']=float(alive[col].median()) if len(alive) and alive[col].notna().any() else np.nan
        post[name]=rec

    out={'status':'FORENSIC_ONLY_NO_RULE','cohort_definition':{
         'true_dead':'active F6.26 + parent loss + total MFE<0.5R + frozen baseline PARENT',
         'false_winner':'active F6.26 + eventual parent winner',
         'other_loser':'active F6.26 loser outside exact F6.25 target; secondary only'},
         'cohort_counts':{'true_dead':len(dead),'false_winner':len(win),'other_loser':len(other)},
         'top_causal_separators':top,'all_causal_stats':stats,'post10_descriptive':post,
         'true_dead_dates':dead[['date','period','parent_pnl','parent_mfe_r','parent_mae_r']].to_dict('records'),
         'false_winner_dates':win[['date','period','parent_pnl','parent_mfe_r','parent_mae_r','base_pnl','base_layer']].to_dict('records')}
    (OUT/'f627_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.27 — FAILED_LAUNCH_10 True-Dead vs Recovery Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**','**Live BBC untouched; F6.26 remains failed and is NOT frozen.**','',
        '## Cohorts',f"- true failure-to-develop caught by F6.26: **{len(dead)}** (D {(dead.i<SPLIT).sum()} / V {(dead.i>=SPLIT).sum()})",f"- false-positive eventual winners: **{len(win)}** (D {(win.i<SPLIT).sum()} / V {(win.i>=SPLIT).sum()})",f"- other acted losers, secondary only: **{len(other)}**",'',
        '## Strongest causal separators available by +10m']
    for r in top[:10]:
        f=r['full'];d=r['discovery'];v=r['validation']
        md.append(f"- `{r['feature']}`: strength full/D/V **{f['strength']:.3f}/{d['strength'] if np.isfinite(d['strength']) else float('nan'):.3f}/{v['strength'] if np.isfinite(v['strength']) else float('nan'):.3f}**, {f['direction']}; median dead/winner **{f['dead_median']:.4f}/{f['winner_median']:.4f}**; LOO median **{r['loo_median_strength']:.3f}**")
    md += ['', '## What happens AFTER the +10m false alarm (descriptive, not a decision feature)']
    for name in ('true_dead','false_winner'):
        r=post[name]
        md += [f"### {name}",f"- N **{r['n']}**, parent PnL sum **{r['parent_pnl_sum']:+.3f}**, MFE/MAE median **{r['parent_mfe_r_med']:.3f}R / {r['parent_mae_r_med']:.3f}R**",f"- later close reclaim entry rate **{100*r['post_reclaim_entry_min_rate']:.1f}%**, median time **{r['post_reclaim_entry_min_median']:.1f}m**",f"- later EMA7 reclaim rate **{100*r['post_reclaim_ema7_min_rate']:.1f}%**, median **{r['post_reclaim_ema7_min_median']:.1f}m**",f"- later +0.5R hit rate **{100*r['post_hit_05r_min_rate']:.1f}%**, median **{r['post_hit_05r_min_median']:.1f}m**",f"- later +1R hit rate **{100*r['post_hit_1r_min_rate']:.1f}%**, median **{r['post_hit_1r_min_median']:.1f}m**",'']
    md += ['## Guardrail','The post-+10m section explains outcomes but cannot be used to justify a +10m live action. Any next candidate must use only the causal feature set above and must be predeclared without threshold/timing sweeps.']
    (OUT/'F6.27_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
