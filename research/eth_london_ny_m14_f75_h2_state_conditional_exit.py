#!/usr/bin/env python3
from __future__ import annotations

import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BAR5=pd.Timedelta(minutes=5)
PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
NOTIONAL=500.0
FEE=0.40
TARGET_EXT=.15
F50=.50
F75=.75
VARIANTS=('BASE_F50','F75_PRE_H2_EXIT','F75_POST_H2_EXIT')

M5_AUDIT=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
M8_TRADES=ROOT/'ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX_Trades.csv'
M10_TRADES=ROOT/'ETH_LONDON_NY_M10_PRE_BREAKOUT_FAILURE_ANATOMY_Trades.csv'
M13_STATUS=ROOT/'ETH_LONDON_NY_M13_F75_PARTIAL_DERISK_Status.txt'
PFX='ETH_LONDON_NY_M14_F75_H2_STATE_CONDITIONAL_EXIT'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

spec=importlib.util.spec_from_file_location('m1',HERE/'eth_london_ny_liquidity_pressure_m1.py')
m1=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m1)

def as_bool(s): return s.astype(str).str.lower().eq('true')
def fast_slice(x,a,z):
    i=int(x.index.searchsorted(a,side='left')); j=int(x.index.searchsorted(z,side='left'))
    return x.iloc[i:j]

def pf(vals):
    a=np.asarray(list(vals),dtype=float)
    if not len(a): return np.nan
    gp=float(a[a>0].sum()) if np.any(a>0) else 0.0
    gl=float(-a[a<0].sum()) if np.any(a<0) else 0.0
    if gl==0 and gp>0:return math.inf
    return gp/gl if gl>0 else np.nan

def metrics(q,col):
    v=pd.to_numeric(q[col],errors='coerce').dropna().to_numpy(float)
    if not len(v): return dict(n=0,wins=0,wr=np.nan,pf=np.nan,expectancy=np.nan,net=0.0,max_ls=0)
    cur=mx=0
    for z in v:
        if z<0: cur+=1; mx=max(mx,cur)
        else: cur=0
    return dict(n=len(v),wins=int((v>0).sum()),wr=float((v>0).mean()),pf=pf(v),expectancy=float(v.mean()),net=float(v.sum()),max_ls=mx)

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{n}f}'

def load_cohort():
    if M5_STATUS.exists(): assert M5_STATUS.read_text().strip()=='ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS'
    if M13_STATUS.exists(): assert M13_STATUS.read_text().strip()=='ETH_LONDON_NY_M13_NO_SUPPORTED_PARTIAL_DERISK'
    a=pd.read_csv(M5_AUDIT)
    a=a[(a.variant=='EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('entry_bar_start','session_end','h2_bar_start'):
        a[c]=pd.to_datetime(a[c],utc=True,errors='coerce')
    for c in ('H','L','R','entry_px'):
        a[c]=pd.to_numeric(a[c],errors='raise')
    a['cohort_id']=a.partition.astype(str)+'|'+a.date_utc.astype(str)+'|'+a.entry_bar_start.astype(str)
    assert len(a)==95 and a.cohort_id.is_unique and (a.R>0).all()
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)

def pnl(entry_px,exit_px,reason,bps):
    k=float(bps)/10000.0
    ep=float(entry_px)*(1.0+k)
    xp=float(exit_px) if reason=='TARGET' else float(exit_px)*(1.0-k)
    return NOTIONAL*(xp/ep-1.0)-FEE

def simulate(x,r,variant):
    H=float(r.H); L=float(r.L); R=float(r.R)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end); ep=float(r.entry_px)
    h2=pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    target=H+TARGET_EXT*R; stop=L+F50*R; f75=L+F75*R
    q=fast_slice(x,start,end)
    assert len(q)>0 and q.index[0]==start and end in x.index
    first_f75_seen=False
    f75_signal=pd.NaT; f75_state='NO_F75_BREACH'
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            return dict(exit_reason='TARGET',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(target),
                        f75_breach=first_f75_seen,f75_signal_bar=f75_signal,f75_state=f75_state,conditional_exit=False)
        if float(b.close)<stop:
            return dict(exit_reason='CLOSE_INVALIDATION',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(b.close),
                        f75_breach=first_f75_seen,f75_signal_bar=f75_signal,f75_state=f75_state,conditional_exit=False)
        if (not first_f75_seen) and float(b.close)<f75:
            first_f75_seen=True; f75_signal=ts
            f75_state='H2_SEEN' if (pd.notna(h2) and h2<=ts) else 'PRE_H2'
            should_exit=((variant=='F75_PRE_H2_EXIT' and f75_state=='PRE_H2') or
                         (variant=='F75_POST_H2_EXIT' and f75_state=='H2_SEEN'))
            if should_exit:
                action=ts+BAR5
                if action<end and action in x.index:
                    px=float(x.loc[action].open)
                    return dict(exit_reason='F75_CONDITIONAL_NEXT_OPEN',exit_bar_start=action,exit_ts=action,exit_px=px,
                                f75_breach=True,f75_signal_bar=ts,f75_state=f75_state,conditional_exit=True)
    return dict(exit_reason='TIME_EXIT',exit_bar_start=end,exit_ts=end,exit_px=float(x.loc[end].open),
                f75_breach=first_f75_seen,f75_signal_bar=f75_signal,f75_state=f75_state,conditional_exit=False)

def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=20,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':99.0,'high':99.2,'low':98.8,'close':99.0},index=idx)
    R=type('R',(),{})
    r=R(); r.H=100.; r.L=90.; r.R=10.; r.entry_px=99.; r.entry_bar_start=idx[0]; r.session_end=idx[-1]; r.h2_bar_start=pd.NaT
    # Target beats same-bar F75 close.
    x.loc[idx[0],['high','close']]=[102.,97.]
    z=simulate(x,r,'F75_PRE_H2_EXIT'); assert z['exit_reason']=='TARGET'
    # F50 close beats F75 conditional event.
    x.loc[idx[0],['high','close']]=[99.5,94.]
    z=simulate(x,r,'F75_PRE_H2_EXIT'); assert z['exit_reason']=='CLOSE_INVALIDATION'
    # PRE_H2 F75 event acts on next open.
    x.loc[idx[0],['high','close']]=[99.5,97.]; x.loc[idx[1],'open']=97.2
    z=simulate(x,r,'F75_PRE_H2_EXIT'); assert z['conditional_exit'] and z['exit_bar_start']==idx[1] and z['f75_state']=='PRE_H2'
    # Same-bar H2 belongs to H2_SEEN.
    r.h2_bar_start=idx[0]
    z=simulate(x,r,'F75_POST_H2_EXIT'); assert z['conditional_exit'] and z['f75_state']=='H2_SEEN'

def main():
    synthetic_tests()
    c=load_cohort(); x,cov=m1.load5('ETHUSDT'); assert cov>=.995
    rows=[]
    for r in c.itertuples(index=False):
        for v in VARIANTS:
            z=simulate(x,r,v)
            p0=pnl(float(r.entry_px),z['exit_px'],z['exit_reason'],0.0)
            p5=pnl(float(r.entry_px),z['exit_px'],z['exit_reason'],5.0)
            rows.append({'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,'variant':v,
                         'entry_bar_start':r.entry_bar_start,'entry_px':r.entry_px,'H':r.H,'L':r.L,'R':r.R,
                         'h2_bar_start':r.h2_bar_start,**z,'pnl_0':p0,'pnl_5':p5})
    t=pd.DataFrame(rows)

    # Exact M8 E15/F50 baseline parity.
    m8=pd.read_csv(M8_TRADES)
    m8=m8[(m8.target_name=='E15')&(m8.risk_name=='F50')].copy()
    m8['exit_ts']=pd.to_datetime(m8.exit_ts,utc=True,errors='coerce')
    base=t[t.variant=='BASE_F50'].copy(); base['exit_ts']=pd.to_datetime(base.exit_ts,utc=True,errors='coerce')
    j=base.merge(m8[['cohort_id','exit_reason','exit_ts','exit_px','pnl_0','pnl_5']],on='cohort_id',suffixes=('_m14','_m8'),validate='one_to_one')
    parity=(len(j)==95 and (j.exit_reason_m14==j.exit_reason_m8).all() and (j.exit_ts_m14==j.exit_ts_m8).all() and
            np.allclose(j.exit_px_m14,j.exit_px_m8,rtol=0,atol=1e-9) and np.allclose(j.pnl_0_m14,j.pnl_0_m8,rtol=0,atol=1e-9) and np.allclose(j.pnl_5_m14,j.pnl_5_m8,rtol=0,atol=1e-9))

    # Attach baseline PnL and state audit against M10 persisted F75 anatomy.
    bp=base[['cohort_id','pnl_0','pnl_5']].rename(columns={'pnl_0':'baseline_pnl_0','pnl_5':'baseline_pnl_5'})
    t=t.merge(bp,on='cohort_id',how='left',validate='many_to_one')
    t['delta_vs_base_0']=t.pnl_0-t.baseline_pnl_0
    t['delta_vs_base_5']=t.pnl_5-t.baseline_pnl_5

    m10=pd.read_csv(M10_TRADES,usecols=['cohort_id','F75_breach','F75_breach_bar_start','F75_h2_before_breach','F75_h2_same_breach_bar'])
    m10['F75_breach']=as_bool(m10.F75_breach); m10['F75_h2_before_breach']=as_bool(m10.F75_h2_before_breach); m10['F75_h2_same_breach_bar']=as_bool(m10.F75_h2_same_breach_bar)
    m10['F75_breach_bar_start']=pd.to_datetime(m10.F75_breach_bar_start,utc=True,errors='coerce')
    cand=t[(t.variant=='F75_PRE_H2_EXIT')&t.f75_breach].merge(m10,on='cohort_id',how='left',validate='one_to_one')
    cand['f75_signal_bar']=pd.to_datetime(cand.f75_signal_bar,utc=True,errors='coerce')
    state_expected=np.where(cand.F75_h2_before_breach|cand.F75_h2_same_breach_bar,'H2_SEEN','PRE_H2')
    state_audit=bool(len(cand)==0 or ((cand.F75_breach)&(cand.f75_signal_bar==cand.F75_breach_bar_start)&(cand.f75_state.to_numpy()==state_expected)).all())

    t.to_csv(OUT_TRADES,index=False)
    chronology=bool((pd.to_datetime(t.loc[t.conditional_exit,'exit_bar_start'],utc=True)==pd.to_datetime(t.loc[t.conditional_exit,'f75_signal_bar'],utc=True)+BAR5).all())
    audit=pd.DataFrame([
        {'check':'cohort_95_x_3','value':len(t),'expected':285,'pass':len(t)==285},
        {'check':'m8_base_e15_f50_exact_parity','value':int(parity),'pass':bool(parity)},
        {'check':'raw_coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'f75_state_matches_m10','value':int(state_audit),'pass':state_audit},
        {'check':'conditional_exit_next_open','value':int(chronology),'pass':chronology},
        {'check':'max_one_row_per_setup_variant','value':int(t.groupby(['cohort_id','variant']).size().max()==1),'pass':bool(t.groupby(['cohort_id','variant']).size().max()==1)},
    ])
    audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    sums=[]
    for v in VARIANTS:
        for p in (*PARTS,'POOLED_MAJOR'):
            q=t[t.variant==v].copy(); q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
            q=q.sort_values('entry_bar_start')
            m0=metrics(q,'pnl_0'); m5=metrics(q,'pnl_5')
            exits=q[q.conditional_exit]
            base_losers=exits[exits.baseline_pnl_0<0]; base_winners=exits[exits.baseline_pnl_0>0]
            sums.append({'partition':p,'variant':v,**{f'{k}_0':val for k,val in m0.items()},**{f'{k}_5':val for k,val in m5.items()},
                         'f75_breach_n':int(q.f75_breach.sum()),'pre_h2_n':int((q.f75_state=='PRE_H2').sum()),'h2_seen_n':int((q.f75_state=='H2_SEEN').sum()),
                         'conditional_exit_n':int(q.conditional_exit.sum()),'exit_base_loser_n':int((exits.baseline_pnl_0<0).sum()),'exit_base_winner_n':int((exits.baseline_pnl_0>0).sum()),
                         'avg_delta_base_loser_0':float(base_losers.delta_vs_base_0.mean()) if len(base_losers) else np.nan,
                         'avg_delta_base_winner_0':float(base_winners.delta_vs_base_0.mean()) if len(base_winners) else np.nan})
    s=pd.DataFrame(sums)

    passes={}
    for v in ('F75_PRE_H2_EXIT','F75_POST_H2_EXIT'):
        majors=s[(s.variant==v)&s.partition.isin(MAJOR)]
        dev=s[(s.variant==v)&(s.partition=='development')].iloc[0]
        ext=s[(s.variant==v)&(s.partition=='external')].iloc[0]
        ref=s[(s.variant==v)&(s.partition=='reference_validation')].iloc[0]
        pool=s[(s.variant==v)&(s.partition=='POOLED_MAJOR')].iloc[0]
        ok=bool(audit_ok and len(majors)==3 and (majors.n_0>=15).all() and (majors.wr_0>=.70).all() and
                dev.pf_0>=1.00 and dev.expectancy_0>0 and dev.net_0>0 and ext.pf_0>1.00 and ext.net_0>0 and ref.pf_0>1.00 and ref.net_0>0 and
                pool.wr_0>=.72 and pool.pf_0>=1.30 and pool.expectancy_0>0 and pool.net_0>0 and pool.pf_5>1.00 and pool.net_5>0)
        passes[v]=ok
        s.loc[s.variant==v,'screen_pass']=ok
    s['screen_pass']=s.get('screen_pass',False).fillna(False)
    s.to_csv(OUT_SUM,index=False)

    pool=s[s.partition=='POOLED_MAJOR']
    dev=s[s.partition=='development']
    passed=pool[(pool.variant.isin(passes))&pool.screen_pass]
    status='ETH_LONDON_NY_M14_H2_STATE_CONDITIONAL_EXIT_SUPPORTED' if len(passed) else 'ETH_LONDON_NY_M14_NO_SUPPORTED_H2_STATE_EXIT'

    lines=['# ETH London -> New York M14 F75 H2-State Conditional Exit — Result','',
           f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen benchmark: **F90 EARLY_RECLAIM -> E15 / F50**. M14 conditions a full F75 next-open exit only on the binary H2 state observed at the first F75 breach.','',
           f'- Cohort: **{len(c)} setups**.','- M8 E15/F50 exact baseline parity: **PASS**.' if parity else '- M8 baseline parity: **FAIL**.',
           f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Pooled-major economics','',
           '| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | F75 breaches | PRE_H2 | H2_SEEN | Cond exits | Pass |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in pool.itertuples(index=False):
        tag='baseline' if r.variant=='BASE_F50' else ('YES' if bool(r.screen_pass) else 'NO')
        lines.append(f'| {r.variant} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.f75_breach_n)} | {int(r.pre_h2_n)} | {int(r.h2_seen_n)} | {int(r.conditional_exit_n)} | {tag} |')
    lines += ['','## Development economics','',
              '| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Cond exits | Base losers cut | Base winners cut |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in dev.itertuples(index=False):
        lines.append(f'| {r.variant} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.conditional_exit_n)} | {int(r.exit_base_loser_n)} | {int(r.exit_base_winner_n)} |')
    lines += ['','## State composition by major partition','',
              '| Partition | F75 breaches | PRE_H2 | H2_SEEN |', '|---|---:|---:|---:|']
    state_rows=s[(s.variant=='F75_PRE_H2_EXIT')&s.partition.isin(MAJOR)]
    for r in state_rows.itertuples(index=False):
        lines.append(f'| {r.partition} | {int(r.f75_breach_n)} | {int(r.pre_h2_n)} | {int(r.h2_seen_n)} |')
    lines += ['','## Decision','',f'**Status: {status}**','',
              f'- Supported candidate(s): **{", ".join(passed.variant.tolist()) if len(passed) else "none"}**.',
              '- M14 tests only the binary H2 state at F75; no extra fraction, level, timeout, re-entry, trailing stop, indicator, leverage, or portfolio rule was searched.']
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
