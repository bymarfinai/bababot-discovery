#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_F85_F15_TRANSFER_M3_WINNER_MAE'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SURV = ROOT / f'{PFX}_SurvivalCurve.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

M2_STATUS = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Status.txt'
M2_SUM = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Summary.csv'
M2_CAND = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Candidates.csv'
M2_WIN = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Windows.csv'
EXPECTED_M2_STATUS = 'ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY'

BASE = 'https://data.binance.vision/data/futures/um'
START = pd.Timestamp('2020-01-01', tz='UTC')
END = pd.Timestamp('2026-08-26', tz='UTC')
BAR5 = pd.Timedelta(minutes=5)
EXE_DUR = pd.Timedelta(hours=6, minutes=30)
MAJOR = ('external', 'development', 'reference_validation')
DISTANCES = [i / 100 for i in range(5, 90, 5)]


def require_corrected_m2():
    if not M2_STATUS.exists():
        raise RuntimeError('corrected M2 status file missing')
    status = M2_STATUS.read_text().strip()
    if status != EXPECTED_M2_STATUS:
        raise RuntimeError(f'M3 blocked: M2 status={status!r}, expected corrected chronology')
    for p in (M2_SUM, M2_CAND, M2_WIN):
        if not p.exists():
            raise RuntimeError(f'M3 blocked: missing corrected M2 input {p.name}')


def archive_urls():
    out = []
    m = pd.Timestamp(START.year, START.month, 1, tz='UTC')
    em = pd.Timestamp(END.year, END.month, 1, tz='UTC')
    while m < em:
        ym = m.strftime('%Y-%m')
        out.append(f'{BASE}/monthly/klines/ETHUSDT/5m/ETHUSDT-5m-{ym}.zip')
        m += pd.offsets.MonthBegin(1)
    d = em
    while d < END.normalize():
        ds = d.strftime('%Y-%m-%d')
        out.append(f'{BASE}/daily/klines/ETHUSDT/5m/ETHUSDT-5m-{ds}.zip')
        d += pd.Timedelta(days=1)
    return out


def fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={'User-Agent': 'bababot-eth-m3/1.0'})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            return pd.read_csv(
                fh, header=None, usecols=[0, 1, 2, 3, 4],
                names=['ts', 'open', 'high', 'low', 'close']
            )


def load5():
    frames = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_one, u) for u in archive_urls()]
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError('no ETHUSDT 5m data')
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors='coerce')
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x['ts'] = pd.to_datetime(t, unit='ms', utc=True, errors='coerce')
    for c in ['open', 'high', 'low', 'close']:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna().drop_duplicates('ts').sort_values('ts')
    x = x[(x.ts >= START) & (x.ts < END)].set_index('ts')
    expected = int((x.index[-1] - x.index[0]) / BAR5) + 1
    coverage = len(x) / expected
    if coverage < .995:
        raise RuntimeError(f'ETH raw 5m coverage too low: {coverage:.6f}')
    return x, coverage


def sl(x, a, z):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def measure_path(q: pd.DataFrame, side: str, f: float, fill_ts: pd.Timestamp,
                 terminal_bar: pd.Timestamp | pd.NaT, outcome: str):
    after_fill = q[q.index >= fill_ts]
    if pd.notna(terminal_bar):
        through_terminal = after_fill[after_fill.index <= terminal_bar]
        pre_terminal = after_fill[after_fill.index < terminal_bar]
    else:
        through_terminal = after_fill
        pre_terminal = after_fill

    if len(pre_terminal) == 0 or len(through_terminal) == 0:
        raise AssertionError('empty adverse path after valid M2 fill')

    next_pre = pre_terminal[pre_terminal.index >= fill_ts + BAR5]

    if side == 'LONG':
        pre_frac = float(pre_terminal.low.min())
        through_frac = float(through_terminal.low.min())
        next_frac = float(next_pre.low.min()) if len(next_pre) else np.nan
        pre_req = max(0.0, f - pre_frac)
        through_req = max(0.0, f - through_frac)
        next_req = max(0.0, f - next_frac) if not pd.isna(next_frac) else np.nan
    else:
        pre_frac = float(pre_terminal.high.max())
        through_frac = float(through_terminal.high.max())
        next_frac = float(next_pre.high.max()) if len(next_pre) else np.nan
        pre_req = max(0.0, pre_frac - f)
        through_req = max(0.0, through_frac - f)
        next_req = max(0.0, next_frac - f) if not pd.isna(next_frac) else np.nan

    return {
        'pre_path_frac': pre_frac,
        'through_terminal_frac': through_frac,
        'next_bar_pre_terminal_frac': next_frac,
        'pre_required_distance': pre_req,
        'through_required_distance': through_req,
        'next_bar_required_distance': next_req,
    }


def synthetic_tests():
    idx = pd.date_range('2026-01-05', periods=3, freq='5min', tz='UTC')
    # Use fraction-space bars directly. Fill at idx[0], H2 terminal idx[2].
    longq = pd.DataFrame({
        'open': [.85, .84, .90], 'high': [.87, .88, 1.01],
        'low': [.82, .80, .70], 'close': [.84, .86, .99]
    }, index=idx)
    a = measure_path(longq, 'LONG', .85, idx[0], idx[2], 'H2')
    assert abs(a['pre_required_distance'] - .05) < 1e-12
    assert abs(a['through_required_distance'] - .15) < 1e-12
    assert not (a['through_required_distance'] < .15)  # equality touches boundary

    shortq = pd.DataFrame({
        'open': [.15, .16, .10], 'high': [.18, .20, .30],
        'low': [.13, .12, -.01], 'close': [.16, .14, .01]
    }, index=idx)
    b = measure_path(shortq, 'SHORT', .15, idx[0], idx[2], 'H2')
    assert abs(b['pre_required_distance'] - .05) < 1e-12
    assert abs(b['through_required_distance'] - .15) < 1e-12
    assert not (b['through_required_distance'] < .15)


def qtile(s: pd.Series, q: float):
    s = pd.to_numeric(s, errors='coerce').dropna()
    return float(s.quantile(q)) if len(s) else np.nan


def main():
    require_corrected_m2()
    synthetic_tests()

    sm = pd.read_csv(M2_SUM)
    pass_rows = sm[(sm.partition == 'POOLED_MAJOR') & (sm.screen == 'SCREEN_PASS')][['clock','side','level']].drop_duplicates()
    if len(pass_rows) == 0:
        raise RuntimeError('corrected M2 has no SCREEN_PASS candidates; M3 has nothing to audit')
    passers = {(str(r.clock), str(r.level)) for r in pass_rows.itertuples(index=False)}

    c = pd.read_csv(M2_CAND)
    w = pd.read_csv(M2_WIN)
    for col in ['reference_start','execution_start','fill_ts']:
        if col in c:
            c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    for col in ['reference_start','execution_start','terminal_bar','eligible_start','leave_bar','k1']:
        if col in w:
            w[col] = pd.to_datetime(w[col], utc=True, errors='coerce')

    # Corrected candidate set must be selected only from M2 screen passers.
    c = c[c.apply(lambda r: (str(r.clock), str(r.level)) in passers, axis=1)].copy()
    c = c[c.filled.astype(str).str.lower().eq('true')].copy()
    if len(c) == 0:
        raise RuntimeError('no filled corrected-M2 survivor candidates')

    keycols = ['clock','partition','reference_start']
    wm = w[keycols + ['terminal','terminal_bar']].copy()
    c = c.merge(wm, on=keycols, how='left', suffixes=('', '_window'), validate='many_to_one')
    if c.terminal_bar.isna().all() and (c.outcome != 'NO_H2').any():
        raise AssertionError('terminal timestamps missing after M2 window join')
    if not (c.outcome.astype(str) == c.terminal.astype(str)).all():
        raise AssertionError('M2 candidate/window outcome identity mismatch')

    x5, coverage = load5()
    rows = []
    for r in c.itertuples(index=False):
        es = pd.Timestamp(r.execution_start)
        q = sl(x5, es, es + EXE_DUR).copy()
        if len(q) != 78:
            raise AssertionError(f'incomplete execution session {r.clock} {es}')
        H = float(r.H); L = float(r.L); R = H - L
        if not R > 0:
            raise AssertionError('invalid frozen range')
        # Convert raw price bars into frozen range-fraction space.
        fq = pd.DataFrame(index=q.index)
        fq['open'] = (q.open - L) / R
        fq['high'] = (q.high - L) / R
        fq['low'] = (q.low - L) / R
        fq['close'] = (q.close - L) / R
        fill_ts = pd.Timestamp(r.fill_ts)
        terminal = pd.Timestamp(r.terminal_bar) if pd.notna(r.terminal_bar) else pd.NaT
        if str(r.outcome) == 'H2':
            if pd.isna(terminal) or not (fill_ts < terminal):
                raise AssertionError('H2 winner terminal must be strictly after fill')
        m = measure_path(fq, str(r.side), float(r.fraction), fill_ts, terminal, str(r.outcome))
        # M2 mae_ru used fill-through-terminal path; M3 must reproduce it.
        if pd.notna(r.mae_ru) and abs(float(r.mae_ru) - m['through_required_distance']) > 1e-9:
            raise AssertionError('M3 raw path does not reproduce corrected M2 candidate MAE')
        mins = float((terminal - fill_ts) / pd.Timedelta(minutes=1)) if str(r.outcome) == 'H2' else np.nan
        rows.append({
            'clock': r.clock, 'side': r.side, 'level': r.level, 'fraction': float(r.fraction),
            'partition': r.partition, 'reference_start': r.reference_start,
            'execution_start': es, 'fill_ts': fill_ts, 'terminal': r.outcome,
            'terminal_bar': terminal, 'minutes_to_h2': mins,
            **m,
        })

    d = pd.DataFrame(rows)
    d.to_csv(OUT_DETAIL, index=False)

    sums = []
    surv = []
    for clock, level in sorted(passers):
        for part in (*MAJOR, 'august', 'POOLED_MAJOR'):
            g = d[(d.clock == clock) & (d.level == level)]
            if part == 'POOLED_MAJOR':
                g = g[g.partition.isin(MAJOR)]
            else:
                g = g[g.partition == part]
            win = g[g.terminal == 'H2']
            fail = g[g.terminal != 'H2']
            wp90 = qtile(win.through_required_distance, .90)
            fp50 = qtile(fail.through_required_distance, .50)
            sums.append({
                'clock': clock, 'side': str(g.side.iloc[0]) if len(g) else '', 'level': level,
                'partition': part, 'fills': len(g), 'h2_winners': len(win),
                'h2_rate': len(win)/len(g) if len(g) else np.nan,
                'winner_cons_p50': qtile(win.through_required_distance,.50),
                'winner_cons_p75': qtile(win.through_required_distance,.75),
                'winner_cons_p90': wp90,
                'winner_cons_p95': qtile(win.through_required_distance,.95),
                'winner_cons_max': float(pd.to_numeric(win.through_required_distance,errors='coerce').max()) if len(win) else np.nan,
                'winner_pre_p50': qtile(win.pre_required_distance,.50),
                'winner_pre_p75': qtile(win.pre_required_distance,.75),
                'winner_pre_p90': qtile(win.pre_required_distance,.90),
                'winner_pre_p95': qtile(win.pre_required_distance,.95),
                'winner_nextbar_median': qtile(win.next_bar_required_distance,.50),
                'median_minutes_to_h2': qtile(win.minutes_to_h2,.50),
                'failures': len(fail),
                'failure_p25': qtile(fail.through_required_distance,.25),
                'failure_p50': fp50,
                'failure_p75': qtile(fail.through_required_distance,.75),
                'failure_p90': qtile(fail.through_required_distance,.90),
                'failure_p50_minus_winner_p90': fp50-wp90 if not pd.isna(fp50) and not pd.isna(wp90) else np.nan,
                'failure_touch_at_winner_p90': float((fail.through_required_distance >= wp90).mean()) if len(fail) and not pd.isna(wp90) else np.nan,
            })
            for D in DISTANCES:
                surv.append({
                    'clock': clock, 'level': level, 'partition': part, 'distance': D,
                    'winner_n': len(win),
                    'winner_conservative_survival_rate': float((win.through_required_distance < D).mean()) if len(win) else np.nan,
                    'winner_pre_h2_survival_rate': float((win.pre_required_distance < D).mean()) if len(win) else np.nan,
                    'failure_n': len(fail),
                    'failure_touch_rate': float((fail.through_required_distance >= D).mean()) if len(fail) else np.nan,
                })

    S = pd.DataFrame(sums)
    V = pd.DataFrame(surv)
    S.to_csv(OUT_SUM, index=False)
    V.to_csv(OUT_SURV, index=False)
    OUT_STATUS.write_text('ETH_M3_WINNER_MAE_AUDIT_COMPLETED\n')

    lines = [
        '# ETH F85/F15 Transfer — M3 Winner MAE / Path Audit — Result', '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.', '',
        f'Corrected M2 survivor set audited: **{len(passers)} habitat-level combinations**.', '',
        'M3 is diagnostic only: no stop selected, no TP, no PnL, no PF.', '',
        '| Habitat | Level | Fills | H2 rate | Winner P90 adverse | Winner P95 | Failure median | Separation (Fail P50 - Win P90) |',
        '|---|---|---:|---:|---:|---:|---:|---:|',
    ]
    pooled = S[S.partition == 'POOLED_MAJOR'].sort_values(['clock','level'])
    for r in pooled.itertuples(index=False):
        def n(x): return '-' if pd.isna(x) else f'{float(x):.3f}R'
        lines.append(
            f'| {r.clock} | {r.level} | {int(r.fills)} | {100*r.h2_rate:.1f}% | '
            f'{n(r.winner_cons_p90)} | {n(r.winner_cons_p95)} | {n(r.failure_p50)} | '
            f'{n(r.failure_p50_minus_winner_p90)} |'
        )
    lines += [
        '', '**Status: ETH_M3_WINNER_MAE_AUDIT_COMPLETED**', '',
        'No level or stop distance is promoted by M3. Stop here; no M4/economic testing was run automatically.'
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
