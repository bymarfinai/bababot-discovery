# BNB Hour-by-Hour Structural Discovery — B27FC

**Anchor tested:** 02:00 WIB only.

- Reference: 02:00–06:00 WIB
- Execution: 06:00–10:00 WIB
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Structure only: K1 -> causal leave -> H2 using frozen B27EM/B27FA/B27FB causal ordering
- No entry, TP, SL, PnL, fee, or holdout economics

## Pooled result

- Complete sessions: **1095**
- K1 qualified: **278 (25.4%)**
- Causal leaves: **162**
- H2 arrivals: **126**
- Opposite breaks before H2: **14**
- Ambiguous H2/opposite: **0**
- No H2 by end: **22**
- H2 / causal-leave rate: **77.8%**
- Resolved H2 share: **90.0%**
- Median leave -> H2: **20.0 min**
- Frozen structural label: **STRONG_STRUCTURAL**

## Frozen comparison vs completed clocks

- 00:00 WIB: **137 leaves / 105 H2 = 76.6%**
- 01:00 WIB: **162 leaves / 132 H2 = 81.5%**
- 02:00 WIB: **162 leaves / 126 H2 = 77.8%**
- B27FC minus prior leader (01:00 WIB) H2-rate delta: **-3.7 percentage points**

## Weekday breakdown

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 36 | 21 | 17 | 81.0% | 1 | 3 | 94.4% | 15.0m |
| Tuesday | 157 | 41 | 26 | 21 | 80.8% | 2 | 3 | 91.3% | 35.0m |
| Wednesday | 156 | 35 | 24 | 22 | 91.7% | 1 | 1 | 95.7% | 22.5m |
| Thursday | 156 | 43 | 19 | 12 | 63.2% | 5 | 2 | 70.6% | 12.5m |
| Friday | 156 | 48 | 25 | 19 | 76.0% | 1 | 5 | 95.0% | 30.0m |
| Saturday | 156 | 40 | 28 | 23 | 82.1% | 2 | 3 | 92.0% | 25.0m |
| Sunday | 157 | 35 | 19 | 12 | 63.2% | 2 | 5 | 85.7% | 12.5m |

## Interpretation

This milestone ranks only whether the 02:00 WIB clock geometry produces a repeatable LONG revisit structure under the same state machine as prior hourly milestones. The H2 rate is not trading WR and cannot be compared to TP/SL WR.

**Status: B27FC_BNB_HOUR02_STRUCTURE_COMPLETE**

STOP: do not test 03:00 WIB or define an entry in B27FC.
