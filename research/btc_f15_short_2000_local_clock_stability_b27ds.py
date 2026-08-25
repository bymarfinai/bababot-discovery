#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_generic_f15_short_clock_scan_b27dr as b27dr

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Result.md'
OUT_CASES = ROOT / 'BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Cases.csv'
OUT_SUM = ROOT / 'BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Summary.csv'
OUT_LEADER = ROOT / 'BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_DevelopmentLeaderboard.csv'
OUT_PARITY = ROOT / 'BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Status.txt'

CLOCKS = (1170,1180,1190,1200,1210,1220,1230)
BASE = 1200
PARTS = b27dr.PART_ORDER
MAJOR = b27dr.MAJOR


def eligible(r):
    return bool(int(r.trades)>=15 and pd.notna(r.wr) and r.wr>=.70 and
                pd.notna(r.pf) and r.pf>=1.50 and pd.notna(r.expectancy) and r.expectancy>0)


def neighbor_ok(r):
    return bool(int(r.trades)>=15 and pd.notna(r.wr) and r.wr>=.65 and
                pd.notna(r.pf) and r.pf>=1.20 and pd.notna(r.expectancy) and r.expectancy>0)


def replication(summary, clock):
    gates={'external':(15,.70,1.50),'reference_validation':(8,.70,1.50)}
    for part,(nmin,wrmin,pfmin) in gates.items():
        r=summary[(summary.clock_min==clock)&(summary.partition==part)].iloc[0]
        if not (int(r.trades)>=nmin and pd.notna(r.wr) and r.wr>=wrmin and
                pd.notna(r.pf) and r.pf>=pfmin and pd.notna(r.expectancy) and r.expectancy>0):
            return False
    return True


def parity(summary):
    exp={
      'external':(27,.7407407407407407,2.2216619995796045,31.351454448932472),
      'development':(19,.7894736842105263,3.9934463719694655,39.460641559222736),
      'reference_validation':(10,.8,2.6998163449196113,6.914226322564891),
      'august':(1,1.0,float('inf'),1.2403565717180713),
    }
    rows=[]
    for part,(n,wr,pf,net) in exp.items():
        r=summary[(summary.clock_min==BASE)&(summary.partition==part)].iloc[0]
        ok_n=int(r.trades)==n
        ok_wr=abs(float(r.wr)-wr)<1e-12
        ok_pf=(math.isinf(pf) and math.isinf(float(r.pf))) or abs(float(r.pf)-pf)<=.03
        ok_net=abs(float(r.total_net)-net)<=.15
        rows += [
          {'check':f'{part}_n','actual':r.trades,'expected':n,'pass':ok_n},
          {'check':f'{part}_wr','actual':r.wr,'expected':wr,'pass':ok_wr},
          {'check':f'{part}_pf','actual':r.pf,'expected':pf,'pass':ok_pf},
          {'check':f'{part}_net','actual':r.total_net,'expected':net,'pass':ok_net},
        ]
    out=pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DS 20:00 parity failed:\n'+out.to_string(index=False))
    return out


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.2f}'


def main():
    x5,coverage=b21.load5()
    anchors=pd.date_range(x5.index.min().normalize(),x5.index.max().normalize(),freq='D',tz='UTC')
    rows=[]
    for a in anchors:
        for c in CLOCKS:
            r=b27dr.build_case(x5,a,c)
            if r is not None: rows.append(r)
    cases=pd.DataFrame(rows)
    sums=[]
    for c in CLOCKS:
        rs,es,ee=b27dr.clock_label(c)
        for p in PARTS:
            g=cases[(cases.clock_min==c)&(cases.partition==p)]
            sums.append({'clock_min':c,'reference_start_utc':rs,'execution_start_utc':es,
                         'execution_end_utc':ee,'partition':p,**b27dr.summarize(g)})
    summary=pd.DataFrame(sums)
    par=parity(summary)

    dev=summary[summary.partition=='development'].copy()
    dev['eligible']=dev.apply(eligible,axis=1)
    dev['distance_from_2000']=abs(dev.clock_min-BASE)
    leader=dev.sort_values(['eligible','pf','wr','expectancy','trades','distance_from_2000','clock_min'],
                           ascending=[False,False,False,False,False,True,True]).reset_index(drop=True)
    q=leader[leader.eligible]
    selected=None if q.empty else q.iloc[0]
    basin=False; rep=False; selected_clock=None
    if selected is None:
        status='B27DS_NO_LOCAL_SHORT_CLOCK'
    else:
        selected_clock=int(selected.clock_min)
        neighbors=[]
        for n in (selected_clock-10,selected_clock+10):
            z=dev[dev.clock_min==n]
            if len(z): neighbors.append(bool(neighbor_ok(z.iloc[0])))
        basin=any(neighbors)
        if not basin:
            status='B27DS_LOCAL_CLOCK_ISOLATED'
        else:
            rep=replication(summary,selected_clock)
            status=('B27DS_LOCAL_BASIN_HISTORICAL_REPLICATION_SUPPORTED' if rep
                    else 'B27DS_LOCAL_BASIN_NOT_REPLICATED')

    cases.to_csv(OUT_CASES,index=False); summary.to_csv(OUT_SUM,index=False)
    leader.to_csv(OUT_LEADER,index=False); par.to_csv(OUT_PARITY,index=False)
    OUT_STATUS.write_text(status+'\n')

    lines=['# B27DS — F15 SHORT 20:00 UTC Local Clock Stability — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
           '**20:00 B27DR parity: PASS.**','',
           '## Development local-clock scan','',
           '| Ref | Exec | End | N | WR | PF | Exp | Net | H2/F15 | Eligible | Neighbor-support |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---|---|']
    for r in leader.itertuples(index=False):
        n_ok=neighbor_ok(pd.Series(r._asdict()))
        lines.append(f'| {r.reference_start_utc} | {r.execution_start_utc} | {r.execution_end_utc} | {r.trades} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {pct(r.h2_after_f15_touch_rate)} | {"YES" if r.eligible else "NO"} | {"YES" if n_ok else "NO"} |')

    lines += ['','## Selection','']
    if selected is None:
        lines.append('No local clock passed the frozen development candidate gate.')
    else:
        rs,es,ee=b27dr.clock_label(selected_clock)
        lines.append(f'Selected clock: **{rs} UTC reference -> {es}-{ee} UTC execution**.')
        lines.append(f'Development: N={int(selected.trades)}, WR={pct(selected.wr)}, PF={num(selected.pf)}, exp=${num(selected.expectancy)}, net=${num(selected.total_net)}.')
        lines.append(f'Immediate-neighbor local basin: **{"SUPPORTED" if basin else "NOT SUPPORTED"}**.')
        lines.append(f'Historical external + reference-validation replication: **{"SUPPORTED" if rep else "NOT SUPPORTED"}**.')
        lines += ['','| Partition | N | WR | PF | Exp | Net | H2/F15 | TP |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for p in PARTS:
            r=summary[(summary.clock_min==selected_clock)&(summary.partition==p)].iloc[0]
            lines.append(f'| {p} | {r.trades} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.total_net)} | {pct(r.h2_after_f15_touch_rate)} | {pct(r.tp_rate)} |')
        pooled=b27dr.summarize(cases[(cases.clock_min==selected_clock)&cases.partition.isin(MAJOR)])
        lines += ['','### Pooled major selected clock','',
                  f'N={pooled["trades"]}, wins={pooled["wins"]}, WR={pct(pooled["wr"])}, PF={num(pooled["pf"])}, expectancy=${num(pooled["expectancy"])}, net=${num(pooled["total_net"])}.']

    lines += ['',f'**Status: {status}**','',
              'Evidence remains exploratory historical discovery; not pristine unseen OOS. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
