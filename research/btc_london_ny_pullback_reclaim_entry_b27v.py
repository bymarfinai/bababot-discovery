#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_PULLBACK_RECLAIM_ENTRY_B27V_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_PULLBACK_RECLAIM_ENTRY_B27V_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_PULLBACK_RECLAIM_ENTRY_B27V_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_PULLBACK_RECLAIM_ENTRY_B27V_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
KS = (1, 2)
ZONES = {'Z75': 0.75, 'Z80': 0.80, 'Z85': 0.85}


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_signals() -> pd.DataFrame:
    raw = pd.read_csv(SIGNALS)
    s = raw[
        (raw.transition == 'LONDON_TO_NEWYORK')
        & (raw.side == 'LONG')
        & (raw.k.isin(KS))
        & (raw.opp_visits_at_signal == 0)
    ].copy()
    for c in ('signal_ts', 'signal_bar_start', 'active_session_end'):
        s[c] = pd.to_datetime(s[c], utc=True)
    s['signal_id'] = (
        s.partition.astype(str) + '|' + s.date_utc.astype(str) + '|K' + s.k.astype(int).astype(str)
        + '|' + s.signal_ts.astype(str)
    )
    assert not s.signal_id.duplicated().any()
    return s.sort_values(['partition', 'signal_ts', 'k']).reset_index(drop=True)


def resolve_trade(q: pd.DataFrame, entry_k: int, entry_px: float, stop_px: float, target_px: float):
    for k in range(entry_k, len(q)):
        r = q.iloc[k]
        tp = float(r.high) >= target_px
        sl = float(r.low) <= stop_px
        if tp and sl:
            return q.index[k], float(stop_px), 'SL_SAME_5M_CONSERVATIVE'
        if sl:
            return q.index[k], float(stop_px), 'SL_PULLBACK_LOW'
        if tp:
            return q.index[k], float(target_px), 'TP_PREV_HIGH'
    return None


def time_exit(x5: pd.DataFrame, session_end: pd.Timestamp):
    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5):
        return None
    return x5.index[pos], float(x5.iloc[pos].open), 'TIME_EXIT_SESSION_END'


def simulate_one(x5: pd.DataFrame, s: pd.Series, zone_name: str) -> dict:
    H = float(s.previous_session_high)
    L = float(s.previous_session_low)
    rng = H - L
    assert H > L
    zone_frac = ZONES[zone_name]
    zone_px = L + zone_frac * rng
    signal_ts = pd.Timestamp(s.signal_ts)
    signal_bar_start = pd.Timestamp(s.signal_bar_start)
    session_end = pd.Timestamp(s.active_session_end)
    q = fast_slice(x5, signal_ts, session_end)

    base = {
        'signal_id': s.signal_id,
        'partition': s.partition,
        'date_utc': s.date_utc,
        'k': int(s.k),
        'signal_ts': signal_ts,
        'signal_bar_start': signal_bar_start,
        'structural_outcome': s.structural_outcome,
        'previous_session_high': H,
        'previous_session_low': L,
        'zone_name': zone_name,
        'zone_fraction': zone_frac,
        'zone_px': zone_px,
    }

    if q.empty:
        return {
            **base, 'status': 'NO_ELIGIBLE_5M', 'activated': False, 'activation_bar_start': pd.NaT,
            'activation_ts': pd.NaT, 'confirmed': False, 'confirmation_bar_start': pd.NaT,
            'confirmation_ts': pd.NaT, 'confirmation_close': np.nan, 'prior_bar_high_at_confirm': np.nan,
            'pullback_low': np.nan, 'pullback_low_fraction': np.nan, 'filled': False,
            'entry_ts': pd.NaT, 'entry_px': np.nan, 'stop_px': np.nan, 'target_px': H,
            'nominal_rr': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
            'exit_reason': 'NO_ELIGIBLE_5M', 'net_pnl_usd': np.nan,
        }

    activated = False
    activation_k = None
    activation_ts = pd.NaT
    pullback_low = np.nan

    for k in range(len(q)):
        ts = q.index[k]
        r = q.iloc[k]
        close = float(r.close)
        low = float(r.low)

        # Structural close-break invalidation is evaluated before activation/confirmation.
        if close > H:
            status = 'TARGET_BROKE_BEFORE_CONFIRMATION'
            return {
                **base, 'status': status, 'activated': activated,
                'activation_bar_start': q.index[activation_k] if activation_k is not None else pd.NaT,
                'activation_ts': (q.index[activation_k] + BAR5) if activation_k is not None else pd.NaT,
                'confirmed': False, 'confirmation_bar_start': pd.NaT, 'confirmation_ts': pd.NaT,
                'confirmation_close': np.nan, 'prior_bar_high_at_confirm': np.nan,
                'pullback_low': pullback_low, 'pullback_low_fraction': ((pullback_low-L)/rng if activated else np.nan),
                'filled': False, 'entry_ts': pd.NaT, 'entry_px': np.nan, 'stop_px': np.nan,
                'target_px': H, 'nominal_rr': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                'exit_reason': status, 'net_pnl_usd': np.nan,
            }
        if close < L:
            status = 'OPPOSITE_BROKE_BEFORE_CONFIRMATION'
            return {
                **base, 'status': status, 'activated': activated,
                'activation_bar_start': q.index[activation_k] if activation_k is not None else pd.NaT,
                'activation_ts': (q.index[activation_k] + BAR5) if activation_k is not None else pd.NaT,
                'confirmed': False, 'confirmation_bar_start': pd.NaT, 'confirmation_ts': pd.NaT,
                'confirmation_close': np.nan, 'prior_bar_high_at_confirm': np.nan,
                'pullback_low': pullback_low, 'pullback_low_fraction': ((pullback_low-L)/rng if activated else np.nan),
                'filled': False, 'entry_ts': pd.NaT, 'entry_px': np.nan, 'stop_px': np.nan,
                'target_px': H, 'nominal_rr': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                'exit_reason': status, 'net_pnl_usd': np.nan,
            }

        if not activated:
            if low <= zone_px:
                activated = True
                activation_k = k
                activation_ts = ts + BAR5
                pullback_low = low
            # Same activation bar can never confirm.
            continue

        pullback_low = min(float(pullback_low), low)
        if k <= int(activation_k):
            continue

        prior_high = float(q.iloc[k - 1].high)
        if close >= zone_px and close > prior_high and L <= close <= H:
            confirmation_bar_start = ts
            confirmation_ts = ts + BAR5
            frozen_pullback_low = float(pullback_low)
            pullback_low_frac = (frozen_pullback_low - L) / rng
            next_k = k + 1
            if next_k >= len(q):
                status = 'NO_ENTRY_BAR'
                return {
                    **base, 'status': status, 'activated': True,
                    'activation_bar_start': q.index[activation_k], 'activation_ts': activation_ts,
                    'confirmed': True, 'confirmation_bar_start': confirmation_bar_start,
                    'confirmation_ts': confirmation_ts, 'confirmation_close': close,
                    'prior_bar_high_at_confirm': prior_high, 'pullback_low': frozen_pullback_low,
                    'pullback_low_fraction': pullback_low_frac, 'filled': False,
                    'entry_ts': pd.NaT, 'entry_px': np.nan, 'stop_px': frozen_pullback_low,
                    'target_px': H, 'nominal_rr': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                    'exit_reason': status, 'net_pnl_usd': np.nan,
                }

            entry_ts = q.index[next_k]
            assert entry_ts == confirmation_ts
            entry_px = float(q.iloc[next_k].open)
            if not (frozen_pullback_low < entry_px < H):
                status = 'INVALID_NEXT_OPEN_GEOMETRY'
                return {
                    **base, 'status': status, 'activated': True,
                    'activation_bar_start': q.index[activation_k], 'activation_ts': activation_ts,
                    'confirmed': True, 'confirmation_bar_start': confirmation_bar_start,
                    'confirmation_ts': confirmation_ts, 'confirmation_close': close,
                    'prior_bar_high_at_confirm': prior_high, 'pullback_low': frozen_pullback_low,
                    'pullback_low_fraction': pullback_low_frac, 'filled': False,
                    'entry_ts': pd.NaT, 'entry_px': np.nan, 'stop_px': frozen_pullback_low,
                    'target_px': H, 'nominal_rr': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
                    'exit_reason': status, 'net_pnl_usd': np.nan,
                }

            stop_px = frozen_pullback_low
            target_px = H
            nominal_rr = (target_px - entry_px) / (entry_px - stop_px)
            solved = resolve_trade(q, next_k, entry_px, stop_px, target_px)
            if solved is None:
                te = time_exit(x5, session_end)
                if te is None:
                    return {
                        **base, 'status': 'CENSORED', 'activated': True,
                        'activation_bar_start': q.index[activation_k], 'activation_ts': activation_ts,
                        'confirmed': True, 'confirmation_bar_start': confirmation_bar_start,
                        'confirmation_ts': confirmation_ts, 'confirmation_close': close,
                        'prior_bar_high_at_confirm': prior_high, 'pullback_low': frozen_pullback_low,
                        'pullback_low_fraction': pullback_low_frac, 'filled': True,
                        'entry_ts': entry_ts, 'entry_px': entry_px, 'stop_px': stop_px,
                        'target_px': target_px, 'nominal_rr': nominal_rr,
                        'exit_ts': pd.NaT, 'exit_px': np.nan, 'exit_reason': 'CENSORED',
                        'net_pnl_usd': np.nan,
                    }
                exit_ts, exit_px, reason = te
            else:
                exit_ts, exit_px, reason = solved
            ret = exit_px / entry_px - 1.0
            return {
                **base, 'status': 'TRADE', 'activated': True,
                'activation_bar_start': q.index[activation_k], 'activation_ts': activation_ts,
                'confirmed': True, 'confirmation_bar_start': confirmation_bar_start,
                'confirmation_ts': confirmation_ts, 'confirmation_close': close,
                'prior_bar_high_at_confirm': prior_high, 'pullback_low': frozen_pullback_low,
                'pullback_low_fraction': pullback_low_frac, 'filled': True,
                'entry_ts': entry_ts, 'entry_px': entry_px, 'stop_px': stop_px,
                'target_px': target_px, 'nominal_rr': nominal_rr, 'exit_ts': exit_ts,
                'exit_px': exit_px, 'exit_reason': reason,
                'net_pnl_usd': ret * NOTIONAL - FEE,
            }

    status = 'NO_CONFIRMATION' if activated else 'ZONE_NOT_REACHED'
    return {
        **base, 'status': status, 'activated': activated,
        'activation_bar_start': q.index[activation_k] if activation_k is not None else pd.NaT,
        'activation_ts': activation_ts, 'confirmed': False, 'confirmation_bar_start': pd.NaT,
        'confirmation_ts': pd.NaT, 'confirmation_close': np.nan, 'prior_bar_high_at_confirm': np.nan,
        'pullback_low': pullback_low, 'pullback_low_fraction': ((pullback_low-L)/rng if activated else np.nan),
        'filled': False, 'entry_ts': pd.NaT, 'entry_px': np.nan,
        'stop_px': pullback_low if activated else np.nan, 'target_px': H,
        'nominal_rr': np.nan, 'exit_ts': pd.NaT, 'exit_px': np.nan,
        'exit_reason': status, 'net_pnl_usd': np.nan,
    }


def synthetic_tests():
    idx = pd.date_range('2026-01-01 13:35', periods=5, freq='5min', tz='UTC')
    q = pd.DataFrame([
        {'open': 99.0, 'high': 99.2, 'low': 97.5, 'close': 98.0},   # activate Z80=98, no confirm same bar
        {'open': 98.0, 'high': 98.4, 'low': 97.0, 'close': 97.6},   # deepen pullback
        {'open': 97.6, 'high': 99.0, 'low': 97.4, 'close': 98.8},   # reclaim: close >=98 and > prior high 98.4
        {'open': 98.7, 'high': 100.0, 'low': 98.5, 'close': 99.8},  # entry next open, TP
        {'open': 99.8, 'high': 100.2, 'low': 99.0, 'close': 100.1},
    ], index=idx)
    fake = pd.Series({
        'signal_id': 'x', 'partition': 'external', 'date_utc': '2026-01-01', 'k': 1,
        'signal_ts': idx[0], 'signal_bar_start': idx[0]-BAR5,
        'active_session_end': idx[-1]+BAR5, 'structural_outcome': 'TARGET_BREAK',
        'previous_session_high': 100.0, 'previous_session_low': 90.0,
    })
    # Embed q into an x5 that also has the session-end bar for time-exit safety.
    x5 = q.copy()
    x5.loc[idx[-1]+BAR5] = {'open': 100.0, 'high': 100.0, 'low': 100.0, 'close': 100.0}
    r = simulate_one(x5.sort_index(), fake, 'Z80')
    assert r['activated'] and r['confirmed'] and r['filled']
    assert pd.Timestamp(r['activation_bar_start']) == idx[0]
    assert pd.Timestamp(r['confirmation_bar_start']) == idx[2]
    assert pd.Timestamp(r['entry_ts']) == idx[3]
    assert abs(float(r['pullback_low']) - 97.0) < 1e-12
    assert r['exit_reason'] == 'TP_PREV_HIGH'

    # Strict close break before confirmation must kill the setup.
    q2 = pd.DataFrame([
        {'open': 99.0, 'high': 99.2, 'low': 97.5, 'close': 98.0},
        {'open': 98.0, 'high': 100.5, 'low': 97.8, 'close': 100.2},
    ], index=idx[:2])
    x52 = q2.copy()
    fake2 = fake.copy(); fake2['active_session_end'] = idx[2]
    r2 = simulate_one(x52, fake2, 'Z80')
    assert r2['status'] == 'TARGET_BROKE_BEFORE_CONFIRMATION' and not r2['filled']

    # Same entry bar touches both stop and target -> conservative stop.
    q3 = pd.DataFrame([
        {'open': 98.0, 'high': 100.1, 'low': 96.9, 'close': 99.0},
    ], index=idx[:1])
    s3 = resolve_trade(q3, 0, 98.0, 97.0, 100.0)
    assert s3[2] == 'SL_SAME_5M_CONSERVATIVE'


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def summarize(g: pd.DataFrame) -> dict:
    n = len(g)
    act = g[g.activated.astype(bool)] if n else g
    conf = g[g.confirmed.astype(bool)] if n else g
    tr = g[g.filled.astype(bool)].copy() if n else g
    x = pd.to_numeric(tr.net_pnl_usd, errors='coerce').dropna() if len(tr) else pd.Series(dtype=float)
    tr_res = tr.loc[x.index] if len(x) else tr.iloc[0:0]
    return {
        'setups': int(n),
        'activations': int(len(act)),
        'activation_rate': float(len(act)/n) if n else np.nan,
        'confirmations': int(len(conf)),
        'confirmation_rate': float(len(conf)/n) if n else np.nan,
        'trades': int(len(x)),
        'wins': int((x > 0).sum()),
        'losses': int((x <= 0).sum()),
        'wr': float((x > 0).mean()) if len(x) else np.nan,
        'tp_rate': float((tr_res.exit_reason == 'TP_PREV_HIGH').mean()) if len(x) else np.nan,
        'pf': pf(x),
        'net_exp': float(x.mean()) if len(x) else np.nan,
        'total_net': float(x.sum()) if len(x) else np.nan,
        'median_rr': float(tr_res.nominal_rr.median()) if len(x) else np.nan,
        'median_pullback_low_fraction': float(conf.pullback_low_fraction.median()) if len(conf) else np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.2f}'


def audit_real(t: pd.DataFrame, s: pd.DataFrame):
    # Exactly one row per frozen signal x zone.
    assert len(t) == len(s) * len(ZONES)
    for zone_name, frac in ZONES.items():
        g = t[t.zone_name == zone_name]
        assert len(g) == len(s)
        assert np.allclose(g.zone_fraction.astype(float), frac)
    # Identity preserved.
    assert set(t.signal_id.unique()) == set(s.signal_id.unique())

    for r in t.itertuples(index=False):
        if bool(r.activated):
            assert pd.Timestamp(r.activation_ts) > pd.Timestamp(r.signal_ts)
        if bool(r.confirmed):
            assert pd.Timestamp(r.confirmation_ts) > pd.Timestamp(r.activation_ts)
            assert float(r.confirmation_close) + 1e-12 >= float(r.zone_px)
            assert float(r.confirmation_close) > float(r.prior_bar_high_at_confirm)
        if bool(r.filled):
            assert pd.Timestamp(r.entry_ts) == pd.Timestamp(r.confirmation_ts)
            assert float(r.pullback_low) < float(r.entry_px) < float(r.target_px)
            assert abs(float(r.stop_px) - float(r.pullback_low)) < 1e-10
            assert float(r.nominal_rr) > 0


def main():
    synthetic_tests()
    x5, coverage = b21.load5()
    s = load_signals()
    rows = []
    for _, sig in s.iterrows():
        for zone_name in ZONES:
            rows.append(simulate_one(x5, sig, zone_name))
    t = pd.DataFrame(rows)
    audit_real(t, s)
    t.to_csv(OUT_TRADES, index=False)

    sums = []
    for part in PARTS:
        for k in KS:
            for zone_name in ZONES:
                g = t[(t.partition == part) & (t.k == k) & (t.zone_name == zone_name)]
                sums.append({'partition': part, 'k': k, 'zone_name': zone_name, **summarize(g)})
    sm = pd.DataFrame(sums)

    passes = {}
    for zone_name in ZONES:
        z = sm[(sm.k == 1) & (sm.zone_name == zone_name) & (sm.partition.isin(MAJOR))]
        passes[zone_name] = bool(
            len(z) == 3 and (z.trades >= 30).all() and (z.net_exp > 0).all() and (z.pf >= 1.20).all()
        )
    sm['screen_pass'] = [passes[r.zone_name] if r.k == 1 else False for r in sm.itertuples(index=False)]
    sm.to_csv(OUT_SUM, index=False)
    t.status.value_counts(dropna=False).rename_axis('status').reset_index(name='n').to_csv(OUT_STATUS, index=False)

    md = [
        '# B27V — London -> New York Pullback Reclaim Entry — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        '**Audit status: PASS.** B27Q K1/K2 OPP0 signal identities are unchanged; entry waits for causal 5m pullback-reclaim confirmation and uses the frozen pre-entry pullback low as stop.', '',
        '## Primary K1 OPP0', '',
        '| Partition | Zone | Setups | Activated | Confirmed | Trades | WR | TP rate | PF | Net exp | Total net | Median RR | Median PB-low f |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in sm[sm.k == 1].itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.zone_name} | {r.setups} | {r.activations} ({pct(r.activation_rate)}) | '
            f'{r.confirmations} ({pct(r.confirmation_rate)}) | {r.trades} | {pct(r.wr)} | {pct(r.tp_rate)} | '
            f'{num(r.pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {num(r.median_rr)} | {num(r.median_pullback_low_fraction)} |'
        )
    md += ['', '## Screen', '']
    good = [z for z, ok in passes.items() if ok]
    md.append('**PASS:** ' + ', '.join(good) if good else '**No K1 zone passed the frozen three-partition screen.**')

    md += ['', '## Secondary K2 diagnostic', '',
           '| Partition | Zone | Trades | WR | TP rate | PF | Net exp | Total net | Median RR |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm[sm.k == 2].itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.zone_name} | {r.trades} | {pct(r.wr)} | {pct(r.tp_rate)} | '
            f'{num(r.pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {num(r.median_rr)} |'
        )
    md += ['', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
