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
OUT_MD = ROOT / 'BTC_CROSSOVER_CYCLE_ENTRY_B23E_Result.md'
OUT_SUMMARY = ROOT / 'BTC_CROSSOVER_CYCLE_ENTRY_B23E_Summary.csv'
OUT_TRADES = ROOT / 'BTC_CROSSOVER_CYCLE_ENTRY_B23E_Trades.csv'

PARTS = b22b.PARTS
TFS = {
    '5m': ('5min', 5),
    '15m': ('15min', 15),
    '1h': ('1h', 60),
    '4h': ('4h', 240),
}
VARIANTS = ['C1_CROSS_ENTRY', 'C2_FIRST_STRONG_AFTER_CROSS']
NOTIONAL = 500.0
FEE_USD = 0.40


def add_cycles(frame: pd.DataFrame) -> pd.DataFrame:
    x = b23d.classify(frame)
    x['bull_cross'] = ((x.ema20 > x.ema50) & (x.ema20.shift(1) <= x.ema50.shift(1))).fillna(False)
    x['bear_cross'] = ((x.ema20 < x.ema50) & (x.ema20.shift(1) >= x.ema50.shift(1))).fillna(False)
    x['c1_valid'] = (x.bull_cross & (x.close > x.ema20) & (x.ema20 > x.ema20.shift(1))).fillna(False)
    return x


def simulate(z: pd.DataFrame, tf: str, minutes: int, part: str, start: pd.Timestamp, end: pd.Timestamp, variant: str):
    idx = z.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 10:
        return []

    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)
    state = z.state.to_numpy(object)
    strong = (z.state == 'STRONG_BULL').to_numpy(bool)
    bull = z.bull_cross.to_numpy(bool)
    bear = z.bear_cross.to_numpy(bool)
    c1 = z.c1_valid.to_numpy(bool)

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

        signal_i = None
        if variant == 'C1_CROSS_ENTRY':
            if c1[cross_i]:
                signal_i = cross_i
        else:
            for j in range(cross_i, cycle_end):
                if strong[j]:
                    signal_i = j
                    break

        if signal_i is not None:
            entry_i = signal_i + 1
            if entry_i < hi and entry_i < cycle_end:
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
                    rows.append({
                        'partition': part,
                        'timeframe': tf,
                        'variant': variant,
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

        # Never re-enter within the same bullish crossover cycle.
        cursor = (bear_i + 1) if bear_i is not None else hi

    return rows


def pf(vals):
    a = pd.Series(vals, dtype=float)
    pos = float(a[a > 0].sum()); neg = float(-a[a < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_ls(vals):
    best = cur = 0
    for v in vals:
        if v <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(g: pd.DataFrame):
    r = g['return'].astype(float); w = r[r > 0]; l = r[r <= 0]
    mae = g.mae.astype(float); net = g.fee_sensitive_pnl_usd.astype(float)
    return {
        'n': int(len(g)), 'wr': float((r > 0).mean()), 'pf': float(pf(r)),
        'mean_ret': float(r.mean()), 'median_ret': float(r.median()),
        'median_winner': float(w.median()) if len(w) else np.nan,
        'median_loser': float(l.median()) if len(l) else np.nan,
        'median_mfe': float(g.mfe.median()), 'median_mae': float(mae.median()), 'p10_mae': float(mae.quantile(.10)),
        'median_cross_to_signal': float(g.bars_cross_to_signal.median()),
        'median_bars': float(g.bars_held.median()), 'median_hold_minutes': float(g.hold_minutes.median()),
        'mean_gross_usd': float(g.gross_pnl_usd.mean()), 'fee_wr': float((net > 0).mean()),
        'fee_pf': float(pf(net)), 'mean_fee_usd': float(net.mean()), 'max_losing_streak': max_ls(r),
        'mae_le_0p5': float((mae <= -.005).mean()), 'mae_le_1p0': float((mae <= -.010).mean()),
        'mae_le_1p5': float((mae <= -.015).mean()), 'mae_le_1p8': float((mae <= -.018).mean()),
    }


def choose_dev(s: pd.DataFrame, tf: str):
    nmin = {'5m':100,'15m':80,'1h':30,'4h':15}[tf]
    q = s[(s.partition == 'development') & (s.timeframe == tf) & (s.n >= nmin)].copy()
    if q.empty: return None
    maxwr = float(q.wr.max())
    near = q[q.wr >= maxwr - .01].copy()
    near['abs_med_loser'] = near.median_loser.abs()
    near = near.sort_values(['pf','abs_med_loser'], ascending=[False, True])
    return near.iloc[0]


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    frames = {tf: add_cycles(b22b.enrich(b22b.resample_ohlc(x5, rule))) for tf,(rule,_) in TFS.items()}
    rows=[]
    for tf,(_,minutes) in TFS.items():
        for part,(start,end) in PARTS.items():
            for variant in VARIANTS:
                rows.extend(simulate(frames[tf], tf, minutes, part, start, end, variant))
    trades=pd.DataFrame(rows); trades.to_csv(OUT_TRADES,index=False)
    sums=[]
    for key,g in trades.groupby(['partition','timeframe','variant']):
        sums.append(dict(zip(['partition','timeframe','variant'],key)) | metrics(g))
    s=pd.DataFrame(sums); s.to_csv(OUT_SUMMARY,index=False)

    selected={}
    for tf in TFS:
        r=choose_dev(s,tf)
        selected[tf]=None if r is None else str(r.variant)

    md=['# BTC Crossover-Cycle Entry B23E — Result','',f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'At most one entry is allowed per EMA20/EMA50 bullish crossover cycle. Monitoring and exit remain on the same timeframe as entry.','',
        '## Development comparison','',
        '| TF | Variant | N | WR | PF | Median winner | Median loser | Median MFE | Median MAE | Cross→signal bars | Mean $ | Fee WR | Fee PF |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order={'5m':0,'15m':1,'1h':2,'4h':3}
    d=s[s.partition=='development'].copy(); d['ord']=d.timeframe.map(order)
    for r in d.sort_values(['ord','variant']).itertuples(index=False):
        md.append(f'| {r.timeframe} | {r.variant} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.median_winner)} | {pct(r.median_loser)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {num(r.median_cross_to_signal,1)} | ${num(r.mean_gross_usd)} | {pct(r.fee_wr)} | {num(r.fee_pf)} |')

    md += ['', '## Frozen selected variant replication', '',
           '| TF | Selected | Partition | N | WR | PF | Mean ret | Median winner | Median loser | Median MFE | Median MAE | P10 MAE | Mean $ | Fee WR | Fee PF | <=-0.5 MAE | <=-1.0 | <=-1.5 | <=-1.8 | Med hold min |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for tf in ['5m','15m','1h','4h']:
        v=selected[tf]
        if v is None: continue
        for part in ['external','development','reference_validation','august']:
            q=s[(s.timeframe==tf)&(s.variant==v)&(s.partition==part)]
            if q.empty: continue
            r=q.iloc[0]
            md.append(f'| {tf} | {v} | {part} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {pct(r.mean_ret)} | {pct(r.median_winner)} | {pct(r.median_loser)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {pct(r.p10_mae)} | ${num(r.mean_gross_usd)} | {pct(r.fee_wr)} | {num(r.fee_pf)} | {pct(r.mae_le_0p5)} | {pct(r.mae_le_1p0)} | {pct(r.mae_le_1p5)} | {pct(r.mae_le_1p8)} | {num(r.median_hold_minutes,1)} |')

    md += ['', '## Frozen gates','']
    for tf in ['5m','15m','1h','4h']:
        v=selected[tf]; checks=[]; highs=[]
        nmin={'5m':30,'15m':30,'1h':20,'4h':10}[tf]
        if v is not None:
            for part in ['external','reference_validation']:
                q=s[(s.timeframe==tf)&(s.variant==v)&(s.partition==part)]
                if q.empty: checks.append(False); highs.append(False); continue
                r=q.iloc[0]
                base=(int(r.n)>=nmin and float(r.wr)>=.80 and float(r.pf)>=1.20 and float(r.median_loser)>-.003 and float(r.mae_le_1p5)<.05)
                checks.append(bool(base)); highs.append(bool(base and float(r.wr)>=.90))
        md.append(f'- {tf}: selected **{v or "NONE"}**; HIGH_PRECISION_CLUE={"PASS" if checks and all(checks) else "FAIL"}; 90PCT_WR_CLAIM={"PASS" if highs and all(highs) else "FAIL"}')

    md += ['', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
