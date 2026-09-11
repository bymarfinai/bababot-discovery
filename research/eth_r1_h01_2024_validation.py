#!/usr/bin/env python3
"""One-shot 2024 validation for the frozen ETH R1 H01 train candidate.

This runner is intentionally NOT a search. It reads the train lock, asserts the exact
frozen candidate, evaluates that candidate once on calendar-year 2024, and applies
only the validation gate preregistered before R1 H00 began.

No alternate rule/lookback/hold is evaluated. OOS 2025+ remains closed.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_economic_first_e12a_long_13_14wib_character as e12
import eth_r1_h00_robust_train as r1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_R1_H01_ROBUST"
LOCK = ROOT / f"{PFX}_FrozenCandidate.csv"
OUT_EVENTS = ROOT / f"{PFX}_ValidationEvents.csv"
OUT_ANCHORS = ROOT / f"{PFX}_ValidationAnchors.csv"
OUT_HALVES = ROOT / f"{PFX}_ValidationHalves.csv"
OUT_SUMMARY = ROOT / f"{PFX}_ValidationSummary.csv"
OUT_RESULT = ROOT / f"{PFX}_ValidationResult.md"
OUT_STATUS = ROOT / f"{PFX}_ValidationStatus.txt"

HOUR_WIB = 1
VAL_START = pd.Timestamp("2024-01-01", tz="UTC")
VAL_END = pd.Timestamp("2025-01-01", tz="UTC")
HALVES = (
    ("2024H1", pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2024-07-01", tz="UTC")),
    ("2024H2", pd.Timestamp("2024-07-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
)


def finite(x):
    return bool(np.isfinite(x))


def pct(x):
    return "nan" if not finite(x) else f"{100.0*float(x):.2f}%"


def money(x):
    return "nan" if not finite(x) else f"${float(x):+.2f}"


def stats(T: pd.DataFrame):
    if len(T) == 0:
        return e12.summarize(np.array([]), np.array([]))
    return e12.summarize(T.net.to_numpy(float), T.gross.to_numpy(float))


def subset_stats(T: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    if len(T) == 0:
        return stats(T)
    m = (pd.DatetimeIndex(T.entry_ts) >= start) & (pd.DatetimeIndex(T.exit_ts) < end)
    return stats(T.loc[m])


def extract_validation(cache, lb: int, hold: int, rule: str):
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        pre = pd.DatetimeIndex(pre)
        ex = pd.DatetimeIndex(ex)
        m = (
            valid & (pre >= VAL_START) & (ent >= VAL_START) &
            (ex < VAL_END) & masks[rule]
        )
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "gross": float(g),
                "net": float(n),
            })
    if not rows:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "gross", "net"])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def main():
    if OUT_RESULT.exists() or OUT_STATUS.exists():
        raise RuntimeError("H01 2024 validation has already been recorded; one-shot protocol forbids rerun")
    if not LOCK.exists():
        raise RuntimeError("frozen H01 train candidate lock is missing")

    L = pd.read_csv(LOCK)
    if len(L) != 1:
        raise AssertionError(f"expected exactly one frozen candidate, got {len(L)}")
    q = L.iloc[0]

    # Hard assertions make any accidental retuning impossible in this generation.
    assert int(q.hour_wib) == 1
    assert int(q.region_id) == 1
    assert str(q.character_rule) == "EFF_HIGH__RV_LOW"
    assert int(q.lookback_min) == 240
    assert int(q.hold_min) == 360
    assert str(q.validation_opened).lower() == "false"

    lb = int(q.lookback_min)
    hold = int(q.hold_min)
    rule = str(q.character_rule)

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    if len(e12.RULES) != 90:
        raise AssertionError(f"rule grammar drift: {len(e12.RULES)}")

    e12.CLOCKS = r1.clocks_for_hour(HOUR_WIB)
    e12.LOOKBACKS = (lb,)
    e12.HOLDS = (hold,)
    cache = e12.prep(x5)

    T = extract_validation(cache, lb, hold, rule)
    s = stats(T)

    validation_pass = bool(
        s["trades"] >= 40 and
        finite(s["win_rate"]) and s["win_rate"] >= .52 and
        s["net_pnl"] > 0 and
        finite(s["expectancy"]) and s["expectancy"] > 0 and
        finite(s["pf"]) and s["pf"] >= 1.05 and
        finite(s["max_dd"]) and s["max_dd"] <= 125 and
        s["max_loss_streak"] <= 10
    )

    anchor_rows = []
    for clock in e12.CLOCKS:
        A = T.loc[T.clock == clock]
        a = stats(A)
        anchor_rows.append({
            "clock_utc_min": int(clock),
            "trades": int(a["trades"]),
            "win_rate": a["win_rate"],
            "net_pnl": a["net_pnl"],
            "expectancy": a["expectancy"],
            "pf": a["pf"],
            "max_dd": a["max_dd"],
            "max_loss_streak": int(a["max_loss_streak"]),
        })
    ADF = pd.DataFrame(anchor_rows)

    half_rows = []
    for name, start, end in HALVES:
        h = subset_stats(T, start, end)
        half_rows.append({
            "period": name,
            "trades": int(h["trades"]),
            "win_rate": h["win_rate"],
            "net_pnl": h["net_pnl"],
            "expectancy": h["expectancy"],
            "pf": h["pf"],
            "max_dd": h["max_dd"],
            "max_loss_streak": int(h["max_loss_streak"]),
        })
    HDF = pd.DataFrame(half_rows)

    summary = pd.DataFrame([{
        "hour_wib": HOUR_WIB,
        "character_rule": rule,
        "lookback_min": lb,
        "hold_min": hold,
        "train_trades": int(q.train_trades),
        "train_wr": float(q.train_wr),
        "train_exp": float(q.train_exp),
        "train_pf": float(q.train_pf),
        "validation_trades": int(s["trades"]),
        "validation_wr": s["win_rate"],
        "validation_net": s["net_pnl"],
        "validation_exp": s["expectancy"],
        "validation_pf": s["pf"],
        "validation_dd": s["max_dd"],
        "validation_ls": int(s["max_loss_streak"]),
        "validation_pass": validation_pass,
        "validation_opened": True,
        "oos_2025plus_opened": False,
    }])

    T.to_csv(OUT_EVENTS, index=False)
    ADF.to_csv(OUT_ANCHORS, index=False)
    HDF.to_csv(OUT_HALVES, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    status = "ROBUST_VALIDATED_HABITAT" if validation_pass else "VALIDATION_FAIL"
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH R1 H01 — One-shot 2024 Validation", "",
        "**Frozen candidate only. No search. OOS 2025+ CLOSED. No live authorization.**", "",
        f"Candidate: **{rule} / LB{lb} / H{hold}**.",
        f"Train reference: N {int(q.train_trades)}, WR {pct(float(q.train_wr))}, exp {money(float(q.train_exp))}, PF {float(q.train_pf):.3f}.", "",
        "## 2024 validation", "",
        f"- N: **{int(s['trades'])}**",
        f"- WR: **{pct(s['win_rate'])}**",
        f"- Net: **{money(s['net_pnl'])}**",
        f"- Expectancy: **{money(s['expectancy'])}/trade**",
        f"- PF: **{float(s['pf']):.3f}**" if finite(s['pf']) else "- PF: **nan**",
        f"- Max DD: **{money(s['max_dd'])}**",
        f"- Max loss streak: **{int(s['max_loss_streak'])}**", "",
        "Preregistered validation gate: N>=40, WR>=52%, net>0, exp>0, PF>=1.05, DD<=125, LS<=10.", "",
        f"## Verdict: **{status}**", "",
        "2024 was used only for this one frozen candidate. No alternate candidate is permitted if this validation fails. OOS 2025+ remains closed.", "",
        "## Diagnostic halves (not part of the validation gate)", "",
        "| Period | N | WR | Net | Exp | PF | DD | LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in HDF.itertuples(index=False):
        lines.append(
            f"| {r.period} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | "
            f"{money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} |"
        )
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
