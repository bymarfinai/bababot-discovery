#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
BASE_PATH=HERE/'eth_b27dx_pair_calibration_v2.py'
spec=importlib.util.spec_from_file_location('eth_v2_base',BASE_PATH); b=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(b)

PFX='ETH_B27DX_S4_PORTFOLIO_LOCK'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_CLOCK=ROOT/f'{PFX}_ClockSummary.csv'; OUT_PARITY=ROOT/f'{PFX}_Parity.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
REF_MIN=300; HORIZON_MIN=360; ENTRY_F=0.75; TARGET_EXT=0.25; STOP_F=0.20
CLOCKS=(300,540,600,960)
PARTS=('external','development','reference_validation')
BAR5=pd.Timedelta(minutes=5)
NOTIONAL=500.0; FEE=0.40
BTC_WR=0.719298; BTC_PF=2.223193; BTC_EXP=1.26

def clock_label(v): return f'{(v//60)%24:02d}:{v%60:02d}'
def finite(v):
    if pd.isna(v): return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)
def pf(vals):
    a=np.asarray(list(vals),dtype=float)
    if len(a)==0:return np.nan
    gp=float(a[a>0].sum()) if np.any(a>0) else 0.0; gl=float(-a[a<0].sum()) if np.any(a<0) else 0.0
    return math.inf if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan)
def metrics(df,pnl_col):
    if df.empty:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0,'max_ls':0}
    v=pd.to_numeric(df[pnl_col],errors='coerce').dropna().to_numpy(float); wins=int((v>0).sum()); cur=mx=0
    for z in v:
        if z<0: cur+=1; mx=max(mx,cur)
        else: cur=0
    return {'n':len(v),'wins':wins,'wr':wins/len(v) if len(v) else np.nan,'pf':pf(v),'expectancy':float(v.mean()) if len(v) else np.nan,'net':float(v.sum()),'max_ls':mx}
def weeks_for(part):
    a,z=b.m.m.PARTS[part]; return float((z-a)/pd.Timedelta(days=7))
def time_exit_open(x,ee):
    pos=int(x.index.searchsorted(ee,side='left'))
    if pos>=len(x) or x.index[pos]!=ee:return None
    return float(x.iloc[pos].open)
def score_trade_detail(x,exe,fill_ts,ee,ep,target,stop,stress_bps=0.0):
    q=exe[exe.index>=fill_ts+BAR5]; reason=None; xp=None; exit_ts=pd.NaT
    for ts,r in q.iterrows():
        ts=pd.Timestamp(ts)
        if float(r.high)>=target:
            xp=float(target); reason='TARGET'; exit_ts=ts+BAR5; break
        if float(r.close)<stop:
            xp=float(r.close); reason='CLOSE_INVALIDATION'; exit_ts=ts+BAR5; break
    if reason is None:
        xp=time_exit_open(x,ee)
        if xp is None:return None
        reason='TIME_EXIT'; exit_ts=pd.Timestamp(ee)
    bps=float(stress_bps)/10000.0; entry_exec=float(ep)*(1.0+bps); exit_exec=float(xp) if reason=='TARGET' else float(xp)*(1.0-bps)
    pnl=NOTIONAL*(exit_exec/entry_exec-1.0)-FEE
    return {'exit_ts':pd.Timestamp(exit_ts),'exit_px':float(xp),'exit_reason':reason,'pnl':float(pnl)}
def build_candidates(x):
    rows=[]
    for part in PARTS:
        for ex in CLOCKS:
            sess=b.sessions_for(x,part,ex,REF_MIN,HORIZON_MIN,'LONG',ENTRY_F)
            for s in sess:
                target=b.target_level(s['L'],s['H'],'LONG',TARGET_EXT); stop=b.stop_level(s['L'],s['H'],STOP_F)
                d0=score_trade_detail(x,s['exe'],s['fill_ts'],s['ee'],s['entry'],target,stop,0.0); d5=score_trade_detail(x,s['exe'],s['fill_ts'],s['ee'],s['entry'],target,stop,5.0)
                if d0 is None or d5 is None:continue
                assert d0['exit_ts']==d5['exit_ts'] and d0['exit_reason']==d5['exit_reason']
                rows.append({'partition':part,'exec_min':ex,'execution_utc':clock_label(ex),'execution_start':pd.Timestamp(s['es']),
                             'entry_bar_start':pd.Timestamp(s['fill_ts']),'entry_px':float(s['entry']),'exit_ts':d0['exit_ts'],'exit_px_0':d0['exit_px'],
                             'exit_reason':d0['exit_reason'],'pnl_0':d0['pnl'],'pnl_5':d5['pnl'],'H':float(s['H']),'L':float(s['L'])})
    c=pd.DataFrame(rows)
    if not c.empty:
        for col in ('execution_start','entry_bar_start','exit_ts'):c[col]=pd.to_datetime(c[col],utc=True)
        c['candidate_id']=c.apply(lambda r:f"{r.partition}|{r.execution_utc}|{r.execution_start.isoformat()}|{r.entry_bar_start.isoformat()}",axis=1)
    return c
def parity_check(x,c):
    rows=[]
    for p in PARTS:
        for ex in CLOCKS:
            q=c[(c.partition==p)&(c.exec_min==ex)].sort_values('entry_bar_start'); calc=metrics(q,'pnl_0')
            exp=b.score_config(x=x,part_name=p,side='LONG',exec_min=ex,ref_min=REF_MIN,horizon_min=HORIZON_MIN,entry_f=ENTRY_F,target_ext=TARGET_EXT,stop_f=STOP_F,stress_bps=0.0)
            for field in ('n','wins','wr','pf','expectancy','net'):
                a=float(calc[field]); e=float(exp[field]); ok=(math.isnan(a) and math.isnan(e)) or (math.isinf(a) and math.isinf(e)) or abs(a-e)<=1e-9
                rows.append({'partition':p,'execution_utc':clock_label(ex),'field':field,'calculated':a,'expected':e,'pass':ok})
    return pd.DataFrame(rows)
def lock_partition(g):
    q=g.sort_values(['entry_bar_start','execution_start','exec_min'],ascending=[True,False,True]).copy(); locked_until=pd.NaT; accepted=[]; blocked_by=[]; active=''
    for r in q.itertuples(index=False):
        if pd.isna(locked_until) or pd.Timestamp(r.entry_bar_start)>=pd.Timestamp(locked_until):
            accepted.append(True); blocked_by.append(''); locked_until=pd.Timestamp(r.exit_ts); active=str(r.execution_utc)
        else:
            accepted.append(False); blocked_by.append(active)
    q['accepted']=accepted; q['blocked_by_clock']=blocked_by; return q
def summarize(c):
    decisions=[]; rows=[]; clock_rows=[]
    for p in PARTS:
        d=lock_partition(c[c.partition==p].copy()); decisions.append(d); a=d[d.accepted].sort_values('entry_bar_start')
        for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
            m=metrics(a,col); rows.append({'partition':p,'stress_bps':stress,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/weeks_for(p),**m})
        for ex in CLOCKS:
            z=d[d.exec_min==ex]; az=z[z.accepted].sort_values('entry_bar_start'); m=metrics(az,'pnl_0')
            clock_rows.append({'partition':p,'execution_utc':clock_label(ex),'candidates':len(z),'accepted':len(az),'blocked':int((~z.accepted).sum()),**m})
    dec=pd.concat(decisions,ignore_index=True); amaj=dec[dec.accepted].sort_values('entry_bar_start'); major_weeks=sum(weeks_for(p) for p in PARTS)
    for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
        m=metrics(amaj,col); rows.append({'partition':'POOLED_MAJOR','stress_bps':stress,'candidates':len(dec),'accepted':len(amaj),'blocked':int((~dec.accepted).sum()),'trades_per_week':len(amaj)/major_weeks,**m})
    for ex in CLOCKS:
        z=dec[dec.exec_min==ex]; az=z[z.accepted].sort_values('entry_bar_start'); m=metrics(az,'pnl_0')
        clock_rows.append({'partition':'POOLED_MAJOR','execution_utc':clock_label(ex),'candidates':len(z),'accepted':len(az),'blocked':int((~z.accepted).sum()),**m})
    return dec,pd.DataFrame(rows),pd.DataFrame(clock_rows)
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=b.m.m.load5(); c=build_candidates(x); c.to_csv(OUT_CAND,index=False); parity=parity_check(x,c); parity.to_csv(OUT_PARITY,index=False); parity_ok=bool(parity['pass'].all()) if len(parity) else False
    dec,summ,clock=summarize(c); dec.to_csv(OUT_DEC,index=False); summ.to_csv(OUT_SUM,index=False); clock.to_csv(OUT_CLOCK,index=False)
    p0=summ[(summ.partition=='POOLED_MAJOR')&(summ.stress_bps==0)].iloc[0]; p5=summ[(summ.partition=='POOLED_MAJOR')&(summ.stress_bps==5)].iloc[0]
    major0=summ[(summ.partition.isin(PARTS))&(summ.stress_bps==0)]
    major_positive=bool(((major0.net>0)&(major0.pf>1.0)).all())
    btc_quality=bool(p0.wr>=BTC_WR and p0.pf>=BTC_PF and p0.expectancy>=BTC_EXP and major_positive)
    stress_ok=bool(p5.pf>=1.0 and p5.net>=0)
    if not parity_ok:status='ETH_S4_PARITY_FAILED'
    elif btc_quality and stress_ok:status='ETH_S4_PORTFOLIO_BTC_QUALITY_SUPPORTED'
    elif major_positive and p0.pf>1.0 and p0.net>0 and stress_ok:status='ETH_S4_PORTFOLIO_POSITIVE_BELOW_BTC_QUALITY'
    else:status='ETH_S4_PORTFOLIO_NOT_SUPPORTED'
    ties=c.groupby(['partition','entry_bar_start']).size() if len(c) else pd.Series(dtype=int); tie_n=int((ties>1).sum())
    lines=['# ETH B27DX — S4 Global One-Position Portfolio Lock — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen representative: **R300/X360 · F75 entry · E25 target · F20 completed-close invalidation** across **05:00, 09:00, 10:00, 16:00 UTC**.','',
           f'- Candidate-detail parity: **{"PASS" if parity_ok else "FAIL"}**.','- Exact same-entry-bar clock ties: **%d**.'%tie_n,'',
           '## Portfolio summary','',
           '| Partition | Stress | Candidates | Accepted | Blocked | Trades/wk | WR | PF | Exp | Net | Max LS |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    order=[*PARTS,'POOLED_MAJOR']
    for p in order:
        for stress in (0,5):
            r=summ[(summ.partition==p)&(summ.stress_bps==stress)].iloc[0]
            lines.append(f'| {p} | {stress} bps | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
    lines += ['','## Pooled-major source-clock contribution (0 bps)','',
              '| Clock | Candidates | Accepted | Blocked | WR | PF | Exp | Net |','|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in clock[clock.partition=='POOLED_MAJOR'].sort_values('execution_utc').itertuples(index=False):
        lines.append(f'| {r.execution_utc} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} |')
    lines += ['','## BTC benchmark gate','',
              '- BTC B27DX LONG benchmark: **WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3**.',
              f'- ETH pooled-major 0 bps: **WR {pct(p0.wr)}, PF {fmt(p0.pf)}, expectancy {fmt(p0.expectancy)}, net {fmt(p0.net)}, max LS {int(p0.max_ls)}**.',
              f'- ETH pooled-major frequency: **{p0.trades_per_week:.3f} accepted trades/week**.',
              f'- BTC-quality gate: **{"PASS" if btc_quality else "FAIL"}**.',f'- 5 bps stress gate: **{"PASS" if stress_ok else "FAIL"}**.','',
              '## Decision','',f'**Status: {status}**','',
              '- No geometry, clock, runner, leverage, fee, or live-code tuning was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
