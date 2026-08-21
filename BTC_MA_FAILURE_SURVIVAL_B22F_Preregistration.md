# BTC Continuous MA Failure Survival B22F — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Question
After a valid bullish MA entry, does an opposing higher-timeframe state cause the entry-timeframe bullish MA structure to fail sooner?

B22E already inspected every bar inside its first-six-bar window, but that six-bar horizon was arbitrary. B22F removes that cutoff. It monitors **every completed entry-timeframe candle after execution** and records the first MA-structure failure candle.

Research only. B22E remains historically unchanged and live BBC is untouched.

## Data / partitions
Same Binance BTCUSDT USD-M 5m source and frozen partitions used by B22E:
- external: 2020-01-01 to 2021-12-31
- development: 2022-01-01 to 2024-12-31
- reference_validation: 2025-01-01 to 2026-07-29
- August 2026: diagnostic only

Higher-timeframe states are causally available only after their candles close.

## Entry families
Frozen from B22B/B22E:
- `PULLBACK_RECLAIM` — primary
- `CROSSOVER_INIT` — secondary diagnostic

Pairs:
- 5m entry → inspect causally available 1h state
- 1h entry → inspect causally available 4h state

Higher state at signal close:
- `STRONG_BULL`
- `STRONG_BEAR`
- `NEUTRAL`

Bull/Bear state definitions are frozen exactly as B22E.

## Continuous post-entry monitoring
Execution occurs at the next entry-timeframe open after the completed entry signal.

Beginning with the **first completed candle after execution**, inspect every consecutive entry-timeframe candle: bar 1, bar 2, bar 3, ... until the first failure event or partition end.

Two failure events are recorded independently.

### SOFT_MA_FAILURE
First completed entry-TF candle satisfying all:
- close < EMA20;
- EMA20 < EMA20 on the immediately previous entry-TF candle;
- normalized bullish EMA20-EMA50 spread < its immediately previous value.

This means the post-entry bullish MA shape has started reversing rather than merely failing to print a higher high.

### HARD_MA_FAILURE
First completed entry-TF candle satisfying either:
- close < EMA50; OR
- EMA20 < EMA50.

This measures deeper structural failure.

For every event record:
- `bars_to_soft_failure`
- `bars_to_hard_failure`
- wall-clock hours to each failure
- censoring at partition end
- higher-TF state at signal close

No fixed TP, SL, MFE threshold, higher-high requirement, or six-bar fakeout cutoff is used.

## Frozen survival checkpoints
For each partition / entry TF / entry type / higher-state group report the fraction of entries whose MA structure has **not yet failed** by completed bar:

`1, 2, 3, 4, 6, 12, 24, 48`

Report separately for SOFT and HARD failure, plus median bars-to-failure among uncensored events.

These checkpoints are descriptive survival summaries, not alternative optimized labels.

## Primary hypothesis
For `PULLBACK_RECLAIM`:
- 5m entry under 1h STRONG_BEAR should have shorter MA survival than 5m entry under 1h STRONG_BULL.
- 1h entry under 4h STRONG_BEAR should have shorter MA survival than 1h entry under 4h STRONG_BULL.

A pair is `OPPOSING_HTF_FAILURE_SUPPORTED` only if, in external, development, and reference_validation:
1. each compared state has N >= 20 for 5m→1h or N >= 10 for 1h→4h;
2. median bars-to-soft-failure is lower under STRONG_BEAR than STRONG_BULL; and
3. soft-MA survival at bar 6 is at least 10 percentage points lower under STRONG_BEAR than STRONG_BULL.

A >=20pp bar-6 survival difference in the same direction across all three partitions is a `STRONG_EFFECT` diagnostic.

If a required Strong Bear group is absent, the pair is `INCONCLUSIVE`, not FAIL.

## Interpretation
Because every trend eventually ends, B22F does **not** call every eventual failure a fakeout. The purpose is to measure **how quickly** the MA shape breaks after entry and whether opposing higher-TF state shifts that failure distribution toward earlier candles.
