# BNB B30-S2B — Structure-Specific 5m Entry Discovery Preregistration

## Scientific identity
`BNB_B30_S2B_STRUCTURE_SPECIFIC_ENTRY_V1`

Parent structure identity: `BNB_B30_S1_STRUCTURE_LIBRARY_V1`.

S2A showed that a small universal entry-archetype set did not pass development for any of the eight structures. That does **not** reject the structures. S2B implements the methodology intended by B30: each structure receives entry mechanisms that are defined from that structure's own price-action geometry.

S2B is a new scientific identity. Its entry rules below are frozen before any S2B outcome is evaluated.

## Separation rule
- S1 detector definitions are immutable.
- S2B may use post-structure 5m bars only to trigger an entry.
- S2B does not use TP/SL, MFE/MAE, PnL, fees, leverage, expectancy, PF, DD or loss streak.
- Economics remains S3 only.

## Data
### Structure identity
Use accepted B29-A1 artifact and reconstruct exact S1 events. Expected S1 counts remain:
S01=8092, S02=797, S03=1577, S04=5109, S05=8542, S06=637, S07=1207, S08=5553.

### 5m execution-path source
Binance Vision USD-M Futures `BNBUSDT` 5m monthly klines. The run records source-file count, row count, boundaries, and deterministic SHA256 of the normalized OHLC path used by S2B.

Raw 5m bars are converted from Binance bar-open timestamps to bar-close timestamps by adding 5 minutes.

Integrity guards before S2B evaluation:
1. raw 5m coverage >=99.5%;
2. A1 15m close-to-close `ret_15` reconstructed from raw 5m closes must match immutable A1 within 5e-8 over the 2022–2026 census overlap;
3. raw current-bar `close_location` at S1 event timestamps must match immutable A1 within 5e-8 where finite.
Failure is tooling/data failure, not a strategy verdict.

## Split
- Development: structures completed in 2022–2024.
- One-shot reference: structures completed in 2025–2026 immutable cutoff.

Exactly one development winner per structure may be exposed to reference. A failed reference winner cannot be replaced by the second-best S2B policy.

## Causal scan window
For every structure completion timestamp `t`, entry triggers may inspect fully closed 5m bars strictly after `t` through `t+60m`. Entry occurs at the close of the first qualifying 5m bar. If no qualifying bar appears, that structure occurrence has no entry for that policy.

## Shared primitives
### `MICRO_BOS_3BAR`
At candidate 5m close `q`:
- LONG: `close(q) > max(high)` of the three immediately preceding fully closed 5m bars;
- SHORT: `close(q) < min(low)` of the three preceding bars.

### `PULLBACK_RECLAIM`
After `t`, first observe at least one adverse 5m candle by close-to-close direction. Freeze the most recent adverse candle extreme. Entry at the first later 5m close that breaks that adverse candle high for LONG or low for SHORT. If another adverse candle occurs before reclaim, update the frozen adverse extreme to that most recent adverse candle.

### `STRUCTURE_EXTREME_BREAK`
The structure candle is the 15m window ending at `t` (three 5m bars). LONG enters on first later 5m close above its high; SHORT enters below its low.

## Frozen policy sets by structure
Each structure has exactly five policies including baseline E0.

### S01 `SWEEP_LOW_RECLAIM` LONG
- E0 `STRUCTURE_CLOSE`
- E1 `SWEEP_LEVEL_RETEST_HOLD`: prior-60m low immediately preceding the sweep bar is revisited (`low <= level`) and the 5m bar closes back above the level.
- E2 `RECLAIM_CANDLE_HIGH_BREAK`: `STRUCTURE_EXTREME_BREAK` long.
- E3 `MICRO_BOS_3BAR`
- E4 `PULLBACK_RECLAIM`

### S05 `SWEEP_HIGH_REJECT` SHORT
Exact mirror of S01 using prior-60m high and closes back below.

### S04 `FAILED_BREAKDOWN_RECLAIM` LONG
- E0 `STRUCTURE_CLOSE`
- E1 `BROKEN_LOW_RETEST_HOLD`: use the prior-60m low reference belonging to the exact `t-15m` break-low bar; enter when a post-structure 5m bar revisits that level and closes back above it.
- E2 `RECLAIM_CANDLE_HIGH_BREAK`
- E3 `MICRO_BOS_3BAR`
- E4 `PULLBACK_RECLAIM`

### S08 `FAILED_BREAKOUT_REJECT` SHORT
Exact mirror of S04 using the prior high of the `t-15m` break-high bar.

### S02 `HL_CONTINUATION` LONG
- E0 `STRUCTURE_CLOSE`
- E1 `HL_MID_RETEST_HOLD`: structure 15m candle midpoint is touched (`low <= midpoint`) and the bar closes back above midpoint.
- E2 `CONTINUATION_HIGH_BREAK`: close above the structure 15m high.
- E3 `MICRO_BOS_3BAR`
- E4 `PULLBACK_RECLAIM`

### S06 `LH_CONTINUATION` SHORT
Exact mirror of S02: midpoint retest/reject and structure-low continuation break.

### S03 `BREAK_HIGH_HOLD` LONG
- E0 `STRUCTURE_CLOSE`
- E1 `BREAKOUT_LEVEL_RETEST_HOLD`: breakout reference is the prior-60m high belonging to the exact `t-15m` first hold bar; enter when a later 5m bar touches that level and closes above it.
- E2 `SECOND_EXPANSION_HIGH_BREAK`: close above the structure 15m high.
- E3 `MICRO_BOS_3BAR`
- E4 `PULLBACK_RECLAIM`

### S07 `BREAK_LOW_HOLD` SHORT
Exact mirror of S03.

## Directional entry evaluation
Numerical flat tolerance: `1e-12`. Flat is not a hit.

From the actual 5m entry close, evaluate close-to-close signed returns at exact +30m, +60m (primary), and +120m. LONG signed return is raw return; SHORT signed return is negative raw return.

This is directional-entry evidence only, not economic simulation.

## Development eligibility
A structure × policy is eligible iff:
1. development N >=100;
2. each 2022/2023/2024 N >=20;
3. participation >=25%;
4. pooled +60m directional hit >=55%;
5. Wilson 95% lower bound >50%;
6. each development year +60m hit >=52%;
7. median signed +60m return >0;
8. at least one auxiliary (+30/+120) hit >=53%.

## Winner selection
Within each structure, select exactly one eligible policy by:
1. highest worst development-era +60m hit;
2. highest Wilson lower bound;
3. highest pooled +60m hit;
4. higher participation;
5. lexical policy id.

## One-shot reference gate
Selected policy passes iff:
1. 2025 N >=15 and 2026 N >=10;
2. reference participation >=25%;
3. combined reference +60m hit >=53%;
4. both 2025 and 2026 +60m hit >50%;
5. combined median signed +60m return >0;
6. at least one reference auxiliary horizon hit >=52%.

## Handoff
Only a `(structure detector, structure-specific entry policy)` pair passing S2B can enter S3 economics. S3 must freeze this pair exactly and may not redefine the structure or entry trigger.

## Anti-rescue
No session filters, no threshold tuning after outcomes, no alternative reference candidate after failure, no merging structures, and no TP/SL search in S2B.
