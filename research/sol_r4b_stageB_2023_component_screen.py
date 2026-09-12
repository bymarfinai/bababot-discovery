#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sol_economic_first_h00_long_07_08wib_character as legacy

ROOT = Path(__file__).resolve().parent.parent
COMP_PATH = ROOT / "SOL_R4B_STAGEA_2022_FROZEN_COMPONENTS.csv"
OUT_CELLS = ROOT / "SOL_R4B_STAGEB_2023_CELL_RESULTS.csv"
OUT_VERDICTS = ROOT / "SOL_R4B_STAGEB_2023_COMPONENT_VERDICTS.csv"
OUT_SURVIVORS = ROOT / "SOL_R4B_STAGEB_2023_STABLE_PLATEAUS.csv"
OUT_RESULT = ROOT / "SOL_R4B_STAGEB_2023_COMPONENT_SCREEN.md"
OUT_STATUS = ROOT / "SOL_R4B_STAGEB_2023_Status.txt"

DEV_START = pd.Timestamp("2022-01-01", tz="UTC")
DEV_END = pd.Timestamp("2023-01-01", tz="UTC")
TEST_START = pd.Timestamp("2023-01-01", tz="UTC")
TEST_END = pd.Timestamp("2024-01-01", tz="UTC")

LOOKBACKS = (60, 120, 180, 240, 360)
HOLDS = (120, 240, 360, 480)


def finite(x) -> bool:
    return bool(np.isfinite(x))


def clocks_for_hour(h: int) -> tuple[int, int, int, int]:
    base = ((int(h) - 7) % 24) * 60
    return tuple((base + q) % 1440 for q in (0, 15, 30, 45))


def parse_cells(s: str) -> list[tuple[int, int]]:
    out = []
    for tok in str(s).split(";"):
        tok = tok.strip()
        if not tok:
            continue
        left, right = tok.split("/")
        out.append((int(left.replace("LB", "")), int(right.replace("H", ""))))
    return out


def prep_hour(x5: pd.DataFrame, hour_wib: int, needed: set[tuple[int, int]]) -> dict:
    cache = {}
    needed_lbs = sorted({lb for lb, _ in needed})
    needed_holds = sorted({hold for _, hold in needed})
    for lb in needed_lbs:
        for clock in clocks_for_hour(hour_wib):
            frame = legacy.state_frame(x5, int(clock), int(lb))
            masks = legacy.masks_for_frame(frame)
            entry_ts = pd.DatetimeIndex(pd.to_datetime(frame.entry_ts, utc=True))
            pre_ts = pd.DatetimeIndex(pd.to_datetime(frame.pre_ts, utc=True))
            for hold in needed_holds:
                if (lb, hold) not in needed:
                    continue
                exit_ts, valid, returns = legacy.hold_returns(x5, frame, int(hold))
                cache[(int(clock), int(lb), int(hold))] = (
                    entry_ts,
                    pre_ts,
                    pd.DatetimeIndex(pd.to_datetime(exit_ts, utc=True)),
                    np.asarray(valid, bool),
                    np.asarray(returns, float),
                    masks,
                )
    return cache


def candidate_events(cache: dict, hour_wib: int, lb: int, hold: int, rule: str,
                     start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for clock in clocks_for_hour(hour_wib):
        ent, pre, ex, valid, returns, masks = cache[(int(clock), int(lb), int(hold))]
        m = valid & (pre >= start) & (ent >= start) & (ex < end) & np.asarray(masks[str(rule)], bool)
        gross = legacy.NOTIONAL * returns[m]
        net = gross - legacy.FEE
        for entry_ts, exit_ts, g, n in zip(ent[m], ex[m], gross, net):
            rows.append({"entry_ts": entry_ts, "exit_ts": exit_ts, "clock": int(clock), "gross": float(g), "net": float(n)})
    if not rows:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "clock", "gross", "net"])
    return pd.DataFrame(rows).sort_values(["entry_ts", "clock"]).reset_index(drop=True)


def stats(T: pd.DataFrame) -> dict:
    if len(T) == 0:
        return legacy.summarize(np.array([]), np.array([]))
    return legacy.summarize(T.net.to_numpy(float), T.gross.to_numpy(float))


def main():
    if not COMP_PATH.exists():
        raise FileNotFoundError(COMP_PATH)
    comps = pd.read_csv(COMP_PATH)
    if comps.empty:
        raise AssertionError("Stage-A frozen components are empty")

    frozen_cells = []
    for r in comps.itertuples(index=False):
        for lb, hold in parse_cells(r.component_cells):
            frozen_cells.append({
                "hour_wib": int(r.hour_wib),
                "component_rank": int(r.component_rank),
                "character_rule": str(r.character_rule),
                "component_size": int(r.component_size),
                "component_cells": str(r.component_cells),
                "lookback_min": int(lb),
                "hold_min": int(hold),
            })
    F = pd.DataFrame(frozen_cells)
    if F.empty:
        raise AssertionError("No frozen Stage-A cells parsed")

    legacy.base.synthetic_tests()
    x5, coverage = legacy.base.load5("SOLUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low: {coverage}")
    idx = pd.DatetimeIndex(pd.to_datetime(x5.index, utc=True))
    x22 = x5[(idx >= DEV_START) & (idx < DEV_END)].copy()
    x23 = x5[(idx >= TEST_START) & (idx < TEST_END)].copy()

    out = []
    for hour in sorted(F.hour_wib.unique()):
        H = F[F.hour_wib == int(hour)].copy()
        needed = {(int(r.lookback_min), int(r.hold_min)) for r in H.itertuples(index=False)}
        print(f"Stage B H{int(hour):02d} WIB: {len(H)} frozen cells", flush=True)
        cache22 = prep_hour(x22, int(hour), needed)
        cache23 = prep_hour(x23, int(hour), needed)
        for c in H.itertuples(index=False):
            rule = str(c.character_rule)
            lb = int(c.lookback_min)
            hold = int(c.hold_min)
            D = candidate_events(cache22, int(hour), lb, hold, rule, DEV_START, DEV_END)
            T = candidate_events(cache23, int(hour), lb, hold, rule, TEST_START, TEST_END)
            ds = stats(D)
            ts = stats(T)

            dev_wr = float(ds["win_rate"]) if finite(ds["win_rate"]) else np.nan
            dev_exp = float(ds["expectancy"]) if finite(ds["expectancy"]) else np.nan
            dev_pf = float(ds["pf"]) if finite(ds["pf"]) else np.nan
            dev_dd = float(ds["max_dd"]) if finite(ds["max_dd"]) else np.nan
            dev_ls = int(ds["max_loss_streak"])
            wr = float(ts["win_rate"]) if finite(ts["win_rate"]) else np.nan
            exp = float(ts["expectancy"]) if finite(ts["expectancy"]) else np.nan
            pf = float(ts["pf"]) if finite(ts["pf"]) else np.nan
            dd = float(ts["max_dd"]) if finite(ts["max_dd"]) else np.nan

            wr_change_pp = 100 * (wr - dev_wr) if finite(wr) and finite(dev_wr) else -np.inf
            exp_ret = exp / dev_exp if dev_exp > 0 and finite(exp) else -np.inf
            pf_ret = pf / dev_pf if dev_pf > 0 and finite(pf) else -np.inf
            dd_cap = min(160.0, 1.50 * dev_dd + 20.0)
            ls_warning = max(12, dev_ls + 4)
            viable = bool(
                ts["trades"] >= 50 and finite(wr) and wr >= .52 and ts["net_pnl"] > 0 and
                finite(exp) and exp > 0 and finite(pf) and pf >= 1.15 and finite(dd) and dd <= dd_cap
            )
            stable = bool(viable and wr_change_pp >= -5.0 and exp_ret >= .60 and pf_ret >= .70)

            out.append({
                "hour_wib": int(hour),
                "component_rank": int(c.component_rank),
                "character_rule": rule,
                "component_size": int(c.component_size),
                "lookback_min": lb,
                "hold_min": hold,
                "dev_n": int(ds["trades"]),
                "dev_wr": dev_wr,
                "dev_net": float(ds["net_pnl"]),
                "dev_exp": dev_exp,
                "dev_pf": dev_pf,
                "dev_dd": dev_dd,
                "dev_ls": dev_ls,
                "test_n": int(ts["trades"]),
                "test_wr": wr,
                "test_net": float(ts["net_pnl"]),
                "test_exp": exp,
                "test_pf": pf,
                "test_dd": dd,
                "test_ls": int(ts["max_loss_streak"]),
                "wr_change_pp": wr_change_pp,
                "exp_retention": exp_ret,
                "pf_retention": pf_ret,
                "dd_cap": dd_cap,
                "ls_warning_threshold": int(ls_warning),
                "risk_clustering_warning": bool(ts["max_loss_streak"] > ls_warning),
                "economically_viable": viable,
                "performance_stable": stable,
            })

    R = pd.DataFrame(out).sort_values(["hour_wib", "component_rank", "hold_min", "lookback_min"]).reset_index(drop=True)
    if len(R) != len(F):
        raise AssertionError(f"frozen cell mismatch: expected {len(F)}, got {len(R)}")
    R.to_csv(OUT_CELLS, index=False)

    verdicts = []
    survivors = []
    for (hour, rank), G in R.groupby(["hour_wib", "component_rank"], sort=True):
        meta = comps[(comps.hour_wib == hour) & (comps.component_rank == rank)].iloc[0]
        n = len(G)
        v = int(G.economically_viable.sum())
        s = int(G.performance_stable.sum())
        frac = v / n if n else 0.0
        if n >= 2 and v >= 2 and s >= 1 and frac >= .50:
            verdict = "STABLE_PLATEAU_FROZEN"
        elif v >= 2:
            verdict = "PARTIAL_PLATEAU_PERSISTENCE"
        elif n == 1 and s >= 1:
            verdict = "NARROW_STABLE_POINT"
        else:
            verdict = "PLATEAU_DEGRADATION_FAIL"
        row = {
            "hour_wib": int(hour),
            "component_rank": int(rank),
            "character_rule": str(meta.character_rule),
            "component_size": int(n),
            "component_cells": str(meta.component_cells),
            "dev_component_wr_min": float(meta.wr_min),
            "dev_component_wr_mean": float(meta.wr_mean),
            "dev_component_exp_floor": float(meta.exp_floor),
            "dev_component_exp_mean": float(meta.exp_mean),
            "test_viable_cells": v,
            "test_stable_cells": s,
            "test_viable_fraction": frac,
            "test_positive_net_cells": int((G.test_net > 0).sum()),
            "test_positive_exp_cells": int((G.test_exp > 0).sum()),
            "test_median_wr": float(G.test_wr.median()),
            "test_median_exp": float(G.test_exp.median()),
            "test_median_pf": float(G.test_pf.median()),
            "test_max_dd": float(G.test_dd.max()),
            "verdict": verdict,
        }
        verdicts.append(row)
        if verdict == "STABLE_PLATEAU_FROZEN":
            survivors.append(row)

    V = pd.DataFrame(verdicts).sort_values(["hour_wib", "component_rank"]).reset_index(drop=True)
    S = pd.DataFrame(survivors)
    if not S.empty:
        S = S.sort_values(["hour_wib", "component_rank"]).reset_index(drop=True)
    V.to_csv(OUT_VERDICTS, index=False)
    S.to_csv(OUT_SURVIVORS, index=False)

    survivor_hours = sorted(S.hour_wib.unique().tolist()) if not S.empty else []
    partial = V[V.verdict == "PARTIAL_PLATEAU_PERSISTENCE"]
    narrow = V[V.verdict == "NARROW_STABLE_POINT"]
    lines = [
        "# SOL R4b — Stage B 2023 Connected-Component Screen", "",
        "**COMPONENT MEMBERSHIP WAS FROZEN FROM 2022. EACH CELL IS TESTED AT THE SAME COORDINATE IN 2023. 2024-2026 CLOSED.**", "",
        f"Frozen components tested: **{len(V)}**. Frozen cells tested: **{len(R)}**.",
        f"Stable plateaus: **{len(S)}** across **{len(survivor_hours)}** WIB hours.",
        f"Partial plateau persistence: **{len(partial)}**. Narrow stable points: **{len(narrow)}**.",
        f"Stable-plateau hours: **{', '.join(f'H{int(h):02d}' for h in survivor_hours) if survivor_hours else 'NONE'}**.", "",
        "| Hour | Rank | Character | Size | 2023 viable | Stable | Viable % | Median WR | Median Exp | Median PF | Max DD | Verdict |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in V.itertuples(index=False):
        lines.append(
            f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | `{r.character_rule}` | {int(r.component_size)} | "
            f"{int(r.test_viable_cells)} | {int(r.test_stable_cells)} | {100*float(r.test_viable_fraction):.1f}% | "
            f"{100*float(r.test_median_wr):.2f}% | ${float(r.test_median_exp):+.2f} | {float(r.test_median_pf):.3f} | "
            f"${float(r.test_max_dd):.2f} | {r.verdict} |"
        )
    if not S.empty:
        lines += ["", "## Stable plateaus frozen for Stage C", "",
                  "| Hour | Rank | Character | Size | 2023 viable/stable | Component cells |",
                  "|---:|---:|---|---:|---:|---|"]
        for r in S.itertuples(index=False):
            lines.append(
                f"| H{int(r.hour_wib):02d} | {int(r.component_rank)} | `{r.character_rule}` | {int(r.component_size)} | "
                f"{int(r.test_viable_cells)}/{int(r.test_stable_cells)} | {r.component_cells} |"
            )
    lines += ["", "No component or cell may be modified after observing these 2023 results."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    OUT_STATUS.write_text("SOL_R4B_STAGEB_COMPLETE\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
