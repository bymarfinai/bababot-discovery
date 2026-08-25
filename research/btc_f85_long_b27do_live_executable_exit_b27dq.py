#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_e20_e10_breathing_runner_b27dn as dn
import btc_f85_long_hybrid_exit_b27do as do

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_Summary.csv'
OUT_ZONE = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_ZoneSummary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_Detail.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_Parity.csv'
OUT_SENS = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_Sensitivity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_B27DO_LIVE_EXECUTABLE_EXIT_B27DQ_Status.txt'
B27DO_SUM = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Summary.csv'

VARIANT = 'LIVE_EXEC_NPLUS2_E10_HYBRID'
RUNNER_ZONES = {'RAW_0530', 'LONDON', 'RAW_2330'}
BAR5 = pd.Timedelta(minutes=5)
STOP_REASONS = {'LIVE_FLOOR_GAP_OPEN', 'LIVE_FLOOR_TOUCH'}


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def summarize(d):
    a = d[d.accepted].copy()
    m = dn.dl.dg.metrics(a)
    return {
        'candidates': len(d),
        'accepted': len(a),
        'blocked': int((~d.accepted).sum()),
        **m,
        'max_loss_streak': dn.dl.streak_losses(a),
    }


def _schedule_floor(pending, effective_ts, floor):
    pending.append((pd.Timestamp(effective_ts), float(floor)))


def live_runner_exit(r, x5):
    entry_start = pd.Timestamp(r.entry_bar_start)
    exec_end = pd.Timestamp(r.execution_end)
    entry_px = float(r.entry_px)
    H = float(r.H)
    R = float(r.range)
    f35 = float(r.F35)
    e20 = float(r.E20)
    e10 = H + 0.10 * R
    q = dn.dl.fast_slice(x5, entry_start, exec_end)
    if q.empty:
        raise AssertionError(f'empty live runner path {r.zone} {entry_start}')

    armed = False
    arm_bar = pd.NaT
    active_floor = np.nan
    pending = []
    scheduled_updates = 0
    activations = 0
    ratchet_updates = 0
    buffer_f35_exit = False
    exit_bar_start = pd.NaT
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None
    max_high_ext = -np.inf
    max_close_ext = -np.inf

    for ts, bar in q.iterrows():
        ts = pd.Timestamp(ts)
        op = float(bar.open); hi = float(bar.high); lo = float(bar.low); cl = float(bar.close)
        max_high_ext = max(max_high_ext, (hi - H) / R)
        max_close_ext = max(max_close_ext, (cl - H) / R)

        # Apply only floors that were scheduled at least one full 5m bar earlier.
        due = [x for x in pending if x[0] <= ts]
        if due:
            due_floor = max(x[1] for x in due)
            if pd.isna(active_floor) or due_floor > active_floor + 1e-12:
                active_floor = due_floor
                activations += 1
            pending = [x for x in pending if x[0] > ts]

        # A floor scored here was already exchange-active before this bar started.
        if armed and not pd.isna(active_floor):
            if op <= active_floor:
                exit_bar_start = ts
                exit_ts = ts
                exit_px = op
                reason = 'LIVE_FLOOR_GAP_OPEN'
                break
            if lo <= active_floor:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = active_floor
                reason = 'LIVE_FLOOR_TOUCH'
                break

        if not armed:
            # Preserve baseline priority: E20 touch is recognized before F35 close invalidation.
            if hi >= e20:
                armed = True
                arm_bar = ts
                desired = e10
                desired, _ = dn.ratchet_floor_from_close(cl, H, R, desired)
                _schedule_floor(pending, ts + 2 * BAR5, desired)
                scheduled_updates += 1
                if desired > e10 + 1e-12:
                    ratchet_updates += 1
                continue
            if cl < f35:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = cl
                reason = 'CLOSE_INVALIDATION_F35'
                break
            continue

        # Initial placement buffer: before the first runner floor is active,
        # preserve the already causal completed-close F35 invalidation.
        if pd.isna(active_floor) and cl < f35:
            exit_bar_start = ts
            exit_ts = ts + BAR5
            exit_px = cl
            reason = 'BUFFER_CLOSE_INVALIDATION_F35'
            buffer_f35_exit = True
            break

        known_floors = [e10]
        if not pd.isna(active_floor):
            known_floors.append(float(active_floor))
        known_floors += [float(x[1]) for x in pending]
        known_floor = max(known_floors)
        desired, _ = dn.ratchet_floor_from_close(cl, H, R, known_floor)
        if desired > known_floor + 1e-12:
            _schedule_floor(pending, ts + 2 * BAR5, desired)
            scheduled_updates += 1
            ratchet_updates += 1

    if reason is None:
        pos = int(x5.index.searchsorted(exec_end, side='left'))
        if pos >= len(x5) or x5.index[pos] != exec_end:
            raise AssertionError(f'missing time-exit bar {exec_end}')
        exit_bar_start = exec_end
        exit_ts = exec_end
        exit_px = float(x5.iloc[pos].open)
        reason = 'LIVE_RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_EXEC_END'

    gross = float(exit_px / entry_px - 1.0)
    net = gross * dn.dl.NOTIONAL - dn.dl.FEE
    fixed_tp = str(r.exit_reason) == 'TP_E20'
    if bool(armed) != bool(fixed_tp):
        raise AssertionError(f'E20 arm parity failed {r.zone} {entry_start}: armed={armed} fixed={r.exit_reason}')

    return {
        'live_exit_bar_start': exit_bar_start,
        'live_exit_ts': exit_ts,
        'live_exit_px': float(exit_px),
        'live_exit_reason': reason,
        'live_net_pnl_usd': net,
        'runner_armed': armed,
        'runner_arm_bar_start': arm_bar,
        'runner_final_active_floor': active_floor,
        'runner_pending_floor_count_at_exit': len(pending),
        'runner_scheduled_updates': scheduled_updates,
        'runner_activations': activations,
        'runner_ratchet_updates': ratchet_updates,
        'runner_buffer_f35_exit': buffer_f35_exit,
        'runner_max_high_ext': max_high_ext,
        'runner_max_close_ext': max_close_ext,
        'runner_delta_vs_fixed_candidate': net - float(r.net_pnl_usd),
    }


def attach_live_runner(stream, x5):
    extra = pd.DataFrame([live_runner_exit(r, x5) for r in stream.itertuples(index=False)])
    return pd.concat([stream.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)


def build_live_hybrid(stream, live):
    q = stream.copy().reset_index(drop=True)
    l = live.copy().reset_index(drop=True)
    assert len(q) == len(l)
    mask = q.zone.isin(RUNNER_ZONES)
    q['management_mode'] = 'FIXED_E20'
    q.loc[mask, 'management_mode'] = VARIANT
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']
    q.loc[mask, 'exit_ts'] = l.loc[mask, 'live_exit_ts'].values
    q.loc[mask, 'exit_px'] = l.loc[mask, 'live_exit_px'].values
    q.loc[mask, 'net_pnl_usd'] = l.loc[mask, 'live_net_pnl_usd'].values
    q['exit_ts'] = pd.to_datetime(q.exit_ts, utc=True)
    for c in [
        'live_exit_reason','runner_armed','runner_arm_bar_start','runner_final_active_floor',
        'runner_pending_floor_count_at_exit','runner_scheduled_updates','runner_activations',
        'runner_ratchet_updates','runner_buffer_f35_exit','runner_max_high_ext',
        'runner_max_close_ext','runner_delta_vs_fixed_candidate'
    ]:
        q[c] = np.nan
        if c in l.columns:
            q.loc[mask, c] = l.loc[mask, c].values
    return q


def apply_stop_slippage(hybrid, bps):
    q = hybrid.copy()
    if bps <= 0:
        return q
    mask = q.zone.isin(RUNNER_ZONES) & q.live_exit_reason.isin(STOP_REASONS)
    q.loc[mask, 'exit_px'] = q.loc[mask, 'exit_px'].astype(float) * (1.0 - float(bps) / 10000.0)
    q.loc[mask, 'net_pnl_usd'] = (
        (q.loc[mask, 'exit_px'].astype(float) / q.loc[mask, 'entry_px'].astype(float) - 1.0)
        * dn.dl.NOTIONAL - dn.dl.FEE
    )
    return q


def score_variant(data, label):
    rows = []
    zone_rows = []
    details = []
    for part in dn.dl.PARTS:
        locked = dn.dl.dg.lock(data[data.partition == part].copy(), f'B27DQ_{label}_{part}')
        details.append(locked)
        rows.append({'variant': label, 'partition': part, **summarize(locked)})
        for z in dn.dl.ZONES:
            a = locked[(locked.zone == z) & locked.accepted].copy()
            zone_rows.append({'variant': label, 'partition': part, 'zone': z, 'accepted': len(a), **dn.dl.dg.metrics(a)})
    pooled = pd.concat([x for x in details if len(x) and x.partition.iloc[0] in dn.dl.MAJOR], ignore_index=True)
    rows.append({'variant': label, 'partition': 'POOLED_MAJOR', **summarize(pooled)})
    for z in dn.dl.ZONES:
        a = pooled[(pooled.zone == z) & pooled.accepted].copy()
        zone_rows.append({'variant': label, 'partition': 'POOLED_MAJOR', 'zone': z, 'accepted': len(a), **dn.dl.dg.metrics(a)})
    return pd.DataFrame(rows), pd.DataFrame(zone_rows), details, pooled


def main():
    x5, coverage = dn.dl.dj.b21.load5()
    stream = dn.dl.load_stream(x5)

    base_parity = dn.dl.baseline_parity(stream)

    # Reproduce original B27DO before interpreting corrected execution.
    breathing = dn.attach_runner(stream, x5)
    old_hybrid = do.build_hybrid(stream, breathing)
    old_sum, _, _, _ = score_variant(old_hybrid, do.HYBRID)
    saved = pd.read_csv(B27DO_SUM)
    parity_rows = []
    for part in (*dn.dl.PARTS, 'POOLED_MAJOR'):
        calc = old_sum[(old_sum.variant == do.HYBRID) & (old_sum.partition == part)].iloc[0]
        exp = saved[(saved.variant == do.HYBRID) & (saved.partition == part)].iloc[0]
        for field in ('candidates','accepted','blocked','wr','pf','expectancy','total_net','max_loss_streak'):
            a = float(calc[field]); b = float(exp[field])
            ok = (math.isinf(a) and math.isinf(b)) or abs(a-b) <= 1e-9
            parity_rows.append({'layer':'B27DO_SAVED','partition':part,'field':field,'calculated':a,'expected':b,'pass':ok})
    if 'pass' in base_parity.columns:
        for r in base_parity.itertuples(index=False):
            parity_rows.append({'layer':'B27DK_BASELINE','partition':getattr(r,'partition',''),
                                'field':getattr(r,'field','parity'),'calculated':getattr(r,'calculated',np.nan),
                                'expected':getattr(r,'expected',np.nan),'pass':bool(getattr(r,'pass'))})
    parity = pd.DataFrame(parity_rows)
    parity.to_csv(OUT_PARITY, index=False)
    if not parity.empty and not bool(parity['pass'].all()):
        raise AssertionError('B27DQ prerequisite parity failed')

    live = attach_live_runner(stream, x5)
    primary = build_live_hybrid(stream, live)

    base_sum, base_zone, _, base_pool = score_variant(stream, 'FIXED_E20')
    pri_sum, pri_zone, pri_details, pri_pool = score_variant(primary, VARIANT)
    summary = pd.concat([base_sum, pri_sum], ignore_index=True)
    zones = pd.concat([base_zone, pri_zone], ignore_index=True)
    summary.to_csv(OUT_SUM, index=False)
    zones.to_csv(OUT_ZONE, index=False)
    pd.concat(pri_details, ignore_index=True).to_csv(OUT_DETAIL, index=False)

    sens_rows = []
    for bps in (0,2,5,10):
        stressed = apply_stop_slippage(primary, bps)
        ss, _, _, pool = score_variant(stressed, f'{VARIANT}_STOPSLIP_{bps}BPS')
        r = ss[ss.partition == 'POOLED_MAJOR'].iloc[0]
        sens_rows.append({'stop_slippage_bps':bps, **{k:r[k] for k in ('accepted','blocked','n','wins','wr','pf','expectancy','total_net','max_loss_streak')}})
    sensitivity = pd.DataFrame(sens_rows)
    sensitivity.to_csv(OUT_SENS, index=False)

    rb = summary[(summary.variant=='FIXED_E20') & (summary.partition=='POOLED_MAJOR')].iloc[0]
    rp = summary[(summary.variant==VARIANT) & (summary.partition=='POOLED_MAJOR')].iloc[0]
    oldp = saved[(saved.variant==do.HYBRID) & (saved.partition=='POOLED_MAJOR')].iloc[0]
    major_primary = summary[(summary.variant==VARIANT) & summary.partition.isin(dn.dl.MAJOR)]

    runner_acc = pri_pool[pri_pool.zone.isin(RUNNER_ZONES) & pri_pool.accepted].copy()
    armed = runner_acc[runner_acc.runner_armed == True].copy()
    stop_exits = runner_acc[runner_acc.live_exit_reason.isin(STOP_REASONS)].copy()
    gap_exits = int((runner_acc.live_exit_reason == 'LIVE_FLOOR_GAP_OPEN').sum())
    touch_exits = int((runner_acc.live_exit_reason == 'LIVE_FLOOR_TOUCH').sum())
    buffer_f35 = int((runner_acc.live_exit_reason == 'BUFFER_CLOSE_INVALIDATION_F35').sum())
    scheduled = int(pd.to_numeric(runner_acc.runner_scheduled_updates, errors='coerce').fillna(0).sum())
    activations = int(pd.to_numeric(runner_acc.runner_activations, errors='coerce').fillna(0).sum())

    support = bool(
        rp.total_net > rb.total_net
        and rp.pf >= 1.80
        and rp.wr >= 0.70
        and rp.accepted >= 0.80 * rb.accepted
        and (major_primary.total_net > 0).all()
    )
    status = 'B27DQ_LIVE_EXECUTABLE_SUPPORTED' if support else 'B27DQ_LIVE_EXECUTABLE_NOT_SUPPORTED'
    OUT_STATUS.write_text(status+'\n')

    lines = [
        '# B27DQ — B27DO Live-Executable TP/Runner Rescore — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Prerequisite parity: PASS.** Fixed-E20 baseline and saved B27DO hybrid metrics reproduced before corrected execution interpretation.','',
        '**Execution correction:** a floor learned from completed bar N is deliberately not scored until bar N+2, giving one full 5m placement/acknowledgement buffer.','',
        'ALT_0330 remains fixed E20. RAW_0530, LONDON and RAW_2330 use the same E10/step-10 structural runner with the corrected activation timing.','',
        '## Exact portfolio comparison after global one-position re-lock','',
        '| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in (*dn.dl.PARTS,'POOLED_MAJOR'):
        for variant in ('FIXED_E20', VARIANT):
            r = summary[(summary.partition==part)&(summary.variant==variant)].iloc[0]
            lines.append(f'| {part} | {variant} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['','## Pooled-major contribution by zone','',
              '| Zone | Exit | N | WR | PF | Exp | Net |',
              '|---|---|---:|---:|---:|---:|---:|']
    zp = zones[(zones.partition=='POOLED_MAJOR') & (zones.variant==VARIANT)]
    for z in dn.dl.ZONES:
        r = zp[zp.zone==z].iloc[0]
        mode = 'FIXED_E20' if z=='ALT_0330' else 'LIVE_EXEC_NPLUS2_E10'
        lines.append(f'| {z} | {mode} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |')

    lines += ['','## Live-execution anatomy','',
              f'- Accepted pooled-major runner-zone trades: **{len(runner_acc)}**; armed: **{len(armed)}**.',
              f'- Scheduled floor updates: **{scheduled}**; actual activations before exit: **{activations}**.',
              f'- Resting-floor touch exits: **{touch_exits}**; gap-open exits: **{gap_exits}**.',
              f'- Initial placement-buffer F35 close exits: **{buffer_f35}**.',
              '- No floor is credited on N+1 after being learned at N close; first eligible scoring bar is N+2.','',
              '## Stop-market slippage sensitivity','',
              '| Adverse stop slippage | N | WR | PF | Exp | Net | Max loss streak |',
              '|---:|---:|---:|---:|---:|---:|---:|']
    for r in sensitivity.itertuples(index=False):
        lines.append(f'| {int(r.stop_slippage_bps)} bps | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['','## Direct scorecard','',
              f'- Fixed E20 baseline: **N {int(rb.accepted)} / WR {pct(rb.wr)} / PF {num(rb.pf)} / Exp {usd(rb.expectancy)} / Net {usd(rb.total_net)}**.',
              f'- Original B27DO research hybrid: **N {int(oldp.accepted)} / WR {pct(oldp.wr)} / PF {num(oldp.pf)} / Exp {usd(oldp.expectancy)} / Net {usd(oldp.total_net)}**.',
              f'- Corrected B27DQ live-executable hybrid: **N {int(rp.accepted)} / WR {pct(rp.wr)} / PF {num(rp.pf)} / Exp {usd(rp.expectancy)} / Net {usd(rp.total_net)}**.',
              f'- Delta B27DQ vs original B27DO: **{usd(float(rp.total_net-oldp.total_net))}** net; WR **{(rp.wr-oldp.wr)*100:+.1f} pp**.',
              f'- Delta B27DQ vs fixed E20: **{usd(float(rp.total_net-rb.total_net))}** net; WR **{(rp.wr-rb.wr)*100:+.1f} pp**.','',
              '## Decision','',f'**Status: {status}**','',
              '**Evidence status: exploratory/engineering validation, not pristine unseen OOS.**','',
              'Research only; live BBC code/configuration unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
