#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_structure_library_v1 as lib
import sol_full_character_long_v1 as fc1
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = 'SOL_FULL_CHARACTER_LONG_V2_MTF_DEMAND'
YEARS = (2020, 2021, 2022, 2023, 2024)

H4_IMPULSE_MAX_BARS = 12
H4_DISP_MULT = 1.5
H4_EFF_MIN = 0.60
H4_RANGE_LOOKBACK = 20


def build_h4(x5: pd.DataFrame) -> pd.DataFrame:
    agg = x5.resample('4h', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'),
        close=('close','last'), n=('close','count')
    )
    return agg[agg.n == 48].drop(columns=['n']).dropna()


def latest_unconsumed_high(high_hist, consumed):
    for h in reversed(high_hist):
        if int(h['pivot_i']) not in consumed:
            return h
    return None


def detect_h4_demands(x5: pd.DataFrame) -> pd.DataFrame:
    h4 = build_h4(x5)
    idx = h4.index
    op = h4.open.astype(float).to_numpy()
    hi = h4.high.astype(float).to_numpy()
    lo = h4.low.astype(float).to_numpy()
    cl = h4.close.astype(float).to_numpy()
    lows_by_confirm, highs_by_confirm = lib.compute_pivots(hi, lo)
    high_hist, low_hist, rows = [], [], []
    consumed = set()
    for i in range(30, len(h4)-2):
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
        if leg_bars < 1 or leg_bars > H4_IMPULSE_MAX_BARS or l1i-H4_RANGE_LOOKBACK < 0:
            continue
        med_range = float(np.median(hi[l1i-H4_RANGE_LOOKBACK:l1i] - lo[l1i-H4_RANGE_LOOKBACK:l1i]))
        if not np.isfinite(med_range) or med_range <= 0:
            continue
        disp = float(cl[i] - float(l1['price']))
        disp_units = disp / med_range
        if disp_units < H4_DISP_MULT:
            continue
        leg_close = cl[l1i:i+1]
        path = float(np.abs(np.diff(leg_close)).sum())
        net = float(cl[i] - cl[l1i])
        eff = net/path if path > 0 else np.nan
        if not np.isfinite(eff) or eff < H4_EFF_MIN:
            continue
        origin_i = None
        for k in range(i-1, l1i-1, -1):
            if cl[k] < op[k]:
                origin_i = int(k)
                break
        if origin_i is None:
            continue
        dlow = float(lo[origin_i]); dtop = float(op[origin_i])
        if not (np.isfinite(dlow) and np.isfinite(dtop) and dtop > dlow):
            continue
        activation = idx[i] + pd.Timedelta(hours=4)
        rows.append({
            'h4_zone_id': str(idx[i]) + '__' + str(int(h0['pivot_i'])),
            'h4_activation_time': activation,
            'h4_breakout_time': activation,
            'h4_breakout_i': int(i),
            'h4_h0_price': level,
            'h4_l1_price': float(l1['price']),
            'h4_origin_time': idx[origin_i],
            'h4_demand_low': dlow,
            'h4_demand_top': dtop,
            'h4_impulse_bars': leg_bars,
            'h4_impulse_disp_pct': disp/float(l1['price'])*100.0,
            'h4_impulse_disp_range_units': disp_units,
            'h4_impulse_efficiency': eff,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError('no H4 bullish demand zones detected')
    return out.sort_values('h4_activation_time').reset_index(drop=True)


def nest_h1_in_fresh_h4(structures: pd.DataFrame, h4zones: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    h1 = fc1.build_h1(x5)
    xidx = x5.index
    xlo = x5.low.astype(float).to_numpy()
    xcl = x5.close.astype(float).to_numpy()
    rows = []
    h4zones = h4zones.sort_values('h4_activation_time').reset_index(drop=True)
    for _, s in structures.iterrows():
        ri = int(s.return_i_h1)
        if ri < 0 or ri >= len(h1):
            continue
        return_start = h1.index[ri]
        return_low = float(h1.low.iloc[ri])
        return_close = float(h1.close.iloc[ri])
        h1_low = float(s.demand_low); h1_top = float(s.demand_top)
        candidates = h4zones[h4zones.h4_activation_time <= return_start]
        chosen = None
        for _, z in candidates.iloc[::-1].iterrows():
            h4_low = float(z.h4_demand_low); h4_top = float(z.h4_demand_top)
            overlap_low = max(h1_low, h4_low)
            overlap_high = min(h1_top, h4_top)
            if overlap_high < overlap_low:
                continue
            if not (return_low <= h4_top and return_close >= h4_low):
                continue
            a = int(xidx.searchsorted(pd.Timestamp(z.h4_activation_time)))
            b = int(xidx.searchsorted(return_start))
            if b > a:
                prior_low = xlo[a:b]
                prior_close = xcl[a:b]
                if np.any(prior_low <= h4_top):
                    continue
                if np.any(prior_close < h4_low):
                    continue
            chosen = z
            break
        if chosen is None:
            continue
        rec = s.to_dict()
        h4_low = float(chosen.h4_demand_low); h4_top = float(chosen.h4_demand_top)
        overlap_low = max(h1_low, h4_low); overlap_high = min(h1_top, h4_top)
        overlap_width = max(0.0, overlap_high-overlap_low)
        h1_width = max(1e-12, h1_top-h1_low)
        rec.update({
            'h4_zone_id': chosen.h4_zone_id,
            'h4_activation_time': chosen.h4_activation_time,
            'h4_demand_low': h4_low,
            'h4_demand_top': h4_top,
            'h4_impulse_bars': int(chosen.h4_impulse_bars),
            'h4_impulse_disp_pct': float(chosen.h4_impulse_disp_pct),
            'h4_impulse_disp_range_units': float(chosen.h4_impulse_disp_range_units),
            'h4_impulse_efficiency': float(chosen.h4_impulse_efficiency),
            'h1_h4_overlap_width': overlap_width,
            'h1_h4_overlap_frac_h1': overlap_width/h1_width,
        })
        rows.append(rec)
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError('no H1 structures nested in fresh H4 demand')
    return out.sort_values('structure_ready_time').reset_index(drop=True)


def exact_sweep_reclaim_trades(nested: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    trades, _ = fc1.apply_triggers(nested, x5)
    detector = 'IMPULSE_NEW_HIGH_DEMAND_PULLBACK__DEMAND_SWEEP_RECLAIM'
    out = trades[trades.structure == detector].copy()
    if out.empty:
        raise RuntimeError('no nested sweep/reclaim trades')
    return out.reset_index(drop=True)


def summarize(v1_structures, nested, trades):
    e = lib.econ(trades)
    ratio = float(trades.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median())
    yearly = []
    pos_years = 0
    for y in YEARS:
        g = trades[trades.year == y].copy()
        ey = lib.econ(g)
        if ey['pnl_usd'] > 0:
            pos_years += 1
        yearly.append({
            'year':y,'n':ey['n'],'wr60':ey['wr'],'expectancy60_pct':ey['expectancy_pct'],
            'pf60':ey['pf'],'pnl60_usd':ey['pnl_usd'],'max_dd_usd':ey['max_dd_usd'],
            'max_loss_streak':ey['max_loss_streak'],
            'clean_up_impulse_rate':float(g.clean_up_impulse.mean()) if len(g) else np.nan,
            'median_mfe_mae_ratio':float(g.mfe_mae_ratio.replace([np.inf,-np.inf],np.nan).median()) if len(g) else np.nan,
            'median_trigger_delay_min':float(g.minutes_after_structure.median()) if len(g) else np.nan,
        })
    gates = {
        'n_ge_100': e['n'] >= 100,
        'expectancy_positive': bool(np.isfinite(e['expectancy_pct']) and e['expectancy_pct'] > 0),
        'pf_ge_1_15': bool(np.isfinite(e['pf']) and e['pf'] >= 1.15),
        'positive_pnl_years_ge_4_of_5': pos_years >= 4,
        'median_mfe_mae_ge_1_20': bool(np.isfinite(ratio) and ratio >= 1.20),
    }
    pooled = {
        'v1_h1_structure_n': int(len(v1_structures)),
        'nested_h4_h1_structure_n': int(len(nested)),
        'nested_retention_rate': len(nested)/len(v1_structures) if len(v1_structures) else np.nan,
        'triggered_n': e['n'],
        'trigger_rate': e['n']/len(nested) if len(nested) else np.nan,
        'wr60': e['wr'],'expectancy60_pct':e['expectancy_pct'],'pf60':e['pf'],
        'pnl60_usd':e['pnl_usd'],'max_dd_usd':e['max_dd_usd'],'max_loss_streak':e['max_loss_streak'],
        'clean_up_impulse_rate':float(trades.clean_up_impulse.mean()),
        'median_mfe_mae_ratio':ratio,
        'median_trigger_delay_min':float(trades.minutes_after_structure.median()),
        'positive_pnl_years':pos_years,
        **{'gate_'+k:v for k,v in gates.items()},
        'verdict':'PASS_TO_CHARACTERIZATION' if all(gates.values()) else 'REJECTED_AS_DEFINED',
    }
    incidence = nested.groupby('year').agg(
        nested_structure_n=('structure_id','count'),
        median_h4_disp_pct=('h4_impulse_disp_pct','median'),
        median_h4_disp_range_units=('h4_impulse_disp_range_units','median'),
        median_h4_efficiency=('h4_impulse_efficiency','median'),
        median_overlap_frac_h1=('h1_h4_overlap_frac_h1','median'),
    ).reset_index()
    return pd.DataFrame([pooled]), pd.DataFrame(yearly), incidence


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5('SOLUSDT')
    if coverage < .995:
        raise RuntimeError(f'coverage too low: {coverage:.6%}')
    v1_structures = fc1.detect_full_character(x5)
    h4zones = detect_h4_demands(x5)
    nested = nest_h1_in_fresh_h4(v1_structures, h4zones, x5)
    trades = exact_sweep_reclaim_trades(nested, x5)
    pooled, yearly, incidence = summarize(v1_structures, nested, trades)

    h4zones.to_csv(ROOT/f'{PFX}_H4DemandZones.csv', index=False)
    nested.to_csv(ROOT/f'{PFX}_NestedStructures.csv', index=False)
    trades.to_csv(ROOT/f'{PFX}_TriggeredTrades.csv', index=False)
    pooled.to_csv(ROOT/f'{PFX}_Summary.csv', index=False)
    yearly.to_csv(ROOT/f'{PFX}_YearSummary.csv', index=False)
    incidence.to_csv(ROOT/f'{PFX}_StructureYearSummary.csv', index=False)

    r = pooled.iloc[0]
    lines = [
        '# SOL Full-Character Long V2 — MTF Demand Result','',
        f'- Data coverage: **{coverage*100:.6f}%**',
        f'- V1 H1 full-character structures: **{int(r.v1_h1_structure_n)}**',
        f'- H1 structures nested in fresh H4 demand: **{int(r.nested_h4_h1_structure_n)}** ({r.nested_retention_rate*100:.2f}%)',
        f'- Exact 5m sweep/reclaim entries: **{int(r.triggered_n)}** ({r.trigger_rate*100:.2f}% of nested structures)',
        '- Character: **fresh H4 bullish demand -> H1 impulse/new-high/demand-pullback -> 5m H1-demand sweep/reclaim**.',
        '- Evaluation 2020-2024; 2025+ remained CLOSED.','',
        '## Nested structure incidence','',
        '| Year | Nested structures | H4 disp | H4 range units | H4 efficiency | H1 overlap |',
        '|---:|---:|---:|---:|---:|---:|',
    ]
    for _, z in incidence.iterrows():
        lines.append(f'| {int(z.year)} | {int(z.nested_structure_n)} | {z.median_h4_disp_pct:.3f}% | {z.median_h4_disp_range_units:.3f} | {z.median_h4_efficiency:.3f} | {z.median_overlap_frac_h1*100:.1f}% |')
    lines += [
        '', '## Exact entry economics','',
        '| N | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|',
        f'| {int(r.triggered_n)} | {r.wr60*100:.2f}% | {r.expectancy60_pct:.4f}% | {lib.pfmt(r.pf60)} | ${r.pnl60_usd:.2f} | ${r.max_dd_usd:.2f} | {r.clean_up_impulse_rate*100:.2f}% | {r.median_mfe_mae_ratio:.3f} | {r.median_trigger_delay_min:.1f}m | {int(r.positive_pnl_years)}/5 | **{r.verdict}** |',
        '', '## Yearly economics','',
        '| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for _, y in yearly.iterrows():
        lines.append(f'| {int(y.year)} | {int(y.n)} | {y.wr60*100 if np.isfinite(y.wr60) else np.nan:.2f}% | {y.expectancy60_pct if np.isfinite(y.expectancy60_pct) else np.nan:.4f}% | {lib.pfmt(y.pf60)} | ${y.pnl60_usd:.2f} | {y.clean_up_impulse_rate*100 if np.isfinite(y.clean_up_impulse_rate) else np.nan:.2f}% | {y.median_mfe_mae_ratio if np.isfinite(y.median_mfe_mae_ratio) else np.nan:.3f} | {y.median_trigger_delay_min if np.isfinite(y.median_trigger_delay_min) else np.nan:.1f}m |')
    lines += ['', '## Frozen gate audit','']
    for gate in ('n_ge_100','expectancy_positive','pf_ge_1_15','positive_pnl_years_ge_4_of_5','median_mfe_mae_ge_1_20'):
        lines.append(f"- {'PASS' if bool(r['gate_'+gate]) else 'FAIL'} — {gate}")
    status = 'PASS_TO_CHARACTERIZATION' if r.verdict == 'PASS_TO_CHARACTERIZATION' else 'REJECTED_AS_DEFINED'
    lines += ['', 'OFFICIAL_VERDICT=' + status]
    (ROOT/f'{PFX}_Result.md').write_text('\n'.join(lines), encoding='utf-8')
    (ROOT/f'{PFX}_Status.txt').write_text('OFFICIAL_VERDICT='+status+'\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()