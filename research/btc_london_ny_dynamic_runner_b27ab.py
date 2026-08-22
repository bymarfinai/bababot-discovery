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

OUT_MD = ROOT / 'BTC_LONDON_NY_DYNAMIC_RUNNER_B27AB_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_DYNAMIC_RUNNER_B27AB_Trades.csv'
OUT_SUMMARY = ROOT / 'BTC_LONDON_NY_DYNAMIC_RUNNER_B27AB_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_DYNAMIC_RUNNER_B27AB_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
RULES = ('BLIND_F85', 'EARLY_RECLAIM', 'SAME_BAR_REJECTION')
PRIMARY = 'EARLY_RECLAIM'


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
    # Blind F85 baseline identities are frozen B27Z E20/D50 rows.
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

    # B27AA executed identities are already frozen and include exact next-open execution.
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
    # Persisted source summaries must reproduce from the exact rows used by B27AB.
    zs = pd.read_csv(B27Z_SUMMARY)
    aa = pd.read_csv(B27AA_SUMMARY)

    expected = {}
    for _, r in zs[(zs.target_name == 'E20') & (zs.stop_name == 'D50')].iterrows():
        expected[('BLIND_F85', r.partition)] = (int(r.trades), float(r.wr), float(r.pf), float(r.net_exp), float(r.total_net))
    for _, r in aa.iterrows():
        expected[(str(r.variant), r.partition)] = (int(r.executed_trades), float(r.wr), float(r.pf), float(r.net_exp), float(r.total_net))

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


def simulate_runner(x5: pd.DataFrame, r: pd.Series) -> dict:
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

    accepted = False
    acceptance_bar_start = pd.NaT
    acceptance_ts = pd.NaT
    acceptance_close = np.nan
    active_trail = f35
    last_confirmed_pivot = np.nan
    trail_updates = 0
    h2_seen = False
    ever_e20 = False
    max_high_entry_to_exit = -np.inf
    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    exit_reason = None

    lows = q['low'].astype(float).to_numpy()

    for i, (ts, bar) in enumerate(q.iterrows()):
        high = float(bar.high)
        close = float(bar.close)
        max_high_entry_to_exit = max(max_high_entry_to_exit, high)
        if high >= H:
            h2_seen = True
        if high >= e20:
            ever_e20 = True

        # A 3-bar pivot centered on i-1 becomes knowable only now, at close of bar i.
        if i >= 2 and lows[i - 1] < lows[i - 2] and lows[i - 1] < lows[i]:
            last_confirmed_pivot = float(lows[i - 1])
            if accepted and last_confirmed_pivot > active_trail:
                old = active_trail
                active_trail = last_confirmed_pivot
                trail_updates += 1
                assert active_trail >= old

        if not accepted:
            # Pre-breakout protection stays exactly F35; there is no fixed TP.
            if close < f35:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = close
                exit_reason = 'PREBREAK_CLOSE_INVALIDATION_F35'
                break

            if close > H:
                accepted = True
                acceptance_bar_start = ts
                acceptance_ts = ts + BAR5
                acceptance_close = close
                if pd.notna(last_confirmed_pivot):
                    active_trail = max(f35, float(last_confirmed_pivot))
                else:
                    active_trail = f35
                # The trail is only known at this completed close, so it cannot stop the activation bar retroactively.
                continue

        else:
            if close < active_trail:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = close
                exit_reason = 'RUNNER_STRUCTURE_CLOSE_BREAK'
                break

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

    # Ex-post peak diagnostics are measured through frozen session end and never influence execution.
    peak_ext = np.nan
    exit_ext = np.nan
    giveback_r = np.nan
    capture_ratio = np.nan
    session_peak_high = np.nan
    exit_above_e20 = False
    if accepted:
        aq = fast_slice(x5, pd.Timestamp(acceptance_bar_start), session_end)
        if not aq.empty:
            session_peak_high = float(aq.high.max())
            peak_ext = float((session_peak_high - H) / rng)
            if exit_reason != 'CENSORED':
                exit_ext = float((float(exit_px) - H) / rng)
                giveback_r = float(peak_ext - exit_ext)
                denom = max(0.0, session_peak_high - H)
                if denom > 0:
                    capture_ratio = float(max(0.0, float(exit_px) - H) / denom)
                exit_above_e20 = bool(float(exit_px) >= e20)

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
        'h2_seen': bool(h2_seen),
        'breakout_accepted': bool(accepted),
        'acceptance_bar_start': acceptance_bar_start,
        'acceptance_ts': acceptance_ts,
        'acceptance_close': acceptance_close,
        'last_confirmed_pivot': last_confirmed_pivot,
        'trail_at_exit': float(active_trail),
        'trail_updates': int(trail_updates),
        'ever_e20': bool(ever_e20),
        'exit_bar_start': exit_bar_start,
        'exit_ts': exit_ts,
        'exit_px': exit_px,
        'runner_exit_reason': exit_reason,
        'gross_return': gross,
        'runner_net_pnl_usd': net,
        'hold_minutes': hold,
        'session_peak_high_after_accept': session_peak_high,
        'session_peak_extension_r': peak_ext,
        'realized_exit_extension_r': exit_ext,
        'giveback_from_peak_r': giveback_r,
        'capture_ratio': capture_ratio,
        'exit_above_e20': bool(exit_above_e20),
    }


def synthetic_tests() -> None:
    idx = pd.date_range('2026-01-02 13:30', periods=12, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    base = {
        'rule': 'EARLY_RECLAIM', 'partition': 'x', 'date_utc': '2026-01-02',
        'signal_ts': idx[0] - BAR5, 'entry_start': idx[0], 'entry_px': 98.5,
        'H': H, 'L': L, 'range': 10.0, 'F35': 93.5, 'E20': 102.0,
        'session_end': idx[10], 'baseline_net_pnl_usd': 0.0,
        'baseline_exit_reason': 'x', 'baseline_exit_px': 98.5,
    }

    # Pre-breakout F35 close invalidation must exit before any runner activation.
    x1 = pd.DataFrame([
        {'open':98.5,'high':99.0,'low':98.0,'close':98.7},
        {'open':98.7,'high':99.1,'low':93.0,'close':93.2},
    ] + [{'open':93.2,'high':94.0,'low':93.0,'close':93.5}] * 10, index=idx)
    z1 = simulate_runner(x1, pd.Series(base))
    assert z1['runner_exit_reason'] == 'PREBREAK_CLOSE_INVALIDATION_F35'
    assert not z1['breakout_accepted']

    # Acceptance -> confirmed pivot -> structural close break.
    bars = [
        {'open':98.5,'high':99.0,'low':98.2,'close':98.8},
        {'open':98.8,'high':100.5,'low':98.6,'close':100.2},  # acceptance
        {'open':100.2,'high':101.2,'low':100.0,'close':101.0},
        {'open':101.0,'high':102.0,'low':100.8,'close':101.8},
        {'open':101.8,'high':102.2,'low':100.2,'close':101.0},
        {'open':101.0,'high':102.5,'low':100.7,'close':102.0},  # confirms pivot 100.2
        {'open':102.0,'high':102.1,'low':99.8,'close':100.0},   # closes below 100.2
        {'open':100.0,'high':100.5,'low':99.5,'close':100.1},
        {'open':100.1,'high':100.5,'low':100.0,'close':100.2},
        {'open':100.2,'high':100.5,'low':100.0,'close':100.2},
        {'open':100.2,'high':100.2,'low':100.2,'close':100.2},
        {'open':100.2,'high':100.2,'low':100.2,'close':100.2},
    ]
    x2 = pd.DataFrame(bars, index=idx)
    z2 = simulate_runner(x2, pd.Series(base))
    assert z2['breakout_accepted']
    assert z2['runner_exit_reason'] == 'RUNNER_STRUCTURE_CLOSE_BREAK'
    assert abs(z2['trail_at_exit'] - 100.2) < 1e-12
    assert z2['ever_e20']

    # No acceptance and no invalidation -> session-end exit.
    x3 = pd.DataFrame([
        {'open':98.5,'high':99.8,'low':97.8,'close':99.0}
    ] * 12, index=idx)
    x3.loc[idx[10], 'open'] = 99.3
    z3 = simulate_runner(x3, pd.Series(base))
    assert z3['runner_exit_reason'] == 'TIME_EXIT_SESSION_END'
    assert not z3['breakout_accepted']
    assert abs(z3['exit_px'] - 99.3) < 1e-12


def summarize(g: pd.DataFrame) -> dict:
    b = g.baseline_net_pnl_usd.astype(float)
    r = pd.to_numeric(g.runner_net_pnl_usd, errors='coerce').dropna()
    rg = g.loc[r.index]
    accepted = rg.breakout_accepted.astype(bool)
    accg = rg[accepted]
    return {
        'trades': int(len(r)),
        'baseline_wr': float((b.loc[r.index] > 0).mean()) if len(r) else np.nan,
        'baseline_pf': pf(b.loc[r.index]),
        'baseline_exp': float(b.loc[r.index].mean()) if len(r) else np.nan,
        'baseline_total': float(b.loc[r.index].sum()) if len(r) else np.nan,
        'runner_wr': float((r > 0).mean()) if len(r) else np.nan,
        'runner_pf': pf(r),
        'runner_exp': float(r.mean()) if len(r) else np.nan,
        'runner_total': float(r.sum()) if len(r) else np.nan,
        'delta_exp': float(r.mean() - b.loc[r.index].mean()) if len(r) else np.nan,
        'delta_total': float(r.sum() - b.loc[r.index].sum()) if len(r) else np.nan,
        'acceptance_rate': float(accepted.mean()) if len(r) else np.nan,
        'prebreak_stop_count': int((rg.runner_exit_reason == 'PREBREAK_CLOSE_INVALIDATION_F35').sum()),
        'structure_exit_count': int((rg.runner_exit_reason == 'RUNNER_STRUCTURE_CLOSE_BREAK').sum()),
        'time_exit_count': int((rg.runner_exit_reason == 'TIME_EXIT_SESSION_END').sum()),
        'e20_reach_rate': float(rg.ever_e20.mean()) if len(rg) else np.nan,
        'exit_above_e20_rate_given_accept': float(accg.exit_above_e20.mean()) if len(accg) else np.nan,
        'median_peak_ext_r_given_accept': float(accg.session_peak_extension_r.median()) if len(accg) else np.nan,
        'median_exit_ext_r_given_accept': float(accg.realized_exit_extension_r.median()) if len(accg) else np.nan,
        'median_capture_ratio_given_accept': float(accg.capture_ratio.median()) if len(accg) else np.nan,
        'median_giveback_r_given_accept': float(accg.giveback_from_peak_r.median()) if len(accg) else np.nan,
        'median_hold_minutes': float(rg.hold_minutes.median()) if len(rg) else np.nan,
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

    rows = [simulate_runner(x5, r) for _, r in c.iterrows()]
    t = pd.DataFrame(rows)
    assert len(t) == len(c)
    assert not t.duplicated(['rule', 'partition', 'date_utc', 'signal_ts']).any()
    assert t.runner_net_pnl_usd.notna().all(), 'censored runner trade found'

    sums = []
    for (rule, part), g in t.groupby(['rule', 'partition'], sort=False):
        sums.append({'rule': rule, 'partition': part, **summarize(g)})

    major = t[t.partition.isin(MAJOR)].copy()
    for rule, g in major.groupby('rule', sort=False):
        sums.append({'rule': rule, 'partition': 'POOLED_MAJOR', **summarize(g)})

    s = pd.DataFrame(sums)

    # Frozen primary gate.
    ps = s[(s.rule == PRIMARY) & (s.partition.isin(MAJOR))].copy()
    pooled = s[(s.rule == PRIMARY) & (s.partition == 'POOLED_MAJOR')].iloc[0]
    primary_supported = bool(
        len(ps) == 3
        and (ps.runner_exp > ps.baseline_exp).all()
        and (ps.runner_pf >= 1.0).all()
        and float(pooled.runner_total) > float(pooled.baseline_total)
    )

    # Real-data structural assertions.
    for r in t.itertuples(index=False):
        assert float(r.F35) < float(r.entry_px)
        if bool(r.breakout_accepted):
            assert pd.notna(r.acceptance_ts)
            assert float(r.acceptance_close) > float(r.H)
            assert float(r.trail_at_exit) >= float(r.F35)
        if r.runner_exit_reason == 'RUNNER_STRUCTURE_CLOSE_BREAK':
            bs = pd.Timestamp(r.exit_bar_start)
            raw = x5.loc[bs]
            assert float(raw.close) < float(r.trail_at_exit)

    t.to_csv(OUT_TRADES, index=False)
    s.to_csv(OUT_SUMMARY, index=False)
    OUT_STATUS.write_text('B27AB_PRIMARY_RUNNER_SUPPORTED\n' if primary_supported else 'B27AB_PRIMARY_RUNNER_NOT_SUPPORTED\n')

    lines = []
    lines.append('# B27AB — London -> New York Post-Breakout Dynamic Runner — Result')
    lines.append('')
    lines.append(f'5m rows: **{len(x5):,}**; coverage: **{100.0 * float(coverage):.4f}%**.')
    lines.append('')
    lines.append('**Audit status: PASS.** Frozen B27Z/B27AA entry identities and fixed-E20 baseline economics reproduce before dynamic-runner results are interpreted.')
    lines.append('')
    lines.append('## Fixed E20 vs dynamic structural runner')
    lines.append('')
    lines.append('| Rule | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Runner WR | Runner PF | Runner exp | Runner total | Delta total | Acceptance | E20 reach |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for _, r in s.iterrows():
        lines.append(
            f"| {r.rule} | {r.partition} | {int(r.trades)} | {pct(r.baseline_wr)} | {num(r.baseline_pf)} | {money(r.baseline_exp)} | {money(r.baseline_total)} | "
            f"{pct(r.runner_wr)} | {num(r.runner_pf)} | {money(r.runner_exp)} | {money(r.runner_total)} | {money(r.delta_total)} | {pct(r.acceptance_rate)} | {pct(r.e20_reach_rate)} |"
        )

    lines.append('')
    lines.append('## Runner peak-capture diagnostics')
    lines.append('')
    lines.append('| Rule | Partition | Structure exits | Time exits | Pre-break stops | Exit >= E20 / accepted | Median peak ext | Median exit ext | Median capture | Median giveback | Median hold min |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for _, r in s.iterrows():
        lines.append(
            f"| {r.rule} | {r.partition} | {int(r.structure_exit_count)} | {int(r.time_exit_count)} | {int(r.prebreak_stop_count)} | "
            f"{pct(r.exit_above_e20_rate_given_accept)} | {num(r.median_peak_ext_r_given_accept)}R | {num(r.median_exit_ext_r_given_accept)}R | "
            f"{pct(r.median_capture_ratio_given_accept)} | {num(r.median_giveback_r_given_accept)}R | {num(r.median_hold_minutes)} |"
        )

    lines.append('')
    lines.append('## Frozen primary gate')
    lines.append('')
    for _, r in ps.iterrows():
        improved = bool(r.runner_exp > r.baseline_exp)
        lines.append(
            f"- {r.partition}: fixed exp {money(r.baseline_exp)} -> runner exp {money(r.runner_exp)}; runner PF {num(r.runner_pf)} -> {'PASS' if improved and r.runner_pf >= 1.0 else 'FAIL'}"
        )
    lines.append('')
    lines.append(f"**Overall: {'B27AB_PRIMARY_RUNNER_SUPPORTED' if primary_supported else 'B27AB_PRIMARY_RUNNER_NOT_SUPPORTED'}.**")
    lines.append('')
    lines.append('E20 is diagnostic only in the runner. No pivot-width, ATR, percentage-trail, or target sweep is performed.')
    lines.append('')
    lines.append('Research only; live BBC unchanged.')
    OUT_MD.write_text('\n'.join(lines) + '\n')

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
