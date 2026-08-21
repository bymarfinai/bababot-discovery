# BTC Weekly-One B6 — Preregistration

Research only. Live BBC untouched.

## Objective
Find a simple BTC setup that trades exactly once per week on either 1H or 4H and has the highest robust chronological validation win rate while keeping RR >= 1:1.

## Frozen search space
- Timeframes: 1H and 4H.
- One fixed weekday + UTC hour slot per week.
- Direction: LONG or SHORT.
- Entry: open of the selected bar.
- Risk unit: ATR(14) known before entry.
- RR: 1.0:1, 1.25:1, 1.5:1.
- 1H max hold: 6 hours.
- 4H max hold: 12 hours.
- Fee: 0.15% per trade.
- If TP and SL are both touched inside the same bar, count SL first (conservative).

No EMA, ORB, funding, OI, macro, or post-result filters.

## Validation
Chronological 70/30 split per cell. Rank primarily by validation WR, then validation expectancy/PF. Report only cells with adequate sample (validation >= 40 trades). A strong candidate should have positive validation expectancy and PF > 1.0; 70%+ validation WR is considered notable and 80%+ exceptional.
