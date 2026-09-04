#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
IN_TRADES=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_TRADES.csv"
OUT_MD=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37B_Result.md"
OUT_SEP=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37B_SEPARATION.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37B_Status.txt"

FEATURES=[
 "parent_loss_R","parent_mfe_R","parent_mae_R","parent_hold_min","ref_width_pct",
 "exit_to_signal_min","signal_to_confirm_min","signal_close_R","confirm_close_R","confirm_body_R",
 "max_close_R_to_confirm","running_mfe_R_to_confirm","running_mae_R_to_confirm","above_H_frac_to_confirm",
 "closes_above_H_to_confirm","reentry_R","preconfirm_30m_return_R","preexit_60m_return_R","preexit_60m_range_R"
]

def fmt(v,d=3):
    if pd.isna(v): return "-"
    return f"{float(v):.{d}f}"

def robust_sep(q,f):
    w=pd.to_numeric(q.loc[q.stress_outcome=="WIN",f],errors="coerce").dropna()
    l=pd.to_numeric(q.loc[q.stress_outcome=="FAIL",f],errors="coerce").dropna()
    if len(w)<4 or len(l)<4:return None
    wm=float(w.median());lm=float(l.median());gap=wm-lm
    wi=float(w.quantile(.75)-w.quantile(.25));li=float(l.quantile(.75)-l.quantile(.25));pooled=(wi+li)/2
    eff=abs(gap)/pooled if pooled>1e-12 else (np.inf if abs(gap)>1e-12 else 0.0)
    return len(w),len(l),wm,lm,gap,eff

def main():
    t=pd.read_csv(IN_TRADES)
    rows=[]
    for (role,part),q in t.groupby(["role","partition"],sort=False):
        for f in FEATURES:
            z=robust_sep(q,f)
            if z is None:continue
            wn,ln,wm,lm,gap,eff=z
            rows.append({"role":role,"partition":part,"feature":f,"win_n":wn,"fail_n":ln,"win_median":wm,"fail_median":lm,"gap":gap,"effect":eff})
    s=pd.DataFrame(rows)
    dev=s[(s.role=="CENTRAL")&(s.partition=="development")].copy()
    ext=s[(s.role=="CENTRAL")&(s.partition=="external")][["feature","gap"]].rename(columns={"gap":"gap_ext"})
    rv=s[(s.role=="CENTRAL")&(s.partition=="reference_validation")][["feature","gap"]].rename(columns={"gap":"gap_rv"})
    z=dev.merge(ext,on="feature",how="left").merge(rv,on="feature",how="left").rename(columns={"gap":"gap_dev","effect":"effect_dev"})
    supports=s[(s.role!="CENTRAL") & (s.partition.isin(["external","reference_validation"]))]
    same=[];avail=[]
    for _,r in z.iterrows():
        ss=supports[supports.feature==r.feature];sg=np.sign(float(r.gap_dev));dirs=np.sign(pd.to_numeric(ss.gap,errors="coerce"))
        same.append(int((dirs==sg).sum()) if sg!=0 else 0);avail.append(len(ss))
    z["support_same_direction"]=same;z["support_available"]=avail
    z["material_dev"]=z.effect_dev>=0.50
    z["central_replicated"]=z.material_dev & (np.sign(z.gap_dev)!=0) & (np.sign(z.gap_dev)==np.sign(z.gap_ext)) & (np.sign(z.gap_dev)==np.sign(z.gap_rv))
    z["strong_replicated"]=z.central_replicated & (z.support_available==4) & (z.support_same_direction>=3)
    z.to_csv(OUT_SEP,index=False)
    strong=z[z.strong_replicated].sort_values(["effect_dev","support_same_direction"],ascending=[False,False])
    status="SOL_LONG_15UTC_A36_BLOCK_REGIME_A37B_SUPPORTED_FOR_A38" if len(strong)>=2 else "SOL_LONG_15UTC_A36_BLOCK_REGIME_A37B_INCONCLUSIVE"
    lines=["# SOL LONG 15:00 UTC A36 Block / Regime Anatomy — A37B Corrected Result","",
      "A37B corrects only the topology support counter. Exact A37 trade ledger and medians are reused.","",
      "## Strong replicated pre-entry separation","","| Feature | Stress-win median | Stress-fail median | Dev gap | Robust effect | External gap | RefVal gap | Support same dir |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    if len(strong):
        for _,r in strong.iterrows():lines.append(f"| {r.feature} | {fmt(r.win_median)} | {fmt(r.fail_median)} | {fmt(r.gap_dev)} | {fmt(r.effect_dev,2)} | {fmt(r.gap_ext)} | {fmt(r.gap_rv)} | {int(r.support_same_direction)}/4 |")
    else:lines.append("| none | - | - | - | - | - | - | - |")
    lines += ["","## Decision","",f"Corrected strong replicated features: **{len(strong)}**.","",f"**Status: {status}**","",
      "A38 is authorized only if this corrected report retains at least two strong replicated features. No threshold grid or OOS retuning.",""]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)

if __name__=="__main__":main()
