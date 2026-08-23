#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
B27BE_RESULT = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Result.md'
B27BE_DETAIL = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'

OUT_MD = ROOT / 'BTC_24H_ADAPTIVE_REGIME_ROUTER_B27BF_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_ADAPTIVE_REGIME_ROUTER_B27BF_Trades.csv'
OUT_BLOCKS = ROOT / 'BTC_24H_ADAPTIVE_REGIME_ROUTER_B27BF_Blocks.csv'
OUT_SUM = ROOT / 'BTC_24H_ADAPTIVE_REGIME_ROUTER_B27BF_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_ADAPTIVE_REGIME_ROUTER_B27BF_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
MAJOR = ('external', 'development', 'reference_validation')
REGIMES = ('BULL', 'BEAR', 'SIDEWAYS')
EPS = 1e-12


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


def boundary_open(x5: pd.DataFrame, ts: pd.Timestamp) -> float:
    p = int(x5.index.searchsorted(ts, side='left'))
    if p >= len(x5) or x5.index[p] != ts:
        raise AssertionError(f'missing exact boundary open {ts}')
    return float(x5.iloc[p].open)


def touches(hi: float, lo: float, cl: float, H: float, L: float) -> tuple[bool, bool, bool, bool]:
    break_hi = cl > H
    break_lo = cl < L
    hit_hi = hi >= H and cl <= H
    hit_lo = lo <= L and cl >= L
    return break_hi, break_lo, hit_hi, hit_lo


def find_long_entry(q: pd.DataFrame, H: float, L: float) -> dict:
    R = H - L
    f85 = L + 0.85 * R
    f35 = L + 0.35 * R
    if not H > L:
        raise AssertionError('bad range')

    low_visits = 0
    hi_touching = False
    lo_touching = False
    k1_i = None

    # Find first High K1 with OPP0.
    for i, (_, b) in enumerate(q.iterrows()):
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bh or bl:
            return {'status': 'BREAK_BEFORE_K1', 'k1': False}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BOTH_LEVELS', 'k1': False}
        if hl and not lo_touching:
            low_visits += 1
        if hh and not hi_touching:
            if low_visits == 0:
                k1_i = i
                break
            return {'status': 'K1_NOT_OPP0', 'k1': False}
        hi_touching = bool(hh)
        lo_touching = bool(hl)

    if k1_i is None:
        return {'status': 'NO_K1', 'k1': False}

    # Collapse K1 High-touch episode; first non-touch completed bar is causal leave.
    leave_i = None
    for j in range(k1_i + 1, len(q)):
        b = q.iloc[j]
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bh or bl:
            return {'status': 'BREAK_BEFORE_LEAVE1', 'k1': True}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BEFORE_LEAVE1', 'k1': True}
        if not hh:
            leave_i = j
            break
    if leave_i is None:
        return {'status': 'NO_LEAVE1', 'k1': True}

    eligible_i = leave_i + 1
    if eligible_i >= len(q):
        return {'status': 'NO_BAR_AFTER_LEAVE1', 'k1': True}

    # SAME_BAR F85 confirmation before H2; entry next 5m open.
    for k in range(eligible_i, len(q)):
        b = q.iloc[k]
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        if hi >= H:
            return {'status': 'H2_BEFORE_F85_CONFIRM', 'k1': True}
        if cl < L:
            return {'status': 'LOW_BREAK_BEFORE_F85_CONFIRM', 'k1': True}
        if cl > H:
            return {'status': 'HIGH_BREAK_BEFORE_F85_CONFIRM', 'k1': True}
        if lo <= f85 <= hi:
            if cl <= f85:
                # SAME_BAR-only lineage: a touched F85 bar that fails to close back above F85
                # does not confirm. Later eligible bars may still touch/reject before H2.
                continue
            entry_i = k + 1
            if entry_i >= len(q):
                return {'status': 'CONFIRMED_NO_NEXT_BAR', 'k1': True}
            entry = q.iloc[entry_i]
            entry_px = float(entry.open)
            if entry_px >= H:
                return {'status': 'MISSED_H2_AT_ENTRY_OPEN', 'k1': True}
            if not (f35 < entry_px < H):
                return {'status': 'INVALID_LONG_ENTRY_GEOMETRY', 'k1': True}
            return {
                'status': 'EXECUTED', 'k1': True,
                'k1_ts': q.index[k1_i], 'leave_ts': q.index[leave_i] + BAR5,
                'confirm_bar_start': q.index[k], 'entry_start': q.index[entry_i],
                'entry_px': entry_px, 'F85': f85, 'F35': f35,
            }

    return {'status': 'NO_F85_CONFIRM_BY_BLOCK_END', 'k1': True}


def simulate_long(x5: pd.DataFrame, entry_start: pd.Timestamp, entry_px: float,
                  H: float, L: float, end: pd.Timestamp) -> dict:
    R = H - L
    f35 = L + 0.35 * R
    e20 = H + 0.20 * R
    q = fast_slice(x5, entry_start, end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing LONG entry bar')
    lows = q.low.astype(float).to_numpy()

    reached = False
    floor_active = False
    floor = np.nan
    activation_bar = pd.NaT
    ratchets = 0
    reason = None
    exit_ts = pd.NaT
    exit_px = np.nan

    for i, (ts, b) in enumerate(q.iterrows()):
        op, hi, lo, cl = map(float, (b.open, b.high, b.low, b.close))

        if floor_active:
            if op <= floor:
                reason = 'LONG_PROFIT_FLOOR_GAP_OPEN'; exit_ts = ts; exit_px = op; break
            if lo <= floor:
                reason = 'LONG_PROFIT_FLOOR_HIT'; exit_ts = ts; exit_px = floor; break

        pivot = np.nan
        if i >= 2 and lows[i-1] < lows[i-2] and lows[i-1] < lows[i]:
            pivot = float(lows[i-1])

        if not reached:
            touched = hi >= e20
            # Exact B27AC conservative precedence: same-bar F35 close invalidation wins.
            if cl < f35:
                reason = 'LONG_PRE_E20_CLOSE_INVALIDATION_F35'
                exit_ts = ts + BAR5
                exit_px = cl
                break
            if touched:
                reached = True
                floor_active = True
                floor = e20
                activation_bar = ts
                if np.isfinite(pivot) and pivot > floor:
                    floor = pivot; ratchets += 1
                continue
        else:
            if np.isfinite(pivot) and pivot > floor:
                old = floor
                floor = pivot
                ratchets += 1
                assert floor >= old - EPS

    if reason is None:
        exit_ts = end
        exit_px = boundary_open(x5, end)
        reason = 'LONG_TIME_EXIT_4H_BOUNDARY'

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    return {
        'activated': bool(reached), 'activation_bar_start': activation_bar,
        'ratchets': int(ratchets), 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'exit_reason': reason, 'net_pnl_usd': net, 'win': bool(net > 0),
    }


def find_short_entry(q: pd.DataFrame, H: float, L: float) -> dict:
    R = H - L
    f15 = L + 0.15 * R
    if not H > L:
        raise AssertionError('bad range')

    high_visits = 0
    hi_touching = False
    lo_touching = False
    k1_i = None

    # Find first Low K1 with OPP0.
    for i, (_, b) in enumerate(q.iterrows()):
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bh or bl:
            return {'status': 'BREAK_BEFORE_K1', 'k1': False}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BOTH_LEVELS', 'k1': False}
        if hh and not hi_touching:
            high_visits += 1
        if hl and not lo_touching:
            if high_visits == 0:
                k1_i = i
                break
            return {'status': 'K1_NOT_OPP0', 'k1': False}
        hi_touching = bool(hh)
        lo_touching = bool(hl)

    if k1_i is None:
        return {'status': 'NO_K1', 'k1': False}

    # Collapse Low visit #1 and require causal leave.
    leave1 = None
    for j in range(k1_i + 1, len(q)):
        b = q.iloc[j]
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bh or bl:
            return {'status': 'BREAK_BEFORE_LEAVE1', 'k1': True}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BEFORE_LEAVE1', 'k1': True}
        if not hl:
            leave1 = j
            break
    if leave1 is None:
        return {'status': 'NO_LEAVE1', 'k1': True}

    # Require distinct valid Low retest #2 after the leave.
    t2 = None
    for k in range(leave1 + 1, len(q)):
        b = q.iloc[k]
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bl:
            return {'status': 'LOW_BREAK_BEFORE_T2', 'k1': True}
        if bh:
            return {'status': 'HIGH_BREAK_BEFORE_T2', 'k1': True}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BEFORE_T2', 'k1': True}
        if hl:
            t2 = k
            break
    if t2 is None:
        return {'status': 'NO_T2', 'k1': True}

    # Collapse retest #2 episode and require causal leave.
    leave2 = None
    for j in range(t2 + 1, len(q)):
        b = q.iloc[j]
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bl:
            return {'status': 'BREAK_BEFORE_LEAVE2', 'k1': True, 't2': True}
        if bh:
            return {'status': 'HIGH_BREAK_BEFORE_LEAVE2', 'k1': True, 't2': True}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BEFORE_LEAVE2', 'k1': True, 't2': True}
        if not hl:
            leave2 = j
            break
    if leave2 is None:
        return {'status': 'NO_LEAVE2', 'k1': True, 't2': True}

    eligible = leave2 + 1
    if eligible >= len(q):
        return {'status': 'NO_BAR_AFTER_LEAVE2', 'k1': True, 't2': True}

    # F15 must fill strictly before T3/breakdown/opposite break.
    for k in range(eligible, len(q)):
        b = q.iloc[k]
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        bh, bl, hh, hl = touches(hi, lo, cl, H, L)
        if bl:
            return {'status': 'BREAKDOWN_BEFORE_F15', 'k1': True, 't2': True}
        if bh:
            return {'status': 'HIGH_BREAK_BEFORE_F15', 'k1': True, 't2': True}
        if hh and hl:
            return {'status': 'AMBIGUOUS_BEFORE_F15', 'k1': True, 't2': True}
        if hl:
            return {'status': 'T3_BEFORE_F15', 'k1': True, 't2': True}
        if lo <= f15 <= hi:
            return {
                'status': 'EXECUTED', 'k1': True, 't2': True,
                'k1_ts': q.index[k1_i], 't2_ts': q.index[t2],
                'leave2_ts': q.index[leave2] + BAR5,
                'entry_start': q.index[k], 'entry_px': f15, 'F15': f15,
            }

    return {'status': 'NO_F15_FILL_BY_BLOCK_END', 'k1': True, 't2': True}


def simulate_short(x5: pd.DataFrame, entry_start: pd.Timestamp, entry_px: float,
                   H: float, L: float, end: pd.Timestamp) -> dict:
    R = H - L
    stop = entry_px + 0.30 * R
    e20 = L - 0.20 * R
    q = fast_slice(x5, entry_start, end)
    if q.empty or q.index[0] != entry_start:
        raise AssertionError('missing SHORT entry bar')
    highs = q.high.astype(float).to_numpy()

    reached = False
    active = False
    ceiling = np.nan
    activation_bar = pd.NaT
    ratchets = 0
    reason = None
    exit_ts = pd.NaT
    exit_px = np.nan

    for i, (ts, b) in enumerate(q.iterrows()):
        op, hi, lo = map(float, (b.open, b.high, b.low))

        if active:
            if op >= ceiling:
                reason = 'SHORT_PROFIT_CEILING_GAP_OPEN'; exit_ts = ts; exit_px = op; break
            if hi >= ceiling:
                reason = 'SHORT_PROFIT_CEILING_HIT'; exit_ts = ts; exit_px = ceiling; break

        pivot = np.nan
        if i >= 2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
            pivot = float(highs[i-1])

        if not reached:
            # Conservative B27BC hard-stop precedence, active from fill bar.
            if op >= stop:
                reason = 'SHORT_PRE_E20_HARD_STOP_GAP_OPEN'; exit_ts = ts; exit_px = op; break
            if hi >= stop - EPS:
                reason = 'SHORT_PRE_E20_HARD_STOP_TOUCH'; exit_ts = ts; exit_px = stop; break
            # Fill bar cannot activate.
            if i > 0 and lo <= e20 + EPS:
                reached = True
                active = True
                ceiling = e20
                activation_bar = ts
                if np.isfinite(pivot) and pivot < ceiling:
                    ceiling = pivot; ratchets += 1
                continue
        else:
            if np.isfinite(pivot) and pivot < ceiling:
                old = ceiling
                ceiling = pivot
                ratchets += 1
                assert ceiling <= old + EPS

    if reason is None:
        exit_ts = end
        exit_px = boundary_open(x5, end)
        reason = 'SHORT_TIME_EXIT_4H_BOUNDARY'

    gross = float(1.0 - float(exit_px) / entry_px)
    net = gross * NOTIONAL - FEE
    return {
        'activated': bool(reached), 'activation_bar_start': activation_bar,
        'ratchets': int(ratchets), 'exit_ts': exit_ts, 'exit_px': float(exit_px),
        'stop_px': stop, 'E20_DOWN': e20,
        'exit_reason': reason, 'net_pnl_usd': net, 'win': bool(net > 0),
    }


def synthetic_tests() -> None:
    # LONG: K1 High -> leave -> F85 same-bar reclaim -> next-open entry -> E20 -> floor exit.
    idx = pd.date_range('2026-01-01 04:00', periods=49, freq='5min', tz='UTC')
    H, L = 100.0, 90.0
    bars = [{'open':95,'high':96,'low':94,'close':95} for _ in range(49)]
    bars[0] = {'open':99,'high':100.2,'low':98.8,'close':99.7}   # K1
    bars[1] = {'open':99.7,'high':99.8,'low':99.0,'close':99.2} # leave
    bars[2] = {'open':99.2,'high':99.3,'low':98.4,'close':98.8} # F85 touch/reclaim
    bars[3] = {'open':98.9,'high':99.5,'low':98.7,'close':99.2} # entry open
    bars[4] = {'open':99.2,'high':102.2,'low':99.0,'close':101.5} # E20
    bars[5] = {'open':101.5,'high':101.7,'low':101.0,'close':101.2}
    bars[6] = {'open':101.2,'high':102.1,'low':101.1,'close':101.5} # floor hit E20=102? open below => gap
    x = pd.DataFrame(bars, index=idx)
    q = x.iloc[:48]
    e = find_long_entry(q, H, L)
    assert e['status'] == 'EXECUTED' and e['entry_start'] == idx[3]
    z = simulate_long(x, e['entry_start'], e['entry_px'], H, L, idx[48])
    assert z['activated'] and z['exit_reason'] in ('LONG_PROFIT_FLOOR_GAP_OPEN','LONG_PROFIT_FLOOR_HIT')

    # SHORT: Low #1 -> leave -> Low #2 -> leave -> F15 -> D30 stop path.
    bars2 = [{'open':95,'high':96,'low':94,'close':95} for _ in range(49)]
    bars2[0] = {'open':91,'high':91.5,'low':89.9,'close':90.4}  # T1
    bars2[1] = {'open':90.4,'high':91.2,'low':90.3,'close':91.0} # leave1
    bars2[2] = {'open':91.0,'high':91.1,'low':89.8,'close':90.3} # T2
    bars2[3] = {'open':90.3,'high':91.4,'low':90.2,'close':91.1} # leave2
    bars2[4] = {'open':91.1,'high':91.7,'low':91.4,'close':91.5} # F15=91.5 fill
    bars2[5] = {'open':91.5,'high':94.6,'low':91.0,'close':94.0} # D30 stop=94.5
    x2 = pd.DataFrame(bars2, index=idx)
    q2 = x2.iloc[:48]
    e2 = find_short_entry(q2, H, L)
    assert e2['status'] == 'EXECUTED' and e2['entry_start'] == idx[4]
    z2 = simulate_short(x2, e2['entry_start'], e2['entry_px'], H, L, idx[48])
    assert z2['exit_reason'] == 'SHORT_PRE_E20_HARD_STOP_TOUCH'


def summarize(g: pd.DataFrame, blocks: pd.DataFrame) -> dict:
    vals = pd.to_numeric(g.net_pnl_usd, errors='coerce') if len(g) else pd.Series(dtype=float)
    days = int(blocks.date_utc.nunique()) if len(blocks) else 0
    weeks = days / 7.0 if days else np.nan
    return {
        'n': int(len(g)),
        'wr': float((vals > 0).mean()) if len(g) else np.nan,
        'pf': pf(vals),
        'expectancy': float(vals.mean()) if len(g) else np.nan,
        'total_pnl': float(vals.sum()) if len(g) else 0.0,
        'activation_rate': float(g.activated.mean()) if len(g) else np.nan,
        'trades_per_week': float(len(g) / weeks) if weeks and weeks > 0 else np.nan,
    }


def fmt(v, n=3):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{n}f}'


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main() -> None:
    synthetic_tests()

    if not B27BE_RESULT.exists() or not B27BE_DETAIL.exists():
        raise AssertionError('B27BE frozen source files missing')
    b27be_text = B27BE_RESULT.read_text()
    assert 'Audit status: PASS' in b27be_text
    assert 'B27BE_SHORT_STRUCTURALLY_FAVORED_NONE__CLOCK_NONE' in b27be_text

    x5, coverage = b21.load5()
    assert len(x5) == 698112 and abs(float(coverage) - 1.0) < 1e-12

    blocks = pd.read_csv(B27BE_DETAIL)
    for c in ('obs_start','obs_end','prev_start','regime_available_ts'):
        blocks[c] = pd.to_datetime(blocks[c], utc=True, errors='raise')
    blocks['date_utc'] = blocks['date_utc'].astype(str)
    blocks = blocks.sort_values(['partition','obs_start']).reset_index(drop=True)
    assert len(blocks) > 9000
    assert blocks.regime.isin(REGIMES).all()
    assert (blocks.regime_available_ts <= blocks.obs_start).all()
    assert not blocks.duplicated(['partition','obs_start']).any()

    trade_rows = []
    block_rows = []

    for _, r in blocks.iterrows():
        start = pd.Timestamp(r.obs_start); end = pd.Timestamp(r.obs_end)
        H = float(r.H); L = float(r.L); R = H - L
        if not H > L: raise AssertionError('nonpositive frozen range')
        q = fast_slice(x5, start, end)
        if len(q) != 48 or q.index[0] != start:
            raise AssertionError('B27BE complete block no longer reproduces')

        le = find_long_entry(q, H, L)
        se = find_short_entry(q, H, L)

        br = {
            'partition': r.partition, 'date_utc': r.date_utc,
            'obs_start': start, 'obs_end': end, 'regime': r.regime,
            'H': H, 'L': L, 'range': R,
            'long_status': le['status'], 'long_k1': bool(le.get('k1', False)),
            'short_status': se['status'], 'short_k1': bool(se.get('k1', False)),
            'short_t2': bool(se.get('t2', False)),
        }

        if le['status'] == 'EXECUTED':
            sim = simulate_long(x5, pd.Timestamp(le['entry_start']), float(le['entry_px']), H, L, end)
            row = {
                'partition': r.partition, 'date_utc': r.date_utc,
                'obs_start': start, 'obs_end': end, 'regime': r.regime,
                'side': 'LONG', 'router_selected': bool(r.regime == 'BULL'),
                'entry_start': le['entry_start'], 'entry_px': float(le['entry_px']),
                'H': H, 'L': L, 'range': R,
                **sim,
            }
            trade_rows.append(row)
            br['long_entry_start'] = le['entry_start']
        else:
            br['long_entry_start'] = pd.NaT

        if se['status'] == 'EXECUTED':
            sim = simulate_short(x5, pd.Timestamp(se['entry_start']), float(se['entry_px']), H, L, end)
            row = {
                'partition': r.partition, 'date_utc': r.date_utc,
                'obs_start': start, 'obs_end': end, 'regime': r.regime,
                'side': 'SHORT', 'router_selected': bool(r.regime == 'BEAR'),
                'entry_start': se['entry_start'], 'entry_px': float(se['entry_px']),
                'H': H, 'L': L, 'range': R,
                **sim,
            }
            trade_rows.append(row)
            br['short_entry_start'] = se['entry_start']
        else:
            br['short_entry_start'] = pd.NaT

        block_rows.append(br)

    tr = pd.DataFrame(trade_rows)
    ba = pd.DataFrame(block_rows)
    if tr.empty:
        raise AssertionError('no diagnostic trades')

    # Router guardrails.
    router = tr[tr.router_selected].copy()
    assert ((router.side == 'LONG') == (router.regime == 'BULL')).all()
    assert ((router.side == 'SHORT') == (router.regime == 'BEAR')).all()
    assert not (router.regime == 'SIDEWAYS').any()
    # One routed position max per block by construction.
    assert not router.duplicated(['partition','obs_start']).any()

    tr.to_csv(OUT_TRADES, index=False)
    ba.to_csv(OUT_BLOCKS, index=False)

    rows = []
    parts = tuple(sorted(blocks.partition.unique()))

    def add_summary(label: str, subset: pd.DataFrame, part: str):
        if part == 'POOLED_MAJOR':
            b = blocks[blocks.partition.isin(MAJOR)]
            g = subset[subset.partition.isin(MAJOR)]
        else:
            b = blocks[blocks.partition == part]
            g = subset[subset.partition == part]
        s = summarize(g, b)
        rows.append({'label': label, 'partition': part, **s})

    for part in (*parts, 'POOLED_MAJOR'):
        add_summary('ROUTER', router, part)
        add_summary('ALL_LONG_DIAGNOSTIC', tr[tr.side == 'LONG'], part)
        add_summary('ALL_SHORT_DIAGNOSTIC', tr[tr.side == 'SHORT'], part)

    # Regime/side diagnostic attribution.
    for side in ('LONG','SHORT'):
        for rg in REGIMES:
            ss = tr[(tr.side == side) & (tr.regime == rg)]
            for part in (*parts, 'POOLED_MAJOR'):
                add_summary(f'{side}_{rg}', ss, part)

    sm = pd.DataFrame(rows)
    sm.to_csv(OUT_SUM, index=False)

    # Frozen support gate.
    ok = True
    for part in MAJOR:
        z = sm[(sm.label == 'ROUTER') & (sm.partition == part)].iloc[0]
        ok = ok and int(z.n) >= 30 and float(z.expectancy) >= 0 and float(z.pf) >= 1.0
    p = sm[(sm.label == 'ROUTER') & (sm.partition == 'POOLED_MAJOR')].iloc[0]
    ok = ok and float(p.expectancy) > 0 and float(p.pf) >= 1.20 and float(p.total_pnl) > 0
    verdict = 'SUPPORTED' if ok else 'NOT_SUPPORTED'
    status = f'B27BF_ADAPTIVE_ROUTER_{verdict}'
    OUT_STATUS.write_text(status + '\n')

    # Setup diagnostics pooled major.
    bp = ba[ba.partition.isin(MAJOR)]
    bull_blocks = int((bp.regime == 'BULL').sum())
    bear_blocks = int((bp.regime == 'BEAR').sum())
    side_blocks = int((bp.regime == 'SIDEWAYS').sum())
    long_exec = int(((bp.regime == 'BULL') & (bp.long_status == 'EXECUTED')).sum())
    short_exec = int(((bp.regime == 'BEAR') & (bp.short_status == 'EXECUTED')).sum())

    lines = [
        '# B27BF — BTC 24H Adaptive Regime Router Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27BE remained frozen and supplied the complete rolling 4H block/range/regime universe. No Asia/London/New-York session label was used for entry eligibility.','',
        '**Router v1:** BULL -> LONG B27W/B27AA/B27AC lineage; BEAR -> SHORT B27AY/B27BC lineage; SIDEWAYS -> FLAT. UTC 4H boundaries refresh state/range but are not preferred trading windows.','',
        '## Router economics','',
        '| Partition | N | WR | PF | Exp/trade $ | Total $ | E20 act | Trades/week |',
        '|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in (*MAJOR, 'POOLED_MAJOR'):
        r = sm[(sm.label == 'ROUTER') & (sm.partition == part)].iloc[0]
        lines.append(f'| {part} | {int(r.n)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.total_pnl)} | {pct(r.activation_rate)} | {fmt(r.trades_per_week,2)} |')

    lines += ['', '## Router components — pooled major','',
        '| Component | Regime | N | WR | PF | Exp/trade $ | Total $ | E20 act |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for label, rg in (('LONG_BULL','BULL'),('SHORT_BEAR','BEAR')):
        r = sm[(sm.label == label) & (sm.partition == 'POOLED_MAJOR')].iloc[0]
        lines.append(f'| {label.split("_")[0]} | {rg} | {int(r.n)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.total_pnl)} | {pct(r.activation_rate)} |')

    lines += ['', '## Counterfactual playbook attribution — pooled major','',
        '| Side / actual regime | N | WR | PF | Exp/trade $ | Total $ | E20 act |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for side in ('LONG','SHORT'):
        for rg in REGIMES:
            r = sm[(sm.label == f'{side}_{rg}') & (sm.partition == 'POOLED_MAJOR')].iloc[0]
            lines.append(f'| {side} / {rg} | {int(r.n)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.total_pnl)} | {pct(r.activation_rate)} |')

    lines += ['', '## Structural opportunity counts — pooled major','',
        f'- BULL observation blocks: **{bull_blocks:,}**; routed LONG executions: **{long_exec:,}**.',
        f'- BEAR observation blocks: **{bear_blocks:,}**; routed SHORT executions: **{short_exec:,}**.',
        f'- SIDEWAYS observation blocks: **{side_blocks:,}**; routed executions by design: **0**.',
        '', '## Frozen verdict','',
        f'**{status}.**', '',
        'Support required >=30 routed trades in each major partition, nonnegative expectancy and PF>=1.0 in each, plus pooled expectancy>0, PF>=1.20, and positive total. No thresholds or router mapping were changed after seeing results.', '',
        'Research only; live BBC unchanged.'
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
