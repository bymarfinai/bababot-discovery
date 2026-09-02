# ETH London -> New York M9A Audit Fix — Result

M9A changes no result-bearing trade semantics or economic outputs. It validates the already-persisted M9 files with NaN-safe zero-N parity and explicit floor chronology.

## M8 E15/F50 baseline parity

| Partition | Pass | N | WR | PF | Net |
|---|---|---:|---:|---:|---:|
| external | PASS | 39 | 0.820513 | 2.079557 | 58.613056 |
| development | PASS | 41 | 0.707317 | 0.896043 | -8.118493 |
| reference_validation | PASS | 15 | 0.733333 | 1.529761 | 12.328720 |
| august | PASS | 0 | - | - | 0.000000 |
| POOLED_MAJOR | PASS | 95 | 0.757895 | 1.403592 | 62.823283 |

- Floor activation chronology: **PASS**.
- Persisted 95-cohort × 4-variant shape: **PASS**.
- Baseline row count: **PASS**.

**Status: ETH_LONDON_NY_M9_AUDIT_VALID**