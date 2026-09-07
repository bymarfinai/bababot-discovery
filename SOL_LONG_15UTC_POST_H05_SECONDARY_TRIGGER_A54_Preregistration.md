# SOL LONG 15:00 UTC Post-H05 Secondary Trigger Anatomy — A54 Preregistration

## Purpose

A52 established `POST_H05` as a replicated warning state and A53 showed that a hard exit on the first `POST_H05` is too blunt: it improves Development economics but sacrifices too much parent-winner PnL in External and Reference Validation.

A54 asks the narrower structural question:

> Once a live 15UTC parent has already entered `POST_H05`, what is the earliest **subsequent causal state** that distinguishes an eventual E40 target from an eventual structural `FAILED_BREAK`?

A54 is anatomy only. It does not change the parent exit and does not scan price thresholds.

## Frozen parent

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: `H + 0.40R`
- Parent mechanics: exact A2/A17 simulator
- Partitions: Development, External, Reference Validation
- Source concept: exact A53 `G2_POST_H05` warning logic

## Frozen cohort

A trade enters the A54 cohort at the first completed candle that, while the trade is still live after breakout confirmation, satisfies:

`H < close <= H + 0.05R`

The warning candle itself is not a secondary trigger; it is time zero for A54.

### Technical cohort audit correction frozen before A54 results

The first A54 runner attempt exposed that `parent_won == True` is not identical to `TARGET`: the frozen A2/A53 accounting defines a winner by positive PnL, so a small number of positive-PnL parents finish by `FAILED_BREAK` or `TIME`.

A separate technical audit of the already-frozen A53 `G2_POST_H05` output was completed **before any valid A54 result existed**. It established the exact 505-row composition:

- Development: 219 total = **31 TARGET + 184 structural FAILED_BREAK + 4 TIME-unresolved**
- External: 148 total = **32 TARGET + 113 structural FAILED_BREAK + 3 TIME-unresolved**
- Reference Validation: 138 total = **29 TARGET + 107 structural FAILED_BREAK + 2 TIME-unresolved**
- Total: 505 = **92 TARGET + 404 structural FAILED_BREAK + 9 TIME-unresolved**

The 404 structural failed-break rows include **6 positive-PnL FAILED_BREAK parents** (2 Development, 3 External, 1 Reference Validation). They remain `FAILED_BREAK` because A54 labels mechanism, not PnL sign.

The 9 `TIME` rows are quarantined as `UNRESOLVED_TIME`: they remain reported and must reconcile, but they are excluded from the primary TARGET-vs-FAILED_BREAK discrimination because neither terminal event occurred within the frozen parent horizon.

Thus the primary comparison cohort is fixed at:

- Development: **215 = 31 TARGET + 184 FAILED_BREAK**
- External: **145 = 32 TARGET + 113 FAILED_BREAK**
- Reference Validation: **136 = 29 TARGET + 107 FAILED_BREAK**
- Total primary: **496 = 92 TARGET + 404 FAILED_BREAK**

No threshold, candidate, Development gate, OOS gate, or selection rule is changed by this technical correction.

## Labels

Labels are future-defined outcomes used only for research comparison:

- `RECOVER_E40`: frozen parent reaches E40 (`parent exit_reason == TARGET`).
- `FAILED_BREAK`: frozen parent later records its structural post-break invalidation close `<= H`, regardless of whether realized parent PnL happens to remain positive.
- `UNRESOLVED_TIME`: frozen parent reaches the time horizon after POST_H05 without E40 or structural failed-break. Quarantined from primary discrimination.

No future-defined label may be used as a live feature.

## Frozen secondary-state grid

No neighboring price threshold may be introduced. Every state uses only the pre-existing A51/A52 levels:

- `H`
- `H + 0.05R`
- `H + 0.10R`

Fixed observation horizons after the POST_H05 warning close are:

- +5m
- +10m
- +15m
- +30m

For each primary-cohort trade and horizon, classify the trade into exactly one causal state using information available by that horizon:

1. `TERMINAL_FAIL_BY_T`: a completed close `<= H` has already occurred before or at the horizon.
2. `TARGET_BY_T`: E40 has already been reached before or at the horizon.
3. `ALIVE_H05`: still live and latest completed close satisfies `H < close <= H+0.05R`.
4. `ALIVE_H10`: still live and latest completed close satisfies `H+0.05R < close <= H+0.10R`.
5. `ALIVE_ABOVE_H10`: still live and latest completed close `> H+0.10R`.

Target/failure precedence must match the frozen parent simulator.

## Frozen path diagnostics after POST_H05

At each fixed horizon, report only causal path information available by then:

- latest close location in R units
- running high extension above H in R
- running low depth below H in R
- count of completed closes in `H < close <= H+0.05R`
- count of completed closes in `H+0.05R < close <= H+0.10R`
- count of completed closes `> H+0.10R`
- whether a close `> H+0.10R` has occurred by the horizon
- whether the high has touched `H+0.10R` by the horizon
- first escape-close time above `H+0.05R`
- first strong escape-close time above `H+0.10R`
- first terminal-fail time `<= H`

These diagnostics are descriptive. No continuous-feature threshold is selected in A54.

## Fixed actionable secondary-trigger candidates

A54 may evaluate only these predeclared single-state candidates, all requiring the trade to still be alive at the observation point:

- `C1_STILL_H05_5M`: at +5m, latest completed close remains in `H < close <= H+0.05R`.
- `C2_NOT_ABOVE_H10_5M`: at +5m, still alive and latest close is `<= H+0.10R`.
- `C3_NO_CLOSE_ABOVE_H10_10M`: by +10m, still alive and no completed close `> H+0.10R` has occurred.
- `C4_STILL_H05_10M`: at +10m, still alive and latest close remains in `H < close <= H+0.05R`.
- `C5_NO_CLOSE_ABOVE_H10_15M`: by +15m, still alive and no completed close `> H+0.10R` has occurred.

A candidate that occurs only after terminal failure is not actionable and must be excluded.

No combinations of candidates are allowed in A54.

## Development discovery gate

For each fixed actionable candidate, compare eventual `FAILED_BREAK` versus `RECOVER_E40` within the full **primary Development POST_H05 cohort** (184 fail / 31 target).

A candidate becomes Development-supported only if all are true:

1. failed-break hit rate >= 30%
2. failed-break hit rate exceeds target hit rate by >= 20 percentage points
3. failed-break / target hit-rate ratio >= 1.50
4. same direction in at least 5 of 6 fixed Development half-year blocks with both outcome cohorts present
5. median lead from candidate knowledge to terminal failed-break knowledge >= 5 minutes among failed trades hit by the candidate

The denominator is the full primary POST_H05 outcome cohort, not only trades surviving to the candidate horizon.

## OOS replication gate

Only Development-supported candidates may be evaluated for confirmation.

A candidate replicates only if independently in both External and Reference Validation:

- failed-break hit rate > target hit rate
- absolute gap >= 15 percentage points
- hit-rate ratio >= 1.25
- failed-break hit rate >= 20%

No OOS retuning is permitted.

## Earliest trigger selection

If more than one candidate replicates, A54 designates the **earliest observation horizon** as the primary secondary-trigger family. Within the same horizon, choose the candidate with the larger Development absolute separation; ties choose the lower target hit rate.

This selection rule is frozen before results.

## Required reconciliation

A54 is invalid unless:

- parent trade counts remain 601 / 281 / 337
- total POST_H05 cohort counts reconcile exactly to 219 / 148 / 138
- mechanism labels reconcile exactly to:
  - Development 31 TARGET / 184 FAILED_BREAK / 4 UNRESOLVED_TIME
  - External 32 / 113 / 3
  - Reference Validation 29 / 107 / 2
- total primary cohort = 496 and quarantined unresolved = 9
- warning timestamp is causal and precedes any candidate timestamp
- no candidate is credited after target or terminal failure

## Decision

Possible statuses:

- `SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_SUPPORTED_FOR_A55`
- `SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_INCONCLUSIVE`

A54 cannot authorize an exit change. If supported, A55 must simulate only the frozen primary secondary trigger as a next-open executable guard against the untouched parent, including raw and 5bps economics.

Research only. Live Baba Bot remains unchanged.
