# ETH R4b — Full-24 Plateau Evaluation

## Executive finding

The full-24 R3/R4/R4b sequence now supports a much stronger conclusion than the original single-winner scan:

> **H04 (04:00-05:00 WIB) is the only hour that demonstrates a broad ETH-native timing plateau surviving 2022 Development -> 2023 same-cell testing and remaining economically alive across the entire frozen component in 2024.**

2025 remains untouched final OOS. 2026 remains closed.

## Why the first R4 result is not the final conclusion

R4 initially selected one plateau center per exact character rule and tested only a Manhattan-distance <=1 neighborhood around that center. It returned zero formal stable survivors from 72 centers.

That center-screen was too aggressive in deduplicating broad same-rule timing regions. H04 exposed the flaw: the R4 center for `DRIVE_DOWN__STR_B80_100` was LB180/H240, while the previously established robust coordinate LB240/H360 is Manhattan distance 2 away and was omitted from that center's local test.

R4b corrected the unit of analysis without loosening the trading/economic gates: all connected 2022 `dev_eligible` timing cells were frozen as components, and every component cell was tested at the exact same coordinate in 2023.

## R4b Stage A — frozen 2022 components

- 72 components frozen across H00-H23 (up to three per hour).
- 248 strict R3-eligible timing cells frozen in total.
- Component membership used 2022 only.
- 2024-2026 remained closed.

H04 rank-1 component:

`DRIVE_DOWN__STR_B80_100`

- LB120/H240
- LB180/H240
- LB240/H240
- LB180/H360
- LB240/H360

The component therefore contains the previously established H04 robust coordinate rather than discarding it through center selection.

## R4b Stage B — 2023 same-cell survival

Across 72 frozen components:

- **1 `STABLE_PLATEAU_FROZEN`: H04**
- 3 `PARTIAL_PLATEAU_PERSISTENCE`: H01, H02, H05
- 0 narrow stable points
- all other components failed the plateau survival rule

### H04

Frozen component size: 5

2023:

- economically viable cells: **5/5**
- performance-stable cells: **2/5**
- viable fraction: **100%**
- median WR: **61.04%**
- median Exp: **+$1.99**
- median PF: **2.709**
- max DD across component: **$51.28**

This is the strongest evidence in the full-24 map because survival is distributed across the complete frozen timing plateau, not concentrated in one chosen coordinate.

### Partial persistence

H01 and H02 retain some viable timing cells, but no same-cell timing meets the full performance-stability requirement. H05 retains a two-cell economically viable subset but similarly has no performance-stable cell under the frozen retention rule.

These are useful regime/persistence clues, but they are not in the same robustness class as H04.

## R4b Stage C — H04 2024 component diagnostic

Only H04 was opened because it was the only formal R4b stable plateau.

All five frozen H04 cells remain economically viable in 2024:

| Timing | 2022 Exp | 2023 Exp | 2024 Exp | 2024 PF | 2024 Net |
|---|---:|---:|---:|---:|---:|
| LB120/H240 | +$3.79 | +$1.64 | +$0.78 | 1.256 | +$91.72 |
| LB180/H240 | +$3.80 | +$1.93 | +$0.54 | 1.222 | +$66.24 |
| LB240/H240 | +$3.53 | +$2.06 | +$0.67 | 1.279 | +$79.87 |
| LB180/H360 | +$2.80 | +$1.99 | +$0.47 | 1.158 | +$57.64 |
| LB240/H360 | +$3.38 | +$2.08 | +$1.67 | 1.661 | +$200.69 |

2024 component summary:

- economically viable: **5/5**
- median WR: **57.50%**
- median Exp: **+$0.67**
- median PF: **1.256**
- diagnostic verdict: **ECONOMIC_PLATEAU_PERSISTS**

None of the five cells meets the old strict 60% expectancy-retention rule versus 2022. This is therefore not evidence of unchanged edge magnitude. It is evidence that the same frozen plateau remains positive and economically viable across a third calendar regime while the edge compresses.

## Current robustness classification

### Tier A — Broad robust / economically persistent

**H04 — `DRIVE_DOWN__STR_B80_100`**

- broad 2022 timing plateau
- 5/5 viable in 2023
- 5/5 viable again in 2024
- exact and neighboring timings remain positive
- magnitude decays in 2024, so risk and expectancy compression must remain explicit

### Tier B — Partial / decaying persistence

- H05
- H01
- H02

These hours show some surviving economics in 2023 but fail the component stability requirement. They should not be promoted to H04's robustness tier from the current evidence.

### Tier C — Shifted/transient clues

- H08: isolated shifted 2023 survivor, then 2024 local collapse
- H11, H15, H19: useful positive/degradation clues from earlier R3 first-pass work, but they did not produce a stable R4b component

### Tier D — Component degradation / collapse

All remaining hours under the frozen R4b component screen.

## Scientific interpretation

The important discovery is not merely that H04 has the best metrics. The distinguishing property is **topological robustness in parameter space**:

1. multiple neighboring timing cells are good in Development;
2. the same cells survive into 2023 rather than requiring a post-hoc timing rescue;
3. the whole five-cell region remains economically positive in 2024;
4. the edge magnitude changes, but the character and timing habitat remain recognizable.

This makes H04 a substantially stronger candidate for final OOS testing than a single-cell backtest winner.

## Data preservation

- 2025 remains fully unopened in R4/R4b and should be preserved as the final full-year OOS for the frozen H04 plateau.
- 2026 remains closed and can later serve as YTD/current-regime evidence after the 2025 result is known.
- No 2025/2026 tuning should occur before the frozen-path result is recorded.
