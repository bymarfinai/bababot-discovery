#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_discovery2_reset_g1_geometry as g1

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G3_DOWNSTREAM_STRUCTURE"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCK = 90
REF_MIN = 180
EXE_MIN = 720
BAR_MIN = 5
DEPTHS = (0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
CHECKS = (0.05, 0.10, 0.20)


def pct(x):
    return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = k / n
    zz = z * z
    den = 1 + zz / n
    center = p + zz / (2 * n)
    rad = z * math.sqrt((p * (1 - p) + zz / (4 * n)) / n)
    return (center - rad) / den


def candidate_specs():
    out = [
        {"label": "DIRECT", "kind": "DIRECT", "depth": np.nan, "simplicity": 0},
        {"label": "LEAVE", "kind": "LEAVE", "depth": np.nan, "simplicity": 1},
    ]
    for d in DEPTHS:
        out.append({"label": f"RETEST_D{int(round(d*100)):02d}", "kind": "RETEST", "depth": d, "simplicity": 2})
    return out


def build_parent_sessions(x5: pd.DataFrame, part: str) -> pd.DataFrame:
    idx = x5.index
    sess = g1.candidate_sessions(idx, CLOCK, REF_MIN, EXE_MIN, part)
    if len(sess) == 0:
        return pd.DataFrame()

    h = x5.high.to_numpy(float)
    l = x5.low.to_numpy(float)
    c = x5.close.to_numpy(float)
    ref_n = REF_MIN // BAR_MIN
    exe_n = EXE_MIN // BAR_MIN
    rows = []

    for r in sess.itertuples(index=False):
        start = int(r.start_pos)
        ref_ix = np.arange(start, start + ref_n)
        exe_start = start + ref_n
        H = float(h[ref_ix].max())
        L = float(l[ref_ix].min())
        R = H - L
        if not R > 0:
            continue

        sig_j = None
        for j in range(exe_n):
            ix = exe_start + j
            hi, lo, cl = h[ix], l[ix], c[ix]
            strict_up = cl > H
            strict_dn = cl < L
            if strict_up or strict_dn:
                break
            hit_hi = (hi >= H) and (cl <= H)
            hit_lo = (lo <= L) and (cl >= L)
            both = hit_hi and hit_lo
            if both or hit_lo:
                break
            if hit_hi:
                sig_j = j
                break

        if sig_j is None:
            continue
        sig_ix = exe_start + sig_j
        rows.append({
            "partition": part,
            "reference_start": r.rs,
            "execution_start": r.re,
            "execution_end": r.ee,
            "exe_start_pos": exe_start,
            "exe_n": exe_n,
            "H": H, "L": L, "R": R,
            "signal_j": sig_j,
            "signal_ts": idx[sig_ix] + pd.Timedelta(minutes=BAR_MIN),
        })
    return pd.DataFrame(rows)


def first_b00(x5: pd.DataFrame, p, spec):
    h = x5.high.to_numpy(float)
    l = x5.low.to_numpy(float)
    c = x5.close.to_numpy(float)
    H, L, R = float(p.H), float(p.L), float(p.R)
    start, n, sj = int(p.exe_start_pos), int(p.exe_n), int(p.signal_j)
    kind = spec["kind"]
    d = spec["depth"]
    left = False
    retested = False

    for j in range(sj + 1, n):
        ix = start + j
        hi, lo, cl = h[ix], l[ix], c[ix]
        strict_up = cl > H
        strict_dn = cl < L
        hit_hi = (hi >= H) and (cl <= H)
        hit_lo = (lo <= L) and (cl >= L)
        both = hit_hi and hit_lo

        if strict_dn or both:
            return None

        if kind == "DIRECT":
            if strict_up:
                return j
            continue

        if kind == "LEAVE":
            if strict_up:
                return j if left else None
            if hi < H:
                left = True
            continue

        # RETEST: breakout before the full leave/retest sequence permanently closes this candidate.
        if strict_up:
            return j if (left and retested) else None

        was_left = left
        if not left and hi < H:
            left = True
        if was_left and not retested:
            floor = H - float(d) * R
            if floor <= cl <= H:
                retested = True

    return None


def followthrough(x5: pd.DataFrame, p, b00_j: int):
    h = x5.high.to_numpy(float)
    c = x5.close.to_numpy(float)
    H, R = float(p.H), float(p.R)
    start, n = int(p.exe_start_pos), int(p.exe_n)
    bix = start + b00_j
    B = float(c[bix])
    out = {"b00_close": B}

    for q in CHECKS:
        key = f"x{int(round(q*100)):02d}"
        target = B + q * R
        success = False
        target_j = None
        terminal = "NO_RESOLVE"
        for j in range(b00_j + 1, n):
            ix = start + j
            hit = h[ix] >= target
            reentry = c[ix] < H
            if hit and reentry:
                terminal = "AMBIGUOUS_SAME_BAR"
                break
            if reentry:
                terminal = "RANGE_REENTRY"
                break
            if hit:
                success = True
                target_j = j
                terminal = "TARGET"
                break
        out[f"{key}_success"] = success
        out[f"{key}_terminal"] = terminal
        out[f"{key}_minutes"] = ((target_j - b00_j) * BAR_MIN) if target_j is not None else np.nan
    return out


def analyze_candidate(x5: pd.DataFrame, parents: pd.DataFrame, spec, return_audit=False):
    records = []
    for p in parents.itertuples(index=False):
        b00 = first_b00(x5, p, spec)
        rec = {
            "partition": p.partition,
            "label": spec["label"],
            "kind": spec["kind"],
            "depth": spec["depth"],
            "reference_start": p.reference_start,
            "execution_start": p.execution_start,
            "H": p.H, "L": p.L, "R": p.R,
            "signal_ts": p.signal_ts,
            "triggered": b00 is not None,
            "b00_j": b00 if b00 is not None else np.nan,
        }
        if b00 is not None:
            bix = int(p.exe_start_pos) + int(b00)
            rec["b00_ts"] = x5.index[bix] + pd.Timedelta(minutes=BAR_MIN)
            rec["pressure_to_b00_min"] = (int(b00) - int(p.signal_j)) * BAR_MIN
            rec.update(followthrough(x5, p, int(b00)))
        else:
            rec["b00_ts"] = pd.NaT
            rec["pressure_to_b00_min"] = np.nan
            rec["b00_close"] = np.nan
            for q in CHECKS:
                key = f"x{int(round(q*100)):02d}"
                rec[f"{key}_success"] = False
                rec[f"{key}_terminal"] = "NO_TRIGGER"
                rec[f"{key}_minutes"] = np.nan
        records.append(rec)

    A = pd.DataFrame(records)
    if return_audit:
        return A

    nparent = len(A)
    T = A[A.triggered].copy()
    nt = len(T)
    row = {
        "partition": parents.partition.iloc[0] if nparent else "",
        "label": spec["label"], "kind": spec["kind"], "depth": spec["depth"],
        "parent_signals": nparent,
        "triggers": nt,
        "participation": nt / nparent if nparent else np.nan,
        "median_pressure_to_b00_min": float(T.pressure_to_b00_min.median()) if nt else np.nan,
        "simplicity": spec["simplicity"],
    }
    for q in CHECKS:
        key = f"x{int(round(q*100)):02d}"
        wins = int(T[f"{key}_success"].sum()) if nt else 0
        row[f"{key}_wins"] = wins
        row[f"{key}_rate"] = wins / nt if nt else np.nan
    row["wilson_lb_x10"] = wilson_lb(int(row["x10_wins"]), nt)
    row["median_b00_to_x10_min"] = float(T.loc[T.x10_success, "x10_minutes"].median()) if int(row["x10_wins"]) else np.nan

    # Four blocks are defined over chronological parent-signal sessions, not only triggered rows.
    positive = 0
    qualified = []
    for bi, ix in enumerate(np.array_split(np.arange(nparent), 4), 1):
        B = A.iloc[ix]
        BT = B[B.triggered]
        bn = len(BT)
        x10 = float(BT.x10_success.mean()) if bn else np.nan
        x20 = float(BT.x20_success.mean()) if bn else np.nan
        row[f"block{bi}_n"] = bn
        row[f"block{bi}_x10"] = x10
        row[f"block{bi}_x20"] = x20
        if bn >= 10:
            qualified.append(x10)
            if x10 >= .45 and x20 >= .25:
                positive += 1
    row["positive_blocks"] = positive
    row["min_qualified_block_x10"] = min(qualified) if qualified else np.nan
    return row


def dev_scan(x5, parents):
    return pd.DataFrame([analyze_candidate(x5, parents, s, False) for s in candidate_specs()])


def build_leaderboard(D):
    D = D.copy()
    D["dev_gate"] = (
        (D.triggers >= 60) & (D.participation >= .25) &
        (D.x10_rate >= .50) & (D.x20_rate >= .30) &
        (D.wilson_lb_x10 >= .40) & (D.positive_blocks >= 3)
    )
    D["neighbors_available"] = 0
    D["neighbors_supportive"] = 0
    D["local_stable"] = True
    for i, r in D.iterrows():
        if r.kind != "RETEST":
            continue
        j = DEPTHS.index(float(r.depth))
        nd = []
        if j > 0: nd.append(DEPTHS[j-1])
        if j + 1 < len(DEPTHS): nd.append(DEPTHS[j+1])
        sup = 0
        for d in nd:
            x = D[(D.kind == "RETEST") & np.isclose(D.depth.astype(float), d)].iloc[0]
            if int(x.triggers) >= 50 and float(x.x10_rate) >= .45 and float(x.x20_rate) >= .25:
                sup += 1
        D.at[i, "neighbors_available"] = len(nd)
        D.at[i, "neighbors_supportive"] = sup
        D.at[i, "local_stable"] = sup >= 1
    D["candidate_eligible"] = D.dev_gate & D.local_stable
    D["retest_boundary"] = (D.kind == "RETEST") & D.depth.isin((min(DEPTHS), max(DEPTHS)))
    C = D[D.candidate_eligible].copy()
    C = C.sort_values(
        ["wilson_lb_x10", "min_qualified_block_x10", "x20_rate", "x10_rate", "triggers",
         "median_pressure_to_b00_min", "simplicity", "depth"],
        ascending=[False, False, False, False, False, True, True, True], na_position="last"
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C)+1)
    return D, C


def selected_spec(sel):
    return {"label": sel.label, "kind": sel.kind, "depth": float(sel.depth) if sel.kind == "RETEST" else np.nan, "simplicity": int(sel.simplicity)}


def holdout(x5, sel):
    spec = selected_spec(sel)
    rows, audits = [], []
    ok_all = True
    for part in ("external", "reference_validation"):
        P = build_parent_sessions(x5, part)
        r = analyze_candidate(x5, P, spec, False)
        ok = (
            int(r["triggers"]) >= 25 and float(r["participation"]) >= .20 and
            float(r["x10_rate"]) >= .45 and float(r["x20_rate"]) >= .25 and
            float(r["wilson_lb_x10"]) >= .30
        )
        r["replication_pass"] = bool(ok)
        rows.append(r); ok_all = ok_all and bool(ok)
        audits.append(analyze_candidate(x5, P, spec, True))
    Pdev = build_parent_sessions(x5, "development")
    audits.insert(1, analyze_candidate(x5, Pdev, spec, True))
    return pd.DataFrame(rows), pd.concat(audits, ignore_index=True), ok_all


def main():
    g1.base.synthetic_tests()
    x5, coverage = g1.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    Pdev = build_parent_sessions(x5, "development")
    parent_dev = g1.analyze_geometry(x5, CLOCK, REF_MIN, EXE_MIN, "development", False)["LONG"]
    if len(Pdev) != int(parent_dev["signals"]):
        raise AssertionError(f"parent-signal mismatch G3={len(Pdev)} G2={parent_dev['signals']}")

    D = dev_scan(x5, Pdev)
    direct = D[D.label == "DIRECT"].iloc[0]
    if int(direct.triggers) != int(parent_dev["same_side"]):
        raise AssertionError(f"DIRECT B00 mismatch {direct.triggers} vs G2 same_side {parent_dev['same_side']}")

    D2, C = build_leaderboard(D)
    D2.to_csv(OUT_DEV, index=False)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH Discovery 2 Reset — G3 Downstream Structure Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen G2 geometry: **LONG / 01:30 UTC / R180 / E720**.",
        f"Development parent pressure signals: **{len(Pdev)}**; frozen G2 same-side breakouts: **{int(parent_dev['same_side'])}**.",
        "B00 itself is not counted as continuation success; X05/X10/X20 are strictly post-B00 clean extensions before a close back below H.", "",
        "## Development structure atlas", "",
        "| Candidate | B00 N | Part. | X05 | X10 | X20 | Wilson X10 | Blocks | Neigh. | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in D2.itertuples(index=False):
        neigh = "-" if r.kind != "RETEST" else f"{int(r.neighbors_supportive)}/{int(r.neighbors_available)}"
        lines.append(f"| {r.label} | {int(r.triggers)} | {pct(r.participation)} | {pct(r.x05_rate)} | {pct(r.x10_rate)} | {pct(r.x20_rate)} | {pct(r.wilson_lb_x10)} | {int(r.positive_blocks)}/4 | {neigh} | {'PASS' if bool(r.candidate_eligible) else 'FAIL'} |")

    if len(C) == 0:
        status = "ETH_DISCOVERY2_RESET_G3_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", "No candidate passed the preregistered Development structure + stability gates.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text()); return

    sel = C.iloc[0]
    lines += [
        "", "## Development-selected structure", "",
        f"**{sel.label}**",
        f"B00 triggers **{int(sel.triggers)}** ({pct(sel.participation)} of parent pressure signals); X05 **{pct(sel.x05_rate)}**; X10 **{pct(sel.x10_rate)}**; X20 **{pct(sel.x20_rate)}**; Wilson X10 **{pct(sel.wilson_lb_x10)}**.",
        f"Median pressure→B00 **{float(sel.median_pressure_to_b00_min):.0f}m**; median B00→X10 **{float(sel.median_b00_to_x10_min):.0f}m**; positive blocks **{int(sel.positive_blocks)}/4**.", "",
        "Development blocks:", "",
        "| Block | B00 N | X10 | X20 |", "|---:|---:|---:|---:|"
    ]
    for b in range(1,5):
        lines.append(f"| {b} | {int(sel[f'block{b}_n'])} | {pct(sel[f'block{b}_x10'])} | {pct(sel[f'block{b}_x20'])} |")

    if bool(sel.retest_boundary):
        status = "ETH_DISCOVERY2_RESET_G3_RETEST_BOUNDARY_OPEN"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", "Selected RETEST depth is an outer sentinel. Per preregistration, holdouts remain closed and the retest-depth family is not localized.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text()); return

    H, A, supported = holdout(x5, sel)
    H.to_csv(OUT_OOS, index=False); A.to_csv(OUT_AUDIT, index=False)
    status = "ETH_DISCOVERY2_RESET_G3_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_G3_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")
    lines += ["", "## Historical replication", "", "| Partition | Parent N | B00 N | Part. | X05 | X10 | X20 | Wilson X10 | Gate |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.parent_signals)} | {int(r.triggers)} | {pct(r.participation)} | {pct(r.x05_rate)} | {pct(r.x10_rate)} | {pct(r.x20_rate)} | {pct(r.wilson_lb_x10)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")
    lines += [
        "", "## Development leaderboard", "",
        "| # | Candidate | B00 N | Part. | X10 | X20 | Wilson | Blocks | Boundary |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in C.itertuples(index=False):
        lines.append(f"| {int(r.dev_rank)} | {r.label} | {int(r.triggers)} | {pct(r.participation)} | {pct(r.x10_rate)} | {pct(r.x20_rate)} | {pct(r.wilson_lb_x10)} | {int(r.positive_blocks)}/4 | {'YES' if bool(r.retest_boundary) else 'NO'} |")
    lines += ["", f"**Status: {status}**", "", "G3 validates structure only. Entry and economics remain undiscovered on the reset lineage.", "Research/shadow only. No live promotion."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
