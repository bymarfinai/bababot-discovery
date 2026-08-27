#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py'
spec = importlib.util.spec_from_file_location('eth_m2_base', BASE_PATH)
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
            eligible_start = ts + m.BAR5
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
                'eligible_start': pd.NaT, 'terminal': 'NO_LEAVE',
                'terminal_bar': pd.NaT}
    if state == 'POST':
        return {'k1': k1, 'clean': True, 'leave_bar': leave_bar,
                'eligible_start': eligible_start, 'terminal': 'NO_H2',
                'terminal_bar': pd.NaT}
    return None


def synthetic_tests():
    H, L = 100.0, 90.0
    idx = pd.date_range('2026-01-05 09:00', periods=6, freq='5min', tz='UTC')
    q = pd.DataFrame([
        [99.0, 100.2, 99.0, 99.5], [99.5, 100.1, 99.0, 99.3],
        [99.3, 99.6, 98.2, 98.4], [98.4, 99.0, 98.3, 98.8],
        [98.8, 100.2, 98.7, 99.7], [99.7, 101.0, 99.5, 100.5],
    ], index=idx, columns=['open','high','low','close'])
    w = corrected_find_window(q, H, L, 'LONG')
    assert w['leave_bar'] == idx[2] and w['eligible_start'] == idx[3]
    c = m.candidate(q, H, L, w, 'LONG', 'F85', .85)
    assert c['filled'] and c['fill_ts'] == idx[3]
    q2=q.copy(); q2.loc[idx[3],['high','low','close']]=[100.2,98.0,99.7]
    w2=corrected_find_window(q2,H,L,'LONG'); c2=m.candidate(q2,H,L,w2,'LONG','F85',.85)
    assert w2['terminal']=='H2' and not c2['filled']
    s = pd.DataFrame([
        [91.0,91.2,89.8,90.5],[90.5,91.0,89.9,90.7],[90.7,91.6,90.2,91.0],
        [91.0,91.7,90.8,91.2],[91.2,91.4,89.8,90.4],[90.4,90.8,89.5,89.8],
    ], index=idx, columns=['open','high','low','close'])
    ws=corrected_find_window(s,H,L,'SHORT'); cs=m.candidate(s,H,L,ws,'SHORT','F15',.15)
    assert ws['leave_bar']==idx[2] and ws['eligible_start']==idx[3] and cs['fill_ts']==idx[3]


def main():
    synthetic_tests()
    m.find_window = corrected_find_window
    m.main()
    result = m.OUT_MD.read_text()
    note = ('\n> **Causal correction applied:** first eligible bar is exactly the raw 5m bar '
            'immediately following the completed leave bar (`leave_start + 5m`). '
            'The prior +10m M2 output is superseded.\n')
    if 'Causal correction applied' not in result:
        lines=result.splitlines(); lines.insert(2,note.strip()); m.OUT_MD.write_text('\n'.join(lines)+'\n')
    m.OUT_STATUS.write_text('ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY\n')


if __name__ == '__main__':
    import subprocess, sys
    subprocess.run([sys.executable, str(HERE / 'eth_f85_f15_transfer_m6_invalidation_atlas.py')], check=True)
