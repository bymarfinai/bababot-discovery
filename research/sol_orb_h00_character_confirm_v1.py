#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_orb_reference_fidelity_v1 as detector
import run_sol_orb_reference_fidelity_v1_fixed as fixed

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_ORB_H00_CHARACTER_CONFIRM_V1'
START, END = detector.base.PARTS['external']
HOUR_UTC = 17  # 00:00 WIB
ORB_MIN_PCT = 0.50
ACCEPT_MIN_PCT = 0.50
EXIT_MIN = 60
VARIANT = 'REACTION_THEN_BOS_VWAP'


def collect_external(x5: pd.DataFrame) -> pd.DataFrame:
    q = x5[(x5.index >= START) & (x5.index < END)]
    days = pd.Index(q.index.normalize().unique()).sort_values()
    rows = []
    for day in days:
        if day.weekday() >= 5:
            continue
        start = day + pd.Timedelta(hours=HOUR_UTC)
        d = detector.detect_session(x5, start)
        if d is None:
            continue
        d = dict(d)
        bos_ts = d.get('bos_time', pd.NaT)
        bos_close = np.nan
        acceptance_pct = np.nan
        if pd.notna(bos_ts):
            br = detector.row_at(x5, pd.Timestamp(bos_ts))
            if br is not None:
                bos_close = float(br.close)
                acceptance_pct = (bos_close / float(d['orb_high']) - 1.0) * 100.0
        d['bos_close'] = bos_close
        d['acceptance_pct'] = acceptance_pct
        d['frozen_orb_pass'] = bool(float(d['orb_range_pct']) >= ORB_MIN_PCT)
        d['frozen_accept_pass'] = bool(np.isfinite(acceptance_pct) and acceptance_pct >= ACCEPT_MIN_PCT)
        d['frozen_character_pass'] = bool(
            pd.notna(d.get(f'{VARIANT}_entry_time'))
            and d['frozen_orb_pass']
            and d['frozen_accept_pass']
        )
        rows.append(d)
    return pd.DataFrame(rows)


def stats(g: pd.DataFrame) -> dict:
    pnl_col = f'{VARIANT}_pnl_{EXIT_MIN}m_usd'
    ret_col = f'{VARIANT}_net_{EXIT_MIN}m_pct'
    q = g[g['frozen_character_pass']].dropna(subset=[pnl_col, ret_col]).sort_values(f'{VARIANT}_entry_time')
    p = q[pnl_col].astype(float)
    n = len(q)
    return {
        'n': n,
        'net_wr': float((q[ret_col].astype(float) > 0).mean()) if n else np.nan,
        'net_pnl_usd': float(p.sum()) if n else np.nan,
        'expectancy_usd': float(p.mean()) if n else np.nan,
        'profit_factor': detector.profit_factor(p),
        'max_dd_usd': detector.max_drawdown(p),
        'max_loss_streak': detector.max_loss_streak(p),
    }


def main():
    # Preserve exact detector logic; only patch the loader so anchored VWAP receives volume.
    detector.base.fetch_one = fixed.fetch_one_with_volume
    x5, coverage = detector.base.load5('SOLUSDT')
    if coverage < .995:
        raise RuntimeError(f'coverage too low: {coverage:.6%}')
    if 'volume' not in x5.columns:
        raise RuntimeError('volume column required for VWAP')

    ev = collect_external(x5)
    trades = ev[ev['frozen_character_pass']].copy()
    pnl_col = f'{VARIANT}_pnl_{EXIT_MIN}m_usd'
    ret_col = f'{VARIANT}_net_{EXIT_MIN}m_pct'
    trades = trades.dropna(subset=[pnl_col, ret_col]).sort_values(f'{VARIANT}_entry_time')

    overall = stats(ev)
    yr_rows = []
    for year in (2020, 2021):
        s = stats(ev[ev['year'] == year])
        s['year'] = year
        yr_rows.append(s)
    yrs = pd.DataFrame(yr_rows)[['year','n','net_wr','net_pnl_usd','expectancy_usd','profit_factor','max_dd_usd','max_loss_streak']]

    n = int(overall['n'])
    if n < 10:
        verdict = 'INCONCLUSIVE'
    elif (
        overall['net_wr'] >= 0.60
        and overall['net_pnl_usd'] > 0
        and overall['profit_factor'] > 1.0
    ):
        verdict = 'PASS'
    else:
        verdict = 'FAIL'

    audit_cols = [
        'session_start','hour_utc','hour_wib','year','orb_high','orb_low','orb_range_pct',
        'has_breakout','breakout_time','has_retest_touch','retest_time','retest_bullish_reaction',
        'retest_above_vwap','bos_time','bos_close','acceptance_pct',
        'frozen_orb_pass','frozen_accept_pass','frozen_character_pass',
        f'{VARIANT}_signal_time',f'{VARIANT}_entry_time',f'{VARIANT}_entry_price',
        f'{VARIANT}_net_{EXIT_MIN}m_pct',f'{VARIANT}_pnl_{EXIT_MIN}m_usd',
    ]
    ev[audit_cols].to_csv(ROOT / f'{PFX}_Audit.csv', index=False)
    trades[audit_cols].to_csv(ROOT / f'{PFX}_Trades.csv', index=False)
    yrs.to_csv(ROOT / f'{PFX}_YearSummary.csv', index=False)

    lines = [
        '# SOL ORB H00 Character Confirmation v1', '',
        f'- Confirmation period: **{START.date()} to {(END - pd.Timedelta(days=1)).date()}** (External only)',
        '- Reference Validation 2025–2026: **CLOSED / NOT USED**',
        '- Anchor: **17:00 UTC / 00:00 WIB**',
        '- Frozen character: 15m ORB range >= 0.50% -> upside break -> bullish retest reaction above anchored VWAP -> small BOS above VWAP -> BOS close >= 0.50% above ORB High -> next-5m-open LONG.',
        '- Exit: fixed +60 minutes; roundtrip cost 0.15%; notional USD 500.',
        '', '## Overall confirmation', '',
        '| N | Net WR | Net PnL | Exp | PF | Max DD | Max LS | Verdict |',
        '|---:|---:|---:|---:|---:|---:|---:|---|',
        f"| {n} | {overall['net_wr']:.2%} | ${overall['net_pnl_usd']:.2f} | ${overall['expectancy_usd']:.2f} | {overall['profit_factor']:.3f} | ${overall['max_dd_usd']:.2f} | {int(overall['max_loss_streak'])} | **{verdict}** |",
        '', '## Year diagnostics', '',
        '| Year | N | Net WR | Net PnL | Exp | PF | Max DD | Max LS |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, r in yrs.iterrows():
        lines.append(
            f"| {int(r.year)} | {int(r.n)} | {r.net_wr:.2%} | ${r.net_pnl_usd:.2f} | ${r.expectancy_usd:.2f} | {r.profit_factor:.3f} | ${r.max_dd_usd:.2f} | {int(r.max_loss_streak)} |"
        )
    lines += [
        '', '## Frozen decision gate', '',
        '- PASS requires N >= 10, net WR >= 60%, net PnL > 0, and PF > 1.0.',
        '- N < 10 is INCONCLUSIVE.',
        '- No threshold/hour/exit tuning is permitted from this run.',
        '', f'## Verdict: **{verdict}**',
    ]
    (ROOT / f'{PFX}_Result.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (ROOT / f'{PFX}_Status.txt').write_text(verdict + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
