#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B28M_FROZEN_OOS_VALIDATION"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_METRICS = ROOT / f"{PFX}_Metrics.csv"
OUT_ANCHORS = ROOT / f"{PFX}_AnchorAtlas.csv"
OUT_TRADES = ROOT / f"{PFX}_Trades.csv"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCKS = (300, 315, 330, 345)  # 05:00..05:45 UTC = 12:00..12:45 WIB
LB = 30
HOLD = 360
RULE = "RV_MID__RANGE_HIGH"
PRIMARY_PARTS = ("external", "reference_validation")
SHADOW_PART = "august"

NOTIONAL = 500.0
FEE = 0.75


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def extract_partition(cache, part: str) -> pd.DataFrame:
    pa, pz = base.PARTS[part]
    rows = []
    for clock in CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, LB, HOLD)]
        m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & masks[RULE]
        idx = np.flatnonzero(m)
        if len(idx) == 0:
            continue
        gross = NOTIONAL * delta[m]
        net = gross - FEE
        for j, g, n in zip(idx, gross, net):
            rows.append({
                "partition": part,
                "clock": int(clock),
                "entry_ts": pd.Timestamp(ent[j]),
                "pre_ts": pd.Timestamp(pre[j]),
                "exit_ts": pd.Timestamp(ex[j]),
                "gross_pnl": float(g),
                "net_pnl": float(n),
            })
    if not rows:
        return pd.DataFrame(columns=[
            "partition", "clock", "entry_ts", "pre_ts", "exit_ts", "gross_pnl", "net_pnl"
        ])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def summarize(T: pd.DataFrame) -> dict:
    if len(T) == 0:
        return engine.summarize(np.array([]), np.array([]))
    return engine.summarize(T.net_pnl.to_numpy(float), T.gross_pnl.to_numpy(float))


def metric_row(name: str, T: pd.DataFrame) -> dict:
    s = summarize(T)
    return {"scope": name, **s}


def partition_gate(s: dict) -> bool:
    return bool(
        s["trades"] >= 40 and np.isfinite(s["win_rate"]) and s["win_rate"] >= .52 and
        s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] > 0 and
        np.isfinite(s["pf"]) and s["pf"] >= 1.05
    )


def pooled_gate(s: dict) -> bool:
    return bool(
        s["trades"] >= 160 and np.isfinite(s["win_rate"]) and s["win_rate"] >= .55 and
        s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] >= .50 and
        np.isfinite(s["pf"]) and s["pf"] >= 1.20 and
        np.isfinite(s["max_dd"]) and s["max_dd"] <= 125 and
        s["max_loss_streak"] <= 8
    )


def anchor_atlas(T: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for clock in CLOCKS:
        q = T[T.clock == clock].sort_values(["entry_ts", "clock"]).reset_index(drop=True)
        s = summarize(q)
        evaluable = bool(s["trades"] >= 40)
        supportive = bool(
            evaluable and np.isfinite(s["win_rate"]) and s["win_rate"] >= .52 and
            s["net_pnl"] > 0 and np.isfinite(s["expectancy"]) and s["expectancy"] > 0 and
            np.isfinite(s["pf"]) and s["pf"] >= 1.05 and
            np.isfinite(s["max_dd"]) and s["max_dd"] <= 125 and
            s["max_loss_streak"] <= 10
        )
        rows.append({
            "clock_utc": engine.e11.hhmm(clock),
            "clock_wib": engine.e11.wib(clock),
            **s,
            "evaluable": evaluable,
            "supportive": supportive,
        })
    return pd.DataFrame(rows)


def year_rows(T: pd.DataFrame) -> list[dict]:
    rows = []
    if len(T) == 0:
        return rows
    years = sorted(pd.DatetimeIndex(T.entry_ts).year.unique())
    for y in years:
        q = T[pd.DatetimeIndex(T.entry_ts).year == y]
        rows.append({"scope": f"YEAR_{int(y)}", **summarize(q)})
    return rows


def main():
    # Freeze the exact B28M habitat into the already-used Development engine.
    engine.CLOCKS = CLOCKS
    base.synthetic_tests()

    x5, coverage = base.load5("BNBUSDT")
    cache = engine.prep(x5)

    frames = {p: extract_partition(cache, p) for p in (*PRIMARY_PARTS, SHADOW_PART)}
    primary = pd.concat([frames[p] for p in PRIMARY_PARTS], ignore_index=True)
    primary = primary.sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    shadow = frames[SHADOW_PART].sort_values(["entry_ts", "clock"]).reset_index(drop=True)

    all_out = pd.concat([frames[p] for p in (*PRIMARY_PARTS, SHADOW_PART)], ignore_index=True)
    all_out = all_out.sort_values(["entry_ts", "clock"]).reset_index(drop=True)
    all_out.to_csv(OUT_TRADES, index=False)

    duplicate_identity = bool(all_out.duplicated(["entry_ts", "clock"]).any())
    data_gate = bool(coverage >= .995 and not duplicate_identity)

    part_summaries = {p: summarize(frames[p]) for p in PRIMARY_PARTS}
    pooled_summary = summarize(primary)
    shadow_summary = summarize(shadow)

    metrics_rows = [metric_row(p, frames[p]) for p in PRIMARY_PARTS]
    metrics_rows.append({"scope": "POOLED_PRIMARY_OOS", **pooled_summary})
    metrics_rows.append({"scope": "AUGUST_SHADOW", **shadow_summary})
    metrics_rows.extend(year_rows(primary))
    metrics = pd.DataFrame(metrics_rows)
    metrics.to_csv(OUT_METRICS, index=False)

    atlas = anchor_atlas(primary)
    atlas.to_csv(OUT_ANCHORS, index=False)
    evaluable_anchors = int(atlas.evaluable.sum())
    supportive_anchors = int(atlas.supportive.sum())
    anchor_gate = bool(evaluable_anchors >= 3 and supportive_anchors >= 3)

    partition_gates = {p: partition_gate(part_summaries[p]) for p in PRIMARY_PARTS}
    p_gate = pooled_gate(pooled_summary)

    if not data_gate:
        status = "BNB_B28M_OOS_DATA_TOOLING_FAILURE"
    elif all(partition_gates.values()) and p_gate and anchor_gate:
        status = "BNB_B28M_OOS_PASS"
    else:
        status = "BNB_B28M_OOS_FUNDAMENTAL_REJECT"

    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# BNB B28M — Frozen OOS Validation Result",
        "",
        f"**Status: {status}**",
        "",
        "## Frozen identity",
        "",
        f"- BNBUSDT LONG, 12:00–13:00 WIB",
        f"- Character `{RULE}` / LB{LB} / hold{HOLD}m",
        f"- Notional ${NOTIONAL:.0f}; cost ${FEE:.2f}/trade",
        "- No OOS tuning or candidate ranking performed.",
        "",
        "## Data / anti-leak",
        "",
        f"- Frozen loader range: {base.START} to {base.END}",
        f"- Loaded observed range: {x5.index.min()} to {x5.index.max()}",
        f"- Raw 5m coverage: {coverage:.6%}",
        f"- Duplicate `(entry_ts, clock)` identities: {duplicate_identity}",
        f"- Data integrity gate: {'PASS' if data_gate else 'FAIL'}",
        "- Primary OOS: `external + reference_validation` only.",
        "- August 2026 is shadow-only and cannot change the decision.",
        "",
        "## Primary OOS metrics",
        "",
        "| Scope | N | WR | Net | Exp | PF | DD | Loss streak | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for p in PRIMARY_PARTS:
        s = part_summaries[p]
        lines.append(
            f"| {p} | {int(s['trades'])} | {pct(s['win_rate'])} | {money(s['net_pnl'])} | "
            f"{money(s['expectancy'])} | {float(s['pf']):.3f} | {money(s['max_dd'])} | "
            f"{int(s['max_loss_streak'])} | {'PASS' if partition_gates[p] else 'FAIL'} |"
        )
    s = pooled_summary
    lines.append(
        f"| **POOLED_PRIMARY_OOS** | **{int(s['trades'])}** | **{pct(s['win_rate'])}** | **{money(s['net_pnl'])}** | "
        f"**{money(s['expectancy'])}** | **{float(s['pf']):.3f}** | **{money(s['max_dd'])}** | "
        f"**{int(s['max_loss_streak'])}** | **{'PASS' if p_gate else 'FAIL'}** |"
    )

    lines += [
        "",
        "## Pooled primary-OOS quarter-hour anchors",
        "",
        "| UTC | WIB | N | WR | Net | Exp | PF | DD | Loss streak | Evaluable | Supportive |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in atlas.itertuples(index=False):
        lines.append(
            f"| {r.clock_utc} | {r.clock_wib} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
            f"{money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | "
            f"{'YES' if r.evaluable else 'NO'} | {'YES' if r.supportive else 'NO'} |"
        )
    lines += [
        "",
        f"Anchor gate: **{'PASS' if anchor_gate else 'FAIL'}** ({supportive_anchors}/{evaluable_anchors} supportive/evaluable).",
        "",
        "## August 2026 shadow diagnostic — not a decision gate",
        "",
        f"N {int(shadow_summary['trades'])}, WR {pct(shadow_summary['win_rate'])}, net {money(shadow_summary['net_pnl'])}, "
        f"exp {money(shadow_summary['expectancy'])}, PF {float(shadow_summary['pf']):.3f}, "
        f"DD {money(shadow_summary['max_dd'])}, loss streak {int(shadow_summary['max_loss_streak'])}.",
        "",
        "## Frozen decision",
        "",
        f"- External partition gate: **{'PASS' if partition_gates['external'] else 'FAIL'}**",
        f"- Reference-validation gate: **{'PASS' if partition_gates['reference_validation'] else 'FAIL'}**",
        f"- Pooled economics/risk gate: **{'PASS' if p_gate else 'FAIL'}**",
        f"- Anchor-stability gate: **{'PASS' if anchor_gate else 'FAIL'}**",
        f"- Final: **{status}**",
        "",
        "No live orders were placed. Research/shadow validation only.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
