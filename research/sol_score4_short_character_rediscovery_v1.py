#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import math
import numpy as np
import pandas as pd

import sol_score4_failure_anatomy_v1 as a1
import sol_structural_liquidity_detector_v3 as v3
import sol_full_character_long_v1 as fc1

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_SCORE4_SHORT_CHARACTER_REDISCOVERY_V1"

END_2024=pd.Timestamp("2025-01-01",tz="UTC")
END_2025=pd.Timestamp("2026-01-01",tz="UTC")
CUTOFF=pd.Timestamp("2026-08-26 00:00:00",tz="UTC")

MOTIFS=(
    "RECLAIM_BREAKS_SWEEP_LOW",
    "RECLAIM_BREAKS_PRE_SWEEP_LOW",
    "RECLAIM_BREAKS_LOCAL_3BAR_LOW",
    "RECLAIM_CLOSE_BELOW_APPROACH_START",
    "RECLAIM_BODY_ENGULFS_SWEEP_BODY",
    "RECLAIM_RANGE_EXPANDS_VS_SWEEP",
    "RECLAIM_RANGE_EXPANDS_VS_PRE_SWEEP",
    "RECLAIM_INSIDE_DEPTH_EXCEEDS_SWEEP_OVERSHOOT",
    "SWEEP_SAME_BAR_REJECTION",
    "APPROACH_3BAR_HIGHER_CLOSES",
    "APPROACH_3BAR_STAIRCASE",
    "APPROACH_LAST_BAR_COMPRESSES_THEN_RECLAIM_EXPANDS",
    "PRE_FILL_5M_BEARISH_BREAK",
)


def pf(x):
    s=pd.Series(x,dtype=float).replace([np.inf,-np.inf],np.nan).dropna()
    pos=float(s[s>0].sum()); neg=float(-s[s<0].sum())
    if neg<=0:
        return math.inf if pos>0 else np.nan
    return pos/neg


def wilson_lower(k,n,z=1.96):
    if n<=0: return np.nan
    p=k/n
    den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half


def build_h1(x5):
    return fc1.build_h1(x5)


def add_motifs(anatomy:pd.DataFrame,h1:pd.DataFrame,x5:pd.DataFrame)->pd.DataFrame:
    x=anatomy.copy().reset_index(drop=True)
    hop=h1.open.astype(float).to_numpy()
    hhi=h1.high.astype(float).to_numpy()
    hlo=h1.low.astype(float).to_numpy()
    hcl=h1.close.astype(float).to_numpy()

    fop=x5.open.astype(float).to_numpy()
    flo=x5.low.astype(float).to_numpy()
    fcl=x5.close.astype(float).to_numpy()

    rows=[]
    for _,r in x.iterrows():
        # The persisted execution anatomy keeps sweep_time rather than sweep_i_h1.
        # Resolve the exact H1 index causally from the timestamp; reclaim_i_h1 is
        # retained by the upstream stack, with reclaim_time as a fallback.
        st=pd.Timestamp(r.sweep_time)
        s=int(h1.index.searchsorted(st,side="left"))
        if s>=len(h1) or h1.index[s] != st:
            raise RuntimeError(f"sweep_time not found in H1 index: {st}")

        if "reclaim_i_h1" in r.index and pd.notna(r.reclaim_i_h1) and int(r.reclaim_i_h1)>=0:
            q=int(r.reclaim_i_h1)
        else:
            rt=pd.Timestamp(r.reclaim_time)
            q=int(h1.index.searchsorted(rt,side="left"))
            if q>=len(h1) or h1.index[q] != rt:
                raise RuntimeError(f"reclaim_time not found in H1 index: {rt}")

        e=int(r.entry_i_5m)
        level=float(r.level)

        out=r.to_dict()
        vals={m:0 for m in MOTIFS}

        if s>=3 and q>=0 and q<len(h1):
            sweep_range=float(hhi[s]-hlo[s])
            reclaim_range=float(hhi[q]-hlo[q])
            pre_range=float(hhi[s-1]-hlo[s-1]) if s-1>=0 else np.nan
            pre2_range=float(hhi[s-2]-hlo[s-2]) if s-2>=0 else np.nan

            vals["RECLAIM_BREAKS_SWEEP_LOW"]=int(hcl[q] < hlo[s])
            vals["RECLAIM_BREAKS_PRE_SWEEP_LOW"]=int(hcl[q] < hlo[s-1])
            vals["RECLAIM_BREAKS_LOCAL_3BAR_LOW"]=int(hcl[q] < float(np.min(hlo[s-3:s])))
            vals["RECLAIM_CLOSE_BELOW_APPROACH_START"]=int(hcl[q] < hcl[s-3])

            reclaim_bear=bool(hcl[q] < hop[q])
            engulf=bool(
                reclaim_bear
                and hop[q] >= max(hop[s],hcl[s])
                and hcl[q] <= min(hop[s],hcl[s])
            )
            vals["RECLAIM_BODY_ENGULFS_SWEEP_BODY"]=int(engulf)

            vals["RECLAIM_RANGE_EXPANDS_VS_SWEEP"]=int(
                np.isfinite(reclaim_range) and np.isfinite(sweep_range) and reclaim_range>sweep_range
            )
            vals["RECLAIM_RANGE_EXPANDS_VS_PRE_SWEEP"]=int(
                np.isfinite(reclaim_range) and np.isfinite(pre_range) and reclaim_range>pre_range
            )

            inside=max(0.0,level-hcl[q])
            overshoot=max(0.0,hhi[s]-level)
            vals["RECLAIM_INSIDE_DEPTH_EXCEEDS_SWEEP_OVERSHOOT"]=int(inside>overshoot)

            vals["SWEEP_SAME_BAR_REJECTION"]=int(hcl[s] < level)

            pc=hcl[s-3:s]
            ph=hhi[s-3:s]
            pl=hlo[s-3:s]
            vals["APPROACH_3BAR_HIGHER_CLOSES"]=int(pc[0] < pc[1] < pc[2])
            vals["APPROACH_3BAR_STAIRCASE"]=int(
                ph[0] < ph[1] < ph[2] and pl[0] < pl[1] < pl[2]
            )
            vals["APPROACH_LAST_BAR_COMPRESSES_THEN_RECLAIM_EXPANDS"]=int(
                np.isfinite(pre_range) and np.isfinite(pre2_range)
                and pre_range<pre2_range and reclaim_range>pre_range
            )

        if e>=2 and e<=len(x5):
            p1=e-1; p2=e-2
            vals["PRE_FILL_5M_BEARISH_BREAK"]=int(
                fcl[p1] < fop[p1] and fcl[p1] < flo[p2]
            )

        out.update(vals)
        rows.append(out)

    return pd.DataFrame(rows)


def cohort(g):
    if len(g)==0:
        return {"n":0,"event_n":0,"event_rate":np.nan,"mean_r":np.nan,"pf":np.nan,"cum_r":0.0}
    return {
        "n":len(g),
        "event_n":int(g.event_label.sum()),
        "event_rate":float(g.event_label.mean()),
        "mean_r":float(g.terminal_r.mean()),
        "pf":float(pf(g.terminal_r)),
        "cum_r":float(g.terminal_r.sum()),
    }


def loo_stats(g):
    if len(g)<=1:
        return np.nan,np.nan
    mean_pass=[]
    event_pass=[]
    for i in range(len(g)):
        z=g.drop(g.index[i])
        mean_pass.append(float(z.terminal_r.mean())>0)
        event_pass.append(float(z.event_label.mean())>=.50)
    return float(np.mean(mean_pass)),float(np.mean(event_pass))


def rule_mask(df,rule):
    m=pd.Series(True,index=df.index)
    for motif in rule:
        m &= pd.to_numeric(df[motif],errors="coerce").fillna(0).astype(int).eq(1)
    return m


def construct(hist):
    buy=hist[hist.side=="BUY_SIDE"].copy().reset_index(drop=True)
    base=cohort(buy)

    rules=[(m,) for m in MOTIFS]
    rules += list(itertools.combinations(MOTIFS,2))

    rows=[]
    for rule in rules:
        sel=buy[rule_mask(buy,rule)].copy()
        cm=cohort(sel)
        lift=cm["event_rate"]-base["event_rate"] if cm["n"] else np.nan
        years=int(pd.to_datetime(sel.loc[sel.event_label==1,"entry_time"],utc=True).dt.year.nunique()) if len(sel) else 0
        loo_mean,loo_event=loo_stats(sel)
        eligible=bool(
            cm["n"]>=5
            and np.isfinite(cm["event_rate"]) and cm["event_rate"]>=.60
            and np.isfinite(lift) and lift>=.20
            and np.isfinite(cm["mean_r"]) and cm["mean_r"]>0
            and np.isfinite(cm["pf"]) and cm["pf"]>1.0
            and years>=2
            and np.isfinite(loo_mean) and loo_mean>=.80
            and np.isfinite(loo_event) and loo_event>=.80
        )
        rows.append({
            "rule_text":" AND ".join(rule),
            "rule_size":len(rule),
            "rule_repr":repr(rule),
            "selected_n":cm["n"],
            "event_n":cm["event_n"],
            "event_rate":cm["event_rate"],
            "lift":lift,
            "mean_r":cm["mean_r"],
            "pf_r":cm["pf"],
            "cum_r":cm["cum_r"],
            "event_years":years,
            "loo_mean_positive_rate":loo_mean,
            "loo_event_ge50_rate":loo_event,
            "wilson_lower":wilson_lower(cm["event_n"],cm["n"]) if cm["n"] else np.nan,
            "eligible":eligible,
        })

    table=pd.DataFrame(rows)
    elig=table[table.eligible==True].copy()
    winner=None
    if len(elig):
        elig=elig.sort_values(
            ["wilson_lower","loo_mean_positive_rate","event_rate","mean_r","selected_n","rule_size","rule_text"],
            ascending=[False,False,False,False,False,True,True]
        )
        w=elig.iloc[0]
        winner={**w.to_dict(),"rule":eval(w.rule_repr,{"__builtins__":{}},{})}
    return buy,base,table,winner


def support(period_df,winner,period):
    buy=period_df[period_df.side=="BUY_SIDE"].copy()
    base=cohort(buy)
    sel=buy[rule_mask(buy,winner["rule"])].copy()
    cm=cohort(sel)
    evaluable=cm["n"]>=2
    if evaluable:
        er=bool(np.isfinite(cm["event_rate"]) and np.isfinite(base["event_rate"]) and cm["event_rate"]>=base["event_rate"])
        mr=bool(np.isfinite(cm["mean_r"]) and np.isfinite(base["mean_r"]) and cm["mean_r"]>=base["mean_r"])
        pos=bool(np.isfinite(cm["mean_r"]) and cm["mean_r"]>0)
        supportive=er and mr and pos
    else:
        er=mr=pos=np.nan
        supportive=False
    return {
        "period":period,
        "baseline_n":base["n"],
        "baseline_event_rate":base["event_rate"],
        "baseline_mean_r":base["mean_r"],
        "selected_n":cm["n"],
        "selected_event_rate":cm["event_rate"],
        "selected_mean_r":cm["mean_r"],
        "selected_pf":cm["pf"],
        "evaluable":evaluable,
        "event_rate_support":er,
        "mean_r_support":mr,
        "positive_mean_support":pos,
        "supportive":supportive,
    },sel


def fmt(v,d=3):
    if v is None or not np.isfinite(v):
        return "inf" if v is not None and np.isinf(v) else "n/a"
    return f"{v:.{d}f}"


def pct(v):
    return "n/a" if v is None or not np.isfinite(v) else f"{100*v:.2f}%"


def main():
    # Explicitly close post-cutoff data for this rediscovery.
    base=v3.wf1.v3.v1.base
    base.END=CUTOFF

    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    h1=build_h1(x5)

    h0,_,_=a1.build_score4_period(x5,END_2024,[2020,2021,2022,2023,2024],"HIST_2020_2024")
    h25,_,_=a1.build_score4_period(x5,END_2025,[2025],"RETRO_2025")
    h26,_,_=a1.build_score4_period(x5,CUTOFF,[2026],"RETRO_2026_PRE")

    h0=add_motifs(h0,h1,x5)
    h25=add_motifs(h25,h1,x5)
    h26=add_motifs(h26,h1,x5)

    hist_buy,base_m,candidates,winner=construct(h0)
    candidates.to_csv(ROOT/f"{PFX}_ConstructionCandidates.csv",index=False)
    hist_buy.to_csv(ROOT/f"{PFX}_HistoricalBuyTrades.csv",index=False)

    lines=[
        "# SOL Score-4 SHORT Character Rediscovery V1 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Scope: Score-4 BUY_SIDE liquidity -> SHORT only.",
        "- One-shot structural rediscovery; post-cutoff data CLOSED.",
        "- No numeric threshold search, session/hour filter, indicator, MFE/MAE or future-path feature.","",
        "## Historical baseline 2020-2024","",
        f"- N: **{base_m['n']}**",
        f"- Structural-event rate: **{pct(base_m['event_rate'])}**",
        f"- Structural-completion mean R: **{fmt(base_m['mean_r'])}R**",
        f"- PF: **{fmt(base_m['pf'])}**",""
    ]

    if winner is None:
        verdict="DROP_SCORE4_SHORT_FROM_TRADABLE_UNIVERSE"
        status="NO_ROBUST_SCORE4_SHORT_STRUCTURAL_CHARACTER"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_RetrospectiveSupport.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_SelectedHistoricalTrades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Selected2025Trades.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Selected2026PreTrades.csv",index=False)
        summary={
            "coverage":coverage,
            "baseline_n":base_m["n"],
            "baseline_event_rate":base_m["event_rate"],
            "baseline_mean_r":base_m["mean_r"],
            "winner_rule":"",
            "status":status,
            "operational_decision":verdict,
        }
        lines += [
            "## Construction result","",
            "No permitted one- or two-motif structural rule passed every frozen construction and leave-one-out robustness gate.","",
            f"**STATUS: {status}**","",
            f"**OPERATIONAL DECISION: {verdict}**","",
            "Per the preregistered stop rule, do not create V2 or rescue the rule with numeric thresholds.",
            "",
            "POST_CUTOFF_DATA=CLOSED"
        ]
    else:
        selected_hist=hist_buy[rule_mask(hist_buy,winner["rule"])].copy()
        selected_hist.to_csv(ROOT/f"{PFX}_SelectedHistoricalTrades.csv",index=False)

        s25,sel25=support(h25,winner,"RETRO_2025")
        s26,sel26=support(h26,winner,"RETRO_2026_PRE")
        sel25.to_csv(ROOT/f"{PFX}_Selected2025Trades.csv",index=False)
        sel26.to_csv(ROOT/f"{PFX}_Selected2026PreTrades.csv",index=False)
        support_df=pd.DataFrame([s25,s26])
        support_df.to_csv(ROOT/f"{PFX}_RetrospectiveSupport.csv",index=False)

        ev=support_df[support_df.evaluable==True]
        all_support=bool(len(ev)>=1 and ev.supportive.all())

        if all_support:
            status="SCORE4_SHORT_STRUCTURAL_CHARACTER_FROZEN_RETROSPECTIVE_SUPPORT"
            verdict="KEEP_FROZEN_CANDIDATE_AWAIT_FRESH_VALIDATION"
        else:
            status="SCORE4_SHORT_STRUCTURAL_CHARACTER_FROZEN_RETROSPECTIVE_MIXED"
            verdict="DROP_SCORE4_SHORT_FROM_TRADABLE_UNIVERSE"

        summary={
            "coverage":coverage,
            "baseline_n":base_m["n"],
            "baseline_event_rate":base_m["event_rate"],
            "baseline_mean_r":base_m["mean_r"],
            "winner_rule":winner["rule_text"],
            "selected_n":winner["selected_n"],
            "selected_event_rate":winner["event_rate"],
            "selected_lift":winner["lift"],
            "selected_mean_r":winner["mean_r"],
            "selected_pf":winner["pf_r"],
            "selected_event_years":winner["event_years"],
            "loo_mean_positive_rate":winner["loo_mean_positive_rate"],
            "loo_event_ge50_rate":winner["loo_event_ge50_rate"],
            "status":status,
            "operational_decision":verdict,
        }

        lines += [
            "## Frozen structural character","",
            f"**{winner['rule_text']}**","",
            f"- Selected N: **{int(winner['selected_n'])}**",
            f"- Event rate: **{pct(winner['event_rate'])}**",
            f"- Lift vs baseline: **{winner['lift']*100:.2f} pp**",
            f"- Mean R: **{fmt(winner['mean_r'])}R**",
            f"- PF: **{fmt(winner['pf_r'])}**",
            f"- Event years represented: **{int(winner['event_years'])}**",
            f"- LOO mean>0 survival: **{pct(winner['loo_mean_positive_rate'])}**",
            f"- LOO event-rate>=50% survival: **{pct(winner['loo_event_ge50_rate'])}**",
            f"- Wilson 95% lower bound: **{pct(winner['wilson_lower'])}**","",
            "## Retrospective consistency","",
            "| Period | Baseline N | Baseline event | Baseline mean R | Selected N | Selected event | Selected mean R | PF | Evaluable | Support |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---|"
        ]
        for s in (s25,s26):
            lines.append(
                f"| {s['period']} | {s['baseline_n']} | {pct(s['baseline_event_rate'])} | {fmt(s['baseline_mean_r'])} | "
                f"{s['selected_n']} | {pct(s['selected_event_rate'])} | {fmt(s['selected_mean_r'])} | {fmt(s['selected_pf'])} | "
                f"{'YES' if s['evaluable'] else 'NO'} | "
                f"{'PASS' if s['evaluable'] and s['supportive'] else ('FAIL' if s['evaluable'] else 'N/A')} |"
            )

        lines += [
            "",
            f"**STATUS: {status}**","",
            f"**OPERATIONAL DECISION: {verdict}**","",
            "No threshold rescue or second rediscovery is permitted.",
            "",
            "POST_CUTOFF_DATA=CLOSED"
        ]

    pd.DataFrame([summary]).to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(
        f"{summary['status']}\n{summary['operational_decision']}\nPOST_CUTOFF_DATA=CLOSED\n",
        encoding="utf-8"
    )
    print(text)


if __name__=="__main__":
    main()
