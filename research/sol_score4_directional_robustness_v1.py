#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import math
import numpy as np
import pandas as pd

import sol_score4_failure_anatomy_v1 as a1
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_SCORE4_DIRECTIONAL_ROBUSTNESS_V1"

END_2024=pd.Timestamp("2025-01-01",tz="UTC")
END_2025=pd.Timestamp("2026-01-01",tz="UTC")
FRESH_CUTOFF=pd.Timestamp("2026-08-26 00:00:00",tz="UTC")

FROZEN_FILL=15.0
FROZEN_IMPROVEMENT=0.21471170803

FILL_GRID=(10.0,15.0,20.0)
IMPROVEMENT_GRID=(0.171769366424,0.214711708030,0.257654049636)

BOOT_N=20000
BOOT_SEED=42017


def pf(rs):
    x=pd.Series(rs,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(x[x>0].sum())
    neg=float(-x[x<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


def m(g):
    if g is None or len(g)==0:
        return {
            "n":0,"event_n":0,"event_rate":np.nan,
            "mean_r":np.nan,"pf_r":np.nan,"cum_r":0.0
        }
    return {
        "n":int(len(g)),
        "event_n":int(g.event_label.sum()),
        "event_rate":float(g.event_label.mean()),
        "mean_r":float(g.terminal_r.mean()),
        "pf_r":float(pf(g.terminal_r)),
        "cum_r":float(g.terminal_r.sum()),
    }


def frozen_buy_mask(df):
    return (
        (df.side=="BUY_SIDE")
        & (pd.to_numeric(df.time_to_fill_min,errors="coerce")<=FROZEN_FILL)
        & (pd.to_numeric(df.directional_improvement_range_units,errors="coerce")<=FROZEN_IMPROVEMENT)
    )


def accepted_mask(df):
    return (df.side=="SELL_SIDE") | frozen_buy_mask(df)


def period_summary(df,period):
    rows=[]
    cohorts={
        "UNFILTERED_ALL":df,
        "ACCEPTED_ALL":df[accepted_mask(df)],
        "UNFILTERED_BUY":df[df.side=="BUY_SIDE"],
        "ACCEPTED_BUY":df[frozen_buy_mask(df)],
        "REJECTED_BUY":df[(df.side=="BUY_SIDE") & (~frozen_buy_mask(df))],
        "SELL_SIDE":df[df.side=="SELL_SIDE"],
    }
    for name,g in cohorts.items():
        rows.append({"period":period,"cohort":name,**m(g)})
    return pd.DataFrame(rows)


def main():
    # Explicitly exclude all post-cutoff market data.
    v3.wf1.v3.v1.base.END=FRESH_CUTOFF
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    hist,_,_=a1.build_score4_period(x5,END_2024,[2020,2021,2022,2023,2024],"HIST_2020_2024")
    y25,_,_=a1.build_score4_period(x5,END_2025,[2025],"RETRO_2025")
    y26,_,_=a1.build_score4_period(x5,FRESH_CUTOFF,[2026],"RETRO_2026_PRE")

    all_pre=pd.concat([hist,y25,y26],ignore_index=True)
    outcon=pd.concat([y25,y26],ignore_index=True)

    # 1. Exact pooled BUY stability.
    buy_all=all_pre[all_pre.side=="BUY_SIDE"].copy()
    buy_acc=all_pre[frozen_buy_mask(all_pre)].copy()
    mb=m(buy_all); ma=m(buy_acc)
    lift=ma["event_rate"]-mb["event_rate"]
    gate1={
        "accepted_buy_n_ge_8":ma["n"]>=8,
        "accepted_buy_event_rate_ge_50pct":bool(np.isfinite(ma["event_rate"]) and ma["event_rate"]>=.50),
        "event_rate_lift_ge_20pp":bool(np.isfinite(lift) and lift>=.20),
        "accepted_buy_mean_r_gt_0":bool(np.isfinite(ma["mean_r"]) and ma["mean_r"]>0),
        "accepted_buy_pf_ge_1_20":bool(np.isfinite(ma["pf_r"]) and ma["pf_r"]>=1.20),
    }
    pass1=all(gate1.values())

    # 2. Temporal consistency.
    ps=pd.concat([
        period_summary(hist,"HIST_2020_2024"),
        period_summary(y25,"RETRO_2025"),
        period_summary(y26,"RETRO_2026_PRE"),
        period_summary(all_pre,"POOLED_PRE_CUTOFF"),
    ],ignore_index=True)

    temp_rows=[]
    for period in ("HIST_2020_2024","RETRO_2025","RETRO_2026_PRE"):
        z=ps[ps.period==period].set_index("cohort")
        ab=z.loc["ACCEPTED_BUY"]; ub=z.loc["UNFILTERED_BUY"]
        evaluable=int(ab["n"])>=2
        event_support=bool(
            evaluable and np.isfinite(ab["event_rate"]) and np.isfinite(ub["event_rate"])
            and ab["event_rate"]>=ub["event_rate"]
        )
        mean_support=bool(
            evaluable and np.isfinite(ab["mean_r"]) and np.isfinite(ub["mean_r"])
            and ab["mean_r"]>=ub["mean_r"]
        )
        supportive=bool(event_support and mean_support) if evaluable else False
        temp_rows.append({
            "period":period,
            "accepted_buy_n":int(ab["n"]),
            "evaluable":evaluable,
            "event_support":event_support if evaluable else np.nan,
            "mean_r_support":mean_support if evaluable else np.nan,
            "supportive":supportive if evaluable else np.nan,
        })
    temporal=pd.DataFrame(temp_rows)
    evaluable=temporal[temporal.evaluable==True]
    pass2=bool(len(evaluable)>=2 and evaluable.supportive.astype(bool).all())

    # 3. Leave-one-accepted-trade-out.
    loo=[]
    for idx in buy_acc.index:
        g=buy_acc.drop(index=idx)
        mm=m(g)
        loo.append({
            "removed_candidate_id":buy_acc.loc[idx,"candidate_id"],
            "n":mm["n"],
            "event_rate":mm["event_rate"],
            "mean_r":mm["mean_r"],
            "pf_r":mm["pf_r"],
            "mean_positive":bool(np.isfinite(mm["mean_r"]) and mm["mean_r"]>0),
            "event_rate_ge_50pct":bool(np.isfinite(mm["event_rate"]) and mm["event_rate"]>=.50),
        })
    loo=pd.DataFrame(loo)
    loo_mean_pass=float(loo.mean_positive.mean()) if len(loo) else 0.0
    loo_event_pass=float(loo.event_rate_ge_50pct.mean()) if len(loo) else 0.0
    pass3=bool(loo_mean_pass>=.80 and loo_event_pass>=.80)

    # 4. Threshold neighborhood sensitivity (no selection).
    neigh=[]
    for ft in FILL_GRID:
        for it in IMPROVEMENT_GRID:
            mask=(
                (buy_all.side=="BUY_SIDE")
                & (pd.to_numeric(buy_all.time_to_fill_min,errors="coerce")<=ft)
                & (pd.to_numeric(buy_all.directional_improvement_range_units,errors="coerce")<=it)
            )
            g=buy_all[mask]
            mm=m(g)
            supportive=bool(
                mm["n"]>=5
                and np.isfinite(mm["event_rate"]) and mm["event_rate"]>mb["event_rate"]
                and np.isfinite(mm["mean_r"]) and mm["mean_r"]>0
            )
            neigh.append({
                "fill_threshold_min":ft,
                "improvement_threshold":it,
                **mm,
                "event_lift":mm["event_rate"]-mb["event_rate"] if mm["n"] else np.nan,
                "supportive":supportive,
                "is_frozen_rule":bool(abs(ft-FROZEN_FILL)<1e-12 and abs(it-FROZEN_IMPROVEMENT)<1e-10),
            })
    neigh=pd.DataFrame(neigh)
    supportive_n=int(neigh.supportive.sum())
    pass4=supportive_n>=6

    # 5. Out-of-construction retrospective check.
    buy_oos=outcon[outcon.side=="BUY_SIDE"].copy()
    buy_oos_acc=outcon[frozen_buy_mask(outcon)].copy()
    mo=m(buy_oos); moa=m(buy_oos_acc)
    oos_lift=moa["event_rate"]-mo["event_rate"]
    gate5={
        "accepted_buy_n_ge_3":moa["n"]>=3,
        "event_rate_lift_ge_10pp":bool(np.isfinite(oos_lift) and oos_lift>=.10),
        "accepted_mean_r_gt_unfiltered":bool(np.isfinite(moa["mean_r"]) and np.isfinite(mo["mean_r"]) and moa["mean_r"]>mo["mean_r"]),
        "accepted_mean_r_gt_0":bool(np.isfinite(moa["mean_r"]) and moa["mean_r"]>0),
    }
    pass5=all(gate5.values())

    # Exact random-subset exceedance diagnostic on out-of-construction BUY.
    k=moa["n"]
    exceed=0; total=0
    subset_rows=[]
    if k>0 and k<=len(buy_oos):
        for inds in itertools.combinations(range(len(buy_oos)),k):
            g=buy_oos.iloc[list(inds)]
            mm=m(g)
            both=bool(
                np.isfinite(mm["event_rate"]) and np.isfinite(moa["event_rate"])
                and np.isfinite(mm["mean_r"]) and np.isfinite(moa["mean_r"])
                and mm["event_rate"]>=moa["event_rate"]
                and mm["mean_r"]>=moa["mean_r"]
            )
            exceed+=int(both); total+=1
        exceed_frac=exceed/total if total else np.nan
    else:
        exceed_frac=np.nan

    # 6. Bootstrap stability on accepted BUY.
    rng=np.random.default_rng(BOOT_SEED)
    rs=buy_acc.terminal_r.astype(float).to_numpy()
    ev=buy_acc.event_label.astype(float).to_numpy()
    boot_mean=[]; boot_event=[]
    if len(rs):
        for _ in range(BOOT_N):
            ix=rng.integers(0,len(rs),size=len(rs))
            boot_mean.append(float(rs[ix].mean()))
            boot_event.append(float(ev[ix].mean()))
    boot_mean=np.asarray(boot_mean,dtype=float)
    boot_event=np.asarray(boot_event,dtype=float)
    p_mean_pos=float((boot_mean>0).mean()) if len(boot_mean) else np.nan
    p_event_ge_base=float((boot_event>=mb["event_rate"]).mean()) if len(boot_event) else np.nan
    pass6=bool(
        np.isfinite(p_mean_pos) and p_mean_pos>=.75
        and np.isfinite(p_event_ge_base) and p_event_ge_base>=.75
    )
    boot_summary=pd.DataFrame([{
        "bootstrap_n":BOOT_N,
        "seed":BOOT_SEED,
        "p_mean_r_gt_0":p_mean_pos,
        "p_event_rate_ge_unfiltered_buy":p_event_ge_base,
        "mean_r_p05":float(np.quantile(boot_mean,.05)),
        "mean_r_p50":float(np.quantile(boot_mean,.50)),
        "mean_r_p95":float(np.quantile(boot_mean,.95)),
        "event_rate_p05":float(np.quantile(boot_event,.05)),
        "event_rate_p50":float(np.quantile(boot_event,.50)),
        "event_rate_p95":float(np.quantile(boot_event,.95)),
    }])

    # 7. SELL-side auto-accept stability.
    sell_all=all_pre[all_pre.side=="SELL_SIDE"].copy()
    ms=m(sell_all)
    sell_period_positive=0
    sell_period_rows=[]
    for label,g in (("HIST_2020_2024",hist),("RETRO_2025",y25),("RETRO_2026_PRE",y26)):
        mm=m(g[g.side=="SELL_SIDE"])
        pos=bool(np.isfinite(mm["mean_r"]) and mm["mean_r"]>0)
        sell_period_positive+=int(pos)
        sell_period_rows.append({"period":label,**mm,"mean_r_positive":pos})
    sell_period=pd.DataFrame(sell_period_rows)
    gate7={
        "pooled_sell_mean_r_gt_0":bool(np.isfinite(ms["mean_r"]) and ms["mean_r"]>0),
        "pooled_sell_pf_ge_1_20":bool(np.isfinite(ms["pf_r"]) and ms["pf_r"]>=1.20),
        "positive_periods_ge_2_of_3":sell_period_positive>=2,
    }
    pass7=all(gate7.values())

    # 8. Full architecture uplift.
    all_m=m(all_pre)
    acc_all=all_pre[accepted_mask(all_pre)].copy()
    acc_m=m(acc_all)
    gate8={
        "accepted_event_rate_gt_unfiltered":bool(np.isfinite(acc_m["event_rate"]) and np.isfinite(all_m["event_rate"]) and acc_m["event_rate"]>all_m["event_rate"]),
        "accepted_mean_r_gt_unfiltered":bool(np.isfinite(acc_m["mean_r"]) and np.isfinite(all_m["mean_r"]) and acc_m["mean_r"]>all_m["mean_r"]),
        "accepted_pf_gt_unfiltered":bool(np.isfinite(acc_m["pf_r"]) and np.isfinite(all_m["pf_r"]) and acc_m["pf_r"]>all_m["pf_r"]),
        "accepted_cum_r_gt_0":bool(np.isfinite(acc_m["cum_r"]) and acc_m["cum_r"]>0),
    }
    pass8=all(gate8.values())

    checks={
        "exact_pooled_buy_stability":pass1,
        "temporal_consistency":pass2,
        "leave_one_out_stability":pass3,
        "threshold_neighborhood_sensitivity":pass4,
        "out_of_construction_retrospective":pass5,
        "bootstrap_stability":pass6,
        "sell_side_auto_accept_stability":pass7,
        "full_architecture_uplift":pass8,
    }
    verdict=(
        "SCORE4_DIRECTIONAL_CHARACTER_RETROSPECTIVELY_ROBUST"
        if all(checks.values())
        else "SCORE4_DIRECTIONAL_CHARACTER_RETROSPECTIVELY_FRAGILE"
    )

    # Persist.
    ps.to_csv(ROOT/f"{PFX}_PeriodSummary.csv",index=False)
    temporal.to_csv(ROOT/f"{PFX}_TemporalConsistency.csv",index=False)
    loo.to_csv(ROOT/f"{PFX}_LeaveOneOut.csv",index=False)
    neigh.to_csv(ROOT/f"{PFX}_NeighborhoodSensitivity.csv",index=False)
    boot_summary.to_csv(ROOT/f"{PFX}_Bootstrap.csv",index=False)
    sell_period.to_csv(ROOT/f"{PFX}_SellPeriodStability.csv",index=False)
    pd.DataFrame([{
        "scope":"POOLED_BUY",
        **{f"unfiltered_{k}":v for k,v in mb.items()},
        **{f"accepted_{k}":v for k,v in ma.items()},
        "event_rate_lift":lift,
        **{f"gate_{k}":v for k,v in gate1.items()},
    },{
        "scope":"OUT_OF_CONSTRUCTION_BUY_2025_2026PRE",
        **{f"unfiltered_{k}":v for k,v in mo.items()},
        **{f"accepted_{k}":v for k,v in moa.items()},
        "event_rate_lift":oos_lift,
        "random_subset_exceedance_fraction":exceed_frac,
        "random_subset_total_combinations":total,
        **{f"gate_{k}":v for k,v in gate5.items()},
    }]).to_csv(ROOT/f"{PFX}_BuyAudit.csv",index=False)

    pd.DataFrame([{
        "unfiltered_all_n":all_m["n"],
        "unfiltered_all_event_rate":all_m["event_rate"],
        "unfiltered_all_mean_r":all_m["mean_r"],
        "unfiltered_all_pf":all_m["pf_r"],
        "unfiltered_all_cum_r":all_m["cum_r"],
        "accepted_all_n":acc_m["n"],
        "accepted_all_event_rate":acc_m["event_rate"],
        "accepted_all_mean_r":acc_m["mean_r"],
        "accepted_all_pf":acc_m["pf_r"],
        "accepted_all_cum_r":acc_m["cum_r"],
        **{f"gate_{k}":v for k,v in gate8.items()},
    }]).to_csv(ROOT/f"{PFX}_ArchitectureUplift.csv",index=False)

    pd.DataFrame([{
        "coverage":coverage,
        "pooled_buy_n":mb["n"],
        "accepted_buy_n":ma["n"],
        "accepted_buy_event_rate":ma["event_rate"],
        "accepted_buy_mean_r":ma["mean_r"],
        "accepted_buy_pf":ma["pf_r"],
        "accepted_buy_event_lift":lift,
        "neighborhood_supportive_n":supportive_n,
        "loo_mean_positive_rate":loo_mean_pass,
        "loo_event_ge50_rate":loo_event_pass,
        "oos_random_subset_exceedance_fraction":exceed_frac,
        "bootstrap_p_mean_gt0":p_mean_pos,
        "bootstrap_p_event_ge_base":p_event_ge_base,
        "pooled_sell_mean_r":ms["mean_r"],
        "pooled_sell_pf":ms["pf_r"],
        **{f"check_{k}":v for k,v in checks.items()},
        "verdict":verdict,
    }]).to_csv(ROOT/f"{PFX}_Summary.csv",index=False)

    def fmt(v,d=3):
        if v is None or not np.isfinite(v):
            return "inf" if v is not None and np.isinf(v) else "n/a"
        return f"{v:.{d}f}"
    def pct(v):
        return "n/a" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"

    lines=[
        "# SOL Score-4 Directional Character Robustness V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Post-cutoff data: **EXCLUDED**.",
        f"- Frozen BUY rule: **time_to_fill_min <= {FROZEN_FILL:g} AND directional_improvement_range_units <= {FROZEN_IMPROVEMENT:.11f}**",
        "- SELL_SIDE remains auto-accepted.",
        "- No threshold was selected or changed in this audit.","",
        "## 1. Exact pooled BUY-side rule","",
        f"- Unfiltered BUY: N **{mb['n']}**, event rate **{pct(mb['event_rate'])}**, mean **{fmt(mb['mean_r'])}R**, PF **{fmt(mb['pf_r'])}**",
        f"- Accepted BUY: N **{ma['n']}**, event rate **{pct(ma['event_rate'])}**, mean **{fmt(ma['mean_r'])}R**, PF **{fmt(ma['pf_r'])}**",
        f"- Event-rate lift: **{lift*100:.2f} pp**",
        f"- Check: **{'PASS' if pass1 else 'FAIL'}**","",
        "## 2. Temporal consistency","",
        "| Period | Accepted BUY N | Evaluable | Event support | Mean-R support |",
        "|---|---:|---|---|---|",
    ]
    for _,r in temporal.iterrows():
        evs="—" if not bool(r.evaluable) else ("PASS" if bool(r.event_support) else "FAIL")
        mrs="—" if not bool(r.evaluable) else ("PASS" if bool(r.mean_r_support) else "FAIL")
        lines.append(f"| {r.period} | {int(r.accepted_buy_n)} | {'YES' if bool(r.evaluable) else 'NO'} | {evs} | {mrs} |")
    lines += [
        f"- Check: **{'PASS' if pass2 else 'FAIL'}**","",
        "## 3. Leave-one-out","",
        f"- Mean R remains positive: **{pct(loo_mean_pass)}** of removals",
        f"- Event rate remains >=50%: **{pct(loo_event_pass)}** of removals",
        f"- Check: **{'PASS' if pass3 else 'FAIL'}**","",
        "## 4. Threshold neighborhood","",
        f"- Supportive variants: **{supportive_n}/9**",
        f"- Check: **{'PASS' if pass4 else 'FAIL'}**","",
        "| Fill <= | Improvement <= | N | Event rate | Mean R | PF | Supportive |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _,r in neigh.iterrows():
        lines.append(
            f"| {r.fill_threshold_min:g} | {r.improvement_threshold:.6f} | {int(r.n)} | "
            f"{pct(r.event_rate)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} | {'YES' if bool(r.supportive) else 'NO'} |"
        )
    lines += [
        "",
        "## 5. 2025 + 2026 pre-cutoff out-of-construction check","",
        f"- Unfiltered BUY: N **{mo['n']}**, event rate **{pct(mo['event_rate'])}**, mean **{fmt(mo['mean_r'])}R**",
        f"- Accepted BUY: N **{moa['n']}**, event rate **{pct(moa['event_rate'])}**, mean **{fmt(moa['mean_r'])}R**, PF **{fmt(moa['pf_r'])}**",
        f"- Event-rate lift: **{oos_lift*100:.2f} pp**",
        f"- Random same-size subset exceedance fraction: **{pct(exceed_frac)}** ({exceed}/{total})",
        f"- Check: **{'PASS' if pass5 else 'FAIL'}**","",
        "## 6. Bootstrap stability","",
        f"- P(mean R > 0): **{pct(p_mean_pos)}**",
        f"- P(event rate >= pooled unfiltered BUY): **{pct(p_event_ge_base)}**",
        f"- Mean-R bootstrap 5/50/95%: **{fmt(float(np.quantile(boot_mean,.05)))}/{fmt(float(np.quantile(boot_mean,.50)))}/{fmt(float(np.quantile(boot_mean,.95)))}R**",
        f"- Event-rate bootstrap 5/50/95%: **{pct(float(np.quantile(boot_event,.05)))}/{pct(float(np.quantile(boot_event,.50)))}/{pct(float(np.quantile(boot_event,.95)))}**",
        f"- Check: **{'PASS' if pass6 else 'FAIL'}**","",
        "## 7. SELL-side auto-accept","",
        f"- Pooled SELL: N **{ms['n']}**, mean **{fmt(ms['mean_r'])}R**, PF **{fmt(ms['pf_r'])}**",
        f"- Positive periods: **{sell_period_positive}/3**",
        f"- Check: **{'PASS' if pass7 else 'FAIL'}**","",
        "## 8. Full architecture uplift","",
        f"- Unfiltered all: N **{all_m['n']}**, event rate **{pct(all_m['event_rate'])}**, mean **{fmt(all_m['mean_r'])}R**, PF **{fmt(all_m['pf_r'])}**, cum **{fmt(all_m['cum_r'])}R**",
        f"- Accepted all: N **{acc_m['n']}**, event rate **{pct(acc_m['event_rate'])}**, mean **{fmt(acc_m['mean_r'])}R**, PF **{fmt(acc_m['pf_r'])}**, cum **{fmt(acc_m['cum_r'])}R**",
        f"- Check: **{'PASS' if pass8 else 'FAIL'}**","",
        "## Primary check audit","",
    ]
    for k,v in checks.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
    lines += [
        "",
        f"**VERDICT: {verdict}**","",
        "This is retrospective robustness evidence only. It does not convert the frozen Score-4 directional character into independent validation.",
        "",
        "POST_CUTOFF_DATA=EXCLUDED"
    ]
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\nPOST_CUTOFF_DATA=EXCLUDED\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
