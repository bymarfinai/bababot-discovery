#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_b27do_live_executable_exit_b27dq as dq
import btc_generic_f15_short_clock_scan_b27dr as dr

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Summary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Detail.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_F15_SHORT_COLLISION_B27DT_Status.txt'

PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
CLOCKS = {
    'SHORT_2000': 1200,
    'SHORT_0430': 270,
    'SHORT_0330': 210,
    'SHORT_0300': 180,
    'SHORT_2100': 1260,
    'SHORT_0000': 0,
}
SETS = {**{k: (v,) for k, v in CLOCKS.items()}, 'SHORT6_BASKET': tuple(CLOCKS.values())}


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def metrics(d):
    if d is None or len(d) == 0:
        return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v = pd.to_numeric(d.pnl, errors='coerce').dropna()
    return {
        'n': int(len(v)), 'wins': int((v > 0).sum()),
        'wr': float((v > 0).mean()) if len(v) else np.nan,
        'pf': pf(v), 'expectancy': float(v.mean()) if len(v) else np.nan,
        'net': float(v.sum()),
    }


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'
def usd(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'


def normalize_long(d, accepted_source=False):
    q = d.copy()
    q['entry_ts'] = pd.to_datetime(q.entry_bar_start, utc=True)
    q['exit_ts_norm'] = pd.to_datetime(q.exit_ts, utc=True)
    q['pnl'] = pd.to_numeric(q.net_pnl_usd, errors='coerce')
    q['side'] = 'LONG'
    q['source'] = 'LONG_' + q.zone.astype(str)
    q['clock_min_norm'] = -1
    q['candidate_id'] = (q.partition.astype(str) + '|LONG|' + q.zone.astype(str) + '|' + q.entry_ts.astype(str))
    cols = ['partition','entry_ts','exit_ts_norm','pnl','side','source','clock_min_norm','candidate_id']
    if accepted_source and 'accepted' in q.columns:
        q = q[q.accepted.astype(bool)]
    return q[cols].dropna(subset=['entry_ts','exit_ts_norm','pnl']).reset_index(drop=True)


def normalize_short(cases):
    q = cases[cases.entry_executed.astype(bool) & cases.fixed_net_pnl_usd.notna()].copy()
    q['entry_ts'] = pd.to_datetime(q.entry_start, utc=True)
    q['exit_ts_norm'] = q.entry_ts + pd.to_timedelta(pd.to_numeric(q.fixed_hold_minutes), unit='m')
    q['pnl'] = pd.to_numeric(q.fixed_net_pnl_usd, errors='coerce')
    q['side'] = 'SHORT'
    rev = {v:k for k,v in CLOCKS.items()}
    q['source'] = q.clock_min.map(rev)
    q['clock_min_norm'] = pd.to_numeric(q.clock_min).astype(int)
    q['candidate_id'] = (q.partition.astype(str) + '|SHORT|' + q.clock_min.astype(str) + '|' + q.entry_ts.astype(str))
    return q[['partition','entry_ts','exit_ts_norm','pnl','side','source','clock_min_norm','candidate_id']].reset_index(drop=True)


def build_long(x5):
    stream = dq.dn.dl.load_stream(x5)
    live = dq.attach_live_runner(stream, x5)
    hybrid = dq.build_live_hybrid(stream, live)
    locked_parts = []
    for part in PARTS:
        z = dq.dn.dl.dg.lock(hybrid[hybrid.partition == part].copy(), f'B27DT_LONG_BASE_{part}')
        locked_parts.append(z)
    locked = pd.concat(locked_parts, ignore_index=True)
    pooled = locked[locked.partition.isin(MAJOR)].copy()
    s = dq.summarize(pooled)
    if not (int(s['accepted']) == 227 and abs(float(s['wr']) - .722) <= .003 and
            abs(float(s['pf']) - 2.25) <= .03 and abs(float(s['total_net']) - 289.76) <= .20 and
            int(s['max_loss_streak']) == 3):
        raise AssertionError('B27DQ baseline parity failed: ' + str(s))
    return hybrid, locked, s


def build_shorts(x5):
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    rows = []
    for anchor in anchors:
        for cm in sorted(set(CLOCKS.values())):
            r = dr.build_case(x5, anchor, cm)
            if r is not None:
                rows.append(r)
    if not rows: raise RuntimeError('no B27DT short cases')
    return pd.DataFrame(rows)


def interval_overlap(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def lock_rows(d, label):
    rows = []
    for part in PARTS:
        q = d[d.partition == part].copy()
        if q.empty: continue
        q['side_order'] = q.side.map({'LONG':0,'SHORT':1}).fillna(9)
        q = q.sort_values(['entry_ts','side_order','clock_min_norm','candidate_id']).reset_index(drop=True)
        active_exit = pd.NaT; active_side = None; active_id = None
        for r in q.itertuples(index=False):
            accept = pd.isna(active_exit) or pd.Timestamp(r.entry_ts) >= pd.Timestamp(active_exit)
            rec = r._asdict()
            rec['portfolio'] = label
            rec['accepted_portfolio'] = bool(accept)
            rec['blocked_by_side'] = None if accept else active_side
            rec['blocked_by_id'] = None if accept else active_id
            rows.append(rec)
            if accept:
                active_exit = pd.Timestamp(r.exit_ts_norm)
                active_side = r.side
                active_id = r.candidate_id
    return pd.DataFrame(rows)


def long_protected(shorts, baseline_long_norm, set_name):
    s = shorts.copy()
    blocked_long = []
    for r in s.itertuples(index=False):
        l = baseline_long_norm[baseline_long_norm.partition == r.partition]
        hit = False
        for z in l.itertuples(index=False):
            if interval_overlap(pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts_norm),
                                pd.Timestamp(z.entry_ts), pd.Timestamp(z.exit_ts_norm)):
                hit = True; break
        blocked_long.append(hit)
    s['blocked_by_long'] = blocked_long
    eligible = s[~s.blocked_by_long].copy()
    locked_short = lock_rows(eligible, f'{set_name}_LONG_PROTECTED_SHORT_LOCK')
    accepted = locked_short[locked_short.accepted_portfolio.astype(bool)].copy() if len(locked_short) else locked_short
    blocked_by_short = int((~locked_short.accepted_portfolio.astype(bool)).sum()) if len(locked_short) else 0
    return s, locked_short, accepted, int(s.blocked_by_long.sum()), blocked_by_short


def first_signal(raw_long_norm, shorts, set_name):
    merged = pd.concat([raw_long_norm, shorts], ignore_index=True)
    return lock_rows(merged, f'{set_name}_FIRST_SIGNAL')


def pooled_major(d):
    return d[d.partition.isin(MAJOR)].copy()


def summarize_set(set_name, clock_tuple, short_all, raw_long_norm, baseline_long_norm, baseline_net):
    shorts = short_all[short_all.clock_min_norm.isin(clock_tuple)].copy()
    standalone = metrics(pooled_major(shorts))

    _, lp_lock, lp_acc, blocked_long, blocked_short = long_protected(shorts, baseline_long_norm, set_name)
    lp_major = pooled_major(lp_acc)
    lpm = metrics(lp_major)

    fs = first_signal(raw_long_norm, shorts, set_name)
    fs_acc = fs[fs.accepted_portfolio.astype(bool)].copy()
    fs_major = pooled_major(fs_acc)
    fsm = metrics(fs_major)
    fs_long = fs_major[fs_major.side == 'LONG']; fs_short = fs_major[fs_major.side == 'SHORT']
    flm = metrics(fs_long); fsm_s = metrics(fs_short)

    base_ids = set(pooled_major(baseline_long_norm).candidate_id)
    fs_long_ids = set(fs_long.candidate_id)
    displaced_ids = base_ids - fs_long_ids
    displaced = pooled_major(baseline_long_norm)
    displaced = displaced[displaced.candidate_id.isin(displaced_ids)]
    displaced_n = len(displaced); displaced_net = float(displaced.pnl.sum()) if len(displaced) else 0.0

    fs_major_all = pooled_major(fs)
    short_blocked_by_long = int(((~fs_major_all.accepted_portfolio.astype(bool)) & (fs_major_all.side == 'SHORT') & (fs_major_all.blocked_by_side == 'LONG')).sum())
    long_blocked_by_short = int(((~fs_major_all.accepted_portfolio.astype(bool)) & (fs_major_all.side == 'LONG') & (fs_major_all.blocked_by_side == 'SHORT')).sum())

    if fsm['net'] <= baseline_net + 1e-12:
        label = 'PORTFOLIO_DEGRADES'
    elif displaced_n == 0 and flm['net'] >= baseline_net - 1e-9:
        label = 'FIRST_SIGNAL_ADDS_WITHOUT_LONG_DAMAGE'
    else:
        label = 'FIRST_SIGNAL_ADDS_WITH_LONG_DISPLACEMENT'

    row = {
        'set': set_name,
        'standalone_n': standalone['n'], 'standalone_wr': standalone['wr'], 'standalone_pf': standalone['pf'], 'standalone_net': standalone['net'],
        'lp_blocked_by_long': blocked_long, 'lp_blocked_by_short': blocked_short,
        'lp_short_n': lpm['n'], 'lp_short_wr': lpm['wr'], 'lp_short_pf': lpm['pf'], 'lp_short_net': lpm['net'],
        'lp_combined_net': baseline_net + lpm['net'], 'lp_delta_vs_long': lpm['net'],
        'fs_total_n': fsm['n'], 'fs_total_wr': fsm['wr'], 'fs_total_pf': fsm['pf'], 'fs_total_net': fsm['net'], 'fs_delta_vs_long': fsm['net'] - baseline_net,
        'fs_long_n': flm['n'], 'fs_long_wr': flm['wr'], 'fs_long_net': flm['net'],
        'fs_short_n': fsm_s['n'], 'fs_short_wr': fsm_s['wr'], 'fs_short_net': fsm_s['net'],
        'fs_displaced_baseline_long_n': displaced_n, 'fs_displaced_baseline_long_net': displaced_net,
        'fs_short_blocked_by_long': short_blocked_by_long, 'fs_long_blocked_by_short': long_blocked_by_short,
        'classification': label,
    }

    detail = []
    if len(lp_lock):
        x = lp_lock.copy(); x['set'] = set_name; x['scenario'] = 'LONG_PROTECTED'; detail.append(x)
    if len(fs):
        x = fs.copy(); x['set'] = set_name; x['scenario'] = 'FIRST_SIGNAL_WINS'; detail.append(x)
    return row, detail


def main():
    x5, coverage = dq.dn.dl.dj.b21.load5()
    raw_long, locked_long, base = build_long(x5)
    raw_long_norm = normalize_long(raw_long, accepted_source=False)
    baseline_long_norm = normalize_long(locked_long, accepted_source=True)
    baseline_net = float(base['total_net'])

    short_cases = build_shorts(x5)
    short_all = normalize_short(short_cases)

    rows = []; details = []
    for name, clocks in SETS.items():
        r, det = summarize_set(name, clocks, short_all, raw_long_norm, baseline_long_norm, baseline_net)
        rows.append(r); details.extend(det)
    summary = pd.DataFrame(rows)
    detail = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    summary.to_csv(OUT_SUM, index=False)
    detail.to_csv(OUT_DETAIL, index=False)

    lines = [
        '# B27DT — F85 LONG + F15 SHORT Collision / Portfolio Interference Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        f'**B27DQ LONG parity: PASS.** Pooled-major N={int(base["accepted"])}, WR={pct(base["wr"])}, PF={num(base["pf"])}, net={usd(base["total_net"])}, max loss streak={int(base["max_loss_streak"])}.','',
        '## LONG_PROTECTED — incremental SHORT without displacing any B27DQ LONG','',
        '| Set | Standalone N | Standalone WR | Standalone PF | Standalone Net | Blocked by LONG | Blocked by SHORT | Added SHORT N | Added WR | Added PF | Added Net | Combined Net |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for r in summary.itertuples(index=False):
        lines.append(f'| {r.set} | {r.standalone_n} | {pct(r.standalone_wr)} | {num(r.standalone_pf)} | {usd(r.standalone_net)} | {r.lp_blocked_by_long} | {r.lp_blocked_by_short} | {r.lp_short_n} | {pct(r.lp_short_wr)} | {num(r.lp_short_pf)} | {usd(r.lp_short_net)} | {usd(r.lp_combined_net)} |')

    lines += ['', '## FIRST_SIGNAL_WINS — LONG and SHORT compete for one BTC slot','',
              '| Set | Total N | Total WR | PF | Combined Net | Delta vs B27DQ | LONG N | LONG WR | LONG Net | SHORT N | SHORT WR | SHORT Net | Displaced baseline LONG | SHORT blocked by LONG | LONG blocked by SHORT | Classification |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in summary.itertuples(index=False):
        lines.append(f'| {r.set} | {r.fs_total_n} | {pct(r.fs_total_wr)} | {num(r.fs_total_pf)} | {usd(r.fs_total_net)} | {usd(r.fs_delta_vs_long)} | {r.fs_long_n} | {pct(r.fs_long_wr)} | {usd(r.fs_long_net)} | {r.fs_short_n} | {pct(r.fs_short_wr)} | {usd(r.fs_short_net)} | {r.fs_displaced_baseline_long_n} | {r.fs_short_blocked_by_long} | {r.fs_long_blocked_by_short} | {r.classification} |')

    best_lp = summary.sort_values(['lp_delta_vs_long','lp_short_pf'], ascending=[False,False]).iloc[0]
    best_fs = summary.sort_values(['fs_delta_vs_long','fs_total_pf'], ascending=[False,False]).iloc[0]
    lines += ['', '## Mechanical readout','',
              f'Best LONG-protected incremental set by net: **{best_lp["set"]}**, adds {usd(best_lp["lp_short_net"])} with {int(best_lp["lp_short_n"])} accepted SHORT trades; combined historical net {usd(best_lp["lp_combined_net"])}.',
              f'Best first-signal set by net delta: **{best_fs["set"]}**, delta {usd(best_fs["fs_delta_vs_long"])}; displaced baseline LONG trades={int(best_fs["fs_displaced_baseline_long_n"])}.', '',
              'Guardrail: the six SHORT clocks were selected after B27DR inspection, so B27DT is exploratory historical portfolio-interference evidence, not pristine OOS validation.', '',
              'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('B27DT_COLLISION_AUDIT_COMPLETED\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
