#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_crossover_cycle_entry_b23e as b23e

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_4H_REGIME_15M_EMA_1TO1_B25A_Result.md'
OUT_SUMMARY = ROOT / 'BTC_4H_REGIME_15M_EMA_1TO1_B25A_Summary.csv'
OUT_TRADES = ROOT / 'BTC_4H_REGIME_15M_EMA_1TO1_B25A_Trades.csv'

PARTS = b22b.PARTS
TP = 0.01
SL = 0.01
NOTIONAL = 500.0
FEE_USD = 0.40
BAR15 = pd.Timedelta(minutes=15)
BAR5 = pd.Timedelta(minutes=5)
BAR4H = pd.Timedelta(hours=4)


def pct(v):
    if v is None or pd.isna(v):
        return '-'
    return f'{100.0 * float(v):.2f}%'


def num(v, d=2):
    if v is None or pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{d}f}'


def build_inputs(x5: pd.DataFrame):
    z15 = b23e.add_cycles(b22b.enrich(b22b.resample_ohlc(x5, '15min')))
    h4 = b22b.resample_ohlc(x5, '4h')
    h4_av = b21._bull_available(h4, BAR4H)
    return z15, h4_av


def regime_on_at(h4_av: pd.DataFrame, when: pd.Timestamp) -> bool:
    pos = int(h4_av.index.searchsorted(when, side='right')) - 1
    if pos < 0:
        return False
    return bool(h4_av.iloc[pos].bull)


def resolve_barriers(x5: pd.DataFrame, entry_ts: pd.Timestamp, entry_px: float, end: pd.Timestamp):
    tp_px = entry_px * (1.0 + TP)
    sl_px = entry_px * (1.0 - SL)
    q = x5[(x5.index >= entry_ts) & (x5.index < end)]
    if q.empty:
        return None

    for ts, row in q.iterrows():
        tp_hit = float(row.high) >= tp_px
        sl_hit = float(row.low) <= sl_px
        if tp_hit and sl_hit:
            return {
                'exit_reason': 'SL_SAME_5M_BAR_CONSERVATIVE',
                'exit_ts': ts,
                'exit_px': sl_px,
                'gross_return': -SL,
                'hold_minutes': float((ts - entry_ts) / pd.Timedelta(minutes=1)),
            }
        if tp_hit:
            return {
                'exit_reason': 'TP',
                'exit_ts': ts,
                'exit_px': tp_px,
                'gross_return': TP,
                'hold_minutes': float((ts - entry_ts) / pd.Timedelta(minutes=1)),
            }
        if sl_hit:
            return {
                'exit_reason': 'SL',
                'exit_ts': ts,
                'exit_px': sl_px,
                'gross_return': -SL,
                'hold_minutes': float((ts - entry_ts) / pd.Timedelta(minutes=1)),
            }
    return None


def simulate_partition(z15: pd.DataFrame, h4_av: pd.DataFrame, x5: pd.DataFrame,
                       part: str, start: pd.Timestamp, end: pd.Timestamp):
    idx = z15.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 10:
        return []

    opens = z15.open.to_numpy(float)
    closes = z15.close.to_numpy(float)
    ema20 = z15.ema20.to_numpy(float)
    ema50 = z15.ema50.to_numpy(float)
    bull = z15.bull_cross.fillna(False).to_numpy(bool)
    bear = z15.bear_cross.fillna(False).to_numpy(bool)

    rows = []
    cursor = max(lo, 1)
    final_i = hi - 1

    while cursor < final_i:
        cross_i = None
        for i in range(cursor, final_i):
            if bull[i]:
                cross_i = i
                break
        if cross_i is None:
            break

        bear_i = None
        for j in range(cross_i + 1, hi):
            if bear[j]:
                bear_i = j
                break
        cycle_end = bear_i if bear_i is not None else hi

        cross_complete = idx[cross_i] + BAR15
        regime_at_cross = regime_on_at(h4_av, cross_complete)

        signal_i = None
        if regime_at_cross:
            for j in range(cross_i + 1, cycle_end):
                if not (ema20[j] > ema50[j]):
                    continue
                if closes[j] > opens[j]:
                    signal_i = j
                    break

        if signal_i is not None:
            signal_complete = idx[signal_i] + BAR15
            regime_at_signal = regime_on_at(h4_av, signal_complete)
            entry_i = signal_i + 1
            if regime_at_signal and entry_i < cycle_end and entry_i < hi:
                entry_ts = idx[entry_i]
                entry_px = float(opens[entry_i])
                resolved = resolve_barriers(x5, entry_ts, entry_px, end)
                base = {
                    'partition': part,
                    'bull_cross_ts': idx[cross_i],
                    'signal_ts': idx[signal_i],
                    'entry_ts': entry_ts,
                    'entry_px': entry_px,
                    'regime_at_cross': regime_at_cross,
                    'regime_at_signal': regime_at_signal,
                }
                if resolved is None:
                    rows.append({
                        **base,
                        'resolved': False,
                        'exit_reason': 'PARTITION_CENSORED',
                        'exit_ts': pd.NaT,
                        'exit_px': np.nan,
                        'gross_return': np.nan,
                        'gross_pnl_usd': np.nan,
                        'net_pnl_usd': np.nan,
                        'hold_minutes': np.nan,
                    })
                else:
                    gross_pnl = float(resolved['gross_return']) * NOTIONAL
                    rows.append({
                        **base,
                        'resolved': True,
                        **resolved,
                        'gross_pnl_usd': gross_pnl,
                        'net_pnl_usd': gross_pnl - FEE_USD,
                    })

        cursor = (bear_i + 1) if bear_i is not None else hi

    return rows


def summarize(g: pd.DataFrame):
    entered = len(g)
    if entered == 0:
        return {
            'entered': 0, 'resolved': 0, 'censored': 0, 'wins': 0, 'losses': 0,
            'wr': np.nan, 'gross_pf': np.nan, 'gross_expectancy_pct': np.nan,
            'net_expectancy_usd': np.nan, 'total_net_usd': np.nan,
            'median_hold_min': np.nan, 'same_bar_ambiguous_rate': np.nan,
        }
    r = g[g.resolved.astype(bool)].copy()
    wins = int((r.exit_reason == 'TP').sum())
    losses = int(len(r) - wins)
    wr = wins / len(r) if len(r) else np.nan
    gross_pf = wins / losses if losses > 0 else (float('inf') if wins > 0 else np.nan)
    gross_exp = float(r.gross_return.mean()) if len(r) else np.nan
    net_exp = float(r.net_pnl_usd.mean()) if len(r) else np.nan
    samebar = float((r.exit_reason == 'SL_SAME_5M_BAR_CONSERVATIVE').mean()) if len(r) else np.nan
    return {
        'entered': int(entered),
        'resolved': int(len(r)),
        'censored': int(entered - len(r)),
        'wins': wins,
        'losses': losses,
        'wr': float(wr) if pd.notna(wr) else np.nan,
        'gross_pf': float(gross_pf) if pd.notna(gross_pf) else np.nan,
        'gross_expectancy_pct': gross_exp,
        'net_expectancy_usd': net_exp,
        'total_net_usd': float(r.net_pnl_usd.sum()) if len(r) else np.nan,
        'median_hold_min': float(r.hold_minutes.median()) if len(r) else np.nan,
        'same_bar_ambiguous_rate': samebar,
    }


def main():
    x5, coverage = b21.load5()
    z15, h4_av = build_inputs(x5)

    rows = []
    for part, (start, end) in PARTS.items():
        rows.extend(simulate_partition(z15, h4_av, x5, part, start, end))

    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for part in PARTS:
        g = trades[trades.partition == part] if len(trades) else pd.DataFrame()
        sums.append({'partition': part, **summarize(g)})
    s = pd.DataFrame(sums)

    major = s[s.partition.isin(['external', 'development', 'reference_validation'])]
    gate = bool(
        len(major) == 3
        and (major.resolved >= 50).all()
        and (major.wr >= 0.55).all()
        and (major.net_expectancy_usd > 0).all()
    )
    s['gate_partition'] = (
        (s.resolved >= 50) & (s.wr >= 0.55) & (s.net_expectancy_usd > 0)
    )
    s.to_csv(OUT_SUMMARY, index=False)

    md = [
        '# BTC 4H Regime + 15m EMA 1:1 B25A — Result',
        '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**',
        '',
        'Frozen setup: 4H B21 bull regime already ON -> 15m EMA20/50 bullish cross -> first later green 15m candle while regime remains ON -> entry next 15m open -> TP +1% / SL -1%.',
        '',
        '5m bars are used only to determine which fixed 1% barrier is touched first. If both barriers occur inside one 5m bar, the trade is counted conservatively as SL.',
        '',
        'Illustration: $10 margin x 50x = $500 notional. Gross TP/SL = +/-$5. Illustrative round-trip fee = $0.40.',
        '',
        '| Partition | Entered | Resolved | W | L | WR | Gross PF | Gross expectancy | Net expectancy/trade | Total net | Median hold min | Same-5m ambiguous | Partition gate |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    for r in s.itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.entered} | {r.resolved} | {r.wins} | {r.losses} | '
            f'{pct(r.wr)} | {num(r.gross_pf)} | {pct(r.gross_expectancy_pct)} | '
            f'${num(r.net_expectancy_usd)} | ${num(r.total_net_usd)} | {num(r.median_hold_min,1)} | '
            f'{pct(r.same_bar_ambiguous_rate)} | {"PASS" if r.gate_partition else "FAIL"} |'
        )
    md += [
        '',
        '## Frozen overall gate',
        '',
        f'- B25A_REPEATABLE_1TO1_EDGE: **{"PASS" if gate else "FAIL"}**',
        '',
        'The overall gate requires external, development, and reference_validation each to have >=50 resolved trades, WR >=55%, and positive fee-sensitive expectancy.',
        '',
        'Research only; live BBC unchanged.',
    ]
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
