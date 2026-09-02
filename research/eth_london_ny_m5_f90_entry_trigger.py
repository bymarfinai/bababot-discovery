#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
VARIANTS = ('BLIND_TOUCH','EARLY_RECLAIM','SAME_BAR_REJECTION')
F90 = 0.90

M2_ENTRIES = ROOT / 'ETH_LONDON_NY_PRE_H2_RETRACE_M2_Entries.csv'
M4_SUMMARY = ROOT / 'ETH_LONDON_NY_M4_STRUCTURE_LADDER_Summary.csv'
OUT_MD = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Result.md'
OUT_SUM = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Summary.csv'
OUT_AUDIT = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
OUT_STATUS = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

m1 = loadmod('eth_m1', HERE / 'eth_london_ny_liquidity_pressure_m1.py')


def fast_slice(x, a, z):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def load_f90():
    e = pd.read_csv(M2_ENTRIES)
    e = e[(e.entry_name == 'F90') & e.filled.astype(str).str.lower().eq('true')].copy()
    for c in ('entry_ts','eligible_start','h2_bar_start','opposite_break_bar_start','signal_ts'):
        e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')
    e['H'] = pd.to_numeric(e.H, errors='raise')
    e['L'] = pd.to_numeric(e.L, errors='raise')
    e['R'] = e.H - e.L
    e['f90_px'] = e.L + F90 * e.R
    e['session_end'] = pd.to_datetime(e.date_utc, utc=True) + pd.Timedelta(hours=20)
    e['opportunity_id'] = e.partition.astype(str) + '|' + e.date_utc.astype(str) + '|' + e.entry_ts.astype(str)
    assert e.opportunity_id.is_unique
    assert np.allclose(e.entry_px.astype(float), e.f90_px.astype(float), rtol=1e-10, atol=1e-9)
    return e.sort_values(['partition','entry_ts']).reset_index(drop=True)


def structural_outcome(x5, entry_bar_start, H, L, end):
    q = fast_slice(x5, entry_bar_start, end)
    assert len(q) and q.index[0] == entry_bar_start
    for ts, b in q.iterrows():
        cl = float(b.close)
        if cl > H:
            return 'STRICT_BREAKOUT', ts
        if cl < L:
            return 'OPPOSITE_BREAK', ts
    return 'NO_BREAK_BY_END', pd.NaT


def base_row(r, variant):
    return {
        'opportunity_id': r.opportunity_id,
        'partition': r.partition,
        'date_utc': r.date_utc,
        'variant': variant,
        'touch_bar_start': pd.Timestamp(r.entry_ts),
        'H': float(r.H), 'L': float(r.L), 'R': float(r.R), 'F90': float(r.f90_px),
        'h2_bar_start': pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT,
        'session_end': pd.Timestamp(r.session_end),
        'confirmed': False,
        'confirmation_bar_start': pd.NaT,
        'confirmation_kind': '',
        'executed': False,
        'entry_bar_start': pd.NaT,
        'entry_px': np.nan,
        'realized_entry_fraction': np.nan,
        'remaining_to_H_R': np.nan,
        'status': '',
        'terminal': '',
        'terminal_bar_start': pd.NaT,
        'strict_breakout': False,
        'h2_after_entry': False,
        'touch_to_confirmation_min': np.nan,
        'touch_to_entry_min': np.nan,
    }


def run_blind(x5, r):
    z = base_row(r, 'BLIND_TOUCH')
    ts = pd.Timestamp(r.entry_ts)
    terminal, terminal_ts = structural_outcome(x5, ts, float(r.H), float(r.L), pd.Timestamp(r.session_end))
    z.update({
        'confirmed': True,
        'confirmation_bar_start': ts,
        'confirmation_kind': 'BLIND_LIMIT',
        'executed': True,
        'entry_bar_start': ts,
        'entry_px': float(r.f90_px),
        'realized_entry_fraction': F90,
        'remaining_to_H_R': 1.0-F90,
        'status': 'EXECUTED',
        'terminal': terminal,
        'terminal_bar_start': terminal_ts,
        'strict_breakout': terminal == 'STRICT_BREAKOUT',
        'h2_after_entry': bool(pd.notna(r.h2_bar_start) and pd.Timestamp(r.h2_bar_start) >= ts),
        'touch_to_confirmation_min': 0.0,
        'touch_to_entry_min': 0.0,
    })
    return z


def find_reclaim(x5, r, same_bar_only=False):
    touch = pd.Timestamp(r.entry_ts); H=float(r.H); L=float(r.L); px=float(r.f90_px)
    end = pd.Timestamp(r.session_end)
    h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    q = fast_slice(x5, touch, end)
    assert len(q) and q.index[0] == touch

    for k, (ts, b) in enumerate(q.iterrows()):
        if pd.notna(h2) and ts >= h2:
            return None, 'H2_BEFORE_CONFIRMATION'
        cl = float(b.close)
        if cl < L:
            return None, 'OPPOSITE_BREAK_BEFORE_CONFIRMATION'
        if same_bar_only and k > 0:
            return None, 'NO_SAME_BAR_RECLAIM'
        if cl > px:
            return ts, ('SAME_BAR' if k == 0 else 'LATER_RECLAIM')
        if same_bar_only:
            return None, 'NO_SAME_BAR_RECLAIM'
    return None, 'SESSION_END_BEFORE_CONFIRMATION'


def run_reclaim(x5, r, same_bar_only=False):
    variant = 'SAME_BAR_REJECTION' if same_bar_only else 'EARLY_RECLAIM'
    z = base_row(r, variant)
    conf, kind = find_reclaim(x5, r, same_bar_only=same_bar_only)
    if conf is None:
        z['status'] = kind
        return z

    touch = pd.Timestamp(r.entry_ts); H=float(r.H); L=float(r.L); R=float(r.R)
    entry_bar = conf + BAR5
    end = pd.Timestamp(r.session_end)
    if entry_bar >= end or entry_bar not in x5.index:
        z.update({'confirmed':True,'confirmation_bar_start':conf,'confirmation_kind':kind,'status':'NO_NEXT_BAR'})
        return z

    op = float(x5.loc[entry_bar].open)
    z.update({
        'confirmed': True,
        'confirmation_bar_start': conf,
        'confirmation_kind': kind,
        'touch_to_confirmation_min': float((conf-touch)/pd.Timedelta(minutes=1)),
    })
    if op >= H:
        z['status'] = 'MISSED_H2_AT_OPEN'
        return z
    if op <= L:
        z['status'] = 'INVALID_OPEN_GEOMETRY'
        return z

    # If a frozen H2 exists before the actual next-bar open, chronology is invalid.
    h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    if pd.notna(h2) and entry_bar > h2:
        z['status'] = 'H2_BEFORE_ENTRY'
        return z

    terminal, terminal_ts = structural_outcome(x5, entry_bar, H, L, end)
    frac = (op-L)/R
    z.update({
        'executed': True,
        'entry_bar_start': entry_bar,
        'entry_px': op,
        'realized_entry_fraction': frac,
        'remaining_to_H_R': 1.0-frac,
        'status': 'EXECUTED',
        'terminal': terminal,
        'terminal_bar_start': terminal_ts,
        'strict_breakout': terminal == 'STRICT_BREAKOUT',
        'h2_after_entry': bool(pd.notna(h2) and h2 >= entry_bar),
        'touch_to_entry_min': float((entry_bar-touch)/pd.Timedelta(minutes=1)),
    })
    return z


def synthetic_tests():
    H,L=100.0,90.0; px=99.0
    idx=pd.date_range('2026-01-05 14:00',periods=7,freq='5min',tz='UTC')
    x=pd.DataFrame([
        [99.2,99.4,98.8,99.1],  # touch + same-bar reclaim
        [99.1,100.2,99.0,99.8], # H2 but no strict breakout
        [99.8,100.5,99.4,100.2],# strict breakout
        [100.2,100.4,99.8,100.1],
        [100.1,100.2,99.8,100.0],
        [100,100,99,99.5],
        [99.5,99.8,99.0,99.2],
    ],index=idx,columns=['open','high','low','close'])
    r=pd.Series({'opportunity_id':'x','partition':'x','date_utc':'2026-01-05','entry_ts':idx[0],
                 'H':H,'L':L,'R':H-L,'f90_px':px,'h2_bar_start':idx[1],
                 'session_end':idx[-1]+BAR5})
    a=run_reclaim(x,r,False)
    assert a['executed'] and a['confirmation_kind']=='SAME_BAR' and a['entry_bar_start']==idx[1]
    assert a['strict_breakout']
    s=run_reclaim(x,r,True)
    assert s['executed'] and s['entry_bar_start']==idx[1]

    # Later reclaim strictly before H2.
    y=x.copy(); y.loc[idx[0],'close']=98.8; y.loc[idx[1],['high','close']]=[99.4,99.2]
    r2=r.copy(); r2['h2_bar_start']=idx[3]
    b=run_reclaim(y,r2,False)
    assert b['executed'] and b['confirmation_kind']=='LATER_RECLAIM'

    # H2 before any reclaim expires.
    y2=x.copy(); y2.loc[idx[0],'close']=98.8
    r3=r.copy(); r3['h2_bar_start']=idx[1]
    c=run_reclaim(y2,r3,False)
    assert not c['executed'] and c['status']=='H2_BEFORE_CONFIRMATION'

    # Opposite close before reclaim expires.
    y3=x.copy(); y3.loc[idx[0],'close']=98.8; y3.loc[idx[1],['high','low','close']]=[98.9,89.0,89.5]
    r4=r.copy(); r4['h2_bar_start']=pd.NaT
    d=run_reclaim(y3,r4,False)
    assert not d['executed'] and d['status']=='OPPOSITE_BREAK_BEFORE_CONFIRMATION'

    # Missed H2 at next open.
    y4=x.copy(); y4.loc[idx[1],'open']=100.1
    e=run_reclaim(y4,r,False)
    assert not e['executed'] and e['status']=='MISSED_H2_AT_OPEN'


def summarize(g, opportunities):
    ex=g[g.executed.astype(bool)].copy()
    n=len(ex); b=int(ex.strict_breakout.sum()) if n else 0
    opp=int((ex.terminal=='OPPOSITE_BREAK').sum()) if n else 0
    nb=int((ex.terminal=='NO_BREAK_BY_END').sum()) if n else 0
    conf=int(g.confirmed.sum())
    same=int((g.confirmation_kind=='SAME_BAR').sum())
    later=int((g.confirmation_kind=='LATER_RECLAIM').sum())
    return {
        'opportunities': opportunities,
        'confirmed': conf,
        'executed': n,
        'retention': n/opportunities if opportunities else np.nan,
        'same_bar_confirmed': same,
        'later_confirmed': later,
        'breakouts': b,
        'breakout_rate': b/n if n else np.nan,
        'opposite_breaks': opp,
        'opposite_rate': opp/n if n else np.nan,
        'no_breaks': nb,
        'no_break_rate': nb/n if n else np.nan,
        'h2_after_entry_rate': ex.h2_after_entry.mean() if n else np.nan,
        'median_touch_to_confirmation_min': pd.to_numeric(ex.touch_to_confirmation_min,errors='coerce').median() if n else np.nan,
        'median_touch_to_entry_min': pd.to_numeric(ex.touch_to_entry_min,errors='coerce').median() if n else np.nan,
        'median_realized_entry_fraction': pd.to_numeric(ex.realized_entry_fraction,errors='coerce').median() if n else np.nan,
        'median_remaining_to_H_R': pd.to_numeric(ex.remaining_to_H_R,errors='coerce').median() if n else np.nan,
    }


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=3): return '-' if pd.isna(v) else f'{float(v):.{n}f}'


def main():
    synthetic_tests()
    x5,cov=m1.load5('ETHUSDT')
    assert cov >= .995
    f90=load_f90()

    rows=[]
    for r in f90.itertuples(index=False):
        rows.append(run_blind(x5,r))
        rows.append(run_reclaim(x5,r,False))
        rows.append(run_reclaim(x5,r,True))
    a=pd.DataFrame(rows)

    # Hard identity and chronology assertions.
    blind=a[a.variant=='BLIND_TOUCH']
    assert len(blind)==len(f90)
    assert set(blind.opportunity_id)==set(f90.opportunity_id)
    assert blind.executed.all()
    assert np.allclose(blind.realized_entry_fraction.astype(float),F90)
    for r in a[a.executed.astype(bool) & a.variant.ne('BLIND_TOUCH')].itertuples(index=False):
        assert pd.Timestamp(r.entry_bar_start)==pd.Timestamp(r.confirmation_bar_start)+BAR5
        assert float(r.entry_px)>float(r.L) and float(r.entry_px)<float(r.H)
        if pd.notna(r.h2_bar_start):
            assert pd.Timestamp(r.entry_bar_start)<=pd.Timestamp(r.h2_bar_start)
    for r in a[a.confirmed.astype(bool) & a.variant.ne('BLIND_TOUCH')].itertuples(index=False):
        bar=x5.loc[pd.Timestamp(r.confirmation_bar_start)]
        assert float(bar.close)>float(r.F90)
        if pd.notna(r.h2_bar_start):
            assert pd.Timestamp(r.confirmation_bar_start)<pd.Timestamp(r.h2_bar_start)

    # Summaries.
    sums=[]
    for part in (*PARTS,'POOLED_MAJOR'):
        if part=='POOLED_MAJOR':
            base=f90[f90.partition.isin(MAJOR)]
            aa=a[a.partition.isin(MAJOR)]
        else:
            base=f90[f90.partition==part]
            aa=a[a.partition==part]
        opportunities=len(base)
        for v in VARIANTS:
            sums.append({'partition':part,'variant':v,**summarize(aa[aa.variant==v],opportunities)})
    sm=pd.DataFrame(sums)

    # M4 F90 control parity.
    m4=pd.read_csv(M4_SUMMARY)
    m4=m4[(m4.asset=='ETH')&(m4.entry_name=='F90')]
    for p in (*MAJOR,'POOLED_MAJOR'):
        x=sm[(sm.partition==p)&(sm.variant=='BLIND_TOUCH')].iloc[0]
        y=m4[m4.partition==p].iloc[0]
        assert int(x.executed)==int(y.fills)
        assert int(x.breakouts)==int(y.breakout_n)
        assert abs(float(x.breakout_rate)-float(y.breakout_rate_fill))<1e-12

    # Frozen screen for EARLY_RECLAIM only.
    er={p:sm[(sm.partition==p)&(sm.variant=='EARLY_RECLAIM')].iloc[0] for p in MAJOR}
    bl={p:sm[(sm.partition==p)&(sm.variant=='BLIND_TOUCH')].iloc[0] for p in MAJOR}
    pool_er=sm[(sm.partition=='POOLED_MAJOR')&(sm.variant=='EARLY_RECLAIM')].iloc[0]
    pool_bl=sm[(sm.partition=='POOLED_MAJOR')&(sm.variant=='BLIND_TOUCH')].iloc[0]
    gate_n=all(int(er[p].executed)>=15 for p in MAJOR)
    gate_ret=float(pool_er.executed)/float(pool_bl.executed) >= .60
    gate_parts=all(float(er[p].breakout_rate)>=float(bl[p].breakout_rate) for p in MAJOR)
    gate_pool=float(pool_er.breakout_rate)>=float(pool_bl.breakout_rate)+.03
    passed=gate_n and gate_ret and gate_parts and gate_pool

    a.to_csv(OUT_AUDIT,index=False)
    sm.to_csv(OUT_SUM,index=False)

    lines=[]
    lines.append('# ETH London -> New York M5 F90 Entry Trigger Calibration — Result\n')
    lines.append(f'ETH raw 5m coverage: **{100*cov:.4f}%**.\n')
    lines.append('Frozen anchor: **F90 after London->NY LONG K1 OPP0 causal leave**. Structural outcome = strict completed 5m breakout `close > H`; H2 is telemetry only.\n')
    lines.append(f'- Exact M2 F90 filled opportunities: **{len(f90)}**.')
    lines.append('- BLIND_TOUCH -> M4 F90 parity: **PASS**.')
    lines.append('- Reclaim chronology / geometry audit: **PASS**.\n')

    lines.append('## Major-partition trigger comparison\n')
    lines.append('| Partition | Variant | Opps | Executed | Retention | Same-bar | Later | Strict BO | BO rate | Opposite | No break | Median entry f |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    q=sm[sm.partition.isin(MAJOR)]
    for r in q.itertuples(index=False):
        lines.append(f'| {r.partition} | {r.variant} | {r.opportunities} | {r.executed} | {pct(r.retention)} | {r.same_bar_confirmed} | {r.later_confirmed} | {r.breakouts} | {pct(r.breakout_rate)} | {r.opposite_breaks} | {r.no_breaks} | {num(r.median_realized_entry_fraction)} |')
    lines.append('')

    lines.append('## Pooled-major\n')
    lines.append('| Variant | N | Retention | BO rate | H2 after entry | Median touch->entry | Median entry f | Remaining to H |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|')
    q=sm[sm.partition=='POOLED_MAJOR']
    for r in q.itertuples(index=False):
        lines.append(f'| {r.variant} | {r.executed} | {pct(r.retention)} | {pct(r.breakout_rate)} | {pct(r.h2_after_entry_rate)} | {num(r.median_touch_to_entry_min,1)}m | {num(r.median_realized_entry_fraction)} | {num(r.median_remaining_to_H_R)}R |')
    lines.append('')

    lines.append('## Frozen EARLY_RECLAIM trigger screen\n')
    lines.append(f'- >=15 executed in every major partition: **{"PASS" if gate_n else "FAIL"}**')
    lines.append(f'- pooled retention >=60% of blind: **{"PASS" if gate_ret else "FAIL"}**')
    lines.append(f'- breakout rate >= blind in every major partition: **{"PASS" if gate_parts else "FAIL"}**')
    lines.append(f'- pooled breakout improvement >=3.0pp: **{"PASS" if gate_pool else "FAIL"}**')
    lines.append('')
    status='ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS' if passed else 'ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_NOT_SUPPORTED'
    lines.append(f'**Status: {status}**\n')
    lines.append('SAME_BAR_REJECTION remains diagnostic only. M5 contains no stop, target, PnL, fee, slippage, runner, or portfolio optimization.')

    OUT_MD.write_text('\n'.join(lines))
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
