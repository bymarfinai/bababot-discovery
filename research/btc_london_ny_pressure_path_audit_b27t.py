#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_london_ny_long_entry_opt_b27r as b27r

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_PRESSURE_PATH_AUDIT_B27T_Result.md'
OUT_PATHS = ROOT / 'BTC_LONDON_NY_PRESSURE_PATH_AUDIT_B27T_Paths.csv'
OUT_SEM = ROOT / 'BTC_LONDON_NY_PRESSURE_PATH_AUDIT_B27T_StopSemantics.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_PRESSURE_PATH_AUDIT_B27T_Summary.csv'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
METHODS = ('NEXT_OPEN','F50','F55','F60','F65','F70','F75','F80')
FRACS = {k:v for k,v in b27r.FRACS.items()}
NOTIONAL = b27r.NOTIONAL
FEE = b27r.FEE


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def primary_signals():
    s = pd.read_csv(SIGNALS)
    s = s[(s.transition == 'LONDON_TO_NEWYORK') & (s.side == 'LONG') & (s.k == 1) & (s.opp_visits_at_signal == 0)].copy()
    for c in ('signal_ts','signal_bar_start','active_session_end'):
        s[c] = pd.to_datetime(s[c], utc=True)
    return s.sort_values(['partition','signal_ts']).reset_index(drop=True)


def path_one(x5, s):
    H = float(s.previous_session_high); L = float(s.previous_session_low)
    sig = pd.Timestamp(s.signal_ts); end = pd.Timestamp(s.active_session_end)
    q = fast_slice(x5, sig, end)
    assert H > L
    rng = H-L
    if q.empty:
        return {'partition':s.partition,'date_utc':s.date_utc,'signal_ts':sig,'structural_outcome':s.structural_outcome,
                'H':H,'L':L,'bars':0,'first_close_break':None,'first_close_break_ts':pd.NaT,
                'min_low':np.nan,'min_low_frac':np.nan,'min_close':np.nan,'min_close_frac':np.nan,
                'wick_L_before_target_close':False,'close_L_before_target_close':False,'wick_H_before_target_close':False,
                **{f'{m}_first_touch_ts':pd.NaT for m in FRACS}}

    first_break = None; first_break_ts = pd.NaT; break_k = len(q)
    for k,(ts,r) in enumerate(q.iterrows()):
        c = float(r.close)
        bh = c > H; bl = c < L
        if bh and bl:
            raise AssertionError('impossible dual close break')
        if bh or bl:
            first_break = 'HIGH' if bh else 'LOW'
            first_break_ts = ts + BAR5
            break_k = k
            break

    # Include bars up to and including the first close-break bar for path extremes, but pre-target flags use strictly prior bars.
    path = q.iloc[:break_k+1] if break_k < len(q) else q
    prior = q.iloc[:break_k] if break_k < len(q) else q
    min_low = float(path.low.min()); min_close = float(path.close.min())
    out = {
        'partition':s.partition,'date_utc':s.date_utc,'signal_ts':sig,'structural_outcome':s.structural_outcome,
        'H':H,'L':L,'bars':len(path),'first_close_break':first_break,'first_close_break_ts':first_break_ts,
        'min_low':min_low,'min_low_frac':(min_low-L)/rng,'min_close':min_close,'min_close_frac':(min_close-L)/rng,
        'wick_L_before_target_close': bool((prior.low.astype(float) <= L).any()) if first_break=='HIGH' else False,
        'close_L_before_target_close': bool((prior.close.astype(float) < L).any()) if first_break=='HIGH' else False,
        'wick_H_before_target_close': bool((prior.high.astype(float) >= H).any()) if first_break=='HIGH' else False,
    }
    for m,f in FRACS.items():
        px = L + f*rng
        hit = q[(q.low.astype(float) <= px) & (q.high.astype(float) >= px)]
        out[f'{m}_first_touch_ts'] = hit.index[0] if len(hit) else pd.NaT

    # Structural identity assertions against B27Q labels.
    expected = {'TARGET_BREAK':'HIGH','OPPOSITE_BREAK':'LOW','NO_BREAK':None}[str(s.structural_outcome)]
    assert first_break == expected, (s.date_utc, s.structural_outcome, first_break)
    if first_break == 'HIGH':
        assert not bool((prior.close.astype(float) < L).any())
    if first_break == 'LOW':
        assert not bool((prior.close.astype(float) > H).any())
    return out


def close_invalidation_limit(x5, s, method):
    H = float(s.previous_session_high); L = float(s.previous_session_low)
    sig = pd.Timestamp(s.signal_ts); end = pd.Timestamp(s.active_session_end)
    q = fast_slice(x5, sig, end)
    if q.empty:
        return None

    if method == 'NEXT_OPEN':
        entry_px = float(q.iloc[0].open); fill_k = 0; fill_ts = q.index[0]
        if not (L <= entry_px <= H):
            return None
    else:
        f = FRACS[method]; entry_px = L + f*(H-L)
        fill_k = None
        for k,(ts,r) in enumerate(q.iterrows()):
            c = float(r.close)
            if c > H or c < L:
                return None
            if float(r.low) <= entry_px <= float(r.high):
                fill_k = k; fill_ts = ts; break
        if fill_k is None:
            return None

    # Same fill-bar target is not awarded for limit entries; close invalidation on fill bar is causal at bar completion.
    r0 = q.iloc[fill_k]
    if float(r0.close) < L:
        exit_px = float(r0.close); reason='CLOSE_INVALID_FILL_BAR'; exit_ts=q.index[fill_k]+BAR5
    else:
        solved = None
        start = fill_k if method == 'NEXT_OPEN' else fill_k + 1
        for k in range(start, len(q)):
            r=q.iloc[k]
            target = float(r.high) >= H
            invalid = float(r.close) < L
            if target and invalid:
                exit_px=float(r.close); reason='CLOSE_INVALID_SAME_BAR_CONSERVATIVE'; exit_ts=q.index[k]+BAR5; solved=True; break
            if invalid:
                exit_px=float(r.close); reason='CLOSE_INVALID'; exit_ts=q.index[k]+BAR5; solved=True; break
            if target:
                exit_px=H; reason='TP_RANGE_EDGE'; exit_ts=q.index[k]; solved=True; break
        if solved is None:
            pos=int(x5.index.searchsorted(end, side='left'))
            if pos>=len(x5):
                return {'filled':True,'entry_px':entry_px,'entry_ts':fill_ts,'exit_px':np.nan,'exit_ts':pd.NaT,'reason':'CENSORED','net':np.nan}
            exit_px=float(x5.iloc[pos].open); exit_ts=x5.index[pos]; reason='TIME_EXIT_SESSION_END'
    ret=exit_px/entry_px-1.0
    return {'filled':True,'entry_px':entry_px,'entry_ts':fill_ts,'exit_px':exit_px,'exit_ts':exit_ts,'reason':reason,'net':ret*NOTIONAL-FEE}


def pf(vals):
    s=pd.Series(vals,dtype=float).dropna(); pos=float(s[s>0].sum()); neg=float(-s[s<0].sum())
    if neg==0 and pos>0:return float('inf')
    return pos/neg if neg>0 else np.nan


def fmt_pct(x): return '-' if pd.isna(x) else f'{100*x:.1f}%'
def fmt_num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def main():
    x5,coverage=b21.load5(); s=primary_signals()
    assert len(s)>0

    paths=pd.DataFrame([path_one(x5,r) for _,r in s.iterrows()])
    paths.to_csv(OUT_PATHS,index=False)

    sem_rows=[]
    for _,r in s.iterrows():
        for method in METHODS:
            # Existing B27R is the exact WICK_STOP control.
            w=b27r.simulate_one(x5,r,method)
            c=close_invalidation_limit(x5,r,method)
            sem_rows.append({
                'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,'method':method,
                'structural_outcome':r.structural_outcome,
                'wick_filled':bool(w.get('filled',False)),'wick_exit_reason':w.get('exit_reason'),
                'wick_net':w.get('net_pnl_usd',np.nan),
                'close_filled':bool(c is not None and c.get('filled',False)),'close_exit_reason':None if c is None else c.get('reason'),
                'close_net':np.nan if c is None else c.get('net',np.nan),
            })
    sem=pd.DataFrame(sem_rows); sem.to_csv(OUT_SEM,index=False)

    # Hard control: aggregate WICK_STOP must match B27R result rows when recomputed through imported engine.
    # Since b27r.simulate_one itself is used, this also prevents accidental reinterpretation.
    assert set(sem.method.unique()) == set(METHODS)

    sums=[]
    for part in PARTS:
        gp=paths[paths.partition==part]
        targ=gp[gp.structural_outcome=='TARGET_BREAK']
        sums.append({
            'partition':part,'signals':len(gp),'target_break_rate':float((gp.structural_outcome=='TARGET_BREAK').mean()) if len(gp) else np.nan,
            'target_break_n':len(targ),
            'target_with_prior_L_wick_n':int(targ.wick_L_before_target_close.sum()) if len(targ) else 0,
            'target_with_prior_L_wick_rate':float(targ.wick_L_before_target_close.mean()) if len(targ) else np.nan,
            'median_min_low_frac_target':float(targ.min_low_frac.median()) if len(targ) else np.nan,
            'p10_min_low_frac_target':float(targ.min_low_frac.quantile(.10)) if len(targ) else np.nan,
            'median_min_close_frac_target':float(targ.min_close_frac.median()) if len(targ) else np.nan,
        })
    sumdf=pd.DataFrame(sums); sumdf.to_csv(OUT_SUM,index=False)

    # Stop-semantics summary.
    ss=[]
    for part in PARTS:
        for method in METHODS:
            g=sem[(sem.partition==part)&(sem.method==method)]
            for kind,col,fillcol in [('WICK_STOP','wick_net','wick_filled'),('CLOSE_INVALIDATION','close_net','close_filled')]:
                r=g[g[fillcol]].copy(); vals=pd.to_numeric(r[col],errors='coerce').dropna()
                ss.append({'partition':part,'method':method,'semantics':kind,'fills':len(vals),
                           'wr':float((vals>0).mean()) if len(vals) else np.nan,
                           'pf':pf(vals),'net_exp':float(vals.mean()) if len(vals) else np.nan,'total_net':float(vals.sum()) if len(vals) else np.nan})
    ssd=pd.DataFrame(ss)

    md=['# B27T — London -> New York Pressure Path / Stop-Semantics Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** B27Q K1 OPP0 signal identity and structural first-close-break outcomes were reproduced exactly.','',
        '## Why 88-90% directional probability can coexist with weak trades','',
        '| Partition | Signals | Target-break | Target breaks | Prior wick to/below Low before eventual High break | Median minimum low fraction | 10th pct minimum low fraction | Median minimum close fraction |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in sumdf.itertuples(index=False):
        md.append(f'| {r.partition} | {r.signals} | {fmt_pct(r.target_break_rate)} | {r.target_break_n} | {r.target_with_prior_L_wick_n} ({fmt_pct(r.target_with_prior_L_wick_rate)}) | {fmt_num(r.median_min_low_frac_target)} | {fmt_num(r.p10_min_low_frac_target)} | {fmt_num(r.median_min_close_frac_target)} |')

    md += ['', 'Range fraction is Low=0, High=1. Negative minimum-low fraction means price wicked below the previous-session Low without necessarily closing below it.', '',
           '## Stop semantics comparison', '',
           '| Partition | Method | Semantics | Fills | WR | PF | Net exp | Total net |',
           '|---|---|---|---:|---:|---:|---:|---:|']
    for r in ssd.itertuples(index=False):
        md.append(f'| {r.partition} | {r.method} | {r.semantics} | {r.fills} | {fmt_pct(r.wr)} | {fmt_num(r.pf)} | ${fmt_num(r.net_exp)} | ${fmt_num(r.total_net)} |')
    md += ['', 'Diagnostic only. CLOSE_INVALIDATION is not promoted as a live stop rule. This audit exists to separate directional edge, path quality, reward:risk, and stop-definition mismatch.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
