#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
import btc_h1_low_reject_structure_lr1 as dataio

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_WEEKLY_RANGE_Diagnostic.md'
OUT_JSON=ROOT/'BTC_WEEKLY_RANGE_Diagnostic.json'
OUT_CSV=ROOT/'BTC_WEEKLY_RANGE_Diagnostic.csv'


def week_key(ts):
    iso=pd.Timestamp(ts).isocalendar()
    return f'{int(iso.year):04d}-W{int(iso.week):02d}'

def main():
    x=dataio.load_1h().copy()
    x['ts']=pd.to_datetime(x.ts,utc=True)
    x=x.sort_values('ts').drop_duplicates('ts').set_index('ts')
    # ISO weeks; require full Monday 00:00 through Sunday 23:00 = 168 H1 bars.
    iso=x.index.isocalendar()
    x['iso_year']=iso.year.astype(int).to_numpy()
    x['iso_week']=iso.week.astype(int).to_numpy()
    rows=[]
    for (y,w),g in x.groupby(['iso_year','iso_week'],sort=True):
        if len(g)!=168:
            continue
        start=g.index.min(); end=g.index.max()
        if start.weekday()!=0 or start.hour!=0 or end.weekday()!=6 or end.hour!=23:
            continue
        hi=float(g.high.max()); lo=float(g.low.min())
        hi_ts=g.high.idxmax(); lo_ts=g.low.idxmin()
        high_to_low=(hi-lo)/hi
        low_to_high=(hi-lo)/lo
        first='HIGH_FIRST' if hi_ts<lo_ts else ('LOW_FIRST' if lo_ts<hi_ts else 'SAME_BAR')
        rows.append({
            'week':f'{y:04d}-W{w:02d}','week_start':start,'week_end':end,
            'high':hi,'high_ts':hi_ts,'low':lo,'low_ts':lo_ts,
            'high_to_low_pct':100*high_to_low,'low_to_high_pct':100*low_to_high,
            'extreme_order':first
        })
    z=pd.DataFrame(rows)
    z.to_csv(OUT_CSV,index=False)
    a=z.high_to_low_pct.to_numpy(float); b=z.low_to_high_pct.to_numpy(float)
    def summ(v):
        return {
            'n':int(len(v)), 'mean':float(np.mean(v)), 'median':float(np.median(v)),
            'min':float(np.min(v)), 'p10':float(np.quantile(v,.10)), 'p25':float(np.quantile(v,.25)),
            'p75':float(np.quantile(v,.75)), 'p90':float(np.quantile(v,.90)), 'max':float(np.max(v))
        }
    buckets={
        'gte_1pct':int((a>=1).sum()),'gte_2pct':int((a>=2).sum()),'gte_3pct':int((a>=3).sum()),
        'gte_4pct':int((a>=4).sum()),'gte_5pct':int((a>=5).sum()),'gte_7_5pct':int((a>=7.5).sum()),
        'gte_10pct':int((a>=10).sum())
    }
    out={
        'coverage':{'first':str(x.index.min()),'last':str(x.index.max()),'h1_rows':int(len(x))},
        'complete_iso_weeks':int(len(z)),
        'high_to_low_pct':summ(a),'low_to_high_pct':summ(b),
        'high_to_low_threshold_counts':buckets,
        'high_first_weeks':int((z.extreme_order=='HIGH_FIRST').sum()),
        'low_first_weeks':int((z.extreme_order=='LOW_FIRST').sum()),
        'smallest_10':z.nsmallest(10,'high_to_low_pct').to_dict('records'),
        'largest_10':z.nlargest(10,'high_to_low_pct').to_dict('records'),
    }
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    s=out['high_to_low_pct']; u=out['low_to_high_pct']; n=len(z)
    md=['# BTC Weekly High-Low Range Diagnostic','',
        f"Coverage **{x.index.min()} -> {x.index.max()}**, official H1 rows **{len(x):,}**. Complete ISO weeks only: **{n}**.",'',
        'Two definitions are reported:','- High→Low drawdown = `(High-Low)/High`.','- Low→High upside = `(High-Low)/Low`.','',
        '## Distribution','',
        '| Metric | Mean | Median | Min | P10 | P25 | P75 | P90 | Max |','|---|---:|---:|---:|---:|---:|---:|---:|---:|',
        f"| High→Low | {s['mean']:.2f}% | {s['median']:.2f}% | {s['min']:.2f}% | {s['p10']:.2f}% | {s['p25']:.2f}% | {s['p75']:.2f}% | {s['p90']:.2f}% | {s['max']:.2f}% |",
        f"| Low→High | {u['mean']:.2f}% | {u['median']:.2f}% | {u['min']:.2f}% | {u['p10']:.2f}% | {u['p25']:.2f}% | {u['p75']:.2f}% | {u['p90']:.2f}% | {u['max']:.2f}% |",'',
        '## Weekly high→low room thresholds','']
    for k,label in [('gte_1pct','>=1%'),('gte_2pct','>=2%'),('gte_3pct','>=3%'),('gte_4pct','>=4%'),('gte_5pct','>=5%'),('gte_7_5pct','>=7.5%'),('gte_10pct','>=10%')]:
        c=buckets[k]; md.append(f'- {label}: **{c}/{n} weeks ({100*c/n:.2f}%)**')
    md += ['',f"Extreme order: high occurred first in **{out['high_first_weeks']}** weeks; low occurred first in **{out['low_first_weeks']}** weeks.",'','## 10 narrowest complete weeks','', '| Week | High→Low | Low→High | Order |','|---|---:|---:|---|']
    for _,r in z.nsmallest(10,'high_to_low_pct').iterrows():
        md.append(f"| {r.week} | {r.high_to_low_pct:.2f}% | {r.low_to_high_pct:.2f}% | {r.extreme_order} |")
    md += ['', '## 10 widest complete weeks','', '| Week | High→Low | Low→High | Order |','|---|---:|---:|---|']
    for _,r in z.nlargest(10,'high_to_low_pct').iterrows():
        md.append(f"| {r.week} | {r.high_to_low_pct:.2f}% | {r.low_to_high_pct:.2f}% | {r.extreme_order} |")
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
