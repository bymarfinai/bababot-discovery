# ETH R3 H05 Practical Robustness Retest Protocol

## Scope

- Pair: ETHUSDT
- Timeframe: 5m
- Direction: LONG only
- Hour: H05 = 05:00–06:00 WIB
- Development: 2022-01-01 through 2022-12-31
- Internal test: 2023-01-01 through 2023-12-31
- Confirmatory validation: 2024-01-01 through 2024-12-31, CLOSED until a 2022→2023 stable candidate is frozen
- Final OOS/reference 2025+: CLOSED
- Character grammar: frozen original 90-rule E12 grammar
- Timing grid: lookbacks (60,120,180,240,360), holds (120,240,360,480)

This protocol keeps the practical-stability concept established in R3 H03/H04, but incorporates the H04 lesson that **maximum loss streak is a risk-clustering diagnostic, not a binary robustness gate**. A stable positive edge is not reclassified as overfit solely because one year contains a longer losing cluster. Loss streak remains reported, compared, and flagged for risk-management purposes.

## 1. 2022 Development eligibility

A cell is Development-eligible when all are true:

- N >= 60
- WR >= 55%
- expectancy >= +$0.50/trade
- PF >= 1.20
- net PnL > 0
- max DD <= $125
- both 2022 half-years have expectancy > 0 and PF > 1
- at least 2/4 anchors are positive with N >= 12, expectancy > 0 and PF > 1

Maximum loss streak is recorded but is **not** an eligibility gate.

Development ranking is frozen before 2023 is evaluated:

1. higher minimum half-year expectancy
2. higher expectancy
3. higher PF
4. lower max DD
5. lower max loss streak (tie-break / risk quality only)
6. higher N
7. lexical rule, then shorter hold, then shorter lookback

Only the top Development cell becomes the frozen Development representative. No alternative Development candidate may be selected after opening 2023.

## 2. Practical stability in 2023

2023 evaluates the frozen rule only in the frozen Development coordinate and cells within Manhattan distance <= 1 on the fixed 5×4 LB/Hold grid. This permits one normal timing step of drift but forbids distant re-optimization.

A 2023 cell is economically viable when:

- N >= 50
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.15
- max DD <= min($160, 1.50 × Development DD + $20)

A viable local 2023 cell is performance-stable versus Development when:

- WR is no more than 5 percentage points below Development WR
- expectancy retention >= 60% of Development expectancy
- PF retention >= 70% of Development PF

Maximum loss streak is diagnostic only. A warning threshold is recorded at max(12, Development LS + 4), but exceeding it does not invalidate economic stability.

The stable local cell used for the final lock is chosen by:

1. smallest Manhattan distance from Development representative
2. highest expectancy retention
3. highest WR retention
4. higher PF
5. lower DD
6. lower loss streak (tie-break only)
7. shorter hold, then shorter lookback

## 3. Neighborhood health

To avoid a single lucky test point, at least **2 cells** in the Development representative's one-step local neighborhood, including the chosen stable test cell, must be economically viable in 2023. At least one of those viable cells must be the exact Development coordinate or an orthogonal one-step neighbor.

No requirement is imposed that the exact same coordinate be the annual optimum.

## 4. 2022→2023 verdict

- `STABLE_EDGE_FROZEN`: a performance-stable local 2023 cell exists and neighborhood health passes.
- `TEST_DEGRADATION_FAIL`: no local cell meets performance stability.
- `LOCAL_NEIGHBORHOOD_FAIL`: a stable point exists but the surrounding local neighborhood is too weak.

If either failure occurs, 2024 stays closed and there is no rescue candidate.

If `STABLE_EDGE_FROZEN`, freeze the character rule, Development coordinate, chosen local 2023 coordinate, allowed one-step timing corridor, and all Development/Test metrics before opening 2024.

## 5. One-shot 2024 confirmation

2024 may be evaluated only after `STABLE_EDGE_FROZEN` is persisted. The final executable coordinate is the chosen 2023 local coordinate and cannot be changed after seeing 2024.

2024 **economic confirmation** passes when:

- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.15
- WR is no more than 6 percentage points below the mean of 2022 Development WR and 2023 Test WR
- expectancy is at least 55% of the mean 2022/2023 expectancy
- PF is at least 65% of the mean 2022/2023 PF
- max DD <= 1.6 × max(2022 DD, 2023 DD) + $20

Loss streak is diagnostic only. The 2024 risk-warning threshold is max(12, max(2022 LS, 2023 LS) + 3).

Statuses:

- `ROBUST_STABLE_HABITAT`: economic confirmation passes and 2024 LS <= warning threshold.
- `ROBUST_STABLE_HABITAT_RISK_WARNING`: economic confirmation passes but 2024 LS exceeds the warning threshold.
- `2024_CONFIRMATION_FAIL`: at least one economic confirmation gate fails.

No 2024 rescue/reselection is permitted.

## Interpretation

Robustness means the edge remains economically recognizable under year-to-year perturbation. It does **not** require identical optimum parameters or identical risk sequences. A result such as WR 60% / +$1,000 in Development followed by WR 58% / +$900 in Test is healthy even if loss clustering differs.

Conversely, a Development edge that becomes negative, loses most expectancy, suffers major PF collapse, or requires a distant timing jump is not robust.

Because H05 has been explored previously, 2022–2023 are not pristine OOS. This is an internal robustness study. 2024 is the one-shot confirmatory partition for this R3 H05 protocol; 2025+ remains closed final OOS/reference.