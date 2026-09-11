# ETH R2 H05 Robust Lab — Preregistration

## Purpose

This branch treats ETH 05:00–06:00 WIB as a methodology laboratory. The objective is **not** to force a passing setup. The objective is to determine whether a LONG-side ETH character exists that is stable across time and nearby parameter choices before any confirmatory validation is opened.

Legacy R1 H05 results are treated as exploratory prior information only. R2 begins a new, explicitly bounded hypothesis process.

## Hard data boundaries

- Pair: ETHUSDT, 5m source used by the existing ETH research engine.
- Direction: LONG only.
- Hour: 05:00–06:00 WIB only.
- Development laboratory: 2022-01-01 through 2023-12-31.
- 2024: **HARD LOCKED confirmatory validation**. No R2 lab runner may load/evaluate 2024 until an internal candidate is frozen.
- Repo OOS 2025+: **CLOSED**.
- Costs/notional/anchor semantics inherit the frozen R1/E12 engine and may not be changed inside R2 simply to improve results.

## Research-round budget

Maximum **5 preregistered rounds**, including diagnostics. Each round must be committed before its result is computed.

- Round 1 — structural diagnosis only; cannot nominate a validation candidate.
- Rounds 2–4 — at most one new structural hypothesis family per round. No unrestricted search expansion.
- Round 5 — final internal confirmation/freeze or STOP.

If no robust internal edge exists by the end of Round 5, verdict is `H05_LAB_NO_ROBUST_EDGE` and the lab stops. The 2024 lock remains closed.

## Anti-overfit rules

1. No change may be justified by 2024 because 2024 cannot be read during the lab.
2. A failed round may inform the *next preregistered hypothesis*, but thresholds/results from the failed round cannot be retrospectively relabeled as PASS.
3. No micro-optimization of lookback/hold around a winner. Timing refinement, if later justified, must be coarse, preregistered, and evaluated as a neighborhood/region.
4. Prefer regions/habitats over maxima. A single attractive cell is insufficient.
5. No more than one frozen H05 candidate may be sent to 2024 in R2.
6. If the frozen candidate fails 2024, H05 R2 ends `VALIDATION_FAIL`; no rescue candidate is selected with knowledge of 2024.
7. All evaluation is chronological; no random cross-validation.
8. Overlapping-horizon leakage across any later train/test boundary must be purged/embargoed by at least the maximum tested hold.

## Internal time blocks

R2 development diagnostics use four chronological blocks:

- 2022-H1
- 2022-H2
- 2023-H1
- 2023-H2

A block is evaluable only when its sample count is sufficient for the metric being interpreted; low-N blocks must be reported rather than silently excluded.

## Robustness dimensions

A potential character must be examined on all of:

- four half-year time blocks;
- four minute anchors (00/15/30/45), where applicable;
- neighboring coarse LB/Hold cells;
- concentration of PnL across blocks/anchors;
- pooled economics (N, WR, net, expectancy, PF, DD, loss streak);
- executable flat-only replay before any validation freeze.

A later frozen candidate must not depend on one isolated timing cell or one dominant half-year.

## Round 1 — frozen question

**Question:** Why did R1 H05 contain one strict+temporal cell but no qualifying plateau, and is there evidence of a repeatable *family-level* habitat worth testing as a new hypothesis?

Round 1 is DIAGNOSTIC ONLY. It uses **2022–2023 only** and cannot open 2024 or freeze a validation candidate.

### Frozen Round-1 scope

Use the existing R1 H05 coarse grid without adding new timings or rules:

- Lookbacks: 60, 120, 180, 240, 360 minutes.
- Holds: 120, 240, 360, 480 minutes.
- Existing 90-rule grammar.

The diagnosis will report for every rule family that has at least one economically supportive R1 H05 cell:

1. connected LB/Hold components and their sizes;
2. strict/temporal membership;
3. four half-year metrics for the strongest structurally relevant cells;
4. four-anchor metrics where available from the engine;
5. PnL concentration by half-year;
6. neighborhood sign consistency;
7. whether the failure is primarily **timing fragility**, **temporal fragility**, **anchor fragility**, **sample insufficiency**, or **economic weakness**.

Legacy hints such as `DRIVE_DOWN__STR_B80_100` and `EFF_LOW__RANGE_HIGH` may be inspected because they were already exposed before this preregistration, but Round 1 may not declare either a winner merely because it was previously attractive.

### Round-1 output

Round 1 must end with one of:

- `NO_FAMILY_HYPOTHESIS` — nothing warrants a Round-2 test; or
- `ONE_FAMILY_HYPOTHESIS` — exactly one structural hypothesis is proposed for Round 2.

Any Round-2 change must then receive a separate preregistration commit **before** its computation.

## Candidate robustness requirements before 2024 can open

These are minimum principles; a later round preregistration may make them stricter but may not weaken them after seeing its own results:

- evidence is a connected timing region, not an isolated cell;
- at least three of four evaluable half-years have positive expectancy and PF > 1;
- no single half-year should account for a majority of positive net PnL unless the other blocks are independently economically positive and the concentration is explicitly justified;
- neighboring cells do not show immediate sign reversal around the representative point;
- anchor diagnostics do not reveal dependence on one anchor alone;
- executable flat-only replay remains economically positive without catastrophic DD/loss-streak deterioration;
- the representative point is chosen by a preregistered robust/central rule, not highest PnL or highest WR.

Passing these internal requirements grants only `INTERNAL_ROBUST_CANDIDATE`, not production/OOS status.

## Confirmatory 2024 rule

2024 may be opened exactly once only after the exact character rule, timing region, representative LB/Hold, costs, and validation gates are committed and frozen. A 2024 failure ends R2 H05. A 2024 pass still does not open final OOS 2025+; that requires the broader 24-hour architecture to be frozen later.
