#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_full_loser_separability_b27cv as cv

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_24H_FULL_LOSER_CLOCK_THRESHOLD_B27CW_Result.md'
OUT_MAP=ROOT/'BTC_24H_FULL_LOSER_CLOCK_THRESHOLD_B27CW_Map.csv'
OUT_MET=ROOT/'BTC_24H_FULL_LOSER_CLOCK_THRESHOLD_B27CW_Metrics.csv'
OUT_FLAGS=ROOT/'BTC_24H_FULL_LOSER_CLOCK_THRESHOLD_B27CW_Flags.csv'
OUT_STATUS=ROOT/'BTC_24H_FULL_LOSER_CLOCK_THRESHOLD_B27CW_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_FULL_LOSER_CLOCK_THRESHOLD_B27CW_Audit.txt'
CLOCKS=cv.CLOCKS
WIB=cv.WIB
MODES=('SAFE','AGGRESSIVE')
CAP={'SAFE':.10,'AGGRESSIVE':.20}
EPS=1e-12
GLOBAL={'SAFE':0.6079191233470493,'AGGRESSIVE':0.4101988544354365}


def flagmask(df,th):
    if math.isinf(th) and th>0:return pd.Series(False,index=df.index)
    return df.model_eligible.astype(bool)&pd.to_numeric(df.bad_prob,errors='coerce').ge(th-EPS)


def metrics(df,th):
    f=flagmask(df,th)
    bad=df.label.eq('BAD'); good=df.label.eq('GOOD')
    bt=int(bad.sum()); gt=int(good.sum())
    be=int((bad&df.model_eligible).sum()); ge=int((good&df.model_eligible).sum())
    bl=bt-be; gr=gt-ge
    bf=int((bad&f).sum()); gf=int((good&f).sum())
    fn=bf+gf
    return {'bad_total':bt,'bad_too_late':bl,'bad_eligible':be,'bad_flagged':bf,
            'bad_capture_all':bf/bt if bt else np.nan,'bad_recall_eligible':bf/be if be else np.nan,
            'good_total':gt,'good_resolved_safe':gr,'good_eligible':ge,'good_flagged':gf,
            'good_sacrifice_all':gf/gt if gt else np.nan,'good_fpr_eligible':gf/ge if ge else np.nan,
            'flagged_n':fn,'flag_precision_bad':bf/fn if fn else np.nan}


def choose_clock(df,cap):
    bt=int(df.label.eq('BAD').sum()); gt=int(df.label.eq('GOOD').sum())
    elig=df[df.model_eligible&df.label.isin(['BAD','GOOD'])].copy()
    if bt==0 or gt==0 or len(elig)==0:return math.inf,metrics(df,math.inf)
    probs=sorted(pd.to_numeric(elig.bad_prob,errors='coerce').dropna().unique(),reverse=True)
    best=(math.inf,metrics(df,math.inf)); bestkey=(-1.0,-1.0,-math.inf)
    for th in [math.inf]+[float(x) for x in probs]:
        m=metrics(df,th)
        if m['good_sacrifice_all']<=cap+EPS:
            key=(m['bad_capture_all'],-m['good_sacrifice_all'],th)
            if key>bestkey: best=(th,m); bestkey=key
    return best


def apply_map(z,mapdf,mode):
    pieces=[]
    for cb in CLOCKS:
        th=float(mapdf[(mapdf.clock_block.eq(cb))&(mapdf['mode'].eq(mode))].threshold.iloc[0])
        q=z[z.clock_block.eq(cb)].copy(); q['_flag']=flagmask(q,th).to_numpy(bool); pieces.append(q)
    d=pd.concat(pieces,ignore_index=True)
    bad=d.label.eq('BAD'); good=d.label.eq('GOOD'); f=d._flag
    bt=int(bad.sum()); gt=int(good.sum()); be=int((bad&d.model_eligible).sum()); ge=int((good&d.model_eligible).sum())
    bf=int((bad&f).sum()); gf=int((good&f).sum()); fn=bf+gf
    return {'bad_total':bt,'bad_too_late':bt-be,'bad_eligible':be,'bad_flagged':bf,
            'bad_capture_all':bf/bt if bt else np.nan,'bad_recall_eligible':bf/be if be else np.nan,
            'good_total':gt,'good_resolved_safe':gt-ge,'good_eligible':ge,'good_flagged':gf,
            'good_sacrifice_all':gf/gt if gt else np.nan,'good_fpr_eligible':gf/ge if ge else np.nan,
            'flagged_n':fn,'flag_precision_bad':bf/fn if fn else np.nan},d


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def thfmt(x):return '+inf' if math.isinf(float(x)) else f'{float(x):.3f}'


def main():
    trades=cv.load_trades(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    h1=cv.build_h1(x5); feats=cv.make_features(trades,x5,h1)
    sc,thr,coef,models=cv.score_all(feats)
    p15=sc[sc.checkpoint.eq('PLUS15')].copy()
    t15=thr[thr.checkpoint.eq('PLUS15')].copy()
    safe=t15[t15['mode'].eq('SAFE')].iloc[0]; agg=t15[t15['mode'].eq('AGGRESSIVE')].iloc[0]
    assert abs(float(safe.development_auc)-0.8860088365243004)<1e-12
    assert abs(float(safe.threshold)-GLOBAL['SAFE'])<1e-12
    assert abs(float(agg.threshold)-GLOBAL['AGGRESSIVE'])<1e-12
    assert int(safe.dev_bad_flagged)==28 and int(safe.dev_good_flagged)==9
    assert len(p15)==652 and int(p15.label.eq('BAD').sum())==78 and int(p15.label.eq('GOOD').sum())==348
    parent_dev=metrics(p15[p15.partition.eq('development')],GLOBAL['SAFE'])
    assert int(parent_dev['bad_flagged'])==28 and int(parent_dev['good_flagged'])==9

    rows=[]
    dev=p15[p15.partition.eq('development')]
    for cb in CLOCKS:
        cell=dev[dev.clock_block.eq(cb)]
        for mode in MODES:
            th,m=choose_clock(cell,CAP[mode])
            rows.append({'clock_block':cb,'wib':WIB[cb],'mode':mode,'threshold':th,**{f'dev_{k}':v for k,v in m.items()}})
    mp=pd.DataFrame(rows); mp.to_csv(OUT_MAP,index=False)

    met=[]; flagpieces=[]
    scopes=[('development',p15[p15.partition.eq('development')]),('external',p15[p15.partition.eq('external')]),
            ('reference_validation',p15[p15.partition.eq('reference_validation')]),
            ('POOLED_REUSED_EXTVAL',p15[p15.partition.isin(['external','reference_validation'])]),('POOLED_MAJOR',p15)]
    for mode in MODES:
        for name,z in scopes:
            mm,dd=apply_map(z,mp,mode); gm=metrics(z,GLOBAL[mode])
            met.append({'scope':'POOL','name':name,'mode':mode,**{f'map_{k}':v for k,v in mm.items()},**{f'global_{k}':v for k,v in gm.items()}})
            if name in ('external','development','reference_validation'):
                dd['partition_scope']=name; dd['mode']=mode; flagpieces.append(dd)
        for cb in CLOCKS:
            th=float(mp[(mp.clock_block.eq(cb))&(mp['mode'].eq(mode))].threshold.iloc[0])
            for part in ('development','external','reference_validation'):
                z=p15[p15.partition.eq(part)&p15.clock_block.eq(cb)]
                mm=metrics(z,th); gm=metrics(z,GLOBAL[mode])
                met.append({'scope':'CLOCK','name':cb,'partition':part,'mode':mode,'threshold':th,**{f'map_{k}':v for k,v in mm.items()},**{f'global_{k}':v for k,v in gm.items()}})
    md=pd.DataFrame(met); md.to_csv(OUT_MET,index=False)
    flags=pd.concat(flagpieces,ignore_index=True)
    flags[['event_id','partition','clock_block','regime','label','mode','bad_prob','model_eligible','resolved_before_or_at','_flag']].to_csv(OUT_FLAGS,index=False)

    def poolrow(name,mode='SAFE'):
        q=md[(md.scope.eq('POOL'))&md.name.eq(name)&md['mode'].eq(mode)]; assert len(q)==1; return q.iloc[0]
    dv=poolrow('development'); ex=poolrow('external'); va=poolrow('reference_validation'); ru=poolrow('POOLED_REUSED_EXTVAL'); ma=poolrow('POOLED_MAJOR')
    gate=bool(float(dv.map_good_sacrifice_all)<=.10+EPS and float(dv.map_bad_capture_all)>=28/38-EPS and
              float(ex.map_bad_capture_all)>=9/23-EPS and float(ex.map_good_sacrifice_all)<=.15+EPS and
              float(va.map_bad_capture_all)>=8/17-EPS and float(va.map_good_sacrifice_all)<=.15+EPS and
              float(ru.map_good_sacrifice_all)<=.15+EPS)
    verdict='B27CW_CLOCK_THRESHOLD_REUSED_CANDIDATE' if gate else 'B27CW_CLOCK_THRESHOLD_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\ntrades_major={len(trades)}\nbad_major=78\ngood_major=348\nother_major=226\ncheckpoint=PLUS15\nb27cv_auc_reproduced={float(safe.development_auc)}\nb27cv_safe_threshold_reproduced={float(safe.threshold)}\nb27cv_safe_dev_bad_flagged_reproduced={int(parent_dev["bad_flagged"])}\nb27cv_safe_dev_good_flagged_reproduced={int(parent_dev["good_flagged"])}\nclocks=6\nuntouched_holdout=NONE\n')

    lines=['# B27CW — BTC 24H F05 SHORT Clock-Specific Full-Loser Threshold — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** B27CV PLUS15 model reproduced exactly: AUC 0.8860088365; global SAFE threshold 0.6079191233; global development SAFE flags 28 BAD / 9 GOOD; 652 trades / 78 BAD / 348 GOOD / 226 OTHER.','',
           '**Anatomy calibration only:** trading WR/PF/expectancy/PnL are N/A. Model/features are unchanged; only development-selected cutoff differs by clock.','',
           '## Six clocks — SAFE threshold map','',
           '| WIB | Threshold | Dev BAD caught | Dev GOOD cut | External BAD / GOOD | Validation BAD / GOOD |',
           '|---|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        th=float(mp[(mp.clock_block.eq(cb))&mp['mode'].eq('SAFE')].threshold.iloc[0])
        rdev=md[(md.scope.eq('CLOCK'))&md.name.eq(cb)&md.partition.eq('development')&md['mode'].eq('SAFE')].iloc[0]
        rext=md[(md.scope.eq('CLOCK'))&md.name.eq(cb)&md.partition.eq('external')&md['mode'].eq('SAFE')].iloc[0]
        rval=md[(md.scope.eq('CLOCK'))&md.name.eq(cb)&md.partition.eq('reference_validation')&md['mode'].eq('SAFE')].iloc[0]
        lines.append(f'| {WIB[cb]} | **{thfmt(th)}** | {int(rdev.map_bad_flagged)}/{int(rdev.map_bad_total)} ({pct(rdev.map_bad_capture_all)}) | {int(rdev.map_good_flagged)}/{int(rdev.map_good_total)} ({pct(rdev.map_good_sacrifice_all)}) | {int(rext.map_bad_flagged)}/{int(rext.map_bad_total)} ({pct(rext.map_bad_capture_all)}) / {int(rext.map_good_flagged)}/{int(rext.map_good_total)} ({pct(rext.map_good_sacrifice_all)}) | {int(rval.map_bad_flagged)}/{int(rval.map_bad_total)} ({pct(rval.map_bad_capture_all)}) / {int(rval.map_good_flagged)}/{int(rval.map_good_total)} ({pct(rval.map_good_sacrifice_all)}) |')
    lines += ['', '## SAFE map vs frozen global B27CV SAFE','',
              '| Scope | BAD capture global→clock | GOOD sacrifice global→clock | Flag precision clock |',
              '|---|---:|---:|---:|']
    for name in ('development','external','reference_validation','POOLED_REUSED_EXTVAL','POOLED_MAJOR'):
        r=poolrow(name)
        lines.append(f'| {name} | {pct(r.global_bad_capture_all)} → **{pct(r.map_bad_capture_all)}** | {pct(r.global_good_sacrifice_all)} → **{pct(r.map_good_sacrifice_all)}** | {pct(r.map_flag_precision_bad)} |')
    lines += ['', '## AGGRESSIVE development thresholds (secondary)','',
              '| WIB | Threshold | BAD capture | GOOD sacrifice |', '|---|---:|---:|---:|']
    for cb in CLOCKS:
        th=float(mp[(mp.clock_block.eq(cb))&mp['mode'].eq('AGGRESSIVE')].threshold.iloc[0])
        r=md[(md.scope.eq('CLOCK'))&md.name.eq(cb)&md.partition.eq('development')&md['mode'].eq('AGGRESSIVE')].iloc[0]
        lines.append(f'| {WIB[cb]} | {thfmt(th)} | {pct(r.map_bad_capture_all)} | {pct(r.map_good_sacrifice_all)} |')
    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              'External/reference_validation are reused-data confirmation, not untouched OOS. No economic abort simulation or live BBC change is authorized by this experiment.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':main()
