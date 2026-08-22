#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_london_ny_pre_second_touch_entry_b27w as b27w

ROOT = Path(__file__).resolve().parent.parent
B27W_ENTRIES = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_F85_WINNER_MAE_B27X_Result.md'
OUT_PATHS = ROOT / 'BTC_LONDON_NY_F85_WINNER_MAE_B27X_Paths.csv'
OUT_WINNER_SUM = ROOT / 'BTC_LONDON_NY_F85_WINNER_MAE_B27X_WinnerSummary.csv'
OUT_SURVIVAL = ROOT / 'BTC_LONDON_NY_F85_WINNER_MAE_B27X_StopSurvival.csv'
OUT_FAILURE_SUM = ROOT / 'BTC_LONDON_NY_F85_WINNER_MAE_B27X_FailureSummary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_F85_WINNER_MAE_B27X_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
F85 = 0.85
PARTS = ('external', 'development', 'reference_validation', 'august')
DISTANCES = tuple(round(x, 2) for x in np.arange(0.05, 0.851, 0.05))


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def fast_slice_inclusive_last(x5: pd.DataFrame, start: pd.Timestamp, last_bar_start: pd.Timestamp) -> pd.DataFrame:
    return fast_slice(x5, start, last_bar_start + BAR5)


def qtile(x: pd.Series, q: float) -> float:
    z = pd.to_numeric(x, errors='coerce').dropna()
    return float(z.quantile(q)) if len(z) else np.nan


def synthetic_tests():
    H, L = 100.0, 90.0
    rng = H - L
    entry = L + F85 * rng  # 98.5
    idx = pd.date_range('2026-01-02 14:00', periods=4, freq='5min', tz='UTC')
    q = pd.DataFrame([
        {'open': 99.0, 'high': 99.0, 'low': 98.0, 'close': 98.6},   # fill bar; low frac .80
        {'open': 98.6, 'high': 99.0, 'low': 97.6, 'close': 98.2},   # pre-H2 low frac .76
        {'open': 98.2, 'high': 99.5, 'low': 98.0, 'close': 99.0},
        {'open': 99.0, 'high': 100.2, 'low': 97.0, 'close': 99.8},  # H2; low frac .70
    ], index=idx)
    assert float(q.iloc[0].low) <= entry <= float(q.iloc[0].high)
    pre = fast_slice(q, idx[0], idx[3])
    through = fast_slice_inclusive_last(q, idx[0], idx[3])
    nxt = fast_slice(q, idx[0] + BAR5, idx[3])
    pre_frac = (float(pre.low.min()) - L) / rng
    through_frac = (float(through.low.min()) - L) / rng
    next_frac = (float(nxt.low.min()) - L) / rng
    assert abs(pre_frac - 0.76) < 1e-12
    assert abs(through_frac - 0.70) < 1e-12
    assert abs(next_frac - 0.76) < 1e-12
    pre_d = max(0.0, F85 - pre_frac)
    through_d = max(0.0, F85 - through_frac)
    assert abs(pre_d - 0.09) < 1e-12
    assert abs(through_d - 0.15) < 1e-12
    # Equality is a stop touch, therefore D15 does NOT survive a .70 minimum fraction.
    stop_frac = F85 - 0.15
    assert not (through_frac > stop_frac)
    assert (through_frac > (F85 - 0.20))


def load_persisted_b27w_f85() -> pd.DataFrame:
    p = pd.read_csv(B27W_ENTRIES)
    p = p[p.entry_name == 'F85'].copy()
    for c in ('signal_ts', 'eligible_start', 'h2_bar_start', 'opposite_break_bar_start', 'entry_ts'):
        if c in p.columns:
            p[c] = pd.to_datetime(p[c], utc=True, errors='coerce')
    p['filled'] = p['filled'].astype(str).str.lower().map({'true': True, 'false': False}).fillna(p['filled']).astype(bool)
    p['target_hit'] = p['target_hit'].astype(str).str.lower().map({'true': True, 'false': False}).fillna(p['target_hit']).astype(bool)
    return p.sort_values(['partition', 'signal_ts']).reset_index(drop=True)


def reconstruct_b27w_f85(x5: pd.DataFrame):
    s = b27w.load_k1()
    windows = pd.DataFrame([b27w.build_window(x5, r) for _, r in s.iterrows()])
    entries = pd.DataFrame([b27w.simulate_entry(x5, w, 'F85', F85) for _, w in windows.iterrows()])
    return s, windows, entries


def assert_identity(rebuilt: pd.DataFrame, persisted: pd.DataFrame):
    assert len(rebuilt) == len(persisted)
    rb = rebuilt.sort_values(['partition', 'signal_ts']).reset_index(drop=True).copy()
    ps = persisted.sort_values(['partition', 'signal_ts']).reset_index(drop=True).copy()
    assert list(rb.partition.astype(str)) == list(ps.partition.astype(str))
    assert list(pd.to_datetime(rb.signal_ts, utc=True)) == list(pd.to_datetime(ps.signal_ts, utc=True))
    assert list(rb.window_status.astype(str)) == list(ps.window_status.astype(str))
    assert list(rb.filled.astype(bool)) == list(ps.filled.astype(bool))
    assert list(rb.target_hit.astype(bool)) == list(ps.target_hit.astype(bool))
    for i in range(len(rb)):
        if bool(rb.loc[i, 'filled']):
            assert pd.Timestamp(rb.loc[i, 'entry_ts']) == pd.Timestamp(ps.loc[i, 'entry_ts'])
            assert abs(float(rb.loc[i, 'entry_px']) - float(ps.loc[i, 'entry_px'])) < 1e-9 * max(1.0, abs(float(rb.loc[i, 'entry_px'])))


def path_row(x5: pd.DataFrame, w: pd.Series, e: pd.Series) -> dict:
    H = float(w.H); L = float(w.L); rng = H - L
    entry_px = L + F85 * rng
    base = {
        'partition': w.partition,
        'date_utc': w.date_utc,
        'signal_ts': pd.Timestamp(w.signal_ts),
        'window_status': w.window_status,
        'filled': bool(e.filled),
        'target_hit': bool(e.target_hit),
        'entry_ts': pd.Timestamp(e.entry_ts) if bool(e.filled) else pd.NaT,
        'entry_px': float(e.entry_px) if bool(e.filled) else np.nan,
        'entry_fraction': F85,
        'H': H,
        'L': L,
        'range': rng,
        'h2_bar_start': pd.Timestamp(w.h2_bar_start) if pd.notna(w.h2_bar_start) else pd.NaT,
        'opposite_break_bar_start': pd.Timestamp(w.opposite_break_bar_start) if pd.notna(w.opposite_break_bar_start) else pd.NaT,
    }
    if not bool(e.filled):
        return {**base,
                'path_class': 'NO_FILL',
                'pre_h2_min_low': np.nan, 'pre_h2_min_frac': np.nan,
                'pre_h2_required_distance': np.nan,
                'to_h2_conservative_min_low': np.nan, 'to_h2_conservative_min_frac': np.nan,
                'to_h2_required_distance': np.nan,
                'next_bar_pre_h2_min_frac': np.nan, 'next_bar_pre_h2_required_distance': np.nan,
                'failure_terminal_min_low': np.nan, 'failure_terminal_min_frac': np.nan,
                'failure_required_distance': np.nan}

    entry_ts = pd.Timestamp(e.entry_ts)
    assert abs(float(e.entry_px) - entry_px) < 1e-9 * max(1.0, abs(entry_px))

    if bool(e.target_hit):
        h2 = pd.Timestamp(w.h2_bar_start)
        assert entry_ts < h2
        pre = fast_slice(x5, entry_ts, h2)
        through = fast_slice_inclusive_last(x5, entry_ts, h2)
        assert len(pre) >= 1 and len(through) == len(pre) + 1
        pre_min = float(pre.low.min())
        through_min = float(through.low.min())
        pre_frac = (pre_min - L) / rng
        through_frac = (through_min - L) / rng
        pre_dist = max(0.0, F85 - pre_frac)
        through_dist = max(0.0, F85 - through_frac)
        nxt = fast_slice(x5, entry_ts + BAR5, h2)
        if len(nxt):
            next_frac = (float(nxt.low.min()) - L) / rng
            next_dist = max(0.0, F85 - next_frac)
        else:
            next_frac = np.nan; next_dist = np.nan
        return {**base,
                'path_class': 'F85_H2_WINNER',
                'pre_h2_min_low': pre_min, 'pre_h2_min_frac': pre_frac,
                'pre_h2_required_distance': pre_dist,
                'to_h2_conservative_min_low': through_min, 'to_h2_conservative_min_frac': through_frac,
                'to_h2_required_distance': through_dist,
                'next_bar_pre_h2_min_frac': next_frac, 'next_bar_pre_h2_required_distance': next_dist,
                'failure_terminal_min_low': np.nan, 'failure_terminal_min_frac': np.nan,
                'failure_required_distance': np.nan}

    # Non-H2 fill: measure adverse path through the terminal bar when there is an opposite/ambiguous terminal,
    # otherwise to session end (exclusive, because session_end is a boundary rather than an active-session bar).
    if w.window_status == 'OPPOSITE_BREAK_BEFORE_H2':
        term = pd.Timestamp(w.opposite_break_bar_start)
        q = fast_slice_inclusive_last(x5, entry_ts, term)
    elif w.window_status == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK':
        term = pd.Timestamp(w.terminal_bar_start)
        q = fast_slice_inclusive_last(x5, entry_ts, term)
    else:
        q = fast_slice(x5, entry_ts, pd.Timestamp(w.session_end))
    assert len(q) >= 1
    mn = float(q.low.min()); mf = (mn - L) / rng; dist = max(0.0, F85 - mf)
    return {**base,
            'path_class': 'F85_NON_H2_FILL',
            'pre_h2_min_low': np.nan, 'pre_h2_min_frac': np.nan,
            'pre_h2_required_distance': np.nan,
            'to_h2_conservative_min_low': np.nan, 'to_h2_conservative_min_frac': np.nan,
            'to_h2_required_distance': np.nan,
            'next_bar_pre_h2_min_frac': np.nan, 'next_bar_pre_h2_required_distance': np.nan,
            'failure_terminal_min_low': mn, 'failure_terminal_min_frac': mf,
            'failure_required_distance': dist}


def winner_summary(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTS:
        g = paths[(paths.partition == part) & (paths.path_class == 'F85_H2_WINNER')]
        rows.append({
            'partition': part,
            'winner_n': int(len(g)),
            'pre_d_p50': qtile(g.pre_h2_required_distance, .50),
            'pre_d_p75': qtile(g.pre_h2_required_distance, .75),
            'pre_d_p90': qtile(g.pre_h2_required_distance, .90),
            'pre_d_p95': qtile(g.pre_h2_required_distance, .95),
            'pre_d_max': float(pd.to_numeric(g.pre_h2_required_distance, errors='coerce').max()) if len(g) else np.nan,
            'cons_d_p50': qtile(g.to_h2_required_distance, .50),
            'cons_d_p75': qtile(g.to_h2_required_distance, .75),
            'cons_d_p90': qtile(g.to_h2_required_distance, .90),
            'cons_d_p95': qtile(g.to_h2_required_distance, .95),
            'cons_d_max': float(pd.to_numeric(g.to_h2_required_distance, errors='coerce').max()) if len(g) else np.nan,
            'nextbar_d_p50': qtile(g.next_bar_pre_h2_required_distance, .50),
            'nextbar_d_p90': qtile(g.next_bar_pre_h2_required_distance, .90),
        })
    return pd.DataFrame(rows)


def stop_survival(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTS:
        g = paths[(paths.partition == part) & (paths.path_class == 'F85_H2_WINNER')].copy()
        for d in DISTANCES:
            stop_frac = F85 - d
            if len(g):
                pre_survive = g.pre_h2_min_frac.astype(float) > stop_frac
                cons_survive = g.to_h2_conservative_min_frac.astype(float) > stop_frac
                pre_n = int(pre_survive.sum()); cons_n = int(cons_survive.sum())
                n = int(len(g))
            else:
                n = pre_n = cons_n = 0
            rows.append({
                'partition': part,
                'distance': d,
                'stop_fraction': stop_frac,
                'winner_n': n,
                'pre_h2_survive_n': pre_n,
                'pre_h2_survive_rate': pre_n / n if n else np.nan,
                'conservative_survive_n': cons_n,
                'conservative_survive_rate': cons_n / n if n else np.nan,
            })
    return pd.DataFrame(rows)


def failure_summary(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTS:
        g = paths[(paths.partition == part) & (paths.path_class == 'F85_NON_H2_FILL')]
        rows.append({
            'partition': part,
            'failure_n': int(len(g)),
            'failure_d_p50': qtile(g.failure_required_distance, .50),
            'failure_d_p75': qtile(g.failure_required_distance, .75),
            'failure_d_p90': qtile(g.failure_required_distance, .90),
            'failure_d_p95': qtile(g.failure_required_distance, .95),
            'failure_d_max': float(pd.to_numeric(g.failure_required_distance, errors='coerce').max()) if len(g) else np.nan,
        })
    return pd.DataFrame(rows)


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.3f}'


def main():
    synthetic_tests()
    x5, coverage = b21.load5()
    s, windows, rebuilt = reconstruct_b27w_f85(x5)
    persisted = load_persisted_b27w_f85()
    assert_identity(rebuilt, persisted)

    assert len(windows) == len(rebuilt) == len(s)
    rows = [path_row(x5, windows.iloc[i], rebuilt.iloc[i]) for i in range(len(rebuilt))]
    paths = pd.DataFrame(rows)

    # Hard real-data assertions.
    assert int(paths.filled.sum()) == int(rebuilt.filled.astype(bool).sum())
    assert int((paths.path_class == 'F85_H2_WINNER').sum()) == int(rebuilt.target_hit.astype(bool).sum())
    for r in paths[paths.path_class == 'F85_H2_WINNER'].itertuples(index=False):
        assert pd.Timestamp(r.entry_ts) < pd.Timestamp(r.h2_bar_start)
        assert float(r.to_h2_conservative_min_low) <= float(r.pre_h2_min_low) + 1e-12
        assert float(r.to_h2_required_distance) + 1e-12 >= float(r.pre_h2_required_distance)
        assert abs(float(r.entry_px) - (float(r.L) + F85 * (float(r.H) - float(r.L)))) < 1e-9 * max(1.0, abs(float(r.entry_px)))

    ws = winner_summary(paths)
    surv = stop_survival(paths)
    fs = failure_summary(paths)

    paths.to_csv(OUT_PATHS, index=False)
    ws.to_csv(OUT_WINNER_SUM, index=False)
    surv.to_csv(OUT_SURVIVAL, index=False)
    fs.to_csv(OUT_FAILURE_SUM, index=False)
    pd.DataFrame(paths.path_class.value_counts()).to_csv(OUT_STATUS)

    md = [
        '# B27X — London -> New York F85 Winner MAE / Stop-Distance Audit — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        '**Audit status: PASS.** B27W F85 fill identity, entry timestamps, and H2 classifications were reproduced exactly from raw 5m chronology.', '',
        'B27X is diagnostic only: no stop distance is selected or promoted.', '',
        '## F85 H2-winner adverse excursion', '',
        '| Partition | Winners | Pre-H2 D P50 | P75 | P90 | P95 | Max | Conservative-through-H2 D P50 | P75 | P90 | P95 | Max |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for r in ws.itertuples(index=False):
        md.append(f'| {r.partition} | {r.winner_n} | {num(r.pre_d_p50)} | {num(r.pre_d_p75)} | {num(r.pre_d_p90)} | {num(r.pre_d_p95)} | {num(r.pre_d_max)} | {num(r.cons_d_p50)} | {num(r.cons_d_p75)} | {num(r.cons_d_p90)} | {num(r.cons_d_p95)} | {num(r.cons_d_max)} |')

    show_ds = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85)
    md += ['', '## Conservative winner-survival curve', '',
           'Distance D is measured downward from F85 in previous-London-range units. Equality with the stop counts as stopped.', '',
           '| Partition | D | Stop fraction | H2 winners | Pre-H2 survive | Conservative through-H2 survive |',
           '|---|---:|---:|---:|---:|---:|']
    for r in surv[surv.distance.isin(show_ds)].itertuples(index=False):
        md.append(f'| {r.partition} | {r.distance:.2f} | {r.stop_fraction:.2f} | {r.winner_n} | {pct(r.pre_h2_survive_rate)} | {pct(r.conservative_survive_rate)} |')

    md += ['', '## Non-H2 filled-path comparison', '',
           '| Partition | Non-H2 fills | Adverse D P50 | P75 | P90 | P95 | Max |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in fs.itertuples(index=False):
        md.append(f'| {r.partition} | {r.failure_n} | {num(r.failure_d_p50)} | {num(r.failure_d_p75)} | {num(r.failure_d_p90)} | {num(r.failure_d_p95)} | {num(r.failure_d_max)} |')

    md += ['', 'Full D05-D85 survival curve and one-row-per-F85-path audit are persisted in CSV outputs.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
