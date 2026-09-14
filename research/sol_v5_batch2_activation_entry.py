#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import roc_auc_score

import sol_v5_batch1_future_path_mapping as b1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH2_ACTIVATION_ENTRY"
BAR = pd.Timedelta(minutes=5)
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
CHECKPOINTS = (5, 10, 15, 20, 25, 30)
TEST_YEARS = (2022, 2023, 2024)
ACTIVATION_Q = 0.90
ROUNDTRIP_COST_PCT = 0.15
NOTIONAL = 500.0

STATE_CONTEXT = (
    "range_30", "range_120", "rv_30", "rv_120",
    "dist_from_high_120_pct", "dist_from_low_120_pct",
    "accel_15", "accel_30",
)
DYNAMIC_FEATURES = (
    "state_score", "state_margin", "sigma60_pct", "impulse_threshold_pct",
    "checkpoint_frac", "ret_from_state_pct", "mfe_so_far_pct", "mae_so_far_pct",
    "post_range_pct", "post_rv_pct", "post_efficiency", "close_pos_post_range",
    "remaining_up_frac", "remaining_down_frac",
    "ret_last5_pct", "ret_last10_pct", "ret_last15_pct", "accel_5_pct",
    "up_close_ratio", "last_body_sigma", "last_range_sigma", "last_close_loc",
    "last_lower_wick_frac", "last_upper_wick_frac", "post_volume_vs_pre120",
) + STATE_CONTEXT
FEATURES = list(DYNAMIC_FEATURES)


def profit_factor(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg <= 0:
        return math.inf if pos > 0 else np.nan
    return pos / neg


def max_drawdown(pnls) -> float:
    a = pd.Series(pnls, dtype=float).dropna()
    if a.empty:
        return np.nan
    eq = a.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def max_loss_streak(pnls) -> int:
    best = cur = 0
    for x in pd.Series(pnls, dtype=float).dropna():
        if x < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def econ_returns(net_pct: pd.Series) -> dict:
    r = pd.Series(net_pct, dtype=float).dropna()
    if r.empty:
        return {"n": 0, "wr": np.nan, "expectancy_pct": np.nan, "net_pnl_usd": 0.0, "pf": np.nan, "max_dd_usd": np.nan, "max_ls": 0}
    pnl = r / 100.0 * NOTIONAL
    return {
        "n": int(len(r)),
        "wr": float((r > 0).mean()),
        "expectancy_pct": float(r.mean()),
        "net_pnl_usd": float(pnl.sum()),
        "pf": float(profit_factor(pnl)),
        "max_dd_usd": float(max_drawdown(pnl)),
        "max_ls": int(max_loss_streak(pnl)),
    }


def episode_starts(mapped: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for y, g in mapped.sort_values("entry_time").groupby("test_year", sort=True):
        q = g.sort_values("entry_time").copy()
        prev_active = q.state_active.shift(1).fillna(False).astype(bool)
        prev_time = pd.to_datetime(q.entry_time.shift(1), utc=True)
        cur_time = pd.to_datetime(q.entry_time, utc=True)
        gap = cur_time - prev_time
        start = q.state_active.astype(bool) & ((~prev_active) | prev_time.isna() | (gap > pd.Timedelta(minutes=15)))
        e = q[start].copy()
        e["episode_id"] = e.entry_time.astype(str)
        parts.append(e)
    out = pd.concat(parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    if out.empty:
        raise RuntimeError("no HIGH_STATE episode starts")
    return out


def _ret_last(anchor: float, closes: np.ndarray, bars: int) -> float:
    if len(closes) == 0:
        return 0.0
    if len(closes) <= bars:
        base = anchor
    else:
        base = float(closes[-bars - 1])
    return float((closes[-1] / base - 1.0) * 100.0) if base > 0 else 0.0


def checkpoint_features(x5: pd.DataFrame, state: pd.Series, p: int, cp_min: int) -> dict | None:
    n = cp_min // 5
    if n < 1 or p + n > len(x5):
        return None
    q = x5.iloc[p:p + n]
    if len(q) != n or q.index[-1] != pd.Timestamp(state.entry_time) + pd.Timedelta(minutes=cp_min - 5):
        return None

    anchor = float(state.anchor_price)
    thr = float(state.impulse_threshold_pct)
    sigma = float(state.sigma60_pct)
    up_barrier = anchor * (1.0 + thr / 100.0)
    dn_barrier = anchor * (1.0 - thr / 100.0)

    # Once either frozen state barrier is touched, activation is no longer eligible.
    if float(q.high.max()) >= up_barrier or float(q.low.min()) <= dn_barrier:
        return None

    op = q.open.astype(float).to_numpy(); hi = q.high.astype(float).to_numpy()
    lo = q.low.astype(float).to_numpy(); cl = q.close.astype(float).to_numpy(); vol = q.volume.astype(float).to_numpy()
    if not all(np.isfinite(a).all() for a in (op, hi, lo, cl, vol)):
        return None
    cur = float(cl[-1])
    path_hi = float(np.max(hi)); path_lo = float(np.min(lo))
    post_range = (path_hi / path_lo - 1.0) * 100.0 if path_lo > 0 else np.nan
    seq = np.r_[anchor, cl]
    lret = np.diff(np.log(seq))
    post_rv = float(np.std(lret, ddof=1) * np.sqrt(max(1, len(lret))) * 100.0) if len(lret) >= 2 else 0.0
    gross_path = abs(float(np.log(cur / anchor))) if anchor > 0 and cur > 0 else 0.0
    path_len = float(np.abs(lret).sum())
    eff = gross_path / path_len if path_len > 1e-12 else 0.0
    span = path_hi - path_lo
    close_pos = (cur - path_lo) / span if span > 0 else 0.5

    ret5 = _ret_last(anchor, cl, 1)
    ret10 = _ret_last(anchor, cl, 2)
    ret15 = _ret_last(anchor, cl, 3)
    if len(cl) >= 2:
        prev5 = float((cl[-2] / (cl[-3] if len(cl) >= 3 else anchor) - 1.0) * 100.0)
    else:
        prev5 = 0.0
    accel5 = ret5 - prev5

    last_o = float(op[-1]); last_h = float(hi[-1]); last_l = float(lo[-1]); last_c = float(cl[-1])
    last_span = last_h - last_l
    lower = max(0.0, min(last_o, last_c) - last_l)
    upper = max(0.0, last_h - max(last_o, last_c))
    close_loc = (last_c - last_l) / last_span if last_span > 0 else 0.5
    body_sigma = ((last_c / last_o - 1.0) * 100.0 / sigma) if last_o > 0 and sigma > 0 else 0.0
    range_sigma = ((last_h / last_l - 1.0) * 100.0 / sigma) if last_l > 0 and sigma > 0 else 0.0

    pre = x5.iloc[max(0, p - 24):p]
    pre_med_vol = float(pre.volume.astype(float).median()) if len(pre) else np.nan
    vol_ratio = float(np.mean(vol) / pre_med_vol) if np.isfinite(pre_med_vol) and pre_med_vol > 0 else 1.0

    f = {
        "state_score": float(state.pred_impulse),
        "state_margin": float(state.pred_impulse - state.state_cutoff),
        "sigma60_pct": sigma,
        "impulse_threshold_pct": thr,
        "checkpoint_frac": float(cp_min / 30.0),
        "ret_from_state_pct": float((cur / anchor - 1.0) * 100.0),
        "mfe_so_far_pct": float((path_hi / anchor - 1.0) * 100.0),
        "mae_so_far_pct": float((path_lo / anchor - 1.0) * 100.0),
        "post_range_pct": float(post_range),
        "post_rv_pct": float(post_rv),
        "post_efficiency": float(eff),
        "close_pos_post_range": float(close_pos),
        "remaining_up_frac": float(((up_barrier / cur - 1.0) * 100.0) / thr) if cur > 0 and thr > 0 else np.nan,
        "remaining_down_frac": float(((cur / dn_barrier - 1.0) * 100.0) / thr) if dn_barrier > 0 and thr > 0 else np.nan,
        "ret_last5_pct": float(ret5),
        "ret_last10_pct": float(ret10),
        "ret_last15_pct": float(ret15),
        "accel_5_pct": float(accel5),
        "up_close_ratio": float(np.mean(cl > op)),
        "last_body_sigma": float(body_sigma),
        "last_range_sigma": float(range_sigma),
        "last_close_loc": float(close_loc),
        "last_lower_wick_frac": float(lower / last_span) if last_span > 0 else 0.0,
        "last_upper_wick_frac": float(upper / last_span) if last_span > 0 else 0.0,
        "post_volume_vs_pre120": float(vol_ratio),
    }
    for k in STATE_CONTEXT:
        f[k] = float(state[k])
    vals = np.asarray(list(f.values()), dtype=float)
    return f if np.isfinite(vals).all() else None


def build_checkpoints(x5: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    pos = x5.index.get_indexer(pd.DatetimeIndex(pd.to_datetime(episodes.entry_time, utc=True)))
    rows = []
    for (_, s), p in zip(episodes.iterrows(), pos):
        if p < 0:
            continue
        for cp in CHECKPOINTS:
            f = checkpoint_features(x5, s, int(p), cp)
            if f is None:
                # Barrier resolution makes all later checkpoints ineligible as well.
                n = cp // 5
                q = x5.iloc[p:p+n]
                anchor = float(s.anchor_price); thr = float(s.impulse_threshold_pct)
                if len(q) and (float(q.high.max()) >= anchor*(1+thr/100.0) or float(q.low.min()) <= anchor*(1-thr/100.0)):
                    break
                continue
            checkpoint_time = pd.Timestamp(s.entry_time) + pd.Timedelta(minutes=cp)
            rows.append({
                "episode_id": str(s.episode_id),
                "state_entry_time": pd.Timestamp(s.entry_time),
                "test_year": int(s.test_year),
                "checkpoint_min": int(cp),
                "checkpoint_time": checkpoint_time,
                "exec_time": checkpoint_time,
                "target_up_first": int(str(s.first_barrier) == "UP_FIRST"),
                "state_first_barrier": str(s.first_barrier),
                "state_ret60_pct": float(s.ret_60m_pct),
                "state_mfe120_pct": float(s.mfe_120m_pct),
                "state_mae120_pct": float(s.mae_120m_pct),
                **f,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no eligible activation checkpoints")
    return out.sort_values(["state_entry_time", "checkpoint_min"]).reset_index(drop=True)


def activation_model():
    return ExtraTreesClassifier(
        n_estimators=320,
        max_depth=8,
        min_samples_leaf=20,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def train_years_for(test_year: int) -> tuple[int, ...]:
    if test_year == 2022:
        return (2021,)
    if test_year == 2023:
        return (2021, 2022)
    if test_year == 2024:
        return (2022, 2023)
    raise ValueError(test_year)


def walk_forward(checkpoints: pd.DataFrame):
    preds, imps = [], []
    for y in TEST_YEARS:
        train_years = train_years_for(y)
        tr = checkpoints[checkpoints.test_year.isin(train_years)].copy()
        te = checkpoints[checkpoints.test_year == y].copy()
        if tr.empty or te.empty or tr.target_up_first.nunique() < 2:
            raise RuntimeError(f"bad activation train/test split for {y}")
        clf = activation_model()
        Xtr = tr[FEATURES].astype(float).to_numpy(); ytr = tr.target_up_first.astype(int).to_numpy()
        clf.fit(Xtr, ytr)
        train_score = clf.predict_proba(Xtr)[:, 1]
        cutoff = float(np.quantile(train_score, ACTIVATION_Q))
        te["activation_score"] = clf.predict_proba(te[FEATURES].astype(float).to_numpy())[:, 1]
        te["activation_cutoff"] = cutoff
        te["activation_candidate"] = te.activation_score >= cutoff
        preds.append(te)
        imps.append(pd.DataFrame({"test_year": y, "feature": FEATURES, "importance": clf.feature_importances_}))
    return pd.concat(preds, ignore_index=True), pd.concat(imps, ignore_index=True)


def earliest_entries(pred: pd.DataFrame) -> pd.DataFrame:
    q = pred[pred.activation_candidate].sort_values(["state_entry_time", "checkpoint_min"]).copy()
    if q.empty:
        return q
    return q.groupby("episode_id", as_index=False, sort=False).head(1).reset_index(drop=True)


def evaluate_entries(x5: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    if entries.empty:
        return entries.copy()
    pos = x5.index.get_indexer(pd.DatetimeIndex(pd.to_datetime(entries.exec_time, utc=True)))
    rows = []
    op = x5.open.astype(float).to_numpy(); hi = x5.high.astype(float).to_numpy(); lo = x5.low.astype(float).to_numpy(); cl = x5.close.astype(float).to_numpy()
    for (_, r), p in zip(entries.iterrows(), pos):
        if p < 0 or p + 23 >= len(x5):
            continue
        exec_ts = pd.Timestamp(r.exec_time)
        if exec_ts + pd.Timedelta(minutes=120) > MODEL_END:
            continue
        if x5.index[p+23] != exec_ts + pd.Timedelta(minutes=115):
            continue
        entry = float(op[p]); exit60 = float(cl[p+11])
        gross60 = (exit60 / entry - 1.0) * 100.0
        net60 = gross60 - ROUNDTRIP_COST_PCT
        h = hi[p:p+24]; l = lo[p:p+24]
        mfe = (float(np.max(h)) / entry - 1.0) * 100.0
        mae = (float(np.min(l)) / entry - 1.0) * 100.0
        out = r.to_dict()
        out.update({
            "exec_entry_price": entry,
            "exec_gross60_pct": gross60,
            "exec_net60_pct": net60,
            "exec_pnl60_usd": net60 / 100.0 * NOTIONAL,
            "exec_mfe120_pct": mfe,
            "exec_mae120_pct": mae,
            "paired_state_net60_pct": float(r.state_ret60_pct) - ROUNDTRIP_COST_PCT,
        })
        rows.append(out)
    return pd.DataFrame(rows).sort_values("exec_time").reset_index(drop=True)


def ratio(mfe, mae) -> float:
    a = float(pd.Series(mfe, dtype=float).median()); b = abs(float(pd.Series(mae, dtype=float).median()))
    return a / b if np.isfinite(a) and np.isfinite(b) and b > 1e-12 else np.nan


def yearly_summary(episodes: pd.DataFrame, executed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for y in TEST_YEARS:
        base = episodes[episodes.test_year == y]
        ex = executed[executed.test_year == y]
        be = float((base.first_barrier.astype(str) == "UP_FIRST").mean()) if len(base) else np.nan
        ue = float(ex.target_up_first.mean()) if len(ex) else np.nan
        ee = econ_returns(ex.exec_net60_pct if len(ex) else pd.Series(dtype=float))
        pe = econ_returns(ex.paired_state_net60_pct if len(ex) else pd.Series(dtype=float))
        rows.append({
            "test_year": y,
            "episode_n": int(len(base)),
            "episode_up_first_rate": be,
            "activation_n": int(len(ex)),
            "activation_rate": float(len(ex)/len(base)) if len(base) else np.nan,
            "activated_up_first_rate": ue,
            "up_first_lift": ue/be if np.isfinite(be) and be > 0 and np.isfinite(ue) else np.nan,
            "exec_wr": ee["wr"], "exec_expectancy_pct": ee["expectancy_pct"], "exec_pf": ee["pf"],
            "paired_state_expectancy_pct": pe["expectancy_pct"],
            "expectancy_improvement_pp": ee["expectancy_pct"] - pe["expectancy_pct"] if np.isfinite(ee["expectancy_pct"]) and np.isfinite(pe["expectancy_pct"]) else np.nan,
            "exec_median_mfe120_pct": float(ex.exec_mfe120_pct.median()) if len(ex) else np.nan,
            "exec_median_mae120_pct": float(ex.exec_mae120_pct.median()) if len(ex) else np.nan,
            "median_activation_min": float(ex.checkpoint_min.median()) if len(ex) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    # Rebuild the frozen V4 state and Batch 1 path map exactly.
    b1.v4.v3.v1.base.fetch_one = b1.v4.v3.v1.fetch_one_with_volume
    x5, coverage = b1.v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")
    ev = b1.v4.build_opportunities(x5)
    pred_state = b1.causal_scores(ev)
    mapped = b1.map_future_paths(x5, pred_state)
    episodes = episode_starts(mapped)
    checkpoints = build_checkpoints(x5, episodes)
    pred_cp, imp = walk_forward(checkpoints)
    chosen = earliest_entries(pred_cp)
    executed = evaluate_entries(x5, chosen)

    test_episodes = episodes[episodes.test_year.isin(TEST_YEARS)].copy()
    test_cp = pred_cp.copy()
    if test_cp.target_up_first.nunique() < 2:
        auc = np.nan
    else:
        auc = float(roc_auc_score(test_cp.target_up_first.astype(int), test_cp.activation_score.astype(float)))

    base_up = float((test_episodes.first_barrier.astype(str) == "UP_FIRST").mean())
    act_up = float(executed.target_up_first.mean()) if len(executed) else np.nan
    up_lift = act_up / base_up if base_up > 0 and np.isfinite(act_up) else np.nan

    exec_e = econ_returns(executed.exec_net60_pct if len(executed) else pd.Series(dtype=float))
    paired_e = econ_returns(executed.paired_state_net60_pct if len(executed) else pd.Series(dtype=float))
    expectancy_improvement = exec_e["expectancy_pct"] - paired_e["expectancy_pct"] if np.isfinite(exec_e["expectancy_pct"]) and np.isfinite(paired_e["expectancy_pct"]) else np.nan

    base_ratio = ratio(test_episodes.mfe_120m_pct, test_episodes.mae_120m_pct)
    exec_ratio = ratio(executed.exec_mfe120_pct, executed.exec_mae120_pct) if len(executed) else np.nan
    ratio_lift = exec_ratio / base_ratio if np.isfinite(exec_ratio) and np.isfinite(base_ratio) and base_ratio > 0 else np.nan

    yr = yearly_summary(test_episodes, executed)
    better_years = int(((yr.activated_up_first_rate > yr.episode_up_first_rate) & yr.activated_up_first_rate.notna()).sum())

    fi = imp.groupby("feature", as_index=False).importance.mean().sort_values("importance", ascending=False)
    gates = {
        "activation_n_ge_300": int(len(executed)) >= 300,
        "checkpoint_auc_ge_0_55": bool(np.isfinite(auc) and auc >= .55),
        "activated_up_first_lift_ge_1_25x": bool(np.isfinite(up_lift) and up_lift >= 1.25),
        "activated_up_first_beats_baseline_ge_2_of_3_years": better_years >= 2,
        "paired_60m_expectancy_improves": bool(np.isfinite(expectancy_improvement) and expectancy_improvement > 0),
        "mfe_mae_ratio_lift_ge_1_15x": bool(np.isfinite(ratio_lift) and ratio_lift >= 1.15),
    }
    passed = bool(all(gates.values()))

    checkpoints.to_csv(ROOT / f"{PFX}_Checkpoints.csv", index=False)
    pred_cp.to_csv(ROOT / f"{PFX}_CheckpointPredictions.csv", index=False)
    executed.to_csv(ROOT / f"{PFX}_ActivatedEntries.csv", index=False)
    yr.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    fi.to_csv(ROOT / f"{PFX}_FeatureImportance.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    def pfmt(v):
        if pd.isna(v): return "n/a"
        if np.isinf(v): return "inf"
        return f"{float(v):.3f}"

    lines = [
        "# SOL V5 Batch 2 — Activation / Adaptive Entry Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- HIGH_STATE episode starts available: **{len(episodes)}**",
        f"- Nested OOS test episodes 2022-2024: **{len(test_episodes)}**",
        f"- Eligible OOS checkpoint rows: **{len(test_cp)}**",
        f"- Activated entries: **{len(executed)}**",
        f"- OOS checkpoint ROC AUC: **{auc:.4f}**",
        f"- Median activation time: **{float(executed.checkpoint_min.median()) if len(executed) else np.nan:.1f} min**",
        f"- 2025+ reference_validation remained CLOSED.", "",
        "## Directional activation", "",
        f"- All HIGH_STATE episode UP_FIRST rate: **{base_up*100:.2f}%**",
        f"- Activated-entry UP_FIRST rate: **{act_up*100:.2f}%**",
        f"- UP_FIRST lift: **{up_lift:.3f}x**", "",
        "## Fixed +60m diagnostic after activation (not TP/SL optimization)", "",
        f"- Activation entry WR: **{exec_e['wr']*100:.2f}%**",
        f"- Activation entry expectancy: **{exec_e['expectancy_pct']:.4f}%**",
        f"- Activation entry PF: **{pfmt(exec_e['pf'])}**",
        f"- Activation net PnL: **${exec_e['net_pnl_usd']:.2f}**",
        f"- Same-episode immediate-state expectancy: **{paired_e['expectancy_pct']:.4f}%**",
        f"- Paired expectancy improvement: **{expectancy_improvement:+.4f} pp**", "",
        "## Future-path geometry", "",
        f"- HIGH_STATE episode median MFE/|MAE| ratio: **{base_ratio:.3f}**",
        f"- Activation-entry median MFE/|MAE| ratio: **{exec_ratio:.3f}**",
        f"- Ratio lift: **{ratio_lift:.3f}x**", "",
        "## Year stability", "",
        "| Year | Episodes | Base UP_FIRST | Activations | Activated UP_FIRST | Lift | Exec WR | Exec Exp | PF | Paired state Exp | Δ Exp | Median trigger |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in yr.iterrows():
        lines.append(
            f"| {int(r.test_year)} | {int(r.episode_n)} | {float(r.episode_up_first_rate)*100:.2f}% | {int(r.activation_n)} | {float(r.activated_up_first_rate)*100:.2f}% | {float(r.up_first_lift):.3f}x | {float(r.exec_wr)*100:.2f}% | {float(r.exec_expectancy_pct):.4f}% | {pfmt(r.exec_pf)} | {float(r.paired_state_expectancy_pct):.4f}% | {float(r.expectancy_improvement_pp):+.4f} | {float(r.median_activation_min):.1f}m |"
        )
    lines += ["", "## Top activation features", ""]
    for _, r in fi.head(12).iterrows():
        lines.append(f"- `{r.feature}` — importance {float(r.importance):.4f}")
    lines += ["", "## Batch 2 decision audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    verdict = "READY_FOR_BATCH3" if passed else "ACTIVATION_NOT_READY"
    lines += ["", f"# BATCH 2 VERDICT: {verdict}", "",
              "READY_FOR_BATCH3 means the causal activation layer materially improves directional precision and path geometry inside frozen HIGH_STATE. It does not authorize live trading or TP/SL tuning against the same OOS sample.",
              "ACTIVATION_NOT_READY means Batch 3 must not be used to rescue this activation rule by optimizing exits on the same OOS sample."]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
