#!/usr/bin/env python3
from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_f85_long_single_position_portfolio_b27dg as dg

ROOT=Path(__file__).resolve().parent.parent
B27DG_SUM=ROOT/'BTC_F85_LONG_SINGLE_POSITION_PORTFOLIO_B27DG_Summary.csv'
OUT_MD=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_Result.md'
OUT_DETAIL=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_Detail.csv'
OUT_SUM=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_Summary.csv'
OUT_SEL=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_Selection.csv'
OUT_PORT=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_PortfolioSummary.csv'
OUT_PARITY=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_PrimaryParity.csv'
OUT_STATUS=ROOT/'BTC_F85_LONG_0530_2330_FILTER_B27DH_Status.txt'

PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
ZONES=('RAW_0530','RAW_2330')
HALF_MIN=195.0
RR_MIN=0.50
FILTERS=(
    'BASE',
    'TOUCH_FIRST_HALF',
    'TOUCH_SECOND_HALF',
    'K1_FIRST_HALF',
    'K1_SECOND_HALF',
    'RR_GE_050',
    'TOUCH_FIRST_HALF__RR_GE_050',
    'TOUCH_SECOND_HALF__RR_GE_050',
    'K1_FIRST_HALF__TOUCH_FIRST_HALF',
    'K1_SECOND_HALF__TOUCH_SECOND_HALF',
)


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'
def usd(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'


def load_enriched():
    c=dg.load().copy()
    c['k1_signal_ts']=pd.to_datetime(c['k1_signal_ts'],utc=True,errors='coerce')
    c['nominal_rr']=pd.to_numeric(c['nominal_rr'],errors='coerce')
    c['k1_elapsed_min']=(c.k1_signal_ts-c.execution_start)/pd.Timedelta(minutes=1)
    z=c[c.zone.isin(ZONES)].copy()
    assert z.k1_signal_ts.notna().all()
    assert z.nominal_rr.notna().all()
    assert (z.k1_elapsed_min>=0).all()
    assert (z.touch_elapsed_min>=0).all()
    return c


def close_enough(a,b):
    if pd.isna(b): return pd.isna(a)
    if math.isinf(float(b)): return math.isinf(float(a)) and ((float(a)>0)==(float(b)>0))
    return abs(float(a)-float(b)) <= 1e-9*max(1.0,abs(float(b)))


def primary_parity(c):
    persisted=pd.read_csv(B27DG_SUM)
    rows=[]
    for part in PARTS:
        g=c[(c.partition==part)&c.primary_eligible].copy()
        d=dg.lock(g,'PRIMARY_2ZONE')
        a=d[d.accepted]
        m=dg.metrics(a)
        q=persisted[(persisted.portfolio=='PRIMARY_2ZONE')&(persisted.partition==part)&persisted.zone.isna()]
        assert len(q)==1,(part,len(q))
        r=q.iloc[0]
        checks={
            'candidates':(len(d),int(r.candidates)),
            'accepted':(len(a),int(r.accepted)),
            'skipped_open':(int((~d.accepted).sum()),int(r.skipped_open)),
            'wr':(m['wr'],float(r.wr)),
            'pf':(m['pf'],float(r.pf)),
            'expectancy':(m['expectancy'],float(r.expectancy)),
            'total_net':(m['total_net'],float(r.total_net)),
        }
        for metric,(actual,expected) in checks.items():
            if metric in ('candidates','accepted','skipped_open'):
                ok=int(actual)==int(expected)
            else:
                ok=close_enough(actual,expected)
            rows.append({'partition':part,'metric':metric,'actual':actual,'expected':expected,'pass':ok})
    out=pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DH primary parity failed:\n'+out[~out['pass']].to_string(index=False))
    return out


def mask_for(g,name):
    m=pd.Series(True,index=g.index)
    if name=='BASE': return m
    if 'TOUCH_FIRST_HALF' in name: m &= g.touch_elapsed_min<=HALF_MIN
    if 'TOUCH_SECOND_HALF' in name: m &= g.touch_elapsed_min>HALF_MIN
    if 'K1_FIRST_HALF' in name: m &= g.k1_elapsed_min<=HALF_MIN
    if 'K1_SECOND_HALF' in name: m &= g.k1_elapsed_min>HALF_MIN
    if 'RR_GE_050' in name: m &= g.nominal_rr>=RR_MIN
    return m


def component_count(name):
    if name=='BASE': return 0
    return name.count('__')+1


def score_filter(c,zone,filt,part):
    raw=c[(c.partition==part)&(c.zone==zone)].copy()
    f=raw[mask_for(raw,filt)].copy()
    pri=c[(c.partition==part)&c.primary_eligible].copy()
    stream=pd.concat([pri,f],ignore_index=True)
    d=dg.lock(stream,f'PRIMARY_PLUS_{zone}_{filt}')
    az=d[(d.zone==zone)&d.accepted].copy()
    ap=d[d.accepted].copy()
    zm=dg.metrics(az); pm=dg.metrics(ap)
    return {
        'zone':zone,'filter':filt,'partition':part,
        'raw_n':len(raw),'filtered_n':len(f),'accepted_n':len(az),
        'blocked_open':len(f)-len(az),
        'filter_retention':len(f)/len(raw) if len(raw) else np.nan,
        'accepted_retention':len(az)/len(raw) if len(raw) else np.nan,
        'zone_wins':zm['wins'],'zone_wr':zm['wr'],'zone_pf':zm['pf'],
        'zone_expectancy':zm['expectancy'],'zone_total_net':zm['total_net'],
        'portfolio_candidates':len(d),'portfolio_accepted':len(ap),
        'portfolio_skipped_open':int((~d.accepted).sum()),
        'portfolio_wr':pm['wr'],'portfolio_pf':pm['pf'],
        'portfolio_expectancy':pm['expectancy'],'portfolio_total_net':pm['total_net'],
    }


def build_summary(c):
    rows=[]
    for zone in ZONES:
        for filt in FILTERS:
            for part in PARTS:
                rows.append(score_filter(c,zone,filt,part))
    return pd.DataFrame(rows)


def select_dev(s):
    rows=[]
    for zone in ZONES:
        d=s[(s.zone==zone)&(s.partition=='development')].copy()
        d['dev75']=(
            (d['filter']!='BASE') & (d.accepted_n>=20) &
            (d.accepted_retention>=.60) & (d.zone_wr>=.75) &
            (d.zone_pf>=1.30) & (d.zone_expectancy>0)
        )
        q=d[d.dev75].copy()
        if len(q):
            q['components']=q['filter'].map(component_count)
            q=q.sort_values(['zone_wr','zone_pf','zone_expectancy','accepted_retention','components','filter'],
                            ascending=[False,False,False,False,True,True])
            p=q.iloc[0]; label='DEV_75_SELECTED'
        else:
            q=d[(d['filter']!='BASE')&(d.accepted_n>=20)&(d.accepted_retention>=.60)&
                (d.zone_pf>=1.20)&(d.zone_expectancy>0)].copy()
            if len(q):
                q['components']=q['filter'].map(component_count)
                q=q.sort_values(['zone_wr','zone_pf','zone_expectancy','accepted_retention','components','filter'],
                                ascending=[False,False,False,False,True,True])
                p=q.iloc[0]; label='BEST_BELOW_75'
            else:
                p=d[d['filter']=='BASE'].iloc[0]; label='NO_FILTER_IMPROVEMENT'
        rows.append({
            'zone':zone,'selected_filter':p['filter'],'selection_label':label,
            'dev_raw_n':int(p.raw_n),'dev_filtered_n':int(p.filtered_n),'dev_accepted_n':int(p.accepted_n),
            'dev_accepted_retention':p.accepted_retention,'dev_wr':p.zone_wr,'dev_pf':p.zone_pf,
            'dev_expectancy':p.zone_expectancy,'dev_total_net':p.zone_total_net,
            'dev_portfolio_wr':p.portfolio_wr,'dev_portfolio_pf':p.portfolio_pf,
            'dev_portfolio_expectancy':p.portfolio_expectancy,'dev_portfolio_total_net':p.portfolio_total_net,
        })
    return pd.DataFrame(rows)


def add_replication(s,sel):
    out=sel.copy()
    reps=[]
    for r in out.itertuples(index=False):
        parts_ok=[]
        for part in ('external','reference_validation'):
            q=s[(s.zone==r.zone)&(s['filter']==r.selected_filter)&(s.partition==part)].iloc[0]
            ok=(q.accepted_n>=10 and q.accepted_retention>=.45 and q.zone_wr>=.70 and
                q.zone_pf>=1.20 and q.zone_expectancy>0)
            parts_ok.append(bool(ok))
            for k,v in {
                f'{part}_raw_n':q.raw_n,f'{part}_accepted_n':q.accepted_n,
                f'{part}_accepted_retention':q.accepted_retention,f'{part}_wr':q.zone_wr,
                f'{part}_pf':q.zone_pf,f'{part}_expectancy':q.zone_expectancy,
                f'{part}_total_net':q.zone_total_net,
            }.items(): out.loc[out.zone==r.zone,k]=v
        reps.append(bool(r.selection_label=='DEV_75_SELECTED' and all(parts_ok)))
    out['replication_supported']=reps
    return out


def selected_filter_map(sel,only_promoted=False):
    m={}
    for r in sel.itertuples(index=False):
        if only_promoted and not bool(r.replication_supported): continue
        m[r.zone]=r.selected_filter
    return m


def portfolio(c,filter_map,label):
    rows=[]; decisions=[]
    for part in PARTS:
        pri=c[(c.partition==part)&c.primary_eligible].copy()
        adds=[]
        for zone,filt in filter_map.items():
            raw=c[(c.partition==part)&(c.zone==zone)].copy()
            adds.append(raw[mask_for(raw,filt)].copy())
        stream=pd.concat([pri,*adds],ignore_index=True) if adds else pri.copy()
        d=dg.lock(stream,label); decisions.append(d)
        a=d[d.accepted]; m=dg.metrics(a)
        rows.append({'portfolio':label,'partition':part,'candidates':len(d),'accepted':len(a),
                     'skipped_open':int((~d.accepted).sum()),**m})
        for zone in ['LONDON','ALT_0330',*ZONES]:
            dz=d[d.zone==zone]
            if not len(dz): continue
            az=dz[dz.accepted]; zm=dg.metrics(az)
            rows.append({'portfolio':label,'partition':part,'zone':zone,'candidates':len(dz),
                         'accepted':len(az),'skipped_open':int((~dz.accepted).sum()),**zm})
    all_d=pd.concat(decisions,ignore_index=True)
    maj=all_d[all_d.partition.isin(MAJOR)]; a=maj[maj.accepted]; m=dg.metrics(a)
    rows.append({'portfolio':label,'partition':'POOLED_MAJOR','candidates':len(maj),'accepted':len(a),
                 'skipped_open':int((~maj.accepted).sum()),**m})
    for zone in ['LONDON','ALT_0330',*ZONES]:
        dz=maj[maj.zone==zone]
        if not len(dz): continue
        az=dz[dz.accepted]; zm=dg.metrics(az)
        rows.append({'portfolio':label,'partition':'POOLED_MAJOR','zone':zone,'candidates':len(dz),
                     'accepted':len(az),'skipped_open':int((~dz.accepted).sum()),**zm})
    return pd.DataFrame(rows),all_d


def write_result(s,sel,ports):
    lines=['# B27DH — F85 LONG 05:30 / 23:30 Zone-Specific Causal Filter Screen — Result','',
           '**Audit status: PASS.** B27DG PRIMARY_2ZONE was reproduced before B27DH interpretation.','',
           'All filter scores below are after combining the candidate with the frozen primary 03:30 + London stream and applying the global one-position lock. Development selection only; external/reference-validation are reused historical replication checks.','']
    for zone in ZONES:
        lines += [f'## {zone} — development','',
                  '| Filter | Raw N | Filtered | Accepted | Accept Retain | WR | PF | Exp | Net | 75% eligible |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
        d=s[(s.zone==zone)&(s.partition=='development')].copy()
        d['eligible']=(d['filter']!='BASE')&(d.accepted_n>=20)&(d.accepted_retention>=.60)&(d.zone_wr>=.75)&(d.zone_pf>=1.30)&(d.zone_expectancy>0)
        d=d.sort_values(['zone_wr','zone_pf'],ascending=False)
        for r in d.itertuples(index=False):
            lines.append(f'| {r.filter} | {int(r.raw_n)} | {int(r.filtered_n)} | {int(r.accepted_n)} | {pct(r.accepted_retention)} | {pct(r.zone_wr)} | {num(r.zone_pf)} | {usd(r.zone_expectancy)} | {usd(r.zone_total_net)} | {"YES" if r.eligible else "NO"} |')
        p=sel[sel.zone==zone].iloc[0]
        lines += ['',f"Selected: **{p.selected_filter}** — **{p.selection_label}**.",
                  f"Development accepted N={int(p.dev_accepted_n)}, retention={pct(p.dev_accepted_retention)}, WR={pct(p.dev_wr)}, PF={num(p.dev_pf)}, exp={usd(p.dev_expectancy)}, net={usd(p.dev_total_net)}.",'',
                  '| Partition | Raw N | Accepted | Retain | WR | PF | Exp | Net |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|']
        for part in PARTS:
            q=s[(s.zone==zone)&(s['filter']==p.selected_filter)&(s.partition==part)].iloc[0]
            lines.append(f'| {part} | {int(q.raw_n)} | {int(q.accepted_n)} | {pct(q.accepted_retention)} | {pct(q.zone_wr)} | {num(q.zone_pf)} | {usd(q.zone_expectancy)} | {usd(q.zone_total_net)} |')
        lines += ['',f"Historical replication supported: **{'YES' if bool(p.replication_supported) else 'NO'}**.",'']
    for label in ('PROMOTED_PORTFOLIO','EXPLORATORY_SELECTED_PORTFOLIO'):
        lines += [f'## {label}','','| Partition | Candidates | Accepted | Skipped open | WR | PF | Exp | Net |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|']
        for part in (*PARTS,'POOLED_MAJOR'):
            q=ports[(ports.portfolio==label)&(ports.partition==part)&ports.zone.isna()].iloc[0]
            lines.append(f'| {part} | {int(q.candidates)} | {int(q.accepted)} | {int(q.skipped_open)} | {pct(q.wr)} | {num(q.pf)} | {usd(q.expectancy)} | {usd(q.total_net)} |')
        lines += ['']
    nrep=int(sel.replication_supported.astype(bool).sum())
    if nrep==2: status='B27DH_BOTH_ZONES_REPLICATION_SUPPORTED'
    elif nrep==1: status='B27DH_ONE_ZONE_REPLICATION_SUPPORTED'
    elif (sel.selection_label=='DEV_75_SELECTED').any(): status='B27DH_DEV75_NOT_REPLICATED'
    elif (sel.selection_label=='BEST_BELOW_75').any(): status='B27DH_IMPROVEMENT_BELOW_75'
    else: status='B27DH_NO_FILTER_IMPROVEMENT'
    lines += ['## Status','',f'**{status}**','','No live BBC change is authorized. Research only.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n')


def main():
    c=load_enriched()
    par=primary_parity(c); par.to_csv(OUT_PARITY,index=False)
    detail=c[c.zone.isin(['LONDON','ALT_0330',*ZONES])].copy(); detail.to_csv(OUT_DETAIL,index=False)
    s=build_summary(c); s.to_csv(OUT_SUM,index=False)
    sel=add_replication(s,select_dev(s)); sel.to_csv(OUT_SEL,index=False)
    promoted=selected_filter_map(sel,only_promoted=True)
    exploratory=selected_filter_map(sel,only_promoted=False)
    p1,_=portfolio(c,promoted,'PROMOTED_PORTFOLIO')
    p2,_=portfolio(c,exploratory,'EXPLORATORY_SELECTED_PORTFOLIO')
    ports=pd.concat([p1,p2],ignore_index=True); ports.to_csv(OUT_PORT,index=False)
    write_result(s,sel,ports)
    print(OUT_MD.read_text())

if __name__=='__main__': main()
