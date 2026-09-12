# ETH R3 H05 — Exploratory 2024 Diagnostic Protocol

## Purpose
H05 failed the preregistered 2023 performance-stability gate because expectancy retention versus 2022 was below 60%, although 4/5 local timing cells remained economically viable. At the user's request, 2024 is opened only as an **exploratory diagnostic** to understand whether the H05 character persists economically. This does **not** convert 2024 into confirmatory validation and cannot retroactively rescue the formal Stage B verdict.

## Frozen character and search scope
- Pair: ETHUSDT
- Direction: LONG only
- Hour: 05:00–06:00 WIB
- Character rule: `DRIVE_DOWN__STR_B80_100`
- 2022 frozen Development coordinate: `LB180 / H240`
- 2024 may evaluate only the same one-step neighborhood already evaluated in 2023:
  - LB180 / H240 (exact Development coordinate)
  - LB120 / H240
  - LB180 / H120
  - LB180 / H360
  - LB240 / H240
- No other rule, lookback, hold, threshold, or market state may be introduced after 2024 is opened.

## 2024 period
- Score only trades whose entry and exit are fully inside 2024-01-01 through 2024-12-31 UTC.
- Historical bars before 2024 may be used only for causal indicator warm-up.
- 2025+ remains CLOSED.

## Reporting
For all five frozen coordinates report: N, WR, net PnL, expectancy/trade, PF, max drawdown, max loss streak, and economic viability using the same Stage B viability definition (N>=50, WR>=52%, Net>0, Exp>0, PF>=1.15, DD within the same risk envelope). Loss streak remains a diagnostic warning, not an economic viability gate.

The exact coordinate `LB180/H240` must be shown separately as the primary three-year comparison (2022 Development -> 2023 Test -> 2024 exploratory diagnostic). Local coordinates are diagnostics only and may not be selected post-hoc as a replacement candidate.

## Interpretation
Allowed conclusions are descriptive only, e.g. `ECONOMIC_PERSISTENCE`, `ECONOMIC_WEAKENING`, or `REGIME_COLLAPSE`. No result from this stage may be labeled pristine OOS or formal confirmatory validation. The prior Stage B status remains unchanged.
