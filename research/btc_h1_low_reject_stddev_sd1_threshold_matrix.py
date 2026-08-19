#!/usr/bin/env python3
"""Complete preregistered SD1 threshold-by-partition diagnostics. No reselection."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

import btc_h1_low_reject_structure_lr1 as lr1
import btc_h1_low_reject_stddev_sd1 as sd1

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_LowReject_StdDev_SD1_Threshold_Matrix.md"
OUT_JSON = ROOT / "BTC_H1_LowReject_StdDev_SD1_Threshold_Matrix.json"


def main():
    x = lr1.load_1h()
    ev = sd1.add_sigma_features(x, lr1.build_events(x))
    ext = ev[(ev.event_ts >= lr1.EXTERNAL_START) & (ev.event_ts < lr1.EXTERNAL_END)].sort_values("event_ts").reset_index(drop=True)
    ref = ev[(ev.event_ts >= lr1.REFERENCE_START) & (ev.event_ts < lr1.REFERENCE_END)].sort_values("event_ts").reset_index(drop=True)
    aug = ev[(ev.event_ts >= lr1.AUG_START) & (ev.event_ts < lr1.AUG_END)].sort_values("event_ts").reset_index(drop=True)
    cut = int(len(ref) * 0.70)
    parts = {
        "development": ref.iloc[:cut].copy(),
        "reference_validation": ref.iloc[cut:].copy(),
        "external": ext,
        "august": aug,
    }
    rows = []
    for t in sd1.THRESHOLDS:
        for part, z in parts.items():
            s = sd1.direction_stats(sd1.filt(z, t))
            rows.append({"threshold_sigma": t, "partition": part, **s})
    result = {
        "protocol": "BTC_H1_LOW_REJECT_STDDEV_SD1_THRESHOLD_MATRIX",
        "frozen_selected_threshold_sigma": 0.0,
        "note": "Diagnostic completion required by SD1 preregistration. Does not reselect threshold.",
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC H1 LOW_REJECT StdDev SD1 — Threshold Matrix",
        "",
        "This completes the preregistered all-threshold diagnostics. **It does not reselect the frozen SD1 threshold (0.00σ).**",
        "",
        "| Min sweep σ | Development N/+3H | Validation N/+3H | External N/+3H | August N/+3H |",
        "|---:|---:|---:|---:|---:|",
    ]
    by = {(r["threshold_sigma"], r["partition"]): r for r in rows}
    for t in sd1.THRESHOLDS:
        vals = []
        for p in ["development", "reference_validation", "external", "august"]:
            r = by[(t, p)]
            vals.append(f"{r['n']}/{sd1.pct(r['pos3h'])}")
        md.append(f"| {t:.2f}σ | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} |")
    md += [
        "",
        "Any apparently attractive non-selected threshold is descriptive only and cannot replace the frozen selector without a new independently preregistered experiment.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
