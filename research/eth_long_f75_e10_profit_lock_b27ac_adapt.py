#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata
import eth_long_f75_dynamic_runner_b27ab_adapt as ab

ROOT = Path(__file__).resolve().parent.parent
PFX = 'ETH_LONG_F75_E10_PROFIT_LOCK_B27AC_ADAPT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
COHORTS = ('BLIND_F75','EARLY_RECLAIM','SAME_BAR_REJECTION')
NOTIONAL = 500.0
FEE = 0.40
PRE_FLOOR_F = 0.15
MILESTONE_EXT = 0.10


def fast_slice(x, start, end):
    a=int(x.index.searchsorted(start,side='left')); b=int(x.index.searchsorted(end,side='left'))
    return x.iloc[a:b]


def hybrid_exit(x5, r):
    entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end)
    entry=float(r.entry_px); H=float(r.H); L=float(r.L); R=float(r.range)
    pre_floor=L+PRE_FLOOR_F*R; e10=H+MILESTONE_EXT*R
    q=fast_slice(x5,entry_ts,end)
    if q.empty or q.index[0] != entry_ts: raise AssertionError('missing hybrid entry bar')
    lows=q.low.astype(float).to_numpy()

    activated=False; active_floor=np.nan; activation_bar=pd.NaT; activation_ts=pd.NaT
    floor_updates=0; reason=None; exit_ts=pd.NaT; exit_px=np.nan

    for k,(ts,bar) in enumerate(q.iterrows()):
        ts=pd.Timestamp(ts); op=float(bar.open); hi=float(bar.high); lo=float(bar.low); cl=float(bar.close)
        newly_confirmed=None
        if k>=2 and lows[k-1] < lows[k-2] and lows[k-1] < lows[k]:
            newly_confirmed=float(lows[k-1])

        if not activated:
            # Close invalidation is known only at completion; it still wins on the E10-touch bar.
            if cl < pre_floor:
                reason='PRE_E10_CLOSE_INVALIDATION_F15'; exit_ts=ts+BAR5; exit_px=cl; break
            if hi >= e10:
                activated=True; activation_bar=ts; activation_ts=ts+BAR5
                active_floor=e10
                if newly_confirmed is not None and newly_confirmed > active_floor:
                    active_floor=newly_confirmed; floor_updates += 1
                # Floor only becomes effective from next bar.
                continue
            continue

        # Existing floor is resting before this bar starts.
        if op <= active_floor:
            reason='ACTIVE_FLOOR_GAP_OPEN'; exit_ts=ts; exit_px=op; break
        if lo <= active_floor:
            reason='ACTIVE_FLOOR_TOUCH'; exit_ts=ts+BAR5; exit_px=float(active_floor); break

        # A pivot confirmed by this bar close can only affect future bars.
        if newly_confirmed is not None and newly_confirmed > active_floor:
            active_floor=newly_confirmed; floor_updates += 1

    if reason is None:
        p=int(x5.index.searchsorted(end,side='left'))
        if p>=len(x5) or x5.index[p] != end: raise AssertionError('missing session end')
        exit_ts=end; exit_px=float(x5.iloc[p].open)
        reason='HYBRID_TIME_EXIT' if activated else 'PRE_E10_TIME_EXIT'

    net=(float(exit_px)/entry-1.0)*NOTIONAL-FEE
    ext=(float(exit_px)-H)/R
    return {'hybrid_exit_ts':exit_ts,'hybrid_exit_px':float(exit_px),'hybrid_exit_reason':reason,
            'hybrid_net_pnl_usd':float(net),'e10_reached':bool(activated),
            'e10_activation_bar_start':activation_bar,'e10_activation_ts':activation_ts,
            'final_floor':float(active_floor) if not pd.isna(active_floor) else np.nan,
            'final_floor_extension':(float(active_floor)-H)/R if not pd.isna(active_floor) else np.nan,
            'floor_updates':int(floor_updates),'realized_exit_extension':float(ext),
            'hybrid_hold_minutes':float((pd.Timestamp(exit_ts)-entry_ts)/pd.Timedelta(minutes=1))}


def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg==0 and pos>0:return float('inf')
    return pos/neg if neg>0 else np.nan


def max_ls(vals):
    b=c=0
    for v in vals:
        if float(v)<=0:c+=1;b=max(b,c)
        else:c=0
    return b


def metrics(g,col):
    x=pd.to_numeric(g[col],errors='coerce').dropna()
    if not len(x):return {'n':0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'net':0.0,'ls':0}
    return {'n':len(x),'wr':float((x>0).mean()),'pf':float(pf(x)),'exp':float(x.mean()),'net':float(x.sum()),'ls':max_ls(x.tolist())}

def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.2f}'


def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=7,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':97.5,'high':99,'low':97,'close':98.0},
        {'open':98,'high':101.2,'low':97.8,'close':100.5}, # E10=101 touched, floor activates next bar
        {'open':100.5,'high':102,'low':100.2,'close':101.5},
        {'open':101.5,'high':103,'low':101.2,'close':102.4},
        {'open':102.4,'high':103,'low':101.8,'close':102.0},
        {'open':102.0,'high':102.2,'low':100.8,'close':101.0},
        {'open':101.0,'high':101.1,'low':100.9,'close':101.0},
    ],index=idx)
    class R:pass
    r=R();r.entry_ts=idx[0];r.session_end=idx[-1]+BAR5;r.entry_px=97.5;r.H=100.;r.L=90.;r.range=10.
    z=hybrid_exit(x,r)
    assert z['e10_reached'] and z['hybrid_exit_px']>=101.0


def main():
    synthetic_tests(); x5,coverage=ethdata.load5(); src=ab.load_cohorts(); rows=[]
    for r in src.itertuples(index=False): rows.append({**r._asdict(),**hybrid_exit(x5,r)})
    d=pd.DataFrame(rows).sort_values(['cohort','partition','entry_ts']).reset_index(drop=True); d.to_csv(OUT_TRADES,index=False)

    sums=[]
    for cohort in COHORTS:
        for part in PARTS:
            g=d[(d.cohort==cohort)&(d.partition==part)].sort_values('entry_ts')
            fm=metrics(g,'fixed_net_pnl_usd'); hm=metrics(g,'hybrid_net_pnl_usd')
            sums.append({'cohort':cohort,'partition':part,'n':hm['n'],'fixed_wr':fm['wr'],'fixed_pf':fm['pf'],'fixed_exp':fm['exp'],'fixed_net':fm['net'],
                         'hybrid_wr':hm['wr'],'hybrid_pf':hm['pf'],'hybrid_exp':hm['exp'],'hybrid_net':hm['net'],
                         'delta_exp':hm['exp']-fm['exp'] if hm['n'] else np.nan,'delta_net':hm['net']-fm['net'],
                         'e10_reach_rate':float(g.e10_reached.mean()) if len(g) else np.nan,
                         'floor_exit_rate':float(g.hybrid_exit_reason.isin(['ACTIVE_FLOOR_GAP_OPEN','ACTIVE_FLOOR_TOUCH']).mean()) if len(g) else np.nan,
                         'hybrid_max_ls':hm['ls']})
    sm=pd.DataFrame(sums);sm.to_csv(OUT_SUM,index=False)

    pr=sm[(sm.cohort=='EARLY_RECLAIM')&sm.partition.isin(MAJOR)]
    pooled=d[(d.cohort=='EARLY_RECLAIM')&d.partition.isin(MAJOR)].sort_values('entry_ts')
    fm=metrics(pooled,'fixed_net_pnl_usd'); hm=metrics(pooled,'hybrid_net_pnl_usd')
    passed=bool(len(pr)==3 and (pr.hybrid_exp>pr.fixed_exp).all() and (pr.hybrid_pf>=1.0).all() and hm['net']>fm['net'])
    status='ETH_LONG_B27AC_ADAPT_PRIMARY_HYBRID_SUPPORTED' if passed else 'ETH_LONG_B27AC_ADAPT_PRIMARY_HYBRID_NOT_SUPPORTED';OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG B27AC-Adapt — E10 Profit-Lock Runner — Result','',f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        'Frozen F75 cohorts and E10+D60/F15 baseline are reused. E10 becomes a hard floor only from the bar after first reach; strict causal 3-bar pivot lows may ratchet it upward.','',
        '| Cohort | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid net | Δexp | E10 reach | Floor exit | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.cohort} | {r.partition} | {r.n} | {pct(r.fixed_wr)} | {num(r.fixed_pf)} | ${num(r.fixed_exp)} | ${num(r.fixed_net)} | {pct(r.hybrid_wr)} | {num(r.hybrid_pf)} | ${num(r.hybrid_exp)} | ${num(r.hybrid_net)} | ${num(r.delta_exp)} | {pct(r.e10_reach_rate)} | {pct(r.floor_exit_rate)} | {r.hybrid_max_ls} |')
    md += ['','## Primary EARLY_RECLAIM pooled major','',f'- Fixed: N={fm["n"]}, WR={pct(fm["wr"])}, PF={num(fm["pf"])}, exp=${num(fm["exp"])}, net=${num(fm["net"])}.',
           f'- Hybrid: N={hm["n"]}, WR={pct(hm["wr"])}, PF={num(hm["pf"])}, exp=${num(hm["exp"])}, net=${num(hm["net"])}.',
           '',f'**Status: {status}**','', 'Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')
if __name__=='__main__':main()
