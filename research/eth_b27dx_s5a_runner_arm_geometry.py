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

PFX='ETH_B27DX_S5A_RUNNER_ARM_GEOMETRY'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CAND=ROOT/f'{PFX}_Candidates.csv'; OUT_DEC=ROOT/f'{PFX}_Decisions.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_CLOCK=ROOT/f'{PFX}_ClockSummary.csv'; OUT_AUDIT=ROOT/f'{PFX}_Audit.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
S4_SUM=ROOT/'ETH_B27DX_S4_PORTFOLIO_LOCK_Summary.csv'
REF_MIN=300; HORIZON_MIN=360; ENTRY_F=0.75; PREARM_STOP_F=0.20
CLOCKS=(300,540,600,960); PARTS=('external','development','reference_validation')
ARMS=(0.10,0.15,0.20,0.25,0.30,0.35,0.40)
GAP=0.10; STEP=0.10; BAR5=pd.Timedelta(minutes=5)
NOTIONAL=500.0; FEE=0.40
BASE_N=478; BASE_WR=0.628; BASE_PF=1.42; BASE_EXP=0.81; BASE_NET=385.75
BTC_WR=0.719298; BTC_PF=2.223193; BTC_EXP=1.26

def clock_label(v): return f'{(v//60)%24:02d}:{v%60:02d}'
def e_label(v): return f'E{int(round(v*100)):02d}'
def pf(vals):
    a=np.asarray(list(vals),dtype=float)
    if len(a)==0:return np.nan
    gp=float(a[a>0].sum()) if np.any(a>0) else 0.; gl=float(-a[a<0].sum()) if np.any(a<0) else 0.
    return math.inf if gl==0 and gp>0 else (gp/gl if gl>0 else np.nan)
def metrics(df,col):
    if df.empty:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0,'max_ls':0}
    v=pd.to_numeric(df[col],errors='coerce').dropna().to_numpy(float); wins=int((v>0).sum()); cur=mx=0
    for z in v:
        if z<0:cur+=1;mx=max(mx,cur)
        else:cur=0
    return {'n':len(v),'wins':wins,'wr':wins/len(v) if len(v) else np.nan,'pf':pf(v),'expectancy':float(v.mean()),'net':float(v.sum()),'max_ls':mx}
def weeks_for(p):
    a,z=b.m.m.PARTS[p]; return float((z-a)/pd.Timedelta(days=7))
def time_exit_open(x,ee):
    pos=int(x.index.searchsorted(ee,side='left'))
    if pos>=len(x) or x.index[pos]!=ee:return None
    return float(x.iloc[pos].open)
def floor_from_close(close,H,R,arm_ext,current_known):
    ext=(float(close)-H)/R
    k=math.floor((ext-arm_ext+1e-12)/STEP)
    if k<=0:return float(current_known)
    desired=H+(arm_ext-GAP+k*STEP)*R
    return max(float(current_known),float(desired))

def runner_exit(x,s,arm_ext,stress_bps=0.0):
    exe=s['exe']; fill_ts=pd.Timestamp(s['fill_ts']); ee=pd.Timestamp(s['ee']); H=float(s['H']); L=float(s['L']); R=H-L; ep=float(s['entry'])
    f20=L+PREARM_STOP_F*R; arm=H+arm_ext*R; initial_floor=H+(arm_ext-GAP)*R
    q=exe[exe.index>=fill_ts+BAR5]
    armed=False; active_floor=np.nan; pending=[]; arm_bar=pd.NaT; reason=None; xp=None; exit_ts=pd.NaT
    scheduled=activations=ratchets=buffer_f20=gap_exits=touch_exits=0; early_violation=0
    for ts,r in q.iterrows():
        ts=pd.Timestamp(ts); op=float(r.open); hi=float(r.high); lo=float(r.low); cl=float(r.close)
        due=[z for z in pending if z[0]<=ts]
        if due:
            for eff,floor,learned in due:
                if eff < learned+2*BAR5: early_violation+=1
            due_floor=max(z[1] for z in due)
            if pd.isna(active_floor) or due_floor>active_floor+1e-12:
                active_floor=float(due_floor); activations+=1
            pending=[z for z in pending if z[0]>ts]
        if armed and not pd.isna(active_floor):
            if op<=active_floor:
                xp=op; reason='LIVE_FLOOR_GAP_OPEN'; exit_ts=ts; gap_exits+=1; break
            if lo<=active_floor:
                xp=float(active_floor); reason='LIVE_FLOOR_TOUCH'; exit_ts=ts+BAR5; touch_exits+=1; break
        if not armed:
            if hi>=arm:
                armed=True; arm_bar=ts
                pending.append((ts+2*BAR5,float(initial_floor),ts)); scheduled+=1
                continue
            if cl<f20:
                xp=cl; reason='CLOSE_INVALIDATION_F20'; exit_ts=ts+BAR5; break
            continue
        if pd.isna(active_floor) and cl<f20:
            xp=cl; reason='BUFFER_CLOSE_INVALIDATION_F20'; exit_ts=ts+BAR5; buffer_f20+=1; break
        known=[float(initial_floor)]
        if not pd.isna(active_floor):known.append(float(active_floor))
        known += [float(z[1]) for z in pending]
        known_floor=max(known)
        desired=floor_from_close(cl,H,R,arm_ext,known_floor)
        if desired>known_floor+1e-12:
            pending.append((ts+2*BAR5,float(desired),ts)); scheduled+=1; ratchets+=1
    if reason is None:
        xp=time_exit_open(x,ee)
        if xp is None:return None
        reason='RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_EXEC_END'; exit_ts=ee
    bps=float(stress_bps)/10000.; entry_exec=ep*(1.+bps); exit_exec=float(xp)*(1.-bps)
    pnl=NOTIONAL*(exit_exec/entry_exec-1.)-FEE
    return {'exit_ts':pd.Timestamp(exit_ts),'exit_px':float(xp),'exit_reason':reason,'pnl':float(pnl),'armed':armed,'arm_bar':arm_bar,
            'scheduled_updates':scheduled,'activations':activations,'ratchet_updates':ratchets,'buffer_f20_exit':buffer_f20,
            'gap_exit':gap_exits,'touch_exit':touch_exits,'early_floor_violation':early_violation}

def build_candidates(x):
    rows=[]; cache={}
    for p in PARTS:
        for ex in CLOCKS:cache[(p,ex)]=b.sessions_for(x,p,ex,REF_MIN,HORIZON_MIN,'LONG',ENTRY_F)
    for arm_ext in ARMS:
        for p in PARTS:
            for ex in CLOCKS:
                for s in cache[(p,ex)]:
                    d0=runner_exit(x,s,arm_ext,0.0); d5=runner_exit(x,s,arm_ext,5.0)
                    if d0 is None or d5 is None:continue
                    if d0['exit_ts']!=d5['exit_ts'] or d0['exit_reason']!=d5['exit_reason']:raise AssertionError('stress changed runner chronology')
                    row={'arm_ext':arm_ext,'arm':e_label(arm_ext),'partition':p,'exec_min':ex,'execution_utc':clock_label(ex),'execution_start':pd.Timestamp(s['es']),
                         'entry_bar_start':pd.Timestamp(s['fill_ts']),'entry_px':float(s['entry']),'exit_ts':d0['exit_ts'],'exit_px_0':d0['exit_px'],'exit_reason':d0['exit_reason'],
                         'pnl_0':d0['pnl'],'pnl_5':d5['pnl'],'H':float(s['H']),'L':float(s['L'])}
                    for k in ('armed','arm_bar','scheduled_updates','activations','ratchet_updates','buffer_f20_exit','gap_exit','touch_exit','early_floor_violation'):row[k]=d0[k]
                    rows.append(row)
    c=pd.DataFrame(rows)
    for col in ('execution_start','entry_bar_start','exit_ts','arm_bar'):
        if col in c:c[col]=pd.to_datetime(c[col],utc=True,errors='coerce')
    return c

def lock(g):
    q=g.sort_values(['entry_bar_start','execution_start','exec_min'],ascending=[True,False,True]).copy(); until=pd.NaT; accepted=[]; blocker=[]; active=''
    for r in q.itertuples(index=False):
        if pd.isna(until) or pd.Timestamp(r.entry_bar_start)>=pd.Timestamp(until):
            accepted.append(True); blocker.append(''); until=pd.Timestamp(r.exit_ts); active=str(r.execution_utc)
        else:accepted.append(False); blocker.append(active)
    q['accepted']=accepted;q['blocked_by_clock']=blocker;return q

def summarize(c):
    decisions=[]; rows=[]; clock_rows=[]; audits=[]
    major_weeks=sum(weeks_for(p) for p in PARTS)
    for arm_ext in ARMS:
        arm=e_label(arm_ext); arm_dec=[]
        for p in PARTS:
            g=c[(c.arm_ext==arm_ext)&(c.partition==p)].copy(); d=lock(g); arm_dec.append(d); decisions.append(d); a=d[d.accepted].sort_values('entry_bar_start')
            audits.append({'arm':arm,'partition':p,'candidate_count':len(g),'early_floor_violations':int(pd.to_numeric(g.early_floor_violation,errors='coerce').fillna(0).sum()),'same_entry_ties':int((g.groupby('entry_bar_start').size()>1).sum())})
            for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
                m=metrics(a,col); rows.append({'arm_ext':arm_ext,'arm':arm,'partition':p,'stress_bps':stress,'candidates':len(d),'accepted':len(a),'blocked':int((~d.accepted).sum()),'trades_per_week':len(a)/weeks_for(p),
                    'armed':int(a.armed.sum()),'floor_exits':int(a.exit_reason.isin(['LIVE_FLOOR_GAP_OPEN','LIVE_FLOOR_TOUCH']).sum()),'gap_exits':int((a.exit_reason=='LIVE_FLOOR_GAP_OPEN').sum()),'buffer_f20_exits':int((a.exit_reason=='BUFFER_CLOSE_INVALIDATION_F20').sum()),'time_exits':int(a.exit_reason.isin(['RUNNER_TIME_EXIT','TIME_EXIT_EXEC_END']).sum()),
                    'scheduled_updates':int(pd.to_numeric(a.scheduled_updates,errors='coerce').fillna(0).sum()),'activations':int(pd.to_numeric(a.activations,errors='coerce').fillna(0).sum()),**m})
            for ex in CLOCKS:
                z=d[d.exec_min==ex]; az=z[z.accepted].sort_values('entry_bar_start'); m=metrics(az,'pnl_0')
                clock_rows.append({'arm':arm,'partition':p,'execution_utc':clock_label(ex),'candidates':len(z),'accepted':len(az),'blocked':int((~z.accepted).sum()),**m})
        dmaj=pd.concat(arm_dec,ignore_index=True); amaj=dmaj[dmaj.accepted].sort_values('entry_bar_start')
        for stress,col in ((0,'pnl_0'),(5,'pnl_5')):
            m=metrics(amaj,col); rows.append({'arm_ext':arm_ext,'arm':arm,'partition':'POOLED_MAJOR','stress_bps':stress,'candidates':len(dmaj),'accepted':len(amaj),'blocked':int((~dmaj.accepted).sum()),'trades_per_week':len(amaj)/major_weeks,
                'armed':int(amaj.armed.sum()),'floor_exits':int(amaj.exit_reason.isin(['LIVE_FLOOR_GAP_OPEN','LIVE_FLOOR_TOUCH']).sum()),'gap_exits':int((amaj.exit_reason=='LIVE_FLOOR_GAP_OPEN').sum()),'buffer_f20_exits':int((amaj.exit_reason=='BUFFER_CLOSE_INVALIDATION_F20').sum()),'time_exits':int(amaj.exit_reason.isin(['RUNNER_TIME_EXIT','TIME_EXIT_EXEC_END']).sum()),
                'scheduled_updates':int(pd.to_numeric(amaj.scheduled_updates,errors='coerce').fillna(0).sum()),'activations':int(pd.to_numeric(amaj.activations,errors='coerce').fillna(0).sum()),**m})
        for ex in CLOCKS:
            z=dmaj[dmaj.exec_min==ex];az=z[z.accepted].sort_values('entry_bar_start');m=metrics(az,'pnl_0')
            clock_rows.append({'arm':arm,'partition':'POOLED_MAJOR','execution_utc':clock_label(ex),'candidates':len(z),'accepted':len(az),'blocked':int((~z.accepted).sum()),**m})
    return pd.concat(decisions,ignore_index=True),pd.DataFrame(rows),pd.DataFrame(clock_rows),pd.DataFrame(audits)
def support_flags(summary,audit):
    out=[]
    for arm_ext in ARMS:
        arm=e_label(arm_ext); p0=summary[(summary.arm_ext==arm_ext)&(summary.partition=='POOLED_MAJOR')&(summary.stress_bps==0)].iloc[0]; p5=summary[(summary.arm_ext==arm_ext)&(summary.partition=='POOLED_MAJOR')&(summary.stress_bps==5)].iloc[0]
        maj=summary[(summary.arm_ext==arm_ext)&summary.partition.isin(PARTS)&(summary.stress_bps==0)]
        causal=int(audit[audit.arm==arm].early_floor_violations.sum())==0; major_pos=bool(((maj.net>0)&(maj.pf>1.0)).all()); stress=bool(p5.pf>=1.0 and p5.net>=0)
        supported=bool(p0.net>BASE_NET and p0.pf>=1.80 and p0.wr>=0.70 and p0.expectancy>BASE_EXP and p0.accepted>=0.80*BASE_N and major_pos and causal and stress)
        btc=bool(p0.wr>=BTC_WR and p0.pf>=BTC_PF and p0.expectancy>=BTC_EXP and major_pos and causal and stress)
        out.append({'arm_ext':arm_ext,'arm':arm,'supported':supported,'btc_quality':btc,'causal_audit':causal,'major_positive':major_pos,'stress_pass':stress})
    return pd.DataFrame(out)
def supported_runs(flags):
    vals=[float(r.arm_ext) for r in flags.sort_values('arm_ext').itertuples(index=False) if bool(r.supported)]
    if not vals:return []
    out=[];cur=[vals[0]]
    for v in vals[1:]:
        if abs((v-cur[-1])-0.05)<1e-9:cur.append(v)
        else:out.append(cur);cur=[v]
    out.append(cur);return out
def fmt(v,nd=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=b.m.m.load5(); c=build_candidates(x); c.to_csv(OUT_CAND,index=False); dec,summ,clock,audit=summarize(c); flags=support_flags(summ,audit); dec.to_csv(OUT_DEC,index=False); summ.to_csv(OUT_SUM,index=False); clock.to_csv(OUT_CLOCK,index=False); audit.to_csv(OUT_AUDIT,index=False)
    runs=supported_runs(flags); family=any(len(r)>=2 for r in runs); anysup=bool(flags.supported.any()); causal=bool(flags.causal_audit.all())
    if not causal:status='ETH_S5A_CAUSAL_AUDIT_FAILED'
    elif family:status='ETH_S5A_NATIVE_ARM_FAMILY_SUPPORTED'
    elif anysup:status='ETH_S5A_SUPPORTED_ARM_ISOLATED'
    else:status='ETH_S5A_NO_SUPPORTED_ARM'
    lines=['# ETH B27DX — S5A Live-Executable Runner Arm Geometry — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',
           'Frozen signal layer: **R300/X360 · F75 entry · F20 pre-arm invalidation · clocks 05:00,09:00,10:00,16:00 UTC**. Only runner arm milestone varies. Breathing gap and ratchet step are fixed at 0.10R with B27DQ-style N+2 activation.','',
           '## Pooled-major arm comparison','',
           '| Arm | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS | Armed | Floor exits | 5bps PF | 5bps Net | Support | BTC quality |',
           '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for f in flags.sort_values('arm_ext').itertuples(index=False):
        r=summ[(summ.arm_ext==f.arm_ext)&(summ.partition=='POOLED_MAJOR')&(summ.stress_bps==0)].iloc[0]; s=summ[(summ.arm_ext==f.arm_ext)&(summ.partition=='POOLED_MAJOR')&(summ.stress_bps==5)].iloc[0]
        lines.append(f'| {f.arm} | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} | {int(r.armed)} | {int(r.floor_exits)} | {fmt(s.pf)} | {fmt(s.net)} | {"YES" if f.supported else "NO"} | {"PASS" if f.btc_quality else "NO"} |')
    lines += ['','## Fixed S4 baseline','',f'- Accepted **{BASE_N}**, frequency **1.393/wk**, WR **62.8%**, PF **1.42**, expectancy **+$0.81/trade**, net **+$385.75**, max LS **5**.','',
              '## Supported arm-family runs','']
    if not runs:lines.append('None.')
    else:
        for i,r in enumerate(runs,1):lines.append(f'- Run {i}: **{" → ".join(e_label(v) for v in r)}** ({len(r)} adjacent arms).')
    lines += ['','## Per-partition 0 bps','', '| Arm | Partition | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |','|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for arm_ext in ARMS:
        for p in PARTS:
            r=summ[(summ.arm_ext==arm_ext)&(summ.partition==p)&(summ.stress_bps==0)].iloc[0]
            lines.append(f'| {e_label(arm_ext)} | {p} | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
    lines += ['','## Causal execution audit','',f'- Early floor activations: **{int(audit.early_floor_violations.sum())}**.',f'- All arm variants causal-audit pass: **{"YES" if causal else "NO"}**.','',
              '## BTC benchmark','', '- BTC B27DX LONG: **WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3**.','- BTC-quality labels above require those pooled-major thresholds plus positive major partitions and 5 bps stress survival.','',
              '## Decision','',f'**Status: {status}**','', '- No breathing-gap, ratchet-step, geometry, clock, leverage, fee, or live-code tuning was performed.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
