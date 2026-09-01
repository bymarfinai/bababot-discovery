#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
BASE_PATH=HERE/'eth_b27dx_pair_calibration_v2.py'
spec=importlib.util.spec_from_file_location('eth_v2_base',BASE_PATH); b=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(b)

PFX='ETH_B27DX_S3B_INVALIDATION_GEOMETRY'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_SCORES=ROOT/f'{PFX}_Scores.csv'; OUT_SUMMARY=ROOT/f'{PFX}_StopSummary.csv'; OUT_ROBUST=ROOT/f'{PFX}_RobustClockStops.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
REF_MIN=300; HORIZON_MIN=360; ENTRY_F=0.80; TARGET_EXT=0.25
CLOCKS=(300,540,600,960)
STOPS=(0.60,0.55,0.50,0.45,0.40,0.35,0.30,0.25,0.20,0.15)
PARTS=('development','external','reference_validation')
BTC_WR=0.719298; BTC_PF=2.223193; BTC_EXP=1.26

def clock_label(v): return f'{(v//60)%24:02d}:{v%60:02d}'
def f_label(v): return f'F{int(round(v*100)):02d}'
def finite(v):
    if pd.isna(v): return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)
def positive(part,r):
    if part=='development': return bool(r['n']>=30 and r['pf']>=1.10 and r['expectancy']>0 and r['net']>0)
    return bool(r['n']>=15 and r['pf']>1.00 and r['expectancy']>0 and r['net']>0)

def run_scores(x):
    rows=[]
    for sf in STOPS:
        for ex in CLOCKS:
            for p in PARTS:
                r=b.score_config(x=x,part_name=p,side='LONG',exec_min=ex,ref_min=REF_MIN,horizon_min=HORIZON_MIN,
                                 entry_f=ENTRY_F,target_ext=TARGET_EXT,stop_f=sf,stress_bps=0.0)
                r['execution_utc']=clock_label(ex); r['stop']=f_label(sf); r['positive']=positive(p,r); rows.append(r)
    return pd.DataFrame(rows)

def summarize(scores):
    robust_rows=[]
    for sf in STOPS:
        for ex in CLOCKS:
            q=scores[(scores.stop_f==sf)&(scores.exec_min==ex)]
            if len(q)==3 and all(bool(q.loc[q.partition==p,'positive'].iloc[0]) for p in PARTS):
                robust_rows.append({'stop_f':sf,'stop':f_label(sf),'exec_min':ex,'execution_utc':clock_label(ex)})
    robust=pd.DataFrame(robust_rows); rows=[]
    for sf in STOPS:
        q=scores[scores.stop_f==sf]; clocks=[] if robust.empty else robust.loc[robust.stop_f==sf,'execution_utc'].tolist()
        row={'stop_f':sf,'stop':f_label(sf),'robust_clock_count':len(clocks),'robust_clocks':','.join(clocks),'supported':len(clocks)>=2}
        for p in PARTS:
            z=q[q.partition==p]
            row[f'{p}_median_wr']=float(pd.to_numeric(z.wr,errors='coerce').median())
            row[f'{p}_median_pf']=float(pd.Series([finite(v) for v in z.pf]).median())
            row[f'{p}_median_exp']=float(pd.to_numeric(z.expectancy,errors='coerce').median())
            row[f'{p}_median_max_ls']=float(pd.to_numeric(z.max_ls,errors='coerce').median())
        z=q[q.execution_utc.isin(clocks)] if clocks else q.iloc[0:0]
        wr=pd.to_numeric(z.wr,errors='coerce').dropna(); pf=[finite(v) for v in z.pf if not pd.isna(v)]; exp=pd.to_numeric(z.expectancy,errors='coerce').dropna(); ls=pd.to_numeric(z.max_ls,errors='coerce').dropna()
        row['robust_major_median_wr']=float(wr.median()) if len(wr) else np.nan
        row['robust_major_median_pf']=float(np.median(pf)) if pf else np.nan
        row['robust_major_median_exp']=float(exp.median()) if len(exp) else np.nan
        row['robust_major_median_max_ls']=float(ls.median()) if len(ls) else np.nan
        row['btc_wr_gap_pp']=100*(row['robust_major_median_wr']-BTC_WR) if len(wr) else np.nan
        row['btc_pf_gap']=row['robust_major_median_pf']-BTC_PF if pf else np.nan
        row['btc_exp_gap']=row['robust_major_median_exp']-BTC_EXP if len(exp) else np.nan
        rows.append(row)
    return pd.DataFrame(rows),robust

def runs(summary):
    vals=[float(r.stop_f) for r in summary.sort_values('stop_f',ascending=False).itertuples(index=False) if bool(r.supported)]
    if not vals:return []
    out=[];cur=[vals[0]]
    for v in vals[1:]:
        if abs((cur[-1]-v)-0.05)<1e-9:cur.append(v)
        else:out.append(cur);cur=[v]
    out.append(cur);return out

def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=b.m.m.load5(); scores=run_scores(x); scores.to_csv(OUT_SCORES,index=False); summary,robust=summarize(scores); summary.to_csv(OUT_SUMMARY,index=False); robust.to_csv(OUT_ROBUST,index=False)
    rr=runs(summary); fam=[x for x in rr if len(x)>=2]
    status='ETH_S3B_NATIVE_INVALIDATION_FAMILY_SUPPORTED' if fam else ('ETH_S3B_SUPPORTED_STOPS_NO_FAMILY' if bool(summary.supported.any()) else 'ETH_S3B_NO_SUPPORTED_STOP')
    lines=['# ETH B27DX — S3B Native Invalidation Geometry — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen: R300/X360, entry **F80**, target **E25**, clocks **05:00, 09:00, 10:00, 16:00 UTC**. Only completed-close invalidation varies.','',
           '## Invalidation summary','',
           '| Stop | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Robust-major Exp | Supported |',
           '|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in summary.itertuples(index=False):
        lines.append(f'| {r.stop} | {r.robust_clock_count}/4 | {r.robust_clocks or "-"} | {pct(r.development_median_wr)} | {fmt(r.development_median_pf)} | {pct(r.external_median_wr)} | {fmt(r.external_median_pf)} | {pct(r.reference_validation_median_wr)} | {fmt(r.reference_validation_median_pf)} | {pct(r.robust_major_median_wr)} | {fmt(r.robust_major_median_pf)} | {fmt(r.robust_major_median_exp)} | {"YES" if r.supported else "NO"} |')
    lines += ['','## Robust clock × invalidation pairs','']
    if robust.empty: lines.append('None.')
    else:
        lines += ['| Stop | Clock |','|---:|---:|']
        for r in robust.sort_values(['stop_f','exec_min'],ascending=[False,True]).itertuples(index=False): lines.append(f'| {r.stop} | {r.execution_utc} |')
    lines += ['','## Supported invalidation-family runs','']
    if not rr: lines.append('None.')
    else:
        for i,run in enumerate(rr,1): lines.append(f'- Run {i}: **{" → ".join(f_label(v) for v in run)}** ({len(run)} adjacent stops).')
    lines += ['','## BTC benchmark diagnostic','',
              '- BTC B27DX LONG final: **WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3**.',
              '- S3B promotion is topology-based, not benchmark-maximization.','','## Decision','',f'**Status: {status}**','',
              '- No entry, target, runner, leverage, lifecycle, clock, or live-code changes were made.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
