# BTC ORB B5 — Confirmation Layer Preregistration

Research only. Live BBC untouched.

## Objective
Reconstruct the missing confirmation layer suggested by the TradeX ORB screenshots: first touch/break is only a GET READY state; entry occurs only after causal confirmation.

## Frozen scope
- BTCUSDT, 5m execution
- Session window: New York-focused ORB family first, because the screenshots explicitly show New York and 5m
- Opening range: first 30 minutes of the NY window
- First touch/break does NOT enter
- Maximum one confirmed trade per session
- RR tested: 1.0R and 1.5R only
- Fee: 0.15%

## Frozen confirmation variants
1. OUTSIDE_CLOSE: after first touch/break, a later 5m candle closes outside the range in the breakout direction; enter next 5m open.
2. RETEST_HOLD: after first touch/break, price retests the broken boundary and closes back outside it in the breakout direction; enter next 5m open.
3. PULLBACK_CONT: after first touch/break and an outside close, allow a shallow pullback that does not close back inside the range, then require a fresh directional close; enter next open.

No EMA, OI, funding, macro, volume-profile, or multi-filter stacking in B5.

## Validation
70/30 chronological split. Report N, wins, WR, expectancy after fee, PF, and average trades/week. No post-result threshold rescue inside B5.
