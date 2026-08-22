#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS_CSV = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_OPT_B27R_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_OPT_B27R_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_OPT_B27R_Summary.csv'
OUT_SELECT = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_OPT_B27R_Selection.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_OPT_B27R_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
TRANSITION = 'LONDON_TO_NEWYORK'
SIDE = 'LONG'
KS = (1, 2)
PARTS = ('external', 'development', 'reference_validation', 'august')
DEV_PARTS = ('external', 'development')
FRACS = {
    'F50': 0.50,
    'F55': 0.55,
    'F60': 0.60,
    'F65': 0.65,
    'F70': 0.70,
    'F75': 0.75,
    'F80': 0.80,
}
METHODS = ('NEXT_OPEN',) + tuple(FRACS.keys()) + ('SIG_MID', 'SIG_LOW')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def pf(vals) -> float:
    s = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def resolve_market(q5: pd.DataFrame, start_k: int, entry_px: float, stop_px: float, target_px: float):
    for k in range(start_k, len(q5)):
        r = q5.iloc[k]
        tp = float(r.high) >= target_px
        sl = float(r.low) <= stop_px
        if tp and sl:
            px, reason = stop_px, 'SL_SAME_5M_CONSERVATIVE'
        elif sl:
            px, reason = stop_px, 'SL_RANGE_EDGE'
        elif tp:
            px, reason = target_px, 'TP_RANGE_EDGE'
        else:
            continue
        ret = px / entry_px - 1.0
        return q5.index[k], float(px), float(ret), reason
    return None


def resolve_limit(q5: pd.DataFrame, fill_k: int, entry_px: float, stop_px: float, target_px: float):
    r0 = q5.iloc[fill_k]
    if float(r0.low) <= stop_px:
        ret = stop_px / entry_px - 1.0
        return q5.index[fill_k], float(stop_px), float(ret), 'SL_FILL_5M_CONSERVATIVE'

    for k in range(fill_k + 1, len(q5)):
        r = q5.iloc[k]
        tp = float(r.high) >= target_px
        sl = float(r.low) <= stop_px
        if tp and sl:
            px, reason = stop_px, 'SL_SAME_5M_CONSERVATIVE'
        elif sl:
            px, reason = stop_px, 'SL_RANGE_EDGE'
        elif tp:
            px, reason = target_px, 'TP_RANGE_EDGE'
        else:
            continue
        ret = px / entry_px - 1.0
        return q5.index[k], float(px), float(ret), reason
    return None


def find_limit_fill(q5: pd.DataFrame, signal_ts: pd.Timestamp, H: float, L: float, entry_px: float):
    k0 = int(q5.index.searchsorted(signal_ts, side='left'))
    for k in range(k0, len(q5)):
        r = q5.iloc[k]
        close = float(r.close)
        if close > H or close < L:
            return {'status': 'RANGE_BROKE_BEFORE_FILL', 'cancel_ts': q5.index[k] + BAR5}
        if float(r.low) <= entry_px <= float(r.high):
            return {'status': 'FILLED', 'fill_k': k, 'fill_ts': q5.index[k]}
    return {'status': 'NO_FILL'}


def finish_time_exit(x5: pd.DataFrame, session_end: pd.Timestamp, entry_px: float, entry_ts: pd.Timestamp):
    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5):
        return None
    ts = x5.index[pos]
    px = float(x5.iloc[pos].open)
    ret = px / entry_px - 1.0
    return ts, px, ret, 'TIME_EXIT_SESSION_END', float((ts - entry_ts) / pd.Timedelta(minutes=1))


def planned_price(method: str, H: float, L: float, sigbar: pd.Series):
    if method in FRACS:
        return float(L + FRACS[method] * (H - L))
    if method == 'SIG_MID':
        return float((float(sigbar.high) + float(sigbar.low)) / 2.0)
    if method == 'SIG_LOW':
        return float(sigbar.low)
    return np.nan


def simulate_one(x5: pd.DataFrame, s: pd.Series, method: str):
    H = float(s.previous_session_high)
    L = float(s.previous_session_low)
    signal_ts = pd.Timestamp(s.signal_ts)
    signal_bar_start = pd.Timestamp(s.signal_bar_start)
    session_end = pd.Timestamp(s.active_session_end)
    assert H > L

    sig_pos = int(x5.index.searchsorted(signal_bar_start, side='left'))
    if sig_pos >= len(x5) or x5.index[sig_pos] != signal_bar_start:
        raise AssertionError('signal bar missing from raw 5m')
    sigbar = x5.iloc[sig_pos]
    q5 = fast_slice(x5, signal_ts, session_end)

    base = {
        'signal_id': f"{s.partition}|{s.transition}|{s.date_utc}|K{int(s.k)}|{signal_ts.isoformat()}",
        'partition': s.partition,
        'transition': s.transition,
        'date_utc': s.date_utc,
        'k': int(s.k),
        'opp_visits_at_signal': int(s.opp_visits_at_signal),
        'signal_ts': signal_ts,
        'signal_bar_start': signal_bar_start,
        'structural_outcome': s.structural_outcome,
        'previous_session_high': H,
        'previous_session_low': L,
        'entry_method': method,
        'stop_px': L,
        'target_px': H,
    }

    if q5.empty:
        return {**base, 'planned_entry_px': np.nan, 'planned_valid': False, 'filled': False,
                'entry_ts': pd.NaT, 'entry_px': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                'exit_reason': 'NO_ELIGIBLE_5M', 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                'hold_minutes': np.nan, 'nominal_rr': np.nan}

    if method == 'NEXT_OPEN':
        first_ts = q5.index[0]
        if first_ts != signal_ts:
            raise AssertionError('NEXT_OPEN first eligible bar does not start at signal_ts')
        entry_px = float(q5.iloc[0].open)
        valid = bool(L <= entry_px <= H)
        if not valid:
            return {**base, 'planned_entry_px': entry_px, 'planned_valid': False, 'filled': False,
                    'entry_ts': pd.NaT, 'entry_px': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                    'exit_reason': 'NEXT_OPEN_OUTSIDE_RANGE', 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                    'hold_minutes': np.nan, 'nominal_rr': np.nan}
        risk = entry_px - L
        reward = H - entry_px
        if risk <= 0 or reward < 0:
            raise AssertionError('invalid NEXT_OPEN geometry')
        rr = reward / risk
        solved = resolve_market(q5, 0, entry_px, L, H)
        if solved is None:
            te = finish_time_exit(x5, session_end, entry_px, first_ts)
            if te is None:
                return {**base, 'planned_entry_px': entry_px, 'planned_valid': True, 'filled': True,
                        'entry_ts': first_ts, 'entry_px': entry_px, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                        'exit_reason': 'CENSORED', 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                        'hold_minutes': np.nan, 'nominal_rr': rr}
            exit_ts, exit_px, ret, reason, hold = te
        else:
            exit_ts, exit_px, ret, reason = solved
            hold = float((exit_ts - first_ts) / pd.Timedelta(minutes=1))
        return {**base, 'planned_entry_px': entry_px, 'planned_valid': True, 'filled': True,
                'entry_ts': first_ts, 'entry_px': entry_px, 'exit_ts': exit_ts, 'exit_px': exit_px,
                'exit_reason': reason, 'gross_return': ret, 'net_pnl_usd': ret * NOTIONAL - FEE,
                'hold_minutes': hold, 'nominal_rr': rr}

    px = planned_price(method, H, L, sigbar)
    valid = bool(L <= px <= H)
    if not valid:
        return {**base, 'planned_entry_px': px, 'planned_valid': False, 'filled': False,
                'entry_ts': pd.NaT, 'entry_px': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                'exit_reason': 'PLANNED_PRICE_OUTSIDE_RANGE', 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                'hold_minutes': np.nan, 'nominal_rr': np.nan}

    risk = px - L
    reward = H - px
    if risk <= 0 or reward < 0:
        return {**base, 'planned_entry_px': px, 'planned_valid': False, 'filled': False,
                'entry_ts': pd.NaT, 'entry_px': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                'exit_reason': 'ZERO_RISK_OR_BAD_GEOMETRY', 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                'hold_minutes': np.nan, 'nominal_rr': np.nan}
    rr = reward / risk

    fill = find_limit_fill(q5, signal_ts, H, L, px)
    if fill['status'] != 'FILLED':
        return {**base, 'planned_entry_px': px, 'planned_valid': True, 'filled': False,
                'entry_ts': pd.NaT, 'entry_px': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                'exit_reason': fill['status'], 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                'hold_minutes': np.nan, 'nominal_rr': rr}

    fill_k = int(fill['fill_k'])
    fill_ts = pd.Timestamp(fill['fill_ts'])
    solved = resolve_limit(q5, fill_k, px, L, H)
    if solved is None:
        te = finish_time_exit(x5, session_end, px, fill_ts)
        if te is None:
            return {**base, 'planned_entry_px': px, 'planned_valid': True, 'filled': True,
                    'entry_ts': fill_ts, 'entry_px': px, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                    'exit_reason': 'CENSORED', 'gross_return': np.nan, 'net_pnl_usd': np.nan,
                    'hold_minutes': np.nan, 'nominal_rr': rr}
        exit_ts, exit_px, ret, reason, hold = te
    else:
        exit_ts, exit_px, ret, reason = solved
        hold = float((exit_ts - fill_ts) / pd.Timedelta(minutes=1))

    return {**base, 'planned_entry_px': px, 'planned_valid': True, 'filled': True,
            'entry_ts': fill_ts, 'entry_px': px, 'exit_ts': exit_ts, 'exit_px': exit_px,
            'exit_reason': reason, 'gross_return': ret, 'net_pnl_usd': ret * NOTIONAL - FEE,
            'hold_minutes': hold, 'nominal_rr': rr}


def metrics(g: pd.DataFrame):
    setups = int(len(g))
    valid = int(g.planned_valid.astype(bool).sum()) if setups else 0
    fills = int(g.filled.astype(bool).sum()) if setups else 0
    r = g[g.filled.astype(bool) & pd.to_numeric(g.net_pnl_usd, errors='coerce').notna()].copy() if setups else g
    n = len(r)
    if n == 0:
        return {'setups': setups, 'valid_plans': valid, 'fills': fills, 'fill_rate': fills/setups if setups else np.nan,
                'wins': 0, 'losses': 0, 'wr': np.nan, 'tp_rate': np.nan, 'net_pf': np.nan,
                'net_exp': np.nan, 'total_net': np.nan, 'time_exit_rate': np.nan, 'median_nominal_rr': np.nan}
    net = pd.to_numeric(r.net_pnl_usd, errors='coerce')
    return {'setups': setups, 'valid_plans': valid, 'fills': n, 'fill_rate': n/setups if setups else np.nan,
            'wins': int((net > 0).sum()), 'losses': int((net <= 0).sum()), 'wr': float((net > 0).mean()),
            'tp_rate': float((r.exit_reason == 'TP_RANGE_EDGE').mean()), 'net_pf': float(pf(net)),
            'net_exp': float(net.mean()), 'total_net': float(net.sum()),
            'time_exit_rate': float((r.exit_reason == 'TIME_EXIT_SESSION_END').mean()),
            'median_nominal_rr': float(pd.to_numeric(r.nominal_rr, errors='coerce').median())}


def summarize(trades: pd.DataFrame):
    rows = []
    for part in PARTS:
        for k in KS:
            for method in METHODS:
                g = trades[(trades.partition == part) & (trades.k == k) & (trades.entry_method == method)]
                rows.append({'partition': part, 'k': k, 'entry_method': method, **metrics(g)})
    return pd.DataFrame(rows)


def select_primary(summary: pd.DataFrame, trades: pd.DataFrame):
    dev = summary[(summary.partition.isin(DEV_PARTS)) & (summary.k == 1)].copy()
    assert set(dev.partition.unique()).issubset(set(DEV_PARTS))
    rows = []
    for method in METHODS:
        z = dev[dev.entry_method == method].set_index('partition')
        if not all(p in z.index for p in DEV_PARTS):
            continue
        ext, dvl = z.loc['external'], z.loc['development']
        eligible = bool(ext.fills >= 20 and dvl.fills >= 20 and ext.net_exp > 0 and dvl.net_exp > 0
                        and ext.net_pf >= 1.10 and dvl.net_pf >= 1.10)
        pool = trades[(trades.k == 1) & (trades.entry_method == method) & trades.partition.isin(DEV_PARTS)
                      & trades.filled.astype(bool) & pd.to_numeric(trades.net_pnl_usd, errors='coerce').notna()]
        pooled_exp = float(pd.to_numeric(pool.net_pnl_usd, errors='coerce').mean()) if len(pool) else np.nan
        rows.append({'entry_method': method, 'external_fills': int(ext.fills), 'development_fills': int(dvl.fills),
                     'external_pf': float(ext.net_pf) if not pd.isna(ext.net_pf) else np.nan,
                     'development_pf': float(dvl.net_pf) if not pd.isna(dvl.net_pf) else np.nan,
                     'external_exp': float(ext.net_exp) if not pd.isna(ext.net_exp) else np.nan,
                     'development_exp': float(dvl.net_exp) if not pd.isna(dvl.net_exp) else np.nan,
                     'min_pf': float(min(ext.net_pf, dvl.net_pf)) if not (pd.isna(ext.net_pf) or pd.isna(dvl.net_pf)) else np.nan,
                     'pooled_dev_exp': pooled_exp, 'min_fills': int(min(ext.fills, dvl.fills)),
                     'dev_eligible': eligible})
    sel = pd.DataFrame(rows)
    elig = sel[sel.dev_eligible].copy()
    if len(elig) == 0:
        return sel, None
    elig = elig.sort_values(['min_pf', 'pooled_dev_exp', 'min_fills'], ascending=[False, False, False])
    return sel, str(elig.iloc[0].entry_method)


def audit_real(x5: pd.DataFrame, signals: pd.DataFrame, trades: pd.DataFrame):
    assert (signals.transition == TRANSITION).all()
    assert (signals.side == SIDE).all()
    assert signals.k.isin(KS).all()
    assert (signals.opp_visits_at_signal == 0).all()
    assert (trades.transition == TRANSITION).all()
    assert (trades.opp_visits_at_signal == 0).all()
    assert ((pd.to_datetime(trades.entry_ts, utc=True, errors='coerce') >= pd.to_datetime(trades.signal_ts, utc=True, errors='coerce'))
            | pd.to_datetime(trades.entry_ts, utc=True, errors='coerce').isna()).all()
    assert np.allclose(pd.to_numeric(trades.stop_px), pd.to_numeric(trades.previous_session_low))
    assert np.allclose(pd.to_numeric(trades.target_px), pd.to_numeric(trades.previous_session_high))

    for method, frac in FRACS.items():
        g = trades[trades.entry_method == method]
        expect = g.previous_session_low.astype(float) + frac * (g.previous_session_high.astype(float) - g.previous_session_low.astype(float))
        assert np.allclose(g.planned_entry_px.astype(float), expect.astype(float))

    # NEXT_OPEN exact mapping.
    for r in trades[(trades.entry_method == 'NEXT_OPEN') & trades.planned_valid.astype(bool)].itertuples(index=False):
        ts = pd.Timestamp(r.signal_ts)
        pos = int(x5.index.searchsorted(ts, side='left'))
        assert pos < len(x5) and x5.index[pos] == ts
        assert abs(float(r.planned_entry_px) - float(x5.iloc[pos].open)) < 1e-9

    # Local methods derive only from completed signal bar.
    for method in ('SIG_MID', 'SIG_LOW'):
        for r in trades[trades.entry_method == method].itertuples(index=False):
            ts = pd.Timestamp(r.signal_bar_start)
            pos = int(x5.index.searchsorted(ts, side='left'))
            assert pos < len(x5) and x5.index[pos] == ts
            row = x5.iloc[pos]
            exp = (float(row.high)+float(row.low))/2.0 if method == 'SIG_MID' else float(row.low)
            assert abs(float(r.planned_entry_px)-exp) < 1e-9

    # No filled limit has a strict close-break before fill.
    lim = trades[(trades.entry_method != 'NEXT_OPEN') & trades.filled.astype(bool)]
    for r in lim.itertuples(index=False):
        q = fast_slice(x5, pd.Timestamp(r.signal_ts), pd.Timestamp(r.entry_ts))
        if len(q):
            assert not ((q.close.astype(float) > float(r.previous_session_high)) | (q.close.astype(float) < float(r.previous_session_low))).any()


def synthetic_tests():
    idx = pd.date_range('2026-01-01 13:30', periods=4, freq='5min', tz='UTC')
    q = pd.DataFrame([
        {'open':99.0,'high':100.0,'low':97.0,'close':99.0},
        {'open':99.0,'high':99.5,'low':95.0,'close':96.0},
        {'open':96.0,'high':98.0,'low':94.0,'close':97.0},
        {'open':97.0,'high':101.0,'low':96.0,'close':100.5},
    ], index=idx)
    f = find_limit_fill(q, idx[1], 100.0, 90.0, 95.0)
    assert f['status'] == 'FILLED' and f['fill_ts'] == idx[1]
    f2 = find_limit_fill(q, idx[1], 100.0, 90.0, 93.0)
    assert f2['status'] == 'RANGE_BROKE_BEFORE_FILL'
    m = resolve_market(q, 1, 99.0, 90.0, 100.0)
    assert m is not None and m[3] == 'TP_RANGE_EDGE'


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    synthetic_tests()
    x5, coverage = b21.load5()
    s = pd.read_csv(SIGNALS_CSV)
    for c in ['signal_ts','signal_bar_start','active_session_end']:
        s[c] = pd.to_datetime(s[c], utc=True, errors='coerce')
    s = s[(s.transition == TRANSITION) & (s.side == SIDE) & s.k.isin(KS) & (s.opp_visits_at_signal == 0)].copy()
    assert len(s) > 0

    rows = []
    for sig in s.itertuples(index=False):
        ser = pd.Series(sig._asdict())
        for method in METHODS:
            rows.append(simulate_one(x5, ser, method))
    trades = pd.DataFrame(rows)
    audit_real(x5, s, trades)
    trades.to_csv(OUT_TRADES, index=False)

    sm = summarize(trades)
    sm.to_csv(OUT_SUM, index=False)

    selection, selected = select_primary(sm, trades)
    if selected is not None:
        ref = sm[(sm.partition == 'reference_validation') & (sm.k == 1) & (sm.entry_method == selected)].iloc[0]
        ref_pass = bool(ref.fills >= 15 and ref.net_exp > 0 and ref.net_pf >= 1.20)
    else:
        ref = None
        ref_pass = False
    selection['selected_primary'] = selection.entry_method.eq(selected) if selected is not None else False
    selection['reference_pass'] = selection.entry_method.eq(selected) & ref_pass if selected is not None else False
    selection.to_csv(OUT_SELECT, index=False)

    status = (trades.groupby(['partition','k','entry_method','exit_reason'], dropna=False).size().reset_index(name='n'))
    status.to_csv(OUT_STATUS, index=False)

    md = [
        '# B27R — London -> New York LONG Entry Optimization — Result','',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** B27Q signal identities were reused unchanged; B27R changed entry mechanics only.','',
        'Primary cohort: London->New York LONG, K1 High visit, OPP0. Secondary: same cohort at K2. TP/SL remain frozen previous-session High/Low.','',
        '## Primary K1 entry grid','',
        '| Partition | Method | Setups | Fills | Fill rate | W | L | WR | TP rate | PF | Net exp | Total net | Median RR |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in PARTS:
        g = sm[(sm.partition == part) & (sm.k == 1)]
        for r in g.itertuples(index=False):
            md.append(f'| {part} | {r.entry_method} | {r.setups} | {r.fills} | {pct(r.fill_rate)} | {r.wins} | {r.losses} | {pct(r.wr)} | {pct(r.tp_rate)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {num(r.median_nominal_rr)} |')

    md += ['', '## Development-only selection','']
    if selected is None:
        md += ['**No primary method satisfied the predeclared external + development eligibility gate.**']
    else:
        md += [f'Selected without using reference_validation/August metrics: **{selected}**.']
        if ref is not None:
            md += [f'Reference-validation: fills **{int(ref.fills)}**, PF **{num(ref.net_pf)}**, net exp **${num(ref.net_exp)}**, WR **{pct(ref.wr)}** -> **{"PASS" if ref_pass else "FAIL"}**.']

    md += ['', '## Secondary K2 diagnostic','',
           '| Partition | Method | Setups | Fills | WR | PF | Net exp | Total net |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for part in PARTS:
        g = sm[(sm.partition == part) & (sm.k == 2)]
        for r in g.itertuples(index=False):
            md.append(f'| {part} | {r.entry_method} | {r.setups} | {r.fills} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} |')

    md += ['', 'Selection is research-only. Reference validation is historical and not pristine independent OOS. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')


if __name__ == '__main__':
    main()
