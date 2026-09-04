#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A27_PATH=Path(__file__).resolve().parent/"sol_long_15utc_reclaim_conversion_a27.py"
spec=importlib.util.spec_from_file_location("a27",A27_PATH)
a27=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a27)
a26=a27.a26; a4=a27.a4; a2=a27.a2

OUT_MD=ROOT/"SOL_LONG_15UTC_RC30C2_RESCUE_ANATOMY_A28_Result.md"
OUT_COHORT=ROOT/"SOL_LONG_15UTC_RC30C2_RESCUE_ANATOMY_A28_COHORT.csv"
OUT_SEP=ROOT/"SOL_LONG_15UTC_RC30C2_RESCUE_ANATOMY_A28_SEPARATION.csv"
OUT_CLASS=ROOT/"SOL_LONG_15UTC_RC30C2_RESCUE_ANATOMY_A28_LOSS_CLASSES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_RC30C2_RESCUE_ANATOMY_A28_Status.txt"
CELLS=a27.CELLS; LANE="RC30_C2"

def fmt(v,d=3):
    if pd.isna(v): return "-"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def feature_row(m,p,t):
    idx=m["idx"]; op=m["open"]; hi=m["high"]; lo=m["low"]; cl=m["close"]
    xi=int(idx.searchsorted(pd.Timestamp(p.exit_ts),"left")); si=int(idx.searchsorted(pd.Timestamp(t.signal_ts),"left"))
    if xi>=len(idx) or si>=len(idx) or idx[xi]!=pd.Timestamp(p.exit_ts) or idx[si]!=pd.Timestamp(t.signal_ts): return None
    H=float(p.H); R=float(p.R)
    first=-1
    for i in range(xi,si+1):
        if float(cl[i])>H: first=i; break
    if first<0:return None
    seg_hi=np.asarray(hi[xi:si+1],float); seg_lo=np.asarray(lo[xi:si+1],float); seg_cl=np.asarray(cl[xi:si+1],float)
    max_close_R=(float(seg_cl.max())-H)/R; signal_close_R=(float(cl[si])-H)/R
    o=float(op[si]); h=float(hi[si]); l=float(lo[si]); c=float(cl[si]); rng=h-l
    pf=a26.path_features(m,p)
    if float(t.combined_episode_pnl)>0: oc="EPISODE_RESCUE"
    elif float(t.recovery_pnl)>0: oc="RECOVERY_WIN_NOT_RESCUE"
    else: oc="RECOVERY_FAIL"
    return {
      "role":p.role,"partition":p.partition,"ref_min":getattr(p,"ref_min",np.nan),"hour":getattr(p,"hour",np.nan),"dev_block":p.dev_block,
      "entry_ts":p.entry_ts,"parent_exit_ts":p.exit_ts,"signal_ts":t.signal_ts,"reentry_ts":t.reentry_ts,"outcome_class":oc,"rescued":oc=="EPISODE_RESCUE",
      "loss_class":p.loss_class,"parent_pnl":float(p.pnl),"parent_pnl_5bps":float(p.pnl_5bps),"parent_loss_return":float(-p.pnl/a2.NOTIONAL),
      "parent_mfe_R":pf["mfe_R"],"parent_mae_R":pf["mae_R"],"parent_hold_min":pf["hold_min"],
      "signal_delay_min":float((si-xi+1)*5),"first_reclaim_delay_min":float((first-xi+1)*5),"first_to_second_gap_min":float((si-first)*5),
      "consecutive_two":bool(si-1>=xi and float(cl[si-1])>H),"closes_le_H_before_signal":int((seg_cl<=H).sum()),
      "first_reclaim_close_R":(float(cl[first])-H)/R,"signal_close_R":signal_close_R,"max_close_R_to_signal":max_close_R,
      "running_mfe_R_to_signal":max(0.,(float(seg_hi.max())-H)/R),"running_mae_R_to_signal":max(0.,(H-float(seg_lo.min()))/R),
      "giveback_R_to_signal":max_close_R-signal_close_R,"signal_body_R":(c-o)/R,"signal_upper_wick_R":(h-max(o,c))/R,"signal_lower_wick_R":(min(o,c)-l)/R,
      "signal_close_location":(c-l)/rng if rng>0 else .5,"recovery_pnl":float(t.recovery_pnl),"combined_episode_pnl":float(t.combined_episode_pnl)}

def build(m):
    rows=[]
    for role,ref,hour in CELLS:
      for part in ("development","external","reference_validation"):
        p=a26.parent_cell(m,part,role,ref,hour); pm={pd.Timestamp(r.entry_ts):r for _,r in p.iterrows()}
        t=a27.simulate_lane(m,p,LANE)
        for _,z in t.iterrows():
          pr=pm.get(pd.Timestamp(z.parent_entry_ts));
          if pr is None: continue
          rr=feature_row(m,pr,z)
          if rr is not None: rr["ref_min"]=ref; rr["hour"]=hour; rows.append(rr)
    return pd.DataFrame(rows)

def sep(cohort):
    features=["parent_loss_return","parent_mfe_R","parent_mae_R","parent_hold_min","signal_delay_min","first_reclaim_delay_min","first_to_second_gap_min","consecutive_two","closes_le_H_before_signal","first_reclaim_close_R","signal_close_R","max_close_R_to_signal","running_mfe_R_to_signal","running_mae_R_to_signal","giveback_R_to_signal","signal_body_R","signal_upper_wick_R","signal_lower_wick_R","signal_close_location"]
    rows=[]
    for (role,part),q in cohort.groupby(["role","partition"],sort=False):
      a=q[q.rescued]; b=q[~q.rescued]
      if len(a)<10 or len(b)<10: continue
      for f in features:
        x=pd.to_numeric(a[f],errors="coerce").dropna().astype(float); y=pd.to_numeric(b[f],errors="coerce").dropna().astype(float)
        if len(x)<10 or len(y)<10: continue
        rows.append({"role":role,"partition":part,"feature":f,"rescue_n":len(x),"nonrescue_n":len(y),"rescue_median":float(x.median()),"nonrescue_median":float(y.median()),"gap":float(x.median()-y.median())})
    raw=pd.DataFrame(rows)
    dev=raw[(raw.role=="CENTRAL")&(raw.partition=="development")].copy()
    ext=raw[(raw.role=="CENTRAL")&(raw.partition=="external")][["feature","gap"]].rename(columns={"gap":"gap_ext"})
    rv=raw[(raw.role=="CENTRAL")&(raw.partition=="reference_validation")][["feature","gap"]].rename(columns={"gap":"gap_rv"})
    z=dev.merge(ext,on="feature",how="left").merge(rv,on="feature",how="left").rename(columns={"gap":"gap_dev"})
    support=raw[(raw.role!="CENTRAL")&raw.partition.isin(["external","reference_validation"])]
    cnt=[]
    for _,r in z.iterrows():
      s=support[support.feature==r.feature]; sg=np.sign(float(r.gap_dev)); cnt.append(int((np.sign(pd.to_numeric(s.gap,errors="coerce"))==sg).sum()) if sg!=0 else 0)
    z["support_same_direction"]=cnt
    z["central_replicated"]=(np.sign(z.gap_dev)!=0)&(np.sign(z.gap_dev)==np.sign(z.gap_ext))&(np.sign(z.gap_dev)==np.sign(z.gap_rv))
    z["strong_replicated"]=z.central_replicated&(z.support_same_direction>=3)
    return z

def class_summary(cohort):
    rows=[]
    for (role,part,lc),q in cohort.groupby(["role","partition","loss_class"],sort=False):
      rows.append({"role":role,"partition":part,"loss_class":lc,"n":len(q),"rescue_rate":float(q.rescued.mean()),"recovery_win_rate":float((q.recovery_pnl>0).mean()),"median_parent_loss":float((-q.parent_pnl).median()),"median_signal_delay":float(q.signal_delay_min.median())})
    return pd.DataFrame(rows)

def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    cohort=build(m); separation=sep(cohort); classes=class_summary(cohort)
    cohort.to_csv(OUT_COHORT,index=False); separation.to_csv(OUT_SEP,index=False); classes.to_csv(OUT_CLASS,index=False)
    cd=cohort[(cohort.role=="CENTRAL")&(cohort.partition=="development")]; resc=cd[cd.rescued]; non=cd[~cd.rescued]
    central_n=int(separation.central_replicated.sum()); strong_n=int(separation.strong_replicated.sum())
    supported=bool(len(resc)>=40 and len(non)>=40 and central_n>=4 and strong_n>=2)
    status="SOL_LONG_15UTC_RC30C2_RESCUE_A28_SUPPORTED_FOR_A29" if supported else "SOL_LONG_15UTC_RC30C2_RESCUE_A28_INCONCLUSIVE"
    lines=["# SOL LONG 15:00 UTC RC30_C2 Rescue Anatomy — A28 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A28 is forensic only and studies the exact A27 RC30_C2 trigger cohort.","","## Central Development cohort","",
      "| Trigger N | Episode rescues | Recovery-win-not-rescue | Recovery fails | Rescue rate |","|---:|---:|---:|---:|---:|",
      f"| {len(cd)} | {len(resc)} | {int((cd.outcome_class=='RECOVERY_WIN_NOT_RESCUE').sum())} | {int((cd.outcome_class=='RECOVERY_FAIL').sum())} | {pct(cd.rescued.mean())} |","",
      "## Loss-class rescue anatomy","","| Loss class | N | Rescue rate | Recovery win rate | Median parent loss | Median signal delay |","|---|---:|---:|---:|---:|---:|"]
    for _,r in classes[(classes.role=="CENTRAL")&(classes.partition=="development")].sort_values("rescue_rate",ascending=False).iterrows():
      lines.append(f"| {r.loss_class} | {int(r.n)} | {pct(r.rescue_rate)} | {pct(r.recovery_win_rate)} | ${fmt(r.median_parent_loss,2)} | {fmt(r.median_signal_delay,0)}m |")
    lines += ["","## Replicated causal separation","","| Feature | Rescue median | Non-rescue median | Dev gap | External gap | RefVal gap | Support same dir |","|---|---:|---:|---:|---:|---:|---:|"]
    for _,r in separation[separation.central_replicated].sort_values(["strong_replicated","feature"],ascending=[False,True]).iterrows():
      lines.append(f"| {r.feature} | {fmt(r.rescue_median)} | {fmt(r.nonrescue_median)} | {fmt(r.gap_dev)} | {fmt(r.gap_ext)} | {fmt(r.gap_rv)} | {int(r.support_same_direction)}/4 |")
    lines += ["","## Decision","",f"Central replicated={central_n}; strong replicated={strong_n}.","",f"**Status: {status}**","",
      "If supported, A29 may guard RC30_C2 using at most three robust causal features. No threshold grid and no OOS retuning.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)
if __name__=="__main__": main()
