#!/usr/bin/env python3
from __future__ import annotations

import io
import math
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bbc_f85_f15_signals as sig

PFX = 'ETH_F85_LONG_EXACT_TRANSPLANT_E1'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_ZONE = ROOT / f'{PFX}_ZoneSummary.csv'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_SENS = ROOT / f'{PFX}_Sensitivity.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

SYMBOL = 'ETHUSDT'
BASE = 'https://data.binance.vision/data/futures/um'
START = pd.Timestamp('2020-01-01T00:00:00Z')
END = pd.Timestamp('2026-08-21T00:00:00Z')
BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
RUNNER_ZONES = {'RAW_0530', 'LONDON', 'RAW_2330'}
STOP_REASONS = {'LIVE_FLOOR_GAP_OPEN', 'LIVE_FLOOR_TOUCH'}
TIE_ORDER = {'LONDON': 0, 'ALT_0330': 1, 'RAW_0530': 2, 'RAW_2330': 4}
PARTS = {
    'external': (pd.Timestamp('2020-01-01', tz='UTC'), pd.Timestamp('2022-01-01', tz='UTC')),
    'development': (pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')),
    'reference_validation': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-07-30', tz='UTC')),
    'august': (pd.Timestamp('2026-08-01', tz='UTC'), pd.Timestamp('2026-08-21', tz='UTC')),
}
MAJOR = ('external', 'development', 'reference_validation')
SLIPPAGE_BPS = (0, 2, 5, 10)


def archive_urls():
    urls = []
    current = pd.Timestamp(START.year, START.month, 1, tz='UTC')
    end_month = pd.Timestamp(END.year, END.month, 1, tz='UTC')
    while current < end_month:
        ym = current.strftime('%Y-%m')
        urls.append(f'{BASE}/monthly/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip')
        current += pd.offsets.MonthBegin(1)
    d = end_month
    while d < END.normalize():
        ds = d.strftime('%Y-%m-%d')
        urls.append(f'{BASE}/daily/klines/{SYMBOL}/5m/{SYMBOL}-5m-{ds}.zip')
        d += pd.Timedelta(days=1)
    return urls


def fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={'User-Agent': 'bababot-eth-e1/1.0'})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            z = pd.read_csv(
                fh, header=None, usecols=[0, 1, 2, 3, 4],
                names=['ts', 'open', 'high', 'low', 'close']
            )
    return z


def load5():
    frames = []
    urls = archive_urls()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(fetch_one, u): u for u in urls}
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError('No ETHUSDT 5m data downloaded')
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x['ts'], errors='coerce')
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x['ts'] = pd.to_datetime(t, unit='ms', utc=True, errors='coerce')
    for c in ['open', 'high', 'low', 'close']:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna().drop_duplicates('ts').sort_values('ts')
    x = x[(x.ts >= START) & (x.ts < END)].set_index('ts')
    if x.empty:
        raise RuntimeError('ETHUSDT archive is empty in frozen horizon')
    expected = int((END - START) / BAR5)
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f'ETHUSDT 5m coverage too low: rows={len(x)} expected={expected} coverage={coverage:.6f}')
    return x, coverage


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def part_for_window(ref_start, exec_start, exec_end):
    for name, (a, z) in PARTS.items():
        if ref_start >= a and exec_start >= a and exec_end <= z:
            return name
    return None


def fixed_exit(x5, r):
    q = fast_slice(x5, pd.Timestamp(r.entry_bar_start), pd.Timestamp(r.execution_end))
    reason = None
    exit_ts = pd.NaT
    exit_px = np.nan
    for ts, bar in q.iterrows():
        if float(bar.high) >= float(r.E20):
            exit_ts = ts
            exit_px = float(r.E20)
            reason = 'TP_E20'
            break
        if float(bar.close) < float(r.F35):
            exit_ts = ts + BAR5
            exit_px = float(bar.close)
            reason = 'CLOSE_INVALIDATION_F35'
            break
    if reason is None:
        pos = int(x5.index.searchsorted(pd.Timestamp(r.execution_end), side='left'))
        if pos >= len(x5) or x5.index[pos] != pd.Timestamp(r.execution_end):
            raise AssertionError(f'missing time-exit bar {r.execution_end}')
        exit_ts = pd.Timestamp(r.execution_end)
        exit_px = float(x5.iloc[pos].open)
        reason = 'TIME_EXIT_EXEC_END'
    gross = float(exit_px / float(r.entry_px) - 1.0)
    net = gross * NOTIONAL - FEE
    return {
        'fixed_exit_ts': exit_ts,
        'fixed_exit_px': exit_px,
        'fixed_exit_reason': reason,
        'fixed_net_pnl_usd': net,
    }


def ratchet_floor_from_close(close: float, H: float, R: float, current_floor: float):
    ext = (close - H) / R
    if ext < 0.30 - 1e-12:
        return current_floor
    milestone_n = int(math.floor((ext + 1e-12) / 0.10))
    floor_ext = max(0.20, (milestone_n - 1) * 0.10)
    return max(current_floor, H + floor_ext * R)


def live_runner_exit(x5, r):
    entry_start = pd.Timestamp(r.entry_bar_start)
    exec_end = pd.Timestamp(r.execution_end)
    entry_px = float(r.entry_px)
    H = float(r.H)
    R = float(r.range)
    f35 = float(r.F35)
    e20 = float(r.E20)
    e10 = H + 0.10 * R
    q = fast_slice(x5, entry_start, exec_end)
    if q.empty:
        raise AssertionError(f'empty runner path {r.zone} {entry_start}')

    armed = False
    active_floor = np.nan
    pending = []
    reason = None
    exit_ts = pd.NaT
    exit_px = np.nan

    for ts, bar in q.iterrows():
        ts = pd.Timestamp(ts)
        op = float(bar.open); hi = float(bar.high); lo = float(bar.low); cl = float(bar.close)

        due = [v for v in pending if v[0] <= ts]
        if due:
            due_floor = max(v[1] for v in due)
            if pd.isna(active_floor) or due_floor > active_floor + 1e-12:
                active_floor = due_floor
            pending = [v for v in pending if v[0] > ts]

        if armed and not pd.isna(active_floor):
            if op <= active_floor:
                exit_ts = ts
                exit_px = op
                reason = 'LIVE_FLOOR_GAP_OPEN'
                break
            if lo <= active_floor:
                exit_ts = ts + BAR5
                exit_px = active_floor
                reason = 'LIVE_FLOOR_TOUCH'
                break

        if not armed:
            if hi >= e20:
                armed = True
                desired = ratchet_floor_from_close(cl, H, R, e10)
                pending.append((ts + 2 * BAR5, desired))
                continue
            if cl < f35:
                exit_ts = ts + BAR5
                exit_px = cl
                reason = 'CLOSE_INVALIDATION_F35'
                break
            continue

        if pd.isna(active_floor) and cl < f35:
            exit_ts = ts + BAR5
            exit_px = cl
            reason = 'BUFFER_CLOSE_INVALIDATION_F35'
            break

        known_floors = [e10]
        if not pd.isna(active_floor):
            known_floors.append(float(active_floor))
        known_floors += [float(v[1]) for v in pending]
        known_floor = max(known_floors)
        desired = ratchet_floor_from_close(cl, H, R, known_floor)
        if desired > known_floor + 1e-12:
            pending.append((ts + 2 * BAR5, desired))

    if reason is None:
        pos = int(x5.index.searchsorted(exec_end, side='left'))
        if pos >= len(x5) or x5.index[pos] != exec_end:
            raise AssertionError(f'missing runner time-exit bar {exec_end}')
        exit_ts = exec_end
        exit_px = float(x5.iloc[pos].open)
        reason = 'LIVE_RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_EXEC_END'

    fixed_tp = str(r.fixed_exit_reason) == 'TP_E20'
    if bool(armed) != bool(fixed_tp):
        raise AssertionError(f'E20 arm parity failed {r.zone} {entry_start}: armed={armed} fixed={r.fixed_exit_reason}')

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    return {
        'exit_ts': exit_ts,
        'exit_px': exit_px,
        'exit_reason': reason,
        'net_pnl_usd': net,
        'runner_armed': armed,
        'active_floor_at_exit': active_floor,
    }


def build_candidates(x5):
    rows = []
    sessions = 0
    anchors = pd.date_range(START.normalize(), END.normalize(), freq='D', tz='UTC')
    for anchor in anchors:
        for zone, cm in sig.LONG_ZONE_CLOCKS.items():
            ref_start = anchor + pd.Timedelta(minutes=cm)
            ref_end = ref_start + sig.REF_DUR
            exec_start = ref_end
            exec_end = exec_start + sig.EXEC_DUR
            part = part_for_window(ref_start, exec_start, exec_end)
            if part is None or exec_start.weekday() >= 5:
                continue
            ref = fast_slice(x5, ref_start, ref_end)
            exe = fast_slice(x5, exec_start, exec_end)
            if len(ref) != sig.REF_BARS or len(exe) != sig.EXEC_BARS:
                continue
            sessions += 1
            adapter = sig.LongF85Session(zone, anchor, ref)
            signals = sig.replay_session(adapter, exe)
            for s in signals:
                base = SimpleNamespace(
                    partition=part,
                    zone=zone,
                    clock_min=cm,
                    anchor_date_utc=str(anchor.date()),
                    reference_start=ref_start,
                    reference_end=ref_end,
                    execution_start=exec_start,
                    execution_end=exec_end,
                    confirmation_bar_start=pd.Timestamp(s.confirmation_bar_start),
                    touch_bar_start=pd.Timestamp(s.confirmation_bar_start),
                    entry_bar_start=pd.Timestamp(s.entry_ts),
                    entry_px=float(s.entry_px),
                    H=float(s.H), L=float(s.L), range=float(s.R),
                    F85=float(s.entry_level), F35=float(s.stop_level), E20=float(s.target_level),
                    touch_elapsed_min=float(s.touch_elapsed_min),
                )
                fx = fixed_exit(x5, base)
                for k, v in fx.items():
                    setattr(base, k, v)
                if zone in RUNNER_ZONES:
                    fin = live_runner_exit(x5, base)
                    mode = 'B27DQ_LIVE_EXEC_NPLUS2_E10_HYBRID'
                else:
                    fin = {
                        'exit_ts': base.fixed_exit_ts,
                        'exit_px': base.fixed_exit_px,
                        'exit_reason': base.fixed_exit_reason,
                        'net_pnl_usd': base.fixed_net_pnl_usd,
                        'runner_armed': False,
                        'active_floor_at_exit': np.nan,
                    }
                    mode = 'FIXED_E20'
                rows.append({
                    'partition': part,
                    'zone': zone,
                    'clock_min': cm,
                    'anchor_date_utc': str(anchor.date()),
                    'reference_start': ref_start,
                    'reference_end': ref_end,
                    'execution_start': exec_start,
                    'execution_end': exec_end,
                    'confirmation_bar_start': base.confirmation_bar_start,
                    'entry_bar_start': base.entry_bar_start,
                    'entry_px': base.entry_px,
                    'H': base.H, 'L': base.L, 'range': base.range,
                    'F85': base.F85, 'F35': base.F35, 'E20': base.E20,
                    'touch_elapsed_min': base.touch_elapsed_min,
                    'management_mode': mode,
                    'fixed_exit_ts': base.fixed_exit_ts,
                    'fixed_exit_px': base.fixed_exit_px,
                    'fixed_exit_reason': base.fixed_exit_reason,
                    'fixed_net_pnl_usd': base.fixed_net_pnl_usd,
                    **fin,
                })
    d = pd.DataFrame(rows)
    if d.empty:
        raise RuntimeError('No ETH exact-transplant LONG candidates generated')
    d['candidate_id'] = d.partition.astype(str) + '|ETH_LONG|' + d.zone.astype(str) + '|' + d.entry_bar_start.astype(str)
    return d, sessions


def lock(g: pd.DataFrame, label: str):
    q = g.copy()
    q['tie_order'] = q.zone.map(TIE_ORDER)
    q = q.sort_values(['entry_bar_start', 'tie_order', 'candidate_id']).reset_index(drop=True)
    locked_until = pd.NaT
    accepted = []
    blocker = []
    active_zone = None
    for r in q.itertuples(index=False):
        ok = pd.isna(locked_until) or pd.Timestamp(r.entry_bar_start) >= pd.Timestamp(locked_until)
        accepted.append(bool(ok))
        blocker.append('' if ok else active_zone)
        if ok:
            locked_until = pd.Timestamp(r.exit_ts)
            active_zone = r.zone
    q['accepted'] = accepted
    q['blocked_by_zone'] = blocker
    q['portfolio'] = label
    return q


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_loss_streak(d):
    q = d.sort_values('entry_bar_start')
    cur = best = 0
    for v in pd.to_numeric(q.net_pnl_usd, errors='coerce'):
        if v <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return int(best)


def metrics(d):
    v = pd.to_numeric(d.net_pnl_usd, errors='coerce').dropna()
    return {
        'n': int(len(v)),
        'wins': int((v > 0).sum()),
        'wr': float((v > 0).mean()) if len(v) else np.nan,
        'pf': pf(v) if len(v) else np.nan,
        'expectancy': float(v.mean()) if len(v) else np.nan,
        'total_net': float(v.sum()) if len(v) else 0.0,
        'max_loss_streak': max_loss_streak(d) if len(v) else 0,
    }


def apply_slippage(d, bps):
    q = d.copy()
    if bps <= 0:
        return q
    mask = q.zone.isin(RUNNER_ZONES) & q.exit_reason.isin(STOP_REASONS)
    q.loc[mask, 'exit_px'] = q.loc[mask, 'exit_px'].astype(float) * (1.0 - float(bps) / 10000.0)
    q.loc[mask, 'net_pnl_usd'] = (
        (q.loc[mask, 'exit_px'].astype(float) / q.loc[mask, 'entry_px'].astype(float) - 1.0) * NOTIONAL - FEE
    )
    return q


def score(candidates):
    summaries = []
    zones = []
    locked_parts = []
    for part in PARTS:
        d = lock(candidates[candidates.partition == part], f'ETH_E1_{part}')
        locked_parts.append(d)
        a = d[d.accepted].copy()
        summaries.append({'partition': part, 'candidates': len(d), 'accepted': len(a), 'blocked': int((~d.accepted).sum()), **metrics(a)})
        for zone in TIE_ORDER:
            az = a[a.zone == zone].copy()
            zones.append({'partition': part, 'zone': zone, **metrics(az)})
    major = pd.concat([d for d in locked_parts if len(d) and d.partition.iloc[0] in MAJOR], ignore_index=True)
    a = major[major.accepted].copy()
    summaries.append({'partition': 'POOLED_MAJOR', 'candidates': len(major), 'accepted': len(a), 'blocked': int((~major.accepted).sum()), **metrics(a)})
    for zone in TIE_ORDER:
        az = a[a.zone == zone].copy()
        zones.append({'partition': 'POOLED_MAJOR', 'zone': zone, **metrics(az)})
    return pd.DataFrame(summaries), pd.DataFrame(zones), pd.concat(locked_parts, ignore_index=True)


def sensitivity(locked):
    rows = []
    for bps in SLIPPAGE_BPS:
        q = apply_slippage(locked[locked.partition.isin(MAJOR) & locked.accepted].copy(), bps)
        rows.append({'stop_slippage_bps': bps, **metrics(q)})
    return pd.DataFrame(rows)


def decision(summary, sens):
    pooled = summary[summary.partition == 'POOLED_MAJOR'].iloc[0]
    five = sens[sens.stop_slippage_bps == 5].iloc[0]
    majors = summary[summary.partition.isin(MAJOR)]
    btc_grade = bool(
        int(pooled.accepted) >= 150 and pooled.wr >= .70 and pooled.pf >= 2.00 and
        pooled.expectancy > 0 and pooled.total_net > 250 and int(pooled.max_loss_streak) <= 4 and
        five.pf > 1.80 and five.total_net > 200 and
        (majors.expectancy > 0).all()
    )
    transferable = bool(
        int(pooled.accepted) >= 100 and pooled.wr >= .65 and pooled.pf >= 1.30 and pooled.total_net > 0 and
        (majors.pf > 1.00).all() and (majors.total_net > 0).all() and
        five.pf > 1.20 and five.total_net > 0
    )
    if btc_grade:
        return 'ETH_E1_BTC_GRADE_CROSS_PAIR_REPLICATION_SUPPORTED'
    if transferable:
        return 'ETH_E1_TRANSFERABLE_EDGE_BELOW_BTC_GRADE'
    return 'ETH_E1_EXACT_TRANSPLANT_NOT_SUPPORTED'


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main():
    x5, coverage = load5()
    candidates, sessions = build_candidates(x5)
    summary, zone_summary, locked = score(candidates)
    sens = sensitivity(locked)
    status = decision(summary, sens)

    summary.to_csv(OUT_SUM, index=False)
    zone_summary.to_csv(OUT_ZONE, index=False)
    locked.to_csv(OUT_TRADES, index=False)
    sens.to_csv(OUT_SENS, index=False)
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH F85 LONG Exact-Transplant E1 — Result', '',
        f'ETHUSDT 5m rows: **{len(x5):,}**; frozen-horizon coverage: **{coverage:.4%}**; causal sessions replayed: **{sessions:,}**.', '',
        'This is a zero-tuning cross-pair transplant of the frozen causal BTC F85 LONG architecture. Signal generation uses the same `LongF85Session` raw closed-5m semantics; zone clocks, F85/F35/E20 geometry, ALT/range-completion filters, B27DQ N+2 runner, one-position lock, USD 500 notional, and USD 0.40 fee are unchanged.', '',
        '## Exact-transplant portfolio', '',
        '| Partition | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in summary.itertuples(index=False):
        lines.append(f'| {r.partition} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['', '## Pooled-major contribution by zone', '',
              '| Zone | N | WR | PF | Exp | Net | Max loss streak |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in zone_summary[zone_summary.partition == 'POOLED_MAJOR'].itertuples(index=False):
        lines.append(f'| {r.zone} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['', '## Runner-stop slippage sensitivity — pooled major', '',
              '| Stop slippage | N | WR | PF | Exp | Net | Max loss streak |',
              '|---:|---:|---:|---:|---:|---:|---:|']
    for r in sens.itertuples(index=False):
        lines.append(f'| {int(r.stop_slippage_bps)} bps | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['', '## Decision', '', f'**{status}**', '',
              'No ETH-specific clock, retracement level, filter, or exit parameter was searched or changed after observing the result.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
