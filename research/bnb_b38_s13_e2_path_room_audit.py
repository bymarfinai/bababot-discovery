#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s3_adaptive_execution as s3
import bnb_b38_s11_e2_economics as s11
import bnb_b38_s12_e2_target_selection as s12

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B38_S13_E2_PATH_ROOM_AUDIT"
START = pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END = pd.Timestamp("2024-12-31T23:59:59Z")
HORIZONS = [4, 12, 24]
THRESHOLDS = [0.25, 0.50, 1.00, 1.50, 2.00]
TARGETS = [
    ("TP1", "tp1", "tp1_source"),
    ("TP2", "tp2", "tp2_source"),
    ("TP3", "tp3", "tp3_source"),
    ("EXPANSION", "expansion_target", None),
    ("H1_NEAREST", "h1_nearest", None),
    ("MAJOR_NEAREST", "major_nearest", None),
]


def period(ts):
    return "DEV" if pd.Timestamp(ts) <= DEV_END else "REF"


def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"


def fmt_num(x, d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"


def first_touch_idx(raw5, entry_ts, level, kind, end):
    if not np.isfinite(level):
        return None
    idx = raw5.index
    i0 = int(idx.searchsorted(entry_ts, side="right"))
    i1 = int(idx.searchsorted(end, side="right"))
    if i1 <= i0:
        return None
    arr = (raw5.high if kind == "HIGH" else raw5.low).to_numpy(float, copy=False)[i0:i1]
    z = np.flatnonzero(arr >= level) if kind == "HIGH" else np.flatnonzero(arr <= level)
    return (i0 + int(z[0])) if len(z) else None


def path_window(raw5, entry_ts, entry, sl, end, hours=None):
    idx = raw5.index
    i0 = int(idx.searchsorted(entry_ts, side="right"))
    stop_idx = first_touch_idx(raw5, entry_ts, sl, "LOW", end)

    horizon_end = end if hours is None else min(end, entry_ts + pd.Timedelta(hours=hours))
    i1 = int(idx.searchsorted(horizon_end, side="right"))
    if stop_idx is not None:
        i1 = min(i1, stop_idx)

    risk = entry - sl
    if not (risk > 0) or i1 <= i0:
        return {
            "mfe_r": np.nan, "mae_r": np.nan, "peak_ts": pd.NaT,
            "peak_hours": np.nan, "post_peak_min_r": np.nan,
            "giveback_r": np.nan, "bars": 0,
            "sl_observed": stop_idx is not None,
            "sl_ts": idx[stop_idx] if stop_idx is not None else pd.NaT,
        }

    q = raw5.iloc[i0:i1]
    hi = q.high.to_numpy(float, copy=False)
    lo = q.low.to_numpy(float, copy=False)
    j = int(np.argmax(hi))
    peak = float(hi[j])
    trough = float(np.min(lo))
    peak_abs = i0 + j
    peak_ts = idx[peak_abs]
    mfe = (peak - entry) / risk
    mae = (trough - entry) / risk

    after = raw5.iloc[peak_abs:i1]
    post_min = float(after.low.min()) if len(after) else peak
    post_min_r = (post_min - entry) / risk
    giveback = (peak - post_min) / risk

    return {
        "mfe_r": float(mfe), "mae_r": float(mae), "peak_ts": peak_ts,
        "peak_hours": float((peak_ts - entry_ts) / pd.Timedelta(hours=1)),
        "post_peak_min_r": float(post_min_r), "giveback_r": float(giveback),
        "bars": int(len(q)), "sl_observed": stop_idx is not None,
        "sl_ts": idx[stop_idx] if stop_idx is not None else pd.NaT,
    }


def target_probe(raw5, entry_ts, entry, sl, target, end):
    if not np.isfinite(target) or target <= entry or not (entry > sl):
        return {
            "available": False, "distance_r": np.nan, "touch_ts": pd.NaT,
            "touch_hours": np.nan, "hit_before_sl": False,
            "ambiguous_with_sl": False, "hit_24h": False,
        }
    risk = entry - sl
    ti = first_touch_idx(raw5, entry_ts, target, "HIGH", end)
    si = first_touch_idx(raw5, entry_ts, sl, "LOW", end)
    hit = ti is not None and (si is None or ti < si)
    amb = ti is not None and si is not None and ti == si
    touch_ts = raw5.index[ti] if ti is not None else pd.NaT
    hrs = float((touch_ts - entry_ts) / pd.Timedelta(hours=1)) if pd.notna(touch_ts) else np.nan
    return {
        "available": True,
        "distance_r": float((target - entry) / risk),
        "touch_ts": touch_ts,
        "touch_hours": hrs,
        "hit_before_sl": bool(hit),
        "ambiguous_with_sl": bool(amb),
        "hit_24h": bool(hit and hrs <= 24.0),
    }


def plan_signature(P):
    q = P[["zone_id", "entry_ts", "entry_price", "touch_low_sl", "tp1"]].copy()
    q = q.sort_values(["entry_ts", "zone_id"])
    lines = []
    for r in q.itertuples(index=False):
        lines.append(
            f"{r.zone_id}|{pd.Timestamp(r.entry_ts).isoformat()}|"
            f"{float(r.entry_price):.10f}|{float(r.touch_low_sl):.10f}|{float(r.tp1):.10f}"
        )
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def room_band(x):
    if not np.isfinite(x): return "NA"
    if x < 0.25: return "<0.25R"
    if x < 0.50: return "0.25-0.50R"
    if x < 1.00: return "0.50-1.00R"
    if x < 2.00: return "1.00-2.00R"
    return ">=2.00R"


def main():
    raw, diag = b31.load_raw()
    if diag["coverage"] < .995:
        raise RuntimeError(f"raw coverage low {diag}")
    a1 = b31.load_a1()
    ident = b31.identity(raw, a1)
    if ident["max_ret15_diff"] > 5e-8 or ident["max_close_location_diff"] > 5e-8:
        raise RuntimeError(f"identity fail {ident}")
    end = raw.index.max()

    s1.START = START
    s1.END = end
    s3.END = end
    h1 = s1.exact_exec(raw, "1h", 12)
    h1 = h1[h1.index <= end]
    m15 = s1.exact_exec(raw, "15min", 3)
    m15 = m15[m15.index <= end]
    raw5 = raw[["open", "high", "low", "close"]].astype(float)

    zones = s1.demand_zones(h1)
    fam = s1.visual_family(m15, zones)
    fam = fam[
        (pd.to_datetime(fam.first_touch_ts, utc=True) >= START) &
        (pd.to_datetime(fam.first_touch_ts, utc=True) <= end)
    ].copy()
    dev = fam[pd.to_datetime(fam.first_touch_ts, utc=True) <= DEV_END]
    ref = fam[pd.to_datetime(fam.first_touch_ts, utc=True) > DEV_END]
    if len(dev) != 788 or len(ref) != 463:
        raise RuntimeError(f"parent parity drift dev={len(dev)} ref={len(ref)}")

    # STEP 1 — freeze exact E2 plans from S11/S12.
    P = s11.e2_plans(m15, h1, fam, end)
    K = s12.known_targets_at_entry(P, m15, h1, fam)
    P = P.merge(K, on="zone_id", how="left", validate="one_to_one")
    P["period"] = [period(x) for x in P.first_touch_ts]

    # S11/S12 economics baseline only includes executable plans:
    # TP1 must exist and entry must sit above the frozen structural touch-low SL.
    P = P[np.isfinite(P.tp1) & (P.entry_price > P.touch_low_sl)].copy()

    if len(P[P.period == "DEV"]) != 440 or len(P[P.period == "REF"]) != 272:
        raise RuntimeError(f"E2 executable parity drift dev={sum(P.period=='DEV')} ref={sum(P.period=='REF')}")

    baseline_rows = []
    for r in P.itertuples(index=False):
        if not np.isfinite(r.tp1) or not (r.entry_price > r.touch_low_sl):
            continue
        out, rt, rr = s11.touch_resolve(
            raw5, r.entry_ts, r.entry_price, r.touch_low_sl, r.tp1, end
        )
        baseline_rows.append({
            "zone_id": r.zone_id, "baseline_outcome": out,
            "baseline_resolution_ts": rt, "baseline_realized_r": rr,
        })
    BASE = pd.DataFrame(baseline_rows)
    P = P.merge(BASE, on="zone_id", how="left", validate="one_to_one")

    parity = {
        "DEV_WIN": int(((P.period == "DEV") & (P.baseline_outcome == "WIN")).sum()),
        "DEV_LOSS": int(((P.period == "DEV") & (P.baseline_outcome == "LOSS")).sum()),
        "REF_WIN": int(((P.period == "REF") & (P.baseline_outcome == "WIN")).sum()),
        "REF_LOSS": int(((P.period == "REF") & (P.baseline_outcome == "LOSS")).sum()),
    }
    expected = {"DEV_WIN": 325, "DEV_LOSS": 115, "REF_WIN": 201, "REF_LOSS": 71}
    if parity != expected:
        raise RuntimeError(f"E2 baseline parity drift got={parity} expected={expected}")

    signature = plan_signature(P)

    # STEP 2 — path audit. Every frozen E2 plan is measured.
    ledger = []
    target_rows = []
    for r in P.itertuples(index=False):
        entry = float(r.entry_price)
        sl = float(r.touch_low_sl)
        risk = entry - sl
        if not (risk > 0):
            continue

        rec = {
            "zone_id": r.zone_id, "first_touch_ts": r.first_touch_ts,
            "period": r.period, "year": r.year, "entry_ts": r.entry_ts,
            "entry_price": entry, "sl": sl, "risk": risk,
            "baseline_outcome": r.baseline_outcome,
            "baseline_resolution_ts": r.baseline_resolution_ts,
            "baseline_realized_r": r.baseline_realized_r,
            "tp1": r.tp1, "tp1_source": r.tp1_source,
            "tp2": r.tp2, "tp2_source": r.tp2_source,
            "tp3": r.tp3, "tp3_source": r.tp3_source,
            "expansion_target": r.expansion_target,
            "h1_nearest": r.h1_nearest,
            "major_nearest": r.major_nearest,
            "known_target_count": r.known_target_count,
        }

        for h in HORIZONS:
            w = path_window(raw5, r.entry_ts, entry, sl, end, hours=h)
            rec[f"mfe_{h}h_r"] = w["mfe_r"]
            rec[f"mae_{h}h_r"] = w["mae_r"]
            rec[f"peak_{h}h_ts"] = w["peak_ts"]
            rec[f"peak_{h}h_hours"] = w["peak_hours"]
            rec[f"post_peak_min_{h}h_r"] = w["post_peak_min_r"]
            rec[f"giveback_{h}h_r"] = w["giveback_r"]

        full = path_window(raw5, r.entry_ts, entry, sl, end, hours=None)
        rec["mfe_pre_sl_r"] = full["mfe_r"]
        rec["mae_pre_sl_r"] = full["mae_r"]
        rec["peak_pre_sl_ts"] = full["peak_ts"]
        rec["peak_pre_sl_hours"] = full["peak_hours"]
        rec["post_peak_min_pre_sl_r"] = full["post_peak_min_r"]
        rec["giveback_pre_sl_r"] = full["giveback_r"]
        rec["sl_observed"] = full["sl_observed"]
        rec["sl_ts"] = full["sl_ts"]

        tp1_r = (float(r.tp1) - entry) / risk if np.isfinite(r.tp1) else np.nan
        rec["tp1_r"] = tp1_r
        rec["room_band_24h"] = room_band(rec["mfe_24h_r"])
        rec["missed_room_24h_r"] = max(0.0, rec["mfe_24h_r"] - tp1_r) if np.isfinite(rec["mfe_24h_r"]) and np.isfinite(tp1_r) else np.nan
        rec["capture_fraction_24h"] = tp1_r / rec["mfe_24h_r"] if np.isfinite(rec["mfe_24h_r"]) and rec["mfe_24h_r"] > 0 and np.isfinite(tp1_r) else np.nan
        rec["missed_room_pre_sl_r"] = max(0.0, rec["mfe_pre_sl_r"] - tp1_r) if np.isfinite(rec["mfe_pre_sl_r"]) and np.isfinite(tp1_r) else np.nan
        rec["capture_fraction_pre_sl"] = tp1_r / rec["mfe_pre_sl_r"] if np.isfinite(rec["mfe_pre_sl_r"]) and rec["mfe_pre_sl_r"] > 0 and np.isfinite(tp1_r) else np.nan

        for th in THRESHOLDS:
            rec[f"reached_{th:.2f}r_24h"] = bool(np.isfinite(rec["mfe_24h_r"]) and rec["mfe_24h_r"] >= th)
            rec[f"reached_{th:.2f}r_pre_sl"] = bool(np.isfinite(rec["mfe_pre_sl_r"]) and rec["mfe_pre_sl_r"] >= th)

        ledger.append(rec)

        # STEP 3 — causal structural/liquidity targets already known at entry.
        for label, col, source_col in TARGETS:
            target = getattr(r, col)
            source = getattr(r, source_col) if source_col else label
            p = target_probe(raw5, r.entry_ts, entry, sl, target, end)
            target_rows.append({
                "zone_id": r.zone_id, "period": r.period, "year": r.year,
                "entry_ts": r.entry_ts, "baseline_outcome": r.baseline_outcome,
                "target": label, "source": source,
                "level": target, **p,
            })

    L = pd.DataFrame(ledger)
    T = pd.DataFrame(target_rows)

    path_summary = []
    for per in ["DEV", "REF"]:
        for out in ["ALL", "WIN", "LOSS"]:
            q = L[L.period == per]
            if out != "ALL":
                q = q[q.baseline_outcome == out]
            if not len(q):
                continue
            path_summary.append({
                "period": per, "baseline_outcome": out, "n": len(q),
                "median_tp1_r": float(q.tp1_r.median()),
                "median_mfe_4h_r": float(q.mfe_4h_r.median()),
                "median_mfe_12h_r": float(q.mfe_12h_r.median()),
                "median_mfe_24h_r": float(q.mfe_24h_r.median()),
                "median_mfe_pre_sl_r": float(q.mfe_pre_sl_r.median()),
                "median_mae_24h_r": float(q.mae_24h_r.median()),
                "median_peak_24h_hours": float(q.peak_24h_hours.median()),
                "median_giveback_24h_r": float(q.giveback_24h_r.median()),
                "median_missed_room_24h_r": float(q.missed_room_24h_r.median()),
                "median_capture_fraction_24h": float(q.capture_fraction_24h.median()),
                "median_missed_room_pre_sl_r": float(q.missed_room_pre_sl_r.median()),
                "median_capture_fraction_pre_sl": float(q.capture_fraction_pre_sl.median()),
            })
    PS = pd.DataFrame(path_summary)

    thresholds = []
    for per in ["DEV", "REF"]:
        for out in ["WIN", "LOSS"]:
            q = L[(L.period == per) & (L.baseline_outcome == out)]
            for th in THRESHOLDS:
                thresholds.append({
                    "period": per, "baseline_outcome": out, "threshold_r": th,
                    "n": len(q),
                    "reached_24h": int(q[f"reached_{th:.2f}r_24h"].sum()),
                    "rate_24h": float(q[f"reached_{th:.2f}r_24h"].mean()),
                    "reached_pre_sl": int(q[f"reached_{th:.2f}r_pre_sl"].sum()),
                    "rate_pre_sl": float(q[f"reached_{th:.2f}r_pre_sl"].mean()),
                })
    TH = pd.DataFrame(thresholds)

    target_map = []
    for per in ["DEV", "REF"]:
        for out in ["ALL", "WIN", "LOSS"]:
            q0 = T[T.period == per]
            if out != "ALL":
                q0 = q0[q0.baseline_outcome == out]
            for target in [x[0] for x in TARGETS]:
                q = q0[(q0.target == target) & (q0.available)]
                if not len(q):
                    continue
                target_map.append({
                    "period": per, "baseline_outcome": out, "target": target,
                    "available": len(q),
                    "median_distance_r": float(q.distance_r.median()),
                    "hit_before_sl": int(q.hit_before_sl.sum()),
                    "hit_before_sl_rate": float(q.hit_before_sl.mean()),
                    "hit_24h": int(q.hit_24h.sum()),
                    "hit_24h_rate": float(q.hit_24h.mean()),
                    "median_touch_hours_when_hit": float(q.loc[q.hit_before_sl, "touch_hours"].median()) if q.hit_before_sl.any() else np.nan,
                    "ambiguous": int(q.ambiguous_with_sl.sum()),
                })
    TM = pd.DataFrame(target_map)

    room_dist = (
        L.groupby(["period", "baseline_outcome", "room_band_24h"], dropna=False)
         .size().reset_index(name="n")
    )

    tp2 = T[(T.target == "TP2") & (T.available)].copy()
    extension = []
    for per in ["DEV", "REF"]:
        for out in ["WIN", "LOSS"]:
            q = tp2[(tp2.period == per) & (tp2.baseline_outcome == out)]
            extension.append({
                "period": per, "baseline_outcome": out, "tp2_available": len(q),
                "tp2_hit_before_sl": int(q.hit_before_sl.sum()),
                "tp2_hit_rate": float(q.hit_before_sl.mean()) if len(q) else np.nan,
                "tp2_hit_24h": int(q.hit_24h.sum()),
                "tp2_hit_24h_rate": float(q.hit_24h.mean()) if len(q) else np.nan,
                "median_tp2_distance_r": float(q.distance_r.median()) if len(q) else np.nan,
            })
    EX = pd.DataFrame(extension)

    L.to_csv(ROOT / f"{PFX}_Ledger.csv.gz", index=False, compression="gzip")
    T.to_csv(ROOT / f"{PFX}_Targets.csv.gz", index=False, compression="gzip")
    PS.to_csv(ROOT / f"{PFX}_PathSummary.csv", index=False)
    TH.to_csv(ROOT / f"{PFX}_Thresholds.csv", index=False)
    TM.to_csv(ROOT / f"{PFX}_TargetMap.csv", index=False)
    room_dist.to_csv(ROOT / f"{PFX}_RoomDistribution.csv", index=False)
    EX.to_csv(ROOT / f"{PFX}_TP2Extension.csv", index=False)
    (ROOT / f"{PFX}_Freeze.txt").write_text(
        "E2_FROZEN=TRUE\n"
        f"PLAN_SIGNATURE_SHA256={signature}\n"
        "DEV_PLANS=440\nREF_PLANS=272\nDEV_WINS=325\nDEV_LOSSES=115\nREF_WINS=201\nREF_LOSSES=71\n",
        encoding="utf-8",
    )

    lines = [
        "# BNB B38-S13 — E2 Path & Real-Room Audit", "",
        "**Step 1 freeze:** exact S10/S11 E2 detector, entry, touch-low SL, and TP1 baseline are unchanged.",
        f"Frozen plan signature: `{signature}`", "",
        "## Baseline parity", "",
        "| Period | Plans | WIN | LOSS | WR |",
        "|---|---:|---:|---:|---:|",
        f"| DEV | 440 | 325 | 115 | {fmt_pct(325/440)} |",
        f"| REF | 272 | 201 | 71 | {fmt_pct(201/272)} |", "",
        "## Step 2 — path anatomy", "",
        "MFE/MAE horizons are capped at the first structural SL touch; the SL bar itself is excluded because intrabar ordering is unknown.", "",
        "| Period | Outcome | N | TP1 med | MFE 4h | MFE 12h | MFE 24h | MFE pre-SL | MAE 24h | Missed room 24h | Capture 24h |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in PS.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.baseline_outcome} | {r.n} | {fmt_num(r.median_tp1_r)}R | "
            f"{fmt_num(r.median_mfe_4h_r)}R | {fmt_num(r.median_mfe_12h_r)}R | "
            f"{fmt_num(r.median_mfe_24h_r)}R | {fmt_num(r.median_mfe_pre_sl_r)}R | "
            f"{fmt_num(r.median_mae_24h_r)}R | {fmt_num(r.median_missed_room_24h_r)}R | "
            f"{fmt_pct(r.median_capture_fraction_24h)} |"
        )

    lines += ["", "### Excursion thresholds", "",
        "| Period | Outcome | Threshold | Reach 24h | Reach pre-SL |",
        "|---|---|---:|---:|---:|"
    ]
    for r in TH.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.baseline_outcome} | {r.threshold_r:.2f}R | "
            f"{r.reached_24h}/{r.n} ({fmt_pct(r.rate_24h)}) | "
            f"{r.reached_pre_sl}/{r.n} ({fmt_pct(r.rate_pre_sl)}) |"
        )

    lines += ["", "## Step 3 — known structural/liquidity room", "",
        "Every level below was already known at entry; no future pivots are used.", "",
        "| Period | Outcome | Target | Available | Med distance | Hit before SL | Hit <=24h | Med hours if hit |",
        "|---|---|---|---:|---:|---:|---:|---:|"
    ]
    for r in TM.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.baseline_outcome} | {r.target} | {r.available} | "
            f"{fmt_num(r.median_distance_r)}R | {r.hit_before_sl} ({fmt_pct(r.hit_before_sl_rate)}) | "
            f"{r.hit_24h} ({fmt_pct(r.hit_24h_rate)}) | {fmt_num(r.median_touch_hours_when_hit,2)}h |"
        )

    lines += ["", "### TP2 extension anatomy (diagnostic only)", "",
        "| Period | Outcome | TP2 available | TP2 hit before SL | TP2 hit <=24h | Med TP2 distance |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for r in EX.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.baseline_outcome} | {r.tp2_available} | "
            f"{r.tp2_hit_before_sl} ({fmt_pct(r.tp2_hit_rate)}) | "
            f"{r.tp2_hit_24h} ({fmt_pct(r.tp2_hit_24h_rate)}) | {fmt_num(r.median_tp2_distance_r)}R |"
        )

    lines += ["", "## Interpretation boundary",
        "This audit does not choose a new TP, SL, or entry rule.",
        "It measures how much room the frozen E2 setup actually had and which causal structural objectives were reachable before invalidation.",
        "Any adaptive TP rule must be derived only after this audit and then validated separately on DEV/REF without changing the frozen detector."
    ]
    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text("BNB_B38_S13_E2_PATH_ROOM_AUDIT_COMPLETE\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
