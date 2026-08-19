#!/usr/bin/env python3
"""G2 — preregistered conflict-only regime veto.

Uses frozen G1 Tuesday predictions. No model refit, threshold, sizing, or A5.11 retune.
Research only; live BBC untouched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(os.getenv("G2_OUT", "g2_out"))
OUT.mkdir(parents=True, exist_ok=True)
G1_TUE = Path(os.getenv("G1_TUE", "../BTC_Global_Regime_G1_Tuesday_Overlay.csv"))
G1_AUG = Path(os.getenv("G1_AUG", "../BTC_Global_Regime_G1_August_Tuesday.csv"))


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
    td = pd.read_csv(G1_TUE)
    td["decision_t_utc"] = pd.to_datetime(td.decision_t_utc, utc=True)
    td = td.sort_values("decision_t_utc").reset_index(drop=True)
    if len(td) != 126:
        raise RuntimeError(f"expected 126 G1 Tuesday opportunities, got {len(td)}")

    pnls = td.a511_pnl.to_numpy(float)
    always = np.ones(len(td), dtype=bool)
    g1 = td.predicted.eq("SELL_COMPATIBLE").to_numpy(bool)
    g2 = ~td.predicted.eq("BUY_COMPATIBLE").to_numpy(bool)

    base_m = metrics(pnls, always)
    g1_m = metrics(pnls, g1)
    g2_m = metrics(pnls, g2)

    class_attr = {}
    for c in ["SELL_COMPATIBLE", "NEUTRAL", "BUY_COMPATIBLE"]:
        m = td.predicted.eq(c).to_numpy(bool)
        class_attr[c] = metrics(pnls[m]) if m.any() else metrics(np.asarray([]))

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = metrics(x.a511_pnl.to_numpy(float))
        xg = metrics(
            x.a511_pnl.to_numpy(float),
            ~x.predicted.eq("BUY_COMPATIBLE").to_numpy(bool),
        )
        blocks.append({
            "block": b,
            "start": x.iloc[0].date_wib,
            "end": x.iloc[-1].date_wib,
            "baseline": xb,
            "g2": xg,
            "pnl_delta": float(xg["pnl"] - xb["pnl"]),
        })

    checks = {
        "coverage_ge_35pct": bool(g2_m["coverage"] >= 0.35),
        "exp_per_opportunity_improves": bool(g2_m["exp_per_opportunity"] > base_m["exp_per_opportunity"]),
        "total_pnl_ge_baseline": bool(g2_m["pnl"] >= base_m["pnl"]),
        "trade_wr_improves": bool(g2_m["trade_wr"] > base_m["trade_wr"]),
        "positive_delta_3_of_4_blocks": bool(sum(x["pnl_delta"] > 0 for x in blocks) >= 3),
    }

    aug = pd.read_csv(G1_AUG)
    aug["g2_trade"] = ~aug.predicted.eq("BUY_COMPATIBLE")
    aug["g2_realized_pnl"] = np.where(aug.g2_trade, aug.a511_pnl, 0.0)
    aug_summary = {
        "n": int(len(aug)),
        "trades": int(aug.g2_trade.sum()),
        "waits": int((~aug.g2_trade).sum()),
        "always_trade_pnl": float(aug.a511_pnl.sum()),
        "g2_pnl": float(aug.g2_realized_pnl.sum()),
        "delta": float(aug.g2_realized_pnl.sum() - aug.a511_pnl.sum()),
    }

    summary = {
        "status": "G2_SHADOW_CANDIDATE_PASS" if all(checks.values()) else "G2_SHADOW_GATE_FAILED",
        "policy": "TRADE on SELL_COMPATIBLE or NEUTRAL; WAIT only on BUY_COMPATIBLE",
        "baseline": base_m,
        "g1_hard_gate": g1_m,
        "g2_conflict_only": g2_m,
        "predicted_class_attribution": class_attr,
        "blocks": blocks,
        "promotion_checks": checks,
        "pass": bool(all(checks.values())),
        "august_report_only": aug_summary,
        "guardrail": "Frozen G1 classes only; no thresholds/sizing/model refit; live BBC untouched.",
    }

    (OUT / "g2_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    aug.to_csv(OUT / "g2_august.csv", index=False)

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    lines = [
        "# BTC Global/Pooled Regime Engine — G2 Conflict-Only Veto",
        "",
        f"**Status: {summary['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Frozen policy",
        "- SELL_COMPATIBLE => TRADE",
        "- NEUTRAL => TRADE",
        "- BUY_COMPATIBLE => WAIT",
        "",
        "## Historical Tuesday comparison",
        "| Policy | Trades | Coverage | WR | PnL | Exp/oppty | PF | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| Always A5.11 | {base_m['trades']} | {pct(base_m['coverage'])} | {pct(base_m['trade_wr'])} | ${base_m['pnl']:+.2f} | ${base_m['exp_per_opportunity']:+.4f} | {base_m['pf']:.3f} | ${base_m['max_dd']:.2f} |",
        f"| G1 hard gate | {g1_m['trades']} | {pct(g1_m['coverage'])} | {pct(g1_m['trade_wr'])} | ${g1_m['pnl']:+.2f} | ${g1_m['exp_per_opportunity']:+.4f} | {g1_m['pf']:.3f} | ${g1_m['max_dd']:.2f} |",
        f"| G2 conflict-only | {g2_m['trades']} | {pct(g2_m['coverage'])} | {pct(g2_m['trade_wr'])} | ${g2_m['pnl']:+.2f} | ${g2_m['exp_per_opportunity']:+.4f} | {g2_m['pf']:.3f} | ${g2_m['max_dd']:.2f} |",
        "",
        "## Outcome by predicted G1 class",
        "| Predicted class | N | WR | PnL | Exp/trade | PF |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for c in ["SELL_COMPATIBLE", "NEUTRAL", "BUY_COMPATIBLE"]:
        m = class_attr[c]
        lines.append(
            f"| {c} | {m['trades']} | {pct(m['trade_wr'])} | ${m['pnl']:+.2f} | ${m['exp_per_trade']:+.4f} | {m['pf'] if m['pf'] is not None else '-'} |"
        )

    lines += [
        "",
        "## Promotion gate",
    ]
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")

    lines += [
        "",
        "## Four chronological blocks",
        "| Block | Dates | Baseline PnL | G2 PnL | Delta |",
        "|---:|---|---:|---:|---:|",
    ]
    for b in blocks:
        lines.append(
            f"| {b['block']} | {b['start']} → {b['end']} | ${b['baseline']['pnl']:+.2f} | ${b['g2']['pnl']:+.2f} | ${b['pnl_delta']:+.2f} |"
        )

    lines += [
        "",
        "## August 2026 — report only",
        "| Date WIB | G1 predicted | G2 decision | A5.11 PnL | G2 realized |",
        "|---|---|---|---:|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(
            f"| {r['date_wib']} | {r['predicted']} | {'TRADE' if r['g2_trade'] else 'WAIT'} | ${r['a511_pnl']:+.2f} | ${r['g2_realized_pnl']:+.2f} |"
        )
    lines += [
        "",
        f"August always trade: **${aug_summary['always_trade_pnl']:+.2f}**; G2: **${aug_summary['g2_pnl']:+.2f}**; delta **${aug_summary['delta']:+.2f}**.",
        "",
        f"**Final G2 verdict: {'PASS — eligible as shadow candidate only.' if summary['pass'] else 'FAIL — keep result; do not tune this mapping inside G2.'}**",
        "",
        "No live BBC changes were made.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G2_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
