#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as data
import sol_economic_first_h00_long_07_08wib_character as engine


ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_DD15_SHORTLIST_VALIDATION"
PARTITIONS = ("development", "external", "reference_validation")
OOS_PARTITIONS = ("external", "reference_validation")
EXPECTED = ROOT / "SOL_ECONOMIC_FIRST_DD15_PASSERS.csv"

CANDIDATES = (
    ("H15", 15, "22:00-23:00", "EFF_HIGH__RANGE_LOW", 240, 960, "prior_oos_locked"),
    ("H17", 17, "00:00-01:00", "EFF_LOW__RANGE_HIGH", 30, 720, "fresh_oos"),
    ("H18", 18, "01:00-02:00", "RV_HIGH__RANGE_MID", 120, 720, "fresh_oos"),
    ("H20", 20, "03:00-04:00", "DRIVE_UP__STR_B80_100", 360, 960, "fresh_oos"),
    ("H21", 21, "04:00-05:00", "DRIVE_UP__RV_HIGH", 360, 960, "fresh_oos"),
    ("H22", 22, "05:00-06:00", "EFF_LOW__EXT_MID", 240, 360, "prior_oos_locked"),
    ("H23", 23, "06:00-07:00", "DRIVE_DOWN__STR_B80_100", 15, 120, "prior_oos_locked"),
)


def summarize(trades: pd.DataFrame) -> dict:
    if not len(trades):
        return engine.summarize(np.array([]), np.array([]))
    return engine.summarize(trades.net.to_numpy(float), trades.gross.to_numpy(float))


def partition_checks(stats: dict) -> dict[str, bool]:
    return {
        "N>=40": stats["trades"] >= 40,
        "WR>=52%": np.isfinite(stats["win_rate"]) and stats["win_rate"] >= .52,
        "net>0": stats["net_pnl"] > 0,
        "exp>0": np.isfinite(stats["expectancy"]) and stats["expectancy"] > 0,
        "PF>=1.05": np.isfinite(stats["pf"]) and stats["pf"] >= 1.05,
        "DD<=125": np.isfinite(stats["max_dd"]) and stats["max_dd"] <= 125,
        "loss_streak<=10": stats["max_loss_streak"] <= 10,
    }


def pooled_checks(stats: dict) -> dict[str, bool]:
    dd_ratio = stats["max_dd"] / stats["net_pnl"] if stats["net_pnl"] > 0 else np.inf
    return {
        "N>=160": stats["trades"] >= 160,
        "WR>55%": np.isfinite(stats["win_rate"]) and stats["win_rate"] > .55,
        "net>0": stats["net_pnl"] > 0,
        "exp>=0.50": np.isfinite(stats["expectancy"]) and stats["expectancy"] >= .50,
        "PF>=1.20": np.isfinite(stats["pf"]) and stats["pf"] >= 1.20,
        "DD/net<=15%": np.isfinite(dd_ratio) and dd_ratio <= .15,
        "loss_streak<=8": stats["max_loss_streak"] <= 8,
    }


def fail_names(prefix: str, checks: dict[str, bool]) -> list[str]:
    return [f"{prefix}:{name}" for name, passed in checks.items() if not passed]


def candidate_dict(row: tuple) -> dict:
    hour, hour_num, wib, rule, lookback, hold, provenance = row
    return {
        "hour": hour, "hour_num": hour_num,
        "utc": f"{hour_num:02d}:00-{(hour_num + 1) % 24:02d}:00", "wib": wib,
        "clocks": tuple(hour_num * 60 + q for q in (0, 15, 30, 45)),
        "rule": rule, "lookback": lookback, "hold": hold, "oos_provenance": provenance,
    }


def trades_for_partition(x5: pd.DataFrame, candidate: dict, partition: str) -> tuple[pd.DataFrame, list[dict]]:
    start, end = data.PARTS[partition]
    pieces: list[pd.DataFrame] = []
    anchors: list[dict] = []
    for clock in candidate["clocks"]:
        frame = engine.state_frame(x5, clock, candidate["lookback"])
        masks = engine.masks_for_frame(frame)
        exit_ts, valid, returns = engine.hold_returns(x5, frame, candidate["hold"])
        entry_ts = pd.DatetimeIndex(frame.entry_ts)
        pre_ts = pd.DatetimeIndex(frame.pre_ts)
        selected = valid & (pre_ts >= start) & (entry_ts >= start) & (exit_ts < end) & masks[candidate["rule"]]
        gross = engine.NOTIONAL * returns[selected]
        net = gross - engine.FEE
        if len(net):
            pieces.append(pd.DataFrame({
                "hour": candidate["hour"], "partition": partition,
                "clock_utc": engine.hhmm(clock), "clock_wib": engine.wib(clock),
                "entry_ts": entry_ts[selected], "exit_ts": exit_ts[selected],
                "gross": gross, "net": net,
            }))
        stats = engine.summarize(net, gross)
        anchors.append({
            "hour": candidate["hour"], "partition": partition,
            "clock_utc": engine.hhmm(clock), "clock_wib": engine.wib(clock),
            **stats, **{f"check_{k}": v for k, v in partition_checks(stats).items()},
            "supportive": all(partition_checks(stats).values()),
        })
    trades = pd.concat(pieces, ignore_index=True).sort_values(["entry_ts", "clock_utc"]) if pieces else pd.DataFrame()
    return trades.reset_index(drop=True), anchors


def development_reconciles(expected: pd.DataFrame, c: dict, stats: dict) -> bool:
    row = expected[(expected.hour == c["hour_num"]) & (expected.character_rule == c["rule"])
                   & (expected.lookback_min == c["lookback"]) & (expected.hold_min == c["hold"])]
    if len(row) != 1:
        return False
    r = row.iloc[0]
    return bool(
        stats["trades"] == int(r.trades)
        and np.isclose(stats["win_rate"], r.win_rate, atol=1e-12)
        and np.isclose(stats["net_pnl"], r.net_pnl, atol=1e-8)
        and np.isclose(stats["max_dd"], r.max_dd, atol=1e-8)
    )


def main() -> None:
    data.synthetic_tests()
    expected = pd.read_csv(EXPECTED)
    x5, coverage = data.load5("SOLUSDT")
    summary_rows, partition_rows, anchor_rows, year_rows, trade_frames = [], [], [], [], []

    for frozen in CANDIDATES:
        c = candidate_dict(frozen)
        by_partition: dict[str, pd.DataFrame] = {}
        partition_gate: dict[str, bool] = {}
        for partition in PARTITIONS:
            trades, anchors = trades_for_partition(x5, c, partition)
            by_partition[partition] = trades
            trade_frames.append(trades)
            anchor_rows.extend(anchors)
            stats = summarize(trades)
            checks = partition_checks(stats)
            partition_gate[partition] = all(checks.values())
            partition_rows.append({
                **{k: c[k] for k in ("hour", "utc", "wib", "rule", "lookback", "hold", "oos_provenance")},
                "partition": partition, **stats,
                "dd_ratio": stats["max_dd"] / stats["net_pnl"] if stats["net_pnl"] > 0 else np.inf,
                "gate": all(checks.values()), "fail_reasons": ";".join(fail_names(partition, checks)),
            })

        dev_stats = summarize(by_partition["development"])
        reconciled = development_reconciles(expected, c, dev_stats)
        oos = pd.concat([by_partition[p] for p in OOS_PARTITIONS], ignore_index=True).sort_values(["entry_ts", "clock_utc"]).reset_index(drop=True)
        oos_stats = summarize(oos)
        pool_checks = pooled_checks(oos_stats)

        local_rows = []
        for clock in (engine.hhmm(v) for v in c["clocks"]):
            a = oos[oos.clock_utc == clock]
            s = summarize(a)
            checks = partition_checks(s)
            local_rows.append((s["trades"] >= 40, all(checks.values())))
            anchor_rows.append({
                "hour": c["hour"], "partition": "combined_oos", "clock_utc": clock,
                "clock_wib": engine.wib(int(clock[:2]) * 60 + int(clock[3:])),
                **s, **{f"check_{k}": v for k, v in checks.items()}, "supportive": all(checks.values()),
            })
        evaluable = sum(int(v[0]) for v in local_rows)
        supportive = sum(int(v[1]) for v in local_rows)
        anchor_gate = evaluable >= 3 and supportive >= 3

        for partition in OOS_PARTITIONS:
            t = by_partition[partition]
            if len(t):
                for year in sorted(pd.DatetimeIndex(t.entry_ts).year.unique()):
                    y = t[pd.DatetimeIndex(t.entry_ts).year == year]
                    year_rows.append({"hour": c["hour"], "partition": partition, "year": int(year), **summarize(y)})

        failures = []
        if not reconciled: failures.append("development_reconciliation")
        for partition in OOS_PARTITIONS:
            failures += fail_names(partition, partition_checks(summarize(by_partition[partition])))
        failures += fail_names("combined_oos", pool_checks)
        if not anchor_gate: failures.append(f"anchor_local:{supportive}/{evaluable}_supportive")

        sample_only = all(
            (":N>=" in f) or f.startswith("anchor_local:")
            for f in failures
        ) if failures else False
        if not reconciled:
            verdict = "RECONCILIATION_FAIL"
        elif not failures:
            verdict = "VALIDATED"
        elif sample_only:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "FAILED"

        summary_rows.append({
            **{k: c[k] for k in ("hour", "utc", "wib", "rule", "lookback", "hold", "oos_provenance")},
            **oos_stats,
            "dd_ratio": oos_stats["max_dd"] / oos_stats["net_pnl"] if oos_stats["net_pnl"] > 0 else np.inf,
            "development_reconciled": reconciled,
            "external_gate": partition_gate["external"],
            "reference_validation_gate": partition_gate["reference_validation"],
            "combined_oos_gate": all(pool_checks.values()),
            "evaluable_anchors": evaluable, "supportive_anchors": supportive,
            "anchor_local_gate": anchor_gate, "verdict": verdict,
            "fail_reasons": ";".join(failures) if failures else "PASS",
        })

    summary = pd.DataFrame(summary_rows)
    partitions = pd.DataFrame(partition_rows)
    anchors = pd.DataFrame(anchor_rows)
    years = pd.DataFrame(year_rows)
    trades = pd.concat(trade_frames, ignore_index=True)
    summary.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    partitions.to_csv(ROOT / f"{PFX}_Partitions.csv", index=False)
    anchors.to_csv(ROOT / f"{PFX}_Anchors.csv", index=False)
    years.to_csv(ROOT / f"{PFX}_Years.csv", index=False)
    trades.to_csv(ROOT / f"{PFX}_Trades.csv", index=False)

    valid = int((summary.verdict == "VALIDATED").sum())
    status = f"SOL_DD15_SHORTLIST_{valid}_OF_7_VALIDATED"
    (ROOT / f"{PFX}_Status.txt").write_text(status + "\n")
    lines = [
        "# SOL DD15 — Frozen Shortlist Validation Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.", "",
        "Seven frozen rank-1 candidates were evaluated without rescanning or substitution. H15/H22/H23 reuse already-opened locked OOS evidence; H17/H18/H20/H21 are the newly opened rescued candidates.", "",
        "| H | WIB | Character | LB/Hold | OOS N | WR | Net | Exp | PF | DD/Net | L-streak | Ext | RefVal | Pool | Anchors | Verdict |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {r.hour} | {r.wib} | {r.rule} | {int(r.lookback)}m/{int(r.hold)}m | {int(r.trades)} | "
            f"{100*r.win_rate:.2f}% | ${r.net_pnl:+.2f} | ${r.expectancy:+.2f} | {r.pf:.3f} | "
            f"{100*r.dd_ratio:.2f}% | {int(r.max_loss_streak)} | {'PASS' if r.external_gate else 'FAIL'} | "
            f"{'PASS' if r.reference_validation_gate else 'FAIL'} | {'PASS' if r.combined_oos_gate else 'FAIL'} | "
            f"{int(r.supportive_anchors)}/{int(r.evaluable_anchors)} | **{r.verdict}** |"
        )
    lines += ["", "## Exact failure reasons", ""]
    for r in summary.itertuples(index=False):
        lines.append(f"- **{r.hour}:** {r.fail_reasons}")
    lines += ["", f"**Status: {status}**", "",
              "Stop here. No new hour, rule, threshold, anchor subset, exit, or replacement candidate is authorized by this run.",
              "Research/shadow only; no live-trading authorization."]
    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n")
    print((ROOT / f"{PFX}_Result.md").read_text())


if __name__ == "__main__":
    main()
