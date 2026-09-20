# SOL Adaptive Entry Router V2 — Frozen Router Preregistration

## Objective

Validate one minimal adaptive entry router built only from the already-observed 2020-2024 construction set.

No 2025 value has been used to choose this router.

## Frozen parent detector

Use only the validated actionable structural-liquidity detector:
- anatomy score >= 3;
- same-reclaim-bar resolved outcomes excluded;
- signal exists only after reclaim H1 close.

BUY_SIDE sweep -> SHORT.
SELL_SIDE sweep -> LONG.

## Frozen router

### Anatomy score = 3
Use **FIVE_MIN_REVERSAL_BREAK**:
- SHORT: first completed 5m close below reclaim H1 low, enter next 5m open;
- LONG: first completed 5m close above reclaim H1 high, enter next 5m open.

### Anatomy score = 4
Use **GAP_25**:
- limit = reclaim_close + 0.25 * (liquidity_level - reclaim_close).

No other score, variant, threshold, or fallback is allowed.

If the assigned route does not fill before the frozen entry deadline, the signal is missed.

## Why this exact router was frozen

Construction-only 2020-2024 observations:
- score-3 FIVE_MIN_REVERSAL_BREAK positive-event capture = 88.98%;
- score-3 FIVE_MIN_REVERSAL_BREAK filled structural precision = 61.41%;
- score-4 GAP_25 positive-event capture = 65.38%;
- score-4 GAP_25 median positive-event price improvement = +0.220 H1 range units.

GAP_25 was the only tested score-4 pullback variant retaining at least 60% of positive structural events in construction.

These observations are construction evidence, not validation.

## Entry deadline and execution semantics

Reuse Adaptive Entry V1 unchanged:
- signal_time = reclaim H1 close;
- entry deadline = earlier of 6h after signal and structural-outcome H1 close;
- limit fills use 5m high/low reach;
- 5m confirmation enters at next 5m open;
- no fill after the structural outcome is known.

## Scientific split

- 2020-2024 = construction only.
- 2025 = frozen router confirmation.
- 2026 YTD = untouched router holdout, opened only if 2025 passes.
- 2027+ CLOSED.

No candidate switching after 2025.

## Primary router metrics

Report:
1. detector signal N;
2. router filled N;
3. overall fill rate;
4. positive structural-event N;
5. positive-event capture;
6. negative-event fill rate;
7. structural-event rate among fills;
8. baseline detector structural-event rate;
9. BUY_SIDE positive capture;
10. SELL_SIDE positive capture;
11. score-3 positive capture and precision;
12. score-4 positive capture;
13. score-4 median positive-event improvement vs immediate market;
14. router median time-to-fill;
15. router median positive adverse excursion until structural resolution.

## Frozen 2025 confirmation gates

Router passes only if all are true:

1. detector signals N >= 50;
2. filled N >= 35;
3. positive structural-event N >= 25;
4. overall positive-event capture >= 75%;
5. structural-event rate among fills >= detector baseline structural-event rate;
6. BUY_SIDE positive-event capture >= 65%;
7. SELL_SIDE positive-event capture >= 65%;
8. score-3 positive-event capture >= 75%;
9. score-4 positive-event capture >= 50% when score-4 has >= 5 positive events;
10. score-4 median positive-event price improvement > 0.

If any fail:
`ADAPTIVE_ENTRY_ROUTER_NOT_CONFIRMED_2025`

2026 remains unopened.

## Untouched 2026 YTD gates

Open only if 2025 passes.

Minimum sample:
1. detector signals N >= 30;
2. filled N >= 20;
3. positive structural-event N >= 10.

Quality:
4. overall positive-event capture >= 70%;
5. structural-event rate among fills >= detector baseline - 3 percentage points;
6. BUY_SIDE positive capture >= 55% when BUY_SIDE has >= 5 positive events;
7. SELL_SIDE positive capture >= 55% when SELL_SIDE has >= 5 positive events;
8. score-3 positive capture >= 65% when score-3 has >= 5 positive events;
9. score-4 positive capture >= 45% when score-4 has >= 5 positive events;
10. score-4 median positive-event improvement > 0 when score-4 has >= 5 filled positive events.

If sample is insufficient:
`2026_ROUTER_HOLDOUT_INSUFFICIENT_SAMPLE`

If sample is sufficient but quality fails:
`ADAPTIVE_ENTRY_ROUTER_NOT_VALIDATED_AS_DEFINED`

If all pass:
`VALIDATED_ADAPTIVE_ENTRY_ROUTER`

## Research boundary

Even a validated router defines entry only.

Adaptive SL and Adaptive TP remain separate future phases.

2027_PLUS=CLOSED
