#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import time
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import sol_full_character_long_v1 as fc1
import sol_structure_library_v1 as lib
import sol_reset_winner_first_v1 as wf1
import sol_structural_liquidity_discovery_v1 as v1

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_STRUCTURAL_LIQUIDITY_ANATOMY_V2"

DEV_YEARS = (2020, 2021, 2022)
CONF_YEARS = (2023, 2024)
ALL_YEARS = DEV_YEARS + CONF_YEARS

APPROACH_MAX_BARS = 6
APPROACH_MIN_BARS = 3
RANGE_LOOKBACK = 20
TOUCH_TOL_RANGE_UNITS = 0.10

CONT_FEATURES = (
    "liquidity_age_h1",
    "source_to_opposite_structure_range_units",
    "opposite_reference_age_h1",
    "same_bar_swept_level_count",
    "same_bar_swept_level_span_range_units",
    "approach_bars",
    "approach_efficiency",
    "approach_net_range_units",
    "approach_median_overlap",
    "approach_overlap_gt50_share",
    "approach_range_contraction_ratio",
    "approach_body_contraction_ratio",
    "approach_directional_close_share",
    "approach_max_directional_body_range_units",
    "approach_start_distance_to_level_range_units",
    "pre_sweep_touch_count",
    "sweep_depth_range_units",
    "sweep_range_units",
    "sweep_body_range_units",
    "sweep_rejection_wick_fraction",
    "sweep_close_inside_range_units",
    "sweep_close_location_reversal",
    "reclaim_delay_h1_bars",
    "reclaim_range_units",
    "reclaim_body_range_units",
    "reclaim_directional_body_range_units",
    "reclaim_close_inside_range_units",
    "reclaim_close_location_reversal",
)

BINARY_FEATURES = ("near_equal_prior_same_side",)
ALL_FEATURES = CONT_FEATURES + BINARY_FEATURES

POSITIVE = "STRUCTURAL_LIQUIDITY_EVENT"
NEGATIVES = ("RECLAIM_FAILED_BEFORE_BOS", "RECLAIM_NO_BOS_WITHIN_WINDOW")


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


def prior_median_range(hi, lo, end_i: int):
    a = max(0, end_i - RANGE_LOOKBACK)
    z = hi[a:end_i] - lo[a:end_i]
    if len(z) < RANGE_LOOKBACK:
        return np.nan
    m = float(np.nanmedian(z))
    return m if np.isfinite(m) and m > 0 else np.nan


def overlap_ratio(ph, pl, ch, cl):
    den = min(ph - pl, ch - cl)
    if not np.isfinite(den) or den <= 0:
        return np.nan
    ov = max(0.0, min(ph, ch) - max(pl, cl))
    return float(np.clip(ov / den, 0.0, 1.0))


def build_same_side_prior_map(h1: pd.DataFrame):
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    _, _, lows, highs = v1.pivot_lists(hi, lo)

    prior_high = {}
    for i, h in enumerate(highs):
        prior_high[int(h["pivot_i"])] = highs[i - 1] if i > 0 else None

    prior_low = {}
    for i, l in enumerate(lows):
        prior_low[int(l["pivot_i"])] = lows[i - 1] if i > 0 else None

    return prior_high, prior_low


def dedup_physical_events(sweeps: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    x = sweeps[
        (sweeps.family == "H1_SWING")
        & sweeps.outcome.isin((POSITIVE,) + NEGATIVES)
        & (pd.to_numeric(sweeps.reclaim_i_h1, errors="coerce") >= 0)
        & (pd.to_numeric(sweeps.significant_opposite_pivot_i, errors="coerce") >= 0)
    ].copy()

    if x.empty:
        raise RuntimeError("no eligible reclaimed H1 swing sweeps")

    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()

    group_cols = ["side", "sweep_i_h1", "reclaim_i_h1"]
    counts = x.groupby(group_cols, dropna=False).size().rename("same_bar_swept_level_count")
    spans = {}
    for key, g in x.groupby(group_cols, dropna=False):
        sweep_i = int(g.sweep_i_h1.iloc[0])
        m = prior_median_range(hi, lo, sweep_i)
        span = float(g.level.max() - g.level.min())
        spans[key] = float(span / m) if np.isfinite(m) and m > 0 else np.nan

    x = x.merge(counts.reset_index(), on=group_cols, how="left")
    x["_span_key"] = list(zip(x.side, x.sweep_i_h1, x.reclaim_i_h1))
    x["same_bar_swept_level_span_range_units"] = x["_span_key"].map(spans)
    x = x.drop(columns=["_span_key"])

    x = x.sort_values(
        ["side", "sweep_i_h1", "reclaim_i_h1", "activation_i_h1", "source_pivot_i", "candidate_id"],
        ascending=[True, True, True, False, False, True],
    )
    x = x.drop_duplicates(group_cols, keep="first").reset_index(drop=True)
    x["event_label"] = (x.outcome == POSITIVE).astype(int)
    return x


def extract_features(events: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    idx = h1.index
    op = h1.open.astype(float).to_numpy()
    hi = h1.high.astype(float).to_numpy()
    lo = h1.low.astype(float).to_numpy()
    cl = h1.close.astype(float).to_numpy()

    prior_high_map, prior_low_map = build_same_side_prior_map(h1)

    rows = []

    for _, r in events.iterrows():
        side = str(r.side)
        sweep_i = int(r.sweep_i_h1)
        reclaim_i = int(r.reclaim_i_h1)
        activation_i = int(r.activation_i_h1)
        source_pivot_i = int(r.source_pivot_i)
        sig_confirm_i = int(r.significant_opposite_confirm_i)
        level = float(r.level)
        sig_level = float(r.significant_opposite_level)

        m = prior_median_range(hi, lo, sweep_i)
        out = r.to_dict()

        out["liquidity_age_h1"] = float(sweep_i - activation_i)
        out["opposite_reference_age_h1"] = float(sweep_i - sig_confirm_i)

        if np.isfinite(m) and m > 0:
            if side == "BUY_SIDE":
                dist = level - sig_level
            else:
                dist = sig_level - level
            out["source_to_opposite_structure_range_units"] = float(dist / m)
        else:
            out["source_to_opposite_structure_range_units"] = np.nan

        prior_same = prior_high_map.get(source_pivot_i) if side == "BUY_SIDE" else prior_low_map.get(source_pivot_i)
        near_equal = 0
        if prior_same is not None and np.isfinite(m) and m > 0:
            pivot_gap = source_pivot_i - int(prior_same["pivot_i"])
            price_diff = abs(level - float(prior_same["price"]))
            if pivot_gap <= 72 and price_diff <= 0.25 * m:
                near_equal = 1
        out["near_equal_prior_same_side"] = int(near_equal)

        # Approach: up to final 6 completed H1 bars immediately before sweep.
        approach_start = max(activation_i, sweep_i - APPROACH_MAX_BARS)
        approach_end = sweep_i
        n = approach_end - approach_start
        out["approach_bars"] = float(n)

        if n >= APPROACH_MIN_BARS and np.isfinite(m) and m > 0:
            aop = op[approach_start:approach_end]
            ahi = hi[approach_start:approach_end]
            alo = lo[approach_start:approach_end]
            acl = cl[approach_start:approach_end]

            direction = 1.0 if side == "BUY_SIDE" else -1.0
            diffs = np.diff(acl)
            path = float(np.nansum(np.abs(diffs)))
            net = float(direction * (acl[-1] - acl[0]))
            out["approach_efficiency"] = float(net / path) if path > 0 else np.nan
            out["approach_net_range_units"] = float(net / m)

            ovs = []
            for j in range(1, n):
                ovs.append(overlap_ratio(ahi[j-1], alo[j-1], ahi[j], alo[j]))
            ovs = np.array(ovs, dtype=float)
            valid = ovs[np.isfinite(ovs)]
            out["approach_median_overlap"] = float(np.nanmedian(valid)) if len(valid) else np.nan
            out["approach_overlap_gt50_share"] = float(np.mean(valid >= .50)) if len(valid) else np.nan

            half = max(1, n // 2)
            ranges = ahi - alo
            bodies = np.abs(acl - aop)
            first_r = float(np.nanmedian(ranges[:half]))
            last_r = float(np.nanmedian(ranges[-half:]))
            first_b = float(np.nanmedian(bodies[:half]))
            last_b = float(np.nanmedian(bodies[-half:]))

            out["approach_range_contraction_ratio"] = float(last_r / first_r) if first_r > 0 else np.nan
            out["approach_body_contraction_ratio"] = float(last_b / first_b) if first_b > 0 else np.nan

            if side == "BUY_SIDE":
                directional = acl > aop
                directional_bodies = np.maximum(acl - aop, 0.0)
                start_dist = level - float(acl[0])
            else:
                directional = acl < aop
                directional_bodies = np.maximum(aop - acl, 0.0)
                start_dist = float(acl[0]) - level

            out["approach_directional_close_share"] = float(np.mean(directional))
            out["approach_max_directional_body_range_units"] = float(np.nanmax(directional_bodies) / m)
            out["approach_start_distance_to_level_range_units"] = float(start_dist / m)
        else:
            for f in (
                "approach_efficiency",
                "approach_net_range_units",
                "approach_median_overlap",
                "approach_overlap_gt50_share",
                "approach_range_contraction_ratio",
                "approach_body_contraction_ratio",
                "approach_directional_close_share",
                "approach_max_directional_body_range_units",
                "approach_start_distance_to_level_range_units",
            ):
                out[f] = np.nan

        if np.isfinite(m) and m > 0:
            tol = TOUCH_TOL_RANGE_UNITS * m
            touches = 0
            for j in range(max(activation_i, 0), sweep_i):
                if side == "BUY_SIDE":
                    if hi[j] <= level and hi[j] >= level - tol:
                        touches += 1
                else:
                    if lo[j] >= level and lo[j] <= level + tol:
                        touches += 1
            out["pre_sweep_touch_count"] = float(touches)
        else:
            out["pre_sweep_touch_count"] = np.nan

        # Sweep geometry.
        sr = float(hi[sweep_i] - lo[sweep_i])
        sb = float(abs(cl[sweep_i] - op[sweep_i]))
        out["sweep_range_units"] = float(sr / m) if np.isfinite(m) and m > 0 else np.nan
        out["sweep_body_range_units"] = float(sb / m) if np.isfinite(m) and m > 0 else np.nan

        if sr > 0:
            if side == "BUY_SIDE":
                wick = hi[sweep_i] - max(op[sweep_i], cl[sweep_i])
                close_loc = (hi[sweep_i] - cl[sweep_i]) / sr
            else:
                wick = min(op[sweep_i], cl[sweep_i]) - lo[sweep_i]
                close_loc = (cl[sweep_i] - lo[sweep_i]) / sr
            out["sweep_rejection_wick_fraction"] = float(max(0.0, wick) / sr)
            out["sweep_close_location_reversal"] = float(close_loc)
        else:
            out["sweep_rejection_wick_fraction"] = np.nan
            out["sweep_close_location_reversal"] = np.nan

        if np.isfinite(m) and m > 0:
            if side == "BUY_SIDE":
                out["sweep_close_inside_range_units"] = float((level - cl[sweep_i]) / m)
            else:
                out["sweep_close_inside_range_units"] = float((cl[sweep_i] - level) / m)
        else:
            out["sweep_close_inside_range_units"] = np.nan

        # Reclaim geometry.
        rr = float(hi[reclaim_i] - lo[reclaim_i])
        rb = float(abs(cl[reclaim_i] - op[reclaim_i]))
        out["reclaim_range_units"] = float(rr / m) if np.isfinite(m) and m > 0 else np.nan
        out["reclaim_body_range_units"] = float(rb / m) if np.isfinite(m) and m > 0 else np.nan

        if side == "BUY_SIDE":
            directional_body = max(float(op[reclaim_i] - cl[reclaim_i]), 0.0)
            inside = level - float(cl[reclaim_i])
            loc = (hi[reclaim_i] - cl[reclaim_i]) / rr if rr > 0 else np.nan
        else:
            directional_body = max(float(cl[reclaim_i] - op[reclaim_i]), 0.0)
            inside = float(cl[reclaim_i]) - level
            loc = (cl[reclaim_i] - lo[reclaim_i]) / rr if rr > 0 else np.nan

        out["reclaim_directional_body_range_units"] = float(directional_body / m) if np.isfinite(m) and m > 0 else np.nan
        out["reclaim_close_inside_range_units"] = float(inside / m) if np.isfinite(m) and m > 0 else np.nan
        out["reclaim_close_location_reversal"] = float(loc) if np.isfinite(loc) else np.nan

        out["sweep_year"] = int(r.sweep_year)
        rows.append(out)

    return pd.DataFrame(rows)


def median_direction_ok(g: pd.DataFrame, feature: str, direction: str):
    z = g[[feature, "event_label"]].copy()
    z[feature] = pd.to_numeric(z[feature], errors="coerce")
    z = z.dropna()
    pos = z[z.event_label == 1][feature]
    neg = z[z.event_label == 0][feature]
    if len(pos) == 0 or len(neg) == 0:
        return False, np.nan, np.nan
    pm = float(pos.median())
    nm = float(neg.median())
    ok = pm > nm if direction == "HIGHER" else pm < nm
    return bool(ok), pm, nm


def feature_summary(features: pd.DataFrame):
    rows = []
    for feature in ALL_FEATURES:
        for label_name, label_value in (("EVENT", 1), ("FAILURE", 0)):
            s = pd.to_numeric(
                features.loc[features.event_label == label_value, feature], errors="coerce"
            ).replace([np.inf, -np.inf], np.nan).dropna()
            rows.append({
                "feature": feature,
                "group": label_name,
                "n": len(s),
                "median": float(s.median()) if len(s) else np.nan,
                "p25": float(s.quantile(.25)) if len(s) else np.nan,
                "p75": float(s.quantile(.75)) if len(s) else np.nan,
            })
    return pd.DataFrame(rows)


def development_audit(features: pd.DataFrame):
    dev = features[features.sweep_year.isin(DEV_YEARS)].copy()
    rows = []
    yearly_rows = []

    for feature in ALL_FEATURES:
        z = dev[[feature, "event_label", "sweep_year"]].copy()
        z[feature] = pd.to_numeric(z[feature], errors="coerce")
        z = z.replace([np.inf, -np.inf], np.nan).dropna(subset=[feature])

        binary = feature in BINARY_FEATURES
        direction = "HIGHER"

        if len(z) == 0 or z.event_label.nunique() < 2:
            rows.append({
                "feature": feature, "binary": binary, "n": len(z),
                "direction": direction, "auc_oriented": np.nan,
                "threshold": np.nan, "baseline_rate": np.nan,
                "favorable_n": 0, "favorable_rate": np.nan,
                "lift": np.nan, "years_direction_ok": 0,
                "development_candidate": False,
            })
            continue

        pos_med = float(z.loc[z.event_label == 1, feature].median())
        neg_med = float(z.loc[z.event_label == 0, feature].median())

        if binary:
            direction = "HIGHER"
            threshold = 1.0
            score = z[feature].astype(float).to_numpy()
            fav = z[feature] == 1
        else:
            direction = "HIGHER" if pos_med > neg_med else "LOWER"
            raw = z[feature].astype(float)
            score = raw.to_numpy() if direction == "HIGHER" else (-raw).to_numpy()
            threshold = float(raw.quantile(.75 if direction == "HIGHER" else .25))
            fav = raw >= threshold if direction == "HIGHER" else raw <= threshold

        auc = float(roc_auc_score(z.event_label.astype(int), score))
        baseline = float(z.event_label.mean())
        fav_n = int(fav.sum())
        fav_rate = float(z.loc[fav, "event_label"].mean()) if fav_n else np.nan
        lift = fav_rate - baseline if np.isfinite(fav_rate) else np.nan

        years_ok = 0
        for year in DEV_YEARS:
            gy = z[z.sweep_year == year].copy()
            ok, pm, nm = median_direction_ok(gy, feature, direction)
            years_ok += int(ok)
            yearly_rows.append({
                "phase": "DEVELOPMENT",
                "feature": feature,
                "year": year,
                "direction": direction,
                "event_median": pm,
                "failure_median": nm,
                "direction_ok": ok,
            })

        candidate = bool(
            len(z) >= 500
            and auc >= .56
            and np.isfinite(lift) and lift >= .08
            and years_ok >= 2
            and fav_n >= 100
        )

        rows.append({
            "feature": feature,
            "binary": binary,
            "n": len(z),
            "event_median": pos_med,
            "failure_median": neg_med,
            "direction": direction,
            "auc_oriented": auc,
            "threshold": threshold,
            "baseline_rate": baseline,
            "favorable_n": fav_n,
            "favorable_rate": fav_rate,
            "lift": lift,
            "years_direction_ok": years_ok,
            "development_candidate": candidate,
        })

    return pd.DataFrame(rows), pd.DataFrame(yearly_rows)


def confirmation_audit(features: pd.DataFrame, dev_audit: pd.DataFrame, yearly_dev: pd.DataFrame):
    conf = features[features.sweep_year.isin(CONF_YEARS)].copy()
    rows = []
    yearly_rows = []

    for _, d in dev_audit[dev_audit.development_candidate].iterrows():
        feature = str(d.feature)
        binary = bool(d.binary)
        direction = str(d.direction)
        threshold = float(d.threshold)

        z = conf[[feature, "event_label", "sweep_year"]].copy()
        z[feature] = pd.to_numeric(z[feature], errors="coerce")
        z = z.replace([np.inf, -np.inf], np.nan).dropna(subset=[feature])

        if len(z) == 0 or z.event_label.nunique() < 2:
            continue

        raw = z[feature].astype(float)
        score = raw.to_numpy() if direction == "HIGHER" else (-raw).to_numpy()
        auc = float(roc_auc_score(z.event_label.astype(int), score))

        if binary:
            fav = raw == 1
        else:
            fav = raw >= threshold if direction == "HIGHER" else raw <= threshold

        baseline = float(z.event_label.mean())
        fav_n = int(fav.sum())
        fav_rate = float(z.loc[fav, "event_label"].mean()) if fav_n else np.nan
        lift = fav_rate - baseline if np.isfinite(fav_rate) else np.nan

        year_passes = {}
        for year in CONF_YEARS:
            gy = z[z.sweep_year == year].copy()
            ok, pm, nm = median_direction_ok(gy, feature, direction)
            year_passes[year] = ok
            yearly_rows.append({
                "phase": "CONFIRMATION",
                "feature": feature,
                "year": year,
                "direction": direction,
                "event_median": pm,
                "failure_median": nm,
                "direction_ok": ok,
            })

        gates = {
            "confirmation_n_ge_300": len(z) >= 300,
            "auc_ge_0_55": auc >= .55,
            "favorable_n_ge_100": fav_n >= 100,
            "favorable_lift_ge_5pp": bool(np.isfinite(lift) and lift >= .05),
            "year_2023_direction_ok": year_passes.get(2023, False),
            "year_2024_direction_ok": year_passes.get(2024, False),
        }
        confirmed = all(gates.values())

        rows.append({
            "feature": feature,
            "binary": binary,
            "direction": direction,
            "threshold_frozen_from_dev": threshold,
            "confirmation_n": len(z),
            "auc_oriented": auc,
            "baseline_rate": baseline,
            "favorable_n": fav_n,
            "favorable_rate": fav_rate,
            "lift": lift,
            **{f"gate_{k}": v for k, v in gates.items()},
            "confirmed_anatomy_feature": confirmed,
        })

    yearly = pd.concat([yearly_dev, pd.DataFrame(yearly_rows)], ignore_index=True)
    return pd.DataFrame(rows), yearly


def main():
    x5, coverage = load5_with_retry("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    h1 = fc1.build_h1(x5)
    candidates0 = v1.generate_candidates(h1)
    _, sweeps = v1.label_candidates(h1, candidates0)

    events = dedup_physical_events(sweeps, h1)
    features = extract_features(events, h1)

    # Ensure only 2020-2024.
    features = features[features.sweep_year.isin(ALL_YEARS)].copy().reset_index(drop=True)

    summary = feature_summary(features)
    dev_audit, yearly_dev = development_audit(features)
    conf_audit, yearly = confirmation_audit(features, dev_audit, yearly_dev)

    confirmed = (
        conf_audit[conf_audit.confirmed_anatomy_feature].copy()
        if len(conf_audit)
        else pd.DataFrame()
    )

    events.to_csv(ROOT / f"{PFX}_PhysicalEvents.csv", index=False)
    features.to_csv(ROOT / f"{PFX}_Features.csv", index=False)
    summary.to_csv(ROOT / f"{PFX}_FeatureSummary.csv", index=False)
    dev_audit.to_csv(ROOT / f"{PFX}_DevelopmentAudit.csv", index=False)
    conf_audit.to_csv(ROOT / f"{PFX}_ConfirmationAudit.csv", index=False)
    yearly.to_csv(ROOT / f"{PFX}_YearDirection.csv", index=False)
    confirmed.to_csv(ROOT / f"{PFX}_ConfirmedFeatures.csv", index=False)

    dev = features[features.sweep_year.isin(DEV_YEARS)]
    conf = features[features.sweep_year.isin(CONF_YEARS)]

    dev_rate = float(dev.event_label.mean()) if len(dev) else np.nan
    conf_rate = float(conf.event_label.mean()) if len(conf) else np.nan

    status = (
        "CONFIRMED_FEATURES="
        + (",".join(confirmed.feature.tolist()) if len(confirmed) else "NONE")
    )

    def pct(v):
        return "n/a" if pd.isna(v) or not np.isfinite(v) else f"{float(v)*100:.2f}%"

    lines = [
        "# SOL Structural Liquidity Anatomy V2 — Result",
        "",
        f"- 5m coverage: **{coverage*100:.6f}%**",
        f"- Reclaimed H1-swing physical events after dedup: **{len(features):,}**",
        f"- Development 2020-2022: N={len(dev):,}, structural-event rate={pct(dev_rate)}",
        f"- Frozen confirmation 2023-2024: N={len(conf):,}, structural-event rate={pct(conf_rate)}",
        "- Decision point: reclaim close; BOS not yet required.",
        "- No entry, TP, SL, PnL, session, or indicator filter.",
        "- 2025+ CLOSED.",
        "",
        "## Development anatomy candidates",
        "",
        "| Feature | Direction | N | AUC | Frozen threshold | Fav N | Baseline | Fav rate | Lift | Years direction | Candidate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, r in dev_audit.sort_values(["development_candidate", "auc_oriented"], ascending=[False, False]).iterrows():
        thr = "1" if bool(r.binary) else (f"{float(r.threshold):.6g}" if np.isfinite(r.threshold) else "n/a")
        lift = f"{float(r.lift)*100:.2f} pp" if np.isfinite(r.lift) else "n/a"
        lines.append(
            f"| {r.feature} | {r.direction} | {int(r.n)} | "
            f"{float(r.auc_oriented):.3f} | {thr} | {int(r.favorable_n)} | "
            f"{pct(r.baseline_rate)} | {pct(r.favorable_rate)} | {lift} | "
            f"{int(r.years_direction_ok)}/3 | {'YES' if bool(r.development_candidate) else 'NO'} |"
        )

    lines += [
        "",
        "## Frozen confirmation of development candidates",
        "",
    ]

    if len(conf_audit):
        lines += [
            "| Feature | Direction | N | AUC | Fav N | Baseline | Fav rate | Lift | 2023 | 2024 | Confirmed |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
        for _, r in conf_audit.sort_values(["confirmed_anatomy_feature", "auc_oriented"], ascending=[False, False]).iterrows():
            lift = f"{float(r.lift)*100:.2f} pp" if np.isfinite(r.lift) else "n/a"
            lines.append(
                f"| {r.feature} | {r.direction} | {int(r.confirmation_n)} | {float(r.auc_oriented):.3f} | "
                f"{int(r.favorable_n)} | {pct(r.baseline_rate)} | {pct(r.favorable_rate)} | {lift} | "
                f"{'PASS' if bool(r.gate_year_2023_direction_ok) else 'FAIL'} | "
                f"{'PASS' if bool(r.gate_year_2024_direction_ok) else 'FAIL'} | "
                f"{'YES' if bool(r.confirmed_anatomy_feature) else 'NO'} |"
            )
    else:
        lines.append("No development feature met the frozen anatomy-candidate gates, so no confirmation feature was tested.")

    lines += [
        "",
        "## Verdict",
        "",
        status,
        "",
        (
            "**CONFIRMED_LIQUIDITY_ANATOMY_FEATURE(S) FOUND.**"
            if len(confirmed)
            else "**NO_CONFIRMED_ANATOMY_FEATURE.**"
        ),
        "",
        "A confirmed feature means the characteristic is observable by reclaim close and repeatedly enriches the later frozen structural-consequence label. It is not yet a complete trading detector or entry rule.",
        "",
        "2025_PLUS=CLOSED",
    ]

    text = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n2025_PLUS=CLOSED\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
