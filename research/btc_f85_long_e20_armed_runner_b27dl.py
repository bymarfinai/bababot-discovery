#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_single_position_portfolio_b27dg as dg
import btc_f85_long_range_completion_recency_b27dj as dj

ROOT = Path(__file__).resolve().parent.parent
BASE_SUM = ROOT / 'BTC_F85_LONG_4ZONE_OPERATING_PORTFOLIO_B27DK_Summary.csv'
OUT_MD = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Summary.csv'
OUT_ZONE = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_ZoneSummary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Detail.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Status.txt'

PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
ZONES = ('ALT_0330', 'RAW_0530', 'LONDON', 'RAW_2330')
ADD_ZONES = ('RAW_0530', 'RAW_2330')
BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def close_enough(a, b, tol=1e-9):
    if pd.isna(b): return pd.isna(a)
    if math.isinf(float(b)):
        return math.isinf(float(a)) and ((float(a) > 0) == (float(b) > 0))
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_stream(x5):
    c = dj.load_candidates()
    for col in ('execution_end', 'entry_bar_start', 'exit_ts'):
        c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    for col in ('H', 'L', 'range', 'F35', 'E20', 'entry_px', 'exit_px', 'net_pnl_usd'):
        c[col] = pd.to_numeric(c[col], errors='coerce')
    c, _ = dj.attach_range_completion(c, x5)
    add = c[c.zone.isin(ADD_ZONES) & c.range_completed_second_half].copy()
    pri = c[c.primary_eligible].copy()
    stream = pd.concat([pri, add], ignore_index=True)
    assert stream.entry_bar_start.notna().all()
    assert stream.execution_end.notna().all()
    assert stream.exit_ts.notna().all()
    return stream


def baseline_parity(stream):
    saved = pd.read_csv(BASE_SUM)
    rows = []
    for part in PARTS:
        d = dg.lock(stream[stream.partition == part].copy(), 'B27DL_BASE_PARITY')
        a = d[d.accepted].copy()
        m = dg.metrics(a)
        q = saved[saved.partition == part]
        assert len(q) == 1, (part, len(q))
        r = q.iloc[0]
        checks = {
            'accepted': (len(a), int(r.accepted)),
            'wr': (m['wr'], float(r.wr)),
            'pf': (m['pf'], float(r.pf)),
            'expectancy': (m['expectancy'], float(r.expectancy)),
            'total_net': (m['total_net'], float(r.total_net)),
        }
        for metric, (actual, expected) in checks.items():
            ok = int(actual) == int(expected) if metric == 'accepted' else close_enough(actual, expected)
            rows.append({'partition': part, 'check': metric, 'actual': actual, 'expected': expected, 'pass': ok})
    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DL B27DK baseline parity failed:\n' + out[~out['pass']].to_string(index=False))
    return out


def ratchet_floor_from_close(close: float, H: float, R: float, current_floor: float) -> tuple[float, float]:
    ext = (close - H) / R
    if ext < 0.30 - 1e-12:
        return current_floor, (current_floor - H) / R
    milestone_n = int(math.floor((ext + 1e-12) / 0.10))
    floor_ext = max(0.20, (milestone_n - 1) * 0.10)
    candidate = H + floor_ext * R
    new_floor = max(current_floor, candidate)
    return new_floor, (new_floor - H) / R


def runner_exit(r, x5):
    entry_start = pd.Timestamp(r.entry_bar_start)
    exec_end = pd.Timestamp(r.execution_end)
    entry_px = float(r.entry_px)
    H = float(r.H)
    R = float(r.range)
    f35 = float(r.F35)
    e20 = float(r.E20)
    q = fast_slice(x5, entry_start, exec_end)
    if q.empty:
        raise AssertionError(f'empty runner path {r.zone} {entry_start}')

    armed = False
    arm_bar = pd.NaT
    floor = np.nan
    floor_ext = np.nan
    floor_raises = 0
    max_high_ext = -np.inf
    max_close_ext = -np.inf
    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None

    for ts, bar in q.iterrows():
        op = float(bar.open)
        hi = float(bar.high)
        lo = float(bar.low)
        cl = float(bar.close)
        max_high_ext = max(max_high_ext, (hi - H) / R)
        max_close_ext = max(max_close_ext, (cl - H) / R)

        if not armed:
            # Preserve baseline priority: E20 high-touch wins over F35 close invalidation.
            if hi >= e20:
                armed = True
                arm_bar = ts
                floor = e20
                floor_ext = 0.20
                new_floor, new_ext = ratchet_floor_from_close(cl, H, R, floor)
                if new_floor > floor + 1e-12:
                    floor_raises += 1
                    floor = new_floor
                    floor_ext = new_ext
                # Newly armed/ratcheted floor becomes effective next 5m bar.
                continue
            if cl < f35:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = cl
                reason = 'CLOSE_INVALIDATION_F35'
                break
            continue

        # Armed floor was known before this bar started.
        if op <= floor:
            exit_bar_start = ts
            exit_ts = ts
            exit_px = op
            reason = 'RUNNER_FLOOR_GAP_OPEN'
            break
        if lo <= floor:
            exit_bar_start = ts
            exit_ts = ts + BAR5
            exit_px = floor
            reason = 'RUNNER_FLOOR_TOUCH'
            break

        new_floor, new_ext = ratchet_floor_from_close(cl, H, R, floor)
        if new_floor > floor + 1e-12:
            floor_raises += 1
            floor = new_floor
            floor_ext = new_ext

    if reason is None:
        pos = int(x5.index.searchsorted(exec_end, side='left'))
        if pos >= len(x5) or x5.index[pos] != exec_end:
            raise AssertionError(f'missing time-exit bar {exec_end}')
        exit_bar_start = exec_end
        exit_ts = exec_end
        exit_px = float(x5.iloc[pos].open)
        reason = 'RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_EXEC_END'

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE
    fixed_tp = str(r.exit_reason) == 'TP_E20'
    if bool(armed) != bool(fixed_tp):
        raise AssertionError(f'E20 arm parity failed {r.zone} {entry_start}: armed={armed} fixed={r.exit_reason}')

    return {
        'runner_exit_bar_start': exit_bar_start,
        'runner_exit_ts': exit_ts,
        'runner_exit_px': float(exit_px),
        'runner_exit_reason': reason,
        'runner_net_pnl_usd': net,
        'runner_armed': armed,
        'runner_arm_bar_start': arm_bar,
        'runner_final_floor': floor,
        'runner_final_floor_ext': floor_ext,
        'runner_floor_raises': floor_raises,
        'runner_max_high_ext': max_high_ext,
        'runner_max_close_ext': max_close_ext,
        'runner_delta_vs_fixed_candidate': net - float(r.net_pnl_usd),
    }


def attach_runner(stream, x5):
    rows = []
    for r in stream.itertuples(index=False):
        rows.append(runner_exit(r, x5))
    extra = pd.DataFrame(rows, index=stream.index)
    q = pd.concat([stream.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']
    q['exit_ts'] = pd.to_datetime(q.runner_exit_ts, utc=True)
    q['exit_px'] = q.runner_exit_px.astype(float)
    q['net_pnl_usd'] = q.runner_net_pnl_usd.astype(float)
    return q


def streak_losses(g):
    v = pd.to_numeric(g.net_pnl_usd, errors='coerce').to_numpy()
    best = cur = 0
    for x in v:
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def summarize_locked(d):
    a = d[d.accepted].copy()
    m = dg.metrics(a)
    return {
        'candidates': len(d), 'accepted': len(a), 'blocked': int((~d.accepted).sum()),
        **m,
        'max_loss_streak': streak_losses(a),
        'armed': int(a.runner_armed.sum()) if 'runner_armed' in a else int((a.exit_reason == 'TP_E20').sum()),
    }


def main():
    x5, coverage = dj.b21.load5()
    stream = load_stream(x5)
    parity = baseline_parity(stream)
    parity.to_csv(OUT_PARITY, index=False)
    runner = attach_runner(stream, x5)

    summary_rows = []
    zone_rows = []
    runner_decisions = []
    baseline_decisions = []

    for part in PARTS:
        b = dg.lock(stream[stream.partition == part].copy(), 'B27DL_FIXED_E20')
        rr = dg.lock(runner[runner.partition == part].copy(), 'B27DL_E20_ARMED_STEP10_RUNNER')
        baseline_decisions.append(b)
        runner_decisions.append(rr)
        bm = summarize_locked(b)
        rm = summarize_locked(rr)
        summary_rows += [
            {'variant': 'FIXED_E20', 'partition': part, **bm},
            {'variant': 'E20_ARMED_STEP10_RUNNER', 'partition': part, **rm},
        ]
        for zone in ZONES:
            bz = b[(b.zone == zone) & b.accepted].copy()
            rz = rr[(rr.zone == zone) & rr.accepted].copy()
            bzm = dg.metrics(bz); rzm = dg.metrics(rz)
            zone_rows += [
                {'variant': 'FIXED_E20', 'partition': part, 'zone': zone, 'accepted': len(bz), **bzm},
                {'variant': 'E20_ARMED_STEP10_RUNNER', 'partition': part, 'zone': zone, 'accepted': len(rz), **rzm,
                 'armed': int(rz.runner_armed.sum()),
                 'floor_exits': int(rz.runner_exit_reason.isin(['RUNNER_FLOOR_TOUCH','RUNNER_FLOOR_GAP_OPEN']).sum()),
                 'armed_time_exits': int((rz.runner_exit_reason == 'RUNNER_TIME_EXIT').sum())},
            ]

    bmaj = pd.concat([x for x in baseline_decisions if x.partition.iloc[0] in MAJOR], ignore_index=True)
    rmaj = pd.concat([x for x in runner_decisions if x.partition.iloc[0] in MAJOR], ignore_index=True)
    bm = summarize_locked(bmaj); rm = summarize_locked(rmaj)
    summary_rows += [
        {'variant': 'FIXED_E20', 'partition': 'POOLED_MAJOR', **bm},
        {'variant': 'E20_ARMED_STEP10_RUNNER', 'partition': 'POOLED_MAJOR', **rm},
    ]
    for zone in ZONES:
        bz = bmaj[(bmaj.zone == zone) & bmaj.accepted].copy()
        rz = rmaj[(rmaj.zone == zone) & rmaj.accepted].copy()
        bzm = dg.metrics(bz); rzm = dg.metrics(rz)
        zone_rows += [
            {'variant': 'FIXED_E20', 'partition': 'POOLED_MAJOR', 'zone': zone, 'accepted': len(bz), **bzm},
            {'variant': 'E20_ARMED_STEP10_RUNNER', 'partition': 'POOLED_MAJOR', 'zone': zone, 'accepted': len(rz), **rzm,
             'armed': int(rz.runner_armed.sum()),
             'floor_exits': int(rz.runner_exit_reason.isin(['RUNNER_FLOOR_TOUCH','RUNNER_FLOOR_GAP_OPEN']).sum()),
             'armed_time_exits': int((rz.runner_exit_reason == 'RUNNER_TIME_EXIT').sum())},
        ]

    summary = pd.DataFrame(summary_rows)
    zones = pd.DataFrame(zone_rows)
    summary.to_csv(OUT_SUM, index=False)
    zones.to_csv(OUT_ZONE, index=False)

    detail = pd.concat(runner_decisions, ignore_index=True)
    detail.to_csv(OUT_DETAIL, index=False)

    rb = summary[(summary.variant == 'FIXED_E20') & (summary.partition == 'POOLED_MAJOR')].iloc[0]
    rr = summary[(summary.variant == 'E20_ARMED_STEP10_RUNNER') & (summary.partition == 'POOLED_MAJOR')].iloc[0]
    major_runner = summary[(summary.variant == 'E20_ARMED_STEP10_RUNNER') & summary.partition.isin(MAJOR)]
    supported = bool(
        rr.total_net > rb.total_net
        and rr.pf >= 1.80
        and rr.wr >= 0.70
        and rr.accepted >= 0.80 * rb.accepted
        and (major_runner.total_net > 0).all()
    )
    status = 'B27DL_RUNNER_SUPPORTED' if supported else 'B27DL_RUNNER_NOT_SUPPORTED'
    OUT_STATUS.write_text(status + '\n')

    accepted_runner = rmaj[rmaj.accepted].copy()
    armed = accepted_runner[accepted_runner.runner_armed].copy()
    milestone_rates = {}
    for e in (0.30, 0.40, 0.50, 0.60, 0.80, 1.00):
        milestone_rates[e] = float((armed.runner_max_high_ext >= e).mean()) if len(armed) else np.nan
    avg_candidate_delta = float(armed.runner_delta_vs_fixed_candidate.mean()) if len(armed) else np.nan
    med_candidate_delta = float(armed.runner_delta_vs_fixed_candidate.median()) if len(armed) else np.nan

    lines = [
        '# B27DL — E20 Armed Step-10 Range Runner — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        '**Audit status: PASS.** The fixed-E20 4-zone portfolio reproduced B27DK before runner results were interpreted.', '',
        'Frozen runner: E20 arms the trade; E20 becomes the next-bar hard floor; completed-close milestones ratchet the floor one 0.10R step behind (E40 close -> E30 floor, E50 close -> E40 floor, etc.).', '',
        '## Exact portfolio comparison after global one-position re-lock', '',
        '| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for part in (*PARTS, 'POOLED_MAJOR'):
        for variant in ('FIXED_E20', 'E20_ARMED_STEP10_RUNNER'):
            r = summary[(summary.partition == part) & (summary.variant == variant)].iloc[0]
            lines.append(f'| {part} | {variant} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['', '## Pooled-major contribution by zone', '',
              '| Zone | Variant | N | WR | PF | Exp | Net | Armed | Floor exits | Armed time exits |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    zpm = zones[zones.partition == 'POOLED_MAJOR']
    for zone in ZONES:
        for variant in ('FIXED_E20','E20_ARMED_STEP10_RUNNER'):
            r = zpm[(zpm.zone == zone) & (zpm.variant == variant)].iloc[0]
            armed_n = '-' if pd.isna(r.get('armed', np.nan)) else str(int(r.armed))
            floor_n = '-' if pd.isna(r.get('floor_exits', np.nan)) else str(int(r.floor_exits))
            time_n = '-' if pd.isna(r.get('armed_time_exits', np.nan)) else str(int(r.armed_time_exits))
            lines.append(f'| {zone} | {variant} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {armed_n} | {floor_n} | {time_n} |')

    lines += ['', '## What happened after old E20 was reached', '',
              f'Runner-armed accepted pooled-major trades: **{len(armed)}**.',
              f'Average candidate-level PnL change on those armed trades versus taking fixed E20: **{usd(avg_candidate_delta)}**; median **{usd(med_candidate_delta)}**.', '']
    for e, rate in milestone_rates.items():
        lines.append(f'- High reached E{int(e*100)} or farther after entry: **{pct(rate)}** of runner-armed accepted trades.')

    delta_net = float(rr.total_net - rb.total_net)
    delta_n = int(rr.accepted - rb.accepted)
    lines += ['', '## Decision', '',
              f'Pooled-major net delta: **{usd(delta_net)}**; accepted-trade delta: **{delta_n:+d}**.',
              f'**Status: {status}**', '',
              'Research/operating exit experiment only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
