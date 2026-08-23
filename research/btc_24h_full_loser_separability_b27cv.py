#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_CLOCK_TP_SL_B27CS_SelectedTrades.csv'
OUT_MD=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Result.md'
OUT_FEATURES=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Features.csv'
OUT_METRICS=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Metrics.csv'
OUT_THRESH=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Thresholds.csv'
OUT_COEF=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Coefficients.csv'
OUT_CLOCK=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Clock.csv'
OUT_REGIME=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Regime.csv'
OUT_STATUS=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_FULL_LOSER_SEPARABILITY_B27CV_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
HOUR=pd.Timedelta(hours=1)
MAJOR=('external','development','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
REGIMES=('BULL','BEAR','SIDEWAYS')
CHECKPOINTS=('RECLAIM','FILL','PLUS5','PLUS10','PLUS15')
MODES=('SAFE','AGGRESSIVE')
EPS=1e-12

CAT=['clock_block','regime']
RECLAIM_NUM=[
    'reclaim_pos_r4','reclaim_body_frac','reclaim_upper_wick_frac','reclaim_lower_wick_frac',
    'remaining_block_min_reclaim','setup_f05_pos_r4','setup_f05_to_h_r4',
    'ema20_dist_r4','ema50_dist_r4','ema20_minus_50_r4','ema50_slope3_r4'
]
FILL_NUM=[
    'entry_pos_r4','entry_gap_f05_r4','entry_to_h_r4','reclaim_to_fill_min'
]
PATH_NUM=[
    'current_close_pos_r4','net_close_from_entry_r4','mae_high_r4','mae_close_r4','mfe_low_r4',
    'rebreak_done','higher_close_streak','higher_high_streak','bullish_frac','close_above_entry_frac',
    'max_bull_body_r4','closes_ge_f10','closes_ge_f15'
]


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x,start,end):
    a=int(x.index.searchsorted(start,'left')); b=int(x.index.searchsorted(end,'left'))
    return x.iloc[a:b]


def load_trades():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts','fill_ts','rebreak_complete_ts','exit_ts'):
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    for c in ('filled','target_reached','rebreak_confirmed'):
        if c in d.columns:d[c]=as_bool(d[c])
    d=d[d.partition.isin(MAJOR)&d.candidate.eq('BASE_H')&d.filled].copy()
    exp={'external':183,'development':297,'reference_validation':172}
    assert len(d)==652,len(d)
    for p,n in exp.items(): assert len(d[d.partition.eq(p)])==n,(p,len(d[d.partition.eq(p)]),n)
    d['label']=np.where(d.exit_reason.astype(str).eq('FULL_SL_HIGH_BREAK'),'BAD',
                        np.where(d.target_reached,'GOOD','OTHER'))
    assert int(d.label.eq('BAD').sum())==78,int(d.label.eq('BAD').sum())
    assert int(d.label.eq('GOOD').sum())==348,int(d.label.eq('GOOD').sum())
    assert int(d.label.eq('OTHER').sum())==226,int(d.label.eq('OTHER').sum())
    assert d.fill_ts.notna().all() and d.exit_ts.notna().all()
    d=d.sort_values(['partition','fill_ts','event_id']).reset_index(drop=True)
    return d


def build_h1(x5):
    h=x5[['open','high','low','close']].resample('1h',label='left',closed='left').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
    n=x5['close'].resample('1h',label='left',closed='left').size().rename('n')
    h=h.join(n)
    h=h[h.n.eq(12)].copy()
    h['complete_ts']=h.index+HOUR
    h['ema20']=h.close.astype(float).ewm(span=20,adjust=False).mean()
    h['ema50']=h.close.astype(float).ewm(span=50,adjust=False).mean()
    h['ema50_lag3']=h.ema50.shift(3)
    return h


def h1_at(h1,t):
    arr=h1.complete_ts.values
    # index is tz-aware, values are UTC ns; Timestamp value is UTC ns.
    pos=int(np.searchsorted(arr,np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None)),side='right')-1)
    assert pos>=3,(t,pos)
    r=h1.iloc[pos]
    assert pd.Timestamp(r.complete_ts)<=pd.Timestamp(t)
    return r


def streak_up(a,cap=3):
    a=np.asarray(a,float)
    if len(a)<2:return 0
    k=0
    for i in range(len(a)-1,0,-1):
        if a[i]>a[i-1]:
            k+=1
            if k>=cap:break
        else:break
    return int(k)


def reclaim_features(x5,r):
    t=pd.Timestamp(r.reclaim_complete_ts); bt=t-BAR5
    assert bt in x5.index,(bt,t)
    b=x5.loc[bt]
    o=float(b.open); h=float(b.high); l=float(b.low); c=float(b.close)
    rng=h-l
    if rng<=0:
        body=up=dn=0.0
    else:
        body=(c-o)/rng
        up=(h-max(o,c))/rng
        dn=(min(o,c)-l)/rng
    R=float(r.R4); L=float(r.L); H=float(r.H); F05=float(r.F05)
    return {
        'reclaim_pos_r4':(c-L)/R,
        'reclaim_body_frac':body,
        'reclaim_upper_wick_frac':up,
        'reclaim_lower_wick_frac':dn,
        'remaining_block_min_reclaim':float((pd.Timestamp(r.obs_end)-t)/pd.Timedelta(minutes=1)),
        'setup_f05_pos_r4':(F05-L)/R,
        'setup_f05_to_h_r4':(H-F05)/R,
        '_reclaim_close':c,
    }


def ema_features(h1,t,px,R):
    h=h1_at(h1,t)
    e20=float(h.ema20); e50=float(h.ema50); lag=float(h.ema50_lag3)
    assert np.isfinite(e20) and np.isfinite(e50) and np.isfinite(lag)
    return {
        'ema20_dist_r4':(px-e20)/R,
        'ema50_dist_r4':(px-e50)/R,
        'ema20_minus_50_r4':(e20-e50)/R,
        'ema50_slope3_r4':(e50-lag)/R,
    }


def checkpoint_ts(r,cp):
    if cp=='RECLAIM':return pd.Timestamp(r.reclaim_complete_ts)
    if cp=='FILL':return pd.Timestamp(r.fill_ts)
    if cp=='PLUS5':return pd.Timestamp(r.fill_ts)+BAR5
    if cp=='PLUS10':return pd.Timestamp(r.fill_ts)+2*BAR5
    if cp=='PLUS15':return pd.Timestamp(r.fill_ts)+3*BAR5
    raise KeyError(cp)


def path_features(x5,r,t):
    fill=pd.Timestamp(r.fill_ts); R=float(r.R4); L=float(r.L); entry=float(r.entry_px)
    q=fast_slice(x5,fill,t)
    assert len(q)>=1,(fill,t,len(q))
    closes=q.close.astype(float).to_numpy(); highs=q.high.astype(float).to_numpy(); lows=q.low.astype(float).to_numpy()
    opens=q.open.astype(float).to_numpy()
    cur=float(closes[-1])
    bull=np.maximum(closes-opens,0.0)
    F10=L+.10*R; F15=L+.15*R
    return {
        'current_close_pos_r4':(cur-L)/R,
        'net_close_from_entry_r4':(cur-entry)/R,
        'mae_high_r4':max(0.0,(float(np.max(highs))-entry)/R),
        'mae_close_r4':max(0.0,(float(np.max(closes))-entry)/R),
        'mfe_low_r4':max(0.0,(entry-float(np.min(lows)))/R),
        'rebreak_done':float(np.any(closes<L)),
        'higher_close_streak':float(streak_up(closes,3)),
        'higher_high_streak':float(streak_up(highs,3)),
        'bullish_frac':float(np.mean(closes>opens)),
        'close_above_entry_frac':float(np.mean(closes>entry)),
        'max_bull_body_r4':float(np.max(bull))/R,
        'closes_ge_f10':float(np.sum(closes>=F10)),
        'closes_ge_f15':float(np.sum(closes>=F15)),
        '_decision_price':cur,
    }


def make_features(trades,x5,h1):
    rows=[]
    for r in trades.itertuples(index=False):
        rf=reclaim_features(x5,r)
        for cp in CHECKPOINTS:
            t=checkpoint_ts(r,cp)
            base={
                'event_id':int(r.event_id),'partition':str(r.partition),'clock_block':str(r.clock_block),
                'regime':str(r.regime),'label':str(r.label),'checkpoint':cp,'decision_ts':t,
                'exit_ts':pd.Timestamp(r.exit_ts),'R4':float(r.R4),'H':float(r.H),'L':float(r.L),
                'F05':float(r.F05),'entry_px':float(r.entry_px),'target_name':str(r.target_name),
            }
            feat={k:v for k,v in rf.items() if not k.startswith('_')}
            if cp=='RECLAIM':
                px=float(rf['_reclaim_close'])
            else:
                feat.update({
                    'entry_pos_r4':(float(r.entry_px)-float(r.L))/float(r.R4),
                    'entry_gap_f05_r4':(float(r.entry_px)-float(r.F05))/float(r.R4),
                    'entry_to_h_r4':(float(r.H)-float(r.entry_px))/float(r.R4),
                    'reclaim_to_fill_min':float((pd.Timestamp(r.fill_ts)-pd.Timestamp(r.reclaim_complete_ts))/pd.Timedelta(minutes=1)),
                })
                if cp=='FILL':
                    px=float(r.entry_px)
                else:
                    pf=path_features(x5,r,t); px=float(pf.pop('_decision_price')); feat.update(pf)
            feat.update(ema_features(h1,t,px,float(r.R4)))
            if cp in ('RECLAIM','FILL'):
                for k in PATH_NUM: feat[k]=np.nan
            if cp=='RECLAIM':
                for k in FILL_NUM: feat[k]=np.nan
            label=str(r.label)
            if cp in ('PLUS5','PLUS10','PLUS15') and label in ('BAD','GOOD'):
                alive=bool(pd.Timestamp(r.exit_ts)>t)
            else:
                alive=True
            base['model_eligible']=bool(label in ('BAD','GOOD') and alive)
            base['resolved_before_or_at']=bool(label in ('BAD','GOOD') and not alive)
            rows.append({**base,**feat})
    out=pd.DataFrame(rows)
    assert len(out)==len(trades)*len(CHECKPOINTS)
    return out


def num_cols(cp):
    cols=list(RECLAIM_NUM)
    if cp!='RECLAIM': cols+=FILL_NUM
    if cp in ('PLUS5','PLUS10','PLUS15'): cols+=PATH_NUM
    return cols


def make_model(cp):
    nums=num_cols(cp)
    pre=ColumnTransformer([
        ('num',Pipeline([('imp',SimpleImputer(strategy='median')),('sc',StandardScaler())]),nums),
        ('cat',OneHotEncoder(handle_unknown='ignore'),CAT),
    ],remainder='drop')
    clf=LogisticRegression(C=1.0,class_weight='balanced',max_iter=2000,solver='liblinear',random_state=27)
    return Pipeline([('pre',pre),('clf',clf)]),nums


def score_all(features):
    scored=[]; thresholds=[]; coefs=[]; models={}
    for cp in CHECKPOINTS:
        z=features[features.checkpoint.eq(cp)].copy()
        tr=z[z.partition.eq('development')&z.model_eligible].copy()
        assert tr.label.isin(['BAD','GOOD']).all() and tr.label.nunique()==2,(cp,tr.label.value_counts().to_dict())
        model,nums=make_model(cp)
        X=tr[nums+CAT]; y=tr.label.eq('BAD').astype(int)
        model.fit(X,y)
        p=model.predict_proba(X)[:,1]
        auc=float(roc_auc_score(y,p))
        models[cp]=model
        for part in MAJOR:
            q=z[z.partition.eq(part)].copy()
            elig=q[q.model_eligible].copy()
            if len(elig): elig['bad_prob']=model.predict_proba(elig[nums+CAT])[:,1]
            q=q.merge(elig[['event_id','bad_prob']],on='event_id',how='left',validate='one_to_one')
            scored.append(q)
        dev_sc=pd.concat(scored[-1:],ignore_index=True) if False else None
        # Development threshold selection uses cumulative all-label denominators at this checkpoint.
        dz=z[z.partition.eq('development')].copy()
        de=dz[dz.model_eligible].copy()
        de['bad_prob']=model.predict_proba(de[nums+CAT])[:,1]
        for mode,cap in [('SAFE',.10),('AGGRESSIVE',.20)]:
            th,met=choose_threshold(dz,de,cap)
            thresholds.append({'checkpoint':cp,'mode':mode,'threshold':th,'development_auc':auc,**met})
        # coefficients are descriptive only
        names=model.named_steps['pre'].get_feature_names_out()
        vals=model.named_steps['clf'].coef_[0]
        order=np.argsort(np.abs(vals))[::-1]
        for rank,i in enumerate(order[:12],1):
            coefs.append({'checkpoint':cp,'rank':rank,'feature':str(names[i]),'coefficient':float(vals[i]),'abs_coefficient':float(abs(vals[i]))})
    sc=pd.concat(scored,ignore_index=True)
    return sc,pd.DataFrame(thresholds),pd.DataFrame(coefs),models


def choose_threshold(all_rows,eligible_scored,good_cap):
    bad_total=int(all_rows.label.eq('BAD').sum()); good_total=int(all_rows.label.eq('GOOD').sum())
    assert bad_total>0 and good_total>0
    probs=np.sort(eligible_scored.bad_prob.dropna().unique())
    candidates=[math.inf]+[float(x) for x in probs[::-1]]+[-math.inf]
    best=None
    for th in candidates:
        flagged=eligible_scored.bad_prob.ge(th) if np.isfinite(th) else (pd.Series(False,index=eligible_scored.index) if th>0 else pd.Series(True,index=eligible_scored.index))
        fb=int((flagged&eligible_scored.label.eq('BAD')).sum()); fg=int((flagged&eligible_scored.label.eq('GOOD')).sum())
        badcap=fb/bad_total; goodsac=fg/good_total
        if goodsac<=good_cap+EPS:
            key=(badcap,-goodsac,th)
            if best is None or key>best[0]: best=(key,th,fb,fg,badcap,goodsac)
    assert best is not None
    _,th,fb,fg,badcap,goodsac=best
    return th,{'dev_bad_flagged':fb,'dev_good_flagged':fg,'dev_bad_capture':badcap,'dev_good_sacrifice':goodsac}


def eval_metrics(all_rows,th):
    d=all_rows[all_rows.label.isin(['BAD','GOOD'])].copy()
    bad=d[d.label.eq('BAD')]; good=d[d.label.eq('GOOD')]
    bt=len(bad); gt=len(good)
    bad_alive=bad[bad.model_eligible]; good_alive=good[good.model_eligible]
    bad_late=bt-len(bad_alive); good_resolved=gt-len(good_alive)
    if np.isposinf(th):
        bflag=pd.Series(False,index=bad_alive.index); gflag=pd.Series(False,index=good_alive.index)
    elif np.isneginf(th):
        bflag=pd.Series(True,index=bad_alive.index); gflag=pd.Series(True,index=good_alive.index)
    else:
        bflag=bad_alive.bad_prob.ge(th); gflag=good_alive.bad_prob.ge(th)
    bf=int(bflag.sum()); gf=int(gflag.sum()); flagged=bf+gf
    return {
        'bad_total':int(bt),'bad_too_late':int(bad_late),'bad_eligible':int(len(bad_alive)),'bad_flagged':bf,
        'bad_capture_all':bf/bt if bt else np.nan,'bad_recall_eligible':bf/len(bad_alive) if len(bad_alive) else np.nan,
        'good_total':int(gt),'good_resolved_safe':int(good_resolved),'good_eligible':int(len(good_alive)),'good_flagged':gf,
        'good_sacrifice_all':gf/gt if gt else np.nan,'good_fpr_eligible':gf/len(good_alive) if len(good_alive) else np.nan,
        'flagged_n':flagged,'flag_precision_bad':bf/flagged if flagged else np.nan,
    }


def build_metrics(sc,thr):
    rows=[]
    for rr in thr.itertuples(index=False):
        cp=rr.checkpoint; mode=rr.mode; th=float(rr.threshold)
        for p in MAJOR:
            z=sc[sc.checkpoint.eq(cp)&sc.partition.eq(p)]
            rows.append({'scope':'PARTITION','name':p,'checkpoint':cp,'mode':mode,'threshold':th,**eval_metrics(z,th)})
        z=sc[sc.checkpoint.eq(cp)]
        rows.append({'scope':'POOL','name':'POOLED_MAJOR','checkpoint':cp,'mode':mode,'threshold':th,**eval_metrics(z,th)})
    return pd.DataFrame(rows)


def build_splits(sc,thr,kind):
    rows=[]
    values=CLOCKS if kind=='CLOCK' else REGIMES
    col='clock_block' if kind=='CLOCK' else 'regime'
    for rr in thr.itertuples(index=False):
        cp=rr.checkpoint; mode=rr.mode; th=float(rr.threshold)
        for v in values:
            z=sc[sc.checkpoint.eq(cp)&sc[col].eq(v)]
            rows.append({'checkpoint':cp,'mode':mode,col:v,'threshold':th,**eval_metrics(z,th)})
    return pd.DataFrame(rows)


def getm(m,scope,name,cp,mode):
    z=m[m.scope.eq(scope)&m.name.eq(name)&m.checkpoint.eq(cp)&m['mode'].eq(mode)]
    assert len(z)==1,(scope,name,cp,mode,len(z)); return z.iloc[0]


def support(m,cp,mode):
    oks=[]
    for p in ('external','reference_validation'):
        r=getm(m,'PARTITION',p,cp,mode)
        if mode=='SAFE':
            ok=bool(r.bad_total>=5 and r.bad_capture_all>=.25-EPS and r.good_sacrifice_all<=.15+EPS)
        else:
            ok=bool(r.bad_total>=5 and r.bad_capture_all>=.40-EPS and r.good_sacrifice_all<=.25+EPS)
        oks.append(ok)
    return bool(all(oks))


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def f3(x):return 'inf' if np.isposinf(x) else ('-inf' if np.isneginf(x) else f'{float(x):.3f}')


def main():
    trades=load_trades(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    h1=build_h1(x5); assert len(h1)>50000
    feat=make_features(trades,x5,h1); feat.to_csv(OUT_FEATURES,index=False)
    sc,thr,coef,models=score_all(feat)
    thr.to_csv(OUT_THRESH,index=False); coef.to_csv(OUT_COEF,index=False)
    met=build_metrics(sc,thr); met.to_csv(OUT_METRICS,index=False)
    clock=build_splits(sc,thr,'CLOCK'); clock.to_csv(OUT_CLOCK,index=False)
    regime=build_splits(sc,thr,'REGIME'); regime.to_csv(OUT_REGIME,index=False)

    supports=[]
    for cp in CHECKPOINTS:
        for mode in MODES:
            if support(met,cp,mode): supports.append((cp,mode))
    verdict='B27CV_FULL_LOSER_DETECTOR_REUSED_CANDIDATE' if supports else 'B27CV_FULL_LOSER_SEPARABILITY_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(
        f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\ntrades_major={len(trades)}\n'
        f'trades_external=183\ntrades_development=297\ntrades_validation=172\n'
        f'bad_major={int(trades.label.eq("BAD").sum())}\ngood_major={int(trades.label.eq("GOOD").sum())}\n'
        f'other_major={int(trades.label.eq("OTHER").sum())}\nfeature_rows={len(feat)}\nh1_complete_rows={len(h1)}\n'
        f'checkpoints={len(CHECKPOINTS)}\nuntouched_holdout=NONE\n')

    lines=['# B27CV — BTC 24H F05 SHORT Full-Loser Separability Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CS executable F05 identity reproduced: external 183 / development 297 / validation 172 / pooled major 652. Labels: BAD High-break 78 / GOOD clock-target 348 / OTHER 226.','',
           '**Classifier anatomy only:** detector trading WR/PF/expectancy/PnL are **N/A**. Models and thresholds were trained/selected development-only; external/reference_validation are reused-data confirmation, not untouched OOS.','',
           '## Primary checkpoint detector readout','',
           '| Checkpoint | Mode | Dev AUC | Threshold | External BAD caught / GOOD cut | Validation BAD caught / GOOD cut | Reused supported |',
           '|---|---|---:|---:|---|---|---|']
    for cp in CHECKPOINTS:
        for mode in MODES:
            tr=thr[thr.checkpoint.eq(cp)&thr['mode'].eq(mode)].iloc[0]
            e=getm(met,'PARTITION','external',cp,mode); v=getm(met,'PARTITION','reference_validation',cp,mode)
            sup=support(met,cp,mode)
            lines.append(f'| {cp} | {mode} | {float(tr.development_auc):.3f} | {f3(float(tr.threshold))} | {e.bad_flagged}/{e.bad_total} ({pct(e.bad_capture_all)}) / {e.good_flagged}/{e.good_total} ({pct(e.good_sacrifice_all)}) | {v.bad_flagged}/{v.bad_total} ({pct(v.bad_capture_all)}) / {v.good_flagged}/{v.good_total} ({pct(v.good_sacrifice_all)}) | {"YES" if sup else "NO"} |')

    lines += ['', '## Six clocks independently — SAFE operating points','',
              '| WIB | Checkpoint | BAD caught/all | GOOD cut/all | Precision among flagged |',
              '|---|---|---:|---:|---:|']
    for cb in CLOCKS:
        for cp in CHECKPOINTS:
            r=clock[(clock.clock_block.eq(cb))&clock.checkpoint.eq(cp)&clock['mode'].eq('SAFE')].iloc[0]
            lines.append(f'| {WIB[cb]} | {cp} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture_all)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice_all)}) | {pct(r.flag_precision_bad)} |')

    lines += ['', '## Regime splits — SAFE operating points','',
              '| Regime | Checkpoint | BAD caught/all | GOOD cut/all | Precision among flagged |',
              '|---|---|---:|---:|---:|']
    for rg in REGIMES:
        for cp in CHECKPOINTS:
            r=regime[(regime.regime.eq(rg))&regime.checkpoint.eq(cp)&regime['mode'].eq('SAFE')].iloc[0]
            lines.append(f'| {rg} | {cp} | {int(r.bad_flagged)}/{int(r.bad_total)} ({pct(r.bad_capture_all)}) | {int(r.good_flagged)}/{int(r.good_total)} ({pct(r.good_sacrifice_all)}) | {pct(r.flag_precision_bad)} |')

    lines += ['', '## Top model signals by absolute coefficient','',
              '| Checkpoint | Rank | Feature | Coefficient |', '|---|---:|---|---:|']
    for cp in CHECKPOINTS:
        z=coef[coef.checkpoint.eq(cp)].head(6)
        for r in z.itertuples(index=False):
            lines.append(f'| {cp} | {int(r.rank)} | `{r.feature}` | {float(r.coefficient):+.3f} |')

    if supports:
        supp=', '.join(f'{cp}/{mode}' for cp,mode in supports)
        lines += ['',f'Reused-supported detector operating points: **{supp}**.']
    else:
        lines += ['', 'Reused-supported detector operating points: **none**.']
    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              'A detector candidate here only establishes separability. It does not prove that actually skipping/aborting trades is profitable; that requires a separate causal economic simulation. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
