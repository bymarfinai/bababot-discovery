#!/usr/bin/env python3
"""F6.30 — Friday F6.29 false-positive winner forensic.

Research only; live BBC untouched. NO management rule is tuned/promoted.
Frozen Friday stack remains FIB5 -> EARLY10 -> F6.5 -> D3 -> F6.24.
F6.29 remains a FAILED same-sample diagnostic and is NOT frozen.

Primary question:
Among the 12 F6.29 +20m cuts, what information already available at +20m
separates the 3 eventual parent winners (false-positive cuts) from the 9 parent
losers (correctly defensive cuts)?

Guardrails:
- only information known by the actual +20m decision open is used;
- no threshold/timing/economic sweep;
- the 3 false-positive winners all sit in discovery, so no D/V claim is made;
- tiny-N evidence is stress-tested with leave-one-out;
- directions are cross-checked against the broader F6.27/F6.28 cohort
  (13 future winners vs 9 true-dead) where the same feature is available.
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
import f627_friday_failed_launch_true_vs_recovery_forensic as f627
import f628_friday_recovery_sequence_10_30_forensic as f628
import f629_friday_context_recovery_fail20_management as f629

OUT=Path(os.getenv('F630_OUT','f630_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
SPLIT=f517.SPLIT_N


def auc_winner_high(w,l,col):
    a=w[col].to_numpy(float); b=l[col].to_numpy(float)
    a=a[np.isfinite(a)]; b=b[np.isfinite(b)]
    if len(a)==0 or len(b)==0:return np.nan
    return float(((a[:,None]>b[None,:]).sum()+0.5*(a[:,None]==b[None,:]).sum())/(len(a)*len(b)))


def sep(w,l,col):
    a=auc_winner_high(w,l,col)
    return {'auc_winner_high':a,'strength':float(max(a,1-a)) if np.isfinite(a) else np.nan,
            'direction':'higher=winner' if np.isfinite(a) and a>=.5 else 'lower=winner',
            'winner_median':float(w[col].median()) if len(w) and w[col].notna().any() else np.nan,
            'loss_median':float(l[col].median()) if len(l) and l[col].notna().any() else np.nan,
            'n_winner':int(w[col].notna().sum()),'n_loss':int(l[col].notna().sum())}


def stat(w,l,col,ext_w=None,ext_l=None):
    full=sep(w,l,col)
    loo=[]
    for idx in w.index:
        if len(w)>1: loo.append(sep(w.drop(index=idx),l,col)['strength'])
    for idx in l.index:
        if len(l)>1: loo.append(sep(w,l.drop(index=idx),col)['strength'])
    ext=None
    if ext_w is not None and ext_l is not None and col in ext_w.columns and col in ext_l.columns:
        ext=sep(ext_w,ext_l,col)
    return {'feature':col,'subset':full,
            'loo_min_strength':float(np.nanmin(loo)) if loo else np.nan,
            'loo_median_strength':float(np.nanmedian(loo)) if loo else np.nan,
            'external':ext,
            'direction_agrees_external':bool(ext is not None and ext['direction']==full['direction'])}


def causal20_features(k,t,tr):
    """Features strictly available at t+20m open."""
    out={}
    out.update(f625.pre_context_extra(k,t,tr))
    out.update(f627.pre_level_features(k,t,float(tr.entry)))
    seq=f628.seq_features(k,t,tr,20)
    if not seq.get('alive',False): return None
    for kk,vv in seq.items():
        if kk!='alive': out[f'seq_{kk}']=vv

    bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(minutes=20))]
    if len(bars)!=4:return None
    feats=[]
    for j in range(4):
        z=f627.cfeat(bars.iloc[j],float(tr.entry)); feats.append(z)
        for kk,vv in z.items():out[f'b{j+1}_{kk}']=vv

    b3,b4=bars.iloc[2],bars.iloc[3]
    a,c=feats[2],feats[3]
    out.update({
      'post10_ret_change':c['ret_r']-a['ret_r'],
      'post10_ema7_gap_change':c['ema7_dist_r']-a['ema7_dist_r'],
      'post10_taker_change':c['taker']-a['taker'],
      'post10_qv_ratio_b4_b3':c['quote_volume']/a['quote_volume'] if a['quote_volume']>0 else np.nan,
      'b4_higher_close':float(float(b4.close)>float(b3.close)),
      'b4_higher_low':float(float(b4.low)>float(b3.low)),
      'b4_higher_high':float(float(b4.high)>float(b3.high)),
      'b3_high_touched_ema7':float(float(b3.high)>=float(b3.ema7)),
      'b4_high_touched_ema7':float(float(b4.high)>=float(b4.ema7)),
      'post10_any_high_touch_ema7':float((float(b3.high)>=float(b3.ema7)) or (float(b4.high)>=float(b4.ema7))),
      'b3_close_below_ema7_r':(float(b3.close)/float(b3.ema7)-1)/R,
      'b4_close_below_ema7_r':(float(b4.close)/float(b4.ema7)-1)/R,
      'post10_max_high_vs_ema7_r':max((float(b3.high)/float(b3.ema7)-1)/R,(float(b4.high)/float(b4.ema7)-1)/R),
      'post10_min_low_r':min(a['low_r'],c['low_r']),
      'post10_max_high_r':max(a['high_r'],c['high_r']),
    })
    return out


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr)
        bst=f624.state(k,tr); base_pnl,base_layer,base_dt=f624.apply(k,t,tr,bst)
        watch=f626.failed_launch_state(k,t,tr)
        watch_active=False
        if watch is not None and watch[f626.RULE]:
            watch_active=bool(base_dt is None or watch['decision_t']<pd.Timestamp(base_dt))
        st=f629.candidate_state(k,t,tr) if watch_active else None
        action=False
        if st is not None and st[f629.RULE]:
            action=bool(base_dt is None or st['decision_t']<pd.Timestamp(base_dt))
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),'parent_mae_r':float(tr.mae/R),
             'base_pnl':float(base_pnl),'base_layer':base_layer,'watch_active':watch_active,'f629_action':action}
        if watch_active:
            z=causal20_features(k,t,tr)
            if z is not None:row.update(z)
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT/'f630_rows.csv',index=False)
    watches=df[df.watch_active].copy()
    acts=df[df.f629_action].copy()
    if len(watches)!=26 or len(acts)!=12:raise RuntimeError(f'parity watch/action {len(watches)}/{len(acts)}')
    false_win=acts[acts.parent_pnl>0].copy(); cut_loss=acts[acts.parent_pnl<=0].copy()
    if (len(false_win),len(cut_loss))!=(3,9):raise RuntimeError(f'F6.29 cohort parity {len(false_win)}/{len(cut_loss)}')

    # Broader external control from F6.27 definitions, evaluated at the same +20m causal information.
    ext_win=watches[watches.parent_pnl>0].copy()
    ext_dead=watches[(watches.parent_pnl<=0)&(watches.parent_mfe_r<.5)&(watches.base_layer=='PARENT')].copy()
    if (len(ext_win),len(ext_dead))!=(13,9):raise RuntimeError(f'external cohort parity {len(ext_win)}/{len(ext_dead)}')

    exclude={'i','period','date','parent_pnl','parent_win','parent_mfe_r','parent_mae_r','base_pnl','base_layer','watch_active','f629_action'}
    cols=[c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
    stats=[]
    for col in cols:
        if false_win[col].notna().sum() and cut_loss[col].notna().sum():
            stats.append(stat(false_win,cut_loss,col,ext_win,ext_dead))
    stats.sort(key=lambda r:(r['direction_agrees_external'],r['loo_median_strength'],r['subset']['strength']),reverse=True)

    # Boolean/natural-state rates, useful because a 3-winner cohort can make AUC look deceptively strong.
    bool_like=[]
    for col in cols:
        vals=set(df[col].dropna().unique().tolist())
        if vals.issubset({0,1,0.0,1.0}):
            a=false_win[col].dropna();b=cut_loss[col].dropna();ew=ext_win[col].dropna();ed=ext_dead[col].dropna()
            if len(a) and len(b):
                rec={'feature':col,'false_winner_rate':float(a.mean()),'cut_loss_rate':float(b.mean()),'gap_winner_minus_loss':float(a.mean()-b.mean()),
                     'external_winner_rate':float(ew.mean()) if len(ew) else np.nan,'external_dead_rate':float(ed.mean()) if len(ed) else np.nan}
                rec['external_gap_winner_minus_dead']=rec['external_winner_rate']-rec['external_dead_rate'] if np.isfinite(rec['external_winner_rate']) and np.isfinite(rec['external_dead_rate']) else np.nan
                rec['same_direction_external']=bool(np.isfinite(rec['external_gap_winner_minus_dead']) and rec['gap_winner_minus_loss']*rec['external_gap_winner_minus_dead']>=0)
                bool_like.append(rec)
    bool_like.sort(key=lambda r:(r['same_direction_external'],abs(r['gap_winner_minus_loss']),abs(r['external_gap_winner_minus_dead']) if np.isfinite(r['external_gap_winner_minus_dead']) else -1),reverse=True)

    out={'status':'FORENSIC_ONLY_NO_RULE','cohort_counts':{'f629_false_winner':len(false_win),'f629_cut_loss':len(cut_loss),'external_future_winner':len(ext_win),'external_true_dead':len(ext_dead)},
         'false_winner_dates':false_win[['date','period','parent_pnl','parent_mfe_r','parent_mae_r']].to_dict('records'),
         'top_continuous':stats[:20],'top_boolean':bool_like[:20],
         'guardrail':'All 3 F6.29 false-positive winners are discovery cases. No validation claim; no threshold/timing/economic sweep; no rule promoted.'}
    (OUT/'f630_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.30 — F6.29 False-Positive Winner Forensic','',
        '**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**','**Live BBC untouched; F6.29 remains failed and is NOT frozen.**','',
        '## Cohorts',f'- false-positive future winners cut by F6.29: **{len(false_win)}** (all discovery)',f'- parent losers cut by F6.29: **{len(cut_loss)}**',f'- broader cross-control: **{len(ext_win)} future winners vs {len(ext_dead)} true-dead**','',
        '## Strongest +20m causal separators with external direction agreement']
    shown=0
    for r in stats:
        if not r['direction_agrees_external']:continue
        s=r['subset'];e=r['external']
        md.append(f"- `{r['feature']}`: subset strength **{s['strength']:.3f}** ({s['direction']}), med winner/loss **{s['winner_median']:.4f}/{s['loss_median']:.4f}**; LOO median/min **{r['loo_median_strength']:.3f}/{r['loo_min_strength']:.3f}**; external strength **{e['strength']:.3f}** same direction")
        shown+=1
        if shown>=12:break
    md += ['', '## Natural boolean clues']
    for r in bool_like[:10]:
        md.append(f"- `{r['feature']}`: false-winner/loss **{100*r['false_winner_rate']:.1f}%/{100*r['cut_loss_rate']:.1f}%**; external winner/dead **{100*r['external_winner_rate']:.1f}%/{100*r['external_dead_rate']:.1f}%**; direction agreement **{r['same_direction_external']}**")
    md += ['', '## Guardrail','All 3 false-positive winners are discovery cases. Treat any apparent perfect separator as hypothesis-generation only. The next step may freeze ONE simple natural-state protection only if the signal also agrees with the broader 13-winner vs 9-dead cross-control; otherwise stop rather than overfit.']
    (OUT/'F6.30_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
