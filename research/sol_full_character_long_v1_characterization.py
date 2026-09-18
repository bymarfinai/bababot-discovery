#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_FULL_CHARACTER_LONG_V1_CHARACTERIZATION'
TRIGGER = 'DEMAND_SWEEP_RECLAIM'
EXPECTED_N = 109
YEARS = (2020, 2021, 2022, 2023, 2024)

FEATURES = [
    'impulse_bars',
    'impulse_displacement_pct',
    'impulse_displacement_range_units',
    'impulse_efficiency',
    'return_delay_h',
    'demand_zone_width_pct',
    'return_touch_depth_in_zone_units',
    'return_close_position_in_zone_units',
    'minutes_after_structure',
    'sweep_depth_pct_below_demand_low',
    'sweep_depth_in_zone_units',
    'reclaim_close_above_demand_low_in_zone_units',
    'reclaim_body_pct',
    'reclaim_range_pct',
    'reclaim_close_location',
    'reclaim_lower_wick_fraction',
    'entry_gap_from_trigger_close_pct',
    'entry_position_in_zone_units',
]


def enrich_exact_sample(structures: pd.DataFrame, trades: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    h1 = fc1.build_h1(x5)
    smap = structures.set_index('structure_id')
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    rows = []

    for _, t in trades.iterrows():
        sid = t.structure_id
        if sid not in smap.index:
            raise RuntimeError('trade structure_id missing from frozen structures: ' + str(sid))
        s = smap.loc[sid]
        sig_time = pd.Timestamp(t.signal_time)
        pos = int(idx.searchsorted(sig_time))
        if pos >= len(idx) or idx[pos] != sig_time:
            raise RuntimeError('signal_time not found in 5m index: ' + str(sig_time))
        entry_pos = pos + 1
        ri = int(s.return_i_h1)
        if ri < 0 or ri >= len(h1):
            raise RuntimeError('return_i_h1 out of range')

        dlow = float(s.demand_low)
        dtop = float(s.demand_top)
        zone_w = dtop - dlow
        if zone_w <= 0:
            raise RuntimeError('non-positive demand zone width')

        ret_low = float(h1.low.iloc[ri])
        ret_close = float(h1.close.iloc[ri])
        trig_open = float(op[pos])
        trig_high = float(hi[pos])
        trig_low = float(lo[pos])
        trig_close = float(cl[pos])
        trig_range = trig_high - trig_low
        entry_open = float(op[entry_pos])

        rec = t.to_dict()
        rec.update({
            'demand_zone_width_pct': zone_w / dlow * 100.0,
            'return_touch_depth_in_zone_units': (dtop - ret_low) / zone_w,
            'return_close_position_in_zone_units': (ret_close - dlow) / zone_w,
            'sweep_depth_pct_below_demand_low': (dlow - trig_low) / dlow * 100.0,
            'sweep_depth_in_zone_units': (dlow - trig_low) / zone_w,
            'reclaim_close_above_demand_low_in_zone_units': (trig_close - dlow) / zone_w,
            'reclaim_body_pct': (trig_close - trig_open) / trig_open * 100.0,
            'reclaim_range_pct': trig_range / trig_open * 100.0,
            'reclaim_close_location': (trig_close - trig_low) / trig_range if trig_range > 0 else np.nan,
            'reclaim_lower_wick_fraction': (min(trig_open, trig_close) - trig_low) / trig_range if trig_range > 0 else np.nan,
            'entry_gap_from_trigger_close_pct': (entry_open / trig_close - 1.0) * 100.0,
            'entry_position_in_zone_units': (entry_open - dlow) / zone_w,
            'return_bar_low': ret_low,
            'return_bar_close': ret_close,
            'trigger_open': trig_open,
            'trigger_high': trig_high,
            'trigger_low': trig_low,
            'trigger_close': trig_close,
        })
        rows.append(rec)

    out = pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)
    if len(out) != EXPECTED_N:
        raise RuntimeError(f'frozen sample mismatch: expected {EXPECTED_N}, got {len(out)}')
    return out


def profile_group(g: pd.DataFrame, label: str) -> list[dict]:
    rows = []
    for f in FEATURES:
        a = pd.to_numeric(g[f], errors='coerce').dropna()
        rows.append({
            'group': label,
            'feature': f,
            'n': int(len(a)),
            'median': float(a.median()) if len(a) else np.nan,
            'mean': float(a.mean()) if len(a) else np.nan,
            'q25': float(a.quantile(.25)) if len(a) else np.nan,
            'q75': float(a.quantile(.75)) if len(a) else np.nan,
        })
    return rows


def winner_loser_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rows.extend(profile_group(df[df.win60 == 1], 'WIN'))
    rows.extend(profile_group(df[df.win60 == 0], 'LOSS'))
    return pd.DataFrame(rows)


def yearly_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in YEARS:
        g = df[df.year == y].copy()
        e = lib.econ(g)
        rec = {
            'year': y, 'n': e['n'], 'wr60': e['wr'],
            'expectancy60_pct': e['expectancy_pct'], 'pf60': e['pf'],
            'pnl60_usd': e['pnl_usd'], 'max_dd_usd': e['max_dd_usd'],
            'max_loss_streak': e['max_loss_streak'],
            'median_mfe60_pct': float(g.mfe60_pct.median()) if len(g) else np.nan,
            'median_mae60_pct': float(g.mae60_pct.median()) if len(g) else np.nan,
            'median_mfe_mae_ratio': float(g.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median()) if len(g) else np.nan,
            'median_time_to_mfe_min': float(g.time_to_mfe_min.median()) if len(g) else np.nan,
            'median_time_to_mae_min': float(g.time_to_mae_min.median()) if len(g) else np.nan,
        }
        for f in FEATURES:
            rec['median_' + f] = float(pd.to_numeric(g[f], errors='coerce').median()) if len(g) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def feature_association(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    wins = df[df.win60 == 1]
    losses = df[df.win60 == 0]
    for f in FEATURES:
        pair = df[[f, 'net60_pct']].replace([np.inf,-np.inf],np.nan).dropna()
        rho, p = spearmanr(pair[f], pair.net60_pct) if len(pair) >= 3 else (np.nan, np.nan)
        allv = pd.to_numeric(df[f], errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
        iqr = float(allv.quantile(.75) - allv.quantile(.25)) if len(allv) else np.nan
        wmed = float(pd.to_numeric(wins[f], errors='coerce').replace([np.inf,-np.inf],np.nan).median()) if len(wins) else np.nan
        lmed = float(pd.to_numeric(losses[f], errors='coerce').replace([np.inf,-np.inf],np.nan).median()) if len(losses) else np.nan
        sep = (wmed - lmed) / iqr if np.isfinite(iqr) and iqr > 0 else np.nan
        rows.append({
            'feature': f, 'n': int(len(pair)), 'spearman_rho_vs_net60': float(rho),
            'spearman_p_descriptive': float(p), 'winner_median': wmed,
            'loser_median': lmed, 'pooled_iqr': iqr,
            'winner_minus_loser_median_over_iqr': sep,
            'abs_spearman': abs(float(rho)) if np.isfinite(rho) else np.nan,
        })
    return pd.DataFrame(rows).sort_values(['abs_spearman','feature'], ascending=[False,True]).reset_index(drop=True)


def compare_2022(df: pd.DataFrame) -> pd.DataFrame:
    bad = df[df.year == 2022].copy()
    good = df[df.year.isin([2021, 2023, 2024])].copy()
    rows = []
    for f in FEATURES:
        a = pd.to_numeric(bad[f], errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
        b = pd.to_numeric(good[f], errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
        pooled = pd.concat([a,b], ignore_index=True)
        iqr = float(pooled.quantile(.75)-pooled.quantile(.25)) if len(pooled) else np.nan
        am = float(a.median()) if len(a) else np.nan
        bm = float(b.median()) if len(b) else np.nan
        rows.append({
            'feature':f, 'n_2022':len(a), 'median_2022':am,
            'n_positive_years':len(b), 'median_2021_2023_2024':bm,
            'pooled_iqr':iqr,
            'median_2022_minus_positive_years_over_iqr':(am-bm)/iqr if np.isfinite(iqr) and iqr>0 else np.nan,
        })
    return pd.DataFrame(rows)


def fmt(v, d=3):
    return 'n/a' if not np.isfinite(v) else f'{float(v):.{d}f}'


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5('SOLUSDT')
    if coverage < .995:
        raise RuntimeError(f'coverage too low: {coverage:.6%}')
    structures = fc1.detect_full_character(x5)
    all_trades, _ = fc1.apply_triggers(structures, x5)
    detector = 'IMPULSE_NEW_HIGH_DEMAND_PULLBACK__' + TRIGGER
    exact = all_trades[all_trades.structure == detector].copy()
    df = enrich_exact_sample(structures, exact, x5)

    wl = winner_loser_profile(df)
    yp = yearly_profile(df)
    assoc = feature_association(df)
    comp22 = compare_2022(df)

    df.to_csv(ROOT/f'{PFX}_EnrichedTrades.csv', index=False)
    wl.to_csv(ROOT/f'{PFX}_WinnerLoserProfile.csv', index=False)
    yp.to_csv(ROOT/f'{PFX}_YearProfile.csv', index=False)
    assoc.to_csv(ROOT/f'{PFX}_FeatureAssociation.csv', index=False)
    comp22.to_csv(ROOT/f'{PFX}_2022Comparison.csv', index=False)

    e = lib.econ(df)
    lines = [
        '# SOL Full-Character Long V1 — Characterization Result','',
        f'- Data coverage: **{coverage*100:.6f}%**',
        f'- Exact frozen trades characterized: **{len(df)}**',
        f'- Frozen economics reproduced: WR **{e["wr"]*100:.2f}%**, expectancy **{e["expectancy_pct"]:.4f}%**, PF **{lib.pfmt(e["pf"])}**, PnL **${e["pnl_usd"]:.2f}**.',
        '- No structure, trigger, entry, trade, threshold, or exit was changed.',
        '- 2025+ remained CLOSED.','',
        '## Winner vs loser medians','',
        '| Feature | Winner median | Loser median | Separation / pooled IQR | Spearman vs net60 |',
        '|---|---:|---:|---:|---:|',
    ]
    for _, r in assoc.iterrows():
        lines.append(f'| {r.feature} | {fmt(r.winner_median)} | {fmt(r.loser_median)} | {fmt(r.winner_minus_loser_median_over_iqr)} | {fmt(r.spearman_rho_vs_net60)} |')

    lines += ['', '## Year economics + path','',
        '| Year | N | WR60 | Exp60 | PF | MFE | MAE | MFE/MAE | tMFE | tMAE |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _, r in yp.iterrows():
        lines.append(f'| {int(r.year)} | {int(r.n)} | {r.wr60*100 if np.isfinite(r.wr60) else np.nan:.2f}% | {r.expectancy60_pct if np.isfinite(r.expectancy60_pct) else np.nan:.4f}% | {lib.pfmt(r.pf60)} | {fmt(r.median_mfe60_pct)}% | {fmt(r.median_mae60_pct)}% | {fmt(r.median_mfe_mae_ratio)} | {fmt(r.median_time_to_mfe_min,1)}m | {fmt(r.median_time_to_mae_min,1)}m |')

    lines += ['', '## 2022 versus 2021+2023+2024 pre-entry character','',
        '| Feature | 2022 median | Positive-years median | Difference / pooled IQR |',
        '|---|---:|---:|---:|']
    comp_sorted = comp22.copy()
    comp_sorted['abs_sep'] = comp_sorted.median_2022_minus_positive_years_over_iqr.abs()
    comp_sorted = comp_sorted.sort_values(['abs_sep','feature'], ascending=[False,True])
    for _, r in comp_sorted.iterrows():
        lines.append(f'| {r.feature} | {fmt(r.median_2022)} | {fmt(r.median_2021_2023_2024)} | {fmt(r.median_2022_minus_positive_years_over_iqr)} |')

    lines += ['', '## Interpretation','',
        '- This is descriptive characterization only; no threshold or filter is selected from these 109 trades.',
        '- Large winner/loser or 2022/non-2022 separations are hypothesis generators only.',
        '- Any next detector must preregister one market-logic rule before observing its result.',
        '', 'OFFICIAL_STATUS=CHARACTERIZATION_COMPLETE_NO_FILTER_SELECTED']

    text = '\n'.join(lines) + '\n'
    (ROOT/f'{PFX}_Result.md').write_text(text, encoding='utf-8')
    (ROOT/f'{PFX}_Status.txt').write_text('OFFICIAL_STATUS=CHARACTERIZATION_COMPLETE_NO_FILTER_SELECTED\nN=109\n2025_PLUS=CLOSED\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()