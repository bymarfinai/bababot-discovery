#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Candidates.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_POST_H2_EXTENSION_B27AM_Result.md'
OUT_PATHS = ROOT / 'BTC_LONDON_NY_SHORT_F15_POST_H2_EXTENSION_B27AM_Paths.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_POST_H2_EXTENSION_B27AM_Summary.csv'
OUT_ATLAS = ROOT / 'BTC_LONDON_NY_SHORT_F15_POST_H2_EXTENSION_B27AM_ExtensionAtlas.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_POST_H2_EXTENSION_B27AM_Status.txt'

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


def b(v) -> bool:
    return str(v).lower() == 'true' if not isinstance(v, (bool, np.bool_)) else bool(v)


def load_f15() -> pd.DataFrame:
    x = pd.read_csv(CAND)
    x = x[x.entry_name.astype(str) == 'F15'].copy()
    x = x[x.filled.map(b)].copy()
    for c in ('signal_ts','eligible_start','h2_bar_start','opposite_break_bar_start','session_end','fill_bar_start'):
        if c in x.columns:
            x[c] = pd.to_datetime(x[c], utc=True, errors='coerce')
    x['h2_after_fill'] = x['h2_after_fill'].map(b)
    for c in ('entry_px','H','L','range','entry_fraction'):
        x[c] = pd.to_numeric(x[c], errors='raise')
    return x.sort_values(['partition','fill_bar_start']).reset_index(drop=True)


def analyze_h2_slice(q: pd.DataFrame, H: float, L: float, h2_start: pd.Timestamp) -> dict:
    R = H - L
    assert R > 0 and len(q) > 0 and q.index[0] == h2_start
    assert float(q.iloc[0].low) <= L

    cb = q[q.close.astype(float) < L]
    first_close_break_start = cb.index[0] if len(cb) else pd.NaT
    first_close_break_ts = first_close_break_start + BAR5 if len(cb) else pd.NaT

    max_low_ext = (L - float(q.low.min())) / R
    max_close_ext = (L - float(q.close.min())) / R
    out = {
        'first_close_break_bar_start': first_close_break_start,
        'first_close_break_ts': first_close_break_ts,
        'max_low_extension': max_low_ext,
        'max_close_extension': max_close_ext,
    }
    for name, e in LEVELS.items():
        px = L - e * R
        lo = q[q.low.astype(float) <= px]
        cl = q[q.close.astype(float) <= px]
        out[f'{name}_price'] = px
        out[f'{name}_low_reach'] = bool(len(lo))
        out[f'{name}_low_reach_bar_start'] = lo.index[0] if len(lo) else pd.NaT
        out[f'{name}_minutes_from_h2'] = float((lo.index[0] - h2_start) / pd.Timedelta(minutes=1)) if len(lo) else np.nan
        out[f'{name}_close_reach'] = bool(len(cl))
        out[f'{name}_close_reach_ts'] = cl.index[0] + BAR5 if len(cl) else pd.NaT
    return out


def synthetic_tests() -> None:
    idx = pd.date_range('2026-01-05 14:00', periods=5, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    q = pd.DataFrame([
        {'open':91.0,'high':91.2,'low':89.8,'close':90.3},  # H2, no close break
        {'open':90.3,'high':90.5,'low':88.8,'close':89.6},  # later close break, E10 wick
        {'open':89.6,'high':90.0,'low':86.8,'close':87.4},  # E30 wick, E25 close
        {'open':87.4,'high':88.0,'low':84.5,'close':85.8},  # E50 wick, E40 close
        {'open':85.8,'high':87.0,'low':85.5,'close':86.5},
    ], index=idx)
    z = analyze_h2_slice(q,H,L,idx[0])
    assert z['first_close_break_bar_start'] == idx[1]
    assert z['E10_low_reach'] and pd.notna(z['E15_low_reach_bar_start'])
    assert z['E50_low_reach'] and not z['E50_close_reach']
    assert abs(z['max_low_extension'] - 0.55) < 1e-12
    q2 = q.copy(); q2.loc[idx[0],'close'] = 89.9
    z2 = analyze_h2_slice(q2,H,L,idx[0])
    assert z2['first_close_break_bar_start'] == idx[0]


def main() -> None:
    synthetic_tests()
    x5, coverage = b21.load5()
    assert len(x5) == 698112, len(x5)
    assert abs(float(coverage)-1.0) < 1e-12, coverage
    e = load_f15()

    frozen = {
        'external': (50,37),
        'development': (79,59),
        'reference_validation': (34,24),
        'august': (1,1),
    }
    for part,(nf,nh) in frozen.items():
        g = e[e.partition == part]
        assert len(g) == nf, (part,len(g),nf)
        assert int(g.h2_after_fill.sum()) == nh, (part,int(g.h2_after_fill.sum()),nh)

    rows = []
    for _, r in e.iterrows():
        H=float(r.H); L=float(r.L); R=H-L
        fill=pd.Timestamp(r.fill_bar_start); end=pd.Timestamp(r.session_end)
        assert abs(float(r.entry_fraction)-0.15) < 1e-12
        expected = L + 0.15*R
        assert abs(float(r.entry_px)-expected) < 1e-9*max(1.0,abs(expected))
        base = {
            'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,
            'fill_bar_start':fill,'entry_px':float(r.entry_px),'H':H,'L':L,'range':R,
            'b27ak_h2_after_fill':bool(r.h2_after_fill),'h2_bar_start':r.h2_bar_start,'session_end':end,
        }
        if not bool(r.h2_after_fill) or pd.isna(r.h2_bar_start):
            z={'has_h2':False,'first_close_break_bar_start':pd.NaT,'first_close_break_ts':pd.NaT,
               'max_low_extension':np.nan,'max_close_extension':np.nan}
            for name,val in LEVELS.items():
                z[f'{name}_price']=L-val*R
                z[f'{name}_low_reach']=False; z[f'{name}_low_reach_bar_start']=pd.NaT
                z[f'{name}_minutes_from_h2']=np.nan; z[f'{name}_close_reach']=False; z[f'{name}_close_reach_ts']=pd.NaT
            rows.append({**base,**z})
            continue

        h2 = pd.Timestamp(r.h2_bar_start)
        assert fill < h2
        q = fast_slice(x5,h2,end)
        if q.empty or q.index[0] != h2:
            raise AssertionError('missing frozen H2 raw bar')
        if float(q.iloc[0].low) > L:
            raise AssertionError('frozen B27AK H2 does not reach L')
        z = analyze_h2_slice(q,H,L,h2)
        rows.append({**base,'has_h2':True,**z})

    p = pd.DataFrame(rows)
    for r in p[p.has_h2.astype(bool)].itertuples(index=False):
        assert pd.Timestamp(r.fill_bar_start) < pd.Timestamp(r.h2_bar_start)
        if pd.notna(r.first_close_break_bar_start):
            assert pd.Timestamp(r.first_close_break_bar_start) >= pd.Timestamp(r.h2_bar_start)
        for name,val in LEVELS.items():
            expected = float(r.L) - val*(float(r.H)-float(r.L))
            assert abs(float(getattr(r,f'{name}_price'))-expected) < 1e-9*max(1.0,abs(expected))

    p.to_csv(OUT_PATHS,index=False)
    sums=[]; atlas=[]
    for part in PARTS:
        g=p[p.partition==part].copy(); h=g[g.has_h2.astype(bool)].copy()
        n=len(g); nh=len(h); cb=int(h.first_close_break_bar_start.notna().sum())
        sums.append({
            'partition':part,'f15_fills':n,'h2_count':nh,'h2_rate':nh/n if n else np.nan,
            'close_break_count':cb,'close_break_rate_given_h2':cb/nh if nh else np.nan,
            'close_break_rate_all_fills':cb/n if n else np.nan,
            'max_low_ext_p25':h.max_low_extension.quantile(.25) if nh else np.nan,
            'max_low_ext_p50':h.max_low_extension.quantile(.50) if nh else np.nan,
            'max_low_ext_p75':h.max_low_extension.quantile(.75) if nh else np.nan,
            'max_low_ext_p90':h.max_low_extension.quantile(.90) if nh else np.nan,
            'max_close_ext_p25':h.max_close_extension.quantile(.25) if nh else np.nan,
            'max_close_ext_p50':h.max_close_extension.quantile(.50) if nh else np.nan,
            'max_close_ext_p75':h.max_close_extension.quantile(.75) if nh else np.nan,
            'max_close_ext_p90':h.max_close_extension.quantile(.90) if nh else np.nan,
        })
        for name,val in LEVELS.items():
            lr=int(h[f'{name}_low_reach'].sum()) if nh else 0
            cr=int(h[f'{name}_close_reach'].sum()) if nh else 0
            mins=pd.to_numeric(h.loc[h[f'{name}_low_reach'].astype(bool),f'{name}_minutes_from_h2'],errors='coerce') if nh else pd.Series(dtype=float)
            atlas.append({
                'partition':part,'extension':name,'extension_frac':val,'f15_fills':n,'h2_count':nh,
                'low_reach_count':lr,'low_reach_rate_given_h2':lr/nh if nh else np.nan,
                'low_reach_rate_all_fills':lr/n if n else np.nan,
                'close_reach_count':cr,'close_reach_rate_given_h2':cr/nh if nh else np.nan,
                'close_reach_rate_all_fills':cr/n if n else np.nan,
                'median_minutes_h2_to_low_reach':float(mins.median()) if len(mins) else np.nan,
            })
    sm=pd.DataFrame(sums); at=pd.DataFrame(atlas)
    sm.to_csv(OUT_SUM,index=False); at.to_csv(OUT_ATLAS,index=False)

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x): return '-' if pd.isna(x) else f'{float(x):.3f}'
    md=['# B27AM — BTC London->NY SHORT F15 Post-H2 Breakdown Extension Atlas — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** Frozen B27AK F15 fill identities and H2 timestamps reproduced exactly; H2 is a milestone, not TP.','',
        '## Breakdown acceptance and downside extension distribution','',
        '| Partition | F15 fills | H2 | H2 rate | 5m close < L given H2 | Close < L all fills | Low ext P25 | P50 | P75 | P90 | Close ext P50 | P75 | P90 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.f15_fills} | {r.h2_count} | {pct(r.h2_rate)} | {pct(r.close_break_rate_given_h2)} | {pct(r.close_break_rate_all_fills)} | {num(r.max_low_ext_p25)} | {num(r.max_low_ext_p50)} | {num(r.max_low_ext_p75)} | {num(r.max_low_ext_p90)} | {num(r.max_close_ext_p50)} | {num(r.max_close_ext_p75)} | {num(r.max_close_ext_p90)} |')
    md += ['','## Frozen extension atlas','',
        '| Partition | Extension | Low reach / H2 | Low reach / all fills | Close reach / H2 | Close reach / all fills | Median min H2→reach |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in at.itertuples(index=False):
        md.append(f'| {r.partition} | {r.extension} | {pct(r.low_reach_rate_given_h2)} | {pct(r.low_reach_rate_all_fills)} | {pct(r.close_reach_rate_given_h2)} | {pct(r.close_reach_rate_all_fills)} | {num(r.median_minutes_h2_to_low_reach)} |')
    md += ['','No TP is selected in B27AM. This atlas exists to characterize SHORT reward-side continuation before any economic target is frozen.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    OUT_STATUS.write_text('B27AM_PASS\n')
    print('\n'.join(md))

if __name__ == '__main__':
    main()
