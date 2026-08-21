#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_dynamic_condition_engine_b23d as b23d

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_CONTINUATION_AFTER_CROSS_B23F_Result.md'
OUT_SUMMARY = ROOT / 'BTC_CONTINUATION_AFTER_CROSS_B23F_Summary.csv'
OUT_TRADES = ROOT / 'BTC_CONTINUATION_AFTER_CROSS_B23F_Trades.csv'
OUT_CYCLES = ROOT / 'BTC_CONTINUATION_AFTER_CROSS_B23F_Cycles.csv'

PARTS = b22b.PARTS
TFS = {
    '5m': ('5min', 5),
    '15m': ('15min', 15),
    '1h': ('1h', 60),
    '4h': ('4h', 240),
}
NOTIONAL = 500.0
FEE_USD = 0.40


def enrich_cycle(frame: pd.DataFrame) -> pd.DataFrame:
    x = b23d.classify(frame)
    x['bull_cross'] = ((x.ema20 > x.ema50) & (x.ema20.shift(1) <= x.ema50.shift(1))).fillna(False)
    x['bear_cross'] = ((x.ema20 < x.ema50) & (x.ema20.shift(1) >= x.ema50.shift(1))).fillna(False)
    x['continuation'] = (
        (x.close > x.open)
        & (x.close > x.close.shift(1))
        & (x.close > x.ema20)
        & (x.ema20 > x.ema50)
        & (x.ema20 > x.ema20.shift(1))
        & (x.ema50 >= x.ema50.shift(1))
        & (x.spread > x.spread.shift(1))
    ).fillna(False)
    return x


def simulate(z: pd.DataFrame, tf: str, minutes: int, part: str, start: pd.Timestamp, end: pd.Timestamp):
    idx = z.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 10:
        return [], []

    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)
    state = z.state.to_numpy(object)
    bull = z.bull_cross.to_numpy(bool)
    bear = z.bear_cross.to_numpy(bool)
    cont = z.continuation.to_numpy(bool)

    trades = []
    cycles = []
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

        signal_i = None
        for j in range(cross_i + 1, cycle_end):
            if cont[j]:
                signal_i = j
                break

        cycle_row = {
            'partition': part,
            'timeframe': tf,
            'bull_cross_ts': idx[cross_i],
            'bear_cross_ts': pd.NaT if bear_i is None else idx[bear_i],
            'continuation_ts': pd.NaT if signal_i is None else idx[signal_i],
            'bars_cross_to_continuation': np.nan if signal_i is None else int(signal_i - cross_i),
            'produced_entry': bool(signal_i is not None and signal_i + 1 < cycle_end and signal_i + 1 < hi),
        }
        cycles.append(cycle_row)

        if cycle_row['produced_entry']:
            entry_i = signal_i + 1
            entry_px = float(opens[entry_i])
            exit_i = None
            exit_reason = None
            monitor_last = min(cycle_end, final_i)

            for j in range(entry_i, monitor_last + 1):
                st = str(state[j])
                if st in ('STRONG_BULL', 'HEALTHY_BULL', 'TRANSITION'):
                    continue
                if st == 'DETERIORATING':
                    if j + 1 < hi:
                        exit_i = j + 1
                        exit_reason = 'DYNAMIC_DETERIORATION_CUT'
                    break
                if st == 'REVERSAL':
                    if j + 1 < hi:
                        exit_i = j + 1
                        exit_reason = 'REVERSAL_CUT'
                    break

            if exit_i is None:
                if bear_i is not None and bear_i + 1 < hi:
                    exit_i = bear_i + 1
                    exit_reason = 'BEAR_CROSS_CUT'
                else:
                    exit_i = final_i
                    exit_reason = 'PARTITION_FORCE_CLOSE'

            if exit_i > entry_i:
                exit_px = float(opens[exit_i])
                path_hi = float(np.nanmax(highs[entry_i:exit_i]))
                path_lo = float(np.nanmin(lows[entry_i:exit_i]))
                ret = exit_px / entry_px - 1.0
                trades.append({
                    'partition': part,
                    'timeframe': tf,
                    'bull_cross_ts': idx[cross_i],
                    'signal_ts': idx[signal_i],
                    'entry_ts': idx[entry_i],
                    'exit_ts': idx[exit_i],
                    'bars_cross_to_signal': int(signal_i - cross_i),
                    'entry_px': entry_px,
                    'exit_px': exit_px,
                    'return': ret,
                    'mfe': path_hi / entry_px - 1.0,
                    'mae': path_lo / entry_px - 1.0,
                    'bars_held': int(exit_i - entry_i),
                    'hold_minutes': int((exit_i - entry_i) * minutes),
                    'gross_pnl_usd': ret * NOTIONAL,
                    'fee_sensitive_pnl_usd': ret * NOTIONAL - FEE_USD,
                    'exit_reason': exit_reason,
                })

        cursor = (bear_i + 1) if bear_i is not None else hi

    return trades, cycles


def pf(vals) -> float:
    a = pd.Series(vals, dtype=float)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def metrics(g: pd.DataFrame, cg: pd.DataFrame) -> dict:
    r = g['return'].astype(float) if len(g) else pd.Series(dtype=float)
    w = r[r > 0]
    l = r[r <= 0]
    mae = g.mae.astype(float) if len(g) else pd.Series(dtype=float)
    net = g.fee_sensitive_pnl_usd.astype(float) if len(g) else pd.Series(dtype=float)
    produced = cg.produced_entry.astype(bool) if len(cg) else pd.Series(dtype=bool)
    triggered_cycles = cg.loc[produced, 'bars_cross_to_continuation'].dropna() if len(cg) else pd.Series(dtype=float)
    return {
        'armed_cycles': int(len(cg)),
        'entry_cycles': int(produced.sum()) if len(cg) else 0,
        'no_trade_rate': float((~produced).mean()) if len(cg) else np.nan,
        'median_bars_cross_to_signal': float(triggered_cycles.median()) if len(triggered_cycles) else np.nan,
        'n': int(len(g)),
        'wr': float((r > 0).mean()) if len(r) else np.nan,
        'pf': float(pf(r)) if len(r) else np.nan,
        'mean_ret': float(r.mean()) if len(r) else np.nan,
        'median_ret': float(r.median()) if len(r) else np.nan,
        'median_winner': float(w.median()) if len(w) else np.nan,
        'median_loser': float(l.median()) if len(l) else np.nan,
        'median_mfe': float(g.mfe.median()) if len(g) else np.nan,
        'median_mae': float(mae.median()) if len(mae) else np.nan,
        'p10_mae': float(mae.quantile(.10)) if len(mae) else np.nan,
        'median_hold_minutes': float(g.hold_minutes.median()) if len(g) else np.nan,
        'mean_gross_usd': float(g.gross_pnl_usd.mean()) if len(g) else np.nan,
        'fee_wr': float((net > 0).mean()) if len(net) else np.nan,
        'fee_pf': float(pf(net)) if len(net) else np.nan,
        'mean_fee_usd': float(net.mean()) if len(net) else np.nan,
        'mae_le_0p5': float((mae <= -.005).mean()) if len(mae) else np.nan,
        'mae_le_1p0': float((mae <= -.010).mean()) if len(mae) else np.nan,
        'mae_le_1p5': float((mae <= -.015).mean()) if len(mae) else np.nan,
        'mae_le_1p8': float((mae <= -.018).mean()) if len(mae) else np.nan,
    }


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    frames = {tf: enrich_cycle(b22b.enrich(b22b.resample_ohlc(x5, rule))) for tf, (rule, _) in TFS.items()}

    all_trades = []
    all_cycles = []
    for tf, (_, minutes) in TFS.items():
        for part, (start, end) in PARTS.items():
            tr, cy = simulate(frames[tf], tf, minutes, part, start, end)
            all_trades.extend(tr)
            all_cycles.extend(cy)

    trades = pd.DataFrame(all_trades)
    cycles = pd.DataFrame(all_cycles)
    trades.to_csv(OUT_TRADES, index=False)
    cycles.to_csv(OUT_CYCLES, index=False)

    sums = []
    for part in PARTS:
        for tf in TFS:
            g = trades[(trades.partition == part) & (trades.timeframe == tf)] if len(trades) else pd.DataFrame()
            cg = cycles[(cycles.partition == part) & (cycles.timeframe == tf)] if len(cycles) else pd.DataFrame()
            sums.append({'partition': part, 'timeframe': tf, **metrics(g, cg)})
    s = pd.DataFrame(sums)
    s.to_csv(OUT_SUMMARY, index=False)

    md = [
        '# BTC Continuation-After-Cross Entry B23F — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Bullish cross only ARMS the setup. A red candle after the cross does not create an entry. Entry occurs only after the first same-timeframe bullish continuation candle satisfying the frozen seven-condition trigger, then executes at the next same-timeframe open.', '',
        f'Position model: **$10 margin × 50x = ${NOTIONAL:.0f} notional**. Fee sensitivity subtracts illustrative **$0.40/trade**.', '',
        '| Partition | TF | Armed cycles | Entry cycles | No-trade | Cross→signal bars | N | WR | PF | Mean ret | Median winner | Median loser | Median MFE | Median MAE | P10 MAE | Mean $ | Fee WR | Fee PF | <=-0.5 MAE | <=-1.0 | <=-1.5 | <=-1.8 | Med hold min |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    order = {'5m': 0, '15m': 1, '1h': 2, '4h': 3}
    s['ord'] = s.timeframe.map(order)
    for r in s.sort_values(['partition', 'ord']).itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.timeframe} | {r.armed_cycles} | {r.entry_cycles} | {pct(r.no_trade_rate)} | {num(r.median_bars_cross_to_signal,1)} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.mean_ret)} | {pct(r.median_winner)} | {pct(r.median_loser)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {pct(r.p10_mae)} | ${num(r.mean_gross_usd)} | {pct(r.fee_wr)} | {num(r.fee_pf)} | {pct(r.mae_le_0p5)} | {pct(r.mae_le_1p0)} | {pct(r.mae_le_1p5)} | {pct(r.mae_le_1p8)} | {num(r.median_hold_minutes,1)} |'
        )

    md += ['', '## Frozen gates', '']
    for tf in ['5m', '15m', '1h', '4h']:
        checks = []
        highs = []
        nmin = {'5m': 30, '15m': 30, '1h': 20, '4h': 10}[tf]
        for part in ['external', 'reference_validation']:
            r = s[(s.partition == part) & (s.timeframe == tf)].iloc[0]
            base = (
                int(r.n) >= nmin
                and pd.notna(r.wr) and float(r.wr) >= .80
                and pd.notna(r.pf) and float(r.pf) >= 1.20
                and pd.notna(r.median_loser) and float(r.median_loser) > -.003
                and pd.notna(r.mae_le_1p5) and float(r.mae_le_1p5) < .05
            )
            checks.append(bool(base))
            highs.append(bool(base and float(r.wr) >= .90))
        md.append(f'- {tf}: HIGH_PRECISION_CLUE={"PASS" if all(checks) else "FAIL"}; 90PCT_WR_CLAIM={"PASS" if all(highs) else "FAIL"}')

    md += ['', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
