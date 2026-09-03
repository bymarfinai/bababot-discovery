#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A1_PATH = Path(__file__).resolve().parent / "sol_long_visit_break_a1.py"
spec = importlib.util.spec_from_file_location("sol_a1", A1_PATH)
a1 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a1)

IN_A1_EVENTS = ROOT / "SOL_LONG_VISIT_BREAK_A1_EVENTS.csv"
OUT_MD = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_Result.md"
OUT_CAND = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_CANDIDATES.csv"
OUT_SEL = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_SELECTED.csv"
OUT_TRADES = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_H1_ENTRY_ECON_A2_Status.txt"

NOTIONAL = 500.0
STRESS = 0.0005
ENTRY_ORDER = {
    "E0_RESTING_H": 0,
    "E1_H1_TOUCH_NEXT_OPEN": 1,
    "E2_H1_BREAK_NEXT_OPEN": 2,
    "E3_H1_RETEST_RECLAIM_NEXT_OPEN": 3,
}
CENTRAL = (240, 18)
SUPPORTS = {
    "CLOCK_SUPPORT": (240, 17),
    "REF_SUPPORT": (180, 18),
}
BAR = pd.Timedelta(minutes=5)


def derive_targets():
    e = pd.read_csv(IN_A1_EVENTS)
    q = e[(e.role == "CENTRAL") & (e.partition == "development") & (pd.to_numeric(e.first_break_visit, errors="coerce") == 1)].copy()
    x = pd.to_numeric(q.extension_before_reclaim_R, errors="coerce").dropna()
    if len(x) < 100:
        raise RuntimeError(f"Too few Development central H1 breakout extensions: {len(x)}")
    rows = []
    levels = []
    for quant in (0.35, 0.50, 0.65):
        raw = float(x.quantile(quant))
        rounded = max(0.05, np.floor((raw + 1e-12) / 0.05) * 0.05)
        rounded = round(float(rounded), 10)
        rows.append((quant, raw, rounded))
        levels.append(rounded)
    return rows, tuple(sorted(set(levels)))


def part_bounds(partition):
    return a1.PARTS[partition]


def dev_block(ts):
    return a1.dev_block(pd.Timestamp(ts))


def session_iter(m, partition, ref_min, hour):
    pa, pz = part_bounds(partition)
    a = max(pa, m["start"])
    z = min(pz, m["end"])
    if a >= z:
        return
    idx = m["idx"]
    hi = m["high"]
    lo = m["low"]
    day0 = a.normalize()
    day1 = (z - BAR).normalize()
    for day in pd.date_range(day0, day1, freq="D", tz="UTC"):
        es = day + pd.Timedelta(hours=hour)
        rs = es - pd.Timedelta(minutes=ref_min)
        ee = es + pd.Timedelta(minutes=a1.XMIN)
        if rs < a or ee > z or rs < m["start"] or ee > m["end"]:
            continue
        ra = int(idx.searchsorted(rs, "left"))
        pos = int(idx.searchsorted(es, "left"))
        endpos = int(idx.searchsorted(ee, "left"))
        if ra >= len(idx) or pos >= len(idx) or endpos <= pos:
            continue
        if idx[ra] != rs or idx[pos] != es:
            continue
        if pos - ra != ref_min // 5 or endpos - pos != a1.X_BARS:
            continue
        if idx[endpos - 1] != ee - BAR:
            continue
        H = float(np.max(hi[ra:pos]))
        L = float(np.min(lo[ra:pos]))
        if H <= L:
            continue
        yield {
            "execution_start": es,
            "ref_min": ref_min,
            "hour": hour,
            "partition": partition,
            "dev_block": dev_block(es),
            "pos": pos,
            "endpos": endpos,
            "H": H,
            "L": L,
            "R": H - L,
        }


def h1_geometry(m, s):
    hi = m["high"]
    lo = m["low"]
    cl = m["close"]
    pos, endpos = s["pos"], s["endpos"]
    h1 = -1
    for i in range(pos, endpos):
        if float(hi[i]) >= s["H"]:
            h1 = i
            break
    if h1 < 0:
        return None
    h1_end = h1
    break_i = -1
    i = h1
    while i < endpos and float(hi[i]) >= s["H"]:
        h1_end = i
        if break_i < 0 and float(cl[i]) > s["H"]:
            break_i = i
        i += 1
    retest_i = -1
    if break_i >= 0:
        for j in range(break_i + 1, endpos - 1):
            if float(lo[j]) <= s["H"] and float(cl[j]) > s["H"]:
                retest_i = j
                break
    return {"h1_i": h1, "h1_end_i": h1_end, "break_i": break_i, "retest_i": retest_i}


def entry_for(m, s, g, family):
    op = m["open"] if "open" in m else None
    idx = m["idx"]
    if family == "E0_RESTING_H":
        return {"entry_i": g["h1_i"], "entry_price": s["H"], "eval_start_i": g["h1_i"] + 1, "known_break": g["break_i"] == g["h1_i"]}
    if family == "E1_H1_TOUCH_NEXT_OPEN":
        ei = g["h1_i"] + 1
        if ei >= s["endpos"]:
            return None
        return {"entry_i": ei, "entry_price": float(op[ei]), "eval_start_i": ei, "known_break": g["break_i"] >= 0 and g["break_i"] < ei}
    if family == "E2_H1_BREAK_NEXT_OPEN":
        if g["break_i"] < 0:
            return None
        ei = g["break_i"] + 1
        if ei >= s["endpos"]:
            return None
        return {"entry_i": ei, "entry_price": float(op[ei]), "eval_start_i": ei, "known_break": True}
    if family == "E3_H1_RETEST_RECLAIM_NEXT_OPEN":
        if g["retest_i"] < 0:
            return None
        ei = g["retest_i"] + 1
        if ei >= s["endpos"]:
            return None
        return {"entry_i": ei, "entry_price": float(op[ei]), "eval_start_i": ei, "known_break": True}
    raise ValueError(family)


def simulate_one(m, s, family, target_R):
    g = h1_geometry(m, s)
    if g is None:
        return None
    ent = entry_for(m, s, g, family)
    if ent is None:
        return None
    op, hi, cl = m["open"], m["high"], m["close"]
    idx = m["idx"]
    target = s["H"] + target_R * s["R"]
    entry_i = int(ent["entry_i"])
    entry_price = float(ent["entry_price"])
    confirmed = bool(ent["known_break"])
    exit_i = s["endpos"] - 1
    exit_price = float(cl[exit_i])
    exit_reason = "TIME"
    invalidation_close_i = -1

    for i in range(int(ent["eval_start_i"]), s["endpos"]):
        if not confirmed and g["break_i"] >= 0 and i >= g["break_i"]:
            confirmed = True

        if i >= entry_i + 1 and float(hi[i]) >= target:
            exit_i = i
            exit_price = target
            exit_reason = "TARGET"
            break

        bad = (float(cl[i]) <= s["H"]) if confirmed else (float(cl[i]) < s["L"])
        if bad:
            invalidation_close_i = i
            ni = i + 1
            if ni < s["endpos"]:
                exit_i = ni
                exit_price = float(op[ni])
                exit_reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
            else:
                exit_i = i
                exit_price = float(cl[i])
                exit_reason = "TIME_AFTER_FINAL_INVALIDATION"
            break

    ret = exit_price / entry_price - 1.0
    pnl = ret * NOTIONAL
    ret5 = ret - STRESS
    pnl5 = ret5 * NOTIONAL
    return {
        "partition": s["partition"],
        "dev_block": s["dev_block"],
        "ref_min": s["ref_min"],
        "hour": s["hour"],
        "execution_start": s["execution_start"],
        "family": family,
        "target_R": target_R,
        "H": s["H"],
        "L": s["L"],
        "R": s["R"],
        "h1_ts": idx[g["h1_i"]],
        "h1_break_ts": idx[g["break_i"]] if g["break_i"] >= 0 else pd.NaT,
        "entry_ts": idx[entry_i],
        "entry_price": entry_price,
        "entry_F": (entry_price - s["L"]) / s["R"],
        "exit_ts": idx[exit_i],
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "return": ret,
        "pnl": pnl,
        "return_5bps": ret5,
        "pnl_5bps": pnl5,
        "won": pnl > 0,
        "won_5bps": pnl5 > 0,
        "h1_break_confirmed": g["break_i"] >= 0,
        "invalidation_close_ts": idx[invalidation_close_i] if invalidation_close_i >= 0 else pd.NaT,
    }


def make_market_with_open(x):
    m = a1.market(x)
    m["open"] = x.open.to_numpy(dtype=float, copy=False)
    return m


def trades_for(m, partition, ref_min, hour, family, target_R):
    rows = []
    for s in session_iter(m, partition, ref_min, hour):
        r = simulate_one(m, s, family, target_R)
        if r is not None:
            rows.append(r)
    return pd.DataFrame(rows)


def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gains = float(x[x > 0].sum())
    losses = float(-x[x < 0].sum())
    if losses == 0:
        return np.inf if gains > 0 else np.nan
    return gains / losses


def max_loss_streak(vals):
    mx = cur = 0
    for v in vals:
        if v <= 0:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return mx


def weeks_for(partition):
    a, b = part_bounds(partition)
    return float((b - a) / pd.Timedelta(weeks=1))


def summarize(t, partition):
    if t.empty:
        return {
            "n": 0, "trades_per_week": 0.0, "wr": np.nan, "pf": np.nan, "expectancy": np.nan, "net": 0.0,
            "max_loss_streak": 0, "wr_5bps": np.nan, "pf_5bps": np.nan, "expectancy_5bps": np.nan, "net_5bps": 0.0,
        }
    t = t.sort_values("entry_ts")
    return {
        "n": len(t),
        "trades_per_week": len(t) / weeks_for(partition),
        "wr": float((t.pnl > 0).mean()),
        "pf": pf(t.pnl),
        "expectancy": float(t.pnl.mean()),
        "net": float(t.pnl.sum()),
        "max_loss_streak": max_loss_streak(t.pnl.tolist()),
        "wr_5bps": float((t.pnl_5bps > 0).mean()),
        "pf_5bps": pf(t.pnl_5bps),
        "expectancy_5bps": float(t.pnl_5bps.mean()),
        "net_5bps": float(t.pnl_5bps.sum()),
    }


def dev_candidate(t, family, target_R):
    s = summarize(t, "development")
    block_pf = []
    adequate = good = 0
    minpf = np.inf
    for bi in range(6):
        b = t[t.dev_block == bi]
        bp = pf(b.pnl) if len(b) else np.nan
        bn = float(b.pnl.sum()) if len(b) else 0.0
        if len(b) >= 15:
            adequate += 1
            block_pf.append(bp)
            if pd.notna(bp):
                minpf = min(minpf, bp)
            if pd.notna(bp) and bp > 1 and bn > 0:
                good += 1
        s[f"b{bi+1}_n"] = len(b)
        s[f"b{bi+1}_pf"] = bp
        s[f"b{bi+1}_net"] = bn
    if minpf == np.inf:
        minpf = np.nan
    eligible = bool(
        s["n"] >= 120
        and adequate >= 5
        and pd.notna(s["pf"]) and s["pf"] > 1.15
        and s["expectancy"] > 0
        and pd.notna(s["pf_5bps"]) and s["pf_5bps"] > 1.00
        and s["expectancy_5bps"] > 0
        and good >= 4
        and (pd.isna(minpf) or minpf >= 0.70)
    )
    return {
        "family": family,
        "family_order": ENTRY_ORDER[family],
        "target_R": target_R,
        **s,
        "adequate_blocks": adequate,
        "profitable_blocks": good,
        "min_adequate_block_pf": minpf,
        "eligible": eligible,
    }


def choose_candidate(c):
    q = c[c.eligible].copy()
    if q.empty:
        return None
    return q.sort_values(
        ["profitable_blocks", "min_adequate_block_pf", "pf_5bps", "pf", "expectancy", "n", "family_order", "target_R"],
        ascending=[False, False, False, False, False, False, True, True],
    ).iloc[0]


def pct(v):
    return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def num(v, d=2):
    if pd.isna(v):
        return "-"
    if np.isinf(v):
        return "inf"
    return f"{float(v):.{d}f}"


def main():
    target_rows, target_levels = derive_targets()
    x, coverage = a1.load5()
    m = make_market_with_open(x)

    cand_rows = []
    dev_trade_frames = []
    for family in ENTRY_ORDER:
        for target_R in target_levels:
            t = trades_for(m, "development", CENTRAL[0], CENTRAL[1], family, target_R)
            if not t.empty:
                t["role"] = "CENTRAL"
                t["candidate_scope"] = "DEVELOPMENT_SCREEN"
                dev_trade_frames.append(t)
            cand_rows.append(dev_candidate(t, family, target_R))

    cand = pd.DataFrame(cand_rows)
    cand.to_csv(OUT_CAND, index=False)
    winner = choose_candidate(cand)

    if winner is None:
        status = "SOL_LONG_H1_ENTRY_ECON_A2_NO_DEVELOPMENT_EDGE"
        pd.DataFrame().to_csv(OUT_SEL, index=False)
        all_dev = pd.concat(dev_trade_frames, ignore_index=True) if dev_trade_frames else pd.DataFrame()
        all_dev.to_csv(OUT_TRADES, index=False)
        lines = [
            "# SOL LONG H1 Entry Economics — A2 Result",
            "",
            f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
            "",
            "A2 froze H1 as the structural breakout visit and tested actual economics for four causal entry timings.",
            "",
            "## Native target derivation",
            "",
        ]
        for q, raw, rounded in target_rows:
            lines.append(f"- Q{int(q*100)} raw extension = **{raw:.3f}R** -> candidate **E{int(rounded*100):02d}**.")
        lines += ["", "## Development candidates", "", "| Entry | Target | N | WR | PF | Exp/trade | Net | 5bps PF | 5bps Exp | Profitable blocks | Pass |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for _, r in cand.iterrows():
            lines.append(f"| {r.family} | E{int(r.target_R*100):02d} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.net)} | {num(r.pf_5bps)} | ${num(r.expectancy_5bps)} | {int(r.profitable_blocks)}/6 | {'YES' if r.eligible else 'NO'} |")
        lines += ["", "## Decision", "", f"**Status: {status}**", "", "No preregistered entry × native-target candidate passed the Development economic screen. OOS was not opened and no entry is frozen.", "", "Research only. Live Baba Bot remains unchanged."]
        OUT_MD.write_text("\n".join(lines) + "\n")
        OUT_STATUS.write_text(status + "\n")
        return

    family = str(winner.family)
    target_R = float(winner.target_R)
    selected_rows = []
    winner_trade_frames = []

    # Development central winner
    devt = trades_for(m, "development", CENTRAL[0], CENTRAL[1], family, target_R)
    devt["role"] = "CENTRAL"
    devt["candidate_scope"] = "FROZEN_WINNER"
    winner_trade_frames.append(devt)
    selected_rows.append({"role": "CENTRAL", "partition": "development", "ref_min": CENTRAL[0], "hour": CENTRAL[1], "family": family, "target_R": target_R, **summarize(devt, "development")})

    central_oos_ok = True
    support_ok = {k: True for k in SUPPORTS}
    for role, (ref_min, hour) in [("CENTRAL", CENTRAL), *SUPPORTS.items()]:
        for partition in ("external", "reference_validation"):
            t = trades_for(m, partition, ref_min, hour, family, target_R)
            t["role"] = role
            t["candidate_scope"] = "FROZEN_WINNER"
            winner_trade_frames.append(t)
            sm = summarize(t, partition)
            selected_rows.append({"role": role, "partition": partition, "ref_min": ref_min, "hour": hour, "family": family, "target_R": target_R, **sm})
            if role == "CENTRAL":
                central_oos_ok = central_oos_ok and bool(
                    sm["n"] >= 40 and pd.notna(sm["pf"]) and sm["pf"] > 1.0 and sm["expectancy"] > 0
                    and pd.notna(sm["pf_5bps"]) and sm["pf_5bps"] > 0.90 and sm["net_5bps"] > -10
                )
            else:
                support_ok[role] = support_ok[role] and bool(pd.notna(sm["pf"]) and sm["pf"] > 1.0 and sm["net"] > 0)

    topology_ok = any(support_ok.values())
    supported = bool(central_oos_ok and topology_ok)
    status = "SOL_LONG_H1_ENTRY_ECON_A2_SUPPORTED" if supported else "SOL_LONG_H1_ENTRY_ECON_A2_FAILED_OOS"
    sel = pd.DataFrame(selected_rows)
    sel.to_csv(OUT_SEL, index=False)
    pd.concat(winner_trade_frames, ignore_index=True).to_csv(OUT_TRADES, index=False)

    lines = [
        "# SOL LONG H1 Entry Economics — A2 Result",
        "",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.",
        "",
        "A2 optimizes actual trade economics, not H1/H2 rate.",
        "",
        "## Native target derivation",
        "",
    ]
    for q, raw, rounded in target_rows:
        lines.append(f"- Q{int(q*100)} raw H1 extension = **{raw:.3f}R** -> **E{int(rounded*100):02d}**.")
    lines += ["", "## Development candidate screen", "", "| Entry | Target | N | WR | PF | Exp/trade | Net | 5bps PF | 5bps Exp | Good blocks | Pass |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in cand.iterrows():
        lines.append(f"| {r.family} | E{int(r.target_R*100):02d} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.net)} | {num(r.pf_5bps)} | ${num(r.expectancy_5bps)} | {int(r.profitable_blocks)}/6 | {'YES' if r.eligible else 'NO'} |")
    lines += [
        "",
        "## Frozen Development winner",
        "",
        f"- Entry: **{family}**.",
        f"- Target: **E{int(target_R*100):02d}**.",
        f"- Development N: **{int(winner.n)}**; WR **{pct(winner.wr)}**; PF **{num(winner.pf)}**; expectancy **${num(winner.expectancy)}**; net **${num(winner.net)}**.",
        f"- Development 5bps PF **{num(winner.pf_5bps)}**; expectancy **${num(winner.expectancy_5bps)}**; net **${num(winner.net_5bps)}**.",
        "",
        "## OOS and topology economics",
        "",
        "| Role | Partition | N | WR | PF | Exp/trade | Net | 5bps PF | 5bps Net |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in sel.iterrows():
        lines.append(f"| {r.role} | {r.partition} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | ${num(r.expectancy)} | ${num(r.net)} | {num(r.pf_5bps)} | ${num(r.net_5bps)} |")
    lines += ["", "## Decision", "", f"**Status: {status}**", ""]
    if supported:
        lines += [
            f"The frozen H1 structure supports **{family} -> E{int(target_R*100):02d}** under the preregistered central OOS and topology economic gates.",
            "",
            "This is the first SOL LONG result in the restarted lineage that is supported by actual WR/PF/expectancy rather than an H-visit proxy. It is still research-only and is not promoted to the live bot.",
        ]
    else:
        lines += [
            f"Development selected **{family} -> E{int(target_R*100):02d}**, but the exact frozen trade rule did not pass all OOS/topology economics. No SOL LONG entry is promoted.",
        ]
    lines += ["", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(status + "\n")


if __name__ == "__main__":
    main()
