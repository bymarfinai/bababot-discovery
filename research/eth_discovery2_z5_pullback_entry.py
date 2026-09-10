#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_native_london_ny_entry_z4 as z4

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_Z5_PULLBACK_ENTRY"
OUT_AUDIT = ROOT / f"{PFX}_Audit.csv"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR5 = pd.Timedelta(minutes=5)
WAIT_BARS = 6
MAJOR = ("external", "development", "reference_validation")
COHORTS = ("F95", "F90")
LEVELS = {"L02": 0.02, "L04": 0.04, "L06": 0.06}
MODES = ("NEXT_OPEN", *LEVELS.keys())
TIE = {"L02": 0, "L04": 1, "L06": 2}
CHECKS = {"C20": 0.20, "C30": 0.30, "C40": 0.40}


def fast_slice(x, a, z):
    return base.fast_slice(x, a, z)


def build_cases(x5: pd.DataFrame) -> pd.DataFrame:
    C = z4.build_cases(x5).copy()
    C = C[C.partition.isin(MAJOR) & C.cohort.isin(COHORTS)].copy()
    f95 = set(C.loc[C.cohort == "F95", "session_id"])
    f90 = set(C.loc[C.cohort == "F90", "session_id"])
    assert f90.issubset(f95)
    assert (C.breakout_close > C.H).all()
    assert (pd.to_datetime(C.breakout_ts, utc=True) > pd.to_datetime(C.retest_ts, utc=True)).all()
    return C


def next_open_entry(x5: pd.DataFrame, c):
    bts = pd.Timestamp(c.breakout_ts)
    ee = pd.Timestamp(c.execution_end)
    if bts >= ee or bts not in x5.index:
        return None
    r = x5.loc[bts]
    return {
        "available": True,
        "entry_start": bts,
        "entry_ts": bts,
        "entry_price": float(r.open),
        "eval_start": bts,
        "fill_kind": "NEXT_OPEN",
        "pre_eval_failure": False,
        "limit_frac": np.nan,
        "limit_price": np.nan,
        "bars_waited": 0,
        "cancel_reason": "",
    }


def limit_entry(x5: pd.DataFrame, c, level_frac: float):
    H, L, R = float(c.H), float(c.L), float(c.R)
    bts = pd.Timestamp(c.breakout_ts)
    ee = pd.Timestamp(c.execution_end)
    limit = H + level_frac * R
    stop = min(ee, bts + WAIT_BARS * BAR5)
    post = fast_slice(x5, bts, stop)
    out = {
        "available": False,
        "entry_start": pd.NaT,
        "entry_ts": pd.NaT,
        "entry_price": np.nan,
        "eval_start": pd.NaT,
        "fill_kind": "",
        "pre_eval_failure": False,
        "limit_frac": level_frac,
        "limit_price": limit,
        "bars_waited": np.nan,
        "cancel_reason": "",
    }
    for i, (ts, r) in enumerate(post.iterrows()):
        op, lo, cl = float(r.open), float(r.low), float(r.close)
        if op <= limit:
            out.update({
                "available": True,
                "entry_start": ts,
                "entry_ts": ts,
                "entry_price": op,
                "eval_start": ts,
                "fill_kind": "OPEN_PRICE_IMPROVEMENT",
                "bars_waited": i,
            })
            assert op <= limit + 1e-12
            return out
        if lo <= limit:
            out.update({
                "available": True,
                "entry_start": ts,
                "entry_ts": ts + BAR5,
                "entry_price": limit,
                "eval_start": ts + BAR5,
                "fill_kind": "INTRABAR_LIMIT",
                "bars_waited": i,
                "pre_eval_failure": bool(cl < L),
            })
            assert ts >= bts
            return out
        if cl < L:
            out["cancel_reason"] = "CLOSE_BELOW_L_BEFORE_FILL"
            return out
    out["cancel_reason"] = "NO_FILL_WITHIN_30M"
    return out


def evaluate(x5: pd.DataFrame, c, ent: dict):
    out = {
        "mfe_frac": np.nan,
        "mae_frac": np.nan,
        "adverse_R": np.nan,
        "close_below_L_before_C20": False,
        "close_below_L_ts": pd.NaT,
    }
    for k in CHECKS:
        out[f"{k}_reached"] = False
        out[f"{k}_ts"] = pd.NaT
        out[f"{k}_already_passed"] = False
    if not ent or not ent.get("available", False):
        return out

    H, L, R = float(c.H), float(c.L), float(c.R)
    ep = float(ent["entry_price"])
    ef = (ep - L) / R
    cps = {k: H + f * R for k, f in CHECKS.items()}
    eligible = {k: ep < p for k, p in cps.items()}
    for k in CHECKS:
        out[f"{k}_already_passed"] = not eligible[k]

    if ent.get("pre_eval_failure", False):
        out["close_below_L_before_C20"] = True
        out["close_below_L_ts"] = pd.Timestamp(ent["entry_ts"])
        return out

    a = pd.Timestamp(ent["eval_start"])
    ee = pd.Timestamp(c.execution_end)
    path = fast_slice(x5, a, ee)
    if len(path) == 0:
        return out

    max_hi = -np.inf
    min_lo = np.inf
    for ts, r in path.iterrows():
        hi, lo, cl = float(r.high), float(r.low), float(r.close)
        max_hi = max(max_hi, hi)
        min_lo = min(min_lo, lo)
        for k, p in cps.items():
            if eligible[k] and not out[f"{k}_reached"] and hi >= p:
                out[f"{k}_reached"] = True
                out[f"{k}_ts"] = ts + BAR5
        if cl < L:
            if not out["C20_reached"]:
                out["close_below_L_before_C20"] = True
                out["close_below_L_ts"] = ts + BAR5
            break

    if max_hi > -np.inf:
        out["mfe_frac"] = (max_hi - L) / R
        out["mae_frac"] = (min_lo - L) / R
        out["adverse_R"] = max(0.0, ef - out["mae_frac"])
    if out["C40_reached"]:
        assert out["C30_reached"] or out["C30_already_passed"]
    if out["C30_reached"]:
        assert out["C20_reached"] or out["C20_already_passed"]
    return out


def build_audit(x5, C):
    rows = []
    controls = {}
    for c in C.itertuples(index=False):
        ctrl = next_open_entry(x5, c)
        if ctrl is None:
            continue
        controls[(c.cohort, c.session_id)] = ctrl["entry_price"]

    for c in C.itertuples(index=False):
        ctrl_price = controls.get((c.cohort, c.session_id), np.nan)
        for mode in MODES:
            if mode == "NEXT_OPEN":
                ent = next_open_entry(x5, c)
            else:
                ent = limit_entry(x5, c, LEVELS[mode])
            if ent is None:
                ent = {"available": False}
            ev = evaluate(x5, c, ent)
            ep = float(ent.get("entry_price", np.nan)) if ent.get("available", False) else np.nan
            ef = (ep - float(c.L)) / float(c.R) if np.isfinite(ep) else np.nan
            improve = (ctrl_price - ep) / float(c.R) if np.isfinite(ep) and np.isfinite(ctrl_price) else np.nan
            if mode != "NEXT_OPEN" and ent.get("available", False):
                assert ep <= float(ent["limit_price"]) + 1e-12
                assert pd.Timestamp(ent["entry_start"]) >= pd.Timestamp(c.breakout_ts)
                assert pd.Timestamp(ent["entry_start"]) < pd.Timestamp(c.execution_end)
            rows.append({
                "cohort": c.cohort,
                "session_id": c.session_id,
                "partition": c.partition,
                "H": c.H, "L": c.L, "R": c.R,
                "breakout_ts": c.breakout_ts,
                "breakout_close_frac": c.breakout_close_frac,
                "execution_end": c.execution_end,
                "mode": mode,
                **ent,
                "entry_frac": ef,
                "control_entry_price": ctrl_price,
                "entry_improvement_R": improve,
                **ev,
            })
    return pd.DataFrame(rows)


def summarize(C, A):
    rows = []
    for part in (*MAJOR, "POOLED_MAJOR"):
        for cohort in COHORTS:
            if part == "POOLED_MAJOR":
                c = C[(C.cohort == cohort) & C.partition.isin(MAJOR)]
                aa = A[(A.cohort == cohort) & A.partition.isin(MAJOR)]
            else:
                c = C[(C.cohort == cohort) & (C.partition == part)]
                aa = A[(A.cohort == cohort) & (A.partition == part)]
            for mode in MODES:
                q = aa[(aa["mode"] == mode) & aa.available.astype(bool)]
                n = len(q); denom = len(c)
                row = {
                    "partition": part, "cohort": cohort, "mode": mode,
                    "b00_cases": denom, "available_entries": n,
                    "participation": n/denom if denom else np.nan,
                    "median_entry_frac": pd.to_numeric(q.entry_frac, errors="coerce").median() if n else np.nan,
                    "median_entry_improvement_R": pd.to_numeric(q.entry_improvement_R, errors="coerce").median() if n else np.nan,
                    "p75_entry_improvement_R": pd.to_numeric(q.entry_improvement_R, errors="coerce").quantile(.75) if n else np.nan,
                    "median_adverse_R": pd.to_numeric(q.adverse_R, errors="coerce").median() if n else np.nan,
                    "p90_adverse_R": pd.to_numeric(q.adverse_R, errors="coerce").quantile(.90) if n else np.nan,
                    "median_mfe_frac": pd.to_numeric(q.mfe_frac, errors="coerce").median() if n else np.nan,
                    "close_below_L_before_C20": int(q.close_below_L_before_C20.astype(bool).sum()) if n else 0,
                }
                for k in CHECKS:
                    hits = int(q[f"{k}_reached"].astype(bool).sum()) if n else 0
                    passed = int(q[f"{k}_already_passed"].astype(bool).sum()) if n else 0
                    row[f"{k}_reach"] = hits
                    row[f"{k}_reach_rate"] = hits/n if n else np.nan
                    row[f"{k}_already_passed"] = passed
                rows.append(row)
    return pd.DataFrame(rows)


def select_dev(S):
    cand = []
    for mode in LEVELS:
        qq = S[(S.partition == "development") & (S["mode"] == mode)]
        cc = S[(S.partition == "development") & (S["mode"] == "NEXT_OPEN")]
        if len(qq) != 2 or len(cc) != 2:
            continue
        ok = True
        for cohort in COHORTS:
            r = qq[qq.cohort == cohort].iloc[0]
            ctrl = cc[cc.cohort == cohort].iloc[0]
            ok = ok and (
                int(r.available_entries) >= 30 and
                float(r.participation) >= .50 and
                float(r.median_entry_frac) <= float(ctrl.median_entry_frac) + 1e-12 and
                float(r.C20_reach_rate) >= .55 and
                float(r.C30_reach_rate) >= .40 and
                int(r.C20_reach) > int(r.close_below_L_before_C20)
            )
        if ok:
            cand.append({
                "mode": mode,
                "min_c30": float(qq.C30_reach_rate.min()),
                "min_c20": float(qq.C20_reach_rate.min()),
                "worst_entry": float(qq.median_entry_frac.max()),
                "min_part": float(qq.participation.min()),
                "tie": TIE[mode],
            })
    if not cand:
        return None, pd.DataFrame()
    L = pd.DataFrame(cand).sort_values(
        ["min_c30","min_c20","worst_entry","min_part","tie"],
        ascending=[False,False,True,False,True]
    ).reset_index(drop=True)
    return str(L.iloc[0]["mode"]), L


def replicate(S, selected):
    rows=[]; all_ok=True
    if selected is None:
        return rows, False
    for part in ("external","reference_validation"):
        for cohort in COHORTS:
            r = S[(S.partition == part)&(S["mode"]==selected)&(S.cohort==cohort)].iloc[0]
            ctrl = S[(S.partition == part)&(S["mode"]=="NEXT_OPEN")&(S.cohort==cohort)].iloc[0]
            ok = (
                int(r.available_entries) >= 18 and
                float(r.participation) >= .40 and
                float(r.median_entry_frac) <= float(ctrl.median_entry_frac) + 1e-12 and
                float(r.C20_reach_rate) >= .50 and
                float(r.C30_reach_rate) >= .35 and
                int(r.C20_reach) > int(r.close_below_L_before_C20)
            )
            rows.append((part,cohort,r,ctrl,ok))
            all_ok = all_ok and ok
    return rows, all_ok


def pct(x):
    return "-" if pd.isna(x) else f"{100*float(x):.1f}%"


def main():
    z4.z2.read_provenance()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"ETH raw 5m coverage too low: {coverage:.6f}")
    C = build_cases(x5)
    A = build_audit(x5, C)
    S = summarize(C, A)
    A.to_csv(OUT_AUDIT, index=False)
    S.to_csv(OUT_SUMMARY, index=False)

    selected, leaderboard = select_dev(S)
    reps, supported = replicate(S, selected)
    status = (
        "ETH_DISCOVERY2_Z5_NO_DEV_CANDIDATE" if selected is None else
        "ETH_DISCOVERY2_Z5_SUPPORTED" if supported else
        "ETH_DISCOVERY2_Z5_CANDIDATE_NOT_REPLICATED"
    )
    OUT_STATUS.write_text(status + "\n")

    lines = [
        "# ETH Discovery 2 — Z5 Breakout Pullback Entry Geometry Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen Z1→Z4 lineage retained. Z5 does not relax the failed Z4 gate.",
        "C20/C30/C40 are structural diagnostics only; no TP/SL/PnL was tested.","",
        "## Pooled major comparison","",
        "| Cohort | Mode | Entries | Part. | Median entry | Median improve vs NEXT_OPEN | C20 | C30 | C40 | Close<L before C20 | Median adverse R |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for cohort in COHORTS:
        for mode in MODES:
            r = S[(S.partition=="POOLED_MAJOR")&(S.cohort==cohort)&(S["mode"]==mode)].iloc[0]
            med_imp = 0.0 if pd.isna(r.median_entry_improvement_R) else float(r.median_entry_improvement_R)
            med_adv = np.nan if pd.isna(r.median_adverse_R) else float(r.median_adverse_R)
            med_adv_s = "-" if pd.isna(med_adv) else f"{med_adv:.3f}"
            lines.append(
                f"| {cohort} | {mode} | {int(r.available_entries)}/{int(r.b00_cases)} | {pct(r.participation)} | "
                f"{float(r.median_entry_frac):.3f} | {med_imp:.3f}R | "
                f"{pct(r.C20_reach_rate)} | {pct(r.C30_reach_rate)} | {pct(r.C40_reach_rate)} | "
                f"{int(r.close_below_L_before_C20)} | {med_adv_s} |"
            )

    lines += ["","## Development selection",""]
    if selected is None:
        lines += ["No preregistered pullback level passed the Development gate for both F95 and F90."]
    else:
        lines += [f"Selected Development mode: **{selected}**.",""]
        for cohort in COHORTS:
            r = S[(S.partition=="development")&(S.cohort==cohort)&(S["mode"]==selected)].iloc[0]
            ctrl = S[(S.partition=="development")&(S.cohort==cohort)&(S["mode"]=="NEXT_OPEN")].iloc[0]
            lines.append(
                f"- {cohort}: N={int(r.available_entries)}/{int(r.b00_cases)} ({pct(r.participation)}), "
                f"entry={float(r.median_entry_frac):.3f} vs control {float(ctrl.median_entry_frac):.3f}, "
                f"C20={pct(r.C20_reach_rate)}, C30={pct(r.C30_reach_rate)}."
            )
        lines += ["","Historical replication:",""]
        for part,cohort,r,ctrl,ok in reps:
            lines.append(
                f"- {part} {cohort}: N={int(r.available_entries)}/{int(r.b00_cases)} ({pct(r.participation)}), "
                f"entry={float(r.median_entry_frac):.3f} vs control {float(ctrl.median_entry_frac):.3f}, "
                f"C20={pct(r.C20_reach_rate)}, C30={pct(r.C30_reach_rate)} -> {'PASS' if ok else 'FAIL'}."
            )
    if len(leaderboard):
        lines += ["","Development candidate leaderboard:",""]
        for i,r in leaderboard.iterrows():
            lines.append(
                f"- #{i+1} {r['mode']}: min C30={pct(r['min_c30'])}, min C20={pct(r['min_c20'])}, "
                f"worst median entry={float(r['worst_entry']):.3f}, min participation={pct(r['min_part'])}."
            )
    lines += ["",f"**Status: {status}**","","Stop after Z5. Economic milestone is not run automatically by this script."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
