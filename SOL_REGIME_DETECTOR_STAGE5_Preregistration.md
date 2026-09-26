# SOL Regime Detector — Stage 5 Forward-Behavior Validation Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 5 is the first stage allowed to use future price behavior. It tests whether the frozen Stage-4 causal states have real descriptive/predictive meaning.

No Stage-4 score, threshold, hysteresis, or transition rule may be changed in Stage 5.

## Data boundary

- Regime states: frozen Stage-4 output.
- Validation population: decision times from 2023-01-01 through 2024-12-31 only.
- Raw future prices: SOLUSDT perpetual futures 5m bars only inside the same 2023-2024 DEV boundary.
- Any observation whose requested horizon would cross 2025-01-01 is excluded for that horizon.
- 2025 and 2026 are not used for calibration, scoring, or validation in Stage 5.

## Entry / decision convention

For a Stage-4 state emitted from a completed 1H candle:

- state is known at that candle close,
- reference entry price = SOLUSDT 5m **open exactly at decision_time / next 1H open**,
- all future-behavior measurement begins from that open.

This is behavioral validation only, not a trading backtest. Every eligible hourly state is labeled independently; one-position constraints do not apply here.

## Frozen future measurements

Horizons: **6H, 12H, 24H**.

For each horizon:

1. forward return = price at exact horizon open / entry open - 1
2. MFE = maximum future high relative to entry
3. MAE = maximum future downside relative to entry
4. first-hit label for symmetric ±1%:
   - POS_FIRST if +1% is hit on an earlier 5m candle than -1%
   - NEG_FIRST if -1% is hit earlier
   - AMBIGUOUS if both are first touched inside the same 5m candle
   - UNRESOLVED if neither is touched before the horizon

AMBIGUOUS and UNRESOLVED are reported but excluded from the resolved directional hit-rate denominator.

## Regime interpretation

At 24H among resolved ±1% events:

- Bull aligned hit = POS_FIRST
- Bear aligned hit = NEG_FIRST
- Sideways has no directional target; its POS_FIRST share is tested for balance.

For forward return:
- expected ordering is Bull > Sideways > Bear.
- directional aligned return is raw return for Bull and negative raw return for Bear.

For excursion:
- Bull should have MFE > MAE in the median.
- Bear should have MAE > MFE in the median.

## Frozen subgroups

### Temporal robustness blocks
Four equal calendar blocks:
- 2023-H1
- 2023-H2
- 2024-H1
- 2024-H2

### Transition diagnostic
For BULL and BEAR only:
- CLEAN = transition_flag == false
- TRANSITION = transition_flag == true

The transition flag is meaningful if CLEAN has higher combined aligned ±1% hit-rate than TRANSITION.

## Mandatory Stage-5 gates

1. Stage-4 status is VALID.
2. Raw 5m DEV coverage >= 99.5%.
3. No state decision time or future window used for a scored horizon crosses 2025-01-01.
4. Each final regime contributes at least 1,000 eligible 24H observations.
5. 24H resolved rate for each regime is at least 60%.
6. Bull 24H aligned resolved hit-rate >= 55%.
7. Bear 24H aligned resolved hit-rate >= 55%.
8. Bull POS_FIRST share minus Bear POS_FIRST share >= 10 percentage points.
9. Sideways POS_FIRST share among resolved events is between 45% and 55%.
10. Median 24H forward return satisfies Bull > Sideways > Bear.
11. Median 24H Bull forward return > 0 and Bear forward return < 0.
12. Median Bull MFE24 > MAE24 and median Bear MAE24 > MFE24.
13. Bull aligned hit-rate > 50% in at least 3 of 4 temporal blocks.
14. Bear aligned hit-rate > 50% in at least 3 of 4 temporal blocks.
15. Combined CLEAN Bull/Bear aligned hit-rate exceeds TRANSITION by at least 2 percentage points.
16. Same-5m ambiguous first-hit share is <= 2% for every regime.
17. No future outcome is used to alter or recompute the Stage-4 state stream.

Stage 5 passes only if every mandatory gate passes. If it fails, the detector is not promoted to OOS Stage 6 without a separately preregistered redesign.
