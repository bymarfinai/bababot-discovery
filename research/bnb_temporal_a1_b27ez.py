#!/usr/bin/env python3
from __future__ import annotations

import math, statistics, sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'research'
for p in (str(ROOT),str(RESEARCH)):
    if p not in sys.path: sys.path.insert(0,p)
import bnb_session_native_london_ny_long_m1_structure_b27em as b27em

TARGET='BNBUSDT'
DEV_START=pd.Timestamp('2022-01-01',tz='UTC'); DEV_END=pd.Timestamp('2025-01-01',tz='UTC')
WIB=ZoneInfo('Asia/Jakarta')
HORIZONS=(15,30,60,120,240); HBAR={m:m//15 for m in HORIZONS}
THRESHOLDS=(0.3,0.5,0.8,1.0); WEEKDAYS=('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
BLOCKS=8; MIN_N=120; STEP_NS=15*60*1_000_000_000
PFX='BNB_TEMPORAL_A1_B27EZ'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'; OUT_SLOT=ROOT/f'{PFX}_Slot_Bests.csv'; OUT_RAW=ROOT/f'{PFX}_Raw_WR_Leaderboard.csv'; OUT_ROBUST=ROOT/f'{PFX}_Robust_Leaderboard.csv'; OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'

def med(xs):
    a=[float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.median(a)) if a else np.nan

def first_touch_np(highs,lows,entry,direction,th):
    fav=entry*(1+direction*th/100); adv=entry*(1-direction*th/100)
    if direction>0:
        for hi,lo in zip(highs,lows):
            hf=hi>=fav; ha=lo<=adv
            if hf and ha:return 'AMBIGUOUS'
            if hf:return 'FAVORABLE'
            if ha:return 'ADVERSE'
    else:
        for hi,lo in zip(highs,lows):
            hf=lo<=fav; ha=hi>=adv
            if hf and ha:return 'AMBIGUOUS'
            if hf:return 'FAVORABLE'
            if ha:return 'ADVERSE'
    return 'NONE'

def make15(x5):
    q=x5[(x5.index>=DEV_START)&(x5.index<DEV_END)].copy()
    exp5=int((DEV_END-DEV_START)/pd.Timedelta(minutes=5)); cov5=len(q)/exp5
    if cov5<.995: raise AssertionError(f'development 5m coverage {cov5:.6%}')
    agg=q[['open','high','low','close']].resample('15min',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'})
    cnt=q.close.resample('15min',label='left',closed='left').count()
    x=agg[cnt.eq(3)].dropna().copy(); exp15=int((DEV_END-DEV_START)/pd.Timedelta(minutes=15)); cov15=len(x)/exp15
    if cov15<.995: raise AssertionError(f'development 15m coverage {cov15:.6%}')
    return x,cov15

def metrics(ev,direction):
    ret=np.asarray([e['ret'] for e in ev],dtype=float); signed=direction*ret
    wins=int((signed>0).sum()); losses=int((signed<0).sum()); resolved=wins+losses
    entry=np.asarray([e['entry'] for e in ev]); mx=np.asarray([e['mx'] for e in ev]); mn=np.asarray([e['mn'] for e in ev])
    if direction>0: mfe=100*(mx-entry)/entry; mae=100*(entry-mn)/entry
    else: mfe=100*(entry-mn)/entry; mae=100*(mx-entry)/entry
    bwrs=[]; pos=strong=very=0
    blocks=np.asarray([e['block'] for e in ev],dtype=int)
    for b in range(BLOCKS):
        z=signed[blocks==b]; w=int((z>0).sum()); l=int((z<0).sum()); r=w+l
        if r:
            wr=100*w/r; bwrs.append(wr); pos+=int(wr>50); strong+=int(wr>=60); very+=int(wr>=65)
    mmfe=float(np.median(mfe)); mmae=float(np.median(mae))
    out={'n':len(ev),'resolved':resolved,'wins':wins,'losses':losses,'wr_pct':100*wins/resolved if resolved else np.nan,
         'avg_signed_return_pct':float(np.mean(signed)),'median_signed_return_pct':float(np.median(signed)),
         'median_mfe_pct':mmfe,'median_mae_pct':mmae,'mfe_mae_ratio':mmfe/mmae if mmae>0 else np.nan,
         'positive_blocks_gt50':pos,'strong_blocks_ge60':strong,'very_strong_blocks_ge65':very,
         'median_block_wr_pct':med(bwrs),'min_block_wr_pct':min(bwrs) if bwrs else np.nan}
    for th in THRESHOLDS:
        c=defaultdict(int)
        for e in ev:c[first_touch_np(e['hi'],e['lo'],e['entry'],direction,th)]+=1
        dec=c['FAVORABLE']+c['ADVERSE']; tag=str(th).replace('.','p')
        out[f'ft_{tag}_fav']=c['FAVORABLE'];out[f'ft_{tag}_adv']=c['ADVERSE'];out[f'ft_{tag}_amb']=c['AMBIGUOUS'];out[f'ft_{tag}_none']=c['NONE'];out[f'ft_{tag}_decisive_n']=dec;out[f'ft_{tag}_wr_pct']=100*c['FAVORABLE']/dec if dec else np.nan
    return out

def build(x):
    ns=x.index.asi8; O=x.open.to_numpy(float);H=x.high.to_numpy(float);L=x.low.to_numpy(float);C=x.close.to_numpy(float)
    local=x.index.tz_convert(WIB); hour_idx=np.flatnonzero(local.minute.to_numpy()==0)
    span_ns=int((DEV_END-DEV_START).value); start_ns=int(DEV_START.value)
    events=defaultdict(lambda:defaultdict(list))
    for i in hour_idx:
        ts_ns=int(ns[i]); wd=int(local[i].weekday()); hour=int(local[i].hour); entry=float(O[i])
        if entry<=0:continue
        block=min(BLOCKS-1,max(0,int((ts_ns-start_ns)*BLOCKS/span_ns)))
        for horizon in HORIZONS:
            hb=HBAR[horizon]; j=i+hb
            if j>len(x) or int(ns[j-1])!=ts_ns+(hb-1)*STEP_NS:continue
            hi=H[i:j];lo=L[i:j]
            events[(wd,hour)][horizon].append({'entry':entry,'ret':100*(C[j-1]-entry)/entry,'mx':float(hi.max()),'mn':float(lo.min()),'hi':hi.copy(),'lo':lo.copy(),'block':block})
    rows=[]
    for wd in range(7):
      for hour in range(24):
       for horizon in HORIZONS:
        ev=events[(wd,hour)][horizon]
        if len(ev)<MIN_N:continue
        ret=np.asarray([e['ret'] for e in ev]); direction=1 if int((ret>0).sum())>=int((ret<0).sum()) else -1
        rows.append({'weekday':WEEKDAYS[wd],'weekday_index_monday0':wd,'hour_wib':hour,'slot':f'{WEEKDAYS[wd]} {hour:02d}:00 WIB','direction':'BUY' if direction>0 else 'SELL','horizon_min':horizon,**metrics(ev,direction)})
    d=pd.DataFrame(rows)
    if len(d)!=840:raise AssertionError(f'expected 840 rows got {len(d)}')
    return d

def stable(df):
    return df.sort_values(['very_strong_blocks_ge65','strong_blocks_ge60','positive_blocks_gt50','median_block_wr_pct','wr_pct','mfe_mae_ratio'],ascending=[False]*6)

def f(x):return '-' if pd.isna(x) else f'{float(x):.2f}'

def main():
    if not (ROOT/f'{PFX}_Preregistration.md').exists():raise AssertionError('B27EZ prereg missing')
    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995:raise AssertionError(f'raw coverage {cov:.6%}')
    x15,cov15=make15(x5); d=build(x15); d.to_csv(OUT_DETAIL,index=False)
    raw=d.sort_values(['wr_pct','median_block_wr_pct','n','mfe_mae_ratio'],ascending=[False]*4).reset_index(drop=True);raw['raw_rank']=np.arange(1,len(raw)+1);raw.head(50).to_csv(OUT_RAW,index=False)
    best=[]
    for _,q in d.groupby(['weekday_index_monday0','hour_wib'],sort=False):best.append(stable(q).iloc[0])
    robust=stable(pd.DataFrame(best)).reset_index(drop=True);robust['robust_rank']=np.arange(1,len(robust)+1);robust.to_csv(OUT_SLOT,index=False);robust.head(50).to_csv(OUT_ROBUST,index=False)
    lines=['# BNB Temporal A1 — B27EZ Result','',f'Raw BNB 5m loader coverage: **{cov:.4%}**. Development 15m coverage: **{cov15:.4%}**.','',
    'Discovery only: **2022-01-01 → 2025-01-01 UTC**, timezone **WIB / UTC+7**. External/reference-validation/August were not used.','',
    'Method mirrors BTC Temporal A1: **168 weekday×hour slots**; each slot/horizon independently selects BUY or SELL; horizons **15/30/60/120/240m**; no common Micro-HL, TP, SL, K1/H2, EMA, or session filter.','',
    '## Raw directional-WR leaders','',
    '| Rank | Slot | Dir | H | N | WR | >50 | >=60 | >=65 | MFE | MAE | MFE/MAE | FT0.3 WR/N | FT0.5 WR/N | FT0.8 WR/N | FT1.0 WR/N |','|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in raw.head(15).iterrows():
        lines.append(f"| {int(r.raw_rank)} | {r.slot} | {r.direction} | {int(r.horizon_min)}m | {int(r.n)} | **{r.wr_pct:.2f}%** | {int(r.positive_blocks_gt50)}/8 | {int(r.strong_blocks_ge60)}/8 | {int(r.very_strong_blocks_ge65)}/8 | {r.median_mfe_pct:.3f}% | {r.median_mae_pct:.3f}% | {r.mfe_mae_ratio:.2f} | {f(r.ft_0p3_wr_pct)}/{int(r.ft_0p3_decisive_n)} | {f(r.ft_0p5_wr_pct)}/{int(r.ft_0p5_decisive_n)} | {f(r.ft_0p8_wr_pct)}/{int(r.ft_0p8_decisive_n)} | {f(r.ft_1p0_wr_pct)}/{int(r.ft_1p0_decisive_n)} |")
    lines+=['','## Stability-first leaders — one horizon per clock slot','',
    '| Rank | Slot | Dir | H | N | WR | >50 | >=60 | >=65 | Median block WR | Min block WR | MFE/MAE |','|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in robust.head(15).iterrows():lines.append(f"| {int(r.robust_rank)} | {r.slot} | {r.direction} | {int(r.horizon_min)}m | {int(r.n)} | **{r.wr_pct:.2f}%** | {int(r.positive_blocks_gt50)}/8 | {int(r.strong_blocks_ge60)}/8 | {int(r.very_strong_blocks_ge65)}/8 | {r.median_block_wr_pct:.2f}% | {r.min_block_wr_pct:.2f}% | {r.mfe_mae_ratio:.2f} |")
    a=raw.iloc[0];b=robust.iloc[0]
    lines+=['','## Discovery checkpoint','',f"Raw-WR leader: **{a.slot} {a.direction}, {int(a.horizon_min)}m**, N={int(a.n)}, WR **{a.wr_pct:.2f}%**, MFE/MAE **{a.mfe_mae_ratio:.2f}**.",f"Stability-first leader: **{b.slot} {b.direction}, {int(b.horizon_min)}m**, N={int(b.n)}, WR **{b.wr_pct:.2f}%**, blocks>50 **{int(b.positive_blocks_gt50)}/8**, blocks>=60 **{int(b.strong_blocks_ge60)}/8**.",'','These are **temporal priors, not trading setups**. First-touch is diagnostic geometry, not a promoted TP/SL.','', '**Status: B27EZ_BNB_TEMPORAL_A1_DEV_COMPLETE**','','STOP: no A2 entry sequence, no filter tuning, no holdout reveal, no live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8');OUT_STATUS.write_text('B27EZ_BNB_TEMPORAL_A1_DEV_COMPLETE\n',encoding='utf-8');print('\n'.join(lines))
if __name__=='__main__':main()
