#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import btc_generic_f85_long_clock_scan_b27de as core


def corrected_london_parity(cases: pd.DataFrame) -> pd.DataFrame:
    q = cases[(cases.clock_min == core.BASELINE_MIN) & cases.partition.isin(core.PART_ORDER)].copy()
    tr = q[q.entry_executed.astype(bool) & q.net_pnl_usd.notna()].copy()

    expected_counts = {'external': 27, 'development': 30, 'reference_validation': 11, 'august': 1}
    rows = []
    for part in core.PART_ORDER:
        z = tr[tr.partition == part]
        rows.append({'check': f'count_{part}', 'actual': len(z), 'expected': expected_counts[part], 'pass': len(z) == expected_counts[part]})

    major = tr[tr.partition.isin(core.MAJOR)].copy()
    vals = pd.to_numeric(major.net_pnl_usd, errors='coerce')
    n = len(major)
    wins = int((vals > 0).sum())
    wr = float((vals > 0).mean()) if n else np.nan
    p = core.pf(vals)
    exp = float(vals.mean()) if n else np.nan
    total = float(vals.sum()) if n else np.nan
    rows += [
        {'check': 'pooled_major_n', 'actual': n, 'expected': 68, 'pass': n == 68},
        {'check': 'pooled_major_wins', 'actual': wins, 'expected': 50, 'pass': wins == 50},
        {'check': 'pooled_major_wr', 'actual': wr, 'expected': 50/68, 'pass': abs(wr - 50/68) < 1e-12 if n else False},
        {'check': 'pooled_major_pf', 'actual': p, 'expected': 1.70, 'pass': pd.notna(p) and abs(float(p) - 1.70) <= 0.03},
        {'check': 'pooled_major_expectancy', 'actual': exp, 'expected': 0.91, 'pass': pd.notna(exp) and abs(float(exp) - 0.91) <= 0.03},
        {'check': 'pooled_major_total', 'actual': total, 'expected': 61.80, 'pass': pd.notna(total) and abs(float(total) - 61.80) <= 0.15},
    ]

    if core.EXISTING_AA.exists():
        aa = pd.read_csv(core.EXISTING_AA)
        aa = aa[(aa.variant == 'SAME_BAR_REJECTION') & (aa.entry_executed.astype(str).str.lower() == 'true')].copy()
        aa['entry_bar_start'] = pd.to_datetime(aa.entry_bar_start, utc=True)
        tr['entry_bar_start'] = pd.to_datetime(tr.entry_bar_start, utc=True)
        akeys = set(zip(aa.partition.astype(str), aa.entry_bar_start.astype(str)))
        gkeys = set(zip(tr.partition.astype(str), tr.entry_bar_start.astype(str)))
        rows.append({'check': 'exact_entry_timestamp_identity', 'actual': len(gkeys & akeys), 'expected': len(akeys), 'pass': gkeys == akeys})

    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DE corrected London parity gate failed:\n' + out.to_string(index=False))
    return out


core.london_parity = corrected_london_parity

if __name__ == '__main__':
    core.main()
