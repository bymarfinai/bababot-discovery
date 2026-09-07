# SOL LONG 15:00 UTC H05 Pre-warning MFE — A61 Preregistration

## Purpose

A52/A55 established that post-breakout H05 weakness carries real failure information. A53, A56, and A59 showed why acting on every H05 warning is economically dangerous: too many eventual winners are cut, and lost winner payoff can exceed rescued loser payoff. A54/A57/A58/A60 did not produce a robust secondary or intrabar confirmation.

A61 tests one new winner-preservation hypothesis:

> Among the frozen first POST_H05 warning cohort, eventual failures had achieved less favorable extension before the warning became known than eventual E40 recoveries.

A61 is anatomy/revalidation only. It does not change position size, exits, or live Baba Bot.

## Frozen parent/cohort

- SOLUSDT LONG, 15:00 UTC / R360.
- Parent: frozen A20/A25B `E0_RESTING_H -> E40` under A2/A17 mechanics.
- Warning cohort: exact A53 `G2_POST_H05` first live warning used by A54.
- Expected warning cohort: Development 219, External 148, Reference Validation 138.
- Primary outcomes: `FAILED_BREAK` versus `RECOVER_E40`; unresolved TIME is diagnostic only.

## One frozen feature

`prewarning_mfe_R = (max completed 5m high from breakout-confirmation bar through warning bar inclusive - H) / R`

All included bars are completed by `warning_known_ts = warning_ts + 5m`; therefore the feature is causal at the same instant the H05 warning becomes actionable. If breakout confirmation occurred before entry, measurement starts at entry. The warning bar is included because its OHLC is known at warning close.

No close/body/range/duration feature, composite score, alternate start point, or feature sweep is permitted.

## Frozen threshold derivation

Development only:
1. compute the Development FAILED_BREAK median prewarning_mfe_R;
2. compute the Development RECOVER_E40 median;
3. require fail median < target median;
4. set one threshold `T = (median_fail + median_target) / 2`;
5. freeze `LOW_MFE = prewarning_mfe_R <= T`.

External and Reference Validation cannot influence T. No percentile sweep, rounding grid, neighbouring threshold, or OOS retuning is allowed.

## Reconciliation gate

- exact A54 cohort counts reconcile;
- every cohort event maps to exactly one frozen parent trade and one warning timestamp;
- no missing/negative/non-finite MFE;
- Development support >=180 fail and >=30 target; External >=100/25; Reference >=100/25;
- T finite, positive, and strictly between Development medians.

Failure => `SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_RECONCILIATION_FAIL`.

## Development gate

LOW_MFE must satisfy ALL:
- fail hit rate > target hit rate;
- gap >= 15 percentage points;
- hit-rate ratio >= 1.35x;
- fail hit rate >= 50%;
- same bad direction in >=5 of 6 Development blocks having >=10 fail and >=3 target observations.

## OOS replication gate

Only if Development passes, BOTH External and Reference Validation must satisfy:
- fail hit > target hit;
- gap >= 10 percentage points;
- ratio >= 1.20x;
- fail hit >= 45%;
- support minima above.

## Interpretation

If supported, A61 authorizes exactly one next experiment: an executable selective H05 guard using the same frozen T, exiting at the next 5m open only when `G2_POST_H05 AND LOW_MFE`. That next experiment must test raw and 5bps economics versus the untouched parent and versus A53 G2.

If A61 fails, do not rescue it by moving T or changing the MFE window.

## Decision states

- `SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_SUPPORTED_FOR_EXECUTABLE_TEST`
- `SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_DEVELOPMENT_ONLY`
- `SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_INCONCLUSIVE`
- `SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.
