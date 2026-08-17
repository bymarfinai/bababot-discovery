#!/usr/bin/env python3
"""S6.2 — Frozen Low-Dimensional Saturday Direction Candidate Test.

Research only; live BBC untouched.

Frozen candidate from S6.1:
- dist_4h_high : extension/location
- ret60        : momentum
- rv4h         : quietness/activity

Model:
- L2 logistic regression, C=1.0, class_weight=None, threshold=0.50
- StandardScaler fit on TRAIN ONLY
- target = SHORT_BETTER (static mirrored SHORT PnL > frozen static BUY PnL)
- no feature selection, threshold sweep, hyperparameter search, or abstention

Causal evaluation:
- rows 0:54 are warm-up only (55 Saturdays)
- Fold 1: train 0:54, test 55:82
- Fold 2: train 0:82, test 83:110
- Fold 3: train 0:110, test 111:138
Every evaluated Saturday must select BUY or SELL; no skip.

Dedicated frozen holdout:
- train discovery 0:82, test validation 83:138

This milestone evaluates direction selection only under the static TP2.6/SL1.2/max18h
geometry. Frozen S5.7G post-entry management is deliberately NOT combined yet.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import s50_saturday_parent_forensics as s50
import s60_saturday_dynamic_direction_oracle as s60
import s61_preentry_direction_feature_atlas as s61

OUT = Path(os.getenv("S62_OUT", "s62_out"))
OUT.mkdir(parents=True, exist_ok=True)

FEATURES = ["dist_4h_high", "ret60", "rv4h"]
EXPECTED_SIGNS = {"dist_4h_high": 1, "ret60": 1, "rv4h": -1}
WARMUP = 55
FOLDS = [(55, 83), (83, 111), (111, 139)]
DISC_END = 83


def metrics(pnls):
    p = np.asarray(pnls, dtype=float)
    n = len(p)
    wins = int((p > 0).sum())
    pos = float(p[p > 0].sum())
    neg = float(-p[p <= 0].sum())
    eq = np.cumsum(p)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = float((peak[1:] - eq).max()) if n else 0.0
    ls = cur = 0
    for x in p:
        if x <= 0:
            cur += 1; ls = max(ls, cur)
        else:
            cur = 0
    return {
        "n": int(n), "wins": wins, "losses": int(n-wins),
        "wr": float(wins/n) if n else np.nan,
        "pnl": float(p.sum()), "expectancy": float(p.mean()) if n else np.nan,
        "pf": float(pos/neg) if neg > 0 else float("inf"),
        "max_dd": dd, "loss_streak": int(ls),
    }


def build_dataset():
    k = s50.load_klines().copy()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    longs = [s50.simulate(k, f, t) for t in entries]
    shorts = [s60.simulate_short(k, f, t) for t in entries]
    if len(entries) != 139 or abs(sum(x.pnl for x in longs) - 87.199692) > .02:
        raise RuntimeError("parent parity fail")

    recs = []
    for i, (t, lg, sh) in enumerate(zip(entries, longs, shorts)):
        r = {
            "idx": i, "date": lg.date, "entry_t": str(t),
            "buy_pnl": float(lg.pnl), "short_pnl": float(sh.pnl),
            "buy_win": bool(lg.pnl > 0), "short_win": bool(sh.pnl > 0),
            "short_better": bool(sh.pnl > lg.pnl),
            "oracle_best_pnl": float(max(lg.pnl, sh.pnl)),
        }
        pf = s61.pre_features(k, t)
        for feat in FEATURES:
            r[feat] = float(pf[feat])
        recs.append(r)
    df = pd.DataFrame(recs)
    if df[FEATURES].isna().any().any():
        raise RuntimeError("missing frozen features")
    return df


def make_model():
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=1000,
            class_weight=None, random_state=0,
        )),
    ])


def fit_predict(train, test):
    Xtr = train[FEATURES].to_numpy(float)
    ytr = train.short_better.astype(int).to_numpy()
    Xte = test[FEATURES].to_numpy(float)
    model = make_model()
    model.fit(Xtr, ytr)
    prob = model.predict_proba(Xte)[:, 1]
    pred_short = prob >= 0.50
    coefs = model.named_steps["clf"].coef_[0]
    return model, prob, pred_short, coefs


def selected_pnl(g, pred_short):
    return np.where(pred_short, g.short_pnl.to_numpy(float), g.buy_pnl.to_numpy(float))


def baseline_bundle(g):
    return {
        "always_buy": metrics(g.buy_pnl.to_numpy(float)),
        "always_short": metrics(g.short_pnl.to_numpy(float)),
        "oracle_best": metrics(g.oracle_best_pnl.to_numpy(float)),
    }


def main():
    df = build_dataset()
    df.to_csv(OUT / "s62_dataset.csv", index=False)

    fold_rows = []
    pred_rows = []
    coef_rows = []

    for fold_id, (lo, hi) in enumerate(FOLDS, start=1):
        train = df.iloc[:lo].copy()
        test = df.iloc[lo:hi].copy()
        model, prob, pred_short, coefs = fit_predict(train, test)
        sp = selected_pnl(test, pred_short)
        selected = metrics(sp)
        base = baseline_bundle(test)
        direction_acc = float((pred_short == test.short_better.to_numpy(bool)).mean())
        decisive = (test.buy_win.to_numpy(bool) ^ test.short_win.to_numpy(bool))
        decisive_correct = float((pred_short[decisive] == test.short_win.to_numpy(bool)[decisive]).mean()) if decisive.any() else np.nan

        fold_rows.append({
            "fold": fold_id, "train_n": len(train), "test_lo": lo, "test_hi_exclusive": hi,
            "test_n": len(test), "selected_wins": selected["wins"], "selected_wr": selected["wr"],
            "selected_pnl": selected["pnl"], "selected_pf": selected["pf"],
            "buy_wr": base["always_buy"]["wr"], "buy_pnl": base["always_buy"]["pnl"],
            "short_wr": base["always_short"]["wr"], "short_pnl": base["always_short"]["pnl"],
            "oracle_wr": base["oracle_best"]["wr"], "oracle_pnl": base["oracle_best"]["pnl"],
            "direction_accuracy": direction_acc, "decisive_direction_accuracy": decisive_correct,
            "short_selected_n": int(pred_short.sum()), "buy_selected_n": int((~pred_short).sum()),
        })
        for feat, coef in zip(FEATURES, coefs):
            coef_rows.append({"fold": fold_id, "train_n": len(train), "feature": feat,
                              "coef_standardized": float(coef),
                              "expected_sign": EXPECTED_SIGNS[feat],
                              "sign_matches": bool(np.sign(coef) == EXPECTED_SIGNS[feat])})
        for j, (_, r) in enumerate(test.iterrows()):
            pred_rows.append({
                "fold": fold_id, "idx": int(r.idx), "date": r.date,
                "prob_short": float(prob[j]), "selected": "SHORT" if pred_short[j] else "BUY",
                "short_better": bool(r.short_better),
                "buy_pnl": float(r.buy_pnl), "short_pnl": float(r.short_pnl),
                "selected_pnl": float(sp[j]),
                "winner_selected": bool(sp[j] > 0),
                **{feat: float(r[feat]) for feat in FEATURES},
            })

    folds = pd.DataFrame(fold_rows)
    folds.to_csv(OUT / "s62_walkforward_folds.csv", index=False)
    preds = pd.DataFrame(pred_rows).sort_values("idx")
    preds.to_csv(OUT / "s62_walkforward_predictions.csv", index=False)
    coefs = pd.DataFrame(coef_rows)
    coefs.to_csv(OUT / "s62_coefficients.csv", index=False)

    wf_g = df[df.idx >= WARMUP].copy()
    if len(preds) != len(wf_g) or preds.idx.tolist() != wf_g.idx.tolist():
        raise RuntimeError("walk-forward coverage parity fail")
    wf_selected = metrics(preds.selected_pnl.to_numpy(float))
    wf_base = baseline_bundle(wf_g)
    wf_direction_acc = float((preds.selected.eq("SHORT").to_numpy() == wf_g.short_better.to_numpy(bool)).mean())
    wf_decisive = (wf_g.buy_win.to_numpy(bool) ^ wf_g.short_win.to_numpy(bool))
    wf_decisive_acc = float((preds.selected.eq("SHORT").to_numpy()[wf_decisive] == wf_g.short_win.to_numpy(bool)[wf_decisive]).mean())

    # Dedicated fixed discovery -> validation holdout.
    train = df.iloc[:DISC_END].copy()
    val = df.iloc[DISC_END:].copy()
    _, vprob, vpred_short, vcoefs = fit_predict(train, val)
    vsp = selected_pnl(val, vpred_short)
    val_selected = metrics(vsp)
    val_base = baseline_bundle(val)
    val_dir_acc = float((vpred_short == val.short_better.to_numpy(bool)).mean())
    val_decisive = (val.buy_win.to_numpy(bool) ^ val.short_win.to_numpy(bool))
    val_dec_acc = float((vpred_short[val_decisive] == val.short_win.to_numpy(bool)[val_decisive]).mean())
    val_rows = val[["idx", "date", "buy_pnl", "short_pnl", "short_better", *FEATURES]].copy()
    val_rows["prob_short"] = vprob
    val_rows["selected"] = np.where(vpred_short, "SHORT", "BUY")
    val_rows["selected_pnl"] = vsp
    val_rows.to_csv(OUT / "s62_validation_predictions.csv", index=False)

    # Predeclared candidate gate. This is NOT a 70% gate.
    wf_wr_beats = wf_selected["wr"] > max(wf_base["always_buy"]["wr"], wf_base["always_short"]["wr"])
    wf_pnl_beats = wf_selected["pnl"] > max(wf_base["always_buy"]["pnl"], wf_base["always_short"]["pnl"])
    val_pnl_beats = val_selected["pnl"] > max(val_base["always_buy"]["pnl"], val_base["always_short"]["pnl"])
    mechanism_signs = {}
    for feat in FEATURES:
        x = coefs[coefs.feature == feat]
        mechanism_signs[feat] = int(x.sign_matches.sum())
    mechanism_ok = all(v >= 2 for v in mechanism_signs.values())
    causal_candidate_pass = bool(wf_wr_beats and wf_pnl_beats and val_pnl_beats and mechanism_ok)

    summary = {
        "frozen_features": FEATURES,
        "model": {"type": "StandardScaler + L2 LogisticRegression", "C": 1.0, "threshold": 0.5},
        "walkforward": {
            "warmup_n": WARMUP, "evaluated_n": int(len(wf_g)),
            "selected": wf_selected, "baselines": wf_base,
            "direction_accuracy": wf_direction_acc,
            "decisive_direction_accuracy": wf_decisive_acc,
            "short_selected_n": int(preds.selected.eq("SHORT").sum()),
            "buy_selected_n": int(preds.selected.eq("BUY").sum()),
            "folds": fold_rows,
        },
        "validation_83_138": {
            "train_n": DISC_END, "test_n": int(len(val)),
            "selected": val_selected, "baselines": val_base,
            "direction_accuracy": val_dir_acc,
            "decisive_direction_accuracy": val_dec_acc,
            "short_selected_n": int(vpred_short.sum()), "buy_selected_n": int((~vpred_short).sum()),
            "coefficients": {feat: float(c) for feat, c in zip(FEATURES, vcoefs)},
        },
        "mechanism_sign_match_counts_3folds": mechanism_signs,
        "gate_components": {
            "wf_wr_beats_both_baselines": bool(wf_wr_beats),
            "wf_pnl_beats_both_baselines": bool(wf_pnl_beats),
            "validation_pnl_beats_both_baselines": bool(val_pnl_beats),
            "mechanism_signs_match_at_least_2_of_3": bool(mechanism_ok),
        },
        "causal_candidate_pass": causal_candidate_pass,
    }
    (OUT / "s62_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x): return f"{100*x:.2f}%"
    def money(x): return f"${x:+.3f}"
    md = [
        "# BTC Temporal Saturday S6.2 — Frozen Low-Dimensional Direction Candidate Test",
        "",
        "**Status:** COMPLETE — CAUSAL WALK-FORWARD DIRECTION TEST; STATIC MANAGEMENT ONLY",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen candidate",
        "- Features: `dist_4h_high`, `ret60`, `rv4h`.",
        "- Model: StandardScaler + L2 logistic regression, C=1.0, probability threshold 0.50.",
        "- Target: `SHORT_BETTER`.",
        "- No threshold/hyperparameter/feature sweep, no abstention, no post-entry feature.",
        "",
        "## Expanding walk-forward",
        f"- Warm-up: first **{WARMUP}** trades (not scored).",
        f"- Future-scored trades: **{len(wf_g)}**, every one forced BUY or SELL.",
        f"- Selected: **{wf_selected['wins']}/{wf_selected['n']} = {pct(wf_selected['wr'])} WR**, PnL **{money(wf_selected['pnl'])}**, PF **{wf_selected['pf']:.3f}**, DD **{wf_selected['max_dd']:.3f}**, LS **{wf_selected['loss_streak']}**.",
        f"- Always BUY same 84: **{pct(wf_base['always_buy']['wr'])}**, {money(wf_base['always_buy']['pnl'])}.",
        f"- Always SHORT same 84: **{pct(wf_base['always_short']['wr'])}**, {money(wf_base['always_short']['pnl'])}.",
        f"- Hindsight best-direction ceiling same 84: **{pct(wf_base['oracle_best']['wr'])}**, {money(wf_base['oracle_best']['pnl'])}.",
        f"- Direction accuracy vs SHORT_BETTER: **{pct(wf_direction_acc)}**; decisive-only direction accuracy **{pct(wf_decisive_acc)}**.",
        f"- Selected BUY/SHORT: **{int(preds.selected.eq('BUY').sum())}/{int(preds.selected.eq('SHORT').sum())}**.",
        "",
        "### Fold results",
    ]
    for r in fold_rows:
        md.append(
            f"- Fold {r['fold']} train {r['train_n']} -> test {r['test_n']}: selected **{pct(r['selected_wr'])} / {money(r['selected_pnl'])}**, BUY {pct(r['buy_wr'])}/{money(r['buy_pnl'])}, SHORT {pct(r['short_wr'])}/{money(r['short_pnl'])}, direction acc {pct(r['direction_accuracy'])}."
        )
    md += [
        "",
        "## Frozen discovery -> validation holdout",
        f"- Train **83**, test **56**.",
        f"- Selected: **{val_selected['wins']}/{val_selected['n']} = {pct(val_selected['wr'])} WR**, PnL **{money(val_selected['pnl'])}**, PF **{val_selected['pf']:.3f}**.",
        f"- Always BUY validation: **{pct(val_base['always_buy']['wr'])} / {money(val_base['always_buy']['pnl'])}**.",
        f"- Always SHORT validation: **{pct(val_base['always_short']['wr'])} / {money(val_base['always_short']['pnl'])}**.",
        f"- Direction accuracy **{pct(val_dir_acc)}**; decisive-only **{pct(val_dec_acc)}**.",
        "",
        "## Mechanism sign stability",
    ]
    for feat in FEATURES:
        vals = coefs[coefs.feature == feat].sort_values("fold")
        md.append(f"- `{feat}` expected {'+' if EXPECTED_SIGNS[feat] > 0 else '-'}; signs matched **{mechanism_signs[feat]}/3** folds; coefficients: " + ", ".join(f"{x:.3f}" for x in vals.coef_standardized))
    md += [
        "",
        "## Predeclared causal-candidate gate",
        f"- WF WR beats both baselines: **{wf_wr_beats}**",
        f"- WF PnL beats both baselines: **{wf_pnl_beats}**",
        f"- Validation PnL beats both baselines: **{val_pnl_beats}**",
        f"- Mechanism signs match >=2/3 folds for all features: **{mechanism_ok}**",
        f"- **CAUSAL CANDIDATE PASS: {causal_candidate_pass}**",
        "",
        "## Interpretation rule",
        "This result is direction-selection evidence only. It must not be combined post hoc with S5.7G in this milestone. If the frozen candidate passes, the next clean step is robustness / alternative train-window testing without changing the feature set or model definition; only after that should the already-frozen post-entry management layer be stacked on top.",
    ]
    (OUT / "S6.2_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
