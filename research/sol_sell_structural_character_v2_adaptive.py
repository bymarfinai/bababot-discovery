#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_SELL_STRUCTURAL_CHARACTER_V2_ADAPTIVE"

MODEL_START = pd.Timestamp("2020-01-01", tz="UTC")
MODEL_END = pd.Timestamp("2025-01-01", tz="UTC")
YEARS = (2020, 2021, 2022, 2023, 2024)

RECLAIM_MAX_H1 = 2
BOS_MAX_H1 = 16
RANGE_LOOKBACK = 20
RETURN_MAX_5M = 14 * 24 * 12
RESPONSE_MAX_5M = 24 * 12


def _latest_unconsumed_high(high_hist, consumed):
    for h in reversed(high_hist):
        if int(h["pivot_i"]) not in consumed:
            return h
    return None


def _latest_low_after(low_hist, high_pivot_i):
    for l in reversed(low_hist):
        if int(l["pivot_i"]) > int(high_pivot_i):
            return l
    return None


def detect_h1_family(x5: pd.DataFrame):
    h1 = fc1.build_h1(x5)
    idx = h1.index
    op = h1.open.astype(float).to_numpy()
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()

    lows_by_confirm, highs_by_confirm = lib.compute_pivots(hi, lo)
    high_hist, low_hist = [], []
    consumed_highs = set()
    stage_a, stage_b = [], []

    first_i = max(30, RANGE_LOOKBACK + 3)
    last_i = len(h1) - BOS_MAX_H1 - RECLAIM_MAX_H1 - 3

    for i in range(first_i, last_i):
        high_hist.extend(highs_by_confirm.get(i, []))
        low_hist.extend(lows_by_confirm.get(i, []))

        h0 = _latest_unconsumed_high(high_hist, consumed_highs)
        if h0 is None:
            continue
        l0 = _latest_low_after(low_hist, int(h0["pivot_i"]))
        if l0 is None:
            continue
        if int(h0["confirm_i"]) >= i or int(l0["confirm_i"]) >= i:
            continue

        level = float(h0["price"])
        if not (hi[i] > level):
            continue

        reclaim_i = None
        reclaim_last = min(i + RECLAIM_MAX_H1, len(h1) - 1)
        for k in range(i, reclaim_last + 1):
            if cl[k] < level:
                reclaim_i = k
                break
        if reclaim_i is None:
            continue

        reclaim_close_time = idx[reclaim_i] + pd.Timedelta(hours=1)
        if reclaim_close_time < MODEL_START or reclaim_close_time >= MODEL_END:
            continue

        consumed_highs.add(int(h0["pivot_i"]))
        raid_extreme = float(np.max(hi[i:reclaim_i + 1]))
        med_range = float(np.median(hi[i - RANGE_LOOKBACK:i] - lo[i - RANGE_LOOKBACK:i]))
        if not np.isfinite(med_range) or med_range <= 0:
            continue

        arow = {
            "structure_id": f"{idx[i]}__H{int(h0['pivot_i'])}__L{int(l0['pivot_i'])}",
            "raid_i_h1": int(i),
            "raid_time": idx[i],
            "reclaim_i_h1": int(reclaim_i),
            "reclaim_time": idx[reclaim_i],
            "reclaim_close_time": reclaim_close_time,
            "year": int(reclaim_close_time.year),
            "liquidity_high": level,
            "liquidity_pivot_i": int(h0["pivot_i"]),
            "liquidity_confirm_i": int(h0["confirm_i"]),
            "significant_low": float(l0["price"]),
            "significant_low_pivot_i": int(l0["pivot_i"]),
            "significant_low_confirm_i": int(l0["confirm_i"]),
            "raid_extreme": raid_extreme,
            "raid_depth_pct": float((raid_extreme / level - 1.0) * 100.0),
            "reclaim_delay_h1_bars": int(reclaim_i - i),
            "reclaim_close": float(cl[reclaim_i]),
            "median_prior_h1_range": med_range,
        }
        stage_a.append(arow)

        bos_i = None
        invalidated_before_bos = False
        for j in range(reclaim_i + 1, min(reclaim_i + BOS_MAX_H1 + 1, len(h1))):
            if cl[j] > raid_extreme:
                invalidated_before_bos = True
                break
            if cl[j] < float(l0["price"]):
                bos_i = j
                break
        if bos_i is None or invalidated_before_bos:
            continue

        origin_i = None
        for k in range(bos_i - 1, i - 1, -1):
            if cl[k] > op[k]:
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
        net_down = float(cl[reclaim_i] - cl[bos_i])
        bear_eff = net_down / path if path > 0 else np.nan

        displacement_units = float((raid_extreme - cl[bos_i]) / med_range)
        bos_extension_units = float((float(l0["price"]) - cl[bos_i]) / med_range)
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
            "bos_low": float(lo[bos_i]),
            "bars_reclaim_to_bos": int(bos_i - reclaim_i),
            "displacement_range_units": displacement_units,
            "bear_path_efficiency": float(bear_eff) if np.isfinite(bear_eff) else np.nan,
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
            pre_low = min(float(b.bos_low), float(np.min(lo[start:touch_i])))
        else:
            pre_low = float(b.bos_low)

        penetration = float((min(float(hi[touch_i]), zhi) - zlo) / width) if width > 0 else np.nan
        penetration = max(0.0, penetration) if np.isfinite(penetration) else np.nan

        crow = {
            **b.to_dict(),
            "first_return_i_5m": int(touch_i),
            "first_return_time": idx[touch_i],
            "bos_to_return_min": float((idx[touch_i] - pd.Timestamp(b.bos_close_time)).total_seconds() / 60.0),
            "return_open": float(op[touch_i]),
            "return_high": float(hi[touch_i]),
            "return_low": float(lo[touch_i]),
            "return_close": float(cl[touch_i]),
            "return_penetration_zone_width": penetration,
            "pre_return_structural_low": pre_low,
        }
        stage_c.append(crow)

        outcome = "UNRESOLVED"
        resolution_i = None
        last_response = min(touch_i + RESPONSE_MAX_5M - 1, len(x5) - 1)

        for i in range(touch_i, last_response + 1):
            if idx[i] >= MODEL_END:
                break
            continuation = bool(lo[i] < pre_low)
            invalidated = bool(cl[i] > zhi)

            if i == touch_i and continuation:
                outcome = "AMBIGUOUS"
                resolution_i = i
                break
            if continuation and invalidated:
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
            minutes = float((resolution_time - idx[touch_i]).total_seconds() / 60.0)
        else:
            resolution_time = pd.NaT
            minutes = np.nan

        horizon_hi = hi[touch_i:last_response + 1]
        horizon_lo = lo[touch_i:last_response + 1]
        max_above_zone = float((np.max(horizon_hi) - zhi) / width) if width > 0 else np.nan
        max_below_prior_low = float((pre_low - np.min(horizon_lo)) / pre_low * 100.0) if pre_low > 0 else np.nan

        stage_d.append({
            **crow,
            "outcome": outcome,
            "resolution_i_5m": int(resolution_i) if resolution_i is not None else -1,
            "resolution_time": resolution_time,
            "return_to_resolution_min": minutes,
            "max_above_zone_width": max_above_zone,
            "max_new_low_extension_pct": max_below_prior_low,
        })

    return pd.DataFrame(stage_c), pd.DataFrame(stage_d)


def summarize(stage_a, stage_b, stage_c, stage_d):
    counts = stage_d.outcome.value_counts().to_dict() if not stage_d.empty else {}
    cont = int(counts.get("CONTINUATION", 0))
    inv = int(counts.get("INVALIDATED", 0))
    amb = int(counts.get("AMBIGUOUS", 0))
    unr = int(counts.get("UNRESOLVED", 0))
    resolved = cont + inv
    rate = cont / resolved if resolved else np.nan

    yearly_rows = []
    for y in YEARS:
        g = stage_d[stage_d.year == y].copy() if not stage_d.empty else pd.DataFrame()
        if g.empty:
            yearly_rows.append({
                "year": y, "n_return": 0, "continuation": 0, "invalidated": 0,
                "ambiguous": 0, "unresolved": 0, "resolved": 0,
                "continuation_rate_resolved": np.nan,
            })
            continue
        vc = g.outcome.value_counts().to_dict()
        c = int(vc.get("CONTINUATION", 0))
        iv = int(vc.get("INVALIDATED", 0))
        rs = c + iv
        yearly_rows.append({
            "year": y,
            "n_return": int(len(g)),
            "continuation": c,
            "invalidated": iv,
            "ambiguous": int(vc.get("AMBIGUOUS", 0)),
            "unresolved": int(vc.get("UNRESOLVED", 0)),
            "resolved": rs,
            "continuation_rate_resolved": c / rs if rs else np.nan,
        })
    yearly = pd.DataFrame(yearly_rows)

    features = [
        "raid_depth_pct",
        "reclaim_delay_h1_bars",
        "bars_reclaim_to_bos",
        "displacement_range_units",
        "bear_path_efficiency",
        "bos_extension_range_units",
        "zone_width_range_units",
        "bos_to_return_min",
        "return_penetration_zone_width",
    ]
    feature_rows = []
    if not stage_d.empty:
        for outcome, g in stage_d.groupby("outcome"):
            row = {"outcome": outcome, "n": int(len(g))}
            for f in features:
                vals = pd.to_numeric(g[f], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
                row[f + "_median"] = float(vals.median()) if len(vals) else np.nan
                row[f + "_p25"] = float(vals.quantile(.25)) if len(vals) else np.nan
                row[f + "_p75"] = float(vals.quantile(.75)) if len(vals) else np.nan
            feature_rows.append(row)
    feature_by_outcome = pd.DataFrame(feature_rows)

    summary = pd.DataFrame([{
        "stage_a_n": int(len(stage_a)),
        "stage_b_n": int(len(stage_b)),
        "stage_c_n": int(len(stage_c)),
        "stage_d_n": int(len(stage_d)),
        "a_to_b": len(stage_b) / len(stage_a) if len(stage_a) else np.nan,
        "b_to_c": len(stage_c) / len(stage_b) if len(stage_b) else np.nan,
        "continuation": cont,
        "invalidated": inv,
        "ambiguous": amb,
        "unresolved": unr,
        "resolved": resolved,
        "continuation_rate_resolved": rate,
        "median_reclaim_to_bos_h1_bars": float(stage_b.bars_reclaim_to_bos.median()) if len(stage_b) else np.nan,
        "median_bos_to_return_min": float(stage_c.bos_to_return_min.median()) if len(stage_c) else np.nan,
        "median_return_to_resolution_min": float(stage_d.loc[stage_d.resolution_i_5m >= 0, "return_to_resolution_min"].median()) if len(stage_d) else np.nan,
    }])

    return summary, yearly, feature_by_outcome


def _pct(v):
    return "n/a" if pd.isna(v) else f"{float(v)*100:.2f}%"


def _num(v, d=2):
    return "n/a" if pd.isna(v) else f"{float(v):.{d}f}"


def main():
    wf1.v3.v1.base.fetch_one = wf1.v3.v1.fetch_one_with_volume
    x5, coverage = wf1.v3.v1.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    _, stage_a, stage_b = detect_h1_family(x5)
    stage_c, stage_d = resolve_return_and_response(stage_b, x5)
    summary, yearly, feature_by_outcome = summarize(stage_a, stage_b, stage_c, stage_d)

    stage_a.to_csv(ROOT / f"{PFX}_StageA_Raids.csv", index=False)
    stage_b.to_csv(ROOT / f"{PFX}_StageB_BOS.csv", index=False)
    stage_c.to_csv(ROOT / f"{PFX}_StageC_Returns.csv", index=False)
    stage_d.to_csv(ROOT / f"{PFX}_StageD_Responses.csv", index=False)
    summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearSummary.csv", index=False)
    feature_by_outcome.to_csv(ROOT / f"{PFX}_FeatureByOutcome.csv", index=False)

    s = summary.iloc[0]
    lines = [
        "# SOL SELL Structural Character V2 — Adaptive Grammar Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        "- Development: **2020-2024**; 2025+ CLOSED.",
        "- No fixed entry, TP or SL is tested here.",
        "- Grammar: **liquidity raid/reclaim -> bearish BOS/new-low state -> return to bearish origin area -> continuation vs origin invalidation**.",
        "",
        "## Structural funnel",
        "",
        "| Stage | Meaning | N | Conversion |",
        "|---|---|---:|---:|",
        f"| A | Buy-side liquidity raid + reclaim family | {len(stage_a)} | 100.00% |",
        f"| B | Bearish BOS + origin block | {len(stage_b)} | {_pct(len(stage_b)/len(stage_a) if len(stage_a) else np.nan)} |",
        f"| C | Corrective return into origin area | {len(stage_c)} | {_pct(len(stage_c)/len(stage_b) if len(stage_b) else np.nan)} |",
        f"| D | Structural response observed | {len(stage_d)} | {_pct(len(stage_d)/len(stage_c) if len(stage_c) else np.nan)} |",
        "",
        "## Structural response after return",
        "",
        f"- CONTINUATION (fresh low first): **{int(s.continuation)}**",
        f"- INVALIDATED (origin close-break first): **{int(s.invalidated)}**",
        f"- AMBIGUOUS: **{int(s.ambiguous)}**",
        f"- UNRESOLVED within 24h: **{int(s.unresolved)}**",
        f"- Continuation rate among resolved cases: **{_pct(s.continuation_rate_resolved)}**",
        "",
        "## Timing anatomy",
        "",
        f"- Median reclaim -> bearish BOS: **{_num(s.median_reclaim_to_bos_h1_bars,1)} H1 bars**",
        f"- Median BOS -> origin return: **{_num(s.median_bos_to_return_min,1)} minutes**",
        f"- Median return -> structural resolution: **{_num(s.median_return_to_resolution_min,1)} minutes**",
        "",
        "## Yearly structural response",
        "",
        "| Year | Returns | Continuation | Invalidated | Ambiguous | Unresolved | Continuation / resolved |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, y in yearly.iterrows():
        lines.append(
            f"| {int(y.year)} | {int(y.n_return)} | {int(y.continuation)} | {int(y.invalidated)} | {int(y.ambiguous)} | {int(y.unresolved)} | {_pct(y.continuation_rate_resolved)} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "This experiment tests the **structural family**, not a candle-perfect copy of one screenshot.",
        "A continuation means that after SOL returned into the bearish origin area it produced a fresh structural low before invalidating that area.",
        "The next phase, if this family is useful, is to characterize which pre-entry information can identify the continuation members causally. Only after that do adaptive entry, SL and TP get designed.",
        "",
        "2025_PLUS=CLOSED",
    ]
    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
