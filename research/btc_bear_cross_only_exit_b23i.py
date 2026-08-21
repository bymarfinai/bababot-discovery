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
OUT_MD = ROOT / 'BTC_BEAR_CROSS_ONLY_EXIT_B23I_Result.md'
OUT_SUMMARY = ROOT / 'BTC_BEAR_CROSS_ONLY_EXIT_B23I_Summary.csv'
OUT_TRADES = ROOT / 'BTC_BEAR_CROSS_ONLY_EXIT_B23I_Trades.csv'
OUT_CYCLES = ROOT / 'BTC_BEAR_CROSS_ONLY_EXIT_B23I_Cycles.csv'
PARTS = b22b.PARTS
TFS = b23e.TFS
NOTIONAL = 500.0
FEE_USD = 0.40


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


def simulate(z: pd.DataFrame, tf: str, minutes: int, part: str, start: pd.Timestamp, end: pd.Timestamp):
    idx = z.index
    lo = int(idx.searchsorted(start, side='left')); hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 10: return [], []
    opens = z.open.to_numpy(float); closes = z.close.to_numpy(float)
    highs = z.high.to_numpy(float); lows = z.low.to_numpy(float)
    ema20 = z.ema20.to_numpy(float); ema50 = z.ema50.to_numpy(float)
    bull = z.bull_cross.to_numpy(bool); bear = z.bear_cross.to_numpy(bool)
    rows=[]; cycles=[]; cursor=max(lo,1); final_i=hi-1

    while cursor < final_i:
        cross_i=None
        for i in range(cursor, final_i):
            if bull[i]: cross_i=i; break
        if cross_i is None: break

        bear_i=None
        for j in range(cross_i+1, hi):
            if bear[j]: bear_i=j; break
        cycle_end = bear_i if bear_i is not None else hi

        signal_i=None; red_before=0
        for j in range(cross_i+1, cycle_end):
            if not (ema20[j] > ema50[j]):
                continue
            if closes[j] > opens[j]:
                signal_i=j; break
            red_before += 1

        entered=False
        if signal_i is not None:
            entry_i=signal_i+1
            if entry_i < cycle_end and entry_i < hi:
                entered=True
                entry_px=float(opens[entry_i])
                exit_i=None; trigger_i=None; reason=None

                # B23I: only an actual bearish EMA20/EMA50 crossover may exit.
                for j in range(entry_i, final_i):
                    if bear[j]:
                        if j+1 < hi:
                            trigger_i=j; exit_i=j+1; reason='BEAR_CROSS_ONLY'
                        break

                if exit_i is None:
                    trigger_i=final_i; exit_i=final_i; reason='PARTITION_FORCE_CLOSE'

                if exit_i > entry_i:
                    exit_px=float(opens[exit_i])
                    path_hi=float(np.nanmax(highs[entry_i:exit_i])); path_lo=float(np.nanmin(lows[entry_i:exit_i]))
                    ret=exit_px/entry_px-1.0
                    rows.append({
                        'partition':part,'timeframe':tf,'bull_cross_ts':idx[cross_i],'signal_ts':idx[signal_i],
                        'entry_ts':idx[entry_i],'exit_trigger_ts':idx[trigger_i],'exit_ts':idx[exit_i],
                        'red_bars_before_signal':red_before,'bars_cross_to_signal':int(signal_i-cross_i),
                        'entry_px':entry_px,'exit_px':exit_px,'return':ret,
                        'mfe':path_hi/entry_px-1.0,'mae':path_lo/entry_px-1.0,
                        'bars_held':int(exit_i-entry_i),'hold_minutes':int((exit_i-entry_i)*minutes),
                        'gross_pnl_usd':ret*NOTIONAL,'fee_sensitive_pnl_usd':ret*NOTIONAL-FEE_USD,
                        'exit_reason':reason,
                    })

        cycles.append({'partition':part,'timeframe':tf,'bull_cross_ts':idx[cross_i],
                       'bear_cross_ts':pd.NaT if bear_i is None else idx[bear_i],
                       'signal_ts':pd.NaT if signal_i is None else idx[signal_i],
                       'entered':entered,'red_bars_before_signal':red_before,
                       'bars_cross_to_signal':np.nan if signal_i is None else int(signal_i-cross_i)})
        cursor=(bear_i+1) if bear_i is not None else hi
    return rows, cycles


def metrics(g: pd.DataFrame, cg: pd.DataFrame):
    if len(g)==0:
        return {'armed_cycles':int(len(cg)),'entry_cycles':int(cg.entered.sum()) if len(cg) else 0,'no_trade_rate':np.nan,'n':0}
    r=g['return'].astype(float); w=r[r>0]; l=r[r<=0]; mae=g.mae.astype(float); net=g.fee_sensitive_pnl_usd.astype(float)
    return {
        'armed_cycles':int(len(cg)),'entry_cycles':int(cg.entered.sum()),'no_trade_rate':float(1-cg.entered.mean()),
        'n':int(len(g)),'wr':float((r>0).mean()),'pf':float(pf(r)),'mean_ret':float(r.mean()),'median_ret':float(r.median()),
        'median_winner':float(w.median()) if len(w) else np.nan,'median_loser':float(l.median()) if len(l) else np.nan,
        'median_mfe':float(g.mfe.median()),'median_mae':float(mae.median()),'p10_mae':float(mae.quantile(.10)),
        'median_hold_minutes':float(g.hold_minutes.median()),'mean_gross_usd':float(g.gross_pnl_usd.mean()),
        'fee_wr':float((net>0).mean()),'fee_pf':float(pf(net)),'mean_fee_usd':float(net.mean()),'max_losing_streak':max_ls(r),
        'mae_le_0p5':float((mae<=-.005).mean()),'mae_le_1p0':float((mae<=-.010).mean()),
        'mae_le_1p5':float((mae<=-.015).mean()),'mae_le_1p8':float((mae<=-.018).mean()),
        'bear_cross_exit_rate':float((g.exit_reason=='BEAR_CROSS_ONLY').mean()),
        'force_close_rate':float((g.exit_reason=='PARTITION_FORCE_CLOSE').mean()),
    }


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5,coverage=b21.load5()
    frames={tf:b23e.add_cycles(b22b.enrich(b22b.resample_ohlc(x5,rule))) for tf,(rule,_) in TFS.items()}
    rows=[]; cycles=[]
    for tf,(_,minutes) in TFS.items():
        for part,(start,end) in PARTS.items():
            rr,cc=simulate(frames[tf],tf,minutes,part,start,end); rows.extend(rr); cycles.extend(cc)
    trades=pd.DataFrame(rows); cyc=pd.DataFrame(cycles)
    trades.to_csv(OUT_TRADES,index=False); cyc.to_csv(OUT_CYCLES,index=False)
    sums=[]
    for tf in TFS:
        for part in PARTS:
            g=trades[(trades.partition==part)&(trades.timeframe==tf)]
            cg=cyc[(cyc.partition==part)&(cyc.timeframe==tf)]
            sums.append({'partition':part,'timeframe':tf,**metrics(g,cg)})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUMMARY,index=False)

    md=['# BTC Bear-Cross-Only Exit B23I — Result','',f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'Entry is frozen B23G first-green-after-cross. After entry, red candles, closes below EMA20, and closes below EMA50 are all HOLD. Exit occurs only when EMA20 crosses below EMA50 on the same timeframe, executed at the next same-timeframe open.','',
        'No fixed TP or SL. Position model: **$10 margin x 50x = $500 notional**; illustrative fee sensitivity subtracts **$0.40/trade**.','',
        '| Partition | TF | N | WR | PF | Mean ret | Median winner | Median loser | Median MFE | Median MAE | P10 MAE | Mean $ | Fee WR | Fee PF | <=-0.5 MAE | <=-1.0 | <=-1.5 | <=-1.8 | Med hold min | Bear-cross exit | Force close |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order={'5m':0,'15m':1,'1h':2,'4h':3}; s['ord']=s.timeframe.map(order)
    for r in s.sort_values(['partition','ord']).itertuples(index=False):
        md.append(f'| {r.partition} | {r.timeframe} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.mean_ret)} | {pct(r.median_winner)} | {pct(r.median_loser)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {pct(r.p10_mae)} | ${num(r.mean_gross_usd)} | {pct(r.fee_wr)} | {num(r.fee_pf)} | {pct(r.mae_le_0p5)} | {pct(r.mae_le_1p0)} | {pct(r.mae_le_1p5)} | {pct(r.mae_le_1p8)} | {num(r.median_hold_minutes,1)} | {pct(r.bear_cross_exit_rate)} | {pct(r.force_close_rate)} |')
    md += ['', '## Frozen gates', '']
    for tf in ['5m','15m','1h','4h']:
        checks=[]; high=[]; nmin={'5m':30,'15m':30,'1h':20,'4h':10}[tf]
        for part in ['external','reference_validation']:
            r=s[(s.partition==part)&(s.timeframe==tf)].iloc[0]
            base=(r.n>=nmin and r.wr>=.80 and r.pf>=1.20 and r.median_loser>-.003 and r.mae_le_1p5<.05)
            checks.append(bool(base)); high.append(bool(base and r.wr>=.90))
        md.append(f'- {tf}: HIGH_PRECISION_CLUE={"PASS" if all(checks) else "FAIL"}; 90PCT_WR_CLAIM={"PASS" if all(high) else "FAIL"}')
    md += ['', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
