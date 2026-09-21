# SOL Execution Cost Audit V1 — Method Freeze

## Objective

Measure whether the current SOL filtered universe can realistically absorb Binance USDⓈ-M execution costs without modifying the strategy.

This audit does **not** change:
- structural detector;
- Missing-C exclusion;
- entry logic;
- stop logic;
- structural-completion exit;
- session/hour logic;
- trade selection.

## Source universe

Input trades:
`SOL_SCORE3_SELL_C_HARD_FAILURE_UNIVERSE_V1_Trades.csv`

Frozen universe:
- Score-3 BUY_SIDE: keep.
- Score-3 SELL_SIDE: keep Missing-A, Missing-B, Missing-D; reject Missing-C.
- Score-4 SELL_SIDE/LONG: keep.
- Score-4 BUY_SIDE/SHORT: excluded.

## Execution interpretation

### Entry
Score-3 `FIVE_MIN_REVERSAL_BREAK` waits for a completed 5m reversal-break bar and enters at the **next 5m open** in research.

For live implementation, exact next-bar-open price cannot be guaranteed. Conservative executable mapping is therefore a market/taker entry immediately after the confirming bar closes.

### Stops
RECLAIM_EXTREME is a protective stop. The existing live stack already supports exchange-native `STOP_MARKET` conditional exits, which are taker-like when triggered.

### Structural/time exit
The backtest exits at the next 5m open once `outcome_known_time` is reached. Conservative live mapping is a market/taker close after the required completed-bar state becomes known.

Therefore the primary reference case is **taker entry + taker exit**.

## Fee references

Two separate references are recorded and must not be conflated:

1. Existing BabaBot config assumption:
   - `fee_pct_roundtrip = 0.001` = 10 bps round trip.
   - `slippage_pct = 0.0005` = 5 bps.
   - Combined existing generic assumption = **15 bps round trip**.

2. Binance public support example for a Regular User:
   - maker = 0.02% per fill;
   - taker = 0.05% per fill.
   - Market orders are taker trades.
   - Two taker fills imply a **10 bps round-trip fee reference** before any account-specific discount.

Actual account fees are **not inferred** from public data. They must ultimately be read/logged from the authenticated production account.

## Market microstructure snapshot

At run time the script queries:
- Binance USDⓈ-M SOLUSDT order book;
- top-of-book bid/ask;
- full bid/ask spread in bps;
- simulated $500 market buy and sell against visible book depth.

This is a point-in-time liquidity snapshot only. It is not treated as a historical slippage guarantee.

## Funding

The script downloads historical SOLUSDT funding rates from Binance for the full trade period.

For each trade:
- SELL_SIDE liquidity implies a LONG trade; positive funding is a cost.
- BUY_SIDE liquidity implies a SHORT trade; positive funding is a benefit.
- Funding is applied only when the position spans a funding timestamp.

Funding impact is converted to R using:
`funding_R = signed_funding_rate * entry_price / initial_risk_price`

## Cost budget

For a round-trip friction assumption `bps`:

`net_R = realized_R + funding_R - (entry_price * bps / 10000) / initial_risk_price`

The audit solves for:
- maximum round-trip friction before PF drops below 1.10;
- maximum round-trip friction before mean net R reaches zero;
- scenario economics at 10, 12, 15, 18, 19, 19.5, 20, 25 and 30 bps;
- current top-of-book taker/taker reference = 10 bps fee + observed full spread;
- remaining extra-slippage/latency budget to PF 1.10 and to break-even.

## Decision rule

No strategy parameter is tuned from these results.

Interpretation:
- If the realistic executable cost estimate is below the PF>=1.10 cost ceiling with a meaningful buffer, execution cost is **not** the primary blocker.
- If it is near or above the ceiling, execution engineering remains a blocker.
- A point-in-time order book snapshot can support a deployment-readiness estimate but cannot substitute for live fill logging.

## Production logging requirement

Before real capital is treated as validated, every live SOL fill should persist:
- signal/reference price;
- submitted order type;
- exchange order id;
- actual average fill price;
- filled quantity;
- commission amount and commission asset;
- maker/taker status if available;
- entry/exit latency;
- realized slippage vs reference price;
- funding charged/received while the position was open.

This audit is an execution-readiness study, not a claim that live fills have already been observed.
