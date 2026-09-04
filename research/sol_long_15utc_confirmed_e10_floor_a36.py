#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A34_PATH = Path(__file__).resolve().parent / "sol_long_15utc_rc30c2_delayed_confirm_a34.py"
spec = importlib.util.spec_from_file_location("a34", A34_PATH)
a34 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a34)
a26 = a34.a26; a2 = a34.a2

OUT_MD = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_Result.md"
OUT_DEV = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_Status.txt"
CELLS = a34.CELLS
TARGET_R = 0.40
STRESS = a2.STRESS


def pf(v):
    x = pd.to_numeric(v, errors="coerce").dropna(); gp = float(x[x>0].sum()); gl = float(-x[x<=0].sum())
    if gl == 0: return np.inf if gp > 0 else np.nan
    return gp / gl


def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def fmt(v,d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def simulate_one(m, r):
    z = a34.rc30c2_signal(m, r)
    if z is None: return None
    signal, endpos = z
    ci = a34.confirmation_index(m, r, "DC10_C12", signal, endpos)
    if ci < 0: return None
    idx=m["idx"]; op=m["open"]; hi=m["high"]; cl=m["close"]
    H=float(r.H); L=float(r.L); R=float(r.R); target=H+TARGET_R*R; floor=H+0.10*R
    entry_i=ci+1
    if entry_i>=endpos: return None
    entry=float(op[entry_i])
    if entry>=target: return None

    exit_i=endpos-1; exit_price=float(cl[exit_i]); reason="TIME"; floor_i=-1
    # Match prior recovery convention: no target/floor credit on the entry bar.
    for i in range(entry_i+1,endpos):
        if float(hi[i])>=target:
            exit_i=i; exit_price=target; reason="TARGET"; break
        if float(cl[i])<=floor:
            floor_i=i; ni=i+1
            if ni<endpos:
                exit_i=ni; exit_price=float(op[ni]); reason="E10_FLOOR"
            else:
                exit_i=i; exit_price=float(cl[i]); reason="TIME_AFTER_E10_FLOOR"
            break
    ret=exit_price/entry-1.0; pnl=ret*a2.NOTIONAL; pnl5=(ret-STRESS)*a2.NOTIONAL
    comb=float(r.pnl)+pnl; comb5=float(r.pnl_5bps)+pnl5
    return {
      "role":r.role,"partition":r.partition,"dev_block":r.dev_block,"execution_start":r.execution_start,
      "H":H,"L":L,"R":R,"parent_entry_ts":r.entry_ts,"parent_exit_ts":r.exit_ts,
      "parent_pnl":float(r.pnl),"parent_pnl_5bps":float(r.pnl_5bps),
      "signal_ts":idx[signal],"confirm_ts":idx[ci],"reentry_ts":idx[entry_i],"reentry_price":entry,"reentry_R":(entry-H)/R,
      "exit_ts":idx[exit_i],"exit_price":exit_price,"exit_reason":reason,"floor_close_ts":idx[floor_i] if floor_i>=0 else pd.NaT,
      "recovery_pnl":pnl,"recovery_pnl_5bps":pnl5,"combined_episode_pnl":comb,"combined_episode_pnl_5bps":comb5,
      "rescued":comb>0,"rescued_5bps":comb5>0,
    }


def simulate(m,parent):
    rows=[]
    for _,r in parent[parent.pnl<=0].iterrows():
        z=simulate_one(m,r)
        if z is not None: rows.append(z)
    return pd.DataFrame(rows)


def stats(parent,t):
    bp=pd.to_numeric(parent.pnl,errors="coerce");bp5=pd.to_numeric(parent.pnl_5bps,errors="coerce")
    rp=pd.to_numeric(t.recovery_pnl,errors="coerce") if len(t) else pd.Series(dtype=float)
    rp5=pd.to_numeric(t.recovery_pnl_5bps,errors="coerce") if len(t) else pd.Series(dtype=float)
    over=pd.concat([bp,rp],ignore_index=True);over5=pd.concat([bp5,rp5],ignore_index=True)
    rmap={pd.Timestamp(x.parent_entry_ts):x for _,x in t.iterrows()} if len(t) else {}
    ep=[];ep5=[]
    for _,p in parent.iterrows():
        rr=rmap.get(pd.Timestamp(p.entry_ts));ep.append(float(p.pnl)+(float(rr.recovery_pnl) if rr is not None else 0.0));ep5.append(float(p.pnl_5bps)+(float(rr.recovery_pnl_5bps) if rr is not None else 0.0))
    ep=pd.Series(ep,dtype=float);ep5=pd.Series(ep5,dtype=float);loss_n=int((bp<=0).sum())
    return {
      "parent_n":len(parent),"parent_wr":float((bp>0).mean()),"parent_pf":pf(bp),"parent_net":float(bp.sum()),
      "parent_wr_5bps":float((bp5>0).mean()),"parent_pf_5bps":pf(bp5),"parent_net_5bps":float(bp5.sum()),
      "recovery_n":len(t),"attempt_rate":len(t)/loss_n if loss_n else np.nan,"floor_exit_rate":float((t.exit_reason=="E10_FLOOR").mean()) if len(t) else np.nan,
      "recovery_wr":float((rp>0).mean()) if len(rp) else np.nan,"recovery_pf":pf(rp),"recovery_exp":float(rp.mean()) if len(rp) else np.nan,"recovery_net":float(rp.sum()),
      "recovery_wr_5bps":float((rp5>0).mean()) if len(rp5) else np.nan,"recovery_pf_5bps":pf(rp5),"recovery_exp_5bps":float(rp5.mean()) if len(rp5) else np.nan,"recovery_net_5bps":float(rp5.sum()),
      "rescue_rate":float(t.rescued.mean()) if len(t) else np.nan,"rescue_rate_5bps":float(t.rescued_5bps.mean()) if len(t) else np.nan,
      "episode_wr":float((ep>0).mean()),"episode_wr_5bps":float((ep5>0).mean()),
      "overlay_pf":pf(over),"overlay_net":float(over.sum()),"overlay_pf_5bps":pf(over5),"overlay_net_5bps":float(over5.sum()),
      "overlay_net_improvement":float(rp.sum()),"overlay_net_improvement_5bps":float(rp5.sum()),
    }


def development(parent,t):
    s=stats(parent,t);adequate=pos=pos5=0;blocks={}
    for bi in range(6):
        q=t[pd.to_numeric(t.dev_block,errors="coerce")==bi] if len(t) else t;n=len(q);net=float(pd.to_numeric(q.recovery_pnl,errors="coerce").sum()) if n else 0.0;net5=float(pd.to_numeric(q.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.0
        blocks[f"b{bi+1}_n"]=n;blocks[f"b{bi+1}_net"]=net;blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=3:
            adequate+=1;pos+=int(net>0);pos5+=int(net5>0)
    up=s["episode_wr"]-s["parent_wr"];up5=s["episode_wr_5bps"]-s["parent_wr_5bps"]
    eligible=bool(s["recovery_n"]>=25 and s["recovery_pf"]>1.25 and s["recovery_pf_5bps"]>1.05 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and s["overlay_net"]>s["parent_net"] and s["overlay_net_5bps"]>s["parent_net_5bps"] and up>=0.02 and up5>=0.01 and s["rescue_rate"]>=0.40 and adequate>=4 and pos>=4 and pos5>=4)
    return {**s,"episode_wr_uplift":up,"episode_wr_uplift_5bps":up5,"adequate_blocks":adequate,"positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}


def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15);tdev=simulate(m,pdev);d=development(pdev,tdev);dev=pd.DataFrame([d]);dev.to_csv(OUT_DEV,index=False)
    winner=bool(d["eligible"]);oosrows=[];frames=[]
    if winner:
        z=tdev.copy();z["scope"]="DEVELOPMENT_FROZEN";frames.append(z)
        for role,ref,hour in CELLS:
            for part in ("external","reference_validation"):
                p=a26.parent_cell(m,part,role,ref,hour);t=simulate(m,p);s=stats(p,t);oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,**s})
                if len(t): t=t.copy();t["scope"]="OOS";frames.append(t)
    oos=pd.DataFrame(oosrows);oos.to_csv(OUT_OOS,index=False)
    if not winner:status="SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_REJECTED_DEVELOPMENT"
    else:
        central=oos[oos.role=="CENTRAL"];support=oos[oos.role!="CENTRAL"]
        central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and (central.overlay_pf>central.parent_pf).all() and (central.overlay_pf_5bps>central.parent_pf_5bps).all() and (central.overlay_net>central.parent_net).all() and (central.overlay_net_5bps>central.parent_net_5bps).all() and ((central.episode_wr-central.parent_wr)>=0).all() and ((central.episode_wr_5bps-central.parent_wr_5bps)>=0).all())
        sr=int((support.recovery_net>0).sum());ss=int((support.recovery_net_5bps>0).sum());so=int((support.overlay_net>support.parent_net).sum());so5=int((support.overlay_net_5bps>support.parent_net_5bps).sum())
        status="SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_SUPPORTED" if central_ok and sr>=3 and ss>=3 and so>=3 and so5>=3 else "SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A36_REJECTED_OOS"
    (pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()).to_csv(OUT_TRADES,index=False)
    r=dev.iloc[0];lines=["# SOL LONG 15:00 UTC Confirmed E10 Recovery Floor — A36 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","", "Single mechanism: exact DC10_C12 delayed-confirmation entry, frozen E40 target, completed close <= E10 exits next open.","","## Development","",
      "| N | Attempt/loss | Floor exit | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue raw/stress | Parent WR→Episode WR | Stress WR→Episode WR | PF→Overlay | Stress PF→Overlay | +blocks raw/stress | Pass |","|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|",
      f"| {int(r.recovery_n)} | {pct(r.attempt_rate)} | {pct(r.floor_exit_rate)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.rescue_rate)}/{pct(r.rescue_rate_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {pct(r.parent_wr_5bps)}→{pct(r.episode_wr_5bps)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |",""]
    if len(oos):
        lines += ["## Frozen OOS","","| Role | Partition | N | Rec WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | 5bps PF→Overlay |","|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
        for _,z in oos.iterrows():lines.append(f"| {z.role} | {z.partition} | {int(z.recovery_n)} | {pct(z.recovery_wr)} | {fmt(z.recovery_pf)} | ${fmt(z.recovery_net)} | {fmt(z.recovery_pf_5bps)} | ${fmt(z.recovery_net_5bps)} | {pct(z.parent_wr)}→{pct(z.episode_wr)} | {fmt(z.parent_pf)}→{fmt(z.overlay_pf)} | {fmt(z.parent_pf_5bps)}→{fmt(z.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","No neighboring floor scan is allowed after A36.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)

if __name__=="__main__":main()
