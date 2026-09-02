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
TARGETS={'E05':.05,'E10':.10,'E15':.15}
F50=.50; F75=.75

M8_TRADES=ROOT/'ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX_Trades.csv'
M14_TRADES=ROOT/'ETH_LONDON_NY_M14_F75_H2_STATE_CONDITIONAL_EXIT_Trades.csv'
M14_STATUS=ROOT/'ETH_LONDON_NY_M14_F75_H2_STATE_CONDITIONAL_EXIT_Status.txt'
PFX='ETH_LONDON_NY_M15_M14_TARGET_FAMILY'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

spec=importlib.util.spec_from_file_location('m14',HERE/'eth_london_ny_m14_f75_h2_state_conditional_exit.py')
m14=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m14)

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{n}f}'

def simulate(x,r,target_ext,managed):
    H=float(r.H); L=float(r.L); R=float(r.R)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end)
    h2=pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
    target=H+float(target_ext)*R; stop=L+F50*R; f75=L+F75*R
    q=m14.fast_slice(x,start,end)
    assert len(q)>0 and q.index[0]==start and end in x.index
    first_f75=False; f75_signal=pd.NaT; f75_state='NO_F75_BREACH'
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            return dict(exit_reason='TARGET',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(target),
                        f75_breach=first_f75,f75_signal_bar=f75_signal,f75_state=f75_state,conditional_exit=False)
        if float(b.close)<stop:
            return dict(exit_reason='CLOSE_INVALIDATION',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(b.close),
                        f75_breach=first_f75,f75_signal_bar=f75_signal,f75_state=f75_state,conditional_exit=False)
        if (not first_f75) and float(b.close)<f75:
            first_f75=True; f75_signal=ts
            f75_state='H2_SEEN' if (pd.notna(h2) and h2<=ts) else 'PRE_H2'
            if managed and f75_state=='H2_SEEN':
                action=ts+BAR5
                if action<end and action in x.index:
                    return dict(exit_reason='F75_CONDITIONAL_NEXT_OPEN',exit_bar_start=action,exit_ts=action,exit_px=float(x.loc[action].open),
                                f75_breach=True,f75_signal_bar=ts,f75_state=f75_state,conditional_exit=True)
    return dict(exit_reason='TIME_EXIT',exit_bar_start=end,exit_ts=end,exit_px=float(x.loc[end].open),
                f75_breach=first_f75,f75_signal_bar=f75_signal,f75_state=f75_state,conditional_exit=False)

def variant_target(v): return v.split('_')[-1]
def is_managed(v): return v.startswith('M14_')

def main():
    assert M14_STATUS.read_text().strip()=='ETH_LONDON_NY_M14_H2_STATE_CONDITIONAL_EXIT_SUPPORTED'
    c=m14.load_cohort(); x,cov=m14.m1.load5('ETHUSDT'); assert cov>=.995
    variants=[f'BASE_{t}' for t in TARGETS]+[f'M14_{t}' for t in TARGETS]
    rows=[]
    for r in c.itertuples(index=False):
        for v in variants:
            tn=variant_target(v); z=simulate(x,r,TARGETS[tn],is_managed(v))
            p0=m14.pnl(float(r.entry_px),z['exit_px'],z['exit_reason'],0.0)
            p5=m14.pnl(float(r.entry_px),z['exit_px'],z['exit_reason'],5.0)
            rows.append({'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,'variant':v,'target_name':tn,
                         'target_ext':TARGETS[tn],'managed':is_managed(v),'entry_bar_start':r.entry_bar_start,'entry_px':r.entry_px,
                         'H':r.H,'L':r.L,'R':r.R,'h2_bar_start':r.h2_bar_start,**z,'pnl_0':p0,'pnl_5':p5})
    t=pd.DataFrame(rows)

    # Exact M8 parity for each unmanaged target.
    m8=pd.read_csv(M8_TRADES)
    m8=m8[(m8.risk_name=='F50') & m8.target_name.isin(TARGETS)].copy()
    m8['exit_ts']=pd.to_datetime(m8.exit_ts,utc=True,errors='coerce')
    parity_rows=[]
    for tn in TARGETS:
        a=t[t.variant==f'BASE_{tn}'].copy(); a['exit_ts']=pd.to_datetime(a.exit_ts,utc=True,errors='coerce')
        b=m8[m8.target_name==tn].copy()
        j=a.merge(b[['cohort_id','exit_reason','exit_ts','exit_px','pnl_0','pnl_5']],on='cohort_id',suffixes=('_m15','_m8'),validate='one_to_one')
        ok=(len(j)==95 and (j.exit_reason_m15==j.exit_reason_m8).all() and (j.exit_ts_m15==j.exit_ts_m8).all() and
            np.allclose(j.exit_px_m15,j.exit_px_m8,rtol=0,atol=1e-9) and
            np.allclose(j.pnl_0_m15,j.pnl_0_m8,rtol=0,atol=1e-9) and np.allclose(j.pnl_5_m15,j.pnl_5_m8,rtol=0,atol=1e-9))
        parity_rows.append((tn,ok))

    # Exact M14 managed E15 parity.
    m14t=pd.read_csv(M14_TRADES)
    m14t=m14t[m14t.variant=='F75_POST_H2_EXIT'].copy(); m14t['exit_ts']=pd.to_datetime(m14t.exit_ts,utc=True,errors='coerce')
    a=t[t.variant=='M14_E15'].copy(); a['exit_ts']=pd.to_datetime(a.exit_ts,utc=True,errors='coerce')
    j=a.merge(m14t[['cohort_id','exit_reason','exit_ts','exit_px','pnl_0','pnl_5']],on='cohort_id',suffixes=('_m15','_m14'),validate='one_to_one')
    m14_parity=(len(j)==95 and (j.exit_reason_m15==j.exit_reason_m14).all() and (j.exit_ts_m15==j.exit_ts_m14).all() and
                np.allclose(j.exit_px_m15,j.exit_px_m14,rtol=0,atol=1e-9) and
                np.allclose(j.pnl_0_m15,j.pnl_0_m14,rtol=0,atol=1e-9) and np.allclose(j.pnl_5_m15,j.pnl_5_m14,rtol=0,atol=1e-9))

    # Same-target baseline deltas.
    bases=t[~t.managed][['cohort_id','target_name','pnl_0','pnl_5']].rename(columns={'pnl_0':'baseline_pnl_0','pnl_5':'baseline_pnl_5'})
    t=t.merge(bases,on=['cohort_id','target_name'],how='left',validate='many_to_one')
    t['delta_vs_base_0']=t.pnl_0-t.baseline_pnl_0; t['delta_vs_base_5']=t.pnl_5-t.baseline_pnl_5
    t.to_csv(OUT_TRADES,index=False)

    chronology=bool((pd.to_datetime(t.loc[t.conditional_exit,'exit_bar_start'],utc=True)==pd.to_datetime(t.loc[t.conditional_exit,'f75_signal_bar'],utc=True)+BAR5).all())
    h2_state=bool((t.loc[t.conditional_exit,'f75_state']=='H2_SEEN').all())
    audit_rows=[
        {'check':'cohort_95_x_6','value':len(t),'expected':570,'pass':len(t)==570},
        {'check':'raw_coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        *[{'check':f'm8_base_{tn}_f50_exact_parity','value':int(ok),'pass':bool(ok)} for tn,ok in parity_rows],
        {'check':'m14_managed_e15_exact_parity','value':int(m14_parity),'pass':bool(m14_parity)},
        {'check':'conditional_exit_next_open','value':int(chronology),'pass':chronology},
        {'check':'conditional_exit_h2_seen_only','value':int(h2_state),'pass':h2_state},
        {'check':'one_row_per_setup_variant','value':int(t.groupby(['cohort_id','variant']).size().max()==1),'pass':bool(t.groupby(['cohort_id','variant']).size().max()==1)},
    ]
    audit=pd.DataFrame(audit_rows); audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    sums=[]
    for v in variants:
        tn=variant_target(v)
        for p in (*PARTS,'POOLED_MAJOR'):
            q=t[t.variant==v].copy(); q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
            q=q.sort_values('entry_bar_start')
            m0=m14.metrics(q,'pnl_0'); m5=m14.metrics(q,'pnl_5')
            exits=q[q.conditional_exit]
            sums.append({'partition':p,'variant':v,'target_name':tn,'managed':is_managed(v),
                         **{f'{k}_0':val for k,val in m0.items()},**{f'{k}_5':val for k,val in m5.items()},
                         'conditional_exit_n':int(q.conditional_exit.sum()),
                         'cut_base_loser_n':int((exits.baseline_pnl_0<0).sum()),'cut_base_winner_n':int((exits.baseline_pnl_0>0).sum()),
                         'delta_net_vs_base_0':float(q.delta_vs_base_0.sum()),'delta_net_vs_base_5':float(q.delta_vs_base_5.sum())})
    s=pd.DataFrame(sums)

    passed=[]
    for tn in TARGETS:
        v=f'M14_{tn}'
        majors=s[(s.variant==v)&s.partition.isin(MAJOR)]
        dev=s[(s.variant==v)&(s.partition=='development')].iloc[0]
        pool=s[(s.variant==v)&(s.partition=='POOLED_MAJOR')].iloc[0]
        ok=bool(audit_ok and len(majors)==3 and (majors.n_0>=15).all() and (majors.wr_0>=.70).all() and
                (majors.pf_0>1.00).all() and (majors.net_0>0).all() and
                dev.pf_5>1.00 and dev.net_5>0 and
                pool.wr_0>=.72 and pool.pf_0>=1.30 and pool.net_0>0 and pool.pf_5>1.10 and pool.net_5>0)
        s.loc[s.variant==v,'screen_pass']=ok
        if ok: passed.append(v)
    s['screen_pass']=s['screen_pass'].fillna(False)
    s.to_csv(OUT_SUM,index=False)

    pool=s[s.partition=='POOLED_MAJOR'].copy(); dev=s[s.partition=='development'].copy()
    if passed:
        rank=pool[pool.variant.isin(passed)].merge(dev[['variant','pf_5']].rename(columns={'pf_5':'dev_pf_5'}),on='variant')
        rank=rank.sort_values(['wr_0','dev_pf_5','pf_0','net_0'],ascending=False)
        best=str(rank.iloc[0].variant)
        status='ETH_LONDON_NY_M15_TARGET_FAMILY_SUPPORTED'
    else:
        best='none'; status='ETH_LONDON_NY_M15_NO_SUPPORTED_TARGET'

    lines=['# ETH London -> New York M15 M14-Management × Target-Family Economics — Result','',
           f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen entry/management: **F90 EARLY_RECLAIM + F50 hard invalidation + M14 POST-H2 F75 next-open exit**.','',
           '- Cohort: **95 setups**.','- Target family: **E05 / E10 / E15 only**.',
           f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Pooled-major economics','',
           '| Variant | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Cond exits | ΔNet vs base | Pass |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in pool.itertuples(index=False):
        lab='baseline' if not bool(r.managed) else ('YES' if bool(r.screen_pass) else 'NO')
        lines.append(f'| {r.variant} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.conditional_exit_n)} | {num(r.delta_net_vs_base_0)} | {lab} |')
    lines += ['','## Development economics','',
              '| Variant | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Cond exits | Losers cut | Winners cut |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in dev.itertuples(index=False):
        lines.append(f'| {r.variant} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.conditional_exit_n)} | {int(r.cut_base_loser_n)} | {int(r.cut_base_winner_n)} |')
    lines += ['','## Decision','',f'**Status: {status}**','',
              f'- Supported managed target(s): **{", ".join(passed) if passed else "none"}**.',
              f'- Frozen ranking winner: **{best}**.',
              '- No target outside E05/E10/E15 and no new management parameter was tested.']
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
