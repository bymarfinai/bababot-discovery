# ETH R3 H03 Stability Retest Protocol

## Scope

- Pair: ETHUSDT
- Timeframe: 5m
- Direction: LONG only
- Hour: H03 = 03:00–04:00 WIB
- Development: 2022-01-01 through 2022-12-31
- Internal test: 2023-01-01 through 2023-12-31
- Confirmatory validation: 2024-01-01 through 2024-12-31, CLOSED until a 2022→2023 stable candidate is frozen
- Final OOS/reference 2025+: CLOSED
- Character grammar: frozen original 90-rule E12 grammar
- Timing grid: lookbacks (60,120,180,240,360), holds (120,240,360,480)

This retest replaces exact cross-year invariance with a practical stability definition. The question is whether an H03 edge remains recognizable after a normal year-to-year perturbation, not whether the exact optimum is mathematically identical.

## 1. 2022 Development eligibility

A cell is Development-eligible when all are true:

- N >= 60
- WR >= 55%
- expectancy >= +$0.50/trade
- PF >= 1.20
- net PnL > 0
- max DD <= $125
- max loss streak <= 10
- both 2022 half-years have expectancy > 0 and PF > 1
- at least 2/4 anchors are positive with N >= 12, expectancy > 0 and PF > 1

Development ranking is frozen before 2023 is evaluated:

1. higher minimum half-year expectancy
2. higher expectancy
3. higher PF
4. lower max DD
5. lower max loss streak
6. higher N
7. lexical rule, then shorter hold, then shorter lookback

Only the top Development cell becomes the frozen Development representative. No alternative Development candidate may be selected after opening 2023.

## 2. Practical stability in 2023

2023 evaluates the frozen rule in a **local neighborhood only**. The neighborhood contains the frozen Development coordinate and cells within Manhattan distance <= 1 on the frozen 5×4 LB/Hold grid. This allows one normal timing step of drift but forbids a distant re-optimization.

A 2023 cell is economically viable when:

- N >= 50
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.15
- max DD <= min($160, 1.50 × Development DD + $20)
- max loss streak <= min(12, Development loss streak + 4)

A viable local 2023 cell is considered **performance-stable** versus Development when:

- WR is no more than 5 percentage points below Development WR
- expectancy retention >= 60% of Development expectancy
- PF retention >= 70% of Development PF

The stable local cell used for the final lock is chosen by:

1. smallest Manhattan distance from Development representative
2. highest expectancy retention
3. highest WR retention
4. higher PF
5. lower DD
6. shorter hold, then shorter lookback

This is not a free 2023 optimizer: only the preregistered one-step local neighborhood may be considered.

## 3. Neighborhood health

To avoid a single lucky test point, at least **2 cells** in the Development representative's one-step local neighborhood, including the chosen stable test cell, must be economically viable in 2023. At least one of those viable cells must be the exact Development coordinate or an orthogonal one-step neighbor.

No requirement is imposed that the exact same coordinate be the annual optimum.

## 4. 2022→2023 verdict

- `STABLE_EDGE_FROZEN`: a performance-stable local 2023 cell exists and neighborhood health passes.
- `TEST_DEGRADATION_FAIL`: no local cell meets performance stability.
- `LOCAL_NEIGHBORHOOD_FAIL`: a stable point exists but the surrounding local neighborhood is too weak.

If either failure occurs, 2024 stays closed and there is no rescue candidate.

If `STABLE_EDGE_FROZEN`, freeze:

- character rule
- Development coordinate
- chosen local 2023 coordinate
- allowed one-step timing corridor
- all Development and Test metrics

before opening 2024.

## 5. One-shot 2024 confirmation

2024 may be evaluated only after `STABLE_EDGE_FROZEN` is persisted. The final executable coordinate is the chosen 2023 local coordinate; it cannot be changed after seeing 2024.

2024 confirmation passes when:

- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.15
- WR is no more than 6 percentage points below the mean of 2022 Development WR and 2023 Test WR
- expectancy is at least 55% of the mean 2022/2023 expectancy
- PF is at least 65% of the mean 2022/2023 PF
- max DD <= 1.6 × max(2022 DD, 2023 DD) + $20
- max loss streak <= max(12, max(2022 LS, 2023 LS) + 3)

Pass status: `ROBUST_STABLE_HABITAT`.
Fail status: `2024_CONFIRMATION_FAIL`.
No 2024 rescue/reselection is permitted.

## Interpretation

This protocol intentionally distinguishes normal degradation from collapse. A Development result such as WR 60%, Exp +$2.00, PF 1.60 followed by Test WR 57–58%, Exp +$1.3–$1.8, PF 1.3–1.5 is acceptable if local timing stability remains present. A Development edge that becomes negative, loses most expectancy, or requires a distant timing jump is not robust.

Because H03 has already been explored in earlier research, 2022–2023 are not pristine OOS. This retest is an internal robustness study. 2024 remains the one-shot confirmatory partition for this R3 protocol; 2025+ remains closed final OOS/reference.