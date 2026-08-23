#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_london_ny_4h_regime_alignment_b27ag as b27ag
import btc_24h_4h_regime_short_atlas_b27be as b27be
import btc_24h_direct_break_retest_short_b27bz as b27bz
import btc_24h_clock_tp_sl_b27cs as b27cs
import btc_24h_full_loser_separability_b27cv as cv

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Result.md'
OUT_BLOCKS=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Blocks.csv'
OUT_SOURCES=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Sources.csv'
OUT_TRADES=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Trades.csv'
OUT_MET=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Metrics.csv'
OUT_CLOCK=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Clock.csv'
OUT_STATUS=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_FULL_LOSER_FRESH_HOLDOUT_B27DA_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
H4=pd.Timedelta(hours=4)
FRESH_START=pd.Timestamp('2026-08-21T00:00:00Z')
FRESH_END=pd.Timestamp('2026-08-23T00:00:00Z')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
T10_SAFE=0.5898635948838399
T15_SAFE=0.6079191233470493
IMPULSE=0.28173076923076923
EPS=1e-12
DETECTORS=('GLOBAL_PLUS15_SAFE','PERSIST_10_15','REFINED_BULL_IMPULSE')


def normalize_raw(z: pd.DataFrame) -> pd.DataFrame:
    x=z.copy()
    t=pd.to_numeric(x['ts'],errors='coerce')
    t=np.where(t>100_000_000_000_000,t/1000.0,t)
    x['ts']=pd.to_datetime(t,unit='ms',utc=True,errors='coerce')
    for c in ('open','high','low','close'):
        x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna().drop_duplicates('ts').sort_values('ts').set_index('ts')


def load_fresh() -> pd.DataFrame:
    frames=[]
    for ds in ('2026-08-21','2026-08-22'):
        url=f'{b21.BASE}/daily/klines/BTCUSDT/5m/BTCUSDT-5m-{ds}.zip'
        z=b21._fetch_one(url)
        if z is None or len(z)==0:
            raise RuntimeError(f'missing archived fresh day {ds}')
        frames.append(normalize_raw(z))
    f=pd.concat(frames).sort_index()
    f=f[(f.index>=FRESH_START)&(f.index<FRESH_END)].copy()
    assert len(f)==576,len(f)
    expected=pd.date_range(FRESH_START,FRESH_END-BAR5,freq='5min',tz='UTC')
    assert f.index.equals(expected),(f.index[0],f.index[-1],len(f))
    return f


def fast_slice(x,start,end):
    a=int(x.index.searchsorted(start,'left')); b=int(x.index.searchsorted(end,'left'))
    return x.iloc[a:b]


def build_blocks(x5,reg):
    rows=[]
    obs=FRESH_START
    while obs < FRESH_END:
        end=obs+H4
        if end+H4>FRESH_END:
            break
        prev_start=obs-H4
        prev=fast_slice(x5,prev_start,obs); q=fast_slice(x5,obs,end)
        assert len(prev)==48 and len(q)==48,(obs,len(prev),len(q))
        assert prev.index[0]==prev_start and q.index[0]==obs
        H=float(prev.high.max()); L=float(prev.low.min()); assert H>L
        regime,reg_bar,reg_av=b27be.causal_state_at(reg,obs)
        assert pd.Timestamp(reg_av)<=obs
        s=b27be.scan_block(q,H,L)
        rows.append({'partition':'fresh_holdout','obs_start':obs,'obs_end':end,'prev_start':prev_start,
                     'H':H,'L':L,'R4':H-L,'regime':regime,'regime_bar_start':reg_bar,
                     'regime_available_ts':reg_av,'clock_block':f'{obs.hour:02d}-{(obs.hour+4)%24:02d}',**s})
        obs += H4
    d=pd.DataFrame(rows)
    assert len(d)==11,len(d)
    assert (pd.to_datetime(d.obs_start,utc=True)>=FRESH_START).all()
    assert ((pd.to_datetime(d.obs_end,utc=True)+H4)<=FRESH_END).all()
    return d


def reconstruct_sources(x5,blocks):
    direct=[]
    for r in blocks.itertuples(index=False):
        if not bool(r.k1_opp0):
            continue
        out=b27bz.evaluate_one(x5,r)
        direct.append(out)
    ev=pd.DataFrame(direct)
    if ev.empty:
        return ev,ev
    for c in ('obs_start','obs_end','retest_complete_ts'):
        ev[c]=pd.to_datetime(ev[c],utc=True,errors='coerce')
    src=ev[(ev.retest_class=='RETEST_RECLAIMED')&ev.retest_complete_ts.notna()&(ev.retest_complete_ts<ev.obs_end)].copy()
    if len(src):
        src['reclaim_complete_ts']=src['retest_complete_ts']
        src['R4']=pd.to_numeric(src['H'])-pd.to_numeric(src['L'])
        src['event_id']=np.arange(1_000_000,1_000_000+len(src),dtype=int)
        src['partition']='fresh_holdout'
    return ev,src


def execute_f05(x5,src):
    if src.empty:
        return pd.DataFrame()
    rows=[]
    for r in src.itertuples(index=False):
        rows.append(b27cs.eval_one(x5,r,'BASE_H'))
    d=pd.DataFrame(rows)
    d=d[d.filled].copy()
    if d.empty:
        return d
    d['label']=np.where(d.exit_reason.astype(str).eq('FULL_SL_HIGH_BREAK'),'BAD',
                        np.where(d.target_reached.astype(bool),'GOOD','OTHER'))
    for c in ('obs_start','obs_end','reclaim_complete_ts','fill_ts','rebreak_complete_ts','exit_ts'):
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    assert ((d.obs_end+H4)<=FRESH_END).all()
    return d.sort_values(['fill_ts','event_id']).reset_index(drop=True)


def fit_frozen_parent(x5):
    old=cv.load_trades()
    h1=cv.build_h1(x5)
    feat=cv.make_features(old,x5,h1)
    sc,thr,coef,models=cv.score_all(feat)
    s10=thr[(thr.checkpoint=='PLUS10')&(thr['mode']=='SAFE')].iloc[0]
    s15=thr[(thr.checkpoint=='PLUS15')&(thr['mode']=='SAFE')].iloc[0]
    assert abs(float(s10.development_auc)-0.8452298452298452)<1e-12
    assert abs(float(s15.development_auc)-0.8860088365243004)<1e-12
    assert abs(float(s10.threshold)-T10_SAFE)<1e-10
    assert abs(float(s15.threshold)-T15_SAFE)<1e-10
    return h1,models,float(s10.development_auc),float(s15.development_auc)


def score_fresh(x5,h1,models,trades):
    if trades.empty:
        return trades.copy()
    feat=cv.make_features(trades,x5,h1)
    pieces=[]
    for cp in ('PLUS10','PLUS15'):
        q=feat[feat.checkpoint.eq(cp)].copy()
        nums=cv.num_cols(cp)
        q['bad_prob']=models[cp].predict_proba(q[nums+cv.CAT])[:,1]
        keep=['event_id','partition','clock_block','regime','label','bad_prob','model_eligible']
        if cp=='PLUS15':keep+=['max_bull_body_r4']
        q=q[keep].copy()
        q=q.rename(columns={'bad_prob':f'p{10 if cp=="PLUS10" else 15}',
                            'model_eligible':f'elig{10 if cp=="PLUS10" else 15}'})
        pieces.append(q)
    a,b=pieces
    keys=['event_id','partition','clock_block','regime','label']
    d=a.merge(b,on=keys,how='inner',validate='one_to_one')
    assert len(d)==len(trades)
    d['f10']=d.elig10.astype(bool)&((pd.to_numeric(d.p10)+EPS)>=T10_SAFE)
    d['f15']=d.elig15.astype(bool)&((pd.to_numeric(d.p15)+EPS)>=T15_SAFE)
    d['GLOBAL_PLUS15_SAFE']=d.f15
    d['PERSIST_10_15']=d.f10&d.f15
    late=(~d.f10)&d.f15
    d['REFINED_BULL_IMPULSE']=(d.f10&d.f15)|(late&(pd.to_numeric(d.max_bull_body_r4)+EPS>=IMPULSE))
    meta=trades[['event_id','fill_ts','exit_ts','exit_reason','target_name','target_reached','entry_px','H','L','R4','obs_start','obs_end']].copy()
    return d.merge(meta,on='event_id',how='left',validate='one_to_one')


def metrics(z,det):
    bad=z.label.eq('BAD') if len(z) else pd.Series(dtype=bool)
    good=z.label.eq('GOOD') if len(z) else pd.Series(dtype=bool)
    other=z.label.eq('OTHER') if len(z) else pd.Series(dtype=bool)
    f=z[det].astype(bool) if len(z) else pd.Series(dtype=bool)
    bt=int(bad.sum()); gt=int(good.sum()); ot=int(other.sum())
    bf=int((bad&f).sum()); gf=int((good&f).sum()); n=bf+gf
    return {'fills_n':int(len(z)),'bad_total':bt,'good_total':gt,'other_total':ot,
            'bad_flagged':bf,'bad_capture':bf/bt if bt else np.nan,
            'good_flagged':gf,'good_sacrifice':gf/gt if gt else np.nan,
            'flagged_bg_n':n,'precision_bad':bf/n if n else np.nan}


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def main():
    old,cov=b21.load5()
    assert len(old)==698112 and abs(float(cov)-1.0)<1e-12
    assert old.index.max()<FRESH_START
    fresh=load_fresh()
    x5=pd.concat([old,fresh]).sort_index()
    assert not x5.index.duplicated().any()
    assert x5.index.max()==FRESH_END-BAR5

    reg=b27ag.build_regime(x5)
    blocks=build_blocks(x5,reg); blocks.to_csv(OUT_BLOCKS,index=False)
    raw_events,src=reconstruct_sources(x5,blocks)
    src.to_csv(OUT_SOURCES,index=False)
    trades=execute_f05(x5,src)

    h1,models,auc10,auc15=fit_frozen_parent(x5)
    scored=score_fresh(x5,h1,models,trades)
    scored.to_csv(OUT_TRADES,index=False)

    rows=[]
    for det in DETECTORS:
        rows.append({'scope':'FRESH_POOLED','name':'ALL','detector':det,
                     'blocks_n':len(blocks),'reclaimed_sources_n':len(src),**metrics(scored,det)})
    met=pd.DataFrame(rows); met.to_csv(OUT_MET,index=False)

    crows=[]
    for cb in CLOCKS:
        bn=int((blocks.clock_block==cb).sum())
        sn=int((src.clock_block==cb).sum()) if len(src) else 0
        z=scored[scored.clock_block==cb] if len(scored) else scored
        for det in DETECTORS:
            crows.append({'clock_block':cb,'wib':WIB[cb],'detector':det,'blocks_n':bn,'reclaimed_sources_n':sn,**metrics(z,det)})
    clock=pd.DataFrame(crows); clock.to_csv(OUT_CLOCK,index=False)

    bt=int((scored.label=='BAD').sum()) if len(scored) else 0
    gt=int((scored.label=='GOOD').sum()) if len(scored) else 0
    ready=bool(bt>=10 and gt>=30)
    status='B27DA_FRESH_HOLDOUT_READY' if ready else 'B27DA_FRESH_HOLDOUT_INSUFFICIENT'
    OUT_STATUS.write_text(status+'\n')
    first_ts=fresh.index.min(); last_ts=fresh.index.max()
    OUT_AUDIT.write_text(
        f'audit=PASS\nold_rows={len(old)}\nold_coverage={float(cov)}\nold_last_ts={old.index.max()}\n'
        f'fresh_start={FRESH_START}\nfresh_end_exclusive={FRESH_END}\nfresh_rows={len(fresh)}\nfresh_first_ts={first_ts}\nfresh_last_ts={last_ts}\n'
        f'fresh_blocks={len(blocks)}\nreclaimed_sources={len(src)}\nf05_fills={len(scored)}\nbad={bt}\ngood={gt}\n'
        f'b27cv_plus10_auc_reproduced={auc10}\nb27cv_plus15_auc_reproduced={auc15}\n'
        f'readiness_bad_min=10\nreadiness_good_min=30\nuntouched_window=POST_2026_08_21_UTC\n'
    )

    lines=['# B27DA — BTC 24H F05 SHORT Fresh Holdout Detector Confirmation — Result','',
           f'Fresh window: **{FRESH_START} -> {FRESH_END} (exclusive)**; fresh raw 5m rows: **{len(fresh):,}**.','',
           f'**Audit status: PASS.** Historical B27CV models reproduced before fresh scoring: +10 AUC {auc10:.10f}; +15 AUC {auc15:.10f}. No fresh row entered fitting or threshold selection.','',
           f'Fresh causal reconstruction: **{len(blocks)}** complete 4H blocks with full +4h horizon -> **{len(src)}** reclaimed source event(s) -> **{len(scored)}** executable F05 fill(s).','',
           '## Six clocks independently','',
           '| UTC / WIB | Blocks | Reclaimed | F05 fills | Detector | BAD caught | GOOD cut | OTHER | Precision |',
           '|---|---:|---:|---:|---|---:|---:|---:|---:|']
    for cb in CLOCKS:
        for det in DETECTORS:
            r=clock[(clock.clock_block==cb)&(clock.detector==det)].iloc[0]
            lines.append(f'| {cb} / {WIB[cb]} | {int(r.blocks_n)} | {int(r.reclaimed_sources_n)} | {int(r.fills_n)} | {det} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)}) | {int(r.other_total)} | {pct(r.precision_bad)} |')
    lines += ['', '## Pooled fresh holdout','',
              '| Detector | Fills | BAD | GOOD | OTHER | BAD caught | GOOD cut | Precision |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for det in DETECTORS:
        r=met[met.detector==det].iloc[0]
        lines.append(f'| {det} | {int(r.fills_n)} | {int(r.bad_total)} | {int(r.good_total)} | {int(r.other_total)} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice)}) | {pct(r.precision_bad)} |')
    lines += ['', '## Readiness','',
              f'Required before detector confirmation: **>=10 BAD and >=30 GOOD**. Fresh holdout currently has **{bt} BAD and {gt} GOOD**.', '',
              f'**Frozen status: `{status}`.**','',
              'Because B27DA is detector/anatomy confirmation only, trading WR/PF/expectancy/PnL for hypothetical early-abort exits are N/A. No live BBC change is authorized.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
