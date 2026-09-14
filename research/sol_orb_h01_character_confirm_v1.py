#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_orb_reference_fidelity_v1 as detector
import run_sol_orb_reference_fidelity_v1_fixed as fixed
import sol_orb_h01_character_discovery_v1 as disc

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_ORB_H01_CHARACTER_CONFIRM_V1'
START = pd.Timestamp('2020-01-01', tz='UTC')
END = pd.Timestamp('2022-01-01', tz='UTC')
HOUR_UTC = 18


def collect_external(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= START) & (x5.index < END)]
    days = pd.Index(q.index.normalize().unique()).sort_values()
    rows = []
    for day in days:
        if day.weekday() >= 5:
            continue
        st = day + pd.Timedelta(hours=HOUR_UTC)
        d = detector.detect_session(x5, st)
        if d is None:
            continue
        bt = d.get('bos_time')
        br = detector.row_at(x5, bt) if pd.notna(bt) else None
        bos_close = float(br.close) if br is not None else np.nan
        d['bos_close'] = bos_close
        d['bos_close_disp_pct'] = (bos_close / float(d['orb_high']) - 1.0) * 100.0 if np.isfinite(bos_close) else np.nan
        rows.append(d)
    return pd.DataFrame(rows)


def main():
    detector.base.fetch_one = fixed.fetch_one_with_volume
    x5, coverage = detector.base.load5('SOLUSDT')
    if 'volume' not in x5.columns:
        raise RuntimeError('volume column required for anchored VWAP')

    ev = collect_external(x5)
    cand = ev[disc.candidate_mask(ev, disc.ORB_MAX, disc.BOS_DISP_MIN)].copy()
    cand.to_csv(ROOT / f'{PFX}_Trades.csv', index=False)
    ev.to_csv(ROOT / f'{PFX}_Audit.csv', index=False)

    pooled = disc.summarize(cand)
    year_rows = []
    for y in (2020, 2021):
        s = disc.summarize(cand[cand.year == y])
        year_rows.append({'year': y, **s})
    years = pd.DataFrame(year_rows)
    years.to_csv(ROOT / f'{PFX}_YearSummary.csv', index=False)

    passed = bool(
        pooled['n'] >= 5
        and pooled['net_wr'] >= 0.60
        and pooled['profit_factor'] > 1.0
        and pooled['net_pnl_usd'] > 0
    )

    pf = 'inf' if math.isinf(pooled['profit_factor']) else f"{pooled['profit_factor']:.3f}"
    lines = [
        '# SOL ORB H01 Character Confirmation v1 — External 2020-2021', '',
        f'- Data coverage loader: {coverage*100:.6f}%',
        '- Frozen rule: 01:00 WIB / 18:00 UTC; ORB <=1.00%; SMALL_BOS_VWAP; BOS close displacement >=0.60%; next-open entry; +60m exit.',
        '- No parameter changed from the development lock.',
        '- 2025+ reference validation remains closed.', '',
        '## External pooled result', '',
        '| N | WR | Net PnL | Exp | PF | Max DD | Max LS |',
        '|---:|---:|---:|---:|---:|---:|---:|',
        f"| {pooled['n']} | {pooled['net_wr']*100:.2f}% | ${pooled['net_pnl_usd']:.2f} | ${pooled['expectancy_usd']:.2f} | {pf} | ${pooled['max_dd_usd']:.2f} | {pooled['max_loss_streak']} |", '',
        '## Year detail', '',
        '| Year | N | WR | PnL | PF |',
        '|---:|---:|---:|---:|---:|',
    ]
    for _, r in years.iterrows():
        if int(r.n) == 0:
            lines.append(f"| {int(r.year)} | 0 | n/a | $0.00 | n/a |")
        else:
            ypf = 'inf' if math.isinf(r.profit_factor) else f'{r.profit_factor:.3f}'
            lines.append(f"| {int(r.year)} | {int(r.n)} | {r.net_wr*100:.2f}% | ${r.net_pnl_usd:.2f} | {ypf} |")
    lines += ['', f"## Verdict: **{'PASS' if passed else 'FAIL'}**", '',
              'If FAIL, do not retune this H01 rule against the external confirmation set.']
    (ROOT / f'{PFX}_Result.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (ROOT / f'{PFX}_Status.txt').write_text(('PASS' if passed else 'FAIL') + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
