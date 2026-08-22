#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_CSV = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
WINDOWS_CSV = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_Summary.csv'
OUT_SELECT = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_Selection.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_F85_EXTENSION_ECON_B27Z_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
TARGETS = {'E10':0.10,'E15':0.15,'E20':0.20}
STOPS = {'D30':0.30,'D40':0.40,'D50':0.50,'D60':0.60}
ENTRY_F = 0.85


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_f85() -> pd.DataFrame:
    e = pd.read_csv(ENTRIES_CSV)
    e = e[(e.entry_name=='F85') & (e.filled.astype(str).str.lower()=='true')].copy()
    for c in ('signal_ts','eligible_start','h2_bar_start','opposite_break_bar_start','entry_ts'):
        e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')

    w = pd.read_csv(WINDOWS_CSV)
    for c in ('signal_ts','session_end','h2_bar_start'):
        w[c] = pd.to_datetime(w[c], utc=True, errors='coerce')
    w = w[['partition','date_utc','signal_ts','session_end','h2_bar_start']].copy()

    z = e.merge(w, on=['partition','date_utc','signal_ts'], how='left', suffixes=('_entry','_window'), validate='many_to_one')
    assert z.session_end.notna().all()

    # The entry file and window file must agree on H2 whenever present.
    a = pd.to_datetime(z.h2_bar_start_entry, utc=True, errors='coerce')
    b = pd.to_datetime(z.h2_bar_start_window, utc=True, errors='coerce')
    same = (a.isna() & b.isna()) | (a == b)
    assert bool(same.all())
    z['h2_bar_start'] = b
    z = z.sort_values(['partition','entry_ts','signal_ts']).reset_index(drop=True)
    return z


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x>0].sum())
    neg = float(-x[x<0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos/neg if neg > 0 else np.nan


def time_exit(x5: pd.DataFrame, session_end: pd.Timestamp, entry_px: float, entry_ts: pd.Timestamp):
    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5):
        return None
    ts = x5.index[pos]
    px = float(x5.iloc[pos].open)
    return ts, px, 'TIME_EXIT_SESSION_END'


def simulate_one(x5: pd.DataFrame, r: pd.Series, target_name: str, stop_name: str) -> dict:
    H = float(r.H); L = float(r.L); rng = H-L
    entry_px = float(r.entry_px)
    entry_ts = pd.Timestamp(r.entry_ts)
    session_end = pd.Timestamp(r.session_end)
    h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT

    ext = TARGETS[target_name]
    dist = STOPS[stop_name]
    target_px = H + ext*rng
    stop_f = ENTRY_F - dist
    boundary_px = L + stop_f*rng
    nominal_rr = (target_px-entry_px)/(entry_px-boundary_px)

    base = {
        'partition': r.partition,
        'date_utc': r.date_utc,
        'signal_ts': pd.Timestamp(r.signal_ts),
        'entry_ts': entry_ts,
        'entry_px': entry_px,
        'H': H,
        'L': L,
        'range': rng,
        'h2_bar_start': h2,
        'target_name': target_name,
        'target_extension': ext,
        'target_px': target_px,
        'stop_name': stop_name,
        'stop_distance': dist,
        'stop_fraction': stop_f,
        'invalidation_boundary_px': boundary_px,
        'nominal_rr': nominal_rr,
    }

    q = fast_slice(x5, entry_ts, session_end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError('missing raw 5m entry bar')

    # B27W identity / geometry assertions from raw 5m.
    er = q.iloc[0]
    if not (float(er.low) <= entry_px <= float(er.high)):
        raise AssertionError('B27W F85 entry does not reproduce on raw 5m')
    expected_entry = L + ENTRY_F*rng
    if abs(entry_px-expected_entry) > 1e-9*max(1.0,abs(expected_entry)):
        raise AssertionError('entry is not exact F85')
    if pd.notna(h2) and not (entry_ts < h2):
        raise AssertionError('entry is not strictly before H2')
    if not (L < boundary_px < entry_px < H < target_px):
        raise AssertionError('invalid trade geometry')

    accepted_close_before_exit = False
    h2_seen = False
    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None

    for k,(ts,bar) in enumerate(q.iterrows()):
        close = float(bar.close)
        high = float(bar.high)

        if pd.notna(h2) and ts >= h2:
            h2_seen = True

        # On entry bar, target is impossible under frozen B27W because H2 cannot be the entry bar.
        # Close invalidation is known only at the completed bar close.
        if k == 0:
            if close < boundary_px:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = close
                reason = 'CLOSE_INVALIDATION_ENTRY_BAR'
                break
            if close > H:
                # This should be impossible if B27W entry is before H2, but retain a hard assertion.
                raise AssertionError('entry bar closes above H despite pre-H2 entry contract')
            continue

        # TP is an intrabar resting limit. If reached, it executes before this bar's close is known.
        if high >= target_px:
            exit_bar_start = ts
            exit_ts = ts
            exit_px = target_px
            reason = f'TP_{target_name}'
            break

        # Only after failing to hit TP do we evaluate the completed close invalidation.
        if close < boundary_px:
            exit_bar_start = ts
            exit_ts = ts + BAR5
            exit_px = close
            reason = 'CLOSE_INVALIDATION'
            break

        # Completed acceptance above H is causal only after the bar closes and only if still in trade.
        if close > H:
            accepted_close_before_exit = True

    if reason is None:
        te = time_exit(x5, session_end, entry_px, entry_ts)
        if te is None:
            return {**base,'exit_bar_start':pd.NaT,'exit_ts':pd.NaT,'exit_px':np.nan,
                    'exit_reason':'CENSORED','gross_return':np.nan,'net_pnl_usd':np.nan,
                    'hold_minutes':np.nan,'h2_before_exit':h2_seen,
                    'accepted_close_above_H_before_exit':accepted_close_before_exit}
        exit_ts, exit_px, reason = te
        exit_bar_start = exit_ts
        if pd.notna(h2) and h2 < session_end:
            h2_seen = True

    gross = float(exit_px/entry_px - 1.0)
    net = gross*NOTIONAL - FEE
    hold = float((pd.Timestamp(exit_ts)-entry_ts)/pd.Timedelta(minutes=1))

    return {**base,'exit_bar_start':exit_bar_start,'exit_ts':exit_ts,'exit_px':float(exit_px),
            'exit_reason':reason,'gross_return':gross,'net_pnl_usd':net,'hold_minutes':hold,
            'h2_before_exit':bool(h2_seen),'accepted_close_above_H_before_exit':bool(accepted_close_before_exit)}


def synthetic_tests():
    idx = pd.date_range('2026-01-02 13:30', periods=7, freq='5min', tz='UTC')
    H,L = 100.0,90.0
    entry = 98.5
    session_end = idx[-1] + BAR5

    def row_base():
        return pd.Series({'partition':'x','date_utc':'2026-01-02','signal_ts':idx[0]-BAR5,
                          'entry_ts':idx[0],'entry_px':entry,'H':H,'L':L,
                          'session_end':session_end,'h2_bar_start':idx[2]})

    # Wick through D30 boundary F55=95.5 but close above it must survive, then H2 and E10 target.
    x = pd.DataFrame([
        {'open':99,'high':99,'low':98.0,'close':98.2},
        {'open':98.2,'high':99,'low':95.0,'close':96.0},
        {'open':96,'high':100.1,'low':96,'close':100.0},
        {'open':100,'high':101.2,'low':99.8,'close':100.8},
        {'open':100.8,'high':101,'low':100,'close':100.5},
        {'open':100.5,'high':101,'low':100,'close':100.5},
        {'open':100.5,'high':101,'low':100,'close':100.5},
    ], index=idx)
    z = simulate_one(x,row_base(),'E10','D30')
    assert z['exit_reason']=='TP_E10'

    # Close invalidation before H2.
    x2=x.copy(); x2.loc[idx[1],'close']=95.0; x2.loc[idx[1],'low']=94.5
    z2=simulate_one(x2,row_base(),'E10','D30')
    assert z2['exit_reason']=='CLOSE_INVALIDATION' and abs(z2['exit_px']-95.0)<1e-12

    # H2 itself is not an exit; target is reached only later.
    x3=x.copy(); x3.loc[idx[2],'high']=100.0; x3.loc[idx[2],'close']=99.9
    z3=simulate_one(x3,row_base(),'E10','D30')
    assert z3['exit_reason']=='TP_E10' and z3['exit_bar_start']==idx[3]

    # Target and later close invalidation on same bar: target wins because stop is close-based.
    x4=x.copy(); x4.loc[idx[3],'high']=101.5; x4.loc[idx[3],'low']=94.0; x4.loc[idx[3],'close']=95.0
    z4=simulate_one(x4,row_base(),'E10','D30')
    assert z4['exit_reason']=='TP_E10'

    # Time exit if neither target nor close invalidation occurs.
    x5=x.copy()
    x5.loc[idx[3:],'high']=100.5
    x5.loc[idx[3:],'close']=100.2
    # Append session-end open for time exit.
    x5.loc[session_end]={'open':100.4,'high':100.4,'low':100.4,'close':100.4}
    z5=simulate_one(x5,row_base(),'E20','D60')
    assert z5['exit_reason']=='TIME_EXIT_SESSION_END'


def summarize(g: pd.DataFrame) -> dict:
    x = pd.to_numeric(g.net_pnl_usd, errors='coerce').dropna()
    resolved = g.loc[x.index].copy()
    wins = x[x>0]
    losses = x[x<=0]
    return {
        'trades': int(len(x)),
        'tp_count': int(resolved.exit_reason.astype(str).str.startswith('TP_').sum()),
        'tp_rate': float(resolved.exit_reason.astype(str).str.startswith('TP_').mean()) if len(resolved) else np.nan,
        'close_invalidation_count': int(resolved.exit_reason.astype(str).str.startswith('CLOSE_INVALIDATION').sum()),
        'time_exit_count': int((resolved.exit_reason=='TIME_EXIT_SESSION_END').sum()),
        'wins': int((x>0).sum()),
        'losses': int((x<=0).sum()),
        'wr': float((x>0).mean()) if len(x) else np.nan,
        'pf': pf(x),
        'net_exp': float(x.mean()) if len(x) else np.nan,
        'total_net': float(x.sum()) if len(x) else np.nan,
        'median_win': float(wins.median()) if len(wins) else np.nan,
        'median_loss': float(losses.median()) if len(losses) else np.nan,
        'median_hold_minutes': float(resolved.hold_minutes.median()) if len(resolved) else np.nan,
        'h2_before_exit_rate': float(resolved.h2_before_exit.mean()) if len(resolved) else np.nan,
        'accept_close_before_exit_rate': float(resolved.accepted_close_above_H_before_exit.mean()) if len(resolved) else np.nan,
        'median_nominal_rr': float(resolved.nominal_rr.median()) if len(resolved) else np.nan,
    }


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def main():
    synthetic_tests()
    x5,coverage = b21.load5()
    src = load_f85()

    # Frozen source counts are derived directly from B27W F85 filled rows; no re-detection.
    assert set(src.partition.unique()).issubset(set(PARTS))
    assert src.entry_ts.notna().all()
    assert src.entry_px.notna().all()

    rows=[]
    for _,r in src.iterrows():
        for target in TARGETS:
            for stop in STOPS:
                rows.append(simulate_one(x5,r,target,stop))
    t=pd.DataFrame(rows)

    # Exact Cartesian identity: every frozen F85 fill must create exactly 12 rows.
    keycols=['partition','date_utc','signal_ts','entry_ts']
    expected=len(src)*len(TARGETS)*len(STOPS)
    assert len(t)==expected
    counts=t.groupby(keycols,dropna=False).size()
    assert (counts==len(TARGETS)*len(STOPS)).all()

    # Geometry and execution assertions on persisted real trades.
    for r in t.itertuples(index=False):
        rng=float(r.H-r.L)
        exp_entry=float(r.L)+ENTRY_F*rng
        exp_target=float(r.H)+TARGETS[r.target_name]*rng
        exp_stop=float(r.L)+(ENTRY_F-STOPS[r.stop_name])*rng
        assert abs(float(r.entry_px)-exp_entry)<1e-9*max(1.0,abs(exp_entry))
        assert abs(float(r.target_px)-exp_target)<1e-9*max(1.0,abs(exp_target))
        assert abs(float(r.invalidation_boundary_px)-exp_stop)<1e-9*max(1.0,abs(exp_stop))
        if str(r.exit_reason).startswith('CLOSE_INVALIDATION'):
            bs=pd.Timestamp(r.exit_bar_start)
            raw=x5.loc[bs]
            assert float(raw.close) < float(r.invalidation_boundary_px)
            assert abs(float(r.exit_px)-float(raw.close))<1e-9*max(1.0,abs(float(raw.close)))
        if str(r.exit_reason).startswith('TP_'):
            bs=pd.Timestamp(r.exit_bar_start)
            raw=x5.loc[bs]
            assert float(raw.high) >= float(r.target_px)
            assert abs(float(r.exit_px)-float(r.target_px))<1e-9*max(1.0,abs(float(r.target_px)))
        assert pd.Timestamp(r.exit_ts) >= pd.Timestamp(r.entry_ts)

    t.to_csv(OUT_TRADES,index=False)

    sums=[]
    for part in PARTS:
        for target in TARGETS:
            for stop in STOPS:
                g=t[(t.partition==part)&(t.target_name==target)&(t.stop_name==stop)]
                sums.append({'partition':part,'target_name':target,'stop_name':stop,**summarize(g)})
    sm=pd.DataFrame(sums)

    passmap={}
    for target in TARGETS:
        for stop in STOPS:
            z=sm[(sm.partition.isin(MAJOR))&(sm.target_name==target)&(sm.stop_name==stop)]
            passed=bool(len(z)==3 and (z.trades>=30).all() and (z.wr>=0.70).all() and (z.net_exp>0).all() and (z.pf>=1.20).all())
            passmap[(target,stop)]=passed
    sm['screen_pass']=[passmap[(r.target_name,r.stop_name)] for r in sm.itertuples(index=False)]
    sm.to_csv(OUT_SUM,index=False)

    selections=[]
    for (target,stop),passed in passmap.items():
        z=sm[(sm.partition.isin(MAJOR))&(sm.target_name==target)&(sm.stop_name==stop)]
        selections.append({'target_name':target,'stop_name':stop,'screen_pass':passed,
                           'min_wr_major':float(z.wr.min()),'min_pf_major':float(z.pf.min()),
                           'min_net_exp_major':float(z.net_exp.min()),'pooled_total_net_major':float(z.total_net.sum())})
    sel=pd.DataFrame(selections).sort_values(['screen_pass','min_pf_major','min_wr_major','pooled_total_net_major'],ascending=[False,False,False,False])
    sel.to_csv(OUT_SELECT,index=False)

    pd.DataFrame(t.exit_reason.value_counts(dropna=False)).to_csv(OUT_STATUS)

    md=['# B27Z — London -> New York F85 Extension Economic Backtest — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** B27W F85 entries are frozen; H2 is a milestone only; B27Z tests E10/E15/E20 breakout targets with D30/D40/D50/D60 5m-close invalidation.','',
        '## Economic results','',
        '| Partition | TP | Stop | Trades | TP rate | WR | PF | Net exp | Total net | H2 before exit | Close>H accepted before exit | Nominal RR |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {r.target_name} | {r.stop_name} | {r.trades} | {pct(r.tp_rate)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.h2_before_exit_rate)} | {pct(r.accept_close_before_exit_rate)} | {num(r.median_nominal_rr)} |')

    md += ['','## Screen','']
    good=[f'{tgt}/{stp}' for (tgt,stp),v in passmap.items() if v]
    if good:
        md.append('**PASS:** '+', '.join(good))
    else:
        md.append('**No target/stop pair passed the frozen three-partition screen.**')

    md += ['','## Ranking snapshot','',
           '| TP | Stop | Pass | Min WR major | Min PF major | Min net exp major | Pooled major net |',
           '|---|---|---:|---:|---:|---:|---:|']
    for r in sel.itertuples(index=False):
        md.append(f'| {r.target_name} | {r.stop_name} | {str(bool(r.screen_pass))} | {pct(r.min_wr_major)} | {num(r.min_pf_major)} | ${num(r.min_net_exp_major)} | ${num(r.pooled_total_net_major)} |')

    md += ['','Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')


if __name__=='__main__':
    main()
