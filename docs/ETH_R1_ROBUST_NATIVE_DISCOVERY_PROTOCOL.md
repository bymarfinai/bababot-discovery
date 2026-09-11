# ETH R1 Robust Native Discovery Protocol

Status: PREREGISTERED BEFORE R1 H00 TRAIN SEARCH.

Purpose: restart ETH hourly LONG discovery with explicit anti-overfit controls. E12-E16 remain research history only and are not production candidates.

## Frozen data policy

- Pair: ETHUSDT, 5m.
- Direction: LONG only.
- Discovery/Train: 2022-01-01 through 2023-12-31.
- Validation: 2024-01-01 through 2024-12-31.
- OOS/reference validation 2025+ remains CLOSED for R1 discovery and validation.
- Validation must not influence rule, lookback, hold, region selection, or representative selection.
- If the frozen 2024 validation candidate fails, the hour fails. No alternate candidate may be tried against 2024 in the same R1 generation.

## Hourly process

One WIB hour is studied at a time. Four 15-minute anchors inside the hour are preserved.

## Frozen character grammar

Reuse the exact 90 E12 character rules. R1 does not invent new rules during the search.

## Coarse timing grid

- Lookbacks: 60, 120, 180, 240, 360 minutes.
- Holds: 120, 240, 360, 480 minutes.
- Total train cells per hour: 5 x 4 x 90 = 1,800.
- No finer timing search is allowed in R1.

## Train strict gate

A cell is strict-pass on 2022-2023 only when all are true:

- pooled N >= 120
- pooled WR >= 55%
- pooled expectancy >= +$0.50/trade
- pooled PF >= 1.20
- pooled max DD <= $125
- pooled max loss streak <= 8
- each of 2022 and 2023: N >= 40, WR >= 52%, expectancy > 0, PF >= 1.05
- at least one train year WR >= 55%
- at least 3/4 anchors are supportive; anchor supportive means N >= 30, WR >= 52%, expectancy > 0, PF >= 1.05, DD <= $125, max loss streak <= 10

## Plateau/supportive cell definition

A train cell is plateau-supportive when all are true:

- pooled N >= 100
- WR >= 52%
- expectancy > 0
- PF >= 1.05
- max DD <= $150
- max loss streak <= 10
- both 2022 and 2023: N >= 25, expectancy > 0, PF >= 1.00

For each rule, supportive cells are connected by orthogonal adjacency on the frozen coarse LB x Hold grid.

A robust train region must:

- contain >= 4 supportive cells,
- span >= 2 distinct lookbacks,
- span >= 2 distinct holds,
- contain >= 1 strict-pass cell that also passes temporal consistency.

## Temporal consistency inside Train

The strict-pass representative is checked on four half-year blocks: 2022-H1, 2022-H2, 2023-H1, 2023-H2.

Temporal consistency requires:

- every block N >= 15,
- at least 3/4 blocks have expectancy > 0 and PF > 1.00,
- no block expectancy < -$0.75/trade.

## Train-only region and representative selection

Exactly one region/candidate may be frozen for validation.

Region ranking, using Train only:
1. more temporally-consistent strict-pass cells,
2. larger supportive component,
3. higher component median expectancy,
4. higher component median PF,
5. lower component median max DD,
6. lexical rule name for deterministic tie-break.

Within the selected region, choose the temporally-consistent strict-pass cell with minimum total Manhattan distance to all supportive cells in that component (grid medoid). Ties: shorter hold, shorter lookback, lexical rule name.

This representative is written to a lock file before validation is run.

## One-shot 2024 validation gate

The frozen candidate is evaluated exactly once on 2024. Validation PASS requires:

- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

Validation is not used to retune anything.

## Status language

- NO_ROBUST_TRAIN_REGION: no region survives train robustness requirements; 2024 remains unopened for that hour.
- VALIDATION_FAIL: one frozen train candidate was tested once on 2024 and failed. No rescue search.
- ROBUST_VALIDATED_HABITAT: one frozen train candidate passed the one-shot 2024 validation. Still research/shadow only; OOS remains closed.

No R1 result authorizes live trading.