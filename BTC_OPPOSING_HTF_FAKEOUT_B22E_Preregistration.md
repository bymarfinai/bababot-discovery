# BTC Opposing Higher-TF Fakeout B22E — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Question
Does a lower-timeframe LONG setup fake out because the next higher timeframe is still in a **strong bear** state?

Primary comparisons:
- 5m LONG entry while causally available 1h state is `STRONG_BEAR` vs `STRONG_BULL` / neutral.
- 1h LONG entry while causally available 4h state is `STRONG_BEAR` vs `STRONG_BULL` / neutral.

This experiment does not redefine fakeout as failure to make a higher high.

## Data / partitions
Same Binance BTCUSDT USD-M 5m source and frozen partitions as B22B/B22D:
- external: 2020-01-01 to 2021-12-31
- development: 2022-01-01 to 2024-12-31
- reference_validation: 2025-01-01 to 2026-07-29
- August 2026: diagnostic only

Higher-timeframe states are usable only after the corresponding candle has closed.

## Entry setup
Use the already frozen B22B LONG signals separately:
- `PULLBACK_RECLAIM` (primary)
- `CROSSOVER_INIT` (secondary diagnostic)

Execution is next entry-timeframe candle open after the completed signal candle.

## Strong bull / strong bear states
`STRONG_BULL(tf)` is unchanged from B22B:
- EMA20 > EMA50
- EMA20 rising versus 3 bars ago
- EMA50 rising versus 3 bars ago
- normalized EMA20-EMA50 spread widening versus 3 bars ago
- close > EMA20

`STRONG_BEAR(tf)` is its exact mirror:
- EMA20 < EMA50
- EMA20 falling versus 3 bars ago
- EMA50 falling versus 3 bars ago
- normalized EMA50-EMA20 bear spread widening versus 3 bars ago
- close < EMA20

At each LONG signal, next-higher-TF state is frozen as exactly one of `STRONG_BEAR`, `STRONG_BULL`, or `NEUTRAL`.

## Primary fakeout definition — immediate MA failure
A LONG entry is `FAKEOUT_MA6` if, within the first **6 completed entry-TF candles after execution**, at least one candle shows all three:
1. close < EMA20,
2. EMA20 < previous EMA20,
3. bullish EMA20-EMA50 spread is narrower than the prior candle.

This directly represents the user's definition: after a valid bullish setup/entry, price immediately turns down and the MA structure stops looking like a clean strong uptrend.

The six-bar horizon is timeframe-relative:
- 5m entry: first 30 minutes.
- 1h entry: first 6 hours.

## Hard-reversal robustness metric
Separately report `HARD_REVERSAL_12`: within the first 12 entry-TF candles, either:
- close < EMA50, or
- EMA20 < EMA50.

This is not the primary label; it is a stricter robustness check.

## Mandatory descriptive outcomes
For each partition × entry TF × entry type × higher-TF state report:
- N
- `FAKEOUT_MA6` rate
- `HARD_REVERSAL_12` rate
- median return after 6 bars
- median MFE / MAE over first 6 bars
- average fraction of the first 6 bars that remain `STRONG_BULL`

## Frozen hypothesis gate
Primary gate uses `PULLBACK_RECLAIM` only.

For each pair (5m→1h, 1h→4h), call `OPPOSING_HTF_SUPPORTED` only if in external, development, and reference-validation:
- opposing `STRONG_BEAR` sample N >= 20 for 5m and N >= 10 for 1h;
- `FAKEOUT_MA6` rate under `STRONG_BEAR` is at least **10 percentage points higher** than under `STRONG_BULL` in every partition.

`STRONG_OPPOSING_HTF_EFFECT` additionally requires >=20 percentage-point excess fakeout rate in every partition.

If sample requirements fail, result is `INCONCLUSIVE`, not PASS/FAIL.

No threshold tuning after results. No live BBC changes.
