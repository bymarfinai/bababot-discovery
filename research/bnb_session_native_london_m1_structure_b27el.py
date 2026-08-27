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

PFX = 'BNB_SESSION_NATIVE_LONDON_M1_STRUCTURE_B27EL'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
LON = ZoneInfo('Europe/London')
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


def episodes(mask: pd.Series) -> int:
    if len(mask) == 0:
        return 0
    a = mask.astype(bool).to_numpy()
    return int(np.sum(a & np.r_[True, ~a[:-1]]))


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def num(x, n=1):
    return '-' if pd.isna(x) else f'{float(x):.{n}f}'


def local_bounds(d):
    pre_start = datetime.combine(d, time(0, 0), tzinfo=LON)
    lon_open = datetime.combine(d, time(8, 0), tzinfo=LON)
    lon_end = datetime.combine(d, time(13, 0), tzinfo=LON)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (pre_start, lon_open, lon_end))


def first_break(exe: pd.DataFrame, H: float, L: float):
    up = exe.close.astype(float) > H
    dn = exe.close.astype(float) < L
    iu = int(np.flatnonzero(up.to_numpy())[0]) if bool(up.any()) else None
    idn = int(np.flatnonzero(dn.to_numpy())[0]) if bool(dn.any()) else None
    if iu is None and idn is None:
        return None, None
    if idn is None or (iu is not None and iu < idn):
        return 'UP_BREAK', iu
    return 'DOWN_BREAK', idn


def post_structure(exe: pd.DataFrame, break_i: int, side: str, H: float, L: float, R: float):
    bts = pd.Timestamp(exe.index[break_i])
    post = exe.iloc[break_i + 1:].copy()  # causal: breakout known only at its close
    boundary = H if side == 'UP_BREAK' else L
    if side == 'UP_BREAK':
        ret = post.low.astype(float) <= H
        accept = post.close.astype(float) < H
        hold = ret & ~accept
        levels = {k: H + k * R for k in (0.10, 0.20, 0.30, 0.50)}
        hits = {k: post.high.astype(float) >= px for k, px in levels.items()}
        opp = post.low.astype(float) <= L
    else:
        ret = post.high.astype(float) >= L
        accept = post.close.astype(float) > L
        hold = ret & ~accept
        levels = {k: L - k * R for k in (0.10, 0.20, 0.30, 0.50)}
        hits = {k: post.low.astype(float) <= px for k, px in levels.items()}
        opp = post.high.astype(float) >= H

    nret = episodes(ret)
    first_retest_ts = pd.NaT
    first_retest_state = 'NO_RETEST'
    if bool(ret.any()):
        ir = int(np.flatnonzero(ret.to_numpy())[0])
        first_retest_ts = pd.Timestamp(post.index[ir])
        first_retest_state = 'ACCEPT_BACK_INSIDE' if bool(accept.iloc[ir]) else 'HOLD_RETEST'

    first_event = 'TIMEOUT'
    first_event_ts = pd.NaT
    for j, (ts, bar) in enumerate(post.iterrows()):
        e10 = bool(hits[0.10].iloc[j])
        r = bool(ret.iloc[j])
        a = bool(accept.iloc[j])
        h = bool(hold.iloc[j])
        if e10 and (r or a):
            first_event = 'AMBIGUOUS_E10_BOUNDARY_INTERACTION'
            first_event_ts = pd.Timestamp(ts)
            break
        if e10:
            first_event = 'DIRECT_E10'
            first_event_ts = pd.Timestamp(ts)
            break
        if a:
            first_event = 'ACCEPT_BACK_INSIDE'
            first_event_ts = pd.Timestamp(ts)
            break
        if h:
            first_event = 'BOUNDARY_HOLD_RETEST'
            first_event_ts = pd.Timestamp(ts)
            break

    hit_ts = {}
    for k, m in hits.items():
        hit_ts[k] = pd.Timestamp(post.index[int(np.flatnonzero(m.to_numpy())[0])]) if bool(m.any()) else pd.NaT

    ret_before_e20 = np.nan
    if pd.notna(hit_ts[0.20]):
        e20pos = int(post.index.get_loc(hit_ts[0.20]))
        ret_before_e20 = episodes(ret.iloc[:e20pos])

    hold_then_e10 = False
    hold_then_e20 = False
    if first_event == 'BOUNDARY_HOLD_RETEST':
        after = post.loc[first_event_ts + BAR5:]
        if len(after):
            if side == 'UP_BREAK':
                hold_then_e10 = bool((after.high.astype(float) >= H + 0.10 * R).any())
                hold_then_e20 = bool((after.high.astype(float) >= H + 0.20 * R).any())
            else:
                hold_then_e10 = bool((after.low.astype(float) <= L - 0.10 * R).any())
                hold_then_e20 = bool((after.low.astype(float) <= L - 0.20 * R).any())

    return {
        'breakout_ts': bts,
        'retest_episodes': nret,
        'retest_bucket': '0' if nret == 0 else ('1' if nret == 1 else ('2' if nret == 2 else '3+')),
        'first_retest_ts': first_retest_ts,
        'first_retest_state': first_retest_state,
        'first_event': first_event,
        'first_event_ts': first_event_ts,
        'post_e10': pd.notna(hit_ts[0.10]),
        'post_e20': pd.notna(hit_ts[0.20]),
        'post_e30': pd.notna(hit_ts[0.30]),
        'post_e50': pd.notna(hit_ts[0.50]),
        'first_e10_ts': hit_ts[0.10],
        'first_e20_ts': hit_ts[0.20],
        'opposite_boundary_reached': bool(opp.any()) if len(post) else False,
        'retest_episodes_before_e20': ret_before_e20,
        'hold_then_e10': hold_then_e10,
        'hold_then_e20': hold_then_e20,
    }


def session_rows(x5: pd.DataFrame):
    rows = []
    start_local = pd.Timestamp(data_base.START).tz_convert(LON).date()
    end_local = pd.Timestamp(data_base.END - pd.Timedelta(days=1)).tz_convert(LON).date()
    for d in pd.date_range(start_local, end_local, freq='D'):
        day = d.date()
        if day.weekday() >= 5:
            continue
        pre_start, lon_open, lon_end = local_bounds(day)
        if pre_start < data_base.START or lon_end > data_base.END:
            continue
        p = part_for(lon_open)
        if p is None:
            continue
        pre = fs(x5, pre_start, lon_open)
        exe = fs(x5, lon_open, lon_end)
        if len(pre) != 96 or len(exe) != 60:
            raise AssertionError(f'incomplete London-local bars {day}: pre={len(pre)} exe={len(exe)}')
        H = float(pre.high.max()); L = float(pre.low.min()); R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive pre-London R {day}')
        side, bi = first_break(exe, H, L)
        offset_h = datetime.combine(day, time(8, 0), tzinfo=LON).utcoffset().total_seconds() / 3600.0
        base = {
            'local_date': str(day), 'partition': p,
            'london_open_utc': lon_open, 'london_end_utc': lon_end,
            'utc_offset_hours': offset_h, 'dst_regime': 'BST' if offset_h == 1 else 'GMT',
            'H': H, 'L': L, 'R': R,
            'break_side': side or 'NO_BREAK',
        }
        if side is None:
            rows.append({**base, 'breakout_ts': pd.NaT, 'minutes_open_to_break': np.nan,
                         'retest_episodes': np.nan, 'retest_bucket': 'NA', 'first_retest_ts': pd.NaT,
                         'first_retest_state': 'NA', 'first_event': 'NO_BREAK', 'first_event_ts': pd.NaT,
                         'post_e10': False, 'post_e20': False, 'post_e30': False, 'post_e50': False,
                         'first_e10_ts': pd.NaT, 'first_e20_ts': pd.NaT,
                         'opposite_boundary_reached': False, 'retest_episodes_before_e20': np.nan,
                         'hold_then_e10': False, 'hold_then_e20': False})
            continue
        z = post_structure(exe, bi, side, H, L, R)
        z['minutes_open_to_break'] = float((z['breakout_ts'] - lon_open) / pd.Timedelta(minutes=1))
        rows.append({**base, **z})
    return pd.DataFrame(rows)


def side_metrics(q: pd.DataFrame):
    if len(q) == 0:
        return {k: np.nan for k in ['n','median_break_min','retest_rate','one_retest_rate','hold_first_rate','accept_first_rate','direct_e10_rate','hold_event_rate','accept_event_rate','ambiguous_rate','e10_rate','e20_rate','e30_rate','e50_rate','opposite_boundary_rate','hold_then_e20_rate']}
    ret = q[q.retest_episodes.fillna(0) > 0]
    hold_first = ret.first_retest_state.eq('HOLD_RETEST') if len(ret) else pd.Series(dtype=bool)
    accept_first = ret.first_retest_state.eq('ACCEPT_BACK_INSIDE') if len(ret) else pd.Series(dtype=bool)
    hold_event = q[q.first_event.eq('BOUNDARY_HOLD_RETEST')]
    return {
        'n': int(len(q)),
        'median_break_min': float(q.minutes_open_to_break.median()),
        'retest_rate': float((q.retest_episodes > 0).mean()),
        'one_retest_rate': float(q.retest_bucket.eq('1').mean()),
        'hold_first_rate': float(hold_first.mean()) if len(ret) else np.nan,
        'accept_first_rate': float(accept_first.mean()) if len(ret) else np.nan,
        'direct_e10_rate': float(q.first_event.eq('DIRECT_E10').mean()),
        'hold_event_rate': float(q.first_event.eq('BOUNDARY_HOLD_RETEST').mean()),
        'accept_event_rate': float(q.first_event.eq('ACCEPT_BACK_INSIDE').mean()),
        'ambiguous_rate': float(q.first_event.eq('AMBIGUOUS_E10_BOUNDARY_INTERACTION').mean()),
        'e10_rate': float(q.post_e10.astype(bool).mean()),
        'e20_rate': float(q.post_e20.astype(bool).mean()),
        'e30_rate': float(q.post_e30.astype(bool).mean()),
        'e50_rate': float(q.post_e50.astype(bool).mean()),
        'opposite_boundary_rate': float(q.opposite_boundary_reached.astype(bool).mean()),
        'hold_then_e20_rate': float(hold_event.hold_then_e20.astype(bool).mean()) if len(hold_event) else np.nan,
    }


def labels(q: pd.DataFrame):
    r = side_metrics(q)
    if r['direct_e10_rate'] >= .50:
        seq = 'DIRECT_CONTINUATION_DOMINANT'
    elif r['hold_event_rate'] >= .50:
        seq = 'HOLD_RETEST_DOMINANT'
    elif r['accept_event_rate'] >= .50:
        seq = 'FAILED_BREAK_DOMINANT'
    else:
        seq = 'MIXED_BREAK_SEQUENCE'
    e20 = q[q.post_e20.astype(bool)].copy()
    if len(e20) == 0:
        ret = 'NO_E20_SAMPLE'
    else:
        c0 = float((e20.retest_episodes_before_e20.fillna(0) == 0).mean())
        c1 = float((e20.retest_episodes_before_e20 == 1).mean())
        cm = float((e20.retest_episodes_before_e20 >= 2).mean())
        if c0 >= .60: ret = 'NO_RETEST_TO_E20_DOMINANT'
        elif c1 >= .50: ret = 'ONE_RETEST_TO_E20_DOMINANT'
        elif cm >= .50: ret = 'MULTI_RETEST_TO_E20_DOMINANT'
        else: ret = 'MIXED_RETEST_TO_E20'
    return seq, ret


def main():
    prereg = ROOT / 'BNB_SESSION_NATIVE_LONDON_M1_STRUCTURE_B27EL_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EL preregistration missing')
    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB coverage below gate {coverage:.6f}')
    d = session_rows(x5)
    if d.empty:
        raise AssertionError('no London sessions generated')
    d.to_csv(OUT_DETAIL, index=False)

    summary = []
    scopes = [('POOLED_MAJOR', d.partition.isin(MAJOR))]
    scopes += [(p, d.partition.eq(p)) for p in PARTS]
    scopes += [('GMT', d.partition.isin(MAJOR) & d.dst_regime.eq('GMT')),
               ('BST', d.partition.isin(MAJOR) & d.dst_regime.eq('BST'))]
    for scope, mask in scopes:
        z = d[mask]
        for side in ('UP_BREAK', 'DOWN_BREAK'):
            q = z[z.break_side.eq(side)]
            summary.append({'scope': scope, 'side': side, **side_metrics(q)})
    s = pd.DataFrame(summary)
    s.to_csv(OUT_SUM, index=False)

    major = d[d.partition.isin(MAJOR)]
    n = len(major); up = int(major.break_side.eq('UP_BREAK').sum()); dn = int(major.break_side.eq('DOWN_BREAK').sum()); no = int(major.break_side.eq('NO_BREAK').sum())
    lines = [
        '# BNB Session-Native Discovery — London M1 Structure — B27EL Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. London clock audit: **Europe/London DST-aware**, pre-range 00:00–08:00 local (96 bars), observation 08:00–13:00 local (60 bars).','',
        'B27EL is structural only: no F85/F15, no entry, no stop, no target selection, no PnL, and no zone-time optimization.','',
        '## Pooled-major London sessions','',
        f'- Complete sessions: **{n}**; UP break **{up} ({pct(up/n)})**; DOWN break **{dn} ({pct(dn/n)})**; NO break **{no} ({pct(no/n)})**.','',
        '| Side | N | Break min med | Any retest | Exactly 1 retest | First retest hold | First retest accept-inside | Direct E10 | Hold-event | Accept-event | E20 | E50 | Opposite boundary |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for side in ('UP_BREAK','DOWN_BREAK'):
        r = s[(s.scope == 'POOLED_MAJOR') & (s.side == side)].iloc[0]
        lines.append(f'| {side} | {int(r.n)} | {num(r.median_break_min)} | {pct(r.retest_rate)} | {pct(r.one_retest_rate)} | {pct(r.hold_first_rate)} | {pct(r.accept_first_rate)} | {pct(r.direct_e10_rate)} | {pct(r.hold_event_rate)} | {pct(r.accept_event_rate)} | {pct(r.e20_rate)} | {pct(r.e50_rate)} | {pct(r.opposite_boundary_rate)} |')

    lines += ['', '## Structural labels','']
    for side in ('UP_BREAK','DOWN_BREAK'):
        q = major[major.break_side.eq(side)]
        a, b = labels(q)
        lines.append(f'- **{side}: {a}; {b}**')

    lines += ['', '## DST stability','', '| Regime | Side | N | Any retest | Direct E10 | Accept-event | E20 | E50 |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for regime in ('GMT','BST'):
        for side in ('UP_BREAK','DOWN_BREAK'):
            r = s[(s.scope == regime) & (s.side == side)].iloc[0]
            lines.append(f'| {regime} | {side} | {int(r.n)} | {pct(r.retest_rate)} | {pct(r.direct_e10_rate)} | {pct(r.accept_event_rate)} | {pct(r.e20_rate)} | {pct(r.e50_rate)} |')

    lines += ['', '**Status: B27EL_BNB_LONDON_NATIVE_STRUCTURE_COMPLETE**','', 'STOP: New York native structure is not executed automatically.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('B27EL_BNB_LONDON_NATIVE_STRUCTURE_COMPLETE\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
