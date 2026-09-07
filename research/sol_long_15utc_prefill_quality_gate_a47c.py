#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INFILE = ROOT / "SOL_LONG_15UTC_PREFILL_PATH_A47B_TRADES.csv"
OUT_DEV = ROOT / "SOL_LONG_15UTC_PREFILL_GATE_A47C_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_15UTC_PREFILL_GATE_A47C_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_PREFILL_GATE_A47C_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_PREFILL_GATE_A47C_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_PREFILL_GATE_A47C_Status.txt"

PARTS = ["development", "external", "reference_validation"]
FEATURE = "prefill_last_close_distance_H_R"
EPS = 1e-12


def pf(s) -> float:
    x = pd.to_numeric(s, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl <= EPS:
        return np.inf if gp > EPS else np.nan
    return gp / gl


def max_streak(vals) -> int:
    best = cur = 0
    for v in vals:
        if float(v) <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def max_dd(q: pd.DataFrame, col: str) -> float:
    if len(q) == 0:
        return 0.0
    z = q.sort_values(["exit_ts", "entry_ts"]).copy()
    eq = pd.to_numeric(z[col], errors="coerce").fillna(0).cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def metrics(q: pd.DataFrame, baseline: pd.DataFrame | None = None) -> dict:
    q = q.sort_values(["exit_ts", "entry_ts"]).copy()
    p = pd.to_numeric(q.pnl, errors="coerce")
    p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    out = {
        "n": len(q),
        "wr": float((p > 0).mean()) if len(q) else np.nan,
        "pf": pf(p),
        "exp": float(p.mean()) if len(q) else np.nan,
        "net": float(p.sum()),
        "max_dd": max_dd(q, "pnl"),
        "max_loss_streak": max_streak(p.tolist()),
        "wr_5bps": float((p5 > 0).mean()) if len(q) else np.nan,
        "pf_5bps": pf(p5),
        "exp_5bps": float(p5.mean()) if len(q) else np.nan,
        "net_5bps": float(p5.sum()),
        "max_dd_5bps": max_dd(q, "pnl_5bps"),
        "max_loss_streak_5bps": max_streak(p5.tolist()),
        "stress_wins": int((p5 > 0).sum()),
        "stress_losses": int((p5 <= 0).sum()),
    }
    if baseline is not None:
        bp = pd.to_numeric(baseline.pnl_5bps, errors="coerce")
        bw = int((bp > 0).sum())
        bl = int((bp <= 0).sum())
        out["winner_retention"] = out["stress_wins"] / bw if bw else np.nan
        out["loser_rejection"] = 1.0 - (out["stress_losses"] / bl) if bl else np.nan
    else:
        out["winner_retention"] = 1.0
        out["loser_rejection"] = 0.0
    return out


def cutoff_for_wr(dev: pd.DataFrame, target: float, min_n: int) -> float:
    z = dev[pd.to_numeric(dev[FEATURE], errors="coerce").notna()].copy()
    z[FEATURE] = pd.to_numeric(z[FEATURE], errors="coerce")
    vals = np.sort(z[FEATURE].dropna().unique())
    for t in vals:
        q = z[z[FEATURE] >= float(t)]
        if len(q) < min_n:
            continue
        wr = float((pd.to_numeric(q.pnl_5bps, errors="coerce") > 0).mean())
        if wr >= target:
            return float(t)
    return np.nan


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def main() -> None:
    t = pd.read_csv(INFILE)
    for c in ["entry_ts", "exit_ts", "execution_start"]:
        t[c] = pd.to_datetime(t[c], utc=True, errors="coerce")
    for c in [FEATURE, "pnl", "pnl_5bps"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")

    dev = t[t.partition == "development"].copy()
    base_dev = metrics(dev)
    wins = dev.loc[dev.pnl_5bps > 0, FEATURE].dropna()
    fails = dev.loc[dev.pnl_5bps <= 0, FEATURE].dropna()
    midpoint = float((wins.median() + fails.median()) / 2.0)
    thresholds = [
        ("MIDPOINT", midpoint),
        ("T55_MAXN", cutoff_for_wr(dev, 0.55, 200)),
        ("T60_MAXN", cutoff_for_wr(dev, 0.60, 150)),
    ]

    dev_rows = []
    seen = {}
    for name, threshold in thresholds:
        if pd.isna(threshold):
            dev_rows.append({"candidate": name, "threshold": np.nan, "available": False, "eligible": False})
            continue
        key = round(float(threshold), 12)
        duplicate_of = seen.get(key)
        if duplicate_of is None:
            seen[key] = name
        q = dev[dev[FEATURE].notna() & (dev[FEATURE] >= float(threshold))].copy()
        m = metrics(q, dev)
        eligible = bool(
            m["n"] >= 200
            and m["wr_5bps"] >= base_dev["wr_5bps"] + 0.08
            and m["pf_5bps"] >= base_dev["pf_5bps"] + 0.15
            and m["exp_5bps"] > base_dev["exp_5bps"]
            and m["net_5bps"] > 0
            and m["winner_retention"] >= 0.40
        )
        dev_rows.append({
            "candidate": name, "threshold": float(threshold), "available": True,
            "duplicate_of": duplicate_of or "", "eligible": eligible, **m
        })

    dev_df = pd.DataFrame(dev_rows)
    valid = dev_df[(dev_df.available == True) & (dev_df.eligible == True)].copy()
    if len(valid):
        sixty = valid[valid.wr_5bps >= 0.60].copy()
        if len(sixty):
            frozen = sixty.sort_values(["n", "pf_5bps"], ascending=[False, False]).iloc[0]
        else:
            frozen = valid.sort_values(["wr_5bps", "n"], ascending=[False, False]).iloc[0]
        frozen_name = str(frozen.candidate)
        threshold = float(frozen.threshold)
    else:
        frozen_name = "NONE"
        threshold = np.nan

    oos_rows = []
    kept_parts = []
    oos_pass = True
    both_60 = True
    if frozen_name != "NONE":
        for part in ["external", "reference_validation"]:
            b = t[t.partition == part].copy()
            q = b[b[FEATURE].notna() & (b[FEATURE] >= threshold)].copy()
            bm = metrics(b)
            m = metrics(q, b)
            passed = bool(
                m["n"] >= 75
                and m["wr_5bps"] > bm["wr_5bps"]
                and m["pf_5bps"] > bm["pf_5bps"]
                and m["exp_5bps"] > bm["exp_5bps"]
                and m["net_5bps"] > 0
                and m["winner_retention"] >= 0.35
            )
            oos_pass &= passed
            both_60 &= bool(m["wr_5bps"] >= 0.60)
            oos_rows.append({
                "partition": part, "candidate": frozen_name, "threshold": threshold, "passed": passed,
                "baseline_n": bm["n"], "baseline_wr_5bps": bm["wr_5bps"], "baseline_pf_5bps": bm["pf_5bps"],
                "baseline_exp_5bps": bm["exp_5bps"], "baseline_net_5bps": bm["net_5bps"], **m
            })
            q["a47c_candidate"] = frozen_name
            q["a47c_threshold"] = threshold
            kept_parts.append(q)

        qd = dev[dev[FEATURE].notna() & (dev[FEATURE] >= threshold)].copy()
        qd["a47c_candidate"] = frozen_name
        qd["a47c_threshold"] = threshold
        kept_parts.insert(0, qd)

    oos_df = pd.DataFrame(oos_rows)
    kept = pd.concat(kept_parts, ignore_index=True) if kept_parts else pd.DataFrame()
    kept.to_csv(OUT_TRADES, index=False)
    dev_df.to_csv(OUT_DEV, index=False)
    oos_df.to_csv(OUT_OOS, index=False)

    pooled = None
    if frozen_name != "NONE":
        pooled = metrics(kept, t)

    if frozen_name == "NONE":
        status = "SOL_LONG_15UTC_PREFILL_GATE_A47C_REJECTED_DEVELOPMENT"
    elif not oos_pass:
        status = "SOL_LONG_15UTC_PREFILL_GATE_A47C_REJECTED_OOS"
    elif both_60:
        status = "SOL_LONG_15UTC_PREFILL_GATE_A47C_SUPPORTED_60PLUS"
    else:
        status = "SOL_LONG_15UTC_PREFILL_GATE_A47C_SUPPORTED_IMPROVEMENT"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG 15UTC Pre-Fill Quality Gate — A47C Result", "",
        "A47C tests one causal one-bar arming rule from the A47B replicated pre-fill distance feature. E0/E40 economics and entry price remain frozen.", "",
        f"Development baseline stress: N **{base_dev['n']}**, WR **{pct(base_dev['wr_5bps'])}**, PF **{fmt(base_dev['pf_5bps'])}**, Exp **${fmt(base_dev['exp_5bps'])}**, Net **${fmt(base_dev['net_5bps'])}**.", "",
        "## Development threshold family", "",
        "| Candidate | T (R) | N | Stress WR | Stress PF | Stress Exp | Stress Net | DD | Loss streak | Winner retention | Loser rejection | Eligible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in dev_df.iterrows():
        if not bool(r.get("available", False)):
            lines.append(f"| {r.candidate} | - | - | - | - | - | - | - | - | - | - | NO |")
            continue
        lines.append(
            f"| {r.candidate} | {fmt(r.threshold,4)} | {int(r.n)} | {pct(r.wr_5bps)} | {fmt(r.pf_5bps)} | ${fmt(r.exp_5bps)} | ${fmt(r.net_5bps)} | "
            f"${fmt(r.max_dd_5bps)} | {int(r.max_loss_streak_5bps)} | {pct(r.winner_retention)} | {pct(r.loser_rejection)} | {'YES' if bool(r.eligible) else 'NO'} |"
        )

    lines += ["", f"Frozen Development winner: **{frozen_name}**" + (f" at **D >= {threshold:.4f}R**." if frozen_name != "NONE" else "."), ""]

    lines += ["## Frozen OOS", "",
              "| Partition | N | Stress WR | Stress PF | Stress Exp | Stress Net | DD | Loss streak | Winner retention | Loser rejection | Pass |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    if len(oos_df):
        for _, r in oos_df.iterrows():
            lines.append(
                f"| {r.partition} | {int(r.n)} | {pct(r.wr_5bps)} | {fmt(r.pf_5bps)} | ${fmt(r.exp_5bps)} | ${fmt(r.net_5bps)} | "
                f"${fmt(r.max_dd_5bps)} | {int(r.max_loss_streak_5bps)} | {pct(r.winner_retention)} | {pct(r.loser_rejection)} | {'YES' if bool(r.passed) else 'NO'} |"
            )
    else:
        lines.append("| - | - | - | - | - | - | - | - | - | - | - |")

    lines += ["", "## Pooled audit", ""]
    if pooled is not None:
        lines += [
            f"Retained **{pooled['n']} / {len(t)}** historical trades. Stress WR **{pct(pooled['wr_5bps'])}**, PF **{fmt(pooled['pf_5bps'])}**, Exp **${fmt(pooled['exp_5bps'])}**, Net **${fmt(pooled['net_5bps'])}**, max DD **${fmt(pooled['max_dd_5bps'])}**, max loss streak **{int(pooled['max_loss_streak_5bps'])}**.",
            f"Pooled winner retention **{pct(pooled['winner_retention'])}**; loser rejection **{pct(pooled['loser_rejection'])}**.", ""
        ]
    else:
        lines += ["No Development-eligible gate; pooled filtered audit not opened.", ""]

    lines += ["## Decision", "", f"**Status: {status}**", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
