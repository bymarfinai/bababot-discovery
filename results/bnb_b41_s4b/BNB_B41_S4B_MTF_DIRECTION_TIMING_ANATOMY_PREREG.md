# BNB B41-S4B — Multi-Timeframe Direction Timing Anatomy Preregistration

## Objective

Audit whether B41 direction characters are real but mistimed by the frozen 15-minute detector.

S4B compares fixed event-relative interaction horizons: **5m, 15m, 30m, 60m**. It is a direction-timing study only; no entry, SL, TP, PnL, PF, or expectancy is optimized.

## Frozen parents

- B41-S1 wall signature:
  `4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6`
- B41-S2 signature:
  `53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2`
- B41-S3 signature:
  `dfcfe845a7547c649defe7f47eeafb356bc2c307c00361b0794a131780e32492`
- B41-S4 signature:
  `c6eb2c0ade6c4f11c3d9d6512ec06473d5d22c3e2d6c8a75a16a640782d960dc`
- Wall: Q80 only.
- Source events: first Q80 touch from S2.
- DEV: 2022-2024.
- REF: 2025-2026.

## Event-relative multi-timeframe windows

For each Q80 first touch, observe from the first-touch 5m bar through:

- TF05: 1 completed 5m bar
- TF15: 3 completed 5m bars
- TF30: 6 completed 5m bars
- TF60: 12 completed 5m bars

These are event-relative horizons, not UTC-aligned resampled candles. This avoids arbitrary candle-boundary latency.

All outcomes begin strictly after the final close of the selected observation horizon.

## Frozen generalized character taxonomy

For each horizon, define OUTSIDE exactly as in S3:
- UPPER: 5m close > wall
- LOWER: 5m close < wall

Characters:

- **C1_CLEAN_REJECTION**: no OUTSIDE close during the horizon.
- **C2_RECLAIM_AFTER_CLOSE**: one or more OUTSIDE closes occurred, final close is INSIDE, and C1 is false.
- **C3_ACCEPTANCE_HOLD**:
  - TF05: the single observed close is OUTSIDE;
  - TF15/TF30/TF60: the final two observed 5m closes are both OUTSIDE.
- **C4_UNSETTLED_BREAK**: final close is OUTSIDE and C3 is false.

The taxonomy is mutually exclusive for every eligible horizon.

## Frozen S4 direction hypotheses under timing audit

Only the four hypotheses already tested by S4 are allowed:

- UPPER + C1 -> SHORT
- UPPER + C3 -> LONG
- LOWER + C1 -> LONG
- LOWER + C2 -> LONG

No lower-acceptance SHORT or other new mapping is introduced in S4B.

## Outcome origin and metrics

Origin = close of the final 5m bar in that timeframe horizon.

For LONG:
aligned return = (future close - detector close) / wall_distance

For SHORT:
aligned return = (detector close - future close) / wall_distance

Frozen metrics:
- aligned close displacement at +60m and +180m;
- hit rate at +60m and +180m;
- post-detector MFE and MAE to UTC session end;
- favorable dominance = MFE > MAE;
- signal count;
- detector latency in minutes.

## DEV-only timing nomination

For each of the four direction hypotheses, evaluate TF05, TF15, TF30, TF60 on DEV only.

A timeframe is **DEV_ELIGIBLE** if:
- valid 180m sample >= 30;
- median aligned 180m > 0;
- 180m hit rate >= 55%;
- favorable dominance > 50%.

Nominate the **earliest** eligible timeframe. Earliest is chosen deliberately to minimize confirmation latency, not maximize DEV performance.

If no timeframe is DEV_ELIGIBLE, the class receives **NO_NOMINATION**.

## REF holdout validation

Only the DEV-nominated timeframe is evaluated as a candidate on REF.

REF validates if:
- valid 180m sample >= 20;
- median aligned 180m > 0;
- 180m hit rate > 50%;
- favorable dominance > 50%.

No alternate timeframe may be substituted after REF is observed.

## Promotion rule

- A class with REF validation becomes **MTF_DIRECTION_SUPPORTED**.
- A class with no DEV nomination or REF failure becomes **NO_TRADE / UNRESOLVED**.
- S4B is **READY_FOR_S5** only if at least one LONG class and at least one SHORT class validate on REF.
- The already-supported S4 Upper+C1 SHORT may remain the frozen short anchor even if S4B finds a faster validated timing.

## Explicit exclusions

No wall quantile search, timeframe interpolation, nonstandard timeframe, candle body/wick filter, volume filter, entry geometry, SL, TP, holding-period optimization, trade WR, PF, expectancy, or PnL.
