#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M5'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_YEAR = ROOT / f'{PFX}_Yearly.csv'
OUT_ROLL = ROOT / f'{PFX}_Rolling.csv'
OUT_H2H = ROOT / f'{PFX}_RAW0530_HeadToHead.csv'
OUT_SEL = ROOT / f'{PFX}_Selection.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

M2_STATUS = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Status.txt'
M2_SUM = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Summary.csv'
M2_CAND = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Candidates.csv'
EXPECTED_STATUS = 'ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY'
END = pd.Timestamp('2026-08-26', tz='UTC')
MAJOR = ('external', 'development', 'reference_validation')
ALL_PARTS = (*MAJOR, 'august')
CANDIDATES = [
    ('ALT_0330', 'F95'),
    ('RAW_0530', 'F90'),
    ('RAW_0530', 'F85'),
    ('LONDON', 'F90'),
    ('RAW_2330', 'F95'),
]


def rate(g: pd.DataFrame) -> float:
    return float((g.outcome.astype(str) == 'H2').mean()) if len(g) else np.nan


def q(s, qv):
    z = pd.to_numeric(s, errors='coerce').dropna()
    return float(z.quantile(qv)) if len(z) else np.nan


def fmt_pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def fmt_num(x, digits=3):
    return '-' if pd.isna(x) else f'{float(x):.{digits}f}'


def window_rows(g: pd.DataFrame, months: int, min_n: int):
    start_anchor = pd.Timestamp('2020-01-01', tz='UTC') + pd.DateOffset(months=months)
    anchors = pd.date_range(start_anchor, pd.Timestamp('2026-08-01', tz='UTC'), freq='MS')
    rows = []
    for z in anchors:
        a = z - pd.DateOffset(months=months)
        w = g[(g.execution_start >= a) & (g.execution_start < z)]
        rows.append({
            'window_months': months,
            'window_start': a,
            'window_end': z,
            'n': len(w),
            'h2_rate': rate(w),
            'eligible': len(w) >= min_n,
        })
    return rows


def require_inputs():
    if M2_STATUS.read_text().strip() != EXPECTED_STATUS:
        raise RuntimeError('M5 blocked: corrected M2 status gate failed')
    for p in (M2_SUM, M2_CAND):
        if not p.exists():
            raise RuntimeError(f'M5 blocked: missing {p.name}')


def main():
    require_inputs()
    sm = pd.read_csv(M2_SUM)
    c = pd.read_csv(M2_CAND)
    for col in ('reference_start', 'execution_start', 'fill_ts'):
        if col in c.columns:
            c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    c = c[c.filled.astype(str).str.lower().eq('true')].copy()
    c = c[c.partition.astype(str).isin(ALL_PARTS)].copy()

    # Every frozen M5 candidate must already be a corrected-M2 pooled SCREEN_PASS.
    for clock, level in CANDIDATES:
        r = sm[(sm.clock == clock) & (sm.level == level) & (sm.partition == 'POOLED_MAJOR')]
        if len(r) != 1 or str(r.iloc[0].screen) != 'SCREEN_PASS':
            raise AssertionError(f'{clock} {level} is not corrected-M2 SCREEN_PASS')
        cc = c[(c.clock == clock) & (c.level == level)]
        if len(cc) == 0:
            raise AssertionError(f'no filled rows for {clock} {level}')

    year_rows, roll_rows, sum_rows = [], [], []

    for clock, level in CANDIDATES:
        g_all = c[(c.clock == clock) & (c.level == level)].copy()
        g_major = g_all[g_all.partition.isin(MAJOR)].copy()

        part_ok = True
        part_stats = {}
        for p in MAJOR:
            gp = g_major[g_major.partition == p]
            pr = rate(gp)
            part_stats[p] = (len(gp), pr)
            part_ok = part_ok and len(gp) >= 30 and (not pd.isna(pr)) and pr >= .70

        eligible_year_rates = []
        eligible_year_count = 0
        years_ge70 = 0
        for y in range(2020, 2027):
            gy = g_all[g_all.execution_start.dt.year == y]
            full_year = y <= 2025
            eligible = full_year and len(gy) >= 10
            yr = rate(gy)
            year_rows.append({
                'clock': clock, 'level': level, 'year': y, 'full_year': full_year,
                'n': len(gy), 'h2_rate': yr, 'eligible_for_screen': eligible,
            })
            if eligible:
                eligible_year_count += 1
                eligible_year_rates.append(yr)
                if yr >= .70:
                    years_ge70 += 1

        yearly_share = years_ge70 / eligible_year_count if eligible_year_count else np.nan
        yearly_min = min(eligible_year_rates) if eligible_year_rates else np.nan

        r12 = window_rows(g_all, 12, 12)
        r6 = window_rows(g_all, 6, 6)
        for rr in r12 + r6:
            roll_rows.append({'clock': clock, 'level': level, **rr})

        e12 = [x for x in r12 if x['eligible']]
        e6 = [x for x in r6 if x['eligible']]
        r12_rates = [x['h2_rate'] for x in e12]
        r6_rates = [x['h2_rate'] for x in e6]
        r12_share = float(np.mean([x >= .70 for x in r12_rates])) if r12_rates else np.nan
        r12_min = float(min(r12_rates)) if r12_rates else np.nan
        r12_median = float(np.median(r12_rates)) if r12_rates else np.nan
        r6_share = float(np.mean([x >= .70 for x in r6_rates])) if r6_rates else np.nan
        r6_min = float(min(r6_rates)) if r6_rates else np.nan
        r6_median = float(np.median(r6_rates)) if r6_rates else np.nan

        recent = g_all[(g_all.execution_start >= END - pd.Timedelta(days=365)) & (g_all.execution_start < END)]
        recent_n, recent_rate = len(recent), rate(recent)

        winners = g_major[g_major.outcome.astype(str) == 'H2']
        pooled_rate = rate(g_major)
        mae_p90 = q(winners.mae_ru, .90)
        mae_p95 = q(winners.mae_ru, .95)
        med_to_h2 = q(winners.minutes_to_h2, .50)

        robust = (
            part_ok
            and eligible_year_count >= 4
            and not pd.isna(yearly_share) and yearly_share >= .75
            and not pd.isna(yearly_min) and yearly_min >= .60
            and len(e12) >= 24
            and not pd.isna(r12_share) and r12_share >= .75
            and not pd.isna(r12_min) and r12_min >= .60
            and recent_n >= 12
            and not pd.isna(recent_rate) and recent_rate >= .70
        )

        sum_rows.append({
            'clock': clock, 'level': level,
            'pooled_major_n': len(g_major), 'pooled_major_h2_rate': pooled_rate,
            'external_n': part_stats['external'][0], 'external_h2_rate': part_stats['external'][1],
            'development_n': part_stats['development'][0], 'development_h2_rate': part_stats['development'][1],
            'reference_validation_n': part_stats['reference_validation'][0], 'reference_validation_h2_rate': part_stats['reference_validation'][1],
            'eligible_full_years': eligible_year_count,
            'yearly_share_ge70': yearly_share, 'yearly_min_h2_rate': yearly_min,
            'rolling12_eligible_windows': len(e12), 'rolling12_share_ge70': r12_share,
            'rolling12_min_h2_rate': r12_min, 'rolling12_median_h2_rate': r12_median,
            'rolling6_eligible_windows': len(e6), 'rolling6_share_ge70': r6_share,
            'rolling6_min_h2_rate': r6_min, 'rolling6_median_h2_rate': r6_median,
            'recent365_n': recent_n, 'recent365_h2_rate': recent_rate,
            'winner_mae_p90': mae_p90, 'winner_mae_p95': mae_p95,
            'winner_median_minutes_to_h2': med_to_h2,
            'robustness_screen': 'ROBUST_PASS' if robust else 'ROBUST_FAIL',
        })

    S = pd.DataFrame(sum_rows)
    Y = pd.DataFrame(year_rows)
    R = pd.DataFrame(roll_rows)

    # RAW0530 direct decomposition: common fills vs incremental cohorts.
    raw = c[(c.clock == 'RAW_0530') & (c.partition.isin(MAJOR)) & (c.level.isin(['F90', 'F85']))].copy()
    f90 = raw[raw.level == 'F90'].set_index('reference_start', drop=False)
    f85 = raw[raw.level == 'F85'].set_index('reference_start', drop=False)
    s90, s85 = set(f90.index), set(f85.index)
    cohorts = [
        ('COMMON_F90_VIEW', f90.loc[list(s90 & s85)] if (s90 & s85) else f90.iloc[0:0]),
        ('COMMON_F85_VIEW', f85.loc[list(s90 & s85)] if (s90 & s85) else f85.iloc[0:0]),
        ('F90_ONLY_INCREMENTAL', f90.loc[list(s90 - s85)] if (s90 - s85) else f90.iloc[0:0]),
        ('F85_ONLY_INCREMENTAL', f85.loc[list(s85 - s90)] if (s85 - s90) else f85.iloc[0:0]),
        ('ALL_F90', f90),
        ('ALL_F85', f85),
    ]
    h2h_rows = []
    for name, gg in cohorts:
        h2h_rows.append({'cohort': name, 'n': len(gg), 'h2_rate': rate(gg)})
    H2H = pd.DataFrame(h2h_rows)

    # Final frozen selection logic.
    selections = []
    for clock in ('ALT_0330', 'RAW_0530', 'LONDON', 'RAW_2330'):
        ss = S[S.clock == clock].copy()
        pp = ss[ss.robustness_screen == 'ROBUST_PASS'].copy()
        if clock != 'RAW_0530':
            if len(pp) == 1:
                r = pp.iloc[0]
                selections.append({'clock': clock, 'selected_level': r.level, 'status': 'ENTRY_LOCKED', 'reason': 'single frozen candidate passed M5 robustness'})
            else:
                selections.append({'clock': clock, 'selected_level': '', 'status': 'NOT_LOCKED', 'reason': 'frozen candidate failed M5 robustness'})
        else:
            if len(pp) == 0:
                selections.append({'clock': clock, 'selected_level': '', 'status': 'NOT_LOCKED', 'reason': 'F90 and F85 both failed M5 robustness'})
            elif len(pp) == 1:
                r = pp.iloc[0]
                selections.append({'clock': clock, 'selected_level': r.level, 'status': 'ENTRY_LOCKED', 'reason': 'only RAW0530 candidate passing M5 robustness'})
            else:
                def key(r):
                    mae = float(r.winner_mae_p90) if not pd.isna(r.winner_mae_p90) else math.inf
                    return (
                        float(r.rolling12_min_h2_rate),
                        float(r.rolling12_share_ge70),
                        float(r.recent365_h2_rate),
                        float(r.pooled_major_h2_rate),
                        -mae,
                        int(r.pooled_major_n),
                    )
                rr = sorted([r for _, r in pp.iterrows()], key=key, reverse=True)[0]
                selections.append({'clock': clock, 'selected_level': rr.level, 'status': 'ENTRY_LOCKED', 'reason': 'both passed; frozen lexicographic robustness tie-break selected this level'})

    SEL = pd.DataFrame(selections)
    S.to_csv(OUT_SUM, index=False)
    Y.to_csv(OUT_YEAR, index=False)
    R.to_csv(OUT_ROLL, index=False)
    H2H.to_csv(OUT_H2H, index=False)
    SEL.to_csv(OUT_SEL, index=False)
    OUT_STATUS.write_text('ETH_M5_ENTRY_ROBUSTNESS_COMPLETED\n')

    lines = [
        '# ETH Transfer — M5 Entry Robustness & Final Selection — Result', '',
        'No new entry levels, stop, target, PnL, PF, fee, or leverage logic was tested.', '',
        '| Habitat | Level | N | Pooled H2 | Worst 12M | 12M >=70% | Recent 365D | Winner MAE P90 | Screen |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|',
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f'| {r.clock} | {r.level} | {int(r.pooled_major_n)} | {fmt_pct(r.pooled_major_h2_rate)} | '
            f'{fmt_pct(r.rolling12_min_h2_rate)} | {fmt_pct(r.rolling12_share_ge70)} | '
            f'{int(r.recent365_n)} / {fmt_pct(r.recent365_h2_rate)} | {fmt_num(r.winner_mae_p90)}R | {r.robustness_screen} |'
        )
    lines += ['', '## RAW_0530 head-to-head', '', '| Cohort | N | H2 rate |', '|---|---:|---:|']
    for r in H2H.itertuples(index=False):
        lines.append(f'| {r.cohort} | {int(r.n)} | {fmt_pct(r.h2_rate)} |')
    lines += ['', '## Final M5 selection', '', '| Habitat | Selected level | Status | Reason |', '|---|---|---|---|']
    for r in SEL.itertuples(index=False):
        lines.append(f'| {r.clock} | {r.selected_level or "-"} | {r.status} | {r.reason} |')
    lines += ['', '**Status: ETH_M5_ENTRY_ROBUSTNESS_COMPLETED**', '', 'Stop after M5. No M6 was run automatically.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
