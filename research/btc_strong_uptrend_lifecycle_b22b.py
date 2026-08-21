#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_STRONG_UPTREND_LIFECYCLE_B22B_Result.md'
OUT_JSON = ROOT / 'BTC_STRONG_UPTREND_LIFECYCLE_B22B_Result.json'
OUT_SUMMARY = ROOT / 'BTC_STRONG_UPTREND_LIFECYCLE_B22B_Summary.csv'
OUT_TRADES = ROOT / 'BTC_STRONG_UPTREND_LIFECYCLE_B22B_Champion_Trades.csv'

PARTS = {
    'external': (pd.Timestamp('2020-01-01', tz='UTC'), pd.Timestamp('2022-01-01', tz='UTC')),
    'development': (pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')),
    'reference_validation': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-07-30', tz='UTC')),
    'august': (pd.Timestamp('2026-08-01', tz='UTC'), pd.Timestamp('2026-08-21', tz='UTC')),
}
TFS = {'5m': '5min', '15m': '15min', '1h': '1h', '4h': '4h'}
ENTRY_TYPES = ['CROSSOVER_INIT', 'PULLBACK_RECLAIM']
EXIT_TYPES = ['E_FAST_20', 'E_WEAKEN_20', 'E_STRUCT_50', 'E_BEAR_CROSS']


def resample_ohlc(x5: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == '5min':
        return x5[['open', 'high', 'low', 'close']].copy()
    return x5[['open', 'high', 'low', 'close']].resample(
        rule, origin='start_day', label='left', closed='left'
    ).agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()


def enrich(frame: pd.DataFrame) -> pd.DataFrame:
    z = frame.copy()
    z['ema20'] = z.close.ewm(span=20, adjust=False, min_periods=20).mean()
    z['ema50'] = z.close.ewm(span=50, adjust=False, min_periods=50).mean()
    z['spread'] = (z.ema20 - z.ema50) / z.close
    z['ema20_rise3'] = z.ema20 > z.ema20.shift(3)
    z['ema50_rise3'] = z.ema50 > z.ema50.shift(3)
    z['spread_widen3'] = z.spread > z.spread.shift(3)
    z['strong'] = (
        (z.ema20 > z.ema50)
        & z.ema20_rise3
        & z.ema50_rise3
        & z.spread_widen3
        & (z.close > z.ema20)
    )
    cross_up = (z.ema20 > z.ema50) & (z.ema20.shift(1) <= z.ema50.shift(1))
    z['entry_CROSSOVER_INIT'] = cross_up & z.ema20_rise3 & z.ema50_rise3 & (z.close > z.ema20)

    prev_zone = (
        (z.low.shift(1) <= z.ema20.shift(1))
        & (z.low.shift(1) >= z.ema50.shift(1))
        & (z.close.shift(1) >= z.ema50.shift(1))
    )
    z['entry_PULLBACK_RECLAIM'] = z.strong & prev_zone & (z.close > z.open) & (z.close > z.ema20)

    z['exit_E_FAST_20'] = z.close < z.ema20
    z['exit_E_WEAKEN_20'] = (z.close < z.ema20) & (z.ema20 < z.ema20.shift(1))
    z['exit_E_STRUCT_50'] = z.close < z.ema50
    z['exit_E_BEAR_CROSS'] = (z.ema20 < z.ema50) & (z.ema20.shift(1) >= z.ema50.shift(1))
    return z


def simulate(z: pd.DataFrame, part: str, start: pd.Timestamp, end: pd.Timestamp, entry_type: str, exit_type: str):
    # Indicators are allowed to use pre-partition warmup, but signals/positions are partition-local.
    idx = z.index
    sig_entry = z[f'entry_{entry_type}'].fillna(False).to_numpy(bool)
    sig_exit = z[f'exit_{exit_type}'].fillna(False).to_numpy(bool)
    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)

    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))  # first bar outside partition
    if hi - lo < 3:
        return []

    trades = []
    cursor = lo
    final_open_i = hi - 1
    while cursor < final_open_i:
        # Find next completed-candle entry signal whose next bar open is still inside partition.
        e_sig = None
        for i in range(cursor, final_open_i):
            if sig_entry[i]:
                e_sig = i
                break
        if e_sig is None:
            break
        e_i = e_sig + 1
        if e_i >= hi:
            break
        entry_px = opens[e_i]

        x_sig = None
        for j in range(e_i, final_open_i):
            if sig_exit[j]:
                x_sig = j
                break
        if x_sig is None:
            x_i = final_open_i
            exit_reason = 'PARTITION_FORCE_CLOSE'
        else:
            x_i = x_sig + 1
            if x_i >= hi:
                x_i = final_open_i
                exit_reason = 'PARTITION_FORCE_CLOSE'
            else:
                exit_reason = exit_type

        if x_i <= e_i:
            cursor = e_i + 1
            continue

        exit_px = opens[x_i]
        path_hi = float(np.nanmax(highs[e_i:x_i]))
        path_lo = float(np.nanmin(lows[e_i:x_i]))
        ret = exit_px / entry_px - 1.0
        mfe = path_hi / entry_px - 1.0
        mae = path_lo / entry_px - 1.0
        trades.append({
            'partition': part,
            'timeframe': None,
            'entry_type': entry_type,
            'exit_type': exit_type,
            'signal_ts': idx[e_sig],
            'entry_ts': idx[e_i],
            'exit_ts': idx[x_i],
            'entry_px': entry_px,
            'exit_px': exit_px,
            'return': ret,
            'mfe': mfe,
            'mae': mae,
            'hold_hours': float((idx[x_i] - idx[e_i]) / pd.Timedelta(hours=1)),
            'exit_reason': exit_reason,
        })
        cursor = x_i
    return trades


def max_losing_streak(rets: pd.Series) -> int:
    best = cur = 0
    for v in rets:
        if v <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return {
            'n': 0, 'win_rate': None, 'mean_return': None, 'median_return': None,
            'profit_factor': None, 'median_hold_h': None, 'median_mfe': None,
            'median_mae': None, 'p90_adverse': None, 'max_losing_streak': None,
        }
    d = pd.DataFrame(trades)
    r = d['return'].astype(float)
    pos = float(r[r > 0].sum())
    neg = float(-r[r < 0].sum())
    pf = float('inf') if neg == 0 and pos > 0 else (pos / neg if neg > 0 else None)
    return {
        'n': int(len(d)),
        'win_rate': float((r > 0).mean()),
        'mean_return': float(r.mean()),
        'median_return': float(r.median()),
        'profit_factor': pf,
        'median_hold_h': float(d.hold_hours.median()),
        'median_mfe': float(d.mfe.median()),
        'median_mae': float(d.mae.median()),
        # 10th percentile MAE = adverse excursion exceeded by only 10% of trades.
        'p90_adverse': float(d.mae.quantile(.10)),
        'max_losing_streak': max_losing_streak(r),
    }


def eligible(row: pd.Series) -> bool:
    n_min = {'5m': 100, '15m': 100, '1h': 50, '4h': 25}[row.timeframe]
    return (
        row.n >= n_min
        and pd.notna(row.profit_factor) and row.profit_factor >= 1.20
        and pd.notna(row.win_rate) and row.win_rate >= .55
        and pd.notna(row.median_return) and row.median_return > 0
    )


def pick_champion(summary: pd.DataFrame):
    dev = summary[summary.partition == 'development'].copy()
    dev['eligible'] = dev.apply(eligible, axis=1)
    q = dev[dev.eligible].copy()
    if q.empty:
        return None
    q = q.sort_values(['profit_factor', 'win_rate', 'n'], ascending=[False, False, False])
    best = q.iloc[0]
    # Tie rule: PF within .02 -> higher win rate -> larger N.
    near = q[q.profit_factor >= best.profit_factor - .02].copy()
    near = near.sort_values(['win_rate', 'n', 'profit_factor'], ascending=[False, False, False])
    return near.iloc[0]


def finite(v):
    if v is None:
        return None
    try:
        return float(v) if math.isfinite(float(v)) else None
    except Exception:
        return None


def pct(v):
    return '-' if v is None or pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    return '-' if v is None or pd.isna(v) or not math.isfinite(float(v)) else f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    summaries = []
    all_trades: dict[tuple[str, str, str, str], list[dict]] = {}

    for tf, rule in TFS.items():
        z = enrich(resample_ohlc(x5, rule))
        for part, (start, end) in PARTS.items():
            for ent in ENTRY_TYPES:
                for ex in EXIT_TYPES:
                    tr = simulate(z, part, start, end, ent, ex)
                    for r in tr:
                        r['timeframe'] = tf
                    all_trades[(part, tf, ent, ex)] = tr
                    m = metrics(tr)
                    summaries.append({'partition': part, 'timeframe': tf, 'entry_type': ent, 'exit_type': ex, **m})

    s = pd.DataFrame(summaries)
    s.to_csv(OUT_SUMMARY, index=False)
    champ = pick_champion(s)

    champion_payload = None
    validation = {'B22B_REPLICATED_CLUE': False, 'HIGH_PRECISION_CLUE': False}
    champion_trades = []
    if champ is not None:
        tf, ent, ex = champ.timeframe, champ.entry_type, champ.exit_type
        rows = s[(s.timeframe == tf) & (s.entry_type == ent) & (s.exit_type == ex)].copy()
        part_metrics = {}
        for r in rows.itertuples(index=False):
            part_metrics[r.partition] = {
                'n': int(r.n), 'win_rate': finite(r.win_rate), 'mean_return': finite(r.mean_return),
                'median_return': finite(r.median_return), 'profit_factor': finite(r.profit_factor),
                'median_hold_h': finite(r.median_hold_h), 'median_mfe': finite(r.median_mfe),
                'median_mae': finite(r.median_mae), 'p90_adverse': finite(r.p90_adverse),
                'max_losing_streak': int(r.max_losing_streak) if pd.notna(r.max_losing_streak) else None,
            }
        checks = []
        hp = []
        for p in ['external', 'reference_validation']:
            m = part_metrics.get(p, {})
            ok = (
                (m.get('n') or 0) >= 20
                and (m.get('win_rate') or 0) >= .60
                and (m.get('profit_factor') or 0) >= 1.20
                and (m.get('median_return') or 0) > 0
                and (m.get('median_mae') is not None and m.get('median_mae') > -.02)
            )
            checks.append(ok)
            hp.append(ok and (m.get('win_rate') or 0) >= .80)
        validation['B22B_REPLICATED_CLUE'] = bool(all(checks))
        validation['HIGH_PRECISION_CLUE'] = bool(all(hp))
        champion_payload = {'timeframe': tf, 'entry_type': ent, 'exit_type': ex, 'partitions': part_metrics}
        for p in PARTS:
            champion_trades.extend(all_trades[(p, tf, ent, ex)])
        pd.DataFrame(champion_trades).to_csv(OUT_TRADES, index=False)
    else:
        pd.DataFrame().to_csv(OUT_TRADES, index=False)

    payload = {
        'experiment': 'B22B_STRONG_UPTREND_LIFECYCLE',
        'data_rows_5m': int(len(x5)),
        'coverage': float(coverage),
        'champion': champion_payload,
        'validation': validation,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Strong Uptrend Lifecycle B22B — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Setup family: EMA20/EMA50 rising/widening strong-uptrend state, crossover or healthy pullback/reclaim entry, and reversal-state exit. No fixed TP and no stop-loss.', '',
        '## Development leaderboard (eligible rows first)', '',
        '| TF | Entry | Exit | N | WR | PF | Median ret | Median MFE | Median MAE | Hold h |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    dev = s[s.partition == 'development'].copy()
    dev['eligible'] = dev.apply(eligible, axis=1)
    dev = dev.sort_values(['eligible', 'profit_factor', 'win_rate'], ascending=[False, False, False])
    for r in dev.head(16).itertuples(index=False):
        md.append(f'| {r.timeframe} | {r.entry_type} | {r.exit_type} | {r.n} | {pct(r.win_rate)} | {num(r.profit_factor)} | {pct(r.median_return)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {num(r.median_hold_h,1)} |')

    md += ['', '## Frozen champion replication', '']
    if champion_payload is None:
        md.append('No development candidate passed the preregistered eligibility gates.')
    else:
        md.append(f"Champion: **{champion_payload['timeframe']} / {champion_payload['entry_type']} / {champion_payload['exit_type']}**")
        md += ['', '| Partition | N | WR | PF | Mean ret | Median ret | Median MFE | Median MAE | P90 adverse | Max L streak |',
               '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in PARTS:
            m = champion_payload['partitions'].get(p, {})
            md.append(f"| {p} | {m.get('n',0)} | {pct(m.get('win_rate'))} | {num(m.get('profit_factor'))} | {pct(m.get('mean_return'))} | {pct(m.get('median_return'))} | {pct(m.get('median_mfe'))} | {pct(m.get('median_mae'))} | {pct(m.get('p90_adverse'))} | {m.get('max_losing_streak') if m.get('max_losing_streak') is not None else '-'} |")
        md += ['', f"- B22B_REPLICATED_CLUE: **{'PASS' if validation['B22B_REPLICATED_CLUE'] else 'FAIL'}**",
               f"- HIGH_PRECISION_CLUE: **{'PASS' if validation['HIGH_PRECISION_CLUE'] else 'FAIL'}**"]

    md += ['', '## Scientific note', '',
           '- Entries and exits are causal: completed-candle signal, execution at next candle open.',
           '- External/reference-validation were not used to select the champion.',
           '- No fees/slippage are included, so marginal gross edges are not promotable.',
           '- No old discovery result and no live BBC logic was changed.']
    OUT_MD.write_text('\n'.join(md) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
