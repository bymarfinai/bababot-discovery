#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import sol_adaptive_risk_manager_v1 as rm
import sol_adaptive_tp_v1 as tp
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_SCORE4_FAILURE_ANATOMY_V1"

END_2024=pd.Timestamp("2025-01-01",tz="UTC")
END_2025=pd.Timestamp("2026-01-01",tz="UTC")
END_2026_PRE=pd.Timestamp("2026-08-26 00:00:00",tz="UTC")
BAR5=pd.Timedelta(minutes=5)

PERIODS=(
    ("HIST_2020_2024",END_2024,[2020,2021,2022,2023,2024]),
    ("RETRO_2025",END_2025,[2025]),
    ("RETRO_2026_PRE",END_2026_PRE,[2026]),
)

RAW_FEATURES=(
    "source_to_opposite_structure_range_units",
    "approach_start_distance_to_level_range_units",
    "reclaim_directional_body_range_units",
    "reclaim_close_inside_range_units",
)

CONT_FEATURES=(
    *RAW_FEATURES,
    "time_to_fill_min",
    "directional_improvement_range_units",
    "initial_risk_range_units",
    "structural_target_distance_range_units",
    "structural_reward_r",
    "mfe_r",
    "mae_r",
    "time_to_mfe_min",
    "terminal_r",
    "giveback_r",
    "retained_fraction",
    "time_to_structural_outcome_min",
    "time_to_050r_min",
    "time_to_100r_min",
    "time_to_150r_min",
    "close_r_30m",
    "close_r_60m",
    "close_r_120m",
    "running_mfe_r_30m",
    "running_mfe_r_60m",
    "running_mfe_r_120m",
    "running_mae_r_30m",
    "running_mae_r_60m",
    "running_mae_r_120m",
    "max_adverse_before_first_050r",
    "favorable_efficiency",
    "close_path_sign_flip_rate",
)


def pf(rs):
    s=pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(s[s>0].sum()); neg=float(-s[s<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


def dir_r(price,entry,risk,short):
    return (entry-price)/risk if short else (price-entry)/risk


def build_score4_period(x5,end_time,years,period):
    trades,pop,h1,x=rm.prepare_period(x5,end_time,years)
    t=trades[trades.anatomy_score==4].copy().reset_index(drop=True)
    if t.empty:
        return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()

    # Merge raw detector-strength magnitudes known at reclaim close.
    raw_cols=["candidate_id",*RAW_FEATURES]
    raw=pop[raw_cols].drop_duplicates("candidate_id")
    t=t.merge(raw,on="candidate_id",how="left",validate="one_to_one")

    t["structural_reward_r"]=(
        pd.to_numeric(t.structural_target_distance_range_units,errors="coerce") /
        pd.to_numeric(t.initial_risk_range_units,errors="coerce")
    )

    # Structural-completion realized result.
    sc=rm.simulate_policy(t,x,"STATIC_RECLAIM_EXTREME")
    sc_keep=sc[[
        "candidate_id","exit_type","exit_time","realized_r","time_to_exit_min"
    ]].rename(columns={
        "exit_type":"structural_exit_type",
        "exit_time":"structural_exit_time",
        "realized_r":"structural_realized_r",
        "time_to_exit_min":"structural_time_to_exit_min",
    })
    t=t.merge(sc_keep,on="candidate_id",how="inner",validate="one_to_one")

    # Fixed 1.5R comparator on same rows.
    fixed=tp.simulate_candidate(t,x,"FIXED_150R")
    fx=fixed[[
        "candidate_id","exit_type","realized_r","time_to_exit_min"
    ]].rename(columns={
        "exit_type":"fixed150_exit_type",
        "realized_r":"fixed150_realized_r",
        "time_to_exit_min":"fixed150_time_to_exit_min",
    })
    t=t.merge(fx,on="candidate_id",how="left",validate="one_to_one")

    path_rows=[]
    idx=x.index
    op=x.open.astype(float).to_numpy()
    hi=x.high.astype(float).to_numpy()
    lo=x.low.astype(float).to_numpy()
    cl=x.close.astype(float).to_numpy()

    for _,r in t.iterrows():
        entry=float(r.entry_price)
        stop=float(r.stop_price)
        risk=float(r.initial_risk_price)
        short=str(r.side)=="BUY_SIDE"
        start=int(r.entry_i_5m)
        end=int(idx.searchsorted(pd.Timestamp(r.outcome_known_time),side="left"))
        end=min(end,len(x))

        if not(np.isfinite(entry) and np.isfinite(stop) and np.isfinite(risk) and risk>0):
            continue
        if start<0 or start>=end:
            continue

        mfe=0.0
        mae=0.0
        mfe_time=idx[start]
        touch050=None; touch100=None; touch150=None
        first_fav050=None; first_adv050=None
        max_adv_before_050=0.0
        checkpoints={30:None,60:None,120:None}

        close_path_abs=0.0
        prev_close=entry
        directional_steps=[]

        stopped=False
        stop_time=pd.NaT
        terminal_r=np.nan
        terminal_time=pd.NaT

        for i in range(start,end):
            # Conservative stop-first handling.
            sl_hit=bool(hi[i]>=stop) if short else bool(lo[i]<=stop)
            if sl_hit:
                stopped=True
                stop_time=idx[i]
                terminal_r=-1.0
                terminal_time=idx[i]
                break

            fav=max(0.0,float(dir_r(lo[i] if short else hi[i],entry,risk,short)))
            adv=max(0.0,float(-dir_r(hi[i] if short else lo[i],entry,risk,short)))
            if fav>mfe:
                mfe=fav
                mfe_time=idx[i]
            mae=max(mae,adv)

            if touch050 is None and mfe>=.50: touch050=idx[i]
            if touch100 is None and mfe>=1.00: touch100=idx[i]
            if touch150 is None and mfe>=1.50: touch150=idx[i]

            if first_fav050 is None and fav>=.50:
                first_fav050=i
            if first_adv050 is None and adv>=.50:
                first_adv050=i

            # If both first occur in the same bar, count adverse first.
            if first_fav050 is None:
                max_adv_before_050=max(max_adv_before_050,adv)
            elif first_fav050==i:
                max_adv_before_050=max(max_adv_before_050,adv)

            close_step=float(cl[i]-prev_close)
            if short:
                close_step=-close_step
            close_path_abs+=abs(float(cl[i]-prev_close))
            if abs(close_step)>1e-12:
                directional_steps.append(1 if close_step>0 else -1)
            prev_close=float(cl[i])

            bar_close=idx[i]+BAR5
            for mins in (30,60,120):
                if checkpoints[mins] is None:
                    cp_time=pd.Timestamp(r.entry_time)+pd.Timedelta(minutes=mins)
                    if bar_close>=cp_time:
                        checkpoints[mins]={
                            "close_r":float(dir_r(cl[i],entry,risk,short)),
                            "mfe_r":float(mfe),
                            "mae_r":float(mae),
                        }

        if not stopped:
            ei=int(idx.searchsorted(pd.Timestamp(r.outcome_known_time),side="left"))
            if ei<len(x):
                ep=float(x.iloc[ei].open); terminal_time=idx[ei]
            else:
                ep=float(x.iloc[-1].close); terminal_time=idx[-1]
            terminal_r=float(dir_r(ep,entry,risk,short))

        giveback=float(mfe-terminal_r)
        retained=float(terminal_r/mfe) if mfe>0 else np.nan

        if first_fav050 is not None:
            if first_adv050 is None:
                fav_before_adv=1
            elif first_fav050<first_adv050:
                fav_before_adv=1
            else:
                fav_before_adv=0
        else:
            fav_before_adv=np.nan

        # Path efficiency based on accepted completed 5m closes only.
        if close_path_abs>0:
            close_net=dir_r(prev_close,entry,risk,short)
            favorable_eff=float((close_net*risk)/close_path_abs)
        else:
            favorable_eff=np.nan

        flips=np.nan
        if len(directional_steps)>=2:
            flips=sum(1 for a,b in zip(directional_steps[:-1],directional_steps[1:]) if a!=b)/(len(directional_steps)-1)

        if terminal_r>=.75:
            cohort="STRONG_WIN"
        elif terminal_r>0:
            cohort="SMALL_WIN"
        elif terminal_r>-.50:
            cohort="SMALL_LOSS"
        else:
            cohort="LARGE_LOSS"

        row=r.to_dict()
        row.update({
            "period":period,
            "mfe_r":float(mfe),
            "mae_r":float(mae),
            "time_to_mfe_min":float((pd.Timestamp(mfe_time)-pd.Timestamp(r.entry_time)).total_seconds()/60.0),
            "terminal_r":float(terminal_r),
            "giveback_r":giveback,
            "retained_fraction":retained,
            "time_to_structural_outcome_min":float(
                (pd.Timestamp(r.outcome_known_time)-pd.Timestamp(r.entry_time)).total_seconds()/60.0
            ),
            "static_sl_hit":int(stopped),
            "touched_050r":int(touch050 is not None),
            "touched_100r":int(touch100 is not None),
            "touched_150r":int(touch150 is not None),
            "time_to_050r_min":float((pd.Timestamp(touch050)-pd.Timestamp(r.entry_time)).total_seconds()/60.0) if touch050 is not None else np.nan,
            "time_to_100r_min":float((pd.Timestamp(touch100)-pd.Timestamp(r.entry_time)).total_seconds()/60.0) if touch100 is not None else np.nan,
            "time_to_150r_min":float((pd.Timestamp(touch150)-pd.Timestamp(r.entry_time)).total_seconds()/60.0) if touch150 is not None else np.nan,
            "first_touch_050_before_adverse_050":fav_before_adv,
            "max_adverse_before_first_050r":float(max_adv_before_050),
            "favorable_efficiency":favorable_eff,
            "close_path_sign_flip_rate":flips,
            "failure_cohort":cohort,
        })
        for mins in (30,60,120):
            z=checkpoints[mins]
            row[f"close_r_{mins}m"]=z["close_r"] if z else np.nan
            row[f"running_mfe_r_{mins}m"]=z["mfe_r"] if z else np.nan
            row[f"running_mae_r_{mins}m"]=z["mae_r"] if z else np.nan

        path_rows.append(row)

    anatomy=pd.DataFrame(path_rows)
    return anatomy,t,fixed


def summarize_period(anatomy):
    rows=[]
    for period,g in anatomy.groupby("period"):
        rows.append({
            "period":period,
            "n":len(g),
            "mean_terminal_r":float(g.terminal_r.mean()),
            "median_terminal_r":float(g.terminal_r.median()),
            "pf_terminal":float(pf(g.terminal_r)),
            "mean_fixed150_r":float(g.fixed150_realized_r.mean()),
            "pf_fixed150":float(pf(g.fixed150_realized_r)),
            "median_mfe_r":float(g.mfe_r.median()),
            "median_mae_r":float(g.mae_r.median()),
            "median_giveback_r":float(g.giveback_r.median()),
            "median_retained_fraction":float(g.retained_fraction.median()),
            "median_time_to_mfe_min":float(g.time_to_mfe_min.median()),
            "median_time_to_outcome_min":float(g.time_to_structural_outcome_min.median()),
            "sl_hit_rate":float(g.static_sl_hit.mean()),
            "touch_050r_rate":float(g.touched_050r.mean()),
            "touch_100r_rate":float(g.touched_100r.mean()),
            "touch_150r_rate":float(g.touched_150r.mean()),
            "positive_event_negative_realized_share":float(((g.event_label==1)&(g.terminal_r<0)).mean()),
            "negative_event_positive_realized_share":float(((g.event_label==0)&(g.terminal_r>0)).mean()),
        })
    return pd.DataFrame(rows)


def side_summary(anatomy):
    rows=[]
    for (period,side),g in anatomy.groupby(["period","side"]):
        rows.append({
            "period":period,"side":side,"n":len(g),
            "mean_terminal_r":float(g.terminal_r.mean()),
            "pf_terminal":float(pf(g.terminal_r)),
            "median_mfe_r":float(g.mfe_r.median()),
            "median_giveback_r":float(g.giveback_r.median()),
            "sl_hit_rate":float(g.static_sl_hit.mean()),
        })
    return pd.DataFrame(rows)


def outcome_summary(anatomy):
    rows=[]
    for (period,label),g in anatomy.groupby(["period","event_label"]):
        rows.append({
            "period":period,
            "group":"POSITIVE" if int(label)==1 else "NEGATIVE",
            "n":len(g),
            "mean_terminal_r":float(g.terminal_r.mean()),
            "median_terminal_r":float(g.terminal_r.median()),
            "median_mfe_r":float(g.mfe_r.median()),
            "median_mae_r":float(g.mae_r.median()),
            "median_giveback_r":float(g.giveback_r.median()),
            "touch_100r_rate":float(g.touched_100r.mean()),
            "sl_hit_rate":float(g.static_sl_hit.mean()),
        })
    return pd.DataFrame(rows)


def cohort_summary(anatomy):
    rows=[]
    for (period,cohort),g in anatomy.groupby(["period","failure_cohort"]):
        n_period=len(anatomy[anatomy.period==period])
        rows.append({
            "period":period,"cohort":cohort,"n":len(g),
            "share":len(g)/n_period if n_period else np.nan,
            "median_mfe_r":float(g.mfe_r.median()),
            "median_giveback_r":float(g.giveback_r.median()),
            "event_positive_rate":float(g.event_label.mean()),
        })
    return pd.DataFrame(rows)


def feature_shift_audit(anatomy):
    hist=anatomy[anatomy.period=="HIST_2020_2024"]
    y25=anatomy[anatomy.period=="RETRO_2025"]
    y26=anatomy[anatomy.period=="RETRO_2026_PRE"]
    rows=[]

    for feature in CONT_FEATURES:
        hs=pd.to_numeric(hist[feature],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
        s25=pd.to_numeric(y25[feature],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
        s26=pd.to_numeric(y26[feature],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()

        hm=float(hs.median()) if len(hs) else np.nan
        iqr=float(hs.quantile(.75)-hs.quantile(.25)) if len(hs) else np.nan
        m25=float(s25.median()) if len(s25) else np.nan
        m26=float(s26.median()) if len(s26) else np.nan

        sh25=(m25-hm)/iqr if np.isfinite(iqr) and iqr>0 and np.isfinite(m25) and np.isfinite(hm) else np.nan
        sh26=(m26-hm)/iqr if np.isfinite(iqr) and iqr>0 and np.isfinite(m26) and np.isfinite(hm) else np.nan
        material=bool(
            np.isfinite(sh26) and abs(sh26)>=.50
            and (not np.isfinite(sh25) or abs(sh26)>=abs(sh25)+.25)
        )
        direction="UP" if np.isfinite(sh26) and sh26>0 else ("DOWN" if np.isfinite(sh26) and sh26<0 else "FLAT_OR_NA")

        rows.append({
            "feature":feature,
            "hist_n":len(hs),"hist_median":hm,"hist_iqr":iqr,
            "y2025_n":len(s25),"y2025_median":m25,"shift_2025_iqr":sh25,
            "y2026_n":len(s26),"y2026_median":m26,"shift_2026_iqr":sh26,
            "material_2026_shift":material,
            "shift_direction":direction,
        })

    return pd.DataFrame(rows)


def comparator_summary(anatomy):
    rows=[]
    for period,g in anatomy.groupby("period"):
        rows.append({
            "period":period,
            "n":len(g),
            "structural_completion_mean_r":float(g.terminal_r.mean()),
            "structural_completion_pf":float(pf(g.terminal_r)),
            "fixed150_mean_r":float(g.fixed150_realized_r.mean()),
            "fixed150_pf":float(pf(g.fixed150_realized_r)),
            "mean_delta_structural_minus_fixed":float(g.terminal_r.mean()-g.fixed150_realized_r.mean()),
        })
    return pd.DataFrame(rows)


def diagnose(anatomy,period_summary,side_sum,shift):
    sh=shift.set_index("feature")

    def mat_down(f):
        return f in sh.index and bool(sh.loc[f,"material_2026_shift"]) and sh.loc[f,"shift_direction"]=="DOWN"
    def mat_up(f):
        return f in sh.index and bool(sh.loc[f,"material_2026_shift"]) and sh.loc[f,"shift_direction"]=="UP"

    p=period_summary.set_index("period")
    hist_touch=float(p.loc["HIST_2020_2024","touch_100r_rate"])
    y26_touch=float(p.loc["RETRO_2026_PRE","touch_100r_rate"])

    modes=[]
    a=mat_down("mfe_r") or (np.isfinite(hist_touch) and np.isfinite(y26_touch) and y26_touch<=hist_touch-.15)
    if a: modes.append("FAILURE_MODE_A_NO_FAVORABLE_EXCURSION")

    b=mat_up("giveback_r") or mat_down("retained_fraction")
    if b: modes.append("FAILURE_MODE_B_EXCESS_GIVEBACK")

    c=mat_up("initial_risk_range_units") or mat_down("structural_reward_r")
    if c: modes.append("FAILURE_MODE_C_RISK_GEOMETRY_EXPANSION")

    d=mat_up("time_to_mfe_min") or mat_down("running_mfe_r_60m") or mat_down("running_mfe_r_120m")
    if d: modes.append("FAILURE_MODE_D_SLOW_OR_STALLED_DELIVERY")

    s26=side_sum[side_sum.period=="RETRO_2026_PRE"].set_index("side")
    e=False
    if "BUY_SIDE" in s26.index and "SELL_SIDE" in s26.index:
        bmean=float(s26.loc["BUY_SIDE","mean_terminal_r"])
        smean=float(s26.loc["SELL_SIDE","mean_terminal_r"])
        e=abs(bmean-smean)>=.30 and ((bmean<0<smean) or (smean<0<bmean))
    if e: modes.append("FAILURE_MODE_E_SIDE_CONCENTRATION")

    if not modes:
        modes=["FAILURE_MODE_F_UNRESOLVED_MIXED"]

    return modes


def fmt(v,d=3):
    return "n/a" if not np.isfinite(v) else ("inf" if np.isinf(v) else f"{v:.{d}f}")


def pct(v):
    return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    frames=[]
    for period,end_time,years in PERIODS:
        a,_,_=build_score4_period(x5,end_time,years,period)
        frames.append(a)

    anatomy=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    if anatomy.empty:
        raise RuntimeError("no score-4 anatomy rows")

    ps=summarize_period(anatomy)
    ss=side_summary(anatomy)
    os=outcome_summary(anatomy)
    cs=cohort_summary(anatomy)
    fs=feature_shift_audit(anatomy)
    comps=comparator_summary(anatomy)
    modes=diagnose(anatomy,ps,ss,fs)

    anatomy.to_csv(ROOT/f"{PFX}_Trades.csv",index=False)
    ps.to_csv(ROOT/f"{PFX}_PeriodSummary.csv",index=False)
    ss.to_csv(ROOT/f"{PFX}_SideSummary.csv",index=False)
    os.to_csv(ROOT/f"{PFX}_OutcomeSummary.csv",index=False)
    cs.to_csv(ROOT/f"{PFX}_FailureCohorts.csv",index=False)
    fs.to_csv(ROOT/f"{PFX}_FeatureShiftAudit.csv",index=False)
    comps.to_csv(ROOT/f"{PFX}_ComparatorSummary.csv",index=False)
    pd.DataFrame({"diagnosis":modes}).to_csv(ROOT/f"{PFX}_Diagnosis.csv",index=False)

    p=ps.set_index("period")
    lines=[
        "# SOL Score-4 Failure Anatomy V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Score 4 only; GAP25 entry; static RECLAIM_EXTREME SL.",
        "- Primary exit analyzed: structural completion.",
        "- All evidence through 2026-08-26 is retrospective.",
        "- Post-cutoff data remained CLOSED.","",
        "## Period anatomy","",
        "| Period | N | Mean R | PF | Median MFE | Median giveback | SL hit | Touch 1.0R | Fixed 1.5R mean |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _,r in ps.iterrows():
        lines.append(
            f"| {r.period} | {int(r.n)} | {fmt(r.mean_terminal_r)} | {fmt(r.pf_terminal)} | "
            f"{fmt(r.median_mfe_r)} | {fmt(r.median_giveback_r)} | {pct(r.sl_hit_rate)} | "
            f"{pct(r.touch_100r_rate)} | {fmt(r.mean_fixed150_r)} |"
        )

    lines+=["","## 2026 material feature shifts","",
            "| Feature | Hist median | 2025 shift | 2026 shift | Direction | Material |",
            "|---|---:|---:|---:|---|---|"]
    for _,r in fs[fs.material_2026_shift==True].sort_values("shift_2026_iqr",key=lambda s:s.abs(),ascending=False).iterrows():
        lines.append(
            f"| {r.feature} | {fmt(r.hist_median)} | {fmt(r.shift_2025_iqr)} IQR | "
            f"{fmt(r.shift_2026_iqr)} IQR | {r.shift_direction} | YES |"
        )
    if not fs.material_2026_shift.any():
        lines.append("| none | — | — | — | — | NO |")

    lines+=["","## 2026 side anatomy","",
            "| Side | N | Mean R | PF | Median MFE | Median giveback |",
            "|---|---:|---:|---:|---:|---:|"]
    for _,r in ss[ss.period=="RETRO_2026_PRE"].iterrows():
        lines.append(
            f"| {r.side} | {int(r.n)} | {fmt(r.mean_terminal_r)} | {fmt(r.pf_terminal)} | "
            f"{fmt(r.median_mfe_r)} | {fmt(r.median_giveback_r)} |"
        )

    lines+=["","## Failure cohorts","",
            "| Period | Cohort | N | Share | Median MFE | Median giveback | Positive-event rate |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for _,r in cs.iterrows():
        lines.append(
            f"| {r.period} | {r.cohort} | {int(r.n)} | {pct(r.share)} | "
            f"{fmt(r.median_mfe_r)} | {fmt(r.median_giveback_r)} | {pct(r.event_positive_rate)} |"
        )

    lines+=["","## Frozen diagnosis",""]
    for m in modes:
        lines.append(f"- **{m}**")

    if len(modes)==1 and modes[0]=="FAILURE_MODE_F_UNRESOLVED_MIXED":
        verdict="SCORE4_FAILURE_ANATOMY_UNRESOLVED"
    else:
        verdict="SCORE4_FAILURE_MODE_IDENTIFIED_RETROSPECTIVELY"

    lines+=["",f"**VERDICT: {verdict}**","",
            "No filter, TP, or exit rule was created in this experiment. Any next rule must be preregistered separately and requires fresh future data for validation.","",
            "POST_CUTOFF_DATA=CLOSED"]

    pd.DataFrame([{
        "coverage":coverage,
        "hist_n":int(p.loc["HIST_2020_2024","n"]),
        "hist_mean_r":float(p.loc["HIST_2020_2024","mean_terminal_r"]),
        "y2025_n":int(p.loc["RETRO_2025","n"]),
        "y2025_mean_r":float(p.loc["RETRO_2025","mean_terminal_r"]),
        "y2026_pre_n":int(p.loc["RETRO_2026_PRE","n"]),
        "y2026_pre_mean_r":float(p.loc["RETRO_2026_PRE","mean_terminal_r"]),
        "diagnoses":";".join(modes),
        "verdict":verdict,
    }]).to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\nPOST_CUTOFF_DATA=CLOSED\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
