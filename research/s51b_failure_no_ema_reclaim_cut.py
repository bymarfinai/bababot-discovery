#!/usr/bin/env python3
"""Saturday T-Method S5.1B — one frozen adaptive failure action test.

Research only; live BBC untouched.

Predeclared hypothesis from S5.1A:
1) monitor completed 5m decisions from +15m through +180m;
2) detect the FIRST frozen FAILURE episode:
      decision-open progress <= -0.10% AND cumulative taker edge < 0
3) after first failure, allow a FULL 60 minutes for frozen EMA20 structural reclaim:
      decision-open > completed-bar EMA20 AND EMA20 slope60 > 0
4) if no reclaim occurs through the +60m confirmation decision and the A7.19
   position is still alive, CUT at that exact causal decision-open.
5) otherwise preserve A7.19 exactly.

No timing/threshold/action sweep is performed. This is a single action test.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s51a_adaptive_failure_timing_atlas as a51

OUT = Path(os.getenv("S51B_OUT", "s51b_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
FIRST_FAIL_SCAN = list(range(15, 181, 5))
RECLAIM_WINDOW = 60


def profit_factor(pnls):
    p = np.asarray(pnls, dtype=float)
    pos = float(p[p > 0].sum())
    neg = float(-p[p <= 0].sum())
    return pos / neg if neg > 0 else float("inf")


def max_dd(pnls):
    p = np.asarray(pnls, dtype=float)
    eq = np.cumsum(p)
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    return float((peak[1:] - eq).max()) if len(eq) else 0.0


def loss_streak(pnls):
    cur = best = 0
    for x in pnls:
        if x <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return best


def metrics(pnls):
    p = np.asarray(pnls, dtype=float)
    w = int((p > 0).sum())
    return {
        "n": int(len(p)), "wins": w, "wr": float(w/len(p)),
        "pnl": float(p.sum()), "expectancy": float(p.mean()),
        "pf": float(profit_factor(p)), "max_dd": max_dd(p),
        "loss_streak": loss_streak(p),
    }


def first_failure(k, t, tr):
    """Return first frozen FAILURE decision state between +15 and +180 while parent alive."""
    for m in FIRST_FAIL_SCAN:
        st = a51.decision_state(k, t, tr, m)
        if st is not None and st["failure"]:
            return m, st
    return None, None


def full_reclaim_check(k, t, tr, first_fail_m):
    """Observe the complete 60m after first failure, including the confirmation decision."""
    confirm_m = int(first_fail_m + RECLAIM_WINDOW)
    reclaim_m = None
    # First point strictly after failure through +60m inclusive.
    for m in range(int(first_fail_m + 5), confirm_m + 1, 5):
        st = a51.decision_state(k, t, tr, m)
        # Parent may have exited before confirmation. Caller decides A7.19 eligibility;
        # if parent is no longer alive, there is no actionable CUT test.
        if st is None:
            continue
        if st["ema_reclaim"]:
            reclaim_m = m
            break
    return confirm_m, reclaim_m


def a719_exit_time(t, tr, s240):
    parent_exit = pd.Timestamp(tr.exit_t)
    if s240["state240"] == "SHALLOW_FAILURE":
        d = t + pd.Timedelta(minutes=240)
        return min(parent_exit, d)
    return parent_exit


def cut_pnl(k, f, t, tr, confirm_m):
    d = t + pd.Timedelta(minutes=int(confirm_m))
    px = float(k.loc[d, "open"])
    fund, _ = s50.funding_cost(k, f, t, d, tr.entry)
    return float(s50.NOTIONAL * (px / tr.entry - 1.0) - s50.FEE - fund), px


def main():
    k = s50.load_klines(); f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    recs = []
    for i, (t, tr) in enumerate(zip(entries, trades)):
        s240 = a50.state240(k, t, tr)
        base = float(a50.a719_pnl(k, f, t, tr, s240))
        base_exit = a719_exit_time(t, tr, s240)
        pre = a50.pre_context(k, t)
        ff_m, ff_state = first_failure(k, t, tr)

        eligible_state = False
        action = False
        confirm_m = np.nan
        reclaim_m = np.nan
        cut = np.nan
        cut_px = np.nan

        if ff_m is not None:
            confirm_m_i, reclaim_m_i = full_reclaim_check(k, t, tr, ff_m)
            confirm_m = float(confirm_m_i)
            reclaim_m = float(reclaim_m_i) if reclaim_m_i is not None else np.nan
            confirm_t = t + pd.Timedelta(minutes=confirm_m_i)
            # Frozen state = first failure plus no EMA reclaim for the FULL 60m.
            eligible_state = reclaim_m_i is None
            # Only act if A7.19 has not already exited before this causal decision.
            # Equality is allowed: same actual open; if A7.19 also exits here, economics converge.
            if eligible_state and confirm_t <= base_exit and confirm_t in k.index:
                action = True
                cut, cut_px = cut_pnl(k, f, t, tr, confirm_m_i)

        strategy_pnl = float(cut) if action else base
        delta = strategy_pnl - base
        recs.append({
            "idx": i, "date": tr.date, "pre_state": pre["pre_state"],
            "parent_pnl": float(tr.pnl), "a719_pnl": base,
            "a719_exit_t": str(base_exit),
            "first_fail_m": float(ff_m) if ff_m is not None else np.nan,
            "first_fail_progress": ff_state["progress"] if ff_state is not None else np.nan,
            "first_fail_taker": ff_state["taker"] if ff_state is not None else np.nan,
            "first_fail_mfe": ff_state["mfe"] if ff_state is not None else np.nan,
            "confirm_m": confirm_m, "reclaim_m": reclaim_m,
            "no_ema_reclaim60_full": bool(eligible_state),
            "action": bool(action), "cut_px": cut_px,
            "strategy_pnl": strategy_pnl, "delta": delta,
        })

    df = pd.DataFrame(recs)

    # Frozen parity gates.
    if len(df) != 139 or int((df.parent_pnl > 0).sum()) != 65 or abs(df.parent_pnl.sum() - 87.20) > 0.20:
        raise RuntimeError("parent parity failed")
    if abs(df.a719_pnl.sum() - 103.3830997612) > 0.01:
        raise RuntimeError("A7.19 parity failed")
    # Reproduce exact +60m frozen failure count independent of S5.1B action.
    p60 = []
    for t, tr in zip(entries, trades):
        st = a51.decision_state(k, t, tr, 60)
        p60.append(bool(st is not None and st["failure"]))
    if (sum(p60), sum(p60[:83]), sum(p60[83:])) != (30, 17, 13):
        raise RuntimeError("+60m failure parity failed")

    base = df.a719_pnl.to_numpy(float)
    strat = df.strategy_pnl.to_numpy(float)
    delta = strat - base
    act = df.action.to_numpy(bool)
    dmask = np.arange(len(df)) < SPLIT
    vmask = ~dmask

    result = metrics(strat)
    base_m = metrics(base)
    action_df = df[df.action]
    eligible_df = df[df.no_ema_reclaim60_full]

    result.update({
        "actions": int(act.sum()),
        "actions_disc": int((act & dmask).sum()),
        "actions_val": int((act & vmask).sum()),
        "delta": float(delta.sum()),
        "disc_pnl": float(strat[dmask].sum()),
        "disc_delta": float(delta[dmask].sum()),
        "val_pnl": float(strat[vmask].sum()),
        "val_delta": float(delta[vmask].sum()),
        "improved": int((delta[act] > 1e-12).sum()),
        "damaged": int((delta[act] < -1e-12).sum()),
        "unchanged": int((np.abs(delta[act]) <= 1e-12).sum()),
        "positive_to_negative": int(((base > 0) & (strat <= 0) & act).sum()),
        "negative_to_positive": int(((base <= 0) & (strat > 0) & act).sum()),
        "robust_pass": bool((act & dmask).sum() >= 5 and (act & vmask).sum() >= 5 and delta[dmask].sum() > 0 and delta[vmask].sum() > 0),
    })

    # Descriptive action cohort by already-frozen pre-entry state only; no routing rule selection.
    pre_diag = []
    for st in ["PULLBACK", "NORMAL", "STRETCHED"]:
        g = action_df[action_df.pre_state == st]
        if len(g):
            pre_diag.append({
                "pre_state": st, "n": int(len(g)),
                "disc_n": int((g.idx < SPLIT).sum()), "val_n": int((g.idx >= SPLIT).sum()),
                "a719_pnl": float(g.a719_pnl.sum()), "cut_pnl": float(g.strategy_pnl.sum()),
                "delta": float(g.delta.sum()),
                "a719_loss_rate": float((g.a719_pnl <= 0).mean()),
            })

    summary = {
        "parent_pnl": float(df.parent_pnl.sum()),
        "a719": base_m,
        "s51b": result,
        "first_failure_n": int(df.first_fail_m.notna().sum()),
        "full_no_reclaim_state_n": int(df.no_ema_reclaim60_full.sum()),
        "action_n": int(df.action.sum()),
        "eligible_but_base_exited_before_confirm": int((df.no_ema_reclaim60_full & ~df.action).sum()),
        "confirmation_median": float(action_df.confirm_m.median()) if len(action_df) else np.nan,
        "confirmation_q25": float(action_df.confirm_m.quantile(.25)) if len(action_df) else np.nan,
        "confirmation_q75": float(action_df.confirm_m.quantile(.75)) if len(action_df) else np.nan,
        "pre_state_diagnostics": pre_diag,
    }
    df.to_csv(OUT / "s51b_rows.csv", index=False)
    (OUT / "s51b_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def money(x): return f"${x:+.3f}"
    def pct(x): return f"{100*x:.2f}%"
    md = [
        "# BTC Temporal Saturday T-Method S5.1B — FAIL → No EMA20 Reclaim 60m CUT",
        "",
        "**Status:** COMPLETE — single predeclared action test; no sweep",
        "**Research only:** live BBC untouched",
        "**Control:** exact A7.19 full-coverage strategy",
        "",
        "## Frozen references",
        f"- Parent: 139 / WR {pct((df.parent_pnl>0).mean())} / {money(df.parent_pnl.sum())}",
        f"- A7.19: 139 / WR {pct(base_m['wr'])} / {money(base_m['pnl'])} / PF {base_m['pf']:.3f} / DD {money(base_m['max_dd'])}",
        "- A7.26 selective benchmark remains preserved separately: 123 trades / +$109.587",
        "",
        "## Frozen S5.1B rule",
        "1. Detect first FAILURE on a completed 5m decision between +15m and +180m.",
        "2. Observe a full 60m after that first failure.",
        "3. If no frozen EMA20 reclaim occurs and A7.19 is still alive, CUT at the exact confirmation open.",
        "4. Otherwise preserve A7.19.",
        "",
        "## Result",
        f"- First-failure occurrences: **{summary['first_failure_n']}**",
        f"- Full no-EMA-reclaim-60m states: **{summary['full_no_reclaim_state_n']}**",
        f"- Actual CUT actions (A7.19 still alive): **{result['actions']}** = {result['actions_disc']} discovery / {result['actions_val']} validation",
        f"- Confirmation timing median: **+{summary['confirmation_median']:.0f}m** (Q25 +{summary['confirmation_q25']:.0f}m / Q75 +{summary['confirmation_q75']:.0f}m)",
        f"- A7.19 → S5.1B PnL: **{money(base_m['pnl'])} → {money(result['pnl'])}**",
        f"- Delta: **{money(result['delta'])}**",
        f"- WR: **{pct(base_m['wr'])} → {pct(result['wr'])}**",
        f"- PF: **{base_m['pf']:.3f} → {result['pf']:.3f}**",
        f"- Max DD: **{money(base_m['max_dd'])} → {money(result['max_dd'])}**",
        f"- Loss streak: **{base_m['loss_streak']} → {result['loss_streak']}**",
        f"- Discovery delta: **{money(result['disc_delta'])}**",
        f"- Validation delta: **{money(result['val_delta'])}**",
        f"- Improved / damaged actions: **{result['improved']} / {result['damaged']}**",
        f"- Negative→positive / positive→negative: **{result['negative_to_positive']} / {result['positive_to_negative']}**",
        f"- Robust gate (>=5 actions each half + positive delta both halves): **{'PASS' if result['robust_pass'] else 'FAIL'}**",
        "",
        "## Pre-entry diagnostics of actual actions (descriptive only)",
        "| State | N D/V | A7.19 loss | A7.19 PnL | CUT PnL | Delta |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in pre_diag:
        md.append(f"| {r['pre_state']} | {r['n']} {r['disc_n']}/{r['val_n']} | {pct(r['a719_loss_rate'])} | {money(r['a719_pnl'])} | {money(r['cut_pnl'])} | {money(r['delta'])} |")
    md += [
        "",
        "## Verdict rule",
        "- PASS only if discovery and validation delta are both positive with >=5 actions in each half.",
        "- If FAIL: close the early-failure action branch; do not tune timing or thresholds; proceed to S5.2 selective RUNNER vs PROTECT.",
        "- If PASS: preserve as a provisional adaptive management layer, still same-sample and not OOS.",
    ]
    (OUT / "S5.1B_CHECKPOINT.md").write_text("\n".join(md))
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
