#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad

ROOT = Path(__file__).resolve().parent.parent
BASE_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Trades.csv'
BASE_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Summary.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_WRONG_SIDE_PERSISTENCE_B27AS_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_WRONG_SIDE_PERSISTENCE_B27AS_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_WRONG_SIDE_PERSISTENCE_B27AS_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_WRONG_SIDE_PERSISTENCE_B27AS_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
RULES = {'P1':1,'P2':2,'P3':3}
NOTIONAL = 500.0
FEE = 0.40
EPS = 1e-12


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def load_baseline() -> pd.DataFrame:
    b = pd.read_csv(BASE_TRADES)
    b = b[(b.target_name == 'E20') & (b.stop_name == 'D50')].copy()
    for c in ('signal_ts','entry_bar_start','h2_bar_start','session_end','exit_bar_start','exit_ts'):
        b[c] = pd.to_datetime(b[c], utc=True, errors='coerce')
    for c in ('entry_px','H','L','range','target_px','boundary_px','net_pnl_usd'):
        b[c] = pd.to_numeric(b[c], errors='raise')
    expected = {'external':50,'development':79,'reference_validation':34,'august':1}
    for part,n in expected.items():
        g=b[b.partition==part]
        assert len(g)==n,(part,len(g),n)
    assert not b.duplicated(['partition','date_utc','signal_ts']).any()
    # Exact frozen geometry.
    f15 = b.L + 0.15*b['range']
    f65 = b.L + 0.65*b['range']
    e20 = b.L - 0.20*b['range']
    assert np.allclose(b.entry_px, f15, rtol=1e-12, atol=1e-9)
    assert np.allclose(b.boundary_px, f65, rtol=1e-12, atol=1e-9)
    assert np.allclose(b.target_px, e20, rtol=1e-12, atol=1e-9)
    return b.sort_values(['partition','entry_bar_start']).reset_index(drop=True)


def verify_baseline(b: pd.DataFrame) -> dict:
    s = pd.read_csv(BASE_SUM)
    s = s[(s.target_name=='E20') & (s.stop_name=='D50')].copy()
    out={}
    for part in PARTS:
        g=b[b.partition==part]
        vals=g.net_pnl_usd.astype(float)
        sr=s[s.partition==part].iloc[0]
        got=(len(g),float((vals>0).mean()),pf(vals),float(vals.mean()),float(vals.sum()))
        exp=(int(sr.n),float(sr.wr),float(sr.pf),float(sr.expectancy),float(sr.total_pnl))
        assert got[0]==exp[0]
        for gv,ev in zip(got[1:],exp[1:]):
            if math.isinf(gv) and math.isinf(ev): continue
            assert abs(gv-ev) < 1e-8*max(1.0,abs(ev)),(part,got,exp)
        out[part]=float(vals.sum())
    out['POOLED_MAJOR']=float(b[b.partition.isin(MAJOR)].net_pnl_usd.sum())
    assert abs(out['POOLED_MAJOR'] - (-11.66557892047709)) < 1e-8
    return out


def time_exit(x5: pd.DataFrame, end: pd.Timestamp):
    p=int(x5.index.searchsorted(end,side='left'))
    if p>=len(x5) or x5.index[p]!=end:
        raise AssertionError('missing exact session-end open')
    return end,float(x5.iloc[p].open)


def simulate(x5: pd.DataFrame, r: pd.Series, rule: str, need: int) -> dict:
    entry_start=pd.Timestamp(r.entry_bar_start)
    end=pd.Timestamp(r.session_end)
    entry=float(r.entry_px); L=float(r.L); f15=entry
    f65=float(r.boundary_px); target=float(r.target_px)
    frozen_h2=pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    q=b27ad.fast_slice(x5,entry_start,end)
    if q.empty or q.index[0]!=entry_start:
        raise AssertionError('missing entry slice')

    run=0; max_run=0; h2_seen=False
    reason=None; exit_bar=pd.NaT; exit_ts=pd.NaT; exit_px=np.nan
    persistence_bar=pd.NaT; persistence_run=0
    for k,(ts,bar) in enumerate(q.iterrows()):
        lo=float(bar.low); cl=float(bar.close)
        # Frozen B27AN resting target precedence; entry/fill bar cannot TP.
        if k>0 and lo <= target + EPS:
            reason='TP_E20_DOWN'; exit_bar=ts; exit_ts=ts; exit_px=target
            break

        hit_h2 = lo <= L + EPS
        if hit_h2:
            h2_seen=True
            # H2 is intrabar and therefore disables the pre-H2 detector before close.
            run=0
        elif not h2_seen:
            if cl > f15:
                run += 1
                max_run=max(max_run,run)
            else:
                run=0
            if run >= need:
                reason=f'PERSISTENCE_{rule}'
                exit_bar=ts; exit_ts=ts+BAR5; exit_px=cl
                persistence_bar=ts; persistence_run=run
                break

        # Frozen completed-close F65 invalidation remains active everywhere.
        if cl > f65:
            reason='CLOSE_INVALIDATION_F65'; exit_bar=ts; exit_ts=ts+BAR5; exit_px=cl
            break

    if reason is None:
        exit_ts,exit_px=time_exit(x5,end)
        exit_bar=end; reason='TIME_EXIT'

    gross=(entry-float(exit_px))/entry
    net=gross*NOTIONAL-FEE
    is_persist=reason.startswith('PERSISTENCE_')
    if is_persist:
        assert pd.notna(persistence_bar)
        assert float(x5.loc[persistence_bar].close) > f15
        if pd.notna(frozen_h2):
            assert persistence_bar < frozen_h2, (rule,persistence_bar,frozen_h2)
    # If frozen H2 occurred before exit-bar, detector must not have fired later.
    if pd.notna(frozen_h2) and is_persist:
        assert persistence_bar < frozen_h2

    return {
        'rule':rule,'need':need,'partition':r.partition,'date_utc':r.date_utc,
        'signal_ts':r.signal_ts,'entry_bar_start':entry_start,'entry_px':entry,
        'H':float(r.H),'L':L,'range':float(r['range']),'F15':f15,'F65':f65,
        'E20_DOWN':target,'frozen_h2_bar_start':frozen_h2,'session_end':end,
        'baseline_exit_reason':r.exit_reason,'baseline_net_pnl_usd':float(r.net_pnl_usd),
        'baseline_loser':bool(float(r.net_pnl_usd)<=0),
        'frozen_h2_failure':bool(pd.isna(frozen_h2)),
        'persistence_exit':is_persist,'persistence_bar_start':persistence_bar,
        'persistence_run':persistence_run,'max_pre_h2_run_seen':max_run,
        'exit_bar_start':exit_bar,'exit_ts':exit_ts,'exit_px':float(exit_px),
        'exit_reason':reason,'net_pnl_usd':net,'win':bool(net>0),
        'h2_before_exit':bool(h2_seen),
    }


def synthetic_tests() -> None:
    idx=pd.date_range('2026-01-05 14:00',periods=8,freq='5min',tz='UTC')
    base={'partition':'x','date_utc':'2026-01-05','signal_ts':idx[0]-BAR5,
          'entry_bar_start':idx[0],'entry_px':91.5,'H':100.0,'L':90.0,'range':10.0,
          'h2_bar_start':idx[5],'target_px':88.0,'boundary_px':96.5,
          'session_end':idx[7],'exit_reason':'TP','net_pnl_usd':1.0}
    # closes above F15, reset, then 2-run: P1 exits bar0, P2 exits bar4; P3 reaches H2 first and never persistence-exits.
    x=pd.DataFrame([
        {'open':91.5,'high':92.2,'low':91.0,'close':92.0},
        {'open':92.0,'high':92.4,'low':91.1,'close':91.4},
        {'open':91.4,'high':92.1,'low':91.0,'close':91.8},
        {'open':91.8,'high':92.5,'low':91.2,'close':92.0},
        {'open':92.0,'high':92.6,'low':91.3,'close':92.1},
        {'open':92.1,'high':92.3,'low':89.8,'close':92.0},
        {'open':92.0,'high':92.1,'low':87.8,'close':88.1},
        {'open':88.1,'high':88.3,'low':87.9,'close':88.0},
    ],index=idx)
    p1=simulate(x,pd.Series(base),'P1',1); assert p1['persistence_exit'] and p1['persistence_bar_start']==idx[0]
    p2=simulate(x,pd.Series(base),'P2',2); assert p2['persistence_exit'] and p2['persistence_bar_start']==idx[3]
    p3=simulate(x,pd.Series(base),'P3',3); assert not p3['persistence_exit'] and p3['exit_reason']=='TP_E20_DOWN'
    # H2 bar close above F15 may not trigger P1.
    b2=dict(base); b2['h2_bar_start']=idx[1]
    x2=x.copy(); x2.loc[idx[0],'close']=91.4; x2.loc[idx[1],['low','close']]=[89.9,92.0]; x2.loc[idx[2],['low','close']]=[87.9,88.2]
    z=simulate(x2,pd.Series(b2),'P1',1); assert not z['persistence_exit'] and z['exit_reason']=='TP_E20_DOWN'


def summarize(tr: pd.DataFrame, baseline_totals: dict) -> pd.DataFrame:
    rows=[]
    for rule in RULES:
        for part in list(PARTS)+['POOLED_MAJOR']:
            g=tr[(tr.rule==rule) & (tr.partition.isin(MAJOR) if part=='POOLED_MAJOR' else (tr.partition==part))].copy()
            p=g[g.persistence_exit.astype(bool)]
            vals=g.net_pnl_usd.astype(float)
            btot=baseline_totals[part]
            rows.append({
                'rule':rule,'partition':part,'n':len(g),
                'persistence_exits':len(p),'persistence_exit_rate':float(len(p)/len(g)) if len(g) else np.nan,
                'persistence_h2_failure_rate':float(p.frozen_h2_failure.mean()) if len(p) else np.nan,
                'persistence_baseline_loser_rate':float(p.baseline_loser.mean()) if len(p) else np.nan,
                'h2_before_exit_rate':float(g.h2_before_exit.mean()) if len(g) else np.nan,
                'tp_rate':float((g.exit_reason=='TP_E20_DOWN').mean()) if len(g) else np.nan,
                'wr':float((vals>0).mean()) if len(g) else np.nan,
                'pf':pf(vals),'expectancy':float(vals.mean()) if len(g) else np.nan,
                'total_pnl':float(vals.sum()) if len(g) else np.nan,
                'median_persistence_pnl':float(p.net_pnl_usd.median()) if len(p) else np.nan,
                'baseline_total':btot,'delta_vs_baseline':float(vals.sum()-btot) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)


def main() -> None:
    synthetic_tests()
    base=load_baseline()
    baseline_totals=verify_baseline(base)
    x5,coverage=b27ad.b21.load5(); assert abs(float(coverage)-1.0)<1e-12

    rows=[]
    for _,r in base.iterrows():
        for rule,need in RULES.items():
            rows.append(simulate(x5,r,rule,need))
    tr=pd.DataFrame(rows)
    assert len(tr)==len(base)*len(RULES)
    sm=summarize(tr,baseline_totals)

    supported=[]; promoted=[]
    for rule in RULES:
        pooled=sm[(sm.rule==rule)&(sm.partition=='POOLED_MAJOR')].iloc[0]
        mech=float(pooled.total_pnl)>baseline_totals['POOLED_MAJOR']
        strict=True
        for part in MAJOR:
            r=sm[(sm.rule==rule)&(sm.partition==part)].iloc[0]
            mech = mech and float(r.expectancy)>=0 and float(r.pf)>=1.0
            strict = strict and int(r.n)>=30 and float(r.wr)>=0.70 and float(r.pf)>=1.20 and float(r.expectancy)>0
        if mech: supported.append(rule)
        if strict: promoted.append(rule)

    status=('B27AS_MECHANISM_SUPPORTED_'+('_'.join(supported) if supported else 'NONE')+
            '__PROMOTION_PASS_'+('_'.join(promoted) if promoted else 'NONE'))
    tr.to_csv(OUT_TRADES,index=False); sm.to_csv(OUT_SUM,index=False); OUT_STATUS.write_text(status+'\n')

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'
    md=['# B27AS — BTC London->NY SHORT F15 Wrong-Side Persistence Exit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AK/B27AN F15 cohort and frozen E20/D50 baseline reproduced before persistence results were interpreted.','',
        f'Frozen pooled-major B27AN E20/D50 baseline: **${baseline_totals["POOLED_MAJOR"]:+.3f}**.','',
        '| Rule | Partition | N | Persist exits | Exit rate | Persist H2-fail | Persist baseline-loser | H2 before exit | TP rate | WR | PF | Exp/trade $ | Total $ | Delta vs base $ | Med persist PnL $ |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for rule in RULES:
        for part in list(PARTS)+['POOLED_MAJOR']:
            r=sm[(sm.rule==rule)&(sm.partition==part)].iloc[0]
            md.append(f'| {rule} | {part} | {int(r.n)} | {int(r.persistence_exits)} | {pct(r.persistence_exit_rate)} | {pct(r.persistence_h2_failure_rate)} | {pct(r.persistence_baseline_loser_rate)} | {pct(r.h2_before_exit_rate)} | {pct(r.tp_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {num(r.delta_vs_baseline)} | {num(r.median_persistence_pnl)} |')
    md += ['','## Frozen readout','',
           '**Mechanism-supported rules: '+(', '.join(supported) if supported else 'NONE')+'.**',
           '**Promotion-pass rules: '+(', '.join(promoted) if promoted else 'NONE')+'.**','',
           'No P4/P5, price buffer, regime filter, alternate entry, alternate stop, alternate TP, candle threshold, or runner was introduced.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__':
    main()
