#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import sol_economic_first_h00_long_07_08wib_character as legacy
import sol_robust_character_discovery_v2_phase1a as v2
import sol_robust_character_discovery_v3 as v3

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_RCD_V3_HISTCONF"
FINALISTS = ROOT / "SOL_RCD_V3_FrozenFinalists.csv"
LOCAL_BOUNDARIES = ROOT / "SOL_RCD_V3_LocalScaleBoundaries.csv"
BROAD_BOUNDARIES = ROOT / "SOL_RCD_V3_BroadVolBoundaries.csv"
PARTS = ("external", "reference_validation")


def out(name: str) -> Path:
    return ROOT / f"{PFX}_{name}"


def load_local_bounds():
    x = pd.read_csv(LOCAL_BOUNDARIES)
    result = {}
    for lb, g in x.groupby("lookback_min"):
        result[int(lb)] = {
            str(r.scale_variable): (float(r.q33), float(r.q67))
            for r in g.itertuples(index=False)
        }
    return result


def load_broad_bounds():
    x = pd.read_csv(BROAD_BOUNDARIES)
    result = {}
    for lb, g in x.groupby("lookback_min"):
        result[int(lb)] = {
            str(r.broad_variable): (float(r.q33), float(r.q67))
            for r in g.itertuples(index=False)
        }
    return result


def build_frame(x5: pd.DataFrame, lb: int, part: str) -> pd.DataFrame:
    a, z = base.PARTS[part]
    pieces = []
    for clock in v3.CLOCKS:
        f = v2.enhanced_frame(x5, clock, lb)
        f = v3.add_range_7d(x5, f)
        et = pd.DatetimeIndex(f.entry_ts)
        pt = pd.DatetimeIndex(f.pre_ts)
        m = (pt >= a) & (et >= a) & (et < z)
        if m.any():
            pieces.append(f.loc[m].copy())
    if not pieces:
        return pd.DataFrame()
    d = pd.concat(pieces, ignore_index=True)
    d["entry_ts"] = pd.to_datetime(d.entry_ts, utc=True)
    d["year"] = d.entry_ts.dt.year.astype(int)
    return d.sort_values(["entry_ts", "clock_min"]).reset_index(drop=True)


def hold_net(x5: pd.DataFrame, df: pd.DataFrame, hold: int, part: str):
    et = pd.DatetimeIndex(df.entry_ts)
    xt = et + pd.Timedelta(minutes=hold)
    xi = x5.index.get_indexer(xt)
    ei = df.entry_ix.to_numpy(int)
    _, z = base.PARTS[part]
    valid = (xi >= 0) & ((xi - ei) == hold // v3.BAR_MIN) & (xt < z)
    ret = np.full(len(df), np.nan, float)
    ok = xi >= 0
    opens = x5.open.to_numpy(float)
    ep = df.entry_price.to_numpy(float)
    ret[ok] = (opens[xi[ok]] - ep[ok]) / ep[ok]
    net = v3.NOTIONAL * ret - v3.FEE
    return valid, net, xt


def selected_trades(x5, df, lbound, bbound, rule, local, broad, hold, part):
    sm = legacy.masks_for_frame(df)[rule]
    lm = v2.scale_masks(df, lbound)[local]
    bm = v3.broad_masks(df, bbound)[broad]
    valid, net_all, exit_ts = hold_net(x5, df, hold, part)
    idx = np.flatnonzero(sm & lm & bm & valid)
    if len(idx) == 0:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "year", "minute_anchor", "hour_utc", "net"])
    return pd.DataFrame({
        "entry_ts": pd.DatetimeIndex(df.entry_ts)[idx],
        "exit_ts": exit_ts[idx],
        "year": df.year.to_numpy(int)[idx],
        "minute_anchor": df.minute_anchor.to_numpy(int)[idx],
        "hour_utc": df.hour_utc.to_numpy(int)[idx],
        "net": net_all[idx],
    }).sort_values("entry_ts").reset_index(drop=True)


def gate(s: dict, combined: bool = False) -> bool:
    if combined:
        return bool(
            s["trades"] >= 180
            and s["net_pnl"] > 0
            and np.isfinite(s["expectancy"]) and s["expectancy"] > 0
            and np.isfinite(s["pf"]) and s["pf"] >= 1.20
            and s["max_loss_streak"] <= 10
        )
    return bool(
        s["trades"] >= 40
        and s["net_pnl"] > 0
        and np.isfinite(s["expectancy"]) and s["expectancy"] > 0
        and np.isfinite(s["pf"]) and s["pf"] >= 1.05
        and s["max_loss_streak"] <= 10
    )


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("SOLUSDT")
    if coverage < 0.995:
        raise RuntimeError(f"coverage too low: {coverage:.6%}")

    finalists = pd.read_csv(FINALISTS).sort_values("freeze_rank")
    if len(finalists) != 5:
        raise RuntimeError(f"expected 5 frozen finalists, got {len(finalists)}")
    local_bounds = load_local_bounds()
    broad_bounds = load_broad_bounds()
    lbs = sorted(set(int(x) for x in finalists.lookback_min))
    frames = {(lb, part): build_frame(x5, lb, part) for lb in lbs for part in (*PARTS, "august")}

    summary_rows, partition_rows, year_rows, anchor_rows, hour_rows, august_rows = [], [], [], [], [], []

    for f in finalists.itertuples(index=False):
        rank = int(f.freeze_rank)
        cid = str(f.candidate_id)
        lb = int(f.lookback_min)
        hold = int(f.hold_min)
        rule = str(f.shape_rule)
        local = str(f.local_scale_state)
        broad = str(f.broad_regime)
        by_part = {}
        stats_by_part = {}
        pass_by_part = {}

        for part in PARTS:
            t = selected_trades(
                x5, frames[(lb, part)], local_bounds[lb], broad_bounds[lb],
                rule, local, broad, hold, part
            )
            by_part[part] = t
            s = v2.stats(t.net.to_numpy(float), True)
            stats_by_part[part] = s
            pass_by_part[part] = gate(s, False)
            partition_rows.append({
                "freeze_rank": rank,
                "candidate_id": cid,
                "partition": part,
                **s,
                "partition_gate": pass_by_part[part],
            })

            for y in sorted(set(t.year.tolist())):
                z = t[t.year == y]
                year_rows.append({
                    "freeze_rank": rank,
                    "candidate_id": cid,
                    "partition": part,
                    "year": int(y),
                    **v2.stats(z.net.to_numpy(float), True),
                })
            for a in v3.ANCHORS:
                z = t[t.minute_anchor == a]
                anchor_rows.append({
                    "freeze_rank": rank,
                    "candidate_id": cid,
                    "partition": part,
                    "minute_anchor": a,
                    **v2.stats(z.net.to_numpy(float), False),
                })
            for h in range(24):
                z = t[t.hour_utc == h]
                hour_rows.append({
                    "freeze_rank": rank,
                    "candidate_id": cid,
                    "partition": part,
                    "hour_utc": h,
                    **v2.stats(z.net.to_numpy(float), False),
                })

        combined = pd.concat([by_part[p] for p in PARTS], ignore_index=True).sort_values("entry_ts").reset_index(drop=True)
        cs = v2.stats(combined.net.to_numpy(float), True)
        combined_gate = gate(cs, True)
        passes = int(pass_by_part["external"]) + int(pass_by_part["reference_validation"])
        if combined_gate and passes == 2:
            label = "HISTORICAL_CONFIRMATION_STRONG"
        elif combined_gate and passes == 1:
            label = "HISTORICAL_CONFIRMATION_PARTIAL"
        else:
            label = "HISTORICAL_CONFIRMATION_FAIL"

        aug = selected_trades(
            x5, frames[(lb, "august")], local_bounds[lb], broad_bounds[lb],
            rule, local, broad, hold, "august"
        )
        aus = v2.stats(aug.net.to_numpy(float), True)
        august_rows.append({
            "freeze_rank": rank,
            "candidate_id": cid,
            **aus,
            "status": "SHADOW_ONLY",
        })

        summary_rows.append({
            "freeze_rank": rank,
            "candidate_id": cid,
            "shape_rule": rule,
            "local_scale_state": local,
            "broad_regime": broad,
            "lookback_min": lb,
            "hold_min": hold,
            "development_trades": int(f.trades),
            "development_expectancy": float(f.expectancy),
            "development_pf": float(f.pf),
            "external_trades": stats_by_part["external"]["trades"],
            "external_win_rate": stats_by_part["external"]["win_rate"],
            "external_net_pnl": stats_by_part["external"]["net_pnl"],
            "external_expectancy": stats_by_part["external"]["expectancy"],
            "external_pf": stats_by_part["external"]["pf"],
            "external_max_loss_streak": stats_by_part["external"]["max_loss_streak"],
            "external_gate": pass_by_part["external"],
            "reference_trades": stats_by_part["reference_validation"]["trades"],
            "reference_win_rate": stats_by_part["reference_validation"]["win_rate"],
            "reference_net_pnl": stats_by_part["reference_validation"]["net_pnl"],
            "reference_expectancy": stats_by_part["reference_validation"]["expectancy"],
            "reference_pf": stats_by_part["reference_validation"]["pf"],
            "reference_max_loss_streak": stats_by_part["reference_validation"]["max_loss_streak"],
            "reference_gate": pass_by_part["reference_validation"],
            "combined_trades": cs["trades"],
            "combined_win_rate": cs["win_rate"],
            "combined_net_pnl": cs["net_pnl"],
            "combined_expectancy": cs["expectancy"],
            "combined_pf": cs["pf"],
            "combined_max_dd": cs["max_dd"],
            "combined_max_loss_streak": cs["max_loss_streak"],
            "combined_gate": combined_gate,
            "expectancy_retention_vs_dev": cs["expectancy"] / float(f.expectancy) if float(f.expectancy) != 0 else np.nan,
            "august_shadow_trades": aus["trades"],
            "august_shadow_expectancy": aus["expectancy"],
            "confirmation_label": label,
        })

    summary = pd.DataFrame(summary_rows)
    pd.DataFrame(partition_rows).to_csv(out("PartitionEconomics.csv"), index=False)
    pd.DataFrame(year_rows).to_csv(out("YearEconomics.csv"), index=False)
    pd.DataFrame(anchor_rows).to_csv(out("AnchorEconomics.csv"), index=False)
    pd.DataFrame(hour_rows).to_csv(out("HourEconomics.csv"), index=False)
    pd.DataFrame(august_rows).to_csv(out("AugustShadow.csv"), index=False)
    summary.to_csv(out("CandidateSummary.csv"), index=False)

    strong = int((summary.confirmation_label == "HISTORICAL_CONFIRMATION_STRONG").sum())
    partial = int((summary.confirmation_label == "HISTORICAL_CONFIRMATION_PARTIAL").sum())
    fail = int((summary.confirmation_label == "HISTORICAL_CONFIRMATION_FAIL").sum())

    lines = [
        "# SOL RCD v3 — Secondary Historical Confirmation Result", "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "Five finalists were frozen before this run; no substitution or retuning was allowed.",
        "This is secondary historical confirmation, not pristine untouched OOS.", "",
        f"**Strong: {strong} / Partial: {partial} / Fail: {fail}.**", "",
        "| Rank | Character | Local | Broad | Ext N | Ext Exp | Ext PF | Ext LS | Gate | Ref N | Ref Exp | Ref PF | Ref LS | Gate | Combined N | Net | Exp | PF | LS | Verdict |",
        "|---:|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {int(r.freeze_rank)} | `{r.shape_rule}` | `{r.local_scale_state}` | `{r.broad_regime}` | "
            f"{int(r.external_trades)} | ${r.external_expectancy:+.2f} | {r.external_pf:.3f} | {int(r.external_max_loss_streak)} | {'PASS' if r.external_gate else 'FAIL'} | "
            f"{int(r.reference_trades)} | ${r.reference_expectancy:+.2f} | {r.reference_pf:.3f} | {int(r.reference_max_loss_streak)} | {'PASS' if r.reference_gate else 'FAIL'} | "
            f"{int(r.combined_trades)} | ${r.combined_net_pnl:+.2f} | ${r.combined_expectancy:+.2f} | {r.combined_pf:.3f} | {int(r.combined_max_loss_streak)} | **{r.confirmation_label}** |"
        )

    status = f"SOL_RCD_V3_HISTCONF_{strong}_STRONG_{partial}_PARTIAL_{fail}_FAIL"
    out("Result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("Status.txt").write_text(status + "\n", encoding="utf-8")
    print(status)
    print(out("Result.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
