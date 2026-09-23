# BNB B41-S6C-L — LONG Causal Invalidation Rule Construction Preregistration

## Objective

Convert the REF-validated B41-S6B-L price-path failure precursors into a small finite set of causal LONG invalidation rules.

This stage constructs an exit rule. It does not optimize TP, leverage, fees, PF, expectancy, or PnL.

## Frozen parents

- S6B-L signature: `35ab7d201fe45d398b3c959483aa7eef5d68a9d901336d57a25489f9b2f54190`
- S6B-L2 signature: `34311bc2e4d9d005c37ee461817463757dcf7532b8aa4f78ac454135430afc86`
- Setup: LOWER Q80 + TF60 C2 reclaim -> MARKET LONG.
- Baseline exit: detector+180m close.
- DEV: 2022-2024.
- REF: 2025-2026.

EMA/Fibonacci are excluded because S6B-L2 found no preregistered incremental information over price path.

## Frozen risk features

At +30m and/or +60m:
- entry_drawdown
- mae_so_far
- down_slope_3

Risk score at each horizon:
equal-weight mean of the three features after DEV-fitted robust scaling (median / IQR). Scaling is frozen before REF.

Higher = greater failure risk.

## Threshold philosophy

No arbitrary percentage stop is searched.

Thresholds are defined from **DEV winners only**:
- Q85 means the 85th percentile of the corresponding risk measure among DEV winners.

Thus every candidate has a predeclared winner-tolerance reference rather than an optimized stop distance.

## Frozen candidates

1. **R1_30_SCORE_Q85**
   - At +30m, exit at the completed 5m close if risk_score_30 >= DEV-winner Q85.

2. **R2_60_DRAW_Q85**
   - At +60m, exit if entry_drawdown_60 >= DEV-winner Q85.

3. **R3_60_SCORE_Q85**
   - At +60m, exit if risk_score_60 >= DEV-winner Q85.

4. **R4_60_2OF3_Q85**
   - At +60m, independently compare entry_drawdown, mae_so_far, down_slope_3 with their DEV-winner Q85.
   - Exit if at least 2 of 3 are at/above threshold.

If candidate does not trigger, hold to the frozen +180m endpoint.

No re-entry.

## Outcome accounting

For a triggered rule:
- exit price = snapshot completed close at +30m or +60m;
- aligned exit outcome = (exit - entry) / wall_distance.

For an untriggered rule:
- outcome = frozen +180m aligned outcome.

Diagnostics:
- stop rate;
- false-stop winner rate = stopped baseline winners / baseline winners;
- loser catch rate = stopped baseline losers / baseline losers;
- median improvement among caught losers = rule outcome - baseline outcome;
- mean outcome delta vs baseline;
- q10 outcome delta vs baseline;
- positive-outcome rate.

## DEV eligibility

Candidate is DEV_ELIGIBLE if:
- baseline n180 >=30;
- false-stop winner rate <=15%;
- loser catch rate >=25%;
- median caught-loser improvement >0;
- mean rule outcome >= baseline mean outcome;
- q10 rule outcome > baseline q10.

## DEV nomination

Among eligible candidates:
1. choose the earliest checkpoint (30m before 60m);
2. ties use fixed simplicity order:
   R2_60_DRAW_Q85 -> R3_60_SCORE_Q85 -> R4_60_2OF3_Q85.

No performance-based tie break after that.

If no candidate qualifies -> NO_NOMINATION.

## REF holdout validation

The single DEV nominee validates only if:
- REF baseline n180 >=20;
- false-stop winner rate <=15%;
- loser catch rate >=25%;
- median caught-loser improvement >0;
- mean rule outcome >= REF baseline mean;
- q10 rule outcome > REF baseline q10.

No alternate rule may replace a failed DEV nominee after REF is observed.

## Gate

- validated nominee -> `LONG_INVALIDATION_READY`
- otherwise -> `LONG_INVALIDATION_NOT_READY`

A validated LONG rule may proceed to LONG-only target/TP discovery while SHORT remains frozen.
