# ETH Temporal A1 — Primitive Time/Horizon Discovery — Preregistration

## Purpose
Return to the simplest BTC-style discovery layer before any structural grammar. This experiment asks only: **at what clock times, in which direction, and over which fixed forward horizon does ETHUSDT show a repeatable unconditional economic bias?**

No E12 90-rule character filters are used. No prior E12/E13 winner hours are used to select the scan space.

## Frozen universe
- Pair: ETHUSDT perpetual
- Raw bars: Binance Futures UM 5m
- Selection partition: Development only = 2022-01-01 through 2024-12-31 UTC
- OOS / post-2024 data: CLOSED and not read for model selection
- Notional: $500 per observation
- Round-trip fee assumption: $0.75 per observation
- Entry anchor: first 5m bar open at each exact UTC hour HH:00
- Directions: LONG and SHORT
- Fixed forward holds: 60, 120, 240, 360, 720, 960 minutes
- Exit: open of the 5m bar exactly `hold` minutes after entry
- One observation per UTC calendar day × hour × direction × hold when both timestamps exist
- Observations are diagnostic probes and may overlap. This stage does **not** impose one-position portfolio sequencing.

## Causality
All entries use only the anchor open at time t. Exits occur strictly in the future at t + hold. No forward information is used to decide entry, direction, or horizon.

## Metrics
For every UTC hour × direction × hold:
- N
- win rate after fee (PnL > 0)
- net PnL
- expectancy per observation
- profit factor
- max drawdown on chronological cumulative PnL
- max loss streak
- year-by-year N, WR, net, expectancy, PF for 2022, 2023, 2024

## Temporal ranking
For each UTC hour, rank all 12 direction/horizon combinations with the following frozen order:
1. positive in all 3 years (net > 0 each year)
2. minimum yearly expectancy descending
3. pooled expectancy descending
4. pooled PF descending
5. pooled WR descending
6. max drawdown ascending
7. max loss streak ascending
8. shorter hold
9. LONG before SHORT only as final deterministic tie-break

The top combination per hour is called the **primitive temporal representative**. This is a map, not a production winner.

## Cross-check rule
Only after the complete 24-hour map is generated may we compare it with prior E12/E13/E15 findings. No E12/E13 hour, rule, hold, or direction is allowed to alter this experiment after results are seen.

## Interpretation
This stage is intentionally primitive. A positive time/horizon bias does not prove a tradable setup because it has no state filter and allows overlapping probes. Its purpose is to reveal ETH-native temporal habitat before structural conditioning.

## Stop rules
- Do not relax gates after seeing results.
- Do not rescue weak hours by importing E12 structural rules.
- Do not use OOS.
- Do not promote any result directly to live trading.
