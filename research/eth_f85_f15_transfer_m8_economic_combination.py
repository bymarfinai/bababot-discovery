#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PFX = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M8'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SEL = ROOT / f'{PFX}_Selection.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')

# Frozen M5 entry identity + M7 target candidate.
LOCKED = {
    'ALT_0330': ('F95', 0.95, 'E30', 0.30),
    'RAW_0530': ('F90', 0.90, 'E30', 0.30),
    'LONDON': ('F90', 0.90, 'E25', 0.25),
    'RAW_2330': ('F95', 0.95, 'E15', 0.15),
}

# Frozen M6 candidates only; no new stop distances are searched in M8.
STOP_CANDIDATES = {
    'ALT_0330': {'HARD_TOUCH': (0.45, 0.50), 'CLOSE_NEXT_OPEN': (0.40, 0.55)},
    'RAW_0530': {'HARD_TOUCH': (0.55, 0.35), 'CLOSE_NEXT_OPEN': (0.40, 0.50)},
    'LONDON': {'HARD_TOUCH': (0.55, 0.35), 'CLOSE_NEXT_OPEN': (0.35, 0.55)},
    'RAW_2330': {'HARD_TOUCH': (0.40, 0.55), 'CLOSE_NEXT_OPEN': (0.30, 0.65)},
}

spec = importlib.util.spec_from_file_location(
    'eth_m2', HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py'
)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def corrected_find_window(exe, H, L, side):
    hi_touch = lo_touch = False
    hi_vis = lo_vis = 0
    state = 'SEEK'
    k1 = pd.NaT
    leave_bar = pd.NaT
    eligible_start = pd.NaT
    for ts, r in exe.iterrows():
        hi, lo, cl = float(r.high), float(r.low), float(r.close)
        if state == 'SEEK':
            if cl > H or cl < L:
                return None
            hh = hi >= H and cl <= H
            ll = lo <= L and cl >= L
            if hh and ll:
                return None
            if side == 'LONG':
                if ll and not lo_touch:
                    lo_vis += 1
                if hh and not hi_touch:
                    hi_vis += 1
                    if hi_vis == 1 and lo_vis == 0:
                        k1 = ts
                        state = 'EP'
                hi_touch, lo_touch = hh, ll
                if lo_vis > 0 and state == 'SEEK':
                    return None
            else:
                if hh and not hi_touch:
                    hi_vis += 1
                if ll and not lo_touch:
                    lo_vis += 1
                    if lo_vis == 1 and hi_vis == 0:
                        k1 = ts
                        state = 'EP'
                hi_touch, lo_touch = hh, ll
                if hi_vis > 0 and state == 'SEEK':
                    return None
            continue
        if state == 'EP':
            if cl > H or cl < L:
                return {'k1': k1, 'clean': False, 'leave_bar': pd.NaT,
                        'eligible_start': pd.NaT, 'terminal': 'BREAK_DURING_K1',
                        'terminal_bar': ts}
            same = (hi >= H and cl <= H) if side == 'LONG' else (lo <= L and cl >= L)
            if same:
                continue
            leave_bar = ts
            eligible_start = ts + BAR5
            state = 'POST'
            continue
        if state == 'POST':
            h2 = (hi >= H) if side == 'LONG' else (lo <= L)
            opp = (cl < L) if side == 'LONG' else (cl > H)
            if h2 and opp:
                term = 'AMBIGUOUS'
            elif h2:
                term = 'H2'
            elif opp:
                term = 'OPPOSITE'
            else:
                continue
            return {'k1': k1, 'clean': True, 'leave_bar': leave_bar,
                    'eligible_start': eligible_start, 'terminal': term,
                    'terminal_bar': ts}
    if state == 'EP':
        return {'k1': k1, 'clean': False, 'leave_bar': pd.NaT,
                'eligible_start': pd.NaT, 'terminal': 'NO_LEAVE', 'terminal_bar': pd.NaT}
    if state == 'POST':
        return {'k1': k1, 'clean': True, 'leave_bar': leave_bar,
                'eligible_start': eligible_start, 'terminal': 'NO_H2', 'terminal_bar': pd.NaT}
    return None


def build_entries(x):
    out = []
    for d in pd.date_range(m.START.normalize(), m.END.normalize(), freq='D', tz='UTC'):
        for clock, (lvl, f, target, ext) in LOCKED.items():
            cm = m.CLOCKS[clock]
            rs = d + pd.Timedelta(minutes=cm)
            re = rs + m.REF
            es = re
            ee = es + m.EXE
            p = m.part(es)
            if p is None or es.weekday() >= 5 or ee > m.END:
                continue
            ref = m.sl(x, rs, re)
            exe = m.sl(x, es, ee)
            if len(ref) != 66 or len(exe) != 78:
                continue
            H = float(ref.high.max())
            L = float(ref.low.min())
            R = H - L
            if R <= 0:
                continue
            w = corrected_find_window(exe, H, L, 'LONG')
            if w is None or not w['clean']:
                continue
            c = m.candidate(exe, H, L, w, 'LONG', lvl, f)
            if not c['filled']:
                continue
            fill = pd.Timestamp(c['fill_ts'])
            terminal = pd.Timestamp(w['terminal_bar']) if pd.notna(w['terminal_bar']) else pd.NaT
            if c['outcome'] == 'H2' and not fill < terminal:
                raise AssertionError('entry/H2 chronology')
            entry = L + f * R
            target_px = H + ext * R
            out.append({
                'clock': clock, 'level': lvl, 'target_name': target,
                'target_extension': ext, 'partition': p,
                'date_utc': es.strftime('%Y-%m-%d'),
                'reference_start': rs, 'execution_start': es,
                'session_end': ee, 'H': H, 'L': L, 'R': R,
                'entry_ts': fill, 'entry_px': entry,
                'm2_outcome': c['outcome'],
                'h2_ts': terminal if c['outcome'] == 'H2' else pd.NaT,
                'target_px': target_px,
            })
    E = pd.DataFrame(out)
    assert not E.empty
    return E


def next_open(x, ts):
    i = int(x.index.searchsorted(ts, side='left'))
    if i >= len(x):
        return None
    return x.index[i], float(x.iloc[i].open)


def simulate(x, r, mode, dist, stop_fraction):
    entry_ts = pd.Timestamp(r.entry_ts)
    session_end = pd.Timestamp(r.session_end)
    H, L, R = float(r.H), float(r.L), float(r.R)
    entry = float(r.entry_px)
    target = float(r.target_px)
    boundary = L + float(stop_fraction) * R
    q = x.iloc[int(x.index.searchsorted(entry_ts)):int(x.index.searchsorted(session_end))]
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError('missing entry bar')
    assert L < boundary < entry < H < target
    h2 = pd.Timestamp(r.h2_ts) if pd.notna(r.h2_ts) else pd.NaT
    h2_seen = False
    accept = False
    exit_bar = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = ''

    for k, (ts, b) in enumerate(q.iterrows()):
        high, low, close = float(b.high), float(b.low), float(b.close)
        if pd.notna(h2) and ts >= h2:
            h2_seen = True
        if mode == 'HARD_TOUCH':
            tp = high >= target
            st = low <= boundary
            if tp and st:
                # OHLC cannot reveal intrabar order; conservative hard-stop-first treatment.
                reason = 'HARD_STOP_AMBIGUOUS_SAME_BAR'
                exit_bar = ts
                exit_ts = ts
                exit_px = boundary
                break
            if st:
                reason = 'HARD_STOP'
                exit_bar = ts
                exit_ts = ts
                exit_px = boundary
                break
            if tp:
                reason = f'TP_{r.target_name}'
                exit_bar = ts
                exit_ts = ts
                exit_px = target
                break
        else:
            # A resting target is known intrabar before the completed close.
            if high >= target:
                reason = f'TP_{r.target_name}'
                exit_bar = ts
                exit_ts = ts
                exit_px = target
                break
            if close < boundary:
                nxt = ts + BAR5
                if nxt <= session_end:
                    op = next_open(x, nxt)
                    if op is not None and op[0] == nxt:
                        reason = 'CLOSE_INVALIDATION'
                        exit_bar = ts
                        exit_ts = op[0]
                        exit_px = op[1]
                        break
        if close > H:
            accept = True

    if not reason:
        op = next_open(x, session_end)
        if op is None:
            raise AssertionError('missing session-end open')
        exit_ts, exit_px = op
        exit_bar = exit_ts
        reason = 'TIME_EXIT_SESSION_END'
        if pd.notna(h2) and h2 < session_end:
            h2_seen = True

    gross = exit_px / entry - 1.0
    net = gross * NOTIONAL - FEE
    hold = (pd.Timestamp(exit_ts) - entry_ts) / pd.Timedelta(minutes=1)
    return {
        'mode': mode, 'stop_distance': dist, 'stop_fraction': stop_fraction,
        'stop_px': boundary, 'exit_bar_start': exit_bar, 'exit_ts': exit_ts,
        'exit_px': exit_px, 'exit_reason': reason, 'gross_return': gross,
        'net_pnl_usd': net, 'hold_minutes': float(hold),
        'h2_before_exit': bool(h2_seen),
        'close_above_H_before_exit': bool(accept),
        'nominal_rr': (target - entry) / (entry - boundary),
    }


def pf(s):
    x = pd.to_numeric(s, errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    return np.inf if neg == 0 and pos > 0 else (pos / neg if neg > 0 else np.nan)


def summarize(g):
    x = pd.to_numeric(g.net_pnl_usd, errors='coerce').dropna()
    w = x[x > 0]
    l = x[x <= 0]
    reasons = g.exit_reason.astype(str)
    return {
        'trades': len(x),
        'tp_count': int(reasons.str.startswith('TP_').sum()),
        'tp_rate': float(reasons.str.startswith('TP_').mean()) if len(x) else np.nan,
        'stop_count': int(reasons.str.contains('STOP|INVALIDATION').sum()),
        'time_exit_count': int((reasons == 'TIME_EXIT_SESSION_END').sum()),
        'wins': int((x > 0).sum()), 'losses': int((x <= 0).sum()),
        'wr': float((x > 0).mean()) if len(x) else np.nan,
        'pf': pf(x), 'net_exp': float(x.mean()) if len(x) else np.nan,
        'total_net': float(x.sum()) if len(x) else np.nan,
        'median_win': float(w.median()) if len(w) else np.nan,
        'median_loss': float(l.median()) if len(l) else np.nan,
        'median_hold_minutes': float(g.hold_minutes.median()) if len(g) else np.nan,
        'h2_before_exit_rate': float(g.h2_before_exit.mean()) if len(g) else np.nan,
        'close_above_H_before_exit_rate': float(g.close_above_H_before_exit.mean()) if len(g) else np.nan,
        'median_nominal_rr': float(g.nominal_rr.median()) if len(g) else np.nan,
    }


def synthetic_tests():
    idx = pd.date_range('2026-01-02 13:30', periods=5, freq='5min', tz='UTC')
    x = pd.DataFrame({
        'open': [98.5, 98, 100, 101, 100],
        'high': [99, 99, 100.2, 101.5, 101],
        'low': [98, 95, 99.5, 100, 100],
        'close': [98.5, 96, 99.9, 101, 100.5],
    }, index=idx)
    r = pd.Series({'entry_ts': idx[0], 'entry_px': 98.5, 'H': 100., 'L': 90., 'R': 10.,
                   'target_px': 101., 'target_name': 'E10',
                   'session_end': idx[-1] + BAR5, 'h2_ts': idx[2]})
    z = simulate(x, r, 'CLOSE_NEXT_OPEN', 0.30, 0.55)
    assert z['exit_reason'] == 'TP_E10'
    x2 = x.copy(); x2.loc[idx[1], 'close'] = 95.
    z2 = simulate(x2, r, 'CLOSE_NEXT_OPEN', 0.30, 0.55)
    assert z2['exit_reason'] == 'CLOSE_INVALIDATION'
    x3 = x.copy(); x3.loc[idx[1], 'low'] = 95.
    z3 = simulate(x3, r, 'HARD_TOUCH', 0.30, 0.55)
    assert z3['exit_reason'] == 'HARD_STOP'
    x4 = x.copy(); x4.loc[idx[2], 'high'] = 101.5; x4.loc[idx[2], 'low'] = 95.; x4.loc[idx[2], 'close'] = 95.
    z4 = simulate(x4, r, 'CLOSE_NEXT_OPEN', 0.30, 0.55)
    assert z4['exit_reason'] == 'TP_E10'


def main():
    synthetic_tests()
    x, coverage = m.load5()
    assert coverage >= .995
    E = build_entries(x)
    rows = []
    for r in E.to_dict('records'):
        for mode, (dist, sf) in STOP_CANDIDATES[r['clock']].items():
            rows.append({**r, **simulate(x, pd.Series(r), mode, dist, sf)})
    T = pd.DataFrame(rows)
    assert len(T) == len(E) * 2
    T.to_csv(OUT_DETAIL, index=False)

    sums = []
    for clock in LOCKED:
        for mode in STOP_CANDIDATES[clock]:
            for p in (*PARTS, 'POOLED_MAJOR'):
                g = T[(T.clock == clock) & (T.mode == mode)]
                g = g[g.partition.isin(MAJOR)] if p == 'POOLED_MAJOR' else g[g.partition == p]
                z = summarize(g)
                z.update({
                    'clock': clock, 'level': LOCKED[clock][0],
                    'target': LOCKED[clock][2], 'target_extension': LOCKED[clock][3],
                    'mode': mode, 'partition': p,
                    'stop_distance': STOP_CANDIDATES[clock][mode][0],
                    'stop_fraction': STOP_CANDIDATES[clock][mode][1],
                })
                sums.append(z)
    S = pd.DataFrame(sums)
    S.to_csv(OUT_SUM, index=False)

    # Exact economic screen inherited from B27Z:
    # each major partition >=30 resolved trades, WR>=70%, positive net expectancy, PF>=1.20.
    selections = []
    for clock in LOCKED:
        for mode in STOP_CANDIDATES[clock]:
            maj = S[(S.clock == clock) & (S.mode == mode) & (S.partition.isin(MAJOR))]
            ok = (len(maj) == 3 and (maj.trades >= 30).all() and
                  (maj.wr >= .70).all() and (maj.net_exp > 0).all() and
                  (maj.pf >= 1.20).all())
            selections.append({
                'clock': clock, 'level': LOCKED[clock][0], 'target': LOCKED[clock][2],
                'mode': mode, 'stop_distance': STOP_CANDIDATES[clock][mode][0],
                'stop_fraction': STOP_CANDIDATES[clock][mode][1], 'screen_pass': bool(ok),
                'min_wr_major': float(maj.wr.min()) if len(maj) else np.nan,
                'min_pf_major': float(maj.pf.min()) if len(maj) else np.nan,
                'min_net_exp_major': float(maj.net_exp.min()) if len(maj) else np.nan,
                'pooled_net_exp': float(S[(S.clock == clock) & (S.mode == mode) & (S.partition == 'POOLED_MAJOR')].net_exp.iloc[0]),
            })
    SEL = pd.DataFrame(selections)
    chosen = []
    for clock in LOCKED:
        c = SEL[SEL.clock == clock]
        p = c[c.screen_pass]
        if len(p):
            q = p.sort_values(['min_net_exp_major', 'min_pf_major', 'min_wr_major'], ascending=False).iloc[0]
            status = 'LOCKED'
        else:
            q = c.sort_values(['min_net_exp_major', 'min_pf_major', 'min_wr_major'], ascending=False).iloc[0]
            status = 'NONE_PASS'
        chosen.append({**q.to_dict(), 'status': status})
    CH = pd.DataFrame(chosen)
    CH.to_csv(OUT_SEL, index=False)

    lines = [
        '# ETH Transfer — M8 Economic Combination Backtest — Result', '',
        f'Raw ETH 5m coverage: **{coverage:.4%}**.', '',
        f'Illustrative notional: **${NOTIONAL:.0f}**; round-trip fee: **${FEE:.2f}**.', '',
        'Frozen entries/targets: ALT F95→E30; RAW0530 F90→E30; LONDON F90→E25; RAW2330 F95→E15.', '',
        '| Habitat | Entry→Target | Hard stop | Close invalidation | Economic selection |',
        '|---|---|---|---|---|',
    ]
    for r in CH.itertuples(index=False):
        hs = SEL[(SEL.clock == r.clock) & (SEL.mode == 'HARD_TOUCH')].iloc[0]
        cs = SEL[(SEL.clock == r.clock) & (SEL.mode == 'CLOSE_NEXT_OPEN')].iloc[0]
        hsx = f"{'PASS' if hs.screen_pass else 'FAIL'} D{int(hs.stop_distance*100):02d}/F{int(hs.stop_fraction*100):02d}"
        csx = f"{'PASS' if cs.screen_pass else 'FAIL'} D{int(cs.stop_distance*100):02d}/F{int(cs.stop_fraction*100):02d}"
        lines.append(f'| {r.clock} | {r.level}→{r.target} | {hsx} | {csx} | **{r.status}**: {r.mode} |')
    lines += [
        '',
        'Screen = each major partition has ≥30 resolved trades, WR ≥70%, positive net expectancy, PF ≥1.20. August is telemetry only.',
        '', '**Status: ETH_M8_ECONOMIC_COMBINATION_COMPLETED**',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('ETH_M8_ECONOMIC_COMBINATION_COMPLETED\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
