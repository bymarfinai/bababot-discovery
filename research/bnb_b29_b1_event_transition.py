#!/usr/bin/env python3
from __future__ import annotations

from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import bnb_b29_a1_structure_fingerprint as a1
import bnb_b29_a2_character_memory as a2
import bnb_b29_a2_character_memory_stable_runner as stable

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_B1_EVENT_TRANSITION"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_EVENTS = ROOT / f"{PFX}_Events.csv.gz"
OUT_FAMILY = ROOT / f"{PFX}_FamilyMetrics.csv"
OUT_FOLDS = ROOT / f"{PFX}_FoldMetrics.csv"
OUT_HORIZONS = ROOT / f"{PFX}_HorizonMetrics.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

SYMBOL = "BNBUSDT"
FROZEN_END = pd.Timestamp("2026-08-26T00:00:00Z")
FROZEN_A1_HASH = "2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6"
FOLDS = [2022, 2023, 2024, 2025, 2026]
HORIZONS = [15, 30, 60, 120, 360]
PRIMARY_H = 60
COOLDOWN = pd.Timedelta(minutes=60)

FAMILIES = {
    "SWEEP_LOW_RECLAIM": "LONG",
    "SWEEP_HIGH_REJECT": "SHORT",
    "BREAK_HIGH_HOLD": "LONG",
    "BREAK_LOW_HOLD": "SHORT",
    "BREAK_HIGH_FAIL": "SHORT",
    "BREAK_LOW_FAIL": "LONG",
    "COMPRESSION_EXPAND_UP": "LONG",
    "COMPRESSION_EXPAND_DOWN": "SHORT",
    "PULLBACK_UP_RESUME": "LONG",
    "PULLBACK_DOWN_RESUME": "SHORT",
}


def wilson_lcb(hits: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return np.nan
    p = hits / n
    den = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (center - margin) / den


def build_raw_event_masks(fp: pd.DataFrame) -> dict[str, pd.Series]:
    prev = fp.shift(1)
    masks = {}
    masks["SWEEP_LOW_RECLAIM"] = fp["sweep_low_60"].eq(1.0)
    masks["SWEEP_HIGH_REJECT"] = fp["sweep_high_60"].eq(1.0)
    masks["BREAK_HIGH_HOLD"] = prev["break_high_60"].eq(1.0) & fp["break_high_60"].eq(1.0)
    masks["BREAK_LOW_HOLD"] = prev["break_low_60"].eq(1.0) & fp["break_low_60"].eq(1.0)
    masks["BREAK_HIGH_FAIL"] = prev["break_high_60"].eq(1.0) & fp["break_high_60"].eq(0.0) & fp["close_location"].lt(0.0)
    masks["BREAK_LOW_FAIL"] = prev["break_low_60"].eq(1.0) & fp["break_low_60"].eq(0.0) & fp["close_location"].gt(0.0)
    masks["COMPRESSION_EXPAND_UP"] = prev["vol_state"].eq("COMPRESS") & fp["vol_state"].eq("EXPAND") & fp["disp_atr_15"].ge(0.25)
    masks["COMPRESSION_EXPAND_DOWN"] = prev["vol_state"].eq("COMPRESS") & fp["vol_state"].eq("EXPAND") & fp["disp_atr_15"].le(-0.25)
    masks["PULLBACK_UP_RESUME"] = prev["path_state"].eq("PULLBACK_FROM_UP") & fp["ret_15"].gt(0.0) & fp["trend_state"].isin(["UP", "STRONG_UP"])
    masks["PULLBACK_DOWN_RESUME"] = prev["path_state"].eq("PULLBACK_FROM_DOWN") & fp["ret_15"].lt(0.0) & fp["trend_state"].isin(["DOWN", "STRONG_DOWN"])
    return masks


def cooldown_select(index: pd.DatetimeIndex, mask: pd.Series) -> pd.DatetimeIndex:
    candidates = pd.DatetimeIndex(index[mask.to_numpy(bool)])
    accepted = []
    last = None
    for ts in candidates:
        if last is None or ts - last >= COOLDOWN:
            accepted.append(ts)
            last = ts
    return pd.DatetimeIndex(accepted)


def build_events(fp: pd.DataFrame, beh: pd.DataFrame) -> pd.DataFrame:
    masks = build_raw_event_masks(fp)
    rows = []
    outcome_cols = [f"fwd_{h}" for h in HORIZONS]
    valid_beh = beh[outcome_cols].notna().all(axis=1)
    for family, direction in FAMILIES.items():
        mask = masks[family] & valid_beh
        selected = cooldown_select(fp.index, mask)
        sign = 1.0 if direction == "LONG" else -1.0
        for ts in selected:
            row = {
                "event_ts": ts,
                "family": family,
                "direction": direction,
                "fold": int(ts.year),
                "structure_state": str(fp.at[ts, "structure_state"]),
                "trend_state": str(fp.at[ts, "trend_state"]),
                "vol_state": str(fp.at[ts, "vol_state"]),
                "path_state": str(fp.at[ts, "path_state"]),
            }
            for h in HORIZONS:
                r = float(beh.at[ts, f"fwd_{h}"])
                row[f"fwd_{h}"] = r
                row[f"signed_{h}"] = sign * r
                row[f"hit_{h}"] = bool(sign * r > 0.0)
            rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out[out["fold"].isin(FOLDS)].sort_values(["event_ts", "family"]).reset_index(drop=True)
    return out


def family_metrics(events: pd.DataFrame):
    family_rows = []
    fold_rows = []
    horizon_rows = []

    for family, direction in FAMILIES.items():
        g = events[events.family == family].copy()
        if len(g) == 0:
            family_rows.append({
                "family": family, "direction": direction, "n": 0,
                "primary_hit": np.nan, "primary_wilson_lcb": np.nan,
                "primary_median_signed_return": np.nan,
                "evaluable_folds": 0, "positive_folds": 0,
                "worst_fold_hit": np.nan, "hit_2025": np.nan, "hit_2026": np.nan,
                "aux_horizons_ge_52": 0, "max_fold_share": np.nan,
                "verdict": "REJECT",
            })
            continue

        fold_hits = {}
        fold_ns = {}
        for y in FOLDS:
            gy = g[g.fold == y]
            n = len(gy)
            fold_ns[y] = n
            hit = float(gy[f"hit_{PRIMARY_H}"].mean()) if n else np.nan
            fold_hits[y] = hit
            fold_rows.append({
                "family": family, "direction": direction, "fold": y, "n": n,
                "hit_60": hit,
                "median_signed_60": float(gy[f"signed_{PRIMARY_H}"].median()) if n else np.nan,
            })

        for h in HORIZONS:
            horizon_rows.append({
                "family": family, "direction": direction, "horizon_min": h,
                "n": len(g),
                "directional_hit": float(g[f"hit_{h}"].mean()),
                "median_signed_return": float(g[f"signed_{h}"].median()),
                "mean_signed_return": float(g[f"signed_{h}"].mean()),
            })

        n = len(g)
        hits = int(g[f"hit_{PRIMARY_H}"].sum())
        primary_hit = hits / n
        lcb = wilson_lcb(hits, n)
        evaluable = [y for y in FOLDS if fold_ns[y] > 0]
        per_fold_min_ok = all(fold_ns[y] >= 15 for y in evaluable)
        positive_folds = sum(1 for y in evaluable if fold_hits[y] > 0.50)
        worst_fold = min((fold_hits[y] for y in evaluable), default=np.nan)
        hit25 = fold_hits.get(2025, np.nan)
        hit26 = fold_hits.get(2026, np.nan)
        aux = [h for h in HORIZONS if h != PRIMARY_H]
        aux_ge = sum(1 for h in aux if float(g[f"hit_{h}"].mean()) >= 0.52)
        max_share = max((fold_ns[y] / n for y in evaluable), default=np.nan)
        median_signed = float(g[f"signed_{PRIMARY_H}"].median())

        passed = all([
            n >= 120,
            len(evaluable) >= 4,
            per_fold_min_ok,
            primary_hit >= 0.55,
            lcb > 0.50,
            median_signed > 0.0,
            positive_folds >= 4,
            np.isfinite(worst_fold) and worst_fold >= 0.475,
            np.isfinite(hit25) and hit25 >= 0.52,
            np.isfinite(hit26) and hit26 >= 0.52,
            aux_ge >= 3,
            np.isfinite(max_share) and max_share <= 0.45,
        ])
        family_rows.append({
            "family": family, "direction": direction, "n": n,
            "primary_hit": primary_hit, "primary_wilson_lcb": lcb,
            "primary_median_signed_return": median_signed,
            "evaluable_folds": len(evaluable), "per_fold_min_ok": per_fold_min_ok,
            "positive_folds": positive_folds, "worst_fold_hit": worst_fold,
            "hit_2025": hit25, "hit_2026": hit26,
            "aux_horizons_ge_52": aux_ge, "max_fold_share": max_share,
            "verdict": "PROMOTE_TO_B2" if passed else "REJECT",
        })

    F = pd.DataFrame(family_rows)
    folds = pd.DataFrame(fold_rows)
    horizons = pd.DataFrame(horizon_rows)

    promoted = F[F.verdict == "PROMOTE_TO_B2"].copy()
    if len(promoted) > 3:
        promoted = promoted.sort_values(
            ["primary_wilson_lcb", "primary_hit", "n", "family"],
            ascending=[False, False, False, True],
        ).head(3)
        keep = set(promoted.family)
        F.loc[(F.verdict == "PROMOTE_TO_B2") & (~F.family.isin(keep)), "verdict"] = "PASS_NOT_TOP3"

    return F, folds, horizons


def fmt_pct(v):
    return "nan" if pd.isna(v) else f"{100.0 * float(v):.2f}%"


def fmt_num(v, n=4):
    return "nan" if pd.isna(v) else f"{float(v):.{n}f}"


def main():
    base.synthetic_tests()
    raw, coverage = stable.load5_frozen_identity(SYMBOL)
    fp = a1.build_fingerprint(raw)
    fp_hash = a1.fingerprint_hash(fp)
    beh = a2.build_behaviour(raw, fp.index)

    a1_ok = fp_hash == FROZEN_A1_HASH
    boundary_ok = bool(pd.DatetimeIndex(raw.index).max() < FROZEN_END and fp.index.max() <= FROZEN_END)
    grid_ok = bool(((fp.index.minute % 15) == 0).all())
    finite_ok = bool(np.isfinite(fp[a1.NUMERIC_FEATURES].to_numpy(float)).all())
    events = build_events(fp, beh)
    event_finite_ok = bool(len(events) > 0 and np.isfinite(events[[f"fwd_{h}" for h in HORIZONS]].to_numpy(float)).all())
    family_known_ok = bool(set(events.family.unique()).issubset(FAMILIES)) if len(events) else False
    integrity_ok = bool(coverage >= 0.995 and a1_ok and boundary_ok and grid_ok and finite_ok and event_finite_ok and family_known_ok)

    F, folds, horizons = family_metrics(events)
    promoted = F[F.verdict == "PROMOTE_TO_B2"].copy()
    if not integrity_ok:
        status = "BNB_B29_B1_DATA_TOOLING_FAILURE"
    elif len(promoted) >= 1:
        status = "BNB_B29_B1_EVENT_TRANSITION_PASS"
    else:
        status = "BNB_B29_B1_EVENT_TRANSITION_REJECT"

    events.to_csv(OUT_EVENTS, index=False, compression="gzip")
    F.to_csv(OUT_FAMILY, index=False)
    folds.to_csv(OUT_FOLDS, index=False)
    horizons.to_csv(OUT_HORIZONS, index=False)
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B29 B1 — Event-Conditioned Structural Transition Result", "",
        f"**Status: {status}**", "",
        "B1 tests fixed causal structural event sequences and forward direction only. No entry, TP, SL, leverage, fees, PnL or live orders are tested.", "",
        "## Integrity", "",
        f"- A1 fingerprint hash: `{fp_hash}`",
        f"- Exact A1 hash: **{'PASS' if a1_ok else 'FAIL'}**",
        f"- Raw 5m coverage: {coverage:.6%}",
        f"- Frozen boundary: **{'PASS' if boundary_ok else 'FAIL'}**",
        f"- 15m decision grid: **{'PASS' if grid_ok else 'FAIL'}**",
        f"- Numeric/event integrity: **{'PASS' if finite_ok and event_finite_ok and family_known_ok else 'FAIL'}**",
        f"- Total de-duplicated events (2022-2026 folds): {len(events):,}", "",
        "## Frozen family gate results", "",
        "| Family | Dir | N | +60m hit | Wilson LCB | Median signed +60m | Folds + | Worst fold | 2025 | 2026 | Aux >=52% | Max era share | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in F.sort_values(["verdict", "primary_wilson_lcb", "family"], ascending=[True, False, True]).iterrows():
        lines.append(
            f"| {r.family} | {r.direction} | {int(r.n)} | {fmt_pct(r.primary_hit)} | {fmt_pct(r.primary_wilson_lcb)} | "
            f"{fmt_pct(r.primary_median_signed_return)} | {int(r.positive_folds)} | {fmt_pct(r.worst_fold_hit)} | "
            f"{fmt_pct(r.hit_2025)} | {fmt_pct(r.hit_2026)} | {int(r.aux_horizons_ge_52)} | {fmt_pct(r.max_fold_share)} | {r.verdict} |"
        )

    lines.extend(["", "## Primary +60m fold detail", "", "| Family | Fold | N | Hit | Median signed return |", "|---|---:|---:|---:|---:|"])
    for _, r in folds.iterrows():
        lines.append(f"| {r.family} | {int(r.fold)} | {int(r.n)} | {fmt_pct(r.hit_60)} | {fmt_pct(r.median_signed_60)} |")

    lines.extend(["", "## Decision", "", f"**{status}**", ""])
    if len(promoted):
        names = ", ".join(promoted.family.tolist())
        lines.append(f"Frozen promoted family/families for B2: **{names}**.")
    else:
        lines.append("No fixed event family satisfies the preregistered promotion gate. Do not proceed to execution discovery from this B1 identity.")
    lines.extend(["", "No live orders were placed.", ""])
    OUT_RESULT.write_text("\n".join(lines))
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
