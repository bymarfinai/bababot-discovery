#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_IN = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv"
A42_IN = ROOT / "SOL_LONG_15UTC_A40_B2_GUARD_A42_TRADES.csv"
A43_RECON_IN = ROOT / "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_RECONCILIATION.csv"

OUT_TRADES = ROOT / "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_TRADES.csv"
OUT_SEP = ROOT / "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_SEPARATION.csv"
OUT_FLIPS = ROOT / "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_PERIOD_FLIPS.csv"
OUT_MD = ROOT / "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_Status.txt"

PARTS = ["development", "external", "reference_validation"]
WINNER = "G_MAE145"
FEATURES = [
    "day_to_date_net_raw",
    "day_to_date_net_stress",
    "week_to_date_net_raw",
    "week_to_date_net_stress",
    "day_to_date_trades",
    "week_to_date_trades",
    "trailing_24h_net_raw",
    "trailing_24h_net_stress",
    "trailing_72h_net_raw",
    "trailing_72h_net_stress",
    "trailing_168h_net_raw",
    "trailing_168h_net_stress",
    "last3_component_mean_raw",
    "last3_component_mean_stress",
    "last5_component_mean_raw",
    "last5_component_mean_stress",
    "equity_drawdown_at_entry_raw",
    "equity_drawdown_at_entry_stress",
]


def week_start(ts: pd.Timestamp) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    if t.tzinfo is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    return t.to_period("W-MON").start_time.tz_localize("UTC")


def flip_label(base: float, overlay: float) -> str:
    bp = float(base) > 0
    op = float(overlay) > 0
    if bp and not op:
        return "POS_TO_NONPOS"
    if (not bp) and op:
        return "NONPOS_TO_POS"
    if bp and op:
        return "POS_STAYS_POS"
    return "NONPOS_STAYS_NONPOS"


def effect_stats(q: pd.DataFrame, feature: str):
    w = pd.to_numeric(q.loc[q.stress_outcome == "WIN", feature], errors="coerce").dropna()
    f = pd.to_numeric(q.loc[q.stress_outcome == "FAIL", feature], errors="coerce").dropna()
    if len(w) == 0 or len(f) == 0:
        return {
            "win_n": len(w), "fail_n": len(f), "win_median": np.nan,
            "fail_median": np.nan, "gap": np.nan, "effect": np.nan,
        }
    wm = float(w.median())
    fm = float(f.median())
    gap = wm - fm
    wi = float(w.quantile(0.75) - w.quantile(0.25))
    fi = float(f.quantile(0.75) - f.quantile(0.25))
    pool = (wi + fi) / 2.0
    if pool > 1e-12:
        eff = abs(gap) / pool
    elif abs(gap) > 1e-12:
        eff = np.inf
    else:
        eff = 0.0
    return {
        "win_n": len(w), "fail_n": len(f), "win_median": wm,
        "fail_median": fm, "gap": gap, "effect": eff,
    }


def causal_state(base_part: pd.DataFrame, entry_ts: pd.Timestamp) -> dict:
    entry = pd.Timestamp(entry_ts)
    prior = base_part[base_part.exit_ts < entry].sort_values(["exit_ts", "entry_ts"]).copy()

    day0 = entry.floor("D")
    week0 = week_start(entry)
    dtd = prior[prior.exit_ts >= day0]
    wtd = prior[prior.exit_ts >= week0]

    def trail(hours: int) -> pd.DataFrame:
        return prior[prior.exit_ts >= entry - pd.Timedelta(hours=hours)]

    t24 = trail(24)
    t72 = trail(72)
    t168 = trail(168)
    last3 = prior.tail(3)
    last5 = prior.tail(5)

    def net(q: pd.DataFrame, col: str) -> float:
        return float(pd.to_numeric(q[col], errors="coerce").fillna(0.0).sum())

    def mean(q: pd.DataFrame, col: str) -> float:
        x = pd.to_numeric(q[col], errors="coerce").dropna()
        return float(x.mean()) if len(x) else np.nan

    def dd(col: str) -> float:
        x = pd.to_numeric(prior[col], errors="coerce").fillna(0.0)
        if len(x) == 0:
            return 0.0
        eq = x.cumsum()
        current = float(eq.iloc[-1])
        peak = max(0.0, float(eq.cummax().max()))
        return max(0.0, peak - current)

    return {
        "day_to_date_net_raw": net(dtd, "pnl"),
        "day_to_date_net_stress": net(dtd, "pnl_5bps"),
        "week_to_date_net_raw": net(wtd, "pnl"),
        "week_to_date_net_stress": net(wtd, "pnl_5bps"),
        "day_to_date_trades": int(len(dtd)),
        "week_to_date_trades": int(len(wtd)),
        "trailing_24h_net_raw": net(t24, "pnl"),
        "trailing_24h_net_stress": net(t24, "pnl_5bps"),
        "trailing_72h_net_raw": net(t72, "pnl"),
        "trailing_72h_net_stress": net(t72, "pnl_5bps"),
        "trailing_168h_net_raw": net(t168, "pnl"),
        "trailing_168h_net_stress": net(t168, "pnl_5bps"),
        "last3_component_mean_raw": mean(last3, "pnl"),
        "last3_component_mean_stress": mean(last3, "pnl_5bps"),
        "last5_component_mean_raw": mean(last5, "pnl"),
        "last5_component_mean_stress": mean(last5, "pnl_5bps"),
        "equity_drawdown_at_entry_raw": dd("pnl"),
        "equity_drawdown_at_entry_stress": dd("pnl_5bps"),
    }


def build_period_diagnostics(base: pd.DataFrame, rec: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTS:
        b = base[base.partition == part].copy()
        r = rec[rec.partition == part].copy()
        for freq in ["DAY", "WEEK"]:
            if freq == "DAY":
                b["bucket"] = b.exit_ts.dt.floor("D")
                r["bucket"] = r.exit_ts.dt.floor("D")
            else:
                b["bucket"] = b.exit_ts.map(week_start)
                r["bucket"] = r.exit_ts.map(week_start)
            bsum = b.groupby("bucket", as_index=True)[["pnl", "pnl_5bps"]].sum()
            rsum = r.groupby("bucket", as_index=True)[["recovery_pnl", "recovery_pnl_5bps"]].sum()
            rcnt = r.groupby("bucket").size()
            for bucket in sorted(rsum.index):
                br = float(bsum.loc[bucket, "pnl"]) if bucket in bsum.index else 0.0
                bs = float(bsum.loc[bucket, "pnl_5bps"]) if bucket in bsum.index else 0.0
                dr = float(rsum.loc[bucket, "recovery_pnl"])
                ds = float(rsum.loc[bucket, "recovery_pnl_5bps"])
                rows.append({
                    "partition": part,
                    "period": freq,
                    "bucket": bucket,
                    "recovery_n": int(rcnt.loc[bucket]),
                    "baseline_raw": br,
                    "recovery_raw": dr,
                    "overlay_raw": br + dr,
                    "flip_raw": flip_label(br, br + dr),
                    "baseline_stress": bs,
                    "recovery_stress": ds,
                    "overlay_stress": bs + ds,
                    "flip_stress": flip_label(bs, bs + ds),
                })
    return pd.DataFrame(rows)


def fmt(v, d=2):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0 * float(v):.1f}%"


def main():
    base = pd.read_csv(BASE_IN)
    for c in ["entry_ts", "exit_ts"]:
        base[c] = pd.to_datetime(base[c], utc=True, errors="coerce")
    for c in ["pnl", "pnl_5bps"]:
        base[c] = pd.to_numeric(base[c], errors="coerce")
    base = base[base.partition.astype(str).isin(PARTS)].copy()

    a42 = pd.read_csv(A42_IN)
    for c in ["parent_entry_ts", "parent_exit_ts", "reentry_ts", "exit_ts"]:
        a42[c] = pd.to_datetime(a42[c], utc=True, errors="coerce")
    for c in ["recovery_pnl", "recovery_pnl_5bps"]:
        a42[c] = pd.to_numeric(a42[c], errors="coerce")
    rec = a42[
        (a42.role.astype(str) == "CENTRAL")
        & (a42.lane.astype(str) == WINNER)
        & (a42.partition.astype(str).isin(PARTS))
    ].copy()

    recon = pd.read_csv(A43_RECON_IN)
    for c in ["parent_entry_ts", "parent_exit_ts", "reentry_ts", "exit_ts"]:
        recon[c] = pd.to_datetime(recon[c], utc=True, errors="coerce")
    key = ["partition", "parent_entry_ts", "parent_exit_ts", "reentry_ts", "exit_ts"]
    rkeys = rec[key].drop_duplicates()
    a43keys = recon[key].drop_duplicates()
    key_match = bool(
        len(rkeys) == len(rec)
        and len(a43keys) == len(recon)
        and len(rkeys.merge(a43keys, on=key, how="inner")) == len(rec) == len(recon)
    )

    parents15 = base[(base.zone.astype(str) == "15UTC_PARENT") & (base.component.astype(str) == "PARENT")][
        ["partition", "entry_ts", "exit_ts"]
    ].rename(columns={"entry_ts": "parent_entry_ts", "exit_ts": "parent_exit_ts"})
    pm = rec[["partition", "parent_entry_ts", "parent_exit_ts"]].merge(
        parents15,
        on=["partition", "parent_entry_ts", "parent_exit_ts"],
        how="left",
        indicator=True,
    )
    parent_match = bool(len(pm) == len(rec) and pm["_merge"].eq("both").all())
    recon_ok = bool(key_match and parent_match and len(rec) > 0)

    enriched = []
    for _, row in rec.sort_values(["partition", "reentry_ts"]).iterrows():
        b = base[base.partition == row.partition].copy()
        state = causal_state(b, row.reentry_ts)
        z = row.to_dict()
        z.update(state)
        z["stress_outcome"] = "WIN" if float(row.recovery_pnl_5bps) > 0 else "FAIL"
        z["raw_outcome"] = "WIN" if float(row.recovery_pnl) > 0 else "FAIL"
        z["day_bucket"] = pd.Timestamp(row.exit_ts).floor("D")
        z["week_bucket"] = week_start(pd.Timestamp(row.exit_ts))
        enriched.append(z)
    trades = pd.DataFrame(enriched)

    period = build_period_diagnostics(base, rec)
    period.to_csv(OUT_FLIPS, index=False)

    # Attach final-period outcome labels for diagnosis only. They are never candidates.
    day_diag = period[period.period == "DAY"][
        ["partition", "bucket", "flip_raw", "flip_stress", "baseline_raw", "overlay_raw", "baseline_stress", "overlay_stress"]
    ].rename(columns={
        "bucket": "day_bucket", "flip_raw": "day_flip_raw", "flip_stress": "day_flip_stress",
        "baseline_raw": "final_day_baseline_raw", "overlay_raw": "final_day_overlay_raw",
        "baseline_stress": "final_day_baseline_stress", "overlay_stress": "final_day_overlay_stress",
    })
    week_diag = period[period.period == "WEEK"][
        ["partition", "bucket", "flip_raw", "flip_stress", "baseline_raw", "overlay_raw", "baseline_stress", "overlay_stress"]
    ].rename(columns={
        "bucket": "week_bucket", "flip_raw": "week_flip_raw", "flip_stress": "week_flip_stress",
        "baseline_raw": "final_week_baseline_raw", "overlay_raw": "final_week_overlay_raw",
        "baseline_stress": "final_week_baseline_stress", "overlay_stress": "final_week_overlay_stress",
    })
    trades = trades.merge(day_diag, on=["partition", "day_bucket"], how="left")
    trades = trades.merge(week_diag, on=["partition", "week_bucket"], how="left")
    trades.to_csv(OUT_TRADES, index=False)

    sep_rows = []
    for feature in FEATURES:
        d = effect_stats(trades[trades.partition == "development"], feature)
        e = effect_stats(trades[trades.partition == "external"], feature)
        r = effect_stats(trades[trades.partition == "reference_validation"], feature)
        dg = d["gap"]
        eg = e["gap"]
        rg = r["gap"]
        counts_ok = bool(
            d["win_n"] >= 5 and d["fail_n"] >= 2
            and e["win_n"] >= 3 and e["fail_n"] >= 2
            and r["win_n"] >= 3 and r["fail_n"] >= 2
        )
        signs_ok = bool(
            pd.notna(dg) and pd.notna(eg) and pd.notna(rg)
            and np.sign(dg) != 0
            and np.sign(dg) == np.sign(eg) == np.sign(rg)
        )
        effect_ok = bool(pd.notna(d["effect"]) and d["effect"] >= 0.50)
        replicated = bool(counts_ok and signs_ok and effect_ok)
        sep_rows.append({
            "feature": feature,
            "dev_win_n": d["win_n"], "dev_fail_n": d["fail_n"],
            "dev_win_median": d["win_median"], "dev_fail_median": d["fail_median"],
            "dev_gap": dg, "dev_effect": d["effect"],
            "external_win_n": e["win_n"], "external_fail_n": e["fail_n"],
            "external_win_median": e["win_median"], "external_fail_median": e["fail_median"],
            "external_gap": eg,
            "reference_win_n": r["win_n"], "reference_fail_n": r["fail_n"],
            "reference_win_median": r["win_median"], "reference_fail_median": r["fail_median"],
            "reference_gap": rg,
            "counts_ok": counts_ok, "signs_ok": signs_ok, "effect_ok": effect_ok,
            "replicated_directional": replicated,
        })
    sep = pd.DataFrame(sep_rows).sort_values(
        ["replicated_directional", "dev_effect"], ascending=[False, False], na_position="last"
    )
    sep.to_csv(OUT_SEP, index=False)

    candidates = sep[sep.replicated_directional].copy()
    week_flips = period[period.period == "WEEK"].copy()
    bad_raw = week_flips[week_flips.flip_raw == "POS_TO_NONPOS"]
    good_raw = week_flips[week_flips.flip_raw == "NONPOS_TO_POS"]
    bad_stress = week_flips[week_flips.flip_stress == "POS_TO_NONPOS"]
    good_stress = week_flips[week_flips.flip_stress == "NONPOS_TO_POS"]

    counts = []
    for part in PARTS:
        q = trades[trades.partition == part]
        counts.append((part, len(q), float((q.recovery_pnl_5bps > 0).mean()) if len(q) else np.nan))

    if not recon_ok:
        status = "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_RECONCILIATION_FAIL"
    elif len(candidates) > 0:
        status = "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_SUPPORTED_FOR_NEXT_TEST"
    else:
        status = "SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_INCONCLUSIVE"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG A42 Portfolio-State Anatomy — A44 Result", "",
        "A44 is forensic only. Frozen A42 `G_MAE145` and A24/A25 portfolio architecture are unchanged.", "",
        f"A42 recovery rows: **{len(trades)}**. A43-key reconciliation: **{key_match}**. 15UTC parent reconciliation: **{parent_match}**.", "",
        "## Recovery sample", "",
        "| Partition | N | Stress WR |", "|---|---:|---:|",
    ]
    for part, n, wr in counts:
        lines.append(f"| {part} | {n} | {pct(wr)} |")

    lines += ["", "## A43 week-flip diagnosis", "",
              f"Raw positive→non-positive weeks: **{len(bad_raw)}**; raw non-positive→positive weeks: **{len(good_raw)}**.",
              f"5bps positive→non-positive weeks: **{len(bad_stress)}**; 5bps non-positive→positive weeks: **{len(good_stress)}**.", ""]

    show = week_flips[(week_flips.flip_raw.isin(["POS_TO_NONPOS", "NONPOS_TO_POS"])) | (week_flips.flip_stress.isin(["POS_TO_NONPOS", "NONPOS_TO_POS"]))]
    lines += ["| Partition | Week | N rec | Base raw | +A42 raw | Raw flip | Base 5bps | +A42 5bps | 5bps flip |",
              "|---|---|---:|---:|---:|---|---:|---:|---|"]
    if len(show):
        for _, r in show.sort_values(["partition", "bucket"]).iterrows():
            lines.append(
                f"| {r.partition} | {pd.Timestamp(r.bucket).date()} | {int(r.recovery_n)} | "
                f"${fmt(r.baseline_raw)} | ${fmt(r.overlay_raw)} | {r.flip_raw} | "
                f"${fmt(r.baseline_stress)} | ${fmt(r.overlay_stress)} | {r.flip_stress} |"
            )
    else:
        lines.append("| none | - | - | - | - | - | - | - | - |")

    lines += ["", "## Replicated causal portfolio-state separators", "",
              "Only pre-entry causal features are eligible here. Full final-day/week diagnostics above are outcomes only.", "",
              "| Feature | Dev WIN med | Dev FAIL med | Dev gap | Effect | External gap | RefVal gap |", 
              "|---|---:|---:|---:|---:|---:|---:|"]
    if len(candidates):
        for _, r in candidates.iterrows():
            lines.append(
                f"| {r.feature} | {fmt(r.dev_win_median)} | {fmt(r.dev_fail_median)} | {fmt(r.dev_gap)} | "
                f"{fmt(r.dev_effect)} | {fmt(r.external_gap)} | {fmt(r.reference_gap)} |"
            )
    else:
        lines.append("| none | - | - | - | - | - | - |")

    lines += ["", "## Decision", "", f"**Status: {status}**", ""]
    if status.endswith("SUPPORTED_FOR_NEXT_TEST"):
        lines += [
            "At least one causal portfolio-state feature separated A42 stress winners/failers in Development and replicated directionally in both frozen validation partitions.",
            "A separate preregistration may test a minimal Development-derived guard; A44 itself authorizes no threshold or combination.", "",
        ]
    elif status.endswith("INCONCLUSIVE"):
        lines += [
            "No causal portfolio-state feature met the preregistered replication rule. Do not invent a week/calendar filter from the A43 failure.", "",
        ]
    lines += ["Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
