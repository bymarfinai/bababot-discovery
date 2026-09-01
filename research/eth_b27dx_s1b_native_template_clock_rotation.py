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

PFX='ETH_B27DX_S1B_NATIVE_TEMPLATE_CLOCK_ROTATION'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_PROBES=ROOT/f'{PFX}_ProbeScores.csv'
OUT_CLOCKS=ROOT/f'{PFX}_ClockSummary.csv'
OUT_SUPPORTED=ROOT/f'{PFX}_SupportedClocks.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

TEMPLATES={
    'NATIVE_SHORT':(240,300),
    'NATIVE_CENTER':(300,360),
    'LEGACY_BENCHMARK':(330,390),
}
CLOCKS=tuple(range(0,1440,30))
ENTRY_PROBES=(0.90,0.85,0.80)
PARTS=('development','external','reference_validation')
VAL_PARTS=('external','reference_validation')
TARGET_EXT=0.20
STOP_F=0.35


def clock_label(v:int)->str:
    return f'{(v//60)%24:02d}:{v%60:02d}'

def probe_label(f:float)->str:
    return f'F{int(round(f*100)):02d}'

def dev_weeks()->float:
    a,z=b.m.m.PARTS['development']
    return float((z-a)/pd.Timedelta(days=7))

def finite_pf(v):
    if pd.isna(v):return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)

def score_probe(x,template:str,ref_min:int,horizon_min:int,part:str,exec_min:int,ef:float)->dict:
    r=b.score_config(x=x,part_name=part,side='LONG',exec_min=exec_min,ref_min=ref_min,
                     horizon_min=horizon_min,entry_f=ef,target_ext=TARGET_EXT,stop_f=STOP_F,stress_bps=0.0)
    r['template']=template;r['execution_utc']=clock_label(exec_min)
    r['reference_start_utc']=clock_label((exec_min-ref_min)%1440);r['probe']=probe_label(ef)
    if part=='development':
        r['positive']=bool(r['n']>=30 and r['pf']>=1.10 and r['expectancy']>0 and r['net']>0)
    else:
        r['positive']=bool(r['n']>=15 and r['pf']>1.00 and r['expectancy']>0 and r['net']>0)
    return r

def run_scores(x)->pd.DataFrame:
    rows=[]
    for template,(ref_min,horizon_min) in TEMPLATES.items():
        for exec_min in CLOCKS:
            for part in PARTS:
                for ef in ENTRY_PROBES:
                    rows.append(score_probe(x,template,ref_min,horizon_min,part,exec_min,ef))
    return pd.DataFrame(rows)

def summarize(scores:pd.DataFrame)->pd.DataFrame:
    rows=[];weeks=dev_weeks()
    for template,(ref_min,horizon_min) in TEMPLATES.items():
        for exec_min in CLOCKS:
            d=scores[(scores.template==template)&(scores.exec_min==exec_min)]
            dev=d[d.partition=='development']
            row={
                'template':template,'ref_min':ref_min,'horizon_min':horizon_min,'exec_min':exec_min,
                'execution_utc':clock_label(exec_min),'reference_start_utc':clock_label((exec_min-ref_min)%1440),
                'development_positive_probes':int(dev.positive.sum()),
                'development_median_pf':float(pd.Series([finite_pf(x) for x in dev.pf]).median()),
                'development_median_expectancy':float(pd.to_numeric(dev.expectancy,errors='coerce').median()),
                'development_median_n':float(pd.to_numeric(dev.n,errors='coerce').median()),
            }
            row['development_pass']=bool(row['development_positive_probes']>=2)
            row['raw_opportunities_per_week']=row['development_median_n']/weeks
            for p in VAL_PARTS:
                q=d[d.partition==p];pos=int(q.positive.sum());enough=int((pd.to_numeric(q.n,errors='coerce')>=15).sum())
                row[f'{p}_positive_probes']=pos;row[f'{p}_enough_n_probes']=enough
                row[f'{p}_pass']=bool(pos>=2 and enough>=2)
            row['supported']=bool(row['development_pass'] and row['external_pass'] and row['reference_validation_pass'])
            rows.append(row)
    return pd.DataFrame(rows)

def contiguous_runs(s:pd.DataFrame,template:str):
    vals=sorted(int(v) for v in s[(s.template==template)&s.supported].exec_min)
    if not vals:return []
    runs=[];cur=[vals[0]]
    for v in vals[1:]:
        if v-cur[-1]==30:cur.append(v)
        else:runs.append(cur);cur=[v]
    runs.append(cur)
    if len(runs)>1 and runs[0][0]==0 and runs[-1][-1]==1410:
        runs=[runs[-1]+[v+1440 for v in runs[0]]]+runs[1:-1]
    return runs

def fmt(x,nd=2):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.{nd}f}'

def main():
    x,coverage=b.m.m.load5()
    scores=run_scores(x);scores.to_csv(OUT_PROBES,index=False)
    clocks=summarize(scores);clocks.to_csv(OUT_CLOCKS,index=False)
    supported=clocks[clocks.supported].copy();supported.to_csv(OUT_SUPPORTED,index=False)

    stats={}
    for template in TEMPLATES:
        q=supported[supported.template==template]
        runs=contiguous_runs(clocks,template)
        stats[template]={
            'n_supported':len(q),'runs':runs,
            'max_run':max([len(r) for r in runs],default=0),
            'median_pf':float(q.development_median_pf.median()) if len(q) else np.nan,
            'raw_density_sum':float(q.raw_opportunities_per_week.sum()) if len(q) else 0.0,
        }
    legacy=stats['LEGACY_BENCHMARK']
    native_expansion=False
    for t in ('NATIVE_SHORT','NATIVE_CENTER'):
        if stats[t]['n_supported']>legacy['n_supported'] or (stats[t]['max_run']>=2 and legacy['max_run']<2):
            native_expansion=True
    total_supported=sum(v['n_supported'] for v in stats.values())
    if total_supported==0:status='ETH_S1B_NO_SUPPORTED_CLOCKS'
    elif native_expansion:status='ETH_S1B_NATIVE_CLOCK_EXPANSION_SUPPORTED'
    else:status='ETH_S1B_NATIVE_TEMPLATES_NO_EXPANSION'

    lines=['# ETH B27DX — S1B Native-Template Full Clock Rotation — Result','',
           f'ETH raw 5m coverage: **{coverage:.4%}**.','',
           'Three preregistered templates were rotated over all 48 UTC half-hour execution clocks using the exact frozen B27DX scorer.','',
           '## Template summary','',
           '| Template | Ref | Horizon | Supported clocks | Longest contiguous run | Median Dev PF | Raw density sum/wk* |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for t,(r,h) in TEMPLATES.items():
        z=stats[t]
        lines.append(f'| {t} | {r}m | {h}m | {z["n_supported"]} | {z["max_run"]} | {fmt(z["median_pf"])} | {z["raw_density_sum"]:.3f} |')
    lines += ['','*Raw density sum is an upper-bound structural diagnostic, not a portfolio trade rate; supported clocks can overlap.*','']

    for t,(r,h) in TEMPLATES.items():
        lines += [f'## {t} — R{r}/X{h}','','| Ref start | Exec start | Dev + | Dev PF | Ext + | Val + | Raw opp/week |','|---:|---:|---:|---:|---:|---:|---:|']
        q=supported[supported.template==t].sort_values('exec_min')
        if q.empty:lines.append('| - | - | - | - | - | - | - |')
        else:
            for xrow in q.itertuples(index=False):
                lines.append(f'| {xrow.reference_start_utc} | {xrow.execution_utc} | {int(xrow.development_positive_probes)}/3 | {fmt(xrow.development_median_pf)} | {int(xrow.external_positive_probes)}/3 | {int(xrow.reference_validation_positive_probes)}/3 | {xrow.raw_opportunities_per_week:.3f} |')
        lines += ['','Contiguous supported runs:']
        runs=stats[t]['runs']
        if not runs:lines.append('- None.')
        else:
            for run in runs:
                labels=[clock_label(v%1440) for v in run]
                lines.append(f'- **{" → ".join(labels)}** ({len(run)} points; width {30*(len(run)-1)}m).')
        lines.append('')

    lines += ['## Decision','',f'**Status: {status}**','',
              f'- Native clock expansion vs legacy: **{"SUPPORTED" if native_expansion else "NOT SUPPORTED"}**.',
              '- No entry/TP/stop/runner/leverage optimization was performed.',
              '- No live BBC changes were made.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())

if __name__=='__main__':main()
