#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor

import sol_v5_batch2_activation_entry as b2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2B_REMAINING_EDGE"
TEST_YEARS = (2022, 2023, 2024)
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0
DIRECTION_Q = 0.70
EDGE_Q = 0.70


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum()); neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def econ(net_pct) -> dict:
    r = pd.Series(net_pct, dtype=float).dropna()
    if r.empty:
        return {"n": 0, "wr": np.nan, "expectancy_pct": np.nan, "pf": np.nan, "net_pnl_usd": 0.0}
    pnl = r / 100.0 * NOTIONAL
    return {
        "n": int(len(r)), "wr": float((r > 0).mean()),
        "expectancy_pct": float(r.mean()), "pf": float(profit_factor(pnl)),
        "net_pnl_usd": float(pnl.sum()),
    }


def remaining_targets(x5: pd.DataFrame, cp: pd.DataFrame) -> pd.DataFrame:
    z = cp.copy()
    idx = x5.index
    op = x5.open.astype(float).to_numpy(); hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy(); cl = x5.close.astype(float).to_numpy()
    exec_pos = idx.get_indexer(pd.DatetimeIndex(pd.to_datetime(z.exec_time, utc=True)))
    state_pos = idx.get_indexer(pd.DatetimeIndex(pd.to_datetime(z.state_entry_time, utc=True)))
    rows = []
    for (_, r), ep, sp in zip(z.iterrows(), exec_pos, state_pos):
        if ep < 0 or sp < 0:
            continue
        # State horizon is exactly 120m from state entry: bars state p..p+23.
        state_last = sp + 23
        if state_last >= len(x5) or ep > state_last:
            continue
        expected_last = pd.Timestamp(r.state_entry_time) + pd.Timedelta(minutes=115)
        if idx[state_last] != expected_last:
            continue
        entry = float(op[ep])
        if not np.isfinite(entry) or entry <= 0:
            continue
        h = hi[ep:state_last + 1]; l = lo[ep:state_last + 1]
        if not len(h):
            continue
        mfe = (float(np.max(h)) / entry - 1.0) * 100.0
        mae_abs = max(0.0, (1.0 - float(np.min(l)) / entry) * 100.0)

        net60 = np.nan
        if ep + 11 < len(x5) and idx[ep + 11] == pd.Timestamp(r.exec_time) + pd.Timedelta(minutes=55):
            gross60 = (float(cl[ep + 11]) / entry - 1.0) * 100.0
            net60 = gross60 - ROUNDTRIP_COST_PCT
        out = r.to_dict()
        out.update({
            "candidate_entry_price": entry,
            "remaining_mfe_pct": mfe,
            "remaining_mae_abs_pct": mae_abs,
            "remaining_net60_pct": net60,
        })
        rows.append(out)
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no checkpoint rows with remaining-path targets")
    return out.sort_values(["state_entry_time", "checkpoint_min"]).reset_index(drop=True)


def regressor(seed: int):
    return ExtraTreesRegressor(
        n_estimators=320, max_depth=8, min_samples_leaf=20,
        max_features="sqrt", random_state=seed, n_jobs=-1,
    )


def train_years_for(test_year: int) -> tuple[int, ...]:
    return b2.train_years_for(test_year)


def walk_forward(cp: pd.DataFrame):
    preds = []
    for y in TEST_YEARS:
        train_years = train_years_for(y)
        tr = cp[cp.test_year.isin(train_years)].copy()
        te = cp[cp.test_year == y].copy()
        if tr.empty or te.empty or tr.target_up_first.nunique() < 2:
            raise RuntimeError(f"bad Batch2B train/test split {y}")
        Xtr = tr[b2.FEATURES].astype(float).to_numpy()
        Xte = te[b2.FEATURES].astype(float).to_numpy()

        clf = b2.activation_model()
        mfe_m = regressor(52); mae_m = regressor(53)
        clf.fit(Xtr, tr.target_up_first.astype(int).to_numpy())
        mfe_m.fit(Xtr, tr.remaining_mfe_pct.astype(float).to_numpy())
        mae_m.fit(Xtr, tr.remaining_mae_abs_pct.astype(float).to_numpy())

        tr_p = clf.predict_proba(Xtr)[:, 1]
        tr_mfe = np.maximum(0.0, mfe_m.predict(Xtr))
        tr_mae = np.maximum(0.0, mae_m.predict(Xtr))
        tr_edge = tr_p * tr_mfe - (1.0 - tr_p) * tr_mae - ROUNDTRIP_COST_PCT
        p_cut = float(np.quantile(tr_p, DIRECTION_Q))
        e_cut = float(np.quantile(tr_edge, EDGE_Q))

        te = te.copy()
        te["p_up"] = clf.predict_proba(Xte)[:, 1]
        te["pred_remaining_mfe_pct"] = np.maximum(0.0, mfe_m.predict(Xte))
        te["pred_remaining_mae_abs_pct"] = np.maximum(0.0, mae_m.predict(Xte))
        te["pred_edge_pct"] = (
            te.p_up * te.pred_remaining_mfe_pct
            - (1.0 - te.p_up) * te.pred_remaining_mae_abs_pct
            - ROUNDTRIP_COST_PCT
        )
        te["direction_cutoff"] = p_cut
        te["edge_cutoff"] = e_cut
        te["entry_candidate"] = (
            (te.p_up >= p_cut) & (te.pred_edge_pct >= e_cut) & (te.pred_edge_pct > 0)
        )
        preds.append(te)
    return pd.concat(preds, ignore_index=True).sort_values(["state_entry_time", "checkpoint_min"]).reset_index(drop=True)


def earliest_entries(pred: pd.DataFrame) -> pd.DataFrame:
    q = pred[pred.entry_candidate].sort_values(["state_entry_time", "checkpoint_min"]).copy()
    if q.empty:
        return q
    return q.groupby("episode_id", as_index=False, sort=False).head(1).reset_index(drop=True)


def ratio(mfe, mae_abs) -> float:
    a = float(pd.Series(mfe, dtype=float).median())
    b = float(pd.Series(mae_abs, dtype=float).median())
    return a / b if np.isfinite(a) and np.isfinite(b) and b > 1e-12 else np.nan


def year_summary(episodes: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        base = episodes[episodes.test_year == y]
        q = selected[selected.test_year == y]
        base_up = float((base.first_barrier.astype(str) == "UP_FIRST").mean()) if len(base) else np.nan
        sel_up = float(q.target_up_first.mean()) if len(q) else np.nan
        ex = econ(q.remaining_net60_pct if len(q) else pd.Series(dtype=float))
        paired = econ((q.state_ret60_pct - ROUNDTRIP_COST_PCT) if len(q) else pd.Series(dtype=float))
        rows.append({
            "test_year": y, "episode_n": int(len(base)), "base_up_first_rate": base_up,
            "selected_n": int(len(q)), "selected_up_first_rate": sel_up,
            "up_first_lift": sel_up/base_up if np.isfinite(sel_up) and np.isfinite(base_up) and base_up > 0 else np.nan,
            "median_trigger_min": float(q.checkpoint_min.median()) if len(q) else np.nan,
            "wr60": ex["wr"], "expectancy60_pct": ex["expectancy_pct"], "pf60": ex["pf"],
            "paired_state_expectancy_pct": paired["expectancy_pct"],
            "paired_delta_pp": ex["expectancy_pct"] - paired["expectancy_pct"] if np.isfinite(ex["expectancy_pct"]) and np.isfinite(paired["expectancy_pct"]) else np.nan,
            "median_remaining_mfe_pct": float(q.remaining_mfe_pct.median()) if len(q) else np.nan,
            "median_remaining_mae_abs_pct": float(q.remaining_mae_abs_pct.median()) if len(q) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    b2.b1.v4.v3.v1.base.fetch_one = b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = b2.b1.v4.build_opportunities(x5)
    state_scores = b2.b1.causal_scores(ev)
    mapped = b2.b1.map_future_paths(x5, state_scores)
    episodes = b2.episode_starts(mapped)
    checkpoints = b2.build_checkpoints(x5, episodes)
    checkpoints = remaining_targets(x5, checkpoints)
    pred = walk_forward(checkpoints)
    selected = earliest_entries(pred)

    test_episodes = episodes[episodes.test_year.isin(TEST_YEARS)].copy()
    test_pred = pred[pred.test_year.isin(TEST_YEARS)].copy()
    base_up = float((test_episodes.first_barrier.astype(str) == "UP_FIRST").mean())
    sel_up = float(selected.target_up_first.mean()) if len(selected) else np.nan

    base_ratio = ratio(test_episodes.mfe_120m_pct, -test_episodes.mae_120m_pct)
    sel_ratio = ratio(selected.remaining_mfe_pct, selected.remaining_mae_abs_pct) if len(selected) else np.nan
    ratio_lift = sel_ratio/base_ratio if np.isfinite(sel_ratio) and np.isfinite(base_ratio) and base_ratio > 0 else np.nan

    ex = econ(selected.remaining_net60_pct if len(selected) else pd.Series(dtype=float))
    paired = econ((selected.state_ret60_pct - ROUNDTRIP_COST_PCT) if len(selected) else pd.Series(dtype=float))
    paired_delta = ex["expectancy_pct"] - paired["expectancy_pct"] if np.isfinite(ex["expectancy_pct"]) and np.isfinite(paired["expectancy_pct"]) else np.nan

    corr_df = test_pred[["pred_edge_pct", "remaining_net60_pct"]].dropna()
    rho = float(spearmanr(corr_df.pred_edge_pct, corr_df.remaining_net60_pct).statistic) if len(corr_df) > 2 else np.nan

    yr = year_summary(test_episodes, selected)
    better_years = int(((yr.selected_up_first_rate > yr.base_up_first_rate) & yr.selected_up_first_rate.notna()).sum())
    gates = {
        "selected_n_ge_250": int(len(selected)) >= 250,
        "selected_up_first_ge_55pct": bool(np.isfinite(sel_up) and sel_up >= .55),
        "selected_up_first_beats_baseline_ge_2_of_3_years": better_years >= 2,
        "mfe_mae_ratio_lift_ge_1_15x": bool(np.isfinite(ratio_lift) and ratio_lift >= 1.15),
        "paired_60m_not_worse_than_minus_0_10pp": bool(np.isfinite(paired_delta) and paired_delta >= -0.10),
        "pred_edge_realized_net60_spearman_positive": bool(np.isfinite(rho) and rho > 0),
    }
    passed = bool(all(gates.values()))
    verdict = "READY_FOR_BATCH2C" if passed else "REMAINING_EDGE_NOT_READY"

    checkpoints.to_csv(ROOT / f"{PFX}_CheckpointsWithTargets.csv", index=False)
    pred.to_csv(ROOT / f"{PFX}_Predictions.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedEntries.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    def pfmt(v):
        if pd.isna(v): return "n/a"
        if np.isinf(v): return "inf"
        return f"{float(v):.3f}"

    lines = [
        "# SOL V5 Batch 2B — Remaining Edge Predictor Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- HIGH_STATE test episodes 2022-2024: **{len(test_episodes)}**",
        f"- Eligible OOS checkpoints: **{len(test_pred)}**",
        f"- Selected adaptive-entry episodes: **{len(selected)}**",
        f"- Median trigger: **{float(selected.checkpoint_min.median()) if len(selected) else np.nan:.1f} min**",
        f"- 2025+ reference_validation remained CLOSED.", "",
        "## Direction and remaining edge", "",
        f"- HIGH_STATE episode UP_FIRST baseline: **{base_up*100:.2f}%**",
        f"- Selected UP_FIRST rate: **{sel_up*100:.2f}%**",
        f"- Direction lift: **{sel_up/base_up if base_up > 0 and np.isfinite(sel_up) else np.nan:.3f}x**",
        f"- Spearman(pred_edge, realized +60m net): **{rho:.4f}**", "",
        "## Entry geometry", "",
        f"- HIGH_STATE median MFE/|MAE| ratio: **{base_ratio:.3f}**",
        f"- Selected remaining MFE/|MAE| ratio: **{sel_ratio:.3f}**",
        f"- Ratio lift: **{ratio_lift:.3f}x**",
        f"- Selected median remaining MFE: **{float(selected.remaining_mfe_pct.median()) if len(selected) else np.nan:.3f}%**",
        f"- Selected median remaining MAE: **-{float(selected.remaining_mae_abs_pct.median()) if len(selected) else np.nan:.3f}%**", "",
        "## Fixed +60m diagnostic", "",
        f"- Selected WR: **{ex['wr']*100:.2f}%**",
        f"- Selected expectancy: **{ex['expectancy_pct']:.4f}%**",
        f"- Selected PF: **{pfmt(ex['pf'])}**",
        f"- Selected net PnL: **${ex['net_pnl_usd']:.2f}**",
        f"- Same-selected-episode immediate-state expectancy: **{paired['expectancy_pct']:.4f}%**",
        f"- Paired delta: **{paired_delta:+.4f} pp**", "",
        "## Year stability", "",
        "| Year | Episodes | Base UP_FIRST | Selected | Selected UP_FIRST | Lift | Trigger | WR60 | Exp60 | PF60 | State Exp | Δ | Rem MFE | Rem MAE |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.episode_n)} | {float(r.base_up_first_rate)*100:.2f}% | {int(r.selected_n)} | {float(r.selected_up_first_rate)*100:.2f}% | {float(r.up_first_lift):.3f}x | {float(r.median_trigger_min):.1f}m | {float(r.wr60)*100:.2f}% | {float(r.expectancy60_pct):.4f}% | {pfmt(r.pf60)} | {float(r.paired_state_expectancy_pct):.4f}% | {float(r.paired_delta_pp):+.4f} | {float(r.median_remaining_mfe_pct):.3f}% | -{float(r.median_remaining_mae_abs_pct):.3f}% |"
        )
    lines += ["", "## Batch 2B decision audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += ["", f"# BATCH 2B VERDICT: {verdict}", "",
              "READY_FOR_BATCH2C means direction plus remaining-edge selection preserved enough post-entry opportunity to proceed to a frozen adaptive-entry policy. It does not authorize TP/SL optimization or opening 2025+.",
              "REMAINING_EDGE_NOT_READY means do not rescue this rule by optimizing exits against the same 2022-2024 research sample."]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
