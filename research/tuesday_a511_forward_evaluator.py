#!/usr/bin/env python3
"""Evaluate the immutable Tuesday A5.11 true-forward ledger.

This evaluator implements BTC_Tuesday_A511_Forward_Promotion_Protocol.md.
It never fetches market data, never retrains a model, never changes the ledger,
and cannot place an exchange order.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEDGER_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Shadow_Ledger.csv"
MODEL_DEFAULT = ROOT / "BTC_Tuesday_Forward_Shadow_Model_State.json"
OUT_JSON_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Evaluation.json"
OUT_MD_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Evaluation.md"

TRUE_FORWARD_START = pd.Timestamp("2026-08-25 06:00:00", tz="Asia/Jakarta").tz_convert("UTC")
BOOTSTRAP_SEED = 20260819
BOOTSTRAP_N = 20_000
PF_GATE = 1.20
MAX_DD_GATE = 26.64
EXPECTED_POLICY = "FROZEN_A5.11_ALWAYS_PAPER_SELL__REGIME_TELEMETRY_ONLY"
EXPECTED_DIRECTION = "SELL"
EXPECTED_CLASSES = {"BUY_COMPATIBLE", "NEUTRAL", "SELL_COMPATIBLE"}
EXPECTED_STATUSES = {"PENDING_SETTLEMENT", "SETTLED"}

REQUIRED_COLUMNS = [
    "date_wib", "decision_t_utc", "evidence_class", "status",
    "snapshot_recorded_at_utc", "snapshot_data_max_ts_utc",
    "model_fingerprint_sha256", "entry_open",
    "p_buy", "p_neutral", "p_sell", "g1_predicted",
    "frozen_sell_prior", "point_sell_lift",
    "weekly_mean_p_sell_168h", "weekly_sell_health", "g7_diagnostic_weight",
    "shadow_direction", "shadow_policy",
    "settled_at_utc", "parent_reason", "parent_pnl", "parent_mfe_pct", "parent_mae_pct",
    "a52_act", "fastmr_act", "runner_recovery", "final_layer", "a511_pnl", "a511_win",
    "g0_label", "g0_label_reason", "g0_first_hit_min",
]


def as_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def as_bool(v) -> bool | None:
    if pd.isna(v):
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    x = str(v).strip().lower()
    if x in {"true", "1", "yes"}:
        return True
    if x in {"false", "0", "no"}:
        return False
    return None


def load_inputs(ledger_path: Path, model_path: Path) -> tuple[pd.DataFrame, dict]:
    model = json.loads(model_path.read_text())
    if ledger_path.exists():
        df = pd.read_csv(ledger_path)
    else:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    return df, model


def integrity_checks(df: pd.DataFrame, model: dict) -> dict:
    violations: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        violations.append("missing_columns:" + ",".join(missing))
        return {"pass": False, "violations": violations}

    fp = str(model.get("model_fingerprint_sha256", ""))
    if not fp:
        violations.append("frozen_model_fingerprint_missing")

    if len(df) == 0:
        return {"pass": len(violations) == 0, "violations": violations}

    dates = df.date_wib.astype(str)
    if dates.duplicated().any():
        bad = sorted(dates[dates.duplicated(keep=False)].unique().tolist())
        violations.append("duplicate_tuesday_dates:" + ",".join(bad))

    bad_status = sorted(set(df.status.dropna().astype(str)) - EXPECTED_STATUSES)
    if bad_status:
        violations.append("unexpected_status:" + ",".join(bad_status))

    for i, r in df.iterrows():
        tag = str(r.get("date_wib", i))
        try:
            t = pd.to_datetime(r.decision_t_utc, utc=True)
        except Exception:
            violations.append(f"{tag}:invalid_decision_timestamp")
            continue

        if str(r.evidence_class) == "TRUE_FORWARD" and t < TRUE_FORWARD_START:
            violations.append(f"{tag}:true_forward_before_frozen_start")
        if str(r.evidence_class) not in {"TRUE_FORWARD", "PARITY_FIXTURE"}:
            violations.append(f"{tag}:unexpected_evidence_class")
        if str(r.model_fingerprint_sha256) != fp:
            violations.append(f"{tag}:model_fingerprint_mismatch")
        if str(r.shadow_direction) != EXPECTED_DIRECTION:
            violations.append(f"{tag}:unexpected_shadow_direction")
        if str(r.shadow_policy) != EXPECTED_POLICY:
            violations.append(f"{tag}:unexpected_shadow_policy")

        try:
            snap = pd.to_datetime(r.snapshot_recorded_at_utc, utc=True)
            data_max = pd.to_datetime(r.snapshot_data_max_ts_utc, utc=True)
            if snap < t:
                violations.append(f"{tag}:snapshot_recorded_before_decision")
            if data_max != t - pd.Timedelta(minutes=5):
                violations.append(f"{tag}:snapshot_data_cap_not_t_minus_5m")
        except Exception:
            violations.append(f"{tag}:invalid_snapshot_timestamp")

        if not np.isfinite(float(r.entry_open)) or float(r.entry_open) <= 0:
            violations.append(f"{tag}:invalid_entry_open")
        probs = np.asarray([r.p_buy, r.p_neutral, r.p_sell], dtype=float)
        if not np.isfinite(probs).all() or np.any(probs < 0) or abs(float(probs.sum()) - 1.0) > 1e-8:
            violations.append(f"{tag}:invalid_g1_probabilities")
        if str(r.g1_predicted) not in EXPECTED_CLASSES:
            violations.append(f"{tag}:unexpected_g1_class")

        if str(r.status) == "SETTLED":
            try:
                settled = pd.to_datetime(r.settled_at_utc, utc=True)
                if settled < t + pd.Timedelta(hours=6):
                    violations.append(f"{tag}:settled_before_6h_horizon")
            except Exception:
                violations.append(f"{tag}:invalid_settlement_timestamp")
            pnl = pd.to_numeric(pd.Series([r.a511_pnl]), errors="coerce").iloc[0]
            if not np.isfinite(pnl):
                violations.append(f"{tag}:missing_a511_pnl")
            b = as_bool(r.a511_win)
            if b is None or (np.isfinite(pnl) and b != bool(pnl > 0)):
                violations.append(f"{tag}:a511_win_inconsistent")
            if pd.isna(r.final_layer) or not str(r.final_layer).strip():
                violations.append(f"{tag}:missing_final_layer")
            if str(r.g0_label) not in EXPECTED_CLASSES:
                violations.append(f"{tag}:unexpected_g0_label")

    return {"pass": len(violations) == 0, "violations": violations}


def max_drawdown(pnls: np.ndarray) -> float:
    if len(pnls) == 0:
        return 0.0
    eq = np.cumsum(pnls)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float(np.max(peak[1:] - eq))


def max_loss_streak(pnls: np.ndarray) -> int:
    best = cur = 0
    for x in pnls:
        if x <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def bootstrap_mean_ci(pnls: np.ndarray) -> dict:
    n = len(pnls)
    if n == 0:
        return {"seed": BOOTSTRAP_SEED, "samples": BOOTSTRAP_N, "ci80": [None, None], "ci95": [None, None]}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means = np.empty(BOOTSTRAP_N, float)
    pos = 0
    batch = 1000
    while pos < BOOTSTRAP_N:
        m = min(batch, BOOTSTRAP_N - pos)
        idx = rng.integers(0, n, size=(m, n))
        means[pos:pos + m] = pnls[idx].mean(axis=1)
        pos += m
    q = np.quantile(means, [0.025, 0.10, 0.90, 0.975])
    return {
        "seed": BOOTSTRAP_SEED,
        "samples": BOOTSTRAP_N,
        "ci80": [float(q[1]), float(q[2])],
        "ci95": [float(q[0]), float(q[3])],
    }


def wilson_interval(wins: int, n: int, z: float = 1.959963984540054) -> list[float | None]:
    if n == 0:
        return [None, None]
    p = wins / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]


def metrics(pnls: np.ndarray) -> dict:
    n = len(pnls)
    if n == 0:
        return {
            "n": 0, "wins": 0, "losses": 0, "wr": None, "wr_wilson95": [None, None],
            "pnl": 0.0, "expectancy": None, "gross_profit": 0.0, "gross_loss": 0.0,
            "pf": None, "max_dd": 0.0, "max_loss_streak": 0,
            "bootstrap_mean": bootstrap_mean_ci(pnls),
        }
    wins = int((pnls > 0).sum())
    gp = float(pnls[pnls > 0].sum())
    gl = float(-pnls[pnls <= 0].sum())
    pf = float(gp / gl) if gl > 0 else None
    return {
        "n": int(n), "wins": wins, "losses": int(n - wins),
        "wr": float(wins / n), "wr_wilson95": wilson_interval(wins, n),
        "pnl": float(pnls.sum()), "expectancy": float(pnls.mean()),
        "gross_profit": gp, "gross_loss": gl, "pf": pf,
        "pf_infinite_no_losses": bool(gl == 0 and gp > 0),
        "max_dd": max_drawdown(pnls), "max_loss_streak": max_loss_streak(pnls),
        "bootstrap_mean": bootstrap_mean_ci(pnls),
    }


def pf_at_least(m: dict, threshold: float) -> bool:
    if m.get("pf_infinite_no_losses"):
        return True
    return m.get("pf") is not None and float(m["pf"]) >= threshold


def group_attribution(df: pd.DataFrame, col: str) -> dict:
    out = {}
    if len(df) == 0 or col not in df.columns:
        return out
    for key, g in df.groupby(col, dropna=False):
        p = as_num(g.a511_pnl).dropna().to_numpy(float)
        mm = metrics(p)
        out[str(key)] = {k: mm[k] for k in ["n", "wins", "losses", "wr", "pnl", "expectancy", "pf"]}
    return out


def rank_corr(x: pd.Series, y: pd.Series) -> float | None:
    z = pd.DataFrame({"x": as_num(x), "y": as_num(y)}).dropna()
    if len(z) < 3 or z.x.nunique() < 2 or z.y.nunique() < 2:
        return None
    return float(z.x.rank(method="average").corr(z.y.rank(method="average")))


def evaluate(df: pd.DataFrame, model: dict) -> dict:
    integ = integrity_checks(df, model)
    if all(c in df.columns for c in REQUIRED_COLUMNS):
        settled = df[(df.evidence_class.astype(str) == "TRUE_FORWARD") & (df.status.astype(str) == "SETTLED")].copy()
        pending = df[(df.evidence_class.astype(str) == "TRUE_FORWARD") & (df.status.astype(str) == "PENDING_SETTLEMENT")].copy()
    else:
        settled = pd.DataFrame(columns=REQUIRED_COLUMNS)
        pending = pd.DataFrame(columns=REQUIRED_COLUMNS)

    settled = settled.sort_values("decision_t_utc") if len(settled) else settled
    pnls = as_num(settled.a511_pnl).dropna().to_numpy(float) if len(settled) else np.asarray([], float)
    m = metrics(pnls)
    n = m["n"]
    ci80_lo, ci80_hi = m["bootstrap_mean"]["ci80"]
    ci95_lo, ci95_hi = m["bootstrap_mean"]["ci95"]

    f2_checks = {
        "n_ge_26": n >= 26,
        "total_pnl_gt_0": m["pnl"] > 0,
        "expectancy_gt_0": m["expectancy"] is not None and m["expectancy"] > 0,
        "pf_ge_1_20": pf_at_least(m, PF_GATE),
        "bootstrap80_lower_gt_0": ci80_lo is not None and ci80_lo > 0,
        "max_dd_le_26_64": m["max_dd"] <= MAX_DD_GATE,
        "integrity_pass": integ["pass"],
    }
    f3_checks = {
        "n_ge_52": n >= 52,
        "total_pnl_gt_0": m["pnl"] > 0,
        "expectancy_gt_0": m["expectancy"] is not None and m["expectancy"] > 0,
        "pf_ge_1_20": pf_at_least(m, PF_GATE),
        "bootstrap95_lower_gt_0": ci95_lo is not None and ci95_lo > 0,
        "max_dd_le_26_64": m["max_dd"] <= MAX_DD_GATE,
        "integrity_pass": integ["pass"],
    }

    if not integ["pass"]:
        stage = "INTEGRITY_HOLD"
        decision = "DATA_INTEGRITY_HOLD"
    elif n < 12:
        stage = "F0"
        decision = "OBSERVE_ONLY"
    elif n < 26:
        stage = "F1"
        early_supportive = m["pnl"] > 0 and (m["expectancy"] or 0) > 0 and pf_at_least(m, 1.0)
        decision = "EARLY_SUPPORTIVE" if early_supportive else "EARLY_CAUTION"
    elif n < 52:
        stage = "F2"
        decision = "CANDIDATE_REVIEW_ELIGIBLE" if all(f2_checks.values()) else "CONTINUE_FORWARD_OBSERVATION"
    else:
        stage = "F3"
        if all(f3_checks.values()):
            decision = "LIVE_ENGINEERING_REVIEW_ELIGIBLE"
        elif ci95_hi is not None and ci95_hi <= 0:
            decision = "FORWARD_EDGE_REJECTED"
        else:
            decision = "CONTINUE_FORWARD_OBSERVATION"

    health_bucket = pd.Series(index=settled.index, dtype="object")
    if len(settled):
        health_bucket = pd.Series(np.where(as_num(settled.weekly_sell_health) >= 0, "health_ge_0", "health_lt_0"), index=settled.index)
        tmp = settled.copy()
        tmp["weekly_health_bucket"] = health_bucket
    else:
        tmp = settled
        tmp["weekly_health_bucket"] = pd.Series(dtype="object")

    next_boundary = 12 if n < 12 else 26 if n < 26 else 52 if n < 52 else None
    return {
        "status": decision,
        "stage": stage,
        "settled_true_forward": n,
        "pending_true_forward": int(len(pending)),
        "next_stage_boundary": next_boundary,
        "observations_to_next_boundary": int(next_boundary - n) if next_boundary is not None else None,
        "frozen_gates": {"pf_min": PF_GATE, "max_dd_max": MAX_DD_GATE, "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_samples": BOOTSTRAP_N},
        "integrity": integ,
        "metrics": m,
        "f2_candidate_checks": f2_checks,
        "f3_strong_checks": f3_checks,
        "telemetry_report_only": {
            "g1_predicted": group_attribution(settled, "g1_predicted"),
            "weekly_health_sign": group_attribution(tmp, "weekly_health_bucket"),
            "g0_label": group_attribution(settled, "g0_label"),
            "spearman_p_sell_vs_pnl": rank_corr(settled.p_sell, settled.a511_pnl) if len(settled) else None,
            "spearman_weekly_health_vs_pnl": rank_corr(settled.weekly_sell_health, settled.a511_pnl) if len(settled) else None,
            "spearman_g7_weight_vs_pnl": rank_corr(settled.g7_diagnostic_weight, settled.a511_pnl) if len(settled) else None,
        },
        "guardrail": "Evaluator is read-only with respect to the forward ledger; telemetry is report-only; no automatic production promotion.",
    }


def fmt_pf(m: dict) -> str:
    if m.get("pf_infinite_no_losses"):
        return "∞"
    return "-" if m.get("pf") is None else f"{m['pf']:.3f}"


def render_md(result: dict) -> str:
    m = result["metrics"]
    wr = "-" if m["wr"] is None else f"{100*m['wr']:.2f}%"
    exp = "-" if m["expectancy"] is None else f"${m['expectancy']:+.4f}"
    ci80 = m["bootstrap_mean"]["ci80"]
    ci95 = m["bootstrap_mean"]["ci95"]
    fci = lambda x: "-" if x is None else f"${x:+.4f}"
    lines = [
        "# BTC Tuesday A5.11 — True Forward Evaluation",
        "",
        f"**Decision: `{result['status']}` — Stage `{result['stage']}`**",
        "",
        "Research/shadow only. This report cannot place or authorize a live order.",
        "",
        "## Current evidence",
        f"- Settled true-forward Tuesdays: **{result['settled_true_forward']}**",
        f"- Pending true-forward Tuesdays: **{result['pending_true_forward']}**",
        f"- Wins / losses: **{m['wins']} / {m['losses']}**",
        f"- WR: **{wr}**",
        f"- Total PnL: **${m['pnl']:+.2f}**",
        f"- Expectancy: **{exp}/trade**",
        f"- PF: **{fmt_pf(m)}**",
        f"- Max DD: **${m['max_dd']:.2f}**",
        f"- Max loss streak: **{m['max_loss_streak']}**",
        f"- Bootstrap 80% mean-PnL CI: **{fci(ci80[0])} → {fci(ci80[1])}**",
        f"- Bootstrap 95% mean-PnL CI: **{fci(ci95[0])} → {fci(ci95[1])}**",
        "",
        "## Integrity",
        f"- Status: **{'PASS' if result['integrity']['pass'] else 'FAIL'}**",
    ]
    if result["integrity"]["violations"]:
        lines += [f"- `{x}`" for x in result["integrity"]["violations"]]
    else:
        lines.append("- No ledger/model integrity violations detected.")

    if result["next_stage_boundary"] is not None:
        lines += [
            "",
            "## Next frozen milestone",
            f"- Boundary: **{result['next_stage_boundary']} settled Tuesdays**",
            f"- Remaining: **{result['observations_to_next_boundary']}**",
        ]

    lines += ["", "## F2 candidate gate"]
    lines += [f"- {'PASS' if ok else 'WAIT/FAIL'} — `{name}`" for name, ok in result["f2_candidate_checks"].items()]
    lines += ["", "## F3 strong-forward gate"]
    lines += [f"- {'PASS' if ok else 'WAIT/FAIL'} — `{name}`" for name, ok in result["f3_strong_checks"].items()]
    lines += [
        "",
        "## Guardrail",
        "G1/G6/G7 telemetry remains diagnostic only. No threshold, model, risk weight, or A5.11 management rule is tuned from this report.",
        "",
        "`LIVE_ENGINEERING_REVIEW_ELIGIBLE` is not live-trading authorization; it only permits a separate explicit production-engineering review.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, default=LEDGER_DEFAULT)
    ap.add_argument("--model", type=Path, default=MODEL_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON_DEFAULT)
    ap.add_argument("--out-md", type=Path, default=OUT_MD_DEFAULT)
    args = ap.parse_args()

    df, model = load_inputs(args.ledger, args.model)
    result = evaluate(df, model)
    args.out_json.write_text(json.dumps(result, indent=2, allow_nan=False))
    args.out_md.write_text(render_md(result))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
