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
PFX="SOL_SCORE4_DIRECTIONAL_ANATOMY_V2"

END_2024=pd.Timestamp("2025-01-01",tz="UTC")
END_2025=pd.Timestamp("2026-01-01",tz="UTC")
FRESH_CUTOFF=pd.Timestamp("2026-08-26 00:00:00",tz="UTC")
BAR5=pd.Timedelta(minutes=5)

FEATURES=(
    "source_to_opposite_structure_range_units",
    "approach_start_distance_to_level_range_units",
    "reclaim_directional_body_range_units",
    "reclaim_close_inside_range_units",
    "time_to_fill_min",
    "directional_improvement_range_units",
    "initial_risk_range_units",
    "structural_target_distance_range_units",
    "structural_reward_r",
)
QUANTILES=(.25,.50,.75)


def pf(s):
    x=pd.Series(s,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


def wilson_lower(successes:int,n:int,z:float=1.96)->float:
    if n<=0:
        return np.nan
    p=successes/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)/n)+(z*z/(4*n*n)))/den
    return center-half


def cohort_metrics(g:pd.DataFrame)->dict:
    if g is None or len(g)==0:
        return {
            "n":0,"event_n":0,"event_rate":np.nan,
            "mean_r":np.nan,"pf_r":np.nan,"cum_r":0.0
        }
    return {
        "n":len(g),
        "event_n":int(g.event_label.sum()),
        "event_rate":float(g.event_label.mean()),
        "mean_r":float(g.terminal_r.mean()),
        "pf_r":float(pf(g.terminal_r)),
        "cum_r":float(g.terminal_r.sum()),
    }


def atom_mask(df:pd.DataFrame,atom:dict)->pd.Series:
    x=pd.to_numeric(df[atom["feature"]],errors="coerce")
    if atom["op"]=="<=":
        return x<=atom["threshold"]
    return x>=atom["threshold"]


def rule_mask(df:pd.DataFrame,atoms:list[dict])->pd.Series:
    m=pd.Series(True,index=df.index)
    for atom in atoms:
        m &= atom_mask(df,atom)
    return m


def rule_text(atoms:list[dict])->str:
    return " AND ".join(
        f"{a['feature']} {a['op']} {a['threshold']:.12g}" for a in atoms
    )


def construct_buy_rule(hist:pd.DataFrame):
    buy=hist[hist.side=="BUY_SIDE"].copy().reset_index(drop=True)
    base=cohort_metrics(buy)

    atoms=[]
    quantile_rows=[]
    for f in FEATURES:
        s=pd.to_numeric(buy[f],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
        for q in QUANTILES:
            t=float(s.quantile(q))
            quantile_rows.append({"feature":f,"quantile":q,"threshold":t})
            atoms.append({"feature":f,"op":"<=","threshold":t,"quantile":q})
            atoms.append({"feature":f,"op":">=","threshold":t,"quantile":q})

    rules=[]
    # one-atom candidates
    for a in atoms:
        rules.append([a])
    # two atoms, distinct features only
    for a,b in itertools.combinations(atoms,2):
        if a["feature"]==b["feature"]:
            continue
        rules.append([a,b])

    candidate_rows=[]
    seen=set()
    for atoms_rule in rules:
        txt=rule_text(atoms_rule)
        if txt in seen:
            continue
        seen.add(txt)

        sel=buy[rule_mask(buy,atoms_rule)].copy()
        m=cohort_metrics(sel)
        lift=m["event_rate"]-base["event_rate"] if m["n"] else np.nan
        wlo=wilson_lower(m["event_n"],m["n"]) if m["n"] else np.nan
        eligible=bool(
            m["n"]>=5
            and np.isfinite(m["event_rate"]) and m["event_rate"]>=.60
            and np.isfinite(lift) and lift>=.20
            and np.isfinite(m["mean_r"]) and m["mean_r"]>0
            and np.isfinite(m["pf_r"]) and m["pf_r"]>1.0
        )
        candidate_rows.append({
            "rule_text":txt,
            "conditions":len(atoms_rule),
            "atoms_repr":repr(atoms_rule),
            "selected_n":m["n"],
            "event_n":m["event_n"],
            "event_rate":m["event_rate"],
            "lift_vs_buy_baseline":lift,
            "wilson_lower":wlo,
            "mean_r":m["mean_r"],
            "pf_r":m["pf_r"],
            "cum_r":m["cum_r"],
            "eligible":eligible,
        })

    table=pd.DataFrame(candidate_rows)
    elig=table[table.eligible==True].copy()
    winner=None
    if len(elig):
        elig=elig.sort_values(
            ["wilson_lower","event_rate","mean_r","selected_n","conditions","rule_text"],
            ascending=[False,False,False,False,True,True]
        )
        wr=elig.iloc[0]
        # Recover exact atoms deterministically from repr.
        winner_atoms=eval(wr.atoms_repr,{"__builtins__":{}},{})
        winner={
            **wr.to_dict(),
            "atoms":winner_atoms,
            "buy_baseline_n":base["n"],
            "buy_baseline_event_rate":base["event_rate"],
            "buy_baseline_mean_r":base["mean_r"],
            "buy_baseline_pf":base["pf_r"],
        }

    return buy,base,pd.DataFrame(quantile_rows),table,winner


def apply_architecture(df:pd.DataFrame,winner:dict)->pd.DataFrame:
    x=df.copy()
    buy=x.side=="BUY_SIDE"
    sell=x.side=="SELL_SIDE"
    buy_pass=pd.Series(False,index=x.index)
    if buy.any():
        buy_pass.loc[buy]=rule_mask(x.loc[buy],winner["atoms"])
    x["accepted"]=((sell)|(buy & buy_pass)).astype(int)
    x["directional_character"]=""
    x.loc[sell,"directional_character"]="SELL_SIDE_AUTO_ACCEPT"
    x.loc[buy & buy_pass,"directional_character"]="BUY_SIDE_RULE_ACCEPT"
    x.loc[buy & ~buy_pass,"directional_character"]="BUY_SIDE_RULE_REJECT"
    return x


def architecture_summary(df:pd.DataFrame,period:str)->pd.DataFrame:
    rows=[]
    cohorts={
        "UNFILTERED_ALL":df,
        "ACCEPTED_ALL":df[df.accepted==1],
        "REJECTED_BUY":df[(df.side=="BUY_SIDE")&(df.accepted==0)],
        "UNFILTERED_BUY":df[df.side=="BUY_SIDE"],
        "ACCEPTED_BUY":df[(df.side=="BUY_SIDE")&(df.accepted==1)],
        "SELL_SIDE":df[df.side=="SELL_SIDE"],
    }
    for name,g in cohorts.items():
        m=cohort_metrics(g)
        rows.append({"period":period,"cohort":name,**m})
    return pd.DataFrame(rows)


def retrospective_support(summary:pd.DataFrame,period:str):
    s=summary[summary.period==period].set_index("cohort")
    ab=s.loc["ACCEPTED_BUY"]
    ub=s.loc["UNFILTERED_BUY"]
    evaluable=int(ab["n"])>=2
    if not evaluable:
        return {
            "period":period,"evaluable":False,
            "accepted_buy_n":int(ab["n"]),
            "event_rate_support":np.nan,
            "mean_r_support":np.nan,
            "supportive":False,
        }
    er=bool(np.isfinite(ab["event_rate"]) and np.isfinite(ub["event_rate"]) and ab["event_rate"]>=ub["event_rate"])
    mr=bool(np.isfinite(ab["mean_r"]) and np.isfinite(ub["mean_r"]) and ab["mean_r"]>=ub["mean_r"])
    return {
        "period":period,"evaluable":True,
        "accepted_buy_n":int(ab["n"]),
        "event_rate_support":er,
        "mean_r_support":mr,
        "supportive":bool(er and mr),
    }


def fresh_audit(df:pd.DataFrame):
    s=architecture_summary(df,"FRESH_POST_CUTOFF")
    z=s.set_index("cohort")
    ua=z.loc["UNFILTERED_ALL"]; aa=z.loc["ACCEPTED_ALL"]
    ub=z.loc["UNFILTERED_BUY"]; ab=z.loc["ACCEPTED_BUY"]; sell=z.loc["SELL_SIDE"]

    sample={
        "total_n_ge_12":int(ua["n"])>=12,
        "accepted_n_ge_8":int(aa["n"])>=8,
        "buy_n_ge_5":int(ub["n"])>=5,
        "accepted_buy_n_ge_3":int(ab["n"])>=3,
        "sell_n_ge_3":int(sell["n"])>=3,
    }
    quality={
        "accepted_total_event_rate_gt_unfiltered":bool(
            np.isfinite(aa["event_rate"]) and np.isfinite(ua["event_rate"]) and aa["event_rate"]>ua["event_rate"]
        ),
        "accepted_total_mean_r_gt_unfiltered":bool(
            np.isfinite(aa["mean_r"]) and np.isfinite(ua["mean_r"]) and aa["mean_r"]>ua["mean_r"]
        ),
        "accepted_buy_event_rate_gt_unfiltered_buy":bool(
            np.isfinite(ab["event_rate"]) and np.isfinite(ub["event_rate"]) and ab["event_rate"]>ub["event_rate"]
        ),
        "accepted_buy_mean_r_gt_unfiltered_buy":bool(
            np.isfinite(ab["mean_r"]) and np.isfinite(ub["mean_r"]) and ab["mean_r"]>ub["mean_r"]
        ),
        "accepted_total_mean_r_gt_0":bool(np.isfinite(aa["mean_r"]) and aa["mean_r"]>0),
        "accepted_total_pf_ge_1_10":bool(np.isfinite(aa["pf_r"]) and aa["pf_r"]>=1.10),
    }
    return s,sample,quality


def fmt(v,d=3):
    if v is None or not np.isfinite(v):
        return "inf" if v is not None and np.isinf(v) else "n/a"
    return f"{v:.{d}f}"


def pct(v):
    return "n/a" if v is None or not np.isfinite(v) else f"{v*100:.2f}%"


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # STEP 1 — construct from historical 2020-2024 only.
    hist,_,_=a1.build_score4_period(x5,END_2024,[2020,2021,2022,2023,2024],"HIST_2020_2024")
    buy,base,qtable,candidates,winner=construct_buy_rule(hist)

    qtable.to_csv(ROOT/f"{PFX}_ConstructionQuantiles.csv",index=False)
    candidates.to_csv(ROOT/f"{PFX}_ConstructionCandidates.csv",index=False)

    if winner is None:
        verdict="NO_SCORE4_DIRECTIONAL_CHARACTER_CANDIDATE"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_HistoricalAcceptedTrades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Retrospective2026PreCutoffTrades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutTrades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_PeriodCohortSummary.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_RetrospectiveSupport.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutAudit.csv",index=False)
        summary=pd.DataFrame([{
            "coverage":coverage,
            "historical_buy_n":base["n"],
            "historical_buy_event_rate":base["event_rate"],
            "winner_rule":"",
            "verdict":verdict
        }])
        lines=[
            "# SOL Score-4 Directional Anatomy V2 — Result","",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            f"- Historical BUY_SIDE N: **{base['n']}**",
            f"- Historical BUY_SIDE event rate: **{pct(base['event_rate'])}**",
            "- No one/two-condition causal BUY_SIDE character passed all frozen historical eligibility gates.",
            "",
            f"**VERDICT: {verdict}**",
        ]
    else:
        # Freeze rule now. Only after this point touch later periods.
        hist_arch=apply_architecture(hist,winner)
        hist_arch.to_csv(ROOT/f"{PFX}_HistoricalAcceptedTrades.csv",index=False)
        hs=architecture_summary(hist_arch,"HIST_2020_2024")

        # STEP 2 — retrospective 2025.
        y25,_,_=a1.build_score4_period(x5,END_2025,[2025],"RETRO_2025")
        y25_arch=apply_architecture(y25,winner)
        y25_arch.to_csv(ROOT/f"{PFX}_Retrospective2025Trades.csv",index=False)
        s25=architecture_summary(y25_arch,"RETRO_2025")

        # STEP 3 — current available 2026, then strict pre/fresh split.
        latest=(x5.index.max()+BAR5).floor("h")
        if latest<=END_2025:
            latest=END_2025
        y26,_,_=a1.build_score4_period(x5,latest,[2026],"ALL_2026_AVAILABLE")
        et=pd.to_datetime(y26.entry_time,utc=True)
        pre=y26[et<FRESH_CUTOFF].copy()
        fresh=y26[et>=FRESH_CUTOFF].copy()

        pre_arch=apply_architecture(pre,winner)
        pre_arch.to_csv(ROOT/f"{PFX}_Retrospective2026PreCutoffTrades.csv",index=False)
        spre=architecture_summary(pre_arch,"RETRO_2026_PRE")

        support=pd.DataFrame([
            retrospective_support(s25,"RETRO_2025"),
            retrospective_support(spre,"RETRO_2026_PRE"),
        ])
        support.to_csv(ROOT/f"{PFX}_RetrospectiveSupport.csv",index=False)

        all_summary=pd.concat([hs,s25,spre],ignore_index=True)

        # Fresh is only evaluated after the candidate is fully frozen.
        fresh_arch=apply_architecture(fresh,winner) if len(fresh) else fresh.copy()
        if len(fresh_arch):
            fresh_arch.to_csv(ROOT/f"{PFX}_FreshHoldoutTrades.csv",index=False)
            sfresh,sample,quality=fresh_audit(fresh_arch)
        else:
            pd.DataFrame().to_csv(ROOT/f"{PFX}_FreshHoldoutTrades.csv",index=False)
            sfresh=pd.DataFrame([
                {"period":"FRESH_POST_CUTOFF","cohort":name,"n":0,"event_n":0,"event_rate":np.nan,"mean_r":np.nan,"pf_r":np.nan,"cum_r":0.0}
                for name in ("UNFILTERED_ALL","ACCEPTED_ALL","REJECTED_BUY","UNFILTERED_BUY","ACCEPTED_BUY","SELL_SIDE")
            ])
            sample={
                "total_n_ge_12":False,"accepted_n_ge_8":False,"buy_n_ge_5":False,
                "accepted_buy_n_ge_3":False,"sell_n_ge_3":False
            }
            quality={
                "accepted_total_event_rate_gt_unfiltered":False,
                "accepted_total_mean_r_gt_unfiltered":False,
                "accepted_buy_event_rate_gt_unfiltered_buy":False,
                "accepted_buy_mean_r_gt_unfiltered_buy":False,
                "accepted_total_mean_r_gt_0":False,
                "accepted_total_pf_ge_1_10":False,
            }

        all_summary=pd.concat([all_summary,sfresh],ignore_index=True)
        all_summary.to_csv(ROOT/f"{PFX}_PeriodCohortSummary.csv",index=False)

        fresh_audit_row={
            "fresh_cutoff":FRESH_CUTOFF,
            "latest_data":latest,
            **{f"sample_{k}":v for k,v in sample.items()},
            **{f"gate_{k}":v for k,v in quality.items()},
        }
        pd.DataFrame([fresh_audit_row]).to_csv(ROOT/f"{PFX}_FreshHoldoutAudit.csv",index=False)

        support_evaluable=support[support.evaluable==True]
        retrospective_supportive=bool(
            len(support_evaluable)>0 and support_evaluable.supportive.all()
        )
        retro_status=(
            "SCORE4_DIRECTIONAL_CHARACTER_FROZEN_RETROSPECTIVE_SUPPORT"
            if retrospective_supportive
            else "SCORE4_DIRECTIONAL_CHARACTER_FROZEN_RETROSPECTIVE_MIXED"
        )

        if not all(sample.values()):
            verdict="SCORE4_DIRECTIONAL_CHARACTER_FROZEN_AWAITING_FRESH_HOLDOUT"
        elif all(quality.values()):
            verdict="SCORE4_DIRECTIONAL_CHARACTER_VALIDATED_FRESH"
        else:
            verdict="SCORE4_DIRECTIONAL_CHARACTER_FAILED_FRESH_HOLDOUT"

        summary=pd.DataFrame([{
            "coverage":coverage,
            "winner_rule":winner["rule_text"],
            "historical_buy_n":winner["buy_baseline_n"],
            "historical_buy_baseline_event_rate":winner["buy_baseline_event_rate"],
            "historical_buy_selected_n":winner["selected_n"],
            "historical_buy_selected_event_rate":winner["event_rate"],
            "historical_buy_lift":winner["lift_vs_buy_baseline"],
            "historical_buy_selected_mean_r":winner["mean_r"],
            "historical_buy_selected_pf":winner["pf_r"],
            "retrospective_status":retro_status,
            "latest_data":latest,
            "fresh_n":int(sfresh.set_index("cohort").loc["UNFILTERED_ALL","n"]),
            "verdict":verdict,
        }])

        lines=[
            "# SOL Score-4 Directional Anatomy V2 — Result","",
            f"- 5m coverage: **{coverage*100:.6f}%**",
            "- Score-4 only; SELL_SIDE auto-accepted; BUY_SIDE governed by one frozen causal character.",
            "- Selection used **2020-2024 BUY_SIDE only**.",
            f"- Fresh cutoff: **{FRESH_CUTOFF}**.",
            "",
            "## Frozen BUY_SIDE directional character","",
            f"**{winner['rule_text']}**","",
            f"- Historical BUY baseline: N=**{winner['buy_baseline_n']}**, event rate **{pct(winner['buy_baseline_event_rate'])}**, mean R **{fmt(winner['buy_baseline_mean_r'])}**",
            f"- Selected BUY: N=**{winner['selected_n']}**, event rate **{pct(winner['event_rate'])}**, lift **{winner['lift_vs_buy_baseline']*100:.2f} pp**",
            f"- Selected BUY structural-completion mean R: **{fmt(winner['mean_r'])}R**, PF **{fmt(winner['pf_r'])}**",
            f"- Wilson 95% lower bound: **{pct(winner['wilson_lower'])}**",
            "",
            "## Period cohort audit","",
            "| Period | Cohort | N | Event rate | Mean R | PF |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for _,r in all_summary.iterrows():
            lines.append(
                f"| {r.period} | {r.cohort} | {int(r.n)} | {pct(r.event_rate)} | {fmt(r.mean_r)} | {fmt(r.pf_r)} |"
            )

        lines+=["","## Retrospective support",""]
        for _,r in support.iterrows():
            if not bool(r.evaluable):
                lines.append(f"- {r.period}: not evaluable (accepted BUY N={int(r.accepted_buy_n)})")
            else:
                lines.append(
                    f"- {r.period}: event-rate support={'PASS' if bool(r.event_rate_support) else 'FAIL'}, "
                    f"mean-R support={'PASS' if bool(r.mean_r_support) else 'FAIL'}"
                )
        lines+=["",f"Retrospective status: **{retro_status}**","",
                "## Fresh holdout audit",""]
        for k,v in sample.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — sample_{k}")
        for k,v in quality.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

        lines+=["",f"**VERDICT: {verdict}**","",
                "No post-cutoff threshold rescue or rule change is allowed."]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n",encoding="utf-8")
    print(text)


if __name__=="__main__":
    main()
