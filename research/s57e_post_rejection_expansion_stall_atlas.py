#!/usr/bin/env python3
"""Saturday T-Method S5.7E — Post-Rejection Expansion vs Stall Atlas.

Research only; live BBC untouched. No new trade action is applied.

Frozen cohort/context:
    REJECTED_HINGE = upper wick of first completed +0.50% hinge candle >=50% range.

Frozen outcome landmark:
    post-signal EXPANDER = reaches +0.80% AFTER rejected morphology is knowable.
    STALLED = does not reach +0.80% after morphology is knowable.

Causal predictor snapshots are fixed at +15m, +30m, +60m after h05. At each
snapshot, the predictive atlas only evaluates trades that are still alive and have
NOT already reached +0.80%. The target is whether +0.80% is reached in the future
AFTER that snapshot. This prevents already-achieved expansion from leaking into a
confirmation rule.

No threshold sweep, no exit/TP/partial-TP simulation, no A7.19 override.
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
import s52d_pre_warning_latent_runner_immunity_atlas as d52
import s57c_hinge_rejection_robustness_management as c57
import s57d_rejected_hinge_excursion_monetization_atlas as d57

OUT = Path(os.getenv("S57E_OUT", "s57e_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
SNAPSHOTS = [15, 30, 60]
TARGET = 0.008

# Fixed binary confirmation hypotheses. Expected direction is declared before run.
BINARY_EXPECTED = {
    "reclaim_body_top": "HIGH",
    "reclaim_hinge_high": "HIGH",
    "ema7_two_closes": "HIGH",
    "ema20_two_closes": "HIGH",
    "recent_taker_pos": "HIGH",
    "higher_low_recent": "HIGH",
    "last_bull_top_q": "HIGH",
    "last_upper_wick_dom": "LOW",
}

CONT_FEATURES = [
    "decision_progress", "max_high_progress", "max_close_progress",
    "min_close_progress", "min_low_progress", "close_vs_hinge_high",
    "close_vs_body_top", "recovery_from_low", "ema7_dist", "ema20_dist",
    "ema7_slope15", "ema20_slope15", "recent15_taker", "cum_taker",
    "pos_taker_frac", "last_body_ratio", "last_upper_wick_ratio",
    "last_lower_wick_ratio", "last_close_location", "recent_low_vs_early_low",
    "range_ratio_recent_vs_early",
]


def rank_auc(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=bool)
    m = np.isfinite(x)
    x, y = x[m], y[m]
    if y.sum() == 0 or (~y).sum() == 0:
        return np.nan
    r = pd.Series(x).rank(method="average").to_numpy()
    n1, n0 = int(y.sum()), int((~y).sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def slope(k, bar_t, col, minutes=15):
    old_t = bar_t - pd.Timedelta(minutes=minutes)
    if old_t not in k.index or bar_t not in k.index:
        return np.nan
    old, cur = float(k.loc[old_t, col]), float(k.loc[bar_t, col])
    return cur / old - 1 if old else np.nan


def snapshot_features(k, tr, h05, hinge_row, minutes):
    snap = h05 + pd.Timedelta(minutes=minutes)
    exit_t = pd.Timestamp(tr.exit_t)
    alive = bool(exit_t > snap and snap in k.index)

    completed = k[(k.index >= h05) & (k.index < snap)]
    future = k[(k.index >= snap) & (k.index < exit_t)] if alive else k.iloc[0:0]
    prior_expand = bool(len(completed) and (completed.high / tr.entry - 1 >= TARGET).any())
    future_expand = bool(len(future) and (future.high / tr.entry - 1 >= TARGET).any())
    unresolved = bool(alive and not prior_expand)

    base = {
        "snapshot_min": minutes,
        "snapshot_t": str(snap),
        "alive": alive,
        "already_expanded08": prior_expand,
        "unresolved": unresolved,
        "future_expand08": future_expand if unresolved else False,
    }
    if not unresolved or len(completed) == 0:
        return base

    last_t = snap - pd.Timedelta(minutes=5)
    last = k.loc[last_t]
    decision_open = float(k.loc[snap, "open"])
    body_top = max(float(hinge_row.open), float(hinge_row.close))
    hinge_high = float(hinge_row.high)

    recent3 = completed.tail(3)
    early3 = completed.head(3)
    last_m = c57.morph(last)
    closes = completed.close.to_numpy(dtype=float)

    max_high = float(completed.high.max())
    max_close = float(completed.close.max())
    min_close = float(completed.close.min())
    min_low = float(completed.low.min())

    recent_low = float(recent3.low.min()) if len(recent3) else np.nan
    early_low = float(early3.low.min()) if len(early3) else np.nan
    recent_range = float((recent3.high - recent3.low).mean()) if len(recent3) else np.nan
    early_range = float((early3.high - early3.low).mean()) if len(early3) else np.nan

    two = completed.tail(2)
    ema7_two = bool(len(two) == 2 and (two.close > two.ema7).all())
    ema20_two = bool(len(two) == 2 and (two.close > two.ema20).all())

    recent_taker = float(np.nanmean(recent3.taker_imb.to_numpy(dtype=float))) if len(recent3) else np.nan
    cum_taker = float(np.nanmean(completed.taker_imb.to_numpy(dtype=float))) if len(completed) else np.nan
    posfrac = float((completed.taker_imb > 0).mean()) if len(completed) else np.nan

    base.update({
        "decision_progress": decision_open / tr.entry - 1,
        "max_high_progress": max_high / tr.entry - 1,
        "max_close_progress": max_close / tr.entry - 1,
        "min_close_progress": min_close / tr.entry - 1,
        "min_low_progress": min_low / tr.entry - 1,
        "close_vs_hinge_high": float(last.close) / hinge_high - 1,
        "close_vs_body_top": float(last.close) / body_top - 1,
        "recovery_from_low": float(last.close) / min_low - 1,
        "ema7_dist": float(last.close) / float(last.ema7) - 1,
        "ema20_dist": float(last.close) / float(last.ema20) - 1,
        "ema7_slope15": slope(k, last_t, "ema7", 15),
        "ema20_slope15": slope(k, last_t, "ema20", 15),
        "recent15_taker": recent_taker,
        "cum_taker": cum_taker,
        "pos_taker_frac": posfrac,
        "last_body_ratio": last_m["body_ratio"],
        "last_upper_wick_ratio": last_m["upper_wick_ratio"],
        "last_lower_wick_ratio": last_m["lower_wick_ratio"],
        "last_close_location": last_m["close_location"],
        "recent_low_vs_early_low": (recent_low / early_low - 1) if np.isfinite(recent_low) and np.isfinite(early_low) and early_low else np.nan,
        "range_ratio_recent_vs_early": (recent_range / early_range) if np.isfinite(recent_range) and np.isfinite(early_range) and early_range else np.nan,
        "reclaim_body_top": bool((completed.close >= body_top).any()),
        "reclaim_hinge_high": bool((completed.close >= hinge_high).any()),
        "ema7_two_closes": ema7_two,
        "ema20_two_closes": ema20_two,
        "recent_taker_pos": bool(np.isfinite(recent_taker) and recent_taker > 0),
        "higher_low_recent": bool(np.isfinite(recent_low) and np.isfinite(early_low) and recent_low > early_low),
        "last_bull_top_q": bool(float(last.close) > float(last.open) and np.isfinite(last_m["close_location"]) and last_m["close_location"] >= 0.75),
        "last_upper_wick_dom": bool(np.isfinite(last_m["upper_wick_ratio"]) and last_m["upper_wick_ratio"] >= 0.50),
    })
    return base


def cont_comp(g, feat, period, minutes):
    ex = g[g.future_expand08]
    st = g[~g.future_expand08]
    em = float(ex[feat].median()) if len(ex) and ex[feat].notna().any() else np.nan
    sm = float(st[feat].median()) if len(st) and st[feat].notna().any() else np.nan
    auc = rank_auc(g[feat].to_numpy(), g.future_expand08.to_numpy())
    direction = "EXPAND_HIGH" if np.isfinite(em) and np.isfinite(sm) and em > sm else ("EXPAND_LOW" if np.isfinite(em) and np.isfinite(sm) and em < sm else "TIE")
    return {
        "snapshot_min": minutes, "period": period, "feature": feat,
        "n": int(len(g)), "expand_n": int(g.future_expand08.sum()),
        "stall_n": int((~g.future_expand08).sum()),
        "expand_median": em, "stall_median": sm,
        "auc_expand_high": auc, "direction": direction,
    }


def binary_row(g, signal, period, minutes):
    yes = g[g[signal]]
    no = g[~g[signal]]
    yr = float(yes.future_expand08.mean()) if len(yes) else np.nan
    nr = float(no.future_expand08.mean()) if len(no) else np.nan
    exp = BINARY_EXPECTED[signal]
    effect = yr - nr if np.isfinite(yr) and np.isfinite(nr) else np.nan
    expected_ok = bool(np.isfinite(effect) and ((exp == "HIGH" and effect > 0) or (exp == "LOW" and effect < 0)))
    return {
        "snapshot_min": minutes, "period": period, "signal": signal,
        "expected": exp, "n": int(len(g)), "yes_n": int(len(yes)),
        "no_n": int(len(no)), "yes_expand_rate": yr, "no_expand_rate": nr,
        "effect_yes_minus_no": effect, "expected_direction_ok": expected_ok,
    }


def main():
    k = s50.load_klines()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    parent_all = float(sum(x.pnl for x in trades))
    if len(trades) != 139 or abs(parent_all - 87.199692) > 0.02:
        raise RuntimeError("parent parity fail")

    rejected = []
    all_a719 = 0.0
    for idx, (t, tr) in enumerate(zip(entries, trades)):
        s240 = a50.state240(k, t, tr)
        a719 = float(a50.a719_pnl(k, f, t, tr, s240))
        all_a719 += a719
        h05, _ = a52.first_hinges(k, t, tr)
        if h05 is None:
            continue
        hinge_ts = h05 - pd.Timedelta(minutes=5)
        hinge = k.loc[hinge_ts]
        cm = c57.morph(hinge)
        is_rejected = bool(np.isfinite(cm["upper_wick_ratio"]) and cm["upper_wick_ratio"] >= 0.50)
        if not is_rejected:
            continue
        post = d57.post_hinge_path(k, tr, h05)
        rejected.append({
            "idx": idx, "date": tr.date, "entry_t": str(t), "h05": h05,
            "hinge_ts": hinge_ts, "parent_pnl": float(tr.pnl), "a719_pnl": a719,
            "post_expand08": bool(post["reach_080bp"]),
            "post_mfe_high": float(post["post_mfe_high"]),
            "post_max_close": float(post["post_max_close"]),
        })

    if abs(all_a719 - 103.3830997612) > 0.02:
        raise RuntimeError("A7.19 parity fail")
    base = pd.DataFrame(rejected).sort_values("idx").reset_index(drop=True)
    if len(base) != 16 or int(base.post_expand08.sum()) != 7:
        raise RuntimeError(f"S5.7D rejected/expander parity fail: {len(base)} / {int(base.post_expand08.sum())}")

    base_out = base.drop(columns=["h05", "hinge_ts"]).copy()
    base_out.to_csv(OUT / "s57e_rejected_outcomes.csv", index=False)

    rows = []
    for r in rejected:
        idx = int(r["idx"])
        t = entries[idx]
        tr = trades[idx]
        h05 = pd.Timestamp(r["h05"])
        hinge = k.loc[pd.Timestamp(r["hinge_ts"])]
        for hm in SNAPSHOTS:
            feat = snapshot_features(k, tr, h05, hinge, hm)
            rows.append({
                "idx": idx, "date": r["date"], "snapshot_min": hm,
                "overall_post_expand08": bool(r["post_expand08"]),
                "parent_pnl": r["parent_pnl"], "a719_pnl": r["a719_pnl"],
                **feat,
            })
    snap = pd.DataFrame(rows).sort_values(["snapshot_min", "idx"]).reset_index(drop=True)
    snap.to_csv(OUT / "s57e_snapshot_features.csv", index=False)

    status_rows = []
    for hm in SNAPSHOTS:
        g = snap[snap.snapshot_min == hm]
        d = g[g.idx < SPLIT]
        v = g[g.idx >= SPLIT]
        for period, x in [("full", g), ("discovery", d), ("validation", v)]:
            u = x[x.unresolved]
            status_rows.append({
                "snapshot_min": hm, "period": period, "n": int(len(x)),
                "alive_n": int(x.alive.sum()), "already_expanded_n": int(x.already_expanded08.sum()),
                "unresolved_n": int(x.unresolved.sum()),
                "future_expand_n": int(u.future_expand08.sum()) if len(u) else 0,
                "future_expand_rate": float(u.future_expand08.mean()) if len(u) else np.nan,
            })
    status = pd.DataFrame(status_rows)
    status.to_csv(OUT / "s57e_snapshot_status.csv", index=False)

    cont_rows, bin_rows = [], []
    for hm in SNAPSHOTS:
        g0 = snap[(snap.snapshot_min == hm) & snap.unresolved].copy()
        for period, g in [
            ("full", g0),
            ("discovery", g0[g0.idx < SPLIT]),
            ("validation", g0[g0.idx >= SPLIT]),
        ]:
            for feat in CONT_FEATURES:
                cont_rows.append(cont_comp(g, feat, period, hm))
            for sig in BINARY_EXPECTED:
                bin_rows.append(binary_row(g, sig, period, hm))

    cont = pd.DataFrame(cont_rows)
    binary = pd.DataFrame(bin_rows)
    cont.to_csv(OUT / "s57e_continuous_atlas.csv", index=False)
    binary.to_csv(OUT / "s57e_binary_confirmation_atlas.csv", index=False)

    # Directional stability summary for continuous information only; no cutoffs.
    stab_rows = []
    for hm in SNAPSHOTS:
        for feat in CONT_FEATURES:
            q = cont[(cont.snapshot_min == hm) & (cont.feature == feat)].set_index("period")
            d, v, full = q.loc["discovery"], q.loc["validation"], q.loc["full"]
            same = bool(d.direction == v.direction and d.direction != "TIE")
            dsep = abs(float(d.auc_expand_high) - 0.5) if np.isfinite(d.auc_expand_high) else np.nan
            vsep = abs(float(v.auc_expand_high) - 0.5) if np.isfinite(v.auc_expand_high) else np.nan
            stab_rows.append({
                "snapshot_min": hm, "feature": feat, "full_auc": full.auc_expand_high,
                "disc_auc": d.auc_expand_high, "val_auc": v.auc_expand_high,
                "disc_direction": d.direction, "val_direction": v.direction,
                "same_direction": same,
                "min_half_separation": float(min(dsep, vsep)) if np.isfinite(dsep) and np.isfinite(vsep) else np.nan,
            })
    stability = pd.DataFrame(stab_rows).sort_values(
        ["snapshot_min", "same_direction", "min_half_separation"], ascending=[True, False, False]
    )
    stability.to_csv(OUT / "s57e_continuous_stability.csv", index=False)

    # Predeclared binary confirmation eligibility. Sample guardrails are deliberately
    # strict for a 16-trade parent cohort: both signal states must exist in D and V;
    # the expected direction must hold in both halves; and full effect >=20pp.
    eligible = []
    for hm in SNAPSHOTS:
        for sig, exp in BINARY_EXPECTED.items():
            q = binary[(binary.snapshot_min == hm) & (binary.signal == sig)].set_index("period")
            d, v, ff = q.loc["discovery"], q.loc["validation"], q.loc["full"]
            support = bool(d.yes_n >= 1 and d.no_n >= 1 and v.yes_n >= 1 and v.no_n >= 1)
            dir_ok = bool(d.expected_direction_ok and v.expected_direction_ok)
            effect_ok = bool(np.isfinite(ff.effect_yes_minus_no) and abs(float(ff.effect_yes_minus_no)) >= 0.20)
            if support and dir_ok and effect_ok:
                eligible.append({
                    "snapshot_min": hm, "signal": sig, "expected": exp,
                    "full_effect": float(ff.effect_yes_minus_no),
                    "disc_effect": float(d.effect_yes_minus_no),
                    "val_effect": float(v.effect_yes_minus_no),
                    "disc_yes_n": int(d.yes_n), "disc_no_n": int(d.no_n),
                    "val_yes_n": int(v.yes_n), "val_no_n": int(v.no_n),
                })
    elig_df = pd.DataFrame(eligible)
    elig_df.to_csv(OUT / "s57e_confirmation_candidates.csv", index=False)

    # Outcome economics are descriptive only; outcome labels are hindsight.
    exp = base[base.post_expand08]
    stalled = base[~base.post_expand08]
    outcome = {
        "expander_n": int(len(exp)), "stalled_n": int(len(stalled)),
        "expander_a719_pnl": float(exp.a719_pnl.sum()),
        "stalled_a719_pnl": float(stalled.a719_pnl.sum()),
        "expander_post_mfe_median": float(exp.post_mfe_high.median()),
        "stalled_post_mfe_median": float(stalled.post_mfe_high.median()),
    }

    summary = {
        "parity": {
            "parent_all": parent_all, "a719_all": all_a719,
            "rejected_n": int(len(base)), "post_expand08_n": int(base.post_expand08.sum()),
            "post_stalled_n": int((~base.post_expand08).sum()),
        },
        "outcome_descriptive": outcome,
        "snapshot_status": status.to_dict(orient="records"),
        "eligible_confirmation_candidates": eligible,
        "continuous_stability": stability.to_dict(orient="records"),
    }
    (OUT / "s57e_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x):
        return "NA" if not np.isfinite(x) else f"{100*x:.1f}%"
    def money(x):
        return f"${x:+.3f}"

    lines = [
        "# BTC Temporal Saturday T-Method S5.7E — Post-Rejection Expansion vs Stall Atlas",
        "",
        "**Status:** COMPLETE — FORENSIC ONLY; NO MANAGEMENT ACTION APPLIED",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen causal design",
        "- Cohort: exact 16 S5.7C/S5.7D `REJECTED_HINGE` trades.",
        "- Overall outcome landmark: post-signal +0.80% expansion (7 expanders / 9 stalled).",
        "- Predictor snapshots: +15m / +30m / +60m after rejected morphology becomes knowable.",
        "- At each snapshot, only alive trades that have NOT already hit +0.80% are evaluated; target is future +0.80% after the snapshot.",
        "- No feature threshold sweep and no action simulation.",
        "",
        "## Parity",
        f"- Static parent all 139: **{money(parent_all)}**",
        f"- A7.19 all 139: **{money(all_a719)}**",
        f"- Rejected cohort: **{len(base)}** = {int(base.post_expand08.sum())} expanders / {int((~base.post_expand08).sum())} stalled",
        "",
        "## Snapshot support",
        "| Snapshot | Period | N | Alive | Already +0.8 | Unresolved | Future expand N/rate |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in status.iterrows():
        lines.append(
            f"| {int(r.snapshot_min)}m | {r.period} | {int(r.n)} | {int(r.alive_n)} | {int(r.already_expanded_n)} | "
            f"{int(r.unresolved_n)} | {int(r.future_expand_n)}/{pct(r.future_expand_rate)} |"
        )

    lines += ["", "## Eligible fixed confirmation events"]
    if eligible:
        lines += ["| Snapshot | Signal | Expected | Full effect | D effect | V effect | D yes/no | V yes/no |",
                  "|---:|---|---|---:|---:|---:|---:|---:|"]
        for r in eligible:
            lines.append(
                f"| {r['snapshot_min']}m | {r['signal']} | {r['expected']} | {r['full_effect']:+.3f} | "
                f"{r['disc_effect']:+.3f} | {r['val_effect']:+.3f} | {r['disc_yes_n']}/{r['disc_no_n']} | {r['val_yes_n']}/{r['val_no_n']} |"
            )
    else:
        lines.append("**NONE** under the predeclared support + D/V direction + >=20pp full-effect gate.")

    lines += ["", "## Strongest continuous information by snapshot"]
    for hm in SNAPSHOTS:
        q = stability[stability.snapshot_min == hm]
        stable = q[q.same_direction].head(6)
        lines.append(f"### +{hm}m")
        if len(stable) == 0:
            lines.append("- No continuous feature has the same expander-vs-stalled direction in discovery and validation.")
        else:
            for _, r in stable.iterrows():
                lines.append(
                    f"- `{r.feature}`: D AUC {r.disc_auc:.3f}, V AUC {r.val_auc:.3f}, "
                    f"direction {r.disc_direction}, min-half separation {r.min_half_separation:.3f}."
                )

    lines += [
        "",
        "## Guardrail",
        "- EXPANDER/STALLED is an outcome label only; it is never used as an input feature.",
        "- A confirmation candidate only survives if the fixed event separates future expansion in both discovery and validation with support on both sides.",
        "- Continuous AUCs are descriptive only; no cutoff is optimized from them.",
        "- A7.19 and A7.26 remain frozen and unchanged.",
    ]
    (OUT / "S5.7E_CHECKPOINT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
