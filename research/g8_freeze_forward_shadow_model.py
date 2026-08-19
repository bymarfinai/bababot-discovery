#!/usr/bin/env python3
"""Freeze the final G1 model for true forward Tuesday shadow inference.

Research/shadow only. Live BBC untouched.

The model is fit exactly once from the frozen G0 dataset ending 2026-07-30 UTC,
serialized to explicit numeric parameters, fingerprinted, and parity-checked
against the already-persisted August G1 and G6 outputs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

import g0_global_pooled_regime_dataset as g0
import g0_global_pooled_regime_dataset_fast as g0fast
import g1_embargoed_pooled_regime_walkforward as g1
import tuesday_a511_true_oos_august as tue

OUT = Path(os.getenv("G8FREEZE_OUT", "g8freeze_out"))
OUT.mkdir(parents=True, exist_ok=True)
G0_DATA = Path(os.getenv("G0_DATA", "../BTC_Global_Regime_G0_Pooled_Hourly_States.csv"))
G1_AUG = Path(os.getenv("G1_AUG", "../BTC_Global_Regime_G1_August_Tuesday.csv"))
G6_AUG = Path(os.getenv("G6_AUG", "../BTC_Global_Regime_G6_August.csv"))
HIST_END = pd.Timestamp("2026-07-30", tz="UTC")
EXPECTED_N = 23304
LOOKBACK_HOURS = 168
TOL = 1e-10


def canonical_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def extract_state(model, hist: pd.DataFrame) -> dict:
    imp = model.named_steps["imputer"]
    scale = model.named_steps["scale"]
    logit = model.named_steps["logit"]
    counts = hist.label.value_counts()
    rates = {c: float((hist.label == c).mean()) for c in g1.CLASSES}
    payload = {
        "state_version": "G1_FINAL_FROZEN_2026-07-30_V1",
        "research_cutoff_exclusive": str(HIST_END),
        "training_n": int(len(hist)),
        "features": list(g1.FEATURES),
        "classes_model_order": [str(x) for x in logit.classes_.tolist()],
        "classes_canonical_order": list(g1.CLASSES),
        "label_counts": {c: int(counts.get(c, 0)) for c in g1.CLASSES},
        "label_rates": rates,
        "frozen_sell_prior": rates["SELL_COMPATIBLE"],
        "imputer_median": [float(x) for x in imp.statistics_.tolist()],
        "scaler_mean": [float(x) for x in scale.mean_.tolist()],
        "scaler_scale": [float(x) for x in scale.scale_.tolist()],
        "logit_coef": [[float(v) for v in row] for row in logit.coef_.tolist()],
        "logit_intercept": [float(x) for x in logit.intercept_.tolist()],
        "model_spec": {
            "imputer": "median",
            "scaler": "StandardScaler",
            "estimator": "LogisticRegression",
            "penalty": "l2",
            "C": 1.0,
            "solver": "lbfgs",
            "max_iter": 2000,
            "class_weight": None,
            "random_state": 7,
        },
        "sklearn_version_at_freeze": sklearn.__version__,
        "purpose": "shadow telemetry inference only; never a production order gate",
    }
    payload["model_fingerprint_sha256"] = canonical_hash(payload)
    return payload


def state_predict(state: dict, X: pd.DataFrame) -> np.ndarray:
    vals = X[state["features"]].to_numpy(float).copy()
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
    logits = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    raw = exp / exp.sum(axis=1, keepdims=True)
    model_order = list(state["classes_model_order"])
    out = np.zeros((len(X), len(g1.CLASSES)), float)
    for j, c in enumerate(g1.CLASSES):
        out[:, j] = raw[:, model_order.index(c)]
    return out


def load_hist() -> pd.DataFrame:
    hist = pd.read_csv(G0_DATA)
    hist["decision_t_utc"] = pd.to_datetime(hist.decision_t_utc, utc=True)
    hist = hist.sort_values("decision_t_utc").reset_index(drop=True)
    if len(hist) != EXPECTED_N:
        raise RuntimeError(f"expected {EXPECTED_N} G0 rows, got {len(hist)}")
    if not (hist.decision_t_utc < HIST_END).all():
        raise RuntimeError("G0 data crosses frozen cutoff")
    if list(g1.FEATURES) != list(g0.FEATURES):
        raise RuntimeError("G1/G0 feature list mismatch")
    return hist


def august_parity(model, state: dict) -> dict:
    ref1 = pd.read_csv(G1_AUG)
    ref1["decision_t_utc"] = pd.to_datetime(ref1.decision_t_utc, utc=True)
    ref6 = pd.read_csv(G6_AUG)
    ref6["decision_t_utc"] = pd.to_datetime(ref6.decision_t_utc, utc=True)
    ref6 = ref6.set_index("decision_t_utc")

    raw = tue.load_extended()
    k = g0.prepare(raw)
    rows = []
    max_pipe_state = 0.0
    max_g1_ref = 0.0
    max_g6_ref = 0.0

    for r in ref1.itertuples(index=False):
        t = r.decision_t_utc
        f, ferr = g0fast.feature_row_fast(k, t)
        if ferr:
            raise RuntimeError(f"G1 August feature error {t}: {ferr}")
        X = pd.DataFrame([{x: f[x] for x in g1.FEATURES}])
        pipe = g1.normalize_proba(model, X)[0]
        frozen = state_predict(state, X)[0]
        max_pipe_state = max(max_pipe_state, float(np.max(np.abs(pipe - frozen))))
        expected = np.asarray([r.p_buy, r.p_neutral, r.p_sell], float)
        max_g1_ref = max(max_g1_ref, float(np.max(np.abs(frozen - expected))))

        hours = pd.date_range(
            start=t - pd.Timedelta(hours=LOOKBACK_HOURS),
            periods=LOOKBACK_HOURS,
            freq="1h",
            tz="UTC",
        )
        feat_rows = []
        for h in hours:
            hf, herr = g0fast.feature_row_fast(k, h)
            if herr:
                raise RuntimeError(f"G6 August feature error {h}: {herr}")
            feat_rows.append({x: hf[x] for x in g1.FEATURES})
        hp = state_predict(state, pd.DataFrame(feat_rows))
        mean_sell = float(hp[:, g1.CLASSES.index("SELL_COMPATIBLE")].mean())
        expected_mean = float(ref6.loc[t, "mean_p_sell_168h"])
        max_g6_ref = max(max_g6_ref, abs(mean_sell - expected_mean))
        rows.append({
            "date_wib": r.date_wib,
            "decision_t_utc": str(t),
            "p_buy": float(frozen[g1.CLASSES.index("BUY_COMPATIBLE")]),
            "p_neutral": float(frozen[g1.CLASSES.index("NEUTRAL")]),
            "p_sell": float(frozen[g1.CLASSES.index("SELL_COMPATIBLE")]),
            "mean_p_sell_168h": mean_sell,
            "weekly_sell_health": mean_sell - float(state["frozen_sell_prior"]),
        })

    checks = {
        "pipeline_vs_serialized_max_abs_le_1e10": bool(max_pipe_state <= TOL),
        "serialized_vs_g1_august_max_abs_le_1e10": bool(max_g1_ref <= TOL),
        "serialized_weekly_vs_g6_august_max_abs_le_1e10": bool(max_g6_ref <= TOL),
    }
    return {
        "rows": rows,
        "max_abs_pipeline_vs_serialized": max_pipe_state,
        "max_abs_serialized_vs_g1_august": max_g1_ref,
        "max_abs_weekly_vs_g6_august": max_g6_ref,
        "checks": checks,
        "pass": bool(all(checks.values())),
    }


def main() -> None:
    hist = load_hist()
    model = g1.make_model()
    model.fit(hist[g1.FEATURES], hist.label)
    state = extract_state(model, hist)
    parity = august_parity(model, state)
    if not parity["pass"]:
        raise RuntimeError("frozen-model parity failed: " + json.dumps(parity, default=str))

    summary = {
        "status": "G8_FORWARD_MODEL_FROZEN_PARITY_PASS",
        "model_fingerprint_sha256": state["model_fingerprint_sha256"],
        "training_n": state["training_n"],
        "frozen_sell_prior": state["frozen_sell_prior"],
        "august_parity": parity,
        "guardrail": "Immutable forward shadow state; no future retraining; live BBC untouched.",
    }
    (OUT / "BTC_Tuesday_Forward_Shadow_Model_State.json").write_text(json.dumps(state, indent=2))
    (OUT / "BTC_Tuesday_Forward_Shadow_Model_Freeze_Summary.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# Tuesday A5.11 Forward Shadow — Frozen G1 Model State",
        "",
        "**Status: PARITY PASS — eligible for immutable forward inference.**",
        "",
        f"- Training rows: **{state['training_n']:,}**",
        f"- Cutoff: **{state['research_cutoff_exclusive']}**",
        f"- Frozen SELL prior: **{100*state['frozen_sell_prior']:.4f}%**",
        f"- Fingerprint: `{state['model_fingerprint_sha256']}`",
        f"- sklearn at freeze: `{state['sklearn_version_at_freeze']}`",
        "",
        "## August implementation parity",
        f"- pipeline vs serialized max abs diff: `{parity['max_abs_pipeline_vs_serialized']:.3e}`",
        f"- serialized vs G1 August max abs diff: `{parity['max_abs_serialized_vs_g1_august']:.3e}`",
        f"- weekly mean pSELL vs G6 August max abs diff: `{parity['max_abs_weekly_vs_g6_august']:.3e}`",
        "",
        "This state is telemetry-only and must not be retrained during the forward protocol.",
        "Live BBC is untouched.",
    ]
    (OUT / "BTC_Tuesday_Forward_Shadow_Model_Freeze.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
