#!/usr/bin/env python3
"""G1 — preregistered embargoed pooled BTC regime walk-forward.

Research only; live BBC untouched.

Inputs are frozen by:
- BTC_Global_Regime_G0_Preregistration.md
- BTC_Global_Regime_G1_Preregistration.md

No feature selection, threshold sweep, or hyperparameter search is performed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import g0_global_pooled_regime_dataset as g0
import g0_global_pooled_regime_dataset_fast as g0fast
import tuesday_a511_true_oos_august as tue

OUT = Path(os.getenv("G1_OUT", "g1_out"))
OUT.mkdir(parents=True, exist_ok=True)
G0_DATA = Path(os.getenv("G0_DATA", "../BTC_Global_Regime_G0_Pooled_Hourly_States.csv"))

CLASSES = ["BUY_COMPATIBLE", "NEUTRAL", "SELL_COMPATIBLE"]
FEATURES = list(g0.FEATURES)
FIRST_MONTH = pd.Timestamp("2024-03-01", tz="UTC")
HIST_END = pd.Timestamp("2026-07-30", tz="UTC")
EMBARGO = pd.Timedelta(hours=6)
EXPECTED_AUG = ["2026-08-04", "2026-08-11", "2026-08-18"]


def make_model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(
            penalty="l2",
            C=1.0,
            solver="lbfgs",
            max_iter=2000,
            class_weight=None,
            random_state=7,
        )),
    ])


def normalize_proba(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    raw = model.predict_proba(X)
    mclasses = list(model.named_steps["logit"].classes_)
    out = np.zeros((len(X), len(CLASSES)), dtype=float)
    for j, c in enumerate(CLASSES):
        if c not in mclasses:
            raise RuntimeError(f"training model missing class {c}; classes={mclasses}")
        out[:, j] = raw[:, mclasses.index(c)]
    return out


def prior_vector(train: pd.DataFrame) -> np.ndarray:
    counts = train.label.value_counts()
    p = np.asarray([float(counts.get(c, 0)) for c in CLASSES], dtype=float)
    if p.sum() <= 0:
        raise RuntimeError("empty class prior")
    p = p / p.sum()
    # Numerical protection only; does not change hard class except degenerate zero classes.
    p = np.clip(p, 1e-12, 1.0)
    return p / p.sum()


def onehot(y: np.ndarray) -> np.ndarray:
    lut = {c: i for i, c in enumerate(CLASSES)}
    z = np.zeros((len(y), len(CLASSES)), dtype=float)
    for i, v in enumerate(y):
        z[i, lut[str(v)]] = 1.0
    return z


def multiclass_brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.sum((p - onehot(y)) ** 2, axis=1)))


def score_predictions(y: np.ndarray, p: np.ndarray, pred: np.ndarray) -> dict:
    sell_i = CLASSES.index("SELL_COMPATIBLE")
    sell_y = (y == "SELL_COMPATIBLE").astype(int)
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "macro_f1": float(f1_score(y, pred, labels=CLASSES, average="macro", zero_division=0)),
        "log_loss": float(log_loss(y, p, labels=CLASSES)),
        "brier": multiclass_brier(y, p),
        "sell_auc": float(roc_auc_score(sell_y, p[:, sell_i])),
        "confusion_matrix": confusion_matrix(y, pred, labels=CLASSES).astype(int).tolist(),
        "labels": CLASSES,
    }


def load_g0() -> pd.DataFrame:
    if not G0_DATA.exists():
        raise RuntimeError(f"missing G0 dataset: {G0_DATA}")
    df = pd.read_csv(G0_DATA)
    df["decision_t_utc"] = pd.to_datetime(df.decision_t_utc, utc=True)
    df = df.sort_values("decision_t_utc").reset_index(drop=True)
    if df.decision_t_utc.min() != pd.Timestamp("2023-12-02", tz="UTC"):
        raise RuntimeError(f"unexpected G0 start {df.decision_t_utc.min()}")
    if not (df.decision_t_utc < HIST_END).all():
        raise RuntimeError("G0 historical dataset crosses frozen cutoff")
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise RuntimeError(f"G0 dataset missing features {missing}")
    bad_labels = sorted(set(df.label) - set(CLASSES))
    if bad_labels:
        raise RuntimeError(f"unexpected labels {bad_labels}")
    return df


def month_starts() -> list[pd.Timestamp]:
    out = []
    cur = FIRST_MONTH
    while cur < HIST_END:
        out.append(cur)
        cur = cur + pd.offsets.MonthBegin(1)
    return out


def walkforward(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    embargo_checks = []

    for ms in month_starts():
        me = min(ms + pd.offsets.MonthBegin(1), HIST_END)
        train = df[(df.decision_t_utc + EMBARGO) <= ms]
        test = df[(df.decision_t_utc >= ms) & (df.decision_t_utc < me)]
        if test.empty:
            continue
        if len(train) < 1000:
            raise RuntimeError(f"insufficient warmup for {ms}: {len(train)}")
        if train.label.nunique() != len(CLASSES):
            raise RuntimeError(f"missing training class for {ms}: {train.label.value_counts().to_dict()}")

        latest_mature = train.decision_t_utc.max() + EMBARGO
        embargo_ok = bool(latest_mature <= ms)
        embargo_checks.append({
            "month": str(ms.date()),
            "train_n": int(len(train)),
            "test_n": int(len(test)),
            "latest_train_label_matures": str(latest_mature),
            "month_start": str(ms),
            "pass": embargo_ok,
        })
        if not embargo_ok:
            raise RuntimeError(f"embargo violation {ms}: {latest_mature}")

        model = make_model()
        model.fit(train[FEATURES], train.label)
        p = normalize_proba(model, test[FEATURES])
        pred = np.asarray([CLASSES[i] for i in np.argmax(p, axis=1)], dtype=object)
        pri = prior_vector(train)
        base_p = np.tile(pri, (len(test), 1))
        base_pred = np.asarray([CLASSES[int(np.argmax(pri))]] * len(test), dtype=object)

        for j, (_, r) in enumerate(test.iterrows()):
            rows.append({
                "decision_t_utc": r.decision_t_utc,
                "actual": r.label,
                "predicted": pred[j],
                "p_buy": float(p[j, CLASSES.index("BUY_COMPATIBLE")]),
                "p_neutral": float(p[j, CLASSES.index("NEUTRAL")]),
                "p_sell": float(p[j, CLASSES.index("SELL_COMPATIBLE")]),
                "baseline_predicted": base_pred[j],
                "baseline_p_buy": float(base_p[j, CLASSES.index("BUY_COMPATIBLE")]),
                "baseline_p_neutral": float(base_p[j, CLASSES.index("NEUTRAL")]),
                "baseline_p_sell": float(base_p[j, CLASSES.index("SELL_COMPATIBLE")]),
                "model_month": str(ms.date()),
                "train_n": int(len(train)),
            })

    wf = pd.DataFrame(rows).sort_values("decision_t_utc").reset_index(drop=True)
    y = wf.actual.to_numpy(str)
    p = wf[["p_buy", "p_neutral", "p_sell"]].to_numpy(float)
    pred = wf.predicted.to_numpy(str)
    bp = wf[["baseline_p_buy", "baseline_p_neutral", "baseline_p_sell"]].to_numpy(float)
    bpred = wf.baseline_predicted.to_numpy(str)

    model_score = score_predictions(y, p, pred)
    baseline_score = score_predictions(y, bp, bpred)

    actual_sell_rate = float((wf.actual == "SELL_COMPATIBLE").mean())
    sell_mask = wf.predicted == "SELL_COMPATIBLE"
    predicted_sell_coverage = float(sell_mask.mean())
    predicted_sell_precision = float((wf.loc[sell_mask, "actual"] == "SELL_COMPATIBLE").mean()) if sell_mask.any() else 0.0

    predicted_class_stats = {}
    for c in CLASSES:
        m = wf.predicted == c
        predicted_class_stats[c] = {
            "n": int(m.sum()),
            "coverage": float(m.mean()),
            "actual_distribution": {
                a: float((wf.loc[m, "actual"] == a).mean()) if m.any() else None for a in CLASSES
            },
        }

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(wf)), 4), start=1):
        x = wf.iloc[idx]
        yy = x.actual.to_numpy(str)
        pp = x[["p_buy", "p_neutral", "p_sell"]].to_numpy(float)
        bb = x[["baseline_p_buy", "baseline_p_neutral", "baseline_p_sell"]].to_numpy(float)
        blocks.append({
            "block": b,
            "start": str(x.iloc[0].decision_t_utc),
            "end": str(x.iloc[-1].decision_t_utc),
            "n": int(len(x)),
            "model_log_loss": float(log_loss(yy, pp, labels=CLASSES)),
            "baseline_log_loss": float(log_loss(yy, bb, labels=CLASSES)),
            "model_brier": multiclass_brier(yy, pp),
            "baseline_brier": multiclass_brier(yy, bb),
        })
        blocks[-1]["logloss_improved"] = bool(blocks[-1]["model_log_loss"] < blocks[-1]["baseline_log_loss"])

    checks = {
        "predictions_ge_18000": bool(len(wf) >= 18000),
        "causal_embargo_all_months": bool(all(x["pass"] for x in embargo_checks)),
        "logloss_beats_prior": bool(model_score["log_loss"] < baseline_score["log_loss"]),
        "brier_beats_prior": bool(model_score["brier"] < baseline_score["brier"]),
        "sell_auc_ge_055": bool(model_score["sell_auc"] >= 0.55),
        "sell_enrichment_ge_3pp": bool(predicted_sell_precision >= actual_sell_rate + 0.03),
        "predicted_sell_coverage_ge_20pct": bool(predicted_sell_coverage >= 0.20),
        "logloss_improves_3_of_4_blocks": bool(sum(x["logloss_improved"] for x in blocks) >= 3),
    }

    summary = {
        "model": model_score,
        "baseline": baseline_score,
        "actual_sell_rate": actual_sell_rate,
        "predicted_sell_coverage": predicted_sell_coverage,
        "predicted_sell_precision": predicted_sell_precision,
        "sell_enrichment_pp": 100.0 * (predicted_sell_precision - actual_sell_rate),
        "predicted_class_stats": predicted_class_stats,
        "blocks": blocks,
        "embargo_checks": embargo_checks,
        "acceptance_checks": checks,
        "pass": bool(all(checks.values())),
    }
    return wf, summary


def trade_metrics(pnls: np.ndarray, traded: np.ndarray | None = None) -> dict:
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


def tuesday_overlay(wf: pd.DataFrame, k: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    pred = wf.set_index("decision_t_utc")
    rows = []
    parity = tue.historical_parity(k)
    if not parity.get("pass"):
        raise RuntimeError("A5.11 parity failed before Tuesday overlay: " + json.dumps(parity, default=str))

    for t in tue.entries(k):
        if t not in pred.index:
            continue
        p = pred.loc[t]
        tr = tue.simulate_parent(k, t)
        lr = tue.layered(k, tr)
        rows.append({
            "date_wib": str((t + pd.Timedelta(hours=7)).date()),
            "decision_t_utc": t,
            "predicted": str(p.predicted),
            "p_buy": float(p.p_buy),
            "p_neutral": float(p.p_neutral),
            "p_sell": float(p.p_sell),
            "trade": bool(p.predicted == "SELL_COMPATIBLE"),
            "a511_pnl": float(lr["a511_pnl"]),
            "a511_win": bool(lr["a511_pnl"] > 0),
        })
    td = pd.DataFrame(rows).sort_values("decision_t_utc").reset_index(drop=True)
    pnls = td.a511_pnl.to_numpy(float)
    trades = td.trade.to_numpy(bool)
    base = trade_metrics(pnls)
    gate = trade_metrics(pnls, trades)

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = trade_metrics(x.a511_pnl.to_numpy(float))
        xg = trade_metrics(x.a511_pnl.to_numpy(float), x.trade.to_numpy(bool))
        blocks.append({
            "block": b,
            "start": x.iloc[0].date_wib,
            "end": x.iloc[-1].date_wib,
            "baseline": xb,
            "gated": xg,
            "pnl_delta": float(xg["pnl"] - xb["pnl"]),
        })

    checks = {
        "coverage_ge_35pct": bool(gate["coverage"] >= 0.35),
        "exp_per_opportunity_improves": bool(gate["exp_per_opportunity"] > base["exp_per_opportunity"]),
        "total_pnl_ge_baseline": bool(gate["pnl"] >= base["pnl"]),
        "trade_wr_improves": bool(gate["trade_wr"] > base["trade_wr"]),
        "positive_delta_3_of_4_blocks": bool(sum(x["pnl_delta"] > 0 for x in blocks) >= 3),
    }
    summary = {
        "a511_parity": parity,
        "baseline": base,
        "gated": gate,
        "blocks": blocks,
        "promotion_checks": checks,
        "shadow_candidate_pass": bool(all(checks.values())),
    }
    return td, summary


def fit_final_model(hist: pd.DataFrame) -> Pipeline:
    model = make_model()
    model.fit(hist[FEATURES], hist.label)
    return model


def august_batch(hist: pd.DataFrame, k: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    model = fit_final_model(hist)
    kprep = g0.prepare(k)
    times = tue.entries(kprep, pd.Timestamp("2026-08-01", tz="UTC"), pd.Timestamp("2026-08-19", tz="UTC"))
    rows = []
    for t in times:
        feat, ferr = g0fast.feature_row_fast(kprep, t)
        if ferr:
            raise RuntimeError(f"August feature error {t}: {ferr}")
        X = pd.DataFrame([{f: feat[f] for f in FEATURES}])
        p = normalize_proba(model, X)[0]
        hard = CLASSES[int(np.argmax(p))]
        label, reason, hit_min = g0fast.label_row_fast(kprep, t)
        tr = tue.simulate_parent(kprep, t)
        lr = tue.layered(kprep, tr)
        rows.append({
            "date_wib": str((t + pd.Timedelta(hours=7)).date()),
            "decision_t_utc": t,
            "p_buy": float(p[CLASSES.index("BUY_COMPATIBLE")]),
            "p_neutral": float(p[CLASSES.index("NEUTRAL")]),
            "p_sell": float(p[CLASSES.index("SELL_COMPATIBLE")]),
            "predicted": hard,
            "trade": bool(hard == "SELL_COMPATIBLE"),
            "actual_g0_label": label,
            "actual_g0_reason": reason,
            "first_hit_min": hit_min,
            "a511_pnl": float(lr["a511_pnl"]),
        })
    aug = pd.DataFrame(rows)
    if aug.date_wib.tolist() != EXPECTED_AUG:
        raise RuntimeError(f"unexpected August dates: {aug.date_wib.tolist()}")
    summary = {
        "n": int(len(aug)),
        "trades": int(aug.trade.sum()),
        "waits": int((~aug.trade).sum()),
        "gated_pnl": float(aug.loc[aug.trade, "a511_pnl"].sum()),
        "always_trade_pnl": float(aug.a511_pnl.sum()),
        "correct_regime": int((aug.predicted == aug.actual_g0_label).sum()),
    }
    return aug, summary


def model_state(hist: pd.DataFrame) -> dict:
    model = fit_final_model(hist)
    imp = model.named_steps["imputer"]
    sc = model.named_steps["scale"]
    lr = model.named_steps["logit"]
    return {
        "features": FEATURES,
        "classes": list(lr.classes_),
        "imputer_medians": {f: float(v) for f, v in zip(FEATURES, imp.statistics_)},
        "scaler_mean": {f: float(v) for f, v in zip(FEATURES, sc.mean_)},
        "scaler_scale": {f: float(v) for f, v in zip(FEATURES, sc.scale_)},
        "coefficients": {
            c: {f: float(v) for f, v in zip(FEATURES, coef)} for c, coef in zip(lr.classes_, lr.coef_)
        },
        "intercepts": {c: float(v) for c, v in zip(lr.classes_, lr.intercept_)},
        "training_n": int(len(hist)),
        "training_end_exclusive": str(HIST_END),
        "model": "median -> standardize -> L2 multinomial logistic C=1 lbfgs",
    }


def main() -> None:
    hist = load_g0()
    wf, pooled = walkforward(hist)

    # Load the frozen raw lineage only after pooled model scoring is complete.
    # It is used for A5.11 parity/overlay and the report-only August batch.
    k = tue.load_extended()
    td, overlay = tuesday_overlay(wf, k)
    aug, aug_summary = august_batch(hist, k)
    state = model_state(hist)

    overall = {
        "status": (
            "G1_POOLED_PASS_TUESDAY_SHADOW_PASS" if pooled["pass"] and overlay["shadow_candidate_pass"]
            else "G1_POOLED_PASS_TUESDAY_SHADOW_FAIL" if pooled["pass"]
            else "G1_POOLED_GATE_FAILED"
        ),
        "preregistration": "BTC_Global_Regime_G1_Preregistration.md",
        "pooled": pooled,
        "tuesday_overlay": overlay,
        "august_report_only": aug_summary,
        "guardrail": "No G1 tuning after result; August report-only; live BBC untouched.",
    }

    wf.to_csv(OUT / "g1_pooled_walkforward_predictions.csv", index=False)
    td.to_csv(OUT / "g1_tuesday_overlay.csv", index=False)
    aug.to_csv(OUT / "g1_august_tuesday.csv", index=False)
    (OUT / "g1_summary.json").write_text(json.dumps(overall, indent=2, default=str))
    (OUT / "g1_final_model_state.json").write_text(json.dumps(state, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    ps = pooled["model"]
    bs = pooled["baseline"]
    ob = overlay["baseline"]
    og = overlay["gated"]
    lines = [
        "# BTC Global/Pooled Regime Engine — G1 Result",
        "",
        f"**Status: {overall['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Pooled embargoed walk-forward",
        f"- Pseudo-OOS states: **{ps['n']:,}**",
        f"- Accuracy: **{pct(ps['accuracy'])}** (prior baseline {pct(bs['accuracy'])})",
        f"- Balanced accuracy: **{pct(ps['balanced_accuracy'])}**",
        f"- Macro F1: **{ps['macro_f1']:.4f}**",
        f"- Log loss: **{ps['log_loss']:.6f}** (prior {bs['log_loss']:.6f})",
        f"- Brier: **{ps['brier']:.6f}** (prior {bs['brier']:.6f})",
        f"- SELL-vs-rest AUC: **{ps['sell_auc']:.4f}**",
        f"- Hard-predicted SELL coverage: **{pct(pooled['predicted_sell_coverage'])}**",
        f"- Actual SELL rate overall: **{pct(pooled['actual_sell_rate'])}**",
        f"- Actual SELL rate when model predicts SELL: **{pct(pooled['predicted_sell_precision'])}**",
        f"- SELL enrichment: **{pooled['sell_enrichment_pp']:+.2f} pp**",
        "",
        "### Pooled acceptance gate",
    ]
    for name, ok in pooled["acceptance_checks"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")

    lines += [
        "",
        "### Four chronological pooled blocks",
        "| Block | Dates | Model LL | Prior LL | Improved | Model Brier | Prior Brier |",
        "|---:|---|---:|---:|---|---:|---:|",
    ]
    for b in pooled["blocks"]:
        lines.append(
            f"| {b['block']} | {b['start']} → {b['end']} | {b['model_log_loss']:.5f} | {b['baseline_log_loss']:.5f} | {'YES' if b['logloss_improved'] else 'NO'} | {b['model_brier']:.5f} | {b['baseline_brier']:.5f} |"
        )

    lines += [
        "",
        "## Frozen Tuesday A5.11 overlay",
        f"- Opportunities: **{ob['opportunities']}**",
        f"- Always trade: WR **{pct(ob['trade_wr'])}**, PnL **${ob['pnl']:+.2f}**, exp/oppty **${ob['exp_per_opportunity']:+.4f}**, PF **{ob['pf']:.3f}**, DD **${ob['max_dd']:.2f}**",
        f"- Regime gate: {og['trades']} trades / {og['waits']} waits ({pct(og['coverage'])} coverage), WR **{pct(og['trade_wr'])}**, PnL **${og['pnl']:+.2f}**, exp/oppty **${og['exp_per_opportunity']:+.4f}**, PF **{og['pf']:.3f}**, DD **${og['max_dd']:.2f}**",
        f"- PnL delta: **${og['pnl'] - ob['pnl']:+.2f}**",
        "",
        "### Tuesday shadow promotion gate",
    ]
    for name, ok in overlay["promotion_checks"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")

    lines += [
        "",
        "### Tuesday chronological blocks",
        "| Block | Dates | Baseline PnL | Gated PnL | Delta |",
        "|---:|---|---:|---:|---:|",
    ]
    for b in overlay["blocks"]:
        lines.append(
            f"| {b['block']} | {b['start']} → {b['end']} | ${b['baseline']['pnl']:+.2f} | ${b['gated']['pnl']:+.2f} | ${b['pnl_delta']:+.2f} |"
        )

    lines += [
        "",
        "## August 2026 — report only",
        "| Date WIB | pSELL | Predicted | Decision | Actual G0 regime | A5.11 PnL |",
        "|---|---:|---|---|---|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(
            f"| {r['date_wib']} | {100*r['p_sell']:.1f}% | {r['predicted']} | {'TRADE' if r['trade'] else 'WAIT'} | {r['actual_g0_label']} | ${r['a511_pnl']:+.2f} |"
        )

    lines += [
        "",
        f"**Pooled model gate: {'PASS' if pooled['pass'] else 'FAIL'}. Tuesday shadow gate: {'PASS' if overlay['shadow_candidate_pass'] else 'FAIL'}.**",
        "",
        "No result in this report changes live BBC automatically.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G1_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(overall, indent=2, default=str))


if __name__ == "__main__":
    main()
