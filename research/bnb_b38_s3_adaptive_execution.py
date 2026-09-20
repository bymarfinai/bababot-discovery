#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s2_h1d_15m_archetypes as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S3_ADAPTIVE_EXECUTION"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2024-12-31T23:59:59Z")

def safe_div(a,b):
    if not np.isfinite(a) or not np.isfinite(b) or abs(b)<1e-12:
        return np.nan
    return float(a/b)

def objective_ladder(entry_ts,entry_price,activation_ts,expansion_high,m15_hi,h1_hi):
    candidates=[]
    q15=m15_hi[
        (m15_hi.pivot_ts>=activation_ts)&
        (m15_hi.confirm_ts<=entry_ts)&
        (m15_hi.level>entry_price)
    ]
    for r in q15.itertuples(index=False):
        candidates.append((float(r.level),"15M_PIVOT_HIGH",r.pivot_ts,r.confirm_ts))

    if float(expansion_high)>entry_price:
        candidates.append((float(expansion_high),"EXPANSION_HIGH",pd.NaT,pd.NaT))

    q1=h1_hi[
        (h1_hi.pivot_ts>=activation_ts)&
        (h1_hi.confirm_ts<=entry_ts)&
        (h1_hi.level>entry_price)
    ]
    for r in q1.itertuples(index=False):
        candidates.append((float(r.level),"H1_PIVOT_HIGH",r.pivot_ts,r.confirm_ts))

    if not candidates:
        return []

    # Collapse exactly-equal price levels while preserving all known structural sources.
    by_price={}
    for level,source,pts,cts in candidates:
        key=float(level)
        if key not in by_price:
            by_price[key]={"level":key,"sources":set(),"pivot_ts":[],"confirm_ts":[]}
        by_price[key]["sources"].add(source)
        if pd.notna(pts): by_price[key]["pivot_ts"].append(pts)
        if pd.notna(cts): by_price[key]["confirm_ts"].append(cts)

    out=[]
    for level in sorted(by_price):
        x=by_price[level]
        out.append({
            "level":level,
            "source":"+".join(sorted(x["sources"])),
            "pivot_ts":max(x["pivot_ts"]) if x["pivot_ts"] else pd.NaT,
            "confirm_ts":max(x["confirm_ts"]) if x["confirm_ts"] else pd.NaT,
        })
    return out

def make_plan(r,entry_ts,entry_price,sl_ref,mode,status,m15_hi,h1_hi,wait_bars=0,swept_during_wait=False):
    width=float(r.demand_width)
    risk=float(entry_price-sl_ref)
    ladder=objective_ladder(
        entry_ts,float(entry_price),r.activation_ts,float(r.expansion_high),m15_hi,h1_hi
    )
    row={
        "zone_id":r.zone_id,
        "activation_ts":r.activation_ts,
        "first_touch_ts":r.first_touch_ts,
        "first_touch_archetype":s2.classify(r),
        "execution_status":status,
        "execution_mode":mode,
        "entry_ts":entry_ts,
        "entry_price":float(entry_price) if np.isfinite(entry_price) else np.nan,
        "sl_reference":float(sl_ref) if np.isfinite(sl_ref) else np.nan,
        "demand_low":float(r.demand_low),
        "demand_high":float(r.demand_high),
        "demand_width":width,
        "expansion_high":float(r.expansion_high),
        "wait_bars_15m":int(wait_bars),
        "swept_during_wait":bool(swept_during_wait),
        "risk_abs":risk if np.isfinite(risk) else np.nan,
        "risk_zw":safe_div(risk,width),
        "risk_pct":safe_div(risk,float(entry_price)) if np.isfinite(entry_price) else np.nan,
        "known_target_count":len(ladder),
        "target_state":"HAS_KNOWN_OVERHEAD_OBJECTIVE" if ladder else "NO_KNOWN_OVERHEAD_OBJECTIVE",
    }
    for k in range(1,4):
        if len(ladder)>=k:
            t=ladder[k-1]
            room=float(t["level"]-entry_price)
            row[f"tp{k}_level"]=t["level"]
            row[f"tp{k}_source"]=t["source"]
            row[f"tp{k}_room_zw"]=safe_div(room,width)
            row[f"tp{k}_rr"]=safe_div(room,risk)
        else:
            row[f"tp{k}_level"]=np.nan
            row[f"tp{k}_source"]=""
            row[f"tp{k}_room_zw"]=np.nan
            row[f"tp{k}_rr"]=np.nan
    return row

def adaptive_plan(m15,h1,fam):
    m15_hi,_=s1.pivots_df(m15)
    h1_hi,_=s1.pivots_df(h1)
    idx=m15.index
    rows=[]

    for r in fam.itertuples(index=False):
        arch=s2.classify(r)

        if arch=="A_CLEAN_PROXIMAL_RECLAIM":
            rows.append(make_plan(
                r,r.first_touch_ts,float(r.touch_close),float(r.demand_low),
                "IMMEDIATE_CLEAN_RECLAIM","ENTRY",m15_hi,h1_hi
            ))
            continue

        if arch=="C_SWEEP_FULL_RECLAIM":
            rows.append(make_plan(
                r,r.first_touch_ts,float(r.touch_close),float(r.touch_low),
                "IMMEDIATE_SWEEP_RECLAIM","ENTRY",m15_hi,h1_hi,
                swept_during_wait=True
            ))
            continue

        start_i=int(idx.searchsorted(r.first_touch_ts,side="right"))
        end_i=int(idx.searchsorted(END,side="right"))
        swept=bool(float(r.touch_low)<float(r.demand_low))
        lowest=float(r.touch_low) if swept else float(r.demand_low)
        triggered=False
        cancelled=False

        for j,i in enumerate(range(start_i,end_i),start=1):
            bar=m15.iloc[i]
            lo=float(bar.low); cl=float(bar.close)
            if lo<float(r.demand_low):
                swept=True
                lowest=min(lowest,lo)

            if cl<float(r.demand_low):
                rows.append(make_plan(
                    r,idx[i],np.nan,np.nan,
                    "PENDING_RECLAIM","CANCELLED_DEMAND_ACCEPTANCE",m15_hi,h1_hi,
                    wait_bars=j,swept_during_wait=swept
                ))
                cancelled=True
                break

            if cl>float(r.demand_high):
                mode="DELAYED_SWEEP_RECLAIM" if swept else "DELAYED_CLEAN_RECLAIM"
                sl=lowest if swept else float(r.demand_low)
                rows.append(make_plan(
                    r,idx[i],cl,sl,mode,"ENTRY",m15_hi,h1_hi,
                    wait_bars=j,swept_during_wait=swept
                ))
                triggered=True
                break

        if not triggered and not cancelled:
            rows.append(make_plan(
                r,pd.NaT,np.nan,np.nan,
                "PENDING_RECLAIM","NO_TRIGGER_BY_END",m15_hi,h1_hi,
                wait_bars=max(0,end_i-start_i),swept_during_wait=swept
            ))

    return pd.DataFrame(rows)

def med(q,col):
    x=pd.to_numeric(q[col],errors="coerce").dropna()
    return float(x.median()) if len(x) else np.nan

def pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def num(x,d=2):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(f"raw coverage low {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity fail {ident}")

    h1=s1.exact_exec(raw,"1h",12)
    m15=s1.exact_exec(raw,"15min",3)
    h1=h1[h1.index<=END].copy()
    m15=m15[m15.index<=END].copy()

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=END)
    ].copy()
    if len(fam)!=788:
        raise RuntimeError(f"frozen family drift: {len(fam)} != 788")

    P=adaptive_plan(m15,h1,fam)
    if len(P)!=788:
        raise RuntimeError(f"plan ledger incomplete: {len(P)} != 788")

    P["retest_year"]=pd.to_datetime(P.first_touch_ts,utc=True).dt.year.astype(int)

    transition=P.groupby(
        ["first_touch_archetype","execution_status","execution_mode"],
        dropna=False
    ).size().reset_index(name="n")

    entries=P[P.execution_status=="ENTRY"].copy()
    modes=[]
    for mode,q in entries.groupby("execution_mode"):
        modes.append({
            "execution_mode":mode,
            "n":len(q),
            "y2022":int((q.retest_year==2022).sum()),
            "y2023":int((q.retest_year==2023).sum()),
            "y2024":int((q.retest_year==2024).sum()),
            "wait_bars_med":med(q,"wait_bars_15m"),
            "risk_zw_med":med(q,"risk_zw"),
            "risk_pct_med":med(q,"risk_pct"),
            "targets_med":med(q,"known_target_count"),
            "no_target_n":int((q.target_state=="NO_KNOWN_OVERHEAD_OBJECTIVE").sum()),
            "tp1_room_zw_med":med(q,"tp1_room_zw"),
            "tp1_rr_med":med(q,"tp1_rr"),
            "tp2_room_zw_med":med(q,"tp2_room_zw"),
            "tp2_rr_med":med(q,"tp2_rr"),
        })
    M=pd.DataFrame(modes)

    src=Counter()
    for col in ["tp1_source","tp2_source","tp3_source"]:
        for x in entries[col].fillna("").astype(str):
            if x: src[(col,x)]+=1
    Src=pd.DataFrame([
        {"target_slot":k[0],"source":k[1],"n":v} for k,v in sorted(src.items())
    ])

    P.to_csv(ROOT/f"{PFX}_PlanLedger.csv.gz",index=False,compression="gzip")
    transition.to_csv(ROOT/f"{PFX}_Transitions.csv",index=False)
    M.to_csv(ROOT/f"{PFX}_ModeGeometry.csv",index=False)
    Src.to_csv(ROOT/f"{PFX}_TargetSources.csv",index=False)

    status_counts=P.execution_status.value_counts().to_dict()
    lines=[
      "# BNB B38-S3 — Adaptive Execution State Machine","",
      "**2022-2024 EXECUTION DESIGN — NO TRADE-OUTCOME SCORING**","",
      "Frozen parent: **788 H1-demand / 15m structural events**.","",
      "## Adaptive state machine","",
      "- **A clean proximal reclaim:** entry at first-touch 15m close; invalidation reference = H1 demand_low.",
      "- **C sweep full reclaim:** entry at first-touch 15m close; invalidation reference = actual sweep low.",
      "- **B/D inside-zone close:** remain PENDING; first later 15m close above demand_high triggers entry. A close below demand_low before confirmation cancels the setup.",
      "- If any sweep occurs while pending, the confirmed execution becomes DELAYED_SWEEP_RECLAIM and invalidation reference = lowest sweep low seen through confirmation.","",
      "## Execution census",
      f"- ENTRY plans: **{status_counts.get('ENTRY',0)}**",
      f"- Cancelled by demand acceptance before reclaim: **{status_counts.get('CANCELLED_DEMAND_ACCEPTANCE',0)}**",
      f"- No trigger by end-2024: **{status_counts.get('NO_TRIGGER_BY_END',0)}**","",
      "## First-touch archetype → execution transition","",
      "| First-touch archetype | Status | Execution mode | N |",
      "|---|---|---|---:|"
    ]
    for r in transition.itertuples(index=False):
        lines.append(f"| {r.first_touch_archetype} | {r.execution_status} | {r.execution_mode} | {r.n} |")

    lines += ["","## Entry-plan geometry by execution mode","",
      "| Mode | N | 2022/23/24 | Wait | Risk | Risk % | TP1 room | TP1 RR | TP2 room | TP2 RR | No target |",
      "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in M.itertuples(index=False):
        lines.append(
            f"| {r.execution_mode} | {r.n} | {r.y2022}/{r.y2023}/{r.y2024} | "
            f"{num(r.wait_bars_med)} x15m | {num(r.risk_zw_med)}ZW | {pct(r.risk_pct_med)} | "
            f"{num(r.tp1_room_zw_med)}ZW | {num(r.tp1_rr_med)}R | "
            f"{num(r.tp2_room_zw_med)}ZW | {num(r.tp2_rr_med)}R | {r.no_target_n} |"
        )

    lines += ["","## Structural target construction",
      "At each entry close, the engine builds a price-sorted ladder from **already-confirmed 15m pivot highs, the frozen expansion high, and already-confirmed H1 pivot highs** above entry.",
      "TP1/TP2/TP3 are therefore event-specific structural objectives; no fixed percentage target is introduced.","",
      "## B38-S3 freeze",
      "**ADAPTIVE EXECUTION LOGIC FROZEN.**",
      "S3 does not say which execution mode is profitable. It only defines when entry becomes structurally confirmed, where structural invalidation resides, and which overhead objectives are actually available at that moment.",
      "The next experiment may score this frozen engine, but must not alter these rules after reading outcomes."
    ]

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S3_ADAPTIVE_EXECUTION_FROZEN\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
