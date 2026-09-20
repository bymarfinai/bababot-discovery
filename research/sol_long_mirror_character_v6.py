#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import time
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_LONG_MIRROR_CHARACTER_V6"

MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
YEARS = (2020, 2021, 2022, 2023, 2024)

RECLAIM_MAX_H1 = 2
BOS_MAX_H1 = 16
RANGE_LOOKBACK = 20
RETURN_MAX_5M = 14 * 24 * 12
RESPONSE_MAX_5M = 24 * 12

FROZEN_BEAR_BODY_SHARE_MIN = 0.141955835962
FROZEN_FALL_PER_BAR_MAX = 0.310541310541


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


def _latest_unconsumed_low(low_hist, consumed):
    for x in reversed(low_hist):
        if int(x["pivot_i"]) not in consumed:
            return x
    return None


def _latest_high_after(high_hist, low_pivot_i):
    for h in reversed(high_hist):
        if int(h["pivot_i"]) > int(low_pivot_i):
            return h
    return None


def detect_h1_long_family(x5: pd.DataFrame):
    h1 = fc1.build_h1(x5)
    idx = h1.index
    op = h1.open.astype(float).to_numpy()
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()

    lows_by_confirm, highs_by_confirm = lib.compute_pivots(hi, lo)
    low_hist, high_hist = [], []
    consumed_lows = set()
    stage_a, stage_b = [], []

    first_i = max(30, RANGE_LOOKBACK + 3)
    last_i = len(h1) - BOS_MAX_H1 - RECLAIM_MAX_H1 - 3

    for i in range(first_i, last_i):
        low_hist.extend(lows_by_confirm.get(i, []))
        high_hist.extend(highs_by_confirm.get(i, []))

        l0 = _latest_unconsumed_low(low_hist, consumed_lows)
        if l0 is None:
            continue
        h0 = _latest_high_after(high_hist, int(l0["pivot_i"]))
        if h0 is None:
            continue
        if int(l0["confirm_i"]) >= i or int(h0["confirm_i"]) >= i:
            continue

        level = float(l0["price"])
        if not (lo[i] < level):
            continue

        reclaim_i = None
        reclaim_last = min(i + RECLAIM_MAX_H1, len(h1) - 1)
        for k in range(i, reclaim_last + 1):
            if cl[k] > level:
                reclaim_i = k
                break
        if reclaim_i is None:
            continue

        reclaim_close_time = idx[reclaim_i] + pd.Timedelta(hours=1)
        if reclaim_close_time < MODEL_START or reclaim_close_time >= MODEL_END:
            continue

        consumed_lows.add(int(l0["pivot_i"]))
        raid_extreme = float(np.min(lo[i:reclaim_i + 1]))
        med_range = float(np.median(hi[i - RANGE_LOOKBACK:i] - lo[i - RANGE_LOOKBACK:i]))
        if not np.isfinite(med_range) or med_range <= 0:
            continue

        arow = {
            "structure_id": f"{idx[i]}__L{int(l0['pivot_i'])}__H{int(h0['pivot_i'])}",
            "raid_i_h1": int(i),
            "raid_time": idx[i],
            "reclaim_i_h1": int(reclaim_i),
            "reclaim_time": idx[reclaim_i],
            "reclaim_close_time": reclaim_close_time,
            "raid_year": int(reclaim_close_time.year),
            "liquidity_low": level,
            "liquidity_pivot_i": int(l0["pivot_i"]),
            "liquidity_confirm_i": int(l0["confirm_i"]),
            "significant_high": float(h0["price"]),
            "significant_high_pivot_i": int(h0["pivot_i"]),
            "significant_high_confirm_i": int(h0["confirm_i"]),
            "raid_extreme": raid_extreme,
            "raid_depth_pct": float((level - raid_extreme) / level * 100.0) if level > 0 else np.nan,
            "reclaim_delay_h1_bars": int(reclaim_i - i),
            "reclaim_close": float(cl[reclaim_i]),
            "median_prior_h1_range": med_range,
        }
        stage_a.append(arow)

        bos_i = None
        invalidated_before_bos = False
        for j in range(reclaim_i + 1, min(reclaim_i + BOS_MAX_H1 + 1, len(h1))):
            if cl[j] < raid_extreme:
                invalidated_before_bos = True
                break
            if cl[j] > float(h0["price"]):
                bos_i = j
                break
        if bos_i is None or invalidated_before_bos:
            continue

        origin_i = None
        for k in range(bos_i - 1, i - 1, -1):
            if cl[k] < op[k]:
                origin_i = int(k)
                break
        if origin_i is None:
            continue

        zone_low = float(lo[origin_i])
        zone_high = float(hi[origin_i])
        if not (np.isfinite(zone_low) and np.isfinite(zone_high) and zone_high > zone_low):
            continue

        path_closes = cl[reclaim_i:bos_i + 1]
        path = float(np.abs(np.diff(path_closes)).sum())
        net_up = float(cl[bos_i] - cl[reclaim_i])
        bull_eff = net_up / path if path > 0 else np.nan

        displacement_units = float((cl[bos_i] - raid_extreme) / med_range)
        bos_extension_units = float((cl[bos_i] - float(h0["price"])) / med_range)
        zone_width_units = float((zone_high - zone_low) / med_range)

        bos_close_time = idx[bos_i] + pd.Timedelta(hours=1)
        if bos_close_time >= MODEL_END:
            continue

        stage_b.append({
            **arow,
            "bos_i_h1": int(bos_i),
            "bos_time": idx[bos_i],
            "bos_close_time": bos_close_time,
            "bos_close": float(cl[bos_i]),
            "bos_high": float(hi[bos_i]),
            "bars_reclaim_to_bos": int(bos_i - reclaim_i),
            "displacement_range_units": displacement_units,
            "bull_path_efficiency": float(bull_eff) if np.isfinite(bull_eff) else np.nan,
            "bos_extension_range_units": bos_extension_units,
            "origin_i_h1": int(origin_i),
            "origin_time": idx[origin_i],
            "origin_open": float(op[origin_i]),
            "origin_high": zone_high,
            "origin_low": zone_low,
            "origin_close": float(cl[origin_i]),
            "zone_low": zone_low,
            "zone_high": zone_high,
            "zone_width_range_units": zone_width_units,
        })

    return h1, pd.DataFrame(stage_a), pd.DataFrame(stage_b)


def resolve_return_and_response(stage_b: pd.DataFrame, x5: pd.DataFrame):
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()

    stage_c, stage_d = [], []

    for _, b in stage_b.iterrows():
        start = int(idx.searchsorted(pd.Timestamp(b.bos_close_time)))
        if start >= len(x5) - 2:
            continue

        last_return = min(start + RETURN_MAX_5M - 1, len(x5) - 2)
        zlo = float(b.zone_low)
        zhi = float(b.zone_high)
        width = zhi - zlo

        touch_i = None
        for i in range(start, last_return + 1):
            if idx[i] >= MODEL_END:
                break
            if hi[i] >= zlo and lo[i] <= zhi:
                touch_i = i
                break
        if touch_i is None:
            continue

        if touch_i > start:
            pre_high = max(float(b.bos_high), float(np.max(hi[start:touch_i])))
        else:
            pre_high = float(b.bos_high)

        penetration = (
            float((zhi - max(float(lo[touch_i]), zlo)) / width)
            if width > 0 else np.nan
        )
        penetration = max(0.0, penetration) if np.isfinite(penetration) else np.nan

        return_time = idx[touch_i]
        crow = {
            **b.to_dict(),
            "first_return_i_5m": int(touch_i),
            "first_return_time": return_time,
            "return_year": int(return_time.year),
            "bos_to_return_min": float((return_time - pd.Timestamp(b.bos_close_time)).total_seconds() / 60.0),
            "return_open": float(op[touch_i]),
            "return_high": float(hi[touch_i]),
            "return_low": float(lo[touch_i]),
            "return_close": float(cl[touch_i]),
            "return_penetration_zone_width": penetration,
            "pre_return_structural_high": pre_high,
        }
        stage_c.append(crow)

        outcome = "UNRESOLVED"
        resolution_i = None
        last_response = min(touch_i + RESPONSE_MAX_5M - 1, len(x5) - 1)

        for i in range(touch_i, last_response + 1):
            if idx[i] >= MODEL_END:
                break
            continuation = bool(hi[i] > pre_high)
            invalidated = bool(cl[i] < zlo)

            if continuation and invalidated:
                outcome = "AMBIGUOUS"
                resolution_i = i
                break
            if i == touch_i and continuation:
                outcome = "AMBIGUOUS"
                resolution_i = i
                break
            if continuation:
                outcome = "CONTINUATION"
                resolution_i = i
                break
            if invalidated:
                outcome = "INVALIDATED"
                resolution_i = i
                break

        if resolution_i is not None:
            resolution_time = idx[resolution_i]
            minutes = float((resolution_time - return_time).total_seconds() / 60.0)
        else:
            resolution_time = pd.NaT
            minutes = np.nan

        stage_d.append({
            **crow,
            "outcome": outcome,
            "resolution_i_5m": int(resolution_i) if resolution_i is not None else -1,
            "resolution_time": resolution_time,
            "return_to_resolution_min": minutes,
        })

    return pd.DataFrame(stage_c), pd.DataFrame(stage_d)


def structural_dedup(stage_d: pd.DataFrame) -> pd.DataFrame:
    if stage_d.empty:
        return stage_d.copy()
    x = stage_d.sort_values(
        ["bos_i_h1", "origin_i_h1", "first_return_i_5m", "raid_i_h1", "structure_id"],
        ascending=[True, True, True, True, True],
    )
    return x.drop_duplicates(
        subset=["bos_i_h1", "origin_i_h1", "first_return_i_5m"],
        keep="first",
    ).reset_index(drop=True)


def overlap_ratio(ph, pl, ch, cl):
    pr = ph - pl
    cr = ch - cl
    den = min(pr, cr)
    if not np.isfinite(den) or den <= 0:
        return np.nan
    ov = max(0.0, min(ph, ch) - max(pl, cl))
    return float(np.clip(ov / den, 0.0, 1.0))


def extract_mirror_features(dedup: pd.DataFrame, x5: pd.DataFrame) -> pd.DataFrame:
    idx = x5.index
    op = x5.open.astype(float).to_numpy()
    hi = x5.high.astype(float).to_numpy()
    lo = x5.low.astype(float).to_numpy()
    cl = x5.close.astype(float).to_numpy()

    rows = []

    for _, r in dedup.iterrows():
        start = int(idx.searchsorted(pd.Timestamp(r.bos_close_time)))
        touch = int(r.first_return_i_5m)

        out = r.to_dict()
        out["path_status"] = "USABLE"

        if touch <= start:
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        pre = hi[start:touch]
        if len(pre) == 0 or not np.isfinite(pre).any():
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        max_high = float(np.nanmax(pre))
        tol = max(1e-12, abs(max_high) * 1e-12)
        rel_candidates = np.where(np.isclose(pre, max_high, rtol=0.0, atol=tol))[0]
        if len(rel_candidates) == 0:
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        anchor = start + int(rel_candidates[-1])
        n = touch - anchor + 1

        out["path_anchor_i_5m"] = anchor
        out["path_anchor_time"] = idx[anchor]
        out["path_anchor_high"] = float(hi[anchor])
        out["descent_bars"] = int(n)

        if n < 4:
            out["path_status"] = "TOO_SHORT_FOR_COMPRESSION"
            rows.append(out)
            continue

        pop = op[anchor:touch+1]
        phi = hi[anchor:touch+1]
        plo = lo[anchor:touch+1]
        pcl = cl[anchor:touch+1]

        ranges = phi - plo
        bodies = np.abs(pcl - pop)
        med_range = float(np.nanmedian(ranges))

        net_fall = float(pcl[0] - pcl[-1])
        diffs = np.diff(pcl)
        path = float(np.nansum(np.abs(diffs)))
        efficiency = net_fall / path if path > 0 else np.nan

        ovs = []
        for j in range(1, n):
            ovs.append(overlap_ratio(phi[j-1], plo[j-1], phi[j], plo[j]))
        ovs = np.array(ovs, dtype=float)
        valid_ovs = ovs[np.isfinite(ovs)]

        third = max(1, n // 3)
        first_r = float(np.nanmedian(ranges[:third]))
        last_r = float(np.nanmedian(ranges[-third:]))
        first_b = float(np.nanmedian(bodies[:third]))
        last_b = float(np.nanmedian(bodies[-third:]))

        bear_bodies = np.maximum(pop - pcl, 0.0)
        bear_sum = float(np.nansum(bear_bodies))
        max_bear = float(np.nanmax(bear_bodies)) if len(bear_bodies) else np.nan

        nz = diffs[np.abs(diffs) > 1e-12]
        if len(nz) >= 2:
            flips = np.sign(nz[1:]) != np.sign(nz[:-1])
            sign_flip = float(np.mean(flips))
        else:
            sign_flip = np.nan

        lower_high_share = float(np.mean(phi[1:] < phi[:-1])) if n >= 2 else np.nan

        denom_drawdown = float(hi[anchor]) - float(r.zone_high)
        drawdown = (
            (float(hi[anchor]) - float(lo[touch])) / denom_drawdown
            if denom_drawdown > 0 else np.nan
        )

        out.update({
            "down_path_efficiency": float(efficiency) if np.isfinite(efficiency) else np.nan,
            "median_adjacent_overlap": float(np.nanmedian(valid_ovs)) if len(valid_ovs) else np.nan,
            "overlap_gt50_share": float(np.mean(valid_ovs >= 0.50)) if len(valid_ovs) else np.nan,
            "range_contraction_ratio": float(last_r / first_r) if first_r > 0 else np.nan,
            "body_contraction_ratio": float(last_b / first_b) if first_b > 0 else np.nan,
            "largest_bear_body_share": float(max_bear / bear_sum) if bear_sum > 0 else np.nan,
            "sign_flip_rate": sign_flip,
            "lower_high_share": lower_high_share,
            "fall_per_bar_range_units": float(net_fall / ((n - 1) * med_range)) if n > 1 and med_range > 0 else np.nan,
            "max_bear_body_range_units": float(max_bear / med_range) if med_range > 0 else np.nan,
            "pre_return_drawdown_fraction": float(drawdown) if np.isfinite(drawdown) else np.nan,
        })
        rows.append(out)

    return pd.DataFrame(rows)


def rate(df: pd.DataFrame) -> float:
    if df.empty:
        return np.nan
    return float((df.outcome == "CONTINUATION").mean())


def mirror_mask(df: pd.DataFrame) -> pd.Series:
    body = pd.to_numeric(df["largest_bear_body_share"], errors="coerce")
    fall = pd.to_numeric(df["fall_per_bar_range_units"], errors="coerce")
    return (body >= FROZEN_BEAR_BODY_SHARE_MIN) & (fall <= FROZEN_FALL_PER_BAR_MAX)


def feature_summary(usable: pd.DataFrame) -> pd.DataFrame:
    features = [
        "descent_bars",
        "down_path_efficiency",
        "median_adjacent_overlap",
        "overlap_gt50_share",
        "range_contraction_ratio",
        "body_contraction_ratio",
        "largest_bear_body_share",
        "sign_flip_rate",
        "lower_high_share",
        "fall_per_bar_range_units",
        "max_bear_body_range_units",
        "pre_return_drawdown_fraction",
    ]
    rows = []
    for outcome, g in usable.groupby("outcome"):
        row = {"outcome": outcome, "n": int(len(g))}
        for f in features:
            s = pd.to_numeric(g[f], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            row[f + "_median"] = float(s.median()) if len(s) else np.nan
            row[f + "_p25"] = float(s.quantile(.25)) if len(s) else np.nan
            row[f + "_p75"] = float(s.quantile(.75)) if len(s) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def comparison_rows(usable: pd.DataFrame, selected: pd.DataFrame):
    rows = []

    def add(label, base, sel):
        br = rate(base)
        sr = rate(sel)
        rows.append({
            "segment": label,
            "baseline_n": len(base),
            "baseline_rate": br,
            "selected_n": len(sel),
            "selected_rate": sr,
            "lift": sr - br if np.isfinite(sr) and np.isfinite(br) else np.nan,
        })

    add("ALL_2020_2024", usable, selected)

    for y in YEARS:
        base = usable[usable.return_year == y].copy()
        sel = selected[selected.return_year == y].copy()
        add(str(y), base, sel)

    early = usable[usable.return_year.isin([2020, 2021, 2022])].copy()
    early_sel = selected[selected.return_year.isin([2020, 2021, 2022])].copy()
    late = usable[usable.return_year.isin([2023, 2024])].copy()
    late_sel = selected[selected.return_year.isin([2023, 2024])].copy()
    add("ERA_2020_2022", early, early_sel)
    add("ERA_2023_2024", late, late_sel)

    return pd.DataFrame(rows)


def main():
    x5, coverage = load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    _, stage_a, stage_b = detect_h1_long_family(x5)
    stage_c, stage_d = resolve_return_and_response(stage_b, x5)
    dedup = structural_dedup(stage_d)
    features = extract_mirror_features(dedup, x5)

    usable = features[
        features.outcome.isin(["CONTINUATION", "INVALIDATED"])
        & (features.path_status == "USABLE")
    ].copy()

    selected = usable[mirror_mask(usable)].copy()
    comparison = comparison_rows(usable, selected)
    feat_sum = feature_summary(usable)

    overall = comparison[comparison.segment == "ALL_2020_2024"].iloc[0]
    yearly = comparison[comparison.segment.isin([str(y) for y in YEARS])].copy()
    eras = comparison[comparison.segment.str.startswith("ERA_")].copy()

    years_above = int(
        (
            pd.to_numeric(yearly.selected_rate, errors="coerce")
            > pd.to_numeric(yearly.baseline_rate, errors="coerce")
        ).fillna(False).sum()
    )

    early = eras[eras.segment == "ERA_2020_2022"].iloc[0]
    late = eras[eras.segment == "ERA_2023_2024"].iloc[0]

    gates = {
        "selected_n_ge_30": int(overall.selected_n) >= 30,
        "selected_rate_ge_45pct": bool(np.isfinite(overall.selected_rate) and overall.selected_rate >= .45),
        "lift_ge_10pp": bool(np.isfinite(overall.lift) and overall.lift >= .10),
        "yearly_above_baseline_ge_4_of_5": years_above >= 4,
        "both_eras_above_baseline": bool(
            np.isfinite(early.selected_rate)
            and np.isfinite(early.baseline_rate)
            and np.isfinite(late.selected_rate)
            and np.isfinite(late.baseline_rate)
            and early.selected_rate > early.baseline_rate
            and late.selected_rate > late.baseline_rate
        ),
    }

    verdict = (
        "DIRECTIONALLY_SYMMETRIC_STRUCTURAL_CHARACTER"
        if all(gates.values())
        else "MIRROR_NOT_CONFIRMED_AS_DEFINED"
    )

    stage_a.to_csv(ROOT / f"{PFX}_StageA_Raids.csv", index=False)
    stage_b.to_csv(ROOT / f"{PFX}_StageB_BOS.csv", index=False)
    stage_c.to_csv(ROOT / f"{PFX}_StageC_Returns.csv", index=False)
    stage_d.to_csv(ROOT / f"{PFX}_StageD_Responses.csv", index=False)
    dedup.to_csv(ROOT / f"{PFX}_DedupResponses.csv", index=False)
    features.to_csv(ROOT / f"{PFX}_PathFeatures.csv", index=False)
    usable.to_csv(ROOT / f"{PFX}_UsableResolved.csv", index=False)
    selected.to_csv(ROOT / f"{PFX}_SelectedMirrorCohort.csv", index=False)
    comparison.to_csv(ROOT / f"{PFX}_Comparison.csv", index=False)
    feat_sum.to_csv(ROOT / f"{PFX}_FeatureSummary.csv", index=False)

    summary = pd.DataFrame([{
        "coverage": coverage,
        "stage_a_n": len(stage_a),
        "stage_b_n": len(stage_b),
        "stage_c_n": len(stage_c),
        "stage_d_n": len(stage_d),
        "dedup_n": len(dedup),
        "usable_resolved_n": len(usable),
        "selected_n": int(overall.selected_n),
        "baseline_rate": float(overall.baseline_rate) if np.isfinite(overall.baseline_rate) else np.nan,
        "selected_rate": float(overall.selected_rate) if np.isfinite(overall.selected_rate) else np.nan,
        "lift": float(overall.lift) if np.isfinite(overall.lift) else np.nan,
        "years_above_baseline": years_above,
        **{f"gate_{k}": v for k, v in gates.items()},
        "verdict": verdict,
    }])
    summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)

    def pct(v):
        return "n/a" if not np.isfinite(v) else f"{v*100:.2f}%"

    lines = [
        "# SOL LONG Mirror Structural Character V6 — Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Validation window: **2020-2024**.",
        "- 2025+ remained CLOSED.",
        "- LONG thresholds were **not optimized**.",
        "- Frozen mirror rule:",
        f"  - largest_bear_body_share >= **{FROZEN_BEAR_BODY_SHARE_MIN:.12f}**",
        f"  - fall_per_bar_range_units <= **{FROZEN_FALL_PER_BAR_MAX:.12f}**",
        "- No entry, TP, SL, session, indicator, or execution optimization.",
        "",
        "## Structural funnel",
        "",
        f"- Stage A sell-side raid/reclaim: **{len(stage_a)}**",
        f"- Stage B bullish BOS + origin: **{len(stage_b)}**",
        f"- Stage C first return: **{len(stage_c)}**",
        f"- Stage D responses: **{len(stage_d)}**",
        f"- Deduplicated paths: **{len(dedup)}**",
        f"- Usable resolved paths: **{len(usable)}**",
        "",
        "## Frozen mirror rule — overall",
        "",
        f"- Baseline: N={int(overall.baseline_n)}, continuation={pct(overall.baseline_rate)}",
        f"- Selected: N={int(overall.selected_n)}, continuation={pct(overall.selected_rate)}",
        f"- Lift: **{overall.lift*100:.2f} pp**" if np.isfinite(overall.lift) else "- Lift: n/a",
        "",
        "## Yearly validation",
        "",
        "| Year | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |",
        "|---:|---:|---:|---:|---:|---:|",
    ]

    for _, y in yearly.iterrows():
        lift = f"{y.lift*100:.2f} pp" if np.isfinite(y.lift) else "n/a"
        lines.append(
            f"| {y.segment} | {int(y.baseline_n)} | {pct(y.baseline_rate)} | "
            f"{int(y.selected_n)} | {pct(y.selected_rate)} | {lift} |"
        )

    lines += [
        "",
        "## Era validation",
        "",
        "| Era | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, e in eras.iterrows():
        lift = f"{e.lift*100:.2f} pp" if np.isfinite(e.lift) else "n/a"
        lines.append(
            f"| {e.segment} | {int(e.baseline_n)} | {pct(e.baseline_rate)} | "
            f"{int(e.selected_n)} | {pct(e.selected_rate)} | {lift} |"
        )

    lines += ["", "## Frozen gate audit", ""]
    for k, v in gates.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} — {k}")

    lines += [
        "",
        f"**VERDICT: {verdict}**",
        "",
        "This experiment tests directional symmetry of the structural character only.",
        "It does not define an entry trigger, stop-loss, take-profit, or trade horizon.",
        "",
        "2025_PLUS=CLOSED",
    ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        f"VERDICT={verdict}\nSELECTED_N={int(overall.selected_n)}\n2025_PLUS=CLOSED\n",
        encoding="utf-8",
    )
    print(text)


if __name__ == "__main__":
    main()
