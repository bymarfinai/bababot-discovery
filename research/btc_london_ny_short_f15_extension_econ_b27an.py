#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_retrace_zone_b27ak as b27ak

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
TARGETS = {'E10':0.10,'E15':0.15,'E20':0.20}
STOPS = {'D30':0.30,'D40':0.40,'D50':0.50,'D60':0.60}
ENTRY_F = 0.15
NOTIONAL = 500.0
FEE = 0.40


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def time_exit(x5: pd.DataFrame, end: pd.Timestamp):
    p = int(x5.index.searchsorted(end, side='left'))
    if p >= len(x5) or x5.index[p] != end:
        raise AssertionError('missing exact session-end open')
    return end, float(x5.iloc[p].open)


def simulate(x5: pd.DataFrame, r: pd.Series, tname: str, ext: float, sname: str, dist: float) -> dict:
    H = float(r.H); L = float(r.L); R = H-L
    entry = float(r.entry_px); entry_start = pd.Timestamp(r.fill_bar_start)
    end = pd.Timestamp(r.session_end)
    target = L - ext*R
    boundary_frac = ENTRY_F + dist
    boundary = L + boundary_frac*R
    assert R > 0
    assert abs(entry - (L + ENTRY_F*R)) < 1e-9*max(1.0,abs(entry))
    assert abs(target - (L-ext*R)) < 1e-9*max(1.0,abs(target))
    assert abs(boundary - (L+(ENTRY_F+dist)*R)) < 1e-9*max(1.0,abs(boundary))
    assert entry < boundary < H

    q = b27ad.fast_slice(x5, entry_start, end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing entry bar')

    reason = None; exit_bar = pd.NaT; exit_ts = pd.NaT; exit_px = np.nan
    for k, (ts, b) in enumerate(q.iterrows()):
        lo = float(b.low); cl = float(b.close)
        if k > 0 and lo <= target:
            reason = 'TP'; exit_bar = ts; exit_ts = ts; exit_px = target
            break
        if cl > boundary:
            reason = 'CLOSE_INVALIDATION'; exit_bar = ts; exit_ts = ts + BAR5; exit_px = cl
            break
    if reason is None:
        exit_ts, exit_px = time_exit(x5, end)
        exit_bar = end
        reason = 'TIME_EXIT'

    gross = (entry-exit_px)/entry
    net = gross*NOTIONAL - FEE
    hold = float((pd.Timestamp(exit_ts)-entry_start)/pd.Timedelta(minutes=1))
    h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    h2_before = bool(pd.notna(h2) and h2 <= pd.Timestamp(exit_bar))

    return {
        'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,
        'entry_bar_start':entry_start,'entry_px':entry,'H':H,'L':L,'range':R,
        'h2_bar_start':h2,'target_name':tname,'target_ext':ext,'target_px':target,
        'stop_name':sname,'stop_distance':dist,'boundary_fraction':boundary_frac,'boundary_px':boundary,
        'session_end':end,'exit_bar_start':exit_bar,'exit_ts':exit_ts,'exit_px':exit_px,
        'exit_reason':reason,'gross_return':gross,'net_pnl_usd':net,'win':bool(net>0),
        'hold_minutes':hold,'h2_before_exit':h2_before,
    }


def synthetic_tests() -> None:
    H,L=100.0,90.0; R=10.0; entry=L+.15*R
    idx=pd.date_range('2026-01-05 14:00',periods=6,freq='5min',tz='UTC')
    base={'partition':'x','date_utc':'2026-01-05','signal_ts':idx[0]-BAR5,
          'fill_bar_start':idx[0],'entry_px':entry,'H':H,'L':L,'range':R,
          'h2_bar_start':idx[1],'session_end':idx[5]}
    # Wick above F45 on fill bar but close below: survives; post-entry bar reaches E10 and closes above boundary -> TP precedence.
    x=pd.DataFrame([
        {'open':91.5,'high':95.0,'low':91.0,'close':93.0},
        {'open':93.0,'high':96.0,'low':88.8,'close':95.5},
        {'open':95.5,'high':96.0,'low':94.0,'close':95.0},
        {'open':95.0,'high':95.2,'low':93.0,'close':94.0},
        {'open':94.0,'high':94.2,'low':92.0,'close':93.0},
        {'open':93.0,'high':93.2,'low':92.0,'close':92.5},
    ],index=idx)
    z=simulate(x,pd.Series(base),'E10',.10,'D30',.30)
    assert z['exit_reason']=='TP' and abs(z['exit_px']-89.0)<1e-12
    # Fill-bar completed close above boundary invalidates immediately.
    x2=x.copy(); x2.loc[idx[0],'close']=95.0; x2.loc[idx[0],'high']=95.2
    z2=simulate(x2,pd.Series(base),'E10',.10,'D30',.30)
    assert z2['exit_reason']=='CLOSE_INVALIDATION' and abs(z2['exit_px']-95.0)<1e-12
    # H2 only is not an exit; no target/invalidation => time exit.
    x3=x.copy();
    x3.loc[idx[1],['high','low','close']]=[93.5,89.8,92.0]
    for t in idx[2:5]: x3.loc[t,['high','low','close']]=[93.0,90.2,92.0]
    z3=simulate(x3,pd.Series(base),'E10',.10,'D30',.30)
    assert z3['exit_reason']=='TIME_EXIT'


def reconstruct_f15(x5: pd.DataFrame) -> pd.DataFrame:
    s=b27ad.load_k1()
    windows=pd.DataFrame([b27ad.build_window(x5,r) for _,r in s.iterrows()])
    rows=[]
    for _,w in windows.iterrows():
        z=b27ak.candidate_fill(x5,w,'F15',ENTRY_F)
        rows.append(z)
    f=pd.DataFrame(rows)
    f=f[f.filled.astype(bool)].copy().sort_values(['partition','fill_bar_start']).reset_index(drop=True)
    expected={'external':(50,37),'development':(79,59),'reference_validation':(34,24),'august':(1,1)}
    for part,(nf,nh) in expected.items():
        g=f[f.partition==part]
        assert len(g)==nf,(part,len(g),nf)
        assert int(g.h2_after_fill.sum())==nh,(part,int(g.h2_after_fill.sum()),nh)
        assert ((pd.to_datetime(g.h2_bar_start,utc=True,errors='coerce') > pd.to_datetime(g.fill_bar_start,utc=True,errors='coerce')) | ~g.h2_after_fill.astype(bool)).all()
    return f


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for tname in TARGETS:
        for sname in STOPS:
            for part in PARTS:
                g=tr[(tr.target_name==tname)&(tr.stop_name==sname)&(tr.partition==part)].copy()
                wins=g[g.net_pnl_usd>0].net_pnl_usd; losses=g[g.net_pnl_usd<0].net_pnl_usd
                rows.append({
                    'target_name':tname,'stop_name':sname,'partition':part,'n':len(g),
                    'tp_count':int((g.exit_reason=='TP').sum()),'tp_rate':float((g.exit_reason=='TP').mean()) if len(g) else np.nan,
                    'close_invalidation_count':int((g.exit_reason=='CLOSE_INVALIDATION').sum()),
                    'time_exit_count':int((g.exit_reason=='TIME_EXIT').sum()),
                    'wr':float((g.net_pnl_usd>0).mean()) if len(g) else np.nan,
                    'pf':pf(g.net_pnl_usd),'expectancy':float(g.net_pnl_usd.mean()) if len(g) else np.nan,
                    'total_pnl':float(g.net_pnl_usd.sum()) if len(g) else np.nan,
                    'median_winner':float(wins.median()) if len(wins) else np.nan,
                    'median_loser':float(losses.median()) if len(losses) else np.nan,
                    'median_hold_minutes':float(g.hold_minutes.median()) if len(g) else np.nan,
                    'h2_before_exit_rate':float(g.h2_before_exit.mean()) if len(g) else np.nan,
                })
    return pd.DataFrame(rows)


def main() -> None:
    synthetic_tests()
    x5,coverage=b27ad.b21.load5()
    assert abs(float(coverage)-1.0)<1e-12
    f=reconstruct_f15(x5)
    rows=[]
    for _,r in f.iterrows():
        for tn,ext in TARGETS.items():
            for sn,d in STOPS.items():
                rows.append(simulate(x5,r,tn,ext,sn,d))
    tr=pd.DataFrame(rows)
    assert len(tr)==len(f)*len(TARGETS)*len(STOPS)
    # Real-data execution assertions.
    for r in tr.itertuples(index=False):
        if r.exit_reason=='TP':
            b=x5.loc[pd.Timestamp(r.exit_bar_start)]
            assert float(b.low) <= float(r.target_px)+1e-9
            assert abs(float(r.exit_px)-float(r.target_px))<1e-9*max(1.0,abs(float(r.target_px)))
        elif r.exit_reason=='CLOSE_INVALIDATION':
            b=x5.loc[pd.Timestamp(r.exit_bar_start)]
            assert float(b.close) > float(r.boundary_px)
            assert abs(float(r.exit_px)-float(b.close))<1e-9*max(1.0,abs(float(b.close)))
        else:
            assert pd.Timestamp(r.exit_ts)==pd.Timestamp(r.session_end)
    sm=summarize(tr)

    passing=[]
    for tn in TARGETS:
        for sn in STOPS:
            ok=True
            for part in MAJOR:
                r=sm[(sm.target_name==tn)&(sm.stop_name==sn)&(sm.partition==part)].iloc[0]
                ok = ok and int(r.n)>=30 and float(r.wr)>=0.70 and float(r.expectancy)>0 and float(r.pf)>=1.20
            if ok: passing.append(f'{tn}/{sn}')

    tr.to_csv(OUT_TRADES,index=False); sm.to_csv(OUT_SUM,index=False)
    status='B27AN_SCREEN_PASS_'+('_'.join(p.replace('/','_') for p in passing) if passing else 'NONE')
    OUT_STATUS.write_text(status+'\n')

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'
    md=['# B27AN — BTC London->NY SHORT F15 Extension Economic Backtest — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AK F15 identities reproduced exactly before economics; no regime or confirmation filter was introduced.','',
        '## Frozen economic grid','',
        '| Target | Stop | Partition | N | TP rate | WR | PF | Exp/trade $ | Total $ | Close invalid | Time exit | H2 before exit |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for tn in TARGETS:
        for sn in STOPS:
            for part in PARTS:
                r=sm[(sm.target_name==tn)&(sm.stop_name==sn)&(sm.partition==part)].iloc[0]
                md.append(f'| {tn} | {sn} | {part} | {int(r.n)} | {pct(r.tp_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {int(r.close_invalidation_count)} | {int(r.time_exit_count)} | {pct(r.h2_before_exit_rate)} |')
    md += ['','## Frozen screen','',
           'Requirement in EACH external/development/reference_validation partition: N>=30, WR>=70%, expectancy>0, PF>=1.20.','',
           '**Passing pairs: '+(', '.join(passing) if passing else 'NONE')+'.**','',
           'No additional target, stop distance, confirmation, regime gate, or runner is selected here.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__':
    main()
