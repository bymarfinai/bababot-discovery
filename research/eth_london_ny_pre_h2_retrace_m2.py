#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PFX = 'ETH_LONDON_NY_PRE_H2_RETRACE_M2'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_WINDOWS = ROOT / f'{PFX}_Windows.csv'
OUT_ENTRIES = ROOT / f'{PFX}_Entries.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
M1_SIGNALS = ROOT / 'ETH_LONDON_NY_LIQUIDITY_PRESSURE_M1_Signals.csv'


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

m1 = loadmod('eth_m1', HERE / 'eth_london_ny_liquidity_pressure_m1.py')
b27w = loadmod('btc_b27w', HERE / 'btc_london_ny_pre_second_touch_entry_b27w.py')

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
FRACS = {'F95':0.95,'F90':0.90,'F85':0.85,'F80':0.80,'F75':0.75}


def load_eth_signals():
    s = pd.read_csv(M1_SIGNALS)
    s = s[s.symbol.eq('ETHUSDT')].copy()
    for c in ('signal_bar_start','signal_ts'):
        s[c] = pd.to_datetime(s[c], utc=True)
    s['previous_session_high'] = pd.to_numeric(s.H, errors='raise')
    s['previous_session_low'] = pd.to_numeric(s.L, errors='raise')
    day = pd.to_datetime(s.date_utc, utc=True)
    s['active_session_end'] = day + pd.Timedelta(hours=20)
    s = s.sort_values(['partition','signal_ts']).reset_index(drop=True)
    assert s.opp_visits_at_signal.astype(int).eq(0).all()
    assert s.hi_visits_at_signal.astype(int).eq(1).all()
    return s


def summary_for(g, windows):
    clean_ids = set(windows.loc[windows.eligible_start.notna(), 'window_id'])
    clean = g[g.window_id.isin(clean_ids)]
    f = g[g.filled.astype(bool)].copy()
    return {
        'setups': int(g.window_id.nunique()),
        'clean_windows': int(len(clean_ids)),
        'h2_windows': int((windows.window_status == 'H2_ARRIVAL').sum()),
        'h2_after_clean_rate': float((windows.loc[windows.eligible_start.notna(),'window_status'] == 'H2_ARRIVAL').mean()) if len(clean_ids) else np.nan,
        'fills': int(len(f)),
        'fill_rate_clean': float(len(f)/len(clean_ids)) if len(clean_ids) else np.nan,
        'target_hits': int(f.target_hit.astype(bool).sum()) if len(f) else 0,
        'target_hit_rate': float(f.target_hit.astype(bool).mean()) if len(f) else np.nan,
        'median_minutes_to_h2': float(pd.to_numeric(f.loc[f.target_hit.astype(bool),'minutes_to_h2'], errors='coerce').median()) if len(f) and f.target_hit.astype(bool).any() else np.nan,
        'reward_to_h_R': float(f.reward_range_frac.median()) if len(f) else np.nan,
        'median_min_post_entry_frac': float(f.min_post_entry_frac.median()) if len(f) else np.nan,
        'p10_min_post_entry_frac': float(f.min_post_entry_frac.quantile(.10)) if len(f) else np.nan,
        'median_mae_R': float(f.adverse_excursion_range_frac.median()) if len(f) else np.nan,
    }


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def num(v, n=2):
    return '-' if pd.isna(v) else f'{float(v):.{n}f}'


def main():
    # Reuse BTC B27W synthetic chronology tests unchanged.
    b27w.synthetic_tests()
    s = load_eth_signals()
    x5, coverage = m1.load5('ETHUSDT')
    assert coverage >= .995

    windows = []
    for i, r in s.iterrows():
        w = b27w.build_window(x5, r)
        w['window_id'] = f"{r.partition}|{r.date_utc}|{pd.Timestamp(r.signal_ts).isoformat()}"
        windows.append(w)
    wdf = pd.DataFrame(windows)

    # Exact M1 identity parity.
    parity = (
        len(wdf) == len(s) and
        list(pd.to_datetime(wdf.signal_ts, utc=True)) == list(pd.to_datetime(s.signal_ts, utc=True))
    )
    if not parity:
        raise AssertionError('ETH M1 K1 identity parity failed')

    entries = []
    for _, w in wdf.iterrows():
        for name, frac in FRACS.items():
            e = b27w.simulate_entry(x5, w, name, frac)
            e['window_id'] = w.window_id
            entries.append(e)
    edf = pd.DataFrame(entries)

    chronology_ok = True
    for r in edf[edf.filled.astype(bool)].itertuples(index=False):
        if pd.Timestamp(r.entry_ts) < pd.Timestamp(r.eligible_start): chronology_ok = False
        if pd.notna(r.h2_bar_start) and not (pd.Timestamp(r.entry_ts) < pd.Timestamp(r.h2_bar_start)): chronology_ok = False
        expected = float(r.L) + float(r.entry_fraction) * (float(r.H)-float(r.L))
        if abs(float(r.entry_px)-expected) > 1e-9*max(1.0,abs(expected)): chronology_ok = False
    if not chronology_ok:
        raise AssertionError('M2 chronology/geometry audit failed')

    wdf.to_csv(OUT_WINDOWS, index=False)
    edf.to_csv(OUT_ENTRIES, index=False)

    rows=[]
    for part in (*PARTS,'POOLED_MAJOR'):
        wp = wdf[wdf.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else wdf[wdf.partition.eq(part)]
        for name in FRACS:
            ep = edf[(edf.entry_name.eq(name)) & (edf.partition.isin(MAJOR) if part=='POOLED_MAJOR' else edf.partition.eq(part))]
            rows.append({'partition':part,'entry_name':name,**summary_for(ep,wp)})
    sm = pd.DataFrame(rows)
    sm.to_csv(OUT_SUM, index=False)

    passes={}
    for name in FRACS:
        ok=True
        for p in MAJOR:
            r=sm[(sm.partition.eq(p))&(sm.entry_name.eq(name))].iloc[0]
            ok = ok and int(r.fills)>=30 and float(r.target_hit_rate)>=.70
        passes[name]=bool(ok)
    supported=[k for k,v in passes.items() if v]

    audit=pd.DataFrame([
        {'check':'m1_signal_identity_parity','value':len(s),'pass':parity},
        {'check':'raw_5m_coverage_ge_99_5','value':coverage,'pass':coverage>=.995},
        {'check':'filled_entry_chronology_geometry','value':int(edf.filled.astype(bool).sum()),'pass':chronology_ok},
        {'check':'one_window_per_m1_signal','value':len(wdf),'pass':len(wdf)==len(s)},
    ])
    audit.to_csv(OUT_AUDIT,index=False)
    status='ETH_LONDON_NY_M2_RETRACE_FAMILY_SUPPORTED' if supported else 'ETH_LONDON_NY_M2_NO_RETRACE_LEVEL_SUPPORTED'

    lines=[
        '# ETH London -> New York Pre-H2 Retrace — M2 Result','',
        f'ETH raw 5m coverage: **{coverage:.4%}**.','',
        'Frozen structure: **London 08:00-13:30 UTC -> New York 13:30-20:00 UTC · LONG K1 OPP0 · causal leave · pre-H2 only**.','',
        f'- Reused M1 ETH K1 identities: **{len(s)}**; parity: **PASS**.',
        f'- Causal/geometry audit: **PASS**.','',
        '## Structural retracement grid','',
        '| Partition | Level | Setups | Clean windows | Fills | Fill/clean | H2 hits | H2 hit/fill | Median fill->H2 | Median MAE |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for p in (*PARTS,'POOLED_MAJOR'):
        for name in FRACS:
            r=sm[(sm.partition.eq(p))&(sm.entry_name.eq(name))].iloc[0]
            lines.append(f'| {p} | {name} | {int(r.setups)} | {int(r.clean_windows)} | {int(r.fills)} | {pct(r.fill_rate_clean)} | {int(r.target_hits)} | {pct(r.target_hit_rate)} | {num(r.median_minutes_to_h2,1)}m | {num(r.median_mae_R,3)}R |')
    lines += ['','## Frozen discovery screen','']
    for name in FRACS:
        lines.append(f'- {name}: **{"SCREEN_PASS" if passes[name] else "NO"}**')
    lines += ['',f'**Supported family: {", ".join(supported) if supported else "NONE"}.**','',
              'No max-rate level is selected. Multiple passing levels remain a family; no intermediate fraction sweep is allowed here.','',
              '## Decision','',f'**Status: {status}**','',
              '- M2 contains no TP/SL/PF/PnL/runner/fee/slippage/portfolio optimization.',
              '- Historical data are already inspected; this is structural calibration evidence, not pristine OOS promotion.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
