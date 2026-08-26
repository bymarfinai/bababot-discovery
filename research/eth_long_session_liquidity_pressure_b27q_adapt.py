#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_LONG_SESSION_LIQUIDITY_PRESSURE_B27Q_ADAPT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_VISITS = ROOT / f'{PFX}_Visits.csv'
OUT_SIGNALS = ROOT / f'{PFX}_Signals.csv'
OUT_STRUCT = ROOT / f'{PFX}_StructuralSummary.csv'
OUT_SELECTED = ROOT / f'{PFX}_SelectedCohort.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ethdata.PARTS
MAJOR = ('external', 'development', 'reference_validation')
KS = (1, 2, 3)
TRANSITIONS = {
    'ASIA_TO_LONDON': {
        'prev_start': (0, 0), 'prev_end': (8, 0),
        'next_start': (8, 0), 'next_end': (13, 30),
    },
    'LONDON_TO_NEWYORK': {
        'prev_start': (8, 0), 'prev_end': (13, 30),
        'next_start': (13, 30), 'next_end': (20, 0),
    },
}


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def ts_for_day(day: pd.Timestamp, hhmm: tuple[int, int]) -> pd.Timestamp:
    hh, mm = hhmm
    return pd.Timestamp(day.date(), tz='UTC') + pd.Timedelta(hours=hh, minutes=mm)


def scan_session(q5: pd.DataFrame, H: float, L: float):
    assert H > L
    hi_visits = 0
    lo_visits = 0
    hi_touching = False
    lo_touching = False
    visits = []

    for ts, r in q5.iterrows():
        hi = float(r.high); lo = float(r.low); cl = float(r.close)
        break_hi = cl > H
        break_lo = cl < L
        if break_hi and break_lo:
            raise AssertionError('strict close beyond both ordered range edges')
        if break_hi or break_lo:
            return {
                'status': 'OK',
                'breakout_side': 'HIGH' if break_hi else 'LOW',
                'breakout_bar_start': pd.Timestamp(ts),
                'breakout_ts': pd.Timestamp(ts) + BAR5,
                'visits': visits,
                'high_visits': hi_visits,
                'low_visits': lo_visits,
            }

        hit_hi = hi >= H and cl <= H
        hit_lo = lo <= L and cl >= L
        if hit_hi and hit_lo:
            return {
                'status': 'AMBIGUOUS_BOTH_LEVELS',
                'breakout_side': None,
                'breakout_bar_start': pd.NaT,
                'breakout_ts': pd.NaT,
                'visits': [],
                'high_visits': np.nan,
                'low_visits': np.nan,
            }

        if hit_hi and not hi_touching:
            hi_visits += 1
            visits.append({
                'level': 'HIGH', 'visit_no': hi_visits,
                'visit_bar_start': pd.Timestamp(ts),
                'visit_ts': pd.Timestamp(ts) + BAR5,
                'same_visits_at_event': hi_visits,
                'opp_visits_at_event': lo_visits,
            })
        if hit_lo and not lo_touching:
            lo_visits += 1
            visits.append({
                'level': 'LOW', 'visit_no': lo_visits,
                'visit_bar_start': pd.Timestamp(ts),
                'visit_ts': pd.Timestamp(ts) + BAR5,
                'same_visits_at_event': lo_visits,
                'opp_visits_at_event': hi_visits,
            })

        hi_touching = bool(hit_hi)
        lo_touching = bool(hit_lo)

    return {
        'status': 'OK', 'breakout_side': None,
        'breakout_bar_start': pd.NaT, 'breakout_ts': pd.NaT,
        'visits': visits, 'high_visits': hi_visits, 'low_visits': lo_visits,
    }


def synthetic_tests():
    H, L = 100.0, 90.0
    idx = pd.date_range('2026-01-05 13:30', periods=6, freq='5min', tz='UTC')
    q = pd.DataFrame([
        {'open': 98, 'high': 100.2, 'low': 97, 'close': 99},
        {'open': 99, 'high': 100.1, 'low': 98, 'close': 99.5},
        {'open': 99.5, 'high': 99.8, 'low': 97, 'close': 98},
        {'open': 98, 'high': 100.3, 'low': 97.5, 'close': 99},
        {'open': 99, 'high': 99.5, 'low': 96, 'close': 98},
        {'open': 98, 'high': 102, 'low': 97, 'close': 101},
    ], index=idx)
    s = scan_session(q, H, L)
    hv = [v for v in s['visits'] if v['level'] == 'HIGH']
    assert len(hv) == 2 and [v['visit_no'] for v in hv] == [1, 2]
    assert s['breakout_side'] == 'HIGH'

    q2 = pd.DataFrame([
        {'open': 95, 'high': 100, 'low': 90, 'close': 95},
    ], index=idx[:1])
    assert scan_session(q2, H, L)['status'] == 'AMBIGUOUS_BOTH_LEVELS'

    q3 = pd.DataFrame([
        {'open': 99, 'high': 102, 'low': 98, 'close': 101},
    ], index=idx[:1])
    s3 = scan_session(q3, H, L)
    assert s3['breakout_side'] == 'HIGH' and s3['high_visits'] == 0


def terminal_outcome(side: str | None) -> str:
    if side == 'HIGH': return 'TARGET_BREAK'
    if side == 'LOW': return 'OPPOSITE_BREAK'
    return 'NO_BREAK'


def collect(x5: pd.DataFrame):
    visits_rows = []
    signals_rows = []
    session_status = []

    for part, (p0, p1) in PARTS.items():
        first_day = p0.normalize()
        last_day = (p1 - pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first_day, last_day, freq='D', tz='UTC'):
            if day.weekday() >= 5:
                continue
            for transition, cfg in TRANSITIONS.items():
                prev_start = ts_for_day(day, cfg['prev_start'])
                prev_end = ts_for_day(day, cfg['prev_end'])
                active_start = ts_for_day(day, cfg['next_start'])
                active_end = ts_for_day(day, cfg['next_end'])
                if prev_start < p0 or active_end > p1:
                    continue
                prev = fast_slice(x5, prev_start, prev_end)
                active = fast_slice(x5, active_start, active_end)
                exp_prev = int((prev_end - prev_start) / BAR5)
                exp_active = int((active_end - active_start) / BAR5)
                if len(prev) != exp_prev or len(active) != exp_active:
                    continue
                H = float(prev.high.max()); L = float(prev.low.min())
                if not H > L:
                    continue
                scan = scan_session(active, H, L)
                session_status.append({
                    'partition': part, 'transition': transition,
                    'date_utc': str(day.date()), 'status': scan['status'],
                    'breakout_side': scan['breakout_side'],
                })
                if scan['status'] != 'OK':
                    continue
                outcome = terminal_outcome(scan['breakout_side'])
                breakout_ts = scan['breakout_ts']
                for v in scan['visits']:
                    vr = {
                        'partition': part, 'transition': transition,
                        'date_utc': str(day.date()),
                        'previous_session_start': prev_start,
                        'previous_session_end': prev_end,
                        'active_session_start': active_start,
                        'active_session_end': active_end,
                        'previous_session_high': H,
                        'previous_session_low': L,
                        'range': H - L,
                        'breakout_side': scan['breakout_side'],
                        'breakout_ts': breakout_ts,
                        'structural_outcome': outcome,
                        **v,
                    }
                    visits_rows.append(vr)
                    if v['level'] == 'HIGH' and int(v['visit_no']) in KS:
                        mins = np.nan
                        if pd.notna(breakout_ts):
                            mins = float((pd.Timestamp(breakout_ts) - pd.Timestamp(v['visit_ts'])) / pd.Timedelta(minutes=1))
                        signals_rows.append({
                            'partition': part, 'transition': transition,
                            'date_utc': str(day.date()),
                            'side': 'LONG', 'k': int(v['visit_no']),
                            'opp_visits_at_signal': int(v['opp_visits_at_event']),
                            'signal_bar_start': v['visit_bar_start'],
                            'signal_ts': v['visit_ts'],
                            'previous_session_high': H,
                            'previous_session_low': L,
                            'range': H - L,
                            'active_session_end': active_end,
                            'structural_outcome': outcome,
                            'breakout_side': scan['breakout_side'],
                            'breakout_ts': breakout_ts,
                            'minutes_to_terminal': mins,
                        })
    return pd.DataFrame(visits_rows), pd.DataFrame(signals_rows), pd.DataFrame(session_status)


def summarize(signals: pd.DataFrame):
    rows = []
    for transition in TRANSITIONS:
        for part in PARTS:
            for k in KS:
                base = signals[(signals.transition == transition) & (signals.partition == part) & (signals.k == k)]
                for purity in ('ALL', 'OPP0'):
                    g = base if purity == 'ALL' else base[base.opp_visits_at_signal == 0]
                    n = int(len(g))
                    br = g[g.structural_outcome != 'NO_BREAK'] if n else g
                    rows.append({
                        'transition': transition, 'partition': part,
                        'k': k, 'purity': purity, 'n': n,
                        'target_break_n': int((g.structural_outcome == 'TARGET_BREAK').sum()) if n else 0,
                        'opposite_break_n': int((g.structural_outcome == 'OPPOSITE_BREAK').sum()) if n else 0,
                        'no_break_n': int((g.structural_outcome == 'NO_BREAK').sum()) if n else 0,
                        'target_break_prob': float((g.structural_outcome == 'TARGET_BREAK').mean()) if n else np.nan,
                        'opposite_break_prob': float((g.structural_outcome == 'OPPOSITE_BREAK').mean()) if n else np.nan,
                        'no_break_prob': float((g.structural_outcome == 'NO_BREAK').mean()) if n else np.nan,
                        'median_minutes_to_terminal': float(br.minutes_to_terminal.median()) if len(br) else np.nan,
                    })
    return pd.DataFrame(rows)


def select_cohort(sm: pd.DataFrame):
    candidates = []
    for transition in TRANSITIONS:
        for k in KS:
            for purity in ('ALL', 'OPP0'):
                z = sm[(sm.transition == transition) & (sm.k == k) & (sm.purity == purity) & sm.partition.isin(MAJOR)]
                if len(z) != 3:
                    continue
                passed = bool((z.n >= 30).all() & (z.target_break_prob >= 0.70).all() & (z.opposite_break_prob <= 0.20).all())
                if not passed:
                    continue
                candidates.append({
                    'transition': transition, 'k': k, 'purity': purity,
                    'min_target_prob': float(z.target_break_prob.min()),
                    'max_opp_prob': float(z.opposite_break_prob.max()),
                    'total_n': int(z.n.sum()),
                })
    if not candidates:
        return pd.DataFrame(columns=['transition','k','purity','min_target_prob','max_opp_prob','total_n'])
    c = pd.DataFrame(candidates)
    c['purity_rank'] = c.purity.map({'OPP0': 0, 'ALL': 1})
    c = c.sort_values(['min_target_prob','total_n','k','purity_rank'], ascending=[False,False,True,True]).reset_index(drop=True)
    return c


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v, d=1): return '-' if pd.isna(v) else f'{float(v):.{d}f}'


def main():
    synthetic_tests()
    x5, coverage = ethdata.load5()
    visits, signals, session_status = collect(x5)
    if signals.empty:
        raise RuntimeError('No ETH LONG structural signals generated')
    sm = summarize(signals)
    selected = select_cohort(sm)

    visits.to_csv(OUT_VISITS, index=False)
    signals.to_csv(OUT_SIGNALS, index=False)
    sm.to_csv(OUT_STRUCT, index=False)
    selected.to_csv(OUT_SELECTED, index=False)

    if len(selected):
        top = selected.iloc[0]
        status = 'ETH_LONG_B27Q_ADAPT_STRUCTURAL_COHORT_FOUND'
        selected_txt = f"{top.transition} / K{int(top.k)} / {top.purity}"
    else:
        status = 'ETH_LONG_B27Q_ADAPT_NO_COHORT_PASS'
        selected_txt = 'NONE'
    OUT_STATUS.write_text(status + '\n')

    md = [
        '# ETH LONG B27Q-Adapt — Result', '',
        f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        'BTC B27Q structural milestone adapted to ETH LONG. No F85/F35/E20 or exit tuning is used here.', '',
        '## Structural pressure census', '',
        '| Transition | Partition | K | Purity | N | Target High break | Opp Low break | No break | Median min to terminal |',
        '|---|---|---:|---|---:|---:|---:|---:|---:|',
    ]
    for r in sm.itertuples(index=False):
        md.append(f'| {r.transition} | {r.partition} | {r.k} | {r.purity} | {r.n} | {pct(r.target_break_prob)} | {pct(r.opposite_break_prob)} | {pct(r.no_break_prob)} | {num(r.median_minutes_to_terminal)} |')
    md += ['', '## Frozen structural screen', '', f'**Status: {status}**', '', f'Selected cohort for ETH B27W-Adapt: **{selected_txt}**.']
    if len(selected):
        md += ['', '| Rank | Transition | K | Purity | Min target prob | Max opp prob | Total N |', '|---:|---|---:|---|---:|---:|---:|']
        for i, r in enumerate(selected.itertuples(index=False), start=1):
            md.append(f'| {i} | {r.transition} | {r.k} | {r.purity} | {pct(r.min_target_prob)} | {pct(r.max_opp_prob)} | {r.total_n} |')
    md += ['', 'Next milestone only if a cohort passes: ETH B27W-Adapt pre-second-touch retracement-entry discovery. No live changes.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
