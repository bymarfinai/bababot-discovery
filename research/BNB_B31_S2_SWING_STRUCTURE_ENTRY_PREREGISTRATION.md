# BNB B31-S2 — Per-Swing-Structure Entry Discovery Preregistration

## Scientific identity
`BNB_B31_S2_SWING_STRUCTURE_ENTRY_V1`

Parent: `BNB_B31_S1_SWING_STRUCTURE_LIBRARY_V1`.

S1 detector definitions, directions, event timestamps, and structural levels are immutable in S2. S2 may only choose a causal **entry trigger after structure completion**.

## Frozen parent counts
- S01 SWING_LOW_SWEEP_RECLAIM LONG: 8,274
- S02 HH_HL_SETUP LONG: 5,326
- S03 BREAK_RETEST_HOLD LONG: 4,348
- S04 FAILED_BREAKDOWN_RECLAIM LONG: 4,362
- S05 SWING_HIGH_SWEEP_REJECT SHORT: 8,553
- S06 LL_LH_SETUP SHORT: 5,039
- S07 BREAK_RETEST_REJECT SHORT: 3,936
- S08 FAILED_BREAKOUT_REJECT SHORT: 4,542

## Data / causality
Use the same Binance Vision 5m source and B31-S1 reconstruction. Recompute the exact S1 event universe and require all parent counts above. Raw/A1 identity guards remain mandatory.

Entry timestamp is always a fully closed 5m bar. Search window is the first 60 minutes after structure completion. If a policy does not trigger, that structure occurrence is simply unfilled for that policy.

No entry may use bars after its trigger timestamp.

## Frozen entry grammar
For every structure, test exactly six causal policies.

### E0 STRUCTURE_CLOSE
Enter at the 5m close coincident with structure completion.

### E1 STRUCTURE_CANDLE_EXTREME_BREAK
Within 60m:
- LONG: first 5m close strictly above the completed 15m structure candle high.
- SHORT: first 5m close strictly below its low.

### E2 STRUCTURAL_LEVEL_RETEST
Use the frozen S1 structural level.
Within 60m:
- LONG: first 5m bar with low <= level and close > level.
- SHORT: first 5m bar with high >= level and close < level.

Interpretation is structure-specific automatically:
- sweep structures retest the swept swing level;
- HH/HL and LL/LH retest the confirmed HL/LH pivot level;
- break-retest structures retest the broken swing;
- failed-break structures retest the reclaimed/rejected swing.

### E3 MICRO_BOS_3BAR
Within 60m:
- LONG: first 5m close > maximum high of the preceding three fully closed 5m bars.
- SHORT: first close < minimum low of preceding three bars.

### E4 PULLBACK_RECLAIM
After at least one adverse 5m close-to-close move after structure completion:
- LONG: first subsequent close above the high of the most recent adverse candle.
- SHORT: first subsequent close below the low of the most recent adverse candle.

### E5 STRUCTURE_MID_RETEST
15m structure-candle midpoint = (high+low)/2.
Within 60m:
- LONG: first bar low <= midpoint and close > midpoint.
- SHORT: first bar high >= midpoint and close < midpoint.

No time/session/day filter is allowed.

## Outcome used only for entry selection
This is still not economics.
For each filled entry measure signed close-to-close direction at exact +30m, +60m, +120m:
- LONG signed return = future_close / entry_close - 1;
- SHORT signed return = -(future_close / entry_close - 1);
- WIN/hit iff signed return > 1e-12; flat is not a hit.

No TP/SL, intrabar excursion, PnL, fees, PF, DD, leverage, or sizing.

## Split
Development only: 2022, 2023, 2024 structure occurrences.
Reference: 2025 and 2026* opened only for one frozen development winner per structure.

## Development gate
A policy is eligible for freezing only if:
1. filled N >= 120;
2. each development year N >= 30;
3. participation >=25% of that structure's development events;
4. pooled +60m hit >=55%;
5. Wilson 95% LCB for +60m >52%;
6. each development-year +60 hit >=52%;
7. median signed +60m >0;
8. at least one of +30m/+120m hit >=53%.

Rank eligible policies by:
1. worst development-year hit;
2. Wilson LCB;
3. pooled +60 hit;
4. participation;
5. policy id lexical.

Freeze at most one entry policy per structure.

## Reference gate
A frozen structure+entry pair passes only if:
1. 2025 N >=30 and 2026 N >=20;
2. reference participation >=25%;
3. combined reference +60 hit >=53%;
4. 2025 hit >50% and 2026 hit >50%;
5. reference Wilson LCB >50%;
6. median signed +60m >0;
7. at least one of +30m/+120m hit >=52%.

## Promotion
Only `STRUCTURE_ENTRY_PASS` pairs may advance to B31-S3 economics.
A directional hit is not trading win rate.

## Anti-rescue
- do not alter S1 structures;
- do not lower gates;
- do not add policies after seeing outcomes;
- do not inspect reference for structures with no development winner;
- do not start economics for rejected pairs.
