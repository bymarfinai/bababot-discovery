#!/usr/bin/env python3
"""G5 — causal pooled-regime risk/conviction governor.

Frozen G1 probabilities only. Every Tuesday remains a trade; exposure can only
be reduced by WEIGHT=min(1,p_sell/baseline_p_sell).
Research only; live BBC untouched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.getenv("G5_OUT", "g5_out"))
OUT.mkdir(parents=True, exist_ok=True)
G1_POOL = Path(os.getenv("G1_POOL", "../BTC_Global_Regime_G1_Pooled_WalkForward_Predictions.csv"))
G1_TUE = Path(os.getenv("G1_TUE", "../BTC_Global_Regime_G1_Tuesday_Overlay.csv"))
G1_AUG = Path(os.getenv("G1_AUG", "../BTC_Global_Regime_G1_August_Tuesday.csv"))
G0_DATA = Path(os.getenv("G0_DATA", "../BTC_Global_Regime_G0_Pooled_Hourly_States.csv"))


def dd(pnls: np.ndarray) -> float:
    x = np.asarray(pnls, float)
    eq = np.cumsum(x)
    if not len(eq):
        return 0.0
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float(np.max(peak[1:] - eq))


def metrics(pnls: np.ndarray, weights: np.ndarray) -> dict:
    p = np.asarray(pnls, float)
    w = np.asarray(weights, float)
    realized = p * w
    exposure = float(w.sum())
    pnl = float(realized.sum())
    mdd = dd(realized)
    return {
        "n": int(len(p)),
        "wins": int((realized > 0).sum()),
        "losses": int((realized <= 0).sum()),
        "wr": float((realized > 0).mean()) if len(p) else None,
        "mean_weight": float(w.mean()) if len(w) else None,
        "median_weight": float(np.median(w)) if len(w) else None,
        "min_weight": float(w.min()) if len(w) else None,
        "max_weight": float(w.max()) if len(w) else None,
        "gross_exposure_units": exposure,
        "exposure_ratio": float(exposure / len(w)) if len(w) else None,
        "pnl": pnl,
        "pnl_per_exposure": float(pnl / exposure) if exposure > 0 else None,
        "max_dd": mdd,
        "pnl_over_dd": float(pnl / mdd) if mdd > 0 else (999.0 if pnl > 0 else None),
    }


def main() -> None:
    pool = pd.read_csv(G1_POOL)
    pool["decision_t_utc"] = pd.to_datetime(pool.decision_t_utc, utc=True)
    tue = pd.read_csv(G1_TUE)
    tue["decision_t_utc"] = pd.to_datetime(tue.decision_t_utc, utc=True)
    causal = pool[["decision_t_utc", "baseline_p_sell"]].drop_duplicates("decision_t_utc")
    td = tue.merge(causal, on="decision_t_utc", how="left", validate="one_to_one")
    if len(td) != 126 or td.baseline_p_sell.isna().any():
        raise RuntimeError(f"unexpected Tuesday causal rows n={len(td)} missing_prior={int(td.baseline_p_sell.isna().sum())}")

    td["sell_lift"] = td.p_sell / td.baseline_p_sell
    td["weight"] = np.minimum(1.0, td.sell_lift)
    td["weighted_pnl"] = td.a511_pnl * td.weight

    pnls = td.a511_pnl.to_numpy(float)
    base = metrics(pnls, np.ones(len(td), dtype=float))
    g5 = metrics(pnls, td.weight.to_numpy(float))

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = metrics(x.a511_pnl.to_numpy(float), np.ones(len(x), dtype=float))
        xg = metrics(x.a511_pnl.to_numpy(float), x.weight.to_numpy(float))
        eff_improved = bool(xg["pnl_per_exposure"] > xb["pnl_per_exposure"])
        blocks.append({
            "block": b,
            "start": x.iloc[0].date_wib,
            "end": x.iloc[-1].date_wib,
            "baseline": xb,
            "g5": xg,
            "efficiency_improved": eff_improved,
        })

    checks = {
        "mean_weight_lt_1": bool(g5["mean_weight"] < 1.0),
        "capital_efficiency_improves": bool(g5["pnl_per_exposure"] > base["pnl_per_exposure"]),
        "drawdown_improves": bool(g5["max_dd"] < base["max_dd"]),
        "pnl_over_dd_improves": bool(g5["pnl_over_dd"] > base["pnl_over_dd"]),
        "absolute_pnl_positive": bool(g5["pnl"] > 0),
        "efficiency_improves_3_of_4_blocks": bool(sum(x["efficiency_improved"] for x in blocks) >= 3),
    }

    g0 = pd.read_csv(G0_DATA)
    final_prior_sell = float((g0.label == "SELL_COMPATIBLE").mean())
    aug = pd.read_csv(G1_AUG)
    aug["baseline_p_sell"] = final_prior_sell
    aug["sell_lift"] = aug.p_sell / final_prior_sell
    aug["weight"] = np.minimum(1.0, aug.sell_lift)
    aug["weighted_pnl"] = aug.a511_pnl * aug.weight
    aug_summary = {
        "baseline_p_sell": final_prior_sell,
        "baseline_pnl": float(aug.a511_pnl.sum()),
        "g5_pnl": float(aug.weighted_pnl.sum()),
        "loss_reduction": float(aug.weighted_pnl.sum() - aug.a511_pnl.sum()),
        "mean_weight": float(aug.weight.mean()),
    }

    summary = {
        "status": "G5_RISK_GOVERNOR_SHADOW_PASS" if all(checks.values()) else "G5_RISK_GOVERNOR_GATE_FAILED",
        "policy": "weight=min(1,p_sell/causal_baseline_p_sell); all Tuesday opportunities remain trades",
        "baseline": base,
        "g5": g5,
        "blocks": blocks,
        "acceptance_checks": checks,
        "pass": bool(all(checks.values())),
        "august_report_only": aug_summary,
        "guardrail": "No new model or threshold; never increases baseline exposure; live BBC untouched.",
    }

    td.to_csv(OUT / "g5_tuesday_rows.csv", index=False)
    aug.to_csv(OUT / "g5_august.csv", index=False)
    (OUT / "g5_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    lines = [
        "# BTC Global/Pooled Regime Engine — G5 Risk Governor",
        "",
        f"**Status: {summary['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Frozen sizing rule",
        "`WEIGHT = min(1.0, pSELL / causal training SELL prior)`",
        "",
        "Every Tuesday remains a trade; G5 can only reduce size and can never exceed baseline exposure.",
        "",
        "## Historical Tuesday economics",
        "| Policy | N | Mean weight | Exposure | WR | PnL | PnL/exposure | Max DD | PnL/DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| Always 1.0x | {base['n']} | {base['mean_weight']:.3f} | {base['gross_exposure_units']:.2f} | {pct(base['wr'])} | ${base['pnl']:+.2f} | ${base['pnl_per_exposure']:+.4f} | ${base['max_dd']:.2f} | {base['pnl_over_dd']:.3f} |",
        f"| G5 governor | {g5['n']} | {g5['mean_weight']:.3f} | {g5['gross_exposure_units']:.2f} | {pct(g5['wr'])} | ${g5['pnl']:+.2f} | ${g5['pnl_per_exposure']:+.4f} | ${g5['max_dd']:.2f} | {g5['pnl_over_dd']:.3f} |",
        "",
        f"G5 weight range: **{g5['min_weight']:.3f} → {g5['max_weight']:.3f}**, median **{g5['median_weight']:.3f}**.",
        "",
        "## Acceptance gate",
    ]
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")

    lines += [
        "",
        "## Four chronological blocks",
        "| Block | Dates | Base exposure | G5 exposure | Base PnL/exposure | G5 PnL/exposure | Improved | Base DD | G5 DD |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for b in blocks:
        lines.append(
            f"| {b['block']} | {b['start']} → {b['end']} | {b['baseline']['gross_exposure_units']:.2f} | {b['g5']['gross_exposure_units']:.2f} | ${b['baseline']['pnl_per_exposure']:+.4f} | ${b['g5']['pnl_per_exposure']:+.4f} | {'YES' if b['efficiency_improved'] else 'NO'} | ${b['baseline']['max_dd']:.2f} | ${b['g5']['max_dd']:.2f} |"
        )

    lines += [
        "",
        "## August 2026 — report only",
        f"Frozen historical SELL prior: **{100*final_prior_sell:.2f}%**.",
        "",
        "| Date WIB | pSELL | SELL lift | Weight | A5.11 PnL | Weighted PnL |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(
            f"| {r['date_wib']} | {100*r['p_sell']:.1f}% | {r['sell_lift']:.3f} | {r['weight']:.3f} | ${r['a511_pnl']:+.2f} | ${r['weighted_pnl']:+.2f} |"
        )
    lines += [
        "",
        f"August baseline: **${aug_summary['baseline_pnl']:+.2f}**; G5: **${aug_summary['g5_pnl']:+.2f}**; loss reduction **${aug_summary['loss_reduction']:+.2f}**.",
        "",
        f"**Final G5 verdict: {'PASS — eligible as a risk-governor shadow candidate only.' if summary['pass'] else 'FAIL — preserve result; do not tune sizing inside G5.'}**",
        "",
        "No live BBC changes were made.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G5_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
