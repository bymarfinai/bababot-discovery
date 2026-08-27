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

PFX = 'BNB_F85_LONG_TRANSFER_M5_TWO_STAGE_ECONOMICS_B27EH'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STRESS = ROOT / f'{PFX}_Slippage.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
MAJOR = ('external', 'development', 'reference_validation')
LONG_SOURCES = ('ALT_0330', 'RAW_0530')
MECHS = ('H2_ONLY', 'H2_50_E10_CONFIRM_E20')
NOTIONAL = 500.0
FEE = 0.40
BAR5 = pd.Timedelta(minutes=5)


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    return x.iloc[int(x.index.searchsorted(a, side='left')):int(x.index.searchsorted(z, side='left'))]


def open_at(x5: pd.DataFrame, ts: pd.Timestamp) -> float:
    pos = int(x5.index.searchsorted(ts, side='left'))
    if pos >= len(x5) or x5.index[pos] != ts:
        raise AssertionError(f'missing exact open at {ts}')
    return float(x5.iloc[pos].open)


def pnl_long(entry: float, exits: list[tuple[float, float]], bps: float = 0.0) -> float:
    f = float(bps) / 10000.0
    e = float(entry) * (1.0 + f)
    gross = 0.0
    weight = 0.0
    for w, px in exits:
        w = float(w)
        x = float(px) * (1.0 - f)
        gross += w * NOTIONAL * (x / e - 1.0)
        weight += w
    if abs(weight - 1.0) > 1e-12:
        raise AssertionError(f'exit weights do not sum to one: {weight}')
    return float(gross - FEE)


def simulate_pre_h2(r: pd.Series, x5: pd.DataFrame):
    entry_ts = pd.Timestamp(r.entry_ts)
    end = pd.Timestamp(r.execution_end)
    H = float(r.H)
    F35 = float(r.stop_level)
    q = fs(x5, entry_ts, end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError(f'missing execution slice {r.candidate_id}')
    for ts, bar in q.iterrows():
        # Frozen target-before-close-invalidation ordering.
        if float(bar.high) >= H:
            return 'H2', pd.Timestamp(ts), H
        if float(bar.close) < F35:
            xts = pd.Timestamp(ts) + BAR5
            return 'PRE_H2_F35_INVALIDATION', xts, open_at(x5, xts)
    return 'PRE_H2_TIME_EXIT', end, open_at(x5, end)


def sim_h2_only(r: pd.Series, x5: pd.DataFrame) -> dict:
    kind, ts, px = simulate_pre_h2(r, x5)
    return {
        'mechanism': 'H2_ONLY',
        'exit1_ts': ts, 'exit1_px': float(px), 'exit1_weight': 1.0,
        'exit2_ts': pd.NaT, 'exit2_px': np.nan, 'exit2_weight': 0.0,
        'exit_reason': kind,
        'h2_reached': kind == 'H2', 'e10_confirmed': False, 'runner_e20_hit': False,
        'runner_failure': False, 'runner_time_exit': False,
    }


def sim_two_stage(r: pd.Series, x5: pd.DataFrame) -> dict:
    kind, h2_ts, first_px = simulate_pre_h2(r, x5)
    if kind != 'H2':
        return {
            'mechanism': 'H2_50_E10_CONFIRM_E20',
            'exit1_ts': h2_ts, 'exit1_px': float(first_px), 'exit1_weight': 1.0,
            'exit2_ts': pd.NaT, 'exit2_px': np.nan, 'exit2_weight': 0.0,
            'exit_reason': kind,
            'h2_reached': False, 'e10_confirmed': False, 'runner_e20_hit': False,
            'runner_failure': False, 'runner_time_exit': False,
        }

    end = pd.Timestamp(r.execution_end)
    H = float(r.H); R = float(r.R)
    E10 = H + 0.10 * R
    E20 = H + 0.20 * R
    next_ts = pd.Timestamp(h2_ts) + BAR5
    q = fs(x5, next_ts, end)
    armed = False
    e10_ts = pd.NaT
    runner_exit_ts = end
    runner_exit_px = open_at(x5, end)
    runner_reason = 'RUNNER_TIME_EXIT_UNCONFIRMED'

    for ts, bar in q.iterrows():
        ts = pd.Timestamp(ts)
        if not armed:
            # E10 is known only when this bar closes; E20 cannot be credited here.
            if float(bar.close) >= E10:
                armed = True
                e10_ts = ts
                continue
            if float(bar.close) < H:
                runner_exit_ts = ts + BAR5
                runner_exit_px = open_at(x5, runner_exit_ts)
                runner_reason = 'RUNNER_FAIL_BEFORE_E10_CLOSE_BELOW_H'
                break
        else:
            # Armed only on bars strictly after the E10 confirmation bar.
            if ts <= e10_ts:
                continue
            if float(bar.high) >= E20:
                runner_exit_ts = ts
                runner_exit_px = E20
                runner_reason = 'RUNNER_TP_E20'
                break
            if float(bar.close) < H:
                runner_exit_ts = ts + BAR5
                runner_exit_px = open_at(x5, runner_exit_ts)
                runner_reason = 'RUNNER_FAIL_AFTER_E10_CLOSE_BELOW_H'
                break

    return {
        'mechanism': 'H2_50_E10_CONFIRM_E20',
        'exit1_ts': pd.Timestamp(h2_ts), 'exit1_px': H, 'exit1_weight': 0.5,
        'exit2_ts': runner_exit_ts, 'exit2_px': float(runner_exit_px), 'exit2_weight': 0.5,
        'exit_reason': runner_reason,
        'h2_reached': True, 'e10_confirmed': bool(armed),
        'runner_e20_hit': runner_reason == 'RUNNER_TP_E20',
        'runner_failure': runner_reason.startswith('RUNNER_FAIL_'),
        'runner_time_exit': runner_reason.startswith('RUNNER_TIME_EXIT_'),
    }


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_ls(d: pd.DataFrame, col: str) -> int:
    q = d.sort_values('entry_ts')
    best = cur = 0
    for v in pd.to_numeric(q[col], errors='coerce'):
        if pd.notna(v) and float(v) <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(d: pd.DataFrame, col: str = 'pnl') -> dict:
    v = pd.to_numeric(d[col], errors='coerce').dropna()
    if len(v) == 0:
        return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0,'max_loss_streak':0}
    return {
        'n': int(len(v)), 'wins': int((v > 0).sum()), 'wr': float((v > 0).mean()),
        'pf': pf(v), 'expectancy': float(v.mean()), 'net': float(v.sum()),
        'max_loss_streak': max_ls(d, col),
    }


def fmt_pf(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def usd(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main():
    b27ef = (ROOT / 'BNB_F85_F15_TRANSFER_M3_FROZEN_ECONOMICS_B27EF_Status.txt').read_text().strip()
    b27eg = (ROOT / 'BNB_F85_F15_TRANSFER_M4_PATH_DIAGNOSTICS_B27EG_Status.txt').read_text().strip()
    if b27ef != 'B27EF_BNB_FROZEN_ECONOMICS_NOT_SUPPORTED':
        raise AssertionError(f'B27EF prerequisite drift: {b27ef}')
    if b27eg != 'B27EG_BNB_PATH_DIAGNOSTICS_COMPLETE':
        raise AssertionError(f'B27EG prerequisite drift: {b27eg}')

    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB coverage below gate: {coverage:.6f}')

    base = pd.read_csv(ROOT / 'BNB_F85_F15_TRANSFER_M3_FROZEN_ECONOMICS_B27EF_Detail.csv')
    for c in ('entry_ts','execution_end','exit_ts'):
        base[c] = pd.to_datetime(base[c], utc=True)
    if base.candidate_id.duplicated().any():
        raise AssertionError('duplicate B27EF candidate IDs')

    long_major = base[
        base.accepted.astype(bool) & base.partition.isin(MAJOR) & base.side.eq('LONG') & base.source.isin(LONG_SOURCES)
    ].copy().sort_values('entry_ts').reset_index(drop=True)
    if len(long_major) != 106:
        raise AssertionError(f'expected 106 accepted pooled-major LONG trades, got {len(long_major)}')
    counts = long_major.source.value_counts().to_dict()
    if counts != {'ALT_0330':55, 'RAW_0530':51}:
        raise AssertionError(f'LONG source identity drift: {counts}')

    rows=[]
    for _, r in long_major.iterrows():
        for fn in (sim_h2_only, sim_two_stage):
            out = fn(r, x5)
            exits = [(out['exit1_weight'], out['exit1_px'])]
            if float(out['exit2_weight']) > 0:
                exits.append((out['exit2_weight'], out['exit2_px']))
            row = {
                'candidate_id': r.candidate_id, 'partition': r.partition, 'source': r.source,
                'entry_ts': r.entry_ts, 'entry_px': float(r.entry_px), 'execution_end': r.execution_end,
                'H': float(r.H), 'L': float(r.L), 'R': float(r.R), 'F35': float(r.stop_level),
                **out,
            }
            for bps in (0,2,5,10):
                row[f'pnl_{bps}bps'] = pnl_long(float(r.entry_px), exits, bps)
            row['pnl'] = row['pnl_0bps']
            rows.append(row)
    d = pd.DataFrame(rows)
    d.to_csv(OUT_DETAIL, index=False)

    # Baseline frozen B27EF LONG and SHORT control.
    base_long = metrics(long_major, 'pnl')
    short = base[base.accepted.astype(bool) & base.partition.isin(MAJOR) & base.source.eq('SHORT_2000')].copy()
    if len(short) != 64:
        raise AssertionError(f'SHORT control drift: {len(short)}')

    summaries=[]; stress_rows=[]
    support={}
    for mech in MECHS:
        q = d[d.mechanism.eq(mech)].copy()
        for scope, mask in [('POOLED_MAJOR', pd.Series(True,index=q.index))] + [
            (src, q.source.eq(src)) for src in LONG_SOURCES
        ] + [(p, q.partition.eq(p)) for p in MAJOR]:
            z = q[mask]
            summaries.append({'mechanism':mech,'scope':scope,**metrics(z,'pnl')})
        for bps in (0,2,5,10):
            m=metrics(q,f'pnl_{bps}bps')
            stress_rows.append({'mechanism':mech,'bps':bps,**m})

        pooled = metrics(q,'pnl')
        src_ok = all(metrics(q[q.source.eq(s)],'pnl')['net'] > 0 for s in LONG_SOURCES)
        part_ok = all(metrics(q[q.partition.eq(p)],'pnl')['net'] > 0 for p in MAJOR)
        m5 = metrics(q,'pnl_5bps')
        support[mech] = bool(
            pooled['n']==106 and pooled['wr']>=.70 and pooled['pf']>=1.50 and pooled['net']>0 and
            pooled['max_loss_streak']<=4 and src_ok and part_ok and m5['pf']>=1.20 and m5['net']>0
        )

    summary=pd.DataFrame(summaries); stress=pd.DataFrame(stress_rows)
    summary.to_csv(OUT_SUM,index=False); stress.to_csv(OUT_STRESS,index=False)

    passing=[m for m in MECHS if support[m]]
    preferred='NONE'
    if passing:
        ranked=[]
        for m in passing:
            r=stress[(stress.mechanism==m)&(stress.bps==5)].iloc[0]
            ranked.append((float(r.pf),float(r.net),m))
        preferred=sorted(ranked,reverse=True)[0][2]

    # Diagnostic frozen-acceptance combined portfolio: replace accepted LONG PnL only; SHORT remains B27EF.
    comb_rows=[]
    for mech in MECHS:
        q=d[d.mechanism.eq(mech)][['candidate_id','entry_ts','pnl']].copy()
        l=q.rename(columns={'pnl':'new_pnl'})
        c=pd.concat([
            l[['entry_ts','new_pnl']].rename(columns={'new_pnl':'pnl'}),
            short[['entry_ts','pnl']]
        ],ignore_index=True).sort_values('entry_ts')
        comb_rows.append({'mechanism':mech,**metrics(c,'pnl')})
    comb=pd.DataFrame(comb_rows)

    lines=[
        '# BNB F85 LONG Transfer — M5 Two-Stage Economics — B27EH Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. Frozen accepted LONG identity: **PASS (106 = 55 ALT_0330 + 51 RAW_0530)**. SHORT control: **64 unchanged B27EF trades**.','',
        'B27EH changes economics only and keeps the B27EF accepted set frozen; no re-arbitration is claimed here.','',
        '## Frozen B27EF LONG baseline','',
        f'- N **{base_long["n"]}**, WR **{pct(base_long["wr"])}**, PF **{fmt_pf(base_long["pf"])}**, expectancy **{usd(base_long["expectancy"])}**, net **{usd(base_long["net"])}**, max loss streak **{base_long["max_loss_streak"]}**.','',
        '## Mechanism results','',
        '| Mechanism | N | WR | PF | Exp | Net | Max LS | Gate |',
        '|---|---:|---:|---:|---:|---:|---:|---|'
    ]
    for mech in MECHS:
        r=summary[(summary.mechanism==mech)&(summary.scope=='POOLED_MAJOR')].iloc[0]
        lines.append(f'| {mech} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {int(r.max_loss_streak)} | {"PASS" if support[mech] else "FAIL"} |')

    lines += ['', '## Source and partition stability','',
              '| Mechanism | Scope | N | WR | PF | Net | Max LS |','|---|---|---:|---:|---:|---:|---:|']
    for _,r in summary[summary.scope!='POOLED_MAJOR'].iterrows():
        lines.append(f'| {r.mechanism} | {r.scope} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.net)} | {int(r.max_loss_streak)} |')

    lines += ['', '## Adverse fill sensitivity — LONG only','',
              '| Mechanism | bps/fill | N | WR | PF | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|']
    for _,r in stress.iterrows():
        lines.append(f'| {r.mechanism} | {int(r.bps)} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.net)} | {int(r.max_loss_streak)} |')

    lines += ['', '## Two-stage state counts','']
    t=d[d.mechanism=='H2_50_E10_CONFIRM_E20']
    lines += [
        f'- H2 reached: **{int(t.h2_reached.sum())}/{len(t)} ({pct(t.h2_reached.mean())})**.',
        f'- E10 completed-close continuation confirmed: **{int(t.e10_confirmed.sum())}/{int(t.h2_reached.sum())} H2 trades ({pct(t[t.h2_reached].e10_confirmed.mean())})**.',
        f'- Runner E20 hits after confirmation: **{int(t.runner_e20_hit.sum())}**.',
        f'- Runner continuation-failure exits: **{int(t.runner_failure.sum())}**.',
        f'- Runner time exits: **{int(t.runner_time_exit.sum())}**.','',
        '## Frozen-acceptance portfolio control (LONG mechanism + unchanged SHORT20)','',
        '| Mechanism | N | WR | PF | Net | Max LS |','|---|---:|---:|---:|---:|---:|']
    for _,r in comb.iterrows():
        lines.append(f'| {r.mechanism} | {int(r.n)} | {pct(r.wr)} | {fmt_pf(r.pf)} | {usd(r.net)} | {int(r.max_loss_streak)} |')

    lines += ['', f'**Preferred mechanism under preregistered gate: {preferred}**','']
    if preferred == 'NONE':
        status='B27EH_BNB_TWO_STAGE_ECONOMICS_NOT_SUPPORTED'
        lines += ['Neither fixed payout architecture satisfies the preregistered robustness gate. No BNB-native payout rule is selected.']
    else:
        status='B27EH_BNB_TWO_STAGE_ECONOMICS_SUPPORTED'
        lines += [f'**{preferred}** satisfies the preregistered robustness gate. This supports only a later independent re-arbitration/validation milestone; it is not yet an executable portfolio claim.']
    lines += ['', f'**Status: {status}**','', 'B27EH stops here. No re-arbitration, parameter optimization, forward shadow, or live integration is run automatically.']

    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
