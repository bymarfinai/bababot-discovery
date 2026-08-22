#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_f15_full_hybrid_activation_grid_b27at as b27at

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Trades.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Result.md'
OUT_WINDOWS = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Windows.csv'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
ENTRY_F = 0.15
BASE_TOTAL = -15.05841591698896
EPS = 1e-12


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def valid_low_retest(r, L: float, H: float) -> bool:
    # Opposite-break precedence: a close > H is never counted as a Low retest.
    return float(r.low) <= L and float(r.close) >= L and float(r.close) <= H


def scan_window(x5: pd.DataFrame, s: pd.Series) -> dict:
    H = float(s.previous_session_high); L = float(s.previous_session_low); R = H-L
    sig = pd.Timestamp(s.signal_bar_start); sig_ts = pd.Timestamp(s.signal_ts); end = pd.Timestamp(s.active_session_end)
    F15 = L + ENTRY_F*R
    q = b27ad.fast_slice(x5, sig, end)
    if q.empty or q.index[0] != sig: raise AssertionError('missing K1 bar')
    if sig_ts != sig + BAR5: raise AssertionError('bad signal clock')
    r0=q.iloc[0]
    if not valid_low_retest(r0,L,H): raise AssertionError('K1 is not valid Low retest')

    base = dict(partition=s.partition,date_utc=s.date_utc,signal_ts=sig_ts,signal_bar_start=sig,
                session_end=end,H=H,L=L,range=R,F15=F15)

    # Collapse K1 visit episode; first normal non-touch bar is causal leave #1.
    k=1; k1_bars=1; leave1=pd.NaT
    while k < len(q):
        r=q.iloc[k]; ts=q.index[k]; c=float(r.close)
        if c < L: return {**base,'status':'BREAKDOWN_BEFORE_H2','k1_episode_bars':k1_bars,'h2_bar_start':pd.NaT,'h2_episode_bars':0,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'BREAKDOWN_BEFORE_H2'}
        if c > H: return {**base,'status':'OPPOSITE_BREAK_BEFORE_H2','k1_episode_bars':k1_bars,'h2_bar_start':pd.NaT,'h2_episode_bars':0,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'OPPOSITE_BREAK_BEFORE_H2'}
        if valid_low_retest(r,L,H):
            k1_bars += 1; k += 1; continue
        leave1=ts; k += 1; break
    if pd.isna(leave1): return {**base,'status':'NO_LEAVE1','k1_episode_bars':k1_bars,'h2_bar_start':pd.NaT,'h2_episode_bars':0,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'NO_LEAVE1'}

    # Search distinct valid retest #2 after the leave-1 bar is complete.
    h2=pd.NaT
    while k < len(q):
        r=q.iloc[k]; ts=q.index[k]; c=float(r.close)
        if c < L: return {**base,'status':'BREAKDOWN_BEFORE_H2','k1_episode_bars':k1_bars,'h2_bar_start':pd.NaT,'h2_episode_bars':0,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'BREAKDOWN_BEFORE_H2'}
        if c > H: return {**base,'status':'OPPOSITE_BREAK_BEFORE_H2','k1_episode_bars':k1_bars,'h2_bar_start':pd.NaT,'h2_episode_bars':0,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'OPPOSITE_BREAK_BEFORE_H2'}
        if valid_low_retest(r,L,H): h2=ts; break
        k += 1
    if pd.isna(h2): return {**base,'status':'NO_H2_BY_SESSION_END','k1_episode_bars':k1_bars,'h2_bar_start':pd.NaT,'h2_episode_bars':0,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'NO_H2_BY_SESSION_END'}

    # Collapse H2 episode and require causal leave #2.
    h2_bars=0
    while k < len(q):
        r=q.iloc[k]; ts=q.index[k]; c=float(r.close)
        if c < L: return {**base,'status':'BREAKDOWN_DURING_H2_EPISODE','k1_episode_bars':k1_bars,'h2_bar_start':h2,'h2_episode_bars':h2_bars,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'BREAKDOWN_DURING_H2_EPISODE'}
        if c > H: return {**base,'status':'OPPOSITE_BREAK_DURING_H2_EPISODE','k1_episode_bars':k1_bars,'h2_bar_start':h2,'h2_episode_bars':h2_bars,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'OPPOSITE_BREAK_DURING_H2_EPISODE'}
        if valid_low_retest(r,L,H): h2_bars += 1; k += 1; continue
        leave2=ts; eligible=ts+BAR5; k += 1; break
    else:
        return {**base,'status':'NO_LEAVE2','k1_episode_bars':k1_bars,'h2_bar_start':h2,'h2_episode_bars':h2_bars,'leave2_bar_start':pd.NaT,'eligible_start':pd.NaT,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'NO_LEAVE2'}

    # k now points to the first eligible bar. Terminal conditions have precedence over fill.
    if k >= len(q):
        return {**base,'status':'CLEAN_NO_FILL','k1_episode_bars':k1_bars,'h2_bar_start':h2,'h2_episode_bars':h2_bars,'leave2_bar_start':leave2,'eligible_start':eligible,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':pd.NaT,'h3_after_fill':False,'terminal':'SESSION_END'}
    if q.index[k] != eligible: raise AssertionError(('eligibility geometry',q.index[k],eligible))

    fill=pd.NaT; h3=pd.NaT; terminal='SESSION_END'
    j=k
    while j < len(q):
        r=q.iloc[j]; ts=q.index[j]; c=float(r.close)
        if c < L: terminal='BREAKDOWN_BEFORE_H3'; break
        if c > H: terminal='OPPOSITE_BREAK_BEFORE_H3'; break
        if valid_low_retest(r,L,H): h3=ts; terminal='H3_ARRIVAL'; break
        if float(r.low) <= F15 <= float(r.high): fill=ts; break
        j += 1

    if pd.isna(fill):
        return {**base,'status':'CLEAN_NO_FILL','k1_episode_bars':k1_bars,'h2_bar_start':h2,'h2_episode_bars':h2_bars,'leave2_bar_start':leave2,'eligible_start':eligible,'filled':False,'fill_bar_start':pd.NaT,'h3_bar_start':h3,'h3_after_fill':False,'terminal':terminal}

    # After fill, locate first H3 / breakdown / opposite-break terminal. Start NEXT bar so fill is strictly before H3.
    j += 1; h3=pd.NaT; terminal='SESSION_END'
    while j < len(q):
        r=q.iloc[j]; ts=q.index[j]; c=float(r.close)
        if c < L: terminal='BREAKDOWN_BEFORE_H3'; break
        if c > H: terminal='OPPOSITE_BREAK_BEFORE_H3'; break
        if valid_low_retest(r,L,H): h3=ts; terminal='H3_ARRIVAL'; break
        j += 1
    if not (fill >= eligible): raise AssertionError('fill before eligibility')
    if pd.notna(h3) and not (fill < h3): raise AssertionError('fill not before H3')

    return {**base,'status':'FILLED','k1_episode_bars':k1_bars,'h2_bar_start':h2,'h2_episode_bars':h2_bars,
            'leave2_bar_start':leave2,'eligible_start':eligible,'filled':True,'fill_bar_start':fill,
            'h3_bar_start':h3,'h3_after_fill':bool(pd.notna(h3)),'terminal':terminal}


def breakdown_after_h3(x5: pd.DataFrame, w: pd.Series) -> bool:
    if not bool(w.h3_after_fill): return False
    start=pd.Timestamp(w.h3_bar_start)+BAR5; end=pd.Timestamp(w.session_end)
    q=b27ad.fast_slice(x5,start,end)
    for _,r in q.iterrows():
        c=float(r.close)
        if c < float(w.L): return True
        if c > float(w.H): return False
    return False


def synthetic_test() -> None:
    idx=pd.date_range('2026-01-05 13:30',periods=13,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':90.5,'high':91.0,'low':89.8,'close':90.4}, # K1
        {'open':90.4,'high':90.8,'low':89.9,'close':90.3}, # same #1
        {'open':90.3,'high':91.2,'low':90.2,'close':91.0}, # leave1
        {'open':91.0,'high':91.3,'low':89.9,'close':90.2}, # H2
        {'open':90.2,'high':90.9,'low':89.8,'close':90.4}, # same #2
        {'open':90.4,'high':91.0,'low':90.2,'close':90.8}, # leave2
        {'open':90.8,'high':91.7,'low':90.7,'close':91.4}, # eligible F15=91.5 fills
        {'open':91.4,'high':92.0,'low':91.0,'close':91.2},
        {'open':91.2,'high':91.3,'low':89.9,'close':90.2}, # H3
        {'open':90.2,'high':90.3,'low':89.0,'close':89.4}, # breakdown
        {'open':89.4,'high':89.5,'low':87.8,'close':88.2}, # E20
        {'open':88.2,'high':88.4,'low':87.5,'close':87.8},
        {'open':87.8,'high':88.0,'low':87.4,'close':87.7},
    ],index=idx)
    s=pd.Series({'partition':'x','date_utc':'2026-01-05','previous_session_high':100.0,'previous_session_low':90.0,
                 'signal_bar_start':idx[0],'signal_ts':idx[0]+BAR5,'active_session_end':idx[-1]+BAR5})
    # Make exact F15 touch on eligible bar.
    x.loc[idx[6],'high']=91.6
    w=scan_window(x,s)
    assert w['filled'] and w['fill_bar_start']==idx[6] and w['h3_after_fill'] and w['h3_bar_start']==idx[8]


def main() -> None:
    synthetic_test()
    x5,coverage=b27ad.b21.load5(); assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12
    s=b27ad.load_k1()

    # Frozen original #1→#2 E20 hybrid baseline must reproduce before timing-shift interpretation.
    bt=pd.read_csv(BASE)
    e20=bt[(bt.activation.astype(str)=='E20') & bt.partition.isin(MAJOR)].copy()
    assert len(e20)==163
    assert abs(float(pd.to_numeric(e20.net_pnl_usd).sum())-BASE_TOTAL)<1e-9
    assert int(e20.activated.astype(str).str.lower().eq('true').sum())==92

    windows=pd.DataFrame([scan_window(x5,r) for _,r in s.iterrows()])
    assert len(windows)==len(s)
    trades=[]
    for _,w in windows[windows.filled.astype(bool)].iterrows():
        rr=pd.Series({'partition':w.partition,'date_utc':w.date_utc,'signal_ts':w.signal_ts,
                      'fill_bar_start':pd.Timestamp(w.fill_bar_start),'entry_px':float(w.F15),
                      'H':float(w.H),'L':float(w.L),'session_end':pd.Timestamp(w.session_end)})
        z=b27at.hybrid(x5,rr,'E20',0.20)
        z['h2_bar_start']=w.h2_bar_start; z['h3_bar_start']=w.h3_bar_start
        z['h3_after_fill']=bool(w.h3_after_fill); z['pre_h3_terminal']=w.terminal
        z['breakdown_after_h3']=breakdown_after_h3(x5,w)
        trades.append(z)
    tr=pd.DataFrame(trades)

    rows=[]
    for part in (*PARTS,'POOLED_MAJOR'):
        gw=windows[windows.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else windows[windows.partition==part]
        gt=tr[tr.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else tr[tr.partition==part]
        n=len(gt); vals=pd.to_numeric(gt.net_pnl_usd,errors='coerce') if n else pd.Series(dtype=float)
        h3=int(gt.h3_after_fill.sum()) if n else 0
        rows.append({
            'partition':part,'k1_opportunities':len(gw),
            'valid_h2_opportunities':int(gw.h2_bar_start.notna().sum()),
            'clean_post_h2_leave_windows':int(gw.eligible_start.notna().sum()),
            'f15_fills_h2_h3':n,'h3_hits':h3,'h3_rate':h3/n if n else np.nan,
            'breakdown_after_h3':int(gt.breakdown_after_h3.sum()) if n else 0,
            'e20_activated':int(gt.activated.sum()) if n else 0,
            'e20_activation_rate':float(gt.activated.mean()) if n else np.nan,
            'wr':float((vals>0).mean()) if n else np.nan,'pf':pf(vals),'expectancy':float(vals.mean()) if n else np.nan,
            'total_pnl':float(vals.sum()) if n else 0.0,
        })
    sm=pd.DataFrame(rows)

    windows.to_csv(OUT_WINDOWS,index=False); tr.to_csv(OUT_TRADES,index=False); sm.to_csv(OUT_SUM,index=False)
    pool=sm[sm.partition=='POOLED_MAJOR'].iloc[0]
    improved=float(pool.total_pnl)>BASE_TOTAL
    robust=all(float(sm[sm.partition==p].iloc[0].expectancy)>=0 and float(sm[sm.partition==p].iloc[0].pf)>=1.0 for p in MAJOR if int(sm[sm.partition==p].iloc[0].f15_fills_h2_h3)>0)
    status='B27AY_PASS__TIMING_SHIFT_' + ('ROBUSTLY_SUPPORTED' if improved and robust else ('POOLED_IMPROVED_NOT_ROBUST' if improved else 'NOT_SUPPORTED'))
    OUT_STATUS.write_text(status+'\n')

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'
    md=['# B27AY — BTC London->NY SHORT F15 Entry Between Retest #2 and #3 — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Frozen original #1→#2 E20-hybrid baseline reproduced exactly before the timing-shift cohort was interpreted.','',
        f'Original pooled-major #1→#2 baseline: N=163, E20 activated=92, total **${BASE_TOTAL:+.3f}**.','',
        '| Partition | K1 | Valid H2 | Clean leave2 | F15 fills #2→#3 | H3 hits | H3/fill | Break after H3 | E20 act | E20/fill | WR | PF | Exp/trade $ | Total $ |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {int(r.k1_opportunities)} | {int(r.valid_h2_opportunities)} | {int(r.clean_post_h2_leave_windows)} | {int(r.f15_fills_h2_h3)} | {int(r.h3_hits)} | {pct(r.h3_rate)} | {int(r.breakdown_after_h3)} | {int(r.e20_activated)} | {pct(r.e20_activation_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} |')
    md += ['','## Frozen readout','',
           f'Pooled-major timing-shift total: **${float(pool.total_pnl):+.3f}** vs original **${BASE_TOTAL:+.3f}** (delta **${float(pool.total_pnl)-BASE_TOTAL:+.3f}**).',
           f'Pooled-major F15 fills between #2→#3: **{int(pool.f15_fills_h2_h3)}**; H3 rate: **{pct(pool.h3_rate)}**; E20 activation rate: **{pct(pool.e20_activation_rate)}**.',
           '',f'**Status:** `{status}`','',
           'No alternative F fraction, stop, activation, confirmation, regime, threshold, or runner parameter was tested. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__': main()
