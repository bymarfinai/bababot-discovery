#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
ZTR = ROOT / 'ETH_LONG_F75_EXTENSION_ECON_B27Z_ADAPT_Trades.csv'
AATR = ROOT / 'ETH_LONG_F75_EARLY_RECLAIM_B27AA_ADAPT_Trades.csv'
WINDOWS = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Windows.csv'
PFX = 'ETH_LONG_F75_DYNAMIC_RUNNER_B27AB_ADAPT'
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
FLOOR_F = 0.15


def fast_slice(x, start, end):
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum()); neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_loss_streak(vals):
    best = cur = 0
    for v in vals:
        if float(v) <= 0: cur += 1; best = max(best, cur)
        else: cur = 0
    return best


def load_windows():
    w = pd.read_csv(WINDOWS)[['partition','date_utc','signal_ts','session_end']].copy()
    w['signal_ts'] = pd.to_datetime(w.signal_ts, utc=True)
    w['session_end'] = pd.to_datetime(w.session_end, utc=True)
    return w


def load_cohorts():
    w = load_windows()
    z = pd.read_csv(ZTR)
    for c in ('signal_ts','entry_ts','h2_bar_start','exit_ts'):
        z[c] = pd.to_datetime(z[c], utc=True, errors='coerce')
    z = z[(z.target_name == 'E10') & (z.boundary_name == 'D60')].copy()
    if z.duplicated(['partition','date_utc','signal_ts']).any():
        raise AssertionError('B27Z blind identity duplicate')
    z = z.merge(w, on=['partition','date_utc','signal_ts'], how='left', validate='one_to_one')
    blind = pd.DataFrame({
        'partition':z.partition,'date_utc':z.date_utc,'signal_ts':z.signal_ts,
        'cohort':'BLIND_F75','entry_ts':z.entry_ts,'entry_px':z.entry_px,
        'H':z.H,'L':z.L,'range':z['range'],'h2_bar_start':z.h2_bar_start,
        'session_end':z.session_end,'fixed_exit_ts':z.exit_ts,'fixed_exit_px':z.exit_px,
        'fixed_exit_reason':z.exit_reason,'fixed_net_pnl_usd':z.net_pnl_usd,
    })

    a = pd.read_csv(AATR)
    for c in ('signal_ts','entry_ts','frozen_h2_bar_start','exit_ts'):
        a[c] = pd.to_datetime(a[c], utc=True, errors='coerce')
    a = a[a.entry_executed.astype(str).str.lower() == 'true'].copy()
    a = a.merge(w, on=['partition','date_utc','signal_ts'], how='left', validate='many_to_one')
    aa_rows=[]
    for variant,cohort in [('EARLY_RECLAIM','EARLY_RECLAIM'),('SAME_BAR_REJECTION','SAME_BAR_REJECTION')]:
        g=a[a.variant==variant].copy()
        if g.duplicated(['partition','date_utc','signal_ts']).any():
            raise AssertionError(f'{variant} identity duplicate')
        aa_rows.append(pd.DataFrame({
            'partition':g.partition,'date_utc':g.date_utc,'signal_ts':g.signal_ts,
            'cohort':cohort,'entry_ts':g.entry_ts,'entry_px':g.entry_px,
            'H':g.H,'L':g.L,'range':g['range'],'h2_bar_start':g.frozen_h2_bar_start,
            'session_end':g.session_end,'fixed_exit_ts':g.exit_ts,'fixed_exit_px':g.exit_px,
            'fixed_exit_reason':g.exit_reason,'fixed_net_pnl_usd':g.net_pnl_usd,
        }))
    out=pd.concat([blind,*aa_rows],ignore_index=True)
    if out.session_end.isna().any(): raise AssertionError('missing session_end')
    return out.sort_values(['cohort','partition','entry_ts']).reset_index(drop=True)


def runner_exit(x5, r):
    entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end)
    entry=float(r.entry_px); H=float(r.H); L=float(r.L); R=float(r.range)
    floor=L+FLOOR_F*R
    if not (L < floor < H and entry < H): raise AssertionError('runner geometry')
    q=fast_slice(x5,entry_ts,end)
    if q.empty or q.index[0] != entry_ts: raise AssertionError('missing runner entry bar')

    active=False
    trail=floor
    activation_bar=pd.NaT
    activation_ts=pd.NaT
    pivots=[]
    trail_updates=0
    reason=None; exit_ts=pd.NaT; exit_px=np.nan

    lows=q.low.astype(float).to_numpy()
    idx=q.index
    for k,(ts,bar) in enumerate(q.iterrows()):
        ts=pd.Timestamp(ts); cl=float(bar.close)

        # Pivot centered at k-1 becomes known only at this completed close.
        newly_confirmed=None
        if k >= 2 and lows[k-1] < lows[k-2] and lows[k-1] < lows[k]:
            newly_confirmed=float(lows[k-1])
            pivots.append((ts+BAR5,newly_confirmed))

        if not active:
            # Pre-breakout protection remains active through this completed close.
            if cl < floor:
                reason='PRE_BREAKOUT_CLOSE_INVALIDATION_F15'; exit_ts=ts+BAR5; exit_px=cl; break
            if cl > H:
                active=True; activation_bar=ts; activation_ts=ts+BAR5
                known=[p for _,p in pivots if p > trail]
                if known:
                    trail=max(trail,max(known)); trail_updates += 1
                # Activation close cannot be retroactively stopped by trail known at same close.
                continue
            continue

        # Runner was already active before this bar. Test old trail first.
        if cl < trail:
            reason='RUNNER_CLOSE_BELOW_TRAIL'; exit_ts=ts+BAR5; exit_px=cl; break
        # Only after surviving this close may the newly confirmed pivot ratchet for future bars.
        if newly_confirmed is not None and newly_confirmed > trail:
            trail=float(newly_confirmed); trail_updates += 1

    if reason is None:
        p=int(x5.index.searchsorted(end,side='left'))
        if p>=len(x5) or x5.index[p] != end: raise AssertionError('missing session-end bar')
        exit_ts=end; exit_px=float(x5.iloc[p].open)
        reason='RUNNER_TIME_EXIT' if active else 'PRE_BREAKOUT_TIME_EXIT'

    gross=float(exit_px/entry-1.0); net=gross*NOTIONAL-FEE
    return {
        'runner_exit_ts':exit_ts,'runner_exit_px':float(exit_px),'runner_exit_reason':reason,
        'runner_net_pnl_usd':net,'runner_activated':bool(active),'activation_bar_start':activation_bar,
        'activation_ts':activation_ts,'final_trail':float(trail),'trail_updates':int(trail_updates),
        'runner_hold_minutes':float((pd.Timestamp(exit_ts)-entry_ts)/pd.Timedelta(minutes=1)),
    }


def metrics(g, col):
    x=pd.to_numeric(g[col],errors='coerce').dropna()
    if not len(x): return {'n':0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'net':0.0,'max_ls':0}
    return {'n':int(len(x)),'wr':float((x>0).mean()),'pf':float(pf(x)),'exp':float(x.mean()),'net':float(x.sum()),'max_ls':max_loss_streak(x.tolist())}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.2f}'


def synthetic_tests():
    # Activation then causal pivot trail; activation bar cannot self-stop.
    idx=pd.date_range('2026-01-05 14:00',periods=7,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':97.5,'high':99,'low':97,'close':98.0},
        {'open':98,'high':101,'low':97.8,'close':100.4},  # acceptance
        {'open':100.4,'high':101,'low':99.5,'close':100.5},
        {'open':100.5,'high':101,'low':99.0,'close':100.2},
        {'open':100.2,'high':101,'low':99.7,'close':100.4}, # confirms pivot low=99 at close
        {'open':100.4,'high':100.8,'low':98.8,'close':98.9}, # exits below active 99 trail
        {'open':98.9,'high':99,'low':98,'close':98.5},
    ],index=idx)
    class R: pass
    r=R(); r.entry_ts=idx[0]; r.session_end=idx[-1]+BAR5; r.entry_px=97.5; r.H=100.; r.L=90.; r.range=10.
    z=runner_exit(x,r)
    assert z['runner_activated'] and z['runner_exit_reason']=='RUNNER_CLOSE_BELOW_TRAIL'
    assert abs(z['final_trail']-99.0)<1e-12 and z['runner_exit_ts']==idx[5]+BAR5


def main():
    synthetic_tests()
    x5,coverage=ethdata.load5(); src=load_cohorts()
    rows=[]
    for r in src.itertuples(index=False):
        rr=runner_exit(x5,r)
        rows.append({**r._asdict(),**rr})
    d=pd.DataFrame(rows).sort_values(['cohort','partition','entry_ts']).reset_index(drop=True)
    d.to_csv(OUT_TRADES,index=False)

    sums=[]
    for cohort in COHORTS:
        for part in PARTS:
            g=d[(d.cohort==cohort)&(d.partition==part)].sort_values('entry_ts')
            fm=metrics(g,'fixed_net_pnl_usd'); rm=metrics(g,'runner_net_pnl_usd')
            sums.append({'cohort':cohort,'partition':part,'n':rm['n'],
                         'fixed_wr':fm['wr'],'fixed_pf':fm['pf'],'fixed_exp':fm['exp'],'fixed_net':fm['net'],
                         'runner_wr':rm['wr'],'runner_pf':rm['pf'],'runner_exp':rm['exp'],'runner_net':rm['net'],
                         'delta_exp':rm['exp']-fm['exp'] if rm['n'] else np.nan,'delta_net':rm['net']-fm['net'],
                         'activation_rate':float(g.runner_activated.mean()) if len(g) else np.nan,
                         'runner_max_ls':rm['max_ls']})
    sm=pd.DataFrame(sums); sm.to_csv(OUT_SUM,index=False)

    pr=sm[(sm.cohort=='EARLY_RECLAIM') & sm.partition.isin(MAJOR)]
    pooled=d[(d.cohort=='EARLY_RECLAIM') & d.partition.isin(MAJOR)].sort_values('entry_ts')
    pfixed=metrics(pooled,'fixed_net_pnl_usd'); prun=metrics(pooled,'runner_net_pnl_usd')
    passed=bool(len(pr)==3 and (pr.runner_exp>pr.fixed_exp).all() and (pr.runner_pf>=1.0).all() and prun['net']>pfixed['net'])
    status='ETH_LONG_B27AB_ADAPT_PRIMARY_RUNNER_SUPPORTED' if passed else 'ETH_LONG_B27AB_ADAPT_PRIMARY_RUNNER_NOT_SUPPORTED'
    OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG B27AB-Adapt — Post-Breakout Dynamic Runner — Result','',
        f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        'Frozen cohorts are reused from B27W/B27Z/B27AA. Runner uses F15 pre-breakout close invalidation, first completed close > H activation, and one strict causal 3-bar pivot-low trail definition.','',
        '| Cohort | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Runner WR | Runner PF | Runner exp | Runner net | Δexp | Activation | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.cohort} | {r.partition} | {r.n} | {pct(r.fixed_wr)} | {num(r.fixed_pf)} | ${num(r.fixed_exp)} | ${num(r.fixed_net)} | {pct(r.runner_wr)} | {num(r.runner_pf)} | ${num(r.runner_exp)} | ${num(r.runner_net)} | ${num(r.delta_exp)} | {pct(r.activation_rate)} | {r.runner_max_ls} |')
    md += ['','## Primary EARLY_RECLAIM pooled-major comparison','',
           f'- Fixed baseline: N={pfixed["n"]}, WR={pct(pfixed["wr"])}, PF={num(pfixed["pf"])}, exp=${num(pfixed["exp"])}, net=${num(pfixed["net"])}.',
           f'- Dynamic runner: N={prun["n"]}, WR={pct(prun["wr"])}, PF={num(prun["pf"])}, exp=${num(prun["exp"])}, net=${num(prun["net"])}.',
           '',f'**Status: {status}**','', 'Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
