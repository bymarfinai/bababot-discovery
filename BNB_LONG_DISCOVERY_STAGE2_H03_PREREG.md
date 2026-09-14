# BNB LONG Reset V1 — Stage 2 H03 Primary Discovery Preregistration

## Status

**FROZEN BEFORE H03 PRIMARY RUN**

This document advances the existing Reset V1 methodology by exactly one habitat only. Nothing in the feature engine, candidate space, diagnostic horizons, gates, ranking, or OOS policy is changed after H00/H01/H02.

## Scope

- Symbol: **BNBUSDT perpetual**
- Side: **LONG only**
- Habitat under test: **03:00–04:00 WIB**
- Quarter-hour anchors: **03:00, 03:15, 03:30, 03:45 WIB**
- Equivalent UTC anchors: **20:00, 20:15, 20:30, 20:45 UTC**
- Development years: **2022, 2023, 2024**
- OOS: **2025-01-01 through 2026-07-30 remains sealed and must not be downloaded/evaluated in this primary run**

## Frozen causal construction

- Features use only completed 5-minute bars strictly before each anchor.
- Reference entry is the 5-minute open at the anchor.
- No anchor-candle high, low, or close is allowed in the signal definition.
- Numeric states use causal same-anchor percentiles from the previous 60 observations, minimum history 40.
- LOW = [0, 1/3), MID = [1/3, 2/3), HIGH = [2/3, 1].
- Binary states remain TRUE/FALSE.

## Frozen primary feature families

1. `drive_15m`
2. `drive_60m`
3. `drive_240m`
4. `ema20_ema50_spread`
5. `range_location_240m`
6. `range_ratio_60_240`
7. `rv_ratio_60_240`
8. `efficiency_60m`
9. `lower_wick_pressure_15m`
10. `swing_slope_30_30`
11. `above_ema20`
12. `ema20_reclaim`

Primary discovery remains exactly one feature/state at a time. No pairwise or multifeature primary search is allowed.

## Frozen diagnostics

- +60m return
- +120m return
- +240m return
- `consensus_return` = mean of the three forward returns
- `consensus_win` = `consensus_return > 0`

These are structural diagnostics, not a final executable TP/SL/hold model.

## Frozen Primary Gate

### Pooled
- N >= 160
- consensus WR > 55%
- mean consensus return > 0
- consensus PF >= 1.20

### Horizon robustness
A horizon is supportive when:
- N >= 160
- WR >= 53%
- mean > 0
- PF >= 1.10

At least **2/3** horizons must be supportive.

### Cross-year robustness
For each of 2022, 2023, and 2024:
- N >= 40
- consensus WR >= 52%
- mean > 0
- PF >= 1.05

Additionally, at least **2/3 years** must have WR > 55%.

### Quarter-hour anchor robustness
An anchor is supportive when:
- N >= 40
- WR >= 52%
- mean > 0
- PF >= 1.05

At least **3/4 anchors** must be supportive.

## Frozen deterministic ranking

Among full-gate passers, rank by:
1. highest minimum yearly mean
2. most years with WR > 55%
3. most supportive anchors
4. most supportive horizons
5. pooled mean
6. pooled WR
7. pooled PF
8. lexical tie-break

## Stop rule

- `PRIMARY_PASS`: freeze the top primary, stop scanning new hours, and move to same-H03 secondary/stress testing. OOS remains sealed.
- `PRIMARY_FAIL`: persist exact diagnostics; H04 becomes eligible.
- `INSUFFICIENT_DATA`: treat as a data issue, not a market failure.

## Explicit prohibitions

No H02 rescue is carried into H03. No threshold relaxation, anchor exclusion, hour merging, TP/SL tuning, leverage/position-size tuning, post-hoc filters, B28 inheritance, peak-WR selection, or OOS exposure is allowed.

H02 remains archived as **structural-valid / execution-unstable** after passing structural/OOS stages but failing the preregistered executable trade-construction robustness gate.
