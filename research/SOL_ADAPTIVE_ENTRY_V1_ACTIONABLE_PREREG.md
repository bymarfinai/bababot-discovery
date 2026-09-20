# SOL Adaptive Entry V1 — Actionable Detector Preregistration

## Objective

Discover a causal entry mechanism after the validated actionable SOL structural-liquidity detector fires.

The detector is frozen:
- direct H1 swing sweep;
- reclaim complete;
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded.

This phase does NOT optimize SL, TP, leverage, sizing, PnL, hour/session, indicators, or regime.

## Scientific split

- 2020-2024 = entry construction.
- 2025 = frozen entry confirmation.
- 2026 YTD = untouched entry holdout, opened only if the construction winner passes 2025.
- 2027+ CLOSED.

2025 was previously used to validate the detector, but no entry rule was selected from 2025.

## Actionable signal time

The detector becomes actionable only after the reclaim H1 candle closes:

`signal_time = reclaim_time + 1 hour`

BUY_SIDE sweep -> SHORT.
SELL_SIDE sweep -> LONG.

## Frozen entry search window

Entry must occur before both:
1. 6 hours after signal_time;
2. the close of the H1 bar that resolves the structural label, if one exists.

If the resolution H1 bar starts at `resolution_time`, its outcome is only known at:
`resolution_time + 1 hour`.

Therefore 5m fills occurring inside that H1 bar are allowed, but no fill at or after its close is allowed.

For unresolved-window negatives, the search window ends 6 hours after signal_time.

## Frozen entry variants

### BASELINE_MARKET

Comparator only.

Enter at the OPEN of the first 5m bar at or after signal_time.

### GAP_25

Limit:
`reclaim_close + 0.25 * (liquidity_level - reclaim_close)`

### GAP_50

Limit:
`reclaim_close + 0.50 * (liquidity_level - reclaim_close)`

### GAP_75

Limit:
`reclaim_close + 0.75 * (liquidity_level - reclaim_close)`

### LIQUIDITY_LEVEL

Limit exactly at the swept H1 liquidity level.

### RECLAIM_BODY_MID

Limit at:
`(reclaim_open + reclaim_close) / 2`

### RECLAIM_OPEN

Limit at the reclaim H1 OPEN.

### FIVE_MIN_REVERSAL_BREAK

Confirmation entry:
- SHORT: first completed 5m close strictly below reclaim H1 LOW;
- LONG: first completed 5m close strictly above reclaim H1 HIGH;
- enter at the next 5m OPEN;
- both confirmation and entry must occur before the frozen entry deadline.

No other lower-timeframe structure is searched.

## Limit fill semantics

SHORT:
- fill when a 5m HIGH >= limit.

LONG:
- fill when a 5m LOW <= limit.

Execution is recorded at the frozen limit price even if the bar gaps through it.

## Entry-quality metrics

For every variant:

1. detector signal N;
2. filled N and fill rate;
3. positive structural-event N;
4. positive events filled;
5. positive-event capture rate;
6. negative-event fill rate;
7. structural-event rate among filled;
8. median time-to-fill;
9. directional price improvement vs BASELINE_MARKET in prior-20-H1 median-range units;
10. same median on positive events only;
11. p25 positive-event price improvement;
12. median structural-target distance from entry in range units;
13. median post-entry adverse excursion until structural outcome is known, on positive events.

Directional price improvement:
- SHORT: (adaptive entry - baseline market entry) / H1 range unit;
- LONG: (baseline market entry - adaptive entry) / H1 range unit.

Positive = better entry price than immediate market.

Structural target distance:
- SHORT: (entry - significant opposite LOW) / H1 range unit;
- LONG: (significant opposite HIGH - entry) / H1 range unit.

## Construction gates — 2020-2024

An adaptive variant is eligible only if:

1. filled N >= 150;
2. positive-event capture >= 70%;
3. filled structural-event rate >= detector baseline rate - 3 percentage points;
4. median positive-event price improvement > 0;
5. p25 positive-event price improvement >= -0.05 range units;
6. BUY_SIDE positive-event capture >= 60%;
7. SELL_SIDE positive-event capture >= 60%.

Select one by:
1. highest median positive-event price improvement;
2. highest p25 positive-event improvement;
3. highest positive-event capture;
4. highest filled structural-event rate;
5. lower median time-to-fill;
6. lexicographic variant name.

BASELINE_MARKET cannot be selected.

If none is eligible:
`NO_ADAPTIVE_ENTRY_CONSTRUCTION_RULE`.

## Frozen 2025 confirmation gates

Construction winner passes only if:

1. filled N >= 40;
2. positive-event capture >= 65%;
3. filled structural-event rate >= 2025 detector baseline - 5 percentage points;
4. median positive-event price improvement > 0;
5. BUY_SIDE positive-event capture >= 55%;
6. SELL_SIDE positive-event capture >= 55%.

If any fail:
`ADAPTIVE_ENTRY_NOT_CONFIRMED_2025`.

No candidate switching after 2025 is observed.

## Untouched 2026 YTD validation gates

2026 is processed only after 2025 passes.

Required sample:
- detector signals N >= 30;
- filled N >= 20;
- positive structural-event N >= 10.

Quality gates:
- positive-event capture >= 60%;
- filled structural-event rate >= 2026 detector baseline - 5 percentage points;
- median positive-event price improvement > 0;
- BUY_SIDE positive-event capture >= 50% when BUY_SIDE has >=5 positive events;
- SELL_SIDE positive-event capture >= 50% when SELL_SIDE has >=5 positive events.

If sample minimums fail:
`2026_ENTRY_HOLDOUT_INSUFFICIENT_SAMPLE`.

If sample is sufficient but quality fails:
`ADAPTIVE_ENTRY_NOT_VALIDATED_AS_DEFINED`.

If all pass:
`VALIDATED_ADAPTIVE_ENTRY`.

No rescue or threshold change is allowed.

## Interpretation

A validated adaptive entry means:

> after the validated actionable liquidity detector fires, the mechanism improves execution location versus immediate market while retaining most true structural moves and without materially degrading structural precision.

It does not yet define risk or reward.

Next:
Adaptive SL -> Adaptive TP -> full ready-to-trade validation.

2027_PLUS=CLOSED
