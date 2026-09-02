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
RISKS={'F55':.55,'F50':.50}
NOTIONAL=500.0
FEE=.40

M5_AUDIT=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
PFX='ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'
OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'

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
    if not len(v): return dict(n=0,wins=0,wr=np.nan,pf=np.nan,expectancy=np.nan,net=0.0,max_ls=0,median_win=np.nan,median_loss=np.nan)
    cur=mx=0
    for z in v:
        if z<0: cur+=1; mx=max(mx,cur)
        else: cur=0
    return dict(n=len(v),wins=int((v>0).sum()),wr=float((v>0).mean()),pf=pf(v),expectancy=float(v.mean()),net=float(v.sum()),max_ls=mx,
                median_win=float(np.median(v[v>0])) if np.any(v>0) else np.nan,
                median_loss=float(np.median(v[v<0])) if np.any(v<0) else np.nan)

def load_cohort():
    if M5_STATUS.exists():
        assert M5_STATUS.read_text().strip()=='ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS'
    a=pd.read_csv(M5_AUDIT)
    a=a[(a.variant=='EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('touch_bar_start','confirmation_bar_start','entry_bar_start','terminal_bar_start','h2_bar_start','session_end'):
        a[c]=pd.to_datetime(a[c],utc=True,errors='coerce')
    for c in ('H','L','R','entry_px','realized_entry_fraction'):
        a[c]=pd.to_numeric(a[c],errors='raise')
    a['cohort_id']=a.partition.astype(str)+'|'+a.date_utc.astype(str)+'|'+a.entry_bar_start.astype(str)
    assert a.cohort_id.is_unique and len(a)>0
    assert (a.R>0).all() and a.entry_bar_start.notna().all()
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)

def score_one(x,r,tname,te,rname,rf,bps=0.0):
    H=float(r.H); L=float(r.L); R=float(r.R); ep=float(r.entry_px)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end)
    target=H+te*R; boundary=L+rf*R
    assert target>H and boundary<ep
    if end not in x.index:return None
    q=fast_slice(x,start,end)
    if q.empty or q.index[0]!=start:return None
    reason=None; xp=None; exit_ts=pd.NaT; exit_bar=pd.NaT
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            reason='TARGET'; xp=float(target); exit_ts=ts+BAR5; exit_bar=ts; break
        if float(b.close)<boundary:
            reason='CLOSE_INVALIDATION'; xp=float(b.close); exit_ts=ts+BAR5; exit_bar=ts; break
    if reason is None:
        reason='TIME_EXIT'; xp=float(x.loc[end].open); exit_ts=end; exit_bar=end
    k=float(bps)/10000.0
    entry_exec=ep*(1.0+k)
    exit_exec=float(xp) if reason=='TARGET' else float(xp)*(1.0-k)
    pnl=NOTIONAL*(exit_exec/entry_exec-1.0)-FEE
    reward=max(target-ep,0.0); risk=max(ep-boundary,1e-12)
    return dict(target_name=tname,target_ext_R=te,risk_name=rname,boundary_f=rf,target_px=target,boundary_px=boundary,
                exit_reason=reason,exit_bar_start=exit_bar,exit_ts=exit_ts,exit_px=float(xp),pnl=float(pnl),
                hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),nominal_rr=float(reward/risk))

def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=73,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':99.2,'high':99.4,'low':99.0,'close':99.2},index=idx)
    row=pd.Series({'H':100.,'L':90.,'R':10.,'entry_px':99.2,'entry_bar_start':idx[0],'session_end':idx[-1]})
    x.loc[idx[0],['high','close']]=[101.2,94.0]
    a=score_one(x,row,'E10',.10,'F55',.55,0)
    assert a and a['exit_reason']=='TARGET' and abs(a['exit_px']-101.0)<1e-12
    x2=x.copy(); x2.loc[idx[0],['high','close']]=[100.0,94.0]
    b=score_one(x2,row,'E10',.10,'F55',.55,0)
    assert b and b['exit_reason']=='CLOSE_INVALIDATION' and abs(b['exit_px']-94.0)<1e-12
    x3=x.copy(); x3.loc[idx[0],['low','close']]=[94.0,96.0]
    c=score_one(x3,row,'E15',.15,'F55',.55,0)
    assert c and c['exit_reason']!='CLOSE_INVALIDATION'

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{n}f}'

def main():
    synthetic_tests()
    c=load_cohort(); x,cov=m1.load5('ETHUSDT'); assert cov>=.995
    rows=[]
    for r in c.itertuples(index=False):
        for tn,te in TARGETS.items():
            for rn,rf in RISKS.items():
                d0=score_one(x,r,tn,te,rn,rf,0.0); d5=score_one(x,r,tn,te,rn,rf,5.0)
                assert d0 is not None and d5 is not None
                assert d0['exit_reason']==d5['exit_reason'] and d0['exit_ts']==d5['exit_ts']
                rows.append({'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,
                             'entry_bar_start':r.entry_bar_start,'entry_px':r.entry_px,'entry_fraction':r.realized_entry_fraction,
                             'H':r.H,'L':r.L,'R':r.R,'h2_bar_start':r.h2_bar_start,
                             'target_name':tn,'risk_name':rn,'target_px':d0['target_px'],'boundary_px':d0['boundary_px'],
                             'nominal_rr':d0['nominal_rr'],'exit_reason':d0['exit_reason'],'exit_bar_start':d0['exit_bar_start'],
                             'exit_ts':d0['exit_ts'],'exit_px':d0['exit_px'],'hold_min':d0['hold_min'],'pnl_0':d0['pnl'],'pnl_5':d5['pnl']})
    t=pd.DataFrame(rows); t.to_csv(OUT_TRADES,index=False)
    expected=len(c)*len(TARGETS)*len(RISKS)
    audit=pd.DataFrame([
        {'check':'m5_early_reclaim_executed','value':len(c),'pass':len(c)==95},
        {'check':'full_6_cell_grid','value':len(t),'expected':expected,'pass':len(t)==expected},
        {'check':'coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'chronology','value':int((pd.to_datetime(t.exit_ts,utc=True)>pd.to_datetime(t.entry_bar_start,utc=True)).all()),'pass':bool((pd.to_datetime(t.exit_ts,utc=True)>pd.to_datetime(t.entry_bar_start,utc=True)).all())},
    ]); audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    sums=[]
    for tn in TARGETS:
        for rn in RISKS:
            for p in (*PARTS,'POOLED_MAJOR'):
                q=t[(t.target_name==tn)&(t.risk_name==rn)].copy()
                q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
                q=q.sort_values('entry_bar_start')
                m0=metrics(q,'pnl_0'); m5=metrics(q,'pnl_5')
                sums.append({'partition':p,'target_name':tn,'risk_name':rn,
                             **{f'{k}_0':v for k,v in m0.items()},**{f'{k}_5':v for k,v in m5.items()},
                             'tp':int((q.exit_reason=='TARGET').sum()),'stop':int((q.exit_reason=='CLOSE_INVALIDATION').sum()),
                             'time_exit':int((q.exit_reason=='TIME_EXIT').sum()),'median_hold':float(q.hold_min.median()) if len(q) else np.nan,
                             'median_entry_f':float(q.entry_fraction.median()) if len(q) else np.nan,
                             'median_nominal_rr':float(q.nominal_rr.median()) if len(q) else np.nan})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUM,index=False)

    ranks=[]
    for tn in TARGETS:
        for rn in RISKS:
            majors=s[(s.target_name==tn)&(s.risk_name==rn)&s.partition.isin(MAJOR)]
            pooled=s[(s.target_name==tn)&(s.risk_name==rn)&(s.partition=='POOLED_MAJOR')].iloc[0]
            screen=bool(audit_ok and len(majors)==3 and (majors.n_0>=15).all() and (majors.wr_0>=.70).all() and
                        (majors.pf_0>=1.20).all() and (majors.expectancy_0>0).all() and (majors.net_0>0).all() and
                        pooled.wr_0>=.70 and pooled.pf_0>=1.20 and pooled.expectancy_0>0 and pooled.net_0>0 and
                        pooled.pf_5>1.0 and pooled.net_5>0)
            ranks.append({'target_name':tn,'risk_name':rn,'screen_pass':screen,'n':int(pooled.n_0),'wr':pooled.wr_0,'pf':pooled.pf_0,
                          'exp':pooled.expectancy_0,'net':pooled.net_0,'wr_5':pooled.wr_5,'pf_5':pooled.pf_5,'exp_5':pooled.expectancy_5,'net_5':pooled.net_5,
                          'tp_rate':pooled.tp/pooled.n_0 if pooled.n_0 else np.nan,'median_rr':pooled.median_nominal_rr})
    rank=pd.DataFrame(ranks)
    passed=rank[rank.screen_pass].sort_values(['wr','pf','exp','pf_5'],ascending=False)
    leader=rank.sort_values(['wr','pf','exp'],ascending=False).iloc[0]
    formal=passed.iloc[0] if len(passed) else None
    status='ETH_LONDON_NY_M8_ECONOMIC_CELL_SUPPORTED' if formal is not None else 'ETH_LONDON_NY_M8_NO_SUPPORTED_ECONOMIC_CELL'

    lines=['# ETH London -> New York M8 F90 Early-Reclaim Economic Matrix — Result','',f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen trade: **F90 EARLY_RECLAIM entry -> E05/E10/E15 limit TP vs F55/F50 completed-close invalidation**.','',
           f'- Executed M5 cohort: **{len(c)}**.',f'- Six-cell chronology/economics audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Pooled-major six-cell comparison','',
           '| Target | Risk | N | WR | PF | Exp | Net | TP rate | Median RR | 5bps WR | 5bps PF | 5bps Net | Pass |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in rank.sort_values(['wr','pf','exp'],ascending=False).itertuples(index=False):
        lines.append(f'| {r.target_name} | {r.risk_name} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {num(r.exp)} | {num(r.net)} | {pct(r.tp_rate)} | {num(r.median_rr)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {"PASS" if r.screen_pass else "NO"} |')
    lines += ['','## Major-partition detail','',
              '| Partition | Target | Risk | N | WR | PF | Exp | Net | 5bps PF | 5bps Net |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    q=s[s.partition.isin(MAJOR)]
    for r in q.itertuples(index=False):
        lines.append(f'| {r.partition} | {r.target_name} | {r.risk_name} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {num(r.pf_5)} | {num(r.net_5)} |')
    lines += ['','## Decision','',f'**Status: {status}**','',
              f'- Descriptive pooled WR leader: **{leader.target_name}/{leader.risk_name} — WR {pct(leader.wr)}, PF {num(leader.pf)}, expectancy {num(leader.exp)}, net {num(leader.net)}**.']
    if formal is not None:
        lines.append(f'- Formal WR-first SCREEN_PASS leader: **{formal.target_name}/{formal.risk_name} — WR {pct(formal.wr)}, PF {num(formal.pf)}, expectancy {num(formal.exp)}, net {num(formal.net)}, 5bps PF {num(formal.pf_5)}, 5bps net {num(formal.net_5)}**.')
    else:
        lines.append('- **No exact cell passed the frozen three-partition economic screen.**')
    lines.append('- No runner, portfolio lock, leverage, timing/regime filter, or post-result retuning was performed.')
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
