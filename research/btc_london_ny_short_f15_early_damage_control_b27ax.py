#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
AT = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Trades.csv'
AW = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_PATH_SHAPE_B27AW_Features.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_DAMAGE_CONTROL_B27AX_Result.md'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_DAMAGE_CONTROL_B27AX_Summary.csv'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_DAMAGE_CONTROL_B27AX_Trades.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_DAMAGE_CONTROL_B27AX_Status.txt'

MAJOR = ('external','development','reference_validation')
HORIZONS = (5,10,15)
THRESHOLDS = (0.05,0.10,0.15,0.20,0.25)
FAMILIES = ('adverse_close_r','wick_imbalance_r')
NOTIONAL = 500.0
FEE = 0.40
BASE_TOTAL = -15.05841591698896
EPS = 1e-12
BAR5 = pd.Timedelta(minutes=5)


def to_bool(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() == 'true'


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def cid(family: str, horizon: int, threshold: float) -> str:
    fam = 'AC' if family == 'adverse_close_r' else 'WI'
    return f'{fam}_H{horizon:02d}_T{int(round(threshold*100)):02d}'


def early_net(entry: float, exit_px: float) -> float:
    return (1.0 - exit_px / entry) * NOTIONAL - FEE


def synthetic_tests() -> None:
    assert abs(early_net(100.0, 99.0) - 4.60) < 1e-12
    assert early_net(100.0, 101.0) < 0
    assert cid('adverse_close_r',10,.15) == 'AC_H10_T15'
    assert cid('wick_imbalance_r',5,.05) == 'WI_H05_T05'


def summarize(g: pd.DataFrame) -> dict:
    vals = pd.to_numeric(g.net_pnl_usd, errors='coerce')
    return {
        'n':len(g),
        'wr':float((vals > 0).mean()) if len(g) else np.nan,
        'pf':pf(vals),
        'expectancy':float(vals.mean()) if len(g) else np.nan,
        'total_pnl':float(vals.sum()) if len(g) else np.nan,
        'early_cut_n':int(g.early_cut.sum()) if len(g) else 0,
        'cut_baseline_winner_n':int((g.early_cut & g.baseline_win).sum()) if len(g) else 0,
        'cut_baseline_e20_n':int((g.early_cut & g.baseline_activated).sum()) if len(g) else 0,
        'early_cut_total_pnl':float(g.loc[g.early_cut,'net_pnl_usd'].sum()) if len(g) else 0.0,
        'same_as_baseline_n':int((~g.early_cut).sum()) if len(g) else 0,
    }


def main() -> None:
    synthetic_tests()
    x5, coverage = b21.load5()
    assert len(x5) == 698112, len(x5)
    assert abs(float(coverage)-1.0) < 1e-12

    at = pd.read_csv(AT)
    at = at[(at.activation.astype(str) == 'E20') & at.partition.isin(MAJOR)].copy()
    for c in ('signal_ts','entry_start','exit_ts','session_end'):
        at[c] = pd.to_datetime(at[c], utc=True, errors='raise')
    for c in ('activated','win'):
        at[c] = at[c].map(to_bool)
    for c in ('entry_px','net_pnl_usd','range'):
        at[c] = pd.to_numeric(at[c], errors='raise')
    at = at.sort_values(['partition','entry_start']).reset_index(drop=True)

    assert len(at) == 163
    assert abs(float(at.net_pnl_usd.sum()) - BASE_TOTAL) < 1e-9
    assert int(at.activated.sum()) == 92

    aw = pd.read_csv(AW)
    aw = aw[aw.partition.isin(MAJOR) & aw.horizon_minutes.isin(HORIZONS)].copy()
    for c in ('signal_ts','entry_start','horizon_end'):
        aw[c] = pd.to_datetime(aw[c], utc=True, errors='raise')
    for c in ('adverse_close_r','adverse_wick_r','favorable_wick_r'):
        aw[c] = pd.to_numeric(aw[c], errors='raise')
    aw['wick_imbalance_r'] = aw.adverse_wick_r - aw.favorable_wick_r
    assert not aw.duplicated(['partition','signal_ts','entry_start','horizon_minutes']).any()

    # Baseline identity map.
    base_cols = ['partition','signal_ts','entry_start','entry_px','activated','win','net_pnl_usd','exit_ts','exit_px','exit_reason']
    base = at[base_cols].copy().rename(columns={
        'activated':'baseline_activated','win':'baseline_win','net_pnl_usd':'baseline_pnl',
        'exit_ts':'baseline_exit_ts','exit_px':'baseline_exit_px','exit_reason':'baseline_exit_reason',
    })

    trade_rows=[]
    summary_rows=[]
    for family in FAMILIES:
        for horizon in HORIZONS:
            f = aw[aw.horizon_minutes == horizon][['partition','signal_ts','entry_start','horizon_end',family]].copy()
            for threshold in THRESHOLDS:
                candidate = cid(family,horizon,threshold)
                z = base.merge(f, on=['partition','signal_ts','entry_start'], how='left', validate='one_to_one')
                z['candidate'] = candidate
                z['family'] = family
                z['horizon_minutes'] = horizon
                z['threshold'] = threshold
                z['feature_value'] = pd.to_numeric(z[family], errors='coerce')
                z['at_risk'] = z.horizon_end.notna()
                z['early_cut'] = z.at_risk & (z.feature_value >= threshold - EPS)
                z['exit_px'] = z.baseline_exit_px.astype(float)
                z['exit_ts'] = z.baseline_exit_ts
                z['exit_reason'] = z.baseline_exit_reason.astype(str)
                z['net_pnl_usd'] = z.baseline_pnl.astype(float)

                for i in z.index[z.early_cut]:
                    hend = pd.Timestamp(z.at[i,'horizon_end'])
                    bar_start = hend - BAR5
                    if bar_start not in x5.index:
                        raise AssertionError(('missing horizon bar',candidate,z.at[i,'partition'],hend))
                    px = float(x5.loc[bar_start,'close'])
                    entry = float(z.at[i,'entry_px'])
                    z.at[i,'exit_px'] = px
                    z.at[i,'exit_ts'] = hend
                    z.at[i,'exit_reason'] = f'EARLY_DAMAGE_{family}_{horizon}m_{threshold:.2f}'
                    z.at[i,'net_pnl_usd'] = early_net(entry,px)
                    # Original baseline must genuinely still have been open at the decision time.
                    assert pd.Timestamp(z.at[i,'baseline_exit_ts']) > hend

                z['pnl_delta_vs_baseline'] = z.net_pnl_usd.astype(float) - z.baseline_pnl.astype(float)
                z['win'] = z.net_pnl_usd.astype(float) > 0
                trade_rows.append(z.copy())

                for part in (*MAJOR,'POOLED_MAJOR'):
                    g = z if part == 'POOLED_MAJOR' else z[z.partition == part]
                    s = summarize(g)
                    s.update({
                        'candidate':candidate,'family':family,'horizon_minutes':horizon,
                        'threshold':threshold,'partition':part,
                        'pnl_delta_vs_baseline':float(g.pnl_delta_vs_baseline.sum()),
                        'at_risk_n':int(g.at_risk.sum()),
                    })
                    summary_rows.append(s)

    tr = pd.concat(trade_rows, ignore_index=True)
    sm = pd.DataFrame(summary_rows)
    assert len(sm[sm.partition=='POOLED_MAJOR']) == 30

    # Promotion gate frozen in preregistration.
    eligible=[]
    for candidate in sm.candidate.unique():
        pool = sm[(sm.candidate==candidate)&(sm.partition=='POOLED_MAJOR')].iloc[0]
        ok = float(pool.total_pnl) > BASE_TOTAL and float(pool.expectancy) > 0
        for part in MAJOR:
            r = sm[(sm.candidate==candidate)&(sm.partition==part)].iloc[0]
            ok = ok and float(r.expectancy) >= 0 and float(r.pf) >= 1.0
        if ok:
            eligible.append(candidate)

    pool = sm[sm.partition=='POOLED_MAJOR'].copy()
    pool['eligible'] = pool.candidate.isin(eligible)
    # Diagnostic best = pooled total only. Formal selection applies gate + frozen tie-break.
    diag = pool.sort_values(['total_pnl','horizon_minutes','threshold','family'], ascending=[False,True,False,True]).iloc[0]
    selected = 'NONE'
    if eligible:
        eg = pool[pool.eligible].sort_values(['total_pnl','horizon_minutes','threshold','family'], ascending=[False,True,False,True])
        selected = str(eg.iloc[0].candidate)

    status = f'B27AX_SELECTED_{selected}__DIAGNOSTIC_BEST_{diag.candidate}'
    OUT_STATUS.write_text(status+'\n')
    tr.to_csv(OUT_TRADES,index=False)
    sm.to_csv(OUT_SUM,index=False)

    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'
    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'

    md=[
        '# B27AX — BTC London->NY SHORT F15 Early Damage-Control Threshold Map — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Frozen B27AT E20 baseline reproduced exactly before any early-exit candidate was interpreted.','',
        f'Frozen pooled-major baseline: N=163, E20 activated=92, total **${BASE_TOTAL:+.3f}**.','',
        'Each candidate is one independent decision at 5m, 10m, or 15m after the fill bar; if H2 had already occurred or the baseline trade had exited, that trade cannot be early-cut.','',
        '## Pooled-major map','',
        '| Candidate | Feature | Horizon | Threshold | At risk | Cuts | Cut baseline winners | Cut baseline E20 | WR | PF | Exp/trade $ | Total $ | Delta vs baseline | Eligible |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|'
    ]
    ps = pool.sort_values(['family','horizon_minutes','threshold'])
    for r in ps.itertuples(index=False):
        md.append(f'| {r.candidate} | {r.family} | {int(r.horizon_minutes)}m | {r.threshold:.2f}R | {int(r.at_risk_n)} | {int(r.early_cut_n)} | {int(r.cut_baseline_winner_n)} | {int(r.cut_baseline_e20_n)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {num(r.pnl_delta_vs_baseline)} | {"YES" if r.eligible else "NO"} |')

    md += ['','## Best diagnostic candidate and formal selection','',
           f'Diagnostic best pooled total: **{diag.candidate}** ({diag.family}, {int(diag.horizon_minutes)}m, threshold {float(diag.threshold):.2f}R) → total **${float(diag.total_pnl):+.3f}**, delta **${float(diag.pnl_delta_vs_baseline):+.3f}** vs baseline.','',
           f'Formal selected candidate under the preregistered cross-partition gate: **{selected}**.','']

    if selected != 'NONE':
        md += ['### Selected candidate by partition','',
               '| Partition | N | WR | PF | Exp/trade $ | Total $ | Cuts | Cut baseline winners | Cut baseline E20 |',
               '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for part in (*MAJOR,'POOLED_MAJOR'):
            r=sm[(sm.candidate==selected)&(sm.partition==part)].iloc[0]
            md.append(f'| {part} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {int(r.early_cut_n)} | {int(r.cut_baseline_winner_n)} | {int(r.cut_baseline_e20_n)} |')
    else:
        md += ['No candidate satisfied the frozen requirement of positive pooled expectancy plus non-negative expectancy and PF>=1.0 in every major partition.']

    md += ['','No thresholds outside the preregistered coarse grid were tested. No feature combination, regime filter, F15/F65/E20 change, runner change, or live BBC change was made.','',f'**Status:** `{status}`']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
