#!/usr/bin/env python3
"""F6.17 — identify why F6.16 P1 cuts 10 eventual winners vs 6 true givebacks.

FORENSIC ONLY. No management threshold/rule promotion. Existing Friday layers untouched.
All features are causal and available by the exact F6.16 decision open.
"""
from __future__ import annotations
import json, os, math
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616

OUT=Path(os.getenv('F617_OUT','f617_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL


def auc_toward_true(y,x):
    y=np.asarray(y,dtype=int); x=np.asarray(x,dtype=float)
    ok=np.isfinite(x); y=y[ok]; x=x[ok]
    pos=x[y==1]; neg=x[y==0]
    if len(pos)==0 or len(neg)==0:return np.nan
    # P(random true-giveback feature > random false-positive-winner feature)
    wins=0.0
    for a in pos:
        wins += np.sum(a>neg) + 0.5*np.sum(a==neg)
    return float(wins/(len(pos)*len(neg)))


def cfeat(b):
    rng=max(float(b.high-b.low),1e-12); body=abs(float(b.close-b.open))
    uw=float(b.high-max(b.open,b.close)); lw=float(min(b.open,b.close)-b.low)
    return {
      'bear':float(b.close<b.open),'body_ratio':body/rng,'upper_wick_ratio':uw/rng,'lower_wick_ratio':lw/rng,
      'close_pos':float((b.close-b.low)/rng),'taker':float(b.taker_imb),
      'ema7_dist':float(b.close/b.ema7-1),'ema20_dist':float(b.close/b.ema20-1),
      'ema7_above_ema20':float(b.ema7>b.ema20),
    }


def features(k,tr,ps):
    ht=ps['hit_t']; dt=ps['decision_t']
    w=k[(k.index>=ht)&(k.index<dt)].copy()
    assert len(w)==4
    fs=[cfeat(b) for _,b in w.iterrows()]
    first,last=w.iloc[0],w.iloc[-1]
    closes=w.close.to_numpy(float); lows=w.low.to_numpy(float); highs=w.high.to_numpy(float); tak=w.taker_imb.to_numpy(float)
    best=float(highs.max()); low=float(lows.min()); lc=float(last.close)
    best_r=(best/tr.entry-1)/R
    progress_r=(lc/tr.entry-1)/R
    dd_best_r=(best/lc-1)/R
    retained=(lc/tr.entry-1)/max(best/tr.entry-1,1e-12)
    out={
      'progress_r':progress_r,'best_r':best_r,'drawdown_from_best_r':dd_best_r,'retained_fraction':retained,
      'window_range_r':(best/low-1)/R,'rebound_from_low_r':(lc/low-1)/R,
      'close_slope_r_per_bar':float(np.polyfit(np.arange(4),closes/tr.entry-1,1)[0]/R),
      'last_vs_prev_r':float((closes[-1]/closes[-2]-1)/R),
      'last2_rising':float(closes[-1]>closes[-2] and closes[-2]>closes[-3]),
      'last_close_up':float(closes[-1]>closes[-2]),
      'last2_lows_rising':float(lows[-1]>lows[-2]),
      'bear_frac':float(np.mean([f['bear'] for f in fs])),
      'last_bear':fs[-1]['bear'],'last_body_ratio':fs[-1]['body_ratio'],'last_upper_wick':fs[-1]['upper_wick_ratio'],'last_lower_wick':fs[-1]['lower_wick_ratio'],'last_close_pos':fs[-1]['close_pos'],
      'taker_med':float(np.median(tak)),'taker_last':float(tak[-1]),'taker_last2_med':float(np.median(tak[-2:])),
      'taker_recovery':float(tak[-1]-tak[0]),'taker_slope':float(np.polyfit(np.arange(4),tak,1)[0]),'positive_taker_frac':float(np.mean(tak>0)),
      'last_ema7_dist':fs[-1]['ema7_dist'],'last_ema20_dist':fs[-1]['ema20_dist'],'ema7_above_ema20':fs[-1]['ema7_above_ema20'],
      'ema7_slope_pct':float(last.ema7/first.ema7-1),'ema20_slope_pct':float(last.ema20/first.ema20-1),
      'decision_open_progress_r':float((ps['decision_open']/tr.entry-1)/R),
      'decision_gap_vs_lastclose_r':float((ps['decision_open']/lc-1)/R),
      'milestone_reject':float(ps['milestone_reject']),'stretch1618':float(ps['stretch1618']),
    }
    return out


def summarize(df,feature):
    t=df[df.true_giveback]; w=df[~df.true_giveback]
    return {
      'feature':feature,'auc_true_high':auc_toward_true(df.true_giveback.astype(int),df[feature]),
      'median_true':float(t[feature].median()),'median_false_winner':float(w[feature].median()),
      'auc_discovery':auc_toward_true(df[df.period=='discovery'].true_giveback.astype(int),df[df.period=='discovery'][feature]),
      'auc_validation':auc_toward_true(df[df.period=='validation'].true_giveback.astype(int),df[df.period=='validation'][feature]),
    }


def main():
    k=f517.load_klines(); days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8); tr=f517.simulate_parent(k,t)
        ps=f616.protection_state(k,tr)
        if ps is None or not ps['P1_FLOW_EMA15']: continue
        pnl,layer,dt=f616.apply_rule(k,t,tr,ps,'P1_FLOW_EMA15')
        if layer!='P1_FLOW_EMA15': continue  # earlier frozen layer has priority
        true=bool(tr.pnl<=0 and tr.mfe>=R and tr.mfe<2*R)
        false=bool(tr.pnl>0)
        if not (true or false): continue
        row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,'true_giveback':true,'parent_pnl':float(tr.pnl),'parent_mfe_r':float(tr.mfe/R),'cut_pnl':float(pnl),'hit_t':str(ps['hit_t']),'decision_t':str(ps['decision_t'])}
        row.update(features(k,tr,ps)); rows.append(row)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f617_detector_cases.csv',index=False)
    if len(df)!=16 or int(df.true_giveback.sum())!=6 or int((~df.true_giveback).sum())!=10:
        raise AssertionError(f'F6.16 detector cohort parity mismatch n={len(df)} true={df.true_giveback.sum()}')
    features_list=[c for c in df.columns if c not in {'i','period','date','true_giveback','parent_pnl','parent_mfe_r','cut_pnl','hit_t','decision_t'}]
    atlas=pd.DataFrame([summarize(df,c) for c in features_list])
    atlas['strength']=np.maximum(atlas.auc_true_high,1-atlas.auc_true_high)
    atlas=atlas.sort_values('strength',ascending=False); atlas.to_csv(OUT/'f617_feature_atlas.csv',index=False)

    # Natural categorical diagnostics, descriptive only; no promotion.
    cats={
      'last_close_up':{},'last2_lows_rising':{},'last_bear':{},'ema7_above_ema20':{},'milestone_reject':{},'stretch1618':{}
    }
    for c in cats:
        cats[c]={'true_rate':float(df[df.true_giveback][c].mean()),'false_winner_rate':float(df[~df.true_giveback][c].mean()),
                 'D_true_rate':float(df[(df.true_giveback)&(df.period=='discovery')][c].mean()),'D_false_rate':float(df[(~df.true_giveback)&(df.period=='discovery')][c].mean()),
                 'V_true_rate':float(df[(df.true_giveback)&(df.period=='validation')][c].mean()),'V_false_rate':float(df[(~df.true_giveback)&(df.period=='validation')][c].mean())}
    top=atlas.head(12).to_dict('records')
    out={'n':len(df),'true_givebacks':int(df.true_giveback.sum()),'false_positive_winners':int((~df.true_giveback).sum()),
         'period_counts':df.groupby(['true_giveback','period']).size().rename_axis(['true_giveback','period']).reset_index(name='n').to_dict('records'),
         'top_features':top,'categorical':cats}
    (OUT/'f617_summary.json').write_text(json.dumps(out,indent=2,default=str))
    md=['# Friday F6.17 — Why F6.16 Cuts Winners vs True Givebacks','', '**FORENSIC ONLY — no management rule tuned or promoted.**','',
        f"Cohort parity: **{len(df)} P1 actions = {int(df.true_giveback.sum())} true +1R givebacks vs {int((~df.true_giveback).sum())} eventual winners.**",'',
        '## Top causal separators at the exact F6.16 decision time','',
        '| feature | AUC true-high | D | V | median true | median false-winner |','|---|---:|---:|---:|---:|---:|']
    for r in top:
        md.append(f"| {r['feature']} | {r['auc_true_high']:.3f} | {r['auc_discovery']:.3f} | {r['auc_validation']:.3f} | {r['median_true']:.5f} | {r['median_false_winner']:.5f} |")
    md += ['', '## Natural categorical diagnostics','']
    for c,v in cats.items(): md.append(f"- **{c}** true {v['true_rate']:.1%} vs false-winner {v['false_winner_rate']:.1%}; D {v['D_true_rate']:.1%}/{v['D_false_rate']:.1%}; V {v['V_true_rate']:.1%}/{v['V_false_rate']:.1%}.")
    md += ['', '## Guardrail','This stage identifies mechanisms only. Do not select thresholds or promote a new exit from this same 16-case atlas. Next stage may predeclare a small number of natural recovery-vs-death hypotheses based on stable D/V separators.']
    (OUT/'F6.17_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
