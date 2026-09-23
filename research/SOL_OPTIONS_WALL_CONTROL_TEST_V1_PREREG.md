# SOL Options Wall Control Test V1 — Preregistration

## Purpose

Test whether prospectively recorded SOL options concentration walls contain reaction information beyond three non-options benchmarks:

1. deterministic distance-matched pseudo-random levels;
2. fixed $5 round-number levels;
3. causal price-only confirmed 1H pivot levels.

This study is downstream of SOL_OPTIONS_LIQUIDITY_MAP_V1 and SOL_OPTIONS_WALL_FORWARD_VALIDATION_V1.

It does not modify the options map formula, detector, entry logic, SL, or TP.

## Confirmatory start

**CONTROL_PREREG_START_UTC = 2026-09-23T04:46:00Z**

Anything whose control anchor begins before this timestamp is exploratory only.

The already-observed 116 touch on 2026-09-22 is explicitly excluded from confirmatory control evidence because its outcome was known before this control design was frozen.

## Control anchor construction

Use saved prospective SOL_OPTIONS_LIQUIDITY_MAP_V1 snapshots only.

The first saved snapshot at or after CONTROL_PREREG_START_UTC becomes the first confirmatory anchor.

After that, create a new independent control anchor when either:

- at least 240 minutes have elapsed since the prior anchor; or
- the options map regime changes before 240 minutes.

A map regime changes when any of these change:

- three-expiry tuple;
- top-three lower put strikes/rank;
- top-three upper call strikes/rank.

This prevents every hourly snapshot from being treated as an independent sample while still allowing a stable map to generate non-overlapping forward observations.

## Frozen forward horizon

Each anchor has a maximum forward horizon of 240 minutes.

If a later map-regime change occurs first, the anchor ends immediately before the new regime begins.

An unfinished horizon is CENSORED, not failure.

## Price source

Binance SOLUSDT spot 1-minute candles.

All control levels use information available at or before the anchor timestamp.

## Candidate sets

### A. OPTIONS

Use the frozen V1 map:

- lower put concentration ranks 1–3;
- upper call concentration ranks 1–3.

### B. RANDOM_MATCHED

For each OPTIONS level independently:

1. calculate absolute distance from anchor spot:
   `d = abs(option_level / spot - 1)`;
2. derive deterministic pseudo-random `u` from SHA256:
   `anchor_snapshot_id | side | rank | RANDOM_MATCHED_V1 | attempt`;
3. map `u` into multiplier range [0.75, 1.25];
4. candidate distance = `d * multiplier`;
5. place the candidate on the same side of spot as the OPTIONS level;
6. round to $0.01.

Reject and deterministically retry if the random level is:
- on the wrong side of spot;
- within 0.10% of spot from any OPTIONS wall on the same side;
- duplicated within the RANDOM_MATCHED set.

Maximum retry attempts: 50.

If no valid level exists, mark the control unavailable rather than changing the rule.

### C. ROUND_5

Generated independently from the options strikes.

For each anchor spot:

Lower side:
- rank 1 = nearest $5 multiple strictly below spot;
- rank 2 = rank 1 - $5;
- rank 3 = rank 1 - $10.

Upper side:
- rank 1 = nearest $5 multiple strictly above spot;
- rank 2 = rank 1 + $5;
- rank 3 = rank 1 + $10.

If a ROUND_5 level equals an OPTIONS level, retain it and mark `overlap_options=true`.

Overlapping observations may be reported descriptively but are excluded from claims that OPTIONS outperformed round numbers at that level.

### D. PRICE_PIVOT_1H

Use the 72 completed Binance SOLUSDT 1H candles ending before the anchor.

A confirmed pivot low at candle i requires:
- low[i] < lows of i-2, i-1, i+1, i+2.

A confirmed pivot high requires:
- high[i] > highs of i-2, i-1, i+1, i+2.

Only pivots whose right-hand confirmation candles closed before the anchor are eligible.

Lower controls:
- three nearest distinct confirmed pivot lows below anchor spot.

Upper controls:
- three nearest distinct confirmed pivot highs above anchor spot.

No volume, derivatives, options, future bars, or discretionary chart marking is allowed.

If fewer than three eligible pivots exist on a side, report only those available.

## Touch definition

A level is touched when a 1-minute candle satisfies:

`low <= level <= high`

Only the first touch during the anchor window is evaluated.

## Frozen reaction measurements

For every first touch report side-normalized:

- MFE and MAE at 15m;
- MFE and MAE at 30m;
- MFE and MAE at 60m;
- MFE and MAE to anchor end;
- close displacement at the same horizons.

Lower-level favorable direction = upward.
Upper-level favorable direction = downward.

## Symmetric first-passage outcomes

Report all three, with no post-hoc selection:

- ±0.25%
- ±0.50%
- ±1.00%

Outcomes:
- FAVORABLE_FIRST
- ADVERSE_FIRST
- SAME_BAR_BOTH
- NONE

## Primary future comparison metric

For confirmatory anchors only:

`NET_REACTION_60 = MFE_60 - MAE_60`

Primary comparison is OPTIONS rank-1 versus RANDOM_MATCHED rank-1.

PRICE_PIVOT_1H rank-1 is the structural price-only benchmark.

ROUND_5 is a diagnostic benchmark because options strikes can naturally coincide with round prices.

Secondary analyses may show ranks 2–3 but may not replace rank-1 as the primary test.

## Sample-size and stopping rule

Do not promote the options layer from this test before all of these are available:

- >= 20 confirmatory OPTIONS rank-1 touches;
- >= 20 confirmatory RANDOM_MATCHED rank-1 touches;
- >= 10 confirmatory PRICE_PIVOT_1H rank-1 touches;
- observations span >= 10 independent anchors.

At the first time those conditions are met, run the frozen evaluation.

### Evidence-supported condition

Label `CONTROL_EVIDENCE_SUPPORTED` only if:

1. median NET_REACTION_60 for OPTIONS rank-1 is greater than RANDOM_MATCHED rank-1;
2. median NET_REACTION_60 for OPTIONS rank-1 is greater than PRICE_PIVOT_1H rank-1;
3. deterministic bootstrap 90% CI for the difference in medians OPTIONS minus RANDOM_MATCHED is entirely above 0;
4. the sign of the OPTIONS-minus-RANDOM advantage is not contradicted at all three first-passage bands when summarized as:
   FAVORABLE_FIRST = +1,
   ADVERSE_FIRST = -1,
   SAME_BAR_BOTH/NONE = 0.

If the minimum sample is reached but these conditions are not met, label `CONTROL_EVIDENCE_NOT_SUPPORTED`.

Before minimum sample:
`CONTROL_SAMPLE_ACCUMULATING`.

## Bootstrap

- 10,000 resamples;
- deterministic RNG seed = 20260923;
- resample touched observations within each compared group;
- statistic = difference in group medians of NET_REACTION_60;
- percentile 90% CI.

## Guardrails

- No control definition may be changed after CONTROL_PREREG_START_UTC based on observed outcomes.
- No threshold may be tuned on the confirmatory sample.
- Historical trades before the options map existed remain ineligible.
- The old 116 touch is exploratory only for this control test.
- This study evaluates information content of the wall, not live profitability.
- No READY_TO_TRADE label may be produced by this test alone.
