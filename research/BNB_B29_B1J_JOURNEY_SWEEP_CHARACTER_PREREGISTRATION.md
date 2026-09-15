# BNB B29-B1J — Journey → Sweep → Reclaim Character Discovery — Preregistration

## Scientific identity
`B29-B1J-v1`

This is a new development identity inspired by the valid B29-B1 finding that `SWEEP_LOW_RECLAIM -> LONG` was temporally stable but missed the frozen 55% primary-hit gate (8,084 events; pooled +60m hit 54.13%). B1J is **not** a rescue or validation of B1. It asks a different question: which *causally-known journey before the sweep plus reclaim anatomy* separates high-quality low sweeps from generic low sweeps?

No entry, TP, SL, leverage, fees, PnL, position sizing, or live orders are part of B1J.

## Immutable source
B1J must consume accepted B29-A1 artifact `10336102957` directly, specifically `BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz` with SHA256:

`eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`

Expected rows: 229,267. First decision: 2020-02-10 14:15 UTC. Last decision: 2026-08-26 00:00 UTC.

Do not rebuild the accepted A1 history from a fresh external download. All previous-row and forward-horizon calculations must require exact 15-minute timestamp continuity and must not cross any known A1 history gap.

## Base event
Use the **same causal base event and same 60-minute same-family cooldown as B1-v1**:

`SWEEP_LOW_RECLAIM -> LONG`, where accepted A1 `sweep_low_60 == 1` on the completed decision bar.

The event bar is fully closed before the event is known.

Primary diagnostic horizon is fixed at **+60 minutes**. Auxiliary robustness horizons remain **+15, +30, +120, +360 minutes**. Directional hit means forward close-to-close return > 0 for LONG.

## Causal character axes
Every axis must be known at the completed event timestamp. Previous-state axes require an exact `t-15m` predecessor.

### Previous 15-minute state axes
1. `pre_path_state`: accepted A1 `path_state` at t-15m.
2. `pre_structure_state`: `structure_state` at t-15m.
3. `pre_trend_state`: `trend_state` at t-15m.
4. `pre_vol_state`: `vol_state` at t-15m.
5. `pre_efficiency_state`: `efficiency_state` at t-15m.
6. `pre_range_state`: `range_state` at t-15m.

### Approach momentum axis
From `disp_atr_60` at t-15m:
- `DOWN`: <= -0.35
- `FLAT`: > -0.35 and < +0.35
- `UP`: >= +0.35

### Low-liquidity journey axis
Look only at exact 15-minute predecessors inside the prior 60 minutes, excluding the event bar:
- `BREAK_BEFORE`: immediately preceding t-15m bar has `break_low_60 == 1`.
- `REPEAT_SWEEP`: otherwise, any exact predecessor in t-60m..t-15m has `sweep_low_60 == 1`.
- `CLEAN_APPROACH`: neither condition above.

If the required exact predecessor path is incomplete, the event is not eligible for B1J.

### Event-bar reclaim anatomy
From the completed sweep/reclaim event bar:

`reclaim_strength` from `close_location`:
- `LOW`: <= 0.00
- `MID`: > 0.00 and < 0.50
- `HIGH`: >= 0.50

`reclaim_body` from `body_range`:
- `LOW`: < 0.33
- `MID`: >= 0.33 and < 0.66
- `HIGH`: >= 0.66

`reclaim_range` from `true_range / atr_360`:
- `QUIET`: < 0.80
- `NORMAL`: >= 0.80 and <= 1.50
- `EXPANDED`: > 1.50

No clock, WIB hour, session, day-of-week, era label, future outcome, or execution variable may be used as a rule clause.

## Rule grammar
A character rule is an AND conjunction of **1, 2, or 3 equality clauses** drawn from **distinct axes** above. Example form only:

`pre_path_state == DOWN_PAUSE AND low_journey == CLEAN_APPROACH AND reclaim_strength == HIGH`

The example is not preferred or promoted; it only illustrates syntax.

Enumerate the complete finite grammar deterministically. No outcome-driven manual filter additions/removals are allowed after the result is observed.

## Development and reference periods
### Character discovery/development
- 2022
- 2023
- 2024

Only these years may rank/select candidate rules.

### Reference validation
After development selection is frozen, evaluate selected rules unchanged on:
- 2025
- 2026 through accepted A1 cutoff

2025/2026 are **reference validation, not untouched OOS**, because B1 already exposed the unconditional base-event outcome in those eras. Final ready-to-trade proof would still require new future shadow data after all rules/execution are frozen.

## Development eligibility and promotion gate
For a rule to enter the ranked development shortlist it must satisfy all:
- pooled development N >= 240;
- N >= 60 in each of 2022, 2023, 2024;
- pooled +60m hit >= 58.0%;
- each development year +60m hit >= 55.0%;
- Wilson 95% lower bound on pooled +60m hit > 55.0%;
- pooled median signed +60m return > 0;
- at least 3 of 4 auxiliary horizons have directional hit >= 54.0%;
- max development-year share <= 45%;
- character uses <=3 clauses.

Multiple-testing control: for every rule that satisfies the frozen sample-size requirements (pooled development N >=240 and N>=60 in each development year), compute the **one-sided exact binomial p-value for directional hit >50%** and apply Benjamini-Hochberg FDR at q=0.05 across that complete tested-rule set. A promoted rule must also be FDR-significant.

Rank eligible development rules deterministically by:
1. highest worst development-year +60m hit;
2. highest pooled Wilson lower bound;
3. highest pooled +60m hit;
4. fewer clauses;
5. larger pooled N;
6. lexical rule string.

Promote at most **3** rules to reference validation. To avoid near-duplicate rules dominating, after selecting a rule, suppress any later rule whose matched development event set has Jaccard overlap > 0.80 with an already selected rule.

## Reference validation gate
A selected rule passes B1J only if, unchanged:
- 2025 N >= 50 and +60m hit >= 55.0%;
- 2026 N >= 40 and +60m hit >= 55.0%;
- combined 2025+2026 +60m hit >= 56.0%;
- combined reference median signed +60m return > 0;
- at least 3 of 4 auxiliary reference horizons have directional hit >= 54.0%;
- pooled 2022–2026 +60m hit >= 57.0%;
- pooled 2022–2026 Wilson 95% lower bound > 55.0%;
- every one of the five eras has +60m hit > 50.0%;
- max five-era share <= 35%.

At least one of the maximum-three frozen candidates must pass every reference gate for status `BNB_B29_B1J_JOURNEY_CHARACTER_PASS`.

Otherwise status is `BNB_B29_B1J_JOURNEY_CHARACTER_REJECT`.

Tooling/integrity failure before valid evaluation is `BNB_B29_B1J_DATA_TOOLING_FAILURE` and is not a scientific rejection.

## Stop rule
After a valid B1J-v1 result, do not rescue it by:
- lowering any gate;
- changing the primary horizon;
- adding clock/session filters;
- changing cut points after observing outcomes;
- allowing >3 clauses;
- searching new axes and calling them B1J-v1;
- selecting a reference winner that was not frozen from the development shortlist;
- proceeding to entry/TP/SL from a rejected rule.

Any materially new grammar or feature family requires a new scientific identity.

No live orders are authorized by this phase.