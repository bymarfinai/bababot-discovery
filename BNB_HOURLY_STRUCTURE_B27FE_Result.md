# BNB Hour-by-Hour Structural Discovery — B27FE

**Anchor tested:** 04:00 WIB only.

- Reference: 04:00–08:00 WIB
- Execution: 08:00–12:00 WIB
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Structure only: K1 -> causal leave -> H2 using frozen causal ordering
- No entry, TP, SL, PnL, fee, or holdout economics

## Pooled result

- Complete sessions: **1095**
- K1 qualified: **224 (20.5%)**
- Causal leaves: **142**
- H2 arrivals: **108**
- Opposite breaks before H2: **7**
- Ambiguous H2/opposite: **0**
- No H2 by end: **27**
- H2 / causal-leave rate: **76.1%**
- Resolved H2 share: **93.9%**
- Median leave -> H2: **17.5 min**
- Frozen structural label: **STRONG_STRUCTURAL**

## Frozen comparison vs completed clocks

- 00:00 WIB: **137 leaves / 105 H2 = 76.6%**
- 01:00 WIB: **162 leaves / 132 H2 = 81.5%**
- 02:00 WIB: **162 leaves / 126 H2 = 77.8%**
- 03:00 WIB: **142 leaves / 96 H2 = 67.6%**
- 04:00 WIB: **142 leaves / 108 H2 = 76.1%**
- B27FE minus prior leader (01:00 WIB) H2-rate delta: **-5.4 percentage points**

## Weekday breakdown

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 21 | 11 | 8 | 72.7% | 0 | 3 | 100.0% | 37.5m |
| Tuesday | 157 | 41 | 21 | 16 | 76.2% | 3 | 2 | 84.2% | 30.0m |
| Wednesday | 156 | 23 | 16 | 13 | 81.2% | 0 | 3 | 100.0% | 10.0m |
| Thursday | 156 | 39 | 29 | 22 | 75.9% | 1 | 6 | 95.7% | 15.0m |
| Friday | 156 | 38 | 28 | 22 | 78.6% | 2 | 4 | 91.7% | 15.0m |
| Saturday | 156 | 35 | 19 | 15 | 78.9% | 1 | 3 | 93.8% | 15.0m |
| Sunday | 157 | 27 | 18 | 12 | 66.7% | 0 | 6 | 100.0% | 20.0m |

## Interpretation

This milestone ranks only whether the 04:00 WIB clock geometry produces a repeatable LONG revisit structure under the same state machine as prior hourly milestones. The H2 rate is not trading WR and cannot be compared to TP/SL WR.

**Status: B27FE_BNB_HOUR04_STRUCTURE_COMPLETE**

STOP: do not test 05:00 WIB or define an entry in B27FE.
