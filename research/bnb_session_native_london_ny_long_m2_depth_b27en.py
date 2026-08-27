#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Same-directory import when executed as `python research/...py`.
import bnb_session_native_london_ny_long_m1_structure_b27em as base

PFX = 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M2_DEPTH_B27EN'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_LEVELS = ROOT / f'{PFX}_Levels.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
DEV = 'development'
BAR5 = pd.Timedelta(minutes=5)
LEVELS = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35]
Q = [0.10, 0.25, 0.50, 0.75, 0.85, 0.90, 0.95]
EXPECTED_DEV_LEAVES = 97


def _ts(v) -> pd.Timestamp:
    t = pd.Timestamp(v)
    return t.tz_localize('UTC') if t.tzinfo is None else t.tz_convert('UTC')


def _preterminal_end(r: pd.Series) -> pd.Timestamp:
    terminal = str(r.terminal)
    if terminal in ('H2_ARRIVAL', 'OPPOSITE_BREAK_BEFORE_H2', 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'):
        if pd.isna(r.terminal_start):
            raise AssertionError(f'missing terminal_start for {terminal} {r.local_date}')
        return _ts(r.terminal_start)
    if terminal == 'NO_H2_BY_END':
        return _ts(r.ny_close_utc)
    raise AssertionError(f'unexpected causal-leave terminal {terminal} {r.local_date}')


def geometry_rows(x5: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    q = sessions[
        sessions.partition.eq(DEV)
        & sessions.qualified.fillna(False).astype(bool)
        & sessions.leave.fillna(False).astype(bool)
    ].copy()

    if len(q) != EXPECTED_DEV_LEAVES:
        raise AssertionError(f'B27EM development causal leaves mismatch: {len(q)} != {EXPECTED_DEV_LEAVES}')
    if set(q.partition.astype(str)) != {DEV}:
        raise AssertionError('non-development row entered B27EN')

    rows = []
    for _, r in q.iterrows():
        H = float(r.H); L = float(r.L); R = float(r.R)
        if not (np.isfinite(H) and np.isfinite(L) and np.isfinite(R) and R > 0 and H > L):
            raise AssertionError(f'invalid range {r.local_date}')

        start = _ts(r.leave_ts)
        end = _preterminal_end(r)
        if end < start:
            raise AssertionError(f'negative measurement window {r.local_date}: {start} -> {end}')

        # fs() is [start, end), so the terminal candle is strictly excluded.
        pre = base.fs(x5, start, end)
        if len(pre):
            if pre.index.min() < start or pre.index.max() >= end:
                raise AssertionError(f'pre-terminal slicing violation {r.local_date}')
            lows = pre.low.astype(float)
            imin = int(np.argmin(lows.to_numpy()))
            low_ts = pd.Timestamp(lows.index[imin])
            pre_low = float(lows.iloc[imin])
        else:
            low_ts = pd.NaT
            pre_low = H

        depth = max(0.0, (H - pre_low) / R)
        low_frac = (pre_low - L) / R

        row = {
            'local_date': str(r.local_date),
            'partition': str(r.partition),
            'duration_regime': str(r.duration_regime),
            'H': H, 'L': L, 'R': R,
            'leave_ts': start,
            'terminal': str(r.terminal),
            'terminal_start': r.terminal_start,
            'measurement_end_exclusive': end,
            'preterminal_bars': int(len(pre)),
            'preterminal_low': pre_low,
            'preterminal_low_bar_start': low_ts,
            'depth_from_H_R': depth,
            'lowest_level_fraction': low_frac,
            'h2': bool(str(r.terminal) == 'H2_ARRIVAL'),
        }

        for f in LEVELS:
            key = f'F{int(round(f * 100)):02d}'
            level_px = L + f * R
            reached = bool(pre_low <= level_px + max(1e-12, abs(level_px) * 1e-12))
            first_start = pd.NaT
            first_signal = pd.NaT
            first_min = np.nan
            if reached and len(pre):
                hit = pre[pre.low.astype(float) <= level_px + max(1e-12, abs(level_px) * 1e-12)]
                if len(hit):
                    first_start = pd.Timestamp(hit.index[0])
                    first_signal = first_start + BAR5
                    first_min = float((first_signal - start) / pd.Timedelta(minutes=1))
            row[f'{key}_reached_preterminal'] = reached
            row[f'{key}_first_touch_bar_start'] = first_start
            row[f'{key}_first_touch_signal_ts'] = first_signal
            row[f'{key}_minutes_leave_to_touch'] = first_min

        rows.append(row)

    d = pd.DataFrame(rows).sort_values('leave_ts').reset_index(drop=True)
    if len(d) != EXPECTED_DEV_LEAVES or not d.partition.eq(DEV).all():
        raise AssertionError('B27EN detail integrity failed')
    return d


def quantile_rows(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [
        ('ALL', d),
        ('H2', d[d.h2]),
        ('NON_H2', d[~d.h2]),
        ('H2_NORMAL_6H30', d[d.h2 & d.duration_regime.eq('NORMAL_6H30')]),
        ('H2_DST_MISMATCH_5H30', d[d.h2 & d.duration_regime.eq('DST_MISMATCH_5H30')]),
    ]
    for name, q in groups:
        vals = pd.to_numeric(q.depth_from_H_R, errors='coerce').dropna()
        rec = {'scope': name, 'n': int(len(vals)), 'mean_depth_R': float(vals.mean()) if len(vals) else np.nan}
        for p in Q:
            rec[f'p{int(p*100):02d}_depth_R'] = float(vals.quantile(p)) if len(vals) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def level_rows(d: pd.DataFrame) -> pd.DataFrame:
    total = len(d)
    h2_total = int(d.h2.sum())
    non_total = total - h2_total
    rows = []
    for f in LEVELS:
        key = f'F{int(round(f * 100)):02d}'
        reached = d[f'{key}_reached_preterminal'].astype(bool)
        h2_reached = reached & d.h2
        non_reached = reached & ~d.h2
        n_reached = int(reached.sum())
        times = pd.to_numeric(d.loc[reached, f'{key}_minutes_leave_to_touch'], errors='coerce').dropna()
        rows.append({
            'level': key,
            'level_fraction_from_L': f,
            'depth_from_H_R': 1.0 - f,
            'all_reached_n': n_reached,
            'all_reached_rate': float(n_reached / total) if total else np.nan,
            'h2_reached_n': int(h2_reached.sum()),
            'h2_capture_share': float(h2_reached.sum() / h2_total) if h2_total else np.nan,
            'non_h2_reached_n': int(non_reached.sum()),
            'non_h2_reach_rate': float(non_reached.sum() / non_total) if non_total else np.nan,
            'structural_h2_share_if_reached': float(h2_reached.sum() / n_reached) if n_reached else np.nan,
            'median_minutes_leave_to_touch': float(times.median()) if len(times) else np.nan,
        })
    return pd.DataFrame(rows)


def pct(v) -> str:
    return '-' if pd.isna(v) else f'{100.0 * float(v):.1f}%'


def fr(v) -> str:
    return '-' if pd.isna(v) else f'{float(v):.3f}R'


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EN preregistration missing')

    x5, coverage = base.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB coverage below gate {coverage:.6f}')

    sessions = base.session_rows(x5)
    d = geometry_rows(x5, sessions)
    d.to_csv(OUT_DETAIL, index=False)

    s = quantile_rows(d)
    s.to_csv(OUT_SUM, index=False)

    lv = level_rows(d)
    lv.to_csv(OUT_LEVELS, index=False)

    h2 = d[d.h2]
    non = d[~d.h2]
    if len(h2) != 76 or len(non) != 21:
        raise AssertionError(f'B27EM dev terminal reproduction mismatch H2={len(h2)} NON_H2={len(non)}')

    h2s = s[s.scope.eq('H2')].iloc[0]
    nons = s[s.scope.eq('NON_H2')].iloc[0]
    f85 = lv[lv.level.eq('F85')].iloc[0]

    status = 'B27EN_BNB_NATIVE_RETRACEMENT_DEPTH_DEV_COMPLETE'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# BNB Session-Native London→New York LONG M2 Native Retracement Depth — B27EN Result', '',
        f'Raw BNB 5m coverage: **{coverage:.4%}**.', '',
        'Discovery scope is **development only (2022-01-01 -> 2025-01-01)**. External, reference-validation, and August partitions are not used to select or rank a level.', '',
        'This is structural depth discovery only: **no entry execution, TP/SL, PnL, fees, SHORT, DST filter, or live integration**.', '',
        '## Integrity reproduction', '',
        f'- Development causal leaves: **{len(d)} / {EXPECTED_DEV_LEAVES}**',
        f'- H2 arrivals: **{len(h2)}**',
        f'- Non-H2: **{len(non)}**',
        '- Terminal candle is excluded from every depth window to avoid 5m intrabar ordering assumptions.', '',
        '## Native retracement depth from H', '',
        '| Scope | N | P10 | P25 | P50 | P75 | P85 | P90 | P95 | Mean |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in s.iterrows():
        lines.append(
            f'| {r.scope} | {int(r.n)} | {fr(r.p10_depth_R)} | {fr(r.p25_depth_R)} | {fr(r.p50_depth_R)} | '
            f'{fr(r.p75_depth_R)} | {fr(r.p85_depth_R)} | {fr(r.p90_depth_R)} | {fr(r.p95_depth_R)} | {fr(r.mean_depth_R)} |'
        )

    lines += [
        '',
        'Interpretation of depth: **0.15R from H = F85**, **0.20R = F80**, **0.30R = F70**, etc.', '',
        f'- H2 winner median depth: **{fr(h2s.p50_depth_R)}**',
        f'- H2 winner P75 depth: **{fr(h2s.p75_depth_R)}**',
        f'- H2 winner P85 depth: **{fr(h2s.p85_depth_R)}**',
        f'- Non-H2 median depth: **{fr(nons.p50_depth_R)}**', '',
        '## Predeclared level reach table', '',
        '| Level | Depth from H | Reach N | Reach rate | H2 captured | Non-H2 reach | H2 share if reached | Median leave→touch |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in lv.iterrows():
        lines.append(
            f'| {r.level} | {fr(r.depth_from_H_R)} | {int(r.all_reached_n)} | {pct(r.all_reached_rate)} | '
            f'{int(r.h2_reached_n)}/{len(h2)} ({pct(r.h2_capture_share)}) | '
            f'{int(r.non_h2_reached_n)}/{len(non)} ({pct(r.non_h2_reach_rate)}) | '
            f'{pct(r.structural_h2_share_if_reached)} | '
            + ('-' if pd.isna(r.median_minutes_leave_to_touch) else f'{float(r.median_minutes_leave_to_touch):.1f}m') + ' |'
        )

    lines += [
        '', '## F85 descriptive checkpoint', '',
        f'- F85 causal pre-terminal reach: **{int(f85.all_reached_n)}/{len(d)} ({pct(f85.all_reached_rate)})**',
        f'- H2 winners that first have enough depth to reach F85 before the H2 terminal candle: **{int(f85.h2_reached_n)}/{len(h2)} ({pct(f85.h2_capture_share)})**',
        f'- Non-H2 events reaching F85 before terminal/end: **{int(f85.non_h2_reached_n)}/{len(non)} ({pct(f85.non_h2_reach_rate)})**',
        f'- Structural H2 share among F85-reached events: **{pct(f85.structural_h2_share_if_reached)}**', '',
        'B27EN does **not** promote F85 or any alternative. The table is the development-only geometry needed to decide which BNB-native level/band, if any, deserves a separately frozen confirmation/validation milestone.', '',
        f'**Status: {status}**', '',
        'STOP: B27EN ends here. No reclaim confirmation, next-bar entry, TP/SL, economics, validation-partition reveal, SHORT, or live integration is run automatically.'
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
