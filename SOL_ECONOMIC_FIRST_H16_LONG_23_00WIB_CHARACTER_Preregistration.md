# SOL Economic-First H16 — One-Hour LONG Character Discovery

## Question
Within **16:00–17:00 UTC / 23:00–00:00 WIB**, can any preregistered SOLUSDT LONG character pass the frozen economic-first Development gates?

## Frozen engine
This hour uses the same frozen engine as the prior SOL economic-first hourly discovery. Only the clock anchors and output labels change.

- Direction: **LONG only**
- Anchors: **16:00, 16:15, 16:30, 16:45 UTC** = **23:00, 23:15, 23:30, 23:45 WIB**
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Holds: 60, 120, 240, 360, 720, 960 minutes
- Frozen character rules: 90
- Candidate universe: 90 × 6 × 6 = **3,240 candidates**
- Development years: 2022–2024 only
- External/OOS/Reference Validation: **closed**
- Entry/exit/economics/fees/causal normalization/gates/ranking: unchanged from the frozen engine

## Independence rule
H16 is independent of H00–H15. The H15 full-gate passer receives **no inherited privilege**. All 3,240 candidates reopen from zero under the same frozen gates.

No rule transfer, gate relaxation, rounding rescue, OOS exposure, Fibonacci/reference-range/visit/breakout/retest/EMA addition, or discretionary candidate promotion is allowed.

## Decision
- If at least one candidate passes every frozen anchor, pooled-economic, and all-era gate, rank the full passers using the frozen ranking and select exactly the top full passer: `SOL_ECONOMIC_FIRST_H16_LONG_CHARACTER_FOUND`.
- Otherwise: `SOL_ECONOMIC_FIRST_H16_NO_LONG_CHARACTER`.

Research/shadow only.