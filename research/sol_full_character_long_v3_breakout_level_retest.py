#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_FULL_CHARACTER_LONG_V3_BREAKOUT_LEVEL_RETEST'
YEARS = (2020, 2021, 2022, 2023, 2024)
RANGE_LOOKBACK = 20
IMPULSE_MAX_BARS = 12
IMPULSE_DISP_MULT = 1.5
IMPULSE_EFF_MIN = 0.60
RETEST_MAX_5M = 288


def latest_unconsumed_high(high_hist, consumed):
    for h in reversed(high_hist):
        if int(h['pivot_i']) not in consumed:
            return h
    return None


def detect_breakout_contexts(x5: pd.DataFrame) -> pd.DataFrame:
    h1 = fc1.build_h1(x5)
    idx = h1.index
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()
    lows_by_confirm, highs_by_confirm = lib.compute_pivots(hi, lo)
    high_hist, low_hist, rows = [], [], []
    consumed = set()

    for i in range(30, len(h1)-2):
        high_hist.extend(highs_by_confirm.get(i, []))
        low_hist.extend(lows_by_confirm.get(i, []))
        h0 = latest_unconsumed_high(high_hist, consumed)
        if h0 is None or not low_hist:
            continue
        l1 = low_hist[-1]
        if int(l1['pivot_i']) <= int(h0['pivot_i']):
            continue
        level = float(h0['price'])
        if not (cl[i] > level and cl[i-1] <= level):
            continue
        consumed.add(int(h0['pivot_i']))

        l1i = int(l1['pivot_i'])
        leg_bars = i - l1i
        if leg_bars < 1 or leg_bars > IMPULSE_MAX_BARS or l1i-RANGE_LOOKBACK < 0:
            continue
        med_range = float(np.median(hi[l1i-RANGE_LOOKBACK:l1i] - lo[l1i-RANGE_LOOKBACK:l1i]))
        if not np.isfinite(med_range) or med_range <= 0:
            continue
        displacement = float(cl[i] - float(l1['price']))
        disp_units = displacement / med_range
        if disp_units < IMPULSE_DISP_MULT:
            continue
        leg_close = cl[l1i:i+1]
        path = float(np.abs(np.diff(leg_close)).sum())
        net = float(cl[i] - cl[l1i])
        eff = net/path if path > 0 else np.nan
        if not np.isfinite(eff) or eff < IMPULSE_EFF_MIN:
            continue

        breakout_close_time = idx[i] + pd.Timedelta(hours=1)
        if breakout_close_time.year not in YEARS:
            continue
        rows.append({
            'context_id': str(idx[i]) + '__' + str(int(h0['pivot_i'])),
            'breakout_close_time': breakout_close_time,
            'breakout_i_h1': int(i),
            'breakout_year': int(breakout_close_time.year),
            'h0_level': level,
            'h0_pivot_i': int(h0['pivot_i']),
            'l1_price': float(l1['price']),
            'l1_pivot_i': l1i,
            'impulse_bars': leg_bars,
            'impulse_displacement_pct': displacement/float(l1['price'])*100.0,
            'impulse_displacement_range_units': disp_units,
            'impulse_efficiency': eff,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError('no qualifying H1 breakout contexts')
    return out.sort_values('breakout_close_time').drop_duplicates('context_id').reset_index(drop=True)


def scan_first_retests(contexts: pd.DataFrame, x5: pd.DataFrame):
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    trades, retests = [], []

    for _, c in contexts.iterrows():
        start = int(idx.searchsorted(pd.Timestamp(c.breakout_close_time)))
        if start >= len(x5)-lib.FUTURE_BARS-2:
            continue
        last = min(start + RETEST_MAX_5M - 1, len(x5)-lib.FUTURE_BARS-2)
        level = float(c.h0_level)
        touched = False
        for i in range(start, last+1):
            if lo[i] <= level:
                touched = True
                valid = bool(lo[i] < level and cl[i] > level)
                retests.append({
                    'context_id': c.context_id,
                    'breakout_close_time': c.breakout_close_time,
                    'first_retest_bar_time': idx[i],
                    'first_retest_delay_min': int((i-start+1)*5),
                    'h0_level': level,
                    'retest_open': float(op[i]),
                    'retest_high': float(hi[i]),
                    'retest_low': float(lo[i]),
                    'retest_close': float(cl[i]),
                    'valid_sweep_reclaim': int(valid),
                })
                if valid:
                    lib.add_signal(trades, 'BREAKOUT_LEVEL_FIRST_RETEST_SWEEP_RECLAIM', i, idx, op, hi, lo, cl, {
                        'context_id': c.context_id,
                        'breakout_close_time': c.breakout_close_time,
                        'h0_level': level,
                        'first_retest_delay_min': int((i-start+1)*5),
                        'impulse_bars': int(c.impulse_bars),
                        'impulse_displacement_pct': float(c.impulse_displacement_pct),
                        'impulse_displacement_range_units': float(c.impulse_displacement_range_units),
                        'impulse_efficiency': float(c.impulse_efficiency),
                    })
                break
        if not touched:
            retests.append({
                'context_id': c.context_id,
                'breakout_close_time': c.breakout_close_time,
                'first_retest_bar_time': pd.NaT,
                'first_retest_delay_min': np.nan,
                'h0_level': level,
                'retest_open': np.nan,'retest_high':np.nan,'retest_low':np.nan,'retest_close':np.nan,
                'valid_sweep_reclaim': 0,
            })

    tr = pd.DataFrame(trades)
    if tr.empty:
        raise RuntimeError('no valid first-retest sweep/reclaim trades')
    tr = tr.sort_values('entry_time').drop_duplicates(['context_id','entry_time']).reset_index(drop=True)
    return tr, pd.DataFrame(retests)


def summarize(contexts, trades, retests):
    pooled = lib.econ(trades)
    ratio = float(trades.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median())
    pos_years = 0
    yrows = []
    for y in YEARS:
        g = trades[trades.year == y].copy()
        e = lib.econ(g)
        if e['pnl_usd'] > 0: pos_years += 1
        yrows.append({
            'year':y,'n':e['n'],'wr60':e['wr'],'expectancy60_pct':e['expectancy_pct'],
            'pf60':e['pf'],'pnl60_usd':e['pnl_usd'],'max_dd_usd':e['max_dd_usd'],
            'max_loss_streak':e['max_loss_streak'],
            'clean_up_impulse_rate':float(g.clean_up_impulse.mean()) if len(g) else np.nan,
            'median_mfe60_pct':float(g.mfe60_pct.median()) if len(g) else np.nan,
            'median_mae60_pct':float(g.mae60_pct.median()) if len(g) else np.nan,
            'median_mfe_mae_ratio':float(g.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median()) if len(g) else np.nan,
            'median_retest_delay_min':float(g.first_retest_delay_min.median()) if len(g) else np.nan,
        })
    gates = {
        'n_ge_100': pooled['n'] >= 100,
        'expectancy_positive': bool(np.isfinite(pooled['expectancy_pct']) and pooled['expectancy_pct'] > 0),
        'pf_ge_1_15': bool(np.isfinite(pooled['pf']) and pooled['pf'] >= 1.15),
        'positive_pnl_years_ge_4_of_5': pos_years >= 4,
        'median_mfe_mae_ge_1_20': bool(np.isfinite(ratio) and ratio >= 1.20),
    }
    valid_n = int(retests.valid_sweep_reclaim.sum())
    summary = {
        'context_n':len(contexts),
        'first_retest_n':int(retests.first_retest_bar_time.notna().sum()),
        'valid_trigger_n':valid_n,
        'valid_rate_vs_context':valid_n/len(contexts),
        'valid_rate_vs_retest':valid_n/max(1,int(retests.first_retest_bar_time.notna().sum())),
        'wr60':pooled['wr'],'expectancy60_pct':pooled['expectancy_pct'],'pf60':pooled['pf'],
        'pnl60_usd':pooled['pnl_usd'],'max_dd_usd':pooled['max_dd_usd'],
        'max_loss_streak':pooled['max_loss_streak'],
        'clean_up_impulse_rate':float(trades.clean_up_impulse.mean()),
        'median_mfe60_pct':float(trades.mfe60_pct.median()),
        'median_mae60_pct':float(trades.mae60_pct.median()),
        'median_mfe_mae_ratio':ratio,
        'median_time_to_mfe_min':float(trades.time_to_mfe_min.median()),
        'median_time_to_mae_min':float(trades.time_to_mae_min.median()),
        'median_retest_delay_min':float(trades.first_retest_delay_min.median()),
        'positive_pnl_years':pos_years,
        **{'gate_'+k:v for k,v in gates.items()},
        'verdict':'PASS_TO_CHARACTERIZATION' if all(gates.values()) else 'REJECTED_AS_DEFINED',
    }
    return pd.DataFrame([summary]), pd.DataFrame(yrows)


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5('SOLUSDT')
    if coverage < .995:
        raise RuntimeError(f'coverage too low: {coverage:.6%}')
    contexts = detect_breakout_contexts(x5)
    trades, retests = scan_first_retests(contexts, x5)
    summary, yearly = summarize(contexts, trades, retests)

    contexts.to_csv(ROOT/f'{PFX}_Contexts.csv', index=False)
    retests.to_csv(ROOT/f'{PFX}_FirstRetests.csv', index=False)
    trades.to_csv(ROOT/f'{PFX}_Trades.csv', index=False)
    summary.to_csv(ROOT/f'{PFX}_Summary.csv', index=False)
    yearly.to_csv(ROOT/f'{PFX}_YearSummary.csv', index=False)

    r = summary.iloc[0]
    lines = [
        '# SOL Full-Character Long V3 — Breakout-Level Retest Result','',
        f'- Data coverage: **{coverage*100:.6f}%**',
        f'- Qualifying impulsive H1 breakout contexts: **{int(r.context_n)}**',
        f'- Contexts reaching a first 5m retest within 24H: **{int(r.first_retest_n)}**',
        f'- Valid first-retest sweep/reclaim entries: **{int(r.valid_trigger_n)}**',
        '- Character: **H1 impulse -> new high -> first retest of broken H1 swing-high -> 5m sweep/reclaim -> LONG**.',
        '- 2020-2024 evaluation; 2025+ remained CLOSED.','',
        '## Pooled economics','',
        '| N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | MFE | MAE | MFE/MAE | Retest delay | Pos yrs | Verdict |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|',
        f"| {int(r.valid_trigger_n)} | {r.wr60*100:.2f}% | {r.expectancy60_pct:.4f}% | {lib.pfmt(r.pf60)} | ${r.pnl60_usd:.2f} | ${r.max_dd_usd:.2f} | {int(r.max_loss_streak)} | {r.clean_up_impulse_rate*100:.2f}% | {r.median_mfe60_pct:.3f}% | {r.median_mae60_pct:.3f}% | {r.median_mfe_mae_ratio:.3f} | {r.median_retest_delay_min:.1f}m | {int(r.positive_pnl_years)}/5 | **{r.verdict}** |",
        '', '## Yearly economics','',
        '| Year | N | WR60 | Exp60 | PF | PnL | MFE/MAE | Retest delay |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, y in yearly.iterrows():
        wr = y.wr60*100 if np.isfinite(y.wr60) else np.nan
        exp = f'{y.expectancy60_pct:.4f}%' if np.isfinite(y.expectancy60_pct) else 'n/a'
        rr = f'{y.median_mfe_mae_ratio:.3f}' if np.isfinite(y.median_mfe_mae_ratio) else 'n/a'
        delay = f'{y.median_retest_delay_min:.1f}m' if np.isfinite(y.median_retest_delay_min) else 'n/a'
        lines.append(f'| {int(y.year)} | {int(y.n)} | {wr:.2f}% | {exp} | {lib.pfmt(y.pf60)} | ${y.pnl60_usd:.2f} | {rr} | {delay} |')
    lines += ['', '## Frozen gate audit','']
    for gate in ('n_ge_100','expectancy_positive','pf_ge_1_15','positive_pnl_years_ge_4_of_5','median_mfe_mae_ge_1_20'):
        lines.append(f"- {'PASS' if bool(r['gate_'+gate]) else 'FAIL'} — {gate}")
    lines += ['', 'OFFICIAL_VERDICT=' + str(r.verdict), '2025_PLUS=CLOSED']
    text = '\n'.join(lines) + '\n'
    (ROOT/f'{PFX}_Result.md').write_text(text, encoding='utf-8')
    (ROOT/f'{PFX}_Status.txt').write_text(f'OFFICIAL_VERDICT={r.verdict}\nTRIGGERED_N={int(r.valid_trigger_n)}\n2025_PLUS=CLOSED\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()