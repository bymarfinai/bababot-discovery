#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import pandas as pd

import btc_f85_long_single_position_portfolio_b27dg as dg
import btc_f85_long_range_completion_recency_b27dj as dj

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F85_LONG_4ZONE_OPERATING_PORTFOLIO_B27DK_Result.md'
OUT_SUM = ROOT / 'BTC_F85_LONG_4ZONE_OPERATING_PORTFOLIO_B27DK_Summary.csv'
OUT_ZONE = ROOT / 'BTC_F85_LONG_4ZONE_OPERATING_PORTFOLIO_B27DK_ZoneSummary.csv'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_4ZONE_OPERATING_PORTFOLIO_B27DK_Detail.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_4ZONE_OPERATING_PORTFOLIO_B27DK_Status.txt'

PARTS = ('external', 'development', 'reference_validation', 'august')
MAJOR = ('external', 'development', 'reference_validation')
ADD_ZONES = ('RAW_0530', 'RAW_2330')


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if float(x) == float('inf'): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main():
    c = dj.load_candidates()
    x5, coverage = dj.b21.load5()
    c, _ = dj.attach_range_completion(c, x5)

    # User-authorized operating portfolio override:
    # keep frozen PRIMARY_2ZONE unchanged and add BOTH B27DJ-filtered zones,
    # regardless of the formal B27DJ promotion gate. Research/operating rescore only;
    # no live BBC code is changed here.
    add = c[c.zone.isin(ADD_ZONES) & c.range_completed_second_half].copy()
    pri = c[c.primary_eligible].copy()
    stream = pd.concat([pri, add], ignore_index=True)

    decisions = []
    summary_rows = []
    zone_rows = []
    for part in PARTS:
        d = dg.lock(stream[stream.partition == part].copy(), 'B27DK_4ZONE_OPERATING')
        decisions.append(d)
        a = d[d.accepted].copy()
        m = dg.metrics(a)
        summary_rows.append({
            'partition': part,
            'candidates': len(d),
            'accepted': len(a),
            'skipped_open': int((~d.accepted).sum()),
            **m,
        })
        for zone in ('ALT_0330', 'LONDON', *ADD_ZONES):
            z = a[a.zone == zone].copy()
            zm = dg.metrics(z)
            zone_rows.append({
                'partition': part,
                'zone': zone,
                'accepted': len(z),
                **zm,
            })

    all_dec = pd.concat(decisions, ignore_index=True)
    maj = all_dec[all_dec.partition.isin(MAJOR)].copy()
    a = maj[maj.accepted].copy()
    m = dg.metrics(a)
    summary_rows.append({
        'partition': 'POOLED_MAJOR',
        'candidates': len(maj),
        'accepted': len(a),
        'skipped_open': int((~maj.accepted).sum()),
        **m,
    })
    for zone in ('ALT_0330', 'LONDON', *ADD_ZONES):
        z = a[a.zone == zone].copy()
        zm = dg.metrics(z)
        zone_rows.append({
            'partition': 'POOLED_MAJOR',
            'zone': zone,
            'accepted': len(z),
            **zm,
        })

    summary = pd.DataFrame(summary_rows)
    zones = pd.DataFrame(zone_rows)
    summary.to_csv(OUT_SUM, index=False)
    zones.to_csv(OUT_ZONE, index=False)
    all_dec.to_csv(OUT_DETAIL, index=False)
    OUT_STATUS.write_text('B27DK_4ZONE_OPERATING_PORTFOLIO_RESCORED\n')

    lines = [
        '# B27DK — 4-Zone Operating Portfolio Exact Rescore', '',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        'Operating zones:',
        '- ALT_0330 with frozen TOUCH_FIRST_HALF primary eligibility.',
        '- RAW_0530 with B27DJ RANGE_COMPLETED_SECOND_HALF.',
        '- LONDON 08:00 frozen Same-Bar F85 primary eligibility.',
        '- RAW_2330 with B27DJ RANGE_COMPLETED_SECOND_HALF.', '',
        'All four zones are merged chronologically and rescored with the same global one-BTC-position lock. This is not a simple sum of standalone zone results.', '',
        '## Portfolio', '',
        '| Partition | Candidates | Accepted | Blocked while open | WR | PF | Exp | Net |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in summary.iterrows():
        lines.append(f"| {r.partition} | {int(r.candidates)} | {int(r.accepted)} | {int(r.skipped_open)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |")

    lines += ['', '## Accepted trades by zone after global lock', '',
              '| Partition | Zone | N | WR | PF | Exp | Net |',
              '|---|---|---:|---:|---:|---:|---:|']
    for _, r in zones.iterrows():
        lines.append(f"| {r.partition} | {r.zone} | {int(r.accepted)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |")

    lines += ['', '**Status: B27DK_4ZONE_OPERATING_PORTFOLIO_RESCORED**', '',
              'Research/operating portfolio rescore only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
