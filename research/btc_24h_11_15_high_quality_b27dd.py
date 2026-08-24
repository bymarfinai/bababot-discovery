#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_full_loser_separability_b27cv as cv
import btc_24h_causal_abort_econ_b27dc as dc

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_24H_11_15_HIGH_QUALITY_B27DD_Result.md'
OUT_CAND=ROOT/'BTC_24H_11_15_HIGH_QUALITY_B27DD_Candidates.csv'
OUT_SEL=ROOT/'BTC_24H_11_15_HIGH_QUALITY_B27DD_Selected.csv'
OUT_REG=ROOT/'BTC_24H_11_15_HIGH_QUALITY_B27DD_Regime.csv'
OUT_STATUS=ROOT/'BTC_24H_11_15_HIGH_QUALITY_B27DD_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_11_15_HIGH_QUALITY_B27DD_Audit.txt'

CLOCK='04-08'
WIB='11-15'
ENTRY_FILTERS=('BASE','NO_SIDEWAYS','LOW_BAD_Q75','LOW_BAD_Q65','NO_SIDEWAYS_LOW_BAD_Q75')
MGMT=('NO_ABORT','REFINED_ABORT')
PARTS=('external','development','reference_validation')
EPS=1e-12


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def money(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'
def pfmt(x): return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{float(x):.2f}')


def fill_scores(x5):
    trades=cv.load_trades()
    h1=cv.build_h1(x5)
    feats=cv.make_features(trades,x5,h1)
    sc,thr,coef,models=cv.score_all(feats)
    q=feats[feats.checkpoint.eq('FILL')].copy()
    nums=cv.num_cols('FILL')
    q['fill_bad_prob']=models['FILL'].predict_proba(q[nums+cv.CAT])[:,1]
    assert len(q)==652 and q.event_id.nunique()==652
    sf=thr[(thr.checkpoint.eq('FILL'))&thr['mode'].eq('SAFE')]
    assert len(sf)==1
    fill_auc=float(sf.iloc[0].development_auc)
    return q[['event_id','partition','clock_block','regime','fill_bad_prob']].copy(),fill_auc


def entry_mask(d,name,q75,q65):
    p=pd.to_numeric(d.fill_bad_prob,errors='coerce')
    ns=~d.regime.astype(str).eq('SIDEWAYS')
    if name=='BASE': return pd.Series(True,index=d.index)
    if name=='NO_SIDEWAYS': return ns
    if name=='LOW_BAD_Q75': return p.le(q75+EPS)
    if name=='LOW_BAD_Q65': return p.le(q65+EPS)
    if name=='NO_SIDEWAYS_LOW_BAD_Q75': return ns & p.le(q75+EPS)
    raise KeyError(name)


def min_rr(g):
    x=pd.to_numeric(g.nominal_rr,errors='coerce').dropna()
    return float(x.min()) if len(x) else np.nan


def scopes(d):
    return (
        ('development',d[d.partition.eq('development')]),
        ('external',d[d.partition.eq('external')]),
        ('reference_validation',d[d.partition.eq('reference_validation')]),
        ('POOLED_REUSED_EXTVAL',d[d.partition.isin(['external','reference_validation'])]),
        ('POOLED_MAJOR',d),
    )


def main():
    x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12
    cand=dc.load_candidates()
    base=cand[(cand.candidate.eq('R100'))&cand.clock_block.eq(CLOCK)].copy()
    exp={'external':38,'development':38,'reference_validation':20}
    assert len(base)==96,len(base)
    for p,n in exp.items(): assert len(base[base.partition.eq(p)])==n,(p,len(base[base.partition.eq(p)]),n)
    rr=pd.to_numeric(base.nominal_rr,errors='coerce'); assert rr.notna().all() and float(rr.min())>=1.0-EPS

    fs,fill_auc=fill_scores(x5)
    fs11=fs[fs.clock_block.eq(CLOCK)].copy(); assert len(fs11)==96
    devp=pd.to_numeric(fs11.loc[fs11.partition.eq('development'),'fill_bad_prob'],errors='coerce')
    assert len(devp)==38 and devp.notna().all()
    q75=float(devp.quantile(.75,interpolation='linear'))
    q65=float(devp.quantile(.65,interpolation='linear'))
    assert q65<=q75+EPS

    post,auc10,auc15=dc.frozen_scores(x5)
    rows=[]; regime_rows=[]; all_detail=[]
    base_scope_n={
        'development':38,'external':38,'reference_validation':20,
        'POOLED_REUSED_EXTVAL':58,'POOLED_MAJOR':96,
    }

    for mg in MGMT:
        drule='NO_ABORT' if mg=='NO_ABORT' else 'REFINED_BULL_IMPULSE'
        managed=dc.apply_rule(x5,base,post,drule)
        managed=managed.merge(fs11[['event_id','fill_bad_prob']],on='event_id',how='left',validate='one_to_one')
        assert managed.fill_bad_prob.notna().all()
        for ef in ENTRY_FILTERS:
            z=managed[entry_mask(managed,ef,q75,q65)].copy()
            assert (pd.to_numeric(z.nominal_rr,errors='coerce')>=1.0-EPS).all()
            z['entry_filter']=ef; z['management']=mg
            all_detail.append(z)
            for scope,g in scopes(z):
                m=dc.econ(g)
                rows.append({
                    'entry_filter':ef,'management':mg,'scope':scope,
                    'baseline_n':base_scope_n[scope],
                    'retention':m['trades_n']/base_scope_n[scope] if base_scope_n[scope] else np.nan,
                    **m,'min_nominal_rr':min_rr(g),
                })
            for scope,g in (('development',z[z.partition.eq('development')]),('POOLED_MAJOR',z)):
                for rg in ('BULL','BEAR','SIDEWAYS'):
                    regime_rows.append({'entry_filter':ef,'management':mg,'scope':scope,'regime':rg,'trades_n':int(g.regime.astype(str).eq(rg).sum())})

    res=pd.DataFrame(rows); res.to_csv(OUT_CAND,index=False)
    pd.DataFrame(regime_rows).to_csv(OUT_REG,index=False)

    # Parent economic reproduction.
    pb=res[(res.entry_filter.eq('BASE'))&(res.management.eq('NO_ABORT'))&(res.scope.eq('POOLED_MAJOR'))].iloc[0]
    assert int(pb.trades_n)==96
    assert abs(float(pb.total_net)-11.77)<.03,(pb.total_net,)
    assert abs(float(pb.wr)-(56/96))<1e-12,(pb.wr,)

    # Development-only frozen selection.
    dev=res[res.scope.eq('development')].copy()
    dev['eligible']=(dev.trades_n>=20)&(dev.wr>=.65-EPS)&(dev.pf>1.0+EPS)&(dev.expectancy>0)&(dev.total_net>0)
    order={(ef,mg):i*2+j for i,ef in enumerate(ENTRY_FILTERS) for j,mg in enumerate(MGMT)}
    eligible=dev[dev.eligible].copy()
    selected=None
    if len(eligible):
        eligible['fixed_order']=[order[(a,b)] for a,b in zip(eligible.entry_filter,eligible.management)]
        eligible=eligible.sort_values(['wr','pf','trades_n','fixed_order'],ascending=[False,False,False,True])
        selected=eligible.iloc[0]

    verdict='B27DD_HIGH_QUALITY_NOT_SUPPORTED'
    selrows=pd.DataFrame()
    final_checks={}
    if selected is not None:
        ef=str(selected.entry_filter); mg=str(selected.management)
        selrows=res[(res.entry_filter.eq(ef))&(res.management.eq(mg))].copy()
        selrows.to_csv(OUT_SEL,index=False)
        def row(scope):
            q=selrows[selrows.scope.eq(scope)]; assert len(q)==1; return q.iloc[0]
        ma=row('POOLED_MAJOR'); ex=row('external'); va=row('reference_validation'); ru=row('POOLED_REUSED_EXTVAL')
        pooled_ok=bool(int(ma.trades_n)>=60 and float(ma.wr)>.70+EPS and float(ma.pf)>1.0+EPS and float(ma.expectancy)>0 and float(ma.total_net)>0 and float(ma.min_nominal_rr)>=1.0-EPS)
        ext_ok=bool(int(ex.trades_n)>=15 and float(ex.pf)>.90+EPS and float(ex.total_net)>=-10.0-EPS and float(ex.expectancy)>=-.25-EPS)
        val_ok=bool(int(va.trades_n)>=15 and float(va.pf)>.90+EPS and float(va.total_net)>=-10.0-EPS and float(va.expectancy)>=-.25-EPS)
        reused_ok=bool(float(ru.wr)>=.65-EPS and float(ru.pf)>1.0+EPS and float(ru.expectancy)>0 and float(ru.total_net)>0)
        final_checks={'pooled_major':pooled_ok,'external':ext_ok,'reference_validation':val_ok,'pooled_reused':reused_ok}
        if pooled_ok and ext_ok and val_ok and reused_ok:
            verdict='B27DD_HIGH_QUALITY_REUSED_CANDIDATE'
    else:
        # Persist an empty selected file for audit consistency.
        pd.DataFrame(columns=res.columns).to_csv(OUT_SEL,index=False)

    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(
        f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nclock={CLOCK}\nwib={WIB}\n'
        f'baseline_trades=96\nbaseline_external=38\nbaseline_development=38\nbaseline_validation=20\n'
        f'fill_model_development_auc={fill_auc}\nq75={q75}\nq65={q65}\n'
        f'b27cv_plus10_auc={auc10}\nb27cv_plus15_auc={auc15}\n'
        f'candidate_count=10\ndevelopment_eligible_n={len(eligible)}\n'
        f'selected={"NONE" if selected is None else str(selected.entry_filter)+"+"+str(selected.management)}\n'
        f'min_rr_asserted=1.0\nexternal_reference_validation_reused=true\nfresh_holdout=INSUFFICIENT_B27DA\n'
    )

    lines=['# B27DD — BTC 11–15 WIB R100 High-Quality Filter Frontier — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**. Audit **PASS**.','',
           f'Frozen development-only FILL-risk thresholds: **Q75={q75:.6f}**, **Q65={q65:.6f}**. B27CV FILL development AUC: **{fill_auc:.4f}**.','',
           'Economic lane is **R100 nominal RR 1:1 only**. Clock is **11–15 WIB / 04-08 UTC**, TP **T15**. External/reference_validation are reused confirmation; fresh B27DA remains insufficient.','',
           '## Development selection — all 10 frozen candidates','',
           '| Entry filter | Management | N | Retain | WR | PF | Exp/trade | Total net | Avg win | Avg loss | MaxDD | Loss streak | Aborts | Eligible |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for ef in ENTRY_FILTERS:
        for mg in MGMT:
            r=dev[(dev.entry_filter.eq(ef))&(dev.management.eq(mg))].iloc[0]
            lines.append(f'| {ef} | {mg} | {int(r.trades_n)} | {pct(r.retention)} | **{pct(r.wr)}** | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.abort_n)} | {"YES" if bool(r.eligible) else "NO"} |')

    if selected is None:
        lines += ['', '## Selection','', '**No development candidate passed the frozen development eligibility gate.**','',f'**Frozen verdict: `{verdict}`.**']
    else:
        ef=str(selected.entry_filter); mg=str(selected.management)
        lines += ['', '## Frozen development selection','',f'Selected: **{ef} + {mg}**. Selection used development only.','',
                  '## Selected rule — confirmation and final target','',
                  '| Scope | N | Retain | WR | PF | Exp/trade | Total net | Avg win | Avg loss | MaxDD | Loss streak | Aborts | Min RR |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for scope in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
            r=selrows[selrows.scope.eq(scope)].iloc[0]
            lines.append(f'| {scope} | {int(r.trades_n)} | {pct(r.retention)} | **{pct(r.wr)}** | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.abort_n)} | {float(r.min_nominal_rr):.2f} |')
        lines += ['', 'Final gates: ' + ', '.join(f'**{k}={"PASS" if v else "FAIL"}**' for k,v in final_checks.items()),'',f'**Frozen verdict: `{verdict}`.**']

        # Regime composition selected rule.
        rr=pd.DataFrame(regime_rows)
        sr=rr[(rr.entry_filter.eq(ef))&(rr.management.eq(mg))]
        lines += ['', '## Selected retained regime composition','', '| Scope | BULL | BEAR | SIDEWAYS |','|---|---:|---:|---:|']
        for scope in ('development','POOLED_MAJOR'):
            q=sr[sr.scope.eq(scope)]
            counts={r.regime:int(r.trades_n) for r in q.itertuples(index=False)}
            lines.append(f'| {scope} | {counts.get("BULL",0)} | {counts.get("BEAR",0)} | {counts.get("SIDEWAYS",0)} |')

    lines += ['', 'Research only. No live BBC change.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
