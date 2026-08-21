# BTC Weekly Best-State B7 — Preregistration

Research only. Live BBC untouched.

## Objective
Within each calendar week, scan causal BTC opportunities on 1H and 4H and select at most ONE trade. NO TRADE is allowed. Target is maximum precision, not frequency.

## Frozen rules
- Timeframes: 1H and 4H only.
- Side: LONG or SHORT determined causally from current trend/momentum state.
- RR: 1:1 and 1.5:1 only; never below 1:1.
- Fee model: 0.15% round-trip as in prior studies.
- Chronological 70/30 discovery/validation split.
- Maximum one selected trade per ISO week across both timeframes.

## Frozen causal features
Only these features may contribute to the score:
1. directional momentum over prior 3 bars,
2. breakout distance beyond prior 20-bar high/low,
3. candle body-to-range ratio,
4. ATR-normalized range expansion,
5. distance from 20-bar midpoint in the trade direction.

No EMA, funding, OI, macro, news, day/hour slot, or post-result threshold rescue.

## Selector families
Three preregistered score variants only:
- MOMENTUM: momentum + directional location.
- BREAKOUT: breakout distance + body quality.
- COMBINED: momentum + breakout distance + body quality + range expansion.

For each week and selector, choose the highest-score eligible opportunity only if its score is above a frozen percentile threshold derived from discovery only (90th, 95th, or 97.5th percentile). Otherwise NO TRADE.

## Promotion view
Report for each selector/threshold/RR: selected weeks, no-trade weeks, wins, losses, WR, expectancy, PF, max losing streak, and chronological blocks. A 100% validation WR is reported only if achieved naturally with at least 20 validation trades; otherwise it is not treated as evidence of certainty.
