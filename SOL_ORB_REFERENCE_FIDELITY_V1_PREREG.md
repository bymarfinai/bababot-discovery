# SOL ORB Reference Fidelity Detector v1 — Preregistration

## Purpose
Rebuild the SOL ORB detector so that it matches the literal structure shown in the reference image as closely as possible before judging the idea.

Reference sequence used here:
1. 15-minute ORB.
2. Upside break above ORB High.
3. Bullish confirmation by candle/wick reaction or a small break of structure.
4. Price above VWAP as bullish confirmation.
5. Entry either from the confirmed retest path or the small-BOS path.

This experiment discovers the character of that structure; it does not tune TP/SL and does not open Reference/OOS.

## Crypto anchor assumption
The image does not specify a crypto session open. Therefore the only non-image assumption is to test every UTC hour as a possible session anchor. For each HH:00 anchor:
- ORB = HH:00, HH:05, HH:10 bars.
- Breakout habitat = HH:15 through HH:55.
- VWAP is anchored to that same HH:00 session start and calculated causally from typical price * volume.

The 24h sweep is used to discover whether any hour behaves like a meaningful opening session. We do not preselect an hour.

## Frozen event definitions
### ORB
- `ORB_HIGH = max(high)` of first three 5m candles.
- `ORB_LOW = min(low)` of first three 5m candles.

### Breakout
- First 5m close above ORB_HIGH from HH:15 through HH:55.
- Record whether breakout close is above anchored VWAP.

### Retest
Within 30m after breakout, first candle whose low trades to or below ORB_HIGH.

### Bullish candle / wick reaction
At the retest candle:
- `reclaim = close >= ORB_HIGH`.
- `bullish_body = close > open`.
- `lower_wick = min(open, close) - low`.
- `body = abs(close - open)`.
- `wick_rejection = lower_wick >= body`.
- `bullish_reaction = reclaim AND (bullish_body OR wick_rejection)`.
- VWAP confirmation requires retest close > anchored VWAP at that close.

`RETEST_REACTION_VWAP` signal occurs when bullish_reaction and VWAP confirmation are both true. Entry is next 5m open. This is the executable interpretation of "enter on the retest" without same-bar hindsight fill.

### Small break of structure
After a retest touch, define the local micro-structure level as:
- max(high of retest candle, high of the immediately preceding 5m candle).

Within the next three 5m candles, the first close above that level is `SMALL_BOS`. It must also close above ORB_HIGH and above anchored VWAP.

`SMALL_BOS_VWAP` entry = next 5m open after the BOS close.

### Combined confirmation
`REACTION_THEN_BOS_VWAP` requires both a bullish retest reaction and a later small BOS with VWAP confirmation. Entry = next 5m open after BOS.

### Reference-union path
`REFERENCE_UNION` enters on the earliest causal signal among:
- RETEST_REACTION_VWAP
- SMALL_BOS_VWAP

This best approximates the image phrase "enter during break of structure or retest of ORB resistance".

## Development universe
- SOLUSDT 5m
- Weekdays
- Development only: 2022-01-01 <= timestamp < 2025-01-01
- All 24 UTC anchor hours
- LONG only
- Reference/OOS closed

## Economics
For each executable variant:
- entry = next 5m open after signal close
- fixed exits: +15m, +30m, +60m, +120m
- reference notional = $500/trade
- round-trip cost = 0.15%
- max one event per variant per anchor session

## Outputs
- event-level structure table
- structural prevalence by UTC/WIB hour
- economics by variant/hour/exit
- year stability by variant/hour/exit for 2022, 2023, 2024
- pooled economics by structure variant

## Stop / anti-overfit rules
- No EMA/Fibonacci/RSI/volume-threshold/regime filters.
- Volume is used only to calculate VWAP.
- No ORB duration sweep.
- No wick/body threshold sweep.
- No BOS lookback sweep.
- No TP/SL optimization.
- No hour dropping during this run.
- No Reference/OOS opening.
- Results may nominate a structural archetype, but any final gate requires a separate preregistered confirmation test.
