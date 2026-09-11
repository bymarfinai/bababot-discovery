#!/usr/bin/env python3
from __future__ import annotations

from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd

import eth_e13c_e12_native_hold_sequential as e13c

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E13D_WINNER_HOUR_SELECTION"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_HOURS = ROOT / f"{PFX}_HourContribution.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

KEY_TO_HOUR = {"K":23, "L":0, "M":1, "O":3}
YEARS = (2022, 2023, 2024)
BASE = dict(n=476, wr=.5525, net=622.52, exp=1.31, pf=1.351, dd=131.02, ls=6)


def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"

def subset_names():
    ks = tuple(KEY_TO_HOUR)
    return ["+".join(c) for r in range(1, len(ks)+1) for c in combinations(ks, r)]

def seq_subset(P: pd.DataFrame, name: str):
    enabled = {KEY_TO_HOUR[k] for k in name.split("+")}
    U = P[P.source_hour_wib.isin(enabled)].copy().sort_values(["entry_ts","source_hour_wib","clock_utc_min"]).reset_index(drop=True)
    exe, skip = [], []
    busy_until = None
    for r in U.itertuples(index=False):
        d = r._asdict(); d["subset"] = name
        if busy_until is None or r.entry_ts >= busy_until:
            d["execution"] = "EXECUTED"; exe.append(d); busy_until = r.exit_ts
        else:
            d["execution"] = "SKIPPED_BUSY"; skip.append(d)
    return U, pd.DataFrame(exe), pd.DataFrame(skip)

def summarize(T):
    return e13c.summarize_df(T)

def candidate_row(name, U, E, S):
    ss = summarize(E)
    row = {
        "subset": name, "enabled_hours": len(name.split("+")),
        "raw_opportunities": len(U), "executed_trades": len(E), "skipped_busy": len(S),
        "skip_rate": len(S)/len(U) if len(U) else np.nan,
        "win_rate": ss.get("win_rate",np.nan), "net_pnl": ss.get("net_pnl",np.nan),
        "expectancy": ss.get("expectancy",np.nan), "pf": ss.get("pf",np.nan),
        "max_dd": ss.get("max_dd",np.nan), "max_loss_streak": ss.get("max_loss_streak",0),
        "max_win_streak": ss.get("max_win_streak",0),
    }
    min_exp = np.inf; years55 = 0; era = True
    for y in YEARS:
        Y = E[pd.DatetimeIndex(E.entry_ts).year == y] if len(E) else E
        ys = summarize(Y)
        n = len(Y); wr=ys.get("win_rate",np.nan); net=ys.get("net_pnl",np.nan); exp=ys.get("expectancy",np.nan); pf=ys.get("pf",np.nan)
        row.update({f"y{y}_n":n,f"y{y}_wr":wr,f"y{y}_net":net,f"y{y}_exp":exp,f"y{y}_pf":pf})
        ok = bool(n>=40 and np.isfinite(wr) and wr>=.52 and net>0 and np.isfinite(exp) and exp>0 and np.isfinite(pf) and pf>=1.05)
        era &= ok
        years55 += int(np.isfinite(wr) and wr>=.55)
        min_exp = min(min_exp, exp if np.isfinite(exp) else -np.inf)
    row["years_wr55"] = years55; row["min_year_exp"] = float(min_exp)
    pooled = bool(
        row["executed_trades"]>=160 and np.isfinite(row["win_rate"]) and row["win_rate"]>=.55 and
        row["net_pnl"]>0 and np.isfinite(row["expectancy"]) and row["expectancy"]>=.50 and
        np.isfinite(row["pf"]) and row["pf"]>=1.20 and np.isfinite(row["max_dd"]) and row["max_dd"]<=BASE["dd"]+1e-9 and
        row["max_loss_streak"]<=BASE["ls"]
    )
    row["pooled_gate"] = pooled
    row["era_gate"] = bool(era and years55>=2)
    row["robust"] = bool(row["pooled_gate"] and row["era_gate"])
    pareto_floor = bool(
        row["robust"] and row["win_rate"]>=BASE["wr"]-1e-12 and row["net_pnl"]>=BASE["net"]-1e-9 and
        row["expectancy"]>=BASE["exp"]-1e-12 and row["pf"]>=BASE["pf"]-1e-12 and
        row["max_dd"]<=BASE["dd"]+1e-9 and row["max_loss_streak"]<=BASE["ls"]
    )
    improved = bool(
        row["win_rate"]>BASE["wr"]+5e-5 or row["net_pnl"]>BASE["net"]+.005 or row["expectancy"]>BASE["exp"]+.005 or
        row["pf"]>BASE["pf"]+.0005 or row["max_dd"]<BASE["dd"]-.005 or row["max_loss_streak"]<BASE["ls"]
    )
    row["strict_pareto_improver"] = bool(pareto_floor and improved)
    return row

def hour_rows(name, U, E, S):
    out=[]
    for key in name.split("+"):
        h=KEY_TO_HOUR[key]; A=U[U.source_hour_wib==h]; X=E[E.source_hour_wib==h] if len(E) else E; Q=S[S.source_hour_wib==h] if len(S) else S
        ss=summarize(X)
        out.append({"subset":name,"key":key,"hour_wib":h,"experiment":e13c.MAP[h][0],"hold_min":e13c.MAP[h][4],
                    "raw_opportunities":len(A),"executed":len(X),"skipped":len(Q),"execution_rate":len(X)/len(A) if len(A) else np.nan,
                    "win_rate":ss.get("win_rate",np.nan),"net_pnl":ss.get("net_pnl",np.nan),"expectancy":ss.get("expectancy",np.nan),"pf":ss.get("pf",np.nan)})
    return out

def main():
    e13c.base.synthetic_tests()
    x5, coverage = e13c.base.load5("ETHUSDT")
    if coverage < .995: raise RuntimeError(f"coverage too low {coverage}")
    allop = e13c.build_opportunities(x5)
    P = allop[allop.source_hour_wib.isin(set(KEY_TO_HOUR.values()))].copy()
    if len(P) != 1027: raise AssertionError(f"expected 1027 formal-pass opportunities from E13C, got {len(P)}")

    rows=[]; hrs=[]; ledgers={}
    for name in subset_names():
        U,E,S=seq_subset(P,name)
        rows.append(candidate_row(name,U,E,S)); hrs += hour_rows(name,U,E,S); ledgers[name]=E
    D=pd.DataFrame(rows)
    if len(D)!=15: raise AssertionError(f"expected 15 subsets, got {len(D)}")
    R=D[D.robust].copy().sort_values(
        ["min_year_exp","years_wr55","expectancy","pf","win_rate","max_dd","max_loss_streak","net_pnl","executed_trades","enabled_hours","subset"],
        ascending=[False,False,False,False,False,True,True,False,False,True,True]
    ).reset_index(drop=True)
    R["rank"] = np.arange(1,len(R)+1)
    D.to_csv(OUT_GRID,index=False); R.to_csv(OUT_LEADER,index=False); pd.DataFrame(hrs).to_csv(OUT_HOURS,index=False)

    selected = None
    if len(R):
        selected = R.iloc[0]
        ledgers[selected["subset"]].to_csv(OUT_TRADES,index=False)

    lines=["# ETH E13D — Winner-Hour Sequential Selection Result","",f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
           "Development only; OOS remained closed.","No TP/SL/early-exit changes. E12 K/L/M/O rules, lookbacks and native holds remained frozen.","",
           "## All 15 static winner-hour subsets","",
           "| Subset | Hrs | N | WR | Net | Exp | PF | DD | LS | 2022 WR/Exp | 2023 | 2024 | Robust | Pareto |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in D.sort_values(["robust","min_year_exp","expectancy","pf"],ascending=[False,False,False,False]).itertuples(index=False):
        lines.append(f"| {r.subset} | {int(r.enabled_hours)} | {int(r.executed_trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.y2022_wr)}/{money(r.y2022_exp)} | {pct(r.y2023_wr)}/{money(r.y2023_exp)} | {pct(r.y2024_wr)}/{money(r.y2024_exp)} | {'YES' if r.robust else 'NO'} | {'YES' if r.strict_pareto_improver else 'NO'} |")

    lines += ["","## E13C reference baseline","",f"N **{BASE['n']}**, WR **{pct(BASE['wr'])}**, net **{money(BASE['net'])}**, exp **{money(BASE['exp'])}**, PF **{BASE['pf']:.3f}**, DD **{money(BASE['dd'])}**, LS **{BASE['ls']}**.",""]
    if selected is None:
        status="ETH_E13D_NO_ROBUST_SUBSET"
        lines += ["## Verdict","",f"**{status}**","","No static subset passed the frozen pooled + era robustness gates. E13C K+L+M+O remains the reference execution baseline."]
    else:
        s=selected; status="ETH_E13D_ROBUST_SUBSET_FOUND"
        lines += ["## Development-selected robust subset","",f"**{s['subset']}**", "",
                  f"N **{int(s['executed_trades'])}**, WR **{pct(s['win_rate'])}**, net **{money(s['net_pnl'])}**, exp **{money(s['expectancy'])}**, PF **{float(s['pf']):.3f}**, DD **{money(s['max_dd'])}**, LS **{int(s['max_loss_streak'])}**.",
                  f"Minimum yearly expectancy **{money(s['min_year_exp'])}**; years WR>=55% **{int(s['years_wr55'])}/3**; strict Pareto vs E13C: **{'YES' if bool(s['strict_pareto_improver']) else 'NO'}**.","",
                  "### Cross-era",""]
        for y in YEARS:
            lines.append(f"- {y}: N **{int(s[f'y{y}_n'])}**, WR **{pct(s[f'y{y}_wr'])}**, net **{money(s[f'y{y}_net'])}**, exp **{money(s[f'y{y}_exp'])}**, PF **{float(s[f'y{y}_pf']):.3f}**")
        lines += ["","### Selected-subset hour contribution","","| Key | WIB | Hold | Raw | Executed | Skip | WR | Net | Exp | PF |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        H=pd.DataFrame(hrs); H=H[H.subset==s['subset']]
        for r in H.itertuples(index=False):
            lines.append(f"| {r.key} | {int(r.hour_wib):02d} | {int(r.hold_min)}m | {int(r.raw_opportunities)} | {int(r.executed)} | {int(r.skipped)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} |")
        lines += ["","## Verdict","",f"**{status}**"]
    lines += ["","Research/shadow only. No OOS exposure and no live authorization."]
    OUT_STATUS.write_text(status+"\n"); OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__ == "__main__": main()
