#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eth_f85_f15_transfer_m1_k1_opp0 as data_base

PFX = 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M1_STRUCTURE_B27EM'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
LON = ZoneInfo('Europe/London')
NY = ZoneInfo('America/New_York')
UTC = ZoneInfo('UTC')
BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external', 'development', 'reference_validation')
PARTS = {
    'external': (pd.Timestamp('2020-01-01', tz='UTC'), pd.Timestamp('2022-01-01', tz='UTC')),
    'development': (pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')),
    'reference_validation': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-07-30', tz='UTC')),
    'august': (pd.Timestamp('2026-08-01', tz='UTC'), pd.Timestamp('2026-08-26', tz='UTC')),
}


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def part_for(ts: pd.Timestamp):
    for name, (a, z) in PARTS.items():
        if a <= ts < z:
            return name
    return None


def local_bounds(day):
    lon_open_local = datetime.combine(day, time(8, 0), tzinfo=LON)
    ny_open_local = datetime.combine(day, time(9, 30), tzinfo=NY)
    ny_close_local = datetime.combine(day, time(16, 0), tzinfo=NY)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (lon_open_local, ny_open_local, ny_close_local))


def duration_regime(minutes: int) -> str:
    if minutes == 390:
        return 'NORMAL_6H30'
    if minutes == 330:
        return 'DST_MISMATCH_5H30'
    return f'OTHER_{minutes}m'


def classify_long(exe: pd.DataFrame, H: float, L: float) -> dict:
    hi_touching = False
    lo_touching = False
    hi_visits = 0
    lo_visits = 0
    state = 'SEEK_K1'
    k1_start = pd.NaT
    k1_signal = pd.NaT
    leave_start = pd.NaT
    leave_ts = pd.NaT

    for ts, r in exe.iterrows():
        ts = pd.Timestamp(ts)
        hi = float(r.high)
        lo = float(r.low)
        cl = float(r.close)

        if state == 'SEEK_K1':
            if cl > H or cl < L:
                return {
                    'qualified': False, 'reason': 'BREAK_BEFORE_K1',
                    'hi_visits': hi_visits, 'lo_visits': lo_visits,
                    'k1_start': pd.NaT, 'k1_signal': pd.NaT,
                    'leave': False, 'leave_start': pd.NaT, 'leave_ts': pd.NaT,
                    'terminal': 'BREAK_BEFORE_K1', 'terminal_start': ts,
                    'minutes_leave_to_h2': np.nan,
                }

            hit_hi = hi >= H and cl <= H
            hit_lo = lo <= L and cl >= L
            if hit_hi and hit_lo:
                return {
                    'qualified': False, 'reason': 'AMBIGUOUS_BOTH_BOUNDARIES',
                    'hi_visits': hi_visits, 'lo_visits': lo_visits,
                    'k1_start': pd.NaT, 'k1_signal': pd.NaT,
                    'leave': False, 'leave_start': pd.NaT, 'leave_ts': pd.NaT,
                    'terminal': 'AMBIGUOUS_BOTH_BOUNDARIES', 'terminal_start': ts,
                    'minutes_leave_to_h2': np.nan,
                }

            new_lo = bool(hit_lo and not lo_touching)
            new_hi = bool(hit_hi and not hi_touching)
            if new_lo:
                lo_visits += 1
            if new_hi:
                hi_visits += 1
                if hi_visits == 1 and lo_visits == 0:
                    k1_start = ts
                    k1_signal = ts + BAR5
                    state = 'K1_EPISODE'

            hi_touching = bool(hit_hi)
            lo_touching = bool(hit_lo)

            if new_lo and state == 'SEEK_K1':
                return {
                    'qualified': False, 'reason': 'OPPOSITE_VISIT_BEFORE_K1',
                    'hi_visits': hi_visits, 'lo_visits': lo_visits,
                    'k1_start': pd.NaT, 'k1_signal': pd.NaT,
                    'leave': False, 'leave_start': pd.NaT, 'leave_ts': pd.NaT,
                    'terminal': 'OPPOSITE_VISIT_BEFORE_K1', 'terminal_start': ts,
                    'minutes_leave_to_h2': np.nan,
                }
            continue

        if state == 'K1_EPISODE':
            if cl > H or cl < L:
                return {
                    'qualified': True, 'reason': '',
                    'hi_visits': hi_visits, 'lo_visits': lo_visits,
                    'k1_start': k1_start, 'k1_signal': k1_signal,
                    'leave': False, 'leave_start': pd.NaT, 'leave_ts': pd.NaT,
                    'terminal': 'BREAK_DURING_K1', 'terminal_start': ts,
                    'minutes_leave_to_h2': np.nan,
                }
            same_high_episode = hi >= H and cl <= H
            if same_high_episode:
                continue
            leave_start = ts
            leave_ts = ts + BAR5
            state = 'AFTER_LEAVE'
            continue

        if state == 'AFTER_LEAVE':
            h2 = hi >= H
            opposite = cl < L
            if h2 and opposite:
                terminal = 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
            elif h2:
                terminal = 'H2_ARRIVAL'
            elif opposite:
                terminal = 'OPPOSITE_BREAK_BEFORE_H2'
            else:
                continue
            mins = float((ts + BAR5 - leave_ts) / pd.Timedelta(minutes=1)) if terminal == 'H2_ARRIVAL' else np.nan
            return {
                'qualified': True, 'reason': '',
                'hi_visits': hi_visits, 'lo_visits': lo_visits,
                'k1_start': k1_start, 'k1_signal': k1_signal,
                'leave': True, 'leave_start': leave_start, 'leave_ts': leave_ts,
                'terminal': terminal, 'terminal_start': ts,
                'minutes_leave_to_h2': mins,
            }

    if state == 'SEEK_K1':
        return {
            'qualified': False, 'reason': 'NO_K1',
            'hi_visits': hi_visits, 'lo_visits': lo_visits,
            'k1_start': pd.NaT, 'k1_signal': pd.NaT,
            'leave': False, 'leave_start': pd.NaT, 'leave_ts': pd.NaT,
            'terminal': 'NO_K1', 'terminal_start': pd.NaT,
            'minutes_leave_to_h2': np.nan,
        }
    if state == 'K1_EPISODE':
        return {
            'qualified': True, 'reason': '',
            'hi_visits': hi_visits, 'lo_visits': lo_visits,
            'k1_start': k1_start, 'k1_signal': k1_signal,
            'leave': False, 'leave_start': pd.NaT, 'leave_ts': pd.NaT,
            'terminal': 'NO_CAUSAL_LEAVE_BY_END', 'terminal_start': pd.NaT,
            'minutes_leave_to_h2': np.nan,
        }
    return {
        'qualified': True, 'reason': '',
        'hi_visits': hi_visits, 'lo_visits': lo_visits,
        'k1_start': k1_start, 'k1_signal': k1_signal,
        'leave': True, 'leave_start': leave_start, 'leave_ts': leave_ts,
        'terminal': 'NO_H2_BY_END', 'terminal_start': pd.NaT,
        'minutes_leave_to_h2': np.nan,
    }


def synthetic_tests():
    idx = pd.date_range('2026-01-05 14:30', periods=7, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    q = pd.DataFrame([
        [99, 100.2, 98.0, 99.5],
        [99.5, 100.1, 98.5, 99.2],
        [99.2, 99.6, 97.0, 98.0],
        [98.0, 99.0, 96.0, 98.5],
        [98.5, 100.1, 98.0, 99.8],
        [99.8, 100.5, 99.0, 100.2],
        [100.2, 101.0, 100.0, 100.8],
    ], index=idx, columns=['open','high','low','close'])
    a = classify_long(q, H, L)
    assert a['qualified'] and a['leave'] and a['terminal'] == 'H2_ARRIVAL'
    assert a['leave_start'] == idx[2]
    q2 = q.copy(); q2.iloc[0] = [95, 99, 89.5, 91]
    assert not classify_long(q2, H, L)['qualified']
    q3 = q.copy(); q3.iloc[4] = [98.5, 100.1, 89.0, 89.5]
    assert classify_long(q3, H, L)['terminal'] == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'


def session_rows(x5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    actual_start = pd.Timestamp(x5.index.min())
    actual_end_exclusive = pd.Timestamp(x5.index.max()) + BAR5
    start_local = actual_start.tz_convert(LON).date()
    end_local = actual_end_exclusive.tz_convert(LON).date()

    for d in pd.date_range(start_local, end_local, freq='D'):
        day = d.date()
        if day.weekday() >= 5:
            continue
        lon_open, ny_open, ny_close = local_bounds(day)
        if lon_open < actual_start or ny_close > actual_end_exclusive:
            continue
        p = part_for(ny_open)
        if p is None:
            continue

        ref_minutes = int((ny_open - lon_open) / pd.Timedelta(minutes=1))
        expected_ref = ref_minutes // 5
        expected_exe = int((ny_close - ny_open) / BAR5)
        if expected_exe != 78:
            raise AssertionError(f'unexpected NY execution duration {day}: {expected_exe} bars')

        ref = fs(x5, lon_open, ny_open)
        exe = fs(x5, ny_open, ny_close)
        if len(ref) != expected_ref or len(exe) != expected_exe:
            raise AssertionError(
                f'incomplete session bars {day}: ref={len(ref)}/{expected_ref} exe={len(exe)}/{expected_exe}'
            )
        if len(ref) == 0:
            continue
        H = float(ref.high.max()); L = float(ref.low.min()); R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive London-NY R {day}')

        out = classify_long(exe, H, L)
        lon_off = datetime.combine(day, time(8, 0), tzinfo=LON).utcoffset().total_seconds() / 3600.0
        ny_off = datetime.combine(day, time(9, 30), tzinfo=NY).utcoffset().total_seconds() / 3600.0
        rows.append({
            'local_date': str(day), 'partition': p,
            'london_open_utc': lon_open, 'ny_open_utc': ny_open, 'ny_close_utc': ny_close,
            'london_utc_offset_hours': lon_off, 'ny_utc_offset_hours': ny_off,
            'reference_minutes': ref_minutes, 'reference_bars': expected_ref,
            'duration_regime': duration_regime(ref_minutes),
            'H': H, 'L': L, 'R': R,
            **out,
        })
    return pd.DataFrame(rows)


def metrics(q: pd.DataFrame) -> dict:
    complete = int(len(q))
    k = q[q.qualified.fillna(False).astype(bool)] if complete else q
    lv = k[k.leave.fillna(False).astype(bool)] if len(k) else k
    h2 = int((lv.terminal == 'H2_ARRIVAL').sum()) if len(lv) else 0
    opp = int((lv.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum()) if len(lv) else 0
    amb = int((lv.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum()) if len(lv) else 0
    no = int((lv.terminal == 'NO_H2_BY_END').sum()) if len(lv) else 0
    resolved = h2 + opp
    return {
        'sessions': complete,
        'k1_opp0': int(len(k)),
        'k1_rate': float(len(k) / complete) if complete else np.nan,
        'causal_leave': int(len(lv)),
        'leave_rate': float(len(lv) / len(k)) if len(k) else np.nan,
        'h2': h2,
        'opposite': opp,
        'ambiguous': amb,
        'no_h2': no,
        'h2_rate': float(h2 / len(lv)) if len(lv) else np.nan,
        'resolved_h2_share': float(h2 / resolved) if resolved else np.nan,
        'median_min_leave_to_h2': float(pd.to_numeric(lv.loc[lv.terminal == 'H2_ARRIVAL', 'minutes_leave_to_h2'], errors='coerce').median()) if h2 else np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100 * float(x):.1f}%'


def main():
    synthetic_tests()
    prereg = ROOT / 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M1_STRUCTURE_B27EM_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EM preregistration missing')

    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB coverage below gate {coverage:.6f}')

    d = session_rows(x5)
    if d.empty:
        raise AssertionError('no B27EM sessions generated')
    d.to_csv(OUT_DETAIL, index=False)

    unexpected = sorted(set(d.loc[~d.duration_regime.isin(['NORMAL_6H30','DST_MISMATCH_5H30']), 'duration_regime'].astype(str)))

    summary_rows = []
    scopes = [('POOLED_MAJOR', d.partition.isin(MAJOR))]
    scopes += [(p, d.partition.eq(p)) for p in PARTS]
    for regime in sorted(d.duration_regime.unique()):
        scopes.append((regime, d.partition.isin(MAJOR) & d.duration_regime.eq(regime)))
    for name, mask in scopes:
        summary_rows.append({'scope': name, **metrics(d[mask])})
    s = pd.DataFrame(summary_rows)
    s.to_csv(OUT_SUM, index=False)

    major = d[d.partition.isin(MAJOR)]
    m = metrics(major)
    if pd.isna(m['h2_rate']):
        label = 'NO_CAUSAL_LEAVE_SAMPLE'
    elif m['h2_rate'] >= .75:
        label = 'STRONG_HIGH_REVISIT'
    elif m['h2_rate'] >= .65:
        label = 'MODERATE_HIGH_REVISIT'
    else:
        label = 'WEAK_HIGH_REVISIT'

    regime_counts = major.duration_regime.value_counts().to_dict()
    status = 'B27EM_BNB_LONDON_NY_LONG_STRUCTURE_COMPLETE'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# BNB Session-Native London→New York LONG M1 Structure — B27EM Result', '',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. Actual raw span: **{x5.index.min()} to {x5.index.max() + BAR5}**.', '',
        'Clocking is DST-aware: reference = **08:00 Europe/London → 09:30 America/New_York**; execution = **09:30 → 16:00 America/New_York**.', '',
        'B27EM is LONG structural only: no F85/F35, entry, stop, target, PnL, short-side test, or zone-time optimization.', '',
        '## Pooled-major LONG structure', '',
        f'- Complete sessions: **{m["sessions"]}**',
        f'- High K1 OPP0: **{m["k1_opp0"]} ({pct(m["k1_rate"])})**',
        f'- Causal leaves: **{m["causal_leave"]} ({pct(m["leave_rate"])})** of qualified K1',
        f'- H2 arrivals after leave: **{m["h2"]} ({pct(m["h2_rate"])})**',
        f'- Opposite breaks before H2: **{m["opposite"]}**; ambiguous: **{m["ambiguous"]}**; no H2 by NY close: **{m["no_h2"]}**',
        f'- Resolved H2 share: **{pct(m["resolved_h2_share"])}**; median leave→H2: **{m["median_min_leave_to_h2"]:.1f} min**' if not pd.isna(m['median_min_leave_to_h2']) else '- Median leave→H2: **-**',
        f'- Structural label: **{label}**', '',
        '## Reference-duration regimes', '',
        f'- Pooled-major counts: **{regime_counts}**',
        f'- Unexpected regimes: **{unexpected if unexpected else "NONE"}**', '',
        '| Scope | Sessions | K1 OPP0 | K1 rate | Leave | H2 rate | Resolved H2 | Median leave→H2 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in s.iterrows():
        lines.append(
            f'| {r.scope} | {int(r.sessions)} | {int(r.k1_opp0)} | {pct(r.k1_rate)} | {int(r.causal_leave)} | {pct(r.h2_rate)} | {pct(r.resolved_h2_share)} | '
            + ('-' if pd.isna(r.median_min_leave_to_h2) else f'{float(r.median_min_leave_to_h2):.1f}m') + ' |'
        )
    lines += ['', f'**Status: {status}**', '', 'STOP: B27EM ends here. No SHORT, entry discovery, zone-time search, economics, or live integration is run automatically.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
