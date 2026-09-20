#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s14_post_tp1_continuation as s14

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B38_S15_PRE_TP1_JOURNEY"
EXPECTED_SIGNATURE = "d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"

FEATURES = [
    "bars_to_tp1",
    "minutes_to_tp1",
    "progress_per_bar_r",
    "distance_remaining_tp1_r",
    "pre_tp1_mae_r",
    "path_efficiency",
    "close_above_entry_rate",
    "green_rate",
    "max_close_pullback_r",
    "last1_progress_r",
    "last3_progress_r",
    "last3_green_rate",
    "tp1_r",
    "tp2_r",
    "extension_gap_r",
    "extension_gap_ratio",
    "known_target_count",
]


def fmt_num(x, d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"


def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"


def first_touch_idx(raw5, entry_ts, level, kind, end):
    return s14.first_touch_idx(raw5, entry_ts, level, kind, end)


def journey_features(raw5, entry_ts, entry, sl, tp1, tp2, t0, known_target_count):
    idx = raw5.index
    risk = entry - sl
    if not (risk > 0):
        raise RuntimeError("invalid risk")

    i0 = int(idx.searchsorted(entry_ts, side="right"))
    q = raw5.iloc[i0:t0].copy()
    bars = len(q)
    touch_ts = idx[t0]
    minutes_to_tp1 = float((touch_ts - entry_ts) / pd.Timedelta(minutes=1))

    tp1_r = (tp1 - entry) / risk
    tp2_r = (tp2 - entry) / risk
    gap_r = (tp2 - tp1) / risk
    gap_ratio = (tp2 - tp1) / (tp1 - entry) if tp1 > entry else np.nan

    if bars == 0:
        return {
            "bars_to_tp1": 0.0,
            "minutes_to_tp1": minutes_to_tp1,
            "progress_per_bar_r": np.nan,
            "distance_remaining_tp1_r": tp1_r,
            "pre_tp1_mae_r": 0.0,
            "path_efficiency": np.nan,
            "close_above_entry_rate": np.nan,
            "green_rate": np.nan,
            "max_close_pullback_r": np.nan,
            "last1_progress_r": np.nan,
            "last3_progress_r": np.nan,
            "last3_green_rate": np.nan,
            "tp1_r": tp1_r,
            "tp2_r": tp2_r,
            "extension_gap_r": gap_r,
            "extension_gap_ratio": gap_ratio,
            "known_target_count": float(known_target_count),
        }

    closes = q.close.to_numpy(float)
    opens = q.open.to_numpy(float)
    lows = q.low.to_numpy(float)

    last_close = float(closes[-1])
    progress_r = (last_close - entry) / risk
    progress_per_bar_r = progress_r / bars
    distance_remaining_r = (tp1 - last_close) / risk
    mae_r = (float(np.min(lows)) - entry) / risk

    path = np.concatenate([[entry], closes])
    total_abs = float(np.sum(np.abs(np.diff(path))))
    efficiency = (last_close - entry) / total_abs if total_abs > 0 else np.nan

    above_rate = float(np.mean(closes > entry))
    green_rate = float(np.mean(closes > opens))

    running_high = np.maximum.accumulate(closes)
    max_pullback_r = float(np.max((running_high - closes) / risk))

    prev = entry if bars == 1 else float(closes[-2])
    last1_r = (last_close - prev) / risk

    j0 = max(0, bars - 3)
    base3 = entry if j0 == 0 else float(closes[j0 - 1])
    last3_r = (last_close - base3) / risk
    last3_green = float(np.mean(closes[j0:] > opens[j0:]))

    return {
        "bars_to_tp1": float(bars),
        "minutes_to_tp1": minutes_to_tp1,
        "progress_per_bar_r": progress_per_bar_r,
        "distance_remaining_tp1_r": distance_remaining_r,
        "pre_tp1_mae_r": mae_r,
        "path_efficiency": efficiency,
        "close_above_entry_rate": above_rate,
        "green_rate": green_rate,
        "max_close_pullback_r": max_pullback_r,
        "last1_progress_r": last1_r,
        "last3_progress_r": last3_r,
        "last3_green_rate": last3_green,
        "tp1_r": tp1_r,
        "tp2_r": tp2_r,
        "extension_gap_r": gap_r,
        "extension_gap_ratio": gap_ratio,
        "known_target_count": float(known_target_count),
    }


def robust_scale(q):
    x = q.dropna().to_numpy(float)
    if not len(x):
        return np.nan
    q25, q75 = np.quantile(x, [0.25, 0.75])
    s = q75 - q25
    if s > 0:
        return float(s)
    sd = float(np.std(x))
    return sd if sd > 0 else np.nan


def feature_compare(L):
    rows = []
    for feature in FEATURES:
        for per in ["DEV", "REF"]:
            q = L[L.period == per]
            e = q[q.label == "EXTENDER"][feature].dropna()
            s = q[q.label == "STOPPER"][feature].dropna()
            med_e = float(e.median()) if len(e) else np.nan
            med_s = float(s.median()) if len(s) else np.nan
            delta = med_e - med_s if np.isfinite(med_e) and np.isfinite(med_s) else np.nan
            scale = robust_scale(q[feature])
            effect = delta / scale if np.isfinite(delta) and np.isfinite(scale) and scale > 0 else np.nan
            rows.append({
                "feature": feature,
                "period": per,
                "n_extender": len(e),
                "n_stopper": len(s),
                "median_extender": med_e,
                "median_stopper": med_s,
                "median_delta": delta,
                "robust_effect": effect,
            })
    return pd.DataFrame(rows)


def make_dev_cuts(L):
    cuts = []
    for feature in FEATURES:
        x = L.loc[L.period == "DEV", feature].dropna().astype(float)
        if not len(x):
            continue
        vals = np.unique(np.quantile(x, [0.25, 0.50, 0.75]))
        cuts.append({
            "feature": feature,
            "q25": float(np.quantile(x, .25)),
            "q50": float(np.quantile(x, .50)),
            "q75": float(np.quantile(x, .75)),
            "unique_internal_cuts": int(len(vals)),
        })
    return pd.DataFrame(cuts)


def assign_band(x, q25, q50, q75):
    if not np.isfinite(x):
        return "NA"
    # Preserve four ordered bands even when some boundaries coincide.
    if x <= q25:
        return "Q1_LOW"
    if x <= q50:
        return "Q2"
    if x <= q75:
        return "Q3"
    return "Q4_HIGH"


def band_audit(L, C):
    rows = []
    cmap = C.set_index("feature")
    for feature in FEATURES:
        if feature not in cmap.index:
            continue
        cr = cmap.loc[feature]
        for per in ["DEV", "REF"]:
            q = L[L.period == per].copy()
            q["band"] = [
                assign_band(float(x), cr.q25, cr.q50, cr.q75) if pd.notna(x) else "NA"
                for x in q[feature]
            ]
            for band in ["Q1_LOW", "Q2", "Q3", "Q4_HIGH", "NA"]:
                z = q[q.band == band]
                if not len(z):
                    continue
                rows.append({
                    "feature": feature,
                    "period": per,
                    "band": band,
                    "n": len(z),
                    "extenders": int((z.label == "EXTENDER").sum()),
                    "stoppers": int((z.label == "STOPPER").sum()),
                    "tp2_rate": float((z.label == "EXTENDER").mean()),
                })
    return pd.DataFrame(rows)


def directional_ranking(COMP, BANDS):
    rows = []
    for feature in FEATURES:
        q = COMP[COMP.feature == feature].set_index("period")
        if not {"DEV", "REF"}.issubset(set(q.index)):
            continue
        de = float(q.loc["DEV", "robust_effect"])
        re = float(q.loc["REF", "robust_effect"])
        same = (
            np.isfinite(de) and np.isfinite(re) and
            np.sign(de) == np.sign(re) and np.sign(de) != 0
        )

        b = BANDS[BANDS.feature == feature]
        devb = b[(b.period == "DEV") & (b.band != "NA")]
        refb = b[(b.period == "REF") & (b.band != "NA")]

        def spread(z):
            if not len(z):
                return np.nan
            return float(z.tp2_rate.max() - z.tp2_rate.min())

        rows.append({
            "feature": feature,
            "dev_effect": de,
            "ref_effect": re,
            "direction_consistent": bool(same),
            "dev_band_spread": spread(devb),
            "ref_band_spread": spread(refb),
            "consistency_score": (
                min(abs(de), abs(re)) if same and np.isfinite(de) and np.isfinite(re) else 0.0
            ),
        })
    R = pd.DataFrame(rows)
    return R.sort_values(
        ["direction_consistent", "consistency_score", "ref_band_spread"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def main():
    raw, diag = b31.load_raw()
    if diag["coverage"] < .995:
        raise RuntimeError(f"raw coverage low {diag}")
    a1 = b31.load_a1()
    ident = b31.identity(raw, a1)
    if ident["max_ret15_diff"] > 5e-8 or ident["max_close_location_diff"] > 5e-8:
        raise RuntimeError(f"identity fail {ident}")

    end = raw.index.max()
    raw5, m15, h1, P, sig = s14.build_frozen(raw, end)
    if sig != EXPECTED_SIGNATURE:
        raise RuntimeError(f"signature drift {sig}")

    Q = P[(P.baseline_outcome == "WIN") & np.isfinite(P.tp2) & (P.tp2 > P.tp1)].copy()
    if int((Q.period == "DEV").sum()) != 288 or int((Q.period == "REF").sum()) != 178:
        raise RuntimeError(
            f"eligible parity drift DEV={int((Q.period=='DEV').sum())} REF={int((Q.period=='REF').sum())}"
        )

    idx = raw5.index
    rows = []
    for r in Q.itertuples(index=False):
        entry = float(r.entry_price)
        sl = float(r.touch_low_sl)
        tp1 = float(r.tp1)
        tp2 = float(r.tp2)

        t0 = first_touch_idx(raw5, r.entry_ts, tp1, "HIGH", end)
        if t0 is None:
            raise RuntimeError(f"missing TP1 touch {r.zone_id}")

        tp2_idx = s14.touch_after_idx(raw5, t0, tp2, "HIGH", len(raw5))
        sl_idx = s14.touch_after_idx(raw5, t0, sl, "LOW", len(raw5))
        extender = tp2_idx is not None and (sl_idx is None or tp2_idx < sl_idx)

        feat = journey_features(
            raw5, r.entry_ts, entry, sl, tp1, tp2, t0, r.known_target_count
        )
        rows.append({
            "zone_id": r.zone_id,
            "period": r.period,
            "year": r.year,
            "entry_ts": r.entry_ts,
            "tp1_touch_ts": idx[t0],
            "label": "EXTENDER" if extender else "STOPPER",
            "tp1_source": r.tp1_source,
            "tp2_source": r.tp2_source,
            **feat,
        })

    L = pd.DataFrame(rows)

    label_summary = []
    for per in ["DEV", "REF"]:
        q = L[L.period == per]
        ext = int((q.label == "EXTENDER").sum())
        stop = int((q.label == "STOPPER").sum())
        label_summary.append({
            "period": per,
            "eligible": len(q),
            "extenders": ext,
            "stoppers": stop,
            "extension_rate": ext / len(q),
        })
    LS = pd.DataFrame(label_summary)

    COMP = feature_compare(L)
    CUTS = make_dev_cuts(L)
    BANDS = band_audit(L, CUTS)
    RANK = directional_ranking(COMP, BANDS)

    source_rows = []
    for per in ["DEV", "REF"]:
        q = L[L.period == per]
        for col in ["tp1_source", "tp2_source"]:
            for src, z in q.groupby(col, dropna=False):
                source_rows.append({
                    "period": per,
                    "source_field": col,
                    "source": src,
                    "n": len(z),
                    "extenders": int((z.label == "EXTENDER").sum()),
                    "tp2_rate": float((z.label == "EXTENDER").mean()),
                })
    SRC = pd.DataFrame(source_rows)

    L.to_csv(ROOT / f"{PFX}_Ledger.csv.gz", index=False, compression="gzip")
    LS.to_csv(ROOT / f"{PFX}_LabelSummary.csv", index=False)
    COMP.to_csv(ROOT / f"{PFX}_FeatureComparison.csv", index=False)
    CUTS.to_csv(ROOT / f"{PFX}_DevCuts.csv", index=False)
    BANDS.to_csv(ROOT / f"{PFX}_BandAudit.csv", index=False)
    RANK.to_csv(ROOT / f"{PFX}_FeatureRanking.csv", index=False)
    SRC.to_csv(ROOT / f"{PFX}_SourceAudit.csv", index=False)
    (ROOT / f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\n"
        "DEV_ELIGIBLE=288\nREF_ELIGIBLE=178\n",
        encoding="utf-8",
    )

    lines = [
        "# BNB B38-S15 — Pre-TP1 Journey Character", "",
        f"Frozen E2 signature: `{sig}`", "",
        "## Label parity", "",
        "| Period | Eligible | EXTENDER | STOPPER | TP2 extension rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in LS.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.eligible} | {r.extenders} | {r.stoppers} | {fmt_pct(r.extension_rate)} |"
        )

    lines += ["", "## EXTENDER vs STOPPER medians", "",
        "| Feature | DEV ext | DEV stop | DEV effect | REF ext | REF stop | REF effect | Same direction? |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    piv = COMP.pivot(index="feature", columns="period")
    for feature in FEATURES:
        d = COMP[(COMP.feature == feature) & (COMP.period == "DEV")].iloc[0]
        r = COMP[(COMP.feature == feature) & (COMP.period == "REF")].iloc[0]
        same = (
            np.isfinite(d.robust_effect) and np.isfinite(r.robust_effect) and
            np.sign(d.robust_effect) == np.sign(r.robust_effect) and np.sign(d.robust_effect) != 0
        )
        lines.append(
            f"| {feature} | {fmt_num(d.median_extender)} | {fmt_num(d.median_stopper)} | "
            f"{fmt_num(d.robust_effect)} | {fmt_num(r.median_extender)} | {fmt_num(r.median_stopper)} | "
            f"{fmt_num(r.robust_effect)} | {'YES' if same else 'NO'} |"
        )

    lines += ["", "## Directional consistency ranking", "",
        "Ranking rewards features whose EXTENDER-vs-STOPPER direction survives from DEV to REF.", "",
        "| Rank | Feature | DEV effect | REF effect | Consistent | DEV quartile spread | REF quartile spread |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    for i, r in enumerate(RANK.itertuples(index=False), 1):
        lines.append(
            f"| {i} | {r.feature} | {fmt_num(r.dev_effect)} | {fmt_num(r.ref_effect)} | "
            f"{'YES' if r.direction_consistent else 'NO'} | {fmt_pct(r.dev_band_spread)} | {fmt_pct(r.ref_band_spread)} |"
        )

    top = RANK.head(6).feature.tolist()
    lines += ["", "## Frozen DEV quartile bands — top consistent features", "",
        "The same DEV-derived cuts are applied unchanged to REF.", ""
    ]
    for feature in top:
        c = CUTS[CUTS.feature == feature].iloc[0]
        lines += [
            f"### {feature}",
            f"DEV cuts: Q25={fmt_num(c.q25)}, Q50={fmt_num(c.q50)}, Q75={fmt_num(c.q75)}",
            "",
            "| Period | Band | N | EXTENDER | STOPPER | TP2 rate |",
            "|---|---|---:|---:|---:|---:|",
        ]
        q = BANDS[(BANDS.feature == feature) & (BANDS.band != "NA")]
        for r in q.itertuples(index=False):
            lines.append(
                f"| {r.period} | {r.band} | {r.n} | {r.extenders} | {r.stoppers} | {fmt_pct(r.tp2_rate)} |"
            )
        lines.append("")

    lines += [
        "## Interpretation boundary",
        "S15 is diagnostic only; no continuation rule is promoted here.",
        "A credible candidate for the next stage must show the same directional relationship in DEV and REF and retain enough sample size to matter.",
        "Any combined rule must be preregistered separately before testing economics."
    ]

    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text("BNB_B38_S15_PRE_TP1_JOURNEY_COMPLETE\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
