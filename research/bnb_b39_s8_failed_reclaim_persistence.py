#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s4_first5_expansion_detector as s4
import bnb_b39_s6_structural_invalidation as s6
import bnb_b39_s7_post_entry_failure_character as s7

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S8_FAILED_RECLAIM_PERSISTENCE"
START=pd.Timestamp("2022-01-01T00:00:00Z")
D1_CUT=s4.D1_CUT
EXPECTED_SIGNATURE=s4.DETECTOR_SIGNATURE

CANDS=[
    "D1_TWO_CLOSES_BELOW",
    "D1_NO_RECLAIM_15M",
    "D1_RECLAIM_ATTEMPT_REJECT",
    "ANCHOR_TWO_CLOSES_BELOW",
    "ANCHOR_NO_RECLAIM_15M",
    "ANCHOR_RECLAIM_ATTEMPT_REJECT",
]

FAMILY={
    "D1_TWO_CLOSES_BELOW":"D1",
    "D1_NO_RECLAIM_15M":"D1",
    "D1_RECLAIM_ATTEMPT_REJECT":"D1",
    "ANCHOR_TWO_CLOSES_BELOW":"ANCHOR",
    "ANCHOR_NO_RECLAIM_15M":"ANCHOR",
    "ANCHOR_RECLAIM_ATTEMPT_REJECT":"ANCHOR",
}

S7_BASE={
    ("DEV","D1"):(0.7906976744186046,0.18518518518518517,0.012613997043449569),
    ("REF","D1"):(0.8235294117647058,0.2289156626506024,0.06307426764565145),
    ("DEV","ANCHOR"):(0.8837209302325582,0.25,0.007853200104430181),
    ("REF","ANCHOR"):(0.8823529411764706,0.27710843373493976,0.04432982618662151),
}
WIDE_BASE_EXP={"DEV":0.013702429268110569,"REF":0.16317037818336672}

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    if x==np.inf:return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def maxdd(rs):
    if not len(rs): return np.nan
    a=np.asarray(rs,float)
    c=np.cumsum(a)
    p=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(p-c))

def resolution_hit(b,target,floor):
    return bool(float(b.high)>=target), bool(float(b.low)<=floor)

def find_first_breach(raw5,entry_ts,target,floor,level,deadline):
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(entry_ts),side="right"))
    i1=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))
    for i in range(i0,i1):
        b=raw5.iloc[i]
        tp,sl=resolution_hit(b,target,floor)
        if float(b.close)<level:
            if tp or sl:
                return {"status":"AMBIGUOUS_INITIAL_BREACH","breach_i":None}
            return {"status":"BREACH","breach_i":i}
        if tp or sl:
            return {"status":"NO_BREACH_BEFORE_RESOLUTION","breach_i":None}
    return {"status":"NO_BREACH","breach_i":None}

def eval_candidate(raw5,entry_ts,target,floor,level,deadline,mode):
    idx=raw5.index
    fb=find_first_breach(raw5,entry_ts,target,floor,level,deadline)
    if fb["status"]!="BREACH":
        return {"signal_status":fb["status"],"signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":pd.NaT}

    bi=int(fb["breach_i"])
    breach_ts=idx[bi]
    end_i=int(idx.searchsorted(pd.Timestamp(deadline),side="right"))

    if mode=="TWO":
        j=bi+1
        if j>=end_i:
            return {"signal_status":"CENSORED_CONFIRMATION","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
        b=raw5.iloc[j]
        tp,sl=resolution_hit(b,target,floor)
        if tp or sl:
            return {"signal_status":"RESOLUTION_DURING_CONFIRMATION","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
        if float(b.close)<level:
            return {"signal_status":"CLEAN_SIGNAL","signal_ts":idx[j],"exit_price":float(b.close),"breach_ts":breach_ts}
        return {"signal_status":"RECLAIMED","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}

    if mode=="NO_RECLAIM15":
        js=[bi+1,bi+2,bi+3]
        if js[-1]>=end_i:
            return {"signal_status":"CENSORED_CONFIRMATION","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
        for j in js:
            b=raw5.iloc[j]
            tp,sl=resolution_hit(b,target,floor)
            if tp or sl:
                return {"signal_status":"RESOLUTION_DURING_CONFIRMATION","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
            if float(b.close)>=level:
                return {"signal_status":"RECLAIMED","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
        b=raw5.iloc[js[-1]]
        return {"signal_status":"CLEAN_SIGNAL","signal_ts":idx[js[-1]],"exit_price":float(b.close),"breach_ts":breach_ts}

    if mode=="REJECT":
        last=min(end_i-1,bi+3)
        if last<=bi:
            return {"signal_status":"CENSORED_CONFIRMATION","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
        for j in range(bi+1,last+1):
            b=raw5.iloc[j]
            tp,sl=resolution_hit(b,target,floor)
            if tp or sl:
                return {"signal_status":"RESOLUTION_DURING_CONFIRMATION","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
            # A completed reclaim invalidates the failed-reclaim pattern.
            if float(b.close)>=level:
                return {"signal_status":"RECLAIMED","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}
            if float(b.high)>=level and float(b.close)<level:
                return {"signal_status":"CLEAN_SIGNAL","signal_ts":idx[j],"exit_price":float(b.close),"breach_ts":breach_ts}
        return {"signal_status":"NO_RECLAIM_ATTEMPT","signal_ts":pd.NaT,"exit_price":np.nan,"breach_ts":breach_ts}

    raise RuntimeError(mode)

def false_exit_anatomy(raw5,signal_ts,level,target,deadline,entry,floor):
    ti=s7.first_touch_idx(raw5,signal_ts,target,"HIGH",deadline)
    if ti is None:
        return {
            "later_target_ts":pd.NaT,"minutes_to_target":np.nan,
            "overshoot_original_r":np.nan,"reclaim_next5":False,"reclaim_within15":False
        }
    later_ts=raw5.index[ti]
    idx=raw5.index
    i0=int(idx.searchsorted(pd.Timestamp(signal_ts),side="left"))
    seg=raw5.iloc[i0:ti+1]
    orig=entry-floor
    overshoot=max(0.0,(level-float(seg.low.min()))/orig) if len(seg) and orig>0 else np.nan
    fl=s7.reclaim_flags(raw5,signal_ts,level,deadline)
    return {
        "later_target_ts":later_ts,
        "minutes_to_target":float((later_ts-pd.Timestamp(signal_ts))/pd.Timedelta(minutes=1)),
        "overshoot_original_r":overshoot,
        **fl
    }

def summarize(q,period,cand):
    q=q.sort_values(["entry_ts","zone_id"]).copy()
    bw=q[q.baseline_status=="WIN"]; bl=q[q.baseline_status=="LOSS"]
    clean=q[q.signal_status=="CLEAN_SIGNAL"]
    cw=clean[clean.baseline_status=="WIN"]; cl=clean[clean.baseline_status=="LOSS"]

    cf=q.copy()
    cf["cf_r"]=np.where(cf.signal_status=="CLEAN_SIGNAL",cf.signal_realized_r,cf.baseline_realized_r)
    cf["cf_status"]=np.where(cf.cf_r>1e-12,"WIN",np.where(cf.cf_r<-1e-12,"LOSS","BE"))
    pos=float(cf.loc[cf.cf_r>0,"cf_r"].sum())
    neg=abs(float(cf.loc[cf.cf_r<0,"cf_r"].sum()))

    fam=FAMILY[cand]
    s7_lc,s7_fe,s7_exp=S7_BASE[(period,fam)]
    exp=float(cf.cf_r.mean()) if len(cf) else np.nan

    return {
        "n":len(q),
        "baseline_wins":len(bw),"baseline_losses":len(bl),
        "clean_signals":len(clean),"signal_rate":len(clean)/len(q) if len(q) else np.nan,
        "loss_captured":len(cl),"loss_capture_rate":len(cl)/len(bl) if len(bl) else np.nan,
        "winner_false_exit":len(cw),"winner_false_exit_rate":len(cw)/len(bw) if len(bw) else np.nan,
        "precision_loss":len(cl)/len(clean) if len(clean) else np.nan,
        "median_exit_r_loss":float(cl.signal_realized_r.median()) if len(cl) else np.nan,
        "median_lead_to_floor_min":float(cl.minutes_signal_to_baseline_resolution.median()) if len(cl) else np.nan,
        "median_lead_to_target_min":float(cw.minutes_signal_to_baseline_resolution.median()) if len(cw) else np.nan,
        "false_exit_reclaim_next5_rate":float(cw.reclaim_next5.mean()) if len(cw) else np.nan,
        "false_exit_reclaim_within15_rate":float(cw.reclaim_within15.mean()) if len(cw) else np.nan,
        "cf_wins":int((cf.cf_status=="WIN").sum()),"cf_losses":int((cf.cf_status=="LOSS").sum()),
        "cf_be":int((cf.cf_status=="BE").sum()),
        "cf_expectancy_r":exp,"cf_total_r":float(cf.cf_r.sum()),
        "cf_pf":pos/neg if neg>0 else (np.inf if pos>0 else np.nan),
        "cf_max_dd_r":maxdd(cf.cf_r.tolist()),
        "delta_vs_wide_baseline":exp-WIDE_BASE_EXP[period],
        "s7_single_loss_capture_rate":s7_lc,
        "s7_single_false_exit_rate":s7_fe,
        "s7_single_expectancy_r":s7_exp,
        "delta_expectancy_vs_s7_single":exp-s7_exp,
        "loss_capture_change_vs_s7":(len(cl)/len(bl)-s7_lc) if len(bl) else np.nan,
        "false_exit_change_vs_s7":(len(cw)/len(bw)-s7_fe) if len(bw) else np.nan,
    }

def main():
    if s4.DETECTOR_SIGNATURE!=EXPECTED_SIGNATURE:
        raise RuntimeError("D1 detector signature drift")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    s1.START=START; s1.END=end
    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=end].copy()
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=end].copy()
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    fam["period"]=["DEV" if pd.Timestamp(x)<=pd.Timestamp("2024-12-31T23:59:59Z") else "REF" for x in fam.first_touch_ts]
    fam["year"]=pd.to_datetime(fam.first_touch_ts,utc=True).dt.year
    F=fam.set_index("zone_id")

    L4=s4.build_ledger(raw5,m15,h1,fam,end)
    P=L4[(L4.decision=="PLUS5_CLOSE")&(L4.decision_status=="ELIGIBLE")].copy()
    P["signal"]=pd.to_numeric(P.p5_close_r,errors="coerce")>D1_CUT
    P=P[P.signal].copy()

    hard={
        "DEV_N":int((P.period=="DEV").sum()),"DEV_GE1":int(((P.period=="DEV")&P.GE1R).sum()),
        "REF_N":int((P.period=="REF").sum()),"REF_GE1":int(((P.period=="REF")&P.GE1R).sum()),
    }
    if hard!={"DEV_N":151,"DEV_GE1":108,"REF_N":101,"REF_GE1":83}:
        raise RuntimeError(f"D1 parity drift {hard}")

    rows=[]
    baseline_check={"DEV":{"WIN":0,"LOSS":0,"AMBIGUOUS":0,"UNRESOLVED":0},
                    "REF":{"WIN":0,"LOSS":0,"AMBIGUOUS":0,"UNRESOLVED":0}}

    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        anchor=float(r.anchor_price)
        er=float(r.event_risk)
        floor=float(r.demand_low)
        entry=float(anchor+float(r.p5_close_r)*er)
        target=anchor+er
        d1_low=float(anchor+float(r.p5_low_r)*er)
        deadline=min(end,pd.Timestamp(r.first_touch_ts)+pd.Timedelta(hours=24))

        bz=s6.resolve(raw5,r.decision_ts,entry,floor,target,deadline)
        bs=bz["status"]; br=float(bz["realized_r"]); bt=bz["resolution_ts"]
        baseline_check[r.period][bs]=baseline_check[r.period].get(bs,0)+1

        defs={
            "D1_TWO_CLOSES_BELOW":(d1_low,"TWO"),
            "D1_NO_RECLAIM_15M":(d1_low,"NO_RECLAIM15"),
            "D1_RECLAIM_ATTEMPT_REJECT":(d1_low,"REJECT"),
            "ANCHOR_TWO_CLOSES_BELOW":(anchor,"TWO"),
            "ANCHOR_NO_RECLAIM_15M":(anchor,"NO_RECLAIM15"),
            "ANCHOR_RECLAIM_ATTEMPT_REJECT":(anchor,"REJECT"),
        }
        orig=entry-floor

        for cand,(level,mode) in defs.items():
            z=eval_candidate(raw5,r.decision_ts,target,floor,level,deadline,mode)
            if z["signal_status"]=="CLEAN_SIGNAL":
                exit_r=(float(z["exit_price"])-entry)/orig
                mins=float((pd.Timestamp(bt)-pd.Timestamp(z["signal_ts"]))/pd.Timedelta(minutes=1)) if pd.notna(bt) else np.nan
            else:
                exit_r=np.nan; mins=np.nan

            anat={
                "later_target_ts":pd.NaT,"minutes_to_target":np.nan,
                "overshoot_original_r":np.nan,"reclaim_next5":False,"reclaim_within15":False
            }
            if z["signal_status"]=="CLEAN_SIGNAL" and bs=="WIN":
                anat=false_exit_anatomy(raw5,z["signal_ts"],level,target,deadline,entry,floor)

            rows.append({
                "zone_id":r.zone_id,"period":r.period,"year":r.year,
                "entry_ts":r.decision_ts,"candidate":cand,"family":FAMILY[cand],
                "entry":entry,"target":target,"floor":floor,"anchor":anchor,"d1_low":d1_low,
                "signal_level":level,"signal_status":z["signal_status"],
                "breach_ts":z["breach_ts"],"signal_ts":z["signal_ts"],
                "signal_exit_price":z["exit_price"],"signal_realized_r":exit_r,
                "minutes_signal_to_baseline_resolution":mins,
                "baseline_status":bs,"baseline_realized_r":br,"baseline_resolution_ts":bt,
                "GE1R":bool(r.GE1R),**anat
            })

    if baseline_check["DEV"].get("WIN",0)!=108 or baseline_check["DEV"].get("LOSS",0)!=43:
        raise RuntimeError(f"DEV baseline parity drift {baseline_check['DEV']}")
    if baseline_check["REF"].get("WIN",0)!=83 or baseline_check["REF"].get("LOSS",0)!=17 or baseline_check["REF"].get("AMBIGUOUS",0)!=1:
        raise RuntimeError(f"REF baseline parity drift {baseline_check['REF']}")

    E=pd.DataFrame(rows)

    SUM=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=E[(E.period==per)&(E.candidate==cand)]
            SUM.append({"period":per,"candidate":cand,"family":FAMILY[cand],**summarize(q,per,cand)})
    SUM=pd.DataFrame(SUM)

    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        per="DEV" if y<=2024 else "REF"
        for cand in CANDS:
            q=E[(E.year==y)&(E.candidate==cand)]
            if len(q):
                # yearly metrics without comparing to S7 aggregate
                bw=q[q.baseline_status=="WIN"]; bl=q[q.baseline_status=="LOSS"]
                clean=q[q.signal_status=="CLEAN_SIGNAL"]
                cw=clean[clean.baseline_status=="WIN"]; cl=clean[clean.baseline_status=="LOSS"]
                cf=q.copy()
                cf["cf_r"]=np.where(cf.signal_status=="CLEAN_SIGNAL",cf.signal_realized_r,cf.baseline_realized_r)
                Y.append({
                    "year":y,"candidate":cand,"family":FAMILY[cand],"n":len(q),
                    "loss_captured":len(cl),"baseline_losses":len(bl),
                    "loss_capture_rate":len(cl)/len(bl) if len(bl) else np.nan,
                    "winner_false_exit":len(cw),"baseline_wins":len(bw),
                    "winner_false_exit_rate":len(cw)/len(bw) if len(bw) else np.nan,
                    "precision_loss":len(cl)/len(clean) if len(clean) else np.nan,
                    "cf_expectancy_r":float(cf.cf_r.mean()),"cf_total_r":float(cf.cf_r.sum())
                })
    Y=pd.DataFrame(Y)

    FW=E[(E.signal_status=="CLEAN_SIGNAL")&(E.baseline_status=="WIN")].copy()
    FWS=[]
    for per in ["DEV","REF"]:
        for cand in CANDS:
            q=FW[(FW.period==per)&(FW.candidate==cand)]
            FWS.append({
                "period":per,"candidate":cand,"false_exit_winners":len(q),
                "reclaim_next5":int(q.reclaim_next5.sum()) if len(q) else 0,
                "reclaim_next5_rate":float(q.reclaim_next5.mean()) if len(q) else np.nan,
                "reclaim_within15":int(q.reclaim_within15.sum()) if len(q) else 0,
                "reclaim_within15_rate":float(q.reclaim_within15.mean()) if len(q) else np.nan,
                "median_signal_to_target_min":float(q.minutes_to_target.median()) if len(q) else np.nan,
                "median_overshoot_original_r":float(q.overshoot_original_r.median()) if len(q) else np.nan,
            })
    FWS=pd.DataFrame(FWS)

    E.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    FWS.to_csv(ROOT/f"{PFX}_FalseExitWinnerSummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"DETECTOR=D1_FIRST5_DISPLACEMENT\n"
        f"DETECTOR_SIGNATURE_SHA256={EXPECTED_SIGNATURE}\n"
        f"D1_P5_CLOSE_R_GT={D1_CUT:.17f}\n"
        "ENTRY=MARKET_SIGNAL_CLOSE\nTARGET=ANCHOR_PLUS_1_EVENT_R\nSTRUCTURAL_FLOOR=DEMAND_LOW\n"
        "LEVELS=D1_LOW,ANCHOR\nPERSISTENCE_LENGTHS=NEXT1_CLOSE,NEXT3_CLOSES\n"
        "CANDIDATES=D1_TWO_CLOSES_BELOW,D1_NO_RECLAIM_15M,D1_RECLAIM_ATTEMPT_REJECT,ANCHOR_TWO_CLOSES_BELOW,ANCHOR_NO_RECLAIM_15M,ANCHOR_RECLAIM_ATTEMPT_REJECT\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S8 — Failed-Reclaim Persistence Character","",
        f"Frozen detector signature: `{EXPECTED_SIGNATURE}`",
        "D1, market entry, +1 event-R target, and demand-low structural floor remain unchanged.","",
        "## Persistence audit","",
        "| Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | CF Exp | Δ vs wide | Δ vs S7 single | S7 loss cap→S8 | S7 false exit→S8 | Total R | PF |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {r.clean_signals}/{r.n} ({fmt_pct(r.signal_rate)}) | "
            f"{r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.precision_loss)} | {fmt_num(r.cf_expectancy_r)}R | "
            f"{fmt_num(r.delta_vs_wide_baseline)}R | {fmt_num(r.delta_expectancy_vs_s7_single)}R | "
            f"{fmt_pct(r.s7_single_loss_capture_rate)}→{fmt_pct(r.loss_capture_rate)} | "
            f"{fmt_pct(r.s7_single_false_exit_rate)}→{fmt_pct(r.winner_false_exit_rate)} | "
            f"{fmt_num(r.cf_total_r)}R | {fmt_num(r.cf_pf)} |"
        )

    lines += ["","## Annual stability","",
        "| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | CF Exp | Total R |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.candidate} | {r.loss_captured}/{r.baseline_losses} ({fmt_pct(r.loss_capture_rate)}) | "
            f"{r.winner_false_exit}/{r.baseline_wins} ({fmt_pct(r.winner_false_exit_rate)}) | "
            f"{fmt_pct(r.precision_loss)} | {fmt_num(r.cf_expectancy_r)}R | {fmt_num(r.cf_total_r)}R |"
        )

    lines += ["","## False-exit reclaim after persistence signal","",
        "| Period | Candidate | False exits | Reclaim next5 | Reclaim <=15m | Med signal→target | Med overshoot |",
        "|---|---|---:|---:|---:|---:|---:|"
    ]
    for r in FWS.itertuples(index=False):
        if r.false_exit_winners:
            lines.append(
                f"| {r.period} | {r.candidate} | {r.false_exit_winners} | "
                f"{r.reclaim_next5} ({fmt_pct(r.reclaim_next5_rate)}) | "
                f"{r.reclaim_within15} ({fmt_pct(r.reclaim_within15_rate)}) | "
                f"{fmt_num(r.median_signal_to_target_min,1)}m | {fmt_num(r.median_overshoot_original_r)} original-R |"
            )

    lines += ["","## Interpretation boundary",
        "S8 tests persistence and failed reclaim only; levels are unchanged from S7.",
        "No candidate is promoted unless it improves wide-floor expectancy in both DEV and REF and improves separation versus the corresponding S7 single-breach state.",
        "If none passes, the wide structural floor remains the correct protection and failure-exit tuning stops."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S8_FAILED_RECLAIM_PERSISTENCE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
