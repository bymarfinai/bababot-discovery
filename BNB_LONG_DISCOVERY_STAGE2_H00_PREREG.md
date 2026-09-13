# BNB LONG Reset V1 — Stage 2 H00 Preregistration

Status: **FROZEN BEFORE H00 DEVELOPMENT EXECUTION**

Branch: `bnb-long-character-discovery-reset-v1`

This document is the mandatory baseline for H00 and, unless a future change is preregistered before seeing a new hour, the same baseline is carried unchanged to later hours.

## Scope

- Symbol: BNBUSDT perpetual futures
- Side: LONG only
- Habitat: H00 = 00:00–01:00 WIB
- Decision anchors: 00:00, 00:15, 00:30, 00:45 WIB
- UTC equivalents: 17:00, 17:15, 17:30, 17:45 UTC
- Development only: local-WIB years 2022, 2023, 2024
- OOS 2025-01-01 through 2026-07-30 remains sealed and is not downloaded or evaluated by the Stage-2 runner.

## Causality

At every anchor, all structural features use only fully completed 5-minute bars strictly before the anchor. The reference entry price is the BNBUSDT 5-minute open at the anchor. No feature may use the anchor candle high, low, close, or any future candle.

## Frozen Structural Baseline

The same raw feature families are inspected at every hour:

1. `drive_15m` — pre-anchor 15-minute directional return.
2. `drive_60m` — pre-anchor 60-minute directional return.
3. `drive_240m` — pre-anchor 240-minute directional return / regime context.
4. `ema20_ema50_spread` — pre-anchor trend-location spread.
5. `range_location_240m` — last completed close location inside the prior 4-hour high-low range.
6. `range_ratio_60_240` — prior 1-hour range divided by prior 4-hour range; compression/expansion context.
7. `rv_ratio_60_240` — prior 1-hour realized volatility divided by prior 4-hour realized volatility.
8. `efficiency_60m` — directional path efficiency over the prior hour.
9. `lower_wick_pressure_15m` — average lower-wick share over the last three completed bars.
10. `swing_slope_30_30` — change in 30-minute range midpoint versus the preceding 30 minutes, normalized by price.
11. `above_ema20` — binary pre-anchor location state.
12. `ema20_reclaim` — binary causal reclaim state: previous completed close at/below its EMA20 followed by latest completed close above its EMA20.

No feature is added after H00 results are seen in order to rescue H00.

## Character Formation

Primary-character discovery is deliberately simple:

- Numeric features are converted to causal percentiles using only the previous 60 observations of the same quarter-hour anchor, with a minimum history of 40.
- Percentile states are frozen as LOW `[0, 1/3)`, MID `[1/3, 2/3)`, HIGH `[2/3, 1]`.
- Binary features are evaluated as TRUE and FALSE states.
- A primary character contains exactly **one structural feature/state**.
- Pairwise/multi-feature combinations are forbidden during the primary search. They belong only to later secondary-confirmation work after a primary character exists.

This prevents a combinatorial rescue search.

## Fixed Directional Diagnostics

Character Discovery does not optimize TP, SL, leverage, or a preferred holding period. Every event is evaluated on the same three fixed diagnostic horizons:

- +60 minutes
- +120 minutes
- +240 minutes

Each horizon return is measured from the anchor open to the open at the exact future horizon. `consensus_return` is the arithmetic mean of the three diagnostic returns. `consensus_win` means `consensus_return > 0`.

These horizons are diagnostics only and cannot later be claimed as the trading hold without Trade Construction.

## Preregistered Primary Gate

A primary character is a Development PASS only when all of the following hold:

### Pooled consensus
- N >= 160
- consensus WR > 55%
- mean consensus return > 0
- consensus profit factor >= 1.20

### Horizon robustness
A horizon is supportive when N >= 160, WR >= 53%, mean return > 0, and PF >= 1.10. At least 2 of 3 horizons must be supportive.

### Cross-year robustness
For each of 2022, 2023, 2024:
- N >= 40
- consensus WR >= 52%
- mean consensus return > 0
- PF >= 1.05

At least 2 of the 3 years must also have consensus WR > 55%.

### Quarter-hour anchor robustness
An anchor is supportive when N >= 40, consensus WR >= 52%, mean consensus return > 0, and PF >= 1.05. At least 3 of the 4 anchors must be supportive.

## Deterministic Ranking

If more than one primary passes, selection is deterministic and is **not** based on peak WR alone. Passers are ranked by:

1. highest minimum yearly mean consensus return
2. highest number of years with WR >55%
3. highest supportive-anchor count
4. highest supportive-horizon count
5. highest pooled mean consensus return
6. highest pooled consensus WR
7. highest pooled PF
8. lexical rule name as final deterministic tie-break

## Verdict / Stop Rule

Possible H00 primary verdicts:

- `PRIMARY_PASS` — freeze the top primary character and stop scanning new hours. Next work is secondary confirmation/stress testing for this same H00 character; OOS stays sealed.
- `PRIMARY_FAIL` — no primary character passed. Persist exact failure diagnostics before moving to H01.
- `INSUFFICIENT_DATA` — data/coverage failure; this is not a market-character rejection.

No gate relaxation is allowed after seeing H00. No B28 winner receives ranking preference. Historical code may be consulted only for causal/data-engineering patterns, not for candidate inheritance.