# SOL ORB E2 Retest Economics v1 — Preregistration

## Purpose

Test whether the already-selected SOL ORB execution coordinate `E2_RETEST_LEVEL` has positive Development economics **before** any additional retest-character filter is promoted.

This is not a new structure search and not a rescue experiment.

## Frozen population

- Pair: SOLUSDT
- Side: LONG only
- Timeframe: 5m
- Habitat: H23 UTC / 06:00–07:00 WIB anchor
- Partition: Development only; Reference/OOS remains closed
- Weekdays only
- Structure detector: ORB v1
- Required sequence: `BREAK_HIGH -> RETEST_HIGH -> ACCEPT_HIGH`
- Frozen signal population expected from prior characterization: 145 sessions
- Entry coordinate: **E2_RETEST_LEVEL = ORB High price on the preregistered retest event**

No structural thresholds may be added in this test.

## Economic assumptions

Use the repository reference economics:

- reference notional: **$500 per trade**
- round-trip cost: **0.15% of notional** (fee + slippage reference cost)
- no leverage-dependent compounding
- one independent reference trade per detected session

The 0.15% cost and $500 notional are inherited from the repository causal baseline rather than derived from ORB outcomes.

## Frozen exits

No TP/SL optimization is allowed in v1. Evaluate deterministic time exits only:

- +15m
- +30m
- +60m
- +120m

For each horizon calculate the exit close exactly at the existing causal forward horizon used by the entry-characterization script.

## Required metrics

For each horizon:

- N
- gross hit rate before costs
- net win rate after round-trip cost
- gross mean return
- net mean return
- total net PnL on $500 reference notional
- expectancy per trade
- profit factor
- max drawdown in dollars using chronological trade PnL
- max loss streak
- yearly N / net win rate / expectancy / net PnL for 2022, 2023, 2024

Also report E2 120m MFE/MAE diagnostics from the causal post-fill observation window.

## Interpretation rule

This run may answer only:

> Does the unfiltered E2 retest entry show economically positive Development behavior under fixed, non-optimized exits after reference trading costs?

It may nominate a horizon for later validation, but it may not promote a live rule.

If economics are weak, do not tune retest thresholds inside this lineage. If economics are promising, characterize retest quality in a new preregistered phase and keep OOS closed.
