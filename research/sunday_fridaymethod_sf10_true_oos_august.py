#!/usr/bin/env python3
"""Sunday Friday-method SF10 — true-OOS August comparison.

Research only; live BBC untouched.

Compare two already-defined pre-OOS candidates WITHOUT changing any rule:
A) Frozen SF6-SF8 only.
B) Frozen SF6-SF8 + fixed FastMR overlay (SF9).

True-OOS dates: 2026-08-02, 2026-08-09, 2026-08-16.
Research cutoff: 2026-07-30 UTC.
No August observation is used to change a threshold, timing, direction, or exit rule.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import sun22_sunday16_frozen_router_true_oos as sun22
import sunday_fridaymethod_sf6_sf8_confirmed_failure as sf68
import sunday_fridaymethod_sf9_fastmr_overlay as sf9

OUT = Path(os.getenv("SUNFM10_OUT", "sunfm10_out"))
OUT.mkdir(parents=True, exist_ok=True)
EXPECTED = ["2026-08-02", "2026-08-09", "2026-08-16"]


def metrics(a):
    a = np.asarray(a, float)
    if len(a) == 0:
        return {"n": 0, "wins": 0, "losses": 0, "wr": None, "pnl": 0.0, "pf": None, "exp": None}
    wins = int((a > 0).sum())
    gp = float(a[a > 0].sum())
    gl = float(-a[a <= 0].sum())
    return {
        "n": int(len(a)),
        "wins": wins,
        "losses": int(len(a) - wins),
        "wr": float(wins / len(a)),
        "pnl": float(a.sum()),
        "pf": float(gp / gl) if gl > 0 else 999.0,
        "exp": float(a.mean()),
    }


def oos_entries(k):
    idx = k.index
    local = idx + pd.Timedelta(hours=7)
    mask = (
        (idx >= pd.Timestamp("2026-08-01", tz="UTC"))
        & (idx < pd.Timestamp("2026-08-18", tz="UTC"))
        & (local.dayofweek == 6)
        & (local.hour == 16)
        & (local.minute == 0)
    )
    return list(idx[mask])


def baseline_detail(k, f, tr):
    """Frozen SF6-SF8 outcome plus causal state details for reporting."""
    s6 = sf68.state(k, tr, 360)
    cand = sf68.candidate6(s6)
    s7 = None
    flow = None
    price_repair = False
    flow_repair = False
    base = sf9.frozen_baseline(k, f, tr)
    if cand:
        s7 = sf68.state(k, tr, 420)
        if s7 is not None:
            fl = sf68.flow67(k, tr)
            flow = None if not np.isfinite(fl) else float(fl)
            price_repair = bool(s7["last_close"] < s6["last_close"])
            flow_repair = bool(np.isfinite(fl) and fl < 0)
    return base, s6, s7, cand, flow, price_repair, flow_repair


def main():
    k, f = sun22.load_extended()
    es = oos_entries(k)
    dates = [t.strftime("%Y-%m-%d") for t in es]
    if dates != EXPECTED:
        raise RuntimeError(f"unexpected OOS Sunday entries {dates}")

    parent_pnls, frozen_pnls, combined_pnls = [], [], []
    rows = []

    for t in es:
        tr = sf68.sun17.simulate_parent(k, f, t)
        base, s6, s7, cand, flow, price_repair, flow_repair = baseline_detail(k, f, tr)
        combo = sf9.overlay_outcome(k, f, tr, base)

        parent_pnls.append(float(tr["pnl"]))
        frozen_pnls.append(float(base["pnl"]))
        combined_pnls.append(float(combo["pnl"]))

        rows.append({
            "date": t.strftime("%Y-%m-%d"),
            "entry_t": str(t),
            "entry": float(tr["entry"]),
            "parent_reason": tr["reason"],
            "parent_exit_t": str(tr["exit_t"]),
            "parent_pnl": float(tr["pnl"]),
            "parent_mfe_pct": 100 * float(tr["mfe"]),
            "parent_mae_pct": 100 * float(tr["mae"]),
            "sf68_candidate6": bool(cand),
            "cp6_progress_pct": None if s6 is None else 100 * float(s6["progress"]),
            "cp6_mfe_pct": None if s6 is None else 100 * float(s6["mfe_r"] * 0.014),
            "cp6_above20": None if s6 is None else bool(s6["above20"]),
            "cp6_green_frac": None if s6 is None else float(s6["green_frac"]),
            "sf68_price_repair7": bool(price_repair),
            "sf68_flow67": flow,
            "sf68_flow_repair7": bool(flow_repair),
            "sf68_layer": base["layer"],
            "sf68_pnl": float(base["pnl"]),
            "sf68_delta_vs_parent": float(base["pnl"] - tr["pnl"]),
            "fastmr_arm": bool(combo.get("fastmr_arm", False)),
            "fastmr_lock_exit": bool(combo.get("fastmr_lock_exit", False)),
            "fastmr_decision_t": None if combo.get("fastmr_decision_t") is None else str(combo.get("fastmr_decision_t")),
            "fastmr_d20_pct": None if combo.get("d20") is None else 100 * float(combo.get("d20")),
            "fastmr_giveback_progress_pct": None if combo.get("giveback_progress") is None else 100 * float(combo.get("giveback_progress")),
            "combined_layer": combo["layer"],
            "combined_pnl": float(combo["pnl"]),
            "combined_delta_vs_sf68": float(combo["pnl"] - base["pnl"]),
            "combined_delta_vs_parent": float(combo["pnl"] - tr["pnl"]),
        })

    df = pd.DataFrame(rows)
    pm = metrics(parent_pnls)
    fm = metrics(frozen_pnls)
    cm = metrics(combined_pnls)

    summary = {
        "status": "COMPLETE_TRUE_OOS_SF68_VS_SF9",
        "research_cutoff": "2026-07-30 00:00:00+00:00",
        "dates": dates,
        "candidate_A": "Frozen Sunday SF6-SF8",
        "candidate_B": "Frozen Sunday SF6-SF8 + fixed FastMR overlay",
        "parent": pm,
        "frozen_sf68": fm,
        "combined_sf68_fastmr": cm,
        "sf68_delta_vs_parent": float(sum(frozen_pnls) - sum(parent_pnls)),
        "combined_delta_vs_parent": float(sum(combined_pnls) - sum(parent_pnls)),
        "fastmr_delta_vs_sf68": float(sum(combined_pnls) - sum(frozen_pnls)),
        "sf68_candidate6_count": int(df.sf68_candidate6.sum()),
        "sf68_cut7_count": int((df.sf68_layer == "CUT7").sum()),
        "fastmr_arm_count": int(df.fastmr_arm.sum()),
        "fastmr_lock_exit_count": int(df.fastmr_lock_exit.sum()),
        "rows": df.to_dict(orient="records"),
        "guardrail": "Both candidates were defined before this replay. Only three post-cutoff Sundays exist; N=3 is an observation, not statistical confirmation, and must not be used to retune either candidate.",
    }

    df.to_csv(OUT / "sunfm10_true_oos_august_rows.csv", index=False)
    (OUT / "sunfm10_true_oos_august_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def wr(m):
        return "-" if m["wr"] is None else f"{100*m['wr']:.1f}%"

    def pf(m):
        return "-" if m["pf"] is None else f"{m['pf']:.2f}"

    md = [
        "# Sunday Friday-Method SF10 — True-OOS August Comparison",
        "",
        "**Status: COMPLETE — BOTH RULESETS FROZEN/UNCHANGED; live BBC untouched.**",
        "",
        "## Candidates",
        "- A: frozen SF6-SF8 only.",
        "- B: frozen SF6-SF8 + fixed FastMR overlay from SF9.",
        "- OOS dates: 2, 9, 16 August 2026.",
        "",
        "## Aggregate",
        f"- Parent: {pm['wins']}/{pm['n']} wins, WR **{wr(pm)}**, PnL **${pm['pnl']:+.2f}**, PF **{pf(pm)}**.",
        f"- Frozen SF6-SF8: {fm['wins']}/{fm['n']} wins, WR **{wr(fm)}**, PnL **${fm['pnl']:+.2f}**, PF **{pf(fm)}**, delta parent **${summary['sf68_delta_vs_parent']:+.2f}**.",
        f"- SF6-SF8 + FastMR: {cm['wins']}/{cm['n']} wins, WR **{wr(cm)}**, PnL **${cm['pnl']:+.2f}**, PF **{pf(cm)}**, delta parent **${summary['combined_delta_vs_parent']:+.2f}**.",
        f"- FastMR incremental vs frozen SF6-SF8 **${summary['fastmr_delta_vs_sf68']:+.2f}**.",
        f"- SF6-SF8 +6h candidates **{summary['sf68_candidate6_count']}**, CUT7 **{summary['sf68_cut7_count']}**.",
        f"- FastMR arms **{summary['fastmr_arm_count']}**, FastMR exits **{summary['fastmr_lock_exit_count']}**.",
        "",
        "| Date | Parent | SF6-SF8 state | SF6-SF8 | FastMR | Combined |",
        "|---|---:|---|---:|---|---:|",
    ]
    for r in rows:
        fmstate = "ARM" if r["fastmr_arm"] else "-"
        md.append(
            f"| {r['date']} | ${r['parent_pnl']:+.2f} | {r['sf68_layer']} | ${r['sf68_pnl']:+.2f} | {fmstate} | ${r['combined_pnl']:+.2f} |"
        )
    md += ["", "## Guardrail", summary["guardrail"]]
    (OUT / "SUNDAY_FRIDAY_METHOD_SF10_TRUE_OOS_AUGUST.md").write_text("\n".join(md) + "\n")

    print(json.dumps(summary, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
