#!/usr/bin/env python3
"""G3 — preregistered relative SELL lift gate.

Uses frozen G1 probabilities and their causal training-set SELL prior.
No new model, threshold sweep, sizing, or A5.11 retune.
Research only; live BBC untouched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.getenv("G3_OUT", "g3_out"))
OUT.mkdir(parents=True, exist_ok=True)
G1_POOL = Path(os.getenv("G1_POOL", "../BTC_Global_Regime_G1_Pooled_WalkForward_Predictions.csv"))
G1_TUE = Path(os.getenv("G1_TUE", "../BTC_Global_Regime_G1_Tuesday_Overlay.csv"))
G1_AUG = Path(os.getenv("G1_AUG", "../BTC_Global_Regime_G1_August_Tuesday.csv"))
G0_DATA = Path(os.getenv("G0_DATA", "../BTC_Global_Regime_G0_Pooled_Hourly_States.csv"))


def metrics(pnls: np.ndarray, traded: np.ndarray | None = None) -> dict:
    pnls = np.asarray(pnls, float)
    if traded is None:
        traded = np.ones(len(pnls), dtype=bool)
    else:
        traded = np.asarray(traded, bool)
    realized = np.where(traded, pnls, 0.0)
    x = pnls[traded]
    wins = int((x > 0).sum()) if len(x) else 0
    gp = float(x[x > 0].sum()) if len(x) else 0.0
    gl = float(-x[x <= 0].sum()) if len(x) else 0.0
    eq = np.cumsum(realized)
    if len(eq):
        peak = np.maximum.accumulate(np.r_[0.0, eq])
        dd = float(np.max(peak[1:] - eq))
    else:
        dd = 0.0
    return {
        "opportunities": int(len(pnls)),
        "trades": int(traded.sum()),
        "waits": int((~traded).sum()),
        "coverage": float(traded.mean()) if len(traded) else None,
        "wins": wins,
        "losses": int(len(x) - wins),
        "trade_wr": float(wins / len(x)) if len(x) else None,
        "pnl": float(realized.sum()),
        "exp_per_opportunity": float(realized.mean()) if len(realized) else None,
        "exp_per_trade": float(x.mean()) if len(x) else None,
        "pf": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else None),
        "max_dd": dd,
    }


def main() -> None:
    pool = pd.read_csv(G1_POOL)
    pool["decision_t_utc"] = pd.to_datetime(pool.decision_t_utc, utc=True)
    tue = pd.read_csv(G1_TUE)
    tue["decision_t_utc"] = pd.to_datetime(tue.decision_t_utc, utc=True)

    causal = pool[["decision_t_utc", "baseline_p_sell"]].drop_duplicates("decision_t_utc")
    td = tue.merge(causal, on="decision_t_utc", how="left", validate="one_to_one")
    if len(td) != 126:
        raise RuntimeError(f"expected 126 Tuesday rows, got {len(td)}")
    if td.baseline_p_sell.isna().any():
        raise RuntimeError("missing causal baseline_p_sell on Tuesday rows")

    td["sell_lift"] = td.p_sell / td.baseline_p_sell
    td["g1_trade"] = td.predicted.eq("SELL_COMPATIBLE")
    td["g2_trade"] = ~td.predicted.eq("BUY_COMPATIBLE")
    td["g3_trade"] = td.p_sell >= td.baseline_p_sell

    pnls = td.a511_pnl.to_numpy(float)
    base = metrics(pnls)
    g1 = metrics(pnls, td.g1_trade.to_numpy(bool))
    g2 = metrics(pnls, td.g2_trade.to_numpy(bool))
    g3 = metrics(pnls, td.g3_trade.to_numpy(bool))

    attr = {
        "lift_ge_1": metrics(pnls[td.g3_trade.to_numpy(bool)]),
        "lift_lt_1": metrics(pnls[(~td.g3_trade).to_numpy(bool)]),
    }

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = metrics(x.a511_pnl.to_numpy(float))
        xg = metrics(x.a511_pnl.to_numpy(float), x.g3_trade.to_numpy(bool))
        blocks.append({
            "block": b,
            "start": x.iloc[0].date_wib,
            "end": x.iloc[-1].date_wib,
            "baseline": xb,
            "g3": xg,
            "pnl_delta": float(xg["pnl"] - xb["pnl"]),
        })

    checks = {
        "coverage_ge_35pct": bool(g3["coverage"] >= 0.35),
        "exp_per_opportunity_improves": bool(g3["exp_per_opportunity"] > base["exp_per_opportunity"]),
        "total_pnl_ge_baseline": bool(g3["pnl"] >= base["pnl"]),
        "trade_wr_improves": bool(g3["trade_wr"] > base["trade_wr"]),
        "positive_delta_3_of_4_blocks": bool(sum(x["pnl_delta"] > 0 for x in blocks) >= 3),
    }

    g0 = pd.read_csv(G0_DATA)
    final_prior_sell = float((g0.label == "SELL_COMPATIBLE").mean())
    aug = pd.read_csv(G1_AUG)
    aug["baseline_p_sell"] = final_prior_sell
    aug["sell_lift"] = aug.p_sell / final_prior_sell
    aug["g3_trade"] = aug.p_sell >= final_prior_sell
    aug["g3_realized_pnl"] = np.where(aug.g3_trade, aug.a511_pnl, 0.0)
    aug_summary = {
        "baseline_p_sell": final_prior_sell,
        "n": int(len(aug)),
        "trades": int(aug.g3_trade.sum()),
        "waits": int((~aug.g3_trade).sum()),
        "always_trade_pnl": float(aug.a511_pnl.sum()),
        "g3_pnl": float(aug.g3_realized_pnl.sum()),
        "delta": float(aug.g3_realized_pnl.sum() - aug.a511_pnl.sum()),
    }

    summary = {
        "status": "G3_SHADOW_CANDIDATE_PASS" if all(checks.values()) else "G3_SHADOW_GATE_FAILED",
        "policy": "TRADE iff p_sell >= causal training baseline_p_sell (SELL_LIFT >= 1.0)",
        "baseline": base,
        "g1_hard_gate": g1,
        "g2_conflict_only": g2,
        "g3_relative_sell_lift": g3,
        "lift_attribution": attr,
        "blocks": blocks,
        "promotion_checks": checks,
        "pass": bool(all(checks.values())),
        "august_report_only": aug_summary,
        "guardrail": "Frozen G1 probabilities; threshold fixed at causal likelihood-ratio neutral boundary 1.0; live BBC untouched.",
    }

    td.to_csv(OUT / "g3_tuesday_rows.csv", index=False)
    aug.to_csv(OUT / "g3_august.csv", index=False)
    (OUT / "g3_summary.json").write_text(json.dumps(summary, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    lines = [
        "# BTC Global/Pooled Regime Engine — G3 Relative SELL Lift",
        "",
        f"**Status: {summary['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Frozen rule",
        "TRADE iff `pSELL >= causal training SELL prior` (SELL_LIFT >= 1.0).",
        "",
        "## Historical Tuesday comparison",
        "| Policy | Trades | Coverage | WR | PnL | Exp/oppty | PF | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Always A5.11 | {base['trades']} | {pct(base['coverage'])} | {pct(base['trade_wr'])} | ${base['pnl']:+.2f} | ${base['exp_per_opportunity']:+.4f} | {base['pf']:.3f} | ${base['max_dd']:.2f} |",
        f"| G1 hard gate | {g1['trades']} | {pct(g1['coverage'])} | {pct(g1['trade_wr'])} | ${g1['pnl']:+.2f} | ${g1['exp_per_opportunity']:+.4f} | {g1['pf']:.3f} | ${g1['max_dd']:.2f} |",
        f"| G2 conflict-only | {g2['trades']} | {pct(g2['coverage'])} | {pct(g2['trade_wr'])} | ${g2['pnl']:+.2f} | ${g2['exp_per_opportunity']:+.4f} | {g2['pf']:.3f} | ${g2['max_dd']:.2f} |",
        f"| G3 relative lift | {g3['trades']} | {pct(g3['coverage'])} | {pct(g3['trade_wr'])} | ${g3['pnl']:+.2f} | ${g3['exp_per_opportunity']:+.4f} | {g3['pf']:.3f} | ${g3['max_dd']:.2f} |",
        "",
        "## Outcome attribution by relative SELL lift",
        "| State | N | WR | PnL | Exp/trade | PF |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, label in [("lift_ge_1", "SELL_LIFT >= 1"), ("lift_lt_1", "SELL_LIFT < 1")]:
        m = attr[key]
        lines.append(f"| {label} | {m['trades']} | {pct(m['trade_wr'])} | ${m['pnl']:+.2f} | ${m['exp_per_trade']:+.4f} | {m['pf']:.3f} |")

    lines += ["", "## Promotion gate"]
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")

    lines += [
        "",
        "## Four chronological blocks",
        "| Block | Dates | Baseline PnL | G3 PnL | Delta |",
        "|---:|---|---:|---:|---:|",
    ]
    for b in blocks:
        lines.append(f"| {b['block']} | {b['start']} → {b['end']} | ${b['baseline']['pnl']:+.2f} | ${b['g3']['pnl']:+.2f} | ${b['pnl_delta']:+.2f} |")

    lines += [
        "",
        "## August 2026 — report only",
        f"Frozen historical SELL prior: **{100*final_prior_sell:.2f}%**.",
        "",
        "| Date WIB | pSELL | SELL lift | Decision | A5.11 PnL | G3 realized |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(f"| {r['date_wib']} | {100*r['p_sell']:.1f}% | {r['sell_lift']:.3f} | {'TRADE' if r['g3_trade'] else 'WAIT'} | ${r['a511_pnl']:+.2f} | ${r['g3_realized_pnl']:+.2f} |")
    lines += [
        "",
        f"August always trade: **${aug_summary['always_trade_pnl']:+.2f}**; G3: **${aug_summary['g3_pnl']:+.2f}**; delta **${aug_summary['delta']:+.2f}**.",
        "",
        f"**Final G3 verdict: {'PASS — eligible as shadow candidate only.' if summary['pass'] else 'FAIL — preserve result; no threshold tuning inside G3.'}**",
        "",
        "No live BBC changes were made.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G3_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
