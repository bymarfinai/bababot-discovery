#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A41_PATH=Path(__file__).resolve().parent/"sol_long_15utc_a40_b2_regime_anatomy_a41.py"
spec=importlib.util.spec_from_file_location("a41",A41_PATH)
a41=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a41)
a40=a41.a40; a36=a40.a36; a26=a40.a26; a2=a40.a2; CELLS=a40.CELLS

OUT_MD=ROOT/"SOL_LONG_15UTC_A40_B2_GUARD_A42_Result.md"
OUT_DEV=ROOT/"SOL_LONG_15UTC_A40_B2_GUARD_A42_DEVELOPMENT.csv"
OUT_OOS=ROOT/"SOL_LONG_15UTC_A40_B2_GUARD_A42_OOS.csv"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_A40_B2_GUARD_A42_TRADES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_A40_B2_GUARD_A42_Status.txt"
LANES=("G_MAE145","G_RET30_220","G_BOTH")

def pf(v):
    x=pd.to_numeric(v,errors="coerce").dropna();gp=float(x[x>0].sum());gl=float(-x[x<=0].sum())
    if gl==0:return np.inf if gp>0 else np.nan
    return gp/gl

def fmt(v,d=2):
    if pd.isna(v):return "-"
    if np.isinf(v):return "inf"
    return f"{float(v):.{d}f}"
def pct(v):return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def enriched_a40(m,parent):
    t=a40.simulate(m,parent)
    if not len(t):return t
    pmap={pd.Timestamp(r.entry_ts):r for _,r in parent.iterrows()};rows=[]
    for _,z in t.iterrows():
        r=pmap.get(pd.Timestamp(z.parent_entry_ts))
        if r is None:continue
        rows.append({**z.to_dict(),**a41.enrich(m,r,z)})
    return pd.DataFrame(rows)

def keep(t,lane):
    if not len(t):return t.copy()
    a=pd.to_numeric(t.parent_mae_R,errors="coerce")<=.145
    b=pd.to_numeric(t.preentry_30m_return_R,errors="coerce")>=.220
    mask=a if lane=="G_MAE145" else (b if lane=="G_RET30_220" else (a&b))
    q=t[mask].copy();q["lane"]=lane;return q

def dev_row(parent,t,lane):
    s=a36.stats(parent,t);adequate=pos=pos5=0;blocks={}
    for bi in range(6):
        q=t[pd.to_numeric(t.dev_block,errors="coerce")==bi];n=len(q)
        net=float(pd.to_numeric(q.recovery_pnl,errors="coerce").sum()) if n else 0.;net5=float(pd.to_numeric(q.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.
        blocks[f"b{bi+1}_n"]=n;blocks[f"b{bi+1}_net"]=net;blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=2:
            adequate+=1;pos+=int(net>0);pos5+=int(net5>0)
    b2n=blocks["b2_n"];b2=blocks["b2_net"];b25=blocks["b2_net_5bps"]
    up=s["episode_wr"]-s["parent_wr"];up5=s["episode_wr_5bps"]-s["parent_wr_5bps"]
    eligible=bool(s["recovery_n"]>=10 and s["recovery_wr"]>=.60 and s["recovery_pf"]>1.50 and s["recovery_pf_5bps"]>1.25 and
      s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and
      up>=.01 and up5>=.01 and s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and
      s["overlay_net"]>s["parent_net"] and s["overlay_net_5bps"]>s["parent_net_5bps"] and
      adequate>=3 and pos==adequate and pos5==adequate and (b2n<2 or (b2>0 and b25>0)))
    return {"lane":lane,**s,"episode_wr_uplift":up,"episode_wr_uplift_5bps":up5,"adequate_blocks":adequate,
            "positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}

def choose(dev):
    q=dev[dev.eligible.astype(bool)].copy()
    if q.empty:return None
    simplicity={"G_MAE145":1,"G_RET30_220":1,"G_BOTH":2};q["complexity"]=q.lane.map(simplicity)
    return q.sort_values(["recovery_net_5bps","recovery_pf_5bps","episode_wr_uplift_5bps","complexity"],ascending=[False,False,False,True]).iloc[0]

def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15);base=enriched_a40(m,pdev)
    rows=[];frames={}
    for lane in LANES:
        t=keep(base,lane);frames[lane]=t;rows.append(dev_row(pdev,t,lane))
    dev=pd.DataFrame(rows);dev.to_csv(OUT_DEV,index=False);winner=choose(dev)
    oosrows=[];alltr=[]
    if winner is not None:
        lane=str(winner.lane);q=frames[lane].copy();q["scope"]="DEVELOPMENT_FROZEN";alltr.append(q)
        for role,ref,hour in CELLS:
            for part in ("external","reference_validation"):
                p=a26.parent_cell(m,part,role,ref,hour);t=keep(enriched_a40(m,p),lane);s=a36.stats(p,t)
                oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,"lane":lane,**s})
                if len(t):z=t.copy();z["scope"]="OOS";alltr.append(z)
    oos=pd.DataFrame(oosrows);oos.to_csv(OUT_OOS,index=False)
    if winner is None:status="SOL_LONG_15UTC_A40_B2_GUARD_A42_REJECTED_DEVELOPMENT"
    else:
        central=oos[oos.role=="CENTRAL"];support=oos[(oos.role!="CENTRAL")&(oos.partition.isin(["external","reference_validation"]))]
        central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and
          (central.recovery_pf>1).all() and (central.recovery_pf_5bps>1).all() and
          (central.overlay_net>=central.parent_net).all() and (central.overlay_net_5bps>=central.parent_net_5bps).all() and
          (central.overlay_pf>=central.parent_pf).all() and (central.overlay_pf_5bps>=central.parent_pf_5bps).all() and
          (central.episode_wr>=central.parent_wr).all() and (central.episode_wr_5bps>=central.parent_wr_5bps).all())
        sr=int((support.recovery_net>0).sum());ss=int((support.recovery_net_5bps>0).sum());so=int((support.overlay_net>=support.parent_net).sum());so5=int((support.overlay_net_5bps>=support.parent_net_5bps).sum())
        status="SOL_LONG_15UTC_A40_B2_GUARD_A42_SUPPORTED" if central_ok and len(support)==4 and sr>=3 and ss>=3 and so>=3 and so5>=3 else "SOL_LONG_15UTC_A40_B2_GUARD_A42_REJECTED_OOS"
    (pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()).to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG 15:00 UTC A40 B2 Regime Guard — A42 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "Exact A40 geometry; only A41 Development-midpoint regime guards are applied.","","## Development","",
      "| Lane | N | WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | Stress WR→Episode WR | PF→Overlay | Stress PF→Overlay | Adequate/+ raw/+ stress | B2 N/net/stress | Pass |","|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|"]
    for _,r in dev.iterrows():
        lines.append(f"| {r.lane} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {pct(r.parent_wr_5bps)}→{pct(r.episode_wr_5bps)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} | {int(r.adequate_blocks)}/{int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {int(r.b2_n)}/${fmt(r.b2_net)}/${fmt(r.b2_net_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["",f"Frozen Development winner: **{str(winner.lane) if winner is not None else 'NONE'}**.",""]
    if len(oos):
        lines += ["## Frozen OOS","","| Role | Partition | N | WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
        for _,r in oos.iterrows():lines.append(f"| {r.role} | {r.partition} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","No neighboring MAE/momentum threshold, E20/E10 change, or OOS retuning is authorized after A42.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)
if __name__=="__main__":main()
