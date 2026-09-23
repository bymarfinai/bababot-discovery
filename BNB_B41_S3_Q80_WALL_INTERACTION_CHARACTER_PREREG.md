# BNB B41-S3 — Q80 Wall Interaction Character Discovery Preregistration

## Objective

Discover causal interaction characters at the frozen B41 Q80 structural wall.

S3 does not optimize an entry, stop, target, win rate, profit factor, or expectancy. It asks only:

> After the first touch of a Q80 wall, what 15-minute interaction state becomes observable, and what directional path tends to follow after that state is known?

## Frozen parents

- B41-S1 wall signature:
  `4eb6cc9ef940d80b447b8b93e3a3df7f8093f60411d5f01500a2968899a27db6`
- B41-S2 signature:
  `53bd3077c750580e4c77e9ebb0d1b13ea8ce37fb750871538ca7c7694f46b3b2`
- Wall family: Q80 WALL only.
- First-touch events: exactly the B41-S2 WALL first-touch ledger.
- DEV: 2022-2024.
- REF: 2025-2026.

No wall definition may be modified in S3.

## Causal observation window

The detector observes exactly three completed 5m bars:

1. the first-touch bar;
2. the next completed 5m bar;
3. the following completed 5m bar.

Thus the character is known only at the close of the third bar. All outcome metrics begin strictly **after** that detector timestamp.

Events without all three same-session bars are marked insufficient and excluded from character outcomes.

## Outside/inside state

For an UPPER wall:
- OUTSIDE = 5m close > wall
- INSIDE = 5m close <= wall

For a LOWER wall:
- OUTSIDE = 5m close < wall
- INSIDE = 5m close >= wall

## Frozen character taxonomy

Using the three close states:

- **C1_CLEAN_REJECTION**: no OUTSIDE closes (000).
- **C2_RECLAIM_AFTER_CLOSE**: one or more OUTSIDE closes occurred, but the third close is INSIDE.
- **C3_ACCEPTANCE_HOLD**: the final two closes are both OUTSIDE.
- **C4_UNSETTLED_BREAK**: the third close is OUTSIDE but C3 is not satisfied.

The four states are mutually exclusive and exhaustive for eligible events.

No penetration threshold, candle-size threshold, wick ratio, volume filter, or timing optimization is used to assign the character.

## Descriptive interaction diagnostics

During the three-bar character window, record:
- number of OUTSIDE closes;
- maximum penetration beyond wall, normalized by wall distance from session open;
- maximum inward move, normalized by wall distance.

These are descriptive only and do not alter character labels.

## Frozen post-character outcomes

All are measured strictly after the detector timestamp.

1. **Signed 60m close displacement**
   - positive = movement inward from the touched wall;
   - negative = movement farther outward.
2. **Signed 180m close displacement**
   - same convention.
3. **Maximum inward excursion to session end**, normalized by wall distance.
4. **Maximum outward excursion to session end**, normalized by wall distance.
5. **Inward dominance** = max inward excursion > max outward excursion.
6. **Equilibrium reached** after the character:
   - UPPER: price later reaches session open or below;
   - LOWER: price later reaches session open or above.
7. **Q95 EXTREME reached** after the character.
8. **Session close inside** the Q80 wall.

## Stability label

For each side × character, if DEV and REF each have at least 20 observations with a valid 180m outcome:

- **STABLE_INWARD** if median signed 180m displacement > 0 in both DEV and REF.
- **STABLE_OUTWARD** if median signed 180m displacement < 0 in both DEV and REF.
- **MIXED** otherwise.
- **INSUFFICIENT** if either period has <20 valid 180m observations.

This label is descriptive. It is not a trading rule.

## Explicit exclusions

S3 does not:
- select LONG or SHORT entries;
- choose an execution bar;
- define SL;
- define TP;
- calculate trade WR, PF, expectancy, PnL;
- search alternative observation windows;
- search alternative close-count rules.

Those belong to later stages.
