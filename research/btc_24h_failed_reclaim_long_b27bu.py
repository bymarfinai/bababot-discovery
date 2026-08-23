#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIG_FILE = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Episodes.csv'
OUT_MD = ROOT / 'BTC_24H_FAILED_RECLAIM_LONG_B27BU_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_FAILED_RECLAIM_LONG_B27BU_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_FAILED_RECLAIM_LONG_B27BU_Summary.csv'
OUT_SELECT = ROOT / 'BTC_24H_FAILED_RECLAIM_LONG_B27BU_Selection.csv'
OUT_STATUS = ROOT / 'BTC_24H_FAILED_RECLAIM_LONG_B27BU_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
H24 = pd.Timedelta(hours=24)
MAJOR = ('external', 'development', 'reference_validation')
OOS = ('external', 'reference_validation')
TARGETS = {'R1_0': 1.0, 'R1_5': 1.5, 'R2_0': 2.0}
NOTIONAL = 500.0
FEE = 0.40


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_signals() -> pd.DataFrame:
    d = pd.read_csv(SIG_FILE)
    for c in ('first_sideways_ts', 'age2_source_start', 'age2_source_end',
              'confirmation_bar_start', 'confirmation_complete_ts',
              'eligible_open_ts', 'exit_effective_ts'):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    d['transition'] = as_bool(d['transition'])
    d['eligible_before_exit'] = as_bool(d['eligible_before_exit'])
    q = d[
        d.partition.isin(MAJOR) &
        (d.origin_state == 'BEAR') &
        (d.path_class == 'FAILED_RECLAIM')
    ].copy().sort_values(['partition', 'eligible_open_ts', 'episode_id']).reset_index(drop=True)

    expected = {'external': 6, 'development': 20, 'reference_validation': 8}
    for part, n in expected.items():
        got = len(q[q.partition == part])
        assert got == n, (part, got, n)
    assert len(q) == 34
    assert len(q[q.partition.isin(OOS)]) == 14
    assert q.eligible_before_exit.all()
    assert q.confirmation_complete_ts.notna().all()
    assert q.eligible_open_ts.notna().all()
    assert (q.eligible_open_ts == q.confirmation_complete_ts).all()
    assert (q.eligible_open_ts < q.exit_effective_ts).all()
    return q


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    if neg > 0:
        return pos / neg
    return np.nan


def get_open_at_or_after(x5: pd.DataFrame, ts: pd.Timestamp):
    pos = int(x5.index.searchsorted(ts, side='left'))
    if pos >= len(x5):
        return None
    return x5.index[pos], float(x5.iloc[pos].open)


def trade_one(x5: pd.DataFrame, r, target_name: str, multiple: float) -> dict:
    source_start = pd.Timestamp(r.age2_source_start)
    source_end = pd.Timestamp(r.age2_source_end)
    q = fast_slice(x5, source_start, source_end)
    assert len(q) == 48, (r.episode_id, len(q))
    assert q.index[0] == source_start and q.index[-1] == source_end - BAR5
    assert (q.index.to_series().diff().dropna() == BAR5).all()

    reclaim_i = int(float(r.first_reclaim_pos)) - 1
    rebreak_i = int(float(r.first_rebreak_pos)) - 1
    assert 0 <= reclaim_i < rebreak_i < 48
    local_low = float(q.iloc[reclaim_i:rebreak_i + 1].low.min())
    boundary = float(r.frozen_boundary)
    assert float(q.iloc[reclaim_i].close) <= boundary
    assert float(q.iloc[rebreak_i].close) > boundary

    entry_ts = pd.Timestamp(r.eligible_open_ts)
    assert entry_ts == pd.Timestamp(r.confirmation_complete_ts)
    pos = int(x5.index.searchsorted(entry_ts, side='left'))
    assert pos < len(x5) and x5.index[pos] == entry_ts
    entry_px = float(x5.iloc[pos].open)

    base = {
        'episode_id': int(r.episode_id),
        'partition': str(r.partition),
        'outcome': str(r.outcome),
        'transition': bool(r.transition),
        'target_name': target_name,
        'target_multiple': float(multiple),
        'frozen_boundary': boundary,
        'first_reclaim_pos': int(float(r.first_reclaim_pos)),
        'first_rebreak_pos': int(float(r.first_rebreak_pos)),
        'confirmation_bar_start': pd.Timestamp(r.confirmation_bar_start),
        'confirmation_complete_ts': pd.Timestamp(r.confirmation_complete_ts),
        'entry_ts': entry_ts,
        'entry_px': entry_px,
        'stop_px': local_low,
        'risk_usd_per_btc': entry_px - local_low,
        'risk_pct_entry': (entry_px - local_low) / entry_px if entry_px else np.nan,
        'regime_exit_effective_ts': pd.Timestamp(r.exit_effective_ts),
    }

    if not (local_low < entry_px):
        return {
            **base, 'status': 'INVALID_STOP_GEOMETRY', 'target_px': np.nan,
            'deadline_ts': pd.NaT, 'exit_ts': pd.NaT, 'exit_px': np.nan,
            'exit_reason': 'INVALID_STOP_GEOMETRY', 'hold_minutes': np.nan,
            'gross_return': np.nan, 'net_pnl_usd': np.nan,
        }

    risk = entry_px - local_low
    target = entry_px + float(multiple) * risk
    assert local_low < entry_px < target

    regime_exit = pd.Timestamp(r.exit_effective_ts)
    cap_exit = entry_ts + H24
    deadline = min(regime_exit, cap_exit)
    assert deadline > entry_ts
    deadline_reason = 'REGIME_EXIT' if regime_exit <= cap_exit else 'TIME_EXIT_24H'

    eq = fast_slice(x5, entry_ts, deadline)
    assert not eq.empty and eq.index[0] == entry_ts

    exit_ts = pd.NaT
    exit_px = np.nan
    exit_reason = None
    for ts, bar in eq.iterrows():
        stop_hit = float(bar.low) <= local_low
        target_hit = float(bar.high) >= target
        # Conservative ambiguity: resting stop wins when both are touched in one 5m bar.
        if stop_hit:
            exit_ts = ts
            exit_px = local_low
            exit_reason = 'SL_LOCAL_LOW'
            break
        if target_hit:
            exit_ts = ts
            exit_px = target
            exit_reason = f'TP_{target_name}'
            break

    if exit_reason is None:
        te = get_open_at_or_after(x5, deadline)
        assert te is not None
        exit_ts, exit_px = te
        exit_reason = deadline_reason

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    hold = float((pd.Timestamp(exit_ts) - entry_ts) / pd.Timedelta(minutes=1))
    return {
        **base, 'status': 'EXECUTED', 'target_px': target,
        'deadline_ts': deadline, 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'exit_reason': exit_reason, 'hold_minutes': hold,
        'gross_return': gross, 'net_pnl_usd': net,
    }


def subset(d: pd.DataFrame, part: str) -> pd.DataFrame:
    if part == 'POOLED_OOS':
        return d[d.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR':
        return d[d.partition.isin(MAJOR)].copy()
    return d[d.partition == part].copy()


def metrics(g: pd.DataFrame) -> dict:
    ex = g[g.status == 'EXECUTED'].copy()
    n = len(ex)
    wins = int((ex.net_pnl_usd > 0).sum()) if n else 0
    losses = int((ex.net_pnl_usd <= 0).sum()) if n else 0
    return {
        'signals': len(g),
        'executed_n': n,
        'invalid_n': int((g.status != 'EXECUTED').sum()),
        'wins': wins,
        'losses': losses,
        'wr': wins / n if n else np.nan,
        'pf': pf(ex.net_pnl_usd) if n else np.nan,
        'expectancy_usd': float(ex.net_pnl_usd.mean()) if n else np.nan,
        'total_net_pnl_usd': float(ex.net_pnl_usd.sum()) if n else np.nan,
        'tp_n': int(ex.exit_reason.astype(str).str.startswith('TP_').sum()) if n else 0,
        'sl_n': int((ex.exit_reason == 'SL_LOCAL_LOW').sum()) if n else 0,
        'regime_exit_n': int((ex.exit_reason == 'REGIME_EXIT').sum()) if n else 0,
        'time24_n': int((ex.exit_reason == 'TIME_EXIT_24H').sum()) if n else 0,
        'median_risk_pct': float(ex.risk_pct_entry.median()) if n else np.nan,
        'median_hold_minutes': float(ex.hold_minutes.median()) if n else np.nan,
    }


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target_name in TARGETS:
        z = d[d.target_name == target_name].copy()
        for part in (*MAJOR, 'POOLED_OOS', 'POOLED_MAJOR'):
            q = subset(z, part)
            for outcome in ('ALL', 'TRANSITION', 'RESUME'):
                g = q if outcome == 'ALL' else q[q.outcome == outcome]
                m = metrics(g)
                rows.append({'target_name': target_name, 'partition': part, 'outcome': outcome, **m})
    return pd.DataFrame(rows)


def row(s: pd.DataFrame, target: str, part: str, outcome: str = 'ALL'):
    q = s[(s.target_name == target) & (s.partition == part) & (s.outcome == outcome)]
    assert len(q) == 1
    return q.iloc[0]


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def fmt_pf(v):
    if pd.isna(v): return '-'
    if np.isinf(v): return 'inf'
    return f'{float(v):.2f}'


def main():
    sig = load_signals()
    x5, coverage = b21.load5()
    assert len(x5) == 698112
    assert abs(float(coverage) - 1.0) < 1e-12

    rows = []
    for r in sig.itertuples(index=False):
        for target_name, mult in TARGETS.items():
            rows.append(trade_one(x5, r, target_name, mult))
    d = pd.DataFrame(rows)
    assert len(d) == 34 * len(TARGETS)
    d.to_csv(OUT_TRADES, index=False)

    s = summarize(d)
    s.to_csv(OUT_SUM, index=False)

    selections = []
    passers = []
    for target in TARGETS:
        major_rows = [row(s, target, p) for p in MAJOR]
        gate_n = all(int(r.executed_n) >= 5 for r in major_rows)
        gate_exp = all(pd.notna(r.expectancy_usd) and float(r.expectancy_usd) > 0 for r in major_rows)
        gate_pf = all(pd.notna(r.pf) and float(r.pf) >= 1.20 for r in major_rows)
        gate_wr = all(pd.notna(r.wr) and float(r.wr) >= .50 for r in major_rows)
        robust = bool(gate_n and gate_exp and gate_pf and gate_wr)
        high70 = bool(robust and all(float(r.wr) >= .70 for r in major_rows))
        min_pf = min(float(r.pf) for r in major_rows) if all(pd.notna(r.pf) for r in major_rows) else np.nan
        pooled = row(s, target, 'POOLED_MAJOR')
        rec = {
            'target_name': target, 'target_multiple': TARGETS[target],
            'gate_n': gate_n, 'gate_positive_expectancy': gate_exp,
            'gate_pf_1p20': gate_pf, 'gate_wr_50': gate_wr,
            'robust_pass': robust, 'high_quality_70': high70,
            'minimum_partition_pf': min_pf,
            'pooled_major_expectancy_usd': pooled.expectancy_usd,
            'pooled_major_total_net_pnl_usd': pooled.total_net_pnl_usd,
        }
        selections.append(rec)
        if robust:
            passers.append(rec)

    sel = pd.DataFrame(selections)
    selected = None
    if passers:
        selected = sorted(
            passers,
            key=lambda z: (z['minimum_partition_pf'], z['pooled_major_expectancy_usd']),
            reverse=True,
        )[0]['target_name']
        verdict = f'B27BU_BEAR_FAILED_RECLAIM_LONG_SUPPORTED_{selected}'
    else:
        verdict = 'B27BU_BEAR_FAILED_RECLAIM_LONG_NOT_SUPPORTED'
    sel['selected'] = sel.target_name.eq(selected) if selected else False
    sel.to_csv(OUT_SELECT, index=False)
    OUT_STATUS.write_text(verdict + '\n')

    lines = [
        '# B27BU — BTC 24H BEAR-Origin Failed-Reclaim LONG Economics — Result', '',
        '**Audit status: PASS.** Entry is the next raw 5m open after B27BT causal re-break confirmation; no eventual regime outcome or containing 4H final close is used for entry or risk geometry.', '',
        'Frozen B27BT BEAR FAILED_RECLAIM identity reproduced exactly: **34 signals = external 6 + development 20 + reference_validation 8; pooled OOS 14.**', '',
        'Economics: **$500 notional, $0.40 round-trip fee**. One frozen structural stop (`LOCAL_LOW`) and targets 1R / 1.5R / 2R.', '',
        '## Major-partition economics', '',
        '| Target | Partition | N | WR | PF | Exp/trade | Total net | TP | SL | Regime exit | 24h exit |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for target in TARGETS:
        for part in MAJOR:
            r = row(s, target, part)
            lines.append(
                f'| {target} | {part} | {int(r.executed_n)} | {fmt_pct(r.wr)} | {fmt_pf(r.pf)} | '
                f'${float(r.expectancy_usd):+.2f} | ${float(r.total_net_pnl_usd):+.2f} | '
                f'{int(r.tp_n)} | {int(r.sl_n)} | {int(r.regime_exit_n)} | {int(r.time24_n)} |'
            )

    lines += ['', '## Pooled readout', '',
              '| Target | Pool | N | WR | PF | Exp/trade | Total net | Median risk | Median hold |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for target in TARGETS:
        for part in ('POOLED_OOS', 'POOLED_MAJOR'):
            r = row(s, target, part)
            lines.append(
                f'| {target} | {part} | {int(r.executed_n)} | {fmt_pct(r.wr)} | {fmt_pf(r.pf)} | '
                f'${float(r.expectancy_usd):+.2f} | ${float(r.total_net_pnl_usd):+.2f} | '
                f'{fmt_pct(r.median_risk_pct)} | {float(r.median_hold_minutes):.0f}m |'
            )

    lines += ['', '## Outcome diagnostic — pooled major', '',
              '| Target | Outcome | N | WR | PF | Exp/trade | Total net |',
              '|---|---|---:|---:|---:|---:|---:|']
    for target in TARGETS:
        for outcome in ('TRANSITION', 'RESUME'):
            r = row(s, target, 'POOLED_MAJOR', outcome)
            lines.append(
                f'| {target} | {outcome} | {int(r.executed_n)} | {fmt_pct(r.wr)} | {fmt_pf(r.pf)} | '
                f'${float(r.expectancy_usd):+.2f} | ${float(r.total_net_pnl_usd):+.2f} |'
            )

    lines += ['', '## Frozen selection gate', '',
              '| Target | N>=5 each | Exp>0 each | PF>=1.20 each | WR>=50% each | ROBUST_PASS | HIGH_QUALITY_70 | Min PF | Selected |',
              '|---|---|---|---|---|---|---|---:|---|']
    for z in selections:
        lines.append(
            f'| {z["target_name"]} | {"PASS" if z["gate_n"] else "FAIL"} | '
            f'{"PASS" if z["gate_positive_expectancy"] else "FAIL"} | '
            f'{"PASS" if z["gate_pf_1p20"] else "FAIL"} | '
            f'{"PASS" if z["gate_wr_50"] else "FAIL"} | '
            f'{"YES" if z["robust_pass"] else "NO"} | {"YES" if z["high_quality_70"] else "NO"} | '
            f'{fmt_pf(z["minimum_partition_pf"])} | {"YES" if selected == z["target_name"] else "NO"} |'
        )

    lines += ['', f'**Frozen verdict: `{verdict}`.**', '',
              'Interpretation: this is an economic screen of the already-inspected B27BT lineage. A pass would still require a separate frequency/portfolio/live-readiness step before any BBC production change.', '',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
