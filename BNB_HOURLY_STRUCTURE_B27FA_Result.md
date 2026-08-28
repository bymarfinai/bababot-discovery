# BNB Hour-by-Hour Structural Discovery — B27FA

**Anchor tested:** 00:00 WIB only.

- Reference: 00:00–04:00 WIB
- Execution: 04:00–08:00 WIB
- Development only: 2022-01-01 through 2025-01-01 UTC
- Raw loader coverage: 100.0000%
- Structure only: K1 -> causal leave -> H2 using frozen B27EM causal ordering
- No entry, TP, SL, PnL, fee, or holdout economics

## Pooled result

- Complete sessions: **1095**
- K1 qualified: **230 (21.0%)**
- Causal leaves: **137**
- H2 arrivals: **105**
- Opposite breaks before H2: **5**
- Ambiguous H2/opposite: **0**
- No H2 by end: **27**
- H2 / causal-leave rate: **76.6%**
- Resolved H2 share: **95.5%**
- Median leave -> H2: **20.0 min**
- Frozen structural label: **STRONG_STRUCTURAL**

## Weekday breakdown

| Day | Sessions | K1 | Leaves | H2 | H2/leave | Opposite | No H2 | Resolved H2 share | Med leave->H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monday | 157 | 30 | 24 | 18 | 75.0% | 0 | 6 | 100.0% | 15.0m |
| Tuesday | 157 | 35 | 19 | 18 | 94.7% | 0 | 1 | 100.0% | 12.5m |
| Wednesday | 156 | 28 | 18 | 13 | 72.2% | 0 | 5 | 100.0% | 20.0m |
| Thursday | 156 | 36 | 23 | 17 | 73.9% | 1 | 5 | 94.4% | 40.0m |
| Friday | 156 | 35 | 19 | 10 | 52.6% | 2 | 7 | 83.3% | 40.0m |
| Saturday | 156 | 41 | 18 | 16 | 88.9% | 1 | 1 | 94.1% | 27.5m |
| Sunday | 157 | 25 | 16 | 13 | 81.2% | 1 | 2 | 92.9% | 15.0m |

## Interpretation

This milestone ranks only whether the 00:00 WIB clock geometry produces a repeatable LONG revisit structure. The H2 rate is not trading WR and cannot be compared to TP/SL WR.

**Status: B27FA_BNB_HOUR00_STRUCTURE_COMPLETE**

STOP: do not test 01:00 WIB or define an entry in B27FA.
