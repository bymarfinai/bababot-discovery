#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eth_f85_f15_transfer_m1_k1_opp0 as data_base
import bnb_f85_long_transfer_m7_retest_sequence_diagnostics_b27ej as m7

PFX = 'BNB_F85_LONG_TRANSFER_M8_ENTRY2_ECONOMICS_B27EK'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STRESS = ROOT / f'{PFX}_Slippage.csv'
OUT_COHORT = ROOT / f'{PFX}_Cohort.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
MAJOR = ('external', 'development', 'reference_validation')
SOURCES = ('ALT_0330', 'RAW_0530')
NOTIONAL = 500.0
FEE = 0.40
BAR5 = pd.Timedelta(minutes=5)


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    return x.iloc[int(x.index.searchsorted(a, side='left')):int(x.index.searchsorted(z, side='left'))]


def bar_at(x: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    p = int(x.index.searchsorted(ts, side='left'))
    if p >= len(x) or x.index[p] != ts:
        raise AssertionError(f'missing exact raw5m bar {ts}')
    return x.iloc[p]


def open_at(x: pd.DataFrame, ts: pd.Timestamp) -> float:
    return float(bar_at(x, ts).open)


def as_bool(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in ('true', '1', 'yes')


def pnl_long(entry: float, exit_px: float, bps: float = 0.0) -> float:
    f = float(bps) / 10000.0
    e = float(entry) * (1.0 + f)
    x = float(exit_px) * (1.0 - f)
    return float(NOTIONAL * (x / e - 1.0) - FEE)


def simulate_h2_only(entry_ts: pd.Timestamp, entry_px: float, end: pd.Timestamp,
                     H: float, F35: float, x5: pd.DataFrame) -> dict:
    q = fs(x5, entry_ts, end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError(f'missing execution slice at {entry_ts}')
    for ts, bar in q.iterrows():
        # Frozen B27EH ordering: H2 target has priority over same-bar close invalidation.
        if float(bar.high) >= H:
            return {'exit_ts': pd.Timestamp(ts), 'exit_px': float(H), 'exit_reason': 'H2', 'h2_reached': True}
        if float(bar.close) < F35:
            xts = pd.Timestamp(ts) + BAR5
            if xts > end:
                xts = end
            return {'exit_ts': xts, 'exit_px': open_at(x5, xts), 'exit_reason': 'PRE_H2_F35_INVALIDATION', 'h2_reached': False}
    return {'exit_ts': end, 'exit_px': open_at(x5, end), 'exit_reason': 'PRE_H2_TIME_EXIT', 'h2_reached': False}


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_ls(d: pd.DataFrame, col: str, time_col: str) -> int:
    q = d.sort_values(time_col)
    best = cur = 0
    for v in pd.to_numeric(q[col], errors='coerce'):
        if pd.notna(v) and float(v) <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(d: pd.DataFrame, col: str, time_col: str) -> dict:
    v = pd.to_numeric(d[col], errors='coerce').dropna()
    if len(v) == 0:
        return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0,'max_loss_streak':0}
    return {
        'n': int(len(v)), 'wins': int((v > 0).sum()), 'wr': float((v > 0).mean()),
        'pf': pf(v), 'expectancy': float(v.mean()), 'net': float(v.sum()),
        'max_loss_streak': max_ls(d, col, time_col),
    }


def q50(x):
    s = pd.to_numeric(pd.Series(x), errors='coerce').dropna()
    return float(s.median()) if len(s) else np.nan


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x, n=3): return '-' if pd.isna(x) else f'{float(x):.{n}f}'
def usd(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'
def fmt_pf(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def main():
    if (ROOT / 'BNB_F85_LONG_TRANSFER_M7_RETEST_SEQUENCE_DIAGNOSTICS_B27EJ_Status.txt').read_text().strip() != 'B27EJ_BNB_RETEST_SEQUENCE_DIAGNOSTICS_COMPLETE':
        raise AssertionError('B27EJ prerequisite drift')

    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB raw coverage below gate: {coverage:.6f}')

    saved = pd.read_csv(ROOT / 'BNB_F85_LONG_TRANSFER_M7_RETEST_SEQUENCE_DIAGNOSTICS_B27EJ_Detail.csv')
    for c in ('entry_ts','execution_end','confirmation_bar_start','structural_h2_ts','entry2_ts','second_reclaim_ts','first_close_below_f85_ts'):
        saved[c] = pd.to_datetime(saved[c], utc=True, errors='coerce')
    q = saved[
        saved.accepted.map(as_bool) & saved.partition.isin(MAJOR) & saved.side.eq('LONG') & saved.source.isin(SOURCES)
    ].copy().sort_values('entry_ts').reset_index(drop=True)
    if len(q) != 106 or q.source.value_counts().to_dict() != {'ALT_0330':55,'RAW_0530':51}:
        raise AssertionError('frozen 106 parent LONG identity drift')
    if q.candidate_id.duplicated().any():
        raise AssertionError('duplicate parent candidate IDs')

    # Reproduce B27EJ ENTRY2 sequence one-to-one from raw5m.
    regen_rows = []
    for _, r in q.iterrows():
        if abs(open_at(x5, pd.Timestamp(r.entry_ts)) - float(r.entry_px)) > max(1e-10, abs(float(r.entry_px))*1e-10):
            raise AssertionError(f'ENTRY1 raw open drift {r.candidate_id}')
        rr = m7.pre_sequence(r, x5)
        saved_exists = as_bool(r.entry2_exists)
        if bool(rr['entry2_exists']) != saved_exists:
            raise AssertionError(f'ENTRY2 existence reproduction failed {r.candidate_id}')
        if saved_exists:
            st = pd.Timestamp(r.entry2_ts); rt = pd.Timestamp(rr['entry2_ts'])
            if st != rt:
                raise AssertionError(f'ENTRY2 timestamp reproduction failed {r.candidate_id}: {st} != {rt}')
            if abs(float(r.entry2_px) - float(rr['entry2_px'])) > max(1e-10, abs(float(r.entry2_px))*1e-10):
                raise AssertionError(f'ENTRY2 price reproduction failed {r.candidate_id}')
            if abs(open_at(x5, st) - float(r.entry2_px)) > max(1e-10, abs(float(r.entry2_px))*1e-10):
                raise AssertionError(f'ENTRY2 raw open drift {r.candidate_id}')
        regen_rows.append(rr)
    regen = pd.DataFrame(regen_rows)
    if int(regen.entry2_exists.astype(bool).sum()) != 45:
        raise AssertionError(f'B27EJ descriptive ENTRY2 count drift: {int(regen.entry2_exists.astype(bool).sum())} != 45')

    # Executable ENTRY2 geometry is preregistered: F35 < entry2 < H and before H2/end.
    rows = []
    for _, r in q.iterrows():
        if not as_bool(r.entry2_exists) or pd.isna(r.entry2_ts) or pd.isna(r.entry2_px):
            continue
        e2ts = pd.Timestamp(r.entry2_ts); e2px = float(r.entry2_px)
        end = pd.Timestamp(r.execution_end); H = float(r.H); L = float(r.L); R = float(r.R); F35 = float(r.stop_level)
        h2ts = pd.Timestamp(r.structural_h2_ts) if pd.notna(r.structural_h2_ts) else pd.NaT
        executable = bool(F35 < e2px < H and e2ts < end and (pd.isna(h2ts) or e2ts < h2ts))
        if not executable:
            continue

        # ENTRY1 same-signal baseline and ENTRY2 use identical H2-only economics.
        s1 = simulate_h2_only(pd.Timestamp(r.entry_ts), float(r.entry_px), end, H, F35, x5)
        s2 = simulate_h2_only(e2ts, e2px, end, H, F35, x5)
        typ = 'ACCEPT_BELOW_RERECLAIM' if pd.notna(r.first_close_below_f85_ts) else 'FIRST_HOLD'
        row = {
            'candidate_id':r.candidate_id,'partition':r.partition,'source':r.source,'entry2_type':typ,
            'entry1_ts':pd.Timestamp(r.entry_ts),'entry1_px':float(r.entry_px),
            'entry2_ts':e2ts,'entry2_px':e2px,'execution_end':end,
            'H':H,'L':L,'R':R,'F35':F35,
            'entry1_depth_R':(float(r.entry_px)-L)/R,'entry2_depth_R':(e2px-L)/R,
            'entry1_reward_H_R':(H-float(r.entry_px))/R,'entry2_reward_H_R':(H-e2px)/R,
            'entry1_risk_F35_R':(float(r.entry_px)-F35)/R,'entry2_risk_F35_R':(e2px-F35)/R,
            'entry1_exit_ts':s1['exit_ts'],'entry1_exit_px':s1['exit_px'],'entry1_exit_reason':s1['exit_reason'],'entry1_h2':s1['h2_reached'],
            'entry2_exit_ts':s2['exit_ts'],'entry2_exit_px':s2['exit_px'],'entry2_exit_reason':s2['exit_reason'],'entry2_h2':s2['h2_reached'],
        }
        for bps in (0,2,5,10):
            row[f'entry1_pnl_{bps}bps'] = pnl_long(float(r.entry_px), float(s1['exit_px']), bps)
            row[f'entry2_pnl_{bps}bps'] = pnl_long(e2px, float(s2['exit_px']), bps)
        row['entry1_pnl'] = row['entry1_pnl_0bps']; row['entry2_pnl'] = row['entry2_pnl_0bps']
        rows.append(row)
    d = pd.DataFrame(rows).sort_values('entry2_ts').reset_index(drop=True)
    if len(d) < 1:
        raise AssertionError('no executable ENTRY2 trades')

    # Mandatory B27EH H2_ONLY baseline reproduction on the exact same IDs.
    eh = pd.read_csv(ROOT / 'BNB_F85_LONG_TRANSFER_M5_TWO_STAGE_ECONOMICS_B27EH_Detail.csv')
    eh = eh[eh.mechanism.eq('H2_ONLY')].copy()
    ref = eh[eh.candidate_id.isin(d.candidate_id)].set_index('candidate_id')
    if set(ref.index) != set(d.candidate_id):
        raise AssertionError('B27EH same-signal baseline join failed')
    for r in d.itertuples(index=False):
        z = ref.loc[r.candidate_id]
        if abs(float(r.entry1_pnl) - float(z.pnl)) > 1e-9:
            raise AssertionError(f'B27EH ENTRY1 H2-only PnL reproduction failed {r.candidate_id}')
        if str(r.entry1_exit_reason) != str(z.exit_reason):
            raise AssertionError(f'B27EH ENTRY1 exit reason reproduction failed {r.candidate_id}')

    d.to_csv(OUT_DETAIL, index=False)

    summary_rows = []
    for strat in ('ENTRY1_SAME_SIGNAL','ENTRY2'):
        pcol = 'entry1_pnl' if strat.startswith('ENTRY1') else 'entry2_pnl'
        tcol = 'entry1_ts' if strat.startswith('ENTRY1') else 'entry2_ts'
        for scope in ('POOLED_MAJOR', *SOURCES, *MAJOR):
            z = d if scope == 'POOLED_MAJOR' else (d[d.source.eq(scope)] if scope in SOURCES else d[d.partition.eq(scope)])
            m = metrics(z, pcol, tcol)
            prefix = 'entry1' if strat.startswith('ENTRY1') else 'entry2'
            summary_rows.append({
                'strategy':strat,'scope':scope,**m,
                'h2_rate':float(z[f'{prefix}_h2'].astype(bool).mean()) if len(z) else np.nan,
                'median_entry_depth_R':q50(z[f'{prefix}_depth_R']),
                'median_reward_H_R':q50(z[f'{prefix}_reward_H_R']),
                'median_risk_F35_R':q50(z[f'{prefix}_risk_F35_R']),
            })
    summary = pd.DataFrame(summary_rows); summary.to_csv(OUT_SUM,index=False)

    stress_rows=[]
    for strat in ('ENTRY1_SAME_SIGNAL','ENTRY2'):
        tcol='entry1_ts' if strat.startswith('ENTRY1') else 'entry2_ts'
        for bps in (0,2,5,10):
            col=('entry1' if strat.startswith('ENTRY1') else 'entry2') + f'_pnl_{bps}bps'
            stress_rows.append({'strategy':strat,'bps':bps,**metrics(d,col,tcol)})
    stress=pd.DataFrame(stress_rows); stress.to_csv(OUT_STRESS,index=False)

    cohort_rows=[]
    for typ in ('FIRST_HOLD','ACCEPT_BELOW_RERECLAIM'):
        z=d[d.entry2_type.eq(typ)]
        for strat in ('ENTRY1_SAME_SIGNAL','ENTRY2'):
            p='entry1_pnl' if strat.startswith('ENTRY1') else 'entry2_pnl'
            t='entry1_ts' if strat.startswith('ENTRY1') else 'entry2_ts'
            cohort_rows.append({'entry2_type':typ,'strategy':strat,**metrics(z,p,t)})
    cohort=pd.DataFrame(cohort_rows); cohort.to_csv(OUT_COHORT,index=False)

    e1=summary[(summary.strategy=='ENTRY1_SAME_SIGNAL')&(summary.scope=='POOLED_MAJOR')].iloc[0]
    e2=summary[(summary.strategy=='ENTRY2')&(summary.scope=='POOLED_MAJOR')].iloc[0]
    e2_5=stress[(stress.strategy=='ENTRY2')&(stress.bps==5)].iloc[0]

    src_ok=True
    for s in SOURCES:
        z=summary[(summary.strategy=='ENTRY2')&(summary.scope==s)].iloc[0]
        if not (int(z.n)>=10 and float(z.net)>0): src_ok=False
    part_ok=True
    for p in MAJOR:
        z=summary[(summary.strategy=='ENTRY2')&(summary.scope==p)].iloc[0]
        if not (int(z.n)>=5 and float(z.net)>0): part_ok=False
    improvement = bool((float(e2.pf)-float(e1.pf) >= .25) or (float(e2.net)-float(e1.net) >= 15.0))
    supported=bool(
        int(e2.n)>=30 and float(e2.wr)>=.70 and float(e2.pf)>=1.50 and float(e2.net)>0 and int(e2.max_loss_streak)<=4 and
        improvement and src_ok and part_ok and float(e2_5.pf)>=1.20 and float(e2_5.net)>0
    )
    status='B27EK_ENTRY2_SUPPORTED' if supported else 'B27EK_BNB_ENTRY2_ECONOMICS_NOT_SUPPORTED'

    def scope_row(strat, scope):
        return summary[(summary.strategy==strat)&(summary.scope==scope)].iloc[0]

    lines=[
        '# BNB F85 LONG Transfer — M8 ENTRY2 Economics — B27EK Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. Frozen parent LONG identity: **PASS (106)**. B27EJ descriptive ENTRY2 reproduction: **PASS (45)**.','',
        f'Executable ENTRY2 trades under preregistered geometry: **{len(d)}**. ENTRY1 comparison uses these exact same candidate IDs.','',
        '## Same-signal economics','',
        '| Strategy | N | WR | PF | Exp | Net | Max LS | H2 rate | Entry depth | Reward→H | Risk→F35 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for strat in ('ENTRY1_SAME_SIGNAL','ENTRY2'):
        r=scope_row(strat,'POOLED_MAJOR')
        lines.append(f'| {strat} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {int(r.max_loss_streak)} | {pct(r.h2_rate)} | {num(r.median_entry_depth_R)}R | {num(r.median_reward_H_R)}R | {num(r.median_risk_F35_R)}R |')
    lines += ['',
        f'- ENTRY2 minus same-signal ENTRY1: WR **{100*(float(e2.wr)-float(e1.wr)):+.1f}pp**, PF **{float(e2.pf)-float(e1.pf):+.2f}**, expectancy **{usd(float(e2.expectancy)-float(e1.expectancy))}**, net **{usd(float(e2.net)-float(e1.net))}**.','',
        '## Source / partition stability','',
        '| Scope | N | WR | PF | Net | Max LS |', '|---|---:|---:|---:|---:|---:|'
    ]
    for scope in (*SOURCES,*MAJOR):
        r=scope_row('ENTRY2',scope)
        lines.append(f'| {scope} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.net)} | {int(r.max_loss_streak)} |')
    lines += ['', '## Slippage — ENTRY2','', '| bps/fill | N | WR | PF | Net | Max LS |','|---:|---:|---:|---:|---:|---:|']
    for bps in (0,2,5,10):
        r=stress[(stress.strategy=='ENTRY2')&(stress.bps==bps)].iloc[0]
        lines.append(f'| {bps} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.net)} | {int(r.max_loss_streak)} |')
    lines += ['', '## ENTRY2 sequence cohorts (descriptive only)','', '| Cohort | N | ENTRY1 WR | ENTRY1 PF | ENTRY1 net | ENTRY2 WR | ENTRY2 PF | ENTRY2 net |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for typ in ('FIRST_HOLD','ACCEPT_BELOW_RERECLAIM'):
        a=cohort[(cohort.entry2_type==typ)&(cohort.strategy=='ENTRY1_SAME_SIGNAL')].iloc[0]
        b=cohort[(cohort.entry2_type==typ)&(cohort.strategy=='ENTRY2')].iloc[0]
        lines.append(f'| {typ} | {int(b.n)} | {pct(a.wr)} | {fmt_pf(a.pf)} | {usd(a.net)} | {pct(b.wr)} | {fmt_pf(b.pf)} | {usd(b.net)} |')
    lines += ['', f'**Support gate: {"PASS" if supported else "FAIL"}**','', f'**Status: {status}**','',
              'B27EK stops here. No source/cohort filter selection, re-arbitration, portfolio integration, forward shadow, or live integration is run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
