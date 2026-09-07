#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A20_PATH = Path(__file__).resolve().parent / "sol_long_additional_clocks_a20.py"
spec = importlib.util.spec_from_file_location("sol_a20", A20_PATH)
a20 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a20)
a2 = a20.a17.a2

REF_MIN = 360
HOUR = 15
BASE_FAMILY = "E0_RESTING_H"
BASE_TARGET = 0.40
FAMILIES = tuple(a2.ENTRY_ORDER.keys())
STRESS = a2.STRESS
EPS = 1e-12

OUT_TARGETS = ROOT / "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_TARGETS.csv"
OUT_DEV = ROOT / "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_TRADES.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_Status.txt"

EXPECTED_BASE = {
    "development": {"n": 601, "net": 338.91, "net5": 188.66},
    "external": {"n": 281, "net": 419.82, "net5": 349.57},
    "reference_validation": {"n": 337, "net": 263.33, "net5": 179.08},
}


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors="coerce").dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl == 0:
        return np.inf if gp > 0 else np.nan
    return gp / gl


def max_loss_streak(vals):
    best = cur = 0
    for v in pd.to_numeric(pd.Series(vals), errors="coerce").fillna(0.0):
        if float(v) <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def summarize(q):
    if q.empty:
        return {"n": 0, "wr": np.nan, "pf": np.nan, "expectancy": np.nan, "net": 0.0,
                "wr_5bps": np.nan, "pf_5bps": np.nan, "expectancy_5bps": np.nan, "net_5bps": 0.0,
                "max_loss_streak": 0}
    p = pd.to_numeric(q.pnl, errors="coerce")
    p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    return {
        "n": len(q),
        "wr": float((p > 0).mean()),
        "pf": pf(p),
        "expectancy": float(p.mean()),
        "net": float(p.sum()),
        "wr_5bps": float((p5 > 0).mean()),
        "pf_5bps": pf(p5),
        "expectancy_5bps": float(p5.mean()),
        "net_5bps": float(p5.sum()),
        "max_loss_streak": max_loss_streak(p),
    }


def baseline_reconciles(m):
    rows = []
    ok = True
    frames = []
    for part in ("development", "external", "reference_validation"):
        q = a2.trades_for(m, part, REF_MIN, HOUR, BASE_FAMILY, BASE_TARGET).copy()
        q["candidate"] = "BASE_E0_E40"
        q["scope"] = "BASELINE"
        frames.append(q)
        s = summarize(q)
        exp = EXPECTED_BASE[part]
        row_ok = bool(
            int(s["n"]) == int(exp["n"])
            and abs(float(s["net"]) - float(exp["net"])) <= 0.06
            and abs(float(s["net_5bps"]) - float(exp["net5"])) <= 0.06
        )
        ok = ok and row_ok
        rows.append({"partition": part, **s, "reconciles": row_ok})
    return ok, pd.DataFrame(rows), frames


def derive_native_targets(m):
    hi = m["high"]
    cl = m["close"]
    exts = []
    sessions = 0
    broken = 0
    for s in a2.session_iter(m, "development", REF_MIN, HOUR):
        sessions += 1
        g = a2.h1_geometry(m, s)
        if g is None or int(g["break_i"]) < 0:
            continue
        broken += 1
        bi = int(g["break_i"])
        reclaim = -1
        for j in range(bi + 1, int(s["endpos"])):
            if float(cl[j]) <= float(s["H"]):
                reclaim = j
                break
        end = reclaim if reclaim >= 0 else int(s["endpos"])
        a = bi + 1
        if a >= end:
            ext = 0.0
        else:
            ext = max(0.0, (float(np.max(hi[a:end])) - float(s["H"])) / float(s["R"]))
        if np.isfinite(ext) and ext > 0:
            exts.append(ext)
    x = pd.Series(exts, dtype=float)
    if len(x) < 100:
        raise RuntimeError(f"Too few positive native extensions: {len(x)}")
    rows = []
    levels = []
    for quant in (0.35, 0.50, 0.65):
        raw = float(x.quantile(quant))
        rounded = max(0.05, np.floor((raw + EPS) / 0.05) * 0.05)
        rounded = round(float(rounded), 10)
        rows.append({"quantile": quant, "raw_extension_R": raw, "target_R": rounded,
                     "development_sessions": sessions, "break_sessions": broken,
                     "positive_extension_n": len(x)})
        levels.append(rounded)
    return pd.DataFrame(rows), tuple(sorted(set(levels)))


def dev_row(q, family, target, base_dev):
    s = summarize(q)
    adequate = positive5 = 0
    min_pf5 = np.inf
    block = {}
    for bi in range(6):
        b = q[pd.to_numeric(q.dev_block, errors="coerce") == bi]
        bn = len(b)
        bp5 = pf(pd.to_numeric(b.pnl_5bps, errors="coerce")) if bn else np.nan
        bnet5 = float(pd.to_numeric(b.pnl_5bps, errors="coerce").sum()) if bn else 0.0
        block[f"b{bi+1}_n"] = bn
        block[f"b{bi+1}_pf_5bps"] = bp5
        block[f"b{bi+1}_net_5bps"] = bnet5
        if bn >= 15:
            adequate += 1
            if pd.notna(bp5):
                min_pf5 = min(min_pf5, float(bp5))
            if bnet5 > 0:
                positive5 += 1
    if min_pf5 == np.inf:
        min_pf5 = np.nan
    eligible = bool(
        s["n"] >= 200
        and pd.notna(s["pf"]) and s["pf"] > 1.15
        and s["net"] > 0
        and pd.notna(s["pf_5bps"]) and s["pf_5bps"] >= float(base_dev.pf_5bps) + 0.10 - EPS
        and s["expectancy_5bps"] >= float(base_dev.expectancy_5bps) + 0.10 - EPS
        and s["net_5bps"] >= 0.80 * float(base_dev.net_5bps) - EPS
        and adequate >= 4
        and positive5 >= 4
        and pd.notna(min_pf5) and min_pf5 >= 0.70 - EPS
    )
    return {
        "family": family,
        "family_order": int(a2.ENTRY_ORDER[family]),
        "target_R": target,
        **s,
        "adequate_blocks": adequate,
        "positive_blocks_5bps": positive5,
        "min_adequate_block_pf_5bps": min_pf5,
        "eligible": eligible,
        **block,
    }


def choose(dev):
    q = dev[dev.eligible.astype(bool)].copy()
    if q.empty:
        return None
    q = q.sort_values(
        ["positive_blocks_5bps", "min_adequate_block_pf_5bps", "pf_5bps", "expectancy_5bps", "net_5bps", "n", "family_order", "target_R"],
        ascending=[False, False, False, False, False, False, True, True],
        kind="mergesort",
    )
    return q.iloc[0]


def pct(v):
    return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"


def num(v, d=2):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def pooled_stats(frames):
    q = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return summarize(q)


def main():
    x, coverage = a2.a1.load5()
    m = a2.make_market_with_open(x)

    recon_ok, base, base_frames = baseline_reconciles(m)
    if not recon_ok:
        status = "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_RECONCILIATION_FAIL"
        base.to_csv(OUT_OOS, index=False)
        pd.DataFrame().to_csv(OUT_TARGETS, index=False)
        pd.DataFrame().to_csv(OUT_DEV, index=False)
        pd.concat(base_frames, ignore_index=True).to_csv(OUT_TRADES, index=False)
        OUT_MD.write_text("# SOL LONG 15UTC Native Entry + Target — A46 Result\n\n**Status: %s**\n\nFrozen A20 baseline failed count/net reconciliation. No calibration test was opened.\n" % status, encoding="utf-8")
        OUT_STATUS.write_text(status + "\n", encoding="utf-8")
        print(status)
        return

    targets, levels = derive_native_targets(m)
    targets.to_csv(OUT_TARGETS, index=False)
    base_dev = base[base.partition == "development"].iloc[0]

    dev_rows = []
    trade_frames = list(base_frames)
    for family in FAMILIES:
        for target in levels:
            q = a2.trades_for(m, "development", REF_MIN, HOUR, family, float(target)).copy()
            q["candidate"] = f"{family}_E{int(round(target*100)):02d}"
            q["scope"] = "DEVELOPMENT_GRID"
            trade_frames.append(q)
            dev_rows.append(dev_row(q, family, float(target), base_dev))
    dev = pd.DataFrame(dev_rows)
    dev.to_csv(OUT_DEV, index=False)
    winner = choose(dev)

    oos_rows = []
    quality_route = return_route = False
    if winner is None:
        status = "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_REJECTED_DEVELOPMENT"
    else:
        family = str(winner.family)
        target = float(winner.target_R)
        cand_oos_frames = []
        base_oos_frames = []
        for part in ("external", "reference_validation"):
            bq = a2.trades_for(m, part, REF_MIN, HOUR, BASE_FAMILY, BASE_TARGET).copy()
            cq = a2.trades_for(m, part, REF_MIN, HOUR, family, target).copy()
            bq["candidate"] = "BASE_E0_E40"; bq["scope"] = "OOS_BASELINE"
            cq["candidate"] = f"{family}_E{int(round(target*100)):02d}"; cq["scope"] = "OOS_FROZEN_CHALLENGER"
            trade_frames.extend([bq, cq])
            base_oos_frames.append(bq); cand_oos_frames.append(cq)
            oos_rows.append({"role": "BASELINE", "partition": part, "family": BASE_FAMILY, "target_R": BASE_TARGET, **summarize(bq)})
            oos_rows.append({"role": "CHALLENGER", "partition": part, "family": family, "target_R": target, **summarize(cq)})

        bo = pooled_stats(base_oos_frames)
        co = pooled_stats(cand_oos_frames)
        oos_rows.append({"role": "BASELINE_POOLED", "partition": "pooled_oos", "family": BASE_FAMILY, "target_R": BASE_TARGET, **bo})
        oos_rows.append({"role": "CHALLENGER_POOLED", "partition": "pooled_oos", "family": family, "target_R": target, **co})

        oq = pd.DataFrame(oos_rows)
        cparts = oq[(oq.role == "CHALLENGER") & oq.partition.isin(["external", "reference_validation"])]
        both_positive = bool(
            len(cparts) == 2
            and (cparts.pf > 1).all() and (cparts.net > 0).all()
            and (cparts.pf_5bps > 1).all() and (cparts.net_5bps > 0).all()
        )
        quality_route = bool(
            both_positive
            and co["pf_5bps"] >= bo["pf_5bps"] + 0.10 - EPS
            and co["expectancy_5bps"] >= 1.20 * bo["expectancy_5bps"] - EPS
            and co["net_5bps"] >= 0.70 * bo["net_5bps"] - EPS
        )
        return_route = bool(
            both_positive
            and co["net_5bps"] >= bo["net_5bps"] - EPS
            and co["pf_5bps"] >= bo["pf_5bps"] - 0.05 - EPS
        )
        status = "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_SUPPORTED" if (quality_route or return_route) else "SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_REJECTED_OOS"

    oos = pd.DataFrame(oos_rows)
    oos.to_csv(OUT_OOS, index=False)
    trades = pd.concat([q for q in trade_frames if q is not None and len(q)], ignore_index=True)
    trades.to_csv(OUT_TRADES, index=False)

    lines = [
        "# SOL LONG 15UTC Native Entry + Target Calibration — A46 Result", "",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
        "A46 keeps the A20 `R360/15` habitat frozen and calibrates only execution timing + target economics natively in Development.", "",
        f"A20 baseline reconciliation: **{recon_ok}**.", "",
        "## Frozen A20 baseline", "",
        "| Partition | N | WR | PF | Net | 5bps WR | 5bps PF | 5bps Exp | 5bps Net |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in base.iterrows():
        lines.append(f"| {r.partition} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.net)} | {pct(r.wr_5bps)} | {num(r.pf_5bps)} | ${num(r.expectancy_5bps)} | ${num(r.net_5bps)} |")

    lines += ["", "## Native target derivation", "",
              "| Quantile | Raw extension | Frozen target | Positive extension N |",
              "|---|---:|---:|---:|"]
    for _, r in targets.iterrows():
        lines.append(f"| Q{int(round(100*r['quantile']))} | {num(r.raw_extension_R,3)}R | E{int(round(100*r.target_R)):02d} | {int(r.positive_extension_n)} |")
    lines += ["", "Native target set: **" + ", ".join(f"E{int(round(100*x)):02d}" for x in levels) + "**.", ""]

    lines += ["## Development calibration grid", "",
              "| Entry | Target | N | WR | PF | 5bps PF | 5bps Exp | 5bps Net | +blocks | Min block PF | Eligible |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in dev.sort_values(["family_order", "target_R"]).iterrows():
        lines.append(f"| {r.family} | E{int(round(r.target_R*100)):02d} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {num(r.pf_5bps)} | ${num(r.expectancy_5bps)} | ${num(r.net_5bps)} | {int(r.positive_blocks_5bps)}/{int(r.adequate_blocks)} | {num(r.min_adequate_block_pf_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |")

    lines += ["", f"Frozen Development challenger: **{('NONE' if winner is None else str(winner.family) + ' / E' + str(int(round(float(winner.target_R)*100))).zfill(2))}**.", ""]

    if len(oos):
        lines += ["## Frozen OOS comparison", "",
                  "| Role | Partition | Entry | Target | N | PF | Net | 5bps PF | 5bps Exp | 5bps Net |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in oos.iterrows():
            lines.append(f"| {r.role} | {r.partition} | {r.family} | E{int(round(r.target_R*100)):02d} | {int(r.n)} | {num(r.pf)} | ${num(r.net)} | {num(r.pf_5bps)} | ${num(r.expectancy_5bps)} | ${num(r.net_5bps)} |")
        lines += ["", f"QUALITY route: **{quality_route}**. RETURN route: **{return_route}**.", ""]

    lines += ["## Decision", "", f"**Status: {status}**", ""]
    if status.endswith("SUPPORTED"):
        lines += ["The 15UTC habitat supports a native execution/target challenger under the preregistered OOS economics gate. This is a calibration result, not permission to alter other SOL sleeves."]
    elif status.endswith("REJECTED_DEVELOPMENT"):
        lines += ["No native entry/target challenger cleared the frozen Development improvement gate. Keep A20 E0/E40; do not open OOS for tuning."]
    else:
        lines += ["A Development challenger existed but did not improve/retain OOS economics enough under the frozen gate. Keep A20 E0/E40; no OOS retuning."]
    lines += ["", "Research only. Live Baba Bot remains unchanged."]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_STATUS.write_text(status + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
