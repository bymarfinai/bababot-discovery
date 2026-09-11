# SOL Economic-First H22 — 05:00–06:00 WIB LONG Character Discovery Preregistration

## Question
Within **22:00–23:00 UTC / 05:00–06:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

## Independence
H22 is independent of H00–H21. No candidate, rule privilege, threshold change, or confirmation from earlier hours may be inherited.

## Frozen engine
Use the frozen SOL economic-first engine from `research/sol_economic_first_h00_long_07_08wib_character.py` without changing the candidate universe, feature definitions, economics, or gates.

- Direction: LONG only
- Anchors: 22:00, 22:15, 22:30, 22:45 UTC = 05:00, 05:15, 05:30, 05:45 WIB
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Holds: 60, 120, 240, 360, 720, 960 minutes
- Character rules: 90
- Candidate universe: 3,240
- Development years: 2022, 2023, 2024 only
- OOS / External / Reference Validation: closed

## Frozen gates
No relaxation, rounding rescue, OOS leakage, or inherited candidate privilege. Exactly the frozen anchor, pooled-economic, and all-era gates from H00 apply.

## Decision
If at least one candidate passes all frozen gates, select the top frozen-ranked candidate and status:
`SOL_ECONOMIC_FIRST_H22_LONG_CHARACTER_FOUND`

Otherwise:
`SOL_ECONOMIC_FIRST_H22_NO_LONG_CHARACTER`

If none passes, the next hour must reopen all 3,240 candidates from zero.

Research/shadow only.
