# BNB B41-S2 — Wall Importance Audit Preregistration

## Objective

Test whether the frozen B41-S1 causal wall hierarchy corresponds to meaningful same-session price decision points.

S2 remains **non-trading**. It does not create entry rules, direction rules, TP, SL, WR, PF, or expectancy.

## Frozen parent

- B41-S1 wall signature:
  `4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6`
- Session: UTC day.
- Wall formation: previous 60 completed sessions only.
- Wall families:
  - MID = Q50 excursion
  - WALL = Q80 excursion
  - EXTREME = Q95 excursion
  - RV1 = trailing 20-session daily realized-volatility ±1 sigma reference

No wall parameters may be changed in S2.

## Touch definition

For an upper level, touch occurs on the first 5m bar with high >= level.
For a lower level, touch occurs on the first 5m bar with low <= level.

A session contributes at most one first-touch observation per side and wall family.

## Frozen importance metrics

For each touched wall:

1. **Touch rate**
   - touched sessions / eligible sessions.

2. **Time to first touch**
   - minutes from UTC session open to first touching 5m interval.

3. **Extreme overshoot**
   - Upper: (HOD - level) / (level - open)
   - Lower: (level - LOD) / (open - level)
   - lower values mean the wall lies closer to the final session extreme.

4. **Near-extreme capture**
   - NE25: overshoot <= 0.25 wall-distance
   - NE50: overshoot <= 0.50 wall-distance

5. **Post-touch opposite reaction**
   - Upper: (level - minimum low from first-touch bar onward) / wall-distance
   - Lower: (maximum high from first-touch bar onward - level) / wall-distance
   - This is descriptive path response, not a trade return.

6. **Session close back inside**
   - Upper: session close < upper level
   - Lower: session close > lower level

7. **Same-side continuation to next wall**
   - MID -> WALL
   - WALL -> EXTREME
   - EXTREME and RV1: not defined.

## Splits

- DEV: 2022-2024
- REF: 2025-2026
- Annual: 2022, 2023, 2024, 2025, 2026

## Importance interpretation

S2 does not optimize thresholds and does not promote a trading rule.

A wall family is tagged **DECISION_POINT_SUPPORTED** only if, on both DEV and REF and on both sides:

- sample >= 50 touched sessions;
- NE25 rate is greater than the corresponding MID rate; and
- median normalized overshoot is lower than the corresponding MID median.

This tag means only that the level is statistically closer to session extremes than MID while retaining sample size. It does not imply reversal edge.

Even if the tag fails, S2 evidence is persisted and the failure reason is reported.

## Explicit exclusions

No candle-pattern filter, reclaim rule, acceptance rule, direction selector, entry, SL, TP, MFE/MAE trade outcome, WR, PF, or expectancy may be optimized in S2.
