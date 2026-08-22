# BTC London -> New York F85 Current State Snapshot

Saved: 2026-08-22

## Frozen structural model
- Instrument: BTCUSDT perpetual
- Research clock: raw 5m
- Session structure: previous London High/Low frozen before New York
- Directional detector: B27Q London -> New York LONG K1 OPP0
- Entry window: after causal leave from Touch High #1 and before Touch High #2
- H2 is a milestone, not TP

## Rule comparison

### 1. Blind F85
- Entry: resting limit at F85 before H2
- Exit framework used for comparison: TP E20; close-invalidation F35
- Major partitions: 149 trades
- Pooled WR: 68.5%
- Pooled PF: 1.40
- Pooled expectancy: +$0.60/trade
- Pooled net: +$89.68 at $500 notional and $0.40 fee
- Per partition: external 46 trades, WR 76.1%, PF 3.40; development 72, WR 63.9%, PF 0.98; reference_validation 31, WR 67.7%, PF 1.08

### 2. Early Reclaim
- Entry: F85 touched, first causal 5m close reclaims/holds >= F85, enter next 5m open if still before H2
- Exit framework: TP E20; close-invalidation F35
- Major partitions: 118 trades
- Pooled WR: 71.2%
- Pooled PF: 1.47
- Pooled expectancy: +$0.65/trade
- Pooled net: +$76.51
- Per partition: external 43 trades, WR 76.7%, PF 2.89; development 54, WR 66.7%, PF 1.08; reference_validation 21, WR 71.4%, PF 0.98
- Status: current best balance between frequency and quality, but NO_PASS on frozen major-partition gate

### 3. Same-Bar Rejection diagnostic subset
- Entry: the same 5m candle that first touches F85 closes back >= F85; enter next 5m open if still causal/pre-H2
- Exit framework: TP E20; close-invalidation F35
- Major partitions: 68 trades
- Pooled WR: 73.5%
- Pooled PF: 1.70
- Pooled expectancy: +$0.91/trade
- Pooled net: +$61.80
- Per partition: external 27 trades, WR 74.1%, PF 2.18; development 30, WR 66.7%, PF 1.17; reference_validation 11, WR 90.9%, PF 6.23
- Status: strongest pooled quality, but sample size is too small for promotion; remains diagnostic only

## Structural B27W reference
For blind F85 fills, probability of eventual Touch High #2 before opposite break/session end:
- external: 89.1% (41/46)
- development: 73.6% (53/72)
- reference_validation: 87.1% (27/31)
- august: 100% (3/3; tiny)
This is structural H2 hit rate, not final trading WR.

## Target framework
Current target rule is E20:
- Let London range R = H - L.
- TP price = H + 0.20 * R.
This is a fixed formula but a dynamic daily price level because H, L, and R change every session.

## Invalidation framework
Current comparison stop is F35 close-invalidation:
- Boundary price = L + 0.35 * R.
- It is not a wick stop.
- Trade invalidates only on a completed raw 5m close below F35, with execution at that close in the backtest.

## Status
Research only. Live BBC unchanged. Do not promote any rule as final/live until a frozen multi-partition gate is passed or an explicit user decision is made.
