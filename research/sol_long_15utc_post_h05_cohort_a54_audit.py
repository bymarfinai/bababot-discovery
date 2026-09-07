#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A53_PATH=Path(__file__).resolve().parent/'sol_long_15utc_executable_guard_a53.py'
spec=importlib.util.spec_from_file_location('a53',A53_PATH)
a53=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a53)
OUT=ROOT/'SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_COHORT_AUDIT.md'
OUTCSV=ROOT/'SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_COHORT_AUDIT.csv'

def main():
    x,cov=a53.a2.a1.load5(); m=a53.a2.make_market_with_open(x)
    t=a53.replay(m)
    q=t[(t.guard=='G2_POST_H05') & t.guard_exit.astype(bool)].copy()
    rows=[]
    for (part,won,reason,lc),z in q.groupby(['partition','parent_won','parent_exit_reason','parent_loss_class'],dropna=False,sort=True):
        rows.append({'partition':part,'parent_won':bool(won),'parent_exit_reason':str(reason),'parent_loss_class':str(lc),'n':len(z)})
    s=pd.DataFrame(rows)
    s.to_csv(OUTCSV,index=False)
    lines=['# A54 Frozen POST_H05 Cohort Technical Audit','',f'Raw coverage: **{100*cov:.4f}%**.','',
           'This is a technical audit of the already-frozen A53 `G2_POST_H05` guard-exit cohort. It does not change A54 thresholds, candidates, or gates.','',
           f'Total G2 guard exits: **{len(q)}**.','',
           '| Partition | Parent won | Parent exit reason | Parent loss class | N |','|---|---:|---|---|---:|']
    for _,r in s.iterrows():
        lines.append(f"| {r.partition} | {str(bool(r.parent_won))} | {r.parent_exit_reason} | {r.parent_loss_class} | {int(r.n)} |")
    lines += ['','## Partition totals','', '| Partition | G2 exits | PnL>0 parent | TARGET parent | non-TARGET positive | M2 failed-break parent | other nonpositive |','|---|---:|---:|---:|---:|---:|---:|']
    for p in a53.PARTS:
        z=q[q.partition==p]
        positive=z.parent_won.astype(bool)
        target=(z.parent_exit_reason.astype(str)=='TARGET')
        m2=z.parent_loss_class.astype(str).str.startswith(('L2_','L3_','L4_','L5_'))
        lines.append(f"| {p} | {len(z)} | {int(positive.sum())} | {int((positive & target).sum())} | {int((positive & ~target).sum())} | {int((~positive & m2).sum())} | {int((~positive & ~m2).sum())} |")
    OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT.read_text())
if __name__=='__main__': main()
