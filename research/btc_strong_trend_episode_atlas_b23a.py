#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_STRONG_TREND_EPISODE_ATLAS_B23A_Result.md'
OUT_SUMMARY = ROOT / 'BTC_STRONG_TREND_EPISODE_ATLAS_B23A_Summary.csv'
OUT_EPISODES = ROOT / 'BTC_STRONG_TREND_EPISODE_ATLAS_B23A_Episodes.csv'
PARTS = b22b.PARTS
TFS = b22b.TFS
CHECKPOINTS = [1,2,3,4,6,12,24,48]


def classify(z: pd.DataFrame) -> pd.DataFrame:
    x = z.copy()
    spread_narrow = x.spread < x.spread.shift(1)
    reversal = (
        (x.close < x.ema50)
        | (x.ema20 < x.ema50)
        | ((x.close < x.ema20) & (x.ema20 < x.ema20.shift(1)) & spread_narrow)
    ).fillna(False)
    strong = x.strong.fillna(False)
    healthy = (
        (x.ema20 > x.ema50)
        & (x.ema50 >= x.ema50.shift(3))
        & (x.close >= x.ema50)
        & (~strong)
        & (~reversal)
    ).fillna(False)
    x['reversal'] = reversal
    x['strong_state'] = strong
    x['healthy_state'] = healthy
    x['weakening_state'] = (~strong & ~healthy & ~reversal).fillna(False)
    return x


def episodes_for(z: pd.DataFrame, tf: str, part: str, start: pd.Timestamp, end: pd.Timestamp):
    idx = z.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi-lo < 3:
        return []
    opens = z.open.to_numpy(float); highs=z.high.to_numpy(float); lows=z.low.to_numpy(float)
    strong=z.strong_state.to_numpy(bool); healthy=z.healthy_state.to_numpy(bool)
    weak=z.weakening_state.to_numpy(bool); rev=z.reversal.to_numpy(bool)
    rows=[]; i=lo
    while i < hi-1:
        if not strong[i]:
            i += 1; continue
        onset=i; entry_i=i+1
        first_non=None; first_non_kind=None; restrong=False; left_strong=False
        j=i+1
        while j < hi:
            if first_non is None and not strong[j]:
                first_non=j
                first_non_kind='REVERSAL' if rev[j] else ('HEALTHY' if healthy[j] else 'WEAKENING')
                left_strong=True
            elif left_strong and strong[j]:
                restrong=True
            if rev[j]:
                break
            j += 1
        censored = j >= hi
        if censored:
            rev_i=None; exit_i=hi-1
        else:
            rev_i=j; exit_i=min(j+1, hi-1)
        max_follow_bars=max(0, hi-1-onset)
        bars_to_rev=None if rev_i is None else int(rev_i-onset)
        bars_to_non=None if first_non is None else int(first_non-onset)
        if exit_i > entry_i:
            path_hi=float(np.nanmax(highs[entry_i:exit_i])); path_lo=float(np.nanmin(lows[entry_i:exit_i]))
            entry_px=float(opens[entry_i]); exit_px=float(opens[exit_i])
            ret=exit_px/entry_px-1.0; mfe=path_hi/entry_px-1.0; mae=path_lo/entry_px-1.0
        else:
            entry_px=float(opens[entry_i]); exit_px=float(opens[exit_i]); ret=exit_px/entry_px-1.0; mfe=np.nan; mae=np.nan
        state_end = rev_i if rev_i is not None else hi
        sl = slice(onset, state_end)
        n=max(1,state_end-onset)
        rows.append({
            'partition':part,'timeframe':tf,'onset_ts':idx[onset],'entry_reference_ts':idx[entry_i],
            'reversal_ts':pd.NaT if rev_i is None else idx[rev_i], 'censored':censored,
            'bars_to_first_non_strong':bars_to_non,'first_non_strong_kind':first_non_kind,
            'bars_to_reversal':bars_to_rev,'max_follow_bars':max_follow_bars,'reentered_strong':restrong,
            'entry_px':entry_px,'exit_px':exit_px,'return_to_reversal':ret,'mfe_to_reversal':mfe,'mae_to_reversal':mae,
            'strong_frac':float(strong[sl].sum()/n),'healthy_frac':float(healthy[sl].sum()/n),'weakening_frac':float(weak[sl].sum()/n),
        })
        i = (rev_i + 1) if rev_i is not None else hi
    return rows


def survival(g: pd.DataFrame, k: int):
    q=g[g.max_follow_bars>=k]
    if q.empty: return np.nan,0
    ok=q.bars_to_reversal.isna() | (q.bars_to_reversal > k)
    return float(ok.mean()),int(len(q))


def summarize(g: pd.DataFrame):
    unc=g.bars_to_reversal.dropna()
    non=g.bars_to_first_non_strong.dropna()
    out={
        'n':int(len(g)), 'reversed_n':int(g.bars_to_reversal.notna().sum()),
        'median_bars_to_reversal':float(unc.median()) if len(unc) else np.nan,
        'median_bars_to_first_non_strong':float(non.median()) if len(non) else np.nan,
        'reentered_strong_rate':float(g.reentered_strong.mean()),
        'median_return_to_reversal':float(g.return_to_reversal.median()),
        'median_mfe_to_reversal':float(g.mfe_to_reversal.median()),
        'median_mae_to_reversal':float(g.mae_to_reversal.median()),
        'mean_strong_frac':float(g.strong_frac.mean()), 'mean_healthy_frac':float(g.healthy_frac.mean()),
        'mean_weakening_frac':float(g.weakening_frac.mean()),
    }
    for k in CHECKPOINTS:
        s,n=survival(g,k); out[f'survival_{k}']=s; out[f'n_at_risk_{k}']=n
    return out


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v): return '-' if pd.isna(v) else f'{float(v):.1f}'


def main():
    x5,coverage=b21.load5(); rows=[]
    for tf,rule in TFS.items():
        z=classify(b22b.enrich(b22b.resample_ohlc(x5,rule)))
        for part,(start,end) in PARTS.items():
            rows.extend(episodes_for(z,tf,part,start,end))
    e=pd.DataFrame(rows); e.to_csv(OUT_EPISODES,index=False)
    sums=[]
    for (part,tf),g in e.groupby(['partition','timeframe']):
        sums.append({'partition':part,'timeframe':tf,**summarize(g)})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUMMARY,index=False)
    md=['# BTC Strong Trend Episode Atlas B23A — Result','',f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'All STRONG episodes are enumerated. This is not restricted to pullback/reclaim entries. An episode starts on the first STRONG candle and remains active through healthy/weakening candles until the first REVERSAL.','',
        '| Partition | TF | N episodes | Median bars→first non-strong | Median bars→reversal | Survive 1 | 2 | 3 | 4 | 6 | 12 | 24 | 48 | Re-enter strong | Median ret→reversal | Median MFE | Median MAE |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order={'5m':0,'15m':1,'1h':2,'4h':3}
    s['ord']=s.timeframe.map(order)
    for r in s.sort_values(['partition','ord']).itertuples(index=False):
        surv=' | '.join(pct(getattr(r,f'survival_{k}')) for k in CHECKPOINTS)
        md.append(f'| {r.partition} | {r.timeframe} | {r.n} | {num(r.median_bars_to_first_non_strong)} | {num(r.median_bars_to_reversal)} | {surv} | {pct(r.reentered_strong_rate)} | {pct(r.median_return_to_reversal)} | {pct(r.median_mfe_to_reversal)} | {pct(r.median_mae_to_reversal)} |')
    md += ['', 'Interpretation: survival is measured from a STRONG onset, not from a pullback entry. B23A does not select an entry confirmation delay or claim a trading WR.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
