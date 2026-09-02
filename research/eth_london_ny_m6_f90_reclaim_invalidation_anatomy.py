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
BANDS = {'F85':.85,'F80':.80,'F75':.75,'F70':.70,'F65':.65,'F60':.60,'F55':.55,'F50':.50}

M5_AUDIT = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
OUT_MD = ROOT / 'ETH_LONDON_NY_M6_F90_RECLAIM_INVALIDATION_ANATOMY_Result.md'
OUT_TRADES = ROOT / 'ETH_LONDON_NY_M6_F90_RECLAIM_INVALIDATION_ANATOMY_Trades.csv'
OUT_CLASS = ROOT / 'ETH_LONDON_NY_M6_F90_RECLAIM_INVALIDATION_ANATOMY_ClassSummary.csv'
OUT_BANDS = ROOT / 'ETH_LONDON_NY_M6_F90_RECLAIM_INVALIDATION_ANATOMY_BoundarySummary.csv'
OUT_STATUS = ROOT / 'ETH_LONDON_NY_M6_F90_RECLAIM_INVALIDATION_ANATOMY_Status.txt'


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


def as_bool(s):
    return s.astype(str).str.lower().eq('true')


def load_cohort():
    if M5_STATUS.exists():
        st = M5_STATUS.read_text().strip()
        assert st == 'ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS', st
    a = pd.read_csv(M5_AUDIT)
    a = a[(a.variant == 'EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('touch_bar_start','confirmation_bar_start','entry_bar_start','terminal_bar_start','h2_bar_start','session_end'):
        a[c] = pd.to_datetime(a[c], utc=True, errors='coerce')
    for c in ('H','L','R','entry_px','realized_entry_fraction'):
        a[c] = pd.to_numeric(a[c], errors='raise')
    a['strict_breakout'] = as_bool(a.strict_breakout)
    a['cohort_id'] = a.partition.astype(str) + '|' + a.date_utc.astype(str) + '|' + a.entry_bar_start.astype(str)
    assert a.cohort_id.is_unique
    assert (a.R > 0).all()
    assert set(a.terminal.unique()).issubset({'STRICT_BREAKOUT','OPPOSITE_BREAK','NO_BREAK_BY_END'})
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)


def classify(term):
    if term == 'STRICT_BREAKOUT': return 'WINNER'
    if term == 'OPPOSITE_BREAK': return 'NON_WINNER_OPPOSITE'
    return 'NON_WINNER_TIME'


def analyze_one(x5, r):
    H=float(r.H); L=float(r.L); R=float(r.R); entry=float(r.entry_px)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end)
    term=str(r.terminal)
    if term in ('STRICT_BREAKOUT','OPPOSITE_BREAK'):
        t=pd.Timestamp(r.terminal_bar_start)
        assert pd.notna(t)
        q=fast_slice(x5,start,t+BAR5)
    else:
        t=end-BAR5
        q=fast_slice(x5,start,end)
    assert len(q)>0 and q.index[0]==start
    assert q.index[-1]==t

    if term=='STRICT_BREAKOUT':
        assert float(x5.loc[t].close)>H
    if term=='OPPOSITE_BREAK':
        assert float(x5.loc[t].close)<L

    min_low=float(q.low.min()); min_close=float(q.close.min())
    low_f=(min_low-L)/R; close_f=(min_close-L)/R; entry_f=(entry-L)/R
    assert low_f <= close_f + 1e-10

    z={
        'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,
        'entry_bar_start':start,'entry_px':entry,'entry_fraction':entry_f,
        'H':H,'L':L,'R':R,'terminal':term,'terminal_class':classify(term),
        'terminal_bar_start':t,'h2_after_entry':bool(str(r.h2_after_entry).lower()=='true'),
        'min_low':min_low,'min_low_fraction':low_f,
        'wick_mae_R':max(0.0,entry_f-low_f),
        'min_close':min_close,'min_close_fraction':close_f,
        'close_drawdown_R':max(0.0,entry_f-close_f),
        'hold_minutes':float((t+BAR5-start)/pd.Timedelta(minutes=1)),
    }
    for name,f in BANDS.items():
        px=L+f*R
        z[f'{name}_px']=px
        z[f'{name}_wick_breach']=bool((q.low < px).any())
        z[f'{name}_close_breach']=bool((q.close < px).any())
    return z


def qv(s,p):
    return float(pd.to_numeric(s,errors='coerce').quantile(p)) if len(s) else np.nan


def class_summary(g, part, cls):
    q=g[g.terminal_class.eq(cls)].copy() if cls!='NON_WINNER' else g[~g.terminal_class.eq('WINNER')].copy()
    return {
        'partition':part,'class':cls,'n':len(q),
        'median_wick_mae_R':qv(q.wick_mae_R,.5),'p75_wick_mae_R':qv(q.wick_mae_R,.75),'p90_wick_mae_R':qv(q.wick_mae_R,.9),
        'median_close_drawdown_R':qv(q.close_drawdown_R,.5),'p75_close_drawdown_R':qv(q.close_drawdown_R,.75),'p90_close_drawdown_R':qv(q.close_drawdown_R,.9),
        'median_min_close_fraction':qv(q.min_close_fraction,.5),'median_hold_minutes':qv(q.hold_minutes,.5),
    }


def boundary_summary(g, part, name):
    w=g[g.terminal_class.eq('WINNER')].copy(); n=g[~g.terminal_class.eq('WINNER')].copy()
    wc=float(w[f'{name}_close_breach'].mean()) if len(w) else np.nan
    nc=float(n[f'{name}_close_breach'].mean()) if len(n) else np.nan
    ww=float(w[f'{name}_wick_breach'].mean()) if len(w) else np.nan
    nw=float(n[f'{name}_wick_breach'].mean()) if len(n) else np.nan
    return {
        'partition':part,'boundary':name,'fraction':BANDS[name],
        'winner_n':len(w),'nonwinner_n':len(n),
        'winner_close_breach_rate':wc,'nonwinner_close_breach_rate':nc,
        'close_separation_pp':100*(nc-wc) if pd.notna(wc) and pd.notna(nc) else np.nan,
        'winner_wick_breach_rate':ww,'nonwinner_wick_breach_rate':nw,
        'wick_separation_pp':100*(nw-ww) if pd.notna(ww) and pd.notna(nw) else np.nan,
    }


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=3): return '-' if pd.isna(v) else f'{float(v):.{n}f}'


def main():
    cohort=load_cohort(); x5,cov=m1.load5('ETHUSDT'); assert cov>=.995
    trades=pd.DataFrame([analyze_one(x5,r) for r in cohort.itertuples(index=False)])
    assert len(trades)==len(cohort)
    assert list(trades.cohort_id)==list(cohort.cohort_id)
    assert np.allclose(trades.entry_px,cohort.entry_px,rtol=1e-10,atol=1e-9)

    class_rows=[]; band_rows=[]
    for part in (*PARTS,'POOLED_MAJOR'):
        g=trades[trades.partition.isin(MAJOR)].copy() if part=='POOLED_MAJOR' else trades[trades.partition.eq(part)].copy()
        for cls in ('WINNER','NON_WINNER','NON_WINNER_OPPOSITE','NON_WINNER_TIME'):
            class_rows.append(class_summary(g,part,cls))
        for name in BANDS:
            band_rows.append(boundary_summary(g,part,name))
    cs=pd.DataFrame(class_rows); bs=pd.DataFrame(band_rows)

    candidates=[]
    for name in BANDS:
        majors=bs[(bs.partition.isin(MAJOR))&(bs.boundary.eq(name))]
        pool=bs[(bs.partition=='POOLED_MAJOR')&(bs.boundary.eq(name))].iloc[0]
        enough=bool((majors.winner_n>=10).all())
        protect=bool((majors.winner_close_breach_rate<=.15).all())
        catch=bool(float(pool.nonwinner_close_breach_rate)>=.40)
        sep=bool(float(pool.close_separation_pp)>=25.0)
        if enough and protect and catch and sep:
            candidates.append(name)

    trades.to_csv(OUT_TRADES,index=False); cs.to_csv(OUT_CLASS,index=False); bs.to_csv(OUT_BANDS,index=False)

    p=cs[cs.partition.eq('POOLED_MAJOR')]
    pw=p[p['class'].eq('WINNER')].iloc[0]; pn=p[p['class'].eq('NON_WINNER')].iloc[0]
    lines=[]
    lines.append('# ETH London -> New York M6 F90 Early-Reclaim Invalidation Anatomy — Result\n')
    lines.append(f'ETH raw 5m coverage: **{100*cov:.4f}%**.\n')
    lines.append('Frozen cohort: **M5 F90 EARLY_RECLAIM executed entries only**. Outcome remains strict completed 5m breakout `close > H`; M6 installs no stop and contains no economics.\n')
    lines.append(f'- Executed cohort: **{len(trades)}**')
    lines.append(f'- Winners: **{int((trades.terminal_class=="WINNER").sum())}**')
    lines.append(f'- Non-winners: **{int((trades.terminal_class!="WINNER").sum())}**')
    lines.append('- Entry identity / terminal chronology audit: **PASS**.\n')

    lines.append('## Pooled-major excursion anatomy\n')
    lines.append('| Class | N | Median wick MAE | P75 | P90 | Median close DD | P75 | P90 | Median min close f |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in (pw,pn):
        lines.append(f'| {r["class"]} | {int(r.n)} | {num(r.median_wick_mae_R)}R | {num(r.p75_wick_mae_R)}R | {num(r.p90_wick_mae_R)}R | {num(r.median_close_drawdown_R)}R | {num(r.p75_close_drawdown_R)}R | {num(r.p90_close_drawdown_R)}R | F{100*float(r.median_min_close_fraction):.1f} |')
    lines.append('')

    lines.append('## Completed-close boundary discrimination — pooled major\n')
    lines.append('| Boundary | Winner breach | Non-winner breach | Separation | Structural candidate |')
    lines.append('|---|---:|---:|---:|---|')
    q=bs[bs.partition.eq('POOLED_MAJOR')]
    for r in q.itertuples(index=False):
        lines.append(f'| {r.boundary} | {pct(r.winner_close_breach_rate)} | {pct(r.nonwinner_close_breach_rate)} | {num(r.close_separation_pp,1)} pp | {"YES" if r.boundary in candidates else "NO"} |')
    lines.append('')

    lines.append('## Major-partition winner protection\n')
    lines.append('| Partition | Winner N | Non-winner N | ' + ' | '.join(BANDS.keys()) + ' |')
    lines.append('|---|---:|---:|' + '|'.join(['---:']*len(BANDS)) + '|')
    for part in MAJOR:
        q=bs[bs.partition.eq(part)].set_index('boundary')
        wn=int(q.iloc[0].winner_n); nn=int(q.iloc[0].nonwinner_n)
        vals=' | '.join(pct(q.loc[name,'winner_close_breach_rate']) for name in BANDS)
        lines.append(f'| {part} | {wn} | {nn} | {vals} |')
    lines.append('')

    lines.append('## Decision\n')
    if candidates:
        lines.append('**Status: ETH_LONDON_NY_M6_STRUCTURAL_INVALIDATION_CANDIDATE_FOUND**\n')
        lines.append('Frozen structural candidate family: **' + ', '.join(candidates) + '**.\n')
        lines.append('These are anatomy candidates only; none is an economic stop until a separately preregistered execution test.')
        status='ETH_LONDON_NY_M6_STRUCTURAL_INVALIDATION_CANDIDATE_FOUND'
    else:
        lines.append('**Status: ETH_LONDON_NY_M6_NO_STRUCTURAL_INVALIDATION_CANDIDATE**\n')
        lines.append('No frozen boundary met the winner-protection + non-winner-capture screen. Do not fine-sweep intermediate levels post hoc.')
        status='ETH_LONDON_NY_M6_NO_STRUCTURAL_INVALIDATION_CANDIDATE'
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
