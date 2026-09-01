#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S10_PATH=HERE/'eth_b27dx_s10_hybrid_profit_lock.py'
spec=importlib.util.spec_from_file_location('eth_s10',S10_PATH); s10=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s10)
s4=s10.s4

PFX='ETH_B27DX_S12_GLOBAL_COLLISION_AUDIT'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'; OUT_MATRIX=ROOT/f'{PFX}_CollisionMatrix.csv'; OUT_BLOCKED=ROOT/f'{PFX}_BlockedOutcomeSummary.csv'; OUT_HOLD=ROOT/f'{PFX}_HoldingSummary.csv'; OUT_TIES=ROOT/f'{PFX}_Ties.csv'; OUT_POS=ROOT/f'{PFX}_BlockingPositions.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
PARTS=s4.PARTS

def pf(vals):
    a=np.asarray(list(vals),dtype=float)
    if len(a)==0:return np.nan
    gp=float(a[a>0].sum()) if np.any(a>0) else 0.; gl=float(-a[a<0].sum()) if np.any(a<0) else 0.
    return math.inf if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan)
def metrics(g,col='pnl_0'):
    if g.empty:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v=pd.to_numeric(g[col],errors='coerce').dropna().to_numpy(float)
    return {'n':len(v),'wins':int((v>0).sum()),'wr':float((v>0).mean()),'pf':pf(v),'expectancy':float(v.mean()),'net':float(v.sum())}
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def lock_with_provenance(c):
    all_rows=[]
    for p in PARTS:
        q=c[c.partition==p].sort_values(['entry_bar_start','execution_start','exec_min'],ascending=[True,False,True]).copy()
        locked_until=pd.NaT; active=None
        rows=[]
        for r in q.itertuples(index=False):
            entry=pd.Timestamp(r.entry_bar_start)
            if pd.isna(locked_until) or entry>=pd.Timestamp(locked_until):
                accepted=True; blocker_id=''; blocker_clock=''; blocker_entry=pd.NaT; blocker_exit=pd.NaT; remain=np.nan; ctype='ACCEPT'
                active=r; locked_until=pd.Timestamp(r.exit_ts)
            else:
                accepted=False
                blocker_id=str(active.candidate_id); blocker_clock=str(active.execution_utc); blocker_entry=pd.Timestamp(active.entry_bar_start); blocker_exit=pd.Timestamp(active.exit_ts)
                remain=float((blocker_exit-entry)/pd.Timedelta(minutes=1))
                ctype='SAME_ENTRY_TIE' if entry==blocker_entry else 'OPEN_POSITION'
            d=r._asdict(); d.update({'accepted_s12':accepted,'collision_type':ctype,'blocker_candidate_id':blocker_id,'blocker_clock':blocker_clock,'blocker_entry':blocker_entry,'blocker_exit':blocker_exit,'minutes_until_blocker_exit':remain})
            if accepted:
                d['blocker_pnl_0']=np.nan; d['blocker_pnl_5']=np.nan
            else:
                d['blocker_pnl_0']=float(active.pnl_0); d['blocker_pnl_5']=float(active.pnl_5)
            rows.append(d)
        all_rows.append(pd.DataFrame(rows))
    return pd.concat(all_rows,ignore_index=True)

def summarize_blocked(b):
    rows=[]
    for by in ('execution_utc','blocker_clock'):
        for key,g in b.groupby(by,dropna=False):
            rows.append({'group_by':by,'group':key,**metrics(g,'pnl_0'),'pf_5':metrics(g,'pnl_5')['pf'],'net_5':metrics(g,'pnl_5')['net']})
    rows.append({'group_by':'ALL','group':'ALL',**metrics(b,'pnl_0'),'pf_5':metrics(b,'pnl_5')['pf'],'net_5':metrics(b,'pnl_5')['net']})
    return pd.DataFrame(rows)

def main():
    x,cov=s4.b.m.m.load5(); fixed,runner,hybrid,audit10=s10.build_hybrid(x)
    base_dec,base_sum,_=s4.summarize(hybrid)
    d=lock_with_provenance(hybrid)
    # parity by candidate id / accepted flag
    b=base_dec[['candidate_id','accepted']].copy().rename(columns={'accepted':'accepted_base'})
    z=d[['candidate_id','accepted_s12']].merge(b,on='candidate_id',how='outer',validate='one_to_one')
    z['pass']=z.accepted_s12.eq(z.accepted_base)
    parity=bool(len(z)==len(d)==len(base_dec) and z['pass'].all())
    audit=pd.DataFrame([
        {'check':'s10_build_audit','value':int(bool(audit10['pass'].all())),'pass':bool(audit10['pass'].all())},
        {'check':'decision_count_parity','value':len(z),'pass':len(z)==len(d)==len(base_dec)},
        {'check':'accepted_decision_parity','value':int(z['pass'].sum()),'pass':parity},
        {'check':'accepted_exit_after_entry','value':int((pd.to_datetime(d.loc[d.accepted_s12,'exit_ts'],utc=True)>=pd.to_datetime(d.loc[d.accepted_s12,'entry_bar_start'],utc=True)).sum()),'pass':bool((pd.to_datetime(d.loc[d.accepted_s12,'exit_ts'],utc=True)>=pd.to_datetime(d.loc[d.accepted_s12,'entry_bar_start'],utc=True)).all())},
    ])
    audit.to_csv(OUT_AUDIT,index=False); d.to_csv(OUT_DETAIL,index=False)
    a=d[d.accepted_s12].copy(); blocked=d[~d.accepted_s12].copy()

    # collision matrix
    mx=blocked.groupby(['blocker_clock','execution_utc']).agg(blocked_n=('candidate_id','size'),standalone_wins=('pnl_0',lambda v:int((pd.to_numeric(v)>0).sum())),standalone_net=('pnl_0','sum')).reset_index()
    mx.to_csv(OUT_MATRIX,index=False)
    bs=summarize_blocked(blocked); bs.to_csv(OUT_BLOCKED,index=False)

    # holding / blocking position anatomy
    a['hold_min']=(pd.to_datetime(a.exit_ts,utc=True)-pd.to_datetime(a.entry_bar_start,utc=True))/pd.Timedelta(minutes=1)
    hc=[]
    for clock,g in a.groupby('execution_utc'):
        hc.append({'execution_utc':clock,'n':len(g),'median_hold_min':float(g.hold_min.median()),'mean_hold_min':float(g.hold_min.mean()),'p75_hold_min':float(g.hold_min.quantile(.75)),**metrics(g,'pnl_0')})
    hold=pd.DataFrame(hc); hold.to_csv(OUT_HOLD,index=False)

    counts=blocked.groupby('blocker_candidate_id').size().rename('signals_blocked').reset_index()
    pos=a[['candidate_id','partition','execution_utc','entry_bar_start','exit_ts','pnl_0','pnl_5','hold_min']].merge(counts,left_on='candidate_id',right_on='blocker_candidate_id',how='left').drop(columns=['blocker_candidate_id'])
    pos['signals_blocked']=pos.signals_blocked.fillna(0).astype(int); pos=pos.sort_values(['signals_blocked','hold_min'],ascending=[False,False]); pos.to_csv(OUT_POS,index=False)

    # exact ties
    ties=[]
    for (p,ts),g in d.groupby(['partition','entry_bar_start']):
        if len(g)<=1: continue
        gg=g.sort_values(['execution_start','exec_min'],ascending=[False,True])
        winner=gg[gg.accepted_s12]
        winner_id=str(winner.iloc[0].candidate_id) if len(winner) else ''
        for r in gg.itertuples(index=False):
            ties.append({'partition':p,'entry_bar_start':ts,'group_size':len(gg),'candidate_id':r.candidate_id,'execution_utc':r.execution_utc,'execution_start':r.execution_start,'current_winner':str(r.candidate_id)==winner_id,'standalone_pnl_0':r.pnl_0,'standalone_pnl_5':r.pnl_5,'exit_ts':r.exit_ts})
    tiedf=pd.DataFrame(ties); tiedf.to_csv(OUT_TIES,index=False)

    # remaining-time buckets
    bins=[-1e-9,5,15,30,60,float('inf')]; labels=['<=5m','5-15m','15-30m','30-60m','>60m']
    blocked['remaining_bucket']=pd.cut(blocked.minutes_until_blocker_exit,bins=bins,labels=labels,include_lowest=True,right=True)
    bucket=blocked.groupby('remaining_bucket',observed=False).agg(n=('candidate_id','size'),wins=('pnl_0',lambda v:int((pd.to_numeric(v)>0).sum())),net=('pnl_0','sum')).reset_index()

    same_tie_groups=int((d.groupby(['partition','entry_bar_start']).size()>1).sum())
    same_tie_candidates=int((d.collision_type=='SAME_ENTRY_TIE').sum())
    blocked_wins=int((blocked.pnl_0>0).sum()); blocked_losses=int((blocked.pnl_0<0).sum()); blocked_flat=int((blocked.pnl_0==0).sum())
    blocked_rate=len(blocked)/len(d) if len(d) else np.nan
    top=pos.head(10)

    lines=['# ETH B27DX — S12 Global Collision / One-Position Audit — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen portfolio under audit: **S10 hybrid** — 05:00 fixed E25 · 09:00 fixed E25 · 10:00 E10 profit-lock runner · 16:00 fixed E25.','',
           f'- S10 source audit: **{"PASS" if bool(audit10["pass"].all()) else "FAIL"}**.',f'- Exact S10 one-position decision parity: **{"PASS" if parity else "FAIL"}**.','',
           '## Global one-position anatomy','',
           f'- Candidates: **{len(d)}**.',f'- Accepted: **{len(a)}**.',f'- Blocked while another ETH position was open: **{len(blocked)} ({blocked_rate:.1%})**.',
           f'- Exact same-entry tie groups: **{same_tie_groups}**; alternatives blocked by same-entry tie: **{same_tie_candidates}**.',
           f'- Blocked candidates standalone outcome: **{blocked_wins} wins / {blocked_losses} losses / {blocked_flat} flat**. These are counterfactual diagnostics only.','',
           '## Collision matrix','',
           '| Active blocker | Later blocked clock | Blocked N | Standalone wins | Standalone net |','|---:|---:|---:|---:|---:|']
    for r in mx.sort_values(['blocker_clock','execution_utc']).itertuples(index=False):
        lines.append(f'| {r.blocker_clock} | {r.execution_utc} | {int(r.blocked_n)} | {int(r.standalone_wins)} | {fmt(r.standalone_net)} |')
    lines += ['', '## Blocked candidate standalone quality by blocked clock','', '| Blocked clock | N | WR | PF | Exp | Net | 5bps PF | 5bps Net |','|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in bs[bs.group_by=='execution_utc'].sort_values('group').itertuples(index=False):
        lines.append(f'| {r.group} | {int(r.n)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {fmt(r.pf_5)} | {fmt(r.net_5)} |')
    lines += ['', '## Accepted holding time by clock','', '| Clock | N | Median hold | Mean hold | P75 hold | WR | PF | Exp | Net |','|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in hold.sort_values('execution_utc').itertuples(index=False):
        lines.append(f'| {r.execution_utc} | {int(r.n)} | {r.median_hold_min:.1f}m | {r.mean_hold_min:.1f}m | {r.p75_hold_min:.1f}m | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} |')
    lines += ['', '## How close blocked signals were to portfolio becoming free','', '| Remaining until blocker exit | N | Standalone wins | Standalone net |','|---|---:|---:|---:|']
    for r in bucket.itertuples(index=False): lines.append(f'| {r.remaining_bucket} | {int(r.n)} | {int(r.wins)} | {fmt(r.net)} |')
    lines += ['', '## Accepted positions that blocked the most later signals','', '| Clock | Entry | Exit | Hold | Signals blocked | Trade PnL |','|---:|---|---|---:|---:|---:|']
    for r in top.itertuples(index=False): lines.append(f'| {r.execution_utc} | {r.entry_bar_start} | {r.exit_ts} | {r.hold_min:.1f}m | {int(r.signals_blocked)} | {fmt(r.pnl_0)} |')
    lines += ['', '## Interpretation guardrail','',
              '- Blocked-candidate PnL is **not executable portfolio PnL** and is never added to S10 results.',
              '- S12 does **not** change clock priority, tie-break, entry, exit, runner, or live configuration.',
              '- Any collision rule suggested by this anatomy requires a new preregistered causal experiment.','',
              '## Decision','',
              f'**Status: {"ETH_S12_GLOBAL_COLLISION_AUDIT_VALID" if parity and bool(audit["pass"].all()) else "ETH_S12_GLOBAL_COLLISION_AUDIT_INVALID"}**']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(lines[-1].replace('**Status: ','').replace('**','')+'\n'); print(OUT_MD.read_text())

if __name__=='__main__': main()
