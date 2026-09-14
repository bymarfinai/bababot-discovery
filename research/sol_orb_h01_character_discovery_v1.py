#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_orb_reference_fidelity_v1 as detector
import run_sol_orb_reference_fidelity_v1_fixed as fixed

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_ORB_H01_CHARACTER_DISCOVERY_V1'
HOUR_UTC = 18
ORB_MAX = 1.00
BOS_DISP_MIN = 0.60
EXIT_MIN = 60


def profit_factor(p):
    a = pd.Series(p, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def summarize(g: pd.DataFrame) -> dict:
    ret = 'SMALL_BOS_VWAP_net_60m_pct'
    pnl = 'SMALL_BOS_VWAP_pnl_60m_usd'
    q = g.dropna(subset=[ret, pnl]).sort_values('SMALL_BOS_VWAP_entry_time')
    p = q[pnl].astype(float)
    return {
        'n': int(len(q)),
        'net_wr': float((q[ret] > 0).mean()) if len(q) else np.nan,
        'net_pnl_usd': float(p.sum()) if len(q) else np.nan,
        'expectancy_usd': float(p.mean()) if len(q) else np.nan,
        'profit_factor': profit_factor(p),
        'max_dd_usd': detector.max_drawdown(p),
        'max_loss_streak': detector.max_loss_streak(p),
    }


def collect_h01(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= detector.DEV_START) & (x5.index < detector.DEV_END)]
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


def candidate_mask(ev: pd.DataFrame, orb_max=ORB_MAX, disp_min=BOS_DISP_MIN):
    return (
        ev['SMALL_BOS_VWAP_entry_time'].notna()
        & (ev['orb_range_pct'] <= orb_max)
        & (ev['bos_close_disp_pct'] >= disp_min)
    )


def main():
    detector.base.fetch_one = fixed.fetch_one_with_volume
    x5, coverage = detector.base.load5('SOLUSDT')
    if coverage < .995:
        raise RuntimeError(f'coverage too low: {coverage:.6%}')
    if 'volume' not in x5.columns:
        raise RuntimeError('volume column required for anchored VWAP')

    ev = collect_h01(x5)
    cand = ev[candidate_mask(ev)].copy()
    cand.to_csv(ROOT / f'{PFX}_Trades.csv', index=False)

    pooled = summarize(cand)
    year_rows = []
    for y in (2022, 2023, 2024):
        s = summarize(cand[cand.year == y])
        year_rows.append({'year': y, **s})
    years = pd.DataFrame(year_rows)
    years.to_csv(ROOT / f'{PFX}_YearSummary.csv', index=False)

    sens_rows = []
    for om in (0.90, 1.00, 1.10):
        for dm in (0.50, 0.60, 0.70):
            q = ev[candidate_mask(ev, om, dm)]
            s = summarize(q)
            sens_rows.append({'orb_max_pct': om, 'bos_disp_min_pct': dm, **s})
    sens = pd.DataFrame(sens_rows)
    sens.to_csv(ROOT / f'{PFX}_Sensitivity.csv', index=False)

    years_ok = bool(
        (years['n'] > 0).all()
        and (years['net_wr'] >= 0.60).all()
    )
    promote = bool(
        pooled['n'] > 0
        and pooled['net_wr'] >= 0.60
        and pooled['profit_factor'] > 1.0
        and pooled['net_pnl_usd'] > 0
        and years_ok
    )

    lines = [
        '# SOL ORB H01 Character Discovery v1 — Development', '',
        f'- Data coverage: {coverage*100:.6f}%',
        '- Session: 18:00 UTC = 01:00 WIB.',
        '- Development only: 2022-2024 weekdays.',
        '- Reference/OOS remains closed.',
        '- Frozen candidate: ORB range <= 1.00%; SMALL_BOS_VWAP; BOS close >= +0.60% above ORB High; next-5m-open LONG; fixed +60m exit.', '',
        '## Frozen candidate', '',
        '| N | WR | Net PnL | Exp | PF | Max DD | Max LS |',
        '|---:|---:|---:|---:|---:|---:|---:|',
        f"| {pooled['n']} | {pooled['net_wr']*100:.2f}% | ${pooled['net_pnl_usd']:.2f} | ${pooled['expectancy_usd']:.2f} | {pooled['profit_factor']:.3f} | ${pooled['max_dd_usd']:.2f} | {pooled['max_loss_streak']} |", '',
        '## Year stability', '',
        '| Year | N | WR | PnL | PF |',
        '|---:|---:|---:|---:|---:|',
    ]
    for _, r in years.iterrows():
        pf = 'inf' if math.isinf(r.profit_factor) else f'{r.profit_factor:.3f}'
        lines.append(f"| {int(r.year)} | {int(r.n)} | {r.net_wr*100:.2f}% | ${r.net_pnl_usd:.2f} | {pf} |")
    lines += ['', '## Neighbor robustness (descriptive only)', '',
              '| ORB max | BOS disp min | N | WR | PnL | PF |',
              '|---:|---:|---:|---:|---:|---:|']
    for _, r in sens.iterrows():
        pf = 'inf' if math.isinf(r.profit_factor) else f'{r.profit_factor:.3f}'
        lines.append(f"| {r.orb_max_pct:.2f}% | {r.bos_disp_min_pct:.2f}% | {int(r.n)} | {r.net_wr*100:.2f}% | ${r.net_pnl_usd:.2f} | {pf} |")
    lines += ['', f"## Decision: **{'PROMOTE_TO_CONFIRMATION' if promote else 'REJECT_H01_DISCOVERY'}**", '',
              'No threshold may be changed after this decision using confirmation data.']
    (ROOT / f'{PFX}_Result.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (ROOT / f'{PFX}_Status.txt').write_text(('PROMOTE_TO_CONFIRMATION' if promote else 'REJECT_H01_DISCOVERY') + '\n', encoding='utf-8')
    ev.to_csv(ROOT / f'{PFX}_Audit.csv', index=False)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
