#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PRIOR = ROOT / "ETH_R4B_STAGE_E_2026_YTD_CELLS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGE_I_ATR_GATE_CELLS.csv"
OUT_SUMMARY = ROOT / "ETH_R4B_STAGE_I_ATR_GATE_SUMMARY.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGE_I_ATR_GATE_Result.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGE_I_ATR_GATE_Status.txt"

EXPECTED = {(120, 240), (180, 240), (240, 240), (180, 360), (240, 360)}
HOUR = 4
RULE = "DRIVE_DOWN__STR_B80_100"
Q = 0.33
MIN_RETENTION = 0.50

PERIODS = [
    ("2022_DEV", pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2023-01-01", tz="UTC")),
    ("2023_TEST", pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC")),
    ("2024_CONFIRM", pd.Timestamp("2024-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
    ("2025_FINAL_OOS", pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")),
]


def finite(x):
    return bool(np.isfinite(x))


def metric(st, key):
    x = float(st[key])
    return x if finite(x) else np.nan


def stats(T: pd.DataFrame):
    return r1.stats_from_df(T[["entry_ts", "exit_ts", "clock", "gross", "net"]].copy())


def build_atr1h(x: pd.DataFrame) -> pd.Series:
    c = x["close"].astype(float)
    h = x["high"].astype(float)
    l = x["low"].astype(float)
    prev = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1) / prev
    # Same Stage-G feature definition. shift(1) guarantees the feature ends one 5m bar before entry.
    return tr.shift(1).rolling(12, min_periods=12).mean().rename("atr1h")


def all_events(cache, lb, hold, last_ts, atr1h):
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        ex = pd.DatetimeIndex(ex)
        m = valid & (ex <= last_ts) & masks[RULE]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            a = float(atr1h.at[entry_ts]) if entry_ts in atr1h.index and finite(atr1h.at[entry_ts]) else np.nan
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "gross": float(g),
                "net": float(n),
                "atr1h": a,
            })
    return pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "clock", "gross", "net", "atr1h"])


def summarize(T: pd.DataFrame):
    if len(T) == 0:
        return {"n": 0, "wr": np.nan, "net": 0.0, "exp": np.nan, "pf": np.nan, "dd": np.nan, "ls": 0}
    st = stats(T)
    return {
        "n": int(st["trades"]),
        "wr": metric(st, "win_rate"),
        "net": float(st["net_pnl"]),
        "exp": metric(st, "expectancy"),
        "pf": metric(st, "pf"),
        "dd": metric(st, "max_dd"),
        "ls": int(st["max_loss_streak"]),
    }


def assert_close(label, got, expected, tol=1e-6):
    if pd.isna(expected):
        return
    if not finite(got) or abs(float(got) - float(expected)) > tol:
        raise AssertionError(f"baseline mismatch {label}: got={got} expected={expected}")


def fmt_pct(x):
    return "NA" if not finite(x) else f"{100*x:.2f}%"


def fmt_money(x):
    return "NA" if not finite(x) else f"${x:+.2f}"


def fmt_num(x, d=3):
    return "NA" if not finite(x) else f"{x:.{d}f}"


def main():
    prior = pd.read_csv(PRIOR)
    if len(prior) != 5:
        raise AssertionError(f"expected 5 frozen cells, got {len(prior)}")
    if set(prior.hour_wib.astype(int)) != {HOUR}:
        raise AssertionError("frozen hour changed")
    if set(prior.character_rule.astype(str)) != {RULE}:
        raise AssertionError("frozen character changed")
    actual = set(zip(prior.lookback_min.astype(int), prior.hold_min.astype(int)))
    if actual != EXPECTED:
        raise AssertionError(f"frozen cells changed: {sorted(actual)}")

    cutoffs = pd.to_datetime(prior.dataset_last_ts_utc, utc=True).unique()
    if len(cutoffs) != 1:
        raise AssertionError("non-unique Stage-E cutoff")
    last_ts = pd.Timestamp(cutoffs[0])

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if idx.max() < last_ts:
        raise RuntimeError(f"dataset does not reach frozen cutoff: {idx.max()} < {last_ts}")
    x = x5[idx <= last_ts].copy()
    atr1h = build_atr1h(x)

    e12.CLOCKS = r1.clocks_for_hour(HOUR)
    e12.LOOKBACKS = sorted(prior.lookback_min.astype(int).unique().tolist())
    e12.HOLDS = sorted(prior.hold_min.astype(int).unique().tolist())
    cache = e12.prep(x)

    event_map = {}
    for c in prior.itertuples(index=False):
        key = (int(c.lookback_min), int(c.hold_min))
        event_map[key] = all_events(cache, *key, last_ts, atr1h)

    # Derive the only gate boundary from 2022 DEV, pooled over UNIQUE entry timestamps across
    # the five frozen cells. No PnL/outcome is used to determine this threshold.
    pooled = []
    for T in event_map.values():
        W = T[(T.entry_ts >= pd.Timestamp("2022-01-01", tz="UTC")) &
              (T.entry_ts < pd.Timestamp("2023-01-01", tz="UTC"))]
        pooled.append(W[["entry_ts", "atr1h"]])
    dev_entries = pd.concat(pooled, ignore_index=True).drop_duplicates("entry_ts").dropna(subset=["atr1h"])
    if len(dev_entries) < 30:
        raise RuntimeError(f"too few unique 2022 DEV entries for frozen ATR boundary: {len(dev_entries)}")
    atr_cut = float(dev_entries.atr1h.quantile(Q))

    # Include 2026 shadow only through the already frozen Stage-E dataset cutoff.
    periods = PERIODS + [("2026_SHADOW", pd.Timestamp("2026-01-01", tz="UTC"), last_ts + pd.Timedelta(minutes=5))]

    rows = []
    prior_idx = prior.set_index(["lookback_min", "hold_min"])
    historical_cols = {
        "2022_DEV": ("dev2022_n", "dev2022_wr", "dev2022_exp", "dev2022_pf"),
        "2023_TEST": ("test2023_n", "test2023_wr", "test2023_exp", "test2023_pf"),
        "2024_CONFIRM": ("y2024_n", "y2024_wr", "y2024_exp", "y2024_pf"),
        "2025_FINAL_OOS": ("oos2025_n", "oos2025_wr", "oos2025_exp", "oos2025_pf"),
        "2026_SHADOW": ("ytd2026_n", "ytd2026_wr", "ytd2026_exp", "ytd2026_pf"),
    }

    for period, start, end in periods:
        for lb, hold in sorted(EXPECTED, key=lambda z: (z[1], z[0])):
            T = event_map[(lb, hold)]
            B = T[(T.entry_ts >= start) & (T.entry_ts < end)].copy()
            G = B[B.atr1h > atr_cut].copy()  # operational modification: skip frozen LOW ATR regime
            bs = summarize(B)
            gs = summarize(G)

            # Reproduce the old checkpoint before allowing any gate result to be interpreted.
            p = prior_idx.loc[(lb, hold)]
            ncol, wrcol, expcol, pfcol = historical_cols[period]
            if int(bs["n"]) != int(p[ncol]):
                raise AssertionError(f"baseline N mismatch {period} LB{lb}/H{hold}: got={bs['n']} expected={p[ncol]}")
            assert_close(f"{period} LB{lb}/H{hold} WR", bs["wr"], p[wrcol], 1e-9)
            assert_close(f"{period} LB{lb}/H{hold} Exp", bs["exp"], p[expcol], 1e-8)
            assert_close(f"{period} LB{lb}/H{hold} PF", bs["pf"], p[pfcol], 1e-8)

            retained = gs["n"] / bs["n"] if bs["n"] else np.nan
            rows.append({
                "period": period,
                "lookback_min": lb,
                "hold_min": hold,
                "atr_gate": atr_cut,
                "baseline_n": bs["n"], "baseline_wr": bs["wr"], "baseline_net": bs["net"],
                "baseline_exp": bs["exp"], "baseline_pf": bs["pf"], "baseline_dd": bs["dd"], "baseline_ls": bs["ls"],
                "gated_n": gs["n"], "retained_pct": retained, "gated_wr": gs["wr"], "gated_net": gs["net"],
                "gated_exp": gs["exp"], "gated_pf": gs["pf"], "gated_dd": gs["dd"], "gated_ls": gs["ls"],
                "delta_net": gs["net"] - bs["net"],
                "delta_exp": gs["exp"] - bs["exp"] if finite(gs["exp"]) and finite(bs["exp"]) else np.nan,
                "delta_pf": gs["pf"] - bs["pf"] if finite(gs["pf"]) and finite(bs["pf"]) else np.nan,
                "delta_dd": gs["dd"] - bs["dd"] if finite(gs["dd"]) and finite(bs["dd"]) else np.nan,
            })

    C = pd.DataFrame(rows)
    C.to_csv(OUT_CELLS, index=False)

    summaries = []
    for period, W in C.groupby("period", sort=False):
        base_positive = int(((W.baseline_exp > 0) & (W.baseline_pf > 1)).sum())
        gate_positive = int(((W.gated_exp > 0) & (W.gated_pf > 1)).sum())
        improved = int(((W.delta_exp > 0) & (W.delta_pf > 0)).sum())
        summaries.append({
            "period": period,
            "atr_gate": atr_cut,
            "baseline_positive_cells": base_positive,
            "gated_positive_cells": gate_positive,
            "improved_exp_pf_cells": improved,
            "median_retained_pct": float(W.retained_pct.median()),
            "median_baseline_exp": float(W.baseline_exp.median()),
            "median_gated_exp": float(W.gated_exp.median()),
            "median_baseline_pf": float(W.baseline_pf.median()),
            "median_gated_pf": float(W.gated_pf.median()),
            "median_delta_net": float(W.delta_net.median()),
            "median_delta_exp": float(W.delta_exp.median()),
            "median_delta_pf": float(W.delta_pf.median()),
            "median_delta_dd": float(W.delta_dd.median()),
        })
    S = pd.DataFrame(summaries)
    S.to_csv(OUT_SUMMARY, index=False)

    # Operational acceptance rule, fixed before looking at output:
    # - 2023/2024/2025: >=4/5 cells remain economically positive after gating.
    # - 2026: >=3/5 cells become economically positive after gating.
    # - median trade retention >=50% in every validation/shadow period.
    # 2022 is threshold-origin year, so it is descriptive rather than acceptance evidence.
    val = S[S.period.isin(["2023_TEST", "2024_CONFIRM", "2025_FINAL_OOS"])]
    sh = S[S.period == "2026_SHADOW"].iloc[0]
    preserve = bool((val.gated_positive_cells >= 4).all())
    retention = bool((S[S.period != "2022_DEV"].median_retained_pct >= MIN_RETENTION).all())
    rescue = bool(sh.gated_positive_cells >= 3 and sh.median_gated_exp > 0 and sh.median_gated_pf > 1)

    if preserve and retention and rescue:
        status = "ATR_GATE_USE__2026_RESCUED__HISTORICAL_EDGE_PRESERVED"
        decision = "USE"
    elif preserve and retention and sh.gated_positive_cells > int(sh.baseline_positive_cells):
        status = "ATR_GATE_CANDIDATE__2026_IMPROVED_NOT_FULLY_RESCUED"
        decision = "CANDIDATE"
    else:
        status = "ATR_GATE_FAIL__DO_NOT_PROMOTE"
        decision = "FAIL"

    anchor = C[(C.lookback_min == 240) & (C.hold_min == 360)]
    lines = [
        "# ETH R4b — Stage I Frozen ATR1H Gate Operational Test",
        "",
        "**ONE MODIFICATION ONLY: skip H04 trades when pre-entry ATR1H is at/below the frozen 2022-DEV q33 boundary.**",
        "No character, lookback, hold, entry, fee, or exit rule is retuned.",
        f"Frozen ATR1H q33 from 2022 DEV unique entries: **{100*atr_cut:.4f}%** (N={len(dev_entries)} unique entry timestamps).",
        f"Dataset cutoff: **{last_ts.isoformat()}**. Coverage **{coverage:.4%}**.",
        f"Operational decision: **{decision}**.",
        f"Stage I status: **{status}**.",
        "",
        "## Five-cell panel summary",
        "",
        "| Period | Base +cells | Gated +cells | Improved Exp+PF | Median retained | Median Exp base -> gated | Median PF base -> gated | Median dNet | Median dDD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {int(r.baseline_positive_cells)}/5 | {int(r.gated_positive_cells)}/5 | "
            f"{int(r.improved_exp_pf_cells)}/5 | {fmt_pct(float(r.median_retained_pct))} | "
            f"{fmt_money(float(r.median_baseline_exp))} -> {fmt_money(float(r.median_gated_exp))} | "
            f"{fmt_num(float(r.median_baseline_pf))} -> {fmt_num(float(r.median_gated_pf))} | "
            f"{fmt_money(float(r.median_delta_net))} | {fmt_money(float(r.median_delta_dd))} |"
        )

    lines += [
        "",
        "## Canonical LB240/H360",
        "",
        "| Period | N base -> gated | Retained | WR base -> gated | Exp base -> gated | PF base -> gated | Net delta | DD base -> gated |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in anchor.itertuples(index=False):
        lines.append(
            f"| {r.period} | {int(r.baseline_n)} -> {int(r.gated_n)} | {fmt_pct(float(r.retained_pct))} | "
            f"{fmt_pct(float(r.baseline_wr))} -> {fmt_pct(float(r.gated_wr))} | "
            f"{fmt_money(float(r.baseline_exp))} -> {fmt_money(float(r.gated_exp))} | "
            f"{fmt_num(float(r.baseline_pf))} -> {fmt_num(float(r.gated_pf))} | "
            f"{fmt_money(float(r.delta_net))} | {fmt_money(float(r.baseline_dd))} -> {fmt_money(float(r.gated_dd))} |"
        )

    lines += [
        "",
        "## Locked interpretation rule",
        "",
        "- USE requires historical preservation (>=4/5 positive cells in 2023, 2024, 2025), >=50% median retention, and a 2026 rescue (>=3/5 positive cells plus positive median expectancy and PF>1).",
        "- CANDIDATE means the frozen gate improves 2026 but does not fully satisfy the rescue rule.",
        "- FAIL means do not tune the ATR threshold further in this stage; move to the next independent modification hypothesis.",
        "- 2022 is the threshold-origin year and is not counted as independent validation.",
    ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(status + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
