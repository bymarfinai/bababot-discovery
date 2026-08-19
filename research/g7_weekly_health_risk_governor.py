#!/usr/bin/env python3
"""G7 — preregistered weekly-health risk governor.

Uses frozen G6 168h slow-state rows. All eligible Tuesdays remain trades and
weight=min(1, mean_p_sell_168h/mean_causal_baseline_168h).
Research only; live BBC untouched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.getenv("G7_OUT", "g7_out"))
OUT.mkdir(parents=True, exist_ok=True)
G6_TUE = Path(os.getenv("G6_TUE", "../BTC_Global_Regime_G6_Tuesday_Rows.csv"))
G6_AUG = Path(os.getenv("G6_AUG", "../BTC_Global_Regime_G6_August.csv"))
G5_TUE = Path(os.getenv("G5_TUE", "../BTC_Global_Regime_G5_Tuesday_Rows.csv"))


def max_dd(x: np.ndarray) -> float:
    p = np.asarray(x, float)
    eq = np.cumsum(p)
    if not len(eq):
        return 0.0
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float(np.max(peak[1:] - eq))


def metrics(pnls: np.ndarray, weights: np.ndarray) -> dict:
    p = np.asarray(pnls, float)
    w = np.asarray(weights, float)
    r = p * w
    exposure = float(w.sum())
    pnl = float(r.sum())
    dd = max_dd(r)
    return {
        "n": int(len(p)),
        "wins": int((r > 0).sum()),
        "losses": int((r <= 0).sum()),
        "wr": float((r > 0).mean()) if len(r) else None,
        "mean_weight": float(w.mean()) if len(w) else None,
        "median_weight": float(np.median(w)) if len(w) else None,
        "min_weight": float(w.min()) if len(w) else None,
        "max_weight": float(w.max()) if len(w) else None,
        "gross_exposure_units": exposure,
        "exposure_ratio": float(exposure / len(w)) if len(w) else None,
        "pnl": pnl,
        "pnl_per_exposure": float(pnl / exposure) if exposure > 0 else None,
        "max_dd": dd,
        "pnl_over_dd": float(pnl / dd) if dd > 0 else (999.0 if pnl > 0 else None),
    }


def main() -> None:
    td = pd.read_csv(G6_TUE)
    td["decision_t_utc"] = pd.to_datetime(td.decision_t_utc, utc=True)
    td = td.sort_values("decision_t_utc").reset_index(drop=True)
    if len(td) < 120:
        raise RuntimeError(f"expected >=120 G6 eligible rows, got {len(td)}")
    if "mean_baseline_p_sell_168h" not in td.columns:
        raise RuntimeError("G6 rows missing mean_baseline_p_sell_168h")

    td["weekly_sell_lift"] = td.mean_p_sell_168h / td.mean_baseline_p_sell_168h
    td["g7_weight"] = np.minimum(1.0, td.weekly_sell_lift)
    td["g7_weighted_pnl"] = td.a511_pnl * td.g7_weight

    pnls = td.a511_pnl.to_numpy(float)
    base = metrics(pnls, np.ones(len(td), dtype=float))
    g7 = metrics(pnls, td.g7_weight.to_numpy(float))

    g5_context = None
    if G5_TUE.exists():
        g5 = pd.read_csv(G5_TUE)
        g5["decision_t_utc"] = pd.to_datetime(g5.decision_t_utc, utc=True)
        z = td[["decision_t_utc", "a511_pnl"]].merge(
            g5[["decision_t_utc", "weight"]], on="decision_t_utc", how="left", validate="one_to_one"
        )
        if not z.weight.isna().any():
            g5_context = metrics(z.a511_pnl.to_numpy(float), z.weight.to_numpy(float))

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = metrics(x.a511_pnl.to_numpy(float), np.ones(len(x), dtype=float))
        xg = metrics(x.a511_pnl.to_numpy(float), x.g7_weight.to_numpy(float))
        improved = bool(xg["pnl_per_exposure"] > xb["pnl_per_exposure"])
        blocks.append({
            "block": b, "start": x.iloc[0].date_wib, "end": x.iloc[-1].date_wib,
            "baseline": xb, "g7": xg, "efficiency_improved": improved,
        })

    checks = {
        "eligible_ge_120": bool(len(td) >= 120),
        "mean_weight_lt_1": bool(g7["mean_weight"] < 1.0),
        "capital_efficiency_improves": bool(g7["pnl_per_exposure"] > base["pnl_per_exposure"]),
        "max_dd_improves": bool(g7["max_dd"] < base["max_dd"]),
        "pnl_over_dd_improves": bool(g7["pnl_over_dd"] > base["pnl_over_dd"]),
        "absolute_pnl_positive": bool(g7["pnl"] > 0),
        "efficiency_improves_3_of_4_blocks": bool(sum(x["efficiency_improved"] for x in blocks) >= 3),
    }

    aug = pd.read_csv(G6_AUG)
    # G6 August uses one frozen final historical prior for every hourly state.
    if "baseline_p_sell" not in aug.columns:
        raise RuntimeError("G6 August rows missing baseline_p_sell")
    aug["weekly_sell_lift"] = aug.mean_p_sell_168h / aug.baseline_p_sell
    aug["g7_weight"] = np.minimum(1.0, aug.weekly_sell_lift)
    aug["g7_weighted_pnl"] = aug.a511_pnl * aug.g7_weight
    aug_summary = {
        "baseline_pnl": float(aug.a511_pnl.sum()),
        "g7_pnl": float(aug.g7_weighted_pnl.sum()),
        "loss_reduction": float(aug.g7_weighted_pnl.sum() - aug.a511_pnl.sum()),
        "mean_weight": float(aug.g7_weight.mean()),
    }

    summary = {
        "status": "G7_WEEKLY_RISK_GOVERNOR_SHADOW_PASS" if all(checks.values()) else "G7_WEEKLY_RISK_GOVERNOR_GATE_FAILED",
        "rule": "weight=min(1, mean_p_sell_168h / mean_causal_baseline_p_sell_168h)",
        "baseline": base,
        "g5_point_risk_context": g5_context,
        "g7": g7,
        "blocks": blocks,
        "acceptance_checks": checks,
        "pass": bool(all(checks.values())),
        "august_report_only": aug_summary,
        "guardrail": "Frozen G6 168h health; no floor/nonlinearity/extra leverage; live BBC untouched.",
    }

    td.to_csv(OUT / "g7_tuesday_rows.csv", index=False)
    aug.to_csv(OUT / "g7_august.csv", index=False)
    (OUT / "g7_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    lines = [
        "# BTC Global/Pooled Regime Engine — G7 Weekly-Health Risk Governor",
        "",
        f"**Status: {summary['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Frozen sizing rule",
        "`WEIGHT = min(1.0, mean_pSELL_168h / mean_causal_SELL_prior_168h)`",
        "",
        "Every eligible Tuesday remains a trade; G7 can only reduce exposure.",
        "",
        "## Historical Tuesday economics",
        "| Policy | N | Mean weight | Exposure | WR | PnL | PnL/exposure | Max DD | PnL/DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| Always 1.0x | {base['n']} | {base['mean_weight']:.3f} | {base['gross_exposure_units']:.2f} | {pct(base['wr'])} | ${base['pnl']:+.2f} | ${base['pnl_per_exposure']:+.4f} | ${base['max_dd']:.2f} | {base['pnl_over_dd']:.3f} |",
        f"| G7 weekly governor | {g7['n']} | {g7['mean_weight']:.3f} | {g7['gross_exposure_units']:.2f} | {pct(g7['wr'])} | ${g7['pnl']:+.2f} | ${g7['pnl_per_exposure']:+.4f} | ${g7['max_dd']:.2f} | {g7['pnl_over_dd']:.3f} |",
    ]
    if g5_context is not None:
        lines.append(f"| G5 point governor (same subset) | {g5_context['n']} | {g5_context['mean_weight']:.3f} | {g5_context['gross_exposure_units']:.2f} | {pct(g5_context['wr'])} | ${g5_context['pnl']:+.2f} | ${g5_context['pnl_per_exposure']:+.4f} | ${g5_context['max_dd']:.2f} | {g5_context['pnl_over_dd']:.3f} |")
    lines += [
        "",
        f"G7 weight range: **{g7['min_weight']:.3f} → {g7['max_weight']:.3f}**, median **{g7['median_weight']:.3f}**.",
        "",
        "## Acceptance gate",
    ]
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")
    lines += [
        "",
        "## Four chronological blocks",
        "| Block | Dates | Base exp | G7 exp | Base PnL/exp | G7 PnL/exp | Improved | Base DD | G7 DD |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for b in blocks:
        lines.append(f"| {b['block']} | {b['start']} → {b['end']} | {b['baseline']['gross_exposure_units']:.2f} | {b['g7']['gross_exposure_units']:.2f} | ${b['baseline']['pnl_per_exposure']:+.4f} | ${b['g7']['pnl_per_exposure']:+.4f} | {'YES' if b['efficiency_improved'] else 'NO'} | ${b['baseline']['max_dd']:.2f} | ${b['g7']['max_dd']:.2f} |")
    lines += [
        "",
        "## August 2026 — report only",
        "| Date WIB | Mean pSELL 168h | Weekly lift | Weight | A5.11 PnL | Weighted PnL |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(f"| {r['date_wib']} | {100*r['mean_p_sell_168h']:.2f}% | {r['weekly_sell_lift']:.3f} | {r['g7_weight']:.3f} | ${r['a511_pnl']:+.2f} | ${r['g7_weighted_pnl']:+.2f} |")
    lines += [
        "",
        f"August baseline: **${aug_summary['baseline_pnl']:+.2f}**; G7: **${aug_summary['g7_pnl']:+.2f}**; loss reduction **${aug_summary['loss_reduction']:+.2f}**.",
        "",
        f"**Final G7 verdict: {'PASS — eligible as weekly risk-governor shadow candidate only.' if summary['pass'] else 'FAIL — preserve result; no sizing retune inside G7.'}**",
        "",
        "No live BBC changes were made.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G7_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
