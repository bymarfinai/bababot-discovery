#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_full_loser_separability_b27cv as cv

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Result.md'
OUT_MET=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Metrics.csv'
OUT_CLOCK=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Clock.csv'
OUT_REGIME=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Regime.csv'
OUT_TRANS=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Transitions.csv'
OUT_FLAGS=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Flags.csv'
OUT_STATUS=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_FULL_LOSER_SEQUENTIAL_B27CX_Audit.txt'

EPS=1e-12
T10_SAFE=0.5898635948838399
T15_SAFE=0.6079191233470493
T10_AGG=0.5494693389519317
T15_AGG=0.4101988544354365
CLOCKS=cv.CLOCKS
WIB=cv.WIB
REGIMES=cv.REGIMES


def flag(prob, eligible, th):
    p=pd.to_numeric(prob,errors='coerce')
    return eligible.astype(bool) & p.notna() & ((p + EPS) >= float(th))


def prepare_join(sc):
    a=sc[sc.checkpoint.eq('PLUS10')].copy()
    b=sc[sc.checkpoint.eq('PLUS15')].copy()
    keep=['event_id','partition','clock_block','regime','label','bad_prob','model_eligible','resolved_before_or_at']
    a=a[keep].rename(columns={'bad_prob':'p10','model_eligible':'elig10','resolved_before_or_at':'resolved10'})
    b=b[keep].rename(columns={'bad_prob':'p15','model_eligible':'elig15','resolved_before_or_at':'resolved15'})
    d=a.merge(b,on=['event_id','partition','clock_block','regime','label'],how='inner',validate='one_to_one')
    assert len(d)==652,len(d)
    d['f10_safe']=flag(d.p10,d.elig10,T10_SAFE)
    d['f15_safe']=flag(d.p15,d.elig15,T15_SAFE)
    d['f10_agg']=flag(d.p10,d.elig10,T10_AGG)
    d['f15_agg']=flag(d.p15,d.elig15,T15_AGG)
    d['safe_persist']=d.f10_safe & d.f15_safe
    d['agg_persist']=d.f10_agg & d.f15_agg
    return d


def metrics(d,rule):
    bad=d.label.eq('BAD'); good=d.label.eq('GOOD')
    bt=int(bad.sum()); gt=int(good.sum())
    too=int((bad & ~d.elig15.astype(bool)).sum())
    resolved=int((good & ~d.elig15.astype(bool)).sum())
    if rule=='PLUS10_SAFE': f=d.f10_safe
    elif rule=='PLUS15_SAFE': f=d.f15_safe
    elif rule=='SAFE_PERSIST_10_15': f=d.safe_persist
    elif rule=='AGG_PERSIST_10_15': f=d.agg_persist
    else: raise KeyError(rule)
    bf=int((bad&f).sum()); gf=int((good&f).sum()); fn=bf+gf
    return {
        'bad_total':bt,'bad_too_late_by15':too,'bad_flagged':bf,
        'bad_capture':bf/bt if bt else np.nan,
        'good_total':gt,'good_resolved_before15':resolved,'good_flagged':gf,
        'good_sacrifice':gf/gt if gt else np.nan,
        'flagged_n':fn,'flag_precision_bad':bf/fn if fn else np.nan,
    }


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def main():
    trades=cv.load_trades(); x5,cov=b21.load5()
    assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    h1=cv.build_h1(x5); feats=cv.make_features(trades,x5,h1)
    sc,thr,coef,models=cv.score_all(feats)

    t10=thr[thr.checkpoint.eq('PLUS10')]
    t15=thr[thr.checkpoint.eq('PLUS15')]
    s10=t10[t10['mode'].eq('SAFE')].iloc[0]; a10=t10[t10['mode'].eq('AGGRESSIVE')].iloc[0]
    s15=t15[t15['mode'].eq('SAFE')].iloc[0]; a15=t15[t15['mode'].eq('AGGRESSIVE')].iloc[0]
    assert abs(float(s10.development_auc)-0.8452298452298452)<1e-12
    assert abs(float(s15.development_auc)-0.8860088365243004)<1e-12
    assert abs(float(s10.threshold)-T10_SAFE)<1e-10
    assert abs(float(s15.threshold)-T15_SAFE)<1e-10
    assert abs(float(a10.threshold)-T10_AGG)<1e-10
    assert abs(float(a15.threshold)-T15_AGG)<1e-10

    d=prepare_join(sc)
    assert int(d.label.eq('BAD').sum())==78
    assert int(d.label.eq('GOOD').sum())==348
    assert int(d.label.eq('OTHER').sum())==226

    # Reproduce parent +15 SAFE boundary counts with inclusive numerical tolerance.
    dev=d[d.partition.eq('development')]
    parent_dev=metrics(dev,'PLUS15_SAFE')
    assert parent_dev['bad_flagged']==28,parent_dev
    assert parent_dev['good_flagged']==9,parent_dev

    scopes=[
        ('development',d[d.partition.eq('development')]),
        ('external',d[d.partition.eq('external')]),
        ('reference_validation',d[d.partition.eq('reference_validation')]),
        ('POOLED_REUSED_EXTVAL',d[d.partition.isin(['external','reference_validation'])]),
        ('POOLED_MAJOR',d),
    ]
    rows=[]
    for name,z in scopes:
        for rule in ('PLUS10_SAFE','PLUS15_SAFE','SAFE_PERSIST_10_15','AGG_PERSIST_10_15'):
            rows.append({'scope':name,'rule':rule,**metrics(z,rule)})
    met=pd.DataFrame(rows); met.to_csv(OUT_MET,index=False)

    # Six clocks independently, all partitions and pooled major.
    crows=[]
    for cb in CLOCKS:
        for part,z0 in [('development',d[d.partition.eq('development')]),('external',d[d.partition.eq('external')]),('reference_validation',d[d.partition.eq('reference_validation')]),('POOLED_MAJOR',d)]:
            z=z0[z0.clock_block.eq(cb)]
            crows.append({'clock_block':cb,'wib':WIB[cb],'partition':part,**metrics(z,'SAFE_PERSIST_10_15')})
    clock=pd.DataFrame(crows); clock.to_csv(OUT_CLOCK,index=False)

    rrows=[]
    for rg in REGIMES:
        for part,z0 in [('development',d[d.partition.eq('development')]),('external',d[d.partition.eq('external')]),('reference_validation',d[d.partition.eq('reference_validation')]),('POOLED_MAJOR',d)]:
            z=z0[z0.regime.eq(rg)]
            rrows.append({'regime':rg,'partition':part,**metrics(z,'SAFE_PERSIST_10_15')})
    reg=pd.DataFrame(rrows); reg.to_csv(OUT_REGIME,index=False)

    # SAFE transition states among BAD/GOOD trades alive at +15.
    tr=[]
    for part,z0 in [('development',d[d.partition.eq('development')]),('external',d[d.partition.eq('external')]),('reference_validation',d[d.partition.eq('reference_validation')]),('POOLED_REUSED_EXTVAL',d[d.partition.isin(['external','reference_validation'])]),('POOLED_MAJOR',d)]:
        z=z0[z0.label.isin(['BAD','GOOD']) & z0.elig15.astype(bool)].copy()
        state=np.select([
            z.f10_safe & z.f15_safe,
            z.f10_safe & ~z.f15_safe,
            ~z.f10_safe & z.f15_safe,
        ],['BOTH','PLUS10_ONLY','PLUS15_ONLY'],default='NEITHER')
        z['state']=state
        for lab in ('BAD','GOOD'):
            q=z[z.label.eq(lab)]
            for st in ('BOTH','PLUS10_ONLY','PLUS15_ONLY','NEITHER'):
                tr.append({'partition':part,'label':lab,'state':st,'n':int(q.state.eq(st).sum()),'denom_alive15':int(len(q))})
    trans=pd.DataFrame(tr); trans.to_csv(OUT_TRANS,index=False)

    d[['event_id','partition','clock_block','regime','label','p10','p15','elig10','elig15','f10_safe','f15_safe','safe_persist','f10_agg','f15_agg','agg_persist']].to_csv(OUT_FLAGS,index=False)

    def row(scope,rule):
        q=met[met.scope.eq(scope)&met.rule.eq(rule)]; assert len(q)==1; return q.iloc[0]
    dv=row('development','SAFE_PERSIST_10_15'); dvb=row('development','PLUS15_SAFE')
    ex=row('external','SAFE_PERSIST_10_15'); exb=row('external','PLUS15_SAFE')
    va=row('reference_validation','SAFE_PERSIST_10_15'); vab=row('reference_validation','PLUS15_SAFE')
    ru=row('POOLED_REUSED_EXTVAL','SAFE_PERSIST_10_15'); rub=row('POOLED_REUSED_EXTVAL','PLUS15_SAFE')
    ma=row('POOLED_MAJOR','SAFE_PERSIST_10_15'); mab=row('POOLED_MAJOR','PLUS15_SAFE')

    gate=bool(
        float(dv.good_sacrifice)<=float(dvb.good_sacrifice)+EPS and
        float(dv.bad_capture)>=.60*float(dvb.bad_capture)-EPS and
        float(ex.good_sacrifice)<=float(exb.good_sacrifice)+EPS and
        float(va.good_sacrifice)<=float(vab.good_sacrifice)+EPS and
        float(rub.good_sacrifice)-float(ru.good_sacrifice)>=.03-EPS and
        float(ru.bad_capture)>=.70*float(rub.bad_capture)-EPS and
        float(ma.flag_precision_bad)>float(mab.flag_precision_bad)+EPS
    )
    verdict='B27CX_SEQUENTIAL_PERSISTENCE_REUSED_CANDIDATE' if gate else 'B27CX_SEQUENTIAL_PERSISTENCE_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(
        f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\ntrades_major={len(d)}\n'
        f'bad_major=78\ngood_major=348\nother_major=226\n'
        f'b27cv_plus10_auc={float(s10.development_auc)}\nb27cv_plus15_auc={float(s15.development_auc)}\n'
        f'b27cv_plus10_safe_threshold={float(s10.threshold)}\nb27cv_plus15_safe_threshold={float(s15.threshold)}\n'
        f'b27cv_plus15_dev_bad_flags=28\nb27cv_plus15_dev_good_flags=9\nuntouched_holdout=NONE\n'
    )

    lines=[
        '# B27CX — BTC 24H F05 SHORT Sequential Full-Loser Persistence — Result','',
        f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
        '**Audit status: PASS.** B27CV +10m/+15m models and frozen thresholds reproduced; 652 executable F05 trades / 78 BAD / 348 GOOD / 226 OTHER.','',
        '**Anatomy only:** trading WR/PF/expectancy/PnL are **N/A**. Primary rule is global SAFE at +10m AND global SAFE at +15m; no model/feature/threshold retuning.','',
        '## Six clocks independently — SAFE persistence (+10 AND +15)','',
        '| WIB | Development BAD / GOOD | External BAD / GOOD | Validation BAD / GOOD | Pooled major BAD / GOOD |',
        '|---|---:|---:|---:|---:|'
    ]
    for cb in CLOCKS:
        vals=[]
        for part in ('development','external','reference_validation','POOLED_MAJOR'):
            r=clock[(clock.clock_block.eq(cb))&clock.partition.eq(part)].iloc[0]
            vals.append(f"{int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) / {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)})")
        lines.append(f'| {WIB[cb]} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |')

    lines += ['', '## Primary pooled comparison','',
              '| Scope | +15 SAFE BAD / GOOD | Sequential BAD / GOOD | Precision +15→sequential |',
              '|---|---:|---:|---:|']
    for name in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        b=row(name,'PLUS15_SAFE'); s=row(name,'SAFE_PERSIST_10_15')
        lines.append(f"| {name} | {int(b.bad_flagged)}/{int(b.bad_total)} ({pct(b.bad_capture)}) / {int(b.good_flagged)}/{int(b.good_total)} ({pct(b.good_sacrifice)}) | **{int(s.bad_flagged)}/{int(s.bad_total)} ({pct(s.bad_capture)}) / {int(s.good_flagged)}/{int(s.good_total)} ({pct(s.good_sacrifice)})** | {pct(b.flag_precision_bad)} → **{pct(s.flag_precision_bad)}** |")

    lines += ['', '## SAFE transition states among trades alive at +15m','',
              '| Scope | Label | BOTH | +10 only | +15 only | Neither |', '|---|---|---:|---:|---:|---:|']
    for part in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        for lab in ('BAD','GOOD'):
            q=trans[(trans.partition.eq(part))&trans.label.eq(lab)]
            get=lambda st:int(q[q.state.eq(st)].n.iloc[0])
            lines.append(f'| {part} | {lab} | {get("BOTH")} | {get("PLUS10_ONLY")} | {get("PLUS15_ONLY")} | {get("NEITHER")} |')

    lines += ['', '## Regime splits — pooled major SAFE persistence','',
              '| Regime | BAD caught | GOOD cut | Precision |', '|---|---:|---:|---:|']
    for rg in REGIMES:
        r=reg[(reg.regime.eq(rg))&reg.partition.eq('POOLED_MAJOR')].iloc[0]
        lines.append(f'| {rg} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)}) | {pct(r.flag_precision_bad)} |')

    lines += ['', '## Secondary descriptive rule','',
              'AGGRESSIVE +10 AND AGGRESSIVE +15 is reported in the CSV metrics but **cannot determine PASS**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'External/reference_validation remain reused-data confirmation, not untouched OOS. No economic abort simulation or live BBC change is authorized.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
