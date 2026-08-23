#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_sideways_continuation_transition_features_b27bi as b27bi

ROOT = Path(__file__).resolve().parent.parent
PRED_FILE = ROOT / 'BTC_24H_MAGNITUDE_AWARE_SIDEWAYS_REDESIGN_B27BJ_Predictions.csv'
OUT_MD = ROOT / 'BTC_24H_BEAR_FALSE_PAUSE_ANATOMY_B27BK_Result.md'
OUT_COHORT = ROOT / 'BTC_24H_BEAR_FALSE_PAUSE_ANATOMY_B27BK_Cohort.csv'
OUT_FEAT = ROOT / 'BTC_24H_BEAR_FALSE_PAUSE_ANATOMY_B27BK_FeatureSummary.csv'
OUT_STATUS = ROOT / 'BTC_24H_BEAR_FALSE_PAUSE_ANATOMY_B27BK_Status.txt'

OOS = ('external','reference_validation')
H4 = pd.Timedelta(hours=4)

EXISTING = (
    'dir_ema_spread_atr',
    'dir_close_ema20_atr',
    'dir_ema7_slope_atr',
    'dir_ema20_slope_atr',
    'dir_body_atr',
    'bar_range_atr',
)
NEW_FEATURES = (
    'dir_close_ema7_atr',
    'dir_close_change_atr',
    'dir_high_change_atr',
    'dir_low_change_atr',
    'dir_spread_change_atr',
    'aligned_close_location',
    'counter_rejection_wick_fraction',
    'aligned_extension_wick_fraction',
    'range_ratio_prev',
    'atr_ratio_prev',
    'aligned_structure_margin',
    'aligned_structure_delta',
    'opposite_structure_delta',
    'prior_directional_age',
)
FEATURES = EXISTING + NEW_FEATURES + ('p_resume',)
BUCKETS = ('TRUE_PAUSE','FALSE_TRANSITION','FALSE_PAUSE','TRUE_TRANSITION')


def rank_auc(values: pd.Series, positive: pd.Series) -> float:
    x = pd.to_numeric(values, errors='coerce')
    y = positive.astype(bool)
    ok = x.notna() & y.notna()
    x=x[ok]; y=y[ok]
    n1=int(y.sum()); n0=int((~y).sum())
    if n1==0 or n0==0:
        return np.nan
    ranks=x.rank(method='average')
    s1=float(ranks[y].sum())
    return (s1 - n1*(n1+1)/2.0)/(n1*n0)


def fmt(v, d=3):
    return '-' if pd.isna(v) else f'{float(v):.{d}f}'


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def load_predictions() -> pd.DataFrame:
    p=pd.read_csv(PRED_FILE)
    for c in ('first_sideways_ts','source_bar_start','feature_available_ts'):
        p[c]=pd.to_datetime(p[c],utc=True)
    p['pred_resume']=p.pred_resume.astype(str).str.lower().eq('true')
    p['y_resume']=pd.to_numeric(p.y_resume,errors='raise').astype(int)
    p['p_resume']=pd.to_numeric(p.p_resume,errors='raise')
    q=p[(p.origin_state=='BEAR') & p.partition.isin(OOS)].copy()
    assert len(q)==242, len(q)
    q['confusion_bucket']=np.select(
        [
            (q.y_resume==1)&q.pred_resume,
            (q.y_resume==1)&(~q.pred_resume),
            (q.y_resume==0)&q.pred_resume,
            (q.y_resume==0)&(~q.pred_resume),
        ],
        ['TRUE_PAUSE','FALSE_TRANSITION','FALSE_PAUSE','TRUE_TRANSITION'],
        default='ERROR'
    )
    vc=q.confusion_bucket.value_counts().to_dict()
    expected={'TRUE_PAUSE':79,'FALSE_TRANSITION':32,'FALSE_PAUSE':74,'TRUE_TRANSITION':57}
    assert vc==expected, (vc,expected)
    assert q.first_sideways_ts.is_unique
    return q.sort_values('first_sideways_ts').reset_index(drop=True)


def build_features(q: pd.DataFrame) -> pd.DataFrame:
    x5,coverage=b21.load5()
    assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12
    reg=b27bi.build_extended_regime(x5).sort_values('effective_ts').reset_index(drop=True)
    by_ts={pd.Timestamp(t):i for i,t in enumerate(reg.effective_ts)}
    rows=[]
    for r in q.itertuples(index=False):
        ts=pd.Timestamp(r.first_sideways_ts)
        assert ts in by_ts
        i=by_ts[ts]
        assert i>0
        cur=reg.iloc[i]; prev=reg.iloc[i-1]
        assert str(cur.regime)=='SIDEWAYS'
        assert str(prev.regime)=='BEAR'
        assert pd.Timestamp(cur.effective_ts)==ts
        assert pd.Timestamp(cur.available_ts)==ts
        assert pd.Timestamp(cur.source_bar_start)+H4==ts
        assert pd.Timestamp(cur.effective_ts)-pd.Timestamp(prev.effective_ts)==H4

        atr=float(cur.atr14); patr=float(prev.atr14)
        assert atr>0 and patr>0
        rng=float(cur.high)-float(cur.low)
        prng=float(prev.high)-float(prev.low)
        assert rng>0 and prng>0
        sgn=-1.0
        upper=float(cur.high)-max(float(cur.open),float(cur.close))
        lower=min(float(cur.open),float(cur.close))-float(cur.low)
        assert upper>=-1e-9 and lower>=-1e-9
        upper=max(0.0,upper); lower=max(0.0,lower)

        aligned=min(int(cur.lh),int(cur.ll))
        paligned=min(int(prev.lh),int(prev.ll))
        opposite=min(int(cur.hh),int(cur.hl))
        popposite=min(int(prev.hh),int(prev.hl))

        calc={
            'dir_ema_spread_atr': sgn*(float(cur.ema7)-float(cur.ema20))/atr,
            'dir_close_ema20_atr': sgn*(float(cur.close)-float(cur.ema20))/atr,
            'dir_ema7_slope_atr': sgn*(float(cur.ema7)-float(prev.ema7))/atr,
            'dir_ema20_slope_atr': sgn*(float(cur.ema20)-float(prev.ema20))/atr,
            'dir_body_atr': sgn*(float(cur.close)-float(cur.open))/atr,
            'bar_range_atr': rng/atr,
            'dir_close_ema7_atr': sgn*(float(cur.close)-float(cur.ema7))/atr,
            'dir_close_change_atr': sgn*(float(cur.close)-float(prev.close))/atr,
            'dir_high_change_atr': sgn*(float(cur.high)-float(prev.high))/atr,
            'dir_low_change_atr': sgn*(float(cur.low)-float(prev.low))/atr,
            'dir_spread_change_atr': (
                sgn*(float(cur.ema7)-float(cur.ema20)) -
                sgn*(float(prev.ema7)-float(prev.ema20))
            )/atr,
            'aligned_close_location': (float(cur.high)-float(cur.close))/rng,
            'counter_rejection_wick_fraction': upper/rng,
            'aligned_extension_wick_fraction': lower/rng,
            'range_ratio_prev': rng/prng,
            'atr_ratio_prev': atr/patr,
            'aligned_structure_margin': float(aligned-opposite),
            'aligned_structure_delta': float(aligned-paligned),
            'opposite_structure_delta': float(opposite-popposite),
            'prior_directional_age': float(r.prior_directional_age),
            'p_resume': float(r.p_resume),
        }
        # Exact reproduction of the six parent features from independently rebuilt bars.
        for f in EXISTING:
            assert np.isclose(float(calc[f]),float(getattr(r,f)),rtol=1e-10,atol=1e-10), (ts,f,calc[f],getattr(r,f))
        row={
            'episode_id':int(r.episode_id),
            'partition':str(r.partition),
            'first_sideways_ts':ts,
            'actual_outcome':str(r.outcome),
            'predicted_outcome':str(r.predicted_outcome),
            'confusion_bucket':str(r.confusion_bucket),
            'pred_resume':bool(r.pred_resume),
            'y_resume':int(r.y_resume),
            'hh':int(cur.hh),'hl':int(cur.hl),'lh':int(cur.lh),'ll':int(cur.ll),
            'prev_hh':int(prev.hh),'prev_hl':int(prev.hl),'prev_lh':int(prev.lh),'prev_ll':int(prev.ll),
        }
        row.update(calc)
        rows.append(row)
    out=pd.DataFrame(rows)
    assert len(out)==242
    assert out.confusion_bucket.value_counts().to_dict()=={'TRUE_PAUSE':79,'FALSE_PAUSE':74,'TRUE_TRANSITION':57,'FALSE_TRANSITION':32}
    assert np.isfinite(out[list(FEATURES)].to_numpy(float)).all()
    return out


def summary_row(q: pd.DataFrame, part: str, feat: str) -> dict:
    a=q[q.confusion_bucket=='TRUE_PAUSE'][feat]
    b=q[q.confusion_bucket=='FALSE_PAUSE'][feat]
    y=q.confusion_bucket.eq('TRUE_PAUSE')
    return {
        'table':'PRIMARY_INHERITED_ONLY',
        'partition':part,'feature':feat,
        'true_pause_n':int(len(a)),'false_pause_n':int(len(b)),
        'true_pause_median':float(a.median()) if len(a) else np.nan,
        'false_pause_median':float(b.median()) if len(b) else np.nan,
        'median_diff':float(a.median()-b.median()) if len(a) and len(b) else np.nan,
        'true_pause_mean':float(a.mean()) if len(a) else np.nan,
        'false_pause_mean':float(b.mean()) if len(b) else np.nan,
        'auc_true_pause_high':rank_auc(q[feat],y),
    }


def feature_summary(d: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for part in (*OOS,'POOLED_OOS'):
        q=d.copy() if part=='POOLED_OOS' else d[d.partition==part].copy()
        inherited=q[q.confusion_bucket.isin(['TRUE_PAUSE','FALSE_PAUSE'])].copy()
        for feat in FEATURES:
            rows.append(summary_row(inherited,part,feat))
        # Four-bucket control anatomy, descriptive only.
        for feat in FEATURES:
            for bucket in BUCKETS:
                x=q[q.confusion_bucket==bucket][feat]
                rows.append({
                    'table':'FOUR_BUCKET_CONTROL','partition':part,'feature':feat,'bucket':bucket,
                    'n':int(len(x)),'median':float(x.median()) if len(x) else np.nan,
                    'mean':float(x.mean()) if len(x) else np.nan,
                })
    return pd.DataFrame(rows)


def robust_features(fs: pd.DataFrame) -> pd.DataFrame:
    p=fs[(fs.table=='PRIMARY_INHERITED_ONLY') & fs.feature.isin(NEW_FEATURES)].copy()
    rows=[]
    for feat in NEW_FEATURES:
        q=p[p.feature==feat].set_index('partition')
        ext=q.loc['external']; val=q.loc['reference_validation']; pool=q.loc['POOLED_OOS']
        counts_ok=(int(ext.true_pause_n)>=20 and int(ext.false_pause_n)>=20 and
                   int(val.true_pause_n)>=20 and int(val.false_pause_n)>=20)
        ae=float(ext.auc_true_pause_high); av=float(val.auc_true_pause_high); ap=float(pool.auc_true_pause_high)
        same_dir=((ae>.5 and av>.5) or (ae<.5 and av<.5))
        each_sep=(abs(ae-.5)>=.10 and abs(av-.5)>=.10)
        pooled_sep=abs(ap-.5)>=.15
        passed=bool(counts_ok and same_dir and each_sep and pooled_sep)
        rows.append({'feature':feat,'external_auc':ae,'validation_auc':av,'pooled_auc':ap,
                     'counts_ok':counts_ok,'same_direction':same_dir,'each_partition_sep':each_sep,
                     'pooled_sep':pooled_sep,'passes':passed})
    return pd.DataFrame(rows)


def main() -> None:
    q=load_predictions()
    d=build_features(q)
    fs=feature_summary(d)
    rf=robust_features(fs)
    passed=rf[rf.passes].copy()
    verdict='B27BK_ROBUST_BEAR_FALSE_PAUSE_DISCRIMINATOR_FOUND' if len(passed) else 'B27BK_NO_ROBUST_BEAR_FALSE_PAUSE_DISCRIMINATOR'

    d.to_csv(OUT_COHORT,index=False)
    fs.to_csv(OUT_FEAT,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    # Confusion counts by OOS partition.
    ctab=d.groupby(['partition','confusion_bucket']).size().unstack(fill_value=0)
    primary=fs[fs.table=='PRIMARY_INHERITED_ONLY']
    pool=primary[primary.partition=='POOLED_OOS'].set_index('feature')

    lines=[
        '# B27BK — BTC 24H BEAR False-Pause Anatomy Audit — Result','',
        '**Audit status: PASS.** Detector anatomy only; no refit, threshold search, decision tree, trading direction, entry, stop, target, fee, WR, PF, PnL, or live change was used.','',
        'B27BJ BEAR pooled-OOS confusion identity reproduced exactly: **79 TRUE_PAUSE + 32 FALSE_TRANSITION + 74 FALSE_PAUSE + 57 TRUE_TRANSITION = 242**.','',
        '## OOS confusion counts','',
        '| Partition | TRUE_PAUSE | FALSE_TRANSITION | FALSE_PAUSE | TRUE_TRANSITION |','|---|---:|---:|---:|---:|'
    ]
    for part in OOS:
        r=ctab.loc[part]
        lines.append(f"| {part} | {int(r.get('TRUE_PAUSE',0))} | {int(r.get('FALSE_TRANSITION',0))} | {int(r.get('FALSE_PAUSE',0))} | {int(r.get('TRUE_TRANSITION',0))} |")

    lines += ['', '## Primary ambiguity: inherited BEAR rows only','',
              'Positive class for AUC = **TRUE_PAUSE**; negative class = **FALSE_PAUSE**. Higher AUC means higher feature values are more continuation-like.','',
              '| Feature | TRUE_PAUSE median | FALSE_PAUSE median | Pooled AUC | External AUC | Validation AUC | Robust gate |',
              '|---|---:|---:|---:|---:|---:|---|']
    rfi=rf.set_index('feature')
    for feat in FEATURES:
        z=pool.loc[feat]
        if feat in rfi.index:
            rr=rfi.loc[feat]
            gate='PASS' if bool(rr.passes) else 'FAIL'
            ea=float(rr.external_auc); va=float(rr.validation_auc)
        else:
            gate='DIAGNOSTIC_ONLY'; ea=float(primary[(primary.partition=='external')&(primary.feature==feat)].iloc[0].auc_true_pause_high); va=float(primary[(primary.partition=='reference_validation')&(primary.feature==feat)].iloc[0].auc_true_pause_high)
        lines.append(f"| {feat} | {fmt(z.true_pause_median)} | {fmt(z.false_pause_median)} | {fmt(z.auc_true_pause_high)} | {fmt(ea)} | {fmt(va)} | {gate} |")

    lines += ['', '## Robust preregistered discriminators','']
    if len(passed):
        for r in passed.sort_values('pooled_auc',key=lambda s:(s-.5).abs(),ascending=False).itertuples(index=False):
            lines.append(f'- **{r.feature}**: external AUC {r.external_auc:.3f}; validation {r.validation_auc:.3f}; pooled {r.pooled_auc:.3f}.')
    else:
        lines.append('- **None.**')

    # Model-confidence diagnostic, explicitly non-promotable in this audit.
    pz=pool.loc['p_resume']
    lines += ['', '## Guardrail','',
              f"B27BJ `p_resume` itself separates the inherited buckets at pooled AUC **{float(pz.auc_true_pause_high):.3f}**, but it is diagnostic only and cannot be used here to choose a new probability threshold after seeing B27BJ.",'',
              f'**Frozen verdict: `{verdict}`.**','',
              'A passing B27BK only identifies causal anatomy for a future separately preregistered detector redesign. It does not alter B27BJ or authorize trading logic.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
