# BNB B32-S1 — Specific Price-Action Structure Library Preregistration

## Scientific identity
`BNB_B32_S1_SPECIFIC_PRICE_ACTION_LIBRARY_V1`

B32 is a new scientific identity after B31 stopped at entry discovery. It does not alter or rescue B31.

## Stage separation
S1 is structure-only. Forbidden in S1: entry selection, forward WIN/LOSS, return, MFE/MAE, TP/SL, PF, PnL, fees, leverage, DD, session/hour filters.

Pipeline:
`B32-S1 specific structure -> B32-S2 structure-specific entry -> B32-S3 economics -> OOS/shadow`.

## Data / causality
Reuse B31 causal 15m reconstruction from Binance Vision 5m and accepted A1 identity guards.
Census: 2022-01-01 through 2026-08-26 00:00 UTC.
Confirmed pivots use the frozen 2-left/2-right rule and become available only on the pivot confirmation bar.

## Frozen structural primitives
For a completed 15m bar:
- range = high-low.
- body_ratio = abs(close-open)/range.
- close_location = ((close-low)-(high-close))/range.
- bullish displacement bar: close>open, body_ratio>=0.55, close_location>=0.50.
- bearish displacement bar: close<open, body_ratio>=0.55, close_location<=-0.50.
- compression3: the three immediately preceding completed 15m bars have strictly non-increasing true ranges and the third range <=0.75 * first range.
- swing impulse magnitude is measured between confirmed swing prices.
- pullback depth = retracement from the latest impulse extreme relative to the prior confirmed impulse leg.

## Frozen detector library

### S01 LIQUIDITY_SWEEP_DISPLACEMENT_LONG
A prior confirmed swing low exists.
1. bar t sweeps it: low < level and close >= level;
2. bar t or t+1 is a bullish displacement bar;
3. displacement close > sweep-bar midpoint.
Completion is the displacement close.

### S02 IMPULSE_HL_READY_LONG
At confirmation of a new swing low:
1. latest two confirmed swing highs are rising;
2. latest two confirmed swing lows are rising;
3. prior upswing amplitude (latest swing high - previous swing low) >= 1.25 * median 15m true range over previous 16 bars;
4. pullback depth from latest swing high to new higher low is between 25% and 75% of that prior upswing;
5. confirmation bar close >= midpoint of its own range.
Completion is higher-low confirmation.

### S03 COMPRESSION_BREAK_RETEST_LONG
1. compression3 immediately precedes a close above the latest previously confirmed swing high;
2. breakout bar is bullish with body_ratio>=0.45;
3. within next 1-3 completed 15m bars, low <= broken level and close > broken level.
Completion is retest-hold close.

### S04 FAILED_BREAK_DISPLACEMENT_LONG
1. a close breaks below latest confirmed swing low;
2. within next 1-3 bars, a close returns >= broken level;
3. reclaim bar or next bar is bullish displacement;
4. displacement close > broken level.
Completion is displacement close.

### S05 LIQUIDITY_SWEEP_DISPLACEMENT_SHORT
Mirror of S01 at confirmed swing high with bearish displacement.

### S06 IMPULSE_LH_READY_SHORT
Mirror of S02:
- falling confirmed highs/lows;
- prior downswing amplitude >=1.25x prior-16 median true range;
- pullback depth 25%-75%;
- confirmation-bar close <= midpoint.

### S07 COMPRESSION_BREAK_RETEST_SHORT
Mirror of S03 below latest confirmed swing low.

### S08 FAILED_BREAK_DISPLACEMENT_SHORT
Mirror of S04 above latest confirmed swing high.

## De-duplication
Per-detector 90-minute cooldown, retaining the first causal completion. Cross-family overlap is measured, not suppressed.

## S1 viability
A detector is STRUCTURALLY_VIABLE iff:
1. pooled N >= 100;
2. at least 4/5 eras have >=12 detections;
3. max era share <=35%;
4. median same-detector gap >=90 minutes;
5. all data/causality guards pass.

No outcome statistic participates in S1 viability.

## Anti-rescue
- no changing thresholds after counts are seen;
- no hour/session/day filters;
- no outcome-based pruning;
- no entry or economics before S1 is frozen.
