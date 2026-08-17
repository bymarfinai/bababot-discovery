#!/usr/bin/env python3
"""Saturday T-Method S5.7G — Frozen Candidate Robustness.

Research only; live BBC untouched.

Exactly two S5.7F candidates are frozen without definition changes:
1) NO_BULL_TOP_Q_30
2) NO_POS_TAKER_60

This milestone does NOT change the stricter S5.7F promotion gate retroactively.
It asks a separate predeclared question: is limited expander clipping a stable
trade-off rather than a same-sample accident?

Robust-tradeoff gate, declared before this run:
A) D/V delta remains positive (S5.7F parity check).
B) Delta is positive in >=3/4 chronological folds; if a fold has no actions,
   require every action-bearing fold positive and >=3 action-bearing folds.
C) Leave-one-action-out total delta remains >0 after removing ANY one action.
D) No eventual expander is flipped from positive A7.19 PnL to nonpositive.
E) Aggregate stalled rescue > absolute aggregate expander clipping.

No signal combinations, threshold tuning, snapshot changes, or exit-price sweep.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s51b_failure_no_ema_reclaim_cut as b51
import s52a_post_failure_recovery_forensics as a52
import s57c_hinge_rejection_robustness_management as c57
import s57d_rejected_hinge_excursion_monetization_atlas as d57
import s57e_post_rejection_expansion_stall_atlas as e57
import s57f_frozen_recovery_management_counterfactual as f57

OUT = Path(os.getenv("S57G_OUT", "s57g_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
FOLD_EDGES = [0, 35, 70, 105, 139]

CANDIDATES = [
    {"name": "NO_BULL_TOP_Q_30", "snapshot_min": 30, "signal": "last_bull_top_q",
     "expected_actions": 9, "expected_delta": 7.857},
    {"name": "NO_POS_TAKER_60", "snapshot_min": 60, "signal": "recent_taker_pos",
     "expected_actions": 5, "expected_delta": 6.855},
]


def fold_id(idx: int) -> int:
    for j in range(4):
        if FOLD_EDGES[j] <= idx < FOLD_EDGES[j + 1]:
            return j + 1
    raise RuntimeError(f"bad idx {idx}")


def build_rows():
    k = s50.load_klines()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    parent_all = float(sum(x.pnl for x in trades))
    if len(trades) != 139 or abs(parent_all - 87.199692) > 0.02:
        raise RuntimeError("parent parity fail")

    states = []
    all_a719 = 0.0
    rejected_count = 0
    rejected_expanders = 0
    for idx, (t, tr) in enumerate(zip(entries, trades)):
        s240 = a50.state240(k, t, tr)
        base = float(a50.a719_pnl(k, f, t, tr, s240))
        all_a719 += base
        base_exit = f57.a719_exit_time(t, tr, s240)

        h05, _ = a52.first_hinges(k, t, tr)
        rejected = False
        post_expand08 = False
        hinge = None
        if h05 is not None:
            hinge_ts = h05 - pd.Timedelta(minutes=5)
            hinge = k.loc[hinge_ts]
            cm = c57.morph(hinge)
            rejected = bool(np.isfinite(cm["upper_wick_ratio"]) and cm["upper_wick_ratio"] >= 0.50)
            if rejected:
                rejected_count += 1
                post = d57.post_hinge_path(k, tr, h05)
                post_expand08 = bool(post["reach_080bp"])
                rejected_expanders += int(post_expand08)

        states.append({
            "idx": idx, "t": t, "tr": tr, "a719_pnl": base,
            "a719_exit": base_exit, "h05": h05, "hinge": hinge,
            "rejected_hinge": rejected, "post_expand08": post_expand08,
        })

    if abs(all_a719 - 103.3830997612) > 0.02:
        raise RuntimeError("A7.19 parity fail")
    if rejected_count != 16 or rejected_expanders != 7:
        raise RuntimeError(f"rejected parity fail {rejected_count}/{rejected_expanders}")

    rows = []
    for cand in CANDIDATES:
        hm, sig = int(cand["snapshot_min"]), cand["signal"]
        for st in states:
            idx, t, tr = st["idx"], st["t"], st["tr"]
            base = float(st["a719_pnl"])
            strategy = base
            action = False
            unresolved = False
            signal_present = np.nan
            action_px = np.nan

            if st["rejected_hinge"] and st["h05"] is not None:
                feat = e57.snapshot_features(k, tr, st["h05"], st["hinge"], hm)
                unresolved = bool(feat.get("unresolved", False))
                if unresolved:
                    signal_present = bool(feat[sig])
                    d = st["h05"] + pd.Timedelta(minutes=hm)
                    if (not signal_present) and d <= st["a719_exit"] and d in k.index:
                        action = True
                        strategy, action_px = f57.exit_open_pnl(k, f, t, tr, d)

            rows.append({
                "candidate": cand["name"], "snapshot_min": hm, "signal": sig,
                "idx": idx, "fold": fold_id(idx), "date": tr.date,
                "rejected_hinge": bool(st["rejected_hinge"]),
                "post_expand08": bool(st["post_expand08"]),
                "unresolved": bool(unresolved), "signal_present": signal_present,
                "action": bool(action), "action_px": action_px,
                "a719_pnl": base, "strategy_pnl": float(strategy),
                "delta": float(strategy - base),
            })

    return pd.DataFrame(rows), parent_all, all_a719


def analyze_candidate(df: pd.DataFrame, cand: dict):
    name = cand["name"]
    g = df[df.candidate == name].copy().sort_values("idx")
    action = g[g.action].copy()

    total_delta = float(g.delta.sum())
    if len(action) != cand["expected_actions"] or abs(total_delta - cand["expected_delta"]) > 0.03:
        raise RuntimeError(f"S5.7F candidate parity fail {name}: actions={len(action)} delta={total_delta}")

    d = g[g.idx < SPLIT]
    v = g[g.idx >= SPLIT]
    d_delta = float(d.delta.sum())
    v_delta = float(v.delta.sum())
    transfer_ok = d_delta > 0 and v_delta > 0

    fold_rows = []
    positive_folds = 0
    action_bearing_folds = 0
    all_action_folds_positive = True
    for fold in range(1, 5):
        x = g[g.fold == fold]
        xa = x[x.action]
        delta = float(x.delta.sum())
        actions = int(len(xa))
        if actions > 0:
            action_bearing_folds += 1
            if delta > 0:
                positive_folds += 1
            else:
                all_action_folds_positive = False
        ex = xa[xa.post_expand08]
        st = xa[~xa.post_expand08]
        fold_rows.append({
            "candidate": name, "fold": fold,
            "idx_lo": FOLD_EDGES[fold-1], "idx_hi_exclusive": FOLD_EDGES[fold],
            "n": int(len(x)), "actions": actions,
            "a719_pnl": float(x.a719_pnl.sum()),
            "strategy_pnl": float(x.strategy_pnl.sum()),
            "delta": delta,
            "improved_actions": int((xa.delta > 1e-12).sum()),
            "damaged_actions": int((xa.delta < -1e-12).sum()),
            "stalled_actions": int(len(st)), "stalled_delta": float(st.delta.sum()),
            "expander_actions": int(len(ex)), "expander_delta": float(ex.delta.sum()),
        })

    fold_ok = bool(
        positive_folds >= 3 and (
            action_bearing_folds == 4 or
            (action_bearing_folds >= 3 and all_action_folds_positive)
        )
    )

    # Action-level leave-one-out: candidate must remain net additive even if any
    # single action, including the best action, is removed.
    action_rows = []
    loo_values = []
    for _, r in action.iterrows():
        loo = total_delta - float(r.delta)
        loo_values.append(loo)
        action_rows.append({
            "candidate": name, "idx": int(r.idx), "fold": int(r.fold), "date": r.date,
            "post_expand08": bool(r.post_expand08),
            "a719_pnl": float(r.a719_pnl), "strategy_pnl": float(r.strategy_pnl),
            "delta": float(r.delta), "leave_one_out_total_delta": float(loo),
            "improved": bool(r.delta > 1e-12), "damaged": bool(r.delta < -1e-12),
        })
    jackknife_ok = bool(len(loo_values) > 0 and min(loo_values) > 0)

    exp = action[action.post_expand08]
    stalled = action[~action.post_expand08]
    exp_delta = float(exp.delta.sum())
    stalled_delta = float(stalled.delta.sum())
    pos_to_nonpos = int(((exp.a719_pnl > 0) & (exp.strategy_pnl <= 0)).sum())
    expander_safety_ok = pos_to_nonpos == 0
    rescue_dominates = stalled_delta > abs(min(0.0, exp_delta))

    # Existing D/V economics are also reported for the outcome tradeoff.
    outcome_half = {}
    for period, x in [("discovery", action[action.idx < SPLIT]), ("validation", action[action.idx >= SPLIT])]:
        xs = x[~x.post_expand08]
        xe = x[x.post_expand08]
        outcome_half[period] = {
            "actions": int(len(x)),
            "delta": float(x.delta.sum()),
            "stalled_actions": int(len(xs)), "stalled_delta": float(xs.delta.sum()),
            "expander_actions": int(len(xe)), "expander_delta": float(xe.delta.sum()),
        }

    robust_tradeoff_pass = bool(
        transfer_ok and fold_ok and jackknife_ok and expander_safety_ok and rescue_dominates
    )

    strat_metrics = b51.metrics(g.strategy_pnl.to_numpy(float))
    result = {
        "candidate": name,
        "actions": int(len(action)),
        "total_delta": total_delta,
        "strategy_pnl": float(g.strategy_pnl.sum()),
        "disc_delta": d_delta, "val_delta": v_delta,
        "positive_folds": positive_folds,
        "action_bearing_folds": action_bearing_folds,
        "fold_ok": fold_ok,
        "jackknife_min_loo_delta": float(min(loo_values)) if loo_values else np.nan,
        "jackknife_ok": jackknife_ok,
        "stalled_actions": int(len(stalled)), "stalled_delta": stalled_delta,
        "expander_actions": int(len(exp)), "expander_delta": exp_delta,
        "expander_positive_to_nonpositive": pos_to_nonpos,
        "expander_safety_ok": expander_safety_ok,
        "rescue_dominates_clipping": rescue_dominates,
        "transfer_ok": transfer_ok,
        "robust_tradeoff_pass": robust_tradeoff_pass,
        "metrics": strat_metrics,
        "outcome_halves": outcome_half,
    }
    return result, fold_rows, action_rows


def main():
    df, parent_all, a719_all = build_rows()
    df.to_csv(OUT / "s57g_all_rows.csv", index=False)

    results, fold_rows, action_rows = [], [], []
    for cand in CANDIDATES:
        result, fr, ar = analyze_candidate(df, cand)
        results.append(result); fold_rows.extend(fr); action_rows.extend(ar)

    pd.DataFrame(fold_rows).to_csv(OUT / "s57g_chronology_folds.csv", index=False)
    pd.DataFrame(action_rows).to_csv(OUT / "s57g_action_jackknife.csv", index=False)
    pd.DataFrame([{
        "candidate": r["candidate"], "actions": r["actions"],
        "strategy_pnl": r["strategy_pnl"], "total_delta": r["total_delta"],
        "disc_delta": r["disc_delta"], "val_delta": r["val_delta"],
        "positive_folds": r["positive_folds"], "action_bearing_folds": r["action_bearing_folds"],
        "jackknife_min_loo_delta": r["jackknife_min_loo_delta"],
        "stalled_delta": r["stalled_delta"], "expander_delta": r["expander_delta"],
        "robust_tradeoff_pass": r["robust_tradeoff_pass"],
    } for r in results]).to_csv(OUT / "s57g_candidate_summary.csv", index=False)

    summary = {
        "parity": {"parent_all": parent_all, "a719_all": a719_all},
        "gate_definition": {
            "transfer": "D and V delta >0",
            "folds": ">=3 positive chronological folds; if any fold has no action, all action-bearing folds positive and >=3 action-bearing folds",
            "jackknife": "total delta remains >0 after removing any one action",
            "expander_safety": "no expander positive->nonpositive",
            "tradeoff": "stalled rescue > absolute expander clipping",
        },
        "candidates": results,
        "robust_tradeoff_pass": [r["candidate"] for r in results if r["robust_tradeoff_pass"]],
    }
    (OUT / "s57g_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def money(x): return f"${x:+.3f}"
    def pct(x): return f"{100*x:.2f}%"

    md = [
        "# BTC Temporal Saturday T-Method S5.7G — Frozen Candidate Robustness",
        "",
        "**Status:** COMPLETE — ROBUSTNESS ONLY; NO SIGNAL/THRESHOLD CHANGES",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen benchmarks",
        f"- Static parent: **{money(parent_all)}**",
        f"- A7.19: **{money(a719_all)}**",
        "- Candidates: `NO_BULL_TOP_Q_30`, `NO_POS_TAKER_60` exactly as S5.7F.",
        "",
        "## Predeclared robust-tradeoff gate",
        "1. D/V delta both positive.",
        "2. >=3/4 positive chronological folds; if a fold has zero actions, every action-bearing fold must be positive and >=3 folds must contain actions.",
        "3. Leave-one-action-out total delta remains >0 for every action.",
        "4. No eventual expander winner is flipped to nonpositive.",
        "5. Aggregate stalled rescue exceeds absolute expander clipping.",
        "",
    ]
    for r in results:
        md += [
            f"## {r['candidate']}",
            f"- full PnL **{money(r['strategy_pnl'])}** / delta vs A7.19 **{money(r['total_delta'])}**",
            f"- D delta **{money(r['disc_delta'])}** / V **{money(r['val_delta'])}**",
            f"- folds positive **{r['positive_folds']}/{r['action_bearing_folds']} action-bearing**; fold gate **{'PASS' if r['fold_ok'] else 'FAIL'}**",
            f"- worst leave-one-action-out delta **{money(r['jackknife_min_loo_delta'])}**; jackknife **{'PASS' if r['jackknife_ok'] else 'FAIL'}**",
            f"- stalled rescue **{money(r['stalled_delta'])}** vs expander clipping **{money(r['expander_delta'])}**",
            f"- expander winner->nonpositive **{r['expander_positive_to_nonpositive']}**",
            f"- WR **{pct(r['metrics']['wr'])}**, PF **{r['metrics']['pf']:.3f}**, DD **{r['metrics']['max_dd']:.3f}**, LS **{r['metrics']['loss_streak']}**",
            f"- ROBUST TRADEOFF: **{'PASS' if r['robust_tradeoff_pass'] else 'FAIL'}**",
            "",
            "### Chronological folds",
        ]
        for fr in [x for x in fold_rows if x["candidate"] == r["candidate"]]:
            md.append(
                f"- Fold {fr['fold']}: actions {fr['actions']} / delta **{money(fr['delta'])}** / "
                f"stalled {fr['stalled_actions']} {money(fr['stalled_delta'])} / "
                f"expander {fr['expander_actions']} {money(fr['expander_delta'])}"
            )
        md.append("")

    passed = summary["robust_tradeoff_pass"]
    md += [
        "## Decision",
        f"- robust-tradeoff pass: **{passed if passed else 'NONE'}**",
        "- This does not rewrite S5.7F's stricter zero-expander-clipping gate; it answers the separately declared robustness question about whether the clipping cost is stable and dominated by stalled rescue.",
        "- No live BBC modification is made in S5.7G.",
    ]
    (OUT / "S5.7G_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
