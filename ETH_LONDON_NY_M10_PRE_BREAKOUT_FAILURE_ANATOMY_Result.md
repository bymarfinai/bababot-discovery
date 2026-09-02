# ETH London -> New York M10 Pre-Breakout Failure Anatomy — Result

ETH raw 5m coverage: **100.0000%**.

Frozen cohort: **M5 F90 EARLY_RECLAIM executed entries**. M10 uses strict completed 5m breakout `close > H` as success and contains no economics.

- Cohort N: **95**; breakout winners: **77**; non-breakout: **18**.
- Audit: **PASS**.

## Family A — reclaim-hold boundary discrimination (pooled major)

| Boundary | Winner breach | Non-winner breach | Separation | Winner reclaim F90 after breach | Non-winner reclaim F90 after breach | Candidate |
|---|---:|---:|---:|---:|---:|---|
| F90 | 53.2% | 100.0% | 46.8 pp | 100.0% | 38.9% | NO |
| F85 | 42.9% | 100.0% | 57.1 pp | 100.0% | 27.8% | NO |
| F80 | 31.2% | 94.4% | 63.3 pp | 100.0% | 11.8% | NO |
| F75 | 22.1% | 83.3% | 61.3 pp | 100.0% | 6.7% | NO |

### Family A — major partition winner protection

| Partition | Boundary | Winner N | Non-winner N | Winner breach | Non-winner breach |
|---|---|---:|---:|---:|---:|
| external | F90 | 32 | 7 | 59.4% | 100.0% |
| external | F85 | 32 | 7 | 46.9% | 100.0% |
| external | F80 | 32 | 7 | 28.1% | 100.0% |
| external | F75 | 32 | 7 | 15.6% | 71.4% |
| development | F90 | 32 | 9 | 53.1% | 100.0% |
| development | F85 | 32 | 9 | 46.9% | 100.0% |
| development | F80 | 32 | 9 | 40.6% | 88.9% |
| development | F75 | 32 | 9 | 31.2% | 88.9% |
| reference_validation | F90 | 13 | 2 | 38.5% | 100.0% |
| reference_validation | F85 | 13 | 2 | 23.1% | 100.0% |
| reference_validation | F80 | 13 | 2 | 15.4% | 100.0% |
| reference_validation | F75 | 13 | 2 | 15.4% | 100.0% |

## Family B — progress stall

| Checkpoint | State | Pooled N | Eventual BO | External | Development | RefVal | Candidate |
|---:|---|---:|---:|---:|---:|---:|---|
| 15m | H2_DONE_NO_BO | 20 | 75.0% | 100.0% (N7) | 54.5% (N11) | 100.0% (N2) | - |
| 15m | NO_H2_NO_BO | 38 | 65.8% | 63.2% (N19) | 71.4% (N14) | 60.0% (N5) | - |
| 30m | H2_DONE_NO_BO | 18 | 72.2% | 100.0% (N7) | 44.4% (N9) | 100.0% (N2) | - |
| 30m | NO_H2_NO_BO | 26 | 61.5% | 53.8% (N13) | 70.0% (N10) | 66.7% (N3) | - |
| 45m | H2_DONE_NO_BO | 17 | 70.6% | 100.0% (N5) | 50.0% (N10) | 100.0% (N2) | - |
| 45m | NO_H2_NO_BO | 20 | 50.0% | 45.5% (N11) | 62.5% (N8) | 0.0% (N1) | - |
| 60m | H2_DONE_NO_BO | 15 | 66.7% | 100.0% (N5) | 44.4% (N9) | 100.0% (N1) | - |
| 60m | NO_H2_NO_BO | 15 | 40.0% | 25.0% (N8) | 66.7% (N6) | 0.0% (N1) | - |

## Development decomposition

- Executed: **41**; breakout winners: **32**; non-breakout failures: **9**.
- Winner median entry->H2: **10.0m**; winner median entry->strict breakout: **17.5m**.
- Non-winner median entry->terminal/session end: **190.0m**.

| Boundary | Dev winner breach | Dev non-winner breach |
|---|---:|---:|
| F90 | 53.1% | 100.0% |
| F85 | 46.9% | 100.0% |
| F80 | 40.6% | 88.9% |
| F75 | 31.2% | 88.9% |

## Decision

**Status: ETH_LONDON_NY_M10_NO_PRE_BO_FAILURE_SIGNATURE**

- Family A structural candidates: **none**.
- Family B stall candidates: **none**.
- M10 does not authorize an exit/filter. Any candidate must be tested separately with frozen execution semantics and economics.