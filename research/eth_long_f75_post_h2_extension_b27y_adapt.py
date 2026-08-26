#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Entries.csv'
WINDOWS = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Windows.csv'
PFX = 'ETH_LONG_F75_POST_H2_EXTENSION_B27Y_ADAPT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PATHS = ROOT / f'{PFX}_Paths.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_ATLAS = ROOT / f'{PFX}_ExtensionAtlas.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

PARTS = ('external','development','reference_validation','august')
LEVELS = {'E05':0.05,'E10':0.10,'E15':0.15,'E20':0.20,'E25':0.25,'E30':0.30,'E40':0.40,'E50':0.50}
BAR5 = pd.Timedelta(minutes=5)
ENTRY_FRAC = 0.75


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_f75():
    e = pd.read_csv(ENTRIES)
    w = pd.read_csv(WINDOWS)
    for c in ('signal_ts','entry_ts','eligible_start','h2_bar_start','opposite_break_bar_start','terminal_bar_start'):
        if c in e.columns:
            e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')
    for c in ('signal_ts','session_end','h2_bar_start'):
        if c in w.columns:
            w[c] = pd.to_datetime(w[c], utc=True, errors='coerce')
    e = e[(e.entry_name=='F75') & (e.filled.astype(str).str.lower()=='true')].copy()
    keep = w[['partition','date_utc','signal_ts','session_end']].copy()
    e = e.merge(keep,on=['partition','date_utc','signal_ts'],how='left',validate='many_to_one')
    if e.session_end.isna().any():
        raise AssertionError('missing session_end')
    expected = e.L.astype(float) + ENTRY_FRAC * e['range'].astype(float)
    if not np.allclose(expected, e.planned_entry_px.astype(float), rtol=1e-10, atol=1e-10):
        raise AssertionError('F75 identity mismatch')
    return e.sort_values(['partition','entry_ts']).reset_index(drop=True)


def analyze_h2_slice(q, H, L, h2_start):
    R = H-L
    if not (R > 0 and len(q) > 0 and q.index[0] == h2_start):
        raise AssertionError('invalid H2 slice')
    if float(q.iloc[0].high) < H:
        raise AssertionError('H2 bar does not reach H')
    cb = q[q.close.astype(float) > H]
    first_close_break_start = cb.index[0] if len(cb) else pd.NaT
    out = {
        'first_close_break_bar_start': first_close_break_start,
        'first_close_break_ts': first_close_break_start + BAR5 if len(cb) else pd.NaT,
        'max_high_extension': (float(q.high.max())-H)/R,
        'max_close_extension': (float(q.close.max())-H)/R,
    }
    for name, ext in LEVELS.items():
        px = H + ext*R
        hi = q[q.high.astype(float) >= px]
        cl = q[q.close.astype(float) >= px]
        out[f'{name}_price'] = px
        out[f'{name}_high_reach'] = bool(len(hi))
        out[f'{name}_high_reach_bar_start'] = hi.index[0] if len(hi) else pd.NaT
        out[f'{name}_minutes_from_h2'] = float((hi.index[0]-h2_start)/pd.Timedelta(minutes=1)) if len(hi) else np.nan
        out[f'{name}_close_reach'] = bool(len(cl))
        out[f'{name}_close_reach_ts'] = cl.index[0] + BAR5 if len(cl) else pd.NaT
    return out


def synthetic_tests():
    idx = pd.date_range('2026-01-05 14:00',periods=5,freq='5min',tz='UTC')
    H,L=100.0,90.0
    q=pd.DataFrame([
        {'open':99,'high':100.2,'low':98.8,'close':99.7},
        {'open':99.7,'high':101.2,'low':99.5,'close':100.4},
        {'open':100.4,'high':103.2,'low':100.0,'close':102.6},
        {'open':102.6,'high':105.5,'low':102,'close':104.2},
        {'open':104.2,'high':104.5,'low':103,'close':103.5},
    ],index=idx)
    z=analyze_h2_slice(q,H,L,idx[0])
    assert z['first_close_break_bar_start']==idx[1]
    assert z['E10_high_reach'] and z['E50_high_reach'] and not z['E50_close_reach']
    assert abs(z['max_high_extension']-0.55)<1e-12


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x): return '-' if pd.isna(x) else f'{float(x):.3f}'


def main():
    synthetic_tests()
    x5, coverage = ethdata.load5()
    e = load_f75()
    rows=[]
    for r in e.itertuples(index=False):
        H=float(r.H); L=float(r.L); R=float(r.range)
        entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end)
        base={'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,
              'entry_ts':entry_ts,'entry_px':float(r.planned_entry_px),'H':H,'L':L,'range':R,
              'b27w_target_hit':bool(r.target_hit),'h2_bar_start':r.h2_bar_start,'session_end':end}
        has_h2=bool(r.window_status=='H2_ARRIVAL' and bool(r.target_hit) and pd.notna(r.h2_bar_start))
        if not has_h2:
            z={'has_h2':False,'first_close_break_bar_start':pd.NaT,'first_close_break_ts':pd.NaT,
               'max_high_extension':np.nan,'max_close_extension':np.nan}
            for name, ext in LEVELS.items():
                z[f'{name}_price']=H+ext*R; z[f'{name}_high_reach']=False
                z[f'{name}_high_reach_bar_start']=pd.NaT; z[f'{name}_minutes_from_h2']=np.nan
                z[f'{name}_close_reach']=False; z[f'{name}_close_reach_ts']=pd.NaT
            rows.append({**base,**z}); continue
        h2=pd.Timestamp(r.h2_bar_start)
        if not entry_ts < h2:
            raise AssertionError('entry not before H2')
        q=fast_slice(x5,h2,end)
        z=analyze_h2_slice(q,H,L,h2)
        rows.append({**base,'has_h2':True,**z})

    p=pd.DataFrame(rows)
    if len(p)!=len(e):
        raise AssertionError('F75 identity count mismatch')
    p.to_csv(OUT_PATHS,index=False)

    sums=[]; atlas=[]
    for part in PARTS:
        g=p[p.partition==part].copy(); h=g[g.has_h2.astype(bool)].copy()
        n=len(g); nh=len(h); cb=int(h.first_close_break_bar_start.notna().sum()) if nh else 0
        sums.append({'partition':part,'f75_fills':n,'h2_count':nh,'h2_rate':nh/n if n else np.nan,
                     'close_break_count':cb,'close_break_rate_given_h2':cb/nh if nh else np.nan,
                     'close_break_rate_all_fills':cb/n if n else np.nan,
                     'max_high_ext_p25':h.max_high_extension.quantile(.25) if nh else np.nan,
                     'max_high_ext_p50':h.max_high_extension.quantile(.50) if nh else np.nan,
                     'max_high_ext_p75':h.max_high_extension.quantile(.75) if nh else np.nan,
                     'max_high_ext_p90':h.max_high_extension.quantile(.90) if nh else np.nan,
                     'max_close_ext_p25':h.max_close_extension.quantile(.25) if nh else np.nan,
                     'max_close_ext_p50':h.max_close_extension.quantile(.50) if nh else np.nan,
                     'max_close_ext_p75':h.max_close_extension.quantile(.75) if nh else np.nan,
                     'max_close_ext_p90':h.max_close_extension.quantile(.90) if nh else np.nan})
        for name, ext in LEVELS.items():
            hr=int(h[f'{name}_high_reach'].sum()) if nh else 0
            cr=int(h[f'{name}_close_reach'].sum()) if nh else 0
            mins=pd.to_numeric(h.loc[h[f'{name}_high_reach'].astype(bool),f'{name}_minutes_from_h2'],errors='coerce') if nh else pd.Series(dtype=float)
            atlas.append({'partition':part,'extension':name,'extension_frac':ext,'f75_fills':n,'h2_count':nh,
                          'high_reach_count':hr,'high_reach_rate_given_h2':hr/nh if nh else np.nan,
                          'high_reach_rate_all_fills':hr/n if n else np.nan,
                          'close_reach_count':cr,'close_reach_rate_given_h2':cr/nh if nh else np.nan,
                          'close_reach_rate_all_fills':cr/n if n else np.nan,
                          'median_minutes_h2_to_high_reach':float(mins.median()) if len(mins) else np.nan})
    sm=pd.DataFrame(sums); at=pd.DataFrame(atlas)
    sm.to_csv(OUT_SUM,index=False); at.to_csv(OUT_ATLAS,index=False)
    status='ETH_LONG_B27Y_ADAPT_EXTENSION_ATLAS_PASS'; OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG B27Y-Adapt — F75 Post-H2 Breakout Extension Atlas — Result','',
        f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** Frozen B27W-Adapt F75 fill identity and H2 timestamps are reused; H2 is a milestone, not TP.','',
        '## Breakout acceptance and extension distribution','',
        '| Partition | F75 fills | H2 | H2 rate | 5m close > H given H2 | Close > H all fills | High ext P25 | P50 | P75 | P90 | Close ext P50 | P75 | P90 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.f75_fills} | {r.h2_count} | {pct(r.h2_rate)} | {pct(r.close_break_rate_given_h2)} | {pct(r.close_break_rate_all_fills)} | {num(r.max_high_ext_p25)} | {num(r.max_high_ext_p50)} | {num(r.max_high_ext_p75)} | {num(r.max_high_ext_p90)} | {num(r.max_close_ext_p50)} | {num(r.max_close_ext_p75)} | {num(r.max_close_ext_p90)} |')
    md += ['','## Frozen extension atlas','',
           '| Partition | Extension | High reach / H2 | High reach / all fills | Close reach / H2 | Close reach / all fills | Median min H2→reach |',
           '|---|---|---:|---:|---:|---:|---:|']
    for r in at.itertuples(index=False):
        md.append(f'| {r.partition} | {r.extension} | {pct(r.high_reach_rate_given_h2)} | {pct(r.high_reach_rate_all_fills)} | {pct(r.close_reach_rate_given_h2)} | {pct(r.close_reach_rate_all_fills)} | {num(r.median_minutes_h2_to_high_reach)} |')
    md += ['',f'**Status: {status}**','',
           'No TP or stop is selected here. Next milestone: B27Z-Adapt economic target/invalidation selection. Research only.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
