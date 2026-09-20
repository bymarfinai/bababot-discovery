#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S7_LAYER_ATTRIBUTION"
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
REF_START=pd.Timestamp("2025-01-01T00:00:00Z")
START=pd.Timestamp("2022-01-01T00:00:00Z")

MODE_POLICY={
    "IMMEDIATE_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "IMMEDIATE_SWEEP_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_CLEAN_RECLAIM":("TP1","tp1_level","tp1_rr"),
    "DELAYED_SWEEP_RECLAIM":("TP2","tp2_level","tp2_rr"),
}

def zone_paths(m15,fam,end):
    idx=m15.index
    rows=[]
    for r in fam.itertuples(index=False):
        z1=float(r.demand_high+r.demand_width)
        z2=float(r.demand_high+2*r.demand_width)
        start_i=int(idx.searchsorted(r.first_touch_ts,side="right"))
        end_i=int(idx.searchsorted(end,side="right"))
        z1_ts=z2_ts=invalid_ts=pd.NaT
        for i in range(start_i,end_i):
            t=idx[i]; c=float(m15.close.iloc[i])
            if c<float(r.demand_low):
                invalid_ts=t
                break
            if pd.isna(z1_ts) and c>z1: z1_ts=t
            if pd.isna(z2_ts) and c>z2: z2_ts=t
        rows.append({
            "zone_id":r.zone_id,
            "first_touch_ts":r.first_touch_ts,
            "z1_level":z1,
            "z2_level":z2,
            "z1_hit_ts":z1_ts,
            "z2_hit_ts":z2_ts,
            "zone_invalid_close_ts":invalid_ts,
            "zone_1zw_valid":pd.notna(z1_ts),
            "zone_2zw_valid":pd.notna(z2_ts),
        })
    return pd.DataFrame(rows)

def first_5m_touch(raw5,start_ts,end_ts,level,side):
    if pd.isna(start_ts) or pd.isna(end_ts): return pd.NaT
    q=raw5[(raw5.index>start_ts)&(raw5.index<=end_ts)]
    if side=="LOW":
        z=q[q.low<=level]
    else:
        z=q[q.high>=level]
    return z.index[0] if len(z) else pd.NaT

def resolve_policy(raw5,entry_ts,sl,tp,end):
    q=raw5[(raw5.index>entry_ts)&(raw5.index<=end)]
    for t,b in q.iterrows():
        st=float(b.low)<=sl
        tg=float(b.high)>=tp
        if st and tg:return "AMBIGUOUS",t
        if tg:return "WIN",t
        if st:return "LOSS",t
    return "UNRESOLVED",pd.NaT

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def summarize(q):
    resolved=q[q.trade_outcome.isin(["WIN","LOSS"])].copy()
    wins=resolved[resolved.trade_outcome=="WIN"]
    losses=resolved[resolved.trade_outcome=="LOSS"]
    n=len(resolved)
    need=max(0,math.ceil(.70*n)-len(wins))
    valid_losses=losses[losses.zone_1zw_valid].shape[0]
    return {
        "entry_plans":len(q),
        "resolved":n,
        "wins":len(wins),
        "losses":len(losses),
        "wr":len(wins)/n if n else np.nan,
        "zone1_valid_all_entries":float(q.zone_1zw_valid.mean()) if len(q) else np.nan,
        "zone2_valid_all_entries":float(q.zone_2zw_valid.mean()) if len(q) else np.nan,
        "wins_needed_for_70":need,
        "zone_valid_losses":valid_losses,
        "zone_valid_loss_headroom_ge_need":bool(valid_losses>=need) if n else False,
        "zone_fail_losses":int((losses.loss_attribution=="ZONE_NOT_1ZW_VALID").sum()),
        "late_entry_losses":int((losses.loss_attribution=="ENTRY_LATE_AFTER_1ZW_MOVE").sum()),
        "false_stop_losses":int((losses.loss_attribution=="SL_FALSE_STOP_BEFORE_VALID_REBOUND").sum()),
        "tp_path_losses":int((losses.loss_attribution=="TP_OBJECTIVE_NOT_REACHED_AFTER_VALID_REBOUND").sum()),
    }

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")
    end=raw.index.max()

    s1.START=START; s1.END=end; s3.END=end
    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=end]
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=end]
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[(pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
            (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)].copy()

    dev=fam[pd.to_datetime(fam.first_touch_ts,utc=True)<=DEV_END]
    ref=fam[pd.to_datetime(fam.first_touch_ts,utc=True)>=REF_START]
    if len(dev)!=788 or len(ref)!=463:
        raise RuntimeError(f"parent parity drift dev={len(dev)} ref={len(ref)}")

    Z=zone_paths(m15,fam,end)
    P=s3.adaptive_plan(m15,h1,fam)

    devp=P[pd.to_datetime(P.first_touch_ts,utc=True)<=DEV_END]
    dc=devp.execution_status.value_counts().to_dict()
    if len(devp)!=788 or dc.get("ENTRY",0)!=690 or dc.get("CANCELLED_DEMAND_ACCEPTANCE",0)!=98:
        raise RuntimeError(f"S3 parity drift {len(devp)} {dc}")

    E=P[P.execution_status=="ENTRY"].copy()
    E=E.merge(Z,on=["zone_id","first_touch_ts"],how="left",validate="one_to_one")

    rows=[]
    for r in E.itertuples(index=False):
        pol,tcol,rrcol=MODE_POLICY[r.execution_mode]
        tp=float(getattr(r,tcol)) if np.isfinite(getattr(r,tcol)) else np.nan
        rr=float(getattr(r,rrcol)) if np.isfinite(getattr(r,rrcol)) else np.nan

        if np.isfinite(tp) and np.isfinite(rr):
            out,rt=resolve_policy(raw5,r.entry_ts,float(r.sl_reference),tp,end)
        else:
            out,rt="NO_POLICY_TARGET",pd.NaT

        late=bool(
            r.zone_1zw_valid and (
                pd.Timestamp(r.z1_hit_ts)<=pd.Timestamp(r.entry_ts) or
                float(r.entry_price)>=float(r.z1_level)
            )
        )

        sl_before_z1=False
        sl_touch_ts=pd.NaT
        if r.zone_1zw_valid and not late:
            sl_touch_ts=first_5m_touch(raw5,r.entry_ts,r.z1_hit_ts,float(r.sl_reference),"LOW")
            sl_before_z1=pd.notna(sl_touch_ts)

        attrib=""
        if out=="LOSS":
            if not bool(r.zone_1zw_valid):
                attrib="ZONE_NOT_1ZW_VALID"
            elif late:
                attrib="ENTRY_LATE_AFTER_1ZW_MOVE"
            elif sl_before_z1:
                attrib="SL_FALSE_STOP_BEFORE_VALID_REBOUND"
            else:
                attrib="TP_OBJECTIVE_NOT_REACHED_AFTER_VALID_REBOUND"

        rows.append({
            "zone_id":r.zone_id,
            "first_touch_ts":r.first_touch_ts,
            "period":period(r.first_touch_ts),
            "execution_mode":r.execution_mode,
            "entry_ts":r.entry_ts,
            "entry_price":float(r.entry_price),
            "sl_reference":float(r.sl_reference),
            "selected_target":pol,
            "target_level":tp,
            "target_rr":rr,
            "zone_1zw_valid":bool(r.zone_1zw_valid),
            "zone_2zw_valid":bool(r.zone_2zw_valid),
            "z1_level":float(r.z1_level),
            "z1_hit_ts":r.z1_hit_ts,
            "z2_hit_ts":r.z2_hit_ts,
            "zone_invalid_close_ts":r.zone_invalid_close_ts,
            "entry_late_after_z1":late,
            "sl_touch_before_z1_ts":sl_touch_ts,
            "sl_false_stop_before_valid_rebound":sl_before_z1,
            "trade_outcome":out,
            "trade_resolution_ts":rt,
            "loss_attribution":attrib,
        })
    L=pd.DataFrame(rows)

    # Parent-zone validity independent of whether S3 entered.
    family_zone=fam[["zone_id","first_touch_ts"]].merge(Z,on=["zone_id","first_touch_ts"],how="left")
    family_zone["period"]=[period(x) for x in family_zone.first_touch_ts]

    parent=[]
    for per,q in family_zone.groupby("period"):
        parent.append({
            "period":per,"parent_events":len(q),
            "zone1_valid_n":int(q.zone_1zw_valid.sum()),
            "zone1_valid_rate":float(q.zone_1zw_valid.mean()),
            "zone2_valid_n":int(q.zone_2zw_valid.sum()),
            "zone2_valid_rate":float(q.zone_2zw_valid.mean()),
        })
    Parent=pd.DataFrame(parent)

    summ=[]
    for per in ["DEV","REF"]:
        q=L[L.period==per]
        summ.append({"period":per,**summarize(q)})
    All=pd.DataFrame(summ)

    bymode=[]
    for (per,mode),q in L.groupby(["period","execution_mode"]):
        bymode.append({"period":per,"execution_mode":mode,**summarize(q)})
    BM=pd.DataFrame(bymode)

    L.to_csv(ROOT/f"{PFX}_TradeLedger.csv.gz",index=False,compression="gzip")
    Parent.to_csv(ROOT/f"{PFX}_ParentZoneValidity.csv",index=False)
    All.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    BM.to_csv(ROOT/f"{PFX}_ByMode.csv",index=False)

    def pct(x):return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    lines=[
      "# BNB B38-S7 — Detector → Zone → Entry → SL → TP Attribution Audit","",
      "**NO SUB-FILTER. NO TRADE REMOVAL. FROZEN B38-S5 EXECUTION.**","",
      f"Data through **{end}**.","",
      "## 1. Is the demand zone itself producing a meaningful rebound?","",
      "| Period | Parent N | +1ZW before demand acceptance failure | +2ZW |",
      "|---|---:|---:|---:|"
    ]
    for r in Parent.itertuples(index=False):
        lines.append(f"| {r.period} | {r.parent_events} | {r.zone1_valid_n} / {pct(r.zone1_valid_rate)} | {r.zone2_valid_n} / {pct(r.zone2_valid_rate)} |")

    lines += ["","## 2–4. Frozen entry population and loss attribution","",
      "| Period | Entries | Resolved | W-L | WR | Entry-pop zone +1ZW valid | Need loss→win for 70% | Current losses on valid zones | Zone fail | Entry late | False SL | TP/path |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in All.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.entry_plans} | {r.resolved} | {r.wins}-{r.losses} | {pct(r.wr)} | "
            f"{pct(r.zone1_valid_all_entries)} | {r.wins_needed_for_70} | {r.zone_valid_losses} | "
            f"{r.zone_fail_losses} | {r.late_entry_losses} | {r.false_stop_losses} | {r.tp_path_losses} |"
        )

    lines += ["","## Loss attribution meaning",
      "- **Zone fail:** underlying demand never produced +1ZW before 15m close acceptance below demand_low.",
      "- **Entry late:** +1ZW rebound was already achieved before the frozen entry.",
      "- **False SL:** entry was timely and the zone later reached +1ZW, but frozen SL was touched first.",
      "- **TP/path:** entry was timely, SL survived until +1ZW, but the frozen selected structural TP still eventually lost.",
      "",
      "## By execution mode","",
      "| Period | Mode | N | WR | Zone +1ZW valid | Need for 70 | Valid-zone losses | Zone fail | Late | False SL | TP/path |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in BM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.execution_mode} | {r.resolved} | {pct(r.wr)} | {pct(r.zone1_valid_all_entries)} | "
            f"{r.wins_needed_for_70} | {r.zone_valid_losses} | {r.zone_fail_losses} | {r.late_entry_losses} | "
            f"{r.false_stop_losses} | {r.tp_path_losses} |"
        )

    lines += ["","## 70% fixed-N diagnostic",
      "The audit does not convert any historical loss into a win. It only checks whether enough current losses occurred on objectively rebounding (+1ZW-valid) demand events to make a fixed-trade-count 70% WR mechanically conceivable through execution improvement.",
      "If the valid-zone-loss count is smaller than the required conversions, the detector/zone layer itself is the hard ceiling under this +1ZW diagnostic."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S7_LAYER_ATTRIBUTION_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
