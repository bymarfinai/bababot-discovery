#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_full_character_long_v1_characterization as ch
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_FULL_CHARACTER_LONG_V1_MEANINGFUL_SWEEP'
BASE_N = 109
SWEEP_DEPTH_ZONE_MIN = 0.25
LOWER_WICK_FRAC_MIN = 0.50
YEARS = (2020, 2021, 2022, 2023, 2024)


def econ_row(g: pd.DataFrame) -> dict:
    e = lib.econ(g)
    ratio = float(g.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median()) if len(g) else np.nan
    return {
        'n': e['n'], 'wr60': e['wr'], 'expectancy60_pct': e['expectancy_pct'],
        'pf60': e['pf'], 'pnl60_usd': e['pnl_usd'], 'max_dd_usd': e['max_dd_usd'],
        'max_loss_streak': e['max_loss_streak'],
        'clean_up_impulse_rate': float(g.clean_up_impulse.mean()) if len(g) else np.nan,
        'median_mfe60_pct': float(g.mfe60_pct.median()) if len(g) else np.nan,
        'median_mae60_pct': float(g.mae60_pct.median()) if len(g) else np.nan,
        'median_mfe_mae_ratio': ratio,
        'median_time_to_mfe_min': float(g.time_to_mfe_min.median()) if len(g) else np.nan,
        'median_time_to_mae_min': float(g.time_to_mae_min.median()) if len(g) else np.nan,
    }


def yearly(g: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for y in YEARS:
        gy = g[g.year == y].copy()
        r = econ_row(gy)
        rows.append({'group':label,'year':y,**r})
    return pd.DataFrame(rows)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5('SOLUSDT')
    if coverage < .995:
        raise RuntimeError(f'coverage too low: {coverage:.6%}')

    structures = fc1.detect_full_character(x5)
    all_trades, _ = fc1.apply_triggers(structures, x5)
    detector = 'IMPULSE_NEW_HIGH_DEMAND_PULLBACK__DEMAND_SWEEP_RECLAIM'
    base = all_trades[all_trades.structure == detector].copy()
    enriched = ch.enrich_exact_sample(structures, base, x5)
    if len(enriched) != BASE_N:
        raise RuntimeError(f'base sample mismatch: expected {BASE_N}, got {len(enriched)}')

    mask = (
        (enriched.sweep_depth_in_zone_units >= SWEEP_DEPTH_ZONE_MIN)
        & (enriched.reclaim_lower_wick_fraction >= LOWER_WICK_FRAC_MIN)
    )
    selected = enriched[mask].copy().reset_index(drop=True)
    complement = enriched[~mask].copy().reset_index(drop=True)
    if selected.empty:
        raise RuntimeError('meaningful-sweep rule selected zero trades')

    base_e = econ_row(enriched)
    sel_e = econ_row(selected)
    comp_e = econ_row(complement)
    sel_year = yearly(selected, 'SELECTED')
    comp_year = yearly(complement, 'COMPLEMENT')
    year_all = pd.concat([sel_year, comp_year], ignore_index=True)
    pos_years = int((sel_year.pnl60_usd > 0).sum())

    gates = {
        'n_ge_100': int(sel_e['n']) >= 100,
        'expectancy_positive': bool(np.isfinite(sel_e['expectancy60_pct']) and sel_e['expectancy60_pct'] > 0),
        'pf_ge_1_15': bool(np.isfinite(sel_e['pf60']) and sel_e['pf60'] >= 1.15),
        'positive_pnl_years_ge_4_of_5': pos_years >= 4,
        'median_mfe_mae_ge_1_20': bool(np.isfinite(sel_e['median_mfe_mae_ratio']) and sel_e['median_mfe_mae_ratio'] >= 1.20),
    }
    verdict = 'PASS_DEVELOPMENT_CONFIRMATION' if all(gates.values()) else 'REJECTED_AS_DEFINED'

    summary = pd.DataFrame([{
        'base_n': len(enriched),
        'selected_n': len(selected),
        'retention_rate': len(selected)/len(enriched),
        **{'base_'+k:v for k,v in base_e.items()},
        **{'selected_'+k:v for k,v in sel_e.items()},
        **{'complement_'+k:v for k,v in comp_e.items()},
        'positive_pnl_years': pos_years,
        **{'gate_'+k:v for k,v in gates.items()},
        'verdict': verdict,
    }])

    selected.to_csv(ROOT/f'{PFX}_SelectedTrades.csv', index=False)
    complement.to_csv(ROOT/f'{PFX}_ComplementTrades.csv', index=False)
    summary.to_csv(ROOT/f'{PFX}_Summary.csv', index=False)
    year_all.to_csv(ROOT/f'{PFX}_YearSummary.csv', index=False)

    def pf(v):
        return lib.pfmt(v)
    def pct(v):
        return 'n/a' if not np.isfinite(v) else f'{v:.4f}%'

    lines = [
        '# SOL Full-Character Long V1 — Meaningful Sweep Confirmation Result','',
        f'- Data coverage: **{coverage*100:.6f}%**',
        f'- Base V1 sweep/reclaim trades reproduced: **{len(enriched)}**',
        f'- Exact rule: sweep depth >= **{SWEEP_DEPTH_ZONE_MIN:.2f}x** demand-zone width AND reclaim lower wick >= **{LOWER_WICK_FRAC_MIN:.2f}** of candle range.',
        f'- Selected trades: **{len(selected)}** ({len(selected)/len(enriched)*100:.2f}% retention).',
        '- 2020-2024 is development confirmation because the rule was motivated by prior characterization.',
        '- 2025+ remained CLOSED.','',
        '## Pooled economics','',
        '| Group | N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | MFE/MAE |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        f"| Base V1 | {int(base_e['n'])} | {base_e['wr60']*100:.2f}% | {base_e['expectancy60_pct']:.4f}% | {pf(base_e['pf60'])} | ${base_e['pnl60_usd']:.2f} | ${base_e['max_dd_usd']:.2f} | {int(base_e['max_loss_streak'])} | {base_e['clean_up_impulse_rate']*100:.2f}% | {base_e['median_mfe_mae_ratio']:.3f} |",
        f"| Meaningful sweep | {int(sel_e['n'])} | {sel_e['wr60']*100:.2f}% | {sel_e['expectancy60_pct']:.4f}% | {pf(sel_e['pf60'])} | ${sel_e['pnl60_usd']:.2f} | ${sel_e['max_dd_usd']:.2f} | {int(sel_e['max_loss_streak'])} | {sel_e['clean_up_impulse_rate']*100:.2f}% | {sel_e['median_mfe_mae_ratio']:.3f} |",
        f"| Complement | {int(comp_e['n'])} | {comp_e['wr60']*100:.2f}% | {comp_e['expectancy60_pct']:.4f}% | {pf(comp_e['pf60'])} | ${comp_e['pnl60_usd']:.2f} | ${comp_e['max_dd_usd']:.2f} | {int(comp_e['max_loss_streak'])} | {comp_e['clean_up_impulse_rate']*100:.2f}% | {comp_e['median_mfe_mae_ratio']:.3f} |",
        '', '## Selected yearly economics','',
        '| Year | N | WR60 | Exp60 | PF | PnL | MFE/MAE |',
        '|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in sel_year.iterrows():
        wr = r.wr60*100 if np.isfinite(r.wr60) else np.nan
        lines.append(f"| {int(r.year)} | {int(r.n)} | {wr:.2f}% | {pct(r.expectancy60_pct)} | {pf(r.pf60)} | ${r.pnl60_usd:.2f} | {r.median_mfe_mae_ratio if np.isfinite(r.median_mfe_mae_ratio) else np.nan:.3f} |")

    lines += ['', '## Frozen gate audit','']
    for k,v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
    lines += [
        '', f'OFFICIAL_VERDICT={verdict}',
        'VALIDATION_STATUS=DEVELOPMENT_CONFIRMATION_ONLY',
        '2025_PLUS=CLOSED',
    ]

    text = '\n'.join(lines) + '\n'
    (ROOT/f'{PFX}_Result.md').write_text(text, encoding='utf-8')
    (ROOT/f'{PFX}_Status.txt').write_text(
        f'OFFICIAL_VERDICT={verdict}\nVALIDATION_STATUS=DEVELOPMENT_CONFIRMATION_ONLY\nSELECTED_N={len(selected)}\n2025_PLUS=CLOSED\n',
        encoding='utf-8'
    )
    print(text)


if __name__ == '__main__':
    main()