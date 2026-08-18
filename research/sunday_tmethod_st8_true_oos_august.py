#!/usr/bin/env python3
"""Sunday T-Method ST8 — frozen FastMR true-OOS replay for August 2026.

Research only; live BBC untouched.
Frozen rule from pre-OOS Sunday reset:
- Sunday 16:00 WIB SELL
- TP 2.5%, SL 1.4%, max hold 18h
- first favorable MFE hinge +1.00%
- hinge close at least 0.60% below EMA20
- within 120m after hinge, completed 5m close gives back to <= +0.60% short progress
- then arm +0.40% profit lock while original parent TP/SL remain
- no EMA7 runner recovery

True-OOS dates: 2026-08-02, 2026-08-09, 2026-08-16.
No August observation changes any rule.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import sun22_sunday16_frozen_router_true_oos as sun22
import sunday_tmethod_st0_st3_reset as st03
import sunday_tmethod_st8_fastmr_family as st8

OUT = Path(os.getenv("SUNT8OOS_OUT", "sunt8oos_out"))
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED = ["2026-08-02", "2026-08-09", "2026-08-16"]
HINGE = 0.010
D20 = 0.006
GIVEBACK = 0.006
LATENCY = 120
LOCK = 0.004


def metrics(a):
    a = np.asarray(a, float)
    if len(a) == 0:
        return {"n": 0, "wins": 0, "wr": None, "pnl": 0.0, "pf": None, "exp": None}
    wins = int((a > 0).sum())
    gp = float(a[a > 0].sum())
    gl = float(-a[a <= 0].sum())
    return {
        "n": int(len(a)),
        "wins": wins,
        "wr": float(wins / len(a)),
        "pnl": float(a.sum()),
        "pf": float(gp / gl) if gl > 0 else 999.0,
        "exp": float(a.mean()),
    }


def oos_entries(k):
    idx = k.index
    local = idx + pd.Timedelta(hours=7)
    m = (
        (local.dayofweek == 6)
        & (local.hour == 16)
        & (local.minute == 0)
        & (idx >= pd.Timestamp("2026-08-01", tz="UTC"))
        & (idx < pd.Timestamp("2026-08-18", tz="UTC"))
    )
    return list(idx[m])


def main():
    k, f = sun22.load_extended()
    es = oos_entries(k)
    dates = [t.strftime("%Y-%m-%d") for t in es]
    if dates != EXPECTED:
        raise RuntimeError(f"unexpected OOS Sunday entries {dates}")

    rows = []
    parent_pnls = []
    managed_pnls = []

    for t in es:
        tr = st03.sun17.simulate_parent(k, f, t)
        h = st03.first_hinge(k, tr, HINGE)
        arm = st8.arm(k, tr, h, D20, GIVEBACK, LATENCY)
        managed, acted, _ = st8.lock_outcome(k, f, tr, arm, False, GIVEBACK)

        h_d20 = None if h is None else st8.d20(k, h)
        parent_pnls.append(float(tr["pnl"]))
        managed_pnls.append(float(managed))
        rows.append({
            "date": t.strftime("%Y-%m-%d"),
            "entry_t": str(t),
            "entry": float(tr["entry"]),
            "parent_reason": tr["reason"],
            "parent_exit_t": str(tr["exit_t"]),
            "parent_pnl": float(tr["pnl"]),
            "parent_mfe_pct": 100 * float(tr["mfe"]),
            "parent_mae_pct": 100 * float(tr["mae"]),
            "reached_1pct_hinge": bool(h is not None),
            "hinge_t": None if h is None else str(h["bar_t"]),
            "hinge_ema20_overextension_pct": None if h_d20 is None else 100 * float(h_d20),
            "fastmr_armed": bool(arm is not None),
            "fastmr_decision_t": None if arm is None else str(arm["decision_t"]),
            "giveback_progress_pct": None if arm is None else 100 * float(arm["progress"]),
            "lock_action": bool(acted),
            "managed_pnl": float(managed),
            "delta_vs_parent": float(managed - tr["pnl"]),
        })

    df = pd.DataFrame(rows)
    pm = metrics(parent_pnls)
    mm = metrics(managed_pnls)
    summary = {
        "status": "COMPLETE_TRUE_OOS_FROZEN_SUNDAY_FASTMR",
        "research_cutoff": "2026-07-30 00:00:00+00:00",
        "dates": dates,
        "frozen_rule": {
            "entry": "Sunday 16:00 WIB SELL",
            "tp_pct": 2.5,
            "sl_pct": 1.4,
            "max_hold_h": 18,
            "hinge_mfe_pct": 1.0,
            "ema20_overextension_pct": 0.6,
            "giveback_progress_pct": 0.6,
            "giveback_latency_h": 2,
            "profit_lock_pct": 0.4,
            "runner_recovery": False,
        },
        "parent": pm,
        "fastmr": mm,
        "fastmr_delta_vs_parent": float(sum(managed_pnls) - sum(parent_pnls)),
        "fastmr_arms": int(df.fastmr_armed.sum()),
        "lock_actions": int(df.lock_action.sum()),
        "rows": df.to_dict(orient="records"),
        "guardrail": "Only three post-cutoff Sundays exist. Rule is replayed unchanged; N=3 cannot confirm or reject the edge and must not be used to retune the frozen settings.",
    }

    df.to_csv(OUT / "sunt8_true_oos_august_trades.csv", index=False)
    (OUT / "sunt8_true_oos_august_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def wr(m):
        return "-" if m["wr"] is None else f"{100*m['wr']:.1f}%"

    def pf(m):
        return "-" if m["pf"] is None else f"{m['pf']:.2f}"

    md = [
        "# Sunday T-Method ST8 — Frozen FastMR True-OOS August",
        "",
        "**Status: COMPLETE — TRUE-OOS OBSERVATION; RULE UNCHANGED; live BBC untouched.**",
        "",
        "## Frozen rule",
        "- Sunday 16:00 WIB SELL / TP2.5 / SL1.4 / max18h.",
        "- +1.00% favorable hinge.",
        "- Hinge EMA20 overextension >=0.60%.",
        "- Within 2h, close gives back to <=+0.60% short progress.",
        "- Arm +0.40% profit lock; no runner recovery.",
        "",
        "## True-OOS August 2026",
        f"- N **{mm['n']}**.",
        f"- Parent: {pm['wins']}/{pm['n']} wins, WR **{wr(pm)}**, PnL **${pm['pnl']:+.2f}**, PF **{pf(pm)}**.",
        f"- FastMR: {mm['wins']}/{mm['n']} wins, WR **{wr(mm)}**, PnL **${mm['pnl']:+.2f}**, PF **{pf(mm)}**.",
        f"- FastMR delta vs parent **${summary['fastmr_delta_vs_parent']:+.2f}**.",
        f"- FastMR armed **{summary['fastmr_arms']}** times; lock acted **{summary['lock_actions']}** times.",
        "",
        "| Date | Parent | MFE | EMA20 ext at +1% | FastMR? | Managed | Delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        d20txt = "-" if r["hinge_ema20_overextension_pct"] is None else f"{r['hinge_ema20_overextension_pct']:.3f}%"
        md.append(
            f"| {r['date']} | ${r['parent_pnl']:+.2f} | {r['parent_mfe_pct']:.3f}% | {d20txt} | {r['fastmr_armed']} | ${r['managed_pnl']:+.2f} | ${r['delta_vs_parent']:+.2f} |"
        )
    md += ["", "## Guardrail", summary["guardrail"]]
    (OUT / "SUNDAY_TMETHOD_ST8_TRUE_OOS_AUGUST_CHECKPOINT.md").write_text("\n".join(md) + "\n")

    print(json.dumps(summary, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
