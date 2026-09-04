#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A26_PATH=Path(__file__).resolve().parent / "sol_long_15utc_loss_conversion_a26.py"
spec=importlib.util.spec_from_file_location("a26",A26_PATH)
a26=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a26)
a17=a26.a17; a4=a26.a4; a2=a26.a2

OUT_MD=ROOT/"SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_Result.md"
OUT_DEV=ROOT/"SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_DEVELOPMENT.csv"
OUT_OOS=ROOT/"SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_OOS.csv"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_TRADES.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_Status.txt"

LANES={"RC30_FIRST":(30,1),"RC30_C2":(30,2),"RC60_C5":(60,5)}
CELLS=[("CENTRAL",360,15),("CLOCK_SUPPORT",360,16),("REF_SUPPORT",300,15)]
TARGET_R=.40; STRESS=a2.STRESS

def pf(v):
    x=pd.to_numeric(v,errors="coerce").dropna(); gp=float(x[x>0].sum()); gl=float(-x[x<=0].sum())
    if gl==0: return np.inf if gp>0 else np.nan
    return gp/gl
def fmt(v,d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def simulate_one(m,r,lane):
    horizon,need=LANES[lane]; w=a4.recovery_window(m,r)
    if w is None: return None
    _,xi,endpos,_=w; idx=m["idx"]; op=m["open"]; hi=m["high"]; cl=m["close"]
    H=float(r.H); L=float(r.L); R=float(r.R); target=H+TARGET_R*R
    search_end=min(xi+horizon//5,endpos); count=0; signal=-1
    for i in range(xi,search_end):
        if float(hi[i])>=target: return None
        if float(cl[i])>H:
            count+=1
            if count>=need:
                signal=i; break
    if signal<0: return None
    entry_i=signal+1
    if entry_i>=endpos: return None
    entry=float(op[entry_i])
    if entry>=target: return None
    exit_i=endpos-1; exit_price=float(cl[exit_i]); reason="TIME"; invalid=-1
    for i in range(entry_i+1,endpos):
        if float(hi[i])>=target:
            exit_i=i; exit_price=target; reason="TARGET"; break
        if float(cl[i])<=H:
            invalid=i; ni=i+1
            if ni<endpos:
                exit_i=ni; exit_price=float(op[ni]); reason="FAILED_RECLAIM"
            else:
                exit_i=i; exit_price=float(cl[i]); reason="TIME_AFTER_FINAL_FAILED_RECLAIM"
            break
    ret=exit_price/entry-1.0; pnl=ret*a2.NOTIONAL; pnl5=(ret-STRESS)*a2.NOTIONAL
    comb=float(r.pnl)+pnl; comb5=float(r.pnl_5bps)+pnl5
    return {"role":r.role,"partition":r.partition,"dev_block":r.dev_block,"execution_start":r.execution_start,
            "lane":lane,"horizon_min":horizon,"required_closes_above_H":need,"H":H,"L":L,"R":R,
            "parent_entry_ts":r.entry_ts,"parent_exit_ts":r.exit_ts,"parent_pnl":float(r.pnl),"parent_pnl_5bps":float(r.pnl_5bps),
            "signal_ts":idx[signal],"signal_delay_min":float((signal-xi+1)*5),"signal_close":float(cl[signal]),
            "reentry_ts":idx[entry_i],"reentry_price":entry,"exit_ts":idx[exit_i],"exit_price":exit_price,"exit_reason":reason,
            "invalidation_close_ts":idx[invalid] if invalid>=0 else pd.NaT,"recovery_pnl":pnl,"recovery_pnl_5bps":pnl5,
            "combined_episode_pnl":comb,"combined_episode_pnl_5bps":comb5,"rescued":comb>0,"rescued_5bps":comb5>0}

def simulate_lane(m,parent,lane):
    rows=[]
    for _,r in parent[parent.pnl<=0].iterrows():
        z=simulate_one(m,r,lane)
        if z is not None: rows.append(z)
    return pd.DataFrame(rows)

def stats(parent,t):
    bp=pd.to_numeric(parent.pnl,errors="coerce"); bp5=pd.to_numeric(parent.pnl_5bps,errors="coerce")
    r=pd.to_numeric(t.recovery_pnl,errors="coerce") if len(t) else pd.Series(dtype=float)
    r5=pd.to_numeric(t.recovery_pnl_5bps,errors="coerce") if len(t) else pd.Series(dtype=float)
    overlay=pd.concat([bp,r],ignore_index=True); overlay5=pd.concat([bp5,r5],ignore_index=True)
    rmap={pd.Timestamp(x.parent_entry_ts):x for _,x in t.iterrows()} if len(t) else {}
    eps=[]; eps5=[]
    for _,p in parent.iterrows():
        rr=rmap.get(pd.Timestamp(p.entry_ts)); eps.append(float(p.pnl)+(float(rr.recovery_pnl) if rr is not None else 0.0)); eps5.append(float(p.pnl_5bps)+(float(rr.recovery_pnl_5bps) if rr is not None else 0.0))
    ep=pd.Series(eps,dtype=float); ep5=pd.Series(eps5,dtype=float)
    loss_n=int((bp<=0).sum())
    return {
      "parent_n":len(parent),"parent_wr":float((bp>0).mean()),"parent_pf":pf(bp),"parent_net":float(bp.sum()),
      "parent_wr_5bps":float((bp5>0).mean()),"parent_pf_5bps":pf(bp5),"parent_net_5bps":float(bp5.sum()),
      "recovery_n":len(t),"recovery_wr":float((r>0).mean()) if len(r) else np.nan,"recovery_pf":pf(r),"recovery_exp":float(r.mean()) if len(r) else np.nan,"recovery_net":float(r.sum()),
      "recovery_wr_5bps":float((r5>0).mean()) if len(r5) else np.nan,"recovery_pf_5bps":pf(r5),"recovery_exp_5bps":float(r5.mean()) if len(r5) else np.nan,"recovery_net_5bps":float(r5.sum()),
      "attempt_rate":len(t)/loss_n if loss_n else np.nan,"rescue_rate":float(t.rescued.mean()) if len(t) else np.nan,"rescue_rate_5bps":float(t.rescued_5bps.mean()) if len(t) else np.nan,
      "episode_wr":float((ep>0).mean()),"episode_wr_5bps":float((ep5>0).mean()),"episode_net":float(ep.sum()),"episode_net_5bps":float(ep5.sum()),
      "overlay_pf":pf(overlay),"overlay_net":float(overlay.sum()),"overlay_pf_5bps":pf(overlay5),"overlay_net_5bps":float(overlay5.sum()),
      "overlay_net_improvement":float(r.sum()),"overlay_net_improvement_5bps":float(r5.sum()),
      "median_signal_delay_min":float(t.signal_delay_min.median()) if len(t) else np.nan}

def dev_row(parent,t,lane):
    s=stats(parent,t); adequate=pos=pos5=0; blocks={}
    for bi in range(6):
        z=t[pd.to_numeric(t.dev_block,errors="coerce")==bi] if len(t) else t
        n=len(z); net=float(pd.to_numeric(z.recovery_pnl,errors="coerce").sum()) if n else 0.; net5=float(pd.to_numeric(z.recovery_pnl_5bps,errors="coerce").sum()) if n else 0.
        blocks[f"b{bi+1}_n"]=n; blocks[f"b{bi+1}_net"]=net; blocks[f"b{bi+1}_net_5bps"]=net5
        if n>=5:
            adequate+=1; pos+=int(net>0); pos5+=int(net5>0)
    eligible=bool(s["recovery_n"]>=60 and s["recovery_pf"]>1.15 and s["recovery_pf_5bps"]>1.0 and s["recovery_exp"]>0 and s["recovery_exp_5bps"]>0 and s["recovery_net"]>0 and s["recovery_net_5bps"]>0 and s["overlay_pf"]>s["parent_pf"] and s["overlay_pf_5bps"]>s["parent_pf_5bps"] and s["episode_wr"]>=s["parent_wr"] and s["rescue_rate"]>=.20 and adequate>=4 and pos>=4 and pos5>=4)
    return {"lane":lane,**s,"adequate_blocks":adequate,"positive_blocks_raw":pos,"positive_blocks_5bps":pos5,"eligible":eligible,**blocks}

def choose(dev):
    q=dev[dev.eligible.astype(bool)].copy()
    if q.empty:return None
    q["episode_wr_uplift"]=q.episode_wr-q.parent_wr
    return q.sort_values(["overlay_net_improvement_5bps","overlay_pf_5bps","episode_wr_uplift","median_signal_delay_min"],ascending=[False,False,False,True]).iloc[0]

def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    pdev=a26.parent_cell(m,"development","CENTRAL",360,15)
    devrows=[]; frames={}
    for lane in LANES:
        t=simulate_lane(m,pdev,lane); frames[lane]=t; devrows.append(dev_row(pdev,t,lane))
    dev=pd.DataFrame(devrows); winner=choose(dev); dev.to_csv(OUT_DEV,index=False)
    oosrows=[]; alltr=[]
    if winner is not None:
      lane=str(winner.lane); z=frames[lane].copy(); z["scope"]="DEVELOPMENT_FROZEN"; alltr.append(z)
      for role,ref,hour in CELLS:
        for part in ("external","reference_validation"):
          p=a26.parent_cell(m,part,role,ref,hour); t=simulate_lane(m,p,lane); s=stats(p,t)
          oosrows.append({"role":role,"partition":part,"ref_min":ref,"hour":hour,"lane":lane,**s})
          if len(t): t=t.copy(); t["scope"]="OOS"; alltr.append(t)
    oos=pd.DataFrame(oosrows); oos.to_csv(OUT_OOS,index=False)
    if winner is None: status="SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_REJECTED_DEVELOPMENT"
    else:
      central=oos[oos.role=="CENTRAL"]; support=oos[oos.role!="CENTRAL"]
      central_ok=bool(len(central)==2 and (central.recovery_net>0).all() and (central.recovery_net_5bps>0).all() and (central.overlay_pf>central.parent_pf).all() and (central.overlay_pf_5bps>central.parent_pf_5bps).all() and (central.overlay_net>central.parent_net).all() and (central.overlay_net_5bps>central.parent_net_5bps).all() and (central.episode_wr>=central.parent_wr).all())
      sr=int((support.recovery_net>0).sum()); ss=int((support.recovery_net_5bps>0).sum()); so=int((support.overlay_net>support.parent_net).sum()); so5=int((support.overlay_net_5bps>support.parent_net_5bps).sum())
      supported=central_ok and sr>=3 and ss>=3 and so>=3 and so5>=3
      status="SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_SUPPORTED" if supported else "SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_REJECTED_OOS"
    if alltr: pd.concat(alltr,ignore_index=True).to_csv(OUT_TRADES,index=False)
    else: pd.DataFrame().to_csv(OUT_TRADES,index=False)
    lines=["# SOL LONG 15:00 UTC Reclaim Conversion — A27 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A27 tests only the three A26-derived reclaim/persistence states. A23 resting recovery remains absent.","","## Development","",
      "| Lane | N | Attempt/loss | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | Parent PF→Overlay PF | 5bps Parent PF→Overlay PF | +blocks raw/stress | Pass |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|"]
    for _,r in dev.iterrows():
      lines.append(f"| {r.lane} | {int(r.recovery_n)} | {pct(r.attempt_rate)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.rescue_rate)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["",f"Frozen Development winner: **{str(winner.lane) if winner is not None else 'NONE'}**.",""]
    if len(oos):
      lines += ["## Frozen OOS","","| Role | Partition | N | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Parent WR→Episode WR | Parent PF→Overlay PF | 5bps PF overlay |","|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|"]
      for _,r in oos.iterrows(): lines.append(f"| {r.role} | {r.partition} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.overlay_pf_5bps)} |")
    lines += ["","## Decision","",f"**Status: {status}**","","A27 is a bounded loss-conversion overlay. If rejected, no neighboring threshold/window scan is authorized; return to anatomy.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)
if __name__=="__main__":main()
