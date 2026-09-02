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
EXTS = {'E05':.05,'E10':.10,'E15':.15,'E20':.20,'E25':.25,'E30':.30}

M5_AUDIT = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
OUT_MD = ROOT / 'ETH_LONDON_NY_M7_F90_RECLAIM_POST_BREAKOUT_EXTENSION_Result.md'
OUT_TRADES = ROOT / 'ETH_LONDON_NY_M7_F90_RECLAIM_POST_BREAKOUT_EXTENSION_Trades.csv'
OUT_SUM = ROOT / 'ETH_LONDON_NY_M7_F90_RECLAIM_POST_BREAKOUT_EXTENSION_Summary.csv'
OUT_STATUS = ROOT / 'ETH_LONDON_NY_M7_F90_RECLAIM_POST_BREAKOUT_EXTENSION_Status.txt'


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
    a = a[(a.variant == 'EARLY_RECLAIM') & as_bool(a.executed) & (a.terminal == 'STRICT_BREAKOUT')].copy()
    for c in ('entry_bar_start','terminal_bar_start','session_end','h2_bar_start','confirmation_bar_start','touch_bar_start'):
        if c in a.columns:
            a[c] = pd.to_datetime(a[c], utc=True, errors='coerce')
    for c in ('H','L','R','entry_px','realized_entry_fraction'):
        a[c] = pd.to_numeric(a[c], errors='raise')
    a['strict_breakout'] = as_bool(a.strict_breakout)
    assert a.strict_breakout.all()
    a['cohort_id'] = a.partition.astype(str) + '|' + a.date_utc.astype(str) + '|' + a.entry_bar_start.astype(str)
    assert a.cohort_id.is_unique
    assert (a.R > 0).all()
    assert a.terminal_bar_start.notna().all()
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)


def first_touch(q: pd.DataFrame, px: float):
    hit = q[q.high.astype(float) >= px]
    return pd.NaT if hit.empty else pd.Timestamp(hit.index[0])


def analyze_one(x5, r):
    H=float(r.H); L=float(r.L); R=float(r.R)
    br=pd.Timestamp(r.terminal_bar_start)
    end=pd.Timestamp(r.session_end)
    assert br in x5.index
    brrow=x5.loc[br]
    assert float(brrow.close) > H
    start=br + BAR5
    q=fast_slice(x5,start,end)

    z={
        'cohort_id':r.cohort_id,
        'partition':r.partition,
        'date_utc':r.date_utc,
        'entry_bar_start':pd.Timestamp(r.entry_bar_start),
        'entry_px':float(r.entry_px),
        'entry_fraction':float(r.realized_entry_fraction),
        'H':H,'L':L,'R':R,
        'breakout_bar_start':br,
        'breakout_bar_close':float(brrow.close),
        'session_end':end,
    }

    max_ext = 0.0
    if len(q):
        max_ext = max(0.0, (float(q.high.max()) - H) / R)
    z['max_causal_extension_R'] = max_ext

    hits=[]
    for name, e in EXTS.items():
        px=H + e*R
        assert np.isclose(px, H + e*(H-L), rtol=1e-12, atol=1e-10)
        samebar=bool(float(brrow.high) >= px)
        ts=first_touch(q,px) if len(q) else pd.NaT
        hit=pd.notna(ts)
        hits.append(hit)
        z[f'{name}_px']=px
        z[f'{name}_same_breakout_bar']=samebar
        z[f'{name}_causal_hit']=hit
        z[f'{name}_causal_ts']=ts
        z[f'{name}_minutes_after_breakout_completion']=(
            float((ts-start)/pd.Timedelta(minutes=1)) if hit else np.nan
        )

    # Monotonic extension ladder: farther causal hit implies every nearer level also hit.
    for i in range(1,len(hits)):
        assert not (hits[i] and not hits[i-1])
    return z


def summarize(g: pd.DataFrame):
    n=len(g)
    out={'confirmed_breakouts':n}
    prev=None
    for name in EXTS:
        hit=g[f'{name}_causal_hit'].astype(bool) if n else pd.Series(dtype=bool)
        same=g[f'{name}_same_breakout_bar'].astype(bool) if n else pd.Series(dtype=bool)
        h=int(hit.sum()) if n else 0
        out[f'{name}_hits']=h
        out[f'{name}_rate']=h/n if n else np.nan
        out[f'{name}_samebar_overshoot_rate']=float(same.mean()) if n else np.nan
        out[f'{name}_median_minutes']=pd.to_numeric(g.loc[hit,f'{name}_minutes_after_breakout_completion'],errors='coerce').median() if h else np.nan
        if prev is not None:
            prevhit=g[f'{prev}_causal_hit'].astype(bool)
            denom=int(prevhit.sum())
            out[f'{name}_given_{prev}']=h/denom if denom else np.nan
        prev=name
    out['median_max_causal_extension_R']=pd.to_numeric(g.max_causal_extension_R,errors='coerce').median() if n else np.nan
    out['p25_max_causal_extension_R']=pd.to_numeric(g.max_causal_extension_R,errors='coerce').quantile(.25) if n else np.nan
    out['p75_max_causal_extension_R']=pd.to_numeric(g.max_causal_extension_R,errors='coerce').quantile(.75) if n else np.nan
    return out


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=2): return '-' if pd.isna(v) else f'{float(v):.{n}f}'


def main():
    cohort=load_cohort()
    x5,cov=m1.load5('ETHUSDT')
    assert cov >= .995

    rows=[]
    for r in cohort.itertuples(index=False):
        rows.append(analyze_one(x5,r))
    t=pd.DataFrame(rows)
    assert len(t)==len(cohort)
    assert set(t.cohort_id)==set(cohort.cohort_id)

    sums=[]
    for part in (*PARTS,'POOLED_MAJOR'):
        if part=='POOLED_MAJOR':
            g=t[t.partition.isin(MAJOR)].copy()
        else:
            g=t[t.partition==part].copy()
        sums.append({'partition':part,**summarize(g)})
    sm=pd.DataFrame(sums)

    # Frozen structural target screen.
    part_n={p:int(sm.loc[sm.partition==p,'confirmed_breakouts'].iloc[0]) for p in MAJOR}
    adequacy=all(v>=10 for v in part_n.values())
    pooled=sm[sm.partition=='POOLED_MAJOR'].iloc[0]
    candidates=[]
    for name in EXTS:
        stable=all(float(sm.loc[sm.partition==p,f'{name}_rate'].iloc[0])>=.80 for p in MAJOR)
        pooled_ok=float(pooled[f'{name}_rate'])>=.85
        if adequacy and stable and pooled_ok:
            candidates.append(name)

    t.to_csv(OUT_TRADES,index=False)
    sm.to_csv(OUT_SUM,index=False)

    lines=[]
    lines.append('# ETH London -> New York M7 F90 Early-Reclaim Post-Breakout Extension — Result\n')
    lines.append(f'ETH raw 5m coverage: **{100*cov:.4f}%**.\n')
    lines.append('Frozen cohort: **M5 F90 EARLY_RECLAIM executed trades that reached strict completed 5m breakout close > H**.\n')
    lines.append(f'- Confirmed-breakout cohort rows: **{len(cohort)}**.')
    lines.append('- Identity / chronology / extension monotonicity audit: **PASS**.')
    lines.append('- Causal extension scoring starts on the next raw 5m bar after breakout-bar completion; same-breakout-bar overshoot is telemetry only.\n')

    lines.append('## Causal extension ladder\n')
    lines.append('| Partition | N BO | E05 | E10 | E15 | E20 | E25 | E30 | Median max ext |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in sm.itertuples(index=False):
        lines.append(f'| {r.partition} | {r.confirmed_breakouts} | {pct(r.E05_rate)} | {pct(r.E10_rate)} | {pct(r.E15_rate)} | {pct(r.E20_rate)} | {pct(r.E25_rate)} | {pct(r.E30_rate)} | {num(r.median_max_causal_extension_R)}R |')
    lines.append('')

    lines.append('## Conditional continuation and timing — POOLED_MAJOR\n')
    lines.append('| Stage | Causal hit | Conditional from prior | Median minutes after BO completion | Same-BO-bar overshoot telemetry |')
    lines.append('|---|---:|---:|---:|---:|')
    prev=None
    for name in EXTS:
        cond='-' if prev is None else pct(pooled[f'{name}_given_{prev}'])
        lines.append(f'| {name} | {pct(pooled[f"{name}_rate"])} | {cond} | {num(pooled[f"{name}_median_minutes"],1)}m | {pct(pooled[f"{name}_samebar_overshoot_rate"])} |')
        prev=name
    lines.append('')

    lines.append('## Frozen structural target screen\n')
    lines.append(f'- Major-partition confirmed-breakout adequacy >=10 each: **{"PASS" if adequacy else "FAIL"}** ({part_n}).')
    for name in EXTS:
        ps=', '.join(f'{p}={pct(sm.loc[sm.partition==p,f"{name}_rate"].iloc[0])}' for p in MAJOR)
        tag='STRUCTURAL_TARGET_CANDIDATE' if name in candidates else 'NO'
        lines.append(f'- {name}: {ps}; pooled={pct(pooled[f"{name}_rate"])} -> **{tag}**')
    lines.append('')

    if candidates:
        status='ETH_LONDON_NY_M7_POST_BREAKOUT_TARGET_FAMILY_SUPPORTED'
        lines.append(f'**Supported structural target family: {", ".join(candidates)}.**\n')
    else:
        status='ETH_LONDON_NY_M7_NO_STRUCTURAL_TARGET_CANDIDATE'
        lines.append('**No extension passed the frozen structural target screen.**\n')
    lines.append(f'**Status: {status}**\n')
    lines.append('M7 is reward-side structural calibration only. No TP, stop, PnL, PF, runner, or live configuration is promoted by this result.')

    OUT_MD.write_text('\n'.join(lines))
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
