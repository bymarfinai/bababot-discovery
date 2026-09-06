#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BASE_IN = ROOT / "SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv"
A42_IN = ROOT / "SOL_LONG_15UTC_A40_B2_GUARD_A42_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_Result.md"
OUT_AUDIT = ROOT / "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_AUDIT.csv"
OUT_CONTRIB = ROOT / "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_CONTRIBUTIONS.csv"
OUT_RECON = ROOT / "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_RECONCILIATION.csv"
OUT_STATUS = ROOT / "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_Status.txt"

PARTS = ["development", "external", "reference_validation"]
SCOPES = PARTS + ["pooled"]
WINNER = "G_MAE145"


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def max_streak(vals, pred):
    best = cur = 0
    for v in vals:
        if pred(float(v)):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def max_dd(q, col):
    z = q.sort_values(["exit_ts", "entry_ts"]).copy()
    eq = pd.to_numeric(z[col], errors="coerce").fillna(0.0).cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max()) if len(eq) else 0.0


def period_pnl(q, col, freq):
    if q.empty:
        return pd.Series(dtype=float)
    z = q.copy()
    if freq == "D":
        z["bucket"] = z.exit_ts.dt.floor("D")
    else:
        z["bucket"] = z.exit_ts.dt.to_period("W-MON").dt.start_time.dt.tz_localize("UTC")
    return z.groupby("bucket")[col].sum().sort_index()


def metrics(q):
    q = q.sort_values(["exit_ts", "entry_ts"]).copy()
    out = {
        "component_trades": int(len(q)),
        "parent_episodes": int((q.component.astype(str) == "PARENT").sum()),
    }
    for suffix, col in [("raw", "pnl"), ("stress", "pnl_5bps")]:
        p = pd.to_numeric(q[col], errors="coerce").dropna()
        d = period_pnl(q, col, "D")
        w = period_pnl(q, col, "W-MON")
        out.update({
            f"wr_{suffix}": float((p > 0).mean()) if len(p) else np.nan,
            f"pf_{suffix}": pf(p),
            f"net_{suffix}": float(p.sum()),
            f"max_drawdown_{suffix}": max_dd(q, col),
            f"max_loss_streak_{suffix}": int(max_streak(p.tolist(), lambda v: v <= 0)),
            f"positive_day_rate_{suffix}": float((d > 0).mean()) if len(d) else np.nan,
            f"positive_week_rate_{suffix}": float((w > 0).mean()) if len(w) else np.nan,
            f"active_days_{suffix}": int(len(d)),
            f"active_weeks_{suffix}": int(len(w)),
        })
    return out


def fnum(v, d=2):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0 * float(v):.2f}%"


def main():
    base = pd.read_csv(BASE_IN)
    for c in ["entry_ts", "exit_ts"]:
        base[c] = pd.to_datetime(base[c], utc=True, errors="coerce")
    for c in ["pnl", "pnl_5bps"]:
        base[c] = pd.to_numeric(base[c], errors="coerce")

    a42 = pd.read_csv(A42_IN)
    for c in ["parent_entry_ts", "parent_exit_ts", "reentry_ts", "exit_ts"]:
        a42[c] = pd.to_datetime(a42[c], utc=True, errors="coerce")
    for c in ["recovery_pnl", "recovery_pnl_5bps"]:
        a42[c] = pd.to_numeric(a42[c], errors="coerce")

    a42 = a42[
        (a42.role.astype(str) == "CENTRAL")
        & (a42.lane.astype(str) == WINNER)
        & (a42.partition.astype(str).isin(PARTS))
    ].copy()

    parents15 = base[
        (base.zone.astype(str) == "15UTC_PARENT")
        & (base.component.astype(str) == "PARENT")
        & (base.partition.astype(str).isin(PARTS))
    ][["partition", "entry_ts", "exit_ts"]].copy()
    parents15 = parents15.rename(columns={"entry_ts": "ledger_parent_entry_ts", "exit_ts": "ledger_parent_exit_ts"})

    recon = a42.merge(
        parents15,
        left_on=["partition", "parent_entry_ts", "parent_exit_ts"],
        right_on=["partition", "ledger_parent_entry_ts", "ledger_parent_exit_ts"],
        how="left",
        indicator=True,
    )
    recon["matched_parent"] = recon["_merge"].eq("both")
    dup_recovery = bool(a42.duplicated(["partition", "parent_entry_ts"], keep=False).any())
    dup_parent = bool(parents15.duplicated(["partition", "ledger_parent_entry_ts", "ledger_parent_exit_ts"], keep=False).any())
    null_critical = bool(a42[["parent_entry_ts", "parent_exit_ts", "reentry_ts", "exit_ts", "recovery_pnl", "recovery_pnl_5bps"]].isna().any().any())
    all_matched = bool(len(recon) > 0 and recon.matched_parent.all())
    all_parts_present = bool(set(a42.partition.astype(str).unique()) == set(PARTS))
    recon_ok = bool(all_matched and all_parts_present and not dup_recovery and not dup_parent and not null_critical)

    recon_out = recon[[
        "partition", "parent_entry_ts", "parent_exit_ts", "reentry_ts", "exit_ts",
        "recovery_pnl", "recovery_pnl_5bps", "matched_parent"
    ]].copy()
    recon_out["duplicate_recovery_parent"] = recon_out.duplicated(["partition", "parent_entry_ts"], keep=False)
    recon_out.to_csv(OUT_RECON, index=False)

    rec = pd.DataFrame({
        "partition": a42.partition.astype(str),
        "zone": "15UTC_A42_RECOVERY",
        "component": "A42_G_MAE145",
        "entry_ts": a42.reentry_ts,
        "exit_ts": a42.exit_ts,
        "pnl": a42.recovery_pnl,
        "pnl_5bps": a42.recovery_pnl_5bps,
    })
    overlay = pd.concat([base, rec], ignore_index=True)

    rows = []
    gate_names = [
        "net_raw_up", "net_stress_up", "pf_raw_up", "pf_stress_up",
        "dd_raw_not_worse", "dd_stress_not_worse",
        "loss_streak_raw_not_worse", "loss_streak_stress_not_worse",
        "day_rate_raw_not_worse", "day_rate_stress_not_worse",
        "week_rate_raw_not_worse", "week_rate_stress_not_worse",
    ]

    for scope in SCOPES:
        b = base.copy() if scope == "pooled" else base[base.partition == scope].copy()
        o = overlay.copy() if scope == "pooled" else overlay[overlay.partition == scope].copy()
        bm = metrics(b)
        om = metrics(o)
        gates = {
            "net_raw_up": om["net_raw"] > bm["net_raw"],
            "net_stress_up": om["net_stress"] > bm["net_stress"],
            "pf_raw_up": om["pf_raw"] > bm["pf_raw"],
            "pf_stress_up": om["pf_stress"] > bm["pf_stress"],
            "dd_raw_not_worse": om["max_drawdown_raw"] <= bm["max_drawdown_raw"],
            "dd_stress_not_worse": om["max_drawdown_stress"] <= bm["max_drawdown_stress"],
            "loss_streak_raw_not_worse": om["max_loss_streak_raw"] <= bm["max_loss_streak_raw"],
            "loss_streak_stress_not_worse": om["max_loss_streak_stress"] <= bm["max_loss_streak_stress"],
            "day_rate_raw_not_worse": om["positive_day_rate_raw"] >= bm["positive_day_rate_raw"],
            "day_rate_stress_not_worse": om["positive_day_rate_stress"] >= bm["positive_day_rate_stress"],
            "week_rate_raw_not_worse": om["positive_week_rate_raw"] >= bm["positive_week_rate_raw"],
            "week_rate_stress_not_worse": om["positive_week_rate_stress"] >= bm["positive_week_rate_stress"],
        }
        row = {"scope": scope, "reconciliation_ok": recon_ok}
        for k, v in bm.items():
            row[f"baseline_{k}"] = v
        for k, v in om.items():
            row[f"overlay_{k}"] = v
        row.update(gates)
        row["all_gates_pass"] = bool(recon_ok and all(gates.values()))
        rows.append(row)

    audit = pd.DataFrame(rows)
    audit.to_csv(OUT_AUDIT, index=False)

    contrib_frames = []
    for label, q in [("baseline", base), ("overlay", overlay)]:
        z = q.groupby(["partition", "zone", "component"], as_index=False).agg(
            n=("pnl", "size"), net_raw=("pnl", "sum"), net_stress=("pnl_5bps", "sum")
        )
        z.insert(0, "portfolio", label)
        contrib_frames.append(z)
        zp = q.groupby(["zone", "component"], as_index=False).agg(
            n=("pnl", "size"), net_raw=("pnl", "sum"), net_stress=("pnl_5bps", "sum")
        )
        zp.insert(0, "partition", "pooled")
        zp.insert(0, "portfolio", label)
        contrib_frames.append(zp)
    contrib = pd.concat(contrib_frames, ignore_index=True)
    contrib.to_csv(OUT_CONTRIB, index=False)

    if not recon_ok:
        status = "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_RECONCILIATION_FAIL"
    elif bool(audit.all_gates_pass.all()):
        status = "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_SUPPORTED"
    else:
        status = "SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_NOT_SUPPORTED"
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")

    lines = [
        "# SOL LONG Three-Zone Portfolio + A42 Integration Audit — A43 Result", "",
        "Frozen A24 component ledger + frozen A42 CENTRAL `G_MAE145`; A25 component-trade/day/week/DD conventions preserved.", "",
        f"A42 recovery rows integrated: **{len(rec)}**. Exact parent reconciliation: **{int(recon_out.matched_parent.sum())}/{len(recon_out)}**. Duplicate recovery parent: **{dup_recovery}**. Duplicate frozen parent key: **{dup_parent}**. Critical null: **{null_critical}**.", "",
        "## Baseline vs +A42", "",
        "| Scope | Trades B→A | Episodes B→A | WR B→A | PF B→A | Net B→A | 5bps WR B→A | 5bps PF B→A | 5bps Net B→A | DD B→A | 5bps DD B→A | Loss streak B→A | 5bps loss streak B→A | Day+ B→A | 5bps Day+ B→A | Week+ B→A | 5bps Week+ B→A | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in audit.iterrows():
        lines.append(
            f"| {r.scope} | {int(r.baseline_component_trades)}→{int(r.overlay_component_trades)} | "
            f"{int(r.baseline_parent_episodes)}→{int(r.overlay_parent_episodes)} | "
            f"{pct(r.baseline_wr_raw)}→{pct(r.overlay_wr_raw)} | {fnum(r.baseline_pf_raw)}→{fnum(r.overlay_pf_raw)} | "
            f"${fnum(r.baseline_net_raw)}→${fnum(r.overlay_net_raw)} | {pct(r.baseline_wr_stress)}→{pct(r.overlay_wr_stress)} | "
            f"{fnum(r.baseline_pf_stress)}→{fnum(r.overlay_pf_stress)} | ${fnum(r.baseline_net_stress)}→${fnum(r.overlay_net_stress)} | "
            f"${fnum(r.baseline_max_drawdown_raw)}→${fnum(r.overlay_max_drawdown_raw)} | ${fnum(r.baseline_max_drawdown_stress)}→${fnum(r.overlay_max_drawdown_stress)} | "
            f"{int(r.baseline_max_loss_streak_raw)}→{int(r.overlay_max_loss_streak_raw)} | {int(r.baseline_max_loss_streak_stress)}→{int(r.overlay_max_loss_streak_stress)} | "
            f"{pct(r.baseline_positive_day_rate_raw)}→{pct(r.overlay_positive_day_rate_raw)} | {pct(r.baseline_positive_day_rate_stress)}→{pct(r.overlay_positive_day_rate_stress)} | "
            f"{pct(r.baseline_positive_week_rate_raw)}→{pct(r.overlay_positive_week_rate_raw)} | {pct(r.baseline_positive_week_rate_stress)}→{pct(r.overlay_positive_week_rate_stress)} | "
            f"{'YES' if r.all_gates_pass else 'NO'} |"
        )

    lines += ["", "## Gate failures", ""]
    any_fail = False
    for _, r in audit.iterrows():
        failed = [g for g in gate_names if not bool(r[g])]
        if failed:
            any_fail = True
            lines.append(f"- **{r.scope}:** " + ", ".join(failed))
    if not any_fail:
        lines.append("- None.")

    lines += ["", "## Net contribution by frozen habitat/component", "",
              "| Partition | Habitat | Component | N | Raw Net | 5bps Net |",
              "|---|---|---|---:|---:|---:|"]
    show = contrib[contrib.portfolio == "overlay"].copy()
    for _, r in show.iterrows():
        lines.append(f"| {r.partition} | {r.zone} | {r.component} | {int(r.n)} | ${fnum(r.net_raw)} | ${fnum(r.net_stress)} |")

    lines += ["", f"**Status: `{status}`**", "",
              "No thresholds or OOS coordinates were changed. Research only; live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
