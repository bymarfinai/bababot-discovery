#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as e12a
import eth_economic_first_e11_market_state_character as e11

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E13A_ONE_POSITION_LONG_22_04WIB"
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
MAX_HOLDS = (240, 480, 720, 960, 1440, 2160, 2880)

# UTC quarter-hour clocks. WIB = UTC+7.
CONFIGS = (
    {"source":"E12J_22_23_NEARMISS", "formal":False, "rule":"RV_MID__RANGE_HIGH", "lb":120,
     "clocks":(900,915,930,945)},
    {"source":"E12K_23_00_FORMAL", "formal":True, "rule":"DRIVE_UP__STR_B60_80", "lb":60,
     "clocks":(960,975,990,1005)},
    {"source":"E12L_00_01_FORMAL", "formal":True, "rule":"EFF_LOW__RANGE_HIGH", "lb":30,
     "clocks":(1020,1035,1050,1065)},
    {"source":"E12M_01_02_FORMAL", "formal":True, "rule":"EFF_HIGH__RV_LOW", "lb":240,
     "clocks":(1080,1095,1110,1125)},
    {"source":"E12N_02_03_NEARMISS", "formal":False, "rule":"EFF_HIGH__RV_HIGH", "lb":360,
     "clocks":(1140,1155,1170,1185)},
    {"source":"E12O_03_04_FORMAL", "formal":True, "rule":"RV_HIGH__RANGE_MID", "lb":360,
     "clocks":(1200,1215,1230,1245)},
)
POLICIES = ("FORMAL_ONLY", "FORMAL_PLUS_NEARMISS")


def pct(x):
    return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"


def money(x):
    return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def build_all_events(x5: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for cfg in CONFIGS:
        for clock in cfg["clocks"]:
            S = e11.state_frame(x5, clock, cfg["lb"])
            masks = e12a.masks_for_frame(S)
            m = masks[cfg["rule"]]
            if not np.any(m):
                continue
            parts.append(pd.DataFrame({
                "entry_ts": pd.DatetimeIndex(S.entry_ts)[m],
                "pre_ts": pd.DatetimeIndex(S.pre_ts)[m],
                "entry_ix": S.entry_ix.to_numpy(int)[m],
                "entry_price": S.entry_price.to_numpy(float)[m],
                "source": cfg["source"],
                "source_formal": bool(cfg["formal"]),
                "character_rule": cfg["rule"],
                "lookback_min": int(cfg["lb"]),
                "clock_utc_min": int(clock),
            }))
    if not parts:
        raise RuntimeError("no E13A events built")
    E = pd.concat(parts, ignore_index=True).sort_values(["entry_ts", "clock_utc_min", "source"]).reset_index(drop=True)
    if E.duplicated(["entry_ts"]).any():
        # The frozen six hour-native configurations use disjoint quarter-hour clocks.
        raise AssertionError("unexpected duplicate entry timestamps")
    return E


def sequential_candidate(x5: pd.DataFrame, Eall: pd.DataFrame, policy: str, max_hold: int):
    pa, pz = base.PARTS["development"]
    E = Eall.copy()
    if policy == "FORMAL_ONLY":
        E = E[E.source_formal].copy()
    elif policy != "FORMAL_PLUS_NEARMISS":
        raise ValueError(policy)

    # Full possible timeout path must remain inside Development.
    E = E[(E.pre_ts >= pa) & (E.entry_ts >= pa) &
          ((E.entry_ts + pd.Timedelta(minutes=max_hold)) <= pz)].copy()
    E = E.sort_values(["entry_ts", "clock_utc_min", "source"]).reset_index(drop=True)

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
        # Strict continuity from entry bar through timeout bar.
        expected_last_open = ent + pd.Timedelta(minutes=max_hold - BAR_MIN)
        if idx[last_j] != expected_last_open:
            continue

        exit_j = None
        exit_net = None
        exit_gross = None
        reason = "TIMEOUT"
        for k in range(max_bars):
            j = ei + k
            cp = float(close[j])
            gross = NOTIONAL * ((cp - ep) / ep)
            net = gross - FEE
            if net > 0:
                exit_j = j
                exit_net = net
                exit_gross = gross
                reason = "PROFIT"
                break
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
            "policy": policy, "max_hold_min": max_hold,
            "entry_ts": ent, "exit_ts": exit_ts, "duration_min": duration,
            "entry_price": ep, "exit_price": cp,
            "source": r.source, "source_formal": bool(r.source_formal),
            "character_rule": r.character_rule, "lookback_min": int(r.lookback_min),
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
        duration_p75 = float(np.quantile(d, .75)); duration_p90 = float(np.quantile(d, .90))
    else:
        s = e12a.summarize(np.array([]), np.array([]))
        timeout_rate = np.nan; timeout_mean = np.nan
        duration_mean = duration_median = duration_p75 = duration_p90 = np.nan

    row = {
        "policy": policy, "max_hold_min": max_hold,
        "candidate_signals": int(len(E)), "accepted_trades": int(len(T)),
        "busy_skips": int(skipped_busy),
        "acceptance_rate": float(len(T) / len(E)) if len(E) else np.nan,
        **s,
        "timeout_rate": timeout_rate, "timeout_mean_pnl": timeout_mean,
        "duration_mean_min": duration_mean, "duration_median_min": duration_median,
        "duration_p75_min": duration_p75, "duration_p90_min": duration_p90,
    }

    # Source counts among actually accepted trades.
    for cfg in CONFIGS:
        key = cfg["source"]
        row[f"accepted__{key}"] = int((T.source == key).sum()) if len(T) else 0

    era_ok = True
    years_wr80 = 0
    min_year_exp = np.inf
    for y in YEARS:
        if len(T):
            ym = pd.DatetimeIndex(T.entry_ts).year == y
            Ty = T.loc[ym]
            ys = e12a.summarize(Ty.net_pnl.to_numpy(float), Ty.gross_pnl.to_numpy(float))
        else:
            ys = e12a.summarize(np.array([]), np.array([]))
        row.update({
            f"y{y}_trades": int(ys["trades"]), f"y{y}_wr": ys["win_rate"],
            f"y{y}_net": ys["net_pnl"], f"y{y}_exp": ys["expectancy"], f"y{y}_pf": ys["pf"],
        })
        ok = bool(
            ys["trades"] >= 40 and np.isfinite(ys["win_rate"]) and ys["win_rate"] >= .75 and
            ys["net_pnl"] > 0 and np.isfinite(ys["expectancy"]) and ys["expectancy"] > 0 and
            np.isfinite(ys["pf"]) and ys["pf"] >= 1.30
        )
        era_ok &= ok
        years_wr80 += int(np.isfinite(ys["win_rate"]) and ys["win_rate"] >= .80)
        min_year_exp = min(min_year_exp, ys["expectancy"] if np.isfinite(ys["expectancy"]) else -np.inf)

    row["years_wr80"] = int(years_wr80)
    row["min_year_exp"] = float(min_year_exp)
    row["pooled_gate"] = bool(
        row["accepted_trades"] >= 150 and np.isfinite(row["win_rate"]) and row["win_rate"] >= .80 and
        row["net_pnl"] > 0 and np.isfinite(row["expectancy"]) and row["expectancy"] >= .50 and
        np.isfinite(row["pf"]) and row["pf"] >= 1.50 and row["max_dd"] <= 125 and
        row["max_loss_streak"] <= 4 and np.isfinite(row["timeout_rate"]) and row["timeout_rate"] <= .20
    )
    row["era_gate"] = bool(era_ok and years_wr80 >= 2)
    row["candidate_gate"] = bool(row["pooled_gate"] and row["era_gate"])
    return row, T


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    Eall = build_all_events(x5)

    rows = []
    ledgers = {}
    for policy in POLICIES:
        for h in MAX_HOLDS:
            row, T = sequential_candidate(x5, Eall, policy, h)
            rows.append(row)
            ledgers[(policy, h)] = T
    D = pd.DataFrame(rows)
    if len(D) != 14:
        raise AssertionError(f"expected 14 candidates, got {len(D)}")
    D.to_csv(OUT_GRID, index=False)

    C = D[D.candidate_gate].copy()
    if len(C):
        C["policy_tie"] = C.policy.map({"FORMAL_ONLY":0, "FORMAL_PLUS_NEARMISS":1})
        C = C.sort_values(
            ["min_year_exp", "timeout_rate", "max_dd", "pf", "expectancy", "win_rate",
             "duration_p90_min", "max_hold_min", "policy_tie"],
            ascending=[False, True, True, False, False, False, True, True, True],
        ).reset_index(drop=True)
        C["dev_rank"] = np.arange(1, len(C)+1)
    C.to_csv(OUT_LEADER, index=False)

    lines = [
        "# ETH E13A — One-Position Sequential LONG 22:00–04:00 WIB Result", "",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Development only; OOS remained closed.",
        "Execution semantics: first valid qualifying signal opens one LONG; while open, later signals are skipped; exit at first completed 5m close with net PnL > $0 after $0.75 fee, otherwise force-close at the preregistered max hold.",
        f"Candidates: **{len(D)}** = 2 entry policies × 7 maximum holds; formal passers: **{len(C)}**.", "",
        "## Full Development grid", "",
        "| Policy | MaxHold | Signals | Trades | SkipBusy | WR | Net | Exp | PF | DD | LS | Timeout | MedDur | P90Dur | 2022 WR/Exp | 2023 | 2024 | Pooled | Era | Full |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    show = D.sort_values(["policy", "max_hold_min"])
    for r in show.itertuples(index=False):
        lines.append(
            f"| {r.policy} | {int(r.max_hold_min)}m | {int(r.candidate_signals)} | {int(r.accepted_trades)} | {int(r.busy_skips)} | "
            f"{pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | "
            f"{pct(r.timeout_rate)} | {r.duration_median_min:.0f}m | {r.duration_p90_min:.0f}m | "
            f"{pct(r.y2022_wr)}/{money(r.y2022_exp)} | {pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | "
            f"{'YES' if r.pooled_gate else 'NO'} | {'YES' if r.era_gate else 'NO'} | {'YES' if r.candidate_gate else 'NO'} |"
        )

    if len(C) == 0:
        status = "ETH_E13A_NO_SEQUENTIAL_LONG_EXECUTION_PASSER"
        OUT_STATUS.write_text(status + "\n")
        lines += ["", f"**Status: {status}**", "",
                  "No candidate passed the frozen pooled + cross-era execution gates. No threshold is relaxed and no OOS data is opened.",
                  "The complete 14-row grid is the formal result; any near-miss interpretation is descriptive only.", "", "Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines) + "\n")
        print(OUT_RESULT.read_text())
        return

    sel = C.iloc[0]
    key = (sel["policy"], int(sel["max_hold_min"]))
    T = ledgers[key].copy()
    T.to_csv(OUT_TRADES, index=False)
    B = T.groupby(["source", "source_formal"], as_index=False).agg(
        trades=("net_pnl","size"), wins=("net_positive","sum"), net_pnl=("net_pnl","sum"),
        expectancy=("net_pnl","mean"), median_duration_min=("duration_min","median"),
        timeout_trades=("exit_reason", lambda s: int((s == "TIMEOUT").sum())),
    )
    B["win_rate"] = B.wins / B.trades
    B["timeout_rate"] = B.timeout_trades / B.trades
    B.to_csv(OUT_BREAKDOWN, index=False)

    status = "ETH_E13A_SEQUENTIAL_LONG_EXECUTION_PASSER_FOUND"
    OUT_STATUS.write_text(status + "\n")
    lines += ["", "## Development-selected sequential executor", "",
              f"**{sel['policy']} / max hold {int(sel['max_hold_min'])}m**", "",
              f"Accepted trades **{int(sel['accepted_trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, loss streak **{int(sel['max_loss_streak'])}**, timeout **{pct(sel['timeout_rate'])}**, median duration **{float(sel['duration_median_min']):.0f}m**, p90 duration **{float(sel['duration_p90_min']):.0f}m**.", "",
              "### Cross-era", "",
              f"- 2022: N {int(sel['y2022_trades'])}, WR {pct(sel['y2022_wr'])}, net {money(sel['y2022_net'])}, exp {money(sel['y2022_exp'])}, PF {float(sel['y2022_pf']):.3f}",
              f"- 2023: N {int(sel['y2023_trades'])}, WR {pct(sel['y2023_wr'])}, net {money(sel['y2023_net'])}, exp {money(sel['y2023_exp'])}, PF {float(sel['y2023_pf']):.3f}",
              f"- 2024: N {int(sel['y2024_trades'])}, WR {pct(sel['y2024_wr'])}, net {money(sel['y2024_net'])}, exp {money(sel['y2024_exp'])}, PF {float(sel['y2024_pf']):.3f}", "",
              "### Accepted trade sources", "",
              "| Source | E12 formal? | Trades | WR | Net | Exp | Timeout | Median duration |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in B.itertuples(index=False):
        lines.append(f"| {r.source} | {'YES' if r.source_formal else 'NO'} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {pct(r.timeout_rate)} | {float(r.median_duration_min):.0f}m |")
    lines += ["", f"**Status: {status}**", "", "Development execution discovery only. OOS remains closed. No live promotion."]
    OUT_RESULT.write_text("\n".join(lines) + "\n")
    print(OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
