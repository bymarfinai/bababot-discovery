#!/usr/bin/env python3
"""Tuesday A5.11 true-forward shadow/telemetry runner.

Modes:
- validate: reproduce frozen August G1/G6 telemetry and A5.11 outcomes.
- snapshot: write pre-outcome Tuesday telemetry only.
- settle: after T+6h, append frozen A5.11 paper outcome without rewriting snapshot.

No exchange order endpoints are called. Live BBC is untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import g0_global_pooled_regime_dataset as g0
import g0_global_pooled_regime_dataset_fast as g0fast
import tuesday_a511_true_oos_august as tue

ROOT = Path(__file__).resolve().parent.parent
MODEL_DEFAULT = ROOT / "BTC_Tuesday_Forward_Shadow_Model_State.json"
LEDGER_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Shadow_Ledger.csv"
STATUS_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Shadow_Status.md"
VALIDATION_JSON_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Shadow_Validation.json"
VALIDATION_MD_DEFAULT = ROOT / "BTC_Tuesday_A511_Forward_Shadow_Validation.md"
G1_AUG_DEFAULT = ROOT / "BTC_Global_Regime_G1_August_Tuesday.csv"
G6_AUG_DEFAULT = ROOT / "BTC_Global_Regime_G6_August.csv"

BASE_URLS = [
    "https://fapi.binance.com/fapi/v1/klines",
    "https://www.binance.com/fapi/v1/klines",
]
SYMBOL = "BTCUSDT"
STEP = pd.Timedelta(minutes=5)
LOOKBACK_HOURS = 168
REST_WARMUP_DAYS = 30
TRUE_FORWARD_START_WIB = "2026-08-25"
CANONICAL_CLASSES = ["BUY_COMPATIBLE", "NEUTRAL", "SELL_COMPATIBLE"]

LEDGER_COLUMNS = [
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


def utc_now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def load_state(path: Path) -> dict:
    state = json.loads(path.read_text())
    fp = state.get("model_fingerprint_sha256")
    if not fp:
        raise RuntimeError("model state missing fingerprint")
    payload = dict(state)
    payload.pop("model_fingerprint_sha256", None)
    calc = canonical_hash(payload)
    if calc != fp:
        raise RuntimeError(f"model fingerprint mismatch: stored={fp} calculated={calc}")
    if state.get("state_version") != "G1_FINAL_FROZEN_2026-07-30_V1":
        raise RuntimeError(f"unexpected state version {state.get('state_version')}")
    if state.get("classes_canonical_order") != CANONICAL_CLASSES:
        raise RuntimeError("unexpected canonical class order")
    if len(state.get("features", [])) != 17:
        raise RuntimeError("unexpected frozen feature count")
    return state


def state_predict(state: dict, rows: pd.DataFrame) -> np.ndarray:
    vals = rows[state["features"]].to_numpy(float).copy()
    med = np.asarray(state["imputer_median"], float)
    mean = np.asarray(state["scaler_mean"], float)
    scl = np.asarray(state["scaler_scale"], float)
    bad = ~np.isfinite(vals)
    if bad.any():
        rr, cc = np.where(bad)
        vals[rr, cc] = med[cc]
    z = (vals - mean) / scl
    coef = np.asarray(state["logit_coef"], float)
    intercept = np.asarray(state["logit_intercept"], float)
    logits = z @ coef.T + intercept
    logits -= logits.max(axis=1, keepdims=True)
    ex = np.exp(logits)
    raw = ex / ex.sum(axis=1, keepdims=True)
    model_order = list(state["classes_model_order"])
    out = np.zeros((len(rows), len(CANONICAL_CLASSES)), float)
    for j, c in enumerate(CANONICAL_CLASSES):
        out[:, j] = raw[:, model_order.index(c)]
    return out


def target_timestamp(date_wib: str | None) -> tuple[str, pd.Timestamp]:
    if date_wib is None:
        now_wib = utc_now().tz_convert("Asia/Jakarta")
        date_wib = str(now_wib.date())
    local = pd.Timestamp(f"{date_wib} 06:00:00", tz="Asia/Jakarta")
    if local.dayofweek != 1:
        raise RuntimeError(f"target {date_wib} is not Tuesday WIB")
    return date_wib, local.tz_convert("UTC")


def _request_chunk(start: pd.Timestamp, end: pd.Timestamp) -> list:
    params = {
        "symbol": SYMBOL,
        "interval": "5m",
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000) - 1,
        "limit": 1500,
    }
    errs = []
    for url in BASE_URLS:
        try:
            r = requests.get(url, params=params, timeout=45, headers={"User-Agent": "bababot-forward-shadow/1.0"})
            if r.status_code != 200:
                errs.append(f"{url} HTTP{r.status_code} {r.text[:100]}")
                continue
            data = r.json()
            if not isinstance(data, list):
                errs.append(f"{url} non-list response")
                continue
            return data
        except Exception as exc:
            errs.append(f"{url} {type(exc).__name__}:{exc}")
    raise RuntimeError("Binance kline request failed: " + " | ".join(errs))


def fetch_5m(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if end <= start:
        raise ValueError("end must be after start")
    rows = []
    cur = start
    while cur < end:
        data = _request_chunk(cur, end)
        if not data:
            break
        rows.extend(data)
        last_open = pd.to_datetime(int(data[-1][0]), unit="ms", utc=True)
        nxt = last_open + STEP
        if nxt <= cur:
            raise RuntimeError("Binance pagination did not advance")
        cur = nxt
        if len(data) < 1500:
            break
    if not rows:
        raise RuntimeError(f"no Binance 5m data for {start} -> {end}")
    z = pd.DataFrame(rows)
    out = pd.DataFrame({
        "ts": pd.to_datetime(pd.to_numeric(z.iloc[:, 0]), unit="ms", utc=True),
        "open": pd.to_numeric(z.iloc[:, 1], errors="coerce"),
        "high": pd.to_numeric(z.iloc[:, 2], errors="coerce"),
        "low": pd.to_numeric(z.iloc[:, 3], errors="coerce"),
        "close": pd.to_numeric(z.iloc[:, 4], errors="coerce"),
        "quote_volume": pd.to_numeric(z.iloc[:, 7], errors="coerce"),
        "taker_buy_quote": pd.to_numeric(z.iloc[:, 10], errors="coerce"),
    }).dropna()
    out = out.drop_duplicates("ts").sort_values("ts")
    out = out[(out.ts >= start) & (out.ts < end)].copy()
    return out.set_index("ts", drop=False)


def fetch_entry_open(t: pd.Timestamp) -> float:
    data = _request_chunk(t, t + STEP)
    if not data:
        raise RuntimeError(f"entry candle unavailable at {t}")
    ts = pd.to_datetime(int(data[0][0]), unit="ms", utc=True)
    if ts != t:
        raise RuntimeError(f"unexpected entry candle {ts}, expected {t}")
    # Deliberately expose only the immutable candle OPEN. No high/low/close is returned.
    return float(data[0][1])


def prepare_rest_for_snapshot(t: pd.Timestamp) -> pd.DataFrame:
    start = t - pd.Timedelta(days=REST_WARMUP_DAYS)
    raw = fetch_5m(start, t)  # hard cap: no T or post-entry bar in feature frame
    k = g0.prepare(raw)
    if k.index.max() != t - STEP:
        raise RuntimeError(f"snapshot max bar {k.index.max()} != expected {t-STEP}")
    return k


def prepare_rest_for_settlement(t: pd.Timestamp) -> pd.DataFrame:
    start = t - pd.Timedelta(days=REST_WARMUP_DAYS)
    end = t + pd.Timedelta(hours=6)
    raw = fetch_5m(start, end)
    k = g0.prepare(raw)
    expected_last = end - STEP
    if k.index.max() != expected_last:
        raise RuntimeError(f"settlement max bar {k.index.max()} != expected {expected_last}")
    return k


def feature_matrix(k: pd.DataFrame, times: list[pd.Timestamp], features: list[str]) -> pd.DataFrame:
    rows = []
    for h in times:
        f, ferr = g0fast.feature_row_fast(k, h)
        if ferr:
            raise RuntimeError(f"feature error {h}: {ferr}")
        rows.append({x: f[x] for x in features})
    return pd.DataFrame(rows)


def telemetry_from_k(state: dict, k: pd.DataFrame, t: pd.Timestamp) -> dict:
    fx = feature_matrix(k, [t], state["features"])
    p = state_predict(state, fx)[0]
    probs = dict(zip(CANONICAL_CLASSES, map(float, p)))
    pred = CANONICAL_CLASSES[int(np.argmax(p))]

    hours = list(pd.date_range(
        start=t - pd.Timedelta(hours=LOOKBACK_HOURS),
        periods=LOOKBACK_HOURS,
        freq="1h",
        tz="UTC",
    ))
    hx = feature_matrix(k, hours, state["features"])
    hp = state_predict(state, hx)
    sell_i = CANONICAL_CLASSES.index("SELL_COMPATIBLE")
    mean_sell = float(hp[:, sell_i].mean())
    prior = float(state["frozen_sell_prior"])
    health = mean_sell - prior
    weight = min(1.0, mean_sell / prior)
    return {
        "p_buy": probs["BUY_COMPATIBLE"],
        "p_neutral": probs["NEUTRAL"],
        "p_sell": probs["SELL_COMPATIBLE"],
        "g1_predicted": pred,
        "frozen_sell_prior": prior,
        "point_sell_lift": probs["SELL_COMPATIBLE"] / prior,
        "weekly_mean_p_sell_168h": mean_sell,
        "weekly_sell_health": health,
        "g7_diagnostic_weight": weight,
    }


def empty_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        return empty_ledger()
    df = pd.read_csv(path)
    for c in LEDGER_COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    return df[LEDGER_COLUMNS].copy()


def write_ledger_atomic(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def render_status(df: pd.DataFrame, path: Path) -> None:
    settled = df[df.status == "SETTLED"] if len(df) else df
    pending = df[df.status == "PENDING_SETTLEMENT"] if len(df) else df
    forward = settled[settled.evidence_class == "TRUE_FORWARD"] if len(settled) else settled
    wins = int(pd.to_numeric(forward.a511_win, errors="coerce").fillna(0).astype(bool).sum()) if len(forward) else 0
    pnl = float(pd.to_numeric(forward.a511_pnl, errors="coerce").fillna(0).sum()) if len(forward) else 0.0
    lines = [
        "# BTC Tuesday A5.11 — Forward Shadow Status",
        "",
        "**Research/shadow only. Live BBC untouched.**",
        "",
        f"- Ledger rows: **{len(df)}**",
        f"- Pending settlement: **{len(pending)}**",
        f"- Settled true-forward rows: **{len(forward)}**",
        f"- True-forward wins: **{wins}**",
        f"- True-forward paper PnL: **${pnl:+.2f}**",
        "",
        "No telemetry field is a production trade gate. Frozen A5.11 paper SELL remains the observation anchor.",
    ]
    if len(df):
        x = df.iloc[-1]
        lines += [
            "",
            "## Latest row",
            f"- Date WIB: **{x.date_wib}**",
            f"- Status: **{x.status}**",
            f"- G1: `{x.g1_predicted}` (pSELL {float(x.p_sell)*100:.2f}%)" if pd.notna(x.p_sell) else "- G1: pending",
            f"- Weekly health: **{float(x.weekly_sell_health):+.5f}**" if pd.notna(x.weekly_sell_health) else "- Weekly health: pending",
            f"- A5.11 PnL: **${float(x.a511_pnl):+.2f}**" if pd.notna(x.a511_pnl) else "- A5.11 PnL: pending settlement",
        ]
    path.write_text("\n".join(lines) + "\n")


def mode_snapshot(args, state: dict) -> None:
    date_wib, t = target_timestamp(args.target_date)
    df = read_ledger(args.ledger)
    existing = df.index[df.date_wib.astype(str) == date_wib].tolist() if len(df) else []
    if existing:
        print(json.dumps({"status": "SNAPSHOT_IDEMPOTENT_NOOP", "date_wib": date_wib}, indent=2))
        render_status(df, args.status_md)
        return

    k = prepare_rest_for_snapshot(t)
    telem = telemetry_from_k(state, k, t)
    entry_open = fetch_entry_open(t)
    evidence_class = "TRUE_FORWARD" if date_wib >= TRUE_FORWARD_START_WIB else "PARITY_FIXTURE"
    row = {c: np.nan for c in LEDGER_COLUMNS}
    row.update({
        "date_wib": date_wib,
        "decision_t_utc": str(t),
        "evidence_class": evidence_class,
        "status": "PENDING_SETTLEMENT",
        "snapshot_recorded_at_utc": str(utc_now()),
        "snapshot_data_max_ts_utc": str(t - STEP),
        "model_fingerprint_sha256": state["model_fingerprint_sha256"],
        "entry_open": entry_open,
        **telem,
        "shadow_direction": "SELL",
        "shadow_policy": "FROZEN_A5.11_ALWAYS_PAPER_SELL__REGIME_TELEMETRY_ONLY",
    })
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.sort_values("date_wib").reset_index(drop=True)
    write_ledger_atomic(df, args.ledger)
    render_status(df, args.status_md)
    print(json.dumps({"status": "SNAPSHOT_WRITTEN", "date_wib": date_wib, **telem}, indent=2))


def mode_settle(args, state: dict) -> None:
    date_wib, t = target_timestamp(args.target_date)
    df = read_ledger(args.ledger)
    idx = df.index[df.date_wib.astype(str) == date_wib].tolist() if len(df) else []
    if len(idx) != 1:
        raise RuntimeError(f"settlement requires exactly one prior snapshot for {date_wib}; found {len(idx)}")
    i = idx[0]
    if str(df.loc[i, "status"]) == "SETTLED":
        print(json.dumps({"status": "SETTLEMENT_IDEMPOTENT_NOOP", "date_wib": date_wib}, indent=2))
        render_status(df, args.status_md)
        return
    if str(df.loc[i, "model_fingerprint_sha256"]) != state["model_fingerprint_sha256"]:
        raise RuntimeError("ledger snapshot model fingerprint differs from frozen state")
    if utc_now() < t + pd.Timedelta(hours=6):
        raise RuntimeError("cannot settle before the frozen 6h horizon completes")

    # Preserve immutable snapshot fields before any settlement work.
    frozen_snapshot = df.loc[i, LEDGER_COLUMNS[:19]].copy()
    k = prepare_rest_for_settlement(t)
    tr = tue.simulate_parent(k, t)
    lr = tue.layered(k, tr)
    label, reason, hit_min = g0fast.label_row_fast(k, t)
    updates = {
        "status": "SETTLED",
        "settled_at_utc": str(utc_now()),
        "parent_reason": tr["reason"],
        "parent_pnl": float(tr["pnl"]),
        "parent_mfe_pct": 100.0 * float(tr["mfe"]),
        "parent_mae_pct": 100.0 * float(tr["mae"]),
        "a52_act": bool(lr["a52_act"]),
        "fastmr_act": bool(lr["fastmr_arm"]),
        "runner_recovery": bool(lr["recovery"]),
        "final_layer": lr["final_layer"],
        "a511_pnl": float(lr["a511_pnl"]),
        "a511_win": bool(lr["a511_pnl"] > 0),
        "g0_label": label,
        "g0_label_reason": reason,
        "g0_first_hit_min": hit_min,
    }
    for key, val in updates.items():
        df.loc[i, key] = val
    # Snapshot must be bitwise/logically unchanged by settlement.
    after_snapshot = df.loc[i, LEDGER_COLUMNS[:19]]
    if not frozen_snapshot.equals(after_snapshot):
        raise RuntimeError("settlement attempted to mutate immutable snapshot fields")
    write_ledger_atomic(df, args.ledger)
    render_status(df, args.status_md)
    print(json.dumps({"status": "SETTLED", "date_wib": date_wib, **updates}, indent=2, default=str))


def mode_validate(args, state: dict) -> None:
    ref1 = pd.read_csv(args.g1_aug)
    ref1["decision_t_utc"] = pd.to_datetime(ref1.decision_t_utc, utc=True)
    ref6 = pd.read_csv(args.g6_aug)
    ref6["decision_t_utc"] = pd.to_datetime(ref6.decision_t_utc, utc=True)
    ref6 = ref6.set_index("decision_t_utc")
    raw = tue.load_extended()
    k = g0.prepare(raw)
    rows = []
    max_g1 = max_g6 = max_a511 = 0.0
    for r in ref1.itertuples(index=False):
        t = r.decision_t_utc
        telem = telemetry_from_k(state, k, t)
        expected = np.asarray([r.p_buy, r.p_neutral, r.p_sell], float)
        actual = np.asarray([telem["p_buy"], telem["p_neutral"], telem["p_sell"]], float)
        max_g1 = max(max_g1, float(np.max(np.abs(actual - expected))))
        max_g6 = max(max_g6, abs(telem["weekly_mean_p_sell_168h"] - float(ref6.loc[t, "mean_p_sell_168h"])))
        tr = tue.simulate_parent(k, t)
        lr = tue.layered(k, tr)
        max_a511 = max(max_a511, abs(float(lr["a511_pnl"]) - float(r.a511_pnl)))
        rows.append({
            "date_wib": r.date_wib,
            **telem,
            "a511_pnl": float(lr["a511_pnl"]),
            "reference_a511_pnl": float(r.a511_pnl),
        })
    checks = {
        "model_fingerprint_valid": True,
        "g1_august_max_abs_le_1e10": bool(max_g1 <= 1e-10),
        "g6_august_max_abs_le_1e10": bool(max_g6 <= 1e-10),
        "a511_august_max_abs_le_1e10": bool(max_a511 <= 1e-10),
    }
    result = {
        "status": "FORWARD_SHADOW_IMPLEMENTATION_PARITY_PASS" if all(checks.values()) else "FORWARD_SHADOW_IMPLEMENTATION_PARITY_FAIL",
        "model_fingerprint_sha256": state["model_fingerprint_sha256"],
        "max_abs_g1_august": max_g1,
        "max_abs_g6_august": max_g6,
        "max_abs_a511_august": max_a511,
        "checks": checks,
        "rows": rows,
        "pass": bool(all(checks.values())),
        "guardrail": "August is parity fixture only; no new forward evidence is claimed.",
    }
    args.validation_json.write_text(json.dumps(result, indent=2, default=str))
    lines = [
        "# Tuesday A5.11 Forward Shadow — Implementation Validation",
        "",
        f"**Status: {'PASS' if result['pass'] else 'FAIL'}**",
        "",
        f"- Frozen model fingerprint: `{state['model_fingerprint_sha256']}`",
        f"- Max G1 August probability diff: `{max_g1:.3e}`",
        f"- Max G6 August weekly pSELL diff: `{max_g6:.3e}`",
        f"- Max A5.11 August PnL diff: `{max_a511:.3e}`",
        "",
        "August 4/11/18 are implementation fixtures only. The first new true-forward row is 2026-08-25 WIB.",
        "Live BBC is untouched.",
    ]
    args.validation_md.write_text("\n".join(lines) + "\n")
    print(json.dumps(result, indent=2, default=str))
    if not result["pass"]:
        raise RuntimeError("forward shadow implementation parity failed")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["validate", "snapshot", "settle"], required=True)
    p.add_argument("--target-date", default=None, help="Tuesday date in WIB, YYYY-MM-DD")
    p.add_argument("--model-state", type=Path, default=MODEL_DEFAULT)
    p.add_argument("--ledger", type=Path, default=LEDGER_DEFAULT)
    p.add_argument("--status-md", type=Path, default=STATUS_DEFAULT)
    p.add_argument("--validation-json", type=Path, default=VALIDATION_JSON_DEFAULT)
    p.add_argument("--validation-md", type=Path, default=VALIDATION_MD_DEFAULT)
    p.add_argument("--g1-aug", type=Path, default=G1_AUG_DEFAULT)
    p.add_argument("--g6-aug", type=Path, default=G6_AUG_DEFAULT)
    return p.parse_args()


def main():
    args = parse_args()
    state = load_state(args.model_state)
    if args.mode == "validate":
        mode_validate(args, state)
    elif args.mode == "snapshot":
        mode_snapshot(args, state)
    else:
        mode_settle(args, state)


if __name__ == "__main__":
    main()
