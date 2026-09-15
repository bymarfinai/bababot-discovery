#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_B1_EVENT_TRANSITION"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_EVENTS = ROOT / f"{PFX}_Events.csv.gz"
OUT_FAMILY = ROOT / f"{PFX}_FamilyMetrics.csv"
OUT_FOLDS = ROOT / f"{PFX}_FoldMetrics.csv"
OUT_HORIZONS = ROOT / f"{PFX}_HorizonMetrics.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

FROZEN_FP = ROOT / "frozen_a1" / "BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz"
FROZEN_FP_SHA256 = "eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa"
FROZEN_ROWS = 229_267
FROZEN_FIRST = pd.Timestamp("2020-02-10T14:15:00Z")
FROZEN_LAST = pd.Timestamp("2026-08-26T00:00:00Z")
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

REQUIRED_COLUMNS = [
    "ret_15", "disp_atr_15", "close_location", "sweep_high_60", "sweep_low_60",
    "break_high_60", "break_low_60", "structure_state", "trend_state",
    "vol_state", "path_state",
]


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_a1() -> tuple[pd.DataFrame, dict]:
    if not FROZEN_FP.exists():
        raise FileNotFoundError(f"missing accepted A1 artifact fingerprint: {FROZEN_FP}")
    digest = file_sha256(FROZEN_FP)
    q = pd.read_csv(FROZEN_FP, compression="gzip")
    if "decision_ts" not in q.columns:
        raise RuntimeError("accepted A1 fingerprint missing decision_ts")
    q["decision_ts"] = pd.to_datetime(q["decision_ts"], utc=True, errors="raise")
    q = q.set_index("decision_ts")
    q.index = pd.DatetimeIndex(q.index)
    diag = {
        "sha256": digest,
        "sha_ok": digest == FROZEN_FP_SHA256,
        "rows": len(q),
        "rows_ok": len(q) == FROZEN_ROWS,
        "first": q.index.min() if len(q) else pd.NaT,
        "last": q.index.max() if len(q) else pd.NaT,
        "boundary_ok": bool(len(q) and q.index.min() == FROZEN_FIRST and q.index.max() == FROZEN_LAST),
        "grid_ok": bool(len(q) > 1 and (q.index.to_series().diff().dropna() == pd.Timedelta(minutes=15)).all()),
        "unique_ok": bool(not q.index.has_duplicates and q.index.is_monotonic_increasing),
        "schema_ok": all(c in q.columns for c in REQUIRED_COLUMNS),
    }
    print("B1 frozen A1 artifact diagnostic:", diag, flush=True)
    if not all([diag["sha_ok"], diag["rows_ok"], diag["boundary_ok"], diag["grid_ok"], diag["unique_ok"], diag["schema_ok"]]):
        raise RuntimeError(f"accepted A1 artifact identity failure: {diag}")
    return q, diag


def build_behaviour_from_frozen_a1(fp: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct forward close-to-close returns exactly from frozen A1 15m returns.

    A1 ret_15 at timestamp t equals C_t/C_{t-15m}-1. Therefore a +H return from
    decision t is the compounded sequence of the next H/15 frozen ret_15 values.
    This avoids any re-download or mutable external market-data dependency.
    """
    r = pd.to_numeric(fp["ret_15"], errors="coerce").astype(float)
    out = pd.DataFrame(index=fp.index)
    for h in HORIZONS:
        steps = h // 15
        growth = pd.Series(1.0, index=fp.index, dtype=float)
        for i in range(1, steps + 1):
            growth = growth * (1.0 + r.shift(-i))
        out[f"fwd_{h}"] = growth - 1.0
    return out


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
    return {
        "SWEEP_LOW_RECLAIM": fp["sweep_low_60"].eq(1.0),
        "SWEEP_HIGH_REJECT": fp["sweep_high_60"].eq(1.0),
        "BREAK_HIGH_HOLD": prev["break_high_60"].eq(1.0) & fp["break_high_60"].eq(1.0),
        "BREAK_LOW_HOLD": prev["break_low_60"].eq(1.0) & fp["break_low_60"].eq(1.0),
        "BREAK_HIGH_FAIL": prev["break_high_60"].eq(1.0) & fp["break_high_60"].eq(0.0) & fp["close_location"].lt(0.0),
        "BREAK_LOW_FAIL": prev["break_low_60"].eq(1.0) & fp["break_low_60"].eq(0.0) & fp["close_location"].gt(0.0),
        "COMPRESSION_EXPAND_UP": prev["vol_state"].eq("COMPRESS") & fp["vol_state"].eq("EXPAND") & fp["disp_atr_15"].ge(0.25),
        "COMPRESSION_EXPAND_DOWN": prev["vol_state"].eq("COMPRESS") & fp["vol_state"].eq("EXPAND") & fp["disp_atr_15"].le(-0.25),
        "PULLBACK_UP_RESUME": prev["path_state"].eq("PULLBACK_FROM_UP") & fp["ret_15"].gt(0.0) & fp["trend_state"].isin(["UP", "STRONG_UP"]),
        "PULLBACK_DOWN_RESUME": prev["path_state"].eq("PULLBACK_FROM_DOWN") & fp["ret_15"].lt(0.0) & fp["trend_state"].isin(["DOWN", "STRONG_DOWN"]),
    }


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
        selected = cooldown_select(fp.index, masks[family] & valid_beh)
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
    family_rows, fold_rows, horizon_rows = [], [], []
    for family, direction in FAMILIES.items():
        g = events[events.family == family].copy()
        if len(g) == 0:
            family_rows.append({
                "family": family, "direction": direction, "n": 0,
                "primary_hit": np.nan, "primary_wilson_lcb": np.nan,
                "primary_median_signed_return": np.nan,
                "evaluable_folds": 0, "per_fold_min_ok": False, "positive_folds": 0,
                "worst_fold_hit": np.nan, "hit_2025": np.nan, "hit_2026": np.nan,
                "aux_horizons_ge_52": 0, "max_fold_share": np.nan, "verdict": "REJECT",
            })
            continue

        fold_hits, fold_ns = {}, {}
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
                "n": len(g), "directional_hit": float(g[f"hit_{h}"].mean()),
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
        hit25, hit26 = fold_hits.get(2025, np.nan), fold_hits.get(2026, np.nan)
        aux_ge = sum(1 for h in HORIZONS if h != PRIMARY_H and float(g[f"hit_{h}"].mean()) >= 0.52)
        max_share = max((fold_ns[y] / n for y in evaluable), default=np.nan)
        median_signed = float(g[f"signed_{PRIMARY_H}"].median())

        passed = all([
            n >= 120, len(evaluable) >= 4, per_fold_min_ok,
            primary_hit >= 0.55, lcb > 0.50, median_signed > 0.0,
            positive_folds >= 4, np.isfinite(worst_fold) and worst_fold >= 0.475,
            np.isfinite(hit25) and hit25 >= 0.52,
            np.isfinite(hit26) and hit26 >= 0.52,
            aux_ge >= 3, np.isfinite(max_share) and max_share <= 0.45,
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


def main():
    fp, diag = load_frozen_a1()
    for c in ["ret_15", "disp_atr_15", "close_location", "sweep_high_60", "sweep_low_60", "break_high_60", "break_low_60"]:
        fp[c] = pd.to_numeric(fp[c], errors="coerce")
    numeric_ok = bool(np.isfinite(fp[["ret_15", "disp_atr_15", "close_location", "sweep_high_60", "sweep_low_60", "break_high_60", "break_low_60"]].to_numpy(float)).all())
    beh = build_behaviour_from_frozen_a1(fp)
    events = build_events(fp, beh)
    event_finite_ok = bool(len(events) > 0 and np.isfinite(events[[f"fwd_{h}" for h in HORIZONS]].to_numpy(float)).all())
    family_known_ok = bool(len(events) > 0 and set(events.family.unique()).issubset(FAMILIES))
    integrity_ok = bool(all([diag["sha_ok"], diag["rows_ok"], diag["boundary_ok"], diag["grid_ok"], diag["unique_ok"], diag["schema_ok"], numeric_ok, event_finite_ok, family_known_ok]))

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
        "## Frozen A1 artifact integrity", "",
        f"- Accepted A1 artifact id: `10336102957`",
        f"- Fingerprint file SHA256: `{diag['sha256']}`",
        f"- Exact frozen file hash: **{'PASS' if diag['sha_ok'] else 'FAIL'}**",
        f"- Rows: {len(fp):,} / expected {FROZEN_ROWS:,}",
        f"- Boundary/grid/schema: **{'PASS' if diag['boundary_ok'] and diag['grid_ok'] and diag['schema_ok'] else 'FAIL'}**",
        f"- Forward outcomes reconstructed only from frozen A1 ret_15: **YES**",
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
        lines.append(f"Frozen promoted family/families for B2: **{', '.join(promoted.family.tolist())}**.")
    else:
        lines.append("No fixed event family satisfies the preregistered promotion gate. Do not proceed to execution discovery from this B1 identity.")
    lines.extend(["", "No live orders were placed.", ""])
    OUT_RESULT.write_text("\n".join(lines))
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
