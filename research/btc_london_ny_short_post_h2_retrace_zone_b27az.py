#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad

ROOT=Path(__file__).resolve().parent.parent
WINS=ROOT/'BTC_LONDON_NY_SHORT_F15_BETWEEN_H2_H3_B27AY_Windows.csv'
OUT_MD=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_RETRACE_ZONE_B27AZ_Result.md'
OUT_CSV=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_RETRACE_ZONE_B27AZ_Atlas.csv'
OUT_STATUS=ROOT/'BTC_LONDON_NY_SHORT_POST_H2_RETRACE_ZONE_B27AZ_Status.txt'
BAR5=pd.Timedelta(minutes=5)
PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
FRACS=tuple(i/100 for i in range(5,100,5))


def valid_low_retest(r,L,H):
    return float(r.low)<=L and float(r.close)>=L and float(r.close)<=H


def first_event(r,L,H):
    c=float(r.close)
    if c<L: return 'DIRECT_BREAKDOWN'
    if c>H: return 'OPPOSITE_BREAK'
    if valid_low_retest(r,L,H): return 'LOW_REVISIT'
    return None


def scan_candidate(x5,w,frac):
    H=float(w.H); L=float(w.L); R=H-L; px=L+frac*R
    start=pd.Timestamp(w.eligible_start); end=pd.Timestamp(w.session_end)
    q=b27ad.fast_slice(x5,start,end)
    fill=pd.NaT; fill_i=None; pre_terminal='SESSION_END'
    for i,(ts,r) in enumerate(q.iterrows()):
        ev=first_event(r,L,H)
        if ev is not None:
            pre_terminal=ev; break
        if float(r.low)<=px<=float(r.high):
            fill=ts; fill_i=i; break
    if fill_i is None:
        return dict(filled=False,fill_bar_start=pd.NaT,entry_px=px,post_event='NO_FILL',downside_resolution=False,direct_breakdown=False,opposite_break=False,unresolved=False,minutes_to_resolution=np.nan,pre_fill_terminal=pre_terminal)
    post_event='SESSION_END'; res_ts=pd.NaT
    for j in range(fill_i+1,len(q)):
        ts=q.index[j]; r=q.iloc[j]; ev=first_event(r,L,H)
        if ev is not None:
            post_event=ev; res_ts=ts; break
    downside=post_event in ('LOW_REVISIT','DIRECT_BREAKDOWN')
    mins=float((res_ts-fill)/pd.Timedelta(minutes=1)) if downside else np.nan
    return dict(filled=True,fill_bar_start=fill,entry_px=px,post_event=post_event,downside_resolution=downside,direct_breakdown=post_event=='DIRECT_BREAKDOWN',opposite_break=post_event=='OPPOSITE_BREAK',unresolved=post_event=='SESSION_END',minutes_to_resolution=mins,pre_fill_terminal='FILLED')


def main():
    x5,coverage=b27ad.b21.load5(); assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12
    w=pd.read_csv(WINS)
    for c in ('signal_ts','signal_bar_start','session_end','h2_bar_start','leave2_bar_start','eligible_start'):
        w[c]=pd.to_datetime(w[c],utc=True,errors='coerce')
    clean=w[w.eligible_start.notna()].copy()
    # Frozen B27AY clean-window identities.
    exp_clean={'external':13,'development':42,'reference_validation':14,'august':1}
    for p,n in exp_clean.items(): assert len(clean[clean.partition==p])==n,(p,len(clean[clean.partition==p]),n)

    details=[]
    for _,r in clean.iterrows():
        for f in FRACS:
            z=scan_candidate(x5,r,f)
            details.append({'partition':r.partition,'signal_ts':r.signal_ts,'frac':f,'zone':f'F{int(round(f*100)):02d}',**z})
    d=pd.DataFrame(details)
    # F15 must reproduce B27AY fills exactly before interpreting any other zone.
    exp_f15={'external':10,'development':26,'reference_validation':6,'august':1}
    f15=d[(d.frac==0.15)&d.filled]
    for p,n in exp_f15.items(): assert len(f15[f15.partition==p])==n,(p,len(f15[f15.partition==p]),n)

    rows=[]
    for f in FRACS:
        zone=f'F{int(round(f*100)):02d}'
        for p in (*PARTS,'POOLED_MAJOR'):
            if p=='POOLED_MAJOR':
                g=d[(d.frac==f)&d.partition.isin(MAJOR)]; c=clean[clean.partition.isin(MAJOR)]
            else:
                g=d[(d.frac==f)&(d.partition==p)]; c=clean[clean.partition==p]
            gf=g[g.filled]
            n=len(gf); res=int(gf.downside_resolution.sum()) if n else 0
            rows.append(dict(zone=zone,frac=f,partition=p,clean_windows=len(c),fills=n,fill_given_clean=n/len(c) if len(c) else np.nan,
                             downside_resolutions=res,resolution_rate=res/n if n else np.nan,
                             direct_breakdowns=int(gf.direct_breakdown.sum()) if n else 0,
                             low_revisits=int((gf.post_event=='LOW_REVISIT').sum()) if n else 0,
                             opposite_breaks=int(gf.opposite_break.sum()) if n else 0,
                             unresolved=int(gf.unresolved.sum()) if n else 0,
                             median_minutes_to_resolution=float(gf.loc[gf.downside_resolution,'minutes_to_resolution'].median()) if res else np.nan))
    a=pd.DataFrame(rows); a.to_csv(OUT_CSV,index=False)
    pool=a[a.partition=='POOLED_MAJOR'].copy()
    low=pool[pool.frac<=0.35]
    high=pool[pool.frac>=0.65]
    max_fill=pool.sort_values(['fills','resolution_rate'],ascending=[False,False]).iloc[0]
    max_res=pool[pool.fills>0].sort_values(['resolution_rate','fills'],ascending=[False,False]).iloc[0]
    lines=['# B27AZ — BTC London->NY SHORT Post-H2 Full-Range Entry-Zone Discovery — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
           '**Audit status: PASS.** B27AY clean post-H2 windows and F15 fill identities reproduced before the F05–F95 atlas was interpreted.','',
           '| Zone | Clean | Fills | Fill/clean | Downside resolve | Resolve/fill | Direct break | Low revisit | Opp break | Unresolved | Med min |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in pool.itertuples(index=False):
        lines.append(f'| {r.zone} | {int(r.clean_windows)} | {int(r.fills)} | {100*r.fill_given_clean:.1f}% | {int(r.downside_resolutions)} | {100*r.resolution_rate:.1f}% | {int(r.direct_breakdowns)} | {int(r.low_revisits)} | {int(r.opposite_breaks)} | {int(r.unresolved)} | {"-" if pd.isna(r.median_minutes_to_resolution) else f"{r.median_minutes_to_resolution:.1f}"} |')
    lines += ['','## Frozen readout','',
              f'Maximum pooled fill count: **{max_fill.zone}** with **{int(max_fill.fills)}** fills and **{100*max_fill.resolution_rate:.1f}%** downside resolution.',
              f'Highest pooled conditional resolution among zones with a fill: **{max_res.zone}** with **{100*max_res.resolution_rate:.1f}%** resolution across **{int(max_res.fills)}** fills.',
              f'High-range F65–F95 total zone rows with at least one pooled fill: **{int((high.fills>0).sum())}/7**.','',
              'No PnL, stop, target, runner, regime, or confirmation rule was used. This atlas does not promote a strategy. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text('B27AZ_PASS\n'); print('\n'.join(lines))

if __name__=='__main__': main()
