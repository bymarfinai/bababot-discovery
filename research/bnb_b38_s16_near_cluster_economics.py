#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s11_e2_economics as s11
import bnb_b38_s12_e2_target_selection as s12
import bnb_b38_s14_post_tp1_continuation as s14

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_B38_S16_NEAR_CLUSTER_ECONOMICS"
EXPECTED_SIGNATURE = "d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
GAP_CUT = 0.12184510703934905

POLICIES = [
    "P0_BASELINE_TP1",
    "P1_CLUSTER_FULL_TP2",
    "P2_CLUSTER_HALF_TP1_HALF_TP2_STRUCTURAL",
    "P3_CLUSTER_HALF_TP1_HALF_TP2_BE",
]


def maxdd(rs):
    if not len(rs):
        return np.nan
    c = np.cumsum(np.asarray(rs, float))
    p = np.maximum.accumulate(np.concatenate([[0.0], c]))[:-1]
    return float(np.max(p - c))


def maxls(seq):
    mx = cur = 0
    for x in seq:
        if x == "LOSS":
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return mx


def first_touch_after(raw5, start_ts, level, kind, end):
    idx = raw5.index
    i0 = int(idx.searchsorted(start_ts, side="right"))
    i1 = int(idx.searchsorted(end, side="right"))
    if i1 <= i0:
        return None
    arr = (raw5.high if kind == "HIGH" else raw5.low).to_numpy(float, copy=False)[i0:i1]
    z = np.flatnonzero(arr >= level) if kind == "HIGH" else np.flatnonzero(arr <= level)
    return i0 + int(z[0]) if len(z) else None


def classify(realized_r):
    if not np.isfinite(realized_r):
        return "UNRESOLVED"
    if realized_r > 1e-12:
        return "WIN"
    if realized_r < -1e-12:
        return "LOSS"
    return "BE"


def full_resolve(raw5, entry_ts, entry, sl, tp, end):
    idx = raw5.index
    ti = first_touch_after(raw5, entry_ts, tp, "HIGH", end)
    si = first_touch_after(raw5, entry_ts, sl, "LOW", end)
    rr = (tp - entry) / (entry - sl)

    if ti is None and si is None:
        return "UNRESOLVED", pd.NaT, np.nan
    if ti is not None and si is not None and ti == si:
        return "AMBIGUOUS", idx[ti], np.nan
    if ti is not None and (si is None or ti < si):
        return "WIN", idx[ti], float(rr)
    return "LOSS", idx[si], -1.0


def runner_structural(raw5, entry_ts, entry, sl, tp1, tp2, end):
    idx = raw5.index
    rr1 = (tp1 - entry) / (entry - sl)
    rr2 = (tp2 - entry) / (entry - sl)

    t1 = first_touch_after(raw5, entry_ts, tp1, "HIGH", end)
    s1 = first_touch_after(raw5, entry_ts, sl, "LOW", end)

    if t1 is None and s1 is None:
        return "UNRESOLVED", pd.NaT, np.nan
    if t1 is not None and s1 is not None and t1 == s1:
        return "AMBIGUOUS", idx[t1], np.nan
    if s1 is not None and (t1 is None or s1 < t1):
        return "LOSS", idx[s1], -1.0

    # TP1 first. Start runner resolution on the next 5m bar to avoid
    # inventing intrabar ordering on the TP1 touch bar.
    partial = 0.5 * rr1
    tp1_ts = idx[t1]
    t2 = first_touch_after(raw5, tp1_ts, tp2, "HIGH", end)
    s2 = first_touch_after(raw5, tp1_ts, sl, "LOW", end)

    if t2 is None and s2 is None:
        return "PARTIAL_OPEN", pd.NaT, float(partial)
    if t2 is not None and s2 is not None and t2 == s2:
        return "AMBIGUOUS_RUNNER", idx[t2], np.nan
    if t2 is not None and (s2 is None or t2 < s2):
        real = partial + 0.5 * rr2
        return classify(real), idx[t2], float(real)

    real = partial - 0.5
    return classify(real), idx[s2], float(real)


def runner_be(raw5, entry_ts, entry, sl, tp1, tp2, end):
    idx = raw5.index
    rr1 = (tp1 - entry) / (entry - sl)
    rr2 = (tp2 - entry) / (entry - sl)

    t1 = first_touch_after(raw5, entry_ts, tp1, "HIGH", end)
    s1 = first_touch_after(raw5, entry_ts, sl, "LOW", end)

    if t1 is None and s1 is None:
        return "UNRESOLVED", pd.NaT, np.nan
    if t1 is not None and s1 is not None and t1 == s1:
        return "AMBIGUOUS", idx[t1], np.nan
    if s1 is not None and (t1 is None or s1 < t1):
        return "LOSS", idx[s1], -1.0

    partial = 0.5 * rr1
    tp1_ts = idx[t1]
    t2 = first_touch_after(raw5, tp1_ts, tp2, "HIGH", end)
    be = first_touch_after(raw5, tp1_ts, entry, "LOW", end)

    if t2 is None and be is None:
        return "PARTIAL_OPEN", pd.NaT, float(partial)
    if t2 is not None and be is not None and t2 == be:
        return "AMBIGUOUS_RUNNER", idx[t2], np.nan
    if t2 is not None and (be is None or t2 < be):
        real = partial + 0.5 * rr2
        return classify(real), idx[t2], float(real)

    return classify(partial), idx[be], float(partial)


def summarize(q, baseline):
    resolved = q[q.outcome.isin(["WIN", "LOSS", "BE"])].copy().sort_values(["entry_ts", "zone_id"])
    econ = resolved[resolved.outcome.isin(["WIN", "LOSS"])].copy()
    wins = resolved[resolved.outcome == "WIN"]
    losses = resolved[resolved.outcome == "LOSS"]
    bes = resolved[resolved.outcome == "BE"]

    pos = float(wins.realized_r.sum()) if len(wins) else 0.0
    neg = abs(float(losses.realized_r.sum())) if len(losses) else 0.0

    bw = set(baseline[baseline.baseline_outcome == "WIN"].zone_id)
    bl = set(baseline[baseline.baseline_outcome == "LOSS"].zone_id)
    cw = set(wins.zone_id)
    cl = set(losses.zone_id)
    cb = set(bes.zone_id)

    cluster = resolved[resolved.is_cluster]
    return {
        "plans": len(q),
        "resolved": len(resolved),
        "wins": len(wins),
        "losses": len(losses),
        "be": len(bes),
        "wr_ex_be": len(wins) / len(econ) if len(econ) else np.nan,
        "win_rate_all": len(wins) / len(resolved) if len(resolved) else np.nan,
        "median_win_r": float(wins.realized_r.median()) if len(wins) else np.nan,
        "expectancy_r": float(resolved.realized_r.mean()) if len(resolved) else np.nan,
        "total_r": float(resolved.realized_r.sum()) if len(resolved) else np.nan,
        "profit_factor": pos / neg if neg > 0 else (np.inf if pos > 0 else np.nan),
        "max_loss_streak": maxls(resolved.outcome.tolist()),
        "max_drawdown_r": maxdd(resolved.realized_r.tolist()) if len(resolved) else np.nan,
        "ambiguous": int(q.outcome.astype(str).str.startswith("AMBIGUOUS").sum()),
        "partial_open": int((q.outcome == "PARTIAL_OPEN").sum()),
        "baseline_wins": len(bw),
        "baseline_win_still_profitable": len(bw & cw),
        "baseline_win_to_loss": len(bw & cl),
        "baseline_win_to_be": len(bw & cb),
        "baseline_losses": len(bl),
        "baseline_loss_to_win": len(bl & cw),
        "cluster_trades": int(q.is_cluster.sum()),
        "cluster_resolved": len(cluster),
        "cluster_total_r": float(cluster.realized_r.sum()) if len(cluster) else np.nan,
        "cluster_expectancy_r": float(cluster.realized_r.mean()) if len(cluster) else np.nan,
    }


def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"


def fmt_num(x, d=3):
    if x == np.inf:
        return "∞"
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"


def main():
    raw, diag = b31.load_raw()
    if diag["coverage"] < .995:
        raise RuntimeError(f"raw coverage low {diag}")
    a1 = b31.load_a1()
    ident = b31.identity(raw, a1)
    if ident["max_ret15_diff"] > 5e-8 or ident["max_close_location_diff"] > 5e-8:
        raise RuntimeError(f"identity fail {ident}")

    end = raw.index.max()
    raw5, m15, h1, P, sig = s14.build_frozen(raw, end)
    if sig != EXPECTED_SIGNATURE:
        raise RuntimeError(f"signature drift got={sig}")

    # Exact executable frozen population.
    if int((P.period == "DEV").sum()) != 440 or int((P.period == "REF").sum()) != 272:
        raise RuntimeError("plan parity drift")

    # Cluster status is known at entry from frozen causal target geometry.
    P = P.copy()
    P["extension_gap_r"] = np.where(
        np.isfinite(P.tp2) & (P.tp2 > P.tp1),
        (P.tp2 - P.tp1) / (P.entry_price - P.touch_low_sl),
        np.nan,
    )
    P["is_cluster"] = (
        np.isfinite(P.tp2) &
        (P.tp2 > P.tp1) &
        np.isfinite(P.extension_gap_r) &
        (P.extension_gap_r <= GAP_CUT)
    )

    # Baseline outcomes for retention accounting.
    B = P[["zone_id", "period", "year", "entry_ts", "baseline_outcome", "baseline_realized_r", "is_cluster"]].copy()

    rows = []
    for r in P.itertuples(index=False):
        entry = float(r.entry_price)
        sl = float(r.touch_low_sl)
        tp1 = float(r.tp1)
        cluster = bool(r.is_cluster)
        tp2 = float(r.tp2) if np.isfinite(r.tp2) else np.nan

        for policy in POLICIES:
            if policy == "P0_BASELINE_TP1" or not cluster:
                out, rt, real = full_resolve(raw5, r.entry_ts, entry, sl, tp1, end)
                target_mode = "TP1"
            elif policy == "P1_CLUSTER_FULL_TP2":
                out, rt, real = full_resolve(raw5, r.entry_ts, entry, sl, tp2, end)
                target_mode = "TP2_FULL"
            elif policy == "P2_CLUSTER_HALF_TP1_HALF_TP2_STRUCTURAL":
                out, rt, real = runner_structural(raw5, r.entry_ts, entry, sl, tp1, tp2, end)
                target_mode = "HALF_TP1_HALF_TP2_STRUCTURAL"
            elif policy == "P3_CLUSTER_HALF_TP1_HALF_TP2_BE":
                out, rt, real = runner_be(raw5, r.entry_ts, entry, sl, tp1, tp2, end)
                target_mode = "HALF_TP1_HALF_TP2_BE"
            else:
                raise RuntimeError(policy)

            rows.append({
                "zone_id": r.zone_id,
                "period": r.period,
                "year": r.year,
                "entry_ts": r.entry_ts,
                "policy": policy,
                "is_cluster": cluster,
                "extension_gap_r": r.extension_gap_r,
                "target_mode": target_mode,
                "outcome": out,
                "resolution_ts": rt,
                "realized_r": real,
                "baseline_outcome": r.baseline_outcome,
                "baseline_realized_r": r.baseline_realized_r,
            })

    L = pd.DataFrame(rows)

    S = []
    for per in ["DEV", "REF"]:
        bp = B[B.period == per]
        for policy in POLICIES:
            q = L[(L.period == per) & (L.policy == policy)]
            S.append({"period": per, "policy": policy, **summarize(q, bp)})
    S = pd.DataFrame(S)

    Y = []
    for y in [2022, 2023, 2024, 2025, 2026]:
        bp = B[B.year == y]
        for policy in POLICIES:
            q = L[(L.year == y) & (L.policy == policy)]
            if len(q):
                Y.append({"year": y, "policy": policy, **summarize(q, bp)})
    Y = pd.DataFrame(Y)

    C = []
    for per in ["DEV", "REF"]:
        q0 = P[P.period == per]
        qc = q0[q0.is_cluster]
        C.append({
            "period": per,
            "all_trades": len(q0),
            "cluster_trades": len(qc),
            "cluster_share": len(qc) / len(q0),
            "cluster_baseline_wins": int((qc.baseline_outcome == "WIN").sum()),
            "cluster_baseline_losses": int((qc.baseline_outcome == "LOSS").sum()),
            "cluster_baseline_wr": float((qc.baseline_outcome == "WIN").mean()) if len(qc) else np.nan,
            "median_gap_r": float(qc.extension_gap_r.median()) if len(qc) else np.nan,
        })
    C = pd.DataFrame(C)

    L.to_csv(ROOT / f"{PFX}_Ledger.csv.gz", index=False, compression="gzip")
    S.to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    Y.to_csv(ROOT / f"{PFX}_ByYear.csv", index=False)
    C.to_csv(ROOT / f"{PFX}_ClusterProfile.csv", index=False)
    (ROOT / f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nGAP_CUT={GAP_CUT:.17f}\n"
        "DEV_PLANS=440\nREF_PLANS=272\n",
        encoding="utf-8",
    )

    lines = [
        "# BNB B38-S16 — Frozen Near-Cluster TP Economics", "",
        f"Frozen E2 signature: `{sig}`",
        f"Frozen S15 gap cut: `extension_gap_r <= {GAP_CUT:.15f}R`", "",
        "## Cluster profile", "",
        "| Period | All E2 | Cluster | Share | Baseline W-L | Baseline WR | Median gap |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in C.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.all_trades} | {r.cluster_trades} | {fmt_pct(r.cluster_share)} | "
            f"{r.cluster_baseline_wins}-{r.cluster_baseline_losses} | {fmt_pct(r.cluster_baseline_wr)} | "
            f"{fmt_num(r.median_gap_r)}R |"
        )

    lines += ["", "## Overall economics", "",
        "| Period | Policy | W-L-BE | WR ex-BE | Med WIN | Exp | Total R | PF | Max DD | Max L | Baseline WIN profitable | WIN→LOSS | LOSS→WIN | Cluster R |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.wins}-{r.losses}-{r.be} | {fmt_pct(r.wr_ex_be)} | "
            f"{fmt_num(r.median_win_r)}R | {fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | "
            f"{fmt_num(r.profit_factor)} | {fmt_num(r.max_drawdown_r)}R | {r.max_loss_streak} | "
            f"{r.baseline_win_still_profitable}/{r.baseline_wins} | {r.baseline_win_to_loss} | "
            f"{r.baseline_loss_to_win} | {fmt_num(r.cluster_total_r)}R |"
        )

    lines += ["", "## Annual stability", "",
        "| Year | Policy | W-L-BE | WR ex-BE | Exp | Total R | PF |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.policy} | {r.wins}-{r.losses}-{r.be} | {fmt_pct(r.wr_ex_be)} | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | {fmt_num(r.profit_factor)} |"
        )

    lines += ["", "## Interpretation boundary",
        "Only execution of the frozen S15 near-cluster character changes in S16.",
        "No detector, entry, SL, target ladder, or gap threshold is retuned.",
        "A policy should not be promoted from DEV alone; REF economics and winner preservation are mandatory."
    ]
    (ROOT / f"{PFX}_Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text("BNB_B38_S16_NEAR_CLUSTER_ECONOMICS_COMPLETE\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
