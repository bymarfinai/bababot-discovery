#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import btc_f85_long_b27do_live_executable_exit_b27dq as dq


def _assign_utc_subset(q, mask, source):
    q['exit_ts'] = q['exit_ts'].astype(object)
    vals = list(pd.to_datetime(source, utc=True))
    q.loc[mask, 'exit_ts'] = vals
    q['exit_ts'] = pd.to_datetime(q['exit_ts'], utc=True)
    return q


def safe_build_old_hybrid(stream, breathing):
    q = stream.copy().reset_index(drop=True)
    b = breathing.copy().reset_index(drop=True)
    assert len(q) == len(b)
    mask = q.zone.isin(dq.do.RUNNER_ZONES)

    q['management_mode'] = 'FIXED_E20'
    q.loc[mask, 'management_mode'] = 'E10_BREATHING'
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']

    q = _assign_utc_subset(q, mask, b.loc[mask, 'exit_ts'])
    q.loc[mask, 'exit_px'] = b.loc[mask, 'exit_px'].astype(float).to_numpy()
    q.loc[mask, 'net_pnl_usd'] = b.loc[mask, 'net_pnl_usd'].astype(float).to_numpy()

    for c in ('runner_armed','runner_exit_reason','runner_final_floor_ext','runner_floor_raises','runner_delta_vs_fixed_candidate'):
        q[c] = pd.Series([None] * len(q), dtype=object)
        if c in b.columns:
            q.loc[mask, c] = b.loc[mask, c].astype(object).to_numpy()
    return q


def safe_build_live_hybrid(stream, live):
    q = stream.copy().reset_index(drop=True)
    l = live.copy().reset_index(drop=True)
    assert len(q) == len(l)
    mask = q.zone.isin(dq.RUNNER_ZONES)

    q['management_mode'] = 'FIXED_E20'
    q.loc[mask, 'management_mode'] = dq.VARIANT
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']

    q = _assign_utc_subset(q, mask, l.loc[mask, 'live_exit_ts'])
    q.loc[mask, 'exit_px'] = l.loc[mask, 'live_exit_px'].astype(float).to_numpy()
    q.loc[mask, 'net_pnl_usd'] = l.loc[mask, 'live_net_pnl_usd'].astype(float).to_numpy()

    cols = [
        'live_exit_reason','runner_armed','runner_arm_bar_start','runner_final_active_floor',
        'runner_pending_floor_count_at_exit','runner_scheduled_updates','runner_activations',
        'runner_ratchet_updates','runner_buffer_f35_exit','runner_max_high_ext',
        'runner_max_close_ext','runner_delta_vs_fixed_candidate'
    ]
    for c in cols:
        q[c] = pd.Series([None] * len(q), dtype=object)
        if c in l.columns:
            q.loc[mask, c] = l.loc[mask, c].astype(object).to_numpy()
    return q


def main():
    dq.do.build_hybrid = safe_build_old_hybrid
    dq.build_live_hybrid = safe_build_live_hybrid
    dq.main()


if __name__ == '__main__':
    main()
