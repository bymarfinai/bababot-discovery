#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BASE_PATH=HERE/'eth_b27dx_pair_calibration_v2.py'
spec=importlib.util.spec_from_file_location('eth_v2_base',BASE_PATH)
b=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(b)

PFX='ETH_B27DX_S2_ENTRY_GEOMETRY'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_SCORES=ROOT/f'{PFX}_Scores.csv'
OUT_SUMMARY=ROOT/f'{PFX}_EntrySummary.csv'
OUT_ROBUST=ROOT/f'{PFX}_RobustClockEntries.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

REF_MIN=300
HORIZON_MIN=360
CLOCKS=(300,540,600,960)  # 05:00,09:00,10:00,16:00 UTC
ENTRIES=(0.95,0.90,0.85,0.80,0.75,0.70,0.65,0.60)
PARTS=('development','external','reference_validation')
TARGET_EXT=0.20
STOP_F=0.35
BTC_WR=0.719298
BTC_PF=2.223193


def clock_label(v:int)->str:
    return f'{(v//60)%24:02d}:{v%60:02d}'

def f_label(v:float)->str:
    return f'F{int(round(v*100)):02d}'

def positive(part:str,r:dict)->bool:
    if part=='development':
        return bool(r['n']>=30 and r['pf']>=1.10 and r['expectancy']>0 and r['net']>0)
    return bool(r['n']>=15 and r['pf']>1.00 and r['expectancy']>0 and r['net']>0)

def finite(v):
    if pd.isna(v): return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)

def run_scores(x)->pd.DataFrame:
    rows=[]
    for ef in ENTRIES:
        for exec_min in CLOCKS:
            for part in PARTS:
                r=b.score_config(x=x,part_name=part,side='LONG',exec_min=exec_min,
                                 ref_min=REF_MIN,horizon_min=HORIZON_MIN,entry_f=ef,
                                 target_ext=TARGET_EXT,stop_f=STOP_F,stress_bps=0.0)
                r['execution_utc']=clock_label(exec_min)
                r['entry']=f_label(ef)
                r['positive']=positive(part,r)
                rows.append(r)
    return pd.DataFrame(rows)

def summarize(scores:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    robust_rows=[]
    for ef in ENTRIES:
        for ex in CLOCKS:
            q=scores[(scores.entry_f==ef)&(scores.exec_min==ex)]
            if len(q)!=3: continue
            ok=all(bool(q.loc[q.partition==p,'positive'].iloc[0]) for p in PARTS)
            if ok:
                robust_rows.append({'entry_f':ef,'entry':f_label(ef),'exec_min':ex,'execution_utc':clock_label(ex)})
    robust=pd.DataFrame(robust_rows)

    rows=[]
    for ef in ENTRIES:
        q=scores[scores.entry_f==ef]
        rclocks=[] if robust.empty else robust.loc[robust.entry_f==ef,'execution_utc'].tolist()
        row={'entry_f':ef,'entry':f_label(ef),'robust_clock_count':len(rclocks),
             'robust_clocks':','.join(rclocks),'supported':len(rclocks)>=2}
        for p in PARTS:
            z=q[q.partition==p]
            row[f'{p}_median_wr']=float(pd.to_numeric(z.wr,errors='coerce').median())
            row[f'{p}_median_pf']=float(pd.Series([finite(v) for v in z.pf]).median())
            row[f'{p}_median_exp']=float(pd.to_numeric(z.expectancy,errors='coerce').median())
            row[f'{p}_median_n']=float(pd.to_numeric(z.n,errors='coerce').median())
        major_wr=[];major_pf=[];major_exp=[]
        if rclocks:
            z=q[q.execution_utc.isin(rclocks)]
            major_wr=pd.to_numeric(z.wr,errors='coerce').dropna().tolist()
            major_pf=[finite(v) for v in z.pf if not pd.isna(v)]
            major_exp=pd.to_numeric(z.expectancy,errors='coerce').dropna().tolist()
        row['robust_major_median_wr']=float(np.median(major_wr)) if major_wr else np.nan
        row['robust_major_median_pf']=float(np.median(major_pf)) if major_pf else np.nan
        row['robust_major_median_exp']=float(np.median(major_exp)) if major_exp else np.nan
        row['btc_wr_gap_pp']=100*((row['robust_major_median_wr'] if not pd.isna(row['robust_major_median_wr']) else 0)-BTC_WR) if rclocks else np.nan
        row['btc_pf_gap']=(row['robust_major_median_pf']-BTC_PF) if rclocks else np.nan
        rows.append(row)
    return pd.DataFrame(rows),robust

def supported_runs(summary:pd.DataFrame):
    vals=[float(r.entry_f) for r in summary.sort_values('entry_f',ascending=False).itertuples(index=False) if bool(r.supported)]
    if not vals:return []
    runs=[];cur=[vals[0]]
    for v in vals[1:]:
        if abs((cur[-1]-v)-0.05)<1e-9:cur.append(v)
        else:runs.append(cur);cur=[v]
    runs.append(cur)
    return runs

def fmt(v,nd=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{nd}f}'

def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,coverage=b.m.m.load5()
    scores=run_scores(x);scores.to_csv(OUT_SCORES,index=False)
    summary,robust=summarize(scores)
    summary.to_csv(OUT_SUMMARY,index=False);robust.to_csv(OUT_ROBUST,index=False)
    runs=supported_runs(summary)
    family_runs=[r for r in runs if len(r)>=2]
    if family_runs:status='ETH_S2_NATIVE_ENTRY_FAMILY_SUPPORTED'
    elif bool(summary.supported.any()):status='ETH_S2_SUPPORTED_ENTRIES_NO_FAMILY'
    else:status='ETH_S2_NO_SUPPORTED_ENTRY'

    lines=['# ETH B27DX — S2 Native Entry Geometry — Result','',
           f'ETH raw 5m coverage: **{coverage:.4%}**.','',
           'Frozen native structure: **R300 / X360**, execution clocks **05:00, 09:00, 10:00, 16:00 UTC**. Only LONG retrace entry fraction varies. Target E20 and completed-close invalidation F35 remain frozen.','',
           '## Entry-fraction summary','',
           '| Entry | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Supported |',
           '|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in summary.itertuples(index=False):
        lines.append(f'| {r.entry} | {r.robust_clock_count}/4 | {r.robust_clocks or "-"} | {pct(r.development_median_wr)} | {fmt(r.development_median_pf)} | {pct(r.external_median_wr)} | {fmt(r.external_median_pf)} | {pct(r.reference_validation_median_wr)} | {fmt(r.reference_validation_median_pf)} | {pct(r.robust_major_median_wr)} | {fmt(r.robust_major_median_pf)} | {"YES" if r.supported else "NO"} |')

    lines += ['','## Robust clock × entry pairs','']
    if robust.empty:lines.append('None.')
    else:
        lines += ['| Entry | Clock |','|---:|---:|']
        for r in robust.sort_values(['entry_f','exec_min'],ascending=[False,True]).itertuples(index=False):
            lines.append(f'| {r.entry} | {r.execution_utc} |')

    lines += ['','## Supported entry-family runs','']
    if not runs:lines.append('None.')
    else:
        for i,run in enumerate(runs,1):
            labels=[f_label(v) for v in run]
            lines.append(f'- Run {i}: **{" → ".join(labels)}** ({len(run)} adjacent fractions).')

    lines += ['','## BTC final benchmark diagnostic','',
              '- BTC B27DX LONG: **WR 71.9%, PF 2.22, expectancy +$1.26/trade**.',
              '- S2 does not require BTC-level economics yet because E20/F35 exits are intentionally frozen.',
              '- Final ETH acceptance remains contingent on BTC-level or better quality after target/invalidation and portfolio-lock calibration.','',
              '## Decision','',f'**Status: {status}**','',
              '- No TP, stop, runner, leverage, lifecycle, or live-code changes were made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())

if __name__=='__main__': main()
