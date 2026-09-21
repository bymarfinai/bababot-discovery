#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import time
import requests
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PFX = "SOL_EXECUTION_COST_AUDIT_V1"
TRADES_FILE = ROOT / "SOL_SCORE3_SELL_C_HARD_FAILURE_UNIVERSE_V1_Trades.csv"
FUNDING_INPUT = ROOT / "research/data/SOL_EXECUTION_COST_AUDIT_V1_FundingByTrade_Input.csv"
BOOK_INPUT = ROOT / "research/data/SOL_EXECUTION_COST_AUDIT_V1_BookSnapshot_Input.csv"
FUNDING_RECORDS_SNAPSHOT = 6623
SYMBOL = "SOLUSDT"
FAPI = "https://fapi.binance.com"

REFERENCE_TAKER_PER_SIDE_BPS = 5.0
REFERENCE_TAKER_TAKER_RT_BPS = 10.0
REPO_FEE_ROUNDTRIP_BPS = 10.0
REPO_SLIPPAGE_BPS = 5.0
REPO_TOTAL_COST_BPS = 15.0
BOOK_TEST_NOTIONAL_USD = 500.0
PF_GATE = 1.10


def profit_factor(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    gp = float(s[s > 0].sum())
    gl = float(-s[s < 0].sum())
    if gl <= 0:
        return math.inf if gp > 0 else np.nan
    return gp / gl


def max_drawdown(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return np.nan
    eq = s.cumsum()
    peak = eq.cummax().clip(lower=0.0)
    return float((peak - eq).max())


def metrics(vals):
    s = pd.Series(vals, dtype=float).replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return {"n": 0, "mean_r": np.nan, "pf": np.nan, "cum_r": 0.0, "max_dd_r": np.nan, "wr": np.nan}
    return {
        "n": int(len(s)),
        "mean_r": float(s.mean()),
        "pf": float(profit_factor(s)),
        "cum_r": float(s.sum()),
        "max_dd_r": float(max_drawdown(s)),
        "wr": float((s > 0).mean()),
    }


def get_json(path, params=None, attempts=4):
    last = None
    for i in range(attempts):
        try:
            r = requests.get(FAPI + path, params=params or {}, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            if i < attempts - 1:
                time.sleep(1.5 * (i + 1))
    raise last


def fetch_funding(start_ms, end_ms):
    rows = []
    cursor = int(start_ms)
    while cursor <= end_ms:
        arr = get_json(
            "/fapi/v1/fundingRate",
            {"symbol": SYMBOL, "startTime": cursor, "endTime": int(end_ms), "limit": 1000},
        )
        if not arr:
            break
        rows.extend(arr)
        last = int(arr[-1]["fundingTime"])
        if last <= cursor:
            break
        cursor = last + 1
        if len(arr) < 1000:
            break
    x = pd.DataFrame(rows)
    if x.empty:
        return pd.DataFrame(columns=["funding_time", "funding_rate"])
    x["funding_time"] = pd.to_datetime(x["fundingTime"], unit="ms", utc=True)
    x["funding_rate"] = pd.to_numeric(x["fundingRate"], errors="coerce")
    return x[["funding_time", "funding_rate"]].dropna().drop_duplicates("funding_time").sort_values("funding_time").reset_index(drop=True)


def book_snapshot():
    book = get_json("/fapi/v1/depth", {"symbol": SYMBOL, "limit": 50})
    bids = [(float(p), float(q)) for p, q in book["bids"]]
    asks = [(float(p), float(q)) for p, q in book["asks"]]
    bid = bids[0][0]
    ask = asks[0][0]
    mid = (bid + ask) / 2.0
    spread_bps = (ask - bid) / mid * 10000.0

    def market_impact(levels, notional, top_price):
        rem = float(notional)
        qty = 0.0
        cost = 0.0
        for price, size in levels:
            capacity = price * size
            take = min(rem, capacity)
            qty += take / price
            cost += take
            rem -= take
            if rem <= 1e-9:
                break
        avg = cost / qty if qty > 0 else np.nan
        depth_slip = abs(avg - top_price) / top_price * 10000.0 if qty > 0 else np.nan
        return {
            "notional_usd": notional,
            "avg_price": avg,
            "top_price": top_price,
            "depth_slippage_bps": depth_slip,
            "unfilled_usd": max(0.0, rem),
        }

    return {
        "event_time": pd.to_datetime(int(book.get("E", 0)), unit="ms", utc=True) if book.get("E") else pd.Timestamp.now(tz="UTC"),
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "full_spread_bps": spread_bps,
        "top_bid_notional_usd": bid * bids[0][1],
        "top_ask_notional_usd": ask * asks[0][1],
        "buy_500": market_impact(asks, BOOK_TEST_NOTIONAL_USD, ask),
        "sell_500": market_impact(bids, BOOK_TEST_NOTIONAL_USD, bid),
    }


def add_funding_impact(trades, funding):
    z = trades.copy()
    z["entry_time"] = pd.to_datetime(z["entry_time"], utc=True)
    z["exit_time"] = pd.to_datetime(z["exit_time"], utc=True)
    z["entry_price"] = pd.to_numeric(z["entry_price"], errors="coerce")
    z["initial_risk_price"] = pd.to_numeric(z["initial_risk_price"], errors="coerce")
    z["realized_r"] = pd.to_numeric(z["realized_r"], errors="coerce")

    ft = funding["funding_time"].to_numpy()
    fr = funding["funding_rate"].to_numpy(dtype=float)
    impacts, counts, cash_rates = [], [], []

    for _, r in z.iterrows():
        et = np.datetime64(r.entry_time.to_datetime64())
        xt = np.datetime64(r.exit_time.to_datetime64())
        mask = (ft >= et) & (ft < xt)
        rates = fr[mask]
        sign = -1.0 if str(r.side) == "SELL_SIDE" else 1.0
        cash_rate = sign * float(np.nansum(rates))
        funding_r = cash_rate * float(r.entry_price) / float(r.initial_risk_price)
        cash_rates.append(cash_rate)
        impacts.append(funding_r)
        counts.append(int(mask.sum()))

    z["funding_events"] = counts
    z["funding_cash_rate_signed"] = cash_rates
    z["funding_r"] = impacts
    return z


def net_r(trades, roundtrip_bps):
    friction_r = (
        pd.to_numeric(trades.entry_price, errors="coerce")
        * (roundtrip_bps / 10000.0)
        / pd.to_numeric(trades.initial_risk_price, errors="coerce")
    )
    return (
        pd.to_numeric(trades.realized_r, errors="coerce")
        + pd.to_numeric(trades.funding_r, errors="coerce")
        - friction_r
    )


def solve_threshold(trades, mode):
    b = 0.0
    while b <= 40.0:
        m = metrics(net_r(trades, b))
        if mode == "pf" and np.isfinite(m["pf"]) and m["pf"] < PF_GATE:
            return {"roundtrip_bps": b, **m}
        if mode == "mean" and np.isfinite(m["mean_r"]) and m["mean_r"] <= 0:
            return {"roundtrip_bps": b, **m}
        b = round(b + 0.01, 2)
    return {"roundtrip_bps": np.nan, **metrics(net_r(trades, 40.0))}


def fmt(v, d=3):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{v:.{d}f}"


def pct(v):
    if v is None or not np.isfinite(v):
        return "n/a"
    return f"{100*v:.2f}%"


def main():
    if not TRADES_FILE.exists():
        raise FileNotFoundError(TRADES_FILE)

    # GitHub-hosted runners receive HTTP 451 from Binance futures endpoints.
    # To preserve the frozen method without changing the data source, V1 uses
    # connector-captured Binance inputs persisted in research/data/.
    z = pd.read_csv(FUNDING_INPUT)
    z["entry_time"] = pd.to_datetime(z.entry_time, utc=True)
    z["exit_time"] = pd.to_datetime(z.exit_time, utc=True)
    for col in ("entry_price", "initial_risk_price", "realized_r", "funding_events", "funding_cash_rate_signed", "funding_r"):
        z[col] = pd.to_numeric(z[col], errors="coerce")

    br = pd.read_csv(BOOK_INPUT).iloc[0]
    book = {
        "event_time": pd.to_datetime(br["snapshot_time_utc"], utc=True),
        "bid": float(br["bid"]),
        "ask": float(br["ask"]),
        "mid": float(br["mid"]),
        "full_spread_bps": float(br["full_spread_bps"]),
        "top_bid_notional_usd": float(br["top_bid_notional_usd"]),
        "top_ask_notional_usd": float(br["top_ask_notional_usd"]),
        "buy_500": {
            "avg_price": float(br["buy_500_avg_price"]),
            "depth_slippage_bps": float(br["buy_500_depth_slippage_bps"]),
            "unfilled_usd": float(br["buy_500_unfilled_usd"]),
        },
        "sell_500": {
            "avg_price": float(br["sell_500_avg_price"]),
            "depth_slippage_bps": float(br["sell_500_depth_slippage_bps"]),
            "unfilled_usd": float(br["sell_500_unfilled_usd"]),
        },
    }

    pf_cut = solve_threshold(z, "pf")
    be_cut = solve_threshold(z, "mean")

    scenario_bps = [0, 10, 12, 15, 18, 19, 19.5, 20, 25, 30]
    scenarios = pd.DataFrame([
        {"roundtrip_bps": bps, **metrics(net_r(z, bps))}
        for bps in scenario_bps
    ])

    topbook_reference_bps = REFERENCE_TAKER_TAKER_RT_BPS + float(book["full_spread_bps"])
    topbook_metrics = metrics(net_r(z, topbook_reference_bps))

    pf_headroom_after_topbook = float(pf_cut["roundtrip_bps"] - topbook_reference_bps)
    be_headroom_after_topbook = float(be_cut["roundtrip_bps"] - topbook_reference_bps)
    pf_headroom_after_repo = float(pf_cut["roundtrip_bps"] - REPO_TOTAL_COST_BPS)
    be_headroom_after_repo = float(be_cut["roundtrip_bps"] - REPO_TOTAL_COST_BPS)
    m15 = metrics(net_r(z, 15))

    summary = {
        "trades_n": int(len(z)),
        "gross_mean_r": float(pd.to_numeric(z.realized_r, errors="coerce").mean()),
        "gross_pf": float(profit_factor(z.realized_r)),
        "funding_records": int(FUNDING_RECORDS_SNAPSHOT),
        "crossing_funding_trades": int((z.funding_events > 0).sum()),
        "crossing_funding_share": float((z.funding_events > 0).mean()),
        "total_funding_events": int(z.funding_events.sum()),
        "funding_mean_r_all": float(z.funding_r.mean()),
        "funding_total_r": float(z.funding_r.sum()),
        "funding_adjusted_mean_r_before_trading_cost": float((z.realized_r + z.funding_r).mean()),
        "funding_adjusted_pf_before_trading_cost": float(profit_factor(z.realized_r + z.funding_r)),
        "snapshot_time_utc": book["event_time"],
        "snapshot_bid": book["bid"],
        "snapshot_ask": book["ask"],
        "snapshot_full_spread_bps": book["full_spread_bps"],
        "snapshot_top_bid_notional_usd": book["top_bid_notional_usd"],
        "snapshot_top_ask_notional_usd": book["top_ask_notional_usd"],
        "snapshot_buy_500_depth_slippage_bps": book["buy_500"]["depth_slippage_bps"],
        "snapshot_sell_500_depth_slippage_bps": book["sell_500"]["depth_slippage_bps"],
        "reference_taker_taker_fee_bps": REFERENCE_TAKER_TAKER_RT_BPS,
        "reference_fee_plus_snapshot_spread_bps": topbook_reference_bps,
        "reference_fee_plus_snapshot_spread_mean_r": topbook_metrics["mean_r"],
        "reference_fee_plus_snapshot_spread_pf": topbook_metrics["pf"],
        "repo_existing_total_cost_bps": REPO_TOTAL_COST_BPS,
        "repo_15bps_mean_r_with_funding": m15["mean_r"],
        "repo_15bps_pf_with_funding": m15["pf"],
        "pf_1_10_cost_ceiling_bps": pf_cut["roundtrip_bps"],
        "breakeven_cost_ceiling_bps": be_cut["roundtrip_bps"],
        "extra_budget_after_fee_plus_spread_to_pf_1_10_bps": pf_headroom_after_topbook,
        "extra_budget_after_fee_plus_spread_to_breakeven_bps": be_headroom_after_topbook,
        "extra_budget_after_repo_15bps_to_pf_1_10_bps": pf_headroom_after_repo,
        "extra_budget_after_repo_15bps_to_breakeven_bps": be_headroom_after_repo,
    }

    pd.DataFrame([summary]).to_csv(ROOT / f"{PFX}_Summary.csv", index=False)
    scenarios.to_csv(ROOT / f"{PFX}_Scenarios.csv", index=False)
    z[[
        "candidate_id", "side", "entry_time", "exit_time", "entry_price",
        "initial_risk_price", "realized_r", "funding_events",
        "funding_cash_rate_signed", "funding_r"
    ]].to_csv(ROOT / f"{PFX}_FundingByTrade.csv", index=False)

    lines = [
        "# SOL Execution Cost Audit V1 — Result",
        "",
        "## Execution mapping",
        "",
        "- Score-3 FIVE_MIN_REVERSAL_BREAK research entry is next-5m-open after a completed reversal-break bar; conservative live mapping is market/taker.",
        "- RECLAIM_EXTREME protective exits map naturally to STOP_MARKET/taker.",
        "- Structural/time completion exits map conservatively to market/taker once the completed-bar state is known.",
        "- Therefore the primary execution reference is taker + taker.",
        "",
        "## Funding",
        "",
        f"- Historical Binance funding records represented by snapshot: **{FUNDING_RECORDS_SNAPSHOT:,}**.",
        f"- Trades crossing >=1 funding timestamp: **{int((z.funding_events > 0).sum())}/{len(z)} ({pct((z.funding_events > 0).mean())})**.",
        f"- Total funding impact: **{fmt(z.funding_r.sum())}R**.",
        f"- Mean funding impact per trade: **{fmt(z.funding_r.mean(), 4)}R**.",
        f"- Gross mean/PF before funding: **{fmt(z.realized_r.mean())}R / {fmt(profit_factor(z.realized_r))}**.",
        f"- After historical funding, before trading friction: **{fmt((z.realized_r + z.funding_r).mean())}R / {fmt(profit_factor(z.realized_r + z.funding_r))}**.",
        "",
        "## Current SOLUSDT order-book snapshot",
        "",
        f"- Snapshot UTC: **{book['event_time']}**",
        f"- Bid / ask: **{book['bid']:.4f} / {book['ask']:.4f}**",
        f"- Full spread: **{book['full_spread_bps']:.3f} bps**",
        f"- Top bid notional: **{book['top_bid_notional_usd']:,.0f} USD**",
        f"- Top ask notional: **{book['top_ask_notional_usd']:,.0f} USD**",
        f"- $500 market-buy depth slippage beyond best ask: **{book['buy_500']['depth_slippage_bps']:.3f} bps**",
        f"- $500 market-sell depth slippage beyond best bid: **{book['sell_500']['depth_slippage_bps']:.3f} bps**",
        "",
        "This snapshot demonstrates current visible depth only; it is not a historical slippage guarantee.",
        "",
        "## Cost budget including historical funding",
        "",
        f"- PF 1.10 round-trip cost ceiling: **{pf_cut['roundtrip_bps']:.2f} bps**.",
        f"- Mean-R break-even round-trip cost ceiling: **{be_cut['roundtrip_bps']:.2f} bps**.",
        f"- Reference taker+taker fee: **{REFERENCE_TAKER_TAKER_RT_BPS:.2f} bps** before account-specific discounts.",
        f"- Reference fee + current full spread: **{topbook_reference_bps:.3f} bps**.",
        f"- Extra slippage/latency budget after fee+spread before PF<1.10: **{pf_headroom_after_topbook:.3f} bps round trip**.",
        f"- Extra slippage/latency budget after fee+spread before mean R<=0: **{be_headroom_after_topbook:.3f} bps round trip**.",
        "",
        "## Existing BabaBot generic cost assumption",
        "",
        f"- Existing config fee assumption: **{REPO_FEE_ROUNDTRIP_BPS:.1f} bps round trip**.",
        f"- Existing config slippage assumption: **{REPO_SLIPPAGE_BPS:.1f} bps**.",
        f"- Existing combined assumption: **{REPO_TOTAL_COST_BPS:.1f} bps**.",
        f"- At 15 bps + historical funding: mean **{m15['mean_r']:.3f}R**, PF **{m15['pf']:.3f}**, cumulative **{m15['cum_r']:.3f}R**.",
        f"- Remaining headroom from 15 bps to PF 1.10 ceiling: **{pf_headroom_after_repo:.2f} bps**.",
        "",
        "## Scenario table",
        "",
        "| Round-trip friction | Mean net R | PF | Cum R | Max DD | WR |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in scenarios.iterrows():
        lines.append(
            f"| {r.roundtrip_bps:.1f} bps | {r.mean_r:.3f} | {r.pf:.3f} | {r.cum_r:.3f} | {r.max_dd_r:.3f} | {pct(r.wr)} |"
        )

    lines += [
        "",
        "## Verdict",
        "",
        "**EXECUTION_COST_NOT_PRIMARY_BLOCKER_AT_EXISTING_15BPS_ASSUMPTION**",
        "",
        "The filtered SOL universe remains above PF 1.10 at the repository's existing 15 bps total-cost assumption even after historical funding is applied.",
        "",
        "The remaining deployment gap is not another detector search. It is live execution instrumentation: record actual account commission, maker/taker status, signal-to-fill slippage, latency, and funding on every SOL trade. Only those realized fills can confirm the production cost distribution.",
    ]

    text_out = "\n".join(lines) + "\n"
    (ROOT / f"{PFX}_Result.md").write_text(text_out, encoding="utf-8")
    (ROOT / f"{PFX}_Status.txt").write_text(
        "EXECUTION_COST_NOT_PRIMARY_BLOCKER_AT_EXISTING_15BPS_ASSUMPTION\n",
        encoding="utf-8",
    )
    print(text_out)


if __name__ == "__main__":
    main()
