# BNB B41-S6B-L2 — LONG EMA / Fibonacci Augmentation Preregistration

## Objective

Test whether familiar technical structures (EMA and Fibonacci) add stable failure information beyond the already validated B41 LONG post-entry price-path precursors.

This is an augmentation/anatomy stage. It does not create an exit rule.

## Frozen parents

- S6B-L signature: `35ab7d201fe45d398b3c959483aa7eef5d68a9d901336d57a25489f9b2f54190`
- Setup remains LOWER Q80 + TF60 C2 reclaim -> MARKET LONG.
- Outcome remains detector+180m aligned outcome >0 WINNER, <=0 LOSER.
- DEV 2022-2024; REF 2025-2026.

## Fixed horizons

Only +30m and +60m after entry are tested because S6B-L already established stable precursor information there.

## Frozen price-path baseline score

At each horizon the baseline risk score is the equal-weight robust-scaled mean of:
1. entry_drawdown
2. mae_so_far
3. down_slope_3

Scaling parameters are fit on DEV only (median and IQR) and applied unchanged to REF.

Higher score = more failure risk.

## EMA features

Computed causally from completed continuous 5m closes available at the snapshot:

Continuous risk-oriented:
- close_below_ema7 = (EMA7 - close) / wall_distance
- close_below_ema20 = (EMA20 - close) / wall_distance
- ema7_below_ema20 = (EMA20 - EMA7) / wall_distance
- ema7_down15 = (EMA7[t-15m] - EMA7[t]) / wall_distance
- ema20_down30 = (EMA20[t-30m] - EMA20[t]) / wall_distance

Binary:
- close_under_ema7
- close_under_ema20
- ema7_under_ema20
- close_under_both_ema

EMA7/EMA20 use pandas EWM span 7/20, adjust=False, on completed 5m closes.

## Fibonacci features

No hindsight swing is allowed.

The frozen LONG reclaim leg is known at entry:
- leg_low = detector extreme from the completed TF60 detector window
- leg_high = market entry close
- leg_size = entry - detector_extreme

Continuous:
- reclaim_fib_giveback = (entry - snapshot_close) / leg_size

Binary standard Fibonacci giveback levels:
- fib_382_breached
- fib_500_breached
- fib_618_breached
- fib_786_breached

A breach means the completed snapshot close is at or below:
entry - fib_level * leg_size.

## Evaluation

Positive class = eventual LOSER.

For every technical feature:
- report univariate failure AUC on DEV and REF;
- build a fixed augmented score = equal-weight robust-scaled mean of the three baseline price-path features plus that one technical feature;
- compare augmented AUC with the frozen baseline score.

Binary features are also robust-scaled using DEV 0/1 distribution; if IQR/std is zero, scale denominator defaults to 1.

## DEV nomination

A technical feature is DEV_NOMINATED if:
- DEV winners >=30 and losers >=20;
- univariate failure AUC >=0.58;
- augmented-score DEV AUC >= baseline DEV AUC +0.015.

## REF validation

A DEV-nominated feature is REF_VALIDATED if:
- REF winners >=20 and losers >=15;
- univariate failure AUC >=0.55;
- augmented-score REF AUC >= baseline REF AUC +0.010.

No feature not nominated on DEV may be promoted from REF.

## Gate

- If >=1 EMA feature validates: EMA_ADDS_STABLE_INFORMATION.
- If >=1 Fibonacci feature validates: FIB_ADDS_STABLE_INFORMATION.
- If neither validates: TECHNICAL_AUGMENTATION_NOT_SUPPORTED.

No SL threshold, TP, trade WR, PF, expectancy, leverage, or PnL is optimized.
