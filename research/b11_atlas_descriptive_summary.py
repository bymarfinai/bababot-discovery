#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_FAST_Atlas.csv'
OUT=ROOT/'BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_DESCRIPTIVE_Summary.md'
OUTCSV=ROOT/'BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_DESCRIPTIVE_Top.csv'

def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'

def main():
    x=pd.read_csv(SRC)
    # Pivot external and validation for each exact TF/family/mode.
    keys=['source_tf','family','mode']
    ext=x[x.partition=='external'].set_index(keys)
    val=x[x.partition=='reference_validation'].set_index(keys)
    dev=x[x.partition=='development'].set_index(keys)
    common=ext.index.intersection(val.index).intersection(dev.index)
    rows=[]
    for k in common:
        e=ext.loc[k]; v=val.loc[k]; d=dev.loc[k]
        rows.append({
            'source_tf':k[0],'family':k[1],'mode':k[2],
            'dev_cov':d.weekly_coverage,'dev_wr':d.weekly_wr,
            'ext_cov':e.weekly_coverage,'ext_wr':e.weekly_wr,
            'val_cov':v.weekly_coverage,'val_wr':v.weekly_wr,
            'ext_raw_wr':e.raw_candidate_wr,'val_raw_wr':v.raw_candidate_wr,
            'min_oos_cov':min(e.weekly_coverage,v.weekly_coverage),
            'min_oos_wr':min(e.weekly_wr,v.weekly_wr),
            'mean_oos_wr':np.mean([e.weekly_wr,v.weekly_wr]),
            'ext_n':int(e.candidate_n),'val_n':int(v.candidate_n),
            'ext_median_hours':e.median_hours,'val_median_hours':v.median_hours,
        })
    z=pd.DataFrame(rows)
    z=z.sort_values(['min_oos_wr','min_oos_cov','mean_oos_wr'],ascending=[False,False,False])
    z.to_csv(OUTCSV,index=False)
    lines=['# B11 MTF Atlas — Descriptive OOS Summary','',
           'Descriptive only. No row below is promoted as a strategy; B11 anti-rescue remains binding.','']
    for tf in ['H1','H4','D1','W1']:
        q=z[z.source_tf==tf].copy()
        lines += [f'## {tf} — best consistent OOS reaction rows','',
                  '| Family | Mode | Ext cov/WR | Val cov/WR | Min OOS WR | Raw ext/val |',
                  '|---|---|---:|---:|---:|---:|']
        for _,r in q.head(12).iterrows():
            lines.append(f"| {r.family} | {r['mode']} | {pct(r.ext_cov)} / {pct(r.ext_wr)} | {pct(r.val_cov)} / {pct(r.val_wr)} | {pct(r.min_oos_wr)} | {pct(r.ext_raw_wr)} / {pct(r.val_raw_wr)} |")
        hi=q[q.min_oos_cov>=0.90].sort_values(['min_oos_wr','mean_oos_wr'],ascending=False)
        lines += ['',f'### {tf} with >=90% coverage in BOTH OOS partitions','']
        if hi.empty:
            lines.append('None.')
        else:
            lines += ['| Family | Mode | Ext cov/WR | Val cov/WR | Min OOS WR |','|---|---|---:|---:|---:|']
            for _,r in hi.head(10).iterrows():
                lines.append(f"| {r.family} | {r['mode']} | {pct(r.ext_cov)} / {pct(r.ext_wr)} | {pct(r.val_cov)} / {pct(r.val_wr)} | {pct(r.min_oos_wr)} |")
        lines.append('')
    # Global rows, coverage bands.
    lines += ['## Global best by minimum OOS coverage band','']
    for cut in [1.0,0.95,0.90,0.75,0.50,0.25]:
        q=z[z.min_oos_cov>=cut].sort_values(['min_oos_wr','mean_oos_wr'],ascending=False)
        if len(q):
            r=q.iloc[0]
            lines.append(f"- >= {100*cut:.0f}% both-partition coverage: `{r.source_tf}|{r.family}|{r['mode']}` — ext {pct(r.ext_cov)}/{pct(r.ext_wr)}, val {pct(r.val_cov)}/{pct(r.val_wr)}, min OOS WR {pct(r.min_oos_wr)}.")
        else:
            lines.append(f'- >= {100*cut:.0f}% both-partition coverage: none.')
    OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__': main()
