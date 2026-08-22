#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_LONDON_NY_SESSION_DIRECTION_B27AP_Result.md'
OUT_DAILY = ROOT / 'BTC_LONDON_NY_SESSION_DIRECTION_B27AP_Daily.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SESSION_DIRECTION_B27AP_Summary.csv'

LON_N = 66
NY_N = 78


def analyze_day(lon: pd.DataFrame, ny: pd.DataFrame, date_utc: str) -> dict:
    assert len(lon) == LON_N and len(ny) == NY_N
    H = float(lon.high.max()); L = float(lon.low.min()); R = H-L
    assert R > 0
    op = float(ny.iloc[0].open); cl = float(ny.iloc[-1].close)
    ret = cl/op - 1.0
    direction = 'UP' if ret > 0 else ('DOWN' if ret < 0 else 'FLAT')

    hb = ny[ny.close.astype(float) > H]
    lb = ny[ny.close.astype(float) < L]
    hts = hb.index[0] if len(hb) else pd.NaT
    lts = lb.index[0] if len(lb) else pd.NaT
    if pd.isna(hts) and pd.isna(lts):
        first = 'NONE'
    elif pd.isna(lts):
        first = 'HIGH_FIRST'
    elif pd.isna(hts):
        first = 'LOW_FIRST'
    elif hts < lts:
        first = 'HIGH_FIRST'
    elif lts < hts:
        first = 'LOW_FIRST'
    else:
        first = 'SAME_BAR_BOTH'

    up_ext = max(0.0, (float(ny.high.max()) - H)/R)
    dn_ext = max(0.0, (L - float(ny.low.min()))/R)
    return {
        'date_utc': date_utc,
        'year': int(date_utc[:4]),
        'london_high': H, 'london_low': L, 'range': R,
        'ny_open': op, 'ny_close': cl, 'ny_return': ret, 'direction': direction,
        'high_close_break': bool(len(hb)), 'low_close_break': bool(len(lb)),
        'first_boundary_break': first,
        'first_high_break_bar_start': hts, 'first_low_break_bar_start': lts,
        'max_up_extension_r': up_ext, 'max_down_extension_r': dn_ext,
    }


def synthetic_test() -> None:
    d = pd.Timestamp('2026-01-05', tz='UTC')
    li = pd.date_range(d+pd.Timedelta(hours=8), periods=LON_N, freq='5min')
    ni = pd.date_range(d+pd.Timedelta(hours=13, minutes=30), periods=NY_N, freq='5min')
    lon = pd.DataFrame({'open':95.0,'high':100.0,'low':90.0,'close':95.0}, index=li)
    rows=[]
    for i in range(NY_N):
        rows.append({'open':95+i*.01,'high':99.0,'low':91.0,'close':95.0})
    ny = pd.DataFrame(rows,index=ni)
    ny.iloc[5, ny.columns.get_loc('close')] = 100.5
    ny.iloc[5, ny.columns.get_loc('high')] = 101.0
    ny.iloc[-1, ny.columns.get_loc('close')] = 101.0
    z=analyze_day(lon,ny,'2026-01-05')
    assert z['direction']=='UP' and z['high_close_break'] and not z['low_close_break']
    assert z['first_boundary_break']=='HIGH_FIRST'


def summarize(g: pd.DataFrame, label: str) -> dict:
    n=len(g)
    up=int((g.direction=='UP').sum()); down=int((g.direction=='DOWN').sum()); flat=int((g.direction=='FLAT').sum())
    hc=int(g.high_close_break.astype(bool).sum()); lc=int(g.low_close_break.astype(bool).sum())
    first_h=int((g.first_boundary_break=='HIGH_FIRST').sum())
    first_l=int((g.first_boundary_break=='LOW_FIRST').sum())
    none=int((g.first_boundary_break=='NONE').sum())
    both=int((g.first_boundary_break=='SAME_BAR_BOTH').sum())
    return {
        'period':label,'n_sessions':n,
        'up_sessions':up,'up_rate':up/n if n else np.nan,
        'down_sessions':down,'down_rate':down/n if n else np.nan,
        'flat_sessions':flat,'flat_rate':flat/n if n else np.nan,
        'mean_ny_return':float(g.ny_return.mean()) if n else np.nan,
        'median_ny_return':float(g.ny_return.median()) if n else np.nan,
        'high_close_breaks':hc,'high_close_break_rate':hc/n if n else np.nan,
        'low_close_breaks':lc,'low_close_break_rate':lc/n if n else np.nan,
        'high_first':first_h,'high_first_rate':first_h/n if n else np.nan,
        'low_first':first_l,'low_first_rate':first_l/n if n else np.nan,
        'none_first':none,'none_first_rate':none/n if n else np.nan,
        'same_bar_both':both,
        'median_up_extension_r':float(g.max_up_extension_r.median()) if n else np.nan,
        'median_down_extension_r':float(g.max_down_extension_r.median()) if n else np.nan,
    }


def main() -> None:
    synthetic_test()
    x5, coverage = b21.load5()
    assert abs(float(coverage)-1.0) < 1e-12
    assert x5.index.tz is not None

    rows=[]
    dates=pd.Index(x5.index.normalize().unique()).sort_values()
    for d in dates:
        if pd.Timestamp(d).weekday() >= 5:
            continue
        lon=x5[(x5.index >= d+pd.Timedelta(hours=8)) & (x5.index < d+pd.Timedelta(hours=13,minutes=30))]
        ny=x5[(x5.index >= d+pd.Timedelta(hours=13,minutes=30)) & (x5.index < d+pd.Timedelta(hours=20))]
        if len(lon)!=LON_N or len(ny)!=NY_N:
            continue
        if lon.index[0] != d+pd.Timedelta(hours=8) or lon.index[-1] != d+pd.Timedelta(hours=13,minutes=25):
            continue
        if ny.index[0] != d+pd.Timedelta(hours=13,minutes=30) or ny.index[-1] != d+pd.Timedelta(hours=19,minutes=55):
            continue
        rows.append(analyze_day(lon,ny,pd.Timestamp(d).strftime('%Y-%m-%d')))

    daily=pd.DataFrame(rows)
    assert len(daily) > 500
    assert not (daily.first_boundary_break=='SAME_BAR_BOTH').any()
    daily.to_csv(OUT_DAILY,index=False)

    sums=[summarize(daily,'ALL')]
    for y,g in daily.groupby('year',sort=True):
        sums.append(summarize(g,str(int(y))))
    sm=pd.DataFrame(sums)
    sm.to_csv(OUT_SUM,index=False)

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def bp(x): return '-' if pd.isna(x) else f'{10000*float(x):+.2f} bp'
    def num(x): return '-' if pd.isna(x) else f'{float(x):.3f}'

    md=[
        '# B27AP — BTC London->NY Session Direction Bias Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** This census uses all complete weekday London/NY sessions and no trading signal or regime selection.','',
        '| Period | N | UP | DOWN | Mean NY ret | Median NY ret | Close>London H | Close<London L | High first | Low first | No break | Med up ext | Med down ext |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for r in sm.itertuples(index=False):
        md.append(f'| {r.period} | {r.n_sessions} | {pct(r.up_rate)} | {pct(r.down_rate)} | {bp(r.mean_ny_return)} | {bp(r.median_ny_return)} | {pct(r.high_close_break_rate)} | {pct(r.low_close_break_rate)} | {pct(r.high_first_rate)} | {pct(r.low_first_rate)} | {pct(r.none_first_rate)} | {num(r.median_up_extension_r)}R | {num(r.median_down_extension_r)}R |')
    md += ['','Interpretation is descriptive only. A small majority/plurality is not equivalent to an always-bullish session.','', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__':
    main()
