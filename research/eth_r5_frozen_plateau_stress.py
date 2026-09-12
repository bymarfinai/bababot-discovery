#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_r1_h00_robust_train as r1
import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
FROZEN_CELLS = ROOT / "ETH_R4B_STAGEA_2022_FROZEN_COMPONENT_CELLS.csv"
R4_2025 = ROOT / "ETH_R4B_STAGE_D_2025_FINAL_OOS_CELLS.csv"
OUT_DETAIL = ROOT / "ETH_R5_FROZEN_PLATEAU_STRESS_CELL_RESULTS.csv"
OUT_COMPONENT = ROOT / "ETH_R5_FROZEN_PLATEAU_STRESS_COMPONENT_RESULTS.csv"
OUT_JACKKNIFE = ROOT / "ETH_R5_FROZEN_PLATEAU_STRESS_JACKKNIFE.csv"
OUT_RESULT = ROOT / "ETH_R5_FROZEN_PLATEAU_STRESS_Result.md"
OUT_STATUS = ROOT / "ETH_R5_FROZEN_PLATEAU_STRESS_Status.txt"

CUTOFF = pd.Timestamp("2026-01-01", tz="UTC")
YEARS = (2022, 2023, 2024, 2025)
FEE_MULTS = (1.0, 1.5, 2.0)
DELAYS = (0, 5, 10, 15)
PRIMARY_FEE_MULT = 1.5
PRIMARY_DELAY = 5
EXPECTED_CELLS = {(120, 240), (180, 240), (240, 240), (180, 360), (240, 360)}


def finite(x):
    return bool(np.isfinite(x))


def component_summary(G: pd.DataFrame) -> dict:
    n = len(G)
    viable_n = int(G.viable.sum())
    med_wr = float(G.wr.median())
    med_exp = float(G.exp.median())
    med_pf = float(G.pf.median())
    med_dd = float(G.dd.median())
    max_dd = float(G.dd.max())
    survived = bool(viable_n >= 3 and med_exp > 0 and med_pf >= 1.15)
    return {
        "cells": n,
        "viable_cells": viable_n,
        "median_wr": med_wr,
        "median_exp": med_exp,
        "median_pf": med_pf,
        "median_dd": med_dd,
        "max_cell_dd": max_dd,
        "component_pass": survived,
    }


def events_for_period(cache, x5, lb: int, hold: int, rule: str, start, end, delay_min: int, fee_mult: float):
    rows = []
    opens = x5.open.to_numpy(float)
    xidx = pd.DatetimeIndex(x5.index)
    delay = pd.Timedelta(minutes=int(delay_min))

    for clock in e12.CLOCKS:
        S, ent, pre, ex, valid, xp, delta, masks = cache[(clock, lb, hold)]
        ent = pd.DatetimeIndex(ent)
        ex = pd.DatetimeIndex(ex)
        base_m = valid & (ent >= start) & (ex < end) & masks[rule]

        if delay_min == 0:
            m = base_m
            gross = e12.NOTIONAL * np.asarray(delta, float)[m]
            ent_exec = ent[m]
            ex_exec = ex[m]
        else:
            ent2 = ent + delay
            ex2 = ex + delay
            ei = xidx.get_indexer(ent2)
            xi = xidx.get_indexer(ex2)
            shifted_valid = (ei >= 0) & (xi >= 0) & (ent2 >= start) & (ex2 < end)
            m = base_m & shifted_valid
            mi = np.flatnonzero(m)
            ep = opens[ei[mi]]
            opx = opens[xi[mi]]
            gross = e12.NOTIONAL * ((opx - ep) / ep)
            ent_exec = ent2[m]
            ex_exec = ex2[m]

        net = gross - (e12.FEE * float(fee_mult))
        for entry_ts, exit_ts, g, n in zip(ent_exec, ex_exec, gross, net):
            rows.append({
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "clock": int(clock),
                "gross": float(g),
                "net": float(n),
            })

    if not rows:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "gross", "net"])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def calc_cell(T: pd.DataFrame, dev_dd: float):
    st = r1.stats_from_df(T)
    wr = float(st["win_rate"]) if finite(st["win_rate"]) else np.nan
    exp = float(st["expectancy"]) if finite(st["expectancy"]) else np.nan
    pf = float(st["pf"]) if finite(st["pf"]) else np.nan
    dd = float(st["max_dd"]) if finite(st["max_dd"]) else np.nan
    dd_cap = min(160.0, 1.50 * float(dev_dd) + 20.0)
    viable = bool(
        int(st["trades"]) >= 50
        and finite(wr) and wr >= .52
        and float(st["net_pnl"]) > 0
        and finite(exp) and exp > 0
        and finite(pf) and pf >= 1.15
        and finite(dd) and dd <= dd_cap
    )
    return {
        "n": int(st["trades"]),
        "wr": wr,
        "net": float(st["net_pnl"]),
        "exp": exp,
        "pf": pf,
        "dd": dd,
        "ls": int(st["max_loss_streak"]),
        "dd_cap": dd_cap,
        "viable": viable,
    }


def reproduce_r4(detail: pd.DataFrame, r4: pd.DataFrame):
    B = detail[(detail.year == 2025) & (detail.fee_mult == 1.0) & (detail.delay_min == 0)].copy()
    checks = []
    fields = [
        ("n", "oos2025_n", 0.0),
        ("wr", "oos2025_wr", 1e-12),
        ("net", "oos2025_net", 1e-9),
        ("exp", "oos2025_exp", 1e-12),
        ("pf", "oos2025_pf", 1e-12),
        ("dd", "oos2025_dd", 1e-9),
        ("ls", "oos2025_ls", 0.0),
    ]
    for b in B.itertuples(index=False):
        rr = r4[(r4.lookback_min == int(b.lookback_min)) & (r4.hold_min == int(b.hold_min))].iloc[0]
        for newf, oldf, tol in fields:
            a = float(getattr(b, newf))
            z = float(rr[oldf])
            checks.append(abs(a - z) <= tol)
    return bool(all(checks)), int(sum(checks)), int(len(checks))


def main():
    frozen = pd.read_csv(FROZEN_CELLS)
    r4 = pd.read_csv(R4_2025)

    C = frozen[
        (frozen.hour_wib == 4)
        & (frozen.component_rank == 1)
        & (frozen.character_rule.astype(str) == "DRIVE_DOWN__STR_B80_100")
    ].copy().sort_values(["hold_min", "lookback_min"]).reset_index(drop=True)

    actual = set(zip(C.lookback_min.astype(int), C.hold_min.astype(int)))
    if len(C) != 5 or actual != EXPECTED_CELLS:
        raise AssertionError(f"Frozen R4 plateau changed: {sorted(actual)}")

    r4_cells = set(zip(r4.lookback_min.astype(int), r4.hold_min.astype(int)))
    if r4_cells != EXPECTED_CELLS:
        raise AssertionError("R4 2025 reference cells do not match frozen plateau")

    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    if idx.max() < pd.Timestamp("2025-12-31 23:55:00", tz="UTC"):
        raise RuntimeError(f"2025 dataset incomplete; max timestamp is {idx.max()}")

    # Hard anti-leak cap. R5 neither scores nor even passes 2026 bars into prep().
    x = x5[idx < CUTOFF].copy()
    if pd.DatetimeIndex(x.index).max() >= CUTOFF:
        raise AssertionError("2026 leak into R5 data frame")

    e12.CLOCKS = r1.clocks_for_hour(4)
    e12.LOOKBACKS = sorted(C.lookback_min.astype(int).unique().tolist())
    e12.HOLDS = sorted(C.hold_min.astype(int).unique().tolist())
    cache = e12.prep(x)

    rows = []
    rule = "DRIVE_DOWN__STR_B80_100"
    for fee_mult in FEE_MULTS:
        for delay_min in DELAYS:
            for year in YEARS:
                start = pd.Timestamp(f"{year}-01-01", tz="UTC")
                end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
                for c in C.itertuples(index=False):
                    lb, hold = int(c.lookback_min), int(c.hold_min)
                    T = events_for_period(cache, x, lb, hold, rule, start, end, delay_min, fee_mult)
                    st = calc_cell(T, float(c.dev_dd))
                    rows.append({
                        "year": year,
                        "fee_mult": float(fee_mult),
                        "delay_min": int(delay_min),
                        "lookback_min": lb,
                        "hold_min": hold,
                        **st,
                    })

    D = pd.DataFrame(rows)
    D.to_csv(OUT_DETAIL, index=False)

    comp_rows = []
    for (fm, dm, y), G in D.groupby(["fee_mult", "delay_min", "year"], sort=True):
        comp_rows.append({
            "fee_mult": float(fm),
            "delay_min": int(dm),
            "year": int(y),
            **component_summary(G),
        })
    S = pd.DataFrame(comp_rows).sort_values(["fee_mult", "delay_min", "year"]).reset_index(drop=True)
    S.to_csv(OUT_COMPONENT, index=False)

    reproduction_ok, reproduction_checks, reproduction_total = reproduce_r4(D, r4)

    primary = S[(S.fee_mult == PRIMARY_FEE_MULT) & (S.delay_min == PRIMARY_DELAY)].copy()
    primary_pass_years = int(primary.component_pass.sum())
    primary_2025_pass = bool(primary.loc[primary.year == 2025, "component_pass"].iloc[0])

    base = S[(S.fee_mult == 1.0) & (S.delay_min == 0)].copy()
    base_pass_years = int(base.component_pass.sum())
    base_2025_pass = bool(base.loc[base.year == 2025, "component_pass"].iloc[0])

    # 2025 leave-one-cell-out jackknife under the preregistered primary stress.
    P25 = D[(D.year == 2025) & (D.fee_mult == PRIMARY_FEE_MULT) & (D.delay_min == PRIMARY_DELAY)].copy()
    jk_rows = []
    for omit in sorted(EXPECTED_CELLS):
        G = P25[~((P25.lookback_min == omit[0]) & (P25.hold_min == omit[1]))].copy()
        viable_n = int(G.viable.sum())
        med_exp = float(G.exp.median())
        med_pf = float(G.pf.median())
        survived = bool(viable_n >= 2 and med_exp > 0 and med_pf >= 1.15)
        jk_rows.append({
            "omitted_lb": omit[0],
            "omitted_hold": omit[1],
            "remaining_cells": len(G),
            "viable_cells": viable_n,
            "median_exp": med_exp,
            "median_pf": med_pf,
            "jackknife_pass": survived,
        })
    J = pd.DataFrame(jk_rows)
    J.to_csv(OUT_JACKKNIFE, index=False)
    jackknife_passes = int(J.jackknife_pass.sum())

    if reproduction_ok and primary_pass_years >= 3 and primary_2025_pass and jackknife_passes >= 3:
        verdict = "R5_FROZEN_PLATEAU_STRESS_PASS"
    else:
        p25 = primary[primary.year == 2025].iloc[0]
        partial = bool(
            reproduction_ok
            and base_pass_years >= 3
            and base_2025_pass
            and (primary_pass_years >= 2 or (float(p25.median_exp) > 0 and float(p25.median_pf) > 1.0))
        )
        verdict = "R5_PARTIAL_STRESS_PERSISTENCE" if partial else "R5_FROZEN_PLATEAU_STRESS_FAIL"

    # Compact scenario aggregate for the report.
    ag = []
    for (fm, dm), G in S.groupby(["fee_mult", "delay_min"], sort=True):
        y25 = G[G.year == 2025].iloc[0]
        ag.append({
            "fee_mult": fm,
            "delay_min": dm,
            "pass_years": int(G.component_pass.sum()),
            "y2025_pass": bool(y25.component_pass),
            "y2025_viable": int(y25.viable_cells),
            "y2025_med_exp": float(y25.median_exp),
            "y2025_med_pf": float(y25.median_pf),
        })
    A = pd.DataFrame(ag)

    lines = [
        "# ETH R5 — Frozen Plateau Stress Audit", "",
        "**NO RESELECTION. H04 R4 PLATEAU FROZEN. 2026 CLOSED.**", "",
        f"Frozen character: **H04 {rule}**; cells: **5**.",
        f"Raw 5m coverage: **{coverage:.4%}**; R5 data hard-capped before **2026-01-01 UTC**.",
        f"R4 2025 baseline reproduction: **{'PASS' if reproduction_ok else 'FAIL'}** ({reproduction_checks}/{reproduction_total} checks).",
        f"Primary stress: **{PRIMARY_FEE_MULT:.1f}x fee + {PRIMARY_DELAY}m execution delay**.",
        f"Primary annual plateau survival: **{primary_pass_years}/4 years**; 2025 survival: **{'YES' if primary_2025_pass else 'NO'}**.",
        f"Primary-stress 2025 jackknife survival: **{jackknife_passes}/5 omissions**.",
        f"Verdict: **{verdict}**.", "",
        "## Primary stress by year", "",
        "| Year | Viable cells | Median WR | Median Exp | Median PF | Max cell DD | Plateau |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in primary.itertuples(index=False):
        lines.append(
            f"| {int(r.year)} | {int(r.viable_cells)}/5 | {100*float(r.median_wr):.2f}% | "
            f"${float(r.median_exp):+.2f} | {float(r.median_pf):.3f} | ${float(r.max_cell_dd):.2f} | "
            f"{'PASS' if bool(r.component_pass) else 'FAIL'} |"
        )

    lines += [
        "", "## 2025 frozen cells — baseline vs primary stress", "",
        "| Cell | Base Exp/PF | Base viable | Primary Exp/PF | Primary viable |",
        "|---|---|:---:|---|:---:|",
    ]
    B25 = D[(D.year == 2025) & (D.fee_mult == 1.0) & (D.delay_min == 0)]
    for cell in sorted(EXPECTED_CELLS, key=lambda x: (x[1], x[0])):
        b = B25[(B25.lookback_min == cell[0]) & (B25.hold_min == cell[1])].iloc[0]
        p = P25[(P25.lookback_min == cell[0]) & (P25.hold_min == cell[1])].iloc[0]
        lines.append(
            f"| LB{cell[0]}/H{cell[1]} | ${float(b.exp):+.2f} / {float(b.pf):.3f} | {'Y' if bool(b.viable) else 'N'} | "
            f"${float(p.exp):+.2f} / {float(p.pf):.3f} | {'Y' if bool(p.viable) else 'N'} |"
        )

    lines += [
        "", "## Full implementation-stress grid — component view", "",
        "| Fee | Delay | Years survived | 2025 viable | 2025 med Exp | 2025 med PF | 2025 plateau |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in A.itertuples(index=False):
        lines.append(
            f"| {float(r.fee_mult):.1f}x | {int(r.delay_min)}m | {int(r.pass_years)}/4 | {int(r.y2025_viable)}/5 | "
            f"${float(r.y2025_med_exp):+.2f} | {float(r.y2025_med_pf):.3f} | {'PASS' if bool(r.y2025_pass) else 'FAIL'} |"
        )

    lines += [
        "", "## 2025 primary-stress leave-one-cell-out jackknife", "",
        "| Omitted | Remaining viable | Median Exp | Median PF | Survives |",
        "|---|---:|---:|---:|:---:|",
    ]
    for r in J.itertuples(index=False):
        lines.append(
            f"| LB{int(r.omitted_lb)}/H{int(r.omitted_hold)} | {int(r.viable_cells)}/4 | "
            f"${float(r.median_exp):+.2f} | {float(r.median_pf):.3f} | {'YES' if bool(r.jackknife_pass) else 'NO'} |"
        )

    lines += [
        "",
        "Interpretation is plateau-level only. No coordinate is promoted or replaced from these results.",
        "Execution delay preserves the frozen signal classification and hold duration; only execution prices shift.",
        "Loss streak is reported in the cell CSV as a diagnostic and is not a hard R5 gate.",
        "2026 is not used anywhere in this experiment.",
    ]

    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text(verdict + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
