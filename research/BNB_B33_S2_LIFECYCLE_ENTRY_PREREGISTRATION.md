# BNB B33-S2 — Lifecycle-Phase Entry Discovery Preregistration

## Scientific identity
`BNB_B33_S2_LIFECYCLE_ENTRY_V1`

Parent: `BNB_B33_S1_STRUCTURE_LIFECYCLE_V1`.

This protocol is frozen before B33-S1 EARLY-phase counts are inspected.

## Question
For each causal structure family, is there an actionable entry after the EARLY phase that is lost by waiting until the MATURE phase?

## Separation
The B33-S1 phase detector is immutable. S2 may only choose a causal entry trigger after a phase timestamp.
No TP/SL, MFE/MAE, PF, PnL, fees, leverage, sizing, DD, or economic optimization.

## Eligible phase universes
Only B33-S1 detectors marked `STRUCTURALLY_VIABLE` may be tested.
S2 must recompute the B33-S1 event ledger and require exact detector counts equal to the persisted B33-S1 summary.

Each of the 16 phase detectors is independent:
`family × direction × EARLY/MATURE`.

## Entry window
Fully closed 5m bars from phase completion through +60m.
If a policy never triggers, that occurrence is unfilled for that policy.

## Frozen six-policy grammar
### E0 PHASE_CLOSE
Entry at phase completion close.

### E1 NATIVE_LEVEL_RETEST
Use the B33 phase's causal structural level.
LONG: first post-phase 5m bar with low <= level and close > level.
SHORT: first with high >= level and close < level.

### E2 PHASE_MID_RETEST
Use midpoint of the completed 15m phase candle.
LONG: first low <= midpoint and close > midpoint.
SHORT: first high >= midpoint and close < midpoint.

### E3 PHASE_EXTREME_BREAK
LONG: first close > phase-candle high.
SHORT: first close < phase-candle low.

### E4 PULLBACK_RECLAIM
After at least one adverse post-phase 5m close-to-close move:
LONG: first later close above the high of the most recent adverse candle.
SHORT: first later close below the low of the most recent adverse candle.

### E5 FOLLOW_THROUGH_DISPLACEMENT
First directional 5m displacement after phase:
body_ratio >=0.55 and
- LONG: close>open, close_location>=0.50;
- SHORT: close<open, close_location<=-0.50.

No clock/session/day filters.

## S2 directional outcome only
Exact signed close-to-close +30m, +60m, +120m after filled entry.
Flat within 1e-12 is not a hit.
This is not trading win rate.

## Split
Development: 2022-2024 phase occurrences.
Reference: 2025-2026*, opened once only for at most one frozen development winner per phase detector.

## Development gate
1. filled N >=100;
2. each development year N>=25;
3. participation >=25%;
4. pooled +60 hit >=55%;
5. Wilson 95% LCB >52%;
6. every development-year +60 hit >=52%;
7. median signed +60 >0;
8. at least one of +30/+120 hit >=53%.

Ranking: worst dev-year hit, Wilson LCB, pooled +60 hit, participation, lexical policy id.
Freeze at most one entry policy per phase detector.

## Reference gate
1. 2025 N>=25 and 2026 N>=15;
2. reference participation >=25%;
3. combined +60 hit >=53%;
4. 2025 and 2026 each >50%;
5. Wilson 95% LCB >50%;
6. median signed +60 >0;
7. at least one of +30/+120 hit >=52%.

## Lifecycle interpretation
The primary comparison is descriptive:
- EARLY phase has a passing entry and MATURE does not: evidence that waiting for full maturity loses actionability.
- both pass: retain both as distinct candidates until economics.
- only MATURE passes: no support for the timing-loss hypothesis.
- neither passes: lifecycle timing does not solve the entry problem for that family.

No direct winner is selected between EARLY and MATURE in S2.

## Promotion
Only `PHASE_ENTRY_PASS` pairs may advance to B33-S3 economics.

## Anti-rescue
No phase edits, no new entry policies, no lower gates, no reference inspection without a development winner, and no economics for rejected pairs.
