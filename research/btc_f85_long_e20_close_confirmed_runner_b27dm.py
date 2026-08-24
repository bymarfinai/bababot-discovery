#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_e20_armed_runner_b27dl as dl

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_Summary.csv'
OUT_ZONE = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_ZoneSummary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_Detail.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_E20_CLOSE_CONFIRMED_RUNNER_B27DM_Status.txt'
B27DL_SUM = ROOT / 'BTC_F85_LONG_E20_ARMED_RUNNER_B27DL_Summary.csv'

PARTS = dl.PARTS
MAJOR = dl.MAJOR
ZONES = dl.ZONES
BAR5 = dl.BAR5
NOTIONAL = dl.NOTIONAL
FEE = dl.FEE

dg = dl.dg
dj = dl.dj


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def confirmed_exit(r, x5):
    entry_start = pd.Timestamp(r.entry_bar_start)
    exec_end = pd.Timestamp(r.execution_end)
    entry_px = float(r.entry_px)
    H = float(r.H)
    R = float(r.range)
    f35 = float(r.F35)
    e20 = float(r.E20)
    q = dl.fast_slice(x5, entry_start, exec_end)
    if q.empty:
        raise AssertionError(f'empty B27DM path {r.zone} {entry_start}')

    armed = False
    wick_reject = False
    arm_bar = pd.NaT
    first_e20_touch_bar = pd.NaT
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
            if hi >= e20:
                first_e20_touch_bar = ts
                if cl >= e20:
                    # Confirmation is known only at the completed 5m close.
                    armed = True
                    arm_bar = ts
                    floor = e20
                    floor_ext = 0.20
                    new_floor, new_ext = dl.ratchet_floor_from_close(cl, H, R, floor)
                    if new_floor > floor + 1e-12:
                        floor_raises += 1
                        floor = new_floor
                        floor_ext = new_ext
                    # The newly known floor becomes executable from the next bar.
                    continue

                # Causal rejection handling: final close is now known, so exit at that close.
                # Do not retroactively claim the earlier E20 intrabar price.
                wick_reject = True
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = cl
                reason = 'E20_WICK_REJECT_CLOSE_EXIT'
                break

            if cl < f35:
                exit_bar_start = ts
                exit_ts = ts + BAR5
                exit_px = cl
                reason = 'CLOSE_INVALIDATION_F35'
                break
            continue

        # Confirmed floor was known before this bar started.
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

        new_floor, new_ext = dl.ratchet_floor_from_close(cl, H, R, floor)
        if new_floor > floor + 1e-12:
            floor_raises += 1
            floor = new_floor
            floor_ext = new_ext

    if reason is None:
        pos = int(x5.index.searchsorted(exec_end, side='left'))
        if pos >= len(x5) or x5.index[pos] != exec_end:
            raise AssertionError(f'missing B27DM time-exit bar {exec_end}')
        exit_bar_start = exec_end
        exit_ts = exec_end
        exit_px = float(x5.iloc[pos].open)
        reason = 'RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_EXEC_END'

    gross = float(exit_px / entry_px - 1.0)
    net = gross * NOTIONAL - FEE

    # Every baseline TP candidate must correspond to either confirmation or wick rejection,
    # and no non-TP baseline candidate may invent an E20 event.
    fixed_tp = str(r.exit_reason) == 'TP_E20'
    e20_event = bool(armed or wick_reject)
    if fixed_tp != e20_event:
        raise AssertionError(
            f'B27DM E20-event parity failed {r.zone} {entry_start}: '
            f'fixed={r.exit_reason} armed={armed} wick_reject={wick_reject}'
        )

    return {
        'runner_exit_bar_start': exit_bar_start,
        'runner_exit_ts': exit_ts,
        'runner_exit_px': float(exit_px),
        'runner_exit_reason': reason,
        'runner_net_pnl_usd': net,
        'runner_armed': armed,
        'runner_wick_reject': wick_reject,
        'runner_first_e20_touch_bar': first_e20_touch_bar,
        'runner_arm_bar_start': arm_bar,
        'runner_final_floor': floor,
        'runner_final_floor_ext': floor_ext,
        'runner_floor_raises': floor_raises,
        'runner_max_high_ext': max_high_ext,
        'runner_max_close_ext': max_close_ext,
        'runner_delta_vs_fixed_candidate': net - float(r.net_pnl_usd),
    }


def attach_variant(stream, x5):
    rows = [confirmed_exit(r, x5) for r in stream.itertuples(index=False)]
    extra = pd.DataFrame(rows, index=stream.index)
    q = pd.concat([stream.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']
    q['exit_ts'] = pd.to_datetime(q.runner_exit_ts, utc=True)
    q['exit_px'] = q.runner_exit_px.astype(float)
    q['net_pnl_usd'] = q.runner_net_pnl_usd.astype(float)
    return q


def summarize(d):
    a = d[d.accepted].copy()
    m = dg.metrics(a)
    return {
        'candidates': len(d),
        'accepted': len(a),
        'blocked': int((~d.accepted).sum()),
        **m,
        'max_loss_streak': dl.streak_losses(a),
        'confirmed': int(a.runner_armed.sum()) if 'runner_armed' in a else np.nan,
        'wick_reject': int(a.runner_wick_reject.sum()) if 'runner_wick_reject' in a else np.nan,
    }


def main():
    x5, coverage = dj.b21.load5()
    stream = dl.load_stream(x5)

    parity = dl.baseline_parity(stream)
    parity.to_csv(OUT_PARITY, index=False)

    variant = attach_variant(stream, x5)

    summary_rows = []
    zone_rows = []
    baseline_decisions = []
    variant_decisions = []

    for part in PARTS:
        b = dg.lock(stream[stream.partition == part].copy(), 'B27DM_FIXED_E20')
        v = dg.lock(variant[variant.partition == part].copy(), 'B27DM_E20_CLOSE_CONFIRMED_STEP10_RUNNER')
        baseline_decisions.append(b)
        variant_decisions.append(v)
        summary_rows += [
            {'variant': 'FIXED_E20', 'partition': part, **summarize(b)},
            {'variant': 'E20_CLOSE_CONFIRMED_STEP10_RUNNER', 'partition': part, **summarize(v)},
        ]

        for zone in ZONES:
            bz = b[(b.zone == zone) & b.accepted].copy()
            vz = v[(v.zone == zone) & v.accepted].copy()
            bm = dg.metrics(bz)
            vm = dg.metrics(vz)
            zone_rows += [
                {'variant': 'FIXED_E20', 'partition': part, 'zone': zone, 'accepted': len(bz), **bm},
                {
                    'variant': 'E20_CLOSE_CONFIRMED_STEP10_RUNNER', 'partition': part, 'zone': zone,
                    'accepted': len(vz), **vm,
                    'confirmed': int(vz.runner_armed.sum()),
                    'wick_reject': int(vz.runner_wick_reject.sum()),
                    'floor_exits': int(vz.runner_exit_reason.isin(['RUNNER_FLOOR_TOUCH','RUNNER_FLOOR_GAP_OPEN']).sum()),
                    'confirmed_time_exits': int((vz.runner_exit_reason == 'RUNNER_TIME_EXIT').sum()),
                },
            ]

    bmaj = pd.concat([x for x in baseline_decisions if x.partition.iloc[0] in MAJOR], ignore_index=True)
    vmaj = pd.concat([x for x in variant_decisions if x.partition.iloc[0] in MAJOR], ignore_index=True)
    summary_rows += [
        {'variant': 'FIXED_E20', 'partition': 'POOLED_MAJOR', **summarize(bmaj)},
        {'variant': 'E20_CLOSE_CONFIRMED_STEP10_RUNNER', 'partition': 'POOLED_MAJOR', **summarize(vmaj)},
    ]

    for zone in ZONES:
        bz = bmaj[(bmaj.zone == zone) & bmaj.accepted].copy()
        vz = vmaj[(vmaj.zone == zone) & vmaj.accepted].copy()
        bm = dg.metrics(bz)
        vm = dg.metrics(vz)
        zone_rows += [
            {'variant': 'FIXED_E20', 'partition': 'POOLED_MAJOR', 'zone': zone, 'accepted': len(bz), **bm},
            {
                'variant': 'E20_CLOSE_CONFIRMED_STEP10_RUNNER', 'partition': 'POOLED_MAJOR', 'zone': zone,
                'accepted': len(vz), **vm,
                'confirmed': int(vz.runner_armed.sum()),
                'wick_reject': int(vz.runner_wick_reject.sum()),
                'floor_exits': int(vz.runner_exit_reason.isin(['RUNNER_FLOOR_TOUCH','RUNNER_FLOOR_GAP_OPEN']).sum()),
                'confirmed_time_exits': int((vz.runner_exit_reason == 'RUNNER_TIME_EXIT').sum()),
            },
        ]

    summary = pd.DataFrame(summary_rows)
    zones = pd.DataFrame(zone_rows)
    detail = pd.concat(variant_decisions, ignore_index=True)
    summary.to_csv(OUT_SUM, index=False)
    zones.to_csv(OUT_ZONE, index=False)
    detail.to_csv(OUT_DETAIL, index=False)

    rb = summary[(summary.variant == 'FIXED_E20') & (summary.partition == 'POOLED_MAJOR')].iloc[0]
    rv = summary[(summary.variant == 'E20_CLOSE_CONFIRMED_STEP10_RUNNER') & (summary.partition == 'POOLED_MAJOR')].iloc[0]
    major_variant = summary[(summary.variant == 'E20_CLOSE_CONFIRMED_STEP10_RUNNER') & summary.partition.isin(MAJOR)]
    supported = bool(
        rv.total_net > rb.total_net
        and rv.pf >= 1.80
        and rv.wr >= 0.70
        and rv.accepted >= 0.80 * rb.accepted
        and (major_variant.total_net > 0).all()
    )
    status = 'B27DM_CLOSE_CONFIRMED_RUNNER_SUPPORTED' if supported else 'B27DM_CLOSE_CONFIRMED_RUNNER_NOT_SUPPORTED'
    OUT_STATUS.write_text(status + '\n')

    accepted_variant = vmaj[vmaj.accepted].copy()
    confirmed = accepted_variant[accepted_variant.runner_armed].copy()
    wick_reject = accepted_variant[accepted_variant.runner_wick_reject].copy()
    milestone_rates = {}
    for e in (0.30, 0.40, 0.50, 0.60, 0.80, 1.00):
        milestone_rates[e] = float((confirmed.runner_max_high_ext >= e).mean()) if len(confirmed) else np.nan

    avg_confirmed_delta = float(confirmed.runner_delta_vs_fixed_candidate.mean()) if len(confirmed) else np.nan
    med_confirmed_delta = float(confirmed.runner_delta_vs_fixed_candidate.median()) if len(confirmed) else np.nan
    avg_wick_delta = float(wick_reject.runner_delta_vs_fixed_candidate.mean()) if len(wick_reject) else np.nan
    med_wick_delta = float(wick_reject.runner_delta_vs_fixed_candidate.median()) if len(wick_reject) else np.nan

    dl_pooled = None
    if B27DL_SUM.exists():
        dls = pd.read_csv(B27DL_SUM)
        q = dls[(dls.variant == 'E20_ARMED_STEP10_RUNNER') & (dls.partition == 'POOLED_MAJOR')]
        if len(q) == 1:
            dl_pooled = q.iloc[0]

    lines = [
        '# B27DM — E20 Close-Confirmed Step-10 Runner — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        '**Audit status: PASS.** Fixed-E20 B27DK parity was reproduced before B27DM was interpreted.', '',
        'Frozen causal rule: on the first E20-touch bar, completed close >= E20 confirms the runner; completed close < E20 exits at that bar close. No retroactive E20 fill is allowed. Confirmed trades then use the same B27DL step-10 structural floor.', '',
        '## Exact portfolio comparison after global one-position re-lock', '',
        '| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r.partition} | {r.variant} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | "
            f"{pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |"
        )

    lines += ['', '## Pooled-major contribution by zone', '',
              '| Zone | Variant | N | WR | PF | Exp | Net | Confirmed | Wick reject | Floor exits |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    zp = zones[zones.partition == 'POOLED_MAJOR']
    for _, r in zp.iterrows():
        if r.variant == 'FIXED_E20':
            lines.append(
                f"| {r.zone} | {r.variant} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | - | - | - |"
            )
        else:
            lines.append(
                f"| {r.zone} | {r.variant} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | "
                f"{int(r.confirmed)} | {int(r.wick_reject)} | {int(r.floor_exits)} |"
            )

    lines += ['', '## Confirmation anatomy', '',
              f'Accepted pooled-major confirmed runners: **{len(confirmed)}**.',
              f'Accepted pooled-major wick-reject close exits: **{len(wick_reject)}**.',
              f'Average candidate-level delta on confirmed runners vs fixed E20: **{usd(avg_confirmed_delta)}**; median **{usd(med_confirmed_delta)}**.',
              f'Average candidate-level delta on wick-reject exits vs fixed E20: **{usd(avg_wick_delta)}**; median **{usd(med_wick_delta)}**.', '']
    for e, rate in milestone_rates.items():
        lines.append(f'- High reached E{int(e*100):02d} or farther among confirmed runners: **{pct(rate)}**.')

    lines += ['', '## Decision', '',
              f'Pooled-major fixed E20: **N {int(rb.accepted)} / WR {pct(rb.wr)} / PF {num(rb.pf)} / Exp {usd(rb.expectancy)} / Net {usd(rb.total_net)}**.',
              f'Pooled-major B27DM: **N {int(rv.accepted)} / WR {pct(rv.wr)} / PF {num(rv.pf)} / Exp {usd(rv.expectancy)} / Net {usd(rv.total_net)}**.',
              f'Net delta vs fixed E20: **{usd(float(rv.total_net-rb.total_net))}**; accepted delta: **{int(rv.accepted-rb.accepted):+d}**; WR delta: **{100*(rv.wr-rb.wr):+.1f} pp**.']
    if dl_pooled is not None:
        lines.append(
            f'For context, prior B27DL universal touch-armed runner: **N {int(dl_pooled.accepted)} / WR {pct(dl_pooled.wr)} / PF {num(dl_pooled.pf)} / Exp {usd(dl_pooled.expectancy)} / Net {usd(dl_pooled.total_net)}**.'
        )
        lines.append(f'B27DM net delta vs B27DL: **{usd(float(rv.total_net-dl_pooled.total_net))}**; WR delta: **{100*(rv.wr-dl_pooled.wr):+.1f} pp**.')
    lines += [f'**Status: {status}**', '', 'Research/operating exit experiment only; live BBC unchanged.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
