#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A4_PATH = Path(__file__).resolve().parent / "sol_long_h1_loss_recovery_a4.py"
spec = importlib.util.spec_from_file_location("sol_a4", A4_PATH)
a4 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a4)
a2 = a4.a2

IN_ATLAS = ROOT / "SOL_LONG_VISIT_BREAK_A1_ATLAS.csv"
IN_H2 = ROOT / "SOL_LONG_H1_LOSS_RECOVERY_A4_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_Result.md"
OUT_DEV = ROOT / "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_TRADES.csv"
OUT_CELLS = ROOT / "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_CELLS.csv"
OUT_STATUS = ROOT / "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_Status.txt"

FAMILY = "E0_RESTING_H"
TARGET_R = 0.40
MATURE_HOUR = 18
STRESS = a2.STRESS
EPS = 1e-12
RANK_COLS = [
    "same_dom_blocks",
    "dominant_min_block_conversion",
    "dominant_break_conversion",
    "dominant_median_extension_R",
    "dominant_opportunity_n",
    "ref_min",
    "hour",
]
RANK_ASC = [False, False, False, False, False, True, True]


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x <= 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def fmt(v, d=2):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def clock_distance(a: int, b: int):
    d = abs(int(a) - int(b)) % 24
    return min(d, 24 - d)


def parse_int_list(v):
    if pd.isna(v):
        return []
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return []
    out = []
    for token in s.split(","):
        token = token.strip()
        if token:
            out.append(int(float(token)))
    return sorted(set(out))


def rank_cells(df):
    return df.sort_values(RANK_COLS, ascending=RANK_ASC, kind="mergesort")


def derive_cells(atlas):
    q = atlas[
        (pd.to_numeric(atlas.dominant_visit, errors="coerce") == 2)
        & atlas.topology_supported.astype(bool)
        & (pd.to_numeric(atlas.same_dom_blocks, errors="coerce") >= 4)
        & (pd.to_numeric(atlas.dominant_opportunity_n, errors="coerce") >= 100)
    ].copy()
    q["clock_distance_from_18"] = q.hour.astype(int).map(lambda h: clock_distance(h, MATURE_HOUR))
    q = q[q.clock_distance_from_18 >= 4].copy()
    q = rank_cells(q)

    chosen = []
    for _, r in q.iterrows():
        h = int(r.hour)
        if any(clock_distance(h, int(x.hour)) <= 2 for x in chosen):
            continue
        chosen.append(r)
        if len(chosen) >= 4:
            break
    if not chosen:
        raise RuntimeError("A17 preregistered atlas derivation produced no candidate cells")

    rows = []
    for rank_i, r in enumerate(chosen, start=1):
        ref = int(r.ref_min)
        hour = int(r.hour)
        dom = int(r.dominant_visit)

        chours = parse_int_list(r.clock_support_hours)
        cq = atlas[(atlas.ref_min.astype(int) == ref) & atlas.hour.astype(int).isin(chours) & (atlas.dominant_visit.astype(int) == dom)].copy()
        if cq.empty:
            raise RuntimeError(f"No frozen clock support for R{ref}/{hour:02d}")
        crow = rank_cells(cq).iloc[0]

        rmins = parse_int_list(r.ref_support_mins)
        rq = atlas[(atlas.hour.astype(int) == hour) & atlas.ref_min.astype(int).isin(rmins) & (atlas.dominant_visit.astype(int) == dom)].copy()
        if rq.empty:
            raise RuntimeError(f"No frozen reference support for R{ref}/{hour:02d}")
        rrow = rank_cells(rq).iloc[0]

        rows.append({
            "candidate": f"Z{rank_i}_R{ref}_H{hour:02d}",
            "anatomy_rank": rank_i,
            "ref_min": ref,
            "hour": hour,
            "clock_distance_from_18": clock_distance(hour, MATURE_HOUR),
            "dominant_visit": dom,
            "same_dom_blocks": int(r.same_dom_blocks),
            "dominant_opportunity_n": int(r.dominant_opportunity_n),
            "dominant_break_conversion": float(r.dominant_break_conversion),
            "dominant_median_extension_R": float(r.dominant_median_extension_R),
            "clock_support_ref_min": int(crow.ref_min),
            "clock_support_hour": int(crow.hour),
            "ref_support_ref_min": int(rrow.ref_min),
            "ref_support_hour": int(rrow.hour),
        })
    return pd.DataFrame(rows)


def max_loss_streak(vals):
    best = 0
    cur = 0
    for v in pd.to_numeric(vals, errors="coerce").fillna(0.0):
        if float(v) <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def weeks_for(partition):
    a, z = a2.part_bounds(partition)
    return float((z - a) / pd.Timedelta(weeks=1))


def stats(q, partition):
    p = pd.to_numeric(q.pnl, errors="coerce")
    p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    return {
        "n": len(q),
        "trades_per_week": len(q) / weeks_for(partition) if weeks_for(partition) > 0 else np.nan,
        "wr": float((p > 0).mean()) if len(q) else np.nan,
        "pf": pf(p),
        "expectancy": float(p.mean()) if len(q) else np.nan,
        "net": float(p.sum()),
        "max_loss_streak": max_loss_streak(p),
        "wr_5bps": float((p5 > 0).mean()) if len(q) else np.nan,
        "pf_5bps": pf(p5),
        "expectancy_5bps": float(p5.mean()) if len(q) else np.nan,
        "net_5bps": float(p5.sum()),
    }


def load_mature_windows():
    parent = a4.load_parent()
    h2 = pd.read_csv(IN_H2)
    for c in ["execution_start", "parent_entry_ts", "parent_exit_ts", "recovery_entry_ts", "recovery_exit_ts"]:
        if c in h2.columns:
            h2[c] = pd.to_datetime(h2[c], utc=True, errors="coerce")
    h2 = h2[(pd.to_numeric(h2.visit_n, errors="coerce") == 2) & (h2.lane.astype(str) == "REC_H2")].copy()
    windows = []
    for _, r in parent.iterrows():
        windows.append((str(r.partition), pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)))
    for _, r in h2.iterrows():
        if pd.notna(r.recovery_entry_ts) and pd.notna(r.recovery_exit_ts):
            windows.append((str(r.partition), pd.Timestamp(r.recovery_entry_ts), pd.Timestamp(r.recovery_exit_ts)))
    return parent, h2, windows


def overlap_rate(q, partition, windows):
    w = [(a, b) for p, a, b in windows if p == partition]
    if not len(q):
        return np.nan
    hit = 0
    for _, r in q.iterrows():
        a, b = pd.Timestamp(r.entry_ts), pd.Timestamp(r.exit_ts)
        if any(a <= wb and b >= wa for wa, wb in w):
            hit += 1
    return hit / len(q)


def simulate_cell(m, partition, ref_min, hour, candidate, role):
    q = a2.trades_for(m, partition, int(ref_min), int(hour), FAMILY, TARGET_R)
    if q.empty:
        return q
    q = q.copy()
    q["candidate"] = candidate
    q["role"] = role
    q["candidate_scope"] = "A17"
    return q


def dev_row(q, candidate, mature_parent, mature_h2, windows):
    s = stats(q, "development")
    pos_raw = 0
    pos_stress = 0
    adequate = 0
    block = {}
    for bi in range(6):
        b = q[pd.to_numeric(q.dev_block, errors="coerce") == bi]
        bn = len(b)
        net = float(pd.to_numeric(b.pnl, errors="coerce").sum())
        net5 = float(pd.to_numeric(b.pnl_5bps, errors="coerce").sum())
        block[f"b{bi+1}_n"] = bn
        block[f"b{bi+1}_net"] = net
        block[f"b{bi+1}_net_5bps"] = net5
        if bn >= 20:
            adequate += 1
            if net > 0:
                pos_raw += 1
            if net5 > 0:
                pos_stress += 1

    mp = mature_parent[(mature_parent.role == "CENTRAL") & (mature_parent.partition == "development")]
    mh = mature_h2[(mature_h2.role == "CENTRAL") & (mature_h2.partition == "development")]
    mature_net = float(pd.to_numeric(mp.pnl, errors="coerce").sum() + pd.to_numeric(mh.recovery_pnl, errors="coerce").sum())
    mature_net5 = float(pd.to_numeric(mp.pnl_5bps, errors="coerce").sum() + pd.to_numeric(mh.recovery_pnl_5bps, errors="coerce").sum())

    eligible = bool(
        s["n"] >= 300
        and s["pf"] > 1.15
        and s["pf_5bps"] > 1.00
        and s["expectancy"] > 0
        and s["net"] > 0
        and s["expectancy_5bps"] > 0
        and s["net_5bps"] > 0
        and adequate >= 4
        and pos_raw >= 4
        and pos_stress >= 4
    )
    out = {
        "candidate": candidate,
        **s,
        "adequate_blocks": adequate,
        "positive_blocks_raw": pos_raw,
        "positive_blocks_5bps": pos_stress,
        "mature_stack_net": mature_net,
        "mature_stack_net_5bps": mature_net5,
        "additive_net": mature_net + s["net"],
        "additive_net_5bps": mature_net5 + s["net_5bps"],
        "mature_overlap_rate": overlap_rate(q, "development", windows),
        "eligible": eligible,
    }
    out.update(block)
    return out


def choose_winner(dev):
    q = dev[dev.eligible.astype(bool)].copy()
    if q.empty:
        return None
    q = q.sort_values(
        ["net_5bps", "pf_5bps", "net", "n", "anatomy_rank"],
        ascending=[False, False, False, False, True],
        kind="mergesort",
    )
    return q.iloc[0]


def write_result(cells, dev, oos, winner, coverage, status):
    lines = [
        "# SOL LONG Multi-Clock Expansion — A17 Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.",
        "",
        "A17 tests new clock habitats mechanically derived from the pre-existing A1 Development anatomy atlas. The mature A2+A4 18:00 UTC stack is unchanged.",
        "",
        "## Frozen candidate cells from prior A1 anatomy",
        "",
        "| Candidate | Ref | Clock UTC | Distance from 18 | A1 stable blocks | A1 break conversion | A1 median extension | Clock support | Ref support |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in cells.iterrows():
        lines.append(
            f"| {r.candidate} | {int(r.ref_min)}m | {int(r.hour):02d}:00 | {int(r.clock_distance_from_18)}h | {int(r.same_dom_blocks)}/6 | {pct(r.dominant_break_conversion)} | {fmt(r.dominant_median_extension_R,3)}R | R{int(r.clock_support_ref_min)}/{int(r.clock_support_hour):02d} | R{int(r.ref_support_ref_min)}/{int(r.ref_support_hour):02d} |"
        )

    lines += [
        "",
        "## Central Development economics",
        "",
        "| Candidate | N | Trades/wk | WR | PF | Exp | Net | 5bps PF | 5bps Exp | 5bps Net | +blocks raw/stress | Mature overlap | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for _, r in dev.iterrows():
        lines.append(
            f"| {r.candidate} | {int(r.n)} | {fmt(r.trades_per_week,2)} | {pct(r.wr)} | {fmt(r.pf)} | ${fmt(r.expectancy)} | ${fmt(r.net)} | {fmt(r.pf_5bps)} | ${fmt(r.expectancy_5bps)} | ${fmt(r.net_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {pct(r.mature_overlap_rate)} | {'YES' if bool(r.eligible) else 'NO'} |"
        )
    lines += ["", f"Frozen Development winner: **{winner.candidate if winner is not None else 'NONE'}**.", ""]

    if winner is not None and len(oos):
        lines += [
            "## Frozen OOS",
            "",
            "| Role | Partition | Cell | N | WR | PF | Net | 5bps PF | 5bps Net |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for _, r in oos.iterrows():
            lines.append(
                f"| {r.role} | {r.partition} | R{int(r.ref_min)}/{int(r.hour):02d} | {int(r.n)} | {pct(r.wr)} | {fmt(r.pf)} | ${fmt(r.net)} | {fmt(r.pf_5bps)} | ${fmt(r.net_5bps)} |"
            )
        exact = oos[oos.role == "CANDIDATE"]
        support = oos[oos.role != "CANDIDATE"]
        central_ok = bool(
            len(exact) == 2
            and (exact.net > 0).all()
            and (exact.net_5bps > 0).all()
            and (exact.pf > 1.0).all()
            and (exact.pf_5bps > 1.0).all()
        )
        sr = int((support.net > 0).sum())
        ss = int((support.net_5bps > 0).sum())
        lines += ["", f"Validation: **central_ok={central_ok}; support positive raw={sr}/4; support positive 5bps={ss}/4**.", ""]

    lines += [
        "## Decision",
        "",
        f"**Status: {status}**",
        "",
        "A17 does not authorize A4 H2 recovery in a new zone. A supported parent zone must test recovery transfer separately.",
        "",
        "Research only. Live Baba Bot remains unchanged.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    atlas = pd.read_csv(IN_ATLAS)
    cells = derive_cells(atlas)
    cells.to_csv(OUT_CELLS, index=False)

    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)
    mature_parent, mature_h2, windows = load_mature_windows()

    dev_rows = []
    all_trades = []
    for _, c in cells.iterrows():
        q = simulate_cell(m, "development", c.ref_min, c.hour, c.candidate, "CANDIDATE")
        all_trades.append(q)
        row = dev_row(q, c.candidate, mature_parent, mature_h2, windows)
        row["anatomy_rank"] = int(c.anatomy_rank)
        row["ref_min"] = int(c.ref_min)
        row["hour"] = int(c.hour)
        dev_rows.append(row)
    dev = pd.DataFrame(dev_rows)
    dev.to_csv(OUT_DEV, index=False)
    winner = choose_winner(dev)

    oos_rows = []
    if winner is not None:
        c = cells[cells.candidate == winner.candidate].iloc[0]
        tests = [
            ("CANDIDATE", int(c.ref_min), int(c.hour)),
            ("CLOCK_SUPPORT", int(c.clock_support_ref_min), int(c.clock_support_hour)),
            ("REF_SUPPORT", int(c.ref_support_ref_min), int(c.ref_support_hour)),
        ]
        for role, ref, hour in tests:
            for partition in ("external", "reference_validation"):
                q = simulate_cell(m, partition, ref, hour, c.candidate, role)
                all_trades.append(q)
                s = stats(q, partition)
                oos_rows.append({
                    "candidate": c.candidate,
                    "role": role,
                    "partition": partition,
                    "ref_min": ref,
                    "hour": hour,
                    **s,
                })
    oos = pd.DataFrame(oos_rows)
    oos.to_csv(OUT_OOS, index=False)

    if winner is None:
        status = "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_REJECTED_DEVELOPMENT"
    else:
        exact = oos[oos.role == "CANDIDATE"]
        support = oos[oos.role != "CANDIDATE"]
        central_ok = bool(
            len(exact) == 2
            and (exact.net > 0).all()
            and (exact.net_5bps > 0).all()
            and (exact.pf > 1.0).all()
            and (exact.pf_5bps > 1.0).all()
        )
        support_raw = int((support.net > 0).sum())
        support_stress = int((support.net_5bps > 0).sum())
        status = (
            "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_SUPPORTED_FOR_RECOVERY_INTEGRATION"
            if central_ok and support_raw >= 3 and support_stress >= 3
            else "SOL_LONG_MULTI_CLOCK_EXPANSION_A17_REJECTED_OOS"
        )

    trades = pd.concat([q for q in all_trades if q is not None and len(q)], ignore_index=True) if any(q is not None and len(q) for q in all_trades) else pd.DataFrame()
    trades.to_csv(OUT_TRADES, index=False)
    write_result(cells, dev, oos, winner, coverage, status)
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
