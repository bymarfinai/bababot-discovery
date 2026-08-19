#!/usr/bin/env python3
"""Tuesday anchored walk-forward TRADE/WAIT engine.

Purpose
-------
Test whether the Tuesday 06:00 WIB SELL prior can generalize when entry quality is
learned causally from prior Tuesdays only, rather than by repeatedly fitting a
static filter on the full 971-day history.

Research only; live BBC untouched.

Predeclared design
------------------
- Frozen execution/outcome = Tuesday A5.11 stack unchanged:
  SELL 06:00 WIB, TP1.35%, SL0.80%, hold6h + A5.2 + A5.9 + A5.11.
- Expanding/anchored walk-forward; NO random split.
- Warmup = first 52 historical Tuesdays.
- At Tuesday i, train only on Tuesdays [0, i).
- Target = whether frozen A5.11 net PnL > 0.
- All 15 pre-entry continuous features from the previously declared causal
  Tuesday atlas are included; there is NO feature selection here.
- Model = median imputation -> standardization -> L2 logistic regression C=1.
- Primary decision threshold is fixed ex ante at p(win) >= 0.50 = TRADE,
  otherwise WAIT. 0.55/0.60 are sensitivity reports only and may NOT replace
  the primary rule based on their results.
- August 4/11/18 are scored only after historical walk-forward is complete.
  One model frozen at the Jul-30 historical cutoff is applied to all three;
  no August outcome is used to refit between those dates.

Important limitation
--------------------
The historical Tuesday sample and feature vocabulary have prior research
exposure. This experiment removes future leakage from the model-fitting path,
but it is pseudo-OOS / walk-forward evidence, not pristine untouched OOS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import tuesday_a511_true_oos_august as tue
import tuesday_august_failure_forensics as featmod

OUT = Path(os.getenv("TUEWF_OUT", "tuewf_out"))
OUT.mkdir(parents=True, exist_ok=True)

WARMUP = 52
PRIMARY_THRESHOLD = 0.50
SENSITIVITY_THRESHOLDS = [0.55, 0.60]
FEATURES = [
    "ret1h", "ret3h", "ret6h", "ret12h", "ret24h", "mon_ret", "overnight_ret",
    "ema_spread", "dist_ema20", "ema20_slope1h", "loc24", "range6", "range24",
    "taker1h", "taker4h",
]


def metrics_opportunity(pnls: np.ndarray, traded: np.ndarray | None = None) -> dict:
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
        "pf": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else None),
        "exp_per_opportunity": float(realized.mean()) if len(realized) else None,
        "exp_per_trade": float(x.mean()) if len(x) else None,
        "max_dd": dd,
    }


def make_model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=2000,
            class_weight=None, random_state=7,
        )),
    ])


def historical_frame(k: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    parity = tue.historical_parity(k)
    if not parity["pass"]:
        raise RuntimeError("A5.11 historical parity failed: " + json.dumps(parity, default=str))

    rows = []
    for i, t in enumerate(tue.entries(k)):
        tr = tue.simulate_parent(k, t)
        lr = tue.layered(k, tr)
        fr = featmod.feature_row(k, t)
        rows.append({
            "i": i,
            "date": str((t + pd.Timedelta(hours=7)).date()),
            "entry_t": t,
            "a511_pnl": float(lr["a511_pnl"]),
            "win": bool(lr["a511_pnl"] > 0),
            "mfe": float(tr["mfe"]),
            "developed": bool(tr["mfe"] >= tue.HINGE),
            **{f: float(fr[f]) for f in FEATURES},
        })
    df = pd.DataFrame(rows)
    if len(df) != 139:
        raise RuntimeError(f"expected 139 historical Tuesdays, got {len(df)}")
    return df, parity


def run_walkforward(hist: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    coef_history = []
    for i in range(WARMUP, len(hist)):
        train = hist.iloc[:i]
        test = hist.iloc[[i]]
        Xtr = train[FEATURES]
        ytr = train["win"].astype(int)
        if ytr.nunique() < 2:
            raise RuntimeError(f"single-class training set at i={i}")

        model = make_model()
        model.fit(Xtr, ytr)
        p = float(model.predict_proba(test[FEATURES])[:, 1][0])

        # store standardized model coefficients for stability audit
        coefs = model.named_steps["logit"].coef_[0]
        coef_history.append({"i": i, **{f: float(c) for f, c in zip(FEATURES, coefs)}})

        r = test.iloc[0]
        rec = {
            "i": int(i),
            "date": r["date"],
            "entry_t": str(r["entry_t"]),
            "train_n": int(i),
            "train_win_rate": float(ytr.mean()),
            "pred_win_p": p,
            "actual_win": bool(r["win"]),
            "actual_a511_pnl": float(r["a511_pnl"]),
            "developed": bool(r["developed"]),
            "mfe": float(r["mfe"]),
            "trade_p50": bool(p >= PRIMARY_THRESHOLD),
        }
        for th in SENSITIVITY_THRESHOLDS:
            rec[f"trade_p{int(th*100)}"] = bool(p >= th)
        rows.append(rec)

    wf = pd.DataFrame(rows)
    if len(wf) != len(hist) - WARMUP:
        raise RuntimeError("walk-forward row count mismatch")

    pnls = wf.actual_a511_pnl.to_numpy(float)
    summary = {
        "baseline_all_trade": metrics_opportunity(pnls),
        "primary_p50": metrics_opportunity(pnls, wf.trade_p50.to_numpy(bool)),
    }
    for th in SENSITIVITY_THRESHOLDS:
        summary[f"sensitivity_p{int(th*100)}"] = metrics_opportunity(
            pnls, wf[f"trade_p{int(th*100)}"].to_numpy(bool)
        )

    # Chronological blocks are report-only, no block can change the primary rule.
    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(wf)), 4), start=1):
        x = wf.iloc[idx]
        blocks.append({
            "block": b,
            "start": x.iloc[0].date,
            "end": x.iloc[-1].date,
            "baseline": metrics_opportunity(x.actual_a511_pnl.to_numpy(float)),
            "primary": metrics_opportunity(x.actual_a511_pnl.to_numpy(float), x.trade_p50.to_numpy(bool)),
        })
    summary["blocks"] = blocks

    years = []
    tmp = wf.copy()
    tmp["year"] = pd.to_datetime(tmp.date).dt.year
    for y, x in tmp.groupby("year"):
        years.append({
            "year": int(y),
            "baseline": metrics_opportunity(x.actual_a511_pnl.to_numpy(float)),
            "primary": metrics_opportunity(x.actual_a511_pnl.to_numpy(float), x.trade_p50.to_numpy(bool)),
        })
    summary["years"] = years

    # Model quality diagnostics, not selection criteria.
    y = wf.actual_win.astype(int).to_numpy()
    p = wf.pred_win_p.to_numpy(float)
    summary["brier"] = float(np.mean((p - y) ** 2))
    summary["mean_pred_p"] = float(p.mean())
    summary["actual_win_rate"] = float(y.mean())

    ch = pd.DataFrame(coef_history)
    coef_stability = []
    for f in FEATURES:
        vals = ch[f].to_numpy(float)
        coef_stability.append({
            "feature": f,
            "median_coef": float(np.median(vals)),
            "positive_share": float((vals > 0).mean()),
            "negative_share": float((vals < 0).mean()),
            "last_coef": float(vals[-1]),
        })
    summary["coefficient_stability"] = coef_stability
    return wf, summary


def august_batch_holdout(k: pd.DataFrame, hist: pd.DataFrame) -> tuple[pd.DataFrame, dict, dict]:
    # One model trained on historical data ending Jul-30 and frozen for all August observations.
    model = make_model()
    model.fit(hist[FEATURES], hist.win.astype(int))

    aes = tue.entries(k, pd.Timestamp("2026-08-01", tz="UTC"), pd.Timestamp("2026-08-19", tz="UTC"))
    rows = []
    for t in aes:
        tr = tue.simulate_parent(k, t)
        lr = tue.layered(k, tr)
        fr = featmod.feature_row(k, t)
        X = pd.DataFrame([{f: float(fr[f]) for f in FEATURES}])
        p = float(model.predict_proba(X)[:, 1][0])
        rows.append({
            "date": str((t + pd.Timedelta(hours=7)).date()),
            "entry_t": str(t),
            "pred_win_p": p,
            "trade_p50": bool(p >= PRIMARY_THRESHOLD),
            "actual_a511_pnl": float(lr["a511_pnl"]),
            "actual_win": bool(lr["a511_pnl"] > 0),
            "mfe": float(tr["mfe"]),
            "developed": bool(tr["mfe"] >= tue.HINGE),
        })
    aug = pd.DataFrame(rows)
    if aug.date.tolist() != ["2026-08-04", "2026-08-11", "2026-08-18"]:
        raise RuntimeError(f"unexpected August dates: {aug.date.tolist()}")

    pnls = aug.actual_a511_pnl.to_numpy(float)
    summary = {
        "baseline_all_trade": metrics_opportunity(pnls),
        "primary_p50": metrics_opportunity(pnls, aug.trade_p50.to_numpy(bool)),
    }

    # Persist final model state in transparent JSON-friendly form for reproducibility/shadow use.
    imp = model.named_steps["imputer"]
    scale = model.named_steps["scale"]
    logit = model.named_steps["logit"]
    state = {
        "features": FEATURES,
        "imputer_medians": {f: float(v) for f, v in zip(FEATURES, imp.statistics_)},
        "scaler_mean": {f: float(v) for f, v in zip(FEATURES, scale.mean_)},
        "scaler_scale": {f: float(v) for f, v in zip(FEATURES, scale.scale_)},
        "logit_coef": {f: float(v) for f, v in zip(FEATURES, logit.coef_[0])},
        "logit_intercept": float(logit.intercept_[0]),
        "decision_threshold": PRIMARY_THRESHOLD,
        "training_n": int(len(hist)),
        "training_end": "2026-07-30 UTC cutoff",
    }
    return aug, summary, state


def fmt_pct(v):
    return "-" if v is None else f"{100*v:.1f}%"


def main():
    k = tue.load_extended()
    hist, parity = historical_frame(k)
    wf, wf_summary = run_walkforward(hist)
    aug, aug_summary, model_state = august_batch_holdout(k, hist)

    primary = wf_summary["primary_p50"]
    base = wf_summary["baseline_all_trade"]
    historical_pass = bool(
        primary["trades"] >= 30
        and primary["pnl"] > 0
        and primary["pf"] is not None and primary["pf"] > 1.0
        and sum(1 for b in wf_summary["blocks"] if b["primary"]["pnl"] > 0) >= 3
    )

    summary = {
        "status": "COMPLETE_TUESDAY_ANCHORED_WALKFORWARD_TRADE_WAIT",
        "design": {
            "warmup_tuesdays": WARMUP,
            "walkforward_opportunities": int(len(wf)),
            "model": "median imputer + StandardScaler + L2 LogisticRegression(C=1)",
            "target": "frozen A5.11 net PnL > 0",
            "primary_threshold": PRIMARY_THRESHOLD,
            "sensitivity_thresholds_report_only": SENSITIVITY_THRESHOLDS,
            "features": FEATURES,
            "feature_selection": "NONE; fixed full causal feature set",
            "random_split": False,
        },
        "historical_parity": parity,
        "walkforward": wf_summary,
        "historical_primary_gate": {
            "pass_minimal_robustness": historical_pass,
            "criteria": "at least 30 trades, positive PnL, PF>1, and >=3/4 positive chronological blocks; threshold/model cannot be changed based on result",
        },
        "august_batch_holdout": aug_summary,
        "model_state_jul30": model_state,
        "guardrail": (
            "Causal expanding walk-forward removes future leakage from each historical prediction, but the broader Tuesday dataset and feature vocabulary have prior research exposure. "
            "Therefore this is stronger pseudo-OOS evidence, not pristine untouched OOS. August is batch-scored with one Jul30-frozen model and is not used for model selection or refitting."
        ),
    }

    wf.to_csv(OUT / "tuesday_walkforward_predictions.csv", index=False)
    aug.to_csv(OUT / "tuesday_walkforward_august.csv", index=False)
    hist.to_csv(OUT / "tuesday_walkforward_historical_inputs.csv", index=False)
    (OUT / "tuesday_walkforward_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (OUT / "tuesday_walkforward_model_state.json").write_text(json.dumps(model_state, indent=2))

    md = [
        "# Tuesday — Anchored Walk-Forward TRADE/WAIT Engine",
        "",
        "**Status: COMPLETE — research only; live BBC untouched.**",
        "",
        "## Locked methodology",
        f"- Warmup: **{WARMUP} Tuesdays**.",
        f"- Walk-forward predictions: **{len(wf)} Tuesdays**; each prediction trains only on prior Tuesdays.",
        "- Frozen outcome/execution: Tuesday A5.11 unchanged.",
        "- Model: median imputation + standardization + L2 logistic regression, C=1.",
        "- No feature selection; all predeclared causal pre-entry features are used.",
        "- Primary rule fixed before result: **p(win) >= 0.50 => TRADE; otherwise WAIT**.",
        "- 0.55/0.60 are sensitivity diagnostics only, never candidate selectors.",
        "",
        "## Historical expanding walk-forward",
        "",
        "| Policy | Opps | Trades | Coverage | Trade WR | PnL | PF | Exp/opportunity | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    policies = [("Always trade", base), ("Primary p>=0.50", primary)]
    for th in SENSITIVITY_THRESHOLDS:
        policies.append((f"Sensitivity p>={th:.2f}", wf_summary[f"sensitivity_p{int(th*100)}"]))
    for name, m in policies:
        md.append(
            f"| {name} | {m['opportunities']} | {m['trades']} | {fmt_pct(m['coverage'])} | {fmt_pct(m['trade_wr'])} | "
            f"${m['pnl']:+.2f} | {('-' if m['pf'] is None else f'{m['pf']:.2f}')} | ${m['exp_per_opportunity']:+.3f} | ${m['max_dd']:.2f} |"
        )

    md += [
        "",
        f"Primary minimal robustness gate: **{'PASS' if historical_pass else 'FAIL'}**.",
        "",
        "### Chronological blocks — primary only",
        "",
        "| Block | Dates | Trades/Opps | WR | PnL | PF |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for b in wf_summary["blocks"]:
        m = b["primary"]
        md.append(
            f"| B{b['block']} | {b['start']} → {b['end']} | {m['trades']}/{m['opportunities']} | {fmt_pct(m['trade_wr'])} | ${m['pnl']:+.2f} | {('-' if m['pf'] is None else f'{m['pf']:.2f}')} |"
        )

    md += [
        "",
        "## August batch holdout",
        "One model is trained through the Jul-30 cutoff and then frozen across all three August Tuesdays.",
        "",
        "| Date | p(win) | Decision | A5.11 PnL | MFE |",
        "|---|---:|---|---:|---:|",
    ]
    for r in aug.itertuples(index=False):
        md.append(f"| {r.date} | {100*r.pred_win_p:.1f}% | {'TRADE' if r.trade_p50 else 'WAIT'} | ${r.actual_a511_pnl:+.2f} | {100*r.mfe:.3f}% |")
    am = aug_summary["primary_p50"]
    ab = aug_summary["baseline_all_trade"]
    md += [
        "",
        f"- August always-trade frozen A5.11: **${ab['pnl']:+.2f}**.",
        f"- August walk-forward model decisions: **{am['trades']} trades / {am['waits']} waits, PnL ${am['pnl']:+.2f}**.",
        "",
        "## Guardrail",
        summary["guardrail"],
    ]
    (OUT / "TUESDAY_WALKFORWARD_TRADE_WAIT.md").write_text("\n".join(md) + "\n")

    print(json.dumps(summary, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
