# SOL Indicator Relationship Discovery — Stage 7G Preregistration

**Status:** FROZEN BEFORE RESULT-BEARING MICROSTRUCTURE ANALYSIS  
**Parent:** Stage 7F showed that expansion/resolution can be filtered, while TP-vs-SL direction remains unstable OOS.  
**Purpose:** introduce genuinely new directional microstructure information without changing the frozen R3 market grammar or TP/SL objective.

## 1. Stage 7G-A — historical source audit

Candidate Binance USD-M SOLUSDT historical sources:

1. `bookDepth` — Binance Vision daily archive.
2. `bookTicker` — Binance Vision daily/monthly archive.
3. `aggTrades` — Binance Vision daily/monthly archive.
4. `liquidationSnapshot` — audit only; may be retired/incomplete.

The REST `/fapi/v1/depth` endpoint is treated as live/current snapshot only and is **not** valid for 2023–2026 backtesting.

### Audit dates
Check exact daily archive existence for:
- 2023-01-15
- 2023-07-15
- 2024-01-15
- 2024-07-15
- 2025-01-15
- 2025-07-15
- 2026-01-15
- 2026-07-15

A source is `HISTORICAL_CANDIDATE` only if:
- at least one audited file exists in DEV 2023–24;
- at least one exists in 2025;
- at least one exists in 2026;
- file header/schema is parseable;
- timestamps are present.

A source is `CORE_ELIGIBLE` only if all eight audit dates exist OR later full-range coverage audit proves >=95% of required signal dates.

Liquidation data cannot be a core Stage-7G source unless it passes the same coverage rule.

## 2. Frozen directional research universe

Stage 7G does **not** use every market timestamp.

Research events are exactly the frozen R3 directional episode onsets from Stage 7F.

Primary directional target:
- among events that resolve to TP or SL within 4H under TP1% / SL1%;
- label TP = frozen R3 direction wins;
- label SL = frozen R3 direction loses.

TIME rows are reported separately but excluded from directional relationship gates.

Stage-A resolution filtering from Stage 7F may be used only as a descriptive subgroup, not to learn new source thresholds before 7G-B preregistration.

## 3. Candidate microstructure families if source passes 7G-A

### Historical bookDepth
Only causal observations timestamped <= onset time:
- bid depth at 1%, 2%, 3%, 4%, 5%
- ask depth at 1%, 2%, 3%, 4%, 5%
- depth imbalance at each percentage:
  `(bid-ask)/(bid+ask)`
- notional imbalance at each percentage
- bid/ask depth slope 1%→5%
- change in imbalance over frozen windows 1m / 5m / 15m if sampling permits.

### Historical bookTicker
Only observations <= onset:
- best bid qty / ask qty
- BBO quantity imbalance
- spread / mid
- spread change 1m / 5m
- bid-qty and ask-qty change 1m / 5m
- signed BBO-pressure persistence over 1m / 5m.

### Historical aggTrades
Only trades <= onset:
- signed taker notional over 30s / 1m / 5m
- raw trade-count imbalance over same windows
- large-trade concentration using 2023-only causal quantile thresholds
- short-window CVD slope
- buy/sell run persistence
- price response per signed aggressive notional.

No post-onset trade or book observation is allowed.

## 4. Stage 7G-B prerequisite

No outcome-bearing microstructure test may be run until:
- 7G-A source audit is persisted;
- eligible source families are named;
- exact features and window definitions are separately frozen in a Stage-7G-B preregistration commit.

## 5. Guardrails

- Do not synthesize historical L2 from candles.
- Do not treat current REST depth as historical.
- Do not use future-nearest book samples; backward-asof only.
- Do not silently replace missing liquidation/order-book history with proxies.
- Do not introduce BTC.D/USDT.D again.
- Do not change Stage-6 states, Stage-7 R3 direction mapping, TP1%, SL1%, or RR 1:1 in Stage 7G.
- Mechanism labels such as wall, absorption, sweep, or liquidity pull are hypotheses unless the historical source actually contains the required structure.

**STAGE7G_A_FROZEN_BEFORE_SOURCE_AUDIT**
