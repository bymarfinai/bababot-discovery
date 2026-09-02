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
VARIANTS={
    'BASE_F50':None,
    'F80_EXIT_ONLY':.80,
    'F80_EXIT_REENTRY':.80,
    'F75_EXIT_ONLY':.75,
    'F75_EXIT_REENTRY':.75,
}
REENTRY_VARIANTS={'F80_EXIT_REENTRY','F75_EXIT_REENTRY'}

M5_AUDIT=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
M10_TRADES=ROOT/'ETH_LONDON_NY_M10_PRE_BREAKOUT_FAILURE_ANATOMY_Trades.csv'
M11_STATUS=ROOT/'ETH_LONDON_NY_M11_DEEP_BREACH_SECONDARY_F90_RECLAIM_Status.txt'
M8_TRADES=ROOT/'ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX_Trades.csv'
PFX='ETH_LONDON_NY_M12_DEEP_EXIT_SECONDARY_REENTRY'
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
    if M11_STATUS.exists(): assert M11_STATUS.read_text().strip()=='ETH_LONDON_NY_M11_SECONDARY_RECLAIM_SIGNATURE_SUPPORTED'
    a=pd.read_csv(M5_AUDIT)
    a=a[(a.variant=='EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('touch_bar_start','confirmation_bar_start','entry_bar_start','terminal_bar_start','h2_bar_start','session_end'):
        a[c]=pd.to_datetime(a[c],utc=True,errors='coerce')
    for c in ('H','L','R','entry_px','realized_entry_fraction'):
        a[c]=pd.to_numeric(a[c],errors='raise')
    a['cohort_id']=a.partition.astype(str)+'|'+a.date_utc.astype(str)+'|'+a.entry_bar_start.astype(str)
    assert len(a)==95 and a.cohort_id.is_unique and (a.R>0).all()
    m10=pd.read_csv(M10_TRADES,usecols=['cohort_id'])
    assert set(a.cohort_id)==set(m10.cohort_id) and len(m10)==95
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)

def leg_path(x,start,entry_px,end,target,stop,deep=None):
    q=fast_slice(x,start,end)
    assert len(q)>0 and q.index[0]==start and end in x.index
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            return dict(reason='TARGET',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(target))
        if deep is not None and float(b.close)<deep:
            return dict(reason='DEEP_EXIT',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(b.close))
        if float(b.close)<stop:
            return dict(reason='CLOSE_INVALIDATION',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(b.close))
    return dict(reason='TIME_EXIT',exit_bar_start=end,exit_ts=end,exit_px=float(x.loc[end].open))

def leg_pnl(entry_px,exit_px,reason,bps):
    k=float(bps)/10000.0
    ep=float(entry_px)*(1.0+k)
    xp=float(exit_px) if reason=='TARGET' else float(exit_px)*(1.0-k)
    return NOTIONAL*(xp/ep-1.0)-FEE

def structural_search_end(r):
    # Do not search for a recovery after an original opposite-break terminal.
    if str(r.terminal)=='OPPOSITE_BREAK':
        return pd.Timestamp(r.terminal_bar_start)+BAR5
    return pd.Timestamp(r.session_end)

def simulate_path(x,r,variant):
    H=float(r.H); L=float(r.L); R=float(r.R)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end); ep=float(r.entry_px)
    target=H+TARGET_EXT*R; stop=L+F50*R; f90=L+.90*R
    deep_f=VARIANTS[variant]
    deep_px=(L+deep_f*R) if deep_f is not None else None
    first=leg_path(x,start,ep,end,target,stop,deep_px)
    z=dict(first_reason=first['reason'],first_exit_bar_start=first['exit_bar_start'],first_exit_ts=first['exit_ts'],first_exit_px=first['exit_px'],
           deep_exit=first['reason']=='DEEP_EXIT',secondary_reclaim=False,reclaim_bar_start=pd.NaT,reentry=False,reentry_bar_start=pd.NaT,reentry_px=np.nan,
           reentry_status='NOT_APPLICABLE',second_reason='',second_exit_bar_start=pd.NaT,second_exit_ts=pd.NaT,second_exit_px=np.nan)
    if variant not in REENTRY_VARIANTS or first['reason']!='DEEP_EXIT': return z

    search_end=structural_search_end(r)
    after=pd.Timestamp(first['exit_bar_start'])+BAR5
    if after>=search_end:
        z['reentry_status']='NO_RECLAIM_BEFORE_TERMINAL'; return z
    q=fast_slice(x,after,search_end)
    hits=q.index[pd.to_numeric(q.close,errors='raise')>f90]
    if not len(hits):
        z['reentry_status']='NO_RECLAIM_BEFORE_TERMINAL'; return z
    rec=pd.Timestamp(hits[0]); z['secondary_reclaim']=True; z['reclaim_bar_start']=rec
    rebar=rec+BAR5
    if rebar>=end or rebar not in x.index:
        z['reentry_status']='NO_NEXT_BAR_BEFORE_END'; return z
    rep=float(x.loc[rebar].open)
    if rep>=target:
        z['reentry_status']='MISSED_TARGET_AT_OPEN'; return z
    if rep<=stop:
        z['reentry_status']='INVALID_BELOW_F50'; return z
    z['reentry']=True; z['reentry_status']='REENTERED'; z['reentry_bar_start']=rebar; z['reentry_px']=rep
    second=leg_path(x,rebar,rep,end,target,stop,None)
    z.update(second_reason=second['reason'],second_exit_bar_start=second['exit_bar_start'],second_exit_ts=second['exit_ts'],second_exit_px=second['exit_px'])
    return z

def path_pnl(z,original_entry,bps):
    p1=leg_pnl(original_entry,z['first_exit_px'],z['first_reason'],bps)
    p2=0.0
    if z['reentry']:
        p2=leg_pnl(z['reentry_px'],z['second_exit_px'],z['second_reason'],bps)
    return p1,p2,p1+p2

def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=73,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':99.2,'high':99.4,'low':99.0,'close':99.2},index=idx)
    # TP must beat same-bar deep close.
    x.loc[idx[0],['high','close']]=[102.0,97.0]
    a=leg_path(x,idx[0],99.2,idx[-1],101.5,98.0,98.5)
    assert a['reason']=='TARGET'
    # Deep close is recognized only as completed-bar exit.
    x.loc[idx[0],['high','close']]=[100.0,98.4]
    b=leg_path(x,idx[0],99.2,idx[-1],101.5,95.0,98.5)
    assert b['reason']=='DEEP_EXIT' and b['exit_ts']==idx[0]+BAR5

def main():
    synthetic_tests()
    c=load_cohort(); x,cov=m1.load5('ETHUSDT'); assert cov>=.995
    rows=[]
    for r in c.itertuples(index=False):
        for v in VARIANTS:
            z=simulate_path(x,r,v)
            p10,p20,p0=path_pnl(z,float(r.entry_px),0.0)
            p15,p25,p5=path_pnl(z,float(r.entry_px),5.0)
            rows.append({'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,'variant':v,
                         'entry_bar_start':r.entry_bar_start,'entry_px':r.entry_px,'H':r.H,'L':r.L,'R':r.R,
                         **z,'first_pnl_0':p10,'second_pnl_0':p20,'pnl_0':p0,'first_pnl_5':p15,'second_pnl_5':p25,'pnl_5':p5,
                         'salvaged_0':bool(z['reentry'] and p10<0 and p0>0),'salvaged_5':bool(z['reentry'] and p15<0 and p5>0)})
    t=pd.DataFrame(rows); t.to_csv(OUT_TRADES,index=False)

    # Exact baseline parity to M8 E15/F50 rows.
    m8=pd.read_csv(M8_TRADES)
    m8=m8[(m8.target_name=='E15')&(m8.risk_name=='F50')].copy()
    m8['exit_ts']=pd.to_datetime(m8.exit_ts,utc=True,errors='coerce')
    base=t[t.variant=='BASE_F50'].copy(); base['first_exit_ts']=pd.to_datetime(base.first_exit_ts,utc=True,errors='coerce')
    j=base.merge(m8[['cohort_id','exit_reason','exit_ts','exit_px','pnl_0','pnl_5']],on='cohort_id',suffixes=('_m12','_m8'),validate='one_to_one')
    parity=(len(j)==95 and (j.first_reason==j.exit_reason).all() and (j.first_exit_ts==j.exit_ts).all() and
            np.allclose(j.first_exit_px,j.exit_px,rtol=0,atol=1e-9) and np.allclose(j.pnl_0_m12,j.pnl_0_m8,rtol=0,atol=1e-9) and np.allclose(j.pnl_5_m12,j.pnl_5_m8,rtol=0,atol=1e-9))
    chronology=bool((pd.to_datetime(t.loc[t.reentry,'reentry_bar_start'],utc=True)>pd.to_datetime(t.loc[t.reentry,'reclaim_bar_start'],utc=True)).all())
    audit=pd.DataFrame([
        {'check':'cohort_95_x_5','value':len(t),'expected':475,'pass':len(t)==475},
        {'check':'m8_base_e15_f50_exact_parity','value':int(parity),'pass':bool(parity)},
        {'check':'raw_coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'reentry_after_reclaim','value':int(chronology),'pass':chronology},
        {'check':'max_one_reentry','value':int(t.groupby(['cohort_id','variant']).size().max()==1),'pass':bool(t.groupby(['cohort_id','variant']).size().max()==1)},
    ]); audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    sums=[]
    for v in VARIANTS:
        for p in (*PARTS,'POOLED_MAJOR'):
            q=t[t.variant==v].copy(); q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
            q=q.sort_values('entry_bar_start')
            m0=metrics(q,'pnl_0'); m5=metrics(q,'pnl_5')
            sums.append({'partition':p,'variant':v,**{f'{k}_0':val for k,val in m0.items()},**{f'{k}_5':val for k,val in m5.items()},
                         'deep_exit_n':int(q.deep_exit.sum()),'secondary_reclaim_n':int(q.secondary_reclaim.sum()),'reentry_n':int(q.reentry.sum()),
                         'no_reclaim_n':int(((q.deep_exit)&(~q.secondary_reclaim)).sum()),
                         'missed_target_open_n':int((q.reentry_status=='MISSED_TARGET_AT_OPEN').sum()),
                         'invalid_below_f50_n':int((q.reentry_status=='INVALID_BELOW_F50').sum()),
                         'salvaged_0_n':int(q.salvaged_0.sum()),'salvaged_5_n':int(q.salvaged_5.sum())})
    s=pd.DataFrame(sums)

    passes={}
    for v in REENTRY_VARIANTS:
        majors=s[(s.variant==v)&s.partition.isin(MAJOR)]
        pool=s[(s.variant==v)&(s.partition=='POOLED_MAJOR')].iloc[0]
        ok=bool(audit_ok and len(majors)==3 and (majors.n_0>=15).all() and (majors.wr_0>=.70).all() and (majors.pf_0>=1.20).all() and
                (majors.expectancy_0>0).all() and (majors.net_0>0).all() and pool.wr_0>=.70 and pool.pf_0>=1.20 and pool.expectancy_0>0 and pool.net_0>0 and
                pool.pf_5>1.0 and pool.net_5>0)
        passes[v]=ok
        s.loc[s.variant==v,'screen_pass']=ok
    s['screen_pass']=s['screen_pass'].fillna(False)
    s.to_csv(OUT_SUM,index=False)

    pool=s[s.partition=='POOLED_MAJOR'].copy()
    dev=s[s.partition=='development'].copy()
    passed=pool[(pool.variant.isin(REENTRY_VARIANTS))&pool.screen_pass].sort_values(['wr_0','pf_0','expectancy_0','pf_5'],ascending=False)
    status='ETH_LONDON_NY_M12_REENTRY_ECONOMIC_VARIANT_SUPPORTED' if len(passed) else 'ETH_LONDON_NY_M12_NO_SUPPORTED_REENTRY_ECONOMIC_VARIANT'

    lines=['# ETH London -> New York M12 Deep-Breach Exit + Secondary F90 Re-entry — Result','',
           f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen benchmark: **F90 EARLY_RECLAIM -> E15 / F50**. Deep-exit variants use F80 or F75 and at most one causal secondary-F90-reclaim next-open re-entry.','',
           f'- Cohort: **95 setups**.',f'- M8 E15/F50 exact baseline parity: **{"PASS" if parity else "FAIL"}**.',f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Pooled-major economics','',
           '| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Deep exits | Re-entries | Salvaged | Pass |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in pool.itertuples(index=False):
        label='baseline' if r.variant=='BASE_F50' else ('PASS' if bool(r.screen_pass) else 'NO')
        lines.append(f'| {r.variant} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.deep_exit_n)} | {int(r.reentry_n)} | {int(r.salvaged_0_n)} | {label} |')
    lines += ['','## Development economics','',
              '| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Deep exits | Re-entries | Salvaged |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in dev.itertuples(index=False):
        lines.append(f'| {r.variant} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.deep_exit_n)} | {int(r.reentry_n)} | {int(r.salvaged_0_n)} |')
    lines += ['','## Re-entry diagnostics — pooled major','',
              '| Variant | Deep exits | Secondary reclaims | Re-entries | No reclaim | Missed >=E15 open | Invalid <=F50 | Salvaged 0bps |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in pool[pool.variant.isin(REENTRY_VARIANTS)].itertuples(index=False):
        lines.append(f'| {r.variant} | {int(r.deep_exit_n)} | {int(r.secondary_reclaim_n)} | {int(r.reentry_n)} | {int(r.no_reclaim_n)} | {int(r.missed_target_open_n)} | {int(r.invalid_below_f50_n)} | {int(r.salvaged_0_n)} |')
    lines += ['','## Decision','',f'**Status: {status}**','']
    if len(passed):
        top=passed.iloc[0]
        lines.append(f'- WR-first formal leader: **{top.variant} — WR {pct(top.wr_0)}, PF {num(top.pf_0)}, expectancy {num(top.expectancy_0)}, net {num(top.net_0)}, 5bps PF {num(top.pf_5)}, 5bps net {num(top.net_5)}**.')
    else:
        lines.append('- **No deep-exit + secondary-reentry variant passed the frozen three-partition economic screen.**')
    lines.append('- EXIT_ONLY controls are diagnostic and cannot promote.')
    lines.append('- No additional level sweep, timing filter, post-breakout floor, leverage, or portfolio lock was tested.')
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
