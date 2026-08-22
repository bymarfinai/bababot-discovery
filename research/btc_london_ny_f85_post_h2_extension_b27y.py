#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
WINDOWS = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_F85_POST_H2_EXTENSION_B27Y_Result.md'
OUT_PATHS = ROOT / 'BTC_LONDON_NY_F85_POST_H2_EXTENSION_B27Y_Paths.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_F85_POST_H2_EXTENSION_B27Y_Summary.csv'
OUT_ATLAS = ROOT / 'BTC_LONDON_NY_F85_POST_H2_EXTENSION_B27Y_ExtensionAtlas.csv'

PARTS = ('external','development','reference_validation','august')
LEVELS = {
    'E05':0.05,'E10':0.10,'E15':0.15,'E20':0.20,
    'E25':0.25,'E30':0.30,'E40':0.40,'E50':0.50,
}
BAR5 = pd.Timedelta(minutes=5)


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_f85() -> pd.DataFrame:
    e = pd.read_csv(ENTRIES)
    w = pd.read_csv(WINDOWS)
    for c in ('signal_ts','entry_ts','eligible_start','h2_bar_start','opposite_break_bar_start'):
        if c in e.columns:
            e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')
    for c in ('signal_ts','session_end','h2_bar_start'):
        if c in w.columns:
            w[c] = pd.to_datetime(w[c], utc=True, errors='coerce')
    e = e[(e.entry_name=='F85') & (e.filled.astype(str).str.lower()=='true')].copy()
    keep = w[['partition','date_utc','signal_ts','session_end']].copy()
    e = e.merge(keep,on=['partition','date_utc','signal_ts'],how='left',validate='many_to_one')
    assert e.session_end.notna().all()
    return e.sort_values(['partition','entry_ts']).reset_index(drop=True)


def analyze_h2_slice(q: pd.DataFrame, H: float, L: float, h2_start: pd.Timestamp) -> dict:
    R = H-L
    assert R > 0 and len(q) > 0 and q.index[0] == h2_start
    assert float(q.iloc[0].high) >= H

    cb = q[ q.close.astype(float) > H ]
    first_close_break_start = cb.index[0] if len(cb) else pd.NaT
    first_close_break_ts = first_close_break_start + BAR5 if len(cb) else pd.NaT
    max_high_ext = (float(q.high.max())-H)/R
    max_close_ext = (float(q.close.max())-H)/R

    out = {
        'first_close_break_bar_start':first_close_break_start,
        'first_close_break_ts':first_close_break_ts,
        'max_high_extension':max_high_ext,
        'max_close_extension':max_close_ext,
    }
    for name,e in LEVELS.items():
        px = H + e*R
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
        {'open':99,'high':100.2,'low':98.8,'close':99.7}, # H2, no close break
        {'open':99.7,'high':101.2,'low':99.5,'close':100.4}, # later close break, E10 wick
        {'open':100.4,'high':103.2,'low':100.0,'close':102.6}, # E30 wick, E25 close
        {'open':102.6,'high':105.5,'low':102,'close':104.2}, # E50 wick, E40 close
        {'open':104.2,'high':104.5,'low':103,'close':103.5},
    ],index=idx)
    z=analyze_h2_slice(q,H,L,idx[0])
    assert z['first_close_break_bar_start']==idx[1]
    assert z['E10_high_reach'] and not z['E15_high_reach_bar_start'] is pd.NaT
    assert z['E50_high_reach'] and not z['E50_close_reach']
    assert abs(z['max_high_extension']-0.55)<1e-12
    # close-break can occur on H2 itself
    q2=q.copy(); q2.loc[idx[0],'close']=100.1
    z2=analyze_h2_slice(q2,H,L,idx[0])
    assert z2['first_close_break_bar_start']==idx[0]


def main():
    synthetic_tests()
    x5,coverage=b21.load5()
    e=load_f85()
    rows=[]
    for _,r in e.iterrows():
        H=float(r.H); L=float(r.L); R=H-L
        entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end)
        base={
            'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,
            'entry_ts':entry_ts,'entry_px':float(r.entry_px),'H':H,'L':L,'range':R,
            'b27w_target_hit':bool(r.target_hit),'h2_bar_start':r.h2_bar_start,'session_end':end,
        }
        expected=L+0.85*R
        assert abs(float(r.entry_px)-expected)<1e-9*max(1.0,abs(expected))
        if not bool(r.target_hit) or pd.isna(r.h2_bar_start):
            z={'has_h2':False,'first_close_break_bar_start':pd.NaT,'first_close_break_ts':pd.NaT,
               'max_high_extension':np.nan,'max_close_extension':np.nan}
            for name,val in LEVELS.items():
                z[f'{name}_price']=H+val*R
                z[f'{name}_high_reach']=False; z[f'{name}_high_reach_bar_start']=pd.NaT
                z[f'{name}_minutes_from_h2']=np.nan; z[f'{name}_close_reach']=False; z[f'{name}_close_reach_ts']=pd.NaT
            rows.append({**base,**z}); continue

        h2=pd.Timestamp(r.h2_bar_start)
        assert entry_ts < h2
        q=fast_slice(x5,h2,end)
        if q.empty or q.index[0]!=h2:
            raise AssertionError('missing frozen H2 raw bar')
        if float(q.iloc[0].high)<H:
            raise AssertionError('frozen B27W H2 does not reach H')
        z=analyze_h2_slice(q,H,L,h2)
        rows.append({**base,'has_h2':True,**z})

    p=pd.DataFrame(rows)
    # B27W identity count and partition counts are frozen.
    expected_counts={'external':46,'development':72,'reference_validation':31,'august':3}
    got=p.groupby('partition').size().to_dict()
    assert got==expected_counts, (got,expected_counts)
    for r in p[p.has_h2.astype(bool)].itertuples(index=False):
        assert pd.Timestamp(r.entry_ts) < pd.Timestamp(r.h2_bar_start)
        if pd.notna(r.first_close_break_bar_start):
            assert pd.Timestamp(r.first_close_break_bar_start) >= pd.Timestamp(r.h2_bar_start)
        for name,val in LEVELS.items():
            expected=float(r.H)+val*(float(r.H)-float(r.L))
            assert abs(float(getattr(r,f'{name}_price'))-expected)<1e-9*max(1.0,abs(expected))

    p.to_csv(OUT_PATHS,index=False)

    sums=[]; atlas=[]
    for part in PARTS:
        g=p[p.partition==part].copy(); h=g[g.has_h2.astype(bool)].copy()
        n=len(g); nh=len(h)
        cb=int(h.first_close_break_bar_start.notna().sum())
        sums.append({
            'partition':part,'f85_fills':n,'h2_count':nh,'h2_rate':nh/n if n else np.nan,
            'close_break_count':cb,'close_break_rate_given_h2':cb/nh if nh else np.nan,
            'close_break_rate_all_fills':cb/n if n else np.nan,
            'max_high_ext_p25':h.max_high_extension.quantile(.25) if nh else np.nan,
            'max_high_ext_p50':h.max_high_extension.quantile(.50) if nh else np.nan,
            'max_high_ext_p75':h.max_high_extension.quantile(.75) if nh else np.nan,
            'max_high_ext_p90':h.max_high_extension.quantile(.90) if nh else np.nan,
            'max_close_ext_p25':h.max_close_extension.quantile(.25) if nh else np.nan,
            'max_close_ext_p50':h.max_close_extension.quantile(.50) if nh else np.nan,
            'max_close_ext_p75':h.max_close_extension.quantile(.75) if nh else np.nan,
            'max_close_ext_p90':h.max_close_extension.quantile(.90) if nh else np.nan,
        })
        for name,val in LEVELS.items():
            hr=int(h[f'{name}_high_reach'].sum()) if nh else 0
            cr=int(h[f'{name}_close_reach'].sum()) if nh else 0
            mins=pd.to_numeric(h.loc[h[f'{name}_high_reach'].astype(bool),f'{name}_minutes_from_h2'],errors='coerce') if nh else pd.Series(dtype=float)
            atlas.append({
                'partition':part,'extension':name,'extension_frac':val,'f85_fills':n,'h2_count':nh,
                'high_reach_count':hr,'high_reach_rate_given_h2':hr/nh if nh else np.nan,
                'high_reach_rate_all_fills':hr/n if n else np.nan,
                'close_reach_count':cr,'close_reach_rate_given_h2':cr/nh if nh else np.nan,
                'close_reach_rate_all_fills':cr/n if n else np.nan,
                'median_minutes_h2_to_high_reach':float(mins.median()) if len(mins) else np.nan,
            })
    sm=pd.DataFrame(sums); at=pd.DataFrame(atlas)
    sm.to_csv(OUT_SUM,index=False); at.to_csv(OUT_ATLAS,index=False)

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x): return '-' if pd.isna(x) else f'{float(x):.3f}'
    md=['# B27Y — London -> New York F85 Post-H2 Breakout Extension Atlas — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** B27W F85 fill identity and H2 timestamps were frozen; H2 is treated as a milestone, not TP.','',
        '## Breakout acceptance and extension distribution','',
        '| Partition | F85 fills | H2 | H2 rate | 5m close > H given H2 | Close > H all fills | High ext P25 | P50 | P75 | P90 | Close ext P50 | P75 | P90 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.f85_fills} | {r.h2_count} | {pct(r.h2_rate)} | {pct(r.close_break_rate_given_h2)} | {pct(r.close_break_rate_all_fills)} | {num(r.max_high_ext_p25)} | {num(r.max_high_ext_p50)} | {num(r.max_high_ext_p75)} | {num(r.max_high_ext_p90)} | {num(r.max_close_ext_p50)} | {num(r.max_close_ext_p75)} | {num(r.max_close_ext_p90)} |')
    md += ['','## Frozen extension atlas','',
        '| Partition | Extension | High reach / H2 | High reach / all fills | Close reach / H2 | Close reach / all fills | Median min H2→reach |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in at.itertuples(index=False):
        md.append(f'| {r.partition} | {r.extension} | {pct(r.high_reach_rate_given_h2)} | {pct(r.high_reach_rate_all_fills)} | {pct(r.close_reach_rate_given_h2)} | {pct(r.close_reach_rate_all_fills)} | {num(r.median_minutes_h2_to_high_reach)} |')
    md += ['','No TP is selected in B27Y. This atlas exists to choose a breakout target later without pretending H2 itself is the exit.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
