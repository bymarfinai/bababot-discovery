#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_PRE_SECOND_TOUCH_ENTRY_B27BQ_Result.md'
OUT_WINDOWS = ROOT / 'BTC_LONDON_NY_SHORT_PRE_SECOND_TOUCH_ENTRY_B27BQ_Windows.csv'
OUT_ENTRIES = ROOT / 'BTC_LONDON_NY_SHORT_PRE_SECOND_TOUCH_ENTRY_B27BQ_Entries.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_PRE_SECOND_TOUCH_ENTRY_B27BQ_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_PRE_SECOND_TOUCH_ENTRY_B27BQ_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
FRACS = {'F05':0.05,'F10':0.10,'F15':0.15,'F20':0.20,'F25':0.25}


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_k1() -> pd.DataFrame:
    s = pd.read_csv(SIGNALS)
    s = s[(s.transition=='LONDON_TO_NEWYORK') & (s.side=='SHORT') & (s.k==1) & (s.opp_visits_at_signal==0)].copy()
    for c in ('signal_ts','signal_bar_start','active_session_end'):
        s[c] = pd.to_datetime(s[c], utc=True)
    return s.sort_values(['partition','signal_ts']).reset_index(drop=True)


def qualifies_low_touch(r, L: float) -> bool:
    return float(r.low) <= L and float(r.close) >= L


def base_window(s,H,L,same_episode_bars,status,leave_bar_start,leave_ts,eligible_start,
                l2_bar_start,l2_ts,opp_bar_start,opp_ts,terminal_bar_start=pd.NaT):
    return {
        'partition': s.partition,
        'date_utc': s.date_utc,
        'signal_bar_start': pd.Timestamp(s.signal_bar_start),
        'signal_ts': pd.Timestamp(s.signal_ts),
        'session_end': pd.Timestamp(s.active_session_end),
        'H': H, 'L': L, 'range': H-L,
        'k1_episode_bars': same_episode_bars,
        'window_status': status,
        'leave_bar_start': leave_bar_start,
        'leave_ts': leave_ts,
        'eligible_start': eligible_start,
        'l2_bar_start': l2_bar_start,
        'l2_ts': l2_ts,
        'opposite_break_bar_start': opp_bar_start,
        'opposite_break_ts': opp_ts,
        'terminal_bar_start': terminal_bar_start,
    }


def build_window(x5: pd.DataFrame, s: pd.Series) -> dict:
    H = float(s.previous_session_high); L = float(s.previous_session_low)
    sig_start = pd.Timestamp(s.signal_bar_start); sig_ts = pd.Timestamp(s.signal_ts)
    end = pd.Timestamp(s.active_session_end)
    assert H > L

    q = fast_slice(x5, sig_start, end)
    if q.empty or q.index[0] != sig_start:
        raise AssertionError('missing K1 signal bar')
    r0 = q.iloc[0]
    if not (qualifies_low_touch(r0,L) and float(r0.close) <= H):
        raise AssertionError('B27Q K1 bar does not reproduce first Low touch')
    if sig_ts != sig_start + BAR5:
        raise AssertionError('unexpected K1 signal timestamp geometry')

    leave_bar_start = pd.NaT; leave_ts = pd.NaT; eligible_start = pd.NaT
    same_episode_bars = 1; leave_pos = None

    for k in range(1, len(q)):
        ts = q.index[k]; r = q.iloc[k]; c = float(r.close)
        if c < L:
            return base_window(s,H,L,same_episode_bars,'NO_WINDOW_LOW_BREAK_DURING_K1',
                               leave_bar_start,leave_ts,eligible_start,pd.NaT,pd.NaT,pd.NaT,pd.NaT)
        if c > H:
            return base_window(s,H,L,same_episode_bars,'NO_WINDOW_HIGH_BREAK_DURING_K1',
                               leave_bar_start,leave_ts,eligible_start,pd.NaT,pd.NaT,pd.NaT,pd.NaT)
        if qualifies_low_touch(r,L):
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

    start_pos = leave_pos + 1
    l2_bar_start = pd.NaT; l2_ts = pd.NaT
    opp_bar_start = pd.NaT; opp_ts = pd.NaT
    status = 'NO_L2_BY_SESSION_END'; terminal_bar_start = pd.NaT

    for k in range(start_pos, len(q)):
        ts = q.index[k]; r = q.iloc[k]
        hit_l = float(r.low) <= L
        break_h = float(r.close) > H
        if hit_l and break_h:
            status = 'AMBIGUOUS_L2_VS_OPPOSITE_BREAK'; terminal_bar_start = ts; break
        if hit_l:
            l2_bar_start = ts; l2_ts = ts + BAR5
            status = 'L2_ARRIVAL'; terminal_bar_start = ts; break
        if break_h:
            opp_bar_start = ts; opp_ts = ts + BAR5
            status = 'OPPOSITE_BREAK_BEFORE_L2'; terminal_bar_start = ts; break

    return base_window(s,H,L,same_episode_bars,status,leave_bar_start,leave_ts,eligible_start,
                       l2_bar_start,l2_ts,opp_bar_start,opp_ts,terminal_bar_start)


def simulate_entry(x5: pd.DataFrame, w: pd.Series, name: str, frac: float) -> dict:
    H=float(w.H); L=float(w.L); rng=H-L; px=L+frac*rng
    base={'partition':w.partition,'date_utc':w.date_utc,'signal_ts':w.signal_ts,
          'window_status':w.window_status,'entry_name':name,'entry_fraction':frac,
          'planned_entry_px':px,'H':H,'L':L,'eligible_start':w.eligible_start,
          'l2_bar_start':w.l2_bar_start,'opposite_break_bar_start':w.opposite_break_bar_start}

    if pd.isna(w.eligible_start) or str(w.window_status).startswith('NO_WINDOW') or w.window_status=='NO_CAUSAL_LEAVE_BY_SESSION_END':
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'target_hit':False,
                'terminal':'NO_CLEAN_WINDOW','minutes_to_l2':np.nan,'reward_range_frac':frac,
                'max_post_entry_frac':np.nan,'adverse_excursion_range_frac':np.nan}

    if w.window_status == 'AMBIGUOUS_L2_VS_OPPOSITE_BREAK':
        terminal_start = pd.Timestamp(w.terminal_bar_start)
    elif w.window_status == 'L2_ARRIVAL':
        terminal_start = pd.Timestamp(w.l2_bar_start)
    elif w.window_status == 'OPPOSITE_BREAK_BEFORE_L2':
        terminal_start = pd.Timestamp(w.opposite_break_bar_start)
    else:
        terminal_start = pd.Timestamp(w.session_end)

    q = fast_slice(x5, pd.Timestamp(w.eligible_start), terminal_start)
    fill_ts=pd.NaT; fill_pos=None
    for k,(ts,r) in enumerate(q.iterrows()):
        if float(r.close) > H:
            raise AssertionError('opposite break appeared inside pre-terminal eligible slice')
        if float(r.low) <= L:
            raise AssertionError('L2 appeared inside pre-terminal eligible slice')
        if float(r.low) <= px <= float(r.high):
            fill_ts=ts; fill_pos=k; break

    if fill_pos is None:
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'target_hit':False,
                'terminal':w.window_status,'minutes_to_l2':np.nan,'reward_range_frac':frac,
                'max_post_entry_frac':np.nan,'adverse_excursion_range_frac':np.nan}

    if not (pd.Timestamp(fill_ts) < terminal_start):
        raise AssertionError('entry is not strictly before terminal/L2 bar')

    post = q.iloc[fill_pos:]
    max_high = float(post.high.max()) if len(post) else px
    max_frac = (max_high-L)/rng
    adverse = max(0.0, max_frac-frac)
    target = bool(w.window_status=='L2_ARRIVAL')
    mins = float((pd.Timestamp(w.l2_bar_start)-pd.Timestamp(fill_ts))/pd.Timedelta(minutes=1)) if target else np.nan
    return {**base,'filled':True,'entry_ts':fill_ts,'entry_px':px,'target_hit':target,
            'terminal':w.window_status,'minutes_to_l2':mins,'reward_range_frac':frac,
            'max_post_entry_frac':max_frac,'adverse_excursion_range_frac':adverse}


def synthetic_tests():
    H,L=100.0,90.0
    idx=pd.date_range('2026-01-02 13:30',periods=8,freq='5min',tz='UTC')
    q=pd.DataFrame([
        {'open':91,'high':92,'low':89.8,'close':90.5},
        {'open':90.5,'high':92,'low':89.9,'close':90.8},
        {'open':90.8,'high':93,'low':90.4,'close':92.0},
        {'open':92.0,'high':94,'low':91.0,'close':93.0},
        {'open':93.0,'high':95,'low':91.2,'close':92.0},
        {'open':92.0,'high':92.5,'low':89.7,'close':90.2},
        {'open':90.2,'high':91,'low':89,'close':89.5},
        {'open':89.5,'high':90,'low':88,'close':88.5},
    ],index=idx)
    s=pd.Series({'partition':'x','date_utc':'2026-01-02','previous_session_high':H,'previous_session_low':L,
                 'signal_bar_start':idx[0],'signal_ts':idx[0]+BAR5,'active_session_end':idx[-1]+BAR5})
    w=build_window(q,s)
    assert w['k1_episode_bars']==2
    assert w['leave_bar_start']==idx[2] and w['eligible_start']==idx[3]
    assert w['window_status']=='L2_ARRIVAL' and w['l2_bar_start']==idx[5]
    e=simulate_entry(q,pd.Series(w),'F15',0.15)
    assert e['filled'] and e['entry_ts']<idx[5] and e['target_hit']

    q2=q.copy(); q2.loc[idx[5],'close']=89.6
    w2=build_window(q2,s)
    assert w2['window_status']=='L2_ARRIVAL' and w2['l2_bar_start']==idx[5]

    q3=q.iloc[:5].copy(); s3=s.copy(); s3['active_session_end']=idx[5]
    w3=build_window(q3,s3)
    assert w3['window_status']=='NO_L2_BY_SESSION_END'

    q4=q.copy(); q4.loc[idx[4],'low']=94.0; q4.loc[idx[4],'close']=100.5
    w4=build_window(q4,s)
    assert w4['window_status']=='OPPOSITE_BREAK_BEFORE_L2'


def summarize(g: pd.DataFrame) -> dict:
    f = g[g.filled.astype(bool)].copy()
    return {
        'setups': int(len(g)),
        'fills': int(len(f)),
        'fill_rate': float(len(f)/len(g)) if len(g) else np.nan,
        'target_hits': int(f.target_hit.sum()) if len(f) else 0,
        'target_hit_rate': float(f.target_hit.mean()) if len(f) else np.nan,
        'median_minutes_to_l2': float(f.loc[f.target_hit,'minutes_to_l2'].median()) if len(f) and f.target_hit.any() else np.nan,
        'median_reward_range_frac': float(f.reward_range_frac.median()) if len(f) else np.nan,
        'median_max_post_entry_frac': float(f.max_post_entry_frac.median()) if len(f) else np.nan,
        'p90_max_post_entry_frac': float(f.max_post_entry_frac.quantile(.90)) if len(f) else np.nan,
        'median_adverse_excursion_range_frac': float(f.adverse_excursion_range_frac.median()) if len(f) else np.nan,
    }


def pct(x): return '-' if pd.isna(x) else f'{100*x:.1f}%'
def num(x): return '-' if pd.isna(x) else f'{float(x):.2f}'


def main():
    synthetic_tests()
    x5,coverage=b21.load5(); s=load_k1()
    windows=pd.DataFrame([build_window(x5,r) for _,r in s.iterrows()])
    assert len(windows)==len(s)
    assert list(pd.to_datetime(windows.signal_ts,utc=True))==list(pd.to_datetime(s.signal_ts,utc=True))

    # Cross-check normal non-breakout L2 visits against frozen B27Q SHORT K2 when available.
    allsig=pd.read_csv(SIGNALS)
    k2=allsig[(allsig.transition=='LONDON_TO_NEWYORK')&(allsig.side=='SHORT')&(allsig.k==2)].copy()
    k2['signal_bar_start']=pd.to_datetime(k2.signal_bar_start,utc=True)
    k2map={(str(r.partition),str(r.date_utc)):pd.Timestamp(r.signal_bar_start) for r in k2.itertuples(index=False)}
    for w in windows.itertuples(index=False):
        if w.window_status=='L2_ARRIVAL':
            bar=x5.loc[pd.Timestamp(w.l2_bar_start)]
            if float(bar.close)>=float(w.L):
                key=(str(w.partition),str(w.date_utc))
                if key in k2map:
                    assert pd.Timestamp(w.l2_bar_start)==k2map[key]

    entries=[]
    for _,w in windows.iterrows():
        for name,frac in FRACS.items():
            entries.append(simulate_entry(x5,w,name,frac))
    e=pd.DataFrame(entries)

    for r in e[e.filled.astype(bool)].itertuples(index=False):
        assert pd.Timestamp(r.entry_ts) >= pd.Timestamp(r.eligible_start)
        if pd.notna(r.l2_bar_start):
            assert pd.Timestamp(r.entry_ts) < pd.Timestamp(r.l2_bar_start)
        expected=float(r.L)+float(r.entry_fraction)*(float(r.H)-float(r.L))
        assert abs(float(r.entry_px)-expected)<1e-9*max(1.0,abs(expected))

    windows.to_csv(OUT_WINDOWS,index=False)
    e.to_csv(OUT_ENTRIES,index=False)
    windows.window_status.value_counts().rename_axis('status').reset_index(name='count').to_csv(OUT_STATUS,index=False)

    rows=[]
    for part in PARTS:
        for name in FRACS:
            g=e[(e.partition==part)&(e.entry_name==name)]
            rows.append({'partition':part,'entry_name':name,**summarize(g)})
    sm=pd.DataFrame(rows)

    passes={}
    for name in FRACS:
        ok=True
        for part in MAJOR:
            r=sm[(sm.partition==part)&(sm.entry_name==name)].iloc[0]
            ok &= int(r.fills)>=30 and float(r.target_hit_rate)>=0.70
        passes[name]=bool(ok)
    sm['screen_pass']=sm.entry_name.map(passes)
    sm.to_csv(OUT_SUM,index=False)

    clean=windows[windows.eligible_start.notna()].copy()
    window_rows=[]
    for part in PARTS:
        g=windows[windows.partition==part]; c=clean[clean.partition==part]
        window_rows.append((part,len(g),len(c),(c.window_status=='L2_ARRIVAL').mean() if len(c) else np.nan))

    md=[]
    md.append('# B27BQ — London -> New York SHORT Pre-Second-Touch Entry Geometry — Result\n')
    md.append(f'5m rows: **{len(x5):,}**; coverage: **{100*coverage:.4f}%**.\n')
    md.append('**Audit status: PASS.** Frozen B27Q London->NY SHORT K1 OPP0 identities are reused; chronology is raw 5m.\n')
    md.append('## Clean-window structure\n')
    md.append('| Partition | K1 setups | Clean windows | L2 arrival after clean leave |\n|---|---:|---:|---:|')
    for part,n,c,p in window_rows:
        md.append(f'| {part} | {n} | {c} | {pct(p)} |')
    md.append('\n## Pre-L2 entry geometry\n')
    md.append('| Partition | Level | Fills | Fill rate | L2 hit | Median min to L2 | Median adverse R | P90 max price f | Screen |\n|---|---|---:|---:|---:|---:|---:|---:|---|')
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_name} | {int(r.fills)} | {pct(r.fill_rate)} | {pct(r.target_hit_rate)} | {num(r.median_minutes_to_l2)} | {num(r.median_adverse_excursion_range_frac)} | {num(r.p90_max_post_entry_frac)} | {"PASS" if r.screen_pass else "-"} |')
    passed=[k for k,v in passes.items() if v]
    md.append('\n## Frozen structural screen\n')
    md.append('Passing requires >=30 pre-L2 fills AND >=70% L2 hit rate in external, development, and reference_validation for the same frozen level.')
    md.append(f'\n**Overall: {"SCREEN_PASS " + ", ".join(passed) if passed else "NO_PASS"}.**\n')
    md.append('This result is structural entry-quality evidence only. It does not define the stop/TP economics and does not modify live BBC.\n')
    OUT_MD.write_text('\n'.join(md),encoding='utf-8')


if __name__=='__main__':
    main()
