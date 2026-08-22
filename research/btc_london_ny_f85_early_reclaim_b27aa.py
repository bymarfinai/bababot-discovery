#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_CSV = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
WINDOWS_CSV = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Summary.csv'
OUT_SELECT = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_Selection.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_F85_EARLY_RECLAIM_B27AA_StatusCounts.csv'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
VARIANTS = ('EARLY_RECLAIM','SAME_BAR_REJECTION')
ENTRY_F = 0.85
STOP_F = 0.35
TARGET_EXT = 0.20
NOTIONAL = 500.0
FEE = 0.40


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_source() -> pd.DataFrame:
    e = pd.read_csv(ENTRIES_CSV)
    e = e[(e.entry_name == 'F85') & (e.filled.astype(str).str.lower() == 'true')].copy()
    for c in ('signal_ts','eligible_start','h2_bar_start','opposite_break_bar_start','entry_ts'):
        e[c] = pd.to_datetime(e[c], utc=True, errors='coerce')

    w = pd.read_csv(WINDOWS_CSV)
    for c in ('signal_ts','session_end','h2_bar_start'):
        w[c] = pd.to_datetime(w[c], utc=True, errors='coerce')
    w = w[['partition','date_utc','signal_ts','session_end','h2_bar_start']].copy()

    z = e.merge(w, on=['partition','date_utc','signal_ts'], how='left', suffixes=('_entry','_window'), validate='many_to_one')
    assert z.session_end.notna().all()
    a = pd.to_datetime(z.h2_bar_start_entry, utc=True, errors='coerce')
    b = pd.to_datetime(z.h2_bar_start_window, utc=True, errors='coerce')
    same = (a.isna() & b.isna()) | (a == b)
    assert bool(same.all())
    z['h2_bar_start'] = b
    z = z.sort_values(['partition','entry_ts','signal_ts']).reset_index(drop=True)

    # B27W F85 identity must be unique per signal opportunity.
    assert not z.duplicated(['partition','date_utc','signal_ts']).any()
    return z


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def time_exit(x5: pd.DataFrame, session_end: pd.Timestamp):
    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5):
        return None
    ts = x5.index[pos]
    return ts, float(x5.iloc[pos].open), 'TIME_EXIT_SESSION_END'


def confirm_and_trade(x5: pd.DataFrame, r: pd.Series, variant: str) -> dict:
    H = float(r.H)
    L = float(r.L)
    rng = H - L
    f85 = L + ENTRY_F * rng
    boundary = L + STOP_F * rng
    target = H + TARGET_EXT * rng
    touch_ts = pd.Timestamp(r.entry_ts)
    session_end = pd.Timestamp(r.session_end)
    frozen_h2 = pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT

    base = {
        'partition': r.partition,
        'date_utc': r.date_utc,
        'signal_ts': pd.Timestamp(r.signal_ts),
        'variant': variant,
        'H': H,
        'L': L,
        'range': rng,
        'F85': f85,
        'F35': boundary,
        'E20': target,
        'touch_bar_start': touch_ts,
        'frozen_h2_bar_start': frozen_h2,
        'session_end': session_end,
    }

    q = fast_slice(x5, touch_ts, session_end)
    if q.empty or q.index[0] != touch_ts:
        raise AssertionError('missing B27W F85 touch bar')
    touch_bar = q.iloc[0]
    if not (float(touch_bar.low) <= f85 <= float(touch_bar.high)):
        raise AssertionError('B27W F85 touch does not reproduce on raw 5m')

    confirmation_bar_start = pd.NaT
    confirmation_ts = pd.NaT
    confirmation_close = np.nan
    confirmation_kind = None
    status = None

    max_k = 1 if variant == 'SAME_BAR_REJECTION' else len(q)
    for k in range(max_k):
        ts = q.index[k]
        bar = q.iloc[k]
        high = float(bar.high)
        close = float(bar.close)

        # A bar that reaches H is already H2 before its completed close can confirm.
        if high >= H:
            status = 'H2_BEFORE_CONFIRMATION'
            break
        if close < L:
            status = 'LOW_CLOSE_BREAK_BEFORE_CONFIRMATION'
            break
        if close > f85:
            confirmation_bar_start = ts
            confirmation_ts = ts + BAR5
            confirmation_close = close
            confirmation_kind = 'SAME_BAR' if k == 0 else 'LATER_RECLAIM'
            status = 'CONFIRMED'
            break

    if status is None:
        status = 'NO_CONFIRMATION' if variant == 'SAME_BAR_REJECTION' else 'NO_CONFIRMATION_BY_SESSION_END'

    no_trade = {
        **base,
        'confirmation_status': status,
        'confirmation_kind': confirmation_kind,
        'confirmation_bar_start': confirmation_bar_start,
        'confirmation_ts': confirmation_ts,
        'confirmation_close': confirmation_close,
        'minutes_touch_to_confirmation': np.nan if pd.isna(confirmation_ts) else float((confirmation_ts - touch_ts) / pd.Timedelta(minutes=1)),
        'entry_executed': False,
        'entry_bar_start': pd.NaT,
        'entry_px': np.nan,
        'entry_fraction': np.nan,
        'entry_on_frozen_h2_bar_open': False,
        'nominal_rr': np.nan,
        'exit_bar_start': pd.NaT,
        'exit_ts': pd.NaT,
        'exit_px': np.nan,
        'exit_reason': status,
        'gross_return': np.nan,
        'net_pnl_usd': np.nan,
        'hold_minutes': np.nan,
        'h2_before_exit': False,
        'accepted_close_above_H_before_exit': False,
    }

    if status != 'CONFIRMED':
        return no_trade

    # Confirmation must strictly precede frozen H2 if B27W observed one.
    if pd.notna(frozen_h2) and not (confirmation_bar_start < frozen_h2):
        raise AssertionError('confirmation is not strictly before frozen H2 bar')
    if not (confirmation_close > f85):
        raise AssertionError('confirmation close is not above F85')

    entry_start = pd.Timestamp(confirmation_ts)
    if entry_start >= session_end:
        return {**no_trade, 'confirmation_status':'CONFIRMED_NO_NEXT_BAR', 'exit_reason':'CONFIRMED_NO_NEXT_BAR'}

    pos = int(x5.index.searchsorted(entry_start, side='left'))
    if pos >= len(x5) or x5.index[pos] != entry_start:
        raise AssertionError('missing next 5m entry bar')
    entry_px = float(x5.iloc[pos].open)

    # If the next bar opens at/above H, the second arrival has already happened at the open.
    if entry_px >= H:
        return {
            **no_trade,
            'confirmation_status':'MISSED_H2_AT_OPEN',
            'confirmation_kind':confirmation_kind,
            'confirmation_bar_start':confirmation_bar_start,
            'confirmation_ts':confirmation_ts,
            'confirmation_close':confirmation_close,
            'minutes_touch_to_confirmation':float((confirmation_ts-touch_ts)/pd.Timedelta(minutes=1)),
            'entry_bar_start':entry_start,
            'exit_reason':'MISSED_H2_AT_OPEN',
        }

    if not (boundary < entry_px < H):
        return {
            **no_trade,
            'confirmation_status':'INVALID_ENTRY_GEOMETRY',
            'confirmation_kind':confirmation_kind,
            'confirmation_bar_start':confirmation_bar_start,
            'confirmation_ts':confirmation_ts,
            'confirmation_close':confirmation_close,
            'minutes_touch_to_confirmation':float((confirmation_ts-touch_ts)/pd.Timedelta(minutes=1)),
            'entry_bar_start':entry_start,
            'entry_px':entry_px,
            'entry_fraction':(entry_px-L)/rng,
            'exit_reason':'INVALID_ENTRY_GEOMETRY',
        }

    # If frozen H2 is earlier than entry open, chronology is broken. Equality is allowed: open precedes intrabar H2.
    if pd.notna(frozen_h2) and frozen_h2 < entry_start:
        raise AssertionError('entry occurs after frozen H2')

    entry_frac = (entry_px - L) / rng
    nominal_rr = (target - entry_px) / (entry_px - boundary)

    eq = fast_slice(x5, entry_start, session_end)
    if eq.empty or eq.index[0] != entry_start:
        raise AssertionError('empty execution slice')

    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    exit_reason = None
    h2_seen = False
    accepted = False

    for ts, bar in eq.iterrows():
        high = float(bar.high)
        close = float(bar.close)

        # Entry is at bar open, so any later intrabar H2/TP is causal.
        if high >= H:
            h2_seen = True

        # Resting E20 target is evaluated before a close-based invalidation from the same bar.
        if high >= target:
            exit_bar_start = ts
            exit_ts = ts
            exit_px = target
            exit_reason = 'TP_E20'
            break

        if close < boundary:
            exit_bar_start = ts
            exit_ts = ts + BAR5
            exit_px = close
            exit_reason = 'CLOSE_INVALIDATION_F35'
            break

        if close > H:
            accepted = True

    if exit_reason is None:
        te = time_exit(x5, session_end)
        if te is None:
            return {
                **base,
                'confirmation_status':'CONFIRMED_EXECUTED',
                'confirmation_kind':confirmation_kind,
                'confirmation_bar_start':confirmation_bar_start,
                'confirmation_ts':confirmation_ts,
                'confirmation_close':confirmation_close,
                'minutes_touch_to_confirmation':float((confirmation_ts-touch_ts)/pd.Timedelta(minutes=1)),
                'entry_executed':True,
                'entry_bar_start':entry_start,
                'entry_px':entry_px,
                'entry_fraction':entry_frac,
                'entry_on_frozen_h2_bar_open':bool(pd.notna(frozen_h2) and entry_start == frozen_h2),
                'nominal_rr':nominal_rr,
                'exit_bar_start':pd.NaT,
                'exit_ts':pd.NaT,
                'exit_px':np.nan,
                'exit_reason':'CENSORED',
                'gross_return':np.nan,
                'net_pnl_usd':np.nan,
                'hold_minutes':np.nan,
                'h2_before_exit':h2_seen,
                'accepted_close_above_H_before_exit':accepted,
            }
        exit_ts, exit_px, exit_reason = te
        exit_bar_start = exit_ts

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    hold = float((pd.Timestamp(exit_ts) - entry_start) / pd.Timedelta(minutes=1))

    return {
        **base,
        'confirmation_status':'CONFIRMED_EXECUTED',
        'confirmation_kind':confirmation_kind,
        'confirmation_bar_start':confirmation_bar_start,
        'confirmation_ts':confirmation_ts,
        'confirmation_close':confirmation_close,
        'minutes_touch_to_confirmation':float((confirmation_ts-touch_ts)/pd.Timedelta(minutes=1)),
        'entry_executed':True,
        'entry_bar_start':entry_start,
        'entry_px':entry_px,
        'entry_fraction':entry_frac,
        'entry_on_frozen_h2_bar_open':bool(pd.notna(frozen_h2) and entry_start == frozen_h2),
        'nominal_rr':nominal_rr,
        'exit_bar_start':exit_bar_start,
        'exit_ts':exit_ts,
        'exit_px':float(exit_px),
        'exit_reason':exit_reason,
        'gross_return':gross,
        'net_pnl_usd':net,
        'hold_minutes':hold,
        'h2_before_exit':bool(h2_seen),
        'accepted_close_above_H_before_exit':bool(accepted),
    }


def synthetic_tests():
    idx = pd.date_range('2026-01-02 13:30', periods=10, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    f85 = 98.5

    def src(h2=idx[3], end=idx[9]):
        return pd.Series({
            'partition':'x','date_utc':'2026-01-02','signal_ts':idx[0]-BAR5,
            'entry_ts':idx[0],'entry_px':f85,'H':H,'L':L,
            'session_end':end,'h2_bar_start':h2,
        })

    # Same-bar rejection: F85 touch closes back above F85; next-open entry.
    x = pd.DataFrame([
        {'open':99.0,'high':99.2,'low':98.2,'close':98.8},
        {'open':98.9,'high':99.3,'low':98.7,'close':99.1},
        {'open':99.1,'high':99.7,'low':99.0,'close':99.5},
        {'open':99.5,'high':100.1,'low':99.4,'close':100.0},
        {'open':100.0,'high':102.2,'low':99.9,'close':101.5},
        {'open':101.5,'high':101.7,'low':101.0,'close':101.2},
        {'open':101.2,'high':101.5,'low':101.0,'close':101.1},
        {'open':101.1,'high':101.2,'low':100.8,'close':101.0},
        {'open':101.0,'high':101.1,'low':100.8,'close':101.0},
        {'open':101.0,'high':101.0,'low':101.0,'close':101.0},
    ], index=idx)
    z = confirm_and_trade(x, src(), 'EARLY_RECLAIM')
    assert z['confirmation_kind'] == 'SAME_BAR'
    assert z['entry_bar_start'] == idx[1]
    assert z['exit_reason'] == 'TP_E20'

    # Later reclaim: touch bar closes below F85, next bar reclaims, entry on following open.
    x2 = x.copy()
    x2.loc[idx[0], 'close'] = 98.3
    x2.loc[idx[1], ['open','high','low','close']] = [98.3, 99.0, 98.0, 98.7]
    z2 = confirm_and_trade(x2, src(), 'EARLY_RECLAIM')
    assert z2['confirmation_kind'] == 'LATER_RECLAIM' and z2['entry_bar_start'] == idx[2]

    # H2 before confirmation: no entry.
    x3 = x2.copy()
    x3.loc[idx[1], ['high','close']] = [100.1, 98.2]
    r3 = src(h2=idx[1])
    z3 = confirm_and_trade(x3, r3, 'EARLY_RECLAIM')
    assert not z3['entry_executed'] and z3['confirmation_status'] == 'H2_BEFORE_CONFIRMATION'

    # Entry at H2 bar open is valid when open < H; open chronologically precedes intrabar H2.
    x4 = x.copy()
    r4 = src(h2=idx[1])
    x4.loc[idx[1], ['open','high','close']] = [99.0, 100.2, 100.0]
    z4 = confirm_and_trade(x4, r4, 'EARLY_RECLAIM')
    assert z4['entry_executed'] and z4['entry_on_frozen_h2_bar_open']

    # But a gap open at/above H means H2 already arrived at the open; skip.
    x5 = x.copy()
    r5 = src(h2=idx[1])
    x5.loc[idx[1], ['open','high','low','close']] = [100.1, 100.4, 99.9, 100.2]
    z5 = confirm_and_trade(x5, r5, 'EARLY_RECLAIM')
    assert not z5['entry_executed'] and z5['confirmation_status'] == 'MISSED_H2_AT_OPEN'

    # Wick below F35 but close above survives; TP later.
    x6 = x.copy()
    x6.loc[idx[1], ['low','close']] = [92.0, 96.0]
    z6 = confirm_and_trade(x6, src(), 'EARLY_RECLAIM')
    assert z6['exit_reason'] == 'TP_E20'

    # Target and close invalidation same bar: resting target wins because stop is only known at close.
    x7 = x.copy()
    x7.loc[idx[2], ['high','low','close']] = [102.2, 92.0, 93.0]
    z7 = confirm_and_trade(x7, src(), 'EARLY_RECLAIM')
    assert z7['exit_reason'] == 'TP_E20'

    # SAME_BAR_REJECTION does not wait for later reclaim.
    z8 = confirm_and_trade(x2, src(), 'SAME_BAR_REJECTION')
    assert not z8['entry_executed'] and z8['confirmation_status'] == 'NO_CONFIRMATION'


def summarize(g: pd.DataFrame) -> dict:
    original = len(g)
    confirmed = int(g.confirmation_kind.notna().sum())
    executed = g[g.entry_executed.astype(bool)].copy()
    x = pd.to_numeric(executed.net_pnl_usd, errors='coerce').dropna()
    resolved = executed.loc[x.index].copy()
    return {
        'opportunities': int(original),
        'confirmed': confirmed,
        'confirmation_rate': float(confirmed / original) if original else np.nan,
        'executed_trades': int(len(x)),
        'execution_rate': float(len(x) / original) if original else np.nan,
        'same_bar_confirmed': int((g.confirmation_kind == 'SAME_BAR').sum()),
        'later_reclaim_confirmed': int((g.confirmation_kind == 'LATER_RECLAIM').sum()),
        'median_touch_to_confirmation_min': float(g.loc[g.confirmation_kind.notna(),'minutes_touch_to_confirmation'].median()) if confirmed else np.nan,
        'entry_on_h2_bar_open_count': int(resolved.entry_on_frozen_h2_bar_open.sum()) if len(resolved) else 0,
        'tp_count': int((resolved.exit_reason == 'TP_E20').sum()),
        'tp_rate': float((resolved.exit_reason == 'TP_E20').mean()) if len(resolved) else np.nan,
        'close_invalidation_count': int((resolved.exit_reason == 'CLOSE_INVALIDATION_F35').sum()),
        'time_exit_count': int((resolved.exit_reason == 'TIME_EXIT_SESSION_END').sum()),
        'wr': float((x > 0).mean()) if len(x) else np.nan,
        'pf': pf(x),
        'net_exp': float(x.mean()) if len(x) else np.nan,
        'total_net': float(x.sum()) if len(x) else np.nan,
        'h2_before_exit_rate': float(resolved.h2_before_exit.mean()) if len(resolved) else np.nan,
        'accept_close_before_exit_rate': float(resolved.accepted_close_above_H_before_exit.mean()) if len(resolved) else np.nan,
        'median_entry_fraction': float(resolved.entry_fraction.median()) if len(resolved) else np.nan,
        'median_nominal_rr': float(resolved.nominal_rr.median()) if len(resolved) else np.nan,
        'median_hold_minutes': float(resolved.hold_minutes.median()) if len(resolved) else np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.2f}'


def main():
    synthetic_tests()
    x5, coverage = b21.load5()
    src = load_source()

    rows = []
    for _, r in src.iterrows():
        for variant in VARIANTS:
            rows.append(confirm_and_trade(x5, r, variant))
    t = pd.DataFrame(rows)

    # Exact Cartesian identity: two confirmation variants per frozen B27W F85 opportunity.
    assert len(t) == len(src) * len(VARIANTS)
    key = ['partition','date_utc','signal_ts','touch_bar_start']
    assert (t.groupby(key, dropna=False).size() == len(VARIANTS)).all()

    # Mandatory real-data chronology / geometry assertions.
    for r in t.itertuples(index=False):
        rng = float(r.H - r.L)
        exp_f85 = float(r.L) + ENTRY_F * rng
        exp_f35 = float(r.L) + STOP_F * rng
        exp_e20 = float(r.H) + TARGET_EXT * rng
        assert abs(float(r.F85) - exp_f85) < 1e-9 * max(1.0, abs(exp_f85))
        assert abs(float(r.F35) - exp_f35) < 1e-9 * max(1.0, abs(exp_f35))
        assert abs(float(r.E20) - exp_e20) < 1e-9 * max(1.0, abs(exp_e20))
        raw_touch = x5.loc[pd.Timestamp(r.touch_bar_start)]
        assert float(raw_touch.low) <= float(r.F85) <= float(raw_touch.high)
        if pd.notna(r.confirmation_bar_start):
            cb = x5.loc[pd.Timestamp(r.confirmation_bar_start)]
            assert float(cb.close) > float(r.F85)
            if pd.notna(r.frozen_h2_bar_start):
                assert pd.Timestamp(r.confirmation_bar_start) < pd.Timestamp(r.frozen_h2_bar_start)
        if bool(r.entry_executed):
            assert pd.Timestamp(r.entry_bar_start) == pd.Timestamp(r.confirmation_ts)
            eb = x5.loc[pd.Timestamp(r.entry_bar_start)]
            assert abs(float(r.entry_px) - float(eb.open)) < 1e-12 * max(1.0, abs(float(eb.open)))
            assert float(r.F35) < float(r.entry_px) < float(r.H)
            if pd.notna(r.frozen_h2_bar_start):
                assert pd.Timestamp(r.entry_bar_start) <= pd.Timestamp(r.frozen_h2_bar_start)
                if pd.Timestamp(r.entry_bar_start) == pd.Timestamp(r.frozen_h2_bar_start):
                    assert float(r.entry_px) < float(r.H)
        if str(r.exit_reason) == 'CLOSE_INVALIDATION_F35':
            raw = x5.loc[pd.Timestamp(r.exit_bar_start)]
            assert float(raw.close) < float(r.F35)
            assert abs(float(r.exit_px) - float(raw.close)) < 1e-12 * max(1.0, abs(float(raw.close)))
        if str(r.exit_reason) == 'TP_E20':
            raw = x5.loc[pd.Timestamp(r.exit_bar_start)]
            assert float(raw.high) >= float(r.E20)
            assert abs(float(r.exit_px) - float(r.E20)) < 1e-9 * max(1.0, abs(float(r.E20)))

    sums = []
    for part in PARTS:
        for variant in VARIANTS:
            g = t[(t.partition == part) & (t.variant == variant)]
            sums.append({'partition':part, 'variant':variant, **summarize(g)})
    sm = pd.DataFrame(sums)

    # Frozen screen only on EARLY_RECLAIM.
    gate_rows = []
    passed = True
    for part in MAJOR:
        r = sm[(sm.partition == part) & (sm.variant == 'EARLY_RECLAIM')].iloc[0]
        ok = bool(r.executed_trades >= 30 and r.wr >= 0.70 and r.pf >= 1.20 and r.net_exp > 0)
        gate_rows.append({'partition':part,'executed_trades':int(r.executed_trades),'wr':float(r.wr),'pf':float(r.pf),'net_exp':float(r.net_exp),'pass':ok})
        passed = passed and ok
    sel = pd.DataFrame(gate_rows)
    sel['overall_pass'] = bool(passed)

    status = t.groupby(['partition','variant','confirmation_status'], dropna=False).size().reset_index(name='count')

    t.to_csv(OUT_TRADES, index=False)
    sm.to_csv(OUT_SUM, index=False)
    sel.to_csv(OUT_SELECT, index=False)
    status.to_csv(OUT_STATUS, index=False)

    lines = [
        '# B27AA — London -> New York Early F85 Rejection / Reclaim Filter — Result',
        '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.',
        '',
        '**Audit status: PASS.** B27W F85 touch opportunities are frozen; B27AA only changes blind F85 execution into the earliest causal 5m reclaim entry. Exit economics are frozen to E20 + F35 close-invalidation.',
        '',
        '## Results',
        '',
        '| Partition | Variant | Opportunities | Confirmed | Executed | Exec rate | Same-bar | Later | TP rate | WR | PF | Net exp | Total net | H2 before exit | Median entry f | Median RR |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in sm.iterrows():
        lines.append(
            f"| {r.partition} | {r.variant} | {int(r.opportunities)} | {int(r.confirmed)} | {int(r.executed_trades)} | {pct(r.execution_rate)} | "
            f"{int(r.same_bar_confirmed)} | {int(r.later_reclaim_confirmed)} | {pct(r.tp_rate)} | {pct(r.wr)} | {num(r.pf)} | ${float(r.net_exp):.2f} | ${float(r.total_net):.2f} | "
            f"{pct(r.h2_before_exit_rate)} | {float(r.median_entry_fraction):.3f} | {float(r.median_nominal_rr):.2f} |"
        )

    lines += ['', '## Frozen EARLY_RECLAIM screen', '']
    for _, r in sel.iterrows():
        lines.append(f"- {r.partition}: N={int(r.executed_trades)}, WR={pct(r.wr)}, PF={num(r.pf)}, exp=${float(r.net_exp):.2f} -> {'PASS' if bool(r['pass']) else 'FAIL'}")
    lines += ['', f"**Overall: {'SCREEN_PASS' if passed else 'NO_PASS'}.**", '']

    # Pairwise incremental view versus SAME_BAR subset is descriptive only.
    lines += [
        '## Interpretation guardrail',
        '',
        'B27AA does not retune F85, E20, or F35 after seeing these results. SAME_BAR_REJECTION is a diagnostic subset only. If EARLY_RECLAIM fails the frozen major-partition gate, this experiment does not authorize F84/F86, candle-shape thresholds, or extra indicator mining.',
        '',
        'Research only; live BBC unchanged.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
