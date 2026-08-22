#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Result.md'
OUT_WINDOWS = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Windows.csv'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
RULES = ('BLIND_F15', 'EARLY_REJECT', 'SAME_BAR_REJECTION')
ENTRY_F = 0.15
STOP_F = 0.65
TARGET_EXT = 0.20
NOTIONAL = 500.0
FEE = 0.40


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def load_k1() -> pd.DataFrame:
    s = pd.read_csv(SIGNALS)
    s = s[(s.transition == 'LONDON_TO_NEWYORK') &
          (s.side == 'SHORT') &
          (pd.to_numeric(s.k) == 1) &
          (pd.to_numeric(s.opp_visits_at_signal) == 0)].copy()
    for c in ('signal_ts', 'signal_bar_start', 'active_session_end'):
        s[c] = pd.to_datetime(s[c], utc=True, errors='raise')
    assert len(s) > 0
    return s.sort_values(['partition', 'signal_ts']).reset_index(drop=True)


def qualifies_low_touch(r, L: float) -> bool:
    return float(r.low) <= L and float(r.close) >= L


def base_window(s, H, L, same_episode_bars, status, leave_bar_start, leave_ts,
                eligible_start, h2_bar_start, h2_ts, opp_bar_start, opp_ts,
                terminal_bar_start=pd.NaT) -> dict:
    return {
        'partition': s.partition,
        'date_utc': s.date_utc,
        'signal_bar_start': pd.Timestamp(s.signal_bar_start),
        'signal_ts': pd.Timestamp(s.signal_ts),
        'session_end': pd.Timestamp(s.active_session_end),
        'H': H, 'L': L, 'range': H - L,
        'k1_episode_bars': int(same_episode_bars),
        'window_status': status,
        'leave_bar_start': leave_bar_start,
        'leave_ts': leave_ts,
        'eligible_start': eligible_start,
        'h2_bar_start': h2_bar_start,
        'h2_ts': h2_ts,
        'opposite_break_bar_start': opp_bar_start,
        'opposite_break_ts': opp_ts,
        'terminal_bar_start': terminal_bar_start,
    }


def build_window(x5: pd.DataFrame, s: pd.Series) -> dict:
    H = float(s.previous_session_high)
    L = float(s.previous_session_low)
    sig_start = pd.Timestamp(s.signal_bar_start)
    sig_ts = pd.Timestamp(s.signal_ts)
    end = pd.Timestamp(s.active_session_end)
    assert H > L

    q = fast_slice(x5, sig_start, end)
    if q.empty or q.index[0] != sig_start:
        raise AssertionError('missing K1 signal bar')
    r0 = q.iloc[0]
    if not (qualifies_low_touch(r0, L) and float(r0.close) <= H):
        raise AssertionError('B27Q SHORT K1 bar does not reproduce first Low touch')
    if sig_ts != sig_start + BAR5:
        raise AssertionError('unexpected K1 signal timestamp geometry')

    leave_bar_start = pd.NaT
    leave_ts = pd.NaT
    eligible_start = pd.NaT
    same_episode_bars = 1
    leave_pos = None

    for k in range(1, len(q)):
        ts = q.index[k]
        r = q.iloc[k]
        c = float(r.close)
        if c < L:
            return base_window(s, H, L, same_episode_bars,
                               'NO_WINDOW_LOW_BREAK_DURING_K1',
                               leave_bar_start, leave_ts, eligible_start,
                               pd.NaT, pd.NaT, pd.NaT, pd.NaT)
        if c > H:
            return base_window(s, H, L, same_episode_bars,
                               'NO_WINDOW_HIGH_BREAK_DURING_K1',
                               leave_bar_start, leave_ts, eligible_start,
                               pd.NaT, pd.NaT, pd.NaT, pd.NaT)
        if qualifies_low_touch(r, L):
            same_episode_bars += 1
            continue
        leave_bar_start = ts
        leave_ts = ts + BAR5
        eligible_start = leave_ts
        leave_pos = k
        break

    if leave_pos is None:
        return base_window(s, H, L, same_episode_bars,
                           'NO_CAUSAL_LEAVE_BY_SESSION_END',
                           leave_bar_start, leave_ts, eligible_start,
                           pd.NaT, pd.NaT, pd.NaT, pd.NaT)

    h2_bar_start = pd.NaT
    h2_ts = pd.NaT
    opp_bar_start = pd.NaT
    opp_ts = pd.NaT
    terminal_bar_start = pd.NaT
    status = 'NO_H2_BY_SESSION_END'

    for k in range(leave_pos + 1, len(q)):
        ts = q.index[k]
        r = q.iloc[k]
        hit_l = float(r.low) <= L
        break_h = float(r.close) > H
        if hit_l and break_h:
            status = 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK'
            terminal_bar_start = ts
            break
        if hit_l:
            h2_bar_start = ts
            h2_ts = ts + BAR5
            terminal_bar_start = ts
            status = 'H2_ARRIVAL'
            break
        if break_h:
            opp_bar_start = ts
            opp_ts = ts + BAR5
            terminal_bar_start = ts
            status = 'OPPOSITE_BREAK_BEFORE_H2'
            break

    return base_window(s, H, L, same_episode_bars, status,
                       leave_bar_start, leave_ts, eligible_start,
                       h2_bar_start, h2_ts, opp_bar_start, opp_ts,
                       terminal_bar_start)


def terminal_start(w: pd.Series) -> pd.Timestamp:
    if w.window_status == 'H2_ARRIVAL':
        return pd.Timestamp(w.h2_bar_start)
    if w.window_status == 'OPPOSITE_BREAK_BEFORE_H2':
        return pd.Timestamp(w.opposite_break_bar_start)
    if w.window_status == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK':
        return pd.Timestamp(w.terminal_bar_start)
    return pd.Timestamp(w.session_end)


def blind_f15(x5: pd.DataFrame, w: pd.Series) -> dict:
    H = float(w.H); L = float(w.L); rng = H - L
    f15 = L + ENTRY_F * rng
    base = {
        'partition': w.partition, 'date_utc': w.date_utc,
        'signal_ts': pd.Timestamp(w.signal_ts), 'window_status': w.window_status,
        'H': H, 'L': L, 'range': rng, 'F15': f15,
        'F65': L + STOP_F * rng, 'E20_DOWN': L - TARGET_EXT * rng,
        'eligible_start': w.eligible_start, 'h2_bar_start': w.h2_bar_start,
        'opposite_break_bar_start': w.opposite_break_bar_start,
        'session_end': pd.Timestamp(w.session_end),
    }
    if pd.isna(w.eligible_start) or str(w.window_status).startswith('NO_WINDOW') or w.window_status == 'NO_CAUSAL_LEAVE_BY_SESSION_END':
        return {**base, 'blind_filled': False, 'blind_touch_bar_start': pd.NaT,
                'blind_entry_px': np.nan, 'h2_after_fill': False,
                'minutes_fill_to_h2': np.nan, 'max_pre_h2_frac': np.nan,
                'adverse_excursion_r': np.nan}

    term = terminal_start(w)
    q = fast_slice(x5, pd.Timestamp(w.eligible_start), term)
    fill_ts = pd.NaT
    fill_pos = None
    for k, (ts, r) in enumerate(q.iterrows()):
        if float(r.low) <= L:
            raise AssertionError('H2 appeared inside pre-terminal eligible slice')
        if float(r.close) > H:
            raise AssertionError('opposite break appeared inside pre-terminal eligible slice')
        if float(r.low) <= f15 <= float(r.high):
            fill_ts = ts
            fill_pos = k
            break

    if fill_pos is None:
        return {**base, 'blind_filled': False, 'blind_touch_bar_start': pd.NaT,
                'blind_entry_px': np.nan, 'h2_after_fill': False,
                'minutes_fill_to_h2': np.nan, 'max_pre_h2_frac': np.nan,
                'adverse_excursion_r': np.nan}

    if not (pd.Timestamp(fill_ts) < term):
        raise AssertionError('blind F15 fill is not strictly before terminal/H2 bar')

    post = q.iloc[fill_pos:]
    max_high = float(post.high.max()) if len(post) else f15
    max_frac = (max_high - L) / rng
    adverse = max(0.0, max_frac - ENTRY_F)
    h2 = bool(w.window_status == 'H2_ARRIVAL')
    mins = float((pd.Timestamp(w.h2_bar_start) - pd.Timestamp(fill_ts)) /
                 pd.Timedelta(minutes=1)) if h2 else np.nan
    return {**base, 'blind_filled': True,
            'blind_touch_bar_start': pd.Timestamp(fill_ts),
            'blind_entry_px': f15, 'h2_after_fill': h2,
            'minutes_fill_to_h2': mins, 'max_pre_h2_frac': max_frac,
            'adverse_excursion_r': adverse}


def confirm_rejection_entry(x5: pd.DataFrame, b: pd.Series, same_bar_only: bool) -> dict:
    base = dict(b)
    variant = 'SAME_BAR_REJECTION' if same_bar_only else 'EARLY_REJECT'
    if not bool(b.blind_filled):
        return {**base, 'rule': variant, 'entry_executed': False,
                'confirmation_kind': None, 'confirmation_bar_start': pd.NaT,
                'entry_start': pd.NaT, 'entry_px': np.nan,
                'entry_fraction': np.nan, 'entry_on_h2_bar_open': False,
                'entry_status': 'NO_BLIND_F15_OPPORTUNITY'}

    touch = pd.Timestamp(b.blind_touch_bar_start)
    term = pd.Timestamp(b.h2_bar_start) if pd.notna(b.h2_bar_start) else (
        pd.Timestamp(b.opposite_break_bar_start) if pd.notna(b.opposite_break_bar_start)
        else pd.Timestamp(b.session_end))
    q = fast_slice(x5, touch, term)
    if q.empty or q.index[0] != touch:
        raise AssertionError('missing F15 touch bar')
    max_k = 1 if same_bar_only else len(q)
    confirm_bar = pd.NaT
    kind = None
    for k in range(max_k):
        ts = q.index[k]
        r = q.iloc[k]
        if float(r.low) <= float(b.L):
            raise AssertionError('H2 inside confirmation slice')
        if float(r.close) > float(b.H):
            raise AssertionError('opposite break inside confirmation slice')
        if float(r.close) < float(b.F15):
            confirm_bar = ts
            kind = 'SAME_BAR' if k == 0 else 'LATER_REJECT'
            break

    if pd.isna(confirm_bar):
        return {**base, 'rule': variant, 'entry_executed': False,
                'confirmation_kind': None, 'confirmation_bar_start': pd.NaT,
                'entry_start': pd.NaT, 'entry_px': np.nan,
                'entry_fraction': np.nan, 'entry_on_h2_bar_open': False,
                'entry_status': 'NO_CONFIRMATION_PRE_H2'}

    entry_start = pd.Timestamp(confirm_bar) + BAR5
    if entry_start >= pd.Timestamp(b.session_end):
        return {**base, 'rule': variant, 'entry_executed': False,
                'confirmation_kind': kind, 'confirmation_bar_start': confirm_bar,
                'entry_start': entry_start, 'entry_px': np.nan,
                'entry_fraction': np.nan, 'entry_on_h2_bar_open': False,
                'entry_status': 'NO_NEXT_BAR'}
    pos = int(x5.index.searchsorted(entry_start, side='left'))
    if pos >= len(x5) or x5.index[pos] != entry_start:
        raise AssertionError('missing next-open entry bar')
    entry_px = float(x5.iloc[pos].open)
    if entry_px <= float(b.L):
        return {**base, 'rule': variant, 'entry_executed': False,
                'confirmation_kind': kind, 'confirmation_bar_start': confirm_bar,
                'entry_start': entry_start, 'entry_px': entry_px,
                'entry_fraction': (entry_px - float(b.L)) / float(b['range']),
                'entry_on_h2_bar_open': False,
                'entry_status': 'MISSED_H2_AT_OPEN'}
    if not (float(b.L) < entry_px < float(b.F65)):
        return {**base, 'rule': variant, 'entry_executed': False,
                'confirmation_kind': kind, 'confirmation_bar_start': confirm_bar,
                'entry_start': entry_start, 'entry_px': entry_px,
                'entry_fraction': (entry_px - float(b.L)) / float(b['range']),
                'entry_on_h2_bar_open': False,
                'entry_status': 'INVALID_ENTRY_GEOMETRY'}
    if pd.notna(b.h2_bar_start) and pd.Timestamp(b.h2_bar_start) < entry_start:
        raise AssertionError('confirmed short entry occurs after frozen H2')

    return {**base, 'rule': variant, 'entry_executed': True,
            'confirmation_kind': kind, 'confirmation_bar_start': confirm_bar,
            'entry_start': entry_start, 'entry_px': entry_px,
            'entry_fraction': (entry_px - float(b.L)) / float(b['range']),
            'entry_on_h2_bar_open': bool(pd.notna(b.h2_bar_start) and pd.Timestamp(b.h2_bar_start) == entry_start),
            'entry_status': 'EXECUTED'}


def make_blind_trade_row(b: pd.Series) -> dict:
    d = dict(b)
    d['rule'] = 'BLIND_F15'
    d['entry_executed'] = bool(b.blind_filled)
    d['confirmation_kind'] = None
    d['confirmation_bar_start'] = pd.NaT
    d['entry_start'] = pd.Timestamp(b.blind_touch_bar_start) if bool(b.blind_filled) else pd.NaT
    d['entry_px'] = float(b.blind_entry_px) if bool(b.blind_filled) else np.nan
    d['entry_fraction'] = ENTRY_F if bool(b.blind_filled) else np.nan
    d['entry_on_h2_bar_open'] = False
    d['entry_status'] = 'EXECUTED' if bool(b.blind_filled) else 'NO_BLIND_F15_FILL'
    return d


def time_exit(x5: pd.DataFrame, session_end: pd.Timestamp):
    pos = int(x5.index.searchsorted(session_end, side='left'))
    if pos >= len(x5) or x5.index[pos] != session_end:
        return None
    return session_end, float(x5.iloc[pos].open), 'TIME_EXIT_SESSION_END'


def simulate_fixed(x5: pd.DataFrame, r: pd.Series) -> dict:
    if not bool(r.entry_executed):
        return {'fixed_exit_reason': 'NO_TRADE', 'fixed_exit_px': np.nan,
                'fixed_net_pnl_usd': np.nan, 'fixed_hold_minutes': np.nan,
                'fixed_h2_seen': False, 'fixed_breakdown_accepted': False,
                'fixed_e20_reached': False}
    entry_start = pd.Timestamp(r.entry_start)
    end = pd.Timestamp(r.session_end)
    entry = float(r.entry_px); L = float(r.L); f65 = float(r.F65); tgt = float(r.E20_DOWN)
    q = fast_slice(x5, entry_start, end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing fixed execution slice')
    h2 = False; accepted = False; reached = False
    exit_ts = pd.NaT; exit_px = np.nan; reason = None
    for ts, bar in q.iterrows():
        low = float(bar.low); close = float(bar.close)
        if low <= L:
            h2 = True
        if low <= tgt:
            reached = True
            exit_ts = ts
            exit_px = tgt
            reason = 'TP_E20_DOWN'
            break
        if close > f65:
            exit_ts = ts + BAR5
            exit_px = close
            reason = 'CLOSE_INVALIDATION_F65'
            break
        if close < L:
            accepted = True
    if reason is None:
        te = time_exit(x5, end)
        if te is None:
            raise AssertionError('missing fixed time exit')
        exit_ts, exit_px, reason = te
    gross = 1.0 - float(exit_px) / entry
    net = gross * NOTIONAL - FEE
    hold = float((pd.Timestamp(exit_ts) - entry_start) / pd.Timedelta(minutes=1))
    return {'fixed_exit_reason': reason, 'fixed_exit_px': float(exit_px),
            'fixed_net_pnl_usd': net, 'fixed_hold_minutes': hold,
            'fixed_h2_seen': bool(h2), 'fixed_breakdown_accepted': bool(accepted),
            'fixed_e20_reached': bool(reached)}


def simulate_hybrid(x5: pd.DataFrame, r: pd.Series) -> dict:
    if not bool(r.entry_executed):
        return {'hybrid_exit_reason': 'NO_TRADE', 'hybrid_exit_px': np.nan,
                'hybrid_net_pnl_usd': np.nan, 'hybrid_hold_minutes': np.nan,
                'hybrid_e20_reached': False, 'hybrid_ceiling_ratchets': 0,
                'hybrid_final_ceiling': np.nan, 'session_trough_after_e20': np.nan,
                'trough_extension_r': np.nan, 'realized_exit_extension_r': np.nan,
                'capture_ratio': np.nan, 'giveback_r': np.nan}
    entry_start = pd.Timestamp(r.entry_start)
    end = pd.Timestamp(r.session_end)
    entry = float(r.entry_px); L = float(r.L); rng = float(r['range'])
    f65 = float(r.F65); e20 = float(r.E20_DOWN)
    q = fast_slice(x5, entry_start, end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing hybrid execution slice')
    highs = q.high.astype(float).to_numpy()
    reached = False
    active = False
    ceiling = np.nan
    ratchets = 0
    e20_bar = pd.NaT
    exit_ts = pd.NaT; exit_px = np.nan; reason = None

    for i, (ts, bar) in enumerate(q.iterrows()):
        o = float(bar.open); h = float(bar.high); lo = float(bar.low); c = float(bar.close)
        if not active:
            if c > f65:
                exit_ts = ts + BAR5
                exit_px = c
                reason = 'PRE_E20_CLOSE_INVALIDATION_F65'
                break
            if lo <= e20:
                reached = True
                e20_bar = ts
                active = True
                ceiling = e20
                # A pivot high confirmed at this completed activation bar may ratchet
                # the ceiling for the NEXT bar only.
                if i >= 2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
                    p = float(highs[i-1])
                    if p < ceiling:
                        ceiling = p
                        ratchets += 1
                continue
        else:
            # Existing ceiling was known before this bar opened.
            if o >= ceiling:
                exit_ts = ts
                exit_px = o
                reason = 'OPEN_GAP_AT_OR_ABOVE_PROFIT_CEILING'
                break
            if h >= ceiling:
                exit_ts = ts
                exit_px = ceiling
                reason = 'PROFIT_CEILING_HIT'
                break
            # Pivot confirmed only at this bar close; effective next bar.
            if i >= 2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
                p = float(highs[i-1])
                if p < ceiling:
                    old = ceiling
                    ceiling = p
                    ratchets += 1
                    if ceiling > old:
                        raise AssertionError('short hybrid ceiling rose')

    if reason is None:
        te = time_exit(x5, end)
        if te is None:
            raise AssertionError('missing hybrid time exit')
        exit_ts, exit_px, reason = te

    gross = 1.0 - float(exit_px) / entry
    net = gross * NOTIONAL - FEE
    hold = float((pd.Timestamp(exit_ts) - entry_start) / pd.Timedelta(minutes=1))

    trough = np.nan; trough_ext = np.nan; exit_ext = np.nan; cap = np.nan; give = np.nan
    if reached:
        aq = fast_slice(x5, pd.Timestamp(e20_bar), end)
        if len(aq):
            trough = float(aq.low.min())
            trough_ext = (L - trough) / rng
            exit_ext = (L - float(exit_px)) / rng
            denom = max(0.0, L - trough)
            if denom > 0:
                cap = max(0.0, L - float(exit_px)) / denom
            give = trough_ext - exit_ext

    return {'hybrid_exit_reason': reason, 'hybrid_exit_px': float(exit_px),
            'hybrid_net_pnl_usd': net, 'hybrid_hold_minutes': hold,
            'hybrid_e20_reached': bool(reached),
            'hybrid_ceiling_ratchets': int(ratchets),
            'hybrid_final_ceiling': float(ceiling) if active else np.nan,
            'session_trough_after_e20': trough, 'trough_extension_r': trough_ext,
            'realized_exit_extension_r': exit_ext, 'capture_ratio': cap,
            'giveback_r': give}


def synthetic_tests() -> None:
    idx = pd.date_range('2026-01-02 13:30', periods=14, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    # K1 Low touch episode, leave, F15 touch, H2.
    x = pd.DataFrame([
        {'open':91.0,'high':92.0,'low':89.8,'close':90.5},
        {'open':90.5,'high':91.8,'low':89.9,'close':90.7},
        {'open':90.7,'high':92.0,'low':90.3,'close':91.5},
        {'open':91.5,'high':92.0,'low':91.2,'close':91.3},
        {'open':91.3,'high':92.2,'low':91.0,'close':91.4},
        {'open':91.4,'high':91.8,'low':89.7,'close':90.2},
        {'open':90.2,'high':90.5,'low':87.5,'close':88.0},
        {'open':88.0,'high':88.5,'low':87.0,'close':87.5},
        {'open':87.5,'high':88.0,'low':86.5,'close':87.0},
        {'open':87.0,'high':87.5,'low':86.8,'close':87.2},
        {'open':87.2,'high':87.3,'low':86.0,'close':86.5},
        {'open':86.5,'high':86.8,'low':86.2,'close':86.4},
        {'open':86.4,'high':86.6,'low':86.0,'close':86.2},
        {'open':86.2,'high':86.4,'low':86.0,'close':86.1},
    ], index=idx)
    s = pd.Series({'partition':'x','date_utc':'2026-01-02',
                   'previous_session_high':H,'previous_session_low':L,
                   'signal_bar_start':idx[0],'signal_ts':idx[0]+BAR5,
                   'active_session_end':idx[-1]+BAR5})
    w = build_window(x, s)
    assert w['k1_episode_bars'] == 2
    assert w['eligible_start'] == idx[3]
    assert w['window_status'] == 'H2_ARRIVAL' and w['h2_bar_start'] == idx[5]
    b = blind_f15(x, pd.Series(w))
    assert b['blind_filled'] and b['blind_touch_bar_start'] == idx[3]
    er = confirm_rejection_entry(x, pd.Series(b), False)
    assert er['entry_executed'] and er['confirmation_kind'] == 'SAME_BAR'
    assert er['entry_start'] == idx[4]

    # Direct hybrid test: entry, E20_DOWN reach, then short profit ceiling ratchets down.
    base = pd.Series({**er, 'entry_executed':True, 'entry_start':idx[4], 'entry_px':91.4,
                      'F65':96.5, 'E20_DOWN':88.0, 'L':90.0, 'H':100.0,
                      'range':10.0, 'session_end':idx[13]})
    h = simulate_hybrid(x, base)
    assert h['hybrid_e20_reached']
    assert h['hybrid_exit_reason'] in ('PROFIT_CEILING_HIT','TIME_EXIT_SESSION_END','OPEN_GAP_AT_OR_ABOVE_PROFIT_CEILING')


def summarize(g: pd.DataFrame) -> dict:
    e = g[g.entry_executed.astype(bool)].copy()
    if len(e) == 0:
        return {'trades':0, 'fixed_wr':np.nan, 'fixed_pf':np.nan, 'fixed_exp':np.nan,
                'fixed_total':np.nan, 'hybrid_wr':np.nan, 'hybrid_pf':np.nan,
                'hybrid_exp':np.nan, 'hybrid_total':np.nan, 'delta_total':np.nan,
                'e20_reach':np.nan, 'winner_preserved':np.nan,
                'median_trough_ext_r':np.nan, 'median_exit_ext_r':np.nan,
                'median_capture':np.nan, 'median_giveback_r':np.nan}
    f = e.fixed_net_pnl_usd.astype(float)
    h = e.hybrid_net_pnl_usd.astype(float)
    fixed_winners = f > 0
    preserved = float((h[fixed_winners] > 0).mean()) if fixed_winners.any() else np.nan
    reached = e[e.hybrid_e20_reached.astype(bool)]
    return {
        'trades': int(len(e)),
        'fixed_wr': float((f > 0).mean()), 'fixed_pf': pf(f),
        'fixed_exp': float(f.mean()), 'fixed_total': float(f.sum()),
        'hybrid_wr': float((h > 0).mean()), 'hybrid_pf': pf(h),
        'hybrid_exp': float(h.mean()), 'hybrid_total': float(h.sum()),
        'delta_total': float(h.sum() - f.sum()),
        'e20_reach': float(e.hybrid_e20_reached.mean()),
        'winner_preserved': preserved,
        'median_trough_ext_r': float(reached.trough_extension_r.median()) if len(reached) else np.nan,
        'median_exit_ext_r': float(reached.realized_exit_extension_r.median()) if len(reached) else np.nan,
        'median_capture': float(reached.capture_ratio.median()) if len(reached) else np.nan,
        'median_giveback_r': float(reached.giveback_r.median()) if len(reached) else np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100.0*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def money(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main() -> None:
    synthetic_tests()
    x5, coverage = b21.load5()
    assert abs(float(coverage) - 1.0) < 1e-12
    s = load_k1()
    windows = pd.DataFrame([build_window(x5, r) for _, r in s.iterrows()])
    assert len(windows) == len(s)
    assert list(pd.to_datetime(windows.signal_ts, utc=True)) == list(pd.to_datetime(s.signal_ts, utc=True))

    blinds = pd.DataFrame([blind_f15(x5, w) for _, w in windows.iterrows()])
    assert len(blinds) == len(windows)

    rows = []
    for _, b in blinds.iterrows():
        rows.append(make_blind_trade_row(b))
        rows.append(confirm_rejection_entry(x5, b, False))
        rows.append(confirm_rejection_entry(x5, b, True))
    t = pd.DataFrame(rows)

    # Same-bar executions must be exact subset of early-reject executions.
    er = t[t.rule == 'EARLY_REJECT'].copy()
    sb = t[(t.rule == 'SAME_BAR_REJECTION') & t.entry_executed.astype(bool)].copy()
    er_keys = set(zip(er.partition.astype(str), er.date_utc.astype(str), er.signal_ts.astype(str)))
    for r in sb.itertuples(index=False):
        key = (str(r.partition), str(r.date_utc), str(r.signal_ts))
        assert key in er_keys
        z = er[(er.partition.astype(str)==key[0]) & (er.date_utc.astype(str)==key[1]) & (er.signal_ts.astype(str)==key[2])].iloc[0]
        assert bool(z.entry_executed) and z.confirmation_kind == 'SAME_BAR'
        assert pd.Timestamp(z.entry_start) == pd.Timestamp(r.entry_start)
        assert abs(float(z.entry_px) - float(r.entry_px)) < 1e-9

    # Formula and chronology assertions.
    for r in t[t.entry_executed.astype(bool)].itertuples(index=False):
        rng = float(r.H) - float(r.L)
        assert abs(float(r.F15) - (float(r.L)+ENTRY_F*rng)) < 1e-9*max(1.0,abs(float(r.F15)))
        assert abs(float(r.F65) - (float(r.L)+STOP_F*rng)) < 1e-9*max(1.0,abs(float(r.F65)))
        assert abs(float(r.E20_DOWN) - (float(r.L)-TARGET_EXT*rng)) < 1e-9*max(1.0,abs(float(r.E20_DOWN)))
        if r.rule != 'BLIND_F15':
            assert pd.Timestamp(r.entry_start) == pd.Timestamp(r.confirmation_bar_start) + BAR5
        if pd.notna(r.h2_bar_start):
            assert pd.Timestamp(r.entry_start) <= pd.Timestamp(r.h2_bar_start)

    fixed = [simulate_fixed(x5, r) for _, r in t.iterrows()]
    hybrid = [simulate_hybrid(x5, r) for _, r in t.iterrows()]
    t = pd.concat([t.reset_index(drop=True), pd.DataFrame(fixed), pd.DataFrame(hybrid)], axis=1)

    # Structural B27W-mirror screen on BLIND_F15.
    structural_rows = []
    structural_pass = True
    for part in PARTS:
        g = blinds[blinds.partition == part]
        f = g[g.blind_filled.astype(bool)]
        hit = float(f.h2_after_fill.mean()) if len(f) else np.nan
        structural_rows.append({'partition':part, 'k1_opportunities':len(g),
                                'clean_windows':int((~g.window_status.astype(str).str.startswith('NO_WINDOW') & (g.window_status!='NO_CAUSAL_LEAVE_BY_SESSION_END')).sum()),
                                'f15_fills':len(f), 'h2_hits':int(f.h2_after_fill.sum()) if len(f) else 0,
                                'h2_hit_rate':hit,
                                'median_minutes_to_h2':float(f.loc[f.h2_after_fill.astype(bool),'minutes_fill_to_h2'].median()) if len(f) and f.h2_after_fill.any() else np.nan})
        if part in MAJOR:
            structural_pass = structural_pass and len(f) >= 30 and pd.notna(hit) and hit >= 0.70
    structural = pd.DataFrame(structural_rows)

    sums = []
    for rule in RULES:
        for part in PARTS:
            g = t[(t.rule == rule) & (t.partition == part)]
            sums.append({'rule':rule, 'partition':part, **summarize(g)})
        g = t[(t.rule == rule) & t.partition.isin(MAJOR)]
        sums.append({'rule':rule, 'partition':'POOLED_MAJOR', **summarize(g)})
    sm = pd.DataFrame(sums)

    # Primary confirmatory economics gate. Same long-side philosophy: no promotion
    # unless every major partition is individually viable and pooled hybrid improves.
    ps = sm[(sm.rule == 'EARLY_REJECT') & sm.partition.isin(MAJOR)]
    pooled = sm[(sm.rule == 'EARLY_REJECT') & (sm.partition == 'POOLED_MAJOR')].iloc[0]
    econ_supported = bool(len(ps)==3 and (ps.trades >= 30).all() and
                          (ps.hybrid_pf >= 1.0).all() and (ps.hybrid_exp > 0).all() and
                          float(pooled.hybrid_total) > float(pooled.fixed_total))

    windows.to_csv(OUT_WINDOWS, index=False)
    t.to_csv(OUT_TRADES, index=False)
    sm.to_csv(OUT_SUM, index=False)
    status = ('B27AD_STRUCTURAL_PASS' if structural_pass else 'B27AD_STRUCTURAL_FAIL') + ' | ' + \
             ('B27AD_ECON_SUPPORTED' if econ_supported else 'B27AD_ECON_NOT_SUPPORTED')
    OUT_STATUS.write_text(status + '\n')

    lines = []
    lines.append('# B27AD — BTC London -> New York SHORT Exact Mirror — Result')
    lines.append('')
    lines.append(f'5m rows: **{len(x5):,}**; coverage: **{100.0*float(coverage):.4f}%**.')
    lines.append('')
    lines.append('**Audit status: PASS.** B27Q SHORT K1 OPP0 identities, low-touch chronology, pre-H2 F15 fills, mirrored rejection entries, fixed E20_DOWN economics, and E20 profit-ceiling runner were evaluated without parameter tuning.')
    lines.append('')
    lines.append('## Structural pre-H2 F15 mirror')
    lines.append('')
    lines.append('| Partition | K1 opps | Clean windows | F15 fills | H2 hits | H2 hit rate | Median min fill->H2 |')
    lines.append('|---|---:|---:|---:|---:|---:|---:|')
    for r in structural.itertuples(index=False):
        lines.append(f'| {r.partition} | {int(r.k1_opportunities)} | {int(r.clean_windows)} | {int(r.f15_fills)} | {int(r.h2_hits)} | {pct(r.h2_hit_rate)} | {num(r.median_minutes_to_h2)} |')
    lines.append('')
    lines.append(f"**Structural screen: {'PASS' if structural_pass else 'FAIL'}.** Exact frozen requirement: >=30 F15 fills and >=70% H2 hit among fills in each major partition.")
    lines.append('')
    lines.append('## Fixed E20_DOWN vs E20-lock short runner')
    lines.append('')
    lines.append('| Rule | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total | Delta total | E20 reach | Winner preserved |')
    lines.append('|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in sm.itertuples(index=False):
        lines.append(f'| {r.rule} | {r.partition} | {int(r.trades)} | {pct(r.fixed_wr)} | {num(r.fixed_pf)} | {money(r.fixed_exp)} | {money(r.fixed_total)} | {pct(r.hybrid_wr)} | {num(r.hybrid_pf)} | {money(r.hybrid_exp)} | {money(r.hybrid_total)} | {money(r.delta_total)} | {pct(r.e20_reach)} | {pct(r.winner_preserved)} |')
    lines.append('')
    lines.append('## Runner downside-extension capture')
    lines.append('')
    lines.append('| Rule | Partition | Median trough ext below L | Median realized exit ext | Median capture | Median giveback |')
    lines.append('|---|---|---:|---:|---:|---:|')
    for r in sm.itertuples(index=False):
        lines.append(f'| {r.rule} | {r.partition} | {num(r.median_trough_ext_r)}R | {num(r.median_exit_ext_r)}R | {pct(r.median_capture)} | {num(r.median_giveback_r)}R |')
    lines.append('')
    lines.append(f"**Primary EARLY_REJECT economics: {'SUPPORTED' if econ_supported else 'NOT SUPPORTED'} under the frozen confirmatory gate.**")
    lines.append('')
    lines.append('No threshold, entry fraction, stop fraction, target extension, pivot width, or timeframe was tuned after seeing SHORT results.')
    lines.append('')
    lines.append('Research only; live BBC unchanged.')
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
