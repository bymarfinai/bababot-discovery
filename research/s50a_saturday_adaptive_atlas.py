#!/usr/bin/env python3
"""Saturday T-Method S5.0A — Adaptive Saturday State Atlas.

Research-only descriptive/causal state mapping. No trading rule is changed.
Frozen references remain:
- static parent: Saturday18 BUY / TP2.6 / SL1.2 / 18h
- A7.19 full-coverage champion
- A7.26 selective candidate

This atlas predeclares Saturday-native states from already established mechanisms:
1) pre-entry stretch score / frozen A7.26 stretched state,
2) 60m thesis health / frozen A7.13 failure signature,
3) causal runner maturity (+0.5 / +0.8),
4) frozen A7 fast-giveback path,
5) frozen A7.19 240m shallow-runner failure state,
6) descriptive 18h timeout health,
7) raw-vs-vol-normalized 60m separation.

No threshold search or economic action optimization is performed here.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50

OUT = Path(os.getenv("S50A_OUT", "s50a_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT_N = 83


def row_at_or_before(k: pd.DataFrame, t: pd.Timestamp):
    x = k[k.index <= t]
    return None if x.empty else x.iloc[-1]


def pre_context(k: pd.DataFrame, t: pd.Timestamp) -> dict:
    """Strict causal pre-entry context. Actual entry open is allowed; indicators end at t-5m."""
    cur_open = float(k.loc[t, "open"])
    done_t = t - pd.Timedelta(minutes=5)
    r = k.loc[done_t]
    r1 = row_at_or_before(k, t - pd.Timedelta(minutes=60))
    r4 = row_at_or_before(k, t - pd.Timedelta(minutes=240))
    r65 = row_at_or_before(k, t - pd.Timedelta(minutes=65))
    w1 = k[(k.index >= t - pd.Timedelta(minutes=60)) & (k.index < t)]
    if r1 is None or r4 is None or r65 is None or len(w1) != 12:
        raise RuntimeError(f"incomplete pre-context {t}")
    pre1 = cur_open / float(r1.close) - 1.0
    pre4 = cur_open / float(r4.close) - 1.0
    ema20 = float(r.ema20)
    ema_slope60 = ema20 / float(r65.ema20) - 1.0
    prior_high = float(w1.high.max())
    dist_below_ph = prior_high / cur_open - 1.0
    conds = [
        pre1 > 0,
        pre4 > 0,
        cur_open > ema20,
        ema_slope60 > 0,
        dist_below_ph <= 0.001,
    ]
    score = int(sum(conds))
    # Exact frozen A7.26 primary qualitative state.
    stretched = all(conds)
    # Symmetric low end is descriptive only, not a trade gate.
    pre_state = "STRETCHED" if stretched else ("PULLBACK" if score <= 1 else "NORMAL")
    return {
        "pre1": pre1,
        "pre4": pre4,
        "pre_above_ema20": cur_open > ema20,
        "pre_ema20_slope60": ema_slope60,
        "pre_dist_below_prior1h_high": dist_below_ph,
        "pre_stretch_score": score,
        "pre_state": pre_state,
    }


def prior_rv24(k: pd.DataFrame, t: pd.Timestamp) -> float:
    w = k[(k.index >= t - pd.Timedelta(hours=24)) & (k.index < t)]
    if len(w) != 288:
        return float("nan")
    c = w.close.astype(float).to_numpy()
    lr = np.diff(np.log(c))
    return float(np.sqrt(np.sum(lr * lr)))


def thesis60(k: pd.DataFrame, t: pd.Timestamp, entry: float) -> dict:
    st = s50.checkpoint_state(k, t, 60, entry)
    if st is None:
        raise RuntimeError(f"no 60m state {t}")
    # Frozen A7.13 stable failure signature; HEALTHY is its sign-symmetric comparator.
    if st["progress"] <= -0.001 and st["taker"] < 0:
        label = "FAILURE_CANDIDATE"
    elif st["progress"] >= 0.001 and st["taker"] > 0:
        label = "HEALTHY"
    else:
        label = "MIXED"
    rv = prior_rv24(k, t)
    return {
        "state60": label,
        "progress60": st["progress"],
        "taker60": st["taker"],
        "mfe60": st["mfe"],
        "mae60": st["mae"],
        "ema20_dist60": st["ema20_dist"],
        "rv24": rv,
        "progress60_rv": st["progress"] / rv if np.isfinite(rv) and rv > 0 else np.nan,
        "mfe60_rv": st["mfe"] / rv if np.isfinite(rv) and rv > 0 else np.nan,
        "mae60_rv": st["mae"] / rv if np.isfinite(rv) and rv > 0 else np.nan,
    }


def scan_runner_path(k: pd.DataFrame, t: pd.Timestamp, trade, entry: float) -> dict:
    exit_t = pd.Timestamp(trade.exit_t)
    bars = k[(k.index >= t) & (k.index < exit_t)]
    first05_t = None
    first08_t = None
    for b in bars.itertuples(index=False):
        if first05_t is None and float(b.high) / entry - 1.0 >= 0.005:
            first05_t = b.ts + pd.Timedelta(minutes=5)
        if first08_t is None and float(b.high) / entry - 1.0 >= 0.008:
            first08_t = b.ts + pd.Timedelta(minutes=5)
    if first05_t is None:
        return {
            "runner_state": "NO_0.5_IMPULSE", "first05_min": np.nan, "first08_min": np.nan,
            "giveback_state": "NO_HINGE", "giveback40_min": np.nan,
        }
    first05_min = (first05_t - t).total_seconds() / 60.0
    # First completed close <= +0.4 after the +0.5 hinge, strictly after hinge completion.
    after = k[(k.index >= first05_t) & (k.index < exit_t)]
    gb_t = None
    for b in after.itertuples(index=False):
        if float(b.close) / entry - 1.0 <= 0.004:
            gb_t = b.ts + pd.Timedelta(minutes=5)
            break
    if first08_t is not None:
        runner_state = "DEEP_RUNNER"
        first08_min = (first08_t - t).total_seconds() / 60.0
    else:
        runner_state = "SHALLOW_RUNNER"
        first08_min = np.nan
    if gb_t is not None:
        gb_min = (gb_t - first05_t).total_seconds() / 60.0
    else:
        gb_min = np.nan
    if gb_t is not None and gb_min <= 5.0:
        giveback_state = "FAST_GIVEBACK"
    elif first08_t is not None and (gb_t is None or first08_t <= gb_t):
        giveback_state = "CONTINUATION_FIRST"
    else:
        giveback_state = "NORMAL_PULLBACK"
    return {
        "runner_state": runner_state,
        "first05_min": first05_min,
        "first08_min": first08_min,
        "giveback_state": giveback_state,
        "giveback40_min": gb_min,
    }


def state240(k: pd.DataFrame, t: pd.Timestamp, trade, entry: float) -> dict:
    decision_t = t + pd.Timedelta(minutes=240)
    if pd.Timestamp(trade.exit_t) <= decision_t:
        return {"state240": "NOT_ALIVE", "progress240_open": np.nan, "mfe240": np.nan, "taker240": np.nan}
    completed = k[(k.index >= t) & (k.index < decision_t)]
    if len(completed) != 48 or decision_t not in k.index:
        raise RuntimeError(f"bad 240m window {t}")
    progress_open = float(k.loc[decision_t, "open"]) / entry - 1.0
    mfe = float(completed.high.max()) / entry - 1.0
    taker = float(np.nanmean(completed.taker_imb.to_numpy()))
    # Frozen A7.19 action state only; no action is applied here.
    failure = (mfe >= 0.005 and mfe < 0.008 and progress_open >= 0.002 and progress_open <= 0.004 and taker < 0)
    return {
        "state240": "SHALLOW_FAILURE" if failure else "PRESERVE",
        "progress240_open": progress_open,
        "mfe240": mfe,
        "taker240": taker,
    }


def timeout18_state(k: pd.DataFrame, t: pd.Timestamp, trade, entry: float) -> dict:
    if trade.reason != "TIMEOUT":
        return {"state18h": "NOT_TIMEOUT", "post18_ret6h": np.nan, "post18_mfe6h": np.nan, "post18_mae6h": np.nan}
    d = t + pd.Timedelta(hours=18)
    done_t = d - pd.Timedelta(minutes=5)
    r = k.loc[done_t]
    r60 = row_at_or_before(k, done_t - pd.Timedelta(minutes=60))
    w60 = k[(k.index >= d - pd.Timedelta(minutes=60)) & (k.index < d)]
    if r60 is None or len(w60) != 12:
        raise RuntimeError(f"bad 18h state {t}")
    above = float(r.close) > float(r.ema20)
    slope = float(r.ema20) / float(r60.ema20) - 1.0
    taker = float(np.nanmean(w60.taker_imb.to_numpy()))
    if above and slope > 0 and taker > 0:
        label = "STILL_ALIVE"
    elif (not above) and slope < 0 and taker < 0:
        label = "DEAD"
    else:
        label = "MIXED"
    # Descriptive only: what happened during the next 6h after the frozen timeout exit?
    px18 = float(r.close)
    fwd = k[(k.index >= d) & (k.index < d + pd.Timedelta(hours=6))]
    if len(fwd) == 72:
        ret6 = float(fwd.iloc[-1].close) / px18 - 1.0
        mfe6 = float(fwd.high.max()) / px18 - 1.0
        mae6 = 1.0 - float(fwd.low.min()) / px18
    else:
        ret6 = mfe6 = mae6 = np.nan
    return {"state18h": label, "post18_ret6h": ret6, "post18_mfe6h": mfe6, "post18_mae6h": mae6}


def auc_binary(y: np.ndarray, score: np.ndarray) -> float:
    mask = np.isfinite(score)
    y = y[mask].astype(int)
    score = score[mask]
    n1 = int(y.sum()); n0 = int(len(y) - n1)
    if n1 == 0 or n0 == 0:
        return float("nan")
    ranks = pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0, "wins": 0, "wr": np.nan, "pnl": 0.0, "avg": np.nan}
    wins = int((df.pnl > 0).sum())
    return {"n": len(df), "wins": wins, "wr": wins / len(df), "pnl": float(df.pnl.sum()), "avg": float(df.pnl.mean())}


def state_table(df: pd.DataFrame, col: str) -> list[dict]:
    out = []
    for state, g in df.groupby(col, dropna=False):
        d = g.iloc[:0]
        # Preserve global chronological split rather than splitting each state independently.
        disc = g[g.idx < SPLIT_N]
        val = g[g.idx >= SPLIT_N]
        r = {"state": str(state), **metrics(g)}
        dm = metrics(disc); vm = metrics(val)
        r.update({f"disc_{k}": v for k, v in dm.items()})
        r.update({f"val_{k}": v for k, v in vm.items()})
        out.append(r)
    return sorted(out, key=lambda x: (-x["n"], x["state"]))


def fmt_pct(x):
    return "NA" if not np.isfinite(x) else f"{100*x:.2f}%"


def fmt_money(x):
    return "NA" if not np.isfinite(x) else f"${x:+.3f}"


def markdown_table(rows: list[dict]) -> str:
    lines = ["| State | N | WR | PnL | Disc N/WR/PnL | Val N/WR/PnL |", "|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(
            f"| {r['state']} | {r['n']} | {fmt_pct(r['wr'])} | {fmt_money(r['pnl'])} | "
            f"{r['disc_n']} / {fmt_pct(r['disc_wr'])} / {fmt_money(r['disc_pnl'])} | "
            f"{r['val_n']} / {fmt_pct(r['val_wr'])} / {fmt_money(r['val_pnl'])} |"
        )
    return "\n".join(lines)


def main():
    k = s50.load_klines()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]
    parent = pd.DataFrame([vars(x) for x in trades])
    if len(parent) != 139 or int((parent.pnl > 0).sum()) != 65 or abs(parent.pnl.sum() - 87.20) > 0.20:
        raise RuntimeError("S5.0A parent reproduction gate failed")

    recs = []
    for idx, (t, tr) in enumerate(zip(entries, trades)):
        r = {"idx": idx, "date": tr.date, "pnl": tr.pnl, "win": tr.pnl > 0, "reason": tr.reason, "mfe_parent": tr.mfe, "mae_parent": tr.mae}
        r.update(pre_context(k, t))
        r.update(thesis60(k, t, tr.entry))
        r.update(scan_runner_path(k, t, tr, tr.entry))
        r.update(state240(k, t, tr, tr.entry))
        r.update(timeout18_state(k, t, tr, tr.entry))
        recs.append(r)
    df = pd.DataFrame(recs)
    df.to_csv(OUT / "s50a_atlas_rows.csv", index=False)

    tables = {}
    for col in ["pre_state", "pre_stretch_score", "state60", "runner_state", "giveback_state", "state240", "state18h"]:
        tables[col] = state_table(df, col)

    # Cross-period raw vs volatility-normalized discrimination at +60m.
    aucs = {}
    for label, g in [("full", df), ("discovery", df[df.idx < SPLIT_N]), ("validation", df[df.idx >= SPLIT_N])]:
        y = g.win.astype(int).to_numpy()
        aucs[label] = {
            "progress60_raw": auc_binary(y, g.progress60.to_numpy(float)),
            "progress60_rv": auc_binary(y, g.progress60_rv.to_numpy(float)),
            "mfe60_raw": auc_binary(y, g.mfe60.to_numpy(float)),
            "mfe60_rv": auc_binary(y, g.mfe60_rv.to_numpy(float)),
            "mae60_raw_loss": auc_binary(1-y, g.mae60.to_numpy(float)),
            "mae60_rv_loss": auc_binary(1-y, g.mae60_rv.to_numpy(float)),
        }

    # Route atlas; descriptive only. Keep routes with >=4 examples to avoid noise.
    df["route"] = df.pre_state + ">" + df.state60 + ">" + df.runner_state + ">" + df.giveback_state + ">" + df.state240
    routes = []
    for route, g in df.groupby("route"):
        if len(g) < 4:
            continue
        m = metrics(g)
        routes.append({"route": route, **m, "disc_n": int((g.idx < SPLIT_N).sum()), "val_n": int((g.idx >= SPLIT_N).sum())})
    routes = sorted(routes, key=lambda x: (-x["n"], x["route"]))

    # 18h timeout follow-through by health state.
    timeout_follow = []
    for st, g in df[df.state18h != "NOT_TIMEOUT"].groupby("state18h"):
        timeout_follow.append({
            "state": st, "n": len(g), "parent_wr": float(g.win.mean()), "parent_pnl": float(g.pnl.sum()),
            "post18_ret6h_mean": float(g.post18_ret6h.mean()), "post18_mfe6h_median": float(g.post18_mfe6h.median()),
            "post18_mae6h_median": float(g.post18_mae6h.median()),
        })

    summary = {
        "parent": metrics(df), "tables": tables, "aucs": aucs, "routes": routes, "timeout_follow": timeout_follow,
    }
    (OUT / "s50a_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    md = []
    md += [
        "# BTC Temporal Saturday T-Method S5.0A — Adaptive State Atlas",
        "",
        "**Status:** DESCRIPTIVE/CAUSAL ATLAS COMPLETE — NO NEW TRADE RULE PROMOTED",
        "**Frozen parent:** Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h",
        "**Sample:** 139 occurrences; discovery first83 / validation last56",
        "**Important:** A7.19 and A7.26 remain untouched benchmarks. S5.0A applies no management action and performs no threshold search.",
        "",
        "## Parent reproduction",
        f"- N 139 / wins {int(df.win.sum())} / losses {int((~df.win).sum())}",
        f"- WR {100*df.win.mean():.2f}% / PnL {fmt_money(df.pnl.sum())}",
        "",
        "## 1. Pre-entry adaptive state",
        "STRETCHED is the exact frozen A7.26 qualitative conjunction. PULLBACK is the symmetric low-end stretch-score state; NORMAL is everything between. No entry is skipped.",
        markdown_table(tables["pre_state"]),
        "",
        "### Stretch-score gradient (0..5)",
        markdown_table(tables["pre_stretch_score"]),
        "",
        "## 2. +60m thesis health",
        "FAILURE_CANDIDATE = frozen A7.13 signature: progress <= -0.10% and cumulative taker edge <0. HEALTHY is the sign-symmetric comparator; MIXED is all else. No CUT/FLIP is applied.",
        markdown_table(tables["state60"]),
        "",
        "## 3. Runner maturity",
        markdown_table(tables["runner_state"]),
        "",
        "## 4. Post-0.5 path / giveback speed",
        "FAST_GIVEBACK uses the pre-existing A7 C1 concept: after first +0.5 hinge, completed close gives back to <=+0.4 within 5m. CONTINUATION_FIRST reaches +0.8 before that giveback; NORMAL_PULLBACK is the remainder.",
        markdown_table(tables["giveback_state"]),
        "",
        "## 5. Frozen A7.19 state at +240m (classification only)",
        markdown_table(tables["state240"]),
        "",
        "## 6. +18h timeout health (descriptive only)",
        "STILL_ALIVE requires price above EMA20 + rising EMA20 + positive recent taker flow; DEAD is the all-bearish mirror; MIXED is the remainder. Parent still exits at 18h in all economics above.",
        markdown_table(tables["state18h"]),
        "",
        "### Next-6h behavior after frozen timeout exit",
    ]
    for r in timeout_follow:
        md.append(f"- {r['state']}: N{r['n']}, next6h mean return {fmt_pct(r['post18_ret6h_mean'])}, median MFE {fmt_pct(r['post18_mfe6h_median'])}, median MAE {fmt_pct(r['post18_mae6h_median'])}")
    md += ["", "## 7. Fixed-percent vs volatility-normalized +60m information", "AUC >0.5 means larger value ranks the target class more often. No threshold is selected."]
    for label, vals in aucs.items():
        md.append(f"- {label}: progress raw {vals['progress60_raw']:.3f} vs RV-normalized {vals['progress60_rv']:.3f}; MFE raw {vals['mfe60_raw']:.3f} vs norm {vals['mfe60_rv']:.3f}; MAE-for-loss raw {vals['mae60_raw_loss']:.3f} vs norm {vals['mae60_rv_loss']:.3f}")
    md += ["", "## 8. Most common dynamic routes (N>=4; descriptive only)"]
    for r in routes[:20]:
        md.append(f"- N{r['n']} / WR {100*r['wr']:.1f}% / PnL {fmt_money(r['pnl'])} / D{r['disc_n']} V{r['val_n']}: `{r['route']}`")
    md += [
        "",
        "## Research guardrail",
        "This atlas is a state map, not a strategy selection pass. Do not choose a new management rule merely because one state has attractive same-sample economics. The next S5.1 experiments may use these predeclared states as context, while A7.19/A7.26 remain preserved benchmarks.",
    ]
    (OUT / "S5.0A_CHECKPOINT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
