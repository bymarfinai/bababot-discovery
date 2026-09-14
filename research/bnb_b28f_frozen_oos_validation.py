#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B28F_FROZEN_OOS_VALIDATION"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_METRICS = ROOT / f"{PFX}_Metrics.csv"
OUT_ANCHORS = ROOT / f"{PFX}_AnchorAtlas.csv"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (1320, 1335, 1350, 1365)
LB = 120
HOLD = 720
RULE = "DRIVE_DOWN__STR_B60_80"
PRIMARY_PARTS = ("external", "reference_validation")
SHADOW_PART = "august"
NOTIONAL = 500.0
FEE = 0.75


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def extract_partition(cache, part):
    pa, pz = base.PARTS[part]
    rows = []
    for clock in CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, LB, HOLD)]
        m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & masks[RULE]
        idx = np.flatnonzero(m)
        gross = NOTIONAL * delta[m]
        net = gross - FEE
        for j, g, n in zip(idx, gross, net):
            rows.append({"partition": part, "clock": int(clock), "entry_ts": pd.Timestamp(ent[j]),
                         "pre_ts": pd.Timestamp(pre[j]), "exit_ts": pd.Timestamp(ex[j]),
                         "gross_pnl": float(g), "net_pnl": float(n)})
    cols = ["partition", "clock", "entry_ts", "pre_ts", "exit_ts", "gross_pnl", "net_pnl"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def summarize(T):
    if len(T) == 0:
        return engine.summarize(np.array([]), np.array([]))
    return engine.summarize(T.net_pnl.to_numpy(float), T.gross_pnl.to_numpy(float))


def partition_gate(s):
    return bool(s["trades"] >= 40 and np.isfinite(s["win_rate"]) and s["win_rate"] >= .52 and
                s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] > 0 and
                np.isfinite(s["pf"]) and s["pf"] >= 1.05)


def pooled_gate(s):
    return bool(s["trades"] >= 160 and np.isfinite(s["win_rate"]) and s["win_rate"] >= .55 and
                s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] >= .50 and
                np.isfinite(s["pf"]) and s["pf"] >= 1.20 and
                np.isfinite(s["max_dd"]) and s["max_dd"] <= 125 and s["max_loss_streak"] <= 8)


def anchor_atlas(T):
    rows = []
    for clock in CLOCKS:
        q = T[T.clock == clock].sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        s = summarize(q)
        evaluable = bool(s["trades"] >= 40)
        supportive = bool(evaluable and np.isfinite(s["win_rate"]) and s["win_rate"] >= .52 and
                          s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] > 0 and
                          np.isfinite(s["pf"]) and s["pf"] >= 1.05 and
                          np.isfinite(s["max_dd"]) and s["max_dd"] <= 125 and s["max_loss_streak"] <= 10)
        rows.append({"clock_utc": engine.e11.hhmm(clock), "clock_wib": engine.e11.wib(clock),
                     **s, "evaluable": evaluable, "supportive": supportive})
    return pd.DataFrame(rows)


def main():
    engine.CLOCKS = CLOCKS
    base.synthetic_tests()
    x5, coverage = base.load5("BNBUSDT")
    cache = engine.prep(x5)
    frames = {p: extract_partition(cache, p) for p in (*PRIMARY_PARTS, SHADOW_PART)}
    primary = pd.concat([frames[p] for p in PRIMARY_PARTS], ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    shadow = frames[SHADOW_PART].sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    all_out = pd.concat([frames[p] for p in (*PRIMARY_PARTS, SHADOW_PART)], ignore_index=True).sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    all_out.to_csv(OUT_TRADES, index=False)

    duplicate_identity = bool(all_out.duplicated(["entry_ts", "clock"]).any())
    data_gate = bool(coverage >= .995 and not duplicate_identity)
    part_s = {p: summarize(frames[p]) for p in PRIMARY_PARTS}
    pooled_s = summarize(primary)
    shadow_s = summarize(shadow)
    p_gates = {p: partition_gate(part_s[p]) for p in PRIMARY_PARTS}
    pooled_ok = pooled_gate(pooled_s)
    atlas = anchor_atlas(primary)
    atlas.to_csv(OUT_ANCHORS, index=False)
    eval_n = int(atlas.evaluable.sum())
    support_n = int(atlas.supportive.sum())
    anchor_ok = bool(eval_n >= 3 and support_n >= 3)

    metrics = [{"scope": p, **part_s[p]} for p in PRIMARY_PARTS]
    metrics += [{"scope": "POOLED_PRIMARY_OOS", **pooled_s}, {"scope": "AUGUST_SHADOW", **shadow_s}]
    pd.DataFrame(metrics).to_csv(OUT_METRICS, index=False)

    if not data_gate:
        status = "BNB_B28F_OOS_DATA_TOOLING_FAILURE"
    elif all(p_gates.values()) and pooled_ok and anchor_ok:
        status = "BNB_B28F_OOS_PASS"
    else:
        status = "BNB_B28F_OOS_FUNDAMENTAL_REJECT"
    OUT_STATUS.write_text(status + "\n")

    lines = ["# BNB B28F — Frozen OOS Validation Result", "", f"**Status: {status}**", "",
             "## Frozen identity", "", f"- BNBUSDT LONG, 05:00–06:00 WIB",
             f"- Character `{RULE}` / LB{LB} / hold{HOLD}m", f"- Notional ${NOTIONAL:.0f}; cost ${FEE:.2f}/trade",
             "- No OOS tuning or candidate ranking performed.", "", "## Data / anti-leak", "",
             f"- Raw 5m coverage: {coverage:.6%}", f"- Duplicate `(entry_ts, clock)` identities: {duplicate_identity}",
             f"- Data integrity gate: {'PASS' if data_gate else 'FAIL'}", "", "## Primary OOS metrics", "",
             "| Scope | N | WR | Net | Exp | PF | DD | Loss streak | Gate |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for p in PRIMARY_PARTS:
        s = part_s[p]
        lines.append(f"| {p} | {int(s['trades'])} | {pct(s['win_rate'])} | {money(s['net_pnl'])} | {money(s['expectancy'])} | {float(s['pf']):.3f} | {money(s['max_dd'])} | {int(s['max_loss_streak'])} | {'PASS' if p_gates[p] else 'FAIL'} |")
    s = pooled_s
    lines.append(f"| **POOLED_PRIMARY_OOS** | **{int(s['trades'])}** | **{pct(s['win_rate'])}** | **{money(s['net_pnl'])}** | **{money(s['expectancy'])}** | **{float(s['pf']):.3f}** | **{money(s['max_dd'])}** | **{int(s['max_loss_streak'])}** | **{'PASS' if pooled_ok else 'FAIL'}** |")
    lines += ["", "## Pooled primary-OOS quarter-hour anchors", "",
              "| UTC | WIB | N | WR | Net | Exp | PF | DD | Loss streak | Evaluable | Supportive |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in atlas.itertuples(index=False):
        lines.append(f"| {r.clock_utc} | {r.clock_wib} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'YES' if r.evaluable else 'NO'} | {'YES' if r.supportive else 'NO'} |")
    lines += ["", f"Anchor gate: **{'PASS' if anchor_ok else 'FAIL'}** ({support_n}/{eval_n} supportive/evaluable).", "",
              "## August 2026 shadow diagnostic — not a decision gate", "",
              f"N {int(shadow_s['trades'])}, WR {pct(shadow_s['win_rate'])}, net {money(shadow_s['net_pnl'])}, exp {money(shadow_s['expectancy'])}, PF {float(shadow_s['pf']):.3f}, DD {money(shadow_s['max_dd'])}, loss streak {int(shadow_s['max_loss_streak'])}.", "",
              "## Frozen decision", "", f"- External partition gate: **{'PASS' if p_gates['external'] else 'FAIL'}**",
              f"- Reference-validation gate: **{'PASS' if p_gates['reference_validation'] else 'FAIL'}**",
              f"- Pooled economics/risk gate: **{'PASS' if pooled_ok else 'FAIL'}**",
              f"- Anchor-stability gate: **{'PASS' if anchor_ok else 'FAIL'}**", f"- Final: **{status}**", "",
              "No live orders were placed. Research/shadow validation only."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
