#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
SIG_PATH = ROOT / 'ETH_LONG_SESSION_LIQUIDITY_PRESSURE_B27Q_ADAPT_Signals.csv'
PFX = 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_WINDOWS = ROOT / f'{PFX}_Windows.csv'
OUT_ENTRIES = ROOT / f'{PFX}_Entries.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SELECTED = ROOT / f'{PFX}_SelectedLevel.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
FRACS = {f'F{x}': x/100.0 for x in range(95,49,-5)}


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def load_cohort():
    s = pd.read_csv(SIG_PATH)
    s = s[(s.transition=='LONDON_TO_NEWYORK') & (s.side=='LONG') & (s.k==1) & (s.opp_visits_at_signal==0)].copy()
    for c in ('signal_bar_start','signal_ts','active_session_end'):
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
        raise AssertionError('missing K1 bar')
    if sig_ts != sig_start + BAR5:
        raise AssertionError('unexpected signal timestamp')
    if not qualifies_high_touch(q.iloc[0], H):
        raise AssertionError('K1 does not reproduce High touch')

    same_episode_bars = 1
    leave_pos = None
    leave_bar_start = pd.NaT
    eligible_start = pd.NaT

    for k in range(1, len(q)):
        ts = q.index[k]; r = q.iloc[k]; c = float(r.close)
        if c > H:
            return base_window(s,H,L,same_episode_bars,'NO_WINDOW_HIGH_BREAK_DURING_K1',pd.NaT,pd.NaT,pd.NaT,pd.NaT)
        if c < L:
            return base_window(s,H,L,same_episode_bars,'NO_WINDOW_LOW_BREAK_DURING_K1',pd.NaT,pd.NaT,pd.NaT,pd.NaT)
        if qualifies_high_touch(r,H):
            same_episode_bars += 1
            continue
        leave_pos = k
        leave_bar_start = ts
        eligible_start = ts + BAR5
        break

    if leave_pos is None:
        return base_window(s,H,L,same_episode_bars,'NO_CAUSAL_LEAVE_BY_SESSION_END',pd.NaT,pd.NaT,pd.NaT,pd.NaT)

    h2_start = pd.NaT; opp_start = pd.NaT; terminal_start = pd.NaT
    status = 'NO_H2_BY_SESSION_END'
    for k in range(leave_pos + 1, len(q)):
        ts = q.index[k]; r = q.iloc[k]
        hit_h = float(r.high) >= H
        break_l = float(r.close) < L
        if hit_h and break_l:
            status = 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
            terminal_start = ts
            break
        if hit_h:
            status = 'H2_ARRIVAL'
            h2_start = ts
            terminal_start = ts
            break
        if break_l:
            status = 'OPPOSITE_BREAK_BEFORE_H2'
            opp_start = ts
            terminal_start = ts
            break

    return base_window(s,H,L,same_episode_bars,status,leave_bar_start,eligible_start,h2_start,opp_start,terminal_start)


def base_window(s,H,L,same_episode_bars,status,leave_bar_start,eligible_start,h2_start,opp_start,terminal_start=pd.NaT):
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
        'eligible_start': eligible_start,
        'h2_bar_start': h2_start,
        'opposite_break_bar_start': opp_start,
        'terminal_bar_start': terminal_start,
    }


def simulate_entry(x5: pd.DataFrame, w: pd.Series, name: str, frac: float) -> dict:
    H=float(w.H); L=float(w.L); rng=H-L; px=L+frac*rng
    base={
        'partition':w.partition,'date_utc':w.date_utc,'signal_ts':w.signal_ts,
        'window_status':w.window_status,'entry_name':name,'entry_fraction':frac,
        'planned_entry_px':px,'H':H,'L':L,'range':rng,
        'eligible_start':w.eligible_start,'h2_bar_start':w.h2_bar_start,
        'opposite_break_bar_start':w.opposite_break_bar_start,'terminal_bar_start':w.terminal_bar_start,
    }
    if pd.isna(w.eligible_start):
        return {**base,'filled':False,'entry_ts':pd.NaT,'target_hit':False,'terminal':'NO_CLEAN_WINDOW',
                'minutes_to_h2':np.nan,'reward_range_frac':1-frac,'min_post_entry_frac':np.nan,
                'adverse_excursion_range_frac':np.nan}

    if pd.notna(w.terminal_bar_start):
        terminal_start = pd.Timestamp(w.terminal_bar_start)
    elif w.window_status == 'NO_H2_BY_SESSION_END':
        terminal_start = pd.Timestamp(w.session_end)
    else:
        terminal_start = pd.Timestamp(w.session_end)

    q = fast_slice(x5, pd.Timestamp(w.eligible_start), terminal_start)
    fill_ts = pd.NaT; fill_pos = None
    for k,(ts,r) in enumerate(q.iterrows()):
        if float(r.close) < L:
            raise AssertionError('opposite break inside eligible pre-terminal slice')
        if float(r.high) >= H:
            raise AssertionError('H2 inside eligible pre-terminal slice')
        if float(r.low) <= px <= float(r.high):
            fill_ts = ts; fill_pos = k; break

    if fill_pos is None:
        return {**base,'filled':False,'entry_ts':pd.NaT,'target_hit':False,'terminal':w.window_status,
                'minutes_to_h2':np.nan,'reward_range_frac':1-frac,'min_post_entry_frac':np.nan,
                'adverse_excursion_range_frac':np.nan}

    if not pd.Timestamp(fill_ts) < terminal_start:
        raise AssertionError('fill not strictly pre-terminal')

    post = q.iloc[fill_pos:]
    min_low = float(post.low.min()) if len(post) else px
    min_frac = (min_low-L)/rng
    adverse = max(0.0, frac-min_frac)
    target = bool(w.window_status == 'H2_ARRIVAL')
    mins = float((pd.Timestamp(w.h2_bar_start)-pd.Timestamp(fill_ts))/pd.Timedelta(minutes=1)) if target else np.nan
    return {**base,'filled':True,'entry_ts':fill_ts,'target_hit':target,'terminal':w.window_status,
            'minutes_to_h2':mins,'reward_range_frac':1-frac,'min_post_entry_frac':min_frac,
            'adverse_excursion_range_frac':adverse}


def synthetic_tests():
    H,L=100.0,90.0
    idx=pd.date_range('2026-01-05 13:30',periods=8,freq='5min',tz='UTC')
    q=pd.DataFrame([
        {'open':99,'high':100.2,'low':98,'close':99.5},
        {'open':99.5,'high':100.1,'low':98.5,'close':99.2},
        {'open':99.2,'high':99.6,'low':97,'close':98},
        {'open':98,'high':98.5,'low':96,'close':97},
        {'open':97,'high':99,'low':95,'close':98.5},
        {'open':98.5,'high':100.4,'low':98,'close':99.8},
        {'open':99.8,'high':101,'low':99,'close':100.5},
        {'open':100.5,'high':101,'low':100,'close':100.8},
    ],index=idx)
    s=pd.Series({'partition':'x','date_utc':'2026-01-05','previous_session_high':H,'previous_session_low':L,
                 'signal_bar_start':idx[0],'signal_ts':idx[0]+BAR5,'active_session_end':idx[-1]+BAR5})
    w=build_window(q,s)
    assert w['k1_episode_bars']==2 and w['eligible_start']==idx[3] and w['window_status']=='H2_ARRIVAL'
    e=simulate_entry(q,pd.Series(w),'F75',0.75)
    assert e['filled'] and e['entry_ts']<idx[5] and e['target_hit']

    q2=q.copy(); q2.loc[idx[5],'close']=89.0
    w2=build_window(q2,s)
    assert w2['window_status']=='AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
    e2=simulate_entry(q2,pd.Series(w2),'F75',0.75)
    assert e2['filled'] and not e2['target_hit']


def summarize(g: pd.DataFrame) -> dict:
    f=g[g.filled.astype(bool)].copy() if len(g) else g
    return {
        'setups':int(len(g)),
        'fills':int(len(f)),
        'fill_rate':float(len(f)/len(g)) if len(g) else np.nan,
        'target_hits':int(f.target_hit.sum()) if len(f) else 0,
        'target_hit_rate':float(f.target_hit.mean()) if len(f) else np.nan,
        'median_minutes_to_h2':float(f.loc[f.target_hit,'minutes_to_h2'].median()) if len(f) and f.target_hit.any() else np.nan,
        'median_reward_range_frac':float(f.reward_range_frac.median()) if len(f) else np.nan,
        'median_min_post_entry_frac':float(f.min_post_entry_frac.median()) if len(f) else np.nan,
        'p10_min_post_entry_frac':float(f.min_post_entry_frac.quantile(.10)) if len(f) else np.nan,
        'median_adverse_excursion_range_frac':float(f.adverse_excursion_range_frac.median()) if len(f) else np.nan,
    }


def select_level(sm: pd.DataFrame):
    passes=[]
    for name,frac in FRACS.items():
        z=sm[(sm.entry_name==name)&sm.partition.isin(MAJOR)]
        if len(z)!=3: continue
        ok=bool((z.fills>=30).all() & (z.target_hit_rate>=0.70).all())
        if ok:
            passes.append({'entry_name':name,'entry_fraction':frac,
                           'min_hit_rate':float(z.target_hit_rate.min()),'total_fills':int(z.fills.sum())})
    if not passes:
        return pd.DataFrame(columns=['entry_name','entry_fraction','min_hit_rate','total_fills'])
    p=pd.DataFrame(passes).sort_values(['entry_fraction','min_hit_rate','total_fills'],ascending=[True,False,False]).reset_index(drop=True)
    return p


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    synthetic_tests()
    x5,coverage=ethdata.load5(); s=load_cohort()
    windows=pd.DataFrame([build_window(x5,r) for _,r in s.iterrows()])
    assert len(windows)==len(s)
    entries=[]
    for _,w in windows.iterrows():
        for name,frac in FRACS.items():
            entries.append(simulate_entry(x5,w,name,frac))
    e=pd.DataFrame(entries)

    windows.to_csv(OUT_WINDOWS,index=False)
    e.to_csv(OUT_ENTRIES,index=False)
    sums=[]
    for part in PARTS:
        for name in FRACS:
            g=e[(e.partition==part)&(e.entry_name==name)]
            sums.append({'partition':part,'entry_name':name,'entry_fraction':FRACS[name],**summarize(g)})
    sm=pd.DataFrame(sums); sm.to_csv(OUT_SUM,index=False)
    selected=select_level(sm); selected.to_csv(OUT_SELECTED,index=False)

    if not len(selected):
        status='ETH_LONG_B27W_ADAPT_NO_LEVEL_PASS'; chosen='NONE'
    else:
        top=selected.iloc[0]; chosen=str(top.entry_name)
        if abs(float(top.entry_fraction)-0.50)<1e-12:
            status='ETH_LONG_B27W_ADAPT_BOUNDARY_EXTENSION_REQUIRED'
        else:
            status='ETH_LONG_B27W_ADAPT_ENTRY_LEVEL_SELECTED'
    OUT_STATUS.write_text(status+'\n')

    wstat=windows.window_status.value_counts()
    md=['# ETH LONG B27W-Adapt — Result','',f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.',
        '',f'Frozen cohort: **LONDON_TO_NEWYORK / LONG / K1 / OPP0**; setups: **{len(windows)}**.','',
        '## Window diagnostic','',
        f'- H2 arrival: {int(wstat.get("H2_ARRIVAL",0))}',
        f'- opposite break before H2: {int(wstat.get("OPPOSITE_BREAK_BEFORE_H2",0))}',
        f'- ambiguous H2 vs opposite break: {int(wstat.get("AMBIGUOUS_H2_VS_OPPOSITE_BREAK",0))}',
        f'- no H2 by session end: {int(wstat.get("NO_H2_BY_SESSION_END",0))}',
        f'- no clean causal window: {int(sum(v for k,v in wstat.items() if str(k).startswith("NO_WINDOW") or k=="NO_CAUSAL_LEAVE_BY_SESSION_END"))}',
        '', '## Pre-H2 ETH retracement grid','',
        '| Partition | Entry | Fills | Fill rate | H2 hit rate | Median min to H2 | Reward to H | Median min f | P10 min f | Median adverse |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_name} | {r.fills} | {pct(r.fill_rate)} | {pct(r.target_hit_rate)} | {num(r.median_minutes_to_h2)} | {pct(r.median_reward_range_frac)} | {num(r.median_min_post_entry_frac)} | {num(r.p10_min_post_entry_frac)} | {pct(r.median_adverse_excursion_range_frac)} |')
    md += ['', '## Frozen screen / selection', '', f'**Status: {status}**', '', f'Selected level: **{chosen}**.']
    if len(selected):
        md += ['', '| Rank | Entry | Fraction | Min major hit rate | Total major fills |','|---:|---|---:|---:|---:|']
        for i,r in enumerate(selected.itertuples(index=False),1):
            md.append(f'| {i} | {r.entry_name} | {r.entry_fraction:.2f} | {pct(r.min_hit_rate)} | {r.total_fills} |')
    if status=='ETH_LONG_B27W_ADAPT_BOUNDARY_EXTENSION_REQUIRED':
        md += ['', 'F50 is a lower-boundary hit, so it is not treated as the final ETH optimum. A separately preregistered deeper-fraction extension is required before B27X-Adapt.']
    elif status=='ETH_LONG_B27W_ADAPT_ENTRY_LEVEL_SELECTED':
        md += ['', 'Next milestone: ETH B27X-Adapt winner MAE / stop-distance audit using the selected ETH fraction.']
    else:
        md += ['', 'No stop/exit tuning is allowed to rescue this milestone.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
