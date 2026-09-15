#!/usr/bin/env python3
from __future__ import annotations

from hashlib import sha256
from itertools import combinations, product
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B29_B1J_JOURNEY_SWEEP_CHARACTER"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_RULES = ROOT / f"{PFX}_AllRules.csv.gz"
OUT_DEV = ROOT / f"{PFX}_DevelopmentEligible.csv"
OUT_SEL = ROOT / f"{PFX}_SelectedCandidates.csv"
OUT_REF = ROOT / f"{PFX}_ReferenceValidation.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"
OUT_EVENTS = ROOT / f"{PFX}_Events.csv.gz"

FROZEN_FP = ROOT / "frozen_a1" / "BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz"
FROZEN_FP_SHA256 = "eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa"
FROZEN_ROWS = 229_267
FROZEN_FIRST = pd.Timestamp("2020-02-10T14:15:00Z")
FROZEN_LAST = pd.Timestamp("2026-08-26T00:00:00Z")
STEP = pd.Timedelta(minutes=15)
COOLDOWN = pd.Timedelta(minutes=60)
HORIZONS = [15, 30, 60, 120, 360]
DEV_YEARS = [2022, 2023, 2024]
REF_YEARS = [2025, 2026]
ALL_YEARS = DEV_YEARS + REF_YEARS

AXIS_VALUES = {
    "pre_path_state": ["PULLBACK_FROM_UP", "CONT_UP", "UP_PAUSE", "PULLBACK_FROM_DOWN", "CONT_DOWN", "DOWN_PAUSE", "MIXED_RANGE"],
    "pre_structure_state": ["HH_HL", "LH_LL", "HH_LL", "LH_HL", "OVERLAP"],
    "pre_trend_state": ["STRONG_DOWN", "DOWN", "FLAT", "UP", "STRONG_UP"],
    "pre_vol_state": ["COMPRESS", "NORMAL", "EXPAND"],
    "pre_efficiency_state": ["LOW", "MID", "HIGH"],
    "pre_range_state": ["LOW", "MID", "HIGH"],
    "approach_momentum": ["DOWN", "FLAT", "UP"],
    "low_journey": ["BREAK_BEFORE", "REPEAT_SWEEP", "CLEAN_APPROACH"],
    "reclaim_strength": ["LOW", "MID", "HIGH"],
    "reclaim_body": ["LOW", "MID", "HIGH"],
    "reclaim_range": ["QUIET", "NORMAL", "EXPANDED"],
}
AXES = list(AXIS_VALUES)


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson_lcb(hits: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return np.nan
    p = hits / n
    den = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (center - margin) / den


def load_frozen_a1() -> tuple[pd.DataFrame, dict]:
    if not FROZEN_FP.exists():
        raise FileNotFoundError(f"missing accepted A1 fingerprint: {FROZEN_FP}")
    digest = file_sha256(FROZEN_FP)
    q = pd.read_csv(FROZEN_FP, compression="gzip", low_memory=False)
    q["decision_ts"] = pd.to_datetime(q["decision_ts"], utc=True, errors="raise")
    q = q.set_index("decision_ts").sort_index()
    required = [
        "ret_15", "disp_atr_60", "close_location", "body_range", "true_range", "atr_360",
        "sweep_low_60", "break_low_60", "path_state", "structure_state", "trend_state",
        "vol_state", "efficiency_state", "range_state",
    ]
    for c in ["ret_15", "disp_atr_60", "close_location", "body_range", "true_range", "atr_360", "sweep_low_60", "break_low_60"]:
        q[c] = pd.to_numeric(q[c], errors="coerce")
    delta = q.index.to_series().diff().dropna()
    diag = {
        "sha256": digest,
        "sha_ok": digest == FROZEN_FP_SHA256,
        "rows": len(q),
        "rows_ok": len(q) == FROZEN_ROWS,
        "first": q.index.min(),
        "last": q.index.max(),
        "boundary_ok": q.index.min() == FROZEN_FIRST and q.index.max() == FROZEN_LAST,
        "quarter_grid_ok": bool(((q.index.minute % 15) == 0).all()),
        "unique_ok": bool(q.index.is_monotonic_increasing and not q.index.has_duplicates),
        "schema_ok": all(c in q.columns for c in required),
        "gap_count": int((delta != STEP).sum()),
    }
    print("B1J immutable A1 diagnostic:", diag, flush=True)
    if not all([diag["sha_ok"], diag["rows_ok"], diag["boundary_ok"], diag["quarter_grid_ok"], diag["unique_ok"], diag["schema_ok"]]):
        raise RuntimeError(f"immutable A1 identity failure: {diag}")
    return q, diag


def build_forward(fp: pd.DataFrame) -> pd.DataFrame:
    r = fp["ret_15"].astype(float)
    out = pd.DataFrame(index=fp.index)
    for h in HORIZONS:
        steps = h // 15
        growth = pd.Series(1.0, index=fp.index, dtype=float)
        valid = pd.Series(True, index=fp.index, dtype=bool)
        for i in range(1, steps + 1):
            rr = r.reindex(fp.index + i * STEP)
            rr.index = fp.index
            valid &= rr.notna()
            growth *= 1.0 + rr.fillna(0.0)
        out[f"fwd_{h}"] = (growth - 1.0).where(valid)
    return out


def cooldown_select(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    accepted = []
    last = None
    for ts in index:
        if last is None or ts - last >= COOLDOWN:
            accepted.append(ts)
            last = ts
    return pd.DatetimeIndex(accepted)


def build_events(fp: pd.DataFrame, beh: pd.DataFrame) -> pd.DataFrame:
    valid_beh = beh[[f"fwd_{h}" for h in HORIZONS]].notna().all(axis=1)
    raw_mask = fp["sweep_low_60"].eq(1.0) & valid_beh
    base_idx = cooldown_select(pd.DatetimeIndex(fp.index[raw_mask]))
    E = pd.DataFrame(index=base_idx)
    E.index.name = "event_ts"
    E["year"] = E.index.year

    pre = fp.reindex(base_idx - STEP)
    pre.index = base_idx
    mapping = {
        "path_state": "pre_path_state",
        "structure_state": "pre_structure_state",
        "trend_state": "pre_trend_state",
        "vol_state": "pre_vol_state",
        "efficiency_state": "pre_efficiency_state",
        "range_state": "pre_range_state",
    }
    for src, dst in mapping.items():
        E[dst] = pre[src].astype("object")

    d = pre["disp_atr_60"].astype(float)
    E["approach_momentum"] = np.where(d <= -0.35, "DOWN", np.where(d >= 0.35, "UP", "FLAT"))

    prior = []
    for i in range(1, 5):
        z = fp.reindex(base_idx - i * STEP)[["sweep_low_60", "break_low_60"]]
        z.index = base_idx
        prior.append(z)
    path_complete = np.logical_and.reduce([z["sweep_low_60"].notna().to_numpy() for z in prior])
    break_prev = prior[0]["break_low_60"].eq(1.0).to_numpy()
    repeat_sweep = np.logical_or.reduce([z["sweep_low_60"].eq(1.0).to_numpy() for z in prior])
    E["low_journey"] = np.where(break_prev, "BREAK_BEFORE", np.where(repeat_sweep, "REPEAT_SWEEP", "CLEAN_APPROACH"))
    E["path_complete"] = path_complete

    cur = fp.loc[base_idx]
    cl = cur["close_location"].astype(float)
    E["reclaim_strength"] = np.where(cl <= 0.0, "LOW", np.where(cl < 0.50, "MID", "HIGH"))
    br = cur["body_range"].astype(float)
    E["reclaim_body"] = np.where(br < 0.33, "LOW", np.where(br < 0.66, "MID", "HIGH"))
    rr = cur["true_range"].astype(float) / cur["atr_360"].astype(float)
    E["reclaim_range"] = np.where(rr < 0.80, "QUIET", np.where(rr <= 1.50, "NORMAL", "EXPANDED"))

    for h in HORIZONS:
        E[f"fwd_{h}"] = beh.loc[base_idx, f"fwd_{h}"].to_numpy(float)
        E[f"hit_{h}"] = E[f"fwd_{h}"] > 0.0

    E = E[E["path_complete"] & E["year"].isin(ALL_YEARS)].copy()
    E = E[E[list(AXIS_VALUES)].notna().all(axis=1)].copy()
    return E.sort_index()


def rule_text(axes: tuple[str, ...], vals: tuple[str, ...]) -> str:
    return " AND ".join(f"{a}=={v}" for a, v in zip(axes, vals))


def rule_mask(df: pd.DataFrame, axes: tuple[str, ...], vals: tuple[str, ...]) -> np.ndarray:
    mask = np.ones(len(df), dtype=bool)
    for a, v in zip(axes, vals):
        mask &= df[a].astype(str).to_numpy() == v
    return mask


def bh_adjust(pvals: np.ndarray) -> np.ndarray:
    m = len(pvals)
    if m == 0:
        return np.array([], dtype=float)
    order = np.argsort(pvals)
    ps = pvals[order]
    adjusted_sorted = np.minimum.accumulate((ps * m / np.arange(1, m + 1))[::-1])[::-1]
    adjusted = np.empty(m, dtype=float)
    adjusted[order] = np.minimum(adjusted_sorted, 1.0)
    return adjusted


def enumerate_dev_rules(events: pd.DataFrame) -> pd.DataFrame:
    dev = events[events["year"].isin(DEV_YEARS)].copy()
    masks = {(a, v): (dev[a].astype(str).to_numpy() == v) for a, vals in AXIS_VALUES.items() for v in vals}
    ym = {y: (dev["year"].to_numpy() == y) for y in DEV_YEARS}
    rows = []
    grammar_count = 0

    for k in (1, 2, 3):
        for ac in combinations(AXES, k):
            for vals in product(*(AXIS_VALUES[a] for a in ac)):
                grammar_count += 1
                mask = np.ones(len(dev), dtype=bool)
                for a, v in zip(ac, vals):
                    mask &= masks[(a, v)]
                n = int(mask.sum())
                ns = {y: int((mask & ym[y]).sum()) for y in DEV_YEARS}
                if n < 240 or min(ns.values()) < 60:
                    continue
                hits = int(dev.loc[mask, "hit_60"].sum())
                year_hits = {y: float(dev.loc[mask & ym[y], "hit_60"].mean()) for y in DEV_YEARS}
                rows.append({
                    "rule": rule_text(ac, vals),
                    "axes": "|".join(ac),
                    "values": "|".join(vals),
                    "clauses": k,
                    "n_dev": n,
                    "n_2022": ns[2022], "n_2023": ns[2023], "n_2024": ns[2024],
                    "hit_dev": hits / n,
                    "hit_2022": year_hits[2022], "hit_2023": year_hits[2023], "hit_2024": year_hits[2024],
                    "worst_dev_hit": min(year_hits.values()),
                    "wilson_dev": wilson_lcb(hits, n),
                    "median_signed_60_dev": float(dev.loc[mask, "fwd_60"].median()),
                    "aux_ge54_dev": sum(float(dev.loc[mask, f"hit_{h}"].mean()) >= 0.54 for h in (15, 30, 120, 360)),
                    "max_dev_share": max(ns.values()) / n,
                    "pval_one_sided": float(binomtest(hits, n, 0.5, alternative="greater").pvalue),
                })

    R = pd.DataFrame(rows)
    if len(R):
        R["qval_bh"] = bh_adjust(R["pval_one_sided"].to_numpy(float))
        R["fdr_sig"] = R["qval_bh"] <= 0.05
        R["dev_gate"] = (
            (R["hit_dev"] >= 0.58) &
            (R["hit_2022"] >= 0.55) & (R["hit_2023"] >= 0.55) & (R["hit_2024"] >= 0.55) &
            (R["wilson_dev"] > 0.55) & (R["median_signed_60_dev"] > 0.0) &
            (R["aux_ge54_dev"] >= 3) & (R["max_dev_share"] <= 0.45) & R["fdr_sig"]
        )
    R.attrs["grammar_count"] = grammar_count
    return R


def parse_rule_row(row: pd.Series) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return tuple(str(row["axes"]).split("|")), tuple(str(row["values"]).split("|"))


def select_candidates(rules: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    dev = events[events["year"].isin(DEV_YEARS)].copy()
    eligible = rules[rules["dev_gate"]].copy().sort_values(
        ["worst_dev_hit", "wilson_dev", "hit_dev", "clauses", "n_dev", "rule"],
        ascending=[False, False, False, True, False, True],
    )
    selected_indices, selected_masks = [], []
    for idx, row in eligible.iterrows():
        axes, vals = parse_rule_row(row)
        mask = rule_mask(dev, axes, vals)
        if any((np.logical_and(mask, sm).sum() / np.logical_or(mask, sm).sum()) > 0.80 for sm in selected_masks):
            continue
        selected_indices.append(idx)
        selected_masks.append(mask)
        if len(selected_indices) == 3:
            break
    selected = eligible.loc[selected_indices].copy() if selected_indices else eligible.head(0).copy()
    selected.insert(0, "candidate_rank", np.arange(1, len(selected) + 1))
    return selected


def evaluate_reference(selected: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in selected.iterrows():
        axes, vals = parse_rule_row(row)
        g = events.loc[rule_mask(events, axes, vals)].copy()
        m = {"candidate_rank": int(row["candidate_rank"]), "rule": row["rule"], "clauses": int(row["clauses"])}
        for y in ALL_YEARS:
            gy = g[g["year"] == y]
            m[f"n_{y}"] = len(gy)
            m[f"hit_{y}"] = float(gy["hit_60"].mean()) if len(gy) else np.nan
            m[f"median60_{y}"] = float(gy["fwd_60"].median()) if len(gy) else np.nan
        gr = g[g["year"].isin(REF_YEARS)]
        gp = g[g["year"].isin(ALL_YEARS)]
        m["n_reference"] = len(gr)
        m["hit_reference"] = float(gr["hit_60"].mean()) if len(gr) else np.nan
        m["median_signed_60_reference"] = float(gr["fwd_60"].median()) if len(gr) else np.nan
        m["aux_ge54_reference"] = sum(float(gr[f"hit_{h}"].mean()) >= 0.54 for h in (15, 30, 120, 360)) if len(gr) else 0
        m["n_pooled"] = len(gp)
        m["hit_pooled"] = float(gp["hit_60"].mean()) if len(gp) else np.nan
        m["wilson_pooled"] = wilson_lcb(int(gp["hit_60"].sum()), len(gp)) if len(gp) else np.nan
        m["max_five_era_share"] = max((len(gp[gp["year"] == y]) / len(gp) for y in ALL_YEARS), default=np.nan)
        m["reference_gate"] = bool(all([
            m["n_2025"] >= 50, np.isfinite(m["hit_2025"]) and m["hit_2025"] >= 0.55,
            m["n_2026"] >= 40, np.isfinite(m["hit_2026"]) and m["hit_2026"] >= 0.55,
            np.isfinite(m["hit_reference"]) and m["hit_reference"] >= 0.56,
            np.isfinite(m["median_signed_60_reference"]) and m["median_signed_60_reference"] > 0.0,
            m["aux_ge54_reference"] >= 3,
            np.isfinite(m["hit_pooled"]) and m["hit_pooled"] >= 0.57,
            np.isfinite(m["wilson_pooled"]) and m["wilson_pooled"] > 0.55,
            all(np.isfinite(m[f"hit_{y}"]) and m[f"hit_{y}"] > 0.50 for y in ALL_YEARS),
            np.isfinite(m["max_five_era_share"]) and m["max_five_era_share"] <= 0.35,
        ]))
        rows.append(m)
    return pd.DataFrame(rows)


def pct(x) -> str:
    return "nan" if pd.isna(x) else f"{100.0 * float(x):.2f}%"


def main() -> None:
    fp, diag = load_frozen_a1()
    beh = build_forward(fp)
    events = build_events(fp, beh)
    integrity_ok = bool(diag["sha_ok"] and diag["rows_ok"] and diag["boundary_ok"] and diag["quarter_grid_ok"] and diag["unique_ok"] and diag["schema_ok"] and len(events) > 0)

    rules = enumerate_dev_rules(events)
    selected = select_candidates(rules, events)
    ref = evaluate_reference(selected, events)
    status = "BNB_B29_B1J_DATA_TOOLING_FAILURE" if not integrity_ok else ("BNB_B29_B1J_JOURNEY_CHARACTER_PASS" if len(ref) and bool(ref["reference_gate"].any()) else "BNB_B29_B1J_JOURNEY_CHARACTER_REJECT")

    events.reset_index().to_csv(OUT_EVENTS, index=False, compression="gzip")
    rules.to_csv(OUT_RULES, index=False, compression="gzip")
    rules[rules["dev_gate"]].sort_values(["worst_dev_hit", "wilson_dev", "hit_dev", "clauses", "n_dev", "rule"], ascending=[False, False, False, True, False, True]).to_csv(OUT_DEV, index=False)
    selected.to_csv(OUT_SEL, index=False)
    ref.to_csv(OUT_REF, index=False)
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B29-B1J — Journey → Sweep → Reclaim Character Result", "", f"**Status: {status}**", "",
        "B1J mines only preregistered causal journey/reclaim clauses around the frozen SWEEP_LOW_RECLAIM -> LONG base event. No entry, TP, SL, leverage, fees, PnL or live orders are tested.", "",
        "## Immutable source integrity", "", "- Accepted A1 artifact id: `10336102957`", f"- Fingerprint SHA256: `{diag['sha256']}`", f"- Exact file hash: **{'PASS' if diag['sha_ok'] else 'FAIL'}**", f"- Rows: {diag['rows']:,}", f"- Known non-15m gaps: {diag['gap_count']} (never crossed by predecessor/outcome calculations)", f"- B1J eligible base events 2022-2026: {len(events):,}", f"- Complete frozen grammar size: {int(rules.attrs.get('grammar_count', 0)):,} rules", f"- Sample-size eligible rules entering FDR family: {len(rules):,}", f"- Rules passing all development gates: {int(rules['dev_gate'].sum()) if len(rules) else 0}", f"- Frozen candidates sent to reference validation: {len(selected)}", "",
        "## Frozen development shortlist", "", "| Rank | Rule | N dev | Hit dev | Wilson LCB | Worst dev era | Aux >=54% | BH q |", "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    if len(selected):
        for _, r in selected.iterrows():
            lines.append(f"| {int(r.candidate_rank)} | `{r.rule}` | {int(r.n_dev)} | {pct(r.hit_dev)} | {pct(r.wilson_dev)} | {pct(r.worst_dev_hit)} | {int(r.aux_ge54_dev)} | {float(r.qval_bh):.6g} |")
    else:
        lines.append("| - | No development rule passed the frozen gate | - | - | - | - | - | - |")

    lines += ["", "## Reference validation", "", "| Rank | Rule | 2025 N / hit | 2026 N / hit | Ref hit | Ref aux >=54% | Pooled hit | Pooled Wilson | Gate |", "|---:|---|---:|---:|---:|---:|---:|---:|---|"]
    if len(ref):
        for _, r in ref.iterrows():
            lines.append(f"| {int(r.candidate_rank)} | `{r.rule}` | {int(r.n_2025)} / {pct(r.hit_2025)} | {int(r.n_2026)} / {pct(r.hit_2026)} | {pct(r.hit_reference)} | {int(r.aux_ge54_reference)} | {pct(r.hit_pooled)} | {pct(r.wilson_pooled)} | {'PASS' if bool(r.reference_gate) else 'REJECT'} |")
    else:
        lines.append("| - | No candidate reached reference validation | - | - | - | - | - | - | REJECT |")

    lines += ["", "## Five-era +60m detail", "", "| Rank | 2022 | 2023 | 2024 | 2025 | 2026 |", "|---:|---:|---:|---:|---:|---:|"]
    for _, r in ref.iterrows():
        lines.append(f"| {int(r.candidate_rank)} | {int(r.n_2022)} / {pct(r.hit_2022)} | {int(r.n_2023)} / {pct(r.hit_2023)} | {int(r.n_2024)} / {pct(r.hit_2024)} | {int(r.n_2025)} / {pct(r.hit_2025)} | {int(r.n_2026)} / {pct(r.hit_2026)} |")

    lines += ["", "## Decision", "", f"**{status}**", ""]
    if status == "BNB_B29_B1J_JOURNEY_CHARACTER_PASS":
        lines.append(f"{int(ref['reference_gate'].sum())} frozen journey character candidate(s) passed every preregistered development and reference gate. This is character-level promotion only; execution discovery remains separate and final ready-to-trade proof still requires future shadow data after the complete strategy is frozen.")
    elif status == "BNB_B29_B1J_JOURNEY_CHARACTER_REJECT":
        lines.append("No frozen journey character candidate passed every preregistered development and reference gate. Do not rescue B1J-v1 by changing clauses, thresholds, horizons, clocks, or sample gates after observing this result.")
    else:
        lines.append("Scientific interpretation is blocked by an integrity/tooling failure.")
    lines += ["", "No live orders were placed."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
