#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_economic_first_e12a_long_13_14wib_character as e12

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E16A_02_03WIB"
HOUR_WIB = 2
YEARS = (2022, 2023, 2024)

BASE_LOOKBACKS = (15, 30, 60, 120, 240, 360)
BASE_HOLDS = (60, 120, 240, 360)
LOOKBACKS = (15, 30, 60, 90, 120, 150, 180, 210, 240, 360)
HOLDS = (60, 120, 180, 210, 240, 270, 300, 330, 360)
EXPECTED_RULES = 90
EXPECTED_REFINED = len(LOOKBACKS) * len(HOLDS) * EXPECTED_RULES

OUT_BASE_GRID = ROOT / f"{PFX}_BaselineGrid.csv"
OUT_BASE_SUMMARY = ROOT / f"{PFX}_BaselineSummary.csv"
OUT_GRID = ROOT / f"{PFX}_Grid.csv"
OUT_PASSERS = ROOT / f"{PFX}_Passers.csv"
OUT_NEAR = ROOT / f"{PFX}_NearMisses.csv"
OUT_SUMMARY = ROOT / f"{PFX}_Summary.csv"
OUT_EVENTS = ROOT / f"{PFX}_ExecutableEvents.csv"
OUT_ACCEPTED = ROOT / f"{PFX}_ExecutableAccepted.csv"
OUT_BLOCKED = ROOT / f"{PFX}_ExecutableBlocked.csv"
OUT_EXEC_SUMMARY = ROOT / f"{PFX}_ExecutableSummary.csv"
OUT_EXEC_YEARS = ROOT / f"{PFX}_ExecutableYears.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"


def clocks_for_hour(h: int):
    base = ((h - 7) % 24) * 60
    return tuple((base + q) % 1440 for q in (0, 15, 30, 45))


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100.0 * float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def rank_passers(D: pd.DataFrame):
    C = D[D.candidate_gate].copy().sort_values(
        ["min_year_exp", "supportive_anchors", "expectancy", "win_rate", "pf", "max_dd",
         "max_loss_streak", "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, False, True, True, True, True, True],
    ).reset_index(drop=True)
    C["dev_rank"] = np.arange(1, len(C) + 1)
    return C


def representative(D: pd.DataFrame):
    return D.sort_values(
        ["candidate_gate", "anchor_gate", "pooled_gate", "era_gate", "min_year_exp",
         "supportive_anchors", "expectancy", "win_rate", "pf", "max_dd", "max_loss_streak",
         "hold_min", "lookback_min", "character_rule"],
        ascending=[False, False, False, False, False, False, False, False, False, True, True,
                   True, True, True],
    ).reset_index(drop=True).iloc[0]


def row_summary(r, coverage: float, full_gate_passers: int, label: str):
    return {
        "stage": label,
        "hour_wib": HOUR_WIB,
        "coverage": coverage,
        "formal_status": "PASS" if bool(r.candidate_gate) else "FAIL",
        "full_gate_passers": int(full_gate_passers),
        "character_rule": r.character_rule,
        "lookback_min": int(r.lookback_min),
        "hold_min": int(r.hold_min),
        "trades": int(r.trades),
        "win_rate": r.win_rate,
        "net_pnl": r.net_pnl,
        "expectancy": r.expectancy,
        "pf": r.pf,
        "max_dd": r.max_dd,
        "max_loss_streak": int(r.max_loss_streak),
        "supportive_anchors": int(r.supportive_anchors),
        "evaluable_anchors": int(r.evaluable_anchors),
        "anchor_gate": bool(r.anchor_gate),
        "pooled_gate": bool(r.pooled_gate),
        "era_gate": bool(r.era_gate),
        "min_year_exp": r.min_year_exp,
        "years_wr55": int(r.years_wr55),
        "y2022_wr": r.y2022_wr, "y2022_exp": r.y2022_exp, "y2022_net": r.y2022_net, "y2022_pf": r.y2022_pf,
        "y2023_wr": r.y2023_wr, "y2023_exp": r.y2023_exp, "y2023_net": r.y2023_net, "y2023_pf": r.y2023_pf,
        "y2024_wr": r.y2024_wr, "y2024_exp": r.y2024_exp, "y2024_net": r.y2024_net, "y2024_pf": r.y2024_pf,
    }


def run_grid(cache, lookbacks, holds):
    rows = [e12.candidate(cache, lb, hold, rule)
            for lb in lookbacks for hold in holds for rule in e12.RULES]
    return pd.DataFrame(rows)


def extract_selected(x5, r):
    pa, pz = e12.base.PARTS["development"]
    lb = int(r.lookback_min)
    hold = int(r.hold_min)
    rule = str(r.character_rule)
    rows = []
    for clock in clocks_for_hour(HOUR_WIB):
        S = e12.e11.state_frame(x5, clock, lb)
        ent = pd.DatetimeIndex(S.entry_ts)
        pre = pd.DatetimeIndex(S.pre_ts)
        masks = e12.masks_for_frame(S)
        ex, valid, xp, delta, _ = e12.e3.hold_base(x5, S, hold)
        ex = pd.DatetimeIndex(ex)
        m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & masks[rule]
        gross = e12.NOTIONAL * np.asarray(delta, float)[m]
        net = gross - e12.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({
                "hour_wib": HOUR_WIB,
                "anchor_utc_min": int(clock),
                "lookback_min": lb,
                "hold_min": hold,
                "character_rule": rule,
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "gross": float(g),
                "net": float(n),
            })
    T = pd.DataFrame(rows).sort_values(["entry_ts", "anchor_utc_min"]).reset_index(drop=True)
    if len(T) != int(r.trades):
        raise AssertionError(f"selected extraction mismatch {len(T)} != {int(r.trades)}")
    return T


def replay_flat(T: pd.DataFrame):
    T = T.sort_values(["entry_ts", "anchor_utc_min"]).reset_index(drop=True)
    accepted, blocked = [], []
    open_until = None
    for r in T.itertuples(index=False):
        entry = pd.Timestamp(r.entry_ts)
        exit_ = pd.Timestamp(r.exit_ts)
        d = r._asdict()
        if open_until is None or entry >= open_until:
            accepted.append(d)
            open_until = exit_
        else:
            d["blocked_by_open_until"] = open_until
            blocked.append(d)
    cols = list(T.columns)
    A = pd.DataFrame(accepted, columns=cols) if accepted else pd.DataFrame(columns=cols)
    B = pd.DataFrame(blocked) if blocked else pd.DataFrame(columns=cols + ["blocked_by_open_until"])
    return A, B


def stats(T: pd.DataFrame):
    if len(T) == 0:
        return e12.summarize(np.array([]), np.array([]))
    return e12.summarize(T.net.to_numpy(float), T.gross.to_numpy(float))


def executable_diagnostic(E: pd.DataFrame):
    A, B = replay_flat(E)
    s = stats(A)
    summary = pd.DataFrame([{
        "source_signals": len(E),
        "accepted_trades": len(A),
        "blocked_signals": len(B),
        "blocked_pct": len(B) / len(E) if len(E) else np.nan,
        "win_rate": s["win_rate"], "net_pnl": s["net_pnl"], "expectancy": s["expectancy"],
        "pf": s["pf"], "max_dd": s["max_dd"], "max_loss_streak": int(s["max_loss_streak"]),
        "max_win_streak": int(s["max_win_streak"]),
    }])
    years = []
    yy = pd.DatetimeIndex(A.entry_ts).year if len(A) else np.array([], int)
    for y in YEARS:
        Y = A.loc[yy == y].copy() if len(A) else A.copy()
        sy = stats(Y)
        years.append({
            "year": y, "trades": int(sy["trades"]), "win_rate": sy["win_rate"],
            "net_pnl": sy["net_pnl"], "expectancy": sy["expectancy"], "pf": sy["pf"],
            "max_dd": sy["max_dd"], "max_loss_streak": int(sy["max_loss_streak"]),
        })
    return A, B, summary, pd.DataFrame(years)


def main():
    e12.base.synthetic_tests()
    x5, coverage = e12.base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    if len(e12.RULES) != EXPECTED_RULES:
        raise AssertionError(f"rule grammar drift: {len(e12.RULES)} != {EXPECTED_RULES}")

    e12.CLOCKS = clocks_for_hour(HOUR_WIB)
    cache = e12.prep(x5)

    # Stage 0: exact E15A reproduction for hour 02.
    e12.LOOKBACKS = BASE_LOOKBACKS
    e12.HOLDS = BASE_HOLDS
    B0 = run_grid(cache, BASE_LOOKBACKS, BASE_HOLDS)
    if len(B0) != len(BASE_LOOKBACKS) * len(BASE_HOLDS) * EXPECTED_RULES:
        raise AssertionError(f"baseline grid mismatch: {len(B0)}")
    b = representative(B0)
    if not (str(b.character_rule) == "DRIVE_DOWN__STR_B60_80" and int(b.lookback_min) == 120 and
            int(b.hold_min) == 360 and int(b.trades) == 311):
        raise AssertionError(
            f"E15A baseline reproduction drift: {b.character_rule}/LB{b.lookback_min}/H{b.hold_min}/N{b.trades}"
        )
    B0.to_csv(OUT_BASE_GRID, index=False)
    pd.DataFrame([row_summary(b, coverage, int(B0.candidate_gate.sum()), "E15A_BASELINE_REPRODUCTION")]).to_csv(
        OUT_BASE_SUMMARY, index=False
    )

    # Stage 1: preregistered timing-resolution refinement. Grammar and gates are unchanged.
    e12.LOOKBACKS = LOOKBACKS
    e12.HOLDS = HOLDS
    D = run_grid(cache, LOOKBACKS, HOLDS)
    if len(D) != EXPECTED_REFINED:
        raise AssertionError(f"refined grid mismatch: {len(D)} != {EXPECTED_REFINED}")
    D.insert(0, "hour_wib", HOUR_WIB)
    C = rank_passers(D)
    r = C.iloc[0] if len(C) else representative(D)

    D.to_csv(OUT_GRID, index=False)
    C.to_csv(OUT_PASSERS, index=False)
    D.sort_values(
        ["candidate_gate", "anchor_gate", "pooled_gate", "era_gate", "min_year_exp",
         "supportive_anchors", "expectancy", "win_rate", "pf", "max_dd", "max_loss_streak"],
        ascending=[False, False, False, False, False, False, False, False, False, True, True],
    ).head(100).to_csv(OUT_NEAR, index=False)
    pd.DataFrame([row_summary(r, coverage, int(D.candidate_gate.sum()), "E16A_REFINED")]).to_csv(OUT_SUMMARY, index=False)

    E = extract_selected(x5, r)
    A, Blk, ES, EY = executable_diagnostic(E)
    E.to_csv(OUT_EVENTS, index=False)
    A.to_csv(OUT_ACCEPTED, index=False)
    Blk.to_csv(OUT_BLOCKED, index=False)
    ES.to_csv(OUT_EXEC_SUMMARY, index=False)
    EY.to_csv(OUT_EXEC_YEARS, index=False)

    formal = len(C) > 0
    status = "ETH_E16A_02_03WIB_NATIVE_CHARACTER_FOUND" if formal else "ETH_E16A_02_03WIB_NO_FORMAL_PASS"
    OUT_STATUS.write_text(status + "\n")

    es = ES.iloc[0]
    lines = [
        "# ETH E16A — 02:00–03:00 WIB LONG Native Character Rediscovery", "",
        "**Development-only. OOS CLOSED. No live authorization.**", "",
        "## Preregistered question", "",
        "Can 02:00–03:00 WIB produce a robust native ETH LONG character after timing calibration while preserving the exact E12 90-rule grammar and formal gates?", "",
        f"ETHUSDT 5m Development coverage: **{coverage:.4%}**.", "",
        "## Stage 0 — E15A baseline reproduction", "",
        f"Reproduced: **{b.character_rule} / LB{int(b.lookback_min)} / H{int(b.hold_min)}**.",
        f"N {int(b.trades)}, WR {pct(b.win_rate)}, net {money(b.net_pnl)}, exp {money(b.expectancy)}, PF {float(b.pf):.3f}, DD {money(b.max_dd)}, LS {int(b.max_loss_streak)}.",
        f"Gates: anchor={bool(b.anchor_gate)}, pooled={bool(b.pooled_gate)}, era={bool(b.era_gate)}. 2024 WR {pct(b.y2024_wr)}, exp {money(b.y2024_exp)}, PF {float(b.y2024_pf):.3f}.", "",
        "## Stage 1 — refined timing grid", "",
        f"Grid: **{len(D):,} candidates** = {len(LOOKBACKS)} lookbacks × {len(HOLDS)} holds × {len(e12.RULES)} rules.",
        f"Formal full-gate passers: **{len(C)}**.", "",
        "### Selected Development representative", "",
        f"**{r.character_rule} / LB{int(r.lookback_min)} / H{int(r.hold_min)}**",
        f"- Formal status: **{'PASS' if bool(r.candidate_gate) else 'FAIL'}**",
        f"- N {int(r.trades)}, WR {pct(r.win_rate)}, net {money(r.net_pnl)}, exp {money(r.expectancy)}, PF {float(r.pf):.3f}, DD {money(r.max_dd)}, LS {int(r.max_loss_streak)}",
        f"- anchors supportive/evaluable: {int(r.supportive_anchors)}/{int(r.evaluable_anchors)}",
        f"- gates: anchor={bool(r.anchor_gate)}, pooled={bool(r.pooled_gate)}, era={bool(r.era_gate)}", "",
        "### Development-year stability", "",
        "| Year | WR | Net | Exp | PF |",
        "|---:|---:|---:|---:|---:|",
        f"| 2022 | {pct(r.y2022_wr)} | {money(r.y2022_net)} | {money(r.y2022_exp)} | {float(r.y2022_pf):.3f} |",
        f"| 2023 | {pct(r.y2023_wr)} | {money(r.y2023_net)} | {money(r.y2023_exp)} | {float(r.y2023_pf):.3f} |",
        f"| 2024 | {pct(r.y2024_wr)} | {money(r.y2024_net)} | {money(r.y2024_exp)} | {float(r.y2024_pf):.3f} |", "",
        "## Executable-opportunity diagnostic", "",
        "The formal gate above is still the original pooled E12 gate. This replay is diagnostic only and removes within-hour anchor overlap chronologically.", "",
        f"Source signals **{int(es.source_signals)}** → accepted **{int(es.accepted_trades)}**, blocked **{int(es.blocked_signals)}** ({pct(es.blocked_pct)}).",
        f"Executable WR {pct(es.win_rate)}, net {money(es.net_pnl)}, exp {money(es.expectancy)}, PF {float(es.pf):.3f}, DD {money(es.max_dd)}, LS {int(es.max_loss_streak)}.", "",
        "| Year | Executable N | WR | Net | Exp | PF | DD | LS |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for y in EY.itertuples(index=False):
        lines.append(
            f"| {int(y.year)} | {int(y.trades)} | {pct(y.win_rate)} | {money(y.net_pnl)} | {money(y.expectancy)} | "
            f"{float(y.pf):.3f} | {money(y.max_dd)} | {int(y.max_loss_streak)} |"
        )
    lines += [
        "", "## Verdict", "", f"**{status}**", "",
        "No gate was relaxed and no OOS data was exposed for selection. All grids, passers, near-misses, and executable-overlap diagnostics are persisted with this result.",
        "Research/shadow only; this does not authorize live trading.",
    ]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
