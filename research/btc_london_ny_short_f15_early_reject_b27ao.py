#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad

ROOT = Path(__file__).resolve().parent.parent
B27AK_CAND = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Candidates.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_REJECT_B27AO_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_REJECT_B27AO_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_REJECT_B27AO_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_REJECT_B27AO_Status.txt'

PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
RULES = ('BLIND_F15','EARLY_REJECT','SAME_BAR_REJECTION')
BAR5 = pd.Timedelta(minutes=5)


def to_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().map({'true': True, 'false': False}).fillna(False).astype(bool)


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def load_b27ak_f15() -> pd.DataFrame:
    x = pd.read_csv(B27AK_CAND)
    x = x[x.entry_name == 'F15'].copy()
    for c in ('signal_ts','fill_bar_start','h2_bar_start','opposite_break_bar_start','session_end'):
        if c in x.columns: x[c] = pd.to_datetime(x[c], utc=True, errors='coerce')
    x['filled'] = to_bool(x['filled'])
    x['h2_after_fill'] = to_bool(x['h2_after_fill'])
    return x.sort_values(['partition','signal_ts']).reset_index(drop=True)


def reconstruct(x5: pd.DataFrame):
    sig = b27ad.load_k1()
    windows = pd.DataFrame([b27ad.build_window(x5, r) for _, r in sig.iterrows()])
    blind = pd.DataFrame([b27ad.blind_f15(x5, w) for _, w in windows.iterrows()])
    return sig, windows, blind


def assert_b27ak_identity(blind: pd.DataFrame, ak: pd.DataFrame) -> None:
    b = blind.sort_values(['partition','signal_ts']).reset_index(drop=True)
    a = ak.sort_values(['partition','signal_ts']).reset_index(drop=True)
    assert len(a) == len(b)
    assert list(pd.to_datetime(a.signal_ts, utc=True)) == list(pd.to_datetime(b.signal_ts, utc=True))
    assert list(a.partition.astype(str)) == list(b.partition.astype(str))
    assert list(a.filled.astype(bool)) == list(b.blind_filled.astype(bool))
    assert list(a.h2_after_fill.astype(bool)) == list(b.h2_after_fill.astype(bool))
    for i in range(len(a)):
        if bool(a.loc[i,'filled']):
            assert pd.Timestamp(a.loc[i,'fill_bar_start']) == pd.Timestamp(b.loc[i,'blind_touch_bar_start'])
            assert abs(float(a.loc[i,'entry_px']) - float(b.loc[i,'blind_entry_px'])) < 1e-9 * max(1.0, abs(float(a.loc[i,'entry_px'])))
    expected = {'external':(50,37),'development':(79,59),'reference_validation':(34,24),'august':(1,1)}
    for part,(nf,nh) in expected.items():
        g = a[(a.partition==part) & a.filled]
        assert len(g)==nf and int(g.h2_after_fill.sum())==nh, (part,len(g),int(g.h2_after_fill.sum()))


def add_derived(r: dict) -> dict:
    z = dict(r)
    touch = pd.Timestamp(z['blind_touch_bar_start'])
    cb = z.get('confirmation_bar_start', pd.NaT)
    es = z.get('entry_start', pd.NaT)
    z['confirmed'] = bool(pd.notna(cb))
    z['minutes_touch_to_confirmation'] = float(((pd.Timestamp(cb)+BAR5)-touch)/pd.Timedelta(minutes=1)) if pd.notna(cb) else np.nan
    z['minutes_touch_to_entry'] = float((pd.Timestamp(es)-touch)/pd.Timedelta(minutes=1)) if pd.notna(es) else np.nan
    if bool(z.get('entry_executed',False)):
        entry=float(z['entry_px']); tgt=float(z['E20_DOWN']); stop=float(z['F65']); rng=float(z['range']); L=float(z['L'])
        z['actual_entry_fraction']=(entry-L)/rng
        risk=stop-entry; reward=entry-tgt
        z['nominal_rr']=reward/risk if risk>0 else np.nan
    else:
        z['actual_entry_fraction']=np.nan; z['nominal_rr']=np.nan
    return z


def make_rows(x5: pd.DataFrame, blind: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _, b in blind[blind.blind_filled.astype(bool)].iterrows():
        # Blind comparator.
        br = pd.Series(b27ad.make_blind_trade_row(b))
        bf = b27ad.simulate_fixed(x5, br)
        bd = dict(br); bd.update(bf); bd['confirmed']=True
        bd['minutes_touch_to_confirmation']=0.0; bd['minutes_touch_to_entry']=0.0
        bd['actual_entry_fraction']=0.15
        risk=float(bd['F65'])-float(bd['entry_px']); reward=float(bd['entry_px'])-float(bd['E20_DOWN'])
        bd['nominal_rr']=reward/risk if risk>0 else np.nan
        rows.append(bd)

        for same in (False, True):
            cr = pd.Series(b27ad.confirm_rejection_entry(x5, b, same_bar_only=same))
            fx = b27ad.simulate_fixed(x5, cr)
            d=dict(cr); d.update(fx)
            rows.append(add_derived(d))
    return pd.DataFrame(rows)


def assertions(tr: pd.DataFrame, x5: pd.DataFrame) -> None:
    for r in tr[tr.rule!='BLIND_F15'].itertuples(index=False):
        if bool(r.confirmed):
            cb=pd.Timestamp(r.confirmation_bar_start)
            pos=int(x5.index.searchsorted(cb,side='left')); assert x5.index[pos]==cb
            assert float(x5.iloc[pos].close) < float(r.F15)
            if pd.notna(r.h2_bar_start): assert cb < pd.Timestamp(r.h2_bar_start)
            if pd.notna(r.opposite_break_bar_start): assert cb < pd.Timestamp(r.opposite_break_bar_start)
        if bool(r.entry_executed):
            assert pd.Timestamp(r.entry_start)==pd.Timestamp(r.confirmation_bar_start)+BAR5
            pos=int(x5.index.searchsorted(pd.Timestamp(r.entry_start),side='left')); assert x5.index[pos]==pd.Timestamp(r.entry_start)
            assert abs(float(r.entry_px)-float(x5.iloc[pos].open)) < 1e-12*max(1.0,abs(float(r.entry_px)))
            assert float(r.L) < float(r.entry_px) < float(r.F65)
        if r.fixed_exit_reason=='CLOSE_INVALIDATION_F65':
            # exit timestamp is completed-bar timestamp; inspect bar start one interval earlier.
            bs=pd.Timestamp(r.entry_start) if pd.isna(r.fixed_hold_minutes) else pd.Timestamp(r.entry_start)+pd.Timedelta(minutes=float(r.fixed_hold_minutes))-BAR5
            pos=int(x5.index.searchsorted(bs,side='left'))
            if pos < len(x5) and x5.index[pos]==bs:
                assert float(x5.iloc[pos].close) > float(r.F65)
        if r.fixed_exit_reason=='TP_E20_DOWN':
            # Exact target price is mandatory.
            assert abs(float(r.fixed_exit_px)-float(r.E20_DOWN)) < 1e-9*max(1.0,abs(float(r.E20_DOWN)))


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for rule in RULES:
        for part in PARTS:
            g=tr[(tr.rule==rule)&(tr.partition==part)].copy()
            ex=g[g.entry_executed.astype(bool)].copy()
            n=len(ex); opp=len(g)
            pnl=pd.to_numeric(ex.fixed_net_pnl_usd,errors='coerce')
            rows.append({
                'rule':rule,'partition':part,'opportunities':opp,
                'confirmed':int(g.confirmed.astype(bool).sum()),
                'confirmation_rate':float(g.confirmed.astype(bool).mean()) if opp else np.nan,
                'executed':n,'execution_rate':n/opp if opp else np.nan,
                'same_bar_confirmations':int((g.confirmation_kind.astype(str)=='SAME_BAR').sum()) if 'confirmation_kind' in g else 0,
                'later_confirmations':int((g.confirmation_kind.astype(str)=='LATER_REJECT').sum()) if 'confirmation_kind' in g else 0,
                'median_touch_to_confirm_min':float(pd.to_numeric(g.minutes_touch_to_confirmation,errors='coerce').median()) if opp else np.nan,
                'median_touch_to_entry_min':float(pd.to_numeric(g.minutes_touch_to_entry,errors='coerce').median()) if opp else np.nan,
                'tp_rate':float((ex.fixed_exit_reason=='TP_E20_DOWN').mean()) if n else np.nan,
                'wr':float((pnl>0).mean()) if n else np.nan,
                'pf':pf(pnl),'expectancy_usd':float(pnl.mean()) if n else np.nan,
                'total_pnl_usd':float(pnl.sum()) if n else np.nan,
                'median_entry_fraction':float(pd.to_numeric(ex.actual_entry_fraction,errors='coerce').median()) if n else np.nan,
                'median_nominal_rr':float(pd.to_numeric(ex.nominal_rr,errors='coerce').median()) if n else np.nan,
                'h2_before_exit_rate':float(ex.fixed_h2_seen.astype(bool).mean()) if n else np.nan,
                'close_invalidations':int((ex.fixed_exit_reason=='CLOSE_INVALIDATION_F65').sum()) if n else 0,
                'time_exits':int((ex.fixed_exit_reason=='TIME_EXIT_SESSION_END').sum()) if n else 0,
            })
    return pd.DataFrame(rows)


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.3f}'


def main() -> None:
    # Reuse previously audited synthetic chronology tests for the exact SHORT confirmation/execution primitives.
    b27ad.synthetic_tests()
    x5,coverage=b27ad.b21.load5(); assert abs(float(coverage)-1.0)<1e-12
    sig,windows,blind=reconstruct(x5)
    ak=load_b27ak_f15(); assert_b27ak_identity(blind,ak)
    tr=make_rows(x5,blind); assertions(tr,x5)
    sm=summarize(tr)

    primary=sm[(sm.rule=='EARLY_REJECT') & sm.partition.isin(MAJOR)]
    screen=bool(len(primary)==3 and all((int(r.executed)>=30 and float(r.wr)>=0.70 and float(r.pf)>=1.20 and float(r.expectancy_usd)>0) for r in primary.itertuples(index=False)))
    status='B27AO_EARLY_REJECT_SCREEN_PASS' if screen else 'B27AO_EARLY_REJECT_NO_PASS'

    tr.to_csv(OUT_TRADES,index=False); sm.to_csv(OUT_SUM,index=False); OUT_STATUS.write_text(status+'\n')

    md=['# B27AO — BTC London->NY SHORT F15 Early-Reject Confirmation Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Independently discovered B27AK F15 fill/touch/H2 identities reproduced exactly before confirmation economics were interpreted.','',
        'Fixed economics: E20_DOWN target + D50/F65 completed-close invalidation. No regime gate or exit re-sweep.','',
        '## Confirmation economics','',
        '| Rule | Partition | Opps | Confirmed | Executed | TP rate | WR | PF | Exp/trade $ | Total $ | Median entry frac | Median nominal RR |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.rule} | {r.partition} | {r.opportunities} | {r.confirmed} ({pct(r.confirmation_rate)}) | {r.executed} | {pct(r.tp_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy_usd)} | {num(r.total_pnl_usd)} | {num(r.median_entry_fraction)} | {num(r.median_nominal_rr)} |')
    md += ['', '## Primary gate', '',
           'EARLY_REJECT requires in EACH external/development/reference_validation: >=30 executed, WR>=70%, PF>=1.20, expectancy>0.', '',
           f'**Status: {status}.**', '',
           'SAME_BAR_REJECTION remains diagnostic only. No F14/F16, candle threshold, regime filter, new stop, target, or runner is introduced.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__':
    main()
