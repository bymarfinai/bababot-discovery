#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_4h_regime_alignment_b27ag as ag

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Cases.csv'
B27DE_SUM = ROOT / 'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Summary.csv'
OUT_MD = ROOT / 'BTC_F85_LONG_ZONE_FILTER_B27DF_Result.md'
OUT_DETAIL = ROOT / 'BTC_F85_LONG_ZONE_FILTER_B27DF_Detail.csv'
OUT_SUM = ROOT / 'BTC_F85_LONG_ZONE_FILTER_B27DF_Summary.csv'
OUT_SEL = ROOT / 'BTC_F85_LONG_ZONE_FILTER_B27DF_Selection.csv'
OUT_PARITY = ROOT / 'BTC_F85_LONG_ZONE_FILTER_B27DF_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F85_LONG_ZONE_FILTER_B27DF_Status.txt'

PARTS = ('external','development','reference_validation','august')
ZONES = {'LONDON': 480, 'ALT_0330': 210}
EXEC_HALF_MIN = 195.0
RR_MIN = 0.50

FILTERS = (
    'BASE',
    'NO_BEAR',
    'TOUCH_FIRST_HALF',
    'RR_GE_050',
    'NO_BEAR__TOUCH_FIRST_HALF',
    'NO_BEAR__RR_GE_050',
    'TOUCH_FIRST_HALF__RR_GE_050',
    'TRIPLE_NO_BEAR__TOUCH_FIRST_HALF__RR_GE_050',
)


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().eq('true')


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def fmt_pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def fmt_num(x, d=2):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.{d}f}'


def fmt_usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def load_base_trades() -> pd.DataFrame:
    c = pd.read_csv(CASES)
    for col in ('k1_signal_ts','execution_start','touch_bar_start','entry_bar_start','exit_ts'):
        c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    c['entry_executed_b'] = as_bool(c.entry_executed)
    c['tp_hit_b'] = as_bool(c.tp_hit)
    c['time_exit_b'] = as_bool(c.time_exit)
    c['clock_min'] = pd.to_numeric(c.clock_min, errors='coerce').astype('Int64')
    c['net_pnl_usd'] = pd.to_numeric(c.net_pnl_usd, errors='coerce')
    c['nominal_rr'] = pd.to_numeric(c.nominal_rr, errors='coerce')
    z = c[c.clock_min.isin(ZONES.values()) & c.entry_executed_b & c.net_pnl_usd.notna()].copy()
    inv = {v:k for k,v in ZONES.items()}
    z['zone'] = z.clock_min.map(inv)
    assert z.zone.notna().all()
    assert z.k1_signal_ts.notna().all() and z.touch_bar_start.notna().all()
    assert z.execution_start.notna().all() and z.nominal_rr.notna().all()
    z['trade_key'] = z.zone.astype(str) + '|' + z.partition.astype(str) + '|' + z.entry_bar_start.astype(str)
    assert not z.trade_key.duplicated().any()
    return z


def summarize_raw(g: pd.DataFrame) -> dict:
    v = pd.to_numeric(g.net_pnl_usd, errors='coerce')
    return {
        'n': int(len(g)),
        'wins': int((v > 0).sum()),
        'wr': float((v > 0).mean()) if len(g) else np.nan,
        'pf': pf(v) if len(g) else np.nan,
        'expectancy': float(v.mean()) if len(g) else np.nan,
        'total_net': float(v.sum()) if len(g) else 0.0,
        'tp_rate': float(g.tp_hit_b.mean()) if len(g) else np.nan,
        'time_exit_rate': float(g.time_exit_b.mean()) if len(g) else np.nan,
    }


def parity(base: pd.DataFrame) -> pd.DataFrame:
    persisted = pd.read_csv(B27DE_SUM)
    rows=[]
    for zone, cm in ZONES.items():
        for part in PARTS:
            g=base[(base.zone==zone)&(base.partition==part)]
            m=summarize_raw(g)
            q=persisted[(pd.to_numeric(persisted.clock_min)==cm)&(persisted.partition==part)]
            assert len(q)==1, (zone,part,len(q))
            r=q.iloc[0]
            checks={
                'n': (m['n'], int(r.trades)),
                'wins': (m['wins'], int(r.wins)),
                'wr': (m['wr'], float(r.wr) if pd.notna(r.wr) else np.nan),
                'pf': (m['pf'], float(r.pf) if pd.notna(r.pf) else np.nan),
                'expectancy': (m['expectancy'], float(r.expectancy) if pd.notna(r.expectancy) else np.nan),
                'total_net': (m['total_net'], float(r.total_net)),
            }
            for metric,(actual,expected) in checks.items():
                if pd.isna(expected): ok=pd.isna(actual)
                elif metric in ('n','wins'): ok=int(actual)==int(expected)
                else: ok=abs(float(actual)-float(expected)) <= 1e-9*max(1.0,abs(float(expected)))
                rows.append({'zone':zone,'partition':part,'metric':metric,'actual':actual,'expected':expected,'pass':ok})
    out=pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DF B27DE parity failed:\n'+out[~out['pass']].to_string(index=False))
    return out


def enrich_features(base: pd.DataFrame) -> pd.DataFrame:
    x5, coverage = ag.b21.load5()
    if coverage < .995:
        raise AssertionError('coverage too low')
    reg = ag.build_regime(x5)
    z=base.copy()
    regimes=[]; regime_bars=[]; regime_av=[]
    for r in z.itertuples(index=False):
        state, rb, av = ag.state_at(reg, pd.Timestamp(r.k1_signal_ts))
        regimes.append(state); regime_bars.append(rb); regime_av.append(av)
    z['regime_at_signal']=regimes
    z['regime_bar_start']=regime_bars
    z['regime_available_ts']=regime_av
    assert (pd.to_datetime(z.regime_available_ts,utc=True) <= pd.to_datetime(z.k1_signal_ts,utc=True)).all()
    z['touch_elapsed_min']=(z.touch_bar_start-z.execution_start)/pd.Timedelta(minutes=1)
    assert (z.touch_elapsed_min >= 0).all()
    z['no_bear']=z.regime_at_signal.ne('BEAR')
    z['touch_first_half']=z.touch_elapsed_min <= EXEC_HALF_MIN
    z['rr_ge_050']=z.nominal_rr >= RR_MIN
    return z


def mask_for(g: pd.DataFrame, name: str) -> pd.Series:
    t=pd.Series(True,index=g.index)
    if 'NO_BEAR' in name: t &= g.no_bear
    if 'TOUCH_FIRST_HALF' in name: t &= g.touch_first_half
    if 'RR_GE_050' in name: t &= g.rr_ge_050
    return t


def build_summary(z: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    base_counts={(zone,part):len(z[(z.zone==zone)&(z.partition==part)]) for zone in ZONES for part in PARTS}
    for zone in ZONES:
        for filt in FILTERS:
            for part in PARTS:
                b=z[(z.zone==zone)&(z.partition==part)]
                g=b[mask_for(b,filt)]
                m=summarize_raw(g)
                bn=base_counts[(zone,part)]
                rows.append({'zone':zone,'filter':filt,'partition':part,'base_n':bn,
                             'retention':float(len(g)/bn) if bn else np.nan,**m})
    return pd.DataFrame(rows)


def component_count(name: str) -> int:
    if name=='BASE': return 0
    return int('NO_BEAR' in name)+int('TOUCH_FIRST_HALF' in name)+int('RR_GE_050' in name)


def select_dev(summary: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for zone in ZONES:
        d=summary[(summary.zone==zone)&(summary.partition=='development')].copy()
        d['dev_75_eligible']=(
            (d['filter']!='BASE') &
            (d.n>=20) & (d.retention>=.60) &
            (d.wr>=.75) & (d.pf>=1.30) & (d.expectancy>0)
        )
        q=d[d.dev_75_eligible].copy()
        if len(q):
            q['components']=q['filter'].map(component_count)
            q=q.sort_values(['wr','pf','expectancy','retention','components','filter'],ascending=[False,False,False,False,True,True])
            pick=q.iloc[0]
            label='DEV_75_SELECTED'
        else:
            q=d[(d['filter']!='BASE')&(d.n>=20)&(d.retention>=.60)&(d.pf>=1.20)&(d.expectancy>0)].copy()
            if len(q):
                q['components']=q['filter'].map(component_count)
                q=q.sort_values(['wr','pf','expectancy','retention','components','filter'],ascending=[False,False,False,False,True,True])
                pick=q.iloc[0]; label='BEST_BELOW_75'
            else:
                pick=d[d['filter']=='BASE'].iloc[0]; label='NO_FILTER_IMPROVEMENT'
        rows.append({'zone':zone,'selected_filter':pick['filter'],'selection_label':label,
                     'dev_n':int(pick.n),'dev_retention':pick.retention,'dev_wr':pick.wr,
                     'dev_pf':pick.pf,'dev_expectancy':pick.expectancy,'dev_total_net':pick.total_net})
    return pd.DataFrame(rows)


def replication(summary: pd.DataFrame, sel: pd.DataFrame) -> pd.DataFrame:
    out=sel.copy()
    reps=[]
    for r in out.itertuples(index=False):
        ok = r.selection_label=='DEV_75_SELECTED'
        details=[]
        for part in ('external','reference_validation'):
            q=summary[(summary.zone==r.zone)&(summary['filter']==r.selected_filter)&(summary.partition==part)].iloc[0]
            part_ok=(q.n>=10 and q.retention>=.45 and q.wr>=.70 and q.pf>=1.20 and q.expectancy>0)
            details.append(part_ok)
            out.loc[out.zone==r.zone,f'{part}_n']=int(q.n)
            out.loc[out.zone==r.zone,f'{part}_retention']=q.retention
            out.loc[out.zone==r.zone,f'{part}_wr']=q.wr
            out.loc[out.zone==r.zone,f'{part}_pf']=q.pf
            out.loc[out.zone==r.zone,f'{part}_expectancy']=q.expectancy
            out.loc[out.zone==r.zone,f'{part}_total_net']=q.total_net
        reps.append(bool(ok and all(details)))
    out['replication_supported']=reps
    return out


def write_result(summary, selection, parity_df, detail):
    lines=['# B27DF — F85 LONG Zone-Specific Causal Filter Screen — Result','',
           '**Audit status: PASS.** B27DE BASE cohorts/economics reproduced exactly before filter interpretation.','',
           'Filter menu was frozen before results: NO_BEAR, first-half touch, nominal RR >= 0.50, and their predeclared combinations. Development selects separately per zone; external/reference-validation are replication checks.','']
    for zone in ZONES:
        lines += [f'## {zone} — development filter table','',
                  '| Filter | N | Retain | WR | PF | Exp | Net | 75% eligible |',
                  '|---|---:|---:|---:|---:|---:|---:|---|']
        d=summary[(summary.zone==zone)&(summary.partition=='development')].copy()
        d['eligible']=(d['filter']!='BASE')&(d.n>=20)&(d.retention>=.60)&(d.wr>=.75)&(d.pf>=1.30)&(d.expectancy>0)
        d=d.sort_values(['wr','pf'],ascending=False)
        for r in d.itertuples(index=False):
            lines.append(f'| {r.filter} | {r.n} | {fmt_pct(r.retention)} | {fmt_pct(r.wr)} | {fmt_num(r.pf)} | {fmt_usd(r.expectancy)} | {fmt_usd(r.total_net)} | {"YES" if r.eligible else "NO"} |')
        pick=selection[selection.zone==zone].iloc[0]
        lines += ['',f"Selected development treatment: **{pick.selected_filter}** — {pick.selection_label}.",
                  f"Development: N={int(pick.dev_n)}, retention={fmt_pct(pick.dev_retention)}, WR={fmt_pct(pick.dev_wr)}, PF={fmt_num(pick.dev_pf)}, exp={fmt_usd(pick.dev_expectancy)}, net={fmt_usd(pick.dev_total_net)}.",'',
                  '| Partition | N | Retain | WR | PF | Exp | Net |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for part in ('external','development','reference_validation','august'):
            q=summary[(summary.zone==zone)&(summary['filter']==pick.selected_filter)&(summary.partition==part)].iloc[0]
            lines.append(f'| {part} | {q.n} | {fmt_pct(q.retention)} | {fmt_pct(q.wr)} | {fmt_num(q.pf)} | {fmt_usd(q.expectancy)} | {fmt_usd(q.total_net)} |')
        lines += ['',f"Historical replication supported: **{'YES' if bool(pick.replication_supported) else 'NO'}**.",'']
    supported=selection[selection.replication_supported.astype(bool)]
    if len(supported): status='B27DF_75_FILTER_REPLICATION_SUPPORTED'
    elif (selection.selection_label=='DEV_75_SELECTED').any(): status='B27DF_75_DEV_ONLY_NOT_REPLICATED'
    elif (selection.selection_label=='BEST_BELOW_75').any(): status='B27DF_IMPROVEMENT_BELOW_75'
    else: status='B27DF_NO_FILTER_IMPROVEMENT'
    lines += ['## Overall status','',f'**{status}**','',
              'Guardrail: a development-only WR increase is not accepted if it fails external/reference-validation replication. No live BBC change is authorized.','',
              'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(status+'\n')


def main():
    base=load_base_trades()
    par=parity(base)
    par.to_csv(OUT_PARITY,index=False)
    detail=enrich_features(base)
    detail.to_csv(OUT_DETAIL,index=False)
    summary=build_summary(detail)
    summary.to_csv(OUT_SUM,index=False)
    sel=select_dev(summary)
    sel=replication(summary,sel)
    sel.to_csv(OUT_SEL,index=False)
    write_result(summary,sel,par,detail)
    print(OUT_MD.read_text())


if __name__=='__main__':
    main()
