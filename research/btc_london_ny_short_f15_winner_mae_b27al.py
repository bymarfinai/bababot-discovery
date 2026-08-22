#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_retrace_zone_b27ak as b27ak

ROOT = Path(__file__).resolve().parent.parent
PERSISTED = ROOT / 'BTC_LONDON_NY_SHORT_RETRACE_ZONE_B27AK_Candidates.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_WINNER_MAE_B27AL_Result.md'
OUT_PATHS = ROOT / 'BTC_LONDON_NY_SHORT_F15_WINNER_MAE_B27AL_Paths.csv'
OUT_WIN = ROOT / 'BTC_LONDON_NY_SHORT_F15_WINNER_MAE_B27AL_WinnerSummary.csv'
OUT_SURV = ROOT / 'BTC_LONDON_NY_SHORT_F15_WINNER_MAE_B27AL_StopSurvival.csv'
OUT_FAIL = ROOT / 'BTC_LONDON_NY_SHORT_F15_WINNER_MAE_B27AL_FailureSummary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_WINNER_MAE_B27AL_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
F15 = 0.15
PARTS = ('external','development','reference_validation','august')
DISTANCES = tuple(round(x,2) for x in np.arange(0.05,0.851,0.05))


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def inclusive(x5, start, last):
    return fast_slice(x5, start, last + BAR5)


def qtile(x, q):
    z = pd.to_numeric(x, errors='coerce').dropna()
    return float(z.quantile(q)) if len(z) else np.nan


def synthetic_test():
    H,L = 100.0,90.0; rng=10.0; entry=L+F15*rng
    idx = pd.date_range('2026-01-02 14:00', periods=4, freq='5min', tz='UTC')
    q = pd.DataFrame([
        {'open':91.0,'high':91.8,'low':90.9,'close':91.4},
        {'open':91.4,'high':92.4,'low':90.8,'close':91.2},
        {'open':91.2,'high':93.0,'low':90.5,'close':91.0},
        {'open':91.0,'high':93.5,'low':89.8,'close':90.1},
    ], index=idx)
    assert float(q.iloc[0].low) <= entry <= float(q.iloc[0].high)
    pre = fast_slice(q, idx[0], idx[3]); thru = inclusive(q, idx[0], idx[3])
    pf = (float(pre.high.max())-L)/rng
    tf = (float(thru.high.max())-L)/rng
    assert abs(pf-0.30) < 1e-12 and abs(tf-0.35) < 1e-12
    assert abs(max(0,pf-F15)-0.15) < 1e-12
    assert abs(max(0,tf-F15)-0.20) < 1e-12
    assert not (tf < F15+0.20)   # equality = stop touch
    assert tf < F15+0.25


def load_persisted():
    p = pd.read_csv(PERSISTED)
    p = p[p.entry_name=='F15'].copy()
    for c in ('signal_ts','eligible_start','h2_bar_start','opposite_break_bar_start','session_end','fill_bar_start'):
        p[c] = pd.to_datetime(p[c], utc=True, errors='coerce')
    p['filled'] = p.filled.astype(str).str.lower().eq('true')
    p['h2_after_fill'] = p.h2_after_fill.astype(str).str.lower().eq('true')
    return p.sort_values(['partition','signal_ts']).reset_index(drop=True)


def rebuild(x5):
    s = b27ad.load_k1()
    w = pd.DataFrame([b27ad.build_window(x5,r) for _,r in s.iterrows()])
    e = pd.DataFrame([b27ak.candidate_fill(x5,row,'F15',F15) for _,row in w.iterrows()])
    return s,w,e


def assert_identity(rb, ps):
    assert len(rb)==len(ps)
    rb=rb.sort_values(['partition','signal_ts']).reset_index(drop=True)
    ps=ps.sort_values(['partition','signal_ts']).reset_index(drop=True)
    assert list(rb.partition.astype(str))==list(ps.partition.astype(str))
    assert list(pd.to_datetime(rb.signal_ts,utc=True))==list(pd.to_datetime(ps.signal_ts,utc=True))
    assert list(rb.filled.astype(bool))==list(ps.filled.astype(bool))
    assert list(rb.h2_after_fill.astype(bool))==list(ps.h2_after_fill.astype(bool))
    for i in range(len(rb)):
        if bool(rb.loc[i,'filled']):
            assert pd.Timestamp(rb.loc[i,'fill_bar_start'])==pd.Timestamp(ps.loc[i,'fill_bar_start'])
            assert abs(float(rb.loc[i,'entry_px'])-float(ps.loc[i,'entry_px'])) < 1e-9*max(1.0,abs(float(rb.loc[i,'entry_px'])))


def path_row(x5,w,e):
    H=float(w.H); L=float(w.L); rng=H-L; px=L+F15*rng
    base={'partition':w.partition,'date_utc':w.date_utc,'signal_ts':pd.Timestamp(w.signal_ts),
          'window_status':w.window_status,'filled':bool(e.filled),'h2_after_fill':bool(e.h2_after_fill),
          'fill_bar_start':pd.Timestamp(e.fill_bar_start) if bool(e.filled) else pd.NaT,
          'entry_px':float(e.entry_px) if bool(e.filled) else np.nan,'entry_fraction':F15,
          'H':H,'L':L,'range':rng,'h2_bar_start':pd.Timestamp(w.h2_bar_start) if pd.notna(w.h2_bar_start) else pd.NaT}
    if not bool(e.filled):
        return {**base,'path_class':'NO_FILL','pre_max_frac':np.nan,'pre_required_d':np.nan,
                'cons_max_frac':np.nan,'cons_required_d':np.nan,'next_max_frac':np.nan,'next_required_d':np.nan,
                'failure_max_frac':np.nan,'failure_required_d':np.nan}
    fill=pd.Timestamp(e.fill_bar_start)
    assert abs(float(e.entry_px)-px) < 1e-9*max(1.0,abs(px))
    if bool(e.h2_after_fill):
        h2=pd.Timestamp(w.h2_bar_start); assert fill < h2
        pre=fast_slice(x5,fill,h2); thru=inclusive(x5,fill,h2)
        assert len(pre)>=1 and len(thru)==len(pre)+1
        pf=(float(pre.high.max())-L)/rng; cf=(float(thru.high.max())-L)/rng
        nxt=fast_slice(x5,fill+BAR5,h2)
        nf=(float(nxt.high.max())-L)/rng if len(nxt) else np.nan
        return {**base,'path_class':'F15_H2_WINNER','pre_max_frac':pf,'pre_required_d':max(0,pf-F15),
                'cons_max_frac':cf,'cons_required_d':max(0,cf-F15),'next_max_frac':nf,
                'next_required_d':max(0,nf-F15) if pd.notna(nf) else np.nan,
                'failure_max_frac':np.nan,'failure_required_d':np.nan}
    if w.window_status=='OPPOSITE_BREAK_BEFORE_H2':
        q=inclusive(x5,fill,pd.Timestamp(w.opposite_break_bar_start))
    elif w.window_status=='AMBIGUOUS_H2_VS_OPPOSITE_BREAK':
        q=inclusive(x5,fill,pd.Timestamp(w.terminal_bar_start))
    else:
        q=fast_slice(x5,fill,pd.Timestamp(w.session_end))
    assert len(q)>=1
    ff=(float(q.high.max())-L)/rng
    return {**base,'path_class':'F15_NON_H2_FILL','pre_max_frac':np.nan,'pre_required_d':np.nan,
            'cons_max_frac':np.nan,'cons_required_d':np.nan,'next_max_frac':np.nan,'next_required_d':np.nan,
            'failure_max_frac':ff,'failure_required_d':max(0,ff-F15)}


def summarize(paths):
    wins=[]; fails=[]; surv=[]
    for part in PARTS:
        g=paths[(paths.partition==part)&(paths.path_class=='F15_H2_WINNER')]
        wins.append({'partition':part,'winner_n':len(g),
                     'pre_p50':qtile(g.pre_required_d,.5),'pre_p75':qtile(g.pre_required_d,.75),'pre_p90':qtile(g.pre_required_d,.9),'pre_p95':qtile(g.pre_required_d,.95),'pre_max':float(g.pre_required_d.max()) if len(g) else np.nan,
                     'cons_p50':qtile(g.cons_required_d,.5),'cons_p75':qtile(g.cons_required_d,.75),'cons_p90':qtile(g.cons_required_d,.9),'cons_p95':qtile(g.cons_required_d,.95),'cons_max':float(g.cons_required_d.max()) if len(g) else np.nan})
        f=paths[(paths.partition==part)&(paths.path_class=='F15_NON_H2_FILL')]
        fails.append({'partition':part,'failure_n':len(f),'p50':qtile(f.failure_required_d,.5),'p75':qtile(f.failure_required_d,.75),'p90':qtile(f.failure_required_d,.9),'p95':qtile(f.failure_required_d,.95),'max':float(f.failure_required_d.max()) if len(f) else np.nan})
        for d in DISTANCES:
            stop=F15+d
            if len(g):
                pre=(g.pre_max_frac.astype(float)<stop); cons=(g.cons_max_frac.astype(float)<stop)
                n=len(g)
            else:
                pre=pd.Series(dtype=bool); cons=pd.Series(dtype=bool); n=0
            surv.append({'partition':part,'distance':d,'stop_fraction':stop,'winner_n':n,
                         'pre_survive_rate':float(pre.mean()) if n else np.nan,
                         'cons_survive_rate':float(cons.mean()) if n else np.nan})
    return pd.DataFrame(wins),pd.DataFrame(fails),pd.DataFrame(surv)


def num(v): return '-' if pd.isna(v) else f'{float(v):.3f}'
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    synthetic_test()
    x5,coverage=b27ad.b21.load5(); assert abs(float(coverage)-1.0)<1e-12
    s,w,e=rebuild(x5); ps=load_persisted(); assert_identity(e,ps)
    expected={'external':(50,37),'development':(79,59),'reference_validation':(34,24),'august':(1,1)}
    for part,(nf,nh) in expected.items():
        g=e[(e.partition==part)&e.filled.astype(bool)]
        assert len(g)==nf and int(g.h2_after_fill.sum())==nh
    paths=pd.DataFrame([path_row(x5,w.iloc[i],e.iloc[i]) for i in range(len(e))])
    for r in paths[paths.path_class=='F15_H2_WINNER'].itertuples(index=False):
        assert pd.Timestamp(r.fill_bar_start)<pd.Timestamp(r.h2_bar_start)
        assert float(r.cons_required_d)+1e-12>=float(r.pre_required_d)
    win,fail,surv=summarize(paths)
    paths.to_csv(OUT_PATHS,index=False); win.to_csv(OUT_WIN,index=False); fail.to_csv(OUT_FAIL,index=False); surv.to_csv(OUT_SURV,index=False)
    OUT_STATUS.write_text('B27AL_PASS\n')
    lines=['# B27AL — BTC London->NY SHORT F15 Winner MAE / Stop-Distance Audit — Result','',f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
           '**Audit status: PASS.** B27AK F15 fill identity and H2 classifications reproduced exactly from raw 5m chronology.','',
           'B27AL is diagnostic only: no stop distance is selected or promoted.','',
           '## F15 H2-winner adverse excursion','',
           '| Partition | Winners | Pre-H2 D P50 | P75 | P90 | P95 | Max | Conservative-through-H2 D P50 | P75 | P90 | P95 | Max |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in win.itertuples(index=False):
        lines.append(f'| {r.partition} | {int(r.winner_n)} | {num(r.pre_p50)} | {num(r.pre_p75)} | {num(r.pre_p90)} | {num(r.pre_p95)} | {num(r.pre_max)} | {num(r.cons_p50)} | {num(r.cons_p75)} | {num(r.cons_p90)} | {num(r.cons_p95)} | {num(r.cons_max)} |')
    lines += ['', '## Selected descriptive survival points','', '| Partition | D | Stop fraction | H2 winners | Pre-H2 survive | Conservative survive |','|---|---:|---:|---:|---:|---:|']
    for part in PARTS:
        for d in (0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.85):
            r=surv[(surv.partition==part)&(np.isclose(surv.distance,d))].iloc[0]
            lines.append(f'| {part} | {d:.2f} | {r.stop_fraction:.2f} | {int(r.winner_n)} | {pct(r.pre_survive_rate)} | {pct(r.cons_survive_rate)} |')
    lines += ['', '## Non-H2 filled-path comparison','', '| Partition | Non-H2 fills | Adverse D P50 | P75 | P90 | P95 | Max |','|---|---:|---:|---:|---:|---:|---:|']
    for r in fail.itertuples(index=False):
        lines.append(f'| {r.partition} | {int(r.failure_n)} | {num(r.p50)} | {num(r.p75)} | {num(r.p90)} | {num(r.p95)} | {num(r.max)} |')
    lines += ['', 'Distance D is measured upward from F15 in previous-London-range units; equality with a stop counts as stopped.','', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
