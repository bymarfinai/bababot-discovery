#!/usr/bin/env python3
"""Saturday T-Method S5.2B — Selective RUNNER vs PROTECT action test.

Research only; live BBC untouched.

Frozen controls:
- parent Saturday18 BUY / TP2.6 / SL1.2 / 18h
- A7.19 full-coverage champion
- A7.26 selective benchmark

S5.2A established:
- management should begin only after a causal +0.50% favorable hinge,
- trades already graduated to +0.80% should be preserved,
- ordinary pullbacks should not be protected indiscriminately,
- prior FAILURE is context, not a hard gate,
- post-hinge flow/structure deterioration is the most promising causal place to act.

Predeclared rules (NO threshold sweep):
A) FLOW_EMA_PROTECT
   After +0.50 hinge, before any +0.80 graduation and before A7.19 exit,
   first completed 5m state with:
      close progress <= +0.30%
      cumulative post-hinge taker edge < 0
      next decision-open < completed-bar EMA20
   => arm +0.20% profit lock at that exact next 5m open.

B) ADAPTIVE_MEMORY_PROTECT
   Same event. CLEAN trades use it directly. If the trade had a frozen FAILURE
   before the +0.50 hinge, require hinge cumulative taker <= 0 as an additional
   weak-recovery confirmation.

Execution is strict causal. If the +0.20 lock has already been lost at the
causal decision-open, exit at the actual open. Otherwise arm the lock. If no
lock/TP is hit before the frozen A7.19 exit, preserve A7.19 exactly.
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

OUT = Path(os.getenv("S52B_OUT", "s52b_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
LOCK = 0.002
GIVEBACK = 0.003
DEEP = 0.008


def profit_factor(p):
    pos = sum(x for x in p if x > 0)
    neg = -sum(x for x in p if x <= 0)
    return float(pos / neg) if neg > 0 else float("inf")


def max_dd(p):
    a = np.asarray(p, dtype=float)
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peak[1:] - eq).max()) if len(eq) else 0.0


def loss_streak(p):
    cur = best = 0
    for x in p:
        if x <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def metrics(p):
    p = list(map(float, p)); n = len(p); w = sum(x > 0 for x in p)
    return {
        "n": n, "wins": w, "wr": w / n if n else np.nan,
        "pnl": float(sum(p)), "expectancy": float(np.mean(p)) if n else np.nan,
        "pf": profit_factor(p), "max_dd": max_dd(p), "loss_streak": loss_streak(p),
    }


def a719_exit_time(t, tr, s240):
    if s240["state240"] == "SHALLOW_FAILURE":
        return t + pd.Timedelta(minutes=240)
    return pd.Timestamp(tr.exit_t)


def first_action_event(k, t, tr, base_exit, h05, prior_failure, hinge_taker, adaptive):
    """Return first causal protect decision event or None.

    Any +0.80 touch in a completed bar before the decision permanently graduates
    the trade and prevents S5.2B action.
    """
    if h05 is None or h05 >= base_exit:
        return None
    post = k[(k.index >= h05) & (k.index < base_exit)]
    if post.empty:
        return None
    tak_num = 0.0
    tak_den = 0
    for b in post.itertuples(index=False):
        decision_t = b.ts + pd.Timedelta(minutes=5)
        if decision_t > base_exit:
            break
        # At decision time the full bar is completed. If +0.8 was touched anywhere
        # in that bar, graduation is already known and runner is preserved.
        if float(b.high) / tr.entry - 1.0 >= DEEP:
            return None
        if np.isfinite(float(b.taker_imb)):
            tak_num += float(b.taker_imb)
            tak_den += 1
        post_taker = tak_num / tak_den if tak_den else np.nan
        close_prog = float(b.close) / tr.entry - 1.0
        if decision_t not in k.index:
            continue
        decision_open = float(k.loc[decision_t, "open"])
        below_ema = decision_open < float(b.ema20)
        event = close_prog <= GIVEBACK and np.isfinite(post_taker) and post_taker < 0 and below_ema
        if not event:
            continue
        if adaptive and prior_failure and not (np.isfinite(hinge_taker) and hinge_taker <= 0):
            # Recovered trade had positive flow at +0.5; preserve it despite later
            # generic deterioration because S5.2A found this interaction matters.
            continue
        return {
            "decision_t": decision_t,
            "decision_open": decision_open,
            "close_progress": close_prog,
            "post_taker": post_taker,
            "ema20": float(b.ema20),
            "prior_failure": bool(prior_failure),
            "hinge_taker": float(hinge_taker) if np.isfinite(hinge_taker) else np.nan,
        }
    return None


def protected_pnl(k, f, t, tr, base_exit, base_pnl, ev):
    d = ev["decision_t"]
    op = float(ev["decision_open"])
    lock_px = tr.entry * (1.0 + LOCK)
    tp_px = tr.entry * (1.0 + s50.TP)
    if op <= lock_px:
        fund, _ = s50.funding_cost(k, f, t, d, tr.entry)
        pnl = s50.NOTIONAL * (op / tr.entry - 1.0) - s50.FEE - fund
        return float(pnl), "ACTUAL_OPEN", d, op
    # Lock is armed at d. Frozen A7.19 remains the terminal fallback.
    bars = k[(k.index >= d) & (k.index < base_exit)]
    for b in bars.itertuples(index=False):
        # Adverse-first ambiguity: profit lock before original TP.
        if float(b.low) <= lock_px:
            ex = b.ts + pd.Timedelta(minutes=5)
            fund, _ = s50.funding_cost(k, f, t, ex, tr.entry)
            pnl = s50.NOTIONAL * LOCK - s50.FEE - fund
            return float(pnl), "LOCK", ex, lock_px
        if float(b.high) >= tp_px:
            ex = b.ts + pd.Timedelta(minutes=5)
            fund, _ = s50.funding_cost(k, f, t, ex, tr.entry)
            pnl = s50.NOTIONAL * s50.TP - s50.FEE - fund
            return float(pnl), "TP", ex, tp_px
    return float(base_pnl), "A719_FALLBACK", base_exit, np.nan


def evaluate(df, action_col, name):
    base = df.a719_pnl.to_numpy(dtype=float)
    strat = base.copy()
    mask = df[action_col].notna().to_numpy()
    strat[mask] = df.loc[mask, action_col].to_numpy(dtype=float)
    delta = strat - base
    disc = slice(0, SPLIT); val = slice(SPLIT, len(df))
    idx = np.where(mask)[0]
    out = {
        "policy": name,
        "actions": int(mask.sum()),
        "actions_disc": int(mask[:SPLIT].sum()),
        "actions_val": int(mask[SPLIT:].sum()),
        **metrics(strat),
        "delta": float(delta.sum()),
        "disc_pnl": float(strat[disc].sum()), "disc_delta": float(delta[disc].sum()),
        "val_pnl": float(strat[val].sum()), "val_delta": float(delta[val].sum()),
        "improved": int((delta[idx] > 1e-12).sum()),
        "damaged": int((delta[idx] < -1e-12).sum()),
        "neg_to_pos": int(((base[idx] <= 0) & (strat[idx] > 0)).sum()),
        "pos_to_neg": int(((base[idx] > 0) & (strat[idx] <= 0)).sum()),
        "future_deep_actions": int(df.loc[mask, "eventual_deep"].sum()),
        "future_deep_damaged": int(((df.loc[mask, "eventual_deep"].to_numpy()) & (delta[idx] < -1e-12)).sum()),
    }
    out["robust_gate"] = bool(out["actions_disc"] >= 5 and out["actions_val"] >= 5 and out["disc_delta"] > 0 and out["val_delta"] > 0)
    return out, strat


def main():
    k = s50.load_klines(); f = s50.load_funding(); entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]
    recs = []
    for i, (t, tr) in enumerate(zip(entries, trades)):
        pre = a50.pre_context(k, t)
        s240 = a50.state240(k, t, tr)
        base_pnl = a50.a719_pnl(k, f, t, tr, s240)
        base_exit = a719_exit_time(t, tr, s240)
        h05, h08 = a52.first_hinges(k, t, tr)
        mem = a52.prehinge_memory(k, t, tr, h05) if h05 is not None else {
            "prior_failure": False, "hinge_taker": np.nan,
        }
        eventual_deep = h08 is not None
        row = {
            "idx": i, "date": tr.date, "pre_state": pre["pre_state"],
            "parent_pnl": float(tr.pnl), "a719_pnl": float(base_pnl),
            "base_exit": str(base_exit), "hinge05": h05 is not None,
            "eventual_deep": eventual_deep, "prior_failure": bool(mem.get("prior_failure", False)),
            "hinge_taker": mem.get("hinge_taker", np.nan),
            "flow_ema_pnl": np.nan, "adaptive_memory_pnl": np.nan,
            "flow_ema_reason": "NONE", "adaptive_reason": "NONE",
        }
        for adaptive, prefix in [(False, "flow_ema"), (True, "adaptive_memory")]:
            ev = first_action_event(k, t, tr, base_exit, h05, row["prior_failure"], row["hinge_taker"], adaptive)
            if ev is not None:
                pnl, reason, ex_t, ex_px = protected_pnl(k, f, t, tr, base_exit, base_pnl, ev)
                row[f"{prefix}_pnl"] = pnl
                row[f"{prefix}_reason"] = reason
                row[f"{prefix}_event_t"] = str(ev["decision_t"])
                row[f"{prefix}_event_min"] = (ev["decision_t"] - t).total_seconds() / 60.0
                row[f"{prefix}_event_progress"] = ev["decision_open"] / tr.entry - 1.0
                row[f"{prefix}_event_post_taker"] = ev["post_taker"]
                row[f"{prefix}_event_ema_dist"] = ev["decision_open"] / ev["ema20"] - 1.0
                row[f"{prefix}_exit_t"] = str(ex_t)
                row[f"{prefix}_exit_px"] = ex_px
        recs.append(row)
    df = pd.DataFrame(recs)

    # Frozen parity gates before interpretation.
    if len(df) != 139 or int((df.parent_pnl > 0).sum()) != 65 or abs(df.parent_pnl.sum() - 87.20) > 0.20:
        raise RuntimeError("parent parity failed")
    if abs(df.a719_pnl.sum() - 103.3830997612) > 0.01:
        raise RuntimeError("A7.19 parity failed")
    if int(df.hinge05.sum()) != 89 or int(df.eventual_deep.sum()) != 61:
        raise RuntimeError("hinge/deep parity failed")
    stretched = df.pre_state.eq("STRETCHED")
    if int(stretched.sum()) != 16 or abs(df.loc[~stretched, "a719_pnl"].sum() - 109.58688181) > 0.01:
        raise RuntimeError("A7.26 parity failed")

    results = []
    series = {}
    for col, name in [("flow_ema_pnl", "FLOW_EMA_PROTECT"), ("adaptive_memory_pnl", "ADAPTIVE_MEMORY_PROTECT")]:
        r, s = evaluate(df, col, name); results.append(r); series[name] = s
    res = pd.DataFrame(results).sort_values(["robust_gate", "delta"], ascending=[False, False]).reset_index(drop=True)
    df.to_csv(OUT / "s52b_rows.csv", index=False)
    res.to_csv(OUT / "s52b_results.csv", index=False)

    parent = metrics(df.parent_pnl)
    a719 = metrics(df.a719_pnl)
    summary = {
        "parent": parent, "a719": a719,
        "a726": {"n": int((~stretched).sum()), "pnl": float(df.loc[~stretched, "a719_pnl"].sum())},
        "results": res.to_dict(orient="records"),
    }
    (OUT / "s52b_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x): return f"{100*x:.2f}%"
    def money(x): return f"${x:+.3f}"
    lines = [
        "# BTC Temporal Saturday T-Method S5.2B — Selective RUNNER vs PROTECT",
        "", "**Research only; live BBC untouched.**", "",
        "## Frozen controls",
        f"- Parent: 139 / WR {pct(parent['wr'])} / {money(parent['pnl'])}",
        f"- A7.19: 139 / WR {pct(a719['wr'])} / {money(a719['pnl'])}",
        f"- A7.26 selective: 123 / {money(summary['a726']['pnl'])}",
        "- +0.50 hinge: 89; eventual +0.80 deep: 61", "",
        "## Predeclared policies",
        "1. FLOW_EMA_PROTECT: after +0.50, before +0.80, close <=+0.30 + post-hinge taker<0 + next-open below EMA20; arm +0.20 lock.",
        "2. ADAPTIVE_MEMORY_PROTECT: same; prior-FAILURE trades additionally require hinge taker<=0.",
        "", "## Results vs exact A7.19",
        "| Policy | Actions D/V | WR | PnL | Delta | Disc delta | Val delta | Improved/Damaged | Neg->Pos / Pos->Neg | Future-deep actions/damaged | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in res.iterrows():
        lines.append(
            f"| {r.policy} | {int(r.actions_disc)}/{int(r.actions_val)} | {pct(r.wr)} | {money(r.pnl)} | {money(r.delta)} | "
            f"{money(r.disc_delta)} | {money(r.val_delta)} | {int(r.improved)}/{int(r.damaged)} | {int(r.neg_to_pos)}/{int(r.pos_to_neg)} | "
            f"{int(r.future_deep_actions)}/{int(r.future_deep_damaged)} | {'PASS' if r.robust_gate else 'FAIL'} |"
        )
    lines += ["", "## Verdict"]
    passing = res[res.robust_gate]
    if len(passing):
        best = passing.iloc[0]
        lines += [
            f"At least one predeclared policy passes the chronological gate. Best: **{best.policy}**.",
            f"It produces {money(best.pnl)} vs A7.19 {money(a719['pnl'])}, delta {money(best.delta)}.",
            "This remains same-sample research and is not pristine OOS. A robustness milestone is required before champion promotion.",
        ]
    else:
        lines += [
            "**No predeclared S5.2B policy passes the chronological gate.**",
            "Do not tune the +0.30 giveback, +0.20 lock, taker sign, or EMA condition on this same sample.",
            "The correct continuation is a new forensic/robustness question, not threshold optimization.",
        ]
    (OUT / "S5.2B_CHECKPOINT.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
