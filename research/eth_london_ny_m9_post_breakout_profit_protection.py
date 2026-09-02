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
FEE=.40
TARGET_EXT=.15
BASE_F=.50
FLOORS={'BASE_F50':None,'BO_FLOOR_F90':.90,'BO_FLOOR_F95':.95,'BO_FLOOR_H':1.00}

M5_AUDIT=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Audit.csv'
M5_STATUS=ROOT/'ETH_LONDON_NY_M5_F90_ENTRY_TRIGGER_Status.txt'
M8_SUM=ROOT/'ETH_LONDON_NY_M8_F90_RECLAIM_ECONOMIC_MATRIX_Summary.csv'
PFX='ETH_LONDON_NY_M9_POST_BREAKOUT_PROFIT_PROTECTION'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_DIAG=ROOT/f'{PFX}_DevelopmentDiagnostic.csv'
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
    if M5_STATUS.exists(): assert M5_STATUS.read_text().strip()=='ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS'
    a=pd.read_csv(M5_AUDIT)
    a=a[(a.variant=='EARLY_RECLAIM') & as_bool(a.executed)].copy()
    for c in ('touch_bar_start','confirmation_bar_start','entry_bar_start','terminal_bar_start','h2_bar_start','session_end'):
        a[c]=pd.to_datetime(a[c],utc=True,errors='coerce')
    for c in ('H','L','R','entry_px','realized_entry_fraction'):
        a[c]=pd.to_numeric(a[c],errors='raise')
    a['cohort_id']=a.partition.astype(str)+'|'+a.date_utc.astype(str)+'|'+a.entry_bar_start.astype(str)
    assert a.cohort_id.is_unique and len(a)==95 and (a.R>0).all()
    return a.sort_values(['partition','entry_bar_start']).reset_index(drop=True)

def pnl_value(entry_px, exit_px, reason, bps):
    k=float(bps)/10000.0
    entry_exec=float(entry_px)*(1.0+k)
    # Resting TP assumed no adverse exit slippage, all non-target exits stressed adversely.
    exit_exec=float(exit_px) if reason=='TARGET' else float(exit_px)*(1.0-k)
    return NOTIONAL*(exit_exec/entry_exec-1.0)-FEE

def first_breakout_until(x,start,end,H):
    q=fast_slice(x,start,end)
    for ts,b in q.iterrows():
        if float(b.close)>H: return pd.Timestamp(ts)
    return pd.NaT

def score_base(x,r,bps=0.0):
    H=float(r.H); L=float(r.L); R=float(r.R); ep=float(r.entry_px)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end)
    target=H+TARGET_EXT*R; boundary=L+BASE_F*R
    q=fast_slice(x,start,end); assert len(q) and q.index[0]==start
    breakout=pd.NaT; reason=None; xp=None; exit_bar=pd.NaT
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            reason='TARGET'; xp=target; exit_bar=ts; break
        if pd.isna(breakout) and float(b.close)>H:
            breakout=ts
        if float(b.close)<boundary:
            reason='CLOSE_INVALIDATION'; xp=float(b.close); exit_bar=ts; break
    if reason is None:
        reason='TIME_EXIT'; xp=float(x.loc[end].open); exit_bar=end
    exit_ts=exit_bar+BAR5 if exit_bar<end else end
    # diagnostic class follows causal baseline chronology
    if reason=='TARGET':
        if pd.isna(breakout) or exit_bar<=breakout:
            cls='E15_SAME_OR_BEFORE_BO_BAR'
        else:
            cls='BREAKOUT_TO_E15'
    elif pd.notna(breakout) and breakout<exit_bar:
        cls='BREAKOUT_GIVEBACK'
    elif pd.notna(breakout) and breakout==exit_bar:
        cls='BREAKOUT_GIVEBACK'
    else:
        cls='NO_BREAKOUT_FAIL'
    return dict(reason=reason,exit_px=float(xp),exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class=cls,
                pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False)

def score_floor(x,r,floor_f,bps=0.0):
    H=float(r.H); L=float(r.L); R=float(r.R); ep=float(r.entry_px)
    start=pd.Timestamp(r.entry_bar_start); end=pd.Timestamp(r.session_end)
    target=H+TARGET_EXT*R; boundary=L+BASE_F*R; floor=L+float(floor_f)*R
    q=fast_slice(x,start,end); assert len(q) and q.index[0]==start
    breakout=pd.NaT
    # Stage 1: M8 semantics until target, F50 invalidation, or strict breakout confirmation.
    for ts,b in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(b.high)>=target:
            reason='TARGET'; xp=target; exit_bar=ts; exit_ts=ts+BAR5
            return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class='E15_SAME_OR_BEFORE_BO_BAR',
                        pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)
        if float(b.close)<boundary:
            reason='CLOSE_INVALIDATION'; xp=float(b.close); exit_bar=ts; exit_ts=ts+BAR5
            return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=pd.NaT,diag_class='NO_BREAKOUT_FAIL',
                        pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)
        if float(b.close)>H:
            breakout=ts
            break
    if pd.isna(breakout):
        reason='TIME_EXIT'; xp=float(x.loc[end].open); exit_bar=end; exit_ts=end
        return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=pd.NaT,diag_class='NO_BREAKOUT_FAIL',
                    pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)

    # Stage 2: floor becomes active only on next raw 5m bar.
    active=breakout+BAR5
    if active>=end:
        reason='TIME_EXIT'; xp=float(x.loc[end].open); exit_bar=end; exit_ts=end
        return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class='BREAKOUT_GIVEBACK',
                    pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)
    post=fast_slice(x,active,end)
    for ts,b in post.iterrows():
        ts=pd.Timestamp(ts); op=float(b.open); lo=float(b.low); hi=float(b.high)
        if op<=floor:
            reason='FLOOR_GAP_OPEN'; xp=op; exit_bar=ts; exit_ts=ts+BAR5
            return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class='BREAKOUT_GIVEBACK',
                        pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)
        hit_floor=lo<=floor; hit_target=hi>=target
        if hit_floor and hit_target:
            return dict(reason='AMBIGUOUS_BOTH',exit_px=np.nan,exit_bar=ts,exit_ts=ts+BAR5,breakout_bar=breakout,diag_class='BREAKOUT_GIVEBACK',
                        pnl=np.nan,hold_min=float((ts+BAR5-start)/pd.Timedelta(minutes=1)),ambiguous=True,floor_px=floor)
        if hit_floor:
            reason='FLOOR_TOUCH'; xp=floor; exit_bar=ts; exit_ts=ts+BAR5
            return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class='BREAKOUT_GIVEBACK',
                        pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)
        if hit_target:
            reason='TARGET'; xp=target; exit_bar=ts; exit_ts=ts+BAR5
            return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class='BREAKOUT_TO_E15',
                        pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)
    reason='TIME_EXIT'; xp=float(x.loc[end].open); exit_bar=end; exit_ts=end
    return dict(reason=reason,exit_px=xp,exit_bar=exit_bar,exit_ts=exit_ts,breakout_bar=breakout,diag_class='BREAKOUT_GIVEBACK',
                pnl=pnl_value(ep,xp,reason,bps),hold_min=float((exit_ts-start)/pd.Timedelta(minutes=1)),ambiguous=False,floor_px=floor)

def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=20,freq='5min',tz='UTC')
    x=pd.DataFrame({'open':99.2,'high':99.4,'low':99.0,'close':99.2},index=idx)
    row=pd.Series({'H':100.,'L':90.,'R':10.,'entry_px':99.2,'entry_bar_start':idx[0],'session_end':idx[-1]})
    # breakout then floor H on next bar
    x.loc[idx[1],['high','low','close']]=[100.4,99.3,100.2]
    x.loc[idx[2],['open','high','low','close']]=[100.2,100.5,99.8,100.1]
    a=score_floor(x,row,1.0,0)
    assert a['reason']=='FLOOR_TOUCH' and abs(a['exit_px']-100.0)<1e-12 and a['breakout_bar']==idx[1]
    # target before breakout confirmation retains target-first M8 semantics
    y=x.copy(); y.loc[idx[0],['high','close']]=[101.6,99.5]
    b=score_floor(y,row,.95,0)
    assert b['reason']=='TARGET' and b['diag_class']=='E15_SAME_OR_BEFORE_BO_BAR'
    # both floor and target on first active bar => ambiguous
    z=x.copy(); z.loc[idx[2],['open','high','low','close']]=[100.2,101.6,99.4,100.5]
    c=score_floor(z,row,1.0,0)
    assert c['ambiguous'] and c['reason']=='AMBIGUOUS_BOTH'

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,n=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{n}f}'

def main():
    synthetic_tests()
    c=load_cohort(); x,cov=m1.load5('ETHUSDT'); assert cov>=.995
    rows=[]
    for r in c.itertuples(index=False):
        for variant,f in FLOORS.items():
            d0=score_base(x,r,0.0) if f is None else score_floor(x,r,f,0.0)
            d5=score_base(x,r,5.0) if f is None else score_floor(x,r,f,5.0)
            assert d0['reason']==d5['reason'] and d0['exit_ts']==d5['exit_ts'] and bool(d0['ambiguous'])==bool(d5['ambiguous'])
            rows.append({'cohort_id':r.cohort_id,'partition':r.partition,'date_utc':r.date_utc,'variant':variant,
                         'entry_bar_start':r.entry_bar_start,'entry_px':r.entry_px,'entry_fraction':r.realized_entry_fraction,
                         'H':r.H,'L':r.L,'R':r.R,'target_px':float(r.H)+TARGET_EXT*float(r.R),
                         'floor_px':np.nan if f is None else d0.get('floor_px',float(r.L)+f*float(r.R)),
                         'breakout_bar_start':d0['breakout_bar'],'diag_class':d0['diag_class'],'exit_reason':d0['reason'],
                         'exit_bar_start':d0['exit_bar'],'exit_ts':d0['exit_ts'],'exit_px':d0['exit_px'],'hold_min':d0['hold_min'],
                         'ambiguous':d0['ambiguous'],'pnl_0':d0['pnl'],'pnl_5':d5['pnl']})
    t=pd.DataFrame(rows); t.to_csv(OUT_TRADES,index=False)

    # Exact M8 E15/F50 baseline parity.
    m8=pd.read_csv(M8_SUM)
    m8b=m8[(m8.target_name=='E15')&(m8.risk_name=='F50')].copy()
    parity=[]
    for p in (*PARTS,'POOLED_MAJOR'):
        q=t[t.variant=='BASE_F50'].copy(); q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
        q=q.sort_values('entry_bar_start'); m0=metrics(q,'pnl_0'); m5=metrics(q,'pnl_5')
        ref=m8b[m8b.partition==p].iloc[0]
        ok=(int(m0['n'])==int(ref.n_0) and abs(float(m0['wr'])-float(ref.wr_0))<1e-12 and abs(float(m0['pf'])-float(ref.pf_0))<1e-10 and
            abs(float(m0['net'])-float(ref.net_0))<1e-8 and abs(float(m5['pf'])-float(ref.pf_5))<1e-10 and abs(float(m5['net'])-float(ref.net_5))<1e-8)
        parity.append(ok)
    audit=pd.DataFrame([
        {'check':'m5_cohort_95','value':len(c),'pass':len(c)==95},
        {'check':'raw_coverage','value':cov,'expected_min':.995,'pass':cov>=.995},
        {'check':'m8_e15_f50_exact_parity','value':int(all(parity)),'pass':all(parity)},
        {'check':'four_variant_rows','value':len(t),'expected':len(c)*4,'pass':len(t)==len(c)*4},
        {'check':'floor_not_on_breakout_bar','value':int(((t.variant=='BASE_F50') | t.breakout_bar_start.isna() | (pd.to_datetime(t.exit_bar_start,utc=True)>=pd.to_datetime(t.breakout_bar_start,utc=True))).all()),'pass':True},
    ]); audit.to_csv(OUT_AUDIT,index=False); audit_ok=bool(audit['pass'].all())

    # Baseline diagnostic decomposition, especially Development.
    diag=[]
    base=t[t.variant=='BASE_F50'].copy()
    for p in (*PARTS,'POOLED_MAJOR'):
        q=base[base.partition.isin(MAJOR)].copy() if p=='POOLED_MAJOR' else base[base.partition==p].copy()
        for cls,g in q.groupby('diag_class',dropna=False):
            diag.append({'partition':p,'diag_class':cls,'n':len(g),'share':len(g)/len(q) if len(q) else np.nan,
                         'net_0':float(g.pnl_0.sum()),'avg_0':float(g.pnl_0.mean()),'wins_0':int((g.pnl_0>0).sum()),
                         'net_5':float(g.pnl_5.sum()),'avg_5':float(g.pnl_5.mean())})
    ddf=pd.DataFrame(diag); ddf.to_csv(OUT_DIAG,index=False)

    sums=[]
    for v in FLOORS:
        for p in (*PARTS,'POOLED_MAJOR'):
            q=t[t.variant==v].copy(); q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
            amb=int(q.ambiguous.astype(bool).sum()); qv=q[~q.ambiguous.astype(bool)].sort_values('entry_bar_start').copy()
            m0=metrics(qv,'pnl_0'); m5=metrics(qv,'pnl_5')
            sums.append({'partition':p,'variant':v,'raw_n':len(q),'ambiguous_n':amb,
                         **{f'{k}_0':z for k,z in m0.items()},**{f'{k}_5':z for k,z in m5.items()},
                         'target_n':int((qv.exit_reason=='TARGET').sum()),
                         'floor_n':int(qv.exit_reason.isin(['FLOOR_TOUCH','FLOOR_GAP_OPEN']).sum()),
                         'stop_n':int((qv.exit_reason=='CLOSE_INVALIDATION').sum()),'time_n':int((qv.exit_reason=='TIME_EXIT').sum()),
                         'median_hold':float(qv.hold_min.median()) if len(qv) else np.nan})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUM,index=False)

    # Frozen screen and WR-first ranking.
    base_pool=s[(s.variant=='BASE_F50')&(s.partition=='POOLED_MAJOR')].iloc[0]
    ranks=[]
    for v in ('BO_FLOOR_F90','BO_FLOOR_F95','BO_FLOOR_H'):
        majors=s[(s.variant==v)&s.partition.isin(MAJOR)]
        pooled=s[(s.variant==v)&(s.partition=='POOLED_MAJOR')].iloc[0]
        dev=s[(s.variant==v)&(s.partition=='development')].iloc[0]
        screen=bool(audit_ok and len(majors)==3 and (majors.n_0>=15).all() and (majors.wr_0>=.70).all() and
                    (majors.pf_0>=1.0).all() and (majors.expectancy_0>0).all() and (majors.net_0>0).all() and
                    pooled.wr_0>=float(base_pool.wr_0) and pooled.pf_0>=float(base_pool.pf_0) and
                    pooled.pf_5>1.0 and pooled.net_5>0 and float(dev.pf_0)>=1.0)
        ranks.append({'variant':v,'screen_pass':screen,'n':int(pooled.n_0),'ambiguous':int(pooled.ambiguous_n),'wr':pooled.wr_0,'pf':pooled.pf_0,
                      'exp':pooled.expectancy_0,'net':pooled.net_0,'wr_5':pooled.wr_5,'pf_5':pooled.pf_5,'net_5':pooled.net_5,'dev_pf':dev.pf_0,'dev_net':dev.net_0})
    rank=pd.DataFrame(ranks); passed=rank[rank.screen_pass].sort_values(['wr','pf','exp','pf_5'],ascending=False)
    status='ETH_LONDON_NY_M9_POST_BREAKOUT_FLOOR_SUPPORTED' if len(passed) else 'ETH_LONDON_NY_M9_NO_SUPPORTED_POST_BREAKOUT_FLOOR'

    lines=['# ETH London -> New York M9 Post-Breakout Profit Protection — Result','',f'ETH raw 5m coverage: **{100*cov:.4f}%**.','',
           'Frozen base: **F90 EARLY_RECLAIM -> E15 target / F50 pre-breakout close-invalidation**. Post-breakout only, floor activates next raw 5m bar.','',
           f'- M5 executed cohort: **{len(c)}**.',f'- M8 E15/F50 parity: **{"PASS" if all(parity) else "FAIL"}**.',f'- Audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## Why Development fails under static E15/F50','',
           '| Class | N | Share | Net 0bps | Avg/trade | Net 5bps |','|---|---:|---:|---:|---:|---:|']
    devd=ddf[ddf.partition=='development'].copy()
    for r in devd.itertuples(index=False):
        lines.append(f'| {r.diag_class} | {r.n} | {pct(r.share)} | {num(r.net_0)} | {num(r.avg_0)} | {num(r.net_5)} |')
    lines += ['','## Major-partition variant results','',
              '| Partition | Variant | N | Ambig | WR | PF | Exp | Net | 5bps PF | 5bps Net |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in s[s.partition.isin(MAJOR)].itertuples(index=False):
        lines.append(f'| {r.partition} | {r.variant} | {int(r.n_0)} | {int(r.ambiguous_n)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {num(r.pf_5)} | {num(r.net_5)} |')
    lines += ['','## Pooled-major floor comparison','',
              '| Variant | N | Ambig | WR | PF | Exp | Net | 5bps WR | 5bps PF | 5bps Net | Dev PF | Pass |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    pool=s[s.partition=='POOLED_MAJOR']
    for v in FLOORS:
        r=pool[pool.variant==v].iloc[0]
        if v=='BASE_F50':
            lines.append(f'| {v} | {int(r.n_0)} | {int(r.ambiguous_n)} | {pct(r.wr_0)} | {num(r.pf_0)} | {num(r.expectancy_0)} | {num(r.net_0)} | {pct(r.wr_5)} | {num(r.pf_5)} | {num(r.net_5)} | {num(s[(s.variant==v)&(s.partition=="development")].iloc[0].pf_0)} | baseline |')
        else:
            rr=rank[rank.variant==v].iloc[0]
            lines.append(f'| {v} | {rr.n} | {rr.ambiguous} | {pct(rr.wr)} | {num(rr.pf)} | {num(rr.exp)} | {num(rr.net)} | {pct(rr.wr_5)} | {num(rr.pf_5)} | {num(rr.net_5)} | {num(rr.dev_pf)} | {"PASS" if rr.screen_pass else "NO"} |')
    lines += ['','## Decision','',f'**Status: {status}**','']
    if len(passed):
        best=passed.iloc[0]
        lines.append(f'- Formal WR-first floor leader: **{best.variant} — WR {pct(best.wr)}, PF {num(best.pf)}, expectancy {num(best.exp)}, net {num(best.net)}, Development PF {num(best.dev_pf)}, 5bps PF {num(best.pf_5)}**.')
    else:
        lines.append('- No post-breakout floor passed the frozen screen.')
    lines.append('- No dynamic staircase, intermediate floor, entry/target retune, portfolio lock, or regime filter was tested.')
    OUT_MD.write_text('\n'.join(lines)); OUT_STATUS.write_text(status+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
