#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_b29_a1_structure_fingerprint as a1
import bnb_b29_a2_character_memory as a2

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_A3_REGIME_MEMORY"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_FOLDS = ROOT / f"{PFX}_FoldMetrics.csv"
OUT_HORIZONS = ROOT / f"{PFX}_HorizonMetrics.csv"
OUT_QUERIES = ROOT / f"{PFX}_Queries.csv.gz"
OUT_REGIMES = ROOT / f"{PFX}_RegimeMetrics.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

SYMBOL = "BNBUSDT"
FROZEN_END = pd.Timestamp("2026-08-26T00:00:00Z")
FROZEN_A1_HASH = "2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6"
MAX_BEHAVIOR = pd.Timedelta(minutes=360)
FOLDS = [2022, 2023, 2024, 2025, 2026]
HORIZONS = [15, 30, 60, 120, 360]
NEIGHBOR_CANDIDATES = 256
K_ANALOGS = 64
MIN_ANALOGS = 48
LOCAL_CAT_PENALTY = 0.35
REGIME_EFF_PENALTY = 0.25

SIM_NUMERIC = list(a2.SIM_NUMERIC)
SIM_CATS = list(a2.SIM_CATS)


def safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    return a.astype(float) / b.astype(float).replace(0.0, np.nan)


def build_regime(raw: pd.DataFrame, fp_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Slow causal regime features from bars fully closed by decision timestamp."""
    x = raw[["open", "high", "low", "close"]].astype(float).copy()
    x.index = pd.DatetimeIndex(x.index) + a1.BAR
    x.index.name = "decision_ts"

    logret = np.log(x["close"]).diff()
    rv6 = logret.rolling(72, min_periods=72).std(ddof=0)
    rv24 = logret.rolling(288, min_periods=288).std(ddof=0)
    logret24 = np.log(x["close"] / x["close"].shift(288))
    trend_z = safe_div(logret24, rv24 * np.sqrt(288.0))

    path24 = x["close"].diff().abs().rolling(288, min_periods=288).sum()
    eff24 = safe_div((x["close"] - x["close"].shift(288)).abs(), path24)
    volratio = safe_div(rv6, rv24)

    out = pd.DataFrame(index=x.index)
    out["macro_trend_z_24h"] = trend_z
    out["macro_eff_24h"] = eff24
    out["macro_vol_ratio_6h_24h"] = volratio

    out["macro_trend_state"] = pd.Series(
        np.select(
            [trend_z < -1.0, trend_z < -0.35, trend_z <= 0.35, trend_z <= 1.0],
            ["STRONG_DOWN", "DOWN", "FLAT", "UP"],
            default="STRONG_UP",
        ), index=out.index, dtype="object"
    )
    out["macro_eff_state"] = pd.Series(
        np.select([eff24 < 0.20, eff24 < 0.40], ["LOW", "MID"], default="HIGH"),
        index=out.index, dtype="object"
    )
    out["macro_vol_state"] = pd.Series(
        np.select([volratio < 0.80, volratio <= 1.25], ["COMPRESS", "NORMAL"], default="EXPAND"),
        index=out.index, dtype="object"
    )
    out["primary_regime"] = out["macro_trend_state"].astype(str) + "|" + out["macro_vol_state"].astype(str)
    out = out.reindex(fp_index)
    return out


def fold_bounds(year: int):
    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    end = FROZEN_END if year == 2026 else pd.Timestamp(f"{year + 1}-01-01T00:00:00Z")
    return start, end


def query_mask(fp: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    m = (fp.index >= start) & (fp.index < end)
    m &= fp["utc_minute"].astype(int).eq(0)
    m &= fp["wib_hour"].astype(int).mod(4).eq(0)
    return m


def select_regime_analogs(mem_idx, mem_cat, mem_eff, q_cat, q_eff, candidate_indices, candidate_distances):
    local_mismatch = (mem_cat[candidate_indices] != q_cat.reshape(1, -1)).mean(axis=1)
    eff_mismatch = (mem_eff[candidate_indices] != q_eff).astype(float)
    adjusted = candidate_distances + LOCAL_CAT_PENALTY * local_mismatch + REGIME_EFF_PENALTY * eff_mismatch
    order = np.argsort(adjusted, kind="stable")
    chosen = []
    seen_dates = set()
    for j in order:
        mi = int(candidate_indices[j])
        day = mem_idx[mi].date()
        if day in seen_dates:
            continue
        seen_dates.add(day)
        chosen.append((mi, float(adjusted[j])))
        if len(chosen) >= K_ANALOGS:
            break
    return chosen


def evaluate_fold(fp: pd.DataFrame, regime: pd.DataFrame, beh: pd.DataFrame, year: int):
    fold_start, fold_end = fold_bounds(year)
    memory_cutoff = fold_start - MAX_BEHAVIOR
    outcome_cols = [f"fwd_{h}" for h in HORIZONS]
    regime_cols = ["macro_trend_z_24h", "macro_eff_24h", "macro_vol_ratio_6h_24h", "macro_trend_state", "macro_eff_state", "macro_vol_state", "primary_regime"]

    reg_valid = regime[regime_cols[:3]].notna().all(axis=1)
    mem_mask = (fp.index <= memory_cutoff) & beh[outcome_cols].notna().all(axis=1) & reg_valid
    qmask = query_mask(fp, fold_start, fold_end) & beh[outcome_cols].notna().all(axis=1) & reg_valid

    mem = fp.loc[mem_mask].copy()
    qry = fp.loc[qmask].copy()
    mem_reg = regime.loc[mem.index, regime_cols].copy()
    qry_reg = regime.loc[qry.index, regime_cols].copy()
    mem_beh = beh.loc[mem.index, outcome_cols]
    qry_beh = beh.loc[qry.index, outcome_cols]

    if len(mem) < 1 or len(qry) < 1:
        raise RuntimeError(f"empty A3 fold {year}: memory={len(mem)} query={len(qry)}")

    mx = mem[SIM_NUMERIC].to_numpy(float)
    qx = qry[SIM_NUMERIC].to_numpy(float)
    med, iqr = a2.robust_scale_fit(mx)
    mz = a2.robust_scale_apply(mx, med, iqr)
    qz = a2.robust_scale_apply(qx, med, iqr)
    if not np.isfinite(mz).all() or not np.isfinite(qz).all():
        raise RuntimeError(f"non-finite scaled features in A3 fold {year}")

    mem_cat = mem[SIM_CATS].astype(str).to_numpy(object)
    qry_cat = qry[SIM_CATS].astype(str).to_numpy(object)
    mem_eff = mem_reg["macro_eff_state"].astype(str).to_numpy(object)
    qry_eff = qry_reg["macro_eff_state"].astype(str).to_numpy(object)
    mem_primary = mem_reg["primary_regime"].astype(str).to_numpy(object)
    qry_primary = qry_reg["primary_regime"].astype(str).to_numpy(object)
    mem_idx = pd.DatetimeIndex(mem.index)

    # Fit one local-neighbor index per causally-known primary regime.
    models = {}
    positions = {}
    for token in sorted(set(mem_primary.tolist())):
        pos = np.flatnonzero(mem_primary == token)
        positions[token] = pos
        if len(pos) >= MIN_ANALOGS:
            n_neighbors = min(NEIGHBOR_CANDIDATES, len(pos))
            model = NearestNeighbors(n_neighbors=n_neighbors, algorithm="ball_tree", metric="euclidean", n_jobs=-1)
            model.fit(mz[pos])
            models[token] = model

    rows = []
    chronology_ok = True
    regime_counts = []
    for qi, ts in enumerate(qry.index):
        token = str(qry_primary[qi])
        if token not in models:
            continue
        pos = positions[token]
        dist_local, ind_local = models[token].kneighbors(qz[qi].reshape(1, -1), return_distance=True)
        candidate_indices = pos[ind_local[0]]
        selected = select_regime_analogs(
            mem_idx, mem_cat, mem_eff, qry_cat[qi], qry_eff[qi],
            candidate_indices, dist_local[0]
        )
        if len(selected) < MIN_ANALOGS:
            continue

        sel_idx = np.array([v[0] for v in selected], dtype=int)
        sel_dist = np.array([v[1] for v in selected], dtype=float)
        sel_ts = mem_idx[sel_idx]
        if not bool(((sel_ts < fold_start) & ((sel_ts + MAX_BEHAVIOR) <= fold_start)).all()):
            chronology_ok = False
        if not bool(np.all(mem_primary[sel_idx] == token)):
            chronology_ok = False

        weights = 1.0 / (1.0 + sel_dist)
        weights /= weights.sum()
        mb = mem_beh.iloc[sel_idx]

        row = {
            "fold": year,
            "query_ts": ts,
            "primary_regime": token,
            "query_macro_eff_state": str(qry_eff[qi]),
            "memory_n": len(mem),
            "regime_memory_n": len(pos),
            "analog_n": len(selected),
            "median_adjusted_distance": float(np.median(sel_dist)),
            "median_similarity": float(np.median(1.0 / (1.0 + sel_dist))),
            "same_primary_regime_rate": float(np.mean(mem_primary[sel_idx] == token)),
            "same_macro_eff_rate": float(np.mean(mem_eff[sel_idx] == qry_eff[qi])),
            "same_structure_rate": float(np.mean(mem_cat[sel_idx, 0] == qry_cat[qi, 0])),
            "same_path_rate": float(np.mean(mem_cat[sel_idx, 6] == qry_cat[qi, 6])),
        }
        for h in HORIZONS:
            vals = mb[f"fwd_{h}"].to_numpy(float)
            row[f"pred_{h}"] = float(np.sum(weights * vals))
            row[f"real_{h}"] = float(qry_beh.iloc[qi][f"fwd_{h}"])
        rows.append(row)
        regime_counts.append((token, len(pos)))

    out = pd.DataFrame(rows)
    if len(out) == 0:
        raise RuntimeError(f"no evaluable A3 queries in fold {year}")

    fold_metrics = {
        "fold": year,
        "fold_start": fold_start,
        "fold_end": fold_end,
        "memory_n": len(mem),
        "query_n": len(qry),
        "evaluable_query_n": len(out),
        "evaluable_coverage": len(out) / len(qry),
        "regime_count_memory": int(pd.Series(mem_primary).nunique()),
        "median_regime_memory_n": float(out["regime_memory_n"].median()),
        "median_analog_n": float(out["analog_n"].median()),
        "median_similarity": float(out["median_similarity"].median()),
        "median_same_primary_regime_rate": float(out["same_primary_regime_rate"].median()),
        "median_same_macro_eff_rate": float(out["same_macro_eff_rate"].median()),
        "median_same_structure_rate": float(out["same_structure_rate"].median()),
        "median_same_path_rate": float(out["same_path_rate"].median()),
        "chronology_ok": bool(chronology_ok),
    }
    rhos, signs, hrows = [], [], []
    for h in HORIZONS:
        rho = a2.rank_corr(out[f"pred_{h}"].to_numpy(float), out[f"real_{h}"].to_numpy(float))
        sign = a2.sign_agreement(out[f"pred_{h}"].to_numpy(float), out[f"real_{h}"].to_numpy(float))
        rhos.append(rho); signs.append(sign)
        hrows.append({"scope": str(year), "horizon_min": h, "n": len(out), "spearman_rho": rho, "sign_agreement": sign})
    fold_metrics["median_rho"] = float(np.nanmedian(rhos))
    fold_metrics["mean_sign_agreement"] = float(np.nanmean(signs))
    return out, fold_metrics, hrows


def fmt_pct(x):
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def fmt_num(x, n=4):
    return "nan" if not np.isfinite(x) else f"{float(x):.{n}f}"


def main():
    base.synthetic_tests()
    raw, coverage = base.load5(SYMBOL)
    if not (pd.DatetimeIndex(raw.index).max() < FROZEN_END):
        raise AssertionError("raw data crosses frozen A1 END")

    fp = a1.build_fingerprint(raw)
    a1_hash = a1.fingerprint_hash(fp)
    a1_hash_ok = a1_hash == FROZEN_A1_HASH
    boundary_ok = bool((fp.index <= FROZEN_END).all())
    schema_ok = all(c in fp.columns for c in SIM_NUMERIC + SIM_CATS)
    regime = build_regime(raw, fp.index)
    beh = a2.build_behaviour(raw, fp.index)

    all_queries, fold_rows, horizon_rows = [], [], []
    for year in FOLDS:
        q, frow, hrows = evaluate_fold(fp, regime, beh, year)
        all_queries.append(q); fold_rows.append(frow); horizon_rows.extend(hrows)
        print(
            f"A3 fold={year} memory={frow['memory_n']} query={frow['query_n']} eval={frow['evaluable_query_n']} "
            f"coverage={frow['evaluable_coverage']:.3f} median_rho={frow['median_rho']:.4f}", flush=True
        )

    Q = pd.concat(all_queries, ignore_index=True)
    F = pd.DataFrame(fold_rows)
    pooled_h = []
    for h in HORIZONS:
        rho = a2.rank_corr(Q[f"pred_{h}"].to_numpy(float), Q[f"real_{h}"].to_numpy(float))
        sign = a2.sign_agreement(Q[f"pred_{h}"].to_numpy(float), Q[f"real_{h}"].to_numpy(float))
        pooled_h.append({"scope": "POOLED", "horizon_min": h, "n": len(Q), "spearman_rho": rho, "sign_agreement": sign})
    H = pd.DataFrame(horizon_rows + pooled_h)

    regime_rows = []
    for token, g in Q.groupby("primary_regime", sort=True):
        rs = [a2.rank_corr(g[f"pred_{h}"].to_numpy(float), g[f"real_{h}"].to_numpy(float)) for h in HORIZONS]
        ss = [a2.sign_agreement(g[f"pred_{h}"].to_numpy(float), g[f"real_{h}"].to_numpy(float)) for h in HORIZONS]
        regime_rows.append({"primary_regime": token, "n": len(g), "median_rho": float(np.nanmedian(rs)), "mean_sign_agreement": float(np.nanmean(ss))})
    R = pd.DataFrame(regime_rows)

    Q.to_csv(OUT_QUERIES, index=False, compression="gzip")
    F.to_csv(OUT_FOLDS, index=False)
    H.to_csv(OUT_HORIZONS, index=False)
    R.to_csv(OUT_REGIMES, index=False)

    pooled = H[H.scope == "POOLED"]
    pooled_rhos = pooled.spearman_rho.to_numpy(float)
    pooled_signs = pooled.sign_agreement.to_numpy(float)

    finite_ok = bool(np.isfinite(Q.select_dtypes(include=[np.number]).to_numpy(float)).all())
    coverage_ok = bool(coverage >= 0.995)
    memory_ok_integrity = bool((F.memory_n >= 20000).all())
    query_ok = bool((F.query_n >= 500).all() and (F.evaluable_query_n >= 500).all())
    eval_coverage_ok = bool((F.evaluable_coverage >= 0.75).all())
    analog_ok = bool((F.median_analog_n >= MIN_ANALOGS).all())
    chronology_ok = bool(F.chronology_ok.all())
    integrity_ok = all([coverage_ok, a1_hash_ok, boundary_ok, schema_ok, finite_ok, memory_ok_integrity, query_ok, eval_coverage_ok, analog_ok, chronology_ok])

    struct_med = float(Q.same_structure_rate.median())
    path_med = float(Q.same_path_rate.median())
    primary_med = float(Q.same_primary_regime_rate.median())
    eff_med = float(Q.same_macro_eff_rate.median())
    coherence_ok = bool(struct_med >= 0.55 and path_med >= 0.60 and primary_med == 1.0 and eff_med >= 0.50)

    positive_h = int(np.sum(pooled_rhos > 0))
    median_rho = float(np.nanmedian(pooled_rhos))
    mean_sign = float(np.nanmean(pooled_signs))
    fold_rho = F.set_index("fold")["median_rho"]
    positive_folds = int(np.sum(fold_rho.to_numpy(float) > 0))
    recent_ok = bool(float(fold_rho.loc[2025]) > 0 and float(fold_rho.loc[2026]) > 0)
    worst_fold = float(np.nanmin(fold_rho.to_numpy(float)))
    behaviour_ok = bool(positive_h >= 4 and median_rho >= 0.03 and mean_sign >= 0.51 and positive_folds >= 4 and recent_ok and worst_fold >= -0.02)

    if not integrity_ok:
        status = "BNB_B29_A3_DATA_TOOLING_FAILURE"
    elif coherence_ok and behaviour_ok:
        status = "BNB_B29_A3_REGIME_MEMORY_PASS"
    else:
        status = "BNB_B29_A3_REGIME_MEMORY_REJECT"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B29 A3 — Regime-Aware Character Memory Result", "",
        f"**Status: {status}**", "",
        "A3 tests a causally-known slow-regime hard gate before local A1 structural similarity. No entry, TP, SL, leverage, fees, PnL, or live orders are tested.", "",
        "## Frozen identity", "",
        f"- A1 fingerprint hash: `{a1_hash}`",
        f"- Frozen A1 hash match: **{'PASS' if a1_hash_ok else 'FAIL'}**",
        f"- Raw 5m coverage: {coverage:.6%}",
        f"- Post-cutoff data touched: **{'NO' if boundary_ok else 'YES'}**",
        f"- Evaluable queries: {len(Q):,}", "",
        "## Walk-forward folds", "",
        "| Fold | Memory N | Query N | Eval N | Coverage | Regimes | Median regime N | Analog N | Same regime | Same macro eff | Same structure | Same path | Median rho | Mean sign |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in F.iterrows():
        lines.append(
            f"| {int(r['fold'])} | {int(r['memory_n']):,} | {int(r['query_n']):,} | {int(r['evaluable_query_n']):,} | {fmt_pct(r['evaluable_coverage'])} | "
            f"{int(r['regime_count_memory'])} | {r['median_regime_memory_n']:.0f} | {r['median_analog_n']:.0f} | {fmt_pct(r['median_same_primary_regime_rate'])} | "
            f"{fmt_pct(r['median_same_macro_eff_rate'])} | {fmt_pct(r['median_same_structure_rate'])} | {fmt_pct(r['median_same_path_rate'])} | "
            f"{fmt_num(r['median_rho'])} | {fmt_pct(r['mean_sign_agreement'])} |"
        )
    lines += ["", "## Pooled fixed-horizon behaviour", "", "| Horizon | N | Spearman rho | Sign agreement |", "|---:|---:|---:|---:|"]
    for _, r in pooled.iterrows():
        lines.append(f"| +{int(r['horizon_min'])}m | {int(r['n']):,} | {fmt_num(r['spearman_rho'])} | {fmt_pct(r['sign_agreement'])} |")

    lines += [
        "", "## Frozen gates", "",
        f"- Exact A1 hash: **{'PASS' if a1_hash_ok else 'FAIL'}**",
        f"- Boundary/schema/numeric/chronology integrity: **{'PASS' if integrity_ok else 'FAIL'}**",
        f"- Evaluable coverage >=75% each fold: **{'PASS' if eval_coverage_ok else 'FAIL'}**",
        f"- Structural/regime coherence: **{'PASS' if coherence_ok else 'FAIL'}** (structure {fmt_pct(struct_med)}, path {fmt_pct(path_med)}, primary {fmt_pct(primary_med)}, macro-eff {fmt_pct(eff_med)})",
        f"- Positive pooled horizons: **{positive_h}/5** (need >=4)",
        f"- Median pooled rho: **{median_rho:.4f}** (need >=0.0300)",
        f"- Mean pooled sign agreement: **{fmt_pct(mean_sign)}** (need >=51.00%)",
        f"- Positive folds: **{positive_folds}/5** (need >=4)",
        f"- 2025 & 2026 positive: **{'PASS' if recent_ok else 'FAIL'}**",
        f"- Worst fold rho: **{worst_fold:.4f}** (must be >=-0.0200)",
        f"- Aggregate behavioural gate: **{'PASS' if behaviour_ok else 'FAIL'}**", "",
        "## Decision", "", f"**{status}**", "",
        "Frozen stop rule applies after this valid identity. No live orders were placed.", ""
    ]
    OUT_RESULT.write_text("\n".join(lines))
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
