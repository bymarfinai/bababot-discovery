#!/usr/bin/env python3
"""Saturday T-Method S5.7D — Rejected-Hinge Excursion Monetization Atlas.

Research only; live BBC untouched. No new trade action is applied.

Frozen context from S5.7C:
    REJECTED_HINGE = upper wick of the first completed +0.50% hinge candle
                     is >= 50% of that candle's full range.

Critical causal convention:
- morphology is only known when the hinge candle has completed;
- therefore monetizable future excursion starts at the hinge decision time h05;
- the hinge candle's own intrabar high is NOT counted as post-signal opportunity.

Questions:
1) How much favorable excursion remains AFTER rejected/accepted morphology is known?
2) At natural existing geometry levels, what fraction reaches each level after h05?
3) Does the rejected-hinge excursion ceiling transfer discovery/validation and folds?
4) Is there a stable natural excursion zone worth a later, separately predeclared
   monetization action test?

No TP/partial-TP/exit simulation and no threshold optimization in this milestone.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s57c_hinge_rejection_robustness_management as c57

OUT = Path(os.getenv("S57D_OUT", "s57d_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
FOLD_EDGES = [0, 35, 70, 105, 139]

# Natural levels inherited from prior Saturday/T-method geometry and previously
# tested TP families. They are descriptive CDF points, not optimized targets.
LEVELS = [0.006, 0.008, 0.010, 0.013, 0.015, 0.020, 0.026]
HORIZONS_MIN = [30, 60, 120, 240, 360]


def fold_id(idx: int) -> int:
    for j in range(4):
        if FOLD_EDGES[j] <= idx < FOLD_EDGES[j + 1]:
            return j + 1
    raise RuntimeError(f"bad idx {idx}")


def post_hinge_path(k, tr, h05):
    """Only information/opportunity AFTER morphology is causally known."""
    exit_t = pd.Timestamp(tr.exit_t)
    bars = k[(k.index >= h05) & (k.index < exit_t)]
    decision_open = float(k.loc[h05, "open"]) if h05 in k.index else np.nan
    decision_progress = decision_open / tr.entry - 1 if np.isfinite(decision_open) else np.nan

    if len(bars):
        post_mfe_high = float(bars.high.max()) / tr.entry - 1
        post_max_close = float(bars.close.max()) / tr.entry - 1
        post_min_low = float(bars.low.min()) / tr.entry - 1
    else:
        post_mfe_high = decision_progress
        post_max_close = decision_progress
        post_min_low = decision_progress

    out = {
        "decision_progress": decision_progress,
        "post_mfe_high": post_mfe_high,
        "post_max_close": post_max_close,
        "post_min_low": post_min_low,
        "post_duration_min": max(0.0, (exit_t - h05).total_seconds() / 60.0),
    }

    # Causal future touches after h05. Same-bar high is allowed for bars that BEGIN
    # at/after h05 because morphology was known before those bars traded.
    for lv in LEVELS:
        key = f"reach_{int(round(lv*10000)):03d}bp"
        first = None
        for b in bars.itertuples(index=False):
            if float(b.high) / tr.entry - 1 >= lv:
                first = b.ts + pd.Timedelta(minutes=5)
                break
        out[key] = first is not None
        out[key + "_min"] = np.nan if first is None else (first - h05).total_seconds() / 60.0

    for hm in HORIZONS_MIN:
        end = min(exit_t, h05 + pd.Timedelta(minutes=hm))
        w = k[(k.index >= h05) & (k.index < end)]
        out[f"mfe_{hm}m"] = (float(w.high.max()) / tr.entry - 1) if len(w) else decision_progress
        out[f"maxclose_{hm}m"] = (float(w.close.max()) / tr.entry - 1) if len(w) else decision_progress

    return out


def base_metrics(g):
    if len(g) == 0:
        return {
            "n": 0, "parent_pnl": 0.0, "a719_pnl": 0.0,
            "parent_wr": np.nan, "a719_wr": np.nan,
            "post_mfe_median": np.nan, "post_mfe_mean": np.nan,
            "post_close_median": np.nan, "decision_progress_median": np.nan,
        }
    return {
        "n": int(len(g)),
        "parent_pnl": float(g.parent_pnl.sum()),
        "a719_pnl": float(g.a719_pnl.sum()),
        "parent_wr": float((g.parent_pnl > 0).mean()),
        "a719_wr": float((g.a719_pnl > 0).mean()),
        "post_mfe_median": float(g.post_mfe_high.median()),
        "post_mfe_mean": float(g.post_mfe_high.mean()),
        "post_close_median": float(g.post_max_close.median()),
        "decision_progress_median": float(g.decision_progress.median()),
    }


def reach_rows(df):
    rows = []
    periods = [
        ("full", df),
        ("discovery", df[df.idx < SPLIT]),
        ("validation", df[df.idx >= SPLIT]),
    ]
    for state, mask in [("REJECTED", df.rejected_hinge), ("ACCEPTED", ~df.rejected_hinge)]:
        for period, pg in periods:
            g = pg[mask.loc[pg.index]]
            for lv in LEVELS:
                k = f"reach_{int(round(lv*10000)):03d}bp"
                hit = g[g[k]]
                rows.append({
                    "state": state,
                    "period": period,
                    "level": lv,
                    "n": int(len(g)),
                    "reached_n": int(g[k].sum()) if len(g) else 0,
                    "reach_rate": float(g[k].mean()) if len(g) else np.nan,
                    "median_minutes_if_reached": float(hit[k + "_min"].median()) if len(hit) else np.nan,
                    "a719_pnl_all": float(g.a719_pnl.sum()) if len(g) else 0.0,
                })
    return rows


def horizon_rows(df):
    rows = []
    for state, mask in [("REJECTED", df.rejected_hinge), ("ACCEPTED", ~df.rejected_hinge)]:
        for period, pg in [("full", df), ("discovery", df[df.idx < SPLIT]), ("validation", df[df.idx >= SPLIT])]:
            g = pg[mask.loc[pg.index]]
            for hm in HORIZONS_MIN:
                rows.append({
                    "state": state,
                    "period": period,
                    "horizon_min": hm,
                    "n": int(len(g)),
                    "mfe_median": float(g[f"mfe_{hm}m"].median()) if len(g) else np.nan,
                    "maxclose_median": float(g[f"maxclose_{hm}m"].median()) if len(g) else np.nan,
                })
    return rows


def main():
    k = s50.load_klines()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    parent_all = float(sum(x.pnl for x in trades))
    if len(trades) != 139 or abs(parent_all - 87.199692) > 0.02:
        raise RuntimeError("parent parity fail")

    rows = []
    all_a719 = 0.0
    for idx, (t, tr) in enumerate(zip(entries, trades)):
        s240 = a50.state240(k, t, tr)
        a719 = float(a50.a719_pnl(k, f, t, tr, s240))
        all_a719 += a719
        h05, h08 = a52.first_hinges(k, t, tr)
        if h05 is None:
            continue

        candle_ts = h05 - pd.Timedelta(minutes=5)
        cm = c57.morph(k.loc[candle_ts])
        rejected = bool(np.isfinite(cm["upper_wick_ratio"]) and cm["upper_wick_ratio"] >= 0.50)
        p = post_hinge_path(k, tr, h05)
        rows.append({
            "idx": idx,
            "fold": fold_id(idx),
            "date": tr.date,
            "rejected_hinge": rejected,
            "deep_original": bool(h08 is not None),
            "hinge_time": str(h05),
            "parent_pnl": float(tr.pnl),
            "a719_pnl": a719,
            "a719_action": s240["state240"] == "SHALLOW_FAILURE",
            "hinge_body_ratio": cm["body_ratio"],
            "hinge_upper_wick_ratio": cm["upper_wick_ratio"],
            "hinge_close_location": cm["close_location"],
            **p,
        })

    if abs(all_a719 - 103.3830997612) > 0.02:
        raise RuntimeError("A7.19 parity fail")

    df = pd.DataFrame(rows).sort_values("idx").reset_index(drop=True)
    if len(df) != 89 or int(df.deep_original.sum()) != 61:
        raise RuntimeError("hinge/deep parity fail")
    rej = df[df.rejected_hinge]
    acc = df[~df.rejected_hinge]
    if len(rej) != 16 or int(rej.deep_original.sum()) != 7:
        raise RuntimeError("S5.7C rejected parity fail")

    df.to_csv(OUT / "s57d_hinge_excursion_rows.csv", index=False)

    groups = {}
    for label, g in [("REJECTED", rej), ("ACCEPTED", acc)]:
        groups[label] = {
            "full": base_metrics(g),
            "discovery": base_metrics(g[g.idx < SPLIT]),
            "validation": base_metrics(g[g.idx >= SPLIT]),
        }

    rr = reach_rows(df)
    pd.DataFrame(rr).to_csv(OUT / "s57d_reach_curve.csv", index=False)
    hr = horizon_rows(df)
    pd.DataFrame(hr).to_csv(OUT / "s57d_horizon_excursion.csv", index=False)

    # Four-fold post-hinge excursion comparison. This tests the ceiling hypothesis
    # without choosing any target from the same sample.
    fold_rows = []
    lower_mfe_folds = 0
    comparable_folds = 0
    for fold in range(1, 5):
        g = df[df.fold == fold]
        r, a = g[g.rejected_hinge], g[~g.rejected_hinge]
        rmed = float(r.post_mfe_high.median()) if len(r) else np.nan
        amed = float(a.post_mfe_high.median()) if len(a) else np.nan
        comparable = len(r) > 0 and len(a) > 0
        consistent = bool(comparable and rmed < amed)
        comparable_folds += int(comparable)
        lower_mfe_folds += int(consistent)
        fold_rows.append({
            "fold": fold,
            "rejected_n": int(len(r)),
            "accepted_n": int(len(a)),
            "rejected_post_mfe_median": rmed,
            "accepted_post_mfe_median": amed,
            "consistent_lower_rejected": consistent,
            "rejected_reach08": float(r.reach_080bp.mean()) if len(r) else np.nan,
            "accepted_reach08": float(a.reach_080bp.mean()) if len(a) else np.nan,
            "rejected_reach10": float(r.reach_100bp.mean()) if len(r) else np.nan,
            "accepted_reach10": float(a.reach_100bp.mean()) if len(a) else np.nan,
        })
    pd.DataFrame(fold_rows).to_csv(OUT / "s57d_chronology_folds.csv", index=False)

    # Stable descriptive candidate levels: no action. We only flag natural levels
    # that rejected trades reach >=60% in both D/V and that are less reachable than
    # the next natural level in both halves. This identifies a possible plateau for
    # a *future separately predeclared* test, not a target chosen for PnL.
    reach_df = pd.DataFrame(rr)
    plateau_candidates = []
    for j, lv in enumerate(LEVELS[:-1]):
        nxt = LEVELS[j + 1]
        def rate(period, level):
            x = reach_df[(reach_df.state == "REJECTED") & (reach_df.period == period) & (np.isclose(reach_df.level, level))]
            return float(x.iloc[0].reach_rate) if len(x) else np.nan
        d0, v0 = rate("discovery", lv), rate("validation", lv)
        d1, v1 = rate("discovery", nxt), rate("validation", nxt)
        if all(np.isfinite(x) for x in [d0, v0, d1, v1]) and d0 >= 0.60 and v0 >= 0.60 and d1 < d0 and v1 < v0:
            plateau_candidates.append({"level": lv, "next_level": nxt, "disc_reach": d0, "val_reach": v0,
                                       "disc_next": d1, "val_next": v1})

    # Ceiling robustness gate: rejected median future excursion lower in D and V,
    # plus at least 3/4 chronology folds. No trading action follows from this alone.
    ceiling_robust = bool(
        groups["REJECTED"]["discovery"]["post_mfe_median"] < groups["ACCEPTED"]["discovery"]["post_mfe_median"]
        and groups["REJECTED"]["validation"]["post_mfe_median"] < groups["ACCEPTED"]["validation"]["post_mfe_median"]
        and lower_mfe_folds >= 3
    )

    summary = {
        "parity": {
            "all_parent_pnl": parent_all,
            "all_a719_pnl": all_a719,
            "hinge_n": len(df),
            "rejected_n": len(rej),
            "accepted_n": len(acc),
        },
        "groups": groups,
        "reach_curve": rr,
        "horizon_excursion": hr,
        "folds": fold_rows,
        "lower_mfe_folds": lower_mfe_folds,
        "comparable_folds": comparable_folds,
        "ceiling_robustness_pass": ceiling_robust,
        "plateau_candidates_descriptive_only": plateau_candidates,
    }
    (OUT / "s57d_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x):
        return "NA" if not np.isfinite(x) else f"{100*x:.1f}%"
    def money(x):
        return f"${x:+.3f}"

    md = [
        "# BTC Temporal Saturday T-Method S5.7D — Rejected-Hinge Excursion Monetization Atlas",
        "",
        "**Status:** COMPLETE — FORENSIC ONLY; NO MONETIZATION ACTION APPLIED",
        "**Research only:** live BBC untouched",
        "",
        "## Causal convention",
        "Morphology is known only after the +0.50 hinge candle completes. All excursion in this atlas begins at `h05` (the next decision time). The hinge candle's own high is excluded from post-signal opportunity.",
        "",
        "## Frozen parity",
        f"- Parent all 139: **{money(parent_all)}**",
        f"- A7.19 all 139: **{money(all_a719)}**",
        f"- +0.50 hinge trades: **{len(df)}**",
        f"- Rejected exact S5.7C: **{len(rej)}**; accepted **{len(acc)}**",
        "",
        "## Post-hinge excursion summary",
    ]
    for state in ["REJECTED", "ACCEPTED"]:
        md.append(f"### {state}")
        for period in ["full", "discovery", "validation"]:
            m = groups[state][period]
            md.append(
                f"- {period}: N {m['n']} / post-MFE median {pct(m['post_mfe_median'])} / "
                f"max-close median {pct(m['post_close_median'])} / A7.19 {money(m['a719_pnl'])}"
            )
        md.append("")

    md += ["## Natural future-reach curve"]
    for lv in LEVELS:
        label = f"+{100*lv:.1f}%"
        vals = {}
        for state in ["REJECTED", "ACCEPTED"]:
            for period in ["full", "discovery", "validation"]:
                x = reach_df[(reach_df.state == state) & (reach_df.period == period) & (np.isclose(reach_df.level, lv))]
                vals[(state, period)] = x.iloc[0] if len(x) else None
        md.append(
            f"- {label}: rejected {pct(vals[('REJECTED','full')].reach_rate)} "
            f"(D {pct(vals[('REJECTED','discovery')].reach_rate)} / V {pct(vals[('REJECTED','validation')].reach_rate)}) vs "
            f"accepted {pct(vals[('ACCEPTED','full')].reach_rate)} "
            f"(D {pct(vals[('ACCEPTED','discovery')].reach_rate)} / V {pct(vals[('ACCEPTED','validation')].reach_rate)})"
        )

    md += ["", "## Four chronology folds"]
    for r in fold_rows:
        md.append(
            f"- Fold {r['fold']}: rejected N{r['rejected_n']} post-MFE median {pct(r['rejected_post_mfe_median'])} vs "
            f"accepted N{r['accepted_n']} {pct(r['accepted_post_mfe_median'])}; consistent={r['consistent_lower_rejected']}"
        )
    md += [
        f"- lower rejected excursion direction: **{lower_mfe_folds}/4 folds**",
        f"- ceiling robustness gate: **{'PASS' if ceiling_robust else 'FAIL'}**",
        "",
        "## Descriptive plateau candidates",
        f"- **{json.dumps(plateau_candidates)}**",
        "- These are NOT TP recommendations and no PnL was optimized at these levels.",
        "",
        "## Guardrail",
        "- No partial TP, fixed TP, cut, sizing, or A7.19 override is simulated here.",
        "- A later action test is eligible only if this atlas shows a chronology-stable post-signal excursion structure.",
    ]
    (OUT / "S5.7D_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
