#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BAR5=pd.Timedelta(minutes=5)
PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
BOUNDS={'F80':.80,'F75':.75}
CHECKPOINTS=(15,30,45,60)
F90=.90

M10_TRADES=ROOT/'ETH_LONDON_NY_M10_PRE_BREAKOUT_FAILURE_ANATOMY_Trades.csv'
M10_STATUS=ROOT/'ETH_LONDON_NY_M10_PRE_BREAKOUT_FAILURE_ANATOMY_Status.txt'
PFX='ETH_LONDON_NY_M11_DEEP_BREACH_SECONDARY_F90_RECLAIM'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_CP=ROOT/f'{PFX}_CheckpointSummary.csv'
OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

spec=importlib.util.spec_from_file_location('m1',HERE/'eth_london_ny_liquidity_pressure_m1.py')
m1=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m1)

def as_bool(s): return s.astype(str).str.lower().eq('true')

def fast_slice(x,a,z):
    i=int(x.index.searchsorted(a,side='left')); j=int(x.index.searchsorted(z,side='left'))
    return x.iloc[i:j]

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=1): return '-' if pd.isna(v) else f'{float(v):.{n}f}'

def load_cohort():
    if M10_STATUS.exists():
        assert M10_STATUS.read_text().strip()=='ETH_LONDON_NY_M10_NO_PRE_BO_FAILURE_SIGNATURE'
    t=pd.read_csv(M10_TRADES)
    for c in ('entry_bar_start','h2_bar_start','terminal_bar_start','terminal_completion',
              'F80_breach_bar_start','F80_reclaim_F90_bar_start','F75_breach_bar_start','F75_reclaim_F90_bar_start'):
        t[c]=pd.to_datetime(t[c],utc=True,errors='coerce')
    for c in ('H','L','R','entry_px','entry_fraction'):
        t[c]=pd.to_numeric(t[c],errors='raise')
    t['eventual_breakout']=as_bool(t.eventual_breakout)
    t['F80_breach']=as_bool(t.F80_breach); t['F75_breach']=as_bool(t.F75_breach)
    assert len(t)==95 and t.cohort_id.is_unique
    return t.sort_values(['partition','entry_bar_start']).reset_index(drop=True)

def analyze_boundary(x,r,bname,bf):
    breach_flag=bool(getattr(r,f'{bname}_breach'))
    if not breach_flag: return None
    H=float(r.H); L=float(r.L); R=float(r.R); f90=L+F90*R; bpx=L+bf*R
    bbar=pd.Timestamp(getattr(r,f'{bname}_breach_bar_start'))
    assert pd.notna(bbar)
    assert float(x.loc[bbar].close) < bpx
    bcomp=bbar+BAR5
    tcomp=pd.Timestamp(r.terminal_completion)
    assert bcomp<=tcomp
    bo_bar=pd.Timestamp(r.terminal_bar_start) if bool(r.eventual_breakout) else pd.NaT
    if bool(r.eventual_breakout):
        assert pd.notna(bo_bar) and float(x.loc[bo_bar].close)>H and bbar<bo_bar
    q=fast_slice(x,bbar+BAR5,tcomp)
    hits=q.index[pd.to_numeric(q.close,errors='raise')>f90]
    rec_bar=pd.Timestamp(hits[0]) if len(hits) else pd.NaT
    rec_comp=rec_bar+BAR5 if pd.notna(rec_bar) else pd.NaT
    if pd.notna(rec_bar): assert rec_bar>bbar
    if bool(r.eventual_breakout):
        if pd.isna(rec_bar): rec_class='NO_RECLAIM_BEFORE_BO'
        elif rec_bar<bo_bar: rec_class='RECLAIM_BEFORE_BO'
        elif rec_bar==bo_bar: rec_class='RECLAIM_ON_BO_BAR'
        else: raise AssertionError('reclaim after breakout terminal')
    else:
        rec_class='NONWINNER_RECLAIM' if pd.notna(rec_bar) else 'NONWINNER_NO_RECLAIM'
    z={
        'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,'boundary':bname,
        'boundary_fraction':bf,'boundary_px':bpx,'F90_px':f90,'H':H,'L':L,'R':R,
        'entry_bar_start':pd.Timestamp(r.entry_bar_start),'deep_breach_bar_start':bbar,'deep_breach_completion':bcomp,
        'eventual_breakout':bool(r.eventual_breakout),'breakout_bar_start':bo_bar,
        'terminal':r.terminal,'terminal_completion':tcomp,
        'secondary_reclaim':pd.notna(rec_bar),'secondary_reclaim_bar_start':rec_bar,
        'secondary_reclaim_completion':rec_comp,'reclaim_class':rec_class,
        'breach_to_reclaim_min':float((rec_comp-bcomp)/pd.Timedelta(minutes=1)) if pd.notna(rec_comp) else np.nan,
        'breach_to_bo_min':float((bo_bar+BAR5-bcomp)/pd.Timedelta(minutes=1)) if pd.notna(bo_bar) else np.nan,
    }
    for m in CHECKPOINTS:
        cp=bcomp+pd.Timedelta(minutes=m)
        # A deadline could only fire when trade has not already structurally resolved by cp.
        alive=cp<tcomp
        z[f'cp{m}_eligible']=bool(alive)
        if alive:
            reclaimed=bool(pd.notna(rec_comp) and rec_comp<=cp)
            z[f'cp{m}_state']='RECLAIMED_F90' if reclaimed else 'NO_RECLAIM_F90'
        else:
            z[f'cp{m}_state']='NOT_ELIGIBLE'
        # Winner protection for a hypothetical no-reclaim deadline: already BO or already reclaimed by cp.
        if bool(r.eventual_breakout):
            bo_comp=bo_bar+BAR5
            z[f'cp{m}_winner_protected']=bool(bo_comp<=cp or (pd.notna(rec_comp) and rec_comp<=cp))
        else:
            z[f'cp{m}_winner_protected']=False
    return z

def summary_for(g,part,b):
    q=g[(g.boundary==b) & (g.partition.isin(MAJOR) if part=='POOLED_MAJOR' else (g.partition==part))].copy()
    w=q[q.eventual_breakout]; n=q[~q.eventual_breakout]
    wr=float(w.secondary_reclaim.mean()) if len(w) else np.nan
    nr=float(n.secondary_reclaim.mean()) if len(n) else np.nan
    return {
        'partition':part,'boundary':b,'deep_breach_n':len(q),'winner_n':len(w),'nonwinner_n':len(n),
        'winner_reclaim_rate':wr,'winner_reclaim_before_bo_rate':float((w.reclaim_class=='RECLAIM_BEFORE_BO').mean()) if len(w) else np.nan,
        'winner_reclaim_on_bo_rate':float((w.reclaim_class=='RECLAIM_ON_BO_BAR').mean()) if len(w) else np.nan,
        'nonwinner_reclaim_rate':nr,'separation_pp':100*(wr-nr) if len(w) and len(n) else np.nan,
        'median_breach_to_reclaim_min':float(q.loc[q.secondary_reclaim,'breach_to_reclaim_min'].median()) if int(q.secondary_reclaim.sum()) else np.nan,
        'p75_breach_to_reclaim_min':float(q.loc[q.secondary_reclaim,'breach_to_reclaim_min'].quantile(.75)) if int(q.secondary_reclaim.sum()) else np.nan,
        'bo_rate_if_reclaim':float(q.loc[q.secondary_reclaim,'eventual_breakout'].mean()) if int(q.secondary_reclaim.sum()) else np.nan,
        'bo_rate_if_no_reclaim':float(q.loc[~q.secondary_reclaim,'eventual_breakout'].mean()) if int((~q.secondary_reclaim).sum()) else np.nan,
    }

def checkpoint_for(g,part,b,m,state):
    q=g[(g.boundary==b) & (g.partition.isin(MAJOR) if part=='POOLED_MAJOR' else (g.partition==part))].copy()
    q=q[q[f'cp{m}_eligible'] & (q[f'cp{m}_state']==state)].copy()
    return {'partition':part,'boundary':b,'checkpoint_min':m,'state':state,'n':len(q),
            'eventual_bo_n':int(q.eventual_breakout.sum()) if len(q) else 0,
            'eventual_bo_rate':float(q.eventual_breakout.mean()) if len(q) else np.nan}

def main():
    c=load_cohort(); x,cov=m1.load5('ETHUSDT'); assert cov>=.995
    rows=[]
    for r in c.itertuples(index=False):
        for b,f in BOUNDS.items():
            z=analyze_boundary(x,r,b,f)
            if z is not None: rows.append(z)
    t=pd.DataFrame(rows); t.to_csv(OUT_TRADES,index=False)
    assert len(t)>0

    sums=[]
    for p in (*PARTS,'POOLED_MAJOR'):
        for b in BOUNDS: sums.append(summary_for(t,p,b))
    s=pd.DataFrame(sums)

    sig={}
    for b in BOUNDS:
        pool=s[(s.partition=='POOLED_MAJOR')&(s.boundary==b)].iloc[0]
        majors=s[(s.partition.isin(MAJOR))&(s.boundary==b)]
        win_ok=majors[majors.winner_n>=5]
        non_ok=majors[majors.nonwinner_n>=5]
        ok=bool(pool.deep_breach_n>=30 and pool.winner_n>=15 and pool.nonwinner_n>=10 and
                pool.winner_reclaim_rate>=.90 and pool.nonwinner_reclaim_rate<=.20 and pool.separation_pp>=65 and
                (len(win_ok)==0 or (win_ok.winner_reclaim_rate>=.85).all()) and
                (len(non_ok)==0 or (non_ok.nonwinner_reclaim_rate<=.35).all()))
        sig[b]=ok
        s.loc[s.boundary==b,'signature_supported']=ok
    s.to_csv(OUT_SUM,index=False)

    cps=[]
    for p in (*PARTS,'POOLED_MAJOR'):
        for b in BOUNDS:
            for m in CHECKPOINTS:
                for st in ('RECLAIMED_F90','NO_RECLAIM_F90'):
                    cps.append(checkpoint_for(t,p,b,m,st))
    cp=pd.DataFrame(cps)

    deadlines=[]
    for b in BOUNDS:
        bw=t[(t.boundary==b)&t.eventual_breakout].copy()
        for m in CHECKPOINTS:
            pool=cp[(cp.partition=='POOLED_MAJOR')&(cp.boundary==b)&(cp.checkpoint_min==m)&(cp.state=='NO_RECLAIM_F90')].iloc[0]
            majors=cp[(cp.partition.isin(MAJOR))&(cp.boundary==b)&(cp.checkpoint_min==m)&(cp.state=='NO_RECLAIM_F90')]
            adequate=majors[majors.n>=5]
            retention=float(bw[f'cp{m}_winner_protected'].mean()) if len(bw) else np.nan
            ok=bool(pool.n>=10 and pool.eventual_bo_rate<=.30 and
                    (len(adequate)==0 or (adequate.eventual_bo_rate<=.40).all()) and retention>=.80)
            deadlines.append({'boundary':b,'checkpoint_min':m,'deadline_candidate':ok,
                              'no_reclaim_n':int(pool.n),'no_reclaim_bo_rate':pool.eventual_bo_rate,
                              'winner_protection_rate':retention})
    d=pd.DataFrame(deadlines)
    for r in d.itertuples(index=False):
        mask=(cp.boundary==r.boundary)&(cp.checkpoint_min==r.checkpoint_min)&(cp.state=='NO_RECLAIM_F90')
        cp.loc[mask,'deadline_candidate']=bool(r.deadline_candidate)
        cp.loc[mask,'winner_protection_rate']=r.winner_protection_rate
    cp.to_csv(OUT_CP,index=False)

    # Mandatory audits.
    expected_breakouts=int(c.eventual_breakout.sum())
    t_winners=t[t.eventual_breakout]
    audit=pd.DataFrame([
        {'check':'m10_cohort_rows','value':len(c),'expected':95,'pass':len(c)==95},
        {'check':'m10_breakout_count','value':expected_breakouts,'expected':77,'pass':expected_breakouts==77},
        {'check':'coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'deep_breach_precedes_reclaim','value':int((pd.to_datetime(t.loc[t.secondary_reclaim,'secondary_reclaim_bar_start'],utc=True)>pd.to_datetime(t.loc[t.secondary_reclaim,'deep_breach_bar_start'],utc=True)).all()),'pass':bool((pd.to_datetime(t.loc[t.secondary_reclaim,'secondary_reclaim_bar_start'],utc=True)>pd.to_datetime(t.loc[t.secondary_reclaim,'deep_breach_bar_start'],utc=True)).all())},
        {'check':'winner_reclaim_class_order','value':int((t_winners.reclaim_class.isin({'RECLAIM_BEFORE_BO','RECLAIM_ON_BO_BAR','NO_RECLAIM_BEFORE_BO'})).all()),'pass':bool((t_winners.reclaim_class.isin({'RECLAIM_BEFORE_BO','RECLAIM_ON_BO_BAR','NO_RECLAIM_BEFORE_BO'})).all())},
    ])
    audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    supported=[b for b,v in sig.items() if v]
    deadline_rows=d[d.deadline_candidate]
    status=('ETH_LONDON_NY_M11_SECONDARY_RECLAIM_SIGNATURE_SUPPORTED' if audit_ok and supported
            else 'ETH_LONDON_NY_M11_NO_SECONDARY_RECLAIM_SIGNATURE')

    lines=['# ETH London -> New York M11 Deep-Breach Secondary F90 Reclaim — Result','',
           f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen cohort: **M5 F90 EARLY_RECLAIM executed entries; deep completed-close breaches F80/F75 only**.','',
           f'- M10 cohort parity: **{len(c)} rows / {expected_breakouts} breakout winners**.',
           f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Secondary F90 reclaim signature — pooled major','',
           '| Boundary | Deep N | Winners | Non-winners | Winner reclaim | Before BO | On BO bar | Non-winner reclaim | Separation | BO if reclaim | BO if no reclaim | Signature |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in s[s.partition=='POOLED_MAJOR'].itertuples(index=False):
        lines.append(f'| {r.boundary} | {int(r.deep_breach_n)} | {int(r.winner_n)} | {int(r.nonwinner_n)} | {pct(r.winner_reclaim_rate)} | {pct(r.winner_reclaim_before_bo_rate)} | {pct(r.winner_reclaim_on_bo_rate)} | {pct(r.nonwinner_reclaim_rate)} | {num(r.separation_pp)} pp | {pct(r.bo_rate_if_reclaim)} | {pct(r.bo_rate_if_no_reclaim)} | {"PASS" if bool(r.signature_supported) else "NO"} |')
    lines += ['','## Major-partition detail','',
              '| Partition | Boundary | Deep N | Winner N | Non-winner N | Winner reclaim | Non-winner reclaim | Median breach->reclaim |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in s[s.partition.isin(MAJOR)].itertuples(index=False):
        lines.append(f'| {r.partition} | {r.boundary} | {int(r.deep_breach_n)} | {int(r.winner_n)} | {int(r.nonwinner_n)} | {pct(r.winner_reclaim_rate)} | {pct(r.nonwinner_reclaim_rate)} | {num(r.median_breach_to_reclaim_min)}m |')
    lines += ['','## No-reclaim recovery deadlines — pooled major','',
              '| Boundary | Checkpoint | No-reclaim N | Eventual BO | Winner protected by deadline | Candidate |',
              '|---|---:|---:|---:|---:|---|']
    for r in d.itertuples(index=False):
        lines.append(f'| {r.boundary} | {int(r.checkpoint_min)}m | {int(r.no_reclaim_n)} | {pct(r.no_reclaim_bo_rate)} | {pct(r.winner_protection_rate)} | {"YES" if bool(r.deadline_candidate) else "NO"} |')
    lines += ['','## Decision','',f'**Status: {status}**','',
              f'- Supported secondary-reclaim boundaries: **{", ".join(supported) if supported else "none"}**.',
              f'- Recovery-deadline candidates: **{", ".join(f"{r.boundary}@{int(r.checkpoint_min)}m" for r in deadline_rows.itertuples(index=False)) if len(deadline_rows) else "none"}**.',
              '- M11 authorizes no trading rule or economics; any deadline/filter requires a separate preregistered execution test.']
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
