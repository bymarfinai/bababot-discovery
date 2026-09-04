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
a26=a27.a26; a2=a27.a2; CELLS=a27.CELLS

OUT_MD=ROOT/"SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_Result.md"
OUT_DEV=ROOT/"SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_DEVELOPMENT.csv"
OUT_OOS=ROOT/"SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_OOS.csv"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_TRADES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_Status.txt"


def pf(v):
    x=pd.to_numeric(v,errors="coerce").dropna();gp=float(x[x>0].sum());gl=float(-x[x<=0].sum())
    if gl==0:return np.inf if gp>0 else np.nan
    return gp/gl

def fmt(v,d=2):
    if pd.isna(v):return "-"
    if np.isinf(v):return "inf"
    return f"{float(v):.{d}f}"
def pct(v):return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def guarded(m,parent):
    base=a27.simulate_lane(m,parent,"RC30_C2")
    pmap={pd.Timestamp(r.entry_ts):r for _,r in parent.iterrows()}
    rows=[]
    for _,z in base.iterrows():
        r=pmap.get(pd.Timestamp(z.parent_entry_ts))
        if r is None:continue
        mae=float(a26.path_features(m,r)["mae_R"])
        if mae<=.145:
            d=z.to_dict();d["parent_mae_R"]=mae;rows.append(d)
    return pd.DataFrame(rows)

def dev_stats(parent,t):
    s=a27.stats(parent,t);adequate=pos=pos5=0;blocks={}
    for bi in range(6):
        q=t[pd.to_numeric(t.dev_block,errors="coerce")==bi] if len(t) else t;n=len(q)
        net=float(pd.to_numeric(q.recovery_pnl,errors="coerce").sum()) if n else 0.;net5=float(pd.to_numeric(q.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.
        blocks[f"b{bi+1}_n"]=n;blocks[f"b{bi+1}_net"]=net;blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=4:
            adequate+=1;pos+=int(net>0);pos5+=int(net5>0)
    up=s["episode_wr"]-s["parent_wr"];up5=s["episode_wr_5bps"]-s["parent_wr_5bps"]
    eligible=bool(s["recovery_n"]>=40 and s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and
      s["recovery_pf"]>1.20 and s["recovery_pf_5bps"]>1.05 and s["overlay_net"]>s["parent_net"] and s["overlay_net_5bps"]>s["parent_net_5bps"] and
      s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and up>=.04 and up5>=.03 and s["rescue_rate"]>=.30 and
      adequate>=4 and pos>=4 and pos5>=4)
    return {**s,"episode_wr_uplift":up,"episode_wr_uplift_5bps":up5,"adequate_blocks":adequate,"positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}

def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15);tdev=guarded(m,pdev);d=dev_stats(pdev,tdev)
    pd.DataFrame([d]).to_csv(OUT_DEV,index=False)
    oosrows=[];frames=[]
    if d["eligible"]:
        q=tdev.copy();q["scope"]="DEVELOPMENT_FROZEN";frames.append(q)
        for role,ref,hour in CELLS:
            for part in ("external","reference_validation"):
                p=a26.parent_cell(m,part,role,ref,hour);t=guarded(m,p);s=a27.stats(p,t)
                oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,**s})
                if len(t):z=t.copy();z["scope"]="OOS";frames.append(z)
    oos=pd.DataFrame(oosrows);oos.to_csv(OUT_OOS,index=False)
    if not d["eligible"]:status="SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_REJECTED_DEVELOPMENT"
    else:
        central=oos[oos.role=="CENTRAL"];support=oos[(oos.role!="CENTRAL")&(oos.partition.isin(["external","reference_validation"]))]
        central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and
          (central.overlay_net>central.parent_net).all() and (central.overlay_net_5bps>central.parent_net_5bps).all() and
          (central.overlay_pf>central.parent_pf).all() and (central.overlay_pf_5bps>central.parent_pf_5bps).all() and
          (central.episode_wr>=central.parent_wr).all() and (central.episode_wr_5bps>=central.parent_wr_5bps).all())
        sr=int((support.recovery_net>0).sum());ss=int((support.recovery_net_5bps>0).sum());so=int((support.overlay_net>support.parent_net).sum());so5=int((support.overlay_net_5bps>support.parent_net_5bps).sum())
        status="SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_SUPPORTED" if central_ok and len(support)==4 and sr>=3 and ss>=3 and so>=3 and so5>=3 else "SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_REJECTED_OOS"
    (pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()).to_csv(OUT_TRADES,index=False)
    r=d;lines=["# SOL LONG 15:00 UTC RC30_C2 Parent-MAE Transfer — A39 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "Exact A27 RC30_C2 recovery with one frozen A37B/A38 upstream gate: parent_mae_R <= 0.145R.","","## Development","",
      "| N | Attempt/loss | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay | +blocks raw/stress | Pass |","|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|",
      f"| {int(r['recovery_n'])} | {pct(r['attempt_rate'])} | {pct(r['recovery_wr'])} | {fmt(r['recovery_pf'])} | ${fmt(r['recovery_net'])} | {fmt(r['recovery_pf_5bps'])} | ${fmt(r['recovery_net_5bps'])} | {pct(r['rescue_rate'])} | {pct(r['parent_wr'])}→{pct(r['episode_wr'])} | {fmt(r['parent_pf'])}→{fmt(r['overlay_pf'])} | {fmt(r['parent_pf_5bps'])}→{fmt(r['overlay_pf_5bps'])} | {int(r['positive_blocks_raw'])}/{int(r['positive_blocks_5bps'])} | {'YES' if r['eligible'] else 'NO'} |",""]
    if len(oos):
        lines += ["## Frozen OOS","","| Role | Partition | N | Rec WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
        for _,z in oos.iterrows():lines.append(f"| {z.role} | {z.partition} | {int(z.recovery_n)} | {pct(z.recovery_wr)} | {fmt(z.recovery_pf)} | ${fmt(z.recovery_net)} | {fmt(z.recovery_pf_5bps)} | ${fmt(z.recovery_net_5bps)} | {pct(z.parent_wr)}→{pct(z.episode_wr)} | {fmt(z.parent_pf)}→{fmt(z.overlay_pf)} | {fmt(z.parent_pf_5bps)}→{fmt(z.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","No neighboring MAE threshold or reclaim-window scan is authorized after A39.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)
if __name__=="__main__":main()
