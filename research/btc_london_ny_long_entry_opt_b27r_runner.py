#!/usr/bin/env python3
"""B27R runner patch.

The first B27R run correctly aborted because audit assertions treated signals on the
final 5m of a session (which have no eligible post-signal entry bar) as if they must
still have a simulated planned order. Those rows are causally non-enterable and are
kept as NO_ELIGIBLE_5M. This patch only makes the audit condition conditional on a
planned price actually existing. It does not change signal selection, entry methods,
fill logic, exits, economics, selection criteria, or any trade outcome.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import btc_london_ny_long_entry_opt_b27r as m


def audit_real_fixed(x5: pd.DataFrame, signals: pd.DataFrame, trades: pd.DataFrame):
    assert (signals.transition == m.TRANSITION).all()
    assert (signals.side == m.SIDE).all()
    assert signals.k.isin(m.KS).all()
    assert (signals.opp_visits_at_signal == 0).all()
    assert (trades.transition == m.TRANSITION).all()
    assert (trades.opp_visits_at_signal == 0).all()

    ent = pd.to_datetime(trades.entry_ts, utc=True, errors='coerce')
    sig = pd.to_datetime(trades.signal_ts, utc=True, errors='coerce')
    assert ((ent >= sig) | ent.isna()).all()
    assert np.allclose(pd.to_numeric(trades.stop_px), pd.to_numeric(trades.previous_session_low))
    assert np.allclose(pd.to_numeric(trades.target_px), pd.to_numeric(trades.previous_session_high))

    # A signal on the final 5m bar has no eligible post-signal bar and therefore no
    # order can exist. For every order that DOES have a planned price, geometry must
    # match the frozen preregistered definition exactly.
    for method, frac in m.FRACS.items():
        g = trades[(trades.entry_method == method) & pd.to_numeric(trades.planned_entry_px, errors='coerce').notna()]
        expect = g.previous_session_low.astype(float) + frac * (g.previous_session_high.astype(float) - g.previous_session_low.astype(float))
        assert np.allclose(g.planned_entry_px.astype(float), expect.astype(float))

    # NEXT_OPEN exact mapping for causally enterable rows only.
    for r in trades[(trades.entry_method == 'NEXT_OPEN') & trades.planned_valid.astype(bool)].itertuples(index=False):
        ts = pd.Timestamp(r.signal_ts)
        pos = int(x5.index.searchsorted(ts, side='left'))
        assert pos < len(x5) and x5.index[pos] == ts
        assert abs(float(r.planned_entry_px) - float(x5.iloc[pos].open)) < 1e-9

    # Local methods must come only from the completed signal bar whenever an order exists.
    for method in ('SIG_MID', 'SIG_LOW'):
        g = trades[(trades.entry_method == method) & pd.to_numeric(trades.planned_entry_px, errors='coerce').notna()]
        for r in g.itertuples(index=False):
            ts = pd.Timestamp(r.signal_bar_start)
            pos = int(x5.index.searchsorted(ts, side='left'))
            assert pos < len(x5) and x5.index[pos] == ts
            row = x5.iloc[pos]
            exp = (float(row.high) + float(row.low)) / 2.0 if method == 'SIG_MID' else float(row.low)
            assert abs(float(r.planned_entry_px) - exp) < 1e-9

    # No filled limit has a strict close-break before its fill.
    lim = trades[(trades.entry_method != 'NEXT_OPEN') & trades.filled.astype(bool)]
    for r in lim.itertuples(index=False):
        q = m.fast_slice(x5, pd.Timestamp(r.signal_ts), pd.Timestamp(r.entry_ts))
        if len(q):
            assert not ((q.close.astype(float) > float(r.previous_session_high)) |
                        (q.close.astype(float) < float(r.previous_session_low))).any()

    # Explicitly verify all rows without a planned price are non-enterable final-bar cases.
    missing = trades[pd.to_numeric(trades.planned_entry_px, errors='coerce').isna()]
    assert set(missing.exit_reason.unique()).issubset({'NO_ELIGIBLE_5M'})


m.audit_real = audit_real_fixed
m.main()
