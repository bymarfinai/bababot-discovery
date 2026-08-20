#!/usr/bin/env python3
"""BTC H1 AMD + FVG Mitigation AMD2.

Frozen before result:
- exact AMD1 3H accumulation / first-session manipulation / exact opposite 3-candle FVG
- wait up to 6H AFTER FVG confirmation for first touch of the near FVG boundary
- enter at that boundary, structural SL at manipulation extreme
- PRIMARY TP = opposite accumulation boundary, only if modeled net RR >= 1:1 after 0.15% fee
- SECONDARY diagnostic = synthetic fixed net-1R target
- conservative 1H fill-candle ordering
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_h1_amd_fvg_amd1 as amd1

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_H1_AMD_FVG_Mitigation_AMD2_Result.md"
OUT_JSON = ROOT / "BTC_H1_AMD_FVG_Mitigation_AMD2_Result.json"
OUT_EVENTS = ROOT / "BTC_H1_AMD_FVG_Mitigation_AMD2_Events.csv"
OUT_AUG = ROOT / "BTC_H1_AMD_FVG_Mitigation_AMD2_August.csv"

EXTERNAL_START = pd.Timestamp("2020-01-01T00:00:00Z")
EXTERNAL_END = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_START = pd.Timestamp("2022-01-01T00:00:00Z")
REFERENCE_END = pd.Timestamp("2026-07-30T00:00:00Z")
# Preserve AMD1's mechanical chronological reference cut for direct comparability.
REFERENCE_CUT = pd.Timestamp("2025-03-18T00:00:00Z")
AUG_START = pd.Timestamp("2026-08-01T00:00:00Z")
AUG_END = pd.Timestamp("2026-08-20T00:00:00Z")

FEE = 0.0015
NOTIONAL = 500.0
MITIGATION_WINDOW_H = 6
HOLD_H = 6


def pct(v):
    if v is None:
        return "-"
    try:
        if math.isnan(float(v)):
            return "-"
    except Exception:
        pass
    return f"{100.0*float(v):.2f}%"


def money(v):
    return f"${float(v):+.2f}"


def side_signed_ret(side: str, entry: float, final: float) -> float:
    raw = final / entry - 1.0
    return raw if side == "LONG" else -raw


def find_mitigation(x: pd.DataFrame, r: pd.Series) -> tuple[int | None, float | None]:
    """First FVG-boundary touch in the frozen six-hour post-confirmation window."""
    start = int(r.fvg_entry_idx)  # first 1H bar AFTER the three FVG-forming bars
    if str(r.side) == "SHORT":
        entry = float(r.fvg_low)   # near/lower edge approached from below
        for idx in range(start, start + MITIGATION_WINDOW_H):
            if idx >= len(x):
                break
            expected = pd.Timestamp(x.ts.iloc[start]) + pd.Timedelta(hours=idx-start)
            if pd.Timestamp(x.ts.iloc[idx]) != expected:
                return None, None
            if float(x.high.iloc[idx]) >= entry:
                return idx, entry
    else:
        entry = float(r.fvg_high)  # near/upper edge approached from above
        for idx in range(start, start + MITIGATION_WINDOW_H):
            if idx >= len(x):
                break
            expected = pd.Timestamp(x.ts.iloc[start]) + pd.Timedelta(hours=idx-start)
            if pd.Timestamp(x.ts.iloc[idx]) != expected:
                return None, None
            if float(x.low.iloc[idx]) <= entry:
                return idx, entry
    return None, None


def execute_target(
    x: pd.DataFrame,
    side: str,
    fill_idx: int,
    entry: float,
    sl: float,
    tp: float,
    risk: float,
    target_dist: float,
) -> dict | None:
    """Conservative six-bar execution from the fill bar.

    Fill bar:
    - SL is credited adverse-first if touched.
    - TP is NEVER credited on fill bar because TP may have occurred before the limit fill.
    Later bars: if SL and TP coexist, SL first.
    """
    f = x.iloc[fill_idx:fill_idx + HOLD_H]
    if len(f) != HOLD_H:
        return None
    for j in range(HOLD_H):
        expected = pd.Timestamp(x.ts.iloc[fill_idx]) + pd.Timedelta(hours=j)
        if pd.Timestamp(f.ts.iloc[j]) != expected:
            return None

    def sl_hit(bar) -> bool:
        return float(bar.low) <= sl if side == "LONG" else float(bar.high) >= sl

    def tp_hit(bar) -> bool:
        return float(bar.high) >= tp if side == "LONG" else float(bar.low) <= tp

    # Fill bar: adverse SL counts; TP is deliberately not credited.
    b0 = f.iloc[0]
    if sl_hit(b0):
        outcome = "SL"
        raw = -risk
        exit_idx = fill_idx
    else:
        outcome = None
        raw = None
        exit_idx = None

    if outcome is None:
        for j in range(1, HOLD_H):
            bar = f.iloc[j]
            s = sl_hit(bar)
            t = tp_hit(bar)
            if s:
                outcome = "SL"
                raw = -risk
                exit_idx = fill_idx + j
                break
            if t:
                outcome = "TP"
                raw = target_dist
                exit_idx = fill_idx + j
                break

    if outcome is None:
        outcome = "TIME"
        final = float(f.close.iloc[-1])
        raw = side_signed_ret(side, entry, final)
        exit_idx = fill_idx + HOLD_H - 1

    net = float(raw) - FEE
    return {
        "outcome": outcome,
        "raw_ret": float(raw),
        "net_ret": net,
        "pnl": net * NOTIONAL,
        "exit_idx": int(exit_idx),
        "exit_ts": pd.Timestamp(x.ts.iloc[exit_idx]),
    }


def enrich_events(x: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    z = base[base.fvg].copy().reset_index(drop=True)
    rows = []
    for _, r in z.iterrows():
        fill_idx, entry = find_mitigation(x, r)
        rec = r.to_dict()
        rec.update({
            "mitigation_filled": fill_idx is not None,
            "mitigation_fill_idx": np.nan if fill_idx is None else int(fill_idx),
            "mitigation_fill_ts": pd.NaT if fill_idx is None else pd.Timestamp(x.ts.iloc[fill_idx]),
            "mitigation_entry": np.nan if entry is None else float(entry),
            "structural_valid": False,
            "risk": np.nan,
            "distribution_tp": np.nan,
            "distribution_target_dist": np.nan,
            "distribution_net_rr": np.nan,
            "distribution_rr_eligible": False,
            "distribution_outcome": None,
            "distribution_net_ret": np.nan,
            "distribution_pnl": np.nan,
            "net1r_tp": np.nan,
            "net1r_outcome": None,
            "net1r_net_ret": np.nan,
            "net1r_pnl": np.nan,
        })
        if fill_idx is None or entry is None:
            rows.append(rec)
            continue

        side = str(r.side)
        if side == "LONG":
            sl = float(r.manip_low)
            if entry <= sl:
                rows.append(rec)
                continue
            risk = (entry - sl) / entry
            dist_tp = float(r.acc_high)
            if dist_tp > entry:
                dist_d = (dist_tp - entry) / entry
            else:
                dist_d = -1.0
            net1r_d = risk + 2.0 * FEE
            net1r_tp = entry * (1.0 + net1r_d)
        else:
            sl = float(r.manip_high)
            if entry >= sl:
                rows.append(rec)
                continue
            risk = (sl - entry) / entry
            dist_tp = float(r.acc_low)
            if dist_tp < entry:
                dist_d = (entry - dist_tp) / entry
            else:
                dist_d = -1.0
            net1r_d = risk + 2.0 * FEE
            net1r_tp = entry * (1.0 - net1r_d)

        rec["structural_valid"] = bool(risk > 0)
        rec["risk"] = float(risk)
        rec["distribution_tp"] = float(dist_tp)
        rec["distribution_target_dist"] = float(dist_d)
        rec["distribution_net_rr"] = float((dist_d - FEE) / (risk + FEE)) if dist_d > 0 else np.nan
        eligible = bool(dist_d >= risk + 2.0 * FEE)
        rec["distribution_rr_eligible"] = eligible
        rec["net1r_tp"] = float(net1r_tp)

        # Secondary fixed net-1R diagnostic for every structurally valid fill.
        ex1 = execute_target(x, side, int(fill_idx), float(entry), float(sl), float(net1r_tp), float(risk), float(net1r_d))
        if ex1 is not None:
            rec["net1r_outcome"] = ex1["outcome"]
            rec["net1r_net_ret"] = ex1["net_ret"]
            rec["net1r_pnl"] = ex1["pnl"]

        # Primary Distribution target only when net RR >= 1:1.
        if eligible:
            exd = execute_target(x, side, int(fill_idx), float(entry), float(sl), float(dist_tp), float(risk), float(dist_d))
            if exd is not None:
                rec["distribution_outcome"] = exd["outcome"]
                rec["distribution_net_ret"] = exd["net_ret"]
                rec["distribution_pnl"] = exd["pnl"]

        rows.append(rec)
    return pd.DataFrame(rows)


def trade_stats(z: pd.DataFrame, kind: str) -> dict:
    if kind == "distribution":
        q = z[z.distribution_rr_eligible & z.distribution_outcome.notna()].copy()
        oc = "distribution_outcome"; pc = "distribution_pnl"; rc = "distribution_net_ret"
    else:
        q = z[z.structural_valid & z.net1r_outcome.notna()].copy()
        oc = "net1r_outcome"; pc = "net1r_pnl"; rc = "net1r_net_ret"
    if q.empty:
        return {"n":0,"tp":0,"sl":0,"time":0,"wr":None,"pnl":0.0,"expectancy":None,"median_risk":None,"median_net_rr":None,"net_positive":None}
    dec = q[q[oc].isin(["TP","SL"])]
    return {
        "n": int(len(q)),
        "tp": int((q[oc] == "TP").sum()),
        "sl": int((q[oc] == "SL").sum()),
        "time": int((q[oc] == "TIME").sum()),
        "wr": float((dec[oc] == "TP").mean()) if len(dec) else None,
        "pnl": float(q[pc].sum()),
        "expectancy": float(q[pc].mean()),
        "median_risk": float(q.risk.median()),
        "median_net_rr": float(q.distribution_net_rr.median()) if kind == "distribution" else 1.0,
        "net_positive": float((q[rc] > 0).mean()),
    }


def cohort_stats(z: pd.DataFrame) -> dict:
    fvg_n = int(len(z))
    fills = z[z.mitigation_filled].copy()
    valid = z[z.structural_valid].copy()
    eligible = z[z.distribution_rr_eligible].copy()
    return {
        "fvg_n": fvg_n,
        "filled_n": int(len(fills)),
        "fill_rate": float(len(fills) / fvg_n) if fvg_n else None,
        "structural_valid_n": int(len(valid)),
        "rr_eligible_n": int(len(eligible)),
        "rr_eligible_rate_of_fvg": float(len(eligible) / fvg_n) if fvg_n else None,
        "distribution": trade_stats(z, "distribution"),
        "net1r": trade_stats(z, "net1r"),
    }


def block_stats(z: pd.DataFrame, kind: str) -> list[dict]:
    if kind == "distribution":
        q = z[z.distribution_rr_eligible & z.distribution_outcome.notna()].copy()
        oc = "distribution_outcome"; pc = "distribution_pnl"
    else:
        q = z[z.structural_valid & z.net1r_outcome.notna()].copy()
        oc = "net1r_outcome"; pc = "net1r_pnl"
    q = q.sort_values("event_ts").reset_index(drop=True)
    if q.empty:
        return []
    bounds = np.linspace(0, len(q), 5, dtype=int)
    out = []
    for j in range(4):
        p = q.iloc[bounds[j]:bounds[j+1]].copy()
        dec = p[p[oc].isin(["TP","SL"])]
        out.append({
            "block": f"B{j+1}",
            "n": int(len(p)),
            "tp": int((p[oc] == "TP").sum()),
            "sl": int((p[oc] == "SL").sum()),
            "time": int((p[oc] == "TIME").sum()),
            "wr": float((dec[oc] == "TP").mean()) if len(dec) else None,
            "pnl": float(p[pc].sum()),
        })
    return out


def main():
    x = amd1.dataio.load_1h()
    base = amd1.build_events(x)
    ev = enrich_events(x, base)
    if ev.empty:
        raise RuntimeError("no exact AMD+FVG events")

    external = ev[(ev.event_ts >= EXTERNAL_START) & (ev.event_ts < EXTERNAL_END)].copy()
    development = ev[(ev.event_ts >= REFERENCE_START) & (ev.event_ts < REFERENCE_CUT)].copy()
    validation = ev[(ev.event_ts >= REFERENCE_CUT) & (ev.event_ts < REFERENCE_END)].copy()
    august = ev[(ev.event_ts >= AUG_START) & (ev.event_ts < AUG_END)].copy()

    ev.to_csv(OUT_EVENTS, index=False)
    august.to_csv(OUT_AUG, index=False)

    parts = {
        "development": development,
        "reference_validation": validation,
        "external": external,
        "august": august,
    }
    aggregate = {k: cohort_stats(v) for k, v in parts.items()}

    matrix = []
    for part, z in parts.items():
        for side in ("LONG", "SHORT"):
            for session in ("ALL", "ASIA_OPEN", "LONDON_OPEN", "NEW_YORK_OPEN"):
                q = z[z.side == side].copy()
                if session != "ALL":
                    q = q[q.session == session].copy()
                s = cohort_stats(q)
                matrix.append({"partition": part, "side": side, "session": session, **s})

    ext_dist_blocks = block_stats(external, "distribution")
    ext_1r_blocks = block_stats(external, "net1r")

    vdist = aggregate["reference_validation"]["distribution"]
    edist = aggregate["external"]["distribution"]
    dist_block_pass = sum(1 for b in ext_dist_blocks if b["n"] >= 8 and b["pnl"] > 0)
    distribution_supported = bool(
        vdist["n"] >= 25 and vdist["wr"] is not None and vdist["wr"] >= 0.60 and vdist["pnl"] > 0
        and edist["n"] >= 40 and edist["wr"] is not None and edist["wr"] >= 0.60 and edist["pnl"] > 0
        and dist_block_pass >= 3
    )
    dist_block80 = sum(1 for b in ext_dist_blocks if b["n"] >= 5 and b["wr"] is not None and b["wr"] >= 0.70)
    cand80 = bool(
        vdist["n"] >= 20 and vdist["wr"] is not None and vdist["wr"] >= 0.80 and vdist["pnl"] > 0
        and edist["n"] >= 30 and edist["wr"] is not None and edist["wr"] >= 0.80 and edist["pnl"] > 0
        and dist_block80 >= 3
    )

    v1 = aggregate["reference_validation"]["net1r"]
    e1 = aggregate["external"]["net1r"]
    r_block_pass = sum(1 for b in ext_1r_blocks if b["n"] >= 8 and b["pnl"] > 0)
    net1r_supported = bool(
        v1["n"] >= 25 and v1["wr"] is not None and v1["wr"] >= 0.60 and v1["pnl"] > 0
        and e1["n"] >= 40 and e1["wr"] is not None and e1["wr"] >= 0.60 and e1["pnl"] > 0
        and r_block_pass >= 3
    )

    result = {
        "protocol": "BTC_H1_AMD_FVG_MITIGATION_AMD2",
        "coverage": {"first": str(x.ts.min()), "last": str(x.ts.max()), "rows1h": int(len(x))},
        "reference_cut": str(REFERENCE_CUT),
        "exact_fvg_total": int(len(ev)),
        "aggregate": aggregate,
        "matrix": matrix,
        "external_distribution_blocks": ext_dist_blocks,
        "external_net1r_blocks": ext_1r_blocks,
        "AMD2_DISTRIBUTION_SUPPORTED": distribution_supported,
        "AMD2_80_CANDIDATE": cand80,
        "AMD2_NET1R_SUPPORTED": net1r_supported,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, default=str) + "\n")

    md = [
        "# BTC H1 AMD + FVG Mitigation AMD2 — Result",
        "",
        "Frozen 1H sequence: 3H accumulation -> first-session manipulation -> exact opposite FVG -> wait max6H for first FVG-boundary mitigation -> limit entry. Primary TP = opposite accumulation boundary only when modeled net RR>=1:1 after 0.15% fee. Secondary diagnostic = fixed net1R. Fill-candle TP is not credited; fill-candle SL is adverse-first.",
        "",
        f"Coverage **{x.ts.min()} -> {x.ts.max()}**, rows **{len(x):,}**. Exact AMD+FVG events **{len(ev)}**. Reference cut **{REFERENCE_CUT}**.",
        "",
        "## Aggregate mitigation / execution",
        "",
        "| Partition | FVG N | Filled | Fill rate | RR-eligible | Dist TP/SL/TIME | Dist WR | Dist PnL | Dist Exp | Median risk | Median net RR | Net1R N/WR/PnL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for part in ("development", "reference_validation", "external", "august"):
        s = aggregate[part]; d = s["distribution"]; n = s["net1r"]
        md.append(
            f"| {part} | {s['fvg_n']} | {s['filled_n']} | {pct(s['fill_rate'])} | {s['rr_eligible_n']} | "
            f"{d['tp']}/{d['sl']}/{d['time']} | {pct(d['wr'])} | {money(d['pnl'])} | "
            f"{('-' if d['expectancy'] is None else money(d['expectancy']))} | {pct(d['median_risk'])} | "
            f"{('-' if d['median_net_rr'] is None else f'{d['median_net_rr']:.2f}')} | "
            f"{n['n']}/{pct(n['wr'])}/{money(n['pnl'])} |"
        )

    md += [
        "",
        "## Fixed side/session cells — reference validation",
        "",
        "| Side | Session | FVG | Fill rate | RR-eligible | Dist WR/PnL | Net1R N/WR/PnL |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in matrix:
        if r["partition"] != "reference_validation" or r["session"] == "ALL":
            continue
        d = r["distribution"]; n = r["net1r"]
        md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {pct(r['fill_rate'])} | {r['rr_eligible_n']} | {pct(d['wr'])}/{money(d['pnl'])} | {n['n']}/{pct(n['wr'])}/{money(n['pnl'])} |")

    md += [
        "",
        "## Fixed side/session cells — external 2020-2021",
        "",
        "| Side | Session | FVG | Fill rate | RR-eligible | Dist WR/PnL | Net1R N/WR/PnL |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in matrix:
        if r["partition"] != "external" or r["session"] == "ALL":
            continue
        d = r["distribution"]; n = r["net1r"]
        md.append(f"| {r['side']} | {r['session']} | {r['fvg_n']} | {pct(r['fill_rate'])} | {r['rr_eligible_n']} | {pct(d['wr'])}/{money(d['pnl'])} | {n['n']}/{pct(n['wr'])}/{money(n['pnl'])} |")

    md += [
        "",
        "## External chronological blocks — Distribution TP",
        "",
        "| Block | N | TP | SL | TIME | WR | PnL |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for b in ext_dist_blocks:
        md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")

    md += [
        "",
        "## External chronological blocks — fixed net1R diagnostic",
        "",
        "| Block | N | TP | SL | TIME | WR | PnL |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for b in ext_1r_blocks:
        md.append(f"| {b['block']} | {b['n']} | {b['tp']} | {b['sl']} | {b['time']} | {pct(b['wr'])} | {money(b['pnl'])} |")

    md += [
        "",
        "## Verdicts",
        "",
        f"**AMD2_DISTRIBUTION_SUPPORTED: {'PASS' if distribution_supported else 'FAIL'}**",
        f"**AMD2_80_CANDIDATE: {'PASS' if cand80 else 'FAIL'}**",
        f"**AMD2_NET1R_SUPPORTED: {'PASS' if net1r_supported else 'FAIL'}**",
        "",
        "No midpoint/partial-FVG entry, later-FVG search, clock/side carve-out, accumulation-length change, or mitigation-window retuning after result.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(OUT_MD.read_text())


if __name__ == "__main__":
    main()
