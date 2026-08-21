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
OUT_MD = ROOT / 'BTC_STRONG_STATE_ENTRY_BY_TF_B23C_Result.md'
OUT_JSON = ROOT / 'BTC_STRONG_STATE_ENTRY_BY_TF_B23C_Result.json'
OUT_SUMMARY = ROOT / 'BTC_STRONG_STATE_ENTRY_BY_TF_B23C_Summary.csv'
OUT_TRADES = ROOT / 'BTC_STRONG_STATE_ENTRY_BY_TF_B23C_Trades.csv'

PARTS = b22b.PARTS
TFS = b22b.TFS
VARIANTS = {'E0_ONSET': 0, 'E1_CONFIRM1': 1, 'E2_CONFIRM2': 2}
MARGIN = 10.0
LEVERAGE = 50.0
NOTIONAL = MARGIN * LEVERAGE
ROUND_TRIP_FEE_RATE = 0.0008
ROUND_TRIP_FEE_USD = NOTIONAL * ROUND_TRIP_FEE_RATE


def max_losing_streak(vals) -> int:
    best = cur = 0
    for v in vals:
        if v <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def profit_factor(vals) -> float:
    a = pd.Series(vals, dtype=float)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def simulate(z: pd.DataFrame, tf: str, part: str, start: pd.Timestamp, end: pd.Timestamp,
             variant: str, confirm_bars: int) -> list[dict]:
    idx = z.index
    strong = z.strong.fillna(False).to_numpy(bool)
    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)

    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 5:
        return []

    fresh = strong & ~np.r_[False, strong[:-1]]
    rows: list[dict] = []
    cursor = lo
    final_i = hi - 1

    while cursor < final_i:
        onset = None
        for i in range(cursor, final_i):
            if fresh[i]:
                onset = i
                break
        if onset is None:
            break

        confirm_end = onset + confirm_bars
        if confirm_end >= final_i:
            break

        # Required confirmation bars must remain STRONG consecutively.
        if confirm_bars > 0 and not bool(strong[onset:confirm_end + 1].all()):
            cursor = onset + 1
            continue

        signal_i = confirm_end
        entry_i = signal_i + 1
        if entry_i >= hi:
            break

        # Monitor every completed entry-timeframe candle after execution.
        break_i = None
        for j in range(entry_i, final_i):
            if not strong[j]:
                break_i = j
                break

        if break_i is None:
            exit_i = final_i
            exit_reason = 'PARTITION_FORCE_CLOSE'
        else:
            exit_i = break_i + 1
            if exit_i >= hi:
                exit_i = final_i
                exit_reason = 'PARTITION_FORCE_CLOSE'
            else:
                exit_reason = 'FIRST_NON_STRONG'

        if exit_i <= entry_i:
            cursor = entry_i + 1
            continue

        entry_px = float(opens[entry_i])
        exit_px = float(opens[exit_i])
        path_hi = float(np.nanmax(highs[entry_i:exit_i]))
        path_lo = float(np.nanmin(lows[entry_i:exit_i]))
        ret = exit_px / entry_px - 1.0
        gross_pnl = ret * NOTIONAL
        net_sensitive_pnl = gross_pnl - ROUND_TRIP_FEE_USD

        rows.append({
            'partition': part,
            'timeframe': tf,
            'variant': variant,
            'onset_ts': idx[onset],
            'signal_ts': idx[signal_i],
            'entry_ts': idx[entry_i],
            'exit_ts': idx[exit_i],
            'entry_px': entry_px,
            'exit_px': exit_px,
            'return': ret,
            'mfe': path_hi / entry_px - 1.0,
            'mae': path_lo / entry_px - 1.0,
            'bars_held': int(exit_i - entry_i),
            'gross_pnl_usd_10x50': gross_pnl,
            'net_sensitive_pnl_usd_10x50': net_sensitive_pnl,
            'exit_reason': exit_reason,
        })
        cursor = exit_i

    return rows


def metrics(g: pd.DataFrame) -> dict:
    if g.empty:
        return {'n': 0}

    r = g['return'].astype(float)
    losers = r[r <= 0]
    winners = r[r > 0]
    pnl = g['gross_pnl_usd_10x50'].astype(float)
    net = g['net_sensitive_pnl_usd_10x50'].astype(float)
    mae = g['mae'].astype(float)

    return {
        'n': int(len(g)),
        'wr': float((r > 0).mean()),
        'pf': float(profit_factor(r)),
        'mean_ret': float(r.mean()),
        'median_ret': float(r.median()),
        'median_winner_ret': float(winners.median()) if len(winners) else np.nan,
        'median_loser_ret': float(losers.median()) if len(losers) else np.nan,
        'p10_loser_ret': float(losers.quantile(.10)) if len(losers) else np.nan,
        'median_mfe': float(g.mfe.median()),
        'median_mae': float(mae.median()),
        'p10_mae': float(mae.quantile(.10)),
        'median_bars': float(g.bars_held.median()),
        'max_losing_streak': max_losing_streak(r),
        'gross_mean_pnl_usd': float(pnl.mean()),
        'gross_median_pnl_usd': float(pnl.median()),
        'net_sensitive_wr': float((net > 0).mean()),
        'net_sensitive_pf': float(profit_factor(net)),
        'net_sensitive_mean_pnl_usd': float(net.mean()),
        'mae_le_0p50': float((mae <= -0.005).mean()),
        'mae_le_1p00': float((mae <= -0.010).mean()),
        'mae_le_1p50': float((mae <= -0.015).mean()),
    }


def choose_dev(s: pd.DataFrame, tf: str):
    mins = {'5m': 500, '15m': 200, '1h': 50, '4h': 20}
    q = s[(s.partition == 'development') & (s.timeframe == tf) & (s.n >= mins[tf])].copy()
    if q.empty:
        return None
    max_wr = q.wr.max()
    near = q[q.wr >= max_wr - .01].copy()
    # Smaller absolute median loser is better => value closer to zero is larger.
    near = near.sort_values(['median_loser_ret', 'pf', 'n'], ascending=[False, False, False])
    return near.iloc[0]


def replicated(row: pd.Series, tf: str) -> tuple[bool, bool]:
    nmins = {'5m': 30, '15m': 30, '1h': 20, '4h': 10}
    base = (
        int(row.n) >= nmins[tf]
        and float(row.wr) >= .70
        and pd.notna(row.pf) and float(row.pf) >= 1.20
        and pd.notna(row.median_loser_ret) and float(row.median_loser_ret) > -.005
        and pd.notna(row.p10_mae) and float(row.p10_mae) > -.015
    )
    high = bool(base and float(row.wr) >= .85)
    return bool(base), high


def finite(v):
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except Exception:
        return None


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
    trades_all = []

    for tf, rule in TFS.items():
        z = b22b.enrich(b22b.resample_ohlc(x5, rule))
        for part, (start, end) in PARTS.items():
            for variant, confirms in VARIANTS.items():
                trades_all.extend(simulate(z, tf, part, start, end, variant, confirms))

    trades = pd.DataFrame(trades_all)
    trades.to_csv(OUT_TRADES, index=False)

    summaries = []
    for key, g in trades.groupby(['partition', 'timeframe', 'variant']):
        summaries.append(dict(zip(['partition', 'timeframe', 'variant'], key)) | metrics(g))
    s = pd.DataFrame(summaries)
    s.to_csv(OUT_SUMMARY, index=False)

    selected = {}
    for tf in TFS:
        dev = choose_dev(s, tf)
        if dev is None:
            selected[tf] = None
            continue
        variant = str(dev.variant)
        part_rows = {}
        rep_checks = []
        high_checks = []
        for part in PARTS:
            q = s[(s.partition == part) & (s.timeframe == tf) & (s.variant == variant)]
            if q.empty:
                continue
            r = q.iloc[0]
            part_rows[part] = {k: finite(r[k]) if k not in ('n',) else int(r[k]) for k in [
                'n','wr','pf','mean_ret','median_ret','median_winner_ret','median_loser_ret','p10_loser_ret',
                'median_mfe','median_mae','p10_mae','median_bars','max_losing_streak','gross_mean_pnl_usd',
                'gross_median_pnl_usd','net_sensitive_wr','net_sensitive_pf','net_sensitive_mean_pnl_usd',
                'mae_le_0p50','mae_le_1p00','mae_le_1p50'
            ]}
            if part in ('external', 'reference_validation'):
                a, b = replicated(r, tf)
                rep_checks.append(a); high_checks.append(b)
        selected[tf] = {
            'variant': variant,
            'development_wr': finite(dev.wr),
            'replicated_precision_clue': bool(len(rep_checks) == 2 and all(rep_checks)),
            'high_precision_clue': bool(len(high_checks) == 2 and all(high_checks)),
            'partitions': part_rows,
        }

    payload = {
        'experiment': 'B23C_STRONG_STATE_ENTRY_BY_TF',
        'data_rows_5m': int(len(x5)),
        'coverage': float(coverage),
        'margin_usd': MARGIN,
        'leverage': LEVERAGE,
        'notional_usd': NOTIONAL,
        'fee_sensitivity_round_trip_rate': ROUND_TRIP_FEE_RATE,
        'fee_sensitivity_round_trip_usd': ROUND_TRIP_FEE_USD,
        'selected': selected,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Strong-State Entry by Timeframe B23C — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        f'Position model: **${MARGIN:.0f} margin × {LEVERAGE:.0f}x = ${NOTIONAL:.0f} notional**. Gross PnL excludes fees/slippage/funding. Fee-sensitive columns subtract an illustrative **{ROUND_TRIP_FEE_RATE:.2%} round trip = ${ROUND_TRIP_FEE_USD:.2f}/trade**, not a claim about the user account fee.', '',
        'Entry universe is every fresh STRONG onset, not pullback-only. Exit is dynamic: inspect every completed candle and exit next open on the first candle that is no longer STRONG.', '',
        '## Development entry comparison', '',
        '| TF | Variant | N | Gross WR | PF | Median loser | P10 MAE | Gross mean $ | Fee-sens WR | Fee-sens mean $ | Median bars |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    order_tf = {'5m':0,'15m':1,'1h':2,'4h':3}
    order_v = {'E0_ONSET':0,'E1_CONFIRM1':1,'E2_CONFIRM2':2}
    devtab = s[s.partition == 'development'].copy()
    devtab['otf'] = devtab.timeframe.map(order_tf); devtab['ov'] = devtab.variant.map(order_v)
    for r in devtab.sort_values(['otf','ov']).itertuples(index=False):
        md.append(f'| {r.timeframe} | {r.variant} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.median_loser_ret)} | {pct(r.p10_mae)} | ${num(r.gross_mean_pnl_usd)} | {pct(r.net_sensitive_wr)} | ${num(r.net_sensitive_mean_pnl_usd)} | {num(r.median_bars,1)} |')

    md += ['', '## Precision-first selection and replication', '',
           '| TF | Selected entry | Partition | N | Gross WR | PF | Median loser | P10 MAE | Gross mean $ | Fee-sens WR | Fee-sens PF | Fee-sens mean $ | <=-0.5% MAE | <=-1.0% | <=-1.5% |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for tf in ['5m','15m','1h','4h']:
        sel = selected.get(tf)
        if not sel:
            md.append(f'| {tf} | NONE | - | 0 | - | - | - | - | - | - | - | - | - | - | - |')
            continue
        for part in ['external','development','reference_validation','august']:
            m = sel['partitions'].get(part)
            if not m:
                continue
            md.append(
                f"| {tf} | {sel['variant']} | {part} | {m['n']} | {pct(m['wr'])} | {num(m['pf'])} | {pct(m['median_loser_ret'])} | {pct(m['p10_mae'])} | "
                f"${num(m['gross_mean_pnl_usd'])} | {pct(m['net_sensitive_wr'])} | {num(m['net_sensitive_pf'])} | ${num(m['net_sensitive_mean_pnl_usd'])} | "
                f"{pct(m['mae_le_0p50'])} | {pct(m['mae_le_1p00'])} | {pct(m['mae_le_1p50'])} |"
            )

    md += ['', '## Gates', '']
    for tf in ['5m','15m','1h','4h']:
        sel = selected.get(tf)
        if sel:
            md.append(f"- {tf}: selected **{sel['variant']}**; REPLICATED_PRECISION_CLUE={'PASS' if sel['replicated_precision_clue'] else 'FAIL'}; HIGH_PRECISION_CLUE={'PASS' if sel['high_precision_clue'] else 'FAIL'}")
        else:
            md.append(f'- {tf}: no development candidate met minimum sample.')

    md += ['', 'Interpretation rules:',
           '- A high STRONG-state survival rate is not automatically a high trading WR; entry price versus first non-STRONG exit determines realized PnL.',
           '- No hard SL is used here. MAE tails show whether 50x would be operationally dangerous even if the dynamic signal later exits.',
           '- Fee-sensitive results are intentionally shown because small-timeframe edges can be consumed by transaction costs.',
           '- Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
