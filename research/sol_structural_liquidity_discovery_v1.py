#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import time
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURAL_LIQUIDITY_DISCOVERY_V1"

MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
YEARS = (2020, 2021, 2022, 2023, 2024)
CONF_YEARS = (2023, 2024)

H1_SWING_LIFE = 14 * 24
H4_SWING_LIFE = 14 * 24
EQUAL_CLUSTER_LIFE = 14 * 24
EQUAL_MAX_GAP_H1 = 72
EQUAL_TOL_RANGE_UNITS = 0.25
RANGE_LOOKBACK = 20
RECLAIM_MAX_H1 = 2
BOS_WINDOW_H1 = 16


def load5_with_retry(symbol: str):
    base = wf1.v3.v1.base
    original = wf1.v3.v1.fetch_one_with_volume

    def retry_fetch(*args, **kwargs):
        last = None
        for attempt in range(4):
            try:
                return original(*args, **kwargs)
            except Exception as e:
                last = e
                if attempt < 3:
                    time.sleep(2.0 * (attempt + 1))
        raise last

    base.fetch_one = retry_fetch
    return base.load5(symbol)


def build_h4(h1: pd.DataFrame) -> pd.DataFrame:
    x = h1.resample("4h", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        n=("close", "count"),
    )
    return x[x.n == 4].drop(columns=["n"]).dropna()


def pivot_lists(hi: np.ndarray, lo: np.ndarray):
    lows_by_confirm, highs_by_confirm = lib.compute_pivots(hi, lo)
    lows, highs = [], []
    for c, xs in lows_by_confirm.items():
        for x in xs:
            lows.append({**x, "confirm_i": int(c)})
    for c, xs in highs_by_confirm.items():
        for x in xs:
            highs.append({**x, "confirm_i": int(c)})
    lows.sort(key=lambda z: (z["confirm_i"], z["pivot_i"]))
    highs.sort(key=lambda z: (z["confirm_i"], z["pivot_i"]))
    return lows_by_confirm, highs_by_confirm, lows, highs


def latest_known_arrays(n: int, lows_by_confirm, highs_by_confirm):
    latest_low_before = [None] * n
    latest_high_before = [None] * n
    latest_low = None
    latest_high = None

    for i in range(n):
        latest_low_before[i] = latest_low
        latest_high_before[i] = latest_high
        for x in lows_by_confirm.get(i, []):
            latest_low = x
        for x in highs_by_confirm.get(i, []):
            latest_high = x

    return latest_low_before, latest_high_before


def med_prior_range(hi, lo, end_i: int):
    start = end_i - RANGE_LOOKBACK
    if start < 0:
        return np.nan
    z = hi[start:end_i] - lo[start:end_i]
    if len(z) != RANGE_LOOKBACK:
        return np.nan
    m = float(np.median(z))
    return m if np.isfinite(m) and m > 0 else np.nan


def add_candidate(rows, family, side, level, activation_i, expiry_i, h1_idx, meta=None):
    if activation_i < 0 or activation_i >= len(h1_idx):
        return
    expiry_i = int(min(max(expiry_i, activation_i + 1), len(h1_idx)))
    activation_time = h1_idx[activation_i]
    expiry_time = h1_idx[expiry_i] if expiry_i < len(h1_idx) else h1_idx[-1] + pd.Timedelta(hours=1)
    if activation_time < MODEL_START or activation_time >= MODEL_END:
        return

    cid = f"{family}|{side}|{activation_time}|{float(level):.12g}|{activation_i}"
    row = {
        "candidate_id": cid,
        "family": family,
        "side": side,
        "level": float(level),
        "activation_i_h1": int(activation_i),
        "activation_time": activation_time,
        "activation_year": int(activation_time.year),
        "expiry_i_h1": int(expiry_i),
        "expiry_time": expiry_time,
    }
    if meta:
        row.update(meta)
    rows.append(row)


def generate_candidates(h1: pd.DataFrame) -> pd.DataFrame:
    idx = h1.index
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()

    _, _, lows, highs = pivot_lists(hi, lo)
    rows = []

    for h in highs:
        ai = int(h["confirm_i"]) + 1
        add_candidate(
            rows, "H1_SWING", "BUY_SIDE", h["price"], ai, ai + H1_SWING_LIFE, idx,
            {"source_pivot_i": int(h["pivot_i"]), "source_confirm_i": int(h["confirm_i"])}
        )
    for l in lows:
        ai = int(l["confirm_i"]) + 1
        add_candidate(
            rows, "H1_SWING", "SELL_SIDE", l["price"], ai, ai + H1_SWING_LIFE, idx,
            {"source_pivot_i": int(l["pivot_i"]), "source_confirm_i": int(l["confirm_i"])}
        )

    for plist, side in ((highs, "BUY_SIDE"), (lows, "SELL_SIDE")):
        for k in range(1, len(plist)):
            p1 = plist[k - 1]
            p2 = plist[k]
            if int(p2["pivot_i"]) - int(p1["pivot_i"]) > EQUAL_MAX_GAP_H1:
                continue
            ai = int(p2["confirm_i"]) + 1
            if ai <= RANGE_LOOKBACK:
                continue
            m = med_prior_range(hi, lo, ai)
            if not np.isfinite(m):
                continue
            diff = abs(float(p2["price"]) - float(p1["price"]))
            if diff > EQUAL_TOL_RANGE_UNITS * m:
                continue
            level = max(float(p1["price"]), float(p2["price"])) if side == "BUY_SIDE" else min(float(p1["price"]), float(p2["price"]))
            add_candidate(
                rows, "H1_EQUAL_CLUSTER", side, level, ai, ai + EQUAL_CLUSTER_LIFE, idx,
                {
                    "source_pivot_i": int(p2["pivot_i"]),
                    "source_confirm_i": int(p2["confirm_i"]),
                    "cluster_prior_pivot_i": int(p1["pivot_i"]),
                    "cluster_price_diff_range_units": float(diff / m),
                }
            )

    h4 = build_h4(h1)
    h4_idx = h4.index
    h4_hi = h4.high.astype(float).to_numpy()
    h4_lo = h4.low.astype(float).to_numpy()
    _, _, h4_lows, h4_highs = pivot_lists(h4_hi, h4_lo)

    for h in h4_highs:
        known_time = h4_idx[int(h["confirm_i"])] + pd.Timedelta(hours=4)
        ai = int(idx.searchsorted(known_time, side="left"))
        add_candidate(
            rows, "H4_SWING", "BUY_SIDE", h["price"], ai, ai + H4_SWING_LIFE, idx,
            {"source_pivot_i": int(h["pivot_i"]), "source_confirm_i": int(h["confirm_i"])}
        )
    for l in h4_lows:
        known_time = h4_idx[int(l["confirm_i"])] + pd.Timedelta(hours=4)
        ai = int(idx.searchsorted(known_time, side="left"))
        add_candidate(
            rows, "H4_SWING", "SELL_SIDE", l["price"], ai, ai + H4_SWING_LIFE, idx,
            {"source_pivot_i": int(l["pivot_i"]), "source_confirm_i": int(l["confirm_i"])}
        )

    tmp = h1.copy()
    tmp["day"] = tmp.index.normalize()
    for day, g in tmp.groupby("day", sort=True):
        if len(g) != 24:
            continue
        at = pd.Timestamp(day) + pd.Timedelta(days=1)
        ai = int(idx.searchsorted(at, side="left"))
        if ai >= len(idx):
            continue
        ei = int(idx.searchsorted(at + pd.Timedelta(days=1), side="left"))
        add_candidate(rows, "PREVIOUS_DAY", "BUY_SIDE", float(g.high.max()), ai, ei, idx, {"source_period_start": pd.Timestamp(day)})
        add_candidate(rows, "PREVIOUS_DAY", "SELL_SIDE", float(g.low.min()), ai, ei, idx, {"source_period_start": pd.Timestamp(day)})

    week_start = h1.index.normalize() - pd.to_timedelta(h1.index.weekday, unit="D")
    tmp2 = h1.copy()
    tmp2["week_start"] = week_start
    for ws, g in tmp2.groupby("week_start", sort=True):
        if len(g) != 168:
            continue
        at = pd.Timestamp(ws) + pd.Timedelta(days=7)
        ai = int(idx.searchsorted(at, side="left"))
        if ai >= len(idx):
            continue
        ei = int(idx.searchsorted(at + pd.Timedelta(days=7), side="left"))
        add_candidate(rows, "PREVIOUS_WEEK", "BUY_SIDE", float(g.high.max()), ai, ei, idx, {"source_period_start": pd.Timestamp(ws)})
        add_candidate(rows, "PREVIOUS_WEEK", "SELL_SIDE", float(g.low.min()), ai, ei, idx, {"source_period_start": pd.Timestamp(ws)})

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("no liquidity candidates generated")

    out = out.sort_values(["family", "side", "activation_time", "level", "candidate_id"])
    out = out.drop_duplicates(["family", "side", "activation_i_h1", "level"], keep="first").reset_index(drop=True)
    return out


def label_candidates(h1: pd.DataFrame, candidates: pd.DataFrame):
    idx = h1.index
    op = h1.open.astype(float).to_numpy()
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()

    lows_by_confirm, highs_by_confirm, _, _ = pivot_lists(hi, lo)
    latest_low_before, latest_high_before = latest_known_arrays(len(h1), lows_by_confirm, highs_by_confirm)

    model_end_i = int(idx.searchsorted(MODEL_END, side="left"))
    candidate_rows = []
    sweep_rows = []

    for _, c in candidates.iterrows():
        start = int(c.activation_i_h1)
        stop = min(int(c.expiry_i_h1), model_end_i, len(h1))
        level = float(c.level)
        side = str(c.side)

        first_breach_i = None
        direct = False
        for j in range(start, stop):
            if side == "BUY_SIDE":
                if hi[j] > level:
                    first_breach_i = j
                    direct = bool(op[j] <= level)
                    break
            else:
                if lo[j] < level:
                    first_breach_i = j
                    direct = bool(op[j] >= level)
                    break

        fully_observed_life = int(pd.Timestamp(c.expiry_time) <= MODEL_END)
        crow = c.to_dict()
        crow.update({
            "fully_observed_life": fully_observed_life,
            "first_breach": int(first_breach_i is not None),
            "direct_first_sweep": int(first_breach_i is not None and direct),
            "first_breach_time": idx[first_breach_i] if first_breach_i is not None else pd.NaT,
            "age_to_first_breach_hours": float((idx[first_breach_i] - pd.Timestamp(c.activation_time)).total_seconds() / 3600.0) if first_breach_i is not None else np.nan,
        })
        candidate_rows.append(crow)

        if first_breach_i is None or not direct:
            continue

        j = first_breach_i
        if j + RECLAIM_MAX_H1 + BOS_WINDOW_H1 >= model_end_i:
            sweep_rows.append({
                **c.to_dict(),
                "sweep_i_h1": int(j),
                "sweep_time": idx[j],
                "sweep_year": int(idx[j].year),
                "sweep_extreme": float(hi[j] if side == "BUY_SIDE" else lo[j]),
                "reclaim_i_h1": -1,
                "outcome": "RIGHT_CENSORED",
            })
            continue

        sweep_extreme = float(hi[j] if side == "BUY_SIDE" else lo[j])
        m = med_prior_range(hi, lo, j)

        if side == "BUY_SIDE":
            sweep_depth = sweep_extreme - level
            sig = latest_low_before[j]
        else:
            sweep_depth = level - sweep_extreme
            sig = latest_high_before[j]

        reclaim_i = None
        for k in range(j, j + RECLAIM_MAX_H1 + 1):
            if side == "BUY_SIDE" and cl[k] < level:
                reclaim_i = k
                break
            if side == "SELL_SIDE" and cl[k] > level:
                reclaim_i = k
                break

        base = {
            **c.to_dict(),
            "sweep_i_h1": int(j),
            "sweep_time": idx[j],
            "sweep_year": int(idx[j].year),
            "sweep_open": float(op[j]),
            "sweep_high": float(hi[j]),
            "sweep_low": float(lo[j]),
            "sweep_close": float(cl[j]),
            "sweep_extreme": sweep_extreme,
            "sweep_depth": float(sweep_depth),
            "sweep_depth_range_units": float(sweep_depth / m) if np.isfinite(m) and m > 0 else np.nan,
            "age_to_sweep_hours": float((idx[j] - pd.Timestamp(c.activation_time)).total_seconds() / 3600.0),
            "same_bar_reclaim": int(reclaim_i == j) if reclaim_i is not None else 0,
            "reclaim_i_h1": int(reclaim_i) if reclaim_i is not None else -1,
            "reclaim_time": idx[reclaim_i] if reclaim_i is not None else pd.NaT,
            "reclaim_delay_h1_bars": int(reclaim_i - j) if reclaim_i is not None else np.nan,
            "significant_opposite_pivot_i": int(sig["pivot_i"]) if sig is not None else -1,
            "significant_opposite_confirm_i": int(sig["confirm_i"]) if sig is not None else -1,
            "significant_opposite_level": float(sig["price"]) if sig is not None else np.nan,
        }

        if reclaim_i is None:
            sweep_rows.append({**base, "outcome": "ACCEPTED_OR_NO_RECLAIM"})
            continue

        if sig is None:
            sweep_rows.append({**base, "outcome": "NO_OPPOSITE_REFERENCE"})
            continue

        outcome = "RECLAIM_NO_BOS_WITHIN_WINDOW"
        resolution_i = None
        bos_i = None

        end = min(reclaim_i + BOS_WINDOW_H1, len(h1), model_end_i)
        for t in range(reclaim_i, end):
            if side == "BUY_SIDE":
                if cl[t] < float(sig["price"]):
                    outcome = "STRUCTURAL_LIQUIDITY_EVENT"
                    resolution_i = t
                    bos_i = t
                    break
                if cl[t] > sweep_extreme:
                    outcome = "RECLAIM_FAILED_BEFORE_BOS"
                    resolution_i = t
                    break
            else:
                if cl[t] > float(sig["price"]):
                    outcome = "STRUCTURAL_LIQUIDITY_EVENT"
                    resolution_i = t
                    bos_i = t
                    break
                if cl[t] < sweep_extreme:
                    outcome = "RECLAIM_FAILED_BEFORE_BOS"
                    resolution_i = t
                    break

        extra = {
            "outcome": outcome,
            "resolution_i_h1": int(resolution_i) if resolution_i is not None else -1,
            "resolution_time": idx[resolution_i] if resolution_i is not None else pd.NaT,
            "sweep_to_resolution_h1_bars": int(resolution_i - j) if resolution_i is not None else np.nan,
            "bos_i_h1": int(bos_i) if bos_i is not None else -1,
            "bos_time": idx[bos_i] if bos_i is not None else pd.NaT,
            "bos_close": float(cl[bos_i]) if bos_i is not None else np.nan,
        }

        if bos_i is not None and np.isfinite(m) and m > 0:
            if side == "BUY_SIDE":
                displacement = sweep_extreme - float(cl[bos_i])
                extension = float(sig["price"]) - float(cl[bos_i])
            else:
                displacement = float(cl[bos_i]) - sweep_extreme
                extension = float(cl[bos_i]) - float(sig["price"])
            extra["displacement_range_units"] = float(displacement / m)
            extra["bos_extension_range_units"] = float(extension / m)
        else:
            extra["displacement_range_units"] = np.nan
            extra["bos_extension_range_units"] = np.nan

        sweep_rows.append({**base, **extra})

    return pd.DataFrame(candidate_rows), pd.DataFrame(sweep_rows)


def safe_rate(num, den):
    return float(num / den) if den else np.nan


def family_summary(candidates: pd.DataFrame, sweeps: pd.DataFrame):
    rows = []
    families = sorted(candidates.family.unique())
    for family in families:
        for side in ("BUY_SIDE", "SELL_SIDE"):
            c = candidates[(candidates.family == family) & (candidates.side == side)].copy()
            s = sweeps[(sweeps.family == family) & (sweeps.side == side) & (sweeps.outcome != "RIGHT_CENSORED")].copy()
            fully = c[c.fully_observed_life == 1].copy()

            structural = int((s.outcome == "STRUCTURAL_LIQUIDITY_EVENT").sum())
            reclaimed = int((s.reclaim_i_h1 >= 0).sum()) if len(s) and "reclaim_i_h1" in s.columns else 0

            rows.append({
                "family": family,
                "side": side,
                "candidate_n": len(c),
                "fully_observed_candidate_n": len(fully),
                "direct_sweep_n": len(s),
                "direct_sweep_rate_fully_observed": safe_rate(int(fully.direct_first_sweep.sum()) if len(fully) else 0, len(fully)),
                "reclaim_n": reclaimed,
                "reclaim_rate_among_sweeps": safe_rate(reclaimed, len(s)),
                "structural_event_n": structural,
                "structural_event_rate_among_sweeps": safe_rate(structural, len(s)),
                "structural_event_rate_among_reclaimed": safe_rate(structural, reclaimed),
                "median_age_to_sweep_hours": float(s.age_to_sweep_hours.median()) if len(s) else np.nan,
                "median_sweep_depth_range_units": float(s.sweep_depth_range_units.median()) if len(s) else np.nan,
                "median_displacement_range_units": float(s.loc[s.outcome == "STRUCTURAL_LIQUIDITY_EVENT", "displacement_range_units"].median()) if structural else np.nan,
            })
    return pd.DataFrame(rows)


def year_summary(sweeps: pd.DataFrame):
    rows = []
    z = sweeps[sweeps.outcome != "RIGHT_CENSORED"].copy()
    for family in sorted(z.family.unique()):
        for side in ("BUY_SIDE", "SELL_SIDE"):
            for year in YEARS:
                g = z[(z.family == family) & (z.side == side) & (z.sweep_year == year)].copy()
                structural = int((g.outcome == "STRUCTURAL_LIQUIDITY_EVENT").sum())
                reclaimed = int((g.reclaim_i_h1 >= 0).sum()) if len(g) and "reclaim_i_h1" in g.columns else 0
                rows.append({
                    "family": family,
                    "side": side,
                    "year": year,
                    "sweep_n": len(g),
                    "reclaim_rate": safe_rate(reclaimed, len(g)),
                    "structural_event_rate_sweep": safe_rate(structural, len(g)),
                    "structural_event_rate_reclaimed": safe_rate(structural, reclaimed),
                })
    return pd.DataFrame(rows)


def enrichment_audit(sweeps: pd.DataFrame, yearly: pd.DataFrame):
    rows = []
    z = sweeps[(sweeps.outcome != "RIGHT_CENSORED") & (sweeps.sweep_year.isin(CONF_YEARS))].copy()

    for family in sorted(z.family.unique()):
        if family == "H1_SWING":
            continue
        for side in ("BUY_SIDE", "SELL_SIDE"):
            g = z[(z.family == family) & (z.side == side)].copy()
            b = z[(z.family == "H1_SWING") & (z.side == side)].copy()

            g_struct = int((g.outcome == "STRUCTURAL_LIQUIDITY_EVENT").sum())
            b_struct = int((b.outcome == "STRUCTURAL_LIQUIDITY_EVENT").sum())
            g_reclaim = int((g.reclaim_i_h1 >= 0).sum()) if len(g) else 0
            b_reclaim = int((b.reclaim_i_h1 >= 0).sum()) if len(b) else 0

            gr = safe_rate(g_struct, len(g))
            br = safe_rate(b_struct, len(b))
            grr = safe_rate(g_struct, g_reclaim)
            brr = safe_rate(b_struct, b_reclaim)

            ygates = {}
            for year in CONF_YEARS:
                gy = yearly[(yearly.family == family) & (yearly.side == side) & (yearly.year == year)]
                by = yearly[(yearly.family == "H1_SWING") & (yearly.side == side) & (yearly.year == year)]
                gv = float(gy.structural_event_rate_sweep.iloc[0]) if len(gy) else np.nan
                bv = float(by.structural_event_rate_sweep.iloc[0]) if len(by) else np.nan
                ygates[year] = bool(np.isfinite(gv) and np.isfinite(bv) and gv > bv)

            gates = {
                "confirmation_sweep_n_ge_30": len(g) >= 30,
                "event_rate_lift_ge_8pp": bool(np.isfinite(gr) and np.isfinite(br) and gr - br >= .08),
                "reclaimed_event_rate_lift_ge_8pp": bool(np.isfinite(grr) and np.isfinite(brr) and grr - brr >= .08),
                "year_2023_above_h1_swing": ygates.get(2023, False),
                "year_2024_above_h1_swing": ygates.get(2024, False),
            }
            verdict = "STRUCTURALLY_ENRICHED_LIQUIDITY_FAMILY" if all(gates.values()) else "NOT_ENRICHED_AS_DEFINED"

            rows.append({
                "family": family,
                "side": side,
                "confirmation_sweep_n": len(g),
                "baseline_h1_swing_sweep_n": len(b),
                "event_rate": gr,
                "baseline_event_rate": br,
                "event_rate_lift": gr - br if np.isfinite(gr) and np.isfinite(br) else np.nan,
                "event_rate_reclaimed": grr,
                "baseline_event_rate_reclaimed": brr,
                "event_rate_reclaimed_lift": grr - brr if np.isfinite(grr) and np.isfinite(brr) else np.nan,
                **{f"gate_{k}": v for k, v in gates.items()},
                "verdict": verdict,
            })

    return pd.DataFrame(rows)


def main():
    x5, coverage = load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    h1 = fc1.build_h1(x5)
    candidates0 = generate_candidates(h1)
    candidates, sweeps = label_candidates(h1, candidates0)

    fam = family_summary(candidates, sweeps)
    yearly = year_summary(sweeps)
    audit = enrichment_audit(sweeps, yearly)

    candidates.to_csv(ROOT / f"{PFX}_Candidates.csv", index=False)
    sweeps.to_csv(ROOT / f"{PFX}_Sweeps.csv", index=False)
    fam.to_csv(ROOT / f"{PFX}_FamilySummary.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    audit.to_csv(ROOT / f"{PFX}_EnrichmentAudit.csv", index=False)

    enriched = audit[audit.verdict == "STRUCTURALLY_ENRICHED_LIQUIDITY_FAMILY"].copy() if len(audit) else pd.DataFrame()

    def pct(v):
        return "n/a" if pd.isna(v) or not np.isfinite(v) else f"{float(v)*100:.2f}%"

    lines = [
        "# SOL Structural Liquidity Discovery V1 — Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        f"- H1 bars: **{len(h1):,}**",
        f"- Liquidity candidate instances: **{len(candidates):,}**",
        f"- Direct first-sweep events: **{len(sweeps):,}**",
        "- 2020-2022 descriptive discovery; 2023-2024 frozen confirmation.",
        "- 2025+ CLOSED.",
        "- No entry, TP, SL, PnL, session, or indicator filter.",
        "",
        "## Candidate-family scorecard",
        "",
        "| Family | Side | Candidates | Fully observed | Sweeps | Sweep rate | Reclaim | Structural event / sweep | Structural event / reclaim | Median age |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for _, r in fam.iterrows():
        age = f"{float(r.median_age_to_sweep_hours):.1f}h" if np.isfinite(r.median_age_to_sweep_hours) else "n/a"
        lines.append(
            f"| {r.family} | {r.side} | {int(r.candidate_n)} | {int(r.fully_observed_candidate_n)} | "
            f"{int(r.direct_sweep_n)} | {pct(r.direct_sweep_rate_fully_observed)} | "
            f"{pct(r.reclaim_rate_among_sweeps)} | {pct(r.structural_event_rate_among_sweeps)} | "
            f"{pct(r.structural_event_rate_among_reclaimed)} | {age} |"
        )

    lines += [
        "",
        "## Frozen enrichment audit — 2023-2024",
        "",
        "Each non-baseline family is compared with H1_SWING on the same side.",
        "",
        "| Family | Side | N | Event rate | H1 swing | Lift | Event/reclaim | H1 swing event/reclaim | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, r in audit.iterrows():
        lift_txt = f"{r.event_rate_lift*100:.2f} pp" if np.isfinite(r.event_rate_lift) else "n/a"
        lines.append(
            f"| {r.family} | {r.side} | {int(r.confirmation_sweep_n)} | {pct(r.event_rate)} | "
            f"{pct(r.baseline_event_rate)} | {lift_txt} | {pct(r.event_rate_reclaimed)} | "
            f"{pct(r.baseline_event_rate_reclaimed)} | **{r.verdict}** |"
        )

    lines += ["", "## Enrichment gate audit", ""]
    for _, r in audit.iterrows():
        lines.append(f"### {r.family} | {r.side} — {r.verdict}")
        for c in [
            "confirmation_sweep_n_ge_30",
            "event_rate_lift_ge_8pp",
            "reclaimed_event_rate_lift_ge_8pp",
            "year_2023_above_h1_swing",
            "year_2024_above_h1_swing",
        ]:
            lines.append(f"- {'PASS' if bool(r['gate_'+c]) else 'FAIL'} — {c}")
        lines.append("")

    status = "ENRICHED_FAMILIES=" + (
        ",".join((enriched.family + "|" + enriched.side).tolist()) if len(enriched) else "NONE"
    )

    lines += [
        "## Interpretation",
        "",
        "STRUCTURAL_LIQUIDITY_EVENT is an observed consequence label: a causally-known level was first swept, reclaimed, and followed by an opposite H1 structural break before the sweep extreme was accepted again.",
        "It is not a claim that hidden orders were directly observed.",
        "",
        status,
        "2025_PLUS=CLOSED",
    ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n2025_PLUS=CLOSED\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
