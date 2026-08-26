#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_f15_short_collision_b27dt as dt

ROOT=Path(__file__).resolve().parent.parent
PFX='BTC_NR7_COMPRESSION_EXPANSION_B27EB'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_TR=ROOT/f'{PFX}_Trades.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_WIN=ROOT/f'{PFX}_Windows.csv'; OUT_SLIP=ROOT/f'{PFX}_Slippage.csv'; OUT_DIAG=ROOT/f'{PFX}_ClockSide.csv'; OUT_PORT=ROOT/f'{PFX}_Portfolio.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
BAR5=pd.Timedelta(minutes=5); BLOCK=pd.Timedelta(hours=4)
NOTIONAL=500.0; FEE=.40
PARTS=dt.PARTS; MAJOR=dt.MAJOR
WINDOWS=(('W1','2020-01-01','2021-07-01',True),('W2','2021-07-01','2023-01-01',True),('W3','2023-01-01','2024-07-01',True),('W4','2024-07-01','2026-01-01',True),('W5_YTD','2026-01-01','2027-01-01',False))


def pf(vals):
    v=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); gp=float(v[v>0].sum()); gl=float(-v[v<0].sum())
    if gl==0 and gp>0:return float('inf')
    return gp/gl if gl>0 else np.nan

def metrics(d,col='pnl'):
    if d is None or len(d)==0:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v=pd.to_numeric(d[col],errors='coerce').dropna()
    return {'n':int(len(v)),'wins':int((v>0).sum()),'wr':float((v>0).mean()),'pf':pf(v),'expectancy':float(v.mean()),'net':float(v.sum())}

def fslice(x,start,end):
    a=int(x.index.searchsorted(start,side='left')); b=int(x.index.searchsorted(end,side='left')); return x.iloc[a:b]

def part_for(comp_start,exp_start,exp_end):
    return dt.dr.part_for_window(comp_start,exp_start,exp_end)

def block_table(x5):
    z=x5[['high','low']].resample('4h',origin='start_day',label='left',closed='left').agg({'high':'max','low':'min'})
    cnt=x5['close'].resample('4h',origin='start_day',label='left',closed='left').count()
    z['count']=cnt; z=z[z['count']==48].copy(); z['range']=z.high-z.low
    return z

def simulate(x5,T,H,L,part):
    end=T+BLOCK; exe=fslice(x5,T,end)
    if len(exe)!=48:return None
    first_i=None; side=None
    for i,(ts,b) in enumerate(exe.iterrows()):
        c=float(b.close)
        if c>H: first_i=i; side='LONG'; break
        if c<L: first_i=i; side='SHORT'; break
    if first_i is None or first_i+1>=len(exe):return None
    b2=exe.iloc[first_i+1]; t2=exe.index[first_i+1]; c2=float(b2.close)
    accepted=(side=='LONG' and c2>H) or (side=='SHORT' and c2<L)
    if not accepted:return None
    entry_ts=t2+BAR5
    if entry_ts>=end:return None
    pos=int(x5.index.searchsorted(entry_ts,side='left'))
    if pos>=len(x5) or x5.index[pos]!=entry_ts:return None
    entry=float(x5.iloc[pos].open); stop=L if side=='LONG' else H
    risk=(entry-stop) if side=='LONG' else (stop-entry)
    if not np.isfinite(risk) or risk<=0:return None
    target=entry+risk if side=='LONG' else entry-risk
    q=fslice(x5,entry_ts,end); exit_ts=pd.NaT; exit_px=np.nan; reason=None
    for ts,b in q.iterrows():
        if side=='LONG': hit_sl=float(b.low)<=stop; hit_tp=float(b.high)>=target
        else: hit_sl=float(b.high)>=stop; hit_tp=float(b.low)<=target
        if hit_sl:
            exit_ts=ts+BAR5; exit_px=stop; reason='SL'; break
        if hit_tp:
            exit_ts=ts+BAR5; exit_px=target; reason='TP'; break
    if reason is None:
        p=int(x5.index.searchsorted(end,side='left'))
        if p>=len(x5) or x5.index[p]!=end:return None
        exit_ts=end; exit_px=float(x5.iloc[p].open); reason='TIME'
    gross=(exit_px/entry-1.0) if side=='LONG' else (1.0-exit_px/entry)
    pnl=gross*NOTIONAL-FEE
    return {'partition':part,'anchor':T,'anchor_hour':int(T.hour),'compression_start':T-BLOCK,'compression_end':T,'H':H,'L':L,'box_range':H-L,'side':side,'first_outside_bar':exe.index[first_i],'second_outside_bar':t2,'entry_ts':entry_ts,'entry_px':entry,'stop_px':stop,'target_px':target,'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'pnl':pnl}

def build_candidates(x5):
    b=block_table(x5); rows=[]; idx=b.index
    for i in range(6,len(b)-1):
        T=idx[i]+BLOCK
        # row i is the compression block [T-4h,T); prior six are i-6..i-1
        cur=b.iloc[i]
        # Require exact contiguous seven 4H blocks and exact expansion block availability.
        expected=[T-BLOCK*(7-j) for j in range(7)]
        actual=list(idx[i-6:i+1])
        if actual!=expected: continue
        if not float(cur['range'])<=float(b.iloc[i-6:i]['range'].min())+1e-12: continue
        comp_start=T-BLOCK; end=T+BLOCK; part=part_for(comp_start,T,end)
        if part is None: continue
        r=simulate(x5,T,float(cur.high),float(cur.low),part)
        if r is not None: rows.append(r)
    q=pd.DataFrame(rows)
    if q.empty:raise RuntimeError('no NR7 candidates')
    for c in ('entry_ts','exit_ts','anchor','compression_start','compression_end','first_outside_bar','second_outside_bar'):q[c]=pd.to_datetime(q[c],utc=True)
    q['source']='NR7_'+q.anchor_hour.astype(str).str.zfill(2)+'_'+q.side
    q['clock_min_norm']=q.anchor_hour*60
    q['candidate_id']=q.partition.astype(str)+'|NR7|'+q.anchor.astype(str)+'|'+q.side.astype(str)
    return q.sort_values('entry_ts').reset_index(drop=True)

def locked_primary(cand):
    n=cand[['partition','entry_ts','exit_ts','pnl','side','source','clock_min_norm','candidate_id']].copy().rename(columns={'exit_ts':'exit_ts_norm'})
    lk=dt.lock_rows(n,'B27EB_NR7_PRIMARY'); return lk[lk.accepted_portfolio.astype(bool)].copy(),lk

def scope_summary(acc):
    rows=[]
    for p in (*PARTS,'POOLED_MAJOR'):
        g=acc[acc.partition==p] if p!='POOLED_MAJOR' else acc[acc.partition.isin(MAJOR)]
        rows.append({'scope':p,**metrics(g)})
    return pd.DataFrame(rows)
def between(d,a,z):
    aa=pd.Timestamp(a,tz='UTC'); zz=pd.Timestamp(z,tz='UTC');return d[(d.entry_ts>=aa)&(d.entry_ts<zz)].copy()
def window_summary(acc):
    p=acc[acc.partition.isin(MAJOR)].copy(); rows=[]
    for name,a,z,complete in WINDOWS:rows.append({'window':name,'start':a,'end':z,'completed':complete,**metrics(between(p,a,z))})
    return pd.DataFrame(rows)
def clock_side_diag(acc):
    p=acc[acc.partition.isin(MAJOR)].copy(); rows=[]
    for h in (0,4,8,12,16,20):
        for s in ('LONG','SHORT'):
            g=p[(p.clock_min_norm==h*60)&(p.side==s)]
            rows.append({'anchor_hour':h,'side':s,**metrics(g)})
    return pd.DataFrame(rows)
def slip(acc):
    p=acc[acc.partition.isin(MAJOR)].copy(); rows=[]
    for bps in (0,2,5,10):
        f=bps/10000.; en=p.entry_px.astype(float).copy(); ex=p.exit_px.astype(float).copy()
        lm=p.side.eq('LONG'); en.loc[lm]*=(1+f); ex.loc[lm]*=(1-f); en.loc[~lm]*=(1-f); ex.loc[~lm]*=(1+f)
        pnl=np.where(lm,(ex/en-1.0)*NOTIONAL-FEE,(1.0-ex/en)*NOTIONAL-FEE)
        z=p.copy();z['pnl_stress']=pnl;rows.append({'bps_per_fill':bps,**metrics(z,'pnl_stress')})
    return pd.DataFrame(rows)
def current_control(x5):
    raw,locked,base=dt.build_long(x5);rawL=dt.normalize_long(raw);sc=dt.build_shorts(x5);sh=dt.normalize_short(sc);s20=sh[sh.clock_min_norm==1200].copy();full=pd.concat([rawL,s20],ignore_index=True)
    lk=dt.lock_rows(full,'B27EB_CONTROL');acc=lk[lk.accepted_portfolio.astype(bool)].copy();m=metrics(dt.pooled(acc))
    if not(m['n']==283 and abs(m['wr']-207/283)<1e-12 and abs(m['pf']-2.34)<=.03 and abs(m['net']-367.49)<=.30):raise AssertionError('control parity '+str(m))
    return full,acc,m
def portfolio(x5,acc):
    full,control,cm=current_control(x5)
    c=acc[['partition','entry_ts','exit_ts','pnl','side','source','clock_min_norm','candidate_id']].copy().rename(columns={'exit_ts':'exit_ts_norm'})
    lk=dt.lock_rows(pd.concat([full,c],ignore_index=True),'B27EB_PLUS_NR7');ac=lk[lk.accepted_portfolio.astype(bool)].copy();am=metrics(dt.pooled(ac))
    cids=set(dt.pooled(control).candidate_id.astype(str)); cur=dt.pooled(ac[~ac.source.str.startswith('NR7_')]); aids=set(cur.candidate_id.astype(str));disp=len(cids-aids)
    inc=dt.pooled(ac[ac.source.str.startswith('NR7_')]);im=metrics(inc)
    return pd.DataFrame([{'portfolio':'CURRENT_LONG_SHORT20',**cm,'incremental_n':0,'incremental_net':0.0,'displaced_current_n':0},{'portfolio':'PLUS_NR7',**am,'incremental_n':im['n'],'incremental_wr':im['wr'],'incremental_pf':im['pf'],'incremental_net':im['net'],'displaced_current_n':disp}]),cm,am,im,disp

def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.2f}'
def usd(x):return f'${float(x):+.2f}'

def main():
    x5,cov=dt.dq.dn.dl.dj.b21.load5();assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    cand=build_candidates(x5);acc,alllk=locked_primary(cand);summ=scope_summary(acc);win=window_summary(acc);diag=clock_side_diag(acc);sl=slip(acc)
    dev=summ[summ.scope=='development'].iloc[0];ext=summ[summ.scope=='external'].iloc[0];val=summ[summ.scope=='reference_validation'].iloc[0]
    devpass=bool(dev.n>=100 and dev.wr>=.65 and dev.pf>=1.30 and dev.expectancy>0)
    repl=bool(devpass and ext.n>=50 and ext.wr>=.60 and ext.pf>=1.20 and ext.expectancy>0 and val.n>=40 and val.wr>=.60 and val.pf>=1.20 and val.expectancy>0)
    completed=win[win.completed.astype(bool)];stab=bool(repl and int(((completed.n>=20)&(completed.net>0)&(completed.pf>=1.05)).sum())>=3 and not ((completed.n>=20)&(completed.pf<.75)).any())
    s5=sl[sl.bps_per_fill==5].iloc[0];execok=bool(stab and s5.wr>=.60 and s5.pf>=1.20 and s5.net>0)
    port=pd.DataFrame();portok=False
    if execok:
        port,cm,am,im,disp=portfolio(x5,acc);portok=bool(am['n']>283 and am['net']>cm['net'] and am['wr']>=.70 and am['pf']>=1.80 and disp<=5 and im['net']>0)
    else:
        _,_,cm=current_control(x5);port=pd.DataFrame([{'portfolio':'CURRENT_LONG_SHORT20',**cm,'incremental_n':0,'incremental_net':0.0,'displaced_current_n':0}])
    supported=bool(devpass and repl and stab and execok and portok);status='B27EB_NR7_COMPRESSION_EXPANSION_HISTORICAL_CANDIDATE_SUPPORTED' if supported else 'B27EB_NR7_COMPRESSION_EXPANSION_NOT_SUPPORTED'
    cand.to_csv(OUT_TR,index=False);summ.to_csv(OUT_SUM,index=False);win.to_csv(OUT_WIN,index=False);sl.to_csv(OUT_SLIP,index=False);diag.to_csv(OUT_DIAG,index=False);port.to_csv(OUT_PORT,index=False);OUT_STATUS.write_text(status+'\n')
    pool=summ[summ.scope=='POOLED_MAJOR'].iloc[0]
    lines=['# B27EB — NR7 Compression -> Accepted Expansion — Result','',f'Raw 5m rows **{len(x5):,}**, coverage **{cov:.4%}**. Raw accepted NR7 candidates before one-position lock: **{len(cand)}**.','',f'Pooled-major locked primary: **N={int(pool.n)}, WR={pct(pool.wr)}, PF={num(pool.pf)}, net={usd(pool.net)}**.','',
           '## Frozen partition test','', '| Scope | N | WR | PF | Exp | Net |','|---|---:|---:|---:|---:|---:|']
    for r in summ.itertuples(index=False):lines.append(f'| {r.scope} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} |')
    lines+=['',f'Development gate: **{"PASS" if devpass else "FAIL"}**. Historical replication: **{"PASS" if repl else "FAIL"}**.','', '## Chronological windows','', '| Window | N | WR | PF | Net |','|---|---:|---:|---:|---:|']
    for r in win.itertuples(index=False):lines.append(f'| {r.window} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} |')
    lines+=['',f'Chronological stability: **{"PASS" if stab else "FAIL"}**.','', '## Adverse slippage','', '| bps/fill | N | WR | PF | Net |','|---:|---:|---:|---:|---:|']
    for r in sl.itertuples(index=False):lines.append(f'| {r.bps_per_fill} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} |')
    lines+=['',f'5bps gate: **{"PASS" if execok else "FAIL"}**.','', '## Diagnostic clock/side anatomy (not selectable)','', '| UTC anchor | Side | N | WR | PF | Net |','|---:|---|---:|---:|---:|---:|']
    for r in diag.itertuples(index=False):lines.append(f'| {r.anchor_hour:02d}:00 | {r.side} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} |')
    lines+=['','## Portfolio','', '| Portfolio | N | WR | PF | Net | Incremental N | Incremental Net | Displaced current |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in port.itertuples(index=False):lines.append(f'| {r.portfolio} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} | {r.incremental_n} | {usd(r.incremental_net)} | {r.displaced_current_n} |')
    lines+=['',f'Portfolio gate: **{"PASS" if portok else "FAIL"}**.','',f'**Status: `{status}`.**','', 'No post-result rescue is allowed inside B27EB. Clock/side rows are diagnostic only. Pre-B27DX portfolio caveat applies. No live exchange writes changed.']
    OUT_MD.write_text('\n'.join(lines)+'\n');print('\n'.join(lines))

if __name__=='__main__':main()
