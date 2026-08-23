#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_ADAPTIVE_F15_PRE_SECOND_LOW_SHORT_B27BY_Result.md'
OUT_EVENTS = ROOT / 'BTC_24H_ADAPTIVE_F15_PRE_SECOND_LOW_SHORT_B27BY_Events.csv'
OUT_SUM = ROOT / 'BTC_24H_ADAPTIVE_F15_PRE_SECOND_LOW_SHORT_B27BY_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_ADAPTIVE_F15_PRE_SECOND_LOW_SHORT_B27BY_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external', 'development', 'reference_validation')
OOS = ('external', 'reference_validation')
REGIMES = ('BULL', 'BEAR', 'SIDEWAYS')
CLOCKS = ('00-04', '04-08', '08-12', '12-16', '16-20', '20-00')
F = 0.15


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_source() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    d['k1_opp0'] = as_bool(d['k1_opp0'])
    for c in ('obs_start', 'obs_end', 'k1_ts', 'k2_ts', 'k3_ts', 'regime_available_ts'):
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    q = d[d.partition.isin(MAJOR) & d.k1_opp0].copy()

    # Exact B27BE major identity.
    expected_part = {'external': 862, 'development': 1264, 'reference_validation': 641}
    expected_regime = {
        ('BULL', 'external'): 400, ('BULL', 'development'): 500, ('BULL', 'reference_validation'): 246,
        ('BEAR', 'external'): 203, ('BEAR', 'development'): 630, ('BEAR', 'reference_validation'): 289,
        ('SIDEWAYS', 'external'): 259, ('SIDEWAYS', 'development'): 134, ('SIDEWAYS', 'reference_validation'): 106,
    }
    assert len(q) == 2767, len(q)
    for part, n in expected_part.items():
        assert len(q[q.partition == part]) == n, (part, len(q[q.partition == part]), n)
    for (rg, part), n in expected_regime.items():
        got = len(q[(q.regime == rg) & (q.partition == part)])
        assert got == n, (rg, part, got, n)
    assert q.k1_ts.notna().all()
    return q.sort_values(['obs_start', 'partition']).reset_index(drop=True)


def low_touch(bar, L: float) -> bool:
    return float(bar.low) <= L and float(bar.close) >= L


def evaluate_one(x5: pd.DataFrame, r) -> dict:
    start = pd.Timestamp(r.obs_start)
    end = pd.Timestamp(r.obs_end)
    H = float(r.H)
    L = float(r.L)
    assert H > L
    f15 = L + F * (H - L)
    assert L < f15 < H

    q = fast_slice(x5, start, end)
    assert len(q) == 48, (start, len(q))
    assert q.index[0] == start and q.index[-1] == end - BAR5
    assert (q.index.to_series().diff().dropna() == BAR5).all()

    k1_complete = pd.Timestamp(r.k1_ts)
    k1_start = k1_complete - BAR5
    pos = int(q.index.searchsorted(k1_start, side='left'))
    assert pos < len(q) and q.index[pos] == k1_start, (start, k1_start)
    assert low_touch(q.iloc[pos], L)

    # Reproduce first Low visit and OPP0 identity before K1.
    if pos > 0:
        pre = q.iloc[:pos]
        assert not any(low_touch(b, L) for _, b in pre.iterrows())
        prior_high_visit = any(float(b.high) >= H and float(b.close) <= H for _, b in pre.iterrows())
        assert not prior_high_visit
        assert not ((pre.close < L) | (pre.close > H)).any()

    # Consume contiguous K1 Low-touch episode.
    j = pos
    while j < len(q):
        b = q.iloc[j]
        c = float(b.close)
        if c < L or c > H:
            # K1 episode cannot contain a strict boundary close under touch semantics.
            break
        if not low_touch(b, L):
            break
        j += 1

    base = {
        'partition': str(r.partition),
        'regime': str(r.regime),
        'clock_block': str(r.clock_block),
        'obs_start': start,
        'obs_end': end,
        'H': H,
        'L': L,
        'range': H - L,
        'f15_px': f15,
        'k1_ts': k1_complete,
        'k1_start': k1_start,
    }

    if j >= len(q):
        return {**base, 'clean_window': False, 'window_status': 'NO_CAUSAL_LEAVE',
                'leave_bar_start': pd.NaT, 'eligible_start': pd.NaT,
                'fill_ts': pd.NaT, 'terminal_ts': end, 'terminal_type': 'BLOCK_END',
                'l2_after_fill': False, 'minutes_fill_to_l2': np.nan}

    leave = q.iloc[j]
    leave_start = q.index[j]
    c = float(leave.close)
    if c < L:
        return {**base, 'clean_window': False, 'window_status': 'LOW_BREAK_BEFORE_LEAVE',
                'leave_bar_start': leave_start, 'eligible_start': pd.NaT,
                'fill_ts': pd.NaT, 'terminal_ts': leave_start, 'terminal_type': 'L2_BREAK',
                'l2_after_fill': False, 'minutes_fill_to_l2': np.nan}
    if c > H:
        return {**base, 'clean_window': False, 'window_status': 'HIGH_BREAK_BEFORE_LEAVE',
                'leave_bar_start': leave_start, 'eligible_start': pd.NaT,
                'fill_ts': pd.NaT, 'terminal_ts': leave_start, 'terminal_type': 'OPPOSITE_HIGH_BREAK',
                'l2_after_fill': False, 'minutes_fill_to_l2': np.nan}
    assert not low_touch(leave, L)

    eligible_start = leave_start + BAR5
    if eligible_start >= end:
        return {**base, 'clean_window': False, 'window_status': 'LEAVE_AT_BLOCK_END',
                'leave_bar_start': leave_start, 'eligible_start': eligible_start,
                'fill_ts': pd.NaT, 'terminal_ts': end, 'terminal_type': 'BLOCK_END',
                'l2_after_fill': False, 'minutes_fill_to_l2': np.nan}

    fill_ts = pd.NaT
    terminal_ts = end
    terminal_type = 'BLOCK_END'

    k = j + 1
    while k < len(q):
        ts = q.index[k]
        b = q.iloc[k]
        lo = float(b.low)
        hi = float(b.high)
        c = float(b.close)

        l2 = lo <= L
        opp = c > H
        if l2 or opp:
            terminal_ts = ts
            if l2 and opp:
                terminal_type = 'AMBIGUOUS_L2_AND_HIGH_BREAK'
            elif l2:
                terminal_type = 'L2_ARRIVAL'
            else:
                terminal_type = 'OPPOSITE_HIGH_BREAK'
            break

        if pd.isna(fill_ts) and lo <= f15 <= hi:
            fill_ts = ts
        k += 1

    hit = bool(pd.notna(fill_ts) and terminal_type == 'L2_ARRIVAL' and pd.Timestamp(fill_ts) < pd.Timestamp(terminal_ts))
    mins = float((pd.Timestamp(terminal_ts) - pd.Timestamp(fill_ts)) / pd.Timedelta(minutes=1)) if hit else np.nan

    if pd.notna(fill_ts):
        assert pd.Timestamp(fill_ts) >= eligible_start
        assert pd.Timestamp(fill_ts) < pd.Timestamp(terminal_ts), (fill_ts, terminal_ts, terminal_type)

    return {
        **base,
        'clean_window': True,
        'window_status': 'CLEAN_CAUSAL_LEAVE',
        'leave_bar_start': leave_start,
        'eligible_start': eligible_start,
        'fill_ts': fill_ts,
        'terminal_ts': terminal_ts,
        'terminal_type': terminal_type,
        'l2_after_fill': hit,
        'minutes_fill_to_l2': mins,
    }


def metrics(g: pd.DataFrame) -> dict:
    clean = g[g.clean_window].copy()
    fills = clean[clean.fill_ts.notna()].copy()
    hits = fills[fills.l2_after_fill].copy()
    return {
        'k1_n': int(len(g)),
        'clean_n': int(len(clean)),
        'fill_n': int(len(fills)),
        'fill_clean_rate': float(len(fills) / len(clean)) if len(clean) else np.nan,
        'l2_hit_n': int(len(hits)),
        'l2_fill_rate': float(len(hits) / len(fills)) if len(fills) else np.nan,
        'median_min_fill_to_l2': float(hits.minutes_fill_to_l2.median()) if len(hits) else np.nan,
    }


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in MAJOR:
        rows.append({'scope': 'PARTITION', 'name': part, **metrics(d[d.partition == part])})
    rows.append({'scope': 'POOL', 'name': 'POOLED_OOS', **metrics(d[d.partition.isin(OOS)])})
    rows.append({'scope': 'POOL', 'name': 'POOLED_MAJOR', **metrics(d[d.partition.isin(MAJOR)])})
    pm = d[d.partition.isin(MAJOR)]
    for rg in REGIMES:
        rows.append({'scope': 'REGIME', 'name': rg, **metrics(pm[pm.regime == rg])})
    for cb in CLOCKS:
        rows.append({'scope': 'CLOCK', 'name': cb, **metrics(pm[pm.clock_block == cb])})
    return pd.DataFrame(rows)


def getrow(s: pd.DataFrame, scope: str, name: str):
    q = s[(s.scope == scope) & (s.name == name)]
    assert len(q) == 1, (scope, name, len(q))
    return q.iloc[0]


def pct(v):
    return '-' if pd.isna(v) else f'{100 * float(v):.1f}%'


def main() -> None:
    src = load_source()
    x5, coverage = b21.load5()
    assert len(x5) == 698112
    assert abs(float(coverage) - 1.0) < 1e-12

    rows = [evaluate_one(x5, r) for r in src.itertuples(index=False)]
    d = pd.DataFrame(rows)
    assert len(d) == 2767
    assert not d.duplicated(['partition', 'obs_start']).any()
    if d.fill_ts.notna().any():
        assert (pd.to_datetime(d.loc[d.fill_ts.notna(), 'fill_ts'], utc=True) >=
                pd.to_datetime(d.loc[d.fill_ts.notna(), 'eligible_start'], utc=True)).all()
        assert (pd.to_datetime(d.loc[d.fill_ts.notna(), 'fill_ts'], utc=True) <
                pd.to_datetime(d.loc[d.fill_ts.notna(), 'terminal_ts'], utc=True)).all()

    d.to_csv(OUT_EVENTS, index=False)
    s = summarize(d)
    s.to_csv(OUT_SUM, index=False)

    transfer = True
    for part in MAJOR:
        r = getrow(s, 'PARTITION', part)
        transfer = transfer and int(r.fill_n) >= 30 and pd.notna(r.l2_fill_rate) and float(r.l2_fill_rate) >= .70

    clock_ok = True
    for cb in CLOCKS:
        r = getrow(s, 'CLOCK', cb)
        clock_ok = clock_ok and int(r.fill_n) >= 30 and pd.notna(r.l2_fill_rate) and float(r.l2_fill_rate) >= .65

    regime_ok = True
    for rg in REGIMES:
        r = getrow(s, 'REGIME', rg)
        regime_ok = regime_ok and int(r.fill_n) >= 30 and pd.notna(r.l2_fill_rate) and float(r.l2_fill_rate) >= .65

    universal = bool(transfer and clock_ok and regime_ok)
    if universal:
        verdict = 'B27BY_F15_FULL24H_ADAPTIVE_SUPPORTED'
    elif transfer:
        verdict = 'B27BY_F15_TRANSFER_SUPPORTED_NOT_UNIVERSAL'
    else:
        verdict = 'B27BY_F15_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict + '\n')

    lines = [
        '# B27BY — BTC 24H Adaptive F15 Pre-Second-Low SHORT — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.', '',
        '**Audit status: PASS.** Exact persisted B27BE K1+OPP0 identities were reused. This is a direct F15 transfer test; no fraction search, session filter, regime filter, stop, target, fee, PF, PnL, or live change was used.', '',
        'Adaptive entry: **F15 = previous completed 4H Low + 0.15 × (High − Low)** after a completed causal leave from Low Touch #1 and strictly before Low Arrival #2.', '',
        '## Major-partition transfer', '',
        '| Partition | K1 OPP0 | Clean leave | F15 fills | Fill/clean | L2 hits | L2/fill | Median fill->L2 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in MAJOR:
        r = getrow(s, 'PARTITION', part)
        lines.append(f'| {part} | {int(r.k1_n)} | {int(r.clean_n)} | {int(r.fill_n)} | {pct(r.fill_clean_rate)} | {int(r.l2_hit_n)} | {pct(r.l2_fill_rate)} | {r.median_min_fill_to_l2:.1f}m |')

    lines += ['', '## Pooled readout', '',
              '| Pool | K1 OPP0 | Clean leave | F15 fills | Fill/clean | L2/fill | Median fill->L2 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for name in ('POOLED_OOS', 'POOLED_MAJOR'):
        r = getrow(s, 'POOL', name)
        med = '-' if pd.isna(r.median_min_fill_to_l2) else f'{float(r.median_min_fill_to_l2):.1f}m'
        lines.append(f'| {name} | {int(r.k1_n)} | {int(r.clean_n)} | {int(r.fill_n)} | {pct(r.fill_clean_rate)} | {pct(r.l2_fill_rate)} | {med} |')

    lines += ['', '## Regime diagnostics — pooled major', '',
              '| Regime | K1 OPP0 | F15 fills | L2/fill | Median fill->L2 |',
              '|---|---:|---:|---:|---:|']
    for rg in REGIMES:
        r = getrow(s, 'REGIME', rg)
        med = '-' if pd.isna(r.median_min_fill_to_l2) else f'{float(r.median_min_fill_to_l2):.1f}m'
        lines.append(f'| {rg} | {int(r.k1_n)} | {int(r.fill_n)} | {pct(r.l2_fill_rate)} | {med} |')

    lines += ['', '## Clock diagnostics — pooled major', '',
              '| UTC block | K1 OPP0 | F15 fills | L2/fill | Median fill->L2 |',
              '|---|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r = getrow(s, 'CLOCK', cb)
        med = '-' if pd.isna(r.median_min_fill_to_l2) else f'{float(r.median_min_fill_to_l2):.1f}m'
        lines.append(f'| {cb} | {int(r.k1_n)} | {int(r.fill_n)} | {pct(r.l2_fill_rate)} | {med} |')

    lines += ['', '## Frozen gates', '',
              f'- F15 transfer gate across external/development/reference_validation: **{"PASS" if transfer else "FAIL"}**.',
              f'- Six-clock full-24H stability gate: **{"PASS" if clock_ok else "FAIL"}**.',
              f'- BULL/BEAR/SIDEWAYS pooled-major stability gate: **{"PASS" if regime_ok else "FAIL"}**.', '',
              f'**Frozen verdict: `{verdict}`.**', '',
              'A structural pass only permits a separately preregistered economic experiment. L2 is a structural milestone, not a TP.', '',
              'Research only. Live BBC unchanged.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
