# SOL Regime + Phase V2 — Stage 6F Predictive Feature Forensics Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 6F asks a narrower question than Stage 6D:

> Which individual causal Stage-6B features, if any, materially separate aligned ±1% winners from losers?

This is feature forensics, not a new model.

## Data policy

- Causal features: frozen Stage-6B output.
- Direction routing and future labels: frozen Stage-6D output.
- 2023 = discovery / orientation / threshold selection.
- 2024 = untouched-by-6F internal validation of those frozen 2023 choices.
- 2025 and 2026 remain unopened.

Stage 6F may not alter:
- Stage-6B features,
- Stage-6C direction routing,
- Stage-6D future labels.

## Target

Primary target:
- resolved 24H aligned ±1% first-hit from Stage 6D.

Secondary confirmation targets:
- resolved 6H aligned ±1% first-hit,
- resolved 12H aligned ±1% first-hit.

AMBIGUOUS and UNRESOLVED rows are excluded from the corresponding horizon target.

## Candidate feature universe

### Direction-routed side features
For every suffix that exists as both:
- `bull_<suffix>`
- `bear_<suffix>`

the row value is selected according to Stage-6D frozen side:
- selected_side=BULL -> bull value
- selected_side=BEAR -> bear value.

The same suffix therefore has one symmetric routed value.

### Shared features
Frozen shared numeric candidates:
- h1_atr_norm
- h1_atr_vs_med72
- h1_atr_pct168
- h1_mean_cross_12
- h1_mean_cross_24
- h1_overlap_12
- h1_overlap_24
- h1_range_path_12
- h1_range_path_24
- atr_slope6
- range24_atr
- compression_6v24
- boundary_touch_count12
- failed_escape_count24
- range_atr
- volume_vs_med24
- v1_regime_duration_hours

Raw OHLCV level is excluded to avoid non-stationary absolute-price discovery.

### Missingness/presence candidates
For a causal candidate with 2023 finite coverage between 5% and 95%, Stage 6F also tests:
- `<feature>__present` = 1 if the causal feature exists on that row, else 0.

This is preregistered because absence of an event clock/reclaim statistic can itself be causal state information.

## Feature typing

- A candidate is binary if its finite 2023 values are only 0/1.
- Otherwise it is continuous.
- Minimum 2023 finite support: 500 resolved 24H observations.
- Minimum 2024 finite support: 500 resolved 24H observations.
- Features below either support floor are reported as ineligible and cannot survive.

## Frozen 2023 discovery rule

### Continuous feature
1. Compute 2023 24H AUC against ALIGNED_FIRST.
2. If raw AUC >=0.50, orientation=HIGH; otherwise orientation=LOW.
3. Freeze favorable-tail threshold from 2023:
   - HIGH -> 80th percentile
   - LOW -> 20th percentile.
4. Apply that exact numeric threshold unchanged to 2024.

### Binary feature
1. Compare 2023 aligned hit-rate for value 1 vs value 0.
2. Freeze favorable value to whichever has higher 2023 hit-rate.
3. Apply the same favorable value unchanged to 2024.

No 2024 statistic may change orientation, threshold, or favorable binary value.

## Frozen metrics

For every eligible candidate:
- raw and oriented AUC 2023 / 2024 at 24H,
- oriented AUC 2024 at 6H / 12H,
- favorable-subset sample count,
- favorable-subset aligned hit-rate,
- favorable-subset lift versus period baseline,
- same frozen favorable rule performance in each half-year,
- half-years where favorable subset beats its block baseline.

## STRONG_SURVIVOR gate

A feature is a STRONG_SURVIVOR only if ALL are true:

1. 2023 oriented 24H AUC >= 0.54.
2. 2024 oriented 24H AUC >= 0.53 using the 2023-frozen orientation.
3. 2023 favorable subset >=100 resolved observations.
4. 2024 favorable subset >=100 resolved observations.
5. 2023 favorable-subset hit-rate >=55%.
6. 2024 favorable-subset hit-rate >=54%.
7. 2023 lift over baseline >=3 percentage points.
8. 2024 lift over baseline >=3 percentage points.
9. Favorable subset beats block baseline in at least 3 of 4 half-year blocks, with >=30 observations in each counted block.
10. On 2024, oriented AUC >=0.52 at **at least one** secondary horizon (6H or 12H).

## WATCHLIST gate

A feature is WATCHLIST if it is not STRONG_SURVIVOR but ALL are true:

1. 2023 oriented AUC >=0.53.
2. 2024 oriented AUC >=0.515.
3. 2023 and 2024 favorable-subset lift are both positive.
4. At least 3 of 4 half-year blocks have the same positive-lift direction with >=30 favorable observations.

WATCHLIST is diagnostic only and is not authorized as a trading filter.

## Multiple-testing discipline

Stage 6F does not claim statistical significance from raw ranking alone.

It reports:
- number of candidates tested,
- survivor count,
- watchlist count,
- empirical null-like concentration of AUCs around 0.50.

No feature may be promoted because it is merely top-ranked.

## Mandatory technical audits

1. Stage 6D status is DEV_VALIDATION_FAILED (forensics follows failure).
2. Stage 6B status is FEATURE_ENGINE_VALID.
3. All input rows are only 2023-2024.
4. 2025/2026 are not loaded.
5. Direction routing is copied unchanged from Stage 6D labels.
6. Future labels are copied unchanged from Stage 6D; no relabeling occurs.
7. 2024 never participates in orientation/threshold fitting.
8. At least 50 eligible candidates are scanned.
9. No candidate name contains forward/future/outcome/TP/SL/trade-result.
10. Every STRONG_SURVIVOR and WATCHLIST meets its frozen gate exactly.

Stage 6F is complete even if zero features survive.
