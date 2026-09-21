# SOL Execution Feasibility Audit V1 — Preregistration

## Objective

Evaluate whether the already-frozen final SOL tradable universe is economically executable on Binance USDⓈ-M Futures after route-specific maker/taker fees, realistic taker slippage, and historical funding.

No detector, entry, SL, exit, side, score, threshold, or trade-selection rule may change.

## Frozen trading universe

Exactly the 302 trades persisted by:
`SOL_FINAL_TRADABLE_UNIVERSE_AUDIT_V1_Trades.csv`

Architecture:
- Score 3, both sides -> trade.
- Score 4 + SELL_SIDE liquidity -> LONG -> trade.
- Score 4 + BUY_SIDE liquidity -> SHORT -> excluded.

## Frozen route execution assumptions

### Score 3 — FIVE_MIN_REVERSAL_BREAK

Upstream implementation enters at the **next 5m open after the completed reversal-break bar**.

Execution assumption:
- entry = taker;
- exit at RECLAIM_EXTREME stop or structural-completion event = taker.

Therefore:
- 2 taker legs per Score-3 trade.

### Score 4 SELL_SIDE/LONG — GAP_25

Upstream implementation places a retracement price and waits for market to touch it before the deadline.

Execution assumption:
- entry = resting limit / maker;
- exit at RECLAIM_EXTREME stop or structural-completion event = taker.

Therefore:
- 1 maker leg + 1 taker leg per Score-4 LONG trade.

No optimistic maker assumption is applied to Score 3.

## Binance regular-user commission assumptions

For the primary baseline:
- USDⓈ-M maker fee = **2 bps** per executed maker leg;
- USDⓈ-M taker fee = **5 bps** per executed taker leg.

BNB-discount sensitivity:
- 10% reduction to standard commission:
  - maker = **1.8 bps**
  - taker = **4.5 bps**

Commission is calculated from actual entry/exit notional:
- fee per unit = execution_price * fee_rate.

## Taker slippage model

Maker GAP25 entry receives zero adverse slippage in the primary execution model.

Each taker leg is stressed by adverse slippage of:
- 0.0 bps
- 0.5 bps
- 1.0 bps
- 2.0 bps
- 3.0 bps
- 5.0 bps

For LONG:
- taker entry price moves upward;
- taker exit price moves downward.

For SHORT:
- taker entry price moves downward;
- taker exit price moves upward.

Fees are then charged on the slippage-adjusted execution price.

No positive price improvement is assumed.

## Current SOLUSDT order-book calibration snapshot

Before opening the audit results, the Binance USDⓈ-M order book snapshot was:

- best bid: 111.7300
- best ask: 111.7400
- full spread: approximately **0.895 bps**
- half spread: approximately **0.447 bps**
- best-ask displayed notional: approximately **43.8k USDT**
- best-bid displayed notional: approximately **113.5k USDT**

Interpretation:
- 0.5 bps per taker leg is the closest frozen stress point to the observed half-spread for small size;
- this one snapshot is calibration only, not historical proof of spread/slippage.

## Historical funding

The audit will request Binance USDⓈ-M SOLUSDT historical funding rates.

For each trade, funding is included only when a funding timestamp occurs strictly after entry and at or before exit.

Per unit position:
- LONG funding cost = mark_price * funding_rate;
- SHORT funding cost = -mark_price * funding_rate.

If mark price is unavailable, entry price is used as fallback.

Funding may therefore be a cost or a credit.

## Funding data plumbing note

The first workflow attempt failed before any metric calculation because the GitHub runner received HTTP 451 from Binance's public funding endpoint.

Without changing any audit rule or cost assumption:
- SOLUSDT funding history was fetched through the connected Binance public-data interface;
- **6,663** records were persisted to `research/SOLUSDT_FUNDING_2020_2026.csv`;
- first funding timestamp: 2020-09-16;
- last funding timestamp: 2026-09-20;
- the connector returned blank historical `markPrice`, so the preregistered entry-price fallback is used for funding notional.

## R accounting

Initial risk remains:
`initial_risk_price`

For each scenario:

`net_R = price_PnL_after_slippage_R - commission_R - funding_R`

Price PnL after slippage is recomputed from adjusted entry and adjusted exit, not approximated by subtracting a fixed R amount.

## Required outputs

Report for:
- ALL
- Score 3
- Score 3 BUY_SIDE/SHORT
- Score 3 SELL_SIDE/LONG
- Score 4 SELL_SIDE/LONG

For every fee/slippage scenario:
- N
- mean net R
- PF
- cumulative net R
- win rate
- max DD
- max loss streak
- median total execution cost R

Also report:
- maker-entry count
- taker-entry count
- taker-exit count
- fee-only result
- BNB-discount fee-only result
- historical funding contribution
- exact break-even extra taker slippage per leg for mean net R = 0
- maximum extra taker slippage per leg retaining PF >= 1.10
- route/component-specific break-even slippage.

## Primary execution-feasibility gates

Primary scenario:
**regular-user fees + 0.5 bps adverse slippage per taker leg + historical funding**

All must pass:

1. ALL mean net R > 0
2. ALL PF >= 1.10
3. ALL cumulative net R > 0
4. Score 3 mean net R > 0
5. Score 3 PF >= 1.05
6. Score-4 LONG mean net R > 0
7. Score-4 LONG PF >= 1.20
8. both BUY_SIDE and SELL_SIDE aggregate mean net R > 0
9. break-even extra taker slippage per leg >= 1.0 bps above regular fees
10. current half-spread calibration (0.447 bps) is below the computed break-even taker-slippage budget.

If all pass:

`SOL_EXECUTION_FEASIBLE_UNDER_BASELINE_BINANCE_ASSUMPTIONS`

If any fail:

`SOL_EXECUTION_NOT_FEASIBLE_UNDER_BASELINE_BINANCE_ASSUMPTIONS`

## Interpretation constraint

This audit does not validate live fills.

A pass means the gross strategy edge appears large enough to survive the frozen fee/slippage/funding assumptions and can advance to paper/live execution measurement.

A fail means do not rescue the system by altering detector, TP, SL, session, or score rules inside this audit.

