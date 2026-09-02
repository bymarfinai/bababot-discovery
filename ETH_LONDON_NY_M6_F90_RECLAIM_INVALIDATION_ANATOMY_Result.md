# ETH London -> New York M6 F90 Early-Reclaim Invalidation Anatomy — Result

ETH raw 5m coverage: **100.0000%**.

Frozen cohort: **M5 F90 EARLY_RECLAIM executed entries only**. Outcome remains strict completed 5m breakout `close > H`; M6 installs no stop and contains no economics.

- Executed cohort: **95**
- Winners: **77**
- Non-winners: **18**
- Entry identity / terminal chronology audit: **PASS**.

## Pooled-major excursion anatomy

| Class | N | Median wick MAE | P75 | P90 | Median close DD | P75 | P90 | Median min close f |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WINNER | 77 | 0.088R | 0.176R | 0.345R | 0.033R | 0.145R | 0.301R | F87.9 |
| NON_WINNER | 18 | 0.916R | 1.113R | 1.232R | 0.779R | 1.026R | 1.079R | F13.2 |

## Completed-close boundary discrimination — pooled major

| Boundary | Winner breach | Non-winner breach | Separation | Structural candidate |
|---|---:|---:|---:|---|
| F85 | 42.9% | 100.0% | 57.1 pp | NO |
| F80 | 31.2% | 94.4% | 63.3 pp | NO |
| F75 | 22.1% | 83.3% | 61.3 pp | NO |
| F70 | 18.2% | 83.3% | 65.2 pp | NO |
| F65 | 10.4% | 83.3% | 72.9 pp | NO |
| F60 | 10.4% | 77.8% | 67.4 pp | NO |
| F55 | 7.8% | 66.7% | 58.9 pp | YES |
| F50 | 5.2% | 66.7% | 61.5 pp | YES |

## Major-partition winner protection

| Partition | Winner N | Non-winner N | F85 | F80 | F75 | F70 | F65 | F60 | F55 | F50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 32 | 7 | 46.9% | 28.1% | 15.6% | 9.4% | 6.2% | 6.2% | 3.1% | 0.0% |
| development | 32 | 9 | 46.9% | 40.6% | 31.2% | 28.1% | 15.6% | 15.6% | 12.5% | 9.4% |
| reference_validation | 13 | 2 | 23.1% | 15.4% | 15.4% | 15.4% | 7.7% | 7.7% | 7.7% | 7.7% |

## Decision

**Status: ETH_LONDON_NY_M6_STRUCTURAL_INVALIDATION_CANDIDATE_FOUND**

Frozen structural candidate family: **F55, F50**.

These are anatomy candidates only; none is an economic stop until a separately preregistered execution test.