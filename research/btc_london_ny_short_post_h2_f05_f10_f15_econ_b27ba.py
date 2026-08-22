#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_post_h2_retrace_zone_b27az as b27az

ROOT = Path(__file__).resolve().parent.parent
WINS = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Windows.csv'
AY_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Summary.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_ECON_B27BA_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_ECON_B27BA_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_ECON_B27BA_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_ECON_B27BA_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
CANDS = {'F05':0.05,'F10':0.10,'F15':0.15}
STOP_F = 0.65
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


def hybrid_general(x5: pd.DataFrame, r: pd.Series, zone: str, entry_frac: float) -> dict:
    H = float(r.H); L = float(r.L); R = H - L
    entry = float(r.entry_px); start = pd.Timestamp(r.fill_bar_start); end = pd.Timestamp(r.session_end)
    f65 = L + STOP_F * R
    milestone = L - EXT * R
    assert H > L
    assert abs(entry - (L + entry_frac * R)) < 1e-9 * max(1.0, abs(entry))
    assert abs(milestone - (L - EXT * R)) < 1e-12 * max(1.0, abs(milestone))
    assert entry < f65

    q = b27ad.fast_slice(x5, start, end)
    if q.empty or q.index[0] != start:
        raise AssertionError('missing entry bar')
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
        o = float(b.open); h = float(b.high); lo = float(b.low); c = float(b.close)

        if active:
            if o >= ceiling:
                exit_bar = ts; exit_ts = ts; exit_px = o; reason = 'PROFIT_CEILING_GAP_OPEN'; break
            if h >= ceiling:
                exit_bar = ts; exit_ts = ts; exit_px = ceiling; reason = 'PROFIT_CEILING_HIT'; break

        pivot = np.nan
        if i >= 2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
            pivot = float(highs[i-1])

        if not reached:
            # Exact B27AT chronology: fill bar cannot activate; later milestone touch
            # precedes a same-bar later completed-close invalidation.
            if i > 0 and lo <= milestone + EPS:
                reached = True
                active = True
                activation_bar = ts
                ceiling = milestone
                if np.isfinite(pivot) and pivot < ceiling:
                    ceiling = pivot
                    ratchets += 1
                continue
            if c > f65:
                exit_bar = ts; exit_ts = ts + BAR5; exit_px = c
                reason = 'PRE_ACT_CLOSE_INVALIDATION_F65'
                break
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

    trough_ext = np.nan; exit_ext = np.nan; capture = np.nan; giveback = np.nan
    if reached:
        aq = b27ad.fast_slice(x5, pd.Timestamp(activation_bar), end)
        trough = float(aq.low.min()) if len(aq) else np.nan
        if np.isfinite(trough):
            trough_ext = (L - trough) / R
            exit_ext = (L - float(exit_px)) / R
            denom = max(0.0, L - trough)
            capture = max(0.0, L - float(exit_px)) / denom if denom > 0 else np.nan
            giveback = trough_ext - exit_ext

    return {
        'zone': zone, 'entry_frac': entry_frac,
        'partition': r.partition, 'date_utc': r.date_utc, 'signal_ts': r.signal_ts,
        'entry_start': start, 'entry_px': entry,
        'H': H, 'L': L, 'range': R, 'F65': f65, 'E20_DOWN': milestone,
        'session_end': end, 'activated': bool(reached), 'activation_bar_start': activation_bar,
        'ratchets': int(ratchets), 'final_ceiling': float(ceiling) if active else np.nan,
        'exit_bar_start': exit_bar, 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'exit_reason': reason, 'net_pnl_usd': net, 'win': bool(net > 0),
        'trough_extension_r': trough_ext, 'realized_exit_extension_r': exit_ext,
        'capture_ratio': capture, 'giveback_r': giveback,
    }


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for zone in CANDS:
        for part in (*PARTS, 'POOLED_MAJOR'):
            if part == 'POOLED_MAJOR':
                g = tr[(tr.zone == zone) & tr.partition.isin(MAJOR)].copy()
            else:
                g = tr[(tr.zone == zone) & (tr.partition == part)].copy()
            vals = pd.to_numeric(g.net_pnl_usd, errors='coerce')
            a = g[g.activated.astype(bool)]
            rows.append({
                'zone': zone, 'partition': part, 'n': len(g),
                'activation_n': int(g.activated.sum()) if len(g) else 0,
                'activation_rate': float(g.activated.mean()) if len(g) else np.nan,
                'wr': float((vals > 0).mean()) if len(g) else np.nan,
                'pf': pf(vals),
                'expectancy': float(vals.mean()) if len(g) else np.nan,
                'total_pnl': float(vals.sum()) if len(g) else 0.0,
                'pre_invalidations': int((g.exit_reason == 'PRE_ACT_CLOSE_INVALIDATION_F65').sum()) if len(g) else 0,
                'ceiling_hits': int((g.exit_reason == 'PROFIT_CEILING_HIT').sum()) if len(g) else 0,
                'gap_exits': int((g.exit_reason == 'PROFIT_CEILING_GAP_OPEN').sum()) if len(g) else 0,
                'time_exits': int((g.exit_reason == 'TIME_EXIT_SESSION_END').sum()) if len(g) else 0,
                'median_ratchets': float(a.ratchets.median()) if len(a) else np.nan,
                'median_capture': float(a.capture_ratio.median()) if len(a) else np.nan,
                'median_giveback': float(a.giveback_r.median()) if len(a) else np.nan,
            })
    return pd.DataFrame(rows)


def synthetic_test() -> None:
    idx = pd.date_range('2026-01-05 14:00', periods=7, freq='5min', tz='UTC')
    x = pd.DataFrame([
        {'open':91.0,'high':91.2,'low':90.4,'close':91.0},
        {'open':91.0,'high':91.4,'low':87.8,'close':88.5},
        {'open':88.5,'high':88.8,'low':87.0,'close':87.5},
        {'open':87.5,'high':88.0,'low':86.5,'close':87.0},
        {'open':87.0,'high':89.2,'low':86.8,'close':88.5},
        {'open':88.5,'high':88.8,'low':87.5,'close':88.0},
        {'open':88.0,'high':88.2,'low':87.5,'close':87.8},
    ], index=idx)
    r = pd.Series({'partition':'x','date_utc':'2026-01-05','signal_ts':idx[0]-BAR5,
                   'fill_bar_start':idx[0],'entry_px':91.0,'H':100.0,'L':90.0,'session_end':idx[6]})
    z = hybrid_general(x, r, 'F10', 0.10)
    assert z['activated'] and z['net_pnl_usd'] > 0


def main() -> None:
    synthetic_test()
    x5, coverage = b27ad.b21.load5()
    assert len(x5) == 698112 and abs(float(coverage)-1.0) < 1e-12

    w = pd.read_csv(WINS)
    for c in ('signal_ts','signal_bar_start','session_end','h2_bar_start','leave2_bar_start','eligible_start'):
        w[c] = pd.to_datetime(w[c], utc=True, errors='coerce')
    clean = w[w.eligible_start.notna()].copy()
    exp_clean = {'external':13,'development':42,'reference_validation':14,'august':1}
    for p,n in exp_clean.items():
        assert len(clean[clean.partition == p]) == n, (p, len(clean[clean.partition == p]), n)

    fills = []
    for _, r in clean.iterrows():
        for zone, frac in CANDS.items():
            z = b27az.scan_candidate(x5, r, frac)
            if bool(z['filled']):
                fills.append({
                    'zone':zone, 'entry_frac':frac,
                    'partition':r.partition, 'date_utc':r.date_utc, 'signal_ts':r.signal_ts,
                    'fill_bar_start':pd.Timestamp(z['fill_bar_start']), 'entry_px':float(z['entry_px']),
                    'H':float(r.H), 'L':float(r.L), 'session_end':pd.Timestamp(r.session_end),
                })
    f = pd.DataFrame(fills)

    # Frozen B27AZ fill identities before economics.
    exp_pool = {'F05':28,'F10':37,'F15':42}
    for zone,n in exp_pool.items():
        got = len(f[(f.zone == zone) & f.partition.isin(MAJOR)])
        assert got == n, (zone, got, n)
    exp_f15 = {'external':10,'development':26,'reference_validation':6,'august':1}
    for p,n in exp_f15.items():
        got = len(f[(f.zone == 'F15') & (f.partition == p)])
        assert got == n, ('F15',p,got,n)

    trades = []
    for _, r in f.iterrows():
        trades.append(hybrid_general(x5, r, str(r.zone), float(r.entry_frac)))
    tr = pd.DataFrame(trades)
    sm = summarize(tr)

    # Mandatory exact B27AY F15 economic reproduction before F05/F10 interpretation.
    old = pd.read_csv(AY_SUM)
    for part in (*PARTS,'POOLED_MAJOR'):
        got = sm[(sm.zone == 'F15') & (sm.partition == part)].iloc[0]
        ref = old[old.partition == part].iloc[0]
        assert int(got.n) == int(ref.f15_fills_h2_h3), (part,'n',got.n,ref.f15_fills_h2_h3)
        assert int(got.activation_n) == int(ref.e20_activated), (part,'activation_n',got.activation_n,ref.e20_activated)
        checks = [('activation_rate','e20_activation_rate'),('wr','wr'),('pf','pf'),('expectancy','expectancy'),('total_pnl','total_pnl')]
        for gc, rc in checks:
            gv = float(got[gc]); rv = float(ref[rc])
            if math.isinf(gv) and math.isinf(rv):
                continue
            assert abs(gv-rv) < 1e-8 * max(1.0,abs(rv)), (part,gc,gv,rv)

    eligible = []
    for zone in CANDS:
        ok = True
        for part in MAJOR:
            r = sm[(sm.zone == zone) & (sm.partition == part)].iloc[0]
            ok = ok and int(r.n) > 0 and float(r.expectancy) >= 0 and float(r.pf) >= 1.0
        if ok:
            eligible.append(zone)

    pool = sm[sm.partition == 'POOLED_MAJOR'].copy().sort_values('total_pnl', ascending=False)
    diagnostic_best = str(pool.iloc[0].zone)
    selected = 'NONE'
    if eligible:
        selected = str(pool[pool.zone.isin(eligible)].iloc[0].zone)
    status = f'B27BA_SELECTED_{selected}__DIAGNOSTIC_BEST_{diagnostic_best}'

    tr.to_csv(OUT_TRADES,index=False)
    sm.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(status+'\n')

    def pct(v):
        return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
    def num(v):
        if pd.isna(v): return '-'
        if math.isinf(float(v)): return 'inf'
        return f'{float(v):.3f}'

    lines = [
        '# B27BA — BTC London->NY SHORT Post-H2 F05/F10/F15 Economic Comparison — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AZ clean windows/fill identities and the full B27AY F15 economics were reproduced before F05/F10 were interpreted.','',
        '| Zone | Partition | N | E20 act | E20 rate | WR | PF | Exp/trade $ | Total $ | Pre-invalid | Ceiling | Gap | Time | Med ratchets | Med capture | Med giveback |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for zone in CANDS:
        for part in (*PARTS,'POOLED_MAJOR'):
            r = sm[(sm.zone == zone) & (sm.partition == part)].iloc[0]
            lines.append(f'| {zone} | {part} | {int(r.n)} | {int(r.activation_n)} | {pct(r.activation_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {int(r.pre_invalidations)} | {int(r.ceiling_hits)} | {int(r.gap_exits)} | {int(r.time_exits)} | {num(r.median_ratchets)} | {pct(r.median_capture)} | {num(r.median_giveback)} |')
    lines += [
        '', '## Frozen selection', '',
        f'Formally eligible zones: **{", ".join(eligible) if eligible else "NONE"}**.',
        f'Selected zone: **{selected}**.',
        f'Highest pooled-PnL diagnostic zone: **{diagnostic_best}**.', '',
        'Only entry zone changed. F65 completed-close invalidation, E20 full-position hybrid continuation, fee/notional, and all chronology were frozen.',
        'No intermediate fraction or post-hoc threshold was tested. Research only; live BBC unchanged.'
    ]
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
