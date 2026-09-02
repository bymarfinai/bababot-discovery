#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
M8=ROOT/'ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX_Summary.csv'
M9T=ROOT/'ETH_LONDON_NY_M9_POST_BREAKOUT_PROFIT_PROTECTION_Trades.csv'
M9S=ROOT/'ETH_LONDON_NY_M9_POST_BREAKOUT_PROFIT_PROTECTION_Summary.csv'
OUT=ROOT/'ETH_LONDON_NY_M9A_AUDIT_FIX_Result.md'
STATUS=ROOT/'ETH_LONDON_NY_M9A_AUDIT_FIX_Status.txt'
BAR5=pd.Timedelta(minutes=5)
PARTS=('external','development','reference_validation','august','POOLED_MAJOR')


def same(a,b,tol=1e-10):
    a=float(a) if pd.notna(a) else float('nan')
    b=float(b) if pd.notna(b) else float('nan')
    if math.isnan(a) and math.isnan(b): return True
    if math.isnan(a) or math.isnan(b): return False
    return abs(a-b)<=tol*max(1.0,abs(a),abs(b))


def main():
    m8=pd.read_csv(M8)
    t=pd.read_csv(M9T)
    s=pd.read_csv(M9S)
    for c in ('entry_bar_start','breakout_bar_start','exit_bar_start','exit_ts'):
        t[c]=pd.to_datetime(t[c],utc=True,errors='coerce')

    ref=m8[(m8.target_name=='E15')&(m8.risk_name=='F50')].copy()
    base=s[s.variant=='BASE_F50'].copy()
    parity=[]
    details=[]
    for p in PARTS:
        a=base[base.partition==p].iloc[0]
        b=ref[ref.partition==p].iloc[0]
        ok=(int(a.n_0)==int(b.n_0) and same(a.wr_0,b.wr_0) and same(a.pf_0,b.pf_0) and
            same(a.net_0,b.net_0,1e-9) and same(a.pf_5,b.pf_5) and same(a.net_5,b.net_5,1e-9))
        parity.append(ok)
        details.append((p,ok,int(a.n_0),a.wr_0,a.pf_0,a.net_0))

    floorish=t[t.exit_reason.isin(['FLOOR_TOUCH','FLOOR_GAP_OPEN','AMBIGUOUS_BOTH'])].copy()
    chronology=bool(len(floorish)==0 or (
        floorish.breakout_bar_start.notna().all() and
        (floorish.exit_bar_start >= floorish.breakout_bar_start + BAR5).all()
    ))
    rows_ok=(len(t)==380 and t.cohort_id.nunique()==95 and set(t.variant.unique())=={'BASE_F50','BO_FLOOR_F90','BO_FLOOR_F95','BO_FLOOR_H'})
    base_rows=bool(len(t[t.variant=='BASE_F50'])==95)
    ok=bool(all(parity) and chronology and rows_ok and base_rows)

    lines=['# ETH London -> New York M9A Audit Fix — Result','',
           'M9A changes no result-bearing trade semantics or economic outputs. It validates the already-persisted M9 files with NaN-safe zero-N parity and explicit floor chronology.','',
           '## M8 E15/F50 baseline parity','',
           '| Partition | Pass | N | WR | PF | Net |','|---|---|---:|---:|---:|---:|']
    for p,po,n,wr,pf,net in details:
        def f(v): return '-' if pd.isna(v) else f'{float(v):.6f}'
        lines.append(f'| {p} | {"PASS" if po else "FAIL"} | {n} | {f(wr)} | {f(pf)} | {f(net)} |')
    lines += ['',f'- Floor activation chronology: **{"PASS" if chronology else "FAIL"}**.',
              f'- Persisted 95-cohort × 4-variant shape: **{"PASS" if rows_ok else "FAIL"}**.',
              f'- Baseline row count: **{"PASS" if base_rows else "FAIL"}**.','',
              f'**Status: {"ETH_LONDON_NY_M9_AUDIT_VALID" if ok else "ETH_LONDON_NY_M9_AUDIT_INVALID"}**']
    OUT.write_text('\n'.join(lines))
    STATUS.write_text(('ETH_LONDON_NY_M9_AUDIT_VALID' if ok else 'ETH_LONDON_NY_M9_AUDIT_INVALID')+'\n')
    print(OUT.read_text())

if __name__=='__main__':
    main()
