#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import btc_f85_long_hybrid_exit_b27do as core


def build_hybrid_minimal(stream, breathing):
    q = stream.copy().reset_index(drop=True)
    b = breathing.copy().reset_index(drop=True)
    assert len(q) == len(b)
    mask = q.zone.isin(core.RUNNER_ZONES)

    q['management_mode'] = 'FIXED_E20'
    q.loc[mask, 'management_mode'] = 'E10_BREATHING'
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']

    # Only the fields used by portfolio locking and PnL scoring are replaced.
    q.loc[mask, 'exit_ts'] = pd.to_datetime(b.loc[mask, 'exit_ts'], utc=True)
    q.loc[mask, 'exit_px'] = b.loc[mask, 'exit_px'].to_numpy()
    q.loc[mask, 'net_pnl_usd'] = b.loc[mask, 'net_pnl_usd'].to_numpy()
    q['exit_ts'] = pd.to_datetime(q.exit_ts, utc=True)
    return q


core.build_hybrid = build_hybrid_minimal

if __name__ == '__main__':
    core.main()
