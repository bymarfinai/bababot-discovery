#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import eth_native_london_ny_entry_z4 as m
import eth_native_london_ny_entry_z4_corrected as c1


def summarize(C: pd.DataFrame, A: pd.DataFrame):
    rows = []
    parts = (*m.MAJOR, 'POOLED_MAJOR')
    for cohort in m.COHORTS:
        for mode in m.MODES:
            for part in parts:
                if part == 'POOLED_MAJOR':
                    c = C[(C.cohort == cohort) & C.partition.isin(m.MAJOR)]
                    a = A[(A.cohort == cohort) & (A['mode'] == mode) & A.partition.isin(m.MAJOR)]
                else:
                    c = C[(C.cohort == cohort) & (C.partition == part)]
                    a = A[(A.cohort == cohort) & (A['mode'] == mode) & (A.partition == part)]
                q = a[a.available.astype(bool)]
                denom = len(c); n = len(q)
                row = {
                    'cohort': cohort, 'mode': mode, 'partition': part,
                    'b00_cases': denom, 'available_entries': n,
                    'participation': n / denom if denom else np.nan,
                    'median_entry_frac': pd.to_numeric(q.entry_frac, errors='coerce').median() if n else np.nan,
                    'median_adverse_R': pd.to_numeric(q.adverse_R, errors='coerce').median() if n else np.nan,
                    'p90_adverse_R': pd.to_numeric(q.adverse_R, errors='coerce').quantile(.90) if n else np.nan,
                    'median_mfe_frac': pd.to_numeric(q.mfe_frac, errors='coerce').median() if n else np.nan,
                    'close_below_L_before_C20': int(q.close_below_L_before_C20.astype(bool).sum()) if n else 0,
                }
                for k in ('C05', 'C10', 'C20'):
                    hits = int(q[f'{k}_reached'].astype(bool).sum()) if n else 0
                    passed = int(q[f'{k}_already_passed'].astype(bool).sum()) if n else 0
                    row[f'{k}_reach'] = hits
                    row[f'{k}_reach_rate'] = hits / n if n else np.nan
                    row[f'{k}_already_passed'] = passed
                    if hits:
                        mins = []
                        for r in q[q[f'{k}_reached'].astype(bool)].itertuples(index=False):
                            ets = pd.Timestamp(r.entry_ts)
                            cts = pd.Timestamp(getattr(r, f'{k}_ts'))
                            mins.append(float((cts - ets) / pd.Timedelta(minutes=1)))
                        row[f'median_minutes_to_{k}'] = float(np.median(mins))
                    else:
                        row[f'median_minutes_to_{k}'] = np.nan
                row['unresolved_no_post_entry_C20'] = n - row['C20_reach'] - row['close_below_L_before_C20']
                rows.append(row)
    return pd.DataFrame(rows)


m.summarize = summarize

if __name__ == '__main__':
    c1.main()
