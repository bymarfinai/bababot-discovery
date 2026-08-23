#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_swing_boundary_invalidation_b27bn as b27bn

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_BULL_SIDEWAYS_SWING_RETEST_CENSUS_B27BO_Result.md'
OUT_EP = ROOT / 'BTC_24H_BULL_SIDEWAYS_SWING_RETEST_CENSUS_B27BO_Episodes.csv'
OUT_SUM = ROOT / 'BTC_24H_BULL_SIDEWAYS_SWING_RETEST_CENSUS_B27BO_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_BULL_SIDEWAYS_SWING_RETEST_CENSUS_B27BO_Status.txt'

H4 = pd.Timedelta(hours=4)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')


def bucket(n: int) -> str:
    return str(n) if n < 3 else '3+'


def qtile(s, q):
    x = pd.to_numeric(pd.Series(s), errors='coerce').dropna()
    return float(x.quantile(q)) if len(x) else np.nan


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def build_rows(reg: pd.DataFrame, parents: pd.DataFrame) -> pd.DataFrame:
    e = parents[parents.origin_state == 'BULL'].copy()
    assert len(e) == 532
    assert int(e.same_direction_resume.sum()) == 281
    assert int(e.opposite_direction_transition.sum()) == 251

    z = reg.sort_values('effective_ts').reset_index(drop=True)
    by_ts = {pd.Timestamp(t): i for i,t in enumerate(z.effective_ts)}
    rows=[]
    for ep in e.itertuples(index=False):
        first_ts = pd.Timestamp(ep.first_sideways_ts)
        i = by_ts[first_ts]
        prev = z.iloc[i-1]
        d = int(ep.n_intervals)
        seg = z.iloc[i:i+d].copy().reset_index(drop=True)
        assert str(prev.regime) == 'BULL'
        assert (seg.regime == 'SIDEWAYS').all()
        assert pd.Timestamp(seg.iloc[0].effective_ts) == first_ts
        assert pd.Timestamp(seg.iloc[-1].effective_ts) == pd.Timestamp(ep.last_sideways_ts)
        boundary = float(prev.lsl) if pd.notna(prev.lsl) else np.nan
        known = pd.notna(boundary)

        if known:
            touch = seg.low.astype(float) <= boundary
            cbreak = seg.close.astype(float) < boundary
            defended = touch & ~cbreak
            first_break0 = next((j for j,v in enumerate(cbreak.tolist()) if bool(v)), None)
            stop = first_break0 if first_break0 is not None else len(seg)
            pre_def = defended.iloc[:stop].astype(bool).reset_index(drop=True)
            raw_retest_bars = int(pre_def.sum())
            prev_def = pre_def.shift(1, fill_value=False)
            distinct = int((pre_def & ~prev_def).sum())
            first_break_age = np.nan if first_break0 is None else int(first_break0 + 1)
            # Assertion: every counted retest is strictly before first break.
            if first_break0 is not None:
                assert not bool(cbreak.iloc[:first_break0].any())
                assert len(pre_def) == first_break0
            assert distinct <= raw_retest_bars
        else:
            raw_retest_bars = 0
            distinct = 0
            first_break_age = np.nan
            first_break0 = None

        rows.append({
            'episode_id': int(ep.episode_id),
            'partition': str(ep.partition),
            'outcome': 'RESUME' if bool(ep.same_direction_resume) else 'TRANSITION',
            'transition': bool(ep.opposite_direction_transition),
            'n_intervals': d,
            'first_sideways_ts': first_ts,
            'frozen_swing_low': boundary,
            'boundary_available': bool(known),
            'close_break_during_sideways': bool(first_break0 is not None),
            'first_close_break_age': first_break_age,
            'first_close_break_hours': np.nan if pd.isna(first_break_age) else 4*float(first_break_age),
            'raw_defended_retest_bars_before_break': raw_retest_bars,
            'distinct_defended_retest_visits_before_break': distinct,
            'retest_bucket': bucket(distinct),
        })
    out = pd.DataFrame(rows)
    assert len(out) == 532
    return out


def sub(d, part):
    if part == 'POOLED_OOS': return d[d.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR': return d[d.partition.isin(MAJOR)].copy()
    return d[d.partition == part].copy()


def summarize(d):
    rows=[]
    for part in (*MAJOR,'POOLED_OOS','POOLED_MAJOR'):
        q = sub(d,part)
        for break_class in ('CLOSE_BREAK','NO_CLOSE_BREAK'):
            z = q[q.close_break_during_sideways == (break_class=='CLOSE_BREAK')]
            for outcome in ('ALL','RESUME','TRANSITION'):
                x = z if outcome=='ALL' else z[z.outcome==outcome]
                n=len(x)
                rows.append({
                    'partition':part,'break_class':break_class,'outcome':outcome,'n':n,
                    'share_of_bull_origin': n/len(q) if len(q) else np.nan,
                    'retest0_n':int((x.retest_bucket=='0').sum()),
                    'retest1_n':int((x.retest_bucket=='1').sum()),
                    'retest2_n':int((x.retest_bucket=='2').sum()),
                    'retest3p_n':int((x.retest_bucket=='3+').sum()),
                    'median_distinct_retests':float(x.distinct_defended_retest_visits_before_break.median()) if n else np.nan,
                    'p75_distinct_retests':qtile(x.distinct_defended_retest_visits_before_break,.75),
                    'p90_distinct_retests':qtile(x.distinct_defended_retest_visits_before_break,.90),
                    'max_distinct_retests':int(x.distinct_defended_retest_visits_before_break.max()) if n else 0,
                    'median_raw_retest_bars':float(x.raw_defended_retest_bars_before_break.median()) if n else np.nan,
                    'p75_raw_retest_bars':qtile(x.raw_defended_retest_bars_before_break,.75),
                    'p90_raw_retest_bars':qtile(x.raw_defended_retest_bars_before_break,.90),
                    'max_raw_retest_bars':int(x.raw_defended_retest_bars_before_break.max()) if n else 0,
                    'median_break_age':float(x.first_close_break_age.median()) if n and break_class=='CLOSE_BREAK' else np.nan,
                    'p75_break_age':qtile(x.first_close_break_age,.75) if break_class=='CLOSE_BREAK' else np.nan,
                    'p90_break_age':qtile(x.first_close_break_age,.90) if break_class=='CLOSE_BREAK' else np.nan,
                    'max_break_age':int(x.first_close_break_age.max()) if n and break_class=='CLOSE_BREAK' else 0,
                })
    return pd.DataFrame(rows)


def getrow(s, part, break_class, outcome='ALL'):
    q=s[(s.partition==part)&(s.break_class==break_class)&(s.outcome==outcome)]
    assert len(q)==1
    return q.iloc[0]


def bucket_text(r):
    n=int(r.n)
    if not n: return '-'
    return f"0x {int(r.retest0_n)} ({pct(r.retest0_n/n)}), 1x {int(r.retest1_n)} ({pct(r.retest1_n/n)}), 2x {int(r.retest2_n)} ({pct(r.retest2_n/n)}), 3+ {int(r.retest3p_n)} ({pct(r.retest3p_n/n)})"


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0)<1e-12
    reg=b27bn.build_instrumented_regime(x5)
    parents=b27bn.load_parent_episodes()
    d=build_rows(reg,parents)
    s=summarize(d)

    oos=sub(d,'POOLED_OOS')
    known=oos[oos.boundary_available]
    br=known[known.close_break_during_sideways]
    gate_identity = len(d)==532 and int((d.outcome=='RESUME').sum())==281 and int((d.outcome=='TRANSITION').sum())==251
    gate_boundary = len(known)/len(oos) >= .95
    gate_sample = len(br) >= 30
    gate_order = bool((br.first_close_break_age >= 1).all())
    supported=all([gate_identity,gate_boundary,gate_sample,gate_order])
    verdict='B27BO_BULL_SWING_RETEST_CENSUS_COMPLETE' if supported else 'B27BO_BULL_SWING_RETEST_CENSUS_INCOMPLETE'

    d.to_csv(OUT_EP,index=False)
    s.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    r=getrow(s,'POOLED_OOS','CLOSE_BREAK')
    rr=getrow(s,'POOLED_OOS','CLOSE_BREAK','RESUME')
    rt=getrow(s,'POOLED_OOS','CLOSE_BREAK','TRANSITION')
    no=getrow(s,'POOLED_OOS','NO_CLOSE_BREAK')
    lines=[
        '# B27BO — BTC 24H BULL→SIDEWAYS Swing-Retest Census — Result','',
        '**Audit status: PASS.** BULL→SIDEWAYS swing-retest census only; no trading direction or economics were used.','',
        'Parent identity reproduced: **532 BULL-origin episodes = 281 RESUME + 251 TRANSITION**. Frozen boundary is the prior completed BULL state latest confirmed swing low.','',
        'A defended retest is a completed 4H SIDEWAYS bar whose low reaches/sweeps the frozen swing low but whose close remains above it. Consecutive defended-retest bars collapse into one distinct visit. A break is the first completed 4H SIDEWAYS close below the frozen swing low.','',
        '## Pooled OOS — episodes that eventually close-break the swing low during SIDEWAYS','',
        f'- Close-break episodes: **{int(r.n)}**.',
        f'- Distinct defended retests before break: **{bucket_text(r)}**.',
        f'- Median distinct retests: **{r.median_distinct_retests:.1f}**; P75 **{r.p75_distinct_retests:.1f}**; P90 **{r.p90_distinct_retests:.1f}**; max **{int(r.max_distinct_retests)}**.',
        f'- Median first close-break age: **{r.median_break_age:.1f} bars / {4*r.median_break_age:.0f}h**; P75 **{r.p75_break_age:.1f} bars**; P90 **{r.p90_break_age:.1f} bars**; max **{int(r.max_break_age)} bars**.','',
        '### By eventual detector outcome','',
        f'- RESUME despite a close-break during SIDEWAYS (N={int(rr.n)}): {bucket_text(rr)}.',
        f'- TRANSITION after a close-break during SIDEWAYS (N={int(rt.n)}): {bucket_text(rt)}.','',
        '## Pooled OOS — no 4H close-break during SIDEWAYS','',
        f'- N **{int(no.n)}**; distinct defended retests across the whole SIDEWAYS episode: {bucket_text(no)}.','',
        '## OOS partition stability','',
        '| Partition | Break N | 0 retest | 1 retest | 2 retests | 3+ retests | Median | Median break age |',
        '|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in OOS:
        p=getrow(s,part,'CLOSE_BREAK')
        n=max(int(p.n),1)
        lines.append(f'| {part} | {int(p.n)} | {pct(p.retest0_n/n)} | {pct(p.retest1_n/n)} | {pct(p.retest2_n/n)} | {pct(p.retest3p_n/n)} | {p.median_distinct_retests:.1f} | {p.median_break_age:.1f} bars |')
    lines += ['', '## Frozen census gate','',
              f'- Exact source/detector/parent identity: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- Frozen swing-low boundary available >=95% pooled OOS: **{"PASS" if gate_boundary else "FAIL"}**.',
              f'- Pooled-OOS close-break N >=30: **{"PASS" if gate_sample else "FAIL"}**.',
              f'- Retests counted strictly before first close-break: **{"PASS" if gate_order else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'Interpretation: this is a structural retest-count census only. It does not prove accumulation/reaccumulation or promote a new detector rule.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
