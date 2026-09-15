#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import sol_v5_batch2_activation_entry as b2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2D_STATE_TIME_DIRECTION"
TEST_YEARS = b2.TEST_YEARS
SELECT_Q = 0.90
ROUNDTRIP_COST_PCT = b2.ROUNDTRIP_COST_PCT

STATE_FEATURES = list(dict.fromkeys(
    list(b2.b1.v4.FEATURES)
    + ["pred_impulse", "state_margin", "sigma60_pct", "impulse_threshold_pct"]
))


def pfmt(v) -> str:
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def build_episode_table(x5: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    ev = b2.b1.v4.build_opportunities(x5)
    pred_state = b2.b1.causal_scores(ev)
    mapped = b2.b1.map_future_paths(x5, pred_state)
    episodes = b2.episode_starts(mapped).copy()
    episodes["state_margin"] = episodes.pred_impulse.astype(float) - episodes.state_cutoff.astype(float)
    episodes["target_up_first"] = (episodes.first_barrier.astype(str) == "UP_FIRST").astype(int)
    episodes["net60_pct"] = episodes.ret_60m_pct.astype(float) - ROUNDTRIP_COST_PCT

    miss = [c for c in STATE_FEATURES if c not in episodes.columns]
    if miss:
        raise RuntimeError(f"missing state-time features: {miss}")
    vals = episodes[STATE_FEATURES].astype(float).to_numpy()
    if not np.isfinite(vals).all():
        raise RuntimeError("non-finite state-time features")
    return episodes.sort_values("entry_time").reset_index(drop=True), float(len(mapped))


def walk_forward(episodes: pd.DataFrame):
    preds, imps = [], []
    for y in TEST_YEARS:
        train_years = b2.train_years_for(y)
        tr = episodes[episodes.test_year.isin(train_years)].copy()
        te = episodes[episodes.test_year == y].copy()
        if tr.empty or te.empty or tr.target_up_first.nunique() < 2:
            raise RuntimeError(f"bad state-time split for {y}")

        clf = b2.activation_model()
        Xtr = tr[STATE_FEATURES].astype(float).to_numpy()
        ytr = tr.target_up_first.astype(int).to_numpy()
        clf.fit(Xtr, ytr)

        train_score = clf.predict_proba(Xtr)[:, 1]
        cutoff = float(np.quantile(train_score, SELECT_Q))

        te = te.copy()
        te["state_long_score"] = clf.predict_proba(te[STATE_FEATURES].astype(float).to_numpy())[:, 1]
        te["state_long_cutoff"] = cutoff
        te["selected_long"] = te.state_long_score >= cutoff
        preds.append(te)
        imps.append(pd.DataFrame({
            "test_year": y,
            "feature": STATE_FEATURES,
            "importance": clf.feature_importances_,
        }))

    return (
        pd.concat(preds, ignore_index=True).sort_values("entry_time").reset_index(drop=True),
        pd.concat(imps, ignore_index=True),
    )


def yearly_summary(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        g = pred[pred.test_year == y].copy()
        s = g[g.selected_long].copy()
        base_up = float(g.target_up_first.mean()) if len(g) else np.nan
        sel_up = float(s.target_up_first.mean()) if len(s) else np.nan
        ee = b2.econ_returns(s.net60_pct if len(s) else pd.Series(dtype=float))
        be = b2.econ_returns(g.net60_pct if len(g) else pd.Series(dtype=float))
        auc = float(roc_auc_score(g.target_up_first.astype(int), g.state_long_score.astype(float))) if g.target_up_first.nunique() > 1 else np.nan
        rows.append({
            "test_year": y,
            "episode_n": int(len(g)),
            "baseline_up_first_rate": base_up,
            "selected_n": int(len(s)),
            "selection_rate": float(len(s)/len(g)) if len(g) else np.nan,
            "selected_up_first_rate": sel_up,
            "up_first_lift": sel_up/base_up if np.isfinite(base_up) and base_up > 0 and np.isfinite(sel_up) else np.nan,
            "auc": auc,
            "selected_wr60": ee["wr"],
            "selected_expectancy60_pct": ee["expectancy_pct"],
            "selected_pf60": ee["pf"],
            "selected_pnl60_usd": ee["net_pnl_usd"],
            "selected_max_dd_usd": ee["max_dd_usd"],
            "selected_max_ls": ee["max_ls"],
            "baseline_expectancy60_pct": be["expectancy_pct"],
            "baseline_pf60": be["pf"],
        })
    return pd.DataFrame(rows)


def main():
    b2.b1.v4.v3.v1.base.fetch_one = b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    episodes, _ = build_episode_table(x5)
    pred, imp = walk_forward(episodes)
    selected = pred[pred.selected_long].copy().sort_values("entry_time").reset_index(drop=True)

    if pred.target_up_first.nunique() < 2:
        auc = np.nan
    else:
        auc = float(roc_auc_score(pred.target_up_first.astype(int), pred.state_long_score.astype(float)))

    base_up = float(pred.target_up_first.mean())
    sel_up = float(selected.target_up_first.mean()) if len(selected) else np.nan
    lift = sel_up / base_up if base_up > 0 and np.isfinite(sel_up) else np.nan

    selected_e = b2.econ_returns(selected.net60_pct if len(selected) else pd.Series(dtype=float))
    base_e = b2.econ_returns(pred.net60_pct)
    yr = yearly_summary(pred)
    fi = imp.groupby("feature", as_index=False).importance.mean().sort_values("importance", ascending=False)
    pos_years = int((yr.selected_pnl60_usd > 0).sum())

    gates = {
        "selected_n_ge_200": int(len(selected)) >= 200,
        "oos_auc_ge_0_55": bool(np.isfinite(auc) and auc >= .55),
        "selected_up_first_ge_50pct": bool(np.isfinite(sel_up) and sel_up >= .50),
        "selected_up_first_lift_ge_1_35x": bool(np.isfinite(lift) and lift >= 1.35),
        "selected_expectancy_positive": bool(np.isfinite(selected_e["expectancy_pct"]) and selected_e["expectancy_pct"] > 0),
        "selected_pf_ge_1_10": bool(np.isfinite(selected_e["pf"]) and selected_e["pf"] >= 1.10),
        "positive_selected_pnl_years_ge_2_of_3": pos_years >= 2,
    }
    passed = bool(all(gates.values()))
    verdict = "READY_FOR_BATCH3_RISK_ENVELOPE" if passed else "STATE_TIME_DIRECTION_NOT_READY"

    pred.to_csv(ROOT / f"{PFX}_Predictions.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedEntries.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    fi.to_csv(ROOT / f"{PFX}_FeatureImportance.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL V5 Batch 2D — State-Time Direction Selector Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- OOS HIGH_STATE test episodes 2022-2024: **{len(pred)}**",
        f"- Selected LONG entries at state onset: **{len(selected)}**",
        f"- Selection rate: **{len(selected)/len(pred)*100:.2f}%**",
        f"- OOS ROC AUC: **{auc:.4f}**",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Direction separation", "",
        f"- All HIGH_STATE UP_FIRST rate: **{base_up*100:.2f}%**",
        f"- Selected UP_FIRST rate: **{sel_up*100:.2f}%**",
        f"- UP_FIRST lift: **{lift:.3f}x**", "",
        "## Fixed +60m diagnostic from state-time entry", "",
        f"- Selected WR: **{selected_e['wr']*100:.2f}%**",
        f"- Selected expectancy: **{selected_e['expectancy_pct']:.4f}%**",
        f"- Selected PF: **{pfmt(selected_e['pf'])}**",
        f"- Selected net PnL: **${selected_e['net_pnl_usd']:.2f}**",
        f"- Selected max DD: **${selected_e['max_dd_usd']:.2f}**",
        f"- Selected max loss streak: **{selected_e['max_ls']}**", "",
        f"- All HIGH_STATE baseline expectancy: **{base_e['expectancy_pct']:.4f}%**",
        f"- All HIGH_STATE baseline PF: **{pfmt(base_e['pf'])}**", "",
        "## Year stability", "",
        "| Year | Episodes | Base UP_FIRST | Selected | Sel UP_FIRST | Lift | AUC | WR60 | Exp60 | PF60 | PnL |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.episode_n)} | {float(r.baseline_up_first_rate)*100:.2f}% | {int(r.selected_n)} | {float(r.selected_up_first_rate)*100:.2f}% | {float(r.up_first_lift):.3f}x | {float(r.auc):.3f} | {float(r.selected_wr60)*100:.2f}% | {float(r.selected_expectancy60_pct):.4f}% | {pfmt(r.selected_pf60)} | ${float(r.selected_pnl60_usd):.2f} |"
        )

    lines += ["", "## Top state-time features", ""]
    for _, r in fi.head(15).iterrows():
        lines.append(f"- `{r.feature}` — importance {float(r.importance):.4f}")

    lines += ["", "## Batch 2D decision audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# BATCH 2D VERDICT: {verdict}", "",
        "READY_FOR_BATCH3_RISK_ENVELOPE means the LONG-capable subset is identifiable at HIGH_STATE onset using only causal state-time information and has positive fixed-horizon economics before any TP/SL work.",
        "STATE_TIME_DIRECTION_NOT_READY means do not rescue this state-time selector by sweeping thresholds, models, holding horizons, hours, TP, or SL on 2022-2024.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
