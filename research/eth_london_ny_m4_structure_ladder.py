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
LEVELS = ('F95','F90','F85','F80','F75')
ETH_ENTRIES = ROOT / 'ETH_LONDON_NY_PRE_H2_RETRACE_M2_Entries.csv'
BTC_ENTRIES = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
OUT_MD = ROOT / 'ETH_LONDON_NY_M4_STRUCTURE_LADDER_Result.md'
OUT_SUM = ROOT / 'ETH_LONDON_NY_M4_STRUCTURE_LADDER_Summary.csv'
OUT_AUDIT = ROOT / 'ETH_LONDON_NY_M4_STRUCTURE_LADDER_Audit.csv'
OUT_STATUS = ROOT / 'ETH_LONDON_NY_M4_STRUCTURE_LADDER_Status.txt'


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


def load_entries(path: Path, asset: str):
    e = pd.read_csv(path)
    e = e[e.filled.astype(str).str.lower().eq('true')].copy()
    e = e[e.entry_name.isin(LEVELS)].copy()
    for c in ('entry_ts','h2_bar_start','signal_ts'):
        if c in e.columns:
            e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')
    e['asset'] = asset
    e['H'] = pd.to_numeric(e.H, errors='raise')
    e['L'] = pd.to_numeric(e.L, errors='raise')
    e['entry_fraction'] = pd.to_numeric(e.entry_fraction, errors='raise')
    e['session_end'] = pd.to_datetime(e.date_utc, utc=True) + pd.Timedelta(hours=20)
    e['row_id'] = asset + '|' + e.partition.astype(str) + '|' + e.date_utc.astype(str) + '|' + e.entry_name.astype(str) + '|' + e.entry_ts.astype(str)
    assert e.row_id.is_unique
    return e.sort_values(['partition','entry_name','entry_ts']).reset_index(drop=True)


def first_extension(q, level):
    for ts, r in q.iterrows():
        if float(r.high) >= level:
            return ts
    return pd.NaT


def analyze_one(x5, r):
    H = float(r.H); L = float(r.L); R = H-L
    assert R > 0
    entry_ts = pd.Timestamp(r.entry_ts)
    end = pd.Timestamp(r.session_end)
    h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    if pd.notna(h2):
        assert entry_ts < h2

    q = fast_slice(x5, entry_ts, end)
    assert len(q) > 0 and q.index[0] == entry_ts

    breakout = pd.NaT
    opposite = pd.NaT
    for ts, b in q.iterrows():
        cl = float(b.close)
        if cl > H:
            breakout = ts
            break
        if cl < L:
            opposite = ts
            break

    if pd.notna(breakout):
        assert pd.notna(h2), 'strict breakout without H2 arrival'
        assert breakout >= h2

    h2_arrived = pd.notna(h2)
    strict_breakout = pd.notna(breakout)
    immediate = bool(h2_arrived and strict_breakout and breakout == h2)
    rejection = bool(h2_arrived and not immediate)
    later_breakout = bool(rejection and strict_breakout and breakout > h2)

    e10 = H + .10*R
    e20 = H + .20*R
    samebar_e10 = False; samebar_e20 = False
    causal_e10 = pd.NaT; causal_e20 = pd.NaT
    if strict_breakout:
        br = x5.loc[breakout]
        samebar_e10 = float(br.high) >= e10
        samebar_e20 = float(br.high) >= e20
        post = fast_slice(x5, breakout + BAR5, end)
        causal_e10 = first_extension(post, e10)
        causal_e20 = first_extension(post, e20)

    def mins(a,b):
        if pd.isna(a) or pd.isna(b): return np.nan
        return float((pd.Timestamp(b)-pd.Timestamp(a))/pd.Timedelta(minutes=1))

    terminal = 'STRICT_BREAKOUT' if strict_breakout else ('OPPOSITE_BREAK' if pd.notna(opposite) else 'NO_BREAK_BY_END')
    return {
        'asset': r.asset, 'partition': r.partition, 'date_utc': r.date_utc,
        'entry_name': r.entry_name, 'entry_fraction': r.entry_fraction,
        'entry_ts': entry_ts, 'H': H, 'L': L, 'R': R,
        'h2_bar_start': h2, 'h2_arrived': h2_arrived,
        'strict_breakout': strict_breakout, 'breakout_bar_start': breakout,
        'opposite_bar_start': opposite, 'terminal': terminal,
        'h2_immediate_breakout': immediate, 'h2_rejection': rejection,
        'later_breakout_after_h2_rejection': later_breakout,
        'same_breakout_bar_e10': samebar_e10, 'same_breakout_bar_e20': samebar_e20,
        'causal_e10_ts': causal_e10, 'causal_e20_ts': causal_e20,
        'causal_e10': pd.notna(causal_e10), 'causal_e20': pd.notna(causal_e20),
        'min_fill_to_h2': mins(entry_ts,h2),
        'min_h2_to_breakout': mins(h2,breakout),
        'min_breakout_to_e10': mins(breakout + BAR5,causal_e10) if pd.notna(breakout) else np.nan,
        'min_breakout_to_e20': mins(breakout + BAR5,causal_e20) if pd.notna(breakout) else np.nan,
    }


def summarize(g):
    n=len(g); h=int(g.h2_arrived.sum()); b=int(g.strict_breakout.sum())
    rej=int(g.h2_rejection.sum()); imm=int(g.h2_immediate_breakout.sum())
    later=int(g.later_breakout_after_h2_rejection.sum())
    opp=int((g.terminal=='OPPOSITE_BREAK').sum()); nb=int((g.terminal=='NO_BREAK_BY_END').sum())
    e10=int(g.causal_e10.sum()); e20=int(g.causal_e20.sum())
    sb10=int(g.same_breakout_bar_e10.sum()); sb20=int(g.same_breakout_bar_e20.sum())
    return {
        'fills':n,
        'h2_n':h,'h2_rate_fill':h/n if n else np.nan,
        'breakout_n':b,'breakout_rate_fill':b/n if n else np.nan,
        'breakout_rate_given_h2':b/h if h else np.nan,
        'h2_immediate_n':imm,'h2_immediate_rate_given_h2':imm/h if h else np.nan,
        'h2_rejection_n':rej,
        'later_breakout_n':later,'later_breakout_rate_given_rejection':later/rej if rej else np.nan,
        'opposite_before_breakout_n':opp,'no_break_by_end_n':nb,
        'causal_e10_n':e10,'causal_e10_rate_given_breakout':e10/b if b else np.nan,
        'causal_e20_n':e20,'causal_e20_rate_given_breakout':e20/b if b else np.nan,
        'samebar_e10_n':sb10,'samebar_e10_rate_given_breakout':sb10/b if b else np.nan,
        'samebar_e20_n':sb20,'samebar_e20_rate_given_breakout':sb20/b if b else np.nan,
        'median_fill_to_h2':g.min_fill_to_h2.median(),
        'median_h2_to_breakout':g.loc[g.strict_breakout,'min_h2_to_breakout'].median() if b else np.nan,
        'median_breakout_to_e10':g.loc[g.causal_e10,'min_breakout_to_e10'].median() if e10 else np.nan,
        'median_breakout_to_e20':g.loc[g.causal_e20,'min_breakout_to_e20'].median() if e20 else np.nan,
    }


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v): return '-' if pd.isna(v) else f'{float(v):.1f}'


def main():
    eth, cov_eth = m1.load5('ETHUSDT')
    btc, cov_btc = m1.load5('BTCUSDT')
    assert cov_eth >= .995 and cov_btc >= .995
    ee = load_entries(ETH_ENTRIES,'ETH')
    be = load_entries(BTC_ENTRIES,'BTC')

    audits=[]
    for x5, e in ((eth,ee),(btc,be)):
        for r in e.itertuples(index=False):
            audits.append(analyze_one(x5,r))
    a=pd.DataFrame(audits)

    # Entry identity and chronology parity assertions.
    assert len(a[a.asset=='ETH']) == len(ee)
    assert len(a[a.asset=='BTC']) == len(be)
    assert set(a.loc[a.asset=='ETH','entry_ts']) == set(ee.entry_ts)
    assert set(a.loc[a.asset=='BTC','entry_ts']) == set(be.entry_ts)
    assert ((a.h2_arrived & (a.entry_ts >= a.h2_bar_start)).sum() == 0)
    assert ((a.h2_immediate_breakout & ~a.strict_breakout).sum() == 0)

    rows=[]
    for asset in ('ETH','BTC'):
        for part in (*PARTS,'POOLED_MAJOR'):
            for level in LEVELS:
                if part=='POOLED_MAJOR':
                    g=a[(a.asset==asset)&a.partition.isin(MAJOR)&(a.entry_name==level)].copy()
                else:
                    g=a[(a.asset==asset)&(a.partition==part)&(a.entry_name==level)].copy()
                rows.append({'asset':asset,'partition':part,'entry_name':level,**summarize(g)})
    sm=pd.DataFrame(rows)
    a.to_csv(OUT_AUDIT,index=False)
    sm.to_csv(OUT_SUM,index=False)

    lines=[]
    lines.append('# ETH London -> New York M4 Structure Ladder — Result\n')
    lines.append(f'Raw 5m coverage: ETH **{100*cov_eth:.4f}%**, BTC **{100*cov_btc:.4f}%**.\n')
    lines.append('Frozen causal ladder: **fill -> H2 arrival -> strict close breakout > H -> post-confirmation E10/E20 extension**. H2 is not TP.\n')
    lines.append(f'- ETH filled entries audited: **{len(ee)}**.')
    lines.append(f'- BTC control filled entries audited: **{len(be)}**.')
    lines.append('- Entry identity / chronology audit: **PASS**.\n')

    for asset in ('ETH','BTC'):
        lines.append(f'## {asset} pooled-major structure\n')
        lines.append('| Entry | N | H2/fill | Breakout/fill | Breakout/H2 | Immediate BO/H2 | Later BO after H2 reject | E10 after confirmed BO | E20 after confirmed BO |')
        lines.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
        q=sm[(sm.asset==asset)&(sm.partition=='POOLED_MAJOR')]
        for r in q.itertuples(index=False):
            lines.append(f'| {r.entry_name} | {r.fills} | {pct(r.h2_rate_fill)} | {pct(r.breakout_rate_fill)} | {pct(r.breakout_rate_given_h2)} | {pct(r.h2_immediate_rate_given_h2)} | {pct(r.later_breakout_rate_given_rejection)} | {pct(r.causal_e10_rate_given_breakout)} | {pct(r.causal_e20_rate_given_breakout)} |')
        lines.append('')

    lines.append('## ETH major-partition breakout calibration\n')
    lines.append('| Partition | Entry | N | H2/fill | Breakout/fill | Breakout/H2 | Immediate BO/H2 | Later BO after reject |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|')
    q=sm[(sm.asset=='ETH')&sm.partition.isin(MAJOR)]
    for r in q.itertuples(index=False):
        lines.append(f'| {r.partition} | {r.entry_name} | {r.fills} | {pct(r.h2_rate_fill)} | {pct(r.breakout_rate_fill)} | {pct(r.breakout_rate_given_h2)} | {pct(r.h2_immediate_rate_given_h2)} | {pct(r.later_breakout_rate_given_rejection)} |')
    lines.append('')
    lines.append('## Decision\n')
    lines.append('**Status: ETH_LONDON_NY_M4_STRUCTURE_LADDER_CALIBRATED**\n')
    lines.append('M4 is descriptive structural calibration only. No entry level, TP, stop, runner, or economic configuration is promoted by this result.')
    OUT_MD.write_text('\n'.join(lines))
    OUT_STATUS.write_text('ETH_LONDON_NY_M4_STRUCTURE_LADDER_CALIBRATED\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
