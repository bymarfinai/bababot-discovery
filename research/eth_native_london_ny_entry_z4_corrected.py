#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_native_london_ny_entry_z4 as m


def select_development(S: pd.DataFrame):
    cand = []
    for mode in m.EXECUTABLE:
        qq = S[(S.partition == 'development') & (S['mode'] == mode) & S.cohort.isin(m.COHORTS)]
        if len(qq) != 2:
            continue
        ok = True
        for r in qq.itertuples(index=False):
            ok = ok and (
                int(r.available_entries) >= 35 and
                float(r.participation) >= .40 and
                float(r.C10_reach_rate) >= .60 and
                float(r.C20_reach_rate) >= .45 and
                int(r.C20_reach) > int(r.close_below_L_before_C20)
            )
        if ok:
            cand.append({
                'mode': mode,
                'min_c20': float(qq.C20_reach_rate.min()),
                'min_c10': float(qq.C10_reach_rate.min()),
                'entry_frac': float(qq.median_entry_frac.max()),
                'min_part': float(qq.participation.min()),
                'tie': m.TIE_PRIORITY[mode],
            })
    if not cand:
        return None, pd.DataFrame()
    L = pd.DataFrame(cand).sort_values(
        ['min_c20', 'min_c10', 'entry_frac', 'min_part', 'tie'],
        ascending=[False, False, True, False, True]
    ).reset_index(drop=True)
    return str(L.iloc[0]['mode']), L


def replication(S: pd.DataFrame, mode: str | None):
    rows = []
    if mode is None:
        return rows, False
    all_ok = True
    for part in ('external', 'reference_validation'):
        for cohort in m.COHORTS:
            r = S[(S.partition == part) & (S['mode'] == mode) & (S.cohort == cohort)].iloc[0]
            ok = (
                int(r.available_entries) >= 20 and
                float(r.participation) >= .30 and
                float(r.C10_reach_rate) >= .55 and
                float(r.C20_reach_rate) >= .40 and
                int(r.C20_reach) > int(r.close_below_L_before_C20)
            )
            all_ok = all_ok and ok
            rows.append((part, cohort, r, ok))
    return rows, all_ok


def main():
    m.synthetic_tests()
    m.z2.read_provenance()
    x5, coverage = base.load5('ETHUSDT')
    if coverage < .995:
        raise RuntimeError(f'ETH raw 5m coverage too low: {coverage:.6f}')

    C = m.build_cases(x5)
    A = m.build_audit(x5, C)
    S = m.summarize(C, A)
    A.to_csv(m.OUT_AUDIT, index=False)
    S.to_csv(m.OUT_SUMMARY, index=False)

    selected, leaderboard = select_development(S)
    reps, supported = replication(S, selected)
    if selected is None:
        status = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4_NO_DEV_CANDIDATE'
    elif supported:
        status = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4_SUPPORTED'
    else:
        status = 'ETH_NATIVE_LONDON_NY_ENTRY_Z4_CANDIDATE_NOT_REPLICATED'
    m.OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH Native London->New York Entry Discovery — Z4 Result', '',
        f'Raw ETHUSDT 5m coverage: **{coverage:.4%}**.',
        'Frozen lineage: 18:30-00:00 WIB reference -> 00:00-06:30 WIB execution; F95/F90 shallow retest; B00 completed 5m close >H.',
        'C05/C10/C20 are structural diagnostics only, not TP.', '',
        '## Pooled major entry-mode comparison', '',
        '| Cohort | Mode | B00 | Entries | Participation | Median entry frac | C10 post-entry | C20 post-entry | Close<L before C20 | Median adverse R |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    pooled = S[S.partition == 'POOLED_MAJOR']
    for cohort in m.COHORTS:
        for mode in m.MODES:
            r = pooled[(pooled.cohort == cohort) & (pooled['mode'] == mode)].iloc[0]
            med_entry = '-' if pd.isna(r.median_entry_frac) else f'{float(r.median_entry_frac):.3f}'
            med_adv = '-' if pd.isna(r.median_adverse_R) else f'{float(r.median_adverse_R):.3f}'
            lines.append(
                f'| {cohort} | {mode} | {int(r.b00_cases)} | {int(r.available_entries)} | {m.pct(r.participation)} | '
                f'{med_entry} | {m.pct(r.C10_reach_rate)} | {m.pct(r.C20_reach_rate)} | '
                f'{int(r.close_below_L_before_C20)} | {med_adv} |'
            )

    lines += ['', '## Development selection', '']
    if selected is None:
        lines += ['No executable entry mode passed the frozen development gate for both F95 and F90.', '']
    else:
        lines += [f'Selected development mode: **{selected}**.', '']
        for cohort in m.COHORTS:
            r = S[(S.partition == 'development') & (S['mode'] == selected) & (S.cohort == cohort)].iloc[0]
            lines.append(
                f'- {cohort}: N={int(r.available_entries)}/{int(r.b00_cases)} ({m.pct(r.participation)}), '
                f'C10={m.pct(r.C10_reach_rate)}, C20={m.pct(r.C20_reach_rate)}, median entry frac={float(r.median_entry_frac):.3f}.'
            )
        lines += ['', 'Historical replication:', '']
        for part, cohort, r, ok in reps:
            lines.append(
                f'- {part} {cohort}: N={int(r.available_entries)}/{int(r.b00_cases)} ({m.pct(r.participation)}), '
                f'C10={m.pct(r.C10_reach_rate)}, C20={m.pct(r.C20_reach_rate)} -> {"PASS" if ok else "FAIL"}.'
            )

    if len(leaderboard):
        lines += ['', 'Development executable leaderboard:', '']
        for i, r in leaderboard.iterrows():
            lines.append(
                f'- #{i+1} {r["mode"]}: min C20={m.pct(r["min_c20"])}, min C10={m.pct(r["min_c10"])}, '
                f'worst median entry frac={float(r["entry_frac"]):.3f}, min participation={m.pct(r["min_part"])}.'
            )

    lines += ['', f'**Status: {status}**', '', 'Stop after Z4. No TP/SL/PnL milestone was run automatically.']
    m.OUT_RESULT.write_text('\n'.join(lines) + '\n')
    print(m.OUT_RESULT.read_text())


if __name__ == '__main__':
    main()
