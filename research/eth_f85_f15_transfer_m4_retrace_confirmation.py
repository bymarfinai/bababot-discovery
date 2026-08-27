#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_F85_F15_TRANSFER_M4_RETRACE_CONFIRMATION'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

M2_PFX = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID'
M2_STATUS = ROOT / f'{M2_PFX}_Status.txt'
M2_SUM = ROOT / f'{M2_PFX}_Summary.csv'
M2_CAND = ROOT / f'{M2_PFX}_Candidates.csv'
M2_WIN = ROOT / f'{M2_PFX}_Windows.csv'
EXPECTED_M2 = 'ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY'

M3_PATH = Path(__file__).resolve().parent / 'eth_f85_f15_transfer_m3_winner_mae.py'
spec = importlib.util.spec_from_file_location('eth_m3_base', M3_PATH)
m3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m3)

BAR5 = pd.Timedelta(minutes=5)
EXE_DUR = pd.Timedelta(hours=6, minutes=30)
MAJOR = ('external', 'development', 'reference_validation')
DISTANCES = [i / 100 for i in range(5, 45, 5)]


def require_upstream():
    if not M2_STATUS.exists() or M2_STATUS.read_text().strip() != EXPECTED_M2:
        raise RuntimeError('M4 blocked: corrected-M2 status gate failed')
    for p in (M2_SUM, M2_CAND, M2_WIN):
        if not p.exists():
            raise RuntimeError(f'M4 blocked: missing {p.name}')


def refine_one(q: pd.DataFrame, fill_ts: pd.Timestamp, terminal_bar, outcome: str,
               H: float, L: float, f: float, D: float):
    R = H - L
    retrace_frac = f - D
    retrace_px = L + retrace_frac * R
    start = fill_ts + BAR5
    search = q[q.index >= start]
    if pd.notna(terminal_bar):
        # confirmation must complete strictly before terminal.
        search = search[search.index < terminal_bar]

    armed = False
    armed_ts = pd.NaT
    confirm_ts = pd.NaT
    entry_ts = pd.NaT
    entry_open = np.nan

    for ts, r in search.iterrows():
        if not armed and float(r.low) <= retrace_px:
            armed = True
            armed_ts = ts
        if armed and float(r.close) > retrace_px:
            confirm_ts = ts
            candidate_entry = ts + BAR5
            if candidate_entry not in q.index:
                break
            if pd.notna(terminal_bar) and candidate_entry > terminal_bar:
                break
            entry_ts = candidate_entry
            entry_open = float(q.loc[entry_ts, 'open'])
            break

    executable = pd.notna(entry_ts)
    entry_frac = (entry_open - L) / R if executable else np.nan
    h2 = bool(executable and outcome == 'H2')
    wait_min = float((entry_ts - fill_ts) / pd.Timedelta(minutes=1)) if executable else np.nan
    entry_to_h2 = (
        float((terminal_bar - entry_ts) / pd.Timedelta(minutes=1))
        if h2 and pd.notna(terminal_bar) else np.nan
    )
    return {
        'distance': D,
        'retrace_fraction': retrace_frac,
        'retrace_price': retrace_px,
        'armed': armed,
        'armed_ts': armed_ts,
        'confirmed': pd.notna(confirm_ts),
        'confirm_ts': confirm_ts,
        'executable': executable,
        'entry_ts': entry_ts,
        'entry_open': entry_open,
        'entry_fraction': entry_frac,
        'entry_improvement': f - entry_frac if executable else np.nan,
        'h2_after_entry': h2,
        'trigger_to_entry_min': wait_min,
        'entry_to_h2_min': entry_to_h2,
    }


def synthetic_tests():
    H, L, f, D = 100.0, 90.0, .90, .10
    idx = pd.date_range('2026-01-05 10:00', periods=5, freq='5min', tz='UTC')
    # Initial fill bar itself reaches deeper than D10, but cannot arm M4.
    q = pd.DataFrame([
        [99.0, 99.2, 97.5, 98.8],   # fill bar; low < retrace but forbidden
        [98.8, 99.0, 98.2, 98.5],   # no retrace to 98.0
        [98.5, 98.7, 97.9, 98.3],   # retrace + same-bar reclaim >98.0
        [98.4, 100.2, 98.3, 99.8],  # next-open entry and H2 terminal bar
        [99.8, 100.5, 99.5, 100.2],
    ], index=idx, columns=['open','high','low','close'])
    r = refine_one(q, idx[0], idx[3], 'H2', H, L, f, D)
    assert r['armed_ts'] == idx[2]
    assert r['confirm_ts'] == idx[2]
    assert r['entry_ts'] == idx[3]
    assert r['h2_after_entry']

    # A reclaim that completes only on terminal bar cannot create an entry.
    q2 = q.copy()
    q2.loc[idx[2], 'close'] = 97.95
    r2 = refine_one(q2, idx[0], idx[3], 'H2', H, L, f, D)
    assert not r2['executable']


def as_bool(s: pd.Series):
    return s.astype(str).str.lower().eq('true')


def summarize_group(g: pd.DataFrame):
    fills = len(g)
    base_h2 = int((g.outcome == 'H2').sum())
    entries = g[as_bool(g.executable)]
    entry_h2 = int((entries.outcome == 'H2').sum())
    base_fail = fills - base_h2
    failure_entries = int((entries.outcome != 'H2').sum())
    return {
        'baseline_fills': fills,
        'baseline_h2': base_h2,
        'baseline_h2_rate': base_h2 / fills if fills else np.nan,
        'armed_n': int(as_bool(g.armed).sum()),
        'armed_rate': float(as_bool(g.armed).mean()) if fills else np.nan,
        'confirmed_n': int(as_bool(g.confirmed).sum()),
        'confirmed_rate': float(as_bool(g.confirmed).mean()) if fills else np.nan,
        'entries': len(entries),
        'entry_availability': len(entries) / fills if fills else np.nan,
        'entry_h2': entry_h2,
        'entry_h2_rate': entry_h2 / len(entries) if len(entries) else np.nan,
        'h2_rate_delta': (entry_h2 / len(entries) - base_h2 / fills) if len(entries) and fills else np.nan,
        'baseline_h2_capture_rate': int((entries.outcome == 'H2').sum()) / base_h2 if base_h2 else np.nan,
        'baseline_failure_rejection_rate': 1 - failure_entries / base_fail if base_fail else np.nan,
        'median_trigger_to_entry_min': pd.to_numeric(entries.trigger_to_entry_min, errors='coerce').median() if len(entries) else np.nan,
        'median_entry_fraction': pd.to_numeric(entries.entry_fraction, errors='coerce').median() if len(entries) else np.nan,
        'median_entry_improvement': pd.to_numeric(entries.entry_improvement, errors='coerce').median() if len(entries) else np.nan,
        'median_entry_to_h2_min': pd.to_numeric(entries.loc[entries.outcome == 'H2', 'entry_to_h2_min'], errors='coerce').median() if entry_h2 else np.nan,
    }


def main():
    require_upstream()
    synthetic_tests()

    sm = pd.read_csv(M2_SUM)
    pass_rows = sm[(sm.partition == 'POOLED_MAJOR') & (sm.screen == 'SCREEN_PASS') & (sm.side == 'LONG')][['clock','level']].drop_duplicates()
    passers = {(str(r.clock), str(r.level)) for r in pass_rows.itertuples(index=False)}
    if not passers:
        raise RuntimeError('M4 has no corrected-M2 LONG SCREEN_PASS candidates')

    c = pd.read_csv(M2_CAND)
    w = pd.read_csv(M2_WIN)
    for col in ('reference_start','execution_start','fill_ts'):
        c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    for col in ('reference_start','execution_start','terminal_bar'):
        w[col] = pd.to_datetime(w[col], utc=True, errors='coerce')

    c = c[c.apply(lambda r: (str(r.clock), str(r.level)) in passers, axis=1)].copy()
    c = c[as_bool(c.filled)].copy()
    wm = w[['clock','partition','reference_start','terminal','terminal_bar']].copy()
    c = c.merge(wm, on=['clock','partition','reference_start'], how='left', validate='many_to_one')
    if not (c.outcome.astype(str) == c.terminal.astype(str)).all():
        raise AssertionError('candidate/window terminal identity mismatch')

    x5, coverage = m3.load5()
    if coverage < .995:
        raise AssertionError('coverage gate failed')

    rows = []
    for r in c.itertuples(index=False):
        es = pd.Timestamp(r.execution_start)
        q = m3.sl(x5, es, es + EXE_DUR)
        if len(q) != 78:
            raise AssertionError(f'incomplete execution session {r.clock} {es}')
        fill_ts = pd.Timestamp(r.fill_ts)
        terminal_bar = pd.Timestamp(r.terminal_bar) if pd.notna(r.terminal_bar) else pd.NaT
        for D in DISTANCES:
            z = refine_one(q, fill_ts, terminal_bar, str(r.outcome), float(r.H), float(r.L), float(r.fraction), D)
            rows.append({
                'clock': r.clock, 'level': r.level, 'partition': r.partition,
                'reference_start': r.reference_start, 'execution_start': es,
                'H': float(r.H), 'L': float(r.L), 'trigger_fraction': float(r.fraction),
                'fill_ts': fill_ts, 'outcome': str(r.outcome), 'terminal_bar': terminal_bar,
                **z,
            })

    D = pd.DataFrame(rows)
    D.to_csv(OUT_DETAIL, index=False)

    sums = []
    for clock, level in sorted(passers):
        for dist in DISTANCES:
            base = D[(D.clock == clock) & (D.level == level) & (D.distance == dist)]
            for part in (*MAJOR, 'august', 'POOLED_MAJOR'):
                g = base[base.partition.isin(MAJOR)] if part == 'POOLED_MAJOR' else base[base.partition == part]
                sums.append({'clock': clock, 'level': level, 'distance': dist, 'partition': part, **summarize_group(g)})

    S = pd.DataFrame(sums)
    S['screen'] = ''
    pass_depths = []
    for clock, level in sorted(passers):
        for dist in DISTANCES:
            pool = S[(S.clock == clock) & (S.level == level) & (S.distance == dist) & (S.partition == 'POOLED_MAJOR')].iloc[0]
            ok = (
                int(pool.entries) > 0 and
                float(pool.entry_availability) >= .40 and
                float(pool.entry_h2_rate) >= .75 and
                float(pool.h2_rate_delta) >= .03
            )
            for part in MAJOR:
                r = S[(S.clock == clock) & (S.level == level) & (S.distance == dist) & (S.partition == part)].iloc[0]
                ok = ok and int(r.entries) >= 20
                if int(r.entries) > 0:
                    ok = ok and float(r.entry_h2_rate) >= float(r.baseline_h2_rate) - .05
                else:
                    ok = False
            if ok:
                pass_depths.append((clock, level, dist))
                S.loc[(S.clock == clock) & (S.level == level) & (S.distance == dist) & (S.partition == 'POOLED_MAJOR'), 'screen'] = 'SCREEN_PASS'

    S.to_csv(OUT_SUM, index=False)
    OUT_STATUS.write_text('ETH_M4_RETRACE_CONFIRMATION_COMPLETED\n')

    lines = [
        '# ETH F85/F15 Transfer — M4 Retrace + Confirmation — Result', '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.', '',
        f'Corrected-M2 LONG survivor universe: **{len(passers)} habitat-level combinations**.', '',
        'Rule: trigger fill -> deeper retrace -> completed 5m reclaim -> next 5m open.', '',
        '| Habitat | Trigger | Passing retraces | Best passing H2 / entries / delta |',
        '|---|---|---|---|',
    ]
    for clock, level in sorted(passers):
        pp = [d for c,l,d in pass_depths if c == clock and l == level]
        if pp:
            cand = S[(S.clock == clock) & (S.level == level) & (S.distance.isin(pp)) & (S.partition == 'POOLED_MAJOR')].copy()
            cand = cand.sort_values(['entry_h2_rate','entries','distance'], ascending=[False,False,True])
            b = cand.iloc[0]
            desc = ', '.join(f'D{int(x*100):02d}' for x in pp)
            best = f"D{int(b.distance*100):02d}: {100*b.entry_h2_rate:.1f}% / {int(b.entries)} / {100*b.h2_rate_delta:+.1f}pp"
        else:
            desc = 'NONE'; best = '-'
        lines.append(f'| {clock} | {level} | {desc} | {best} |')
    lines += ['', '**Status: ETH_M4_RETRACE_CONFIRMATION_COMPLETED**', '',
              'No stop, TP, PnL, PF, leverage, or M5 was run. Stop after M4.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
