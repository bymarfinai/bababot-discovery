# SOL LONG 15:00 UTC Post-H05 Secondary Trigger Anatomy — A54 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A54 observes the frozen parent after the first live `POST_H05` warning. No exit is changed and no new price threshold is scanned.

## Reconciliation

Total POST_H05 cohort: **505** = **92 TARGET + 404 FAILED_BREAK + 9 quarantined TIME**. Errors: **0**.

| Partition | Total | TARGET | FAILED_BREAK | TIME quarantine | Median warning→target | Median warning→fail |
|---|---:|---:|---:|---:|---:|---:|
| development | 219 | 31 | 184 | 4 | 20m | 5m |
| external | 148 | 32 | 113 | 3 | 25m | 10m |
| reference_validation | 138 | 29 | 107 | 2 | 20m | 5m |

## Fixed actionable candidate discrimination

| Candidate | Part | Fail hit | Target hit | Gap | Ratio | Lead | Dev blocks | Replicated |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| C1_STILL_H05_5M | development | 17.9% | 16.1% | 1.8% | 1.11x | 10m | 3/6 | no |
| C1_STILL_H05_5M | external | 26.5% | 34.4% | -7.8% | 0.77x | 10m | - | no |
| C1_STILL_H05_5M | reference_validation | 15.0% | 27.6% | -12.6% | 0.54x | 5m | - | no |
| C2_NOT_ABOVE_H10_5M | development | 34.2% | 35.5% | -1.2% | 0.96x | 10m | 1/6 | no |
| C2_NOT_ABOVE_H10_5M | external | 43.4% | 56.2% | -12.9% | 0.77x | 10m | - | no |
| C2_NOT_ABOVE_H10_5M | reference_validation | 27.1% | 44.8% | -17.7% | 0.60x | 10m | - | no |
| C3_NO_CLOSE_ABOVE_H10_10M | development | 13.0% | 16.1% | -3.1% | 0.81x | 10m | 2/6 | no |
| C3_NO_CLOSE_ABOVE_H10_10M | external | 20.4% | 34.4% | -14.0% | 0.59x | 10m | - | no |
| C3_NO_CLOSE_ABOVE_H10_10M | reference_validation | 10.3% | 24.1% | -13.9% | 0.43x | 5m | - | no |
| C4_STILL_H05_10M | development | 10.3% | 3.2% | 7.1% | 3.20x | 10m | 5/6 | no |
| C4_STILL_H05_10M | external | 16.8% | 21.9% | -5.1% | 0.77x | 10m | - | no |
| C4_STILL_H05_10M | reference_validation | 6.5% | 13.8% | -7.3% | 0.47x | 5m | - | no |
| C5_NO_CLOSE_ABOVE_H10_15M | development | 6.5% | 3.2% | 3.3% | 2.02x | 10m | 4/6 | no |
| C5_NO_CLOSE_ABOVE_H10_15M | external | 8.0% | 15.6% | -7.7% | 0.51x | 10m | - | no |
| C5_NO_CLOSE_ABOVE_H10_15M | reference_validation | 3.7% | 17.2% | -13.5% | 0.22x | 20m | - | no |

## Pooled post-warning state progression

| T | Outcome | terminal fail | target | alive H05 | alive H10 | alive >H10 |
|---:|---|---:|---:|---:|---:|---:|
| +5m | FAILED_BREAK | 53.5% | 0.0% | 19.6% | 15.3% | 11.6% |
| +5m | RECOVER_E40 | 0.0% | 7.6% | 26.1% | 19.6% | 46.7% |
| +10m | FAILED_BREAK | 69.6% | 0.0% | 11.1% | 6.9% | 12.4% |
| +10m | RECOVER_E40 | 0.0% | 29.3% | 13.0% | 22.8% | 34.8% |
| +15m | FAILED_BREAK | 79.0% | 0.0% | 6.2% | 5.9% | 8.9% |
| +15m | RECOVER_E40 | 0.0% | 44.6% | 5.4% | 10.9% | 39.1% |
| +30m | FAILED_BREAK | 89.1% | 0.0% | 2.5% | 2.7% | 5.7% |
| +30m | RECOVER_E40 | 0.0% | 63.0% | 1.1% | 3.3% | 32.6% |

## Decision

Replicated actionable secondary triggers: **none**.

**Status: SOL_LONG_15UTC_POST_H05_SECONDARY_TRIGGER_A54_INCONCLUSIVE**

A54 is anatomy only. A supported candidate must be separately executed in A55 at the next available open; no live rule changes are authorized here.

Research only. Live Baba Bot remains unchanged.
