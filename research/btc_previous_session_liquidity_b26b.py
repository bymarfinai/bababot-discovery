#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_PREVIOUS_SESSION_LIQUIDITY_B26B_Result.md'
OUT_SUMMARY = ROOT / 'BTC_PREVIOUS_SESSION_LIQUIDITY_B26B_Summary.csv'
OUT_TRADES = ROOT / 'BTC_PREVIOUS_SESSION_LIQUIDITY_B26B_Trades.csv'

PARTS = b22b.PARTS
NOTIONAL = 500.0
FEE_USD = 0.40
BODY_MIN = 0.60
BAR = pd.Timedelta(minutes=5)

TRANSITIONS = {
    'ASIA_TO_LONDON': {
        'prev_start': (0, 0), 'prev_end': (8, 0),
        'next_start': (8, 0), 'next_end': (13, 30),
    },
    'LONDON_TO_NEWYORK': {
        'prev_start': (8, 0), 'prev_end': (13, 30),
        'next_start': (13, 30), 'next_end': (20, 0),
    },
}


def ts_for_day(day: pd.Timestamp, hhmm: tuple[int, int]) -> pd.Timestamp:
    hh, mm = hhmm
    return pd.Timestamp(day.date(), tz='UTC') + pd.Timedelta(hours=hh, minutes=mm)


def body_ratio(row) -> float:
    rng = float(row.high) - float(row.low)
    return abs(float(row.close) - float(row.open)) / rng if rng > 0 else 0.0


def last_confirmed_swings(q: pd.DataFrame, sweep_pos: int):
    # A centered 3-bar swing at k is causally known only after k+1 completes.
    # For a sweep at s, require k+1 < s, so k <= s-2.
    if sweep_pos < 3:
        return None, None, None, None
    lows = q.low.to_numpy(float)
    highs = q.high.to_numpy(float)
    last_low = last_high = None
    last_low_ts = last_high_ts = None
    for k in range(1, sweep_pos - 1):
        if lows[k] < lows[k - 1] and lows[k] < lows[k + 1]:
            last_low = float(lows[k]); last_low_ts = q.index[k]
        if highs[k] > highs[k - 1] and highs[k] > highs[k + 1]:
            last_high = float(highs[k]); last_high_ts = q.index[k]
    return last_low, last_high, last_low_ts, last_high_ts


def find_candidate(q: pd.DataFrame, prev_hi: float, prev_lo: float, side: str):
    opens = q.open.to_numpy(float)
    highs = q.high.to_numpy(float)
    lows = q.low.to_numpy(float)
    closes = q.close.to_numpy(float)
    idx = q.index

    for s in range(0, len(q) - 2):
        if side == 'SHORT':
            swept = highs[s] > prev_hi and closes[s] < prev_hi
        else:
            swept = lows[s] < prev_lo and closes[s] > prev_lo
        if not swept:
            continue

        sw_low, sw_high, sw_low_ts, sw_high_ts = last_confirmed_swings(q, s)
        bos_level = sw_low if side == 'SHORT' else sw_high
        bos_level_ts = sw_low_ts if side == 'SHORT' else sw_high_ts
        if bos_level is None:
            continue

        bos = None
        for j in range(s + 1, len(q) - 1):
            br = body_ratio(q.iloc[j])
            if side == 'SHORT':
                ok = closes[j] < bos_level and closes[j] < opens[j] and br >= BODY_MIN
            else:
                ok = closes[j] > bos_level and closes[j] > opens[j] and br >= BODY_MIN
            if ok:
                bos = j
                break
        if bos is None:
            continue

        retest = None
        for r in range(bos + 1, len(q) - 1):
            if side == 'SHORT':
                ok = highs[r] >= bos_level and closes[r] < bos_level
            else:
                ok = lows[r] <= bos_level and closes[r] > bos_level
            if ok:
                retest = r
                break
        if retest is None:
            continue

        entry_pos = retest + 1
        if entry_pos >= len(q):
            continue
        entry_px = float(opens[entry_pos])
        entry_ts = idx[entry_pos]

        if side == 'SHORT':
            sweep_extreme = float(np.max(highs[s:bos + 1]))
            stop_px = sweep_extreme
            risk_px = stop_px - entry_px
            if risk_px <= 0:
                continue
            target_px = entry_px - 2.0 * risk_px
        else:
            sweep_extreme = float(np.min(lows[s:bos + 1]))
            stop_px = sweep_extreme
            risk_px = entry_px - stop_px
            if risk_px <= 0:
                continue
            target_px = entry_px + 2.0 * risk_px

        return {
            'side': side,
            'sweep_ts': idx[s],
            'bos_ts': idx[bos],
            'bos_level': float(bos_level),
            'bos_level_ts': bos_level_ts,
            'retest_ts': idx[retest],
            'entry_ts': entry_ts,
            'entry_px': entry_px,
            'sweep_extreme': sweep_extreme,
            'stop_px': float(stop_px),
            'target_px': float(target_px),
            'risk_pct': float(risk_px / entry_px),
        }
    return None


def resolve(x5: pd.DataFrame, cand: dict, session_end: pd.Timestamp):
    entry_ts = cand['entry_ts']
    entry_px = float(cand['entry_px'])
    stop_px = float(cand['stop_px'])
    target_px = float(cand['target_px'])
    side = cand['side']
    q = x5[(x5.index >= entry_ts) & (x5.index < session_end)]

    for ts, row in q.iterrows():
        if side == 'LONG':
            tp_hit = float(row.high) >= target_px
            sl_hit = float(row.low) <= stop_px
        else:
            tp_hit = float(row.low) <= target_px
            sl_hit = float(row.high) >= stop_px
        if tp_hit and sl_hit:
            exit_px = stop_px; reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp_hit:
            exit_px = target_px; reason = 'TP_2R'
        elif sl_hit:
            exit_px = stop_px; reason = 'SL'
        else:
            continue
        gross_ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return reason, ts, float(exit_px), float(gross_ret)

    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5):
        return None
    ts = x5.index[pos]
    exit_px = float(x5.iloc[pos].open)
    gross_ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
    return 'TIME_EXIT_SESSION_END', ts, exit_px, float(gross_ret)


def simulate_day(x5: pd.DataFrame, transition: str, cfg: dict, day: pd.Timestamp,
                 partition: str, part_start: pd.Timestamp, part_end: pd.Timestamp):
    prev_start = ts_for_day(day, cfg['prev_start'])
    prev_end = ts_for_day(day, cfg['prev_end'])
    next_start = ts_for_day(day, cfg['next_start'])
    next_end = ts_for_day(day, cfg['next_end'])
    if prev_start < part_start or next_end > part_end:
        return None

    prev = x5[(x5.index >= prev_start) & (x5.index < prev_end)]
    q = x5[(x5.index >= next_start) & (x5.index < next_end)]
    exp_prev = int((prev_end - prev_start) / BAR)
    exp_next = int((next_end - next_start) / BAR)
    if len(prev) != exp_prev or len(q) != exp_next:
        return None

    prev_hi = float(prev.high.max())
    prev_lo = float(prev.low.min())
    candidates = []
    for side in ('LONG', 'SHORT'):
        c = find_candidate(q, prev_hi, prev_lo, side)
        if c is not None:
            candidates.append(c)
    if not candidates:
        return None
    cand = sorted(candidates, key=lambda z: z['entry_ts'])[0]
    solved = resolve(x5, cand, next_end)
    if solved is None:
        return None
    reason, exit_ts, exit_px, gross_ret = solved
    gross_pnl = gross_ret * NOTIONAL
    net_pnl = gross_pnl - FEE_USD
    return {
        'partition': partition,
        'transition': transition,
        'date_utc': str(day.date()),
        'previous_session_high': prev_hi,
        'previous_session_low': prev_lo,
        **cand,
        'exit_reason': reason,
        'exit_ts': exit_ts,
        'exit_px': exit_px,
        'gross_return': gross_ret,
        'gross_pnl_usd': gross_pnl,
        'net_pnl_usd': net_pnl,
        'hold_minutes': float((exit_ts - cand['entry_ts']) / pd.Timedelta(minutes=1)),
    }


def pf(vals: pd.Series):
    v = pd.to_numeric(vals, errors='coerce').dropna()
    pos = float(v[v > 0].sum()); neg = float(-v[v < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def summarize(g: pd.DataFrame):
    if len(g) == 0:
        return {'n': 0, 'wins': 0, 'losses': 0, 'wr': np.nan, 'tp_rate': np.nan,
                'net_pf': np.nan, 'net_expectancy_usd': np.nan, 'total_net_usd': np.nan,
                'median_risk_pct': np.nan, 'median_hold_min': np.nan,
                'time_exit_rate': np.nan, 'samebar_rate': np.nan}
    net = g.net_pnl_usd.astype(float)
    return {
        'n': int(len(g)),
        'wins': int((net > 0).sum()),
        'losses': int((net <= 0).sum()),
        'wr': float((net > 0).mean()),
        'tp_rate': float((g.exit_reason == 'TP_2R').mean()),
        'net_pf': float(pf(net)),
        'net_expectancy_usd': float(net.mean()),
        'total_net_usd': float(net.sum()),
        'median_risk_pct': float(g.risk_pct.median()),
        'median_hold_min': float(g.hold_minutes.median()),
        'time_exit_rate': float((g.exit_reason == 'TIME_EXIT_SESSION_END').mean()),
        'samebar_rate': float((g.exit_reason == 'SL_SAME_5M_CONSERVATIVE').mean()),
    }


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    rows = []
    for part, (start, end) in PARTS.items():
        first_day = start.normalize()
        last_day = (end - pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first_day, last_day, freq='D', tz='UTC'):
            if day.weekday() >= 5:
                continue
            for transition, cfg in TRANSITIONS.items():
                r = simulate_day(x5, transition, cfg, day, part, start, end)
                if r is not None:
                    rows.append(r)

    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for transition in TRANSITIONS:
        for part in PARTS:
            if len(trades):
                g = trades[(trades.transition == transition) & (trades.partition == part)]
            else:
                g = pd.DataFrame()
            sums.append({'transition': transition, 'partition': part, **summarize(g)})
    s = pd.DataFrame(sums)

    major = ('external', 'development', 'reference_validation')
    verdicts = {}
    for transition in TRANSITIONS:
        z = s[(s.transition == transition) & s.partition.isin(major)]
        passed = bool(len(z) == 3 and (z.n >= 30).all() and
                      (z.net_expectancy_usd > 0).all() and (z.net_pf >= 1.20).all())
        verdicts[transition] = passed
    s['repeatable_pass'] = [verdicts[r.transition] for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUMMARY, index=False)

    md = [
        '# BTC Previous-Session Liquidity B26B — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Frozen sequence: completed previous-session HIGH/LOW -> next-session sweep and reclaim -> causal fractal ChoCH/BOS with displacement -> structure retest -> next-5m-open entry -> stop beyond sweep extreme -> TP 2R; otherwise time exit at active-session end. Weekdays only.', '',
        'Session windows are fixed UTC: Asia 00:00-08:00, London 08:00-13:30, New York 13:30-20:00.', '',
        '| Transition | Partition | N | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Median risk | Median hold min | Time exit | Same-5m ambiguity |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in s.itertuples(index=False):
        md.append(
            f'| {r.transition} | {r.partition} | {r.n} | {r.wins} | {r.losses} | {pct(r.wr)} | '
            f'{pct(r.tp_rate)} | {num(r.net_pf)} | ${num(r.net_expectancy_usd)} | ${num(r.total_net_usd)} | '
            f'{pct(r.median_risk_pct)} | {num(r.median_hold_min,1)} | {pct(r.time_exit_rate)} | {pct(r.samebar_rate)} |'
        )
    md += ['', '## Frozen repeatability verdict', '']
    for transition in TRANSITIONS:
        md.append(f'- {transition}: **{"PASS" if verdicts[transition] else "FAIL"}**')
    overall = any(verdicts.values())
    md += ['', f'**B26B overall: {"PASS" if overall else "FAIL"}.**', '',
           'Gate requires the same transition to have >=30 trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
