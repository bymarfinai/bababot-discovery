#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_HIERARCHICAL_STRONG_UPTREND_B22C_Result.md'
OUT_JSON = ROOT / 'BTC_HIERARCHICAL_STRONG_UPTREND_B22C_Result.json'
OUT_SUMMARY = ROOT / 'BTC_HIERARCHICAL_STRONG_UPTREND_B22C_Summary.csv'
OUT_TRADES = ROOT / 'BTC_HIERARCHICAL_STRONG_UPTREND_B22C_Champion_Trades.csv'

PARTS = b22b.PARTS
REGIMES = ['R4', 'R1H4']
ENTRY_TFS = {'5m': ('5min', pd.Timedelta(minutes=5)), '15m': ('15min', pd.Timedelta(minutes=15))}
EXIT_TYPES = ['X_ENTRY_STRUCT50', 'X_1H_WEAK', 'X_4H_WEAK', 'X_COMPOSITE']


def available_map(source: pd.Series, source_duration: pd.Timedelta, target_close: pd.DatetimeIndex) -> np.ndarray:
    s = source.fillna(False).astype(bool).copy()
    s.index = s.index + source_duration
    return s.reindex(target_close, method='ffill').fillna(False).to_numpy(bool)


def simulate_arrays(z: pd.DataFrame, part: str, start: pd.Timestamp, end: pd.Timestamp,
                    entry_sig: np.ndarray, exit_sig: np.ndarray,
                    entry_tf: str, regime: str, exit_type: str):
    idx = z.index
    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 3:
        return []
    final_open_i = hi - 1
    cursor = lo
    trades = []
    while cursor < final_open_i:
        e_sig = None
        for i in range(cursor, final_open_i):
            if entry_sig[i]:
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
            if exit_sig[j]:
                x_sig = j
                break
        if x_sig is None:
            x_i = final_open_i
            reason = 'PARTITION_FORCE_CLOSE'
        else:
            x_i = x_sig + 1
            if x_i >= hi:
                x_i = final_open_i
                reason = 'PARTITION_FORCE_CLOSE'
            else:
                reason = exit_type
        if x_i <= e_i:
            cursor = e_i + 1
            continue

        exit_px = opens[x_i]
        path_hi = float(np.nanmax(highs[e_i:x_i]))
        path_lo = float(np.nanmin(lows[e_i:x_i]))
        trades.append({
            'partition': part, 'entry_tf': entry_tf, 'regime': regime, 'exit_type': exit_type,
            'signal_ts': idx[e_sig], 'entry_ts': idx[e_i], 'exit_ts': idx[x_i],
            'entry_px': entry_px, 'exit_px': exit_px,
            'return': exit_px / entry_px - 1.0,
            'mfe': path_hi / entry_px - 1.0,
            'mae': path_lo / entry_px - 1.0,
            'hold_hours': float((idx[x_i] - idx[e_i]) / pd.Timedelta(hours=1)),
            'exit_reason': reason,
        })
        cursor = x_i
    return trades


def eligible(r: pd.Series) -> bool:
    n_min = 100 if r.entry_tf == '5m' else 60
    return (
        r.n >= n_min
        and pd.notna(r.profit_factor) and r.profit_factor >= 1.20
        and pd.notna(r.win_rate) and r.win_rate >= .55
        and pd.notna(r.median_return) and r.median_return > 0
        and pd.notna(r.median_mae) and r.median_mae > -.015
    )


def pick_champion(s: pd.DataFrame):
    d = s[s.partition == 'development'].copy()
    d['eligible'] = d.apply(eligible, axis=1)
    q = d[d.eligible].copy()
    if q.empty:
        return None
    q = q.sort_values(['profit_factor', 'win_rate', 'n'], ascending=[False, False, False])
    best = q.iloc[0]
    near = q[q.profit_factor >= best.profit_factor - .02].copy()
    return near.sort_values(['win_rate', 'n', 'profit_factor'], ascending=[False, False, False]).iloc[0]


def finite(v):
    if v is None:
        return None
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def pct(v):
    return '-' if v is None or pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    return '-' if v is None or pd.isna(v) or not math.isfinite(float(v)) else f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    h1 = b22b.enrich(b22b.resample_ohlc(x5, '1h'))
    h4 = b22b.enrich(b22b.resample_ohlc(x5, '4h'))
    h1_weak = (h1.close < h1.ema20) & (h1.ema20 < h1.ema20.shift(1))
    h4_weak = (h4.close < h4.ema20) & (h4.ema20 < h4.ema20.shift(1))

    summaries = []
    all_trades = {}
    for entry_tf, (rule, dur) in ENTRY_TFS.items():
        z = b22b.enrich(b22b.resample_ohlc(x5, rule))
        close_clock = z.index + dur
        r4 = available_map(h4.strong, pd.Timedelta(hours=4), close_clock)
        r1 = available_map(h1.strong, pd.Timedelta(hours=1), close_clock)
        x1 = available_map(h1_weak, pd.Timedelta(hours=1), close_clock)
        x4 = available_map(h4_weak, pd.Timedelta(hours=4), close_clock)
        base_entry = z.entry_PULLBACK_RECLAIM.fillna(False).to_numpy(bool)
        entry_struct = z.exit_E_STRUCT_50.fillna(False).to_numpy(bool)

        regime_arrays = {'R4': r4, 'R1H4': r4 & r1}
        exit_arrays = {
            'X_ENTRY_STRUCT50': entry_struct,
            'X_1H_WEAK': x1,
            'X_4H_WEAK': x4,
            'X_COMPOSITE': entry_struct | x1,
        }

        for regime, rmask in regime_arrays.items():
            esig = base_entry & rmask
            for ex, xsig in exit_arrays.items():
                for part, (start, end) in PARTS.items():
                    tr = simulate_arrays(z, part, start, end, esig, xsig, entry_tf, regime, ex)
                    all_trades[(part, entry_tf, regime, ex)] = tr
                    m = b22b.metrics(tr)
                    summaries.append({'partition': part, 'entry_tf': entry_tf, 'regime': regime, 'exit_type': ex, **m})

    s = pd.DataFrame(summaries)
    s.to_csv(OUT_SUMMARY, index=False)
    champ = pick_champion(s)
    champion = None
    gates = {'B22C_REPLICATED_CLUE': False, 'HIGH_PRECISION_CLUE': False}
    champ_trades = []

    if champ is not None:
        etf, reg, ex = champ.entry_tf, champ.regime, champ.exit_type
        rows = s[(s.entry_tf == etf) & (s.regime == reg) & (s.exit_type == ex)]
        pm = {}
        for r in rows.itertuples(index=False):
            pm[r.partition] = {
                'n': int(r.n), 'win_rate': finite(r.win_rate), 'mean_return': finite(r.mean_return),
                'median_return': finite(r.median_return), 'profit_factor': finite(r.profit_factor),
                'median_hold_h': finite(r.median_hold_h), 'median_mfe': finite(r.median_mfe),
                'median_mae': finite(r.median_mae), 'p90_adverse': finite(r.p90_adverse),
                'max_losing_streak': int(r.max_losing_streak) if pd.notna(r.max_losing_streak) else None,
            }
        oks, hps = [], []
        for p in ['external', 'reference_validation']:
            m = pm.get(p, {})
            ok = (
                (m.get('n') or 0) >= 30
                and (m.get('win_rate') or 0) >= .60
                and (m.get('profit_factor') or 0) >= 1.20
                and (m.get('median_return') or 0) > 0
                and m.get('median_mae') is not None and m.get('median_mae') > -.015
            )
            oks.append(ok)
            hps.append(ok and (m.get('win_rate') or 0) >= .80)
        gates['B22C_REPLICATED_CLUE'] = bool(all(oks))
        gates['HIGH_PRECISION_CLUE'] = bool(all(hps))
        champion = {'entry_tf': etf, 'regime': reg, 'exit_type': ex, 'partitions': pm}
        for p in PARTS:
            champ_trades.extend(all_trades[(p, etf, reg, ex)])
        pd.DataFrame(champ_trades).to_csv(OUT_TRADES, index=False)
    else:
        pd.DataFrame().to_csv(OUT_TRADES, index=False)

    payload = {
        'experiment': 'B22C_HIERARCHICAL_STRONG_UPTREND',
        'data_rows_5m': int(len(x5)), 'coverage': float(coverage),
        'champion': champion, 'gates': gates,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Hierarchical Strong Uptrend B22C — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Hierarchy: 4h (or 1h+4h) strong-uptrend permission → 5m/15m healthy pullback-reclaim entry → reversal-state exit. No fixed TP and no stop.', '',
        '## Development leaderboard', '',
        '| Entry TF | Regime | Exit | N | WR | PF | Median ret | Median MFE | Median MAE | Hold h | Eligible |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|',
    ]
    dev = s[s.partition == 'development'].copy()
    dev['eligible'] = dev.apply(eligible, axis=1)
    dev = dev.sort_values(['eligible', 'profit_factor', 'win_rate'], ascending=[False, False, False])
    for r in dev.itertuples(index=False):
        md.append(f'| {r.entry_tf} | {r.regime} | {r.exit_type} | {r.n} | {pct(r.win_rate)} | {num(r.profit_factor)} | {pct(r.median_return)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {num(r.median_hold_h,1)} | {"YES" if r.eligible else "NO"} |')

    md += ['', '## Frozen champion replication', '']
    if champion is None:
        md.append('No development candidate passed all preregistered eligibility gates.')
    else:
        md.append(f"Champion: **{champion['entry_tf']} / {champion['regime']} / {champion['exit_type']}**")
        md += ['', '| Partition | N | WR | PF | Mean ret | Median ret | Median MFE | Median MAE | P90 adverse | Max L streak |',
               '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in PARTS:
            m = champion['partitions'].get(p, {})
            md.append(f"| {p} | {m.get('n',0)} | {pct(m.get('win_rate'))} | {num(m.get('profit_factor'))} | {pct(m.get('mean_return'))} | {pct(m.get('median_return'))} | {pct(m.get('median_mfe'))} | {pct(m.get('median_mae'))} | {pct(m.get('p90_adverse'))} | {m.get('max_losing_streak') if m.get('max_losing_streak') is not None else '-'} |")
        md += ['', f"- B22C_REPLICATED_CLUE: **{'PASS' if gates['B22C_REPLICATED_CLUE'] else 'FAIL'}**",
               f"- HIGH_PRECISION_CLUE: **{'PASS' if gates['HIGH_PRECISION_CLUE'] else 'FAIL'}**"]

    md += ['', '## Causality', '',
           'Higher-timeframe states are shifted to their candle-close availability time before being mapped to the entry clock. Entry and exit execution is always on the next entry-timeframe open.', '',
           'This is research only; live BBC remains untouched.']
    OUT_MD.write_text('\n'.join(md) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
