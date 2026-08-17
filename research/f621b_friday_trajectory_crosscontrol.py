#!/usr/bin/env python3
"""F6.21b — cross-control check for F6.21 trajectory separators.

Re-runs the frozen F6.21 forensic and explicitly checks whether separators found
against F6.20 false-positive winners also survive against the broader eligible
winner control. FORENSIC ONLY; no trading action or threshold tuning.
"""
from __future__ import annotations
import os, json
from pathlib import Path
import numpy as np
import pandas as pd

os.environ['F621_OUT']=os.getenv('F621B_BASE_OUT','f621b_base')
import f621_friday_low_giveback_trajectory_forensic as base

OUT=Path(os.getenv('F621B_OUT','f621b_out')); OUT.mkdir(parents=True,exist_ok=True)


def stable_row(r):
    vals=[r.auc_loss_high,r.auc_D,r.auc_V]
    if any(pd.isna(v) for v in vals): return False
    dirs=[v>=0.5 for v in vals]
    strengths=[max(v,1-v) for v in vals]
    return bool(len(set(dirs))==1 and strengths[0]>=.65 and strengths[1]>=.60 and strengths[2]>=.60)


def main():
    base.main()
    atlas=pd.read_csv(base.OUT/'f621_trajectory_atlas.csv')
    atlas['stable']=atlas.apply(stable_row,axis=1)
    fp=atlas[atlas.control=='false_positive'].copy()
    bw=atlas[atlas.control=='broad_winner'].copy()
    key=['horizon','feature']
    m=fp.merge(bw,on=key,suffixes=('_fp','_broad'))
    m['same_direction']=m.direction_fp==m.direction_broad
    m['cross_stable']=m.stable_fp & m.stable_broad & m.same_direction
    # Conservative score, descriptive only: weakest AUC strength among
    # full/D/V x both controls, provided direction agrees.
    strength_cols=[]
    for side in ('fp','broad'):
        for c in ('auc_loss_high','auc_D','auc_V'):
            new=f'str_{c}_{side}'
            m[new]=m[f'{c}_{side}'].apply(lambda v:max(v,1-v) if pd.notna(v) else np.nan)
            strength_cols.append(new)
    m['min_strength']=m[strength_cols].min(axis=1)
    m=m.sort_values('min_strength',ascending=False)
    m.to_csv(OUT/'f621b_crosscontrol.csv',index=False)

    focus=['taker_last2_mean','longest_below_ema20','frac_below_ema20','longest_below_ema7','bars_since_above_ema7','end_progress_r','progress_last3_slope']
    focus_rows=m[m.feature.isin(focus)].copy()
    cross=m[m.cross_stable].copy()
    out={
      'cross_stable_count':int(len(cross)),
      'cross_stable':cross.head(20).to_dict('records'),
      'top_crosscontrol':m.head(20).to_dict('records'),
      'focus_features':focus_rows.to_dict('records'),
      'method':'same F6.21 cohorts/features; cross-stable requires original frozen stability screen independently vs false-positive and broad controls, with same loss direction',
      'guardrail':'forensic only; no exit rule tuned or promoted'
    }
    (OUT/'f621b_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Friday F6.21b — Trajectory Cross-Control Check','',
        '**Status: COMPLETE — FORENSIC ONLY; NO EXIT RULE TUNED/PROMOTED.**',
        '**Live BBC untouched; frozen stack unchanged.**','',
        'This check guards against selection bias from using F6.20 false-positive winners as the primary control. A separator is cross-stable only if it passes the same frozen full/D/V stability screen against BOTH false-positive winners and all broad eligible winners, with the same loss direction.','',
        f"## Cross-stable separators: **{len(cross)}**"]
    if len(cross)==0:
        md.append('- none')
    else:
        for _,r in cross.head(20).iterrows():
            md.append(f"- {int(r.horizon)}m {r.feature}: direction {r.direction_fp}; FP AUC full/D/V {r.auc_loss_high_fp:.3f}/{r.auc_D_fp:.3f}/{r.auc_V_fp:.3f}; broad {r.auc_loss_high_broad:.3f}/{r.auc_D_broad:.3f}/{r.auc_V_broad:.3f}; weakest strength {r.min_strength:.3f}")
    md += ['', '## Focus check']
    for _,r in focus_rows.iterrows():
        md.append(f"- {int(r.horizon)}m {r.feature}: FP direction {r.direction_fp}, AUC {r.auc_loss_high_fp:.3f} D/V {r.auc_D_fp:.3f}/{r.auc_V_fp:.3f}; broad direction {r.direction_broad}, AUC {r.auc_loss_high_broad:.3f} D/V {r.auc_D_broad:.3f}/{r.auc_V_broad:.3f}; cross-stable {bool(r.cross_stable)}")
    md += ['', '## Guardrail','If an EMA20 inverse separator disappears against broad controls, treat it as control-selection artifact rather than market edge. Only cross-stable, interpretable trajectory features should be considered for a predeclared F6.22 action test.']
    (OUT/'F6.21B_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
