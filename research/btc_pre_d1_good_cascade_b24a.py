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

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_PRE_D1_GOOD_CASCADE_B24A_Result.md'
OUT_JSON = ROOT / 'BTC_PRE_D1_GOOD_CASCADE_B24A_Result.json'
OUT_EVENTS = ROOT / 'BTC_PRE_D1_GOOD_CASCADE_B24A_Events.csv'
OUT_BUCKETS = ROOT / 'BTC_PRE_D1_GOOD_CASCADE_B24A_Buckets.csv'

FEATURE_TFS = {
    'm15': ('15min', pd.Timedelta(minutes=15)),
    'h1': ('1h', pd.Timedelta(hours=1)),
    'h4': ('4h', pd.Timedelta(hours=4)),
    'd1': ('1d', pd.Timedelta(days=1)),
}
FEATURES = []
for tf in FEATURE_TFS:
    FEATURES += [f'{tf}_fast_gap', f'{tf}_slow_gap', f'{tf}_price_pos', f'{tf}_bull']


def on_times_resolution_safe(state: pd.Series) -> pd.DatetimeIndex:
    s = state.fillna(False).astype(bool)
    return s.index[s & ~s.shift(1, fill_value=False)]


def first_on_resolution_safe(on_idx: pd.DatetimeIndex, seed: pd.Timestamp):
    j = int(on_idx.searchsorted(seed, side='left'))
    if j >= len(on_idx):
        return pd.NaT
    t = on_idx[j]
    return t if t <= seed + b21.HORIZON else pd.NaT


def build_feature_maps(x5: pd.DataFrame, base_index: pd.DatetimeIndex):
    out = {}
    for tf, (rule, dur) in FEATURE_TFS.items():
        frame = b21._resample(x5, rule)
        av = b21._bull_available(frame, dur)
        z = av.reindex(base_index, method='ffill').copy()
        z[f'{tf}_fast_gap'] = (z.sma7 - z.sma25) / z.close
        z[f'{tf}_slow_gap'] = (z.sma25 - z.sma99) / z.close
        z[f'{tf}_price_pos'] = (z.close - z.sma25) / z.close
        z[f'{tf}_bull'] = z.bull.astype(float)
        out[tf] = z[[f'{tf}_fast_gap', f'{tf}_slow_gap', f'{tf}_price_pos', f'{tf}_bull']]
    return out


def make_events(casc: pd.DataFrame, states: pd.DataFrame, fmap: dict[str, pd.DataFrame]):
    c = casc[casc.stage_index >= 3].copy()
    rows = []
    for r in c.itertuples(index=False):
        t = pd.Timestamp(r.on_4h)
        if pd.isna(t) or t not in states.index:
            continue
        # Strictly pre-D1: Daily bull must still be OFF at the 4H anchor.
        if bool(states.loc[t, 'd1_bull']):
            continue
        if pd.isna(r.ret72):
            continue
        row = {
            'partition': r.partition,
            'seed_ts': r.seed_ts,
            'anchor_4h_ts': t,
            'on_1d': r.on_1d,
            'stage_index': int(r.stage_index),
            'ret72': float(r.ret72),
            'eventually_d1': int(r.stage_index == 4),
            'positive72': int(float(r.ret72) > 0),
            'good_d1_72h': int((r.stage_index == 4) and (float(r.ret72) > 0)),
        }
        for tf in FEATURE_TFS:
            vals = fmap[tf].loc[t]
            for col in vals.index:
                row[col] = float(vals[col]) if pd.notna(vals[col]) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


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


def fmt_pct(x):
    return '-' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{100*x:.2f}%'


def main():
    # Use the corrected B21 timestamp-safe event lookup.
    b21._on_times = on_times_resolution_safe
    b21._first_on = first_on_resolution_safe

    x5, coverage = b21.load5()
    states = b21.build_state_table(x5)
    casc = b21.build_cascades(states, x5)
    fmap = build_feature_maps(x5, states.index)
    ev = make_events(casc, states, fmap)

    train = ev[ev.partition.isin(['external', 'development'])].copy()
    val = ev[ev.partition == 'reference_validation'].copy()
    aug = ev[ev.partition == 'august'].copy()

    Xtr = train[FEATURES]
    ytr = train.good_d1_72h.to_numpy(int)
    Xv = val[FEATURES]
    yv = val.good_d1_72h.to_numpy(int)

    pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scale', StandardScaler()),
        ('lr', LogisticRegression(C=1.0, penalty='l2', class_weight='balanced', max_iter=5000, random_state=23)),
    ])
    pipe.fit(Xtr, ytr)
    val_score = pipe.predict_proba(Xv)[:, 1]
    val['score'] = val_score
    if len(aug):
        aug['score'] = pipe.predict_proba(aug[FEATURES])[:, 1]

    baseline = float(yv.mean()) if len(yv) else np.nan
    auc = safe_auc(yv, val_score)
    ap = float(average_precision_score(yv, val_score)) if len(yv) else np.nan
    buckets = [top_bucket(yv, val_score, f) for f in [0.05, 0.10, 0.20, 0.30]]

    # Secondary hindsight cohort: those later known to reach D1.
    vd1 = val[val.eventually_d1 == 1].copy()
    yd1 = vd1.positive72.to_numpy(int)
    sd1 = vd1.score.to_numpy(float)
    d1_auc = safe_auc(yd1, sd1) if len(vd1) else None

    # Standardized logistic coefficients for interpretation only.
    coefs = pipe.named_steps['lr'].coef_[0]
    coef_rows = sorted(zip(FEATURES, coefs), key=lambda z: abs(z[1]), reverse=True)

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

    # Persist scores for audit.
    full = ev.copy()
    full['score'] = np.nan
    full.loc[val.index, 'score'] = val['score']
    if len(aug):
        full.loc[aug.index, 'score'] = aug['score']
    full.to_csv(OUT_EVENTS, index=False)
    pd.DataFrame(buckets).to_csv(OUT_BUCKETS, index=False)

    payload = {
        'source_rows_5m': int(len(x5)),
        'coverage': float(coverage),
        'features': FEATURES,
        'train_n': int(len(train)),
        'train_good': int(ytr.sum()),
        'validation_n': int(len(val)),
        'validation_good': int(yv.sum()),
        'validation_baseline': baseline,
        'validation_auc': auc,
        'validation_average_precision': ap,
        'buckets': buckets,
        'validation_d1_cohort_n': int(len(vd1)),
        'validation_d1_positive': int(yd1.sum()) if len(vd1) else 0,
        'validation_d1_negative': int(len(vd1) - yd1.sum()) if len(vd1) else 0,
        'validation_d1_positive_rate': float(yd1.mean()) if len(vd1) else None,
        'validation_d1_forensic_auc': d1_auc,
        'coefficients_standardized': [{'feature': a, 'coef': float(b)} for a, b in coef_rows],
        'B24A_USEFUL_PRE_D1_DETECTOR': useful,
        'B24A_HIGH_PRECISION_CLUE': high_precision,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Pre-D1 Good Cascade B24A — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Question: at the first causal 4H-bull activation, while Daily bull is still OFF, can already-visible state geometry identify events that later become a Daily-bull cascade AND have positive 72h return?', '',
        'No candle-survival counting rule is used. Features are current causal SMA-state geometry only.', '',
        '## Primary real-time test — untouched reference validation', '',
        f'- Eligible pre-D1 4H events: **{len(val):,}**',
        f'- GOOD_D1_72H events: **{int(yv.sum()):,}**',
        f'- Baseline success prevalence: **{fmt_pct(baseline)}**',
        f'- ROC AUC: **{auc:.3f}**' if auc is not None else '- ROC AUC: -',
        f'- Average precision: **{ap:.3f}** ({ap/baseline:.2f}x baseline)' if baseline > 0 else f'- Average precision: **{ap:.3f}**', '',
        '| Highest detector scores | N | Successful | Precision | Recall of all successes | Lift vs baseline |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for b in buckets:
        lift = b['precision']/baseline if baseline > 0 else np.nan
        md.append(f"| Top {int(b['fraction']*100)}% | {b['n']} | {b['good']} | {fmt_pct(b['precision'])} | {fmt_pct(b['recall'])} | {lift:.2f}x |")

    md += ['', '## Secondary forensic view — old Daily-stage cohort', '',
           'This section is hindsight-only and is NOT a trading accuracy claim.', '',
           f'- Daily-stage events still eligible at the pre-D1 4H anchor: **{len(vd1)}**',
           f'- Positive 72h: **{int(yd1.sum()) if len(vd1) else 0}**',
           f'- Non-positive 72h: **{int(len(vd1)-yd1.sum()) if len(vd1) else 0}**',
           f'- Positive rate: **{fmt_pct(float(yd1.mean()) if len(vd1) else None)}**',
           f'- Detector AUC inside this hindsight cohort: **{d1_auc:.3f}**' if d1_auc is not None else '- Detector AUC inside this hindsight cohort: -', '',
           '## Strongest standardized model coefficients', '',
           '| Feature | Coefficient |', '|---|---:|']
    for feature, coef in coef_rows[:8]:
        md.append(f'| {feature} | {coef:.4f} |')

    md += ['', '## Frozen gates', '',
           f'- B24A_USEFUL_PRE_D1_DETECTOR: **{"PASS" if useful else "FAIL"}**',
           f'- B24A_HIGH_PRECISION_CLUE: **{"PASS" if high_precision else "FAIL"}**', '',
           'If the gates fail, this experiment is not useful as a real-time pre-D1 trading detector.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
