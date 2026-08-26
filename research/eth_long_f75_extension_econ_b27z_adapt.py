#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Entries.csv'
WINDOWS = ROOT / 'ETH_LONG_PRE_SECOND_TOUCH_ENTRY_B27W_ADAPT_Windows.csv'
PFX = 'ETH_LONG_F75_EXTENSION_ECON_B27Z_ADAPT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
ENTRY_FRAC = 0.75
TARGETS = {'E05':0.05,'E10':0.10,'E15':0.15}
BOUNDS = {'D30':0.45,'D40':0.35,'D50':0.25,'D60':0.15}
NOTIONAL = 500.0
FEE = 0.40


def fast_slice(x, start, end):
    a=int(x.index.searchsorted(start,side='left')); b=int(x.index.searchsorted(end,side='left'))
    return x.iloc[a:b]


def load_f75():
    e=pd.read_csv(ENTRIES); w=pd.read_csv(WINDOWS)
    for c in ('signal_ts','entry_ts','h2_bar_start','terminal_bar_start'):
        if c in e.columns: e[c]=pd.to_datetime(e[c],utc=True,errors='coerce')
    for c in ('signal_ts','session_end'):
        w[c]=pd.to_datetime(w[c],utc=True,errors='coerce')
    e=e[(e.entry_name=='F75') & (e.filled.astype(str).str.lower()=='true')].copy()
    e=e.merge(w[['partition','date_utc','signal_ts','session_end']],on=['partition','date_utc','signal_ts'],how='left',validate='many_to_one')
    if e.session_end.isna().any(): raise AssertionError('missing session_end')
    expected=e.L.astype(float)+ENTRY_FRAC*e['range'].astype(float)
    if not np.allclose(expected,e.planned_entry_px.astype(float),rtol=1e-10,atol=1e-10):
        raise AssertionError('F75 identity mismatch')
    return e.sort_values(['partition','entry_ts']).reset_index(drop=True)


def solve_trade(x5, r, target_name, target_ext, bound_name, bound_frac):
    entry_ts=pd.Timestamp(r.entry_ts); end=pd.Timestamp(r.session_end)
    H=float(r.H); L=float(r.L); R=float(r.range); entry=float(r.planned_entry_px)
    target=H+target_ext*R; boundary=L+bound_frac*R
    if not abs(entry-(L+ENTRY_FRAC*R)) < 1e-9*max(1.0,abs(entry)):
        raise AssertionError('entry geometry')
    q=fast_slice(x5,entry_ts,end)
    if q.empty or q.index[0] != entry_ts: raise AssertionError('missing entry bar')
    exit_ts=pd.NaT; exit_px=np.nan; reason=None
    h2_before=False; close_break_before=False
    h2=pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT

    for k,(ts,bar) in enumerate(q.iterrows()):
        ts=pd.Timestamp(ts); hi=float(bar.high); cl=float(bar.close)
        if pd.notna(h2) and h2 <= ts: h2_before=True
        if cl > H: close_break_before=True
        # On entry bar, target cannot be credited because intrabar order vs exact fill is unknown.
        # Completed close invalidation can be observed after the fill.
        if k==0:
            if cl < boundary:
                exit_ts=ts+BAR5; exit_px=cl; reason='CLOSE_INVALIDATION_ENTRY_BAR'
                break
            continue
        # Later-bar intrabar target is known before bar-close invalidation.
        if hi >= target:
            exit_ts=ts; exit_px=target; reason=f'TP_{target_name}'
            break
        if cl < boundary:
            exit_ts=ts+BAR5; exit_px=cl; reason=f'CLOSE_INVALIDATION_{bound_name}'
            break
    if reason is None:
        pos=int(x5.index.searchsorted(end,side='left'))
        if pos>=len(x5) or x5.index[pos] != end: raise AssertionError('missing session-end bar')
        exit_ts=end; exit_px=float(x5.iloc[pos].open); reason='TIME_EXIT_SESSION_END'
    gross=float(exit_px/entry-1.0); net=gross*NOTIONAL-FEE
    return {'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,
            'entry_ts':entry_ts,'entry_px':entry,'H':H,'L':L,'range':R,'h2_bar_start':h2,
            'target_name':target_name,'target_ext':target_ext,'target_px':target,
            'boundary_name':bound_name,'boundary_frac':bound_frac,'boundary_px':boundary,
            'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'gross_return':gross,
            'net_pnl_usd':net,'win':bool(net>0),'hold_minutes':float((exit_ts-entry_ts)/pd.Timedelta(minutes=1)),
            'h2_before_exit':bool(pd.notna(h2) and h2 <= exit_ts),
            'close_break_above_H_before_exit':bool(close_break_before)}


def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg==0 and pos>0: return float('inf')
    return pos/neg if neg>0 else np.nan


def max_loss_streak(vals):
    best=cur=0
    for v in vals:
        if v<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return best


def metrics(g):
    if len(g)==0: return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0,'tp_rate':np.nan,'inv_rate':np.nan,'time_rate':np.nan,'med_win':np.nan,'med_loss':np.nan,'med_hold':np.nan,'h2_rate':np.nan,'close_break_rate':np.nan,'max_loss_streak':0}
    net=g.net_pnl_usd.astype(float); wins=net[net>0]; losses=net[net<=0]
    return {'n':int(len(g)),'wins':int((net>0).sum()),'wr':float((net>0).mean()),'pf':float(pf(net)),
            'expectancy':float(net.mean()),'net':float(net.sum()),'tp_rate':float(g.exit_reason.str.startswith('TP_').mean()),
            'inv_rate':float(g.exit_reason.str.startswith('CLOSE_INVALIDATION').mean()),'time_rate':float((g.exit_reason=='TIME_EXIT_SESSION_END').mean()),
            'med_win':float(wins.median()) if len(wins) else np.nan,'med_loss':float(losses.median()) if len(losses) else np.nan,
            'med_hold':float(g.hold_minutes.median()),'h2_rate':float(g.h2_before_exit.mean()),'close_break_rate':float(g.close_break_above_H_before_exit.mean()),
            'max_loss_streak':max_loss_streak(net.tolist())}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=5,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':97.5,'high':98.0,'low':96.0,'close':97.0},
        {'open':97.0,'high':100.2,'low':96.5,'close':99.8},
        {'open':99.8,'high':101.0,'low':99.0,'close':100.6},
        {'open':100.6,'high':102,'low':100,'close':101.5},
        {'open':101.5,'high':102,'low':101,'close':101.2},
    ],index=idx)
    class R: pass
    r=R(); r.entry_ts=idx[0]; r.session_end=idx[-1]+BAR5; r.H=100.; r.L=90.; r.range=10.; r.planned_entry_px=97.5
    r.h2_bar_start=idx[1]; r.partition='x'; r.date_utc='2026-01-05'; r.signal_ts=idx[0]-BAR5
    z=solve_trade(x,r,'E05',.05,'D40',.35)
    assert z['exit_reason']=='TP_E05' and abs(z['exit_px']-100.5)<1e-12


def main():
    synthetic_tests(); x5,coverage=ethdata.load5(); src=load_f75(); rows=[]
    for r in src.itertuples(index=False):
        for tn,te in TARGETS.items():
            for bn,bf in BOUNDS.items(): rows.append(solve_trade(x5,r,tn,te,bn,bf))
    d=pd.DataFrame(rows); d.to_csv(OUT_TRADES,index=False)
    sums=[]
    for part in PARTS:
        for tn in TARGETS:
            for bn in BOUNDS:
                g=d[(d.partition==part)&(d.target_name==tn)&(d.boundary_name==bn)].sort_values('entry_ts')
                sums.append({'partition':part,'target':tn,'boundary':bn,**metrics(g)})
    sm=pd.DataFrame(sums)
    passes=[]
    for tn in TARGETS:
        for bn in BOUNDS:
            z=sm[(sm.target==tn)&(sm.boundary==bn)&sm.partition.isin(MAJOR)]
            ok=bool(len(z)==3 and (z.n>=30).all() and (z.wr>=.70).all() and (z.expectancy>0).all() and (z.pf>=1.20).all())
            min_pf=float(z.pf.min()) if len(z)==3 else np.nan; min_exp=float(z.expectancy.min()) if len(z)==3 else np.nan
            pooled=d[(d.partition.isin(MAJOR))&(d.target_name==tn)&(d.boundary_name==bn)].sort_values('entry_ts')
            pm=metrics(pooled)
            passes.append({'target':tn,'boundary':bn,'screen_pass':ok,'min_major_pf':min_pf,'min_major_expectancy':min_exp,'pooled_n':pm['n'],'pooled_wr':pm['wr'],'pooled_pf':pm['pf'],'pooled_expectancy':pm['expectancy'],'pooled_net':pm['net'],'pooled_max_loss_streak':pm['max_loss_streak']})
    ps=pd.DataFrame(passes)
    passing=ps[ps.screen_pass].copy()
    if len(passing):
        passing=passing.sort_values(['min_major_pf','min_major_expectancy','pooled_net'],ascending=[False,False,False])
        winner=passing.iloc[0]; status='ETH_LONG_B27Z_ADAPT_ECONOMIC_PAIR_FOUND'
    else:
        winner=None; status='ETH_LONG_B27Z_ADAPT_NO_PAIR_PASSED'
    sm.to_csv(OUT_SUM,index=False); OUT_STATUS.write_text(status+'\n')

    md=['# ETH LONG B27Z-Adapt — F75 Extension Economic Backtest — Result','',
        f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**; frozen F75 fills: **{len(src)}**.','',
        'Frozen grid: targets E05/E10/E15 × completed-close invalidation D30(F45)/D40(F35)/D50(F25)/D60(F15). $500 notional, $0.40 round-trip fee.','',
        '## Major-partition economics','',
        '| Partition | Target | Boundary | N | WR | PF | Exp | Net | TP | Invalidation | Time exit | Max LS |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm[sm.partition.isin(MAJOR)].itertuples(index=False):
        md.append(f'| {r.partition} | {r.target} | {r.boundary} | {r.n} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.net)} | {pct(r.tp_rate)} | {pct(r.inv_rate)} | {pct(r.time_rate)} | {r.max_loss_streak} |')
    md += ['','## Cross-partition screen','',
           '| Target | Boundary | Pass | Min PF | Min exp | Pooled N | Pooled WR | Pooled PF | Pooled exp | Pooled net | Max LS |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in ps.sort_values(['screen_pass','min_major_pf','pooled_net'],ascending=[False,False,False]).itertuples(index=False):
        md.append(f'| {r.target} | {r.boundary} | {"PASS" if r.screen_pass else "FAIL"} | {num(r.min_major_pf)} | ${num(r.min_major_expectancy)} | {r.pooled_n} | {pct(r.pooled_wr)} | {num(r.pooled_pf)} | ${num(r.pooled_expectancy)} | ${num(r.pooled_net)} | {r.pooled_max_loss_streak} |')
    if winner is not None:
        md += ['',f'**Selected pair: {winner.target} + {winner.boundary}.**']
    else:
        md += ['','**No target/invalidation pair passed all frozen major-partition gates.**']
    md += ['',f'**Status: {status}**','', 'Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
