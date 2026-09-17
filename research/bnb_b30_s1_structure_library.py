#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B30_S1_STRUCTURE_LIBRARY"
FP = ROOT / "frozen_a1" / "BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz"
FP_SHA256 = "eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa"
FP_ROWS = 229_267
FP_FIRST = pd.Timestamp("2020-02-10T14:15:00Z")
FP_LAST = pd.Timestamp("2026-08-26T00:00:00Z")
STEP = pd.Timedelta(minutes=15)
COOLDOWN = pd.Timedelta(minutes=60)
YEARS = [2022, 2023, 2024, 2025, 2026]
START = pd.Timestamp("2022-01-01T00:00:00Z")
END = FP_LAST

DETECTORS = [
    ("S01", "SWEEP_LOW_RECLAIM", "LONG"),
    ("S02", "HL_CONTINUATION", "LONG"),
    ("S03", "BREAK_HIGH_HOLD", "LONG"),
    ("S04", "FAILED_BREAKDOWN_RECLAIM", "LONG"),
    ("S05", "SWEEP_HIGH_REJECT", "SHORT"),
    ("S06", "LH_CONTINUATION", "SHORT"),
    ("S07", "BREAK_LOW_HOLD", "SHORT"),
    ("S08", "FAILED_BREAKOUT_REJECT", "SHORT"),
]


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fp() -> tuple[pd.DataFrame, dict]:
    if not FP.exists():
        raise FileNotFoundError(FP)
    file_hash = digest(FP)
    x = pd.read_csv(FP, compression="gzip", low_memory=False)
    x["decision_ts"] = pd.to_datetime(x["decision_ts"], utc=True, errors="raise")
    x = x.set_index("decision_ts").sort_index()
    req = [
        "sweep_low_60", "sweep_high_60", "break_low_60", "break_high_60",
        "close_location", "path_state", "structure_state",
    ]
    for c in ["sweep_low_60", "sweep_high_60", "break_low_60", "break_high_60", "close_location"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    diag = {
        "sha256": file_hash,
        "sha_ok": file_hash == FP_SHA256,
        "rows": len(x),
        "rows_ok": len(x) == FP_ROWS,
        "first": x.index.min(),
        "last": x.index.max(),
        "bounds_ok": x.index.min() == FP_FIRST and x.index.max() == FP_LAST,
        "unique_monotonic": bool(x.index.is_monotonic_increasing and not x.index.has_duplicates),
        "quarter_grid": bool(((x.index.minute % 15) == 0).all()),
        "schema_ok": all(c in x.columns for c in req),
    }
    if not all([diag["sha_ok"], diag["rows_ok"], diag["bounds_ok"], diag["unique_monotonic"], diag["quarter_grid"], diag["schema_ok"]]):
        raise RuntimeError(f"immutable A1 integrity failure: {diag}")
    return x, diag


def predecessor_frame(x: pd.DataFrame) -> pd.DataFrame:
    pre = x.reindex(x.index - STEP).copy()
    pre.index = x.index
    return pre


def raw_masks(x: pd.DataFrame) -> dict[str, pd.Series]:
    pre = predecessor_frame(x)
    exact_pre = pre.index.to_series().map(lambda ts: ts - STEP).isin(x.index).to_numpy()
    exact_pre = pd.Series(exact_pre, index=x.index)

    masks: dict[str, pd.Series] = {}
    masks["S01"] = x["sweep_low_60"].eq(1.0)
    masks["S02"] = (
        exact_pre
        & pre["path_state"].eq("PULLBACK_FROM_UP")
        & x["path_state"].eq("CONT_UP")
        & x["structure_state"].eq("HH_HL")
    )
    masks["S03"] = exact_pre & pre["break_high_60"].eq(1.0) & x["break_high_60"].eq(1.0)
    masks["S04"] = (
        exact_pre
        & pre["break_low_60"].eq(1.0)
        & x["break_low_60"].eq(0.0)
        & x["close_location"].gt(0.0)
    )
    masks["S05"] = x["sweep_high_60"].eq(1.0)
    masks["S06"] = (
        exact_pre
        & pre["path_state"].eq("PULLBACK_FROM_DOWN")
        & x["path_state"].eq("CONT_DOWN")
        & x["structure_state"].eq("LH_LL")
    )
    masks["S07"] = exact_pre & pre["break_low_60"].eq(1.0) & x["break_low_60"].eq(1.0)
    masks["S08"] = (
        exact_pre
        & pre["break_high_60"].eq(1.0)
        & x["break_high_60"].eq(0.0)
        & x["close_location"].lt(0.0)
    )
    return masks


def cooldown(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    accepted: list[pd.Timestamp] = []
    last: pd.Timestamp | None = None
    for ts in index.sort_values():
        if last is None or ts - last >= COOLDOWN:
            accepted.append(ts)
            last = ts
    return pd.DatetimeIndex(accepted)


def build_events(x: pd.DataFrame) -> pd.DataFrame:
    census = x[(x.index >= START) & (x.index <= END)].copy()
    masks = raw_masks(x)
    rows = []
    name_by_id = {i: (n, d) for i, n, d in DETECTORS}
    for sid, _, _ in DETECTORS:
        idx = pd.DatetimeIndex(x.index[masks[sid]])
        idx = idx[(idx >= START) & (idx <= END)]
        idx = cooldown(idx)
        name, direction = name_by_id[sid]
        for ts in idx:
            rows.append({"event_ts": ts, "structure_id": sid, "structure": name, "direction": direction, "year": ts.year})
    e = pd.DataFrame(rows)
    if len(e):
        e = e.sort_values(["event_ts", "structure_id"]).reset_index(drop=True)
    return e


def summarize(events: pd.DataFrame) -> pd.DataFrame:
    observed_days = (END - START) / pd.Timedelta(days=1)
    rows = []
    for sid, name, direction in DETECTORS:
        z = events[events["structure_id"] == sid].sort_values("event_ts")
        n = len(z)
        counts = {y: int((z["year"] == y).sum()) for y in YEARS}
        gaps_h = z["event_ts"].diff().dropna() / pd.Timedelta(hours=1)
        evaluable = sum(counts[y] >= 15 for y in YEARS)
        max_share = max(counts.values()) / n if n else np.nan
        median_gap = float(gaps_h.median()) if len(gaps_h) else np.nan
        p10_gap = float(gaps_h.quantile(0.10)) if len(gaps_h) else np.nan
        viable = (
            n >= 120
            and evaluable >= 4
            and max_share <= 0.35
            and (np.isnan(median_gap) or median_gap >= 1.0)
        )
        rows.append({
            "structure_id": sid,
            "structure": name,
            "direction": direction,
            "n": n,
            **{f"n_{y}": counts[y] for y in YEARS},
            "detections_per_365d": n / observed_days * 365.0,
            "median_gap_hours": median_gap,
            "p10_gap_hours": p10_gap,
            "eras_ge15": evaluable,
            "max_era_share": max_share,
            "status": "STRUCTURALLY_VIABLE" if viable else "INSUFFICIENT_STRUCTURE_SAMPLE",
        })
    return pd.DataFrame(rows)


def overlaps(events: pd.DataFrame) -> pd.DataFrame:
    sets = {sid: set(events.loc[events.structure_id == sid, "event_ts"]) for sid, _, _ in DETECTORS}
    rows = []
    for sid_a, name_a, _ in DETECTORS:
        for sid_b, name_b, _ in DETECTORS:
            a, b = sets[sid_a], sets[sid_b]
            inter = len(a & b)
            union = len(a | b)
            rows.append({
                "structure_id_a": sid_a,
                "structure_a": name_a,
                "structure_id_b": sid_b,
                "structure_b": name_b,
                "same_timestamp_overlap": inter,
                "jaccard": inter / union if union else np.nan,
            })
    return pd.DataFrame(rows)


def render(summary: pd.DataFrame, overlap: pd.DataFrame, diag: dict) -> str:
    viable = summary[summary.status == "STRUCTURALLY_VIABLE"]
    status = "BNB_B30_S1_STRUCTURE_LIBRARY_READY" if len(viable) else "BNB_B30_S1_NO_VIABLE_STRUCTURE"
    lines = [
        "# BNB B30-S1 — Pure Structure Detector Library Result",
        "",
        f"**Status: {status}**",
        "",
        "S1 is a structural census only. No entry, future WIN/LOSS, return, MFE/MAE, TP/SL or PnL is evaluated here.",
        "",
        "## Immutable source integrity",
        f"- SHA256: `{diag['sha256']}` — {'PASS' if diag['sha_ok'] else 'FAIL'}",
        f"- Rows: **{diag['rows']:,}**",
        f"- Bounds: **{diag['first']} → {diag['last']}**",
        "- Exact predecessor clauses never cross missing 15m timestamps.",
        "",
        "## Structure census",
        "| ID | Structure | Side | N | 2022 | 2023 | 2024 | 2025 | 2026* | /year | Median gap | Eras >=15 | Max era | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in summary.iterrows():
        lines.append(
            f"| {r.structure_id} | {r.structure} | {r.direction} | {int(r.n)} | {int(r.n_2022)} | {int(r.n_2023)} | {int(r.n_2024)} | {int(r.n_2025)} | {int(r.n_2026)} | {r.detections_per_365d:.1f} | {r.median_gap_hours:.1f}h | {int(r.eras_ge15)} | {r.max_era_share:.1%} | {r.status} |"
        )
    lines += [
        "",
        "`2026*` ends at the immutable A1 cutoff 2026-08-26.",
        "",
        "## Cross-family same-timestamp overlap",
        "Only non-zero off-diagonal overlaps are listed; overlap is descriptive and does not suppress either detector.",
        "",
    ]
    nz = overlap[(overlap.structure_id_a < overlap.structure_id_b) & (overlap.same_timestamp_overlap > 0)].copy()
    if len(nz):
        lines += ["| A | B | Same timestamp | Jaccard |", "|---|---|---:|---:|"]
        for _, r in nz.sort_values("same_timestamp_overlap", ascending=False).iterrows():
            lines.append(f"| {r.structure_id_a} {r.structure_a} | {r.structure_id_b} {r.structure_b} | {int(r.same_timestamp_overlap)} | {r.jaccard:.2%} |")
    else:
        lines.append("No off-diagonal same-timestamp overlaps.")
    lines += [
        "",
        "## Decision",
        f"**{status}**",
        "",
        f"Structurally viable detectors: **{len(viable)}/{len(summary)}**.",
        "Every viable detector advances independently to B30-S2 entry discovery. S2 may search structure-specific entry mechanisms but may not change these S1 definitions. Economics remains forbidden until an entry mechanism is frozen.",
        "",
        "No live orders were placed.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    x, diag = load_fp()
    events = build_events(x)
    summary = summarize(events)
    overlap = overlaps(events)

    # Hard schema guard: S1 artifacts may not contain outcome/execution vocabulary.
    forbidden = ("entry", "win", "loss", "future", "return", "mfe", "mae", "tp", "sl", "pnl", "profit", "expect")
    cols = [str(c).lower() for c in events.columns] + [str(c).lower() for c in summary.columns] + [str(c).lower() for c in overlap.columns]
    bad = [c for c in cols if any(tok in c for tok in forbidden)]
    if bad:
        raise RuntimeError(f"S1 forbidden output column(s): {bad}")

    events.to_csv(ROOT / f"{PFX}_Events.csv.gz", index=False, compression="gzip")
    summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    overlap.to_csv(ROOT / f"{PFX}_Overlap.csv", index=False)
    result = render(summary, overlap, diag)
    (ROOT / f"{PFX}_Result.md").write_text(result, encoding="utf-8")
    status = "BNB_B30_S1_STRUCTURE_LIBRARY_READY" if (summary.status == "STRUCTURALLY_VIABLE").any() else "BNB_B30_S1_NO_VIABLE_STRUCTURE"
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n", encoding="utf-8")
    print(result, flush=True)


if __name__ == "__main__":
    main()
