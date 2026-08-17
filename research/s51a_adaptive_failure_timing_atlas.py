#!/usr/bin/env python3
"""Saturday T-Method S5.1A — adaptive failure timing/persistence atlas.

Research only; live BBC untouched. No CUT/FLIP action is applied.

Goal: replace a fixed +60m mental model with a causal 5m state path.
We reuse the frozen Saturday failure signature without tuning it:
    progress at decision-open <= -0.10% AND cumulative taker edge < 0

Every completed 5m decision from +15m through +180m is observed while the
original Saturday position is still alive. We map:
- first failure onset time,
- consecutive persistence / episode duration,
- first recovery to the frozen sign-symmetric HEALTHY state,
- causal impulse already established before failure,
- pre-entry PULLBACK/NORMAL/STRETCHED state,
- EMA20 reclaim context,
- eventual parent and A7.19 outcomes.

Persistence durations (5/10/15/20/30m) are descriptive atlas cuts, not rule
selection. No new trade-management policy is promoted by this script.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50

OUT = Path(os.getenv("S51A_OUT", "s51a_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
SCAN_MINUTES = list(range(15, 181, 5))
PERSIST_MINUTES = [5, 10, 15, 20, 30]


def metrics(g: pd.DataFrame) -> dict:
    if len(g) == 0:
        return {"n": 0, "parent_loss_rate": np.nan, "a719_loss_rate": np.nan,
                "parent_pnl": 0.0, "a719_pnl": 0.0, "deep_rate": np.nan,
                "hinge05_rate": np.nan}
    return {
        "n": int(len(g)),
        "parent_loss_rate": float((g.parent_pnl <= 0).mean()),
        "a719_loss_rate": float((g.a719_pnl <= 0).mean()),
        "parent_pnl": float(g.parent_pnl.sum()),
        "a719_pnl": float(g.a719_pnl.sum()),
        "deep_rate": float(g.eventual_deep.mean()),
        "hinge05_rate": float(g.eventual_05.mean()),
    }


def split_metrics(df: pd.DataFrame, mask: pd.Series, label: str, extra: dict | None = None) -> dict:
    g = df[mask]
    d = g[g.idx < SPLIT]
    v = g[g.idx >= SPLIT]
    out = {"label": label, **metrics(g)}
    dm = metrics(d); vm = metrics(v)
    out.update({f"disc_{k}": val for k, val in dm.items()})
    out.update({f"val_{k}": val for k, val in vm.items()})
    if extra:
        out.update(extra)
    return out


def decision_state(k: pd.DataFrame, t: pd.Timestamp, tr, minutes: int) -> dict | None:
    d = t + pd.Timedelta(minutes=minutes)
    if pd.Timestamp(tr.exit_t) <= d or d not in k.index:
        return None
    bars = k[(k.index >= t) & (k.index < d)]
    if len(bars) != minutes // 5:
        return None
    op = float(k.loc[d, "open"])
    progress = op / tr.entry - 1.0
    taker = float(np.nanmean(bars.taker_imb.to_numpy()))
    mfe = float(bars.high.max()) / tr.entry - 1.0
    mae = 1.0 - float(bars.low.min()) / tr.entry
    done_t = d - pd.Timedelta(minutes=5)
    done = k.loc[done_t]
    old_t = done_t - pd.Timedelta(minutes=60)
    old = k.loc[old_t] if old_t in k.index else None
    ema20 = float(done.ema20)
    ema_dist_open = op / ema20 - 1.0
    ema_slope60 = (ema20 / float(old.ema20) - 1.0) if old is not None else np.nan
    failure = bool(progress <= -0.001 and taker < 0)
    healthy = bool(progress >= 0.001 and taker > 0)
    ema_reclaim = bool(op > ema20 and np.isfinite(ema_slope60) and ema_slope60 > 0)
    return {
        "m": minutes,
        "failure": failure,
        "healthy": healthy,
        "progress": progress,
        "taker": taker,
        "mfe": mfe,
        "mae": mae,
        "ema_dist": ema_dist_open,
        "ema_slope60": ema_slope60,
        "ema_reclaim": ema_reclaim,
    }


def summarize_path(states: list[dict]) -> dict:
    if not states:
        return {
            "any_failure": False, "first_fail_min": np.nan, "max_persist_min": 0,
            "episodes": 0, "first_healthy_after_fail_min": np.nan,
            "healthy_within30": False, "healthy_within60": False,
            "first_ema_reclaim_after_fail_min": np.nan,
            "ema_reclaim_within30": False, "ema_reclaim_within60": False,
            "mfe_at_first_fail": np.nan, "no03_at_first_fail": False,
            "no05_at_first_fail": False,
        }
    fail_idxs = [i for i, s in enumerate(states) if s["failure"]]
    if not fail_idxs:
        return {
            "any_failure": False, "first_fail_min": np.nan, "max_persist_min": 0,
            "episodes": 0, "first_healthy_after_fail_min": np.nan,
            "healthy_within30": False, "healthy_within60": False,
            "first_ema_reclaim_after_fail_min": np.nan,
            "ema_reclaim_within30": False, "ema_reclaim_within60": False,
            "mfe_at_first_fail": np.nan, "no03_at_first_fail": False,
            "no05_at_first_fail": False,
        }
    first_i = fail_idxs[0]
    first = states[first_i]
    # Consecutive failure episodes measured on adjacent 5m decision points.
    max_run = cur = episodes = 0
    in_ep = False
    for s in states:
        if s["failure"]:
            cur += 1
            max_run = max(max_run, cur)
            if not in_ep:
                episodes += 1
                in_ep = True
        else:
            cur = 0
            in_ep = False
    first_healthy = np.nan
    first_reclaim = np.nan
    for s in states[first_i + 1:]:
        if np.isnan(first_healthy) and s["healthy"]:
            first_healthy = s["m"]
        if np.isnan(first_reclaim) and s["ema_reclaim"]:
            first_reclaim = s["m"]
        if not np.isnan(first_healthy) and not np.isnan(first_reclaim):
            break
    ff = first["m"]
    return {
        "any_failure": True,
        "first_fail_min": float(ff),
        "max_persist_min": int(max_run * 5),
        "episodes": int(episodes),
        "first_healthy_after_fail_min": first_healthy,
        "healthy_within30": bool(np.isfinite(first_healthy) and first_healthy - ff <= 30),
        "healthy_within60": bool(np.isfinite(first_healthy) and first_healthy - ff <= 60),
        "first_ema_reclaim_after_fail_min": first_reclaim,
        "ema_reclaim_within30": bool(np.isfinite(first_reclaim) and first_reclaim - ff <= 30),
        "ema_reclaim_within60": bool(np.isfinite(first_reclaim) and first_reclaim - ff <= 60),
        "mfe_at_first_fail": float(first["mfe"]),
        "no03_at_first_fail": bool(first["mfe"] < 0.003),
        "no05_at_first_fail": bool(first["mfe"] < 0.005),
    }


def first_persistence_confirmation(states: list[dict], need_min: int) -> float:
    need = need_min // 5
    run = 0
    for s in states:
        if s["failure"]:
            run += 1
            if run >= need:
                return float(s["m"])
        else:
            run = 0
    return np.nan


def time_bin(x):
    if not np.isfinite(x): return "NO_FAILURE"
    if x <= 30: return "15-30"
    if x <= 60: return "35-60"
    if x <= 120: return "65-120"
    return "125-180"


def main():
    k = s50.load_klines(); f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]
    recs = []
    path_rows = []
    for i, (t, tr) in enumerate(zip(entries, trades)):
        pre = a50.pre_context(k, t)
        s240 = a50.state240(k, t, tr)
        a719 = a50.a719_pnl(k, f, t, tr, s240)
        rp = a50.runner_path(k, t, tr)
        states = []
        for m in SCAN_MINUTES:
            st = decision_state(k, t, tr, m)
            if st is None:
                continue
            states.append(st)
            path_rows.append({"idx": i, "date": tr.date, "pre_state": pre["pre_state"], **st})
        p = summarize_path(states)
        for pm in PERSIST_MINUTES:
            p[f"persist{pm}_confirm_min"] = first_persistence_confirmation(states, pm)
            p[f"persist{pm}"] = bool(np.isfinite(p[f"persist{pm}_confirm_min"]))
        recs.append({
            "idx": i, "date": tr.date, "pre_state": pre["pre_state"],
            "pre_score": pre["pre_stretch_score"], "parent_pnl": float(tr.pnl),
            "a719_pnl": float(a719), "eventual_05": bool(rp["runner_state"] != "NO_0.5_IMPULSE"),
            "eventual_deep": bool(rp["runner_state"] == "DEEP_RUNNER"),
            "runner_state": rp["runner_state"], **p,
        })
    df = pd.DataFrame(recs)
    paths = pd.DataFrame(path_rows)

    # Hard frozen parity gates.
    if len(df) != 139 or int((df.parent_pnl > 0).sum()) != 65 or abs(df.parent_pnl.sum() - 87.20) > 0.20:
        raise RuntimeError("parent parity failed")
    if abs(df.a719_pnl.sum() - 103.3830997612) > 0.01:
        raise RuntimeError("A7.19 parity failed")
    # Exact +60m frozen FAILURE parity from S5.0A/S5.1.
    p60 = paths[paths.m == 60]
    f60 = p60.failure
    if (int(f60.sum()), int(p60.loc[f60, 'idx'].lt(SPLIT).sum()), int(p60.loc[f60, 'idx'].ge(SPLIT).sum())) != (30, 17, 13):
        raise RuntimeError("+60m failure parity failed")

    df["first_fail_bin"] = df.first_fail_min.apply(time_bin)
    df.to_csv(OUT / "s51a_trade_atlas.csv", index=False)
    paths.to_csv(OUT / "s51a_5m_paths.csv", index=False)

    tables = {}
    tables["any_failure"] = [
        split_metrics(df, df.any_failure, "ANY_FAILURE"),
        split_metrics(df, ~df.any_failure, "NO_FAILURE_15_180"),
    ]
    tables["onset_bins"] = []
    for b in ["15-30", "35-60", "65-120", "125-180"]:
        tables["onset_bins"].append(split_metrics(df, df.first_fail_bin.eq(b), b))

    tables["persistence"] = []
    for pm in PERSIST_MINUTES:
        mask = df[f"persist{pm}"]
        confirms = df.loc[mask, f"persist{pm}_confirm_min"]
        tables["persistence"].append(split_metrics(
            df, mask, f"PERSIST_{pm}M",
            {"confirm_median": float(confirms.median()) if len(confirms) else np.nan}
        ))

    tables["prestate_persist15"] = []
    for st in ["PULLBACK", "NORMAL", "STRETCHED"]:
        mask = df.persist15 & df.pre_state.eq(st)
        tables["prestate_persist15"].append(split_metrics(df, mask, f"{st}+PERSIST15"))

    # Recovery maps after any first failure.
    af = df.any_failure
    tables["recovery"] = [
        split_metrics(df, af & df.healthy_within30, "FAIL_THEN_HEALTHY<=30M"),
        split_metrics(df, af & ~df.healthy_within30 & df.healthy_within60, "FAIL_THEN_HEALTHY_35_60M"),
        split_metrics(df, af & ~df.healthy_within60, "FAIL_NO_HEALTHY<=60M"),
    ]
    tables["ema_reclaim"] = [
        split_metrics(df, af & df.ema_reclaim_within30, "FAIL_EMA_RECLAIM<=30M"),
        split_metrics(df, af & ~df.ema_reclaim_within30 & df.ema_reclaim_within60, "FAIL_EMA_RECLAIM_35_60M"),
        split_metrics(df, af & ~df.ema_reclaim_within60, "FAIL_NO_EMA_RECLAIM<=60M"),
    ]

    # Composite descriptive states requested by the adaptive hypothesis. These are NOT action rules.
    tables["composites"] = []
    composites = {
        "PERSIST15+NO_HEALTHY60": df.persist15 & ~df.healthy_within60,
        "PERSIST20+NO_HEALTHY60": df.persist20 & ~df.healthy_within60,
        "PERSIST15+NO03_AT_FIRST_FAIL": df.persist15 & df.no03_at_first_fail,
        "STRETCHED+PERSIST15": df.persist15 & df.pre_state.eq("STRETCHED"),
        "PULLBACK+PERSIST15": df.persist15 & df.pre_state.eq("PULLBACK"),
    }
    for name, mask in composites.items():
        tables["composites"].append(split_metrics(df, mask, name))

    # Identify only descriptive candidates with reasonable presence in both chronological halves.
    candidates = []
    for section in ["persistence", "prestate_persist15", "recovery", "ema_reclaim", "composites"]:
        for r in tables[section]:
            if r["disc_n"] >= 5 and r["val_n"] >= 5:
                # Stable harmful state = loss rate >=60% in both halves.
                stable_bad = (r["disc_a719_loss_rate"] >= 0.60 and r["val_a719_loss_rate"] >= 0.60)
                # Stable recovery state = loss rate <=45% in both halves.
                stable_good = (r["disc_a719_loss_rate"] <= 0.45 and r["val_a719_loss_rate"] <= 0.45)
                if stable_bad or stable_good:
                    candidates.append({"section": section, "kind": "BAD" if stable_bad else "GOOD", **r})

    summary = {
        "parent_pnl": float(df.parent_pnl.sum()),
        "a719_pnl": float(df.a719_pnl.sum()),
        "n": len(df),
        "any_failure_n": int(df.any_failure.sum()),
        "tables": tables,
        "stable_descriptive_candidates": candidates,
    }
    (OUT / "s51a_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x): return "NA" if not np.isfinite(x) else f"{100*x:.2f}%"
    def money(x): return "NA" if not np.isfinite(x) else f"${x:+.3f}"
    def mdtable(rows):
        z = ["| State | N D/V | A7.19 loss% | A7.19 PnL | Disc loss% / PnL | Val loss% / PnL | Deep% |",
             "|---|---:|---:|---:|---:|---:|---:|"]
        for r in rows:
            z.append(f"| {r['label']} | {r['n']} {r['disc_n']}/{r['val_n']} | {pct(r['a719_loss_rate'])} | {money(r['a719_pnl'])} | {pct(r['disc_a719_loss_rate'])} / {money(r['disc_a719_pnl'])} | {pct(r['val_a719_loss_rate'])} / {money(r['val_a719_pnl'])} | {pct(r['deep_rate'])} |")
        return "\n".join(z)

    md = [
        "# BTC Temporal Saturday T-Method S5.1A — Adaptive Failure Timing/Persistence Atlas",
        "",
        "**Status:** COMPLETE — FORENSIC ONLY; NO NEW ACTION RULE PROMOTED",
        "**Live BBC:** untouched",
        "**Frozen references:** parent +$87.20; A7.19 +$103.383; A7.26 preserved separately.",
        "",
        "## Method",
        "The frozen FAILURE signature is evaluated every completed 5m decision from +15m through +180m while the original trade is alive: `decision-open progress <= -0.10% AND cumulative taker edge < 0`. No threshold was tuned.",
        "",
        "## Any failure", mdtable(tables['any_failure']), "",
        "## First failure onset", mdtable(tables['onset_bins']), "",
        "## Persistence atlas", mdtable(tables['persistence']), "",
        "## Pre-entry state x 15m persistence", mdtable(tables['prestate_persist15']), "",
        "## Recovery after first failure", mdtable(tables['recovery']), "",
        "## EMA20 reclaim after first failure", mdtable(tables['ema_reclaim']), "",
        "## Composite descriptive states", mdtable(tables['composites']), "",
        "## Stable descriptive candidates (minimum 5 in both halves)",
    ]
    if candidates:
        for c in candidates:
            md.append(f"- {c['kind']} / {c['section']} / `{c['label']}`: N{c['n']} ({c['disc_n']}/{c['val_n']}), A7.19 loss {pct(c['a719_loss_rate'])}, discovery {pct(c['disc_a719_loss_rate'])}, validation {pct(c['val_a719_loss_rate'])}, A7.19 PnL {money(c['a719_pnl'])}.")
    else:
        md.append("- None. Persistence did not create a state with adequate support and the same directional outcome in both chronology halves.")
    md += [
        "",
        "## Interpretation rule",
        "This checkpoint does not choose a best persistence duration and does not apply CUT/FLIP. If a naturally stable BAD state exists, the next step may be one tightly predeclared action test. If not, the early-failure branch should be closed and research should proceed to S5.2 selective RUNNER vs PROTECT.",
    ]
    (OUT / "S5.1A_CHECKPOINT.md").write_text("\n".join(md))
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
