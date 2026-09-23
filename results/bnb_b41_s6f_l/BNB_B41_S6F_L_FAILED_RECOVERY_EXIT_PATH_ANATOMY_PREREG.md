# BNB B41-S6F-L — Failed-Recovery Exit Path Anatomy Preregistration

## Objective

Study the price path after a LONG trade has:
1. fired the frozen S6C-L `R4_60_2OF3_Q85` alarm at detector+60m, and
2. failed the frozen S6E-L `E1_45M_WALL_RECLAIM` recovery test at detector+105m.

S6F-L does **not** create an exit rule. It asks whether a failed-recovery trade typically:
- continues directly lower,
- bounces shortly after failure confirmation,
- retests the failure-confirmation price,
- retests/reclaims Q80,
- or gives a better executable exit before detector+180m.

## Frozen parents

- S6D-L signature: `fc4ec7581c282e2f61f578df00ace715451381b92d15c82453d56f369e33281a`
- S6E-L signature: `953f2a9a1a721fbe0c8fcefcaa73feb4470ae72e7407b9e4cb14aab4f4b7a5e8`
- Failed-recovery cohort is exactly the trades where E1_45M_WALL_RECLAIM exits.
- Expected parity:
  - DEV: 7 failed recoveries = 1 baseline winner + 6 baseline losers.
  - REF: 7 failed recoveries = 0 baseline winners + 7 baseline losers.

Because the cohort is small, S6F-L is mechanism discovery with REF directional checking only.

## Failure anchor

- failure confirmation timestamp = detector +105m.
- failure close = completed 5m close at detector+105m.
- Q80 wall is frozen from the parent setup.
- remaining frozen horizon = detector+180m, i.e. 75m after failure confirmation.

## Fixed post-failure checkpoints

Observe completed 5m closes at:
- +5m
- +10m
- +15m
- +30m
- +45m
- +60m

after failure confirmation.

No checkpoint after +60m is used because only 15m would remain before the frozen endpoint.

## Fixed path measurements

For each checkpoint:
1. `close_delta_from_failure` = (checkpoint close - failure close) / wall_distance
2. `mfe_from_failure` = (max post-failure high - failure close) / wall_distance
3. `mae_from_failure` = (failure close - min post-failure low) / wall_distance
4. `wait_outcome` = (checkpoint close - entry) / wall_distance
5. `wait_improve_vs_immediate` = wait_outcome - immediate failure-close outcome
6. `wait_improve_vs_endpoint` = wait_outcome - frozen +180m baseline outcome
7. `close_above_failure`
8. `touch_wall_after_failure`
9. `close_wall_after_failure`

Additionally over the full remaining +75m:
- max favorable bounce from failure close;
- max adverse continuation from failure close;
- first completed close above failure close;
- first touch of Q80 wall;
- first completed close back above Q80 wall;
- time to each event if it occurs.

## Fixed executable bounce probes

These are anatomy probes, not selectable exits in S6F-L.

A. `FIRST_CLOSE_ABOVE_FAILURE_30`
- within 30m after failure confirmation, first completed 5m close above the failure close;
- record that actual close and normalized outcome.

B. `FIRST_WALL_TOUCH_60`
- within 60m after failure confirmation, first bar whose high reaches Q80 wall;
- hypothetical executable limit exit at the frozen wall price.

C. `FIRST_WALL_CLOSE_60`
- within 60m, first completed close at/above Q80 wall;
- exit at actual completed close.

For each probe, report fill/event rate and outcome improvement vs immediate failure exit and vs frozen +180m endpoint.

## DEV bounce mechanism screen

Evaluate baseline losers only.

A fixed-wait checkpoint is a DEV_BOUNCE_CANDIDATE if:
- DEV loser n >=6;
- median wait improvement vs immediate >0;
- >=50% of DEV losers have wait improvement vs immediate >0;
- median wait improvement vs endpoint >0.

An executable bounce probe is a DEV_BOUNCE_CANDIDATE if:
- DEV loser n >=6;
- event/fill rate >=50%;
- among filled events, median improvement vs immediate >0;
- among filled events, median improvement vs endpoint >0.

## REF directional check

A DEV candidate is REF_DIRECTIONALLY_CONSISTENT if:
- REF loser n >=6;
- for fixed waits: median improvement vs immediate >0 and median improvement vs endpoint >0;
- for event probes: fill rate >=40%, median improvement vs immediate >0, and median improvement vs endpoint >0.

No candidate becomes a trading rule in S6F-L.

## Gate

- >=1 DEV bounce candidate with REF directional consistency ->
  `FAILED_RECOVERY_BOUNCE_MECHANISM_FOUND`
- otherwise ->
  `NO_STABLE_FAILED_RECOVERY_BOUNCE_MECHANISM`

A positive result permits a separately preregistered S6G-L exit-timing rule.
No TP, EMA/Fibonacci, leverage, PF, expectancy, fees/slippage optimization, or PnL optimization.
