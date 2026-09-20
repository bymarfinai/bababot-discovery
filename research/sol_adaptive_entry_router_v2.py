#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_adaptive_entry_v1_actionable as e1
import sol_structural_liquidity_detector_v3 as v3

ROOT=Path(__file__).resolve().parent.parent
PFX="SOL_ADAPTIVE_ENTRY_ROUTER_V2"

CONSTRUCTION_END=pd.Timestamp("2025-01-01",tz="UTC")
CONFIRM_END=pd.Timestamp("2026-01-01",tz="UTC")
BAR5=pd.Timedelta(minutes=5)


def rate(df):
    return float(df.event_label.mean()) if len(df) else np.nan


def med(s):
    s=pd.to_numeric(s,errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
    return float(s.median()) if len(s) else np.nan


def route_entries(pop:pd.DataFrame,h1:pd.DataFrame,x5:pd.DataFrame)->pd.DataFrame:
    parts=[]
    s3=pop[pop.anatomy_score==3].copy()
    s4=pop[pop.anatomy_score==4].copy()

    if len(s3):
        r3=e1.eval_variant(s3,h1,x5,"FIVE_MIN_REVERSAL_BREAK")
        r3["assigned_route"]="SCORE3_FIVE_MIN_REVERSAL_BREAK"
        parts.append(r3)

    if len(s4):
        r4=e1.eval_variant(s4,h1,x5,"GAP_25")
        r4["assigned_route"]="SCORE4_GAP25"
        parts.append(r4)

    if not parts:
        return pd.DataFrame()
    out=pd.concat(parts,ignore_index=True)
    out["router_variant"]="SCORE3_CONFIRM__SCORE4_GAP25"
    return out.sort_values(["signal_time","candidate_id"]).reset_index(drop=True)


def route_metrics(rows:pd.DataFrame):
    if rows.empty:
        return {
            "signal_n":0,"filled_n":0,"positive_n":0,
            "positive_filled_n":0,"positive_capture_rate":np.nan,
            "filled_event_rate":np.nan,"detector_baseline_rate":np.nan,
            "negative_fill_rate":np.nan,"median_time_to_fill_min":np.nan,
            "median_positive_adverse_excursion":np.nan,
        }

    filled=rows[rows.filled==1].copy()
    pos=rows[rows.event_label==1].copy()
    neg=rows[rows.event_label==0].copy()
    posfill=filled[filled.event_label==1].copy()

    out={
        "signal_n":len(rows),
        "filled_n":len(filled),
        "fill_rate":len(filled)/len(rows) if len(rows) else np.nan,
        "positive_n":len(pos),
        "positive_filled_n":len(posfill),
        "positive_capture_rate":len(posfill)/len(pos) if len(pos) else np.nan,
        "negative_n":len(neg),
        "negative_filled_n":int(((rows.event_label==0)&(rows.filled==1)).sum()),
        "negative_fill_rate":float((neg.filled==1).mean()) if len(neg) else np.nan,
        "filled_event_rate":float(filled.event_label.mean()) if len(filled) else np.nan,
        "detector_baseline_rate":float(rows.event_label.mean()),
        "median_time_to_fill_min":med(filled.time_to_fill_min),
        "median_positive_adverse_excursion":med(posfill.positive_adverse_excursion_range_units),
    }

    for side in ("BUY_SIDE","SELL_SIDE"):
        z=rows[(rows.side==side)&(rows.event_label==1)]
        out[f"{side.lower()}_positive_n"]=len(z)
        out[f"{side.lower()}_positive_filled_n"]=int((z.filled==1).sum())
        out[f"{side.lower()}_positive_capture"]=float((z.filled==1).mean()) if len(z) else np.nan

    for score in (3,4):
        z=rows[(rows.anatomy_score==score)&(rows.event_label==1)]
        zfill=z[z.filled==1]
        out[f"score{score}_signal_n"]=int((rows.anatomy_score==score).sum())
        out[f"score{score}_positive_n"]=len(z)
        out[f"score{score}_positive_filled_n"]=len(zfill)
        out[f"score{score}_positive_capture"]=len(zfill)/len(z) if len(z) else np.nan
        out[f"score{score}_filled_event_rate"]=float(
            rows[(rows.anatomy_score==score)&(rows.filled==1)].event_label.mean()
        ) if len(rows[(rows.anatomy_score==score)&(rows.filled==1)]) else np.nan

    score4_pos_fill=rows[
        (rows.anatomy_score==4)&(rows.event_label==1)&(rows.filled==1)
    ]
    out["score4_positive_median_improvement"]=med(
        score4_pos_fill.directional_improvement_range_units
    )
    out["score4_positive_filled_n_for_improvement"]=len(score4_pos_fill)

    return out


def confirmation_gates(m):
    gates={
        "signal_n_ge_50":int(m["signal_n"])>=50,
        "filled_n_ge_35":int(m["filled_n"])>=35,
        "positive_n_ge_25":int(m["positive_n"])>=25,
        "positive_capture_ge_75pct":bool(np.isfinite(m["positive_capture_rate"]) and m["positive_capture_rate"]>=.75),
        "filled_event_rate_ge_detector_baseline":bool(
            np.isfinite(m["filled_event_rate"]) and np.isfinite(m["detector_baseline_rate"])
            and m["filled_event_rate"]>=m["detector_baseline_rate"]
        ),
        "buy_positive_capture_ge_65pct":bool(
            np.isfinite(m["buy_side_positive_capture"]) and m["buy_side_positive_capture"]>=.65
        ),
        "sell_positive_capture_ge_65pct":bool(
            np.isfinite(m["sell_side_positive_capture"]) and m["sell_side_positive_capture"]>=.65
        ),
        "score3_positive_capture_ge_75pct":bool(
            np.isfinite(m["score3_positive_capture"]) and m["score3_positive_capture"]>=.75
        ),
        "score4_positive_capture_ge_50pct_if_n_ge5":bool(
            int(m["score4_positive_n"])<5 or
            (np.isfinite(m["score4_positive_capture"]) and m["score4_positive_capture"]>=.50)
        ),
        "score4_positive_improvement_gt_0":bool(
            np.isfinite(m["score4_positive_median_improvement"])
            and m["score4_positive_median_improvement"]>0
        ),
    }
    return gates


def holdout_gates(m):
    sample={
        "signal_n_ge_30":int(m["signal_n"])>=30,
        "filled_n_ge_20":int(m["filled_n"])>=20,
        "positive_n_ge_10":int(m["positive_n"])>=10,
    }

    quality={
        "positive_capture_ge_70pct":bool(
            np.isfinite(m["positive_capture_rate"]) and m["positive_capture_rate"]>=.70
        ),
        "filled_event_rate_not_below_baseline_minus_3pp":bool(
            np.isfinite(m["filled_event_rate"]) and np.isfinite(m["detector_baseline_rate"])
            and m["filled_event_rate"]>=m["detector_baseline_rate"]-.03
        ),
        "buy_positive_capture_ge_55pct_if_n_ge5":bool(
            int(m["buy_side_positive_n"])<5 or
            (np.isfinite(m["buy_side_positive_capture"]) and m["buy_side_positive_capture"]>=.55)
        ),
        "sell_positive_capture_ge_55pct_if_n_ge5":bool(
            int(m["sell_side_positive_n"])<5 or
            (np.isfinite(m["sell_side_positive_capture"]) and m["sell_side_positive_capture"]>=.55)
        ),
        "score3_positive_capture_ge_65pct_if_n_ge5":bool(
            int(m["score3_positive_n"])<5 or
            (np.isfinite(m["score3_positive_capture"]) and m["score3_positive_capture"]>=.65)
        ),
        "score4_positive_capture_ge_45pct_if_n_ge5":bool(
            int(m["score4_positive_n"])<5 or
            (np.isfinite(m["score4_positive_capture"]) and m["score4_positive_capture"]>=.45)
        ),
        "score4_positive_improvement_gt_0_if_5_filled":bool(
            int(m["score4_positive_filled_n_for_improvement"])<5 or
            (np.isfinite(m["score4_positive_median_improvement"]) and m["score4_positive_median_improvement"]>0)
        ),
    }
    return sample,quality


def render_metrics(title,m):
    def pct(v):
        return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"
    def num(v,d=4):
        return "n/a" if not np.isfinite(v) else f"{v:.{d}f}"

    return [
        f"## {title}","",
        f"- Signals: **{int(m['signal_n'])}**",
        f"- Filled: **{int(m['filled_n'])}** ({pct(m.get('fill_rate',np.nan))})",
        f"- Positive structural events: **{int(m['positive_n'])}**",
        f"- Positive-event capture: **{pct(m['positive_capture_rate'])}**",
        f"- Filled structural-event rate: **{pct(m['filled_event_rate'])}** vs detector baseline **{pct(m['detector_baseline_rate'])}**",
        f"- Negative-event fill rate: **{pct(m['negative_fill_rate'])}**",
        f"- BUY positive capture: **{pct(m['buy_side_positive_capture'])}**",
        f"- SELL positive capture: **{pct(m['sell_side_positive_capture'])}**",
        f"- Score-3 positive capture: **{pct(m['score3_positive_capture'])}**",
        f"- Score-4 positive capture: **{pct(m['score4_positive_capture'])}**",
        f"- Score-4 median positive improvement: **{num(m['score4_positive_median_improvement'])} H1 range units**",
        f"- Median time-to-fill: **{num(m['median_time_to_fill_min'],1)} min**",
        f"- Median positive adverse excursion: **{num(m['median_positive_adverse_excursion'])} H1 range units**",
        ""
    ]


def main():
    x5,coverage=v3.load5_with_retry("SOLUSDT")
    if coverage<.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    # Construction diagnostics: no validation decision is made from later years.
    pc,hc=e1.actionable_detector_population(
        x5,CONSTRUCTION_END,[2020,2021,2022,2023,2024]
    )
    xc=x5[x5.index<CONSTRUCTION_END]
    rc=route_entries(pc,hc,xc)
    mc=route_metrics(rc)

    rc.to_csv(ROOT/f"{PFX}_ConstructionEntries.csv",index=False)
    pd.DataFrame([mc]).to_csv(ROOT/f"{PFX}_ConstructionMetrics.csv",index=False)

    # Frozen 2025 confirmation.
    p25,h25=e1.actionable_detector_population(x5,CONFIRM_END,[2025])
    x25=x5[x5.index<CONFIRM_END]
    r25=route_entries(p25,h25,x25)
    m25=route_metrics(r25)
    gates25=confirmation_gates(m25)
    pass25=all(gates25.values())

    r25.to_csv(ROOT/f"{PFX}_Confirmation2025Entries.csv",index=False)
    pd.DataFrame([{**m25,**{f"gate_{k}":v for k,v in gates25.items()}}]).to_csv(
        ROOT/f"{PFX}_Confirmation2025Metrics.csv",index=False
    )

    lines=[
        "# SOL Adaptive Entry Router V2 — Result","",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Frozen router: **score 3 -> FIVE_MIN_REVERSAL_BREAK; score 4 -> GAP_25**.",
        "- Actionable detector remains SCORE>=3 with same-reclaim-bar resolved outcomes excluded.",
        "- No SL, TP, PnL, hour, indicator, or regime optimization.",""
    ]
    lines+=render_metrics("Construction 2020-2024",mc)
    lines+=render_metrics("Frozen 2025 confirmation",m25)
    lines+=["## 2025 gate audit",""]
    for k,v in gates25.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    if not pass25:
        verdict="ADAPTIVE_ENTRY_ROUTER_NOT_CONFIRMED_2025"
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Holdout2026Entries.csv",index=False)
        pd.DataFrame().to_csv(ROOT/f"{PFX}_Holdout2026Metrics.csv",index=False)

        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_signal_n":mc["signal_n"],
            "construction_positive_capture":mc["positive_capture_rate"],
            "construction_filled_event_rate":mc["filled_event_rate"],
            "construction_score4_positive_improvement":mc["score4_positive_median_improvement"],
            "confirmation_2025_signal_n":m25["signal_n"],
            "confirmation_2025_positive_capture":m25["positive_capture_rate"],
            "confirmation_2025_filled_event_rate":m25["filled_event_rate"],
            "confirmation_2025_score4_positive_improvement":m25["score4_positive_median_improvement"],
            "confirmation_2025_passed":False,
            "holdout_2026_opened":False,
            "verdict":verdict,
        }])
        lines+=["",f"**VERDICT: {verdict}**","",
                "- 2026 remained unopened because the frozen router failed confirmation.","",
                "2027_PLUS=CLOSED"]
    else:
        # Open 2026 only now.
        latest_complete=(x5.index.max()+BAR5).floor("h")
        if latest_complete<=CONFIRM_END:
            latest_complete=CONFIRM_END

        p26,h26=e1.actionable_detector_population(x5,latest_complete,[2026])
        x26=x5[x5.index<latest_complete]
        r26=route_entries(p26,h26,x26)
        m26=route_metrics(r26)
        sample26,quality26=holdout_gates(m26)

        if not all(sample26.values()):
            verdict="2026_ROUTER_HOLDOUT_INSUFFICIENT_SAMPLE"
        elif all(quality26.values()):
            verdict="VALIDATED_ADAPTIVE_ENTRY_ROUTER"
        else:
            verdict="ADAPTIVE_ENTRY_ROUTER_NOT_VALIDATED_AS_DEFINED"

        r26.to_csv(ROOT/f"{PFX}_Holdout2026Entries.csv",index=False)
        pd.DataFrame([{
            **m26,
            "data_end":latest_complete,
            **{f"sample_{k}":v for k,v in sample26.items()},
            **{f"gate_{k}":v for k,v in quality26.items()},
            "verdict":verdict,
        }]).to_csv(ROOT/f"{PFX}_Holdout2026Metrics.csv",index=False)

        summary=pd.DataFrame([{
            "coverage":coverage,
            "construction_signal_n":mc["signal_n"],
            "construction_positive_capture":mc["positive_capture_rate"],
            "construction_filled_event_rate":mc["filled_event_rate"],
            "construction_score4_positive_improvement":mc["score4_positive_median_improvement"],
            "confirmation_2025_signal_n":m25["signal_n"],
            "confirmation_2025_positive_capture":m25["positive_capture_rate"],
            "confirmation_2025_filled_event_rate":m25["filled_event_rate"],
            "confirmation_2025_score4_positive_improvement":m25["score4_positive_median_improvement"],
            "confirmation_2025_passed":True,
            "holdout_2026_opened":True,
            "holdout_2026_data_end":latest_complete,
            "holdout_2026_signal_n":m26["signal_n"],
            "holdout_2026_positive_capture":m26["positive_capture_rate"],
            "holdout_2026_filled_event_rate":m26["filled_event_rate"],
            "holdout_2026_score4_positive_improvement":m26["score4_positive_median_improvement"],
            "verdict":verdict,
        }])

        lines+=["","## 2025 verdict","","**PASS — frozen router confirmed. 2026 YTD was opened only after this pass.**",""]
        lines+=render_metrics("Untouched 2026 YTD",m26)
        lines+=["## 2026 sample audit",""]
        for k,v in sample26.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        lines+=["","## 2026 quality audit",""]
        for k,v in quality26.items():
            lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")
        lines+=["",f"**VERDICT: {verdict}**","",
                "This verdict concerns adaptive entry routing only. SL and TP remain separate.","",
                "2027_PLUS=CLOSED"]

    summary.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    text="\n".join(lines)+"\n"
    (ROOT/f"{PFX}_Result.md").write_text(text,encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(verdict+"\n2027_PLUS=CLOSED\n",encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
