#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Entries.csv'
WINDOWS_PATH = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Windows.csv'
PFX = 'ETH_LONG_F75_WINNER_MAE_B27X_ADAPT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PATHS = ROOT / f'{PFX}_Paths.csv'
OUT_SURV = ROOT / f'{PFX}_Survival.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
ENTRY_FRAC = 0.75
DS = [x / 100.0 for x in range(5, 76, 5)]


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def qtl(x, q):
    s = pd.to_numeric(pd.Series(x), errors='coerce').dropna()
    return float(s.quantile(q)) if len(s) else np.nan


def fmt(v, d=3):
    return '-' if pd.isna(v) else f'{float(v):.{d}f}'


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def load_paths_source():
    e = pd.read_csv(ENTRIES_PATH)
    e = e[(e.entry_name == 'F75') & (e.filled.astype(str).str.lower() == 'true')].copy()
    w = pd.read_csv(WINDOWS_PATH)[['partition','date_utc','signal_ts','session_end']].copy()
    for c in ('signal_ts','session_end'):
        w[c] = pd.to_datetime(w[c], utc=True)
    for c in ('signal_ts','entry_ts','h2_bar_start','terminal_bar_start'):
        e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')
    e = e.merge(w, on=['partition','date_utc','signal_ts'], how='left', validate='many_to_one')
    if e.session_end.isna().any():
        raise AssertionError('missing session_end after B27W merge')
    expected = e['L'].astype(float) + ENTRY_FRAC * e['range'].astype(float)
    if not np.allclose(expected, e['planned_entry_px'].astype(float), rtol=1e-10, atol=1e-10):
        raise AssertionError('F75 price identity mismatch')
    return e.sort_values(['partition','entry_ts']).reset_index(drop=True)


def build_path(x5: pd.DataFrame, r) -> dict:
    entry = pd.Timestamp(r.entry_ts)
    H = float(r.H); L = float(r.L); R = float(r.range); px = float(r.planned_entry_px)
    winner = bool(r.window_status == 'H2_ARRIVAL' and bool(r.target_hit))
    h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    terminal = pd.Timestamp(r.terminal_bar_start) if pd.notna(r.terminal_bar_start) else pd.NaT
    session_end = pd.Timestamp(r.session_end)

    if winner:
        if pd.isna(h2) or not entry < h2:
            raise AssertionError('winner must have later H2')
        pre = fast_slice(x5, entry, h2)
        through = fast_slice(x5, entry, h2 + BAR5)
        if pre.empty or through.empty:
            raise AssertionError('empty winner path')
        pre_min = float(pre.low.min())
        through_min = float(through.low.min())
        pre_d = max(0.0, (px - pre_min) / R)
        through_d = max(0.0, (px - through_min) / R)
        nonh2_d = np.nan
        path_end = h2 + BAR5
    else:
        end = terminal + BAR5 if pd.notna(terminal) else session_end
        q = fast_slice(x5, entry, end)
        if q.empty:
            raise AssertionError('empty non-H2 path')
        mn = float(q.low.min())
        nonh2_d = max(0.0, (px - mn) / R)
        pre_d = np.nan
        through_d = np.nan
        path_end = end

    return {
        'partition': r.partition,
        'date_utc': r.date_utc,
        'signal_ts': r.signal_ts,
        'entry_ts': entry,
        'entry_px': px,
        'H': H, 'L': L, 'range': R,
        'window_status': r.window_status,
        'h2_bar_start': h2,
        'terminal_bar_start': terminal,
        'session_end': session_end,
        'winner': winner,
        'pre_h2_adverse_d': pre_d,
        'through_h2_adverse_d': through_d,
        'non_h2_adverse_d': nonh2_d,
        'path_end': path_end,
    }


def synthetic_tests():
    idx = pd.date_range('2026-01-05 14:00', periods=5, freq='5min', tz='UTC')
    x = pd.DataFrame([
        {'open':97.5,'high':98,'low':96.8,'close':97.2},
        {'open':97.2,'high':99,'low':96.0,'close':98.5},
        {'open':98.5,'high':100.2,'low':95.5,'close':99.5},
        {'open':99.5,'high':101,'low':99,'close':100.5},
        {'open':100.5,'high':101,'low':100,'close':100.8},
    ], index=idx)
    class R: pass
    r=R(); r.entry_ts=idx[0]; r.H=100.; r.L=90.; r.range=10.; r.planned_entry_px=97.5
    r.window_status='H2_ARRIVAL'; r.target_hit=True; r.h2_bar_start=idx[2]; r.terminal_bar_start=idx[2]
    r.session_end=idx[-1]+BAR5; r.partition='x'; r.date_utc='2026-01-05'; r.signal_ts=idx[0]-BAR5
    p=build_path(x,r)
    assert abs(p['pre_h2_adverse_d']-0.15)<1e-12
    assert abs(p['through_h2_adverse_d']-0.20)<1e-12


def main():
    synthetic_tests()
    x5, coverage = ethdata.load5()
    src = load_paths_source()
    paths = pd.DataFrame([build_path(x5, r) for r in src.itertuples(index=False)])
    if len(paths) != len(src):
        raise AssertionError('B27W F75 fill identity count mismatch')
    paths.to_csv(OUT_PATHS, index=False)

    surv_rows=[]
    for part in PARTS:
        g=paths[paths.partition==part]
        winners=g[g.winner.astype(bool)]
        for D in DS:
            surv_rows.append({
                'partition':part,'D':D,'stop_fraction':ENTRY_FRAC-D,
                'h2_winners':int(len(winners)),
                'pre_h2_survive_rate':float((winners.pre_h2_adverse_d < D).mean()) if len(winners) else np.nan,
                'through_h2_survive_rate':float((winners.through_h2_adverse_d < D).mean()) if len(winners) else np.nan,
            })
    surv=pd.DataFrame(surv_rows); surv.to_csv(OUT_SURV,index=False)

    status='ETH_LONG_B27X_ADAPT_MAE_AUDIT_PASS'
    OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG B27X-Adapt — F75 Winner MAE / Stop-Distance Audit — Result','',
        f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        f'Exact frozen B27W-Adapt F75 fills reproduced: **{len(paths)}**. B27X-Adapt is diagnostic only; no stop is selected.','',
        '## F75 H2-winner adverse excursion','',
        '| Partition | F75 fills | Winners | Pre-H2 D P50 | P75 | P90 | P95 | Max | Through-H2 D P50 | P75 | P90 | P95 | Max |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in PARTS:
        g=paths[paths.partition==part]; w=g[g.winner.astype(bool)]
        md.append(f'| {part} | {len(g)} | {len(w)} | {fmt(qtl(w.pre_h2_adverse_d,.50))} | {fmt(qtl(w.pre_h2_adverse_d,.75))} | {fmt(qtl(w.pre_h2_adverse_d,.90))} | {fmt(qtl(w.pre_h2_adverse_d,.95))} | {fmt(w.pre_h2_adverse_d.max() if len(w) else np.nan)} | {fmt(qtl(w.through_h2_adverse_d,.50))} | {fmt(qtl(w.through_h2_adverse_d,.75))} | {fmt(qtl(w.through_h2_adverse_d,.90))} | {fmt(qtl(w.through_h2_adverse_d,.95))} | {fmt(w.through_h2_adverse_d.max() if len(w) else np.nan)} |')

    md += ['', '## Conservative winner-survival curve', '',
           '| Partition | D | Stop fraction | Winners | Pre-H2 survive | Through-H2 survive |',
           '|---|---:|---:|---:|---:|---:|']
    for r in surv.itertuples(index=False):
        md.append(f'| {r.partition} | {r.D:.2f} | {r.stop_fraction:.2f} | {r.h2_winners} | {pct(r.pre_h2_survive_rate)} | {pct(r.through_h2_survive_rate)} |')

    md += ['', '## Non-H2 filled-path adverse excursion', '',
           '| Partition | Non-H2 fills | D P50 | P75 | P90 | P95 | Max |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for part in PARTS:
        n=paths[(paths.partition==part)&(~paths.winner.astype(bool))]
        md.append(f'| {part} | {len(n)} | {fmt(qtl(n.non_h2_adverse_d,.50))} | {fmt(qtl(n.non_h2_adverse_d,.75))} | {fmt(qtl(n.non_h2_adverse_d,.90))} | {fmt(qtl(n.non_h2_adverse_d,.95))} | {fmt(n.non_h2_adverse_d.max() if len(n) else np.nan)} |')

    md += ['', f'**Status: {status}**', '', 'Next milestone: adapt the BTC post-H2 extension atlas / invalidation-target diagnostics before economic selection. Research only.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
