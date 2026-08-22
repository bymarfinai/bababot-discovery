#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_post_h2_f05_f10_f15_mae_b27bb as b27bb

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_EQUAL_DISTANCE_STOP_B27BC_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_EQUAL_DISTANCE_STOP_B27BC_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_EQUAL_DISTANCE_STOP_B27BC_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_EQUAL_DISTANCE_STOP_B27BC_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
CANDS = {'F05':0.05,'F10':0.10,'F15':0.15}
DISTS = {'D30':0.30,'D40':0.40,'D50':0.50}
EXT = 0.20
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


def session_open(x5: pd.DataFrame, end: pd.Timestamp) -> float:
    p = int(x5.index.searchsorted(end, side='left'))
    if p >= len(x5) or x5.index[p] != end:
        raise AssertionError('missing exact session-end open')
    return float(x5.iloc[p].open)


def hard_stop_hybrid(x5: pd.DataFrame, r: pd.Series, dist_name: str, dist: float) -> dict:
    zone = str(r.zone)
    ef = float(r.entry_frac)
    H = float(r.H); L = float(r.L); R = H - L
    entry = float(r.entry_px)
    start = pd.Timestamp(r.fill_bar_start)
    end = pd.Timestamp(r.session_end)
    stop = entry + dist * R
    milestone = L - EXT * R

    assert H > L and R > 0
    assert abs(entry - (L + ef*R)) < 1e-9 * max(1.0, abs(entry))
    assert abs(stop - (entry + dist*R)) < 1e-12 * max(1.0, abs(stop))
    assert abs(milestone - (L - EXT*R)) < 1e-12 * max(1.0, abs(milestone))

    q = b27ad.fast_slice(x5, start, end)
    if q.empty or q.index[0] != start:
        raise AssertionError('missing fill bar')
    highs = q.high.astype(float).to_numpy()

    reached = False
    active = False
    ceiling = np.nan
    ratchets = 0
    activation_bar = pd.NaT
    exit_bar = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None

    for i, (ts, b) in enumerate(q.iterrows()):
        o = float(b.open); h = float(b.high); lo = float(b.low)

        if active:
            # Exact post-activation hybrid behavior: gap/open first, then resting ceiling.
            if o >= ceiling:
                exit_bar = ts; exit_ts = ts; exit_px = o
                reason = 'PROFIT_CEILING_GAP_OPEN'
                break
            if h >= ceiling:
                exit_bar = ts; exit_ts = ts; exit_px = ceiling
                reason = 'PROFIT_CEILING_HIT'
                break

        pivot = np.nan
        if i >= 2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
            pivot = float(highs[i-1])

        if not reached:
            # Resting hard stop is active from the fill bar. Conservative OHLC rule:
            # if stop and E20 are both in the same bar, stop wins because intrabar
            # ordering cannot be known from 5m OHLC.
            if o >= stop:
                exit_bar = ts; exit_ts = ts; exit_px = o
                reason = 'PRE_ACT_HARD_STOP_GAP_OPEN'
                break
            if h >= stop - EPS:
                exit_bar = ts; exit_ts = ts; exit_px = stop
                reason = 'PRE_ACT_HARD_STOP_TOUCH'
                break
            # Fill bar cannot activate E20; activation begins from a later raw 5m bar.
            if i > 0 and lo <= milestone + EPS:
                reached = True
                active = True
                activation_bar = ts
                ceiling = milestone
                if np.isfinite(pivot) and pivot < ceiling:
                    ceiling = pivot
                    ratchets += 1
                continue
        else:
            if np.isfinite(pivot) and pivot < ceiling:
                old = ceiling
                ceiling = pivot
                ratchets += 1
                assert ceiling <= old + EPS

    if reason is None:
        exit_bar = end
        exit_ts = end
        exit_px = session_open(x5, end)
        reason = 'TIME_EXIT_SESSION_END'

    gross = 1.0 - float(exit_px) / entry
    net = gross * NOTIONAL - FEE

    return {
        'zone': zone, 'entry_frac': ef, 'distance': dist_name, 'distance_r': dist,
        'partition': r.partition, 'date_utc': r.date_utc, 'signal_ts': r.signal_ts,
        'fill_bar_start': start, 'entry_px': entry, 'H': H, 'L': L, 'range': R,
        'stop_px': stop, 'E20_DOWN': milestone, 'session_end': end,
        'activated': bool(reached), 'activation_bar_start': activation_bar,
        'ratchets': int(ratchets), 'final_ceiling': float(ceiling) if active else np.nan,
        'exit_bar_start': exit_bar, 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'exit_reason': reason, 'net_pnl_usd': net, 'win': bool(net > 0),
    }


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for zone in CANDS:
        for dn in DISTS:
            for part in (*PARTS, 'POOLED_MAJOR'):
                if part == 'POOLED_MAJOR':
                    g = tr[(tr.zone == zone) & (tr.distance == dn) & tr.partition.isin(MAJOR)].copy()
                else:
                    g = tr[(tr.zone == zone) & (tr.distance == dn) & (tr.partition == part)].copy()
                vals = pd.to_numeric(g.net_pnl_usd, errors='coerce')
                rows.append({
                    'zone': zone, 'distance': dn, 'distance_r': DISTS[dn], 'partition': part,
                    'n': len(g),
                    'activation_n': int(g.activated.sum()) if len(g) else 0,
                    'activation_rate': float(g.activated.mean()) if len(g) else np.nan,
                    'wr': float((vals > 0).mean()) if len(g) else np.nan,
                    'pf': pf(vals),
                    'expectancy': float(vals.mean()) if len(g) else np.nan,
                    'total_pnl': float(vals.sum()) if len(g) else 0.0,
                    'hard_stop_touch': int((g.exit_reason == 'PRE_ACT_HARD_STOP_TOUCH').sum()) if len(g) else 0,
                    'hard_stop_gap': int((g.exit_reason == 'PRE_ACT_HARD_STOP_GAP_OPEN').sum()) if len(g) else 0,
                    'ceiling_hits': int((g.exit_reason == 'PROFIT_CEILING_HIT').sum()) if len(g) else 0,
                    'gap_exits': int((g.exit_reason == 'PROFIT_CEILING_GAP_OPEN').sum()) if len(g) else 0,
                    'time_exits': int((g.exit_reason == 'TIME_EXIT_SESSION_END').sum()) if len(g) else 0,
                })
    return pd.DataFrame(rows)


def synthetic_test() -> None:
    # Conservative same-bar ambiguity: hard stop wins over E20 when both are in the bar.
    idx = pd.date_range('2026-01-05 14:00', periods=5, freq='5min', tz='UTC')
    x = pd.DataFrame([
        {'open':90.5,'high':91.0,'low':90.4,'close':90.7},
        {'open':90.7,'high':94.0,'low':87.5,'close':88.0},
        {'open':88.0,'high':88.5,'low':87.0,'close':87.5},
        {'open':87.5,'high':88.0,'low':86.8,'close':87.0},
        {'open':87.0,'high':87.5,'low':86.5,'close':86.9},
    ], index=idx)
    r = pd.Series({'zone':'F05','entry_frac':.05,'partition':'x','date_utc':'2026-01-05',
        'signal_ts':idx[0]-BAR5,'fill_bar_start':idx[0],'entry_px':90.5,
        'H':100.0,'L':90.0,'session_end':idx[-1]+BAR5})
    z = hard_stop_hybrid(x, r, 'D30', .30)
    assert z['exit_reason'] == 'PRE_ACT_HARD_STOP_TOUCH'
    assert abs(float(z['exit_px']) - 93.5) < 1e-12


def main() -> None:
    synthetic_test()
    x5, coverage = b27ad.b21.load5()
    assert len(x5) == 698112 and abs(float(coverage)-1.0) < 1e-12

    clean = b27bb.load_clean()
    fills = b27bb.build_fills(x5, clean)

    # Mandatory B27AZ fill identity assertions.
    exp_pool = {'F05':28,'F10':37,'F15':42}
    for zone, n in exp_pool.items():
        got = len(fills[(fills.zone == zone) & fills.partition.isin(MAJOR)])
        assert got == n, (zone, got, n)

    # Mandatory B27BB stop-independent raw E20 reach assertions.
    paths = pd.DataFrame([b27bb.path_one(x5, r) for _, r in fills.iterrows()])
    exp_raw = {'F05':17,'F10':22,'F15':24}
    for zone, n in exp_raw.items():
        got = int(paths[(paths.zone == zone) & paths.partition.isin(MAJOR)].e20_reached.sum())
        assert got == n, (zone, 'raw_e20', got, n)

    rows = []
    for _, r in fills.iterrows():
        for dn, d in DISTS.items():
            rows.append(hard_stop_hybrid(x5, r, dn, d))
    tr = pd.DataFrame(rows)
    sm = summarize(tr)

    eligible = []
    for zone in CANDS:
        for dn in DISTS:
            ok = True
            for part in MAJOR:
                rr = sm[(sm.zone == zone) & (sm.distance == dn) & (sm.partition == part)].iloc[0]
                ok = ok and int(rr.n) > 0 and float(rr.expectancy) >= 0 and float(rr.pf) >= 1.0
            if ok:
                eligible.append(f'{zone}/{dn}')

    pool = sm[sm.partition == 'POOLED_MAJOR'].copy()
    pool['candidate'] = pool.zone.astype(str) + '/' + pool.distance.astype(str)
    pool = pool.sort_values(['total_pnl','pf'], ascending=[False,False])
    diagnostic_best = str(pool.iloc[0].candidate)
    selected = 'NONE'
    if eligible:
        selected = str(pool[pool.candidate.isin(eligible)].iloc[0].candidate)

    status = f'B27BC_SELECTED_{selected.replace("/","_")}__DIAGNOSTIC_BEST_{diagnostic_best.replace("/","_")}'
    tr.to_csv(OUT_TRADES, index=False)
    sm.to_csv(OUT_SUM, index=False)
    OUT_STATUS.write_text(status + '\n')

    def pct(v):
        return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
    def num(v):
        if pd.isna(v): return '-'
        if math.isinf(float(v)): return 'inf'
        return f'{float(v):.3f}'

    lines = [
        '# B27BC — BTC London->NY SHORT Post-Retest#2 Equal-Distance Hard-Stop Economics — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AZ fill identities and B27BB stop-independent raw E20 reach counts reproduced before the 9-candidate economics grid was interpreted.','',
        'Hard stop is resting/intrabar from the fill bar; same-bar stop-vs-E20 ambiguity is resolved stop-first conservatively.','',
        '| Zone | D | Partition | N | E20 act | E20 rate | WR | PF | Exp/trade $ | Total $ | Stop touch | Stop gap | Ceiling | Hybrid gap | Time |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for zone in CANDS:
        for dn in DISTS:
            for part in (*PARTS, 'POOLED_MAJOR'):
                r = sm[(sm.zone == zone) & (sm.distance == dn) & (sm.partition == part)].iloc[0]
                lines.append(
                    f'| {zone} | {dn} | {part} | {int(r.n)} | {int(r.activation_n)} | {pct(r.activation_rate)} | '
                    f'{pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | '
                    f'{int(r.hard_stop_touch)} | {int(r.hard_stop_gap)} | {int(r.ceiling_hits)} | {int(r.gap_exits)} | {int(r.time_exits)} |'
                )
    lines += ['', '## Frozen selection', '',
        f'Formally eligible candidates: **{", ".join(eligible) if eligible else "NONE"}**.',
        f'Selected candidate: **{selected}**.',
        f'Highest pooled-PnL diagnostic candidate: **{diagnostic_best}**.', '',
        'No intermediate entry fraction, stop distance, activation milestone, regime, confirmation, candle rule, or runner parameter was searched.',
        'Research only; live BBC unchanged.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
