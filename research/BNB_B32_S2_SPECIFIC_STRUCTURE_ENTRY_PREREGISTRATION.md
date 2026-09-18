# BNB B32-S2 — Structure-Specific Entry Discovery Preregistration

## Scientific identity
`BNB_B32_S2_SPECIFIC_STRUCTURE_ENTRY_V1`

Parent: `BNB_B32_S1_SPECIFIC_PRICE_ACTION_LIBRARY_V1`.

S1 detector definitions, completion timestamps, directions, structural levels, and counts are immutable.

## Frozen parent counts
- S01 LIQUIDITY_SWEEP_DISPLACEMENT_LONG: 1,980
- S02 IMPULSE_HL_READY_LONG: 2,021
- S03 COMPRESSION_BREAK_RETEST_LONG: 639
- S04 FAILED_BREAK_DISPLACEMENT_LONG: 2,702
- S05 LIQUIDITY_SWEEP_DISPLACEMENT_SHORT: 1,863
- S06 IMPULSE_LH_READY_SHORT: 1,789
- S07 COMPRESSION_BREAK_RETEST_SHORT: 548
- S08 FAILED_BREAK_DISPLACEMENT_SHORT: 2,637

## Stage separation
S2 searches only for a causal entry trigger after structure completion.
Forbidden: TP/SL, MFE/MAE, PF, PnL, fees, leverage, sizing, DD.

## Entry window
Only fully closed 5m bars from structure completion through +60m.
If a policy never triggers, the occurrence is unfilled for that policy.

## Structure-specific entry families

Each structure gets the same six causal concepts, but the structural level is native to that structure:
- sweep level for S01/S05;
- confirmed HL/LH pivot for S02/S06;
- broken swing level for S03/S07;
- reclaimed/rejected failed-break level for S04/S08.

### E0 COMPLETION_CLOSE
Enter at structure completion close.

### E1 NATIVE_LEVEL_RETEST
LONG: first post-completion 5m bar with low <= native level and close > level.
SHORT: first with high >= level and close < level.

### E2 COMPLETION_MID_RETEST
Use midpoint of the completed 15m structure candle.
LONG: first low <= midpoint and close > midpoint.
SHORT: first high >= midpoint and close < midpoint.

### E3 COMPLETION_EXTREME_BREAK
LONG: first close > completed 15m structure high.
SHORT: first close < completed 15m structure low.

### E4 PULLBACK_RECLAIM
After at least one adverse post-completion 5m close-to-close move:
LONG: first later close above the high of the most recent adverse candle.
SHORT: first later close below the low of the most recent adverse candle.

### E5 FOLLOW_THROUGH_DISPLACEMENT
First post-completion 5m directional displacement bar:
- body_ratio >= 0.55;
- LONG close>open and close_location>=0.50;
- SHORT close<open and close_location<=-0.50.

No clock/session/day filters.

## Directional outcome for S2 only
For each filled entry:
- exact signed close-to-close +30m, +60m, +120m;
- flat within 1e-12 is not a hit.

This is not trading economics.

## Split
Development: structure occurrences in 2022-2024.
Reference: 2025-2026*, opened once for at most one frozen development winner per structure.

## Development gate
1. filled N >=100;
2. each development year N>=25;
3. participation >=25%;
4. +60 hit >=55%;
5. Wilson 95% LCB >52%;
6. each dev-year hit >=52%;
7. median signed +60 >0;
8. at least one of +30/+120 hit >=53%.

Ranking: worst dev-year hit, Wilson, pooled +60 hit, participation, lexical policy id.

## Reference gate
1. 2025 N>=25 and 2026 N>=15;
2. participation >=25%;
3. combined +60 hit >=53%;
4. each reference era >50%;
5. Wilson 95% LCB >50%;
6. median signed +60 >0;
7. at least one +30/+120 hit >=52%.

## Promotion
Only STRUCTURE_ENTRY_PASS pairs advance to B32-S3 economics.

## Anti-rescue
No structure edits, no new entry policies, no lowered gates, no reference inspection for structures without a dev winner, and no economics for rejected pairs.
