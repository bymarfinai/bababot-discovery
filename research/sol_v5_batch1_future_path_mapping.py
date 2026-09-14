#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import sol_impulse_precursor_discovery_v4 as v4

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_V5_BATCH1_FUTURE_PATH_MAPPING"
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
HORIZONS = (5, 10, 15, 20, 30, 45, 60, 90, 120)
ACTIVE_Q = 0.90
MIN_ACTIVE_N = 5000
MIN_LIFT = 1.20


def causal_score_year(ev: pd.DataFrame, test_year: int) -> pd.DataFrame:
    train_start, train_end = v4.training_bounds(test_year)
    test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
    tr = ev[(ev.entry_time >= train_start) & (ev.exit_known_time <= train_end)].copy()
    te = ev[(ev.entry_time >= train_end) & (ev.entry_time < test_end)].copy()
    if tr.empty or te.empty:
        raise RuntimeError(f"missing train/test for {test_year}")

    mt = v4.matched_training(tr, test_year)
    clf = v4.model()
    clf.fit(mt[v4.FEATURES].astype(float).to_numpy(), mt.impulse.astype(int).to_numpy())

    train_scores = clf.predict_proba(tr[v4.FEATURES].astype(float).to_numpy())[:, 1]
    cutoff = float(np.quantile(train_scores, ACTIVE_Q))

    te = te.copy()
    te["test_year"] = test_year
    te["pred_impulse"] = clf.predict_proba(te[v4.FEATURES].astype(float).to_numpy())[:, 1]
    te["state_cutoff"] = cutoff
    te["state_active"] = te.pred_impulse >= cutoff
    return te


def causal_scores(ev: pd.DataFrame) -> pd.DataFrame:
    parts = [causal_score_year(ev, y) for y in v4.TEST_YEARS]
    out = pd.concat(parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    return out


def add_descriptive_deciles(pred: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for y, g in pred.groupby("test_year"):
        q = g.copy()
        q["score_decile"] = pd.qcut(
            q.pred_impulse.rank(method="first"), 10, labels=range(1, 11)
        ).astype(int)
        parts.append(q)
    return pd.concat(parts, ignore_index=True).sort_values("entry_time").reset_index(drop=True)


def map_future_paths(x5: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    z = pred.copy()
    z["entry_time"] = pd.to_datetime(z.entry_time, utc=True)
    z = z[z.entry_time + pd.Timedelta(minutes=120) <= MODEL_END].copy()

    positions = x5.index.get_indexer(pd.DatetimeIndex(z.entry_time))
    valid = positions >= 0
    valid &= positions + 23 < len(x5)
    if valid.any():
        check_idx = np.flatnonzero(valid)
        last_actual = x5.index[positions[check_idx] + 23]
        last_expected = pd.DatetimeIndex(z.entry_time.iloc[check_idx]) + pd.Timedelta(minutes=115)
        contig = np.asarray(last_actual == last_expected)
        v2 = valid.copy()
        v2[check_idx] = contig
        valid = v2
    z = z.iloc[np.flatnonzero(valid)].reset_index(drop=True)
    positions = positions[valid]
    if z.empty:
        raise RuntimeError("no OOS rows with complete +120m future path")

    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()

    anchor = op[positions]
    hi_mat = np.column_stack([hi[positions + j] for j in range(24)])
    lo_mat = np.column_stack([lo[positions + j] for j in range(24)])
    cum_hi = np.maximum.accumulate(hi_mat, axis=1)
    cum_lo = np.minimum.accumulate(lo_mat, axis=1)

    z["anchor_price"] = anchor
    for h in HORIZONS:
        j = h // 5 - 1
        close_h = cl[positions + j]
        z[f"ret_{h}m_pct"] = (close_h / anchor - 1.0) * 100.0
        z[f"mfe_{h}m_pct"] = (cum_hi[:, j] / anchor - 1.0) * 100.0
        z[f"mae_{h}m_pct"] = (cum_lo[:, j] / anchor - 1.0) * 100.0

    arg_mfe = np.argmax(hi_mat, axis=1)
    arg_mae = np.argmin(lo_mat, axis=1)
    z["time_to_mfe_120m_min"] = (arg_mfe + 1) * 5
    z["time_to_mae_120m_min"] = (arg_mae + 1) * 5

    thr = z.impulse_threshold_pct.astype(float).to_numpy()
    up_barrier = anchor * (1.0 + thr / 100.0)
    dn_barrier = anchor * (1.0 - thr / 100.0)
    up_touch = hi_mat >= up_barrier[:, None]
    dn_touch = lo_mat <= dn_barrier[:, None]
    up_any = up_touch.any(axis=1)
    dn_any = dn_touch.any(axis=1)
    up_idx = np.argmax(up_touch, axis=1)
    dn_idx = np.argmax(dn_touch, axis=1)
    up_time = np.where(up_any, (up_idx + 1) * 5.0, np.nan)
    dn_time = np.where(dn_any, (dn_idx + 1) * 5.0, np.nan)
    z["up_impulse_120"] = up_any.astype(int)
    z["down_impulse_120"] = dn_any.astype(int)
    z["time_to_up_impulse_min"] = up_time
    z["time_to_down_impulse_min"] = dn_time

    first = np.full(len(z), "NONE", dtype=object)
    first[up_any & ~dn_any] = "UP_FIRST"
    first[dn_any & ~up_any] = "DOWN_FIRST"
    both = up_any & dn_any
    first[both & (up_time < dn_time)] = "UP_FIRST"
    first[both & (dn_time < up_time)] = "DOWN_FIRST"
    first[both & (up_time == dn_time)] = "BOTH_SAME_BAR"
    z["first_barrier"] = first

    pre_up_mae = np.full(len(z), np.nan, dtype=float)
    rows = np.arange(len(z))
    pre_up_mae[up_any] = (
        cum_lo[rows[up_any], up_idx[up_any]] / anchor[up_any] - 1.0
    ) * 100.0
    z["pre_up_impulse_mae_pct"] = pre_up_mae

    sigma = z.sigma60_pct.astype(float).to_numpy()
    z["mfe_120m_sigma"] = z.mfe_120m_pct.astype(float) / sigma
    z["mae_120m_sigma"] = z.mae_120m_pct.astype(float) / sigma
    z["ret_120m_sigma"] = z.ret_120m_pct.astype(float) / sigma

    archetype = np.full(len(z), "NO_UP_120", dtype=object)
    archetype[up_any & (up_time <= 30)] = "EARLY_UP"
    archetype[up_any & (up_time > 30) & (up_time <= 60)] = "MID_UP"
    archetype[up_any & (up_time > 60)] = "LATE_UP"
    z["path_archetype"] = archetype
    return add_descriptive_deciles(z)


def safe_ratio(a: float, b: float) -> float:
    return float(a / b) if np.isfinite(a) and np.isfinite(b) and b > 0 else np.nan


def summarize(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"n": 0}
    fb = g.first_barrier.astype(str)
    uphit = float(g.up_impulse_120.mean())
    dnhit = float(g.down_impulse_120.mean())
    return {
        "n": int(len(g)),
        "mean_score": float(g.pred_impulse.mean()),
        "v4_impulse60_rate": float(g.impulse.mean()),
        "up_impulse120_rate": uphit,
        "down_impulse120_rate": dnhit,
        "up_first_rate": float((fb == "UP_FIRST").mean()),
        "down_first_rate": float((fb == "DOWN_FIRST").mean()),
        "both_same_bar_rate": float((fb == "BOTH_SAME_BAR").mean()),
        "no_barrier_rate": float((fb == "NONE").mean()),
        "median_ret30_pct": float(g.ret_30m_pct.median()),
        "median_ret60_pct": float(g.ret_60m_pct.median()),
        "median_ret120_pct": float(g.ret_120m_pct.median()),
        "median_mfe30_pct": float(g.mfe_30m_pct.median()),
        "median_mae30_pct": float(g.mae_30m_pct.median()),
        "median_mfe60_pct": float(g.mfe_60m_pct.median()),
        "median_mae60_pct": float(g.mae_60m_pct.median()),
        "median_mfe120_pct": float(g.mfe_120m_pct.median()),
        "median_mae120_pct": float(g.mae_120m_pct.median()),
        "median_mfe120_sigma": float(g.mfe_120m_sigma.median()),
        "median_mae120_sigma": float(g.mae_120m_sigma.median()),
        "median_time_to_mfe120_min": float(g.time_to_mfe_120m_min.median()),
        "median_time_to_mae120_min": float(g.time_to_mae_120m_min.median()),
        "median_time_to_up_impulse_min": float(g.loc[g.up_impulse_120 == 1, "time_to_up_impulse_min"].median()),
        "median_pre_up_impulse_mae_pct": float(g.loc[g.up_impulse_120 == 1, "pre_up_impulse_mae_pct"].median()),
    }


def scope_summaries(mapped: pd.DataFrame):
    rows = []
    for year_label, gy in [("POOLED", mapped)] + [(str(y), g) for y, g in mapped.groupby("test_year")]:
        for scope, q in (("ALL", gy), ("ACTIVE", gy[gy.state_active]), ("INACTIVE", gy[~gy.state_active])):
            rows.append({"year": year_label, "scope": scope, **summarize(q)})
    return pd.DataFrame(rows)


def score_decile_summary(mapped: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, g in mapped.groupby("score_decile"):
        s = summarize(g)
        rows.append({"score_decile": int(d), **s})
    return pd.DataFrame(rows).sort_values("score_decile")


def horizon_quantiles(mapped: pd.DataFrame) -> pd.DataFrame:
    rows = []
    active = mapped[mapped.state_active].copy()
    groups = [("POOLED", active)] + [(str(y), g) for y, g in active.groupby("test_year")]
    for year_label, g in groups:
        for h in HORIZONS:
            r = g[f"ret_{h}m_pct"].astype(float)
            mfe = g[f"mfe_{h}m_pct"].astype(float)
            mae = g[f"mae_{h}m_pct"].astype(float)
            rows.append({
                "year": year_label, "horizon_min": h, "n": int(len(g)),
                "ret_p10": float(r.quantile(.10)), "ret_p25": float(r.quantile(.25)), "ret_p50": float(r.quantile(.50)), "ret_p75": float(r.quantile(.75)), "ret_p90": float(r.quantile(.90)),
                "mfe_p25": float(mfe.quantile(.25)), "mfe_p50": float(mfe.quantile(.50)), "mfe_p75": float(mfe.quantile(.75)),
                "mae_p25": float(mae.quantile(.25)), "mae_p50": float(mae.quantile(.50)), "mae_p75": float(mae.quantile(.75)),
                "close_positive_rate": float((r > 0).mean()),
            })
    return pd.DataFrame(rows)


def timing_archetypes(mapped: pd.DataFrame) -> pd.DataFrame:
    active = mapped[mapped.state_active].copy()
    rows = []
    groups = [("POOLED", active)] + [(str(y), g) for y, g in active.groupby("test_year")]
    order = ("EARLY_UP", "MID_UP", "LATE_UP", "NO_UP_120")
    for year_label, g in groups:
        for a in order:
            q = g[g.path_archetype == a]
            rows.append({
                "year": year_label, "archetype": a, "n": int(len(q)),
                "rate": float(len(q) / len(g)) if len(g) else np.nan,
                "median_pre_up_mae_pct": float(q.pre_up_impulse_mae_pct.median()) if a != "NO_UP_120" and len(q) else np.nan,
                "median_ret120_pct": float(q.ret_120m_pct.median()) if len(q) else np.nan,
            })
    return pd.DataFrame(rows)


def main():
    v4.v3.v1.base.fetch_one = v4.v3.v1.fetch_one_with_volume
    x5, coverage = v4.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    ev = v4.build_opportunities(x5)
    pred = causal_scores(ev)
    mapped = map_future_paths(x5, pred)
    scope = scope_summaries(mapped)
    dec = score_decile_summary(mapped)
    horizons = horizon_quantiles(mapped)
    timing = timing_archetypes(mapped)

    pooled_active = scope[(scope.year == "POOLED") & (scope.scope == "ACTIVE")].iloc[0]
    pooled_inactive = scope[(scope.year == "POOLED") & (scope.scope == "INACTIVE")].iloc[0]
    up_lift = safe_ratio(float(pooled_active.up_impulse120_rate), float(pooled_inactive.up_impulse120_rate))
    up_first_lift = safe_ratio(float(pooled_active.up_first_rate), float(pooled_inactive.up_first_rate))

    years_up = 0
    years_up_first = 0
    for y in v4.TEST_YEARS:
        a = scope[(scope.year == str(y)) & (scope.scope == "ACTIVE")].iloc[0]
        i = scope[(scope.year == str(y)) & (scope.scope == "INACTIVE")].iloc[0]
        years_up += int(float(a.up_impulse120_rate) > float(i.up_impulse120_rate))
        years_up_first += int(float(a.up_first_rate) > float(i.up_first_rate))

    active = mapped[mapped.state_active].copy()
    rho_mfe = float(spearmanr(active.pred_impulse.astype(float), active.mfe_120m_pct.astype(float)).statistic)
    rho_mae = float(spearmanr(active.pred_impulse.astype(float), active.mae_120m_pct.astype(float)).statistic)

    gates = {
        "active_n_ge_5000": int(pooled_active.n) >= MIN_ACTIVE_N,
        "up_impulse120_lift_ge_1_20x": bool(np.isfinite(up_lift) and up_lift >= MIN_LIFT),
        "up_first_lift_ge_1_20x": bool(np.isfinite(up_first_lift) and up_first_lift >= MIN_LIFT),
        "active_up_hit_beats_inactive_ge_3_years": years_up >= 3,
        "active_up_first_beats_inactive_ge_3_years": years_up_first >= 3,
    }
    useful = bool(all(gates.values()))
    verdict = "USEFUL_FOR_BATCH2" if useful else "NO_STABLE_PATH_ENRICHMENT"

    state_cols = [
        "test_year", "signal_time", "entry_time", "hour_utc", "minute_utc", "hour_wib",
        "sigma60_pct", "impulse_threshold_pct", "impulse", "pred_impulse", "state_cutoff", "state_active", "score_decile",
        "ret_30m_pct", "ret_60m_pct", "ret_120m_pct", "mfe_30m_pct", "mae_30m_pct", "mfe_60m_pct", "mae_60m_pct", "mfe_120m_pct", "mae_120m_pct",
        "time_to_mfe_120m_min", "time_to_mae_120m_min", "up_impulse_120", "down_impulse_120", "time_to_up_impulse_min", "time_to_down_impulse_min",
        "first_barrier", "pre_up_impulse_mae_pct", "mfe_120m_sigma", "mae_120m_sigma", "ret_120m_sigma", "path_archetype",
    ]
    mapped[state_cols].to_csv(ROOT / f"{PFX}_StateScoresAndPaths.csv", index=False)
    mapped[mapped.state_active][state_cols].to_csv(ROOT / f"{PFX}_ActiveFuturePaths.csv", index=False)
    scope.to_csv(ROOT / f"{PFX}_ScopeSummary.csv", index=False)
    dec.to_csv(ROOT / f"{PFX}_ScoreDecilePathSummary.csv", index=False)
    horizons.to_csv(ROOT / f"{PFX}_HorizonQuantiles.csv", index=False)
    timing.to_csv(ROOT / f"{PFX}_TimingArchetypes.csv", index=False)
    pd.DataFrame([{"gate": k, "pass": v} for k, v in gates.items()]).to_csv(ROOT / f"{PFX}_GateAudit.csv", index=False)

    lines = [
        "# SOL V5 Batch 1 — Future Path Mapping Result", "",
        f"- Data coverage: **{coverage*100:.6f}%**",
        f"- OOS opportunities with complete +120m path: **{len(mapped)}**",
        f"- Causal HIGH_STATE observations: **{int(pooled_active.n)}**",
        "- HIGH_STATE cutoff: prior-training 90th percentile of frozen V4 score, applied to the following year.",
        "- 2025+ reference_validation remained CLOSED.", "",
        "## HIGH_STATE vs INACTIVE — pooled", "",
        "| Metric | HIGH_STATE | INACTIVE | Lift / difference |",
        "|---|---:|---:|---:|",
        f"| V4 60m impulse rate | {float(pooled_active.v4_impulse60_rate)*100:.2f}% | {float(pooled_inactive.v4_impulse60_rate)*100:.2f}% | {safe_ratio(float(pooled_active.v4_impulse60_rate), float(pooled_inactive.v4_impulse60_rate)):.3f}x |",
        f"| Upside diagnostic barrier hit by 120m | {float(pooled_active.up_impulse120_rate)*100:.2f}% | {float(pooled_inactive.up_impulse120_rate)*100:.2f}% | {up_lift:.3f}x |",
        f"| UP_FIRST | {float(pooled_active.up_first_rate)*100:.2f}% | {float(pooled_inactive.up_first_rate)*100:.2f}% | {up_first_lift:.3f}x |",
        f"| DOWN_FIRST | {float(pooled_active.down_first_rate)*100:.2f}% | {float(pooled_inactive.down_first_rate)*100:.2f}% | {float(pooled_active.down_first_rate)-float(pooled_inactive.down_first_rate):+.2%} |",
        f"| Median MFE 120m | {float(pooled_active.median_mfe120_pct):.3f}% | {float(pooled_inactive.median_mfe120_pct):.3f}% | {float(pooled_active.median_mfe120_pct)-float(pooled_inactive.median_mfe120_pct):+.3f} pp |",
        f"| Median MAE 120m | {float(pooled_active.median_mae120_pct):.3f}% | {float(pooled_inactive.median_mae120_pct):.3f}% | {float(pooled_active.median_mae120_pct)-float(pooled_inactive.median_mae120_pct):+.3f} pp |",
        "",
        "## HIGH_STATE path timing", "",
        f"- Median time-to-MFE(120m window): **{float(pooled_active.median_time_to_mfe120_min):.1f} min**",
        f"- Median time-to-MAE(120m window): **{float(pooled_active.median_time_to_mae120_min):.1f} min**",
        f"- Median time to upside diagnostic impulse, when hit: **{float(pooled_active.median_time_to_up_impulse_min):.1f} min**",
        f"- Median adverse excursion before upside impulse hit: **{float(pooled_active.median_pre_up_impulse_mae_pct):.3f}%**",
        f"- Spearman(V4 score, MFE120) within HIGH_STATE: **{rho_mfe:.4f}**",
        f"- Spearman(V4 score, MAE120) within HIGH_STATE: **{rho_mae:.4f}**",
        "",
        "## HIGH_STATE timing archetypes — pooled", "",
        "| Archetype | N | Rate | Median pre-up MAE | Median 120m return |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, r in timing[timing.year == "POOLED"].iterrows():
        pre = "n/a" if pd.isna(r.median_pre_up_mae_pct) else f"{float(r.median_pre_up_mae_pct):.3f}%"
        lines.append(f"| {r.archetype} | {int(r.n)} | {float(r.rate)*100:.2f}% | {pre} | {float(r.median_ret120_pct):.3f}% |")

    lines += ["", "## Year stability", "", "| Year | Active N | Up hit 120m | Inactive up hit | UP_FIRST | Inactive UP_FIRST | Median MFE120 | Median MAE120 |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for y in v4.TEST_YEARS:
        a = scope[(scope.year == str(y)) & (scope.scope == "ACTIVE")].iloc[0]
        i = scope[(scope.year == str(y)) & (scope.scope == "INACTIVE")].iloc[0]
        lines.append(f"| {y} | {int(a.n)} | {float(a.up_impulse120_rate)*100:.2f}% | {float(i.up_impulse120_rate)*100:.2f}% | {float(a.up_first_rate)*100:.2f}% | {float(i.up_first_rate)*100:.2f}% | {float(a.median_mfe120_pct):.3f}% | {float(a.median_mae120_pct):.3f}% |")

    lines += ["", "## Batch 1 decision audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — `{k}`")
    lines += [
        "", f"# BATCH 1 VERDICT: {verdict}", "",
        "`USEFUL_FOR_BATCH2` means the frozen V4 state materially and repeatedly enriches favorable future-path geometry, so Batch 2 may search for an activation trigger *inside* that state. It is not a live-trading PASS and does not authorize TP/SL optimization.",
        "`NO_STABLE_PATH_ENRICHMENT` means Batch 2 should not be built by retuning the same HIGH_STATE percentile or diagnostic barrier on this OOS sample.",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(verdict + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
