#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as e12a
import eth_e13a_one_position_long_22_04wib as e13a

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E13B_PROFIT_FLOOR_LONG_22_04WIB"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_BREAKDOWN = ROOT / f"{PFX}_SelectedSourceBreakdown.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

NOTIONAL = 500.0
FEE = 0.75
BAR_MIN = 5
YEARS = (2022, 2023, 2024)
TARGET_NET_PCTS = (0.001, 0.002, 0.003, 0.005, 0.0075, 0.010, 0.015)
MAX_HOLDS = (240, 480, 720, 960, 1440, 2160, 2880)


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def sequential_candidate(x5: pd.DataFrame, Eall: pd.DataFrame, target_pct: float, max_hold: int):
    pa, pz = base.PARTS["development"]
    E = Eall[Eall.source_formal].copy()
    E = E[(E.pre_ts >= pa) & (E.entry_ts >= pa) &
          ((E.entry_ts + pd.Timedelta(minutes=max_hold)) <= pz)].copy()
    E = E.sort_values(["entry_ts", "clock_utc_min", "source"]).reset_index(drop=True)

    target_net = NOTIONAL * float(target_pct)
    close = x5.close.to_numpy(float)
    idx = x5.index
    max_bars = max_hold // BAR_MIN
    busy_until = pd.Timestamp.min.tz_localize("UTC")
    accepted = []
    skipped_busy = 0

    for r in E.itertuples(index=False):
        ent = pd.Timestamp(r.entry_ts)
        if ent < busy_until:
            skipped_busy += 1
            continue
        ei = int(r.entry_ix)
        ep = float(r.entry_price)
        last_j = ei + max_bars - 1
        if last_j >= len(x5):
            continue
        if idx[last_j] != ent + pd.Timedelta(minutes=max_hold - BAR_MIN):
            continue

        exit_j = None
        exit_gross = None
        exit_net = None
        reason = "TIMEOUT"
        for k in range(max_bars):
            j = ei + k
            cp = float(close[j])
            gross = NOTIONAL * ((cp - ep) / ep)
            net = gross - FEE
            if net >= target_net:
                exit_j = j; exit_gross = gross; exit_net = net; reason = "TARGET"; break
        if exit_j is None:
            exit_j = last_j
            cp = float(close[exit_j])
            exit_gross = NOTIONAL * ((cp - ep) / ep)
            exit_net = exit_gross - FEE
        else:
            cp = float(close[exit_j])

        exit_ts = idx[exit_j] + pd.Timedelta(minutes=BAR_MIN)
        duration = int((exit_ts - ent).total_seconds() // 60)
        busy_until = exit_ts
        accepted.append({
            "target_net_pct": target_pct, "target_net_usd": target_net, "max_hold_min": max_hold,
            "entry_ts": ent, "exit_ts": exit_ts, "duration_min": duration,
            "entry_price": ep, "exit_price": cp,
            "source": r.source, "character_rule": r.character_rule, "lookback_min": int(r.lookback_min),
            "clock_utc_min": int(r.clock_utc_min),
            "gross_pnl": float(exit_gross), "fee": FEE, "net_pnl": float(exit_net),
            "exit_reason": reason, "net_positive": bool(exit_net > 0),
        })

    T = pd.DataFrame(accepted)
    if len(T):
        T = T.sort_values("entry_ts").reset_index(drop=True)
        s = e12a.summarize(T.net_pnl.to_numpy(float), T.gross_pnl.to_numpy(float))
        d = T.duration_min.to_numpy(float)
        timeout = T.exit_reason.eq("TIMEOUT")
        timeout_rate = float(timeout.mean())
        timeout_mean = float(T.loc[timeout, "net_pnl"].mean()) if timeout.any() else np.nan
        duration_mean = float(np.mean(d)); duration_median = float(np.median(d))
        duration_p75 = float(np.quantile(d,.75)); duration_p90 = float(np.quantile(d,.90))
    else:
        s = e12a.summarize(np.array([]), np.array([]))
        timeout_rate = timeout_mean = duration_mean = duration_median = duration_p75 = duration_p90 = np.nan

    row = {
        "target_net_pct": target_pct, "target_net_usd": target_net, "max_hold_min": max_hold,
        "candidate_signals": int(len(E)), "accepted_trades": int(len(T)), "busy_skips": int(skipped_busy),
        "acceptance_rate": float(len(T)/len(E)) if len(E) else np.nan,
        **s,
        "timeout_rate": timeout_rate, "timeout_mean_pnl": timeout_mean,
        "duration_mean_min": duration_mean, "duration_median_min": duration_median,
        "duration_p75_min": duration_p75, "duration_p90_min": duration_p90,
    }
    for cfg in e13a.CONFIGS:
        if cfg["formal"]:
            row[f"accepted__{cfg['source']}"] = int((T.source == cfg["source"]).sum()) if len(T) else 0

    era_ok = True
    years_wr70 = 0
    min_year_exp = np.inf
    for y in YEARS:
        if len(T):
            ym = pd.DatetimeIndex(T.entry_ts).year == y
            Ty = T.loc[ym]
            ys = e12a.summarize(Ty.net_pnl.to_numpy(float), Ty.gross_pnl.to_numpy(float))
        else:
            ys = e12a.summarize(np.array([]), np.array([]))
        row.update({
            f"y{y}_trades": int(ys["trades"]), f"y{y}_wr": ys["win_rate"], f"y{y}_net": ys["net_pnl"],
            f"y{y}_exp": ys["expectancy"], f"y{y}_pf": ys["pf"],
        })
        ok = bool(
            ys["trades"] >= 40 and np.isfinite(ys["win_rate"]) and ys["win_rate"] >= .65 and
            ys["net_pnl"] > 0 and np.isfinite(ys["expectancy"]) and ys["expectancy"] > 0 and
            np.isfinite(ys["pf"]) and ys["pf"] >= 1.15
        )
        era_ok &= ok
        years_wr70 += int(np.isfinite(ys["win_rate"]) and ys["win_rate"] >= .70)
        min_year_exp = min(min_year_exp, ys["expectancy"] if np.isfinite(ys["expectancy"]) else -np.inf)

    row["years_wr70"] = int(years_wr70)
    row["min_year_exp"] = float(min_year_exp)
    row["pooled_gate"] = bool(
        row["accepted_trades"] >= 150 and np.isfinite(row["win_rate"]) and row["win_rate"] >= .70 and
        row["net_pnl"] > 0 and np.isfinite(row["expectancy"]) and row["expectancy"] >= .50 and
        np.isfinite(row["pf"]) and row["pf"] >= 1.30 and row["max_dd"] <= 125 and
        row["max_loss_streak"] <= 6 and np.isfinite(row["timeout_rate"]) and row["timeout_rate"] <= .30
    )
    row["era_gate"] = bool(era_ok and years_wr70 >= 2)
    row["candidate_gate"] = bool(row["pooled_gate"] and row["era_gate"])
    return row, T


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    Eall = e13a.build_all_events(x5)

    rows = []
    ledgers = {}
    for t in TARGET_NET_PCTS:
        for h in MAX_HOLDS:
            row, T = sequential_candidate(x5, Eall, t, h)
            rows.append(row); ledgers[(t,h)] = T
    D = pd.DataFrame(rows)
    if len(D) != 49:
        raise AssertionError(f"expected 49 candidates, got {len(D)}")
    D.to_csv(OUT_GRID, index=False)

    C = D[D.candidate_gate].copy()
    if len(C):
        C = C.sort_values(
            ["min_year_exp", "max_dd", "pf", "expectancy", "win_rate", "timeout_rate",
             "duration_p90_min", "max_hold_min", "target_net_pct"],
            ascending=[False, True, False, False, False, True, True, True, True],
        ).reset_index(drop=True)
        C["dev_rank"] = np.arange(1,len(C)+1)
    C.to_csv(OUT_LEADER,index=False)

    lines = [
        "# ETH E13B — Sequential LONG Minimum-Profit-Floor Discovery Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Development only; OOS remained closed.",
        "Entry universe: E12 formal LONG characters only inside 22:00–04:00 WIB.",
        "One position maximum; later signals skipped while busy; exit at first completed 5m close meeting the net-profit floor, otherwise timeout.",
        f"Candidates: **{len(D)}** = 7 profit floors × 7 max holds; formal passers: **{len(C)}**.", "",
        "## Full Development grid", "",
        "| NetFloor | MaxHold | Trades | WR | Net | Exp | PF | DD | LS | Timeout | MedDur | P90Dur | 2022 WR/Exp | 2023 | 2024 | Pooled | Era | Full |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in D.sort_values(["target_net_pct","max_hold_min"]).itertuples(index=False):
        lines.append(
            f"| {pct(r.target_net_pct)} ({money(r.target_net_usd)}) | {int(r.max_hold_min)}m | {int(r.accepted_trades)} | {pct(r.win_rate)} | "
            f"{money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.timeout_rate)} | "
            f"{r.duration_median_min:.0f}m | {r.duration_p90_min:.0f}m | {pct(r.y2022_wr)}/{money(r.y2022_exp)} | {pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | "
            f"{'YES' if r.pooled_gate else 'NO'} | {'YES' if r.era_gate else 'NO'} | {'YES' if r.candidate_gate else 'NO'} |"
        )

    if len(C) == 0:
        status = "ETH_E13B_NO_PROFIT_FLOOR_PASSER"
        OUT_STATUS.write_text(status+"\n")
        lines += ["", f"**Status: {status}**", "",
                  "No minimum-profit-floor candidate passed the frozen pooled + era gates. No rescue and no OOS exposure.", "", "Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel = C.iloc[0]
    key = (float(sel["target_net_pct"]), int(sel["max_hold_min"]))
    T = ledgers[key].copy(); T.to_csv(OUT_TRADES,index=False)
    B = T.groupby("source",as_index=False).agg(
        trades=("net_pnl","size"), wins=("net_positive","sum"), net_pnl=("net_pnl","sum"),
        expectancy=("net_pnl","mean"), median_duration_min=("duration_min","median"),
        timeout_trades=("exit_reason",lambda s:int((s=="TIMEOUT").sum())),
    )
    B["win_rate"] = B.wins/B.trades; B["timeout_rate"] = B.timeout_trades/B.trades
    B.to_csv(OUT_BREAKDOWN,index=False)

    status = "ETH_E13B_PROFIT_FLOOR_PASSER_FOUND"
    OUT_STATUS.write_text(status+"\n")
    lines += ["", "## Development-selected executor", "",
              f"**Net floor {pct(sel['target_net_pct'])} = {money(sel['target_net_usd'])} / max hold {int(sel['max_hold_min'])}m**", "",
              f"N **{int(sel['accepted_trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, LS **{int(sel['max_loss_streak'])}**, timeout **{pct(sel['timeout_rate'])}**, median duration **{float(sel['duration_median_min']):.0f}m**, p90 **{float(sel['duration_p90_min']):.0f}m**.", "",
              "### Cross-era", "",
              f"- 2022: N {int(sel['y2022_trades'])}, WR {pct(sel['y2022_wr'])}, net {money(sel['y2022_net'])}, exp {money(sel['y2022_exp'])}, PF {float(sel['y2022_pf']):.3f}",
              f"- 2023: N {int(sel['y2023_trades'])}, WR {pct(sel['y2023_wr'])}, net {money(sel['y2023_net'])}, exp {money(sel['y2023_exp'])}, PF {float(sel['y2023_pf']):.3f}",
              f"- 2024: N {int(sel['y2024_trades'])}, WR {pct(sel['y2024_wr'])}, net {money(sel['y2024_net'])}, exp {money(sel['y2024_exp'])}, PF {float(sel['y2024_pf']):.3f}", "",
              "### Accepted source breakdown", "",
              "| Source | Trades | WR | Net | Exp | Timeout | Median duration |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in B.itertuples(index=False):
        lines.append(f"| {r.source} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {pct(r.timeout_rate)} | {float(r.median_duration_min):.0f}m |")
    lines += ["", f"**Status: {status}**", "", "Development execution discovery only. OOS remains closed; no live promotion."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
