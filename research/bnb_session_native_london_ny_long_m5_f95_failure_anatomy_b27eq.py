from __future__ import annotations

from pathlib import Path
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
PARTS=['development','reference_validation']
EXPECTED={'development':(21,20,1),'reference_validation':(7,6,1)}
PFX='BNB_SESSION_NATIVE_LONDON_NY_LONG_M5_F95_FAILURE_ANATOMY_B27EQ'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'
OUT_SUM=ROOT/f'{PFX}_Winner_Distribution.csv'
OUT_FLAGS=ROOT/f'{PFX}_Failure_Flags.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'
FEATURES=[
 'minutes_leave_to_signal','minutes_leave_to_entry','signal_open_depth_R','signal_low_depth_R','signal_close_depth_R',
 'signal_range_R','signal_body_R','signal_body_ratio','signal_close_position','reclaim_overshoot_R','wick_below_F95_R',
 'pre_entry_max_depth_R','pre_entry_min_close_depth_R','pre_entry_max_close_depth_R','pre_entry_bar_count','entry_depth_R'
]

def f(v): return '-' if pd.isna(v) else f'{float(v):.4f}'
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def build(x5):
    sessions=b27em.session_rows(x5)
    rows=[]
    for part in PARTS:
        q=sessions[(sessions.partition==part)&sessions.leave.fillna(False).astype(bool)].copy()
        for _,s in q.iterrows():
            ny_open=pd.Timestamp(s.ny_open_utc); ny_close=pd.Timestamp(s.ny_close_utc)
            exe=b27em.fs(x5,ny_open,ny_close)
            H=float(s.H); L=float(s.L); R=float(s.R); leave_ts=pd.Timestamp(s.leave_ts)
            z=b27eo.discover_candidate('E2_F95_RECLAIM',exe,leave_ts,H,L,R)
            if not bool(z.get('eligible',False)):
                continue
            entry_ts=pd.Timestamp(z['entry_ts'])
            signal_start=entry_ts-BAR5
            if signal_start not in exe.index:
                raise AssertionError(f'missing signal bar {s.local_date}')
            bar=exe.loc[signal_start]
            o,h,l,c=map(float,[bar.open,bar.high,bar.low,bar.close])
            F95=L+.95*R
            window=exe[(exe.index>=leave_ts)&(exe.index<=signal_start)]
            if window.empty: raise AssertionError(f'empty causal window {s.local_date}')
            rg=h-l
            body=c-o
            close_depths=(H-window.close.astype(float))/R
            rec={
                'local_date':str(s.local_date),'partition':part,'duration_regime':str(s.duration_regime),
                'outcome':str(z['outcome']),'h2':str(z['outcome'])=='H2_ARRIVAL','H':H,'L':L,'R':R,'F95':F95,
                'leave_ts':leave_ts,'signal_start':signal_start,'entry_ts':entry_ts,'entry_px':float(z['entry_px']),
                'minutes_leave_to_signal':float((signal_start-leave_ts)/pd.Timedelta(minutes=1)),
                'minutes_leave_to_entry':float((entry_ts-leave_ts)/pd.Timedelta(minutes=1)),
                'signal_open_depth_R':(H-o)/R,'signal_low_depth_R':(H-l)/R,'signal_close_depth_R':(H-c)/R,
                'signal_range_R':rg/R,'signal_body_R':body/R,
                'signal_body_ratio':abs(body)/rg if rg>0 else 0.0,
                'signal_close_position':(c-l)/rg if rg>0 else 0.5,
                'reclaim_overshoot_R':(c-F95)/R,
                'wick_below_F95_R':max(0.0,(F95-l)/R),
                'pre_entry_max_depth_R':max(0.0,(H-float(window.low.min()))/R),
                'pre_entry_min_close_depth_R':float(close_depths.min()),
                'pre_entry_max_close_depth_R':float(close_depths.max()),
                'pre_entry_bar_count':int(len(window)),
                'entry_depth_R':float(z['entry_depth_R']),
                'terminal_start':z.get('terminal_start',pd.NaT),
                'post_entry_mae_R':float(z.get('post_entry_mae_R',np.nan)),
            }
            rows.append(rec)
    d=pd.DataFrame(rows).sort_values(['partition','entry_ts']).reset_index(drop=True)
    for part,(n,w,l) in EXPECTED.items():
        z=d[d.partition==part]
        if len(z)!=n or int(z.h2.sum())!=w or int((~z.h2).sum())!=l:
            raise AssertionError(f'{part} integrity got n={len(z)} h2={int(z.h2.sum())} non={int((~z.h2).sum())}')
    if len(d)!=28 or int(d.h2.sum())!=26 or int((~d.h2).sum())!=2:
        raise AssertionError('combined integrity mismatch')
    return d

def winner_dist(d):
    w=d[d.h2]
    rows=[]
    for k in FEATURES:
        x=pd.to_numeric(w[k],errors='coerce').dropna()
        rows.append({'feature':k,'n':len(x),'min':x.min(),'p25':x.quantile(.25),'median':x.median(),'p75':x.quantile(.75),'max':x.max()})
    return pd.DataFrame(rows)

def flags(d,s):
    fails=d[~d.h2]
    rows=[]
    sm=s.set_index('feature')
    for _,r in fails.iterrows():
        for k in FEATURES:
            v=float(r[k]); a=sm.loc[k]
            if v<float(a['min']): flag='BELOW_WINNER_MIN'
            elif v>float(a['max']): flag='ABOVE_WINNER_MAX'
            elif v<float(a['p25']): flag='BELOW_WINNER_P25'
            elif v>float(a['p75']): flag='ABOVE_WINNER_P75'
            else: flag='INSIDE_WINNER_IQR'
            rows.append({'local_date':r.local_date,'partition':r.partition,'feature':k,'value':v,'flag':flag,
                         'winner_min':a['min'],'winner_p25':a['p25'],'winner_median':a['median'],'winner_p75':a['p75'],'winner_max':a['max']})
    return pd.DataFrame(rows)

def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists(): raise AssertionError('B27EQ preregistration missing')
    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995: raise AssertionError(f'coverage {cov}')
    d=build(x5); d.to_csv(OUT_DETAIL,index=False)
    s=winner_dist(d); s.to_csv(OUT_SUM,index=False)
    fl=flags(d,s); fl.to_csv(OUT_FLAGS,index=False)
    failures=d[~d.h2].copy()
    same=[]
    for k in FEATURES:
        q=fl[fl.feature==k]
        fs=list(q.flag)
        if len(fs)==2 and fs[0]==fs[1] and fs[0] in ['BELOW_WINNER_P25','ABOVE_WINNER_P75','BELOW_WINNER_MIN','ABOVE_WINNER_MAX']:
            same.append((k,fs[0]))
    outside_full=fl[fl.flag.isin(['BELOW_WINNER_MIN','ABOVE_WINNER_MAX'])]
    lines=[
      '# BNB Session-Native LONG M5 F95 Failure Anatomy — B27EQ Result','',
      f'Raw BNB 5m coverage: **{cov:.4%}**.','',
      'Post-validation descriptive diagnosis only. No new rule is promoted.','',
      '## Cohort integrity','',
      '- Development F95 entries: **21 = 20 H2 + 1 non-H2**',
      '- Reference-validation F95 entries: **7 = 6 H2 + 1 non-H2**',
      '- Combined: **28 = 26 H2 + 2 non-H2**','',
      '## Winner causal pre-entry distribution','',
      '| Feature | Min | P25 | Median | P75 | Max |','|---|---:|---:|---:|---:|---:|'
    ]
    for _,r in s.iterrows():
        lines.append(f"| {r.feature} | {f(r['min'])} | {f(r.p25)} | {f(r['median'])} | {f(r.p75)} | {f(r['max'])} |")
    lines += ['', '## The two observed failures','',
              '| Date | Partition | Leave→entry | Signal low depth | Signal close depth | Overshoot | Wick below F95 | Pre-entry max depth | Entry depth | Post-entry MAE |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in failures.iterrows():
        lines.append(f"| {r.local_date} | {r.partition} | {r.minutes_leave_to_entry:.1f}m | {r.signal_low_depth_R:.4f}R | {r.signal_close_depth_R:.4f}R | {r.reclaim_overshoot_R:.4f}R | {r.wick_below_F95_R:.4f}R | {r.pre_entry_max_depth_R:.4f}R | {r.entry_depth_R:.4f}R | {r.post_entry_mae_R:.4f}R |")
    lines += ['', '## Same-direction outside-winner-IQR descriptive leads','']
    if same:
        for k,flag in same: lines.append(f'- **{k}**: both failures = `{flag}`')
    else: lines.append('- **None.** The two failures do not share a same-direction outside-IQR anomaly on the preregistered causal feature set.')
    lines += ['', '## Outside full winner min-max anomalies','']
    if len(outside_full):
        for _,r in outside_full.iterrows(): lines.append(f"- {r.local_date} / **{r.feature}** = {r.value:.4f}: `{r.flag}` versus winner range [{r.winner_min:.4f}, {r.winner_max:.4f}]")
    else: lines.append('- **None.** Neither failure is outside the full winner min-max range on any preregistered causal feature.')
    lines += ['', 'Interpretation: B27EQ is deliberately too small for a new filter. A feature is only a descriptive lead if both failures separate in the same direction; even then it requires a separately frozen test and cannot be called validated here.','',
              '**Status: B27EQ_BNB_F95_FAILURE_ANATOMY_COMPLETE**','',
              'STOP: no threshold tuning, no candidate promotion, no F90/F85, no economics, no August, no SHORT/live.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27EQ_BNB_F95_FAILURE_ANATOMY_COMPLETE\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
