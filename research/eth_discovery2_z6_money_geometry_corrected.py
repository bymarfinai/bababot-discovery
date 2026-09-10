#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import eth_london_ny_liquidity_pressure_m1 as base
import eth_discovery2_z6_money_geometry as m


def main():
    x5, coverage = base.load5("ETHUSDT")
    if coverage < .995:
        raise RuntimeError(f"ETH raw 5m coverage too low: {coverage:.6f}")
    E = m.build_parent_entries(x5)
    G = m.development_grid(x5, E)
    G.to_csv(m.OUT_GRID, index=False)
    sel, eligible = m.select_dev(G)
    H, replicated = m.evaluate_selected(x5, E, sel)

    if sel is None:
        status = "ETH_DISCOVERY2_Z6_NO_DEV_CANDIDATE"
        selected_trades = pd.DataFrame()
    else:
        cohort=sel["cohort"]; tp=float(sel["tp_r"]); sl=float(sel["sl_r"]); hold=int(sel["hold_min"])
        tt=[]
        for part in m.PARTS:
            T=m.run_config(x5,E,cohort,part,tp,sl,hold)
            if len(T): tt.append(T)
        selected_trades=pd.concat(tt,ignore_index=True) if tt else pd.DataFrame()
        status = "ETH_DISCOVERY2_Z6_SUPPORTED" if replicated else "ETH_DISCOVERY2_Z6_CANDIDATE_NOT_REPLICATED"
    m.OUT_STATUS.write_text(status+"\n")
    if len(selected_trades): selected_trades.to_csv(m.OUT_TRADES,index=False)
    if len(H): H.to_csv(m.OUT_SUMMARY,index=False)

    lines=[
        "# ETH Discovery 2 — Z6 Money Geometry Result","",
        f"Raw ETHUSDT 5m coverage: **{coverage:.4%}**.",
        "Frozen parent: Z5 L06 entry. Fixed $500 notional, $0.75 round-trip cost, no compounding.",
        f"Frozen Development search: {len(G)} configurations.",""
    ]
    if sel is None:
        lines += ["No configuration passed the preregistered Development economic gate."]
    else:
        lines += ["## Development winner","",
            f"**{sel['cohort']} / TP {float(sel['tp_r']):.2f}R / SL {float(sel['sl_r']):.2f}R / hold {int(sel['hold_min'])}m**","",
            f"- Trades: {int(sel['trades'])}; TP/SL/timeout = {int(sel['tp_hits'])}/{int(sel['sl_hits'])}/{int(sel['timeouts'])}.",
            f"- Net WR: **{m.pct(sel['win_rate'])}**.",
            f"- Net PnL: **{m.fmt_money(sel['net_pnl'])}**; expectancy **{m.fmt_money(sel['expectancy'])}/trade**; net/100 trades **{m.fmt_money(sel['net_per_100_trades'])}**.",
            f"- PF: **{float(sel['pf']):.3f}**; max DD **{m.fmt_money(sel['max_dd'])}**; max loss streak **{int(sel['max_loss_streak'])}**; max win streak **{int(sel['max_win_streak'])}**.",
            f"- Positive Development blocks: {int(sel['positive_blocks'])}/4; block PnLs = [{m.fmt_money(sel['block1'])}, {m.fmt_money(sel['block2'])}, {m.fmt_money(sel['block3'])}, {m.fmt_money(sel['block4'])}].",
            "","## Historical replication","",
            "| Partition | Trades | WR | Net PnL | Exp/trade | PF | Max DD | Loss streak | Pass |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|"
        ]
        for _,r in H.iterrows():
            lines.append(
                f"| {r['partition']} | {int(r['trades'])} | {m.pct(r['win_rate'])} | {m.fmt_money(r['net_pnl'])} | "
                f"{m.fmt_money(r['expectancy'])} | {float(r['pf']):.3f} | {m.fmt_money(r['max_dd'])} | "
                f"{int(r['max_loss_streak'])} | {'PASS' if bool(r['pass']) else 'FAIL'} |"
            )
        allsum=m.summarize_trades(selected_trades)
        lines += ["","## All historical partitions combined — descriptive only","",
            f"- Trades: {allsum['trades']}.",
            f"- Net WR: **{m.pct(allsum['win_rate'])}**.",
            f"- Net PnL: **{m.fmt_money(allsum['net_pnl'])}**; expectancy **{m.fmt_money(allsum['expectancy'])}/trade**; net/100 trades **{m.fmt_money(allsum['net_per_100_trades'])}**.",
            f"- PF: **{allsum['pf']:.3f}**; max DD **{m.fmt_money(allsum['max_dd'])}**; max loss streak **{allsum['max_loss_streak']}**; max win streak **{allsum['max_win_streak']}**.",
            "","## BTC A3.9 preferred consistency context","",
            "BTC reference: 139 trades, 56.83% WR, +$95.734 net, $0.6887/trade expectancy, PF 1.431, $31.636 max DD, max loss streak 4.",
        ]
        boundary=[]
        if float(sel['tp_r']) in (min(m.TPS),max(m.TPS)): boundary.append('TP')
        if float(sel['sl_r']) in (min(m.SLS),max(m.SLS)): boundary.append('SL')
        if int(sel['hold_min']) in (min(m.HOLDS),max(m.HOLDS)): boundary.append('HOLD')
        lines += ["","## Search-boundary diagnostic","", f"Winner boundary dimensions: **{', '.join(boundary) if boundary else 'NONE'}**."]
        lines += ["","## Top Development candidates","",
            "| # | Cohort | TP R | SL R | Hold | Trades | WR | Net | PF | DD | Pos blocks |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
        ]
        for i,r in eligible.head(12).iterrows():
            lines.append(f"| {i+1} | {r.cohort} | {r.tp_r:.2f} | {r.sl_r:.2f} | {int(r.hold_min)} | {int(r.trades)} | {m.pct(r.win_rate)} | {m.fmt_money(r.net_pnl)} | {r.pf:.3f} | {m.fmt_money(r.max_dd)} | {int(r.positive_blocks)}/4 |")
    lines += ["",f"**Status: {status}**","","Research/shadow only. No live promotion."]
    m.OUT_RESULT.write_text("\n".join(lines)+"\n")
    print(m.OUT_RESULT.read_text())


if __name__ == "__main__":
    main()
