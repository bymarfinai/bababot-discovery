#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PRIOR = ROOT / "ETH_R4B_STAGE_E_2026_YTD_CELLS.csv"
OUT_CELLS = ROOT / "ETH_R4B_STAGE_F_2026_TEMPORAL_CELLS.csv"
OUT_PAIRS = ROOT / "ETH_R4B_STAGE_F_2026_HORIZON_PAIRS.csv"
OUT_RESULT = ROOT / "ETH_R4B_STAGE_F_2026_TEMPORAL_Result.md"
OUT_STATUS = ROOT / "ETH_R4B_STAGE_F_2026_TEMPORAL_Status.txt"
EXPECTED = {(120,240),(180,240),(240,240),(180,360),(240,360)}
HOUR = 4
RULE = "DRIVE_DOWN__STR_B80_100"

# Pre-registered temporal cuts. Primary windows are deliberately broad enough to
# retain useful event counts. Quarterly windows are secondary localization only.
WINDOWS = [
    ("P1_JAN_APR", "primary", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-05-01", tz="UTC")),
    ("P2_MAY_AUG", "primary", pd.Timestamp("2026-05-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")),
    ("Q1_JAN_MAR", "secondary", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-04-01", tz="UTC")),
    ("Q2_APR_JUN", "secondary", pd.Timestamp("2026-04-01", tz="UTC"), pd.Timestamp("2026-07-01", tz="UTC")),
    ("Q3_JUL_AUG", "secondary", pd.Timestamp("2026-07-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC")),
]


def finite(x):
    return bool(np.isfinite(x))


def stats(T):
    return r1.stats_from_df(T)


def events_for_window(cache, lb, hold, start, end, last_ts):
    rows = []
    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        ex = pd.DatetimeIndex(ex)
        # Attribute a trade to the regime in which the entry signal occurred.
        # Exit may cross a window boundary but must remain inside the frozen Stage-E cutoff.
        m = valid & (ent >= start) & (ent < end) & (ex <= last_ts) & masks[RULE]
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
    return pd.DataFrame(rows, columns=["entry_ts", "exit_ts", "clock", "gross", "net"])


def metric(st, key):
    x = float(st[key])
    return x if finite(x) else np.nan


def fmt_pct(x):
    return "NA" if not finite(x) else f"{100*x:.2f}%"


def fmt_money(x):
    return "NA" if not finite(x) else f"${x:+.2f}"


def fmt_pf(x):
    return "NA" if not finite(x) else f"{x:.3f}"


def main():
    prior = pd.read_csv(PRIOR)
    if len(prior) != 5:
        raise AssertionError(f"expected 5 frozen cells, got {len(prior)}")
    if set(prior.hour_wib.astype(int)) != {HOUR}:
        raise AssertionError("frozen hour changed")
    if set(prior.character_rule.astype(str)) != {RULE}:
        raise AssertionError("frozen rule changed")
    actual = set(zip(prior.lookback_min.astype(int), prior.hold_min.astype(int)))
    if actual != EXPECTED:
        raise AssertionError(f"frozen cells changed: {sorted(actual)}")

    cutoffs = pd.to_datetime(prior.dataset_last_ts_utc, utc=True).unique()
    if len(cutoffs) != 1:
        raise AssertionError(f"Stage-E dataset cutoff not unique: {cutoffs}")
    last_ts = pd.Timestamp(cutoffs[0])

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if idx.max() < last_ts:
        raise RuntimeError(f"raw dataset no longer reaches frozen Stage-E cutoff: latest={idx.max()}, cutoff={last_ts}")
    x = x5[idx <= last_ts].copy()

    e12.CLOCKS = r1.clocks_for_hour(HOUR)
    e12.LOOKBACKS = sorted(prior.lookback_min.astype(int).unique().tolist())
    e12.HOLDS = sorted(prior.hold_min.astype(int).unique().tolist())
    cache = e12.prep(x)

    rows = []
    for window_name, window_role, start, end in WINDOWS:
        for c in prior.sort_values(["hold_min", "lookback_min"]).itertuples(index=False):
            lb = int(c.lookback_min)
            hold = int(c.hold_min)
            T = events_for_window(cache, lb, hold, start, end, last_ts)
            st = stats(T)
            rows.append({
                "window": window_name,
                "window_role": window_role,
                "entry_start_utc": start.isoformat(),
                "entry_end_exclusive_utc": end.isoformat(),
                "dataset_cutoff_utc": last_ts.isoformat(),
                "hour_wib": HOUR,
                "character_rule": RULE,
                "lookback_min": lb,
                "hold_min": hold,
                "n": int(st["trades"]),
                "wr": metric(st, "win_rate"),
                "net": float(st["net_pnl"]),
                "exp": metric(st, "expectancy"),
                "pf": metric(st, "pf"),
                "dd": metric(st, "max_dd"),
                "max_loss_streak": int(st["max_loss_streak"]),
            })

    R = pd.DataFrame(rows)
    order = {w[0]: i for i, w in enumerate(WINDOWS)}
    R["_order"] = R.window.map(order)
    R = R.sort_values(["_order", "hold_min", "lookback_min"]).drop(columns="_order").reset_index(drop=True)
    R.to_csv(OUT_CELLS, index=False)

    # Paired shorter-vs-longer horizon diagnostic for lookbacks present at both horizons.
    pair_rows = []
    for window_name, window_role, start, end in WINDOWS:
        W = R[R.window == window_name]
        for lb in (180, 240):
            a = W[(W.lookback_min == lb) & (W.hold_min == 240)].iloc[0]
            b = W[(W.lookback_min == lb) & (W.hold_min == 360)].iloc[0]
            comparable_pf = finite(a.pf) and finite(b.pf)
            shorter_dominates = bool(
                finite(a.exp) and finite(b.exp) and
                a.net > b.net and a.exp > b.exp and
                comparable_pf and a.pf > b.pf
            )
            pair_rows.append({
                "window": window_name,
                "window_role": window_role,
                "lookback_min": lb,
                "n_h240": int(a.n),
                "n_h360": int(b.n),
                "wr_h240": float(a.wr),
                "wr_h360": float(b.wr),
                "delta_wr_h240_minus_h360": float(a.wr - b.wr) if finite(a.wr) and finite(b.wr) else np.nan,
                "net_h240": float(a.net),
                "net_h360": float(b.net),
                "delta_net_h240_minus_h360": float(a.net - b.net),
                "exp_h240": float(a.exp),
                "exp_h360": float(b.exp),
                "delta_exp_h240_minus_h360": float(a.exp - b.exp) if finite(a.exp) and finite(b.exp) else np.nan,
                "pf_h240": float(a.pf),
                "pf_h360": float(b.pf),
                "delta_pf_h240_minus_h360": float(a.pf - b.pf) if comparable_pf else np.nan,
                "shorter_horizon_dominates_net_exp_pf": shorter_dominates,
            })
    P = pd.DataFrame(pair_rows)
    P["_order"] = P.window.map(order)
    P = P.sort_values(["_order", "lookback_min"]).drop(columns="_order").reset_index(drop=True)
    P.to_csv(OUT_PAIRS, index=False)

    primary = R[R.window_role == "primary"]
    primary_pairs = P[P.window_role == "primary"]
    anchor = primary[(primary.lookback_min == 240) & (primary.hold_min == 360)].set_index("window")
    p1 = anchor.loc["P1_JAN_APR"]
    p2 = anchor.loc["P2_MAY_AUG"]

    def weak(r):
        return finite(r.exp) and finite(r.pf) and r.exp < 0 and r.pf < 1.0

    def alive(r):
        return finite(r.exp) and finite(r.pf) and r.exp > 0 and r.pf > 1.0

    if weak(p1) and weak(p2):
        onset = "BREAKDOWN_PRESENT_FROM_EARLY_2026"
    elif alive(p1) and weak(p2):
        onset = "LATE_2026_BREAKDOWN"
    elif weak(p1) and alive(p2):
        onset = "EARLY_BREAKDOWN_WITH_LATER_RECOVERY"
    else:
        onset = "MIXED_TEMPORAL_BREAKDOWN"

    dom_count = int(primary_pairs.shorter_horizon_dominates_net_exp_pf.sum())
    if dom_count == len(primary_pairs):
        horizon = "H240_RELATIVE_ADVANTAGE_PERSISTS_BOTH_WINDOWS"
    elif dom_count >= 3:
        horizon = "H240_RELATIVE_ADVANTAGE_MOSTLY_PERSISTS"
    elif dom_count >= 1:
        horizon = "H240_RELATIVE_ADVANTAGE_MIXED"
    else:
        horizon = "NO_CONSISTENT_H240_RELATIVE_ADVANTAGE"

    status = f"{onset}__{horizon}"

    lines = [
        "# ETH R4b — Stage F 2026 Temporal-Regime Diagnostic",
        "",
        "**DIAGNOSTIC ONLY. SAME FIVE FROZEN H04 CELLS. NO RESELECTION. NO RETUNING. NO 2026 WINNER PROMOTION.**",
        "",
        f"Dataset cutoff frozen to Stage E: **{last_ts.isoformat()}**.",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Primary windows: **Jan–Apr** and **May–Aug (through frozen data cutoff)**, attributed by entry timestamp.",
        "Secondary localization: **Q1 / Q2 / Q3-to-date**. Quarterly samples are descriptive only.",
        f"Canonical LB240/H360 temporal verdict: **{onset}**.",
        f"Paired H240-vs-H360 diagnostic: **{horizon}** ({dom_count}/{len(primary_pairs)} primary LB-window comparisons dominate on Net + Exp + PF).",
        f"Stage F status: **{status}**.",
        "",
        "## Primary four-month windows",
        "",
        "| Window | LB/Hold | N | WR | Net | Exp | PF | DD | LS |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in primary.itertuples(index=False):
        lines.append(
            f"| {r.window} | LB{int(r.lookback_min)}/H{int(r.hold_min)} | {int(r.n)} | {fmt_pct(float(r.wr))} | {fmt_money(float(r.net))} | {fmt_money(float(r.exp))} | {fmt_pf(float(r.pf))} | {fmt_money(float(r.dd))} | {int(r.max_loss_streak)} |"
        )

    lines += [
        "",
        "## Paired horizon diagnostic — primary windows",
        "",
        "| Window | LB | Exp H240 | Exp H360 | ΔExp | PF H240 | PF H360 | ΔNet | H240 dominates Net+Exp+PF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in primary_pairs.itertuples(index=False):
        lines.append(
            f"| {r.window} | {int(r.lookback_min)} | {fmt_money(float(r.exp_h240))} | {fmt_money(float(r.exp_h360))} | {fmt_money(float(r.delta_exp_h240_minus_h360))} | {fmt_pf(float(r.pf_h240))} | {fmt_pf(float(r.pf_h360))} | {fmt_money(float(r.delta_net_h240_minus_h360))} | {'Y' if r.shorter_horizon_dominates_net_exp_pf else 'N'} |"
        )

    lines += [
        "",
        "## Secondary quarterly localization",
        "",
        "| Window | LB/Hold | N | WR | Net | Exp | PF |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in R[R.window_role == "secondary"].itertuples(index=False):
        lines.append(
            f"| {r.window} | LB{int(r.lookback_min)}/H{int(r.hold_min)} | {int(r.n)} | {fmt_pct(float(r.wr))} | {fmt_money(float(r.net))} | {fmt_money(float(r.exp))} | {fmt_pf(float(r.pf))} |"
        )

    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- Stage D 2025 remains the final untouched full-year OOS verdict.",
        "- Stage E and Stage F are shadow/current-regime diagnostics only.",
        "- Stage F does not relax the frozen N>=50 viability gate; subperiod N is intentionally too small for formal viability claims.",
        "- H240-vs-H360 comparisons test relative horizon resilience only. They do not select or promote a new live cell.",
        "- No hour, rule, lookback, hold, threshold, entry logic, or risk rule is changed from the frozen H04 plateau.",
    ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(status + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
