#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_structure_library_v1 as v1
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_FULL_CHARACTER_LONG_V1'
YEARS = (2020, 2021, 2022, 2023, 2024)

IMPULSE_MAX_BARS = 12
IMPULSE_DISP_MULT = 1.5
IMPULSE_EFF_MIN = 0.60
RANGE_LOOKBACK = 20
RETURN_MAX_H1 = 24
TRIGGER_MAX_5M = 24
BODY_LOOKBACK_5M = 20
DISP_BODY_MULT = 1.5
DISP_CLOSE_LOC = 0.75
BOS_LOOKBACK_5M = 12

TRIGGERS = (
    'DEMAND_SWEEP_RECLAIM',
    'BULLISH_DISPLACEMENT_EXIT_ZONE',
    'BREAK_LAST_RETRACE_PIVOT_HIGH',
)


def build_h1(x5: pd.DataFrame) -> pd.DataFrame:
    agg = x5.resample('1h', label='left', closed='left').agg(
        open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
        close=('close', 'last'), n=('close', 'count')
    )
    return agg[agg.n == 12].drop(columns=['n']).dropna()


def latest_unconsumed_high(high_hist, consumed):
    for h in reversed(high_hist):
        if int(h['pivot_i']) not in consumed:
            return h
    return None


def detect_full_character(x5: pd.DataFrame) -> pd.DataFrame:
    h1 = build_h1(x5)
    idx = h1.index
    op = h1.open.astype(float).to_numpy()
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()
    lows_by_confirm, highs_by_confirm = v1.compute_pivots(hi, lo)
    high_hist, low_hist, pending, rows = [], [], [], []
    consumed_highs = set()

    for i in range(30, len(h1) - RETURN_MAX_H1 - 2):
        high_hist.extend(highs_by_confirm.get(i, []))
        low_hist.extend(lows_by_confirm.get(i, []))

        keep = []
        for p in pending:
            if i <= p['breakout_i']:
                keep.append(p); continue
            if i > p['deadline_i'] or cl[i] < p['demand_low']:
                continue
            if lo[i] <= p['demand_top']:
                ready_time = idx[i] + pd.Timedelta(hours=1)
                if ready_time.year in YEARS:
                    rows.append({
                        'structure_id': str(idx[p['breakout_i']]) + '__' + str(int(p['h0_pivot_i'])),
                        'structure_ready_time': ready_time, 'year': int(ready_time.year),
                        'breakout_time': idx[p['breakout_i']] + pd.Timedelta(hours=1),
                        'breakout_i_h1': int(p['breakout_i']), 'return_i_h1': int(i),
                        'return_delay_h': int(i - p['breakout_i']),
                        'h0_price': float(p['h0_price']), 'h0_pivot_i': int(p['h0_pivot_i']),
                        'l1_price': float(p['l1_price']), 'l1_pivot_i': int(p['l1_pivot_i']),
                        'origin_time': idx[p['origin_i']], 'origin_i_h1': int(p['origin_i']),
                        'demand_low': float(p['demand_low']), 'demand_top': float(p['demand_top']),
                        'impulse_bars': int(p['impulse_bars']),
                        'impulse_displacement_pct': float(p['impulse_displacement_pct']),
                        'impulse_displacement_range_units': float(p['impulse_displacement_range_units']),
                        'impulse_efficiency': float(p['impulse_efficiency']),
                    })
                continue
            keep.append(p)
        pending = keep

        h0 = latest_unconsumed_high(high_hist, consumed_highs)
        if h0 is None or not low_hist:
            continue
        l1 = low_hist[-1]
        if int(l1['pivot_i']) <= int(h0['pivot_i']):
            continue
        level = float(h0['price'])
        if not (cl[i] > level and cl[i-1] <= level):
            continue
        consumed_highs.add(int(h0['pivot_i']))
        l1i = int(l1['pivot_i'])
        leg_bars = i - l1i
        if leg_bars < 1 or leg_bars > IMPULSE_MAX_BARS or l1i - RANGE_LOOKBACK < 0:
            continue
        median_range20 = float(np.median(hi[l1i-RANGE_LOOKBACK:l1i] - lo[l1i-RANGE_LOOKBACK:l1i]))
        if not np.isfinite(median_range20) or median_range20 <= 0:
            continue
        displacement = float(cl[i] - float(l1['price']))
        disp_units = displacement / median_range20
        if disp_units < IMPULSE_DISP_MULT:
            continue
        leg_close = cl[l1i:i+1]
        path = float(np.abs(np.diff(leg_close)).sum())
        net_close = float(cl[i] - cl[l1i])
        efficiency = net_close / path if path > 0 else np.nan
        if not np.isfinite(efficiency) or efficiency < IMPULSE_EFF_MIN:
            continue
        origin_i = None
        for k in range(i-1, l1i-1, -1):
            if cl[k] < op[k]:
                origin_i = int(k); break
        if origin_i is None:
            continue
        demand_low, demand_top = float(lo[origin_i]), float(op[origin_i])
        if not (np.isfinite(demand_low) and np.isfinite(demand_top) and demand_top > demand_low):
            continue
        pending.append({
            'breakout_i': int(i), 'deadline_i': int(i + RETURN_MAX_H1),
            'h0_price': level, 'h0_pivot_i': int(h0['pivot_i']),
            'l1_price': float(l1['price']), 'l1_pivot_i': l1i, 'origin_i': origin_i,
            'demand_low': demand_low, 'demand_top': demand_top, 'impulse_bars': leg_bars,
            'impulse_displacement_pct': displacement / float(l1['price']) * 100.0,
            'impulse_displacement_range_units': disp_units, 'impulse_efficiency': efficiency,
        })

    out = pd.DataFrame(rows)
    if out.empty: raise RuntimeError('no full-character H1 structures detected')
    return out.sort_values('structure_ready_time').drop_duplicates('structure_id').reset_index(drop=True)


def latest_retrace_pivot_high(ready_pos, highs_by_confirm):
    candidates = []
    for ci in range(max(0, ready_pos-BOS_LOOKBACK_5M), ready_pos):
        for h in highs_by_confirm.get(ci, []):
            if int(h['pivot_i']) >= ready_pos-BOS_LOOKBACK_5M and int(h['confirm_i']) <= ready_pos-1:
                candidates.append(h)
    return max(candidates, key=lambda h: int(h['pivot_i'])) if candidates else None


def apply_triggers(structures, x5):
    idx = x5.index
    op = x5.open.astype(float).to_numpy(); hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy(); cl = x5.close.astype(float).to_numpy()
    _, highs_by_confirm = v1.compute_pivots(hi, lo)
    trades, elig_rows = [], []
    for _, s in structures.iterrows():
        ready_time = pd.Timestamp(s.structure_ready_time)
        ready_pos = int(idx.searchsorted(ready_time))
        if ready_pos >= len(x5)-v1.FUTURE_BARS-2 or ready_pos < BODY_LOOKBACK_5M: continue
        demand_low, demand_top = float(s.demand_low), float(s.demand_top)
        median_body20 = float(np.median(np.abs(cl[ready_pos-BODY_LOOKBACK_5M:ready_pos] - op[ready_pos-BODY_LOOKBACK_5M:ready_pos])))
        bos_ref = latest_retrace_pivot_high(ready_pos, highs_by_confirm)
        metas = {
            'DEMAND_SWEEP_RECLAIM': (True, demand_low),
            'BULLISH_DISPLACEMENT_EXIT_ZONE': (bool(np.isfinite(median_body20) and median_body20 > 0), demand_top),
            'BREAK_LAST_RETRACE_PIVOT_HIGH': (bos_ref is not None, float(bos_ref['price']) if bos_ref is not None else np.nan),
        }
        for trigger in TRIGGERS:
            eligible, ref = metas[trigger]
            elig_rows.append({'structure_id': s.structure_id, 'structure_ready_time': ready_time, 'year': int(s.year), 'trigger': trigger, 'eligible': bool(eligible), 'reference_level': ref})
            if not eligible: continue
            last_scan = min(ready_pos + TRIGGER_MAX_5M - 1, len(x5)-v1.FUTURE_BARS-2)
            for i in range(ready_pos, last_scan+1):
                if cl[i] < demand_low: break
                fired = False
                if trigger == 'DEMAND_SWEEP_RECLAIM':
                    fired = bool(lo[i] < demand_low and cl[i] > demand_low)
                elif trigger == 'BULLISH_DISPLACEMENT_EXIT_ZONE':
                    rng = float(hi[i]-lo[i])
                    if rng > 0:
                        body = float(cl[i]-op[i]); close_loc = float((cl[i]-lo[i])/rng)
                        fired = bool(body > 0 and body >= DISP_BODY_MULT*median_body20 and close_loc >= DISP_CLOSE_LOC and cl[i] > demand_top)
                else:
                    fired = bool(cl[i] > ref)
                if fired:
                    detector = 'IMPULSE_NEW_HIGH_DEMAND_PULLBACK__' + trigger
                    v1.add_signal(trades, detector, i, idx, op, hi, lo, cl, {
                        'full_character': 'IMPULSE_NEW_HIGH_DEMAND_PULLBACK', 'entry_trigger': trigger,
                        'structure_id': s.structure_id, 'structure_ready_time': ready_time,
                        'minutes_after_structure': int((i-ready_pos+1)*5),
                        'demand_low': demand_low, 'demand_top': demand_top, 'trigger_reference_level': ref,
                        'impulse_bars': int(s.impulse_bars),
                        'impulse_displacement_pct': float(s.impulse_displacement_pct),
                        'impulse_displacement_range_units': float(s.impulse_displacement_range_units),
                        'impulse_efficiency': float(s.impulse_efficiency), 'return_delay_h': int(s.return_delay_h),
                    })
                    break
    tr = pd.DataFrame(trades)
    if tr.empty: raise RuntimeError('no triggered trades detected')
    tr = tr.sort_values(['structure','entry_time','structure_id']).drop_duplicates(['structure','entry_time','structure_id']).reset_index(drop=True)
    return tr, pd.DataFrame(elig_rows)


def summarize(structures, trades, elig):
    pooled, yearly = [], []
    for trigger in TRIGGERS:
        detector = 'IMPULSE_NEW_HIGH_DEMAND_PULLBACK__' + trigger
        g = trades[trades.structure == detector].copy(); e = v1.econ(g)
        eligible_n = int(elig[(elig.trigger == trigger) & (elig.eligible)].shape[0])
        ratio = float(g.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median()) if len(g) else np.nan
        pos_years = 0
        for y in YEARS:
            gy = g[g.year == y].copy(); ey = v1.econ(gy)
            if ey['pnl_usd'] > 0: pos_years += 1
            yearly.append({'trigger': trigger,'year':y,'n':ey['n'],'wr60':ey['wr'],'expectancy60_pct':ey['expectancy_pct'],'pf60':ey['pf'],'pnl60_usd':ey['pnl_usd'],'max_dd_usd':ey['max_dd_usd'],'max_loss_streak':ey['max_loss_streak'],'clean_up_impulse_rate':float(gy.clean_up_impulse.mean()) if len(gy) else np.nan,'median_mfe_mae_ratio':float(gy.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median()) if len(gy) else np.nan,'median_trigger_delay_min':float(gy.minutes_after_structure.median()) if len(gy) else np.nan})
        gates = {'n_ge_100':e['n']>=100,'expectancy_positive':bool(np.isfinite(e['expectancy_pct']) and e['expectancy_pct']>0),'pf_ge_1_15':bool(np.isfinite(e['pf']) and e['pf']>=1.15),'positive_pnl_years_ge_4_of_5':pos_years>=4,'median_mfe_mae_ge_1_20':bool(np.isfinite(ratio) and ratio>=1.20)}
        pooled.append({'structure':'IMPULSE_NEW_HIGH_DEMAND_PULLBACK','trigger':trigger,'structure_n':int(len(structures)),'eligible_n':eligible_n,'triggered_n':e['n'],'trigger_rate_vs_eligible':e['n']/eligible_n if eligible_n else np.nan,'wr60':e['wr'],'expectancy60_pct':e['expectancy_pct'],'pf60':e['pf'],'pnl60_usd':e['pnl_usd'],'max_dd_usd':e['max_dd_usd'],'max_loss_streak':e['max_loss_streak'],'clean_up_impulse_rate':float(g.clean_up_impulse.mean()) if len(g) else np.nan,'median_mfe_mae_ratio':ratio,'median_trigger_delay_min':float(g.minutes_after_structure.median()) if len(g) else np.nan,'positive_pnl_years':pos_years,**{'gate_'+k:v for k,v in gates.items()},'verdict':'PASS_TO_CHARACTERIZATION' if all(gates.values()) else 'REJECTED_AS_DEFINED'})
    sy = structures.groupby('year').agg(structure_n=('structure_id','count'),median_impulse_bars=('impulse_bars','median'),median_impulse_disp_pct=('impulse_displacement_pct','median'),median_impulse_disp_range_units=('impulse_displacement_range_units','median'),median_impulse_efficiency=('impulse_efficiency','median'),median_return_delay_h=('return_delay_h','median')).reset_index()
    return pd.DataFrame(pooled), pd.DataFrame(yearly), sy


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5('SOLUSDT')
    if coverage < .995: raise RuntimeError(f'coverage too low: {coverage:.6%}')
    structures = detect_full_character(x5)
    trades, elig = apply_triggers(structures, x5)
    pooled, yearly, sy = summarize(structures, trades, elig)
    structures.to_csv(ROOT/f'{PFX}_Structures.csv', index=False)
    elig.to_csv(ROOT/f'{PFX}_TriggerEligibility.csv', index=False)
    trades.to_csv(ROOT/f'{PFX}_TriggeredTrades.csv', index=False)
    pooled.to_csv(ROOT/f'{PFX}_Summary.csv', index=False)
    yearly.to_csv(ROOT/f'{PFX}_YearSummary.csv', index=False)
    sy.to_csv(ROOT/f'{PFX}_StructureYearSummary.csv', index=False)

    lines = ['# SOL Full-Character Long V1 — Result','',f'- Data coverage: **{coverage*100:.6f}%**',f'- Completed H1 full-character structures: **{len(structures)}**','- Character: **H1 impulse -> new high -> impulse-origin demand -> first fresh demand pullback**.','- Entry triggers: separate causal 5m layer after structure completion.','- Evaluation: 2020-2024; 2025+ remained CLOSED.','- Entry = next 5m open after trigger; fixed +60m diagnostic; 0.15% RT cost.','','## Structure incidence','','| Year | Structures | Impulse bars | Impulse disp | Range units | Efficiency | Return delay |','|---:|---:|---:|---:|---:|---:|---:|']
    for _, r in sy.iterrows(): lines.append(f'| {int(r.year)} | {int(r.structure_n)} | {r.median_impulse_bars:.1f} | {r.median_impulse_disp_pct:.3f}% | {r.median_impulse_disp_range_units:.3f} | {r.median_impulse_efficiency:.3f} | {r.median_return_delay_h:.1f}h |')
    lines += ['','## Structure x entry-trigger scorecard','','| Trigger | Structures | Eligible | Entries | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for _, r in pooled.iterrows(): lines.append(f'| {r.trigger} | {int(r.structure_n)} | {int(r.eligible_n)} | {int(r.triggered_n)} | {r.trigger_rate_vs_eligible*100:.2f}% | {r.wr60*100:.2f}% | {r.expectancy60_pct:.4f}% | {v1.pfmt(r.pf60)} | ${r.pnl60_usd:.2f} | ${r.max_dd_usd:.2f} | {r.clean_up_impulse_rate*100:.2f}% | {r.median_mfe_mae_ratio:.3f} | {r.median_trigger_delay_min:.1f}m | {int(r.positive_pnl_years)}/5 | **{r.verdict}** |')
    lines += ['','## Yearly economics','']
    for trigger in TRIGGERS:
        lines += [f'### {trigger}','', '| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for _, r in yearly[yearly.trigger == trigger].iterrows(): lines.append(f'| {int(r.year)} | {int(r.n)} | {r.wr60*100:.2f}% | {r.expectancy60_pct:.4f}% | {v1.pfmt(r.pf60)} | ${r.pnl60_usd:.2f} | {r.clean_up_impulse_rate*100:.2f}% | {r.median_mfe_mae_ratio:.3f} | {r.median_trigger_delay_min:.1f}m |')
        lines.append('')
    lines += ['## Frozen gate audit','']
    for _, r in pooled.iterrows():
        lines.append(f'### {r.trigger} — {r.verdict}')
        for gate in ('n_ge_100','expectancy_positive','pf_ge_1_15','positive_pnl_years_ge_4_of_5','median_mfe_mae_ge_1_20'): lines.append(f"- {'PASS' if bool(r['gate_'+gate]) else 'FAIL'} — {gate}")
        lines.append('')
    passing = pooled[pooled.verdict == 'PASS_TO_CHARACTERIZATION'].trigger.tolist()
    status = 'PASSING_FULL_CHARACTER_TRIGGERS=' + (','.join(passing) if passing else 'NONE')
    lines += ['## Interpretation rule','', 'PASS_TO_CHARACTERIZATION means this exact full H1 character + 5m trigger may advance to structure-specific execution / TP / SL characterization.', 'REJECTED_AS_DEFINED rejects only the exact trigger on this frozen full-character structure. Do not rescue it on 2020-2024 by retuning the structure or trigger.','',status]
    (ROOT/f'{PFX}_Result.md').write_text('\n'.join(lines), encoding='utf-8')
    (ROOT/f'{PFX}_Status.txt').write_text(status+'\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()