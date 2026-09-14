#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd
import requests

import sol_orb_reference_fidelity_v1 as detector


def fetch_one_with_volume(url: str):
    r = requests.get(
        url,
        timeout=90,
        headers={'User-Agent': 'bababot-sol-orb-reference-fidelity-v1/1.0'},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh,
                header=None,
                usecols=[0, 1, 2, 3, 4, 5],
                names=['ts', 'open', 'high', 'low', 'close', 'volume'],
            )


def econ_summary_fixed(ev, by_year=False):
    rows = []
    group_cols = ['hour_utc', 'year'] if by_year else 'hour_utc'
    for keys, g in ev.groupby(group_cols):
        if by_year:
            hour, year = keys
        else:
            hour, year = keys, None
        for v in detector.VARIANTS:
            for h in detector.HORIZONS:
                col = f'{v}_pnl_{h}m_usd'
                ret = f'{v}_net_{h}m_pct'
                gg = g.dropna(subset=[col]).sort_values(f'{v}_entry_time')
                p = gg[col].astype(float)
                row = {
                    'hour_utc': int(hour),
                    'hour_wib': int((int(hour) + 7) % 24),
                    'variant': v,
                    'exit_minutes': h,
                    'n': len(gg),
                    'net_wr': float((gg[ret] > 0).mean()) if len(gg) else np.nan,
                    'net_pnl_usd': float(p.sum()) if len(gg) else np.nan,
                    'expectancy_usd': float(p.mean()) if len(gg) else np.nan,
                    'profit_factor': detector.profit_factor(p),
                }
                if by_year:
                    row['year'] = int(year)
                else:
                    row['max_dd_usd'] = detector.max_drawdown(p)
                    row['max_loss_streak'] = detector.max_loss_streak(p)
                rows.append(row)
    sort_cols = ['variant', 'hour_utc', 'exit_minutes'] + (['year'] if by_year else [])
    return pd.DataFrame(rows).sort_values(sort_cols)


def main():
    detector.base.fetch_one = fetch_one_with_volume
    detector.econ_summary = econ_summary_fixed
    detector.main()


if __name__ == '__main__':
    main()
