#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_5M_MOVE_SCALE_B22A_Result.md'
OUT_JSON=ROOT/'BTC_5M_MOVE_SCALE_B22A_Result.json'
OUT_CSV=ROOT/'BTC_5M_MOVE_SCALE_B22A_Thresholds.csv'
THRESHOLDS=[.0010,.0015,.0020,.0025,.0030,.0040,.0050]
HORIZONS=[1,3,6,12]  # 5m,15m,30m,60m


def first_touch(q,entry,thr):
    tp=entry*(1+thr); sl=entry*(1-thr)
    for _,r in q.iterrows():
        hit_tp=float(r.high)>=tp; hit_sl=float(r.low)<=sl
        if hit_tp and hit_sl:return 'SL_TIE'
        if hit_sl:return 'SL'
        if hit_tp:return 'TP'
    return 'NONE'


def summarize_seed(x5,states,seeds,cohort):
    rows=[]
    for bars in HORIZONS:
        mfes=[]; maes=[]; touches={t:[] for t in THRESHOLDS}
        for t in seeds:
            if t not in x5.index:continue
            loc=x5.index.get_loc(t)
            if not isinstance(loc,(int,np.integer)) or loc+bars>len(x5):continue
            q=x5.iloc[loc:loc+bars]
            entry=float(q.iloc[0].open)
            mfes.append(float(q.high.max())/entry-1)
            maes.append(float(q.low.min())/entry-1)
            for thr in THRESHOLDS:touches[thr].append(first_touch(q,entry,thr))
        for thr in THRESHOLDS:
            a=touches[thr]; n=len(a); tp=sum(v=='TP' for v in a); sl=sum(v in ('SL','SL_TIE') for v in a)
            rows.append({'cohort':cohort,'horizon_min':bars*5,'threshold_pct':thr*100,'n':n,
                         'tp_hit_rate':sum(v=='TP' for v in a)/n if n else None,
                         'up_touch_rate':sum(v in ('TP',) for v in a)/n if n else None,
                         'down_touch_rate':sl/n if n else None,
                         'symmetric_first_touch_wr':tp/(tp+sl) if tp+sl else None,
                         'median_mfe_pct':np.median(mfes)*100 if mfes else None,
                         'p75_mfe_pct':np.quantile(mfes,.75)*100 if mfes else None,
                         'median_mae_pct':np.median(maes)*100 if maes else None})
    return rows


def main():
    x5,cov=b21.load5(); states=b21.build_state_table(x5)
    # Descriptive 5m scale on analysis window.
    xa=x5[(x5.index>=b21.ANALYSIS_START)&(x5.index<b21.END)].copy()
    prev=xa.close.shift(1)
    tr=pd.concat([(xa.high-xa.low),(xa.high-prev).abs(),(xa.low-prev).abs()],axis=1).max(axis=1)
    atr14=tr.rolling(14,min_periods=14).mean()/xa.close
    candle_range=(xa.high-xa.low)/xa.open
    seed_mask=states.m5_bull & ~states.m5_bull.shift(1,fill_value=False)
    all_seeds=states.index[seed_mask]
    h4_seeds=states.index[seed_mask & states.h4_bull]
    h4h1_seeds=states.index[seed_mask & states.h4_bull & states.h1_bull]
    rows=[]
    rows+=summarize_seed(x5,states,all_seeds,'ALL_5M_BULL_ON')
    rows+=summarize_seed(x5,states,h4_seeds,'5M_ON_WHILE_4H_BULL')
    rows+=summarize_seed(x5,states,h4h1_seeds,'5M_ON_WHILE_1H_4H_BULL')
    df=pd.DataFrame(rows);df.to_csv(OUT_CSV,index=False)
    scale={'data_rows':len(xa),'coverage':cov,
           'median_5m_range_pct':float(candle_range.median()*100),
           'p75_5m_range_pct':float(candle_range.quantile(.75)*100),
           'p90_5m_range_pct':float(candle_range.quantile(.90)*100),
           'median_atr14_5m_pct':float(atr14.median()*100),
           'p75_atr14_5m_pct':float(atr14.quantile(.75)*100),
           'seed_counts':{'all':len(all_seeds),'h4':len(h4_seeds),'h1_h4':len(h4h1_seeds)}}
    OUT_JSON.write_text(json.dumps({'scale':scale,'rows':rows},indent=2)+'\n')
    md=['# BTC 5m Move Scale B22A — Descriptive Result','',
        f"Data rows: **{len(xa):,}**; coverage **{cov:.4%}**",'',
        '## Native 5m movement scale','',
        f"- Median 5m high-low range: **{scale['median_5m_range_pct']:.3f}%**",
        f"- P75 5m high-low range: **{scale['p75_5m_range_pct']:.3f}%**",
        f"- P90 5m high-low range: **{scale['p90_5m_range_pct']:.3f}%**",
        f"- Median 14-bar ATR on 5m: **{scale['median_atr14_5m_pct']:.3f}%**",
        f"- P75 14-bar ATR on 5m: **{scale['p75_atr14_5m_pct']:.3f}%**",'',
        '## Bull-trigger target reach','',
        '| Cohort | Horizon | Target | N | TP-first | SL/tie-first | Sym first-touch WR | Median MFE | P75 MFE |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['threshold_pct'] not in (0.15,0.20,0.25,0.30,0.40,0.50):continue
        f=lambda v:'-' if v is None else f'{100*v:.1f}%'
        md.append(f"| {r['cohort']} | {r['horizon_min']}m | {r['threshold_pct']:.2f}% | {r['n']} | {f(r['tp_hit_rate'])} | {f(r['down_touch_rate'])} | {f(r['symmetric_first_touch_wr'])} | {r['median_mfe_pct']:.3f}% | {r['p75_mfe_pct']:.3f}% |")
    md+=['','This is a descriptive scale/feasibility check, not a promoted trading rule. It uses causal completed-bar B21 states at entry.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps({'scale':scale},indent=2))

if __name__=='__main__':main()
