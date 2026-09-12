# ETH R4b — Stage D 2025 Final Full-Year OOS Protocol

## Purpose

Run one untouched full-year out-of-sample test on the only R4b component that survived the frozen 2022 -> 2023 plateau screen and remained economically positive across the full frozen component in the 2024 diagnostic.

**2025 is opened once as FINAL_FULL_YEAR_OOS. 2026 remains CLOSED.**

## Frozen target

WIB hour: **H04 = 04:00-05:00 WIB**  
Character: **DRIVE_DOWN__STR_B80_100**  
Frozen R4b component rank: **1**

The exact five timing cells are frozen before 2025 is opened:

- LB120 / H240
- LB180 / H240
- LB240 / H240
- LB180 / H360
- LB240 / H360

No 2025 timing reselection, no replacement candidate, no character change, and no threshold tuning is permitted.

## OOS period

Use full historical data for indicator warm-up, then include only events satisfying:

- entry timestamp >= 2025-01-01 00:00:00 UTC
- exit timestamp < 2026-01-01 00:00:00 UTC

The 2026 period must not be read, summarized, selected against, or used to modify this test.

## Per-cell economic viability gate

Reuse the R4b economic viability logic without relaxation:

- N >= 50
- WR >= 52%
- Net PnL > 0
- Expectancy > 0
- PF >= 1.15
- DD <= min(160, 1.50 * 2022 DD + 20)

Maximum loss streak is a risk-clustering diagnostic only. The warning threshold remains max(12, 2022 LS + 4).

## Retention diagnostics

For transparency, report versus the cell's own frozen 2022 baseline:

- WR change in percentage points
- expectancy retention
- PF retention
- strict-retention diagnostic: viable AND WR change >= -5 pp AND expectancy retention >= 60% AND PF retention >= 70%

This strict-retention diagnostic is not allowed to override the component-level economic verdict by itself. The user's working robustness definition emphasizes recognizable positive economics and parameter breadth, not exact annual equality.

## Frozen component-level FINAL OOS verdict

Let `n = 5` frozen cells.

- **FINAL_OOS_PLATEAU_PASS**: at least 50% of frozen cells are economically viable (therefore at least 3/5), component median expectancy > 0, and component median PF >= 1.15.
- **PARTIAL_FINAL_OOS_PERSISTENCE**: pass is not reached, but at least 2 cells are economically viable OR both component median expectancy > 0 and median PF > 1.00.
- **FINAL_OOS_PLATEAU_FAIL**: neither condition above is met.

The result is evaluated on the whole frozen plateau. A best individual 2025 cell may be reported descriptively but cannot replace the frozen component or become a post-hoc winner.

## Outputs

Report all five cells with 2022/2023/2024 references and 2025 N, WR, Net, Exp, PF, DD, LS, viability, retention, and risk warning. Persist a component summary and final OOS verdict.

After this stage, **2026 remains unopened** until a separate explicit decision.