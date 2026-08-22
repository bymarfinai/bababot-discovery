#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_london_ny_short_post_h2_equal_distance_stop_b27bc as b27bc

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Result.md'
OUT_DAYS = ROOT / 'BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Days.csv'
OUT_SETUPS = ROOT / 'BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Setups.csv'
OUT_TRADES = ROOT / 'BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Trades.csv'
OUT_SUM = ROOT / 'BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Summary.csv'
OUT_STATUS = ROOT / 'BTC_NY_POSTNY_OFFSESSION_SHORT_B27BD_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = b22b.PARTS
MAJOR = ('external','development','reference_validation')
ENTRY_F = 0.15
DIST = 0.30
NY_START = (13,30)
NY_END = (20,0)
OBS_START = (20,0)
OBS_END_NEXT_DAY = (0,0)
EPS = 1e-12


def ts(day: pd.Timestamp, hh: int, mm: int) -> pd.Timestamp:
    return pd.Timestamp(day.date(), tz='UTC') + pd.Timedelta(hours=hh, minutes=mm)


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def hit_low(r, L: float) -> bool:
    return float(r.low) <= L and float(r.close) >= L


def hit_high(r, H: float) -> bool:
    return float(r.high) >= H and float(r.close) <= H


def raw_diag(q: pd.DataFrame, H: float, L: float) -> dict:
    ret_bp = (float(q.iloc[-1].close) / float(q.iloc[0].open) - 1.0) * 1e4
    hb = False; lb = False; first = 'NO_BREAK'; first_ts = pd.NaT
    for t, r in q.iterrows():
        bh = float(r.close) > H
        bl = float(r.close) < L
        assert not (bh and bl)
        hb = hb or bh; lb = lb or bl
        if first == 'NO_BREAK' and (bh or bl):
            first = 'HIGH' if bh else 'LOW'
            first_ts = t + BAR5
    return {'off_return_bp':ret_bp,'close_break_high':hb,'close_break_low':lb,
            'first_close_break':first,'first_close_break_ts':first_ts}


def consume_episode(q: pd.DataFrame, start_i: int, L: float) -> int:
    j = start_i
    while j + 1 < len(q) and hit_low(q.iloc[j+1], L):
        j += 1
    return j


def scan_setup(q: pd.DataFrame, H: float, L: float, partition: str, date_utc: str,
               session_end: pd.Timestamp) -> dict:
    R = H - L
    F15 = L + ENTRY_F * R
    base = {'partition':partition,'date_utc':date_utc,'H':H,'L':L,'range':R,
            'F15':F15,'session_end':session_end,'status':None,
            'touch1_bar_start':pd.NaT,'leave1_bar_start':pd.NaT,
            'touch2_bar_start':pd.NaT,'leave2_bar_start':pd.NaT,
            'eligible_start':pd.NaT,'fill_bar_start':pd.NaT,'entry_px':np.nan,
            'opp_visit_before_t1':False}
    assert R > 0

    # Touch #1 with K1-like OPP0 purity.
    opp = False; t1 = None
    for i, (t, r) in enumerate(q.iterrows()):
        bh = float(r.close) > H; bl = float(r.close) < L
        if bh or bl:
            return {**base,'status':'BREAK_BEFORE_T1','opp_visit_before_t1':opp}
        hl = hit_low(r,L); hh = hit_high(r,H)
        if hl and hh:
            return {**base,'status':'AMBIGUOUS_BOTH_AT_T1','opp_visit_before_t1':opp}
        if hh: opp = True
        if hl:
            if opp:
                return {**base,'status':'T1_NOT_OPP0','touch1_bar_start':t,'opp_visit_before_t1':True}
            t1 = i; break
    if t1 is None:
        return {**base,'status':'NO_T1','opp_visit_before_t1':opp}

    t1_end = consume_episode(q,t1,L)
    # Causal leave after touch #1.
    leave1 = None
    for j in range(t1_end+1, len(q)):
        r=q.iloc[j]; t=q.index[j]
        if float(r.close) < L or float(r.close) > H:
            return {**base,'status':'BREAK_BEFORE_LEAVE1','touch1_bar_start':q.index[t1]}
        if hit_low(r,L):
            raise AssertionError('touch episode was not fully consumed')
        leave1=j; break
    if leave1 is None:
        return {**base,'status':'NO_LEAVE1','touch1_bar_start':q.index[t1]}

    # Distinct valid touch #2 after the completed leave bar.
    t2=None
    for j in range(leave1+1,len(q)):
        r=q.iloc[j]; t=q.index[j]
        if float(r.close) < L:
            return {**base,'status':'LOW_BREAK_BEFORE_T2','touch1_bar_start':q.index[t1],'leave1_bar_start':q.index[leave1]}
        if float(r.close) > H:
            return {**base,'status':'HIGH_BREAK_BEFORE_T2','touch1_bar_start':q.index[t1],'leave1_bar_start':q.index[leave1]}
        hl=hit_low(r,L); hh=hit_high(r,H)
        if hl and hh:
            return {**base,'status':'AMBIGUOUS_BOTH_AT_T2','touch1_bar_start':q.index[t1],'leave1_bar_start':q.index[leave1]}
        if hl:
            t2=j; break
    if t2 is None:
        return {**base,'status':'NO_T2','touch1_bar_start':q.index[t1],'leave1_bar_start':q.index[leave1]}

    t2_end=consume_episode(q,t2,L)
    leave2=None
    for j in range(t2_end+1,len(q)):
        r=q.iloc[j]
        if float(r.close) < L or float(r.close) > H:
            return {**base,'status':'BREAK_BEFORE_LEAVE2','touch1_bar_start':q.index[t1],
                    'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2]}
        if hit_low(r,L):
            raise AssertionError('touch2 episode was not fully consumed')
        leave2=j; break
    if leave2 is None:
        return {**base,'status':'NO_LEAVE2','touch1_bar_start':q.index[t1],
                'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2]}

    eligible_i=leave2+1
    eligible_start = q.index[leave2] + BAR5
    assert eligible_i >= len(q) or q.index[eligible_i] == eligible_start
    if eligible_i >= len(q):
        return {**base,'status':'NO_BAR_AFTER_LEAVE2','touch1_bar_start':q.index[t1],
                'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2],
                'leave2_bar_start':q.index[leave2],'eligible_start':eligible_start}

    fill=None
    for j in range(eligible_i,len(q)):
        r=q.iloc[j]; t=q.index[j]
        # Next Low revisit/direct breakdown terminates before any ambiguous same-bar F15 fill.
        if float(r.low) <= L:
            return {**base,'status':'LOW_REVISIT_BEFORE_F15','touch1_bar_start':q.index[t1],
                    'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2],
                    'leave2_bar_start':q.index[leave2],'eligible_start':eligible_start}
        if float(r.close) > H:
            return {**base,'status':'HIGH_BREAK_BEFORE_F15','touch1_bar_start':q.index[t1],
                    'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2],
                    'leave2_bar_start':q.index[leave2],'eligible_start':eligible_start}
        if float(r.low) <= F15 <= float(r.high):
            fill=j; break
    if fill is None:
        return {**base,'status':'NO_F15_FILL','touch1_bar_start':q.index[t1],
                'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2],
                'leave2_bar_start':q.index[leave2],'eligible_start':eligible_start}

    assert q.index[t1] < q.index[leave1] < q.index[t2] < q.index[leave2] < q.index[fill]
    return {**base,'status':'F15_FILLED','touch1_bar_start':q.index[t1],
            'leave1_bar_start':q.index[leave1],'touch2_bar_start':q.index[t2],
            'leave2_bar_start':q.index[leave2],'eligible_start':eligible_start,
            'fill_bar_start':q.index[fill],'entry_px':F15}


def pf(vals) -> float:
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna()
    pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg==0 and pos>0: return float('inf')
    return pos/neg if neg>0 else np.nan


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12

    days=[]; setups=[]; trades=[]
    for part,(pstart,pend) in PARTS.items():
        first=pstart.normalize(); last=(pend-pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first,last,freq='D',tz='UTC'):
            if day.weekday()>=5: continue
            ns=ts(day,13,30); ne=ts(day,20,0); os=ne; oe=day.normalize()+pd.Timedelta(days=1)
            if ns < pstart or oe > pend: continue
            src=fast_slice(x5,ns,ne); obs=fast_slice(x5,os,oe)
            if len(src)!=78 or len(obs)!=48: continue
            H=float(src.high.max()); L=float(src.low.min()); assert H>L
            d={'partition':part,'date_utc':str(day.date()),'source_start':ns,'source_end':ne,
               'obs_start':os,'obs_end':oe,'H':H,'L':L,'range':H-L,**raw_diag(obs,H,L)}
            days.append(d)
            s=scan_setup(obs,H,L,part,str(day.date()),oe)
            setups.append(s)
            if s['status']=='F15_FILLED':
                r=pd.Series({'zone':'F15','entry_frac':ENTRY_F,'partition':part,'date_utc':str(day.date()),
                             'signal_ts':pd.Timestamp(s['touch2_bar_start'])+BAR5,
                             'fill_bar_start':pd.Timestamp(s['fill_bar_start']),'entry_px':float(s['entry_px']),
                             'H':H,'L':L,'session_end':oe})
                z=b27bc.hard_stop_hybrid(x5,r,'D30',DIST)
                z['source_transition']='NY_TO_POSTNY_OFFSESSION'
                trades.append(z)

    dd=pd.DataFrame(days); ss=pd.DataFrame(setups); tr=pd.DataFrame(trades)
    dd.to_csv(OUT_DAYS,index=False); ss.to_csv(OUT_SETUPS,index=False); tr.to_csv(OUT_TRADES,index=False)

    # Raw direction summary and setup economics.
    rows=[]
    for part in (*PARTS,'POOLED_MAJOR'):
        gd=dd[dd.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else dd[dd.partition==part]
        gt=tr[tr.partition.isin(MAJOR)] if (part=='POOLED_MAJOR' and len(tr)) else (tr[tr.partition==part] if len(tr) else pd.DataFrame())
        vals=pd.to_numeric(gt.net_pnl_usd,errors='coerce') if len(gt) else pd.Series(dtype=float)
        rows.append({'partition':part,'complete_days':len(gd),
                     'down_day_rate':float((gd.off_return_bp<0).mean()) if len(gd) else np.nan,
                     'mean_return_bp':float(gd.off_return_bp.mean()) if len(gd) else np.nan,
                     'median_return_bp':float(gd.off_return_bp.median()) if len(gd) else np.nan,
                     'break_high_rate':float(gd.close_break_high.mean()) if len(gd) else np.nan,
                     'break_low_rate':float(gd.close_break_low.mean()) if len(gd) else np.nan,
                     'first_high_rate':float((gd.first_close_break=='HIGH').mean()) if len(gd) else np.nan,
                     'first_low_rate':float((gd.first_close_break=='LOW').mean()) if len(gd) else np.nan,
                     'no_break_rate':float((gd.first_close_break=='NO_BREAK').mean()) if len(gd) else np.nan,
                     'setup_n':len(gt),'activation_n':int(gt.activated.sum()) if len(gt) else 0,
                     'activation_rate':float(gt.activated.mean()) if len(gt) else np.nan,
                     'wr':float((vals>0).mean()) if len(gt) else np.nan,
                     'pf':pf(vals) if len(gt) else np.nan,
                     'expectancy':float(vals.mean()) if len(gt) else np.nan,
                     'total_pnl':float(vals.sum()) if len(gt) else 0.0})
    sm=pd.DataFrame(rows); sm.to_csv(OUT_SUM,index=False)

    major_rows=sm[sm.partition.isin(MAJOR)]
    pool=sm[sm.partition=='POOLED_MAJOR'].iloc[0]
    robust=bool(int(pool.setup_n)>0 and float(pool.expectancy)>0 and float(pool.pf)>=1.20 and
                (major_rows.setup_n>=5).all() and (major_rows.expectancy>=0).all() and (major_rows.pf>=1.0).all())
    status='B27BD_ROBUST_SUPPORTED' if robust else 'B27BD_NOT_ROBUST'
    OUT_STATUS.write_text(status+'\n')

    def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
    def num(v,d=3):
        if pd.isna(v): return '-'
        if math.isinf(float(v)): return 'inf'
        return f'{float(v):.{d}f}'

    counts=ss.status.value_counts().to_dict() if len(ss) else {}
    lines=['# B27BD — BTC NY -> Post-NY Off-Session SHORT Audit — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
           '**Audit status: PASS.** The NY range was frozen only after 20:00 UTC; observation used complete 20:00-24:00 UTC weekday blocks.','',
           'Only the time/source-session geometry changed versus the current leading SHORT candidate: NY H/L -> post-NY off-session. Entry remained F15 after two distinct Low retests, hard stop D30, E20 full-position hybrid.','',
           '## Raw post-NY direction census','',
           '| Partition | Days | Down days | Mean bp | Median bp | Close>NY H | Close<NY L | High first | Low first | No break |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in (*PARTS,'POOLED_MAJOR'):
        r=sm[sm.partition==p].iloc[0]
        lines.append(f'| {p} | {int(r.complete_days)} | {pct(r.down_day_rate)} | {num(r.mean_return_bp,2)} | {num(r.median_return_bp,2)} | {pct(r.break_high_rate)} | {pct(r.break_low_rate)} | {pct(r.first_high_rate)} | {pct(r.first_low_rate)} | {pct(r.no_break_rate)} |')
    lines += ['','## Current SHORT candidate shifted to off-session','',
              '| Partition | N | E20 act | Act rate | WR | PF | Exp/trade $ | Total $ |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in (*PARTS,'POOLED_MAJOR'):
        r=sm[sm.partition==p].iloc[0]
        lines.append(f'| {p} | {int(r.setup_n)} | {int(r.activation_n)} | {pct(r.activation_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} |')
    lines += ['','## Setup census','']
    for k,v in sorted(counts.items(), key=lambda kv:(-kv[1],kv[0])):
        lines.append(f'- {k}: {v}')
    lines += ['',f'**Frozen support verdict: {status}.**','',
              'No regime, alternate entry zone, alternate stop distance, or alternate activation threshold was searched. Weekends were not included in this audit.','',
              'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
