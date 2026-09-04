#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A28_PATH=Path(__file__).resolve().parent/"sol_long_15utc_rc30c2_rescue_anatomy_a28.py"
spec=importlib.util.spec_from_file_location("a28",A28_PATH)
a28=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a28)
a27=a28.a27; a26=a28.a26; a2=a28.a2

OUT_MD=ROOT/"SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_Result.md"
OUT_DEV=ROOT/"SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_DEVELOPMENT.csv"
OUT_OOS=ROOT/"SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_OOS.csv"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_TRADES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_Status.txt"

LANES=("Q_CLOSE08","Q_BODY04","Q_CLOSE08_BODY04")
CELLS=a27.CELLS

def fmt(v,d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def pass_guard(f,lane):
    c=float(f["signal_close_R"])>=.08
    b=float(f["signal_body_R"])>=.04
    if lane=="Q_CLOSE08": return c
    if lane=="Q_BODY04": return b
    return c and b

def guarded_lane(m,parent,lane):
    raw=a27.simulate_lane(m,parent,"RC30_C2")
    if raw.empty:return raw
    pm={pd.Timestamp(r.entry_ts):r for _,r in parent.iterrows()}
    keep=[]
    for i,z in raw.iterrows():
        p=pm.get(pd.Timestamp(z.parent_entry_ts))
        if p is None: continue
        f=a28.feature_row(m,p,z)
        if f is not None and pass_guard(f,lane): keep.append(i)
    q=raw.loc[keep].copy() if keep else raw.iloc[0:0].copy()
    if len(q): q["guard_lane"]=lane
    return q

def dev_row(parent,t,lane):
    s=a27.stats(parent,t); adequate=pos=pos5=0; blocks={}
    for bi in range(6):
        z=t[pd.to_numeric(t.dev_block,errors="coerce")==bi] if len(t) else t
        n=len(z); net=float(pd.to_numeric(z.recovery_pnl,errors="coerce").sum()) if n else 0.; net5=float(pd.to_numeric(z.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.
        blocks[f"b{bi+1}_n"]=n; blocks[f"b{bi+1}_net"]=net; blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=5:
            adequate+=1; pos+=int(net>0); pos5+=int(net5>0)
    eligible=bool(s["recovery_n"]>=40 and s["recovery_pf"]>1.20 and s["recovery_pf_5bps"]>1.05 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and s["overlay_net"]>s["parent_net"] and s["overlay_net_5bps"]>s["parent_net_5bps"] and s["episode_wr"]>s["parent_wr"] and s["rescue_rate"]>=.30 and adequate>=4 and pos>=4 and pos5>=4)
    return {"lane":lane,**s,"adequate_blocks":adequate,"positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}

def choose(dev):
    q=dev[dev.eligible.astype(bool)].copy()
    if q.empty:return None
    q["episode_wr_uplift"]=q.episode_wr-q.parent_wr
    return q.sort_values(["overlay_net_improvement_5bps","overlay_pf_5bps","episode_wr_uplift","recovery_n"],ascending=[False,False,False,False]).iloc[0]

def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15)
    rows=[]; frames={}
    for lane in LANES:
        t=guarded_lane(m,pdev,lane); frames[lane]=t; rows.append(dev_row(pdev,t,lane))
    dev=pd.DataFrame(rows); dev.to_csv(OUT_DEV,index=False); winner=choose(dev)
    oosrows=[]; alltr=[]
    if winner is not None:
        lane=str(winner.lane); z=frames[lane].copy(); z["scope"]="DEVELOPMENT_FROZEN"; alltr.append(z)
        for role,ref,hour in CELLS:
            for part in ("external","reference_validation"):
                p=a26.parent_cell(m,part,role,ref,hour); t=guarded_lane(m,p,lane); s=a27.stats(p,t)
                oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,"lane":lane,**s})
                if len(t): t=t.copy(); t["scope"]="OOS"; alltr.append(t)
    oos=pd.DataFrame(oosrows); oos.to_csv(OUT_OOS,index=False)
    if winner is None: status="SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_REJECTED_DEVELOPMENT"
    else:
        central=oos[oos.role=="CENTRAL"]; support=oos[oos.role!="CENTRAL"]
        central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and (central.overlay_pf>central.parent_pf).all() and (central.overlay_pf_5bps>central.parent_pf_5bps).all() and (central.overlay_net>central.parent_net).all() and (central.overlay_net_5bps>central.parent_net_5bps).all() and (central.episode_wr>central.parent_wr).all())
        sr=int((support.recovery_net>0).sum()); ss=int((support.recovery_net_5bps>0).sum()); so=int((support.overlay_net>support.parent_net).sum()); so5=int((support.overlay_net_5bps>support.parent_net_5bps).sum())
        supported=central_ok and sr>=3 and ss>=3 and so>=3 and so5>=3
        status="SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_SUPPORTED" if supported else "SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_REJECTED_OOS"
    (pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()).to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG 15:00 UTC RC30_C2 Quality Guard — A29 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A29 applies only A28-derived fixed quality guards to the exact RC30_C2 trigger.","","## Development","",
      "| Lane | N | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay PF | 5bps PF→Overlay | +blocks raw/stress | Pass |","|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|"]
    for _,r in dev.iterrows():
        lines.append(f"| {r.lane} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.rescue_rate)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["",f"Frozen Development winner: **{str(winner.lane) if winner is not None else 'NONE'}**.",""]
    if len(oos):
      lines += ["## Frozen OOS","","| Role | Partition | N | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | 5bps PF→Overlay |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
      for _,r in oos.iterrows(): lines.append(f"| {r.role} | {r.partition} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","No neighboring threshold scan is allowed after A29. If rejected, return to loss anatomy or leave 15UTC parent-only.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)
if __name__=="__main__":main()
