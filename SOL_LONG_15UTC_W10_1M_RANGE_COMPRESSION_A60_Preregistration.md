# SOL LONG 15:00 UTC W10 1m Range Compression Revalidation — A60 Preregistration

## Purpose

A57 found no robust discrete 5m loss-confirmation sequence. A58 then decomposed the first W10 warning candle into causal completed 1m states K1–K4. No frozen binary 1m motif replicated strongly enough for execution, but the report-only continuous anatomy exposed one pair-native candidate worth a separately locked test: **latest completed 1m range normalized by R** (`latest_range_R`).

A60 asks one narrow question:

> Within the frozen first-W10 anatomy cohort, does unusually small normalized 1m range at one Development-selected causal observation time consistently identify a fail-heavier subset across Development, External, and Reference Validation?

A60 is **candidate revalidation only**. It does not alter exits, position size, or live Baba Bot. Because `latest_range_R` was nominated after inspecting A58's completed research output, A60 is explicitly exploratory rather than a pristine unseen confirmation. Even a SUPPORTED result can authorize only a later live-opportunity replay; it cannot authorize trading.

## Frozen parent and cohort

- Pair: SOLUSDT LONG.
- Clock/reference: 15:00 UTC / R360.
- Parent: frozen A20/A25B `E0_RESTING_H -> E40` under A2/A17 mechanics.
- Target: `H + 0.40R`.
- Cohort: A58 first W10 warning (`H < completed 5m close <= H+0.10R` after confirmed breakout while parent remains live).
- Outcomes for primary discrimination: `FAILED_BREAK` versus `RECOVER_E40`; unresolved TIME is excluded from the binary discrimination but reported.
- Source states: `SOL_LONG_15UTC_W10_INTRABAR_1M_A58_STATES.csv` produced under A58's 1m→5m parity gate.

Expected W10 outcome counts before K filtering:
- Development: 233 FAILED_BREAK / 63 RECOVER_E40 / 4 unresolved TIME.
- External: 133 / 54 / 5.
- Reference Validation: 134 / 48 / 2.

## One frozen continuous candidate

A60 tests **only**:

`latest_range_R = (latest completed 1m high - latest completed 1m low) / R`

No directional close feature, body feature, path-range feature, composite score, alternate normalization, or feature sweep is allowed.

### Frozen observation time

A60 uses **K3 only**, i.e. after the third completed 1m candle inside the frozen A58 W10 5m candle.

Reason frozen before this run: among A58's Development-only continuous summaries, K3 had the largest fail-versus-target median separation for `latest_range_R`. K1/K2/K4 are not candidate alternatives in A60 and cannot replace K3 after results are seen.

### Frozen threshold derivation

The threshold is derived from **Development K3 only**:

1. calculate the Development K3 median `latest_range_R` for FAILED_BREAK;
2. calculate the Development K3 median for RECOVER_E40;
3. require `median_fail < median_target`;
4. set exactly one threshold to their arithmetic midpoint:

`T = (median_fail + median_target) / 2`

5. freeze the bad/compression state as:

`COMPRESSED_K3 = latest_range_R <= T`

The implementation must derive `T` before computing any External or Reference Validation classification metrics. No percentile sweep, neighboring threshold, rounding grid, or OOS retuning is permitted.

For reconciliation, the A58 continuous report indicates approximate Development K3 medians of 0.07096R for FAILED_BREAK and 0.08531R for RECOVER_E40, implying T near 0.07813R. These values are reconciliation references, not separately tunable inputs.

## Data/reconciliation gate

A60 is technically valid only if:

1. the A58 states file exists and contains exactly one K3 state per valid W10 event;
2. Development K3 contains at least 200 FAILED_BREAK and 50 RECOVER_E40 observations;
3. External K3 contains at least 100 FAILED_BREAK and 35 RECOVER_E40 observations;
4. Reference Validation K3 contains at least 100 FAILED_BREAK and 35 RECOVER_E40 observations;
5. Development medians reconcile approximately to the preregistration references (absolute tolerance 0.002R each);
6. the derived threshold is finite, positive, and lies strictly between the two Development medians;
7. no partition other than Development contributes to threshold derivation.

Any failure is `SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_RECONCILIATION_FAIL` and no interpretation is allowed.

## Development discrimination gate

A60 passes Development only if ALL are true for K3 `COMPRESSED_K3`:

1. fail hit rate > target hit rate;
2. fail-target hit-rate gap >= 10 percentage points;
3. fail/target hit-rate ratio >= 1.25x;
4. fail hit rate >= 45%;
5. the bad direction (`fail hit > target hit`) appears in at least 4 of 6 frozen Development half-year blocks where the block contains >=10 fail and >=3 target observations.

The block test uses the same single frozen threshold T derived from the full Development sample; blocks do not derive their own thresholds.

## OOS replication gate

Only if Development passes, independently require in BOTH External and Reference Validation:

1. fail hit rate > target hit rate;
2. fail-target gap >= 5 percentage points;
3. fail/target hit-rate ratio >= 1.15x;
4. fail hit rate >= 40%;
5. the preregistered support minima are met.

No OOS threshold adjustment is allowed.

## Diagnostics

Report at minimum:

- derived Development medians and frozen T;
- N, compressed N, fail hit, target hit, gap, and ratio for each partition;
- unresolved TIME counts and compression rate as diagnostics only;
- six Development block hit rates/gaps using the same T;
- pass/fail of each Development and OOS gate.

## Interpretation and next experiment

A60 remains conditioned on the completed future-known W10 5m cohort used by A58. Therefore a replicated result means only:

> normalized 1m range compression carries outcome information inside the W10 anatomy cohort.

If A60 is supported, the next experiment must replay this fixed K3/T concept over **all live-causal post-breakout opportunities without conditioning on the future completed W10 candle**, and only then may an executable economics rule be considered.

If A60 fails, do not tune K, T, or add directional features to rescue it. Treat `latest_range_R` as descriptive anatomy and move to a different causal hypothesis.

## Decision states

- `SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_SUPPORTED_FOR_LIVE_REVALIDATION` — Development and both OOS replication gates pass.
- `SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_DEVELOPMENT_ONLY` — Development passes but either OOS partition fails.
- `SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_INCONCLUSIVE` — Development gate fails.
- `SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_RECONCILIATION_FAIL` — technical/data gate fails.

Research only. Live Baba Bot remains unchanged.
