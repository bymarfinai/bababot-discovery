#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e12a_long_13_14wib_character as e12a
import eth_e13a_one_position_long_22_04wib as e13a

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_E13C_SOURCE_SUBSET_LONG_22_04WIB"
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
TARGET_NET_PCT = 0.010
TARGET_NET_USD = NOTIONAL * TARGET_NET_PCT
MAX_HOLD = 2160

SOURCE_MAP = {
    "K": "E12K_23_00_FORMAL",
    "L": "E12L_00_01_FORMAL",
    "M": "E12M_01_02_FORMAL",
    "O": "E12O_03_04_FORMAL",
}
SUBSETS = tuple(
    combo for n in range(1, len(SOURCE_MAP)+1)
    for combo in combinations(SOURCE_MAP.keys(), n)
)


def pct(x): return "nan" if not np.isfinite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not np.isfinite(x) else f"${float(x):+.2f}"


def candidate(x5: pd.DataFrame, Eall: pd.DataFrame, subset):
    pa, pz = base.PARTS["development"]
    names = [SOURCE_MAP[k] for k in subset]
    E = Eall[Eall.source.isin(names)].copy()
    E = E[(E.pre_ts >= pa) & (E.entry_ts >= pa) &
          ((E.entry_ts + pd.Timedelta(minutes=MAX_HOLD)) <= pz)].copy()
    E = E.sort_values(["entry_ts","clock_utc_min","source"]).reset_index(drop=True)

    close = x5.close.to_numpy(float)
    idx = x5.index
    max_bars = MAX_HOLD // BAR_MIN
    busy_until = pd.Timestamp.min.tz_localize("UTC")
    accepted=[]; skipped=0

    for r in E.itertuples(index=False):
        ent=pd.Timestamp(r.entry_ts)
        if ent < busy_until:
            skipped += 1; continue
        ei=int(r.entry_ix); ep=float(r.entry_price)
        last_j=ei+max_bars-1
        if last_j >= len(x5): continue
        if idx[last_j] != ent + pd.Timedelta(minutes=MAX_HOLD-BAR_MIN): continue
        exit_j=None; exit_gross=None; exit_net=None; reason="TIMEOUT"
        for k in range(max_bars):
            j=ei+k; cp=float(close[j])
            gross=NOTIONAL*((cp-ep)/ep); net=gross-FEE
            if net >= TARGET_NET_USD:
                exit_j=j; exit_gross=gross; exit_net=net; reason="TARGET"; break
        if exit_j is None:
            exit_j=last_j; cp=float(close[exit_j])
            exit_gross=NOTIONAL*((cp-ep)/ep); exit_net=exit_gross-FEE
        else:
            cp=float(close[exit_j])
        exit_ts=idx[exit_j]+pd.Timedelta(minutes=BAR_MIN)
        busy_until=exit_ts
        accepted.append({
            "subset":"".join(subset), "source_count":len(subset),
            "entry_ts":ent,"exit_ts":exit_ts,"duration_min":int((exit_ts-ent).total_seconds()//60),
            "entry_price":ep,"exit_price":cp,"source":r.source,"character_rule":r.character_rule,
            "lookback_min":int(r.lookback_min),"clock_utc_min":int(r.clock_utc_min),
            "gross_pnl":float(exit_gross),"fee":FEE,"net_pnl":float(exit_net),
            "exit_reason":reason,"net_positive":bool(exit_net>0),
        })

    T=pd.DataFrame(accepted)
    if len(T):
        T=T.sort_values("entry_ts").reset_index(drop=True)
        s=e12a.summarize(T.net_pnl.to_numpy(float),T.gross_pnl.to_numpy(float))
        d=T.duration_min.to_numpy(float); tm=T.exit_reason.eq("TIMEOUT")
        timeout_rate=float(tm.mean()); timeout_mean=float(T.loc[tm,"net_pnl"].mean()) if tm.any() else np.nan
        dm=float(np.mean(d)); dmed=float(np.median(d)); d75=float(np.quantile(d,.75)); d90=float(np.quantile(d,.90))
    else:
        s=e12a.summarize(np.array([]),np.array([])); timeout_rate=timeout_mean=dm=dmed=d75=d90=np.nan

    row={"subset":"".join(subset),"source_count":len(subset),"candidate_signals":len(E),"accepted_trades":len(T),
         "busy_skips":skipped,"acceptance_rate":len(T)/len(E) if len(E) else np.nan,**s,
         "timeout_rate":timeout_rate,"timeout_mean_pnl":timeout_mean,
         "duration_mean_min":dm,"duration_median_min":dmed,"duration_p75_min":d75,"duration_p90_min":d90}
    for key,name in SOURCE_MAP.items():
        row[f"accepted_{key}"]=int((T.source==name).sum()) if len(T) else 0

    era_ok=True; years70=0; minexp=np.inf
    for y in YEARS:
        if len(T):
            Ty=T.loc[pd.DatetimeIndex(T.entry_ts).year==y]
            ys=e12a.summarize(Ty.net_pnl.to_numpy(float),Ty.gross_pnl.to_numpy(float))
        else: ys=e12a.summarize(np.array([]),np.array([]))
        row.update({f"y{y}_trades":int(ys["trades"]),f"y{y}_wr":ys["win_rate"],f"y{y}_net":ys["net_pnl"],f"y{y}_exp":ys["expectancy"],f"y{y}_pf":ys["pf"]})
        ok=bool(ys["trades"]>=40 and np.isfinite(ys["win_rate"]) and ys["win_rate"]>=.65 and ys["net_pnl"]>0 and
                np.isfinite(ys["expectancy"]) and ys["expectancy"]>0 and np.isfinite(ys["pf"]) and ys["pf"]>=1.15)
        era_ok &= ok; years70 += int(np.isfinite(ys["win_rate"]) and ys["win_rate"]>=.70)
        minexp=min(minexp,ys["expectancy"] if np.isfinite(ys["expectancy"]) else -np.inf)
    row["years_wr70"]=years70; row["min_year_exp"]=float(minexp)
    row["pooled_gate"]=bool(row["accepted_trades"]>=150 and np.isfinite(row["win_rate"]) and row["win_rate"]>=.70 and
        row["net_pnl"]>0 and np.isfinite(row["expectancy"]) and row["expectancy"]>=.50 and np.isfinite(row["pf"]) and row["pf"]>=1.30 and
        row["max_dd"]<=125 and row["max_loss_streak"]<=6 and np.isfinite(row["timeout_rate"]) and row["timeout_rate"]<=.30)
    row["era_gate"]=bool(era_ok and years70>=2); row["candidate_gate"]=bool(row["pooled_gate"] and row["era_gate"])
    return row,T


def main():
    base.synthetic_tests(); x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    Eall=e13a.build_all_events(x5)
    rows=[]; ledgers={}
    for subset in SUBSETS:
        row,T=candidate(x5,Eall,subset); rows.append(row); ledgers["".join(subset)]=T
    D=pd.DataFrame(rows)
    if len(D)!=15: raise AssertionError(f"expected 15 subsets, got {len(D)}")
    D.to_csv(OUT_GRID,index=False)
    C=D[D.candidate_gate].copy()
    if len(C):
        C=C.sort_values(["min_year_exp","source_count","max_dd","pf","expectancy","win_rate","timeout_rate","duration_p90_min","subset"],
                        ascending=[False,False,True,False,False,False,True,True,True]).reset_index(drop=True)
        C["dev_rank"]=np.arange(1,len(C)+1)
    C.to_csv(OUT_LEADER,index=False)

    lines=["# ETH E13C — Sequential LONG Source-Subset Discovery Result","",
           f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
           "Development only; OOS remained closed.",
           "Frozen exit: net floor **1.00% = $5.00** at completed 5m close; max hold **2160m / 36h**.",
           "Sources: all 15 non-empty subsets of E12 formal K/L/M/O hour characters.",
           f"Formal passers: **{len(C)} / 15**.","",
           "| Subset | Sources | Trades | WR | Net | Exp | PF | DD | LS | Timeout | MedDur | 2022 WR/Exp/PF | 2023 | 2024 | Pooled | Era | Full |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    for r in D.sort_values(["source_count","subset"]).itertuples(index=False):
        lines.append(f"| {r.subset} | {int(r.source_count)} | {int(r.accepted_trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.timeout_rate)} | {r.duration_median_min:.0f}m | {pct(r.y2022_wr)}/{money(r.y2022_exp)}/{float(r.y2022_pf):.3f} | {pct(r.y2023_wr)}/{money(r.y2023_exp)}/{float(r.y2023_pf):.3f} | {pct(r.y2024_wr)}/{money(r.y2024_exp)}/{float(r.y2024_pf):.3f} | {'YES' if r.pooled_gate else 'NO'} | {'YES' if r.era_gate else 'NO'} | {'YES' if r.candidate_gate else 'NO'} |")

    if len(C)==0:
        status="ETH_E13C_NO_SOURCE_SUBSET_PASSER"; OUT_STATUS.write_text(status+"\n")
        lines += ["",f"**Status: {status}**","","No source subset passed unchanged E13B gates at the frozen 1.00% / 36h exit coordinate. No rescue and no OOS exposure.","","Research/shadow only."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]; T=ledgers[sel["subset"]].copy(); T.to_csv(OUT_TRADES,index=False)
    B=T.groupby("source",as_index=False).agg(trades=("net_pnl","size"),wins=("net_positive","sum"),net_pnl=("net_pnl","sum"),expectancy=("net_pnl","mean"),median_duration_min=("duration_min","median"),timeout_trades=("exit_reason",lambda s:int((s=="TIMEOUT").sum())))
    B["win_rate"]=B.wins/B.trades; B["timeout_rate"]=B.timeout_trades/B.trades; B.to_csv(OUT_BREAKDOWN,index=False)
    status="ETH_E13C_SOURCE_SUBSET_PASSER_FOUND"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Development-selected source subset","",f"**{sel['subset']} ({int(sel['source_count'])} sources)**","",
              f"N **{int(sel['accepted_trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, LS **{int(sel['max_loss_streak'])}**, timeout **{pct(sel['timeout_rate'])}**, median duration **{float(sel['duration_median_min']):.0f}m**.","",
              "### Cross-era","",f"- 2022: N {int(sel['y2022_trades'])}, WR {pct(sel['y2022_wr'])}, exp {money(sel['y2022_exp'])}, PF {float(sel['y2022_pf']):.3f}",f"- 2023: N {int(sel['y2023_trades'])}, WR {pct(sel['y2023_wr'])}, exp {money(sel['y2023_exp'])}, PF {float(sel['y2023_pf']):.3f}",f"- 2024: N {int(sel['y2024_trades'])}, WR {pct(sel['y2024_wr'])}, exp {money(sel['y2024_exp'])}, PF {float(sel['y2024_pf']):.3f}","",
              "### Source breakdown","","| Source | Trades | WR | Net | Exp | Timeout | Median duration |","|---|---:|---:|---:|---:|---:|---:|"]
    for r in B.itertuples(index=False): lines.append(f"| {r.source} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {pct(r.timeout_rate)} | {float(r.median_duration_min):.0f}m |")
    lines += ["",f"**Status: {status}**","","Development execution discovery only. OOS remains closed; no live promotion."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
