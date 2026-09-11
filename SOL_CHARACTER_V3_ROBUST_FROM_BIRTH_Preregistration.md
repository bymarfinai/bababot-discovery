# SOL Character Discovery V3 — Robust-from-Birth Preregistration

## Objective

Discover a **high-performance SOLUSDT LONG market mechanism that is robust from birth**, rather than selecting an exact parameter peak first and testing robustness afterward.

The objective remains aggressive: **maximize performance subject to frozen robustness constraints**. Stability is a hard eligibility filter, not a substitute for performance.

## Research universe

- Research/scoring window: **2022-01-01 UTC through 2026-07-30 UTC, exclusive end**.
- 2025 through 2026-07-30 have already been exposed by prior SOL validation work and are therefore research data in V3, not OOS.
- Pre-2022 bars may be loaded only as causal history for rolling state normalization.
- **August 2026 must not be downloaded, loaded, scored, ranked, or used for tie-breaking.**
- Direction: LONG only.
- Fixed notional: $500.
- Round-trip fee: $0.75.
- Entry/exit: exact 5m-open, fixed time hold.
- Causal state construction remains identical to the frozen SOL economic-first engine: rolling same-anchor normalization uses only observations before the current observation.

## Why V3 changes the search space

V1/V2 searched exact rule/clock/LB/hold combinations and found strong historical peaks that were not stable into 2026. V3 therefore reduces multiplicity and searches **simple market mechanisms over broad two-hour habitats**. An exact parameter cell cannot win unless the surrounding time/parameter region is also healthy.

## Frozen mechanism grammar

Exactly eight simple two-factor hypotheses are allowed:

1. `DOWN_SHOCK_REVERSAL`: negative pre-entry drive + top-20% causal drive strength.
2. `DOWN_INEFFICIENT_SNAPBACK`: negative drive + LOW causal efficiency.
3. `DOWN_RANGE_EXHAUSTION`: negative drive + HIGH causal realized range.
4. `DOWN_VOL_EXHAUSTION`: negative drive + HIGH causal realized volatility.
5. `UP_SHOCK_CONTINUATION`: positive drive + top-20% causal drive strength.
6. `UP_EFFICIENT_CONTINUATION`: positive drive + HIGH causal efficiency.
7. `UP_VOL_EXPANSION_CONTINUATION`: positive drive + HIGH causal realized volatility.
8. `UP_COMPRESSION_CONTINUATION`: positive drive + LOW causal realized range.

No extra conjunctions, rule mining, threshold tuning, or post-result mechanism additions are allowed.

## Broad time habitats

The UTC day is frozen into **12 non-overlapping two-hour habitats**:

`00-02, 02-04, 04-06, 06-08, 08-10, 10-12, 12-14, 14-16, 16-18, 18-20, 20-22, 22-24 UTC`.

Each habitat contains eight quarter-hour anchors. This is deliberately broader than the V1/V2 exact-hour search.

Lookbacks remain frozen at **15, 30, 60, 120, 240, 360 minutes**.
Holds remain frozen at **60, 120, 240, 360, 720, 960 minutes**.

Total V3 raw universe: **12 habitats × 8 mechanisms × 6 lookbacks × 6 holds = 3,456 candidates**.

## Frozen pooled performance gate

A candidate must satisfy all:

- raw N >= 300;
- WR >= 60.00%;
- net > 0;
- expectancy >= +$1.50/trade;
- PF >= 1.70;
- max drawdown <= $175;
- max loss streak <= 8.

No threshold may be relaxed if nothing passes.

## Frozen chronological era gate

Evaluate 2022, 2023, 2024, 2025, and 2026-YTD separately.

Every fold must satisfy:

- N >= 30;
- WR >= 55.00%;
- positive net and expectancy;
- PF >= 1.15.

Additionally, at least **3 of 5 folds must have WR >= 60.00%**.

A failed 2026 fold cannot be rescued by stronger earlier years.

## Frozen two-hour habitat plateau gate

The candidate is split into its two constituent UTC hours. **Both hours** must independently satisfy:

- N >= 100;
- WR >= 56.00%;
- expectancy >= +$0.50/trade;
- PF >= 1.25;
- max DD <= $200;
- max loss streak <= 10.

Quarter-hour anchor diagnostics are also frozen:

- anchor evaluable at N >= 25;
- supportive when WR >= 54%, expectancy > 0, PF >= 1.10, DD <= $150, loss streak <= 10;
- at least 7/8 anchors must be evaluable;
- at least 6/8 must be supportive;
- no evaluable anchor may have expectancy < -$0.50 or PF < 0.90.

This prevents a single magic hour or quarter-hour from carrying a two-hour habitat.

## Frozen overlap-adjusted effective-N gate

Selected trade exposure intervals are merged into chronological overlap clusters. Each merged cluster counts as one effective observation.

Candidate requirement:

- effective exposure clusters >= 120;
- effective-N / raw-N >= 0.35.

## Frozen LB/hold neighborhood plateau gate

For the same mechanism and same two-hour habitat, inspect immediate parameter neighbors:

- previous/next lookback at the same hold;
- previous/next hold at the same lookback.

A neighbor is supportive when:

- pooled WR >= 57%;
- expectancy >= +$1.00/trade;
- PF >= 1.40;
- net > 0;
- DD <= $225;
- at least 4/5 yearly folds have positive expectancy;
- both constituent hours have positive expectancy.

Candidate requirement:

- at least 3 immediate neighbors available;
- at least 2 supportive neighbors.

Thus the selected cell must belong to a parameter plateau rather than an isolated spike.

## Selection and ranking

Only candidates passing **pooled + era + habitat plateau + effective-N + neighborhood plateau** are eligible.

Among full passers, rank in this order:

1. minimum yearly expectancy descending;
2. number of supportive parameter neighbors descending;
3. pooled WR descending;
4. pooled expectancy descending;
5. pooled PF descending;
6. effective exposure clusters descending;
7. max DD ascending;
8. shorter hold, shorter lookback, lexical mechanism/session.

Exactly one selected V3 configuration is reported if any full passer exists; all full passers remain visible.

## Interpretation guardrails

- No failed gate is relaxed.
- No mechanism/clock/LB/hold receives rescue treatment after results are visible.
- V1/V2 winners receive no inherited privilege.
- A high-WR isolated cell is not a V3 character.
- Research/shadow only.
- **August 2026 remains pristine for a separately preregistered holdout only after a V3 candidate is frozen.**
