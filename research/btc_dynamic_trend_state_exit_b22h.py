#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_opposing_htf_fakeout_b22e as b22e

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_DYNAMIC_TREND_STATE_EXIT_B22H_Result.md'
OUT_CSV = ROOT / 'BTC_DYNAMIC_TREND_STATE_EXIT_B22H_Summary.csv'
OUT_TRADES = ROOT / 'BTC_DYNAMIC_TREND_STATE_EXIT_B22H_Trades.csv'
PARTS = b22b.PARTS
PAIRS = b22e.PAIRS


def add_dynamic_states(z: pd.DataFrame) -> pd.DataFrame:
    x = z.copy()
    e20_up = x.ema20 > x.ema20.shift(3)
    e50_up = x.ema50 > x.ema50.shift(3)
    e50_nonneg = x.ema50 >= x.ema50.shift(3)
    spread_widen = x.spread >= x.spread.shift(1)
    spread_narrow = x.spread < x.spread.shift(1)

    reversal_close50 = x.close < x.ema50
    reversal_cross = x.ema20 < x.ema50
    reversal_roll = (x.close < x.ema20) & (x.ema20 < x.ema20.shift(1)) & spread_narrow
    x['reversal'] = (reversal_close50 | reversal_cross | reversal_roll).fillna(False)
    x['reversal_reason'] = np.select(
        [reversal_close50.fillna(False), reversal_cross.fillna(False), reversal_roll.fillna(False)],
        ['CLOSE_BELOW_EMA50', 'EMA20_BELOW_EMA50', 'BELOW_EMA20_SLOPE_DOWN_SPREAD_NARROW'],
        default='NONE',
    )
    x['strong_cont'] = (
        (x.ema20 > x.ema50) & e20_up & e50_up & (x.close >= x.ema20) & spread_widen & (~x.reversal)
    ).fillna(False)
    x['healthy_cont'] = (
        (x.ema20 > x.ema50) & e50_nonneg & (x.close >= x.ema50) & (~x.reversal) & (~x.strong_cont)
    ).fillna(False)
    return x


def metrics(g: pd.DataFrame) -> dict:
    if g.empty:
        return {}
    r = g['return'].astype(float)
    pos = float(r[r > 0].sum()); neg = float(-r[r < 0].sum())
    pf = np.inf if neg == 0 and pos > 0 else (pos / neg if neg > 0 else np.nan)
    best = cur = 0
    for x in r:
        if x <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return {
        'n': int(len(g)), 'wr': float((r > 0).mean()), 'pf': pf,
        'mean_ret': float(r.mean()), 'median_ret': float(r.median()),
        'median_mfe': float(g.mfe.median()), 'median_mae': float(g.mae.median()),
        'median_bars': float(g.bars_held.median()), 'max_losing_streak': int(best),
        'mean_strong_frac': float(g.strong_frac.mean()),
        'mean_healthy_frac': float(g.healthy_frac.mean()),
    }


def simulate(z: pd.DataFrame, hstate: np.ndarray, entry_tf: str, higher_tf: str):
    idx = z.index
    sig = z.entry_PULLBACK_RECLAIM.fillna(False).to_numpy(bool)
    opens = z.open.to_numpy(float); highs = z.high.to_numpy(float); lows = z.low.to_numpy(float)
    reversal = z.reversal.fillna(False).to_numpy(bool)
    reasons = z.reversal_reason.to_numpy(object)
    strong = z.strong_cont.fillna(False).to_numpy(bool)
    healthy = z.healthy_cont.fillna(False).to_numpy(bool)
    rows = []

    for part, (start, end) in PARTS.items():
        lo = int(idx.searchsorted(start, side='left')); hi = int(idx.searchsorted(end, side='left'))
        for state in ['STRONG_BEAR', 'NEUTRAL', 'STRONG_BULL']:
            cursor = lo
            while cursor < hi - 1:
                s_i = None
                for i in range(cursor, hi - 1):
                    if sig[i] and str(hstate[i]) == state:
                        s_i = i; break
                if s_i is None:
                    break
                e_i = s_i + 1
                if e_i >= hi:
                    break

                r_i = None
                for j in range(e_i, hi - 1):
                    if reversal[j]:
                        r_i = j; break

                if r_i is None:
                    x_i = hi - 1; exit_reason = 'PARTITION_FORCE_CLOSE'
                    monitor_end = x_i
                else:
                    x_i = min(r_i + 1, hi - 1)
                    exit_reason = str(reasons[r_i]) if x_i < hi else 'PARTITION_FORCE_CLOSE'
                    monitor_end = r_i + 1

                if x_i <= e_i:
                    cursor = e_i + 1
                    continue

                entry = float(opens[e_i]); exit_px = float(opens[x_i])
                path_hi = float(np.nanmax(highs[e_i:x_i])); path_lo = float(np.nanmin(lows[e_i:x_i]))
                nmon = max(1, monitor_end - e_i)
                rows.append({
                    'partition': part, 'entry_tf': entry_tf, 'higher_tf': higher_tf,
                    'higher_state_at_entry': state, 'signal_ts': idx[s_i], 'entry_ts': idx[e_i],
                    'exit_ts': idx[x_i], 'entry_px': entry, 'exit_px': exit_px,
                    'return': exit_px / entry - 1.0, 'mfe': path_hi / entry - 1.0,
                    'mae': path_lo / entry - 1.0, 'bars_held': int(x_i - e_i),
                    'strong_bars': int(strong[e_i:monitor_end].sum()),
                    'healthy_bars': int(healthy[e_i:monitor_end].sum()),
                    'strong_frac': float(strong[e_i:monitor_end].sum() / nmon),
                    'healthy_frac': float(healthy[e_i:monitor_end].sum() / nmon),
                    'exit_reason': exit_reason,
                })
                cursor = x_i
    return rows


def pct(x):
    return '-' if pd.isna(x) else f'{100 * float(x):.2f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def main():
    x5, coverage = b21.load5()
    rows = []
    for entry_tf, cfg in PAIRS.items():
        z = add_dynamic_states(b22e.add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['rule']))))
        h = b22e.add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['higher_rule'])))
        hs = b22e.higher_state(h, cfg['higher_dur'], z.index + cfg['dur'])
        rows.extend(simulate(z, hs, entry_tf, cfg['higher_name']))

    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)
    sums = []
    for key, g in trades.groupby(['partition', 'entry_tf', 'higher_tf', 'higher_state_at_entry']):
        sums.append(dict(zip(['partition', 'entry_tf', 'higher_tf', 'higher_state_at_entry'], key)) | metrics(g))
    s = pd.DataFrame(sums)
    s.to_csv(OUT_CSV, index=False)

    md = [
        '# BTC Dynamic Trend-State Exit B22H — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Every completed entry-timeframe candle is reclassified dynamically. HOLD while STRONG_CONTINUATION or HEALTHY_CONTINUATION; EXIT at next open after first REVERSAL. No fixed TP and no fixed candle horizon.', '',
        '| Partition | Entry→HTF | HTF state @ entry | N | WR | PF | Mean ret | Median ret | Median MFE | Median MAE | Median bars | Strong frac | Healthy frac | Max L streak |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    order = {'STRONG_BEAR': 0, 'NEUTRAL': 1, 'STRONG_BULL': 2}
    s['ord'] = s.higher_state_at_entry.map(order)
    for r in s.sort_values(['partition', 'entry_tf', 'ord']).itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.entry_tf}→{r.higher_tf} | {r.higher_state_at_entry} | {r.n} | {pct(r.wr)} | {num(r.pf)} | '
            f'{pct(r.mean_ret)} | {pct(r.median_ret)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {r.median_bars:.1f} | '
            f'{pct(r.mean_strong_frac)} | {pct(r.mean_healthy_frac)} | {int(r.max_losing_streak)} |'
        )
    md += ['', 'State transitions are evaluated at every completed candle; normal healthy pullbacks are allowed without forcing an exit.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')

if __name__ == '__main__':
    main()
