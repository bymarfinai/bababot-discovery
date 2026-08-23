#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_full_loser_separability_b27cv as cv

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Result.md'
OUT_MET=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Metrics.csv'
OUT_CLOCK=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Clock.csv'
OUT_REGIME=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Regime.csv'
OUT_LATE=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_LateOnly.csv'
OUT_DIAG=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Diagnostics.csv'
OUT_STATUS=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_FULL_LOSER_LATE_ONLY_B27CY_Audit.txt'

EPS=1e-12
T10_SAFE=0.5898635948838399
T15_SAFE=0.6079191233470493
CLOCKS=cv.CLOCKS
WIB=cv.WIB
REGIMES=cv.REGIMES
SECONDARY=('max_bull_body_r4','higher_close_streak','net_close_from_entry_r4')


def flag(prob,eligible,th):
    p=pd.to_numeric(prob,errors='coerce')
    return eligible.astype(bool)&p.notna()&((p+EPS)>=float(th))


def prepare(sc):
    a=sc[sc.checkpoint.eq('PLUS10')].copy()
    b=sc[sc.checkpoint.eq('PLUS15')].copy()
    keys=['event_id','partition','clock_block','regime','label']
    a=a[keys+['bad_prob','model_eligible']].rename(columns={'bad_prob':'p10','model_eligible':'elig10'})
    b=b[keys+['bad_prob','model_eligible']+list(SECONDARY)].rename(columns={'bad_prob':'p15','model_eligible':'elig15'})
    d=a.merge(b,on=keys,how='inner',validate='one_to_one')
    assert len(d)==652,len(d)
    d['f10']=flag(d.p10,d.elig10,T10_SAFE)
    d['f15']=flag(d.p15,d.elig15,T15_SAFE)
    d['state']=np.select([d.f10&d.f15,d.f10&~d.f15,~d.f10&d.f15],['BOTH','PLUS10_ONLY','PLUS15_ONLY'],default='NEITHER')
    d['delta_bad_prob']=pd.to_numeric(d.p15,errors='coerce')-pd.to_numeric(d.p10,errors='coerce')
    return d


def late_metrics(z,th):
    q=z[z.label.isin(['BAD','GOOD'])&z.elig15.astype(bool)&z.state.eq('PLUS15_ONLY')].copy()
    bad=q.label.eq('BAD'); good=q.label.eq('GOOD')
    bt=int(bad.sum()); gt=int(good.sum())
    if math.isinf(th): f=pd.Series(False,index=q.index)
    else: f=(q.delta_bad_prob+EPS)>=float(th)
    bf=int((bad&f).sum()); gf=int((good&f).sum()); fn=bf+gf
    return {'late_bad_total':bt,'late_bad_flagged':bf,'late_bad_capture':bf/bt if bt else np.nan,
            'late_good_total':gt,'late_good_flagged':gf,'late_good_sacrifice':gf/gt if gt else np.nan,
            'late_flagged_n':fn,'late_precision_bad':bf/fn if fn else np.nan}


def choose_delta(dev):
    q=dev[dev.label.isin(['BAD','GOOD'])&dev.elig15.astype(bool)&dev.state.eq('PLUS15_ONLY')].copy()
    assert int(q.label.eq('BAD').sum())==6 and int(q.label.eq('GOOD').sum())==6,q.label.value_counts().to_dict()
    vals=sorted(q.delta_bad_prob.dropna().unique(),reverse=True)
    best=(math.inf,late_metrics(dev,math.inf)); keybest=(-1.0,-1.0,-math.inf)
    for th in [math.inf]+[float(x) for x in vals]:
        m=late_metrics(dev,th)
        gs=float(m['late_good_sacrifice']) if not pd.isna(m['late_good_sacrifice']) else 0.0
        bc=float(m['late_bad_capture']) if not pd.isna(m['late_bad_capture']) else 0.0
        if gs<=.3334+EPS:
            key=(bc,-gs,th)
            if key>keybest:
                best=(th,m); keybest=key
    return best


def state_flag(d,delta_th):
    late=(d.state.eq('PLUS15_ONLY')&d.elig15.astype(bool))
    latepass=pd.Series(False,index=d.index) if math.isinf(delta_th) else (late&(d.delta_bad_prob+EPS>=float(delta_th)))
    return d.state.eq('BOTH')|latepass


def metrics(d,rule,delta_th):
    bad=d.label.eq('BAD'); good=d.label.eq('GOOD')
    bt=int(bad.sum()); gt=int(good.sum())
    if rule=='PLUS15_SAFE': f=d.f15
    elif rule=='PERSIST_BOTH': f=d.state.eq('BOTH')
    elif rule=='REFINED_STATE': f=state_flag(d,delta_th)
    else: raise KeyError(rule)
    bf=int((bad&f).sum()); gf=int((good&f).sum()); fn=bf+gf
    lm=late_metrics(d,delta_th)
    return {'bad_total':bt,'bad_flagged':bf,'bad_capture':bf/bt if bt else np.nan,
            'good_total':gt,'good_flagged':gf,'good_sacrifice':gf/gt if gt else np.nan,
            'flagged_n':fn,'flag_precision_bad':bf/fn if fn else np.nan,**lm}


def diag_rows(d):
    dev=d[d.partition.eq('development')&d.label.isin(['BAD','GOOD'])&d.elig15.astype(bool)&d.state.eq('PLUS15_ONLY')]
    dirs={}
    for feat in SECONDARY:
        y=dev.label.eq('BAD').astype(int)
        x=pd.to_numeric(dev[feat],errors='coerce')
        auc=float(roc_auc_score(y,x))
        dirs[feat]=1 if auc>=.5 else -1
    rows=[]
    for part in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        if part=='POOLED_REUSED_EXTVAL': z=d[d.partition.isin(['external','reference_validation'])]
        elif part=='POOLED_MAJOR': z=d
        else: z=d[d.partition.eq(part)]
        q=z[z.label.isin(['BAD','GOOD'])&z.elig15.astype(bool)&z.state.eq('PLUS15_ONLY')]
        for feat in ('delta_bad_prob',)+SECONDARY:
            bad=pd.to_numeric(q.loc[q.label.eq('BAD'),feat],errors='coerce').dropna()
            good=pd.to_numeric(q.loc[q.label.eq('GOOD'),feat],errors='coerce').dropna()
            if feat=='delta_bad_prob': direction=1
            else: direction=dirs[feat]
            auc=np.nan
            if len(bad)>0 and len(good)>0:
                yy=q.label.eq('BAD').astype(int)
                xx=pd.to_numeric(q[feat],errors='coerce')*direction
                ok=xx.notna()
                if yy[ok].nunique()==2: auc=float(roc_auc_score(yy[ok],xx[ok]))
            rows.append({'partition':part,'feature':feat,'direction':direction,'bad_n':len(bad),'good_n':len(good),
                         'bad_median':float(bad.median()) if len(bad) else np.nan,
                         'good_median':float(good.median()) if len(good) else np.nan,'directional_auc':auc})
    return pd.DataFrame(rows)


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def thfmt(x): return '+inf' if math.isinf(float(x)) else f'{float(x):.4f}'


def main():
    trades=cv.load_trades(); x5,cov=b21.load5()
    assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    h1=cv.build_h1(x5); feats=cv.make_features(trades,x5,h1)
    sc,thr,coef,models=cv.score_all(feats)
    s10=thr[(thr.checkpoint.eq('PLUS10'))&thr['mode'].eq('SAFE')].iloc[0]
    s15=thr[(thr.checkpoint.eq('PLUS15'))&thr['mode'].eq('SAFE')].iloc[0]
    assert abs(float(s10.development_auc)-0.8452298452298452)<1e-12
    assert abs(float(s15.development_auc)-0.8860088365243004)<1e-12
    assert abs(float(s10.threshold)-T10_SAFE)<1e-10
    assert abs(float(s15.threshold)-T15_SAFE)<1e-10

    d=prepare(sc)
    assert int(d.label.eq('BAD').sum())==78 and int(d.label.eq('GOOD').sum())==348 and int(d.label.eq('OTHER').sum())==226
    expected={'development':(6,6),'external':(2,3),'reference_validation':(4,6)}
    for part,(nb,ng) in expected.items():
        q=d[d.partition.eq(part)&d.elig15.astype(bool)&d.state.eq('PLUS15_ONLY')]
        assert int(q.label.eq('BAD').sum())==nb,(part,'BAD',q.label.value_counts().to_dict())
        assert int(q.label.eq('GOOD').sum())==ng,(part,'GOOD',q.label.value_counts().to_dict())

    delta_th,devlate=choose_delta(d[d.partition.eq('development')])

    scopes=[('development',d[d.partition.eq('development')]),('external',d[d.partition.eq('external')]),
            ('reference_validation',d[d.partition.eq('reference_validation')]),
            ('POOLED_REUSED_EXTVAL',d[d.partition.isin(['external','reference_validation'])]),('POOLED_MAJOR',d)]
    rows=[]
    for name,z in scopes:
        for rule in ('PLUS15_SAFE','PERSIST_BOTH','REFINED_STATE'):
            rows.append({'scope':name,'rule':rule,'delta_threshold':delta_th,**metrics(z,rule,delta_th)})
    met=pd.DataFrame(rows); met.to_csv(OUT_MET,index=False)

    clockrows=[]
    for cb in CLOCKS:
        z=d[d.clock_block.eq(cb)]
        clockrows.append({'clock_block':cb,'wib':WIB[cb],**metrics(z,'REFINED_STATE',delta_th)})
    clock=pd.DataFrame(clockrows); clock.to_csv(OUT_CLOCK,index=False)

    regrows=[]
    for rg in REGIMES:
        z=d[d.regime.eq(rg)]
        regrows.append({'regime':rg,**metrics(z,'REFINED_STATE',delta_th)})
    reg=pd.DataFrame(regrows); reg.to_csv(OUT_REGIME,index=False)

    late=d[d.label.isin(['BAD','GOOD'])&d.elig15.astype(bool)&d.state.eq('PLUS15_ONLY')].copy()
    late['delta_flag']=False if math.isinf(delta_th) else ((late.delta_bad_prob+EPS)>=float(delta_th))
    late[['event_id','partition','clock_block','regime','label','p10','p15','delta_bad_prob','delta_flag']+list(SECONDARY)].to_csv(OUT_LATE,index=False)
    diag=diag_rows(d); diag.to_csv(OUT_DIAG,index=False)

    def row(scope,rule):
        q=met[met.scope.eq(scope)&met.rule.eq(rule)]; assert len(q)==1; return q.iloc[0]
    dv=row('development','REFINED_STATE'); ex=row('external','REFINED_STATE'); va=row('reference_validation','REFINED_STATE')
    ru=row('POOLED_REUSED_EXTVAL','REFINED_STATE'); rub=row('POOLED_REUSED_EXTVAL','PLUS15_SAFE')
    ma=row('POOLED_MAJOR','REFINED_STATE'); mab=row('POOLED_MAJOR','PLUS15_SAFE')
    dl=late_metrics(d[d.partition.eq('development')],delta_th)
    el=late_metrics(d[d.partition.eq('external')],delta_th)
    vl=late_metrics(d[d.partition.eq('reference_validation')],delta_th)

    gate=bool(
        float(dl['late_bad_capture'])>=.50-EPS and float(dl['late_good_sacrifice'])<=.3334+EPS and
        float(el['late_bad_capture'])>=.50-EPS and float(el['late_good_sacrifice'])<=.3334+EPS and
        float(vl['late_bad_capture'])>=.50-EPS and float(vl['late_good_sacrifice'])<=.3334+EPS and
        float(ru.bad_capture)>=.70*float(rub.bad_capture)-EPS and
        float(rub.good_sacrifice)-float(ru.good_sacrifice)>=.03-EPS and
        float(ma.flag_precision_bad)>float(mab.flag_precision_bad)+EPS
    )
    verdict='B27CY_LATE_ONLY_REFINEMENT_REUSED_CANDIDATE' if gate else 'B27CY_LATE_ONLY_REFINEMENT_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(
        f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\ntrades_major=652\nbad_major=78\ngood_major=348\nother_major=226\n'
        f'b27cv_plus10_auc={float(s10.development_auc)}\nb27cv_plus15_auc={float(s15.development_auc)}\n'
        f'late_dev_bad=6\nlate_dev_good=6\nlate_external_bad=2\nlate_external_good=3\nlate_validation_bad=4\nlate_validation_good=6\n'
        f'delta_threshold={delta_th}\nuntouched_holdout=NONE\n'
    )

    lines=['# B27CY — BTC 24H F05 SHORT Late-Only BAD Refinement — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** B27CV/B27CX identities reproduced: 652 trades / 78 BAD / 348 GOOD / 226 OTHER; PLUS15_ONLY development 6 BAD/6 GOOD, external 2/3, validation 4/6.','',
           f'Primary development-only delta threshold: **{thfmt(delta_th)}**. Anatomy only: trading WR/PF/expectancy/PnL are **N/A**.','',
           '## Six clocks independently — refined +15m state machine','',
           '| WIB | BAD caught | GOOD cut | Precision | Late-only BAD / GOOD flagged |',
           '|---|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=clock[clock.clock_block.eq(cb)].iloc[0]
        lines.append(f"| {WIB[cb]} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)}) | {pct(r.flag_precision_bad)} | {int(r.late_bad_flagged)}/{int(r.late_bad_total)} / {int(r.late_good_flagged)}/{int(r.late_good_total)} |")

    lines += ['', '## Pooled comparison','',
              '| Scope | +15 SAFE BAD / GOOD | Persistence BOTH BAD / GOOD | Refined state BAD / GOOD | Precision refined |',
              '|---|---:|---:|---:|---:|']
    for name in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        b=row(name,'PLUS15_SAFE'); p=row(name,'PERSIST_BOTH'); r=row(name,'REFINED_STATE')
        lines.append(f"| {name} | {int(b.bad_flagged)}/{int(b.bad_total)} ({pct(b.bad_capture)}) / {int(b.good_flagged)}/{int(b.good_total)} ({pct(b.good_sacrifice)}) | {int(p.bad_flagged)}/{int(p.bad_total)} ({pct(p.bad_capture)}) / {int(p.good_flagged)}/{int(p.good_total)} ({pct(p.good_sacrifice)}) | **{int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) / {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)})** | {pct(r.flag_precision_bad)} |")

    lines += ['', '## PLUS15_ONLY primary delta gate','',
              '| Partition | BAD caught | GOOD cut | Delta BAD median | Delta GOOD median |', '|---|---:|---:|---:|---:|']
    for part in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        if part=='POOLED_REUSED_EXTVAL': z=d[d.partition.isin(['external','reference_validation'])]
        elif part=='POOLED_MAJOR': z=d
        else: z=d[d.partition.eq(part)]
        lm=late_metrics(z,delta_th)
        q=z[z.label.isin(['BAD','GOOD'])&z.elig15.astype(bool)&z.state.eq('PLUS15_ONLY')]
        bm=q.loc[q.label.eq('BAD'),'delta_bad_prob'].median(); gm=q.loc[q.label.eq('GOOD'),'delta_bad_prob'].median()
        lines.append(f"| {part} | {int(lm['late_bad_flagged'])}/{int(lm['late_bad_total'])} ({pct(lm['late_bad_capture'])}) | {int(lm['late_good_flagged'])}/{int(lm['late_good_total'])} ({pct(lm['late_good_sacrifice'])}) | {float(bm):.4f} | {float(gm):.4f} |")

    lines += ['', '## Secondary diagnostics — directional AUC','',
              '| Feature | Development | External | Validation |', '|---|---:|---:|---:|']
    for feat in SECONDARY:
        vals=[]
        for part in ('development','external','reference_validation'):
            rr=diag[(diag.partition.eq(part))&diag.feature.eq(feat)].iloc[0]
            vals.append(pct(rr.directional_auc))
        lines.append(f'| `{feat}` | {vals[0]} | {vals[1]} | {vals[2]} |')

    lines += ['', '## Regime splits — pooled major refined state','',
              '| Regime | BAD caught | GOOD cut | Precision |', '|---|---:|---:|---:|']
    for rg in REGIMES:
        r=reg[reg.regime.eq(rg)].iloc[0]
        lines.append(f"| {rg} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)}) | {pct(r.flag_precision_bad)} |")

    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              'External/reference_validation are reused-data confirmation, not untouched OOS. No economic abort simulation or live BBC change is authorized.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
