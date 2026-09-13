# SOL ORB Causal Retest Character v1 — Preregistration

## Goal
Find the structural character that separates economically useful vs failed SOLUSDT ORB-high retests using only information available by the close of the retest candle. This follows the 24h causal E2 sweep, where unconditional touch-entry was not robust.

## Frozen universe
- SOLUSDT 5m
- Development only: 2022-01-01 <= timestamp < 2025-01-01
- Weekdays
- All 24 UTC anchor hours
- ORB = first three 5m candles of each hour
- First close above ORB high = breakout
- First retest within next 30m: low <= ORB high and close >= ORB midpoint
- Reference/OOS remains closed

## Causality boundary
This experiment characterizes a **retest-close decision**. Features may use the completed retest candle, but nothing after its close. Therefore it does not claim a fill at the earlier ORB-high touch. A later executable strategy derived from this experiment must enter no earlier than the next 5m open after the retest candle closes.

## Frozen retest-time features
All normalized by ORB range where applicable:
1. `orb_range_pct`
2. `breakout_extension_r` = (breakout close - ORB high) / ORB range
3. `breakout_body_r` = abs(breakout close - breakout open) / ORB range
4. `bars_orb_to_break`
5. `bars_break_to_retest`
6. `retest_low_depth_r` = (ORB high - retest low) / ORB range
7. `retest_close_r` = (retest close - ORB high) / ORB range
8. `retest_body_r` = abs(retest close - retest open) / ORB range
9. `retest_upper_wick_r`
10. `retest_lower_wick_r`
11. `retest_close_location` = (close-low)/(high-low)
12. `retest_bullish` = close > open

## Outcome diagnostics
From **next 5m open after retest close**, measure fixed +15m/+30m/+60m/+120m returns, with $500 notional and 0.15% round-trip cost. Also record whether later acceptance occurs, but acceptance is an outcome diagnostic, never an entry prerequisite.

## Discovery method
- Compare feature distributions for positive vs non-positive net outcomes at 30m/60m/120m.
- Produce quartile maps for continuous features and categorical maps for `retest_bullish`.
- Produce hour-agnostic pooled maps first; hour is descriptive only.
- Do not promote a threshold in this run.
- Look specifically for broad/interior zones that remain directionally useful across 2022/2023/2024, rather than choosing the best single quartile.

## Anti-overfit rules
- No VWAP/EMA/Fibonacci/volume/regime additions.
- No TP/SL search.
- No hour cherry-picking.
- No threshold optimization or gate promotion in this experiment.
- No Reference/OOS opening.
- Any candidate character nominated from these distributions requires a separate preregistered confirmation test.
