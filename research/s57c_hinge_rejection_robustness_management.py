#!/usr/bin/env python3
"""Saturday T-Method S5.7C — Hinge Rejection Robustness x Management Interaction.

Research only; live BBC untouched. No new trade action is applied.

Frozen candidate from S5.7B (no threshold tuning):
    REJECTED_HINGE = upper wick of the first completed +0.50% hinge candle
                     is >= 50% of that candle's full range.

Questions:
1) Does rejected-hinge lower future >=+0.80 deep-runner probability robustly across
   discovery/validation and four chronological folds?
2) Is the clue economically meaningful under frozen parent/A7.19 management?
3) Does it interact with A7.19 SHALLOW_FAILURE monetization?
4) Is it merely duplicating A7.26 pre-entry STRETCHED, or is it orthogonal?

No wick/body threshold sweep, no new exit/protect/partial-TP rule.
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

OUT = Path(os.getenv("S57C_OUT", "s57c_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
FOLD_EDGES = [0, 35, 70, 105, 139]  # original 139-Saturday chronology, fixed natural quarters


def morph(row):
    o, h, l, c = map(float, [row.open, row.high, row.low, row.close])
    rng = max(h - l, 0.0)
    if rng <= 0:
        return {"body_ratio": np.nan, "upper_wick_ratio": np.nan, "lower_wick_ratio": np.nan,
                "close_location": np.nan, "bull": c > o}
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return {
        "body_ratio": body / rng,
        "upper_wick_ratio": upper / rng,
        "lower_wick_ratio": lower / rng,
        "close_location": (c - l) / rng,
        "bull": c > o,
    }


def metrics(g):
    if len(g) == 0:
        return {"n": 0, "deep_rate": np.nan, "parent_pnl": 0.0, "a719_pnl": 0.0,
                "a719_delta": 0.0, "parent_wr": np.nan, "a719_wr": np.nan,
                "mfe_median": np.nan, "mae_median": np.nan, "a719_actions": 0}
    return {
        "n": int(len(g)),
        "deep_rate": float(g.deep.mean()),
        "parent_pnl": float(g.parent_pnl.sum()),
        "a719_pnl": float(g.a719_pnl.sum()),
        "a719_delta": float((g.a719_pnl - g.parent_pnl).sum()),
        "parent_wr": float((g.parent_pnl > 0).mean()),
        "a719_wr": float((g.a719_pnl > 0).mean()),
        "mfe_median": float(g.parent_mfe.median()),
        "mae_median": float(g.parent_mae.median()),
        "a719_actions": int(g.a719_action.sum()),
    }


def split_metrics(g):
    out = {"full": metrics(g)}
    out["discovery"] = metrics(g[g.idx < SPLIT])
    out["validation"] = metrics(g[g.idx >= SPLIT])
    return out


def fold_id(idx):
    for j in range(4):
        if FOLD_EDGES[j] <= idx < FOLD_EDGES[j + 1]:
            return j + 1
    raise RuntimeError(f"bad idx {idx}")


def main():
    k = s50.load_klines()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    # Frozen all-trade parity.
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
        if candle_ts not in k.index:
            raise RuntimeError(f"missing hinge candle {candle_ts}")
        cm = morph(k.loc[candle_ts])
        rejected = bool(np.isfinite(cm["upper_wick_ratio"]) and cm["upper_wick_ratio"] >= 0.50)
        pre = a50.pre_context(k, t)
        rows.append({
            "idx": idx,
            "fold": fold_id(idx),
            "date": tr.date,
            "deep": bool(h08 is not None),
            "rejected_hinge": rejected,
            "accepted_hinge": not rejected,
            "hinge_time": str(h05),
            "time_to05_min": float((h05 - t).total_seconds() / 60.0),
            "parent_pnl": float(tr.pnl),
            "a719_pnl": a719,
            "a719_action": s240["state240"] == "SHALLOW_FAILURE",
            "parent_mfe": float(tr.mfe),
            "parent_mae": float(tr.mae),
            "pre_state": pre["pre_state"],
            "stretched": pre["pre_state"] == "STRETCHED",
            **cm,
        })

    if abs(all_a719 - 103.3830997612) > 0.02:
        raise RuntimeError("A7.19 parity fail")

    df = pd.DataFrame(rows).sort_values("idx").reset_index(drop=True)
    if len(df) != 89 or int(df.deep.sum()) != 61 or int((~df.deep).sum()) != 28:
        raise RuntimeError("hinge/deep parity fail")
    # Exact frozen S5.7B candidate parity.
    rej = df[df.rejected_hinge]
    acc = df[~df.rejected_hinge]
    if len(rej) != 16 or int(rej.deep.sum()) != 7:
        raise RuntimeError(f"S5.7B rejected-hinge parity fail: {len(rej)} / {int(rej.deep.sum())}")

    df.to_csv(OUT / "s57c_hinge_rows.csv", index=False)

    groups = {
        "REJECTED_HINGE": split_metrics(rej),
        "ACCEPTED_HINGE": split_metrics(acc),
    }

    # Four chronological fold robustness on original Saturday index.
    fold_rows = []
    fold_consistent = 0
    folds_comparable = 0
    for fold in range(1, 5):
        g = df[df.fold == fold]
        r = g[g.rejected_hinge]
        a = g[~g.rejected_hinge]
        rr, aa = metrics(r), metrics(a)
        comparable = len(r) > 0 and len(a) > 0 and np.isfinite(rr["deep_rate"]) and np.isfinite(aa["deep_rate"])
        consistent = bool(comparable and rr["deep_rate"] < aa["deep_rate"])
        folds_comparable += int(comparable)
        fold_consistent += int(consistent)
        fold_rows.append({
            "fold": fold,
            "idx_lo": FOLD_EDGES[fold - 1],
            "idx_hi_exclusive": FOLD_EDGES[fold],
            "rejected_n": rr["n"],
            "rejected_deep_rate": rr["deep_rate"],
            "rejected_a719_pnl": rr["a719_pnl"],
            "accepted_n": aa["n"],
            "accepted_deep_rate": aa["deep_rate"],
            "accepted_a719_pnl": aa["a719_pnl"],
            "comparable": comparable,
            "direction_consistent": consistent,
        })
    pd.DataFrame(fold_rows).to_csv(OUT / "s57c_chronology_folds.csv", index=False)

    # A7.19 management interaction: exact action versus no action by rejection state.
    interaction_rows = []
    for label, mask in [
        ("REJECTED", df.rejected_hinge),
        ("ACCEPTED", ~df.rejected_hinge),
        ("REJECTED_A719_ACTION", df.rejected_hinge & df.a719_action),
        ("ACCEPTED_A719_ACTION", (~df.rejected_hinge) & df.a719_action),
        ("REJECTED_NO_A719_ACTION", df.rejected_hinge & (~df.a719_action)),
        ("ACCEPTED_NO_A719_ACTION", (~df.rejected_hinge) & (~df.a719_action)),
    ]:
        g = df[mask]
        sm = split_metrics(g)
        for period in ["full", "discovery", "validation"]:
            interaction_rows.append({"state": label, "period": period, **sm[period]})
    pd.DataFrame(interaction_rows).to_csv(OUT / "s57c_management_interaction.csv", index=False)

    # Orthogonality to A7.26 STRETCHED.
    overlap = pd.crosstab(df.rejected_hinge, df.stretched)
    overlap_rows = []
    for rejected in [False, True]:
        for stretched in [False, True]:
            g = df[(df.rejected_hinge == rejected) & (df.stretched == stretched)]
            sm = split_metrics(g)
            overlap_rows.append({
                "rejected_hinge": rejected,
                "stretched": stretched,
                "full_n": sm["full"]["n"],
                "full_deep_rate": sm["full"]["deep_rate"],
                "full_a719_pnl": sm["full"]["a719_pnl"],
                "disc_n": sm["discovery"]["n"],
                "disc_deep_rate": sm["discovery"]["deep_rate"],
                "val_n": sm["validation"]["n"],
                "val_deep_rate": sm["validation"]["deep_rate"],
            })
    pd.DataFrame(overlap_rows).to_csv(OUT / "s57c_a726_overlap.csv", index=False)

    disc_rej = groups["REJECTED_HINGE"]["discovery"]
    disc_acc = groups["ACCEPTED_HINGE"]["discovery"]
    val_rej = groups["REJECTED_HINGE"]["validation"]
    val_acc = groups["ACCEPTED_HINGE"]["validation"]
    robust_pass = bool(
        disc_rej["deep_rate"] < disc_acc["deep_rate"]
        and val_rej["deep_rate"] < val_acc["deep_rate"]
        and fold_consistent >= 3
    )

    # Management promotion is intentionally harder: rejected cohort itself must be
    # economically broken under frozen A7.19 in BOTH halves before a new management
    # action is even eligible. Otherwise morphology remains confidence context only.
    management_action_eligible = bool(
        robust_pass
        and disc_rej["n"] >= 5 and val_rej["n"] >= 5
        and disc_rej["a719_pnl"] <= 0
        and val_rej["a719_pnl"] <= 0
    )

    summary = {
        "parity": {
            "all_parent_pnl": parent_all,
            "all_a719_pnl": all_a719,
            "hinge_n": len(df),
            "deep_n": int(df.deep.sum()),
            "rejected_n": len(rej),
            "rejected_deep_n": int(rej.deep.sum()),
        },
        "groups": groups,
        "folds": fold_rows,
        "folds_comparable": folds_comparable,
        "folds_consistent": fold_consistent,
        "robustness_pass": robust_pass,
        "management_action_eligible": management_action_eligible,
        "a719_action_counts": {
            "all_hinge": int(df.a719_action.sum()),
            "rejected": int((df.rejected_hinge & df.a719_action).sum()),
            "accepted": int(((~df.rejected_hinge) & df.a719_action).sum()),
        },
        "stretched_overlap": {
            "rejected_and_stretched": int((df.rejected_hinge & df.stretched).sum()),
            "rejected_total": int(df.rejected_hinge.sum()),
            "stretched_hinge_total": int(df.stretched.sum()),
        },
    }
    (OUT / "s57c_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x):
        return "NA" if not np.isfinite(x) else f"{100*x:.2f}%"
    def money(x):
        return f"${x:+.3f}"

    md = [
        "# BTC Temporal Saturday T-Method S5.7C — Hinge Rejection Robustness × Management Interaction",
        "",
        "**Status:** COMPLETE — FORENSIC / ROBUSTNESS ONLY; NO NEW ACTION APPLIED",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen candidate",
        "`REJECTED_HINGE = first +0.50 hinge candle upper wick >=50% of full candle range`.",
        "No wick/body threshold sweep.",
        "",
        "## Parity",
        f"- Parent all 139: **{money(parent_all)}**",
        f"- A7.19 all 139: **{money(all_a719)}**",
        f"- +0.50 hinge: **{len(df)}** = 61 deep / 28 shallow",
        f"- Rejected hinge exact S5.7B parity: **{len(rej)}**, deep **{int(rej.deep.sum())} / {len(rej)} = {pct(rej.deep.mean())}**",
        "",
        "## Frozen group results",
    ]
    for label in ["REJECTED_HINGE", "ACCEPTED_HINGE"]:
        md.append(f"### {label}")
        for period in ["full", "discovery", "validation"]:
            m = groups[label][period]
            md.append(
                f"- {period}: N {m['n']} / deep {pct(m['deep_rate'])} / parent {money(m['parent_pnl'])} / "
                f"A7.19 {money(m['a719_pnl'])} / A7.19-parent {money(m['a719_delta'])} / actions {m['a719_actions']}"
            )
        md.append("")

    md += ["## Four chronological folds"]
    for r in fold_rows:
        md.append(
            f"- Fold {r['fold']} idx {r['idx_lo']}..{r['idx_hi_exclusive']-1}: "
            f"rejected N{r['rejected_n']} deep {pct(r['rejected_deep_rate'])} vs "
            f"accepted N{r['accepted_n']} deep {pct(r['accepted_deep_rate'])}; "
            f"consistent={r['direction_consistent']}"
        )
    md += [
        f"- comparable folds: **{folds_comparable}/4**",
        f"- expected direction held: **{fold_consistent}/4**",
        f"- robustness gate: **{'PASS' if robust_pass else 'FAIL'}**",
        "",
        "## A7.19 interaction",
        f"- A7.19 actions among +0.50 hinge trades: **{int(df.a719_action.sum())}**",
        f"- rejected hinge actions: **{int((df.rejected_hinge & df.a719_action).sum())} / {len(rej)}**",
        f"- accepted hinge actions: **{int(((~df.rejected_hinge) & df.a719_action).sum())} / {len(acc)}**",
        "- `A7.19-parent` measures whether frozen +240m monetization improved the same cohort; no new action is simulated.",
        "",
        "## A7.26 overlap",
        f"- rejected + STRETCHED: **{int((df.rejected_hinge & df.stretched).sum())} / {len(rej)} rejected**",
        f"- total STRETCHED among +0.50 hinge trades: **{int(df.stretched.sum())} / {len(df)}**",
        "- This tests whether hinge rejection is merely a re-expression of the existing pre-entry exhaustion state.",
        "",
        "## Promotion gates",
        f"- morphology robustness: **{'PASS' if robust_pass else 'FAIL'}**",
        f"- new management action eligible: **{'YES' if management_action_eligible else 'NO'}**",
        "- A new management action requires the rejected cohort to be economically nonpositive under A7.19 in both discovery and validation; otherwise rejection remains a confidence/context signal only.",
        "",
        "## Guardrail",
        "No immediate cut, partial TP, protect, delay, sizing change, or A7.19 override is applied in S5.7C.",
    ]
    (OUT / "S5.7C_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
