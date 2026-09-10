#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import itertools
import numpy as np
import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_z6_money_geometry as econ

ROOT = Path(__file__).resolve().parent.parent
PFX = "ETH_DISCOVERY2_Z7_CHECKPOINT_HARVEST"
OUT_GRID = ROOT / f"{PFX}_DevelopmentGrid.csv"
OUT_TRADES = ROOT / f"{PFX}_SelectedTrades.csv"
OUT_SUMMARY = ROOT / f"{PFX}_SelectedSummary.csv"
OUT_RESULT = ROOT / f"{PFX}_Result.md"
OUT_STATUS = ROOT / f"{PFX}_Status.txt"

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.75
COHORTS = ("F95", "F90")
SLS = (0.20, 0.30)
HOLDS = (120, 240)
MODE_ORDER = {
    "FULL_C30": 0,
    "FULL_C40": 1,
    "P50_C20_C40_BE": 2,
    "P50_C20_C50_BE": 3,
    "P50_C30_C50_BE": 4,
}
MODE_SPECS = {
    "FULL_C30": {"kind":"full", "target":0.30},
    "FULL_C40": {"kind":"full", "target":0.40},
    "P50_C20_C40_BE": {"kind":"partial", "first":0.20, "runner":0.40},
    "P50_C20_C50_BE": {"kind":"partial", "first":0.20, "runner":0.50},
    "P50_C30_C50_BE": {"kind":"partial", "first":0.30, "runner":0.50},
}
PARTS = ("development", "external", "reference_validation")


def fast_slice(x, a, z):
    return base.fast_slice(x, a, z)


def slice_pnl(notional, entry, exit_price):
    return float(notional) * (float(exit_price) / float(entry) - 1.0)


def simulate_trade(x5: pd.DataFrame, r, mode: str, sl_r: float, hold_min: int):
    spec = MODE_SPECS[mode]
    ep = float(r.entry_price)
    H = float(r.H)
    R = float(r.R)
    initial_sl = ep - float(sl_r) * R
    deadline = min(pd.Timestamp(r.execution_end), pd.Timestamp(r.entry_ts) + pd.Timedelta(minutes=int(hold_min)))
    path = fast_slice(x5, pd.Timestamp(r.eval_start), deadline)
    if len(path) == 0:
        return None

    gross = 0.0
    remaining = NOTIONAL
    partial_done = False
    be_active = False
    exit_ts = pd.NaT
    final_exit_price = np.nan
    reason = ""

    if spec["kind"] == "full":
        target = H + float(spec["target"]) * R
        for ts,b in path.iterrows():
            hi,lo = float(b.high),float(b.low)
            if lo <= initial_sl and hi >= target:
                gross += slice_pnl(remaining, ep, initial_sl)
                remaining = 0.0; reason="INITIAL_SL"; final_exit_price=initial_sl; exit_ts=ts+BAR5; break
            if lo <= initial_sl:
                gross += slice_pnl(remaining, ep, initial_sl)
                remaining = 0.0; reason="INITIAL_SL"; final_exit_price=initial_sl; exit_ts=ts+BAR5; break
            if hi >= target:
                gross += slice_pnl(remaining, ep, target)
                remaining = 0.0; reason="FULL_TARGET"; final_exit_price=target; exit_ts=ts+BAR5; break
        if remaining > 0:
            last_ts=path.index[-1]; px=float(path.iloc[-1].close)
            gross += slice_pnl(remaining,ep,px)
            remaining=0.0; reason="TIMEOUT"; final_exit_price=px; exit_ts=last_ts+BAR5
    else:
        first = H + float(spec["first"]) * R
        runner = H + float(spec["runner"]) * R
        half = NOTIONAL * 0.5
        for ts,b in path.iterrows():
            hi,lo=float(b.high),float(b.low)
            current_stop = ep if be_active else initial_sl
            if lo <= current_stop:
                # Conservative ordering: active stop wins against any same-bar target.
                gross += slice_pnl(remaining,ep,current_stop)
                remaining=0.0
                reason="PARTIAL_BE" if partial_done and be_active else "INITIAL_SL"
                final_exit_price=current_stop; exit_ts=ts+BAR5
                break

            if not partial_done and hi >= first:
                gross += slice_pnl(half,ep,first)
                remaining -= half
                partial_done=True
                if hi >= runner:
                    gross += slice_pnl(remaining,ep,runner)
                    remaining=0.0; reason="PARTIAL_RUNNER"; final_exit_price=runner; exit_ts=ts+BAR5
                    break
                # BE activates only after this bar completes; next iteration sees it.
                be_active=True
                continue

            if partial_done and hi >= runner:
                gross += slice_pnl(remaining,ep,runner)
                remaining=0.0; reason="PARTIAL_RUNNER"; final_exit_price=runner; exit_ts=ts+BAR5
                break

        if remaining > 0:
            last_ts=path.index[-1]; px=float(path.iloc[-1].close)
            gross += slice_pnl(remaining,ep,px)
            remaining=0.0
            reason="TIMEOUT_AFTER_PARTIAL" if partial_done else "TIMEOUT"
            final_exit_price=px; exit_ts=last_ts+BAR5

    if pd.isna(exit_ts):
        raise AssertionError("missing exit_ts")
    if pd.Timestamp(exit_ts) > deadline:
        raise AssertionError("exit after deadline")
    net = gross - FEE
    return {
        "cohort":r.cohort,
        "session_id":r.session_id,
        "partition":r.partition,
        "entry_ts":r.entry_ts,
        "entry_price":ep,
        "R":R,
        "mode":mode,
        "sl_r":sl_r,
        "hold_min":hold_min,
        "exit_ts":exit_ts,
        "exit_price":final_exit_price,
        "reason":reason,
        "gross_pnl":gross,
        "fee":FEE,
        "net_pnl":net,
        "net_positive":bool(net>0),
        "hold_minutes":float((pd.Timestamp(exit_ts)-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1)),
    }


def run_config(x5,E,cohort,part,mode,sl_r,hold_min):
    q=E[(E.cohort==cohort)&(E.partition==part)]
    rows=[]
    for r in q.itertuples(index=False):
        t=simulate_trade(x5,r,mode,sl_r,hold_min)
        if t is not None: rows.append(t)
    return pd.DataFrame(rows)


def summarize(T,blocks=0):
    if T is None or len(T)==0: return None
    T=T.sort_values(["entry_ts","session_id"]).reset_index(drop=True)
    pnls=T.net_pnl.to_numpy(float)
    ml,mw=econ.streaks(pnls)
    out={
        "trades":len(T),
        "win_rate":float((T.net_pnl>0).mean()),
        "gross_pnl":float(T.gross_pnl.sum()),
        "fees":float(T.fee.sum()),
        "net_pnl":float(T.net_pnl.sum()),
        "expectancy":float(T.net_pnl.mean()),
        "pf":float(econ.profit_factor(pnls)),
        "max_dd":float(econ.max_drawdown(pnls)),
        "max_loss_streak":int(ml),
        "max_win_streak":int(mw),
        "avg_hold_min":float(T.hold_minutes.mean()),
        "net_per_100_trades":float(T.net_pnl.mean()*100.0),
    }
    for reason in ("FULL_TARGET","INITIAL_SL","PARTIAL_RUNNER","PARTIAL_BE","TIMEOUT_AFTER_PARTIAL","TIMEOUT"):
        out[reason.lower()] = int((T.reason==reason).sum())
    if blocks:
        chunks=np.array_split(np.arange(len(T)),blocks)
        vals=[float(T.iloc[idx].net_pnl.sum()) if len(idx) else 0.0 for idx in chunks]
        out["block_pnls"]=vals
        out["positive_blocks"]=int(sum(v>0 for v in vals))
    return out


def development_grid(x5,E):
    rows=[]
    for cohort,mode,sl_r,hold in itertools.product(COHORTS,MODE_SPECS.keys(),SLS,HOLDS):
        T=run_config(x5,E,cohort,"development",mode,sl_r,hold)
        s=summarize(T,blocks=4)
        if s is None: continue
        rows.append({
            "cohort":cohort,"mode":mode,"sl_r":sl_r,"hold_min":hold,
            **{k:v for k,v in s.items() if k!="block_pnls"},
            "block1":s["block_pnls"][0],"block2":s["block_pnls"][1],
            "block3":s["block_pnls"][2],"block4":s["block_pnls"][3],
        })
    return pd.DataFrame(rows)


def select_dev(G):
    q=G[(G.trades>=35)&(G.net_pnl>0)&(G.expectancy>0)&(G.pf>=1.20)&(G.max_dd<=35.0)&(G.positive_blocks>=3)].copy()
    if len(q)==0: return None,q
    q["mode_tie"]=q["mode"].map(MODE_ORDER)
    q["cohort_tie"]=q.cohort.map({"F95":0,"F90":1})
    q=q.sort_values(
        ["net_pnl","pf","max_dd","win_rate","max_loss_streak","hold_min","sl_r","mode_tie","cohort_tie"],
        ascending=[False,False,True,False,True,True,True,True,True]
    ).reset_index(drop=True)
    return q.iloc[0].to_dict(),q


def replicate(x5,E,sel):
    if sel is None: return pd.DataFrame(),False
    rows=[]; holdouts=[]; all_ok=True
    for part in ("external","reference_validation"):
        T=run_config(x5,E,sel["cohort"],part,sel["mode"],float(sel["sl_r"]),int(sel["hold_min"]))
        s=summarize(T)
        ok=s is not None and s["trades"]>=15 and s["net_pnl"]>0 and s["expectancy"]>0 and s["pf"]>=1.05
        all_ok=all_ok and bool(ok)
        rows.append({"partition":part,**(s or {}),"passed":bool(ok)})
        if T is not None and len(T): holdouts.append(T)
    pooled_ok=False
    if holdouts:
        P=pd.concat(holdouts,ignore_index=True)
        ps=summarize(P)
        pooled_ok=ps["net_pnl"]>0 and ps["pf"]>=1.15
        rows.append({"partition":"POOLED_HOLDOUT",**ps,"passed":bool(pooled_ok)})
    return pd.DataFrame(rows),bool(all_ok and pooled_ok)


def money(x): return f"${float(x):.2f}"
def pct(x): return f"{100*float(x):.2f}%"


def main():
    x5,coverage=base.load5("ETHUSDT")
    if coverage<.995: raise RuntimeError(f"coverage too low {coverage}")
    E=econ.build_parent_entries(x5)
    G=development_grid(x5,E)
    G.to_csv(OUT_GRID,index=False)
    sel,eligible=select_dev(G)
    H,supported=replicate(x5,E,sel)
    if sel is None:
        status="ETH_DISCOVERY2_Z7_NO_DEV_CANDIDATE"; ST=pd.DataFrame()
    else:
        tt=[]
        for part in PARTS:
            T=run_config(x5,E,sel["cohort"],part,sel["mode"],float(sel["sl_r"]),int(sel["hold_min"]))
            if len(T): tt.append(T)
        ST=pd.concat(tt,ignore_index=True) if tt else pd.DataFrame()
        status="ETH_DISCOVERY2_Z7_SUPPORTED" if supported else "ETH_DISCOVERY2_Z7_CANDIDATE_NOT_REPLICATED"
    OUT_STATUS.write_text(status+"\n")
    if len(ST): ST.to_csv(OUT_TRADES,index=False)
    if len(H): H.to_csv(OUT_SUMMARY,index=False)

    lines=["# ETH Discovery 2 — Z7 Checkpoint-Harvest Result","",f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",f"Frozen Development family: {len(G)} configurations.",""]
    if sel is None:
        lines.append("No configuration passed the preregistered Development gate.")
    else:
        lines += ["## Development winner","",f"**{sel['cohort']} / {sel['mode']} / initial SL {float(sel['sl_r']):.2f}R / hold {int(sel['hold_min'])}m**","",
            f"- Trades {int(sel['trades'])}; WR **{pct(sel['win_rate'])}**.",
            f"- Net **{money(sel['net_pnl'])}**; expectancy **{money(sel['expectancy'])}/trade**; net/100 **{money(sel['net_per_100_trades'])}**.",
            f"- PF **{float(sel['pf']):.3f}**; max DD **{money(sel['max_dd'])}**; loss streak **{int(sel['max_loss_streak'])}**; win streak **{int(sel['max_win_streak'])}**.",
            f"- Positive blocks {int(sel['positive_blocks'])}/4: [{money(sel['block1'])}, {money(sel['block2'])}, {money(sel['block3'])}, {money(sel['block4'])}].",
            f"- Outcomes: full_target={int(sel['full_target'])}, initial_sl={int(sel['initial_sl'])}, partial_runner={int(sel['partial_runner'])}, partial_be={int(sel['partial_be'])}, timeout_after_partial={int(sel['timeout_after_partial'])}, timeout={int(sel['timeout'])}.",
            "","## Historical replication","","| Partition | Trades | WR | Net | Exp | PF | DD | Loss streak | Pass |","|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for _,r in H.iterrows():
            lines.append(f"| {r['partition']} | {int(r['trades'])} | {pct(r['win_rate'])} | {money(r['net_pnl'])} | {money(r['expectancy'])} | {float(r['pf']):.3f} | {money(r['max_dd'])} | {int(r['max_loss_streak'])} | {'PASS' if bool(r['passed']) else 'FAIL'} |")
        alls=summarize(ST)
        lines += ["","## Combined all historical partitions — descriptive only","",f"- Trades {alls['trades']}; WR **{pct(alls['win_rate'])}**; net **{money(alls['net_pnl'])}**; expectancy **{money(alls['expectancy'])}/trade**; PF **{alls['pf']:.3f}**; max DD **{money(alls['max_dd'])}**; loss streak **{alls['max_loss_streak']}**.","","## BTC A3.9 context","","BTC preferred consistency reference: 139 trades, 56.83% WR, +$95.734 net, $0.6887/trade expectancy, PF 1.431, $31.636 max DD, loss streak 4.","","## Top Development candidates","","| # | Cohort | Mode | SL R | Hold | WR | Net | PF | DD | Pos blocks |","|---:|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for i,r in eligible.head(12).iterrows():
            lines.append(f"| {i+1} | {r.cohort} | {r['mode']} | {r.sl_r:.2f} | {int(r.hold_min)} | {pct(r.win_rate)} | {money(r.net_pnl)} | {r.pf:.3f} | {money(r.max_dd)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","Research/shadow only. No live promotion."]
    OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(OUT_RESULT.read_text())


if __name__=="__main__":
    main()
