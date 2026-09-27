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

## Stage 7G-B — BookDepth Directional Relationship (FROZEN BEFORE OUTCOMES)

Stage 7G-A2 full-calendar audit:
- bookDepth: 1,358 / 1,363 days = 99.633% coverage, ~584 MB compressed.
- aggTrades: 1,363 / 1,363 days = 100%, ~10.4 GB compressed.
- bookTicker and liquidationSnapshot are not core eligible.

Stage 7G-B uses **bookDepth only**. aggTrades is deferred to a separately preregistered follow-up because it is a materially larger source and must not be introduced opportunistically after bookDepth outcomes.

### Causal alignment
- Research rows = exact R3 new directional episode onsets.
- Only bookDepth snapshots with timestamp <= onset are allowed.
- Current snapshot must be no older than **90 seconds**.
- For lagged book features, the selected prior snapshot must be <= target lag timestamp and no older than 90 seconds relative to that lag target.
- No future-nearest match.
- Feature coverage must be >=95% in DEV 2023–24, 2025, and 2026 or Stage 7G-B is source-failed and no relationship result is promoted.

### Direction normalization
Raw depth imbalance at absolute percentage p:
`DI_p = (bid_depth_-p - ask_depth_+p) / (bid_depth_-p + ask_depth_+p)`.

Raw notional imbalance:
`NI_p = (bid_notional_-p - ask_notional_+p) / (bid_notional_-p + ask_notional_+p)`.

Every directional feature is multiplied by:
- +1 for frozen R3 LONG
- -1 for frozen R3 SHORT.

Therefore positive means depth/notional pressure aligned with the frozen R3 direction.

### Frozen feature list
Current snapshot:
1. signed_depth_imb_1
2. signed_depth_imb_2
3. signed_depth_imb_5
4. signed_notional_imb_1
5. signed_notional_imb_2
6. signed_notional_imb_5
7. signed_depth_slope_1to5 = side-signed [log(bidDepth5/bidDepth1) - log(askDepth5/askDepth1)]
8. signed_notional_slope_1to5 = analogous notional slope.

Causal changes:
9. depth_imb1_change_1m
10. depth_imb1_change_5m
11. depth_imb1_change_15m
12. depth_imb5_change_1m
13. depth_imb5_change_5m
14. depth_imb5_change_15m
15. notional_imb1_change_1m
16. notional_imb1_change_5m
17. notional_imb1_change_15m

All change features are current signed value minus lagged signed value.

### Primary directional target
Only resolved 4H onset events:
- TP = frozen R3 direction reaches +1% before -1%.
- SL = frozen R3 direction reaches -1% before +1%.
- TIME excluded from the primary TP-vs-SL relationship atlas.

No execution filtering is used for the anatomy atlas; events may overlap.

### Bucketing
For each of the 17 features:
- derive 33.33% and 66.67% cuts from resolved DEV 2023–24 only;
- freeze those exact cuts;
- apply them unchanged to 2025 and 2026.

For each partition report LOW/MID/HIGH N and TP rate.

Primary contrast:
`delta_TP = TP_rate(HIGH) - TP_rate(LOW)`.

A feature is `REPLICATED_DIRECTIONAL_MICROSTRUCTURE` only if:
- DEV high N >=150 and low N >=150;
- 2025 high/low N >=75 each;
- 2026 high/low N >=75 each;
- |DEV delta_TP| >=8 percentage points;
- 2025 and 2026 delta_TP have the same sign as DEV;
- |2025 delta_TP| >=4pp;
- |2026 delta_TP| >=4pp.

No threshold rescue, feature combinations, RF, logistic model, side deletion, or cell deletion are allowed in Stage 7G-B.

### Stage 7G-C prerequisite
Only features passing the frozen replication gate may be considered for an executable combination with the frozen Stage-7F resolution layer. Any such combination requires a new preregistration commit before outcome testing.

**STAGE7G_B_FROZEN_BEFORE_OUTCOMES**
