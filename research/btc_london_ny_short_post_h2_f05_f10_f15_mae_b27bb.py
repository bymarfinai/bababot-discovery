#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_post_h2_retrace_zone_b27az as b27az

ROOT=Path(__file__).resolve().parent.parent
WINS=ROOT/'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Windows.csv'
OUT_MD=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_MAE_B27BB_Result.md'
OUT_PATHS=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_MAE_B27BB_Paths.csv'
OUT_SUM=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_MAE_B27BB_Summary.csv'
OUT_SURV=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_MAE_B27BB_Survival.csv'
OUT_STATUS=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_F05_F10_F15_MAE_B27BB_Status.txt'
BAR5=pd.Timedelta(minutes=5)
PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
CANDS={'F05':0.05,'F10':0.10,'F15':0.15}
DGRID=(0.10,0.20,0.30,0.40,0.50,0.60)
E20=0.20


def qtile(s,q):
    x=pd.to_numeric(s,errors='coerce').dropna()
    return float(x.quantile(q)) if len(x) else np.nan


def load_clean():
    w=pd.read_csv(WINS)
    for c in ('signal_ts','signal_bar_start','session_end','h2_bar_start','leave2_bar_start','eligible_start'):
        w[c]=pd.to_datetime(w[c],utc=True,errors='coerce')
    clean=w[w.eligible_start.notna()].copy()
    exp={'external':13,'development':42,'reference_validation':14,'august':1}
    for p,n in exp.items(): assert len(clean[clean.partition==p])==n,(p,len(clean[clean.partition==p]),n)
    return clean


def build_fills(x5,clean):
    rows=[]
    for _,r in clean.iterrows():
        for z,f in CANDS.items():
            s=b27az.scan_candidate(x5,r,f)
            if bool(s['filled']):
                rows.append(dict(zone=z,entry_frac=f,partition=r.partition,date_utc=r.date_utc,
                    signal_ts=r.signal_ts,fill_bar_start=pd.Timestamp(s['fill_bar_start']),entry_px=float(s['entry_px']),
                    H=float(r.H),L=float(r.L),range=float(r.H-r.L),session_end=pd.Timestamp(r.session_end)))
    f=pd.DataFrame(rows)
    expected={
        'F05':{'external':8,'development':17,'reference_validation':3,'august':0},
        'F10':{'external':10,'development':22,'reference_validation':5,'august':0},
        'F15':{'external':10,'development':26,'reference_validation':6,'august':1},
    }
    for z,d in expected.items():
        for p,n in d.items():
            got=len(f[(f.zone==z)&(f.partition==p)])
            assert got==n,(z,p,got,n)
    assert len(f[(f.zone=='F05')&f.partition.isin(MAJOR)])==28
    assert len(f[(f.zone=='F10')&f.partition.isin(MAJOR)])==37
    assert len(f[(f.zone=='F15')&f.partition.isin(MAJOR)])==42
    return f


def path_one(x5,r):
    z=str(r.zone); ef=float(r.entry_frac); H=float(r.H); L=float(r.L); R=H-L
    start=pd.Timestamp(r.fill_bar_start); end=pd.Timestamp(r.session_end); target=L-E20*R
    q=b27ad.fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start
    act_i=None; terminal_i=len(q)-1; path_class='NON_E20_SESSION_END'
    for i,(ts,b) in enumerate(q.iterrows()):
        c=float(b.close); lo=float(b.low)
        if i>0 and lo<=target:
            act_i=i; terminal_i=i; path_class='E20_REACHER'; break
        if c>H:
            terminal_i=i; path_class='NON_E20_OPPOSITE_BREAK'; break
    if act_i is not None:
        pre=q.iloc[:act_i]  # fill through bar before activation
        cons=q.iloc[:act_i+1]
        assert len(pre)>=1
        pre_frac=(float(pre.high.max())-L)/R
        cons_frac=(float(cons.high.max())-L)/R
        return dict(**r.to_dict(),path_class=path_class,e20_reached=True,e20_bar_start=q.index[act_i],
                    terminal_bar_start=q.index[terminal_i],pre_e20_max_high_frac=pre_frac,
                    pre_e20_required_d=max(0.0,pre_frac-ef),cons_max_high_frac=cons_frac,
                    cons_required_d=max(0.0,cons_frac-ef),failure_max_high_frac=np.nan,failure_required_d=np.nan)
    fail=q.iloc[:terminal_i+1]
    ff=(float(fail.high.max())-L)/R
    return dict(**r.to_dict(),path_class=path_class,e20_reached=False,e20_bar_start=pd.NaT,
                terminal_bar_start=q.index[terminal_i],pre_e20_max_high_frac=np.nan,pre_e20_required_d=np.nan,
                cons_max_high_frac=np.nan,cons_required_d=np.nan,failure_max_high_frac=ff,
                failure_required_d=max(0.0,ff-ef))


def summarize(paths):
    rows=[]; surv=[]
    for z,ef in CANDS.items():
        for p in (*PARTS,'POOLED_MAJOR'):
            g=paths[(paths.zone==z)&paths.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else paths[(paths.zone==z)&(paths.partition==p)]
            w=g[g.e20_reached.astype(bool)]; f=g[~g.e20_reached.astype(bool)]
            rows.append(dict(zone=z,entry_frac=ef,partition=p,n=len(g),e20_n=len(w),e20_rate=len(w)/len(g) if len(g) else np.nan,
                win_pre_p50=qtile(w.pre_e20_required_d,.50),win_pre_p75=qtile(w.pre_e20_required_d,.75),
                win_pre_p90=qtile(w.pre_e20_required_d,.90),win_pre_p95=qtile(w.pre_e20_required_d,.95),
                win_pre_max=float(w.pre_e20_required_d.max()) if len(w) else np.nan,
                win_cons_p50=qtile(w.cons_required_d,.50),win_cons_p75=qtile(w.cons_required_d,.75),
                win_cons_p90=qtile(w.cons_required_d,.90),win_cons_p95=qtile(w.cons_required_d,.95),
                win_cons_max=float(w.cons_required_d.max()) if len(w) else np.nan,
                fail_n=len(f),fail_p50=qtile(f.failure_required_d,.50),fail_p75=qtile(f.failure_required_d,.75),
                fail_p90=qtile(f.failure_required_d,.90),fail_p95=qtile(f.failure_required_d,.95),
                fail_max=float(f.failure_required_d.max()) if len(f) else np.nan))
            for d in DGRID:
                surv.append(dict(zone=z,partition=p,distance=d,stop_frac=ef+d,winner_n=len(w),
                    pre_survive=float((w.pre_e20_required_d<d).mean()) if len(w) else np.nan,
                    conservative_survive=float((w.cons_required_d<d).mean()) if len(w) else np.nan))
    return pd.DataFrame(rows),pd.DataFrame(surv)


def synthetic_test():
    idx=pd.date_range('2026-01-05 14:00',periods=5,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':91.0,'high':91.4,'low':90.8,'close':91.1},
        {'open':91.1,'high':92.0,'low':90.7,'close':91.5},
        {'open':91.5,'high':92.5,'low':87.8,'close':88.5},
        {'open':88.5,'high':89.0,'low':87.0,'close':87.5},
        {'open':87.5,'high':88.0,'low':87.0,'close':87.2},],index=idx)
    r=pd.Series(dict(zone='F10',entry_frac=.10,partition='x',date_utc='2026-01-05',signal_ts=idx[0]-BAR5,
        fill_bar_start=idx[0],entry_px=91.0,H=100.0,L=90.0,range=10.0,session_end=idx[-1]+BAR5))
    z=path_one(x,r)
    assert z['e20_reached'] and z['e20_bar_start']==idx[2]
    assert abs(z['pre_e20_required_d']-.10)<1e-12
    assert abs(z['cons_required_d']-.15)<1e-12


def num(v): return '-' if pd.isna(v) else f'{float(v):.3f}'
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    synthetic_test()
    x5,coverage=b27ad.b21.load5(); assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12
    clean=load_clean(); fills=build_fills(x5,clean)
    paths=pd.DataFrame([path_one(x5,r) for _,r in fills.iterrows()])
    sm,surv=summarize(paths)
    paths.to_csv(OUT_PATHS,index=False); sm.to_csv(OUT_SUM,index=False); surv.to_csv(OUT_SURV,index=False)
    OUT_STATUS.write_text('B27BB_PASS\n')
    lines=['# B27BB — BTC London->NY SHORT Post-Retest#2 F05/F10/F15 Winner MAE / Natural Stop-Distance Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AZ/B27BA clean windows and F05/F10/F15 fill identities reproduced before stop-independent MAE was interpreted.','',
        'Old F65 invalidation was NOT applied. B27BB selects no stop.','',
        '## Pooled-major winner MAE','',
        '| Zone | N | E20 raw | E20 rate | Pre-E20 D P50 | P75 | P90 | P95 | Max | Through-E20 D P50 | P75 | P90 | P95 | Max |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for z in CANDS:
        r=sm[(sm.zone==z)&(sm.partition=='POOLED_MAJOR')].iloc[0]
        lines.append(f'| {z} | {int(r.n)} | {int(r.e20_n)} | {pct(r.e20_rate)} | {num(r.win_pre_p50)} | {num(r.win_pre_p75)} | {num(r.win_pre_p90)} | {num(r.win_pre_p95)} | {num(r.win_pre_max)} | {num(r.win_cons_p50)} | {num(r.win_cons_p75)} | {num(r.win_cons_p90)} | {num(r.win_cons_p95)} | {num(r.win_cons_max)} |')
    lines += ['','## Pooled-major non-E20 adverse distance','',
        '| Zone | Fail N | D P50 | P75 | P90 | P95 | Max |','|---|---:|---:|---:|---:|---:|---:|']
    for z in CANDS:
        r=sm[(sm.zone==z)&(sm.partition=='POOLED_MAJOR')].iloc[0]
        lines.append(f'| {z} | {int(r.fail_n)} | {num(r.fail_p50)} | {num(r.fail_p75)} | {num(r.fail_p90)} | {num(r.fail_p95)} | {num(r.fail_max)} |')
    lines += ['','## Major partitions — conservative winner D','',
        '| Zone | Partition | Winners | P50 | P75 | P90 | P95 | Max |','|---|---|---:|---:|---:|---:|---:|---:|']
    for z in CANDS:
        for p in MAJOR:
            r=sm[(sm.zone==z)&(sm.partition==p)].iloc[0]
            lines.append(f'| {z} | {p} | {int(r.e20_n)} | {num(r.win_cons_p50)} | {num(r.win_cons_p75)} | {num(r.win_cons_p90)} | {num(r.win_cons_p95)} | {num(r.win_cons_max)} |')
    lines += ['','## Pooled-major descriptive winner survival','',
        '| Zone | D | Stop fraction | Winners | Pre-E20 survive | Conservative survive |','|---|---:|---:|---:|---:|---:|']
    for z in CANDS:
        for d in DGRID:
            r=surv[(surv.zone==z)&(surv.partition=='POOLED_MAJOR')&np.isclose(surv.distance,d)].iloc[0]
            lines.append(f'| {z} | {d:.2f} | {r.stop_frac:.2f} | {int(r.winner_n)} | {pct(r.pre_survive)} | {pct(r.conservative_survive)} |')
    lines += ['','Distance D is measured upward from each zone’s own entry fraction. Equality with a hypothetical stop counts as stopped.','No PnL or stop was selected. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
