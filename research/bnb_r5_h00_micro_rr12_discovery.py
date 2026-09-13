#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e11_market_state_character as e11
import eth_economic_first_e12a_long_13_14wib_character as engine

ROOT = Path(__file__).resolve().parent.parent
PFX = "BNB_R5_H00_MICRO_RR12"
OUT_GRID = ROOT / f"{PFX}_DEVELOPMENT_GRID.csv"
OUT_ELIGIBLE = ROOT / f"{PFX}_DEVELOPMENT_ELIGIBLE.csv"
OUT_SELECTED = ROOT / f"{PFX}_SELECTED.csv"
OUT_2025 = ROOT / f"{PFX}_2025_HOLDOUT.csv"
OUT_ANCHORS = ROOT / f"{PFX}_ANCHOR_ATLAS.csv"
OUT_RESULT = ROOT / f"{PFX}_RESULT.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

DEV_START = pd.Timestamp("2022-01-01", tz="UTC")
DEV_END = pd.Timestamp("2025-01-01", tz="UTC")
HOLD_START = DEV_END
HOLD_END = pd.Timestamp("2026-01-01", tz="UTC")
CLOCKS = (1020, 1035, 1050, 1065)  # 17:00..17:45 UTC = 00:00..00:45 WIB
LOOKBACKS = (15, 30, 60, 120, 240, 360)
MAX_HOLDS = (15, 30, 60, 90, 120)
DIRECTIONS = ("LONG", "SHORT")
RULES = tuple(engine.RULES)
TP_PCT = 0.0030
SL_PCT = 0.0015
NOTIONAL = 500.0
FEE = 0.75
SLIPPAGE_BPS = (0, 2, 5, 10)
BAR_MIN = 5


def finite(x): return bool(np.isfinite(x))
def pct(x): return "nan" if not finite(x) else f"{100*float(x):.2f}%"
def money(x): return "nan" if not finite(x) else f"${float(x):+.2f}"
def hhmm(m): return f"{(int(m)//60)%24:02d}:{int(m)%60:02d}"
def wib(m):
    x=(int(m)+420)%1440
    return hhmm(x)


def stats(net, gross):
    return engine.summarize(np.asarray(net,float), np.asarray(gross,float))


def first_touch_arrays(x5: pd.DataFrame, S: pd.DataFrame, max_hold: int, direction: str):
    idx = pd.DatetimeIndex(x5.index)
    op = x5.open.to_numpy(float)
    hi = x5.high.to_numpy(float)
    lo = x5.low.to_numpy(float)
    ei = S.entry_ix.to_numpy(int)
    ent = pd.DatetimeIndex(S.entry_ts)
    ex = ent + pd.Timedelta(minutes=max_hold)
    xi = idx.get_indexer(ex)
    valid = (ei >= 0) & (xi >= 0) & ((xi - ei) == max_hold // BAR_MIN)

    outcome = np.full(len(S), "INVALID", dtype=object)
    gross = np.full(len(S), np.nan, float)
    exit_price = np.full(len(S), np.nan, float)
    bars_used = np.full(len(S), np.nan, float)
    ep = S.entry_price.to_numpy(float)
    dsign = 1.0 if direction == "LONG" else -1.0

    for i in np.flatnonzero(valid):
        e = float(ep[i])
        if direction == "LONG":
            tp = e * (1.0 + TP_PCT)
            sl = e * (1.0 - SL_PCT)
        else:
            tp = e * (1.0 - TP_PCT)
            sl = e * (1.0 + SL_PCT)

        resolved = False
        # Scan completed 5m bars from the entry bar up to, but not including, the max-hold exit bar.
        for k in range(int(ei[i]), int(xi[i])):
            if direction == "LONG":
                hit_tp = hi[k] >= tp
                hit_sl = lo[k] <= sl
            else:
                hit_tp = lo[k] <= tp
                hit_sl = hi[k] >= sl

            # Conservative intrabar ambiguity rule: SL wins ties.
            if hit_sl:
                outcome[i] = "SL"
                exit_price[i] = sl
                gross[i] = -NOTIONAL * SL_PCT
                bars_used[i] = k - int(ei[i]) + 1
                resolved = True
                break
            if hit_tp:
                outcome[i] = "TP"
                exit_price[i] = tp
                gross[i] = NOTIONAL * TP_PCT
                bars_used[i] = k - int(ei[i]) + 1
                resolved = True
                break

        if not resolved:
            xp = float(op[int(xi[i])])
            outcome[i] = "TIMEOUT"
            exit_price[i] = xp
            gross[i] = NOTIONAL * dsign * ((xp - e) / e)
            bars_used[i] = max_hold // BAR_MIN

    return {
        "entry_ts": ent, "exit_ts": ex, "valid": valid, "outcome": outcome,
        "gross": gross, "exit_price": exit_price, "bars_used": bars_used,
    }


def period_metrics(T: pd.DataFrame, bps: int = 0):
    if T.empty:
        s=stats([],[])
        return {**s,"tp_first_rate":np.nan,"sl_first_rate":np.nan,"timeout_rate":np.nan,
                "tp_n":0,"sl_n":0,"timeout_n":0,"avg_minutes":np.nan}
    cost = FEE + NOTIONAL * (2.0 * bps / 10000.0)
    gross = T.gross.to_numpy(float)
    net = gross - cost
    s = stats(net, gross)
    out = T.outcome.astype(str)
    return {
        **s,
        "tp_first_rate":float((out=="TP").mean()),
        "sl_first_rate":float((out=="SL").mean()),
        "timeout_rate":float((out=="TIMEOUT").mean()),
        "tp_n":int((out=="TP").sum()),"sl_n":int((out=="SL").sum()),"timeout_n":int((out=="TIMEOUT").sum()),
        "avg_minutes":float(T.bars_used.mean()*BAR_MIN),
    }


def build_event_cache(x5):
    cache={}
    for lb in LOOKBACKS:
        for clock in CLOCKS:
            S=e11.state_frame(x5,clock,lb)
            masks=engine.masks_for_frame(S)
            for hold in MAX_HOLDS:
                for direction in DIRECTIONS:
                    O=first_touch_arrays(x5,S,hold,direction)
                    cache[(clock,lb,hold,direction)] = (S,masks,O)
    return cache


def events_for_cell(cache, lb:int, hold:int, direction:str, rule:str, start, end):
    frames=[]
    for clock in CLOCKS:
        S,masks,O=cache[(clock,lb,hold,direction)]
        ent=pd.DatetimeIndex(O["entry_ts"])
        ex=pd.DatetimeIndex(O["exit_ts"])
        m=np.asarray(O["valid"],bool) & (ent>=start) & (ex<end) & np.asarray(masks[rule],bool)
        if not m.any():
            continue
        frames.append(pd.DataFrame({
            "entry_ts":ent[m],"exit_ts":ex[m],"clock":clock,"clock_wib":wib(clock),
            "outcome":np.asarray(O["outcome"],object)[m],"gross":np.asarray(O["gross"],float)[m],
            "bars_used":np.asarray(O["bars_used"],float)[m],
        }))
    if not frames:
        return pd.DataFrame(columns=["entry_ts","exit_ts","clock","clock_wib","outcome","gross","bars_used"])
    return pd.concat(frames,ignore_index=True).sort_values(["entry_ts","clock"]).reset_index(drop=True)


def score_development(cache, lb, hold, direction, rule):
    T=events_for_cell(cache,lb,hold,direction,rule,DEV_START,DEV_END)
    pooled=period_metrics(T,0)
    pooled2=period_metrics(T,2)
    row={
        "lookback_min":lb,"max_hold_min":hold,"direction":direction,"character_rule":rule,
        "trades":int(pooled["trades"]),"tp_first_rate":pooled["tp_first_rate"],"net_win_rate":pooled["win_rate"],
        "net_pnl":pooled["net_pnl"],"expectancy":pooled["expectancy"],"pf":pooled["pf"],"max_dd":pooled["max_dd"],
        "max_loss_streak":int(pooled["max_loss_streak"]),"timeout_rate":pooled["timeout_rate"],"avg_minutes":pooled["avg_minutes"],
        "exp_2bps":pooled2["expectancy"],"pf_2bps":pooled2["pf"],"net_2bps":pooled2["net_pnl"],
    }
    annual_tp=[]; annual_net_positive=[]
    for y in (2022,2023,2024):
        Y=T[pd.DatetimeIndex(T.entry_ts).year==y].copy() if len(T) else T.copy()
        ys=period_metrics(Y,0)
        row.update({
            f"y{y}_n":int(ys["trades"]),f"y{y}_tp_rate":ys["tp_first_rate"],f"y{y}_net_wr":ys["win_rate"],
            f"y{y}_net":ys["net_pnl"],f"y{y}_exp":ys["expectancy"],f"y{y}_pf":ys["pf"],
        })
        annual_tp.append(ys["tp_first_rate"] if finite(ys["tp_first_rate"]) else -np.inf)
        annual_net_positive.append(bool(ys["net_pnl"]>0 and finite(ys["expectancy"]) and ys["expectancy"]>0))
    row["min_annual_tp_rate"]=float(min(annual_tp))

    anchor_good=0
    for clock in CLOCKS:
        A=T[T.clock==clock].copy() if len(T) else T.copy()
        a=period_metrics(A,0)
        good=bool(a["trades"]>=25 and finite(a["tp_first_rate"]) and a["tp_first_rate"]>=.65)
        anchor_good += int(good)
        row.update({f"a{clock}_n":int(a["trades"]),f"a{clock}_tp_rate":a["tp_first_rate"],f"a{clock}_good":good})
    row["good_anchors"]=anchor_good

    eligible=bool(
        row["trades"]>=150
        and all(row[f"y{y}_n"]>=40 for y in (2022,2023,2024))
        and finite(row["tp_first_rate"]) and row["tp_first_rate"]>=.70
        and finite(row["min_annual_tp_rate"]) and row["min_annual_tp_rate"]>=.65
        and all(annual_net_positive)
        and row["net_pnl"]>0 and finite(row["expectancy"]) and row["expectancy"]>0
        and finite(row["pf"]) and row["pf"]>=1.20
        and finite(row["max_dd"]) and row["max_dd"]<=160.0
        and anchor_good>=3
    )
    target=bool(
        eligible
        and row["tp_first_rate"]>=.80
        and row["min_annual_tp_rate"]>=.75
        and finite(row["exp_2bps"]) and row["exp_2bps"]>0
        and finite(row["pf_2bps"]) and row["pf_2bps"]>=1.15
    )
    row["eligible"]=eligible
    row["high_wr_target_hit"]=target
    return row


def score_2025(cache, sel):
    T=events_for_cell(cache,int(sel.lookback_min),int(sel.max_hold_min),str(sel.direction),str(sel.character_rule),HOLD_START,HOLD_END)
    rows=[]
    for bps in SLIPPAGE_BPS:
        s=period_metrics(T,bps)
        rows.append({
            "period":"2025","slippage_bps_per_side":bps,"trades":int(s["trades"]),
            "tp_first_rate":s["tp_first_rate"],"net_win_rate":s["win_rate"],"net_pnl":s["net_pnl"],
            "expectancy":s["expectancy"],"pf":s["pf"],"max_dd":s["max_dd"],
            "max_loss_streak":int(s["max_loss_streak"]),"timeout_rate":s["timeout_rate"],"avg_minutes":s["avg_minutes"],
        })
    atlas=[]
    for clock in CLOCKS:
        A=T[T.clock==clock].copy() if len(T) else T.copy()
        s=period_metrics(A,0)
        atlas.append({"clock_utc":hhmm(clock),"clock_wib":wib(clock),"trades":int(s["trades"]),
                      "tp_first_rate":s["tp_first_rate"],"net_pnl":s["net_pnl"],"expectancy":s["expectancy"],"pf":s["pf"]})
    return pd.DataFrame(rows), pd.DataFrame(atlas)


def main():
    if len(RULES)!=90: raise AssertionError(f"expected 90 rules, got {len(RULES)}")
    base.synthetic_tests()
    x5,coverage=base.load5("BNBUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low: {coverage}")
    idx=pd.DatetimeIndex(pd.to_datetime(x5.index,utc=True))
    if idx.max()<pd.Timestamp("2025-12-31 23:55:00",tz="UTC"):
        raise RuntimeError(f"2025 incomplete: {idx.max()}")
    # Hard-close 2026 before feature construction.
    x=x5[idx<HOLD_END].copy()
    cache=build_event_cache(x)

    rows=[]
    for lb in LOOKBACKS:
        for hold in MAX_HOLDS:
            for direction in DIRECTIONS:
                for rule in RULES:
                    rows.append(score_development(cache,lb,hold,direction,rule))
    D=pd.DataFrame(rows)
    if len(D)!=5400: raise AssertionError(f"expected 5400 cells, got {len(D)}")
    D.to_csv(OUT_GRID,index=False)

    E=D[D.eligible].copy()
    if not E.empty:
        E["dir_tie"]=E.direction.map({"LONG":0,"SHORT":1})
        E=E.sort_values(
            ["high_wr_target_hit","min_annual_tp_rate","tp_first_rate","trades","exp_2bps","expectancy","pf","max_dd","max_hold_min","lookback_min","character_rule","dir_tie"],
            ascending=[False,False,False,False,False,False,False,True,True,True,True,True],kind="mergesort"
        ).reset_index(drop=True)
        E["rank"]=np.arange(1,len(E)+1)
    E.to_csv(OUT_ELIGIBLE,index=False)

    # If no eligible cell exists, still report the strongest sample-qualified near miss without changing gates.
    if E.empty:
        Q=D[(D.trades>=150)&(D.y2022_n>=40)&(D.y2023_n>=40)&(D.y2024_n>=40)].copy()
        if Q.empty:
            status="BNB_R5_H00_NO_EVALUABLE_MICRO_CHARACTER"
            OUT_STATUS.write_text(status+"\n")
            OUT_RESULT.write_text(f"# BNB R5 H00 Micro RR1:2\n\n**Status: {status}**\n\nNo sample-qualified cell. 2026 remained closed.\n")
            return
        Q=Q.sort_values(["min_annual_tp_rate","tp_first_rate","trades","expectancy","pf"],ascending=[False,False,False,False,False]).reset_index(drop=True)
        sel=Q.iloc[0]
        selection_class="SAMPLE_QUALIFIED_NEAR_MISS"
    else:
        sel=E.iloc[0]
        selection_class="HIGH_WR_TARGET" if bool(sel.high_wr_target_hit) else "ELIGIBLE_NEAR_MISS"

    pd.DataFrame([sel]).to_csv(OUT_SELECTED,index=False)
    H,A=score_2025(cache,sel)
    H.to_csv(OUT_2025,index=False); A.to_csv(OUT_ANCHORS,index=False)
    h0=H[H.slippage_bps_per_side==0].iloc[0]
    h2=H[H.slippage_bps_per_side==2].iloc[0]

    dev_target=bool(sel.high_wr_target_hit) if "high_wr_target_hit" in sel.index else False
    continuation=bool(
        int(h0.trades)>=40 and finite(h0.tp_first_rate) and float(h0.tp_first_rate)>=.70
        and float(h0.net_pnl)>0 and finite(h0.expectancy) and float(h0.expectancy)>0
        and finite(h0.pf) and float(h0.pf)>=1.10
        and float(h2.net_pnl)>0 and finite(h2.expectancy) and float(h2.expectancy)>0
    )
    status=("BNB_R5_H00_HIGH_WR_MICRO_CHARACTER_FOUND" if dev_target and continuation
            else "BNB_R5_H00_MICRO_CHARACTER_NEAR_MISS" if continuation
            else "BNB_R5_H00_MICRO_CHARACTER_NOT_SUPPORTED")
    OUT_STATUS.write_text(status+"\n")

    lines=[
        "# BNB R5 — H00 Micro RR 1:2 Character Discovery","",
        "**TP +0.30% / SL -0.15%. First-touch scoring. 2022–2024 selection only; 2025 historical holdout diagnostic; 2026 CLOSED.**","",
        f"Coverage: **{coverage:.4%}**. Search cells: **{len(D):,}**. Eligible cells: **{len(E):,}**. High-WR target cells: **{int(D.high_wr_target_hit.sum()):,}**.",
        f"Selection class: **{selection_class}**.","",
        "## Development-selected cell","",
        f"**{sel.direction} / {sel.character_rule} / LB{int(sel.lookback_min)} / max hold {int(sel.max_hold_min)}m**","",
        f"2022–2024 N **{int(sel.trades)}**, TP-first **{pct(sel.tp_first_rate)}**, net WR **{pct(sel.net_win_rate)}**, Net **{money(sel.net_pnl)}**, Exp **{money(sel.expectancy)}/trade**, PF **{float(sel.pf):.3f}**, DD **{money(sel.max_dd)}**.",
        f"2bps/side: Net **{money(sel.net_2bps)}**, Exp **{money(sel.exp_2bps)}**, PF **{float(sel.pf_2bps):.3f}**.",
        f"Annual TP-first: 2022 **{pct(sel.y2022_tp_rate)}** (N {int(sel.y2022_n)}), 2023 **{pct(sel.y2023_tp_rate)}** (N {int(sel.y2023_n)}), 2024 **{pct(sel.y2024_tp_rate)}** (N {int(sel.y2024_n)}).", "",
        "## 2025 historical holdout diagnostic","",
        "| Slip/side | N | TP-first | Net WR | Net | Exp | PF | DD | LS | Timeout | Avg min |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in H.itertuples(index=False):
        lines.append(f"| {int(r.slippage_bps_per_side)} bps | {int(r.trades)} | {pct(r.tp_first_rate)} | {pct(r.net_win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.timeout_rate)} | {float(r.avg_minutes):.1f} |")
    lines += ["","## 2025 anchor atlas","","| WIB | N | TP-first | Net | Exp | PF |","|---:|---:|---:|---:|---:|---:|"]
    for r in A.itertuples(index=False):
        lines.append(f"| {r.clock_wib} | {int(r.trades)} | {pct(r.tp_first_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} |")
    lines += ["",f"**Status: {status}**","",
              "Same-bar TP/SL ambiguity is always scored as SL-first. No gate relaxation was performed.",
              "The search remains weekday-only for comparability with the inherited causal character engine.",
              "2026 was not used anywhere in this experiment.","","Research/shadow only."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())

if __name__=="__main__": main()
