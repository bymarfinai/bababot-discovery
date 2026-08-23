#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_regime_detector_audit_b27bg as b27bg
import btc_24h_sideways_transition_anatomy_b27bh as b27bh
import btc_london_ny_4h_regime_alignment_b27ag as b27ag

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_Result.md'
OUT_EP = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_Episodes.csv'
OUT_SCORE = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_ScoreSummary.csv'
OUT_CLAUSE = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_ClauseSummary.csv'
OUT_FEAT = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_FeatureSummary.csv'
OUT_MASK = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_Masks.csv'
OUT_STATUS = ROOT / 'BTC_24H_SIDEWAYS_CONTINUATION_TRANSITION_FEATURES_B27BI_Status.txt'

H4 = pd.Timedelta(hours=4)
MAJOR = ('external','development','reference_validation')
ORIGINS = ('BULL','BEAR')
CLAUSES = ('structure_high_ok','structure_low_ok','ema_order_ok','close_side_ok')
FEATURES = (
    'directional_evidence_score',
    'aligned_structure_strength',
    'opposite_structure_strength',
    'dir_ema_spread_atr',
    'dir_close_ema20_atr',
    'dir_ema7_slope_atr',
    'dir_ema20_slope_atr',
    'dir_body_atr',
    'bar_range_atr',
    'prior_directional_age',
)


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def fmt_num(v, d=3):
    return '-' if pd.isna(v) else f'{float(v):.{d}f}'


def qtile(s, q):
    x = pd.to_numeric(pd.Series(s), errors='coerce').dropna()
    return float(x.quantile(q)) if len(x) else np.nan


def rank_auc(values: pd.Series, positive: pd.Series) -> float:
    x = pd.to_numeric(values, errors='coerce')
    y = positive.astype(bool)
    ok = x.notna() & y.notna()
    x = x[ok]
    y = y[ok]
    n1 = int(y.sum())
    n0 = int((~y).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = x.rank(method='average')
    s1 = float(ranks[y].sum())
    return (s1 - n1*(n1+1)/2.0) / (n1*n0)


def build_extended_regime(x5: pd.DataFrame) -> pd.DataFrame:
    z = x5[['open','high','low','close']].copy()
    agg = z.resample('4h', origin='epoch', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last')
    )
    cnt = z.close.resample('4h', origin='epoch', label='left', closed='left').count()
    agg['n5'] = cnt
    agg = agg[(agg.n5 == 48) & agg.open.notna() & agg.close.notna()].copy()
    assert len(agg) >= 1000

    H = agg.high.to_numpy(float)
    L = agg.low.to_numpy(float)
    C = agg.close.to_numpy(float)
    ef = b27ag.ema(C, 7)
    es = b27ag.ema(C, 20)
    at = b27ag.atr(H, L, C, 14)
    det = b27ag.SwingRegime(5, 0.5)

    states=[]; hhs=[]; hls=[]; lhs=[]; lls=[]
    for i in range(len(agg)):
        st = det.process(i, H, L, C, ef, es, at)
        states.append(st)
        hhs.append(int(det.hh)); hls.append(int(det.hl)); lhs.append(int(det.lh)); lls.append(int(det.ll))

    agg['ema7']=ef; agg['ema20']=es; agg['atr14']=at
    agg['hh']=hhs; agg['hl']=hls; agg['lh']=lhs; agg['ll']=lls
    agg['regime']=states
    agg['available_ts']=agg.index + H4
    agg['source_bar_start']=agg.index
    agg['effective_ts']=pd.to_datetime(agg.available_ts, utc=True)

    # Counter recording must not change regime semantics.
    base = b27ag.build_regime(x5)
    assert agg.index.equals(base.index)
    assert agg.regime.equals(base.regime)
    assert np.allclose(agg.ema7.to_numpy(float), base.ema7.to_numpy(float), rtol=0, atol=0)
    assert np.allclose(agg.ema20.to_numpy(float), base.ema20.to_numpy(float), rtol=0, atol=0)
    assert np.allclose(agg.atr14.to_numpy(float), base.atr14.to_numpy(float), rtol=0, atol=0)

    gap = agg.effective_ts.diff()
    new_ep = agg.regime.ne(agg.regime.shift(1)) | gap.ne(H4)
    agg['episode_id'] = new_ep.cumsum().astype(int)
    agg['state_age_intervals'] = agg.groupby('episode_id').cumcount() + 1
    agg['partition'] = agg.effective_ts.map(b27bg.assign_partition)
    return agg.reset_index(drop=True)


def build_episode_features(reg: pd.DataFrame) -> pd.DataFrame:
    ep = b27bh.episode_anatomy(reg)
    b = ep[ep.partition.isin(MAJOR) & ep.bracketed_directional].copy()

    # Exact B27BH identity first.
    assert len(b) == 1023, len(b)
    assert int(b.same_direction_resume.sum()) == 527
    assert int(b.opposite_direction_transition.sum()) == 496
    assert int((b.origin_state=='BULL').sum()) == 532
    assert int((b.origin_state=='BEAR').sum()) == 491

    z = reg.sort_values('effective_ts').reset_index(drop=True).copy()
    by_ts = {pd.Timestamp(t): i for i,t in enumerate(z.effective_ts)}
    rows=[]
    for e in b.itertuples(index=False):
        ts = pd.Timestamp(e.first_sideways_ts)
        i = by_ts[ts]
        r = z.iloc[i]
        assert str(r.regime) == 'SIDEWAYS'
        assert pd.Timestamp(r.effective_ts) == ts
        assert i > 0
        prev = z.iloc[i-1]
        assert pd.Timestamp(r.effective_ts) - pd.Timestamp(prev.effective_ts) == H4
        assert str(prev.regime) == str(e.origin_state)
        assert pd.Timestamp(r.available_ts) == ts

        origin = str(e.origin_state)
        sgn = 1.0 if origin == 'BULL' else -1.0
        if origin == 'BULL':
            sh = int(r.hh) >= 2
            sl = int(r.hl) >= 2
            eo = float(r.ema7) > float(r.ema20)
            cs = float(r.close) > float(r.ema20)
            aligned = min(int(r.hh), int(r.hl))
            opposite = min(int(r.lh), int(r.ll))
        else:
            sh = int(r.lh) >= 2
            sl = int(r.ll) >= 2
            eo = float(r.ema7) < float(r.ema20)
            cs = float(r.close) < float(r.ema20)
            aligned = min(int(r.lh), int(r.ll))
            opposite = min(int(r.hh), int(r.hl))

        score = int(sh) + int(sl) + int(eo) + int(cs)
        assert 0 <= score <= 3, (origin, score, ts)
        mask = ''.join([
            'H' if not sh else '-',
            'L' if not sl else '-',
            'E' if not eo else '-',
            'C' if not cs else '-',
        ])
        atr = float(r.atr14)
        assert atr > 0
        prev_i = i-1
        rows.append({
            'episode_id': int(e.episode_id),
            'partition': str(e.partition),
            'origin_state': origin,
            'exit_state': str(e.exit_state),
            'outcome': 'RESUME' if bool(e.same_direction_resume) else 'TRANSITION',
            'resume': bool(e.same_direction_resume),
            'first_sideways_ts': ts,
            'source_bar_start': pd.Timestamp(r.source_bar_start),
            'feature_available_ts': pd.Timestamp(r.available_ts),
            'structure_high_ok': bool(sh),
            'structure_low_ok': bool(sl),
            'ema_order_ok': bool(eo),
            'close_side_ok': bool(cs),
            'directional_evidence_score': score,
            'failed_clause_mask': mask,
            'aligned_structure_strength': aligned,
            'opposite_structure_strength': opposite,
            'hh': int(r.hh), 'hl': int(r.hl), 'lh': int(r.lh), 'll': int(r.ll),
            'ema7': float(r.ema7), 'ema20': float(r.ema20), 'atr14': atr,
            'dir_ema_spread_atr': sgn*(float(r.ema7)-float(r.ema20))/atr,
            'dir_close_ema20_atr': sgn*(float(r.close)-float(r.ema20))/atr,
            'dir_ema7_slope_atr': sgn*(float(r.ema7)-float(z.iloc[prev_i].ema7))/atr,
            'dir_ema20_slope_atr': sgn*(float(r.ema20)-float(z.iloc[prev_i].ema20))/atr,
            'dir_body_atr': sgn*(float(r.close)-float(r.open))/atr,
            'bar_range_atr': (float(r.high)-float(r.low))/atr,
            'prior_directional_age': int(prev.state_age_intervals),
        })
    out = pd.DataFrame(rows)
    assert len(out)==1023
    assert (out.feature_available_ts == out.first_sideways_ts).all()
    return out


def subset(d, part, origin):
    q=d[d.origin_state==origin]
    if part=='POOLED_MAJOR':
        return q[q.partition.isin(MAJOR)].copy()
    return q[q.partition==part].copy()


def score_summary(d):
    rows=[]
    for part in (*MAJOR,'POOLED_MAJOR'):
        for origin in ORIGINS:
            q=subset(d,part,origin)
            for outcome in ('RESUME','TRANSITION'):
                x=q[q.outcome==outcome].directional_evidence_score
                rows.append({
                    'partition':part,'origin':origin,'outcome':outcome,'n':len(x),
                    'mean_score':float(x.mean()) if len(x) else np.nan,
                    'median_score':float(x.median()) if len(x) else np.nan,
                    'p25_score':qtile(x,.25),'p75_score':qtile(x,.75),
                })
            for score in range(4):
                x=q[q.directional_evidence_score==score]
                rows.append({
                    'partition':part,'origin':origin,'outcome':f'SCORE_{score}','n':len(x),
                    'resume_rate':float(x.resume.mean()) if len(x) else np.nan,
                })
    return pd.DataFrame(rows)


def clause_summary(d):
    rows=[]
    for part in (*MAJOR,'POOLED_MAJOR'):
        for origin in ORIGINS:
            q=subset(d,part,origin)
            for clause in CLAUSES:
                for retained in (True,False):
                    x=q[q[clause]==retained]
                    rows.append({
                        'partition':part,'origin':origin,'clause':clause,'retained':retained,
                        'n':len(x),'resume_n':int(x.resume.sum()) if len(x) else 0,
                        'resume_rate':float(x.resume.mean()) if len(x) else np.nan,
                    })
    return pd.DataFrame(rows)


def feature_summary(d):
    rows=[]
    for part in (*MAJOR,'POOLED_MAJOR'):
        for origin in ORIGINS:
            q=subset(d,part,origin)
            for feat in FEATURES:
                a=pd.to_numeric(q[q.resume][feat],errors='coerce').dropna()
                b=pd.to_numeric(q[~q.resume][feat],errors='coerce').dropna()
                rows.append({
                    'partition':part,'origin':origin,'feature':feat,
                    'resume_n':len(a),'transition_n':len(b),
                    'resume_median':float(a.median()) if len(a) else np.nan,
                    'transition_median':float(b.median()) if len(b) else np.nan,
                    'median_diff':float(a.median()-b.median()) if len(a) and len(b) else np.nan,
                    'resume_mean':float(a.mean()) if len(a) else np.nan,
                    'transition_mean':float(b.mean()) if len(b) else np.nan,
                    'mean_diff':float(a.mean()-b.mean()) if len(a) and len(b) else np.nan,
                    'auc_resume_high':rank_auc(q[feat],q.resume),
                })
    return pd.DataFrame(rows)


def mask_summary(d):
    rows=[]
    for part in (*MAJOR,'POOLED_MAJOR'):
        for origin in ORIGINS:
            q=subset(d,part,origin)
            for mask,x in q.groupby('failed_clause_mask',sort=True):
                rows.append({'partition':part,'origin':origin,'mask':mask,'n':len(x),
                             'resume_n':int(x.resume.sum()),'resume_rate':float(x.resume.mean())})
    return pd.DataFrame(rows)


def clause_consistency(cs, origin, clause):
    diffs=[]
    for part in MAJOR:
        q=cs[(cs.partition==part)&(cs.origin==origin)&(cs.clause==clause)].set_index('retained')
        if True not in q.index or False not in q.index:
            return False, np.nan
        rt=q.loc[True]; rf=q.loc[False]
        if int(rt.n)==0 or int(rf.n)==0 or pd.isna(rt.resume_rate) or pd.isna(rf.resume_rate):
            return False, np.nan
        diffs.append(float(rt.resume_rate-rf.resume_rate))
    signs=np.sign(np.array(diffs,float))
    consistent=bool(np.all(signs>0) or np.all(signs<0))
    return consistent, float(np.mean(diffs))


def primary_readout(d, ss, cs):
    detail={}
    origin_pass=[]
    for origin in ORIGINS:
        pooled=ss[(ss.partition=='POOLED_MAJOR')&(ss.origin==origin)&(ss.outcome.isin(['RESUME','TRANSITION']))].set_index('outcome')
        med_ok=float(pooled.loc['RESUME','median_score']) > float(pooled.loc['TRANSITION','median_score'])
        part_diffs=[]
        for part in MAJOR:
            q=ss[(ss.partition==part)&(ss.origin==origin)&(ss.outcome.isin(['RESUME','TRANSITION']))].set_index('outcome')
            part_diffs.append(float(q.loc['RESUME','mean_score']-q.loc['TRANSITION','mean_score']))
        means_ok=all(v>0 for v in part_diffs)
        consistent=[]
        for clause in CLAUSES:
            ok,avg=clause_consistency(cs,origin,clause)
            if ok: consistent.append((clause,avg))
        clause_ok=len(consistent)>0
        passed=bool(med_ok and means_ok and clause_ok)
        origin_pass.append(passed)
        detail[origin]={'median_ok':med_ok,'part_diffs':part_diffs,'consistent_clauses':consistent,'pass':passed}
    verdict='B27BI_DIRECTIONAL_EVIDENCE_SUPPORTS_CONTINUATION_PAUSE' if all(origin_pass) else 'B27BI_FIRST_SIDEWAYS_FEATURES_INSUFFICIENT_OR_UNSTABLE'
    return verdict,detail


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0)<1e-12

    reg=build_extended_regime(x5)
    assert (reg.n5==48).all()
    d=build_episode_features(reg)
    ss=score_summary(d)
    cs=clause_summary(d)
    fs=feature_summary(d)
    ms=mask_summary(d)
    verdict,detail=primary_readout(d,ss,cs)

    d.to_csv(OUT_EP,index=False)
    ss.to_csv(OUT_SCORE,index=False)
    cs.to_csv(OUT_CLAUSE,index=False)
    fs.to_csv(OUT_FEAT,index=False)
    ms.to_csv(OUT_MASK,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BI — BTC 24H SIDEWAYS Continuation-vs-Transition Feature Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** First-SIDEWAYS-bar causal detector anatomy only; no trade direction, entry, stop, target, fee, WR, PF, or PnL was used.','',
        'B27BH episode identity reproduced exactly: **1,023 bracketed episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532, BEAR-origin 491.**','',
        '## Frozen primary evidence score','',
        '| Origin | Outcome | N | Mean score | Median | P25 | P75 |','|---|---|---:|---:|---:|---:|---:|'
    ]
    for origin in ORIGINS:
        q=ss[(ss.partition=='POOLED_MAJOR')&(ss.origin==origin)&(ss.outcome.isin(['RESUME','TRANSITION']))]
        for outcome in ('RESUME','TRANSITION'):
            z=q[q.outcome==outcome].iloc[0]
            lines.append(f'| {origin} | {outcome} | {int(z.n)} | {z.mean_score:.3f} | {z.median_score:.1f} | {z.p25_score:.1f} | {z.p75_score:.1f} |')

    lines += ['', '## RESUME rate by evidence score — pooled major','',
              '| Origin | Score 0 | Score 1 | Score 2 | Score 3 |','|---|---:|---:|---:|---:|']
    for origin in ORIGINS:
        q=ss[(ss.partition=='POOLED_MAJOR')&(ss.origin==origin)&ss.outcome.str.startswith('SCORE_')].set_index('outcome')
        vals=[]
        for score in range(4):
            z=q.loc[f'SCORE_{score}']
            vals.append(f'{fmt_pct(z.resume_rate)} (N={int(z.n)})')
        lines.append(f'| {origin} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |')

    lines += ['', '## Individual origin-clause retention — pooled major','',
              '| Origin | Clause | Retained N / resume | Failed N / resume | Difference |','|---|---|---:|---:|---:|']
    for origin in ORIGINS:
        for clause in CLAUSES:
            q=cs[(cs.partition=='POOLED_MAJOR')&(cs.origin==origin)&(cs.clause==clause)].set_index('retained')
            rt=q.loc[True]; rf=q.loc[False]
            diff=float(rt.resume_rate-rf.resume_rate) if not pd.isna(rt.resume_rate) and not pd.isna(rf.resume_rate) else np.nan
            lines.append(f'| {origin} | {clause} | {int(rt.n)} / {fmt_pct(rt.resume_rate)} | {int(rf.n)} / {fmt_pct(rf.resume_rate)} | {fmt_pct(diff)} |')

    lines += ['', '## Continuous first-bar features — pooled major','',
              '| Origin | Feature | RESUME median | TRANSITION median | Diff | AUC (higher=RESUME) |','|---|---|---:|---:|---:|---:|']
    for origin in ORIGINS:
        q=fs[(fs.partition=='POOLED_MAJOR')&(fs.origin==origin)]
        for feat in FEATURES:
            z=q[q.feature==feat].iloc[0]
            lines.append(f'| {origin} | {feat} | {fmt_num(z.resume_median)} | {fmt_num(z.transition_median)} | {fmt_num(z.median_diff)} | {fmt_num(z.auc_resume_high)} |')

    lines += ['', '## Primary preregistered readout','']
    for origin in ORIGINS:
        x=detail[origin]
        diffs=', '.join(f'{p}:{v:+.3f}' for p,v in zip(MAJOR,x['part_diffs']))
        cc=', '.join(f'{c} ({avg:+.1%} avg retained-minus-failed resume rate)' for c,avg in x['consistent_clauses']) or 'none'
        lines.append(f'- **{origin}:** pooled median-score criterion={"PASS" if x["median_ok"] else "FAIL"}; mean-score differences [{diffs}]; consistent clause(s): {cc}; origin result={"PASS" if x["pass"] else "FAIL"}.')
    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              '## Interpretation boundary','',
              'B27BI may identify causal characteristics of continuation-like pauses versus genuine transitions, but it does not alter the detector. Any inherited-state, hysteresis, confirmation, or new pause/transition state requires a separate preregistered redesign audit.','',
              'The terms continuation-like pause and transition describe state-machine outcomes only; no participant accumulation/distribution mechanism is inferred.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':
    main()
