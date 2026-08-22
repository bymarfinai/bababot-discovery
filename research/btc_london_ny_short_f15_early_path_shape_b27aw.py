#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
AV = ROOT / 'BTC_LONDON_NY_SHORT_F15_FAILURE_STAGE_B27AV_Trades.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_PATH_SHAPE_B27AW_Result.md'
OUT_ATLAS = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_PATH_SHAPE_B27AW_Atlas.csv'
OUT_COUNTS = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_PATH_SHAPE_B27AW_Counts.csv'
OUT_FEATURES = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_PATH_SHAPE_B27AW_Features.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_EARLY_PATH_SHAPE_B27AW_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation')
HORIZONS = (1,2,3,4,6,8,12)
BASE_TOTAL = -15.05841591698896

FAIL_HIGH = {
    'adverse_wick_r','adverse_close_r','wrong_side_close_fraction',
    'higher_high_step_fraction','adverse_favorable_ratio',
}
H2_HIGH = {
    'favorable_wick_r','favorable_close_r','net_close_progress_r',
    'lower_low_step_fraction','close_path_efficiency',
}
FEATURES = (
    'adverse_wick_r','favorable_wick_r','adverse_close_r','favorable_close_r',
    'net_close_progress_r','wrong_side_close_fraction','lower_low_step_fraction',
    'higher_high_step_fraction','close_path_efficiency','adverse_favorable_ratio',
)
assert set(FEATURES) == FAIL_HIGH | H2_HIGH


def to_bool(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() == 'true'


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def shape(q: pd.DataFrame, entry: float, R: float) -> dict:
    assert len(q) >= 1 and R > 0
    hi = q.high.astype(float).to_numpy()
    lo = q.low.astype(float).to_numpy()
    cl = q.close.astype(float).to_numpy()
    adverse_wick = max(0.0, float(np.max(hi)) - entry) / R
    favorable_wick = max(0.0, entry - float(np.min(lo))) / R
    adverse_close = max(0.0, float(np.max(cl)) - entry) / R
    favorable_close = max(0.0, entry - float(np.min(cl))) / R
    net = (entry - float(cl[-1])) / R
    wrong = float(np.mean(cl > entry))
    if len(q) >= 2:
        ll = float(np.mean(lo[1:] < lo[:-1]))
        hh = float(np.mean(hi[1:] > hi[:-1]))
        denom = float(np.sum(np.abs(np.diff(cl))))
        eff = (float(cl[0]) - float(cl[-1])) / denom if denom > 0 else 0.0
    else:
        ll = np.nan
        hh = np.nan
        eff = 0.0
    ratio = adverse_wick / max(favorable_wick, 1e-12)
    return {
        'adverse_wick_r':adverse_wick,
        'favorable_wick_r':favorable_wick,
        'adverse_close_r':adverse_close,
        'favorable_close_r':favorable_close,
        'net_close_progress_r':net,
        'wrong_side_close_fraction':wrong,
        'lower_low_step_fraction':ll,
        'higher_high_step_fraction':hh,
        'close_path_efficiency':eff,
        'adverse_favorable_ratio':ratio,
    }


def synthetic_tests() -> None:
    idx = pd.date_range('2026-01-05 14:05', periods=4, freq='5min', tz='UTC')
    down = pd.DataFrame([
        {'open':91.5,'high':91.7,'low':91.0,'close':91.1},
        {'open':91.1,'high':91.2,'low':90.6,'close':90.7},
        {'open':90.7,'high':90.8,'low':90.2,'close':90.3},
        {'open':90.3,'high':90.4,'low':90.1,'close':90.2},
    ], index=idx)
    up = pd.DataFrame([
        {'open':91.5,'high':91.9,'low':91.3,'close':91.8},
        {'open':91.8,'high':92.2,'low':91.7,'close':92.1},
        {'open':92.1,'high':92.5,'low':92.0,'close':92.4},
        {'open':92.4,'high':92.8,'low':92.3,'close':92.7},
    ], index=idx)
    a = shape(down,91.5,10.0); b = shape(up,91.5,10.0)
    assert a['net_close_progress_r'] > 0 and b['net_close_progress_r'] < 0
    assert a['favorable_wick_r'] > b['favorable_wick_r']
    assert b['adverse_wick_r'] > a['adverse_wick_r']
    assert a['lower_low_step_fraction'] == 1.0
    assert b['higher_high_step_fraction'] == 1.0
    assert a['close_path_efficiency'] > 0 and b['close_path_efficiency'] < 0


def expected_ok(feature: str, h2_med: float, fail_med: float) -> bool:
    if pd.isna(h2_med) or pd.isna(fail_med): return False
    if feature in FAIL_HIGH: return fail_med > h2_med
    return h2_med > fail_med


def main() -> None:
    synthetic_tests()
    x5, coverage = b21.load5()
    assert len(x5) == 698112, len(x5)
    assert abs(float(coverage)-1.0) < 1e-12

    av = pd.read_csv(AV)
    for c in ('signal_ts','entry_start','h2_bar_start','exit_ts','session_end'):
        av[c] = pd.to_datetime(av[c], utc=True, errors='coerce')
    for c in ('activated','h2_before_exit'):
        av[c] = av[c].map(to_bool)
    av['net_pnl_usd'] = pd.to_numeric(av.net_pnl_usd, errors='raise')

    major = av[av.partition.isin(PARTS)].copy()
    assert len(major) == 163
    assert abs(float(major.net_pnl_usd.sum()) - BASE_TOTAL) < 1e-9
    assert int(major.activated.sum()) == 92
    assert int(major.h2_before_exit.sum()) == 115
    assert int((major.stage_bucket.astype(str) == 'PRE_H2_FAILURE').sum()) == 48
    assert int((~major.h2_before_exit).sum()) == 48
    assert (major.loc[~major.h2_before_exit,'stage_bucket'].astype(str) == 'PRE_H2_FAILURE').all()

    feature_rows=[]
    count_rows=[]
    for h in HORIZONS:
        for r in major.itertuples(index=False):
            entry_start = pd.Timestamp(r.entry_start)
            obs_start = entry_start + BAR5
            horizon_end = obs_start + h*BAR5
            exit_ts = pd.Timestamp(r.exit_ts)
            # Must still be unresolved at the end of the frozen horizon.
            if not (exit_ts > horizon_end):
                continue
            if bool(r.h2_before_exit) and pd.notna(r.h2_bar_start) and pd.Timestamp(r.h2_bar_start) < horizon_end:
                continue
            q = fast_slice(x5, obs_start, horizon_end)
            if len(q) != h or q.index[0] != obs_start or q.index[-1] != horizon_end-BAR5:
                raise AssertionError(('missing post-fill bars',r.partition,r.entry_start,h,len(q)))
            R=float(r.range); entry=float(r.entry_px)
            assert abs(entry-(float(r.L)+0.15*R)) < 1e-9*max(1.0,abs(entry))
            z=shape(q,entry,R)
            outcome='LATER_H2' if bool(r.h2_before_exit) else 'PRE_H2_FAILURE'
            feature_rows.append({
                'partition':r.partition,'signal_ts':r.signal_ts,'entry_start':entry_start,
                'horizon_bars':h,'horizon_minutes':5*h,'horizon_end':horizon_end,
                'outcome':outcome,'eventual_e20':bool(r.activated),**z,
            })
        fh = pd.DataFrame([x for x in feature_rows if x['horizon_bars']==h])
        for part in (*PARTS,'POOLED_MAJOR'):
            g=fh if part=='POOLED_MAJOR' else fh[fh.partition==part]
            count_rows.append({
                'horizon_bars':h,'horizon_minutes':5*h,'partition':part,'n':len(g),
                'later_h2_n':int((g.outcome=='LATER_H2').sum()),
                'pre_h2_failure_n':int((g.outcome=='PRE_H2_FAILURE').sum()),
                'eventual_e20_n':int(g.eventual_e20.sum()) if len(g) else 0,
            })

    fr=pd.DataFrame(feature_rows)
    counts=pd.DataFrame(count_rows)
    assert len(fr) > 0

    atlas=[]
    for h in HORIZONS:
        gh=fr[fr.horizon_bars==h]
        for feature in FEATURES:
            part_flags=[]
            for part in (*PARTS,'POOLED_MAJOR'):
                g=gh if part=='POOLED_MAJOR' else gh[gh.partition==part]
                a=pd.to_numeric(g.loc[g.outcome=='LATER_H2',feature],errors='coerce').dropna()
                b=pd.to_numeric(g.loc[g.outcome=='PRE_H2_FAILURE',feature],errors='coerce').dropna()
                hm=float(a.median()) if len(a) else np.nan
                fm=float(b.median()) if len(b) else np.nan
                ok=expected_ok(feature,hm,fm)
                if part in PARTS: part_flags.append(ok)
                atlas.append({
                    'horizon_bars':h,'horizon_minutes':5*h,'feature':feature,'partition':part,
                    'later_h2_n':len(a),'failure_n':len(b),'later_h2_median':hm,
                    'failure_median':fm,'failure_minus_h2_median_gap':fm-hm if np.isfinite(hm) and np.isfinite(fm) else np.nan,
                    'expected_direction_ok':bool(ok),
                })
            # consistency is added after the per-partition rows exist
    at=pd.DataFrame(atlas)
    consistency=[]
    for h in HORIZONS:
        for feature in FEATURES:
            g=at[(at.horizon_bars==h)&(at.feature==feature)&(at.partition.isin(PARTS))]
            consistency.append({
                'horizon_bars':h,'horizon_minutes':5*h,'feature':feature,
                'partitions_expected_direction':int(g.expected_direction_ok.sum()),
                'consistent_3of3':bool(len(g)==3 and g.expected_direction_ok.all()),
            })
    cs=pd.DataFrame(consistency)
    at=at.merge(cs,on=['horizon_bars','horizon_minutes','feature'],how='left',validate='many_to_one')

    fr.to_csv(OUT_FEATURES,index=False)
    counts.to_csv(OUT_COUNTS,index=False)
    at.to_csv(OUT_ATLAS,index=False)
    OUT_STATUS.write_text('B27AW_PASS\n')

    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        ax=abs(float(x))
        if ax >= 1000: return f'{float(x):.1f}'
        return f'{float(x):.3f}'

    md=[
        '# B27AW — BTC London->NY SHORT F15 Early Path-Shape Atlas — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Frozen B27AV identities reproduced: pooled-major N=163, H2-before-exit=115, PRE_H2_FAILURE=48, E20 activated=92, realized E20-hybrid total $-15.05841591698896.','',
        'The fill bar high/low was excluded. Every horizon uses only completed 5m bars after the fill bar and only trades still unresolved at that horizon.','',
        '## At-risk sample by horizon','',
        '| Horizon | Partition | At risk | Later H2 | PRE_H2 failure | Eventual E20 |',
        '|---:|---|---:|---:|---:|---:|'
    ]
    for r in counts.itertuples(index=False):
        md.append(f'| {int(r.horizon_minutes)}m | {r.partition} | {int(r.n)} | {int(r.later_h2_n)} | {int(r.pre_h2_failure_n)} | {int(r.eventual_e20_n)} |')

    md += ['','## Pooled-major median path shape','',
           '| Horizon | Feature | Later-H2 median | Failure median | Failure-H2 gap | Expected direction across major partitions |',
           '|---:|---|---:|---:|---:|---:|']
    pool=at[at.partition=='POOLED_MAJOR'].copy()
    for r in pool.itertuples(index=False):
        md.append(f'| {int(r.horizon_minutes)}m | {r.feature} | {num(r.later_h2_median)} | {num(r.failure_median)} | {num(r.failure_minus_h2_median_gap)} | {int(r.partitions_expected_direction)}/3 |')

    md += ['','## 3-of-3 partition-consistent expected-direction horizons','']
    for feature in FEATURES:
        g=cs[(cs.feature==feature)&cs.consistent_3of3]
        horizons=', '.join(f'{int(x)}m' for x in g.horizon_minutes.tolist()) if len(g) else 'NONE'
        md.append(f'- **{feature}:** {horizons}')

    md += ['','## Guardrail readout','',
           'No feature threshold, feature combination, classifier, stop, target, entry change, regime slice, or runner change was selected in B27AW. This atlas only localizes early causal path-shape separation.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))


if __name__=='__main__':
    main()
