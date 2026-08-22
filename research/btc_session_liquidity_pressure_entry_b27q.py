#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_previous_session_direct_sweep_b26c as b26c

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Result.md'
OUT_VISITS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Visits.csv'
OUT_SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_TRADES = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Trades.csv'
OUT_STRUCT = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_StructuralSummary.csv'
OUT_ENTRY = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_EntrySummary.csv'
OUT_STATUS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_StatusCounts.csv'

PARTS = b22b.PARTS
TRANSITIONS = b26c.TRANSITIONS
BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE_USD = 0.40
KS = (1, 2, 3)
DEPTHS = ('SHALLOW', 'MID', 'DEEP', 'NEAR_OPPOSITE_EDGE')
MAJOR_PARTS = ('external', 'development', 'reference_validation')

# Fraction from previous-session Low (0) to High (1).
ENTRY_FRAC = {
    'LONG': {
        'SHALLOW': 0.75,
        'MID': 0.50,
        'DEEP': 0.25,
        'NEAR_OPPOSITE_EDGE': 0.10,
    },
    'SHORT': {
        'SHALLOW': 0.25,
        'MID': 0.50,
        'DEEP': 0.75,
        'NEAR_OPPOSITE_EDGE': 0.90,
    },
}


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def scan_session(q5: pd.DataFrame, prev_hi: float, prev_lo: float):
    """Chronological 5m census of exact frozen High/Low visits before first strict breakout."""
    assert prev_hi > prev_lo
    hi_visits = 0
    lo_visits = 0
    hi_touching = False
    lo_touching = False
    visits = []

    for ts, r in q5.iterrows():
        high = float(r.high)
        low = float(r.low)
        close = float(r.close)

        # Final breakout is evaluated first and is never counted as a touch.
        break_hi = close > prev_hi
        break_lo = close < prev_lo
        if break_hi and break_lo:
            raise AssertionError('Impossible strict close beyond both ordered range edges')
        if break_hi or break_lo:
            return {
                'status': 'OK',
                'breakout_side': 'HIGH' if break_hi else 'LOW',
                'breakout_bar_start': ts,
                'breakout_ts': ts + BAR5,
                'visits': visits,
                'high_visits': hi_visits,
                'low_visits': lo_visits,
            }

        hit_hi = high >= prev_hi and close <= prev_hi
        hit_lo = low <= prev_lo and close >= prev_lo

        # One 5m candle spanning both frozen edges has unknown visit order.
        if hit_hi and hit_lo:
            return {
                'status': 'AMBIGUOUS_BOTH_LEVELS',
                'breakout_side': None,
                'breakout_bar_start': pd.NaT,
                'breakout_ts': pd.NaT,
                'visits': [],
                'high_visits': np.nan,
                'low_visits': np.nan,
            }

        if hit_hi and not hi_touching:
            hi_visits += 1
            visits.append({
                'level': 'HIGH',
                'visit_no': hi_visits,
                'visit_bar_start': ts,
                'visit_ts': ts + BAR5,
                'same_visits_at_event': hi_visits,
                'opp_visits_at_event': lo_visits,
            })
        if hit_lo and not lo_touching:
            lo_visits += 1
            visits.append({
                'level': 'LOW',
                'visit_no': lo_visits,
                'visit_bar_start': ts,
                'visit_ts': ts + BAR5,
                'same_visits_at_event': lo_visits,
                'opp_visits_at_event': hi_visits,
            })

        hi_touching = bool(hit_hi)
        lo_touching = bool(hit_lo)

    return {
        'status': 'OK',
        'breakout_side': None,
        'breakout_bar_start': pd.NaT,
        'breakout_ts': pd.NaT,
        'visits': visits,
        'high_visits': hi_visits,
        'low_visits': lo_visits,
    }


def structural_outcome(signal_level: str, breakout_side: str | None) -> str:
    if breakout_side is None:
        return 'NO_BREAK'
    return 'TARGET_BREAK' if breakout_side == signal_level else 'OPPOSITE_BREAK'


def find_fill(q5: pd.DataFrame, signal_ts: pd.Timestamp, prev_hi: float, prev_lo: float, entry_px: float):
    """Order eligible from next 5m bar; strict close-break cancels before any ambiguous same-bar fill."""
    start_i = int(q5.index.searchsorted(signal_ts, side='left'))
    for k in range(start_i, len(q5)):
        r = q5.iloc[k]
        close = float(r.close)
        if close > prev_hi or close < prev_lo:
            return {
                'status': 'RANGE_BROKE_BEFORE_FILL',
                'cancel_ts': q5.index[k] + BAR5,
            }
        if float(r.low) <= entry_px <= float(r.high):
            return {
                'status': 'FILLED',
                'fill_k': k,
                'fill_ts': q5.index[k],
            }
    return {'status': 'NO_FILL'}


def resolve_after_fill(q5: pd.DataFrame, fill_k: int, side: str, entry_px: float,
                       stop_px: float, target_px: float):
    # Fill-bar ordering is unknowable. Charge stop if touched; do not award target-only.
    r0 = q5.iloc[fill_k]
    stop_hit = float(r0.low) <= stop_px if side == 'LONG' else float(r0.high) >= stop_px
    if stop_hit:
        ret = (stop_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return q5.index[fill_k], float(stop_px), float(ret), 'SL_FILL_5M_CONSERVATIVE'

    for k in range(fill_k + 1, len(q5)):
        r = q5.iloc[k]
        if side == 'LONG':
            tp = float(r.high) >= target_px
            sl = float(r.low) <= stop_px
        else:
            tp = float(r.low) <= target_px
            sl = float(r.high) >= stop_px

        if tp and sl:
            exit_px = stop_px
            reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp:
            exit_px = target_px
            reason = 'TP_RANGE_EDGE'
        elif sl:
            exit_px = stop_px
            reason = 'SL_RANGE_EDGE'
        else:
            continue

        ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return q5.index[k], float(exit_px), float(ret), reason
    return None


def simulate_candidate(x5: pd.DataFrame, q5: pd.DataFrame, signal: dict, depth: str,
                       prev_hi: float, prev_lo: float, session_end: pd.Timestamp):
    side = signal['side']
    frac = ENTRY_FRAC[side][depth]
    entry_px = prev_lo + frac * (prev_hi - prev_lo)
    stop_px = prev_lo if side == 'LONG' else prev_hi
    target_px = prev_hi if side == 'LONG' else prev_lo
    risk = abs(entry_px - stop_px)
    reward = abs(target_px - entry_px)
    nominal_rr = reward / risk

    base = {
        **signal,
        'entry_depth': depth,
        'entry_fraction_from_low': frac,
        'planned_entry_px': float(entry_px),
        'stop_px': float(stop_px),
        'target_px': float(target_px),
        'nominal_rr': float(nominal_rr),
    }

    fill = find_fill(q5, pd.Timestamp(signal['signal_ts']), prev_hi, prev_lo, entry_px)
    if fill['status'] != 'FILLED':
        return {
            **base,
            'filled': False,
            'entry_ts': pd.NaT,
            'entry_px': np.nan,
            'exit_ts': pd.NaT,
            'exit_px': np.nan,
            'exit_reason': fill['status'],
            'gross_return': np.nan,
            'net_pnl_usd': np.nan,
            'hold_minutes': np.nan,
        }

    fill_k = int(fill['fill_k'])
    fill_ts = pd.Timestamp(fill['fill_ts'])
    solved = resolve_after_fill(q5, fill_k, side, entry_px, stop_px, target_px)

    if solved is None:
        pos = int(x5.index.searchsorted(session_end, side='left'))
        if pos >= len(x5):
            return {
                **base,
                'filled': True,
                'entry_ts': fill_ts,
                'entry_px': float(entry_px),
                'exit_ts': pd.NaT,
                'exit_px': np.nan,
                'exit_reason': 'CENSORED',
                'gross_return': np.nan,
                'net_pnl_usd': np.nan,
                'hold_minutes': np.nan,
            }
        exit_ts = x5.index[pos]
        exit_px = float(x5.iloc[pos].open)
        ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        reason = 'TIME_EXIT_SESSION_END'
    else:
        exit_ts, exit_px, ret, reason = solved

    return {
        **base,
        'filled': True,
        'entry_ts': fill_ts,
        'entry_px': float(entry_px),
        'exit_ts': exit_ts,
        'exit_px': float(exit_px),
        'exit_reason': reason,
        'gross_return': float(ret),
        'net_pnl_usd': float(ret * NOTIONAL - FEE_USD),
        'hold_minutes': float((exit_ts - fill_ts) / pd.Timedelta(minutes=1)),
    }


def synthetic_tests():
    def frame(rows):
        idx = pd.date_range('2026-01-01 08:00', periods=len(rows), freq='5min', tz='UTC')
        return pd.DataFrame(rows, index=idx)

    H, L = 100.0, 90.0

    # Consecutive high touches are one visit; leave then return makes visit #2.
    q = frame([
        {'open': 95, 'high': 100, 'low': 94, 'close': 99},
        {'open': 99, 'high': 101, 'low': 98, 'close': 99.5},
        {'open': 99, 'high': 99.8, 'low': 97, 'close': 98},
        {'open': 98, 'high': 100.2, 'low': 97, 'close': 99},
        {'open': 99, 'high': 102, 'low': 98, 'close': 101},
    ])
    s = scan_session(q, H, L)
    hv = [v for v in s['visits'] if v['level'] == 'HIGH']
    assert len(hv) == 2 and [v['visit_no'] for v in hv] == [1, 2]
    assert s['breakout_side'] == 'HIGH'
    # Breakout bar itself must not create visit #3.
    assert s['high_visits'] == 2

    # Both-level bar must be rejected as chronologically ambiguous.
    q2 = frame([
        {'open': 95, 'high': 100, 'low': 90, 'close': 95},
    ])
    s2 = scan_session(q2, H, L)
    assert s2['status'] == 'AMBIGUOUS_BOTH_LEVELS'

    # A strict breakout on the first bar creates zero visits.
    q3 = frame([
        {'open': 99, 'high': 102, 'low': 98, 'close': 101},
    ])
    s3 = scan_session(q3, H, L)
    assert s3['breakout_side'] == 'HIGH' and s3['high_visits'] == 0

    # Next-bar eligibility: a price touch inside the signal bar cannot be used as a fill.
    q4 = frame([
        {'open': 99, 'high': 100, 'low': 94, 'close': 99},
        {'open': 99, 'high': 99, 'low': 96, 'close': 97},
        {'open': 97, 'high': 98, 'low': 94, 'close': 96},
    ])
    signal_ts = q4.index[0] + BAR5
    f = find_fill(q4, signal_ts, H, L, 95.0)
    assert f['status'] == 'FILLED' and f['fill_ts'] == q4.index[2]


def pf(vals) -> float:
    s = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def structural_summary(signals: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for transition in TRANSITIONS:
        for part in PARTS:
            for side in ('LONG', 'SHORT'):
                for k in KS:
                    base = signals[
                        (signals.transition == transition)
                        & (signals.partition == part)
                        & (signals.side == side)
                        & (signals.k == k)
                    ]
                    for purity in ('ALL', 'OPP0'):
                        g = base if purity == 'ALL' else base[base.opp_visits_at_signal == 0]
                        n = int(len(g))
                        rows.append({
                            'transition': transition,
                            'partition': part,
                            'side': side,
                            'k': k,
                            'purity': purity,
                            'n': n,
                            'target_break_n': int((g.structural_outcome == 'TARGET_BREAK').sum()) if n else 0,
                            'opposite_break_n': int((g.structural_outcome == 'OPPOSITE_BREAK').sum()) if n else 0,
                            'no_break_n': int((g.structural_outcome == 'NO_BREAK').sum()) if n else 0,
                            'target_break_prob': float((g.structural_outcome == 'TARGET_BREAK').mean()) if n else np.nan,
                            'opposite_break_prob': float((g.structural_outcome == 'OPPOSITE_BREAK').mean()) if n else np.nan,
                            'no_break_prob': float((g.structural_outcome == 'NO_BREAK').mean()) if n else np.nan,
                        })
    return pd.DataFrame(rows)


def entry_metrics(g: pd.DataFrame) -> dict:
    setups = int(len(g))
    f = g[g.filled.astype(bool)].copy() if setups else g
    r = f[pd.to_numeric(f.net_pnl_usd, errors='coerce').notna()].copy() if len(f) else f
    if len(r) == 0:
        return {
            'setups': setups,
            'fills': 0,
            'fill_rate': 0.0 if setups else np.nan,
            'wins': 0,
            'losses': 0,
            'wr': np.nan,
            'tp_rate': np.nan,
            'net_pf': np.nan,
            'net_exp': np.nan,
            'total_net': np.nan,
            'time_exit_rate': np.nan,
            'median_nominal_rr': float(g.nominal_rr.median()) if setups else np.nan,
        }
    net = pd.to_numeric(r.net_pnl_usd, errors='coerce')
    wins = int((net > 0).sum())
    return {
        'setups': setups,
        'fills': int(len(r)),
        'fill_rate': float(len(r) / setups) if setups else np.nan,
        'wins': wins,
        'losses': int(len(r) - wins),
        'wr': float(wins / len(r)),
        'tp_rate': float((r.exit_reason == 'TP_RANGE_EDGE').mean()),
        'net_pf': float(pf(net)),
        'net_exp': float(net.mean()),
        'total_net': float(net.sum()),
        'time_exit_rate': float((r.exit_reason == 'TIME_EXIT_SESSION_END').mean()),
        'median_nominal_rr': float(r.nominal_rr.median()),
    }


def entry_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for transition in TRANSITIONS:
        for part in PARTS:
            for side in ('LONG', 'SHORT'):
                for k in KS:
                    base0 = trades[
                        (trades.transition == transition)
                        & (trades.partition == part)
                        & (trades.side == side)
                        & (trades.k == k)
                    ]
                    for purity in ('ALL', 'OPP0'):
                        base = base0 if purity == 'ALL' else base0[base0.opp_visits_at_signal == 0]
                        for depth in DEPTHS:
                            g = base[base.entry_depth == depth]
                            rows.append({
                                'transition': transition,
                                'partition': part,
                                'side': side,
                                'k': k,
                                'purity': purity,
                                'entry_depth': depth,
                                **entry_metrics(g),
                            })
    s = pd.DataFrame(rows)

    screen = {}
    keys = ['transition', 'side', 'k', 'purity', 'entry_depth']
    for vals, g in s[s.partition.isin(MAJOR_PARTS)].groupby(keys, dropna=False):
        screen[vals] = bool(
            len(g) == 3
            and (g.fills >= 50).all()
            and (g.net_exp > 0).all()
            and (g.net_pf >= 1.20).all()
        )
    s['screen_pass'] = [screen.get((r.transition, r.side, r.k, r.purity, r.entry_depth), False)
                        for r in s.itertuples(index=False)]
    return s


def audit_real(x5: pd.DataFrame, visits: pd.DataFrame, signals: pd.DataFrame, trades: pd.DataFrame):
    # Visit ordinals contiguous for every level lifecycle within one frozen session.
    if len(visits):
        for _, g in visits.groupby(['partition', 'transition', 'date_utc', 'level']):
            nums = sorted(g.visit_no.astype(int).tolist())
            assert nums == list(range(1, len(nums) + 1))
            assert pd.to_datetime(g.visit_ts, utc=True).notna().all()
            bt = pd.to_datetime(g.breakout_ts, utc=True, errors='coerce')
            vt = pd.to_datetime(g.visit_ts, utc=True)
            mask = bt.notna()
            if mask.any():
                assert (vt[mask] < bt[mask]).all()

    # Every signal is a persisted visit K1/K2/K3 and is before breakout when one exists.
    if len(signals):
        assert signals.k.astype(int).isin(KS).all()
        assert (signals.k.astype(int) == signals.visit_no.astype(int)).all()
        bt = pd.to_datetime(signals.breakout_ts, utc=True, errors='coerce')
        st = pd.to_datetime(signals.signal_ts, utc=True)
        mask = bt.notna()
        if mask.any():
            assert (st[mask] < bt[mask]).all()

    # Trade mapping, exact fractions, causal entry eligibility, and no pre-fill close break.
    f = trades[trades.filled.astype(bool)].copy()
    for r in trades.itertuples(index=False):
        frac = ENTRY_FRAC[r.side][r.entry_depth]
        expected = float(r.previous_session_low + frac * (r.previous_session_high - r.previous_session_low))
        assert abs(float(r.planned_entry_px) - expected) <= 1e-9 * max(1.0, abs(expected))
        if r.side == 'LONG':
            assert float(r.stop_px) == float(r.previous_session_low)
            assert float(r.target_px) == float(r.previous_session_high)
        else:
            assert float(r.stop_px) == float(r.previous_session_high)
            assert float(r.target_px) == float(r.previous_session_low)

    if len(f):
        assert (pd.to_datetime(f.entry_ts, utc=True) >= pd.to_datetime(f.signal_ts, utc=True)).all()
        assert np.allclose(f.entry_px.astype(float), f.planned_entry_px.astype(float), rtol=0, atol=1e-9)
        for r in f.itertuples(index=False):
            a = pd.Timestamp(r.signal_ts)
            b = pd.Timestamp(r.entry_ts) + BAR5
            q = fast_slice(x5, a, b)
            assert len(q) > 0
            assert not ((q.close.astype(float) > float(r.previous_session_high)) |
                        (q.close.astype(float) < float(r.previous_session_low))).any()


def pct(v, d=1):
    return '-' if pd.isna(v) else f'{100 * float(v):.{d}f}%'


def num(v, d=2):
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{d}f}'


def main():
    synthetic_tests()
    x5, coverage = b21.load5()

    visit_rows = []
    signal_rows = []
    trade_rows = []
    status_rows = []

    for part, (part_start, part_end) in PARTS.items():
        first_day = part_start.normalize()
        last_day = (part_end - pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first_day, last_day, freq='D', tz='UTC'):
            if day.weekday() >= 5:
                continue
            for transition, cfg in TRANSITIONS.items():
                prev_start = b26c.ts_for_day(day, cfg['prev_start'])
                prev_end = b26c.ts_for_day(day, cfg['prev_end'])
                next_start = b26c.ts_for_day(day, cfg['next_start'])
                next_end = b26c.ts_for_day(day, cfg['next_end'])

                # Scoring partition applies to active session; same-day completed previous session is required.
                if next_start < part_start or next_end > part_end:
                    continue
                prev = fast_slice(x5, prev_start, prev_end)
                q5 = fast_slice(x5, next_start, next_end)
                if len(prev) != int((prev_end - prev_start) / BAR5) or len(q5) != int((next_end - next_start) / BAR5):
                    status_rows.append({'partition': part, 'transition': transition, 'date_utc': str(day.date()), 'status': 'INCOMPLETE_DATA'})
                    continue

                prev_hi = float(prev.high.max())
                prev_lo = float(prev.low.min())
                assert prev_hi > prev_lo

                scan = scan_session(q5, prev_hi, prev_lo)
                status_rows.append({'partition': part, 'transition': transition, 'date_utc': str(day.date()), 'status': scan['status']})
                if scan['status'] != 'OK':
                    continue

                session_base = {
                    'partition': part,
                    'transition': transition,
                    'date_utc': str(day.date()),
                    'previous_session_start': prev_start,
                    'previous_session_end': prev_end,
                    'active_session_start': next_start,
                    'active_session_end': next_end,
                    'previous_session_high': prev_hi,
                    'previous_session_low': prev_lo,
                    'breakout_side': scan['breakout_side'],
                    'breakout_bar_start': scan['breakout_bar_start'],
                    'breakout_ts': scan['breakout_ts'],
                }

                for v in scan['visits']:
                    visit_rows.append({**session_base, **v})
                    if int(v['visit_no']) not in KS:
                        continue
                    side = 'LONG' if v['level'] == 'HIGH' else 'SHORT'
                    sig = {
                        **session_base,
                        'side': side,
                        'signal_level': v['level'],
                        'k': int(v['visit_no']),
                        'visit_no': int(v['visit_no']),
                        'signal_bar_start': v['visit_bar_start'],
                        'signal_ts': v['visit_ts'],
                        'same_visits_at_signal': int(v['same_visits_at_event']),
                        'opp_visits_at_signal': int(v['opp_visits_at_event']),
                        'structural_outcome': structural_outcome(v['level'], scan['breakout_side']),
                    }
                    signal_rows.append(sig)
                    for depth in DEPTHS:
                        trade_rows.append(simulate_candidate(x5, q5, sig, depth, prev_hi, prev_lo, next_end))

    visits = pd.DataFrame(visit_rows)
    signals = pd.DataFrame(signal_rows)
    trades = pd.DataFrame(trade_rows)
    status = pd.DataFrame(status_rows)

    audit_real(x5, visits, signals, trades)

    visits.to_csv(OUT_VISITS, index=False)
    signals.to_csv(OUT_SIGNALS, index=False)
    trades.to_csv(OUT_TRADES, index=False)
    status.groupby(['partition', 'transition', 'status'], dropna=False).size().reset_index(name='n').to_csv(OUT_STATUS, index=False)

    ss = structural_summary(signals)
    es = entry_summary(trades)
    ss.to_csv(OUT_STRUCT, index=False)
    es.to_csv(OUT_ENTRY, index=False)

    md = [
        '# B27Q — Causal Previous-Session Liquidity Pressure -> Retrace Entry Grid — Result',
        '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.',
        '',
        '**Audit status: PASS.** Synthetic chronology tests and real-data mapping assertions completed before persistence.',
        '',
        'Exact frozen previous-session High/Low only. Distinct visits are counted on raw 5m chronology; no B27C-P aggregated touch count is reused.',
        '',
        '## Structural pressure probability',
        '',
        '| Transition | Partition | Side | K | Purity | N | Target break | Opposite break | No break |',
        '|---|---|---|---:|---|---:|---:|---:|---:|',
    ]
    for r in ss.itertuples(index=False):
        if r.partition == 'august' or r.n == 0:
            continue
        md.append(
            f'| {r.transition} | {r.partition} | {r.side} | {int(r.k)} | {r.purity} | {int(r.n)} | '
            f'{pct(r.target_break_prob)} | {pct(r.opposite_break_prob)} | {pct(r.no_break_prob)} |'
        )

    # Provisional screen candidates: show each exact candidate once with worst major-partition metrics.
    passed = es[es.screen_pass].copy()
    md += ['', '## Provisional entry screen', '']
    if len(passed) == 0:
        md.append('**No entry candidate passed the predeclared three-partition screen.**')
    else:
        agg = (passed[passed.partition.isin(MAJOR_PARTS)]
               .groupby(['transition', 'side', 'k', 'purity', 'entry_depth'], as_index=False)
               .agg(min_fills=('fills', 'min'), min_pf=('net_pf', 'min'), min_exp=('net_exp', 'min'),
                    min_wr=('wr', 'min'), max_wr=('wr', 'max'), min_fill_rate=('fill_rate', 'min'),
                    rr=('median_nominal_rr', 'median')))
        md += [
            '| Transition | Side | K | Purity | Entry | Min N | Min fill | WR range | Min PF | Min exp | Nominal RR |',
            '|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|',
        ]
        for r in agg.sort_values(['min_pf', 'min_exp'], ascending=False).itertuples(index=False):
            md.append(
                f'| {r.transition} | {r.side} | {int(r.k)} | {r.purity} | {r.entry_depth} | {int(r.min_fills)} | '
                f'{pct(r.min_fill_rate)} | {pct(r.min_wr)}-{pct(r.max_wr)} | {num(r.min_pf)} | ${num(r.min_exp)} | {num(r.rr)}R |'
            )

    md += [
        '',
        'Full entry grid is persisted in `BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_EntrySummary.csv`.',
        'Every distinct visit is auditable in `BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Visits.csv`.',
        '',
        'A `SCREEN_PASS` is discovery evidence only because multiple K/depth combinations are examined. It is not independent validation and does not modify live BBC.',
        '',
        'Research only; live BBC unchanged.',
    ]
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
