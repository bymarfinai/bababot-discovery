#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import bnb_b29_a1_structure_fingerprint as a1
import bnb_b29_a2_character_memory as a2
import bnb_b29_a2_character_memory_stable_runner as stable
import bnb_b29_a3_regime_aware_character_memory as a3

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_A4_SELECTIVE_EVIDENCE"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_FOLDS = ROOT / f"{PFX}_FoldMetrics.csv"
OUT_HORIZONS = ROOT / f"{PFX}_HorizonMetrics.csv"
OUT_QUERIES = ROOT / f"{PFX}_SelectedQueries.csv.gz"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

SYMBOL = "BNBUSDT"
FROZEN_END = pd.Timestamp("2026-08-26T00:00:00Z")
FROZEN_A1_HASH = "2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6"
FOLDS = [2022, 2023, 2024, 2025, 2026]
HORIZONS = [15, 30, 60, 120, 360]

# Frozen A4 evidence thresholds.
MIN_MEDIAN_ABS_PRED = 0.00050
MIN_MAX_ABS_PRED = 0.00100
MIN_SIMILARITY = 0.35
MIN_STRUCTURE = 0.50
MIN_PATH = 0.50
MIN_REGIME_MEMORY = 1000
REQUIRED_ANALOGS = 64

# Accepted A3 parent baseline from its frozen valid result.
A3_BASELINE_MEAN_SIGN = 0.5061
A3_BASELINE_MEDIAN_RHO = 0.0198


def evidence_columns(q: pd.DataFrame) -> pd.DataFrame:
    out = q.copy()
    pred_cols = [f"pred_{h}" for h in HORIZONS]
    pred = out[pred_cols].to_numpy(float)
    signs = np.sign(pred)
    sign_sum = signs.sum(axis=1)
    nonzero = np.all(signs != 0.0, axis=1)
    all_same = nonzero & (np.abs(sign_sum) == len(HORIZONS))
    out["direction_consensus_5of5"] = all_same
    out["diagnostic_direction"] = np.where(sign_sum > 0, 1, np.where(sign_sum < 0, -1, 0)).astype(int)
    out["median_abs_pred"] = np.median(np.abs(pred), axis=1)
    out["max_abs_pred"] = np.max(np.abs(pred), axis=1)

    clauses = {
        "gate_direction": out["direction_consensus_5of5"].astype(bool),
        "gate_strength": (out["median_abs_pred"] >= MIN_MEDIAN_ABS_PRED) & (out["max_abs_pred"] >= MIN_MAX_ABS_PRED),
        "gate_similarity": out["median_similarity"] >= MIN_SIMILARITY,
        "gate_structure": out["same_structure_rate"] >= MIN_STRUCTURE,
        "gate_path": out["same_path_rate"] >= MIN_PATH,
        "gate_density": (out["regime_memory_n"] >= MIN_REGIME_MEMORY) & (out["analog_n"] == REQUIRED_ANALOGS),
    }
    for name, mask in clauses.items():
        out[name] = mask.astype(bool)
    gate_cols = list(clauses)
    out["evidence_ready"] = out[gate_cols].all(axis=1)
    out["evidence_state"] = np.where(out["evidence_ready"], "EVIDENCE_READY", "NO_MEMORY")
    return out


def directional_hit(real: np.ndarray, direction: np.ndarray) -> float:
    real = np.asarray(real, dtype=float)
    direction = np.asarray(direction, dtype=int)
    m = np.isfinite(real) & (direction != 0)
    if not m.any():
        return np.nan
    return float(np.mean(np.sign(real[m]) == direction[m]))


def fmt_pct(x: float) -> str:
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def fmt_num(x: float, n: int = 4) -> str:
    return "nan" if not np.isfinite(x) else f"{float(x):.{n}f}"


def main():
    # Exact accepted A1 identity; stable loader retries rather than accepting a missing tail.
    raw, coverage = stable.load5_frozen_identity(SYMBOL)
    idx = pd.DatetimeIndex(raw.index)
    raw_boundary_ok = bool(len(idx) and idx.max() < FROZEN_END)

    fp = a1.build_fingerprint(raw)
    a1_hash = a1.fingerprint_hash(fp)
    a1_hash_ok = a1_hash == FROZEN_A1_HASH
    fp_boundary_ok = bool((fp.index <= FROZEN_END).all())
    regime = a3.build_regime(raw, fp.index)
    beh = a2.build_behaviour(raw, fp.index)

    parent_queries = []
    selected_queries = []
    fold_rows = []
    horizon_rows = []
    parent_chronology_ok = True

    for year in FOLDS:
        q_parent, parent_fold, _ = a3.evaluate_fold(fp, regime, beh, year)
        parent_chronology_ok = parent_chronology_ok and bool(parent_fold["chronology_ok"])
        q = evidence_columns(q_parent)
        s = q[q["evidence_ready"]].copy()
        parent_queries.append(q)
        selected_queries.append(s)

        fold_hits = []
        fold_rhos = []
        for h in HORIZONS:
            hit = directional_hit(s[f"real_{h}"].to_numpy(float), s["diagnostic_direction"].to_numpy(int)) if len(s) else np.nan
            rho = a2.rank_corr(s[f"pred_{h}"].to_numpy(float), s[f"real_{h}"].to_numpy(float)) if len(s) >= 3 else np.nan
            fold_hits.append(hit)
            fold_rhos.append(rho)
            horizon_rows.append({
                "scope": str(year),
                "horizon_min": h,
                "n": len(s),
                "directional_hit": hit,
                "spearman_rho": rho,
            })

        fold_rows.append({
            "fold": year,
            "parent_n": len(q),
            "selected_n": len(s),
            "selected_coverage": (len(s) / len(q)) if len(q) else np.nan,
            "median_similarity": float(s["median_similarity"].median()) if len(s) else np.nan,
            "median_structure_rate": float(s["same_structure_rate"].median()) if len(s) else np.nan,
            "median_path_rate": float(s["same_path_rate"].median()) if len(s) else np.nan,
            "median_regime_memory_n": float(s["regime_memory_n"].median()) if len(s) else np.nan,
            "median_abs_pred": float(s["median_abs_pred"].median()) if len(s) else np.nan,
            "mean_directional_hit": float(np.nanmean(fold_hits)) if len(s) else np.nan,
            "median_rho": float(np.nanmedian(fold_rhos)) if len(s) else np.nan,
        })
        print(
            f"A4 fold={year} parent={len(q)} selected={len(s)} coverage={len(s)/len(q):.3%} "
            f"mean_hit={np.nanmean(fold_hits) if len(s) else np.nan:.4f} median_rho={np.nanmedian(fold_rhos) if len(s) else np.nan:.4f}",
            flush=True,
        )

    P = pd.concat(parent_queries, ignore_index=True)
    S = pd.concat(selected_queries, ignore_index=True)
    F = pd.DataFrame(fold_rows)

    pooled_hits = []
    pooled_rhos = []
    for h in HORIZONS:
        hit = directional_hit(S[f"real_{h}"].to_numpy(float), S["diagnostic_direction"].to_numpy(int)) if len(S) else np.nan
        rho = a2.rank_corr(S[f"pred_{h}"].to_numpy(float), S[f"real_{h}"].to_numpy(float)) if len(S) >= 3 else np.nan
        pooled_hits.append(hit)
        pooled_rhos.append(rho)
        horizon_rows.append({
            "scope": "POOLED",
            "horizon_min": h,
            "n": len(S),
            "directional_hit": hit,
            "spearman_rho": rho,
        })
    H = pd.DataFrame(horizon_rows)

    S.to_csv(OUT_QUERIES, index=False, compression="gzip")
    F.to_csv(OUT_FOLDS, index=False)
    H.to_csv(OUT_HORIZONS, index=False)

    # Integrity: every selected row must satisfy the preregistered clauses.
    gate_cols = ["gate_direction", "gate_strength", "gate_similarity", "gate_structure", "gate_path", "gate_density"]
    selected_clause_ok = bool(len(S) > 0 and S[gate_cols].all(axis=None))
    finite_cols = [
        "median_similarity", "same_structure_rate", "same_path_rate", "regime_memory_n", "analog_n",
        "median_abs_pred", "max_abs_pred",
    ] + [f"pred_{h}" for h in HORIZONS] + [f"real_{h}" for h in HORIZONS]
    numeric_finite_ok = bool(len(S) > 0 and np.isfinite(S[finite_cols].to_numpy(float)).all())
    integrity_ok = all([
        coverage >= 0.995,
        raw_boundary_ok,
        fp_boundary_ok,
        a1_hash_ok,
        parent_chronology_ok,
        selected_clause_ok,
        numeric_finite_ok,
    ])

    # Selectivity gates.
    per_fold_n_ok = bool((F["selected_n"] >= 50).all())
    per_fold_cov_ok = bool(((F["selected_coverage"] >= 0.01) & (F["selected_coverage"] <= 0.35)).all())
    pooled_coverage = (len(S) / len(P)) if len(P) else np.nan
    pooled_cov_ok = bool(np.isfinite(pooled_coverage) and pooled_coverage <= 0.25)
    selectivity_ok = all([per_fold_n_ok, per_fold_cov_ok, pooled_cov_ok])

    # Behavioural gates.
    mean_hit = float(np.nanmean(pooled_hits))
    median_rho = float(np.nanmedian(pooled_rhos))
    hit_horizons_52 = int(np.sum(np.asarray(pooled_hits, dtype=float) >= 0.52))
    positive_folds = int(np.sum(F["median_rho"].to_numpy(float) > 0.0))
    no_fold_below_50 = bool((F["mean_directional_hit"] >= 0.50).all())
    hit_2025 = float(F.loc[F.fold == 2025, "mean_directional_hit"].iloc[0])
    hit_2026 = float(F.loc[F.fold == 2026, "mean_directional_hit"].iloc[0])
    sign_lift_pp = 100.0 * (mean_hit - A3_BASELINE_MEAN_SIGN)
    rho_lift = median_rho - A3_BASELINE_MEDIAN_RHO

    behavioural_ok = all([
        mean_hit >= 0.525,
        hit_horizons_52 >= 4,
        median_rho >= 0.0400,
        positive_folds >= 4,
        no_fold_below_50,
        hit_2025 >= 0.515,
        hit_2026 >= 0.515,
        sign_lift_pp >= 1.50,
        rho_lift >= 0.0150,
    ])

    if not integrity_ok:
        status = "BNB_B29_A4_DATA_TOOLING_FAILURE"
    elif selectivity_ok and behavioural_ok:
        status = "BNB_B29_A4_SELECTIVE_EVIDENCE_PASS"
    else:
        status = "BNB_B29_A4_SELECTIVE_EVIDENCE_REJECT"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B29 A4 — Selective Character Evidence Result", "",
        f"**Status: {status}**", "",
        "A4 applies an outcome-blind sparse evidence gate to the frozen A3 regime-aware character memory. No entry, TP, SL, leverage, fees, PnL or live orders are tested.", "",
        "## Frozen identity", "",
        f"- A1 fingerprint hash: `{a1_hash}`",
        f"- Frozen A1 hash match: **{'PASS' if a1_hash_ok else 'FAIL'}**",
        f"- Raw 5m coverage: {coverage:.6%}",
        f"- Post-cutoff data touched: **{'NO' if raw_boundary_ok and fp_boundary_ok else 'YES'}**",
        f"- A3 parent queries: {len(P):,}",
        f"- A4 EVIDENCE_READY queries: {len(S):,}",
        f"- Pooled selected coverage: {fmt_pct(pooled_coverage)}", "",
        "## Walk-forward folds", "",
        "| Fold | Parent N | Ready N | Coverage | Mean directional hit | Median rho | Similarity | Structure | Path | Median regime N | Median abs pred |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in F.iterrows():
        lines.append(
            f"| {int(r.fold)} | {int(r.parent_n):,} | {int(r.selected_n):,} | {fmt_pct(r.selected_coverage)} | "
            f"{fmt_pct(r.mean_directional_hit)} | {fmt_num(r.median_rho)} | {fmt_pct(r.median_similarity)} | "
            f"{fmt_pct(r.median_structure_rate)} | {fmt_pct(r.median_path_rate)} | {int(r.median_regime_memory_n) if np.isfinite(r.median_regime_memory_n) else 0:,} | {fmt_pct(r.median_abs_pred)} |"
        )

    lines += ["", "## Pooled fixed-horizon behaviour", "", "| Horizon | N | Directional hit | Spearman rho |", "|---:|---:|---:|---:|"]
    for h, hit, rho in zip(HORIZONS, pooled_hits, pooled_rhos):
        lines.append(f"| +{h}m | {len(S):,} | {fmt_pct(hit)} | {fmt_num(rho)} |")

    lines += [
        "", "## Frozen gates", "",
        f"- Exact A1 / boundary / chronology / finite / clause integrity: **{'PASS' if integrity_ok else 'FAIL'}**",
        f"- Each fold Ready N >=50: **{'PASS' if per_fold_n_ok else 'FAIL'}**",
        f"- Each fold coverage 1%-35%: **{'PASS' if per_fold_cov_ok else 'FAIL'}**",
        f"- Pooled coverage <=25%: **{'PASS' if pooled_cov_ok else 'FAIL'}** ({fmt_pct(pooled_coverage)})",
        f"- Mean directional hit: **{fmt_pct(mean_hit)}** (need >=52.50%)",
        f"- Pooled horizons >=52% hit: **{hit_horizons_52}/5** (need >=4)",
        f"- Median pooled rho: **{fmt_num(median_rho)}** (need >=0.0400)",
        f"- Positive chronological folds: **{positive_folds}/5** (need >=4)",
        f"- No fold mean hit below 50%: **{'PASS' if no_fold_below_50 else 'FAIL'}**",
        f"- 2025 mean hit: **{fmt_pct(hit_2025)}** (need >=51.50%)",
        f"- 2026 mean hit: **{fmt_pct(hit_2026)}** (need >=51.50%)",
        f"- Mean sign lift vs A3: **{sign_lift_pp:+.2f}pp** (need >=+1.50pp)",
        f"- Median-rho lift vs A3: **{rho_lift:+.4f}** (need >=+0.0150)",
        f"- Aggregate behavioural gate: **{'PASS' if behavioural_ok else 'FAIL'}**",
        "", "## Decision", "", f"**{status}**", "",
        "Frozen stop rule applies to this A4 identity. No live orders were placed.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
