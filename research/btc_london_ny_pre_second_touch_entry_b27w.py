#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Result.md'
OUT_WINDOWS = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
OUT_ENTRIES = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
FRACS = {'F95':0.95,'F90':0.90,'F85':0.85,'F80':0.80,'F75':0.75}


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_k1():
    s = pd.read_csv(SIGNALS)
    s = s[(s.transition=='LONDON_TO_NEWYORK') & (s.side=='LONG') & (s.k==1) & (s.opp_visits_at_signal==0)].copy()
    for c in ('signal_ts','signal_bar_start','active_session_end'):
        s[c] = pd.to_datetime(s[c], utc=True)
    return s.sort_values(['partition','signal_ts']).reset_index(drop=True)


def qualifies_high_touch(r, H: float) -> bool:
    return float(r.high) >= H and float(r.close) <= H


def build_window(x5: pd.DataFrame, s: pd.Series) -> dict:
    H = float(s.previous_session_high); L = float(s.previous_session_low)
    sig_start = pd.Timestamp(s.signal_bar_start); sig_ts = pd.Timestamp(s.signal_ts)
    end = pd.Timestamp(s.active_session_end)
    assert H > L

    q = fast_slice(x5, sig_start, end)
    if q.empty or q.index[0] != sig_start:
        raise AssertionError('missing K1 signal bar')
    r0 = q.iloc[0]
    if not (qualifies_high_touch(r0,H) and float(r0.close) >= L):
        raise AssertionError('B27Q K1 bar does not reproduce first High touch')
    if sig_ts != sig_start + BAR5:
        raise AssertionError('unexpected K1 signal timestamp geometry')

    leave_bar_start = pd.NaT; leave_ts = pd.NaT; eligible_start = pd.NaT
    same_episode_bars = 1
    leave_pos = None

    # K1 episode is contiguous. We need a completed non-touch bar before an entry window is causal.
    for k in range(1, len(q)):
        ts = q.index[k]; r = q.iloc[k]; c = float(r.close)
        if c > H:
            return base_window(s,H,L,same_episode_bars,'NO_WINDOW_HIGH_BREAK_DURING_K1',
                               leave_bar_start,leave_ts,eligible_start,pd.NaT,pd.NaT,pd.NaT,pd.NaT)
        if c < L:
            return base_window(s,H,L,same_episode_bars,'NO_WINDOW_LOW_BREAK_DURING_K1',
                               leave_bar_start,leave_ts,eligible_start,pd.NaT,pd.NaT,pd.NaT,pd.NaT)
        if qualifies_high_touch(r,H):
            same_episode_bars += 1
            continue
        leave_bar_start = ts
        leave_ts = ts + BAR5
        eligible_start = leave_ts
        leave_pos = k
        break

    if leave_pos is None:
        return base_window(s,H,L,same_episode_bars,'NO_CAUSAL_LEAVE_BY_SESSION_END',
                           leave_bar_start,leave_ts,eligible_start,pd.NaT,pd.NaT,pd.NaT,pd.NaT)

    # Search only after leave bar completion. H2 is first later arrival to H, even if it breaks out.
    start_pos = leave_pos + 1
    h2_bar_start = pd.NaT; h2_ts = pd.NaT
    opp_bar_start = pd.NaT; opp_ts = pd.NaT
    status = 'NO_H2_BY_SESSION_END'
    terminal_bar_start = pd.NaT

    for k in range(start_pos, len(q)):
        ts = q.index[k]; r = q.iloc[k]
        hit_h = float(r.high) >= H
        break_l = float(r.close) < L
        if hit_h and break_l:
            status = 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
            terminal_bar_start = ts
            break
        if hit_h:
            h2_bar_start = ts; h2_ts = ts + BAR5
            terminal_bar_start = ts
            status = 'H2_ARRIVAL'
            break
        if break_l:
            opp_bar_start = ts; opp_ts = ts + BAR5
            terminal_bar_start = ts
            status = 'OPPOSITE_BREAK_BEFORE_H2'
            break

    return base_window(s,H,L,same_episode_bars,status,leave_bar_start,leave_ts,eligible_start,
                       h2_bar_start,h2_ts,opp_bar_start,opp_ts,terminal_bar_start)


def base_window(s,H,L,same_episode_bars,status,leave_bar_start,leave_ts,eligible_start,
                h2_bar_start,h2_ts,opp_bar_start,opp_ts,terminal_bar_start=pd.NaT):
    return {
        'partition': s.partition,
        'date_utc': s.date_utc,
        'signal_bar_start': pd.Timestamp(s.signal_bar_start),
        'signal_ts': pd.Timestamp(s.signal_ts),
        'session_end': pd.Timestamp(s.active_session_end),
        'H': H, 'L': L,
        'range': H-L,
        'k1_episode_bars': same_episode_bars,
        'window_status': status,
        'leave_bar_start': leave_bar_start,
        'leave_ts': leave_ts,
        'eligible_start': eligible_start,
        'h2_bar_start': h2_bar_start,
        'h2_ts': h2_ts,
        'opposite_break_bar_start': opp_bar_start,
        'opposite_break_ts': opp_ts,
        'terminal_bar_start': terminal_bar_start,
    }


def simulate_entry(x5: pd.DataFrame, w: pd.Series, name: str, frac: float) -> dict:
    H=float(w.H); L=float(w.L); rng=H-L; px=L+frac*rng
    base={'partition':w.partition,'date_utc':w.date_utc,'signal_ts':w.signal_ts,
          'window_status':w.window_status,'entry_name':name,'entry_fraction':frac,
          'planned_entry_px':px,'H':H,'L':L,'eligible_start':w.eligible_start,
          'h2_bar_start':w.h2_bar_start,'opposite_break_bar_start':w.opposite_break_bar_start}

    if pd.isna(w.eligible_start) or w.window_status.startswith('NO_WINDOW') or w.window_status=='NO_CAUSAL_LEAVE_BY_SESSION_END':
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'target_hit':False,
                'terminal':'NO_CLEAN_WINDOW','minutes_to_h2':np.nan,'reward_range_frac':1-frac,
                'min_post_entry_frac':np.nan,'adverse_excursion_range_frac':np.nan}
    if w.window_status == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK':
        # We may still have earlier eligible bars; use the ambiguous bar only as hard terminal and never as fill/target.
        terminal_start = pd.Timestamp(w.terminal_bar_start)
    elif w.window_status == 'H2_ARRIVAL':
        terminal_start = pd.Timestamp(w.h2_bar_start)
    elif w.window_status == 'OPPOSITE_BREAK_BEFORE_H2':
        terminal_start = pd.Timestamp(w.opposite_break_bar_start)
    else:
        terminal_start = pd.Timestamp(w.session_end)

    q = fast_slice(x5, pd.Timestamp(w.eligible_start), terminal_start)
    fill_ts=pd.NaT; fill_pos=None
    for k,(ts,r) in enumerate(q.iterrows()):
        if float(r.close) < L:
            raise AssertionError('opposite break appeared inside pre-terminal eligible slice')
        if float(r.high) >= H:
            raise AssertionError('H2 appeared inside pre-terminal eligible slice')
        if float(r.low) <= px <= float(r.high):
            fill_ts=ts; fill_pos=k; break

    if fill_pos is None:
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'target_hit':False,
                'terminal':w.window_status,'minutes_to_h2':np.nan,'reward_range_frac':1-frac,
                'min_post_entry_frac':np.nan,'adverse_excursion_range_frac':np.nan}

    # Entry must be strictly before the terminal/H2 bar.
    if not (pd.Timestamp(fill_ts) < terminal_start):
        raise AssertionError('entry is not strictly before terminal/H2 bar')

    post = q.iloc[fill_pos:]
    min_low = float(post.low.min()) if len(post) else px
    min_frac = (min_low-L)/rng
    adverse = max(0.0, frac-min_frac)
    target = bool(w.window_status=='H2_ARRIVAL')
    mins = float((pd.Timestamp(w.h2_bar_start)-pd.Timestamp(fill_ts))/pd.Timedelta(minutes=1)) if target else np.nan
    return {**base,'filled':True,'entry_ts':fill_ts,'entry_px':px,'target_hit':target,
            'terminal':w.window_status,'minutes_to_h2':mins,'reward_range_frac':1-frac,
            'min_post_entry_frac':min_frac,'adverse_excursion_range_frac':adverse}


def synthetic_tests():
    H,L=100.0,90.0
    idx=pd.date_range('2026-01-02 13:30',periods=8,freq='5min',tz='UTC')
    # K1 spans two bars, then leave, then pullback, then H2 revisit.
    q=pd.DataFrame([
        {'open':99,'high':100.2,'low':98,'close':99.5},
        {'open':99.5,'high':100.1,'low':98.5,'close':99.2},
        {'open':99.2,'high':99.6,'low':97.0,'close':98.0},  # causal leave completes here
        {'open':98.0,'high':98.5,'low':96.0,'close':97.0},  # first eligible bar
        {'open':97.0,'high':99.0,'low':95.0,'close':98.5},
        {'open':98.5,'high':100.4,'low':98.0,'close':99.8}, # H2
        {'open':99.8,'high':101,'low':99,'close':100.5},
        {'open':100.5,'high':101,'low':100,'close':100.8},
    ],index=idx)
    s=pd.Series({'partition':'x','date_utc':'2026-01-02','previous_session_high':H,'previous_session_low':L,
                 'signal_bar_start':idx[0],'signal_ts':idx[0]+BAR5,'active_session_end':idx[-1]+BAR5})
    w=build_window(q,s)
    assert w['k1_episode_bars']==2
    assert w['leave_bar_start']==idx[2] and w['eligible_start']==idx[3]
    assert w['window_status']=='H2_ARRIVAL' and w['h2_bar_start']==idx[5]
    e=simulate_entry(q,pd.Series(w),'F75',0.75)
    assert e['filled'] and e['entry_ts']<idx[5] and e['target_hit']

    # Second arrival can itself close above H and still counts as H2.
    q2=q.copy(); q2.loc[idx[5],'close']=100.3
    w2=build_window(q2,s)
    assert w2['window_status']=='H2_ARRIVAL' and w2['h2_bar_start']==idx[5]

    # No H2 by end remains a valid clean window, not a target.
    q3=q.iloc[:5].copy()
    s3=s.copy(); s3['active_session_end']=idx[5]
    w3=build_window(q3,s3)
    assert w3['window_status']=='NO_H2_BY_SESSION_END'


def summarize(g: pd.DataFrame) -> dict:
    clean = g[~g.window_status.isin(['NO_CLEAN_WINDOW'])]
    f = g[g.filled.astype(bool)].copy()
    return {
        'setups': int(len(g)),
        'fills': int(len(f)),
        'fill_rate': float(len(f)/len(g)) if len(g) else np.nan,
        'target_hits': int(f.target_hit.sum()) if len(f) else 0,
        'target_hit_rate': float(f.target_hit.mean()) if len(f) else np.nan,
        'median_minutes_to_h2': float(f.loc[f.target_hit,'minutes_to_h2'].median()) if f.target_hit.any() else np.nan,
        'median_reward_range_frac': float(f.reward_range_frac.median()) if len(f) else np.nan,
        'median_min_post_entry_frac': float(f.min_post_entry_frac.median()) if len(f) else np.nan,
        'p10_min_post_entry_frac': float(f.min_post_entry_frac.quantile(.10)) if len(f) else np.nan,
        'median_adverse_excursion_range_frac': float(f.adverse_excursion_range_frac.median()) if len(f) else np.nan,
    }


def pct(x): return '-' if pd.isna(x) else f'{100*x:.1f}%'
def num(x): return '-' if pd.isna(x) else f'{float(x):.2f}'


def main():
    synthetic_tests()
    x5,coverage=b21.load5(); s=load_k1()
    windows=pd.DataFrame([build_window(x5,r) for _,r in s.iterrows()])
    # Identity: exactly one window per frozen B27Q K1 OPP0 signal.
    assert len(windows)==len(s)
    assert list(pd.to_datetime(windows.signal_ts,utc=True))==list(pd.to_datetime(s.signal_ts,utc=True))

    # Cross-check normal non-breakout H2 visits against frozen B27Q K2 when one exists.
    allsig=pd.read_csv(SIGNALS)
    k2=allsig[(allsig.transition=='LONDON_TO_NEWYORK')&(allsig.side=='LONG')&(allsig.k==2)].copy()
    k2['signal_bar_start']=pd.to_datetime(k2.signal_bar_start,utc=True)
    k2map={(str(r.partition),str(r.date_utc)):pd.Timestamp(r.signal_bar_start) for r in k2.itertuples(index=False)}
    for w in windows.itertuples(index=False):
        if w.window_status=='H2_ARRIVAL':
            bar=x5.loc[pd.Timestamp(w.h2_bar_start)]
            if float(bar.close)<=float(w.H):
                key=(str(w.partition),str(w.date_utc))
                if key in k2map:
                    assert pd.Timestamp(w.h2_bar_start)==k2map[key]

    entries=[]
    for _,w in windows.iterrows():
        for name,frac in FRACS.items():
            entries.append(simulate_entry(x5,w,name,frac))
    e=pd.DataFrame(entries)

    # Hard chronology assertions.
    for r in e[e.filled.astype(bool)].itertuples(index=False):
        assert pd.Timestamp(r.entry_ts) >= pd.Timestamp(r.eligible_start)
        if pd.notna(r.h2_bar_start):
            assert pd.Timestamp(r.entry_ts) < pd.Timestamp(r.h2_bar_start)
        expected=float(r.L)+float(r.entry_fraction)*(float(r.H)-float(r.L))
        assert abs(float(r.entry_px)-expected)<1e-9*max(1.0,abs(expected))

    windows.to_csv(OUT_WINDOWS,index=False)
    e.to_csv(OUT_ENTRIES,index=False)
    pd.DataFrame(windows.window_status.value_counts()).to_csv(OUT_STATUS)

    sums=[]
    for part in PARTS:
        for name in FRACS:
            g=e[(e.partition==part)&(e.entry_name==name)]
            sums.append({'partition':part,'entry_name':name,**summarize(g)})
    sm=pd.DataFrame(sums)
    passes={}
    for name in FRACS:
        z=sm[(sm.entry_name==name)&(sm.partition.isin(MAJOR))]
        passes[name]=bool(len(z)==3 and (z.fills>=30).all() and (z.target_hit_rate>=0.70).all())
    sm['screen_pass']=sm.entry_name.map(passes)
    sm.to_csv(OUT_SUM,index=False)

    # Window-level diagnostics independent of entry level.
    wd=[]
    for part in PARTS:
        g=windows[windows.partition==part]
        clean=g[g.eligible_start.notna() & (g.window_status!='AMBIGUOUS_H2_VS_OPPOSITE_BREAK')]
        wd.append((part,len(g),len(clean),float((clean.window_status=='H2_ARRIVAL').mean()) if len(clean) else np.nan,
                   int((clean.window_status=='H2_ARRIVAL').sum()),int((clean.window_status=='OPPOSITE_BREAK_BEFORE_H2').sum()),int((clean.window_status=='NO_H2_BY_SESSION_END').sum())))

    md=['# B27W — London -> New York Pre-Second-Touch Entry — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** Frozen B27Q K1 OPP0 signals were reused unchanged. Entry is only allowed after a causal leave from Touch #1 and strictly before the first later return/arrival to High.','',
        '## Window diagnostic','',
        '| Partition | K1 setups | Clean windows | H2 probability | H2 | Opp break first | No H2 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for part,n,c,p,h,o,no in wd:
        md.append(f'| {part} | {n} | {c} | {pct(p)} | {h} | {o} | {no} |')
    md += ['','## Pre-H2 limit-entry grid','',
           '| Partition | Entry | Fills | Fill rate | H2 hit rate after fill | Median min to H2 | Reward to H | Median min price f | P10 min price f | Median adverse excursion |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_name} | {r.fills} | {pct(r.fill_rate)} | {pct(r.target_hit_rate)} | {num(r.median_minutes_to_h2)} | {pct(r.median_reward_range_frac)} | {num(r.median_min_post_entry_frac)} | {num(r.p10_min_post_entry_frac)} | {pct(r.median_adverse_excursion_range_frac)} |')
    md += ['','## Screen','']
    good=[k for k,v in passes.items() if v]
    md.append('**PASS:** '+', '.join(good) if good else '**No frozen pre-H2 level passed the three-partition discovery screen.**')
    md += ['','This experiment isolates entry availability/quality before the second High arrival. It does not optimize stops and is not a live-promotion test.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')


if __name__=='__main__':
    main()
