#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eth_f85_f15_transfer_m1_k1_opp0 as data_base

PFX = 'BNB_F85_LONG_TRANSFER_M6_ENTRY_DEPTH_DIAGNOSTICS_B27EI'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_GEOM = ROOT / f'{PFX}_GeometrySummary.csv'
OUT_ATLAS = ROOT / f'{PFX}_EntryAtlas.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
MAJOR = ('external', 'development', 'reference_validation')
SOURCES = ('ALT_0330', 'RAW_0530')
LEVELS = (80, 75, 70, 65)
BAR5 = pd.Timedelta(minutes=5)


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    return x.iloc[int(x.index.searchsorted(a, side='left')):int(x.index.searchsorted(z, side='left'))]


def bar_at(x5: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    pos = int(x5.index.searchsorted(ts, side='left'))
    if pos >= len(x5) or x5.index[pos] != ts:
        raise AssertionError(f'missing exact raw5m bar {ts}')
    return x5.iloc[pos]


def qtile(x, q):
    s = pd.to_numeric(pd.Series(x), errors='coerce').dropna()
    return float(s.quantile(q)) if len(s) else np.nan


def pct(x):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def num(x, n=3):
    return '-' if pd.isna(x) else f'{float(x):.{n}f}'


def current_geometry(r: pd.Series, x5: pd.DataFrame) -> dict:
    cts = pd.Timestamp(r.confirmation_bar_start)
    ets = pd.Timestamp(r.entry_ts)
    cbar = bar_at(x5, cts)
    ebar = bar_at(x5, ets)
    H = float(r.H); L = float(r.L); R = float(r.R)
    entry = float(r.entry_px); f85 = float(r.entry_level); f35 = float(r.stop_level)
    if R <= 0:
        raise AssertionError(f'nonpositive R {r.candidate_id}')
    if abs(float(ebar.open) - entry) > max(1e-10, abs(entry) * 1e-10):
        raise AssertionError(f'entry open drift {r.candidate_id}: raw={ebar.open} saved={entry}')
    if float(cbar.close) <= f85:
        raise AssertionError(f'confirmation no longer closes >F85 {r.candidate_id}')
    if not (f35 < entry < H):
        raise AssertionError(f'frozen entry geometry drift {r.candidate_id}')
    return {
        'confirmation_close': float(cbar.close),
        'confirmation_close_depth_R': (float(cbar.close) - L) / R,
        'entry_depth_R': (entry - L) / R,
        'entry_premium_vs_F85_R': (entry - f85) / R,
        'confirmation_to_entry_gap_R': (entry - float(cbar.close)) / R,
        'reward_to_H_R': (H - entry) / R,
        'risk_to_F35_R': (entry - f35) / R,
        'h2_reward_risk': (H - entry) / (entry - f35) if entry > f35 else np.nan,
    }


def level_opportunity(r: pd.Series, x5: pd.DataFrame, level_pct: int) -> dict:
    entry_ts = pd.Timestamp(r.entry_ts)
    end = pd.Timestamp(r.execution_end)
    H = float(r.H); L = float(r.L); R = float(r.R)
    level = L + (float(level_pct) / 100.0) * R
    q = fs(x5, entry_ts, end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError(f'missing entry-window slice {r.candidate_id}')

    hit = q.low.astype(float) <= level
    if not bool(hit.any()):
        return {
            'level_pct': level_pct, 'level_px': level,
            'fill_state': 'NO_FILL', 'fill_ts': pd.NaT,
            'clean_fill': False, 'ambiguous_fill_h2_same_bar': False,
            'later_h2': False, 'later_h2_ts': pd.NaT,
            'minutes_fill_to_h2': np.nan,
            'reward_to_H_R_at_level': (H - level) / R,
            'post_fill_future_mae_R': np.nan,
        }

    idx = int(np.flatnonzero(hit.to_numpy())[0])
    fts = pd.Timestamp(q.index[idx])
    fbar = q.iloc[idx]
    ambiguous = float(fbar.high) >= H
    if ambiguous:
        return {
            'level_pct': level_pct, 'level_px': level,
            'fill_state': 'AMBIGUOUS_FILL_H2_SAME_BAR', 'fill_ts': fts,
            'clean_fill': False, 'ambiguous_fill_h2_same_bar': True,
            'later_h2': False, 'later_h2_ts': pd.NaT,
            'minutes_fill_to_h2': np.nan,
            'reward_to_H_R_at_level': (H - level) / R,
            'post_fill_future_mae_R': np.nan,
        }

    post_start = fts + BAR5
    post = fs(x5, post_start, end)
    later_h2 = False
    h2ts = pd.NaT
    if len(post):
        hh = post.high.astype(float) >= H
        if bool(hh.any()):
            h2ts = pd.Timestamp(post.index[int(np.flatnonzero(hh.to_numpy())[0])])
            later_h2 = True
        # Exclude the fill bar itself because intrabar order after the first level touch is unknown.
        future_low = float(post.low.min())
        mae = max(0.0, (level - future_low) / R)
    else:
        mae = 0.0

    return {
        'level_pct': level_pct, 'level_px': level,
        'fill_state': 'CLEAN_FILL', 'fill_ts': fts,
        'clean_fill': True, 'ambiguous_fill_h2_same_bar': False,
        'later_h2': bool(later_h2), 'later_h2_ts': h2ts,
        'minutes_fill_to_h2': ((h2ts - fts).total_seconds() / 60.0) if later_h2 else np.nan,
        'reward_to_H_R_at_level': (H - level) / R,
        'post_fill_future_mae_R': float(mae),
    }


def geom_metrics(q: pd.DataFrame) -> dict:
    return {
        'n': int(len(q)),
        'confirmation_close_depth_p25_R': qtile(q.confirmation_close_depth_R, .25),
        'confirmation_close_depth_median_R': qtile(q.confirmation_close_depth_R, .50),
        'confirmation_close_depth_p75_R': qtile(q.confirmation_close_depth_R, .75),
        'entry_depth_p25_R': qtile(q.entry_depth_R, .25),
        'entry_depth_median_R': qtile(q.entry_depth_R, .50),
        'entry_depth_p75_R': qtile(q.entry_depth_R, .75),
        'entry_premium_vs_F85_median_R': qtile(q.entry_premium_vs_F85_R, .50),
        'confirmation_to_entry_gap_median_R': qtile(q.confirmation_to_entry_gap_R, .50),
        'reward_to_H_median_R': qtile(q.reward_to_H_R, .50),
        'risk_to_F35_median_R': qtile(q.risk_to_F35_R, .50),
        'h2_reward_risk_median': qtile(q.h2_reward_risk, .50),
    }


def atlas_metrics(q: pd.DataFrame, denominator=106) -> dict:
    clean = q[q.clean_fill.astype(bool)]
    amb = q[q.ambiguous_fill_h2_same_bar.astype(bool)]
    no = q[q.fill_state.eq('NO_FILL')]
    return {
        'signals': int(len(q)),
        'clean_fills': int(len(clean)),
        'clean_fill_rate_106': float(len(clean) / denominator) if denominator else np.nan,
        'ambiguous_same_bar': int(len(amb)),
        'no_fill': int(len(no)),
        'later_h2': int(clean.later_h2.astype(bool).sum()) if len(clean) else 0,
        'h2_after_fill_rate': float(clean.later_h2.astype(bool).mean()) if len(clean) else np.nan,
        'median_minutes_fill_to_h2': qtile(clean.loc[clean.later_h2.astype(bool), 'minutes_fill_to_h2'], .50),
        'median_reward_to_H_R': qtile(clean.reward_to_H_R_at_level, .50),
        'median_post_fill_future_mae_R': qtile(clean.post_fill_future_mae_R, .50),
    }


def main():
    if (ROOT / 'BNB_F85_LONG_TRANSFER_M5_TWO_STAGE_ECONOMICS_B27EH_Status.txt').read_text().strip() != 'B27EH_BNB_TWO_STAGE_ECONOMICS_NOT_SUPPORTED':
        raise AssertionError('B27EH prerequisite drift')
    if (ROOT / 'BNB_F85_F15_TRANSFER_M4_PATH_DIAGNOSTICS_B27EG_Status.txt').read_text().strip() != 'B27EG_BNB_PATH_DIAGNOSTICS_COMPLETE':
        raise AssertionError('B27EG prerequisite drift')

    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB coverage below gate: {coverage:.6f}')

    d = pd.read_csv(ROOT / 'BNB_F85_F15_TRANSFER_M4_PATH_DIAGNOSTICS_B27EG_Detail.csv')
    for c in ('entry_ts', 'execution_end', 'confirmation_bar_start', 'structural_h2_ts'):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    q = d[
        d.accepted.astype(bool) & d.partition.isin(MAJOR) & d.side.eq('LONG') & d.source.isin(SOURCES)
    ].copy().sort_values('entry_ts').reset_index(drop=True)
    if len(q) != 106:
        raise AssertionError(f'expected 106 accepted pooled-major LONG, got {len(q)}')
    counts = q.source.value_counts().to_dict()
    if counts != {'ALT_0330': 55, 'RAW_0530': 51}:
        raise AssertionError(f'source identity drift: {counts}')
    if q.candidate_id.duplicated().any():
        raise AssertionError('duplicate frozen LONG candidate IDs')

    detail_rows = []
    atlas_rows = []
    for _, r in q.iterrows():
        g = current_geometry(r, x5)
        base = {k: r[k] for k in [
            'candidate_id','partition','source','entry_ts','entry_px','confirmation_bar_start',
            'H','L','R','entry_level','stop_level','economic_label','structural_outcome','structural_h2_ts'
        ]}
        detail_rows.append({**base, **g})
        for lv in LEVELS:
            atlas_rows.append({**base, **level_opportunity(r, x5, lv)})

    detail = pd.DataFrame(detail_rows)
    atlas_detail = pd.DataFrame(atlas_rows)
    detail.to_csv(OUT_DETAIL, index=False)

    geom_rows = []
    for src in ('POOLED_LONG', *SOURCES):
        z0 = detail if src == 'POOLED_LONG' else detail[detail.source.eq(src)]
        for cohort in ('ALL','WIN','LOSS','H2','NON_H2'):
            z = z0
            if cohort == 'WIN': z = z[z.economic_label.eq('WIN')]
            elif cohort == 'LOSS': z = z[z.economic_label.eq('LOSS')]
            elif cohort == 'H2': z = z[z.structural_outcome.eq('H2')]
            elif cohort == 'NON_H2': z = z[~z.structural_outcome.eq('H2')]
            geom_rows.append({'scope':src,'cohort':cohort,**geom_metrics(z)})
    geom = pd.DataFrame(geom_rows)
    geom.to_csv(OUT_GEOM, index=False)

    atlas_summary_rows = []
    candidate_levels = []
    for lv in LEVELS:
        lvq = atlas_detail[atlas_detail.level_pct.eq(lv)]
        # pooled/source/partition summaries
        for scope in ('POOLED_LONG', *SOURCES, *MAJOR):
            if scope == 'POOLED_LONG': z = lvq
            elif scope in SOURCES: z = lvq[lvq.source.eq(scope)]
            else: z = lvq[lvq.partition.eq(scope)]
            den = 106 if scope == 'POOLED_LONG' else max(1, len(z))
            atlas_summary_rows.append({'level_pct':lv,'scope':scope,**atlas_metrics(z, den)})

        pooled = atlas_metrics(lvq, 106)
        source_ok = True
        for src in SOURCES:
            sm = atlas_metrics(lvq[lvq.source.eq(src)], max(1, len(lvq[lvq.source.eq(src)])))
            if not (sm['clean_fills'] >= 10 and pd.notna(sm['h2_after_fill_rate']) and sm['h2_after_fill_rate'] >= .70):
                source_ok = False
        part_ok = True
        for p in MAJOR:
            pm = atlas_metrics(lvq[lvq.partition.eq(p)], max(1, len(lvq[lvq.partition.eq(p)])))
            if pm['clean_fills'] >= 5 and not (pd.notna(pm['h2_after_fill_rate']) and pm['h2_after_fill_rate'] >= .65):
                part_ok = False
        is_candidate = bool(
            pooled['clean_fills'] >= 30 and pooled['clean_fill_rate_106'] >= .30 and
            pd.notna(pooled['h2_after_fill_rate']) and pooled['h2_after_fill_rate'] >= .75 and
            source_ok and part_ok and pd.notna(pooled['median_reward_to_H_R']) and pooled['median_reward_to_H_R'] >= .20
        )
        if is_candidate:
            candidate_levels.append(f'F{lv}')

    atlas_summary = pd.DataFrame(atlas_summary_rows)
    atlas_summary.to_csv(OUT_ATLAS, index=False)

    pg = geom[(geom.scope.eq('POOLED_LONG'))]
    allg = pg[pg.cohort.eq('ALL')].iloc[0]
    wing = pg[pg.cohort.eq('WIN')].iloc[0]
    losg = pg[pg.cohort.eq('LOSS')].iloc[0]

    lines = [
        '# BNB F85 LONG Transfer — M6 Entry Depth Diagnostics — B27EI Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. Frozen accepted LONG identity: **PASS (106 = 55 ALT_0330 + 51 RAW_0530)**.','',
        'B27EI is diagnostic only: no alternative-entry PnL, no stop change, no candidate filtering, and no level selection by economics.','',
        '## Current F85 next-open geometry','',
        '| Cohort | N | Confirm close depth med | Entry depth med | Premium vs F85 med | Reward→H med | Risk→F35 med | H2 reward/risk med |',
        '|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for label, r in [('ALL',allg),('WIN',wing),('LOSS',losg)]:
        lines.append(
            f'| {label} | {int(r.n)} | {num(r.confirmation_close_depth_median_R)}R | {num(r.entry_depth_median_R)}R | '
            f'{num(r.entry_premium_vs_F85_median_R)}R | {num(r.reward_to_H_median_R)}R | {num(r.risk_to_F35_median_R)}R | {num(r.h2_reward_risk_median)} |'
        )

    lines += ['', '## Deeper-entry causal opportunity atlas','',
              '| Level | Clean fills | Fill rate | Ambiguous same-bar | No fill | H2 after clean fill | Median fill→H2 | Reward→H | Future MAE | Diagnostic label |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for lv in LEVELS:
        r = atlas_summary[(atlas_summary.level_pct.eq(lv)) & atlas_summary.scope.eq('POOLED_LONG')].iloc[0]
        label = 'ENTRY_DEPTH_CANDIDATE' if f'F{lv}' in candidate_levels else '-'
        lines.append(
            f'| F{lv} | {int(r.clean_fills)} | {pct(r.clean_fill_rate_106)} | {int(r.ambiguous_same_bar)} | {int(r.no_fill)} | '
            f'{pct(r.h2_after_fill_rate)} | {num(r.median_minutes_fill_to_h2,1)}m | {num(r.median_reward_to_H_R)}R | '
            f'{num(r.median_post_fill_future_mae_R)}R | {label} |'
        )

    lines += ['', '## Source stability for deeper fills','',
              '| Level | Source | Clean fills | H2 after fill | Reward→H | Future MAE |',
              '|---|---|---:|---:|---:|---:|']
    for lv in LEVELS:
        for src in SOURCES:
            r = atlas_summary[(atlas_summary.level_pct.eq(lv)) & atlas_summary.scope.eq(src)].iloc[0]
            lines.append(f'| F{lv} | {src} | {int(r.clean_fills)} | {pct(r.h2_after_fill_rate)} | {num(r.median_reward_to_H_R)}R | {num(r.median_post_fill_future_mae_R)}R |')

    if candidate_levels:
        interpretation = f'Diagnostic deeper-entry candidates satisfying all frozen non-economic gates: **{", ".join(candidate_levels)}**. This does not select a strategy; a separate preregistered economic test is required.'
    else:
        interpretation = 'No deeper level satisfies the frozen diagnostic gate. Entry depth alone is not yet supported as the next strategy change.'
    lines += ['', '## Interpretation','', interpretation,'',
              '**Status: B27EI_BNB_ENTRY_DEPTH_DIAGNOSTICS_COMPLETE**','',
              'B27EI stops here. No alternative-entry economics or strategy selection is run automatically.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('B27EI_BNB_ENTRY_DEPTH_DIAGNOSTICS_COMPLETE\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
