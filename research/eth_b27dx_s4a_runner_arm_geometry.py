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

PFX='ETH_B27DX_S4A_RUNNER_ARM_GEOMETRY'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_SCORES=ROOT/f'{PFX}_Scores.csv'; OUT_SUMMARY=ROOT/f'{PFX}_ArmSummary.csv'; OUT_ROBUST=ROOT/f'{PFX}_RobustClockArms.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
BAR5=pd.Timedelta(minutes=5); REF_MIN=300; HORIZON_MIN=360; ENTRY_F=0.80; PRESTOP_F=0.35
CLOCKS=(300,540,600,960); ARMS=(0.10,0.15,0.20,0.25,0.30,0.35,0.40); PARTS=('development','external','reference_validation')
BTC_WR=0.719298; BTC_PF=2.223193

def clock_label(v):return f'{(v//60)%24:02d}:{v%60:02d}'
def a_label(v):return f'E{int(round(v*100)):02d}'
def finite(v):
    if pd.isna(v):return np.nan
    return 999999.0 if math.isinf(float(v)) else float(v)
def positive(part,r):
    if part=='development':return bool(r['n']>=30 and r['pf']>=1.10 and r['expectancy']>0 and r['net']>0)
    return bool(r['n']>=15 and r['pf']>1.00 and r['expectancy']>0 and r['net']>0)
def time_exit_open(x,ee):
    pos=int(x.index.searchsorted(ee,side='left'))
    if pos>=len(x) or x.index[pos]!=ee:return None
    return float(x.iloc[pos].open)
def desired_floor_ext(close_ext,arm_ext,current_ext):
    if close_ext < arm_ext+0.10-1e-12:return current_ext
    milestone=math.floor((close_ext+1e-12)/0.10)*0.10
    return max(current_ext,milestone-0.10)
def runner_trade(x,s,arm_ext):
    H=float(s['H']);L=float(s['L']);R=H-L;entry=float(s['entry']);ee=pd.Timestamp(s['ee']);fill=pd.Timestamp(s['fill_ts']);exe=s['exe']
    f35=L+PRESTOP_F*R;arm_px=H+arm_ext*R;initial_ext=max(0.0,arm_ext-0.10)
    q=exe[exe.index>=fill+BAR5]
    armed=False;active=np.nan;pending=[];reason=None;xp=None;arm_ts=pd.NaT;raises=0
    for ts,bar in q.iterrows():
        ts=pd.Timestamp(ts);op=float(bar.open);hi=float(bar.high);lo=float(bar.low);cl=float(bar.close)
        due=[z for z in pending if z[0]<=ts]
        if due:
            due_ext=max(z[1] for z in due);active=due_ext if pd.isna(active) else max(active,due_ext);pending=[z for z in pending if z[0]>ts]
        if armed and not pd.isna(active):
            floor_px=H+active*R
            if op<=floor_px:xp=op;reason='RUNNER_GAP_OPEN';break
            if lo<=floor_px:xp=floor_px;reason='RUNNER_FLOOR_TOUCH';break
        if not armed:
            if hi>=arm_px:
                armed=True;arm_ts=ts;cur=initial_ext;cur=desired_floor_ext((cl-H)/R,arm_ext,cur);pending.append((ts+2*BAR5,cur));continue
            if cl<f35:xp=cl;reason='PREARM_CLOSE_F35';break
            continue
        if pd.isna(active) and cl<f35:xp=cl;reason='BUFFER_CLOSE_F35';break
        known=[initial_ext]+([float(active)] if not pd.isna(active) else [])+[float(z[1]) for z in pending]
        cur=max(known);des=desired_floor_ext((cl-H)/R,arm_ext,cur)
        if des>cur+1e-12:pending.append((ts+2*BAR5,des));raises+=1
    if reason is None:
        xp=time_exit_open(x,ee)
        if xp is None:return None
        reason='RUNNER_TIME_EXIT' if armed else 'TIME_EXIT_UNARMED'
    pnl=500.0*(xp/entry-1.0)-0.40
    return float(pnl),reason,armed,raises

def score(x,part,ex,arm_ext):
    sess=b.sessions_for(x,part,ex,REF_MIN,HORIZON_MIN,'LONG',ENTRY_F);pnls=[];arms=raises=0;reasons={}
    for s in sess:
        out=runner_trade(x,s,arm_ext)
        if out is None:continue
        pnl,reason,armed,nraise=out;pnls.append(pnl);arms+=int(armed);raises+=nraise;reasons[reason]=reasons.get(reason,0)+1
    d=b.metrics(pnls);d.update({'partition':part,'exec_min':ex,'execution_utc':clock_label(ex),'arm_ext':arm_ext,'arm':a_label(arm_ext),'armed_trades':arms,'ratchet_raises':raises,'reasons':str(reasons)});d['positive']=positive(part,d);return d
def run_scores(x):return pd.DataFrame([score(x,p,ex,a) for a in ARMS for ex in CLOCKS for p in PARTS])
def summarize(scores):
    rr=[]
    for a in ARMS:
        for ex in CLOCKS:
            q=scores[(scores.arm_ext==a)&(scores.exec_min==ex)]
            if len(q)==3 and all(bool(q.loc[q.partition==p,'positive'].iloc[0]) for p in PARTS):rr.append({'arm_ext':a,'arm':a_label(a),'exec_min':ex,'execution_utc':clock_label(ex)})
    robust=pd.DataFrame(rr);rows=[]
    for a in ARMS:
        q=scores[scores.arm_ext==a];cl=[] if robust.empty else robust.loc[robust.arm_ext==a,'execution_utc'].tolist();row={'arm_ext':a,'arm':a_label(a),'robust_clock_count':len(cl),'robust_clocks':','.join(cl),'supported':len(cl)>=2}
        for p in PARTS:
            z=q[q.partition==p];row[f'{p}_median_wr']=float(pd.to_numeric(z.wr,errors='coerce').median());row[f'{p}_median_pf']=float(pd.Series([finite(v) for v in z.pf]).median());row[f'{p}_median_exp']=float(pd.to_numeric(z.expectancy,errors='coerce').median())
        z=q[q.execution_utc.isin(cl)] if cl else q.iloc[0:0];wr=pd.to_numeric(z.wr,errors='coerce').dropna();pf=[finite(v) for v in z.pf if not pd.isna(v)];ep=pd.to_numeric(z.expectancy,errors='coerce').dropna();ls=pd.to_numeric(z.max_ls,errors='coerce').dropna()
        row['robust_major_median_wr']=float(wr.median()) if len(wr) else np.nan;row['robust_major_median_pf']=float(np.median(pf)) if pf else np.nan;row['robust_major_median_exp']=float(ep.median()) if len(ep) else np.nan;row['robust_major_max_ls']=int(ls.max()) if len(ls) else np.nan;row['btc_wr_gap_pp']=100*(row['robust_major_median_wr']-BTC_WR) if len(wr) else np.nan;row['btc_pf_gap']=row['robust_major_median_pf']-BTC_PF if pf else np.nan;rows.append(row)
    return pd.DataFrame(rows),robust
def runs(summary):
    vals=[float(r.arm_ext) for r in summary.sort_values('arm_ext').itertuples(index=False) if bool(r.supported)]
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
    x,cov=b.m.m.load5();scores=run_scores(x);scores.to_csv(OUT_SCORES,index=False);summary,robust=summarize(scores);summary.to_csv(OUT_SUMMARY,index=False);robust.to_csv(OUT_ROBUST,index=False);rns=runs(summary);fam=[r for r in rns if len(r)>=2]
    status='ETH_S4A_NATIVE_RUNNER_ARM_FAMILY_SUPPORTED' if fam else ('ETH_S4A_SUPPORTED_ARMS_NO_FAMILY' if bool(summary.supported.any()) else 'ETH_S4A_NO_SUPPORTED_ARM')
    lines=['# ETH B27DX — S4A Native Runner Arm Geometry — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','','Frozen: R300/X360, F80 entry, pre-arm F35 close invalidation, BTC-style causal N+2 one-step-behind runner architecture. Only arm threshold varies.','','## Arm summary','','| Arm | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Robust-major exp | Max LS | Supported |','|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in summary.itertuples(index=False):lines.append(f'| {r.arm} | {r.robust_clock_count}/4 | {r.robust_clocks or "-"} | {pct(r.development_median_wr)} | {fmt(r.development_median_pf)} | {pct(r.external_median_wr)} | {fmt(r.external_median_pf)} | {pct(r.reference_validation_median_wr)} | {fmt(r.reference_validation_median_pf)} | {pct(r.robust_major_median_wr)} | {fmt(r.robust_major_median_pf)} | {fmt(r.robust_major_median_exp)} | {fmt(r.robust_major_max_ls,0)} | {"YES" if r.supported else "NO"} |')
    lines += ['','## Robust clock × arm pairs','']
    if robust.empty:lines.append('None.')
    else:
        lines += ['| Arm | Clock |','|---:|---:|'];[lines.append(f'| {r.arm} | {r.execution_utc} |') for r in robust.sort_values(['arm_ext','exec_min']).itertuples(index=False)]
    lines += ['','## Supported arm-family runs','']
    if not rns:lines.append('None.')
    else:
        for i,run in enumerate(rns,1):lines.append(f'- Run {i}: **{" → ".join(a_label(v) for v in run)}** ({len(run)} adjacent arms).')
    lines += ['','## BTC benchmark diagnostic','','- BTC B27DX LONG final: WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3.','- Arm promotion remains topology-based; final acceptance requires portfolio locking and stress.','','## Decision','',f'**Status: {status}**','','- No live BBC changes.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text(status+'\n');print(OUT_MD.read_text())
if __name__=='__main__':main()
