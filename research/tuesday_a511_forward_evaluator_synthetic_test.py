#!/usr/bin/env python3
"""Synthetic gate tests for the preregistered Tuesday forward evaluator.

No market data is fetched or used. These are deterministic fabricated ledger rows
whose only purpose is to verify F0/F1/F2/F3, rejection, and integrity-hold logic.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import tuesday_a511_forward_evaluator as ev

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "BTC_Tuesday_A511_Forward_Evaluator_Synthetic_Test.json"
OUT_MD = ROOT / "BTC_Tuesday_A511_Forward_Evaluator_Synthetic_Test.md"
MODEL = ROOT / "BTC_Tuesday_Forward_Shadow_Model_State.json"


def make_row(i: int, pnl: float, model: dict) -> dict:
    date = pd.Timestamp("2026-08-25", tz="Asia/Jakarta") + pd.Timedelta(weeks=i)
    t = pd.Timestamp(f"{date.date()} 06:00:00", tz="Asia/Jakarta").tz_convert("UTC")
    prior = float(model["frozen_sell_prior"])
    p_buy, p_neutral, p_sell = 0.20, 0.20, 0.60
    row = {c: np.nan for c in ev.REQUIRED_COLUMNS}
    row.update({
        "date_wib": str(date.date()),
        "decision_t_utc": str(t),
        "evidence_class": "TRUE_FORWARD",
        "status": "SETTLED",
        "snapshot_recorded_at_utc": str(t + pd.Timedelta(minutes=1)),
        "snapshot_data_max_ts_utc": str(t - pd.Timedelta(minutes=5)),
        "model_fingerprint_sha256": model["model_fingerprint_sha256"],
        "entry_open": 100000.0 + i,
        "p_buy": p_buy,
        "p_neutral": p_neutral,
        "p_sell": p_sell,
        "g1_predicted": "SELL_COMPATIBLE",
        "frozen_sell_prior": prior,
        "point_sell_lift": p_sell / prior,
        "weekly_mean_p_sell_168h": 0.50,
        "weekly_sell_health": 0.50 - prior,
        "g7_diagnostic_weight": 1.0,
        "shadow_direction": "SELL",
        "shadow_policy": ev.EXPECTED_POLICY,
        "settled_at_utc": str(t + pd.Timedelta(hours=6, minutes=10)),
        "parent_reason": "SYNTHETIC",
        "parent_pnl": pnl,
        "parent_mfe_pct": 1.0,
        "parent_mae_pct": 0.2,
        "a52_act": False,
        "fastmr_act": False,
        "runner_recovery": False,
        "final_layer": "SYNTHETIC",
        "a511_pnl": pnl,
        "a511_win": bool(pnl > 0),
        "g0_label": "SELL_COMPATIBLE" if pnl > 0 else "BUY_COMPATIBLE",
        "g0_label_reason": "synthetic_fixture",
        "g0_first_hit_min": 60,
    })
    return row


def build(n: int, pnl: float, model: dict) -> pd.DataFrame:
    return pd.DataFrame([make_row(i, pnl, model) for i in range(n)], columns=ev.REQUIRED_COLUMNS)


def run_case(name: str, df: pd.DataFrame, model: dict, expected: str) -> dict:
    result = ev.evaluate(df, model)
    actual = result["status"]
    ok = actual == expected
    return {
        "case": name,
        "rows": int(len(df)),
        "expected": expected,
        "actual": actual,
        "pass": bool(ok),
        "integrity_pass": bool(result["integrity"]["pass"]),
    }


def main() -> None:
    model = json.loads(MODEL.read_text())
    cases = []
    cases.append(run_case("F0_empty", pd.DataFrame(columns=ev.REQUIRED_COLUMNS), model, "OBSERVE_ONLY"))
    cases.append(run_case("F1_12_supportive", build(12, 1.0, model), model, "EARLY_SUPPORTIVE"))
    cases.append(run_case("F2_26_strong_positive", build(26, 1.0, model), model, "CANDIDATE_REVIEW_ELIGIBLE"))
    cases.append(run_case("F3_52_strong_positive", build(52, 1.0, model), model, "LIVE_ENGINEERING_REVIEW_ELIGIBLE"))
    cases.append(run_case("F3_52_strong_negative", build(52, -1.0, model), model, "FORWARD_EDGE_REJECTED"))

    bad = build(12, 1.0, model)
    bad.loc[0, "model_fingerprint_sha256"] = "deliberately-invalid-fingerprint"
    cases.append(run_case("integrity_bad_fingerprint", bad, model, "DATA_INTEGRITY_HOLD"))

    dup = build(12, 1.0, model)
    dup.loc[1, "date_wib"] = dup.loc[0, "date_wib"]
    cases.append(run_case("integrity_duplicate_date", dup, model, "DATA_INTEGRITY_HOLD"))

    passed = all(x["pass"] for x in cases)
    payload = {
        "status": "PASS" if passed else "FAIL",
        "synthetic_only": True,
        "market_data_used": False,
        "cases": cases,
        "guardrail": "Synthetic fixtures only; no market-data inference and no change to frozen promotion gates.",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# Tuesday A5.11 Forward Evaluator — Synthetic Gate Test",
        "",
        f"**Status: {'PASS' if passed else 'FAIL'}**",
        "",
        "No market data is used. These fixtures only verify the preregistered decision-state implementation.",
        "",
        "| Case | Rows | Expected | Actual | Result |",
        "|---|---:|---|---|---|",
    ]
    for x in cases:
        lines.append(f"| {x['case']} | {x['rows']} | `{x['expected']}` | `{x['actual']}` | {'PASS' if x['pass'] else 'FAIL'} |")
    lines += [
        "",
        "A PASS does not provide trading evidence; it only proves the evaluator maps fabricated states to the frozen protocol decisions correctly.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(json.dumps(payload, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
