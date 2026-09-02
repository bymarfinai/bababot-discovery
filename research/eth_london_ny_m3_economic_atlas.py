#!/usr/bin/env python3
from __future__ import annotations

import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PFX='ETH_LONDON_NY_M3_ECONOMIC_ATLAS'
M2_ENTRIES=ROOT/'ETH_LONDON_NY_PRE_H2_RETRACE_M2_Entries.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_BEST=ROOT/f'{PFX}_EntryLeaders.csv'
OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

spec=importlib.util.spec_from_file_location('m1',HERE/'eth_london_ny_liquidity_pressure_m1.py')
m1=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(m1)

BAR5=pd.Timedelta(minutes=5)
PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
FRACS={'F95':.95,'F90':.90,'F85':.85,'F80':.80,'F75':.75}
TARGETS={'E10':.10,'E15':.15,'E20':.20}
RISKS={'D30':.30,'D40':.40,'D50':.50,'D60':.60}
NOTIONAL=500.0
FEE=.40


def pf(vals):
    a=np.asarray(list(vals),dtype=float)
    if len(a)==0:return np.nan
    gp=float(a[a>0].sum()) if np.any(a>0) else 0.0
    gl=float(-a[a<0].sum()) if np.any(a<0) else 0.0
    if gl==0 and gp>0:return math.inf
    return gp/gl if gl>0 else np.nan


def metrics(df,col):
    v=pd.to_numeric(df[col],errors='coerce').dropna().to_numpy(float)
    if not len(v):return dict(n=0,wins=0,wr=np.nan,pf=np.nan,expectancy=np.nan,net=0.0,max_ls=0,median_win=np.nan,median_loss=np.nan)
    cur=mx=0
    for z in v:
        if z<0:cur+=1;mx=max(mx,cur)
        else:cur=0
    return dict(n=len(v),wins=int((v>0).sum()),wr=float((v>0).mean()),pf=pf(v),expectancy=float(v.mean()),net=float(v.sum()),max_ls=mx,
                median_win=float(np.median(v[v>0])) if np.any(v>0) else np.nan,
                median_loss=float(np.median(v[v<0])) if np.any(v<0) else np.nan)


def load_entries():
    e=pd.read_csv(M2_ENTRIES)
    e=e[e.filled.astype(str).str.lower().eq('true')].copy()
    for c in ('signal_ts','eligible_start','h2_bar_start','opposite_break_bar_start','entry_ts'):
        e[c]=pd.to_datetime(e[c],utc=True,errors='coerce')
    e['entry_fraction']=pd.to_numeric(e.entry_fraction,errors='raise')
    e['entry_px']=pd.to_numeric(e.entry_px,errors='raise')
    e['H']=pd.to_numeric(e.H,errors='raise'); e['L']=pd.to_numeric(e.L,errors='raise')
    assert e.entry_ts.notna().all()
    assert e.entry_name.isin(FRACS).all()
    for r in e.itertuples(index=False):
        exp=float(r.L)+FRACS[str(r.entry_name)]*(float(r.H)-float(r.L))
        assert abs(float(r.entry_px)-exp)<=1e-9*max(1.0,abs(exp))
        if pd.notna(r.h2_bar_start): assert pd.Timestamp(r.entry_ts)<pd.Timestamp(r.h2_bar_start)
    return e.sort_values(['partition','entry_name','entry_ts']).reset_index(drop=True)


def fast_slice(x,a,z):
    i=int(x.index.searchsorted(a,side='left')); j=int(x.index.searchsorted(z,side='left'))
    return x.iloc[i:j]


def score_one(x,r,tname,text,rname,risk,bps=0.0):
    H=float(r.H); L=float(r.L); R=H-L; ep=float(r.entry_px); ets=pd.Timestamp(r.entry_ts)
    target=H+text*R
    boundary=L+(float(r.entry_fraction)-risk)*R
    day=pd.Timestamp(str(r.date_utc),tz='UTC')
    session_end=day+pd.Timedelta(hours=20)
    if session_end not in x.index: return None
    q=fast_slice(x,ets,session_end)
    if q.empty or q.index[0]!=ets:return None
    reason=None; xp=None; exit_ts=pd.NaT
    # Fill bar: limit fill occurred intrabar; only completed-close invalidation is causal afterward.
    r0=q.iloc[0]
    if float(r0.close)<boundary:
        reason='CLOSE_INVALIDATION'; xp=float(r0.close); exit_ts=ets+BAR5
    else:
        for ts,b in q.iloc[1:].iterrows():
            ts=pd.Timestamp(ts)
            if float(b.high)>=target:
                reason='TARGET'; xp=float(target); exit_ts=ts+BAR5; break
            if float(b.close)<boundary:
                reason='CLOSE_INVALIDATION'; xp=float(b.close); exit_ts=ts+BAR5; break
    if reason is None:
        xp=float(x.loc[session_end].open); reason='TIME_EXIT'; exit_ts=session_end
    k=float(bps)/10000.0
    entry_exec=ep*(1.0+k)
    exit_exec=float(xp) if reason=='TARGET' else float(xp)*(1.0-k)
    pnl=NOTIONAL*(exit_exec/entry_exec-1.0)-FEE
    return dict(target_name=tname,target_ext=text,risk_name=rname,risk_R=risk,target_px=target,boundary_px=boundary,
                exit_ts=exit_ts,exit_px=float(xp),exit_reason=reason,pnl=float(pnl),hold_min=float((exit_ts-ets)/pd.Timedelta(minutes=1)))


def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=73,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':98.5,'high':99.0,'low':98.0,'close':98.5},index=idx)
    x.loc[idx[1],['high','close']]=[101.2,100.5]
    row=pd.Series({'H':100.,'L':90.,'entry_px':98.5,'entry_fraction':.85,'entry_ts':idx[0],'date_utc':'2026-01-05'})
    a=score_one(x,row,'E10',.10,'D50',.50,0)
    assert a and a['exit_reason']=='TARGET' and abs(a['exit_px']-101.0)<1e-12
    x2=x.copy(); x2.loc[idx[0],'close']=93.0
    b=score_one(x2,row,'E20',.20,'D50',.50,0)
    assert b and b['exit_reason']=='CLOSE_INVALIDATION' and b['exit_ts']==idx[0]+BAR5
    x3=x.copy(); x3.loc[idx[1],['high','close']]=[101.2,92.0]
    c=score_one(x3,row,'E10',.10,'D50',.50,0)
    assert c and c['exit_reason']=='TARGET'


def fmt(v,n=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{n}f}'

def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    synthetic_tests()
    e=load_entries()
    x,cov=m1.load5('ETHUSDT')
    rows=[]
    for r in e.itertuples(index=False):
        for tn,te in TARGETS.items():
            for rn,rk in RISKS.items():
                d0=score_one(x,r,tn,te,rn,rk,0.0); d5=score_one(x,r,tn,te,rn,rk,5.0)
                if d0 is None or d5 is None:continue
                assert d0['exit_ts']==d5['exit_ts'] and d0['exit_reason']==d5['exit_reason']
                rows.append({'partition':r.partition,'date_utc':r.date_utc,'window_id':r.window_id,'entry_name':r.entry_name,
                             'entry_fraction':r.entry_fraction,'entry_ts':r.entry_ts,'entry_px':r.entry_px,'H':r.H,'L':r.L,
                             'target_name':tn,'risk_name':rn,'target_px':d0['target_px'],'boundary_px':d0['boundary_px'],
                             'exit_ts':d0['exit_ts'],'exit_px':d0['exit_px'],'exit_reason':d0['exit_reason'],'hold_min':d0['hold_min'],
                             'pnl_0':d0['pnl'],'pnl_5':d5['pnl']})
    t=pd.DataFrame(rows)
    t.to_csv(OUT_TRADES,index=False)

    expected=len(e)*len(TARGETS)*len(RISKS)
    audit=pd.DataFrame([
        {'check':'m2_filled_rows_loaded','value':len(e),'pass':len(e)>0},
        {'check':'full_grid_rows','value':len(t),'expected':expected,'pass':len(t)==expected},
        {'check':'eth_coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'entry_geometry','value':1,'pass':True},
        {'check':'chronology','value':int((pd.to_datetime(t.exit_ts,utc=True)>pd.to_datetime(t.entry_ts,utc=True)).all()),'pass':bool((pd.to_datetime(t.exit_ts,utc=True)>pd.to_datetime(t.entry_ts,utc=True)).all())},
    ])
    audit.to_csv(OUT_AUDIT,index=False)
    audit_ok=bool(audit['pass'].all())

    sums=[]
    for en in FRACS:
        for tn in TARGETS:
            for rn in RISKS:
                for p in (*PARTS,'POOLED_MAJOR'):
                    q=t[(t.entry_name==en)&(t.target_name==tn)&(t.risk_name==rn)]
                    if p=='POOLED_MAJOR':q=q[q.partition.isin(MAJOR)]
                    else:q=q[q.partition==p]
                    m0=metrics(q.sort_values('entry_ts'),'pnl_0'); m5=metrics(q.sort_values('entry_ts'),'pnl_5')
                    sums.append({'partition':p,'entry_name':en,'target_name':tn,'risk_name':rn,
                                 **{f'{k}_0':v for k,v in m0.items()},**{f'{k}_5':v for k,v in m5.items()},
                                 'tp':int((q.exit_reason=='TARGET').sum()),'stop':int((q.exit_reason=='CLOSE_INVALIDATION').sum()),
                                 'time_exit':int((q.exit_reason=='TIME_EXIT').sum()),'median_hold':float(q.hold_min.median()) if len(q) else np.nan})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUM,index=False)

    pass_rows=[]
    for en in FRACS:
        for tn in TARGETS:
            for rn in RISKS:
                majors=s[(s.entry_name==en)&(s.target_name==tn)&(s.risk_name==rn)&s.partition.isin(MAJOR)]
                pooled=s[(s.entry_name==en)&(s.target_name==tn)&(s.risk_name==rn)&(s.partition=='POOLED_MAJOR')].iloc[0]
                screen=bool(len(majors)==3 and (majors.n_0>=30).all() and (majors.wr_0>=.70).all() and (majors.pf_0>=1.20).all() and (majors.expectancy_0>0).all() and (majors.net_0>0).all() and pooled.pf_5>1 and pooled.net_5>0)
                pass_rows.append({'entry_name':en,'target_name':tn,'risk_name':rn,'screen_pass':screen,'pooled_n':int(pooled.n_0),
                                  'pooled_wr':pooled.wr_0,'pooled_pf':pooled.pf_0,'pooled_exp':pooled.expectancy_0,'pooled_net':pooled.net_0,
                                  'wr_5':pooled.wr_5,'pf_5':pooled.pf_5,'exp_5':pooled.expectancy_5,'net_5':pooled.net_5})
    rank=pd.DataFrame(pass_rows)
    leaders=[]
    for en in FRACS:
        q=rank[rank.entry_name==en].sort_values(['pooled_wr','pooled_pf','pooled_exp'],ascending=False).iloc[0]
        leaders.append(q.to_dict())
    leaders=pd.DataFrame(leaders); leaders.to_csv(OUT_BEST,index=False)
    passed=rank[rank.screen_pass].sort_values(['pooled_wr','pooled_pf','pooled_exp','pf_5'],ascending=False)
    observed=rank.sort_values(['pooled_wr','pooled_pf','pooled_exp'],ascending=False).iloc[0]
    formal=passed.iloc[0] if len(passed) else None
    status='ETH_LONDON_NY_M3_ECONOMIC_CELL_SUPPORTED' if audit_ok and formal is not None else 'ETH_LONDON_NY_M3_NO_SUPPORTED_ECONOMIC_CELL'

    lines=['# ETH London -> New York M3 Economic Atlas — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen structure: **London->NY LONG K1 OPP0 · causal leave · M2 pre-H2 F95/F90/F85/F80/F75 entries**.','',
           f'- M2 filled entries loaded: **{len(e)}**.',f'- Full 60-cell chronology audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Best observed cell within each entry level (ranked by pooled actual WR)','',
           '| Entry | Target | Risk | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Formal pass |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in leaders.sort_values('pooled_wr',ascending=False).itertuples(index=False):
        lines.append(f'| {r.entry_name} | {r.target_name} | {r.risk_name} | {int(r.pooled_n)} | {pct(r.pooled_wr)} | {fmt(r.pooled_pf)} | {fmt(r.pooled_exp)} | {fmt(r.pooled_net)} | {pct(r.wr_5)} | {fmt(r.pf_5)} | {fmt(r.net_5)} | {"PASS" if r.screen_pass else "NO"} |')
    lines += ['','## All formal SCREEN_PASS cells','']
    if len(passed):
        lines += ['| Rank | Entry | Target | Risk | N | WR | PF | Exp | Net | 5bps PF | 5bps Net |','|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
        for i,r in enumerate(passed.itertuples(index=False),1):
            lines.append(f'| {i} | {r.entry_name} | {r.target_name} | {r.risk_name} | {int(r.pooled_n)} | {pct(r.pooled_wr)} | {fmt(r.pooled_pf)} | {fmt(r.pooled_exp)} | {fmt(r.pooled_net)} | {fmt(r.pf_5)} | {fmt(r.net_5)} |')
    else: lines.append('**None.**')
    lines += ['','## Decision','',f'**Status: {status}**','',
              f'- Descriptive pooled WR leader: **{observed.entry_name}/{observed.target_name}/{observed.risk_name} — WR {pct(observed.pooled_wr)}, PF {fmt(observed.pooled_pf)}, expectancy {fmt(observed.pooled_exp)}, net {fmt(observed.pooled_net)}**.',
              '- Descriptive leaders are not promoted when the frozen three-partition screen fails.',
              '- No runner, clock expansion, portfolio lock, leverage, or post-result threshold tuning was performed.']
    if formal is not None:
        lines.append(f'- Formal WR-first economic leader among SCREEN_PASS cells: **{formal.entry_name}/{formal.target_name}/{formal.risk_name} — WR {pct(formal.pooled_wr)}, PF {fmt(formal.pooled_pf)}, expectancy {fmt(formal.pooled_exp)}, net {fmt(formal.pooled_net)}**.')
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':main()
