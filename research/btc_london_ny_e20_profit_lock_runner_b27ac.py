#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
B27Z_TRADES = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_Trades.csv'
B27Z_SUMMARY = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_Summary.csv'
B27AA_TRADES = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Trades.csv'
B27AA_SUMMARY = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Summary.csv'

OUT_MD = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Trades.csv'
OUT_SUMMARY = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
RULES = ('BLIND_F85', 'EARLY_RECLAIM', 'SAME_BAR_REJECTION')
PRIMARY = 'EARLY_RECLAIM'
EPS = 1e-12


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def dtcol(df: pd.DataFrame, cols) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def load_cohorts() -> pd.DataFrame:
    z = pd.read_csv(B27Z_TRADES)
    z = z[(z.target_name == 'E20') & (z.stop_name == 'D50')].copy()
    z = dtcol(z, ['signal_ts', 'entry_ts', 'h2_bar_start', 'exit_ts'])
    z['rule'] = 'BLIND_F85'
    z['entry_start'] = z['entry_ts']
    z['F35'] = pd.to_numeric(z['invalidation_boundary_px'])
    z['E20'] = pd.to_numeric(z['target_px'])
    z['session_end'] = pd.to_datetime(z['date_utc'].astype(str), utc=True) + pd.Timedelta(hours=20)
    z['baseline_net_pnl_usd'] = pd.to_numeric(z['net_pnl_usd'])
    z['baseline_exit_reason'] = z['exit_reason'].astype(str)
    z['baseline_exit_px'] = pd.to_numeric(z['exit_px'])

    a = pd.read_csv(B27AA_TRADES)
    a = dtcol(a, ['signal_ts', 'entry_bar_start', 'session_end', 'exit_ts'])
    a = a[a.entry_executed.astype(str).str.lower() == 'true'].copy()
    a['rule'] = a['variant'].astype(str)
    a['entry_start'] = a['entry_bar_start']
    a['baseline_net_pnl_usd'] = pd.to_numeric(a['net_pnl_usd'])
    a['baseline_exit_reason'] = a['exit_reason'].astype(str)
    a['baseline_exit_px'] = pd.to_numeric(a['exit_px'])

    cols = [
        'rule', 'partition', 'date_utc', 'signal_ts', 'entry_start', 'entry_px',
        'H', 'L', 'range', 'F35', 'E20', 'session_end',
        'baseline_net_pnl_usd', 'baseline_exit_reason', 'baseline_exit_px'
    ]
    c = pd.concat([z[cols], a[cols]], ignore_index=True)
    c = dtcol(c, ['signal_ts', 'entry_start', 'session_end'])
    for k in ['entry_px', 'H', 'L', 'range', 'F35', 'E20', 'baseline_net_pnl_usd', 'baseline_exit_px']:
        c[k] = pd.to_numeric(c[k], errors='raise')

    assert set(c.rule.unique()) == set(RULES)
    assert set(c.partition.unique()).issubset(set(PARTS))
    assert c.entry_start.notna().all() and c.session_end.notna().all()
    assert not c.duplicated(['rule', 'partition', 'date_utc', 'signal_ts']).any()
    assert ((c.L < c.F35) & (c.F35 < c.entry_px) & (c.entry_px < c.E20)).all()
    return c.sort_values(['rule', 'partition', 'entry_start']).reset_index(drop=True)


def verify_baselines(c: pd.DataFrame) -> None:
    zs = pd.read_csv(B27Z_SUMMARY)
    aa = pd.read_csv(B27AA_SUMMARY)
    expected = {}
    for _, r in zs[(zs.target_name == 'E20') & (zs.stop_name == 'D50')].iterrows():
        expected[('BLIND_F85', r.partition)] = (
            int(r.trades), float(r.wr), float(r.pf), float(r.net_exp), float(r.total_net)
        )
    for _, r in aa.iterrows():
        expected[(str(r.variant), r.partition)] = (
            int(r.executed_trades), float(r.wr), float(r.pf), float(r.net_exp), float(r.total_net)
        )

    for (rule, part), g in c.groupby(['rule', 'partition']):
        vals = g.baseline_net_pnl_usd.astype(float)
        got = (len(vals), float((vals > 0).mean()), pf(vals), float(vals.mean()), float(vals.sum()))
        exp = expected[(rule, part)]
        assert got[0] == exp[0]
        for gv, ev in zip(got[1:], exp[1:]):
            if math.isinf(gv) and math.isinf(ev):
                continue
            assert abs(gv - ev) < 1e-8 * max(1.0, abs(ev)), (rule, part, got, exp)


def time_exit(x5: pd.DataFrame, session_end: pd.Timestamp):
    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5) or x5.index[pos] != session_end:
        return None
    return session_end, float(x5.iloc[pos].open), 'TIME_EXIT_SESSION_END'


def simulate_hybrid(x5: pd.DataFrame, r: pd.Series) -> dict:
    entry_start = pd.Timestamp(r.entry_start)
    session_end = pd.Timestamp(r.session_end)
    entry_px = float(r.entry_px)
    H = float(r.H)
    L = float(r.L)
    rng = float(r['range'])
    f35 = float(r.F35)
    e20 = float(r.E20)

    q = fast_slice(x5, entry_start, session_end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing raw 5m entry bar')

    lows = q['low'].astype(float).to_numpy()
    e20_reached = False
    e20_touch_bar_start = pd.NaT
    e20_floor_effective_start = pd.NaT
    floor_active = False
    active_floor = np.nan
    floor_updates = 0
    latest_confirmed_pivot = np.nan
    max_floor = np.nan
    activation_bar_close = np.nan
    activation_close_below_e20 = False

    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    exit_reason = None
    exit_floor_kind = None

    for i, (ts, bar) in enumerate(q.iterrows()):
        op = float(bar.open)
        hi = float(bar.high)
        lo = float(bar.low)
        cl = float(bar.close)

        # A floor created by a prior completed bar is a resting stop for this bar.
        if floor_active:
            assert np.isfinite(active_floor) and active_floor >= e20 - EPS
            if op <= active_floor:
                exit_bar_start = ts
                exit_ts = ts
                exit_px = op
                exit_floor_kind = 'E20' if active_floor <= e20 + EPS else 'STRUCTURAL'
                exit_reason = 'LOCK_FLOOR_OPEN_EXIT'
                break
            if lo <= active_floor:
                exit_bar_start = ts
                exit_ts = ts
                exit_px = active_floor
                exit_floor_kind = 'E20' if active_floor <= e20 + EPS else 'STRUCTURAL'
                exit_reason = 'LOCK_FLOOR_STOP'
                break

        # A strict 3-bar pivot centered on i-1 becomes knowable only at this bar close.
        pivot_now = np.nan
        if i >= 2 and lows[i - 1] < lows[i - 2] and lows[i - 1] < lows[i]:
            pivot_now = float(lows[i - 1])
            latest_confirmed_pivot = pivot_now

        if not e20_reached:
            touched_now = hi >= e20

            # Pre-E20 risk remains the frozen F35 completed-close invalidation.
            if cl < f35:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = cl
                exit_reason = 'PRE_E20_CLOSE_INVALIDATION_F35'
                break

            if touched_now:
                e20_reached = True
                e20_touch_bar_start = ts
                e20_floor_effective_start = ts + BAR5
                activation_bar_close = cl
                activation_close_below_e20 = bool(cl < e20)
                active_floor = e20
                # A pivot confirmed at the same completed close is causal for the next bar.
                if np.isfinite(pivot_now) and pivot_now > active_floor:
                    active_floor = pivot_now
                    floor_updates += 1
                max_floor = active_floor
                floor_active = True
                continue
        else:
            # Surviving this bar means the old floor was not hit. A newly confirmed pivot
            # can only raise the resting floor for the NEXT bar.
            if np.isfinite(pivot_now) and pivot_now > active_floor:
                old = active_floor
                active_floor = pivot_now
                floor_updates += 1
                assert active_floor >= old
                max_floor = max(float(max_floor), active_floor)

    if exit_reason is None:
        te = time_exit(x5, session_end)
        if te is None:
            exit_reason = 'CENSORED'
        else:
            exit_ts, exit_px, exit_reason = te
            exit_bar_start = exit_ts

    if exit_reason == 'CENSORED':
        gross = np.nan
        net = np.nan
        hold = np.nan
    else:
        gross = float(exit_px / entry_px - 1.0)
        net = gross * NOTIONAL - FEE
        hold = float((pd.Timestamp(exit_ts) - entry_start) / pd.Timedelta(minutes=1))

    session_peak = np.nan
    peak_ext = np.nan
    exit_ext = np.nan
    giveback_r = np.nan
    capture_ratio = np.nan
    exit_at_or_above_e20 = False
    if e20_reached:
        aq = fast_slice(x5, pd.Timestamp(e20_touch_bar_start), session_end)
        if not aq.empty:
            session_peak = float(aq.high.max())
            peak_ext = float((session_peak - H) / rng)
        if exit_reason != 'CENSORED':
            exit_ext = float((float(exit_px) - H) / rng)
            if np.isfinite(peak_ext):
                giveback_r = float(peak_ext - exit_ext)
                denom = max(0.0, session_peak - H)
                if denom > 0:
                    capture_ratio = float(max(0.0, float(exit_px) - H) / denom)
            exit_at_or_above_e20 = bool(float(exit_px) >= e20 - EPS)

    baseline_win = bool(float(r.baseline_net_pnl_usd) > 0)
    hybrid_win = bool(np.isfinite(net) and net > 0)

    return {
        'rule': r.rule,
        'partition': r.partition,
        'date_utc': r.date_utc,
        'signal_ts': pd.Timestamp(r.signal_ts),
        'entry_start': entry_start,
        'entry_px': entry_px,
        'H': H,
        'L': L,
        'range': rng,
        'F35': f35,
        'E20': e20,
        'session_end': session_end,
        'baseline_net_pnl_usd': float(r.baseline_net_pnl_usd),
        'baseline_exit_reason': r.baseline_exit_reason,
        'baseline_exit_px': float(r.baseline_exit_px),
        'e20_reached': bool(e20_reached),
        'e20_touch_bar_start': e20_touch_bar_start,
        'e20_floor_effective_start': e20_floor_effective_start,
        'activation_bar_close': activation_bar_close,
        'activation_close_below_e20': bool(activation_close_below_e20),
        'latest_confirmed_pivot': latest_confirmed_pivot,
        'floor_updates': int(floor_updates),
        'final_active_floor': active_floor,
        'max_active_floor': max_floor,
        'exit_floor_kind': exit_floor_kind,
        'exit_bar_start': exit_bar_start,
        'exit_ts': exit_ts,
        'exit_px': exit_px,
        'hybrid_exit_reason': exit_reason,
        'gross_return': gross,
        'hybrid_net_pnl_usd': net,
        'hold_minutes': hold,
        'session_peak_high_after_e20': session_peak,
        'session_peak_extension_r': peak_ext,
        'realized_exit_extension_r': exit_ext,
        'giveback_from_peak_r': giveback_r,
        'capture_ratio': capture_ratio,
        'exit_at_or_above_e20': bool(exit_at_or_above_e20),
        'baseline_win': baseline_win,
        'hybrid_win': hybrid_win,
        'baseline_win_preserved': bool((not baseline_win) or hybrid_win),
    }


def synthetic_tests() -> None:
    idx = pd.date_range('2026-01-02 13:30', periods=12, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    base = {
        'rule': 'EARLY_RECLAIM', 'partition': 'x', 'date_utc': '2026-01-02',
        'signal_ts': idx[0] - BAR5, 'entry_start': idx[0], 'entry_px': 98.5,
        'H': H, 'L': L, 'range': 10.0, 'F35': 93.5, 'E20': 102.0,
        'session_end': idx[10], 'baseline_net_pnl_usd': 1.0,
        'baseline_exit_reason': 'TP_E20', 'baseline_exit_px': 102.0,
    }

    # 1) Pre-E20 F35 close invalidation remains unchanged.
    x1 = pd.DataFrame([
        {'open':98.5,'high':99.0,'low':98.0,'close':98.7},
        {'open':98.7,'high':99.1,'low':93.0,'close':93.2},
    ] + [{'open':93.2,'high':94.0,'low':93.0,'close':93.5}] * 10, index=idx)
    z1 = simulate_hybrid(x1, pd.Series(base))
    assert z1['hybrid_exit_reason'] == 'PRE_E20_CLOSE_INVALIDATION_F35'
    assert not z1['e20_reached']

    # 2) E20 touch arms floor only for next bar; next bar retrace exits exactly at E20.
    bars2 = [
        {'open':98.5,'high':99.5,'low':98.2,'close':99.0},
        {'open':99.0,'high':100.5,'low':98.8,'close':100.0},
        {'open':100.0,'high':102.4,'low':99.8,'close':102.2},  # E20 touch
        {'open':102.2,'high':103.0,'low':101.8,'close':102.0}, # floor hit
    ] + [{'open':102.0,'high':102.2,'low':101.8,'close':102.0}] * 8
    x2 = pd.DataFrame(bars2, index=idx)
    z2 = simulate_hybrid(x2, pd.Series(base))
    assert z2['e20_reached']
    assert z2['e20_floor_effective_start'] == idx[3]
    assert z2['hybrid_exit_reason'] == 'LOCK_FLOOR_STOP'
    assert z2['exit_floor_kind'] == 'E20'
    assert abs(z2['exit_px'] - 102.0) < 1e-12

    # 3) E20 touch, survive, confirmed higher pivot ratchets floor, then structural floor is hit.
    bars3 = [
        {'open':98.5,'high':99.5,'low':98.2,'close':99.0},
        {'open':99.0,'high':100.5,'low':98.8,'close':100.0},
        {'open':100.0,'high':102.4,'low':99.8,'close':102.2},  # touch E20
        {'open':102.2,'high':104.0,'low':102.1,'close':103.5},
        {'open':103.5,'high':105.0,'low':103.0,'close':104.5},
        {'open':104.5,'high':105.5,'low':102.8,'close':103.8},
        {'open':103.8,'high':106.0,'low':103.4,'close':105.5}, # confirms pivot 102.8
        {'open':105.5,'high':106.0,'low':102.7,'close':103.0}, # hits 102.8 floor
    ] + [{'open':103.0,'high':103.2,'low':102.9,'close':103.0}] * 4
    x3 = pd.DataFrame(bars3, index=idx)
    z3 = simulate_hybrid(x3, pd.Series(base))
    assert z3['hybrid_exit_reason'] == 'LOCK_FLOOR_STOP'
    assert z3['exit_floor_kind'] == 'STRUCTURAL'
    assert abs(z3['exit_px'] - 102.8) < 1e-12
    assert z3['floor_updates'] >= 1

    # 4) Touch bar may close back below E20; floor is not retroactive, next open below floor exits at open.
    bars4 = [
        {'open':98.5,'high':99.5,'low':98.2,'close':99.0},
        {'open':99.0,'high':100.5,'low':98.8,'close':100.0},
        {'open':100.0,'high':102.4,'low':99.8,'close':100.5},  # touched but gave back in same bar
        {'open':100.5,'high':101.0,'low':100.0,'close':100.4},
    ] + [{'open':100.4,'high':100.8,'low':100.0,'close':100.4}] * 8
    x4 = pd.DataFrame(bars4, index=idx)
    z4 = simulate_hybrid(x4, pd.Series(base))
    assert z4['e20_reached'] and z4['activation_close_below_e20']
    assert z4['hybrid_exit_reason'] == 'LOCK_FLOOR_OPEN_EXIT'
    assert abs(z4['exit_px'] - 100.5) < 1e-12

    # 5) No E20, no invalidation -> frozen session-end exit.
    x5 = pd.DataFrame([
        {'open':98.5,'high':100.0,'low':97.8,'close':99.0}
    ] * 12, index=idx)
    x5.loc[idx[10], 'open'] = 99.3
    z5 = simulate_hybrid(x5, pd.Series(base))
    assert z5['hybrid_exit_reason'] == 'TIME_EXIT_SESSION_END'
    assert not z5['e20_reached']
    assert abs(z5['exit_px'] - 99.3) < 1e-12


def summarize(g: pd.DataFrame) -> dict:
    b = g.baseline_net_pnl_usd.astype(float)
    h = pd.to_numeric(g.hybrid_net_pnl_usd, errors='coerce').dropna()
    hg = g.loc[h.index]
    locked = hg[hg.e20_reached.astype(bool)]
    baseline_winners = hg[hg.baseline_net_pnl_usd > 0]
    return {
        'trades': int(len(h)),
        'baseline_wr': float((b.loc[h.index] > 0).mean()) if len(h) else np.nan,
        'baseline_pf': pf(b.loc[h.index]),
        'baseline_exp': float(b.loc[h.index].mean()) if len(h) else np.nan,
        'baseline_total': float(b.loc[h.index].sum()) if len(h) else np.nan,
        'hybrid_wr': float((h > 0).mean()) if len(h) else np.nan,
        'hybrid_pf': pf(h),
        'hybrid_exp': float(h.mean()) if len(h) else np.nan,
        'hybrid_total': float(h.sum()) if len(h) else np.nan,
        'delta_exp': float(h.mean() - b.loc[h.index].mean()) if len(h) else np.nan,
        'delta_total': float(h.sum() - b.loc[h.index].sum()) if len(h) else np.nan,
        'e20_reach_rate': float(hg.e20_reached.mean()) if len(hg) else np.nan,
        'pre_e20_stop_count': int((hg.hybrid_exit_reason == 'PRE_E20_CLOSE_INVALIDATION_F35').sum()),
        'floor_stop_count': int((hg.hybrid_exit_reason == 'LOCK_FLOOR_STOP').sum()),
        'floor_open_exit_count': int((hg.hybrid_exit_reason == 'LOCK_FLOOR_OPEN_EXIT').sum()),
        'time_exit_count': int((hg.hybrid_exit_reason == 'TIME_EXIT_SESSION_END').sum()),
        'structural_floor_exit_count': int((hg.exit_floor_kind == 'STRUCTURAL').sum()),
        'e20_floor_exit_count': int((hg.exit_floor_kind == 'E20').sum()),
        'activation_close_below_e20_rate': float(locked.activation_close_below_e20.mean()) if len(locked) else np.nan,
        'exit_at_or_above_e20_rate_given_reach': float(locked.exit_at_or_above_e20.mean()) if len(locked) else np.nan,
        'median_peak_ext_r_given_reach': float(locked.session_peak_extension_r.median()) if len(locked) else np.nan,
        'median_exit_ext_r_given_reach': float(locked.realized_exit_extension_r.median()) if len(locked) else np.nan,
        'median_capture_ratio_given_reach': float(locked.capture_ratio.median()) if len(locked) else np.nan,
        'median_giveback_r_given_reach': float(locked.giveback_from_peak_r.median()) if len(locked) else np.nan,
        'median_floor_updates_given_reach': float(locked.floor_updates.median()) if len(locked) else np.nan,
        'median_hold_minutes': float(hg.hold_minutes.median()) if len(hg) else np.nan,
        'baseline_winner_preservation_rate': float(baseline_winners.hybrid_win.mean()) if len(baseline_winners) else np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def num(x):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.2f}'


def money(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main() -> None:
    synthetic_tests()
    x5, coverage = b21.load5()
    c = load_cohorts()
    verify_baselines(c)

    rows = [simulate_hybrid(x5, r) for _, r in c.iterrows()]
    t = pd.DataFrame(rows)
    assert len(t) == len(c)
    assert not t.duplicated(['rule', 'partition', 'date_utc', 'signal_ts']).any()
    assert t.hybrid_net_pnl_usd.notna().all(), 'censored hybrid trade found'

    sums = []
    for (rule, part), g in t.groupby(['rule', 'partition'], sort=False):
        sums.append({'rule': rule, 'partition': part, **summarize(g)})
    major = t[t.partition.isin(MAJOR)].copy()
    for rule, g in major.groupby('rule', sort=False):
        sums.append({'rule': rule, 'partition': 'POOLED_MAJOR', **summarize(g)})
    s = pd.DataFrame(sums)

    ps = s[(s.rule == PRIMARY) & (s.partition.isin(MAJOR))].copy()
    pooled = s[(s.rule == PRIMARY) & (s.partition == 'POOLED_MAJOR')].iloc[0]
    primary_supported = bool(
        len(ps) == 3
        and (ps.hybrid_exp > ps.baseline_exp).all()
        and (ps.hybrid_pf >= 1.0).all()
        and float(pooled.hybrid_total) > float(pooled.baseline_total)
    )

    # Real-data assertions.
    for r in t.itertuples(index=False):
        assert float(r.F35) < float(r.entry_px) < float(r.E20)
        if bool(r.e20_reached):
            assert pd.notna(r.e20_touch_bar_start)
            assert pd.notna(r.e20_floor_effective_start)
            assert pd.Timestamp(r.e20_floor_effective_start) == pd.Timestamp(r.e20_touch_bar_start) + BAR5
            if np.isfinite(float(r.final_active_floor)):
                assert float(r.final_active_floor) >= float(r.E20) - EPS
        if r.hybrid_exit_reason == 'LOCK_FLOOR_STOP':
            assert r.exit_floor_kind in ('E20', 'STRUCTURAL')
            assert float(r.exit_px) >= float(r.E20) - EPS
        if r.hybrid_exit_reason == 'LOCK_FLOOR_OPEN_EXIT':
            # Gap/open safety can realize below the armed floor; this is intentionally not hidden.
            assert pd.notna(r.exit_bar_start)

    assert abs(float(coverage) - 1.0) < 1e-12

    t.to_csv(OUT_TRADES, index=False)
    s.to_csv(OUT_SUMMARY, index=False)
    OUT_STATUS.write_text('B27AC_PRIMARY_HYBRID_SUPPORTED\n' if primary_supported else 'B27AC_PRIMARY_HYBRID_NOT_SUPPORTED\n')

    lines = []
    lines.append('# B27AC — London -> New York E20 Profit-Lock Runner — Result')
    lines.append('')
    lines.append(f'5m rows: **{len(x5):,}**; coverage: **{100.0 * float(coverage):.4f}%**.')
    lines.append('')
    lines.append('**Audit status: PASS.** Frozen B27Z/B27AA entry identities and fixed-E20 baseline economics reproduce before the hybrid result is interpreted.')
    lines.append('')
    lines.append('## Fixed E20 vs E20-lock structural runner')
    lines.append('')
    lines.append('| Rule | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total | Delta total | E20 reach | Winner preserved |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for _, r in s.iterrows():
        lines.append(
            f"| {r.rule} | {r.partition} | {int(r.trades)} | {pct(r.baseline_wr)} | {num(r.baseline_pf)} | {money(r.baseline_exp)} | {money(r.baseline_total)} | "
            f"{pct(r.hybrid_wr)} | {num(r.hybrid_pf)} | {money(r.hybrid_exp)} | {money(r.hybrid_total)} | {money(r.delta_total)} | {pct(r.e20_reach_rate)} | {pct(r.baseline_winner_preservation_rate)} |"
        )

    lines.append('')
    lines.append('## Profit-lock diagnostics')
    lines.append('')
    lines.append('| Rule | Partition | Pre-E20 stops | E20-floor exits | Structural-floor exits | Open/gap exits | Time exits | Exit >= E20 / reached | Touch-bar close < E20 | Median peak ext | Median exit ext | Median capture | Median giveback | Median ratchets |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for _, r in s.iterrows():
        lines.append(
            f"| {r.rule} | {r.partition} | {int(r.pre_e20_stop_count)} | {int(r.e20_floor_exit_count)} | {int(r.structural_floor_exit_count)} | {int(r.floor_open_exit_count)} | {int(r.time_exit_count)} | "
            f"{pct(r.exit_at_or_above_e20_rate_given_reach)} | {pct(r.activation_close_below_e20_rate)} | {num(r.median_peak_ext_r_given_reach)}R | {num(r.median_exit_ext_r_given_reach)}R | "
            f"{pct(r.median_capture_ratio_given_reach)} | {num(r.median_giveback_r_given_reach)}R | {num(r.median_floor_updates_given_reach)} |"
        )

    lines.append('')
    lines.append('## Frozen primary gate')
    lines.append('')
    for _, r in ps.iterrows():
        passed = bool(r.hybrid_exp > r.baseline_exp and r.hybrid_pf >= 1.0)
        lines.append(
            f"- {r.partition}: fixed exp {money(r.baseline_exp)} -> hybrid exp {money(r.hybrid_exp)}; hybrid PF {num(r.hybrid_pf)} -> {'PASS' if passed else 'FAIL'}"
        )
    lines.append('')
    lines.append(f"**Overall: {'B27AC_PRIMARY_HYBRID_SUPPORTED' if primary_supported else 'B27AC_PRIMARY_HYBRID_NOT_SUPPORTED'}.**")
    lines.append('')
    lines.append('E20 is frozen. The E20 floor is effective only from the bar after first E20 reach; no retroactive intrabar stop is assumed.')
    lines.append('')
    lines.append('Research only; live BBC unchanged.')
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
