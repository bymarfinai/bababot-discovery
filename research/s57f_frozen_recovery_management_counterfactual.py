#!/usr/bin/env python3
"""Saturday T-Method S5.7F — Frozen Recovery Candidates x Management Counterfactual.

Research only; live BBC untouched.

Frozen context from S5.7C-E:
    REJECTED_HINGE = upper wick of first completed +0.50% hinge candle >=50% range.

Frozen recovery candidates from S5.7E (definitions are imported unchanged):
1) +30m higher_low_recent
2) +30m last_bull_top_q
3) +60m recent_taker_pos

Counterfactual for each candidate is tested SEPARATELY:
- only if the trade is REJECTED_HINGE;
- only if still alive and unresolved (has not already reached +0.80%) at snapshot;
- if the frozen recovery signal is ABSENT, exit at that exact snapshot actual open;
- otherwise preserve frozen A7.19 exactly.

No candidate combinations, no snapshot/threshold sweep, no alternative exit-price sweep.
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

OUT = Path(os.getenv("S57F_OUT", "s57f_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83

CANDIDATES = [
    {"name": "NO_HIGHER_LOW_30", "snapshot_min": 30, "signal": "higher_low_recent"},
    {"name": "NO_BULL_TOP_Q_30", "snapshot_min": 30, "signal": "last_bull_top_q"},
    {"name": "NO_POS_TAKER_60", "snapshot_min": 60, "signal": "recent_taker_pos"},
]


def a719_exit_time(t, tr, s240):
    parent_exit = pd.Timestamp(tr.exit_t)
    if s240["state240"] == "SHALLOW_FAILURE":
        return min(parent_exit, t + pd.Timedelta(minutes=240))
    return parent_exit


def exit_open_pnl(k, f, t, tr, d):
    px = float(k.loc[d, "open"])
    fund, _ = s50.funding_cost(k, f, t, d, tr.entry)
    pnl = float(s50.NOTIONAL * (px / tr.entry - 1.0) - s50.FEE - fund)
    return pnl, px


def candidate_result(df, name):
    g = df[df.candidate == name].copy()
    base = g.a719_pnl.to_numpy(float)
    strat = g.strategy_pnl.to_numpy(float)
    delta = strat - base
    act = g.action.to_numpy(bool)
    dmask = g.idx.to_numpy(int) < SPLIT
    vmask = ~dmask

    result = b51.metrics(strat)
    base_m = b51.metrics(base)
    result.update({
        "candidate": name,
        "actions": int(act.sum()),
        "actions_disc": int((act & dmask).sum()),
        "actions_val": int((act & vmask).sum()),
        "delta": float(delta.sum()),
        "disc_pnl": float(strat[dmask].sum()),
        "disc_delta": float(delta[dmask].sum()),
        "val_pnl": float(strat[vmask].sum()),
        "val_delta": float(delta[vmask].sum()),
        "improved_actions": int((delta[act] > 1e-12).sum()),
        "damaged_actions": int((delta[act] < -1e-12).sum()),
        "positive_to_nonpositive": int(((base > 0) & (strat <= 0) & act).sum()),
        "negative_to_positive": int(((base <= 0) & (strat > 0) & act).sum()),
        "baseline": base_m,
    })

    # Rejected-only outcome diagnostics. post_expand08 is defined causally after h05
    # in S5.7D; it is used here only for diagnostics, never for action selection.
    rej = g[g.rejected_hinge]
    outcome = {}
    for label, mask in [("EXPANDER", rej.post_expand08), ("STALLED", ~rej.post_expand08)]:
        x = rej[mask].copy()
        xa = x[x.action]
        outcome[label] = {
            "n": int(len(x)),
            "actions": int(len(xa)),
            "delta": float(x.delta.sum()),
            "disc_delta": float(x.loc[x.idx < SPLIT, "delta"].sum()),
            "val_delta": float(x.loc[x.idx >= SPLIT, "delta"].sum()),
            "positive_to_nonpositive": int(((x.a719_pnl > 0) & (x.strategy_pnl <= 0) & x.action).sum()),
            "a719_pnl": float(x.a719_pnl.sum()),
            "strategy_pnl": float(x.strategy_pnl.sum()),
        }
    result["outcomes"] = outcome

    # Predeclared promotion gate: no candidate is promoted on full-sample uplift alone.
    # It must transfer D/V, genuinely help stalled economics in both halves, and must
    # not economically damage the expander cohort or flip an expander winner <=0.
    ex = outcome["EXPANDER"]
    st = outcome["STALLED"]
    support_ok = result["actions_disc"] >= 2 and result["actions_val"] >= 2
    transfer_ok = result["disc_delta"] > 0 and result["val_delta"] > 0
    stalled_ok = st["disc_delta"] > 0 and st["val_delta"] > 0
    expander_safe = (
        ex["delta"] >= -1e-12
        and ex["disc_delta"] >= -1e-12
        and ex["val_delta"] >= -1e-12
        and ex["positive_to_nonpositive"] == 0
    )
    result["gate_components"] = {
        "support_ok": bool(support_ok),
        "transfer_ok": bool(transfer_ok),
        "stalled_ok": bool(stalled_ok),
        "expander_safe": bool(expander_safe),
    }
    result["promotion_pass"] = bool(support_ok and transfer_ok and stalled_ok and expander_safe)
    return result


def main():
    k = s50.load_klines()
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    parent_all = float(sum(x.pnl for x in trades))
    if len(trades) != 139 or abs(parent_all - 87.199692) > 0.02:
        raise RuntimeError("parent parity fail")

    # Build frozen per-trade state once.
    states = []
    all_a719 = 0.0
    rejected_count = 0
    rejected_expanders = 0
    for idx, (t, tr) in enumerate(zip(entries, trades)):
        s240 = a50.state240(k, t, tr)
        base = float(a50.a719_pnl(k, f, t, tr, s240))
        all_a719 += base
        base_exit = a719_exit_time(t, tr, s240)

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
            "idx": idx, "t": t, "tr": tr, "s240": s240,
            "a719_pnl": base, "a719_exit": base_exit,
            "h05": h05, "hinge": hinge,
            "rejected_hinge": rejected, "post_expand08": post_expand08,
        })

    if abs(all_a719 - 103.3830997612) > 0.02:
        raise RuntimeError("A7.19 parity fail")
    if rejected_count != 16 or rejected_expanders != 7:
        raise RuntimeError(f"rejected parity fail {rejected_count}/{rejected_expanders}")

    recs = []
    for cand in CANDIDATES:
        hm = int(cand["snapshot_min"])
        sig = cand["signal"]
        for st in states:
            idx, t, tr = st["idx"], st["t"], st["tr"]
            base = float(st["a719_pnl"])
            action = False
            strategy = base
            action_px = np.nan
            unresolved = False
            signal_present = np.nan
            snapshot_t = t + pd.Timedelta(minutes=hm) if st["h05"] is None else st["h05"] + pd.Timedelta(minutes=hm)

            if st["rejected_hinge"] and st["h05"] is not None:
                feat = e57.snapshot_features(k, tr, st["h05"], st["hinge"], hm)
                unresolved = bool(feat.get("unresolved", False))
                if unresolved:
                    signal_present = bool(feat[sig])
                    d = st["h05"] + pd.Timedelta(minutes=hm)
                    # Action only if A7.19 is still alive at the exact causal decision.
                    if (not signal_present) and d <= st["a719_exit"] and d in k.index:
                        action = True
                        strategy, action_px = exit_open_pnl(k, f, t, tr, d)

            recs.append({
                "candidate": cand["name"], "snapshot_min": hm, "signal": sig,
                "idx": idx, "date": tr.date,
                "rejected_hinge": bool(st["rejected_hinge"]),
                "post_expand08": bool(st["post_expand08"]),
                "unresolved": bool(unresolved),
                "signal_present": signal_present,
                "action": bool(action), "action_px": action_px,
                "a719_pnl": base, "strategy_pnl": float(strategy),
                "delta": float(strategy - base),
            })

    df = pd.DataFrame(recs)
    df.to_csv(OUT / "s57f_counterfactual_rows.csv", index=False)

    results = [candidate_result(df, c["name"]) for c in CANDIDATES]
    pd.DataFrame([{
        "candidate": r["candidate"], "actions": r["actions"],
        "actions_disc": r["actions_disc"], "actions_val": r["actions_val"],
        "pnl": r["pnl"], "delta": r["delta"],
        "disc_delta": r["disc_delta"], "val_delta": r["val_delta"],
        "wr": r["wr"], "pf": r["pf"], "max_dd": r["max_dd"], "loss_streak": r["loss_streak"],
        "expander_actions": r["outcomes"]["EXPANDER"]["actions"],
        "expander_delta": r["outcomes"]["EXPANDER"]["delta"],
        "stalled_actions": r["outcomes"]["STALLED"]["actions"],
        "stalled_delta": r["outcomes"]["STALLED"]["delta"],
        "promotion_pass": r["promotion_pass"],
    } for r in results]).to_csv(OUT / "s57f_candidate_summary.csv", index=False)

    summary = {
        "parity": {
            "parent_all": parent_all,
            "a719_all": all_a719,
            "rejected_n": rejected_count,
            "rejected_expanders": rejected_expanders,
            "rejected_stalled": rejected_count - rejected_expanders,
        },
        "candidates": results,
        "promoted": [r["candidate"] for r in results if r["promotion_pass"]],
    }
    (OUT / "s57f_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def money(x): return f"${x:+.3f}"
    def pct(x): return f"{100*x:.2f}%"

    md = [
        "# BTC Temporal Saturday T-Method S5.7F — Frozen Recovery Candidates × Management Counterfactual",
        "",
        "**Status:** COMPLETE — ACTION COUNTERFACTUAL; FROZEN CANDIDATES ONLY",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen design",
        "Each S5.7E recovery candidate is tested separately. On a REJECTED_HINGE trade that remains unresolved at the candidate snapshot, absence of the frozen recovery event exits at that exact snapshot actual open; otherwise A7.19 is preserved.",
        "",
        "No candidate combinations, threshold tuning, alternate snapshot, or exit-price sweep.",
        "",
        "## Parity",
        f"- Parent all 139: **{money(parent_all)}**",
        f"- A7.19 all 139: **{money(all_a719)}**",
        f"- Rejected: **{rejected_count}** = {rejected_expanders} expanders / {rejected_count-rejected_expanders} stalled",
        "",
        "## Candidate results",
    ]
    for r in results:
        ex, st = r["outcomes"]["EXPANDER"], r["outcomes"]["STALLED"]
        md += [
            f"### {r['candidate']}",
            f"- actions: **{r['actions']}** = D {r['actions_disc']} / V {r['actions_val']}",
            f"- full strategy: **{money(r['pnl'])}** vs A7.19 {money(r['baseline']['pnl'])}; delta **{money(r['delta'])}**",
            f"- D delta **{money(r['disc_delta'])}** / V delta **{money(r['val_delta'])}**",
            f"- WR **{pct(r['wr'])}**, PF **{r['pf']:.3f}**, DD **{r['max_dd']:.3f}**, LS **{r['loss_streak']}**",
            f"- stalled: actions {st['actions']} / delta **{money(st['delta'])}** / D {money(st['disc_delta'])} / V {money(st['val_delta'])}",
            f"- expanders: actions {ex['actions']} / delta **{money(ex['delta'])}** / D {money(ex['disc_delta'])} / V {money(ex['val_delta'])} / pos->nonpos {ex['positive_to_nonpositive']}",
            f"- gate: {r['gate_components']} -> **{'PASS' if r['promotion_pass'] else 'FAIL'}**",
            "",
        ]

    md += [
        "## Promotion decision",
        f"- promoted candidates: **{summary['promoted'] if summary['promoted'] else 'NONE'}**",
        "- A candidate cannot be promoted from aggregate uplift alone: D/V transfer, stalled improvement, and expander safety are all required.",
        "- A7.19 remains frozen unless a candidate passes the full gate.",
    ]
    (OUT / "S5.7F_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
