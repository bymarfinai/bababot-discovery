#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIG_FILE = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Episodes.csv'
OUT_MD = ROOT / 'BTC_24H_FAILED_RECLAIM_WIDE_RISK_B27BW_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_FAILED_RECLAIM_WIDE_RISK_B27BW_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_FAILED_RECLAIM_WIDE_RISK_B27BW_Summary.csv'
OUT_SELECT = ROOT / 'BTC_24H_FAILED_RECLAIM_WIDE_RISK_B27BW_Selection.csv'
OUT_STATUS = ROOT / 'BTC_24H_FAILED_RECLAIM_WIDE_RISK_B27BW_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
H24 = pd.Timedelta(hours=24)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
STOPS = {'S2': 2.0, 'S3': 3.0}
TARGETS = {'T1_0': 1.0, 'T1_5': 1.5, 'T2_0': 2.0}
NOTIONAL = 500.0
FEE = 0.40


def as_bool(s):
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_signals():
    d = pd.read_csv(SIG_FILE)
    for c in ('age2_source_start','age2_source_end','confirmation_bar_start',
              'confirmation_complete_ts','eligible_open_ts','exit_effective_ts'):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    d['transition'] = as_bool(d['transition'])
    q = d[
        d.partition.isin(MAJOR) &
        (d.origin_state == 'BEAR') &
        (d.path_class == 'FAILED_RECLAIM')
    ].copy().sort_values(['partition','eligible_open_ts','episode_id']).reset_index(drop=True)
    expected = {'external':6,'development':20,'reference_validation':8}
    for p,n in expected.items():
        assert len(q[q.partition == p]) == n
    assert len(q) == 34
    assert len(q[q.partition.isin(OOS)]) == 14
    assert q.eligible_open_ts.notna().all()
    assert (q.eligible_open_ts == q.confirmation_complete_ts).all()
    assert (q.eligible_open_ts < q.exit_effective_ts).all()
    return q


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def open_at_or_after(x5, ts):
    i = int(x5.index.searchsorted(ts, side='left'))
    assert i < len(x5)
    return x5.index[i], float(x5.iloc[i].open)


def trade_one(x5, r, stop_name, stop_mult, target_name, target_mult):
    start = pd.Timestamp(r.age2_source_start)
    end = pd.Timestamp(r.age2_source_end)
    q = fast_slice(x5, start, end)
    assert len(q) == 48
    assert q.index[0] == start and q.index[-1] == end - BAR5
    assert (q.index.to_series().diff().dropna() == BAR5).all()

    reclaim_i = int(float(r.first_reclaim_pos)) - 1
    rebreak_i = int(float(r.first_rebreak_pos)) - 1
    assert 0 <= reclaim_i < rebreak_i < 48
    local_low = float(q.iloc[reclaim_i:rebreak_i+1].low.min())

    entry_ts = pd.Timestamp(r.eligible_open_ts)
    i = int(x5.index.searchsorted(entry_ts, side='left'))
    assert i < len(x5) and x5.index[i] == entry_ts
    entry_px = float(x5.iloc[i].open)
    local_r = entry_px - local_low
    assert local_r > 0

    wide_r = float(stop_mult) * local_r
    stop_px = entry_px - wide_r
    target_px = entry_px + float(target_mult) * wide_r
    assert stop_px < entry_px < target_px

    regime_exit = pd.Timestamp(r.exit_effective_ts)
    cap = entry_ts + H24
    deadline = min(regime_exit, cap)
    deadline_reason = 'REGIME_EXIT' if regime_exit <= cap else 'TIME_EXIT_24H'
    assert deadline > entry_ts

    eq = fast_slice(x5, entry_ts, deadline)
    assert not eq.empty and eq.index[0] == entry_ts

    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None
    for ts, bar in eq.iterrows():
        sl = float(bar.low) <= stop_px
        tp = float(bar.high) >= target_px
        if sl:
            exit_ts = ts; exit_px = stop_px; reason = f'SL_{stop_name}'
            break
        if tp:
            exit_ts = ts; exit_px = target_px; reason = f'TP_{target_name}'
            break

    if reason is None:
        exit_ts, exit_px = open_at_or_after(x5, deadline)
        reason = deadline_reason

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    return {
        'episode_id': int(r.episode_id), 'partition': str(r.partition),
        'outcome': str(r.outcome), 'transition': bool(r.transition),
        'variant': f'{stop_name}_{target_name}',
        'stop_name': stop_name, 'stop_mult_local_r': float(stop_mult),
        'target_name': target_name, 'target_mult_wide_r': float(target_mult),
        'confirmation_complete_ts': pd.Timestamp(r.confirmation_complete_ts),
        'entry_ts': entry_ts, 'entry_px': entry_px,
        'local_low': local_low, 'local_r': local_r,
        'local_r_pct_entry': local_r / entry_px,
        'wide_r': wide_r, 'wide_r_pct_entry': wide_r / entry_px,
        'stop_px': stop_px, 'target_px': target_px,
        'deadline_ts': deadline, 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'exit_reason': reason,
        'hold_minutes': float((pd.Timestamp(exit_ts)-entry_ts)/pd.Timedelta(minutes=1)),
        'gross_return': gross, 'net_pnl_usd': net,
    }


def subset(d, part):
    if part == 'POOLED_OOS': return d[d.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR': return d[d.partition.isin(MAJOR)].copy()
    return d[d.partition == part].copy()


def metrics(g):
    n = len(g)
    wins = int((g.net_pnl_usd > 0).sum()) if n else 0
    return {
        'n': n,
        'wins': wins,
        'losses': n-wins,
        'wr': wins/n if n else np.nan,
        'pf': pf(g.net_pnl_usd) if n else np.nan,
        'expectancy_usd': float(g.net_pnl_usd.mean()) if n else np.nan,
        'total_net_pnl_usd': float(g.net_pnl_usd.sum()) if n else np.nan,
        'tp_n': int(g.exit_reason.astype(str).str.startswith('TP_').sum()) if n else 0,
        'sl_n': int(g.exit_reason.astype(str).str.startswith('SL_').sum()) if n else 0,
        'regime_exit_n': int((g.exit_reason == 'REGIME_EXIT').sum()) if n else 0,
        'time24_n': int((g.exit_reason == 'TIME_EXIT_24H').sum()) if n else 0,
        'median_wide_r_pct': float(g.wide_r_pct_entry.median()) if n else np.nan,
        'median_hold_minutes': float(g.hold_minutes.median()) if n else np.nan,
    }


def summarize(d):
    rows=[]
    for variant in sorted(d.variant.unique()):
        z=d[d.variant==variant]
        for part in (*MAJOR,'POOLED_OOS','POOLED_MAJOR'):
            q=subset(z,part)
            for outcome in ('ALL','TRANSITION','RESUME'):
                g=q if outcome=='ALL' else q[q.outcome==outcome]
                rows.append({'variant':variant,'partition':part,'outcome':outcome,**metrics(g)})
    return pd.DataFrame(rows)


def getrow(s,variant,part,outcome='ALL'):
    q=s[(s.variant==variant)&(s.partition==part)&(s.outcome==outcome)]
    assert len(q)==1
    return q.iloc[0]


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def pff(v):
    if pd.isna(v): return '-'
    if np.isinf(v): return 'inf'
    return f'{float(v):.2f}'


def main():
    sig=load_signals()
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0)<1e-12

    rows=[]
    for r in sig.itertuples(index=False):
        for sn,sm in STOPS.items():
            for tn,tm in TARGETS.items():
                rows.append(trade_one(x5,r,sn,sm,tn,tm))
    d=pd.DataFrame(rows)
    assert len(d)==34*6
    assert (d.stop_px < d.entry_px).all() and (d.entry_px < d.target_px).all()
    d.to_csv(OUT_TRADES,index=False)
    s=summarize(d)
    s.to_csv(OUT_SUM,index=False)

    selections=[]; passers=[]
    for variant in sorted(d.variant.unique()):
        major=[getrow(s,variant,p) for p in MAJOR]
        gate_n=all(int(r.n)>=5 for r in major)
        gate_exp=all(pd.notna(r.expectancy_usd) and float(r.expectancy_usd)>0 for r in major)
        gate_pf=all(pd.notna(r.pf) and float(r.pf)>=1.20 for r in major)
        gate_wr=all(pd.notna(r.wr) and float(r.wr)>=.50 for r in major)
        robust=bool(gate_n and gate_exp and gate_pf and gate_wr)
        high70=bool(robust and all(float(r.wr)>=.70 for r in major))
        minpf=min(float(r.pf) for r in major) if all(pd.notna(r.pf) for r in major) else np.nan
        pooled=getrow(s,variant,'POOLED_MAJOR')
        sm=float(d[d.variant==variant].stop_mult_local_r.iloc[0])
        rec={'variant':variant,'stop_mult_local_r':sm,
             'gate_n':gate_n,'gate_positive_expectancy':gate_exp,
             'gate_pf_1p20':gate_pf,'gate_wr_50':gate_wr,
             'robust_pass':robust,'high_quality_70':high70,
             'minimum_partition_pf':minpf,
             'pooled_major_expectancy_usd':float(pooled.expectancy_usd),
             'pooled_major_total_net_pnl_usd':float(pooled.total_net_pnl_usd)}
        selections.append(rec)
        if robust: passers.append(rec)

    selected=None
    if passers:
        selected=sorted(passers,key=lambda z:(z['minimum_partition_pf'],z['pooled_major_expectancy_usd'],-z['stop_mult_local_r']),reverse=True)[0]['variant']
        verdict=f'B27BW_FAILED_RECLAIM_WIDE_RISK_SUPPORTED_{selected}'
    else:
        verdict='B27BW_FAILED_RECLAIM_WIDE_RISK_NOT_SUPPORTED'
    sel=pd.DataFrame(selections)
    sel['selected']=sel.variant.eq(selected) if selected else False
    sel.to_csv(OUT_SELECT,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BW — BTC 24H BEAR-Origin Failed-Reclaim Widened-Risk Economics — Result','',
        '**Audit status: PASS.** Same B27BT causal signal and next-5m-open entry; only the two preregistered B27BV-derived widened risk envelopes are tested.','',
        'Signal identity reproduced exactly: **34 = external 6 + development 20 + reference_validation 8; pooled OOS 14.**','',
        'Economics: **$500 notional, $0.40 round-trip fee**. Stops: S2/S3 local-R; targets: 1R/1.5R/2R of actual widened risk.','',
        '## Major-partition economics','',
        '| Variant | Partition | N | WR | PF | Exp/trade | Total net | TP | SL | Regime exit | 24h exit | Median risk |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for variant in sorted(d.variant.unique()):
        for part in MAJOR:
            r=getrow(s,variant,part)
            lines.append(f'| {variant} | {part} | {int(r.n)} | {pct(r.wr)} | {pff(r.pf)} | ${float(r.expectancy_usd):+.2f} | ${float(r.total_net_pnl_usd):+.2f} | {int(r.tp_n)} | {int(r.sl_n)} | {int(r.regime_exit_n)} | {int(r.time24_n)} | {pct(r.median_wide_r_pct)} |')

    lines += ['', '## Pooled readout','',
              '| Variant | Pool | N | WR | PF | Exp/trade | Total net | Median risk | Median hold |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for variant in sorted(d.variant.unique()):
        for part in ('POOLED_OOS','POOLED_MAJOR'):
            r=getrow(s,variant,part)
            lines.append(f'| {variant} | {part} | {int(r.n)} | {pct(r.wr)} | {pff(r.pf)} | ${float(r.expectancy_usd):+.2f} | ${float(r.total_net_pnl_usd):+.2f} | {pct(r.median_wide_r_pct)} | {float(r.median_hold_minutes):.0f}m |')

    lines += ['', '## Outcome diagnostic — pooled major','',
              '| Variant | Outcome | N | WR | PF | Exp/trade | Total net |',
              '|---|---|---:|---:|---:|---:|---:|']
    for variant in sorted(d.variant.unique()):
        for outcome in ('TRANSITION','RESUME'):
            r=getrow(s,variant,'POOLED_MAJOR',outcome)
            lines.append(f'| {variant} | {outcome} | {int(r.n)} | {pct(r.wr)} | {pff(r.pf)} | ${float(r.expectancy_usd):+.2f} | ${float(r.total_net_pnl_usd):+.2f} |')

    lines += ['', '## Frozen selection gate','',
              '| Variant | N>=5 each | Exp>0 each | PF>=1.20 each | WR>=50% each | ROBUST_PASS | HIGH_QUALITY_70 | Min PF | Selected |',
              '|---|---|---|---|---|---|---|---:|---|']
    for rec in selections:
        lines.append(f"| {rec['variant']} | {'PASS' if rec['gate_n'] else 'FAIL'} | {'PASS' if rec['gate_positive_expectancy'] else 'FAIL'} | {'PASS' if rec['gate_pf_1p20'] else 'FAIL'} | {'PASS' if rec['gate_wr_50'] else 'FAIL'} | {'YES' if rec['robust_pass'] else 'NO'} | {'YES' if rec['high_quality_70'] else 'NO'} | {pff(rec['minimum_partition_pf'])} | {'YES' if rec['variant']==selected else 'NO'} |")

    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              'A pass is still historical discovery evidence and would require a separate frequency/portfolio/live-readiness step before any BBC production change.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
