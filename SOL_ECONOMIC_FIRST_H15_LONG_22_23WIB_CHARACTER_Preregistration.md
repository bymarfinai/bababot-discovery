# SOL Economic-First H15 — One-Hour LONG Character Discovery

## Frozen question
Does SOLUSDT have a robust LONG character inside **15:00–16:00 UTC / 22:00–23:00 WIB** under the same frozen economic-first methodology used for prior hourly discovery?

## Independent hour
H15 is independent of H00–H14. No candidate, rule privilege, parameter preference, or validation privilege is inherited from any prior hour.

## Frozen anchors
- 15:00 UTC / 22:00 WIB
- 15:15 UTC / 22:15 WIB
- 15:30 UTC / 22:30 WIB
- 15:45 UTC / 22:45 WIB

## Frozen universe and engine
- LONG only
- SOLUSDT Binance Futures raw 5m weekday bars
- Development years 2022–2024 only
- External and Reference Validation remain closed
- 90 frozen character rules
- lookbacks: 15, 30, 60, 120, 240, 360 minutes
- holds: 60, 120, 240, 360, 720, 960 minutes
- 90 × 6 × 6 = 3,240 candidates
- fixed notional $500
- round-trip fee $0.75
- rolling causal normalization: ROLL_N=60, MIN_HIST=40
- causal state excludes the current observation
- entry at exact 5m-open; exit at exact 5m-open after fixed hold
- no TP, SL, Fibonacci, reference range, visit, breakout, retest, or EMA

## Frozen gates
Anchor, pooled-economic, and all-era gates are identical to the frozen base engine. There is no gate relaxation, rounding rescue, candidate inheritance, or OOS exposure.

## Decision
- If at least one candidate passes every frozen gate: `SOL_ECONOMIC_FIRST_H15_LONG_CHARACTER_FOUND` and select exactly the top-ranked full passer under the frozen ranking.
- Otherwise: `SOL_ECONOMIC_FIRST_H15_NO_LONG_CHARACTER`.

If no candidate passes, the next hour must reopen all 3,240 candidates from zero.

Research/shadow only.
