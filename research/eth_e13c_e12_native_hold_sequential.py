#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as e12a
import eth_economic_first_e11_market_state_character as e11
import eth_economic_first_e3_drive_strength_fast as e3

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E13C_E12_NATIVE_HOLD_SEQUENTIAL"
OUT_OPPS = ROOT / f"{PFX}_AllOpportunities.csv"
OUT_SUM = ROOT / f"{PFX}_PolicySummary.csv"
OUT_HOUR = ROOT / f"{PFX}_HourExecutionSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_ExecutedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

NOTIONAL = 500.0
FEE = 0.75
YEARS = (2022, 2023, 2024)

# hour_wib: (experiment, formal_status, rule, lookback_min, hold_min)
MAP = {
    0:("E12L","PASS","EFF_LOW__RANGE_HIGH",30,720),
    1:("E12M","PASS","EFF_HIGH__RV_LOW",240,960),
    2:("E12N","FAIL","EFF_HIGH__RV_HIGH",360,720),
    3:("E12O","PASS","RV_HIGH__RANGE_MID",360,240),
    4:("E12P","FAIL","EFF_HIGH__RV_HIGH",120,960),
    5:("E12Q","FAIL","RV_HIGH__RANGE_MID",360,960),
    6:("E12R","FAIL","EFF_LOW__RANGE_MID",60,720),
    7:("E12S","FAIL","EFF_MID__RANGE_LOW",240,720),
    8:("E12T","FAIL","EFF_LOW__RANGE_MID",360,720),
    9:("E12U","FAIL","EFF_LOW__RANGE_HIGH",15,720),
    10:("E12V","FAIL","DRIVE_UP__STR_B80_100",120,960),
    11:("E12W","FAIL","EFF_MID__RANGE_HIGH",360,720),
    12:("E12X","FAIL","DRIVE_UP__STR_B80_100",240,360),
    13:("E12A","FAIL","DRIVE_DOWN__RV_HIGH",60,360),
    14:("E12B","FAIL","DRIVE_UP__STR_B80_100",360,360),
    15:("E12C","FAIL","DRIVE_UP__EFF_HIGH",360,960),
    16:("E12D","FAIL","DRIVE_UP__STR_B20_40",240,960),
    17:("E12E","FAIL","EFF_HIGH__EXT_LOW",30,960),
    18:("E12F","FAIL","DRIVE_DOWN__RANGE_MID",60,720),
    19:("E12G","FAIL","DRIVE_UP__RV_HIGH",240,960),
    20:("E12H","FAIL","RV_LOW__RANGE_HIGH",15,960),
    21:("E12I","FAIL","RV_HIGH__RANGE_MID",240,960),
    22:("E12J","FAIL","RV_MID__RANGE_HIGH",120,960),
    23:("E12K","PASS","DRIVE_UP__STR_B60_80",60,720),
}
PASS_HOURS = {h for h,v in MAP.items() if v[1] == "PASS"}


def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"
def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"

def utc_base(hour_wib: int) -> int:
    return ((hour_wib - 7) % 24) * 60

def build_opportunities(x5: pd.DataFrame) -> pd.DataFrame:
    pa, pz = base.PARTS["development"]
    rows = []
    for hour in range(24):
        exp, formal, rule, lb, hold = MAP[hour]
        for q in (0, 15, 30, 45):
            clock = (utc_base(hour) + q) % 1440
            S = e11.state_frame(x5, clock, lb)
            ent = pd.DatetimeIndex(S.entry_ts)
            pre = pd.DatetimeIndex(S.pre_ts)
            masks = e12a.masks_for_frame(S)
            ex, valid, xp, delta, _ = e3.hold_base(x5, S, hold)
            m = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & masks[rule]
            if not np.any(m):
                continue
            gross = NOTIONAL * delta[m]
            net = gross - FEE
            ep = S.entry_price.to_numpy(float)[m]
            for i in range(int(m.sum())):
                rows.append({
                    "experiment": exp,
                    "formal_status": formal,
                    "source_hour_wib": hour,
                    "anchor_wib": f"{hour:02d}:{q:02d}",
                    "clock_utc_min": clock,
                    "rule": rule,
                    "lookback_min": lb,
                    "hold_min": hold,
                    "entry_ts": ent[m][i],
                    "exit_ts": ex[m][i],
                    "entry_price": float(ep[i]),
                    "exit_price": float(xp[m][i]),
                    "gross_pnl": float(gross[i]),
                    "net_pnl": float(net[i]),
                    "win": bool(net[i] > 0),
                })
    T = pd.DataFrame(rows)
    if len(T) == 0:
        return T
    return T.sort_values(["entry_ts","source_hour_wib","clock_utc_min"]).reset_index(drop=True)


def summarize_df(T: pd.DataFrame):
    if len(T) == 0:
        return e12a.summarize(np.array([]), np.array([]))
    return e12a.summarize(T.net_pnl.to_numpy(float), T.gross_pnl.to_numpy(float))


def sequentialize(T: pd.DataFrame, policy: str):
    if policy == "FORMAL_PASS_ONLY":
        U = T[T.source_hour_wib.isin(PASS_HOURS)].copy()
    elif policy == "ALL_HOURLY_REPRESENTATIVES":
        U = T.copy()
    else:
        raise ValueError(policy)
    U = U.sort_values(["entry_ts","source_hour_wib","clock_utc_min"]).reset_index(drop=True)
    exec_rows, skip_rows = [], []
    busy_until = None
    for r in U.itertuples(index=False):
        if busy_until is None or r.entry_ts >= busy_until:
            d = r._asdict(); d["policy"] = policy; d["execution"] = "EXECUTED"
            exec_rows.append(d)
            busy_until = r.exit_ts
        else:
            d = r._asdict(); d["policy"] = policy; d["execution"] = "SKIPPED_BUSY"
            skip_rows.append(d)
    E = pd.DataFrame(exec_rows)
    S = pd.DataFrame(skip_rows)
    return U, E, S


def policy_row(policy, U, E, S):
    raw = summarize_df(U)
    seq = summarize_df(E)
    row = {
        "policy": policy,
        "raw_opportunities": len(U),
        "executed_trades": len(E),
        "skipped_busy": len(S),
        "skip_rate": len(S)/len(U) if len(U) else np.nan,
        "raw_wr": raw.get("win_rate", np.nan),
        "raw_net": raw.get("net_pnl", np.nan),
        "raw_exp": raw.get("expectancy", np.nan),
        "raw_pf": raw.get("pf", np.nan),
        "raw_dd": raw.get("max_dd", np.nan),
        "raw_loss_streak": raw.get("max_loss_streak", 0),
        "seq_wr": seq.get("win_rate", np.nan),
        "seq_net": seq.get("net_pnl", np.nan),
        "seq_exp": seq.get("expectancy", np.nan),
        "seq_pf": seq.get("pf", np.nan),
        "seq_dd": seq.get("max_dd", np.nan),
        "seq_loss_streak": seq.get("max_loss_streak", 0),
        "seq_win_streak": seq.get("max_win_streak", 0),
        "avg_hold_h": E.hold_min.mean()/60 if len(E) else np.nan,
        "median_hold_h": E.hold_min.median()/60 if len(E) else np.nan,
    }
    for y in YEARS:
        Y = E[pd.DatetimeIndex(E.entry_ts).year == y] if len(E) else E
        ys = summarize_df(Y)
        row[f"y{y}_n"] = len(Y)
        row[f"y{y}_wr"] = ys.get("win_rate", np.nan)
        row[f"y{y}_net"] = ys.get("net_pnl", np.nan)
        row[f"y{y}_exp"] = ys.get("expectancy", np.nan)
        row[f"y{y}_pf"] = ys.get("pf", np.nan)
    return row


def hour_summary(policy, U, E, S):
    rows = []
    for h in range(24):
        a = U[U.source_hour_wib == h]
        e = E[E.source_hour_wib == h] if len(E) else E
        s = S[S.source_hour_wib == h] if len(S) else S
        if len(a) == 0 and policy == "FORMAL_PASS_ONLY" and h not in PASS_HOURS:
            continue
        ss = summarize_df(e)
        rows.append({
            "policy":policy,"hour_wib":h,"experiment":MAP[h][0],"formal_status":MAP[h][1],
            "rule":MAP[h][2],"lookback_min":MAP[h][3],"hold_min":MAP[h][4],
            "raw_opportunities":len(a),"executed":len(e),"skipped":len(s),
            "execution_rate":len(e)/len(a) if len(a) else np.nan,
            "executed_wr":ss.get("win_rate",np.nan),"executed_net":ss.get("net_pnl",np.nan),
            "executed_exp":ss.get("expectancy",np.nan),"executed_pf":ss.get("pf",np.nan),
        })
    return pd.DataFrame(rows)


def main():
    base.synthetic_tests()
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"coverage too low {coverage}")
    T = build_opportunities(x5)
    if len(T) == 0:
        raise RuntimeError("no opportunities built")
    T.to_csv(OUT_OPPS, index=False)

    summaries, hours, ledgers = [], [], []
    for policy in ("FORMAL_PASS_ONLY","ALL_HOURLY_REPRESENTATIVES"):
        U,E,S = sequentialize(T, policy)
        summaries.append(policy_row(policy,U,E,S))
        hours.append(hour_summary(policy,U,E,S))
        if len(E): ledgers.append(E)
    PS = pd.DataFrame(summaries)
    HS = pd.concat(hours, ignore_index=True)
    ET = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    PS.to_csv(OUT_SUM,index=False)
    HS.to_csv(OUT_HOUR,index=False)
    ET.to_csv(OUT_TRADES,index=False)

    lines = [
        "# ETH E13C — E12 Native-Hold One-Position Sequential Audit Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Development only; OOS remained closed.",
        "No TP/SL/profit-floor discovery. Every source hour retained its frozen E12 rule, lookback, and fixed hold.","",
        "## Policy summary","",
        "| Policy | Raw opps | Executed | Busy-skipped | Skip rate | Raw WR | Seq WR | Raw net | Seq net | Seq exp | Seq PF | Raw DD | Seq DD | Raw LS | Seq LS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in PS.itertuples(index=False):
        lines.append(f"| {r.policy} | {r.raw_opportunities} | {r.executed_trades} | {r.skipped_busy} | {pct(r.skip_rate)} | {pct(r.raw_wr)} | {pct(r.seq_wr)} | {money(r.raw_net)} | {money(r.seq_net)} | {money(r.seq_exp)} | {r.seq_pf:.3f} | {money(r.raw_dd)} | {money(r.seq_dd)} | {int(r.raw_loss_streak)} | {int(r.seq_loss_streak)} |")
    lines += ["","## Sequential cross-era readout",""]
    for r in PS.itertuples(index=False):
        lines += [f"### {r.policy}",""]
        for y in YEARS:
            lines.append(f"- {y}: N **{int(getattr(r,f'y{y}_n'))}**, WR **{pct(getattr(r,f'y{y}_wr'))}**, net **{money(getattr(r,f'y{y}_net'))}**, exp **{money(getattr(r,f'y{y}_exp'))}**, PF **{float(getattr(r,f'y{y}_pf')):.3f}**")
        lines += [f"- avg native hold among executed trades: **{r.avg_hold_h:.2f}h**; median **{r.median_hold_h:.2f}h**",""]

    lines += ["## Executed-trade source hours",""]
    for policy in ("FORMAL_PASS_ONLY","ALL_HOURLY_REPRESENTATIVES"):
        lines += [f"### {policy}","","| WIB | E12 | Formal | Hold | Raw opps | Executed | Skipped | Exec rate | WR | Net |","|---:|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        Z=HS[HS.policy==policy]
        for r in Z.itertuples(index=False):
            lines.append(f"| {int(r.hour_wib):02d} | {r.experiment} | {r.formal_status} | {int(r.hold_min)}m | {int(r.raw_opportunities)} | {int(r.executed)} | {int(r.skipped)} | {pct(r.execution_rate)} | {pct(r.executed_wr)} | {money(r.executed_net)} |")
        lines.append("")

    status="ETH_E13C_NATIVE_HOLD_SEQUENTIAL_AUDIT_COMPLETE"
    OUT_STATUS.write_text(status+"\n")
    lines += ["## Status","",f"**{status}**","","This audit changes execution accounting only. It does not promote FAIL-hour characters and does not authorize live trading."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())

if __name__ == "__main__":
    main()
