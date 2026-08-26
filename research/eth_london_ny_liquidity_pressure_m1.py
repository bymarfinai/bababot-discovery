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
PFX = 'ETH_LONDON_NY_LIQUIDITY_PRESSURE_M1'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_VISITS = ROOT / f'{PFX}_Visits.csv'
OUT_SIGNALS = ROOT / f'{PFX}_Signals.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BASE = 'https://data.binance.vision/data/futures/um'
START = pd.Timestamp('2020-01-01T00:00:00Z')
END = pd.Timestamp('2026-08-26T00:00:00Z')
BAR5 = pd.Timedelta(minutes=5)
LONDON_START_MIN = 8 * 60
LONDON_END_MIN = 13 * 60 + 30
NY_END_MIN = 20 * 60

PARTS = {
    'external': (pd.Timestamp('2020-01-01', tz='UTC'), pd.Timestamp('2022-01-01', tz='UTC')),
    'development': (pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')),
    'reference_validation': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-07-30', tz='UTC')),
    'august': (pd.Timestamp('2026-08-01', tz='UTC'), END),
}
MAJOR = ('external', 'development', 'reference_validation')


def urls(symbol: str):
    out = []
    m = pd.Timestamp(START.year, START.month, 1, tz='UTC')
    em = pd.Timestamp(END.year, END.month, 1, tz='UTC')
    while m < em:
        ym = m.strftime('%Y-%m')
        out.append(f'{BASE}/monthly/klines/{symbol}/5m/{symbol}-5m-{ym}.zip')
        m += pd.offsets.MonthBegin(1)
    d = em
    while d < END.normalize():
        ds = d.strftime('%Y-%m-%d')
        out.append(f'{BASE}/daily/klines/{symbol}/5m/{symbol}-5m-{ds}.zip')
        d += pd.Timedelta(days=1)
    return out


def fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={'User-Agent': 'bababot-eth-london-ny-m1/1.0'})
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


def load5(symbol: str):
    frames = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch_one, u) for u in urls(symbol)]
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError(f'no {symbol} 5m data')
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x.ts, errors='coerce')
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x['ts'] = pd.to_datetime(t, unit='ms', utc=True, errors='coerce')
    for c in ['open', 'high', 'low', 'close']:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna().drop_duplicates('ts').sort_values('ts')
    x = x[(x.ts >= START) & (x.ts < END)].set_index('ts')
    idx = x.index
    expected = int((idx[-1] - idx[0]) / BAR5) + 1
    coverage = len(x) / expected
    if coverage < .995:
        raise RuntimeError(f'{symbol} 5m coverage too low: {coverage:.6f}')
    return x, coverage


def fast_slice(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def partition_for(ts: pd.Timestamp):
    for name, (a, z) in PARTS.items():
        if a <= ts < z:
            return name
    return None


def analyze_session(symbol: str, part: str, day: pd.Timestamp, london: pd.DataFrame, ny: pd.DataFrame):
    H = float(london.high.max()); L = float(london.low.min())
    if not H > L:
        raise AssertionError('invalid London range')

    hi_touching = False
    lo_touching = False
    hi_visits = 0
    lo_visits = 0
    visit_rows = []
    signal = None
    terminal = 'NO_BREAK'
    terminal_ts = pd.NaT
    target_minutes = np.nan

    for ts, r in ny.iterrows():
        hi = float(r.high); lo = float(r.low); cl = float(r.close)

        # B27Q semantics: strict breakout evaluated BEFORE touch counting.
        if cl > H:
            terminal = 'TARGET_BREAK' if signal is not None else 'BULL_BREAK_BEFORE_SIGNAL'
            terminal_ts = ts + BAR5
            if signal is not None:
                target_minutes = float((terminal_ts - signal['signal_ts']) / pd.Timedelta(minutes=1))
            break
        if cl < L:
            terminal = 'OPPOSITE_BREAK' if signal is not None else 'BEAR_BREAK_BEFORE_SIGNAL'
            terminal_ts = ts + BAR5
            break

        hit_hi = hi >= H and cl <= H
        hit_lo = lo <= L and cl >= L
        if hit_hi and hit_lo:
            terminal = 'AMBIGUOUS_BOTH_LEVELS'
            terminal_ts = ts + BAR5
            break

        if hit_hi and not hi_touching:
            hi_visits += 1
            visit_rows.append({
                'symbol': symbol, 'partition': part, 'date_utc': str(day.date()),
                'level': 'HIGH', 'visit_ordinal': hi_visits,
                'bar_start': ts, 'visit_signal_ts': ts + BAR5,
                'H': H, 'L': L,
                'opposite_visits_known': lo_visits,
            })
            if signal is None and hi_visits == 1 and lo_visits == 0:
                signal = {
                    'symbol': symbol, 'partition': part, 'date_utc': str(day.date()),
                    'signal_bar_start': ts, 'signal_ts': ts + BAR5,
                    'H': H, 'L': L, 'range': H - L,
                    'hi_visits_at_signal': hi_visits,
                    'opp_visits_at_signal': lo_visits,
                }

        if hit_lo and not lo_touching:
            lo_visits += 1
            visit_rows.append({
                'symbol': symbol, 'partition': part, 'date_utc': str(day.date()),
                'level': 'LOW', 'visit_ordinal': lo_visits,
                'bar_start': ts, 'visit_signal_ts': ts + BAR5,
                'H': H, 'L': L,
                'opposite_visits_known': hi_visits,
            })

        hi_touching = bool(hit_hi)
        lo_touching = bool(hit_lo)

    if signal is None:
        return visit_rows, None

    hi_after_signal = sum(
        1 for v in visit_rows
        if v['level'] == 'HIGH' and v['visit_signal_ts'] > signal['signal_ts']
    )
    signal.update({
        'terminal': terminal if terminal in ('TARGET_BREAK', 'OPPOSITE_BREAK', 'NO_BREAK') else terminal,
        'terminal_ts': terminal_ts,
        'minutes_to_target_break': target_minutes,
        'final_high_visits_known': hi_visits,
        'final_low_visits_known': lo_visits,
        'reached_k2': hi_visits >= 2,
        'reached_k3': hi_visits >= 3,
        'high_visits_after_signal': hi_after_signal,
    })
    return visit_rows, signal


def run_symbol(symbol: str, x5: pd.DataFrame):
    visits = []
    signals = []
    anchors = pd.date_range(START.normalize(), END.normalize(), freq='D', tz='UTC')
    complete_sessions = {p: 0 for p in PARTS}

    for day in anchors:
        if day.weekday() >= 5:
            continue
        ls = day + pd.Timedelta(minutes=LONDON_START_MIN)
        le = day + pd.Timedelta(minutes=LONDON_END_MIN)
        ne = day + pd.Timedelta(minutes=NY_END_MIN)
        part = partition_for(le)
        if part is None or ne > END:
            continue
        london = fast_slice(x5, ls, le)
        ny = fast_slice(x5, le, ne)
        if len(london) != 66 or len(ny) != 78:
            continue
        complete_sessions[part] += 1
        v, s = analyze_session(symbol, part, day, london, ny)
        visits.extend(v)
        if s is not None:
            signals.append(s)

    return pd.DataFrame(visits), pd.DataFrame(signals), complete_sessions


def synthetic_tests():
    H, L = 100.0, 90.0
    idx = pd.date_range('2026-01-05 13:30', periods=8, freq='5min', tz='UTC')
    london_idx = pd.date_range('2026-01-05 08:00', periods=66, freq='5min', tz='UTC')
    london = pd.DataFrame({'open':95,'high':99,'low':91,'close':95}, index=london_idx)
    london.iloc[10, london.columns.get_loc('high')] = H
    london.iloc[20, london.columns.get_loc('low')] = L

    # K1 spans two bars, leaves, K2 occurs, then strict target breakout.
    ny = pd.DataFrame([
        [99,100.2,98,99.5],
        [99.5,100.1,98.5,99.2],
        [99.2,99.6,97,98],
        [98,100.1,97.5,99.8],
        [99.8,99.9,98,99],
        [99,101,98.5,100.5],
        [100.5,101,100,100.7],
        [100.7,101,100,100.8],
    ], index=idx, columns=['open','high','low','close'])
    v, s = analyze_session('X','x',pd.Timestamp('2026-01-05',tz='UTC'),london,ny)
    assert s is not None and s['opp_visits_at_signal'] == 0
    assert sum(1 for z in v if z['level']=='HIGH') == 2
    assert s['terminal'] == 'TARGET_BREAK' and s['reached_k2']

    # Opposite Low visit first means later High K1 is not OPP0.
    ny2 = ny.copy()
    ny2.iloc[0] = [92,93,89.8,90.5]
    ny2.iloc[1] = [90.5,91,90.1,90.8]
    ny2.iloc[2] = [99,100.2,98,99.5]
    _, s2 = analyze_session('X','x',pd.Timestamp('2026-01-05',tz='UTC'),london,ny2)
    assert s2 is None

    # Strict breakout bar must not become a touch signal.
    ny3 = ny.copy()
    ny3.iloc[0] = [99,101,98,100.2]
    _, s3 = analyze_session('X','x',pd.Timestamp('2026-01-05',tz='UTC'),london,ny3)
    assert s3 is None

    # Both-level bar is ambiguous and cannot signal.
    ny4 = ny.copy()
    ny4.iloc[0] = [95,100.2,89.8,95]
    _, s4 = analyze_session('X','x',pd.Timestamp('2026-01-05',tz='UTC'),london,ny4)
    assert s4 is None


def summarize(signals: pd.DataFrame, sessions: dict, symbol: str):
    rows = []
    for part in (*PARTS.keys(), 'POOLED_MAJOR'):
        if part == 'POOLED_MAJOR':
            q = signals[signals.partition.isin(MAJOR)].copy()
            n_sessions = sum(sessions[p] for p in MAJOR)
        else:
            q = signals[signals.partition == part].copy()
            n_sessions = sessions.get(part, 0)
        t = int((q.terminal == 'TARGET_BREAK').sum()) if len(q) else 0
        o = int((q.terminal == 'OPPOSITE_BREAK').sum()) if len(q) else 0
        nb = int((q.terminal == 'NO_BREAK').sum()) if len(q) else 0
        rows.append({
            'symbol': symbol,
            'partition': part,
            'complete_sessions': n_sessions,
            'k1_opp0_signals': len(q),
            'k1_rate': len(q)/n_sessions if n_sessions else np.nan,
            'target_break': t,
            'opposite_break': o,
            'no_break': nb,
            'target_break_rate': t/len(q) if len(q) else np.nan,
            'opposite_break_rate': o/len(q) if len(q) else np.nan,
            'no_break_rate': nb/len(q) if len(q) else np.nan,
            'resolved_same_side_wr': t/(t+o) if t+o else np.nan,
            'median_minutes_to_target': pd.to_numeric(q.loc[q.terminal=='TARGET_BREAK','minutes_to_target_break'], errors='coerce').median() if t else np.nan,
            'k2_rate': q.reached_k2.astype(bool).mean() if len(q) else np.nan,
            'k3_rate': q.reached_k3.astype(bool).mean() if len(q) else np.nan,
        })
    return pd.DataFrame(rows)


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    synthetic_tests()

    data = {}; coverage = {}; all_visits = []; all_signals = []; sums = []
    for symbol in ('BTCUSDT','ETHUSDT'):
        data[symbol], coverage[symbol] = load5(symbol)
        v, s, sess = run_symbol(symbol, data[symbol])
        if len(v): all_visits.append(v)
        if len(s): all_signals.append(s)
        sums.append(summarize(s, sess, symbol))

    visits = pd.concat(all_visits, ignore_index=True) if all_visits else pd.DataFrame()
    signals = pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()
    summary = pd.concat(sums, ignore_index=True)
    visits.to_csv(OUT_VISITS, index=False)
    signals.to_csv(OUT_SIGNALS, index=False)

    eth = summary[(summary.symbol=='ETHUSDT') & (summary.partition=='POOLED_MAJOR')].iloc[0]
    btc = summary[(summary.symbol=='BTCUSDT') & (summary.partition=='POOLED_MAJOR')].iloc[0]
    parts_ok = True
    for p in MAJOR:
        r = summary[(summary.symbol=='ETHUSDT') & (summary.partition==p)].iloc[0]
        parts_ok = parts_ok and int(r.target_break) > int(r.opposite_break)

    gate = (
        int(eth.k1_opp0_signals) >= 100 and
        float(eth.target_break_rate) >= .50 and
        float(eth.resolved_same_side_wr) >= .65 and
        float(eth.target_break_rate) >= float(btc.target_break_rate) - .10 and
        parts_ok
    )
    status = 'ETH_LONDON_NY_M1_LIQUIDITY_PRESSURE_SUPPORTED' if gate else 'ETH_LONDON_NY_M1_LIQUIDITY_PRESSURE_NOT_SUPPORTED'
    summary['m1_gate'] = ''
    summary.loc[(summary.symbol=='ETHUSDT') & (summary.partition=='POOLED_MAJOR'),'m1_gate'] = 'PASS' if gate else 'FAIL'
    summary.to_csv(OUT_SUMMARY, index=False)
    OUT_STATUS.write_text(status+'\n')

    lines = [
        '# ETH London -> New York Liquidity Pressure — M1 Result','',
        f'Raw 5m coverage: BTC **{coverage["BTCUSDT"]:.4%}**, ETH **{coverage["ETHUSDT"]:.4%}**.','',
        'Scope: London 08:00-13:30 UTC -> New York 13:30-20:00 UTC, LONG K1 OPP0 only. No F-levels, no entry, no economics.','',
        '## ETH by partition','',
        '| Partition | Sessions | K1 OPP0 | Target | Opposite | No break | Target rate | Resolved same-side | K2 rate | K3 rate |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for p in (*PARTS.keys(),'POOLED_MAJOR'):
        r = summary[(summary.symbol=='ETHUSDT') & (summary.partition==p)].iloc[0]
        lines.append(f'| {p} | {int(r.complete_sessions)} | {int(r.k1_opp0_signals)} | {int(r.target_break)} | {int(r.opposite_break)} | {int(r.no_break)} | {pct(r.target_break_rate)} | {pct(r.resolved_same_side_wr)} | {pct(r.k2_rate)} | {pct(r.k3_rate)} |')
    lines += [
        '', '## Pooled-major BTC control','',
        f'- BTC K1 OPP0: **{int(btc.k1_opp0_signals)}**',
        f'- BTC target-break rate: **{pct(btc.target_break_rate)}**',
        f'- BTC resolved same-side rate: **{pct(btc.resolved_same_side_wr)}**',
        '', f'**Status: {status}**','',
        'Per preregistration, stop here. Do not run the B27W-style pre-H2 F95/F90/F85/F80/F75 grid automatically.'
    ]
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
