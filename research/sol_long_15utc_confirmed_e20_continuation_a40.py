#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A36_PATH=Path(__file__).resolve().parent/"sol_long_15utc_confirmed_e10_floor_a36.py"
spec=importlib.util.spec_from_file_location("a36",A36_PATH)
a36=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a36)
a34=a36.a34; a26=a36.a26; a2=a36.a2; CELLS=a36.CELLS
OUT_MD=ROOT/"SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_Result.md"
OUT_DEV=ROOT/"SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_DEVELOPMENT.csv"
OUT_OOS=ROOT/"SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_OOS.csv"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_TRADES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_Status.txt"


def fmt(v,d=2):
    if pd.isna(v):return "-"
    if np.isinf(v):return "inf"
    return f"{float(v):.{d}f}"
def pct(v):return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def simulate_one(m,r):
    z=a34.rc30c2_signal(m,r)
    if z is None:return None
    signal,endpos=z
    ci=a34.confirmation_index(m,r,"DC10_C12",signal,endpos)
    if ci<0:return None
    idx=m["idx"];op=m["open"];hi=m["high"];cl=m["close"]
    H=float(r.H);L=float(r.L);R=float(r.R);e10=H+.10*R;e20=H+.20*R;e40=H+.40*R
    entry_i=-1;cancel_i=-1
    for i in range(ci+1,endpos):
        # E20 touch is intrabar and therefore precedes the completed close of the same bar.
        if float(hi[i])>=e20:
            entry_i=i;break
        if float(cl[i])<=e10:
            cancel_i=i;break
    if entry_i<0:return None
    entry=e20;exit_i=endpos-1;exit_price=float(cl[exit_i]);reason="TIME";floor_i=-1
    # Entry bar: target not credited. A completed E10 failure close on the entry bar is causal and exits next open.
    if float(cl[entry_i])<=e10:
        floor_i=entry_i;ni=entry_i+1
        if ni<endpos:exit_i=ni;exit_price=float(op[ni]);reason="E10_FLOOR_ENTRY_BAR"
        else:exit_i=entry_i;exit_price=float(cl[entry_i]);reason="TIME_AFTER_E10_FLOOR"
    else:
        for i in range(entry_i+1,endpos):
            if float(hi[i])>=e40:
                exit_i=i;exit_price=e40;reason="TARGET";break
            if float(cl[i])<=e10:
                floor_i=i;ni=i+1
                if ni<endpos:exit_i=ni;exit_price=float(op[ni]);reason="E10_FLOOR"
                else:exit_i=i;exit_price=float(cl[i]);reason="TIME_AFTER_E10_FLOOR"
                break
    ret=exit_price/entry-1.;pnl=ret*a2.NOTIONAL;pnl5=(ret-a2.STRESS)*a2.NOTIONAL
    comb=float(r.pnl)+pnl;comb5=float(r.pnl_5bps)+pnl5
    return {"role":r.role,"partition":r.partition,"dev_block":r.dev_block,"execution_start":r.execution_start,
      "H":H,"L":L,"R":R,"parent_entry_ts":r.entry_ts,"parent_exit_ts":r.exit_ts,"parent_pnl":float(r.pnl),"parent_pnl_5bps":float(r.pnl_5bps),
      "signal_ts":idx[signal],"confirm_ts":idx[ci],"reentry_ts":idx[entry_i],"reentry_price":entry,"reentry_R":.20,
      "exit_ts":idx[exit_i],"exit_price":exit_price,"exit_reason":reason,"floor_close_ts":idx[floor_i] if floor_i>=0 else pd.NaT,
      "recovery_pnl":pnl,"recovery_pnl_5bps":pnl5,"combined_episode_pnl":comb,"combined_episode_pnl_5bps":comb5,"rescued":comb>0,"rescued_5bps":comb5>0}

def simulate(m,parent):
    rows=[]
    for _,r in parent[parent.pnl<=0].iterrows():
        z=simulate_one(m,r)
        if z is not None:rows.append(z)
    return pd.DataFrame(rows)

def dev_stats(parent,t):
    s=a36.stats(parent,t);adequate=pos=pos5=0;blocks={}
    for bi in range(6):
        q=t[pd.to_numeric(t.dev_block,errors="coerce")==bi] if len(t) else t;n=len(q)
        net=float(pd.to_numeric(q.recovery_pnl,errors="coerce").sum()) if n else 0.;net5=float(pd.to_numeric(q.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.
        blocks[f"b{bi+1}_n"]=n;blocks[f"b{bi+1}_net"]=net;blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=2:
            adequate+=1;pos+=int(net>0);pos5+=int(net5>0)
    up=s["episode_wr"]-s["parent_wr"];up5=s["episode_wr_5bps"]-s["parent_wr_5bps"]
    eligible=bool(s["recovery_n"]>=15 and s["recovery_pf"]>1.30 and s["recovery_pf_5bps"]>1.10 and
      s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and
      s["overlay_net"]>s["parent_net"] and s["overlay_net_5bps"]>s["parent_net_5bps"] and
      s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and
      up>=.02 and up5>=.01 and s["rescue_rate"]>=.40 and adequate>=4 and pos>=4 and pos5>=4)
    return {**s,"episode_wr_uplift":up,"episode_wr_uplift_5bps":up5,"adequate_blocks":adequate,"positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}

def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15);tdev=simulate(m,pdev);d=dev_stats(pdev,tdev)
    pd.DataFrame([d]).to_csv(OUT_DEV,index=False);oosrows=[];frames=[]
    if d["eligible"]:
        q=tdev.copy();q["scope"]="DEVELOPMENT_FROZEN";frames.append(q)
        for role,ref,hour in CELLS:
            for part in ("external","reference_validation"):
                p=a26.parent_cell(m,part,role,ref,hour);t=simulate(m,p);s=a36.stats(p,t);oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,**s})
                if len(t):z=t.copy();z["scope"]="OOS";frames.append(z)
    oos=pd.DataFrame(oosrows);oos.to_csv(OUT_OOS,index=False)
    if not d["eligible"]:status="SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_REJECTED_DEVELOPMENT"
    else:
        central=oos[oos.role=="CENTRAL"];support=oos[(oos.role!="CENTRAL")&(oos.partition.isin(["external","reference_validation"]))]
        central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and
          (central.overlay_net>central.parent_net).all() and (central.overlay_net_5bps>central.parent_net_5bps).all() and
          (central.overlay_pf>central.parent_pf).all() and (central.overlay_pf_5bps>central.parent_pf_5bps).all() and
          (central.episode_wr>=central.parent_wr).all() and (central.episode_wr_5bps>=central.parent_wr_5bps).all())
        sr=int((support.recovery_net>0).sum());ss=int((support.recovery_net_5bps>0).sum());so=int((support.overlay_net>support.parent_net).sum());so5=int((support.overlay_net_5bps>support.parent_net_5bps).sum())
        status="SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_SUPPORTED" if central_ok and len(support)==4 and sr>=3 and ss>=3 and so>=3 and so5>=3 else "SOL_LONG_15UTC_CONFIRMED_E20_CONTINUATION_A40_REJECTED_OOS"
    (pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()).to_csv(OUT_TRADES,index=False)
    r=d;lines=["# SOL LONG 15:00 UTC Confirmed E20 Continuation Recovery — A40 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "Exact RC30_C2 -> DC10_C12 confirmation; no immediate entry. E10 close cancels before entry; E20 touch enters; E40 target; post-entry E10 close exits next open.","","## Development","",
      "| N | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | Stress WR→Episode WR | PF→Overlay | Stress PF→Overlay | +blocks raw/stress | Pass |","|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|",
      f"| {int(r['recovery_n'])} | {pct(r['recovery_wr'])} | {fmt(r['recovery_pf'])} | ${fmt(r['recovery_net'])} | {fmt(r['recovery_pf_5bps'])} | ${fmt(r['recovery_net_5bps'])} | {pct(r['rescue_rate'])} | {pct(r['parent_wr'])}→{pct(r['episode_wr'])} | {pct(r['parent_wr_5bps'])}→{pct(r['episode_wr_5bps'])} | {fmt(r['parent_pf'])}→{fmt(r['overlay_pf'])} | {fmt(r['parent_pf_5bps'])}→{fmt(r['overlay_pf_5bps'])} | {int(r['positive_blocks_raw'])}/{int(r['positive_blocks_5bps'])} | {'YES' if r['eligible'] else 'NO'} |",""]
    if len(oos):
        lines += ["## Frozen OOS","","| Role | Partition | N | Rec WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
        for _,z in oos.iterrows():lines.append(f"| {z.role} | {z.partition} | {int(z.recovery_n)} | {pct(z.recovery_wr)} | {fmt(z.recovery_pf)} | ${fmt(z.recovery_net)} | {fmt(z.recovery_pf_5bps)} | ${fmt(z.recovery_net_5bps)} | {pct(z.parent_wr)}→{pct(z.episode_wr)} | {fmt(z.parent_pf)}→{fmt(z.overlay_pf)} | {fmt(z.parent_pf_5bps)}→{fmt(z.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","No E15/E25 trigger scan, alternate floor, or OOS retuning is authorized after A40.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)
if __name__=="__main__":main()
