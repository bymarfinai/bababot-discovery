#!/usr/bin/env python3
"""BTC H1 LOW_REJECT standard-deviation normalization SD1."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_h1_low_reject_structure_lr1 as lr1

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_LowReject_StdDev_SD1_Result.md"
OUT_JSON = ROOT / "BTC_H1_LowReject_StdDev_SD1_Result.json"
OUT_GRID = ROOT / "BTC_H1_LowReject_StdDev_SD1_Grid.csv"
OUT_AUG = ROOT / "BTC_H1_LowReject_StdDev_SD1_August.csv"

THRESHOLDS = [0.00, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50]
MIN_DEV_N = 25


def wilson(w: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = w / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / den
    return center - half, center + half


def add_sigma_features(x: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in ev.iterrows():
        i = int(r.source_index)
        if i < 24:
            continue
        prior24 = x.iloc[i-24:i]
        event_ts = pd.Timestamp(r.event_ts)
        if len(prior24) != 24:
            continue
        if pd.Timestamp(prior24.ts.iloc[0]) != event_ts - pd.Timedelta(hours=24):
            continue
        if pd.Timestamp(prior24.ts.iloc[-1]) != event_ts - pd.Timedelta(hours=1):
            continue
        hourly_log_returns = np.log(prior24.close.to_numpy(float) / prior24.open.to_numpy(float))
        sigma24 = float(np.std(hourly_log_returns, ddof=1))
        if not np.isfinite(sigma24) or sigma24 <= 0:
            continue
        sweep_frac = (float(r.prior3_low) - float(r.event_low)) / float(r.prior3_low)
        sweep_sigma = sweep_frac / sigma24
        q = r.to_dict()
        q.update({"sigma24": sigma24, "sweep_frac": sweep_frac, "sweep_sigma": sweep_sigma})
        rows.append(q)
    return pd.DataFrame(rows)


def filt(z: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if z.empty:
        return z.copy()
    return z[z.sweep_sigma >= threshold].copy()


def direction_stats(z: pd.DataFrame) -> dict:
    if z.empty:
        return {
            "n": 0, "wins3h": 0, "pos1h": None, "pos3h": None,
            "wilson_lo": None, "wilson_hi": None,
            "avg3h": None, "median3h": None,
            "median_sweep_sigma": None, "mean_sweep_sigma": None,
        }
    w = int(z.positive3h.sum())
    n = int(len(z))
    lo, hi = wilson(w, n)
    return {
        "n": n,
        "wins3h": w,
        "pos1h": float(z.positive1h.mean()),
        "pos3h": float(z.positive3h.mean()),
        "wilson_lo": lo,
        "wilson_hi": hi,
        "avg3h": float(z.ret3h_long.mean()),
        "median3h": float(z.ret3h_long.median()),
        "median_sweep_sigma": float(z.sweep_sigma.median()),
        "mean_sweep_sigma": float(z.sweep_sigma.mean()),
    }


def block_stats(z: pd.DataFrame) -> list[dict]:
    if z.empty:
        return []
    y = z.sort_values("event_ts").reset_index(drop=True)
    bounds = np.linspace(0, len(y), 5, dtype=int)
    out = []
    for j in range(4):
        p = y.iloc[bounds[j]:bounds[j+1]].copy()
        out.append({"block": f"B{j+1}", **direction_stats(p)})
    return out


def per_hour(z: pd.DataFrame) -> list[dict]:
    out = []
    for h in lr1.EVENT_HOURS:
        q = z[z.event_hour_utc == h]
        out.append({"hour_utc": h, "hour_wib": (h + 7) % 24, **direction_stats(q)})
    return out


def pct(v):
    return "-" if v is None else f"{100*v:.2f}%"


def money(v):
    return "-" if v is None else f"${v:.3f}"


def sigtxt(v):
    return "-" if v is None else f"{v:.3f}σ"


def main():
    x = lr1.load_1h()
    ev = add_sigma_features(x, lr1.build_events(x))

    ext = ev[(ev.event_ts >= lr1.EXTERNAL_START) & (ev.event_ts < lr1.EXTERNAL_END)].sort_values("event_ts").reset_index(drop=True)
    ref = ev[(ev.event_ts >= lr1.REFERENCE_START) & (ev.event_ts < lr1.REFERENCE_END)].sort_values("event_ts").reset_index(drop=True)
    aug = ev[(ev.event_ts >= lr1.AUG_START) & (ev.event_ts < lr1.AUG_END)].sort_values("event_ts").reset_index(drop=True)

    cut = int(math.floor(len(ref) * 0.70))
    dev = ref.iloc[:cut].copy()
    val = ref.iloc[cut:].copy()

    grid = []
    for t in THRESHOLDS:
        s = direction_stats(filt(dev, t))
        grid.append({"threshold_sigma": t, **s, "eligible": bool(s["n"] >= MIN_DEV_N)})

    eligible = [r for r in grid if r["eligible"]]
    if not eligible:
        raise RuntimeError("no SD1 threshold with development N>=25")
    eligible.sort(key=lambda r: (
        -(r["wilson_lo"] if r["wilson_lo"] is not None else -1.0),
        -(r["pos3h"] if r["pos3h"] is not None else -1.0),
        -r["n"],
        r["threshold_sigma"],
    ))
    selected = eligible[0]
    threshold = float(selected["threshold_sigma"])
    pd.DataFrame(grid).to_csv(OUT_GRID, index=False)

    cohorts = {
        "development_selected": filt(dev, threshold),
        "reference_validation_selected": filt(val, threshold),
        "external_selected": filt(ext, threshold),
        "august_selected": filt(aug, threshold),
        "development_control": dev,
        "reference_validation_control": val,
        "external_control": ext,
        "august_control": aug,
    }
    dirstats = {k: direction_stats(v) for k, v in cohorts.items()}
    execstats = {k: lr1.execution_stats(lr1.execution_rows(x, v)) for k, v in cohorts.items()}

    ext_sel = cohorts["external_selected"]
    val_sel = cohorts["reference_validation_selected"]
    aug_sel = cohorts["august_selected"]
    ext_blocks = block_stats(ext_sel)
    val_hours = per_hour(val_sel)
    ext_hours = per_hour(ext_sel)

    if aug_sel.empty:
        pd.DataFrame(columns=["event_ts"]).to_csv(OUT_AUG, index=False)
    else:
        aug_sel.to_csv(OUT_AUG, index=False)

    block_support = sum(1 for b in ext_blocks if b["n"] >= 8 and b["pos3h"] is not None and b["pos3h"] >= 0.60)
    direction_supported = bool(
        dirstats["reference_validation_selected"]["n"] >= 25
        and dirstats["reference_validation_selected"]["pos3h"] is not None
        and dirstats["reference_validation_selected"]["pos3h"] >= 0.65
        and dirstats["external_selected"]["n"] >= 40
        and dirstats["external_selected"]["pos3h"] is not None
        and dirstats["external_selected"]["pos3h"] >= 0.65
        and block_support >= 3
    )
    block80 = sum(1 for b in ext_blocks if b["n"] >= 5 and b["pos3h"] is not None and b["pos3h"] >= 0.70)
    cand80 = bool(
        dirstats["reference_validation_selected"]["n"] >= 20
        and dirstats["reference_validation_selected"]["pos3h"] is not None
        and dirstats["reference_validation_selected"]["pos3h"] >= 0.80
        and dirstats["external_selected"]["n"] >= 30
        and dirstats["external_selected"]["pos3h"] is not None
        and dirstats["external_selected"]["pos3h"] >= 0.80
        and block80 >= 3
    )

    result = {
        "protocol": "BTC_H1_LOW_REJECT_STDDEV_SD1",
        "coverage": {"first": str(x.ts.min()), "last": str(x.ts.max()), "rows1h": int(len(x))},
        "core_counts": {"external": int(len(ext)), "reference": int(len(ref)), "development": int(len(dev)), "reference_validation": int(len(val)), "august": int(len(aug))},
        "selected_threshold_sigma": threshold,
        "development_selector": selected,
        "grid": grid,
        "direction": dirstats,
        "execution": execstats,
        "external_blocks": ext_blocks,
        "validation_by_hour": val_hours,
        "external_by_hour": ext_hours,
        "SD1_DIRECTION_SUPPORTED": direction_supported,
        "SD1_80_CANDIDATE": cand80,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC H1 LOW_REJECT StdDev SD1 — Result",
        "",
        "Four fixed clocks only: **11:00 / 15:00 / 01:00 / 02:00 WIB**. 1H LOW_REJECT vs prior3H range. StdDev uses only the prior 24 completed 1H candle log returns.",
        "",
        f"Core events: external **{len(ext)}**, reference **{len(ref)}** (dev {len(dev)}, validation {len(val)}), August **{len(aug)}**.",
        "",
        "## Development threshold grid",
        "",
        "| Min sweep sigma | N | +1H | +3H | Wilson low | Avg3H | Median sweep sigma |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in grid:
        md.append(
            f"| {r['threshold_sigma']:.2f}σ | {r['n']} | {pct(r['pos1h'])} | {pct(r['pos3h'])} | "
            f"{pct(r['wilson_lo'])} | {pct(r['avg3h'])} | {sigtxt(r['median_sweep_sigma'])} |"
        )

    md += [
        "",
        f"Frozen selector chose **sweep >= {threshold:.2f}σ** from development only.",
        "",
        "## Directional validation",
        "",
        "| Partition | Rule | N | +1H | +3H | Wilson low | Avg3H | Median3H |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for part in ["development", "reference_validation", "external", "august"]:
        for rule in ["selected", "control"]:
            s = dirstats[f"{part}_{rule}"]
            md.append(
                f"| {part} | {rule} | {s['n']} | {pct(s['pos1h'])} | {pct(s['pos3h'])} | "
                f"{pct(s['wilson_lo'])} | {pct(s['avg3h'])} | {pct(s['median3h'])} |"
            )

    md += [
        "",
        "## External chronological blocks — selected threshold",
        "",
        "| Block | N | +1H | +3H | Avg3H |",
        "|---|---:|---:|---:|---:|",
    ]
    for b in ext_blocks:
        md.append(f"| {b['block']} | {b['n']} | {pct(b['pos1h'])} | {pct(b['pos3h'])} | {pct(b['avg3h'])} |")

    md += [
        "",
        "## Selected threshold by clock",
        "",
        "### Reference validation",
        "",
        "| WIB | N | +3H | Avg3H |",
        "|---:|---:|---:|---:|",
    ]
    for h in val_hours:
        md.append(f"| {h['hour_wib']:02d}:00 | {h['n']} | {pct(h['pos3h'])} | {pct(h['avg3h'])} |")
    md += ["", "### External 2020-2021", "", "| WIB | N | +3H | Avg3H |", "|---:|---:|---:|---:|"]
    for h in ext_hours:
        md.append(f"| {h['hour_wib']:02d}:00 | {h['n']} | {pct(h['pos3h'])} | {pct(h['avg3h'])} |")

    md += [
        "",
        "## Executable net RR 1:1 diagnostic",
        "",
        "LONG next1H open; SL=event low; TP raw distance=risk+0.30%; fee0.15%; max6H.",
        "",
        "| Partition | Rule | N | TP | SL | WR | PnL | Exp/trade |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for part in ["development", "reference_validation", "external", "august"]:
        for rule in ["selected", "control"]:
            s = execstats[f"{part}_{rule}"]
            md.append(
                f"| {part} | {rule} | {s['n']} | {s['tp']} | {s['sl']} | {pct(s['decisive_wr'])} | "
                f"${s['pnl']:.2f} | {money(s['expectancy'])} |"
            )

    md += [
        "",
        f"**SD1_DIRECTION_SUPPORTED: {'PASS' if direction_supported else 'FAIL'}**",
        f"**SD1_80_CANDIDATE: {'PASS' if cand80 else 'FAIL'}**",
        "",
        "Threshold was selected on development only. Validation, external, August and per-clock breakdowns were not used in selection. No post-result rescue.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
