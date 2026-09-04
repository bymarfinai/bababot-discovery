#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A17_PATH = Path(__file__).resolve().parent / "sol_long_multi_clock_expansion_a17.py"
spec = importlib.util.spec_from_file_location("a17", A17_PATH)
a17 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a17)
a4 = a17.a4; a3 = a4.a3; a2 = a17.a2

OUT_MD = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_Result.md"
OUT_LOSSES = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_LOSSES.csv"
OUT_SNAP = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_SNAPSHOTS.csv"
OUT_SEP = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_SEPARATION.csv"
OUT_TAX = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_TAXONOMY.csv"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_LOSS_CONVERSION_A26_Status.txt"

TARGET_R = 0.40
SNAPS = (5,10,15,30,60)
CELLS = [("CENTRAL",360,15),("CLOCK_SUPPORT",360,16),("REF_SUPPORT",300,15)]
EPS=1e-12


def fmt(v,d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def parent_cell(m, part, role, ref, hour):
    q=a17.simulate_cell(m,part,ref,hour,"A26",role).copy()
    if q.empty: return q
    q["loss_class"]=[a3.loss_class(r) for _,r in q.iterrows()]
    return q

def path_features(m,r):
    idx=m["idx"]; hi=m["high"]; lo=m["low"]
    ei=int(idx.searchsorted(pd.Timestamp(r.entry_ts),"left")); xi=int(idx.searchsorted(pd.Timestamp(r.exit_ts),"left"))
    seg_hi=np.asarray(hi[ei:xi+1],float); seg_lo=np.asarray(lo[ei:xi+1],float)
    H=float(r.H); R=float(r.R)
    return {
      "mfe_R":max(0.0,(float(seg_hi.max())-H)/R),
      "mae_R":max(0.0,(H-float(seg_lo.min()))/R),
      "hold_min":float((pd.Timestamp(r.exit_ts)-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1)),
      "entry_to_break_min":float((pd.Timestamp(r.h1_break_ts)-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1)) if pd.notna(r.h1_break_ts) else np.nan,
      "break_to_fail_min":float((pd.Timestamp(r.invalidation_close_ts)-pd.Timestamp(r.h1_break_ts))/pd.Timedelta(minutes=1)) if pd.notna(r.h1_break_ts) and pd.notna(r.invalidation_close_ts) else np.nan,
    }

def post_exit_anatomy(m,r):
    w=a4.recovery_window(m,r)
    if w is None: return None,[]
    _,xi,endpos,eps=w; idx=m["idx"]; hi=m["high"]; lo=m["low"]; cl=m["close"]
    H=float(r.H); R=float(r.R); target=H+TARGET_R*R
    hit=-1
    for i in range(xi,endpos):
        if float(hi[i])>=target: hit=i; break
    reclaim=-1
    for i in range(xi,endpos):
        if float(cl[i])>H: reclaim=i; break
    target_after_reclaim=-1
    if reclaim>=0:
        for i in range(reclaim+1,endpos):
            if float(hi[i])>=target: target_after_reclaim=i; break
    target_visit=np.nan; eligible=False
    if hit>=0:
        for j,st in enumerate(eps,start=1):
            nxt=eps[j] if j<len(eps) else endpos
            if st<=hit<nxt:
                target_visit=j; eligible=st>=xi; break
    base={
      "latent_class":"LATENT_RECOVERABLE" if hit>=0 else "TRUE_FAILURE_PROXY",
      "latent_target_recovered":hit>=0,
      "latent_recovery_min":float((idx[hit]-pd.Timestamp(r.exit_ts))/pd.Timedelta(minutes=1)) if hit>=0 else np.nan,
      "latent_target_visit":target_visit,
      "latent_target_visit_entry_eligible":eligible,
      "post_exit_reclaim":reclaim>=0,
      "reclaim_min":float((idx[reclaim]-pd.Timestamp(r.exit_ts))/pd.Timedelta(minutes=1)) if reclaim>=0 else np.nan,
      "target_after_reclaim":target_after_reclaim>=0,
      "reclaim_to_target_min":float((idx[target_after_reclaim]-idx[reclaim])/pd.Timedelta(minutes=1)) if target_after_reclaim>=0 else np.nan,
      "visit_count":len(eps),
    }
    snaps=[]
    for sm in SNAPS:
        si=xi+(sm//5)-1
        if si>=endpos: continue
        sh=np.asarray(hi[xi:si+1],float); sl=np.asarray(lo[xi:si+1],float); sc=np.asarray(cl[xi:si+1],float)
        snaps.append({
          "snapshot_min":sm,
          "close_R":(float(sc[-1])-H)/R,
          "running_mfe_R":max(0.0,(float(sh.max())-H)/R),
          "running_mae_R":max(0.0,(H-float(sl.min()))/R),
          "closes_above_H":int((sc>H).sum()),
          "closes_le_H":int((sc<=H).sum()),
          "reclaim_by_snapshot":bool((sc>H).any()),
        })
    return base,snaps

def build(m):
    losses=[]; snaps=[]
    for role,ref,hour in CELLS:
      for part in ("development","external","reference_validation"):
        q=parent_cell(m,part,role,ref,hour)
        for _,r in q[q.pnl<=0].iterrows():
          post,ss=post_exit_anatomy(m,r)
          if post is None: continue
          row={"role":role,"partition":part,"ref_min":ref,"hour":hour,"dev_block":r.dev_block,
               "execution_start":r.execution_start,"entry_ts":r.entry_ts,"exit_ts":r.exit_ts,"H":r.H,"L":r.L,"R":r.R,
               "pnl":float(r.pnl),"pnl_5bps":float(r.pnl_5bps),"loss_class":r.loss_class,**path_features(m,r),**post}
          losses.append(row)
          for z in ss:
            snaps.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,"entry_ts":r.entry_ts,
                          "loss_class":r.loss_class,"latent_class":post["latent_class"],**z})
    return pd.DataFrame(losses),pd.DataFrame(snaps)

def taxonomy(losses):
    rows=[]
    for (role,part,lc),q in losses.groupby(["role","partition","loss_class"],sort=False):
      gl=float(-q.pnl.sum())
      rows.append({"role":role,"partition":part,"loss_class":lc,"n":len(q),"gross_loss":gl,
                   "median_loss":float((-q.pnl).median()),"latent_rate":float(q.latent_target_recovered.mean()),
                   "median_recovery_min":float(q.loc[q.latent_target_recovered,"latent_recovery_min"].median()) if q.latent_target_recovered.any() else np.nan,
                   "median_target_visit":float(q.loc[q.latent_target_recovered,"latent_target_visit"].median()) if q.latent_target_recovered.any() else np.nan,
                   "reclaim_rate":float(q.post_exit_reclaim.mean()),"target_after_reclaim_rate":float(q.target_after_reclaim.mean())})
    return pd.DataFrame(rows)

def separation(losses,snaps):
    rows=[]
    base_features=["mfe_R","mae_R","hold_min","entry_to_break_min","break_to_fail_min","reclaim_min","visit_count"]
    for (role,part),q in losses.groupby(["role","partition"],sort=False):
      a=q[q.latent_class=="LATENT_RECOVERABLE"]; b=q[q.latent_class=="TRUE_FAILURE_PROXY"]
      if len(a)<10 or len(b)<10: continue
      for f in base_features:
        x=pd.to_numeric(a[f],errors="coerce").dropna(); y=pd.to_numeric(b[f],errors="coerce").dropna()
        if len(x)>=10 and len(y)>=10:
          rows.append({"role":role,"partition":part,"snapshot_min":0,"feature":f,"latent_n":len(x),"true_n":len(y),
                       "latent_median":float(x.median()),"true_median":float(y.median()),"gap":float(x.median()-y.median())})
    for (role,part,sm),q in snaps.groupby(["role","partition","snapshot_min"],sort=False):
      a=q[q.latent_class=="LATENT_RECOVERABLE"]; b=q[q.latent_class=="TRUE_FAILURE_PROXY"]
      if len(a)<10 or len(b)<10: continue
      for f in ["close_R","running_mfe_R","running_mae_R","closes_above_H","closes_le_H","reclaim_by_snapshot"]:
        x=pd.to_numeric(a[f],errors="coerce").dropna().astype(float); y=pd.to_numeric(b[f],errors="coerce").dropna().astype(float)
        if len(x)>=10 and len(y)>=10:
          rows.append({"role":role,"partition":part,"snapshot_min":sm,"feature":f,"latent_n":len(x),"true_n":len(y),
                       "latent_median":float(x.median()),"true_median":float(y.median()),"gap":float(x.median()-y.median())})
    return pd.DataFrame(rows)

def replication(sep):
    dev=sep[(sep.role=="CENTRAL")&(sep.partition=="development")].copy()
    ext=sep[(sep.role=="CENTRAL")&(sep.partition=="external")][["snapshot_min","feature","gap"]].rename(columns={"gap":"gap_ext"})
    rv=sep[(sep.role=="CENTRAL")&(sep.partition=="reference_validation")][["snapshot_min","feature","gap"]].rename(columns={"gap":"gap_rv"})
    z=dev.merge(ext,on=["snapshot_min","feature"],how="left").merge(rv,on=["snapshot_min","feature"],how="left")
    z=z.rename(columns={"gap":"gap_dev"})
    support=sep[sep.role!="CENTRAL"]
    counts=[]
    for _,r in z.iterrows():
      s=support[(support.snapshot_min==r.snapshot_min)&(support.feature==r.feature)]
      sg=np.sign(float(r.gap_dev))
      support_same=int((np.sign(pd.to_numeric(s.gap,errors="coerce"))==sg).sum()) if sg!=0 else 0
      counts.append(support_same)
    z["support_same_direction"]=counts
    z["central_replicated"]=(np.sign(z.gap_dev)!=0)&(np.sign(z.gap_dev)==np.sign(z.gap_ext))&(np.sign(z.gap_dev)==np.sign(z.gap_rv))
    z["strong_replicated"]=z.central_replicated&(z.support_same_direction>=3)
    return z

def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    losses,snaps=build(m); tax=taxonomy(losses); sep=separation(losses,snaps); rep=replication(sep)
    losses.to_csv(OUT_LOSSES,index=False); snaps.to_csv(OUT_SNAP,index=False); tax.to_csv(OUT_TAX,index=False); rep.to_csv(OUT_SEP,index=False)
    cd=losses[(losses.role=="CENTRAL")&(losses.partition=="development")]
    lat=cd[cd.latent_class=="LATENT_RECOVERABLE"]; tru=cd[cd.latent_class=="TRUE_FAILURE_PROXY"]
    gl=float(-cd.pnl.sum()); latgl=float(-lat.pnl.sum())
    cohort_ok=(len(lat)>=80 and len(tru)>=80) or (len(lat)>=0.25*len(cd) and len(tru)>=0.25*len(cd))
    material=(len(lat)/len(cd)>=0.20 if len(cd) else False) or (latgl/gl>=0.20 if gl>0 else False)
    central_n=int(rep.central_replicated.sum()); strong_n=int(rep.strong_replicated.sum())
    supported=bool(cohort_ok and material and central_n>=5 and strong_n>=3)
    status="SOL_LONG_15UTC_LOSS_CONVERSION_A26_SUPPORTED_FOR_A27" if supported else "SOL_LONG_15UTC_LOSS_CONVERSION_A26_INCONCLUSIVE"
    lines=["# SOL LONG 15:00 UTC Loss Conversion Anatomy — A26 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A26 is forensic only. The A20 R360/15 parent is unchanged and A23 recovery remains rejected.","",
      "## Central Development loss opportunity","",
      "| Losers | Latent recoverable | True-failure proxy | Latent share | Latent loss-$ share | Median recovery | Median target visit | Post-exit reclaim | E40 after reclaim |",
      "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
      f"| {len(cd)} | {len(lat)} | {len(tru)} | {pct(len(lat)/len(cd) if len(cd) else np.nan)} | {pct(latgl/gl if gl>0 else np.nan)} | {fmt(lat.latent_recovery_min.median(),0)}m | {fmt(lat.latent_target_visit.median(),1)} | {pct(lat.post_exit_reclaim.mean() if len(lat) else np.nan)} | {pct(lat.target_after_reclaim.mean() if len(lat) else np.nan)} |","",
      "## Central Development taxonomy","","| Loss class | N | Gross loss | Latent→E40 | Median recovery | Median target visit | Reclaim | E40 after reclaim |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in tax[(tax.role=="CENTRAL")&(tax.partition=="development")].sort_values("gross_loss",ascending=False).iterrows():
      lines.append(f"| {r.loss_class} | {int(r.n)} | ${fmt(r.gross_loss)} | {pct(r.latent_rate)} | {fmt(r.median_recovery_min,0)}m | {fmt(r.median_target_visit,1)} | {pct(r.reclaim_rate)} | {pct(r.target_after_reclaim_rate)} |")
    lines += ["","## Replicated causal separation","","| Snap | Feature | Latent median | True-failure median | Dev gap | Ext gap | RefVal gap | Support same dir |","|---:|---|---:|---:|---:|---:|---:|---:|"]
    rr=rep[rep.central_replicated].copy().sort_values(["strong_replicated","snapshot_min"],ascending=[False,True])
    for _,r in rr.head(20).iterrows():
      lines.append(f"| {'path' if int(r.snapshot_min)==0 else '+'+str(int(r.snapshot_min))+'m'} | {r.feature} | {fmt(r.latent_median,3)} | {fmt(r.true_median,3)} | {fmt(r.gap_dev,3)} | {fmt(r.gap_ext,3)} | {fmt(r.gap_rv,3)} | {int(r.support_same_direction)}/4 |")
    lines += ["","## Decision","",f"Central replicated dimensions: **{central_n}**; strong replicated (>=3/4 supports): **{strong_n}**.","",f"**Status: {status}**","",
      "If supported, A27 must convert the replicated anatomy into a small preregistered causal recovery-state family. No threshold grid and no OOS retuning.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)
if __name__=="__main__": main()
