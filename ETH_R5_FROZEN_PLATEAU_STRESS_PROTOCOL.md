# ETH R5 — Frozen Plateau Stress Protocol

**Preregistered before R5 outputs are opened.**

## Frozen object

R5 does **not** perform discovery or reselection. It inherits exactly the R4 champion:

- Hour: **H04 WIB**
- Character: **DRIVE_DOWN__STR_B80_100**
- Frozen cells: **LB120/H240, LB180/H240, LB240/H240, LB180/H360, LB240/H360**
- Calibration history: 2022 discovery/freeze -> 2023 frozen validation -> 2024 persistence -> 2025 untouched final OOS
- **2026 remains CLOSED and must not be read or scored.**

## Question

Does the frozen R4 structural plateau remain economically alive under modest implementation stress, or was the apparent robustness dependent on exact backtest execution assumptions?

## Stress grid

The signal rule, hour, LB/Hold cells, masks, and membership remain frozen. Only implementation assumptions change.

- Total fee multipliers: **1.0x, 1.5x, 2.0x** of the R4 fee ($0.75/trade)
- Execution delays: **0, 5, 10, 15 minutes**
- Delay shifts both entry and exit by the same amount, preserving the frozen hold duration.
- Character classification is evaluated at the original frozen signal timestamp; it is never recomputed after the delay.
- The full grid is descriptive. The preregistered **primary stress** is **1.5x fee + 5-minute delay**.

## Per-cell economic viability

For each frozen cell and calendar year 2022–2025:

- N >= 50
- WR >= 52%
- Net > 0
- Expectancy > 0
- PF >= 1.15
- DD <= the same R4 adaptive cap: `min(160, 1.50 * dev2022_DD + 20)`

Loss streak remains a diagnostic only and is not a hard rejection gate.

## Component-level survival

A five-cell plateau-year survives when:

- at least **3/5 cells** are economically viable,
- median expectancy > 0,
- median PF >= 1.15.

R5 never requires all coordinates to pass.

## Baseline reproduction gate

Before interpreting stress results, fee 1.0x / delay 0 for 2025 must reproduce the frozen R4 Stage-D cell results (N and principal economics) within numerical tolerance. If reproduction fails, R5 is invalid and stops.

## Primary R5 verdict

`R5_FROZEN_PLATEAU_STRESS_PASS` requires:

1. baseline reproduction passes;
2. under **1.5x fee + 5m delay**, the plateau survives in at least **3 of 4** calendar years 2022–2025;
3. **2025 must be one of the surviving years**;
4. 2025 leave-one-cell-out jackknife survives in at least **3 of 5** omissions, using a four-cell component rule of >=2/4 viable cells, median expectancy > 0, median PF >= 1.15.

`R5_PARTIAL_STRESS_PERSISTENCE` means baseline reproduces and remains structurally positive, but the primary stress gate above is not fully met.

`R5_FROZEN_PLATEAU_STRESS_FAIL` means baseline reproduction fails or the plateau loses component-level economics materially under the preregistered stress.

## Anti-overfit restrictions

- No new feature, threshold, hour, rule, LB, Hold, or cell may be selected from R5 outcomes.
- No failed coordinate may be replaced.
- No scenario may be promoted post-hoc as the primary test.
- R5 is an audit of the frozen R4 plateau, not a new search.
- **No 2026 data may be scored or used for indicator state in this experiment; the data frame is hard-capped before 2026-01-01 UTC.**
