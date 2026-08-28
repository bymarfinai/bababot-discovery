#!/usr/bin/env python3
from __future__ import annotations

import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em

TARGET = 'BNBUSDT'
DEV_START = pd.Timestamp('2022-01-01 00:00:00', tz='UTC')
DEV_END = pd.Timestamp('2025-01-01 00:00:00', tz='UTC')
WIB = ZoneInfo('Asia/Jakarta')
HORIZONS = (15, 30, 60, 120, 240)
HORIZON_BARS = {m: m // 15 for m in HORIZONS}
THRESHOLDS_PCT = (0.3, 0.5, 0.8, 1.0)
WEEKDAYS = ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')
BLOCKS = 8
MIN_N = 120
PFX = 'BNB_TEMPORAL_A1_B27EZ'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SLOT = ROOT / f'{PFX}_Slot_Bests.csv'
OUT_RAW = ROOT / f'{PFX}_Raw_WR_Leaderboard.csv'
OUT_ROBUST = ROOT / f'{PFX}_Robust_Leaderboard.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def med(xs):
    vals = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.median(vals)) if vals else np.nan


def mean(xs):
    vals = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.mean(vals)) if vals else np.nan


def first_touch(path: pd.DataFrame, entry: float, direction: int, threshold_pct: float) -> str:
    fav = entry * (1.0 + direction * threshold_pct / 100.0)
    adv = entry * (1.0 - direction * threshold_pct / 100.0)
    for _, r in path.iterrows():
        hi = float(r.high); lo = float(r.low)
        if direction > 0:
            hf = hi >= fav; ha = lo <= adv
        else:
            hf = lo <= fav; ha = hi >= adv
        if hf and ha:
            return 'AMBIGUOUS'
        if hf:
            return 'FAVORABLE'
        if ha:
            return 'ADVERSE'
    return 'NONE'


def make_15m(x5: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    q = x5[(x5.index >= DEV_START) & (x5.index < DEV_END)].copy()
    expected5 = int((DEV_END - DEV_START) / pd.Timedelta(minutes=5))
    cov5 = len(q) / expected5
    if cov5 < .995:
        raise AssertionError(f'development 5m coverage below gate: {cov5:.6%}')
    ohlc = q[['open','high','low','close']].resample('15min', label='left', closed='left').agg({
        'open':'first','high':'max','low':'min','close':'last'
    })
    cnt = q['close'].resample('15min', label='left', closed='left').count()
    x15 = ohlc[cnt == 3].dropna().copy()
    expected15 = int((DEV_END - DEV_START) / pd.Timedelta(minutes=15))
    cov15 = len(x15) / expected15
    if cov15 < .995:
        raise AssertionError(f'development 15m coverage below gate: {cov15:.6%}')
    return x15, cov15


def event_metrics(events: list[dict], direction: int) -> dict:
    signed = [direction * e['ret_pct'] for e in events]
    wins = sum(x > 0 for x in signed)
    losses = sum(x < 0 for x in signed)
    resolved = wins + losses
    mfe=[]; mae=[]
    for e in events:
        entry=e['entry']
        if direction > 0:
            mfe.append(100.0*(e['max_high']-entry)/entry)
            mae.append(100.0*(entry-e['min_low'])/entry)
        else:
            mfe.append(100.0*(entry-e['min_low'])/entry)
            mae.append(100.0*(e['max_high']-entry)/entry)
    block_wrs=[]
    pos=strong=very=0
    for b in range(BLOCKS):
        xs=[direction*e['ret_pct'] for e in events if e['block']==b]
        bw=sum(x>0 for x in xs); bl=sum(x<0 for x in xs); br=bw+bl
        wr=(bw/br) if br else np.nan
        if not pd.isna(wr):
            block_wrs.append(100*wr)
            pos += int(wr > .50)
            strong += int(wr >= .60)
            very += int(wr >= .65)
    ft={}
    for th in THRESHOLDS_PCT:
        c=defaultdict(int)
        for e in events:
            c[first_touch(e['path'],e['entry'],direction,th)] += 1
        decisive=c['FAVORABLE']+c['ADVERSE']
        ft[th]={
            'fav':c['FAVORABLE'],'adv':c['ADVERSE'],'amb':c['AMBIGUOUS'],'none':c['NONE'],
            'wr':100*c['FAVORABLE']/decisive if decisive else np.nan,
            'decisive':decisive,
        }
    med_mfe=med(mfe); med_mae=med(mae)
    out={
        'n':len(events),'resolved':resolved,'wins':wins,'losses':losses,
        'wr_pct':100*wins/resolved if resolved else np.nan,
        'avg_signed_return_pct':mean(signed),'median_signed_return_pct':med(signed),
        'median_mfe_pct':med_mfe,'median_mae_pct':med_mae,
        'mfe_mae_ratio':med_mfe/med_mae if med_mae and not pd.isna(med_mae) else np.nan,
        'positive_blocks_gt50':pos,'strong_blocks_ge60':strong,'very_strong_blocks_ge65':very,
        'median_block_wr_pct':med(block_wrs),'min_block_wr_pct':min(block_wrs) if block_wrs else np.nan,
    }
    for th,z in ft.items():
        tag=str(th).replace('.','p')
        out[f'ft_{tag}_fav']=z['fav']; out[f'ft_{tag}_adv']=z['adv']; out[f'ft_{tag}_amb']=z['amb']; out[f'ft_{tag}_none']=z['none']
        out[f'ft_{tag}_decisive_n']=z['decisive']; out[f'ft_{tag}_wr_pct']=z['wr']
    return out


def build(x15: pd.DataFrame) -> pd.DataFrame:
    by_ts={pd.Timestamp(ts):r for ts,r in x15.iterrows()}
    span=(DEV_END-DEV_START).total_seconds()
    events=defaultdict(lambda:defaultdict(list))
    for ts,r in x15.iterrows():
        ts=pd.Timestamp(ts)
        local=ts.tz_convert(WIB)
        if local.minute != 0:
            continue
        entry=float(r.open)
        if entry <= 0:
            continue
        slot=(local.weekday(),local.hour)
        block=min(BLOCKS-1,max(0,int((ts-DEV_START).total_seconds()*BLOCKS/span)))
        for horizon in HORIZONS:
            hb=HORIZON_BARS[horizon]
            idx=[ts+pd.Timedelta(minutes=15*k) for k in range(hb)]
            if any(t not in by_ts for t in idx):
                continue
            path=x15.loc[idx]
            final_close=float(path.iloc[-1].close)
            events[slot][horizon].append({
                'ts':ts,'block':block,'entry':entry,
                'ret_pct':100.0*(final_close-entry)/entry,
                'max_high':float(path.high.max()),'min_low':float(path.low.min()),'path':path,
            })
    rows=[]
    for wd in range(7):
        for hour in range(24):
            for horizon in HORIZONS:
                xs=events[(wd,hour)][horizon]
                if len(xs) < MIN_N:
                    continue
                up=sum(e['ret_pct']>0 for e in xs); down=sum(e['ret_pct']<0 for e in xs)
                direction=1 if up>=down else -1
                rows.append({
                    'weekday':WEEKDAYS[wd],'weekday_index_monday0':wd,'hour_wib':hour,
                    'slot':f'{WEEKDAYS[wd]} {hour:02d}:00 WIB','direction':'BUY' if direction>0 else 'SELL',
                    'horizon_min':horizon,**event_metrics(xs,direction)
                })
    d=pd.DataFrame(rows)
    if len(d) != 168*len(HORIZONS):
        raise AssertionError(f'expected 840 slot-horizon rows, got {len(d)}')
    return d


def stability_sort(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(
        ['very_strong_blocks_ge65','strong_blocks_ge60','positive_blocks_gt50','median_block_wr_pct','wr_pct','mfe_mae_ratio'],
        ascending=[False,False,False,False,False,False]
    )


def fmt(x,dec=2):
    return '-' if pd.isna(x) else f'{float(x):.{dec}f}'


def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EZ preregistration missing')
    x5,cov_all=b27em.data_base.load5(TARGET)
    if cov_all < .995:
        raise AssertionError(f'raw BNB coverage gate failed {cov_all:.6%}')
    x15,cov15=make_15m(x5)
    d=build(x15)
    d.to_csv(OUT_DETAIL,index=False)

    raw=d.sort_values(['wr_pct','median_block_wr_pct','n','mfe_mae_ratio'],ascending=[False,False,False,False]).reset_index(drop=True)
    raw['raw_rank']=np.arange(1,len(raw)+1)
    raw.head(50).to_csv(OUT_RAW,index=False)

    bests=[]
    for _,q in d.groupby(['weekday_index_monday0','hour_wib'],sort=False):
        bests.append(stability_sort(q).iloc[0])
    sb=pd.DataFrame(bests)
    robust=stability_sort(sb).reset_index(drop=True)
    robust['robust_rank']=np.arange(1,len(robust)+1)
    robust.to_csv(OUT_SLOT,index=False)
    robust.head(50).to_csv(OUT_ROBUST,index=False)

    top_raw=raw.head(15)
    top_rob=robust.head(15)
    lines=[
        '# BNB Temporal A1 — B27EZ Result','',
        f'Raw BNB 5m loader coverage: **{cov_all:.4%}**. Development-resampled 15m coverage: **{cov15:.4%}**.','',
        'Discovery only: **2022-01-01 → 2025-01-01 UTC**, slot timezone **WIB / UTC+7**. External/reference-validation/August were not used.','',
        'Method mirrors BTC Temporal A1: scan all **168 weekday×hour slots**, each slot/horizon independently selects BUY or SELL from forward-return sign; horizons **15/30/60/120/240m**; no common Micro-HL, TP, SL, K1/H2, EMA, or session filter.','',
        '## Raw directional-WR leaders','',
        '| Rank | Slot | Dir | Horizon | N | WR | Blocks>50 | Blocks>=60 | Blocks>=65 | Med MFE | Med MAE | MFE/MAE | FT0.3 WR/N | FT0.5 WR/N | FT0.8 WR/N | FT1.0 WR/N |',
        '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in top_raw.iterrows():
        lines.append(
            f"| {int(r.raw_rank)} | {r.slot} | {r.direction} | {int(r.horizon_min)}m | {int(r.n)} | **{r.wr_pct:.2f}%** | {int(r.positive_blocks_gt50)}/8 | {int(r.strong_blocks_ge60)}/8 | {int(r.very_strong_blocks_ge65)}/8 | {r.median_mfe_pct:.3f}% | {r.median_mae_pct:.3f}% | {r.mfe_mae_ratio:.2f} | {fmt(r.ft_0p3_wr_pct)}/{int(r.ft_0p3_decisive_n)} | {fmt(r.ft_0p5_wr_pct)}/{int(r.ft_0p5_decisive_n)} | {fmt(r.ft_0p8_wr_pct)}/{int(r.ft_0p8_decisive_n)} | {fmt(r.ft_1p0_wr_pct)}/{int(r.ft_1p0_decisive_n)} |"
        )
    lines += ['', '## Stability-first leaders — one horizon per clock slot','',
        '| Rank | Slot | Dir | Horizon | N | WR | Blocks>50 | >=60 | >=65 | Median block WR | Min block WR | MFE/MAE |',
        '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in top_rob.iterrows():
        lines.append(f"| {int(r.robust_rank)} | {r.slot} | {r.direction} | {int(r.horizon_min)}m | {int(r.n)} | **{r.wr_pct:.2f}%** | {int(r.positive_blocks_gt50)}/8 | {int(r.strong_blocks_ge60)}/8 | {int(r.very_strong_blocks_ge65)}/8 | {r.median_block_wr_pct:.2f}% | {r.min_block_wr_pct:.2f}% | {r.mfe_mae_ratio:.2f} |")

    leader=raw.iloc[0]
    robust_leader=robust.iloc[0]
    lines += ['', '## Discovery checkpoint','',
        f"Raw-WR leader: **{leader.slot} {leader.direction}, {int(leader.horizon_min)}m**, N={int(leader.n)}, directional WR **{leader.wr_pct:.2f}%**, median MFE/MAE **{leader.mfe_mae_ratio:.2f}**.",
        f"Stability-first leader: **{robust_leader.slot} {robust_leader.direction}, {int(robust_leader.horizon_min)}m**, N={int(robust_leader.n)}, WR **{robust_leader.wr_pct:.2f}%**, blocks >50 **{int(robust_leader.positive_blocks_gt50)}/8**, blocks >=60 **{int(robust_leader.strong_blocks_ge60)}/8**.",
        '',
        'These are **temporal priors, not trading setups**. First-touch rows are execution geometry diagnostics, not a promoted TP/SL. B27EZ intentionally stops before any A2 price-path/entry refinement.','',
        '**Status: B27EZ_BNB_TEMPORAL_A1_DEV_COMPLETE**','',
        'STOP: no A2 entry sequence, no filter tuning, no holdout reveal, no live integration.'
    ]
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    OUT_STATUS.write_text('B27EZ_BNB_TEMPORAL_A1_DEV_COMPLETE\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
