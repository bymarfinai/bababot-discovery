#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_e20_armed_runner_b27dl as dl

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_Summary.csv'
OUT_ZONE = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_ZoneSummary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_Detail.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_Status.txt'
B27DL_SUM = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Summary.csv'

VARIANT = 'E20_TOUCH_E10_BREATHING_STEP10_RUNNER'
BAR5 = pd.Timedelta(minutes=5)


def ratchet_floor_from_close(close: float, H: float, R: float, current_floor: float):
    ext = (close - H) / R
    if ext < 0.30 - 1e-12:
        return current_floor, (current_floor - H) / R
    milestone_n = int(math.floor((ext + 1e-12) / 0.10))
    floor_ext = max(0.10, (milestone_n - 1) * 0.10)
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
    e10 = H + 0.10 * R
    q = dl.fast_slice(x5, entry_start, exec_end)
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
        op = float(bar.open); hi = float(bar.high); lo = float(bar.low); cl = float(bar.close)
        max_high_ext = max(max_high_ext, (hi - H) / R)
        max_close_ext = max(max_close_ext, (cl - H) / R)

        if not armed:
            # Same pre-arm priority as baseline/B27DL: E20 high-touch before F35 close invalidation.
            if hi >= e20:
                armed = True
                arm_bar = ts
                floor = e10
                floor_ext = 0.10
                new_floor, new_ext = ratchet_floor_from_close(cl, H, R, floor)
                if new_floor > floor + 1e-12:
                    floor_raises += 1
                    floor = new_floor
                    floor_ext = new_ext
                # Newly known floor becomes active only on the next completed 5m bar.
                continue
            if cl < f35:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = cl
                reason = 'CLOSE_INVALIDATION_F35'
                break
            continue

        if op <= floor:
            exit_bar_start = ts
            exit_ts = ts
            exit_px = op
            reason = 'BREATHING_FLOOR_GAP_OPEN'
            break
        if lo <= floor:
            exit_bar_start = ts
            exit_ts = ts + BAR5
            exit_px = floor
            reason = 'BREATHING_FLOOR_TOUCH'
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
        reason = 'BREATHING_RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_EXEC_END'

    gross = float(exit_px / entry_px - 1.0)
    net = gross * dl.NOTIONAL - dl.FEE
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
        'runner_initial_floor': e10 if armed else np.nan,
        'runner_final_floor': floor,
        'runner_final_floor_ext': floor_ext,
        'runner_floor_raises': floor_raises,
        'runner_max_high_ext': max_high_ext,
        'runner_max_close_ext': max_close_ext,
        'runner_delta_vs_fixed_candidate': net - float(r.net_pnl_usd),
    }


def attach_runner(stream, x5):
    extra = pd.DataFrame([runner_exit(r, x5) for r in stream.itertuples(index=False)])
    q = pd.concat([stream.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']
    q['exit_ts'] = pd.to_datetime(q.runner_exit_ts, utc=True)
    q['exit_px'] = q.runner_exit_px.astype(float)
    q['net_pnl_usd'] = q.runner_net_pnl_usd.astype(float)
    return q


def summarize_locked(d):
    a = d[d.accepted].copy()
    m = dl.dg.metrics(a)
    return {
        'candidates': len(d), 'accepted': len(a), 'blocked': int((~d.accepted).sum()),
        **m, 'max_loss_streak': dl.streak_losses(a),
        'armed': int(a.runner_armed.sum()) if 'runner_armed' in a else int((a.exit_reason == 'TP_E20').sum()),
    }


def main():
    x5, coverage = dl.dj.b21.load5()
    stream = dl.load_stream(x5)
    parity = dl.baseline_parity(stream)
    parity.to_csv(OUT_PARITY, index=False)
    runner = attach_runner(stream, x5)

    summary_rows, zone_rows, baseline_decisions, runner_decisions = [], [], [], []
    for part in dl.PARTS:
        b = dl.dg.lock(stream[stream.partition == part].copy(), 'B27DN_FIXED_E20')
        rr = dl.dg.lock(runner[runner.partition == part].copy(), 'B27DN_E10_BREATHING_RUNNER')
        baseline_decisions.append(b); runner_decisions.append(rr)
        summary_rows += [
            {'variant':'FIXED_E20','partition':part,**summarize_locked(b)},
            {'variant':VARIANT,'partition':part,**summarize_locked(rr)},
        ]
        for zone in dl.ZONES:
            bz = b[(b.zone == zone) & b.accepted].copy()
            rz = rr[(rr.zone == zone) & rr.accepted].copy()
            bzm = dl.dg.metrics(bz); rzm = dl.dg.metrics(rz)
            zone_rows += [
                {'variant':'FIXED_E20','partition':part,'zone':zone,'accepted':len(bz),**bzm},
                {'variant':VARIANT,'partition':part,'zone':zone,'accepted':len(rz),**rzm,
                 'armed':int(rz.runner_armed.sum()),
                 'floor_exits':int(rz.runner_exit_reason.isin(['BREATHING_FLOOR_TOUCH','BREATHING_FLOOR_GAP_OPEN']).sum()),
                 'armed_time_exits':int((rz.runner_exit_reason == 'BREATHING_RUNNER_TIME_EXIT').sum())},
            ]

    bmaj = pd.concat([x for x in baseline_decisions if x.partition.iloc[0] in dl.MAJOR], ignore_index=True)
    rmaj = pd.concat([x for x in runner_decisions if x.partition.iloc[0] in dl.MAJOR], ignore_index=True)
    summary_rows += [
        {'variant':'FIXED_E20','partition':'POOLED_MAJOR',**summarize_locked(bmaj)},
        {'variant':VARIANT,'partition':'POOLED_MAJOR',**summarize_locked(rmaj)},
    ]
    for zone in dl.ZONES:
        bz = bmaj[(bmaj.zone == zone) & bmaj.accepted].copy()
        rz = rmaj[(rmaj.zone == zone) & rmaj.accepted].copy()
        bzm = dl.dg.metrics(bz); rzm = dl.dg.metrics(rz)
        zone_rows += [
            {'variant':'FIXED_E20','partition':'POOLED_MAJOR','zone':zone,'accepted':len(bz),**bzm},
            {'variant':VARIANT,'partition':'POOLED_MAJOR','zone':zone,'accepted':len(rz),**rzm,
             'armed':int(rz.runner_armed.sum()),
             'floor_exits':int(rz.runner_exit_reason.isin(['BREATHING_FLOOR_TOUCH','BREATHING_FLOOR_GAP_OPEN']).sum()),
             'armed_time_exits':int((rz.runner_exit_reason == 'BREATHING_RUNNER_TIME_EXIT').sum())},
        ]

    summary = pd.DataFrame(summary_rows); zones = pd.DataFrame(zone_rows)
    summary.to_csv(OUT_SUM, index=False); zones.to_csv(OUT_ZONE, index=False)
    detail = pd.concat(runner_decisions, ignore_index=True); detail.to_csv(OUT_DETAIL, index=False)

    rb = summary[(summary.variant=='FIXED_E20') & (summary.partition=='POOLED_MAJOR')].iloc[0]
    rr = summary[(summary.variant==VARIANT) & (summary.partition=='POOLED_MAJOR')].iloc[0]
    major_runner = summary[(summary.variant==VARIANT) & summary.partition.isin(dl.MAJOR)]
    promising = bool(rr.total_net > rb.total_net and rr.pf >= 1.80 and rr.wr >= 0.70 and rr.accepted >= 0.80*rb.accepted and (major_runner.total_net > 0).all())
    status = 'B27DN_E10_BREATHING_PROMISING_EXPLORATORY' if promising else 'B27DN_E10_BREATHING_NOT_PROMISING'
    OUT_STATUS.write_text(status+'\n')

    prior = pd.read_csv(B27DL_SUM)
    p = prior[(prior.variant=='E20_ARMED_STEP10_RUNNER') & (prior.partition=='POOLED_MAJOR')].iloc[0]
    delta_fixed = float(rr.total_net-rb.total_net)
    delta_dl = float(rr.total_net-p.total_net)
    wr_delta_fixed = float(rr.wr-rb.wr)
    wr_delta_dl = float(rr.wr-p.wr)

    accepted = rmaj[rmaj.accepted].copy(); armed = accepted[accepted.runner_armed].copy()
    avg_delta = float(armed.runner_delta_vs_fixed_candidate.mean()) if len(armed) else np.nan
    med_delta = float(armed.runner_delta_vs_fixed_candidate.median()) if len(armed) else np.nan

    lines = [
        '# B27DN — E20 Touch + E10 Breathing Floor Runner — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** Fixed-E20 B27DK parity was reproduced before B27DN interpretation.','',
        '**Evidence status: exploratory.** E10 was hypothesis-generated from previously inspected B27DM wick-reject anatomy; this is not pristine OOS confirmation.','',
        'Frozen rule: first E20 high-touch arms the runner; starting next 5m bar the hard floor is E10. Completed-close E30 -> E20 floor, E40 -> E30, E50 -> E40, etc. Floor never decreases.','',
        '## Exact portfolio comparison after global one-position re-lock','',
        '| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in (*dl.PARTS,'POOLED_MAJOR'):
        for variant in ('FIXED_E20',VARIANT):
            r = summary[(summary.partition==part)&(summary.variant==variant)].iloc[0]
            lines.append(f'| {part} | {variant} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {dl.pct(r.wr)} | {dl.num(r.pf)} | {dl.usd(r.expectancy)} | {dl.usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['','## Pooled-major contribution by zone','',
              '| Zone | Variant | N | WR | PF | Exp | Net | Armed | Floor exits | Armed time exits |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    zpm = zones[zones.partition=='POOLED_MAJOR']
    for zone in dl.ZONES:
        for variant in ('FIXED_E20',VARIANT):
            r = zpm[(zpm.zone==zone)&(zpm.variant==variant)].iloc[0]
            an = '-' if pd.isna(r.get('armed',np.nan)) else str(int(r.armed))
            fn = '-' if pd.isna(r.get('floor_exits',np.nan)) else str(int(r.floor_exits))
            tn = '-' if pd.isna(r.get('armed_time_exits',np.nan)) else str(int(r.armed_time_exits))
            lines.append(f'| {zone} | {variant} | {int(r.accepted)} | {dl.pct(r.wr)} | {dl.num(r.pf)} | {dl.usd(r.expectancy)} | {dl.usd(r.total_net)} | {an} | {fn} | {tn} |')

    lines += ['','## Direct scorecard','',
              f'- Fixed E20: **N {int(rb.accepted)} / WR {dl.pct(rb.wr)} / PF {dl.num(rb.pf)} / Exp {dl.usd(rb.expectancy)} / Net {dl.usd(rb.total_net)}**.',
              f'- Prior B27DL E20-floor runner: **N {int(p.accepted)} / WR {dl.pct(p.wr)} / PF {dl.num(p.pf)} / Exp {dl.usd(p.expectancy)} / Net {dl.usd(p.total_net)}**.',
              f'- B27DN E10 breathing runner: **N {int(rr.accepted)} / WR {dl.pct(rr.wr)} / PF {dl.num(rr.pf)} / Exp {dl.usd(rr.expectancy)} / Net {dl.usd(rr.total_net)}**.',
              f'- B27DN net delta vs fixed: **{dl.usd(delta_fixed)}**; WR delta: **{wr_delta_fixed*100:+.1f} pp**.',
              f'- B27DN net delta vs B27DL: **{dl.usd(delta_dl)}**; WR delta: **{wr_delta_dl*100:+.1f} pp**.',
              f'- Armed accepted trades: **{len(armed)}**; mean candidate delta vs fixed E20 on armed: **{dl.usd(avg_delta)}**; median: **{dl.usd(med_delta)}**.','',
              '## Decision','',f'**Status: {status}**','',
              'Research/operating exit experiment only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
