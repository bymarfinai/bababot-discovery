#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_SESSION_OPEN_TRAP_B26A_Result.md'
OUT_SUMMARY = ROOT / 'BTC_SESSION_OPEN_TRAP_B26A_Summary.csv'
OUT_TRADES = ROOT / 'BTC_SESSION_OPEN_TRAP_B26A_Trades.csv'

PARTS = b22b.PARTS
NOTIONAL = 500.0
FEE_USD = 0.40
BAR = pd.Timedelta(minutes=5)
OR_LEN = pd.Timedelta(minutes=15)
SETUP_WINDOW = pd.Timedelta(minutes=75)
EXIT_WINDOW = pd.Timedelta(hours=4)
BODY_MIN = 0.60

SESSIONS = {
    'NYSE_0930': ('America/New_York', 9, 30),
    'LONDON_0800': ('Europe/London', 8, 0),
    'NSE_0915': ('Asia/Kolkata', 9, 15),
}
VARIANTS = ('V1_STRUCTURE_RETEST', 'V2_FVG_RETEST')


def body_ratio(row) -> float:
    rng = float(row.high) - float(row.low)
    return abs(float(row.close) - float(row.open)) / rng if rng > 0 else 0.0


def session_opens(start: pd.Timestamp, end: pd.Timestamp, tz_name: str, hh: int, mm: int):
    tz = ZoneInfo(tz_name)
    local_start = start.tz_convert(tz).date()
    local_end = (end - pd.Timedelta(seconds=1)).tz_convert(tz).date()
    for d in pd.date_range(local_start, local_end, freq='D'):
        if d.weekday() >= 5:
            continue
        naive = pd.Timestamp(d.date()) + pd.Timedelta(hours=hh, minutes=mm)
        yield naive.tz_localize(tz).tz_convert('UTC')


def last_confirmed_swings(q: pd.DataFrame, sweep_pos: int):
    # A 3-bar fractal centered at k is known only after k+1 completes.
    # For a sweep at sweep_pos, k+1 must be strictly before the sweep bar.
    last_low = None
    last_high = None
    last_low_ts = None
    last_high_ts = None
    if sweep_pos < 3:
        return last_low, last_high, last_low_ts, last_high_ts
    lows = q.low.to_numpy(float)
    highs = q.high.to_numpy(float)
    for k in range(1, sweep_pos - 1):
        if lows[k] < lows[k - 1] and lows[k] < lows[k + 1]:
            last_low = float(lows[k]); last_low_ts = q.index[k]
        if highs[k] > highs[k - 1] and highs[k] > highs[k + 1]:
            last_high = float(highs[k]); last_high_ts = q.index[k]
    return last_low, last_high, last_low_ts, last_high_ts


def find_side_candidate(q: pd.DataFrame, or_hi: float, or_lo: float, deadline: pd.Timestamp,
                        side: str, variant: str):
    opens = q.open.to_numpy(float)
    highs = q.high.to_numpy(float)
    lows = q.low.to_numpy(float)
    closes = q.close.to_numpy(float)
    idx = q.index

    # OR occupies positions 0,1,2. Search after it.
    for s in range(3, len(q) - 2):
        if idx[s] >= deadline:
            break
        if side == 'SHORT':
            swept = highs[s] > or_hi and closes[s] < or_hi
        else:
            swept = lows[s] < or_lo and closes[s] > or_lo
        if not swept:
            continue

        sw_low, sw_high, sw_low_ts, sw_high_ts = last_confirmed_swings(q, s)
        bos_level = sw_low if side == 'SHORT' else sw_high
        bos_level_ts = sw_low_ts if side == 'SHORT' else sw_high_ts
        if bos_level is None:
            continue

        bos = None
        for j in range(s + 1, len(q) - 1):
            if idx[j] >= deadline:
                break
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

        fvg_mid = None
        if variant == 'V2_FVG_RETEST':
            if bos < 2:
                continue
            if side == 'SHORT':
                # Bearish FVG: current high is below low two bars earlier.
                if not (highs[bos] < lows[bos - 2]):
                    continue
                fvg_mid = (highs[bos] + lows[bos - 2]) / 2.0
            else:
                # Bullish FVG: current low is above high two bars earlier.
                if not (lows[bos] > highs[bos - 2]):
                    continue
                fvg_mid = (lows[bos] + highs[bos - 2]) / 2.0

        retest = None
        for r in range(bos + 1, len(q) - 1):
            # Retest candle must complete within the setup window.
            if idx[r] + BAR > deadline:
                break
            if variant == 'V1_STRUCTURE_RETEST':
                if side == 'SHORT':
                    ok = highs[r] >= bos_level and closes[r] < bos_level
                else:
                    ok = lows[r] <= bos_level and closes[r] > bos_level
            else:
                if side == 'SHORT':
                    ok = highs[r] >= fvg_mid and closes[r] < fvg_mid
                else:
                    ok = lows[r] <= fvg_mid and closes[r] > fvg_mid
            if ok:
                retest = r
                break
        if retest is None:
            continue

        entry_pos = retest + 1
        if entry_pos >= len(q):
            continue
        entry_ts = idx[entry_pos]
        entry_px = float(opens[entry_pos])
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
            'sweep_extreme': sweep_extreme,
            'bos_ts': idx[bos],
            'bos_level': float(bos_level),
            'bos_level_ts': bos_level_ts,
            'fvg_mid': np.nan if fvg_mid is None else float(fvg_mid),
            'retest_ts': idx[retest],
            'entry_ts': entry_ts,
            'entry_px': entry_px,
            'stop_px': float(stop_px),
            'target_px': float(target_px),
            'risk_pct': float(risk_px / entry_px),
        }
    return None


def resolve(x5: pd.DataFrame, cand: dict, horizon: pd.Timestamp):
    entry_ts = cand['entry_ts']; entry_px = cand['entry_px']
    stop_px = cand['stop_px']; target_px = cand['target_px']; side = cand['side']
    q = x5[(x5.index >= entry_ts) & (x5.index < horizon)]
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

    # Frozen time exit at first open at/after 4h boundary.
    pos = int(x5.index.searchsorted(horizon, side='left'))
    if pos >= len(x5):
        return None
    ts = x5.index[pos]; exit_px = float(x5.iloc[pos].open)
    gross_ret = (exit_px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
    return 'TIME_EXIT_4H', ts, exit_px, float(gross_ret)


def simulate_session(x5: pd.DataFrame, session_name: str, open_ts: pd.Timestamp, variant: str,
                     partition: str, part_end: pd.Timestamp):
    or_end = open_ts + OR_LEN
    deadline = open_ts + SETUP_WINDOW
    horizon = open_ts + EXIT_WINDOW
    if horizon >= part_end:
        return None
    q = x5[(x5.index >= open_ts) & (x5.index < deadline)]
    # Need complete contiguous OR and enough post-OR data.
    if len(q) < 8:
        return None
    orq = q[(q.index >= open_ts) & (q.index < or_end)]
    if len(orq) != 3:
        return None
    if not all((orq.index[i] - orq.index[0]) == i * BAR for i in range(3)):
        return None
    or_hi = float(orq.high.max()); or_lo = float(orq.low.min())

    candidates = []
    for side in ('LONG', 'SHORT'):
        c = find_side_candidate(q, or_hi, or_lo, deadline, side, variant)
        if c is not None:
            candidates.append(c)
    if not candidates:
        return None
    cand = sorted(candidates, key=lambda z: z['entry_ts'])[0]
    solved = resolve(x5, cand, horizon)
    if solved is None:
        return None
    reason, exit_ts, exit_px, gross_ret = solved
    gross_pnl = gross_ret * NOTIONAL
    net_pnl = gross_pnl - FEE_USD
    return {
        'partition': partition,
        'session': session_name,
        'variant': variant,
        'session_open_ts': open_ts,
        'or_high': or_hi,
        'or_low': or_lo,
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
                'median_risk_pct': np.nan, 'median_hold_min': np.nan, 'time_exit_rate': np.nan,
                'samebar_rate': np.nan}
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
        'time_exit_rate': float((g.exit_reason == 'TIME_EXIT_4H').mean()),
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
        for session_name, (tz, hh, mm) in SESSIONS.items():
            for open_ts in session_opens(start, end, tz, hh, mm):
                if open_ts < start or open_ts >= end:
                    continue
                for variant in VARIANTS:
                    r = simulate_session(x5, session_name, open_ts, variant, part, end)
                    if r is not None:
                        rows.append(r)
    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for session_name in SESSIONS:
        for variant in VARIANTS:
            for part in PARTS:
                g = trades[(trades.session == session_name) & (trades.variant == variant) & (trades.partition == part)] if len(trades) else pd.DataFrame()
                sums.append({'session': session_name, 'variant': variant, 'partition': part, **summarize(g)})
    s = pd.DataFrame(sums)

    major = ('external', 'development', 'reference_validation')
    verdicts = {}
    for session_name in SESSIONS:
        for variant in VARIANTS:
            z = s[(s.session == session_name) & (s.variant == variant) & s.partition.isin(major)]
            passed = bool(len(z) == 3 and (z.n >= 30).all() and (z.net_expectancy_usd > 0).all() and (z.net_pf >= 1.20).all())
            verdicts[(session_name, variant)] = passed
    s['repeatable_pass'] = [verdicts[(r.session, r.variant)] for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUMMARY, index=False)

    md = [
        '# BTC Session Open Trap B26A — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Frozen sequence: 15m opening range -> price-defined sweep and reclaim -> causal fractal ChoCH/BOS with displacement -> retest -> next-5m-open entry -> stop beyond sweep extreme -> TP 2R. Weekdays only.', '',
        'V1_STRUCTURE_RETEST retests the broken structure level. V2_FVG_RETEST additionally requires a 3-candle FVG on the BOS candle and retests its midpoint.', '',
        '| Session | Variant | Partition | N | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Median risk | Median hold min | Time exit | Same-5m ambiguity |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for r in s.itertuples(index=False):
        md.append(f'| {r.session} | {r.variant} | {r.partition} | {r.n} | {r.wins} | {r.losses} | {pct(r.wr)} | {pct(r.tp_rate)} | {num(r.net_pf)} | ${num(r.net_expectancy_usd)} | ${num(r.total_net_usd)} | {pct(r.median_risk_pct)} | {num(r.median_hold_min,1)} | {pct(r.time_exit_rate)} | {pct(r.samebar_rate)} |')
    md += ['', '## Frozen repeatability verdict', '']
    for (session_name, variant), passed in verdicts.items():
        md.append(f'- {session_name} + {variant}: **{"PASS" if passed else "FAIL"}**')
    overall = any(verdicts.values())
    md += ['', f'**B26A overall: {"PASS" if overall else "FAIL"}.**', '',
           'Gate requires the same session+variant to have >=30 trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
