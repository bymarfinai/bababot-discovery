#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_DYNAMIC_CONDITION_ENGINE_B23D_Result.md'
OUT_SUMMARY = ROOT / 'BTC_DYNAMIC_CONDITION_ENGINE_B23D_Summary.csv'
OUT_TRADES = ROOT / 'BTC_DYNAMIC_CONDITION_ENGINE_B23D_Trades.csv'

PARTS = b22b.PARTS
TFS = {
    '5m': ('5min', pd.Timedelta(minutes=5), 5),
    '15m': ('15min', pd.Timedelta(minutes=15), 15),
    '1h': ('1h', pd.Timedelta(hours=1), 60),
    '4h': ('4h', pd.Timedelta(hours=4), 240),
}
CONTEXTS = {
    '5m': ['15m', '1h', '4h'],
    '15m': ['1h', '4h'],
    '1h': ['4h'],
    '4h': [],
}
MARGIN = 10.0
LEVERAGE = 50.0
NOTIONAL = MARGIN * LEVERAGE
FEE_RT = 0.0008
FEE_USD = NOTIONAL * FEE_RT


def classify(z: pd.DataFrame) -> pd.DataFrame:
    x = z.copy()
    e20_up3 = x.ema20 > x.ema20.shift(3)
    e50_up3 = x.ema50 > x.ema50.shift(3)
    e50_nonneg3 = x.ema50 >= x.ema50.shift(3)
    spread_widen3 = x.spread > x.spread.shift(3)

    strong = (
        (x.ema20 > x.ema50)
        & e20_up3
        & e50_up3
        & spread_widen3
        & (x.close > x.ema20)
    ).fillna(False)

    reversal = ((x.close < x.ema50) | (x.ema20 < x.ema50)).fillna(False)

    det_score = (
        (x.ema20 <= x.ema20.shift(1)).astype(int)
        + (x.spread < x.spread.shift(1)).astype(int)
        + (x.close < x.ema20).astype(int)
    )
    deteriorating = (
        (x.ema20 > x.ema50)
        & (x.close >= x.ema50)
        & (det_score >= 2)
        & (~reversal)
        & (~strong)
    ).fillna(False)

    healthy = (
        (x.ema20 > x.ema50)
        & e50_nonneg3
        & (x.close >= x.ema50)
        & (~strong)
        & (~deteriorating)
        & (~reversal)
    ).fillna(False)

    state = np.select(
        [reversal.to_numpy(bool), deteriorating.to_numpy(bool), strong.to_numpy(bool), healthy.to_numpy(bool)],
        ['REVERSAL', 'DETERIORATING', 'STRONG_BULL', 'HEALTHY_BULL'],
        default='TRANSITION',
    )
    x['state'] = state
    x['fresh_strong'] = strong & (~strong.shift(1).fillna(False))
    return x


def state_asof(frame: pd.DataFrame, dur: pd.Timedelta, timestamps: pd.DatetimeIndex) -> np.ndarray:
    s = pd.Series(frame.state.to_numpy(object), index=frame.index + dur)
    return s.reindex(timestamps, method='ffill').fillna('NA').to_numpy(object)


def profit_factor(vals) -> float:
    a = pd.Series(vals, dtype=float)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_losing_streak(vals) -> int:
    best = cur = 0
    for v in vals:
        if v <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def simulate(frame: pd.DataFrame, tf: str, minutes: int, contexts: dict[str, tuple[pd.DataFrame, pd.Timedelta]]) -> list[dict]:
    idx = frame.index
    opens = frame.open.to_numpy(float)
    highs = frame.high.to_numpy(float)
    lows = frame.low.to_numpy(float)
    state = frame.state.to_numpy(object)
    fresh = frame.fresh_strong.fillna(False).to_numpy(bool)

    # State of each allowed higher TF known at the anchor bar open/close timestamp.
    ctx_arrays = {}
    for name, (cf, cdur) in contexts.items():
        ctx_arrays[name] = state_asof(cf, cdur, idx)

    rows = []
    for part, (start, end) in PARTS.items():
        lo = int(idx.searchsorted(start, side='left'))
        hi = int(idx.searchsorted(end, side='left'))
        if hi - lo < 5:
            continue
        cursor = lo
        final_i = hi - 1

        while cursor < final_i:
            sig_i = None
            for i in range(cursor, final_i):
                if fresh[i]:
                    sig_i = i
                    break
            if sig_i is None:
                break

            # Signal exists only after sig_i candle closes. Entry is next same-TF open.
            entry_i = sig_i + 1
            if entry_i >= hi:
                break
            entry_px = float(opens[entry_i])

            exit_i = None
            exit_reason = None
            for j in range(entry_i, final_i):
                st = str(state[j])
                if st in ('STRONG_BULL', 'HEALTHY_BULL'):
                    continue
                if st == 'DETERIORATING':
                    exit_i = j + 1
                    exit_reason = 'DYNAMIC_DETERIORATION_CUT'
                    break
                if st == 'REVERSAL':
                    exit_i = j + 1
                    exit_reason = 'REVERSAL_CUT'
                    break
                # TRANSITION is observed but not enough by itself to force an exit.

            if exit_i is None or exit_i >= hi:
                exit_i = final_i
                exit_reason = 'PARTITION_FORCE_CLOSE'
            if exit_i <= entry_i:
                cursor = entry_i + 1
                continue

            exit_px = float(opens[exit_i])
            path_hi = float(np.nanmax(highs[entry_i:exit_i]))
            path_lo = float(np.nanmin(lows[entry_i:exit_i]))
            ret = exit_px / entry_px - 1.0
            gross = ret * NOTIONAL
            net = gross - FEE_USD

            rec = {
                'partition': part,
                'timeframe': tf,
                'signal_ts': idx[sig_i],
                'entry_ts': idx[entry_i],
                'exit_ts': idx[exit_i],
                'entry_px': entry_px,
                'exit_px': exit_px,
                'return': ret,
                'mfe': path_hi / entry_px - 1.0,
                'mae': path_lo / entry_px - 1.0,
                'bars_held': int(exit_i - entry_i),
                'hold_minutes': int((exit_i - entry_i) * minutes),
                'gross_pnl_usd': gross,
                'fee_sensitive_pnl_usd': net,
                'exit_reason': exit_reason,
            }
            for cname, carr in ctx_arrays.items():
                rec[f'context_{cname}'] = str(carr[entry_i])
            rows.append(rec)
            cursor = exit_i
    return rows


def metrics(g: pd.DataFrame) -> dict:
    r = g['return'].astype(float)
    winners = r[r > 0]
    losers = r[r <= 0]
    mae = g.mae.astype(float)
    gross = g.gross_pnl_usd.astype(float)
    net = g.fee_sensitive_pnl_usd.astype(float)
    counts = g.exit_reason.value_counts(normalize=True)
    return {
        'n': int(len(g)),
        'wr': float((r > 0).mean()),
        'pf': float(profit_factor(r)),
        'mean_ret': float(r.mean()),
        'median_ret': float(r.median()),
        'median_winner_ret': float(winners.median()) if len(winners) else np.nan,
        'median_loser_ret': float(losers.median()) if len(losers) else np.nan,
        'median_mfe': float(g.mfe.median()),
        'median_mae': float(mae.median()),
        'p10_mae': float(mae.quantile(.10)),
        'median_bars': float(g.bars_held.median()),
        'median_hold_minutes': float(g.hold_minutes.median()),
        'max_losing_streak': max_losing_streak(r),
        'mean_gross_usd': float(gross.mean()),
        'fee_sensitive_wr': float((net > 0).mean()),
        'fee_sensitive_pf': float(profit_factor(net)),
        'mean_fee_sensitive_usd': float(net.mean()),
        'mae_le_0p5': float((mae <= -.005).mean()),
        'mae_le_1p0': float((mae <= -.010).mean()),
        'mae_le_1p5': float((mae <= -.015).mean()),
        'mae_le_1p8': float((mae <= -.018).mean()),
        'exit_deterioration': float(counts.get('DYNAMIC_DETERIORATION_CUT', 0.0)),
        'exit_reversal': float(counts.get('REVERSAL_CUT', 0.0)),
        'exit_forced': float(counts.get('PARTITION_FORCE_CLOSE', 0.0)),
    }


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()

    frames = {}
    for tf, (rule, dur, minutes) in TFS.items():
        frames[tf] = classify(b22b.enrich(b22b.resample_ohlc(x5, rule)))

    rows = []
    for tf, (_, _, minutes) in TFS.items():
        ctx = {c: (frames[c], TFS[c][1]) for c in CONTEXTS[tf]}
        rows.extend(simulate(frames[tf], tf, minutes, ctx))

    trades = pd.DataFrame(rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for (part, tf), g in trades.groupby(['partition','timeframe']):
        sums.append({'partition':part,'timeframe':tf,**metrics(g)})
    s = pd.DataFrame(sums)
    s.to_csv(OUT_SUMMARY, index=False)

    md = [
        '# BTC Dynamic Condition Engine B23D — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        f'Position model: **${MARGIN:.0f} margin × {LEVERAGE:.0f}x = ${NOTIONAL:.0f} notional**. Fee sensitivity subtracts illustrative **{FEE_RT:.2%} round trip = ${FEE_USD:.2f}/trade**.', '',
        '**Corrected design:** each timeframe is independent. A 5m trade is monitored on 5m, 15m on 15m, 1h on 1h, and 4h on 4h. Higher-TF states are recorded only as context diagnostics and never manage the primary trade.', '',
        'Entry is the next same-timeframe open after a fresh image-like STRONG_BULL onset. HOLD on STRONG_BULL or HEALTHY_BULL; exit next same-timeframe open on DETERIORATING or REVERSAL. No fixed TP/SL and no fixed bar horizon.', '',
        '| Partition | TF | N | WR | PF | Mean ret | Median winner | Median loser | Median MFE | Median MAE | P10 MAE | Mean $ | Fee WR | Fee PF | Fee mean $ | <=-0.5 MAE | <=-1.0 | <=-1.5 | <=-1.8 | Med bars | Med time min |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    order = {'5m':0,'15m':1,'1h':2,'4h':3}
    s['ord'] = s.timeframe.map(order)
    for r in s.sort_values(['partition','ord']).itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.timeframe} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.mean_ret)} | {pct(r.median_winner_ret)} | {pct(r.median_loser_ret)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {pct(r.p10_mae)} | ${num(r.mean_gross_usd)} | {pct(r.fee_sensitive_wr)} | {num(r.fee_sensitive_pf)} | ${num(r.mean_fee_sensitive_usd)} | {pct(r.mae_le_0p5)} | {pct(r.mae_le_1p0)} | {pct(r.mae_le_1p5)} | {pct(r.mae_le_1p8)} | {num(r.median_bars,1)} | {num(r.median_hold_minutes,1)} |'
        )

    md += ['', '## Exit-reason mix', '',
           '| Partition | TF | Deterioration cut | Reversal cut | Forced close |',
           '|---|---|---:|---:|---:|']
    for r in s.sort_values(['partition','ord']).itertuples(index=False):
        md.append(f'| {r.partition} | {r.timeframe} | {pct(r.exit_deterioration)} | {pct(r.exit_reversal)} | {pct(r.exit_forced)} |')

    md += ['', '## Frozen precision gates', '']
    for tf in ['5m','15m','1h','4h']:
        nmin={'5m':30,'15m':30,'1h':20,'4h':10}[tf]
        checks=[]; high=[]
        for part in ['external','reference_validation']:
            q=s[(s.partition==part)&(s.timeframe==tf)]
            if q.empty:
                checks.append(False); high.append(False); continue
            r=q.iloc[0]
            base=(int(r.n)>=nmin and float(r.wr)>=.80 and float(r.pf)>=1.20 and float(r.median_loser_ret)>-.003 and float(r.mae_le_1p5)<.05)
            checks.append(bool(base)); high.append(bool(base and float(r.wr)>=.90))
        md.append(f'- {tf}: HIGH_PRECISION_CLUE={"PASS" if all(checks) else "FAIL"}; 90PCT_WR_CLAIM={"PASS" if all(high) else "FAIL"}')

    md += ['', 'Important for 50x: monitoring at the selected timeframe means an adverse move can occur inside a candle before the condition-based exit becomes executable. MAE tails are reported to expose this explicitly; they are not liquidation-price calculations.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__ == '__main__':
    main()
