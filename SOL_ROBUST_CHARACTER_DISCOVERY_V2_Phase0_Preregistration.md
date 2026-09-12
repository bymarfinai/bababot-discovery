# SOL Robust Character Discovery v2 — Phase 0 Preregistration

Status: PREREGISTERED BEFORE ANY RCD-v2 CANDIDATE SEARCH

## 1. Research question

How can we discover SOLUSDT LONG characters that are robust by construction rather than first maximizing pooled backtest performance and later rescuing failing candidates with post-hoc filters?

RCD-v2 explicitly changes the search objective from **best backtest** to **stable economic region**.

The discovery target is not a single optimized timestamp/rule/hold tuple. A candidate character must represent a repeatable market state whose economics remain acceptable across calendar years, neighboring parameter settings, multiple intrahour anchors where applicable, and predeclared absolute-scale regimes.

## 2. Prior evidence and contamination boundary

Prior SOL work exposed Development and OOS behavior for H04/H15/H22/H23. Those four setups are retained as methodological failure cases and are NOT rescue targets in RCD-v2.

Known lesson from H04 A1: relative structure can remain syntactically similar while absolute movement scale compresses materially. Therefore RCD-v2 must model both relative shape and absolute scale during discovery instead of adding scale only after OOS failure.

RCD-v2 will use only the Development partition for candidate generation, ranking, and internal robustness qualification:

- Development: 2022-01-01 <= t < 2025-01-01

The following remain sealed during candidate discovery and freeze:

- External: 2020-01-01 <= t < 2022-01-01
- Reference Validation: 2025-01-01 <= t < 2026-07-30
- August 2026: 2026-08-01 <= t < 2026-08-26

Because prior research has already exposed some aggregate OOS behavior, later RCD-v2 confirmation on External/Reference Validation must be described as **secondary historical confirmation**, not pristine untouched OOS. Truly fresh validation requires forward data after the existing dataset end.

## 3. Fixed trading mechanics for character discovery

Character discovery must not optimize execution mechanics.

- Pair: SOLUSDT
- Side: LONG only
- Source timeframe: 5m
- Candidate decision times: quarter-hour grid only (minute 00/15/30/45)
- Entry: exact 5m open at candidate decision time
- Exit: exact-open time exit after frozen hold
- Notional: USD 500
- Round-trip fee: USD 0.75
- No TP/SL
- No trailing stop
- No Fibonacci entry adjustment
- No limit-entry rescue
- No intrabar look-ahead

Hold is treated as a structural horizon, not a final execution optimization. Predeclared hold grid:

- 60m, 120m, 240m, 360m, 720m, 960m

## 4. Search-space philosophy

RCD-v2 does NOT begin by splitting the market into 24 independent hourly habitats.

Time-of-day is a context feature. A robust state may appear preferentially at one clock, but the state definition must be discovered from market structure first rather than from an hour-first partition.

The permitted feature families are deliberately restricted to interpretable causal market-state variables.

### 4.1 Relative shape family

For predeclared lookbacks 15m, 30m, 60m, 120m, 240m, 360m:

- efficiency / directional efficiency
- realized high-low range
- signed drive return
- extension from recent range midpoint / boundaries where available causally
- percentile rank of efficiency within trailing causal history
- percentile rank of realized range within trailing causal history
- percentile rank of extension / drive where already implemented causally

### 4.2 Absolute scale family

Absolute scale must be present during discovery, not added after failure.

Permitted causal absolute-state variables:

- raw realized range over structural lookback
- trailing 24h realized range
- trailing 72h realized range
- trailing 7d realized range when data support is causal
- volatility expansion/compression ratio versus a longer trailing baseline

Absolute-state discretization must use Development-derived quantile boundaries only. No arbitrary threshold scanning is permitted.

Default quantization for continuous scale variables:

- LOW: <= Development q33
- MID: > q33 and <= q67
- HIGH: > q67

Where a ratio is used, the same Development-only quantile rule applies.

### 4.3 Directional / broader-context family

Permitted causal variables:

- trailing 24h return
- trailing 72h return
- trailing 7d return
- location within trailing 24h range
- location within trailing 72h range
- location within trailing 7d range

These must also use Development-derived quantile/state boundaries where discretization is required.

### 4.4 Time context

Permitted time context:

- UTC hour
- quarter-hour anchor 00/15/30/45
- weekday

Time context may identify concentration or preference, but candidates that require one isolated quarter-hour anchor with no neighboring support receive a robustness penalty and cannot be called broad SOL characters.

## 5. Candidate construction constraints

To control combinatorial overfitting, candidate states must be shallow and interpretable.

Allowed candidate complexity:

- one structural/shape condition alone, OR
- one structural/shape condition + one absolute-scale condition, OR
- one structural/shape condition + one broader-context condition, OR
- one structural/shape condition + one absolute-scale condition + one broader-context condition

Maximum conjunction depth: 3 state clauses, excluding time context and hold.

Forbidden:

- arbitrary numeric threshold scans
- unconstrained Boolean trees
- feature subsets selected using External/Reference Validation
- thresholds defined from OOS behavior
- post-hoc deletion of bad years/anchors
- runner-up substitution after historical confirmation failure

## 6. Internal Development robustness tests

A candidate may not qualify from pooled 2022-2024 economics alone.

For every candidate, calculate pooled Development plus separate 2022, 2023, 2024 economics:

- N trades
- win rate
- net PnL
- expectancy / trade
- profit factor
- max drawdown
- maximum loss streak

### 6.1 Minimum pooled gate

A candidate must satisfy all:

- N >= 180 across Development
- net PnL > 0
- expectancy > 0
- PF >= 1.20
- max loss streak <= 10

WR is reported but is not a standalone primary gate because payoff distribution matters.

### 6.2 Calendar consistency gate

For each of 2022, 2023, 2024:

- N >= 40
- net PnL > 0
- expectancy > 0
- PF >= 1.05

All three years must pass. No two-of-three rescue.

### 6.3 Concentration guard

No single calendar year may contribute more than 65% of total Development net PnL.

No single quarter-hour anchor may contribute more than 60% of Development net PnL unless at least one adjacent anchor also has positive expectancy and PF >= 1.05.

This guard is intended to reject one-anchor accidents and one-year jackpots.

## 7. Parameter-neighborhood / plateau robustness

A robust character should occupy an economic region rather than a single sharp optimum.

For each candidate center, evaluate predeclared neighboring lookbacks and holds without changing the state semantics.

Lookback neighborhood uses the ordered grid:

15, 30, 60, 120, 240, 360 minutes.

Hold neighborhood uses:

60, 120, 240, 360, 720, 960 minutes.

For a center point to pass the plateau test:

- at least 3 evaluated neighboring parameter points including the center must have positive expectancy
- at least 2 of those must have PF >= 1.10
- median neighborhood expectancy must be > 0
- no single point may contribute more than 55% of the neighborhood's summed positive net PnL

A candidate whose center is excellent but immediate neighbors collapse is classified as SPIKE_OPTIMUM and is rejected from robust-character freeze.

## 8. Clock stability test

Clock is context, not initial partition.

For candidates with enough occurrences across anchors, report economics by quarter-hour anchor and UTC hour.

A candidate is penalized for clock fragility if:

- only one quarter-hour anchor has positive expectancy, or
- removing its best anchor flips pooled Development expectancy <= 0.

Preferred robust candidates retain positive expectancy after excluding their single best anchor.

This is a scoring preference; however a candidate failing the concentration guard in Section 6.3 is rejected.

## 9. Regime stability test

Absolute scale is part of the candidate definition when required.

For every candidate, report economics across Development-defined LOW/MID/HIGH absolute-scale regimes for the principal scale variable even if the candidate itself does not gate on scale.

Two acceptable robust forms exist:

1. BROAD_REGIME character: positive expectancy in at least 2 of 3 scale regimes and pooled gates pass.
2. CONDITIONAL_REGIME character: the regime state is explicitly part of the preregistered candidate definition and all calendar/plateau gates pass within that condition.

A candidate discovered without a regime clause may NOT add one after historical confirmation failure and retain the same confirmatory status.

## 10. Robustness score

Hard gates decide eligibility first. Score ranks only candidates that pass all hard gates.

RCD-v2 Robustness Score = 100 points:

- 25 pts calendar consistency
- 20 pts parameter-neighborhood / plateau stability
- 15 pts pooled economic quality
- 15 pts clock / anchor stability
- 15 pts regime stability
- 10 pts sample strength / concentration quality

Score construction must be monotonic and documented in code before candidate results are inspected. Score components may be normalized against fixed gate anchors, but must not use OOS data.

The highest raw PnL is NOT automatically the highest-ranked candidate.

## 11. Candidate freeze rule

After Development discovery completes:

- retain at most 5 characters
- prefer structurally distinct characters over near-duplicates
- freeze exact state clauses, lookback, hold, clock treatment, and all Development-derived quantile boundaries
- persist candidate definitions before any External/Reference Validation evaluation

No more than 5 candidates may be historically confirmed. No substitution after confirmation begins.

## 12. Historical confirmation stage

External and Reference Validation are exposed only after candidate freeze.

Because these eras have been viewed in prior SOL research, labels are:

- HISTORICAL_CONFIRMATION_STRONG
- HISTORICAL_CONFIRMATION_PARTIAL
- HISTORICAL_CONFIRMATION_FAIL

They are not described as pristine OOS.

Frozen candidate mechanics and thresholds cannot be changed during confirmation.

August 2026, if used, is SHADOW_ONLY because sample size is expected to be small.

## 13. Stop rules

If zero candidates pass Development robustness gates:

- do not loosen gates in the same experiment
- do not expose OOS to rescue discovery
- diagnose which robustness dimension is failing
- create a new preregistered generation only if methodology changes are justified

If candidates pass Development but fail historical confirmation:

- record failure anatomy
- do not add filters and call the same candidate confirmed
- any revised candidate becomes a new generation with secondary/post-hoc status until fresh forward data exists

## 14. Phase 1 implementation target

Phase 1 will build the causal state table and evaluate interpretable candidate families under the gates above.

Required persisted outputs:

- causal state feature table summary
- candidate universe manifest
- all candidate economics
- year-by-year economics
- anchor/hour economics
- regime economics
- parameter-neighborhood results
- robustness score breakdown
- rejected-candidate reasons
- frozen finalist manifest (0 to 5 candidates)
- run log and status file

## 15. Scientific success criterion

Phase 1 succeeds scientifically even if zero finalists survive.

The experiment is considered methodologically successful if it answers whether SOL contains a Development-era character region that is simultaneously economically positive, calendar-consistent, plateau-like, non-concentrated, and regime-aware under rules fixed before candidate search.

The North Star is:

> Discover a SOL market character that is robust by construction, not repaired into robustness after seeing failure.
