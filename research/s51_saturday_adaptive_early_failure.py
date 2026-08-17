#!/usr/bin/env python3
"""Saturday T-Method S5.1 — adaptive early-failure action test.

Research only; live BBC untouched.
Frozen references:
- parent Saturday18 BUY / TP2.6 / SL1.2 / 18h
- A7.19 full-coverage management champion
- A7.26 selective candidate

Question: the frozen +60m FAILURE_CANDIDATE state has 30 live-position signals / 23 eventual parent losses.
Can a causal action at the exact +60m open monetize that diagnosis without destroying Saturday slow runners?

No threshold search. Predeclared action families:
- CUT at +60m actual open
- FLIP_SHORT_1p2_1p2
- FLIP_SHORT_2p6_1p2 (mirror parent magnitude)

Predeclared routing cohorts only use already-frozen Saturday states:
- all FAILURE_CANDIDATE
- pre-entry PULLBACK / NORMAL / STRETCHED
- NO_0.3_IMPULSE_BY_60M (MFE60 < +0.30%; existing A7 meaningful-impulse boundary)
- STRETCHED + NO_0.3_IMPULSE_BY_60M

All non-routed occurrences retain A7.19 exactly.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50

OUT = Path(os.getenv("S51_OUT", "s51_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83


def profit_factor(pnls):
    pos = sum(x for x in pnls if x > 0)
    neg = -sum(x for x in pnls if x <= 0)
    return float(pos / neg) if neg > 0 else float("inf")


def max_dd(pnls):
    eq = np.cumsum(np.asarray(pnls, dtype=float))
    peak = np.maximum.accumulate(np.r_[0.0, eq])
    dd = peak[1:] - eq
    return float(dd.max()) if len(dd) else 0.0


def loss_streak(pnls):
    cur = best = 0
    for x in pnls:
        if x <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def metrics(pnls):
    p = list(map(float, pnls))
    n = len(p)
    w = sum(x > 0 for x in p)
    return {
        "n": n,
        "wins": w,
        "wr": w / n if n else np.nan,
        "pnl": float(sum(p)),
        "expectancy": float(np.mean(p)) if n else np.nan,
        "pf": profit_factor(p),
        "max_dd": max_dd(p),
        "loss_streak": loss_streak(p),
    }


def funding_cost_side(k, f, start_t, exit_t, entry_px, side):
    """Canonical funding proxy. side=+1 long cost; side=-1 short cost."""
    rows = f[(f.ts > start_t) & (f.ts <= exit_t)]
    qty = s50.NOTIONAL / entry_px
    total = 0.0
    for r in rows.itertuples(index=False):
        px = float(k.loc[r.ts, "open"]) if r.ts in k.index else entry_px
        total += side * qty * px * float(r.rate)
    return float(total)


def cut60_pnl(k, f, t, tr):
    d = t + pd.Timedelta(minutes=60)
    px = float(k.loc[d, "open"])
    long_fund = funding_cost_side(k, f, t, d, tr.entry, +1)
    return float(s50.NOTIONAL * (px / tr.entry - 1.0) - s50.FEE - long_fund)


def short_leg(k, f, initial_t, decision_t, short_entry, tp, sl):
    """SHORT begins at decision open and may run only until original 18h horizon."""
    end_t = initial_t + pd.Timedelta(minutes=s50.HOLD_MIN)
    bars = k[(k.index >= decision_t) & (k.index < end_t)]
    if bars.empty:
        raise RuntimeError(f"no short bars {initial_t}")
    tp_px = short_entry * (1.0 - tp)
    sl_px = short_entry * (1.0 + sl)
    reason = "TIMEOUT"
    exit_t = end_t
    exit_px = float(bars.iloc[-1].close)
    for b in bars.itertuples(index=False):
        # adverse-first same-5m convention for SHORT
        if float(b.high) >= sl_px:
            reason = "SL"
            exit_t = b.ts + pd.Timedelta(minutes=5)
            exit_px = sl_px
            break
        if float(b.low) <= tp_px:
            reason = "TP"
            exit_t = b.ts + pd.Timedelta(minutes=5)
            exit_px = tp_px
            break
    fund = funding_cost_side(k, f, decision_t, exit_t, short_entry, -1)
    pnl = s50.NOTIONAL * (1.0 - exit_px / short_entry) - s50.FEE - fund
    return float(pnl), reason, str(exit_t)


def flip60_pnl(k, f, t, tr, tp, sl):
    d = t + pd.Timedelta(minutes=60)
    px = float(k.loc[d, "open"])
    # Close BUY at exact causal decision-open.
    long_fund = funding_cost_side(k, f, t, d, tr.entry, +1)
    long_leg = s50.NOTIONAL * (px / tr.entry - 1.0) - s50.FEE - long_fund
    short_pnl, reason, exit_t = short_leg(k, f, t, d, px, tp, sl)
    return float(long_leg + short_pnl), reason, exit_t


def build_rows(k, f, entries, trades):
    out = []
    for i, (t, tr) in enumerate(zip(entries, trades)):
        pre = a50.pre_context(k, t)
        s60 = a50.thesis60(k, t, tr)
        s240 = a50.state240(k, t, tr)
        base719 = a50.a719_pnl(k, f, t, tr, s240)
        failure = s60["state60"] == "FAILURE_CANDIDATE"
        no03 = bool(failure and np.isfinite(s60["mfe60"]) and s60["mfe60"] < 0.003)
        rec = {
            "idx": i,
            "date": tr.date,
            "parent_pnl": float(tr.pnl),
            "a719_pnl": float(base719),
            "pre_state": pre["pre_state"],
            "pre_score": pre["pre_stretch_score"],
            "state60": s60["state60"],
            "progress60": s60["progress60"],
            "taker60": s60["taker60"],
            "mfe60": s60["mfe60"],
            "mae60": s60["mae60"],
            "failure": failure,
            "no03_by60": no03,
            "cut60": np.nan,
            "flip_1p2_1p2": np.nan,
            "flip_2p6_1p2": np.nan,
        }
        if failure:
            rec["cut60"] = cut60_pnl(k, f, t, tr)
            rec["flip_1p2_1p2"] = flip60_pnl(k, f, t, tr, 0.012, 0.012)[0]
            rec["flip_2p6_1p2"] = flip60_pnl(k, f, t, tr, 0.026, 0.012)[0]
        out.append(rec)
    return pd.DataFrame(out)


def cohort_masks(df):
    f = df.failure
    return {
        "FAIL_ALL": f,
        "FAIL_PULLBACK": f & df.pre_state.eq("PULLBACK"),
        "FAIL_NORMAL": f & df.pre_state.eq("NORMAL"),
        "FAIL_STRETCHED": f & df.pre_state.eq("STRETCHED"),
        "FAIL_NO03_BY60": f & df.no03_by60,
        "FAIL_STRETCHED_NO03": f & df.pre_state.eq("STRETCHED") & df.no03_by60,
    }


def evaluate_policy(df, mask, action_col, name):
    strategy = df.a719_pnl.to_numpy(dtype=float).copy()
    idxs = np.where(mask.to_numpy())[0]
    vals = df.loc[mask, action_col].to_numpy(dtype=float)
    if np.any(~np.isfinite(vals)):
        raise RuntimeError(f"nonfinite action {name}")
    strategy[idxs] = vals
    base = df.a719_pnl.to_numpy(dtype=float)
    delta = strategy - base
    disc = slice(0, SPLIT)
    val = slice(SPLIT, len(df))
    out = {
        "policy": name,
        "cohort": name.split("__")[0],
        "action": name.split("__")[1],
        "actions": int(mask.sum()),
        "actions_disc": int(mask.iloc[:SPLIT].sum()),
        "actions_val": int(mask.iloc[SPLIT:].sum()),
        **metrics(strategy),
        "delta": float(delta.sum()),
        "disc_pnl": float(strategy[disc].sum()),
        "disc_delta": float(delta[disc].sum()),
        "val_pnl": float(strategy[val].sum()),
        "val_delta": float(delta[val].sum()),
        "improved": int((delta[idxs] > 1e-12).sum()),
        "damaged": int((delta[idxs] < -1e-12).sum()),
        "unchanged": int((np.abs(delta[idxs]) <= 1e-12).sum()),
        "robust_gate": bool(mask.iloc[:SPLIT].sum() >= 5 and mask.iloc[SPLIT:].sum() >= 5 and delta[disc].sum() > 0 and delta[val].sum() > 0),
    }
    return out, strategy


def fmt_money(x): return f"${x:+.3f}"
def fmt_pct(x): return f"{100*x:.2f}%"


def main():
    k = s50.load_klines()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]
    df = build_rows(k, f, entries, trades)

    # Hard parity gates before any economics are interpreted.
    if len(df) != 139 or int((df.parent_pnl > 0).sum()) != 65 or abs(df.parent_pnl.sum() - 87.20) > 0.20:
        raise RuntimeError("parent parity failed")
    if abs(df.a719_pnl.sum() - 103.3830997612) > 0.01:
        raise RuntimeError("A7.19 parity failed")
    fail = df.failure
    if (int(fail.sum()), int(fail.iloc[:83].sum()), int(fail.iloc[83:].sum())) != (30, 17, 13):
        raise RuntimeError("A7.13 failure-state parity failed")
    if int(((df.parent_pnl <= 0) & fail).sum()) != 23:
        raise RuntimeError("failure loss-precision parity failed")

    masks = cohort_masks(df)
    actions = {
        "CUT60": "cut60",
        "FLIP12_12": "flip_1p2_1p2",
        "FLIP26_12": "flip_2p6_1p2",
    }
    results = []
    series = {}
    for cohort, mask in masks.items():
        for action, col in actions.items():
            r, strat = evaluate_policy(df, mask, col, f"{cohort}__{action}")
            results.append(r)
            series[r["policy"]] = strat
    res = pd.DataFrame(results).sort_values(["robust_gate", "delta"], ascending=[False, False]).reset_index(drop=True)
    res.to_csv(OUT / "s51_policy_results.csv", index=False)

    # Cohort diagnostics under A7.19 control and action alternatives.
    diag = []
    for cohort, mask in masks.items():
        g = df[mask]
        d = {
            "cohort": cohort,
            "n": len(g),
            "disc_n": int((g.idx < SPLIT).sum()),
            "val_n": int((g.idx >= SPLIT).sum()),
            "a719_wr": float((g.a719_pnl > 0).mean()) if len(g) else np.nan,
            "a719_pnl": float(g.a719_pnl.sum()),
            "parent_loss_rate": float((g.parent_pnl <= 0).mean()) if len(g) else np.nan,
            "cut_positive_rate": float((g.cut60 > 0).mean()) if len(g) else np.nan,
            "flip12_positive_rate": float((g.flip_1p2_1p2 > 0).mean()) if len(g) else np.nan,
            "flip26_positive_rate": float((g.flip_2p6_1p2 > 0).mean()) if len(g) else np.nan,
        }
        diag.append(d)
    diag_df = pd.DataFrame(diag)
    diag_df.to_csv(OUT / "s51_cohort_diagnostics.csv", index=False)
    df.to_csv(OUT / "s51_rows.csv", index=False)

    base = metrics(df.a719_pnl)
    parent = metrics(df.parent_pnl)
    robust = res[res.robust_gate]
    best_robust = robust.iloc[0].to_dict() if len(robust) else None
    best_full = res.iloc[0].to_dict() if len(res) else None

    summary = {
        "parent": parent,
        "a719": base,
        "failure_state": {
            "n": int(fail.sum()),
            "disc": int(fail.iloc[:83].sum()),
            "val": int(fail.iloc[83:].sum()),
            "parent_losses": int(((df.parent_pnl <= 0) & fail).sum()),
            "loss_precision": float(((df.parent_pnl <= 0) & fail).sum() / fail.sum()),
        },
        "cohorts": diag,
        "best_robust": best_robust,
        "best_full_delta": best_full,
        "results": res.to_dict(orient="records"),
    }
    (OUT / "s51_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    lines = [
        "# BTC Temporal Saturday T-Method S5.1 — Adaptive Early-Failure Action Test",
        "",
        "**Research only; live BBC untouched.**",
        "**All 139 entries retained. Non-routed trades remain exact A7.19.**",
        "",
        "## Frozen parity",
        f"- Parent: {parent['n']} trades / WR {fmt_pct(parent['wr'])} / {fmt_money(parent['pnl'])}",
        f"- A7.19: {base['n']} trades / WR {fmt_pct(base['wr'])} / {fmt_money(base['pnl'])}",
        f"- +60m FAILURE_CANDIDATE: 30 signals (17 discovery / 13 validation), 23/30 eventual parent losses = 76.67% loss precision",
        "",
        "## Policy results (A7.19 overlay)",
        "| Policy | Actions D/V | WR | PnL | Delta | Disc Δ | Val Δ | Improved/Damaged | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in res.iterrows():
        lines.append(
            f"| {r.policy} | {int(r.actions_disc)}/{int(r.actions_val)} | {fmt_pct(r.wr)} | {fmt_money(r.pnl)} | {fmt_money(r.delta)} | {fmt_money(r.disc_delta)} | {fmt_money(r.val_delta)} | {int(r.improved)}/{int(r.damaged)} | {'PASS' if r.robust_gate else 'FAIL'} |"
        )
    lines += ["", "## Cohort diagnostics", "| Cohort | N D/V | Parent-loss precision | A7.19 cohort WR/PnL | CUT +rate | Flip12 +rate | Flip26 +rate |", "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in diag_df.iterrows():
        lines.append(
            f"| {r.cohort} | {int(r.n)} {int(r.disc_n)}/{int(r.val_n)} | {fmt_pct(r.parent_loss_rate)} | {fmt_pct(r.a719_wr)} / {fmt_money(r.a719_pnl)} | {fmt_pct(r.cut_positive_rate)} | {fmt_pct(r.flip12_positive_rate)} | {fmt_pct(r.flip26_positive_rate)} |"
        )
    lines += ["", "## Predeclared interpretation rule", "A policy is not promotable merely because full-sample delta is positive. Strong S5.1 gate requires >=5 routed actions in each chronology half and positive delta vs A7.19 in both discovery and validation. No threshold/geometry is retuned after seeing these results."]
    if best_robust:
        lines += ["", "## S5.1 verdict", f"At least one predeclared policy passes the chronology gate. Best passing policy: **{best_robust['policy']}**, delta {fmt_money(best_robust['delta'])}, full PnL {fmt_money(best_robust['pnl'])}, WR {fmt_pct(best_robust['wr'])}. This remains same-sample research and must still be checked for mechanism/robustness before champion promotion."]
    else:
        lines += ["", "## S5.1 verdict", "**No predeclared CUT/FLIP policy passes the chronology gate.** The +60m failure state remains useful as diagnosis, but immediate reversal/exit is not robust enough to replace A7.19. Proceed to S5.2 selective RUNNER-vs-PROTECT rather than tuning these thresholds on the same sample."]
    (OUT / "S5.1_CHECKPOINT.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
