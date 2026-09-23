# BNB B41-S6D-L — Triggered LONG Recovery Anatomy Preregistration

## Objective

Among LONG trades where the frozen S6C-L alarm `R4_60_2OF3_Q85` fires at +60m, identify what distinguishes:
- **FALSE_STOP_WINNER**: alarm fired, but frozen +180m outcome is positive.
- **TRUE_FAILURE_LOSER**: alarm fired, and frozen +180m outcome is non-positive.

S6D-L is recovery anatomy only. It does not create or promote an exit rule.

## Frozen parent

S6C-L signature:
`75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f`

Frozen alarm:
- checkpoint = detector +60m
- alarm = at least 2 of:
  1. entry_drawdown >= DEV-winner Q85
  2. mae_so_far >= DEV-winner Q85
  3. down_slope_3 >= DEV-winner Q85

Expected alarm cohort parity:
- DEV: 14 = 6 false-stop winners + 8 true-failure losers
- REF: 10 = 2 false-stop winners + 8 true-failure losers

## Fixed post-alarm observation windows

Observe completed 5m bars only after the +60m alarm, at:
- +15m
- +30m
- +45m
- +60m

relative to the alarm.

Thus the latest anatomy snapshot is detector+120m, still before the frozen +180m endpoint.

## Fixed recovery features

Continuous, higher = stronger recovery:
1. `close_progress` = (snapshot close - alarm close) / wall_distance
2. `mfe_from_alarm` = (max post-alarm high - alarm close) / wall_distance
3. `recovery_ratio` = (snapshot close - alarm close) / (entry - alarm close), only when alarm close < entry
4. `up_slope_3` = 3-bar close slope at snapshot / wall_distance

Continuous, lower = healthier:
5. `mae_from_alarm` = (alarm close - min post-alarm low) / wall_distance

Binary recovery events:
6. `close_above_alarm`
7. `touch_reclaim_entry`
8. `close_reclaim_entry`
9. `touch_reclaim_wall`
10. `close_reclaim_wall`
11. `close_break_pre15_high` = snapshot close > highest completed close in the 15m immediately before/alarm bar
12. `no_new_low_after_alarm` = post-alarm minimum low >= alarm-bar low

All levels are known at the alarm.

## DEV mechanism screen

Because the alarm cohort is small, S6D-L does not use a standard validation gate.

A binary recovery event is a **DEV_MECHANISM_CANDIDATE** if:
- DEV false-stop winner n >= 5;
- event occurs in >=50% of false-stop winners;
- event occurs in <=25% of true-failure losers;
- winner-minus-loser recovery-rate gap >=40 percentage points.

A continuous feature is a **DEV_MECHANISM_CANDIDATE** if:
- DEV false-stop winner n >=5 and loser n >=8;
- recovery AUC >=0.70.
For `mae_from_alarm`, score is negated so higher always means healthier/recovery.

## REF directional check

REF is descriptive only because only two false-stop winners exist.

A DEV candidate is `REF_DIRECTIONALLY_CONSISTENT` if:
- for binary events, false-winner rate > loser rate;
- for continuous features, recovery AUC >0.50.

No candidate is promoted to a trading rule in S6D-L.

## Gate

- >=1 DEV mechanism candidate with REF directional consistency ->
  `RECOVERY_MECHANISM_CANDIDATE_FOUND`
- otherwise ->
  `NO_STABLE_RECOVERY_MECHANISM_FOUND`

A positive result permits a separately preregistered S6E-L recovery-test rule. It does not itself authorize an exit rule.

No EMA/Fibonacci, TP, WR optimization, PF, expectancy, leverage, or PnL optimization.
