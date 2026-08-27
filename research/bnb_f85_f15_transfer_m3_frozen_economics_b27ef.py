#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bbc_f85_f15_signals as sig
import eth_f85_f15_transfer_m1_k1_opp0 as data_base
import bnb_f85_f15_transfer_m2_exact_signal_b27ee as m2
import btc_f85_long_b27do_live_executable_exit_b27dq as dq
import btc_london_ny_short_mirror_b27ad as shortmod

PFX = 'BNB_F85_F15_TRANSFER_M3_FROZEN_ECONOMICS_B27EF'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SOURCE = ROOT / f'{PFX}_SourceSummary.csv'
OUT_STRESS = ROOT / f'{PFX}_Slippage.csv'
OUT_EXIT = ROOT / f'{PFX}_ExitReasons.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
MAJOR = ('external', 'development', 'reference_validation')
SOURCES = ('ALT_0330', 'RAW_0530', 'SHORT_2000')
PRIORITY = {'ALT_0330': 0, 'RAW_0530': 1, 'SHORT_2000': 2}
BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40


def fs(x, a, z):
    return x.iloc[int(x.index.searchsorted(a, side='left')):int(x.index.searchsorted(z, side='left'))]


def candidate_id(partition, side, source, entry_ts):
    return f'{partition}|{side}|{source}|{pd.Timestamp(entry_ts).isoformat()}'


def replay_candidates(x5):
    rows = []
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    for a in anchors:
        for source in ('ALT_0330', 'RAW_0530'):
            cm = sig.LONG_ZONE_CLOCKS[source]
            rs = a + pd.Timedelta(minutes=cm)
            re = rs + sig.REF_DUR
            es = re
            ee = es + sig.EXEC_DUR
            p = m2.part_for(es)
            if p is None or es.weekday() >= 5:
                continue
            ref, exe = fs(x5, rs, re), fs(x5, es, ee)
            if len(ref) != sig.REF_BARS or len(exe) != sig.EXEC_BARS:
                continue
            for s in sig.replay_session(sig.LongF85Session(source, a, ref), exe):
                rows.append({
                    'partition': p, 'side': 'LONG', 'source': source,
                    'anchor_date_utc': str(a.date()), 'execution_end': ee,
                    'entry_ts': pd.Timestamp(s.entry_ts), 'entry_px': float(s.entry_px),
                    'confirmation_bar_start': pd.Timestamp(s.confirmation_bar_start),
                    'H': float(s.H), 'L': float(s.L), 'R': float(s.R),
                    'entry_level': float(s.entry_level), 'stop_level': float(s.stop_level),
                    'target_level': float(s.target_level),
                    'touch_elapsed_min': float(s.touch_elapsed_min),
                })

        cm = sig.SHORT20_CLOCK
        rs = a + pd.Timedelta(minutes=cm)
        re = rs + sig.REF_DUR
        es = re
        ee = es + sig.EXEC_DUR
        p = m2.part_for(es)
        if p is None or es.weekday() >= 5:
            continue
        ref, exe = fs(x5, rs, re), fs(x5, es, ee)
        if len(ref) != sig.REF_BARS or len(exe) != sig.EXEC_BARS:
            continue
        for s in sig.replay_session(sig.ShortF15Session(a, ref), exe):
            rows.append({
                'partition': p, 'side': 'SHORT', 'source': 'SHORT_2000',
                'anchor_date_utc': str(a.date()), 'execution_end': ee,
                'entry_ts': pd.Timestamp(s.entry_ts), 'entry_px': float(s.entry_px),
                'confirmation_bar_start': pd.Timestamp(s.confirmation_bar_start),
                'H': float(s.H), 'L': float(s.L), 'R': float(s.R),
                'entry_level': float(s.entry_level), 'stop_level': float(s.stop_level),
                'target_level': float(s.target_level),
                'touch_elapsed_min': float(s.touch_elapsed_min),
            })
    d = pd.DataFrame(rows)
    if d.empty:
        raise AssertionError('no B27EF candidates generated')
    d['candidate_id'] = [candidate_id(r.partition, r.side, r.source, r.entry_ts) for r in d.itertuples(index=False)]
    return d.sort_values(['entry_ts', 'source', 'candidate_id']).reset_index(drop=True)


def fixed_long_exit(r, x5):
    entry_ts = pd.Timestamp(r.entry_ts)
    end = pd.Timestamp(r.execution_end)
    entry = float(r.entry_px)
    f35 = float(r.stop_level)
    e20 = float(r.target_level)
    q = fs(x5, entry_ts, end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError(f'missing LONG execution slice {r.candidate_id}')
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None
    for ts, bar in q.iterrows():
        if float(bar.high) >= e20:
            exit_ts = pd.Timestamp(ts)
            exit_px = e20
            reason = 'TP_E20'
            break
        if float(bar.close) < f35:
            exit_ts = pd.Timestamp(ts) + BAR5
            exit_px = float(bar.close)
            reason = 'CLOSE_INVALIDATION_F35'
            break
    if reason is None:
        pos = int(x5.index.searchsorted(end, side='left'))
        if pos >= len(x5) or x5.index[pos] != end:
            raise AssertionError(f'missing LONG time-exit bar {r.candidate_id}')
        exit_ts = end
        exit_px = float(x5.iloc[pos].open)
        reason = 'TIME_EXIT_EXEC_END'
    net = (float(exit_px) / entry - 1.0) * NOTIONAL - FEE
    return {'exit_ts': exit_ts, 'exit_px': float(exit_px), 'exit_reason': reason, 'pnl': float(net)}


def evaluate_candidate(r, x5):
    if r.side == 'LONG':
        fixed = fixed_long_exit(r, x5)
        if r.source == 'ALT_0330':
            return fixed
        if r.source != 'RAW_0530':
            raise AssertionError(f'unexpected LONG source {r.source}')
        rr = SimpleNamespace(
            entry_bar_start=pd.Timestamp(r.entry_ts),
            execution_end=pd.Timestamp(r.execution_end),
            entry_px=float(r.entry_px), H=float(r.H), range=float(r.R),
            F35=float(r.stop_level), E20=float(r.target_level), zone='RAW_0530',
            exit_reason=fixed['exit_reason'], net_pnl_usd=fixed['pnl'],
        )
        live = dq.live_runner_exit(rr, x5)
        return {
            'exit_ts': pd.Timestamp(live['live_exit_ts']),
            'exit_px': float(live['live_exit_px']),
            'exit_reason': str(live['live_exit_reason']),
            'pnl': float(live['live_net_pnl_usd']),
        }

    sr = pd.Series({
        'entry_executed': True,
        'entry_start': pd.Timestamp(r.entry_ts),
        'session_end': pd.Timestamp(r.execution_end),
        'entry_px': float(r.entry_px),
        'L': float(r.L), 'F65': float(r.stop_level), 'E20_DOWN': float(r.target_level),
        'range': float(r.R),
    })
    out = shortmod.simulate_fixed(x5, sr)
    if pd.isna(out['fixed_net_pnl_usd']):
        raise AssertionError(f'SHORT simulator returned no trade {r.candidate_id}')
    exit_ts = pd.Timestamp(r.entry_ts) + pd.Timedelta(minutes=float(out['fixed_hold_minutes']))
    return {
        'exit_ts': exit_ts,
        'exit_px': float(out['fixed_exit_px']),
        'exit_reason': str(out['fixed_exit_reason']),
        'pnl': float(out['fixed_net_pnl_usd']),
    }


def lock_portfolio(d):
    q = d.copy()
    q['priority'] = q.source.map(PRIORITY).astype(int)
    q = q.sort_values(['entry_ts', 'priority', 'candidate_id']).reset_index(drop=True)
    q['accepted'] = False
    q['blocked_by'] = ''
    active_exit = pd.NaT
    active_id = ''
    for i, r in q.iterrows():
        et = pd.Timestamp(r.entry_ts)
        if pd.isna(active_exit) or pd.Timestamp(active_exit) <= et:
            q.at[i, 'accepted'] = True
            active_exit = pd.Timestamp(r.exit_ts)
            active_id = str(r.candidate_id)
            if active_exit < et:
                raise AssertionError('accepted exit precedes entry')
        else:
            q.at[i, 'blocked_by'] = active_id
    a = q[q.accepted.astype(bool)].sort_values('entry_ts')
    prev_exit = pd.NaT
    for r in a.itertuples(index=False):
        if pd.notna(prev_exit) and pd.Timestamp(r.entry_ts) < pd.Timestamp(prev_exit):
            raise AssertionError('overlapping accepted BNB positions')
        prev_exit = pd.Timestamp(r.exit_ts)
    return q


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def loss_streak(d, col='pnl'):
    q = d.sort_values('entry_ts')
    best = cur = 0
    for v in pd.to_numeric(q[col], errors='coerce'):
        if pd.notna(v) and float(v) <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(d, col='pnl'):
    v = pd.to_numeric(d[col], errors='coerce').dropna()
    if len(v) == 0:
        return {'n': 0, 'wins': 0, 'wr': np.nan, 'pf': np.nan, 'expectancy': np.nan, 'net': 0.0, 'max_loss_streak': 0}
    return {
        'n': int(len(v)), 'wins': int((v > 0).sum()),
        'wr': float((v > 0).mean()), 'pf': pf(v),
        'expectancy': float(v.mean()), 'net': float(v.sum()),
        'max_loss_streak': loss_streak(d, col),
    }


def summary_tables(locked):
    acc = locked[locked.accepted.astype(bool)].copy()
    rows = []
    for p in (*data_base.PARTS.keys(), 'POOLED_MAJOR'):
        q = acc[acc.partition.isin(MAJOR)] if p == 'POOLED_MAJOR' else acc[acc.partition == p]
        raw = locked[locked.partition.isin(MAJOR)] if p == 'POOLED_MAJOR' else locked[locked.partition == p]
        rows.append({'partition': p, 'candidates': len(raw), 'accepted': len(q), 'blocked': int(len(raw)-len(q)), **metrics(q)})
    src_rows=[]
    for src in SOURCES:
        q = acc[(acc.source == src) & acc.partition.isin(MAJOR)]
        raw = locked[(locked.source == src) & locked.partition.isin(MAJOR)]
        src_rows.append({'source': src, 'side': 'SHORT' if src == 'SHORT_2000' else 'LONG',
                         'candidates': len(raw), 'accepted': len(q), 'blocked': len(raw)-len(q), **metrics(q)})
    return pd.DataFrame(rows), pd.DataFrame(src_rows)


def stressed_metrics(locked, bps):
    q = locked[locked.accepted.astype(bool) & locked.partition.isin(MAJOR)].copy()
    f = float(bps) / 10000.0
    long = q.side.eq('LONG')
    short = q.side.eq('SHORT')
    q['stress_entry_px'] = q.entry_px.astype(float)
    q['stress_exit_px'] = q.exit_px.astype(float)
    q.loc[long, 'stress_entry_px'] = q.loc[long, 'entry_px'].astype(float) * (1 + f)
    q.loc[long, 'stress_exit_px'] = q.loc[long, 'exit_px'].astype(float) * (1 - f)
    q.loc[short, 'stress_entry_px'] = q.loc[short, 'entry_px'].astype(float) * (1 - f)
    q.loc[short, 'stress_exit_px'] = q.loc[short, 'exit_px'].astype(float) * (1 + f)
    q['stress_pnl'] = np.where(
        long,
        (q.stress_exit_px / q.stress_entry_px - 1.0) * NOTIONAL - FEE,
        (1.0 - q.stress_exit_px / q.stress_entry_px) * NOTIONAL - FEE,
    )
    return metrics(q, 'stress_pnl')


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main():
    # Prerequisites are frozen before economics.
    m1 = (ROOT / 'BNB_F85_F15_TRANSFER_M1_K1_OPP0_B27ED_Status.txt').read_text().strip()
    if m1 != 'B27ED_BNB_M1_K1_OPP0_STRUCTURAL_REPLICATION_SUPPORTED':
        raise AssertionError(f'B27ED prerequisite drift: {m1}')
    if not (ROOT / 'BNB_F85_F15_TRANSFER_M2_EXACT_SIGNAL_B27EE_Result.md').exists():
        raise AssertionError('B27EE result missing')

    # BTC economic constants and exact adapters must remain unchanged.
    assert shortmod.NOTIONAL == NOTIONAL and shortmod.FEE == FEE
    assert dq.dn.dl.NOTIONAL == NOTIONAL and dq.dn.dl.FEE == FEE
    assert sig.LONG_ZONE_CLOCKS['ALT_0330'] == 210
    assert sig.LONG_ZONE_CLOCKS['RAW_0530'] == 330
    assert sig.SHORT20_CLOCK == 1200

    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB coverage below prereg gate: {coverage:.6f}')

    cand = replay_candidates(x5)
    if set(cand.source.unique()) != set(SOURCES):
        raise AssertionError(f'unexpected source set: {sorted(cand.source.unique())}')

    # Exact B27EE signal identity + geometry reproduction for the three frozen habitats.
    saved = pd.read_csv(ROOT / 'BNB_F85_F15_TRANSFER_M2_EXACT_SIGNAL_B27EE_Detail.csv')
    saved = saved[(saved.symbol == TARGET) & saved.source.isin(SOURCES)].copy()
    saved['entry_ts'] = pd.to_datetime(saved.entry_ts, utc=True)
    saved['candidate_id'] = [candidate_id(r.partition, r.side, r.source, r.entry_ts) for r in saved.itertuples(index=False)]
    got_ids = cand.sort_values(['entry_ts','source']).candidate_id.tolist()
    want_ids = saved.sort_values(['entry_ts','source']).candidate_id.tolist()
    if got_ids != want_ids:
        raise AssertionError(f'B27EE candidate identity drift: generated={len(got_ids)} expected={len(want_ids)}')
    gm = cand.set_index('candidate_id'); sm = saved.set_index('candidate_id')
    for cid in got_ids:
        for a,b in (('entry_px','entry_px'),('H','H'),('L','L'),('entry_level','entry_level'),('stop_level','stop_level'),('target_level','target_level')):
            if not np.isclose(float(gm.at[cid,a]), float(sm.at[cid,b]), rtol=1e-10, atol=1e-10):
                raise AssertionError(f'B27EE geometry drift {cid} {a}')

    econ=[]
    for r in cand.itertuples(index=False):
        z = evaluate_candidate(r, x5)
        econ.append(z)
    econ = pd.DataFrame(econ)
    d = pd.concat([cand.reset_index(drop=True), econ.reset_index(drop=True)], axis=1)
    d['exit_ts'] = pd.to_datetime(d.exit_ts, utc=True)
    locked = lock_portfolio(d)
    locked.to_csv(OUT_DETAIL, index=False)

    summary, sources = summary_tables(locked)
    summary.to_csv(OUT_SUM, index=False)
    sources.to_csv(OUT_SOURCE, index=False)

    stress_rows=[]
    for bps in (0,2,5,10):
        m=stressed_metrics(locked,bps)
        stress_rows.append({'slippage_bps_per_fill':bps,**m})
    stress=pd.DataFrame(stress_rows)
    stress.to_csv(OUT_STRESS,index=False)

    exits=(locked[locked.accepted.astype(bool) & locked.partition.isin(MAJOR)]
           .groupby(['source','side','exit_reason'],dropna=False).size().reset_index(name='n'))
    exits.to_csv(OUT_EXIT,index=False)

    pool=summary[summary.partition=='POOLED_MAJOR'].iloc[0]
    major=summary[summary.partition.isin(MAJOR)]
    s5=stress[stress.slippage_bps_per_fill==5].iloc[0]
    support=bool(
        int(pool.accepted)>=60 and float(pool.wr)>=.70 and float(pool.pf)>=1.80 and float(pool.net)>0
        and int(pool.max_loss_streak)<=4
        and bool((major.net>0).all())
        and bool((sources.net>0).all())
        and float(s5.wr)>=.65 and float(s5.pf)>=1.50 and float(s5.net)>0
    )
    status='B27EF_BNB_FROZEN_ECONOMICS_SUPPORTED' if support else 'B27EF_BNB_FROZEN_ECONOMICS_NOT_SUPPORTED'
    OUT_STATUS.write_text(status+'\n')

    lines=[
        '# BNB F85/F15 Transfer — M3 Frozen BTC-Rule Economics — B27EF Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. Exact B27EE candidate identity/geometry reproduction: **PASS ({len(cand)} candidates)**.','',
        'Frozen portfolio: **ALT_0330 fixed E20 + RAW_0530 B27DQ N+2 runner + SHORT_2000 fixed E20_DOWN**. $500 notional, $0.40 fee, one BNB position.','',
        '## Pooled-major portfolio','',
        '| Candidates | Accepted | Blocked | Wins | WR | PF | Expectancy | Net | Max loss streak |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        f'| {int(pool.candidates)} | {int(pool.accepted)} | {int(pool.blocked)} | {int(pool.wins)} | {pct(pool.wr)} | {num(pool.pf)} | {usd(pool.expectancy)} | {usd(pool.net)} | {int(pool.max_loss_streak)} |','',
        '## Source contribution','',
        '| Source | Side | Candidates | Accepted | WR | PF | Exp | Net | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for r in sources.itertuples(index=False):
        lines.append(f'| {r.source} | {r.side} | {r.candidates} | {r.accepted} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {r.max_loss_streak} |')
    lines += ['', '## Major partitions','',
              '| Partition | N | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|']
    for p in MAJOR:
        r=summary[summary.partition==p].iloc[0]
        lines.append(f'| {p} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {int(r.max_loss_streak)} |')
    lines += ['', '## Adverse fill sensitivity — pooled major','',
              '| Slippage/fill | N | WR | PF | Exp | Net | Max LS |','|---:|---:|---:|---:|---:|---:|---:|']
    for r in stress.itertuples(index=False):
        lines.append(f'| {r.slippage_bps_per_fill} bps | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {r.max_loss_streak} |')
    lines += ['', '## Exit reasons','', '| Source | Side | Exit reason | N |','|---|---|---|---:|']
    for r in exits.itertuples(index=False):
        lines.append(f'| {r.source} | {r.side} | {r.exit_reason} | {r.n} |')
    lines += ['',f'**Status: {status}**','',
              'B27EF stops here. No BNB-specific optimization, forward shadow, or next milestone is run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
