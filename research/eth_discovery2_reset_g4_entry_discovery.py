#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_discovery2_reset_g1_geometry as g1
import eth_discovery2_reset_g3_downstream_structure as g3

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_RESET_G4_ENTRY_DISCOVERY"
OUT_DEV = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_OOS = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_AUDIT = ROOT / f"{PFX}_SelectedAudit.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR_MIN = 5
LEVELS = (0.00, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12)
WAITS = (5, 15, 30, 60)
CHECKS = (0.05, 0.10, 0.20)
DIRECT = {"label": "DIRECT", "kind": "DIRECT", "depth": np.nan, "simplicity": 0}


def pct(x):
    return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return np.nan
    p = k / n
    zz = z * z
    den = 1 + zz / n
    center = p + zz / (2*n)
    rad = z * math.sqrt((p*(1-p) + zz/(4*n))/n)
    return (center - rad) / den


def candidate_specs():
    out = [{"label": "NEXT_OPEN", "kind": "NEXT_OPEN", "q": np.nan, "wait_min": 0}]
    for q in LEVELS:
        for w in WAITS:
            out.append({
                "label": f"L{int(round(q*100)):02d}_W{w:02d}",
                "kind": "LIMIT", "q": q, "wait_min": w,
            })
    return out


def build_b00_cases(x5: pd.DataFrame, part: str) -> pd.DataFrame:
    P = g3.build_parent_sessions(x5, part)
    rows = []
    for p in P.itertuples(index=False):
        b00 = g3.first_b00(x5, p, DIRECT)
        if b00 is None:
            continue
        bix = int(p.exe_start_pos) + int(b00)
        complete_ts = x5.index[bix] + pd.Timedelta(minutes=BAR_MIN)
        rows.append({
            "partition": part,
            "reference_start": p.reference_start,
            "execution_start": p.execution_start,
            "execution_end": p.execution_end,
            "exe_start_pos": int(p.exe_start_pos),
            "exe_n": int(p.exe_n),
            "H": float(p.H), "L": float(p.L), "R": float(p.R),
            "signal_j": int(p.signal_j),
            "signal_ts": p.signal_ts,
            "b00_j": int(b00),
            "b00_bar_start": x5.index[bix],
            "b00_complete_ts": complete_ts,
            "b00_close": float(x5.close.iloc[bix]),
        })
    return pd.DataFrame(rows)


def next_open_entry(x5: pd.DataFrame, c):
    j = int(c.b00_j) + 1
    if j >= int(c.exe_n):
        return None
    ix = int(c.exe_start_pos) + j
    ts = x5.index[ix]
    if ts >= pd.Timestamp(c.execution_end):
        return None
    return {
        "available": True,
        "entry_j": j,
        "entry_bar_start": ts,
        "entry_ts": ts,
        "entry_price": float(x5.open.iloc[ix]),
        "fill_kind": "NEXT_OPEN",
        "intrabar": False,
        "pre_eval_failure": False,
        "bars_waited": 0,
        "cancel_reason": "",
        "limit_price": np.nan,
    }


def limit_entry(x5: pd.DataFrame, c, q: float, wait_min: int):
    H, R = float(c.H), float(c.R)
    limit = H + q*R
    start_j = int(c.b00_j) + 1
    max_bars = wait_min // BAR_MIN
    out = {
        "available": False,
        "entry_j": np.nan,
        "entry_bar_start": pd.NaT,
        "entry_ts": pd.NaT,
        "entry_price": np.nan,
        "fill_kind": "",
        "intrabar": False,
        "pre_eval_failure": False,
        "bars_waited": np.nan,
        "cancel_reason": "",
        "limit_price": limit,
    }
    if start_j >= int(c.exe_n):
        out["cancel_reason"] = "NO_EXECUTION_BAR"
        return out

    last_j = min(int(c.exe_n), start_j + max_bars)
    for j in range(start_j, last_j):
        ix = int(c.exe_start_pos) + j
        ts = x5.index[ix]
        if ts >= pd.Timestamp(c.execution_end):
            break
        op = float(x5.open.iloc[ix]); lo = float(x5.low.iloc[ix]); cl = float(x5.close.iloc[ix])
        waited = j - start_j
        if op <= limit:
            out.update({
                "available": True, "entry_j": j, "entry_bar_start": ts, "entry_ts": ts,
                "entry_price": op, "fill_kind": "OPEN_PRICE_IMPROVEMENT", "intrabar": False,
                "pre_eval_failure": False, "bars_waited": waited,
            })
            return out
        if lo <= limit:
            out.update({
                "available": True, "entry_j": j, "entry_bar_start": ts,
                "entry_ts": ts + pd.Timedelta(minutes=BAR_MIN),
                "entry_price": limit, "fill_kind": "INTRABAR_LIMIT", "intrabar": True,
                "pre_eval_failure": bool(cl < H), "bars_waited": waited,
            })
            return out
        if cl < H:
            out["cancel_reason"] = "CLOSE_BELOW_H_BEFORE_FILL"
            return out

    out["cancel_reason"] = "NO_FILL_WITHIN_WINDOW"
    return out


def evaluate_entry(x5: pd.DataFrame, c, ent: dict):
    out = {
        "close_below_H_before_E10": False,
        "reentry_ts": pd.NaT,
    }
    for q in CHECKS:
        key = f"e{int(round(q*100)):02d}"
        out[f"{key}_success"] = False
        out[f"{key}_ts"] = pd.NaT
        out[f"{key}_minutes"] = np.nan
    if not ent or not ent.get("available", False):
        return out

    H, R = float(c.H), float(c.R)
    ep = float(ent["entry_price"])
    ej = int(ent["entry_j"])
    targets = {q: ep + q*R for q in CHECKS}

    if bool(ent.get("pre_eval_failure", False)):
        out["close_below_H_before_E10"] = True
        out["reentry_ts"] = pd.Timestamp(ent["entry_ts"])
        return out

    # Open fills can evaluate their fill bar. Intrabar fills start on the next bar
    # because high-vs-fill ordering inside the fill bar is unknowable.
    start_j = ej + 1 if bool(ent.get("intrabar", False)) else ej
    if start_j >= int(c.exe_n):
        return out

    success_j = {}
    for j in range(start_j, int(c.exe_n)):
        ix = int(c.exe_start_pos) + j
        ts = x5.index[ix]
        if ts >= pd.Timestamp(c.execution_end):
            break
        hi = float(x5.high.iloc[ix]); cl = float(x5.close.iloc[ix])
        reentry = cl < H
        hit_map = {q: (hi >= target) for q, target in targets.items()}

        # Per preregistration, same-bar target + completed close below H is
        # conservatively not credited for still-unresolved checkpoints.
        if reentry:
            for q in CHECKS:
                key = f"e{int(round(q*100)):02d}"
                if not out[f"{key}_success"] and hit_map[q]:
                    pass
            if not out["e10_success"]:
                out["close_below_H_before_E10"] = True
                out["reentry_ts"] = ts + pd.Timedelta(minutes=BAR_MIN)
            break

        for q in CHECKS:
            key = f"e{int(round(q*100)):02d}"
            if (not out[f"{key}_success"]) and hit_map[q]:
                out[f"{key}_success"] = True
                out[f"{key}_ts"] = ts + pd.Timedelta(minutes=BAR_MIN)
                success_j[q] = j

    for q, j in success_j.items():
        key = f"e{int(round(q*100)):02d}"
        # Entry timestamp is exact for open fills, conservative bar completion for intrabar fills.
        entry_anchor = ej if not bool(ent.get("intrabar", False)) else ej + 1
        out[f"{key}_minutes"] = max(0, (j - entry_anchor)*BAR_MIN)
    return out


def build_audit(x5: pd.DataFrame, C: pd.DataFrame, spec: dict) -> pd.DataFrame:
    rows = []
    for c in C.itertuples(index=False):
        ctrl = next_open_entry(x5, c)
        ctrl_price = float(ctrl["entry_price"]) if ctrl and ctrl.get("available") else np.nan
        ent = next_open_entry(x5, c) if spec["kind"] == "NEXT_OPEN" else limit_entry(x5, c, float(spec["q"]), int(spec["wait_min"]))
        if ent is None:
            ent = {"available": False, "cancel_reason": "NO_EXECUTION_BAR"}
        ev = evaluate_entry(x5, c, ent)
        ep = float(ent.get("entry_price", np.nan)) if ent.get("available", False) else np.nan
        excess = (ep - float(c.H))/float(c.R) if np.isfinite(ep) else np.nan
        improve = (ctrl_price - ep)/float(c.R) if np.isfinite(ep) and np.isfinite(ctrl_price) else np.nan
        b00_to_fill = (int(ent.get("bars_waited", 0))*BAR_MIN) if ent.get("available", False) and np.isfinite(ent.get("bars_waited", np.nan)) else np.nan
        rows.append({
            "partition": c.partition,
            "reference_start": c.reference_start,
            "execution_start": c.execution_start,
            "execution_end": c.execution_end,
            "H": c.H, "L": c.L, "R": c.R,
            "signal_ts": c.signal_ts,
            "b00_complete_ts": c.b00_complete_ts,
            "b00_close": c.b00_close,
            "mode": spec["label"], "kind": spec["kind"],
            "q": spec.get("q", np.nan), "wait_min": spec.get("wait_min", 0),
            **ent,
            "entry_excess_R": excess,
            "next_open_price": ctrl_price,
            "entry_improvement_R": improve,
            "b00_to_fill_min": b00_to_fill,
            **ev,
        })
    return pd.DataFrame(rows)


def summarize_audit(A: pd.DataFrame, spec: dict):
    ncase = len(A)
    F = A[A.available.astype(bool)].copy()
    nf = len(F)
    row = {
        "partition": A.partition.iloc[0] if ncase else "",
        "mode": spec["label"], "kind": spec["kind"],
        "q": spec.get("q", np.nan), "wait_min": spec.get("wait_min", 0),
        "b00_cases": ncase, "fills": nf,
        "participation": nf/ncase if ncase else np.nan,
        "median_entry_excess_R": float(pd.to_numeric(F.entry_excess_R, errors="coerce").median()) if nf else np.nan,
        "median_entry_improvement_R": float(pd.to_numeric(F.entry_improvement_R, errors="coerce").median()) if nf else np.nan,
        "median_b00_to_fill_min": float(pd.to_numeric(F.b00_to_fill_min, errors="coerce").median()) if nf else np.nan,
        "close_below_H_before_E10": int(F.close_below_H_before_E10.astype(bool).sum()) if nf else 0,
    }
    for q in CHECKS:
        key = f"e{int(round(q*100)):02d}"
        wins = int(F[f"{key}_success"].astype(bool).sum()) if nf else 0
        row[f"{key}_wins"] = wins
        row[f"{key}_rate"] = wins/nf if nf else np.nan
        row[f"effective_{key}"] = wins/ncase if ncase else np.nan
    row["wilson_lb_effective_e10"] = wilson_lb(int(row["e10_wins"]), ncase)
    row["median_fill_to_e10_min"] = float(pd.to_numeric(F.loc[F.e10_success, "e10_minutes"], errors="coerce").median()) if int(row["e10_wins"]) else np.nan

    positive = 0
    for bi, ix in enumerate(np.array_split(np.arange(ncase), 4), 1):
        B = A.iloc[ix]
        BF = B[B.available.astype(bool)]
        bn = len(B); bfill = len(BF)
        eff10 = int(BF.e10_success.astype(bool).sum())/bn if bn else np.nan
        eff20 = int(BF.e20_success.astype(bool).sum())/bn if bn else np.nan
        part = bfill/bn if bn else np.nan
        row[f"block{bi}_n"] = bn
        row[f"block{bi}_part"] = part
        row[f"block{bi}_eff10"] = eff10
        row[f"block{bi}_eff20"] = eff20
        if bn >= 35 and part >= .45 and eff10 >= .30 and eff20 >= .18:
            positive += 1
    row["positive_blocks"] = positive
    return row


def dev_scan(x5, Cdev):
    rows = []
    audits = {}
    for spec in candidate_specs():
        A = build_audit(x5, Cdev, spec)
        audits[spec["label"]] = A
        rows.append(summarize_audit(A, spec))
    return pd.DataFrame(rows), audits


def build_leaderboard(D: pd.DataFrame):
    D = D.copy()
    is_limit = D.kind == "LIMIT"
    D["dev_gate"] = (
        (D.fills >= 100) & (D.participation >= .55) &
        (D.e10_rate >= .50) & (D.e20_rate >= .35) &
        (D.effective_e10 >= .35) & (D.effective_e20 >= .22) &
        (D.wilson_lb_effective_e10 >= .28) & (D.positive_blocks >= 3) &
        ((~is_limit) | (D.median_entry_improvement_R >= .005))
    )

    D["neighbors_available"] = 0
    D["neighbors_supportive"] = 0
    D["local_stable"] = True
    lookup = {}
    for r in D.itertuples(index=False):
        if r.kind == "LIMIT":
            lookup[(round(float(r.q), 8), int(r.wait_min))] = r

    for i, r in D.iterrows():
        if r.kind != "LIMIT":
            continue
        q = float(r.q); w = int(r.wait_min)
        qi = LEVELS.index(q); wi = WAITS.index(w)
        keys = []
        if qi > 0: keys.append((LEVELS[qi-1], w))
        if qi+1 < len(LEVELS): keys.append((LEVELS[qi+1], w))
        if wi > 0: keys.append((q, WAITS[wi-1]))
        if wi+1 < len(WAITS): keys.append((q, WAITS[wi+1]))
        sup = 0
        for k in keys:
            x = lookup[(round(float(k[0]), 8), int(k[1]))]
            if int(x.fills) >= 80 and float(x.participation) >= .45 and float(x.effective_e10) >= .30 and float(x.effective_e20) >= .18:
                sup += 1
        need = min(2, len(keys))
        D.at[i, "neighbors_available"] = len(keys)
        D.at[i, "neighbors_supportive"] = sup
        D.at[i, "local_stable"] = sup >= need

    D["candidate_eligible"] = D.dev_gate & D.local_stable
    D["upper_boundary"] = (D.kind == "LIMIT") & ((D.q == max(LEVELS)) | (D.wait_min == max(WAITS)))
    D["is_next_open"] = (D.kind == "NEXT_OPEN").astype(int)
    C = D[D.candidate_eligible].copy()
    C = C.sort_values(
        ["wilson_lb_effective_e10", "effective_e20", "effective_e10", "e20_rate",
         "median_entry_improvement_R", "participation", "wait_min", "is_next_open", "q"],
        ascending=[False, False, False, False, False, False, True, False, True],
        na_position="last"
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C)+1)
    return D, C


def spec_from_row(r):
    if r.kind == "NEXT_OPEN":
        return {"label": "NEXT_OPEN", "kind": "NEXT_OPEN", "q": np.nan, "wait_min": 0}
    return {"label": str(r.mode), "kind": "LIMIT", "q": float(r.q), "wait_min": int(r.wait_min)}


def holdout_scan(x5, sel):
    spec = spec_from_row(sel)
    rows = []; audits = []; all_ok = True
    for part in ("external", "reference_validation"):
        C = build_b00_cases(x5, part)
        A = build_audit(x5, C, spec)
        r = summarize_audit(A, spec)
        ok = (
            int(r["fills"]) >= 40 and float(r["participation"]) >= .45 and
            float(r["e10_rate"]) >= .45 and float(r["e20_rate"]) >= .30 and
            float(r["effective_e10"]) >= .30 and float(r["effective_e20"]) >= .18 and
            float(r["wilson_lb_effective_e10"]) >= .20 and
            (spec["kind"] == "NEXT_OPEN" or float(r["median_entry_improvement_R"]) >= 0.0)
        )
        r["replication_pass"] = bool(ok)
        rows.append(r); audits.append(A); all_ok = all_ok and bool(ok)
    return pd.DataFrame(rows), pd.concat(audits, ignore_index=True), all_ok


def main():
    g1.base.synthetic_tests()
    x5, coverage = g1.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")

    Cdev = build_b00_cases(x5, "development")
    Pdev = g3.build_parent_sessions(x5, "development")
    if len(Pdev) != 206:
        raise AssertionError(f"unexpected frozen G2 parent pressure count {len(Pdev)}")
    if len(Cdev) != 184:
        raise AssertionError(f"unexpected frozen G3 DIRECT B00 count {len(Cdev)}")

    D, audits = dev_scan(x5, Cdev)
    D2, L = build_leaderboard(D)
    D2.to_csv(OUT_DEV, index=False)
    L.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH Discovery 2 Reset — G4 ETH-Native Entry Discovery Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen lineage: **LONG / 01:30 UTC / R180 / E720 / HIGH-side pressure → DIRECT B00**.",
        f"Development frozen B00 cases: **{len(Cdev)}**.",
        "G4 compares executable entry price × patience only. No TP/SL/PnL is tested.", "",
        "## Development entry atlas", "",
        "| Candidate | Fills | Part. | Entry excess R | Improve vs N/O | E10 | E20 | Eff E10 | Eff E20 | Wilson Eff E10 | Blocks | Neigh. | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]
    for r in D2.itertuples(index=False):
        imp = "-" if pd.isna(r.median_entry_improvement_R) else f"{float(r.median_entry_improvement_R):+.3f}R"
        excess = "-" if pd.isna(r.median_entry_excess_R) else f"{float(r.median_entry_excess_R):.3f}"
        neigh = "-" if r.kind == "NEXT_OPEN" else f"{int(r.neighbors_supportive)}/{int(r.neighbors_available)}"
        lines.append(
            f"| {r.mode} | {int(r.fills)}/{int(r.b00_cases)} | {pct(r.participation)} | {excess} | {imp} | "
            f"{pct(r.e10_rate)} | {pct(r.e20_rate)} | {pct(r.effective_e10)} | {pct(r.effective_e20)} | "
            f"{pct(r.wilson_lb_effective_e10)} | {int(r.positive_blocks)}/4 | {neigh} | {'PASS' if bool(r.candidate_eligible) else 'FAIL'} |"
        )

    if len(L) == 0:
        status = "ETH_DISCOVERY2_RESET_G4_NO_DEV_CANDIDATE"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", "No candidate passed the preregistered Development entry + stability gates.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        OUT_RESULT.write_text("\n".join(lines)+"\n")
        print(OUT_RESULT.read_text()); return

    sel = L.iloc[0]
    lines += [
        "", "## Development-selected entry", "",
        f"**{sel.mode}**",
        f"Fills **{int(sel.fills)}/{int(sel.b00_cases)} ({pct(sel.participation)})**; median entry excess **{float(sel.median_entry_excess_R):.3f}R**; median improvement vs NEXT_OPEN **{float(sel.median_entry_improvement_R):+.3f}R**.",
        f"Conditional E10 **{pct(sel.e10_rate)}**; E20 **{pct(sel.e20_rate)}**; effective E10 **{pct(sel.effective_e10)}**; effective E20 **{pct(sel.effective_e20)}**; Wilson effective E10 **{pct(sel.wilson_lb_effective_e10)}**.",
        f"Median B00→fill **{float(sel.median_b00_to_fill_min):.0f}m**; median fill→E10 **{float(sel.median_fill_to_e10_min):.0f}m**; positive blocks **{int(sel.positive_blocks)}/4**.", "",
        "Development blocks:", "", "| Block | B00 N | Fill part. | Eff E10 | Eff E20 |", "|---:|---:|---:|---:|---:|"
    ]
    for b in range(1,5):
        lines.append(f"| {b} | {int(sel[f'block{b}_n'])} | {pct(sel[f'block{b}_part'])} | {pct(sel[f'block{b}_eff10'])} | {pct(sel[f'block{b}_eff20'])} |")

    if bool(sel.upper_boundary):
        status = "ETH_DISCOVERY2_RESET_G4_ENTRY_BOUNDARY_OPEN"
        OUT_STATUS.write_text(status + "\n")
        A = audits[str(sel.mode)]
        A.to_csv(OUT_AUDIT, index=False)
        lines += ["", "Selected resting-limit coordinate lies on the preregistered upper q/wait sentinel. Holdouts remain closed; no second-best substitution.", "", f"**Status: {status}**", "", "Research/shadow only. No live promotion."]
        OUT_RESULT.write_text("\n".join(lines)+"\n")
        print(OUT_RESULT.read_text()); return

    H, Ahold, supported = holdout_scan(x5, sel)
    Adev = audits[str(sel.mode)]
    pd.concat([Ahold.iloc[0:0], Adev], ignore_index=True) if False else None
    H.to_csv(OUT_OOS, index=False)
    pd.concat([Adev, Ahold], ignore_index=True).to_csv(OUT_AUDIT, index=False)
    status = "ETH_DISCOVERY2_RESET_G4_SUPPORTED" if supported else "ETH_DISCOVERY2_RESET_G4_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status + "\n")

    lines += ["", "## Historical replication", "", "| Partition | B00 | Fills | Part. | Improve | E10 | E20 | Eff E10 | Eff E20 | Wilson | Gate |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        imp = 0.0 if pd.isna(r.median_entry_improvement_R) else float(r.median_entry_improvement_R)
        lines.append(f"| {r.partition} | {int(r.b00_cases)} | {int(r.fills)} | {pct(r.participation)} | {imp:+.3f}R | {pct(r.e10_rate)} | {pct(r.e20_rate)} | {pct(r.effective_e10)} | {pct(r.effective_e20)} | {pct(r.wilson_lb_effective_e10)} | {'PASS' if bool(r.replication_pass) else 'FAIL'} |")

    lines += ["", "## Development leaderboard", "", "| # | Candidate | Fills | Part. | Improve | Eff E10 | Eff E20 | Wilson | Boundary |", "|---:|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in L.itertuples(index=False):
        imp = 0.0 if pd.isna(r.median_entry_improvement_R) else float(r.median_entry_improvement_R)
        lines.append(f"| {int(r.dev_rank)} | {r.mode} | {int(r.fills)} | {pct(r.participation)} | {imp:+.3f}R | {pct(r.effective_e10)} | {pct(r.effective_e20)} | {pct(r.wilson_lb_effective_e10)} | {'YES' if bool(r.upper_boundary) else 'NO'} |")

    lines += ["", f"**Status: {status}**", "", "G4 validates entry geometry only. Economics remain undiscovered on the reset lineage.", "Research/shadow only. No live promotion."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
