#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_b27dx_pair_calibration_v2.py'
spec = importlib.util.spec_from_file_location('eth_v2_base', BASE_PATH)
b = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(b)

PFX = 'ETH_B27DX_S1A_NATIVE_LIFECYCLE_DURATION'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_PROBES = ROOT / f'{PFX}_ProbeScores.csv'
OUT_CELLS = ROOT / f'{PFX}_CellSummary.csv'
OUT_SUPPORTED = ROOT / f'{PFX}_SupportedCells.csv'
OUT_COMPONENTS = ROOT / f'{PFX}_Components.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

ANCHORS = (570, 960)  # 09:30, 16:00
REF_MINS = (120, 180, 240, 300, 330, 360)
HORIZON_MINS = (180, 240, 300, 360, 390, 420)
ENTRY_PROBES = (0.90, 0.85, 0.80)
TARGET_EXT = 0.20
STOP_F = 0.35
PARTS = ('development', 'external', 'reference_validation')
VAL_PARTS = ('external', 'reference_validation')


def clock_label(v: int) -> str:
    return f'{(v // 60) % 24:02d}:{v % 60:02d}'


def probe_label(f: float) -> str:
    return f'F{int(round(f*100)):02d}'


def finite_pf(v) -> float:
    if pd.isna(v):
        return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)


def score_probe(x, part: str, anchor: int, ref_min: int, horizon_min: int, ef: float) -> dict:
    r = b.score_config(
        x=x, part_name=part, side='LONG', exec_min=anchor,
        ref_min=ref_min, horizon_min=horizon_min, entry_f=ef,
        target_ext=TARGET_EXT, stop_f=STOP_F, stress_bps=0.0,
    )
    r['anchor_min'] = anchor
    r['anchor_utc'] = clock_label(anchor)
    r['reference_start_utc'] = clock_label((anchor-ref_min) % 1440)
    r['probe'] = probe_label(ef)
    if part == 'development':
        r['positive'] = bool(r['n'] >= 30 and r['pf'] >= 1.10 and r['expectancy'] > 0 and r['net'] > 0)
    else:
        r['positive'] = bool(r['n'] >= 15 and r['pf'] > 1.00 and r['expectancy'] > 0 and r['net'] > 0)
    return r


def run_scores(x) -> pd.DataFrame:
    rows=[]
    for anchor in ANCHORS:
        for ref_min in REF_MINS:
            for horizon_min in HORIZON_MINS:
                for part in PARTS:
                    for ef in ENTRY_PROBES:
                        rows.append(score_probe(x, part, anchor, ref_min, horizon_min, ef))
    return pd.DataFrame(rows)


def dev_weeks() -> float:
    a,z = b.m.m.PARTS['development']
    return float((z-a)/pd.Timedelta(days=7))


def summarize(scores: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    weeks=dev_weeks()
    for anchor in ANCHORS:
        for ref_min in REF_MINS:
            for horizon_min in HORIZON_MINS:
                d=scores[(scores.anchor_min==anchor)&(scores.ref_min==ref_min)&(scores.horizon_min==horizon_min)]
                row={
                    'anchor_min':anchor,'anchor_utc':clock_label(anchor),
                    'ref_min':ref_min,'horizon_min':horizon_min,
                    'reference_start_utc':clock_label((anchor-ref_min)%1440),
                }
                dev=d[d.partition=='development']
                row['development_positive_probes']=int(dev.positive.sum())
                row['development_pass']=bool(row['development_positive_probes']>=2)
                row['development_median_pf']=float(pd.Series([finite_pf(x) for x in dev.pf]).median())
                row['development_median_expectancy']=float(pd.to_numeric(dev.expectancy,errors='coerce').median())
                row['development_median_n']=float(pd.to_numeric(dev.n,errors='coerce').median())
                row['development_raw_opportunities_per_week']=row['development_median_n']/weeks
                for p in VAL_PARTS:
                    q=d[d.partition==p]
                    pos=int(q.positive.sum())
                    enough=int((pd.to_numeric(q.n,errors='coerce')>=15).sum())
                    row[f'{p}_positive_probes']=pos
                    row[f'{p}_enough_n_probes']=enough
                    row[f'{p}_pass']=bool(pos>=2 and enough>=2)
                row['supported']=bool(row['development_pass'] and row['external_pass'] and row['reference_validation_pass'])
                rows.append(row)
    return pd.DataFrame(rows)


def neighbor_cells(ref_min:int,horizon_min:int):
    ri=REF_MINS.index(ref_min); hi=HORIZON_MINS.index(horizon_min)
    out=[]
    for dr,dh in ((-1,0),(1,0),(0,-1),(0,1)):
        rj=ri+dr; hj=hi+dh
        if 0<=rj<len(REF_MINS) and 0<=hj<len(HORIZON_MINS):
            out.append((REF_MINS[rj],HORIZON_MINS[hj]))
    return out


def components_for_anchor(cells: pd.DataFrame, anchor:int):
    sup={(int(r.ref_min),int(r.horizon_min)) for r in cells[(cells.anchor_min==anchor)&cells.supported].itertuples(index=False)}
    comps=[]; seen=set()
    for cell in sorted(sup):
        if cell in seen: continue
        stack=[cell]; seen.add(cell); comp=[]
        while stack:
            u=stack.pop(); comp.append(u)
            for v in neighbor_cells(*u):
                if v in sup and v not in seen:
                    seen.add(v); stack.append(v)
        comps.append(sorted(comp))
    return comps


def component_table(cells:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for anchor in ANCHORS:
        for i,comp in enumerate(components_for_anchor(cells,anchor),1):
            refs=sorted({r for r,_ in comp}); horizons=sorted({h for _,h in comp})
            q=cells[(cells.anchor_min==anchor)&cells.apply(lambda x:(int(x.ref_min),int(x.horizon_min)) in set(comp),axis=1)]
            qualifies=len(comp)>=3 and len(refs)>=2 and len(horizons)>=2
            rows.append({
                'anchor_min':anchor,'anchor_utc':clock_label(anchor),'component_id':i,
                'cells':len(comp),'distinct_refs':len(refs),'distinct_horizons':len(horizons),
                'ref_values':','.join(map(str,refs)),'horizon_values':','.join(map(str,horizons)),
                'median_raw_opportunities_per_week':float(q.development_raw_opportunities_per_week.median()) if len(q) else np.nan,
                'qualifying_native_component':qualifies,
            })
    return pd.DataFrame(rows)


def fmt(x,nd=2):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.{nd}f}'


def main():
    x,coverage=b.m.m.load5()
    scores=run_scores(x); scores.to_csv(OUT_PROBES,index=False)
    cells=summarize(scores); cells.to_csv(OUT_CELLS,index=False)
    supported=cells[cells.supported].copy(); supported.to_csv(OUT_SUPPORTED,index=False)
    comps=component_table(cells); comps.to_csv(OUT_COMPONENTS,index=False)

    qualifying=bool(len(comps) and comps.qualifying_native_component.any())
    if supported.empty:
        status='ETH_S1A_NO_SUPPORTED_DURATION_CELL'
    elif qualifying:
        status='ETH_S1A_NATIVE_LIFECYCLE_SUPPORTED'
    else:
        status='ETH_S1A_SUPPORTED_CELLS_NO_2D_FAMILY'

    # identical supported duration cells across anchors
    sets={a:{(int(r.ref_min),int(r.horizon_min)) for r in supported[supported.anchor_min==a].itertuples(index=False)} for a in ANCHORS}
    overlap=sorted(sets[ANCHORS[0]] & sets[ANCHORS[1]])

    lines=[
        '# ETH B27DX — S1A Native Lifecycle Duration Discovery — Result','',
        f'ETH raw 5m coverage: **{coverage:.4%}**.','',
        'B27DX causal grammar, F90/F85/F80 probes, E20 target, F35 completed-close invalidation, fee/notional, and historical partitions are frozen. Only reference duration and execution lifespan vary.','',
        '## Supported structural cells','',
    ]
    if supported.empty:
        lines.append('None.')
    else:
        lines += ['| Anchor | Ref | Horizon | Ref start | Dev + | Dev PF | Ext + | Val + | Raw opp/week |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in supported.sort_values(['anchor_min','ref_min','horizon_min']).itertuples(index=False):
            lines.append(f'| {r.anchor_utc} | {int(r.ref_min)}m | {int(r.horizon_min)}m | {r.reference_start_utc} | {int(r.development_positive_probes)}/3 | {fmt(r.development_median_pf)} | {int(r.external_positive_probes)}/3 | {int(r.reference_validation_positive_probes)}/3 | {fmt(r.development_raw_opportunities_per_week,3)} |')

    lines += ['','## Connected duration components','']
    if comps.empty:
        lines.append('None.')
    else:
        lines += ['| Anchor | Component | Cells | Refs | Horizons | Median raw opp/week | Native 2D family |','|---:|---:|---:|---:|---:|---:|---|']
        for r in comps.itertuples(index=False):
            lines.append(f'| {r.anchor_utc} | {int(r.component_id)} | {int(r.cells)} | {r.ref_values} | {r.horizon_values} | {fmt(r.median_raw_opportunities_per_week,3)} | {"YES" if bool(r.qualifying_native_component) else "NO"} |')

    lines += ['','## Cross-anchor overlap','']
    if overlap:
        for ref_min,horizon_min in overlap:
            a=supported[(supported.anchor_min==ANCHORS[0])&(supported.ref_min==ref_min)&(supported.horizon_min==horizon_min)].iloc[0]
            z=supported[(supported.anchor_min==ANCHORS[1])&(supported.ref_min==ref_min)&(supported.horizon_min==horizon_min)].iloc[0]
            combined=float(a.development_raw_opportunities_per_week+z.development_raw_opportunities_per_week)
            lines.append(f'- R{ref_min}/X{horizon_min}: 09:30 **{a.development_raw_opportunities_per_week:.3f}/wk** + 16:00 **{z.development_raw_opportunities_per_week:.3f}/wk** = raw two-anchor **{combined:.3f}/wk**.')
    else:
        lines.append('No identical supported duration cell across both anchors.')

    legacy=cells[(cells.ref_min==330)&(cells.horizon_min==390)]
    lines += ['','## Legacy BTC-derived benchmark','']
    for r in legacy.itertuples(index=False):
        lines.append(f'- {r.anchor_utc} R330/X390: supported **{"YES" if bool(r.supported) else "NO"}**, raw opportunity density **{r.development_raw_opportunities_per_week:.3f}/wk**.')

    lines += ['','## Decision','',f'**Status: {status}**','',
              'Opportunity density is diagnostic only and never overrides the historical support gates.',
              'No entry/TP/stop/runner/leverage optimization and no live BBC changes were made.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
