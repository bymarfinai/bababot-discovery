#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, recall_score, brier_score_loss

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_regime_detector_audit_b27bg as b27bg

ROOT = Path(__file__).resolve().parent.parent
EP_FILE = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_Episodes.csv'
OUT_MD = ROOT / 'BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Result.md'
OUT_PRED = ROOT / 'BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Predictions.csv'
OUT_MODEL = ROOT / 'BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Models.csv'
OUT_STATE = ROOT / 'BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_StateSummary.csv'
OUT_STATUS = ROOT / 'BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Status.txt'

MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
ORIGINS = ('BULL','BEAR')
FEATURES = (
    'dir_ema_spread_atr',
    'dir_close_ema20_atr',
    'dir_ema7_slope_atr',
    'dir_ema20_slope_atr',
    'dir_body_atr',
    'bar_range_atr',
)
H4 = pd.Timedelta(hours=4)


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def load_episodes() -> pd.DataFrame:
    e = pd.read_csv(EP_FILE)
    e['first_sideways_ts'] = pd.to_datetime(e['first_sideways_ts'], utc=True)
    e['feature_available_ts'] = pd.to_datetime(e['feature_available_ts'], utc=True)
    e['source_bar_start'] = pd.to_datetime(e['source_bar_start'], utc=True)
    for c in FEATURES:
        e[c] = pd.to_numeric(e[c], errors='raise')
    e['y_resume'] = e['outcome'].eq('RESUME').astype(int)
    # Exact B27BI identity.
    assert len(e) == 1023, len(e)
    assert int(e.y_resume.sum()) == 527
    assert int((e.y_resume == 0).sum()) == 496
    assert int((e.origin_state == 'BULL').sum()) == 532
    assert int((e.origin_state == 'BEAR').sum()) == 491
    assert set(e.origin_state.unique()) == set(ORIGINS)
    assert (e.feature_available_ts == e.first_sideways_ts).all()
    assert (e.source_bar_start + H4 == e.feature_available_ts).all()
    assert not e.duplicated(['first_sideways_ts']).any()
    return e


def fit_models(e: pd.DataFrame):
    models = {}
    rows = []
    for origin in ORIGINS:
        tr = e[(e.partition == 'development') & (e.origin_state == origin)].copy()
        assert len(tr) >= 100
        X = tr.loc[:, FEATURES].to_numpy(float)
        y = tr.y_resume.to_numpy(int)
        mu = X.mean(axis=0)
        sd = X.std(axis=0, ddof=0)
        assert np.all(np.isfinite(mu)) and np.all(np.isfinite(sd)) and np.all(sd > 0)
        Z = (X - mu) / sd
        clf = LogisticRegression(
            penalty='l2', C=1.0, solver='lbfgs', max_iter=1000,
            class_weight=None, fit_intercept=True,
        )
        clf.fit(Z, y)
        models[origin] = (mu, sd, clf)
        for i, f in enumerate(FEATURES):
            rows.append({
                'origin': origin, 'feature': f,
                'development_mean': float(mu[i]),
                'development_std': float(sd[i]),
                'coefficient_standardized': float(clf.coef_[0, i]),
                'intercept': float(clf.intercept_[0]),
            })
    return models, pd.DataFrame(rows)


def predict_all(e: pd.DataFrame, models) -> pd.DataFrame:
    out = e.copy()
    out['p_resume'] = np.nan
    for origin in ORIGINS:
        q = out.origin_state == origin
        mu, sd, clf = models[origin]
        X = out.loc[q, FEATURES].to_numpy(float)
        Z = (X - mu) / sd
        out.loc[q, 'p_resume'] = clf.predict_proba(Z)[:, 1]
    assert out.p_resume.notna().all()
    out['pred_resume'] = out.p_resume >= 0.50
    out['predicted_outcome'] = np.where(out.pred_resume, 'RESUME', 'TRANSITION')
    out['correct'] = out.pred_resume.astype(int).eq(out.y_resume)
    return out


def metric_row(q: pd.DataFrame, origin: str, part: str) -> dict:
    n = len(q)
    if n == 0:
        return {'origin':origin,'partition':part,'n':0}
    y = q.y_resume.to_numpy(int)
    p = q.p_resume.to_numpy(float)
    yh = q.pred_resume.astype(int).to_numpy()
    auc = roc_auc_score(y,p) if len(np.unique(y)) == 2 else np.nan
    bal = balanced_accuracy_score(y,yh) if len(np.unique(y)) == 2 else np.nan
    sens = recall_score(y,yh,pos_label=1,zero_division=0)
    spec = recall_score(y,yh,pos_label=0,zero_division=0)
    return {
        'origin':origin,'partition':part,'n':n,
        'actual_resume_rate':float(y.mean()),
        'pred_resume_rate':float(yh.mean()),
        'auc':float(auc) if np.isfinite(auc) else np.nan,
        'balanced_accuracy':float(bal) if np.isfinite(bal) else np.nan,
        'resume_recall':float(sens),
        'transition_recall':float(spec),
        'brier':float(brier_score_loss(y,p)),
        'tp_resume':int(((y==1)&(yh==1)).sum()),
        'fn_resume_as_transition':int(((y==1)&(yh==0)).sum()),
        'fp_transition_as_resume':int(((y==0)&(yh==1)).sum()),
        'tn_transition':int(((y==0)&(yh==0)).sum()),
    }


def classifier_metrics(p: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for origin in ORIGINS:
        for part in (*MAJOR,'POOLED_OOS','august'):
            if part == 'POOLED_OOS':
                q=p[(p.origin_state==origin)&p.partition.isin(OOS)]
            else:
                q=p[(p.origin_state==origin)&(p.partition==part)]
            rows.append(metric_row(q,origin,part))
    return pd.DataFrame(rows)


def apply_redesign(reg: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    z = reg.sort_values('effective_ts').reset_index(drop=True).copy()
    z['raw_regime'] = z['regime'].astype(str)
    z['redesigned_regime'] = z['raw_regime']
    z['b27bj_tag'] = ''
    pmap = pred.set_index('first_sideways_ts')[['origin_state','pred_resume','p_resume','outcome']]

    prev_raw = z.raw_regime.shift(1)
    first_side = (z.raw_regime == 'SIDEWAYS') & prev_raw.isin(ORIGINS) & ((z.effective_ts-z.effective_ts.shift(1))==H4)
    matched=0; inherited=0
    for i in z.index[first_side]:
        ts=z.at[i,'effective_ts']
        if ts not in pmap.index:
            # B27BH reported exactly one censored/gap/boundary SIDEWAYS episode; leave raw.
            z.at[i,'b27bj_tag']='UNLABELED_FIRST_SIDEWAYS'
            continue
        r=pmap.loc[ts]
        assert str(r.origin_state) == str(prev_raw.iloc[i])
        matched += 1
        if bool(r.pred_resume):
            z.at[i,'redesigned_regime']=str(r.origin_state)
            z.at[i,'b27bj_tag']='INHERITED_PAUSE'
            inherited += 1
        else:
            z.at[i,'b27bj_tag']='EXPOSE_SIDEWAYS'
    assert matched == 1023, matched
    # Never relabel raw directional bars.
    d=z.raw_regime.isin(ORIGINS)
    assert (z.loc[d,'redesigned_regime'] == z.loc[d,'raw_regime']).all()
    return z, inherited


def summarize_variant(z: pd.DataFrame, col: str, variant: str) -> pd.DataFrame:
    r=z.copy()
    r['regime']=r[col]
    # rebuild global episode segmentation under the chosen exposed state.
    gap=r.effective_ts.diff()
    new_ep=r.regime.ne(r.regime.shift(1)) | gap.ne(H4)
    r['episode_id']=new_ep.cumsum().astype(int)
    e=b27bg.episode_table(r)
    t=b27bg.transition_table(r)
    s=b27bg.summarize(r,e,t)
    s['variant']=variant
    return s


def max_occ_drift(s: pd.DataFrame) -> float:
    q=s[s.partition.isin(MAJOR)].pivot(index='regime',columns='partition',values='occupancy')
    m=0.0
    for state in ('BULL','BEAR','SIDEWAYS'):
        vals=q.loc[state].dropna().astype(float).to_numpy()
        if len(vals): m=max(m,float(vals.max()-vals.min()))
    return m


def direct_share(s: pd.DataFrame) -> float:
    q=s[(s.partition=='POOLED_MAJOR') & (s.regime=='BULL')].iloc[0]
    changes=int(q.state_changes)
    return float(q.direct_bull_bear_changes/changes) if changes else np.nan


def main():
    e=load_episodes()
    models, model_df=fit_models(e)
    p=predict_all(e,models)
    cm=classifier_metrics(p)

    x5,coverage=b21.load5()
    assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12
    reg,_=b27bg.build_effective(x5)
    raw_flip=b27bg.flipback_stats(reg,'POOLED_MAJOR')
    assert raw_flip[0]==459 and raw_flip[1]==2202, raw_flip

    z,inherited=apply_redesign(reg,p)
    raw_s=summarize_variant(z,'raw_regime','RAW')
    new_s=summarize_variant(z,'redesigned_regime','B27BJ')
    ss=pd.concat([raw_s,new_s],ignore_index=True)
    new_reg=z.copy(); new_reg['regime']=new_reg['redesigned_regime']
    new_flip=b27bg.flipback_stats(new_reg,'POOLED_MAJOR')

    raw_drift=max_occ_drift(raw_s)
    new_drift=max_occ_drift(new_s)
    assert abs(raw_drift-.205) < .01, raw_drift

    # Frozen promotion gates.
    gate_identity=True
    gate_auc=True
    for origin in ORIGINS:
        for part in OOS:
            r=cm[(cm.origin==origin)&(cm.partition==part)].iloc[0]
            gate_auc = gate_auc and float(r.auc) >= .60
    gate_bal=True; gate_spec=True
    for origin in ORIGINS:
        r=cm[(cm.origin==origin)&(cm.partition=='POOLED_OOS')].iloc[0]
        gate_bal = gate_bal and float(r.balanced_accuracy) >= .57
        gate_spec = gate_spec and float(r.transition_recall) >= .55
    gate_flip=(float(new_flip[2]) < float(raw_flip[2])) and (float(new_flip[2]) <= .18)
    gate_persist=True
    for part in MAJOR:
        for state in ORIGINS:
            r=new_s[(new_s.partition==part)&(new_s.regime==state)].iloc[0]
            gate_persist = gate_persist and float(r.persistence) >= .60
    gate_drift=new_drift <= raw_drift + 1e-12

    supported=all([gate_identity,gate_auc,gate_bal,gate_spec,gate_flip,gate_persist,gate_drift])
    verdict='B27BJ_MAGNITUDE_AWARE_REDESIGN_SUPPORTED' if supported else 'B27BJ_MAGNITUDE_AWARE_REDESIGN_NOT_SUPPORTED'

    p.to_csv(OUT_PRED,index=False)
    model_df.to_csv(OUT_MODEL,index=False)
    ss.to_csv(OUT_STATE,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BJ — BTC 24H Magnitude-Aware SIDEWAYS Redesign Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Detector redesign only; no LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, or session optimization was used.','',
        'B27BI identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**','',
        '## Frozen model','',
        'Separate BULL-origin and BEAR-origin L2 logistic regressions were fit on **development only**, using the six preregistered B27BI continuous causal features. External and reference_validation were not used for scaling, fitting, thresholding, feature selection, or model choice. Threshold was frozen at `P(RESUME)>=0.50`.','',
        '## Classifier metrics','',
        '| Origin | Partition | N | Actual resume | Pred resume | AUC | Balanced acc | Resume recall | Transition recall | Brier |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for origin in ORIGINS:
        for part in ('development','external','reference_validation','POOLED_OOS','august'):
            r=cm[(cm.origin==origin)&(cm.partition==part)].iloc[0]
            if int(r.n)==0:
                lines.append(f'| {origin} | {part} | 0 | - | - | - | - | - | - | - |')
            else:
                lines.append(f'| {origin} | {part} | {int(r.n)} | {fmt_pct(r.actual_resume_rate)} | {fmt_pct(r.pred_resume_rate)} | {r.auc:.3f} | {r.balanced_accuracy:.3f} | {fmt_pct(r.resume_recall)} | {fmt_pct(r.transition_recall)} | {r.brier:.3f} |')

    lines += ['', '## OOS confusion accounting','',
              '| Origin | OOS N | RESUME->RESUME | RESUME->TRANSITION | TRANSITION->RESUME (4h delayed SIDEWAYS) | TRANSITION->TRANSITION |',
              '|---|---:|---:|---:|---:|---:|']
    for origin in ORIGINS:
        r=cm[(cm.origin==origin)&(cm.partition=='POOLED_OOS')].iloc[0]
        lines.append(f'| {origin} | {int(r.n)} | {int(r.tp_resume)} | {int(r.fn_resume_as_transition)} | {int(r.fp_transition_as_resume)} | {int(r.tn_transition)} |')

    lines += ['', '## Raw vs redesigned detector','',
              f'- Raw pooled-major one-interval flip-back: **{raw_flip[0]}/{raw_flip[1]} = {fmt_pct(raw_flip[2])}**.',
              f'- B27BJ pooled-major one-interval flip-back: **{new_flip[0]}/{new_flip[1]} = {fmt_pct(new_flip[2])}**.',
              f'- First-SIDEWAYS intervals tagged `INHERITED_PAUSE`: **{inherited}**.',
              f'- Raw maximum major-partition occupancy drift: **{100*raw_drift:.1f}pp**.',
              f'- B27BJ maximum major-partition occupancy drift: **{100*new_drift:.1f}pp**.',
              f'- Raw direct BULL<->BEAR change share: **{fmt_pct(direct_share(raw_s))}**.',
              f'- B27BJ direct BULL<->BEAR change share: **{fmt_pct(direct_share(new_s))}**.','',
              '### BULL / BEAR persistence by partition','',
              '| Partition | State | Raw persistence | B27BJ persistence | Raw occupancy | B27BJ occupancy |',
              '|---|---|---:|---:|---:|---:|']
    for part in (*MAJOR,'POOLED_MAJOR'):
        for state in ORIGINS:
            a=raw_s[(raw_s.partition==part)&(raw_s.regime==state)].iloc[0]
            b=new_s[(new_s.partition==part)&(new_s.regime==state)].iloc[0]
            lines.append(f'| {part} | {state} | {fmt_pct(a.persistence)} | {fmt_pct(b.persistence)} | {fmt_pct(a.occupancy)} | {fmt_pct(b.occupancy)} |')

    lines += ['', '## Frozen promotion gate','',
              f'- Identity / causality: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- AUC >=0.60 in external AND validation for each origin: **{"PASS" if gate_auc else "FAIL"}**.',
              f'- Pooled-OOS balanced accuracy >=0.57 for each origin: **{"PASS" if gate_bal else "FAIL"}**.',
              f'- Pooled-OOS TRANSITION recall >=0.55 for each origin: **{"PASS" if gate_spec else "FAIL"}**.',
              f'- Flip-back improves and <=18.0%: **{"PASS" if gate_flip else "FAIL"}**.',
              f'- BULL/BEAR persistence >=60% in every major partition: **{"PASS" if gate_persist else "FAIL"}**.',
              f'- Occupancy drift does not worsen vs raw: **{"PASS" if gate_drift else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              '## Interpretation boundary','',
              'If supported, B27BJ only supports this exact one-bar magnitude-aware inherited-pause redesign as a regime detector candidate. It does not establish any trading direction or entry rule. If not supported, no B27BJ threshold/model/state semantics may be modified post hoc; a new experiment ID is required.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
