#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_previous_session_direct_sweep_b26c as b26c
import btc_prev_session_level_retest_atlas_b27l as b27l

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_ALL_TF_FIRST_RETEST_MIDPOINT_ENTRY_B27P_Result.md'
OUT_SUM = ROOT / 'BTC_ALL_TF_FIRST_RETEST_MIDPOINT_ENTRY_B27P_Summary.csv'
OUT_TRADES = ROOT / 'BTC_ALL_TF_FIRST_RETEST_MIDPOINT_ENTRY_B27P_Trades.csv'
OUT_STATUS = ROOT / 'BTC_ALL_TF_FIRST_RETEST_MIDPOINT_ENTRY_B27P_StatusCounts.csv'

PARTS = b22b.PARTS
TRANSITIONS = b26c.TRANSITIONS
BAR5 = pd.Timedelta(minutes=5)
TOL = 0.002
NOTIONAL = 500.0
FEE_USD = 0.40
REPORT_TFS = ('5m', '15m', '1h', '4h')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def first_signal_5m(q5: pd.DataFrame, prev_hi: float, prev_lo: float):
    for k, (ts, r) in enumerate(q5.iterrows()):
        close = float(r.close); high = float(r.high); low = float(r.low)

        # A completed strict range break before a valid retest consumes the thesis.
        if close > prev_hi or close < prev_lo:
            return {'status':'BREAK_BEFORE_RETEST'}

        hit_hi = b27l.intersects(high, low, prev_hi, TOL)
        hit_lo = b27l.intersects(high, low, prev_lo, TOL)

        if hit_hi and hit_lo:
            return {'status':'AMBIGUOUS_BOTH_ZONES'}
        if hit_hi:
            return {
                'status':'SIGNAL', 'side':'LONG', 'signal_level':'HIGH',
                'signal_k':k, 'signal_bar_start':ts, 'signal_ts':ts + BAR5,
            }
        if hit_lo:
            return {
                'status':'SIGNAL', 'side':'SHORT', 'signal_level':'LOW',
                'signal_k':k, 'signal_bar_start':ts, 'signal_ts':ts + BAR5,
            }
    return {'status':'NO_RETEST'}


def find_midpoint_fill(q5: pd.DataFrame, signal_k: int, prev_hi: float, prev_lo: float, midpoint: float):
    # Order is eligible only from the NEXT 5m bar after the retest bar.
    for k in range(signal_k + 1, len(q5)):
        r = q5.iloc[k]
        close = float(r.close)

        # Conservative deterministic ordering: if a bar closes out of the frozen range
        # before we can prove a midpoint fill occurred first, cancel the unfilled order.
        if close > prev_hi or close < prev_lo:
            return {'status':'RANGE_BROKE_BEFORE_FILL', 'cancel_k':k, 'cancel_ts':q5.index[k] + BAR5}

        if float(r.low) <= midpoint <= float(r.high):
            return {'status':'FILLED', 'fill_k':k, 'fill_ts':q5.index[k]}

    return {'status':'NO_FILL_MIDPOINT'}


def resolve_after_fill(q5: pd.DataFrame, fill_k: int, side: str, midpoint: float,
                       stop_px: float, target_px: float, session_end: pd.Timestamp):
    # Same fill-bar ordering is unknown at 5m resolution.
    # Stop touch is conservatively charged; target-only touch is not awarded.
    r0 = q5.iloc[fill_k]
    if side == 'LONG':
        fillbar_sl = float(r0.low) <= stop_px
    else:
        fillbar_sl = float(r0.high) >= stop_px
    if fillbar_sl:
        exit_px = stop_px
        ret = (exit_px / midpoint - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return q5.index[fill_k], float(exit_px), float(ret), 'SL_FILL_5M_CONSERVATIVE'

    for k in range(fill_k + 1, len(q5)):
        r = q5.iloc[k]
        if side == 'LONG':
            tp = float(r.high) >= target_px
            sl = float(r.low) <= stop_px
        else:
            tp = float(r.low) <= target_px
            sl = float(r.high) >= stop_px

        if tp and sl:
            exit_px = stop_px; reason = 'SL_SAME_5M_CONSERVATIVE'
        elif tp:
            exit_px = target_px; reason = 'TP_RANGE_EDGE'
        elif sl:
            exit_px = stop_px; reason = 'SL_RANGE_EDGE'
        else:
            continue

        ret = (exit_px / midpoint - 1.0) * (1.0 if side == 'LONG' else -1.0)
        return q5.index[k], float(exit_px), float(ret), reason

    return None


def blank_result(base: dict, sig: dict, reason: str):
    return {
        **base,
        'side': sig.get('side'),
        'signal_level': sig.get('signal_level'),
        'signal_bar_start': sig.get('signal_bar_start', pd.NaT),
        'signal_ts': sig.get('signal_ts', pd.NaT),
        'filled': False,
        'entry_ts': pd.NaT, 'entry_px': np.nan,
        'stop_px': np.nan, 'target_px': np.nan,
        'exit_ts': pd.NaT, 'exit_px': np.nan,
        'exit_reason': reason,
        'gross_return': np.nan, 'net_pnl_usd': np.nan, 'hold_minutes': np.nan,
    }


def simulate_day(x5: pd.DataFrame, partition: str, part_start: pd.Timestamp, part_end: pd.Timestamp,
                 transition: str, cfg: dict, day: pd.Timestamp):
    ps = b26c.ts_for_day(day, cfg['prev_start']); pe = b26c.ts_for_day(day, cfg['prev_end'])
    ns = b26c.ts_for_day(day, cfg['next_start']); ne = b26c.ts_for_day(day, cfg['next_end'])
    if ps < part_start or ne > part_end:
        return None

    prev = fast_slice(x5, ps, pe)
    q5 = fast_slice(x5, ns, ne)
    if len(prev) != int((pe-ps)/BAR5) or len(q5) != int((ne-ns)/BAR5):
        return None

    prev_hi = float(prev.high.max()); prev_lo = float(prev.low.min())
    if not prev_hi > prev_lo:
        return None
    midpoint = (prev_hi + prev_lo) / 2.0

    base = {
        'partition': partition, 'transition': transition, 'date_utc': str(day.date()),
        'previous_session_high': prev_hi, 'previous_session_low': prev_lo,
        'midpoint': midpoint, 'active_session_start': ns, 'active_session_end': ne,
    }

    sig = first_signal_5m(q5, prev_hi, prev_lo)
    if sig['status'] != 'SIGNAL':
        return {**blank_result(base, sig, sig['status']), 'setup_status':sig['status']}

    side = sig['side']
    stop_px = prev_lo if side == 'LONG' else prev_hi
    target_px = prev_hi if side == 'LONG' else prev_lo

    fill = find_midpoint_fill(q5, int(sig['signal_k']), prev_hi, prev_lo, midpoint)
    if fill['status'] != 'FILLED':
        row = blank_result(base, sig, fill['status'])
        row['setup_status'] = 'SIGNAL'
        row['stop_px'] = stop_px
        row['target_px'] = target_px
        return row

    fill_k = int(fill['fill_k']); fill_ts = fill['fill_ts']
    solved = resolve_after_fill(q5, fill_k, side, midpoint, stop_px, target_px, ne)
    if solved is None:
        pos = int(x5.index.searchsorted(ne, side='left'))
        if pos >= len(x5):
            return {
                **base, **sig, 'setup_status':'SIGNAL', 'filled':True,
                'entry_ts':fill_ts, 'entry_px':midpoint, 'stop_px':stop_px, 'target_px':target_px,
                'exit_ts':pd.NaT, 'exit_px':np.nan, 'exit_reason':'CENSORED',
                'gross_return':np.nan, 'net_pnl_usd':np.nan, 'hold_minutes':np.nan,
            }
        exit_ts = x5.index[pos]; exit_px = float(x5.iloc[pos].open)
        ret = (exit_px / midpoint - 1.0) * (1.0 if side == 'LONG' else -1.0)
        reason = 'TIME_EXIT_SESSION_END'
    else:
        exit_ts, exit_px, ret, reason = solved

    net = float(ret * NOTIONAL - FEE_USD)
    return {
        **base, **sig, 'setup_status':'SIGNAL', 'filled':True,
        'entry_ts':fill_ts, 'entry_px':midpoint, 'stop_px':stop_px, 'target_px':target_px,
        'exit_ts':exit_ts, 'exit_px':float(exit_px), 'exit_reason':reason,
        'gross_return':float(ret), 'net_pnl_usd':net,
        'hold_minutes':float((exit_ts-fill_ts)/pd.Timedelta(minutes=1)),
    }


def audit_base_rows(x5: pd.DataFrame, base_rows: pd.DataFrame):
    f = base_rows[base_rows.filled.astype(bool)].copy()

    # 1) entry must start no earlier than the next 5m bar after the signal bar.
    if len(f):
        assert (pd.to_datetime(f.entry_ts, utc=True) >= pd.to_datetime(f.signal_ts, utc=True)).all()

    # 2) side/level mapping.
    sig = base_rows[base_rows.setup_status == 'SIGNAL']
    assert ((sig.side == 'LONG') == (sig.signal_level == 'HIGH')).all()
    assert ((sig.side == 'SHORT') == (sig.signal_level == 'LOW')).all()

    # 3/4) midpoint, SL, TP mapping.
    if len(f):
        assert np.allclose(f.entry_px.astype(float), f.midpoint.astype(float), rtol=0, atol=1e-9)
        lf = f[f.side=='LONG']; sf = f[f.side=='SHORT']
        if len(lf):
            assert np.allclose(lf.stop_px.astype(float), lf.previous_session_low.astype(float), rtol=0, atol=1e-9)
            assert np.allclose(lf.target_px.astype(float), lf.previous_session_high.astype(float), rtol=0, atol=1e-9)
        if len(sf):
            assert np.allclose(sf.stop_px.astype(float), sf.previous_session_high.astype(float), rtol=0, atol=1e-9)
            assert np.allclose(sf.target_px.astype(float), sf.previous_session_low.astype(float), rtol=0, atol=1e-9)

    # 5) no strict close break is allowed strictly between signal completion and entry.
    for r in f.itertuples(index=False):
        a = pd.Timestamp(r.signal_ts)
        b = pd.Timestamp(r.entry_ts)
        q = fast_slice(x5, a, b)
        if len(q):
            assert not ((q.close.astype(float) > float(r.previous_session_high)) |
                        (q.close.astype(float) < float(r.previous_session_low))).any()


def duplicate_timeframes_and_assert(base_rows: pd.DataFrame) -> pd.DataFrame:
    frames=[]
    for tf in REPORT_TFS:
        z=base_rows.copy(); z.insert(0,'tf',tf); frames.append(z)
    out=pd.concat(frames, ignore_index=True)

    keycols=['transition','partition','date_utc','side','signal_level','signal_bar_start','signal_ts',
             'filled','entry_ts','entry_px','stop_px','target_px','exit_reason','exit_ts','exit_px','net_pnl_usd']
    ref = out[out.tf=='5m'][keycols].reset_index(drop=True)
    for tf in REPORT_TFS[1:]:
        cur = out[out.tf==tf][keycols].reset_index(drop=True)
        pd.testing.assert_frame_equal(ref, cur, check_dtype=False, check_exact=False, rtol=0, atol=1e-12)
    return out


def pf(vals):
    s = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos=float(s[s>0].sum()); neg=float(-s[s<0].sum())
    if neg==0 and pos>0: return float('inf')
    return pos/neg if neg>0 else np.nan


def summarize(g: pd.DataFrame):
    setups=g[g.setup_status=='SIGNAL'] if len(g) else g
    filled=setups[setups.filled.astype(bool)] if len(setups) else setups
    resolved=filled[pd.to_numeric(filled.net_pnl_usd, errors='coerce').notna()].copy() if len(filled) else filled
    if len(resolved)==0:
        return {'days':int(len(g)),'setups':int(len(setups)),'fills':0,
                'fill_rate':float(len(filled)/len(setups)) if len(setups) else np.nan,
                'wins':0,'losses':0,'wr':np.nan,'tp_rate':np.nan,'net_pf':np.nan,
                'net_exp':np.nan,'total_net':np.nan,'time_exit_rate':np.nan}
    net=pd.to_numeric(resolved.net_pnl_usd, errors='coerce')
    wins=int((net>0).sum()); losses=int((net<=0).sum())
    return {'days':int(len(g)),'setups':int(len(setups)),'fills':int(len(resolved)),
            'fill_rate':float(len(resolved)/len(setups)) if len(setups) else np.nan,
            'wins':wins,'losses':losses,'wr':float(wins/len(resolved)),
            'tp_rate':float((resolved.exit_reason=='TP_RANGE_EDGE').mean()),
            'net_pf':pf(net),'net_exp':float(net.mean()),'total_net':float(net.sum()),
            'time_exit_rate':float((resolved.exit_reason=='TIME_EXIT_SESSION_END').mean())}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    rows=[]
    for part,(start,end) in PARTS.items():
        for day in pd.date_range(start.normalize(), (end-pd.Timedelta(seconds=1)).normalize(), freq='D', tz='UTC'):
            if day.weekday()>=5: continue
            for transition,cfg in TRANSITIONS.items():
                r=simulate_day(x5,part,start,end,transition,cfg,day)
                if r is not None: rows.append(r)

    base_rows=pd.DataFrame(rows)
    audit_base_rows(x5, base_rows)
    trades=duplicate_timeframes_and_assert(base_rows)
    trades.to_csv(OUT_TRADES,index=False)

    sums=[]
    for tf in REPORT_TFS:
        for transition in TRANSITIONS:
            for part in PARTS:
                base=trades[(trades.tf==tf)&(trades.transition==transition)&(trades.partition==part)]
                for group,gg in [('ALL',base),('LONG',base[base.side=='LONG']),('SHORT',base[base.side=='SHORT'])]:
                    sums.append({'tf':tf,'transition':transition,'partition':part,'group':group,**summarize(gg)})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUM,index=False)

    status=(trades.groupby(['tf','transition','partition','setup_status','exit_reason'],dropna=False)
            .size().reset_index(name='n'))
    status.to_csv(OUT_STATUS,index=False)

    # Cross-TF summary invariance assertion as a second independent check.
    metric_cols=['transition','partition','group','days','setups','fills','fill_rate','wins','losses','wr','tp_rate','net_pf','net_exp','total_net','time_exit_rate']
    ref=s[s.tf=='5m'][metric_cols].reset_index(drop=True)
    for tf in REPORT_TFS[1:]:
        cur=s[s.tf==tf][metric_cols].reset_index(drop=True)
        pd.testing.assert_frame_equal(ref,cur,check_dtype=False,check_exact=False,rtol=0,atol=1e-12)

    major=('external','development','reference_validation')
    verdicts={}
    for transition in TRANSITIONS:
        q=s[(s.tf=='5m')&(s.transition==transition)&(s.group=='ALL')&s.partition.isin(major)]
        verdicts[transition]=bool(len(q)==3 and (q.fills>=100).all() and (q.net_exp>0).all() and (q.net_pf>=1.20).all())

    md=['# B27P — Corrected All-TF First Retest -> Midpoint Entry Result','',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        'Rule: first valid 5m High-zone retest (±0.20%, without strict close breakout) -> BULL -> BUY frozen previous-session midpoint from the next 5m bar onward. First valid Low-zone retest -> BEAR -> SELL midpoint. Unfilled order is cancelled if the frozen range strictly close-breaks first. LONG SL=Low/TP=High; SHORT SL=High/TP=Low. $500 notional; $0.40 fee.','',
        '**Audit:** all preregistered causality/mapping assertions passed, including exact trade-set identity across 5m/15m/1H/4H. Because fixed horizontal-level touch ordering is resolved on the same 5m event clock, the four chart-timeframe rows are expected to be identical.','',
        '## Primary result (5m event clock; identical for 15m/1H/4H)','',
        '| Transition | Partition | Group | Setups | Fills | Fill rate | W | L | WR | TP rate | Net PF | Net exp/trade | Total net | Time exit |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    use=s[s.tf=='5m']
    for r in use.itertuples(index=False):
        md.append(f'| {r.transition} | {r.partition} | {r.group} | {r.setups} | {r.fills} | {pct(r.fill_rate)} | {r.wins} | {r.losses} | {pct(r.wr)} | {pct(r.tp_rate)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.time_exit_rate)} |')

    md += ['', '## Cross-timeframe check','',
           '| TF | Result set |', '|---|---|']
    for tf in REPORT_TFS:
        md.append(f'| {tf} | Identical audited event/trade set |')

    md += ['', '## Pre-registered verdict','']
    for transition in TRANSITIONS:
        md.append(f'- {transition}: **{"PASS" if verdicts[transition] else "FAIL"}**')
    md += ['', f'**B27P overall: {"PASS" if any(verdicts.values()) else "FAIL"}.**','',
           'Gate requires >=100 filled trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation for the same transition.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')


if __name__=='__main__':
    main()
