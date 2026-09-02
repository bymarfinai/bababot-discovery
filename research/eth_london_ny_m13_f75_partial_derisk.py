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
VARIANTS={'BASE_F50':0.0,'F75_CUT25':.25,'F75_CUT50':.50,'F75_CUT75':.75}

M5_AUDIT=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
M8_TRADES=ROOT/'ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX_Trades.csv'
M12_STATUS=ROOT/'ETH_LONDON_NY_M12_DEEP_EXIT_SECONDARY_REENTRY_Status.txt'
PFX='ETH_LONDON_NY_M13_F75_PARTIAL_DERISK'
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
    if M12_STATUS.exists(): assert M12_STATUS.read_text().strip()=='ETH_LONDON_NY_M12_NO_SUPPORTED_REENTRY_ECONOMIC_VARIANT'
    a=pd.read_csv(M5_AUDIT)
    a=a[(a.variant=='EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('entry_bar_start','session_end'):
        a[c]=pd.to_datetime(a[c],utc=True,errors='coerce')
    for c in ('H','L','R','entry_px'):
        a[c]=pd.to_numeric(a[c],errors='raise')
    a['cohort_id']=a.partition.astype(str)+'|'+a.date_utc.astype(str)+'|'+a.entry_bar_start.astype(str)
    assert len(a)==95 and a.cohort_id.is_unique and (a.R>0).all()
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)

def base_path(x,start,end,target,stop):
    q=fast_slice(x,start,end)
    assert len(q)>0 and q.index[0]==start and end in x.index
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            return dict(reason='TARGET',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(target))
        if float(b.close)<stop:
            return dict(reason='CLOSE_INVALIDATION',exit_bar_start=ts,exit_ts=ts+BAR5,exit_px=float(b.close))
    return dict(reason='TIME_EXIT',exit_bar_start=end,exit_ts=end,exit_px=float(x.loc[end].open))

def residual_path(x,start,end,target,stop):
    if start>=end:
        return dict(reason='TIME_EXIT',exit_bar_start=end,exit_ts=end,exit_px=float(x.loc[end].open))
    return base_path(x,start,end,target,stop)

def frac_pnl(entry_px,exit_px,reason,bps,fraction):
    if fraction<=0:return 0.0
    k=float(bps)/10000.0
    ep=float(entry_px)*(1.0+k)
    xp=float(exit_px) if reason=='TARGET' else float(exit_px)*(1.0-k)
    return NOTIONAL*float(fraction)*(xp/ep-1.0)-FEE*float(fraction)

def simulate(x,r,variant):
    cut=float(VARIANTS[variant])
    H=float(r.H); L=float(r.L); R=float(r.R)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end); ep=float(r.entry_px)
    target=H+TARGET_EXT*R; stop=L+F50*R; f75=L+F75*R
    if cut==0:
        z=base_path(x,start,end,target,stop)
        return dict(derisk_event=False,derisk_executed=False,derisk_signal_bar=pd.NaT,derisk_bar_start=pd.NaT,derisk_px=np.nan,
                    cut_fraction=0.0,residual_fraction=1.0,partial_reason='',partial_exit_px=np.nan,
                    residual_reason=z['reason'],residual_exit_bar_start=z['exit_bar_start'],residual_exit_ts=z['exit_ts'],residual_exit_px=z['exit_px'])

    q=fast_slice(x,start,end)
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            return dict(derisk_event=False,derisk_executed=False,derisk_signal_bar=pd.NaT,derisk_bar_start=pd.NaT,derisk_px=np.nan,
                        cut_fraction=0.0,residual_fraction=1.0,partial_reason='',partial_exit_px=np.nan,
                        residual_reason='TARGET',residual_exit_bar_start=ts,residual_exit_ts=ts+BAR5,residual_exit_px=float(target))
        if float(b.close)<stop:
            return dict(derisk_event=False,derisk_executed=False,derisk_signal_bar=pd.NaT,derisk_bar_start=pd.NaT,derisk_px=np.nan,
                        cut_fraction=0.0,residual_fraction=1.0,partial_reason='',partial_exit_px=np.nan,
                        residual_reason='CLOSE_INVALIDATION',residual_exit_bar_start=ts,residual_exit_ts=ts+BAR5,residual_exit_px=float(b.close))
        if float(b.close)<f75:
            action=ts+BAR5
            if action>=end:
                z=base_path(x,start,end,target,stop)
                return dict(derisk_event=True,derisk_executed=False,derisk_signal_bar=ts,derisk_bar_start=pd.NaT,derisk_px=np.nan,
                            cut_fraction=0.0,residual_fraction=1.0,partial_reason='',partial_exit_px=np.nan,
                            residual_reason=z['reason'],residual_exit_bar_start=z['exit_bar_start'],residual_exit_ts=z['exit_ts'],residual_exit_px=z['exit_px'])
            px=float(x.loc[action].open)
            res=residual_path(x,action,end,target,stop)
            return dict(derisk_event=True,derisk_executed=True,derisk_signal_bar=ts,derisk_bar_start=action,derisk_px=px,
                        cut_fraction=cut,residual_fraction=1.0-cut,partial_reason='F75_PARTIAL_NEXT_OPEN',partial_exit_px=px,
                        residual_reason=res['reason'],residual_exit_bar_start=res['exit_bar_start'],residual_exit_ts=res['exit_ts'],residual_exit_px=res['exit_px'])
    z=base_path(x,start,end,target,stop)
    return dict(derisk_event=False,derisk_executed=False,derisk_signal_bar=pd.NaT,derisk_bar_start=pd.NaT,derisk_px=np.nan,
                cut_fraction=0.0,residual_fraction=1.0,partial_reason='',partial_exit_px=np.nan,
                residual_reason=z['reason'],residual_exit_bar_start=z['exit_bar_start'],residual_exit_ts=z['exit_ts'],residual_exit_px=z['exit_px'])

def calc_pnl(z,entry_px,bps):
    if z['derisk_executed']:
        p1=frac_pnl(entry_px,z['partial_exit_px'],'PARTIAL',bps,z['cut_fraction'])
        p2=frac_pnl(entry_px,z['residual_exit_px'],z['residual_reason'],bps,z['residual_fraction'])
        return p1,p2,p1+p2
    p=frac_pnl(entry_px,z['residual_exit_px'],z['residual_reason'],bps,1.0)
    return 0.0,p,p

def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=20,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':99.0,'high':99.2,'low':98.8,'close':99.0},index=idx)
    # Target takes precedence over same-bar F75 close.
    x.loc[idx[0],['high','close']]=[102.0,97.0]
    r=type('R',(),{'H':100.0,'L':90.0,'R':10.0,'entry_bar_start':idx[0],'session_end':idx[-1],'entry_px':99.0})
    z=simulate(x,r,'F75_CUT50'); assert z['residual_reason']=='TARGET' and not z['derisk_executed']
    # F50 close invalidation takes precedence over F75 partial.
    x.loc[idx[0],['high','close']]=[99.5,94.0]
    z=simulate(x,r,'F75_CUT50'); assert z['residual_reason']=='CLOSE_INVALIDATION' and not z['derisk_executed']
    # F75 signal executes next open.
    x.loc[idx[0],['high','close']]=[99.5,97.0]; x.loc[idx[1],'open']=97.2
    z=simulate(x,r,'F75_CUT50'); assert z['derisk_executed'] and z['derisk_bar_start']==idx[1]

def main():
    synthetic_tests()
    c=load_cohort(); x,cov=m1.load5('ETHUSDT'); assert cov>=.995
    rows=[]
    for r in c.itertuples(index=False):
        for v in VARIANTS:
            z=simulate(x,r,v)
            a0,b0,p0=calc_pnl(z,float(r.entry_px),0.0)
            a5,b5,p5=calc_pnl(z,float(r.entry_px),5.0)
            rows.append({'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,'variant':v,
                         'entry_bar_start':r.entry_bar_start,'entry_px':r.entry_px,'H':r.H,'L':r.L,'R':r.R,
                         **z,'partial_pnl_0':a0,'residual_pnl_0':b0,'pnl_0':p0,'partial_pnl_5':a5,'residual_pnl_5':b5,'pnl_5':p5})
    t=pd.DataFrame(rows)

    # Exact baseline parity to M8 E15/F50.
    m8=pd.read_csv(M8_TRADES)
    m8=m8[(m8.target_name=='E15')&(m8.risk_name=='F50')].copy()
    m8['exit_ts']=pd.to_datetime(m8.exit_ts,utc=True,errors='coerce')
    base=t[t.variant=='BASE_F50'].copy(); base['residual_exit_ts']=pd.to_datetime(base.residual_exit_ts,utc=True,errors='coerce')
    j=base.merge(m8[['cohort_id','exit_reason','exit_ts','exit_px','pnl_0','pnl_5']],on='cohort_id',suffixes=('_m13','_m8'),validate='one_to_one')
    parity=(len(j)==95 and (j.residual_reason==j.exit_reason).all() and (j.residual_exit_ts==j.exit_ts).all() and
            np.allclose(j.residual_exit_px,j.exit_px,rtol=0,atol=1e-9) and np.allclose(j.pnl_0_m13,j.pnl_0_m8,rtol=0,atol=1e-9) and np.allclose(j.pnl_5_m13,j.pnl_5_m8,rtol=0,atol=1e-9))

    # Attach baseline PnL for saved/surrendered diagnostics.
    bp=base[['cohort_id','pnl_0','pnl_5']].rename(columns={'pnl_0':'baseline_pnl_0','pnl_5':'baseline_pnl_5'})
    t=t.merge(bp,on='cohort_id',how='left',validate='many_to_one')
    t['delta_vs_base_0']=t.pnl_0-t.baseline_pnl_0
    t['delta_vs_base_5']=t.pnl_5-t.baseline_pnl_5
    t.to_csv(OUT_TRADES,index=False)

    chronology=bool((pd.to_datetime(t.loc[t.derisk_executed,'derisk_bar_start'],utc=True)==pd.to_datetime(t.loc[t.derisk_executed,'derisk_signal_bar'],utc=True)+BAR5).all())
    fractions=bool(np.allclose(t.cut_fraction+t.residual_fraction,1.0,rtol=0,atol=1e-12))
    audit=pd.DataFrame([
        {'check':'cohort_95_x_4','value':len(t),'expected':380,'pass':len(t)==380},
        {'check':'m8_base_e15_f50_exact_parity','value':int(parity),'pass':bool(parity)},
        {'check':'raw_coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'derisk_next_open_chronology','value':int(chronology),'pass':chronology},
        {'check':'fractions_sum_one','value':int(fractions),'pass':fractions},
        {'check':'max_one_row_per_setup_variant','value':int(t.groupby(['cohort_id','variant']).size().max()==1),'pass':bool(t.groupby(['cohort_id','variant']).size().max()==1)},
    ])
    audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    sums=[]
    for v in VARIANTS:
        for p in (*PARTS,'POOLED_MAJOR'):
            q=t[t.variant==v].copy(); q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
            q=q.sort_values('entry_bar_start')
            m0=metrics(q,'pnl_0'); m5=metrics(q,'pnl_5')
            losers=q[q.baseline_pnl_0<0]; winners=q[q.baseline_pnl_0>0]
            saved=float(losers.delta_vs_base_0.mean()) if len(losers) else np.nan
            surrender=float((-winners.delta_vs_base_0).mean()) if len(winners) else np.nan
            sums.append({'partition':p,'variant':v,**{f'{k}_0':val for k,val in m0.items()},**{f'{k}_5':val for k,val in m5.items()},
                         'derisk_n':int(q.derisk_executed.sum()),'avg_loss_saved_on_base_loser_0':saved,'avg_profit_surrendered_on_base_winner_0':surrender})
    s=pd.DataFrame(sums)

    passes={}
    for v in ('F75_CUT25','F75_CUT50','F75_CUT75'):
        majors=s[(s.variant==v)&s.partition.isin(MAJOR)]
        dev=s[(s.variant==v)&(s.partition=='development')].iloc[0]
        ext=s[(s.variant==v)&(s.partition=='external')].iloc[0]
        ref=s[(s.variant==v)&(s.partition=='reference_validation')].iloc[0]
        pool=s[(s.variant==v)&(s.partition=='POOLED_MAJOR')].iloc[0]
        ok=bool(audit_ok and len(majors)==3 and (majors.n_0>=15).all() and (majors.wr_0>=.70).all() and
                dev.pf_0>=1.0 and dev.expectancy_0>0 and dev.net_0>0 and
                ext.pf_0>1.0 and ext.net_0>0 and ref.pf_0>1.0 and ref.net_0>0 and
                pool.wr_0>=.72 and pool.pf_0>=1.30 and pool.expectancy_0>0 and pool.net_0>0 and pool.pf_5>1.0 and pool.net_5>0)
        passes[v]=ok; s.loc[s.variant==v,'screen_pass']=ok
    s['screen_pass']=s['screen_pass'].fillna(False)
    s.to_csv(OUT_SUM,index=False)

    passed=s[(s.partition=='POOLED_MAJOR')&s.variant.isin(passes)&s.screen_pass].copy()
    if len(passed):
        rank=[]
        for v in passed.variant:
            d=s[(s.partition=='development')&(s.variant==v)].iloc[0]
            p=s[(s.partition=='POOLED_MAJOR')&(s.variant==v)].iloc[0]
            rank.append((v,d.pf_0,d.wr_0,p.wr_0,p.pf_5))
        best=sorted(rank,key=lambda x:(x[1],x[2],x[3],x[4]),reverse=True)[0][0]
        status='ETH_LONDON_NY_M13_PARTIAL_DERISK_SUPPORTED'
    else:
        best='none'; status='ETH_LONDON_NY_M13_NO_SUPPORTED_PARTIAL_DERISK'

    pool=s[s.partition=='POOLED_MAJOR']; dev=s[s.partition=='development']
    lines=['# ETH London -> New York M13 F75 Partial De-risk — Result','',f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen benchmark: **F90 EARLY_RECLAIM -> E15 / F50**. F75 partial reductions execute causally at the next raw 5m open; no re-entry.','',
           f'- Cohort: **95 setups**.','- M8 E15/F50 exact baseline parity: **PASS**.' if parity else '- M8 E15/F50 exact baseline parity: **FAIL**.',
           f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Pooled-major economics','',
           '| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | F75 reductions | Loss saved/base loser | Profit surrendered/base winner | Pass |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in pool.itertuples(index=False):
        lab='baseline' if r.variant=='BASE_F50' else ('YES' if bool(r.screen_pass) else 'NO')
        lines.append(f'| {r.variant} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.derisk_n)} | {num(r.avg_loss_saved_on_base_loser_0)} | {num(r.avg_profit_surrendered_on_base_winner_0)} | {lab} |')
    lines += ['','## Development economics','',
              '| Variant | N | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | F75 reductions |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in dev.itertuples(index=False):
        lines.append(f'| {r.variant} | {int(r.n_0)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {int(r.derisk_n)} |')
    lines += ['','## Decision','',f'**Status: {status}**','',f'- Best supported variant: **{best}**.',
              '- No additional fraction, level, timeout, re-entry, trailing stop, leverage, or portfolio rule was tested.']
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
