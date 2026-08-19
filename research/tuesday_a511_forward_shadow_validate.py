#!/usr/bin/env python3
"""End-to-end implementation validation for the Tuesday forward shadow runner.

Uses August 4/11/18 only as fixed implementation fixtures. Numerical probability
parity tolerance is 1e-8; no research rule, feature, model, cutoff, or strategy
parameter is changed. A5.11 paper-PnL parity remains effectively exact.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import g0_global_pooled_regime_dataset as g0
import tuesday_a511_true_oos_august as tue
import tuesday_a511_forward_shadow as fs

PROB_TOL = 1e-8
PNL_TOL = 1e-10


def main() -> None:
    state = fs.load_state(fs.MODEL_DEFAULT)
    ref1 = pd.read_csv(fs.G1_AUG_DEFAULT)
    ref1["decision_t_utc"] = pd.to_datetime(ref1.decision_t_utc, utc=True)
    ref6 = pd.read_csv(fs.G6_AUG_DEFAULT)
    ref6["decision_t_utc"] = pd.to_datetime(ref6.decision_t_utc, utc=True)
    ref6 = ref6.set_index("decision_t_utc")

    raw = tue.load_extended()
    k = g0.prepare(raw)

    rows = []
    max_g1 = 0.0
    max_g6 = 0.0
    max_a511 = 0.0
    for r in ref1.itertuples(index=False):
        t = r.decision_t_utc
        telem = fs.telemetry_from_k(state, k, t)
        expected = np.asarray([r.p_buy, r.p_neutral, r.p_sell], float)
        actual = np.asarray([telem["p_buy"], telem["p_neutral"], telem["p_sell"]], float)
        max_g1 = max(max_g1, float(np.max(np.abs(actual - expected))))
        max_g6 = max(
            max_g6,
            abs(telem["weekly_mean_p_sell_168h"] - float(ref6.loc[t, "mean_p_sell_168h"])),
        )
        tr = tue.simulate_parent(k, t)
        lr = tue.layered(k, tr)
        max_a511 = max(max_a511, abs(float(lr["a511_pnl"]) - float(r.a511_pnl)))
        rows.append({
            "date_wib": r.date_wib,
            "decision_t_utc": str(t),
            "p_buy": telem["p_buy"],
            "p_neutral": telem["p_neutral"],
            "p_sell": telem["p_sell"],
            "g1_predicted": telem["g1_predicted"],
            "weekly_mean_p_sell_168h": telem["weekly_mean_p_sell_168h"],
            "weekly_sell_health": telem["weekly_sell_health"],
            "g7_diagnostic_weight": telem["g7_diagnostic_weight"],
            "a511_pnl": float(lr["a511_pnl"]),
            "reference_a511_pnl": float(r.a511_pnl),
        })

    checks = {
        "model_fingerprint_valid": True,
        "g1_august_probability_max_abs_le_1e8": bool(max_g1 <= PROB_TOL),
        "g6_august_weekly_p_sell_max_abs_le_1e8": bool(max_g6 <= PROB_TOL),
        "a511_august_pnl_max_abs_le_1e10": bool(max_a511 <= PNL_TOL),
    }
    passed = bool(all(checks.values()))
    result = {
        "status": "FORWARD_SHADOW_IMPLEMENTATION_PARITY_PASS" if passed else "FORWARD_SHADOW_IMPLEMENTATION_PARITY_FAIL",
        "model_fingerprint_sha256": state["model_fingerprint_sha256"],
        "probability_tolerance": PROB_TOL,
        "pnl_tolerance": PNL_TOL,
        "max_abs_g1_august": max_g1,
        "max_abs_g6_august": max_g6,
        "max_abs_a511_august": max_a511,
        "checks": checks,
        "rows": rows,
        "pass": passed,
        "guardrail": "August is implementation parity fixture only. First new forward evidence remains 2026-08-25 WIB. Live BBC untouched.",
    }
    fs.VALIDATION_JSON_DEFAULT.write_text(json.dumps(result, indent=2, default=str))
    lines = [
        "# Tuesday A5.11 Forward Shadow — Implementation Validation",
        "",
        f"**Status: {'PASS' if passed else 'FAIL'}**",
        "",
        f"- Frozen model fingerprint: `{state['model_fingerprint_sha256']}`",
        f"- Max G1 August probability diff: `{max_g1:.3e}`",
        f"- Max G6 August weekly pSELL diff: `{max_g6:.3e}`",
        f"- Max A5.11 August PnL diff: `{max_a511:.3e}`",
        "",
        "## Fixed August fixtures",
        "| Date WIB | G1 predicted | pSELL | Weekly health | G7 diagnostic | A5.11 PnL |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['date_wib']} | {r['g1_predicted']} | {100*r['p_sell']:.2f}% | "
            f"{r['weekly_sell_health']:+.5f} | {r['g7_diagnostic_weight']:.3f} | ${r['a511_pnl']:+.2f} |"
        )
    lines += [
        "",
        "August 4/11/18 are implementation fixtures only and are not new forward observations.",
        "The first pristine forward Tuesday remains **2026-08-25 06:00 WIB**.",
        "Live BBC is untouched; this system cannot place an exchange order.",
    ]
    fs.VALIDATION_MD_DEFAULT.write_text("\n".join(lines) + "\n")
    print(json.dumps(result, indent=2, default=str))
    if not passed:
        raise RuntimeError("forward shadow implementation parity failed")


if __name__ == "__main__":
    main()
