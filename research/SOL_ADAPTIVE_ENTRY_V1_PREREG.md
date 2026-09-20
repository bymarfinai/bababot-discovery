# SOL Adaptive Entry V1 — Preregistration

## Objective

Find the most efficient **causal entry mechanism** after the already-validated SOL structural-liquidity detector fires.

This phase starts only after:
- H1 swing liquidity is directly swept;
- reclaim is complete;
- the frozen detector score is **>= 3 of 4**;
- the decision is known at the H1 reclaim close.

This phase does NOT optimize:
- stop-loss;
- take-profit;
- position sizing;
- leverage;
- PnL;
- session/hour;
- indicator/regime filters.

## Frozen detector

Reuse SOL Structural Liquidity Detector V3 unchanged.

Detector conditions:
- A: source_to_opposite_structure_range_units <= 2.073485713625842
- B: approach_start_distance_to_level_range_units <= 1.4084118083030879
- C: reclaim_directional_body_range_units >= 0.4999999999999881
- D: reclaim_close_inside_range_units >= 0.6013241386375646
- detector = anatomy_score >= 3

No detector threshold may be changed.

## Scientific split

- 2020-2024 = entry construction.
- 2025 = frozen entry confirmation. It is not whole-system untouched because V3 already used it for detector validation, but no entry rule has been selected from 2025.
- 2026 YTD = unopened entry holdout. It is processed only if one entry rule passes 2025 confirmation.
- Events whose structural response is right-censored at the data end are excluded.
- No 2026 value may influence entry construction or 2025 confirmation.
- 2026 YTD is the final untouched entry check for V1.

## Side convention

- BUY_SIDE liquidity sweep -> bearish reversal direction -> SHORT entry.
- SELL_SIDE liquidity sweep -> bullish reversal direction -> LONG entry.

## Signal timestamp

The detector is actionable only when the reclaim H1 candle has fully closed.

`signal_time = reclaim_time + 1 hour`

The immediate baseline is the open of the first complete 5m bar at or after signal_time.

## Entry search deadline

An adaptive entry must occur before BOTH:

1. 6 hours after signal_time;
2. the start of the H1 bar that resolves the structural label, when such a resolution bar exists.

This prevents an entry from using the H1 bar that later confirms BOS or invalidation.

If no entry occurs before the deadline, the signal is MISSED for that entry variant.

## Frozen entry variants

### BASELINE_MARKET

Enter at the first 5m OPEN at or after signal_time.

This is the comparator and cannot be selected as the adaptive winner.

### GAP_25

Limit entry 25% of the way from reclaim close back toward the swept liquidity level:

`reclaim_close + 0.25 * (liquidity_level - reclaim_close)`

### GAP_50

Same formula at 50%.

### GAP_75

Same formula at 75%.

### LIQUIDITY_LEVEL

Limit entry exactly at the swept H1 liquidity level.

### RECLAIM_BODY_MID

Limit entry at:
`(reclaim_open + reclaim_close) / 2`

### RECLAIM_OPEN

Limit entry at the reclaim H1 OPEN.

### FIVE_MIN_REVERSAL_BREAK

Confirmation entry.

Starting at signal_time:
- SHORT: wait for first completed 5m candle CLOSE strictly below the reclaim H1 LOW;
- LONG: wait for first completed 5m candle CLOSE strictly above the reclaim H1 HIGH;
- enter at the next 5m OPEN;
- confirmation and entry must occur before the frozen entry deadline.

No lower-timeframe pivot search or threshold optimization is allowed.

## Limit fill semantics

For SHORT limit entries:
- filled when a completed/active 5m bar HIGH reaches or exceeds the limit price.

For LONG limit entries:
- filled when a 5m bar LOW reaches or falls below the limit price.

Execution price is the frozen limit price, even if the bar gaps through it. This is conservative with respect to price improvement.

If the first eligible 5m open is already beyond a limit in a marketable direction:
- fill at the frozen limit price, not a more favorable open.

## Structural labels

Entry variants are evaluated against the already-frozen structural outcome:
- positive = STRUCTURAL_LIQUIDITY_EVENT;
- negative = RECLAIM_FAILED_BEFORE_BOS or RECLAIM_NO_BOS_WITHIN_WINDOW.

No TP/SL label is introduced.

## Entry-quality metrics

For every variant report:

1. detector signals N;
2. filled N;
3. overall fill rate;
4. positive structural events N;
5. positive events filled N;
6. positive-event capture rate;
7. negative-event fill rate;
8. structural-event rate among filled entries;
9. median time-to-fill;
10. median directional price improvement vs BASELINE_MARKET in prior-H1-range units;
11. same median improvement on positive structural events only;
12. p25 positive-event improvement;
13. median structural-target distance from entry in prior-H1-range units;
14. median post-entry adverse excursion until structural resolution, on positive events only.

Directional price improvement:
- SHORT: (adaptive entry - market baseline entry) / prior median H1 range;
- LONG: (market baseline entry - adaptive entry) / prior median H1 range.

Positive means better entry price than immediate market.

Structural-target distance:
- SHORT: (entry - significant opposite low) / prior median H1 range;
- LONG: (significant opposite high - entry) / prior median H1 range.

## Construction gates — 2020-2024

An adaptive variant is eligible only if:

1. filled N >= 150;
2. positive-event capture rate >= 70%;
3. structural-event rate among fills >= detector baseline structural-event rate - 3 percentage points;
4. median positive-event price improvement > 0;
5. p25 positive-event price improvement >= -0.05 H1 range units;
6. positive-event capture rate >= 60% on BUY_SIDE;
7. positive-event capture rate >= 60% on SELL_SIDE.

Select exactly one eligible adaptive variant by:
1. highest median positive-event price improvement;
2. then highest p25 positive-event price improvement;
3. then highest positive-event capture rate;
4. then highest structural-event rate among fills;
5. then lower median time-to-fill;
6. then lexicographic variant name.

If no adaptive variant is eligible:
**NO_ADAPTIVE_ENTRY_CONSTRUCTION_RULE**.

## Frozen 2025 confirmation gates

The construction winner passes 2025 only if:

1. filled N >= 40;
2. positive-event capture rate >= 65%;
3. structural-event rate among fills >= 2025 detector baseline - 5 percentage points;
4. median positive-event price improvement > 0;
5. BUY_SIDE positive-event capture >= 55%;
6. SELL_SIDE positive-event capture >= 55%.

Only if all pass may 2026 YTD be opened.

If confirmation fails:
**ADAPTIVE_ENTRY_NOT_CONFIRMED_2025**.

No alternate construction variant may be substituted after observing 2025.

## Untouched 2026 YTD validation gates

The frozen entry variant is called:
**VALIDATED_ADAPTIVE_ENTRY**

only if all are true:

1. detector signals N >= 30;
2. filled N >= 20;
3. positive structural events N >= 10;
4. positive-event capture rate >= 60%;
5. structural-event rate among fills >= 2026 detector baseline - 5 percentage points;
6. median positive-event price improvement > 0;
7. BUY_SIDE positive-event capture >= 50% when BUY_SIDE has >= 5 positive events;
8. SELL_SIDE positive-event capture >= 50% when SELL_SIDE has >= 5 positive events.

If the available 2026 sample is too small for the frozen minimums:
**2026_ENTRY_HOLDOUT_INSUFFICIENT_SAMPLE**.

If sample is sufficient but any quality gate fails:
**ADAPTIVE_ENTRY_NOT_VALIDATED_AS_DEFINED**.

No threshold rescue or candidate switching is permitted.

## Interpretation

A validated adaptive entry means:

> after the validated structural-liquidity detector fires, this execution mechanism improves entry location versus immediate market while retaining most true structural moves and without materially degrading structural precision.

It does not yet define risk or reward.

Next phases remain:
**Adaptive SL -> Adaptive TP -> full ready-to-trade validation**.

2027_PLUS=CLOSED
