#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_f15_extension_econ_b27an as b27an

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Status.txt'
AQ_SUM = ROOT / 'BTC_LONDON_NY_SHORT_BLIND_F15_E20_PROFIT_LOCK_B27AQ_Summary.csv'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
ACTS = {'E05':.05,'E10':.10,'E15':.15,'E20':.20,'E25':.25,'E30':.30,'E40':.40,'E50':.50}
NOTIONAL = 500.0
FEE = 0.40
ENTRY_F = .15
STOP_F = .65
EPS = 1e-12


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def session_open(x5, end):
    p = int(x5.index.searchsorted(end, side='left'))
    if p >= len(x5) or x5.index[p] != end:
        raise AssertionError('missing exact session-end open')
    return float(x5.iloc[p].open)


def hybrid(x5: pd.DataFrame, r: pd.Series, act_name: str, ext: float) -> dict:
    H = float(r.H); L = float(r.L); R = H - L
    entry = float(r.entry_px); start = pd.Timestamp(r.fill_bar_start); end = pd.Timestamp(r.session_end)
    f65 = L + STOP_F * R; milestone = L - ext * R
    assert abs(entry - (L + ENTRY_F * R)) < 1e-9 * max(1.0, abs(entry))
    assert abs(milestone - (L - ext * R)) < 1e-12 * max(1.0, abs(milestone))

    q = b27ad.fast_slice(x5, start, end)
    if q.empty or q.index[0] != start: raise AssertionError('missing entry bar')
    highs = q.high.astype(float).to_numpy()

    reached = False; active = False; ceiling = np.nan; ratchets = 0; activation_bar = pd.NaT
    exit_bar = pd.NaT; exit_ts = pd.NaT; exit_px = np.nan; reason = None

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
            # Fill bar cannot activate. Intrabar milestone touch precedes same-bar close invalidation.
            if i > 0 and lo <= milestone + EPS:
                reached = True; active = True; activation_bar = ts; ceiling = milestone
                if np.isfinite(pivot) and pivot < ceiling:
                    ceiling = pivot; ratchets += 1
                continue
            if c > f65:
                exit_bar = ts; exit_ts = ts + BAR5; exit_px = c; reason = 'PRE_ACT_CLOSE_INVALIDATION_F65'; break
        else:
            if np.isfinite(pivot) and pivot < ceiling:
                old = ceiling; ceiling = pivot; ratchets += 1
                assert ceiling <= old + EPS

    if reason is None:
        exit_bar = end; exit_ts = end; exit_px = session_open(x5, end); reason = 'TIME_EXIT_SESSION_END'

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
        'activation': act_name, 'ext': ext, 'partition': r.partition, 'date_utc': r.date_utc,
        'signal_ts': r.signal_ts, 'entry_start': start, 'entry_px': entry,
        'H': H, 'L': L, 'range': R, 'F65': f65, 'activation_px': milestone,
        'session_end': end, 'activated': bool(reached), 'activation_bar_start': activation_bar,
        'ratchets': int(ratchets), 'final_ceiling': float(ceiling) if active else np.nan,
        'exit_bar_start': exit_bar, 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'exit_reason': reason, 'net_pnl_usd': net, 'win': bool(net > 0),
        'trough_extension_r': trough_ext, 'realized_exit_extension_r': exit_ext,
        'capture_ratio': capture, 'giveback_r': giveback,
    }


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for act in ACTS:
        for part in list(PARTS) + ['POOLED_MAJOR']:
            if part == 'POOLED_MAJOR':
                g = tr[(tr.activation == act) & tr.partition.isin(MAJOR)].copy()
            else:
                g = tr[(tr.activation == act) & (tr.partition == part)].copy()
            a = g[g.activated.astype(bool)]
            vals = g.net_pnl_usd.astype(float)
            rows.append({
                'activation': act, 'partition': part, 'n': len(g),
                'activation_rate': float(g.activated.mean()) if len(g) else np.nan,
                'wr': float((vals > 0).mean()) if len(g) else np.nan,
                'pf': pf(vals), 'expectancy': float(vals.mean()) if len(g) else np.nan,
                'total_pnl': float(vals.sum()) if len(g) else np.nan,
                'ceiling_hits': int((g.exit_reason == 'PROFIT_CEILING_HIT').sum()),
                'gap_exits': int((g.exit_reason == 'PROFIT_CEILING_GAP_OPEN').sum()),
                'time_exits': int((g.exit_reason == 'TIME_EXIT_SESSION_END').sum()),
                'pre_invalidations': int((g.exit_reason == 'PRE_ACT_CLOSE_INVALIDATION_F65').sum()),
                'median_ratchets': float(a.ratchets.median()) if len(a) else np.nan,
                'median_trough_ext': float(a.trough_extension_r.median()) if len(a) else np.nan,
                'median_exit_ext': float(a.realized_exit_extension_r.median()) if len(a) else np.nan,
                'median_capture': float(a.capture_ratio.median()) if len(a) else np.nan,
                'median_giveback': float(a.giveback_r.median()) if len(a) else np.nan,
            })
    return pd.DataFrame(rows)


def synthetic_tests():
    idx = pd.date_range('2026-01-05 14:00', periods=7, freq='5min', tz='UTC')
    x = pd.DataFrame([
        {'open':91.5,'high':92.0,'low':91.0,'close':91.6},
        {'open':91.6,'high':97.0,'low':88.8,'close':97.0},
        {'open':88.5,'high':88.8,'low':87.0,'close':87.5},
        {'open':87.5,'high':88.0,'low':86.5,'close':87.0},
        {'open':87.0,'high':89.2,'low':86.8,'close':88.5},
        {'open':88.5,'high':88.8,'low':87.5,'close':88.0},
        {'open':88.0,'high':88.2,'low':87.5,'close':87.8},
    ], index=idx)
    r = pd.Series({'partition':'x','date_utc':'2026-01-05','signal_ts':idx[0]-BAR5,
                   'fill_bar_start':idx[0],'entry_px':91.5,'H':100.0,'L':90.0,'session_end':idx[6]})
    z = hybrid(x, r, 'E10', .10)
    assert z['activated']
    assert z['exit_reason'] != 'PRE_ACT_CLOSE_INVALIDATION_F65'
    assert z['net_pnl_usd'] > 0


def main():
    synthetic_tests()
    x5, coverage = b27ad.b21.load5(); assert abs(float(coverage)-1.0) < 1e-12
    f = b27an.reconstruct_f15(x5)
    expected_n = {'external':50,'development':79,'reference_validation':34,'august':1}
    for part, n in expected_n.items(): assert len(f[f.partition == part]) == n

    # Frozen B27AN E20/D50 fixed baseline.
    fixed = pd.DataFrame([b27an.simulate(x5, r, 'E20', .20, 'D50', .50) for _, r in f.iterrows()])
    fixed_total = float(fixed[fixed.partition.isin(MAJOR)].net_pnl_usd.sum())
    assert abs(fixed_total - (-11.66557892047709)) < 0.02

    rows = []
    for _, r in f.iterrows():
        for act, ext in ACTS.items(): rows.append(hybrid(x5, r, act, ext))
    tr = pd.DataFrame(rows); assert len(tr) == len(f) * len(ACTS)

    # Mandatory exact E20 reproduction of B27AQ summary before interpretation.
    sm = summarize(tr)
    aq = pd.read_csv(AQ_SUM)
    for part in list(PARTS) + ['POOLED_MAJOR']:
        got = sm[(sm.activation == 'E20') & (sm.partition == part)].iloc[0]
        old = aq[aq.partition == part].iloc[0]
        checks = [('n','n'),('wr','wr'),('pf','pf'),('expectancy','exp'),('total_pnl','total'),('activation_rate','e20_rate')]
        for gc, oc in checks:
            gv = float(got[gc]); ov = float(old[oc])
            if math.isinf(gv) and math.isinf(ov): continue
            assert abs(gv - ov) < 1e-8 * max(1.0, abs(ov)), (part, gc, gv, ov)

    supported = []
    for act in ACTS:
        pool = sm[(sm.activation == act) & (sm.partition == 'POOLED_MAJOR')].iloc[0]
        ok = float(pool.expectancy) > 0 and float(pool.pf) >= 1.20 and float(pool.total_pnl) > fixed_total
        for part in MAJOR:
            rr = sm[(sm.activation == act) & (sm.partition == part)].iloc[0]
            ok = ok and float(rr.expectancy) >= 0 and float(rr.pf) >= 1.0
        if ok: supported.append(act)

    pool_rows = sm[sm.partition == 'POOLED_MAJOR'].copy().sort_values('total_pnl', ascending=False)
    diagnostic_best = str(pool_rows.iloc[0].activation)
    selected = 'NONE'
    if supported:
        eligible = pool_rows[pool_rows.activation.isin(supported)]
        selected = str(eligible.iloc[0].activation)
    status = f'B27AT_SELECTED_{selected}__DIAGNOSTIC_BEST_{diagnostic_best}'

    tr.to_csv(OUT_TRADES, index=False); sm.to_csv(OUT_SUM, index=False); OUT_STATUS.write_text(status+'\n')

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'

    md = ['# B27AT — BTC London->NY SHORT F15 Full-Position Hybrid Activation Grid — Result','',
          f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
          '**Audit status: PASS.** Frozen F15 cohort, B27AN fixed baseline, and B27AQ E20 full-hybrid reproduction passed before the activation grid was interpreted.','',
          f'Frozen B27AN E20/D50 pooled-major fixed baseline: **${fixed_total:+.3f}**.','',
          '| Activation | Partition | N | Activation | WR | PF | Exp/trade $ | Total $ | Ceiling | Gap | Time | Pre-invalid | Med ratchets | Med trough | Med exit ext | Med capture | Med giveback |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for act in ACTS:
        for part in list(PARTS) + ['POOLED_MAJOR']:
            r = sm[(sm.activation == act) & (sm.partition == part)].iloc[0]
            md.append(f'| {act} | {part} | {int(r.n)} | {pct(r.activation_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {int(r.ceiling_hits)} | {int(r.gap_exits)} | {int(r.time_exits)} | {int(r.pre_invalidations)} | {num(r.median_ratchets)} | {num(r.median_trough_ext)} | {num(r.median_exit_ext)} | {pct(r.median_capture)} | {num(r.median_giveback)} |')
    md += ['', '## Frozen selection', '',
           f'**Supported candidates: {", ".join(supported) if supported else "NONE"}.**',
           f'**Selected activation: {selected}.**',
           f'**Highest pooled-PnL diagnostic candidate: {diagnostic_best}.**', '',
           'No intermediate activation, split ratio, alternate stop, entry, regime, confirmation, candle threshold, or runner parameter was searched.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n'); print('\n'.join(md))

if __name__ == '__main__':
    main()
