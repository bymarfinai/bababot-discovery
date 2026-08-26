#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_f15_short_collision_b27dt as dt

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Detail.csv'
PFX='BTC_24H_POST_REBREAK_SHORT_ECON_B27DZ'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_GRID=ROOT/f'{PFX}_Grid.csv'; OUT_TR=ROOT/f'{PFX}_Trades.csv'; OUT_WIN=ROOT/f'{PFX}_Windows.csv'; OUT_SLIP=ROOT/f'{PFX}_Slippage.csv'; OUT_PORT=ROOT/f'{PFX}_Portfolio.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
MAJOR=('external','development','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
RRS=(1.0,1.5,2.0)
RR_LABEL={1.0:'RR100',1.5:'RR150',2.0:'RR200'}
NOTIONAL=500.0; FEE=.40; BAR5=pd.Timedelta(minutes=5)
WINDOWS=(('W1','2020-01-01','2021-07-01',True),('W2','2021-07-01','2023-01-01',True),('W3','2023-01-01','2024-07-01',True),('W4','2024-07-01','2026-01-01',True),('W5_YTD','2026-01-01','2027-01-01',False))
CLOCK_MIN={'00-04':0,'04-08':240,'08-12':480,'12-16':720,'16-20':960,'20-00':1200}

def as_bool(s):
    return s if s.dtype==bool else s.astype(str).str.lower().eq('true')

def pf(vals):
    v=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); gp=float(v[v>0].sum()); gl=float(-v[v<0].sum())
    if gl==0 and gp>0:return float('inf')
    return gp/gl if gl>0 else np.nan

def metrics(d,col='pnl'):
    if d is None or len(d)==0:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v=pd.to_numeric(d[col],errors='coerce').dropna()
    return {'n':len(v),'wins':int((v>0).sum()),'wr':float((v>0).mean()),'pf':pf(v),'expectancy':float(v.mean()),'net':float(v.sum())}

def fslice(x,start,end):
    a=int(x.index.searchsorted(start,'left')); b=int(x.index.searchsorted(end,'left')); return x.iloc[a:b]

def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','rebreak_complete_ts'): d[c]=pd.to_datetime(d[c],utc=True,errors='raise')
    d['followthrough_eligible']=as_bool(d.followthrough_eligible)
    q=d[d.partition.isin(MAJOR)].copy().sort_values(['partition','obs_start']).reset_index(drop=True)
    exp={'external':149,'development':237,'reference_validation':133}
    assert len(q)==519
    for p,n in exp.items(): assert len(q[q.partition==p])==n,(p,len(q[q.partition==p]),n)
    return q

def simulate(x5,r,rr):
    entry_ts=pd.Timestamp(r.rebreak_complete_ts); end=pd.Timestamp(r.obs_end); L=float(r.L); R4=float(r.R4); tgt=L-.10*R4
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'rebreak_complete_ts':entry_ts,'H':float(r.H),'L':L,'R4':R4,'rr':rr,'variant':RR_LABEL[rr]}
    if not bool(r.followthrough_eligible) or entry_ts>=end:return {**base,'executed':False,'skip_reason':'NO_NEXT_WINDOW'}
    pos=int(x5.index.searchsorted(entry_ts,'left'))
    if pos>=len(x5) or x5.index[pos]!=entry_ts:return {**base,'executed':False,'skip_reason':'MISSING_ENTRY_BAR'}
    entry=float(x5.iloc[pos].open)
    if entry>=L:return {**base,'executed':False,'skip_reason':'NEXT_OPEN_RECLAIMED_L','entry_ts':entry_ts,'entry_px':entry}
    if entry<=tgt:return {**base,'executed':False,'skip_reason':'TARGET_ALREADY_PASSED','entry_ts':entry_ts,'entry_px':entry}
    reward=entry-tgt; stop=entry+reward/rr
    q=fslice(x5,entry_ts,end)
    exit_ts=pd.NaT; exit_px=np.nan; reason=None
    for ts,b in q.iterrows():
        hit_stop=float(b.high)>=stop; hit_tgt=float(b.low)<=tgt
        if hit_stop:
            exit_ts=ts+BAR5; exit_px=stop; reason='STOP'; break
        if hit_tgt:
            exit_ts=ts+BAR5; exit_px=tgt; reason='TP_T10'; break
    if reason is None:
        p=int(x5.index.searchsorted(end,'left'))
        if p>=len(x5) or x5.index[p]!=end:return {**base,'executed':False,'skip_reason':'MISSING_TIME_EXIT','entry_ts':entry_ts,'entry_px':entry}
        exit_ts=end; exit_px=float(x5.iloc[p].open); reason='TIME'
    pnl=(1.0-exit_px/entry)*NOTIONAL-FEE
    return {**base,'executed':True,'skip_reason':'','entry_ts':entry_ts,'entry_px':entry,'target_px':tgt,'stop_px':stop,'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'pnl':pnl}

def grid_summary(tr):
    rows=[]
    for cb in CLOCKS:
        for rr in RRS:
            g=tr[(tr.clock_block==cb)&(tr.rr==rr)&tr.executed.astype(bool)]
            for p in MAJOR: rows.append({'clock_block':cb,'rr':rr,'variant':RR_LABEL[rr],'scope':p,**metrics(g[g.partition==p])})
            rows.append({'clock_block':cb,'rr':rr,'variant':RR_LABEL[rr],'scope':'POOLED_MAJOR',**metrics(g)})
    return pd.DataFrame(rows)

def select_development(grid):
    picks=[]
    for cb in CLOCKS:
        g=grid[(grid.clock_block==cb)&(grid.scope=='development')].copy()
        g['eligible']=(g.n>=25)&(g.wr>=.65)&(g.pf>=1.30)&(g.expectancy>0)
        e=g[g.eligible].copy()
        if e.empty:
            picks.append({'clock_block':cb,'selected':False,'variant':'','rr':np.nan,'dev_n':0,'dev_wr':np.nan,'dev_pf':np.nan,'dev_net':0.0}); continue
        e['rr_tie']=e.rr
        z=e.sort_values(['pf','wr','expectancy','n','rr_tie'],ascending=[False,False,False,False,False]).iloc[0]
        picks.append({'clock_block':cb,'selected':True,'variant':z.variant,'rr':float(z.rr),'dev_n':int(z.n),'dev_wr':float(z.wr),'dev_pf':float(z.pf),'dev_net':float(z.net)})
    return pd.DataFrame(picks)

def between(d,a,z):
    aa=pd.Timestamp(a,tz='UTC'); zz=pd.Timestamp(z,tz='UTC'); return d[(d.entry_ts>=aa)&(d.entry_ts<zz)].copy()

def stress(g,bps):
    f=bps/10000.0; x=g.copy(); en=x.entry_px.astype(float)*(1-f); ex=x.exit_px.astype(float)*(1+f); x['pnl_stress']=(1-ex/en)*NOTIONAL-FEE; return metrics(x,'pnl_stress')

def current_control(x5):
    raw,locked,base=dt.build_long(x5); rawL=dt.normalize_long(raw)
    sc=dt.build_shorts(x5); sh=dt.normalize_short(sc); s20=sh[sh.clock_min_norm==1200].copy()
    full=pd.concat([rawL,s20],ignore_index=True); lock=dt.lock_rows(full,'B27DZ_CONTROL'); acc=lock[lock.accepted_portfolio.astype(bool)].copy(); m=metrics(dt.pooled(acc))
    assert m['n']==283 and abs(m['net']-367.49)<=.30,(m)
    return full,acc,m

def main():
    x5,cov=dt.dq.dn.dl.dj.b21.load5(); src=load_source(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    rows=[]
    for r in src.itertuples(index=False):
        for rr in RRS: rows.append(simulate(x5,r,rr))
    tr=pd.DataFrame(rows); tr['executed']=tr.executed.fillna(False).astype(bool)
    for c in ('entry_ts','exit_ts'):
        if c in tr.columns: tr[c]=pd.to_datetime(tr[c],utc=True,errors='coerce')
    tr.to_csv(OUT_TR,index=False)
    grid=grid_summary(tr); picks=select_development(grid)

    win_rows=[]; slip_rows=[]; port_rows=[]; verdict_rows=[]
    control_full,control_acc,control_m=current_control(x5); control_ids=set(dt.pooled(control_acc).candidate_id.astype(str))
    for p in picks.itertuples(index=False):
        if not p.selected:
            verdict_rows.append({'clock_block':p.clock_block,'selected_variant':'','replication_pass':False,'stability_pass':False,'slippage_pass':False,'portfolio_pass':False,'survivor':False}); continue
        rr=float(p.rr); g=tr[(tr.clock_block==p.clock_block)&(tr.rr==rr)&tr.executed].copy()
        ext=metrics(g[g.partition=='external']); val=metrics(g[g.partition=='reference_validation'])
        repl=bool(ext['n']>=15 and ext['wr']>=.60 and ext['pf']>=1.20 and ext['expectancy']>0 and val['n']>=15 and val['wr']>=.60 and val['pf']>=1.20 and val['expectancy']>0)
        passes=0; bad=False
        for wn,a,z,completed in WINDOWS:
            m=metrics(between(g,a,z)); wp=bool(m['n']>=5 and m['net']>0 and m['pf']>=1.05)
            if completed: passes+=int(wp); bad=bad or bool(m['n']>=5 and pd.notna(m['pf']) and m['pf']<.70)
            win_rows.append({'clock_block':p.clock_block,'variant':p.variant,'window':wn,'completed':completed,**m,'pass':wp})
        stab=bool(passes>=3 and not bad)
        sm={}
        for bps in (0,2,5,10):
            m=stress(g,bps); slip_rows.append({'clock_block':p.clock_block,'variant':p.variant,'bps':bps,**m});
            if bps==5: sm=m
        slipok=bool(sm['wr']>=.60 and sm['pf']>=1.20 and sm['net']>0)

        # portfolio test only if standalone prereg gates pass
        portok=False; displaced=0; inc_n=0; inc_net=0.0; comb=control_m
        if repl and stab and slipok:
            cand=g[['partition','entry_ts','exit_ts','pnl']].copy().rename(columns={'exit_ts':'exit_ts_norm'}); cand['side']='SHORT'; cand['source']='POST_REBREAK_'+p.clock_block; cand['clock_min_norm']=CLOCK_MIN[p.clock_block]
            cand['candidate_id']=cand.partition.astype(str)+'|POSTRB|'+p.clock_block+'|'+cand.entry_ts.astype(str)
            lk=dt.lock_rows(pd.concat([control_full,cand],ignore_index=True),'B27DZ_'+p.clock_block); ac=lk[lk.accepted_portfolio.astype(bool)].copy(); comb=metrics(dt.pooled(ac))
            acc_ids=set(dt.pooled(ac).candidate_id.astype(str)); displaced=len(control_ids-acc_ids)
            acand=dt.pooled(ac[ac.source=='POST_REBREAK_'+p.clock_block]); im=metrics(acand); inc_n=im['n']; inc_net=im['net']
            portok=bool(comb['net']>control_m['net'] and displaced<=math.floor(.02*283) and inc_net>0)
        port_rows.append({'clock_block':p.clock_block,'variant':p.variant,'control_n':control_m['n'],'control_wr':control_m['wr'],'control_pf':control_m['pf'],'control_net':control_m['net'],'combined_n':comb['n'],'combined_wr':comb['wr'],'combined_pf':comb['pf'],'combined_net':comb['net'],'incremental_n':inc_n,'incremental_net':inc_net,'displaced_current_n':displaced,'portfolio_pass':portok})
        survivor=bool(repl and stab and slipok and portok)
        verdict_rows.append({'clock_block':p.clock_block,'selected_variant':p.variant,'replication_pass':repl,'stability_pass':stab,'slippage_pass':slipok,'portfolio_pass':portok,'survivor':survivor,'external_n':ext['n'],'external_wr':ext['wr'],'external_pf':ext['pf'],'external_net':ext['net'],'validation_n':val['n'],'validation_wr':val['wr'],'validation_pf':val['pf'],'validation_net':val['net'],'completed_windows_pass':passes})

    wins=pd.DataFrame(win_rows); slips=pd.DataFrame(slip_rows); ports=pd.DataFrame(port_rows); verdict=pd.DataFrame(verdict_rows)
    grid.to_csv(OUT_GRID,index=False); wins.to_csv(OUT_WIN,index=False); slips.to_csv(OUT_SLIP,index=False); ports.to_csv(OUT_PORT,index=False)
    survivors=int(verdict.survivor.sum()) if len(verdict) else 0; status=f'B27DZ_{survivors}_POST_REBREAK_CLOCKS_SURVIVE'; OUT_STATUS.write_text(status+'\n')

    def pct(x): return '-' if pd.isna(x) else f'{100*x:.1f}%'
    def num(x): return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{x:.2f}')
    def usd(x): return f'${x:+.2f}'
    lines=['# B27DZ — 24H Post-Rebreak SHORT Economic Discovery — Result','',f'5m rows: **{len(x5):,}**; coverage **{cov:.4%}**. Exact B27CI source identity: **519** rebreak events.','',f'Current pre-B27DX control reproduced: **N={control_m["n"]}, WR={pct(control_m["wr"])}, PF={num(control_m["pf"])}, net={usd(control_m["net"])}**.','', '## Development-selected lane per 4H clock','', '| Clock | Variant | Dev N | WR | PF | Net | Ext N/WR/PF | Val N/WR/PF | WF | 5bps WR/PF/Net | Portfolio | Survivor |','|---|---|---:|---:|---:|---:|---|---|---:|---|---|---|']
    for p in picks.itertuples(index=False):
        v=verdict[verdict.clock_block==p.clock_block].iloc[0]
        if not p.selected:
            lines.append(f'| {p.clock_block} | none | - | - | - | - | - | - | - | - | - | **NO** |'); continue
        s5=slips[(slips.clock_block==p.clock_block)&(slips.bps==5)].iloc[0]
        lines.append(f'| {p.clock_block} | {p.variant} | {p.dev_n} | {pct(p.dev_wr)} | {num(p.dev_pf)} | {usd(p.dev_net)} | {int(v.external_n)}/{pct(v.external_wr)}/{num(v.external_pf)} | {int(v.validation_n)}/{pct(v.validation_wr)}/{num(v.validation_pf)} | {int(v.completed_windows_pass)}/4 | {pct(s5.wr)}/{num(s5.pf)}/{usd(s5.net)} | {"PASS" if v.portfolio_pass else "FAIL"} | **{"YES" if v.survivor else "NO"}** |')
    lines += ['',f'**Status: `{status}`.**','', 'No post-result tuning is permitted inside B27DZ. Any survivor remains reused-historical evidence and still requires independent raw-event parity / forward shadow before live use. If zero survive, this mechanism is rejected under the frozen T10 + RR lanes.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
