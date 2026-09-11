# SOL Robustness-First Discovery V2 — Preregistration

## Objective

Discover SOLUSDT LONG characters that are not merely strong in one historical slice, but remain economically strong across chronological regimes while preserving high headline performance.

The objective is **maximize performance subject to frozen robustness constraints**. This is not a low-performance stability search.

## Research universe

- Research window: **2022-01-01 UTC through 2026-07-30 UTC (exclusive end)**.
- 2022-2024 were the original Development years.
- 2025 through 2026-07-30 have already been exposed by the prior four-winner Reference Validation and therefore are now part of the research universe, not pristine OOS.
- **August 2026 remains unopened and must not be loaded, scored, ranked, or used for tie-breaking in this experiment.**
- Direction: LONG only.
- Fixed notional: $500.
- Round-trip fee: $0.75.
- Entry/exit: exact 5m-open, fixed time hold.
- Causal state definitions remain identical to the frozen SOL economic-first engine.

## Candidate grammar

The existing simple 90-rule grammar is retained; no new multi-factor rule proliferation is allowed.

For each of 24 UTC hours:
- four quarter-hour anchors;
- lookbacks: 15, 30, 60, 120, 240, 360 minutes;
- holds: 60, 120, 240, 360, 720, 960 minutes;
- 90 causal character rules.

Total raw candidate universe: **24 × 4-anchor hourly habitats × 6 × 6 × 90 = 77,760 hourly candidates**.

A candidate is the pooled four-anchor hourly habitat for one fixed rule/lookback/hold.

## Frozen hard performance gate

A candidate must satisfy all:

- pooled raw N >= 250;
- pooled WR >= 60.00%;
- pooled net > 0;
- pooled expectancy >= +$1.50/trade;
- pooled PF >= 1.70;
- pooled max drawdown <= $175;
- pooled max loss streak <= 8.

These thresholds are not relaxed if no candidate passes.

## Frozen chronological regime gate

Evaluate five chronological folds separately: 2022, 2023, 2024, 2025, and 2026 through 2026-07-30.

Every fold must satisfy:

- N >= 20;
- WR >= 55.00%;
- positive net and expectancy;
- PF >= 1.15.

Additionally:

- at least 3 of the 5 folds must have WR >= 60.00%.

No averaging may rescue a failed fold.

## Frozen within-hour anchor gate

For each of the four quarter-hour anchors, an anchor is evaluable at N >= 25 and supportive when:

- WR >= 55%;
- positive net and expectancy;
- PF >= 1.20;
- DD <= $150;
- max loss streak <= 10.

Candidate requirement:

- at least 3 evaluable anchors;
- at least 3 supportive anchors.

## Overlap-adjusted effective-N gate

Raw N is not treated as independent when trade holding intervals overlap.

Selected trades are sorted chronologically and merged into overlapping exposure clusters. Each cluster counts as one effective observation.

Candidate requirement:

- effective exposure clusters >= 100;
- effective-N / raw-N >= 0.35.

This penalizes apparently large sample sizes generated mainly by overlapping quarter-hour positions.

## Parameter-neighborhood stability gate

After the preceding gates pass, inspect only the immediate same-hour/same-rule parameter neighbors:

- previous/next lookback with the same hold;
- previous/next hold with the same lookback.

A neighbor is soft-supportive when, over the same research universe:

- WR >= 56%;
- expectancy >= +$0.50/trade;
- PF >= 1.25;
- net > 0;
- at least 4 of 5 chronological folds have positive expectancy.

Candidate requirement:

- at least 2 available immediate neighbors;
- at least 2 soft-supportive neighbors.

This prevents selection of isolated parameter spikes.

## Ranking

Robustness gates are filters, not the ranking objective.

Among candidates passing **all** frozen gates, rank for aggressive performance in this order:

1. pooled WR descending;
2. pooled expectancy descending;
3. pooled PF descending;
4. effective exposure clusters descending;
5. max DD ascending;
6. shorter hold, then shorter lookback, then lexical rule.

Exactly one V2 selected candidate is reported if any full passer exists. Other full passers remain visible.

## Interpretation guardrails

- No candidate is retuned after viewing this experiment.
- No failed gate is relaxed.
- No replacement candidate receives special treatment based on prior H04/H15/H22/H23 results.
- This is research/shadow only.
- August 2026 remains pristine for a separately preregistered final holdout test only after V2 selection and anti-overfit checks are complete.
