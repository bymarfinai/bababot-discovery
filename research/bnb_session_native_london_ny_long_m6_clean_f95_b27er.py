from __future__ import annotations

from pathlib import Path
import math
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m3_entry_b27eo as b27eo

TARGET='BNBUSDT'
BAR5=pd.Timedelta(minutes=5)
DEV='development'
EXT='external'
PFX='BNB_SESSION_NATIVE_LONDON_NY_LONG_M6_CLEAN_F95_B27ER'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'


def pct(x):
    return '-' if pd.isna(x) else f'{100.0*float(x):.1f}%'


def wilson(k,n,z=1.959963984540054):
    if n<=0:
        return (np.nan,np.nan)
    p=k/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return max(0.0,center-half), min(1.0,center+half)


def feature_row(s, exe, z, part):
    entry_ts=pd.Timestamp(z['entry_ts'])
    signal_start=entry_ts-BAR5
    if signal_start not in exe.index:
        raise AssertionError(f'missing signal bar {s.local_date}')
    bar=exe.loc[signal_start]
    H=float(s.H); L=float(s.L); R=float(s.R)
    leave_ts=pd.Timestamp(s.leave_ts)
    window=exe[(exe.index>=leave_ts)&(exe.index<=signal_start)]
    if window.empty:
        raise AssertionError(f'empty causal window {s.local_date}')
    signal_low_depth=(H-float(bar.low))/R
    pre_entry_max_depth=max(0.0,(H-float(window.low.min()))/R)
    return {
        'local_date':str(s.local_date),
        'partition':part,
        'duration_regime':str(s.duration_regime),
        'upstream_terminal':str(s.terminal),
        'outcome':str(z['outcome']),
        'h2':str(z['outcome'])=='H2_ARRIVAL',
        'H':H,'L':L,'R':R,
        'leave_ts':leave_ts,'signal_start':signal_start,'entry_ts':entry_ts,
        'entry_px':float(z['entry_px']),
        'entry_depth_R':float(z['entry_depth_R']),
        'minutes_leave_to_entry':float(z['minutes_leave_to_entry']),
        'minutes_entry_to_h2':float(z['minutes_entry_to_h2']) if not pd.isna(z['minutes_entry_to_h2']) else np.nan,
        'post_entry_mae_R':float(z['post_entry_mae_R']),
        'signal_low_depth_R':signal_low_depth,
        'pre_entry_max_depth_R':pre_entry_max_depth,
    }


def build_partition(x5, sessions, part):
    q=sessions[(sessions.partition==part)&sessions.leave.fillna(False).astype(bool)].copy()
    rows=[]
    for _,s in q.iterrows():
        ny_open=pd.Timestamp(s.ny_open_utc); ny_close=pd.Timestamp(s.ny_close_utc)
        exe=b27em.fs(x5,ny_open,ny_close)
        H=float(s.H); L=float(s.L); R=float(s.R); leave_ts=pd.Timestamp(s.leave_ts)
        z=b27eo.discover_candidate('E2_F95_RECLAIM',exe,leave_ts,H,L,R)
        if not bool(z.get('eligible',False)):
            continue
        rows.append(feature_row(s,exe,z,part))
    return pd.DataFrame(rows)


def summarize(label,d,upstream_h2):
    n=len(d); h=int(d.h2.sum()) if n else 0; non=n-h
    rate=h/n if n else np.nan
    lo,hi=wilson(h,n)
    wh=d[d.h2] if n else d
    return {
        'cohort':label,
        'eligible':n,
        'h2':h,
        'non_h2':non,
        'h2_rate':rate,
        'wilson_lo':lo,
        'wilson_hi':hi,
        'winner_capture':h/upstream_h2 if upstream_h2 else np.nan,
        'median_leave_entry_min':pd.to_numeric(d.minutes_leave_to_entry,errors='coerce').median() if n else np.nan,
        'median_entry_h2_min':pd.to_numeric(wh.minutes_entry_to_h2,errors='coerce').median() if h else np.nan,
        'median_entry_depth_R':pd.to_numeric(d.entry_depth_R,errors='coerce').median() if n else np.nan,
        'median_mae_R':pd.to_numeric(d.post_entry_mae_R,errors='coerce').median() if n else np.nan,
        'p75_mae_R':pd.to_numeric(d.post_entry_mae_R,errors='coerce').quantile(.75) if n else np.nan,
    }


def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27ER preregistration missing')

    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995:
        raise AssertionError(f'coverage gate failed {cov}')

    sessions=b27em.session_rows(x5)
    ext_up=sessions[(sessions.partition==EXT)&sessions.leave.fillna(False).astype(bool)].copy()
    if len(ext_up)!=63 or int((ext_up.terminal=='H2_ARRIVAL').sum())!=45 or int((ext_up.terminal!='H2_ARRIVAL').sum())!=18:
        raise AssertionError(f'external upstream integrity n={len(ext_up)} h2={int((ext_up.terminal=="H2_ARRIVAL").sum())}')

    dev=build_partition(x5,sessions,DEV)
    if len(dev)!=21 or int(dev.h2.sum())!=20 or int((~dev.h2).sum())!=1:
        raise AssertionError(f'development F95 integrity n={len(dev)} h2={int(dev.h2.sum())}')

    devw=dev[dev.h2].copy()
    path_p75=float(devw.pre_entry_max_depth_R.quantile(.75))
    reclaim_low_p75=float(devw.signal_low_depth_R.quantile(.75))

    ext=build_partition(x5,sessions,EXT)
    if ext.empty:
        raise AssertionError('no external raw F95 entries')
    ext['clean_f95']=(ext.pre_entry_max_depth_R<=path_p75)&(ext.signal_low_depth_R<=reclaim_low_p75)
    clean=ext[ext.clean_f95].copy()

    raw_s=summarize('RAW_F95_EXTERNAL',ext,45)
    clean_s=summarize('CLEAN_F95_EXTERNAL',clean,45)
    sm=pd.DataFrame([raw_s,clean_s])
    sm.to_csv(OUT_SUM,index=False)
    ext.to_csv(OUT_DETAIL,index=False)

    raw_n=int(raw_s['eligible']); clean_n=int(clean_s['eligible'])
    retention=clean_n/raw_n if raw_n else np.nan
    delta_pp=(clean_s['h2_rate']-raw_s['h2_rate'])*100.0 if raw_n and clean_n else np.nan

    supported=(clean_n>=8 and delta_pp>=5.0 and retention>=0.50)
    strong=(supported and clean_s['h2_rate']>=0.90)
    if clean_n<8:
        verdict='INCONCLUSIVE_LOW_N'
    elif strong:
        verdict='STRONG_SUPPORT'
    elif supported:
        verdict='SUPPORTED'
    else:
        verdict='NOT_SUPPORTED'

    lines=[
        '# BNB Session-Native LONG M6 Clean F95 External Holdout — B27ER Result','',
        f'Raw BNB 5m coverage: **{cov:.4%}**.','',
        'Thresholds were derived mechanically from **development H2 F95 entries only** before evaluating external.','',
        '## Frozen thresholds','',
        f'- Development H2 F95 entries used for thresholds: **{len(devw)}**',
        f'- `PATH_P75` (pre-entry max depth): **{path_p75:.4f}R**',
        f'- `RECLAIM_LOW_P75` (reclaim-candle low depth): **{reclaim_low_p75:.4f}R**',
        '- CLEAN_F95 requires **both** dimensions <= their development-winner P75 thresholds.','',
        '## External upstream integrity','',
        '- Causal leaves: **63 / 63**',
        '- Upstream H2: **45 / 45**',
        '- Upstream non-H2: **18 / 18**','',
        '## External holdout comparison','',
        '| Cohort | Eligible | H2 | H2 rate | Wilson 95% | Winner capture | Med leave→entry | Med entry→H2 | Med entry depth | Med MAE | P75 MAE |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for r in [raw_s,clean_s]:
        lines.append(f"| {r['cohort']} | {int(r['eligible'])} | {int(r['h2'])} | {pct(r['h2_rate'])} | {pct(r['wilson_lo'])} – {pct(r['wilson_hi'])} | {pct(r['winner_capture'])} | {r['median_leave_entry_min']:.1f}m | {r['median_entry_h2_min']:.1f}m | {r['median_entry_depth_R']:.4f}R | {r['median_mae_R']:.4f}R | {r['p75_mae_R']:.4f}R |")
    lines += ['', '## Preregistered support contract','',
              f'- Clean retention: **{pct(retention)}** ({clean_n}/{raw_n})',
              f'- Delta H2 rate: **{delta_pp:+.1f} percentage points**',
              '- Required: clean N >= 8; delta >= +5pp; retention >= 50%.',
              '- Strong support additionally requires clean H2-after-entry >= 90%.','',
              f'**Verdict: {verdict}**','',
              'H2-after-entry remains a **structural outcome rate, not trading win rate**.','',
              f'**Status: B27ER_BNB_CLEAN_F95_EXTERNAL_{verdict}**','',
              'STOP: no alternate percentile, time/body/wick tuning, F90/F85, economics, August, SHORT, or live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(f'B27ER_BNB_CLEAN_F95_EXTERNAL_{verdict}\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
