#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import btc_mtf_bull_cascade_b21 as b21
import btc_pre_d1_good_cascade_b24a as b24a

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_PRE_D1_FORWARD_B24B_Result.md'
OUT_JSON = ROOT / 'BTC_PRE_D1_FORWARD_B24B_Result.json'
OUT_EVENTS = ROOT / 'BTC_PRE_D1_FORWARD_B24B_Events.csv'
OUT_BUCKETS = ROOT / 'BTC_PRE_D1_FORWARD_B24B_Buckets.csv'
FEATURES = b24a.FEATURES


def top_bucket(y: np.ndarray, scores: np.ndarray, frac: float):
    n = len(y)
    k = max(1, int(math.ceil(n * frac)))
    order = np.argsort(-scores)
    pick = order[:k]
    total_good = int(y.sum())
    captured = int(y[pick].sum())
    return {
        'fraction': frac,
        'n': k,
        'good': captured,
        'precision': float(captured / k),
        'recall': float(captured / total_good) if total_good else None,
    }


def safe_auc(y, s):
    return float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else None


def pct(x):
    return '-' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{100*x:.2f}%'


def main():
    b21._on_times = b24a.on_times_resolution_safe
    b21._first_on = b24a.first_on_resolution_safe

    x5, coverage = b21.load5()
    states = b21.build_state_table(x5)
    casc = b21.build_cascades(states, x5)
    fmap = b24a.build_feature_maps(x5, states.index)
    ev = b24a.make_events(casc, states, fmap)

    fwd_rows = []
    for r in ev.itertuples(index=False):
        anchor = pd.Timestamp(r.anchor_4h_ts)
        f = b21._fwd(x5, anchor, 72)
        if not f['n_ok']:
            continue
        row = r._asdict()
        row['fwd72_ret_from_4h'] = float(f['ret'])
        row['fwd72_mfe_from_4h'] = float(f['mfe'])
        row['fwd72_mae_from_4h'] = float(f['mae'])
        row['fwd72_positive'] = int(float(f['ret']) > 0)
        row['good_d1_fwd72'] = int((int(r.eventually_d1) == 1) and (float(f['ret']) > 0))
        fwd_rows.append(row)
    z = pd.DataFrame(fwd_rows)

    train = z[z.partition.isin(['external', 'development'])].copy()
    val = z[z.partition == 'reference_validation'].copy()
    aug = z[z.partition == 'august'].copy()

    Xtr = train[FEATURES]
    ytr = train.good_d1_fwd72.to_numpy(int)
    Xv = val[FEATURES]
    yv = val.good_d1_fwd72.to_numpy(int)

    pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scale', StandardScaler()),
        ('lr', LogisticRegression(C=1.0, penalty='l2', class_weight='balanced', max_iter=5000, random_state=23)),
    ])
    pipe.fit(Xtr, ytr)
    sv = pipe.predict_proba(Xv)[:, 1]
    val['score'] = sv
    if len(aug):
        aug['score'] = pipe.predict_proba(aug[FEATURES])[:, 1]

    baseline = float(yv.mean())
    auc = safe_auc(yv, sv)
    ap = float(average_precision_score(yv, sv))
    buckets = [top_bucket(yv, sv, f) for f in [0.05, 0.10, 0.20, 0.30]]

    vd1 = val[val.eventually_d1 == 1].copy()
    d1_pos = int(vd1.fwd72_positive.sum())
    d1_n = int(len(vd1))
    d1_rate = float(vd1.fwd72_positive.mean()) if d1_n else None
    d1_auc = safe_auc(vd1.fwd72_positive.to_numpy(int), vd1.score.to_numpy(float)) if d1_n else None

    useful = bool(
        auc is not None and auc >= 0.65 and
        ap >= 1.50 * baseline and
        buckets[2]['precision'] >= 1.50 * baseline and
        buckets[2]['recall'] is not None and buckets[2]['recall'] >= 0.30
    )
    high_precision = bool(
        buckets[1]['precision'] >= 2.0 * baseline and
        buckets[1]['recall'] is not None and buckets[1]['recall'] >= 0.20
    )

    coefs = pipe.named_steps['lr'].coef_[0]
    coef_rows = sorted(zip(FEATURES, coefs), key=lambda x: abs(x[1]), reverse=True)

    full = z.copy()
    full['score'] = np.nan
    full.loc[val.index, 'score'] = val.score
    if len(aug):
        full.loc[aug.index, 'score'] = aug.score
    full.to_csv(OUT_EVENTS, index=False)
    pd.DataFrame(buckets).to_csv(OUT_BUCKETS, index=False)

    payload = {
        'source_rows_5m': int(len(x5)),
        'coverage': float(coverage),
        'train_n': int(len(train)),
        'train_good': int(ytr.sum()),
        'validation_n': int(len(val)),
        'validation_good': int(yv.sum()),
        'validation_baseline': baseline,
        'validation_auc': auc,
        'validation_average_precision': ap,
        'buckets': buckets,
        'validation_eventual_d1_n': d1_n,
        'validation_eventual_d1_fwd72_positive': d1_pos,
        'validation_eventual_d1_fwd72_nonpositive': d1_n-d1_pos,
        'validation_eventual_d1_fwd72_positive_rate': d1_rate,
        'validation_eventual_d1_forensic_auc': d1_auc,
        'coefficients_standardized': [{'feature': f, 'coef': float(c)} for f, c in coef_rows],
        'B24B_USEFUL_PRE_D1_FORWARD_DETECTOR': useful,
        'B24B_HIGH_PRECISION_CLUE': high_precision,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Pre-D1 Forward B24B — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'B24B corrects B24A: the outcome clock starts at the causal 4H detector time, not at the earlier 5m seed.', '',
        '## Primary real-time test — untouched reference validation', '',
        f'- Eligible pre-D1 4H events with full next-72h data: **{len(val):,}**',
        f'- GOOD_D1_FWD72 events: **{int(yv.sum()):,}**',
        f'- Baseline prevalence: **{pct(baseline)}**',
        f'- ROC AUC: **{auc:.3f}**' if auc is not None else '- ROC AUC: -',
        f'- Average precision: **{ap:.3f}** ({ap/baseline:.2f}x baseline)' if baseline > 0 else f'- Average precision: **{ap:.3f}**', '',
        '| Highest detector scores | N | Successful | Precision | Recall | Lift vs baseline |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for b in buckets:
        lift = b['precision']/baseline if baseline > 0 else np.nan
        md.append(f"| Top {int(b['fraction']*100)}% | {b['n']} | {b['good']} | {pct(b['precision'])} | {pct(b['recall'])} | {lift:.2f}x |")

    md += ['', '## Eventual-Daily cohort — future outcome from the 4H decision time', '',
           f'- Eventual Daily events: **{d1_n}**',
           f'- Price positive over NEXT 72h from 4H anchor: **{d1_pos}**',
           f'- Non-positive: **{d1_n-d1_pos}**',
           f'- Future-positive rate: **{pct(d1_rate)}**',
           f'- Detector AUC inside this eventual-Daily cohort: **{d1_auc:.3f}**' if d1_auc is not None else '- Detector AUC inside this eventual-Daily cohort: -', '',
           '## Strongest standardized coefficients', '', '| Feature | Coefficient |', '|---|---:|']
    for f, c in coef_rows[:8]:
        md.append(f'| {f} | {c:.4f} |')

    md += ['', '## Frozen gates', '',
           f'- B24B_USEFUL_PRE_D1_FORWARD_DETECTOR: **{"PASS" if useful else "FAIL"}**',
           f'- B24B_HIGH_PRECISION_CLUE: **{"PASS" if high_precision else "FAIL"}**', '',
           'B24B is the fair forward test. B24A must not be used to claim trading performance.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
