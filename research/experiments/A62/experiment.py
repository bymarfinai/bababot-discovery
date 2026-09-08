#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

BAR=pd.Timedelta(minutes=5); PARTS=("development","external","reference_validation")
SHOW={"development":"Development","external":"External Validation","reference_validation":"Reference Validation"}
PARENT={"development":601,"external":281,"reference_validation":337}
LOSSES={"development":357,"external":166,"reference_validation":187}
L0={"development":37,"external":13,"reference_validation":26}
AGES=(30,60,120); EPS=1e-12
DIR={"running_mfe_R":"lower","running_mae_R":"higher","close_H_R":"lower","recovery_from_worst_R":"lower","drawdown_from_best_R":"higher","upper_half_close_fraction":"lower"}


def load_a55(root):
    p=root/"research"/"sol_long_15utc_loss_confirmation_candle_a55.py"
    s=importlib.util.spec_from_file_location("a62_a55",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def pos(idx,t):
    t=pd.Timestamp(t); i=int(idx.searchsorted(t,"left"))
    if i>=len(idx) or idx[i]!=t: raise RuntimeError(f"timestamp parity failure {t}")
    return i

def lastbar(entry,age): return pd.Timestamp(entry)+pd.Timedelta(minutes=age)-BAR
def startbar(entry): return pd.Timestamp(entry)+BAR

def eligible_case(r,t):
    return bool(r.mechanism=="M0_REFERENCE_INVALIDATION" and pd.notna(r.invalidation_close_ts) and pd.isna(r.h1_break_ts) and pd.Timestamp(r.invalidation_close_ts)>t and pd.Timestamp(r.exit_ts)>t)
def eligible_control(r,t):
    return bool(r.economic_win and pd.Timestamp(r.exit_ts)>t and (pd.isna(r.invalidation_close_ts) or pd.Timestamp(r.invalidation_close_ts)>t) and (pd.isna(r.h1_break_ts) or pd.Timestamp(r.h1_break_ts)>t))

def choose_control(pool,case,age,idx):
    z=[]
    for _,w in pool.iterrows():
        if case.partition=="development":
            cb=pd.to_numeric(pd.Series([case.dev_block]),errors="coerce").iloc[0]; wb=pd.to_numeric(pd.Series([w.dev_block]),errors="coerce").iloc[0]
            if pd.isna(cb) or pd.isna(wb) or int(cb)!=int(wb): continue
        t=lastbar(w.entry_ts,age)
        try: pos(idx,startbar(w.entry_ts)); pos(idx,t)
        except RuntimeError: continue
        if not eligible_control(w,t): continue
        d=abs((pd.Timestamp(w.execution_start)-pd.Timestamp(case.execution_start)).total_seconds())
        z.append((d,pd.Timestamp(w.execution_start),pd.Timestamp(w.entry_ts),w,t))
    if not z:return None
    z.sort(key=lambda x:(x[0],x[1],x[2])); return z[0][3],z[0][4]

def features(m,r,age):
    idx=m["idx"]; s=startbar(r.entry_ts); t=lastbar(r.entry_ts,age); a=pos(idx,s); b=pos(idx,t)
    hi=np.asarray(m["high"][a:b+1],float); lo=np.asarray(m["low"][a:b+1],float); cl=np.asarray(m["close"][a:b+1],float)
    H,L,R=float(r.H),float(r.L),float(r.R); mx=float(hi.max()); mn=float(lo.min()); c=float(cl[-1])
    f={"running_mfe_R":max(0.,(mx-H)/R),"running_mae_R":max(0.,(H-mn)/R),"close_H_R":(c-H)/R,"recovery_from_worst_R":(c-mn)/R,"drawdown_from_best_R":(mx-c)/R,"upper_half_close_fraction":float(np.mean(cl>=L+.5*R))}
    if R<=0 or not all(np.isfinite(v) for v in f.values()): raise RuntimeError(f"bad feature row {r.entry_ts} age {age}")
    return s,t,f

def stat(q,f):
    a=pd.to_numeric(q[f"case__{f}"],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna(); b=pd.to_numeric(q[f"control__{f}"],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna(); n=min(len(a),len(b))
    if not n:return dict(n=0,case_median=np.nan,control_median=np.nan,median_gap=np.nan,effect=np.nan)
    am=float(a.median()); bm=float(b.median()); g=am-bm; iq=(float(a.quantile(.75)-a.quantile(.25))+float(b.quantile(.75)-b.quantile(.25)))/2; e=abs(g)/iq if iq>EPS else (np.inf if abs(g)>EPS else 0.)
    return dict(n=n,case_median=am,control_median=bm,median_gap=g,effect=e)
def dirok(g,d): return bool(pd.notna(g) and ((d=="lower" and g<-EPS) or (d=="higher" and g>EPS)))

def run(context):
    root=Path(context["repo_root"]); out=Path(context["results_dir"]); out.mkdir(parents=True,exist_ok=True)
    a55=load_a55(root); x,cov=a55.a2.a1.load5(); m=a55.a2.make_market_with_open(x); idx=m["idx"]
    parents={p:a55.parent(m,p) for p in PARTS}; recon=[]; errs=[]
    for p,q in parents.items():
        pn=len(q); ln=int((~q.economic_win).sum()); n0=int((q.mechanism=="M0_REFERENCE_INVALIDATION").sum()); recon.append(dict(partition=p,parent_n=pn,loss_n=ln,l0_n=n0))
        if pn!=PARENT[p]:errs.append(f"{p} parent {pn}!={PARENT[p]}")
        if ln!=LOSSES[p]:errs.append(f"{p} losses {ln}!={LOSSES[p]}")
        if n0!=L0[p]:errs.append(f"{p} L0 {n0}!={L0[p]}")
    if errs: raise RuntimeError("; ".join(errs))
    recon=pd.DataFrame(recon); rows=[]; cover=[]
    for p,q in parents.items():
        cases=q[q.mechanism=="M0_REFERENCE_INVALIDATION"]; wins=q[q.economic_win]
        for age in AGES:
            eligible=matched=0; used=[]
            for _,r in cases.iterrows():
                t=lastbar(r.entry_ts,age); pos(idx,startbar(r.entry_ts)); pos(idx,t)
                if not eligible_case(r,t):continue
                eligible+=1; c=choose_control(wins,r,age,idx)
                if c is None:continue
                w,wt=c; cs,ct,cf=features(m,r,age); ws,wtt,wf=features(m,w,age); matched+=1; used.append(str(pd.Timestamp(w.entry_ts)))
                z={"partition":p,"snapshot_age_min":age,"case_entry_ts":r.entry_ts,"case_execution_start":r.execution_start,"case_dev_block":r.dev_block,"case_invalidation_close_ts":r.invalidation_close_ts,"case_measurement_start_ts":cs,"case_last_completed_bar_ts":ct,"case_pnl":float(r.pnl),"control_entry_ts":w.entry_ts,"control_execution_start":w.execution_start,"control_dev_block":w.dev_block,"control_break_ts":w.h1_break_ts,"control_exit_ts":w.exit_ts,"control_measurement_start_ts":ws,"control_last_completed_bar_ts":wtt,"control_pnl":float(w.pnl)}
                for f in DIR:z[f"case__{f}"]=cf[f];z[f"control__{f}"]=wf[f]
                rows.append(z)
            cc=Counter(used); cover.append(dict(partition=p,snapshot_age_min=age,l0_total=len(cases),eligible_l0_n=eligible,matched_n=matched,match_rate=matched/eligible if eligible else np.nan,unique_control_n=len(cc),reused_match_n=sum(max(0,v-1) for v in cc.values()),max_control_reuse=max(cc.values()) if cc else 0))
    ev=pd.DataFrame(rows); coverage=pd.DataFrame(cover)
    if ev.empty or ev.duplicated(["partition","snapshot_age_min","case_entry_ts"]).any():raise RuntimeError("empty or duplicate A62 events")
    blocks=[]
    for age in AGES:
      for f,d in DIR.items():
       for bi in range(6):
        s=stat(ev[(ev.partition=="development")&(ev.snapshot_age_min==age)&(pd.to_numeric(ev.case_dev_block,errors="coerce")==bi)],f); blocks.append(dict(snapshot_age_min=age,feature=f,direction=d,dev_block=bi,**s,adequate=s["n"]>=5,direction_ok=s["n"]>=5 and dirok(s["median_gap"],d)))
    blocks=pd.DataFrame(blocks); metrics=[]
    for p in PARTS:
      for age in AGES:
       for f,d in DIR.items():
        s=stat(ev[(ev.partition==p)&(ev.snapshot_age_min==age)],f); ab=gb=0; bok=False
        if p=="development":
            b=blocks[(blocks.snapshot_age_min==age)&(blocks.feature==f)]; a=b[b.adequate]; ab=len(a); gb=int(a.direction_ok.sum()); bok=ab>=3 and gb==ab
        metrics.append(dict(partition=p,snapshot_age_min=age,feature=f,direction=d,**s,direction_ok=dirok(s["median_gap"],d),adequate_dev_blocks=ab,same_direction_dev_blocks=gb,dev_block_rule_pass=bok))
    met=pd.DataFrame(metrics); met["development_eligible"]=False; met["oos_replication_pass"]=False; met["full_snapshot_replication"]=False; repl={f:[] for f in DIR}
    for age in AGES:
      for f in DIR:
        dm=(met.partition=="development")&(met.snapshot_age_min==age)&(met.feature==f); d=met[dm].iloc[0]; dp=bool(d.n>=20 and d.direction_ok and d.effect>=.30-EPS and d.dev_block_rule_pass); met.loc[dm,"development_eligible"]=dp; oo=[]
        for p in ("external","reference_validation"):
            mm=(met.partition==p)&(met.snapshot_age_min==age)&(met.feature==f); r=met[mm].iloc[0]; ok=bool(dp and r.n>=8 and r.direction_ok and r.effect>=.10-EPS);met.loc[mm,"oos_replication_pass"]=ok;oo.append(ok)
        full=dp and all(oo);met.loc[(met.snapshot_age_min==age)&(met.feature==f),"full_snapshot_replication"]=full
        if full:repl[f].append(age)
    supported=[f for f,a in repl.items() if len(a)>=2]; status="SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_SUPPORTED" if supported else "SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_INCONCLUSIVE"
    files={"EVENTS":ev,"COVERAGE":coverage,"METRICS":met,"BLOCKS":blocks,"RECONCILIATION":recon}; artifacts=[]
    for name,df in files.items():
        p=out/f"SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_{name}.csv";df.to_csv(p,index=False);artifacts.append(p)
    sp=out/"SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_Status.txt";sp.write_text(status+"\n");artifacts.append(sp)
    rp=out/"SOL_LONG_15UTC_L0_EARLY_PROGRESS_A62_Result.md"; lines=["# SOL LONG 15:00 UTC L0 Early Progress Anatomy — A62 Result","",f"**Gate status: {status}**","",f"Raw SOLUSDT 5m coverage: **{100*cov:.4f}%**.","","Entry touch/fill candle is excluded. A62 is descriptive only; live Baba Bot is unchanged.","","## Reconciliation","","| Partition | Parent | Losses | L0/M0 |","|---|---:|---:|---:|"]
    for _,r in recon.iterrows():lines.append(f"| {SHOW[r.partition]} | {int(r.parent_n)} | {int(r.loss_n)} | {int(r.l0_n)} |")
    lines += ["","## Snapshot matching","","| Partition | Age | Eligible | Matched | Unique controls | Max reuse |","|---|---:|---:|---:|---:|---:|"]
    for _,r in coverage.iterrows():lines.append(f"| {SHOW[r.partition]} | {int(r.snapshot_age_min)}m | {int(r.eligible_l0_n)} | {int(r.matched_n)} | {int(r.unique_control_n)} | {int(r.max_control_reuse)}x |")
    lines += ["","## Replication","","| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |","|---:|---|---:|---:|---:|---:|---|"]
    fmt=lambda v:"-" if pd.isna(v) else ("inf" if np.isinf(v) else f"{float(v):.3f}")
    for age in AGES:
      for f in DIR:
        d=met[(met.partition=="development")&(met.snapshot_age_min==age)&(met.feature==f)].iloc[0];e=met[(met.partition=="external")&(met.snapshot_age_min==age)&(met.feature==f)].iloc[0];r=met[(met.partition=="reference_validation")&(met.snapshot_age_min==age)&(met.feature==f)].iloc[0]
        lines.append(f"| {age}m | {f} | {fmt(d.median_gap)}/{fmt(d.effect)} | {int(d.same_direction_dev_blocks)}/{int(d.adequate_dev_blocks)} | {fmt(e.median_gap)}/{fmt(e.effect)} | {fmt(r.median_gap)}/{fmt(r.effect)} | {'YES' if d.full_snapshot_replication else 'NO'} |")
    lines += ["","## 2-of-3 family rule",""]+[f"- `{f}`: {repl[f] if repl[f] else 'none'} -> **{'SUPPORTED' if len(repl[f])>=2 else 'NO'}**" for f in DIR]+["",f"Supported families: **{', '.join(supported) if supported else 'none'}**.","","No threshold, composite, gate, derisk, or exit is authorized by A62. Any intervention requires a separate preregistered experiment.","","Research only. Live Baba Bot remains unchanged."]
    rp.write_text("\n".join(lines)+"\n");artifacts.append(rp)
    observed={"execution_parent":{"range":"R360","hour":"15UTC","entry":"E0_RESTING_H","target":"E40"},"central_losses_total":710,"l0_total":76,"partitions":{"Development":{"central_losses":357,"l0":37},"External Validation":{"central_losses":166,"l0":13},"Reference Validation":{"central_losses":187,"l0":26}}}
    summary={"gate_status":status,"market_coverage":float(cov),"supported_feature_families":supported,"replicated_snapshots_by_feature":repl,"matched_pairs_by_partition_snapshot":{f"{r.partition}:{int(r.snapshot_age_min)}m":int(r.matched_n) for _,r in coverage.iterrows()},"interpretation_boundary":"descriptive_only_no_executable_intervention"}
    return {"observed":observed,"summary":summary,"artifacts":[p.relative_to(root).as_posix() for p in artifacts]}
