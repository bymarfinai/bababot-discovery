#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_b29_a1_structure_fingerprint as a1

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_A2_CHARACTER_MEMORY"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_FOLDS = ROOT / f"{PFX}_FoldMetrics.csv"
OUT_HORIZONS = ROOT / f"{PFX}_HorizonMetrics.csv"
OUT_QUERIES = ROOT / f"{PFX}_Queries.csv.gz"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

SYMBOL = "BNBUSDT"
FROZEN_END = pd.Timestamp("2026-08-26T00:00:00Z")
FROZEN_A1_HASH = "2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6"
MAX_BEHAVIOR = pd.Timedelta(minutes=360)
NEIGHBOR_CANDIDATES = 256
K_ANALOGS = 64
MIN_ANALOGS = 48
CAT_PENALTY = 0.35

FOLDS = [2022, 2023, 2024, 2025, 2026]
HORIZONS = [15, 30, 60, 120, 360]

SIM_NUMERIC = [
    "disp_atr_15", "disp_atr_30", "disp_atr_60", "disp_atr_120", "disp_atr_360",
    "eff_30", "eff_60", "eff_120", "eff_360",
    "atr30_atr360", "atr60_atr360", "rv60_rv360",
    "body_range", "close_location",
    "range_pos_60", "range_pos_120", "range_pos_360",
    "dist_prior_high_60_atr", "dist_prior_low_60_atr",
    "dist_prior_high_120_atr", "dist_prior_low_120_atr",
    "sweep_high_60", "sweep_low_60", "break_high_60", "break_low_60",
    "tod_sin", "tod_cos",
]
SIM_CATS = [
    "structure_state", "trend_state", "efficiency_state", "vol_state",
    "range_state", "liquidity_state", "path_state", "wib_bucket",
]


def robust_scale_fit(x: np.ndarray):
    med = np.nanmedian(x, axis=0)
    q25 = np.nanpercentile(x, 25, axis=0)
    q75 = np.nanpercentile(x, 75, axis=0)
    iqr = q75 - q25
    iqr[~np.isfinite(iqr) | (np.abs(iqr) < 1e-12)] = 1.0
    return med, iqr


def robust_scale_apply(x: np.ndarray, med: np.ndarray, iqr: np.ndarray):
    z = (x - med) / iqr
    return np.clip(z, -8.0, 8.0)


def rank_corr(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if int(m.sum()) < 3:
        return np.nan
    rx = pd.Series(x[m]).rank(method="average").to_numpy(float)
    ry = pd.Series(y[m]).rank(method="average").to_numpy(float)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def sign_agreement(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    if not m.any():
        return np.nan
    return float(np.mean(np.sign(x[m]) == np.sign(y[m])))


def build_behaviour(raw: pd.DataFrame, fp_index: pd.DatetimeIndex) -> pd.DataFrame:
    close = pd.Series(raw["close"].to_numpy(float), index=pd.DatetimeIndex(raw.index) + a1.BAR)
    out = pd.DataFrame(index=fp_index)
    for h in HORIZONS:
        steps = h // 5
        fwd = close.shift(-steps) / close - 1.0
        out[f"fwd_{h}"] = fwd.reindex(fp_index)
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


def select_analogs(
    mem_idx: pd.DatetimeIndex,
    mem_cat: np.ndarray,
    q_cat: np.ndarray,
    candidate_indices: np.ndarray,
    candidate_distances: np.ndarray,
):
    mismatch = (mem_cat[candidate_indices] != q_cat.reshape(1, -1)).mean(axis=1)
    adjusted = candidate_distances + CAT_PENALTY * mismatch
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


def evaluate_fold(fp: pd.DataFrame, beh: pd.DataFrame, year: int):
    fold_start, fold_end = fold_bounds(year)
    memory_cutoff = fold_start - MAX_BEHAVIOR
    outcome_cols = [f"fwd_{h}" for h in HORIZONS]

    mem_mask = fp.index <= memory_cutoff
    mem_mask &= beh[outcome_cols].notna().all(axis=1)
    qmask = query_mask(fp, fold_start, fold_end)
    qmask &= beh[outcome_cols].notna().all(axis=1)

    mem = fp.loc[mem_mask].copy()
    qry = fp.loc[qmask].copy()
    mem_beh = beh.loc[mem.index, outcome_cols]
    qry_beh = beh.loc[qry.index, outcome_cols]

    if len(mem) < 1 or len(qry) < 1:
        raise RuntimeError(f"empty fold {year}: memory={len(mem)} query={len(qry)}")

    mx = mem[SIM_NUMERIC].to_numpy(float)
    qx = qry[SIM_NUMERIC].to_numpy(float)
    med, iqr = robust_scale_fit(mx)
    mz = robust_scale_apply(mx, med, iqr)
    qz = robust_scale_apply(qx, med, iqr)
    if not np.isfinite(mz).all() or not np.isfinite(qz).all():
        raise RuntimeError(f"non-finite scaled features in fold {year}")

    n_neighbors = min(NEIGHBOR_CANDIDATES, len(mem))
    nn = NearestNeighbors(n_neighbors=n_neighbors, algorithm="ball_tree", metric="euclidean", n_jobs=-1)
    nn.fit(mz)
    dists, inds = nn.kneighbors(qz, return_distance=True)

    mem_cat = mem[SIM_CATS].astype(str).to_numpy(object)
    qry_cat = qry[SIM_CATS].astype(str).to_numpy(object)
    mem_idx = pd.DatetimeIndex(mem.index)

    rows = []
    chronology_ok = True
    for qi, ts in enumerate(qry.index):
        selected = select_analogs(mem_idx, mem_cat, qry_cat[qi], inds[qi], dists[qi])
        if len(selected) < MIN_ANALOGS:
            continue
        sel_idx = np.array([x[0] for x in selected], dtype=int)
        sel_dist = np.array([x[1] for x in selected], dtype=float)
        sel_ts = mem_idx[sel_idx]
        if not bool(((sel_ts < fold_start) & ((sel_ts + MAX_BEHAVIOR) <= fold_start)).all()):
            chronology_ok = False

        weights = 1.0 / (1.0 + sel_dist)
        weights = weights / weights.sum()
        mb = mem_beh.iloc[sel_idx]

        row = {
            "fold": year,
            "query_ts": ts,
            "memory_n": len(mem),
            "analog_n": len(selected),
            "median_adjusted_distance": float(np.median(sel_dist)),
            "median_similarity": float(np.median(1.0 / (1.0 + sel_dist))),
            "same_structure_rate": float(np.mean(mem_cat[sel_idx, 0] == qry_cat[qi, 0])),
            "same_path_rate": float(np.mean(mem_cat[sel_idx, 6] == qry_cat[qi, 6])),
        }
        for h in HORIZONS:
            vals = mb[f"fwd_{h}"].to_numpy(float)
            row[f"pred_{h}"] = float(np.sum(weights * vals))
            row[f"real_{h}"] = float(qry_beh.iloc[qi][f"fwd_{h}"])
        rows.append(row)

    out = pd.DataFrame(rows)
    if len(out) == 0:
        raise RuntimeError(f"no evaluable queries in fold {year}")

    fold_metrics = {
        "fold": year,
        "fold_start": fold_start,
        "fold_end": fold_end,
        "memory_n": len(mem),
        "query_n": len(qry),
        "evaluable_query_n": len(out),
        "median_analog_n": float(out["analog_n"].median()),
        "median_adjusted_distance": float(out["median_adjusted_distance"].median()),
        "median_similarity": float(out["median_similarity"].median()),
        "median_same_structure_rate": float(out["same_structure_rate"].median()),
        "median_same_path_rate": float(out["same_path_rate"].median()),
        "chronology_ok": bool(chronology_ok),
    }
    rhos = []
    signs = []
    horizon_rows = []
    for h in HORIZONS:
        rho = rank_corr(out[f"pred_{h}"].to_numpy(float), out[f"real_{h}"].to_numpy(float))
        sign = sign_agreement(out[f"pred_{h}"].to_numpy(float), out[f"real_{h}"].to_numpy(float))
        rhos.append(rho); signs.append(sign)
        horizon_rows.append({"scope": str(year), "horizon_min": h, "n": len(out), "spearman_rho": rho, "sign_agreement": sign})
    fold_metrics["median_rho"] = float(np.nanmedian(rhos))
    fold_metrics["mean_sign_agreement"] = float(np.nanmean(signs))
    return out, fold_metrics, horizon_rows


def fmt_pct(x):
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def fmt_num(x, digits=4):
    return "nan" if not np.isfinite(x) else f"{float(x):.{digits}f}"


def main():
    base.synthetic_tests()
    raw, coverage = base.load5(SYMBOL)
    if not (pd.DatetimeIndex(raw.index).max() < FROZEN_END):
        raise AssertionError("raw data crosses frozen A1 END")

    fp = a1.build_fingerprint(raw)
    a1_hash = a1.fingerprint_hash(fp)
    a1_hash_ok = a1_hash == FROZEN_A1_HASH
    schema_ok = all(c in fp.columns for c in SIM_NUMERIC + SIM_CATS)
    boundary_ok = bool((fp.index <= FROZEN_END).all())
    beh = build_behaviour(raw, fp.index)

    all_queries = []
    fold_rows = []
    horizon_rows = []
    for year in FOLDS:
        q, frow, hrows = evaluate_fold(fp, beh, year)
        all_queries.append(q)
        fold_rows.append(frow)
        horizon_rows.extend(hrows)
        print(f"fold={year} memory={frow['memory_n']} query={frow['query_n']} evaluable={frow['evaluable_query_n']} median_rho={frow['median_rho']:.4f}")

    Q = pd.concat(all_queries, ignore_index=True)
    F = pd.DataFrame(fold_rows)

    pooled_h = []
    for h in HORIZONS:
        rho = rank_corr(Q[f"pred_{h}"].to_numpy(float), Q[f"real_{h}"].to_numpy(float))
        sign = sign_agreement(Q[f"pred_{h}"].to_numpy(float), Q[f"real_{h}"].to_numpy(float))
        pooled_h.append({"scope": "POOLED", "horizon_min": h, "n": len(Q), "spearman_rho": rho, "sign_agreement": sign})
    H = pd.DataFrame(horizon_rows + pooled_h)

    Q.to_csv(OUT_QUERIES, index=False, compression="gzip")
    F.to_csv(OUT_FOLDS, index=False)
    H.to_csv(OUT_HORIZONS, index=False)

    pooled = H[H.scope == "POOLED"].copy()
    pooled_rhos = pooled.spearman_rho.to_numpy(float)
    pooled_signs = pooled.sign_agreement.to_numpy(float)

    finite_ok = bool(np.isfinite(Q.select_dtypes(include=[np.number]).to_numpy(float)).all())
    fold_memory_ok = bool((F.memory_n >= 20000).all())
    fold_query_ok = bool((F.evaluable_query_n >= 500).all())
    analog_ok = bool((F.median_analog_n >= MIN_ANALOGS).all())
    chronology_ok = bool(F.chronology_ok.all())
    coverage_ok = bool(coverage >= 0.995)
    integrity_ok = all([coverage_ok, a1_hash_ok, schema_ok, boundary_ok, finite_ok, fold_memory_ok, fold_query_ok, analog_ok, chronology_ok])

    struct_med = float(Q.same_structure_rate.median())
    path_med = float(Q.same_path_rate.median())
    structural_ok = bool(struct_med >= 0.35 and path_med >= 0.35)

    positive_h = int(np.sum(pooled_rhos > 0))
    median_pooled_rho = float(np.nanmedian(pooled_rhos))
    mean_pooled_sign = float(np.nanmean(pooled_signs))
    positive_folds = int(np.sum(F.median_rho.to_numpy(float) > 0))
    memory_ok = bool(positive_h >= 4 and median_pooled_rho >= 0.03 and mean_pooled_sign >= 0.505 and positive_folds >= 3)

    if not integrity_ok:
        status = "BNB_B29_A2_DATA_TOOLING_FAILURE"
    elif structural_ok and memory_ok:
        status = "BNB_B29_A2_CHARACTER_MEMORY_PASS"
    else:
        status = "BNB_B29_A2_CHARACTER_MEMORY_REJECT"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B29 A2 — Character Memory Result", "",
        f"**Status: {status}**", "",
        "A2 evaluates walk-forward structural similarity and forward price behaviour only. It does not define or test entry, TP, SL, leverage, fees, PnL, or live execution.", "",
        "## Frozen representation / data", "",
        f"- A1 fingerprint hash: `{a1_hash}`",
        f"- Frozen A1 hash match: **{'PASS' if a1_hash_ok else 'FAIL'}**",
        f"- Raw 5m coverage: {coverage:.6%}",
        f"- Post-{FROZEN_END} data touched: **{'NO' if boundary_ok else 'YES'}**",
        f"- Evaluable sampled queries: {len(Q):,}", "",
        "## Walk-forward folds", "",
        "| Fold | Memory N | Query N | Evaluable | Median analog N | Similarity | Same structure | Same path | Median rho | Mean sign | Chronology |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in F.itertuples(index=False):
        lines.append(
            f"| {int(r.fold)} | {int(r.memory_n):,} | {int(r.query_n):,} | {int(r.evaluable_query_n):,} | "
            f"{r.median_analog_n:.0f} | {r.median_similarity:.4f} | {fmt_pct(r.median_same_structure_rate)} | "
            f"{fmt_pct(r.median_same_path_rate)} | {r.median_rho:.4f} | {fmt_pct(r.mean_sign_agreement)} | {'PASS' if r.chronology_ok else 'FAIL'} |"
        )

    lines += ["", "## Pooled fixed-horizon behaviour", "",
              "| Horizon | N | Spearman rho | Sign agreement |",
              "|---:|---:|---:|---:|"]
    for r in pooled.itertuples(index=False):
        lines.append(f"| +{int(r.horizon_min)}m | {int(r.n):,} | {fmt_num(r.spearman_rho)} | {fmt_pct(r.sign_agreement)} |")

    lines += [
        "", "## Frozen gates", "",
        f"- Coverage: **{'PASS' if coverage_ok else 'FAIL'}**",
        f"- A1 hash guard: **{'PASS' if a1_hash_ok else 'FAIL'}**",
        f"- Schema guard: **{'PASS' if schema_ok else 'FAIL'}**",
        f"- Frozen boundary: **{'PASS' if boundary_ok else 'FAIL'}**",
        f"- Numeric finite: **{'PASS' if finite_ok else 'FAIL'}**",
        f"- Memory-size gate: **{'PASS' if fold_memory_ok else 'FAIL'}**",
        f"- Query-count gate: **{'PASS' if fold_query_ok else 'FAIL'}**",
        f"- Analog-count gate: **{'PASS' if analog_ok else 'FAIL'}**",
        f"- Chronology / behaviour-known gate: **{'PASS' if chronology_ok else 'FAIL'}**",
        f"- Structural coherence: **{'PASS' if structural_ok else 'FAIL'}** (median structure {fmt_pct(struct_med)}, path {fmt_pct(path_med)})",
        f"- Positive pooled horizons: **{positive_h}/5** (need >=4)",
        f"- Median pooled rho: **{median_pooled_rho:.4f}** (need >=0.0300)",
        f"- Mean pooled sign agreement: **{fmt_pct(mean_pooled_sign)}** (need >=50.50%)",
        f"- Positive chronological folds: **{positive_folds}/5** (need >=3)",
        f"- Aggregate character-memory gate: **{'PASS' if memory_ok else 'FAIL'}**", "",
        "## Decision", "",
        f"**{status}**", "",
        "If PASS, freeze A2 as a reusable BNB character-memory layer before any entry/TP/SL work. If REJECT, do not tune this A2 identity against the same results.", "",
        "No live orders were placed.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
