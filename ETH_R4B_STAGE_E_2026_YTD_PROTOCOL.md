# ETH R4b — Stage E 2026 YTD Shadow / Current-Regime Protocol

## Status

**FORWARD SHADOW CHECK ONLY. NO RESELECTION. NO RETUNING.**

Stage D 2025 remains the final untouched full-year OOS decision. Stage E does not replace or retroactively alter that verdict.

## Frozen target

- Hour habitat: **H04 WIB**
- Character: **`DRIVE_DOWN__STR_B80_100`**
- Frozen component rank: **1**
- Frozen timing cells (exactly five):
  - LB120 / Hold240
  - LB180 / Hold240
  - LB240 / Hold240
  - LB180 / Hold360
  - LB240 / Hold360

No new hour, character rule, lookback, hold, threshold, coordinate, or ranking may be selected using 2026 data.

## Evaluation window

- Start: **2026-01-01 00:00 UTC**
- End: latest complete ETHUSDT 5m timestamp available to the runner at execution time.
- Prior history may be retained only for indicator warm-up.
- Only trades with entry on/after 2026-01-01 and an exit timestamp fully available in the dataset are scored.

## Frozen per-cell economic viability gate

A cell is economically viable when all are true:

- N >= 50
- WR >= 52%
- Net > 0
- Expectancy > 0
- PF >= 1.15
- DD <= adaptive cap `min($160, 1.50 * 2022_dev_DD + $20)`

Max loss streak is a diagnostic warning only, not a hard rejection gate. Warning threshold remains `max(12, 2022_dev_loss_streak + 4)`.

## Plateau-level Stage E interpretation

- **CURRENT_REGIME_PLATEAU_ALIVE**: at least 50% of the five frozen cells are economically viable, median expectancy > 0, and median PF >= 1.15.
- **CURRENT_REGIME_PARTIAL_PERSISTENCE**: primary gate is not met, but at least two cells are viable OR both median expectancy > 0 and median PF > 1.00.
- **CURRENT_REGIME_PLATEAU_WEAK**: otherwise.

The verdict is about the frozen five-cell region, never a post-hoc best 2026 coordinate.

## Required reporting

Report per-cell N, WR, Net, Exp, PF, DD, loss streak, viability, and risk-clustering warning; plateau medians; count of viable cells; latest dataset timestamp; and comparison of canonical pre-2026 anchor LB240/H360 across 2022, 2023, 2024, 2025, and 2026 YTD.

2026 data must not be used to modify the strategy after this check.