#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import sol_v5_batch2_activation_entry as b2

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2H_POST_STATE_ACTIVATION_ONSET"
ONSET_WINDOW_BARS = 3
ONSET_FRAC = 0.50
SELECT_Q = 0.90
TEST_YEARS = b2.TEST_YEARS
ROUNDTRIP_COST_PCT = b2.ROUNDTRIP_COST_PCT


def pfmt(v) -> str:
    if pd.isna(v):
        return "n/a"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.3f}"


def build_labeled_checkpoints(x5: pd.DataFrame):
    ev = b2.b1.v4.build_opportunities(x5)
    pred_state = b2.b1.causal_scores(ev)
    mapped = b2.b1.map_future_paths(x5, pred_state)
    episodes = b2.episode_starts(mapped).copy()
    cp = b2.build_checkpoints(x5, episodes).copy()

    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()
    pos = idx.get_indexer(pd.DatetimeIndex(pd.to_datetime(cp.exec_time, utc=True)))

    valid = pos >= 0
    valid &= pos + 11 < len(x5)
    valid &= pos + ONSET_WINDOW_BARS - 1 < len(x5)
    cp = cp.iloc[np.flatnonzero(valid)].copy().reset_index(drop=True)
    pos = pos[valid]
    if cp.empty:
        raise RuntimeError("no complete Batch 2H checkpoints")

    entry = op[pos]
    thr = cp.impulse_threshold_pct.astype(float).to_numpy()
    up_barrier = entry * (1.0 + ONSET_FRAC * thr / 100.0)
    dn_barrier = entry * (1.0 - ONSET_FRAC * thr / 100.0)

    onset_hi = np.column_stack([hi[pos + j] for j in range(ONSET_WINDOW_BARS)])
    onset_lo = np.column_stack([lo[pos + j] for j in range(ONSET_WINDOW_BARS)])
    up_touch = onset_hi >= up_barrier[:, None]
    dn_touch = onset_lo <= dn_barrier[:, None]
    up_any = up_touch.any(axis=1)
    dn_any = dn_touch.any(axis=1)
    up_idx = np.argmax(up_touch, axis=1)
    dn_idx = np.argmax(dn_touch, axis=1)
    imminent = up_any & (~dn_any | (up_idx < dn_idx))
    # same-bar first touch is conservatively not a positive label
    imminent &= ~(up_any & dn_any & (up_idx == dn_idx))

    cp["exec_price"] = entry
    cp["target_imminent_up_onset"] = imminent.astype(int)
    cp["onset_up_touch"] = up_any.astype(int)
    cp["onset_down_touch"] = dn_any.astype(int)

    future_hi = np.column_stack([hi[pos + j] for j in range(12)])
    future_lo = np.column_stack([lo[pos + j] for j in range(12)])
    exitp = cl[pos + 11]
    cp["entry_ret60_gross_pct"] = (exitp / entry - 1.0) * 100.0
    cp["entry_net60_pct"] = cp.entry_ret60_gross_pct.astype(float) - ROUNDTRIP_COST_PCT
    cp["entry_mfe60_pct"] = (future_hi.max(axis=1) / entry - 1.0) * 100.0
    cp["entry_mae60_pct"] = (future_lo.min(axis=1) / entry - 1.0) * 100.0
    denom = np.abs(cp.entry_mae60_pct.astype(float).to_numpy())
    cp["entry_mfe_mae_ratio"] = np.where(denom > 1e-9, cp.entry_mfe60_pct.astype(float).to_numpy() / denom, np.nan)

    miss = [c for c in b2.FEATURES if c not in cp.columns]
    if miss:
        raise RuntimeError(f"missing checkpoint features: {miss}")
    a = cp[b2.FEATURES].astype(float).to_numpy()
    if not np.isfinite(a).all():
        raise RuntimeError("non-finite checkpoint features")
    return episodes, cp


def walk_forward(cp: pd.DataFrame):
    scored = []
    for y in TEST_YEARS:
        train_years = b2.train_years_for(y)
        tr = cp[cp.test_year.isin(train_years)].copy()
        te = cp[cp.test_year == y].copy()
        if tr.empty or te.empty or tr.target_imminent_up_onset.nunique() < 2:
            raise RuntimeError(f"bad Batch 2H fold {y}")

        clf = b2.activation_model()
        Xtr = tr[b2.FEATURES].astype(float).to_numpy()
        ytr = tr.target_imminent_up_onset.astype(int).to_numpy()
        clf.fit(Xtr, ytr)
        train_score = clf.predict_proba(Xtr)[:, 1]
        cutoff = float(np.quantile(train_score, SELECT_Q))

        te = te.copy()
        te["onset_score"] = clf.predict_proba(te[b2.FEATURES].astype(float).to_numpy())[:, 1]
        te["onset_cutoff"] = cutoff
        te["qualifies"] = te.onset_score >= cutoff
        scored.append(te)

    out = pd.concat(scored, ignore_index=True).sort_values(["state_entry_time", "checkpoint_min"]).reset_index(drop=True)
    return out


def select_first(scored: pd.DataFrame) -> pd.DataFrame:
    q = scored[scored.qualifies].copy()
    if q.empty:
        return q
    q = q.sort_values(["state_entry_time", "checkpoint_min"])
    return q.groupby("episode_id", as_index=False, group_keys=False).head(1).reset_index(drop=True)


def yearly_summary(scored: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        g = scored[scored.test_year == y].copy()
        s = selected[selected.test_year == y].copy()
        auc = float(roc_auc_score(g.target_imminent_up_onset.astype(int), g.onset_score.astype(float))) if g.target_imminent_up_onset.nunique() > 1 else np.nan
        ee = b2.econ_returns(s.entry_net60_pct if len(s) else pd.Series(dtype=float))
        paired = b2.econ_returns((s.state_ret60_pct.astype(float) - ROUNDTRIP_COST_PCT) if len(s) else pd.Series(dtype=float))
        rows.append({
            "test_year": y,
            "checkpoint_n": int(len(g)),
            "onset_base_rate": float(g.target_imminent_up_onset.mean()) if len(g) else np.nan,
            "checkpoint_auc": auc,
            "selected_n": int(len(s)),
            "selected_onset_precision": float(s.target_imminent_up_onset.mean()) if len(s) else np.nan,
            "median_trigger_min": float(s.checkpoint_min.median()) if len(s) else np.nan,
            "entry_wr60": ee["wr"],
            "entry_expectancy60_pct": ee["expectancy_pct"],
            "entry_pf60": ee["pf"],
            "entry_pnl60_usd": ee["net_pnl_usd"],
            "entry_max_dd_usd": ee["max_dd_usd"],
            "entry_max_ls": ee["max_ls"],
            "paired_state_expectancy60_pct": paired["expectancy_pct"],
            "paired_delta_expectancy_pct": ee["expectancy_pct"] - paired["expectancy_pct"] if np.isfinite(ee["expectancy_pct"]) and np.isfinite(paired["expectancy_pct"]) else np.nan,
            "median_mfe60_pct": float(s.entry_mfe60_pct.median()) if len(s) else np.nan,
            "median_mae60_pct": float(s.entry_mae60_pct.median()) if len(s) else np.nan,
            "median_mfe_mae_ratio": float(s.entry_mfe_mae_ratio.replace([np.inf, -np.inf], np.nan).median()) if len(s) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    b2.b1.v4.v3.v1.base.fetch_one = b2.b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b2.b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    episodes, cp = build_labeled_checkpoints(x5)
    scored = walk_forward(cp)
    selected = select_first(scored)

    auc = float(roc_auc_score(scored.target_imminent_up_onset.astype(int), scored.onset_score.astype(float))) if scored.target_imminent_up_onset.nunique() > 1 else np.nan
    onset_base = float(scored.target_imminent_up_onset.mean())
    onset_prec = float(selected.target_imminent_up_onset.mean()) if len(selected) else np.nan
    entry_e = b2.econ_returns(selected.entry_net60_pct if len(selected) else pd.Series(dtype=float))
    paired_e = b2.econ_returns((selected.state_ret60_pct.astype(float) - ROUNDTRIP_COST_PCT) if len(selected) else pd.Series(dtype=float))

    # All HIGH_STATE episode baseline in the same 2022-2024 universe.
    eps = episodes[episodes.test_year.isin(TEST_YEARS)].copy()
    all_state_e = b2.econ_returns(eps.ret_60m_pct.astype(float) - ROUNDTRIP_COST_PCT)

    finite_ratio = selected.entry_mfe_mae_ratio.replace([np.inf, -np.inf], np.nan) if len(selected) else pd.Series(dtype=float)
    med_ratio = float(finite_ratio.median()) if len(finite_ratio) else np.nan
    yr = yearly_summary(scored, selected)
    pos_years = int((yr.entry_pnl60_usd > 0).sum())
    paired_delta = entry_e["expectancy_pct"] - paired_e["expectancy_pct"] if np.isfinite(entry_e["expectancy_pct"]) and np.isfinite(paired_e["expectancy_pct"]) else np.nan

    gates = {
        "selected_oos_n_ge_150": int(len(selected)) >= 150,
        "checkpoint_onset_auc_ge_0_60": bool(np.isfinite(auc) and auc >= .60),
        "selected_onset_precision_ge_50pct": bool(np.isfinite(onset_prec) and onset_prec >= .50),
        "selected_expectancy_positive": bool(np.isfinite(entry_e["expectancy_pct"]) and entry_e["expectancy_pct"] > 0),
        "selected_pf_ge_1_10": bool(np.isfinite(entry_e["pf"]) and entry_e["pf"] >= 1.10),
        "positive_selected_pnl_years_ge_2_of_3": pos_years >= 2,
        "activation_expectancy_beats_paired_state": bool(np.isfinite(paired_delta) and paired_delta > 0),
        "median_mfe_mae_ratio_ge_1_15": bool(np.isfinite(med_ratio) and med_ratio >= 1.15),
    }
    passed = bool(all(gates.values()))
    verdict = "READY_FOR_BATCH3_RISK_ENVELOPE" if passed else "RESET_SOL_DISCOVERY"

    scored.to_csv(ROOT / f"{PFX}_CheckpointScores.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedTrades.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL V5 Batch 2H — Post-State Activation Onset Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- OOS eligible checkpoints 2022-2024: **{len(scored)}**",
        f"- OOS HIGH_STATE episodes represented: **{scored.episode_id.nunique()}**",
        f"- Selected first activation entries: **{len(selected)}**",
        f"- Checkpoint onset base rate: **{onset_base*100:.2f}%**",
        f"- Checkpoint onset ROC AUC: **{auc:.4f}**",
        f"- Selected onset precision: **{onset_prec*100:.2f}%**",
        f"- Median selected trigger: **{float(selected.checkpoint_min.median()) if len(selected) else np.nan:.1f}m**",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## Fixed +60m economics", "",
        f"- ALL HIGH_STATE immediate expectancy: **{all_state_e['expectancy_pct']:.4f}%**, PF **{pfmt(all_state_e['pf'])}**",
        f"- Paired selected episodes immediate-state expectancy: **{paired_e['expectancy_pct']:.4f}%**, PF **{pfmt(paired_e['pf'])}**",
        f"- Batch 2H activation-entry WR: **{entry_e['wr']*100:.2f}%**",
        f"- Batch 2H activation-entry expectancy: **{entry_e['expectancy_pct']:.4f}%**",
        f"- Batch 2H activation-entry PF: **{pfmt(entry_e['pf'])}**",
        f"- Batch 2H activation-entry PnL: **${entry_e['net_pnl_usd']:.2f}**",
        f"- Paired expectancy delta vs immediate state: **{paired_delta:.4f} pp**", "",
        "## Post-entry geometry", "",
        f"- Median MFE60: **{float(selected.entry_mfe60_pct.median()) if len(selected) else np.nan:.4f}%**",
        f"- Median MAE60: **{float(selected.entry_mae60_pct.median()) if len(selected) else np.nan:.4f}%**",
        f"- Median MFE/|MAE| ratio: **{med_ratio:.3f}**", "",
        "## Year stability", "",
        "| Year | Checkpoints | Base onset | AUC | Selected | Precision | Trigger | WR60 | Exp60 | PF | PnL | Paired state exp | Delta | Ratio |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.checkpoint_n)} | {float(r.onset_base_rate)*100:.2f}% | {float(r.checkpoint_auc):.3f} | {int(r.selected_n)} | {float(r.selected_onset_precision)*100:.2f}% | {float(r.median_trigger_min):.1f}m | {float(r.entry_wr60)*100:.2f}% | {float(r.entry_expectancy60_pct):.4f}% | {pfmt(r.entry_pf60)} | ${float(r.entry_pnl60_usd):.2f} | {float(r.paired_state_expectancy60_pct):.4f}% | {float(r.paired_delta_expectancy_pct):.4f} | {float(r.median_mfe_mae_ratio):.3f} |"
        )

    lines += ["", "## Batch 2H gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# BATCH 2H VERDICT: {verdict}", "",
        "READY_FOR_BATCH3_RISK_ENVELOPE means imminent activation onset is identifiable early enough to create positive pre-exit-optimization OOS economics and improve timing versus immediate state entry.",
        "RESET_SOL_DISCOVERY means the frozen V5 HIGH_STATE → activation path failed its final preregistered entry test. Do not rescue it by sweeping onset semantics, checkpoint timing, model, cutoff, hours, horizon, TP or SL on 2022-2024.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
