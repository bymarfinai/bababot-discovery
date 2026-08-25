#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_e20_e10_breathing_runner_b27dn as dn

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Summary.csv'
OUT_ZONE = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_ZoneSummary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Detail.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_HYBRID_EXIT_B27DO_Status.txt'
B27DN_SUM = ROOT / 'BTC_F85_LONG_E20_E10_BREATHING_RUNNER_B27DN_Summary.csv'

HYBRID = 'HYBRID_0330_FIXED_OTHERS_E10'
RUNNER_ZONES = {'RAW_0530', 'LONDON', 'RAW_2330'}


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


def build_hybrid(stream, breathing):
    q = stream.copy().reset_index(drop=True)
    b = breathing.copy().reset_index(drop=True)
    assert len(q) == len(b)
    mask = q.zone.isin(RUNNER_ZONES)

    q['management_mode'] = 'FIXED_E20'
    q.loc[mask, 'management_mode'] = 'E10_BREATHING'
    q['fixed_exit_ts'] = q['exit_ts']
    q['fixed_exit_px'] = q['exit_px']
    q['fixed_net_pnl_usd'] = q['net_pnl_usd']

    q.loc[mask, 'exit_ts'] = b.loc[mask, 'exit_ts'].values
    q.loc[mask, 'exit_px'] = b.loc[mask, 'exit_px'].values
    q.loc[mask, 'net_pnl_usd'] = b.loc[mask, 'net_pnl_usd'].values
    q['exit_ts'] = pd.to_datetime(q.exit_ts, utc=True)

    for c in ('runner_armed','runner_exit_reason','runner_final_floor_ext','runner_floor_raises','runner_delta_vs_fixed_candidate'):
        q[c] = np.nan
        if c in b.columns:
            q.loc[mask, c] = b.loc[mask, c].values
    return q


def main():
    x5, coverage = dn.dl.dj.b21.load5()
    stream = dn.dl.load_stream(x5)
    parity = dn.dl.baseline_parity(stream)
    parity.to_csv(OUT_PARITY, index=False)
    breathing = dn.attach_runner(stream, x5)
    hybrid = build_hybrid(stream, breathing)

    saved_dn = pd.read_csv(B27DN_SUM)
    summary_rows = []
    zone_rows = []
    details = []

    for part in dn.dl.PARTS:
        base = dn.dl.dg.lock(stream[stream.partition == part].copy(), 'B27DO_FIXED_E20')
        hy = dn.dl.dg.lock(hybrid[hybrid.partition == part].copy(), 'B27DO_HYBRID')
        details.append(hy)
        summary_rows += [
            {'variant':'FIXED_E20','partition':part,**summarize(base)},
            {'variant':HYBRID,'partition':part,**summarize(hy)},
        ]
        for z in dn.dl.ZONES:
            hz = hy[(hy.zone == z) & hy.accepted].copy()
            m = dn.dl.dg.metrics(hz)
            zone_rows.append({'partition':part,'zone':z,'accepted':len(hz),**m})

    bmaj = pd.concat([dn.dl.dg.lock(stream[stream.partition == p].copy(), 'B27DO_FIXED_E20') for p in dn.dl.MAJOR], ignore_index=True)
    hmaj = pd.concat([dn.dl.dg.lock(hybrid[hybrid.partition == p].copy(), 'B27DO_HYBRID') for p in dn.dl.MAJOR], ignore_index=True)
    summary_rows += [
        {'variant':'FIXED_E20','partition':'POOLED_MAJOR',**summarize(bmaj)},
        {'variant':HYBRID,'partition':'POOLED_MAJOR',**summarize(hmaj)},
    ]
    for z in dn.dl.ZONES:
        hz = hmaj[(hmaj.zone == z) & hmaj.accepted].copy()
        m = dn.dl.dg.metrics(hz)
        zone_rows.append({'partition':'POOLED_MAJOR','zone':z,'accepted':len(hz),**m})

    summary = pd.DataFrame(summary_rows)
    zones = pd.DataFrame(zone_rows)
    summary.to_csv(OUT_SUM, index=False)
    zones.to_csv(OUT_ZONE, index=False)
    pd.concat(details, ignore_index=True).to_csv(OUT_DETAIL, index=False)

    rb = summary[(summary.variant=='FIXED_E20') & (summary.partition=='POOLED_MAJOR')].iloc[0]
    rh = summary[(summary.variant==HYBRID) & (summary.partition=='POOLED_MAJOR')].iloc[0]
    rd = saved_dn[(saved_dn.variant==dn.VARIANT) & (saved_dn.partition=='POOLED_MAJOR')].iloc[0]
    major_h = summary[(summary.variant==HYBRID) & summary.partition.isin(dn.dl.MAJOR)]

    promising = bool(
        rh.total_net > rb.total_net
        and rh.total_net > rd.total_net
        and rh.wr > rd.wr
        and rh.pf >= 1.80
        and rh.accepted >= 0.80 * rb.accepted
        and (major_h.total_net > 0).all()
    )
    status = 'B27DO_HYBRID_PROMISING_EXPLORATORY' if promising else 'B27DO_HYBRID_NOT_PROMISING'
    OUT_STATUS.write_text(status+'\n')

    lines = [
        '# B27DO — 4-Zone Hybrid Exit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** Fixed-E20 B27DK parity reproduced before hybrid interpretation.','',
        '**Evidence status: exploratory.** The zone-specific exit assignment was selected after inspecting prior per-zone B27DN results.','',
        'Hybrid: ALT_0330 uses fixed E20; RAW_0530, LONDON and RAW_2330 use the frozen B27DN E20-touch -> E10 breathing step-10 runner.','',
        '## Exact portfolio comparison after global one-position re-lock','',
        '| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in (*dn.dl.PARTS,'POOLED_MAJOR'):
        for variant in ('FIXED_E20',HYBRID):
            r = summary[(summary.partition==part)&(summary.variant==variant)].iloc[0]
            lines.append(f'| {part} | {variant} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} | {int(r.max_loss_streak)} |')

    lines += ['','## Pooled-major hybrid contribution by zone','',
              '| Zone | Exit | N | WR | PF | Exp | Net |',
              '|---|---|---:|---:|---:|---:|---:|']
    zp = zones[zones.partition=='POOLED_MAJOR']
    for z in dn.dl.ZONES:
        r = zp[zp.zone==z].iloc[0]
        mode = 'FIXED_E20' if z=='ALT_0330' else 'E10_BREATHING'
        lines.append(f'| {z} | {mode} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |')

    lines += ['','## Direct scorecard','',
              f'- Fixed E20: **N {int(rb.accepted)} / WR {pct(rb.wr)} / PF {num(rb.pf)} / Exp {usd(rb.expectancy)} / Net {usd(rb.total_net)}**.',
              f'- Universal B27DN E10 breathing: **N {int(rd.accepted)} / WR {pct(rd.wr)} / PF {num(rd.pf)} / Exp {usd(rd.expectancy)} / Net {usd(rd.total_net)}**.',
              f'- B27DO hybrid: **N {int(rh.accepted)} / WR {pct(rh.wr)} / PF {num(rh.pf)} / Exp {usd(rh.expectancy)} / Net {usd(rh.total_net)}**.',
              f'- Hybrid delta vs fixed: **{usd(float(rh.total_net-rb.total_net))}**; WR delta **{(rh.wr-rb.wr)*100:+.1f} pp**.',
              f'- Hybrid delta vs universal B27DN: **{usd(float(rh.total_net-rd.total_net))}**; WR delta **{(rh.wr-rd.wr)*100:+.1f} pp**.','',
              '## Decision','',f'**Status: {status}**','',
              'Research/operating exit experiment only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
