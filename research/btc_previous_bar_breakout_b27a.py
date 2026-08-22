#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_PREVIOUS_BAR_BREAKOUT_B27A_Result.md'
OUT_SUM = ROOT / 'BTC_PREVIOUS_BAR_BREAKOUT_B27A_Summary.csv'
OUT_TRADES = ROOT / 'BTC_PREVIOUS_BAR_BREAKOUT_B27A_Trades.csv'
PARTS = b22b.PARTS
TFS = {'5m': ('5min', pd.Timedelta(minutes=5)), '15m': ('15min', pd.Timedelta(minutes=15)), '1h': ('1h', pd.Timedelta(hours=1)), '4h': ('4h', pd.Timedelta(hours=4))}
RRS = {'R1': 1.0, 'R2': 2.0}
NOTIONAL = 500.0
FEE = 0.40


def pf(v):
    s = pd.Series(v, dtype=float)
    pos = float(s[s > 0].sum()); neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def build_tf(x5, rule):
    z = b22b.resample_ohlc(x5, rule)
    z['long_sig'] = (z.close > z.high.shift(1)).fillna(False)
    z['short_sig'] = (z.close < z.low.shift(1)).fillna(False)
    return z


def resolve(x5_idx, x5_hi, x5_lo, entry_ts, entry_px, stop_px, target_px, side, part_end):
    a = int(x5_idx.searchsorted(entry_ts, side='left'))
    b = int(x5_idx.searchsorted(part_end, side='left'))
    for k in range(a, b):
        if side == 'LONG':
            tp = x5_hi[k] >= target_px; sl = x5_lo[k] <= stop_px
        else:
            tp = x5_lo[k] <= target_px; sl = x5_hi[k] >= stop_px
        if tp and sl:
            px = stop_px; reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp:
            px = target_px; reason = 'TP'
        elif sl:
            px = stop_px; reason = 'SL'
        else:
            continue
        ret = (px / entry_px - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return x5_idx[k], float(px), float(ret), reason
    return None


def simulate(z, tf, dur, rr_name, rr, x5, part, start, end):
    idx = z.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 3: return []

    opens = z.open.to_numpy(float); highs = z.high.to_numpy(float); lows = z.low.to_numpy(float)
    ls = z.long_sig.to_numpy(bool); ss = z.short_sig.to_numpy(bool)
    xidx = x5.index; xhi = x5.high.to_numpy(float); xlo = x5.low.to_numpy(float)
    rows = []; blocked_until = None

    for i in range(max(lo, 1), hi - 1):
        if not (ls[i] or ss[i]):
            continue
        signal_complete = idx[i] + dur
        entry_i = i + 1
        entry_ts = idx[entry_i]
        if entry_ts >= end:
            break
        if blocked_until is not None and entry_ts <= blocked_until:
            continue
        side = 'LONG' if ls[i] else 'SHORT'
        entry_px = float(opens[entry_i])
        if side == 'LONG':
            stop_px = float(lows[i]); risk = entry_px - stop_px
            if risk <= 0: continue
            target_px = entry_px + rr * risk
        else:
            stop_px = float(highs[i]); risk = stop_px - entry_px
            if risk <= 0: continue
            target_px = entry_px - rr * risk
        risk_pct = risk / entry_px
        solved = resolve(xidx, xhi, xlo, entry_ts, entry_px, stop_px, target_px, side, end)
        if solved is None:
            rows.append({'partition':part,'timeframe':tf,'rr':rr_name,'side':side,'signal_ts':idx[i],
                         'signal_complete_ts':signal_complete,'entry_ts':entry_ts,'entry_px':entry_px,
                         'stop_px':stop_px,'target_px':target_px,'risk_pct':risk_pct,'resolved':False,
                         'exit_ts':pd.NaT,'exit_px':np.nan,'gross_return':np.nan,'net_pnl_usd':np.nan,'exit_reason':'CENSORED'})
            blocked_until = end
            break
        exit_ts, exit_px, ret, reason = solved
        rows.append({'partition':part,'timeframe':tf,'rr':rr_name,'side':side,'signal_ts':idx[i],
                     'signal_complete_ts':signal_complete,'entry_ts':entry_ts,'entry_px':entry_px,
                     'stop_px':stop_px,'target_px':target_px,'risk_pct':risk_pct,'resolved':True,
                     'exit_ts':exit_ts,'exit_px':exit_px,'gross_return':ret,
                     'net_pnl_usd':ret*NOTIONAL-FEE,'exit_reason':reason,
                     'hold_minutes':float((exit_ts-entry_ts)/pd.Timedelta(minutes=1))})
        blocked_until = exit_ts
    return rows


def summarize(g):
    if len(g)==0: return {'entered':0,'resolved':0,'wins':0,'losses':0,'wr':np.nan,'net_pf':np.nan,'net_exp':np.nan,'total_net':np.nan,'med_risk':np.nan,'med_hold':np.nan,'samebar':np.nan}
    r = g[g.resolved.astype(bool)].copy()
    if len(r)==0: return {'entered':len(g),'resolved':0,'wins':0,'losses':0,'wr':np.nan,'net_pf':np.nan,'net_exp':np.nan,'total_net':np.nan,'med_risk':float(g.risk_pct.median()),'med_hold':np.nan,'samebar':np.nan}
    net=r.net_pnl_usd.astype(float); wins=int((r.exit_reason=='TP').sum()); losses=len(r)-wins
    return {'entered':int(len(g)),'resolved':int(len(r)),'wins':wins,'losses':int(losses),'wr':wins/len(r),
            'net_pf':pf(net),'net_exp':float(net.mean()),'total_net':float(net.sum()),
            'med_risk':float(r.risk_pct.median()),'med_hold':float(r.hold_minutes.median()),
            'samebar':float((r.exit_reason=='SL_SAME_5M_CONSERVATIVE').mean())}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    frames={tf:build_tf(x5,rule) for tf,(rule,_) in TFS.items()}
    rows=[]
    for tf,(_,dur) in TFS.items():
        for rr_name,rr in RRS.items():
            for part,(start,end) in PARTS.items():
                rows.extend(simulate(frames[tf],tf,dur,rr_name,rr,x5,part,start,end))
    trades=pd.DataFrame(rows); trades.to_csv(OUT_TRADES,index=False)
    sums=[]
    for tf in TFS:
        for rr_name in RRS:
            for part in PARTS:
                g=trades[(trades.timeframe==tf)&(trades.rr==rr_name)&(trades.partition==part)] if len(trades) else pd.DataFrame()
                sums.append({'timeframe':tf,'rr':rr_name,'partition':part,**summarize(g)})
    s=pd.DataFrame(sums)
    major=('external','development','reference_validation')
    verdict={}
    for tf in TFS:
        for rr_name in RRS:
            z=s[(s.timeframe==tf)&(s.rr==rr_name)&s.partition.isin(major)]
            verdict[(tf,rr_name)]=bool(len(z)==3 and (z.resolved>=100).all() and (z.net_exp>0).all() and (z.net_pf>=1.20).all())
    s['repeatable_pass']=[verdict[(r.timeframe,r.rr)] for r in s.itertuples(index=False)]
    s.to_csv(OUT_SUM,index=False)

    md=['# BTC Previous-Bar Breakout B27A — Result','',f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**','',
        'Frozen rule: previous same-timeframe candle high/low -> completed breakout candle closes beyond it -> entry next same-timeframe open -> stop at opposite extreme of breakout candle. No filters. R1=1R TP; R2=2R TP. Underlying 5m resolves first barrier touch; same-5m ambiguity is conservative SL.','',
        '| TF | RR | Partition | Resolved | W | L | WR | Net PF | Net exp/trade | Total net | Median stop distance | Median hold min | Same-5m ambiguous |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order={'5m':0,'15m':1,'1h':2,'4h':3}; s['ord']=s.timeframe.map(order)
    for r in s.sort_values(['ord','rr','partition']).itertuples(index=False):
        md.append(f'| {r.timeframe} | {r.rr} | {r.partition} | {r.resolved} | {r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.med_risk)} | {num(r.med_hold,1)} | {pct(r.samebar)} |')
    md += ['', '## Repeatability verdict', '']
    for tf in TFS:
        for rr_name in RRS:
            md.append(f'- {tf} {rr_name}: **{"PASS" if verdict[(tf,rr_name)] else "FAIL"}**')
    md += ['', f'**B27A overall: {"PASS" if any(verdict.values()) else "FAIL"}.**', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
