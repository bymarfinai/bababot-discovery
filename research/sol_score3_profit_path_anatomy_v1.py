#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_adaptive_tp_v1 as tp
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_SCORE3_PROFIT_PATH_ANATOMY_V1"
CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
RETRO_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)

SIGNATURES=(
    "ABS_DD_025R",
    "ABS_DD_050R",
    "FRAC_DD_25PCT",
    "FRAC_DD_50PCT",
    "TWO_OPPOSITE_CLOSES",
    "MICRO_BREAK_3BAR",
)

MILESTONES=(.25,.50,.75,1.00,1.50)


def directional_r(price,entry,risk,short):
    return (entry-price)/risk if short else (price-entry)/risk


def path_for_trade(r,x5):
    idx=x5.index
    op=x5.open.astype(float).to_numpy()
    hi=x5.high.astype(float).to_numpy()
    lo=x5.low.astype(float).to_numpy()
    cl=x5.close.astype(float).to_numpy()

    entry=float(r.entry_price)
    stop=float(r.stop_price)
    risk=float(r.initial_risk_price)
    short=(str(r.side)=="BUY_SIDE")
    start=int(r.entry_i_5m)
    end=int(idx.searchsorted(pd.Timestamp(r.outcome_known_time),side="left"))
    end=min(end,len(x5))

    if not (np.isfinite(entry) and np.isfinite(stop) and np.isfinite(risk) and risk>0):
        return None, []
    if start<0 or start>=end:
        return None, []

    mfe=0.0
    mae=0.0
    mfe_i=start
    mfe_time=idx[start]
    activation_050_i=None
    milestones={m:None for m in MILESTONES}
    sig_state={s:None for s in SIGNATURES}

    bars=[]
    stopped=False
    stop_i=-1
    stop_time=pd.NaT

    for i in range(start,end):
        # Conservative: active SL is checked before using any other intrabar extreme.
        sl_hit=bool(hi[i]>=stop) if short else bool(lo[i]<=stop)
        if sl_hit:
            stopped=True
            stop_i=i
            stop_time=idx[i]
            break

        favorable=directional_r(lo[i] if short else hi[i],entry,risk,short)
        adverse=-directional_r(hi[i] if short else lo[i],entry,risk,short)
        favorable=max(0.0,float(favorable))
        adverse=max(0.0,float(adverse))

        if favorable>mfe:
            mfe=favorable
            mfe_i=i
            mfe_time=idx[i]
        mae=max(mae,adverse)

        for m in MILESTONES:
            if milestones[m] is None and mfe>=m:
                milestones[m]=idx[i]

        if activation_050_i is None and mfe>=.50:
            activation_050_i=i

        close_r=directional_r(cl[i],entry,risk,short)
        dd_abs=mfe-close_r
        dd_frac=(dd_abs/mfe) if mfe>0 else np.nan

        bars.append({
            "i":i,
            "time":idx[i],
            "open":op[i],
            "high":hi[i],
            "low":lo[i],
            "close":cl[i],
            "close_r":float(close_r),
            "running_mfe_r":float(mfe),
        })

        if activation_050_i is None:
            continue

        # Absolute/relative giveback signatures.
        if sig_state["ABS_DD_025R"] is None and dd_abs>=.25:
            sig_state["ABS_DD_025R"]=(i,idx[i],float(close_r),float(mfe))
        if sig_state["ABS_DD_050R"] is None and dd_abs>=.50:
            sig_state["ABS_DD_050R"]=(i,idx[i],float(close_r),float(mfe))
        if sig_state["FRAC_DD_25PCT"] is None and np.isfinite(dd_frac) and dd_frac>=.25:
            sig_state["FRAC_DD_25PCT"]=(i,idx[i],float(close_r),float(mfe))
        if sig_state["FRAC_DD_50PCT"] is None and np.isfinite(dd_frac) and dd_frac>=.50:
            sig_state["FRAC_DD_50PCT"]=(i,idx[i],float(close_r),float(mfe))

        # Two consecutive adverse candle bodies, both after +0.50R activation.
        if sig_state["TWO_OPPOSITE_CLOSES"] is None and i-1>=activation_050_i:
            if short:
                opp_now=cl[i]>op[i]
                opp_prev=cl[i-1]>op[i-1]
            else:
                opp_now=cl[i]<op[i]
                opp_prev=cl[i-1]<op[i-1]
            if opp_now and opp_prev:
                sig_state["TWO_OPPOSITE_CLOSES"]=(i,idx[i],float(close_r),float(mfe))

        # 3-bar micro reversal break, using only prior completed bars.
        if sig_state["MICRO_BREAK_3BAR"] is None and i>=activation_050_i and i>=3:
            if short:
                trig=cl[i]>max(hi[i-3:i])
            else:
                trig=cl[i]<min(lo[i-3:i])
            if trig:
                sig_state["MICRO_BREAK_3BAR"]=(i,idx[i],float(close_r),float(mfe))

    if stopped:
        terminal_r=-1.0
        terminal_time=stop_time
        terminal_type="SL"
        path_end_i=stop_i
    else:
        ei=int(idx.searchsorted(pd.Timestamp(r.outcome_known_time),side="left"))
        if ei<len(x5):
            terminal_price=float(x5.iloc[ei].open)
            terminal_time=idx[ei]
            path_end_i=ei
        else:
            terminal_price=float(x5.iloc[-1].close)
            terminal_time=idx[-1]
            path_end_i=len(x5)-1
        terminal_r=float(directional_r(terminal_price,entry,risk,short))
        terminal_type="HORIZON"

    giveback=float(mfe-terminal_r)
    retained=float(terminal_r/mfe) if mfe>0 else np.nan

    if int(r.event_label)==1:
        if mfe<.50:
            cohort="NEVER_REACHED_050R"
        elif giveback<.25:
            cohort="RETAINED"
        elif giveback<.50:
            cohort="MODERATE_GIVEBACK"
        else:
            cohort="LARGE_GIVEBACK"
    else:
        cohort="NEGATIVE_EVENT"

    path_row={
        "candidate_id":r.candidate_id,
        "side":r.side,
        "anatomy_score":int(r.anatomy_score),
        "event_label":int(r.event_label),
        "outcome":r.outcome,
        "entry_time":r.entry_time,
        "entry_price":entry,
        "stop_price":stop,
        "initial_risk_price":risk,
        "outcome_known_time":r.outcome_known_time,
        "terminal_type":terminal_type,
        "terminal_time":terminal_time,
        "terminal_r":terminal_r,
        "mfe_r":float(mfe),
        "mae_r":float(mae),
        "mfe_time":mfe_time,
        "time_to_mfe_min":float((pd.Timestamp(mfe_time)-pd.Timestamp(r.entry_time)).total_seconds()/60.0),
        "giveback_r":giveback,
        "retained_fraction":retained,
        "profit_path_cohort":cohort,
        "reached_050r":int(mfe>=.50),
        "static_sl_hit":int(stopped),
    }
    for m in MILESTONES:
        key=str(m).replace(".","_")
        t=milestones[m]
        path_row[f"touch_{key}r_time"]=t if t is not None else pd.NaT
        path_row[f"touch_{key}r_min"]=(
            float((pd.Timestamp(t)-pd.Timestamp(r.entry_time)).total_seconds()/60.0)
            if t is not None else np.nan
        )

    sig_rows=[]
    # For recovery, inspect only valid bars after each trigger and before stop/horizon.
    for s in SIGNATURES:
        z=sig_state[s]
        if z is None:
            sig_rows.append({
                "candidate_id":r.candidate_id,
                "signature":s,
                "side":r.side,
                "event_label":int(r.event_label),
                "entry_time":r.entry_time,
                "triggered":0,
                "trigger_i_5m":-1,
                "trigger_time":pd.NaT,
                "trigger_close_r":np.nan,
                "pretrigger_peak_r":np.nan,
                "terminal_r":terminal_r,
                "saved_r":np.nan,
                "recovered_new_peak":0,
                "new_peak_increment_r":np.nan,
                "time_trigger_to_end_min":np.nan,
            })
            continue

        ti,tt,tr,pre_peak=z
        later_peak=pre_peak
        # Only use bars already accepted into the path (stop bar was never appended).
        for b in bars:
            if b["i"]>ti:
                later_peak=max(later_peak,float(b["running_mfe_r"]))
        recovered=later_peak>pre_peak+1e-12
        sig_rows.append({
            "candidate_id":r.candidate_id,
            "signature":s,
            "side":r.side,
            "event_label":int(r.event_label),
            "entry_time":r.entry_time,
            "triggered":1,
            "trigger_i_5m":int(ti),
            "trigger_time":tt,
            "trigger_close_r":float(tr),
            "pretrigger_peak_r":float(pre_peak),
            "terminal_r":terminal_r,
            "saved_r":float(tr-terminal_r),
            "recovered_new_peak":int(recovered),
            "new_peak_increment_r":float(max(0.0,later_peak-pre_peak)),
            "time_trigger_to_end_min":float((pd.Timestamp(terminal_time)-pd.Timestamp(tt)).total_seconds()/60.0),
        })

    return path_row,sig_rows


def build_period(x5,end_time,years,phase):
    trades,_,_,x=tp.prepared_trades(x5,end_time,years)
    trades=trades[trades.anatomy_score==3].copy().reset_index(drop=True)

    paths=[]
    sigs=[]
    for _,r in trades.iterrows():
        p,s=path_for_trade(r,x)
        if p is not None:
            p["phase"]=phase
            paths.append(p)
            for z in s:
                z["phase"]=phase
                sigs.append(z)

    return pd.DataFrame(paths),pd.DataFrame(sigs)


def path_summary(paths):
    rows=[]
    for phase in paths.phase.unique():
        p=paths[paths.phase==phase]
        for group,label in (("POSITIVE",1),("NEGATIVE",0)):
            g=p[p.event_label==label]
            rows.append({
                "phase":phase,
                "group":group,
                "n":len(g),
                "mfe_median":float(g.mfe_r.median()) if len(g) else np.nan,
                "mfe_p25":float(g.mfe_r.quantile(.25)) if len(g) else np.nan,
                "mfe_p75":float(g.mfe_r.quantile(.75)) if len(g) else np.nan,
                "mae_median":float(g.mae_r.median()) if len(g) else np.nan,
                "time_to_mfe_median_min":float(g.time_to_mfe_min.median()) if len(g) else np.nan,
                "terminal_r_median":float(g.terminal_r.median()) if len(g) else np.nan,
                "giveback_median":float(g.giveback_r.median()) if len(g) else np.nan,
                "reached_050r_rate":float(g.reached_050r.mean()) if len(g) else np.nan,
                "static_sl_hit_rate":float(g.static_sl_hit.mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)


def cohort_summary(paths):
    rows=[]
    p=paths[paths.event_label==1].copy()
    for phase in p.phase.unique():
        z=p[p.phase==phase]
        for c,g in z.groupby("profit_path_cohort"):
            rows.append({
                "phase":phase,
                "cohort":c,
                "n":len(g),
                "share":len(g)/len(z) if len(z) else np.nan,
                "median_mfe_r":float(g.mfe_r.median()),
                "median_terminal_r":float(g.terminal_r.median()),
                "median_giveback_r":float(g.giveback_r.median()),
                "median_time_to_mfe_min":float(g.time_to_mfe_min.median()),
            })
    return pd.DataFrame(rows)


def year_summary(paths):
    x=paths.copy()
    x["year"]=pd.to_datetime(x.entry_time,utc=True).dt.year.astype(int)
    rows=[]
    for (phase,year,label),g in x.groupby(["phase","year","event_label"]):
        rows.append({
            "phase":phase,
            "year":int(year),
            "group":"POSITIVE" if int(label)==1 else "NEGATIVE",
            "n":len(g),
            "median_mfe_r":float(g.mfe_r.median()),
            "median_terminal_r":float(g.terminal_r.median()),
            "median_giveback_r":float(g.giveback_r.median()),
            "reached_050r_rate":float(g.reached_050r.mean()),
        })
    return pd.DataFrame(rows)


def signature_audit(paths,sigs):
    rows=[]
    year_rows=[]

    for phase in paths.phase.unique():
        p=paths[paths.phase==phase].copy()
        s=sigs[sigs.phase==phase].copy()
        pos_eligible=p[(p.event_label==1)&(p.reached_050r==1)]
        neg_eligible=p[(p.event_label==0)&(p.reached_050r==1)]

        for signature in SIGNATURES:
            ss=s[s.signature==signature]
            sp=ss[(ss.event_label==1)&(ss.triggered==1)]
            sn=ss[(ss.event_label==0)&(ss.triggered==1)]

            pos_trig_rate=len(sp)/len(pos_eligible) if len(pos_eligible) else np.nan
            neg_trig_rate=len(sn)/len(neg_eligible) if len(neg_eligible) else np.nan

            row={
                "phase":phase,
                "signature":signature,
                "positive_eligible_050r_n":len(pos_eligible),
                "positive_trigger_n":len(sp),
                "positive_trigger_rate":pos_trig_rate,
                "negative_eligible_050r_n":len(neg_eligible),
                "negative_trigger_n":len(sn),
                "negative_trigger_rate":neg_trig_rate,
                "median_pretrigger_peak_r":float(sp.pretrigger_peak_r.median()) if len(sp) else np.nan,
                "median_trigger_close_r":float(sp.trigger_close_r.median()) if len(sp) else np.nan,
                "median_terminal_r":float(sp.terminal_r.median()) if len(sp) else np.nan,
                "median_saved_r":float(sp.saved_r.median()) if len(sp) else np.nan,
                "recovery_rate":float(sp.recovered_new_peak.mean()) if len(sp) else np.nan,
                "median_new_peak_increment_r":float(sp.new_peak_increment_r.median()) if len(sp) else np.nan,
                "median_trigger_to_end_min":float(sp.time_trigger_to_end_min.median()) if len(sp) else np.nan,
            }

            # Development candidate gates only on discovery phase.
            if phase=="DISCOVERY_2020_2024":
                sx=sp.copy()
                sx["year"]=pd.to_datetime(sx.entry_time,utc=True).dt.year.astype(int)
                positive_saved_years=0
                for year in (2020,2021,2022,2023,2024):
                    gy=sx[sx.year==year]
                    med_saved=float(gy.saved_r.median()) if len(gy) else np.nan
                    ok=bool(np.isfinite(med_saved) and med_saved>0)
                    positive_saved_years+=int(ok)
                    year_rows.append({
                        "phase":phase,
                        "signature":signature,
                        "year":year,
                        "trigger_n":len(gy),
                        "median_saved_r":med_saved,
                        "saved_positive":ok,
                    })

                candidate=bool(
                    len(pos_eligible)>=80
                    and len(sp)>=40
                    and np.isfinite(row["median_saved_r"]) and row["median_saved_r"]>=.20
                    and np.isfinite(row["recovery_rate"]) and row["recovery_rate"]<=.35
                    and np.isfinite(row["median_trigger_close_r"]) and row["median_trigger_close_r"]>0
                    and positive_saved_years>=4
                )
                row["positive_saved_years"]=positive_saved_years
                row["development_candidate"]=candidate

            elif phase=="RETROSPECTIVE_2025":
                consistent=bool(
                    len(pos_eligible)>=15
                    and len(sp)>=8
                    and np.isfinite(row["median_saved_r"]) and row["median_saved_r"]>0
                    and np.isfinite(row["recovery_rate"]) and row["recovery_rate"]<=.45
                    and np.isfinite(row["median_trigger_close_r"]) and row["median_trigger_close_r"]>0
                )
                row["retrospective_consistent"]=consistent

            rows.append(row)

    return pd.DataFrame(rows),pd.DataFrame(year_rows)


def fmt(v,d=3):
    return "n/a" if not np.isfinite(v) else f"{v:.{d}f}"


def pct(v):
    return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    pdev,sdev=build_period(x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024],"DISCOVERY_2020_2024")
    p25,s25=build_period(x5,RETRO_END,[2025],"RETROSPECTIVE_2025")

    paths=pd.concat([pdev,p25],ignore_index=True)
    sigs=pd.concat([sdev,s25],ignore_index=True)

    ps=path_summary(paths)
    cs=cohort_summary(paths)
    ys=year_summary(paths)
    audit,year_audit=signature_audit(paths,sigs)

    dev_a=audit[audit.phase=="DISCOVERY_2020_2024"].copy()
    retro_a=audit[audit.phase=="RETROSPECTIVE_2025"].copy()
    candidates=dev_a[dev_a.development_candidate==True].copy() if "development_candidate" in dev_a.columns else pd.DataFrame()

    # Attach retrospective consistency for the same signature.
    promoted=[]
    for _,r in candidates.iterrows():
        rr=retro_a[retro_a.signature==r.signature]
        consistent=bool(len(rr) and bool(rr.iloc[0].get("retrospective_consistent",False)))
        promoted.append({
            "signature":r.signature,
            "development_candidate":True,
            "retrospective_2025_consistent":consistent,
            "status":"PROFIT_GIVEBACK_SIGNATURE_CANDIDATE" if consistent else "DEVELOPMENT_ONLY_NOT_CONSISTENT_2025"
        })
    promoted=pd.DataFrame(promoted)

    paths.to_csv(ROOT/f"{PFX}_Paths.csv",index=False)
    sigs.to_csv(ROOT/f"{PFX}_SignatureEvents.csv",index=False)
    ps.to_csv(ROOT/f"{PFX}_PathSummary.csv",index=False)
    cs.to_csv(ROOT/f"{PFX}_CohortSummary.csv",index=False)
    ys.to_csv(ROOT/f"{PFX}_YearSummary.csv",index=False)
    audit.to_csv(ROOT/f"{PFX}_SignatureAudit.csv",index=False)
    year_audit.to_csv(ROOT/f"{PFX}_SignatureYearAudit.csv",index=False)
    promoted.to_csv(ROOT/f"{PFX}_Candidates.csv",index=False)

    dev_pos=pdev[pdev.event_label==1]
    retro_pos=p25[p25.event_label==1]

    lines=[
        "# SOL Score-3 Profit-Path Anatomy V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Scope: anatomy score 3 only.",
        "- Entry and RECLAIM_EXTREME SL frozen.",
        "- No TP active.",
        "- 2025 is retrospective consistency only; 2026+ CLOSED.","",
        "## Core positive-event anatomy","",
        f"- 2020-2024 positive N: **{len(dev_pos)}**",
        f"- 2020-2024 median MFE: **{fmt(dev_pos.mfe_r.median())}R**",
        f"- 2020-2024 median terminal R: **{fmt(dev_pos.terminal_r.median())}R**",
        f"- 2020-2024 median giveback: **{fmt(dev_pos.giveback_r.median())}R**",
        f"- 2020-2024 reached +0.50R: **{pct(dev_pos.reached_050r.mean())}**",
        f"- 2020-2024 median time-to-MFE: **{fmt(dev_pos.time_to_mfe_min.median(),1)} min**",
        f"- 2025 positive N: **{len(retro_pos)}**",
        f"- 2025 median MFE: **{fmt(retro_pos.mfe_r.median())}R**",
        f"- 2025 median terminal R: **{fmt(retro_pos.terminal_r.median())}R**",
        f"- 2025 median giveback: **{fmt(retro_pos.giveback_r.median())}R**",
        "",
        "## Positive profit-path cohorts","",
        "| Phase | Cohort | N | Share | Median MFE | Median terminal | Median giveback |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _,r in cs.iterrows():
        lines.append(
            f"| {r.phase} | {r.cohort} | {int(r.n)} | {pct(r.share)} | "
            f"{fmt(r.median_mfe_r)} | {fmt(r.median_terminal_r)} | {fmt(r.median_giveback_r)} |"
        )

    lines+=["","## Causal giveback signature audit","",
            "| Phase | Signature | Eligible +0.5R | Trigger N | Trigger rate | Median exit-at-trigger R | Median final R | Median saved R | Recovery rate | Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _,r in audit.iterrows():
        if r.phase=="DISCOVERY_2020_2024":
            status="CANDIDATE" if bool(r.get("development_candidate",False)) else "NO"
        else:
            status="CONSISTENT" if bool(r.get("retrospective_consistent",False)) else "NO"
        lines.append(
            f"| {r.phase} | {r.signature} | {int(r.positive_eligible_050r_n)} | {int(r.positive_trigger_n)} | "
            f"{pct(r.positive_trigger_rate)} | {fmt(r.median_trigger_close_r)} | {fmt(r.median_terminal_r)} | "
            f"{fmt(r.median_saved_r)} | {pct(r.recovery_rate)} | {status} |"
        )

    lines+=["","## Candidate status",""]
    if len(promoted):
        for _,r in promoted.iterrows():
            lines.append(f"- **{r.signature}** — {r.status}")
        final_status=(
            "PROFIT_GIVEBACK_SIGNATURE_CANDIDATE_FOUND"
            if (promoted.status=="PROFIT_GIVEBACK_SIGNATURE_CANDIDATE").any()
            else "NO_RETROSPECTIVELY_CONSISTENT_GIVEBACK_SIGNATURE"
        )
    else:
        lines.append("- No development signature passed all preregistered candidate gates.")
        final_status="NO_PROFIT_GIVEBACK_SIGNATURE_CANDIDATE"

    lines+=["",f"**VERDICT: {final_status}**","",
            "This is anatomy discovery only. No TP or adaptive exit has been validated.","",
            "2026_PLUS=CLOSED"]

    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(final_status+"\n2026_PLUS=CLOSED\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
