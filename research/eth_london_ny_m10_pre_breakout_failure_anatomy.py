#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
BOUNDS = {'F90':.90,'F85':.85,'F80':.80,'F75':.75}
CHECKPOINTS = (15,30,45,60)

M5_AUDIT = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS = ROOT / 'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
PFX = 'ETH_LONDON_NY_M10_PRE_BREAKOUT_FAILURE_ANATOMY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_A = ROOT / f'{PFX}_BoundarySummary.csv'
OUT_B = ROOT / f'{PFX}_StallSummary.csv'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def loadmod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

m1 = loadmod('eth_m1', HERE / 'eth_london_ny_liquidity_pressure_m1.py')


def as_bool(s):
    return s.astype(str).str.lower().eq('true')


def fast_slice(x, a, z):
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def load_cohort():
    if M5_STATUS.exists():
        assert M5_STATUS.read_text().strip() == 'ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS'
    a = pd.read_csv(M5_AUDIT)
    a = a[(a.variant == 'EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('touch_bar_start','confirmation_bar_start','entry_bar_start','terminal_bar_start','h2_bar_start','session_end'):
        a[c] = pd.to_datetime(a[c], utc=True, errors='coerce')
    for c in ('H','L','R','entry_px','realized_entry_fraction'):
        a[c] = pd.to_numeric(a[c], errors='raise')
    a['strict_breakout'] = as_bool(a.strict_breakout)
    a['cohort_id'] = a.partition.astype(str) + '|' + a.date_utc.astype(str) + '|' + a.entry_bar_start.astype(str)
    assert a.cohort_id.is_unique
    assert len(a) == 95
    assert (a.R > 0).all()
    assert set(a.terminal.unique()).issubset({'STRICT_BREAKOUT','OPPOSITE_BREAK','NO_BREAK_BY_END'})
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)


def outcome_class(term):
    if term == 'STRICT_BREAKOUT': return 'BREAKOUT_WINNER'
    if term == 'OPPOSITE_BREAK': return 'NON_BREAKOUT_OPPOSITE'
    return 'NON_BREAKOUT_TIME'


def terminal_completion(r):
    if str(r.terminal) in ('STRICT_BREAKOUT','OPPOSITE_BREAK'):
        return pd.Timestamp(r.terminal_bar_start) + BAR5
    return pd.Timestamp(r.session_end)


def analyze_trade(x5, r):
    H=float(r.H); L=float(r.L); R=float(r.R)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end)
    term=str(r.terminal); tcomp=terminal_completion(r)
    if term in ('STRICT_BREAKOUT','OPPOSITE_BREAK'):
        tbar=pd.Timestamp(r.terminal_bar_start)
        q=fast_slice(x5,start,tbar+BAR5)
    else:
        tbar=end-BAR5
        q=fast_slice(x5,start,end)
    assert len(q)>0 and q.index[0]==start

    # Terminal integrity.
    if term == 'STRICT_BREAKOUT':
        assert float(x5.loc[pd.Timestamp(r.terminal_bar_start)].close) > H
    elif term == 'OPPOSITE_BREAK':
        assert float(x5.loc[pd.Timestamp(r.terminal_bar_start)].close) < L

    z={
        'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,
        'entry_bar_start':start,'entry_px':float(r.entry_px),'entry_fraction':float(r.realized_entry_fraction),
        'H':H,'L':L,'R':R,'h2_bar_start':pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT,
        'terminal':term,'terminal_bar_start':pd.Timestamp(r.terminal_bar_start) if pd.notna(r.terminal_bar_start) else pd.NaT,
        'terminal_completion':tcomp,'outcome_class':outcome_class(term),
        'eventual_breakout':term=='STRICT_BREAKOUT',
        'entry_to_terminal_min':float((tcomp-start)/pd.Timedelta(minutes=1)),
        'entry_to_h2_min':float((pd.Timestamp(r.h2_bar_start)+BAR5-start)/pd.Timedelta(minutes=1)) if pd.notna(r.h2_bar_start) else np.nan,
        'entry_to_bo_min':float((pd.Timestamp(r.terminal_bar_start)+BAR5-start)/pd.Timedelta(minutes=1)) if term=='STRICT_BREAKOUT' else np.nan,
    }

    closes = pd.to_numeric(q.close, errors='raise')
    z['min_pre_terminal_close_f'] = float((closes.min()-L)/R)

    # Family A: completed-close breach before/at terminal, never after breakout.
    for name,f in BOUNDS.items():
        px=L+f*R
        hits=q.index[pd.to_numeric(q.close,errors='raise') < px]
        if len(hits):
            bts=pd.Timestamp(hits[0]); bcomp=bts+BAR5
            post=q.loc[q.index>bts]
            rec=post.index[pd.to_numeric(post.close,errors='raise') > (L+.90*R)]
            rec_ts=pd.Timestamp(rec[0]) if len(rec) else pd.NaT
            h2=pd.Timestamp(r.h2_bar_start) if pd.notna(r.h2_bar_start) else pd.NaT
            z[f'{name}_breach']=True
            z[f'{name}_breach_bar_start']=bts
            z[f'{name}_breach_min']=float((bcomp-start)/pd.Timedelta(minutes=1))
            z[f'{name}_reclaim_F90_after']=pd.notna(rec_ts)
            z[f'{name}_reclaim_F90_bar_start']=rec_ts
            z[f'{name}_h2_before_breach']=bool(pd.notna(h2) and h2 < bts)
            z[f'{name}_h2_same_breach_bar']=bool(pd.notna(h2) and h2 == bts)
        else:
            z[f'{name}_breach']=False
            z[f'{name}_breach_bar_start']=pd.NaT
            z[f'{name}_breach_min']=np.nan
            z[f'{name}_reclaim_F90_after']=False
            z[f'{name}_reclaim_F90_bar_start']=pd.NaT
            z[f'{name}_h2_before_breach']=False
            z[f'{name}_h2_same_breach_bar']=False

    # Family B: causal checkpoint state only if still alive and unbroken at checkpoint.
    h2_comp=(pd.Timestamp(r.h2_bar_start)+BAR5) if pd.notna(r.h2_bar_start) else pd.NaT
    for m in CHECKPOINTS:
        cp=start+pd.Timedelta(minutes=m)
        alive = cp < tcomp if term in ('STRICT_BREAKOUT','OPPOSITE_BREAK') else cp < end
        # At cp == terminal completion, event is already known and case is not eligible.
        z[f'cp{m}_eligible']=bool(alive)
        if alive:
            h2_done=bool(pd.notna(h2_comp) and h2_comp <= cp)
            z[f'cp{m}_state']='H2_DONE_NO_BO' if h2_done else 'NO_H2_NO_BO'
        else:
            z[f'cp{m}_state']='NOT_ELIGIBLE'
    return z


def boundary_summary(t, part, bound):
    g=t[t.partition.isin(MAJOR)].copy() if part=='POOLED_MAJOR' else t[t.partition==part].copy()
    w=g[g.eventual_breakout.astype(bool)]
    n=g[~g.eventual_breakout.astype(bool)]
    col=f'{bound}_breach'
    wr=float(w[col].mean()) if len(w) else np.nan
    nr=float(n[col].mean()) if len(n) else np.nan
    return {
        'partition':part,'boundary':bound,'n':len(g),'winner_n':len(w),'nonwinner_n':len(n),
        'winner_breach_rate':wr,'nonwinner_breach_rate':nr,
        'separation_pp':100*(nr-wr) if len(w) and len(n) else np.nan,
        'winner_reclaim_after_breach_rate':float(w.loc[w[col],f'{bound}_reclaim_F90_after'].mean()) if int(w[col].sum()) else np.nan,
        'nonwinner_reclaim_after_breach_rate':float(n.loc[n[col],f'{bound}_reclaim_F90_after'].mean()) if int(n[col].sum()) else np.nan,
    }


def stall_summary(t, part, mins, state):
    g=t[t.partition.isin(MAJOR)].copy() if part=='POOLED_MAJOR' else t[t.partition==part].copy()
    q=g[(g[f'cp{mins}_eligible'].astype(bool)) & (g[f'cp{mins}_state']==state)].copy()
    return {
        'partition':part,'checkpoint_min':mins,'state':state,'eligible_n':len(q),
        'eventual_breakout_n':int(q.eventual_breakout.sum()) if len(q) else 0,
        'eventual_breakout_rate':float(q.eventual_breakout.mean()) if len(q) else np.nan,
        'nonbreakout_n':int((~q.eventual_breakout.astype(bool)).sum()) if len(q) else 0,
    }


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def num(v,n=1):
    return '-' if pd.isna(v) else f'{float(v):.{n}f}'


def main():
    c=load_cohort()
    x,cov=m1.load5('ETHUSDT')
    assert cov>=.995
    rows=[analyze_trade(x,r) for r in c.itertuples(index=False)]
    t=pd.DataFrame(rows)
    t.to_csv(OUT_TRADES,index=False)

    # Exact M5 outcome parity.
    assert len(t)==95
    assert int(t.eventual_breakout.sum()) == int(c.strict_breakout.sum())

    arows=[]
    for p in (*PARTS,'POOLED_MAJOR'):
        for b in BOUNDS:
            arows.append(boundary_summary(t,p,b))
    a=pd.DataFrame(arows)

    # Frozen Family A candidate screen.
    candidate_a=[]
    for b in BOUNDS:
        majors=a[(a.boundary==b)&a.partition.isin(MAJOR)]
        pool=a[(a.boundary==b)&(a.partition=='POOLED_MAJOR')].iloc[0]
        ok=bool(len(majors)==3 and (majors.winner_n>=10).all() and
                (majors.winner_breach_rate<=.20).all() and
                pool.nonwinner_breach_rate>=.50 and pool.separation_pp>=30.0)
        candidate_a.append((b,ok))
        a.loc[a.boundary==b,'structural_candidate']=ok
    a.to_csv(OUT_A,index=False)

    brows=[]
    for p in (*PARTS,'POOLED_MAJOR'):
        for m in CHECKPOINTS:
            for state in ('H2_DONE_NO_BO','NO_H2_NO_BO'):
                brows.append(stall_summary(t,p,m,state))
    bs=pd.DataFrame(brows)

    candidate_b=[]
    for m in CHECKPOINTS:
        pool=bs[(bs.partition=='POOLED_MAJOR')&(bs.checkpoint_min==m)&(bs.state=='NO_H2_NO_BO')].iloc[0]
        majors=bs[(bs.partition.isin(MAJOR))&(bs.checkpoint_min==m)&(bs.state=='NO_H2_NO_BO')]
        adequate=majors[majors.eligible_n>=5]
        ok=bool(pool.eligible_n>=10 and pool.eventual_breakout_rate<=.50 and
                (len(adequate)==0 or (adequate.eventual_breakout_rate<=.60).all()))
        candidate_b.append((m,ok))
        mask=(bs.checkpoint_min==m)&(bs.state=='NO_H2_NO_BO')
        bs.loc[mask,'stall_candidate']=ok
    bs.to_csv(OUT_B,index=False)

    # Audits.
    audit=pd.DataFrame([
        {'check':'m5_cohort_rows','value':len(t),'expected':95,'pass':len(t)==95},
        {'check':'m5_breakout_parity','value':int(t.eventual_breakout.sum()),'expected':int(c.strict_breakout.sum()),'pass':int(t.eventual_breakout.sum())==int(c.strict_breakout.sum())},
        {'check':'coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'winner_terminal_close_gt_H','value':int((t.loc[t.eventual_breakout].apply(lambda r: float(x.loc[pd.Timestamp(r.terminal_bar_start)].close)>float(r.H),axis=1)).all()),'pass':bool((t.loc[t.eventual_breakout].apply(lambda r: float(x.loc[pd.Timestamp(r.terminal_bar_start)].close)>float(r.H),axis=1)).all())},
        {'check':'checkpoint_states_valid','value':int(all(set(t[f"cp{m}_state"].unique()).issubset({'H2_DONE_NO_BO','NO_H2_NO_BO','NOT_ELIGIBLE'}) for m in CHECKPOINTS)),'pass':all(set(t[f"cp{m}_state"].unique()).issubset({'H2_DONE_NO_BO','NO_H2_NO_BO','NOT_ELIGIBLE'}) for m in CHECKPOINTS)},
    ])
    audit.to_csv(OUT_AUDIT,index=False)
    audit_ok=bool(audit['pass'].all())

    dev=t[t.partition=='development'].copy()
    devw=dev[dev.eventual_breakout]
    devn=dev[~dev.eventual_breakout]

    lines=['# ETH London -> New York M10 Pre-Breakout Failure Anatomy — Result','',
           f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen cohort: **M5 F90 EARLY_RECLAIM executed entries**. M10 uses strict completed 5m breakout `close > H` as success and contains no economics.','',
           f'- Cohort N: **{len(t)}**; breakout winners: **{int(t.eventual_breakout.sum())}**; non-breakout: **{int((~t.eventual_breakout).sum())}**.',
           f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Family A — reclaim-hold boundary discrimination (pooled major)','',
           '| Boundary | Winner breach | Non-winner breach | Separation | Winner reclaim F90 after breach | Non-winner reclaim F90 after breach | Candidate |',
           '|---|---:|---:|---:|---:|---:|---|']
    for r in a[a.partition=='POOLED_MAJOR'].itertuples(index=False):
        lines.append(f'| {r.boundary} | {pct(r.winner_breach_rate)} | {pct(r.nonwinner_breach_rate)} | {num(r.separation_pp)} pp | {pct(r.winner_reclaim_after_breach_rate)} | {pct(r.nonwinner_reclaim_after_breach_rate)} | {"YES" if bool(r.structural_candidate) else "NO"} |')

    lines += ['','### Family A — major partition winner protection','',
              '| Partition | Boundary | Winner N | Non-winner N | Winner breach | Non-winner breach |',
              '|---|---|---:|---:|---:|---:|']
    for r in a[a.partition.isin(MAJOR)].itertuples(index=False):
        lines.append(f'| {r.partition} | {r.boundary} | {int(r.winner_n)} | {int(r.nonwinner_n)} | {pct(r.winner_breach_rate)} | {pct(r.nonwinner_breach_rate)} |')

    lines += ['','## Family B — progress stall','',
              '| Checkpoint | State | Pooled N | Eventual BO | External | Development | RefVal | Candidate |',
              '|---:|---|---:|---:|---:|---:|---:|---|']
    for m in CHECKPOINTS:
        for state in ('H2_DONE_NO_BO','NO_H2_NO_BO'):
            pool=bs[(bs.partition=='POOLED_MAJOR')&(bs.checkpoint_min==m)&(bs.state==state)].iloc[0]
            vals={}
            for p in MAJOR:
                rr=bs[(bs.partition==p)&(bs.checkpoint_min==m)&(bs.state==state)].iloc[0]
                vals[p]=f'{pct(rr.eventual_breakout_rate)} (N{int(rr.eligible_n)})'
            cand=bool(pool.stall_candidate) if state=='NO_H2_NO_BO' and pd.notna(pool.stall_candidate) else False
            lines.append(f'| {m}m | {state} | {int(pool.eligible_n)} | {pct(pool.eventual_breakout_rate)} | {vals["external"]} | {vals["development"]} | {vals["reference_validation"]} | {"YES" if cand else "-"} |')

    lines += ['','## Development decomposition','',
              f'- Executed: **{len(dev)}**; breakout winners: **{len(devw)}**; non-breakout failures: **{len(devn)}**.',
              f'- Winner median entry->H2: **{num(devw.entry_to_h2_min.median())}m**; winner median entry->strict breakout: **{num(devw.entry_to_bo_min.median())}m**.',
              f'- Non-winner median entry->terminal/session end: **{num(devn.entry_to_terminal_min.median())}m**.','',
              '| Boundary | Dev winner breach | Dev non-winner breach |',
              '|---|---:|---:|']
    for b in BOUNDS:
        rr=a[(a.partition=='development')&(a.boundary==b)].iloc[0]
        lines.append(f'| {b} | {pct(rr.winner_breach_rate)} | {pct(rr.nonwinner_breach_rate)} |')

    ac=[b for b,ok in candidate_a if ok]
    bc=[f'{m}m' for m,ok in candidate_b if ok]
    status='ETH_LONDON_NY_M10_PRE_BO_FAILURE_SIGNATURE_FOUND' if audit_ok and (ac or bc) else 'ETH_LONDON_NY_M10_NO_PRE_BO_FAILURE_SIGNATURE'
    lines += ['','## Decision','',f'**Status: {status}**','',
              f'- Family A structural candidates: **{", ".join(ac) if ac else "none"}**.',
              f'- Family B stall candidates: **{", ".join(bc) if bc else "none"}**.',
              '- M10 does not authorize an exit/filter. Any candidate must be tested separately with frozen execution semantics and economics.']
    OUT_MD.write_text('\n'.join(lines))
    OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
