#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_economic_first_e3_drive_strength_fast as e3

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_ECONOMIC_FIRST_E5_E2_STRENGTH_BANDS"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_LEADER = ROOT / f"{PFX}_DevelopmentLeaderboard.csv"
OUT_SUMMARY = ROOT / f"{PFX}_HoldoutSummary.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

CLOCK = 17 * 60
LOOKBACK = 360
HOLD = 720
NOTIONAL = 500.0
FEE = 0.75
BANDS = (
    ("B0_20", 0.00, 0.20, False),
    ("B20_40", 0.20, 0.40, False),
    ("B40_60", 0.40, 0.60, False),
    ("B60_80", 0.60, 0.80, False),
    ("B80_100", 0.80, 1.00, True),
)
MODES = ("MOMENTUM", "REVERSAL")


def money(x): return f"${float(x):+.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def band_mask(strength, lo, hi, inclusive_hi):
    if inclusive_hi:
        return (strength >= lo) & (strength <= hi)
    return (strength >= lo) & (strength < hi)


def base_arrays(x5, S, part):
    ent = pd.DatetimeIndex(S.entry_ts)
    pre = pd.DatetimeIndex(S.pre_ts)
    strength = S.strength_pct.to_numpy(float)
    ex, valid, xp, delta, sign = e3.hold_base(x5, S, HOLD)
    pa, pz = base.PARTS[part]
    partmask = valid & (pre >= pa) & (ent >= pa) & (ex < pz) & np.isfinite(strength)
    return ent, pre, strength, ex, xp, delta, sign, partmask


def pnl_arrays(delta, sign, mode):
    direction = sign if mode == "MOMENTUM" else -sign
    gross = NOTIONAL * direction * delta
    net = gross - FEE
    return direction, gross, net


def scan_dev(x5, S):
    _, _, strength, _, _, delta, sign, pm = base_arrays(x5, S, "development")
    rows=[]
    for ordinal,(name,lo,hi,inc_hi) in enumerate(BANDS):
        bm = band_mask(strength,lo,hi,inc_hi)
        for mode in MODES:
            _,gross,net=pnl_arrays(delta,sign,mode)
            m=pm & bm
            s=e3.summarize(net[m],gross[m],4)
            rows.append({
                "clock_utc":"17:00","clock_wib":"00:00","lookback_min":LOOKBACK,"hold_min":HOLD,
                "band":name,"band_ordinal":ordinal,"band_lo":lo,"band_hi":hi,"mode":mode,**s
            })
    D=pd.DataFrame(rows)
    if len(D)!=10: raise AssertionError(f"expected 10 candidates, got {len(D)}")
    D["candidate_gate"]=(
        (D.trades>=100)&(D.win_rate>=.52)&(D.net_pnl>0)&(D.expectancy>=.50)&
        (D.pf>=1.15)&(D.max_dd<=120)&(D.max_loss_streak<=8)&(D.positive_blocks>=3)
    )
    D["mode_tie"]=D["mode"].map({"MOMENTUM":0,"REVERSAL":1})
    C=D[D.candidate_gate].copy().sort_values(
        ["net_per_100","win_rate","pf","max_dd","max_loss_streak","trades","band_ordinal","mode_tie"],
        ascending=[False,False,False,True,True,False,True,True]
    ).reset_index(drop=True)
    C["dev_rank"]=np.arange(1,len(C)+1)
    return D,C


def unfiltered_summary(x5,S,part,mode="MOMENTUM"):
    _,_,_,_,_,delta,sign,pm=base_arrays(x5,S,part)
    _,gross,net=pnl_arrays(delta,sign,mode)
    return e3.summarize(net[pm],gross[pm],4 if part=="development" else 0)


def selected_trade_df(x5,S,part,sel):
    ent,pre,strength,ex,xp,delta,sign,pm=base_arrays(x5,S,part)
    name=str(sel["band"]); lo=float(sel["band_lo"]); hi=float(sel["band_hi"])
    inc_hi=(name=="B80_100")
    bm=band_mask(strength,lo,hi,inc_hi)
    direction,gross,net=pnl_arrays(delta,sign,str(sel["mode"]))
    m=pm & bm
    return pd.DataFrame({
        "partition":part,"clock_utc":"17:00","clock_wib":"00:00","lookback_min":LOOKBACK,"hold_min":HOLD,
        "band":name,"band_lo":lo,"band_hi":hi,"mode":str(sel["mode"]),
        "pre_ts":pre[m],"entry_ts":ent[m],"exit_ts":ex[m],
        "pre_price":S.pre_price.to_numpy(float)[m],"entry_price":S.entry_price.to_numpy(float)[m],"exit_price":xp[m],
        "drive_return":S.drive_return.to_numpy(float)[m],"strength_pct":strength[m],
        "trade_side":np.where(direction[m]>0,"LONG","SHORT"),"gross_pnl":gross[m],"fee":FEE,
        "net_pnl":net[m],"net_positive":net[m]>0,
    })


def main():
    base.synthetic_tests()
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    S=e3.signal_frame(x5,CLOCK,LOOKBACK)
    unf=unfiltered_summary(x5,S,"development","MOMENTUM")
    D,C=scan_dev(x5,S)
    D.to_csv(OUT_GRID,index=False); C.to_csv(OUT_LEADER,index=False)

    lines=[
        "# ETH Economic-First E5 — E2 Strength-Band Regime Map Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen E2 anchor: **17:00 UTC / LB360 / hold720**. Only causal strength band and response mode vary.",
        f"Direct unfiltered MOMENTUM reproduction: N **{int(unf['trades'])}**, WR **{pct(unf['win_rate'])}**, net **{money(unf['net_pnl'])}**, exp **{money(unf['expectancy'])}/trade**, PF **{unf['pf']:.3f}**, DD **{money(unf['max_dd'])}**.","",
        "## Development strength-band atlas","",
        "| Band | Mode | N | WR | Net | Exp | PF | DD | L-streak | Blocks | Gate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in D.sort_values(["band_ordinal","mode_tie"]).itertuples(index=False):
        lines.append(f"| {r.band} | {r.mode} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.positive_blocks)}/4 | {'PASS' if r.candidate_gate else 'FAIL'} |")

    if len(C)==0:
        status="ETH_ECONOMIC_FIRST_E5_NO_DEV_CANDIDATE"; OUT_STATUS.write_text(status+"\n")
        lines += ["",f"**Status: {status}**","","No band-response candidate met the preregistered economic + WR gate. No holdouts opened.","","Research/shadow only. No live promotion or profit guarantee."]
        OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text()); return

    sel=C.iloc[0]
    lines += ["","## Development-selected regime","",
              f"**{sel['band']} / {sel['mode']}**: N **{int(sel['trades'])}**, WR **{pct(sel['win_rate'])}**, net **{money(sel['net_pnl'])}**, exp **{money(sel['expectancy'])}/trade**, PF **{float(sel['pf']):.3f}**, DD **{money(sel['max_dd'])}**, loss streak **{int(sel['max_loss_streak'])}**, blocks **{int(sel['positive_blocks'])}/4**."]
    Tdev=selected_trade_df(x5,S,"development",sel)
    hrows=[]; tlist=[Tdev]; allok=True
    for part in ("external","reference_validation"):
        T=selected_trade_df(x5,S,part,sel)
        s=e3.summarize(T.net_pnl.to_numpy(float),T.gross_pnl.to_numpy(float),0)
        ok=(s.get("trades",0)>=50 and s.get("win_rate",0)>=.505 and s.get("net_pnl",-1)>0 and s.get("expectancy",-1)>0 and s.get("pf",0)>=1.05 and s.get("max_loss_streak",99)<=10)
        hrows.append({"partition":part,**s,"replication_pass":bool(ok)}); allok &= bool(ok); tlist.append(T)
    H=pd.DataFrame(hrows); H.to_csv(OUT_SUMMARY,index=False); pd.concat(tlist,ignore_index=True).to_csv(OUT_TRADES,index=False)
    status="ETH_ECONOMIC_FIRST_E5_SUPPORTED" if allok else "ETH_ECONOMIC_FIRST_E5_CANDIDATE_NOT_REPLICATED"; OUT_STATUS.write_text(status+"\n")
    lines += ["","## Historical replication","","| Partition | N | WR | Net | Exp | PF | DD | L-streak | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in H.itertuples(index=False):
        lines.append(f"| {r.partition} | {int(r.trades)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {money(r.expectancy)} | {float(r.pf):.3f} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {'PASS' if r.replication_pass else 'FAIL'} |")
    allT=pd.concat(tlist,ignore_index=True).sort_values("entry_ts")
    sa=e3.summarize(allT.net_pnl.to_numpy(float),allT.gross_pnl.to_numpy(float),0)
    lines += ["","## Combined historical — descriptive","",
              f"N **{sa['trades']}**, WR **{pct(sa['win_rate'])}**, net **{money(sa['net_pnl'])}**, exp **{money(sa['expectancy'])}/trade**, PF **{sa['pf']:.3f}**, DD **{money(sa['max_dd'])}**, loss streak **{sa['max_loss_streak']}**.","",f"**Status: {status}**","","Research/shadow only. No live promotion or profit guarantee."]
    OUT_RESULT.write_text("\n".join(lines)+"\n"); print(OUT_RESULT.read_text())

if __name__=="__main__": main()
