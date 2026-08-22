#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Result.md'
OUT_CAND = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Candidates.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Status.txt'

PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
FRACS = {'F05':0.05,'F10':0.10,'F15':0.15,'F20':0.20,'F25':0.25}
BAR5 = pd.Timedelta(minutes=5)


def candidate_fill(x5: pd.DataFrame, w: pd.Series, name: str, frac: float) -> dict:
    H = float(w.H); L = float(w.L); rng = H - L
    px = L + frac * rng
    base = {
        'partition': w.partition,
        'date_utc': w.date_utc,
        'signal_ts': pd.Timestamp(w.signal_ts),
        'window_status': w.window_status,
        'entry_name': name,
        'entry_fraction': frac,
        'planned_entry_px': px,
        'H': H, 'L': L, 'range': rng,
        'eligible_start': w.eligible_start,
        'h2_bar_start': w.h2_bar_start,
        'opposite_break_bar_start': w.opposite_break_bar_start,
        'session_end': pd.Timestamp(w.session_end),
    }

    assert H > L
    assert abs(px - (L + frac * (H - L))) <= 1e-12 * max(1.0, abs(px))

    if pd.isna(w.eligible_start) or str(w.window_status).startswith('NO_WINDOW') or w.window_status == 'NO_CAUSAL_LEAVE_BY_SESSION_END':
        return {**base, 'filled': False, 'fill_bar_start': pd.NaT,
                'entry_px': np.nan, 'h2_after_fill': False,
                'minutes_fill_to_h2': np.nan, 'terminal': 'NO_CLEAN_WINDOW'}

    term = b27ad.terminal_start(w)
    q = b27ad.fast_slice(x5, pd.Timestamp(w.eligible_start), term)
    fill_ts = pd.NaT
    for ts, r in q.iterrows():
        # The pre-terminal slice must not contain the terminal conditions.
        if float(r.low) <= L:
            raise AssertionError('H2 appeared inside pre-terminal eligible slice')
        if float(r.close) > H:
            raise AssertionError('opposite break appeared inside pre-terminal eligible slice')
        if float(r.low) <= px <= float(r.high):
            fill_ts = ts
            break

    if pd.isna(fill_ts):
        return {**base, 'filled': False, 'fill_bar_start': pd.NaT,
                'entry_px': np.nan, 'h2_after_fill': False,
                'minutes_fill_to_h2': np.nan, 'terminal': w.window_status}

    if not (pd.Timestamp(fill_ts) >= pd.Timestamp(w.eligible_start)):
        raise AssertionError('candidate filled before causal eligibility')
    if not (pd.Timestamp(fill_ts) < term):
        raise AssertionError('candidate fill is not strictly before terminal/H2 bar')

    h2 = bool(w.window_status == 'H2_ARRIVAL')
    mins = float((pd.Timestamp(w.h2_bar_start) - pd.Timestamp(fill_ts)) /
                 pd.Timedelta(minutes=1)) if h2 else np.nan
    return {**base, 'filled': True, 'fill_bar_start': pd.Timestamp(fill_ts),
            'entry_px': px, 'h2_after_fill': h2,
            'minutes_fill_to_h2': mins, 'terminal': w.window_status}


def synthetic_test() -> None:
    idx = pd.date_range('2026-01-02 13:30', periods=8, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    x = pd.DataFrame([
        {'open':91.0,'high':92.0,'low':89.8,'close':90.5},  # K1 low touch
        {'open':90.5,'high':91.8,'low':89.9,'close':90.7},  # same episode
        {'open':90.7,'high':92.0,'low':90.3,'close':91.5},  # causal leave
        {'open':91.5,'high':92.2,'low':91.2,'close':91.4},  # eligible; F15 in range
        {'open':91.4,'high':93.0,'low':91.0,'close':92.5},
        {'open':92.5,'high':93.0,'low':89.7,'close':90.2},  # H2 terminal
        {'open':90.2,'high':90.5,'low':88.0,'close':88.5},
        {'open':88.5,'high':89.0,'low':87.5,'close':88.0},
    ], index=idx)
    s = pd.Series({'partition':'x','date_utc':'2026-01-02',
                   'previous_session_high':H,'previous_session_low':L,
                   'signal_bar_start':idx[0],'signal_ts':idx[0]+BAR5,
                   'active_session_end':idx[-1]+BAR5})
    w = pd.Series(b27ad.build_window(x, s))
    assert w.window_status == 'H2_ARRIVAL'
    assert w.eligible_start == idx[3]
    z = candidate_fill(x, w, 'F15', 0.15)
    assert z['filled'] and z['fill_bar_start'] == idx[3] and z['h2_after_fill']


def pct(v) -> str:
    return '-' if pd.isna(v) else f'{100.0*float(v):.1f}%'


def num(v) -> str:
    if pd.isna(v): return '-'
    return f'{float(v):.1f}'


def main() -> None:
    synthetic_test()
    x5, coverage = b27ad.b21.load5()
    assert abs(float(coverage) - 1.0) < 1e-12
    s = b27ad.load_k1()
    windows = pd.DataFrame([b27ad.build_window(x5, r) for _, r in s.iterrows()])
    assert len(windows) == len(s)
    assert list(pd.to_datetime(windows.signal_ts, utc=True)) == list(pd.to_datetime(s.signal_ts, utc=True))

    rows = []
    for _, w in windows.iterrows():
        for name, frac in FRACS.items():
            rows.append(candidate_fill(x5, w, name, frac))
    cand = pd.DataFrame(rows)

    # Reproduce frozen B27AD F15 structural identities exactly before interpreting grid.
    expected = {
        'external': (50, 37),
        'development': (79, 59),
        'reference_validation': (34, 24),
        'august': (1, 1),
    }
    f15 = cand[cand.entry_name == 'F15']
    for part, (fills_exp, h2_exp) in expected.items():
        g = f15[(f15.partition == part) & f15.filled.astype(bool)]
        assert len(g) == fills_exp, (part, len(g), fills_exp)
        assert int(g.h2_after_fill.sum()) == h2_exp, (part, int(g.h2_after_fill.sum()), h2_exp)

    sums = []
    passing = []
    for name, frac in FRACS.items():
        candidate_pass = True
        for part in PARTS:
            gw = windows[windows.partition == part]
            g = cand[(cand.entry_name == name) & (cand.partition == part)]
            f = g[g.filled.astype(bool)]
            h2n = int(f.h2_after_fill.sum()) if len(f) else 0
            rate = float(f.h2_after_fill.mean()) if len(f) else np.nan
            clean = int((~gw.window_status.astype(str).str.startswith('NO_WINDOW') &
                         (gw.window_status != 'NO_CAUSAL_LEAVE_BY_SESSION_END')).sum())
            sums.append({
                'entry_name': name, 'entry_fraction': frac, 'partition': part,
                'k1_opportunities': int(len(gw)), 'clean_windows': clean,
                'fills': int(len(f)), 'h2_hits': h2n, 'h2_hit_rate': rate,
                'fill_given_clean': float(len(f)/clean) if clean else np.nan,
                'median_minutes_fill_to_h2': float(f.loc[f.h2_after_fill.astype(bool),'minutes_fill_to_h2'].median()) if h2n else np.nan,
            })
            if part in MAJOR:
                candidate_pass = candidate_pass and len(f) >= 30 and pd.notna(rate) and rate >= 0.70
        if candidate_pass:
            passing.append(name)

    sm = pd.DataFrame(sums)
    cand.to_csv(OUT_CAND, index=False)
    sm.to_csv(OUT_SUM, index=False)
    status = 'B27AK_PASSING_ZONES_' + ('_'.join(passing) if passing else 'NONE')
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# B27AK — BTC London->NY SHORT Pre-H2 Retrace Zone Discovery — Result',
        '',
        f'5m rows: **{len(x5):,}**; coverage: **{100.0*float(coverage):.4f}%**.',
        '',
        '**Audit status: PASS.** Frozen B27AD K1/OPP0 chronology reproduced and F15 structural identities matched before the independent SHORT retrace grid was interpreted.',
        '',
        '## Frozen F05-F25 structural grid',
        '',
        '| Zone | Partition | K1 | Clean | Fills | Fill/clean | H2 hits | H2/fill | Median min fill->H2 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for name in FRACS:
        for part in PARTS:
            r = sm[(sm.entry_name == name) & (sm.partition == part)].iloc[0]
            lines.append(f'| {name} | {part} | {int(r.k1_opportunities)} | {int(r.clean_windows)} | {int(r.fills)} | {pct(r.fill_given_clean)} | {int(r.h2_hits)} | {pct(r.h2_hit_rate)} | {num(r.median_minutes_fill_to_h2)} |')
    lines += [
        '',
        '## Frozen screen',
        '',
        'Requirement: >=30 fills AND >=70% H2/fill in EACH external, development, and reference_validation partition.',
        '',
        '**Passing zones: ' + (', '.join(passing) if passing else 'NONE') + '.**',
        '',
        'No PnL, stop, target, runner, EMA, swing, or 4H regime information was used to choose a zone.',
        '',
        'If more than one zone passes, this result does not post-hoc choose one winner.',
        '',
        'Research only; live BBC unchanged.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
