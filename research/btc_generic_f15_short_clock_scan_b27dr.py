#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_london_ny_short_mirror_b27ad as b27ad

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_Result.md'
OUT_CASES = ROOT / 'BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_Cases.csv'
OUT_SUM = ROOT / 'BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_Summary.csv'
OUT_LEADER = ROOT / 'BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_DevelopmentLeaderboard.csv'
OUT_PARITY = ROOT / 'BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_LondonParity.csv'
OUT_STATUS = ROOT / 'BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_Status.txt'

PARTS = b22b.PARTS
PART_ORDER = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
BAR5 = pd.Timedelta(minutes=5)
REF_DUR = pd.Timedelta(hours=5, minutes=30)
EXEC_DUR = pd.Timedelta(hours=6, minutes=30)
REF_BARS = 66
EXEC_BARS = 78
CLOCKS_MIN = tuple(range(0, 24 * 60, 30))
BASELINE_MIN = 8 * 60


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def part_for_window(ref_start, exec_start, exec_end):
    for name, (a, z) in PARTS.items():
        if ref_start >= a and exec_start >= a and exec_end <= z:
            return name
    return None


def clock_label(minute):
    base = pd.Timestamp('2026-01-01', tz='UTC') + pd.Timedelta(minutes=minute)
    ref_end = base + REF_DUR; exec_end = ref_end + EXEC_DUR
    def f(t):
        dayoff = int((t.normalize() - base.normalize()) / pd.Timedelta(days=1))
        core = t.strftime('%H:%M')
        return core if dayoff == 0 else f'{core}+{dayoff}d'
    return f(base), f(ref_end), f(exec_end)


def find_short_k1(exe, H, L):
    hi_touching = lo_touching = False
    hi_visits = lo_visits = 0
    for ts, r in exe.iterrows():
        close = float(r.close)
        if close > H or close < L:
            return None
        hit_hi = float(r.high) >= H and close <= H
        hit_lo = float(r.low) <= L and close >= L
        if hit_hi and hit_lo:
            return None
        if hit_lo and not lo_touching:
            lo_visits += 1
            if lo_visits == 1 and hi_visits == 0:
                return ts
        if hit_hi and not hi_touching:
            hi_visits += 1
        hi_touching = bool(hit_hi); lo_touching = bool(hit_lo)
    return None


def empty_case(part, anchor, clock_min, ref_start, ref_end, exec_start, exec_end, status):
    return {
        'partition': part, 'anchor_date_utc': str(anchor.date()), 'clock_min': clock_min,
        'reference_start': ref_start, 'reference_end': ref_end,
        'execution_start': exec_start, 'execution_end': exec_end,
        'case_status': status, 'k1_signal_ts': pd.NaT, 'leave_ts': pd.NaT,
        'blind_filled': False, 'h2_after_fill': False,
        'same_bar_confirmed': False, 'entry_executed': False,
        'fixed_net_pnl_usd': np.nan, 'fixed_exit_reason': status,
        'fixed_e20_reached': False,
    }


def build_case(x5, anchor, clock_min):
    ref_start = anchor + pd.Timedelta(minutes=clock_min)
    ref_end = ref_start + REF_DUR
    exec_start = ref_end; exec_end = exec_start + EXEC_DUR
    part = part_for_window(ref_start, exec_start, exec_end)
    if part is None or exec_start.weekday() >= 5: return None
    ref = fast_slice(x5, ref_start, ref_end); exe = fast_slice(x5, exec_start, exec_end)
    if len(ref) != REF_BARS or len(exe) != EXEC_BARS:
        return empty_case(part, anchor, clock_min, ref_start, ref_end, exec_start, exec_end, 'DATA_GAP')
    H = float(ref.high.max()); L = float(ref.low.min())
    if not (math.isfinite(H) and math.isfinite(L) and H > L):
        return empty_case(part, anchor, clock_min, ref_start, ref_end, exec_start, exec_end, 'INVALID_RANGE')
    sig_start = find_short_k1(exe, H, L)
    if sig_start is None:
        return empty_case(part, anchor, clock_min, ref_start, ref_end, exec_start, exec_end, 'NO_K1_OPP0')

    s = pd.Series({
        'partition': part, 'date_utc': str(anchor.date()),
        'previous_session_high': H, 'previous_session_low': L,
        'signal_bar_start': sig_start, 'signal_ts': sig_start + BAR5,
        'active_session_end': exec_end,
    })
    w = pd.Series(b27ad.build_window(x5, s))
    blind = pd.Series(b27ad.blind_f15(x5, w))
    entry = pd.Series(b27ad.confirm_rejection_entry(x5, blind, same_bar_only=True))
    fixed = b27ad.simulate_fixed(x5, entry)

    d = {
        'partition': part, 'anchor_date_utc': str(anchor.date()), 'clock_min': clock_min,
        'reference_start': ref_start, 'reference_end': ref_end,
        'execution_start': exec_start, 'execution_end': exec_end,
        'case_status': str(entry.entry_status),
        'k1_signal_ts': sig_start + BAR5,
        'leave_ts': w.leave_ts,
        'window_status': w.window_status,
        'H': H, 'L': L, 'range': H-L,
        'F15': blind.F15, 'F65': blind.F65, 'E20_DOWN': blind.E20_DOWN,
        'blind_filled': bool(blind.blind_filled),
        'blind_touch_bar_start': blind.blind_touch_bar_start,
        'h2_after_fill': bool(blind.h2_after_fill),
        'same_bar_confirmed': bool(entry.confirmation_kind == 'SAME_BAR'),
        'confirmation_bar_start': entry.confirmation_bar_start,
        'entry_executed': bool(entry.entry_executed),
        'entry_start': entry.entry_start, 'entry_px': entry.entry_px,
        'entry_fraction': entry.entry_fraction,
    }
    d.update(fixed)
    return d


def summarize(g):
    k1 = g[g.k1_signal_ts.notna()]
    clean = g[g.leave_ts.notna()]
    touch = g[g.blind_filled.astype(bool)]
    conf = g[g.same_bar_confirmed.astype(bool)]
    tr = g[g.entry_executed.astype(bool) & g.fixed_net_pnl_usd.notna()]
    vals = pd.to_numeric(tr.fixed_net_pnl_usd, errors='coerce')
    return {
        'days': len(g), 'k1_opp0': len(k1), 'clean_windows': len(clean),
        'f15_touches': len(touch),
        'h2_after_f15_touch_rate': float(touch.h2_after_fill.astype(bool).mean()) if len(touch) else np.nan,
        'same_bar_confirmations': len(conf), 'trades': len(tr),
        'wins': int((vals > 0).sum()) if len(tr) else 0,
        'wr': float((vals > 0).mean()) if len(tr) else np.nan,
        'pf': pf(vals) if len(tr) else np.nan,
        'expectancy': float(vals.mean()) if len(tr) else np.nan,
        'total_net': float(vals.sum()) if len(tr) else 0.0,
        'tp_rate': float(tr.fixed_e20_reached.astype(bool).mean()) if len(tr) else np.nan,
        'time_exit_rate': float((tr.fixed_exit_reason == 'TIME_EXIT_SESSION_END').mean()) if len(tr) else np.nan,
    }


def dev_eligible(r):
    return bool(int(r.trades) >= 25 and pd.notna(r.wr) and r.wr >= .70 and
                pd.notna(r.pf) and r.pf >= 1.30 and pd.notna(r.expectancy) and r.expectancy > 0)


def historical_replication_supported(summary, clock_min):
    for part, nmin in (('external', 15), ('reference_validation', 10)):
        r = summary[(summary.clock_min == clock_min) & (summary.partition == part)].iloc[0]
        if not (int(r.trades) >= nmin and pd.notna(r.wr) and r.wr >= .65 and
                pd.notna(r.pf) and r.pf >= 1.20 and pd.notna(r.expectancy) and r.expectancy > 0):
            return False
    return True


def london_parity(cases):
    tr = cases[(cases.clock_min == BASELINE_MIN) & cases.entry_executed.astype(bool) &
               cases.fixed_net_pnl_usd.notna()].copy()
    rows = []
    expected = {'external':25, 'development':25, 'reference_validation':12, 'august':1}
    for part in PART_ORDER:
        n = len(tr[tr.partition == part])
        rows.append({'check':f'count_{part}', 'actual':n, 'expected':expected[part], 'pass':n == expected[part]})
    major = tr[tr.partition.isin(MAJOR)]
    vals = pd.to_numeric(major.fixed_net_pnl_usd, errors='coerce')
    n = len(major); wins = int((vals > 0).sum()); wr = float((vals > 0).mean()); p = pf(vals)
    exp = float(vals.mean()); total = float(vals.sum())
    rows += [
        {'check':'pooled_major_n','actual':n,'expected':62,'pass':n==62},
        {'check':'pooled_major_wins','actual':wins,'expected':36,'pass':wins==36},
        {'check':'pooled_major_wr','actual':wr,'expected':36/62,'pass':abs(wr-36/62)<1e-12},
        {'check':'pooled_major_pf','actual':p,'expected':.73,'pass':abs(p-.73)<=.03},
        {'check':'pooled_major_expectancy','actual':exp,'expected':-.44,'pass':abs(exp+.44)<=.03},
        {'check':'pooled_major_total','actual':total,'expected':-27.49,'pass':abs(total+27.49)<=.15},
    ]
    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DR London SHORT parity failed:\n' + out.to_string(index=False))
    return out


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.2f}'


def main():
    x5, coverage = b21.load5()
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    rows = []
    for anchor in anchors:
        for clock_min in CLOCKS_MIN:
            r = build_case(x5, anchor, clock_min)
            if r is not None: rows.append(r)
    cases = pd.DataFrame(rows)
    if cases.empty: raise RuntimeError('no B27DR cases')
    parity = london_parity(cases)

    sums = []
    for clock_min in CLOCKS_MIN:
        rs, es, ee = clock_label(clock_min)
        for part in PART_ORDER:
            g = cases[(cases.clock_min == clock_min) & (cases.partition == part)]
            sums.append({'clock_min':clock_min,'reference_start_utc':rs,'execution_start_utc':es,
                         'execution_end_utc':ee,'partition':part,**summarize(g)})
    summary = pd.DataFrame(sums)
    dev = summary[summary.partition == 'development'].copy()
    dev['dev_eligible'] = dev.apply(dev_eligible, axis=1)
    dev['is_london_baseline'] = dev.clock_min == BASELINE_MIN
    leader = dev.sort_values(['dev_eligible','pf','wr','expectancy','trades','clock_min'],
                             ascending=[False,False,False,False,False,True]).reset_index(drop=True)
    eligible = leader[leader.dev_eligible & ~leader.is_london_baseline]
    selected = None if eligible.empty else eligible.iloc[0]
    if selected is None:
        status='B27DR_NO_NEW_SHORT_CLOCK_CANDIDATE'; replication=False
    else:
        sel=int(selected.clock_min); replication=historical_replication_supported(summary, sel)
        status=('B27DR_NEW_SHORT_CLOCK_HISTORICAL_REPLICATION_SUPPORTED' if replication
                else 'B27DR_NEW_SHORT_CLOCK_DEV_CANDIDATE_NOT_REPLICATED')

    cases.to_csv(OUT_CASES,index=False); summary.to_csv(OUT_SUM,index=False)
    leader.to_csv(OUT_LEADER,index=False); parity.to_csv(OUT_PARITY,index=False)
    OUT_STATUS.write_text(status+'\n')

    lines=['# B27DR — Generic F15 SHORT Clock-Rotation Scan — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
           '**London SHORT parity: PASS.** Generic 08:00 UTC reproduced persisted B27AD SAME_BAR_REJECTION fixed-E20_DOWN control.','',
           '## Development clock leaderboard','',
           '| Ref | Exec | End | N | WR | PF | Exp | Net | K1 | F15 | H2/F15 | Same-bar | Eligible |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in leader.head(20).itertuples(index=False):
        lines.append(f'| {r.reference_start_utc} | {r.execution_start_utc} | {r.execution_end_utc} | {r.trades} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {r.k1_opp0} | {r.f15_touches} | {pct(r.h2_after_f15_touch_rate)} | {r.same_bar_confirmations} | {"YES" if r.dev_eligible else "NO"} |')
    lines += ['','## London baseline','',
              '| Partition | N | WR | PF | Exp | Net | H2/F15 | TP |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for part in PART_ORDER:
        r=summary[(summary.clock_min==BASELINE_MIN)&(summary.partition==part)].iloc[0]
        lines.append(f'| {part} | {r.trades} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {pct(r.h2_after_f15_touch_rate)} | {pct(r.tp_rate)} |')
    lines += ['','## New SHORT clock selection','']
    if selected is None:
        lines.append('No non-London clock passed the frozen development gate.')
    else:
        sel=int(selected.clock_min); rs,es,ee=clock_label(sel)
        lines.append(f'Selected development clock: **reference {rs} -> execution {es}-{ee} UTC**.')
        lines.append(f'Development N={int(selected.trades)}, WR={pct(selected.wr)}, PF={num(selected.pf)}, exp=${num(selected.expectancy)}, net=${num(selected.total_net)}, H2/F15={pct(selected.h2_after_f15_touch_rate)}.')
        lines.append(f'Historical external + reference-validation replication: **{"SUPPORTED" if replication else "NOT SUPPORTED"}**.')
        lines += ['','| Partition | N | WR | PF | Exp | Net | H2/F15 | TP |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for part in PART_ORDER:
            r=summary[(summary.clock_min==sel)&(summary.partition==part)].iloc[0]
            lines.append(f'| {part} | {r.trades} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {pct(r.h2_after_f15_touch_rate)} | {pct(r.tp_rate)} |')
    lines += ['',f'**Status: {status}**','',
              'Guardrail: 48-clock historical discovery with frozen SHORT structure; reused historical partitions are not pristine unseen OOS.','',
              'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
