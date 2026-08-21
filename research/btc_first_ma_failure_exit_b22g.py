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
OUT_MD = ROOT / 'BTC_FIRST_MA_FAILURE_EXIT_B22G_Result.md'
OUT_CSV = ROOT / 'BTC_FIRST_MA_FAILURE_EXIT_B22G_Summary.csv'
OUT_TRADES = ROOT / 'BTC_FIRST_MA_FAILURE_EXIT_B22G_Trades.csv'
PARTS = b22b.PARTS
PAIRS = b22e.PAIRS
EXIT_TYPES = ['FIRST_SOFT_FAILURE', 'FIRST_HARD_FAILURE']


def metrics(g: pd.DataFrame) -> dict:
    if g.empty:
        return dict(n=0, wr=np.nan, pf=np.nan, mean_ret=np.nan, median_ret=np.nan,
                    median_mfe=np.nan, median_mae=np.nan, median_bars=np.nan, max_losing_streak=np.nan)
    r = g['return'].astype(float)
    pos = float(r[r > 0].sum())
    neg = float(-r[r < 0].sum())
    pf = np.inf if neg == 0 and pos > 0 else (pos / neg if neg > 0 else np.nan)
    best = cur = 0
    for x in r:
        if x <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return dict(n=len(g), wr=float((r > 0).mean()), pf=pf, mean_ret=float(r.mean()),
                median_ret=float(r.median()), median_mfe=float(g.mfe.median()),
                median_mae=float(g.mae.median()), median_bars=float(g.bars_held.median()),
                max_losing_streak=int(best))


def simulate(z: pd.DataFrame, hstate: np.ndarray, entry_tf: str, higher_tf: str, exit_type: str):
    idx = z.index
    sig = z.entry_PULLBACK_RECLAIM.fillna(False).to_numpy(bool)
    opens = z.open.to_numpy(float); highs = z.high.to_numpy(float); lows = z.low.to_numpy(float)
    soft = ((z.close < z.ema20) & (z.ema20 < z.ema20.shift(1)) & (z.spread < z.spread.shift(1))).fillna(False).to_numpy(bool)
    hard = ((z.close < z.ema50) | (z.ema20 < z.ema50)).fillna(False).to_numpy(bool)
    exit_sig = soft if exit_type == 'FIRST_SOFT_FAILURE' else hard
    rows = []
    for part, (start, end) in PARTS.items():
        lo = int(idx.searchsorted(start, side='left')); hi = int(idx.searchsorted(end, side='left'))
        for state in ['STRONG_BEAR','NEUTRAL','STRONG_BULL']:
            cursor = lo
            while cursor < hi - 1:
                e_sig = None
                for i in range(cursor, hi - 1):
                    if sig[i] and str(hstate[i]) == state:
                        e_sig = i; break
                if e_sig is None: break
                e_i = e_sig + 1
                if e_i >= hi: break
                x_sig = None
                for j in range(e_i, hi - 1):
                    if exit_sig[j]:
                        x_sig = j; break
                if x_sig is None:
                    x_i = hi - 1; reason = 'PARTITION_FORCE_CLOSE'
                else:
                    x_i = x_sig + 1
                    if x_i >= hi:
                        x_i = hi - 1; reason = 'PARTITION_FORCE_CLOSE'
                    else:
                        reason = exit_type
                if x_i <= e_i:
                    cursor = e_i + 1; continue
                entry = opens[e_i]; exit_px = opens[x_i]
                path_hi = float(np.nanmax(highs[e_i:x_i])); path_lo = float(np.nanmin(lows[e_i:x_i]))
                rows.append(dict(partition=part, entry_tf=entry_tf, higher_tf=higher_tf, higher_state=state,
                                 exit_type=exit_type, signal_ts=idx[e_sig], entry_ts=idx[e_i], exit_ts=idx[x_i],
                                 entry_px=entry, exit_px=exit_px, return=exit_px/entry-1,
                                 mfe=path_hi/entry-1, mae=path_lo/entry-1, bars_held=int(x_i-e_i), exit_reason=reason))
                cursor = x_i
    return rows


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.2f}%'
def num(x): return '-' if pd.isna(x) or not math.isfinite(float(x)) else f'{float(x):.2f}'


def main():
    x5, coverage = b21.load5()
    rows=[]
    for entry_tf, cfg in PAIRS.items():
        z = b22e.add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['rule'])))
        h = b22e.add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['higher_rule'])))
        hs = b22e.higher_state(h, cfg['higher_dur'], z.index + cfg['dur'])
        for ex in EXIT_TYPES:
            rows.extend(simulate(z, hs, entry_tf, cfg['higher_name'], ex))
    trades=pd.DataFrame(rows); trades.to_csv(OUT_TRADES,index=False)
    sums=[]
    for key,g in trades.groupby(['partition','entry_tf','higher_tf','higher_state','exit_type']):
        sums.append(dict(zip(['partition','entry_tf','higher_tf','higher_state','exit_type'],key)) | metrics(g))
    s=pd.DataFrame(sums); s.to_csv(OUT_CSV,index=False)
    md=['# BTC First-MA-Failure Exit B22G — Result','',f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'Actual trade WR when every candle is monitored and the trade exits on the first MA-structure failure. No six-bar cutoff.','',
        '| Partition | Entry→HTF | HTF state | Exit | N | WR | PF | Mean ret | Median ret | Median MFE | Median MAE | Median bars | Max L streak |',
        '|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order={'STRONG_BEAR':0,'NEUTRAL':1,'STRONG_BULL':2}
    s['ord']=s.higher_state.map(order)
    for r in s.sort_values(['partition','entry_tf','exit_type','ord']).itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_tf}→{r.higher_tf} | {r.higher_state} | {r.exit_type} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.mean_ret)} | {pct(r.median_ret)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {r.median_bars:.1f} | {int(r.max_losing_streak)} |')
    md += ['', 'WR is based on realized exit return > 0. Survival to a given candle is not a win/loss statistic.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
