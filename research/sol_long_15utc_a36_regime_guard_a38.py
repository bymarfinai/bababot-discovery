#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A37_PATH=Path(__file__).resolve().parent/"sol_long_15utc_a36_block_regime_a37.py"
spec=importlib.util.spec_from_file_location("a37",A37_PATH)
a37=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a37)
a36=a37.a36; a26=a37.a26; a2=a37.a2; CELLS=a36.CELLS

OUT_MD=ROOT/"SOL_LONG_15UTC_A36_REGIME_GUARD_A38_Result.md"
OUT_DEV=ROOT/"SOL_LONG_15UTC_A36_REGIME_GUARD_A38_DEVELOPMENT.csv"
OUT_OOS=ROOT/"SOL_LONG_15UTC_A36_REGIME_GUARD_A38_OOS.csv"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_A36_REGIME_GUARD_A38_TRADES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_A36_REGIME_GUARD_A38_Status.txt"
LANES=("G_MAE145","G_MFE279","G_BOTH")


def pf(v):
    x=pd.to_numeric(v,errors="coerce").dropna();gp=float(x[x>0].sum());gl=float(-x[x<=0].sum())
    if gl==0:return np.inf if gp>0 else np.nan
    return gp/gl

def fmt(v,d=2):
    if pd.isna(v):return "-"
    if np.isinf(v):return "inf"
    return f"{float(v):.{d}f}"
def pct(v):return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def apply_guard(t,lane):
    if t.empty:return t.copy()
    mae=pd.to_numeric(t.parent_mae_R,errors="coerce");mfe=pd.to_numeric(t.running_mfe_R_to_confirm,errors="coerce")
    if lane=="G_MAE145":q=t[mae<=.145]
    elif lane=="G_MFE279":q=t[mfe>=.279]
    else:q=t[(mae<=.145)&(mfe>=.279)]
    return q.copy()

def dev_row(parent,t,lane):
    s=a36.stats(parent,t);adequate=pos=pos5=0;blocks={}
    for bi in range(6):
        q=t[pd.to_numeric(t.dev_block,errors="coerce")==bi] if len(t) else t;n=len(q)
        net=float(pd.to_numeric(q.recovery_pnl,errors="coerce").sum()) if n else 0.;net5=float(pd.to_numeric(q.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.
        blocks[f"b{bi+1}_n"]=n;blocks[f"b{bi+1}_net"]=net;blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=2:
            adequate+=1;pos+=int(net>0);pos5+=int(net5>0)
    up=s["episode_wr"]-s["parent_wr"];up5=s["episode_wr_5bps"]-s["parent_wr_5bps"]
    eligible=bool(
      s["recovery_n"]>=15 and s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and
      s["recovery_pf"]>1.25 and s["recovery_pf_5bps"]>1.05 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and
      s["overlay_net"]>s["parent_net"] and s["overlay_net_5bps"]>s["parent_net_5bps"] and
      s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and
      up>=.02 and up5>=.01 and s["rescue_rate"]>=.40 and adequate>=4 and pos>=4 and pos5>=4)
    return {"lane":lane,**s,"episode_wr_uplift":up,"episode_wr_uplift_5bps":up5,"adequate_blocks":adequate,"positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}

def choose(dev):
    q=dev[dev.eligible.astype(bool)].copy()
    if q.empty:return None
    simp={"G_MAE145":0,"G_MFE279":0,"G_BOTH":1};q["complexity"]=q.lane.map(simp)
    return q.sort_values(["overlay_net_improvement_5bps","recovery_pf_5bps","overlay_net_improvement","episode_wr_uplift","complexity"],ascending=[False,False,False,False,True]).iloc[0]

def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15);base=a37.build_cell(m,"development","CENTRAL",360,15)
    rows=[];frames={}
    for lane in LANES:
        t=apply_guard(base,lane);frames[lane]=t;rows.append(dev_row(pdev,t,lane))
    dev=pd.DataFrame(rows);dev.to_csv(OUT_DEV,index=False);winner=choose(dev)
    oosrows=[];alltr=[]
    if winner is not None:
        lane=str(winner.lane);z=frames[lane].copy();z["scope"]="DEVELOPMENT_FROZEN";alltr.append(z)
        for role,ref,hour in CELLS:
            for part in ("external","reference_validation"):
                p=a26.parent_cell(m,part,role,ref,hour);bt=a37.build_cell(m,part,role,ref,hour);t=apply_guard(bt,lane);s=a36.stats(p,t)
                oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,"lane":lane,**s})
                if len(t):q=t.copy();q["scope"]="OOS";alltr.append(q)
    oos=pd.DataFrame(oosrows);oos.to_csv(OUT_OOS,index=False)
    if winner is None:status="SOL_LONG_15UTC_A36_REGIME_GUARD_A38_REJECTED_DEVELOPMENT"
    else:
        central=oos[oos.role=="CENTRAL"];support=oos[(oos.role!="CENTRAL") & (oos.partition.isin(["external","reference_validation"]))]
        central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and
          (central.overlay_net>central.parent_net).all() and (central.overlay_net_5bps>central.parent_net_5bps).all() and
          (central.overlay_pf>central.parent_pf).all() and (central.overlay_pf_5bps>central.parent_pf_5bps).all() and
          ((central.episode_wr-central.parent_wr)>=0).all() and ((central.episode_wr_5bps-central.parent_wr_5bps)>=0).all())
        raw=int((support.recovery_net>0).sum());st=int((support.recovery_net_5bps>0).sum());ov=int((support.overlay_net>support.parent_net).sum());ov5=int((support.overlay_net_5bps>support.parent_net_5bps).sum())
        status="SOL_LONG_15UTC_A36_REGIME_GUARD_A38_SUPPORTED" if central_ok and len(support)==4 and raw>=3 and st>=3 and ov>=3 and ov5>=3 else "SOL_LONG_15UTC_A36_REGIME_GUARD_A38_REJECTED_OOS"
    (pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()).to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG 15:00 UTC A36 Regime Guard — A38 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A38 applies only the corrected A37B Development-midpoint guards to the exact A36 recovery.","","## Development","",
      "| Lane | N | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay | +blocks raw/stress | Pass |","|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|"]
    for _,r in dev.iterrows():lines.append(f"| {r.lane} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.rescue_rate)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["",f"Frozen Development winner: **{str(winner.lane) if winner is not None else 'NONE'}**.",""]
    if len(oos):
        lines += ["## Frozen OOS","","| Role | Partition | N | Rec WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
        for _,r in oos.iterrows():lines.append(f"| {r.role} | {r.partition} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","No neighboring MAE/MFE threshold scan or OOS retuning is authorized after A38.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)
if __name__=="__main__":main()
